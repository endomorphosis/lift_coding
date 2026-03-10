"""Command router and response composer."""

import json
import logging
import os
from typing import Any

import duckdb

from handsfree.agents.results_views import resolve_result_query
from handsfree.ai import (
    AIRequestContext,
    AICapabilityRequest,
    build_policy_resolution,
    discover_failure_history_cids,
    execute_ai_request,
    get_ai_backend_policy,
)
from handsfree.auth import FIXTURE_USER_ID
from handsfree.db.ai_history_index import store_ai_history_record
from handsfree.mcp import (
    get_provider_descriptor,
    infer_provider_capability,
    resolve_capability_execution_mode,
    resolve_provider_capability,
)

from .intent_parser import ParsedIntent
from .pending_actions import PendingActionManager
from .profiles import Profile, ProfileConfig
from .session_context import SessionContext

logger = logging.getLogger(__name__)

# Constants for response formatting
PR_TITLE_PREVIEW_LENGTH = 30  # Max characters for PR title previews in brief summaries


def _trace_result_envelope(trace: dict[str, Any] | None) -> dict[str, Any] | None:
    if not isinstance(trace, dict):
        return None
    envelope = trace.get("mcp_result_envelope")
    return envelope if isinstance(envelope, dict) else None


def _trace_result_preview(trace: dict[str, Any] | None) -> str | None:
    envelope = _trace_result_envelope(trace)
    summary = envelope.get("summary") if envelope else None
    if isinstance(summary, str) and summary.strip():
        return summary.strip()
    preview = (trace or {}).get("mcp_result_preview")
    if isinstance(preview, str) and preview.strip():
        return preview.strip()
    return None


def _trace_result_output(trace: dict[str, Any] | None) -> Any:
    envelope = _trace_result_envelope(trace)
    if envelope and "structured_output" in envelope:
        return envelope.get("structured_output")
    return (trace or {}).get("mcp_result_output")


def _trace_result_cid(trace: dict[str, Any] | None) -> str | None:
    envelope = _trace_result_envelope(trace)
    if envelope:
        artifact_refs = envelope.get("artifact_refs")
        if isinstance(artifact_refs, dict):
            cid = artifact_refs.get("result_cid")
            if isinstance(cid, str) and cid.strip():
                return cid.strip()
    cid = (trace or {}).get("mcp_cid")
    if isinstance(cid, str) and cid.strip():
        return cid.strip()
    output = _trace_result_output(trace)
    if isinstance(output, dict):
        cid = output.get("cid")
        if isinstance(cid, str) and cid.strip():
            return cid.strip()
    return None


def _trace_follow_up_actions(trace: dict[str, Any] | None) -> list[dict[str, Any]]:
    envelope = _trace_result_envelope(trace)
    actions = envelope.get("follow_up_actions") if envelope else None
    return actions if isinstance(actions, list) else []


def _render_agent_result_lines(
    preview: str | None,
    output: dict[str, Any] | None,
) -> list[str]:
    """Render compact user-facing lines from structured agent output."""
    lines: list[str] = []
    if isinstance(output, dict):
        if output.get("workflow") == "wearables_bridge_connectivity":
            device_name = output.get("device_name") or output.get("device_id")
            target_state = output.get("target_connection_state")
            target_rssi = output.get("target_rssi")
            if device_name:
                lines.append(f"device: {device_name}")
            if target_state:
                lines.append(f"state: {target_state}")
            if target_rssi is not None:
                lines.append(f"rssi: {target_rssi}")
            if lines:
                return lines[:3]
        for key in ("message", "status", "expanded_queries", "target_terms", "seed_urls"):
            value = output.get(key)
            if value is None:
                continue
            if isinstance(value, list):
                rendered = ", ".join(str(item) for item in value[:3])
            else:
                rendered = str(value)
            if rendered:
                lines.append(f"{key}: {rendered}")

        task_info = output.get("task")
        if isinstance(task_info, dict):
            task_status = task_info.get("status")
            task_id = task_info.get("task_id")
            if task_status:
                lines.append(f"task.status: {task_status}")
            if task_id:
                lines.append(f"task.id: {task_id}")

    if not lines and preview:
        lines.append(f"Result: {preview}")
    return lines[:3]


def _filter_router_result_tasks(
    tasks: list[Any],
    *,
    capability: str | None,
    latest_only: bool,
) -> list[Any]:
    filtered = [
        task for task in tasks
        if task.state == "completed"
        and isinstance(task.trace, dict)
        and (
            task.trace.get("mcp_result_envelope") is not None
            or task.trace.get("mcp_result_preview") is not None
            or task.trace.get("mcp_result_output") is not None
        )
    ]
    if capability:
        filtered = [
            task for task in filtered
            if isinstance(task.trace, dict) and task.trace.get("mcp_capability") == capability
        ]
    if latest_only:
        latest: list[Any] = []
        seen: set[tuple[str, str | None]] = set()
        for task in filtered:
            trace = task.trace if isinstance(task.trace, dict) else {}
            key = (task.provider, trace.get("mcp_capability"))
            if key in seen:
                continue
            seen.add(key)
            latest.append(task)
        filtered = latest
    return filtered


def _result_task_deep_link(task: Any) -> str | None:
    """Return the best available deep link for a result task."""
    trace = task.trace if isinstance(task.trace, dict) else {}
    pr_url = trace.get("pr_url")
    if isinstance(pr_url, str) and pr_url.strip():
        return pr_url.strip()

    cid = _trace_result_cid(trace)
    if cid:
        return f"ipfs://{cid}"

    seed_url = trace.get("mcp_seed_url")
    if isinstance(seed_url, str) and seed_url.strip():
        return seed_url.strip()

    return f"/v1/agents/tasks/{task.id}"


def _extract_cid_from_deep_link(deep_link: str | None) -> str | None:
    """Extract an IPFS CID from a result deep link when present."""
    if not isinstance(deep_link, str):
        return None
    if deep_link.startswith("ipfs://"):
        cid = deep_link.removeprefix("ipfs://").strip()
        return cid or None
    return None


def _build_result_card(task: Any) -> dict[str, Any]:
    """Build a navigable card for a completed result task."""
    trace = task.trace if isinstance(task.trace, dict) else {}
    preview = _trace_result_preview(trace)
    output = _trace_result_output(trace)
    provider_label = trace.get("provider_label") or task.provider
    capability = trace.get("mcp_capability") or "result"
    workflow = output.get("workflow") if isinstance(output, dict) else None
    card = {
        "title": "Wearables Connectivity Receipt"
        if workflow == "wearables_bridge_connectivity"
        else f"{provider_label} {str(capability).replace('_', ' ')}",
        "subtitle": f"Task {task.id[:8]} • completed",
        "lines": _render_agent_result_lines(
            preview,
            output if isinstance(output, dict) else None,
        )
        or [task.instruction or "Agent result"],
        "deep_link": _result_task_deep_link(task),
        "task_id": task.id,
        "provider": task.provider,
        "capability": capability,
    }
    follow_up_actions = _trace_follow_up_actions(trace)
    card["action_items"] = follow_up_actions or _build_result_action_items(card)
    card["actions"] = _available_result_actions(card)
    return card


def _serialize_result_for_ipfs(task: Any, card: dict[str, Any] | None = None) -> str:
    """Serialize a completed result task into a stable JSON payload for IPFS."""
    trace = task.trace if isinstance(task.trace, dict) else {}
    payload: dict[str, Any] = {
        "task_id": task.id,
        "provider": task.provider,
        "provider_label": trace.get("provider_label") or task.provider,
        "capability": trace.get("mcp_capability"),
        "instruction": task.instruction,
        "state": task.state,
        "result_preview": _trace_result_preview(trace),
        "result_output": _trace_result_output(trace),
        "result_envelope": _trace_result_envelope(trace),
        "deep_link": (card or {}).get("deep_link") if isinstance(card, dict) else _result_task_deep_link(task),
    }
    return json.dumps(payload, sort_keys=True)


def _build_result_action_items(card: dict[str, Any]) -> list[dict[str, Any]]:
    """Return structured result actions for client-side rendering."""
    deep_link = card.get("deep_link")
    cid = _extract_cid_from_deep_link(deep_link if isinstance(deep_link, str) else None)
    capability = str(card.get("capability") or "").strip().lower()
    is_wearables_receipt = str(card.get("title") or "").lower() == "wearables connectivity receipt"

    save_mode_items: list[dict[str, Any]] = [
        {
            "id": "save_result_to_ipfs_local",
            "label": "Save To IPFS Locally",
            "phrase": "save that result to ipfs locally",
            "execution_mode": "direct_import",
            "execution_mode_label": "Local",
            "params": {"mcp_preferred_execution_mode": "direct_import"},
        },
        {
            "id": "save_result_to_ipfs_remote",
            "label": "Save To IPFS Remotely",
            "phrase": "save that result to ipfs remotely",
            "execution_mode": "mcp_remote",
            "execution_mode_label": "Remote",
            "params": {"mcp_preferred_execution_mode": "mcp_remote"},
        },
    ]

    items: list[dict[str, Any]] = [
        {"id": "open_result", "label": "Open Result", "phrase": "open that result"},
        {
            "id": "show_result_details",
            "label": "Task Details",
            "phrase": "show task details for that result",
        },
        {
            "id": "show_related_results",
            "label": "Related Results",
            "phrase": "show another result like this",
        },
        {
            "id": "save_result_to_ipfs",
            "label": "Save To IPFS",
            "phrase": "save that result to ipfs",
        },
    ]

    if is_wearables_receipt:
        items = [
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
            *items,
        ]

    if cid:
        items.extend(
            [
                {
                    "id": "read_cid",
                    "label": "Read Receipt" if is_wearables_receipt else "Read CID",
                    "phrase": "read the wearables receipt" if is_wearables_receipt else "read the cid",
                    "params": {"cid": cid},
                },
                {
                    "id": "share_cid",
                    "label": "Share CID",
                    "phrase": "share that cid",
                    "params": {"cid": cid},
                },
                {
                    "id": "pin_result",
                    "label": "Pin",
                    "phrase": "pin that",
                    "params": {"cid": cid},
                },
                {
                    "id": "pin_result_local",
                    "label": "Pin Locally",
                    "phrase": "pin that locally",
                    "execution_mode": "direct_import",
                    "execution_mode_label": "Local",
                    "params": {"cid": cid, "mcp_preferred_execution_mode": "direct_import"},
                },
                {
                    "id": "pin_result_remote",
                    "label": "Pin Remotely",
                    "phrase": "pin that remotely",
                    "execution_mode": "mcp_remote",
                    "execution_mode_label": "Remote",
                    "params": {"cid": cid, "mcp_preferred_execution_mode": "mcp_remote"},
                },
                {
                    "id": "unpin_result_local",
                    "label": "Unpin Locally",
                    "phrase": "unpin that locally",
                    "execution_mode": "direct_import",
                    "execution_mode_label": "Local",
                    "params": {"cid": cid, "mcp_preferred_execution_mode": "direct_import"},
                },
                {
                    "id": "unpin_result_remote",
                    "label": "Unpin Remotely",
                    "phrase": "unpin that remotely",
                    "execution_mode": "mcp_remote",
                    "execution_mode_label": "Remote",
                    "params": {"cid": cid, "mcp_preferred_execution_mode": "mcp_remote"},
                },
            ]
        )
        items.extend(save_mode_items)
        items.append(
            {
                "id": "unpin_result",
                "label": "Unpin",
                "phrase": "unpin that",
                "params": {"cid": cid},
            }
        )
    else:
        items.extend(save_mode_items)
    if capability in {"workflow", "agentic_fetch"}:
        items.append(
            {
                "id": "rerun_workflow",
                "label": "Rerun Workflow",
                "phrase": "rerun that workflow remotely",
                "execution_mode": "mcp_remote",
                "execution_mode_label": "Remote",
                "params": {"mcp_preferred_execution_mode": "mcp_remote"},
            }
        )
    if capability == "agentic_fetch":
        items.append(
            {
                "id": "rerun_fetch_with_url",
                "label": "Rerun Fetch",
                "phrase": "rerun that fetch with https://example.com remotely",
                "execution_mode": "mcp_remote",
                "execution_mode_label": "Remote",
                "params": {
                    "mcp_seed_url": "https://example.com",
                    "mcp_preferred_execution_mode": "mcp_remote",
                },
            }
        )
    if capability == "dataset_discovery":
        items.append(
            {
                "id": "rerun_dataset_search",
                "label": "Rerun Dataset Search",
                "phrase": "rerun that dataset search with labor law datasets remotely",
                "execution_mode": "mcp_remote",
                "execution_mode_label": "Remote",
                "params": {
                    "mcp_input": "labor law datasets",
                    "mcp_preferred_execution_mode": "mcp_remote",
                },
            }
        )
    return items


def _available_result_actions(card: dict[str, Any]) -> list[str]:
    """Return user-facing actions available for the selected result card."""
    action_items = card.get("action_items")
    if isinstance(action_items, list) and action_items:
        return [item["phrase"] for item in action_items if isinstance(item, dict) and "phrase" in item]
    return [item["phrase"] for item in _build_result_action_items(card)]


def _execution_mode_suffix(mode: str | None) -> str:
    """Return a human-readable execution mode suffix for confirmation text."""
    return {
        "direct_import": " locally",
        "mcp_remote": " remotely",
    }.get(str(mode or "").strip().lower(), "")


def _execution_mode_label(mode: str | None) -> str | None:
    """Return a short label for a resolved execution mode."""
    normalized = str(mode or "").strip().lower()
    return {
        "direct_import": "Local",
        "mcp_remote": "Remote",
    }.get(normalized)


def _requested_local_fallback(preferred_mode: str | None, resolved_mode: str | None) -> bool:
    """Return whether a local request had to fall back to remote execution."""
    return (
        str(preferred_mode or "").strip().lower() == "direct_import"
        and str(resolved_mode or "").strip().lower() == "mcp_remote"
    )


def _execution_mode_policy_note(preferred_mode: str | None, resolved_mode: str | None) -> str:
    """Return a user-facing note when policy forces a remote fallback."""
    if _requested_local_fallback(preferred_mode, resolved_mode):
        return " Local execution isn't available right now, so I'll use remote MCP instead."
    return ""


def _execution_mode_detail_line(preferred_mode: str | None, resolved_mode: str | None) -> str | None:
    """Return an execution detail line for task/result cards."""
    label = _execution_mode_label(resolved_mode)
    if not label:
        return None
    if _requested_local_fallback(preferred_mode, resolved_mode):
        return f"Execution: {label} (local unavailable)"
    return f"Execution: {label}"


