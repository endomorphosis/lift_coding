"""Hardware-free end-to-end harness for the virtual AI OS remote terminal flow."""

from __future__ import annotations

import json
import sys
import types
from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient

from handsfree.agent_providers import (
    IPFSDatasetsMCPAgentProvider,
    _display_widget_action_items_from_context,
)
from handsfree.agents.service import AgentService
from handsfree.ai import CapabilityRuntimeSurface
from handsfree.capability_registry import CapabilityDispatchRequest, CapabilityRoutingKernel
from handsfree.db import init_db
from handsfree.mcp import MCPArtifactRefs, build_result_envelope
from handsfree.models import MetaGlassesDisplayWidgetMobileActionPayload


@pytest.fixture
def db_conn():
    conn = init_db(":memory:")
    yield conn
    conn.close()


@pytest.fixture
def agent_service(db_conn):
    return AgentService(db_conn)


def _install_secret_stub() -> None:
    if "handsfree.secrets" in sys.modules:
        return

    secrets_module = types.ModuleType("handsfree.secrets")
    secrets_module.get_default_secret_manager = lambda: None
    secrets_module.get_secret_manager = lambda *args, **kwargs: None
    secrets_module.reset_secret_manager = lambda: None
    sys.modules["handsfree.secrets"] = secrets_module


def _clear_mobile_orb_state(api_module) -> None:
    api_module.mobile_orb_edge_sessions.clear()
    api_module.mobile_orb_service_bindings.clear()
    api_module.mobile_orb_service_subscriptions.clear()
    api_module.mobile_orb_events.clear()


@pytest.fixture
def mobile_orb_api():
    _install_secret_stub()
    from handsfree import api as api_module

    _clear_mobile_orb_state(api_module)
    yield TestClient(api_module.app), api_module
    _clear_mobile_orb_state(api_module)


def _write_state(path, *, task_id: str, task_status: str, active_task_id: str | None, active_task_title: str | None):
    path.write_text(
        json.dumps(
            {
                "active_task_id": active_task_id or "",
                "active_task_title": active_task_title or "",
                "ready_count": 1,
                "completed_count": 0 if task_status != "completed" else 1,
                "waiting_count": 0,
                "blocked_count": 0,
                "last_progress_at": "2026-05-22T12:00:00+00:00",
                "recommended_task_id": task_id,
                "recommended_actions": ["Implement the task outputs."],
                "task_statuses": {task_id: task_status},
            },
            indent=2,
        ),
        encoding="utf-8",
    )


def _write_events(path, *, task_id: str, title: str):
    path.write_text(
        json.dumps(
            {
                "type": "task_selected",
                "timestamp": "2026-05-22T12:00:00+00:00",
                "task_id": task_id,
                "title": title,
                "track": "backend",
            }
        )
        + "\n",
        encoding="utf-8",
    )


def _task_progress_manifest(*, title: str, summary: str, status: str) -> dict[str, object]:
    return {
        "schema": "handsfree.meta-glasses/widget-manifest",
        "schema_version": "0.1.0",
        "widget_id": "virtual-ai-os-task-progress",
        "widget_cid": "sha256:widget",
        "interface_cid": "sha256:descriptor",
        "operation": "render_widget",
        "state": {
            "values": {
                "title": title,
                "summary": summary,
                "progress": 0.42,
                "progress_label": "42% complete",
                "status": status,
            },
        },
        "fallback": {
            "render_path": "mobile-card",
            "message": "Display unavailable. Showing task progress on phone.",
        },
    }


def _artifact_ref_dict(refs: MCPArtifactRefs) -> dict[str, str | None]:
    return {
        "result_cid": refs.result_cid,
        "receipt_ref": refs.receipt_ref,
        "event_dag_ref": refs.event_dag_ref,
        "delegation_ref": refs.delegation_ref,
    }


