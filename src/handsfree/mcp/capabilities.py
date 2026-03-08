"""MCP tool bindings for HandsFree task delegation."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from .client import MCPConfigurationError
from .models import MCPServerConfig


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


def resolve_task_binding(
    *,
    server_family: str,
    config: MCPServerConfig,
    base_arguments: dict[str, Any],
    remote_task_id: str | None = None,
) -> MCPTaskBinding:
    """Resolve the start/status/cancel tools for a provider family."""
    if server_family == "ipfs_datasets":
        return _resolve_ipfs_datasets_binding(
            config=config,
            base_arguments=base_arguments,
            remote_task_id=remote_task_id,
            status_tool_default="get_task_status",
        )

    if server_family == "ipfs_accelerate":
        return _resolve_ipfs_accelerate_binding(
            config=config,
            base_arguments=base_arguments,
            remote_task_id=remote_task_id,
            status_tool_default="get_task_status",
        )

    if server_family == "ipfs_kit":
        return _resolve_ipfs_kit_binding(config=config, base_arguments=base_arguments)

    raise MCPConfigurationError(f"Unsupported MCP server family: {server_family}")


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
