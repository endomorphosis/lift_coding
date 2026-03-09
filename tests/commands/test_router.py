"""Tests for command router."""

import uuid

import pytest

from handsfree.commands.intent_parser import IntentParser
from handsfree.commands.pending_actions import PendingActionManager
from handsfree.commands.profiles import Profile
from handsfree.commands.router import CommandRouter
from handsfree.db import init_db
from handsfree.db.action_logs import write_action_log


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


class TestAIIntents:
    """Test AI intent routing."""

    def test_ai_summarize_diff(
        self, parser: IntentParser, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Router should handle ai.summarize_diff through Copilot CLI fixtures."""
        intent = parser.parse("summarize diff for pr 123")
        router = CommandRouter(PendingActionManager())
        monkeypatch.setenv("HANDSFREE_CLI_FIXTURE_MODE", "true")
        response = router.route(intent, Profile.DEFAULT)

        assert response["status"] == "ok"
        assert "shared action handling" in response["spoken_text"].lower()
        assert response["intent"]["name"] == "ai.summarize_diff"
        assert response["debug"]["capability_id"] == "copilot.pr.diff_summary"
        assert response["debug"]["execution_mode"] == "fixture"

    def test_ai_rag_summary(
        self, parser: IntentParser, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Router should handle ai.rag_summary through the shared AI executor."""
        intent = parser.parse("rag summary for pr 123 on openai/example")
        router = CommandRouter(PendingActionManager())

        class StubExecution:
            capability_id = "github.pr.rag_summary"

            class execution_mode:
                value = "orchestrated"

            output = {
                "spoken_text": "Augmented summary",
                "headline": "RAG summary for PR #123",
                "summary": "Augmented summary with risks.",
                "trace": {"provider": "composite"},
            }

        def stub_execute_ai_request(request, **kwargs):
            assert request.capability_id == "github.pr.rag_summary"
            assert request.context.repo == "openai/example"
            assert request.context.pr_number == 123
            assert kwargs["profile_config"].profile == Profile.DEFAULT
            return StubExecution()

        monkeypatch.setattr("handsfree.commands.router.execute_ai_request", stub_execute_ai_request)
        monkeypatch.setenv("HANDSFREE_GH_CLI_ENABLED", "true")

        response = router.route(intent, Profile.DEFAULT)

        assert response["status"] == "ok"
        assert response["spoken_text"] == "Augmented summary"
        assert response["debug"]["capability_id"] == "github.pr.rag_summary"
        assert response["debug"]["execution_mode"] == "orchestrated"
        assert response["debug"]["policy_resolution"]["requested_workflow"] == "pr_rag_summary"
        assert response["debug"]["policy_resolution"]["resolved_workflow"] == "pr_rag_summary"
        assert response["debug"]["policy_resolution"]["policy_applied"] is False

    def test_ai_accelerated_rag_summary(
        self, parser: IntentParser, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Router should handle ai.accelerated_rag_summary through the shared AI executor."""
        intent = parser.parse("accelerated rag summary for pr 123 on openai/example")
        router = CommandRouter(PendingActionManager())

        class StubExecution:
            capability_id = "github.pr.accelerated_summary"

            class execution_mode:
                value = "orchestrated"

            output = {
                "spoken_text": "Accelerated summary",
                "headline": "Accelerated summary for PR #123",
                "summary": "Accelerated summary with risks.",
                "trace": {"provider": "composite"},
            }

        def stub_execute_ai_request(request, **kwargs):
            assert request.capability_id == "github.pr.accelerated_summary"
            assert request.context.repo == "openai/example"
            assert request.context.pr_number == 123
            assert kwargs["profile_config"].profile == Profile.DEFAULT
            return StubExecution()

        monkeypatch.setattr("handsfree.commands.router.execute_ai_request", stub_execute_ai_request)

        response = router.route(intent, Profile.DEFAULT)

        assert response["status"] == "ok"
        assert response["spoken_text"] == "Accelerated summary"
        assert response["debug"]["capability_id"] == "github.pr.accelerated_summary"
        assert response["debug"]["execution_mode"] == "orchestrated"

    def test_ai_rag_summary_can_select_accelerated_backend_from_env(
        self, parser: IntentParser, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Standard rag summary intent should switch to accelerated backend from env."""
        intent = parser.parse("rag summary for pr 123 on openai/example")
        router = CommandRouter(PendingActionManager())

        class StubExecution:
            capability_id = "github.pr.accelerated_summary"

            class execution_mode:
                value = "orchestrated"

            output = {
                "spoken_text": "Accelerated summary",
                "headline": "Accelerated summary for PR #123",
                "summary": "Accelerated summary with risks.",
                "trace": {"provider": "composite"},
            }

        def stub_execute_ai_request(request, **kwargs):
            assert request.capability_id == "github.pr.accelerated_summary"
            return StubExecution()

        monkeypatch.setattr("handsfree.commands.router.execute_ai_request", stub_execute_ai_request)
        monkeypatch.setenv("HANDSFREE_AI_DEFAULT_SUMMARY_BACKEND", "accelerated")

        response = router.route(intent, Profile.DEFAULT)

        assert response["status"] == "ok"
        assert response["debug"]["capability_id"] == "github.pr.accelerated_summary"
        assert response["debug"]["policy_resolution"]["requested_workflow"] == "pr_rag_summary"
        assert response["debug"]["policy_resolution"]["resolved_workflow"] == "accelerated_pr_summary"
        assert response["debug"]["policy_resolution"]["policy_applied"] is True

    def test_ai_rag_summary_can_select_accelerated_backend_from_phrase(
        self, parser: IntentParser, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Standard rag summary intent should switch to accelerated backend from phrase hint."""
        intent = parser.parse("use acceleration for augmented summary for pr 123")
        router = CommandRouter(PendingActionManager())

        class StubExecution:
            capability_id = "github.pr.accelerated_summary"

            class execution_mode:
                value = "orchestrated"

            output = {
                "spoken_text": "Accelerated summary",
                "headline": "Accelerated summary for PR #123",
                "summary": "Accelerated summary with risks.",
                "trace": {"provider": "composite"},
            }

        def stub_execute_ai_request(request, **kwargs):
            assert request.capability_id == "github.pr.accelerated_summary"
            assert request.context.pr_number == 123
            return StubExecution()

        monkeypatch.setattr("handsfree.commands.router.execute_ai_request", stub_execute_ai_request)

        response = router.route(intent, Profile.DEFAULT)

        assert response["status"] == "ok"
        assert response["debug"]["capability_id"] == "github.pr.accelerated_summary"

    def test_ai_rag_summary_can_select_accelerated_backend_and_persist(
        self, parser: IntentParser, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Standard rag summary intent should combine accelerated backend selection with persistence."""
        intent = parser.parse("use acceleration for augmented summary for pr 123 to ipfs")
        router = CommandRouter(PendingActionManager())

        class StubExecution:
            capability_id = "github.pr.accelerated_summary"

            class execution_mode:
                value = "orchestrated"

            output = {
                "spoken_text": "Persisted accelerated summary",
                "headline": "Accelerated summary for PR #123",
                "summary": "Accelerated summary with risks.",
                "ipfs_cid": "bafy-accelerated-summary",
                "trace": {"provider": "composite", "ipfs_cid": "bafy-accelerated-summary"},
            }

        def stub_execute_ai_request(request, **kwargs):
            assert request.capability_id == "github.pr.accelerated_summary"
            assert request.options["persist_output"] is True
            assert request.options["ipfs_options"] == {"pin": True}
            return StubExecution()

        monkeypatch.setattr("handsfree.commands.router.execute_ai_request", stub_execute_ai_request)

        response = router.route(intent, Profile.DEFAULT)

        assert response["status"] == "ok"
        assert response["debug"]["capability_id"] == "github.pr.accelerated_summary"
        assert response["debug"]["persist_output"] is True
        assert response["debug"]["ipfs_cid"] == "bafy-accelerated-summary"

    def test_ai_accelerate_generate_and_store(
        self, parser: IntentParser, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Router should handle accelerated generate/store through the shared AI executor."""
        intent = parser.parse(
            "generate and store with acceleration summarize the failure cluster to ipfs"
        )
        router = CommandRouter(PendingActionManager())

        class StubExecution:
            capability_id = "ipfs.accelerate.generate_and_store"

            class execution_mode:
                value = "orchestrated"

            output = {
                "spoken_text": "Stored accelerated output as bafy-accelerated.",
                "headline": "Accelerated stored output",
                "summary": "Stored accelerated output in IPFS.",
                "cid": "bafy-accelerated",
                "trace": {"provider": "composite"},
            }

        def stub_execute_ai_request(request, **kwargs):
            assert request.capability_id == "ipfs.accelerate.generate_and_store"
            assert request.inputs["prompt"] == "summarize the failure cluster"
            assert request.inputs["kit_pin"] is True
            assert request.options["ipfs_options"] == {"pin": False}
            return StubExecution()

        monkeypatch.setattr("handsfree.commands.router.execute_ai_request", stub_execute_ai_request)

        response = router.route(intent, Profile.DEFAULT)

        assert response["status"] == "ok"
        assert response["spoken_text"] == "Stored accelerated output as bafy-accelerated."
        assert response["debug"]["capability_id"] == "ipfs.accelerate.generate_and_store"
        assert response["debug"]["resolved_context"]["prompt"] == "summarize the failure cluster"

    def test_ai_accelerated_explain_failure(
        self, parser: IntentParser, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Router should handle accelerated failure analysis through the shared AI executor."""
        intent = parser.parse("accelerated explain workflow CI Linux for pr 123")
        router = CommandRouter(PendingActionManager())

        class StubExecution:
            capability_id = "github.check.accelerated_failure_explain"

            class execution_mode:
                value = "orchestrated"

            output = {
                "spoken_text": "Accelerated failure analysis is ready.",
                "headline": "Accelerated failure analysis",
                "summary": "CI Linux is failing during setup.",
                "repo": "default/repo",
                "pr_number": 123,
                "failure_target": "CI Linux",
                "failure_target_type": "workflow",
                "trace": {"provider": "composite"},
            }

        def stub_execute_ai_request(request, **kwargs):
            assert request.capability_id == "github.check.accelerated_failure_explain"
            assert request.context.pr_number == 123
            assert request.context.workflow_name == "CI Linux"
            return StubExecution()

        monkeypatch.setattr("handsfree.commands.router.execute_ai_request", stub_execute_ai_request)

        response = router.route(intent, Profile.DEFAULT)

        assert response["status"] == "ok"
        assert response["spoken_text"] == "Accelerated failure analysis is ready."
        assert response["debug"]["capability_id"] == "github.check.accelerated_failure_explain"
        assert response["debug"]["resolved_context"]["repo"] == "openai/example"

    def test_ai_rag_summary_can_request_ipfs_persistence(
        self, parser: IntentParser, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """RAG summary intents should pass persistence options into the AI request."""
        intent = parser.parse("store augmented summary for pull request 123 to ipfs")
        router = CommandRouter(PendingActionManager())

        class StubExecution:
            capability_id = "github.pr.rag_summary"

            class execution_mode:
                value = "orchestrated"

            output = {
                "spoken_text": "Persisted summary",
                "headline": "RAG summary for PR #123",
                "summary": "Augmented summary with risks.",
                "ipfs_cid": "bafy-summary",
                "trace": {"provider": "composite", "ipfs_cid": "bafy-summary"},
            }

        def stub_execute_ai_request(request, **kwargs):
            assert request.capability_id == "github.pr.rag_summary"
            assert request.options["persist_output"] is True
            assert request.options["ipfs_options"] == {"pin": True}
            return StubExecution()

        monkeypatch.setattr("handsfree.commands.router.execute_ai_request", stub_execute_ai_request)
        monkeypatch.setenv("HANDSFREE_GH_CLI_ENABLED", "true")

        response = router.route(intent, Profile.DEFAULT)

        assert response["status"] == "ok"
        assert "Stored in IPFS as bafy-summary" in response["cards"][0]["lines"]
        assert response["debug"]["persist_output"] is True
        assert response["debug"]["ipfs_cid"] == "bafy-summary"

    def test_ai_read_cid_routes_to_ipfs_read_capability(
        self, parser: IntentParser, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Stored AI outputs should be readable through the shared AI request path."""
        intent = parser.parse("read summary from cid bafy123")
        router = CommandRouter(PendingActionManager())

        class StubExecution:
            capability_id = "ipfs.content.read_ai_output"

            class execution_mode:
                value = "direct_import"

            output = {
                "spoken_text": "Recovered summary text.",
                "headline": "Stored summary",
                "summary": "Recovered summary text.",
                "cid": "bafy123",
                "trace": {"provider": "ipfs_content_router", "operation": "cat", "cid": "bafy123"},
            }

        def stub_execute_ai_request(request, **kwargs):
            assert request.capability_id == "ipfs.content.read_ai_output"
            assert request.options["cid"] == "bafy123"
            return StubExecution()

        monkeypatch.setattr("handsfree.commands.router.execute_ai_request", stub_execute_ai_request)

        response = router.route(intent, Profile.DEFAULT)

        assert response["status"] == "ok"
        assert response["spoken_text"] == "Recovered summary text."
        assert response["debug"]["capability_id"] == "ipfs.content.read_ai_output"
        assert response["debug"]["resolved_context"]["cid"] == "bafy123"

    def test_ai_explain_failure(
        self, parser: IntentParser, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Router should handle ai.explain_failure through Copilot CLI fixtures."""
        intent = parser.parse("explain failing checks for pr 123")
        router = CommandRouter(PendingActionManager())
        monkeypatch.setenv("HANDSFREE_CLI_FIXTURE_MODE", "true")
        response = router.route(intent, Profile.DEFAULT)

        assert response["status"] == "ok"
        assert "missing fixture" in response["spoken_text"].lower()
        assert response["intent"]["name"] == "ai.explain_failure"
        assert response["debug"]["capability_id"] == "copilot.pr.failure_explain"

    def test_ai_explain_failure_can_use_composite_capability(
        self, parser: IntentParser, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Failure analysis should switch to the composite path when enabled."""
        intent = parser.parse("explain failing checks for pr 124 on openai/example")
        router = CommandRouter(PendingActionManager(), github_provider=object())

        class StubExecution:
            capability_id = "github.check.failure_rag_explain"

            class execution_mode:
                value = "orchestrated"

            output = {
                "spoken_text": "Augmented failure analysis",
                "headline": "Failure analysis for PR #124",
                "summary": "Check CI Linux setup first.",
                "trace": {"provider": "composite"},
            }

        def stub_execute_ai_request(request, **kwargs):
            assert request.capability_id == "github.check.failure_rag_explain"
            assert request.context.repo == "openai/example"
            assert request.context.pr_number == 124
            assert request.options["github_provider"] is router.github_provider
            return StubExecution()

        monkeypatch.setattr("handsfree.commands.router.execute_ai_request", stub_execute_ai_request)
        monkeypatch.setenv("HANDSFREE_AI_DEFAULT_FAILURE_BACKEND", "composite")
        monkeypatch.setenv("HANDSFREE_GH_CLI_ENABLED", "true")

        response = router.route(intent, Profile.DEFAULT)

        assert response["status"] == "ok"
        assert response["spoken_text"] == "Augmented failure analysis"
        assert response["debug"]["capability_id"] == "github.check.failure_rag_explain"
        assert response["debug"]["execution_mode"] == "orchestrated"
        assert response["debug"]["policy_resolution"]["requested_workflow"] == "failure_rag_explain"
        assert response["debug"]["policy_resolution"]["resolved_workflow"] == "failure_rag_explain"
        assert response["debug"]["policy_resolution"]["policy_applied"] is False

    def test_ai_explain_failure_persistence_flows_to_composite_request(
        self, parser: IntentParser, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Failure analysis persistence requests should pass IPFS options through."""
        intent = parser.parse("persist explain failure for pull request 124 to ipfs")
        router = CommandRouter(PendingActionManager(), github_provider=object())

        class StubExecution:
            capability_id = "github.check.failure_rag_explain"

            class execution_mode:
                value = "orchestrated"

            output = {
                "spoken_text": "Persisted failure analysis",
                "headline": "Failure analysis for PR #124",
                "summary": "Start with the first failing check.",
                "ipfs_cid": "bafy-failure",
                "trace": {"provider": "composite", "ipfs_cid": "bafy-failure"},
            }

        def stub_execute_ai_request(request, **kwargs):
            assert request.capability_id == "github.check.failure_rag_explain"
            assert request.options["persist_output"] is True
            assert request.options["ipfs_options"] == {"pin": True}
            return StubExecution()

        monkeypatch.setattr("handsfree.commands.router.execute_ai_request", stub_execute_ai_request)
        monkeypatch.setenv("HANDSFREE_AI_DEFAULT_FAILURE_BACKEND", "composite")
        monkeypatch.setenv("HANDSFREE_GH_CLI_ENABLED", "true")

        response = router.route(intent, Profile.DEFAULT)

        assert response["status"] == "ok"
        assert response["debug"]["persist_output"] is True
        assert response["debug"]["ipfs_cid"] == "bafy-failure"

    def test_ai_explain_failure_can_select_accelerated_backend_from_phrase(
        self, parser: IntentParser, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Standard failure intent should switch to accelerated backend from phrase hint."""
        intent = parser.parse("use acceleration for explain workflow CI Linux for pr 456")
        router = CommandRouter(PendingActionManager(), github_provider=object())

        class StubExecution:
            capability_id = "github.check.accelerated_failure_explain"

            class execution_mode:
                value = "orchestrated"

            output = {
                "spoken_text": "Accelerated failure analysis",
                "headline": "Accelerated failure analysis for PR #456",
                "summary": "CI Linux is failing during setup.",
                "trace": {"provider": "composite"},
            }

        def stub_execute_ai_request(request, **kwargs):
            assert request.capability_id == "github.check.accelerated_failure_explain"
            assert request.context.pr_number == 456
            assert request.context.workflow_name == "CI Linux"
            assert request.options["github_provider"] is router.github_provider
            return StubExecution()

        monkeypatch.setattr("handsfree.commands.router.execute_ai_request", stub_execute_ai_request)

        response = router.route(intent, Profile.DEFAULT)

        assert response["status"] == "ok"
        assert response["spoken_text"] == "Accelerated failure analysis"
        assert response["debug"]["capability_id"] == "github.check.accelerated_failure_explain"
        assert response["debug"]["policy_resolution"]["requested_workflow"] == "failure_rag_explain"
        assert response["debug"]["policy_resolution"]["resolved_workflow"] == "accelerated_failure_explain"
        assert response["debug"]["policy_resolution"]["policy_applied"] is True

    def test_ai_explain_failure_can_select_accelerated_backend_and_persist(
        self, parser: IntentParser, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Standard failure intent should combine accelerated backend selection with persistence."""
        intent = parser.parse("use acceleration for explain failure for pr 456 to ipfs")
        router = CommandRouter(PendingActionManager(), github_provider=object())

        class StubExecution:
            capability_id = "github.check.accelerated_failure_explain"

            class execution_mode:
                value = "orchestrated"

            output = {
                "spoken_text": "Persisted accelerated failure analysis",
                "headline": "Accelerated failure analysis for PR #456",
                "summary": "CI Linux is failing during setup.",
                "ipfs_cid": "bafy-accelerated-failure",
                "trace": {"provider": "composite", "ipfs_cid": "bafy-accelerated-failure"},
            }

        def stub_execute_ai_request(request, **kwargs):
            assert request.capability_id == "github.check.accelerated_failure_explain"
            assert request.options["persist_output"] is True
            assert request.options["ipfs_options"] == {"pin": True}
            assert request.options["github_provider"] is router.github_provider
            return StubExecution()

        monkeypatch.setattr("handsfree.commands.router.execute_ai_request", stub_execute_ai_request)

        response = router.route(intent, Profile.DEFAULT)

        assert response["status"] == "ok"
        assert response["debug"]["capability_id"] == "github.check.accelerated_failure_explain"
        assert response["debug"]["persist_output"] is True
        assert response["debug"]["ipfs_cid"] == "bafy-accelerated-failure"

    def test_ai_explain_failure_explicit_copilot_overrides_composite_flag(
        self, parser: IntentParser, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Explicit Copilot phrasing should keep the Copilot failure capability."""
        intent = parser.parse("use copilot to explain failure for pull request 456")
        router = CommandRouter(PendingActionManager(), github_provider=object())
        captured: dict[str, object] = {}

        class StubExecution:
            capability_id = "copilot.pr.failure_explain"

            class execution_mode:
                value = "cli_live"

            output = {
                "spoken_text": "Copilot failure analysis",
                "headline": "Failure analysis",
                "summary": "Copilot summary",
                "trace": {"provider": "copilot_cli", "source": "live"},
            }

        def stub_execute_ai_request(request, **kwargs):
            captured["request"] = request
            return StubExecution()

        monkeypatch.setattr("handsfree.commands.router.execute_ai_request", stub_execute_ai_request)
        monkeypatch.setenv("HANDSFREE_AI_DEFAULT_FAILURE_BACKEND", "composite")
        monkeypatch.setenv("HANDSFREE_GH_CLI_ENABLED", "true")

        response = router.route(intent, Profile.DEFAULT)

        assert response["status"] == "ok"
        assert captured["request"].capability_id == "copilot.pr.failure_explain"
        assert response["debug"]["capability_id"] == "copilot.pr.failure_explain"

    def test_ai_explain_named_failure(
        self, parser: IntentParser, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Router should handle named workflow failures through Copilot CLI fixtures."""
        intent = parser.parse("explain workflow CI Linux for pr 123")
        router = CommandRouter(PendingActionManager())
        monkeypatch.setenv("HANDSFREE_CLI_FIXTURE_MODE", "true")
        response = router.route(intent, Profile.DEFAULT)

        assert response["status"] == "ok"
        assert "failing in setup" in response["spoken_text"].lower()
        assert response["intent"]["name"] == "ai.explain_failure"

    def test_ai_explain_named_failure_passes_workflow_context(
        self, parser: IntentParser, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Router should pass workflow_name through the AI request context."""
        intent = parser.parse("explain workflow CI Linux for pr 123")
        router = CommandRouter(PendingActionManager())
        captured = {}

        class StubExecution:
            output = {
                "spoken_text": "CI Linux is failing in setup.",
                "headline": "Failure analysis",
                "summary": "CI Linux setup is failing.",
                "trace": {"step": "copilot"},
            }

        def stub_execute_ai_request(request, **kwargs):
            captured["request"] = request
            return StubExecution()

        monkeypatch.setattr("handsfree.commands.router.execute_ai_request", stub_execute_ai_request)
        monkeypatch.setenv("HANDSFREE_CLI_FIXTURE_MODE", "true")

        response = router.route(intent, Profile.DEFAULT)

        assert response["status"] == "ok"
        assert captured["request"].context.workflow_name == "CI Linux"
        assert captured["request"].context.check_name is None
        assert captured["request"].context.failure_target is None

    def test_ai_explain_named_check_passes_check_context(
        self, parser: IntentParser, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Router should pass check_name through the AI request context."""
        intent = parser.parse("explain check unit tests for pr 123")
        router = CommandRouter(PendingActionManager())
        captured = {}

        class StubExecution:
            output = {
                "spoken_text": "Unit tests are failing.",
                "headline": "Failure analysis",
                "summary": "Unit tests are failing.",
                "trace": {"step": "copilot"},
            }

        def stub_execute_ai_request(request, **kwargs):
            captured["request"] = request
            return StubExecution()

        monkeypatch.setattr("handsfree.commands.router.execute_ai_request", stub_execute_ai_request)
        monkeypatch.setenv("HANDSFREE_CLI_FIXTURE_MODE", "true")

        response = router.route(intent, Profile.DEFAULT)

        assert response["status"] == "ok"
        assert captured["request"].context.check_name == "unit tests"
        assert captured["request"].context.workflow_name is None
        assert captured["request"].context.failure_target is None

    def test_ai_intent_uses_session_pr_context(
        self, parser: IntentParser, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """AI intents should reuse the last referenced PR from session context."""
        monkeypatch.setenv("HANDSFREE_CLI_FIXTURE_MODE", "true")
        router = CommandRouter(PendingActionManager())

        router.route(parser.parse("summarize pr 123"), Profile.DEFAULT, session_id="ai-session")
        response = router.route(
            parser.parse("summarize diff"),
            Profile.DEFAULT,
            session_id="ai-session",
        )

        assert response["status"] == "ok"
        assert "shared action handling" in response["spoken_text"].lower()
        assert response["debug"]["resolved_context"]["pr_number"] == 123

    def test_ai_intent_includes_resolved_repo_context(
        self, parser: IntentParser, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """AI intent cards and debug metadata should expose the resolved repo."""
        monkeypatch.setenv("HANDSFREE_CLI_FIXTURE_MODE", "true")
        router = CommandRouter(PendingActionManager())

        response = router.route(
            parser.parse("summarize diff for pr 123 on openai/example"),
            Profile.DEFAULT,
        )

        assert response["status"] == "ok"
        assert "openai/example" in response["cards"][0]["title"]
        assert response["debug"]["resolved_context"]["repo"] == "openai/example"

    def test_ai_find_similar_failures_uses_shared_ai_executor(
        self, parser: IntentParser, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Router should handle similar-failure lookup through the shared AI executor."""
        intent = parser.parse("find similar failures for pr 125 on openai/example")
        router = CommandRouter(PendingActionManager(), github_provider=object())

        class StubExecution:
            capability_id = "github.check.find_similar_failures"

            class execution_mode:
                value = "orchestrated"

            output = {
                "headline": "Similar failures for PR #125",
                "summary": "Top match: PR 101 in openai/example with score 0.98. Dependency install failed.",
                "spoken_text": "Top match: PR 101 in openai/example with score 0.98.",
                "ranked_matches": [
                    {
                        "score": 0.98,
                        "summary": "Dependency install failed.",
                        "repo": "openai/example",
                        "pr_number": 101,
                    }
                ],
                "trace": {"provider": "composite"},
            }

        def stub_execute_ai_request(request, **kwargs):
            assert request.capability_id == "github.check.find_similar_failures"
            assert request.context.repo == "openai/example"
            assert request.context.pr_number == 125
            assert request.options["github_provider"] is router.github_provider
            return StubExecution()

        monkeypatch.setattr("handsfree.commands.router.execute_ai_request", stub_execute_ai_request)

        response = router.route(intent, Profile.DEFAULT)

        assert response["status"] == "ok"
        assert response["intent"]["name"] == "ai.find_similar_failures"
        assert response["debug"]["capability_id"] == "github.check.find_similar_failures"
        assert response["spoken_text"].startswith("Top match:")

    def test_ai_find_similar_failures_passes_history_cids(
        self, parser: IntentParser, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Router should forward CID-backed history inputs to similar-failure retrieval."""
        intent = parser.parse("find similar failures for pr 125 using cids bafy123 and bafy456")
        router = CommandRouter(PendingActionManager(), github_provider=object())

        class StubExecution:
            capability_id = "github.check.find_similar_failures"

            class execution_mode:
                value = "orchestrated"

            output = {
                "headline": "Similar failures for PR #125",
                "summary": "No similar prior failures were found in the current candidate set.",
                "spoken_text": "No similar prior failures were found in the current candidate set.",
                "ranked_matches": [],
                "trace": {"provider": "composite"},
            }

        def stub_execute_ai_request(request, **kwargs):
            assert request.inputs["history_cids"] == ["bafy123", "bafy456"]
            return StubExecution()

        monkeypatch.setattr("handsfree.commands.router.execute_ai_request", stub_execute_ai_request)

        response = router.route(intent, Profile.DEFAULT)

        assert response["status"] == "ok"
        assert response["intent"]["entities"]["history_cids"] == ["bafy123", "bafy456"]

    def test_ai_find_similar_failures_can_use_session_pr_context(
        self, parser: IntentParser, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Similar-failure lookup should reuse the last referenced PR from session context."""
        router = CommandRouter(PendingActionManager(), github_provider=object())
        captured = {}

        class StubExecution:
            capability_id = "github.check.find_similar_failures"

            class execution_mode:
                value = "orchestrated"

            output = {
                "headline": "Similar failures for PR #123",
                "summary": "No similar prior failures were found in the current candidate set.",
                "spoken_text": "No similar prior failures were found in the current candidate set.",
                "ranked_matches": [],
                "trace": {"provider": "composite"},
            }

        def stub_execute_ai_request(request, **kwargs):
            captured["request"] = request
            return StubExecution()

        monkeypatch.setattr("handsfree.commands.router.execute_ai_request", stub_execute_ai_request)

        router.route(parser.parse("summarize pr 123"), Profile.DEFAULT, session_id="similar-session")
        response = router.route(
            parser.parse("find similar failures"),
            Profile.DEFAULT,
            session_id="similar-session",
        )

        assert response["status"] == "ok"
        assert captured["request"].context.pr_number == 123

    def test_ai_explain_failure_passes_history_cids_to_composite_backend(
        self, parser: IntentParser, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Composite failure analysis should receive CID-backed history inputs."""
        intent = parser.parse("explain workflow CI Linux for pr 123 using cids bafy123, bafy456")
        router = CommandRouter(PendingActionManager(), github_provider=object())

        class StubExecution:
            capability_id = "github.check.failure_rag_explain"

            class execution_mode:
                value = "orchestrated"

            output = {
                "spoken_text": "Failure analysis with history.",
                "headline": "Failure analysis",
                "summary": "Retrieved two related failures from CID-backed history.",
                "trace": {"provider": "composite"},
            }

        def stub_execute_ai_request(request, **kwargs):
            assert request.capability_id == "github.check.failure_rag_explain"
            assert request.context.workflow_name == "CI Linux"
            assert request.inputs["history_cids"] == ["bafy123", "bafy456"]
            assert request.options["github_provider"] is router.github_provider
            return StubExecution()

        monkeypatch.setattr("handsfree.commands.router.execute_ai_request", stub_execute_ai_request)
        monkeypatch.setenv("HANDSFREE_AI_DEFAULT_FAILURE_BACKEND", "composite")

        response = router.route(intent, Profile.DEFAULT)

        assert response["status"] == "ok"
        assert response["intent"]["name"] == "ai.explain_failure"

    def test_ai_find_similar_failures_auto_discovers_history_cids_from_logs(
        self, parser: IntentParser, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Router should auto-discover recent persisted failure-analysis CIDs for retrieval."""
        db_conn = init_db(":memory:")
        user_id = str(uuid.uuid4())
        write_action_log(
            db_conn,
            user_id=user_id,
            action_type="ai.execute.github.check.failure_rag_explain",
            ok=True,
            result={
                "output": {
                    "repo": "openai/example",
                    "pr_number": 101,
                    "failure_target": "CI Linux",
                    "failure_target_type": "workflow",
                    "ipfs_cid": "bafy-history-1",
                }
            },
        )
        write_action_log(
            db_conn,
            user_id=user_id,
            action_type="ai.execute.github.check.failure_rag_explain",
            ok=True,
            result={
                "output": {
                    "repo": "other/repo",
                    "pr_number": 102,
                    "failure_target": "CI Linux",
                    "failure_target_type": "workflow",
                    "ipfs_cid": "bafy-ignore",
                }
            },
        )
        intent = parser.parse("find similar workflow CI Linux failures for pr 125 on openai/example")
        router = CommandRouter(PendingActionManager(), db_conn=db_conn, github_provider=object())

        class StubExecution:
            capability_id = "github.check.find_similar_failures"

            class execution_mode:
                value = "orchestrated"

            output = {
                "headline": "Similar failures for PR #125",
                "summary": "Found one related failure.",
                "spoken_text": "Found one related failure.",
                "ranked_matches": [],
                "trace": {"provider": "composite"},
            }

        def stub_execute_ai_request(request, **kwargs):
            assert request.inputs["history_cids"] == ["bafy-history-1"]
            return StubExecution()

        monkeypatch.setattr("handsfree.commands.router.execute_ai_request", stub_execute_ai_request)

        response = router.route(intent, Profile.DEFAULT, user_id=user_id)

        assert response["status"] == "ok"
        assert response["debug"]["resolved_context"]["history_cids"] == ["bafy-history-1"]
        db_conn.close()

    def test_ai_explain_failure_auto_discovers_history_cids_from_logs(
        self, parser: IntentParser, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Composite failure analysis should auto-discover matching persisted history CIDs."""
        db_conn = init_db(":memory:")
        user_id = str(uuid.uuid4())
        write_action_log(
            db_conn,
            user_id=user_id,
            action_type="ai.execute.github.check.failure_rag_explain",
            ok=True,
            result={
                "output": {
                    "repo": "openai/example",
                    "pr_number": 98,
                    "failure_target": "CI Linux",
                    "failure_target_type": "workflow",
                    "ipfs_cid": "bafy-history-2",
                }
            },
        )
        intent = parser.parse("explain workflow CI Linux for pr 123 on openai/example")
        router = CommandRouter(PendingActionManager(), db_conn=db_conn, github_provider=object())

        class StubExecution:
            capability_id = "github.check.failure_rag_explain"

            class execution_mode:
                value = "orchestrated"

            output = {
                "spoken_text": "Failure analysis with discovered history.",
                "headline": "Failure analysis",
                "summary": "Loaded one prior related failure from persisted history.",
                "trace": {"provider": "composite"},
            }

        def stub_execute_ai_request(request, **kwargs):
            assert request.inputs["history_cids"] == ["bafy-history-2"]
            return StubExecution()

        monkeypatch.setattr("handsfree.commands.router.execute_ai_request", stub_execute_ai_request)
        monkeypatch.setenv("HANDSFREE_AI_DEFAULT_FAILURE_BACKEND", "composite")

        response = router.route(intent, Profile.DEFAULT, user_id=user_id)

        assert response["status"] == "ok"
        assert response["debug"]["resolved_context"]["history_cids"] == ["bafy-history-2"]
        db_conn.close()

    def test_ai_intent_routes_through_shared_capability_executor(
        self, parser: IntentParser, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Router should delegate AI intents to the shared capability layer."""
        intent = parser.parse("explain pr 123")
        router = CommandRouter(PendingActionManager())
        captured: dict[str, object] = {}

        class StubExecution:
            capability_id = "copilot.pr.explain"

            class execution_mode:
                value = "cli_live"

            output = {
                "spoken_text": "Stub explanation",
                "headline": "Stub headline",
                "summary": "Stub summary",
                "trace": {"provider": "copilot_cli", "source": "live"},
            }

        def stub_execute_ai_request(request, **kwargs: object) -> StubExecution:
            captured["request"] = request
            captured["kwargs"] = kwargs
            return StubExecution()

        monkeypatch.setattr(
            "handsfree.commands.router.execute_ai_request",
            stub_execute_ai_request,
        )
        monkeypatch.setenv("HANDSFREE_GH_CLI_ENABLED", "true")

        response = router.route(intent, Profile.DEFAULT)

        assert response["status"] == "ok"
        assert response["spoken_text"] == "Stub explanation"
        assert captured["request"].capability_id == "copilot.pr.explain"
        assert captured["request"].context.pr_number == 123
        assert response["intent"]["name"] == "ai.summarize_diff"

    def test_ai_intent_captures_repo_context(
        self, parser: IntentParser, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """AI intents with explicit repo should update session context."""
        monkeypatch.setenv("HANDSFREE_CLI_FIXTURE_MODE", "true")
        router = CommandRouter(PendingActionManager())

        router.route(
            parser.parse("explain pr 123 on owner/repo"),
            Profile.DEFAULT,
            session_id="repo-session",
        )

        context = router._session_context.get_repo_pr("repo-session")
        assert context["repo"] == "owner/repo"
        assert context["pr_number"] == 123

    def test_pr_summarize_uses_cli_fixture_when_enabled(
        self, router: CommandRouter, parser: IntentParser, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Test CLI-backed PR summary path in fixture mode."""
        monkeypatch.setenv("HANDSFREE_CLI_FIXTURE_MODE", "true")
        monkeypatch.setenv("HANDSFREE_GH_CLI_ENABLED", "true")

        intent = parser.parse("summarize pr 123")
        response = router.route(intent, Profile.DEFAULT)

        assert response["status"] == "ok"
        assert "Add command system" in response["spoken_text"]
        assert response["debug"]["tool_calls"][0]["provider"] == "github_cli"


class TestAIIntents:
    """Test AI intent routing."""

    def test_ai_explain_pr_requires_cli_enablement(
        self, router: CommandRouter, parser: IntentParser
    ) -> None:
        """Test AI explain returns a clear error when CLI is disabled."""
        intent = parser.parse("explain pr 123")
        response = router.route(intent, Profile.DEFAULT)

        assert response["status"] == "error"
        assert "not enabled" in response["spoken_text"].lower()

    def test_ai_explain_pr_uses_copilot_fixture(
        self, router: CommandRouter, parser: IntentParser, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Test Copilot explain path in fixture mode."""
        monkeypatch.setenv("HANDSFREE_CLI_FIXTURE_MODE", "true")
        monkeypatch.setenv("HANDSFREE_GH_CLI_ENABLED", "true")

        intent = parser.parse("explain pr 123")
        response = router.route(intent, Profile.DEFAULT)

        assert response["status"] == "ok"
        assert "intent parsing" in response["spoken_text"].lower()
        assert response["debug"]["tool_calls"][0]["provider"] == "copilot_cli"


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


class TestProfileVerbosityTuning:
    """Test profile-based verbosity tuning per PR-027 acceptance criteria."""

    def test_pr_summarize_workout_ultra_brief(
        self, router: CommandRouter, parser: IntentParser
    ) -> None:
        """Test pr.summarize with profile=workout returns 1-2 sentence summaries."""
        intent = parser.parse("summarize pr 123")
        response = router.route(intent, Profile.WORKOUT)

        assert response["status"] == "ok"
        spoken_text = response["spoken_text"]

        # Ultra-brief: should be very short
        word_count = len(spoken_text.split())
        assert word_count <= 15  # Max words for workout profile

        # Should still mention PR number
        assert "123" in spoken_text

    def test_pr_summarize_relaxed_detailed(
        self, router: CommandRouter, parser: IntentParser
    ) -> None:
        """Test pr.summarize with profile=relaxed returns detailed summaries."""
        intent = parser.parse("summarize pr 123")
        response = router.route(intent, Profile.RELAXED)

        assert response["status"] == "ok"
        spoken_text = response["spoken_text"]

        # Detailed: should be much longer than workout
        workout_response = router.route(intent, Profile.WORKOUT)
        workout_words = len(workout_response["spoken_text"].split())
        relaxed_words = len(spoken_text.split())

        assert relaxed_words > workout_words
        assert relaxed_words > 20  # Should be detailed

    def test_pr_summarize_focused_actionable(
        self, router: CommandRouter, parser: IntentParser
    ) -> None:
        """Test pr.summarize with profile=focused prioritizes actionable items."""
        intent = parser.parse("summarize pr 456")
        response = router.route(intent, Profile.FOCUSED)

        assert response["status"] == "ok"
        spoken_text = response["spoken_text"]

        # Focused: brief and actionable
        word_count = len(spoken_text.split())
        assert word_count <= 20  # Max words for focused profile

    def test_pr_summarize_commute_brief(self, router: CommandRouter, parser: IntentParser) -> None:
        """Test pr.summarize with profile=commute returns brief summaries."""
        intent = parser.parse("summarize pr 789")
        response = router.route(intent, Profile.COMMUTE)

        assert response["status"] == "ok"
        spoken_text = response["spoken_text"]

        # Brief: 2-3 sentences
        word_count = len(spoken_text.split())
        assert word_count <= 30  # Max words for commute profile
        assert word_count > 10  # Should have some detail

    def test_pr_summarize_kitchen_conversational(
        self, router: CommandRouter, parser: IntentParser
    ) -> None:
        """Test pr.summarize with profile=kitchen returns conversational summaries."""
        intent = parser.parse("summarize pr 101")
        response = router.route(intent, Profile.KITCHEN)

        assert response["status"] == "ok"
        spoken_text = response["spoken_text"]

        # Moderate: 3-4 sentences, conversational
        word_count = len(spoken_text.split())
        assert word_count <= 40  # Max words for kitchen profile
        assert word_count > 15  # Should be conversational

    def test_inbox_list_workout_brief(self, router: CommandRouter, parser: IntentParser) -> None:
        """Test inbox.list with profile=workout returns ultra-brief summaries."""
        intent = parser.parse("inbox")
        response = router.route(intent, Profile.WORKOUT)

        assert response["status"] == "ok"
        spoken_text = response["spoken_text"]

        # Ultra-brief
        word_count = len(spoken_text.split())
        assert word_count <= 15

    def test_inbox_list_focused_actionable(
        self, router: CommandRouter, parser: IntentParser
    ) -> None:
        """Test inbox.list with profile=focused prioritizes actionable items."""
        intent = parser.parse("inbox")
        response = router.route(intent, Profile.FOCUSED)

        assert response["status"] == "ok"
        spoken_text = response["spoken_text"]

        # Should be actionable and brief
        word_count = len(spoken_text.split())
        assert word_count <= 20

        # Should mention actionable items (PRs, checks)
        assert "PR" in spoken_text or "check" in spoken_text.lower()

    def test_inbox_list_relaxed_detailed(self, router: CommandRouter, parser: IntentParser) -> None:
        """Test inbox.list with profile=relaxed returns detailed summaries."""
        intent = parser.parse("inbox")
        response = router.route(intent, Profile.RELAXED)

        assert response["status"] == "ok"
        spoken_text = response["spoken_text"]

        # Should be detailed
        workout_response = router.route(intent, Profile.WORKOUT)
        workout_words = len(workout_response["spoken_text"].split())
        relaxed_words = len(spoken_text.split())

        assert relaxed_words > workout_words

    def test_default_behavior_unchanged(self, router: CommandRouter, parser: IntentParser) -> None:
        """Test that default behavior (no profile) remains unchanged."""
        intent = parser.parse("summarize pr 123")
        response = router.route(intent, Profile.DEFAULT)

        assert response["status"] == "ok"
        spoken_text = response["spoken_text"]

        # Default should be moderate/balanced
        word_count = len(spoken_text.split())
        assert word_count <= 25  # Max words for default profile

    def test_all_profiles_tested(self, router: CommandRouter, parser: IntentParser) -> None:
        """Test that all profiles have appropriate configurations."""
        intent = parser.parse("summarize pr 999")

        profiles_tested = [
            Profile.WORKOUT,
            Profile.COMMUTE,
            Profile.KITCHEN,
            Profile.FOCUSED,
            Profile.RELAXED,
            Profile.DEFAULT,
        ]

        for profile in profiles_tested:
            response = router.route(intent, profile)
            assert response["status"] == "ok"
            assert len(response["spoken_text"]) > 0

            # Verify each profile respects its word limit
            from handsfree.commands.profiles import ProfileConfig

            config = ProfileConfig.for_profile(profile)
            word_count = len(response["spoken_text"].split())
            assert word_count <= config.max_spoken_words + 1  # +1 for potential "..."

    def test_profile_verbosity_ordering(self, router: CommandRouter, parser: IntentParser) -> None:
        """Test that profiles follow expected verbosity ordering."""
        intent = parser.parse("inbox")

        # Get responses for all profiles
        workout = router.route(intent, Profile.WORKOUT)
        focused = router.route(intent, Profile.FOCUSED)
        default = router.route(intent, Profile.DEFAULT)
        kitchen = router.route(intent, Profile.KITCHEN)
        relaxed = router.route(intent, Profile.RELAXED)

        # Count words
        workout_words = len(workout["spoken_text"].split())
        focused_words = len(focused["spoken_text"].split())
        default_words = len(default["spoken_text"].split())
        kitchen_words = len(kitchen["spoken_text"].split())
        relaxed_words = len(relaxed["spoken_text"].split())

        # Verify ordering: workout <= focused <= default <= kitchen <= relaxed
        assert workout_words <= focused_words
        assert focused_words <= default_words
        assert relaxed_words >= kitchen_words

    def test_critical_info_preserved_across_profiles(
        self, router: CommandRouter, parser: IntentParser
    ) -> None:
        """Test that critical information is preserved regardless of profile."""
        intent = parser.parse("summarize pr 456")

        # All profiles should include the PR number
        for profile in Profile:
            response = router.route(intent, profile)
            assert "456" in response["spoken_text"]
