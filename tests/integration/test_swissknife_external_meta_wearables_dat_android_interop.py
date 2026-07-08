"""SwissKnife/external/meta-wearables-dat-android interoperability regression tests for MGW-574."""

from __future__ import annotations

import json
import sys
from pathlib import Path

from jsonschema import Draft202012Validator

REPO_ROOT = Path(__file__).resolve().parents[2]
SRC_ROOT = REPO_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from handsfree.swissknife_meta_wearables_dat_android_interop import (  # noqa: E402
    GOAL_ID,
    GOAL_PACKET,
    REQUIRED_DEVICE_SESSION_STATES,
    REQUIRED_DISPLAY_BUTTON_STYLES,
    REQUIRED_DISPLAY_ICON_NAMES,
    REQUIRED_MANIFEST_METADATA_KEYS,
    REQUIRED_MANIFEST_PERMISSIONS,
    REQUIRED_SWISSKNIFE_META_WEARABLES_DAT_ANDROID_OPERATIONS,
    SwissKnifeMetaWearablesDATAndroidInteropError,
    build_swissknife_meta_wearables_dat_android_handoff,
    discover_meta_wearables_dat_android_display_contract,
)

META_WEARABLES_DAT_ANDROID_ROOT = REPO_ROOT / "external" / "meta-wearables-dat-android"
DESCRIPTOR_TS_PATH = (
    "swissknife/src/services/mcp/meta-wearables-dat-android-display-interop-descriptor.ts"
)

GOAL_PACKET_GOALS = {
    "VAIOS-G700",
    "VAIOS-G701",
    "VAIOS-G702",
    "VAIOS-G703",
    "VAIOS-G704",
    "VAIOS-G705",
    "VAIOS-G706",
}


def read_text(path: str) -> str:
    return (REPO_ROOT / path).read_text(encoding="utf-8")


def read_json(path: str) -> dict:
    return json.loads((REPO_ROOT / path).read_text(encoding="utf-8"))


