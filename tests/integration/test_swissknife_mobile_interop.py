"""SwissKnife/mobile interoperability contract regression tests for MGW-569."""

from __future__ import annotations

import json
import subprocess
import tempfile
from pathlib import Path

from jsonschema import Draft202012Validator


REPO_ROOT = Path(__file__).resolve().parents[2]
GOAL_PACKET_GOALS = {
    "VAIOS-G700",
    "VAIOS-G701",
    "VAIOS-G702",
    "VAIOS-G703",
    "VAIOS-G704",
    "VAIOS-G705",
    "VAIOS-G706",
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
DISPLAY_WIDGET_OPERATIONS = {
    "render_widget",
    "update_widget",
    "clear_widget",
    "focus_next",
    "focus_previous",
    "activate",
    "reset_session",
    "play_video",
    "subscribe_updates",
}


def read_json(path: str) -> dict:
    return json.loads((REPO_ROOT / path).read_text(encoding="utf-8"))


def load_js_exports(path: str, export_names: list[str]) -> dict:
    script = r"""
const fs = require('fs');
const vm = require('vm');
const path = process.argv[1];
const requested = JSON.parse(process.argv[2]);
let source = fs.readFileSync(path, 'utf8');
const functionExports = [];
source = source.replace(/export const\s+([A-Za-z0-9_]+)\s*=/g, (_, name) => {
  return `const ${name} = exports.${name} =`;
});
source = source.replace(/export function\s+([A-Za-z0-9_]+)\s*\(/g, (_, name) => {
  functionExports.push(name);
  return `function ${name}(`;
});
source = `${source}\n${functionExports.map((name) => `exports.${name} = ${name};`).join('\n')}`;
const context = { exports: {} };
vm.runInNewContext(source, context, { filename: path });
const selected = {};
for (const name of requested) {
  selected[name] = context.exports[name];
}
process.stdout.write(JSON.stringify(selected));
"""
    result = subprocess.run(
        ["node", "-e", script, str(REPO_ROOT / path), json.dumps(export_names)],
        check=True,
        text=True,
        capture_output=True,
    )
    return json.loads(result.stdout)


def assert_module_is_valid_esm(path: str) -> None:
    source = (REPO_ROOT / path).read_text(encoding="utf-8")
    with tempfile.NamedTemporaryFile("w", suffix=".mjs", delete=False) as handle:
        handle.write(source)
        temp_path = handle.name
    try:
        subprocess.run(["node", "--check", temp_path], check=True, capture_output=True, text=True)
    finally:
        Path(temp_path).unlink(missing_ok=True)


def swissknife_mobile_control_surface_payload() -> dict:
    policy_bundle_ref = {
        "policy_id": "policy:swissknife:mobile-interop",
        "policy_cid": "local:swissknife:mobile-interop",
        "version": "0.1.0",
        "scope": "swissknife-mobile-interop",
        "source": "system_default",
    }
    logic_binding = {
        "binding_id": "binding:swissknife-mobile-display-widget",
        "policy_bundle_ref": policy_bundle_ref,
        "compiled_policy_cid": "local:swissknife:mobile-interop",
        "ir_version": "0.1.0",
        "frame_fact_kinds": ["actor", "surface", "event", "method", "context", "device"],
        "surface_refs": ["agent", "remote_client", "mobile"],
        "method_refs": ["dispatch_glasses_response", "render_widget"],
        "norm_refs": ["agent_identity", "allowed_surfaces", "arguments_hash"],
        "compiled_artifact_refs": [
            {
                "artifact_type": "deontic_policy",
                "cid": "local:swissknife:mobile-interop",
                "media_type": "application/json",
                "description": "interface contract swissknife mobile",
            }
        ],
        "interaction_envelope_schema_ref": "interaction_envelope",
        "policy_decision_schema_ref": "policy_decision",
        "mediation_receipt_schema_ref": "mediation_receipt",
        "mediation_required": True,
    }
    return {
        "control_surface_contract": {
            "version": "0.1.0",
            "control_surfaces": [
                {
                    "id": "swissknife.mobile.remote-client",
                    "kind": "remote_client",
                    "event_types": ["dispatch_glasses_response", "display_widget_action"],
                    "intent_resolver": "swissknife.mobile.intent_resolver",
                    "confidence_policy": {"min_confidence": 0.8, "clarify_below": 0.65},
                    "logic_bindings": [logic_binding],
                }
            ],
            "intent_bindings": [
                {
                    "intent": "swissknife.mobile.render_widget",
                    "method": "render_widget",
                    "target_ref": "mobile:display_widget_bridge",
                    "allowed_surfaces": ["agent", "remote_client", "mobile"],
                    "required_context_facts": ["agent_identity", "device_context"],
                    "logic_bindings": [logic_binding],
                }
            ],
            "policy_hooks": {
                "compile_api": "swissknife://control-surface/compile",
                "evaluate_api": "swissknife://control-surface/evaluate",
                "decision_receipt": True,
                "compiled_artifact_types": ["deontic_policy", "explanation"],
            },
            "context_schema": {
                "state_frames": ["mobile_edge_session", "display_widget_session"],
                "time_context": True,
                "location_context": False,
                "device_context": True,
                "agent_identity": True,
            },
            "conflict_resolution": {
                "default": "require_confirmation",
                "requires_explanation": True,
                "requires_user_confirmation_for": ["activate", "revoke_binding"],
            },
            "logic_bindings": [logic_binding],
            "mediation_receipts": {
                "decision_schema_ref": "policy_decision",
                "receipt_schema_ref": "mediation_receipt",
                "emit_for_outcomes": ["allow", "deny", "require_confirmation"],
                "store": "audit_log",
            },
        }
    }


def swissknife_mobile_interaction_envelope() -> dict:
    policy_bundle_ref = {
        "policy_id": "policy:swissknife:mobile-interop",
        "policy_cid": "local:swissknife:mobile-interop",
        "version": "0.1.0",
        "scope": "swissknife-mobile-interop",
        "source": "system_default",
    }
    return {
        "interaction_id": "interaction:swissknife-mobile:render-widget:1",
        "surface": "remote_client",
        "surface_event": "dispatch_glasses_response",
        "raw_payload": {
            "edge_session_id": "local:edge-session:handsfree-mobile-orb-edge",
            "render_targets": ["display_widget", "audio", "mobile_card"],
        },
        "normalized_intent": {
            "intent": "swissknife.mobile.render_widget",
            "method": "render_widget",
            "target_ref": "mobile:display_widget_bridge",
            "arguments": {
                "widget_id": "task-progress-active",
                "operation": "render_widget",
                "arguments_hash": "sha256:swissknife-mobile-render-widget",
            },
            "confidence": 0.96,
        },
        "actor": {
            "type": "agent",
            "id": "swissknife:operator-agent",
            "delegation_chain": ["ucan:swissknife-mobile-interop"],
        },
        "context": {
            "local_time": "2026-07-08T00:00:00Z",
            "state_frames": ["mobile_edge_session", "display_widget_session"],
            "device_mode": "handsfree",
            "platform": "mobile",
            "location_context": {},
            "device_context": {
                "edge_id": "handsfree-mobile-orb-edge",
                "dat_capabilities": {"display": True, "audio": True},
            },
        },
        "control_surface_contract_ref": "swissknife/contracts/control_surface_contract.schema.json",
        "policy_bundle_ref": policy_bundle_ref,
        "compiled_policy_cid": "local:swissknife:mobile-interop",
        "logic_bindings": [
            {
                "binding_id": "binding:swissknife-mobile-display-widget",
                "policy_bundle_ref": policy_bundle_ref,
                "compiled_policy_cid": "local:swissknife:mobile-interop",
                "surface_ref": "remote_client",
                "method_ref": "render_widget",
                "norm_refs": ["agent_identity", "allowed_surfaces", "arguments_hash"],
            }
        ],
    }


def test_mobile_descriptor_exports_swissknife_interop_contract() -> None:
    exports = load_js_exports(
        "mobile/src/orb/metaGlassesOrbDescriptors.js",
        [
            "SWISSKNIFE_MOBILE_INTEROP_INTERFACE",
            "SWISSKNIFE_MOBILE_INTEROP_DESCRIPTOR",
            "MOBILE_ORB_BRIDGE_OPERATIONS",
            "DISPLAY_WIDGET_BRIDGE_OPERATIONS",
        ],
    )

    interface = exports["SWISSKNIFE_MOBILE_INTEROP_INTERFACE"]
    descriptor = exports["SWISSKNIFE_MOBILE_INTEROP_DESCRIPTOR"]

    assert interface["metadata"]["interface_contract"] == "interface contract swissknife mobile"
    assert set(interface["objective_goals"]) == GOAL_PACKET_GOALS
    assert {method["name"] for method in interface["methods"]} == (
        MOBILE_ORB_OPERATIONS | DISPLAY_WIDGET_OPERATIONS
    )
    assert set(exports["MOBILE_ORB_BRIDGE_OPERATIONS"]) == MOBILE_ORB_OPERATIONS
    assert set(exports["DISPLAY_WIDGET_BRIDGE_OPERATIONS"]) == DISPLAY_WIDGET_OPERATIONS
    assert descriptor["schema_refs"] == {
        "control_surface_contract": "swissknife/contracts/control_surface_contract.schema.json",
        "interaction_envelope": "swissknife/contracts/interaction_envelope.schema.json",
        "mediation_receipt": "swissknife/contracts/mediation_receipt.schema.json",
        "mcp_plus_plus_compatibility_receipt": (
            "swissknife/contracts/mcp_plus_plus_compatibility_receipt.schema.json"
        ),
    }
    assert descriptor["runtime_handoff"]["source_surface"] == "swissknife"
    assert descriptor["runtime_handoff"]["target_surface"] == "mobile"
    assert {"agent", "remote_client"}.issubset(
        set(descriptor["runtime_handoff"]["allowed_surfaces"])
    )


def test_mobile_display_widget_contract_maps_swissknife_actions_to_dat_methods() -> None:
    exports = load_js_exports(
        "mobile/src/utils/metaWearablesDatDisplayWidgetContract.js",
        [
            "DISPLAY_WIDGET_ACTION_IDS",
            "DISPLAY_WIDGET_ORB_OPERATION_BY_ACTION_ID",
            "DISPLAY_WIDGET_DAT_METHOD_BY_ACTION_ID",
            "SWISSKNIFE_DISPLAY_WIDGET_ACTION_CONTRACT",
        ],
    )

    action_ids = set(exports["DISPLAY_WIDGET_ACTION_IDS"])
    contract = exports["SWISSKNIFE_DISPLAY_WIDGET_ACTION_CONTRACT"]

    assert contract["producer"] == "swissknife"
    assert contract["consumer"] == "mobile"
    assert contract["interface_contract"] == "interface contract swissknife mobile"
    assert set(contract["action_ids"]) == action_ids
    assert set(contract["operation_by_action_id"]) == action_ids
    assert set(contract["dat_method_by_action_id"]) == action_ids
    assert contract["operation_by_action_id"]["mobile_render_display_widget"] == "render_widget"
    assert contract["dat_method_by_action_id"]["mobile_render_display_widget"] == (
        "renderDisplayWidget"
    )


def test_swissknife_control_surface_and_interaction_envelope_validate_for_mobile() -> None:
    control_schema = read_json("swissknife/contracts/control_surface_contract.schema.json")
    envelope_schema = read_json("swissknife/contracts/interaction_envelope.schema.json")

    Draft202012Validator(control_schema).validate(swissknife_mobile_control_surface_payload())
    Draft202012Validator(envelope_schema).validate(swissknife_mobile_interaction_envelope())


def test_mobile_orb_bridge_module_remains_parseable_after_contract_wiring() -> None:
    assert_module_is_valid_esm("mobile/src/orb/metaGlassesMobileOrbBridge.js")
    source = (REPO_ROOT / "mobile/src/orb/metaGlassesMobileOrbBridge.js").read_text(
        encoding="utf-8"
    )
    assert "SWISSKNIFE_MOBILE_INTEROP_DESCRIPTOR" in source
    assert "SWISSKNIFE_MOBILE_INTEROP_INTERFACE" in source
    assert source.count("export const MOBILE_ORB_DIAGNOSTICS_CONTRACT") == 1


def test_docs_discovery_and_heap_record_objective_validation_repair() -> None:
    docs = (REPO_ROOT / "docs/integration/swissknife-mobile.md").read_text(encoding="utf-8")
    discovery = (
        REPO_ROOT
        / "data/meta_glasses_display_widgets/discovery/2026-07-08-mgw-583-mgw-569-validation-repair.md"
    ).read_text(encoding="utf-8")
    heap = (
        REPO_ROOT / "implementation_plan/docs/23-virtual-ai-os-objective-goal-heap.md"
    ).read_text(encoding="utf-8")

    required_terms = [
        "MGW-569",
        "MGW-583",
        "VAIOS-G700",
        "goal_packet/interoperability/swissknife/06921590135c",
        "objective validation repair",
        "interface contract swissknife mobile",
        "tests/integration/test_swissknife_mobile_interop.py",
        "mobile/src/orb/metaGlassesOrbDescriptors.js",
        "mobile/src/utils/metaWearablesDatDisplayWidgetContract.js",
        "swissknife/contracts/control_surface_contract.schema.json",
        "swissknife/contracts/interaction_envelope.schema.json",
    ]
    for content in (docs, discovery, heap):
        for term in required_terms:
            assert term in content
    for goal_id in GOAL_PACKET_GOALS:
        assert goal_id in discovery
        assert goal_id in heap
