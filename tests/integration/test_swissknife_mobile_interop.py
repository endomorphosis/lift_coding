"""SwissKnife <-> mobile interop validation for VAIOS-G700 / MGW-569."""

from __future__ import annotations

import ast
import json
import re
import sys
import types
from pathlib import Path

from fastapi.testclient import TestClient
from jsonschema import Draft202012Validator

ROOT = Path(__file__).resolve().parents[2]

if "handsfree.secrets" not in sys.modules:
    secrets_module = types.ModuleType("handsfree.secrets")
    secrets_module.get_default_secret_manager = lambda: None
    secrets_module.get_secret_manager = lambda *args, **kwargs: None
    secrets_module.reset_secret_manager = lambda: None
    sys.modules["handsfree.secrets"] = secrets_module

from handsfree import api as api_module  # noqa: E402


client = TestClient(api_module.app)


def _read_json(relative_path: str) -> dict:
    return json.loads((ROOT / relative_path).read_text(encoding="utf-8"))


def _read_text(relative_path: str) -> str:
    return (ROOT / relative_path).read_text(encoding="utf-8")


def _exported_array(source: str, name: str) -> list[str]:
    match = re.search(rf"export const {name} = (\[[\s\S]*?\])(?: as const)?;", source)
    assert match, f"missing export const {name}"
    return ast.literal_eval(match.group(1))


def _exported_string(source: str, name: str) -> str:
    match = re.search(rf"export const {name}\s*=\s*'([^']+)';", source)
    assert match, f"missing export const {name}"
    return match.group(1)


def _reset_mobile_orb_state() -> None:
    api_module.mobile_orb_edge_sessions.clear()
    api_module.mobile_orb_service_bindings.clear()
    api_module.mobile_orb_service_subscriptions.clear()
    api_module.mobile_orb_events.clear()
    api_module.mobile_orb_receipts.clear()
    api_module.mobile_orb_invocations.clear()
    api_module.mobile_orb_dispatches.clear()
    api_module.mobile_orb_revocations.clear()


def _logic_binding() -> dict:
    policy_bundle_ref = {
        "policy_id": "policy:hallucinate-app:remote-client-transport",
        "policy_cid": "local:hallucinate-app:remote-client-transport",
        "version": "0.1.0",
        "scope": "remote-client-transport",
        "source": "system_default",
    }
    return {
        "binding_id": "hallucinate_app.remote_client.mobile.invoke_service",
        "policy_bundle_ref": policy_bundle_ref,
        "compiled_policy_cid": "local:hallucinate-app:remote-client-transport",
        "frame_fact_kinds": ["actor", "surface", "event", "method", "target", "context"],
        "surface_refs": ["mobile", "meta_glasses", "display_widget"],
        "method_refs": ["invoke_service", "dispatch_glasses_response"],
        "norm_refs": ["remote_client_transport_receipt"],
        "compiled_artifact_refs": [
            {
                "artifact_type": "deontic_policy",
                "cid": "local:hallucinate-app:remote-client-transport",
                "media_type": "application/json",
            }
        ],
        "interaction_envelope_schema_ref": "interaction_envelope",
        "policy_decision_schema_ref": "policy_decision",
        "mediation_receipt_schema_ref": "mediation_receipt",
        "mediation_required": True,
    }


