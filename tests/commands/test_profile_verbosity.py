"""Tests for profile-based verbosity tuning (PR-027)."""

import pytest

from handsfree.commands.intent_parser import IntentParser
from handsfree.commands.pending_actions import PendingActionManager
from handsfree.commands.profiles import Profile, ProfileConfig
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


class TestProfileEnum:
    """Test that new profiles are available."""

    def test_focused_profile_exists(self) -> None:
        """Test that FOCUSED profile exists."""
        assert Profile.FOCUSED.value == "focused"

    def test_relaxed_profile_exists(self) -> None:
        """Test that RELAXED profile exists."""
        assert Profile.RELAXED.value == "relaxed"


class TestProfileVerbosityConfig:
    """Test verbosity configuration for each profile."""

    def test_workout_verbosity(self) -> None:
        """Test workout profile has ultra-brief verbosity."""
        config = ProfileConfig.for_profile(Profile.WORKOUT)
        assert config.max_summary_sentences == 2
        assert config.max_inbox_items == 3
        assert config.detail_level == "minimal"

    def test_commute_verbosity(self) -> None:
        """Test commute profile has brief verbosity."""
        config = ProfileConfig.for_profile(Profile.COMMUTE)
        assert config.max_summary_sentences == 3
        assert config.max_inbox_items == 5
        assert config.detail_level == "brief"

    def test_kitchen_verbosity(self) -> None:
        """Test kitchen profile has moderate verbosity."""
        config = ProfileConfig.for_profile(Profile.KITCHEN)
        assert config.max_summary_sentences == 4
        assert config.max_inbox_items == 5
        assert config.detail_level == "moderate"

    def test_focused_verbosity(self) -> None:
        """Test focused profile has minimal verbosity."""
        config = ProfileConfig.for_profile(Profile.FOCUSED)
        assert config.max_summary_sentences == 2
        assert config.max_inbox_items == 3
        assert config.detail_level == "minimal"

    def test_relaxed_verbosity(self) -> None:
        """Test relaxed profile has detailed verbosity."""
        config = ProfileConfig.for_profile(Profile.RELAXED)
        assert config.max_summary_sentences == 10
        assert config.max_inbox_items == 10
        assert config.detail_level == "detailed"

    def test_default_verbosity(self) -> None:
        """Test default profile has moderate verbosity."""
        config = ProfileConfig.for_profile(Profile.DEFAULT)
        assert config.max_summary_sentences == 4
        assert config.max_inbox_items == 5
        assert config.detail_level == "moderate"


class TestSummaryTruncation:
    """Test summary truncation based on profile."""

    def test_truncate_summary_within_limit(self) -> None:
        """Test that summary within limit is not truncated."""
        config = ProfileConfig.for_profile(Profile.WORKOUT)  # 2 sentences max
        text = "First sentence. Second sentence."
        result = config.truncate_summary(text)
        assert result == text

    def test_truncate_summary_exceeds_limit(self) -> None:
        """Test that summary exceeding limit is truncated."""
        config = ProfileConfig.for_profile(Profile.WORKOUT)  # 2 sentences max
        text = "First sentence. Second sentence. Third sentence. Fourth sentence."
        result = config.truncate_summary(text)
        # Should have first 2 sentences only
        assert "First sentence" in result
        assert "Second sentence" in result
        assert "Third sentence" not in result
        assert "Fourth sentence" not in result

    def test_truncate_summary_preserves_critical_info(self) -> None:
        """Test that critical information is always preserved."""
        config = ProfileConfig.for_profile(Profile.WORKOUT)  # 2 sentences max
        text = (
            "First normal sentence. Second normal sentence. "
            "Third sentence has SECURITY alert. Fourth normal sentence."
        )
        result = config.truncate_summary(text)
        # Should preserve security sentence even if truncating
        assert "SECURITY alert" in result

    def test_truncate_summary_empty_text(self) -> None:
        """Test that empty text is handled correctly."""
        config = ProfileConfig.for_profile(Profile.WORKOUT)
        assert config.truncate_summary("") == ""


