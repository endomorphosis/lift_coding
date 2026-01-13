"""Agent provider abstraction for task execution.

Defines the interface for agent providers and includes stub implementations
for copilot and custom agents.
"""

import logging
from abc import ABC, abstractmethod
from typing import Any

from handsfree.db.agent_tasks import AgentTask

logger = logging.getLogger(__name__)


class AgentProvider(ABC):
    """Abstract base class for agent providers."""

    @abstractmethod
    def start_task(self, task: AgentTask) -> dict[str, Any]:
        """Start executing an agent task.

        Args:
            task: The agent task to execute.

        Returns:
            Dictionary with status and metadata about the started task.
        """
        pass

    @abstractmethod
    def check_status(self, task: AgentTask) -> dict[str, Any]:
        """Check the current status of a running task.

        Args:
            task: The agent task to check.

        Returns:
            Dictionary with current status and any updates.
        """
        pass

    @abstractmethod
    def cancel_task(self, task: AgentTask) -> dict[str, Any]:
        """Cancel a running task.

        Args:
            task: The agent task to cancel.

        Returns:
            Dictionary with cancellation status.
        """
        pass


class MockAgentProvider(AgentProvider):
    """Mock agent provider for testing and development.

    This provider simulates agent behavior by automatically
    transitioning through states without actual execution.
    """

    def __init__(self):
        """Initialize the mock provider."""
        self.tasks = {}

    def start_task(self, task: AgentTask) -> dict[str, Any]:
        """Start a mock task execution."""
        logger.info(f"MockAgentProvider: Starting task {task.id}")

        # Store task state
        self.tasks[task.id] = {
            "status": "running",
            "progress": "Mock agent started processing",
            "step": 0,
        }

        return {
            "ok": True,
            "status": "running",
            "message": "Mock agent started",
            "trace": {
                "provider": "mock",
                "instruction": task.instruction,
                "started_at": str(task.created_at),
            },
        }

    def check_status(self, task: AgentTask) -> dict[str, Any]:
        """Check mock task status."""
        if task.id not in self.tasks:
            return {
                "ok": False,
                "status": "unknown",
                "message": "Task not found in mock provider",
            }

        task_state = self.tasks[task.id]
        step = task_state["step"]

        # Simulate progress over multiple checks
        if step == 0:
            task_state["step"] = 1
            task_state["progress"] = "Analyzing code"
            return {
                "ok": True,
                "status": "running",
                "message": "Analyzing code",
            }
        elif step == 1:
            task_state["step"] = 2
            task_state["progress"] = "Generating changes"
            return {
                "ok": True,
                "status": "running",
                "message": "Generating changes",
            }
        elif step == 2:
            # Complete the task
            task_state["status"] = "completed"
            task_state["progress"] = "Mock PR opened"
            return {
                "ok": True,
                "status": "completed",
                "message": "Mock PR opened at https://github.com/mock/repo/pull/123",
                "trace": {
                    "pr_url": "https://github.com/mock/repo/pull/123",
                    "commits": ["abc123"],
                },
            }

        return {
            "ok": True,
            "status": task_state["status"],
            "message": task_state["progress"],
        }

    def cancel_task(self, task: AgentTask) -> dict[str, Any]:
        """Cancel a mock task."""
        if task.id in self.tasks:
            self.tasks[task.id]["status"] = "failed"
            self.tasks[task.id]["progress"] = "Cancelled by user"

        return {
            "ok": True,
            "status": "failed",
            "message": "Task cancelled",
        }


class CopilotAgentProvider(AgentProvider):
    """GitHub Copilot agent provider (stub implementation).

    This is a placeholder for actual Copilot integration.
    In production, this would interface with GitHub Copilot APIs.
    """

    def start_task(self, task: AgentTask) -> dict[str, Any]:
        """Start a Copilot task (stubbed)."""
        logger.info(f"CopilotAgentProvider: Would start task {task.id}")

        return {
            "ok": True,
            "status": "running",
            "message": "[STUB] Copilot agent would be invoked here",
            "trace": {
                "provider": "copilot",
                "instruction": task.instruction,
            },
        }

    def check_status(self, task: AgentTask) -> dict[str, Any]:
        """Check Copilot task status (stubbed)."""
        return {
            "ok": True,
            "status": "running",
            "message": "[STUB] Copilot task status would be checked here",
        }

    def cancel_task(self, task: AgentTask) -> dict[str, Any]:
        """Cancel a Copilot task (stubbed)."""
        return {
            "ok": True,
            "status": "failed",
            "message": "[STUB] Copilot task would be cancelled here",
        }


class CustomAgentProvider(AgentProvider):
    """Custom agent provider (stub implementation).

    This is a placeholder for custom containerized agent runners.
    In production, this would manage custom agent workflows.
    """

    def start_task(self, task: AgentTask) -> dict[str, Any]:
        """Start a custom agent task (stubbed)."""
        logger.info(f"CustomAgentProvider: Would start task {task.id}")

        return {
            "ok": True,
            "status": "running",
            "message": "[STUB] Custom agent would be started here",
            "trace": {
                "provider": "custom",
                "instruction": task.instruction,
            },
        }

    def check_status(self, task: AgentTask) -> dict[str, Any]:
        """Check custom agent task status (stubbed)."""
        return {
            "ok": True,
            "status": "running",
            "message": "[STUB] Custom agent status would be checked here",
        }

    def cancel_task(self, task: AgentTask) -> dict[str, Any]:
        """Cancel a custom agent task (stubbed)."""
        return {
            "ok": True,
            "status": "failed",
            "message": "[STUB] Custom agent would be cancelled here",
        }


def get_provider(provider_name: str) -> AgentProvider:
    """Get an agent provider by name.

    Args:
        provider_name: Name of the provider (copilot, custom, mock).

    Returns:
        AgentProvider instance.

    Raises:
        ValueError: If provider name is not recognized.
    """
    providers = {
        "mock": MockAgentProvider,
        "copilot": CopilotAgentProvider,
        "custom": CustomAgentProvider,
    }

    if provider_name not in providers:
        raise ValueError(f"Unknown provider: {provider_name}")

    return providers[provider_name]()
