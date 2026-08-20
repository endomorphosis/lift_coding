"""FACP-055: release qualification predicate and RightsIR.

Acceptance (taskboard):
- Datasets license conflict and SwissKnife missing license/provenance block
  automatically.
- Unknown rights remain human review.
- Release predicate rejects stale proof, simulation-as-live, mutable ref,
  missing capability, incompatible contract, or unresolved mandatory rights.

Artifacts are machine-readable policy only; this task does not sign, publish,
or infer legal clearance.
"""

from __future__ import annotations

import json
import tomllib
from pathlib import Path
from typing import Any

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
QUAL_DIR = (
    REPO_ROOT
    / "implementation_plan"
    / "formal_assurance_control_plane"
    / "release"
    / "qualification"
)
RIGHTS_IR_PATH = QUAL_DIR / "rights_ir.json"
RELEASE_PREDICATE_PATH = QUAL_DIR / "release_predicate.json"
INVENTORY_PATH = (
    REPO_ROOT
    / "implementation_plan"
    / "formal_assurance_control_plane"
    / "baseline"
    / "release_rights.json"
)

TASK_ID = "FACP-055"
GOAL_ID = "FACP-G810"
BUNDLE = "facp/release/rights"
RIGHTS_SCHEMA = "facp/rights-ir@1"
PREDICATE_SCHEMA = "facp/release-predicate@1"

REQUIRED_RIGHTS_EVIDENCE = {
    "licenses",
    "data_rights",
    "model_rights",
    "attribution",
    "share_alike",
    "commercial",
    "redistribution",
    "unknown_custom",
}

REQUIRED_PREDICATE_EVIDENCE = {
    "source",
    "lock",
    "build_environment",
    "tests",
    "proofs",
    "contracts",
    "live_capabilities",
    "licenses",
    "data_rights",
    "model_rights",
    "attribution",
    "share_alike",
    "commercial",
    "redistribution",
    "unknown_custom",
}

REQUIRED_REJECTION_CODES = {
    "stale_proof",
    "simulation_as_live",
    "mutable_ref",
    "missing_capability",
    "incompatible_contract",
    "unresolved_mandatory_rights",
}

DATASETS_NODE_ID = "rights:datasets-mit-vs-agpl"
SWISSKNIFE_NODE_ID = "rights:swissknife-undeclared"
UNKNOWN_NODE_IDS = {
    "rights:unknown-custom-license-text",
    "rights:data-model-rights-unknown",
}


def _load_json(path: Path) -> dict[str, Any]:
    assert path.is_file(), f"missing artifact: {path}"
    payload = json.loads(path.read_text(encoding="utf-8"))
    assert isinstance(payload, dict)
    return payload


def _condition_holds(record: dict[str, Any], condition: dict[str, Any]) -> bool:
    field = condition["field"]
    if "in" in condition:
        return record.get(field) in condition["in"]
    if "equals" in condition:
        return record.get(field) is condition["equals"] or record.get(field) == condition["equals"]
    raise AssertionError(f"unsupported condition: {condition}")


def _rule_matches(record: dict[str, Any], rule: dict[str, Any]) -> bool:
    if "when_any" in rule:
        return any(_condition_holds(record, cond) for cond in rule["when_any"])
    if "when_all" in rule:
        return all(_condition_holds(record, cond) for cond in rule["when_all"])
    raise AssertionError(f"rejection rule missing when_any/when_all: {rule['code']}")


def evaluate_release_admissible(
    predicate: dict[str, Any], record: dict[str, Any]
) -> tuple[bool, list[str]]:
    """Evaluate ReleaseAdmissible rejection rules against a qualification record."""
    codes: list[str] = []
    order = predicate["rejection_code_order"]
    rules_by_code = {rule["code"]: rule for rule in predicate["rejection_rules"]}
    for code in order:
        rule = rules_by_code[code]
        if _rule_matches(record, rule):
            assert rule["blocks_release"] is True
            codes.append(code)
    return (len(codes) == 0, codes)


def dispose_rights_node(rights_ir: dict[str, Any], node: dict[str, Any]) -> dict[str, Any]:
    """Apply RightsIR evaluation rules to a node; never machine-clear unknown/conflict."""
    status = node["status"]
    mapping = rights_ir["status_to_disposition"]
    assert status in mapping, f"unmapped rights status: {status}"
    disposition = mapping[status]

    matched_rule = None
    for rule in rights_ir["evaluation_rules"]:
        if status in rule["when_status_in"]:
            matched_rule = rule
            break
    assert matched_rule is not None, f"no evaluation rule for status={status}"
    assert matched_rule["then_disposition"] == disposition
    assert matched_rule["machine_clearance_allowed"] is False

    vocab = rights_ir["disposition_vocabulary"][disposition]
    assert bool(vocab["blocks_release"]) == bool(matched_rule["blocks_release"])
    return {
        "node_id": node["id"],
        "status": status,
        "disposition": disposition,
        "blocks_release": bool(matched_rule["blocks_release"]),
        "machine_clearance_allowed": False,
        "requires_human_review": bool(vocab["requires_human_review"]),
        "reason_code": matched_rule["reason_code"],
        "mandatory": bool(node.get("mandatory", False)),
    }


