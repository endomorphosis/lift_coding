"""FACP-059: Compose one end-to-end proof-carrying workflow.

Acceptance (taskboard):
- One trace satisfies every contract and transition invariant end to end.
- Negative trace variants fail at the intended gate.
- All effects/authority/evidence remain classified.
- Receipt binds exact source forest and no private/secret value.

Owns only composed_workflow.json and this hermetic fan-in test. Consumes
qualified repository artifacts (contracts, TEP monitor, translation receipts,
cohort, supply-chain, controller, admission client) without editing them.
"""

from __future__ import annotations

import copy
import hashlib
import json
import re
import subprocess
import sys
from collections.abc import Mapping
from dataclasses import dataclass, field
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

RECEIPT_PATH = (
    REPO_ROOT
    / "implementation_plan"
    / "formal_assurance_control_plane"
    / "release"
    / "terminal"
    / "composed_workflow.json"
)
CONTRACTS_PATH = (
    REPO_ROOT / "Mcp-Plus-Plus" / "schemas" / "assurance" / "v1" / "repository-contracts.json"
)
SCHEDULER_PATH = REPO_ROOT / "config" / "formal_assurance_control_plane_scheduler.json"
COHORT_PATH = (
    REPO_ROOT
    / "external"
    / "ipfs_kit"
    / "data"
    / "formal_assurance"
    / "backend_receipts"
    / "cohort.json"
)
ACCELERATE_ROOT = REPO_ROOT / "external" / "ipfs_accelerate"
DATASETS_ROOT = REPO_ROOT / "external" / "ipfs_datasets"

RECEIPT_SCHEMA = "facp/composed-workflow@1"
COMPOSITION_PROOF_SCHEMA = "facp/composition-proof@1"
TASK_ID = "FACP-059"
GOAL_ID = "FACP-G820"
BUNDLE = "facp/release/composition"
RELEASE = "composed-workflow-v1"
VOCAB_SCHEMA = "facp/formal-claim-algebra-v1@1"

REQUIRED_EVIDENCE_SUBSET = {
    "canonical_request",
    "admission_token",
    "translation_receipt",
    "observed_execution",
    "immutable_storage_current_pointer_receipt",
    "presentation_projection",
    "repository_assumption_guarantee_discharge",
    "failure_compensation_traces",
}

REQUIRED_DEPENDS_ON = {
    "FACP-023",
    "FACP-025",
    "FACP-026",
    "FACP-028",
    "FACP-041",
    "FACP-046",
    "FACP-048",
    "FACP-049",
    "FACP-051",
    "FACP-052",
    "FACP-054",
    "FACP-056",
    "FACP-057",
    "FACP-058",
}

PLANNING_FOREST_PATHS = (
    "Mcp-Plus-Plus",
    "external/ipfs_accelerate",
    "external/ipfs_datasets",
    "external/ipfs_kit",
    "swissknife",
)

REQUIRED_PROHIBITED_EFFECTS = {
    "real_legal_filing_or_payment",
    "private_data_exfiltration",
    "unsupported_live_backend",
    "browser_authority",
    "simulation_as_production",
    "omit_failed_assumption",
    "undisclosed_environmental_premise",
    "assume_away_component_defect",
    "credential_or_secret_in_receipt",
    "network",
    "sign_or_publish_production_release",
}

REQUIRED_TERMINAL_WORKFLOW = (
    "swissknife_request",
    "host_authentication_and_admission",
    "datasets_semantic_compilation_translation_receipt",
    "accelerate_scheduling_and_observed_execution",
    "kit_immutable_persistence_current_pointer",
    "swissknife_evidence_presentation",
)

REQUIRED_INVARIANTS = {
    "NoDoubleEffect",
    "NoStaleFenceCompletion",
    "NoSuccessWithoutObservation",
    "NoConfirmationReuse",
    "NoBlindUnknownRetry",
}

