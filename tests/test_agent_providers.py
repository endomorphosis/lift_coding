"""Tests for agent providers."""

import pytest

from handsfree.agents import (
    CopilotProvider,
    CustomProvider,
    MockAgentRunner,
    MockProvider,
    get_mock_runner,
    get_provider,
)


class TestAgentProviders:
    """Test agent provider implementations."""

    def test_copilot_provider_is_stub(self):
        """Test that CopilotProvider is a placeholder."""
        provider = CopilotProvider()

        result = provider.invoke(
            task_id="test-123",
            instruction="fix bug",
            target_type="issue",
            target_ref="owner/repo#42",
        )

        assert result.success is False
        assert "not implemented" in result.message.lower()
        assert result.trace is not None
        assert result.trace["provider"] == "copilot"

    def test_custom_provider_is_stub(self):
        """Test that CustomProvider is a placeholder."""
        provider = CustomProvider()

        result = provider.invoke(
            task_id="test-123",
            instruction="review pr",
            target_type="pr",
            target_ref="owner/repo#99",
        )

        assert result.success is False
        assert "not implemented" in result.message.lower()
        assert result.trace is not None
        assert result.trace["provider"] == "custom"

    def test_get_provider_factory(self):
        """Test provider factory function."""
        copilot = get_provider("copilot")
        assert isinstance(copilot, CopilotProvider)

        custom = get_provider("custom")
        assert isinstance(custom, CustomProvider)

        mock = get_provider("mock")
        assert isinstance(mock, MockProvider)

    def test_get_provider_unknown(self):
        """Test provider factory with unknown provider."""
        with pytest.raises(ValueError, match="Unknown provider"):
            get_provider("unknown")


class TestMockAgentRunner:
    """Test the deterministic mock agent runner."""

    def test_register_and_retrieve_task(self):
        """Test registering and retrieving a task."""
        runner = MockAgentRunner()

        runner.register_task(
            task_id="task-123",
            instruction="test instruction",
            target_type="issue",
            target_ref="owner/repo#42",
        )

        info = runner.get_task_info("task-123")

        assert info is not None
        assert info["instruction"] == "test instruction"
        assert info["target_type"] == "issue"
        assert info["target_ref"] == "owner/repo#42"
        assert info["state"] == "registered"
        assert info["steps"] == []

    def test_advance_task_state(self):
        """Test advancing task state."""
        runner = MockAgentRunner()

        runner.register_task(task_id="task-123", instruction="test", target_type=None, target_ref=None)

        success = runner.advance_task("task-123", "running", {"action": "started"})

        assert success is True
        info = runner.get_task_info("task-123")
        assert info["state"] == "running"
        assert len(info["steps"]) == 1
        assert info["steps"][0]["action"] == "started"

    def test_advance_multiple_steps(self):
        """Test advancing through multiple steps."""
        runner = MockAgentRunner()

        runner.register_task(task_id="task-123", instruction="test", target_type=None, target_ref=None)
        runner.advance_task("task-123", "running", {"step": 1})
        runner.advance_task("task-123", "processing", {"step": 2})
        runner.advance_task("task-123", "completed", {"step": 3})

        info = runner.get_task_info("task-123")
        assert info["state"] == "completed"
        assert len(info["steps"]) == 3

    def test_advance_nonexistent_task(self):
        """Test advancing a nonexistent task."""
        runner = MockAgentRunner()

        success = runner.advance_task("nonexistent", "running")

        assert success is False

    def test_clear_tasks(self):
        """Test clearing all tasks."""
        runner = MockAgentRunner()

        runner.register_task(task_id="task-1", instruction="test1", target_type=None, target_ref=None)
        runner.register_task(task_id="task-2", instruction="test2", target_type=None, target_ref=None)

        runner.clear()

        assert runner.get_task_info("task-1") is None
        assert runner.get_task_info("task-2") is None

    def test_global_runner_instance(self):
        """Test that get_mock_runner returns the same instance."""
        runner1 = get_mock_runner()
        runner2 = get_mock_runner()

        assert runner1 is runner2

        # Register a task in runner1
        runner1.register_task(task_id="shared-task", instruction="test", target_type=None, target_ref=None)

        # Should be visible in runner2
        info = runner2.get_task_info("shared-task")
        assert info is not None


class TestMockProvider:
    """Test the mock provider."""

    def test_invoke_registers_task(self):
        """Test that invoke registers a task with the runner."""
        runner = MockAgentRunner()
        runner.clear()  # Start fresh
        provider = MockProvider(runner)

        result = provider.invoke(
            task_id="test-123",
            instruction="test task",
            target_type="issue",
            target_ref="owner/repo#42",
        )

        assert result.success is True
        assert "registered" in result.message.lower()

        # Check that task is registered
        info = runner.get_task_info("test-123")
        assert info is not None
        assert info["instruction"] == "test task"

    def test_get_status_found(self):
        """Test getting status of a registered task."""
        runner = MockAgentRunner()
        runner.clear()
        provider = MockProvider(runner)

        provider.invoke(
            task_id="test-123", instruction="test", target_type=None, target_ref=None
        )

        status = provider.get_status("test-123")

        assert status["task_id"] == "test-123"
        assert status["found"] is True
        assert status["state"] == "registered"

    def test_get_status_not_found(self):
        """Test getting status of a nonexistent task."""
        runner = MockAgentRunner()
        runner.clear()
        provider = MockProvider(runner)

        status = provider.get_status("nonexistent")

        assert status["task_id"] == "nonexistent"
        assert status["found"] is False

    def test_mock_provider_with_global_runner(self):
        """Test mock provider using the global runner."""
        # Clear global runner first
        global_runner = get_mock_runner()
        global_runner.clear()

        # Create provider without explicit runner
        provider = MockProvider()

        result = provider.invoke(
            task_id="global-task", instruction="test", target_type=None, target_ref=None
        )

        assert result.success is True

        # Verify task is in global runner
        info = global_runner.get_task_info("global-task")
        assert info is not None
