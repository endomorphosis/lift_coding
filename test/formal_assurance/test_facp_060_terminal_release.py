"""FACP-060: Seal the terminal proof-carrying release.

Acceptance (taskboard):
- Independent verifier reconstructs manifest identity and every required predicate.
- All zero floors are zero.
- Signatures bind complete closure.
- Any unresolved right, stale proof/capability, mutable dependency,
  nonreproducible artifact, simulated evidence, or unsupported claim keeps
  release nonadmissible.

Owns only release_manifest.json and this hermetic fan-in test. Consumes
FACP-059 composed workflow and qualification artifacts as immutable inputs.
Does not publish/deploy or waive zero floors.
"""

from __future__ import annotations

import copy
import hashlib
import json
import re
import subprocess
from pathlib import Path
from typing import Any

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
MANIFEST_PATH = (
    REPO_ROOT
    / "implementation_plan"
    / "formal_assurance_control_plane"
    / "release"
    / "terminal"
    / "release_manifest.json"
)
COMPOSED_PATH = (
    REPO_ROOT
    / "implementation_plan"
    / "formal_assurance_control_plane"
    / "release"
    / "terminal"
    / "composed_workflow.json"
)
QUAL_DIR = (
    REPO_ROOT
    / "implementation_plan"
    / "formal_assurance_control_plane"
    / "release"
    / "qualification"
)
RELEASE_PREDICATE_PATH = QUAL_DIR / "release_predicate.json"
RIGHTS_IR_PATH = QUAL_DIR / "rights_ir.json"
PORTFOLIO_LOCK_PATH = QUAL_DIR / "portfolio.lock.json"
PROVENANCE_PATH = QUAL_DIR / "provenance_policy.json"
SCHEDULER_PATH = REPO_ROOT / "config" / "formal_assurance_control_plane_scheduler.json"
CONTRACTS_PATH = (
    REPO_ROOT / "Mcp-Plus-Plus" / "schemas" / "assurance" / "v1" / "repository-contracts.json"
)
COHORT_PATH = (
    REPO_ROOT
    / "external"
    / "ipfs_kit"
    / "data"
    / "formal_assurance"
    / "backend_receipts"
    / "cohort.json"
)
WPD_HISTORICAL_PATH = (
    REPO_ROOT / "implementation_plan" / "docs" / "47-wpd-terminal-release-receipt.json"
)

MANIFEST_SCHEMA = "facp/terminal-release@1"
TASK_ID = "FACP-060"
GOAL_ID = "FACP-G820"
BUNDLE = "facp/release/terminal"
RELEASE = "terminal-release-v1"
VOCAB_SCHEMA = "facp/formal-claim-algebra-v1@1"
PREDICATE_NAME = "ReleaseAdmissible"

REQUIRED_EVIDENCE_SUBSET = {
    "source_forest",
    "immutable_lock",
    "build_environment_artifacts",
    "contracts_controller_policies",
    "proofs_tests",
    "live_capability_receipts",
    "rights",
    "reproducibility_provenance",
    "composed_trace",
    "residual_risks_human_exceptions",
}

REQUIRED_ZERO_FLOORS = {
    "simulated_to_live_promotion",
    "effects_without_admission_token",
    "stale_proof_reuse",
    "browser_authored_authority",
    "pseudo_cid_on_supported_paths",
    "release_with_mutable_dependencies",
    "success_without_observed_or_verified_evidence",
    "secret_flow_to_public_evidence",
    "blind_retry_unknown_irreversible_effects",
    "llm_self_certification_or_policy_authority",
}

REQUIRED_CONJUNCT_IDS = {
    "exact_source_binding",
    "immutable_dependency_closure",
    "identified_build_environment",
    "current_proofs_and_tests",
    "contract_compatibility",
    "rights_resolution",
    "live_capabilities",
    "reproducibility_and_provenance",
    "composed_workflow_trace",
    "zero_floors",
    "signature_binds_complete_closure",
    "historical_receipt_not_current",
}

