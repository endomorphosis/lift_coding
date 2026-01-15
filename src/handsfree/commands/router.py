"""Command router and response composer."""

import logging
from typing import Any

import duckdb

from .intent_parser import ParsedIntent
from .pending_actions import PendingActionManager
from .profiles import Profile, ProfileConfig

logger = logging.getLogger(__name__)


class CommandRouter:
    """Route parsed intents to handlers and compose responses."""

    # Intents that require confirmation (side effects)
    SIDE_EFFECT_INTENTS = {
        "pr.request_review",
        "pr.merge",
        "agent.delegate",
        "checks.rerun",
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
            return self._handle_request_review_with_policy(intent, user_id, idempotency_key)

        # Special handling for checks.rerun - integrate with policy engine
        if intent.name == "checks.rerun" and self.db_conn and user_id:
            return self._handle_rerun_checks_with_policy(intent, user_id, idempotency_key)

        # Check if this is a side-effect intent requiring confirmation (profile-based fallback)
        if intent.name in self.SIDE_EFFECT_INTENTS and profile_config.confirmation_required:
            return self._create_confirmation_response(intent, profile_config)

        # Route to domain handlers
        if intent.name == "inbox.list":
            response = self._handle_inbox_list(intent, profile_config)
        elif intent.name.startswith("pr."):
            response = self._handle_pr_intent(intent, profile_config)
        elif intent.name.startswith("checks."):
            response = self._handle_checks_intent(intent, profile_config)
        elif intent.name.startswith("agent."):
            response = self._handle_agent_intent(intent, profile_config)
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
            if issue_num:
                return f"I can ask the agent to {instruction} issue {issue_num}."
            elif pr_num:
                return f"I can ask the agent to {instruction} PR {pr_num}."
            return f"I can delegate to the agent: {instruction}."
        elif intent.name == "checks.rerun":
            pr_num = intent.entities.get("pr_number")
            if pr_num:
                return f"I can re-run checks on PR {pr_num}."
            return "I can re-run checks."
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
        self, intent: ParsedIntent, profile_config: ProfileConfig
    ) -> dict[str, Any]:
        """Handle inbox.list intent."""
        # Stub: in PR-005 this will integrate with GitHub
        spoken_text = "You have 2 PRs waiting for review and 1 failing check."
        if profile_config.profile == Profile.WORKOUT:
            spoken_text = "2 PRs, 1 failing."

        # Apply profile-based truncation
        spoken_text = profile_config.truncate_spoken_text(spoken_text)

        return {
            "status": "ok",
            "intent": intent.to_dict(),
            "spoken_text": spoken_text,
        }

    def _handle_pr_intent(
        self, intent: ParsedIntent, profile_config: ProfileConfig
    ) -> dict[str, Any]:
        """Handle PR-related intents."""
        if intent.name == "pr.summarize":
            pr_num = intent.entities.get("pr_number", "unknown")
            spoken_text = f"PR {pr_num} adds the command system with intent parsing."
            if profile_config.profile == Profile.WORKOUT:
                spoken_text = f"PR {pr_num}: command system."
        elif intent.name == "pr.request_review":
            # Should have been caught by confirmation flow
            spoken_text = "Review request submitted."
        elif intent.name == "pr.merge":
            # Should have been caught by confirmation flow
            spoken_text = "Merge submitted."
        else:
            spoken_text = "PR intent recognized but not implemented."

        # Apply profile-based truncation
        spoken_text = profile_config.truncate_spoken_text(spoken_text)

        return {
            "status": "ok",
            "intent": intent.to_dict(),
            "spoken_text": spoken_text,
        }

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

    def _handle_agent_intent(
        self, intent: ParsedIntent, profile_config: ProfileConfig
    ) -> dict[str, Any]:
        """Handle agent-related intents."""
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

            # Extract entities
            instruction = intent.entities.get("instruction", "handle this")
            issue_num = intent.entities.get("issue_number")
            pr_num = intent.entities.get("pr_number")
            provider = intent.entities.get("provider", "copilot")

            target_type = None
            target_ref = None
            if issue_num:
                target_type = "issue"
                target_ref = f"#{issue_num}"
            elif pr_num:
                target_type = "pr"
                target_ref = f"#{pr_num}"

            # Create task (user_id would come from context in real implementation)
            result = self._agent_service.delegate(
                user_id="default-user",  # Placeholder
                instruction=instruction,
                provider=provider,
                target_type=target_type,
                target_ref=target_ref,
            )

            spoken_text = result.get("spoken_text", "Agent task created.")
            spoken_text = profile_config.truncate_spoken_text(spoken_text)

            return {
                "status": "ok",
                "intent": intent.to_dict(),
                "spoken_text": spoken_text,
            }

        elif intent.name == "agent.status":
            if not self._agent_service:
                spoken_text = "Agent service not available."
            else:
                # Get status (user_id would come from context in real implementation)
                result = self._agent_service.get_status(user_id="default-user")
                spoken_text = result.get("spoken_text", "No agent tasks.")

            spoken_text = profile_config.truncate_spoken_text(spoken_text)

            return {
                "status": "ok",
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
        idempotency_key: str | None,
    ) -> dict[str, Any]:
        """Handle pr.request_review with full policy evaluation, rate limiting, and audit logging.

        Args:
            intent: The parsed pr.request_review intent
            user_id: User identifier for policy evaluation
            idempotency_key: Optional idempotency key

        Returns:
            Response dict with status, spoken_text, and optional pending_action
        """
        from handsfree.db.action_logs import write_action_log
        from handsfree.db.pending_actions import create_pending_action
        from handsfree.policy import PolicyDecision, evaluate_action_policy
        from handsfree.rate_limit import check_rate_limit

        # Extract entities
        reviewers = intent.entities.get("reviewers", [])
        pr_number = intent.entities.get("pr_number")
        repo = intent.entities.get("repo", "default/repo")

        # Validate required fields
        if not pr_number:
            return {
                "status": "error",
                "intent": intent.to_dict(),
                "spoken_text": (
                    "Please specify a PR number, for example: "
                    "'request review from alice on PR 123'."
                ),
            }

        if not reviewers:
            return {
                "status": "error",
                "intent": intent.to_dict(),
                "spoken_text": "Please specify at least one reviewer.",
            }

        # Check rate limit
        rate_limit_result = check_rate_limit(
            self.db_conn,
            user_id,
            "request_review",
            window_seconds=60,
            max_requests=10,
        )

        if not rate_limit_result.allowed:
            # Write audit log for rate limit denial
            try:
                write_action_log(
                    self.db_conn,
                    user_id=user_id,
                    action_type="request_review",
                    ok=False,
                    target=f"{repo}#{pr_number}",
                    request={"reviewers": reviewers},
                    result={"error": "rate_limited", "message": rate_limit_result.reason},
                    idempotency_key=idempotency_key,
                )
            except ValueError:
                # Idempotency key already used - this is a retry
                pass

            return {
                "status": "error",
                "intent": intent.to_dict(),
                "spoken_text": f"Rate limit exceeded. {rate_limit_result.reason}",
            }

        # Evaluate policy
        policy_result = evaluate_action_policy(
            self.db_conn,
            user_id,
            repo,
            "request_review",
        )

        # Handle policy decisions
        if policy_result.decision == PolicyDecision.DENY:
            # Write audit log for policy denial
            try:
                write_action_log(
                    self.db_conn,
                    user_id=user_id,
                    action_type="request_review",
                    ok=False,
                    target=f"{repo}#{pr_number}",
                    request={"reviewers": reviewers},
                    result={"error": "policy_denied", "message": policy_result.reason},
                    idempotency_key=idempotency_key,
                )
            except ValueError:
                # Idempotency key already used
                pass

            return {
                "status": "error",
                "intent": intent.to_dict(),
                "spoken_text": f"Action not allowed: {policy_result.reason}",
            }

        elif policy_result.decision == PolicyDecision.REQUIRE_CONFIRMATION:
            # Create pending action in database
            reviewers_str = ", ".join(reviewers)
            summary = f"Request review from {reviewers_str} on {repo}#{pr_number}"
            pending_action = create_pending_action(
                self.db_conn,
                user_id=user_id,
                summary=summary,
                action_type="request_review",
                action_payload={
                    "repo": repo,
                    "pr_number": pr_number,
                    "reviewers": reviewers,
                },
                expires_in_seconds=300,  # 5 minutes
            )

            # Write audit log for confirmation required
            write_action_log(
                self.db_conn,
                user_id=user_id,
                action_type="request_review",
                ok=True,
                target=f"{repo}#{pr_number}",
                request={"reviewers": reviewers},
                result={
                    "status": "needs_confirmation",
                    "token": pending_action.token,
                    "reason": policy_result.reason,
                },
                idempotency_key=idempotency_key,
            )

            return {
                "status": "needs_confirmation",
                "intent": intent.to_dict(),
                "spoken_text": f"{summary}. Say 'confirm' to proceed.",
                "pending_action": {
                    "token": pending_action.token,
                    "expires_at": pending_action.expires_at.isoformat(),
                    "summary": summary,
                },
            }

        # Policy allows the action - execute it directly
        target = f"{repo}#{pr_number}"

        # Check if live mode is enabled and token is available
        import logging

        from handsfree.github.auth import get_default_auth_provider

        logger = logging.getLogger(__name__)

        auth_provider = get_default_auth_provider()
        token = None
        if auth_provider.supports_live_mode():
            token = auth_provider.get_token(user_id)

        # Execute via GitHub API if live mode enabled and token available
        if token:
            import logging

            from handsfree.github.client import request_reviewers as github_request_reviewers

            logger = logging.getLogger(__name__)

            logger.info(
                "Executing request_review via GitHub API (live mode) for %s",
                target,
            )

            github_result = github_request_reviewers(
                repo=repo,
                pr_number=pr_number,
                reviewers=reviewers,
                token=token,
            )

            if github_result["ok"]:
                # Write audit log for successful execution
                write_action_log(
                    self.db_conn,
                    user_id=user_id,
                    action_type="request_review",
                    ok=True,
                    target=target,
                    request={"reviewers": reviewers},
                    result={
                        "status": "success",
                        "message": "Review requested (live mode)",
                        "github_response": github_result.get("response_data"),
                    },
                    idempotency_key=idempotency_key,
                )

                reviewers_str = ", ".join(reviewers)
                return {
                    "status": "ok",
                    "intent": intent.to_dict(),
                    "spoken_text": f"Review requested from {reviewers_str} on {target}.",
                }
            else:
                # GitHub API call failed
                write_action_log(
                    self.db_conn,
                    user_id=user_id,
                    action_type="request_review",
                    ok=False,
                    target=target,
                    request={"reviewers": reviewers},
                    result={
                        "status": "error",
                        "message": github_result["message"],
                        "status_code": github_result.get("status_code"),
                    },
                    idempotency_key=idempotency_key,
                )

                return {
                    "status": "error",
                    "intent": intent.to_dict(),
                    "spoken_text": f"Failed to request reviewers: {github_result['message']}",
                }
        else:
            # Fixture mode - simulate success
            logger.info(
                "Executing request_review in fixture mode (no live token) for %s",
                target,
            )

            write_action_log(
                self.db_conn,
                user_id=user_id,
                action_type="request_review",
                ok=True,
                target=target,
                request={"reviewers": reviewers},
                result={"status": "success", "message": "Review requested (fixture)"},
                idempotency_key=idempotency_key,
            )

            reviewers_str = ", ".join(reviewers)
            return {
                "status": "ok",
                "intent": intent.to_dict(),
                "spoken_text": f"Review requested from {reviewers_str} on {target}.",
            }

    def _handle_rerun_checks_with_policy(
        self,
        intent: ParsedIntent,
        user_id: str,
        idempotency_key: str | None,
    ) -> dict[str, Any]:
        """Handle checks.rerun with full policy evaluation, rate limiting, and audit logging.

        Args:
            intent: The parsed checks.rerun intent
            user_id: User identifier for policy evaluation
            idempotency_key: Optional idempotency key

        Returns:
            Response dict with status, spoken_text, and optional pending_action
        """
        from handsfree.db.action_logs import write_action_log
        from handsfree.db.pending_actions import create_pending_action
        from handsfree.policy import PolicyDecision, evaluate_action_policy
        from handsfree.rate_limit import check_rate_limit

        # Extract entities
        pr_number = intent.entities.get("pr_number")
        repo = intent.entities.get("repo", "default/repo")

        # Validate required fields
        if not pr_number:
            return {
                "status": "error",
                "intent": intent.to_dict(),
                "spoken_text": (
                    "Please specify a PR number, for example: 'rerun checks for PR 123'."
                ),
            }

        # Check rate limit
        rate_limit_result = check_rate_limit(
            self.db_conn,
            user_id,
            "rerun",
            window_seconds=60,
            max_requests=5,
        )

        if not rate_limit_result.allowed:
            # Write audit log for rate limit denial
            try:
                write_action_log(
                    self.db_conn,
                    user_id=user_id,
                    action_type="rerun",
                    ok=False,
                    target=f"{repo}#{pr_number}",
                    request={},
                    result={"error": "rate_limited", "message": rate_limit_result.reason},
                    idempotency_key=idempotency_key,
                )
            except ValueError:
                # Idempotency key already used - this is a retry
                pass

            return {
                "status": "error",
                "intent": intent.to_dict(),
                "spoken_text": f"Rate limit exceeded. {rate_limit_result.reason}",
            }

        # Evaluate policy
        policy_result = evaluate_action_policy(
            self.db_conn,
            user_id,
            repo,
            "rerun",
        )

        # Handle policy decisions
        if policy_result.decision == PolicyDecision.DENY:
            # Write audit log for policy denial
            try:
                write_action_log(
                    self.db_conn,
                    user_id=user_id,
                    action_type="rerun",
                    ok=False,
                    target=f"{repo}#{pr_number}",
                    request={},
                    result={"error": "policy_denied", "message": policy_result.reason},
                    idempotency_key=idempotency_key,
                )
            except ValueError:
                # Idempotency key already used
                pass

            return {
                "status": "error",
                "intent": intent.to_dict(),
                "spoken_text": f"Action not allowed: {policy_result.reason}",
            }

        elif policy_result.decision == PolicyDecision.REQUIRE_CONFIRMATION:
            # Create pending action in database
            summary = f"Re-run checks on {repo}#{pr_number}"
            pending_action = create_pending_action(
                self.db_conn,
                user_id=user_id,
                summary=summary,
                action_type="rerun_checks",
                action_payload={
                    "repo": repo,
                    "pr_number": pr_number,
                },
                expires_in_seconds=300,  # 5 minutes
            )

            # Write audit log for confirmation required
            write_action_log(
                self.db_conn,
                user_id=user_id,
                action_type="rerun",
                ok=True,
                target=f"{repo}#{pr_number}",
                request={},
                result={
                    "status": "needs_confirmation",
                    "token": pending_action.token,
                    "reason": policy_result.reason,
                },
                idempotency_key=idempotency_key,
            )

            return {
                "status": "needs_confirmation",
                "intent": intent.to_dict(),
                "spoken_text": f"{summary}. Say 'confirm' to proceed.",
                "pending_action": {
                    "token": pending_action.token,
                    "expires_at": pending_action.expires_at.isoformat(),
                    "summary": summary,
                },
            }

        # Policy allows the action - execute it directly
        target = f"{repo}#{pr_number}"

        # Check if live mode is enabled and token is available
        import logging

        from handsfree.github.auth import get_default_auth_provider

        logger = logging.getLogger(__name__)

        auth_provider = get_default_auth_provider()
        token = None
        if auth_provider.supports_live_mode():
            token = auth_provider.get_token(user_id)

        # Execute via GitHub API if live mode enabled and token available
        if token:
            from handsfree.github.client import rerun_workflow

            logger.info(
                "Executing rerun_checks via GitHub API (live mode) for %s",
                target,
            )

            github_result = rerun_workflow(
                repo=repo,
                pr_number=pr_number,
                token=token,
            )

            if github_result["ok"]:
                # Write audit log for successful execution
                write_action_log(
                    self.db_conn,
                    user_id=user_id,
                    action_type="rerun",
                    ok=True,
                    target=target,
                    request={},
                    result={
                        "status": "success",
                        "message": "Checks re-run (live mode)",
                        "run_id": github_result.get("run_id"),
                    },
                    idempotency_key=idempotency_key,
                )

                return {
                    "status": "ok",
                    "intent": intent.to_dict(),
                    "spoken_text": f"Checks re-run on {target}.",
                }
            else:
                # GitHub API call failed
                write_action_log(
                    self.db_conn,
                    user_id=user_id,
                    action_type="rerun",
                    ok=False,
                    target=target,
                    request={},
                    result={
                        "status": "error",
                        "message": github_result["message"],
                        "status_code": github_result.get("status_code"),
                    },
                    idempotency_key=idempotency_key,
                )

                return {
                    "status": "error",
                    "intent": intent.to_dict(),
                    "spoken_text": f"Failed to rerun checks: {github_result['message']}",
                }
        else:
            # Fixture mode - simulate success
            logger.info(
                "Executing rerun_checks in fixture mode (no live token) for %s",
                target,
            )

            write_action_log(
                self.db_conn,
                user_id=user_id,
                action_type="rerun",
                ok=True,
                target=target,
                request={},
                result={"status": "success", "message": "Checks re-run (fixture)"},
                idempotency_key=idempotency_key,
            )

            return {
                "status": "ok",
                "intent": intent.to_dict(),
                "spoken_text": f"Checks re-run on {target}.",
            }
