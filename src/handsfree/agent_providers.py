"""Agent provider abstraction for task execution.

Defines the interface for agent providers and includes stub implementations
for copilot and custom agents.
"""

import json
import logging
import os
from datetime import UTC, datetime
from pathlib import Path
import shutil
import subprocess
import re
import uuid
from abc import ABC, abstractmethod
from functools import lru_cache
from typing import Any

from handsfree.cli.executor import CLIExecutor
from handsfree.cli.parsers import parse_output
from handsfree.commands.profiles import Profile, ProfileConfig
from handsfree.config import get_meta_glasses_display_widget_config
from handsfree.db.agent_tasks import AgentTask
from handsfree.ipfs_datasets_routers import get_embeddings_router
from handsfree.ipfs_kit_adapters import get_ipfs_kit_adapter
from handsfree.metrics import get_metrics_collector
from handsfree.meta_glasses_display_widget_contract import (
    DISPLAY_WIDGET_ACTION_CONTRACT,
    DISPLAY_WIDGET_ACTION_DEFINITIONS,
)
from handsfree.mcp import (
    MCPClient,
    MCPClientError,
    MCPConfigurationError,
    MCPTaskBinding,
    MCPToolInvocationResult,
    build_result_envelope,
    build_result_envelope_from_invocation,
    envelope_to_trace,
    get_mcp_server_config,
    is_mcp_provider_enabled,
    resolve_task_binding,
)

logger = logging.getLogger(__name__)
CLI_DETECTION_TIMEOUT_SECONDS = 2
WEARABLES_MOBILE_BASE_ACTIONS: tuple[dict[str, str], ...] = (
    {
        "id": "mobile_open_wearables_diagnostics",
        "label": "Open Diagnostics",
        "phrase": "open wearables bridge diagnostics",
    },
    {
        "id": "mobile_reconnect_wearables_target",
        "label": "Reconnect Target",
        "phrase": "reconnect the selected wearables target",
    },
    {
        "id": "mobile_render_wearables_display_test",
        "label": "Render Display Test",
        "phrase": "render a wearables display test card",
    },
)
WEARABLES_MOBILE_CLEAR_DISPLAY_ACTION = {
    "id": "mobile_clear_wearables_display",
    "label": "Clear Display",
    "phrase": "clear the wearables display",
}
WEARABLES_MOBILE_PLAY_DISPLAY_VIDEO_ACTION = {
    "id": "mobile_play_wearables_display_video",
    "label": "Play Display Video",
    "phrase": "play a wearables display video",
}
WEARABLES_MOBILE_RESET_DISPLAY_ACTION = {
    "id": "mobile_reset_wearables_display_session",
    "label": "Reset Display Session",
    "phrase": "reset the wearables display session",
}


def _nonempty_string(value: Any) -> str | None:
    if isinstance(value, str) and value.strip():
        return value.strip()
    return None


def _first_nonempty_string(*values: Any) -> str | None:
    for value in values:
        normalized = _nonempty_string(value)
        if normalized is not None:
            return normalized
    return None


