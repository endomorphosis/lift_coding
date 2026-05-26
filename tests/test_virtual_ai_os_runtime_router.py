"""Tests for the virtual AI OS runtime router."""

from handsfree.ai import (
    CapabilityExecutionMode,
    CapabilityRuntimeSurface,
    resolve_virtual_ai_os_runtime_route,
)
from handsfree.capability_registry import (
    NORMALIZED_ERROR_CONTRACT_ID,
    CapabilityDispatchRequest,
    CapabilityRoutingKernel,
    RuntimeRouter,
)


def test_runtime_router_uses_direct_adapter_for_embedding_by_default():
    route = resolve_virtual_ai_os_runtime_route("embedding")

    assert route.execution_mode == CapabilityExecutionMode.DIRECT_IMPORT
    assert route.runtime_surface == CapabilityRuntimeSurface.DIRECT_ADAPTER
    assert route.handler_ref == "handsfree.ipfs_datasets_routers:get_embeddings_router"
    assert route.cli_command is None


def test_runtime_router_uses_cli_surface_for_requested_ipfs_pin_cli_mode():
    route = resolve_virtual_ai_os_runtime_route(
        "ipfs_pin",
        requested_mode=CapabilityExecutionMode.DIRECT_CLI,
    )

    assert route.runtime_surface == CapabilityRuntimeSurface.LOCAL_CLI
    assert route.cli_command == "ipfs-kit"
    assert route.handler_ref == "handsfree.ai.runtime_router:run_local_cli"


def test_runtime_router_uses_daemon_surface_for_accelerate_workflow():
    route = resolve_virtual_ai_os_runtime_route("workflow")

    assert route.execution_mode == CapabilityExecutionMode.MCP_REMOTE
    assert route.runtime_surface == CapabilityRuntimeSurface.DAEMON_MEDIATED
    assert route.handler_ref == "handsfree.ai.runtime_router:run_daemon_workflow"


def test_runtime_router_allows_swissknife_orb_override_for_remote_capability():
    route = resolve_virtual_ai_os_runtime_route(
        "dataset_discovery",
        preferred_surface=CapabilityRuntimeSurface.SWISSKNIFE_ORB,
    )

    assert route.execution_mode == CapabilityExecutionMode.MCP_REMOTE
    assert route.runtime_surface == CapabilityRuntimeSurface.SWISSKNIFE_ORB
    assert route.handler_ref == "swissknife.orb::dataset_discovery"


def test_runtime_router_rejects_invalid_surface_for_direct_import_capability():
    try:
        resolve_virtual_ai_os_runtime_route(
            "embedding",
            preferred_surface=CapabilityRuntimeSurface.SWISSKNIFE_ORB,
        )
    except ValueError as exc:
        assert "does not support runtime surface" in str(exc)
    else:
        raise AssertionError("Expected unsupported runtime surface to fail")


def test_capability_routing_kernel_dispatches_with_fallback_and_presentations():
    plan = CapabilityRoutingKernel().dispatch_task(
        CapabilityDispatchRequest(
            capability_id="embedding",
            payload={"text": "route me"},
        )
    )

    assert plan.capability_id == "embedding"
    assert plan.route.runtime_surface == CapabilityRuntimeSurface.DIRECT_ADAPTER
    assert plan.fallback_route is not None
    assert plan.fallback_route.execution_mode == CapabilityExecutionMode.MCP_REMOTE
    assert plan.fallback_route.runtime_surface == CapabilityRuntimeSurface.MCP_PROVIDER
    assert plan.error_contract_id == NORMALIZED_ERROR_CONTRACT_ID
    assert [entry.surface_id for entry in plan.entrypoints] == [
        "local_python",
        "hallucinate_app",
        "mobile_glasses",
    ]
    assert (
        plan.entrypoints[0].handler_ref
        == "handsfree.ipfs_datasets_routers:get_embeddings_router"
    )
    assert plan.payload == {"text": "route me"}


def test_capability_routing_kernel_builds_swissknife_orb_mobile_task_flow_plan():
    plan = CapabilityRoutingKernel().dispatch_task(
        CapabilityDispatchRequest(
            capability_id="dataset_discovery",
            preferred_surface=CapabilityRuntimeSurface.SWISSKNIFE_ORB,
            source_surface="todo_daemon",
            payload={
                "task_id": "VAI-019",
                "todo_daemon_state": {"task_status": "ready"},
                "artifact_refs": {
                    "result_cid": "bafybeivai019taskprogress",
                    "receipt_ref": "bafybeivai019receipt",
                    "event_dag_ref": "bafybeivai019eventdag",
                },
            },
        )
    )

    assert plan.route.execution_mode == CapabilityExecutionMode.MCP_REMOTE
    assert plan.route.runtime_surface == CapabilityRuntimeSurface.SWISSKNIFE_ORB
    assert plan.route.handler_ref == "swissknife.orb::dataset_discovery"
    assert plan.fallback_route is not None
    assert plan.fallback_route.runtime_surface == CapabilityRuntimeSurface.LOCAL_CLI
    assert [entry.surface_id for entry in plan.entrypoints] == [
        "swissknife_orb",
        "hallucinate_app",
        "mobile_glasses",
    ]
    assert plan.entrypoints[-1].handler_ref == (
        "handsfree.meta_glasses_mobile_orb_runtime:invoke_mobile_orb_runtime_binding"
    )
    assert plan.payload["task_id"] == "VAI-019"
    assert plan.payload["artifact_refs"]["receipt_ref"] == "bafybeivai019receipt"


def test_runtime_router_normalizes_route_planning_errors():
    router = RuntimeRouter()
    try:
        router.resolve_route(
            "dataset_discovery",
            requested_mode=CapabilityExecutionMode.DIRECT_IMPORT,
        )
    except ValueError as exc:
        error = router.build_error_contract(
            exc,
            capability_id="dataset_discovery",
            details={"requested_mode": "direct_import"},
        )
    else:
        raise AssertionError("Expected unsupported route to fail")

    assert error.as_dict() == {
        "ok": False,
        "contract_id": NORMALIZED_ERROR_CONTRACT_ID,
        "capability_id": "dataset_discovery",
        "error_code": "capability_route_error",
        "message": "Capability 'dataset_discovery' does not support execution mode 'direct_import'",
        "recoverable": True,
        "details": {"requested_mode": "direct_import"},
    }