def evaluate_rights_graph(rights_ir: dict[str, Any]) -> dict[str, Any]:
    results = [dispose_rights_node(rights_ir, node) for node in rights_ir["nodes"]]
    machine_blocks = [
        item for item in results if item["disposition"] == "machine_block"
    ]
    human_review = [
        item for item in results if item["disposition"] == "human_review"
    ]
    mandatory_unresolved = [
        item
        for item in results
        if item["mandatory"] and item["disposition"] in {"machine_block", "human_review"}
    ]
    return {
        "results": results,
        "machine_blocks": machine_blocks,
        "human_review": human_review,
        "mandatory_unresolved": mandatory_unresolved,
        "rights_resolved": len(mandatory_unresolved) == 0,
        "machine_clearance_attempted": False,
    }


@pytest.fixture(scope="module")
def rights_ir() -> dict[str, Any]:
    return _load_json(RIGHTS_IR_PATH)


@pytest.fixture(scope="module")
def release_predicate() -> dict[str, Any]:
    return _load_json(RELEASE_PREDICATE_PATH)


@pytest.fixture(scope="module")
def inventory() -> dict[str, Any]:
    return _load_json(INVENTORY_PATH)


def test_artifacts_schema_and_policy_binding(
    rights_ir: dict[str, Any], release_predicate: dict[str, Any]
) -> None:
    assert rights_ir["schema"] == RIGHTS_SCHEMA
    assert release_predicate["schema"] == PREDICATE_SCHEMA
    assert rights_ir["task_id"] == TASK_ID
    assert release_predicate["task_id"] == TASK_ID
    assert rights_ir["goal_id"] == GOAL_ID
    assert release_predicate["goal_id"] == GOAL_ID
    assert rights_ir["bundle"] == BUNDLE
    assert release_predicate["bundle"] == BUNDLE
    assert release_predicate["predicate"] == "ReleaseAdmissible"
    assert rights_ir["behavior_change"] is False
    assert release_predicate["behavior_change"] is False

    assert set(rights_ir["evidence_subset"]) >= REQUIRED_RIGHTS_EVIDENCE
    assert set(release_predicate["evidence_subset"]) >= REQUIRED_PREDICATE_EVIDENCE

    rights_policy = rights_ir["policy"]
    assert rights_policy["spdx_boolean_expressions"] is True
    assert rights_policy["ambiguous_legal_interpretation_human_blocked"] is True
    assert rights_policy["machine_clearance_of_unknown_or_conflict_forbidden"] is True
    assert rights_policy["conflict_machine_blocks"] is True
    assert rights_policy["missing_license_or_provenance_machine_blocks"] is True
    assert rights_policy["unknown_remains_human_review"] is True
    assert rights_policy["fail_closed"] is True

    pred_policy = release_predicate["policy"]
    assert pred_policy["fail_closed"] is True
    assert pred_policy["stale_proof_reuse_forbidden"] is True
    assert pred_policy["simulation_cannot_satisfy_live"] is True
    assert pred_policy["mutable_dependency_blocks_release"] is True
    assert pred_policy["missing_capability_blocks_release"] is True
    assert pred_policy["contract_incompatibility_blocks_release"] is True
    assert pred_policy["ambiguous_rights_remain_human_blocked"] is True

    prohibited = set(rights_ir["authority"]["prohibited_effects"]) | set(
        release_predicate["authority"]["prohibited_effects"]
    )
    assert "infer_legal_clearance" in prohibited
    assert "unknown_or_conflict_to_compatible" in prohibited
    assert "sign_or_publish" in prohibited


def test_rejection_rules_cover_required_codes(release_predicate: dict[str, Any]) -> None:
    codes = {rule["code"] for rule in release_predicate["rejection_rules"]}
    assert codes == REQUIRED_REJECTION_CODES
    assert set(release_predicate["rejection_code_order"]) == REQUIRED_REJECTION_CODES
    for rule in release_predicate["rejection_rules"]:
        assert rule["blocks_release"] is True
        assert "when_any" in rule or "when_all" in rule