def _record_or_empty(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _normalize_display_widget_policy_decision(policy_decision: Any) -> dict[str, Any] | None:
    """Normalize HandsFree and Swissknife policy decisions into one wire shape."""
    if policy_decision is None:
        return None

    raw_reasons: Any = None
    policy_id: str | None = None
    source: str | None = "handsfree"
    if isinstance(policy_decision, dict):
        raw_outcome = (
            policy_decision.get("outcome")
            or policy_decision.get("decision")
            or policy_decision.get("policy_outcome")
        )
        raw_reasons = policy_decision.get("reasons", policy_decision.get("reason"))
        policy_id = _nonempty_string(policy_decision.get("policy_id"))
        source = _nonempty_string(policy_decision.get("source")) or source
    else:
        raw_outcome = policy_decision

    outcome = str(raw_outcome or "").strip().lower()
    outcome = {
        "allow": "permit",
        "allowed": "permit",
        "approved": "permit",
        "confirm": "require_confirmation",
        "confirmation": "require_confirmation",
        "needs_confirmation": "require_confirmation",
        "require-confirmation": "require_confirmation",
        "required_confirmation": "require_confirmation",
        "policy_denied": "deny",
        "denied": "deny",
    }.get(outcome, outcome)
    if outcome not in {"permit", "deny", "require_confirmation"}:
        return None

    reasons: list[str] = []
    if isinstance(raw_reasons, list):
        reasons = [str(reason) for reason in raw_reasons if str(reason).strip()]
    elif isinstance(raw_reasons, str) and raw_reasons.strip():
        reasons = [raw_reasons.strip()]

    normalized: dict[str, Any] = {"outcome": outcome}
    if reasons:
        normalized["reasons"] = reasons
    if policy_id:
        normalized["policy_id"] = policy_id
    if source:
        normalized["source"] = source
    return normalized


def build_meta_glasses_display_widget_action_items(
    *,
    descriptor_cid: str,
    widget_cid: str,
    orb_receipt_cid: str,
    policy_decision: dict[str, Any] | str,
    widget_id: str,
    correlation_id: str,
    interface_cid: str | None = None,
    request_id: str | None = None,
    issued_at: str | None = None,
    state: dict[str, Any] | None = None,
    patch: dict[str, Any] | None = None,
    manifest: dict[str, Any] | None = None,
    focus: dict[str, Any] | None = None,
    activated_action_id: str | None = None,
    video: dict[str, Any] | None = None,
    subscription: dict[str, Any] | None = None,
    fallback: dict[str, Any] | None = None,
) -> list[dict[str, Any]]:
    """Build local mobile action items for Meta glasses display widget operations."""
    required_values = {
        "descriptor_cid": _nonempty_string(descriptor_cid),
        "widget_cid": _nonempty_string(widget_cid),
        "orb_receipt_cid": _nonempty_string(orb_receipt_cid),
        "widget_id": _nonempty_string(widget_id),
        "correlation_id": _nonempty_string(correlation_id),
    }
    missing = [key for key, value in required_values.items() if value is None]
    normalized_policy = _normalize_display_widget_policy_decision(policy_decision)
    if normalized_policy is None:
        missing.append("policy_decision")
    if missing:
        raise ValueError(f"Missing display widget action contract fields: {', '.join(missing)}")

    resolved_issued_at = issued_at or _now_iso()
    resolved_interface_cid = _nonempty_string(interface_cid) or required_values["descriptor_cid"]
    action_items: list[dict[str, Any]] = []
    for definition in DISPLAY_WIDGET_ACTION_DEFINITIONS:
        payload: dict[str, Any] = {
            "contract": DISPLAY_WIDGET_ACTION_CONTRACT,
            "type": definition["id"],
            "action": definition["action"],
            "operation": definition["operation"],
            "descriptor_cid": required_values["descriptor_cid"],
            "interface_cid": resolved_interface_cid,
            "widget_id": required_values["widget_id"],
            "widget_cid": required_values["widget_cid"],
            "orb_receipt_cid": required_values["orb_receipt_cid"],
            "policy_decision": normalized_policy,
            "correlation_id": required_values["correlation_id"],
            "issued_at": resolved_issued_at,
        }
        if request_id:
            payload["request_id"] = request_id
        if definition["action"] in {"render", "play_video", "subscribe_updates"}:
            if state:
                payload["state"] = state
            if manifest:
                payload["manifest"] = manifest
        elif definition["action"] == "update" and patch:
            payload["patch"] = patch
        elif definition["action"] == "focus":
            payload["focus"] = focus or {"direction": "next"}
        elif definition["action"] == "activate" and activated_action_id:
            payload["activated_action_id"] = activated_action_id
        if definition["action"] == "play_video" and video:
            payload["video"] = video
        elif definition["action"] == "subscribe_updates" and subscription:
            payload["subscription"] = subscription
        if fallback:
            payload["fallback"] = fallback

        params = {
            "descriptor_cid": required_values["descriptor_cid"],
            "widget_cid": required_values["widget_cid"],
            "orb_receipt_cid": required_values["orb_receipt_cid"],
            "policy_decision": normalized_policy,
            "display_widget_action": payload,
        }
        action_items.append(
            {
                "id": definition["id"],
                "label": definition["label"],
                "phrase": definition["phrase"],
                "params": params,
                "mobile_payload": payload,
            }
        )
    return action_items


def _display_widget_action_items_from_context(
    client_context: dict[str, Any],
    receipt: dict[str, Any],
    envelope: Any,
) -> list[dict[str, Any]]:
    mobile_action = _record_or_empty(receipt.get("mobile_action"))
    artifact_refs = getattr(envelope, "artifact_refs", None)
    trace = getattr(envelope, "trace", None)
    descriptor_cid = _first_nonempty_string(
        client_context.get("display_widget_descriptor_cid"),
        client_context.get("display_widget_interface_cid"),
        receipt.get("descriptor_cid"),
        receipt.get("interface_cid"),
        receipt.get("source_interface_cid"),
        mobile_action.get("descriptor_cid"),
        mobile_action.get("interface_cid"),
    )
    widget_cid = _first_nonempty_string(
        client_context.get("display_widget_cid"),
        receipt.get("widget_cid"),
        mobile_action.get("widget_cid"),
    )
    orb_receipt_cid = _first_nonempty_string(
        client_context.get("display_widget_orb_receipt_cid"),
        client_context.get("display_widget_receipt_cid"),
        receipt.get("orb_receipt_cid"),
        receipt.get("receipt_cid"),
        getattr(artifact_refs, "receipt_ref", None),
    )
    widget_id = _first_nonempty_string(
        client_context.get("display_widget_id"),
        receipt.get("widget_id"),
        mobile_action.get("widget_id"),
    )
    correlation_id = _first_nonempty_string(
        client_context.get("display_widget_correlation_id"),
        receipt.get("correlation_id"),
        mobile_action.get("correlation_id"),
        getattr(trace, "request_id", None),
    )
    policy_decision = (
        client_context.get("display_widget_policy_decision")
        or receipt.get("policy_decision")
        or receipt.get("policy_outcome")
        or mobile_action.get("policy_decision")
    )
    if not all([descriptor_cid, widget_cid, orb_receipt_cid, widget_id, correlation_id]):
        return []

    display_widget_config = get_meta_glasses_display_widget_config()
    if not display_widget_config.enabled:
        return []

    normalized_policy = _normalize_display_widget_policy_decision(policy_decision)
    if display_widget_config.require_trusted_descriptor:
        if normalized_policy is None:
            get_metrics_collector().record_display_widget_policy_denial(
                reason="missing_or_invalid_policy_decision",
            )
            return []
        if normalized_policy["outcome"] != "permit":
            get_metrics_collector().record_display_widget_policy_denial(
                reason=normalized_policy["outcome"],
            )
            return []

    activated_action = _record_or_empty(receipt.get("activated_action"))
    activated_action_id = _first_nonempty_string(
        client_context.get("display_widget_activated_action_id"),
        receipt.get("activated_action_id"),
        activated_action.get("action_id"),
        activated_action.get("backend_action_id"),
        mobile_action.get("activated_action_id"),
    )
    fallback = (
        _record_or_empty(receipt.get("fallback"))
        or _record_or_empty(mobile_action.get("fallback"))
        or None
    )
    if not display_widget_config.allow_webapp_fallback:
        fallback = None

    try:
        return build_meta_glasses_display_widget_action_items(
            descriptor_cid=descriptor_cid,
            interface_cid=_first_nonempty_string(receipt.get("interface_cid"), mobile_action.get("interface_cid")),
            widget_cid=widget_cid,
            orb_receipt_cid=orb_receipt_cid,
            policy_decision=normalized_policy or policy_decision,
            widget_id=widget_id,
            correlation_id=correlation_id,
            request_id=_first_nonempty_string(receipt.get("request_id"), mobile_action.get("request_id")),
            issued_at=_first_nonempty_string(receipt.get("issued_at"), mobile_action.get("issued_at")),
            state=_record_or_empty(mobile_action.get("state")) or None,
            patch=_record_or_empty(receipt.get("patch")) or _record_or_empty(mobile_action.get("patch")) or None,
            manifest=(
                _record_or_empty(receipt.get("manifest"))
                or _record_or_empty(mobile_action.get("manifest"))
                or None
            ),
            focus=_record_or_empty(receipt.get("focus")) or _record_or_empty(mobile_action.get("focus")) or None,
            activated_action_id=activated_action_id,
            video=_record_or_empty(receipt.get("video")) or _record_or_empty(mobile_action.get("video")) or None,
            subscription=(
                _record_or_empty(receipt.get("subscription"))
                or _record_or_empty(mobile_action.get("subscription"))
                or None
            ),
            fallback=fallback,
        )
    except ValueError:
        return []


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
        """Start a Copilot CLI task through the shared AI request contract."""
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
        repo = _extract_target_repo(task.target_ref)
        if task.target_type == "pr" and pr_number:
            from handsfree.ai.capabilities import execute_ai_request
            from handsfree.ai.models import AIRequestContext, AICapabilityRequest
            from handsfree.ai.policy import build_policy_resolution
            from handsfree.models import AIWorkflow

            task_trace = getattr(task, "trace", None) or {}
            capability_id = _select_delegated_capability_with_trace(task.instruction, task_trace)
            requested_workflow = _infer_delegated_requested_workflow_with_trace(
                task.instruction, task_trace
            )
            request = AICapabilityRequest(
                capability_id=capability_id,
                context=AIRequestContext(repo=repo, pr_number=pr_number),
            )
            try:
                execution = execute_ai_request(
                    request,
                    cli_executor=executor,
                    profile_config=ProfileConfig.for_profile(Profile.DEFAULT),
                )
                result = execution.output
                if isinstance(result, dict):
                    result_trace = result.get("trace", {})
                    trace.update(
                        {
                            "capability_id": execution.capability_id,
                            "execution_mode": execution.execution_mode.value,
                            "command_id": result_trace.get("command_id"),
                            "source": result_trace.get("source"),
                            "duration_ms": result_trace.get("duration_ms"),
                            "preview": result.get("spoken_text") or result.get("summary"),
                            "policy_resolution": build_policy_resolution(
                                requested_workflow=requested_workflow,
                                resolved_workflow={
                                    "github.pr.rag_summary": AIWorkflow.PR_RAG_SUMMARY,
                                    "github.pr.accelerated_summary": AIWorkflow.ACCELERATED_PR_SUMMARY,
                                    "github.check.failure_rag_explain": AIWorkflow.FAILURE_RAG_EXPLAIN,
                                    "github.check.accelerated_failure_explain": AIWorkflow.ACCELERATED_FAILURE_EXPLAIN,
                                }.get(execution.capability_id, requested_workflow),
                                requested_capability_id=None,
                                resolved_capability_id=execution.capability_id,
                            ).model_dump(mode="json")
                            if requested_workflow is not None
                            else None,
                        }
                    )
                    return {
                        "ok": True,
                        "status": "running",
                        "message": result.get("spoken_text", "[STUB] Copilot CLI task started"),
                        "trace": trace,
                    }
            except Exception:
                logger.warning(
                    "Failed to execute shared AI request for Copilot task %s",
                    task.id,
                    exc_info=True,
                )
                if capability_id.startswith("copilot.pr."):
                    raw_result = executor.execute(
                        _command_id_for_copilot_capability(capability_id),
                        "copilot",
                        pr_number=pr_number,
                    )
                    if raw_result.ok:
                        preview = raw_result.stdout.strip().splitlines()[0] if raw_result.stdout.strip() else ""
                        trace.update(
                            {
                                "capability_id": capability_id,
                                "command_id": raw_result.command_id,
                                "source": raw_result.source,
                                "duration_ms": raw_result.duration_ms,
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
            "mcp_execution_mode",
            "mcp_pin_action",
            "mcp_preferred_execution_mode",
            "mcp_seed_url",
            "mcp_texts",
            "provider_label",
        ):
            value = trace.get(key)
            if value is not None:
                arguments[key] = value
        return arguments

    def _decorate_envelope_for_task(
        self,
        task: AgentTask,
        envelope,
    ):
        trace = task.trace or {}
        if (
            self.provider_name != "ipfs_accelerate_mcp"
            or trace.get("wearables_bridge_requested_workflow") != "wearables_bridge_connectivity"
        ):
            return envelope
        return _build_wearables_bridge_connectivity_envelope(task, envelope)

    def start_task(self, task: AgentTask) -> dict[str, Any]:
        daemon_result = _todo_daemon_status_result(task)
        if daemon_result is not None:
            return daemon_result

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
            local_result = self._execute_local_binding(task, binding)
            if local_result is not None:
                return {
                    "ok": True,
                    "status": "running",
                    "message": local_result["message"],
                    "trace": trace | local_result["trace"],
                }
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
            envelope = build_result_envelope_from_invocation(
                provider_name=self.provider_name,
                server_family=self.server_family,
                capability_id=binding.capability_id,
                execution_mode=binding.execution_mode or "mcp_remote",
                invocation=result,
                remote_task_id=remote_task_id,
                status="running",
            )
            envelope = self._decorate_envelope_for_task(task, envelope)
            return {
                "ok": True,
                "status": "running",
                "message": envelope.spoken_text,
                "trace": trace
                | {
                    "mcp_handshake": handshake.get("server") or handshake.get("result") or "ok",
                    "mcp_capability": binding.capability_id,
                    "mcp_execution_mode": binding.execution_mode or "mcp_remote",
                    "mcp_started_at": _now_iso(),
                    "mcp_timeout_s": config.timeout_s,
                    "mcp_poll_interval_s": config.poll_interval_s,
                    "mcp_status_strategy": "tool_polling",
                    "mcp_sync_completed": False,
                }
                | envelope_to_trace(envelope),
            }

        envelope = build_result_envelope_from_invocation(
            provider_name=self.provider_name,
            server_family=self.server_family,
            capability_id=binding.capability_id,
            execution_mode=binding.execution_mode or "mcp_remote",
            invocation=result,
        )
        envelope = self._decorate_envelope_for_task(task, envelope)
        return {
            "ok": True,
            "status": "running",
            "message": envelope.spoken_text,
            "trace": trace
            | {
                "mcp_handshake": handshake.get("server") or handshake.get("result") or "ok",
                "mcp_capability": binding.capability_id,
                "mcp_execution_mode": binding.execution_mode or "mcp_remote",
                "mcp_started_at": _now_iso(),
                "mcp_timeout_s": config.timeout_s,
                "mcp_poll_interval_s": config.poll_interval_s,
                "mcp_sync_completed": result.run_id is None and result.status == "completed",
            }
            | envelope_to_trace(envelope)
            | {
                "mcp_result_output": result.output if result.run_id is None else None,
            },
        }

    def check_status(self, task: AgentTask) -> dict[str, Any]:
        daemon_result = _todo_daemon_status_result(task)
        if daemon_result is not None:
            return daemon_result

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
        envelope = build_result_envelope(
            provider_name=self.provider_name,
            server_family=self.server_family,
            capability_id=str(trace.get("mcp_capability") or "").strip() or None,
            execution_mode=str(trace.get("mcp_execution_mode") or "mcp_remote"),
            status=mapped_status,
            tool_name=str(trace.get("tool_name") or "") or None,
            spoken_text=status.message,
            structured_output=status.output,
            run_id=status.run_id,
            last_protocol_state=status.status,
        )
        timed_out, elapsed_s, timeout_s = _trace_timeout_state(trace)
        if mapped_status == "running" and timed_out:
            timeout_summary = (
                f"{self.provider_name} task timed out after {timeout_s}s."
                if timeout_s is not None
                else f"{self.provider_name} task timed out."
            )
            timeout_envelope = build_result_envelope(
                provider_name=self.provider_name,
                server_family=self.server_family,
                capability_id=str(trace.get("mcp_capability") or "").strip() or None,
                execution_mode=str(trace.get("mcp_execution_mode") or "mcp_remote"),
                status="failed",
                tool_name=str(trace.get("tool_name") or "") or None,
                spoken_text=timeout_summary,
                summary=timeout_summary,
                structured_output={"status": "timeout", "timeout": True, "elapsed_s": elapsed_s},
                request_id=str(trace.get("mcp_request_id") or "") or None,
                run_id=status.run_id,
                last_protocol_state="timeout",
            )
            timeout_envelope = self._decorate_envelope_for_task(task, timeout_envelope)
            return {
                "ok": False,
                "status": "failed",
                "message": timeout_envelope.spoken_text,
                "trace": envelope_to_trace(timeout_envelope)
                | {"mcp_result_output": timeout_envelope.structured_output},
            }
        envelope = self._decorate_envelope_for_task(task, envelope)
        return {
            "ok": True,
            "status": mapped_status,
            "message": envelope.spoken_text,
            "trace": envelope_to_trace(envelope)
            | {
                "mcp_result_output": status.output if mapped_status == "completed" else None,
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
        mapped_status = _map_mcp_status_to_task_state(protocol_status)
        envelope = build_result_envelope_from_invocation(
            provider_name=self.provider_name,
            server_family=self.server_family,
            capability_id=str(trace.get("mcp_capability") or "").strip() or None,
            execution_mode=str(trace.get("mcp_execution_mode") or "mcp_remote"),
            invocation=result,
            remote_task_id=str(remote_task_id),
            status=mapped_status,
        )
        timed_out, elapsed_s, timeout_s = _trace_timeout_state(trace)
        if mapped_status == "running" and timed_out:
            timeout_summary = (
                f"{self.provider_name} task timed out after {timeout_s}s."
                if timeout_s is not None
                else f"{self.provider_name} task timed out."
            )
            timeout_envelope = build_result_envelope(
                provider_name=self.provider_name,
                server_family=self.server_family,
                capability_id=str(trace.get("mcp_capability") or "").strip() or None,
                execution_mode=str(trace.get("mcp_execution_mode") or "mcp_remote"),
                status="failed",
                tool_name=envelope.trace.tool_name,
                spoken_text=timeout_summary,
                summary=timeout_summary,
                structured_output={"status": "timeout", "timeout": True, "elapsed_s": elapsed_s},
                request_id=envelope.trace.request_id,
                remote_task_id=str(remote_task_id),
                last_protocol_state="timeout",
            )
            timeout_envelope = self._decorate_envelope_for_task(task, timeout_envelope)
            return {
                "ok": False,
                "status": "failed",
                "message": timeout_envelope.spoken_text,
                "trace": envelope_to_trace(timeout_envelope)
                | {"mcp_result_output": timeout_envelope.structured_output},
            }
        envelope = self._decorate_envelope_for_task(task, envelope)
        return {
            "ok": True,
            "status": mapped_status,
            "message": envelope.spoken_text,
            "trace": envelope_to_trace(envelope)
            | {
                "mcp_result_output": result.output
                if mapped_status == "completed"
                else None,
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

    def _execute_local_binding(
        self,
        task: AgentTask,
        binding: MCPTaskBinding,
    ) -> dict[str, Any] | None:
        if binding.execution_mode != "direct_import":
            return None

        trace = task.trace or {}
        capability_id = binding.capability_id
        if capability_id == "ipfs_pin":
            cid = str(trace.get("mcp_cid") or "").strip()
            if not cid:
                raise MCPConfigurationError("ipfs_pin requires a CID")

            pin_action = str(trace.get("mcp_pin_action") or "").strip().lower()
            adapter = get_ipfs_kit_adapter()
            if pin_action == "unpin":
                output = adapter.unpin(cid)
                tool_name = "ipfs_kit.unpin"
                preview = f"Unpinned {cid}."
            else:
                output = adapter.pin(cid)
                tool_name = "ipfs_kit.pin"
                preview = f"Pinned {cid}."

            return {
                "message": preview,
                "trace": {
                    "mcp_capability": capability_id,
                    "mcp_execution_mode": "direct_import",
                    "mcp_sync_completed": True,
                }
                | envelope_to_trace(
                    build_result_envelope(
                        provider_name=self.provider_name,
                        server_family=self.server_family,
                        capability_id=capability_id,
                        execution_mode="direct_import",
                        status="completed",
                        tool_name=tool_name,
                        spoken_text=preview,
                        structured_output=output,
                    )
                ),
            }

        if capability_id == "ipfs_add":
            content = str(trace.get("mcp_input") or task.instruction or "").strip()
            if not content:
                raise MCPConfigurationError("ipfs_add requires content to add to IPFS")

            adapter = get_ipfs_kit_adapter()
            output = adapter.add_bytes(content.encode("utf-8"))

            if isinstance(output, str):
                cid = output.strip() or None
                structured_output: Any = {"cid": cid} if cid else {"result": output}
            else:
                structured_output = output
                cid = None
                if isinstance(output, dict):
                    cid = str(
                        output.get("cid")
                        or output.get("Hash")
                        or output.get("hash")
                        or output.get("value")
                        or ""
                    ).strip() or None

            preview = f"Saved content to IPFS as {cid}." if cid else "Saved content to IPFS."
            return {
                "message": preview,
                "trace": {
                    "mcp_capability": capability_id,
                    "mcp_execution_mode": "direct_import",
                    "mcp_sync_completed": True,
                    **({"mcp_cid": cid} if cid else {}),
                }
                | envelope_to_trace(
                    build_result_envelope(
                        provider_name=self.provider_name,
                        server_family=self.server_family,
                        capability_id=capability_id,
                        execution_mode="direct_import",
                        status="completed",
                        tool_name="ipfs_kit.add_bytes",
                        spoken_text=preview,
                        structured_output=structured_output,
                    )
                ),
            }

        if capability_id == "ipfs_cat":
            cid = str(trace.get("mcp_cid") or trace.get("mcp_input") or "").strip()
            if not cid:
                raise MCPConfigurationError("ipfs_cat requires a CID or IPFS path")

            adapter = get_ipfs_kit_adapter()
            output = adapter.cat(cid)
            structured_output = {
                "cid": cid,
                "content": output.decode("utf-8", errors="replace") if isinstance(output, bytes) else output,
            }
            preview = f"Read content from {cid}."
            return {
                "message": preview,
                "trace": {
                    "mcp_capability": capability_id,
                    "mcp_execution_mode": "direct_import",
                    "mcp_sync_completed": True,
                    "mcp_cid": cid,
                }
                | envelope_to_trace(
                    build_result_envelope(
                        provider_name=self.provider_name,
                        server_family=self.server_family,
                        capability_id=capability_id,
                        execution_mode="direct_import",
                        status="completed",
                        tool_name="ipfs_kit.cat",
                        spoken_text=preview,
                        structured_output=structured_output,
                    )
                ),
            }

        if capability_id == "embedding":
            router = get_embeddings_router()
            texts = trace.get("mcp_texts")
            if isinstance(texts, list) and texts:
                output = router.embed_texts([str(text) for text in texts])
                preview = f"Generated embeddings for {len(texts)} texts."
                tool_name = "ipfs_datasets.embed_texts"
            else:
                text = str(trace.get("mcp_input") or task.instruction or "").strip()
                if not text:
                    raise MCPConfigurationError("embedding requires input text")
                output = router.embed_text(text)
                preview = "Generated embedding."
                tool_name = "ipfs_datasets.embed_text"

            return {
                "message": preview,
                "trace": {
                    "mcp_capability": capability_id,
                    "mcp_execution_mode": "direct_import",
                    "mcp_sync_completed": True,
                }
                | envelope_to_trace(
                    build_result_envelope(
                        provider_name=self.provider_name,
                        server_family=self.server_family,
                        capability_id=capability_id,
                        execution_mode="direct_import",
                        status="completed",
                        tool_name=tool_name,
                        spoken_text=preview,
                        structured_output=output,
                    )
                ),
            }

        raise MCPConfigurationError(
            f"Direct execution is not implemented for capability '{capability_id}'"
        )


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


def _now_iso() -> str:
    """Return a UTC ISO-8601 timestamp for MCP trace metadata."""
    return datetime.now(UTC).isoformat()


def _trace_timeout_state(trace: dict[str, Any] | None) -> tuple[bool, int | None, int | None]:
    """Return whether an MCP task has exceeded its configured timeout."""
    normalized_trace = trace or {}
    started_at = normalized_trace.get("mcp_started_at")
    timeout_s = normalized_trace.get("mcp_timeout_s")

    if not isinstance(started_at, str) or not started_at.strip():
        return False, None, None
    if not isinstance(timeout_s, (int, float)) or timeout_s <= 0:
        return False, None, None

    try:
        started = datetime.fromisoformat(started_at.replace("Z", "+00:00"))
    except ValueError:
        return False, None, None

    elapsed_s = max(0, int((datetime.now(UTC) - started).total_seconds()))
    timeout_int = int(timeout_s)
    return elapsed_s > timeout_int, elapsed_s, timeout_int


def _todo_daemon_config(trace: dict[str, Any] | None) -> dict[str, str] | None:
    normalized_trace = trace or {}
    state_path = _first_nonempty_string(
        normalized_trace.get("todo_daemon_state_path"),
        normalized_trace.get("virtual_ai_os_state_path"),
    )
    task_id = _first_nonempty_string(
        normalized_trace.get("todo_daemon_task_id"),
        normalized_trace.get("virtual_ai_os_task_id"),
    )
    if state_path is None or task_id is None:
        return None
    config = {"state_path": state_path, "task_id": task_id}
    events_path = _first_nonempty_string(
        normalized_trace.get("todo_daemon_events_path"),
        normalized_trace.get("virtual_ai_os_events_path"),
    )
    if events_path is not None:
        config["events_path"] = events_path
    return config


def _load_json_record(path: str) -> dict[str, Any]:
    payload = json.loads(Path(path).read_text(encoding="utf-8"))
    return payload if isinstance(payload, dict) else {}


def _load_jsonl_records(path: str | None) -> list[dict[str, Any]]:
    if not path:
        return []
    file_path = Path(path)
    if not file_path.exists():
        return []
    events: list[dict[str, Any]] = []
    for raw_line in file_path.read_text(encoding="utf-8").splitlines():
        raw_line = raw_line.strip()
        if not raw_line:
            continue
        try:
            payload = json.loads(raw_line)
        except json.JSONDecodeError:
            continue
        if isinstance(payload, dict):
            events.append(payload)
    return events


def _todo_daemon_task_title(
    *,
    task_id: str,
    state: dict[str, Any],
    events: list[dict[str, Any]],
    fallback: str | None,
) -> str:
    if state.get("active_task_id") == task_id:
        title = _first_nonempty_string(state.get("active_task_title"))
        if title is not None:
            return title
    for event in reversed(events):
        if str(event.get("task_id") or "") != task_id:
            continue
        title = _first_nonempty_string(event.get("title"))
        if title is not None:
            return title
    return fallback or task_id


def _map_todo_daemon_status_to_task_state(task_id: str, state: dict[str, Any]) -> tuple[str, str]:
    statuses = state.get("task_statuses") if isinstance(state.get("task_statuses"), dict) else {}
    daemon_status = str(statuses.get(task_id) or "").strip().lower()
    active_task_id = _first_nonempty_string(state.get("active_task_id"))
    if daemon_status == "completed":
        return "completed", daemon_status
    if daemon_status in {"blocked", "needs_input"}:
        return "needs_input", daemon_status or "blocked"
    if daemon_status in {"failed", "error"}:
        return "failed", daemon_status
    if active_task_id == task_id:
        return "running", daemon_status or "active"
    if daemon_status in {"ready", "waiting", "todo", "running", "active"}:
        return "running", daemon_status
    return "running", daemon_status or "unknown"


def _todo_daemon_progress_summary(
    *,
    task_id: str,
    title: str,
    mapped_status: str,
    daemon_status: str,
    state: dict[str, Any],
) -> str:
    active_task_id = _first_nonempty_string(state.get("active_task_id"))
    if mapped_status == "completed":
        return f"{task_id} completed: {title}."
    if mapped_status == "needs_input":
        return f"{task_id} is blocked: {title}."
    if active_task_id == task_id:
        return f"{task_id} active in the todo daemon: {title}."
    if daemon_status == "ready":
        return f"{task_id} is ready in the todo daemon: {title}."
    if daemon_status == "waiting":
        return f"{task_id} is waiting on dependencies: {title}."
    return f"{task_id} status is {daemon_status}: {title}."


def _todo_daemon_trace_update(task: AgentTask) -> dict[str, Any] | None:
    config = _todo_daemon_config(task.trace)
    if config is None:
        return None

    state = _load_json_record(config["state_path"])
    events = _load_jsonl_records(config.get("events_path"))
    task_id = config["task_id"]
    mapped_status, daemon_status = _map_todo_daemon_status_to_task_state(task_id, state)
    title = _todo_daemon_task_title(
        task_id=task_id,
        state=state,
        events=events,
        fallback=task.instruction,
    )
    summary = _todo_daemon_progress_summary(
        task_id=task_id,
        title=title,
        mapped_status=mapped_status,
        daemon_status=daemon_status,
        state=state,
    )
    structured_output = {
        "task_id": task_id,
        "title": title,
        "task_status": daemon_status,
        "active_task_id": _first_nonempty_string(state.get("active_task_id")),
        "active_task_title": _first_nonempty_string(state.get("active_task_title")),
        "ready_count": state.get("ready_count"),
        "completed_count": state.get("completed_count"),
        "waiting_count": state.get("waiting_count"),
        "blocked_count": state.get("blocked_count"),
        "recommended_task_id": _first_nonempty_string(state.get("recommended_task_id")),
        "recommended_actions": state.get("recommended_actions")
        if isinstance(state.get("recommended_actions"), list)
        else [],
    }
    return {
        "sync_completed": mapped_status == "completed",
        "todo_daemon_result_envelope": {
            "capability_id": task_id,
            "provider": task.provider,
            "server_family": "ipfs_datasets_todo_daemon",
            "execution_mode": "orchestrated",
            "status": mapped_status,
            "spoken_text": summary,
            "summary": summary,
            "structured_output": structured_output,
            "follow_up_actions": [],
            "artifact_refs": {
                "result_cid": None,
                "receipt_ref": None,
                "event_dag_ref": None,
                "delegation_ref": None,
            },
            "trace": {
                "request_id": None,
                "run_id": None,
                "remote_task_id": task_id,
                "tool_name": "ipfs_datasets.todo_daemon",
                "last_protocol_state": daemon_status,
                "provider_profiles": ["virtual_ai_os"],
            },
        },
        "todo_daemon_result_preview": summary,
        "todo_daemon_result_output": structured_output,
        "todo_daemon_task_id": task_id,
        "todo_daemon_task_title": title,
        "todo_daemon_task_status": daemon_status,
        "todo_daemon_active_task_id": structured_output["active_task_id"],
        "todo_daemon_active_task_title": structured_output["active_task_title"],
        "todo_daemon_ready_count": structured_output["ready_count"],
        "todo_daemon_completed_count": structured_output["completed_count"],
        "todo_daemon_waiting_count": structured_output["waiting_count"],
        "todo_daemon_blocked_count": structured_output["blocked_count"],
        "todo_daemon_last_progress_at": _first_nonempty_string(state.get("last_progress_at")),
    }


def _todo_daemon_status_result(task: AgentTask) -> dict[str, Any] | None:
    trace_update = _todo_daemon_trace_update(task)
    if trace_update is None:
        return None
    envelope = trace_update["todo_daemon_result_envelope"]
    return {
        "ok": True,
        "status": envelope["status"],
        "message": envelope["spoken_text"],
        "trace": trace_update,
    }


def _extract_target_number(target_ref: str | None) -> int | None:
    """Extract a numeric item identifier from refs like owner/repo#123."""
    if not target_ref:
        return None

    match = re.search(r"#(\d+)$", target_ref)
    if not match:
        return None

    return int(match.group(1))


def _extract_target_repo(target_ref: str | None) -> str | None:
    """Extract owner/repo from refs like owner/repo#123."""
    if not target_ref or "#" not in target_ref:
        return None

    repo, _sep, _suffix = target_ref.partition("#")
    return repo or None


def _select_delegated_ai_capability(instruction: str | None) -> str:
    """Map delegated PR instructions onto shared AI capabilities."""
    from handsfree.ai.policy import get_ai_backend_policy

    normalized = (instruction or "").lower()
    policy = get_ai_backend_policy()
    if "fail" in normalized or "check" in normalized:
        if policy.failure_backend == "accelerated":
            return "github.check.accelerated_failure_explain"
        if policy.failure_backend == "composite":
            return "github.check.failure_rag_explain"
        return "copilot.pr.failure_explain"
    if "diff" in normalized:
        return "copilot.pr.diff_summary"
    if "summary" in normalized or "summarize" in normalized:
        if policy.summary_backend == "accelerated":
            return "github.pr.accelerated_summary"
        return "github.pr.rag_summary"
    return "copilot.pr.explain"


def _infer_delegated_requested_workflow(instruction: str | None):
    """Infer the requested workflow alias for delegated PR tasks, if any."""
    from handsfree.models import AIWorkflow

    normalized = (instruction or "").lower()
    if "fail" in normalized or "check" in normalized:
        return AIWorkflow.FAILURE_RAG_EXPLAIN
    if "summary" in normalized or "summarize" in normalized:
        return AIWorkflow.PR_RAG_SUMMARY
    return None


def _select_delegated_capability_with_trace(
    instruction: str | None, trace: dict[str, Any] | None
) -> str:
    """Prefer explicit orchestration hints from task trace before text heuristics."""
    normalized_trace = trace or {}
    if normalized_trace.get("wearables_bridge_requested_workflow") == "wearables_bridge_connectivity":
        return "workflow"
    trace_capability = normalized_trace.get("mcp_capability")
    if isinstance(trace_capability, str) and trace_capability.strip():
        return trace_capability
    return _select_delegated_ai_capability(instruction)


def _infer_delegated_requested_workflow_with_trace(
    instruction: str | None, trace: dict[str, Any] | None
):
    """Prefer explicit workflow hints from task trace before text heuristics."""
    normalized_trace = trace or {}
    trace_workflow = normalized_trace.get("wearables_bridge_requested_workflow")
    if isinstance(trace_workflow, str) and trace_workflow.strip():
        return trace_workflow
    return _infer_delegated_requested_workflow(instruction)


def _build_wearables_bridge_connectivity_envelope(task: AgentTask, envelope):
    """Wrap a generic MCP workflow result in a wearables connectivity receipt."""
    trace = task.trace or {}
    client_context = trace.get("client_context") if isinstance(trace.get("client_context"), dict) else {}
    device_id = client_context.get("device_id")
    device_name = client_context.get("device_name") or device_id or "wearable target"
    target_state = client_context.get("target_connection_state") or "connected"
    target_last_seen_at = client_context.get("target_last_seen_at")
    target_rssi = client_context.get("target_rssi")
    raw_display_capable = client_context.get("display_capable")
    if isinstance(raw_display_capable, bool):
        display_capable = raw_display_capable
    elif isinstance(raw_display_capable, int):
        display_capable = raw_display_capable == 1
    elif isinstance(raw_display_capable, float):
        # Only the numeric true sentinel (1/1.0) is treated as display-capable.
        display_capable = raw_display_capable.is_integer() and int(raw_display_capable) == 1
    elif isinstance(raw_display_capable, str):
        display_capable = raw_display_capable.strip().lower() in {"1", "true", "yes", "on"}
    else:
        display_capable = False
    display_connection_state = client_context.get("display_connection_state")
    if not isinstance(display_connection_state, str) or not display_connection_state.strip():
        display_connection_state = "unknown"
    display_last_action = client_context.get("display_last_action")
    if not isinstance(display_last_action, str) or not display_last_action.strip():
        display_last_action = None
    display_last_status = client_context.get("display_last_status")
    if not isinstance(display_last_status, str) or not display_last_status.strip():
        display_last_status = None
    receipt = envelope.structured_output if isinstance(envelope.structured_output, dict) else {}

    if envelope.status == "completed":
        summary = f"Wearables bridge connectivity receipt captured for {device_name}."
    elif envelope.status == "failed" and receipt.get("timeout"):
        summary = f"Wearables bridge connectivity workflow timed out for {device_name}."
    elif envelope.status == "running":
        summary = f"Wearables bridge connectivity workflow running for {device_name}."
    elif envelope.status == "failed":
        summary = f"Wearables bridge connectivity workflow failed for {device_name}."
    else:
        summary = f"Wearables bridge connectivity workflow needs input for {device_name}."

    structured_output = {
        "workflow": "wearables_bridge_connectivity",
        "device_id": device_id,
        "device_name": device_name,
        "target_connection_state": target_state,
        "target_last_seen_at": target_last_seen_at,
        "target_rssi": target_rssi,
        "provider": envelope.provider,
        "execution_mode": envelope.execution_mode,
        "status": envelope.status,
        "display": {
            "capable": display_capable,
            "connection_state": display_connection_state,
            "last_action": display_last_action,
            "last_status": display_last_status,
        },
        "receipt": envelope.structured_output,
    }
    mobile_actions: list[dict[str, Any]] = list(WEARABLES_MOBILE_BASE_ACTIONS)
    if display_capable:
        mobile_actions.extend(
            [
                WEARABLES_MOBILE_CLEAR_DISPLAY_ACTION,
                WEARABLES_MOBILE_PLAY_DISPLAY_VIDEO_ACTION,
                WEARABLES_MOBILE_RESET_DISPLAY_ACTION,
            ]
        )
        mobile_actions.extend(
            _display_widget_action_items_from_context(client_context, receipt, envelope)
        )

    follow_up_actions = [
        *mobile_actions,
        {
            "id": "agent_status",
            "label": "Check Task",
            "phrase": "check the wearables bridge task",
        }
    ]
    if envelope.artifact_refs.result_cid:
        follow_up_actions.append(
            {
                "id": "read_cid",
                "label": "Read Receipt",
                "phrase": "read the wearables receipt",
            }
        )

    return build_result_envelope(
        provider_name=envelope.provider,
        server_family=envelope.server_family,
        capability_id="workflow",
        execution_mode=envelope.execution_mode,
        status=envelope.status,
        tool_name=envelope.trace.tool_name,
        spoken_text=summary,
        summary=summary,
        structured_output=structured_output,
        request_id=envelope.trace.request_id,
        run_id=envelope.trace.run_id,
        remote_task_id=envelope.trace.remote_task_id,
        last_protocol_state=envelope.trace.last_protocol_state,
        artifact_refs=envelope.artifact_refs,
        provider_profiles=envelope.trace.provider_profiles,
        follow_up_actions=follow_up_actions,
        needs_input_schema=envelope.needs_input_schema,
    )


def _command_id_for_copilot_capability(capability_id: str) -> str:
    """Map shared Copilot capabilities back to raw CLI command ids for fallback."""
    mapping = {
        "copilot.pr.explain": "gh.copilot.explain_pr",
        "copilot.pr.diff_summary": "gh.copilot.summarize_diff",
        "copilot.pr.failure_explain": "gh.copilot.explain_failure",
    }
    return mapping.get(capability_id, "gh.copilot.explain_pr")