def swissknife_meta_wearables_dat_android_control_surface_payload() -> dict:
    """Python mirror of buildSwissKnifeMetaWearablesDATAndroidControlSurfaceContract()."""
    policy_bundle_ref = {
        "policy_id": "policy:swissknife:meta-wearables-dat-android-display-interop",
        "policy_cid": "local:swissknife:meta-wearables-dat-android-display-interop",
        "version": "0.1.0",
        "scope": "swissknife-meta-wearables-dat-android-display-interop",
        "source": "system_default",
    }
    logic_binding = {
        "binding_id": "binding:swissknife-meta-wearables-dat-android-display-session",
        "policy_bundle_ref": policy_bundle_ref,
        "compiled_policy_cid": "local:swissknife:meta-wearables-dat-android-display-interop",
        "ir_version": "0.1.0",
        "frame_fact_kinds": ["actor", "surface", "event", "method", "context"],
        "surface_refs": ["agent", "mcp_server", "remote_client"],
        "method_refs": [
            "meta_wearables_dat_android.session.start",
            "meta_wearables_dat_android.display.send_content",
        ],
        "norm_refs": ["agent_identity", "allowed_surfaces", "arguments_hash"],
        "compiled_artifact_refs": [
            {
                "artifact_type": "deontic_policy",
                "cid": "local:swissknife:meta-wearables-dat-android-display-interop",
                "media_type": "application/json",
                "description": "interface contract swissknife external/meta-wearables-dat-android",
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
                    "id": "swissknife.meta_wearables_dat_android.display-service",
                    "kind": "display_service",
                    "event_types": ["session_start", "send_content"],
                    "intent_resolver": "swissknife.meta_wearables_dat_android.intent_resolver",
                    "confidence_policy": {"min_confidence": 0.85, "clarify_below": 0.6},
                    "logic_bindings": [logic_binding],
                }
            ],
            "intent_bindings": [
                {
                    "intent": "swissknife.meta_wearables_dat_android.send_content",
                    "method": "meta_wearables_dat_android.display.send_content",
                    "target_ref": "meta_wearables_dat_android:display_session",
                    "allowed_surfaces": ["agent", "mcp_server", "remote_client"],
                    "required_context_facts": ["agent_identity", "device_id"],
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
                "state_frames": ["meta_wearables_dat_android_display_session"],
                "time_context": True,
                "location_context": False,
                "device_context": True,
                "agent_identity": True,
            },
            "conflict_resolution": {
                "default": "require_confirmation",
                "requires_explanation": True,
                "requires_user_confirmation_for": ["session_stop", "display_detach"],
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


def swissknife_meta_wearables_dat_android_interaction_envelope() -> dict:
    """Python mirror of buildSwissKnifeMetaWearablesDATAndroidInteractionEnvelope()."""
    policy_bundle_ref = {
        "policy_id": "policy:swissknife:meta-wearables-dat-android-display-interop",
        "policy_cid": "local:swissknife:meta-wearables-dat-android-display-interop",
        "version": "0.1.0",
        "scope": "swissknife-meta-wearables-dat-android-display-interop",
        "source": "system_default",
    }
    return {
        "interaction_id": "interaction:swissknife-meta-wearables-dat-android:send-content:1",
        "surface": "display_service",
        "surface_event": "send_content",
        "raw_payload": {
            "device_id": "swissknife-meta-wearables-dat-android-device",
            "content": {"kind": "flexBox", "gap": 12, "padding": 24},
        },
        "normalized_intent": {
            "intent": "swissknife.meta_wearables_dat_android.send_content",
            "method": "meta_wearables_dat_android.display.send_content",
            "target_ref": "meta_wearables_dat_android:display_session",
            "arguments": {
                "device_id": "swissknife-meta-wearables-dat-android-device",
                "arguments_hash": "sha256:swissknife-meta-wearables-dat-android-send-content",
            },
            "confidence": 0.95,
        },
        "actor": {
            "type": "agent",
            "id": "swissknife:meta-wearables-dat-android-operator-agent",
            "delegation_chain": ["ucan:swissknife-meta-wearables-dat-android-display-interop"],
        },
        "context": {
            "local_time": "2026-07-08T00:00:00Z",
            "state_frames": ["meta_wearables_dat_android_display_session"],
            "device_mode": "mobile",
            "platform": "meta_wearables_dat_android",
            "location_context": {},
            "device_context": {
                "device_session_states": list(REQUIRED_DEVICE_SESSION_STATES),
                "display_icon_names": list(REQUIRED_DISPLAY_ICON_NAMES),
                "display_button_styles": list(REQUIRED_DISPLAY_BUTTON_STYLES),
            },
        },
        "control_surface_contract_ref": "swissknife/contracts/control_surface_contract.schema.json",
        "policy_bundle_ref": policy_bundle_ref,
        "compiled_policy_cid": "local:swissknife:meta-wearables-dat-android-display-interop",
        "logic_bindings": [
            {
                "binding_id": "binding:swissknife-meta-wearables-dat-android-display-session",
                "policy_bundle_ref": policy_bundle_ref,
                "compiled_policy_cid": "local:swissknife:meta-wearables-dat-android-display-interop",
                "surface_ref": "display_service",
                "method_ref": "meta_wearables_dat_android.display.send_content",
                "norm_refs": ["agent_identity", "allowed_surfaces", "arguments_hash"],
            }
        ],
    }


def test_meta_wearables_dat_android_display_descriptors_exist_on_disk() -> None:
    expected_paths = [
        "external/meta-wearables-dat-android/.cursor/rules/display-access.mdc",
        "external/meta-wearables-dat-android/.cursor/rules/session-lifecycle.mdc",
        "external/meta-wearables-dat-android/.cursor/rules/permissions-registration.mdc",
        "external/meta-wearables-dat-android/samples/DisplayAccess/app/src/main/AndroidManifest.xml",
        "external/meta-wearables-dat-android/samples/DisplayAccess/app/src/main/java/com/meta/"
        "wearable/dat/externalsampleapps/displayaccess/display/DisplayViewModel.kt",
    ]
    for relative_path in expected_paths:
        assert (REPO_ROOT / relative_path).is_file(), f"missing {relative_path}"


def test_discover_meta_wearables_dat_android_display_contract_finds_expected_surface() -> None:
    contract = discover_meta_wearables_dat_android_display_contract(META_WEARABLES_DAT_ANDROID_ROOT)

    assert set(REQUIRED_DEVICE_SESSION_STATES).issubset(set(contract.device_session_states))
    assert set(REQUIRED_MANIFEST_METADATA_KEYS).issubset(set(contract.manifest_metadata_keys))
    assert set(REQUIRED_MANIFEST_PERMISSIONS).issubset(set(contract.manifest_permissions))
    assert set(REQUIRED_DISPLAY_ICON_NAMES).issubset(set(contract.display_icon_names))
    assert set(REQUIRED_DISPLAY_BUTTON_STYLES).issubset(set(contract.display_button_styles))
    assert contract.display_access_doc_path.endswith(".cursor/rules/display-access.mdc")
    assert contract.session_lifecycle_doc_path.endswith(".cursor/rules/session-lifecycle.mdc")
    assert contract.permissions_registration_doc_path.endswith(
        ".cursor/rules/permissions-registration.mdc"
    )
    assert contract.display_manifest_path.endswith(
        "samples/DisplayAccess/app/src/main/AndroidManifest.xml"
    )
    assert contract.display_view_model_path.endswith("display/DisplayViewModel.kt")


def test_discover_meta_wearables_dat_android_display_contract_raises_for_missing_root(
    tmp_path,
) -> None:
    missing_root = tmp_path / "does-not-exist"
    try:
        discover_meta_wearables_dat_android_display_contract(missing_root)
    except SwissKnifeMetaWearablesDATAndroidInteropError as exc:
        assert "not found" in str(exc)
    else:
        raise AssertionError("expected SwissKnifeMetaWearablesDATAndroidInteropError")


def test_build_swissknife_meta_wearables_dat_android_handoff_is_deterministic() -> None:
    first = build_swissknife_meta_wearables_dat_android_handoff(META_WEARABLES_DAT_ANDROID_ROOT)
    second = build_swissknife_meta_wearables_dat_android_handoff(META_WEARABLES_DAT_ANDROID_ROOT)

    assert first.as_dict() == second.as_dict()
    assert (
        first.interface_contract
        == "interface contract swissknife external/meta-wearables-dat-android"
    )
    assert first.goal_id == GOAL_ID == "VAIOS-G705"
    assert first.goal_packet == GOAL_PACKET
    assert first.source_repository == "swissknife"
    assert first.target_repository == "external/meta-wearables-dat-android"
    assert first.content_cid.startswith("sha256:")
    assert first.content_cid == f"sha256:{first.payload_sha256}"
    assert first.payload_size_bytes > 0
    assert set(REQUIRED_DEVICE_SESSION_STATES).issubset(set(first.device_session_states))
    assert set(REQUIRED_DISPLAY_ICON_NAMES).issubset(set(first.display_icon_names))
    assert set(REQUIRED_DISPLAY_BUTTON_STYLES).issubset(set(first.display_button_styles))
    assert set(first.required_swissknife_operations) == set(
        REQUIRED_SWISSKNIFE_META_WEARABLES_DAT_ANDROID_OPERATIONS
    )


def test_swissknife_descriptor_module_exports_interop_contract() -> None:
    src = read_text(DESCRIPTOR_TS_PATH)

    assert "export const SWISSKNIFE_META_WEARABLES_DAT_ANDROID_INTEROP_INTERFACE" in src
    assert "export const SWISSKNIFE_META_WEARABLES_DAT_ANDROID_INTEROP_DESCRIPTOR" in src
    assert "'interface contract swissknife external/meta-wearables-dat-android'" in src
    assert "'goal_packet/interoperability/swissknife/06921590135c'" in src
    assert "export function registerSwissKnifeMetaWearablesDATAndroidDisplayInterop" in src
    assert (
        "export function createMCPPlusPlusClientWithSwissKnifeMetaWearablesDATAndroidInterop"
        in src
    )
    assert "export function buildSwissKnifeMetaWearablesDATAndroidControlSurfaceContract" in src
    assert "export function buildSwissKnifeMetaWearablesDATAndroidInteractionEnvelope" in src

    for goal_id in GOAL_PACKET_GOALS:
        assert goal_id in src
    for operation in REQUIRED_SWISSKNIFE_META_WEARABLES_DAT_ANDROID_OPERATIONS:
        assert operation in src
    for state in REQUIRED_DEVICE_SESSION_STATES:
        assert state in src
    for icon_name in REQUIRED_DISPLAY_ICON_NAMES:
        assert icon_name in src
    for button_style in REQUIRED_DISPLAY_BUTTON_STYLES:
        assert button_style in src
    for metadata_key in REQUIRED_MANIFEST_METADATA_KEYS:
        assert metadata_key in src
    for permission in REQUIRED_MANIFEST_PERMISSIONS:
        assert permission in src

    assert "swissknife/contracts/control_surface_contract.schema.json" in src
    assert "swissknife/contracts/interaction_envelope.schema.json" in src
    assert "swissknife/contracts/mediation_receipt.schema.json" in src
    assert (
        "external/meta-wearables-dat-android/.cursor/rules/display-access.mdc" in src
    )
    assert (
        "external/meta-wearables-dat-android/.cursor/rules/session-lifecycle.mdc" in src
    )
    assert (
        "external/meta-wearables-dat-android/.cursor/rules/permissions-registration.mdc" in src
    )
    assert (
        "external/meta-wearables-dat-android/samples/DisplayAccess/app/src/main/AndroidManifest.xml"
        in src
    )
    assert "MGW-574" in src
    assert "VAIOS-G705" in src
    assert "agent_identity" in src
    assert "allowed_surfaces" in src
    assert "arguments_hash" in src


def test_swissknife_control_surface_and_interaction_envelope_validate_for_meta_wearables_dat_android() -> (
    None
):
    control_schema = read_json("swissknife/contracts/control_surface_contract.schema.json")
    envelope_schema = read_json("swissknife/contracts/interaction_envelope.schema.json")

    Draft202012Validator(control_schema).validate(
        swissknife_meta_wearables_dat_android_control_surface_payload()
    )
    Draft202012Validator(envelope_schema).validate(
        swissknife_meta_wearables_dat_android_interaction_envelope()
    )


def test_docs_discovery_and_heap_record_objective_validation_repair() -> None:
    docs = read_text("docs/integration/swissknife-external_meta_wearables_dat_android.md")
    discovery = read_text(
        "data/meta_glasses_display_widgets/discovery/"
        "2026-07-08-mgw-574-objective-validation-repair.md"
    )
    gap = read_text(
        "data/meta_glasses_display_widgets/discovery/2026-07-08-mgw-574-objective-gap-73dd061c433c.md"
    )
    heap = read_text("implementation_plan/docs/23-virtual-ai-os-objective-goal-heap.md")

    required_terms = [
        "MGW-574",
        "VAIOS-G705",
        "goal_packet/interoperability/swissknife/06921590135c",
        "objective validation repair",
        "interface contract swissknife external/meta-wearables-dat-android",
        "tests/integration/test_swissknife_external_meta_wearables_dat_android_interop.py",
        DESCRIPTOR_TS_PATH,
        "src/handsfree/swissknife_meta_wearables_dat_android_interop.py",
        "swissknife/contracts/control_surface_contract.schema.json",
        "swissknife/contracts/interaction_envelope.schema.json",
        "external/meta-wearables-dat-android/.cursor/rules/display-access.mdc",
        "external/meta-wearables-dat-android/.cursor/rules/session-lifecycle.mdc",
        "external/meta-wearables-dat-android/.cursor/rules/permissions-registration.mdc",
    ]
    for content in (docs, discovery, heap):
        for term in required_terms:
            assert term in content, f"missing {term!r}"
    for goal_id in GOAL_PACKET_GOALS:
        assert goal_id in discovery
        assert goal_id in heap
    assert "VAIOS-G705" in gap
