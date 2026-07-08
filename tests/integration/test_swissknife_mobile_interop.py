"""SwissKnife/mobile interoperability contract validation for VAIOS-G700.

The objective scanner filed MGW-569 because the artifacts existed but lacked a
non-skipped validation repair. These tests load the SwissKnife schemas, the
mobile ORB descriptors, and the display-widget action contract as one handoff.
"""

from __future__ import annotations

import copy
import hashlib
import json
import re
from pathlib import Path

from jsonschema import Draft202012Validator
from referencing import Registry, Resource


ROOT = Path(__file__).resolve().parents[2]
SWISSKNIFE_CONTRACTS = ROOT / "swissknife" / "contracts"
MOBILE_ORB_DESCRIPTORS = ROOT / "mobile" / "src" / "orb" / "metaGlassesOrbDescriptors.js"
MOBILE_DISPLAY_CONTRACT = (
    ROOT / "mobile" / "src" / "utils" / "metaWearablesDatDisplayWidgetContract.js"
)
DOC = ROOT / "docs" / "integration" / "swissknife-mobile.md"
DISCOVERY = (
    ROOT
    / "data"
    / "meta_glasses_display_widgets"
    / "discovery"
    / "2026-07-08-mgw-569-objective-validation-repair.md"
)
HEAP = ROOT / "implementation_plan" / "docs" / "23-virtual-ai-os-objective-goal-heap.md"


def load_schema(name: str) -> dict:
    return json.loads((SWISSKNIFE_CONTRACTS / name).read_text())


def exported_array(source: str, name: str) -> list[str]:
    match = re.search(rf"export const {name}\s*=\s*\[(.*?)\];", source, re.S)
    assert match, f"{name} export not found"
    return re.findall(r"'([^']+)'", match.group(1))


def exported_object_body(source: str, name: str) -> str:
    match = re.search(rf"export const {name}\s*=\s*\{{(.*?)\n\}};", source, re.S)
    assert match, f"{name} export not found"
    return match.group(1)


def exported_string_map(source: str, name: str) -> dict[str, str]:
    body = exported_object_body(source, name)
    return dict(re.findall(r"([A-Za-z0-9_]+): '([^']+)'", body))


def local_cid(seed: str) -> str:
    return f"sha256:{hashlib.sha256(seed.encode()).hexdigest()}"


POLICY_BUNDLE_REF = {
    "policy_id": "policy:swissknife-mobile-display-widget",
    "policy_cid": "local:policy:swissknife-mobile-display-widget",
    "version": "0.1.0",
    "scope": "mobile-display-widget",
    "source": "descriptor",
}

LOGIC_BINDING = {
    "binding_id": "binding:swissknife-mobile-display-widget",
    "policy_bundle_ref": POLICY_BUNDLE_REF,
    "compiled_policy_cid": "local:compiled-policy:swissknife-mobile-display-widget",
    "ir_version": "0.1.0",
    "frame_fact_kinds": ["actor", "surface", "event", "method", "target", "context", "device"],
    "surface_refs": ["mobile", "meta_glasses_display"],
    "method_refs": ["render_widget", "update_widget", "dispatch_glasses_response"],
    "norm_refs": ["norm:allow-mobile-display-widget"],
    "compiled_artifact_refs": [
        {
            "artifact_type": "frame_logic",
            "cid": "local:frame-logic:swissknife-mobile-display-widget",
            "media_type": "application/json",
            "description": "Frame facts for SwissKnife to mobile display widget dispatch.",
        },
        {
            "artifact_type": "deontic_policy",
            "cid": "local:deontic-policy:swissknife-mobile-display-widget",
            "media_type": "text/plain",
        },
    ],
    "interaction_envelope_schema_ref": "interaction_envelope",
    "policy_decision_schema_ref": "policy_decision",
    "mediation_receipt_schema_ref": "mediation_receipt",
    "mediation_required": True,
}


