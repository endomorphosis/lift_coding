"""Agent provider abstraction for task execution.

Defines the interface for agent providers and includes stub implementations
for copilot and custom agents.
"""

import json
import logging
import os
import shutil
import subprocess
import re
import shutil
import subprocess
import uuid
from abc import ABC, abstractmethod
from functools import lru_cache
from typing import Any

from handsfree.cli.executor import CLIExecutor
from handsfree.cli.parsers import parse_output
from handsfree.db.agent_tasks import AgentTask
from handsfree.mcp import (
    MCPClient,
    MCPClientError,
    MCPConfigurationError,
    MCPToolInvocationResult,
    get_mcp_server_config,
    is_mcp_provider_enabled,
    resolve_task_binding,
)

logger = logging.getLogger(__name__)
CLI_DETECTION_TIMEOUT_SECONDS = 2


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


@lru_cache(maxsize=1)
def _detect_copilot_cli_available() -> bool:
    """Detect whether GitHub Copilot CLI is available via gh.

    Returns:
        True when `gh` is installed and `gh copilot --help` exits successfully.
    """
    gh_path = shutil.which("gh")
    if not gh_path:
        return False

    try:
        result = subprocess.run(
            [gh_path, "copilot", "--help"],
            capture_output=True,
            text=True,
            timeout=CLI_DETECTION_TIMEOUT_SECONDS,
            check=False,
        )
        return result.returncode == 0
    except subprocess.TimeoutExpired:
        logger.debug(
            "Timed out after %ss while detecting Copilot CLI availability",
            CLI_DETECTION_TIMEOUT_SECONDS,
        )
        return False
    except (OSError, subprocess.SubprocessError):
        return False


def is_copilot_cli_available() -> bool:
    """Return cached Copilot CLI availability."""
    return _detect_copilot_cli_available()


def reset_copilot_cli_availability_cache() -> None:
    """Clear cached Copilot CLI availability (primarily for tests)."""
    _detect_copilot_cli_available.cache_clear()


