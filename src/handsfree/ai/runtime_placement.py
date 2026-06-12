"""Runtime placement policy for virtual AI OS capability routes."""

from __future__ import annotations

from .capability_registry import get_virtual_ai_os_capability
from .models import (
    AICapabilityRuntimePlacement,
    CapabilityExecutionMode,
    CapabilityPlacementLayer,
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

_SWISSKNIFE_PREFERRED_REMOTE_CAPABILITIES = {
    "ui_render_session",
}

_SERVER_FAMILY_PLACEMENTS: dict[str, tuple[CapabilityPlacementLayer, str]] = {
    "ipfs_datasets": (
        CapabilityPlacementLayer.SEMANTIC_ROUTING,
        "endomorphosis/ipfs_datasets_py",
    ),
    "ipfs_accelerate": (
        CapabilityPlacementLayer.EXECUTION_ACCELERATION,
        "endomorphosis/ipfs_accelerate_py",
    ),
    "ipfs_kit": (
        CapabilityPlacementLayer.CONTENT_PROVENANCE,
        "endomorphosis/ipfs_kit_py",
    ),
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
        **_placement_metadata(capability_id, execution_mode, runtime_surface),
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
    if capability_id in _SWISSKNIFE_PREFERRED_REMOTE_CAPABILITIES:
        return CapabilityRuntimeSurface.SWISSKNIFE_ORB
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
    if capability_id in _SWISSKNIFE_PREFERRED_REMOTE_CAPABILITIES:
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


def _placement_metadata(
    capability_id: str,
    execution_mode: CapabilityExecutionMode,
    runtime_surface: CapabilityRuntimeSurface,
) -> dict[str, object]:
    entry = get_virtual_ai_os_capability(capability_id)

    if runtime_surface == CapabilityRuntimeSurface.SWISSKNIFE_ORB:
        return {
            "placement_layer": CapabilityPlacementLayer.SWISSKNIFE_ORB,
            "target_repo": "endomorphosis/swissknife",
            "reason": "SwissKnife owns ORB binding and virtual desktop tool invocation.",
            "constraints": ("preserve_capability_id", "receipt_backed_operator_fallback"),
        }

    if runtime_surface == CapabilityRuntimeSurface.MCP_PROVIDER:
        return {
            "placement_layer": CapabilityPlacementLayer.MCP_PROTOCOL,
            "target_repo": entry.owner_repo,
            "reason": "MCP/MCP++ protocol routing keeps the provider implementation behind MCP.",
            "constraints": (
                "distributed_mcp_surface",
                "do_not_require_standalone_mcp_plus_plus_runtime",
            ),
        }

    if runtime_surface == CapabilityRuntimeSurface.DAEMON_MEDIATED:
        if entry.server_family == "ipfs_accelerate":
            layer, target_repo = _SERVER_FAMILY_PLACEMENTS[entry.server_family]
            reason = "ipfs_accelerate_py owns long-running execution placement workflows."
            constraints = ("daemon_supervised", "artifact_receipts_required")
        else:
            layer = CapabilityPlacementLayer.HANDSFREE_DAEMON
            target_repo = "handsfree"
            reason = "HandsFree daemon mediation owns supervised local task scheduling."
            constraints = ("daemon_supervised",)
        return {
            "placement_layer": layer,
            "target_repo": target_repo,
            "reason": reason,
            "constraints": constraints,
        }

    if runtime_surface in {
        CapabilityRuntimeSurface.DIRECT_ADAPTER,
        CapabilityRuntimeSurface.LOCAL_CLI,
    }:
        try:
            layer, target_repo = _SERVER_FAMILY_PLACEMENTS[entry.server_family]
        except KeyError as exc:
            raise ValueError(
                f"Capability '{entry.capability_id}' has no placement layer for "
                f"server family '{entry.server_family}'"
            ) from exc
        return {
            "placement_layer": layer,
            "target_repo": target_repo,
            "reason": "Local execution stays with the component repository that owns the capability.",
            "constraints": ("local_runtime_available",),
        }

    raise ValueError(
        f"Unsupported runtime surface '{runtime_surface.value}' for placement of "
        f"capability '{entry.capability_id}'/{execution_mode.value}"
    )