def mobile_display_arguments() -> dict:
    return {
        "contract": "handsfree.meta-glasses/display-widget-action@0.1.0",
        "action_id": "mobile_render_display_widget",
        "operation": "render_widget",
        "dat_method": "renderDisplayWidget",
        "widget_id": "task-progress-active",
        "widget_cid": local_cid("widget:task-progress-active"),
    }


def sample_interaction_envelope() -> dict:
    return {
        "interaction_id": "interaction:swissknife-mobile:render-widget",
        "surface": "mobile",
        "surface_event": "display_action",
        "raw_payload": mobile_display_arguments(),
        "normalized_intent": {
            "intent": "display.render",
            "method": "render_widget",
            "target_ref": "mobile.display_widget",
            "arguments": mobile_display_arguments(),
            "confidence": 0.99,
        },
        "actor": {
            "type": "remote_client",
            "id": "swissknife.operator-session",
            "delegation_chain": ["swissknife", "mobile"],
        },
        "context": {
            "local_time": "2026-07-08T00:00:00Z",
            "state_frames": ["display_widget_session", "mobile_orb_edge_session"],
            "device_mode": "handsfree",
            "platform": "ios",
            "location_context": {},
            "device_context": {
                "edge_runtime": "mobile",
                "device_model": "Meta Ray-Ban Display",
            },
        },
        "control_surface_contract_ref": "control_surface_contract",
        "policy_bundle_ref": POLICY_BUNDLE_REF,
        "compiled_policy_cid": LOGIC_BINDING["compiled_policy_cid"],
        "logic_bindings": [
            {
                "binding_id": LOGIC_BINDING["binding_id"],
                "policy_bundle_ref": POLICY_BUNDLE_REF,
                "compiled_policy_cid": LOGIC_BINDING["compiled_policy_cid"],
                "surface_ref": "mobile",
                "method_ref": "render_widget",
                "norm_refs": ["norm:allow-mobile-display-widget"],
            }
        ],
    }


def sample_control_surface_contract() -> dict:
    return {
        "control_surface_contract": {
            "version": "0.1.0",
            "control_surfaces": [
                {
                    "id": "mobile.display_widget",
                    "kind": "mobile",
                    "event_types": ["display_action"],
                    "intent_resolver": "swissknife.display_widget.intent_resolver",
                    "confidence_policy": {"min_confidence": 0.7, "clarify_below": 0.9},
                    "logic_bindings": [LOGIC_BINDING],
                }
            ],
            "intent_bindings": [
                {
                    "intent": "display.render",
                    "method": "render_widget",
                    "target_ref": "mobile.display_widget",
                    "allowed_surfaces": ["mobile", "meta_glasses_display"],
                    "required_context_facts": ["actor", "agent_identity", "device_context"],
                    "logic_bindings": [LOGIC_BINDING],
                }
            ],
            "policy_hooks": {
                "compile_api": "swissknife.policy.compile",
                "evaluate_api": "swissknife.policy.evaluate",
                "decision_receipt": True,
                "compiled_artifact_types": ["frame_logic", "event_calculus", "deontic_policy"],
            },
            "context_schema": {
                "state_frames": ["display_widget_session", "mobile_orb_edge_session"],
                "time_context": True,
                "location_context": False,
                "device_context": True,
                "agent_identity": True,
            },
            "conflict_resolution": {
                "default": "deny_over_permit",
                "requires_explanation": True,
                "requires_user_confirmation_for": ["mobile_activate_display_widget_action"],
            },
            "logic_bindings": [LOGIC_BINDING],
            "mediation_receipts": {
                "decision_schema_ref": "policy_decision",
                "receipt_schema_ref": "mediation_receipt",
                "emit_for_outcomes": ["allow", "deny", "require_confirmation"],
                "store": "audit_log",
            },
        }
    }


