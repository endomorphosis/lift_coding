"""Swissknife virtual UI and ORB binding contract for the virtual AI OS."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from handsfree.ai.capability_registry import (
    get_virtual_ai_os_capability,
    list_virtual_ai_os_capabilities,
)


@dataclass(frozen=True)
class SwissknifeVirtualUIBinding:
    """Virtual desktop entrypoint that hosts virtual AI OS operator controls."""

    surface_id: str
    app_id: str
    label: str
    launch_command: str
    source_ref: str
    fallback_surface_ids: tuple[str, ...]


@dataclass(frozen=True)
class SwissknifeORBPlaneBinding:
    """ORB-side binding points exposed by the Swissknife submodule."""

    surface_id: str
    handler_namespace: str
    router_module: str
    descriptor_pack_module: str
    descriptor_pack_export: str
    transport_kinds: tuple[str, ...]
    capability_ids: tuple[str, ...]
    source_refs: tuple[str, ...]
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class SwissknifeVirtualAIOSBinding:
    """Complete Swissknife binding across the virtual UI and ORB planes."""

    binding_id: str
    version: str
    virtual_ui: SwissknifeVirtualUIBinding
    orb_plane: SwissknifeORBPlaneBinding

    def as_dict(self) -> dict[str, Any]:
        """Return a JSON-serializable binding descriptor."""
        return {
            "binding_id": self.binding_id,
            "version": self.version,
            "virtual_ui": {
                "surface_id": self.virtual_ui.surface_id,
                "app_id": self.virtual_ui.app_id,
                "label": self.virtual_ui.label,
                "launch_command": self.virtual_ui.launch_command,
                "source_ref": self.virtual_ui.source_ref,
                "fallback_surface_ids": self.virtual_ui.fallback_surface_ids,
            },
            "orb_plane": {
                "surface_id": self.orb_plane.surface_id,
                "handler_namespace": self.orb_plane.handler_namespace,
                "router_module": self.orb_plane.router_module,
                "descriptor_pack_module": self.orb_plane.descriptor_pack_module,
                "descriptor_pack_export": self.orb_plane.descriptor_pack_export,
                "transport_kinds": self.orb_plane.transport_kinds,
                "capability_ids": self.orb_plane.capability_ids,
                "source_refs": self.orb_plane.source_refs,
                "metadata": dict(self.orb_plane.metadata),
            },
        }


def _registered_capability_ids() -> tuple[str, ...]:
    return tuple(entry.capability_id for entry in list_virtual_ai_os_capabilities())


_SWISSKNIFE_BINDING = SwissknifeVirtualAIOSBinding(
    binding_id="handsfree.virtual_ai_os.swissknife.v1",
    version="0.1.0",
    virtual_ui=SwissknifeVirtualUIBinding(
        surface_id="swissknife_virtual_desktop",
        app_id="mcp-control",
        label="SwissKnife MCP Control",
        launch_command="swissknife sk-desktop launch mcp-control --workspace virtual-ai-os",
        source_ref="swissknife/src/shared/constants/index.ts#APP_IDS.MCP_CONTROL",
        fallback_surface_ids=("hallucinate_app", "mobile_glasses"),
    ),
    orb_plane=SwissknifeORBPlaneBinding(
        surface_id="swissknife_orb",
        handler_namespace="swissknife.orb",
        router_module="swissknife/src/services/mcp-orb-capability-router.ts",
        descriptor_pack_module="swissknife/src/services/mcp-ipfs-datasets-descriptor-pack.ts",
        descriptor_pack_export="getIPFSDatasetsDescriptorPackDescriptors",
        transport_kinds=("local", "websocket", "http", "mcp-server"),
        capability_ids=_registered_capability_ids(),
        source_refs=(
            "swissknife/src/services/mcp-orb-capability-router.ts",
            "swissknife/src/services/mcp-ipfs-datasets-descriptor-pack.ts",
            "swissknife/src/services/mcp-ui-profile.ts",
        ),
        metadata={
            "control_surface_contract": "swissknife/contracts/control_surface_contract.schema.json",
            "interaction_envelope": "swissknife/contracts/interaction_envelope.schema.json",
            "mediation_receipt": "swissknife/contracts/mediation_receipt.schema.json",
        },
    ),
)


def get_swissknife_virtual_ai_os_binding() -> SwissknifeVirtualAIOSBinding:
    """Return the stable Swissknife virtual AI OS binding descriptor."""
    return _SWISSKNIFE_BINDING


def get_swissknife_orb_handler_ref(capability_id: str) -> str:
    """Return the ORB handler reference for a capability supported by Swissknife."""
    normalized_capability = get_virtual_ai_os_capability(capability_id).capability_id
    if normalized_capability not in _SWISSKNIFE_BINDING.orb_plane.capability_ids:
        raise ValueError(f"Capability '{normalized_capability}' is not bound to Swissknife ORB")
    return f"{_SWISSKNIFE_BINDING.orb_plane.handler_namespace}::{normalized_capability}"


def build_swissknife_surface_metadata() -> dict[str, Any]:
    """Return compact endpoint metadata for routing plans and surface catalogs."""
    binding = get_swissknife_virtual_ai_os_binding()
    return {
        "binding_id": binding.binding_id,
        "version": binding.version,
        "virtual_ui_surface": binding.virtual_ui.surface_id,
        "virtual_ui_app_id": binding.virtual_ui.app_id,
        "virtual_ui_launch_command": binding.virtual_ui.launch_command,
        "orb_router_module": binding.orb_plane.router_module,
        "orb_descriptor_pack_module": binding.orb_plane.descriptor_pack_module,
        "orb_descriptor_pack_export": binding.orb_plane.descriptor_pack_export,
        "orb_transport_kinds": binding.orb_plane.transport_kinds,
        "fallback_surface_ids": binding.virtual_ui.fallback_surface_ids,
    }


def validate_swissknife_binding_sources(repo_root: Path) -> tuple[str, ...]:
    """Return missing source refs for the local Swissknife binding, if any."""
    binding = get_swissknife_virtual_ai_os_binding()
    source_refs = (
        binding.virtual_ui.source_ref.split("#", 1)[0],
        *binding.orb_plane.source_refs,
        *(
            ref
            for ref in binding.orb_plane.metadata.values()
            if isinstance(ref, str) and ref.startswith("swissknife/")
        ),
    )
    return tuple(ref for ref in source_refs if not (repo_root / ref).exists())


__all__ = [
    "SwissknifeORBPlaneBinding",
    "SwissknifeVirtualAIOSBinding",
    "SwissknifeVirtualUIBinding",
    "build_swissknife_surface_metadata",
    "get_swissknife_orb_handler_ref",
    "get_swissknife_virtual_ai_os_binding",
    "validate_swissknife_binding_sources",
]
