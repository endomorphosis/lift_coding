"""Tests for the Swissknife virtual UI and ORB binding contract."""

from pathlib import Path

from handsfree.ai import CapabilityRuntimeSurface, get_virtual_ai_os_capability
from handsfree.capability_registry import CapabilityDispatchRequest, CapabilityRoutingKernel
from handsfree.swissknife_virtual_ui import (
    get_swissknife_orb_handler_ref,
    get_swissknife_virtual_ai_os_binding,
    validate_swissknife_binding_sources,
)

REPO_ROOT = Path(__file__).resolve().parents[1]


def test_swissknife_virtual_ai_os_binding_points_to_existing_sources():
    binding = get_swissknife_virtual_ai_os_binding()

    assert binding.binding_id == "handsfree.virtual_ai_os.swissknife.v1"
    assert binding.virtual_ui.surface_id == "swissknife_virtual_desktop"
    assert binding.virtual_ui.app_id == "mcp-control"
    assert binding.orb_plane.surface_id == "swissknife_orb"
    assert binding.orb_plane.handler_namespace == "swissknife.orb"
    assert validate_swissknife_binding_sources(REPO_ROOT) == ()


def test_swissknife_orb_binding_uses_registered_virtual_ai_os_capabilities():
    binding = get_swissknife_virtual_ai_os_binding()
    expected_capability_ids = {
        get_virtual_ai_os_capability(capability_id).capability_id
        for capability_id in binding.orb_plane.capability_ids
    }

    assert {"dataset_discovery", "ui_render_session", "device_render_transport"} <= (
        expected_capability_ids
    )
    assert (
        get_swissknife_orb_handler_ref("dataset_discovery")
        == "swissknife.orb::dataset_discovery"
    )
    assert (
        get_swissknife_orb_handler_ref("ui_render_session")
        == "swissknife.orb::ui_render_session"
    )


def test_swissknife_orb_dispatch_plan_exposes_virtual_ui_binding_metadata():
    plan = CapabilityRoutingKernel().dispatch_task(
        CapabilityDispatchRequest(
            capability_id="dataset_discovery",
            preferred_surface=CapabilityRuntimeSurface.SWISSKNIFE_ORB,
        )
    )

    swissknife_endpoint = plan.entrypoints[0]

    assert swissknife_endpoint.surface_id == "swissknife_orb"
    assert swissknife_endpoint.handler_ref == "swissknife.orb::dataset_discovery"
    assert swissknife_endpoint.metadata["virtual_ui_surface"] == "swissknife_virtual_desktop"
    assert swissknife_endpoint.metadata["virtual_ui_app_id"] == "mcp-control"
    assert (
        swissknife_endpoint.metadata["orb_router_module"]
        == "swissknife/src/services/mcp-orb-capability-router.ts"
    )
    assert swissknife_endpoint.metadata["orb_transport_kinds"] == (
        "local",
        "websocket",
        "http",
        "mcp-server",
    )
    assert (
        swissknife_endpoint.metadata["mobile_orb_runtime"]
        == "handsfree.meta_glasses_mobile_orb_runtime:invoke_mobile_orb_runtime_binding"
    )
