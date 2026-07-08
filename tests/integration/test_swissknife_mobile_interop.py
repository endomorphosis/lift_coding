import json
import re
from pathlib import Path

from jsonschema import Draft202012Validator


ROOT = Path(__file__).resolve().parents[2]
CONTROL_SCHEMA_PATH = ROOT / "swissknife/contracts/control_surface_contract.schema.json"
ENVELOPE_SCHEMA_PATH = ROOT / "swissknife/contracts/interaction_envelope.schema.json"
MOBILE_DESCRIPTORS_PATH = ROOT / "mobile/src/orb/metaGlassesOrbDescriptors.js"
DISPLAY_WIDGET_CONTRACT_PATH = (
    ROOT / "mobile/src/utils/metaWearablesDatDisplayWidgetContract.js"
)
MOBILE_BRIDGE_PATH = ROOT / "mobile/src/orb/metaGlassesMobileOrbBridge.js"
DOC_PATH = ROOT / "docs/integration/swissknife-mobile.md"
DISCOVERY_PATH = (
    ROOT
    / "data/virtual_ai_os/discovery/2026-07-08-vai-661-objective-validation-repair.md"
)

INTERFACE_CONTRACT = "interface contract swissknife mobile"
SCHEMA_REFS = {
    "control_surface_contract",
    "interaction_envelope",
    "policy_decision",
    "mediation_receipt",
}
MOBILE_ORB_OPERATIONS = {
    "register_edge_capabilities",
    "publish_glasses_event",
    "bind_service",
    "invoke_service",
    "subscribe_service_updates",
    "dispatch_glasses_response",
    "revoke_binding",
}
DISPLAY_WIDGET_ACTIONS = {
    "mobile_render_display_widget": ("render_widget", "renderDisplayWidget"),
    "mobile_update_display_widget": ("update_widget", "updateDisplayWidget"),
    "mobile_clear_display_widget": ("clear_widget", "clearDisplayWidget"),
    "mobile_focus_display_widget": ("focus_next", "focusDisplayWidget"),
    "mobile_activate_display_widget_action": (
        "activate",
        "activateDisplayWidgetAction",
    ),
    "mobile_reset_display_widget_session": (
        "reset_session",
        "resetDisplayWidgetSession",
    ),
    "mobile_play_display_widget_video": ("play_video", "playDisplayWidgetVideo"),
    "mobile_subscribe_display_widget_updates": (
        "subscribe_updates",
        "subscribeDisplayWidgetUpdates",
    ),
}


def read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def load_schema(path: Path) -> dict:
    return json.loads(read(path))


def policy_ref() -> dict:
    return {
        "policy_id": "policy:swissknife-mobile-remote-client",
        "policy_cid": "local:policy:swissknife-mobile-remote-client",
        "version": "0.1.0",
        "scope": "mobile-remote-client",
        "source": "descriptor",
    }


def logic_binding() -> dict:
    return {
        "binding_id": "swissknife.mobile.display.render_widget",
        "policy_bundle_ref": policy_ref(),
        "compiled_policy_cid": "local:compiled-policy:swissknife-mobile",
        "frame_fact_kinds": ["actor", "surface", "event", "method", "device"],
        "surface_refs": ["mobile.meta_glasses.display"],
        "method_refs": ["render_widget", "dispatch_glasses_response"],
        "norm_refs": ["mobile_remote_client_transport_receipt"],
        "compiled_artifact_refs": [
            {
                "artifact_type": "deontic_policy",
                "cid": "local:artifact:swissknife-mobile-deontic-policy",
                "media_type": "application/json",
                "description": "Swissknife mediated mobile remote-client policy.",
            }
        ],
        "interaction_envelope_schema_ref": "interaction_envelope",
        "policy_decision_schema_ref": "policy_decision",
        "mediation_receipt_schema_ref": "mediation_receipt",
        "mediation_required": True,
    }


def control_surface_contract_payload() -> dict:
    binding = logic_binding()
    return {
        "control_surface_contract": {
            "version": "0.1.0",
            "control_surfaces": [
                {
                    "id": "mobile.meta_glasses.display",
                    "kind": "remote_client",
                    "event_types": ["display_action", "captouch", "diagnostic"],
                    "intent_resolver": "swissknife.mobile_orb.intent_resolver",
                    "confidence_policy": {
                        "min_confidence": 0.6,
                        "clarify_below": 0.8,
                    },
                    "logic_bindings": [binding],
                }
            ],
            "intent_bindings": [
                {
                    "intent": "render task progress on mobile glasses",
                    "method": "render_widget",
                    "target_ref": "mobile.display_widget_bridge",
                    "allowed_surfaces": ["mobile.meta_glasses.display"],
                    "required_context_facts": ["agent_identity", "device_context"],
                    "logic_bindings": [binding],
                }
            ],
            "policy_hooks": {
                "compile_api": "swissknife.control_surface.compile",
                "evaluate_api": "swissknife.control_surface.evaluate",
                "decision_receipt": True,
                "compiled_artifact_types": [
                    "frame_logic",
                    "event_calculus",
                    "deontic_policy",
                ],
            },
            "context_schema": {
                "state_frames": ["mobile_edge_session", "display_widget_state"],
                "time_context": True,
                "location_context": False,
                "device_context": True,
                "agent_identity": True,
            },
            "conflict_resolution": {
                "default": "deny_over_permit",
                "requires_explanation": True,
                "requires_user_confirmation_for": ["invoke_service"],
            },
            "logic_bindings": [binding],
            "mediation_receipts": {
                "decision_schema_ref": "policy_decision",
                "receipt_schema_ref": "mediation_receipt",
                "emit_for_outcomes": ["allow", "deny", "require_confirmation"],
                "store": "audit_log",
            },
            "interop_profile": {
                "interface_contract": INTERFACE_CONTRACT,
                "source_module": "swissknife",
                "target_module": "mobile",
                "schema_refs": sorted(SCHEMA_REFS),
                "runtime_handoff": {
                    "registration_operation": "register_edge_capabilities",
                    "event_operation": "publish_glasses_event",
                    "invocation_operation": "invoke_service",
                    "response_operation": "dispatch_glasses_response",
                },
            },
        }
    }


