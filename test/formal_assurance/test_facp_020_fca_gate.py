"""FACP-020: seal formal-claim-algebra-v1 conformance gate.

Acceptance (taskboard):
- All implementations agree.
- No forbidden promotion is constructible.
- No unqualified production claim is newly introduced.
- Receipt binds exact source/dependencies and explicitly excludes the
  four-path migration until FACP-031.

Producer artifacts are immutable inputs; this task writes only the sealed
gate receipt and this hermetic fan-in test.
"""

from __future__ import annotations

import hashlib
import importlib.util
import json
import re
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
    / "formal_claim_algebra_v1.json"
)
SCHEDULER_PATH = REPO_ROOT / "config" / "formal_assurance_control_plane_scheduler.json"
TCB_PATH = (
    REPO_ROOT
    / "implementation_plan"
    / "formal_assurance_control_plane"
    / "baseline"
    / "trusted_computing_base.json"
)
CORPUS_PATH = (
    REPO_ROOT
    / "implementation_plan"
    / "formal_assurance_control_plane"
    / "baseline"
    / "defect_corpus.jsonl"
)
DAY90_GATE_PATH = (
    REPO_ROOT
    / "implementation_plan"
    / "formal_assurance_control_plane"
    / "gates"
    / "day90_four_path.json"
)

GATE_SCHEMA = "facp/fca-conformance@1"
TASK_ID = "FACP-020"
GOAL_ID = "FACP-G100"
BUNDLE = "facp/fca/gate"
RELEASE = "formal-claim-algebra-v1"
VOCAB_SCHEMA = "facp/formal-claim-algebra-v1@1"
PINNED_LEAN = "4.33.0"

REQUIRED_EVIDENCE_SUBSET = {
    "theorem_toolchain_identities",
    "vector_digests",
    "cross_language_transition_matrix",
    "compatibility_loss_report",
    "scanner_corpus_score",
}

