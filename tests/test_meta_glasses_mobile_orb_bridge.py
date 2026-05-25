"""Mobile ORB bridge backend contract tests."""

# ruff: noqa: I001

import json
import sys
import types
from pathlib import Path

from fastapi.testclient import TestClient

if "handsfree.secrets" not in sys.modules:
    secrets_module = types.ModuleType("handsfree.secrets")
    secrets_module.get_default_secret_manager = lambda: None
    secrets_module.get_secret_manager = lambda *args, **kwargs: None
    secrets_module.reset_secret_manager = lambda: None
    sys.modules["handsfree.secrets"] = secrets_module

from handsfree.api import app  # noqa: E402


client = TestClient(app)


def _register_edge() -> dict:
    response = client.post(
        "/v1/mobile/orb/register_edge_capabilities",
        json={
            "edge_id": "handsfree-mobile-orb-edge",
            "platform": "ios",
            "device_id": "AA:BB",
            "device_model": "Meta Ray-Ban Display",
            "dat_capabilities": {
                "session": True,
                "audio": True,
                "display": True,
                "displayVideo": True,
                "webAppDisplay": True,
            },
            "local_interface_cids": ["sha256:mobile", "sha256:display"],
            "transport_preferences": ["local", "http", "websocket", "mcp-server"],
        },
    )
    assert response.status_code == 200
    return response.json()


def test_mobile_orb_descriptor_artifact_declares_phone_edge_methods() -> None:
    descriptor = json.loads(
        Path("spec/meta_glasses_mobile_orb_bridge_interface.json").read_text(
            encoding="utf-8"
        )
    )

    assert descriptor["name"] == "mobile_orb_bridge"
    assert descriptor["namespace"] == "handsfree.meta_glasses.mobile"
    assert [method["name"] for method in descriptor["methods"]] == [
        "register_edge_capabilities",
        "publish_glasses_event",
        "bind_service",
        "invoke_service",
        "subscribe_service_updates",
        "dispatch_glasses_response",
        "revoke_binding",
    ]