REQUIRED_NEGATIVE_FIXTURE_IDS = {
    "neg:unresolved-right",
    "neg:stale-proof",
    "neg:stale-capability",
    "neg:mutable-dependency",
    "neg:nonreproducible-artifact",
    "neg:simulated-evidence",
    "neg:unsupported-claim",
    "neg:historical-wpd-receipt",
    "pos:all-clear-synthetic",
}

REQUIRED_PROHIBITED_EFFECTS = {
    "publish",
    "deploy",
    "waive_zero_floor",
    "accept_human_prose_as_proof",
    "accept_provider_output_as_proof",
    "sign_with_missing_evidence",
    "sign_with_stale_evidence",
    "sign_with_conflicting_evidence",
    "treat_historical_receipt_as_current_qualification",
    "simulation_as_production",
}

PLANNING_FOREST_PATHS = (
    "Mcp-Plus-Plus",
    "external/ipfs_accelerate",
    "external/ipfs_datasets",
    "external/ipfs_kit",
    "swissknife",
)

FULL_SHA_RE = re.compile(r"^[0-9a-f]{40}$")
DIGEST_RE = re.compile(r"^[0-9a-f]{64}$")

SECRET_OR_PRIVATE_KEYS = {
    "goose_secret_key",
    "X-Secret-Key",
    "secret_header",
    "authorization",
    "api_key",
    "password",
    "secret",
    "bearer_token",
    "backend_credentials",
    "token_secret",
    "private_context",
    "private_key",
    "signing_key",
}


def _sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _canonical_json_bytes(value: Any) -> bytes:
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
    ).encode("utf-8")


def _canonical_content_sha256(manifest: dict[str, Any]) -> str:
    without = {key: value for key, value in manifest.items() if key != "content_sha256"}
    return hashlib.sha256(_canonical_json_bytes(without)).hexdigest()


def _git_rev_parse(*args: str) -> str:
    completed = subprocess.run(
        ["git", "rev-parse", *args],
        check=True,
        capture_output=True,
        text=True,
        cwd=REPO_ROOT,
    )
    return completed.stdout.strip()


def _gitlink_commit(path: str) -> str:
    completed = subprocess.run(
        ["git", "ls-tree", "HEAD", path],
        check=True,
        capture_output=True,
        text=True,
        cwd=REPO_ROOT,
    )
    parts = completed.stdout.strip().split()
    assert len(parts) >= 3, completed.stdout
    assert parts[1] == "commit", completed.stdout
    return parts[2]


def _load_json(path: Path) -> dict[str, Any]:
    assert path.is_file(), f"missing artifact: {path}"
    payload = json.loads(path.read_text(encoding="utf-8"))
    assert isinstance(payload, dict)
    return payload


def _walk_keys(value: Any) -> set[str]:
    keys: set[str] = set()
    if isinstance(value, dict):
        for key, child in value.items():
            keys.add(str(key))
            keys |= _walk_keys(child)
    elif isinstance(value, list):
        for child in value:
            keys |= _walk_keys(child)
    return keys


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
    """Independent reconstruction of ReleaseAdmissible rejection codes."""
    codes: list[str] = []
    rules_by_code = {rule["code"]: rule for rule in predicate["rejection_rules"]}
    for code in predicate["rejection_code_order"]:
        rule = rules_by_code[code]
        if _rule_matches(record, rule):
            assert rule["blocks_release"] is True
            codes.append(code)
    return (len(codes) == 0, codes)