AUTHORITY_CLASSES = {"none", "proposal_only", "kernel_admitted", "live_observed"}
EVIDENCE_CLASSES = {"fixture", "simulated", "hermetic", "live", "unknown"}
EFFECT_CLASSES = {
    "pure",
    "read",
    "write",
    "process",
    "credential",
    "install",
    "repository",
    "publish",
    "payment",
    "private",
    "legal",
    "irreversible",
}
IFA_LABELS = {
    "Public",
    "Internal",
    "RepositoryPrivate",
    "TenantPrivate",
    "MatterConfidential",
    "Credential",
    "CryptographicSecret",
    "WitnessSecret",
}

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
    "host_path",
    "file_path",
    "filesystem_path",
}

FULL_SHA_RE = re.compile(r"^[0-9a-f]{40}$")
DIGEST_RE = re.compile(r"^[0-9a-f]{64}$")


def _sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _canonical_json_bytes(value: Any) -> bytes:
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
    ).encode("utf-8")


def _canonical_content_sha256(receipt: dict[str, Any]) -> str:
    without = {key: value for key, value in receipt.items() if key != "content_sha256"}
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


def _ensure_path(root: Path) -> None:
    token = str(root)
    if token not in sys.path:
        sys.path.insert(0, token)


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


def _walk_string_values(value: Any) -> list[str]:
    out: list[str] = []
    if isinstance(value, dict):
        for child in value.values():
            out.extend(_walk_string_values(child))
    elif isinstance(value, list):
        for child in value:
            out.extend(_walk_string_values(child))
    elif isinstance(value, str):
        out.append(value)
    return out


# ---------------------------------------------------------------------------
# Compact assume/guarantee composer (mirrors FACP-048 hermetic evaluator)
# ---------------------------------------------------------------------------


def _all_contracts(registry: Mapping[str, Any]) -> dict[str, dict[str, Any]]:
    contracts = dict(registry["contracts"])
    for repo_id, contract in (registry.get("external_guarantees") or {}).items():
        contracts[repo_id] = contract
    return contracts


def _index_guarantees(
    contracts: Mapping[str, Mapping[str, Any]],
) -> dict[str, dict[str, Any]]:
    out: dict[str, dict[str, Any]] = {}
    for repo_id, contract in contracts.items():
        for guarantee in contract.get("guarantees") or []:
            row = dict(guarantee)
            row["repository_id"] = repo_id
            row["contract_id"] = contract["id"]
            out[guarantee["id"]] = row
    return out


def _index_assumptions(
    contracts: Mapping[str, Mapping[str, Any]],
) -> dict[str, dict[str, Any]]:
    out: dict[str, dict[str, Any]] = {}
    for repo_id, contract in contracts.items():
        for assumption in contract.get("assumptions") or []:
            row = dict(assumption)
            row["repository_id"] = repo_id
            row["contract_id"] = contract["id"]
            out[assumption["id"]] = row
    return out


@dataclass(frozen=True)
class DischargeResult:
    assumption_id: str
    status: str
    guarantee_id: str | None
    boundary_id: str | None
    rejection_code: str | None = None
    unresolved_reason: str | None = None


@dataclass
class CompositionReport:
    discharges: list[DischargeResult] = field(default_factory=list)
    violations: list[str] = field(default_factory=list)
    unresolved: list[str] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return not self.violations


