"""Runtime placement policy for virtual AI OS capability routes."""

from __future__ import annotations

from .models import (
    AICapabilityRuntimePlacement,
    CapabilityExecutionMode,
    CapabilityRuntimeSurface,
)


_MCP_REMOTE_DATA_SURFACES = {
    "embedding",
    "dataset_discovery",
    "storage",
    "ipfs_pin",
}

_DAEMON_PREFERRED_REMOTE_CAPABILITIES = {
    "workflow",
    "agentic_fetch",
}


def resolve_virtual_ai_os_runtime_placement(
    capability_id: str,
    execution_mode: CapabilityExecutionMode,
    preferred_surface: str | CapabilityRuntimeSurface | None = None,
) -> AICapabilityRuntimePlacement:
    """Resolve where a capability should run for a selected execution mode."""
    normalized_surface = normalize_virtual_ai_os_runtime_surface(preferred_surface)
    supported_surfaces = supported_virtual_ai_os_runtime_surfaces(capability_id, execution_mode)
    default_surface = default_virtual_ai_os_runtime_surface(capability_id, execution_mode)

    if normalized_surface is None:
        runtime_surface = default_surface
    elif normalized_surface in supported_surfaces:
        runtime_surface = normalized_surface
    else:
        raise ValueError(
            f"Capability '{capability_id}' does not support runtime surface '{normalized_surface.value}' "
            f"for execution mode '{execution_mode.value}'"
        )

    return AICapabilityRuntimePlacement(
        capability_id=capability_id,
        execution_mode=execution_mode,
        runtime_surface=runtime_surface,
        supported_surfaces=supported_surfaces,
        fallback_surfaces=tuple(surface for surface in supported_surfaces if surface != runtime_surface),
    )


def default_virtual_ai_os_runtime_surface(
    capability_id: str,
    execution_mode: CapabilityExecutionMode,
) -> CapabilityRuntimeSurface:
    """Return the default runtime surface for one capability/mode pair."""
    if execution_mode == CapabilityExecutionMode.DIRECT_IMPORT:
        return CapabilityRuntimeSurface.DIRECT_ADAPTER
    if execution_mode == CapabilityExecutionMode.DIRECT_CLI:
        return CapabilityRuntimeSurface.LOCAL_CLI
    if execution_mode == CapabilityExecutionMode.ORCHESTRATED:
        return CapabilityRuntimeSurface.DAEMON_MEDIATED
    if capability_id in _DAEMON_PREFERRED_REMOTE_CAPABILITIES:
        return CapabilityRuntimeSurface.DAEMON_MEDIATED
    return CapabilityRuntimeSurface.MCP_PROVIDER


def supported_virtual_ai_os_runtime_surfaces(
    capability_id: str,
    execution_mode: CapabilityExecutionMode,
) -> tuple[CapabilityRuntimeSurface, ...]:
    """Return all supported runtime surfaces for one capability/mode pair."""
    if execution_mode == CapabilityExecutionMode.DIRECT_IMPORT:
        return (CapabilityRuntimeSurface.DIRECT_ADAPTER,)
    if execution_mode == CapabilityExecutionMode.DIRECT_CLI:
        return (CapabilityRuntimeSurface.LOCAL_CLI,)
    if execution_mode == CapabilityExecutionMode.ORCHESTRATED:
        return (CapabilityRuntimeSurface.DAEMON_MEDIATED,)
    if capability_id in _MCP_REMOTE_DATA_SURFACES:
        return (CapabilityRuntimeSurface.MCP_PROVIDER, CapabilityRuntimeSurface.SWISSKNIFE_ORB)
    return (
        CapabilityRuntimeSurface.MCP_PROVIDER,
        CapabilityRuntimeSurface.DAEMON_MEDIATED,
        CapabilityRuntimeSurface.SWISSKNIFE_ORB,
    )


def normalize_virtual_ai_os_runtime_surface(
    value: str | CapabilityRuntimeSurface | None,
) -> CapabilityRuntimeSurface | None:
    """Normalize runtime-surface input from API, daemon, or Python callers."""
    if value is None:
        return None
    if isinstance(value, CapabilityRuntimeSurface):
        return value
    normalized = value.strip().lower()
    if not normalized:
        return None
    return CapabilityRuntimeSurface(normalized)
