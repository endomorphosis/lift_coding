"""Tests for command router."""

import pytest

from handsfree.commands.intent_parser import IntentParser
from handsfree.commands.pending_actions import PendingActionManager
from handsfree.commands.profiles import Profile
from handsfree.commands.router import CommandRouter


@pytest.fixture
def pending_manager() -> PendingActionManager:
    """Create a pending actions manager."""
    return PendingActionManager()


@pytest.fixture
def router(pending_manager: PendingActionManager) -> CommandRouter:
    """Create a command router."""
    return CommandRouter(pending_manager)


@pytest.fixture
def parser() -> IntentParser:
    """Create an intent parser."""
    return IntentParser()


class TestConfirmationFlow:
    """Test confirmation flow for side-effect intents."""

    def test_side_effect_requires_confirmation_in_workout(
        self, router: CommandRouter, parser: IntentParser
    ) -> None:
        """Test that side effects require confirmation in workout profile."""
        intent = parser.parse("request review from alice on pr 123")

        response = router.route(intent, Profile.WORKOUT, session_id="test-session")

        assert response["status"] == "needs_confirmation"
        assert "pending_action" in response
        assert "token" in response["pending_action"]
        assert "confirm" in response["spoken_text"].lower()

    def test_side_effect_no_confirmation_in_commute(
        self, router: CommandRouter, parser: IntentParser
    ) -> None:
        """Test that side effects don't require confirmation in commute profile."""
        intent = parser.parse("request review from alice on pr 123")

        response = router.route(intent, Profile.COMMUTE, session_id="test-session")

        # Commute profile doesn't require confirmation
        # But since real implementation isn't there, we get OK status
        assert response["status"] == "ok"
        assert "pending_action" not in response

    def test_confirmation_summary_format(self, router: CommandRouter, parser: IntentParser) -> None:
        """Test that confirmation summary is human-readable."""
        intent = parser.parse("request review from bob and alice on pr 456")

        response = router.route(intent, Profile.WORKOUT)

        summary = response["pending_action"]["summary"]
        assert "bob" in summary.lower()
        assert "alice" in summary.lower()
        assert "456" in summary


class TestSystemRepeat:
    """Test system.repeat functionality."""

    def test_repeat_with_history(self, router: CommandRouter, parser: IntentParser) -> None:
        """Test repeat returns last response."""
        # First command
        intent1 = parser.parse("inbox")
        response1 = router.route(intent1, Profile.DEFAULT, session_id="session1")
        original_text = response1["spoken_text"]

        # Repeat command
        intent2 = parser.parse("repeat")
        response2 = router.route(intent2, Profile.DEFAULT, session_id="session1")

        assert response2["spoken_text"] == original_text

    def test_repeat_without_history(self, router: CommandRouter, parser: IntentParser) -> None:
        """Test repeat without previous command."""
        intent = parser.parse("repeat")
        response = router.route(intent, Profile.DEFAULT, session_id="new-session")

        assert "nothing to repeat" in response["spoken_text"].lower()

    def test_repeat_different_sessions(self, router: CommandRouter, parser: IntentParser) -> None:
        """Test that repeat is session-specific."""
        # Session 1
        intent1 = parser.parse("inbox")
        router.route(intent1, Profile.DEFAULT, session_id="session1")

        # Session 2 - should not see session1's history
        intent2 = parser.parse("repeat")
        response = router.route(intent2, Profile.DEFAULT, session_id="session2")

        assert "nothing to repeat" in response["spoken_text"].lower()


class TestSystemCommands:
    """Test system command handling."""

    def test_confirm(self, router: CommandRouter, parser: IntentParser) -> None:
        """Test system.confirm command."""
        intent = parser.parse("confirm")
        response = router.route(intent, Profile.DEFAULT)

        assert response["status"] == "ok"
        assert response["intent"]["name"] == "system.confirm"

    def test_cancel(self, router: CommandRouter, parser: IntentParser) -> None:
        """Test system.cancel command."""
        intent = parser.parse("cancel")
        response = router.route(intent, Profile.DEFAULT)

        assert response["status"] == "ok"
        assert "cancelled" in response["spoken_text"].lower()

    def test_set_profile(self, router: CommandRouter, parser: IntentParser) -> None:
        """Test system.set_profile command."""
        intent = parser.parse("workout mode")
        response = router.route(intent, Profile.DEFAULT)

        assert response["status"] == "ok"
        assert "workout" in response["spoken_text"].lower()