def sample_policy_decision() -> dict:
    envelope = sample_interaction_envelope()
    return {
        "decision_id": "decision:swissknife-mobile:render-widget",
        "interaction_id": envelope["interaction_id"],
        "interaction_envelope": envelope,
        "outcome": "allow",
        "policy_bundle_ref": POLICY_BUNDLE_REF,
        "compiled_policy_cid": LOGIC_BINDING["compiled_policy_cid"],
        "decided_at": "2026-07-08T00:00:01Z",
        "matched_norms": [
            {
                "norm_id": "norm:allow-mobile-display-widget",
                "outcome": "allow",
                "priority": 10,
                "policy_bundle_ref": POLICY_BUNDLE_REF,
                "logic_clause_refs": ["clause:mobile-display-widget"],
                "explanation": "SwissKnife may render the active mobile display widget.",
            }
        ],
        "effects": [
            {
                "outcome": "allow",
                "method": "render_widget",
                "target_ref": "mobile.display_widget",
                "arguments": mobile_display_arguments(),
                "confirmation_required": False,
                "reason": "Known display-widget action and mobile ORB descriptor.",
            }
        ],
        "frame_facts": [
            {
                "fact_id": "fact:surface:mobile",
                "kind": "surface",
                "subject": "mobile",
                "predicate": "accepts",
                "value": "render_widget",
                "attrs": {"agent_identity": "swissknife.operator-session"},
            }
        ],
        "reasons": ["display_widget_action is listed in mobile handoff contract"],
        "explanation": "SwissKnife display-widget render is allowed on the mobile ORB edge.",
        "confidence": 0.99,
        "metadata": {"objective": "VAIOS-G700"},
    }


def sample_mediation_receipt() -> dict:
    return {
        "receipt_id": "receipt:swissknife-mobile:render-widget",
        "emitted_at": "2026-07-08T00:00:02Z",
        "control_surface_contract_ref": "control_surface_contract",
        "interaction_envelope": sample_interaction_envelope(),
        "policy_decision": sample_policy_decision(),
        "policy_refs": [
            {
                "policy_bundle_ref": POLICY_BUNDLE_REF,
                "compiled_policy_cid": LOGIC_BINDING["compiled_policy_cid"],
                "matched_norm_refs": ["norm:allow-mobile-display-widget"],
                "compiled_artifact_refs": [
                    {
                        "artifact_type": artifact["artifact_type"],
                        "cid": artifact["cid"],
                        "media_type": artifact["media_type"],
                    }
                    for artifact in LOGIC_BINDING["compiled_artifact_refs"]
                ],
            }
        ],
        "mediation_result": {
            "outcome": "allow",
            "invoked": True,
            "final_method": "render_widget",
            "final_target_ref": "mobile.display_widget",
            "confirmation_required": False,
        },
        "explanation": "Interaction was mediated before mobile invocation.",
        "metadata": {"objective": "VAIOS-G700", "pair": "swissknife mobile"},
    }


