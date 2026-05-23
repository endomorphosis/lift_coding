"""Tests for the virtual AI OS runtime router."""

from handsfree.ai import (
    CapabilityExecutionMode,
    CapabilityRuntimeSurface,
    resolve_virtual_ai_os_runtime_route,
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