"""Tests for Copilot CLI provider scaffold."""

from datetime import UTC, datetime
from types import SimpleNamespace

from handsfree.ai import AIExecutionMode
from handsfree.agent_providers import (
    CopilotCLIAgentProvider,
    get_provider,
    is_copilot_cli_available,
    reset_copilot_cli_availability_cache,
)
from handsfree.cli.models import CLIResult


class TestCopilotCLIAvailability:
    """Test Copilot CLI availability detection."""

    def test_returns_false_when_gh_missing(self, monkeypatch):
        """Availability check should return False when gh is not installed."""
        reset_copilot_cli_availability_cache()
        monkeypatch.setattr("handsfree.agent_providers.shutil.which", lambda _: None)
        assert is_copilot_cli_available() is False


class TestCopilotCLIProvider:
    """Test Copilot CLI provider behavior."""

    def test_factory_returns_copilot_cli_provider(self):
        """Provider factory should support copilot_cli."""
        provider = get_provider("copilot_cli")
        assert isinstance(provider, CopilotCLIAgentProvider)

    def test_start_task_fails_when_cli_unavailable(self, monkeypatch):
        """Provider should fail fast with clear metadata when CLI is unavailable."""
        monkeypatch.setattr(
            "handsfree.agent_providers.is_copilot_cli_available",
            lambda: False,
        )
        provider = CopilotCLIAgentProvider()
        task = SimpleNamespace(
            id="task-123",
            instruction="explain failing tests",
            created_at=datetime.now(UTC),
        )

        result = provider.start_task(task)

        assert result["ok"] is False
        assert result["status"] == "failed"
        assert result["trace"]["provider"] == "copilot_cli"
        assert result["trace"]["cli_available"] is False

    def test_start_task_uses_fixture_mode_for_pr_targets(self, monkeypatch):
        """Provider should attach fixture-backed CLI trace when fixture mode is enabled."""
        monkeypatch.setenv("HANDSFREE_CLI_FIXTURE_MODE", "true")
        monkeypatch.setattr(
            "handsfree.agent_providers.is_copilot_cli_available",
            lambda: False,
        )
        provider = CopilotCLIAgentProvider()
        task = SimpleNamespace(
            id="task-123",
            instruction="explain pr 123",
            target_type="pr",
            target_ref="owner/repo#123",
            created_at=datetime.now(UTC),
        )

        result = provider.start_task(task)

        assert result["ok"] is True
        assert result["trace"]["provider"] == "copilot_cli"
        assert result["trace"]["fixture_mode"] is True
        assert result["trace"]["source"] == "fixture"

    def test_start_task_uses_shared_ai_request_contract(self, monkeypatch):
        """Provider should delegate PR tasks through the shared AI request layer."""
        monkeypatch.setattr(
            "handsfree.agent_providers.is_copilot_cli_available",
            lambda: True,
        )
        captured: dict[str, object] = {}

        class StubExecution:
            capability_id = "copilot.pr.failure_explain"
            execution_mode = AIExecutionMode.CLI_LIVE
            output = {
                "spoken_text": "Shared failure explanation",
                "summary": "Shared failure explanation",
                "trace": {
                    "command_id": "gh.copilot.explain_failure",
                    "source": "cli_live",
                    "duration_ms": 12,
                },
            }

        def stub_execute_ai_request(request, **kwargs):
            captured["request"] = request
            captured["kwargs"] = kwargs
            return StubExecution()

        monkeypatch.setattr(
            "handsfree.ai.capabilities.execute_ai_request",
            stub_execute_ai_request,
        )

        provider = CopilotCLIAgentProvider()
        task = SimpleNamespace(
            id="task-456",
            instruction="explain failing checks for pr 123",
            target_type="pr",
            target_ref="owner/repo#123",
            created_at=datetime.now(UTC),
        )

        result = provider.start_task(task)

        assert result["ok"] is True
        assert captured["request"].capability_id == "copilot.pr.failure_explain"
        assert captured["request"].context.repo == "owner/repo"
        assert captured["request"].context.pr_number == 123
        assert result["trace"]["execution_mode"] == "cli_live"
        assert result["trace"]["policy_resolution"]["requested_workflow"] == "failure_rag_explain"
        assert result["trace"]["policy_resolution"]["resolved_workflow"] == "failure_rag_explain"
        assert result["trace"]["policy_resolution"]["policy_applied"] is False
        assert result["message"] == "Shared failure explanation"

    def test_start_task_uses_policy_selected_accelerated_summary_capability(self, monkeypatch):
        """Provider should honor accelerated summary policy when delegating PR summaries."""
        monkeypatch.setattr(
            "handsfree.agent_providers.is_copilot_cli_available",
            lambda: True,
        )
        monkeypatch.setenv("HANDSFREE_AI_DEFAULT_SUMMARY_BACKEND", "accelerated")
        captured: dict[str, object] = {}

        class StubExecution:
            capability_id = "github.pr.accelerated_summary"
            execution_mode = AIExecutionMode.ORCHESTRATED
            output = {
                "spoken_text": "Accelerated delegated summary",
                "summary": "Accelerated delegated summary",
                "trace": {
                    "provider": "composite",
                },
            }

        def stub_execute_ai_request(request, **kwargs):
            captured["request"] = request
            return StubExecution()

        monkeypatch.setattr(
            "handsfree.ai.capabilities.execute_ai_request",
            stub_execute_ai_request,
        )

        provider = CopilotCLIAgentProvider()
        task = SimpleNamespace(
            id="task-457",
            instruction="summarize pr 123",
            target_type="pr",
            target_ref="owner/repo#123",
            created_at=datetime.now(UTC),
        )

        result = provider.start_task(task)

        assert result["ok"] is True
        assert captured["request"].capability_id == "github.pr.accelerated_summary"
        assert result["trace"]["execution_mode"] == "orchestrated"
        assert result["trace"]["policy_resolution"]["requested_workflow"] == "pr_rag_summary"
        assert result["trace"]["policy_resolution"]["resolved_workflow"] == "accelerated_pr_summary"
        assert result["trace"]["policy_resolution"]["policy_applied"] is True

    def test_start_task_uses_policy_selected_composite_failure_capability(self, monkeypatch):
        """Provider should honor composite failure policy when delegating PR failures."""
        monkeypatch.setattr(
            "handsfree.agent_providers.is_copilot_cli_available",
            lambda: True,
        )
        monkeypatch.setenv("HANDSFREE_AI_DEFAULT_FAILURE_BACKEND", "composite")
        captured: dict[str, object] = {}

        class StubExecution:
            capability_id = "github.check.failure_rag_explain"
            execution_mode = AIExecutionMode.ORCHESTRATED
            output = {
                "spoken_text": "Composite delegated failure analysis",
                "summary": "Composite delegated failure analysis",
                "trace": {
                    "provider": "composite",
                },
            }

        def stub_execute_ai_request(request, **kwargs):
            captured["request"] = request
            return StubExecution()

        monkeypatch.setattr(
            "handsfree.ai.capabilities.execute_ai_request",
            stub_execute_ai_request,
        )

        provider = CopilotCLIAgentProvider()
        task = SimpleNamespace(
            id="task-458",
            instruction="explain failing checks for pr 123",
            target_type="pr",
            target_ref="owner/repo#123",
            created_at=datetime.now(UTC),
        )

        result = provider.start_task(task)

        assert result["ok"] is True
        assert captured["request"].capability_id == "github.check.failure_rag_explain"
        assert result["trace"]["execution_mode"] == "orchestrated"
        assert result["trace"]["policy_resolution"]["requested_workflow"] == "failure_rag_explain"
        assert result["trace"]["policy_resolution"]["resolved_workflow"] == "failure_rag_explain"
        assert result["trace"]["policy_resolution"]["policy_applied"] is False

    def test_start_task_handles_non_json_cli_output(self, monkeypatch):
        """Provider should degrade safely when CLI output is not parseable JSON."""
        monkeypatch.setattr(
            "handsfree.agent_providers.is_copilot_cli_available",
            lambda: True,
        )

        class FakeExecutor:
            def fixture_mode(self):
                return False

            def execute(self, *_args, **_kwargs):
                return CLIResult(
                    ok=True,
                    stdout="The gh-copilot extension has been deprecated.",
                    command_id="gh.copilot.explain_pr",
                    duration_ms=12,
                    source="cli_live",
                )

        monkeypatch.setattr("handsfree.agent_providers.CLIExecutor", FakeExecutor)

        provider = CopilotCLIAgentProvider()
        task = SimpleNamespace(
            id="task-789",
            instruction="explain pr 123",
            target_type="pr",
            target_ref="owner/repo#123",
            created_at=datetime.now(UTC),
        )

        result = provider.start_task(task)

        assert result["ok"] is True
        assert result["status"] == "running"
        assert result["trace"]["provider"] == "copilot_cli"
        assert result["trace"]["parse_error"] is True
        assert "deprecated" in result["message"].lower()