class TestInboxFiltering:
    """Test inbox item filtering based on profile."""

    def test_filter_inbox_within_limit(self) -> None:
        """Test that inbox within limit is not filtered."""
        config = ProfileConfig.for_profile(Profile.WORKOUT)  # 3 items max
        items = [{"title": "PR 1"}, {"title": "PR 2"}]
        result = config.filter_inbox_items(items)
        assert len(result) == 2

    def test_filter_inbox_exceeds_limit(self) -> None:
        """Test that inbox exceeding limit is filtered."""
        config = ProfileConfig.for_profile(Profile.WORKOUT)  # 3 items max
        items = [
            {"title": "PR 1"},
            {"title": "PR 2"},
            {"title": "PR 3"},
            {"title": "PR 4"},
            {"title": "PR 5"},
        ]
        result = config.filter_inbox_items(items)
        assert len(result) == 3

    def test_filter_inbox_focused_prioritizes_actionable(self) -> None:
        """Test that FOCUSED profile prioritizes actionable items."""
        config = ProfileConfig.for_profile(Profile.FOCUSED)  # 3 items max
        items = [
            {"title": "Informational PR 1", "requested_reviewer": False},
            {"title": "Review request PR 2", "requested_reviewer": True},
            {"title": "Informational PR 3", "requested_reviewer": False},
            {"title": "Assigned PR 4", "assignee": True, "requested_reviewer": False},
            {"title": "Informational PR 5", "requested_reviewer": False},
        ]
        result = config.filter_inbox_items(items)
        # Should get actionable items first
        assert len(result) == 3
        assert result[0]["title"] == "Review request PR 2"
        assert result[1]["title"] == "Assigned PR 4"

    def test_filter_inbox_empty_list(self) -> None:
        """Test that empty list is handled correctly."""
        config = ProfileConfig.for_profile(Profile.WORKOUT)
        assert config.filter_inbox_items([]) == []


class TestPrSummarizeVerbosity:
    """Test pr.summarize with different profiles."""

    def test_pr_summarize_workout_brief(self, router: CommandRouter, parser: IntentParser) -> None:
        """Test that pr.summarize with workout profile returns brief summary."""
        intent = parser.parse("summarize pr 123")
        response = router.route(intent, Profile.WORKOUT, session_id="test-session")

        assert response["status"] == "ok"
        spoken_text = response["spoken_text"]
        # Workout profile should be very brief
        word_count = len(spoken_text.split())
        assert word_count <= 15  # max_spoken_words for WORKOUT

    def test_pr_summarize_relaxed_detailed(
        self, router: CommandRouter, parser: IntentParser
    ) -> None:
        """Test that pr.summarize with relaxed profile returns detailed summary."""
        intent = parser.parse("summarize pr 123")
        response = router.route(intent, Profile.RELAXED, session_id="test-session")

        assert response["status"] == "ok"
        spoken_text = response["spoken_text"]
        # Relaxed profile should be more detailed
        # Should have multiple sentences with full context
        assert len(spoken_text) > 50  # Significantly longer than workout

    def test_pr_summarize_focused_actionable(
        self, router: CommandRouter, parser: IntentParser
    ) -> None:
        """Test that pr.summarize with focused profile is brief and actionable."""
        intent = parser.parse("summarize pr 123")
        response = router.route(intent, Profile.FOCUSED, session_id="test-session")

        assert response["status"] == "ok"
        spoken_text = response["spoken_text"]
        # Focused profile should be brief
        word_count = len(spoken_text.split())
        assert word_count <= 20  # max_spoken_words for FOCUSED

    def test_pr_summarize_default_unchanged(
        self, router: CommandRouter, parser: IntentParser
    ) -> None:
        """Test that pr.summarize with default profile maintains original behavior."""
        intent = parser.parse("summarize pr 123")
        response = router.route(intent, Profile.DEFAULT, session_id="test-session")

        assert response["status"] == "ok"
        assert "spoken_text" in response
        # Default behavior should be moderate
        spoken_text = response["spoken_text"]
        assert len(spoken_text) > 0