def test_mobile_descriptors_are_importable_contract_artifacts() -> None:
    descriptor_source = _read_text("mobile/src/orb/metaGlassesOrbDescriptors.js")
    display_contract_source = _read_text(
        "mobile/src/utils/metaWearablesDatDisplayWidgetContract.js"
    )
    swissknife_bridge_source = _read_text(
        "swissknife/src/services/glasses/meta-glasses-mobile-orb-bridge.ts"
    )
    swissknife_bridge_test = _read_text(
        "swissknife/test/mcp-plus-plus/meta-glasses-mobile-orb-bridge.test.ts"
    )
    mobile_spec = _read_json("spec/meta_glasses_mobile_orb_bridge_interface.json")
    display_spec = _read_json("spec/meta_glasses_display_widget_orb_interface.json")

    mobile_operations = _exported_array(descriptor_source, "MOBILE_ORB_BRIDGE_OPERATIONS")
    display_operations = _exported_array(descriptor_source, "DISPLAY_WIDGET_BRIDGE_OPERATIONS")
    allowed_surfaces = _exported_array(descriptor_source, "MOBILE_ORB_ALLOWED_SURFACES")

    assert mobile_spec["methods"]
    assert [method["name"] for method in mobile_spec["methods"]] == mobile_operations
    assert [method["name"] for method in display_spec["methods"]] == display_operations
    assert mobile_spec["allowed_surfaces"] == allowed_surfaces
    assert set(mobile_spec["runtime_handoff"].values()).issubset(set(mobile_operations))
    assert mobile_spec["control_surface_contract_ref"] == _exported_string(
        descriptor_source, "MOBILE_ORB_CONTROL_SURFACE_CONTRACT_REF"
    )
    assert mobile_spec["interop_contract"] == _exported_string(
        descriptor_source, "MOBILE_ORB_SWISSKNIFE_INTEROP_CONTRACT"
    )
    assert "swissknifeMobileInteropDescriptorBundle" in descriptor_source
    assert _exported_array(
        swissknife_bridge_source, "META_GLASSES_MOBILE_ORB_OPERATIONS"
    ) == mobile_operations
    for evidence_term in [
        "CONTROL_SURFACE_SCHEMA_REFS",
        "remote_client_policy_contract: false",
        "descriptor_kind: 'mcp-idl'",
        "transport: 'mcp-server'",
        "server_family",
        "tool_name",
        "provider_name",
    ]:
        assert evidence_term in swissknife_bridge_source or evidence_term in swissknife_bridge_test

    display_action_ids = _exported_array(display_contract_source, "DISPLAY_WIDGET_ACTION_IDS")
    for action_id in display_action_ids:
        assert action_id in display_contract_source
    assert "displayWidgetInteropMapping" in display_contract_source
    assert "buildDisplayWidgetActionHandoff" in display_contract_source
    assert "validateDisplayWidgetActionHandoff" in display_contract_source
    assert "DISPLAY_WIDGET_SWISSKNIFE_HANDOFF_CONTRACT" in display_contract_source
    assert "DISPLAY_WIDGET_DAT_METHOD_BY_ACTION_ID" in display_contract_source


def test_swissknife_control_schema_accepts_mobile_remote_client_handoff() -> None:
    control_schema = _read_json("swissknife/contracts/control_surface_contract.schema.json")
    binding = _logic_binding()
    sample = {
        "control_surface_contract": {
            "version": "0.1.0",
            "control_surfaces": [
                {
                    "id": "mobile",
                    "kind": "remote_client",
                    "event_types": ["invoke_service", "dispatch_glasses_response"],
                    "intent_resolver": "handsfree.meta_glasses.mobile.mobile_orb_bridge",
                    "logic_bindings": [binding],
                }
            ],
            "intent_bindings": [
                {
                    "intent": "mobile.invoke_service",
                    "method": "invoke_service",
                    "target_ref": "handsfree.meta_glasses.mobile.mobile_orb_bridge.invoke_service",
                    "allowed_surfaces": ["mobile", "meta_glasses", "display_widget"],
                    "required_context_facts": ["agent_identity", "arguments_hash"],
                    "logic_bindings": [binding],
                }
            ],
            "policy_hooks": {
                "compile_api": "swissknife.control_surface.compile",
                "evaluate_api": "swissknife.control_surface.evaluate",
                "decision_receipt": True,
                "compiled_artifact_types": ["deontic_policy", "frame_logic"],
            },
            "context_schema": {
                "state_frames": ["edge_session", "display_widget"],
                "time_context": True,
                "location_context": True,
                "device_context": True,
                "agent_identity": True,
            },
            "conflict_resolution": {
                "default": "deny_over_permit",
                "requires_explanation": True,
            },
            "logic_bindings": [binding],
            "mediation_receipts": {
                "decision_schema_ref": "policy_decision",
                "receipt_schema_ref": "mediation_receipt",
                "emit_for_outcomes": ["allow", "deny", "require_confirmation"],
                "store": "audit_log",
            },
            "mobile_remote_client_handoff": {
                "contract": "handsfree.meta-glasses/swissknife-mobile-interop@0.1.0",
                "control_surface_contract_ref": "control_surface_contract:hallucinate-app:remote-client",
                "allowed_surfaces": ["mobile", "meta_glasses", "display_widget"],
                "artifact_fields": [
                    "control_surface_contract_ref",
                    "interaction_envelope",
                    "normalized_intent",
                    "policy_decision",
                    "mediation_receipt",
                ],
                "runtime_handoff": {
                    "register": "register_edge_capabilities",
                    "event": "publish_glasses_event",
                    "bind": "bind_service",
                    "invoke": "invoke_service",
                    "subscribe": "subscribe_service_updates",
                    "dispatch": "dispatch_glasses_response",
                    "revoke": "revoke_binding",
                },
                "descriptor_refs": [
                    "mobile/src/orb/metaGlassesOrbDescriptors.js",
                    "mobile/src/utils/metaWearablesDatDisplayWidgetContract.js",
                ],
            },
        }
    }

    Draft202012Validator(control_schema).validate(sample)


