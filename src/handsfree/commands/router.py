"""Command router and response composer."""

import logging
import os
from typing import Any

import duckdb

from handsfree.ai import execute_ai_capability
from handsfree.auth import FIXTURE_USER_ID
from handsfree.mcp import get_provider_descriptor, infer_provider_capability

from .intent_parser import ParsedIntent
from .pending_actions import PendingActionManager
from .profiles import Profile, ProfileConfig
from .session_context import SessionContext

logger = logging.getLogger(__name__)

# Constants for response formatting
PR_TITLE_PREVIEW_LENGTH = 30  # Max characters for PR title previews in brief summaries


class CommandRouter:
    """Route parsed intents to handlers and compose responses."""

    # Intents that require confirmation (side effects)
    SIDE_EFFECT_INTENTS = {
        "pr.request_review",
        "pr.merge",
        "agent.delegate",
        "checks.rerun",
        "pr.comment",
    }

    def __init__(
        self,
        pending_actions: PendingActionManager,
        db_conn: duckdb.DuckDBPyConnection | None = None,
        github_provider: Any | None = None,
    ) -> None:
        """Initialize the router.

        Args:
            pending_actions: Manager for pending confirmation actions
            db_conn: Optional database connection for agent operations
            github_provider: Optional GitHub provider for fetching PR/check data
        """
        self.pending_actions = pending_actions
        self.db_conn = db_conn
        self.github_provider = github_provider
        # Session state for system.repeat - maps session_id to last response
        self._last_responses: dict[str, dict[str, Any]] = {}
        # Session state for system.next - maps session_id to (items, current_index)
        self._navigation_state: dict[str, tuple[list[dict[str, Any]], int]] = {}
        # Session context for tracking repo/PR across commands
        self._session_context = SessionContext()

        # Initialize agent service if DB is available
        self._agent_service = None
        if db_conn:
            from handsfree.agents.service import AgentService

            self._agent_service = AgentService(db_conn)

    def route(
        self,
        intent: ParsedIntent,
        profile: Profile,
        session_id: str | None = None,
        user_id: str | None = None,
        idempotency_key: str | None = None,
    ) -> dict[str, Any]:
        """Route an intent to appropriate handler and compose response.

        Args:
            intent: Parsed intent from the parser
            profile: User's current profile
            session_id: Optional session identifier for repeat functionality
            user_id: Optional user identifier for policy evaluation and audit logging
            idempotency_key: Optional idempotency key for deduplication

        Returns:
            Dictionary conforming to CommandResponse schema
        """
        profile_config = ProfileConfig.for_profile(profile)

        # Handle debug commands
        if intent.name == "debug.transcript":
            return self._handle_debug_transcript(user_id, profile_config, intent)

        # Handle system commands
        if intent.name == "system.repeat":
            return self._handle_repeat(session_id, profile_config, intent)
        elif intent.name == "system.next":
            return self._handle_next(session_id, profile_config, intent)
        elif intent.name == "system.confirm":
            return self._handle_confirm(intent, profile_config)
        elif intent.name == "system.cancel":
            return self._handle_cancel(intent, profile_config)
        elif intent.name == "system.set_profile":
            return self._handle_set_profile(intent, profile_config)

        # Special handling for pr.request_review - integrate with policy engine
        # Policy-based handling takes precedence over profile-based confirmation
        if intent.name == "pr.request_review" and self.db_conn and user_id:
            return self._handle_request_review_with_policy(
                intent, user_id, session_id, idempotency_key
            )

        # Special handling for checks.rerun - integrate with policy engine
        if intent.name == "checks.rerun" and self.db_conn and user_id:
            return self._handle_rerun_checks_with_policy(
                intent, user_id, session_id, idempotency_key
            )

        # Special handling for pr.comment - integrate with policy engine
        if intent.name == "pr.comment" and self.db_conn and user_id:
            return self._handle_comment_with_policy(intent, user_id, session_id, idempotency_key)

        # Check if this is a side-effect intent requiring confirmation (profile-based fallback)
        if intent.name in self.SIDE_EFFECT_INTENTS and profile_config.confirmation_required:
            return self._create_confirmation_response(intent, profile_config)

        # Route to domain handlers
        if intent.name == "inbox.list":
            response = self._handle_inbox_list(intent, profile_config, user_id)
        elif intent.name.startswith("pr."):
            response = self._handle_pr_intent(intent, profile_config, user_id)
        elif intent.name.startswith("checks."):
            response = self._handle_checks_intent(intent, profile_config)
        elif intent.name.startswith("agent."):
            response = self._handle_agent_intent(intent, profile_config, user_id)
        elif intent.name.startswith("ai."):
            response = self._handle_ai_intent(intent, profile_config, session_id)
        elif intent.name == "unknown":
            response = self._handle_unknown(intent, profile_config)
        else:
            response = {
                "status": "error",
                "intent": intent.to_dict(),
                "spoken_text": "I don't know how to handle that yet.",
            }

        # Store response for system.repeat
        if session_id:
            self._last_responses[session_id] = response

            # Store navigation state for list-like responses
            self._store_navigation_state(session_id, response, intent)

            # Capture repo/PR context from certain intents
            self._capture_session_context(session_id, intent)

        return response

    def _create_confirmation_response(
        self, intent: ParsedIntent, profile_config: ProfileConfig
    ) -> dict[str, Any]:
        """Create a response requesting confirmation for a side-effect intent."""
        # Generate human-readable summary
        summary = self._format_confirmation_summary(intent)

        # Create pending action
        pending = self.pending_actions.create(
            intent_name=intent.name, entities=intent.entities, summary=summary
        )

        spoken_text = f"{summary} Say 'confirm' to proceed."
        if profile_config.profile == Profile.WORKOUT:
            spoken_text = f"{summary} Confirm?"

        # Apply profile-based truncation
        spoken_text = profile_config.truncate_spoken_text(spoken_text)

        return {
            "status": "needs_confirmation",
            "intent": intent.to_dict(),
            "spoken_text": spoken_text,
            "pending_action": pending.to_dict(),
        }

    def _format_confirmation_summary(self, intent: ParsedIntent) -> str:
        """Format a human-readable summary of the pending action."""
        if intent.name == "pr.request_review":
            reviewers = intent.entities.get("reviewers", [])
            pr_num = intent.entities.get("pr_number")
            reviewers_str = " and ".join(reviewers)
            if pr_num:
                return f"I can request review from {reviewers_str} on PR {pr_num}."
            return f"I can request review from {reviewers_str}."
        elif intent.name == "pr.merge":
            pr_num = intent.entities.get("pr_number", "this PR")
            method = intent.entities.get("merge_method", "merge")
            return f"I can {method} PR {pr_num}."
        elif intent.name == "agent.delegate":
            instruction = intent.entities.get("instruction", "handle this")
            issue_num = intent.entities.get("issue_number")
            pr_num = intent.entities.get("pr_number")
            provider = intent.entities.get("provider", "copilot")
            provider_descriptor = get_provider_descriptor(provider)
            provider_label = provider_descriptor.display_name if provider_descriptor else "the agent"
            if issue_num:
                return f"I can ask {provider_label} to {instruction} issue {issue_num}."
            elif pr_num:
                return f"I can ask {provider_label} to {instruction} PR {pr_num}."
            return f"I can delegate to {provider_label}: {instruction}."
        elif intent.name == "checks.rerun":
            pr_num = intent.entities.get("pr_number")
            if pr_num:
                return f"I can re-run checks on PR {pr_num}."
            return "I can re-run checks."
        elif intent.name == "pr.comment":
            pr_num = intent.entities.get("pr_number")
            comment_body = intent.entities.get("comment_body", "")
            # Truncate long comments in confirmation message
            preview = comment_body[:50] + "..." if len(comment_body) > 50 else comment_body
            return f"I can post comment on PR {pr_num}: {preview}"
        return "I can execute this action."

    def _handle_repeat(
        self,
        session_id: str | None,
        profile_config: ProfileConfig,
        intent: ParsedIntent,
    ) -> dict[str, Any]:
        """Handle system.repeat to replay last response."""
        if not session_id or session_id not in self._last_responses:
            spoken_text = profile_config.truncate_spoken_text("Nothing to repeat.")
            return {
                "status": "ok",
                "intent": intent.to_dict(),
                "spoken_text": spoken_text,
            }

        # Return the last response for this session
        return self._last_responses[session_id]

    def _handle_next(
        self,
        session_id: str | None,
        profile_config: ProfileConfig,
        intent: ParsedIntent,
    ) -> dict[str, Any]:
        """Handle system.next to advance through list items."""
        if not session_id or session_id not in self._navigation_state:
            spoken_text = profile_config.truncate_spoken_text(
                "No list to navigate. Try asking for inbox or PR summary first."
            )
            return {
                "status": "ok",
                "intent": intent.to_dict(),
                "spoken_text": spoken_text,
            }

        items, current_index = self._navigation_state[session_id]
        next_index = current_index + 1

        if next_index >= len(items):
            spoken_text = profile_config.truncate_spoken_text("No more items.")
            return {
                "status": "ok",
                "intent": intent.to_dict(),
                "spoken_text": spoken_text,
            }

        # Update navigation state
        self._navigation_state[session_id] = (items, next_index)

        # Build response for next item
        next_item = items[next_index]
        response = self._build_item_response(next_item, next_index, len(items), profile_config)

        # Store as last response for repeat
        self._last_responses[session_id] = response

        return response

    def _store_navigation_state(
        self,
        session_id: str,
        response: dict[str, Any],
        intent: ParsedIntent,
    ) -> None:
        """Store navigation state for list-like responses.

        Args:
            session_id: Session identifier
            response: Response dict that may contain navigable items
            intent: The intent that generated this response
        """
        # Check if response has cards (indicates list-like data)
        if "cards" not in response or not response["cards"]:
            # Clear navigation state if no cards
            if session_id in self._navigation_state:
                del self._navigation_state[session_id]
            return

        # Store cards as navigable items with metadata
        items = []
        for card in response["cards"]:
            items.append(
                {
                    "type": "card",
                    "intent_name": intent.name,
                    "data": card,
                }
            )

        # Store with index 0 (showing first item)
        self._navigation_state[session_id] = (items, 0)

    def _capture_session_context(
        self,
        session_id: str,
        intent: ParsedIntent,
    ) -> None:
        """Capture repo/PR context from intents that reference them.

        This allows subsequent commands to omit repo/PR and use the last
        referenced values from the session.

        Args:
            session_id: Session identifier
            intent: The intent that may contain repo/PR references
        """
        # Capture context from pr.summarize
        if intent.name == "pr.summarize":
            pr_number = intent.entities.get("pr_number")
            repo = intent.entities.get("repo")
            if pr_number and repo:
                self._session_context.set_repo_pr(session_id, repo, pr_number)
            elif pr_number:
                # If no repo specified, use a default or preserve existing repo
                context = self._session_context.get_repo_pr(session_id)
                repo = context.get("repo", "default/repo")
                self._session_context.set_repo_pr(session_id, repo, pr_number)

        # Capture context from checks.status
        elif intent.name == "checks.status":
            pr_number = intent.entities.get("pr_number")
            repo = intent.entities.get("repo")
            if pr_number and repo:
                self._session_context.set_repo_pr(session_id, repo, pr_number)
            elif pr_number:
                # If no repo specified, use a default or preserve existing repo
                context = self._session_context.get_repo_pr(session_id)
                repo = context.get("repo", "default/repo")
                self._session_context.set_repo_pr(session_id, repo, pr_number)

        elif intent.name.startswith("ai."):
            pr_number = intent.entities.get("pr_number")
            repo = intent.entities.get("repo")
            if pr_number and repo:
                self._session_context.set_repo_pr(session_id, repo, pr_number)
            elif pr_number:
                context = self._session_context.get_repo_pr(session_id)
                repo = context.get("repo", "default/repo")
                self._session_context.set_repo_pr(session_id, repo, pr_number)

        # Note: inbox.list doesn't capture PR context since it shows multiple PRs
        # We only capture single PR references for now

    def _handle_debug_transcript(
        self, user_id: str | None, profile_config: ProfileConfig, intent: ParsedIntent
    ) -> dict[str, Any]:
        """Handle debug.transcript to return the last stored transcript.

        Args:
            user_id: User identifier for filtering commands
            profile_config: User's profile configuration
            intent: The debug.transcript intent

        Returns:
            Response dict with the last transcript
        """
        from handsfree.db.commands import get_commands
        from handsfree.logging_utils import redact_secrets

        if not self.db_conn or not user_id:
            spoken_text = profile_config.truncate_spoken_text("Debug information not available.")
            return {
                "status": "error",
                "intent": intent.to_dict(),
                "spoken_text": spoken_text,
            }

        # Get the most recent command with transcript for this user
        commands = get_commands(
            self.db_conn,
            user_id=user_id,
            limit=10,  # Check last 10 commands
        )

        # Find the first command with a transcript
        last_transcript = None
        for cmd in commands:
            if cmd.transcript:
                last_transcript = cmd.transcript
                break

        if not last_transcript:
            spoken_text = profile_config.truncate_spoken_text(
                "No recent transcript found. Try enabling debug mode in your client."
            )
            return {
                "status": "ok",
                "intent": intent.to_dict(),
                "spoken_text": spoken_text,
            }

        # Redact secrets from transcript
        safe_transcript = redact_secrets(last_transcript)

        # Build response based on profile
        if profile_config.profile == Profile.WORKOUT:
            spoken_text = f"I heard: {safe_transcript}"
        else:
            spoken_text = f"The last command I heard was: {safe_transcript}"

        spoken_text = profile_config.truncate_spoken_text(spoken_text)

        return {
            "status": "ok",
            "intent": intent.to_dict(),
            "spoken_text": spoken_text,
        }

    def _build_item_response(
        self,
        item: dict[str, Any],
        index: int,
        total: int,
        profile_config: ProfileConfig,
    ) -> dict[str, Any]:
        """Build a response for a single navigation item.

        Args:
            item: Item data dict
            index: Current item index (0-based)
            total: Total number of items
            profile_config: User's profile configuration

        Returns:
            Response dict
        """
        intent_name = item.get("intent_name", "unknown")
        card_data = item.get("data", {})

        # Build spoken text based on profile
        if profile_config.profile == Profile.WORKOUT:
            spoken_text = f"Item {index + 1} of {total}: {card_data.get('title', 'Unknown')}."
        else:
            title = card_data.get("title", "Unknown")
            subtitle = card_data.get("subtitle", "")
            spoken_text = f"Item {index + 1} of {total}: {title}. {subtitle}"

        # Apply profile-based truncation
        spoken_text = profile_config.truncate_spoken_text(spoken_text)

        return {
            "status": "ok",
            "intent": {
                "name": f"system.next.{intent_name}",
                "confidence": 1.0,
                "entities": {"index": index, "total": total},
            },
            "spoken_text": spoken_text,
            "cards": [card_data],
        }

    def _handle_confirm(
        self, intent: ParsedIntent, profile_config: ProfileConfig
    ) -> dict[str, Any]:
        """Handle system.confirm - execute pending action."""
        # In a real implementation, this would get the pending token from context
        # For now, return a placeholder
        spoken_text = profile_config.truncate_spoken_text(
            "Confirmation received. This will be implemented in the API endpoint."
        )
        return {
            "status": "ok",
            "intent": intent.to_dict(),
            "spoken_text": spoken_text,
        }

    def _handle_cancel(self, intent: ParsedIntent, profile_config: ProfileConfig) -> dict[str, Any]:
        """Handle system.cancel - cancel pending action."""
        spoken_text = profile_config.truncate_spoken_text("Cancelled.")
        return {
            "status": "ok",
            "intent": intent.to_dict(),
            "spoken_text": spoken_text,
        }

    def _handle_set_profile(
        self, intent: ParsedIntent, profile_config: ProfileConfig
    ) -> dict[str, Any]:
        """Handle system.set_profile to change user profile."""
        profile_name = intent.entities.get("profile", "default")
        spoken_text = profile_config.truncate_spoken_text(f"Switched to {profile_name} mode.")
        return {
            "status": "ok",
            "intent": intent.to_dict(),
            "spoken_text": spoken_text,
        }

    def _handle_inbox_list(
        self, intent: ParsedIntent, profile_config: ProfileConfig, user_id: str | None = None
    ) -> dict[str, Any]:
        """Handle inbox.list intent with profile-based verbosity."""
        # Get user from intent entities or fall back to fixture user
        user = intent.entities.get("user", "testuser")
        
        # Use GitHub provider if available
        if self.github_provider:
            from handsfree.handlers.inbox import handle_inbox_list
            
            # Use privacy mode from profile configuration
            privacy_mode = profile_config.privacy_mode
            
            try:
                # Call the inbox handler with user_id for live mode support
                result = handle_inbox_list(
                    provider=self.github_provider,
                    user=user,
                    privacy_mode=privacy_mode,
                    profile_config=profile_config,
                    user_id=user_id,
                )
                
                # Return response with inbox items
                return {
                    "status": "ok",
                    "intent": intent.to_dict(),
                    "spoken_text": result["spoken_text"],
                    "cards": [
                        {
                            "title": item["title"],
                            "subtitle": f"{item['repo']} • Priority {item['priority']}",
                            "url": item["url"],
                        }
                        for item in result["items"][:5]  # Limit to top 5 for UI
                    ] if "items" in result and result["items"] else [],
                }
            except Exception as e:
                logger.error("Failed to fetch inbox: %s", str(e))
                # Fall back to error message
                spoken_text = "Could not fetch inbox items."
                if profile_config.profile == Profile.WORKOUT:
                    spoken_text = "Inbox unavailable."
                spoken_text = profile_config.truncate_spoken_text(spoken_text)
                return {
                    "status": "error",
                    "intent": intent.to_dict(),
                    "spoken_text": spoken_text,
                }
        
        # Fallback: Stub data if no GitHub provider
        profile = profile_config.profile

        if profile == Profile.WORKOUT:
            # Ultra-brief: key numbers only
            spoken_text = "2 PRs, 1 failing."
        elif profile == Profile.COMMUTE:
            # Brief: essential info
            spoken_text = "You have 2 PRs waiting for review and 1 failing check."
        elif profile == Profile.FOCUSED:
            # Minimal: actionable items only
            spoken_text = "2 PRs need review. 1 check failing on PR 145."
        elif profile == Profile.KITCHEN:
            # Moderate: conversational
            spoken_text = "You have 2 pull requests waiting for review and 1 check that's failing."
        elif profile == Profile.RELAXED:
            # Detailed: full context
            spoken_text = (
                "You have 2 pull requests waiting for your review. "
                "PR 142 from alice and PR 145 from bob. "
                "There's also 1 failing check on PR 145 that needs attention."
            )
        else:  # DEFAULT
            # Balanced
            spoken_text = "You have 2 PRs waiting for review and 1 failing check."

        # Apply profile-based truncation as safety net
        spoken_text = profile_config.truncate_spoken_text(spoken_text)

        return {
            "status": "ok",
            "intent": intent.to_dict(),
            "spoken_text": spoken_text,
        }

    def _format_inbox_summary(
        self, prs: list[dict[str, Any]], profile_config: ProfileConfig
    ) -> str:
        """Format inbox summary based on profile verbosity.

        Args:
            prs: List of PR dictionaries
            profile_config: User's profile configuration

        Returns:
            Formatted spoken summary
        """
        if not prs:
            if profile_config.profile == Profile.WORKOUT:
                return "Inbox empty."
            return "Your inbox is empty."

        count = len(prs)

        # Count actionable vs informational
        review_requests = sum(1 for pr in prs if pr.get("requested_reviewer", False))
        assignments = sum(1 for pr in prs if pr.get("assignee", False))

        # Build summary based on profile
        if profile_config.profile == Profile.WORKOUT:
            # Ultra-brief: just counts
            if review_requests > 0:
                return f"{review_requests} PRs."
            return f"{count} items."

        elif profile_config.profile == Profile.FOCUSED:
            # Brief, actionable items only
            actionable = review_requests + assignments
            if actionable > 0:
                return f"{actionable} actionable PRs."
            return f"{count} inbox items."

        elif profile_config.profile == Profile.RELAXED:
            # Detailed: full context
            parts = []
            if review_requests > 0:
                parts.append(
                    f"{review_requests} pull request{'s' if review_requests != 1 else ''} "
                    f"waiting for your review"
                )
            if assignments > 0:
                parts.append(f"{assignments} PR{'s' if assignments != 1 else ''} assigned to you")
            if not parts:
                parts.append(f"{count} inbox item{'s' if count != 1 else ''}")

            summary = "You have " + " and ".join(parts) + "."

            # Add detail about first PR
            if prs:
                first_pr = prs[0]
                summary += (
                    f" First item: PR #{first_pr.get('pr_number')} "
                    f"in {first_pr.get('repo', 'unknown')}: {first_pr.get('title', 'Untitled')}."
                )

            return summary

        else:
            # Moderate/default: balanced detail
            parts = []
            if review_requests > 0:
                parts.append(f"{review_requests} PRs for review")
            if assignments > 0:
                parts.append(f"{assignments} assigned")
            if not parts:
                parts.append(f"{count} items")

            return "You have " + " and ".join(parts) + "."

    def _handle_pr_intent(
        self, intent: ParsedIntent, profile_config: ProfileConfig, user_id: str | None = None
    ) -> dict[str, Any]:
        """Handle PR-related intents with profile-based verbosity."""
        profile = profile_config.profile

        if intent.name == "pr.summarize":
            pr_num = intent.entities.get("pr_number")
            repo = intent.entities.get("repo", "owner/repo")  # Default repo for fixture mode

            if pr_num and self._use_cli_for_read_intents():
                try:
                    from handsfree.cli import GitHubCLIAdapter

                    result = GitHubCLIAdapter().summarize_pr(pr_num, profile_config)
                    return {
                        "status": "ok",
                        "intent": intent.to_dict(),
                        "spoken_text": result["spoken_text"],
                        "cards": [
                            {
                                "title": result["title"],
                                "subtitle": (
                                    f"PR #{pr_num} • {result['state']} • by {result['author']}"
                                ),
                                "lines": [
                                    (
                                        f"{result['changed_files']} files, "
                                        f"+{result['additions']} -{result['deletions']}"
                                    )
                                ],
                            }
                        ],
                        "debug": {"tool_calls": [result["trace"]]},
                    }
                except Exception as e:
                    logger.info("CLI PR summary unavailable, falling back: %s", str(e))

            # Use GitHub provider if available and pr_number is specified
            if self.github_provider and pr_num:
                from handsfree.handlers.pr_summary import handle_pr_summarize

                # Use privacy mode from profile configuration
                privacy_mode = profile_config.privacy_mode

                try:
                    # Call the PR summary handler with user_id for live mode support
                    result = handle_pr_summarize(
                        provider=self.github_provider,
                        repo=repo,
                        pr_number=pr_num,
                        privacy_mode=privacy_mode,
                        profile_config=profile_config,
                        user_id=user_id,
                    )
                    
                    # Return response with PR details
                    return {
                        "status": "ok",
                        "intent": intent.to_dict(),
                        "spoken_text": result["spoken_text"],
                        "cards": [
                            {
                                "title": result["title"],
                                "subtitle": f"PR #{pr_num} • {result['state']} • by {result['author']}",
                                "body": f"{result['changed_files']} files, +{result['additions']} -{result['deletions']}",
                            }
                        ],
                    }
                except Exception as e:
                    logger.error("Failed to fetch PR summary for %s#%d: %s", repo, pr_num, str(e))
                    # Fall back to error message
                    spoken_text = f"Could not fetch PR {pr_num}."
                    if profile_config.profile == Profile.WORKOUT:
                        spoken_text = f"PR {pr_num} unavailable."
                    spoken_text = profile_config.truncate_spoken_text(spoken_text)
                    return {
                        "status": "error",
                        "intent": intent.to_dict(),
                        "spoken_text": spoken_text,
                    }
            
            # Fallback: stub data
            pr_num_str = str(pr_num) if pr_num else "unknown"
            
            # Stub data - in production this would come from GitHub provider
            # Generate profile-appropriate PR summaries
            if profile == Profile.WORKOUT:
                # Ultra-brief: 1-2 sentences, key numbers only
                spoken_text = f"PR {pr_num_str}: command system."
            elif profile == Profile.COMMUTE:
                # Brief: 2-3 sentences, essential info
                spoken_text = (
                    f"PR {pr_num_str} adds the command system. "
                    "It includes intent parsing and profile support."
                )
            elif profile == Profile.FOCUSED:
                # Minimal: brief, actionable
                spoken_text = (
                    f"PR {pr_num_str} adds command system with intent parsing. Ready for review."
                )
            elif profile == Profile.KITCHEN:
                # Moderate: 3-4 sentences, conversational
                spoken_text = (
                    f"PR {pr_num_str} adds the command system with intent parsing. "
                    "It supports profiles like workout and commute. "
                    "The system includes confirmation flow for side effects."
                )
            elif profile == Profile.RELAXED:
                # Detailed: full context, all details
                spoken_text = (
                    f"PR {pr_num_str} adds the command system with intent parsing "
                    "and profile support. "
                    "The system recognizes voice commands and routes them to "
                    "appropriate handlers. "
                    "It includes profiles for workout, commute, kitchen, focused, "
                    "and relaxed contexts. "
                    "There's a confirmation flow for side-effect intents, "
                    "and the spoken responses are adjusted based on the active profile."
                )
            else:  # DEFAULT
                # Balanced
                spoken_text = f"PR {pr_num_str} adds the command system with intent parsing."

        elif intent.name == "pr.request_review":
            # Should have been caught by confirmation flow
            spoken_text = "Review request submitted."
        elif intent.name == "pr.merge":
            # Should have been caught by confirmation flow
            spoken_text = "Merge submitted."
        else:
            spoken_text = "PR intent recognized but not implemented."

        # Apply profile-based truncation as safety net
        spoken_text = profile_config.truncate_spoken_text(spoken_text)

        return {
            "status": "ok",
            "intent": intent.to_dict(),
            "spoken_text": spoken_text,
        }

    def _handle_ai_intent(
        self,
        intent: ParsedIntent,
        profile_config: ProfileConfig,
        session_id: str | None = None,
    ) -> dict[str, Any]:
        """Handle AI / Copilot read-only intents."""
        command_map = {
            "ai.explain_pr": {
                "capability_id": "copilot.pr.explain",
                "card_title": "Copilot explanation",
                "error_label": "explain",
            },
            "ai.summarize_diff": {
                "capability_id": "copilot.pr.diff_summary",
                "card_title": "Copilot diff summary",
                "error_label": "summarize diff for",
            },
            "ai.explain_failure": {
                "capability_id": "copilot.pr.failure_explain",
                "card_title": "Copilot failure analysis",
                "error_label": "explain failing checks for",
            },
        }
        if intent.name not in command_map:
            spoken_text = profile_config.truncate_spoken_text("I don't know that AI command yet.")
            return {
                "status": "error",
                "intent": intent.to_dict(),
                "spoken_text": spoken_text,
            }

        pr_num = intent.entities.get("pr_number")
        repo = intent.entities.get("repo")
        if not pr_num:
            context = self._session_context.get_repo_pr(session_id, fallback_repo="default/repo")
            pr_num = context.get("pr_number")
            if not repo:
                repo = context.get("repo")
        if not pr_num:
            spoken_text = profile_config.truncate_spoken_text("Please specify a PR number.")
            return {
                "status": "error",
                "intent": intent.to_dict(),
                "spoken_text": spoken_text,
            }

        if not self._use_cli_for_read_intents():
            spoken_text = profile_config.truncate_spoken_text(
                "Copilot CLI explain is not enabled."
            )
            return {
                "status": "error",
                "intent": intent.to_dict(),
                "spoken_text": spoken_text,
            }

        try:
            config = command_map[intent.name]
            adapter_kwargs: dict[str, Any] = {}
            if intent.name == "ai.explain_failure":
                adapter_kwargs["failure_target"] = intent.entities.get("failure_target")
                adapter_kwargs["failure_target_type"] = intent.entities.get("failure_target_type")
            execution = execute_ai_capability(
                config["capability_id"],
                pr_number=pr_num,
                profile_config=profile_config,
                **adapter_kwargs,
            )
            result = execution.output
            card_title = f"{config['card_title']} for PR #{pr_num}"
            if repo:
                card_title = f"{card_title} on {repo}"
            return {
                "status": "ok",
                "intent": intent.to_dict(),
                "spoken_text": result["spoken_text"],
                "cards": [
                    {
                        "title": card_title,
                        "subtitle": result["headline"],
                        "lines": [result["summary"]],
                    }
                ],
                "debug": {
                    "tool_calls": [result["trace"]],
                    "resolved_context": {"pr_number": pr_num, "repo": repo},
                    "capability_id": execution.capability_id,
                    "execution_mode": execution.execution_mode.value,
                },
            }
        except Exception as e:
            logger.error("Failed AI CLI command %s for PR %s: %s", intent.name, pr_num, str(e))
            spoken_text = profile_config.truncate_spoken_text(
                f"Could not {command_map[intent.name]['error_label']} PR {pr_num} with Copilot."
            )
            return {
                "status": "error",
                "intent": intent.to_dict(),
                "spoken_text": spoken_text,
            }

        spoken_text = profile_config.truncate_spoken_text(
            "I don't know how to handle that AI request yet."
        )
        return {
            "status": "error",
            "intent": intent.to_dict(),
            "spoken_text": spoken_text,
        }

    def _use_cli_for_read_intents(self) -> bool:
        """Return whether CLI-backed read intents are enabled."""
        return (
            os.getenv("HANDSFREE_GH_CLI_ENABLED", "false").lower() == "true"
            or os.getenv("HANDSFREE_CLI_FIXTURE_MODE", "false").lower() == "true"
        )

    def _format_pr_summary(
        self,
        pr_details: dict[str, Any],
        checks: list[dict[str, Any]],
        reviews: list[dict[str, Any]],
        profile_config: ProfileConfig,
    ) -> str:
        """Format PR summary based on profile verbosity.

        Args:
            pr_details: PR details dictionary
            checks: List of check run dictionaries
            reviews: List of review dictionaries
            profile_config: User's profile configuration

        Returns:
            Formatted spoken summary with appropriate detail level
        """
        pr_num = pr_details.get("pr_number", "unknown")
        title = pr_details.get("title", "Untitled")
        author = pr_details.get("author", "unknown")
        state = pr_details.get("state", "open")

        # Count check statuses
        checks_total = len(checks)
        checks_failing = sum(1 for c in checks if c.get("conclusion") == "failure")
        checks_pending = sum(1 for c in checks if c.get("status") != "completed")

        # Count reviews
        approvals = sum(1 for r in reviews if r.get("state") == "APPROVED")
        changes_requested = sum(1 for r in reviews if r.get("state") == "CHANGES_REQUESTED")

        # Check for security/critical labels
        labels = pr_details.get("labels", [])
        has_security = any(label.lower() in ["security", "vulnerability"] for label in labels)

        # Build summary based on profile
        if profile_config.profile == Profile.WORKOUT:
            # Ultra-brief: 1-2 sentences, key numbers only
            summary = f"PR {pr_num}: {title[:PR_TITLE_PREVIEW_LENGTH]}."
            if checks_failing > 0:
                summary += f" {checks_failing} failing."
            elif has_security:
                summary += " Security."
            return summary

        elif profile_config.profile == Profile.FOCUSED:
            # Brief, actionable items only
            summary = f"PR {pr_num}: {title}."
            if checks_failing > 0:
                summary += f" {checks_failing} checks failing."
            if changes_requested > 0:
                summary += " Changes requested."
            elif approvals > 0:
                summary += f" {approvals} approved."
            return summary

        elif profile_config.profile == Profile.RELAXED:
            # Detailed: full context, all details
            summary = f"Pull request {pr_num} by {author}: {title}."

            # Add description preview if available
            description = pr_details.get("description", "")
            if description:
                # Take first sentence or first 100 chars
                desc_preview = description.split(".")[0][:100]
                summary += f" Description: {desc_preview}."

            # Add check status
            if checks_total > 0:
                if checks_failing > 0:
                    summary += f" {checks_failing} of {checks_total} checks failing."
                elif checks_pending > 0:
                    summary += f" {checks_pending} checks still pending."
                else:
                    summary += f" All {checks_total} checks passing."

            # Add review status
            if approvals > 0:
                summary += f" {approvals} approval{'s' if approvals != 1 else ''}."
            if changes_requested > 0:
                summary += (
                    f" {changes_requested} reviewer{'s' if changes_requested != 1 else ''} "
                    "requested changes."
                )

            # Add state
            if state == "open":
                summary += " PR is open and awaiting review."

            # Security alert always included
            if has_security:
                summary += " SECURITY: This PR contains security-related changes."

            return summary

        else:
            # Moderate/default: balanced detail (2-4 sentences)
            summary = f"PR {pr_num}: {title}."

            # Add check status
            if checks_failing > 0:
                summary += f" {checks_failing} checks failing."
            elif checks_total > 0:
                summary += f" All {checks_total} checks passing."

            # Add review status
            if approvals > 0:
                summary += f" {approvals} approved."
            elif changes_requested > 0:
                summary += " Changes requested."

            # Security alert always included
            if has_security:
                summary += " Security changes included."

            return profile_config.truncate_summary(summary)

    def _handle_checks_intent(
        self, intent: ParsedIntent, profile_config: ProfileConfig
    ) -> dict[str, Any]:
        """Handle checks-related intents."""
        # If no GitHub provider, fall back to placeholder
        if not self.github_provider:
            spoken_text = "All checks passing."
            if profile_config.profile == Profile.WORKOUT:
                spoken_text = "Checks OK."
            spoken_text = profile_config.truncate_spoken_text(spoken_text)
            return {
                "status": "ok",
                "intent": intent.to_dict(),
                "spoken_text": spoken_text,
            }

        # Extract entities
        pr_number = intent.entities.get("pr_number")
        repo = intent.entities.get("repo")

        # PR-specific variant (preferred)
        if pr_number:
            # Use a default repo if not specified (in real app, would come from context)
            if not repo:
                repo = "owner/repo"  # Fallback for fixture mode

            try:
                checks = self.github_provider.get_pr_checks(repo, pr_number)
                spoken_text = self._format_checks_summary(checks, pr_number, profile_config)
            except Exception as e:
                # Log error and return fallback message
                logger.warning("Failed to fetch checks for PR %s: %s", pr_number, str(e))
                spoken_text = f"Could not fetch checks for PR {pr_number}."
                if profile_config.profile == Profile.WORKOUT:
                    spoken_text = "Check lookup failed."
        # Best-effort repo variant
        elif repo:
            # In a real implementation, this would query recent PRs or commits for the repo
            # For now, return a helpful message
            spoken_text = (
                "Checks lookup by repo requires more context. Try 'checks for pr <number>'."
            )
            if profile_config.profile == Profile.WORKOUT:
                spoken_text = "Need PR number."
        # Generic ci status (best-effort, no context)
        else:
            # Without context, we can't determine which PR/repo to check
            spoken_text = "Please specify a PR number, for example: 'checks for PR 123'."
            if profile_config.profile == Profile.WORKOUT:
                spoken_text = "Need PR number."

        # Apply profile-based truncation
        spoken_text = profile_config.truncate_spoken_text(spoken_text)

        return {
            "status": "ok",
            "intent": intent.to_dict(),
            "spoken_text": spoken_text,
        }

    def _format_checks_summary(
        self, checks: list[dict[str, Any]], pr_number: int, profile_config: ProfileConfig
    ) -> str:
        """Format a privacy-safe spoken summary of check results.

        Args:
            checks: List of check run dictionaries
            pr_number: PR number
            profile_config: User's profile configuration

        Returns:
            Spoken summary string
        """
        total = len(checks)
        if total == 0:
            if profile_config.profile == Profile.WORKOUT:
                return "No checks."
            return f"PR {pr_number} has no checks."

        # Count check statuses
        passed = sum(1 for c in checks if c.get("conclusion") == "success")
        failed = sum(1 for c in checks if c.get("conclusion") == "failure")
        pending = sum(1 for c in checks if c.get("status") != "completed")

        # Build spoken text based on status
        if failed > 0:
            # Get the first failing check name (privacy-safe)
            first_failing = next(
                (c.get("name", "unknown") for c in checks if c.get("conclusion") == "failure"),
                None,
            )
            if profile_config.profile == Profile.WORKOUT:
                spoken_text = f"{failed} failing, {passed} passing."
                if first_failing:
                    spoken_text += f" First: {first_failing}."
            else:
                spoken_text = (
                    f"PR {pr_number}: {failed} check{'s' if failed != 1 else ''} failing, "
                    f"{passed} passing."
                )
                if first_failing:
                    spoken_text += f" First failing check: {first_failing}."
        elif pending > 0:
            if profile_config.profile == Profile.WORKOUT:
                spoken_text = f"{pending} pending, {passed} passing."
            else:
                spoken_text = (
                    f"PR {pr_number}: {pending} check{'s' if pending != 1 else ''} pending, "
                    f"{passed} passing."
                )
        else:
            # All passing
            if profile_config.profile == Profile.WORKOUT:
                spoken_text = "All checks passing."
            else:
                spoken_text = (
                    f"PR {pr_number}: all {total} check{'s' if total != 1 else ''} passing."
                )

        return spoken_text

    def _get_effective_user_id(self, user_id: str | None) -> str:
        """Get effective user ID, falling back to fixture user if none provided.

        Args:
            user_id: Optional user identifier from request.

        Returns:
            User ID to use for operations (authenticated user or fixture user).
        """
        return user_id if user_id else FIXTURE_USER_ID

    def _handle_agent_intent(
        self,
        intent: ParsedIntent,
        profile_config: ProfileConfig,
        user_id: str | None = None,
    ) -> dict[str, Any]:
        """Handle agent-related intents.

        Args:
            intent: Parsed agent intent
            profile_config: User's profile configuration
            user_id: User identifier (required for agent operations)
        """
        if intent.name == "agent.delegate":
            # This should normally be caught by confirmation flow,
            # but handle it here if confirmation was bypassed
            if not self._agent_service:
                spoken_text = profile_config.truncate_spoken_text("Agent service not available.")
                return {
                    "status": "error",
                    "intent": intent.to_dict(),
                    "spoken_text": spoken_text,
                }

            if not user_id:
                spoken_text = profile_config.truncate_spoken_text(
                    "User authentication required for agent delegation."
                )
                return {
                    "status": "error",
                    "intent": intent.to_dict(),
                    "spoken_text": spoken_text,
                }

            # Extract entities
            instruction = intent.entities.get("instruction", "handle this")
            issue_num = intent.entities.get("issue_number")
            pr_num = intent.entities.get("pr_number")
            provider = intent.entities.get("provider", "copilot")
            provider_descriptor = get_provider_descriptor(provider)
            provider_label = provider_descriptor.display_name if provider_descriptor else provider
            inferred_capability = infer_provider_capability(provider, instruction)

            target_type = None
            target_ref = None
            if issue_num:
                target_type = "issue"
                target_ref = f"#{issue_num}"
            elif pr_num:
                target_type = "pr"
                target_ref = f"#{pr_num}"

            # Build trace with intent information
            from datetime import UTC, datetime

            trace = {
                "intent_name": intent.name,
                "entities": {
                    "instruction": instruction,
                    "issue_number": issue_num,
                    "pr_number": pr_num,
                    "provider": provider,
                    "provider_label": provider_label,
                    "mcp_capability": inferred_capability,
                },
                "created_at": datetime.now(UTC).isoformat(),
            }

            # Create task with authenticated user_id
            result = self._agent_service.delegate(
                user_id=user_id,
                instruction=instruction,
                provider=provider,
                target_type=target_type,
                target_ref=target_ref,
                trace=trace,
            )

            spoken_text = result.get("spoken_text", "Agent task created.")
            spoken_text = profile_config.truncate_spoken_text(spoken_text)

            response_intent = intent.to_dict()
            response_intent.setdefault("entities", {})
            response_intent["entities"] = dict(response_intent["entities"]) | {
                "task_id": result.get("task_id"),
                "provider": provider,
                "state": result.get("state"),
            }

            response: dict[str, Any] = {
                "status": "ok",
                "intent": response_intent,
                "spoken_text": spoken_text,
                "debug": {
                    "tool_calls": [
                        {
                            "task_id": result.get("task_id"),
                            "provider": result.get("provider"),
                            "state": result.get("state"),
                        }
                    ]
                },
            }

            if result.get("state") == "completed" and result.get("result_output"):
                output = result["result_output"]
                capability_label = (inferred_capability or "result").replace("_", " ")
                card_lines: list[str] = []
                if isinstance(output, dict):
                    for key in ("message", "status", "expanded_queries", "target_terms", "seed_urls"):
                        value = output.get(key)
                        if value is None:
                            continue
                        if isinstance(value, list):
                            rendered = ", ".join(str(item) for item in value[:3])
                        else:
                            rendered = str(value)
                        card_lines.append(f"{key}: {rendered}")
                response["cards"] = [
                    {
                        "title": f"{provider_label} {capability_label}",
                        "subtitle": f"Task {str(result.get('task_id', ''))[:8]} • completed",
                        "lines": card_lines[:3] or [spoken_text],
                    }
                ]
                response["debug"]["tool_calls"][0]["result_output"] = output
            else:
                response["cards"] = [
                    {
                        "title": "Agent Task Created",
                        "subtitle": f"Task {str(result.get('task_id', ''))[:8]}",
                        "lines": [
                            f"Provider: {result.get('provider')}",
                            f"Instruction: {instruction}",
                            f"State: {result.get('state')}",
                        ],
                    }
                ]

            return response

        elif intent.name == "agent.status":
            if not self._agent_service:
                spoken_text = "Agent service not available."
            else:
                if not user_id:
                    spoken_text = "User authentication required."
                else:
                    # Get status for authenticated user
                    result = self._agent_service.get_status(user_id=user_id)
                    spoken_text = result.get("spoken_text", "No agent tasks.")

            spoken_text = profile_config.truncate_spoken_text(spoken_text)

            return {
                "status": "ok",
                "intent": intent.to_dict(),
                "spoken_text": spoken_text,
            }

        elif intent.name == "agent.pause":
            if not self._agent_service:
                spoken_text = profile_config.truncate_spoken_text("Agent service not available.")
                return {
                    "status": "error",
                    "intent": intent.to_dict(),
                    "spoken_text": spoken_text,
                }

            if not user_id:
                spoken_text = profile_config.truncate_spoken_text("User authentication required.")
                return {
                    "status": "error",
                    "intent": intent.to_dict(),
                    "spoken_text": spoken_text,
                }

            task_id = intent.entities.get("task_id")
            try:
                result = self._agent_service.pause_task(user_id=user_id, task_id=task_id)
                spoken_text = result.get("spoken_text", "Task paused.")
                spoken_text = profile_config.truncate_spoken_text(spoken_text)

                return {
                    "status": "ok",
                    "intent": intent.to_dict(),
                    "spoken_text": spoken_text,
                }
            except ValueError as e:
                spoken_text = profile_config.truncate_spoken_text(str(e))
                return {
                    "status": "error",
                    "intent": intent.to_dict(),
                    "spoken_text": spoken_text,
                }

        elif intent.name == "agent.resume":
            if not self._agent_service:
                spoken_text = profile_config.truncate_spoken_text("Agent service not available.")
                return {
                    "status": "error",
                    "intent": intent.to_dict(),
                    "spoken_text": spoken_text,
                }

            if not user_id:
                spoken_text = profile_config.truncate_spoken_text("User authentication required.")
                return {
                    "status": "error",
                    "intent": intent.to_dict(),
                    "spoken_text": spoken_text,
                }

            task_id = intent.entities.get("task_id")
            try:
                result = self._agent_service.resume_task(user_id=user_id, task_id=task_id)
                spoken_text = result.get("spoken_text", "Task resumed.")
                spoken_text = profile_config.truncate_spoken_text(spoken_text)

                return {
                    "status": "ok",
                    "intent": intent.to_dict(),
                    "spoken_text": spoken_text,
                }
            except ValueError as e:
                spoken_text = profile_config.truncate_spoken_text(str(e))
                return {
                    "status": "error",
                    "intent": intent.to_dict(),
                    "spoken_text": spoken_text,
                }

        else:
            spoken_text = profile_config.truncate_spoken_text(
                "Agent intent recognized but not implemented."
            )

        return {
            "status": "ok",
            "intent": intent.to_dict(),
            "spoken_text": spoken_text,
        }

    def _handle_unknown(
        self, intent: ParsedIntent, profile_config: ProfileConfig
    ) -> dict[str, Any]:
        """Handle unknown intents."""
        spoken_text = profile_config.truncate_spoken_text("I didn't catch that. Can you try again?")
        return {
            "status": "error",
            "intent": intent.to_dict(),
            "spoken_text": spoken_text,
        }

    def _handle_request_review_with_policy(
        self,
        intent: ParsedIntent,
        user_id: str,
        session_id: str | None,
        idempotency_key: str | None,
    ) -> dict[str, Any]:
        """Handle pr.request_review with full policy evaluation, rate limiting, and audit logging.

        Args:
            intent: The parsed pr.request_review intent
            user_id: User identifier for policy evaluation
            session_id: Session identifier for context resolution
            idempotency_key: Optional idempotency key

        Returns:
            Response dict with status, spoken_text, and optional pending_action
        """
        from fastapi import HTTPException

        from handsfree.actions import DirectActionRequest, process_direct_action_request_detailed

        # Extract entities
        reviewers = intent.entities.get("reviewers", [])
        pr_number = intent.entities.get("pr_number")
        repo = intent.entities.get("repo")

        # Resolve missing repo/pr_number from session context
        if not pr_number or not repo:
            context = self._session_context.get_repo_pr(session_id, fallback_repo="default/repo")
            if not pr_number and "pr_number" in context:
                pr_number = context["pr_number"]
            if not repo and "repo" in context:
                repo = context["repo"]

        # Validate required fields
        if not pr_number:
            return {
                "status": "error",
                "intent": intent.to_dict(),
                "spoken_text": (
                    "Please specify a PR number, for example: "
                    "'request review from alice on PR 123'. "
                    "Or first check a PR summary to set context."
                ),
            }

        if not reviewers:
            return {
                "status": "error",
                "intent": intent.to_dict(),
                "spoken_text": "Please specify at least one reviewer.",
            }

        reviewers_str = ", ".join(reviewers)
        try:
            detailed = process_direct_action_request_detailed(
                conn=self.db_conn,
                user_id=user_id,
                request=DirectActionRequest(
                    endpoint="/v1/command",
                    action_type="request_review",
                    execution_action_type="request_review",
                    pending_action_type="request_review",
                    repo=repo,
                    pr_number=pr_number,
                    action_payload={
                        "repo": repo,
                        "pr_number": pr_number,
                        "reviewers": reviewers,
                    },
                    log_request={"reviewers": reviewers},
                    pending_summary=f"Request review from {reviewers_str} on {repo}#{pr_number}",
                    idempotency_key=idempotency_key,
                    anomaly_request_data={"reviewers": reviewers},
                ),
                idempotency_store={},
            )
        except HTTPException as exc:
            if exc.status_code == 403 and isinstance(exc.detail, dict):
                return {
                    "status": "error",
                    "intent": intent.to_dict(),
                    "spoken_text": f"Action not allowed: {exc.detail.get('message', 'policy denied')}",
                }
            raise

        if detailed.http_response is not None:
            retry_after = detailed.http_response.headers.get("Retry-After")
            retry_msg = f" Please try again in {retry_after} seconds." if retry_after else ""
            return {
                "status": "error",
                "intent": intent.to_dict(),
                "spoken_text": f"Rate limit exceeded.{retry_msg}",
            }

        if detailed.pending_token:
            return {
                "status": "needs_confirmation",
                "intent": intent.to_dict(),
                "spoken_text": f"{detailed.pending_summary}. Say 'confirm' to proceed.",
                "pending_action": {
                    "token": detailed.pending_token,
                    "expires_at": detailed.pending_expires_at.isoformat(),
                    "summary": detailed.pending_summary,
                },
            }

        result = detailed.action_result
        if result and result.ok:
            return {
                "status": "ok",
                "intent": intent.to_dict(),
                "spoken_text": f"Review requested from {reviewers_str} on {repo}#{pr_number}.",
            }

        return {
            "status": "error",
            "intent": intent.to_dict(),
            "spoken_text": result.message if result else "Failed to request reviewers.",
        }

    def _handle_rerun_checks_with_policy(
        self,
        intent: ParsedIntent,
        user_id: str,
        session_id: str | None,
        idempotency_key: str | None,
    ) -> dict[str, Any]:
        """Handle checks.rerun with full policy evaluation, rate limiting, and audit logging.

        Args:
            intent: The parsed checks.rerun intent
            user_id: User identifier for policy evaluation
            session_id: Session identifier for context resolution
            idempotency_key: Optional idempotency key

        Returns:
            Response dict with status, spoken_text, and optional pending_action
        """
        from fastapi import HTTPException

        from handsfree.actions import DirectActionRequest, process_direct_action_request_detailed

        # Extract entities
        pr_number = intent.entities.get("pr_number")
        repo = intent.entities.get("repo")

        # Resolve missing repo/pr_number from session context
        if not pr_number or not repo:
            context = self._session_context.get_repo_pr(session_id, fallback_repo="default/repo")
            if not pr_number and "pr_number" in context:
                pr_number = context["pr_number"]
            if not repo and "repo" in context:
                repo = context["repo"]

        # Validate required fields
        if not pr_number:
            return {
                "status": "error",
                "intent": intent.to_dict(),
                "spoken_text": (
                    "Please specify a PR number, for example: 'rerun checks for PR 123'. "
                    "Or first check a PR summary to set context."
                ),
            }

        try:
            detailed = process_direct_action_request_detailed(
                conn=self.db_conn,
                user_id=user_id,
                request=DirectActionRequest(
                    endpoint="/v1/command",
                    action_type="rerun",
                    execution_action_type="rerun",
                    pending_action_type="rerun_checks",
                    repo=repo,
                    pr_number=pr_number,
                    action_payload={"repo": repo, "pr_number": pr_number},
                    log_request={},
                    pending_summary=f"Re-run checks on {repo}#{pr_number}",
                    idempotency_key=idempotency_key,
                ),
                idempotency_store={},
            )
        except HTTPException as exc:
            if exc.status_code == 403 and isinstance(exc.detail, dict):
                return {
                    "status": "error",
                    "intent": intent.to_dict(),
                    "spoken_text": f"Action not allowed: {exc.detail.get('message', 'policy denied')}",
                }
            raise

        if detailed.http_response is not None:
            retry_after = detailed.http_response.headers.get("Retry-After")
            retry_msg = f" Please try again in {retry_after} seconds." if retry_after else ""
            return {
                "status": "error",
                "intent": intent.to_dict(),
                "spoken_text": f"Rate limit exceeded.{retry_msg}",
            }

        if detailed.pending_token:
            return {
                "status": "needs_confirmation",
                "intent": intent.to_dict(),
                "spoken_text": f"{detailed.pending_summary}. Say 'confirm' to proceed.",
                "pending_action": {
                    "token": detailed.pending_token,
                    "expires_at": detailed.pending_expires_at.isoformat(),
                    "summary": detailed.pending_summary,
                },
            }

        result = detailed.action_result
        if result and result.ok:
            return {
                "status": "ok",
                "intent": intent.to_dict(),
                "spoken_text": f"Checks re-run on {repo}#{pr_number}.",
            }

        return {
            "status": "error",
            "intent": intent.to_dict(),
            "spoken_text": result.message if result else "Failed to rerun checks.",
        }

    def _handle_comment_with_policy(
        self,
        intent: ParsedIntent,
        user_id: str,
        session_id: str | None,
        idempotency_key: str | None,
    ) -> dict[str, Any]:
        """Handle pr.comment with full policy evaluation, rate limiting, and audit logging.

        Args:
            intent: The parsed pr.comment intent
            user_id: User identifier for policy evaluation
            session_id: Session identifier for context resolution
            idempotency_key: Optional idempotency key

        Returns:
            Response dict with status, spoken_text, and optional pending_action
        """
        from fastapi import HTTPException

        from handsfree.actions import DirectActionRequest, process_direct_action_request_detailed

        # Extract entities
        pr_number = intent.entities.get("pr_number")
        comment_body = intent.entities.get("comment_body", "")
        repo = intent.entities.get("repo")

        # Resolve missing repo/pr_number from session context
        if not pr_number or not repo:
            context = self._session_context.get_repo_pr(session_id, fallback_repo="default/repo")
            if not pr_number and "pr_number" in context:
                pr_number = context["pr_number"]
            if not repo and "repo" in context:
                repo = context["repo"]

        # Validate required fields
        if not pr_number:
            return {
                "status": "error",
                "intent": intent.to_dict(),
                "spoken_text": (
                    "Please specify a PR number, for example: 'comment on PR 123: looks good'. "
                    "Or first check a PR summary to set context."
                ),
            }

        if not comment_body:
            return {
                "status": "error",
                "intent": intent.to_dict(),
                "spoken_text": "Please specify the comment text.",
            }

        comment_preview = comment_body[:50] + "..." if len(comment_body) > 50 else comment_body
        try:
            detailed = process_direct_action_request_detailed(
                conn=self.db_conn,
                user_id=user_id,
                request=DirectActionRequest(
                    endpoint="/v1/command",
                    action_type="comment",
                    execution_action_type="comment",
                    pending_action_type="comment",
                    repo=repo,
                    pr_number=pr_number,
                    action_payload={
                        "repo": repo,
                        "pr_number": pr_number,
                        "comment_body": comment_body,
                    },
                    log_request={"comment_body": comment_body},
                    pending_summary=f"Post comment on {repo}#{pr_number}: {comment_preview}",
                    idempotency_key=idempotency_key,
                    anomaly_request_data={"comment_body": comment_body},
                ),
                idempotency_store={},
            )
        except HTTPException as exc:
            if exc.status_code == 403 and isinstance(exc.detail, dict):
                return {
                    "status": "error",
                    "intent": intent.to_dict(),
                    "spoken_text": f"Action not allowed: {exc.detail.get('message', 'policy denied')}",
                }
            raise

        if detailed.http_response is not None:
            retry_after = detailed.http_response.headers.get("Retry-After")
            retry_msg = f" Please try again in {retry_after} seconds." if retry_after else ""
            return {
                "status": "error",
                "intent": intent.to_dict(),
                "spoken_text": f"Rate limit exceeded.{retry_msg}",
            }

        if detailed.pending_token:
            return {
                "status": "needs_confirmation",
                "intent": intent.to_dict(),
                "spoken_text": f"{detailed.pending_summary}. Say 'confirm' to proceed.",
                "pending_action": {
                    "token": detailed.pending_token,
                    "expires_at": detailed.pending_expires_at.isoformat(),
                    "summary": detailed.pending_summary,
                },
            }

        result = detailed.action_result
        if result and result.ok:
            return {
                "status": "ok",
                "intent": intent.to_dict(),
                "spoken_text": f"Comment posted on {repo}#{pr_number}: {comment_preview}",
            }

        return {
            "status": "error",
            "intent": intent.to_dict(),
            "spoken_text": result.message if result else "Failed to post comment.",
        }