class TestInboxIntent:
    """Test inbox.list intent routing."""

    def test_inbox_list_default_profile(self, router: CommandRouter, parser: IntentParser) -> None:
        """Test inbox list with default profile."""
        intent = parser.parse("inbox")
        response = router.route(intent, Profile.DEFAULT)

        assert response["status"] == "ok"
        assert response["intent"]["name"] == "inbox.list"
        assert len(response["spoken_text"]) > 0

    def test_inbox_list_workout_profile(self, router: CommandRouter, parser: IntentParser) -> None:
        """Test inbox list with workout profile (shorter response)."""
        intent = parser.parse("inbox")
        response = router.route(intent, Profile.WORKOUT)

        assert response["status"] == "ok"
        # Workout profile should have shorter response
        workout_text = response["spoken_text"]

        # Compare with default profile
        response_default = router.route(intent, Profile.DEFAULT)
        default_text = response_default["spoken_text"]

        # Workout should be shorter or equal
        assert len(workout_text.split()) <= len(default_text.split())


class TestPRIntents:
    """Test PR intent routing."""

    def test_pr_summarize(self, router: CommandRouter, parser: IntentParser) -> None:
        """Test pr.summarize intent."""
        intent = parser.parse("summarize pr 123")
        response = router.route(intent, Profile.DEFAULT)

        assert response["status"] == "ok"
        assert response["intent"]["name"] == "pr.summarize"
        assert "123" in response["spoken_text"]

    def test_pr_summarize_workout_profile(
        self, router: CommandRouter, parser: IntentParser
    ) -> None:
        """Test pr.summarize with workout profile."""
        intent = parser.parse("summarize pr 456")
        response = router.route(intent, Profile.WORKOUT)

        # Workout should have shorter summary
        assert len(response["spoken_text"].split()) < 10


class TestChecksIntents:
    """Test checks intent routing."""

    def test_checks_status(self, router: CommandRouter, parser: IntentParser) -> None:
        """Test checks.status intent."""
        intent = parser.parse("ci status")
        response = router.route(intent, Profile.DEFAULT)

        assert response["status"] == "ok"
        assert response["intent"]["name"] == "checks.status"


class TestAgentIntents:
    """Test agent intent routing."""

    def test_agent_delegate(self, router: CommandRouter, parser: IntentParser) -> None:
        """Test agent.delegate intent."""
        intent = parser.parse("ask the agent to fix issue 918")

        # With workout profile (requires confirmation)
        response = router.route(intent, Profile.WORKOUT)

        assert response["status"] == "needs_confirmation"
        assert "pending_action" in response

    def test_agent_status(self, router: CommandRouter, parser: IntentParser) -> None:
        """Test agent.status intent."""
        intent = parser.parse("agent status")
        response = router.route(intent, Profile.DEFAULT)

        assert response["status"] == "ok"
        assert response["intent"]["name"] == "agent.status"


class TestUnknownIntent:
    """Test unknown intent handling."""

    def test_unknown_intent(self, router: CommandRouter, parser: IntentParser) -> None:
        """Test handling of unknown intents."""
        intent = parser.parse("random gibberish")
        response = router.route(intent, Profile.DEFAULT)

        assert response["status"] == "error"
        assert "didn't catch that" in response["spoken_text"].lower()


class TestResponseFormat:
    """Test response format compliance."""

    def test_response_has_required_fields(
        self, router: CommandRouter, parser: IntentParser
    ) -> None:
        """Test that responses have required fields."""
        intent = parser.parse("inbox")
        response = router.route(intent, Profile.DEFAULT)

        # Required fields per OpenAPI schema
        assert "status" in response
        assert "intent" in response
        assert "spoken_text" in response

        # Intent should be properly formatted
        assert "name" in response["intent"]
        assert "confidence" in response["intent"]
        assert "entities" in response["intent"]