class CommandRouter:
    """Route parsed intents to handlers and compose responses."""

    # Intents that require confirmation (side effects)
    SIDE_EFFECT_INTENTS = {
        "pr.request_review",
        "pr.merge",
        "agent.delegate",
        "agent.result_pin",
        "agent.result_unpin",
        "agent.result_rerun",
        "agent.result_rerun_fetch",
        "agent.result_rerun_dataset",
        "agent.result_save_ipfs",
        "checks.rerun",
        "pr.comment",
    }

    def __init__(
        self,
        pending_actions: PendingActionManager,
        db_conn: duckdb.DuckDBPyConnection | None = None,
        github_provider: Any | None = None,
    ) -> None:
        """Initialize the router.

        Args:
            pending_actions: Manager for pending confirmation actions
            db_conn: Optional database connection for agent operations
            github_provider: Optional GitHub provider for fetching PR/check data
        """
        self.pending_actions = pending_actions
        self.db_conn = db_conn
        self.github_provider = github_provider
        # Session state for system.repeat - maps session_id to last response
        self._last_responses: dict[str, dict[str, Any]] = {}
        # Session state for system.next - maps session_id to (items, current_index)
        self._navigation_state: dict[str, tuple[list[dict[str, Any]], int]] = {}
        # Session context for tracking repo/PR across commands
        self._session_context = SessionContext()

        # Initialize agent service if DB is available
        self._agent_service = None
        if db_conn:
            from handsfree.agents.service import AgentService

            self._agent_service = AgentService(db_conn)

    def route(
        self,
        intent: ParsedIntent,
        profile: Profile,
        session_id: str | None = None,
        user_id: str | None = None,
        idempotency_key: str | None = None,
    ) -> dict[str, Any]:
        """Route an intent to appropriate handler and compose response.

        Args:
            intent: Parsed intent from the parser
            profile: User's current profile
            session_id: Optional session identifier for repeat functionality
            user_id: Optional user identifier for policy evaluation and audit logging
            idempotency_key: Optional idempotency key for deduplication

        Returns:
            Dictionary conforming to CommandResponse schema
        """
        profile_config = ProfileConfig.for_profile(profile)

        # Handle debug commands
        if intent.name == "debug.transcript":
            return self._handle_debug_transcript(user_id, profile_config, intent)

        # Handle system commands
        if intent.name == "system.repeat":
            return self._handle_repeat(session_id, profile_config, intent)
        elif intent.name == "system.next":
            return self._handle_next(session_id, profile_config, intent)
        elif intent.name == "system.confirm":
            return self._handle_confirm(intent, profile_config)
        elif intent.name == "system.cancel":
            return self._handle_cancel(intent, profile_config)
        elif intent.name == "system.set_profile":
            return self._handle_set_profile(intent, profile_config)

        # Special handling for pr.request_review - integrate with policy engine
        # Policy-based handling takes precedence over profile-based confirmation
        if intent.name == "pr.request_review" and self.db_conn and user_id:
            return self._handle_request_review_with_policy(
                intent, user_id, session_id, idempotency_key
            )

        # Special handling for checks.rerun - integrate with policy engine
        if intent.name == "checks.rerun" and self.db_conn and user_id:
            return self._handle_rerun_checks_with_policy(
                intent, user_id, session_id, idempotency_key
            )

        # Special handling for pr.comment - integrate with policy engine
        if intent.name == "pr.comment" and self.db_conn and user_id:
            return self._handle_comment_with_policy(intent, user_id, session_id, idempotency_key)

        # Check if this is a side-effect intent requiring confirmation (profile-based fallback)
        if intent.name in self.SIDE_EFFECT_INTENTS and profile_config.confirmation_required:
            return self._create_confirmation_response(intent, profile_config)

        # Route to domain handlers
        if intent.name == "inbox.list":
            response = self._handle_inbox_list(intent, profile_config, user_id)
        elif intent.name.startswith("pr."):
            response = self._handle_pr_intent(intent, profile_config, user_id)
        elif intent.name.startswith("checks."):
            response = self._handle_checks_intent(intent, profile_config)
        elif intent.name.startswith("agent."):
            response = self._handle_agent_intent(intent, profile_config, user_id, session_id)
        elif intent.name.startswith("ai."):
            response = self._handle_ai_intent(intent, profile_config, session_id, user_id)
        elif intent.name == "unknown":
            response = self._handle_unknown(intent, profile_config)
        else:
            response = {
                "status": "error",
                "intent": intent.to_dict(),
                "spoken_text": "I don't know how to handle that yet.",
            }

        # Store response for system.repeat
        if session_id:
            self._last_responses[session_id] = response

            # Store navigation state for list-like responses
            self._store_navigation_state(session_id, response, intent)

            # Capture repo/PR context from certain intents
            self._capture_session_context(session_id, intent)

        return response

    def _create_confirmation_response(
        self, intent: ParsedIntent, profile_config: ProfileConfig
    ) -> dict[str, Any]:
        """Create a response requesting confirmation for a side-effect intent."""
        # Generate human-readable summary
        summary = self._format_confirmation_summary(intent)

        # Create pending action
        pending = self.pending_actions.create(
            intent_name=intent.name, entities=intent.entities, summary=summary
        )

        spoken_text = f"{summary} Say 'confirm' to proceed."
        if profile_config.profile == Profile.WORKOUT:
            spoken_text = f"{summary} Confirm?"

        # Apply profile-based truncation
        spoken_text = profile_config.truncate_spoken_text(spoken_text)

        return {
            "status": "needs_confirmation",
            "intent": intent.to_dict(),
            "spoken_text": spoken_text,
            "pending_action": pending.to_dict(),
        }

    def _format_confirmation_summary(self, intent: ParsedIntent) -> str:
        """Format a human-readable summary of the pending action."""
        if intent.name == "pr.request_review":
            reviewers = intent.entities.get("reviewers", [])
            pr_num = intent.entities.get("pr_number")
            reviewers_str = " and ".join(reviewers)
            if pr_num:
                return f"I can request review from {reviewers_str} on PR {pr_num}."
            return f"I can request review from {reviewers_str}."
        elif intent.name == "pr.merge":
            pr_num = intent.entities.get("pr_number", "this PR")
            method = intent.entities.get("merge_method", "merge")
            return f"I can {method} PR {pr_num}."
        elif intent.name == "agent.delegate":
            instruction = intent.entities.get("instruction", "handle this")
            issue_num = intent.entities.get("issue_number")
            pr_num = intent.entities.get("pr_number")
            provider = intent.entities.get("provider", "copilot")
            provider_descriptor = get_provider_descriptor(provider)
            provider_label = provider_descriptor.display_name if provider_descriptor else "the agent"
            capability = resolve_provider_capability(
                provider,
                intent.entities.get("mcp_capability"),
                instruction,
            )
            execution_mode = resolve_capability_execution_mode(
                provider,
                capability,
                intent.entities.get("mcp_preferred_execution_mode"),
            )
            mode_suffix = _execution_mode_suffix(execution_mode)
            mode_note = _execution_mode_policy_note(
                intent.entities.get("mcp_preferred_execution_mode"),
                execution_mode,
            )
            if issue_num:
                return (
                    f"I can ask {provider_label} to {instruction} issue {issue_num}{mode_suffix}."
                    f"{mode_note}"
                )
            elif pr_num:
                return (
                    f"I can ask {provider_label} to {instruction} PR {pr_num}{mode_suffix}."
                    f"{mode_note}"
                )
            return f"I can delegate to {provider_label}{mode_suffix}: {instruction}.{mode_note}"
        elif intent.name == "agent.result_pin":
            execution_mode = resolve_capability_execution_mode(
                "ipfs_kit_mcp",
                "ipfs_pin",
                intent.entities.get("mcp_preferred_execution_mode"),
            )
            return (
                f"I can pin the current IPFS result{_execution_mode_suffix(execution_mode)}."
                f"{_execution_mode_policy_note(intent.entities.get('mcp_preferred_execution_mode'), execution_mode)}"
            )
        elif intent.name == "agent.result_unpin":
            execution_mode = resolve_capability_execution_mode(
                "ipfs_kit_mcp",
                "ipfs_pin",
                intent.entities.get("mcp_preferred_execution_mode"),
            )
            return (
                f"I can unpin the current IPFS result{_execution_mode_suffix(execution_mode)}."
                f"{_execution_mode_policy_note(intent.entities.get('mcp_preferred_execution_mode'), execution_mode)}"
            )
        elif intent.name == "agent.result_rerun":
            return (
                "I can rerun the current workflow result"
                f"{_execution_mode_suffix(intent.entities.get('mcp_preferred_execution_mode') or 'mcp_remote')}"
                "."
            )
        elif intent.name == "agent.result_rerun_fetch":
            seed_url = intent.entities.get("mcp_seed_url")
            if seed_url:
                return (
                    f"I can rerun the current fetch with {seed_url}"
                    f"{_execution_mode_suffix(intent.entities.get('mcp_preferred_execution_mode') or 'mcp_remote')}"
                    "."
                )
            return (
                "I can rerun the current fetch with a new URL"
                f"{_execution_mode_suffix(intent.entities.get('mcp_preferred_execution_mode') or 'mcp_remote')}"
                "."
            )
        elif intent.name == "agent.result_rerun_dataset":
            query = intent.entities.get("mcp_input")
            if query:
                return (
                    f"I can rerun the current dataset search with {query}"
                    f"{_execution_mode_suffix(intent.entities.get('mcp_preferred_execution_mode') or 'mcp_remote')}"
                    "."
                )
            return (
                "I can rerun the current dataset search with a new query"
                f"{_execution_mode_suffix(intent.entities.get('mcp_preferred_execution_mode') or 'mcp_remote')}"
                "."
            )
        elif intent.name == "agent.result_save_ipfs":
            execution_mode = resolve_capability_execution_mode(
                "ipfs_kit_mcp",
                "ipfs_add",
                intent.entities.get("mcp_preferred_execution_mode"),
            )
            return (
                f"I can save the current result to IPFS{_execution_mode_suffix(execution_mode)}."
                f"{_execution_mode_policy_note(intent.entities.get('mcp_preferred_execution_mode'), execution_mode)}"
            )
        elif intent.name == "checks.rerun":
            pr_num = intent.entities.get("pr_number")
            if pr_num:
                return f"I can re-run checks on PR {pr_num}."
            return "I can re-run checks."
        elif intent.name == "pr.comment":
            pr_num = intent.entities.get("pr_number")
            comment_body = intent.entities.get("comment_body", "")
            # Truncate long comments in confirmation message
            preview = comment_body[:50] + "..." if len(comment_body) > 50 else comment_body
            return f"I can post comment on PR {pr_num}: {preview}"
        return "I can execute this action."

    def _handle_repeat(
        self,
        session_id: str | None,
        profile_config: ProfileConfig,
        intent: ParsedIntent,
    ) -> dict[str, Any]:
        """Handle system.repeat to replay last response."""
        if not session_id or session_id not in self._last_responses:
            spoken_text = profile_config.truncate_spoken_text("Nothing to repeat.")
            return {
                "status": "ok",
                "intent": intent.to_dict(),
                "spoken_text": spoken_text,
            }

        # Return the last response for this session
        return self._last_responses[session_id]

    def _handle_next(
        self,
        session_id: str | None,
        profile_config: ProfileConfig,
        intent: ParsedIntent,
    ) -> dict[str, Any]:
        """Handle system.next to advance through list items."""
        if not session_id or session_id not in self._navigation_state:
            spoken_text = profile_config.truncate_spoken_text(
                "No list to navigate. Try asking for inbox or PR summary first."
            )
            return {
                "status": "ok",
                "intent": intent.to_dict(),
                "spoken_text": spoken_text,
            }

        items, current_index = self._navigation_state[session_id]
        next_index = current_index + 1

        if next_index >= len(items):
            spoken_text = profile_config.truncate_spoken_text("No more items.")
            return {
                "status": "ok",
                "intent": intent.to_dict(),
                "spoken_text": spoken_text,
            }

        # Update navigation state
        self._navigation_state[session_id] = (items, next_index)

        # Build response for next item
        next_item = items[next_index]
        response = self._build_item_response(next_item, next_index, len(items), profile_config)

        # Store as last response for repeat
        self._last_responses[session_id] = response

        return response

    def _store_navigation_state(
        self,
        session_id: str,
        response: dict[str, Any],
        intent: ParsedIntent,
    ) -> None:
        """Store navigation state for list-like responses.

        Args:
            session_id: Session identifier
            response: Response dict that may contain navigable items
            intent: The intent that generated this response
        """
        # Check if response has cards (indicates list-like data)
        if "cards" not in response or not response["cards"]:
            # Clear navigation state if no cards
            if session_id in self._navigation_state:
                del self._navigation_state[session_id]
            return

        # Store cards as navigable items with metadata
        items = []
        for card in response["cards"]:
            items.append(
                {
                    "type": "card",
                    "intent_name": intent.name,
                    "data": card,
                }
            )

        # Store with index 0 (showing first item)
        self._navigation_state[session_id] = (items, 0)

    def _get_current_navigation_card(self, session_id: str | None) -> dict[str, Any] | None:
        """Return the currently selected card for a session, if any."""
        if not session_id or session_id not in self._navigation_state:
            return None
        items, current_index = self._navigation_state[session_id]
        if current_index < 0 or current_index >= len(items):
            return None
        item = items[current_index]
        if item.get("type") != "card":
            return None
        data = item.get("data")
        return data if isinstance(data, dict) else None

    def seed_navigation_card(self, session_id: str, card: dict[str, Any]) -> None:
        """Seed the current navigation state with a single preselected card."""
        self._navigation_state[session_id] = (
            [{"type": "card", "intent_name": "agent.result_seed", "data": card}],
            0,
        )

    def _capture_session_context(
        self,
        session_id: str,
        intent: ParsedIntent,
    ) -> None:
        """Capture repo/PR context from intents that reference them.

        This allows subsequent commands to omit repo/PR and use the last
        referenced values from the session.

        Args:
            session_id: Session identifier
            intent: The intent that may contain repo/PR references
        """
        # Capture context from pr.summarize
        if intent.name == "pr.summarize":
            pr_number = intent.entities.get("pr_number")
            repo = intent.entities.get("repo")
            if pr_number and repo:
                self._session_context.set_repo_pr(session_id, repo, pr_number)
            elif pr_number:
                # If no repo specified, use a default or preserve existing repo
                context = self._session_context.get_repo_pr(session_id)
                repo = context.get("repo", "default/repo")
                self._session_context.set_repo_pr(session_id, repo, pr_number)

        # Capture context from checks.status
        elif intent.name == "checks.status":
            pr_number = intent.entities.get("pr_number")
            repo = intent.entities.get("repo")
            if pr_number and repo:
                self._session_context.set_repo_pr(session_id, repo, pr_number)
            elif pr_number:
                # If no repo specified, use a default or preserve existing repo
                context = self._session_context.get_repo_pr(session_id)
                repo = context.get("repo", "default/repo")
                self._session_context.set_repo_pr(session_id, repo, pr_number)

        elif intent.name.startswith("ai."):
            pr_number = intent.entities.get("pr_number")
            repo = intent.entities.get("repo")
            if pr_number and repo:
                self._session_context.set_repo_pr(session_id, repo, pr_number)
            elif pr_number:
                context = self._session_context.get_repo_pr(session_id)
                repo = context.get("repo", "default/repo")
                self._session_context.set_repo_pr(session_id, repo, pr_number)

        # Note: inbox.list doesn't capture PR context since it shows multiple PRs
        # We only capture single PR references for now

    def _handle_debug_transcript(
        self, user_id: str | None, profile_config: ProfileConfig, intent: ParsedIntent
    ) -> dict[str, Any]:
        """Handle debug.transcript to return the last stored transcript.

        Args:
            user_id: User identifier for filtering commands
            profile_config: User's profile configuration
            intent: The debug.transcript intent

        Returns:
            Response dict with the last transcript
        """
        from handsfree.db.commands import get_commands
        from handsfree.logging_utils import redact_secrets

        if not self.db_conn or not user_id:
            spoken_text = profile_config.truncate_spoken_text("Debug information not available.")
            return {
                "status": "error",
                "intent": intent.to_dict(),
                "spoken_text": spoken_text,
            }

        # Get the most recent command with transcript for this user
        commands = get_commands(
            self.db_conn,
            user_id=user_id,
            limit=10,  # Check last 10 commands
        )

        # Find the first command with a transcript
        last_transcript = None
        for cmd in commands:
            if cmd.transcript:
                last_transcript = cmd.transcript
                break

        if not last_transcript:
            spoken_text = profile_config.truncate_spoken_text(
                "No recent transcript found. Try enabling debug mode in your client."
            )
            return {
                "status": "ok",
                "intent": intent.to_dict(),
                "spoken_text": spoken_text,
            }

        # Redact secrets from transcript
        safe_transcript = redact_secrets(last_transcript)

        # Build response based on profile
        if profile_config.profile == Profile.WORKOUT:
            spoken_text = f"I heard: {safe_transcript}"
        else:
            spoken_text = f"The last command I heard was: {safe_transcript}"

        spoken_text = profile_config.truncate_spoken_text(spoken_text)

        return {
            "status": "ok",
            "intent": intent.to_dict(),
            "spoken_text": spoken_text,
        }

    def _build_item_response(
        self,
        item: dict[str, Any],
        index: int,
        total: int,
        profile_config: ProfileConfig,
    ) -> dict[str, Any]:
        """Build a response for a single navigation item.

        Args:
            item: Item data dict
            index: Current item index (0-based)
            total: Total number of items
            profile_config: User's profile configuration

        Returns:
            Response dict
        """
        intent_name = item.get("intent_name", "unknown")
        card_data = item.get("data", {})

        # Build spoken text based on profile
        if profile_config.profile == Profile.WORKOUT:
            spoken_text = f"Item {index + 1} of {total}: {card_data.get('title', 'Unknown')}."
        else:
            title = card_data.get("title", "Unknown")
            subtitle = card_data.get("subtitle", "")
            spoken_text = f"Item {index + 1} of {total}: {title}. {subtitle}"

        # Apply profile-based truncation
        spoken_text = profile_config.truncate_spoken_text(spoken_text)

        return {
            "status": "ok",
            "intent": {
                "name": f"system.next.{intent_name}",
                "confidence": 1.0,
                "entities": {"index": index, "total": total},
            },
            "spoken_text": spoken_text,
            "cards": [card_data],
        }

    def _handle_confirm(
        self, intent: ParsedIntent, profile_config: ProfileConfig
    ) -> dict[str, Any]:
        """Handle system.confirm - execute pending action."""
        # In a real implementation, this would get the pending token from context
        # For now, return a placeholder
        spoken_text = profile_config.truncate_spoken_text(
            "Confirmation received. This will be implemented in the API endpoint."
        )
        return {
            "status": "ok",
            "intent": intent.to_dict(),
            "spoken_text": spoken_text,
        }

    def _handle_cancel(self, intent: ParsedIntent, profile_config: ProfileConfig) -> dict[str, Any]:
        """Handle system.cancel - cancel pending action."""
        spoken_text = profile_config.truncate_spoken_text("Cancelled.")
        return {
            "status": "ok",
            "intent": intent.to_dict(),
            "spoken_text": spoken_text,
        }

    def _handle_set_profile(
        self, intent: ParsedIntent, profile_config: ProfileConfig
    ) -> dict[str, Any]:
        """Handle system.set_profile to change user profile."""
        profile_name = intent.entities.get("profile", "default")
        spoken_text = profile_config.truncate_spoken_text(f"Switched to {profile_name} mode.")
        return {
            "status": "ok",
            "intent": intent.to_dict(),
            "spoken_text": spoken_text,
        }

    def _handle_inbox_list(
        self, intent: ParsedIntent, profile_config: ProfileConfig, user_id: str | None = None
    ) -> dict[str, Any]:
        """Handle inbox.list intent with profile-based verbosity."""
        # Get user from intent entities or fall back to fixture user
        user = intent.entities.get("user", "testuser")
        
        # Use GitHub provider if available
        if self.github_provider:
            from handsfree.handlers.inbox import handle_inbox_list
            
            # Use privacy mode from profile configuration
            privacy_mode = profile_config.privacy_mode
            
            try:
                # Call the inbox handler with user_id for live mode support
                result = handle_inbox_list(
                    provider=self.github_provider,
                    user=user,
                    privacy_mode=privacy_mode,
                    profile_config=profile_config,
                    user_id=user_id,
                )
                
                # Return response with inbox items
                return {
                    "status": "ok",
                    "intent": intent.to_dict(),
                    "spoken_text": result["spoken_text"],
                    "cards": [
                        {
                            "title": item["title"],
                            "subtitle": f"{item['repo']} • Priority {item['priority']}",
                            "url": item["url"],
                        }
                        for item in result["items"][:5]  # Limit to top 5 for UI
                    ] if "items" in result and result["items"] else [],
                }
            except Exception as e:
                logger.error("Failed to fetch inbox: %s", str(e))
                # Fall back to error message
                spoken_text = "Could not fetch inbox items."
                if profile_config.profile == Profile.WORKOUT:
                    spoken_text = "Inbox unavailable."
                spoken_text = profile_config.truncate_spoken_text(spoken_text)
                return {
                    "status": "error",
                    "intent": intent.to_dict(),
                    "spoken_text": spoken_text,
                }
        
        # Fallback: Stub data if no GitHub provider
        profile = profile_config.profile

        if profile == Profile.WORKOUT:
            # Ultra-brief: key numbers only
            spoken_text = "2 PRs, 1 failing."
        elif profile == Profile.COMMUTE:
            # Brief: essential info
            spoken_text = "You have 2 PRs waiting for review and 1 failing check."
        elif profile == Profile.FOCUSED:
            # Minimal: actionable items only
            spoken_text = "2 PRs need review. 1 check failing on PR 145."
        elif profile == Profile.KITCHEN:
            # Moderate: conversational
            spoken_text = "You have 2 pull requests waiting for review and 1 check that's failing."
        elif profile == Profile.RELAXED:
            # Detailed: full context
            spoken_text = (
                "You have 2 pull requests waiting for your review. "
                "PR 142 from alice and PR 145 from bob. "
                "There's also 1 failing check on PR 145 that needs attention."
            )
        else:  # DEFAULT
            # Balanced
            spoken_text = "You have 2 PRs waiting for review and 1 failing check."

        # Apply profile-based truncation as safety net
        spoken_text = profile_config.truncate_spoken_text(spoken_text)

        return {
            "status": "ok",
            "intent": intent.to_dict(),
            "spoken_text": spoken_text,
        }

    def _format_inbox_summary(
        self, prs: list[dict[str, Any]], profile_config: ProfileConfig
    ) -> str:
        """Format inbox summary based on profile verbosity.

        Args:
            prs: List of PR dictionaries
            profile_config: User's profile configuration

        Returns:
            Formatted spoken summary
        """
        if not prs:
            if profile_config.profile == Profile.WORKOUT:
                return "Inbox empty."
            return "Your inbox is empty."

        count = len(prs)

        # Count actionable vs informational
        review_requests = sum(1 for pr in prs if pr.get("requested_reviewer", False))
        assignments = sum(1 for pr in prs if pr.get("assignee", False))

        # Build summary based on profile
        if profile_config.profile == Profile.WORKOUT:
            # Ultra-brief: just counts
            if review_requests > 0:
                return f"{review_requests} PRs."
            return f"{count} items."

        elif profile_config.profile == Profile.FOCUSED:
            # Brief, actionable items only
            actionable = review_requests + assignments
            if actionable > 0:
                return f"{actionable} actionable PRs."
            return f"{count} inbox items."

        elif profile_config.profile == Profile.RELAXED:
            # Detailed: full context
            parts = []
            if review_requests > 0:
                parts.append(
                    f"{review_requests} pull request{'s' if review_requests != 1 else ''} "
                    f"waiting for your review"
                )
            if assignments > 0:
                parts.append(f"{assignments} PR{'s' if assignments != 1 else ''} assigned to you")
            if not parts:
                parts.append(f"{count} inbox item{'s' if count != 1 else ''}")

            summary = "You have " + " and ".join(parts) + "."

            # Add detail about first PR
            if prs:
                first_pr = prs[0]
                summary += (
                    f" First item: PR #{first_pr.get('pr_number')} "
                    f"in {first_pr.get('repo', 'unknown')}: {first_pr.get('title', 'Untitled')}."
                )

            return summary

        else:
            # Moderate/default: balanced detail
            parts = []
            if review_requests > 0:
                parts.append(f"{review_requests} PRs for review")
            if assignments > 0:
                parts.append(f"{assignments} assigned")
            if not parts:
                parts.append(f"{count} items")

            return "You have " + " and ".join(parts) + "."

    def _handle_pr_intent(
        self, intent: ParsedIntent, profile_config: ProfileConfig, user_id: str | None = None
    ) -> dict[str, Any]:
        """Handle PR-related intents with profile-based verbosity."""
        profile = profile_config.profile

        if intent.name == "pr.summarize":
            pr_num = intent.entities.get("pr_number")
            repo = intent.entities.get("repo", "owner/repo")  # Default repo for fixture mode

            if pr_num and self._use_cli_for_read_intents():
                try:
                    from handsfree.cli import GitHubCLIAdapter

                    result = GitHubCLIAdapter().summarize_pr(pr_num, profile_config)
                    return {
                        "status": "ok",
                        "intent": intent.to_dict(),
                        "spoken_text": result["spoken_text"],
                        "cards": [
                            {
                                "title": result["title"],
                                "subtitle": (
                                    f"PR #{pr_num} • {result['state']} • by {result['author']}"
                                ),
                                "lines": [
                                    (
                                        f"{result['changed_files']} files, "
                                        f"+{result['additions']} -{result['deletions']}"
                                    )
                                ],
                            }
                        ],
                        "debug": {"tool_calls": [result["trace"]]},
                    }
                except Exception as e:
                    logger.info("CLI PR summary unavailable, falling back: %s", str(e))

            # Use GitHub provider if available and pr_number is specified
            if self.github_provider and pr_num:
                from handsfree.handlers.pr_summary import handle_pr_summarize

                # Use privacy mode from profile configuration
                privacy_mode = profile_config.privacy_mode

                try:
                    # Call the PR summary handler with user_id for live mode support
                    result = handle_pr_summarize(
                        provider=self.github_provider,
                        repo=repo,
                        pr_number=pr_num,
                        privacy_mode=privacy_mode,
                        profile_config=profile_config,
                        user_id=user_id,
                    )
                    
                    # Return response with PR details
                    return {
                        "status": "ok",
                        "intent": intent.to_dict(),
                        "spoken_text": result["spoken_text"],
                        "cards": [
                            {
                                "title": result["title"],
                                "subtitle": f"PR #{pr_num} • {result['state']} • by {result['author']}",
                                "body": f"{result['changed_files']} files, +{result['additions']} -{result['deletions']}",
                            }
                        ],
                    }
                except Exception as e:
                    logger.error("Failed to fetch PR summary for %s#%d: %s", repo, pr_num, str(e))
                    # Fall back to error message
                    spoken_text = f"Could not fetch PR {pr_num}."
                    if profile_config.profile == Profile.WORKOUT:
                        spoken_text = f"PR {pr_num} unavailable."
                    spoken_text = profile_config.truncate_spoken_text(spoken_text)
                    return {
                        "status": "error",
                        "intent": intent.to_dict(),
                        "spoken_text": spoken_text,
                    }
            
            # Fallback: stub data
            pr_num_str = str(pr_num) if pr_num else "unknown"
            
            # Stub data - in production this would come from GitHub provider
            # Generate profile-appropriate PR summaries
            if profile == Profile.WORKOUT:
                # Ultra-brief: 1-2 sentences, key numbers only
                spoken_text = f"PR {pr_num_str}: command system."
            elif profile == Profile.COMMUTE:
                # Brief: 2-3 sentences, essential info
                spoken_text = (
                    f"PR {pr_num_str} adds the command system. "
                    "It includes intent parsing and profile support."
                )
            elif profile == Profile.FOCUSED:
                # Minimal: brief, actionable
                spoken_text = (
                    f"PR {pr_num_str} adds command system with intent parsing. Ready for review."
                )
            elif profile == Profile.KITCHEN:
                # Moderate: 3-4 sentences, conversational
                spoken_text = (
                    f"PR {pr_num_str} adds the command system with intent parsing. "
                    "It supports profiles like workout and commute. "
                    "The system includes confirmation flow for side effects."
                )
            elif profile == Profile.RELAXED:
                # Detailed: full context, all details
                spoken_text = (
                    f"PR {pr_num_str} adds the command system with intent parsing "
                    "and profile support. "
                    "The system recognizes voice commands and routes them to "
                    "appropriate handlers. "
                    "It includes profiles for workout, commute, kitchen, focused, "
                    "and relaxed contexts. "
                    "There's a confirmation flow for side-effect intents, "
                    "and the spoken responses are adjusted based on the active profile."
                )
            else:  # DEFAULT
                # Balanced
                spoken_text = f"PR {pr_num_str} adds the command system with intent parsing."

        elif intent.name == "pr.request_review":
            # Should have been caught by confirmation flow
            spoken_text = "Review request submitted."
        elif intent.name == "pr.merge":
            # Should have been caught by confirmation flow
            spoken_text = "Merge submitted."
        else:
            spoken_text = "PR intent recognized but not implemented."

        # Apply profile-based truncation as safety net
        spoken_text = profile_config.truncate_spoken_text(spoken_text)

        return {
            "status": "ok",
            "intent": intent.to_dict(),
            "spoken_text": spoken_text,
        }

    def _handle_ai_intent(
        self,
        intent: ParsedIntent,
        profile_config: ProfileConfig,
        session_id: str | None = None,
        user_id: str | None = None,
    ) -> dict[str, Any]:
        """Handle AI / Copilot read-only intents."""
        command_map = {
            "ai.explain_pr": {
                "capability_id": "copilot.pr.explain",
                "card_title": "Copilot explanation",
                "error_label": "explain",
            },
            "ai.summarize_diff": {
                "capability_id": "copilot.pr.diff_summary",
                "card_title": "Copilot diff summary",
                "error_label": "summarize diff for",
            },
            "ai.explain_failure": {
                "capability_id": "copilot.pr.failure_explain",
                "card_title": "Failure analysis",
                "error_label": "explain failing checks for",
            },
            "ai.accelerated_explain_failure": {
                "capability_id": "github.check.accelerated_failure_explain",
                "card_title": "Accelerated failure analysis",
                "error_label": "build accelerated failure analysis for",
            },
            "ai.accelerated_rag_summary": {
                "capability_id": "github.pr.accelerated_summary",
                "card_title": "Accelerated PR summary",
                "error_label": "build an accelerated summary for",
            },
            "ai.rag_summary": {
                "capability_id": "github.pr.rag_summary",
                "card_title": "Augmented PR summary",
                "error_label": "build an augmented summary for",
            },
            "ai.find_similar_failures": {
                "capability_id": "github.check.find_similar_failures",
                "card_title": "Similar failures",
                "error_label": "find similar failures for",
            },
            "ai.read_cid": {
                "capability_id": "ipfs.content.read_ai_output",
                "card_title": "Stored AI output",
                "error_label": "read stored AI output for",
            },
            "ai.accelerate_generate_and_store": {
                "capability_id": "ipfs.accelerate.generate_and_store",
                "card_title": "Accelerated stored output",
                "error_label": "generate and store accelerated output for",
            },
        }
        if intent.name not in command_map:
            spoken_text = profile_config.truncate_spoken_text("I don't know that AI command yet.")
            return {
                "status": "error",
                "intent": intent.to_dict(),
                "spoken_text": spoken_text,
            }

        pr_num = intent.entities.get("pr_number")
        repo = intent.entities.get("repo")
        if intent.name not in {"ai.read_cid", "ai.accelerate_generate_and_store"}:
            if not pr_num:
                context = self._session_context.get_repo_pr(session_id, fallback_repo="default/repo")
                pr_num = context.get("pr_number")
                if not repo:
                    repo = context.get("repo")
            if not pr_num:
                spoken_text = profile_config.truncate_spoken_text("Please specify a PR number.")
                return {
                    "status": "error",
                    "intent": intent.to_dict(),
                    "spoken_text": spoken_text,
                }

        if self._ai_intent_requires_cli(intent.name) and not self._use_cli_for_read_intents():
            spoken_text = profile_config.truncate_spoken_text(
                "Copilot CLI explain is not enabled."
            )
            return {
                "status": "error",
                "intent": intent.to_dict(),
                "spoken_text": spoken_text,
            }

        try:
            config = dict(command_map[intent.name])
            requested_workflow = None
            if intent.name == "ai.rag_summary":
                from handsfree.models import AIWorkflow

                requested_workflow = AIWorkflow.PR_RAG_SUMMARY
            elif intent.name == "ai.explain_failure":
                from handsfree.models import AIWorkflow

                requested_workflow = AIWorkflow.FAILURE_RAG_EXPLAIN
            if intent.name == "ai.explain_failure":
                config.update(self._select_failure_ai_capability(intent))
            if intent.name == "ai.rag_summary":
                config.update(self._select_pr_summary_ai_capability(intent))
            request_options: dict[str, Any] = {}
            request_inputs: dict[str, Any] = {}
            if config["capability_id"] == "github.check.failure_rag_explain" and self.github_provider:
                request_options["github_provider"] = self.github_provider
            if config["capability_id"] == "github.check.accelerated_failure_explain" and self.github_provider:
                request_options["github_provider"] = self.github_provider
            if config["capability_id"] == "github.check.find_similar_failures" and self.github_provider:
                request_options["github_provider"] = self.github_provider
            if intent.entities.get("persist_output") is True:
                request_options["persist_output"] = True
                request_options["ipfs_options"] = {"pin": True}
            if intent.name == "ai.read_cid":
                request_options["cid"] = intent.entities.get("cid")
            if intent.name == "ai.accelerate_generate_and_store":
                request_inputs["prompt"] = intent.entities.get("prompt")
                if intent.entities.get("kit_pin") is True:
                    request_inputs["kit_pin"] = True
                    request_options["ipfs_options"] = {"pin": False}
            if intent.entities.get("history_cids"):
                request_inputs["history_cids"] = list(intent.entities["history_cids"])
            elif config["capability_id"] in {
                "github.check.failure_rag_explain",
                "github.check.accelerated_failure_explain",
                "github.check.find_similar_failures",
            }:
                auto_history_cids = self._discover_failure_history_cids(
                    user_id=user_id,
                    repo=repo,
                    pr_number=pr_num,
                    workflow_name=intent.entities.get("workflow_name"),
                    check_name=intent.entities.get("check_name"),
                    failure_target=intent.entities.get("failure_target"),
                    failure_target_type=intent.entities.get("failure_target_type"),
                )
                if auto_history_cids:
                    request_inputs["history_cids"] = auto_history_cids

            request = AICapabilityRequest(
                capability_id=config["capability_id"],
                context=AIRequestContext(
                    repo=repo,
                    pr_number=pr_num,
                    workflow_name=intent.entities.get("workflow_name"),
                    check_name=intent.entities.get("check_name"),
                    failure_target=intent.entities.get("failure_target"),
                    failure_target_type=intent.entities.get("failure_target_type"),
                    session_id=session_id,
                ),
                inputs=request_inputs,
                options=request_options,
            )
            execution = execute_ai_request(request, profile_config=profile_config)
            result = execution.output
            if intent.name == "ai.find_similar_failures":
                headline, summary, spoken_text = self._format_similar_failures_result(
                    result,
                    pr_num=pr_num,
                    profile_config=profile_config,
                )
                result = dict(result)
                result.setdefault("headline", headline)
                result.setdefault("summary", summary)
                result.setdefault("spoken_text", spoken_text)
            if (
                self.db_conn
                and user_id
                and execution.capability_id in {
                    "github.check.failure_rag_explain",
                    "github.check.accelerated_failure_explain",
                }
                and isinstance(result.get("ipfs_cid"), str)
                and result["ipfs_cid"].strip()
            ):
                store_ai_history_record(
                    self.db_conn,
                    user_id=user_id,
                    capability_id=execution.capability_id,
                    repo=result.get("repo") or repo,
                    pr_number=result.get("pr_number") or pr_num,
                    failure_target=result.get("failure_target") or intent.entities.get("failure_target"),
                    failure_target_type=result.get("failure_target_type")
                    or intent.entities.get("failure_target_type"),
                    ipfs_cid=result["ipfs_cid"].strip(),
                )
            if intent.name == "ai.read_cid":
                card_title = f"{config['card_title']} {result['cid']}"
            elif intent.name == "ai.accelerate_generate_and_store":
                card_title = config["card_title"]
            else:
                card_title = f"{config['card_title']} for PR #{pr_num}"
                if repo:
                    card_title = f"{card_title} on {repo}"
            card_lines = [result.get("summary") or str(result.get("generated") or result.get("cid") or "Completed.")]
            if result.get("ipfs_cid"):
                card_lines.append(f"Stored in IPFS as {result['ipfs_cid']}")
            elif result.get("cid"):
                card_lines.append(f"Stored in IPFS as {result['cid']}")
            return {
                "status": "ok",
                "intent": intent.to_dict(),
                "spoken_text": result.get("spoken_text")
                or profile_config.truncate_spoken_text(
                    f"Stored accelerated output as {result.get('cid', 'a new CID')}."
                ),
                "cards": [
                    {
                        "title": card_title,
                        "subtitle": result.get("headline") or config["card_title"],
                        "lines": card_lines,
                    }
                ],
                "debug": {
                    "tool_calls": [result["trace"]],
                    "resolved_context": {
                        "pr_number": pr_num,
                        "repo": repo,
                        "cid": intent.entities.get("cid"),
                        "history_cids": request_inputs.get("history_cids", []),
                        "prompt": request_inputs.get("prompt"),
                    },
                    "capability_id": execution.capability_id,
                    "execution_mode": execution.execution_mode.value,
                    "persist_output": bool(intent.entities.get("persist_output")),
                    "ipfs_cid": result.get("ipfs_cid"),
                    "policy_resolution": build_policy_resolution(
                        requested_workflow=requested_workflow,
                        resolved_workflow={
                            "github.pr.rag_summary": requested_workflow,
                            "github.pr.accelerated_summary": AIWorkflow.ACCELERATED_PR_SUMMARY,
                            "github.check.failure_rag_explain": requested_workflow,
                            "github.check.accelerated_failure_explain": AIWorkflow.ACCELERATED_FAILURE_EXPLAIN,
                        }.get(execution.capability_id, requested_workflow)
                        if requested_workflow is not None
                        else None,
                        requested_capability_id=None,
                        resolved_capability_id=execution.capability_id,
                    ).model_dump(mode="json")
                    if requested_workflow is not None
                    else None,
                },
            }
        except Exception as e:
            logger.error("Failed AI CLI command %s for PR %s: %s", intent.name, pr_num, str(e))
            spoken_text = profile_config.truncate_spoken_text(
                f"Could not {command_map[intent.name]['error_label']} PR {pr_num} with Copilot."
            )
            return {
                "status": "error",
                "intent": intent.to_dict(),
                "spoken_text": spoken_text,
            }

        spoken_text = profile_config.truncate_spoken_text(
            "I don't know how to handle that AI request yet."
        )
        return {
            "status": "error",
            "intent": intent.to_dict(),
            "spoken_text": spoken_text,
        }

    def _discover_failure_history_cids(
        self,
        *,
        user_id: str | None,
        repo: str | None,
        pr_number: int | None,
        workflow_name: str | None,
        check_name: str | None,
        failure_target: str | None,
        failure_target_type: str | None,
        limit: int = 50,
    ) -> list[str]:
        """Discover recent persisted failure-analysis outputs to reuse as history."""
        return discover_failure_history_cids(
            self.db_conn,
            user_id=user_id,
            repo=repo,
            pr_number=pr_number,
            workflow_name=workflow_name,
            check_name=check_name,
            failure_target=failure_target,
            failure_target_type=failure_target_type,
            limit=limit,
        )

    def _select_failure_ai_capability(self, intent: ParsedIntent) -> dict[str, str]:
        """Select the backend capability for failure analysis intents."""
        provider = str(intent.entities.get("provider") or "").lower()
        if provider == "copilot_cli":
            return {
                "capability_id": "copilot.pr.failure_explain",
                "card_title": "Copilot failure analysis",
            }

        backend = str(intent.entities.get("failure_backend") or "").lower()
        if backend == "accelerated":
            return {
                "capability_id": "github.check.accelerated_failure_explain",
                "card_title": "Accelerated failure analysis",
            }

        policy = get_ai_backend_policy()
        if policy.failure_backend == "accelerated":
            return {
                "capability_id": "github.check.accelerated_failure_explain",
                "card_title": "Accelerated failure analysis",
            }

        if policy.failure_backend == "composite":
            return {
                "capability_id": "github.check.failure_rag_explain",
                "card_title": "Augmented failure analysis",
            }

        return {
            "capability_id": "copilot.pr.failure_explain",
            "card_title": "Copilot failure analysis",
        }

    def _select_pr_summary_ai_capability(self, intent: ParsedIntent) -> dict[str, str]:
        """Select the backend capability for PR summary intents."""
        backend = str(intent.entities.get("summary_backend") or "").lower()
        if backend == "accelerated":
            return {
                "capability_id": "github.pr.accelerated_summary",
                "card_title": "Accelerated PR summary",
            }

        policy = get_ai_backend_policy()
        if policy.summary_backend == "accelerated":
            return {
                "capability_id": "github.pr.accelerated_summary",
                "card_title": "Accelerated PR summary",
            }

        return {
            "capability_id": "github.pr.rag_summary",
            "card_title": "Augmented PR summary",
        }

    def _ai_intent_requires_cli(self, intent_name: str) -> bool:
        """Return whether an AI intent depends on CLI-backed read access."""
        return intent_name in {
            "ai.explain_pr",
            "ai.summarize_diff",
            "ai.explain_failure",
        }

    def _use_cli_for_read_intents(self) -> bool:
        """Return whether CLI-backed read intents are enabled."""
        return (
            os.getenv("HANDSFREE_GH_CLI_ENABLED", "false").lower() == "true"
            or os.getenv("HANDSFREE_CLI_FIXTURE_MODE", "false").lower() == "true"
        )

    def _format_similar_failures_result(
        self,
        result: dict[str, Any],
        *,
        pr_num: int | None,
        profile_config: ProfileConfig,
    ) -> tuple[str, str, str]:
        """Render a user-facing summary for similar-failure retrieval results."""
        ranked_matches = list(result.get("ranked_matches") or [])
        headline = f"Similar failures for PR #{pr_num}" if pr_num else "Similar failures"
        if not ranked_matches:
            summary = "No similar prior failures were found in the current candidate set."
            return headline, summary, profile_config.truncate_spoken_text(summary)

        top_match = ranked_matches[0]
        summary = (
            f"Top match: PR {top_match.get('pr_number') or 'unknown'}"
            f" in {top_match.get('repo') or 'unknown repo'}"
            f" with score {top_match.get('score', 0):.2f}. "
            f"{top_match.get('summary') or ''}".strip()
        )
        spoken_text = profile_config.truncate_spoken_text(summary)
        return headline, summary, spoken_text

    def _format_pr_summary(
        self,
        pr_details: dict[str, Any],
        checks: list[dict[str, Any]],
        reviews: list[dict[str, Any]],
        profile_config: ProfileConfig,
    ) -> str:
        """Format PR summary based on profile verbosity.

        Args:
            pr_details: PR details dictionary
            checks: List of check run dictionaries
            reviews: List of review dictionaries
            profile_config: User's profile configuration

        Returns:
            Formatted spoken summary with appropriate detail level
        """
        pr_num = pr_details.get("pr_number", "unknown")
        title = pr_details.get("title", "Untitled")
        author = pr_details.get("author", "unknown")
        state = pr_details.get("state", "open")

        # Count check statuses
        checks_total = len(checks)
        checks_failing = sum(1 for c in checks if c.get("conclusion") == "failure")
        checks_pending = sum(1 for c in checks if c.get("status") != "completed")

        # Count reviews
        approvals = sum(1 for r in reviews if r.get("state") == "APPROVED")
        changes_requested = sum(1 for r in reviews if r.get("state") == "CHANGES_REQUESTED")

        # Check for security/critical labels
        labels = pr_details.get("labels", [])
        has_security = any(label.lower() in ["security", "vulnerability"] for label in labels)

        # Build summary based on profile
        if profile_config.profile == Profile.WORKOUT:
            # Ultra-brief: 1-2 sentences, key numbers only
            summary = f"PR {pr_num}: {title[:PR_TITLE_PREVIEW_LENGTH]}."
            if checks_failing > 0:
                summary += f" {checks_failing} failing."
            elif has_security:
                summary += " Security."
            return summary

        elif profile_config.profile == Profile.FOCUSED:
            # Brief, actionable items only
            summary = f"PR {pr_num}: {title}."
            if checks_failing > 0:
                summary += f" {checks_failing} checks failing."
            if changes_requested > 0:
                summary += " Changes requested."
            elif approvals > 0:
                summary += f" {approvals} approved."
            return summary

        elif profile_config.profile == Profile.RELAXED:
            # Detailed: full context, all details
            summary = f"Pull request {pr_num} by {author}: {title}."

            # Add description preview if available
            description = pr_details.get("description", "")
            if description:
                # Take first sentence or first 100 chars
                desc_preview = description.split(".")[0][:100]
                summary += f" Description: {desc_preview}."

            # Add check status
            if checks_total > 0:
                if checks_failing > 0:
                    summary += f" {checks_failing} of {checks_total} checks failing."
                elif checks_pending > 0:
                    summary += f" {checks_pending} checks still pending."
                else:
                    summary += f" All {checks_total} checks passing."

            # Add review status
            if approvals > 0:
                summary += f" {approvals} approval{'s' if approvals != 1 else ''}."
            if changes_requested > 0:
                summary += (
                    f" {changes_requested} reviewer{'s' if changes_requested != 1 else ''} "
                    "requested changes."
                )

            # Add state
            if state == "open":
                summary += " PR is open and awaiting review."

            # Security alert always included
            if has_security:
                summary += " SECURITY: This PR contains security-related changes."

            return summary

        else:
            # Moderate/default: balanced detail (2-4 sentences)
            summary = f"PR {pr_num}: {title}."

            # Add check status
            if checks_failing > 0:
                summary += f" {checks_failing} checks failing."
            elif checks_total > 0:
                summary += f" All {checks_total} checks passing."

            # Add review status
            if approvals > 0:
                summary += f" {approvals} approved."
            elif changes_requested > 0:
                summary += " Changes requested."

            # Security alert always included
            if has_security:
                summary += " Security changes included."

            return profile_config.truncate_summary(summary)

    def _handle_checks_intent(
        self, intent: ParsedIntent, profile_config: ProfileConfig
    ) -> dict[str, Any]:
        """Handle checks-related intents."""
        # If no GitHub provider, fall back to placeholder
        if not self.github_provider:
            spoken_text = "All checks passing."
            if profile_config.profile == Profile.WORKOUT:
                spoken_text = "Checks OK."
            spoken_text = profile_config.truncate_spoken_text(spoken_text)
            return {
                "status": "ok",
                "intent": intent.to_dict(),
                "spoken_text": spoken_text,
            }

        # Extract entities
        pr_number = intent.entities.get("pr_number")
        repo = intent.entities.get("repo")

        # PR-specific variant (preferred)
        if pr_number:
            # Use a default repo if not specified (in real app, would come from context)
            if not repo:
                repo = "owner/repo"  # Fallback for fixture mode

            try:
                checks = self.github_provider.get_pr_checks(repo, pr_number)
                spoken_text = self._format_checks_summary(checks, pr_number, profile_config)
            except Exception as e:
                # Log error and return fallback message
                logger.warning("Failed to fetch checks for PR %s: %s", pr_number, str(e))
                spoken_text = f"Could not fetch checks for PR {pr_number}."
                if profile_config.profile == Profile.WORKOUT:
                    spoken_text = "Check lookup failed."
        # Best-effort repo variant
        elif repo:
            # In a real implementation, this would query recent PRs or commits for the repo
            # For now, return a helpful message
            spoken_text = (
                "Checks lookup by repo requires more context. Try 'checks for pr <number>'."
            )
            if profile_config.profile == Profile.WORKOUT:
                spoken_text = "Need PR number."
        # Generic ci status (best-effort, no context)
        else:
            # Without context, we can't determine which PR/repo to check
            spoken_text = "Please specify a PR number, for example: 'checks for PR 123'."
            if profile_config.profile == Profile.WORKOUT:
                spoken_text = "Need PR number."

        # Apply profile-based truncation
        spoken_text = profile_config.truncate_spoken_text(spoken_text)

        return {
            "status": "ok",
            "intent": intent.to_dict(),
            "spoken_text": spoken_text,
        }

    def _format_checks_summary(
        self, checks: list[dict[str, Any]], pr_number: int, profile_config: ProfileConfig
    ) -> str:
        """Format a privacy-safe spoken summary of check results.

        Args:
            checks: List of check run dictionaries
            pr_number: PR number
            profile_config: User's profile configuration

        Returns:
            Spoken summary string
        """
        total = len(checks)
        if total == 0:
            if profile_config.profile == Profile.WORKOUT:
                return "No checks."
            return f"PR {pr_number} has no checks."

        # Count check statuses
        passed = sum(1 for c in checks if c.get("conclusion") == "success")
        failed = sum(1 for c in checks if c.get("conclusion") == "failure")
        pending = sum(1 for c in checks if c.get("status") != "completed")

        # Build spoken text based on status
        if failed > 0:
            # Get the first failing check name (privacy-safe)
            first_failing = next(
                (c.get("name", "unknown") for c in checks if c.get("conclusion") == "failure"),
                None,
            )
            if profile_config.profile == Profile.WORKOUT:
                spoken_text = f"{failed} failing, {passed} passing."
                if first_failing:
                    spoken_text += f" First: {first_failing}."
            else:
                spoken_text = (
                    f"PR {pr_number}: {failed} check{'s' if failed != 1 else ''} failing, "
                    f"{passed} passing."
                )
                if first_failing:
                    spoken_text += f" First failing check: {first_failing}."
        elif pending > 0:
            if profile_config.profile == Profile.WORKOUT:
                spoken_text = f"{pending} pending, {passed} passing."
            else:
                spoken_text = (
                    f"PR {pr_number}: {pending} check{'s' if pending != 1 else ''} pending, "
                    f"{passed} passing."
                )
        else:
            # All passing
            if profile_config.profile == Profile.WORKOUT:
                spoken_text = "All checks passing."
            else:
                spoken_text = (
                    f"PR {pr_number}: all {total} check{'s' if total != 1 else ''} passing."
                )

        return spoken_text

    def _get_effective_user_id(self, user_id: str | None) -> str:
        """Get effective user ID, falling back to fixture user if none provided.

        Args:
            user_id: Optional user identifier from request.

        Returns:
            User ID to use for operations (authenticated user or fixture user).
        """
        return user_id if user_id else FIXTURE_USER_ID

    def _handle_agent_intent(
        self,
        intent: ParsedIntent,
        profile_config: ProfileConfig,
        user_id: str | None = None,
        session_id: str | None = None,
    ) -> dict[str, Any]:
        """Handle agent-related intents.

        Args:
            intent: Parsed agent intent
            profile_config: User's profile configuration
            user_id: User identifier (required for agent operations)
            session_id: Optional session identifier for result navigation
        """
        if intent.name == "agent.delegate":
            # This should normally be caught by confirmation flow,
            # but handle it here if confirmation was bypassed
            if not self._agent_service:
                spoken_text = profile_config.truncate_spoken_text("Agent service not available.")
                return {
                    "status": "error",
                    "intent": intent.to_dict(),
                    "spoken_text": spoken_text,
                }

            if not user_id:
                spoken_text = profile_config.truncate_spoken_text(
                    "User authentication required for agent delegation."
                )
                return {
                    "status": "error",
                    "intent": intent.to_dict(),
                    "spoken_text": spoken_text,
                }

            # Extract entities
            instruction = intent.entities.get("instruction", "handle this")
            issue_num = intent.entities.get("issue_number")
            pr_num = intent.entities.get("pr_number")
            provider = intent.entities.get("provider", "copilot")
            provider_descriptor = get_provider_descriptor(provider)
            provider_label = provider_descriptor.display_name if provider_descriptor else provider
            inferred_capability = resolve_provider_capability(
                provider,
                intent.entities.get("mcp_capability"),
                instruction,
            ) or infer_provider_capability(provider, instruction)
            preferred_execution_mode = intent.entities.get("mcp_preferred_execution_mode")
            resolved_execution_mode = resolve_capability_execution_mode(
                provider,
                inferred_capability,
                preferred_execution_mode,
            )

            target_type = None
            target_ref = None
            if issue_num:
                target_type = "issue"
                target_ref = f"#{issue_num}"
            elif pr_num:
                target_type = "pr"
                target_ref = f"#{pr_num}"

            # Build trace with intent information
            from datetime import UTC, datetime

            trace = {
                "intent_name": intent.name,
                "provider_label": provider_label,
                "mcp_capability": inferred_capability,
                "mcp_execution_mode": resolved_execution_mode,
                "entities": {
                    "instruction": instruction,
                    "issue_number": issue_num,
                    "pr_number": pr_num,
                    "provider": provider,
                    "provider_label": provider_label,
                    "mcp_capability": inferred_capability,
                    "mcp_execution_mode": resolved_execution_mode,
                    "mcp_preferred_execution_mode": preferred_execution_mode,
                },
                "created_at": datetime.now(UTC).isoformat(),
            }

            for key in (
                "mcp_input",
                "mcp_cid",
                "mcp_pin_action",
                "mcp_seed_url",
                "mcp_texts",
                "mcp_preferred_execution_mode",
            ):
                value = intent.entities.get(key)
                if value is not None:
                    trace[key] = value
                    trace["entities"][key] = value

            # Create task with authenticated user_id
            result = self._agent_service.delegate(
                user_id=user_id,
                instruction=instruction,
                provider=provider,
                target_type=target_type,
                target_ref=target_ref,
                trace=trace,
            )

            spoken_text = result.get("spoken_text", "Agent task created.")
            spoken_text = (
                f"{spoken_text}"
                f"{_execution_mode_policy_note(preferred_execution_mode, resolved_execution_mode)}"
            )
            spoken_text = profile_config.truncate_spoken_text(spoken_text)

            response_intent = intent.to_dict()
            response_intent.setdefault("entities", {})
            response_intent["entities"] = dict(response_intent["entities"]) | {
                "task_id": result.get("task_id"),
                "provider": provider,
                "state": result.get("state"),
                "mcp_execution_mode": resolved_execution_mode,
            }

            response: dict[str, Any] = {
                "status": "ok",
                "intent": response_intent,
                "spoken_text": spoken_text,
                "debug": {
                    "tool_calls": [
                        {
                            "task_id": result.get("task_id"),
                            "provider": result.get("provider"),
                            "state": result.get("state"),
                            "mcp_execution_mode": resolved_execution_mode,
                        }
                    ]
                },
            }

            if result.get("state") == "completed" and result.get("result_output"):
                output = result["result_output"]
                capability_label = (inferred_capability or "result").replace("_", " ")
                card_lines = _render_agent_result_lines(result.get("result_preview"), output)
                response["cards"] = [
                    {
                        "title": f"{provider_label} {capability_label}",
                        "subtitle": f"Task {str(result.get('task_id', ''))[:8]} • completed",
                        "lines": card_lines[:3] or [spoken_text],
                    }
                ]
                response["debug"]["tool_calls"][0]["result_output"] = output
            else:
                card_lines = [
                    f"Provider: {result.get('provider')}",
                    f"Instruction: {instruction}",
                    f"State: {result.get('state')}",
                ]
                execution_line = _execution_mode_detail_line(
                    preferred_execution_mode,
                    resolved_execution_mode,
                )
                if execution_line:
                    card_lines.append(execution_line)
                response["cards"] = [
                    {
                        "title": "Agent Task Created",
                        "subtitle": f"Task {str(result.get('task_id', ''))[:8]}",
                        "lines": card_lines,
                    }
                ]

            execution_line = _execution_mode_detail_line(
                preferred_execution_mode,
                resolved_execution_mode,
            )
            if execution_line and response.get("cards"):
                first_card = response["cards"][0]
                if isinstance(first_card, dict):
                    lines = first_card.get("lines")
                    if isinstance(lines, list) and execution_line not in lines:
                        lines.append(execution_line)

            return response

        elif intent.name == "agent.status":
            if not self._agent_service:
                spoken_text = "Agent service not available."
            else:
                if not user_id:
                    spoken_text = "User authentication required."
                else:
                    # Get status for authenticated user
                    result = self._agent_service.get_status(user_id=user_id)
                    spoken_text = result.get("spoken_text", "No agent tasks.")

            spoken_text = profile_config.truncate_spoken_text(spoken_text)

            cards: list[dict[str, Any]] = []
            tool_calls: list[dict[str, Any]] = []
            if self._agent_service and user_id:
                for task in result.get("tasks", [])[:5]:
                    instruction = task.get("instruction")
                    if instruction and len(instruction) > 60:
                        instruction_display = instruction[:60] + "..."
                    else:
                        instruction_display = instruction or "No instruction"

                    card_lines = [f"Instruction: {instruction_display}"]
                    card_lines.extend(
                        _render_agent_result_lines(
                            task.get("result_preview"),
                            task.get("result_output"),
                        )
                    )
                    execution_line = _execution_mode_detail_line(
                        task.get("mcp_preferred_execution_mode"),
                        task.get("mcp_execution_mode"),
                    )
                    if execution_line and execution_line not in card_lines:
                        card_lines.append(execution_line)
                    cards.append(
                        {
                            "title": f"Task {str(task.get('id', ''))[:8]}",
                            "subtitle": f"{task.get('state')} • {task.get('provider', 'unknown')}",
                            "lines": card_lines[:4],
                        }
                    )

                    tool_call = {
                        "task_id": task.get("id"),
                        "provider": task.get("provider"),
                        "state": task.get("state"),
                    }
                    if task.get("result_output") is not None:
                        tool_call["result_output"] = task["result_output"]
                    tool_calls.append(tool_call)

            return {
                "status": "ok",
                "intent": intent.to_dict(),
                "spoken_text": spoken_text,
                "cards": cards,
                "debug": {"tool_calls": tool_calls},
            }

        elif intent.name == "agent.results":
            if not self.db_conn:
                spoken_text = profile_config.truncate_spoken_text("Agent service not available.")
                return {
                    "status": "ok",
                    "intent": intent.to_dict(),
                    "spoken_text": spoken_text,
                }
            if not user_id:
                spoken_text = profile_config.truncate_spoken_text("User authentication required.")
                return {
                    "status": "error",
                    "intent": intent.to_dict(),
                    "spoken_text": spoken_text,
                }

            from handsfree.db.agent_tasks import get_agent_tasks

            view = intent.entities.get("view")
            try:
                resolved = resolve_result_query(view=view)
            except ValueError as exc:
                spoken_text = profile_config.truncate_spoken_text(str(exc))
                return {
                    "status": "error",
                    "intent": intent.to_dict(),
                    "spoken_text": spoken_text,
                }

            tasks = get_agent_tasks(
                conn=self.db_conn,
                user_id=user_id,
                provider=resolved["provider"],
                state="completed",
                sort_by=resolved["sort"],
                direction=resolved["direction"],
                limit=100,
                offset=0,
            )
            tasks = _filter_router_result_tasks(
                tasks,
                capability=resolved["capability"],
                latest_only=bool(resolved["latest_only"]),
            )

            if not tasks:
                spoken_text = profile_config.truncate_spoken_text("No agent results found.")
                return {
                    "status": "ok",
                    "intent": intent.to_dict(),
                    "spoken_text": spoken_text,
                    "cards": [],
                    "debug": {"tool_calls": []},
                }

            view_label = str(resolved["view"] or "results").replace("_", " ")
            spoken_text = profile_config.truncate_spoken_text(
                f"{len(tasks)} {view_label} result{'s' if len(tasks) != 1 else ''}."
            )
            cards: list[dict[str, Any]] = []
            tool_calls: list[dict[str, Any]] = []
            for task in tasks[:5]:
                trace = task.trace if isinstance(task.trace, dict) else {}
                output = _trace_result_output(trace)
                cards.append(_build_result_card(task))
                tool_call = {
                    "task_id": task.id,
                    "provider": task.provider,
                    "state": task.state,
                }
                if output is not None:
                    tool_call["result_output"] = output
                tool_calls.append(tool_call)

            response_intent = intent.to_dict()
            response_intent.setdefault("entities", {})
            response_intent["entities"] = dict(response_intent["entities"]) | {
                "view": resolved["view"],
                "result_count": len(tasks),
            }

            return {
                "status": "ok",
                "intent": response_intent,
                "spoken_text": spoken_text,
                "cards": cards,
                "debug": {"tool_calls": tool_calls},
            }

        elif intent.name == "agent.result_open":
            card = self._get_current_navigation_card(session_id)
            if not card:
                spoken_text = profile_config.truncate_spoken_text(
                    "No result selected. Ask for agent results first."
                )
                return {
                    "status": "ok",
                    "intent": intent.to_dict(),
                    "spoken_text": spoken_text,
                }
            deep_link = card.get("deep_link")
            spoken_text = profile_config.truncate_spoken_text("Opening the current result.")
            return {
                "status": "ok",
                "intent": intent.to_dict(),
                "spoken_text": spoken_text,
                "cards": [card],
                "debug": {"tool_calls": [{"deep_link": deep_link}]},
            }

        elif intent.name == "agent.result_actions":
            card = self._get_current_navigation_card(session_id)
            if not card:
                spoken_text = profile_config.truncate_spoken_text(
                    "No result selected. Ask for agent results first."
                )
                return {
                    "status": "ok",
                    "intent": intent.to_dict(),
                    "spoken_text": spoken_text,
                }

            actions = _available_result_actions(card)
            spoken_text = profile_config.truncate_spoken_text(
                f"You can {actions[0]}, {actions[1]}, or {actions[2]}."
            )
            return {
                "status": "ok",
                "intent": intent.to_dict(),
                "spoken_text": spoken_text,
                "cards": [
                    {
                        "title": "Available result actions",
                        "subtitle": card.get("title", "Current result"),
                        "lines": actions[:6],
                        "task_id": card.get("task_id"),
                        "deep_link": card.get("deep_link"),
                        "action_items": _build_result_action_items(card),
                        "actions": actions,
                    }
                ],
                "debug": {"tool_calls": [{"actions": actions, "action_items": _build_result_action_items(card)}]},
            }

        elif intent.name == "agent.result_details":
            if not self.db_conn:
                spoken_text = profile_config.truncate_spoken_text("Agent service not available.")
                return {
                    "status": "error",
                    "intent": intent.to_dict(),
                    "spoken_text": spoken_text,
                }
            if not user_id:
                spoken_text = profile_config.truncate_spoken_text("User authentication required.")
                return {
                    "status": "error",
                    "intent": intent.to_dict(),
                    "spoken_text": spoken_text,
                }

            card = self._get_current_navigation_card(session_id)
            if not card:
                spoken_text = profile_config.truncate_spoken_text(
                    "No result selected. Ask for agent results first."
                )
                return {
                    "status": "ok",
                    "intent": intent.to_dict(),
                    "spoken_text": spoken_text,
                }

            from handsfree.db.agent_tasks import get_agent_task_by_id

            task_id = card.get("task_id")
            if not isinstance(task_id, str) or not task_id:
                spoken_text = profile_config.truncate_spoken_text(
                    "The current result does not have task details."
                )
                return {
                    "status": "error",
                    "intent": intent.to_dict(),
                    "spoken_text": spoken_text,
                }

            task = get_agent_task_by_id(self.db_conn, task_id)
            if not task or task.user_id != user_id:
                spoken_text = profile_config.truncate_spoken_text("The current result is unavailable.")
                return {
                    "status": "error",
                    "intent": intent.to_dict(),
                    "spoken_text": spoken_text,
                }

            trace = task.trace if isinstance(task.trace, dict) else {}
            provider_label = trace.get("provider_label") or task.provider
            capability = trace.get("mcp_capability")
            preview = _trace_result_preview(trace)
            output = _trace_result_output(trace)
            lines = [
                f"State: {task.state}",
                f"Instruction: {task.instruction or 'No instruction'}",
            ]
            if capability:
                lines.insert(1, f"Capability: {str(capability).replace('_', ' ')}")
            lines.extend(
                _render_agent_result_lines(
                    preview,
                    output if isinstance(output, dict) else None,
                )
            )

            spoken_parts = [str(provider_label)]
            if capability:
                spoken_parts.append(str(capability).replace("_", " "))
            spoken_text = profile_config.truncate_spoken_text(
                " ".join(spoken_parts) + f" details. State {task.state}."
            )
            return {
                "status": "ok",
                "intent": {
                    "name": intent.name,
                    "confidence": intent.confidence,
                    "entities": {"task_id": task.id},
                },
                "spoken_text": spoken_text,
                "cards": [
                    {
                        "title": f"{provider_label} details",
                        "subtitle": f"Task {task.id[:8]}",
                        "lines": lines[:6],
                        "deep_link": _result_task_deep_link(task),
                        "task_id": task.id,
                    }
                ],
                "debug": {
                    "tool_calls": [
                        {
                            "task_id": task.id,
                            "provider": task.provider,
                            "state": task.state,
                            "result_output": output,
                        }
                    ]
                },
            }

        elif intent.name == "agent.result_related":
            if not self.db_conn:
                spoken_text = profile_config.truncate_spoken_text("Agent service not available.")
                return {
                    "status": "error",
                    "intent": intent.to_dict(),
                    "spoken_text": spoken_text,
                }
            if not user_id:
                spoken_text = profile_config.truncate_spoken_text("User authentication required.")
                return {
                    "status": "error",
                    "intent": intent.to_dict(),
                    "spoken_text": spoken_text,
                }

            card = self._get_current_navigation_card(session_id)
            if not card:
                spoken_text = profile_config.truncate_spoken_text(
                    "No result selected. Ask for agent results first."
                )
                return {
                    "status": "ok",
                    "intent": intent.to_dict(),
                    "spoken_text": spoken_text,
                }

            from handsfree.db.agent_tasks import get_agent_tasks

            provider = card.get("provider")
            capability = card.get("capability")
            source_task_id = card.get("task_id")
            tasks = get_agent_tasks(
                conn=self.db_conn,
                user_id=user_id,
                provider=provider if isinstance(provider, str) else None,
                state="completed",
                sort_by="updated_at",
                direction="desc",
                limit=100,
                offset=0,
            )
            tasks = _filter_router_result_tasks(
                tasks,
                capability=capability if isinstance(capability, str) else None,
                latest_only=False,
            )
            if isinstance(source_task_id, str):
                tasks = [task for task in tasks if task.id != source_task_id]

            if not tasks:
                spoken_text = profile_config.truncate_spoken_text("No related agent results found.")
                return {
                    "status": "ok",
                    "intent": intent.to_dict(),
                    "spoken_text": spoken_text,
                    "cards": [],
                    "debug": {"tool_calls": []},
                }

            spoken_text = profile_config.truncate_spoken_text(
                f"{len(tasks)} related result{'s' if len(tasks) != 1 else ''}."
            )
            return {
                "status": "ok",
                "intent": {
                    "name": intent.name,
                    "confidence": intent.confidence,
                    "entities": {
                        "provider": provider,
                        "capability": capability,
                        "source_task_id": source_task_id,
                        "result_count": len(tasks),
                    },
                },
                "spoken_text": spoken_text,
                "cards": [_build_result_card(task) for task in tasks[:5]],
                "debug": {
                    "tool_calls": [
                        {
                            "task_id": task.id,
                            "provider": task.provider,
                            "state": task.state,
                        }
                        for task in tasks[:5]
                    ]
                },
            }

        elif intent.name == "agent.result_read":
            card = self._get_current_navigation_card(session_id)
            if not card:
                spoken_text = profile_config.truncate_spoken_text(
                    "No result selected. Ask for agent results first."
                )
                return {
                    "status": "ok",
                    "intent": intent.to_dict(),
                    "spoken_text": spoken_text,
                }
            cid = _extract_cid_from_deep_link(card.get("deep_link"))
            if not cid:
                spoken_text = profile_config.truncate_spoken_text(
                    "The current result is not an IPFS CID."
                )
                return {
                    "status": "error",
                    "intent": intent.to_dict(),
                    "spoken_text": spoken_text,
                }
            return self._handle_ai_intent(
                ParsedIntent(name="ai.read_cid", confidence=0.95, entities={"cid": cid}),
                profile_config,
                session_id=session_id,
            )

        elif intent.name == "agent.result_save_ipfs":
            if not self._agent_service or not self.db_conn:
                spoken_text = profile_config.truncate_spoken_text("Agent service not available.")
                return {
                    "status": "error",
                    "intent": intent.to_dict(),
                    "spoken_text": spoken_text,
                }
            if not user_id:
                spoken_text = profile_config.truncate_spoken_text(
                    "User authentication required for agent delegation."
                )
                return {
                    "status": "error",
                    "intent": intent.to_dict(),
                    "spoken_text": spoken_text,
                }

            card = self._get_current_navigation_card(session_id)
            if not card:
                spoken_text = profile_config.truncate_spoken_text(
                    "No result selected. Ask for agent results first."
                )
                return {
                    "status": "ok",
                    "intent": intent.to_dict(),
                    "spoken_text": spoken_text,
                }

            from handsfree.db.agent_tasks import get_agent_task_by_id

            source_task_id = card.get("task_id")
            if not isinstance(source_task_id, str) or not source_task_id:
                spoken_text = profile_config.truncate_spoken_text(
                    "The current result cannot be saved to IPFS."
                )
                return {
                    "status": "error",
                    "intent": intent.to_dict(),
                    "spoken_text": spoken_text,
                }

            source_task = get_agent_task_by_id(self.db_conn, source_task_id)
            if not source_task or source_task.user_id != user_id:
                spoken_text = profile_config.truncate_spoken_text("The current result is unavailable.")
                return {
                    "status": "error",
                    "intent": intent.to_dict(),
                    "spoken_text": spoken_text,
                }

            serialized_result = _serialize_result_for_ipfs(source_task, card)
            preferred_mode = (
                str(
                    intent.entities.get("mcp_preferred_execution_mode")
                    or intent.entities.get("mcp_execution_mode")
                    or ""
                ).strip().lower()
                or None
            )
            resolved_execution_mode = resolve_capability_execution_mode(
                "ipfs_kit_mcp",
                "ipfs_add",
                preferred_mode,
            )
            result = self._agent_service.delegate(
                user_id=user_id,
                instruction="save selected result to ipfs",
                provider="ipfs_kit_mcp",
                trace={
                    "intent_name": intent.name,
                    "provider_label": "IPFS Kit",
                    "mcp_capability": "ipfs_add",
                    "mcp_input": serialized_result,
                    "source_task_id": source_task.id,
                    "saved_result_provider": source_task.provider,
                    "saved_result_capability": (source_task.trace or {}).get("mcp_capability")
                    if isinstance(source_task.trace, dict)
                    else None,
                    "mcp_preferred_execution_mode": preferred_mode,
                },
            )
            spoken_text = profile_config.truncate_spoken_text(
                f"{result.get('spoken_text', 'Saving the current result to IPFS.')}"
                f"{_execution_mode_policy_note(preferred_mode, resolved_execution_mode)}"
            )
            card_lines = [
                f"From task: {source_task.id[:8]}",
                f"State: {result.get('state')}",
            ]
            execution_line = _execution_mode_detail_line(preferred_mode, resolved_execution_mode)
            if execution_line:
                card_lines.append(execution_line)
            return {
                "status": "ok",
                "intent": {
                    "name": intent.name,
                    "confidence": intent.confidence,
                    "entities": {
                        "source_task_id": source_task.id,
                        "task_id": result.get("task_id"),
                        "provider": result.get("provider"),
                        "mcp_execution_mode": resolved_execution_mode,
                        "mcp_preferred_execution_mode": preferred_mode,
                    },
                },
                "spoken_text": spoken_text,
                "cards": [
                    {
                        "title": "Result save requested",
                        "subtitle": f"Task {str(result.get('task_id', ''))[:8]}",
                        "lines": card_lines,
                    }
                ],
                "debug": {
                    "tool_calls": [
                        {
                            "task_id": result.get("task_id"),
                            "provider": result.get("provider"),
                            "state": result.get("state"),
                            "source_task_id": source_task.id,
                        }
                    ]
                },
            }

        elif intent.name == "agent.result_share":
            card = self._get_current_navigation_card(session_id)
            if not card:
                spoken_text = profile_config.truncate_spoken_text(
                    "No result selected. Ask for agent results first."
                )
                return {
                    "status": "ok",
                    "intent": intent.to_dict(),
                    "spoken_text": spoken_text,
                }
            cid = _extract_cid_from_deep_link(card.get("deep_link"))
            if not cid:
                spoken_text = profile_config.truncate_spoken_text(
                    "The current result is not an IPFS CID."
                )
                return {
                    "status": "error",
                    "intent": intent.to_dict(),
                    "spoken_text": spoken_text,
                }

            share_payload = {
                "cid": cid,
                "uri": f"ipfs://{cid}",
                "text": f"IPFS CID: {cid}",
            }
            spoken_text = profile_config.truncate_spoken_text(f"Share this CID: {cid}.")
            return {
                "status": "ok",
                "intent": {
                    "name": intent.name,
                    "confidence": intent.confidence,
                    "entities": {"cid": cid},
                },
                "spoken_text": spoken_text,
                "cards": [
                    {
                        "title": "Share IPFS CID",
                        "subtitle": card.get("title", "Current result"),
                        "lines": [f"CID: {cid}", f"URI: ipfs://{cid}"],
                        "deep_link": f"ipfs://{cid}",
                    }
                ],
                "debug": {"tool_calls": [{"share_payload": share_payload}]},
            }

        elif intent.name == "agent.result_pin":
            if not self._agent_service:
                spoken_text = profile_config.truncate_spoken_text("Agent service not available.")
                return {
                    "status": "error",
                    "intent": intent.to_dict(),
                    "spoken_text": spoken_text,
                }
            if not user_id:
                spoken_text = profile_config.truncate_spoken_text(
                    "User authentication required for agent delegation."
                )
                return {
                    "status": "error",
                    "intent": intent.to_dict(),
                    "spoken_text": spoken_text,
                }

            card = self._get_current_navigation_card(session_id)
            if not card:
                spoken_text = profile_config.truncate_spoken_text(
                    "No result selected. Ask for agent results first."
                )
                return {
                    "status": "ok",
                    "intent": intent.to_dict(),
                    "spoken_text": spoken_text,
                }
            cid = _extract_cid_from_deep_link(card.get("deep_link"))
            if not cid:
                spoken_text = profile_config.truncate_spoken_text(
                    "The current result is not an IPFS CID."
                )
                return {
                    "status": "error",
                    "intent": intent.to_dict(),
                    "spoken_text": spoken_text,
                }

            resolved_execution_mode = resolve_capability_execution_mode(
                "ipfs_kit_mcp",
                "ipfs_pin",
                intent.entities.get("mcp_preferred_execution_mode"),
            )
            result = self._agent_service.delegate(
                user_id=user_id,
                instruction=f"pin {cid} on ipfs",
                provider="ipfs_kit_mcp",
                trace={
                    "intent_name": intent.name,
                    "provider_label": "IPFS Kit",
                    "mcp_capability": "ipfs_pin",
                    "mcp_execution_mode": resolved_execution_mode,
                    "mcp_preferred_execution_mode": intent.entities.get("mcp_preferred_execution_mode"),
                    "mcp_cid": cid,
                    "mcp_pin_action": "pin",
                },
            )
            spoken_text = profile_config.truncate_spoken_text(
                f"{result.get('spoken_text', f'Pinning {cid} on IPFS.')}"
                f"{_execution_mode_policy_note(intent.entities.get('mcp_preferred_execution_mode'), resolved_execution_mode)}"
            )
            card_lines = [f"CID: {cid}", f"State: {result.get('state')}"]
            execution_line = _execution_mode_detail_line(
                intent.entities.get("mcp_preferred_execution_mode"),
                resolved_execution_mode,
            )
            if execution_line:
                card_lines.append(execution_line)
            return {
                "status": "ok",
                "intent": {
                    "name": intent.name,
                    "confidence": intent.confidence,
                    "entities": {
                        "cid": cid,
                        "task_id": result.get("task_id"),
                        "mcp_execution_mode": resolved_execution_mode,
                    },
                },
                "spoken_text": spoken_text,
                "cards": [
                    {
                        "title": "IPFS pin requested",
                        "subtitle": f"Task {str(result.get('task_id', ''))[:8]}",
                        "lines": card_lines,
                    }
                ],
                "debug": {
                    "tool_calls": [
                        {
                            "task_id": result.get("task_id"),
                            "provider": result.get("provider"),
                            "state": result.get("state"),
                            "cid": cid,
                            "mcp_execution_mode": resolved_execution_mode,
                        }
                    ]
                },
            }

        elif intent.name == "agent.result_unpin":
            if not self._agent_service:
                spoken_text = profile_config.truncate_spoken_text("Agent service not available.")
                return {
                    "status": "error",
                    "intent": intent.to_dict(),
                    "spoken_text": spoken_text,
                }
            if not user_id:
                spoken_text = profile_config.truncate_spoken_text(
                    "User authentication required for agent delegation."
                )
                return {
                    "status": "error",
                    "intent": intent.to_dict(),
                    "spoken_text": spoken_text,
                }

            card = self._get_current_navigation_card(session_id)
            if not card:
                spoken_text = profile_config.truncate_spoken_text(
                    "No result selected. Ask for agent results first."
                )
                return {
                    "status": "ok",
                    "intent": intent.to_dict(),
                    "spoken_text": spoken_text,
                }
            cid = _extract_cid_from_deep_link(card.get("deep_link"))
            if not cid:
                spoken_text = profile_config.truncate_spoken_text(
                    "The current result is not an IPFS CID."
                )
                return {
                    "status": "error",
                    "intent": intent.to_dict(),
                    "spoken_text": spoken_text,
                }

            resolved_execution_mode = resolve_capability_execution_mode(
                "ipfs_kit_mcp",
                "ipfs_pin",
                intent.entities.get("mcp_preferred_execution_mode"),
            )
            result = self._agent_service.delegate(
                user_id=user_id,
                instruction=f"unpin {cid} on ipfs",
                provider="ipfs_kit_mcp",
                trace={
                    "intent_name": intent.name,
                    "provider_label": "IPFS Kit",
                    "mcp_capability": "ipfs_pin",
                    "mcp_execution_mode": resolved_execution_mode,
                    "mcp_preferred_execution_mode": intent.entities.get("mcp_preferred_execution_mode"),
                    "mcp_cid": cid,
                    "mcp_pin_action": "unpin",
                },
            )
            spoken_text = profile_config.truncate_spoken_text(
                f"{result.get('spoken_text', f'Unpinning {cid} on IPFS.')}"
                f"{_execution_mode_policy_note(intent.entities.get('mcp_preferred_execution_mode'), resolved_execution_mode)}"
            )
            card_lines = [f"CID: {cid}", f"State: {result.get('state')}"]
            execution_line = _execution_mode_detail_line(
                intent.entities.get("mcp_preferred_execution_mode"),
                resolved_execution_mode,
            )
            if execution_line:
                card_lines.append(execution_line)
            return {
                "status": "ok",
                "intent": {
                    "name": intent.name,
                    "confidence": intent.confidence,
                    "entities": {
                        "cid": cid,
                        "task_id": result.get("task_id"),
                        "mcp_execution_mode": resolved_execution_mode,
                    },
                },
                "spoken_text": spoken_text,
                "cards": [
                    {
                        "title": "IPFS unpin requested",
                        "subtitle": f"Task {str(result.get('task_id', ''))[:8]}",
                        "lines": card_lines,
                    }
                ],
                "debug": {
                    "tool_calls": [
                        {
                            "task_id": result.get("task_id"),
                            "provider": result.get("provider"),
                            "state": result.get("state"),
                            "cid": cid,
                            "pin_action": "unpin",
                            "mcp_execution_mode": resolved_execution_mode,
                        }
                    ]
                },
            }

        elif intent.name == "agent.result_rerun":
            if not self._agent_service or not self.db_conn:
                spoken_text = profile_config.truncate_spoken_text("Agent service not available.")
                return {
                    "status": "error",
                    "intent": intent.to_dict(),
                    "spoken_text": spoken_text,
                }
            if not user_id:
                spoken_text = profile_config.truncate_spoken_text(
                    "User authentication required for agent delegation."
                )
                return {
                    "status": "error",
                    "intent": intent.to_dict(),
                    "spoken_text": spoken_text,
                }

            card = self._get_current_navigation_card(session_id)
            if not card:
                spoken_text = profile_config.truncate_spoken_text(
                    "No result selected. Ask for agent results first."
                )
                return {
                    "status": "ok",
                    "intent": intent.to_dict(),
                    "spoken_text": spoken_text,
                }

            from handsfree.db.agent_tasks import get_agent_task_by_id

            source_task_id = card.get("task_id")
            if not isinstance(source_task_id, str) or not source_task_id:
                spoken_text = profile_config.truncate_spoken_text(
                    "The current result cannot be rerun."
                )
                return {
                    "status": "error",
                    "intent": intent.to_dict(),
                    "spoken_text": spoken_text,
                }

            source_task = get_agent_task_by_id(self.db_conn, source_task_id)
            if not source_task or source_task.user_id != user_id:
                spoken_text = profile_config.truncate_spoken_text("The current result is unavailable.")
                return {
                    "status": "error",
                    "intent": intent.to_dict(),
                    "spoken_text": spoken_text,
                }

            source_trace = source_task.trace if isinstance(source_task.trace, dict) else {}
            capability = source_trace.get("mcp_capability")
            if source_task.provider != "ipfs_accelerate_mcp" or capability not in {
                "workflow",
                "agentic_fetch",
            }:
                spoken_text = profile_config.truncate_spoken_text(
                    "The current result is not a rerunnable workflow."
                )
                return {
                    "status": "error",
                    "intent": intent.to_dict(),
                    "spoken_text": spoken_text,
                }

            resolved_execution_mode = resolve_capability_execution_mode(
                "ipfs_accelerate_mcp",
                str(capability),
                intent.entities.get("mcp_preferred_execution_mode"),
            )
            rerun_trace = {
                "intent_name": intent.name,
                "provider_label": source_trace.get("provider_label", "IPFS Accelerate"),
                "mcp_capability": capability,
                "mcp_execution_mode": resolved_execution_mode,
                "mcp_preferred_execution_mode": intent.entities.get("mcp_preferred_execution_mode"),
                "rerun_of_task_id": source_task.id,
                "source_task_id": source_task.id,
            }
            for key in ("mcp_input", "mcp_seed_url", "mcp_target_terms", "mcp_workflow_name"):
                value = source_trace.get(key)
                if value is not None:
                    rerun_trace[key] = value

            instruction = source_task.instruction or "rerun workflow"
            result = self._agent_service.delegate(
                user_id=user_id,
                instruction=instruction,
                provider="ipfs_accelerate_mcp",
                target_type=source_task.target_type,
                target_ref=source_task.target_ref,
                trace=rerun_trace,
            )
            spoken_text = profile_config.truncate_spoken_text(
                result.get("spoken_text", "Workflow rerun requested.")
            )
            return {
                "status": "ok",
                "intent": {
                    "name": intent.name,
                    "confidence": intent.confidence,
                    "entities": {
                        "source_task_id": source_task.id,
                        "task_id": result.get("task_id"),
                        "provider": result.get("provider"),
                        "mcp_execution_mode": resolved_execution_mode,
                    },
                },
                "spoken_text": spoken_text,
                "cards": [
                    {
                        "title": "Workflow rerun requested",
                        "subtitle": f"Task {str(result.get('task_id', ''))[:8]}",
                        "lines": [
                            f"From task: {source_task.id[:8]}",
                            f"Capability: {str(capability).replace('_', ' ')}",
                            f"State: {result.get('state')}",
                        ],
                    }
                ],
                "debug": {
                    "tool_calls": [
                        {
                            "task_id": result.get("task_id"),
                            "provider": result.get("provider"),
                            "state": result.get("state"),
                            "source_task_id": source_task.id,
                            "capability": capability,
                            "mcp_execution_mode": resolved_execution_mode,
                        }
                    ]
                },
            }

        elif intent.name == "agent.result_rerun_fetch":
            if not self._agent_service or not self.db_conn:
                spoken_text = profile_config.truncate_spoken_text("Agent service not available.")
                return {
                    "status": "error",
                    "intent": intent.to_dict(),
                    "spoken_text": spoken_text,
                }
            if not user_id:
                spoken_text = profile_config.truncate_spoken_text(
                    "User authentication required for agent delegation."
                )
                return {
                    "status": "error",
                    "intent": intent.to_dict(),
                    "spoken_text": spoken_text,
                }

            card = self._get_current_navigation_card(session_id)
            if not card:
                spoken_text = profile_config.truncate_spoken_text(
                    "No result selected. Ask for agent results first."
                )
                return {
                    "status": "ok",
                    "intent": intent.to_dict(),
                    "spoken_text": spoken_text,
                }

            from handsfree.db.agent_tasks import get_agent_task_by_id

            source_task_id = card.get("task_id")
            if not isinstance(source_task_id, str) or not source_task_id:
                spoken_text = profile_config.truncate_spoken_text(
                    "The current result cannot be rerun."
                )
                return {
                    "status": "error",
                    "intent": intent.to_dict(),
                    "spoken_text": spoken_text,
                }

            source_task = get_agent_task_by_id(self.db_conn, source_task_id)
            if not source_task or source_task.user_id != user_id:
                spoken_text = profile_config.truncate_spoken_text("The current result is unavailable.")
                return {
                    "status": "error",
                    "intent": intent.to_dict(),
                    "spoken_text": spoken_text,
                }

            source_trace = source_task.trace if isinstance(source_task.trace, dict) else {}
            if (
                source_task.provider != "ipfs_accelerate_mcp"
                or source_trace.get("mcp_capability") != "agentic_fetch"
            ):
                spoken_text = profile_config.truncate_spoken_text(
                    "The current result is not a rerunnable fetch."
                )
                return {
                    "status": "error",
                    "intent": intent.to_dict(),
                    "spoken_text": spoken_text,
                }

            new_seed_url = intent.entities.get("mcp_seed_url")
            if not isinstance(new_seed_url, str) or not new_seed_url.strip():
                spoken_text = profile_config.truncate_spoken_text(
                    "A new fetch URL is required."
                )
                return {
                    "status": "error",
                    "intent": intent.to_dict(),
                    "spoken_text": spoken_text,
                }
            new_seed_url = new_seed_url.strip()

            mcp_input = source_trace.get("mcp_input")
            if not isinstance(mcp_input, str) or not mcp_input.strip():
                spoken_text = profile_config.truncate_spoken_text(
                    "The current fetch result does not include target terms."
                )
                return {
                    "status": "error",
                    "intent": intent.to_dict(),
                    "spoken_text": spoken_text,
                }

            rerun_trace = {
                "intent_name": intent.name,
                "provider_label": source_trace.get("provider_label", "IPFS Accelerate"),
                "mcp_capability": "agentic_fetch",
                "mcp_execution_mode": resolve_capability_execution_mode(
                    "ipfs_accelerate_mcp",
                    "agentic_fetch",
                    intent.entities.get("mcp_preferred_execution_mode"),
                ),
                "mcp_preferred_execution_mode": intent.entities.get("mcp_preferred_execution_mode"),
                "rerun_of_task_id": source_task.id,
                "source_task_id": source_task.id,
                "mcp_input": mcp_input,
                "mcp_seed_url": new_seed_url,
            }
            resolved_execution_mode = rerun_trace["mcp_execution_mode"]
            instruction = f"discover and fetch {mcp_input.strip()} from {new_seed_url}"
            result = self._agent_service.delegate(
                user_id=user_id,
                instruction=instruction,
                provider="ipfs_accelerate_mcp",
                target_type=source_task.target_type,
                target_ref=source_task.target_ref,
                trace=rerun_trace,
            )
            spoken_text = profile_config.truncate_spoken_text(
                result.get("spoken_text", f"Rerunning the current fetch with {new_seed_url}.")
            )
            return {
                "status": "ok",
                "intent": {
                    "name": intent.name,
                    "confidence": intent.confidence,
                    "entities": {
                        "source_task_id": source_task.id,
                        "task_id": result.get("task_id"),
                        "provider": result.get("provider"),
                        "mcp_seed_url": new_seed_url,
                        "mcp_execution_mode": resolved_execution_mode,
                    },
                },
                "spoken_text": spoken_text,
                "cards": [
                    {
                        "title": "Fetch rerun requested",
                        "subtitle": f"Task {str(result.get('task_id', ''))[:8]}",
                        "lines": [
                            f"From task: {source_task.id[:8]}",
                            f"Target terms: {mcp_input.strip()}",
                            f"Seed URL: {new_seed_url}",
                        ],
                    }
                ],
                "debug": {
                    "tool_calls": [
                        {
                            "task_id": result.get("task_id"),
                            "provider": result.get("provider"),
                            "state": result.get("state"),
                            "source_task_id": source_task.id,
                            "mcp_seed_url": new_seed_url,
                            "mcp_execution_mode": resolved_execution_mode,
                        }
                    ]
                },
            }

        elif intent.name == "agent.result_rerun_dataset":
            if not self._agent_service or not self.db_conn:
                spoken_text = profile_config.truncate_spoken_text("Agent service not available.")
                return {
                    "status": "error",
                    "intent": intent.to_dict(),
                    "spoken_text": spoken_text,
                }
            if not user_id:
                spoken_text = profile_config.truncate_spoken_text(
                    "User authentication required for agent delegation."
                )
                return {
                    "status": "error",
                    "intent": intent.to_dict(),
                    "spoken_text": spoken_text,
                }

            card = self._get_current_navigation_card(session_id)
            if not card:
                spoken_text = profile_config.truncate_spoken_text(
                    "No result selected. Ask for agent results first."
                )
                return {
                    "status": "ok",
                    "intent": intent.to_dict(),
                    "spoken_text": spoken_text,
                }

            from handsfree.db.agent_tasks import get_agent_task_by_id

            source_task_id = card.get("task_id")
            if not isinstance(source_task_id, str) or not source_task_id:
                spoken_text = profile_config.truncate_spoken_text(
                    "The current result cannot be rerun."
                )
                return {
                    "status": "error",
                    "intent": intent.to_dict(),
                    "spoken_text": spoken_text,
                }

            source_task = get_agent_task_by_id(self.db_conn, source_task_id)
            if not source_task or source_task.user_id != user_id:
                spoken_text = profile_config.truncate_spoken_text("The current result is unavailable.")
                return {
                    "status": "error",
                    "intent": intent.to_dict(),
                    "spoken_text": spoken_text,
                }

            source_trace = source_task.trace if isinstance(source_task.trace, dict) else {}
            if (
                source_task.provider != "ipfs_datasets_mcp"
                or source_trace.get("mcp_capability") != "dataset_discovery"
            ):
                spoken_text = profile_config.truncate_spoken_text(
                    "The current result is not a rerunnable dataset search."
                )
                return {
                    "status": "error",
                    "intent": intent.to_dict(),
                    "spoken_text": spoken_text,
                }

            new_query = intent.entities.get("mcp_input")
            if not isinstance(new_query, str) or not new_query.strip():
                spoken_text = profile_config.truncate_spoken_text(
                    "A new dataset query is required."
                )
                return {
                    "status": "error",
                    "intent": intent.to_dict(),
                    "spoken_text": spoken_text,
                }
            new_query = new_query.strip()

            rerun_trace = {
                "intent_name": intent.name,
                "provider_label": source_trace.get("provider_label", "IPFS Datasets"),
                "mcp_capability": "dataset_discovery",
                "mcp_execution_mode": resolve_capability_execution_mode(
                    "ipfs_datasets_mcp",
                    "dataset_discovery",
                    intent.entities.get("mcp_preferred_execution_mode"),
                ),
                "mcp_preferred_execution_mode": intent.entities.get("mcp_preferred_execution_mode"),
                "rerun_of_task_id": source_task.id,
                "source_task_id": source_task.id,
                "mcp_input": new_query,
            }
            resolved_execution_mode = rerun_trace["mcp_execution_mode"]
            instruction = f"find {new_query}"
            result = self._agent_service.delegate(
                user_id=user_id,
                instruction=instruction,
                provider="ipfs_datasets_mcp",
                target_type=source_task.target_type,
                target_ref=source_task.target_ref,
                trace=rerun_trace,
            )
            spoken_text = profile_config.truncate_spoken_text(
                result.get("spoken_text", f"Rerunning the current dataset search with {new_query}.")
            )
            return {
                "status": "ok",
                "intent": {
                    "name": intent.name,
                    "confidence": intent.confidence,
                    "entities": {
                        "source_task_id": source_task.id,
                        "task_id": result.get("task_id"),
                        "provider": result.get("provider"),
                        "mcp_input": new_query,
                        "mcp_execution_mode": resolved_execution_mode,
                    },
                },
                "spoken_text": spoken_text,
                "cards": [
                    {
                        "title": "Dataset rerun requested",
                        "subtitle": f"Task {str(result.get('task_id', ''))[:8]}",
                        "lines": [
                            f"From task: {source_task.id[:8]}",
                            f"Query: {new_query}",
                            f"State: {result.get('state')}",
                        ],
                    }
                ],
                "debug": {
                    "tool_calls": [
                        {
                            "task_id": result.get("task_id"),
                            "provider": result.get("provider"),
                            "state": result.get("state"),
                            "source_task_id": source_task.id,
                            "mcp_input": new_query,
                            "mcp_execution_mode": resolved_execution_mode,
                        }
                    ]
                },
            }

        elif intent.name == "agent.pause":
            if not self._agent_service:
                spoken_text = profile_config.truncate_spoken_text("Agent service not available.")
                return {
                    "status": "error",
                    "intent": intent.to_dict(),
                    "spoken_text": spoken_text,
                }

            if not user_id:
                spoken_text = profile_config.truncate_spoken_text("User authentication required.")
                return {
                    "status": "error",
                    "intent": intent.to_dict(),
                    "spoken_text": spoken_text,
                }

            task_id = intent.entities.get("task_id")
            try:
                result = self._agent_service.pause_task(user_id=user_id, task_id=task_id)
                spoken_text = result.get("spoken_text", "Task paused.")
                spoken_text = profile_config.truncate_spoken_text(spoken_text)

                return {
                    "status": "ok",
                    "intent": intent.to_dict(),
                    "spoken_text": spoken_text,
                }
            except ValueError as e:
                spoken_text = profile_config.truncate_spoken_text(str(e))
                return {
                    "status": "error",
                    "intent": intent.to_dict(),
                    "spoken_text": spoken_text,
                }

        elif intent.name == "agent.resume":
            if not self._agent_service:
                spoken_text = profile_config.truncate_spoken_text("Agent service not available.")
                return {
                    "status": "error",
                    "intent": intent.to_dict(),
                    "spoken_text": spoken_text,
                }

            if not user_id:
                spoken_text = profile_config.truncate_spoken_text("User authentication required.")
                return {
                    "status": "error",
                    "intent": intent.to_dict(),
                    "spoken_text": spoken_text,
                }

            task_id = intent.entities.get("task_id")
            try:
                result = self._agent_service.resume_task(user_id=user_id, task_id=task_id)
                spoken_text = result.get("spoken_text", "Task resumed.")
                spoken_text = profile_config.truncate_spoken_text(spoken_text)

                return {
                    "status": "ok",
                    "intent": intent.to_dict(),
                    "spoken_text": spoken_text,
                }
            except ValueError as e:
                spoken_text = profile_config.truncate_spoken_text(str(e))
                return {
                    "status": "error",
                    "intent": intent.to_dict(),
                    "spoken_text": spoken_text,
                }

        else:
            spoken_text = profile_config.truncate_spoken_text(
                "Agent intent recognized but not implemented."
            )

        return {
            "status": "ok",
            "intent": intent.to_dict(),
            "spoken_text": spoken_text,
        }

    def _handle_unknown(
        self, intent: ParsedIntent, profile_config: ProfileConfig
    ) -> dict[str, Any]:
        """Handle unknown intents."""
        spoken_text = profile_config.truncate_spoken_text("I didn't catch that. Can you try again?")
        return {
            "status": "error",
            "intent": intent.to_dict(),
            "spoken_text": spoken_text,
        }

    def _handle_request_review_with_policy(
        self,
        intent: ParsedIntent,
        user_id: str,
        session_id: str | None,
        idempotency_key: str | None,
    ) -> dict[str, Any]:
        """Handle pr.request_review with full policy evaluation, rate limiting, and audit logging.

        Args:
            intent: The parsed pr.request_review intent
            user_id: User identifier for policy evaluation
            session_id: Session identifier for context resolution
            idempotency_key: Optional idempotency key

        Returns:
            Response dict with status, spoken_text, and optional pending_action
        """
        from fastapi import HTTPException

        from handsfree.actions import DirectActionRequest, process_direct_action_request_detailed

        # Extract entities
        reviewers = intent.entities.get("reviewers", [])
        pr_number = intent.entities.get("pr_number")
        repo = intent.entities.get("repo")

        # Resolve missing repo/pr_number from session context
        if not pr_number or not repo:
            context = self._session_context.get_repo_pr(session_id, fallback_repo="default/repo")
            if not pr_number and "pr_number" in context:
                pr_number = context["pr_number"]
            if not repo and "repo" in context:
                repo = context["repo"]

        # Validate required fields
        if not pr_number:
            return {
                "status": "error",
                "intent": intent.to_dict(),
                "spoken_text": (
                    "Please specify a PR number, for example: "
                    "'request review from alice on PR 123'. "
                    "Or first check a PR summary to set context."
                ),
            }

        if not reviewers:
            return {
                "status": "error",
                "intent": intent.to_dict(),
                "spoken_text": "Please specify at least one reviewer.",
            }

        reviewers_str = ", ".join(reviewers)
        try:
            detailed = process_direct_action_request_detailed(
                conn=self.db_conn,
                user_id=user_id,
                request=DirectActionRequest(
                    endpoint="/v1/command",
                    action_type="request_review",
                    execution_action_type="request_review",
                    pending_action_type="request_review",
                    repo=repo,
                    pr_number=pr_number,
                    action_payload={
                        "repo": repo,
                        "pr_number": pr_number,
                        "reviewers": reviewers,
                    },
                    log_request={"reviewers": reviewers},
                    pending_summary=f"Request review from {reviewers_str} on {repo}#{pr_number}",
                    idempotency_key=idempotency_key,
                    anomaly_request_data={"reviewers": reviewers},
                ),
                idempotency_store={},
            )
        except HTTPException as exc:
            if exc.status_code == 403 and isinstance(exc.detail, dict):
                return {
                    "status": "error",
                    "intent": intent.to_dict(),
                    "spoken_text": f"Action not allowed: {exc.detail.get('message', 'policy denied')}",
                }
            raise

        if detailed.http_response is not None:
            retry_after = detailed.http_response.headers.get("Retry-After")
            retry_msg = f" Please try again in {retry_after} seconds." if retry_after else ""
            return {
                "status": "error",
                "intent": intent.to_dict(),
                "spoken_text": f"Rate limit exceeded.{retry_msg}",
            }

        if detailed.pending_token:
            return {
                "status": "needs_confirmation",
                "intent": intent.to_dict(),
                "spoken_text": f"{detailed.pending_summary}. Say 'confirm' to proceed.",
                "pending_action": {
                    "token": detailed.pending_token,
                    "expires_at": detailed.pending_expires_at.isoformat(),
                    "summary": detailed.pending_summary,
                },
            }

        result = detailed.action_result
        if result and result.ok:
            return {
                "status": "ok",
                "intent": intent.to_dict(),
                "spoken_text": f"Review requested from {reviewers_str} on {repo}#{pr_number}.",
            }

        return {
            "status": "error",
            "intent": intent.to_dict(),
            "spoken_text": result.message if result else "Failed to request reviewers.",
        }

    def _handle_rerun_checks_with_policy(
        self,
        intent: ParsedIntent,
        user_id: str,
        session_id: str | None,
        idempotency_key: str | None,
    ) -> dict[str, Any]:
        """Handle checks.rerun with full policy evaluation, rate limiting, and audit logging.

        Args:
            intent: The parsed checks.rerun intent
            user_id: User identifier for policy evaluation
            session_id: Session identifier for context resolution
            idempotency_key: Optional idempotency key

        Returns:
            Response dict with status, spoken_text, and optional pending_action
        """
        from fastapi import HTTPException

        from handsfree.actions import DirectActionRequest, process_direct_action_request_detailed

        # Extract entities
        pr_number = intent.entities.get("pr_number")
        repo = intent.entities.get("repo")

        # Resolve missing repo/pr_number from session context
        if not pr_number or not repo:
            context = self._session_context.get_repo_pr(session_id, fallback_repo="default/repo")
            if not pr_number and "pr_number" in context:
                pr_number = context["pr_number"]
            if not repo and "repo" in context:
                repo = context["repo"]

        # Validate required fields
        if not pr_number:
            return {
                "status": "error",
                "intent": intent.to_dict(),
                "spoken_text": (
                    "Please specify a PR number, for example: 'rerun checks for PR 123'. "
                    "Or first check a PR summary to set context."
                ),
            }

        try:
            detailed = process_direct_action_request_detailed(
                conn=self.db_conn,
                user_id=user_id,
                request=DirectActionRequest(
                    endpoint="/v1/command",
                    action_type="rerun",
                    execution_action_type="rerun",
                    pending_action_type="rerun_checks",
                    repo=repo,
                    pr_number=pr_number,
                    action_payload={"repo": repo, "pr_number": pr_number},
                    log_request={},
                    pending_summary=f"Re-run checks on {repo}#{pr_number}",
                    idempotency_key=idempotency_key,
                ),
                idempotency_store={},
            )
        except HTTPException as exc:
            if exc.status_code == 403 and isinstance(exc.detail, dict):
                return {
                    "status": "error",
                    "intent": intent.to_dict(),
                    "spoken_text": f"Action not allowed: {exc.detail.get('message', 'policy denied')}",
                }
            raise

        if detailed.http_response is not None:
            retry_after = detailed.http_response.headers.get("Retry-After")
            retry_msg = f" Please try again in {retry_after} seconds." if retry_after else ""
            return {
                "status": "error",
                "intent": intent.to_dict(),
                "spoken_text": f"Rate limit exceeded.{retry_msg}",
            }

        if detailed.pending_token:
            return {
                "status": "needs_confirmation",
                "intent": intent.to_dict(),
                "spoken_text": f"{detailed.pending_summary}. Say 'confirm' to proceed.",
                "pending_action": {
                    "token": detailed.pending_token,
                    "expires_at": detailed.pending_expires_at.isoformat(),
                    "summary": detailed.pending_summary,
                },
            }

        result = detailed.action_result
        if result and result.ok:
            return {
                "status": "ok",
                "intent": intent.to_dict(),
                "spoken_text": f"Checks re-run on {repo}#{pr_number}.",
            }

        return {
            "status": "error",
            "intent": intent.to_dict(),
            "spoken_text": result.message if result else "Failed to rerun checks.",
        }

    def _handle_comment_with_policy(
        self,
        intent: ParsedIntent,
        user_id: str,
        session_id: str | None,
        idempotency_key: str | None,
    ) -> dict[str, Any]:
        """Handle pr.comment with full policy evaluation, rate limiting, and audit logging.

        Args:
            intent: The parsed pr.comment intent
            user_id: User identifier for policy evaluation
            session_id: Session identifier for context resolution
            idempotency_key: Optional idempotency key

        Returns:
            Response dict with status, spoken_text, and optional pending_action
        """
        from fastapi import HTTPException

        from handsfree.actions import DirectActionRequest, process_direct_action_request_detailed

        # Extract entities
        pr_number = intent.entities.get("pr_number")
        comment_body = intent.entities.get("comment_body", "")
        repo = intent.entities.get("repo")

        # Resolve missing repo/pr_number from session context
        if not pr_number or not repo:
            context = self._session_context.get_repo_pr(session_id, fallback_repo="default/repo")
            if not pr_number and "pr_number" in context:
                pr_number = context["pr_number"]
            if not repo and "repo" in context:
                repo = context["repo"]

        # Validate required fields
        if not pr_number:
            return {
                "status": "error",
                "intent": intent.to_dict(),
                "spoken_text": (
                    "Please specify a PR number, for example: 'comment on PR 123: looks good'. "
                    "Or first check a PR summary to set context."
                ),
            }

        if not comment_body:
            return {
                "status": "error",
                "intent": intent.to_dict(),
                "spoken_text": "Please specify the comment text.",
            }

        comment_preview = comment_body[:50] + "..." if len(comment_body) > 50 else comment_body
        try:
            detailed = process_direct_action_request_detailed(
                conn=self.db_conn,
                user_id=user_id,
                request=DirectActionRequest(
                    endpoint="/v1/command",
                    action_type="comment",
                    execution_action_type="comment",
                    pending_action_type="comment",
                    repo=repo,
                    pr_number=pr_number,
                    action_payload={
                        "repo": repo,
                        "pr_number": pr_number,
                        "comment_body": comment_body,
                    },
                    log_request={"comment_body": comment_body},
                    pending_summary=f"Post comment on {repo}#{pr_number}: {comment_preview}",
                    idempotency_key=idempotency_key,
                    anomaly_request_data={"comment_body": comment_body},
                ),
                idempotency_store={},
            )
        except HTTPException as exc:
            if exc.status_code == 403 and isinstance(exc.detail, dict):
                return {
                    "status": "error",
                    "intent": intent.to_dict(),
                    "spoken_text": f"Action not allowed: {exc.detail.get('message', 'policy denied')}",
                }
            raise

        if detailed.http_response is not None:
            retry_after = detailed.http_response.headers.get("Retry-After")
            retry_msg = f" Please try again in {retry_after} seconds." if retry_after else ""
            return {
                "status": "error",
                "intent": intent.to_dict(),
                "spoken_text": f"Rate limit exceeded.{retry_msg}",
            }

        if detailed.pending_token:
            return {
                "status": "needs_confirmation",
                "intent": intent.to_dict(),
                "spoken_text": f"{detailed.pending_summary}. Say 'confirm' to proceed.",
                "pending_action": {
                    "token": detailed.pending_token,
                    "expires_at": detailed.pending_expires_at.isoformat(),
                    "summary": detailed.pending_summary,
                },
            }

        result = detailed.action_result
        if result and result.ok:
            return {
                "status": "ok",
                "intent": intent.to_dict(),
                "spoken_text": f"Comment posted on {repo}#{pr_number}: {comment_preview}",
            }

        return {
            "status": "error",
            "intent": intent.to_dict(),
            "spoken_text": result.message if result else "Failed to post comment.",
        }