class CopilotCLIAgentProvider(AgentProvider):
    """GitHub Copilot CLI provider scaffold.

    This provider is the first implementation step toward real CLI-backed
    Copilot task delegation. It currently validates CLI availability and
    returns structured trace metadata for future command execution phases.
    """

    def start_task(self, task: AgentTask) -> dict[str, Any]:
        """Start a Copilot CLI task (scaffold)."""
        if not is_copilot_cli_available():
        executor = CLIExecutor()
        fixture_mode = executor.fixture_mode()
        cli_available = is_copilot_cli_available()

        if not fixture_mode and not cli_available:
            return {
                "ok": False,
                "status": "failed",
                "message": "Copilot CLI is not available (`gh copilot` not detected)",
                "trace": {
                    "provider": "copilot_cli",
                    "cli_available": False,
                },
            }

        trace = {
            "provider": "copilot_cli",
            "instruction": task.instruction,
            "cli_available": cli_available,
            "fixture_mode": fixture_mode,
        }

        pr_number = _extract_target_number(task.target_ref)
        if task.target_type == "pr" and pr_number:
            result = executor.execute("gh.copilot.explain_pr", "copilot", pr_number=pr_number)
            if result.ok:
                try:
                    parsed = parse_output("gh_copilot_explain_pr", result.stdout)
                except Exception:
                    logger.warning(
                        "Failed to parse Copilot CLI output for task %s",
                        task.id,
                        exc_info=True,
                    )
                    preview = result.stdout.strip().splitlines()[0] if result.stdout.strip() else ""
                    trace.update(
                        {
                            "command_id": result.command_id,
                            "source": result.source,
                            "duration_ms": result.duration_ms,
                            "parse_error": True,
                            "preview": preview[:200],
                        }
                    )
                    return {
                        "ok": True,
                        "status": "running",
                        "message": preview or "[STUB] Copilot CLI task started",
                        "trace": trace,
                    }
                trace.update(
                    {
                        "command_id": result.command_id,
                        "source": result.source,
                        "duration_ms": result.duration_ms,
                        "preview": parsed.get("spoken_text") or parsed.get("summary"),
                    }
                )
                return {
                    "ok": True,
                    "status": "running",
                    "message": parsed.get("spoken_text", "[STUB] Copilot CLI task started"),
                    "trace": trace,
                }

        return {
            "ok": True,
            "status": "running",
            "message": "[STUB] Copilot CLI agent would be invoked here",
            "trace": {
                "provider": "copilot_cli",
                "instruction": task.instruction,
                "cli_available": True,
            },
        }

    def check_status(self, task: AgentTask) -> dict[str, Any]:
        """Check Copilot CLI task status (stubbed)."""
        return {
            "ok": True,
            "status": "running",
            "message": "[STUB] Copilot CLI task status would be checked here",
        }

    def cancel_task(self, task: AgentTask) -> dict[str, Any]:
        """Cancel a Copilot CLI task (stubbed)."""
        return {
            "ok": True,
            "status": "failed",
            "message": "[STUB] Copilot CLI task would be cancelled here",
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


def _map_mcp_status_to_task_state(status: str) -> str:
    normalized = status.strip().lower()
    if normalized in {"completed", "succeeded", "success"}:
        return "completed"
    if normalized in {"failed", "error", "cancelled", "canceled"}:
        return "failed"
    if normalized in {"needs_input", "requires_input", "awaiting_input"}:
        return "needs_input"
    return "running"


class MCPAgentProvider(AgentProvider):
    """Shared MCP-backed agent provider implementation."""

    provider_name = "mcp"
    server_family = ""

    def __init__(self, client: MCPClient | None = None):
        self._client = client

    def _get_client(self) -> MCPClient:
        if self._client is None:
            self._client = MCPClient(get_mcp_server_config(self.server_family))
        return self._client

    def _tool_name(self) -> str:
        config = get_mcp_server_config(self.server_family)
        return config.tool_name or f"{self.server_family}.run_task"

    def _base_trace(self, task: AgentTask) -> dict[str, Any]:
        endpoint = ""
        try:
            endpoint = get_mcp_server_config(self.server_family).endpoint
        except Exception:
            endpoint = ""
        return {
            "provider": self.provider_name,
            "mcp_server_family": self.server_family,
            "mcp_endpoint": endpoint,
            "correlation_id": str(uuid.uuid4()),
            "task_id": task.id,
        }

    def _build_arguments(self, task: AgentTask) -> dict[str, Any]:
        arguments = {
            "task_id": task.id,
            "instruction": task.instruction,
            "target_type": task.target_type,
            "target_ref": task.target_ref,
            "provider": self.provider_name,
        }
        trace = task.trace or {}
        for key in (
            "mcp_capability",
            "mcp_input",
            "mcp_cid",
            "mcp_pin_action",
            "mcp_seed_url",
            "provider_label",
        ):
            value = trace.get(key)
            if value is not None:
                arguments[key] = value
        return arguments

    def start_task(self, task: AgentTask) -> dict[str, Any]:
        trace = self._base_trace(task)

        if not is_mcp_provider_enabled(self.provider_name):
            return {
                "ok": False,
                "status": "failed",
                "message": f"{self.provider_name} is disabled by configuration",
                "trace": trace | {"error": "provider_disabled"},
            }

        client = self._get_client()
        try:
            config = get_mcp_server_config(self.server_family)
            client.validate_configuration()
            handshake = client.handshake()
            binding = resolve_task_binding(
                server_family=self.server_family,
                config=config,
                base_arguments=self._build_arguments(task),
            )
            result = client.invoke_tool(
                tool_name=binding.start_call.tool_name,
                arguments=binding.start_call.arguments,
                correlation_id=trace["correlation_id"],
            )
        except MCPConfigurationError as exc:
            return {
                "ok": False,
                "status": "failed",
                "message": str(exc),
                "trace": trace | {"error": "configuration_error"},
            }
        except MCPClientError as exc:
            return {
                "ok": False,
                "status": "failed",
                "message": str(exc),
                "trace": trace | {"error": "protocol_error"},
            }

        remote_task_id = self._extract_remote_task_id(result, binding.remote_id_field)
        if remote_task_id and binding.supports_remote_status:
            return {
                "ok": True,
                "status": "running",
                "message": f"{self.provider_name} task submitted",
                "trace": trace
                | {
                    "mcp_handshake": handshake.get("server") or handshake.get("result") or "ok",
                    "tool_name": result.tool_name,
                    "mcp_request_id": result.request_id,
                    "mcp_run_id": None,
                    "mcp_remote_task_id": remote_task_id,
                    "mcp_status_strategy": "tool_polling",
                    "last_protocol_state": result.output.get("status", result.status),
                    "mcp_result_preview": result.output.get("message")
                    or result.content[0].get("text")
                    if result.content and isinstance(result.content[0], dict)
                    else None,
                    "mcp_sync_completed": False,
                },
            }

        return {
            "ok": True,
            "status": "running",
            "message": f"{self.provider_name} task started",
            "trace": trace
            | {
                "mcp_handshake": handshake.get("server") or handshake.get("result") or "ok",
                "tool_name": result.tool_name,
                "mcp_request_id": result.request_id,
                "mcp_run_id": result.run_id,
                "last_protocol_state": result.status,
                "mcp_result_preview": self._extract_remote_message(result),
                "mcp_result_output": result.output if result.run_id is None else None,
                "mcp_sync_completed": result.run_id is None and result.status == "completed",
            },
        }

    def check_status(self, task: AgentTask) -> dict[str, Any]:
        trace = task.trace or {}
        if trace.get("mcp_status_strategy") == "tool_polling":
            return self._check_remote_task_status(task, trace)
        run_id = trace.get("mcp_run_id")
        if not run_id and trace.get("mcp_sync_completed"):
            return {
                "ok": True,
                "status": "completed",
                "message": trace.get("mcp_result_preview") or f"{self.provider_name} task completed",
                "trace": {
                    "last_protocol_state": "completed",
                },
            }
        if not run_id:
            return {
                "ok": False,
                "status": "failed",
                "message": "Task trace is missing mcp_run_id",
            }

        try:
            status = self._get_client().get_run_status(
                str(run_id),
                correlation_id=trace.get("correlation_id"),
            )
        except MCPClientError as exc:
            return {
                "ok": False,
                "status": "failed",
                "message": str(exc),
                "trace": {"last_protocol_state": "status_error"},
            }

        mapped_status = _map_mcp_status_to_task_state(status.status)
        return {
            "ok": True,
            "status": mapped_status,
            "message": status.message or f"{self.provider_name} task is {mapped_status}",
            "trace": {
                "last_protocol_state": status.status,
                "mcp_run_id": status.run_id,
            },
        }

    def _check_remote_task_status(self, task: AgentTask, trace: dict[str, Any]) -> dict[str, Any]:
        remote_task_id = trace.get("mcp_remote_task_id")
        if not remote_task_id:
            return {
                "ok": False,
                "status": "failed",
                "message": "Task trace is missing mcp_remote_task_id",
            }

        try:
            config = get_mcp_server_config(self.server_family)
            binding = resolve_task_binding(
                server_family=self.server_family,
                config=config,
                base_arguments=self._build_arguments(task),
                remote_task_id=str(remote_task_id),
            )
            if binding.status_call is None:
                return {
                    "ok": False,
                    "status": "failed",
                    "message": "Provider does not define a remote status tool",
                }
            result = self._get_client().invoke_tool(
                tool_name=binding.status_call.tool_name,
                arguments=binding.status_call.arguments,
                correlation_id=trace.get("correlation_id") or str(uuid.uuid4()),
            )
        except MCPClientError as exc:
            return {
                "ok": False,
                "status": "failed",
                "message": str(exc),
                "trace": {"last_protocol_state": "status_error"},
            }

        protocol_status = self._extract_remote_status(result)
        return {
            "ok": True,
            "status": _map_mcp_status_to_task_state(protocol_status),
            "message": self._extract_remote_message(result)
            or f"{self.provider_name} task is {_map_mcp_status_to_task_state(protocol_status)}",
            "trace": {
                "last_protocol_state": protocol_status,
                "mcp_remote_task_id": remote_task_id,
            },
        }

    def cancel_task(self, task: AgentTask) -> dict[str, Any]:
        trace = task.trace or {}
        if trace.get("mcp_status_strategy") == "tool_polling":
            return self._cancel_remote_task(task, trace)
        run_id = (task.trace or {}).get("mcp_run_id")
        if not run_id:
            return {
                "ok": False,
                "status": "failed",
                "message": "Task trace is missing mcp_run_id",
            }

        try:
            self._get_client().cancel_run(
                str(run_id),
                correlation_id=(task.trace or {}).get("correlation_id"),
            )
        except MCPClientError as exc:
            return {
                "ok": False,
                "status": "failed",
                "message": str(exc),
            }

        return {
            "ok": True,
            "status": "failed",
            "message": "Task cancelled",
            "trace": {
                "last_protocol_state": "cancelled",
                "mcp_run_id": run_id,
            },
        }

    def _cancel_remote_task(self, task: AgentTask, trace: dict[str, Any]) -> dict[str, Any]:
        remote_task_id = trace.get("mcp_remote_task_id")
        if not remote_task_id:
            return {
                "ok": False,
                "status": "failed",
                "message": "Task trace is missing mcp_remote_task_id",
            }

        try:
            config = get_mcp_server_config(self.server_family)
            binding = resolve_task_binding(
                server_family=self.server_family,
                config=config,
                base_arguments=self._build_arguments(task),
                remote_task_id=str(remote_task_id),
            )
            if binding.cancel_call is None:
                return {
                    "ok": False,
                    "status": "failed",
                    "message": "Provider does not define a remote cancel tool",
                }
            self._get_client().invoke_tool(
                tool_name=binding.cancel_call.tool_name,
                arguments=binding.cancel_call.arguments,
                correlation_id=trace.get("correlation_id") or str(uuid.uuid4()),
            )
        except MCPClientError as exc:
            return {
                "ok": False,
                "status": "failed",
                "message": str(exc),
            }

        return {
            "ok": True,
            "status": "failed",
            "message": "Task cancelled",
            "trace": {
                "last_protocol_state": "cancelled",
                "mcp_remote_task_id": remote_task_id,
            },
        }

    def _extract_remote_task_id(
        self,
        result: MCPToolInvocationResult,
        field_name: str | None,
    ) -> str | None:
        if not field_name:
            return None
        value = result.output.get(field_name)
        if value is None:
            value = result.output.get("result", {}).get(field_name) if isinstance(result.output.get("result"), dict) else None
        if value is None:
            return None
        return str(value)

    def _extract_remote_status(self, result: MCPToolInvocationResult) -> str:
        for key in ("status", "task_status", "state"):
            value = result.output.get(key)
            if isinstance(value, str) and value.strip():
                return value.strip().lower()
        task = result.output.get("task")
        if isinstance(task, dict):
            for key in ("status", "state"):
                value = task.get(key)
                if isinstance(value, str) and value.strip():
                    return value.strip().lower()
        summary = result.output.get("summary")
        if isinstance(summary, dict):
            status_value = summary.get("status")
            if isinstance(status_value, str) and status_value.strip():
                return status_value.strip().lower()
        return result.status

    def _extract_remote_message(self, result: MCPToolInvocationResult) -> str | None:
        for key in ("message", "detail"):
            value = result.output.get(key)
            if isinstance(value, str) and value.strip():
                return value
        if result.content and isinstance(result.content[0], dict):
            text = result.content[0].get("text")
            if isinstance(text, str) and text.strip():
                return text
        return None


class IPFSDatasetsMCPAgentProvider(MCPAgentProvider):
    """MCP-backed provider for ipfs_datasets_py server tasks."""

    provider_name = "ipfs_datasets_mcp"
    server_family = "ipfs_datasets"


class IPFSKitMCPAgentProvider(MCPAgentProvider):
    """MCP-backed provider for ipfs_kit_py server tasks."""

    provider_name = "ipfs_kit_mcp"
    server_family = "ipfs_kit"


class IPFSAccelerateMCPAgentProvider(MCPAgentProvider):
    """MCP-backed provider for ipfs_accelerate_py server tasks."""

    provider_name = "ipfs_accelerate_mcp"
    server_family = "ipfs_accelerate"


def get_provider(provider_name: str) -> AgentProvider:
    """Get an agent provider by name.

    For the mock provider, returns a singleton instance to maintain state across calls.
    For other providers, creates new instances.

    Args:
        provider_name: Name of the provider
            (copilot, copilot_cli, custom, mock, github_issue_dispatch).

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
        "copilot_cli": CopilotCLIAgentProvider,
        "custom": CustomAgentProvider,
        "github_issue_dispatch": GitHubIssueDispatchProvider,
        "ipfs_datasets_mcp": IPFSDatasetsMCPAgentProvider,
        "ipfs_kit_mcp": IPFSKitMCPAgentProvider,
        "ipfs_accelerate_mcp": IPFSAccelerateMCPAgentProvider,
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


def _extract_target_number(target_ref: str | None) -> int | None:
    """Extract a numeric item identifier from refs like owner/repo#123."""
    if not target_ref:
        return None

    match = re.search(r"#(\d+)$", target_ref)
    if not match:
        return None

    return int(match.group(1))
