"""Public capability routing kernel for the virtual AI OS.

This module is the stable top-level entry point for capability routing evidence.
It delegates the concrete registry and route selection to ``handsfree.ai`` while
exposing one kernel path that can be shared by local Python, daemon tasks,
MCP/MCP++, SwissKnife ORB, Hallucinate App, and mobile/glasses surfaces.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from typing import Any

from handsfree.ai.capability_registry import (
    build_virtual_ai_os_execution_matrix,
    get_virtual_ai_os_capability,
    list_virtual_ai_os_capabilities,
    resolve_virtual_ai_os_execution_mode,
)
from handsfree.ai.models import (
    AICapabilityRegistryEntry,
    AICapabilityRoute,
    CapabilityExecutionMode,
    CapabilityRuntimeSurface,
)
from handsfree.ai.runtime_router import resolve_virtual_ai_os_runtime_route

NORMALIZED_ERROR_CONTRACT_ID = "handsfree.capability.error.v1"

CAPABILITY_ROUTING_SURFACE_LABELS: Mapping[str, str] = {
    "local_python": "local Python",
    "daemon_task": "daemon tasks",
    "mcp_mcp_plus_plus": "MCP/MCP++",
    "swissknife_orb": "SwissKnife ORB",
    "hallucinate_app": "Hallucinate App",
    "mobile_glasses": "mobile/glasses",
}

CAPABILITY_ROUTING_SURFACES = tuple(CAPABILITY_ROUTING_SURFACE_LABELS)


@dataclass(frozen=True)
class CapabilitySurfaceEndpoint:
    """A routable runtime or presentation surface for a capability plan."""

    surface_id: str
    label: str
    role: str
    handler_ref: str
    cli_command: str | None = None


@dataclass(frozen=True)
class CapabilityDispatchRequest:
    """Route-planning request for a stable virtual AI OS capability id."""

    capability_id: str
    payload: Mapping[str, Any] = field(default_factory=dict)
    requested_mode: str | CapabilityExecutionMode | None = None
    provider_preferred_modes: tuple[str | CapabilityExecutionMode, ...] = ()
    policy_preferred_modes: tuple[str | CapabilityExecutionMode, ...] = ()
    preferred_surface: str | CapabilityRuntimeSurface | None = None
    source_surface: str | None = None


@dataclass(frozen=True)
class CapabilityDispatchPlan:
    """Resolved route plus the surfaces that can consume the dispatch plan."""

    capability_id: str
    route: AICapabilityRoute
    payload: Mapping[str, Any]
    entrypoints: tuple[CapabilitySurfaceEndpoint, ...]
    fallback_route: AICapabilityRoute | None = None
    error_contract_id: str = NORMALIZED_ERROR_CONTRACT_ID


@dataclass(frozen=True)
class CapabilityRoutingError:
    """Normalized route-planning error envelope for callers and child goals."""

    capability_id: str | None
    error_code: str
    message: str
    recoverable: bool
    contract_id: str = NORMALIZED_ERROR_CONTRACT_ID
    details: Mapping[str, Any] = field(default_factory=dict)

    def as_dict(self) -> dict[str, Any]:
        """Return the normalized error contract as JSON-serializable data."""
        return {
            "ok": False,
            "contract_id": self.contract_id,
            "capability_id": self.capability_id,
            "error_code": self.error_code,
            "message": self.message,
            "recoverable": self.recoverable,
            "details": dict(self.details),
        }


class CapabilityRegistry:
    """Top-level facade for stable virtual AI OS capability ids."""

    def list_capabilities(self) -> list[AICapabilityRegistryEntry]:
        """Return registered capabilities in deterministic order."""
        return list_virtual_ai_os_capabilities()

    def get(self, capability_id: str) -> AICapabilityRegistryEntry:
        """Resolve a canonical or legacy capability id."""
        return get_virtual_ai_os_capability(capability_id)

    def resolve_execution_mode(
        self,
        capability_id: str,
        *,
        requested_mode: str | CapabilityExecutionMode | None = None,
        provider_preferred_modes: tuple[str | CapabilityExecutionMode, ...] = (),
        policy_preferred_modes: tuple[str | CapabilityExecutionMode, ...] = (),
        allow_fallback: bool = True,
    ) -> CapabilityExecutionMode:
        """Resolve the execution mode for a capability through the shared registry."""
        return resolve_virtual_ai_os_execution_mode(
            capability_id,
            requested_mode=requested_mode,
            provider_preferred_modes=provider_preferred_modes,
            policy_preferred_modes=policy_preferred_modes,
            allow_fallback=allow_fallback,
        )

    def execution_matrix(self) -> list[dict[str, object]]:
        """Return the compact registry execution matrix."""
        return build_virtual_ai_os_execution_matrix()


class RuntimeRouter:
    """Route capabilities into concrete runtime and presentation surfaces."""

    def resolve_route(
        self,
        capability_id: str,
        *,
        requested_mode: str | CapabilityExecutionMode | None = None,
        provider_preferred_modes: tuple[str | CapabilityExecutionMode, ...] = (),
        policy_preferred_modes: tuple[str | CapabilityExecutionMode, ...] = (),
        preferred_surface: str | CapabilityRuntimeSurface | None = None,
    ) -> AICapabilityRoute:
        """Resolve one capability into the underlying runtime route."""
        return resolve_virtual_ai_os_runtime_route(
            capability_id,
            requested_mode=requested_mode,
            provider_preferred_modes=provider_preferred_modes,
            policy_preferred_modes=policy_preferred_modes,
            preferred_surface=preferred_surface,
        )

    def dispatch_task(self, request: CapabilityDispatchRequest | str) -> CapabilityDispatchPlan:
        """Build a dispatch plan without executing the selected capability."""
        if isinstance(request, str):
            dispatch_request = CapabilityDispatchRequest(capability_id=request)
        else:
            dispatch_request = request
        route = self.resolve_route(
            dispatch_request.capability_id,
            requested_mode=dispatch_request.requested_mode,
            provider_preferred_modes=dispatch_request.provider_preferred_modes,
            policy_preferred_modes=dispatch_request.policy_preferred_modes,
            preferred_surface=dispatch_request.preferred_surface,
        )
        fallback_route = self.resolve_fallback_route(route)
        return CapabilityDispatchPlan(
            capability_id=route.capability_id,
            route=route,
            payload=dict(dispatch_request.payload),
            entrypoints=_entrypoints_for_route(route),
            fallback_route=fallback_route,
        )

    def resolve_fallback_route(self, route: AICapabilityRoute) -> AICapabilityRoute | None:
        """Resolve the capability's fallback route when it has a distinct mode."""
        fallback_mode = route.fallback_execution_mode
        if fallback_mode is None or fallback_mode == route.execution_mode:
            return None
        return self.resolve_route(route.capability_id, requested_mode=fallback_mode)

    def build_error_contract(
        self,
        exc: Exception,
        *,
        capability_id: str | None = None,
        recoverable: bool = True,
        details: Mapping[str, Any] | None = None,
    ) -> CapabilityRoutingError:
        """Normalize route-planning failures for API, app, and mobile callers."""
        return CapabilityRoutingError(
            capability_id=capability_id,
            error_code="capability_route_error",
            message=str(exc),
            recoverable=recoverable,
            details=details or {},
        )