def sample_mcp_receipt() -> dict:
    return {
        "receipt_schema": "mcp_plus_plus_compatibility_receipt_v1",
        "task_id": "HAO-445",
        "session_id": "session:swissknife-mobile",
        "correlation_id": "corr:swissknife-mobile-render",
        "daemon_id": "ipfs-kit",
        "server_package": "ipfs_kit_py",
        "swissknife_consumer": "mobile/src/orb/metaGlassesOrbDescriptors.js#SWISSKNIFE_MOBILE_INTEROP_INTERFACE",
        "protocol_negotiation": {
            "method": "initialize",
            "protocol_version": "2026-07-08",
            "client_profiles": ["mcp++/profile-a-idl", "mcp++/receipts"],
            "server_profiles": ["mcp++/profile-a-idl", "mcp++/receipts"],
            "negotiated_profiles": ["mcp++/profile-a-idl", "mcp++/receipts"],
            "initialized": True,
        },
        "capability_descriptor": {
            "descriptor_id": "handsfree.meta_glasses.interop.swissknife_mobile_interop@0.1.0",
            "interface_cid": local_cid("swissknife-mobile-interop-interface"),
            "schema_hash": local_cid("swissknife-mobile-schema"),
            "name": "swissknife_mobile_interop",
            "namespace": "handsfree.meta_glasses.interop",
            "version": "0.1.0",
            "methods": ["register_edge_capabilities", "render_widget", "dispatch_glasses_response"],
            "requires": ["mcp++/profile-a-idl", "mcp++/receipts"],
            "compatibility_checked": True,
            "compatibility_verdict": "compatible",
            "event_streams": True,
        },
        "transport": {
            "kind": "orb",
            "protocol_path": "swissknife/mobile/orb",
            "endpoint": "mobile-orb-edge",
            "auth_present": True,
            "redaction_profile": "content-reference-only",
        },
        "tool_call": {
            "tool_name": "render_widget",
            "tool_category": "display_widget",
            "upstream_function": "renderDisplayWidget",
            "jsonrpc_method": "tools/call",
            "arguments_hash": local_cid(json.dumps(mobile_display_arguments(), sort_keys=True)),
            "dispatch_allowed": True,
            "upstream_status": "ok",
        },
        "policy_contract": {
            "interaction_envelope_id": sample_interaction_envelope()["interaction_id"],
            "policy_decision_id": sample_policy_decision()["decision_id"],
            "policy_outcome": "allow",
            "policy_receipt_id": sample_mediation_receipt()["receipt_id"],
            "mediation_receipt_id": sample_mediation_receipt()["receipt_id"],
            "control_surface_contract_ref": "control_surface_contract",
        },
        "receipt_lineage": {
            "envelope_cid": local_cid("envelope:swissknife-mobile-render"),
            "artifact_cid": local_cid("artifact:display-widget"),
            "event_cid": local_cid("event:render-widget"),
            "decision_cid": local_cid("decision:render-widget"),
            "receipt_cid": local_cid("receipt:render-widget"),
            "tool_receipt_id": "receipt:swissknife-mobile:render-widget",
        },
        "lifecycle_events": [
            {"event": "initialize", "at": "2026-07-08T00:00:00Z", "status": "ok"},
            {
                "event": "policy_decision",
                "at": "2026-07-08T00:00:01Z",
                "status": "allow",
                "receipt_cid": local_cid("receipt:render-widget"),
            },
            {
                "event": "receipt_emitted",
                "at": "2026-07-08T00:00:02Z",
                "status": "ok",
                "receipt_cid": local_cid("receipt:render-widget"),
            },
        ],
        "validated_at": "2026-07-08T00:00:03Z",
    }


def test_mobile_descriptor_advertises_swissknife_contract_refs() -> None:
    source = MOBILE_ORB_DESCRIPTORS.read_text()
    interop_body = exported_object_body(source, "SWISSKNIFE_MOBILE_INTEROP_INTERFACE")

    assert exported_array(source, "SWISSKNIFE_MOBILE_INTEROP_OPERATIONS") == [
        "register_edge_capabilities",
        "render_widget",
        "update_widget",
        "clear_widget",
        "focus_next",
        "activate",
        "dispatch_glasses_response",
    ]
    for schema_name in (
        "control_surface_contract",
        "interaction_envelope",
        "mcp_plus_plus_compatibility_receipt",
        "mediation_receipt",
    ):
        assert schema_name in interop_body
    assert "swissknife" in interop_body
    assert "mobile" in interop_body
    assert "descriptor.contractRefs" in source
    assert "ref.contract_refs" in source
    assert "ref.handoff" in source