def test_mobile_orb_runtime_handoff_emits_interaction_envelope_arguments_hash() -> None:
    _reset_mobile_orb_state()
    try:
        registered = client.post(
            "/v1/mobile/orb/register_edge_capabilities",
            json={
                "edge_id": "swissknife-mobile-interop-edge",
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
                "local_interface_cids": [
                    "handsfree.meta_glasses.mobile.mobile_orb_bridge@0.1.0",
                    "handsfree.meta_glasses.display.display_widget_bridge@0.1.0",
                ],
                "transport_preferences": ["local", "mcp-server"],
            },
        )
        assert registered.status_code == 200
        registered_payload = registered.json()

        binding = client.post(
            "/v1/mobile/orb/bind_service",
            json={
                "edge_session_id": registered_payload["edge_session_id"],
                "service_interface_cid": "sha256:task-service",
                "service_descriptor": {
                    "name": "task_status_service",
                    "namespace": "handsfree.services.tasks",
                    "methods": [{"name": "get_task_status"}],
                    "metadata": {
                        "server_family": "ipfs_datasets",
                        "tool_name": "tools_dispatch",
                        "provider_name": "ipfs_datasets_mcp",
                    },
                },
                "operation": "get_task_status",
                "transport_preference": "mcp-server",
                "user_intent": "show task status on display",
            },
        )
        assert binding.status_code == 200
        binding_payload = binding.json()

        invoked = client.post(
            "/v1/mobile/orb/invoke_service",
            json={
                "binding_handle": binding_payload["binding_handle"],
                "operation": "get_task_status",
                "arguments": {
                    "task_id": "task-123",
                    "display_widget_action": {
                        "operation": "render_widget",
                        "descriptor_cid": "sha256:display",
                        "manifest": {
                            "widget_id": "task-progress-active",
                            "widget_cid": "sha256:widget",
                            "state": {"values": {"title": "Sync dataset", "progress": 0.42}},
                        },
                    },
                    "spoken_text": "Sync dataset is 42 percent complete.",
                },
                "correlation_id": "corr-swissknife-mobile",
                "parent_receipt_cids": [
                    registered_payload["mediation_receipt"]["receipt_id"],
                    binding_payload["mediation_receipt"]["receipt_id"],
                ],
            },
        )
        assert invoked.status_code == 200
        invoked_payload = invoked.json()

        interaction_schema = _read_json("swissknife/contracts/interaction_envelope.schema.json")
        Draft202012Validator(interaction_schema).validate(
            invoked_payload["interaction_envelope"]
        )

        normalized_intent = invoked_payload["interaction_envelope"]["normalized_intent"]
        assert normalized_intent["method"] == "invoke_service"
        assert normalized_intent["arguments"]["operation"] == "get_task_status"
        assert normalized_intent["arguments_hash"].startswith("sha256:arguments:")
        assert invoked_payload["control_surface_contract_ref"] == (
            "control_surface_contract:hallucinate-app:remote-client"
        )
        assert invoked_payload["mediation_receipt"]["policy_decision"]["outcome"] == "allow"
        assert invoked_payload["display_widget_action"]["contract"] == (
            "handsfree.meta-glasses/display-widget-action@0.1.0"
        )
        assert invoked_payload["display_widget_action"]["type"] == (
            "mobile_render_display_widget"
        )
        assert invoked_payload["display_widget_action"]["orb_receipt_cid"] == (
            invoked_payload["receipt_cid"]
        )
        assert invoked_payload["service_result"]["orb_binding"]["transport"] == "mcp-server"
    finally:
        _reset_mobile_orb_state()