def evaluate_terminal_admissible(
    manifest: dict[str, Any],
    predicate: dict[str, Any],
    record: dict[str, Any],
) -> tuple[bool, list[str], list[str]]:
    """Combine ReleaseAdmissible codes with terminal extended blockers."""
    admissible, codes = evaluate_release_admissible(predicate, record)
    extended: list[str] = []
    if record.get("nonreproducible_blockers_present") is True or (
        record.get("reproducibility_complete") is False
    ):
        extended.append("nonreproducible_artifact")
    if record.get("unsupported_claim_present") is True:
        extended.append("unsupported_claim")
    if record.get("simulated_evidence_as_production") is True:
        if "simulation_as_live" not in codes:
            extended.append("simulated_evidence")
    if not record.get("zero_floors_all_zero", True):
        extended.append("zero_floor_breach")

    # Historical WPD receipt can never clear the terminal predicate.
    for forbidden in manifest.get("historical_receipts_forbidden") or []:
        assert forbidden.get("satisfies_facp_terminal_release") is False

    if codes or extended:
        return False, codes, extended
    return admissible, codes, extended


def reconstruct_closure_identity(manifest: dict[str, Any]) -> str:
    """Independent reconstruction of closure identity from sealed materials."""
    artifacts = [
        {"role": row["role"], "path": row["path"], "sha256": row["sha256"]}
        for row in manifest["closure"]["artifacts"]
    ]
    forest = [
        {"path": row["path"], "gitlink_commit": row["gitlink_commit"]}
        for row in manifest["source_binding"]["planning_forest"]
    ]
    materials = {
        "artifact_digests": sorted(artifacts, key=lambda item: item["role"]),
        "planning_forest": sorted(forest, key=lambda item: item["path"]),
        "controller_commit": manifest["source_binding"]["controller_commit"],
        "controller_tree": manifest["source_binding"]["controller_tree"],
        "zero_floors": manifest["zero_floors"],
        "release_admissible": manifest["predicates"]["release_admissible"],
        "rejection_codes": sorted(manifest["predicates"]["rejection_codes"]),
    }
    return hashlib.sha256(_canonical_json_bytes(materials)).hexdigest()


def reconstruct_signature_payload_sha256(manifest: dict[str, Any]) -> str:
    body = {key: value for key, value in manifest.items() if key != "content_sha256"}
    sig = dict(body["signature"])
    sig.pop("payload_sha256", None)
    body["signature"] = sig
    return hashlib.sha256(_canonical_json_bytes(body)).hexdigest()


@pytest.fixture(scope="module")
def manifest() -> dict[str, Any]:
    return _load_json(MANIFEST_PATH)


@pytest.fixture(scope="module")
def release_predicate() -> dict[str, Any]:
    return _load_json(RELEASE_PREDICATE_PATH)


@pytest.fixture(scope="module")
def rights_ir() -> dict[str, Any]:
    return _load_json(RIGHTS_IR_PATH)


@pytest.fixture(scope="module")
def portfolio_lock() -> dict[str, Any]:
    return _load_json(PORTFOLIO_LOCK_PATH)


@pytest.fixture(scope="module")
def composed() -> dict[str, Any]:
    return _load_json(COMPOSED_PATH)


@pytest.fixture(scope="module")
def scheduler() -> dict[str, Any]:
    return _load_json(SCHEDULER_PATH)


@pytest.fixture(scope="module")
def cohort() -> dict[str, Any]:
    return _load_json(COHORT_PATH)


def test_manifest_schema_task_bundle_goal_and_evidence_subset(
    manifest: dict[str, Any],
) -> None:
    assert manifest["schema"] == MANIFEST_SCHEMA
    assert manifest["schema_version"] == 1
    assert manifest["task_id"] == TASK_ID
    assert manifest["goal_id"] == GOAL_ID
    assert manifest["bundle"] == BUNDLE
    assert manifest["release"] == RELEASE
    assert manifest["vocabulary_schema"] == VOCAB_SCHEMA
    assert manifest["predicate"] == PREDICATE_NAME
    assert manifest["status"] == "sealed"
    assert manifest["behavior_change"] is False
    assert manifest["title"]
    assert manifest["generated_at"]
    assert set(manifest["evidence_subset"]) >= REQUIRED_EVIDENCE_SUBSET