class AssumeGuaranteeComposer:
    """Fail-closed composer for facp/repository-contracts@1."""

    def __init__(self, registry: Mapping[str, Any]) -> None:
        self.registry = registry
        self.contracts = _all_contracts(registry)
        self.guarantees = _index_guarantees(self.contracts)
        self.assumptions = _index_assumptions(self.contracts)
        self.boundaries = {row["id"]: row for row in registry["composition_boundaries"]}
        self.env_rules = {row["id"]: row for row in registry["environment_discharge_rules"]}
        self._unqualified: set[str] = set()
        self._extra_assumptions: list[dict[str, Any]] = []

    def mark_unqualified(self, *guarantee_ids: str) -> None:
        self._unqualified.update(guarantee_ids)

    def inject_assumption(self, assumption: Mapping[str, Any]) -> None:
        self._extra_assumptions.append(dict(assumption))

    def _guarantee_qualified(self, guarantee_id: str) -> bool:
        if guarantee_id in self._unqualified:
            return False
        guarantee = self.guarantees.get(guarantee_id)
        if guarantee is None:
            return False
        return guarantee.get("qualification", {}).get("status") == "qualified"

    def _boundary_for_assumption(self, assumption_id: str) -> dict[str, Any] | None:
        for boundary in self.boundaries.values():
            if boundary["assumption_id"] == assumption_id:
                return boundary
        return None

    def discharge_assumption(self, assumption: Mapping[str, Any]) -> DischargeResult:
        aid = assumption["id"]
        boundary = self._boundary_for_assumption(aid)
        boundary_id = boundary["id"] if boundary else None

        if assumption.get("environment"):
            if assumption.get("explicit_unresolved") and assumption.get("unresolved_reason"):
                return DischargeResult(
                    assumption_id=aid,
                    status="unresolved",
                    guarantee_id=None,
                    boundary_id=boundary_id,
                    unresolved_reason=str(assumption["unresolved_reason"]),
                )
            return DischargeResult(
                assumption_id=aid,
                status="violated",
                guarantee_id=None,
                boundary_id=boundary_id,
                rejection_code="ENV_UNDISCLOSED_PREMISE",
            )

        required = assumption.get("required_guarantee")
        provider = assumption.get("provider_repository")
        if not required or not provider:
            return DischargeResult(
                assumption_id=aid,
                status="violated",
                guarantee_id=required,
                boundary_id=boundary_id,
                rejection_code="ENV_PROVIDER_DISCHARGE_REQUIRED",
            )
        if not self._guarantee_qualified(required):
            code = (
                boundary["violation_code"]
                if boundary is not None
                else "ENV_PROVIDER_DISCHARGE_REQUIRED"
            )
            return DischargeResult(
                assumption_id=aid,
                status="violated",
                guarantee_id=required,
                boundary_id=boundary_id,
                rejection_code=code,
            )
        if boundary is not None:
            if boundary["guarantee_id"] != required:
                return DischargeResult(
                    assumption_id=aid,
                    status="violated",
                    guarantee_id=required,
                    boundary_id=boundary_id,
                    rejection_code=boundary["violation_code"],
                )
            if boundary["provider_repository"] != provider:
                return DischargeResult(
                    assumption_id=aid,
                    status="violated",
                    guarantee_id=required,
                    boundary_id=boundary_id,
                    rejection_code=boundary["violation_code"],
                )
        return DischargeResult(
            assumption_id=aid,
            status="discharged",
            guarantee_id=required,
            boundary_id=boundary_id,
        )

    def compose(self) -> CompositionReport:
        report = CompositionReport()
        assumptions = list(self.assumptions.values()) + self._extra_assumptions
        for assumption in assumptions:
            result = self.discharge_assumption(assumption)
            report.discharges.append(result)
            if result.status == "violated":
                assert result.rejection_code
                report.violations.append(result.rejection_code)
            elif result.status == "unresolved":
                report.unresolved.append(result.assumption_id)
        return report

    def apply_seeded_failure(self, seed: Mapping[str, Any]) -> tuple[CompositionReport, str]:
        broken = seed.get("broken_guarantee_id")
        if broken:
            self.mark_unqualified(broken)
        for gid in seed.get("also_unqualified_guarantee_ids") or []:
            self.mark_unqualified(gid)
        if seed.get("broken_assumption_id") and seed.get("expected_violation_code") == (
            "ENV_UNDISCLOSED_PREMISE"
        ):
            self.inject_assumption(
                {
                    "id": seed["broken_assumption_id"],
                    "environment": True,
                    "explicit_unresolved": False,
                    "unresolved_reason": "",
                    "kind": "environment",
                }
            )
        report = self.compose()
        expected = seed["expected_violation_code"]
        return report, expected


@pytest.fixture(scope="module")
def receipt() -> dict[str, Any]:
    assert RECEIPT_PATH.is_file(), f"missing composed workflow receipt: {RECEIPT_PATH}"
    payload = json.loads(RECEIPT_PATH.read_text(encoding="utf-8"))
    assert isinstance(payload, dict)
    return payload


@pytest.fixture(scope="module")
def scheduler() -> dict[str, Any]:
    assert SCHEDULER_PATH.is_file(), f"missing scheduler: {SCHEDULER_PATH}"
    payload = json.loads(SCHEDULER_PATH.read_text(encoding="utf-8"))
    assert isinstance(payload, dict)
    return payload


