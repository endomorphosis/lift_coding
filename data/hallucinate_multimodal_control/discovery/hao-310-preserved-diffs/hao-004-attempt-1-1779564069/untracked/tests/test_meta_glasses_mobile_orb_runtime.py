"""Focused tests for Meta glasses mobile ORB runtime transport resolution."""

from __future__ import annotations

from handsfree.mcp.models import MCPServerConfig, MCPToolInvocationResult
from handsfree.meta_glasses_mobile_orb_runtime import (
    attach_mobile_orb_runtime_binding,
    invoke_mobile_orb_runtime_binding,
)
from handsfree.models import MetaGlassesMobileOrbInvokeServiceRequest


def test_mcp_server_runtime_binding_resolves_and_invokes(monkeypatch) -> None:
    binding_record = {
        "service_interface_cid": "sha256:task-service",
        "service_descriptor": {
            "name": "task_status_service",
            "namespace": "handsfree.services.ipfs_datasets.tasks",
            "metadata": {
                "server_family": "ipfs_datasets",
                "tool_name": "tools_dispatch",
            },
        },
        "orb_binding": {
            "interface_cid": "sha256:task-service",
            "service_id": "task_status_service",
            "operation": "get_task_status",
            "transport": "mcp-server",
            "transport_binding": {
                "transport": "mcp-server",
                "service_id": "task_status_service",
                "operation": "get_task_status",
                "metadata": {},
            },
        },
        "transport_preference": "mcp-server",
    }

    captured: dict[str, object] = {}

    monkeypatch.setattr(
        "handsfree.meta_glasses_mobile_orb_runtime.get_mcp_server_config",
        lambda server_family: MCPServerConfig(
            server_family=server_family,
            endpoint="http://mcp.example.test",
            tool_name="tools_dispatch",
        ),
    )

    class FakeClient:
        def __init__(self, config: MCPServerConfig) -> None:
            captured["config"] = config

        def invoke_tool(self, tool_name: str, arguments: dict[str, object], correlation_id: str):
            captured["tool_name"] = tool_name
            captured["arguments"] = arguments
            captured["correlation_id"] = correlation_id
            return MCPToolInvocationResult(
                request_id="req-1",
                run_id="run-1",
                status="completed",
                tool_name=tool_name,
                output={"task_status": "running"},
                raw_response={},
                content=[],
            )

    monkeypatch.setattr("handsfree.meta_glasses_mobile_orb_runtime.MCPClient", FakeClient)

    attach_mobile_orb_runtime_binding(binding_record)

    runtime_binding = binding_record["runtime_binding"]
    assert runtime_binding["status"] == "ready"
    assert runtime_binding["server_family"] == "ipfs_datasets"
    assert (
        binding_record["orb_binding"]["transport_binding"]["runtime"]["tool_name"]
        == "tools_dispatch"
    )

    result = invoke_mobile_orb_runtime_binding(
        binding=binding_record,
        request=MetaGlassesMobileOrbInvokeServiceRequest(
            binding_handle="binding-1",
            operation="get_task_status",
            arguments={"task_id": "task-123"},
            correlation_id="corr-1",
        ),
    )

    assert captured["tool_name"] == "tools_dispatch"
    assert captured["arguments"] == {
        "task_id": "task-123",
        "operation": "get_task_status",
        "service_id": "task_status_service",
        "interface_cid": "sha256:task-service",
    }
    assert captured["correlation_id"] == "corr-1"
    assert result["status"] == "completed"
    assert result["output"] == {"task_status": "running"}


def test_mcp_server_runtime_binding_resolves_from_orb_transport_metadata(monkeypatch) -> None:
    binding_record = {
        "service_interface_cid": "sha256:task-service",
        "service_descriptor": {
            "name": "task_status_service",
            "namespace": "handsfree.services.tasks",
        },
        "orb_binding": {
            "interface_cid": "sha256:task-service",
            "service_id": "task_status_service",
            "operation": "get_task_status",
            "transport": "mcp-server",
            "transport_binding": {
                "transport": "mcp-server",
                "service_id": "task_status_service",
                "operation": "get_task_status",
                "metadata": {
                    "server_family": "ipfs_accelerate",
                    "tool_name": "tools_dispatch",
                },
            },
        },
        "transport_preference": "mcp-server",
    }

    monkeypatch.setattr(
        "handsfree.meta_glasses_mobile_orb_runtime.get_mcp_server_config",
        lambda server_family: MCPServerConfig(
            server_family=server_family,
            endpoint="http://mcp.example.test",
            tool_name="fallback_tool",
        ),
    )

    attach_mobile_orb_runtime_binding(binding_record)

    runtime_binding = binding_record["runtime_binding"]
    assert runtime_binding["status"] == "ready"
    assert runtime_binding["server_family"] == "ipfs_accelerate"
    assert runtime_binding["tool_name"] == "tools_dispatch"
    assert runtime_binding["resolution_source"] == "descriptor"
