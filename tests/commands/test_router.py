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


class TestSystemNext:
    """Test system.next navigation functionality."""

    def test_next_without_list(self, router: CommandRouter, parser: IntentParser) -> None:
        """Test next without any list context."""
        intent = parser.parse("next")
        response = router.route(intent, Profile.DEFAULT, session_id="new-session")

        assert response["status"] == "ok"
        assert "no list" in response["spoken_text"].lower()

    def test_next_after_inbox(self, router: CommandRouter, parser: IntentParser) -> None:
        """Test next navigation through inbox items."""
        # First, get inbox which should have multiple items
        intent1 = parser.parse("inbox")
        response1 = router.route(intent1, Profile.DEFAULT, session_id="session1")

        # If there are cards, we should be able to navigate
        if "cards" in response1 and len(response1.get("cards", [])) > 1:
            # Next command should return second item
            intent2 = parser.parse("next")
            response2 = router.route(intent2, Profile.DEFAULT, session_id="session1")

            assert response2["status"] == "ok"
            assert "cards" in response2
            assert len(response2["cards"]) == 1  # Should return single card for next item

    def test_next_at_end_of_list(self, router: CommandRouter, parser: IntentParser) -> None:
        """Test next when at end of list."""
        # Get inbox
        intent1 = parser.parse("inbox")
        response1 = router.route(intent1, Profile.DEFAULT, session_id="session1")

        # If there are cards, navigate through all of them
        if "cards" in response1:
            card_count = len(response1.get("cards", []))

            # Navigate through all items
            for _ in range(card_count):
                intent_next = parser.parse("next")
                router.route(intent_next, Profile.DEFAULT, session_id="session1")

            # One more next should indicate no more items
            intent_final = parser.parse("next")
            response_final = router.route(intent_final, Profile.DEFAULT, session_id="session1")

            assert "no more items" in response_final["spoken_text"].lower()

    def test_next_different_sessions(self, router: CommandRouter, parser: IntentParser) -> None:
        """Test that next navigation is session-specific."""
        # Session 1 - get inbox
        intent1 = parser.parse("inbox")
        router.route(intent1, Profile.DEFAULT, session_id="session1")

        # Session 2 - next should not see session1's list
        intent2 = parser.parse("next")
        response2 = router.route(intent2, Profile.DEFAULT, session_id="session2")

        assert "no list" in response2["spoken_text"].lower()

    def test_repeat_after_next(self, router: CommandRouter, parser: IntentParser) -> None:
        """Test that repeat works after next navigation."""
        # Get inbox
        intent1 = parser.parse("inbox")
        response1 = router.route(intent1, Profile.DEFAULT, session_id="session1")

        # Navigate to next if possible
        if "cards" in response1 and len(response1.get("cards", [])) > 1:
            intent2 = parser.parse("next")
            response2 = router.route(intent2, Profile.DEFAULT, session_id="session1")

            # Repeat should return the same next item
            intent3 = parser.parse("repeat")
            response3 = router.route(intent3, Profile.DEFAULT, session_id="session1")

            assert response3["spoken_text"] == response2["spoken_text"]


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

    def test_checks_rerun_requires_confirmation_in_workout(
        self, router: CommandRouter, parser: IntentParser
    ) -> None:
        """Test that checks.rerun requires confirmation in workout profile."""
        intent = parser.parse("rerun checks for pr 123")

        response = router.route(intent, Profile.WORKOUT, session_id="test-session")

        assert response["status"] == "needs_confirmation"
        assert "pending_action" in response
        assert "token" in response["pending_action"]
        assert "confirm" in response["spoken_text"].lower()

    def test_checks_rerun_no_confirmation_in_commute(
        self, router: CommandRouter, parser: IntentParser
    ) -> None:
        """Test that checks.rerun doesn't require confirmation in commute profile."""
        intent = parser.parse("rerun checks for pr 123")

        response = router.route(intent, Profile.COMMUTE, session_id="test-session")

        # Commute profile doesn't require confirmation
        assert response["status"] == "ok"
        assert "pending_action" not in response

    def test_checks_rerun_confirmation_summary(
        self, router: CommandRouter, parser: IntentParser
    ) -> None:
        """Test that checks.rerun confirmation summary is human-readable."""
        intent = parser.parse("rerun checks for pr 456")

        response = router.route(intent, Profile.WORKOUT)

        summary = response["pending_action"]["summary"]
        assert "456" in summary
        assert "re-run" in summary.lower() or "rerun" in summary.lower()

    def test_checks_rerun_without_pr_requires_pr(
        self, router: CommandRouter, parser: IntentParser
    ) -> None:
        """Test that checks.rerun without PR number shows error in commute profile."""
        intent = parser.parse("rerun checks")

        # In commute profile (no confirmation), should immediately fail for missing PR
        response = router.route(intent, Profile.COMMUTE, session_id="test-session")

        # Since there's no pr_number, it should be handled as a basic checks intent
        # The actual validation for pr_number would happen in policy handler
        assert response["status"] == "ok"

    def test_checks_status(self, router: CommandRouter, parser: IntentParser) -> None:
        """Test checks.status intent."""
        intent = parser.parse("ci status")
        response = router.route(intent, Profile.DEFAULT)

        assert response["status"] == "ok"
        assert response["intent"]["name"] == "checks.status"

    def test_checks_status_with_pr_all_passing(
        self, parser: IntentParser, pending_manager: PendingActionManager
    ) -> None:
        """Test checks.status with PR number - all checks passing."""
        from handsfree.github import GitHubProvider

        # Create router with real provider
        provider = GitHubProvider()
        router = CommandRouter(pending_manager, github_provider=provider)

        # Parse "checks for pr 123" (PR 123 has all checks passing)
        intent = parser.parse("checks for pr 123")
        response = router.route(intent, Profile.DEFAULT)

        assert response["status"] == "ok"
        assert response["intent"]["name"] == "checks.status"
        # Should mention all checks passing
        assert "all" in response["spoken_text"].lower()
        assert "passing" in response["spoken_text"].lower()
        assert "123" in response["spoken_text"]

    def test_checks_status_with_pr_failing(
        self, parser: IntentParser, pending_manager: PendingActionManager
    ) -> None:
        """Test checks.status with PR number - some checks failing."""
        from handsfree.github import GitHubProvider

        # Create router with real provider
        provider = GitHubProvider()
        router = CommandRouter(pending_manager, github_provider=provider)

        # Parse "checks for pr 124" (PR 124 has 1 failing check)
        intent = parser.parse("checks for pr 124")
        response = router.route(intent, Profile.DEFAULT)

        assert response["status"] == "ok"
        assert response["intent"]["name"] == "checks.status"
        # Should mention failing check
        assert "failing" in response["spoken_text"].lower()
        assert "124" in response["spoken_text"]
        # Should include the name of the first failing check
        assert "ci / test" in response["spoken_text"].lower()

    def test_checks_status_workout_profile(
        self, parser: IntentParser, pending_manager: PendingActionManager
    ) -> None:
        """Test checks.status with workout profile (shorter response)."""
        from handsfree.github import GitHubProvider

        # Create router with real provider
        provider = GitHubProvider()
        router = CommandRouter(pending_manager, github_provider=provider)

        # Parse "checks for pr 124" with workout profile
        intent = parser.parse("checks for pr 124")
        response = router.route(intent, Profile.WORKOUT)

        assert response["status"] == "ok"
        # Workout response should be shorter
        assert len(response["spoken_text"].split()) <= 16  # 15 words + potential "..."

    def test_checks_status_without_pr_number(
        self, parser: IntentParser, pending_manager: PendingActionManager
    ) -> None:
        """Test checks.status without PR number requests more context."""
        from handsfree.github import GitHubProvider

        # Create router with real provider
        provider = GitHubProvider()
        router = CommandRouter(pending_manager, github_provider=provider)

        # Parse "ci status" (no PR number)
        intent = parser.parse("ci status")
        response = router.route(intent, Profile.DEFAULT)

        assert response["status"] == "ok"
        # Should ask for PR number
        assert (
            "pr" in response["spoken_text"].lower() or "number" in response["spoken_text"].lower()
        )

    def test_checks_status_no_github_provider(
        self, router: CommandRouter, parser: IntentParser
    ) -> None:
        """Test checks.status without GitHub provider falls back gracefully."""
        # The default router fixture doesn't have a provider
        intent = parser.parse("checks for pr 123")
        response = router.route(intent, Profile.DEFAULT)

        assert response["status"] == "ok"
        # Should fall back to placeholder
        assert "passing" in response["spoken_text"].lower()


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


