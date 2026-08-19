"""FACP-007: release, dependency, Git, and rights qualification inventory gate.

Validates that ``release_rights.json`` identifies every mutable/unknown/stale
qualification input with an exact source and blocking predicate, and keeps
historical receipts separated from current-tree qualification. Discovery only;
no legal clearance is inferred.
"""

from __future__ import annotations

import json
import subprocess
import tomllib
from pathlib import Path
from typing import Any

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
REPORT_PATH = (
    REPO_ROOT
    / "implementation_plan"
    / "formal_assurance_control_plane"
    / "baseline"
    / "release_rights.json"
)
SCHEDULER_PATH = REPO_ROOT / "config" / "formal_assurance_control_plane_scheduler.json"

SCHEMA = "FACPReleaseRightsInventory@1"
TASK_ID = "FACP-007"
GOAL_ID = "FACP-G010"
BUNDLE = "facp/inventory/release"

REQUIRED_EVIDENCE_SUBSET = {
    "mutable_revisions",
    "gitlink_ancestry",
    "campaign_divergence",
    "stale_receipts",
    "package_repository_license_conflicts",
    "missing_provenance",
    "reproducibility_inputs",
}

REQUIRED_INPUT_CLASSES = {"mutable", "unknown", "stale"}

REQUIRED_INPUT_IDS = {
    "qi:accelerate-git-plus-main-mutable-deps",
    "qi:accelerate-torch-nightly-mutable-index",
    "qi:gitmodules-floating-branch-tracking",
    "qi:swissknife-competing-lockfiles",
    "qi:accelerate-local-branch-tip-diverges-from-gitlink",
    "qi:datasets-local-branch-tip-diverges-from-gitlink",
    "qi:swissknife-local-branch-tip-diverges-from-gitlink",
    "qi:kit-kernel-vfs-release-receipt-stale-vs-gitlink",
    "qi:kit-external-backend-receipts-empty",
    "qi:kit-release-candidate-receipt-historical",
    "qi:kit-soak-chaos-receipt-historical",
    "qi:iroh-release-receipts-historical",
    "qi:wpd-terminal-release-receipt-historical",
    "qi:datasets-package-vs-repository-license-conflict",
    "qi:root-license-file-without-package-metadata",
    "qi:swissknife-missing-license-and-provenance",
    "qi:mcp-plusplus-missing-license-file",
    "qi:missing-portfolio-lock-and-sbom",
    "qi:mcp-plusplus-tests-rs-missing-cargo-lock",
    "qi:unchecked-out-nonplanning-gitlinks",
}

REQUIRED_HISTORICAL_IDS = {
    "historical:kit-kernel-vfs-release-receipt",
    "historical:kit-release-candidate-receipt",
    "historical:kit-soak-chaos-receipt",
    "historical:kit-iroh-release-receipts",
    "historical:wpd-terminal-release-receipt",
    "historical:facp-v2-namespace-failure-evidence",
}

PLANNING_FOREST_PATHS = (
    "Mcp-Plus-Plus",
    "external/ipfs_accelerate",
    "external/ipfs_datasets",
    "external/ipfs_kit",
    "swissknife",
)


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


def _git_rev_parse(*args: str, cwd: Path | None = None) -> str:
    completed = subprocess.run(
        ["git", "rev-parse", *args],
        check=True,
        capture_output=True,
        text=True,
        cwd=cwd or REPO_ROOT,
    )
    return completed.stdout.strip()


def _input_by_id(report: dict[str, Any], input_id: str) -> dict[str, Any]:
    for entry in report["qualification_inputs"]:
        if entry["id"] == input_id:
            return entry
    raise AssertionError(f"missing qualification input: {input_id}")


@pytest.fixture(scope="module")
def report() -> dict[str, Any]:
    assert REPORT_PATH.is_file(), f"missing inventory report: {REPORT_PATH}"
    payload = json.loads(REPORT_PATH.read_text(encoding="utf-8"))
    assert isinstance(payload, dict)
    return payload


