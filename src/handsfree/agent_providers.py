"""Agent provider abstraction for task execution.

Defines the interface for agent providers and includes stub implementations
for copilot and custom agents.
"""

import json
import logging
import os
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


class GitHubIssueDispatchProvider(AgentProvider):
    """GitHub issue-based agent delegation provider.

    This provider creates a GitHub issue to represent a delegated agent task.
    The issue contains task metadata and can be correlated back when a PR is opened.

    Configuration via environment variables:
    - HANDSFREE_AGENT_DISPATCH_REPO: Repository to create issues in (format: "owner/repo")
    - GITHUB_TOKEN or GitHub App credentials for authentication
    """

    def __init__(self, token_provider: Any = None):
        """Initialize the GitHub issue dispatch provider.

        Args:
            token_provider: Optional token provider for GitHub API access.
                          If not provided, will attempt to use environment token.
        """
        self.token_provider = token_provider
        self.dispatch_repo = os.getenv("HANDSFREE_AGENT_DISPATCH_REPO")

    def _get_token(self) -> str | None:
        """Get GitHub API token for dispatch operations.

        Returns:
            GitHub token or None if not available.
        """
        if self.token_provider:
            return self.token_provider.get_token()
        return os.getenv("GITHUB_TOKEN")

    def _is_configured(self) -> bool:
        """Check if provider is properly configured.

        Returns:
            True if dispatch repository and token are available.
        """
        return bool(self.dispatch_repo and self._get_token())

    def start_task(self, task: AgentTask) -> dict[str, Any]:
        """Start a task by creating a GitHub issue.

        Args:
            task: The agent task to execute.

        Returns:
            Dictionary with status and metadata about the dispatched task.
        """
        if not self._is_configured():
            error_msg = "GitHubIssueDispatchProvider not configured: "
            if not self.dispatch_repo:
                error_msg += "HANDSFREE_AGENT_DISPATCH_REPO not set"
            elif not self._get_token():
                error_msg += "No GitHub token available"

            logger.error(error_msg)
            return {
                "ok": False,
                "status": "failed",
                "message": error_msg,
                "trace": {"error": "configuration_error"},
            }

        try:
            # Import here to avoid circular dependency
            from handsfree.github.client import create_issue

            # Truncate instruction for title (GitHub max is 256 chars)
            title = task.instruction[:100] if task.instruction else "Agent Task"
            if task.instruction and len(task.instruction) > 100:
                title += "..."

            # Build issue body with task metadata
            body_parts = [
                "# Agent Task Delegation",
                "",
                f"**Task ID:** `{task.id}`",
                f"**User ID:** `{task.user_id}`",
                "",
            ]

            if task.target_type and task.target_ref:
                body_parts.extend(
                    [
                        f"**Target:** {task.target_type} `{task.target_ref}`",
                        "",
                    ]
                )

            if task.instruction:
                body_parts.extend(
                    [
                        "## Instructions",
                        "",
                        task.instruction,
                        "",
                    ]
                )

            body_parts.extend(
                [
                    "---",
                    "",
                    "<!-- agent_task_metadata",
                    json.dumps(
                        {
                            "task_id": task.id,
                            "user_id": task.user_id,
                            "provider": "github_issue_dispatch",
                        }
                    ),
                    "-->",
                ]
            )

            body = "\n".join(body_parts)

            # Create the issue
            result = create_issue(
                repo=self.dispatch_repo,
                title=title,
                body=body,
                labels=["copilot-agent"],
                token=self._get_token(),
            )

            if result.get("ok"):
                issue_url = result.get("issue_url")
                issue_number = result.get("issue_number")

                logger.info(
                    "Created dispatch issue for task %s: %s#%d",
                    task.id,
                    self.dispatch_repo,
                    issue_number,
                )

                return {
                    "ok": True,
                    "status": "running",
                    "message": f"Dispatch issue created: {issue_url}",
                    "trace": {
                        "provider": "github_issue_dispatch",
                        "dispatch_repo": self.dispatch_repo,
                        "issue_url": issue_url,
                        "issue_number": issue_number,
                    },
                }
            else:
                error_msg = result.get("message", "Failed to create issue")
                logger.error("Failed to create dispatch issue for task %s: %s", task.id, error_msg)
                return {
                    "ok": False,
                    "status": "failed",
                    "message": f"Failed to create dispatch issue: {error_msg}",
                    "trace": {
                        "provider": "github_issue_dispatch",
                        "error": "issue_creation_failed",
                    },
                }

        except Exception as e:
            logger.exception("Error creating dispatch issue for task %s", task.id)
            return {
                "ok": False,
                "status": "failed",
                "message": f"Exception during dispatch: {type(e).__name__}: {str(e)}",
                "trace": {
                    "provider": "github_issue_dispatch",
                    "error": "exception",
                },
            }

    def check_status(self, task: AgentTask) -> dict[str, Any]:
        """Check the current status of a dispatched task.

        The task status is primarily updated via webhook correlation,
        so this method returns the current state without polling GitHub.

        Args:
            task: The agent task to check.

        Returns:
            Dictionary with current status.
        """
        # Extract trace information
        trace = task.trace or {}
        issue_url = trace.get("issue_url")
        pr_url = trace.get("pr_url")

        if pr_url:
            return {
                "ok": True,
                "status": "completed",
                "message": f"PR opened: {pr_url}",
            }
        elif issue_url:
            return {
                "ok": True,
                "status": "running",
                "message": f"Dispatch issue created: {issue_url}",
            }
        else:
            return {
                "ok": True,
                "status": task.state,
                "message": "Task status tracked via webhooks",
            }

    def cancel_task(self, task: AgentTask) -> dict[str, Any]:
        """Cancel a dispatched task.

        Note: This does not close the GitHub issue, as that could be
        misleading if work is already in progress.

        Args:
            task: The agent task to cancel.

        Returns:
            Dictionary with cancellation status.
        """
        logger.info("Cancelling dispatched task %s", task.id)
        return {
            "ok": True,
            "status": "failed",
            "message": "Task cancelled (dispatch issue remains open)",
        }


def get_provider(provider_name: str) -> AgentProvider:
    """Get an agent provider by name.

    For the mock provider, returns a singleton instance to maintain state across calls.
    For other providers, creates new instances.

    Args:
        provider_name: Name of the provider (copilot, custom, mock, github_issue_dispatch).

    Returns:
        AgentProvider instance.

    Raises:
        ValueError: If provider name is not recognized.
    """
    # Use singleton for mock provider to maintain state
    if provider_name == "mock":
        global _mock_provider_instance
        if _mock_provider_instance is None:
            _mock_provider_instance = MockAgentProvider()
        return _mock_provider_instance

    providers = {
        "copilot": CopilotAgentProvider,
        "custom": CustomAgentProvider,
        "github_issue_dispatch": GitHubIssueDispatchProvider,
    }

    if provider_name not in providers:
        raise ValueError(f"Unknown provider: {provider_name}")

    return providers[provider_name]()


def reset_mock_provider() -> None:
    """Reset the mock provider singleton instance.

    This is primarily for testing purposes to ensure test isolation.
    """
    global _mock_provider_instance
    _mock_provider_instance = None


# Global mock provider instance
_mock_provider_instance: MockAgentProvider | None = None
