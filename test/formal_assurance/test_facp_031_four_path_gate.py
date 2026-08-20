"""FACP-031: seal the four-path FCA day-90 gate.

Acceptance (taskboard):
- No migrated path exhibits import mutation, false success, mock-to-live,
  pseudo-CID, hermetic-to-live, candidate-to-current, or browser-to-authority
  promotion.
- Gate binds all exact commits and limitations.

Producer migration artifacts are immutable inputs; this task writes only the
sealed day-90 receipt and this hermetic fan-in test.
"""

from __future__ import annotations

import hashlib
import importlib.util
import json
import os
import re
import subprocess
import sys
import types
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from facp_historical_git import (
    assert_historical_ancestor,
    blob_bytes,
    git_output,
    superproject_gitlink,
    tree_path_exists,
)

GATE_PATH = (
    REPO_ROOT
    / "implementation_plan"
    / "formal_assurance_control_plane"
    / "gates"
    / "day90_four_path.json"
)
FCA_GATE_PATH = (
    REPO_ROOT
    / "implementation_plan"
    / "formal_assurance_control_plane"
    / "gates"
    / "formal_claim_algebra_v1.json"
)
SCHEDULER_PATH = REPO_ROOT / "config" / "formal_assurance_control_plane_scheduler.json"
VECTORS_PATH = (
    REPO_ROOT / "swissknife" / "test" / "formal-assurance" / "browser-authority-vectors.json"
)

GATE_SCHEMA = "facp/day90-gate@1"
TASK_ID = "FACP-031"
GOAL_ID = "FACP-G200"
BUNDLE = "facp/migration/gate"
VOCAB_SCHEMA = "facp/formal-claim-algebra-v1@1"

REQUIRED_EVIDENCE_SUBSET = {
    "import_purity",
    "typed_outcomes",
    "mock_provenance",
    "canonical_cid",
    "live_qualification",
    "proof_roles",
    "browser_nonauthority",
    "ambiguous_claim_scan",
}

REQUIRED_DEPENDS_ON = {
    "FACP-022",
    "FACP-023",
    "FACP-025",
    "FACP-026",
    "FACP-027",
    "FACP-028",
    "FACP-030",
}

REQUIRED_SHARED_INPUTS = {
    "FACP-020",
    "FACP-021",
    "FACP-024",
    "FACP-029",
}

FORBIDDEN_PROMOTIONS = {
    "import_mutation",
    "false_success",
    "mock_to_live",
    "pseudo_cid",
    "hermetic_to_live",
    "candidate_to_current",
    "browser_to_authority",
}

