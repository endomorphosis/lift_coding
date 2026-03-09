"""MCP tool bindings for HandsFree task delegation."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from .client import MCPConfigurationError
from .catalog import (
    resolve_capability_execution_mode,
    resolve_provider_capability,
    resolve_provider_name_for_server_family,
)
from .models import (
    MCPArtifactRefs,
    MCPExecutionResultEnvelope,
    MCPExecutionTrace,
    MCPServerConfig,
    MCPToolInvocationResult,
)


@dataclass(frozen=True)
class MCPToolCall:
    """Concrete MCP tool invocation."""

    tool_name: str
    arguments: dict[str, Any]


@dataclass(frozen=True)
class MCPTaskBinding:
    """Resolved task binding for an MCP-backed provider."""

    start_call: MCPToolCall
    status_call: MCPToolCall | None = None
    cancel_call: MCPToolCall | None = None
    remote_id_field: str | None = None
    supports_remote_status: bool = False
    capability_id: str | None = None
    execution_mode: str | None = None


def build_result_envelope(
    *,
    provider_name: str,
    server_family: str,
    capability_id: str | None,
    execution_mode: str,
    status: str,
    tool_name: str | None,
    spoken_text: str | None = None,
    summary: str | None = None,
    structured_output: Any = None,
    request_id: str | None = None,
    run_id: str | None = None,
    remote_task_id: str | None = None,
    last_protocol_state: str | None = None,
    artifact_refs: MCPArtifactRefs | None = None,
    provider_profiles: tuple[str, ...] = (),
    follow_up_actions: list[dict[str, Any]] | None = None,
    needs_input_schema: dict[str, Any] | None = None,
) -> MCPExecutionResultEnvelope:
    """Build a canonical HandsFree result envelope."""
    normalized_status = _normalize_envelope_status(status)
    resolved_summary = (summary or spoken_text or _infer_summary(structured_output) or "").strip()
    resolved_spoken_text = (spoken_text or resolved_summary or _default_spoken_text(normalized_status)).strip()
    return MCPExecutionResultEnvelope(
        capability_id=capability_id,
        provider=provider_name,
        server_family=server_family,
        execution_mode=execution_mode,
        status=normalized_status,
        spoken_text=resolved_spoken_text,
        summary=resolved_summary or resolved_spoken_text,
        structured_output=structured_output,
        follow_up_actions=list(follow_up_actions or ()),
        artifact_refs=artifact_refs or _artifact_refs_from_output(structured_output),
        trace=MCPExecutionTrace(
            request_id=request_id,
            run_id=run_id,
            remote_task_id=remote_task_id,
            tool_name=tool_name,
            last_protocol_state=last_protocol_state or normalized_status,
            provider_profiles=provider_profiles,
        ),
        needs_input_schema=needs_input_schema,
    )


def build_result_envelope_from_invocation(
    *,
    provider_name: str,
    server_family: str,
    capability_id: str | None,
    execution_mode: str,
    invocation: MCPToolInvocationResult,
    remote_task_id: str | None = None,
    status: str | None = None,
) -> MCPExecutionResultEnvelope:
    """Build an execution envelope from an MCP invocation result."""
    resolved_status = status or invocation.output.get("status") or invocation.status
    return build_result_envelope(
        provider_name=provider_name,
        server_family=server_family,
        capability_id=capability_id,
        execution_mode=execution_mode,
        status=str(resolved_status),
        tool_name=invocation.tool_name,
        spoken_text=_extract_message(invocation.output, invocation.content),
        structured_output=invocation.output,
        request_id=invocation.request_id,
        run_id=invocation.run_id,
        remote_task_id=remote_task_id,
        last_protocol_state=str(invocation.output.get("status") or invocation.status),
    )


def envelope_to_trace(envelope: MCPExecutionResultEnvelope) -> dict[str, Any]:
    """Project a canonical envelope into the task-trace representation."""
    return {
        "mcp_result_envelope": {
            "capability_id": envelope.capability_id,
            "provider": envelope.provider,
            "server_family": envelope.server_family,
            "execution_mode": envelope.execution_mode,
            "status": envelope.status,
            "spoken_text": envelope.spoken_text,
            "summary": envelope.summary,
            "structured_output": envelope.structured_output,
            "follow_up_actions": envelope.follow_up_actions,
            "artifact_refs": {
                "result_cid": envelope.artifact_refs.result_cid,
                "receipt_ref": envelope.artifact_refs.receipt_ref,
                "event_dag_ref": envelope.artifact_refs.event_dag_ref,
                "delegation_ref": envelope.artifact_refs.delegation_ref,
            },
            "trace": {
                "request_id": envelope.trace.request_id,
                "run_id": envelope.trace.run_id,
                "remote_task_id": envelope.trace.remote_task_id,
                "tool_name": envelope.trace.tool_name,
                "last_protocol_state": envelope.trace.last_protocol_state,
                "provider_profiles": list(envelope.trace.provider_profiles),
            },
            "needs_input_schema": envelope.needs_input_schema,
        },
        "mcp_result_preview": envelope.summary,
        "mcp_result_output": envelope.structured_output,
        "mcp_request_id": envelope.trace.request_id,
        "mcp_run_id": envelope.trace.run_id,
        "mcp_remote_task_id": envelope.trace.remote_task_id,
        "tool_name": envelope.trace.tool_name,
        "last_protocol_state": envelope.trace.last_protocol_state,
        "mcp_result_cid": envelope.artifact_refs.result_cid,
        "mcp_receipt_ref": envelope.artifact_refs.receipt_ref,
        "mcp_event_dag_ref": envelope.artifact_refs.event_dag_ref,
        "mcp_delegation_ref": envelope.artifact_refs.delegation_ref,
        "mcp_follow_up_actions": envelope.follow_up_actions,
        "mcp_needs_input_schema": envelope.needs_input_schema,
    }


def _normalize_envelope_status(status: str | None) -> str:
    normalized = (status or "").strip().lower()
    if normalized in {"completed", "success", "succeeded"}:
        return "completed"
    if normalized in {"needs_input", "requires_input", "awaiting_input"}:
        return "needs_input"
    if normalized in {"failed", "error", "cancelled", "canceled"}:
        return "failed"
    if normalized:
        return "running"
    return "running"


def _default_spoken_text(status: str) -> str:
    if status == "completed":
        return "Task completed."
    if status == "needs_input":
        return "I need more information."
    if status == "failed":
        return "Task failed."
    return "Task started."


def _extract_message(output: Any, content: list[dict[str, Any]]) -> str | None:
    if isinstance(output, dict):
        for key in ("message", "detail", "summary"):
            value = output.get(key)
            if isinstance(value, str) and value.strip():
                return value
    for item in content:
        if not isinstance(item, dict):
            continue
        text = item.get("text")
        if isinstance(text, str) and text.strip():
            return text.strip()
    return None


def _infer_summary(structured_output: Any) -> str | None:
    if isinstance(structured_output, dict):
        for key in ("message", "summary", "detail"):
            value = structured_output.get(key)
            if isinstance(value, str) and value.strip():
                return value.strip()
        cid = structured_output.get("cid")
        if isinstance(cid, str) and cid.strip():
            return f"Result CID {cid.strip()}"
    return None


def _artifact_refs_from_output(structured_output: Any) -> MCPArtifactRefs:
    if not isinstance(structured_output, dict):
        return MCPArtifactRefs()
    return MCPArtifactRefs(
        result_cid=_first_str(structured_output, "cid", "ipfs_cid", "result_cid"),
        receipt_ref=_first_str(structured_output, "receipt_cid", "receipt_ref"),
        event_dag_ref=_first_str(structured_output, "event_dag_cid", "event_dag_ref"),
        delegation_ref=_first_str(structured_output, "delegation_cid", "delegation_ref"),
    )


def _first_str(data: dict[str, Any], *keys: str) -> str | None:
    for key in keys:
        value = data.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()
    return None


def resolve_task_binding(
    *,
    server_family: str,
    config: MCPServerConfig,
    base_arguments: dict[str, Any],
    remote_task_id: str | None = None,
) -> MCPTaskBinding:
    """Resolve the start/status/cancel tools for a provider family."""
    provider_name = _resolve_provider_name(server_family, base_arguments)
    requested_capability = str(base_arguments.get("mcp_capability") or "").strip().lower() or None
    resolved_capability = _resolve_capability(
        provider_name=provider_name,
        requested_capability=requested_capability,
        instruction=str(base_arguments.get("instruction") or ""),
    )
    resolved_execution_mode = (
        resolve_capability_execution_mode(
            provider_name,
            resolved_capability,
            preferred_mode=str(
                base_arguments.get("mcp_preferred_execution_mode")
                or base_arguments.get("mcp_execution_mode")
                or config.preferred_execution_mode
                or ""
            ),
        )
        if provider_name
        else None
    )
    normalized_arguments = dict(base_arguments)
    if resolved_capability:
        normalized_arguments["mcp_capability"] = resolved_capability

    if server_family == "ipfs_datasets":
        return _with_binding_metadata(
            _resolve_ipfs_datasets_binding(
            config=config,
            base_arguments=normalized_arguments,
            remote_task_id=remote_task_id,
            status_tool_default="get_task_status",
            ),
            capability_id=resolved_capability,
            execution_mode=resolved_execution_mode,
        )

    if server_family == "ipfs_accelerate":
        return _with_binding_metadata(
            _resolve_ipfs_accelerate_binding(
            config=config,
            base_arguments=normalized_arguments,
            remote_task_id=remote_task_id,
            status_tool_default="get_task_status",
            ),
            capability_id=resolved_capability,
            execution_mode=resolved_execution_mode,
        )

    if server_family == "ipfs_kit":
        return _with_binding_metadata(
            _resolve_ipfs_kit_binding(config=config, base_arguments=normalized_arguments),
            capability_id=resolved_capability,
            execution_mode=resolved_execution_mode,
        )

    raise MCPConfigurationError(f"Unsupported MCP server family: {server_family}")


def _resolve_provider_name(server_family: str, base_arguments: dict[str, Any]) -> str | None:
    provider_name = str(base_arguments.get("provider") or "").strip().lower()
    if provider_name:
        return provider_name
    return resolve_provider_name_for_server_family(server_family)


def _resolve_capability(
    *,
    provider_name: str | None,
    requested_capability: str | None,
    instruction: str,
) -> str | None:
    del instruction

    if not requested_capability:
        return None

    if not provider_name:
        return requested_capability

    resolved_capability = resolve_provider_capability(
        provider_name,
        requested_capability=requested_capability,
    )
    if requested_capability and resolved_capability is None:
        raise MCPConfigurationError(
            f"Capability '{requested_capability}' is not supported by provider '{provider_name}'"
        )
    return resolved_capability


def _with_binding_metadata(
    binding: MCPTaskBinding,
    *,
    capability_id: str | None,
    execution_mode: str | None,
) -> MCPTaskBinding:
    return MCPTaskBinding(
        start_call=binding.start_call,
        status_call=binding.status_call,
        cancel_call=binding.cancel_call,
        remote_id_field=binding.remote_id_field,
        supports_remote_status=binding.supports_remote_status,
        capability_id=capability_id,
        execution_mode=execution_mode,
    )


def _resolve_meta_dispatch_binding(
    *,
    config: MCPServerConfig,
    base_arguments: dict[str, Any],
    remote_task_id: str | None,
    status_tool_default: str,
) -> MCPTaskBinding:
    top_level_tool = config.tool_name or "tools_dispatch"
    if top_level_tool != "tools_dispatch":
        return MCPTaskBinding(
            start_call=MCPToolCall(tool_name=top_level_tool, arguments=base_arguments),
        )

    category = config.task_category or "background_task_tools"
    create_tool = config.task_create_tool or "manage_background_tasks"
    status_tool = config.task_status_tool or status_tool_default
    cancel_tool = config.task_cancel_tool or "manage_background_tasks"

    start_call = MCPToolCall(
        tool_name="tools_dispatch",
        arguments=_dispatch_args(
            config.server_family,
            category=category,
            tool_name=create_tool,
            parameters={
                "action": "create",
                "task_type": "handsfree_agent_request",
                "parameters": base_arguments,
                "priority": "normal",
                "task_config": {
                    "source": "handsfree",
                    "provider": base_arguments.get("provider"),
                    "target_type": base_arguments.get("target_type"),
                    "target_ref": base_arguments.get("target_ref"),
                },
            },
        ),
    )

    if not remote_task_id:
        return MCPTaskBinding(
            start_call=start_call,
            remote_id_field="task_id",
            supports_remote_status=True,
        )

    status_call = MCPToolCall(
        tool_name="tools_dispatch",
        arguments=_dispatch_args(
            config.server_family,
            category=category,
            tool_name=status_tool,
            parameters={"task_id": remote_task_id},
        ),
    )
    cancel_call = MCPToolCall(
        tool_name="tools_dispatch",
        arguments=_dispatch_args(
            config.server_family,
            category=category,
            tool_name=cancel_tool,
            parameters={
                "action": "cancel",
                "task_id": remote_task_id,
            },
        ),
    )
    return MCPTaskBinding(
        start_call=start_call,
        status_call=status_call,
        cancel_call=cancel_call,
        remote_id_field="task_id",
        supports_remote_status=True,
    )


def _resolve_ipfs_datasets_binding(
    *,
    config: MCPServerConfig,
    base_arguments: dict[str, Any],
    remote_task_id: str | None,
    status_tool_default: str,
) -> MCPTaskBinding:
    capability = str(base_arguments.get("mcp_capability") or "").strip().lower()
    if capability == "dataset_discovery":
        query = str(base_arguments.get("mcp_input") or base_arguments.get("instruction") or "").strip()
        if not query:
            raise MCPConfigurationError("dataset discovery requires a non-empty query")
        return MCPTaskBinding(
            start_call=MCPToolCall(
                tool_name="tools_dispatch",
                arguments=_dispatch_args(
                    config.server_family,
                    category="legal_dataset_tools",
                    tool_name="expand_legal_query",
                    parameters={"query": query},
                ),
            ),
        )
    return _resolve_meta_dispatch_binding(
        config=config,
        base_arguments=base_arguments,
        remote_task_id=remote_task_id,
        status_tool_default=status_tool_default,
    )


def _resolve_ipfs_accelerate_binding(
    *,
    config: MCPServerConfig,
    base_arguments: dict[str, Any],
    remote_task_id: str | None,
    status_tool_default: str,
) -> MCPTaskBinding:
    capability = str(base_arguments.get("mcp_capability") or "").strip().lower()
    if capability == "agentic_fetch":
        seed_url = str(base_arguments.get("mcp_seed_url") or "").strip()
        target_terms = str(base_arguments.get("mcp_input") or "").strip()
        if not seed_url or not target_terms:
            raise MCPConfigurationError("agentic fetch requires both a seed URL and target terms")
        return MCPTaskBinding(
            start_call=MCPToolCall(
                tool_name="tools_dispatch",
                arguments=_dispatch_args(
                    config.server_family,
                    category="web_archive_tools",
                    tool_name="unified_agentic_discover_and_fetch",
                    parameters={
                        "seed_urls": [seed_url],
                        "target_terms": [target_terms],
                    },
                ),
            ),
        )
    return _resolve_meta_dispatch_binding(
        config=config,
        base_arguments=base_arguments,
        remote_task_id=remote_task_id,
        status_tool_default=status_tool_default,
    )


def _resolve_ipfs_kit_binding(
    *,
    config: MCPServerConfig,
    base_arguments: dict[str, Any],
) -> MCPTaskBinding:
    capability = str(base_arguments.get("mcp_capability") or "").strip().lower()
    instruction = str(base_arguments.get("instruction") or "").strip()
    explicit_tool_name = config.tool_name

    if explicit_tool_name:
        return MCPTaskBinding(
            start_call=MCPToolCall(tool_name=explicit_tool_name, arguments=base_arguments),
        )

    if capability == "ipfs_add":
        content = str(base_arguments.get("mcp_input") or instruction).strip()
        if not content:
            raise MCPConfigurationError("ipfs_add requires content to add to IPFS")
        return MCPTaskBinding(
            start_call=MCPToolCall(
                tool_name="ipfs_add",
                arguments={"content": content},
            ),
        )

    if capability == "ipfs_cat":
        cid = str(base_arguments.get("mcp_cid") or base_arguments.get("mcp_input") or "").strip()
        if not cid:
            raise MCPConfigurationError("ipfs_cat requires a CID or IPFS path")
        return MCPTaskBinding(
            start_call=MCPToolCall(
                tool_name="ipfs_cat",
                arguments={"cid": cid},
            ),
        )

    if capability == "ipfs_pin":
        cid = str(base_arguments.get("mcp_cid") or base_arguments.get("mcp_input") or "").strip()
        if not cid:
            raise MCPConfigurationError("ipfs_pin requires a CID")
        pin_action = str(base_arguments.get("mcp_pin_action") or "").strip().lower()
        tool_name = "ipfs_pin_rm" if pin_action == "unpin" else "ipfs_pin_add"
        return MCPTaskBinding(
            start_call=MCPToolCall(
                tool_name=tool_name,
                arguments={"cid": cid},
            ),
        )

    raise MCPConfigurationError(
        "ipfs_kit MCP delegation needs either a concrete HANDSFREE_MCP_IPFS_KIT_TOOL_NAME "
        "or a direct supported capability such as add/cat/pin"
    )


def _dispatch_args(
    server_family: str,
    *,
    category: str,
    tool_name: str,
    parameters: dict[str, Any],
) -> dict[str, Any]:
    if server_family == "ipfs_datasets":
        return {
            "category": category,
            "tool": tool_name,
            "params": parameters,
        }
    return {
        "category": category,
        "tool_name": tool_name,
        "parameters": parameters,
    }