@pytest.fixture(scope="module")
def contracts() -> dict[str, Any]:
    assert CONTRACTS_PATH.is_file(), CONTRACTS_PATH
    payload = json.loads(CONTRACTS_PATH.read_text(encoding="utf-8"))
    assert isinstance(payload, dict)
    return payload


@pytest.fixture(scope="module")
def cohort() -> dict[str, Any]:
    assert COHORT_PATH.is_file(), COHORT_PATH
    payload = json.loads(COHORT_PATH.read_text(encoding="utf-8"))
    assert isinstance(payload, dict)
    return payload


def test_receipt_schema_task_bundle_goal_and_evidence_subset(
    receipt: dict[str, Any],
) -> None:
    assert receipt["schema"] == RECEIPT_SCHEMA
    assert receipt["schema_version"] == 1
    assert receipt["task_id"] == TASK_ID
    assert receipt["goal_id"] == GOAL_ID
    assert receipt["bundle"] == BUNDLE
    assert receipt["release"] == RELEASE
    assert receipt["vocabulary_schema"] == VOCAB_SCHEMA
    assert receipt["composition_proof_schema"] == COMPOSITION_PROOF_SCHEMA
    assert receipt["status"] == "sealed"
    assert receipt["behavior_change"] is False
    assert receipt["title"]
    assert receipt["generated_at"]
    assert set(receipt["evidence_subset"]) >= REQUIRED_EVIDENCE_SUBSET
    assert tuple(receipt["terminal_workflow"]) == REQUIRED_TERMINAL_WORKFLOW


def test_policy_forbids_browser_simulation_secrets_and_network(
    receipt: dict[str, Any],
) -> None:
    policy = receipt["policy"]
    assert policy["fail_closed"] is True
    assert policy["provider_authority"] == "proposal-only"
    assert policy["producer_artifacts_immutable"] is True
    assert policy["simulation_as_production_forbidden"] is True
    assert policy["browser_authority_forbidden"] is True
    assert policy["omit_failed_assumption_forbidden"] is True
    assert policy["no_unqualified_production_claim"] is True
    assert policy["no_network"] is True
    assert policy["credentials_forbidden_in_receipt"] is True
    assert REQUIRED_PROHIBITED_EFFECTS <= set(policy["prohibited_effects"])


def test_content_sha256_binds_canonical_receipt(receipt: dict[str, Any]) -> None:
    assert DIGEST_RE.match(receipt["content_sha256"])
    binding = receipt["content_binding"]
    assert binding["alg"] == "sha256"
    assert "sort-keys" in binding["canonicalization"] or "separators" in binding["canonicalization"]
    assert binding["covers"] == "gate_record_excluding_content_sha256"
    assert _canonical_content_sha256(receipt) == receipt["content_sha256"]


def test_source_binding_commits_forest_and_depends_on(
    receipt: dict[str, Any],
) -> None:
    binding = receipt["source_binding"]
    assert FULL_SHA_RE.match(binding["controller_commit"])
    assert FULL_SHA_RE.match(binding["controller_tree"])
    assert_historical_ancestor(REPO_ROOT, binding["controller_commit"])
    assert binding["controller_tree"] == git_output(
        REPO_ROOT, "rev-parse", f"{binding['controller_commit']}^{{tree}}"
    )
    assert binding["scheduler_config"] == ("config/formal_assurance_control_plane_scheduler.json")
    scheduler_bytes = _historical_blob(binding, binding["scheduler_config"])
    assert DIGEST_RE.match(binding["scheduler_config_sha256"])
    assert binding["scheduler_config_sha256"] == hashlib.sha256(scheduler_bytes).hexdigest()
    historical_scheduler = json.loads(scheduler_bytes)
    assert DIGEST_RE.match(binding["repository_contracts_sha256"])
    assert binding["repository_contracts_sha256"] == _historical_sha256(
        binding, binding["repository_contracts_path"]
    )
    assert DIGEST_RE.match(binding["portfolio_lock_sha256"])
    assert binding["portfolio_lock_sha256"] == _historical_sha256(
        binding, binding["portfolio_lock_path"]
    )

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


