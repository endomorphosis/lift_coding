"""FACP-006: MCP++ schemas and canonicalization inventory gate.

Validates that mcplusplus_contracts.json maps every wire model and
canonicalization rule across Python/TypeScript/Rust/Go, records conflicting
and permissive choices, binds the exact MCP++ gitlink, and names the smallest
executable compiler source of truth without selecting a final assurance encoding.
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path
from typing import Any

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from facp_historical_git import (
    assert_historical_ancestor,
    blob_text,
    current_head,
    git_output,
    superproject_gitlink,
    tree_path_exists,
)

REPORT_PATH = (
    REPO_ROOT
    / "implementation_plan"
    / "formal_assurance_control_plane"
    / "baseline"
    / "mcplusplus_contracts.json"
)
MCP_ROOT = REPO_ROOT / "Mcp-Plus-Plus"

REQUIRED_EVIDENCE = {
    "IDL",
    "profiles A-H",
    "DAG-JSON/DAG-CBOR/JSON choices",
    "CID families",
    "Python/TS/Rust/Go validators",
    "duplicate semantics",
    "unknown-field behavior",
}

REQUIRED_LANGUAGES = ("python", "typescript", "rust", "go")
REQUIRED_PROFILES = ("A", "B", "C", "D", "E", "F", "G", "H")

CORE_WIRE_MODELS = {
    "JSONRPCRequest",
    "JSONRPCResponse",
    "InitializeParams",
    "InitializeResult",
    "InterfaceDescriptor",
    "ExecutionEnvelope",
    "ExecutionReceipt",
    "UCANToken",
    "Delegation",
    "DelegationChain",
    "PolicyDecision",
    "DAGEvent",
    "TransportMessage",
    "P2PMessage",
    "SessionError",
    "BusMessage",
    "AuditEntry",
    "WasmProofResult",
    "ZKProofArtifact",
    "ProfileGArtifacts",
    "ProfileHArtifacts",
}

REQUIRED_CONFLICT_CATEGORIES = {
    "canonicalization",
    "cid_families",
    "unknown_field_behavior",
    "duplicate_semantics",
}

FORBIDDEN_SOT_PATHS = {
    "Mcp-Plus-Plus/tests-py/validators/mcp_idl.py",
    "Mcp-Plus-Plus/tests-ts/src/validators/mcpIDL.ts",
    "validators/models.py",
}


@pytest.fixture(scope="module")
def report() -> dict[str, Any]:
    assert REPORT_PATH.is_file(), f"missing inventory report: {REPORT_PATH}"
    payload = json.loads(REPORT_PATH.read_text(encoding="utf-8"))
    assert isinstance(payload, dict)
    return payload


def _gitlink_commit() -> str:
    return superproject_gitlink(REPO_ROOT, "HEAD", "Mcp-Plus-Plus")


def _git_mcp_head() -> str:
    return current_head(MCP_ROOT)


def _mcp_relative(path: str) -> str:
    return str(Path(path).relative_to("Mcp-Plus-Plus"))


def _report_producer_commit() -> str:
    relative = str(REPORT_PATH.relative_to(REPO_ROOT))
    commits = git_output(
        REPO_ROOT, "log", "--diff-filter=A", "--format=%H", "--", relative
    ).splitlines()
    assert len(commits) == 1, f"expected one producer commit for {relative}: {commits}"
    assert_historical_ancestor(REPO_ROOT, commits[0])
    return commits[0]


def _read_span(commit: str, path: str, line_start: int, line_end: int) -> str:
    if path.startswith("Mcp-Plus-Plus/"):
        text = blob_text(MCP_ROOT, commit, _mcp_relative(path))
    else:
        text = blob_text(REPO_ROOT, _report_producer_commit(), path)
    lines = text.splitlines()
    assert 1 <= line_start <= line_end <= len(lines), (
        f"span out of range for {path}: {line_start}-{line_end} (file has {len(lines)} lines)"
    )
    return "\n".join(lines[line_start - 1 : line_end])


def _assert_quote(
    commit: str,
    path: str,
    line_start: int,
    line_end: int,
    quote: str,
    *,
    label: str,
) -> None:
    span = _read_span(commit, path, line_start, line_end)
    assert quote in span, (
        f"{label} quote not reproducible at {path}:{line_start}-{line_end}: {quote!r}"
    )


def test_report_task_and_schema_binding(report: dict[str, Any]) -> None:
    assert report["task_id"] == "FACP-006"
    assert report["goal_id"] == "FACP-G010"
    assert report["schema"] == "FACPMCPPlusPlusContractsInventory@1"
    assert report["bundle"] == "facp/inventory/mcplusplus"
    assert report["behavior_change"] is False
    assert report["discovery_is_not_completion"] is True
    assert set(report["evidence_subset"]) >= REQUIRED_EVIDENCE
    assert set(report["languages"]) == set(REQUIRED_LANGUAGES)
    assert "select_final_assurance_encoding_in_this_task" in report["prohibited_conclusions"]


def test_source_binding_matches_exact_mcpplusplus_gitlink(report: dict[str, Any]) -> None:
    binding = report["source_binding"]
    assert binding["submodule_path"] == "Mcp-Plus-Plus"
    assert binding["gitlink_path"] == "Mcp-Plus-Plus"
    assert binding["planning_revision"] == binding["gitlink_commit"]
    current_gitlink = _gitlink_commit()
    assert _git_mcp_head() == current_gitlink
    assert_historical_ancestor(MCP_ROOT, binding["gitlink_commit"], current_gitlink)
    assert binding["worktree_status"] == "clean"
    dirty = subprocess.run(
        ["git", "-C", str(MCP_ROOT), "status", "--porcelain"],
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()
    assert dirty == ""


def test_profiles_a_through_h_are_mapped(report: dict[str, Any]) -> None:
    bound_commit = report["source_binding"]["gitlink_commit"]
    profiles = report["profiles"]
    assert isinstance(profiles, list)
    by_id = {item["id"]: item for item in profiles}
    assert set(by_id) == set(REQUIRED_PROFILES)

    for profile_id, item in by_id.items():
        assert item["spec"].startswith("Mcp-Plus-Plus/docs/spec/")
        assert tree_path_exists(MCP_ROOT, bound_commit, _mcp_relative(item["spec"])), item["spec"]
        assert "canonicalization" in item
        validators = item["validators"]
        assert set(validators) == set(REQUIRED_LANGUAGES)
        for language, path in validators.items():
            if path is None:
                # Profile H has no Rust/Go codec ports yet.
                assert profile_id == "H" and language in {"rust", "go"}
                continue
            assert tree_path_exists(MCP_ROOT, bound_commit, _mcp_relative(path)), (
                f"{profile_id}/{language}: {path}"
            )

    assert by_id["A"]["capability_key"] == "mcp++/mcp-idl"
    assert by_id["B"]["capability_key"] == "mcp++/cid-envelope"
    assert by_id["H"]["capability_key"] == "mcp++/x402-payments"
    assert by_id["H"]["json_schema"] == "Mcp-Plus-Plus/schemas/profile-h/1.0"
    assert tree_path_exists(MCP_ROOT, bound_commit, _mcp_relative(by_id["H"]["json_schema"]))
    assert by_id["G"]["capability_key"] is None


def test_wire_models_cover_core_shapes_across_languages(report: dict[str, Any]) -> None:
    models = report["wire_models"]
    assert isinstance(models, list) and len(models) >= 30
    by_name = {item["model"]: item for item in models}
    assert CORE_WIRE_MODELS <= set(by_name)

    for name, item in by_name.items():
        presence = item["presence"]
        assert set(presence) == set(REQUIRED_LANGUAGES), name
        unknown = item["unknown_fields"]
        assert set(unknown) == set(REQUIRED_LANGUAGES), name
        for language in REQUIRED_LANGUAGES:
            assert presence[language] not in (None, ""), name
            assert unknown[language] not in (None, ""), name

    # Profile G/H artifact families must list kinds and closed unknown-field policy.
    g_art = by_name["ProfileGArtifacts"]
    assert len(g_art["kinds"]) == 14
    assert g_art["unknown_fields"]["python"] == "reject"
    assert g_art["unknown_fields"]["typescript"] == "reject"

    h_art = by_name["ProfileHArtifacts"]
    assert len(h_art["kinds"]) == 9
    assert h_art["unknown_fields"]["python"] == "reject"
    assert h_art["presence"]["rust"] is False
    assert h_art["presence"]["go"] is False

    # At least one model must be flagged as a cross-language shape conflict.
    assert any(item.get("shape_conflict") for item in models)


def test_canonicalization_rules_cover_encoding_choices(report: dict[str, Any]) -> None:
    bound_commit = report["source_binding"]["gitlink_commit"]
    rules = report["canonicalization_rules"]
    assert isinstance(rules, list) and len(rules) >= 5
    by_id = {item["rule_id"]: item for item in rules}

    required = {
        "CANON-IDL-MULTI",
        "CANON-PROFILE-B-CID",
        "CANON-PROFILE-D-COMMITMENT",
        "CANON-PROFILE-G-DAGJSON",
        "CANON-PROFILE-H-DAGJSON",
        "CANON-FACP-CCC-PLANNED",
    }
    assert required <= set(by_id)

    encodings_seen: set[str] = set()
    for rule in rules:
        for choice in rule["encoding_choices"]:
            encodings_seen.add(choice)
        authority = rule["authority"]
        _assert_quote(
            bound_commit,
            authority["path"],
            int(authority["line_start"]),
            int(authority["line_end"]),
            authority["quote"],
            label=rule["rule_id"],
        )
        for impl in rule.get("implementations") or []:
            if "quote" in impl:
                _assert_quote(
                    bound_commit,
                    impl["path"],
                    int(impl["line_start"]),
                    int(impl["line_end"]),
                    impl["quote"],
                    label=f"{rule['rule_id']}:{impl.get('language', 'impl')}",
                )

    assert "dag_json" in encodings_seen
    assert "dag_cbor" in encodings_seen
    assert any("json" in choice for choice in encodings_seen)

    g_rule = by_id["CANON-PROFILE-G-DAGJSON"]
    assert g_rule["status"] == "executable_cross_checked"
    assert g_rule["ports"]["python"] == "full_codec"
    assert g_rule["ports"]["typescript"] == "full_codec"

    planned = by_id["CANON-FACP-CCC-PLANNED"]
    assert planned["status"] == "planned_not_implemented"
    assert planned["encoding_choices"] == ["dag_cbor"]


def test_cid_families_are_inventoried(report: dict[str, Any]) -> None:
    families = {item["family_id"]: item for item in report["cid_families"]}
    required = {
        "cidv1_raw_sha256_base32",
        "cidv0_sha256_base58btc",
        "cidv1_dag_json_sha256_base32",
        "sha256_hex_digest_alias",
        "pseudo_bafy_test_cid",
    }
    assert required <= set(families)
    assert families["cidv1_raw_sha256_base32"]["example_prefix"] == "bafkrei"
    assert families["cidv1_dag_json_sha256_base32"]["example_prefix"] == "baguqeera"
    assert families["cidv1_dag_json_sha256_base32"]["multicodec"] == "0x0129"
    assert (
        "Profile B 59-char bafkrei regex"
        in families["cidv1_dag_json_sha256_base32"]["conflicts_with"]
    )


def test_conflicting_and_permissive_choices_are_identified(
    report: dict[str, Any],
) -> None:
    bound_commit = report["source_binding"]["gitlink_commit"]
    conflicts = report["conflicting_or_permissive_choices"]
    assert isinstance(conflicts, list) and len(conflicts) >= 8
    categories = {item["category"] for item in conflicts}
    assert REQUIRED_CONFLICT_CATEGORIES <= categories

    by_id = {item["conflict_id"]: item for item in conflicts}
    assert "MCP-CANON-ENCODING-FRAGMENTATION" in by_id
    assert "MCP-CID-FAMILY-B-VS-GH" in by_id
    assert "MCP-UNKNOWN-FIELD-PERMISSIVE" in by_id
    assert "MCP-SHAPE-IDL-INTERFACE" in by_id
    assert "MCP-IDL-PSEUDO-CID" in by_id

    permissive = by_id["MCP-UNKNOWN-FIELD-PERMISSIVE"]
    assert "InterfaceDescriptor" in permissive["permissive_models"]
    assert "ExecutionReceipt" in permissive["permissive_models"]
    assert "JSONRPCRequest" in permissive["strict_models_py_ts"]
    assert "ExecutionEnvelope" in permissive["strict_models_py_ts"]

    for item in conflicts:
        assert item["disposition"] == "inventory_only_do_not_select"
        assert item["severity"] in {"high", "medium", "low"}
        assert item["evidence"], item["conflict_id"]
        for evidence in item["evidence"]:
            _assert_quote(
                bound_commit,
                evidence["path"],
                int(evidence["line_start"]),
                int(evidence["line_end"]),
                evidence["quote"],
                label=item["conflict_id"],
            )


def test_smallest_compiler_source_of_truth_is_named(report: dict[str, Any]) -> None:
    bound_commit = report["source_binding"]["gitlink_commit"]
    sot = report["smallest_compiler_source_of_truth"]
    assert sot["name"]
    assert sot["path"] == "Mcp-Plus-Plus/tests-py/validators/profile_g.py"
    assert sot["symbol"] == "canonical_profile_g_bytes"
    assert sot["not_selected_as_final_assurance_encoding"] is True
    assert sot["path"] not in FORBIDDEN_SOT_PATHS
    _assert_quote(
        bound_commit,
        sot["path"],
        int(sot["line_start"]),
        int(sot["line_end"]),
        sot["quote"],
        label="smallest_compiler_source_of_truth",
    )

    future = sot["future_compiler_owner"]
    assert future["path"] == "Mcp-Plus-Plus/tools/assurance_idl"
    assert future["generated_schemas"] == "Mcp-Plus-Plus/schemas/assurance/v1"
    assert future["planned_encoding"] == "deterministic_dag_cbor"
    assert future["status"] == "planned_absent"
    assert not tree_path_exists(MCP_ROOT, bound_commit, _mcp_relative(future["path"]))
    assert not tree_path_exists(MCP_ROOT, bound_commit, _mcp_relative(future["generated_schemas"]))

    # Inventory must not pretend pseudo-CID IDL helpers are the compiler SoT.
    assert "mcp_idl" not in sot["path"]
    assert "bafy" not in sot["path"]
    assert sot["path"] != "Mcp-Plus-Plus/tests-py/validators/models.py"


def test_schemas_and_conformance_inventory_are_bound(report: dict[str, Any]) -> None:
    bound_commit = report["source_binding"]["gitlink_commit"]
    schemas = report["schemas_inventory"]
    for path in schemas["present"]:
        assert tree_path_exists(MCP_ROOT, bound_commit, _mcp_relative(path)), path
    for path in schemas["absent"]:
        assert not tree_path_exists(MCP_ROOT, bound_commit, _mcp_relative(path)), path

    vectors = report["conformance_vectors"]
    vector_dir = _mcp_relative(vectors["directory"])
    assert tree_path_exists(MCP_ROOT, bound_commit, vector_dir)
    assert tree_path_exists(MCP_ROOT, bound_commit, _mcp_relative(vectors["readme"]))
    for name in vectors["canonical_wire_models_named"]:
        assert isinstance(name, str) and name
    for filename in vectors["profile_g_h_vector_sets"]:
        assert tree_path_exists(MCP_ROOT, bound_commit, f"{vector_dir}/{filename}"), filename


def test_report_does_not_select_final_encoding(report: dict[str, Any]) -> None:
    assert report["behavior_change"] is False
    assert (
        report["smallest_compiler_source_of_truth"]["not_selected_as_final_assurance_encoding"]
        is True
    )
    for conflict in report["conflicting_or_permissive_choices"]:
        assert conflict["disposition"] == "inventory_only_do_not_select"
    # Planned DAG-CBOR remains planned, not adopted by this inventory.
    planned = next(
        rule
        for rule in report["canonicalization_rules"]
        if rule["rule_id"] == "CANON-FACP-CCC-PLANNED"
    )
    assert planned["status"] == "planned_not_implemented"