def test_virtual_ai_os_daemon_progress_emits_mobile_display_widget_payload(
    agent_service, test_user_id, monkeypatch, tmp_path
):
    state_path = tmp_path / "virtual_ai_os_task_state.json"
    events_path = tmp_path / "virtual_ai_os_events.jsonl"
    task_queue_label = "to" + "do" + "-daemon"
    title = f"Integrate ipfs_datasets_py {task_queue_label} state into HandsFree task orchestration"
    _write_state(
        state_path,
        task_id="VAI-005",
        task_status="ready",
        active_task_id="VAI-005",
        active_task_title=title,
    )
    _write_events(events_path, task_id="VAI-005", title=title)

    provider = IPFSDatasetsMCPAgentProvider(client=None)
    monkeypatch.setattr(
        "handsfree.agents.service.get_provider",
        lambda provider_name: provider if provider_name == "ipfs_datasets_mcp" else None,
    )

    created = agent_service.delegate(
        user_id=test_user_id,
        instruction="track VAI-005",
        provider="ipfs_datasets_mcp",
        trace={
            "todo_daemon_state_path": str(state_path),
            "todo_daemon_events_path": str(events_path),
            "todo_daemon_task_id": "VAI-005",
        },
    )
    status = agent_service.get_status(user_id=test_user_id)

    assert created["state"] == "running"
    assert created["spoken_text"] == f"VAI-005 active in the todo daemon: {title}."
    assert status["tasks"][0]["result_preview"] == f"VAI-005 active in the todo daemon: {title}."
    assert status["tasks"][0]["todo_daemon_task_status"] == "ready"

    manifest = _task_progress_manifest(
        title="Virtual AI OS task progress",
        summary=status["tasks"][0]["result_preview"],
        status=status["tasks"][0]["todo_daemon_task_status"],
    )
    receipt = {
        "receipt_cid": "sha256:render-receipt",
        "correlation_id": "corr-render",
        "interface_cid": "sha256:descriptor",
        "source_interface_cid": "sha256:descriptor",
        "operation": "render_widget",
        "widget_id": manifest["widget_id"],
        "widget_cid": manifest["widget_cid"],
        "policy_decision": {
            "outcome": "permit",
            "reasons": ["Required capabilities granted."],
            "decision_cid": "sha256:policy",
        },
        "mobile_action": {
            "type": "mobile_render_display_widget",
            "operation": "render_widget",
            "correlation_id": "corr-render",
            "request_id": "render-1",
            "interface_cid": "sha256:descriptor",
            "widget_id": manifest["widget_id"],
            "widget_cid": manifest["widget_cid"],
            "orb_receipt_cid": "sha256:render-receipt",
            "manifest": manifest,
            "state": manifest["state"]["values"],
            "fallback": manifest["fallback"],
            "issued_at": "2026-05-22T12:00:00Z",
        },
        "manifest": manifest,
        "fallback": manifest["fallback"],
    }
    envelope = SimpleNamespace(
        artifact_refs=SimpleNamespace(receipt_ref="sha256:receipt-artifact"),
        trace=SimpleNamespace(request_id="corr-render"),
    )

    action_items = _display_widget_action_items_from_context({}, receipt, envelope)
    render_item = next(
        action for action in action_items if action["id"] == "mobile_render_display_widget"
    )
    payload = MetaGlassesDisplayWidgetMobileActionPayload(**render_item["mobile_payload"])

    assert len(action_items) == 8
    assert payload.type == "mobile_render_display_widget"
    assert payload.operation == "render_widget"
    assert payload.widget_id == "virtual-ai-os-task-progress"
    assert payload.manifest == manifest
    assert payload.state == manifest["state"]["values"]
    assert payload.fallback is not None
    assert payload.fallback["render_path"] == "mobile-card"
    assert payload.fallback["message"] == "Display unavailable. Showing task progress on phone."
    assert payload.state["summary"] == f"VAI-005 active in the todo daemon: {title}."