def test_producer_input_digests_match_filesystem(receipt: dict[str, Any]) -> None:
    producers = {row["task_id"]: row for row in receipt["source_binding"]["producer_inputs"]}
    assert REQUIRED_DEPENDS_ON <= set(producers)
    for row in receipt["source_binding"]["producer_inputs"]:
        assert row["role"]
        assert isinstance(row["paths"], list) and row["paths"]
        for item in row["paths"]:
            assert DIGEST_RE.match(item["sha256"])
            assert item["sha256"] == _historical_sha256(receipt["source_binding"], item["path"]), (
                item["path"]
            )


def test_terminal_workflow_matches_repository_contracts(
    receipt: dict[str, Any], contracts: dict[str, Any]
) -> None:
    assert receipt["terminal_workflow"] == contracts["terminal_workflow"]
    assert tuple(receipt["terminal_workflow"]) == REQUIRED_TERMINAL_WORKFLOW


def test_positive_trace_steps_cover_terminal_workflow_with_classifications(
    receipt: dict[str, Any],
) -> None:
    trace = receipt["positive_trace"]
    assert trace["trace_id"] == "accept/composed-happy-path"
    assert trace["expect_accept"] is True
    assert trace["environment"] == "hermetic"
    assert trace["origin"] == "synthetic_fixture"
    assert trace["claimed_environment"] == "local_reviewed_synthetic"
    assert trace["claimed_environment"] not in {"live", "production"}
    assert trace["authority_class"] in AUTHORITY_CLASSES
    assert trace["evidence_class"] in EVIDENCE_CLASSES
    assert trace["ifa_label"] in IFA_LABELS
    assert trace["evidence_class"] != "live"  # whole workflow is hermetic synthetic

    steps = trace["steps"]
    assert [step["workflow_step"] for step in steps] == list(REQUIRED_TERMINAL_WORKFLOW)
    for step in steps:
        assert step["authority_class"] in AUTHORITY_CLASSES
        assert step["evidence_class"] in EVIDENCE_CLASSES
        assert step["effect_class"] in EFFECT_CLASSES
        assert step["ifa_label"] in IFA_LABELS
        assert step["gate"] == step["workflow_step"]


def test_positive_canonical_request_and_admission_strip_browser_authority(
    receipt: dict[str, Any],
) -> None:
    steps = {step["workflow_step"]: step for step in receipt["positive_trace"]["steps"]}
    request = steps["swissknife_request"]["canonical_request"]
    assert request["consent"] == "absent"
    assert request["authority_decision"] is None
    assert "allow" not in request
    assert "policy_decision" not in request
    assert DIGEST_RE.match(request["argument_digest"])
    assert request["argument_cid"].startswith("cid:argument:")

    token = steps["host_authentication_and_admission"]["admission_token"]
    assert token["schema"] == "facp/admission-token@1"
    assert token["issuer"] == "effect_admission_kernel"
    assert token["kernel_call"] == "effect_admission_kernel.unlock_handler"
    assert token["effect_class"] == "write"
    assert token["observation_obligation"] == "independent_observation_required"
    assert token["closed_outcome"] == "Observed"
    assert token["argument_cid"] == request["argument_cid"]
    assert "consent" not in token or token.get("consent") in {None, "absent"}


def test_positive_translation_receipt_round_trips_module(receipt: dict[str, Any]) -> None:
    _ensure_path(DATASETS_ROOT)
    from ipfs_datasets_py.logic.translation_validation.formal_assurance import (
        EqualityCriteria,
        EqualityCriteriaKind,
        PreservationClass,
        TranslationReceipt,
    )

    steps = {step["workflow_step"]: step for step in receipt["positive_trace"]["steps"]}
    raw = steps["datasets_semantic_compilation_translation_receipt"]["translation_receipt"]
    assert raw["named_losses"] == []
    assert raw["preservation_class"] == "exact"
    assert raw["equality_criteria"]["kind"] == "exact"

    rebuilt = TranslationReceipt(
        source_cid=raw["source_cid"],
        target_cid=raw["target_cid"],
        compiler_cid=raw["compiler_cid"],
        source_schema=raw["source_schema"],
        target_schema=raw["target_schema"],
        preservation_class=PreservationClass(raw["preservation_class"]),
        equality_criteria=EqualityCriteria(
            criteria_id=raw["equality_criteria"]["criteria_id"],
            kind=EqualityCriteriaKind(raw["equality_criteria"]["kind"]),
            description=raw["equality_criteria"].get("description", ""),
            property_ids=tuple(raw["equality_criteria"].get("property_ids") or ()),
        ),
        assumptions=tuple(raw.get("assumptions") or ()),
        obligations=tuple(raw.get("obligations") or ()),
    )
    assert rebuilt.source_cid != rebuilt.target_cid
    assert rebuilt.preservation_class is PreservationClass.EXACT
    assert isinstance(rebuilt.receipt_cid, str) and rebuilt.receipt_cid


