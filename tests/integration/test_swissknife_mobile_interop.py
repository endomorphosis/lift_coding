"""Integration proof for the Swissknife/mobile ORB control-surface contract."""

from __future__ import annotations

import json
from pathlib import Path

from jsonschema import Draft202012Validator


REPO_ROOT = Path(__file__).resolve().parents[2]
PACKET_GOALS = [
    "VAIOS-G700",
    "VAIOS-G701",
    "VAIOS-G702",
    "VAIOS-G703",
    "VAIOS-G704",
    "VAIOS-G705",
    "VAIOS-G706",
]
SCANNER_IMPORT_ROOT_EVIDENCE = {
    "Bio",
    "PIL",
    "__future__",
    "argparse",
    "asyncio",
    "base64",
    "collections",
    "concurrent",
    "contextlib",
    "cross",
    "cross_browser_model_sharding",
    "dataclasses",
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
DISPLAY_WIDGET_ACTION_IDS = {
    "mobile_render_display_widget",
    "mobile_update_display_widget",
    "mobile_clear_display_widget",
    "mobile_focus_display_widget",
    "mobile_activate_display_widget_action",
    "mobile_reset_display_widget_session",
    "mobile_play_display_widget_video",
    "mobile_subscribe_display_widget_updates",
}


def read(path: str) -> str:
    return (REPO_ROOT / path).read_text(encoding="utf-8")


def load_json(path: str) -> dict[str, object]:
    return json.loads(read(path))


def logic_binding(binding_id: str, method_refs: list[str]) -> dict[str, object]:
    return {
        "binding_id": binding_id,
        "policy_bundle_ref": {
            "policy_id": "policy:swissknife-mobile:orb-control",
            "policy_cid": "sha256:policy-swissknife-mobile",
            "version": "0.1.0",
            "scope": "descriptor",
            "source": "descriptor",
        },
        "compiled_policy_cid": "sha256:compiled-swissknife-mobile-policy",
        "ir_version": "0.1.0",
        "frame_fact_kinds": ["actor", "surface", "event", "method", "target", "context", "device"],
        "surface_refs": ["mobile", "native_display", "display_webapp", "agent"],
        "method_refs": method_refs,
        "norm_refs": [f"{binding_id}.allow_authenticated_mobile_orb"],
        "interaction_envelope_schema_ref": "interaction_envelope",
        "policy_decision_schema_ref": "policy_decision",
        "mediation_receipt_schema_ref": "mediation_receipt",
        "mediation_required": True,
    }


def sample_control_surface_contract() -> dict[str, object]:
    methods = ["register_edge_capabilities", "invoke_service", "render_widget"]
    binding = logic_binding("swissknife.mobile.control_surface_contract.default", methods)
    return {
        "control_surface_contract": {
            "version": "0.1.0",
            "control_surfaces": [
                {
                    "id": "mobile",
                    "kind": "edge_client",
                    "event_types": ["session_state", "display_action", "permission_state"],
                    "intent_resolver": "mobile_orb_bridge",
                    "confidence_policy": {"min_confidence": 0.8, "clarify_below": 0.7},
                    "logic_bindings": [binding],
                }
            ],
            "intent_bindings": [
                {
                    "intent": "display_widget.render",
                    "method": "render_widget",
                    "target_ref": "meta_wearables_dat.display_widget",
                    "allowed_surfaces": [
                        "mobile",
                        "native_display",
                        "display_webapp",
                        "mobile_card",
                        "notification",
                        "audio_summary",
                    ],
                    "required_context_facts": ["agent_identity", "arguments_hash"],
                    "logic_bindings": [binding],
                }
            ],
            "policy_hooks": {
                "compile_api": "swissknife.control_surface_policy.compile_control_surface_policy_rule",
                "evaluate_api": "swissknife.control_surface_mediator.evaluate_control_surface_interaction",
                "decision_receipt": True,
                "compiled_artifact_types": [
                    "frame_logic",
                    "event_calculus",
                    "deontic_policy",
                    "ucan",
                    "explanation",
                    "source_text",
                ],
            },
            "context_schema": {
                "state_frames": ["mobile_orb_edge_session", "display_widget_active"],
                "time_context": True,
                "location_context": True,
                "device_context": True,
                "agent_identity": True,
            },
            "conflict_resolution": {
                "default": "deny_over_permit",
                "requires_explanation": True,
                "requires_user_confirmation_for": ["destructive", "communication.send"],
            },
            "logic_bindings": [binding],
            "mediation_receipts": {
                "decision_schema_ref": "policy_decision",
                "receipt_schema_ref": "mediation_receipt",
                "emit_for_outcomes": ["allow", "deny", "require_confirmation", "fallback_surface"],
                "store": "audit_log",
            },
            "interop_targets": [
                {
                    "target_id": "interface contract swissknife mobile",
                    "submodule": "mobile",
                    "objective_goal_id": "VAIOS-G700",
                    "objective_packet_goals": PACKET_GOALS,
                    "descriptor_refs": [
                        "mobile/src/orb/metaGlassesOrbDescriptors.js",
                        "mobile/src/utils/metaWearablesDatDisplayWidgetContract.js",
                    ],
                    "contract_refs": {
                        "control_surface_contract_schema_ref": "control_surface_contract",
                        "interaction_envelope_schema_ref": "interaction_envelope",
                        "policy_decision_schema_ref": "policy_decision",
                        "mediation_receipt_schema_ref": "mediation_receipt",
                        "mcp_plus_plus_compatibility_receipt_schema_ref": (
                            "mcp_plus_plus_compatibility_receipt"
                        ),
                    },
                    "allowed_surfaces": [
                        "mobile",
                        "native_display",
                        "display_webapp",
                        "mobile_card",
                        "notification",
                        "audio_summary",
                        "agent",
                    ],
                    "runtime_handoff": {
                        "agent_identity": True,
                        "arguments_hash": True,
                        "receipt_chain": [
                            "interaction_envelope",
                            "policy_decision",
                            "mediation_receipt",
                            "mcp_plus_plus_compatibility_receipt",
                        ],
                    },
                }
            ],
        }
    }


def sample_interaction_envelope() -> dict[str, object]:
    return {
        "interaction_id": "mobile-display-widget:corr-vai-661",
        "surface": "mobile",
        "surface_event": "mobile_render_display_widget",
        "raw_payload": {"widget_id": "handsfree.task-progress-widget"},
        "normalized_intent": {
            "intent": "display_widget.render",
            "method": "render_widget",
            "target_ref": "meta_wearables_dat.display_widget",
            "arguments": {"widget_id": "handsfree.task-progress-widget", "state": {"progress": 0.5}},
            "arguments_hash": "sha256:mobile-display-widget-arguments",
            "allowed_surfaces": [
                "mobile",
                "native_display",
                "display_webapp",
                "mobile_card",
                "notification",
                "audio_summary",
            ],
            "confidence": 1,
        },
        "actor": {
            "type": "agent",
            "id": "mobile:operator",
            "delegation_chain": ["did:key:operator", "did:key:swissknife-mobile-orb"],
            "agent_identity": {
                "kind": "agent",
                "id": "swissknife.mobile_orb",
                "platform": "mobile",
                "edge_session_id": "edge-session-vai-661",
                "allowed_surfaces": ["mobile", "native_display", "display_webapp"],
            },
        },
        "context": {
            "local_time": "2026-07-08T00:00:00.000Z",
            "state_frames": ["mobile_orb_edge_session", "display_widget_active"],
            "device_mode": "handsfree",
            "platform": "mobile",
            "location_context": {"source": "phone_gps.context"},
            "device_context": {"device_id": "meta-glasses-device-vai-661"},
        },
        "control_surface_contract_ref": "control_surface_contract:swissknife-mobile-display-widget",
        "policy_bundle_ref": {
            "policy_id": "policy:swissknife-mobile:orb-control",
            "policy_cid": "sha256:policy-swissknife-mobile",
            "version": "0.1.0",
            "scope": "descriptor",
            "source": "descriptor",
        },
        "compiled_policy_cid": "sha256:compiled-swissknife-mobile-policy",
        "logic_bindings": [
            {
                "binding_id": "swissknife.mobile.control_surface_contract.default",
                "policy_bundle_ref": {
                    "policy_id": "policy:swissknife-mobile:orb-control",
                    "policy_cid": "sha256:policy-swissknife-mobile",
                    "version": "0.1.0",
                    "scope": "descriptor",
                    "source": "descriptor",
                },
                "compiled_policy_cid": "sha256:compiled-swissknife-mobile-policy",
                "surface_ref": "mobile",
                "method_ref": "render_widget",
                "norm_refs": ["swissknife.mobile.render_widget.allow_authenticated_mobile_orb"],
            }
        ],
    }


def assert_valid(schema_path: str, payload: dict[str, object]) -> None:
    validator = Draft202012Validator(load_json(schema_path))
    errors = sorted(validator.iter_errors(payload), key=lambda error: list(error.path))
    assert errors == [], "\n".join(error.message for error in errors)


def test_swissknife_mobile_contract_and_envelope_validate_against_schemas() -> None:
    assert_valid(
        "swissknife/contracts/control_surface_contract.schema.json",
        sample_control_surface_contract(),
    )
    assert_valid(
        "swissknife/contracts/interaction_envelope.schema.json",
        sample_interaction_envelope(),
    )


def test_mobile_orb_descriptors_publish_swissknife_interop_metadata() -> None:
    source = read("mobile/src/orb/metaGlassesOrbDescriptors.js")

    assert "SWISSKNIFE_MOBILE_INTEROP_CONTRACT" in source
    assert "interface contract swissknife mobile" in source
    assert "swissknife/contracts/control_surface_contract.schema.json" in source
    assert "swissknife/contracts/interaction_envelope.schema.json" in source
    assert "agent_identity" in source
    assert "arguments_hash" in source
    assert "allowed_surfaces" in source
    assert "swissknifeMobileInteropDescriptorRef" in source
    for operation in MOBILE_ORB_OPERATIONS:
        assert f"'{operation}'" in source
    for goal in PACKET_GOALS:
        assert f"'{goal}'" in source


def test_meta_wearables_display_widget_actions_have_dat_orb_handoff() -> None:
    source = read("mobile/src/utils/metaWearablesDatDisplayWidgetContract.js")

    assert "SWISSKNIFE_DISPLAY_WIDGET_HANDOFF_CONTRACT" in source
    assert "buildSwissknifeDisplayWidgetHandoff" in source
    assert "displayWidgetActionContractRef" in source
    assert "interaction_envelope.actor.agent_identity" in source
    assert "interaction_envelope.normalized_intent.arguments_hash" in source
    for action_id in DISPLAY_WIDGET_ACTION_IDS:
        assert action_id in source
    for token in ["renderDisplayWidget", "updateDisplayWidget", "playDisplayWidgetVideo"]:
        assert token in source


def test_objective_heap_docs_and_discovery_record_validation_repair() -> None:
    heap = read("implementation_plan/docs/23-virtual-ai-os-objective-goal-heap.md")
    docs = read("docs/integration/swissknife-mobile.md")
    discovery = read("data/virtual_ai_os/discovery/2026-07-08-vai-661-objective-validation-repair.md")

    for text in (heap, docs, discovery):
        assert "VAIOS-G700" in text
        assert "objective validation repair" in text
        assert "tests/integration/test_swissknife_mobile_interop.py" in text
        assert "interface contract swissknife mobile" in text
        assert "control_surface_contract" in text
        assert "interaction_envelope" in text
    for goal in PACKET_GOALS:
        assert goal in heap
        assert goal in discovery
    for scanner_term in SCANNER_IMPORT_ROOT_EVIDENCE:
        assert scanner_term in heap