def test_negative_fixtures_reject_exactly_expected_codes(
    release_predicate: dict[str, Any],
) -> None:
    fixtures = release_predicate["negative_fixtures"]
    by_id = {fixture["id"]: fixture for fixture in fixtures}
    required_negatives = {
        "neg:stale-proof": "stale_proof",
        "neg:simulation-as-live": "simulation_as_live",
        "neg:mutable-ref": "mutable_ref",
        "neg:missing-capability": "missing_capability",
        "neg:incompatible-contract": "incompatible_contract",
        "neg:unresolved-mandatory-rights": "unresolved_mandatory_rights",
    }
    for fixture_id, expected_code in required_negatives.items():
        fixture = by_id[fixture_id]
        admissible, codes = evaluate_release_admissible(
            release_predicate, fixture["record"]
        )
        assert admissible is False
        assert expected_code in codes
        assert set(fixture["expect_codes"]) <= set(codes)

    positive = by_id["pos:all-clear-synthetic"]
    assert positive.get("synthetic_clearance_only") is True
    admissible, codes = evaluate_release_admissible(
        release_predicate, positive["record"]
    )
    assert admissible is True
    assert codes == []


def test_datasets_license_conflict_blocks_automatically(
    rights_ir: dict[str, Any], inventory: dict[str, Any]
) -> None:
    node = next(n for n in rights_ir["nodes"] if n["id"] == DATASETS_NODE_ID)
    assert node["status"] == "conflict"
    assert node["mandatory"] is True
    assert node["package_spdx"] == "MIT"
    assert node["repository_spdx"] == "AGPL-3.0-only"

    pyproject = tomllib.loads(
        (REPO_ROOT / "external/ipfs_datasets/pyproject.toml").read_text(encoding="utf-8")
    )
    assert pyproject["project"]["license"]["text"] == "MIT"
    license_text = (REPO_ROOT / "external/ipfs_datasets/LICENSE").read_text(
        encoding="utf-8"
    )
    assert "GNU AFFERO GENERAL PUBLIC LICENSE" in license_text

    decision = dispose_rights_node(rights_ir, node)
    assert decision["disposition"] == "machine_block"
    assert decision["blocks_release"] is True
    assert decision["machine_clearance_allowed"] is False
    assert decision["requires_human_review"] is False
    assert decision["reason_code"] == "rights_conflict"

    assert (
        rights_ir["acceptance_bindings"]["datasets_license_conflict_blocks_automatically"]
        == DATASETS_NODE_ID
    )
    conflict_ids = {item["id"] for item in inventory["rights_summary"]["conflicts"]}
    assert "rights:datasets-mit-vs-agpl" in conflict_ids


def test_swissknife_missing_license_provenance_blocks_automatically(
    rights_ir: dict[str, Any], inventory: dict[str, Any]
) -> None:
    node = next(n for n in rights_ir["nodes"] if n["id"] == SWISSKNIFE_NODE_ID)
    assert node["status"] == "missing"
    assert node["mandatory"] is True
    assert node["spdx_expression"] == "NOASSERTION"

    package = json.loads(
        (REPO_ROOT / "swissknife/package.json").read_text(encoding="utf-8")
    )
    assert package.get("license", None) in ("", None)
    assert not (REPO_ROOT / "swissknife/LICENSE").exists()
    assert not (REPO_ROOT / "swissknife/LICENSE.md").exists()

    decision = dispose_rights_node(rights_ir, node)
    assert decision["disposition"] == "machine_block"
    assert decision["blocks_release"] is True
    assert decision["machine_clearance_allowed"] is False
    assert decision["reason_code"] == "missing_license_or_provenance"

    assert (
        rights_ir["acceptance_bindings"][
            "swissknife_missing_license_provenance_blocks_automatically"
        ]
        == SWISSKNIFE_NODE_ID
    )
    missing_ids = {item["id"] for item in inventory["rights_summary"]["missing"]}
    assert "rights:swissknife-undeclared" in missing_ids


def test_unknown_rights_remain_human_review(rights_ir: dict[str, Any]) -> None:
    graph = evaluate_rights_graph(rights_ir)
    human_ids = {item["node_id"] for item in graph["human_review"]}
    assert UNKNOWN_NODE_IDS <= human_ids

    for node_id in UNKNOWN_NODE_IDS:
        node = next(n for n in rights_ir["nodes"] if n["id"] == node_id)
        decision = dispose_rights_node(rights_ir, node)
        assert decision["disposition"] == "human_review"
        assert decision["blocks_release"] is True
        assert decision["requires_human_review"] is True
        assert decision["machine_clearance_allowed"] is False
        assert decision["reason_code"] == "unknown_rights_human_review"

    # Compatible-without-human-clearance must not become machine clearance.
    assert rights_ir["status_to_disposition"]["compatible"] == "human_review"
    assert rights_ir["status_to_disposition"]["unknown"] == "human_review"
    assert rights_ir["status_to_disposition"]["ambiguous"] == "human_review"
    assert rights_ir["status_to_disposition"]["custom_unparsed"] == "human_review"
    assert rights_ir["status_to_disposition"]["conflict"] == "machine_block"
    assert rights_ir["status_to_disposition"]["missing"] == "machine_block"


