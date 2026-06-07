"""Tests for multimodal control-surface JSON schema contracts."""

from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path

from jsonschema import Draft202012Validator, ValidationError
from referencing import Registry, Resource


sys.path.append(str(Path(__file__).parent.parent.parent))

from hallucinate_app.control_surface_intents import normalize_interaction


HALLUCINATE_ROOT = Path(__file__).resolve().parents[3]
CONTRACT_DIR = HALLUCINATE_ROOT / "swissknife" / "contracts"
SCHEMA_FILES = {
    "control_surface_contract": "control_surface_contract.schema.json",
    "interaction_envelope": "interaction_envelope.schema.json",
    "policy_decision": "policy_decision.schema.json",
    "mediation_receipt": "mediation_receipt.schema.json",
}


class TestControlSurfaceSchemas(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.schemas = {
            name: json.loads((CONTRACT_DIR / filename).read_text(encoding="utf-8"))
            for name, filename in SCHEMA_FILES.items()
        }
        cls.registry = Registry().with_resources(
            (schema["$id"], Resource.from_contents(schema))
            for schema in cls.schemas.values()
        )

    def _validator(self, schema_name: str) -> Draft202012Validator:
        return Draft202012Validator(self.schemas[schema_name], registry=self.registry)

    def _logic_binding(self) -> dict[str, object]:
        return {
            "policy_bundle_ref": "policy:quiet-hours-gestures",
            "compiled_policy_cid": "bafy-policy-quiet-hours",
            "policy_ir_version": "0.1.0",
            "compiler_api": "ipfs_datasets_py.logic.api.compile_nl_to_policy",
            "evaluator_api": "ipfs_datasets_py.logic.api.evaluate_nl_policy",
            "compiled_artifact_refs": {
                "frame_logic": "bafy-frame-logic",
                "event_calculus": "bafy-event-calculus",
                "deontic": "bafy-deontic",
            },
            "interaction_envelope_schema_ref": "interaction_envelope.schema.json",
            "policy_decision_schema_ref": "policy_decision.schema.json",
            "mediation_receipt_schema_ref": "mediation_receipt.schema.json",
        }

    def _sample_contract(self) -> dict[str, object]:
        return {
            "name": "hallucinate-display",
            "control_surface_contract": {
                "version": "0.1.0",
                "control_surfaces": [
                    {
                        "id": "gesture",
                        "kind": "captouch_or_wrist",
                        "event_types": ["tap", "swipe", "hold", "wrist_raise"],
                        "intent_resolver": "gesture_mapping_table",
                        "logic_bindings": self._logic_binding(),
                    },
                    {
                        "id": "voice",
                        "kind": "voice_command",
                        "event_types": ["utterance", "confirm", "cancel"],
                        "intent_resolver": "nl_policy_compiler",
                        "confidence_policy": {
                            "min_confidence": 0.85,
                            "clarify_below": 0.92,
                        },
                        "logic_bindings": self._logic_binding(),
                    },
                ],
                "intent_bindings": [
                    {
                        "intent": "display.activate",
                        "method": "activate",
                        "target_ref": "widget:primary-action",
                        "allowed_surfaces": ["gesture", "mouse", "voice", "agent"],
                        "required_decision_outcomes": [
                            "allow",
                            "deny",
                            "require_confirmation",
                            "fallback_surface",
                        ],
                        "logic_bindings": self._logic_binding(),
                    }
                ],
                "logic_bindings": self._logic_binding(),
                "policy_hooks": {
                    "compile_api": "ipfs_datasets_py.logic.api.compile_nl_to_policy",
                    "evaluate_api": "ipfs_datasets_py.logic.api.evaluate_nl_policy",
                    "decision_receipt": True,
                    "policy_bundle_ref": "policy:quiet-hours-gestures",
                    "compiled_policy_cid": "bafy-policy-quiet-hours",
                    "interaction_envelope_schema_ref": "interaction_envelope.schema.json",
                    "policy_decision_schema_ref": "policy_decision.schema.json",
                    "mediation_receipt_schema_ref": "mediation_receipt.schema.json",
                },
                "context_schema": {
                    "state_frames": ["sleeping", "driving", "meeting", "screen_locked"],
                    "time_context": True,
                    "location_context": True,
                    "device_context": True,
                    "agent_identity": True,
                },
                "conflict_resolution": {
                    "default": "deny_over_permit",
                    "requires_explanation": True,
                    "requires_user_confirmation_for": [
                        "destructive",
                        "financial",
                        "communication.send",
                    ],
                },
                "mediation_receipts": {
                    "enabled": True,
                    "schema_ref": "mediation_receipt.schema.json",
                    "store_ref": "audit:control_surface_mediation",
                    "include_interaction_envelope": True,
                    "include_policy_decision": True,
                    "include_logic_bindings": True,
                },
            },
        }

    def _sample_envelope(self) -> dict[str, object]:
        return normalize_interaction(
            interaction_id="gesture-quiet-hours-001",
            surface="gesture",
            surface_event="wrist_raise",
            raw_payload={"sensor": "captouch", "gesture": "wrist_raise"},
            normalized_intent={
                "intent": "display.activate",
                "method": "activate",
                "target_ref": "widget:primary-action",
                "arguments": {"source": "gesture"},
                "confidence": 0.91,
            },
            actor={
                "type": "user",
                "id": "operator-7",
                "delegation_chain": ["operator-7"],
            },
            context={
                "local_time": "2026-05-23T23:15:00-07:00",
                "state_frames": ["sleeping", "quiet_hours"],
                "device_mode": "quiet_hours",
                "platform": "hallucinate_app",
                "device_context": {"surface": "desktop-shell"},
            },
        ).as_dict()

    def _sample_decision(self, envelope: dict[str, object]) -> dict[str, object]:
        logic_binding = self._logic_binding()
        return {
            "decision_id": "decision:gesture-quiet-hours-001",
            "interaction_id": envelope["interaction_id"],
            "decided_at": "2026-05-23T23:15:01-07:00",
            "outcome": "deny",
            "surface": envelope["surface"],
            "surface_event": envelope["surface_event"],
            "method": "activate",
            "target_ref": "widget:primary-action",
            "policy_bundle_ref": logic_binding["policy_bundle_ref"],
            "compiled_policy_cid": logic_binding["compiled_policy_cid"],
            "logic_bindings": logic_binding,
            "policy_refs": [
                {
                    "policy_id": "policy:quiet-hours-gestures",
                    "policy_bundle_ref": "policy:quiet-hours-gestures",
                    "compiled_policy_cid": "bafy-policy-quiet-hours",
                    "norm_id": "norm:quiet-hours-wrist-raise",
                    "source_text": "Ignore my wrist gestures at night, because I'm sleeping.",
                    "explanation": "Deny wrist activation while sleeping and quiet hours hold.",
                }
            ],
            "matched_norms": [
                {
                    "norm_id": "norm:quiet-hours-wrist-raise",
                    "outcome": "deny",
                    "priority": 100,
                    "guard_refs": ["guard:state:sleeping", "guard:time:quiet-hours"],
                }
            ],
            "effect": {
                "outcome": "deny",
                "method": "activate",
                "target_ref": "widget:primary-action",
                "arguments": {"source": "gesture"},
                "confirmation_required": False,
                "reason": "Gesture activation is suppressed while sleeping.",
            },
            "explanation": {
                "summary": "Wrist activation denied by the quiet-hours gesture policy.",
                "operator_visible": True,
                "policy_messages": [
                    "Deny wrist gesture activation when sleeping and quiet hours hold."
                ],
                "frame_fact_refs": ["fact:surface:gesture", "fact:state:sleeping"],
            },
            "metadata": {"evaluator": "control_surface_policy"},
        }

    def _sample_receipt(
        self,
        envelope: dict[str, object],
        decision: dict[str, object],
    ) -> dict[str, object]:
        return {
            "receipt_id": "receipt:gesture-quiet-hours-001",
            "receipt_type": "mediation_receipt",
            "interaction_id": envelope["interaction_id"],
            "decision_id": decision["decision_id"],
            "created_at": "2026-05-23T23:15:01-07:00",
            "surface": envelope["surface"],
            "surface_event": envelope["surface_event"],
            "normalized_intent": envelope["normalized_intent"],
            "actor": envelope["actor"],
            "context": envelope["context"],
            "interaction_envelope": envelope,
            "policy_decision": decision,
            "logic_bindings": decision["logic_bindings"],
            "policy_refs": decision["policy_refs"],
            "explanation": {
                "summary": "Wrist activation denied by policy.",
                "outcome_reason": "The sleeping and quiet-hours guards matched the gesture event.",
                "operator_visible": True,
                "policy_messages": [
                    "Deny wrist gesture activation when sleeping and quiet hours hold."
                ],
            },
            "audit": {
                "raw_payload_cid": "bafy-raw-gesture-event",
                "context_fact_count": 6,
            },
        }

    def test_schema_files_are_valid_draft_2020_12(self) -> None:
        for schema in self.schemas.values():
            Draft202012Validator.check_schema(schema)

    def test_contract_binds_surfaces_and_methods_to_policy_artifacts(self) -> None:
        contract = self._sample_contract()
        self._validator("control_surface_contract").validate(contract)

        section = contract["control_surface_contract"]
        surface_binding = section["control_surfaces"][0]["logic_bindings"]
        method_binding = section["intent_bindings"][0]["logic_bindings"]

        self.assertEqual(surface_binding["policy_bundle_ref"], "policy:quiet-hours-gestures")
        self.assertEqual(method_binding["compiled_policy_cid"], "bafy-policy-quiet-hours")
        self.assertEqual(
            section["mediation_receipts"]["schema_ref"],
            "mediation_receipt.schema.json",
        )

    def test_interaction_decision_and_receipt_examples_validate(self) -> None:
        envelope = self._sample_envelope()
        decision = self._sample_decision(envelope)
        receipt = self._sample_receipt(envelope, decision)

        self._validator("interaction_envelope").validate(envelope)
        self._validator("policy_decision").validate(decision)
        self._validator("mediation_receipt").validate(receipt)

        self.assertEqual(receipt["policy_decision"]["compiled_policy_cid"], "bafy-policy-quiet-hours")
        self.assertEqual(receipt["interaction_envelope"]["interaction_id"], receipt["interaction_id"])

    def test_missing_compiled_policy_binding_is_rejected(self) -> None:
        contract = self._sample_contract()
        intent_binding = contract["control_surface_contract"]["intent_bindings"][0]
        del intent_binding["logic_bindings"]["compiled_policy_cid"]

        with self.assertRaises(ValidationError):
            self._validator("control_surface_contract").validate(contract)

    def test_mediation_receipt_requires_policy_decision(self) -> None:
        envelope = self._sample_envelope()
        decision = self._sample_decision(envelope)
        receipt = self._sample_receipt(envelope, decision)
        del receipt["policy_decision"]

        with self.assertRaises(ValidationError):
            self._validator("mediation_receipt").validate(receipt)


if __name__ == "__main__":
    unittest.main()