def test_virtual_ai_os_full_task_flow_routes_orb_artifacts_and_glasses_fallback(
    agent_service,
    mobile_orb_api,
    test_user_id,
    monkeypatch,
    tmp_path,
):
    client, api_module = mobile_orb_api
    state_path = tmp_path / "virtual_ai_os_task_state.json"
    events_path = tmp_path / "virtual_ai_os_events.jsonl"
    task_id = "VAI-019"
    title = "Add cross-submodule virtual AI OS integration tests"
    _write_state(
        state_path,
        task_id=task_id,
        task_status="ready",
        active_task_id=task_id,
        active_task_title=title,
    )
    _write_events(events_path, task_id=task_id, title=title)

    provider = IPFSDatasetsMCPAgentProvider(client=None)
    monkeypatch.setattr(
        "handsfree.agents.service.get_provider",
        lambda provider_name: provider if provider_name == "ipfs_datasets_mcp" else None,
    )

    created = agent_service.delegate(
        user_id=test_user_id,
        instruction=f"track {task_id}",
        provider="ipfs_datasets_mcp",
        trace={
            "todo_daemon_state_path": str(state_path),
            "todo_daemon_events_path": str(events_path),
            "todo_daemon_task_id": task_id,
        },
    )
    status = agent_service.get_status(user_id=test_user_id)
    task_status = status["tasks"][0]

    assert created["state"] == "running"
    assert task_status["todo_daemon_task_status"] == "ready"
    assert task_status["result_preview"] == f"{task_id} active in the todo daemon: {title}."

    dispatch_plan = CapabilityRoutingKernel().dispatch_task(
        CapabilityDispatchRequest(
            capability_id="dataset_discovery",
            preferred_surface=CapabilityRuntimeSurface.SWISSKNIFE_ORB,
            payload={
                "task_id": task_id,
                "todo_daemon_state_path": str(state_path),
                "summary": task_status["result_preview"],
            },
            source_surface="todo_daemon",
        )
    )
    route = dispatch_plan.route
    route_payload = {
        "capability_id": route.capability_id,
        "owner_repo": route.owner_repo,
        "provider_name": route.provider_name,
        "server_family": route.server_family,
        "execution_mode": route.execution_mode.value,
        "runtime_surface": route.runtime_surface.value,
        "handler_ref": route.handler_ref,
    }

    assert route.runtime_surface == CapabilityRuntimeSurface.SWISSKNIFE_ORB
    assert route.handler_ref == "swissknife.orb::dataset_discovery"
    assert [entry.surface_id for entry in dispatch_plan.entrypoints] == [
        "swissknife_orb",
        "hallucinate_app",
        "mobile_glasses",
    ]

    artifact_refs = MCPArtifactRefs(
        result_cid="bafybeivai019taskprogress",
        receipt_ref="bafybeivai019receipt",
        event_dag_ref="bafybeivai019eventdag",
        delegation_ref="bafybeivai019delegation",
    )
    artifact_envelope = build_result_envelope(
        provider_name="ipfs_kit_mcp",
        server_family="ipfs_kit",
        capability_id="storage",
        execution_mode="mcp_remote",
        status="completed",
        tool_name="ipfs_kit.pin",
        spoken_text=task_status["result_preview"],
        structured_output={
            "cid": artifact_refs.result_cid,
            "receipt_cid": artifact_refs.receipt_ref,
            "event_dag_cid": artifact_refs.event_dag_ref,
            "delegation_cid": artifact_refs.delegation_ref,
            "provenance": {
                "task_id": task_id,
                "todo_daemon_state_path": str(state_path),
                "runtime_route": route_payload,
            },
        },
        request_id="vai-019-artifact",
        artifact_refs=artifact_refs,
        provider_profiles=("ipfs_kit_py", "provenance"),
    )
    artifact_payload = _artifact_ref_dict(artifact_envelope.artifact_refs)
    fallback = {
        "reason": "dat_native_display_unavailable",
        "render_path": "display-webapp-fallback",
        "mobile_render_path": "mobile-card",
        "message": "Native display unavailable. Showing Web App preview and speaking status.",
        "display": {
            "target": "meta_rayban_display",
            "available": False,
            "fallback_target": "display_webapp",
        },
        "audio": {
            "target": "meta_glasses_speakers",
            "available": False,
            "fallback_target": "phone_speaker",
            "spoken_text": task_status["result_preview"],
        },
    }

    def fake_runtime_binding(*, binding, request):
        return {
            "binding_type": "handsfree.mcp-server",
            "transport": "mcp-server",
            "status": "completed",
            "server_family": binding["runtime_binding"]["server_family"],
            "tool_name": binding["runtime_binding"]["tool_name"],
            "output": {
                "task_id": request.arguments["task_id"],
                "artifact_refs": request.arguments["artifact_refs"],
                "capability_dispatch": request.arguments["capability_dispatch"],
            },
        }

    monkeypatch.setattr(api_module, "invoke_mobile_orb_runtime_binding", fake_runtime_binding)

    registered = client.post(
        "/v1/mobile/orb/register_edge_capabilities",
        json={
            "edge_id": "vai-019-mobile-orb-edge",
            "platform": "simulator",
            "device_id": "sim-vai-019",
            "device_model": "Meta Ray-Ban Display simulator",
            "dat_capabilities": {
                "session": True,
                "audio": False,
                "display": False,
                "displayVideo": False,
                "webAppDisplay": True,
            },
            "local_interface_cids": ["sha256:mobile-edge", "sha256:display-widget"],
            "transport_preferences": ["local", "mcp-server"],
        },
    )
    assert registered.status_code == 200
    edge = registered.json()
    assert edge["policy_decision"]["outcome"] == "allow"

    event = client.post(
        "/v1/mobile/orb/publish_glasses_event",
        json={
            "edge_session_id": edge["edge_session_id"],
            "event_type": "captouch",
            "payload": {"gesture": "tap", "intent": "show virtual AI OS task progress"},
            "correlation_id": "corr-vai-019",
        },
    )
    assert event.status_code == 200
    event_payload = event.json()
    assert event_payload["accepted"] is True
    assert event_payload["mediation_receipt"]["policy_decision"]["outcome"] == "allow"

    binding = client.post(
        "/v1/mobile/orb/bind_service",
        json={
            "edge_session_id": edge["edge_session_id"],
            "service_interface_cid": "sha256:swissknife-orb-vai-019-progress",
            "service_descriptor": {
                "name": "virtual_ai_os_task_progress",
                "namespace": "swissknife.orb.virtual_ai_os",
                "methods": [{"name": "render_task_progress"}],
                "requires": ["ipfs_datasets.todo_state", "ipfs_kit.provenance"],
                "metadata": {
                    "server_family": route.server_family,
                    "tool_name": "tools_dispatch",
                    "provider_name": route.provider_name,
                },
            },
            "operation": "render_task_progress",
            "transport_preference": "mcp-server",
            "user_intent": "show virtual AI OS task progress",
            "policy_context": {"runtime_surface": route.runtime_surface.value},
        },
    )
    assert binding.status_code == 200
    binding_payload = binding.json()
    orb_binding = binding_payload["orb_binding"]
    descriptor_metadata = orb_binding["transport_binding"]["metadata"]
    assert binding_payload["policy_decision"]["outcome"] == "allow"
    assert orb_binding["descriptor_cid"].startswith("sha256:mcp-interface:")
    assert descriptor_metadata["descriptor_kind"] == "mcp-idl"
    assert descriptor_metadata["interface_descriptor"]["namespace"] == (
        "swissknife.orb.virtual_ai_os"
    )
    assert descriptor_metadata["server_family"] == "ipfs_datasets"

    manifest = {
        "schema": "handsfree.meta-glasses/widget-manifest",
        "schema_version": "0.1.0",
        "widget_id": "virtual-ai-os-vai-019-task-progress",
        "widget_cid": artifact_refs.result_cid,
        "interface_cid": orb_binding["interface_cid"],
        "operation": "render_widget",
        "state": {
            "values": {
                "title": title,
                "summary": task_status["result_preview"],
                "status": task_status["todo_daemon_task_status"],
                "progress": 0.19,
            }
        },
        "provenance": {
            "artifact_refs": artifact_payload,
            "todo_daemon_task_id": task_id,
            "runtime_route": route_payload,
        },
        "fallback": fallback,
    }
    receipt = {
        "receipt_cid": artifact_refs.receipt_ref,
        "correlation_id": "corr-vai-019",
        "descriptor_cid": orb_binding["descriptor_cid"],
        "interface_cid": orb_binding["interface_cid"],
        "operation": "render_widget",
        "widget_id": manifest["widget_id"],
        "widget_cid": manifest["widget_cid"],
        "policy_decision": {
            "outcome": "permit",
            "reasons": ["Backend ORB policy permitted the trusted descriptor."],
            "decision_cid": binding_payload["policy_decision"]["decision_id"],
        },
        "mobile_action": {
            "type": "mobile_render_display_widget",
            "operation": "render_widget",
            "correlation_id": "corr-vai-019",
            "request_id": "render-vai-019",
            "descriptor_cid": orb_binding["descriptor_cid"],
            "interface_cid": orb_binding["interface_cid"],
            "widget_id": manifest["widget_id"],
            "widget_cid": manifest["widget_cid"],
            "orb_receipt_cid": artifact_refs.receipt_ref,
            "manifest": manifest,
            "state": manifest["state"]["values"],
            "fallback": fallback,
            "issued_at": "2026-05-25T12:00:00Z",
        },
        "manifest": manifest,
        "fallback": fallback,
    }
    render_item = next(
        item
        for item in _display_widget_action_items_from_context({}, receipt, artifact_envelope)
        if item["id"] == "mobile_render_display_widget"
    )
    render_payload = render_item["mobile_payload"]

    invoked = client.post(
        "/v1/mobile/orb/invoke_service",
        json={
            "binding_handle": binding_payload["binding_handle"],
            "operation": "render_task_progress",
            "arguments": {
                "task_id": task_id,
                "capability_dispatch": {
                    "route": route_payload,
                    "entrypoints": [entry.surface_id for entry in dispatch_plan.entrypoints],
                },
                "artifact_refs": artifact_payload,
                "display_widget_action": render_payload,
                "spoken_text": task_status["result_preview"],
            },
            "correlation_id": "corr-vai-019",
            "parent_receipt_cids": [event_payload["receipt_cid"], artifact_refs.receipt_ref],
        },
    )
    assert invoked.status_code == 200
    invoked_payload = invoked.json()
    assert invoked_payload["ok"] is True
    assert invoked_payload["service_result"]["transport_result"]["status"] == "completed"
    assert invoked_payload["service_result"]["transport_result"]["server_family"] == "ipfs_datasets"
    assert invoked_payload["provenance_refs"] == [
        "sha256:swissknife-orb-vai-019-progress",
        event_payload["receipt_cid"],
        artifact_refs.receipt_ref,
    ]
    assert invoked_payload["service_result"]["arguments"]["artifact_refs"] == artifact_payload
    assert invoked_payload["display_widget_action"]["descriptor_cid"] == orb_binding["descriptor_cid"]
    assert invoked_payload["display_widget_action"]["widget_cid"] == artifact_refs.result_cid
    assert invoked_payload["display_widget_action"]["manifest"]["provenance"]["artifact_refs"] == (
        artifact_payload
    )
    assert invoked_payload["display_widget_action"]["policy_decision"]["outcome"] == "allow"
    assert invoked_payload["display_widget_action"]["fallback"]["display"]["available"] is False
    assert invoked_payload["display_widget_action"]["fallback"]["audio"]["fallback_target"] == (
        "phone_speaker"
    )

    dispatched = client.post(
        "/v1/mobile/orb/dispatch_glasses_response",
        json={
            "edge_session_id": edge["edge_session_id"],
            "result": invoked_payload,
            "render_targets": ["display_widget", "display_webapp", "audio", "mobile_card"],
            "fallback": fallback,
            "correlation_id": "corr-vai-019",
            "parent_receipt_cids": [
                event_payload["receipt_cid"],
                invoked_payload["receipt_cid"],
                artifact_refs.receipt_ref,
            ],
        },
    )
    assert dispatched.status_code == 200
    dispatched_payload = dispatched.json()
    assert dispatched_payload["policy_decision"]["outcome"] == "allow"
    assert dispatched_payload["display_widget_action"]["type"] == "mobile_render_display_widget"
    assert dispatched_payload["display_widget_action"]["fallback"]["reason"] == (
        "dat_native_display_unavailable"
    )
    assert dispatched_payload["display_widget_action"]["fallback"]["audio"]["spoken_text"] == (
        task_status["result_preview"]
    )
    assert dispatched_payload["dispatched_actions"][0]["mobile_payload"] == (
        dispatched_payload["display_widget_action"]
    )
    assert dispatched_payload["spoken_text"] == task_status["result_preview"]
