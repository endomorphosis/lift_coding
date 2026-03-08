"""Tests for Copilot CLI provider scaffold."""

from datetime import UTC, datetime
from types import SimpleNamespace

from handsfree.agent_providers import (
    CopilotCLIAgentProvider,
    get_provider,
    is_copilot_cli_available,
    reset_copilot_cli_availability_cache,
)
<<<<<<< Updated upstream
=======
from handsfree.cli.models import CLIResult
>>>>>>> Stashed changes


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
<<<<<<< Updated upstream
=======

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
>>>>>>> Stashed changes
