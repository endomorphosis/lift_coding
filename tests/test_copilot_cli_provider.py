"""Tests for Copilot CLI provider scaffold."""

from datetime import UTC, datetime
from types import SimpleNamespace

from handsfree.agent_providers import (
    CopilotCLIAgentProvider,
    get_provider,
    is_copilot_cli_available,
)


class TestCopilotCLIAvailability:
    """Test Copilot CLI availability detection."""

    def test_returns_false_when_gh_missing(self, monkeypatch):
        """Availability check should return False when gh is not installed."""
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