REQUIRED_DEPENDS_ON = {
    "FACP-012",
    "FACP-014",
    "FACP-015",
    "FACP-017",
    "FACP-018",
    "FACP-019",
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
PROHIBITED_RE = re.compile(r"\b(sorry|admit|axiom)\b")
THEOREM_RE = re.compile(r"^theorem\s+(\w+)\b", re.MULTILINE)

# Unqualified production claim shapes that must not appear as newly introduced
# gate authority fields.
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
    """Read a receipt input from the exact controller forest that sealed it."""

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


def _lean_without_comments(text: str) -> str:
    stripped = re.sub(r"/-.*?-/", "", text, flags=re.DOTALL)
    return re.sub(r"--.*?$", "", stripped, flags=re.MULTILINE)


def _load_module(path: Path) -> Any:
    spec = importlib.util.spec_from_file_location(path.stem, path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _ensure_validators_path() -> None:
    tests_py = REPO_ROOT / "Mcp-Plus-Plus" / "tests-py"
    if str(tests_py) not in sys.path:
        sys.path.insert(0, str(tests_py))


def _ensure_accelerate_path() -> None:
    accel = REPO_ROOT / "external" / "ipfs_accelerate"
    if str(accel) not in sys.path:
        sys.path.insert(0, str(accel))


def _ensure_kit_path() -> None:
    kit = REPO_ROOT / "external" / "ipfs_kit"
    if str(kit) not in sys.path:
        sys.path.insert(0, str(kit))


def _canonical_content_sha256(gate: dict[str, Any]) -> str:
    without_digest = {key: value for key, value in gate.items() if key != "content_sha256"}
    canonical = json.dumps(without_digest, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def _scannable_seed_ids(entries: list[dict[str, Any]]) -> list[str]:
    seed_ids: list[str] = []
    for entry in entries:
        spans = entry.get("source_spans") or []
        if not spans:
            continue
        if all(
            isinstance(span.get("start_line"), int)
            and span["start_line"] >= 1
            and isinstance(span.get("end_line"), int)
            and span["end_line"] >= span["start_line"]
            for span in spans
        ):
            seed_ids.append(str(entry["seed_id"]))
    return seed_ids


@pytest.fixture(scope="module")
def gate() -> dict[str, Any]:
    assert GATE_PATH.is_file(), f"missing FCA gate: {GATE_PATH}"
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
    assert gate["release"] == RELEASE
    assert gate["vocabulary_schema"] == VOCAB_SCHEMA
    assert gate["status"] == "sealed"
    assert gate["behavior_change"] is False
    assert gate["title"]
    assert gate["generated_at"]
    assert set(gate["evidence_subset"]) >= REQUIRED_EVIDENCE_SUBSET


def test_policy_excludes_four_path_and_forbids_unsafe_effects(gate: dict[str, Any]) -> None:
    policy = gate["policy"]
    assert policy["producer_artifacts_immutable"] is True
    assert policy["discovery_is_not_completion"] is True
    assert policy["provider_authority"] == "none"
    assert policy["four_path_migration_excluded_until"] == "FACP-031"
    assert policy["no_unqualified_production_claim"] is True
    assert policy["fail_closed"] is True
    prohibited = set(policy["prohibited_effects"])
    assert {
        "mark_migrated_paths_complete",
        "accept_stale_or_partial_language_results",
        "provider_authored_completion",
        "construct_forbidden_promotion",
        "introduce_unqualified_production_claim",
    } <= prohibited


def test_content_sha256_binds_canonical_gate_record(gate: dict[str, Any]) -> None:
    assert DIGEST_RE.match(gate["content_sha256"])
    binding = gate["content_binding"]
    assert binding["alg"] == "sha256"
    assert "sort-keys" in binding["canonicalization"]
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

    assert binding["spec_sha256"] == _historical_sha256(binding, binding["spec_path"])

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
    assert set(binding["shared_producer_inputs"]) == {"FACP-013", "FACP-016"}

    producers = {row["task_id"]: row for row in binding["producer_inputs"]}
    assert REQUIRED_DEPENDS_ON | {"FACP-013", "FACP-016"} <= set(producers)
    for row in binding["producer_inputs"]:
        assert row["role"]
        assert isinstance(row["paths"], list) and row["paths"]
        for item in row["paths"]:
            assert DIGEST_RE.match(item["sha256"])
            assert item["sha256"] == _historical_sha256(binding, item["path"]), item["path"]


def test_theorem_toolchain_identities(gate: dict[str, Any]) -> None:
    identities = gate["theorem_toolchain_identities"]
    binding = gate["source_binding"]
    assert identities["schema"] == "facp/illegal-promotion-proof@1"
    assert identities["lean_pinned_version"] == PINNED_LEAN
    assert identities["lean_commit"]
    assert identities["prohibited_declarations_absent"] is True

    tcb_bytes = _historical_blob(binding, str(TCB_PATH.relative_to(REPO_ROOT)))
    tcb = json.loads(tcb_bytes)
    lean = next(component for component in tcb["components"] if component.get("name") == "lean4")
    assert lean["version"] == identities["lean_pinned_version"]
    assert identities["lean_commit"] in (lean.get("raw") or "")
    assert identities["tcb_sha256"] == hashlib.sha256(tcb_bytes).hexdigest()

    promotion = _historical_blob(binding, identities["promotion_lean_path"])
    basic = _historical_blob(binding, identities["basic_lean_path"])
    lakefile = _historical_blob(binding, identities["lakefile_path"])
    assert identities["promotion_lean_sha256"] == hashlib.sha256(promotion).hexdigest()
    assert identities["basic_lean_sha256"] == hashlib.sha256(basic).hexdigest()
    assert identities["lakefile_sha256"] == hashlib.sha256(lakefile).hexdigest()

    text = promotion.decode("utf-8")
    theorems = THEOREM_RE.findall(text)
    assert identities["theorem_count"] == len(theorems) >= 40
    assert identities["theorem_names"] == theorems
    assert not PROHIBITED_RE.search(_lean_without_comments(text))


def test_vector_digests_and_counts(gate: dict[str, Any]) -> None:
    digests = gate["vector_digests"]
    vectors_path = REPO_ROOT / digests["vectors_path"]
    rules_path = REPO_ROOT / digests["rules_path"]
    envelope_path = REPO_ROOT / digests["envelope_schema_path"]
    assert digests["vectors_sha256"] == _sha256_file(vectors_path)
    assert digests["rules_sha256"] == _sha256_file(rules_path)
    assert digests["envelope_schema_sha256"] == _sha256_file(envelope_path)

    vectors = json.loads(vectors_path.read_text(encoding="utf-8"))
    assert digests["positive_vector_count"] == len(vectors["positive_vectors"])
    assert digests["negative_vector_count"] == len(vectors["negative_vectors"])
    assert digests["mutation_vector_count"] == len(vectors["mutation_vectors"])
    assert digests["theorem_case_count"] == len(vectors["theorem_cases"])
    assert digests["positive_vector_count"] >= 1
    assert digests["negative_vector_count"] >= 1
    assert digests["mutation_vector_count"] >= 1


def test_cross_language_implementations_agree(gate: dict[str, Any]) -> None:
    matrix = gate["cross_language_transition_matrix"]
    assert matrix["agree"] is True
    assert matrix["languages"] == ["lean", "rust", "python", "typescript"]
    assert matrix["python_normative_vectors_pass"] is True
    assert matrix["rust_tables_match_rules"] is True
    assert matrix["typescript_tables_match_rules"] is True
    assert matrix["lean_forbidden_promotion_theorems_present"] is True
    assert matrix["weak_origin_production_success_blocked"] is True

    _ensure_validators_path()
    from validators import formal_claim_algebra as fca

    rules = fca.load_promotion_rules()
    vectors = fca.load_normative_vectors()
    counts = fca.evaluate_all_normative_vectors(rules, vectors)
    assert counts["accept"] == matrix["positive_accept"]
    assert counts["reject"] == matrix["negative_reject"] + matrix["mutation_reject"]
    assert counts["accept"] == gate["vector_digests"]["positive_vector_count"]
    assert matrix["negative_reject"] == gate["vector_digests"]["negative_vector_count"]
    assert matrix["mutation_reject"] == gate["vector_digests"]["mutation_vector_count"]

    weak = fca.EvidenceEnvelope.from_mapping(fca.WEAKEST_ENVELOPE)
    with pytest.raises(fca.FcaError):
        fca.ProductionSuccessClaim.try_admit(weak, fca.EvidenceBag(frozenset()), rules)

    rust_mod = _load_module(
        REPO_ROOT / "Mcp-Plus-Plus/tests-py/integration/test_formal_claim_algebra_rust.py"
    )
    ts_mod = _load_module(
        REPO_ROOT / "Mcp-Plus-Plus/tests-py/integration/test_formal_claim_algebra_typescript.py"
    )
    rust_mod.test_rust_transition_tables_match_promotion_rules()
    ts_mod.test_typescript_transition_tables_match_promotion_rules()


def test_compatibility_loss_report_blocks_unsafe_promotion(gate: dict[str, Any]) -> None:
    report = gate["compatibility_loss_report"]
    accel = report["accelerate_adapter"]
    kit = report["kit_adapter"]

    assert accel["task_id"] == "FACP-014"
    assert accel["unsafe_promotion"] is False
    assert accel["unsafe_promotion_default"] is False
    assert accel["information_losing_reverse_projection_refused"] is True
    assert accel["adapter_sha256"] == _sha256_file(REPO_ROOT / accel["adapter_path"])

    assert kit["task_id"] == "FACP-015"
    assert kit["unsafe_promotion"] is False
    assert kit["unsafe_promotion_default"] is False
    assert kit["round_trip_preserves_distinctions"] is True
    assert kit["zero_qualified_nonqualifying"] is True
    assert kit["envelope_only_reverse_projection_refused"] is True
    assert kit["adapter_sha256"] == _sha256_file(REPO_ROOT / kit["adapter_path"])

    _ensure_accelerate_path()
    from ipfs_accelerate_py.agent_supervisor.assurance.formal_claim_adapter import (
        UNSAFE_PROMOTION_DEFAULT,
        Authority,
        Freshness,
        Proof,
        TypedIncompatibility,
        project_envelope_to_assurance_level,
    )
    from ipfs_accelerate_py.agent_supervisor.assurance.formal_claim_adapter import (
        EvidenceEnvelope as AccelEnvelope,
    )

    assert UNSAFE_PROMOTION_DEFAULT is False
    rich = AccelEnvelope.weakest().with_updates(
        proof=Proof.VERIFIED,
        authority=Authority.VALID,
        freshness=Freshness.CURRENT,
    )
    refused = project_envelope_to_assurance_level(rich)
    assert isinstance(refused, TypedIncompatibility)
    assert refused.code == accel["refusal_code"]
    assert refused.unsafe_promotion is True

    _ensure_kit_path()
    from ipfs_kit_py.assurance.formal_claim_adapter import (
        UNSAFE_PROMOTION as KIT_UNSAFE,
    )
    from ipfs_kit_py.assurance.formal_claim_adapter import (
        InformationLosingProjection,
        adapt_live_qualification_summary,
        is_nonqualifying,
        project_from_envelope_only,
        round_trip,
    )

    assert KIT_UNSAFE is False
    zero = adapt_live_qualification_summary(
        live_qualified_backend_count=0,
        storage_selectable_count=2,
        inventory_production_count=0,
    )
    assert is_nonqualifying(zero) is True
    assert zero.unsafe_promotion is False
    assert zero.production_supported is False
    assert round_trip(zero.kit).to_dict() == zero.kit.to_dict()
    with pytest.raises(InformationLosingProjection):
        project_from_envelope_only(zero.envelope)


def test_scanner_corpus_score_and_allowlist_integrity(gate: dict[str, Any]) -> None:
    score = gate["scanner_corpus_score"]
    binding = gate["source_binding"]
    assert score["allowlist_cannot_suppress_corpus"] is True
    assert score["no_new_unqualified_production_claim"] is True
    assert score["score"] == 1.0
    assert score["seeds_bound"] == score["seeds_scannable"] >= 1
    assert score["seeds_total"] >= score["seeds_scannable"]
    scanner_bytes = _historical_blob(binding, score["scanner_path"])
    corpus_bytes = _historical_blob(binding, score["corpus_path"])
    assert score["scanner_sha256"] == hashlib.sha256(scanner_bytes).hexdigest()
    assert score["corpus_sha256"] == hashlib.sha256(corpus_bytes).hexdigest()

    _ensure_accelerate_path()
    from ipfs_accelerate_py.agent_supervisor.analysis.formal_claim_scanner import (
        SCANNER_VERSION,
    )
    from ipfs_accelerate_py.agent_supervisor.analysis.formal_claim_scanner import (
        SCHEMA as SCANNER_SCHEMA,
    )

    assert score["schema"] == SCANNER_SCHEMA
    assert score["scanner_version"] == SCANNER_VERSION

    entries = [
        json.loads(line) for line in corpus_bytes.decode("utf-8").splitlines() if line.strip()
    ]
    assert len(entries) == score["seeds_total"]
    seed_ids = _scannable_seed_ids(entries)
    assert len(seed_ids) == score["seeds_scannable"]
    assert score["seeds_bound"] == len(seed_ids)
    assert score["finding_count"] >= score["seeds_bound"]
    assert score["reject_or_corpus_bound_count"] == score["finding_count"]


def test_four_path_migration_explicitly_excluded_until_facp_031(gate: dict[str, Any]) -> None:
    exclusion = gate["exclusions"]["four_path_migration"]
    assert exclusion["excluded"] is True
    assert exclusion["deferred_until_task"] == "FACP-031"
    assert exclusion["migration_complete"] is False
    assert exclusion["migrated_paths_marked_complete"] is False
    assert exclusion["day90_gate_path"].endswith("day90_four_path.json")
    assert exclusion["day90_gate_present"] is tree_path_exists(
        REPO_ROOT,
        gate["source_binding"]["controller_commit"],
        str(DAY90_GATE_PATH.relative_to(REPO_ROOT)),
    )
    assert set(exclusion["repositories"]) == {
        "external/ipfs_accelerate",
        "external/ipfs_datasets",
        "external/ipfs_kit",
        "swissknife",
    }
    assert "FACP-031" in exclusion["reading"]
    assert "deferred" in exclusion["reading"].lower()

    acceptance = gate["acceptance"]
    assert acceptance["all_implementations_agree"] is True
    assert acceptance["no_forbidden_promotion_constructible"] is True
    assert acceptance["no_unqualified_production_claim_newly_introduced"] is True
    assert acceptance["receipt_binds_exact_source_and_dependencies"] is True
    assert acceptance["four_path_migration_excluded_until_facp_031"] is True


def test_gate_does_not_introduce_unqualified_production_claim_fields(
    gate: dict[str, Any],
) -> None:
    """The sealed receipt must not mint unqualified success/support fields."""

    guarded_roots = {
        "",
        "acceptance",
        "policy",
        "cross_language_transition_matrix",
        "compatibility_loss_report",
        "scanner_corpus_score",
        "exclusions",
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
    assert gate["exclusions"]["four_path_migration"]["migration_complete"] is False
    assert gate["behavior_change"] is False
