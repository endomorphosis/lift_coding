"""Runtime transport helpers for Meta glasses mobile ORB bindings."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from handsfree.mcp.client import MCPClient, MCPClientError
from handsfree.mcp.config import get_mcp_server_config
from handsfree.models import MetaGlassesMobileOrbInvokeServiceRequest


def _first_nonempty_string(*values: Any) -> str | None:
    for value in values:
        if isinstance(value, str) and value.strip():
            return value.strip()
    return None


def _get_nested_mapping(value: Any, *keys: str) -> Mapping[str, Any] | None:
    current = value
    for key in keys:
        if not isinstance(current, Mapping):
            return None
        current = current.get(key)
    return current if isinstance(current, Mapping) else None


def _get_mapping(value: Mapping[str, Any], key: str) -> Mapping[str, Any]:
    child = value.get(key)
    return child if isinstance(child, Mapping) else {}


def _infer_server_family(namespace: str | None) -> str | None:
    normalized = (namespace or "").strip().lower().replace("-", "_").replace(".", "_")
    if not normalized:
        return None
    if "ipfs_datasets" in normalized:
        return "ipfs_datasets"
    if "ipfs_kit" in normalized:
        return "ipfs_kit"
    if "ipfs_accelerate" in normalized:
        return "ipfs_accelerate"
    return None


def _resolve_mcp_server_family(binding_record: Mapping[str, Any]) -> tuple[str | None, str | None]:
    orb_binding = _get_mapping(binding_record, "orb_binding")
    transport_binding = _get_mapping(orb_binding, "transport_binding")
    metadata = _get_mapping(transport_binding, "metadata")
    descriptor = _get_mapping(binding_record, "service_descriptor")
    descriptor_metadata = _get_mapping(descriptor, "metadata")
    policy_context = _get_mapping(binding_record, "policy_context")

    server_family = _first_nonempty_string(
        metadata.get("server_family"),
        metadata.get("mcp_server_family"),
        descriptor.get("server_family"),
        descriptor_metadata.get("server_family"),
        policy_context.get("server_family"),
        policy_context.get("mcp_server_family"),
        _infer_server_family(
            _first_nonempty_string(
                descriptor.get("namespace"),
                metadata.get("namespace"),
            )
        ),
    )
    if server_family:
        return server_family, "descriptor"
    return None, None


def resolve_mobile_orb_runtime_binding(binding_record: Mapping[str, Any]) -> dict[str, Any] | None:
    """Resolve a stored mobile ORB binding into a concrete runtime transport reference."""
    orb_binding = binding_record.get("orb_binding")
    if not isinstance(orb_binding, Mapping):
        return None

    transport = _first_nonempty_string(
        orb_binding.get("transport"),
        binding_record.get("transport_preference"),
        binding_record.get("transport"),
    )
    if transport != "mcp-server":
        return None

    transport_metadata = _get_nested_mapping(
        orb_binding,
        "transport_binding",
        "metadata",
    ) or {}

    service_id = _first_nonempty_string(
        orb_binding.get("service_id"),
        binding_record.get("service_interface_cid"),
    )
    operation = _first_nonempty_string(
        orb_binding.get("operation"),
        binding_record.get("operation"),
        "invoke",
    )
    server_family, resolution_source = _resolve_mcp_server_family(binding_record)
    descriptor = _get_mapping(binding_record, "service_descriptor")
    descriptor_metadata = _get_mapping(descriptor, "metadata")
    tool_name = _first_nonempty_string(
        transport_metadata.get("tool_name") if isinstance(transport_metadata, Mapping) else None,
        descriptor_metadata.get("tool_name") if isinstance(descriptor_metadata, Mapping) else None,
        descriptor.get("tool_name") if isinstance(descriptor, Mapping) else None,
        operation,
    )

    runtime_binding = {
        "binding_type": "handsfree.mcp-server",
        "transport": "mcp-server",
        "interface_cid": orb_binding.get("interface_cid"),
        "service_id": service_id,
        "operation": operation,
        "tool_name": tool_name,
        "status": "unresolved",
        "resolution_source": resolution_source,
    }

    if not server_family:
        return {
            **runtime_binding,
            "reason": "missing_server_family",
        }

    runtime_binding["server_family"] = server_family
    try:
        config = get_mcp_server_config(server_family)
    except ValueError:
        return {
            **runtime_binding,
            "status": "invalid",
            "reason": "unknown_server_family",
        }

    runtime_binding.update(
        {
            "client_transport": config.transport,
            "rpc_path": config.rpc_path,
            "endpoint": config.endpoint or None,
            "command": config.command or None,
        }
    )
    if config.endpoint or config.command:
        runtime_binding["status"] = "ready"
    else:
        runtime_binding["reason"] = "missing_transport_configuration"
    return runtime_binding


def attach_mobile_orb_runtime_binding(binding_record: dict[str, Any]) -> dict[str, Any]:
    """Attach resolved runtime transport metadata to a stored binding record."""
    runtime_binding = resolve_mobile_orb_runtime_binding(binding_record)
    if runtime_binding is None:
        return binding_record

    binding_record["runtime_binding"] = runtime_binding
    orb_binding = binding_record.get("orb_binding")
    if isinstance(orb_binding, dict):
        transport_binding = orb_binding.get("transport_binding")
        if isinstance(transport_binding, dict):
            transport_binding["runtime"] = runtime_binding
    return binding_record


def invoke_mobile_orb_runtime_binding(
    *,
    binding: Mapping[str, Any],
    request: MetaGlassesMobileOrbInvokeServiceRequest,
) -> dict[str, Any] | None:
    """Invoke a concrete transport binding when one has been resolved."""
    runtime_binding = binding.get("runtime_binding")
    if not isinstance(runtime_binding, Mapping):
        return None
    if runtime_binding.get("binding_type") != "handsfree.mcp-server":
        return None
    if runtime_binding.get("status") != "ready":
        return dict(runtime_binding)

    server_family = _first_nonempty_string(runtime_binding.get("server_family"))
    tool_name = _first_nonempty_string(runtime_binding.get("tool_name"), request.operation)
    if server_family is None or tool_name is None:
        return {
            **dict(runtime_binding),
            "status": "error",
            "reason": "missing_runtime_target",
        }

    config = get_mcp_server_config(server_family)
    arguments = dict(request.arguments)
    arguments.setdefault("operation", request.operation)
    arguments.setdefault("service_id", runtime_binding.get("service_id"))
    arguments.setdefault("interface_cid", runtime_binding.get("interface_cid"))

    try:
        result = MCPClient(config).invoke_tool(
            tool_name=tool_name,
            arguments=arguments,
            correlation_id=request.correlation_id,
        )
    except MCPClientError as exc:
        return {
            **dict(runtime_binding),
            "status": "error",
            "error": str(exc),
        }

    return {
        **dict(runtime_binding),
        "status": result.status,
        "request_id": result.request_id,
        "run_id": result.run_id,
        "tool_name": result.tool_name,
        "output": result.output,
        "content": result.content,
    }