def test_mobile_orb_edge_register_event_bind_invoke_dispatch_revoke_flow() -> None:
    registered = _register_edge()

    assert registered["accepted_interface_cids"] == ["sha256:mobile", "sha256:display"]
    assert registered["policy_cid"] is None
    assert registered["control_surface_contract_ref"].startswith("control_surface_contract:")
    assert registered["interaction_envelope"]["normalized_intent"]["method"] == (
        "register_edge_capabilities"
    )
    assert registered["mediation_receipt"]["policy_decision"]["outcome"] == "allow"

    event = client.post(
        "/v1/mobile/orb/publish_glasses_event",
        json={
            "edge_session_id": registered["edge_session_id"],
            "event_type": "captouch",
            "payload": {"gesture": "tap", "intent": "show task status"},
            "correlation_id": "corr-task-status",
        },
    )
    assert event.status_code == 200
    event_payload = event.json()
    assert event_payload["accepted"] is True
    assert event_payload["interaction_envelope"]["surface"] == "meta_glasses"
    assert event_payload["normalized_intent"]["method"] == "publish_glasses_event"
    assert event_payload["mediation_receipt"]["policy_decision"]["outcome"] == "allow"
    assert "invoke_service" in event_payload["routed_operations"]

    binding = client.post(
        "/v1/mobile/orb/bind_service",
        json={
            "edge_session_id": registered["edge_session_id"],
            "service_interface_cid": "sha256:task-service",
            "service_descriptor": {
                "name": "task_status_service",
                "namespace": "handsfree.services.tasks",
                "methods": [{"name": "get_task_status"}],
            },
            "operation": "get_task_status",
            "transport_preference": "mcp-server",
            "user_intent": "show task status",
        },
    )
    assert binding.status_code == 200
    binding_payload = binding.json()
    assert binding_payload["transport"] == "mcp-server"
    assert binding_payload["policy_decision"]["outcome"] == "allow"
    assert binding_payload["policy_decision"]["decision_id"].startswith(
        "sha256:control-surface-decision:"
    )
    assert binding_payload["interaction_envelope"]["normalized_intent"]["method"] == (
        "bind_service"
    )
    assert binding_payload["mediation_receipt"]["policy_decision"] == (
        binding_payload["policy_decision"]
    )
    assert binding_payload["orb_binding"]["interface_cid"] == "sha256:task-service"
    assert binding_payload["orb_binding"]["service_id"] == "task_status_service"
    assert binding_payload["orb_binding"]["transport_binding"]["metadata"]["descriptor_kind"] == (
        "mcp-idl"
    )

    display_widget_action = {
        "operation": "render_widget",
        "descriptor_cid": "sha256:display",
        "manifest": {
            "widget_id": "task-progress-active",
            "widget_cid": "sha256:widget",
            "state": {"values": {"title": "Sync dataset", "progress": 0.42}},
        },
        "fallback": {
            "render_path": "mobile-card",
            "message": "Display unavailable. Showing task status on phone.",
        },
    }
    invoked = client.post(
        "/v1/mobile/orb/invoke_service",
        json={
            "binding_handle": binding_payload["binding_handle"],
            "operation": "get_task_status",
            "arguments": {
                "task_id": "task-123",
                "display_widget_action": display_widget_action,
                "spoken_text": "Sync dataset is 42 percent complete.",
            },
            "correlation_id": "corr-task-status",
            "parent_receipt_cids": [event_payload["receipt_cid"]],
        },
    )
    assert invoked.status_code == 200
    invoked_payload = invoked.json()
    assert invoked_payload["ok"] is True
    assert invoked_payload["service_result"]["orb_binding"]["interface_cid"] == (
        "sha256:task-service"
    )
    assert invoked_payload["service_result"]["orb_binding"]["transport"] == "mcp-server"
    assert invoked_payload["service_result"]["orb_binding"]["transport_binding"]["operation"] == (
        "get_task_status"
    )
    assert invoked_payload["display_widget_action"]["contract"] == (
        "handsfree.meta-glasses/display-widget-action@0.1.0"
    )
    assert invoked_payload["display_widget_action"]["type"] == "mobile_render_display_widget"
    assert invoked_payload["display_widget_action"]["action"] == "render"
    assert invoked_payload["display_widget_action"]["widget_id"] == "task-progress-active"
    assert invoked_payload["display_widget_action"]["widget_cid"] == "sha256:widget"
    assert invoked_payload["display_widget_action"]["orb_receipt_cid"] == (
        invoked_payload["receipt_cid"]
    )
    assert invoked_payload["policy_decision"]["outcome"] == "allow"
    assert invoked_payload["mediation_receipt"]["policy_decision"] == (
        invoked_payload["policy_decision"]
    )
    assert invoked_payload["display_widget_action"]["policy_decision"]["outcome"] == "allow"
    assert invoked_payload["display_widget_action"]["mediation_receipt"]["policy_decision"] == (
        invoked_payload["display_widget_action"]["policy_decision"]
    )
    assert invoked_payload["display_widget_action"]["correlation_id"] == "corr-task-status"
    assert invoked_payload["follow_up_actions"][0]["id"] == "mobile_render_display_widget"
    assert invoked_payload["follow_up_actions"][0]["params"]["display_widget_action"] == (
        invoked_payload["display_widget_action"]
    )
    assert invoked_payload["spoken_text"] == "Sync dataset is 42 percent complete."
    assert event_payload["receipt_cid"] in invoked_payload["provenance_refs"]

    dispatched = client.post(
        "/v1/mobile/orb/dispatch_glasses_response",
        json={
            "edge_session_id": registered["edge_session_id"],
            "result": invoked_payload,
            "render_targets": ["display_widget", "audio", "mobile_card"],
            "correlation_id": "corr-task-status",
            "parent_receipt_cids": [
                event_payload["receipt_cid"],
                invoked_payload["receipt_cid"],
            ],
        },
    )
    assert dispatched.status_code == 200
    dispatched_payload = dispatched.json()
    assert dispatched_payload["display_widget_action"]["type"] == "mobile_render_display_widget"
    assert dispatched_payload["display_widget_action"]["contract"] == (
        "handsfree.meta-glasses/display-widget-action@0.1.0"
    )
    assert dispatched_payload["dispatched_actions"][0]["id"] == "mobile_render_display_widget"
    assert dispatched_payload["dispatched_actions"][0]["params"]["display_widget_action"] == (
        dispatched_payload["display_widget_action"]
    )
    assert dispatched_payload["dispatched_actions"][0]["mobile_payload"] == (
        dispatched_payload["display_widget_action"]
    )
    assert dispatched_payload["spoken_text"] == "Sync dataset is 42 percent complete."
    assert dispatched_payload["receipt_cid"].startswith("sha256:mobile-orb-receipt:")

    subscription = client.post(
        "/v1/mobile/orb/subscribe_service_updates",
        json={
            "binding_handle": binding_payload["binding_handle"],
            "operation": "get_task_status",
            "stream": "task-status",
            "correlation_id": "corr-task-status",
        },
    )
    assert subscription.status_code == 200
    subscription_payload = subscription.json()
    assert subscription_payload["generation_key"].endswith(":get_task_status:task-status")
    assert subscription_payload["subscription"]["subscription_id"] == (
        subscription_payload["subscription_id"]
    )
    assert subscription_payload["subscription"]["binding_handle"] == (
        binding_payload["binding_handle"]
    )
    assert subscription_payload["subscription"]["service_interface_cid"] == (
        "sha256:task-service"
    )
    assert subscription_payload["subscription"]["status"] == "active"
    assert subscription_payload["subscription"]["orb_binding"]["service_id"] == (
        "task_status_service"
    )

    diagnostics = client.get(
        "/v1/mobile/orb/diagnostics",
        params={"edge_session_id": registered["edge_session_id"]},
    )
    assert diagnostics.status_code == 200
    diagnostics_payload = diagnostics.json()
    assert diagnostics_payload["edge_session_id"] == registered["edge_session_id"]
    assert diagnostics_payload["edge_sessions_count"] == 1
    assert diagnostics_payload["events_count"] == 1
    assert diagnostics_payload["bindings_count"] == 1
    assert diagnostics_payload["subscriptions_count"] == 1
    assert diagnostics_payload["bindings"][0]["binding_handle"] == (
        binding_payload["binding_handle"]
    )
    assert diagnostics_payload["subscriptions"][0]["subscription_id"] == (
        subscription_payload["subscription_id"]
    )

    revoked = client.post(
        "/v1/mobile/orb/revoke_binding",
        json={
            "binding_handle": binding_payload["binding_handle"],
            "reason": "test complete",
            "correlation_id": "corr-task-status",
        },
    )
    assert revoked.status_code == 200
    assert revoked.json()["revoked"] is True