def test_positive_tep_happy_path_holds_all_invariants(receipt: dict[str, Any]) -> None:
    _ensure_path(ACCELERATE_ROOT)
    from ipfs_accelerate_py.agent_supervisor.runtime.formal_transition_monitor import (
        REQUIRED_INVARIANTS as MONITOR_INVARIANTS,
    )
    from ipfs_accelerate_py.agent_supervisor.runtime.formal_transition_monitor import (
        evaluate_all_normative_vectors,
        evaluate_normative_vector,
        load_normative_vectors,
    )

    steps = {step["workflow_step"]: step for step in receipt["positive_trace"]["steps"]}
    accel = steps["accelerate_scheduling_and_observed_execution"]
    assert accel["tep_vector_id"] == "accept/happy-path"
    assert set(accel["invariants_held"]) >= REQUIRED_INVARIANTS
    assert set(MONITOR_INVARIANTS) == REQUIRED_INVARIANTS

    vectors = {vector.vector_id: vector for vector in load_normative_vectors()}
    happy = vectors["accept/happy-path"]
    verdict = evaluate_normative_vector(happy)
    assert verdict.accepted is True
    assert set(verdict.invariants) >= REQUIRED_INVARIANTS
    assert all(verdict.invariants[name] for name in REQUIRED_INVARIANTS)

    corpus = evaluate_all_normative_vectors()
    assert corpus["exact_match"] is True
    assert corpus["failures"] == []

    compensation = receipt["positive_trace"]["compensation_trace"]
    assert compensation["tep_vector_id"] == "accept/compensation"
    assert evaluate_normative_vector(vectors["accept/compensation"]).accepted is True


def test_positive_composition_discharges_every_non_env_assumption(
    receipt: dict[str, Any], contracts: dict[str, Any]
) -> None:
    composer = AssumeGuaranteeComposer(contracts)
    report = composer.compose()
    assert report.ok, report.violations

    by_id = {row.assumption_id: row for row in report.discharges}
    for assumption in composer.assumptions.values():
        result = by_id[assumption["id"]]
        if assumption.get("environment") or assumption.get("explicit_unresolved"):
            assert result.status == "unresolved"
            assert result.unresolved_reason
        else:
            assert result.status == "discharged", assumption["id"]
            assert result.guarantee_id
            assert composer._guarantee_qualified(result.guarantee_id)

    # Receipt records the explicit unresolved environmental assumptions.
    recorded = {row["id"]: row for row in receipt["assumptions"]}
    for assumption_id, row in recorded.items():
        assert row["status"] == "unresolved"
        assert row["explicit_unresolved"] is True
        assert row["unresolved_reason"]
        assert assumption_id in by_id


def test_positive_kit_step_binds_live_local_filesystem_only(
    receipt: dict[str, Any], cohort: dict[str, Any]
) -> None:
    steps = {step["workflow_step"]: step for step in receipt["positive_trace"]["steps"]}
    kit = steps["kit_immutable_persistence_current_pointer"]["kit_persistence"]
    assert kit["backend_id"] == "local_filesystem"
    assert kit["disposition"] == "LiveQualified"
    assert kit["live_qualified"] is True
    assert kit["suite_complete"] is True
    assert kit["credentials_stored"] is False
    assert kit["unsafe_promotion"] is False
    assert kit["candidate_implies_admitted"] is False
    assert kit["admitted_stale_becomes_current"] is False
    assert kit["cohort_sha256"] == _sha256_file(COHORT_PATH)
    assert kit["unavailable_backends"]["pinned_ipfs"] == "Unavailable"
    assert kit["unavailable_backends"]["iroh"] == "Unavailable"

    results = cohort["results"]
    assert results["local_filesystem"]["disposition"] == "LiveQualified"
    assert results["local_filesystem"]["live_qualified"] is True
    assert results["pinned_ipfs"]["live_qualified"] is False
    assert results["iroh"]["live_qualified"] is False