def test_policy_forbids_publish_waiver_and_prose_as_proof(
    manifest: dict[str, Any],
) -> None:
    policy = manifest["policy"]
    assert policy["fail_closed"] is True
    assert policy["provider_authority"] == "none"
    assert policy["implementation_mode"] == "deterministic-only"
    assert policy["waive_zero_floor_forbidden"] is True
    assert policy["publish_or_deploy_forbidden"] is True
    assert policy["human_prose_is_not_proof"] is True
    assert policy["provider_output_is_not_proof"] is True
    assert policy["simulation_as_production_forbidden"] is True
    assert policy["historical_receipt_is_not_current_qualification"] is True
    assert policy["sign_with_missing_stale_or_conflicting_evidence_forbidden"] is True
    assert policy["production_release_claim_forbidden_while_nonadmissible"] is True
    assert REQUIRED_PROHIBITED_EFFECTS <= set(policy["prohibited_effects"])


def test_independent_verifier_reconstructs_manifest_identity(
    manifest: dict[str, Any],
) -> None:
    assert DIGEST_RE.match(manifest["content_sha256"])
    binding = manifest["content_binding"]
    assert binding["alg"] == "sha256"
    assert "sort-keys" in binding["canonicalization"] or "separators" in binding[
        "canonicalization"
    ]
    assert binding["covers"] == "gate_record_excluding_content_sha256"
    assert _canonical_content_sha256(manifest) == manifest["content_sha256"]


def test_source_binding_matches_current_forest_and_producer_digests(
    manifest: dict[str, Any], scheduler: dict[str, Any], composed: dict[str, Any]
) -> None:
    binding = manifest["source_binding"]
    assert binding["controller_commit"] == _git_rev_parse("HEAD")
    assert binding["controller_tree"] == _git_rev_parse("HEAD^{tree}")
    assert FULL_SHA_RE.match(binding["controller_commit"])
    assert FULL_SHA_RE.match(binding["controller_tree"])

    assert binding["scheduler_config_sha256"] == _sha256_file(SCHEDULER_PATH)
    assert binding["repository_contracts_sha256"] == _sha256_file(CONTRACTS_PATH)
    assert binding["portfolio_lock_sha256"] == _sha256_file(PORTFOLIO_LOCK_PATH)
    assert binding["release_predicate_sha256"] == _sha256_file(RELEASE_PREDICATE_PATH)
    assert binding["rights_ir_sha256"] == _sha256_file(RIGHTS_IR_PATH)
    assert binding["provenance_policy_sha256"] == _sha256_file(PROVENANCE_PATH)
    assert binding["composed_workflow_sha256"] == _sha256_file(COMPOSED_PATH)

    composed_without = {
        key: value for key, value in composed.items() if key != "content_sha256"
    }
    composed_content = hashlib.sha256(
        _canonical_json_bytes(composed_without)
    ).hexdigest()
    assert composed_content == composed["content_sha256"]
    assert binding["composed_workflow_content_sha256"] == composed_content

    forest = {entry["path"]: entry for entry in binding["planning_forest"]}
    assert set(forest) == set(PLANNING_FOREST_PATHS)
    sb = scheduler["source_binding"]
    for path, entry in forest.items():
        assert FULL_SHA_RE.match(entry["gitlink_commit"])
        assert entry["gitlink_commit"] == _gitlink_commit(path)
        field = entry["planning_revision_field"]
        assert entry["scheduler_planning_revision"] == sb[field]
        assert entry["matches_scheduler_planning_revision"] is (
            entry["gitlink_commit"] == sb[field]
        )

    assert set(binding["depends_on"]) == {"FACP-059"}

    producers = {row["task_id"]: row for row in binding["producer_inputs"]}
    assert {"FACP-059", "FACP-055", "FACP-056", "FACP-057", "FACP-058"} <= set(producers)
    for row in binding["producer_inputs"]:
        assert row["role"]
        assert row["paths"]
        for item in row["paths"]:
            path = REPO_ROOT / item["path"]
            assert path.is_file(), item["path"]
            assert DIGEST_RE.match(item["sha256"])
            assert item["sha256"] == _sha256_file(path), item["path"]