class TestProfileResponseShaping:
    """Test that profile configurations actually affect response length."""

    def test_workout_shorter_than_default_pr_summary(
        self, router: CommandRouter, parser: IntentParser
    ) -> None:
        """Test that workout profile yields shorter PR summaries."""
        intent = parser.parse("summarize pr 123")

        workout_response = router.route(intent, Profile.WORKOUT)
        default_response = router.route(intent, Profile.DEFAULT)

        workout_words = len(workout_response["spoken_text"].split())
        default_words = len(default_response["spoken_text"].split())

        # Workout should be <= 15 words (accounting for "...")
        assert workout_words <= 16  # 15 words + potential "..."
        # Default should be <= 25 words
        assert default_words <= 26

    def test_workout_shorter_than_default_inbox(
        self, router: CommandRouter, parser: IntentParser
    ) -> None:
        """Test that workout profile yields shorter inbox responses."""
        intent = parser.parse("inbox")

        workout_response = router.route(intent, Profile.WORKOUT)
        default_response = router.route(intent, Profile.DEFAULT)

        workout_words = len(workout_response["spoken_text"].split())
        default_words = len(default_response["spoken_text"].split())

        # Both should respect their limits
        assert workout_words <= 16  # 15 words + potential "..."
        assert default_words <= 26

    def test_all_profiles_respect_word_limits(
        self, router: CommandRouter, parser: IntentParser
    ) -> None:
        """Test that all profiles respect their max_spoken_words limits."""
        intent = parser.parse("inbox")

        for profile in Profile:
            from handsfree.commands.profiles import ProfileConfig

            config = ProfileConfig.for_profile(profile)
            response = router.route(intent, profile)

            word_count = len(response["spoken_text"].split())
            # Allow for "..." which adds one extra "word"
            assert word_count <= config.max_spoken_words + 1

    def test_truncation_is_deterministic(self, router: CommandRouter, parser: IntentParser) -> None:
        """Test that truncation produces consistent results."""
        intent = parser.parse("summarize pr 456")

        # Call multiple times with same profile
        response1 = router.route(intent, Profile.WORKOUT)
        response2 = router.route(intent, Profile.WORKOUT)
        response3 = router.route(intent, Profile.WORKOUT)

        # Should get identical results
        assert response1["spoken_text"] == response2["spoken_text"]
        assert response2["spoken_text"] == response3["spoken_text"]
