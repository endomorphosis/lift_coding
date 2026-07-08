"""SwissKnife/external/ipfs_accelerate interoperability regression tests for VAI-662."""

from __future__ import annotations

import json
import sys
from pathlib import Path

from jsonschema import Draft202012Validator

REPO_ROOT = Path(__file__).resolve().parents[2]
SRC_ROOT = REPO_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from handsfree.swissknife_ipfs_accelerate_interop import (  # noqa: E402
    GOAL_ID,
    GOAL_PACKET,
    REQUIRED_SWISSKNIFE_DUCKDB_OPERATIONS,
    REQUIRED_TIME_SERIES_TABLES,
    SwissKnifeIPFSAccelerateInteropError,
    build_swissknife_duckdb_handoff,
    discover_ipfs_accelerate_duckdb_contract,
)

IPFS_ACCELERATE_ROOT = REPO_ROOT / "external" / "ipfs_accelerate"
DESCRIPTOR_TS_PATH = "swissknife/src/services/mcp/ipfs-accelerate-duckdb-interop-descriptor.ts"

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


def swissknife_ipfs_accelerate_control_surface_payload() -> dict:
    """Python mirror of buildSwissKnifeIPFSAccelerateControlSurfaceContract()."""
    policy_bundle_ref = {
        "policy_id": "policy:swissknife:ipfs-accelerate-duckdb-interop",
        "policy_cid": "local:swissknife:ipfs-accelerate-duckdb-interop",
        "version": "0.1.0",
        "scope": "swissknife-ipfs-accelerate-duckdb-interop",
        "source": "system_default",
    }
    logic_binding = {
        "binding_id": "binding:swissknife-ipfs-accelerate-benchmark-schema",
        "policy_bundle_ref": policy_bundle_ref,
        "compiled_policy_cid": "local:swissknife:ipfs-accelerate-duckdb-interop",
        "ir_version": "0.1.0",
        "frame_fact_kinds": ["actor", "surface", "event", "method", "context"],
        "surface_refs": ["agent", "mcp_server", "remote_client"],
        "method_refs": [
            "accelerate.duckdb.get_performance_results",
            "accelerate.duckdb.check_schema",
        ],
        "norm_refs": ["agent_identity", "allowed_surfaces", "arguments_hash"],
        "compiled_artifact_refs": [
            {
                "artifact_type": "deontic_policy",
                "cid": "local:swissknife:ipfs-accelerate-duckdb-interop",
                "media_type": "application/json",
                "description": "interface contract swissknife external/ipfs_accelerate",
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
                    "id": "swissknife.ipfs_accelerate.data-service",
                    "kind": "data_service",
                    "event_types": ["get_performance_results", "check_schema"],
                    "intent_resolver": "swissknife.ipfs_accelerate.intent_resolver",
                    "confidence_policy": {"min_confidence": 0.85, "clarify_below": 0.6},
                    "logic_bindings": [logic_binding],
                }
            ],
            "intent_bindings": [
                {
                    "intent": "swissknife.ipfs_accelerate.get_performance_results",
                    "method": "accelerate.duckdb.get_performance_results",
                    "target_ref": "ipfs_accelerate:duckdb_benchmark_schema",
                    "allowed_surfaces": ["agent", "mcp_server", "remote_client"],
                    "required_context_facts": ["agent_identity", "benchmark_db_path"],
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
                "state_frames": ["ipfs_accelerate_benchmark_session"],
                "time_context": True,
                "location_context": False,
                "device_context": False,
                "agent_identity": True,
            },
            "conflict_resolution": {
                "default": "require_confirmation",
                "requires_explanation": True,
                "requires_user_confirmation_for": [
                    "create_performance_tables",
                    "create_common_tables",
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


def swissknife_ipfs_accelerate_interaction_envelope() -> dict:
    """Python mirror of buildSwissKnifeIPFSAccelerateInteractionEnvelope()."""
    policy_bundle_ref = {
        "policy_id": "policy:swissknife:ipfs-accelerate-duckdb-interop",
        "policy_cid": "local:swissknife:ipfs-accelerate-duckdb-interop",
        "version": "0.1.0",
        "scope": "swissknife-ipfs-accelerate-duckdb-interop",
        "source": "system_default",
    }
    return {
        "interaction_id": "interaction:swissknife-ipfs-accelerate:get-performance-results:1",
        "surface": "data_service",
        "surface_event": "get_performance_results",
        "raw_payload": {
            "benchmark_db_path": "local:duckdb:benchmark_db.duckdb",
            "table": "performance_baselines",
        },
        "normalized_intent": {
            "intent": "swissknife.ipfs_accelerate.get_performance_results",
            "method": "accelerate.duckdb.get_performance_results",
            "target_ref": "ipfs_accelerate:duckdb_benchmark_schema",
            "arguments": {
                "table": "performance_baselines",
                "arguments_hash": "sha256:swissknife-ipfs-accelerate-get-performance-results",
            },
            "confidence": 0.95,
        },
        "actor": {
            "type": "agent",
            "id": "swissknife:ipfs-accelerate-operator-agent",
            "delegation_chain": ["ucan:swissknife-ipfs-accelerate-duckdb-interop"],
        },
        "context": {
            "local_time": "2026-07-08T00:00:00Z",
            "state_frames": ["ipfs_accelerate_benchmark_session"],
            "device_mode": "server",
            "platform": "ipfs_accelerate",
            "location_context": {},
            "device_context": {
                "time_series_tables": list(REQUIRED_TIME_SERIES_TABLES),
            },
        },
        "control_surface_contract_ref": "swissknife/contracts/control_surface_contract.schema.json",
        "policy_bundle_ref": policy_bundle_ref,
        "compiled_policy_cid": "local:swissknife:ipfs-accelerate-duckdb-interop",
        "logic_bindings": [
            {
                "binding_id": "binding:swissknife-ipfs-accelerate-benchmark-schema",
                "policy_bundle_ref": policy_bundle_ref,
                "compiled_policy_cid": "local:swissknife:ipfs-accelerate-duckdb-interop",
                "surface_ref": "data_service",
                "method_ref": "accelerate.duckdb.get_performance_results",
                "norm_refs": ["agent_identity", "allowed_surfaces", "arguments_hash"],
            }
        ],
    }


def test_ipfs_accelerate_duckdb_schema_descriptors_exist_on_disk() -> None:
    expected_paths = [
        "external/ipfs_accelerate/data/duckdb/db_schema/time_series_schema.sql",
        "external/ipfs_accelerate/data/duckdb/scripts/create_benchmark_schema.py",
        "external/ipfs_accelerate/data/duckdb/utils/check_database_schema.py",
        "external/ipfs_accelerate/data/duckdb/utils/check_db_schema.py",
    ]
    for relative_path in expected_paths:
        assert (REPO_ROOT / relative_path).is_file(), f"missing {relative_path}"


def test_discover_ipfs_accelerate_duckdb_contract_finds_time_series_tables() -> None:
    contract = discover_ipfs_accelerate_duckdb_contract(IPFS_ACCELERATE_ROOT)

    assert set(REQUIRED_TIME_SERIES_TABLES).issubset(set(contract.time_series_tables))
    assert {"create_performance_tables", "create_common_tables", "create_views"}.issubset(
        set(contract.benchmark_schema_functions)
    )
    assert {"check_schema", "get_all_tables", "get_performance_results"}.issubset(
        set(contract.check_schema_functions)
    )
    assert contract.time_series_schema_path.endswith(
        "data/duckdb/db_schema/time_series_schema.sql"
    )
    assert contract.benchmark_schema_script_path.endswith(
        "data/duckdb/scripts/create_benchmark_schema.py"
    )
    assert contract.check_database_schema_path.endswith(
        "data/duckdb/utils/check_database_schema.py"
    )
    assert contract.check_db_schema_path.endswith("data/duckdb/utils/check_db_schema.py")


def test_discover_ipfs_accelerate_duckdb_contract_raises_for_missing_root(tmp_path) -> None:
    missing_root = tmp_path / "does-not-exist"
    try:
        discover_ipfs_accelerate_duckdb_contract(missing_root)
    except SwissKnifeIPFSAccelerateInteropError as exc:
        assert "not found" in str(exc)
    else:
        raise AssertionError("expected SwissKnifeIPFSAccelerateInteropError")


def test_build_swissknife_duckdb_handoff_is_deterministic() -> None:
    first = build_swissknife_duckdb_handoff(IPFS_ACCELERATE_ROOT)
    second = build_swissknife_duckdb_handoff(IPFS_ACCELERATE_ROOT)

    assert first.as_dict() == second.as_dict()
    assert first.interface_contract == "interface contract swissknife external/ipfs_accelerate"
    assert first.goal_id == GOAL_ID == "VAIOS-G701"
    assert first.goal_packet == GOAL_PACKET
    assert first.source_repository == "swissknife"
    assert first.target_repository == "external/ipfs_accelerate"
    assert first.content_cid.startswith("sha256:")
    assert first.content_cid == f"sha256:{first.payload_sha256}"
    assert first.payload_size_bytes > 0
    assert set(REQUIRED_TIME_SERIES_TABLES).issubset(set(first.time_series_tables))
    assert set(first.required_swissknife_operations) == set(REQUIRED_SWISSKNIFE_DUCKDB_OPERATIONS)


def test_swissknife_descriptor_module_exports_interop_contract() -> None:
    src = read_text(DESCRIPTOR_TS_PATH)

    assert "export const SWISSKNIFE_IPFS_ACCELERATE_INTEROP_INTERFACE" in src
    assert "export const SWISSKNIFE_IPFS_ACCELERATE_INTEROP_DESCRIPTOR" in src
    assert "'interface contract swissknife external/ipfs_accelerate'" in src
    assert "'goal_packet/interoperability/swissknife/06921590135c'" in src
    assert "export function registerSwissKnifeIPFSAccelerateDuckDBInterop" in src
    assert "export function createMCPPlusPlusClientWithSwissKnifeIPFSAccelerateInterop" in src
    assert "export function buildSwissKnifeIPFSAccelerateControlSurfaceContract" in src
    assert "export function buildSwissKnifeIPFSAccelerateInteractionEnvelope" in src

    for goal_id in GOAL_PACKET_GOALS:
        assert goal_id in src
    for operation in REQUIRED_SWISSKNIFE_DUCKDB_OPERATIONS:
        assert operation in src

    assert "swissknife/contracts/control_surface_contract.schema.json" in src
    assert "swissknife/contracts/interaction_envelope.schema.json" in src
    assert "swissknife/contracts/mediation_receipt.schema.json" in src
    assert "external/ipfs_accelerate/data/duckdb/db_schema/time_series_schema.sql" in src
    assert "external/ipfs_accelerate/data/duckdb/scripts/create_benchmark_schema.py" in src
    assert "external/ipfs_accelerate/data/duckdb/utils/check_database_schema.py" in src
    assert "external/ipfs_accelerate/data/duckdb/utils/check_db_schema.py" in src
    assert "VAI-662" in src
    assert "VAIOS-G701" in src
    assert "agent_identity" in src
    assert "allowed_surfaces" in src
    assert "arguments_hash" in src


def test_swissknife_control_surface_and_interaction_envelope_validate_for_ipfs_accelerate() -> None:
    control_schema = read_json("swissknife/contracts/control_surface_contract.schema.json")
    envelope_schema = read_json("swissknife/contracts/interaction_envelope.schema.json")

    Draft202012Validator(control_schema).validate(
        swissknife_ipfs_accelerate_control_surface_payload()
    )
    Draft202012Validator(envelope_schema).validate(
        swissknife_ipfs_accelerate_interaction_envelope()
    )


def test_docs_discovery_and_heap_record_objective_validation_repair() -> None:
    docs = read_text("docs/integration/swissknife-external_ipfs_accelerate.md")
    discovery = read_text(
        "data/virtual_ai_os/discovery/2026-07-08-vai-662-objective-validation-repair.md"
    )
    gap = read_text(
        "data/virtual_ai_os/discovery/2026-07-08-vai-662-objective-gap-2394e45d2012.md"
    )
    heap = read_text("implementation_plan/docs/23-virtual-ai-os-objective-goal-heap.md")

    required_terms = [
        "VAI-662",
        "VAIOS-G701",
        "goal_packet/interoperability/swissknife/06921590135c",
        "objective validation repair",
        "interface contract swissknife external/ipfs_accelerate",
        "tests/integration/test_swissknife_external_ipfs_accelerate_interop.py",
        DESCRIPTOR_TS_PATH,
        "src/handsfree/swissknife_ipfs_accelerate_interop.py",
        "swissknife/contracts/control_surface_contract.schema.json",
        "swissknife/contracts/interaction_envelope.schema.json",
        "external/ipfs_accelerate/data/duckdb/db_schema/time_series_schema.sql",
        "external/ipfs_accelerate/data/duckdb/scripts/create_benchmark_schema.py",
        "external/ipfs_accelerate/data/duckdb/utils/check_database_schema.py",
        "external/ipfs_accelerate/data/duckdb/utils/check_db_schema.py",
    ]
    for content in (docs, discovery, heap):
        for term in required_terms:
            assert term in content, f"missing {term!r}"
    for goal_id in GOAL_PACKET_GOALS:
        assert goal_id in discovery
        assert goal_id in heap
    assert "VAIOS-G701" in gap