@pytest.fixture(scope="module")
def scheduler() -> dict[str, Any]:
    assert SCHEDULER_PATH.is_file(), f"missing scheduler config: {SCHEDULER_PATH}"
    payload = json.loads(SCHEDULER_PATH.read_text(encoding="utf-8"))
    assert isinstance(payload, dict)
    return payload


def test_report_task_and_schema_binding(report: dict[str, Any]) -> None:
    assert report["schema"] == SCHEMA
    assert report["task_id"] == TASK_ID
    assert report["goal_id"] == GOAL_ID
    assert report["bundle"] == BUNDLE
    assert report["behavior_change"] is False
    assert set(report["evidence_subset"]) >= REQUIRED_EVIDENCE_SUBSET
    assert report["policy"]["discovery_is_not_completion"] is True
    assert report["policy"]["historical_receipt_is_not_current_qualification"] is True
    assert report["policy"]["ambiguous_rights_remain_human_blocked"] is True
    prohibited = set(report["authority"]["prohibited_effects"])
    assert "infer_legal_clearance" in prohibited
    assert "sign_or_publish" in prohibited
    assert "fetch_or_update_dependencies" in prohibited


def test_source_binding_matches_scheduler_and_gitlinks(
    report: dict[str, Any], scheduler: dict[str, Any]
) -> None:
    binding = report["source_binding"]
    assert binding["controller_commit"] == _git_rev_parse("HEAD")
    assert binding["controller_tree"] == _git_rev_parse("HEAD^{tree}")
    assert binding["scheduler_config"] == (
        "config/formal_assurance_control_plane_scheduler.json"
    )

    sb = scheduler["source_binding"]
    forest = {entry["path"]: entry for entry in binding["planning_forest"]}
    assert set(forest) == set(PLANNING_FOREST_PATHS)

    expected = {
        "Mcp-Plus-Plus": sb["mcp_plus_plus_planning_revision"],
        "external/ipfs_accelerate": sb["accelerate_planning_revision"],
        "external/ipfs_datasets": sb["datasets_planning_revision"],
        "external/ipfs_kit": sb["kit_planning_revision"],
        "swissknife": sb["swissknife_planning_revision"],
    }
    for path, commit in expected.items():
        assert forest[path]["gitlink_commit"] == commit
        assert _gitlink_commit(path) == commit


def test_every_qualification_input_has_source_and_blocking_predicate(
    report: dict[str, Any],
) -> None:
    inputs = report["qualification_inputs"]
    assert isinstance(inputs, list) and len(inputs) >= len(REQUIRED_INPUT_IDS)

    seen: set[str] = set()
    for entry in inputs:
        input_id = entry["id"]
        assert input_id not in seen
        seen.add(input_id)
        assert entry["class"] in REQUIRED_INPUT_CLASSES
        assert entry["category"]
        assert entry["title"]
        sources = entry["sources"]
        assert isinstance(sources, list) and sources
        for source in sources:
            assert "path" in source
            assert source["path"], f"{input_id} source path empty"
        predicate = entry["blocking_predicate"]
        assert isinstance(predicate, str) and predicate.strip()
        assert entry["blocks_release"] is True
        assert entry["legal_clearance_inferred"] is False

    assert REQUIRED_INPUT_IDS <= seen
    assert set(report["qualification_input_classes"]) == REQUIRED_INPUT_CLASSES


def test_historical_receipts_separated_from_current_tree_qualification(
    report: dict[str, Any],
) -> None:
    historical = report["historical_receipts"]
    current = report["current_tree_qualification"]

    hist_ids = {entry["id"] for entry in historical}
    assert REQUIRED_HISTORICAL_IDS <= hist_ids

    for entry in historical:
        assert entry["current_tree_qualification_authority"] is False
        assert entry["disposition"]
        assert entry["reason"]
        # Historical entries must not be listed as current qualification evidence.
        assert entry["id"] not in current.get("evidence", [])

    assert current["release_admissible"] is False
    assert current["live_capability_receipts_current"] is False
    assert current["immutable_dependency_closure_present"] is False
    assert current["rights_resolved"] is False
    assert current["reproducible_provenance_present"] is False

    blocking_ids = set(current["blocking_qualification_input_ids"])
    assert REQUIRED_INPUT_IDS <= blocking_ids

    # No historical receipt path may be treated as a current-tree authority source.
    historical_paths = {
        entry["path"] for entry in historical if "path" in entry
    }
    authority_statement = current["authority_statement"].lower()
    assert "historical" in authority_statement
    assert "excluded" in authority_statement or "exact" in authority_statement
    for path in historical_paths:
        assert path not in current.get("accepted_evidence_paths", [])


