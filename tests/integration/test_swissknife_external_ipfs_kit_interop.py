"""SwissKnife/external/ipfs_kit interoperability regression tests for MGW-572."""

from __future__ import annotations

import json
import sys
from pathlib import Path

from jsonschema import Draft202012Validator

REPO_ROOT = Path(__file__).resolve().parents[2]
SRC_ROOT = REPO_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from handsfree.swissknife_ipfs_kit_interop import (  # noqa: E402
    GOAL_ID,
    GOAL_PACKET,
    REQUIRED_BUCKET_VFS_MCP_TOOLS,
    REQUIRED_DAG_PB_MESSAGES,
    REQUIRED_DEPRECATIONS_REPORT_KEYS,
    REQUIRED_FIX_MCP_SCHEMA_PATHS,
    REQUIRED_SWISSKNIFE_IPFS_KIT_OPERATIONS,
    SwissKnifeIPFSKitInteropError,
    build_swissknife_ipfs_kit_handoff,
    discover_ipfs_kit_mcp_schema_contract,
)

IPFS_KIT_ROOT = REPO_ROOT / "external" / "ipfs_kit"
DESCRIPTOR_TS_PATH = "swissknife/src/services/mcp/ipfs-kit-mcp-schema-interop-descriptor.ts"

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


def swissknife_ipfs_kit_control_surface_payload() -> dict:
    """Python mirror of buildSwissKnifeIPFSKitControlSurfaceContract()."""
    policy_bundle_ref = {
        "policy_id": "policy:swissknife:ipfs-kit-mcp-schema-interop",
        "policy_cid": "local:swissknife:ipfs-kit-mcp-schema-interop",
        "version": "0.1.0",
        "scope": "swissknife-ipfs-kit-mcp-schema-interop",
        "source": "system_default",
    }
    logic_binding = {
        "binding_id": "binding:swissknife-ipfs-kit-bucket-vfs",
        "policy_bundle_ref": policy_bundle_ref,
        "compiled_policy_cid": "local:swissknife:ipfs-kit-mcp-schema-interop",
        "ir_version": "0.1.0",
        "frame_fact_kinds": ["actor", "surface", "event", "method", "context"],
        "surface_refs": ["agent", "mcp_server", "remote_client"],
        "method_refs": [
            "ipfs_kit.bucket_vfs.cross_query",
            "ipfs_kit.mcp_schema.validate_deprecations_report",
        ],
        "norm_refs": ["agent_identity", "allowed_surfaces", "arguments_hash"],
        "compiled_artifact_refs": [
            {
                "artifact_type": "deontic_policy",
                "cid": "local:swissknife:ipfs-kit-mcp-schema-interop",
                "media_type": "application/json",
                "description": "interface contract swissknife external/ipfs_kit",
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
                    "id": "swissknife.ipfs_kit.data-service",
                    "kind": "data_service",
                    "event_types": ["cross_query", "validate_deprecations_report"],
                    "intent_resolver": "swissknife.ipfs_kit.intent_resolver",
                    "confidence_policy": {"min_confidence": 0.85, "clarify_below": 0.6},
                    "logic_bindings": [logic_binding],
                }
            ],
            "intent_bindings": [
                {
                    "intent": "swissknife.ipfs_kit.cross_query",
                    "method": "ipfs_kit.bucket_vfs.cross_query",
                    "target_ref": "ipfs_kit:bucket_vfs",
                    "allowed_surfaces": ["agent", "mcp_server", "remote_client"],
                    "required_context_facts": ["agent_identity", "bucket_name"],
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
                "state_frames": ["ipfs_kit_bucket_vfs_session"],
                "time_context": True,
                "location_context": False,
                "device_context": False,
                "agent_identity": True,
            },
            "conflict_resolution": {
                "default": "require_confirmation",
                "requires_explanation": True,
                "requires_user_confirmation_for": [
                    "bucket_delete",
                    "bucket_export_car",
                ],
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


def swissknife_ipfs_kit_interaction_envelope() -> dict:
    """Python mirror of buildSwissKnifeIPFSKitInteractionEnvelope()."""
    policy_bundle_ref = {
        "policy_id": "policy:swissknife:ipfs-kit-mcp-schema-interop",
        "policy_cid": "local:swissknife:ipfs-kit-mcp-schema-interop",
        "version": "0.1.0",
        "scope": "swissknife-ipfs-kit-mcp-schema-interop",
        "source": "system_default",
    }
    return {
        "interaction_id": "interaction:swissknife-ipfs-kit:cross-query:1",
        "surface": "data_service",
        "surface_event": "cross_query",
        "raw_payload": {
            "bucket_name": "swissknife-ipfs-kit-bucket",
            "query": "SELECT * FROM files",
        },
        "normalized_intent": {
            "intent": "swissknife.ipfs_kit.cross_query",
            "method": "ipfs_kit.bucket_vfs.cross_query",
            "target_ref": "ipfs_kit:bucket_vfs",
            "arguments": {
                "bucket_name": "swissknife-ipfs-kit-bucket",
                "arguments_hash": "sha256:swissknife-ipfs-kit-cross-query",
            },
            "confidence": 0.95,
        },
        "actor": {
            "type": "agent",
            "id": "swissknife:ipfs-kit-operator-agent",
            "delegation_chain": ["ucan:swissknife-ipfs-kit-mcp-schema-interop"],
        },
        "context": {
            "local_time": "2026-07-08T00:00:00Z",
            "state_frames": ["ipfs_kit_bucket_vfs_session"],
            "device_mode": "server",
            "platform": "ipfs_kit",
            "location_context": {},
            "device_context": {
                "bucket_vfs_mcp_tools": list(REQUIRED_BUCKET_VFS_MCP_TOOLS),
            },
        },
        "control_surface_contract_ref": "swissknife/contracts/control_surface_contract.schema.json",
        "policy_bundle_ref": policy_bundle_ref,
        "compiled_policy_cid": "local:swissknife:ipfs-kit-mcp-schema-interop",
        "logic_bindings": [
            {
                "binding_id": "binding:swissknife-ipfs-kit-bucket-vfs",
                "policy_bundle_ref": policy_bundle_ref,
                "compiled_policy_cid": "local:swissknife:ipfs-kit-mcp-schema-interop",
                "surface_ref": "data_service",
                "method_ref": "ipfs_kit.bucket_vfs.cross_query",
                "norm_refs": ["agent_identity", "allowed_surfaces", "arguments_hash"],
            }
        ],
    }


def test_ipfs_kit_mcp_schema_descriptors_exist_on_disk() -> None:
    expected_paths = [
        "external/ipfs_kit/archive/archive_clutter/fix_scripts/fix_mcp_schema.py",
        "external/ipfs_kit/backup/archive_clutter/fix_scripts/fix_mcp_schema.py",
        "external/ipfs_kit/backup/patches/fixes/fix_mcp_schema.py",
        "external/ipfs_kit/data/deprecations_report.schema.json",
        "external/ipfs_kit/docs/implementation/BUCKET_VFS_INTERFACES_COMPLETE.md",
        "external/ipfs_kit/docs/py-ipld-dag-pb/ipld_dag_pb/dag-pb.proto",
    ]
    for relative_path in expected_paths:
        assert (REPO_ROOT / relative_path).is_file(), f"missing {relative_path}"


def test_discover_ipfs_kit_mcp_schema_contract_finds_expected_surface() -> None:
    contract = discover_ipfs_kit_mcp_schema_contract(IPFS_KIT_ROOT)

    assert set(REQUIRED_BUCKET_VFS_MCP_TOOLS).issubset(set(contract.bucket_vfs_mcp_tools))
    assert set(REQUIRED_DAG_PB_MESSAGES).issubset(set(contract.dag_pb_messages))
    assert set(REQUIRED_DEPRECATIONS_REPORT_KEYS).issubset(
        set(contract.deprecations_report_required_keys)
    )
    for relative_path in REQUIRED_FIX_MCP_SCHEMA_PATHS:
        assert any(path.endswith(relative_path) for path in contract.fix_mcp_schema_paths)
    assert contract.deprecations_report_schema_path.endswith(
        "data/deprecations_report.schema.json"
    )
    assert contract.bucket_vfs_doc_path.endswith(
        "docs/implementation/BUCKET_VFS_INTERFACES_COMPLETE.md"
    )
    assert contract.dag_pb_proto_path.endswith("docs/py-ipld-dag-pb/ipld_dag_pb/dag-pb.proto")


def test_discover_ipfs_kit_mcp_schema_contract_raises_for_missing_root(tmp_path) -> None:
    missing_root = tmp_path / "does-not-exist"
    try:
        discover_ipfs_kit_mcp_schema_contract(missing_root)
    except SwissKnifeIPFSKitInteropError as exc:
        assert "not found" in str(exc)
    else:
        raise AssertionError("expected SwissKnifeIPFSKitInteropError")


def test_build_swissknife_ipfs_kit_handoff_is_deterministic() -> None:
    first = build_swissknife_ipfs_kit_handoff(IPFS_KIT_ROOT)
    second = build_swissknife_ipfs_kit_handoff(IPFS_KIT_ROOT)

    assert first.as_dict() == second.as_dict()
    assert first.interface_contract == "interface contract swissknife external/ipfs_kit"
    assert first.goal_id == GOAL_ID == "VAIOS-G703"
    assert first.goal_packet == GOAL_PACKET
    assert first.source_repository == "swissknife"
    assert first.target_repository == "external/ipfs_kit"
    assert first.content_cid.startswith("sha256:")
    assert first.content_cid == f"sha256:{first.payload_sha256}"
    assert first.payload_size_bytes > 0
    assert set(REQUIRED_BUCKET_VFS_MCP_TOOLS).issubset(set(first.bucket_vfs_mcp_tools))
    assert set(REQUIRED_DAG_PB_MESSAGES).issubset(set(first.dag_pb_messages))
    assert set(first.required_swissknife_operations) == set(
        REQUIRED_SWISSKNIFE_IPFS_KIT_OPERATIONS
    )


def test_swissknife_descriptor_module_exports_interop_contract() -> None:
    src = read_text(DESCRIPTOR_TS_PATH)

    assert "export const SWISSKNIFE_IPFS_KIT_INTEROP_INTERFACE" in src
    assert "export const SWISSKNIFE_IPFS_KIT_INTEROP_DESCRIPTOR" in src
    assert "'interface contract swissknife external/ipfs_kit'" in src
    assert "'goal_packet/interoperability/swissknife/06921590135c'" in src
    assert "export function registerSwissKnifeIPFSKitMCPSchemaInterop" in src
    assert "export function createMCPPlusPlusClientWithSwissKnifeIPFSKitInterop" in src
    assert "export function buildSwissKnifeIPFSKitControlSurfaceContract" in src
    assert "export function buildSwissKnifeIPFSKitInteractionEnvelope" in src

    for goal_id in GOAL_PACKET_GOALS:
        assert goal_id in src
    for operation in REQUIRED_SWISSKNIFE_IPFS_KIT_OPERATIONS:
        assert operation in src
    for tool in REQUIRED_BUCKET_VFS_MCP_TOOLS:
        assert tool in src
    for message in REQUIRED_DAG_PB_MESSAGES:
        assert message in src

    assert "swissknife/contracts/control_surface_contract.schema.json" in src
    assert "swissknife/contracts/interaction_envelope.schema.json" in src
    assert "swissknife/contracts/mediation_receipt.schema.json" in src
    assert "external/ipfs_kit/archive/archive_clutter/fix_scripts/fix_mcp_schema.py" in src
    assert "external/ipfs_kit/backup/archive_clutter/fix_scripts/fix_mcp_schema.py" in src
    assert "external/ipfs_kit/backup/patches/fixes/fix_mcp_schema.py" in src
    assert "external/ipfs_kit/data/deprecations_report.schema.json" in src
    assert "external/ipfs_kit/docs/implementation/BUCKET_VFS_INTERFACES_COMPLETE.md" in src
    assert "external/ipfs_kit/docs/py-ipld-dag-pb/ipld_dag_pb/dag-pb.proto" in src
    assert "MGW-572" in src
    assert "VAIOS-G703" in src
    assert "agent_identity" in src
    assert "allowed_surfaces" in src
    assert "arguments_hash" in src


def test_swissknife_control_surface_and_interaction_envelope_validate_for_ipfs_kit() -> None:
    control_schema = read_json("swissknife/contracts/control_surface_contract.schema.json")
    envelope_schema = read_json("swissknife/contracts/interaction_envelope.schema.json")

    Draft202012Validator(control_schema).validate(swissknife_ipfs_kit_control_surface_payload())
    Draft202012Validator(envelope_schema).validate(swissknife_ipfs_kit_interaction_envelope())


def test_docs_discovery_and_heap_record_objective_validation_repair() -> None:
    docs = read_text("docs/integration/swissknife-external_ipfs_kit.md")
    discovery = read_text(
        "data/meta_glasses_display_widgets/discovery/2026-07-08-mgw-572-objective-validation-repair.md"
    )
    gap = read_text(
        "data/meta_glasses_display_widgets/discovery/2026-07-08-mgw-572-objective-gap-f463532ba4e3.md"
    )
    heap = read_text("implementation_plan/docs/23-virtual-ai-os-objective-goal-heap.md")

    required_terms = [
        "MGW-572",
        "VAIOS-G703",
        "goal_packet/interoperability/swissknife/06921590135c",
        "objective validation repair",
        "interface contract swissknife external/ipfs_kit",
        "tests/integration/test_swissknife_external_ipfs_kit_interop.py",
        DESCRIPTOR_TS_PATH,
        "src/handsfree/swissknife_ipfs_kit_interop.py",
        "swissknife/contracts/control_surface_contract.schema.json",
        "swissknife/contracts/interaction_envelope.schema.json",
        "external/ipfs_kit/archive/archive_clutter/fix_scripts/fix_mcp_schema.py",
        "external/ipfs_kit/backup/archive_clutter/fix_scripts/fix_mcp_schema.py",
        "external/ipfs_kit/backup/patches/fixes/fix_mcp_schema.py",
        "external/ipfs_kit/data/deprecations_report.schema.json",
    ]
    for content in (docs, discovery, heap):
        for term in required_terms:
            assert term in content, f"missing {term!r}"
    for goal_id in GOAL_PACKET_GOALS:
        assert goal_id in discovery
        assert goal_id in heap
    assert "VAIOS-G703" in gap
