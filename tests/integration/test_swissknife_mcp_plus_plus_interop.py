"""SwissKnife/Mcp-Plus-Plus interoperability contract regression tests for VAI-665."""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest
from jsonschema import Draft202012Validator

REPO_ROOT = Path(__file__).resolve().parents[2]
MCP_PLUS_PLUS_TESTS_PY = REPO_ROOT / "Mcp-Plus-Plus" / "tests-py"

GOAL_PACKET_GOALS = {
    "VAIOS-G700",
    "VAIOS-G701",
    "VAIOS-G702",
    "VAIOS-G703",
    "VAIOS-G704",
    "VAIOS-G705",
    "VAIOS-G706",
}

MCP_PLUS_PLUS_INTEROP_OPERATIONS = {
    "mcpplusplus.negotiate_capabilities",
    "mcpplusplus.execute_with_envelope",
    "mcpplusplus.create_delegation",
    "mcpplusplus.evaluate_policy",
    "mcpplusplus.get_dag_frontier",
    "mcpplusplus.check_compatibility",
    "mcpplusplus.create_p2p_session",
}


def read_text(path: str) -> str:
    return (REPO_ROOT / path).read_text(encoding="utf-8")


def read_json(path: str) -> dict:
    return json.loads((REPO_ROOT / path).read_text(encoding="utf-8"))


