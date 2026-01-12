"""Command router and response composer."""

from typing import Any

from .intent_parser import ParsedIntent
from .pending_actions import PendingActionManager
from .profiles import Profile, ProfileConfig


class CommandRouter:
    """Route parsed intents to handlers and compose responses."""

    # Intents that require confirmation (side effects)
    SIDE_EFFECT_INTENTS = {
        "pr.request_review",
        "pr.merge",
        "agent.delegate",
    }

    def __init__(self, pending_actions: PendingActionManager) -> None:
        """Initialize the router.

        Args:
            pending_actions: Manager for pending confirmation actions
        """
        self.pending_actions = pending_actions
        # Session state for system.repeat - maps session_id to last response
        self._last_responses: dict[str, dict[str, Any]] = {}

    def route(
        self,
        intent: ParsedIntent,
        profile: Profile,
        session_id: str | None = None,
    ) -> dict[str, Any]:
        """Route an intent to appropriate handler and compose response.

        Args:
            intent: Parsed intent from the parser
            profile: User's current profile
            session_id: Optional session identifier for repeat functionality

        Returns:
            Dictionary conforming to CommandResponse schema
        """
        profile_config = ProfileConfig.for_profile(profile)

        # Handle system commands
        if intent.name == "system.repeat":
            return self._handle_repeat(session_id, profile_config, intent)
        elif intent.name == "system.confirm":
            return self._handle_confirm(intent, profile_config)
        elif intent.name == "system.cancel":
            return self._handle_cancel(intent, profile_config)
        elif intent.name == "system.set_profile":
            return self._handle_set_profile(intent, profile_config)

        # Check if this is a side-effect intent requiring confirmation
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
        return "I can execute this action."

    def _handle_repeat(
        self,
        session_id: str | None,
        profile_config: ProfileConfig,
        intent: ParsedIntent,
    ) -> dict[str, Any]:
        """Handle system.repeat to replay last response."""
        if not session_id or session_id not in self._last_responses:
            return {
                "status": "ok",
                "intent": intent.to_dict(),
                "spoken_text": "Nothing to repeat.",
            }

        # Return the last response for this session
        return self._last_responses[session_id]

    def _handle_confirm(
        self, intent: ParsedIntent, profile_config: ProfileConfig
    ) -> dict[str, Any]:
        """Handle system.confirm - execute pending action."""
        # In a real implementation, this would get the pending token from context
        # For now, return a placeholder
        return {
            "status": "ok",
            "intent": intent.to_dict(),
            "spoken_text": "Confirmation received. This will be implemented in the API endpoint.",
        }

    def _handle_cancel(self, intent: ParsedIntent, profile_config: ProfileConfig) -> dict[str, Any]:
        """Handle system.cancel - cancel pending action."""
        return {
            "status": "ok",
            "intent": intent.to_dict(),
            "spoken_text": "Cancelled.",
        }

    def _handle_set_profile(
        self, intent: ParsedIntent, profile_config: ProfileConfig
    ) -> dict[str, Any]:
        """Handle system.set_profile to change user profile."""
        profile_name = intent.entities.get("profile", "default")
        return {
            "status": "ok",
            "intent": intent.to_dict(),
            "spoken_text": f"Switched to {profile_name} mode.",
        }

    def _handle_inbox_list(
        self, intent: ParsedIntent, profile_config: ProfileConfig
    ) -> dict[str, Any]:
        """Handle inbox.list intent."""
        # Stub: in PR-005 this will integrate with GitHub
        spoken_text = "You have 2 PRs waiting for review and 1 failing check."
        if profile_config.profile == Profile.WORKOUT:
            spoken_text = "2 PRs, 1 failing."

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

        return {
            "status": "ok",
            "intent": intent.to_dict(),
            "spoken_text": spoken_text,
        }

    def _handle_checks_intent(
        self, intent: ParsedIntent, profile_config: ProfileConfig
    ) -> dict[str, Any]:
        """Handle checks-related intents."""
        spoken_text = "All checks passing."
        if profile_config.profile == Profile.WORKOUT:
            spoken_text = "Checks OK."

        return {
            "status": "ok",
            "intent": intent.to_dict(),
            "spoken_text": spoken_text,
        }

    def _handle_agent_intent(
        self, intent: ParsedIntent, profile_config: ProfileConfig
    ) -> dict[str, Any]:
        """Handle agent-related intents."""
        if intent.name == "agent.delegate":
            # Should have been caught by confirmation flow
            spoken_text = "Agent task created."
        elif intent.name == "agent.progress":
            spoken_text = "The agent is working on 1 task."
        else:
            spoken_text = "Agent intent recognized but not implemented."

        return {
            "status": "ok",
            "intent": intent.to_dict(),
            "spoken_text": spoken_text,
        }

    def _handle_unknown(
        self, intent: ParsedIntent, profile_config: ProfileConfig
    ) -> dict[str, Any]:
        """Handle unknown intents."""
        return {
            "status": "error",
            "intent": intent.to_dict(),
            "spoken_text": "I didn't catch that. Can you try again?",
        }