class CapabilityRoutingKernel:
    """Small composition root for registry lookup and runtime dispatch planning."""

    def __init__(
        self,
        *,
        registry: CapabilityRegistry | None = None,
        router: RuntimeRouter | None = None,
    ) -> None:
        self.registry = registry or CapabilityRegistry()
        self.router = router or RuntimeRouter()

    def dispatch_task(self, request: CapabilityDispatchRequest | str) -> CapabilityDispatchPlan:
        """Resolve a stable capability id into a dispatch plan."""
        return self.router.dispatch_task(request)


def list_capability_routing_surfaces() -> tuple[CapabilitySurfaceEndpoint, ...]:
    """Return the virtual AI OS routing-surface catalog."""
    return (
        CapabilitySurfaceEndpoint(
            surface_id="local_python",
            label=CAPABILITY_ROUTING_SURFACE_LABELS["local_python"],
            role="runtime",
            handler_ref="handsfree.ai.runtime_router",
        ),
        CapabilitySurfaceEndpoint(
            surface_id="daemon_task",
            label=CAPABILITY_ROUTING_SURFACE_LABELS["daemon_task"],
            role="scheduler",
            handler_ref="handsfree.ai.runtime_router:run_daemon_workflow",
        ),
        CapabilitySurfaceEndpoint(
            surface_id="mcp_mcp_plus_plus",
            label=CAPABILITY_ROUTING_SURFACE_LABELS["mcp_mcp_plus_plus"],
            role="remote_provider",
            handler_ref="handsfree.mcp",
        ),
        CapabilitySurfaceEndpoint(
            surface_id="swissknife_orb",
            label=CAPABILITY_ROUTING_SURFACE_LABELS["swissknife_orb"],
            role="orb_bridge",
            handler_ref="swissknife.orb",
        ),
        *_PRESENTATION_SURFACE_ENDPOINTS,
    )