MIGRATED_REPOS = {
    "external/ipfs_accelerate",
    "external/ipfs_datasets",
    "external/ipfs_kit",
    "swissknife",
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

FORBIDDEN_GATE_CLAIM_KEYS = {
    "success",
    "available",
    "supported",
    "verified",
    "proven",
    "authorized",
    "allowed",
    "current",
    "production",
    "capability",
}

NOW = datetime(2026, 8, 19, 12, 0, tzinfo=UTC)


def _sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


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


def _historical_blob(binding: dict[str, Any], path: str) -> bytes:
    """Read a receipt input from its immutable controller forest."""

    controller_commit = binding["controller_commit"]
    for entry in binding["planning_forest"]:
        repository_path = entry["path"]
        prefix = f"{repository_path}/"
        if not path.startswith(prefix):
            continue
        recorded_commit = entry["gitlink_commit"]
        assert (
            superproject_gitlink(REPO_ROOT, controller_commit, repository_path) == recorded_commit
        )
        current_commit = superproject_gitlink(REPO_ROOT, "HEAD", repository_path)
        assert_historical_ancestor(REPO_ROOT / repository_path, recorded_commit, current_commit)
        relative_path = path.removeprefix(prefix)
        assert tree_path_exists(REPO_ROOT / repository_path, recorded_commit, relative_path)
        return blob_bytes(REPO_ROOT / repository_path, recorded_commit, relative_path)

    assert tree_path_exists(REPO_ROOT, controller_commit, path)
    return blob_bytes(REPO_ROOT, controller_commit, path)


def _historical_sha256(binding: dict[str, Any], path: str) -> str:
    return hashlib.sha256(_historical_blob(binding, path)).hexdigest()


def _canonical_content_sha256(gate: dict[str, Any]) -> str:
    without_digest = {key: value for key, value in gate.items() if key != "content_sha256"}
    canonical = json.dumps(without_digest, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def _ensure_path(path: Path) -> None:
    token = str(path)
    if token not in sys.path:
        sys.path.insert(0, token)


def _load_assurance_module(package_root: Path, package_name: str, module_file: Path) -> Any:
    """Load ``package_name.assurance.<stem>`` from an exact worktree path."""

    assurance_dir = module_file.parent
    package_mod_name = package_name
    assurance_mod_name = f"{package_name}.assurance"
    module_mod_name = f"{package_name}.assurance.{module_file.stem}"

    if package_mod_name not in sys.modules:
        try:
            __import__(package_mod_name)
        except ImportError:
            pkg = types.ModuleType(package_mod_name)
            pkg.__path__ = [str(package_root / package_name)]  # type: ignore[attr-defined]
            sys.modules[package_mod_name] = pkg

    if assurance_mod_name not in sys.modules:
        assurance_pkg = types.ModuleType(assurance_mod_name)
        assurance_pkg.__path__ = [str(assurance_dir)]  # type: ignore[attr-defined]
        sys.modules[assurance_mod_name] = assurance_pkg
        sys.modules[package_mod_name].assurance = assurance_pkg  # type: ignore[attr-defined]

    spec = importlib.util.spec_from_file_location(module_mod_name, module_file)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_mod_name] = module
    spec.loader.exec_module(module)
    setattr(sys.modules[assurance_mod_name], module_file.stem, module)
    return module


def _load_module(path: Path) -> Any:
    spec = importlib.util.spec_from_file_location(path.stem, path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[path.stem] = module
    spec.loader.exec_module(module)
    return module


@pytest.fixture(scope="module")
def gate() -> dict[str, Any]:
    assert GATE_PATH.is_file(), f"missing day-90 gate: {GATE_PATH}"
    payload = json.loads(GATE_PATH.read_text(encoding="utf-8"))
    assert isinstance(payload, dict)
    return payload


@pytest.fixture(scope="module")
def scheduler() -> dict[str, Any]:
    assert SCHEDULER_PATH.is_file(), f"missing scheduler: {SCHEDULER_PATH}"
    payload = json.loads(SCHEDULER_PATH.read_text(encoding="utf-8"))
    assert isinstance(payload, dict)
    return payload


def test_gate_schema_task_and_bundle_binding(gate: dict[str, Any]) -> None:
    assert gate["schema"] == GATE_SCHEMA
    assert gate["schema_version"] == 1
    assert gate["task_id"] == TASK_ID
    assert gate["goal_id"] == GOAL_ID
    assert gate["bundle"] == BUNDLE
    assert gate["vocabulary_schema"] == VOCAB_SCHEMA
    assert gate["status"] == "sealed"
    assert gate["behavior_change"] is False
    assert gate["title"]
    assert gate["generated_at"]
    assert set(gate["evidence_subset"]) >= REQUIRED_EVIDENCE_SUBSET
    assert gate["fca_conformance_gate_path"].endswith("formal_claim_algebra_v1.json")
    assert gate["fca_conformance_gate_sha256"] == _historical_sha256(
        gate["source_binding"], str(FCA_GATE_PATH.relative_to(REPO_ROOT))
    )
    assert DIGEST_RE.match(gate["fca_conformance_gate_sha256"])


def test_policy_forbids_unsafe_effects_and_waivers(gate: dict[str, Any]) -> None:
    policy = gate["policy"]
    assert policy["producer_artifacts_immutable"] is True
    assert policy["discovery_is_not_completion"] is True
    assert policy["provider_authority"] == "none"
    assert policy["fail_closed"] is True
    assert policy["no_unqualified_production_claim"] is True
    assert policy["no_live_external_effect"] is True
    assert policy["no_release_claim"] is True
    assert policy["no_waive_missing_migration"] is True
    assert policy["no_infer_rights"] is True
    assert policy["migrated_repository_commits_immutable"] is True
    prohibited = set(policy["prohibited_effects"])
    assert {
        "live_external_effect",
        "release_claim",
        "waive_missing_migration",
        "infer_rights",
        "construct_forbidden_promotion",
        "introduce_unqualified_production_claim",
        "provider_authored_completion",
    } <= prohibited


def test_content_sha256_binds_canonical_gate_record(gate: dict[str, Any]) -> None:
    assert DIGEST_RE.match(gate["content_sha256"])
    binding = gate["content_binding"]
    assert binding["alg"] == "sha256"
    assert "sort-keys" in binding["canonicalization"]
    assert binding["covers"] == "gate_record_excluding_content_sha256"
    assert _canonical_content_sha256(gate) == gate["content_sha256"]


def test_source_binding_exact_commits_and_producer_digests(
    gate: dict[str, Any],
) -> None:
    binding = gate["source_binding"]
    assert FULL_SHA_RE.match(binding["controller_commit"])
    assert FULL_SHA_RE.match(binding["controller_tree"])
    assert_historical_ancestor(REPO_ROOT, binding["controller_commit"])
    assert binding["controller_tree"] == git_output(
        REPO_ROOT, "rev-parse", f"{binding['controller_commit']}^{{tree}}"
    )
    assert binding["scheduler_config"] == ("config/formal_assurance_control_plane_scheduler.json")
    historical_scheduler = json.loads(_historical_blob(binding, binding["scheduler_config"]))

    forest = {entry["path"]: entry for entry in binding["planning_forest"]}
    assert set(forest) == set(PLANNING_FOREST_PATHS)
    sb = historical_scheduler["source_binding"]
    for path, entry in forest.items():
        assert FULL_SHA_RE.match(entry["gitlink_commit"])
        assert entry["gitlink_commit"] == superproject_gitlink(
            REPO_ROOT, binding["controller_commit"], path
        )
        assert_historical_ancestor(
            REPO_ROOT / path,
            entry["gitlink_commit"],
            superproject_gitlink(REPO_ROOT, "HEAD", path),
        )
        field = entry["planning_revision_field"]
        assert entry["scheduler_planning_revision"] == sb[field]
        assert entry["matches_scheduler_planning_revision"] is (
            entry["gitlink_commit"] == sb[field]
        )

    assert set(binding["depends_on"]) == REQUIRED_DEPENDS_ON
    assert set(binding["shared_producer_inputs"]) == REQUIRED_SHARED_INPUTS

    producers = {row["task_id"]: row for row in binding["producer_inputs"]}
    assert REQUIRED_DEPENDS_ON | REQUIRED_SHARED_INPUTS <= set(producers)
    for row in binding["producer_inputs"]:
        assert row["role"]
        assert isinstance(row["paths"], list) and row["paths"]
        for item in row["paths"]:
            assert DIGEST_RE.match(item["sha256"])
            assert item["sha256"] == _historical_sha256(binding, item["path"]), item["path"]


def test_migrated_paths_bind_four_repositories_and_commits(gate: dict[str, Any]) -> None:
    migrated = gate["migrated_paths"]
    assert migrated["migration_complete"] is True
    assert migrated["four_path_count"] == 4
    repos = {row["path"]: row for row in migrated["repositories"]}
    assert set(repos) == MIGRATED_REPOS
    binding = gate["source_binding"]
    for path, row in repos.items():
        assert FULL_SHA_RE.match(row["gitlink_commit"])
        assert row["gitlink_commit"] == superproject_gitlink(
            REPO_ROOT, binding["controller_commit"], path
        )
        assert_historical_ancestor(
            REPO_ROOT / path,
            row["gitlink_commit"],
            superproject_gitlink(REPO_ROOT, "HEAD", path),
        )
        assert row["lane"]
        assert row["goal_id"].startswith("FACP-G2")
        assert isinstance(row["tasks"], list) and row["tasks"]
        for item in row["assurance_module_digests"]:
            assert item["sha256"] == _historical_sha256(binding, item["path"])


def test_forbidden_promotions_and_limitations_bound(gate: dict[str, Any]) -> None:
    promotions = gate["forbidden_promotions"]
    assert set(promotions) == FORBIDDEN_PROMOTIONS
    matrix = gate["promotion_denial_matrix"]
    assert set(matrix) == FORBIDDEN_PROMOTIONS
    for name in FORBIDDEN_PROMOTIONS:
        row = promotions[name]
        assert row["blocked"] is True
        assert matrix[name] is False
        assert row["repository"] in MIGRATED_REPOS
        assert row["producer_tasks"]
        assert row["oracle"]
        assert row["evidence_keys"]
        assert row["adapter_sha256"] == _historical_sha256(
            gate["source_binding"], row["adapter_path"]
        )

    limitations = gate["limitations"]
    assert isinstance(limitations, list) and len(limitations) >= 6
    ids = {item["id"] for item in limitations}
    assert "lim:hermetic-fanin-only" in ids
    assert "lim:no-release-claim" in ids
    assert "lim:inventoried-seams-only" in ids
    for item in limitations:
        assert item["id"].startswith("lim:")
        assert item["statement"]

    acceptance = gate["acceptance"]
    assert acceptance["no_import_mutation"] is True
    assert acceptance["no_false_success"] is True
    assert acceptance["no_mock_to_live"] is True
    assert acceptance["no_pseudo_cid"] is True
    assert acceptance["no_hermetic_to_live"] is True
    assert acceptance["no_candidate_to_current"] is True
    assert acceptance["no_browser_to_authority"] is True
    assert acceptance["gate_binds_exact_commits"] is True
    assert acceptance["gate_binds_limitations"] is True
    assert acceptance["all_forbidden_promotions_blocked"] is True


def test_gate_does_not_introduce_unqualified_production_claim_fields(
    gate: dict[str, Any],
) -> None:
    guarded_roots = {
        "",
        "acceptance",
        "policy",
        "promotion_denial_matrix",
        "ambiguous_claim_scan",
        "migrated_paths",
    }

    def walk(node: Any, path: str = "") -> None:
        if isinstance(node, dict):
            for key, value in node.items():
                key_l = str(key).lower()
                if key_l in FORBIDDEN_GATE_CLAIM_KEYS and path in guarded_roots:
                    pytest.fail(f"unqualified production claim field {key!r} at {path or '<root>'}")
                walk(value, f"{path}.{key}" if path else str(key))
        elif isinstance(node, list):
            for index, item in enumerate(node):
                walk(item, f"{path}[{index}]")

    walk(gate)
    assert gate["behavior_change"] is False
    assert gate["ambiguous_claim_scan"]["migration_adapters_unsafe_promotion"] is False
    assert gate["ambiguous_claim_scan"]["no_new_unqualified_production_claim"] is True


def test_import_mutation_blocked_on_datasets_path() -> None:
    _ensure_path(REPO_ROOT / "external" / "ipfs_datasets")
    init = _load_assurance_module(
        REPO_ROOT / "external" / "ipfs_datasets",
        "ipfs_datasets_py",
        REPO_ROOT
        / "external"
        / "ipfs_datasets"
        / "ipfs_datasets_py"
        / "assurance"
        / "initialization.py",
    )
    init.reset_initialization_state()
    assert init.is_initialized() is False
    assert init.is_install_authorized() is False
    assert init.is_legacy_opt_in_authorized() is False

    failed = init.initialize_datasets()
    assert failed.outcome == "Failed"
    assert failed.code == "missing_state_root"
    assert failed.ok is False
    assert failed.details.get("implicit_home_forbidden") is True

    env = init.hermetic_core_import_env(base={})
    assert isinstance(env, dict)
    assert env["IPFS_DATASETS_AUTO_INSTALL"] == "0"
    assert env["IPFS_KIT_AUTO_INSTALL_DEPS"] == "0"
    assert env["IPFS_AUTO_INSTALL"] == "0"
    assert env["IPFS_DATASETS_PY_MINIMAL_IMPORTS"] == "1"
    # Under a hermetic fragment (no ambient truthy legacy flags), silent
    # default-on remains impossible without explicit authorization.
    cleared = {key: os.environ[key] for key in init._LEGACY_AUTO_INSTALL_KEYS if key in os.environ}
    try:
        for key in init._LEGACY_AUTO_INSTALL_KEYS:
            os.environ.pop(key, None)
        assert init.legacy_opt_in_cannot_silently_default_on() is True
    finally:
        os.environ.update(cleared)


def test_false_success_blocked_on_datasets_path() -> None:
    _ensure_path(REPO_ROOT / "external" / "ipfs_datasets")
    outcomes = _load_assurance_module(
        REPO_ROOT / "external" / "ipfs_datasets",
        "ipfs_datasets_py",
        REPO_ROOT / "external" / "ipfs_datasets" / "ipfs_datasets_py" / "assurance" / "outcomes.py",
    )
    assert outcomes.UNSAFE_PROMOTION is False
    missing = outcomes.unavailable_missing_backend(operation="download", backend="ipfs")
    assert missing.outcome == "Unavailable"
    assert missing.ok is False
    assert missing.unsafe_promotion is False

    replaced = outcomes.replace_false_success_fallback(
        family="download_fallback_stub_success",
        backend_available=False,
    )
    assert replaced.outcome == "Unavailable"
    assert replaced.ok is False
    assert replaced.defect_id == "DS-FALSE-001"

    attempted = outcomes.begin_attempt(operation="download")
    assert attempted.outcome == "Attempted"
    assert attempted.ok is False

    compat = outcomes.project_compatibility(
        {"status": "success", "dataset": None, "operation": "download"}
    )
    assert compat.outcome in {"Unavailable", "Simulated", "Unknown", "Failed", "Rejected"}
    assert compat.ok is False
    assert compat.unsafe_promotion is False


def test_mock_to_live_blocked_on_accelerate_path() -> None:
    _ensure_path(REPO_ROOT / "external" / "ipfs_accelerate")
    cap = _load_assurance_module(
        REPO_ROOT / "external" / "ipfs_accelerate",
        "ipfs_accelerate_py",
        REPO_ROOT
        / "external"
        / "ipfs_accelerate"
        / "ipfs_accelerate_py"
        / "assurance"
        / "capability_outcomes.py",
    )
    assert cap.UNSAFE_PROMOTION is False
    route = cap.route_backend("cuda", probe=None, now=NOW)
    assert route.admitted is False
    assert route.outcome.outcome == "Unavailable"
    assert route.outcome.ok is False

    sim = cap.select_simulation_namespace("mock_worker", explicit_test_mode=False)
    assert sim.outcome == "Unavailable"
    assert sim.ok is False
    assert "test_mode" in sim.code or "simulation" in sim.code

    inferred = cap.resolve_inference_outcome(
        backend="cuda",
        simulated=True,
        mock_handler=True,
        explicit_test_mode=False,
        now=NOW,
    )
    assert inferred.outcome == "Unavailable"
    assert inferred.ok is False

    refused = cap.refuse_compatibility_success(
        {"success": True, "available": True, "implementation_type": "REAL"}
    )
    assert refused.outcome == "Unavailable"
    assert refused.ok is False
    assert refused.unsafe_promotion is False


def test_pseudo_cid_blocked_on_accelerate_path() -> None:
    _ensure_path(REPO_ROOT / "external" / "ipfs_accelerate")
    identity = _load_assurance_module(
        REPO_ROOT / "external" / "ipfs_accelerate",
        "ipfs_accelerate_py",
        REPO_ROOT
        / "external"
        / "ipfs_accelerate"
        / "ipfs_accelerate_py"
        / "assurance"
        / "content_identity.py",
    )
    with pytest.raises(identity.ContentIdentityError) as raw_exc:
        identity.reject_pseudo_cid("a" * 64)
    assert raw_exc.value.integrity == identity.Integrity.UNCHECKED
    assert raw_exc.value.code == identity.IdentityErrorCode.PSEUDO_CID_RAW_HEX

    with pytest.raises(identity.ContentIdentityError) as qm_exc:
        identity.reject_pseudo_cid("Qm" + ("a" * 44))
    assert qm_exc.value.integrity == identity.Integrity.UNCHECKED

    minted = identity.mint_content_identity(b"facp-031-day90-identity")
    assert minted.cid.startswith("bafy") or minted.cid.startswith("bafk")
    assert len(minted.digest_hex) == 64
    mutated = identity.verify_content_identity(
        minted.cid, identity.flip_one_bit(minted.canonical_bytes)
    )
    assert mutated.ok is False
    assert mutated.integrity == identity.Integrity.UNCHECKED


def test_hermetic_to_live_blocked_on_kit_path() -> None:
    _ensure_path(REPO_ROOT / "external" / "ipfs_kit")
    live = _load_assurance_module(
        REPO_ROOT / "external" / "ipfs_kit",
        "ipfs_kit_py",
        REPO_ROOT / "external" / "ipfs_kit" / "ipfs_kit_py" / "assurance" / "live_backend_gate.py",
    )
    assert live.UNSAFE_PROMOTION is False

    empty = live.select_storage_backend([], now=NOW)
    assert empty.closed_outcome == live.CLOSED_OUTCOME_UNAVAILABLE
    assert empty.production_supported is False
    assert empty.fallback_attempted is False
    assert empty.selected_backend is None

    base = live.current_live_evidence("iroh", now=NOW)
    for origin, environment in (
        ("hermetic", "hermetic"),
        ("fixture", "test"),
        ("configured", "configured"),
        ("declared", "hermetic"),
    ):
        evidence = base.with_overrides(origin=origin, environment=environment)
        assessment = live.assess_live_evidence(evidence, now=NOW)
        assert assessment.live_qualified is False
        assert assessment.demotion_reason is live.DemotionReason.NON_LIVE

    demoted = live.select_storage_backend(
        [base.with_overrides(origin="hermetic", environment="hermetic")],
        now=NOW,
    )
    assert demoted.closed_outcome == live.CLOSED_OUTCOME_UNAVAILABLE
    assert demoted.production_supported is False
    assert demoted.fallback_attempted is False


def test_candidate_to_current_blocked_on_kit_path() -> None:
    _ensure_path(REPO_ROOT / "external" / "ipfs_kit")
    proof = _load_assurance_module(
        REPO_ROOT / "external" / "ipfs_kit",
        "ipfs_kit_py",
        REPO_ROOT / "external" / "ipfs_kit" / "ipfs_kit_py" / "assurance" / "proof_role_gate.py",
    )
    assert proof.UNSAFE_PROMOTION is False
    candidate = proof.candidate_evidence(candidate_cid="bafycandidate-facp031-0001")
    assert proof.candidate_implies_admitted(candidate) is False

    admission = proof.evaluate_admission(candidate, now=NOW)
    assert admission.allowed is False
    assert admission.implies_admitted is False

    promotion = proof.evaluate_current_promotion(candidate, now=NOW)
    assert promotion.allowed is False
    assert promotion.closed_outcome in {
        proof.CLOSED_OUTCOME_REJECTED,
        proof.CLOSED_OUTCOME_UNKNOWN,
        proof.CLOSED_OUTCOME_UNAVAILABLE,
    }

    # Stale admitted evidence also cannot become current.
    admitted_stale = proof.ProofRoleEvidence(
        role=proof.ProofRole.ADMITTED.value,
        proof="verified",
        freshness="stale",
        candidate_cid="bafycandidate-facp031-0001",
        authorization_cid="bafyauth-facp031-0001",
        proof_key="proof-key-facp031",
        verifier_identity="verifier-facp031",
        source_closure="bafysource-facp031-0001",
    )
    stale_promo = proof.evaluate_current_promotion(admitted_stale, now=NOW)
    assert stale_promo.allowed is False


def test_browser_to_authority_blocked_on_swissknife_path() -> None:
    assert VECTORS_PATH.is_file()
    vectors = json.loads(VECTORS_PATH.read_text(encoding="utf-8"))
    assert vectors["schema"] == "facp/browser-nonauthority@1"
    assert vectors["task_id"] == "FACP-029"

    facp029 = _load_module(
        REPO_ROOT / "test" / "formal_assurance" / "test_facp_029_swissknife_browser_vectors.py"
    )
    facp030 = _load_module(
        REPO_ROOT / "test" / "formal_assurance" / "test_facp_030_swissknife_host_projection.py"
    )

    paired = vectors["paired_vectors"]
    assert isinstance(paired, list) and paired
    for case in paired:
        left = facp029.project_host_authorization_input(case["request_a"])
        right = facp029.project_host_authorization_input(case["request_b"])
        assert left == right
        assert case["host_authorization_input_a"] == case["host_authorization_input_b"]
        assert case["host_authorization_result_a"] == case["host_authorization_result_b"]

    legacy = next(
        seed
        for seed in vectors["failing_seeds"]
        if seed["seed_id"] == "cx-sk-auth-default-granted-consent"
    )
    assert legacy["accepted_evidence"] is False
    assert vectors["authority"]["browser_fields_are_not_host_admission"] is True
    assert (
        vectors["acceptance"]["paired_browser_authority_deltas_preserve_host_authorization"] is True
    )

    gateway = (
        REPO_ROOT / "swissknife" / "src" / "services" / "mcp" / "formalAssuranceGateway.ts"
    ).read_text(encoding="utf-8")
    assert "consent" in gateway.lower()
    assert "absent" in gateway
    assert "must never construct allow/policy/authority" in gateway

    request = facp030.project_canonical_host_request(
        {
            "method": "tools/call",
            "resource_id": "virtual-desktop",
            "arguments": {"action": "open", "path": "/tmp/demo"},
            "actor_id": "operator:facp031",
            "session_id": "session:facp031",
            "consent": "granted",
            "allow": True,
            "policy_decision": {"effect": "allow"},
        }
    )
    assert request["consent"] == "absent"
    assert request["authority_decision"] is None
    decision = facp030.project_host_decision_from_bindings(request)
    assert decision["outcome"] == "deny"
    assert decision["authority"] == "absent"


def test_ambiguous_claim_scan_binds_migration_adapters(gate: dict[str, Any]) -> None:
    scan = gate["ambiguous_claim_scan"]
    assert scan["bound"] is True
    assert scan["allowlist_cannot_suppress_corpus"] is True
    assert scan["migration_adapters_unsafe_promotion"] is False
    assert scan["no_new_unqualified_production_claim"] is True

    fca_gate = json.loads(FCA_GATE_PATH.read_text(encoding="utf-8"))
    assert fca_gate["scanner_corpus_score"]["score"] == 1.0
    assert fca_gate["scanner_corpus_score"]["allowlist_cannot_suppress_corpus"] is True

    for path in scan["scanned_adapter_paths"]:
        assert (REPO_ROOT / path).is_file(), path

    # Python migration adapters must keep the closed unsafe_promotion=false contract.
    _ensure_path(REPO_ROOT / "external" / "ipfs_datasets")
    _ensure_path(REPO_ROOT / "external" / "ipfs_accelerate")
    _ensure_path(REPO_ROOT / "external" / "ipfs_kit")
    for package_root, package_name, relative in (
        (
            REPO_ROOT / "external" / "ipfs_datasets",
            "ipfs_datasets_py",
            "ipfs_datasets_py/assurance/outcomes.py",
        ),
        (
            REPO_ROOT / "external" / "ipfs_accelerate",
            "ipfs_accelerate_py",
            "ipfs_accelerate_py/assurance/capability_outcomes.py",
        ),
        (
            REPO_ROOT / "external" / "ipfs_kit",
            "ipfs_kit_py",
            "ipfs_kit_py/assurance/live_backend_gate.py",
        ),
        (
            REPO_ROOT / "external" / "ipfs_kit",
            "ipfs_kit_py",
            "ipfs_kit_py/assurance/proof_role_gate.py",
        ),
    ):
        module = _load_assurance_module(package_root, package_name, package_root / relative)
        assert module.UNSAFE_PROMOTION is False