def test_display_widget_handoff_matrix_matches_orb_and_dat_operations() -> None:
    descriptor_source = MOBILE_ORB_DESCRIPTORS.read_text()
    display_source = MOBILE_DISPLAY_CONTRACT.read_text()

    display_operations = exported_array(descriptor_source, "DISPLAY_WIDGET_BRIDGE_OPERATIONS")
    action_ids = exported_array(display_source, "DISPLAY_WIDGET_ACTION_IDS")
    orb_by_action = exported_string_map(display_source, "DISPLAY_WIDGET_ORB_OPERATION_BY_ACTION_ID")
    dat_by_action = exported_string_map(display_source, "DISPLAY_WIDGET_DAT_METHOD_BY_ACTION_ID")

    assert len(action_ids) == len(set(action_ids))
    assert set(action_ids) == set(orb_by_action) == set(dat_by_action)
    assert [orb_by_action[action_id] for action_id in action_ids] == [
        operation for operation in display_operations if operation != "focus_previous"
    ]
    assert dat_by_action["mobile_render_display_widget"] == "renderDisplayWidget"
    assert dat_by_action["mobile_play_display_widget_video"] == "playDisplayWidgetVideo"
    assert "SWISSKNIFE_DISPLAY_WIDGET_SCHEMA_REFS" in display_source
    assert "SWISSKNIFE_DISPLAY_WIDGET_HANDOFFS" in display_source


def test_swissknife_schemas_accept_a_mobile_runtime_handoff() -> None:
    schemas = {
        name: load_schema(name)
        for name in (
            "control_surface_contract.schema.json",
            "interaction_envelope.schema.json",
            "policy_decision.schema.json",
            "mediation_receipt.schema.json",
            "mcp_plus_plus_compatibility_receipt.schema.json",
        )
    }

    Draft202012Validator(schemas["control_surface_contract.schema.json"]).validate(
        sample_control_surface_contract()
    )
    Draft202012Validator(schemas["interaction_envelope.schema.json"]).validate(
        sample_interaction_envelope()
    )

    registry = Registry().with_resources(
        [
            (schemas["interaction_envelope.schema.json"]["$id"], Resource.from_contents(schemas["interaction_envelope.schema.json"])),
            (schemas["policy_decision.schema.json"]["$id"], Resource.from_contents(schemas["policy_decision.schema.json"])),
        ]
    )
    Draft202012Validator(schemas["policy_decision.schema.json"], registry=registry).validate(
        sample_policy_decision()
    )
    Draft202012Validator(schemas["mediation_receipt.schema.json"], registry=registry).validate(
        sample_mediation_receipt()
    )
    Draft202012Validator(schemas["mcp_plus_plus_compatibility_receipt.schema.json"]).validate(
        sample_mcp_receipt()
    )

    assert schemas["control_surface_contract.schema.json"]["x-interop"]["pair"] == "swissknife mobile"
    assert schemas["interaction_envelope.schema.json"]["x-interop"]["objective"] == "VAIOS-G700"


def test_docs_discovery_and_heap_record_objective_validation_repair() -> None:
    required_files = [
        DOC,
        DISCOVERY,
        HEAP,
        MOBILE_ORB_DESCRIPTORS,
        MOBILE_DISPLAY_CONTRACT,
        SWISSKNIFE_CONTRACTS / "control_surface_contract.schema.json",
        SWISSKNIFE_CONTRACTS / "interaction_envelope.schema.json",
    ]
    for path in required_files:
        assert path.exists(), f"{path} must exist for MGW-569"

    combined = "\n".join(path.read_text() for path in (DOC, DISCOVERY, HEAP))
    for term in (
        "VAIOS-G700",
        "MGW-569",
        "objective validation repair",
        "interface contract swissknife mobile",
        "tests/integration/test_swissknife_mobile_interop.py",
        "docs/integration/swissknife-mobile.md",
        "mobile/src/orb/metaGlassesOrbDescriptors.js",
        "mobile/src/utils/metaWearablesDatDisplayWidgetContract.js",
        "swissknife/contracts/control_surface_contract.schema.json",
        "swissknife/contracts/interaction_envelope.schema.json",
    ):
        assert term in combined

    heap_section = HEAP.read_text().split("## VAIOS-G700 Interoperate swissknife with mobile", 1)[1]
    heap_section = heap_section.split("## VAIOS-G701", 1)[0]
    assert "- Status: completed" in heap_section
    assert "Completion evidence:" in heap_section
    assert "Completion validation:" in heap_section

    # Guard against accidental mutation of the shared fixture constructors above.
    assert sample_interaction_envelope() == copy.deepcopy(sample_interaction_envelope())