def test_rights_graph_blocks_current_tree_release(
    rights_ir: dict[str, Any], release_predicate: dict[str, Any]
) -> None:
    graph = evaluate_rights_graph(rights_ir)
    assert graph["rights_resolved"] is False
    assert graph["machine_clearance_attempted"] is False

    machine_ids = {item["node_id"] for item in graph["machine_blocks"]}
    assert DATASETS_NODE_ID in machine_ids
    assert SWISSKNIFE_NODE_ID in machine_ids

    current = release_predicate["current_tree_qualification"]
    assert current["release_admissible"] is False
    assert "unresolved_mandatory_rights" in current["blocking_rejection_codes"]
    assert DATASETS_NODE_ID in current["rights_ir_blocking_node_ids"]
    assert SWISSKNIFE_NODE_ID in current["rights_ir_blocking_node_ids"]

    # Compose a current-tree-like record from RightsIR mandatory unresolved state.
    record = {
        "proof_freshness": "current",
        "proof_tree_match": True,
        "historical_receipt_used_as_current": False,
        "origin": "live_observed",
        "claimed_environment": "live",
        "dependency_mutability": "immutable",
        "has_mutable_ref": False,
        "capability_status": "present",
        "live_capability_present": True,
        "contract_status": "compatible",
        "contracts_compatible": True,
        "rights_disposition": "machine_block",
        "mandatory_rights_resolved": False,
        "rights_status": "conflict",
    }
    admissible, codes = evaluate_release_admissible(release_predicate, record)
    assert admissible is False
    assert "unresolved_mandatory_rights" in codes


def test_apparently_aligned_is_not_clearance(rights_ir: dict[str, Any]) -> None:
    aligned = [
        node
        for node in rights_ir["nodes"]
        if node["status"] == "apparently_aligned"
    ]
    assert aligned
    for node in aligned:
        decision = dispose_rights_node(rights_ir, node)
        assert decision["disposition"] == "observation_only_not_clearance"
        assert decision["machine_clearance_allowed"] is False
        assert decision["blocks_release"] is False
        assert decision["reason_code"] == "alignment_observation_only"


def test_acceptance_flags_match_evaluated_behavior(
    rights_ir: dict[str, Any], release_predicate: dict[str, Any]
) -> None:
    acceptance = release_predicate["acceptance"]
    assert acceptance["datasets_license_conflict_blocks_automatically"] is True
    assert acceptance["swissknife_missing_license_provenance_blocks_automatically"] is True
    assert acceptance["unknown_rights_remain_human_review"] is True
    assert acceptance["rejects_stale_proof"] is True
    assert acceptance["rejects_simulation_as_live"] is True
    assert acceptance["rejects_mutable_ref"] is True
    assert acceptance["rejects_missing_capability"] is True
    assert acceptance["rejects_incompatible_contract"] is True
    assert acceptance["rejects_unresolved_mandatory_rights"] is True
    assert acceptance["current_tree_release_admissible_claimed"] is False

    graph = evaluate_rights_graph(rights_ir)
    assert any(item["node_id"] == DATASETS_NODE_ID for item in graph["machine_blocks"])
    assert any(item["node_id"] == SWISSKNIFE_NODE_ID for item in graph["machine_blocks"])
    assert UNKNOWN_NODE_IDS <= {item["node_id"] for item in graph["human_review"]}

    for code in REQUIRED_REJECTION_CODES:
        fixture = next(
            item
            for item in release_predicate["negative_fixtures"]
            if code in item.get("expect_codes", [])
        )
        admissible, codes = evaluate_release_admissible(
            release_predicate, fixture["record"]
        )
        assert admissible is False
        assert code in codes


def test_cross_refs_and_necessary_evidence(
    rights_ir: dict[str, Any], release_predicate: dict[str, Any]
) -> None:
    assert rights_ir["release_predicate_ref"].endswith("release_predicate.json")
    assert release_predicate["rights_ir_ref"].endswith("rights_ir.json")
    assert "rights_resolution" in release_predicate["necessary_evidence"]
    assert "immutable_dependency_closure" in release_predicate["necessary_evidence"]
    conjunct_ids = {item["id"] for item in release_predicate["conjuncts"]}
    assert "rights_resolution" in conjunct_ids
    assert "immutable_dependency_closure" in conjunct_ids
    assert "live_capabilities" in conjunct_ids
    assert "contract_compatibility" in conjunct_ids
