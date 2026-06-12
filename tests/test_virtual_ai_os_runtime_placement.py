"""Tests for the virtual AI OS runtime placement layer."""

from handsfree.ai import (
    CapabilityExecutionMode,
    CapabilityPlacementLayer,
    CapabilityRuntimeSurface,
    resolve_virtual_ai_os_runtime_placement,
    resolve_virtual_ai_os_runtime_route,
)


def test_runtime_placement_keeps_direct_embedding_on_semantic_layer():
    route = resolve_virtual_ai_os_runtime_route("embedding")

    assert route.placement_layer == CapabilityPlacementLayer.SEMANTIC_ROUTING
    assert route.placement_target == "endomorphosis/ipfs_datasets_py"
    assert route.placement_constraints == ("local_runtime_available",)


def test_runtime_placement_routes_accelerate_workflow_to_execution_layer():
    route = resolve_virtual_ai_os_runtime_route("workflow")

    assert route.runtime_surface == CapabilityRuntimeSurface.DAEMON_MEDIATED
    assert route.placement_layer == CapabilityPlacementLayer.EXECUTION_ACCELERATION
    assert route.placement_target == "endomorphosis/ipfs_accelerate_py"
    assert "artifact_receipts_required" in route.placement_constraints


def test_runtime_placement_records_mcp_guardrail_without_standalone_runtime():
    decision = resolve_virtual_ai_os_runtime_placement(
        "dataset_discovery",
        CapabilityExecutionMode.MCP_REMOTE,
        CapabilityRuntimeSurface.MCP_PROVIDER,
    )

    assert decision.placement_layer == CapabilityPlacementLayer.MCP_PROTOCOL
    assert decision.target_repo == "endomorphosis/ipfs_datasets_py"
    assert "distributed_mcp_surface" in decision.constraints
    assert "do_not_require_standalone_mcp_plus_plus_runtime" in decision.constraints


def test_runtime_placement_routes_orb_override_to_swissknife_layer():
    route = resolve_virtual_ai_os_runtime_route(
        "dataset_discovery",
        preferred_surface=CapabilityRuntimeSurface.SWISSKNIFE_ORB,
    )

    assert route.placement_layer == CapabilityPlacementLayer.SWISSKNIFE_ORB
    assert route.placement_target == "endomorphosis/swissknife"
    assert "receipt_backed_operator_fallback" in route.placement_constraints


def test_runtime_placement_routes_operator_console_override_to_hallucinate_app_layer():
    route = resolve_virtual_ai_os_runtime_route(
        "dataset_discovery",
        preferred_surface=CapabilityRuntimeSurface.OPERATOR_CONSOLE,
    )

    assert route.placement_layer == CapabilityPlacementLayer.OPERATOR_CONSOLE
    assert route.placement_target == "endomorphosis/hallucinate_app"
    assert "daemon_manager_receipts_required" in route.placement_constraints
    assert "swissknife_virtual_desktop_fallback" in route.placement_constraints