def test_closure_artifacts_match_filesystem_and_identity_reconstructs(
    manifest: dict[str, Any],
) -> None:
    closure = manifest["closure"]
    assert DIGEST_RE.match(closure["identity_sha256"])
    assert reconstruct_closure_identity(manifest) == closure["identity_sha256"]
    assert closure["identity_sha256"] == manifest["signature"]["closure_identity_sha256"]

    roles = {row["role"] for row in closure["artifacts"]}
    for required in {
        "release_predicate",
        "rights_ir",
        "portfolio_lock",
        "provenance_policy",
        "composed_workflow",
        "repository_contracts",
        "backend_cohort",
        "external_conformance",
    }:
        assert required in roles

    for row in closure["artifacts"]:
        path = REPO_ROOT / row["path"]
        assert path.is_file(), row["path"]
        assert DIGEST_RE.match(row["sha256"])
        assert row["sha256"] == _sha256_file(path), row["path"]


def test_zero_floors_are_all_zero(manifest: dict[str, Any]) -> None:
    floors = manifest["zero_floors"]
    assert set(floors) >= REQUIRED_ZERO_FLOORS
    for name in REQUIRED_ZERO_FLOORS:
        assert floors[name] == 0, name
    assert sum(floors.values()) == 0
    assert manifest["acceptance"]["all_zero_floors_are_zero"] is True


def test_predicates_reconstruct_nonadmissible_current_tree(
    manifest: dict[str, Any],
    release_predicate: dict[str, Any],
    rights_ir: dict[str, Any],
    portfolio_lock: dict[str, Any],
) -> None:
    predicates = manifest["predicates"]
    assert predicates["name"] == PREDICATE_NAME
    assert predicates["release_admissible"] is False
    assert manifest["acceptance"]["current_tree_release_admissible"] is False

    conjunct_ids = {row["id"] for row in predicates["conjuncts"]}
    assert REQUIRED_CONJUNCT_IDS <= conjunct_ids
    for row in predicates["conjuncts"]:
        assert "satisfied" in row
        assert row["blocks_release_when_unsatisfied"] is True

    # Unsatisfied conjuncts must include rights and immutable closure.
    by_id = {row["id"]: row for row in predicates["conjuncts"]}
    assert by_id["rights_resolution"]["satisfied"] is False
    assert by_id["immutable_dependency_closure"]["satisfied"] is False
    assert by_id["reproducibility_and_provenance"]["satisfied"] is False
    assert by_id["zero_floors"]["satisfied"] is True
    assert by_id["signature_binds_complete_closure"]["satisfied"] is True
    assert by_id["composed_workflow_trace"]["satisfied"] is True
    assert by_id["historical_receipt_not_current"]["satisfied"] is True

    record = predicates["qualification_record"]
    admissible, codes, extended = evaluate_terminal_admissible(
        manifest, release_predicate, record
    )
    assert admissible is False
    assert set(codes) == set(predicates["rejection_codes"])
    assert "mutable_ref" in codes
    assert "unresolved_mandatory_rights" in codes
    assert "nonreproducible_artifact" in {
        blocker["code"] for blocker in predicates["extended_blockers"]
    } or "nonreproducible_artifact" in extended

    # RightsIR mandatory blockers remain present.
    status_map = rights_ir["status_to_disposition"]
    vocab = rights_ir["disposition_vocabulary"]
    blocking_ids = {
        node["id"]
        for node in rights_ir["nodes"]
        if node.get("mandatory")
        and vocab[status_map[node["status"]]]["blocks_release"]
    }
    sealed_blocking = {row["node_id"] for row in manifest["rights"]["mandatory_blocking_nodes"]}
    assert blocking_ids == sealed_blocking
    assert manifest["rights"]["mandatory_rights_resolved"] is False
    assert manifest["rights"]["machine_clearance_attempted"] is False

    assert (
        portfolio_lock["current_tree_qualification"]["release_admissible"] is False
    )
    assert (
        release_predicate["current_tree_qualification"]["release_admissible"] is False
    )


