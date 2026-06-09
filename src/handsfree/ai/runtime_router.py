"""Deterministic route planning for cross-repo virtual AI OS capabilities."""

from __future__ import annotations

from handsfree.ipfs_accelerate_adapters import get_ipfs_accelerate_cli_command
from handsfree.ipfs_kit_adapters import get_ipfs_kit_cli_command

from .capability_registry import (
    get_virtual_ai_os_capability,
    resolve_virtual_ai_os_execution_mode,
)
from .models import (
    AICapabilityRoute,
    CapabilityExecutionMode,
    CapabilityRuntimeSurface,
)

_DATASETS_CLI_COMMAND = "python external/ipfs_datasets/ipfs_datasets_cli.py"


def resolve_virtual_ai_os_runtime_route(
    capability_id: str,
    *,
    requested_mode: str | CapabilityExecutionMode | None = None,
    provider_preferred_modes: tuple[str | CapabilityExecutionMode, ...] = (),
    policy_preferred_modes: tuple[str | CapabilityExecutionMode, ...] = (),
    preferred_surface: str | CapabilityRuntimeSurface | None = None,
) -> AICapabilityRoute:
    """Resolve one cross-repo capability into a concrete runtime surface."""
    entry = get_virtual_ai_os_capability(capability_id)
    execution_mode = resolve_virtual_ai_os_execution_mode(
        capability_id,
        requested_mode=requested_mode,
        provider_preferred_modes=provider_preferred_modes,
        policy_preferred_modes=policy_preferred_modes,
    )
    runtime_surface = _resolve_runtime_surface(
        entry.capability_id, execution_mode, preferred_surface
    )
    handler_ref, cli_command = _resolve_handler(
        entry.capability_id, execution_mode, runtime_surface
    )
    return AICapabilityRoute(
        capability_id=entry.capability_id,
        owner_repo=entry.owner_repo,
        provider_name=entry.provider_name,
        server_family=entry.server_family,
        execution_mode=execution_mode,
        runtime_surface=runtime_surface,
        confirmation_policy=entry.confirmation_policy,
        handler_ref=handler_ref,
        cli_command=cli_command,
        fallback_execution_mode=entry.fallback_execution_mode,
    )


def _resolve_runtime_surface(
    capability_id: str,
    execution_mode: CapabilityExecutionMode,
    preferred_surface: str | CapabilityRuntimeSurface | None,
) -> CapabilityRuntimeSurface:
    normalized_surface = _normalize_surface(preferred_surface)
    default_surface = _default_runtime_surface(capability_id, execution_mode)
    if normalized_surface is None:
        return default_surface
    if normalized_surface not in _supported_surfaces_for_mode(capability_id, execution_mode):
        raise ValueError(
            f"Capability '{capability_id}' does not support runtime surface '{normalized_surface.value}' "
            f"for execution mode '{execution_mode.value}'"
        )
    return normalized_surface


def _default_runtime_surface(
    capability_id: str,
    execution_mode: CapabilityExecutionMode,
) -> CapabilityRuntimeSurface:
    if execution_mode == CapabilityExecutionMode.DIRECT_IMPORT:
        return CapabilityRuntimeSurface.DIRECT_ADAPTER
    if execution_mode == CapabilityExecutionMode.DIRECT_CLI:
        return CapabilityRuntimeSurface.LOCAL_CLI
    if execution_mode == CapabilityExecutionMode.ORCHESTRATED:
        return CapabilityRuntimeSurface.DAEMON_MEDIATED
    if capability_id in {"workflow", "agentic_fetch"}:
        return CapabilityRuntimeSurface.DAEMON_MEDIATED
    return CapabilityRuntimeSurface.MCP_PROVIDER


def _supported_surfaces_for_mode(
    capability_id: str,
    execution_mode: CapabilityExecutionMode,
) -> tuple[CapabilityRuntimeSurface, ...]:
    if execution_mode == CapabilityExecutionMode.DIRECT_IMPORT:
        return (CapabilityRuntimeSurface.DIRECT_ADAPTER,)
    if execution_mode == CapabilityExecutionMode.DIRECT_CLI:
        return (CapabilityRuntimeSurface.LOCAL_CLI,)
    if execution_mode == CapabilityExecutionMode.ORCHESTRATED:
        return (CapabilityRuntimeSurface.DAEMON_MEDIATED,)
    if capability_id in {"embedding", "dataset_discovery", "storage", "ipfs_pin"}:
        return (CapabilityRuntimeSurface.MCP_PROVIDER, CapabilityRuntimeSurface.SWISSKNIFE_ORB)
    return (
        CapabilityRuntimeSurface.MCP_PROVIDER,
        CapabilityRuntimeSurface.DAEMON_MEDIATED,
        CapabilityRuntimeSurface.SWISSKNIFE_ORB,
    )


def _resolve_handler(
    capability_id: str,
    execution_mode: CapabilityExecutionMode,
    runtime_surface: CapabilityRuntimeSurface,
) -> tuple[str, str | None]:
    if runtime_surface == CapabilityRuntimeSurface.DIRECT_ADAPTER:
        return _resolve_direct_adapter_handler(capability_id), None
    if runtime_surface == CapabilityRuntimeSurface.LOCAL_CLI:
        return "handsfree.ai.runtime_router:run_local_cli", _resolve_cli_command(capability_id)
    if runtime_surface == CapabilityRuntimeSurface.DAEMON_MEDIATED:
        return "handsfree.ai.runtime_router:run_daemon_workflow", None
    if runtime_surface == CapabilityRuntimeSurface.SWISSKNIFE_ORB:
        return f"swissknife.orb::{capability_id}", None
    if runtime_surface == CapabilityRuntimeSurface.MCP_PROVIDER:
        return f"handsfree.mcp::{capability_id}", None
    raise ValueError(
        f"Unsupported runtime surface '{runtime_surface.value}' for '{capability_id}'/{execution_mode.value}"
    )


def _resolve_direct_adapter_handler(capability_id: str) -> str:
    mapping = {
        "embedding": "handsfree.ipfs_datasets_routers:get_embeddings_router",
        "ipfs_pin": "handsfree.ipfs_kit_adapters:get_ipfs_kit_adapter",
    }
    try:
        return mapping[capability_id]
    except KeyError as exc:
        raise ValueError(f"Capability '{capability_id}' has no direct-adapter route") from exc


def _resolve_cli_command(capability_id: str) -> str:
    mapping = {
        "dataset_discovery": _DATASETS_CLI_COMMAND,
        "storage": get_ipfs_kit_cli_command(),
        "ipfs_pin": get_ipfs_kit_cli_command(),
        "agentic_fetch": get_ipfs_accelerate_cli_command(),
    }
    try:
        return mapping[capability_id]
    except KeyError as exc:
        raise ValueError(f"Capability '{capability_id}' has no CLI route") from exc


def _normalize_surface(
    value: str | CapabilityRuntimeSurface | None,
) -> CapabilityRuntimeSurface | None:
    if value is None:
        return None
    if isinstance(value, CapabilityRuntimeSurface):
        return value
    normalized = value.strip().lower()
    if not normalized:
        return None
    return CapabilityRuntimeSurface(normalized)