def test_mobile_orb_rejects_missing_edge_session_and_binding() -> None:
    event = client.post(
        "/v1/mobile/orb/publish_glasses_event",
        json={
            "edge_session_id": "missing",
            "event_type": "captouch",
            "payload": {},
            "correlation_id": "corr-missing",
        },
    )
    assert event.status_code == 404
    assert event.json()["error"] == "edge_session_not_found"

    invoked = client.post(
        "/v1/mobile/orb/invoke_service",
        json={
            "binding_handle": "missing",
            "operation": "get_task_status",
            "arguments": {},
            "correlation_id": "corr-missing",
        },
    )
    assert invoked.status_code == 404
    assert invoked.json()["error"] == "binding_not_found"


def test_openapi_exposes_mobile_orb_bridge_contracts() -> None:
    response = client.get("/openapi.json")

    assert response.status_code == 200
    schema = response.json()
    assert "/v1/mobile/orb/register_edge_capabilities" in schema["paths"]
    assert "/v1/mobile/orb/diagnostics" in schema["paths"]
    assert "/v1/mobile/orb/invoke_service" in schema["paths"]
    assert "/v1/mobile/orb/dispatch_glasses_response" in schema["paths"]
    schemas = schema["components"]["schemas"]
    assert "MetaGlassesMobileOrbRegisterRequest" in schemas
    assert "MetaGlassesMobileOrbInvokeServiceResponse" in schemas