_RUNTIME_SURFACE_ENDPOINTS: Mapping[
    CapabilityRuntimeSurface,
    tuple[str, str, str],
] = {
    CapabilityRuntimeSurface.DIRECT_ADAPTER: (
        "local_python",
        "runtime",
        "local Python direct adapter",
    ),
    CapabilityRuntimeSurface.LOCAL_CLI: (
        "local_python",
        "runtime_cli",
        "local Python CLI",
    ),
    CapabilityRuntimeSurface.MCP_PROVIDER: (
        "mcp_mcp_plus_plus",
        "remote_provider",
        "MCP/MCP++ provider",
    ),
    CapabilityRuntimeSurface.DAEMON_MEDIATED: (
        "daemon_task",
        "scheduler",
        "daemon tasks scheduler",
    ),
    CapabilityRuntimeSurface.SWISSKNIFE_ORB: (
        "swissknife_orb",
        "orb_bridge",
        "SwissKnife ORB",
    ),
}

_PRESENTATION_SURFACE_ENDPOINTS = (
    CapabilitySurfaceEndpoint(
        surface_id="hallucinate_app",
        label=CAPABILITY_ROUTING_SURFACE_LABELS["hallucinate_app"],
        role="operator_console",
        handler_ref="hallucinate_app/index.js#operator_console",
    ),
    CapabilitySurfaceEndpoint(
        surface_id="mobile_glasses",
        label=CAPABILITY_ROUTING_SURFACE_LABELS["mobile_glasses"],
        role="remote_terminal",
        handler_ref="handsfree.meta_glasses_mobile_orb_runtime:invoke_mobile_orb_runtime_binding",
    ),
)


def _entrypoints_for_route(route: AICapabilityRoute) -> tuple[CapabilitySurfaceEndpoint, ...]:
    surface_id, role, fallback_handler_ref = _RUNTIME_SURFACE_ENDPOINTS[route.runtime_surface]
    runtime_endpoint = CapabilitySurfaceEndpoint(
        surface_id=surface_id,
        label=CAPABILITY_ROUTING_SURFACE_LABELS[surface_id],
        role=role,
        handler_ref=route.handler_ref or fallback_handler_ref,
        cli_command=route.cli_command,
    )
    return (runtime_endpoint, *_PRESENTATION_SURFACE_ENDPOINTS)


__all__ = [
    "CAPABILITY_ROUTING_SURFACE_LABELS",
    "CAPABILITY_ROUTING_SURFACES",
    "NORMALIZED_ERROR_CONTRACT_ID",
    "CapabilityDispatchPlan",
    "CapabilityDispatchRequest",
    "CapabilityRegistry",
    "CapabilityRoutingError",
    "CapabilityRoutingKernel",
    "CapabilitySurfaceEndpoint",
    "RuntimeRouter",
    "list_capability_routing_surfaces",
]