def test_signature_binds_complete_closure_and_withholds_production_auth(
    manifest: dict[str, Any],
) -> None:
    signature = manifest["signature"]
    assert signature["alg"] == "ed25519"
    assert signature["covers"] == "complete_closure"
    assert signature["status"] == "withheld"
    assert signature["reason"] == "release_nonadmissible"
    assert signature["production_release_authorized"] is False
    assert signature["key_material_present"] is False
    assert signature["request"]["requested"] is True
    assert signature["request"]["authorized"] is False

    assert DIGEST_RE.match(signature["closure_identity_sha256"])
    assert DIGEST_RE.match(signature["payload_sha256"])
    assert reconstruct_signature_payload_sha256(manifest) == signature["payload_sha256"]

    artifact_digests = {row["sha256"] for row in manifest["closure"]["artifacts"]}
    bound = set(signature["bound_digests"])
    assert artifact_digests <= bound
    assert signature["closure_identity_sha256"] in bound
    assert manifest["acceptance"]["signatures_bind_complete_closure"] is True


def test_live_capabilities_and_reproducibility_remain_incomplete(
    manifest: dict[str, Any], cohort: dict[str, Any]
) -> None:
    live = manifest["live_capabilities"]
    assert live["cohort_sha256"] == _sha256_file(COHORT_PATH)
    assert live["local_filesystem"]["live_qualified"] is True
    assert live["local_filesystem"]["disposition"] == cohort["results"]["local_filesystem"][
        "disposition"
    ]
    assert live["pinned_ipfs"]["live_qualified"] is False
    assert live["iroh"]["live_qualified"] is False
    assert live["production_cohort_complete"] is False

    repro = manifest["reproducibility"]
    assert repro["immutable_dependency_closure_complete"] is False
    assert repro["release_admissible"] is False
    assert repro["signed_production_provenance_present"] is False
    assert repro["blocking_codes"]


def test_residual_risks_and_human_exceptions_are_explicit(
    manifest: dict[str, Any],
) -> None:
    assert manifest["residual_risks"]
    assert all(row["status"] == "open" for row in manifest["residual_risks"])
    exceptions = manifest["human_exceptions"]
    assert exceptions
    for row in exceptions:
        assert row["waives_zero_floor"] is False
        assert row["clears_release"] is False


def test_historical_wpd_receipt_does_not_satisfy_terminal_predicate(
    manifest: dict[str, Any],
) -> None:
    forbidden = {row["id"]: row for row in manifest["historical_receipts_forbidden"]}
    assert "historical:wpd-terminal-release-receipt" in forbidden
    row = forbidden["historical:wpd-terminal-release-receipt"]
    assert row["satisfies_facp_terminal_release"] is False
    path = REPO_ROOT / row["path"]
    assert path == WPD_HISTORICAL_PATH
    assert path.is_file()
    assert row["sha256"] == _sha256_file(path)

    historical = _load_json(path)
    assert historical.get("promotion_allowed") is True
    # Historical campaign pass must not flip the sealed FACP terminal verdict.
    assert manifest["predicates"]["release_admissible"] is False
    assert manifest["acceptance"]["historical_campaign_receipt_does_not_satisfy"] is True