def test_datasets_license_conflict_matches_sources(report: dict[str, Any]) -> None:
    entry = _input_by_id(report, "qi:datasets-package-vs-repository-license-conflict")
    assert entry["class"] == "unknown"
    assert entry["category"] == "package_repository_license_conflicts"

    pyproject = tomllib.loads(
        (REPO_ROOT / "external/ipfs_datasets/pyproject.toml").read_text(
            encoding="utf-8"
        )
    )
    package_license = pyproject["project"]["license"]["text"]
    assert package_license == "MIT"

    license_text = (REPO_ROOT / "external/ipfs_datasets/LICENSE").read_text(
        encoding="utf-8"
    )
    assert "GNU AFFERO GENERAL PUBLIC LICENSE" in license_text

    rights = report["rights_summary"]
    conflict_ids = {item["id"] for item in rights["conflicts"]}
    assert "rights:datasets-mit-vs-agpl" in conflict_ids
    assert rights["machine_clearance_allowed"] is False
    assert rights["human_review_required"] is True


def test_swissknife_missing_license_and_competing_locks(
    report: dict[str, Any],
) -> None:
    missing = _input_by_id(report, "qi:swissknife-missing-license-and-provenance")
    assert missing["class"] == "unknown"
    package = json.loads(
        (REPO_ROOT / "swissknife/package.json").read_text(encoding="utf-8")
    )
    assert package.get("license", None) in ("", None)
    assert not (REPO_ROOT / "swissknife/LICENSE").exists()
    assert not (REPO_ROOT / "swissknife/LICENSE.md").exists()

    locks = _input_by_id(report, "qi:swissknife-competing-lockfiles")
    assert locks["class"] == "mutable"
    for relative in (
        "swissknife/package-lock.json",
        "swissknife/yarn.lock",
        "swissknife/pnpm-lock.yaml",
        "swissknife/web/package-lock.json",
    ):
        assert (REPO_ROOT / relative).is_file(), relative


def test_mutable_git_plus_main_dependencies_exist(report: dict[str, Any]) -> None:
    entry = _input_by_id(report, "qi:accelerate-git-plus-main-mutable-deps")
    assert entry["class"] == "mutable"
    found = False
    for source in entry["sources"]:
        path = REPO_ROOT / source["path"]
        assert path.is_file(), source["path"]
        text = path.read_text(encoding="utf-8")
        if "git+" in text and ("@main" in text or "@master" in text):
            found = True
    assert found, "expected at least one git+@main mutable dependency source"

    nightly = _input_by_id(report, "qi:accelerate-torch-nightly-mutable-index")
    nightly_path = REPO_ROOT / nightly["sources"][0]["path"]
    nightly_text = nightly_path.read_text(encoding="utf-8")
    assert "nightly" in nightly_text
    assert "torch" in nightly_text


