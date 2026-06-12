"""Virtual runtime placement decisions for cross-repo capability routes."""

from __future__ import annotations

from dataclasses import dataclass, field

from .capability_registry import get_virtual_ai_os_capability
from .models import (
    CapabilityExecutionMode,
    CapabilityPlacementLayer,
    CapabilityRuntimeSurface,
)


@dataclass(frozen=True)
class RuntimePlacementDecision:
    """Resolved virtual runtime layer and guardrails for a capability route."""

    capability_id: str
    execution_mode: CapabilityExecutionMode
    runtime_surface: CapabilityRuntimeSurface
    placement_layer: CapabilityPlacementLayer
    target_repo: str
    reason: str
    constraints: tuple[str, ...] = ()
    supported_surfaces: tuple[CapabilityRuntimeSurface, ...] = field(default_factory=tuple)
    fallback_surfaces: tuple[CapabilityRuntimeSurface, ...] = field(default_factory=tuple)


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


def supported_virtual_ai_os_runtime_surfaces(
    capability_id: str,
    execution_mode: CapabilityExecutionMode,
) -> tuple[CapabilityRuntimeSurface, ...]:
    """Return the ordered tuple of runtime surfaces supported for a capability and mode."""
    if execution_mode == CapabilityExecutionMode.DIRECT_IMPORT:
        return (CapabilityRuntimeSurface.DIRECT_ADAPTER,)
    if execution_mode == CapabilityExecutionMode.DIRECT_CLI:
        return (CapabilityRuntimeSurface.LOCAL_CLI,)
    if execution_mode == CapabilityExecutionMode.ORCHESTRATED:
        return (CapabilityRuntimeSurface.DAEMON_MEDIATED,)
    if capability_id in {
        "embedding",
        "dataset_discovery",
        "storage",
        "ipfs_pin",
        "ui_render_session",
    }:
        return (CapabilityRuntimeSurface.MCP_PROVIDER, CapabilityRuntimeSurface.SWISSKNIFE_ORB)
    return (
        CapabilityRuntimeSurface.MCP_PROVIDER,
        CapabilityRuntimeSurface.DAEMON_MEDIATED,
        CapabilityRuntimeSurface.SWISSKNIFE_ORB,
    )


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
    if capability_id == "ui_render_session":
        return CapabilityRuntimeSurface.SWISSKNIFE_ORB
    if capability_id in {"workflow", "agentic_fetch"}:
        return CapabilityRuntimeSurface.DAEMON_MEDIATED
    return CapabilityRuntimeSurface.MCP_PROVIDER


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


def resolve_virtual_ai_os_runtime_placement(
    capability_id: str,
    execution_mode: CapabilityExecutionMode,
    runtime_surface: CapabilityRuntimeSurface | None = None,
    *,
    preferred_surface: str | CapabilityRuntimeSurface | None = None,
) -> RuntimePlacementDecision:
    """Resolve the virtual runtime layer for a capability route.

    The resolved surface is taken from ``preferred_surface`` (keyword, accepts
    string or enum) if given, then from the positional ``runtime_surface`` arg
    for backward compatibility, and finally from the default for the
    capability/mode pair.  ``supported_surfaces`` and ``fallback_surfaces`` are
    always populated on the returned decision.
    """
    entry = get_virtual_ai_os_capability(capability_id)

    chosen = _normalize_surface(preferred_surface) or runtime_surface
    if chosen is None:
        chosen = _default_runtime_surface(capability_id, execution_mode)

    surfaces = supported_virtual_ai_os_runtime_surfaces(capability_id, execution_mode)
    fallback = tuple(s for s in surfaces if s != chosen)

    if chosen == CapabilityRuntimeSurface.SWISSKNIFE_ORB:
        return RuntimePlacementDecision(
            capability_id=entry.capability_id,
            execution_mode=execution_mode,
            runtime_surface=chosen,
            placement_layer=CapabilityPlacementLayer.SWISSKNIFE_ORB,
            target_repo="endomorphosis/swissknife",
            reason="SwissKnife owns ORB binding and virtual desktop tool invocation.",
            constraints=("preserve_capability_id", "receipt_backed_operator_fallback"),
            supported_surfaces=surfaces,
            fallback_surfaces=fallback,
        )

    if chosen == CapabilityRuntimeSurface.MCP_PROVIDER:
        return RuntimePlacementDecision(
            capability_id=entry.capability_id,
            execution_mode=execution_mode,
            runtime_surface=chosen,
            placement_layer=CapabilityPlacementLayer.MCP_PROTOCOL,
            target_repo=entry.owner_repo,
            reason="MCP/MCP++ protocol routing keeps the provider implementation behind MCP.",
            constraints=(
                "distributed_mcp_surface",
                "do_not_require_standalone_mcp_plus_plus_runtime",
            ),
            supported_surfaces=surfaces,
            fallback_surfaces=fallback,
        )

    if chosen == CapabilityRuntimeSurface.DAEMON_MEDIATED:
        if entry.server_family == "ipfs_accelerate":
            layer, target_repo = _SERVER_FAMILY_PLACEMENTS[entry.server_family]
            reason = "ipfs_accelerate_py owns long-running execution placement workflows."
            constraints = ("daemon_supervised", "artifact_receipts_required")
        else:
            layer = CapabilityPlacementLayer.HANDSFREE_DAEMON
            target_repo = "handsfree"
            reason = "HandsFree daemon mediation owns supervised local task scheduling."
            constraints = ("daemon_supervised",)
        return RuntimePlacementDecision(
            capability_id=entry.capability_id,
            execution_mode=execution_mode,
            runtime_surface=chosen,
            placement_layer=layer,
            target_repo=target_repo,
            reason=reason,
            constraints=constraints,
            supported_surfaces=surfaces,
            fallback_surfaces=fallback,
        )

    if chosen in {
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
        return RuntimePlacementDecision(
            capability_id=entry.capability_id,
            execution_mode=execution_mode,
            runtime_surface=chosen,
            placement_layer=layer,
            target_repo=target_repo,
            reason="Local execution stays with the component repository that owns the capability.",
            constraints=("local_runtime_available",),
            supported_surfaces=surfaces,
            fallback_surfaces=fallback,
        )

    raise ValueError(
        f"Unsupported runtime surface '{chosen.value}' for placement of "
        f"capability '{entry.capability_id}'"
    )


__all__ = [
    "RuntimePlacementDecision",
    "resolve_virtual_ai_os_runtime_placement",
    "supported_virtual_ai_os_runtime_surfaces",
]
