"""Unit tests for Meta glasses mobile ORB artifact helpers."""

from __future__ import annotations

from handsfree.meta_glasses_mobile_orb_artifacts import (
    build_mobile_orb_bind_service_artifacts,
    build_mobile_orb_policy_decision,
    build_mobile_orb_register_artifacts,
)
from handsfree.models import (
    MetaGlassesMobileOrbBindServiceRequest,
    MetaGlassesMobileOrbRegisterRequest,
)


def test_build_mobile_orb_policy_decision_matches_orb_shape() -> None:
    decision = build_mobile_orb_policy_decision("Service descriptor binding accepted.")

    assert decision["outcome"] == "permit"
    assert decision["required_capabilities"] == []
    assert decision["granted_capabilities"] == []
    assert decision["decision_cid"].startswith("sha256:mobile-orb-policy-decision:")


def test_build_mobile_orb_bind_service_artifacts_include_orb_binding_metadata() -> None:
    request = MetaGlassesMobileOrbBindServiceRequest(
        edge_session_id="sha256:edge-session",
        service_interface_cid="sha256:task-service",
        service_descriptor={
            "name": "task_status_service",
            "namespace": "handsfree.services.tasks",
            "methods": [{"name": "get_task_status"}],
        },
        operation="get_task_status",
        transport_preference="mcp-server",
        user_intent="show task status",
    )

    binding_handle, policy_decision, binding_record = build_mobile_orb_bind_service_artifacts(
        request=request,
        bound_at="2026-05-23T00:00:00Z",
    )

    assert binding_handle.startswith("sha256:mobile-orb-binding:")
    assert policy_decision["decision_cid"].startswith("sha256:mobile-orb-policy-decision:")
    assert binding_record["orb_binding"]["handle"] == binding_handle
    assert binding_record["orb_binding"]["interface_cid"] == "sha256:task-service"
    assert binding_record["orb_binding"]["service_id"] == "task_status_service"
    assert binding_record["orb_binding"]["operation"] == "get_task_status"
    assert binding_record["orb_binding"]["transport"] == "mcp-server"
    assert binding_record["orb_binding"]["transport_binding"]["transport"] == "mcp-server"
    assert binding_record["orb_binding"]["transport_binding"]["operation"] == "get_task_status"
    metadata = binding_record["orb_binding"]["transport_binding"]["metadata"]
    assert metadata["descriptor_kind"] == "mcp-idl"
    assert metadata["interface_descriptor"] == {
        "name": "task_status_service",
        "namespace": "handsfree.services.tasks",
        "version": "0.1.0",
        "methods": [{"name": "get_task_status"}],
        "errors": [],
        "requires": [],
        "compatibility": {},
    }


def test_build_mobile_orb_bind_service_artifacts_normalize_descriptor_cid() -> None:
    request_a = MetaGlassesMobileOrbBindServiceRequest(
        edge_session_id="sha256:edge-session",
        service_interface_cid="sha256:task-service",
        service_descriptor={
            "namespace": "handsfree.services.tasks",
            "methods": [{"name": "get_task_status", "outputSchema": {"type": "object"}}],
            "name": "task_status_service",
        },
        transport_preference="mcp-server",
    )
    request_b = MetaGlassesMobileOrbBindServiceRequest(
        edge_session_id="sha256:edge-session",
        service_interface_cid="sha256:task-service",
        service_descriptor={
            "name": "task_status_service",
            "methods": [{"outputSchema": {"type": "object"}, "name": "get_task_status"}],
            "namespace": "handsfree.services.tasks",
        },
        transport_preference="mcp-server",
    )

    _, _, binding_record_a = build_mobile_orb_bind_service_artifacts(
        request=request_a,
        bound_at="2026-05-23T00:00:00Z",
    )
    _, _, binding_record_b = build_mobile_orb_bind_service_artifacts(
        request=request_b,
        bound_at="2026-05-23T00:00:00Z",
    )

    assert (
        binding_record_a["orb_binding"]["descriptor_cid"]
        == binding_record_b["orb_binding"]["descriptor_cid"]
    )


def test_build_mobile_orb_bind_service_artifacts_preserve_descriptor_routing_metadata() -> None:
    request = MetaGlassesMobileOrbBindServiceRequest(
        edge_session_id="sha256:edge-session",
        service_interface_cid="sha256:task-service",
        service_descriptor={
            "name": "task_status_service",
            "namespace": "handsfree.services.tasks",
            "methods": [{"name": "pause_task"}],
            "metadata": {
                "mcp_server_family": "ipfs_datasets",
                "operation_tool_name": "tools_dispatch",
                "provider_name": "ipfs_datasets_mcp",
                "ignored": "not exposed",
            },
        },
        operation="pause_task",
        transport_preference="mcp-server",
    )

    _, _, binding_record = build_mobile_orb_bind_service_artifacts(
        request=request,
        bound_at="2026-05-23T00:00:00Z",
    )

    metadata = binding_record["orb_binding"]["transport_binding"]["metadata"]
    assert metadata["server_family"] == "ipfs_datasets"
    assert metadata["tool_name"] == "tools_dispatch"
    assert metadata["provider_name"] == "ipfs_datasets_mcp"
    assert "ignored" not in metadata
    assert metadata["interface_descriptor"]["metadata"] == {
        "provider_name": "ipfs_datasets_mcp",
        "server_family": "ipfs_datasets",
        "tool_name": "tools_dispatch",
    }


def test_build_mobile_orb_register_artifacts_preserve_interface_cids() -> None:
    request = MetaGlassesMobileOrbRegisterRequest(
        edge_id="edge-123",
        platform="ios",
        dat_capabilities={"display": True, "audio": True},
        local_interface_cids=["sha256:mobile", "sha256:display"],
        transport_preferences=["local", "mcp-server"],
    )

    edge_session_id, policy_cid, edge_session = build_mobile_orb_register_artifacts(
        request=request,
        registered_at="2026-05-23T00:00:00Z",
    )

    assert edge_session_id.startswith("sha256:mobile-orb-edge:")
    assert policy_cid.startswith("sha256:mobile-orb-policy:")
    assert edge_session["local_interface_cids"] == ["sha256:mobile", "sha256:display"]
    assert edge_session["policy_cid"] == policy_cid
