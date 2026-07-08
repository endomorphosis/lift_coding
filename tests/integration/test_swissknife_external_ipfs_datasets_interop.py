"""SwissKnife/external/ipfs_datasets interoperability regression tests for MGW-571."""

from __future__ import annotations

import json
import sys
from pathlib import Path

from jsonschema import Draft202012Validator

REPO_ROOT = Path(__file__).resolve().parents[2]
SRC_ROOT = REPO_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from handsfree.swissknife_ipfs_datasets_interop import (  # noqa: E402
    GOAL_ID,
    GOAL_PACKET,
    REQUIRED_BUCKET_VFS_CLI_COMMANDS,
    REQUIRED_BUCKET_VFS_MCP_TOOLS,
    REQUIRED_DEPRECATIONS_REPORT_KEYS,
    REQUIRED_SWISSKNIFE_IPFS_DATASETS_OPERATIONS,
    REQUIRED_UNIFIED_BUCKET_BACKENDS,
    REQUIRED_UNIFIED_BUCKET_CLASSES,
    REQUIRED_UNIFIED_BUCKET_METHODS,
    SwissKnifeIPFSDatasetsInteropError,
    build_swissknife_ipfs_datasets_handoff,
    discover_ipfs_datasets_bucket_vfs_contract,
)

IPFS_DATASETS_ROOT = REPO_ROOT / "external" / "ipfs_datasets"
DESCRIPTOR_TS_PATH = "swissknife/src/services/mcp/ipfs-datasets-bucket-vfs-interop-descriptor.ts"

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