@pytest.mark.parametrize(
    "fixture_id",
    sorted(REQUIRED_NEGATIVE_FIXTURE_IDS - {"pos:all-clear-synthetic"}),
)
def test_negative_fixtures_keep_release_nonadmissible(
    manifest: dict[str, Any],
    release_predicate: dict[str, Any],
    fixture_id: str,
) -> None:
    fixtures = {row["id"]: row for row in manifest["negative_fixtures"]}
    assert set(fixtures) >= REQUIRED_NEGATIVE_FIXTURE_IDS
    fixture = fixtures[fixture_id]
    assert fixture["expect_admissible"] is False

    base = copy.deepcopy(manifest["predicates"]["qualification_record"])
    base.update(fixture["mutation"])
    admissible, codes, extended = evaluate_terminal_admissible(
        manifest, release_predicate, base
    )
    assert admissible is False

    for code in fixture.get("expect_codes") or []:
        assert code in codes, (fixture_id, codes)
    for code in fixture.get("expect_extended_codes") or []:
        assert code in extended or code in {
            blocker["code"] for blocker in manifest["predicates"]["extended_blockers"]
        }, (fixture_id, extended)


def test_synthetic_all_clear_fixture_is_admissible_but_not_current_tree_claim(
    manifest: dict[str, Any], release_predicate: dict[str, Any]
) -> None:
    fixtures = {row["id"]: row for row in manifest["negative_fixtures"]}
    positive = fixtures["pos:all-clear-synthetic"]
    assert positive["synthetic_clearance_only"] is True
    assert positive["expect_admissible"] is True

    record = dict(positive["mutation"])
    admissible, codes, extended = evaluate_terminal_admissible(
        manifest, release_predicate, record
    )
    assert admissible is True
    assert codes == []
    assert extended == []

    # Synthetic clearance must not rewrite the sealed current-tree verdict.
    assert manifest["predicates"]["release_admissible"] is False
    assert manifest["acceptance"]["current_tree_release_admissible"] is False


def test_acceptance_flags_match_fail_closed_behavior(
    manifest: dict[str, Any],
) -> None:
    acceptance = manifest["acceptance"]
    assert acceptance["independent_verifier_reconstructs_manifest_identity"] is True
    assert (
        acceptance["independent_verifier_reconstructs_every_required_predicate"] is True
    )
    assert acceptance["all_zero_floors_are_zero"] is True
    assert acceptance["signatures_bind_complete_closure"] is True
    assert acceptance["unresolved_right_keeps_nonadmissible"] is True
    assert acceptance["stale_proof_or_capability_keeps_nonadmissible"] is True
    assert acceptance["mutable_dependency_keeps_nonadmissible"] is True
    assert acceptance["nonreproducible_artifact_keeps_nonadmissible"] is True
    assert acceptance["simulated_evidence_keeps_nonadmissible"] is True
    assert acceptance["unsupported_claim_keeps_nonadmissible"] is True
    assert acceptance["historical_campaign_receipt_does_not_satisfy"] is True
    assert acceptance["current_tree_release_admissible"] is False
    assert acceptance["production_publish_or_deploy_performed"] is False


def test_manifest_contains_no_secret_key_material(manifest: dict[str, Any]) -> None:
    keys = _walk_keys(manifest)
    leaked = SECRET_OR_PRIVATE_KEYS & keys
    assert not leaked, leaked
    sanitization = manifest["sanitization"]
    assert sanitization["credentials_stored"] is False
    assert sanitization["private_or_secret_values_present"] is False
    assert sanitization["key_material_in_artifact_forbidden"] is True
    assert manifest["signature"]["key_material_present"] is False


def test_composed_workflow_terminal_path_is_bound(
    manifest: dict[str, Any], composed: dict[str, Any]
) -> None:
    assert manifest["closure"]["terminal_workflow"] == composed["terminal_workflow"]
    assert manifest["closure"]["composed_workflow_status"] == "sealed"
    assert composed["status"] == "sealed"
    assert tuple(composed["terminal_workflow"]) == (
        "swissknife_request",
        "host_authentication_and_admission",
        "datasets_semantic_compilation_translation_receipt",
        "accelerate_scheduling_and_observed_execution",
        "kit_immutable_persistence_current_pointer",
        "swissknife_evidence_presentation",
    )