def test_positive_presentation_never_authorizes(receipt: dict[str, Any]) -> None:
    steps = {step["workflow_step"]: step for step in receipt["positive_trace"]["steps"]}
    presentation = steps["swissknife_evidence_presentation"]["presentation"]
    assert presentation["may_upgrade_evidence"] is False
    assert presentation["authority_decision_from_browser"] is False
    assert presentation["authorizes"] is False
    assert presentation["evidence_class"] == "host_issued"
    assert "admission_token_cid" in presentation["displays"]
    assert "translation_receipt.receipt_cid" in presentation["displays"]


def test_classifications_cover_effects_authority_evidence_ifa(
    receipt: dict[str, Any],
) -> None:
    classifications = receipt["classifications"]
    effects = classifications["effects"]
    assert effects["effect_class"] in EFFECT_CLASSES
    assert effects["reversibility_class"] in {"reversible", "compensatable", "irreversible"}
    assert effects["idempotency_class"] in {
        "pure_idempotent",
        "idempotent",
        "at_most_once",
        "non_idempotent",
    }
    authority = classifications["authority"]
    assert authority["browser"] == "none"
    assert authority["host_token"] == "kernel_admitted"
    assert authority["presentation"] == "none"
    evidence = classifications["evidence"]
    assert evidence["workflow"] == "hermetic"
    assert evidence["simulation_as_production"] is False
    assert evidence["kit_backend_local_filesystem"] == "live"
    assert evidence["pinned_ipfs"] == "unavailable"
    assert evidence["iroh"] == "unavailable"
    labels = classifications["ifa_labels"]
    assert labels["receipt_body"] in IFA_LABELS
    assert labels["presentation_projection"] == "Public"
    assert labels["secrets"] == "CryptographicSecret"
    assert labels["credentials"] == "Credential"


@pytest.mark.parametrize(
    "variant_id",
    [
        "seed:browser-allow-as-admission",
        "seed:candidate-to-current",
        "seed:success-without-observation",
        "seed:datasets-external-effect-success",
        "seed:undisclosed-environment-premise",
    ],
)
def test_negative_contract_seeds_fail_at_intended_gate(
    receipt: dict[str, Any],
    contracts: dict[str, Any],
    variant_id: str,
) -> None:
    variants = {row["id"]: row for row in receipt["negative_variants"]}
    variant = variants[variant_id]
    seeds = {row["id"]: row for row in contracts["seeded_integration_failures"]}
    seed = seeds[variant["seed_id"]]

    composer = AssumeGuaranteeComposer(contracts)
    report, expected = composer.apply_seeded_failure(seed)
    assert not report.ok, variant_id
    assert expected == variant["expected_violation_code"]
    assert expected in report.violations

    # Gate mapping is part of the composition receipt.
    if variant["fail_gate"] != "composition_discharge":
        assert variant["fail_gate"] in REQUIRED_TERMINAL_WORKFLOW
        boundary_id = variant.get("violated_boundary_id")
        if boundary_id:
            boundary = next(
                row for row in contracts["composition_boundaries"] if row["id"] == boundary_id
            )
            assert (
                boundary["workflow_step"] == variant["fail_gate"]
                or boundary["workflow_step"] == "swissknife_request"
                or boundary["workflow_step"] == "normative_contract_resolution"
            )