def swissknife_ipfs_datasets_control_surface_payload() -> dict:
    """Python mirror of buildSwissKnifeIPFSDatasetsControlSurfaceContract()."""
    policy_bundle_ref = {
        "policy_id": "policy:swissknife:ipfs-datasets-bucket-vfs-interop",
        "policy_cid": "local:swissknife:ipfs-datasets-bucket-vfs-interop",
        "version": "0.1.0",
        "scope": "swissknife-ipfs-datasets-bucket-vfs-interop",
        "source": "system_default",
    }
    logic_binding = {
        "binding_id": "binding:swissknife-ipfs-datasets-bucket-vfs",
        "policy_bundle_ref": policy_bundle_ref,
        "compiled_policy_cid": "local:swissknife:ipfs-datasets-bucket-vfs-interop",
        "ir_version": "0.1.0",
        "frame_fact_kinds": ["actor", "surface", "event", "method", "context"],
        "surface_refs": ["agent", "mcp_server", "remote_client"],
        "method_refs": [
            "ipfs_datasets.bucket_vfs.cross_query",
            "ipfs_datasets.unified_bucket.create_backend_bucket",
            "ipfs_datasets.deprecations.validate_report",
        ],
        "norm_refs": ["agent_identity", "allowed_surfaces", "arguments_hash"],
        "compiled_artifact_refs": [
            {
                "artifact_type": "deontic_policy",
                "cid": "local:swissknife:ipfs-datasets-bucket-vfs-interop",
                "media_type": "application/json",
                "description": "interface contract swissknife external/ipfs_datasets",
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
                    "id": "swissknife.ipfs_datasets.data-service",
                    "kind": "data_service",
                    "event_types": [
                        "cross_query",
                        "create_backend_bucket",
                        "validate_report",
                    ],
                    "intent_resolver": "swissknife.ipfs_datasets.intent_resolver",
                    "confidence_policy": {"min_confidence": 0.85, "clarify_below": 0.6},
                    "logic_bindings": [logic_binding],
                }
            ],
            "intent_bindings": [
                {
                    "intent": "swissknife.ipfs_datasets.cross_query",
                    "method": "ipfs_datasets.bucket_vfs.cross_query",
                    "target_ref": "ipfs_datasets:bucket_vfs",
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
                "state_frames": ["ipfs_datasets_bucket_vfs_session"],
                "time_context": True,
                "location_context": False,
                "device_context": False,
                "agent_identity": True,
            },
            "conflict_resolution": {
                "default": "require_confirmation",
                "requires_explanation": True,
                "requires_user_confirmation_for": ["bucket_delete", "bucket_export_car"],
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


def swissknife_ipfs_datasets_interaction_envelope() -> dict:
    """Python mirror of buildSwissKnifeIPFSDatasetsInteractionEnvelope()."""
    policy_bundle_ref = {
        "policy_id": "policy:swissknife:ipfs-datasets-bucket-vfs-interop",
        "policy_cid": "local:swissknife:ipfs-datasets-bucket-vfs-interop",
        "version": "0.1.0",
        "scope": "swissknife-ipfs-datasets-bucket-vfs-interop",
        "source": "system_default",
    }
    return {
        "interaction_id": "interaction:swissknife-ipfs-datasets:cross-query:1",
        "surface": "data_service",
        "surface_event": "cross_query",
        "raw_payload": {
            "bucket_name": "swissknife-ipfs-datasets-bucket",
            "query": "SELECT bucket_name, file_path, cid FROM files",
        },
        "normalized_intent": {
            "intent": "swissknife.ipfs_datasets.cross_query",
            "method": "ipfs_datasets.bucket_vfs.cross_query",
            "target_ref": "ipfs_datasets:bucket_vfs",
            "arguments": {
                "bucket_name": "swissknife-ipfs-datasets-bucket",
                "arguments_hash": "sha256:swissknife-ipfs-datasets-cross-query",
            },
            "confidence": 0.95,
        },
        "actor": {
            "type": "agent",
            "id": "swissknife:ipfs-datasets-operator-agent",
            "delegation_chain": ["ucan:swissknife-ipfs-datasets-bucket-vfs-interop"],
        },
        "context": {
            "local_time": "2026-07-08T00:00:00Z",
            "state_frames": ["ipfs_datasets_bucket_vfs_session"],
            "device_mode": "server",
            "platform": "ipfs_datasets",
            "location_context": {},
            "device_context": {
                "bucket_vfs_mcp_tools": list(REQUIRED_BUCKET_VFS_MCP_TOOLS),
                "unified_bucket_backends": list(REQUIRED_UNIFIED_BUCKET_BACKENDS),
            },
        },
        "control_surface_contract_ref": "swissknife/contracts/control_surface_contract.schema.json",
        "policy_bundle_ref": policy_bundle_ref,
        "compiled_policy_cid": "local:swissknife:ipfs-datasets-bucket-vfs-interop",
        "logic_bindings": [
            {
                "binding_id": "binding:swissknife-ipfs-datasets-bucket-vfs",
                "policy_bundle_ref": policy_bundle_ref,
                "compiled_policy_cid": "local:swissknife:ipfs-datasets-bucket-vfs-interop",
                "surface_ref": "data_service",
                "method_ref": "ipfs_datasets.bucket_vfs.cross_query",
                "norm_refs": ["agent_identity", "allowed_surfaces", "arguments_hash"],
            }
        ],
    }


def test_ipfs_datasets_bucket_vfs_descriptors_exist_on_disk() -> None:
    expected_paths = [
        "external/ipfs_datasets/.tools/ipfs_kit_py/data/deprecations_report.schema.json",
        (
            "external/ipfs_datasets/.tools/ipfs_kit_py/docs/implementation/"
            "BUCKET_VFS_INTERFACES_COMPLETE.md"
        ),
        "external/ipfs_datasets/.tools/ipfs_kit_py/examples/demo_bucket_vfs_interfaces.py",
        "external/ipfs_datasets/.tools/ipfs_kit_py/examples/demo_unified_bucket_interface.py",
    ]
    for relative_path in expected_paths:
        assert (REPO_ROOT / relative_path).is_file(), f"missing {relative_path}"


def test_discover_ipfs_datasets_bucket_vfs_contract_finds_expected_surface() -> None:
    contract = discover_ipfs_datasets_bucket_vfs_contract(IPFS_DATASETS_ROOT)

    assert set(REQUIRED_DEPRECATIONS_REPORT_KEYS).issubset(
        set(contract.deprecations_report_required_keys)
    )
    assert set(REQUIRED_BUCKET_VFS_MCP_TOOLS).issubset(set(contract.bucket_vfs_mcp_tools))
    assert set(REQUIRED_BUCKET_VFS_CLI_COMMANDS).issubset(
        set(contract.bucket_vfs_cli_commands)
    )
    assert {"DemoBucket"}.issubset(set(contract.demo_classes))
    assert {"demo_cli_interface", "demo_mcp_api", "build_demo_report"}.issubset(
        set(contract.demo_functions)
    )
    assert set(REQUIRED_UNIFIED_BUCKET_CLASSES).issubset(
        set(contract.unified_bucket_imports)
    )
    assert set(REQUIRED_UNIFIED_BUCKET_METHODS).issubset(
        set(contract.unified_bucket_methods)
    )
    assert set(REQUIRED_UNIFIED_BUCKET_BACKENDS).issubset(
        set(contract.unified_bucket_backends)
    )
    assert contract.deprecations_report_schema_path.endswith(
        ".tools/ipfs_kit_py/data/deprecations_report.schema.json"
    )
    assert contract.bucket_vfs_doc_path.endswith(
        ".tools/ipfs_kit_py/docs/implementation/BUCKET_VFS_INTERFACES_COMPLETE.md"
    )
    assert contract.bucket_vfs_demo_path.endswith(
        ".tools/ipfs_kit_py/examples/demo_bucket_vfs_interfaces.py"
    )
    assert contract.unified_bucket_demo_path.endswith(
        ".tools/ipfs_kit_py/examples/demo_unified_bucket_interface.py"
    )


def test_discover_ipfs_datasets_bucket_vfs_contract_raises_for_missing_root(tmp_path) -> None:
    missing_root = tmp_path / "does-not-exist"
    try:
        discover_ipfs_datasets_bucket_vfs_contract(missing_root)
    except SwissKnifeIPFSDatasetsInteropError as exc:
        assert "not found" in str(exc)
    else:
        raise AssertionError("expected SwissKnifeIPFSDatasetsInteropError")


def test_build_swissknife_ipfs_datasets_handoff_is_deterministic() -> None:
    first = build_swissknife_ipfs_datasets_handoff(IPFS_DATASETS_ROOT)
    second = build_swissknife_ipfs_datasets_handoff(IPFS_DATASETS_ROOT)

    assert first.as_dict() == second.as_dict()
    assert first.interface_contract == "interface contract swissknife external/ipfs_datasets"
    assert first.goal_id == GOAL_ID == "VAIOS-G702"
    assert first.goal_packet == GOAL_PACKET
    assert first.source_repository == "swissknife"
    assert first.target_repository == "external/ipfs_datasets"
    assert first.content_cid.startswith("sha256:")
    assert first.content_cid == f"sha256:{first.payload_sha256}"
    assert first.payload_size_bytes > 0
    assert set(REQUIRED_BUCKET_VFS_MCP_TOOLS).issubset(set(first.bucket_vfs_mcp_tools))
    assert set(REQUIRED_BUCKET_VFS_CLI_COMMANDS).issubset(
        set(first.bucket_vfs_cli_commands)
    )
    assert set(REQUIRED_UNIFIED_BUCKET_BACKENDS).issubset(
        set(first.unified_bucket_backends)
    )
    assert set(first.required_swissknife_operations) == set(
        REQUIRED_SWISSKNIFE_IPFS_DATASETS_OPERATIONS
    )


def test_swissknife_descriptor_module_exports_interop_contract() -> None:
    src = read_text(DESCRIPTOR_TS_PATH)

    assert "export const SWISSKNIFE_IPFS_DATASETS_INTEROP_INTERFACE" in src
    assert "export const SWISSKNIFE_IPFS_DATASETS_INTEROP_DESCRIPTOR" in src
    assert "'interface contract swissknife external/ipfs_datasets'" in src
    assert "'goal_packet/interoperability/swissknife/06921590135c'" in src
    assert "export function registerSwissKnifeIPFSDatasetsBucketVFSInterop" in src
    assert "export function createMCPPlusPlusClientWithSwissKnifeIPFSDatasetsInterop" in src
    assert "export function buildSwissKnifeIPFSDatasetsControlSurfaceContract" in src
    assert "export function buildSwissKnifeIPFSDatasetsInteractionEnvelope" in src

    for goal_id in GOAL_PACKET_GOALS:
        assert goal_id in src
    for operation in REQUIRED_SWISSKNIFE_IPFS_DATASETS_OPERATIONS:
        assert operation in src
    for tool in REQUIRED_BUCKET_VFS_MCP_TOOLS:
        assert tool in src
    for backend in REQUIRED_UNIFIED_BUCKET_BACKENDS:
        assert backend in src

    assert "swissknife/contracts/control_surface_contract.schema.json" in src
    assert "swissknife/contracts/interaction_envelope.schema.json" in src
    assert "swissknife/contracts/mediation_receipt.schema.json" in src
    assert (
        "external/ipfs_datasets/.tools/ipfs_kit_py/data/deprecations_report.schema.json"
        in src
    )
    assert (
        "external/ipfs_datasets/.tools/ipfs_kit_py/docs/implementation/"
        "BUCKET_VFS_INTERFACES_COMPLETE.md"
    ) in src
    assert (
        "external/ipfs_datasets/.tools/ipfs_kit_py/examples/demo_bucket_vfs_interfaces.py"
        in src
    )
    assert (
        "external/ipfs_datasets/.tools/ipfs_kit_py/examples/demo_unified_bucket_interface.py"
        in src
    )
    assert "MGW-571" in src
    assert "VAIOS-G702" in src
    assert "agent_identity" in src
    assert "allowed_surfaces" in src
    assert "arguments_hash" in src


def test_swissknife_control_surface_and_interaction_envelope_validate_for_ipfs_datasets() -> None:
    control_schema = read_json("swissknife/contracts/control_surface_contract.schema.json")
    envelope_schema = read_json("swissknife/contracts/interaction_envelope.schema.json")

    Draft202012Validator(control_schema).validate(
        swissknife_ipfs_datasets_control_surface_payload()
    )
    Draft202012Validator(envelope_schema).validate(
        swissknife_ipfs_datasets_interaction_envelope()
    )


def test_docs_discovery_and_heap_record_objective_validation_repair() -> None:
    docs = read_text("docs/integration/swissknife-external_ipfs_datasets.md")
    discovery = read_text(
        "data/meta_glasses_display_widgets/discovery/"
        "2026-07-08-mgw-571-objective-validation-repair.md"
    )
    gap = read_text(
        "data/meta_glasses_display_widgets/discovery/"
        "2026-07-08-mgw-571-objective-gap-c21adb3eb488.md"
    )
    heap = read_text("implementation_plan/docs/23-virtual-ai-os-objective-goal-heap.md")

    required_terms = [
        "MGW-571",
        "VAIOS-G702",
        "goal_packet/interoperability/swissknife/06921590135c",
        "objective validation repair",
        "interface contract swissknife external/ipfs_datasets",
        "tests/integration/test_swissknife_external_ipfs_datasets_interop.py",
        DESCRIPTOR_TS_PATH,
        "src/handsfree/swissknife_ipfs_datasets_interop.py",
        "swissknife/contracts/control_surface_contract.schema.json",
        "swissknife/contracts/interaction_envelope.schema.json",
        "external/ipfs_datasets/.tools/ipfs_kit_py/data/deprecations_report.schema.json",
        (
            "external/ipfs_datasets/.tools/ipfs_kit_py/docs/implementation/"
            "BUCKET_VFS_INTERFACES_COMPLETE.md"
        ),
        "external/ipfs_datasets/.tools/ipfs_kit_py/examples/demo_bucket_vfs_interfaces.py",
        "external/ipfs_datasets/.tools/ipfs_kit_py/examples/demo_unified_bucket_interface.py",
    ]
    for content in (docs, discovery, heap):
        for term in required_terms:
            assert term in content, f"missing {term!r}"
    for goal_id in GOAL_PACKET_GOALS:
        assert goal_id in discovery
        assert goal_id in heap
    assert "VAIOS-G702" in gap