def test_stale_kit_receipt_not_current_gitlink(report: dict[str, Any]) -> None:
    entry = _input_by_id(report, "qi:kit-kernel-vfs-release-receipt-stale-vs-gitlink")
    assert entry["class"] == "stale"
    receipt_path = REPO_ROOT / "external/ipfs_kit/docs/kernel_vfs/release_receipt.json"
    receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
    bound = receipt["source_evidence"]["implementation_baseline"]["commit"]
    kit_gitlink = _gitlink_commit("external/ipfs_kit")
    assert bound != kit_gitlink
    assert any(
        source.get("observed") == bound for source in entry["sources"]
    )
    assert any(
        source.get("observed") == kit_gitlink for source in entry["sources"]
    )

    # Ancestry: receipt baseline is ancestor of current gitlink, hence stale-not-foreign.
    merge_base = subprocess.run(
        ["git", "-C", str(REPO_ROOT / "external/ipfs_kit"), "merge-base", bound, kit_gitlink],
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()
    assert merge_base == bound

    empty = _input_by_id(report, "qi:kit-external-backend-receipts-empty")
    index = json.loads(
        (
            REPO_ROOT
            / "external/ipfs_kit/docs/runtime_readiness/backend_external_receipts/index.json"
        ).read_text(encoding="utf-8")
    )
    assert index.get("receipts") == []
    assert empty["class"] == "stale"


def test_historical_receipt_files_exist_and_are_non_authority(
    report: dict[str, Any],
) -> None:
    for entry in report["historical_receipts"]:
        if entry["id"] == "historical:facp-v2-namespace-failure-evidence":
            path = REPO_ROOT / entry["path"]
            assert path.is_file()
            continue
        path = REPO_ROOT / entry["path"]
        assert path.is_file(), entry["path"]
        if path.suffix == ".json":
            payload = json.loads(path.read_text(encoding="utf-8"))
            assert isinstance(payload, (dict, list))
        assert entry["current_tree_qualification_authority"] is False

    # Cross-link: qualification inputs that cite historical receipts must point at
    # entries that deny current-tree authority.
    historical_by_id = {entry["id"]: entry for entry in report["historical_receipts"]}
    for entry in report["qualification_inputs"]:
        ref = entry.get("historical_receipt_ref")
        if not ref:
            continue
        assert ref in historical_by_id
        assert historical_by_id[ref]["current_tree_qualification_authority"] is False


def test_mcp_plusplus_and_reproducibility_gaps(report: dict[str, Any]) -> None:
    mcp = _input_by_id(report, "qi:mcp-plusplus-missing-license-file")
    assert mcp["class"] == "unknown"
    assert not (REPO_ROOT / "Mcp-Plus-Plus/LICENSE").exists()
    assert not (REPO_ROOT / "Mcp-Plus-Plus/LICENSE.md").exists()
    readme = (REPO_ROOT / "Mcp-Plus-Plus/README.md").read_text(encoding="utf-8")
    assert "MIT License" in readme

    portfolio = _input_by_id(report, "qi:missing-portfolio-lock-and-sbom")
    assert portfolio["class"] == "unknown"
    assert not (REPO_ROOT / "portfolio.lock.json").exists()
    assert not (REPO_ROOT / "sbom.json").exists()

    cargo = _input_by_id(report, "qi:mcp-plusplus-tests-rs-missing-cargo-lock")
    assert (REPO_ROOT / "Mcp-Plus-Plus/tests-rs/Cargo.toml").is_file()
    assert not (REPO_ROOT / "Mcp-Plus-Plus/tests-rs/Cargo.lock").exists()
    assert cargo["class"] == "unknown"


def test_root_license_metadata_gap_and_acceptance(report: dict[str, Any]) -> None:
    entry = _input_by_id(report, "qi:root-license-file-without-package-metadata")
    assert entry["class"] == "unknown"
    license_text = (REPO_ROOT / "LICENSE").read_text(encoding="utf-8")
    assert "GNU AFFERO GENERAL PUBLIC LICENSE" in license_text
    pyproject = tomllib.loads(
        (REPO_ROOT / "pyproject.toml").read_text(encoding="utf-8")
    )
    assert pyproject["project"].get("license") is None

    acceptance = report["acceptance"]
    assert acceptance["every_mutable_unknown_stale_input_has_exact_source"] is True
    assert (
        acceptance["every_mutable_unknown_stale_input_has_blocking_predicate"] is True
    )
    assert (
        acceptance["historical_receipts_separated_from_current_tree_qualification"]
        is True
    )
    assert acceptance["legal_clearance_inferred"] is False
    assert acceptance["release_admissible_claimed"] is False

    assert report["current_tree_qualification"]["release_admissible"] is False