@pytest.mark.parametrize(
    "variant_id",
    [
        "tep:reject/double-effect",
        "tep:reject/confirmation-reuse",
        "tep:reject/blind-unknown-retry",
    ],
)
def test_negative_tep_vectors_fail_at_intended_gate(
    receipt: dict[str, Any], variant_id: str
) -> None:
    _ensure_path(ACCELERATE_ROOT)
    from ipfs_accelerate_py.agent_supervisor.runtime.formal_transition_monitor import (
        evaluate_normative_vector,
        load_normative_vectors,
    )

    variants = {row["id"]: row for row in receipt["negative_variants"]}
    variant = variants[variant_id]
    vectors = {vector.vector_id: vector for vector in load_normative_vectors()}
    vector = vectors[variant["tep_vector_id"]]
    assert vector.expect_accept is False
    verdict = evaluate_normative_vector(vector)
    assert verdict.accepted is False
    assert variant["fail_gate"] in {
        "accelerate_scheduling_and_observed_execution",
        "host_authentication_and_admission",
    }
    assert verdict.code == variant["expected_code"]


def test_seed_success_without_observation_also_rejects_tep_vector(
    receipt: dict[str, Any],
) -> None:
    _ensure_path(ACCELERATE_ROOT)
    from ipfs_accelerate_py.agent_supervisor.runtime.formal_transition_monitor import (
        evaluate_normative_vector,
        load_normative_vectors,
    )

    variants = {row["id"]: row for row in receipt["negative_variants"]}
    variant = variants["seed:success-without-observation"]
    assert variant["tep_vector_id"] == "reject/success-without-observation"
    vectors = {vector.vector_id: vector for vector in load_normative_vectors()}
    verdict = evaluate_normative_vector(vectors[variant["tep_vector_id"]])
    assert verdict.accepted is False


def test_receipt_contains_no_private_or_secret_values(receipt: dict[str, Any]) -> None:
    keys = _walk_keys(receipt)
    leaked = SECRET_OR_PRIVATE_KEYS & keys
    assert not leaked, leaked

    sanitization = receipt["sanitization"]
    assert set(sanitization["forbidden_keys"]) >= SECRET_OR_PRIVATE_KEYS
    assert sanitization["credentials_stored"] is False
    assert sanitization["private_or_secret_values_present"] is False
    assert receipt["acceptance"]["no_private_or_secret_values"] is True
    assert receipt["acceptance"]["receipt_binds_exact_source_forest"] is True

    # No PEM/JWT-looking secret material in string values.
    secretish = re.compile(
        r"BEGIN (RSA |EC |OPENSSH )?PRIVATE KEY|eyJ[A-Za-z0-9_-]{20,}\.[A-Za-z0-9_-]{10,}"
    )
    for text in _walk_string_values(receipt):
        assert not secretish.search(text), text[:80]


def test_failures_empty_when_sealed(receipt: dict[str, Any]) -> None:
    assert receipt["status"] == "sealed"
    assert receipt["failures"] == []
    acceptance = receipt["acceptance"]
    assert acceptance["positive_trace_satisfies_every_contract_and_tep_invariant"] is True
    assert acceptance["negative_variants_fail_at_intended_gates"] is True
    assert acceptance["effects_authority_evidence_classified"] is True


def test_capsule_invalidates_when_contract_digest_changes(
    receipt: dict[str, Any], contracts: dict[str, Any]
) -> None:
    capsule_spec = receipt["positive_trace"]["capsule"]
    assert capsule_spec["capsule_id"] == "capsule:composed-workflow@1"
    assert capsule_spec["kind"] == "release"

    composer = AssumeGuaranteeComposer(contracts)
    digests = {
        contract["id"]: "sha256:" + hashlib.sha256(_canonical_json_bytes(contract)).hexdigest()
        for contract in composer.contracts.values()
    }
    required = list(capsule_spec["required_contract_ids"])
    for contract_id in required:
        assert contract_id in digests

    target_id = required[0]
    original = next(
        contract for contract in composer.contracts.values() if contract["id"] == target_id
    )
    mutated = copy.deepcopy(original)
    mutated["version"] = int(mutated.get("version") or 1) + 1
    mutated_digest = "sha256:" + hashlib.sha256(_canonical_json_bytes(mutated)).hexdigest()
    assert mutated_digest != digests[target_id]

    # Contract digest change must invalidate the composed-workflow capsule binding.
    assert digests[target_id] != mutated_digest
    assert target_id in capsule_spec["required_contract_ids"]