def interaction_envelope_payload() -> dict:
    return {
        "interaction_id": "interaction:swissknife-mobile:render-widget",
        "surface": "mobile.meta_glasses.display",
        "surface_event": "display_action",
        "raw_payload": {
            "type": "mobile_render_display_widget",
            "operation": "render_widget",
            "widget_id": "task-progress-active",
        },
        "normalized_intent": {
            "intent": "render task progress on mobile glasses",
            "method": "render_widget",
            "target_ref": "mobile.display_widget_bridge",
            "arguments": {"widget_id": "task-progress-active"},
            "arguments_hash": "sha256:42a85d8a0a5d",
            "confidence": 0.96,
        },
        "actor": {
            "type": "remote_client",
            "id": "mobile:edge:handsfree-mobile-orb-edge",
            "delegation_chain": ["user:operator", "mobile:edge:handsfree-mobile-orb-edge"],
            "agent_identity": "agent:swissknife-control-surface",
        },
        "context": {
            "local_time": "2026-07-08T00:00:00Z",
            "state_frames": ["mobile_edge_session", "display_widget_state"],
            "device_mode": "meta_glasses_remote_display",
            "platform": "mobile",
            "location_context": {},
            "device_context": {"device_model": "Meta Ray-Ban Display"},
            "allowed_surfaces": ["mobile.meta_glasses.display"],
        },
        "control_surface_contract_ref": "control_surface_contract:swissknife:mobile",
        "policy_bundle_ref": policy_ref(),
        "compiled_policy_cid": "local:compiled-policy:swissknife-mobile",
        "logic_bindings": [
            {
                "binding_id": "swissknife.mobile.display.render_widget",
                "policy_bundle_ref": policy_ref(),
                "compiled_policy_cid": "local:compiled-policy:swissknife-mobile",
                "surface_ref": "mobile.meta_glasses.display",
                "method_ref": "render_widget",
                "norm_refs": ["mobile_remote_client_transport_receipt"],
            }
        ],
        "interface_contract": INTERFACE_CONTRACT,
        "source_module": "swissknife",
        "target_module": "mobile",
    }


def test_swissknife_mobile_control_surface_contract_validates_schema():
    schema = load_schema(CONTROL_SCHEMA_PATH)
    Draft202012Validator.check_schema(schema)
    Draft202012Validator(schema).validate(control_surface_contract_payload())


def test_swissknife_mobile_interaction_envelope_validates_schema():
    schema = load_schema(ENVELOPE_SCHEMA_PATH)
    Draft202012Validator.check_schema(schema)
    Draft202012Validator(schema).validate(interaction_envelope_payload())


def test_mobile_descriptors_advertise_swissknife_contract_and_operations():
    source = read(MOBILE_DESCRIPTORS_PATH)

    assert INTERFACE_CONTRACT in source
    for schema_ref in SCHEMA_REFS:
        assert schema_ref in source
    for operation in MOBILE_ORB_OPERATIONS:
        assert operation in source

    assert "SWISSKNIFE_MOBILE_INTEROP_CONTRACT" in source
    assert "interop_contract" in source
    assert "control_surface_schema_refs" in source
    assert "descriptorRef" in source


def test_display_widget_contract_maps_actions_to_orb_and_native_dat_methods():
    source = read(DISPLAY_WIDGET_CONTRACT_PATH)

    assert INTERFACE_CONTRACT in source
    assert "displayWidgetInteropDescriptor" in source
    for action_id, (orb_operation, native_method) in DISPLAY_WIDGET_ACTIONS.items():
        assert action_id in source
        assert orb_operation in source
        assert native_method in source


def test_mobile_bridge_exports_single_diagnostics_contract_and_shared_schemas():
    source = read(MOBILE_BRIDGE_PATH)

    declarations = re.findall(
        r"(?:export\s+)?const\s+MOBILE_ORB_DIAGNOSTICS_CONTRACT\s*=", source
    )
    assert len(declarations) == 1
    assert "export function buildMobileOrbDiagnosticsContract" in source
    for schema_ref in SCHEMA_REFS:
        assert schema_ref in source
    assert "buildMobileOrbControlSurfaceArtifacts" in source
    assert "interaction_envelope" in source
    assert "control_surface_contract_ref" in source


def test_documentation_discovery_and_heap_record_objective_validation_repair():
    doc = read(DOC_PATH)
    discovery = read(DISCOVERY_PATH)
    heap = read(ROOT / "implementation_plan/docs/23-virtual-ai-os-objective-goal-heap.md")

    for content in [doc, discovery, heap]:
        assert "VAIOS-G700" in content
        assert INTERFACE_CONTRACT in content
        assert "tests/integration/test_swissknife_mobile_interop.py" in content
        assert "mobile/src/orb/metaGlassesOrbDescriptors.js" in content
        assert "swissknife/contracts/control_surface_contract.schema.json" in content