def swissknife_mcp_plus_plus_control_surface_payload() -> dict:
    """Python mirror of buildSwissKnifeMcpPlusPlusControlSurfaceContract()."""
    policy_bundle_ref = {
        "policy_id": "policy:swissknife:mcp-plus-plus-interop",
        "policy_cid": "local:swissknife:mcp-plus-plus-interop",
        "version": "0.1.0",
        "scope": "swissknife-mcp-plus-plus-interop",
        "source": "system_default",
    }
    logic_binding = {
        "binding_id": "binding:swissknife-mcp-plus-plus-negotiate",
        "policy_bundle_ref": policy_bundle_ref,
        "compiled_policy_cid": "local:swissknife:mcp-plus-plus-interop",
        "ir_version": "0.1.0",
        "frame_fact_kinds": ["actor", "surface", "event", "method", "context"],
        "surface_refs": ["agent", "mcp_server", "remote_client"],
        "method_refs": ["mcpplusplus.execute_with_envelope", "mcpplusplus.negotiate_capabilities"],
        "norm_refs": ["agent_identity", "allowed_surfaces", "arguments_hash"],
        "compiled_artifact_refs": [
            {
                "artifact_type": "deontic_policy",
                "cid": "local:swissknife:mcp-plus-plus-interop",
                "media_type": "application/json",
                "description": "interface contract swissknife Mcp-Plus-Plus",
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
                    "id": "swissknife.mcp_plus_plus.mcp-server",
                    "kind": "mcp_server",
                    "event_types": ["execute_with_envelope", "negotiate_capabilities"],
                    "intent_resolver": "swissknife.mcp_plus_plus.intent_resolver",
                    "confidence_policy": {"min_confidence": 0.85, "clarify_below": 0.6},
                    "logic_bindings": [logic_binding],
                }
            ],
            "intent_bindings": [
                {
                    "intent": "swissknife.mcp_plus_plus.execute_with_envelope",
                    "method": "mcpplusplus.execute_with_envelope",
                    "target_ref": "mcp_plus_plus:interop_descriptor",
                    "allowed_surfaces": ["agent", "mcp_server", "remote_client"],
                    "required_context_facts": ["agent_identity", "interface_cid"],
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
                "state_frames": ["mcp_plus_plus_session"],
                "time_context": True,
                "location_context": False,
                "device_context": False,
                "agent_identity": True,
            },
            "conflict_resolution": {
                "default": "require_confirmation",
                "requires_explanation": True,
                "requires_user_confirmation_for": ["execute_with_envelope"],
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


def swissknife_mcp_plus_plus_interaction_envelope() -> dict:
    """Python mirror of buildSwissKnifeMcpPlusPlusInteractionEnvelope()."""
    policy_bundle_ref = {
        "policy_id": "policy:swissknife:mcp-plus-plus-interop",
        "policy_cid": "local:swissknife:mcp-plus-plus-interop",
        "version": "0.1.0",
        "scope": "swissknife-mcp-plus-plus-interop",
        "source": "system_default",
    }
    return {
        "interaction_id": "interaction:swissknife-mcp-plus-plus:execute-with-envelope:1",
        "surface": "mcp_server",
        "surface_event": "execute_with_envelope",
        "raw_payload": {
            "interface_cid": "bafyswissknifemcpplusplusinterop000000001",
            "method": "mcpplusplus.negotiate_capabilities",
        },
        "normalized_intent": {
            "intent": "swissknife.mcp_plus_plus.execute_with_envelope",
            "method": "mcpplusplus.execute_with_envelope",
            "target_ref": "mcp_plus_plus:interop_descriptor",
            "arguments": {
                "interface_cid": "bafyswissknifemcpplusplusinterop000000001",
                "arguments_hash": "sha256:swissknife-mcp-plus-plus-execute-with-envelope",
            },
            "confidence": 0.97,
        },
        "actor": {
            "type": "agent",
            "id": "swissknife:mcp-plus-plus-operator-agent",
            "delegation_chain": ["ucan:swissknife-mcp-plus-plus-interop"],
        },
        "context": {
            "local_time": "2026-07-08T00:00:00Z",
            "state_frames": ["mcp_plus_plus_session"],
            "device_mode": "server",
            "platform": "mcp_plus_plus",
            "location_context": {},
            "device_context": {
                "interface_cid": "bafyswissknifemcpplusplusinterop000000001",
                "negotiated_profiles": ["mcp++/mcp-idl", "mcp++/cid-envelope", "mcp++/deontic-policy"],
            },
        },
        "control_surface_contract_ref": "swissknife/contracts/control_surface_contract.schema.json",
        "policy_bundle_ref": policy_bundle_ref,
        "compiled_policy_cid": "local:swissknife:mcp-plus-plus-interop",
        "logic_bindings": [
            {
                "binding_id": "binding:swissknife-mcp-plus-plus-negotiate",
                "policy_bundle_ref": policy_bundle_ref,
                "compiled_policy_cid": "local:swissknife:mcp-plus-plus-interop",
                "surface_ref": "mcp_server",
                "method_ref": "mcpplusplus.execute_with_envelope",
                "norm_refs": ["agent_identity", "allowed_surfaces", "arguments_hash"],
            }
        ],
    }


def test_swissknife_descriptor_module_exports_interop_contract() -> None:
    src = read_text("swissknife/src/services/mcp/mcp-plus-plus-interop-descriptor.ts")

    assert "export const SWISSKNIFE_MCP_PLUS_PLUS_INTEROP_INTERFACE" in src
    assert "export const SWISSKNIFE_MCP_PLUS_PLUS_INTEROP_DESCRIPTOR" in src
    assert "'interface contract swissknife Mcp-Plus-Plus'" in src
    assert "'goal_packet/interoperability/swissknife/06921590135c'" in src
    assert "export function registerSwissKnifeMcpPlusPlusInterop" in src
    assert "export function createMCPPlusPlusClientWithSwissKnifeInterop" in src
    assert "export function toMcpIdlValidatorDescriptor" in src
    assert "export function buildSwissKnifeMcpPlusPlusControlSurfaceContract" in src
    assert "export function buildSwissKnifeMcpPlusPlusInteractionEnvelope" in src

    for goal_id in GOAL_PACKET_GOALS:
        assert goal_id in src
    for operation in MCP_PLUS_PLUS_INTEROP_OPERATIONS:
        assert operation in src

    assert "swissknife/contracts/control_surface_contract.schema.json" in src
    assert "swissknife/contracts/interaction_envelope.schema.json" in src
    assert "swissknife/contracts/mediation_receipt.schema.json" in src
    assert "swissknife/contracts/policy_decision.schema.json" in src
    assert "swissknife/contracts/mcp_plus_plus_compatibility_receipt.schema.json" in src
    assert "Mcp-Plus-Plus/tests-py/fixtures/valid/mcp_idl_descriptor.json" in src
    assert (
        "Mcp-Plus-Plus/tests-py/fixtures/valid/swissknife_mcp_plus_plus_interop_descriptor.json"
        in src
    )
    assert "VAI-665" in src
    assert "VAIOS-G704" in src
    assert "agent_identity" in src
    assert "allowed_surfaces" in src
    assert "arguments_hash" in src


def test_swissknife_control_surface_and_interaction_envelope_validate_for_mcp_plus_plus() -> None:
    control_schema = read_json("swissknife/contracts/control_surface_contract.schema.json")
    envelope_schema = read_json("swissknife/contracts/interaction_envelope.schema.json")

    Draft202012Validator(control_schema).validate(
        swissknife_mcp_plus_plus_control_surface_payload()
    )
    Draft202012Validator(envelope_schema).validate(
        swissknife_mcp_plus_plus_interaction_envelope()
    )


@pytest.fixture(scope="module")
def mcp_idl_validator():
    if not MCP_PLUS_PLUS_TESTS_PY.is_dir():
        pytest.skip("Mcp-Plus-Plus submodule not checked out in this worktree")
    sys.path.insert(0, str(MCP_PLUS_PLUS_TESTS_PY))
    from validators.mcp_idl import MCPIDLValidator  # type: ignore

    return MCPIDLValidator()


def test_mcp_plus_plus_idl_validator_accepts_swissknife_interop_descriptor(mcp_idl_validator) -> None:
    fixture = read_json(
        "Mcp-Plus-Plus/tests-py/fixtures/valid/swissknife_mcp_plus_plus_interop_descriptor.json"
    )
    assert fixture["task_id"] == "VAI-665"
    assert fixture["goal_id"] == "VAIOS-G704"
    assert fixture["goal_packet"] == "goal_packet/interoperability/swissknife/06921590135c"
    assert fixture["interface_contract"] == "interface contract swissknife Mcp-Plus-Plus"

    descriptor = fixture["payload"]
    assert {method["name"] for method in descriptor["methods"]} == MCP_PLUS_PLUS_INTEROP_OPERATIONS

    result = mcp_idl_validator.validate_descriptor(descriptor)

    assert result.is_valid, result.errors
    assert result.message_type == "interface_descriptor"
    assert "interface_cid" in result.metadata


def test_mcp_idl_descriptor_fixture_still_validates_with_shared_validator(mcp_idl_validator) -> None:
    fixture = read_json("Mcp-Plus-Plus/tests-py/fixtures/valid/mcp_idl_descriptor.json")
    assert fixture["swissknife_interop_ref"] == (
        "Mcp-Plus-Plus/tests-py/fixtures/valid/swissknife_mcp_plus_plus_interop_descriptor.json"
    )

    result = mcp_idl_validator.validate_descriptor(fixture["payload"])

    assert result.is_valid, result.errors
    assert result.metadata.get("interface_cid")


def test_docs_discovery_and_heap_record_objective_validation_repair() -> None:
    docs = read_text("docs/integration/swissknife-mcp_plus_plus.md")
    discovery = read_text("data/virtual_ai_os/discovery/2026-07-08-vai-665-validation-repair.md")
    gap = read_text("data/virtual_ai_os/discovery/2026-07-08-vai-665-objective-gap-57359897bf4f.md")
    heap = read_text("implementation_plan/docs/23-virtual-ai-os-objective-goal-heap.md")

    required_terms = [
        "VAI-665",
        "VAIOS-G704",
        "goal_packet/interoperability/swissknife/06921590135c",
        "objective validation repair",
        "interface contract swissknife Mcp-Plus-Plus",
        "tests/integration/test_swissknife_mcp_plus_plus_interop.py",
        "swissknife/src/services/mcp/mcp-plus-plus-interop-descriptor.ts",
        "swissknife/contracts/control_surface_contract.schema.json",
        "swissknife/contracts/interaction_envelope.schema.json",
        "Mcp-Plus-Plus/tests-py/fixtures/valid/mcp_idl_descriptor.json",
    ]
    for content in (docs, discovery, heap):
        for term in required_terms:
            assert term in content, f"missing {term!r}"
    for goal_id in GOAL_PACKET_GOALS:
        assert goal_id in discovery
        assert goal_id in heap
    assert "VAIOS-G704" in gap