class TestInboxListVerbosity:
    """Test inbox.list with different profiles."""

    def test_inbox_list_workout_brief(self, router: CommandRouter, parser: IntentParser) -> None:
        """Test that inbox.list with workout profile returns brief summary."""
        intent = parser.parse("inbox")
        response = router.route(intent, Profile.WORKOUT, session_id="test-session")

        assert response["status"] == "ok"
        spoken_text = response["spoken_text"]
        # Workout profile should be very brief
        assert len(spoken_text) < 30  # Very short
        # Should contain numbers
        assert any(char.isdigit() for char in spoken_text)

    def test_inbox_list_relaxed_detailed(
        self, router: CommandRouter, parser: IntentParser
    ) -> None:
        """Test that inbox.list with relaxed profile returns detailed summary."""
        intent = parser.parse("inbox")
        response = router.route(intent, Profile.RELAXED, session_id="test-session")

        assert response["status"] == "ok"
        spoken_text = response["spoken_text"]
        # Relaxed profile should be more detailed
        assert len(spoken_text) > 50  # Much longer
        # Should contain full context
        assert "pull request" in spoken_text.lower() or "pr" in spoken_text.lower()

    def test_inbox_list_focused_actionable(
        self, router: CommandRouter, parser: IntentParser
    ) -> None:
        """Test that inbox.list with focused profile prioritizes actionable items."""
        intent = parser.parse("inbox")
        response = router.route(intent, Profile.FOCUSED, session_id="test-session")

        assert response["status"] == "ok"
        spoken_text = response["spoken_text"]
        # Focused profile should mention actionable items
        assert "actionable" in spoken_text.lower() or "pr" in spoken_text.lower()

    def test_inbox_list_default_unchanged(
        self, router: CommandRouter, parser: IntentParser
    ) -> None:
        """Test that inbox.list with default profile maintains original behavior."""
        intent = parser.parse("inbox")
        response = router.route(intent, Profile.DEFAULT, session_id="test-session")

        assert response["status"] == "ok"
        assert "spoken_text" in response
        # Default should return moderate detail
        spoken_text = response["spoken_text"]
        assert len(spoken_text) > 0


class TestCriticalInfoPreservation:
    """Test that critical information is preserved regardless of profile."""

    def test_security_alert_preserved_in_workout(self) -> None:
        """Test that security alerts are preserved even in workout profile."""
        config = ProfileConfig.for_profile(Profile.WORKOUT)
        text = "Normal sentence. Another sentence. SECURITY ALERT: vulnerability found. Final sentence."
        result = config.truncate_summary(text)
        # Security alert should be present
        assert "SECURITY ALERT" in result or "vulnerability" in result

    def test_failing_check_preserved_in_focused(self) -> None:
        """Test that failing check info is preserved in focused profile."""
        config = ProfileConfig.for_profile(Profile.FOCUSED)
        text = "Normal info. Another detail. Check is FAILING. More info."
        result = config.truncate_summary(text)
        # Failing check should be mentioned
        assert "FAILING" in result


class TestProfileComparison:
    """Test that profiles have the expected relative verbosity levels."""

    def test_workout_more_brief_than_default(self) -> None:
        """Test that workout profile is more brief than default."""
        workout = ProfileConfig.for_profile(Profile.WORKOUT)
        default = ProfileConfig.for_profile(Profile.DEFAULT)

        assert workout.max_summary_sentences < default.max_summary_sentences
        assert workout.max_inbox_items <= default.max_inbox_items
        assert workout.max_spoken_words < default.max_spoken_words

    def test_relaxed_more_detailed_than_default(self) -> None:
        """Test that relaxed profile is more detailed than default."""
        relaxed = ProfileConfig.for_profile(Profile.RELAXED)
        default = ProfileConfig.for_profile(Profile.DEFAULT)

        assert relaxed.max_summary_sentences > default.max_summary_sentences
        assert relaxed.max_inbox_items >= default.max_inbox_items
        assert relaxed.max_spoken_words > default.max_spoken_words

    def test_verbosity_ordering(self) -> None:
        """Test that profiles are ordered by verbosity level."""
        workout = ProfileConfig.for_profile(Profile.WORKOUT)
        focused = ProfileConfig.for_profile(Profile.FOCUSED)
        commute = ProfileConfig.for_profile(Profile.COMMUTE)
        default = ProfileConfig.for_profile(Profile.DEFAULT)
        kitchen = ProfileConfig.for_profile(Profile.KITCHEN)
        relaxed = ProfileConfig.for_profile(Profile.RELAXED)

        # Check that verbosity increases as expected
        verbosity_order = [
            workout.max_spoken_words,
            focused.max_spoken_words,
            default.max_spoken_words,
            commute.max_spoken_words,
            kitchen.max_spoken_words,
            relaxed.max_spoken_words,
        ]

        # Workout and focused should be shortest
        assert workout.max_spoken_words <= focused.max_spoken_words
        # Relaxed should be longest
        assert relaxed.max_spoken_words == max(verbosity_order)
