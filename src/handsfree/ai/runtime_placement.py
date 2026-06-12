"""Virtual runtime placement decisions for cross-repo capability routes."""

from __future__ import annotations

from dataclasses import dataclass

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
    runtime_surface: CapabilityRuntimeSurface,
) -> RuntimePlacementDecision:
    """Resolve the virtual runtime layer for an already-valid route choice."""
    entry = get_virtual_ai_os_capability(capability_id)

    if runtime_surface == CapabilityRuntimeSurface.SWISSKNIFE_ORB:
        return RuntimePlacementDecision(
            capability_id=entry.capability_id,
            execution_mode=execution_mode,
            runtime_surface=runtime_surface,
            placement_layer=CapabilityPlacementLayer.SWISSKNIFE_ORB,
            target_repo="endomorphosis/swissknife",
            reason="SwissKnife owns ORB binding and virtual desktop tool invocation.",
            constraints=("preserve_capability_id", "receipt_backed_operator_fallback"),
        )

    if runtime_surface == CapabilityRuntimeSurface.MCP_PROVIDER:
        return RuntimePlacementDecision(
            capability_id=entry.capability_id,
            execution_mode=execution_mode,
            runtime_surface=runtime_surface,
            placement_layer=CapabilityPlacementLayer.MCP_PROTOCOL,
            target_repo=entry.owner_repo,
            reason="MCP/MCP++ protocol routing keeps the provider implementation behind MCP.",
            constraints=(
                "distributed_mcp_surface",
                "do_not_require_standalone_mcp_plus_plus_runtime",
            ),
        )

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
        return RuntimePlacementDecision(
            capability_id=entry.capability_id,
            execution_mode=execution_mode,
            runtime_surface=runtime_surface,
            placement_layer=layer,
            target_repo=target_repo,
            reason=reason,
            constraints=constraints,
        )

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
        return RuntimePlacementDecision(
            capability_id=entry.capability_id,
            execution_mode=execution_mode,
            runtime_surface=runtime_surface,
            placement_layer=layer,
            target_repo=target_repo,
            reason="Local execution stays with the component repository that owns the capability.",
            constraints=("local_runtime_available",),
        )

    raise ValueError(
        f"Unsupported runtime surface '{runtime_surface.value}' for placement of "
        f"capability '{entry.capability_id}'"
    )


__all__ = [
    "RuntimePlacementDecision",
    "resolve_virtual_ai_os_runtime_placement",
]
