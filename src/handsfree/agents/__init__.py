"""Agent providers for delegating tasks to different agent systems.

This module defines the provider interface and implements placeholder providers
for Copilot and custom agents, plus a deterministic mock runner for testing.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any


@dataclass
class AgentInvocationResult:
    """Result of an agent invocation attempt."""

    success: bool
    message: str
    trace: dict[str, Any] | None = None


class AgentProvider(ABC):
    """Abstract interface for agent providers."""

    @abstractmethod
    def invoke(
        self,
        task_id: str,
        instruction: str | None,
        target_type: str | None,
        target_ref: str | None,
    ) -> AgentInvocationResult:
        """Invoke the agent with a task.

        Args:
            task_id: Unique task identifier.
            instruction: Instruction text for the agent.
            target_type: Type of target ("issue", "pr", or None).
            target_ref: Reference to target (e.g., "owner/repo#123").

        Returns:
            AgentInvocationResult with success status and details.
        """
        pass

    @abstractmethod
    def get_status(self, task_id: str) -> dict[str, Any]:
        """Get status of a task.

        Args:
            task_id: Unique task identifier.

        Returns:
            Dictionary with task status information.
        """
        pass


class CopilotProvider(AgentProvider):
    """Placeholder provider for GitHub Copilot agent.

    NOTE: This is a stub implementation that does NOT perform real invocation.
    Real implementation will be added in a future PR.
    """

    def invoke(
        self,
        task_id: str,
        instruction: str | None,
        target_type: str | None,
        target_ref: str | None,
    ) -> AgentInvocationResult:
        """Placeholder invocation - does not perform real agent call."""
        return AgentInvocationResult(
            success=False,
            message="Copilot invocation not implemented (placeholder only)",
            trace={"provider": "copilot", "task_id": task_id, "stub": True},
        )

    def get_status(self, task_id: str) -> dict[str, Any]:
        """Placeholder status - returns stub data."""
        return {
            "task_id": task_id,
            "provider": "copilot",
            "status": "not_implemented",
            "message": "Copilot status not implemented (placeholder only)",
        }


class CustomProvider(AgentProvider):
    """Placeholder provider for custom agent implementations.

    NOTE: This is a stub implementation that does NOT perform real invocation.
    Real implementation will be added in a future PR.
    """

    def invoke(
        self,
        task_id: str,
        instruction: str | None,
        target_type: str | None,
        target_ref: str | None,
    ) -> AgentInvocationResult:
        """Placeholder invocation - does not perform real agent call."""
        return AgentInvocationResult(
            success=False,
            message="Custom provider invocation not implemented (placeholder only)",
            trace={"provider": "custom", "task_id": task_id, "stub": True},
        )

    def get_status(self, task_id: str) -> dict[str, Any]:
        """Placeholder status - returns stub data."""
        return {
            "task_id": task_id,
            "provider": "custom",
            "status": "not_implemented",
            "message": "Custom provider status not implemented (placeholder only)",
        }


class MockAgentRunner:
    """Deterministic mock agent runner for testing.

    This runner does NOT use timers and requires explicit state transitions
    via API calls to ensure stable, deterministic tests.
    """

    def __init__(self) -> None:
        """Initialize the mock runner."""
        self._tasks: dict[str, dict[str, Any]] = {}

    def register_task(
        self,
        task_id: str,
        instruction: str | None,
        target_type: str | None,
        target_ref: str | None,
    ) -> None:
        """Register a task with the mock runner.

        Args:
            task_id: Unique task identifier.
            instruction: Instruction text for the agent.
            target_type: Type of target ("issue", "pr", or None).
            target_ref: Reference to target (e.g., "owner/repo#123").
        """
        self._tasks[task_id] = {
            "instruction": instruction,
            "target_type": target_type,
            "target_ref": target_ref,
            "state": "registered",
            "steps": [],
        }

    def advance_task(self, task_id: str, new_state: str, step_info: dict[str, Any] | None = None) -> bool:
        """Explicitly advance task to a new state.

        Args:
            task_id: Task identifier.
            new_state: New state to transition to.
            step_info: Optional information about this step.

        Returns:
            True if transition succeeded, False if task not found.
        """
        if task_id not in self._tasks:
            return False

        self._tasks[task_id]["state"] = new_state
        if step_info:
            self._tasks[task_id]["steps"].append(step_info)
        return True

    def get_task_info(self, task_id: str) -> dict[str, Any] | None:
        """Get information about a task.

        Args:
            task_id: Task identifier.

        Returns:
            Task information dict or None if not found.
        """
        return self._tasks.get(task_id)

    def clear(self) -> None:
        """Clear all registered tasks."""
        self._tasks.clear()


# Global mock runner instance for testing
_mock_runner = MockAgentRunner()


def get_mock_runner() -> MockAgentRunner:
    """Get the global mock runner instance."""
    return _mock_runner


class MockProvider(AgentProvider):
    """Mock provider that uses the deterministic mock runner."""

    def __init__(self, runner: MockAgentRunner | None = None) -> None:
        """Initialize mock provider.

        Args:
            runner: Optional mock runner instance. If None, uses global instance.
        """
        self.runner = runner or get_mock_runner()

    def invoke(
        self,
        task_id: str,
        instruction: str | None,
        target_type: str | None,
        target_ref: str | None,
    ) -> AgentInvocationResult:
        """Register task with mock runner."""
        self.runner.register_task(task_id, instruction, target_type, target_ref)
        return AgentInvocationResult(
            success=True,
            message="Task registered with mock runner",
            trace={"provider": "mock", "task_id": task_id},
        )

    def get_status(self, task_id: str) -> dict[str, Any]:
        """Get task status from mock runner."""
        info = self.runner.get_task_info(task_id)
        if not info:
            return {"task_id": task_id, "found": False}

        return {
            "task_id": task_id,
            "found": True,
            "state": info["state"],
            "steps": info["steps"],
        }


def get_provider(provider_name: str) -> AgentProvider:
    """Factory function to get an agent provider by name.

    Args:
        provider_name: Name of the provider ("copilot", "custom", "mock").

    Returns:
        AgentProvider instance.

    Raises:
        ValueError: If provider_name is unknown.
    """
    providers = {
        "copilot": CopilotProvider(),
        "custom": CustomProvider(),
        "mock": MockProvider(),
    }

    provider = providers.get(provider_name.lower())
    if not provider:
        raise ValueError(
            f"Unknown provider: {provider_name}. "
            f"Valid providers: {', '.join(providers.keys())}"
        )

    return provider
