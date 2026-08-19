"""FACP-002: validate Accelerate unsafe-claims inventory bindings.

The inventory is discovery evidence only. These tests assert content binding
and required fields; they do not treat discovery as remediation completion.
"""

from __future__ import annotations

import json
import re
import subprocess
from pathlib import Path

import pytest

WORKSPACE = Path(__file__).resolve().parents[2]
REPORT_PATH = (
    WORKSPACE
    / "implementation_plan"
    / "formal_assurance_control_plane"
    / "baseline"
    / "accelerate_claims.json"
)

SCHEMA = "facp/inventory/accelerate_claims@1"
TASK_ID = "FACP-002"
GITLINK = "external/ipfs_accelerate"

REQUIRED_TOP_LEVEL = {
    "schema",
    "schema_version",
    "task_id",
    "goal_id",
    "source_binding",
    "evidence_subset",
    "confirmed_defects",
    "policy",
}

REQUIRED_DEFECT_FIELDS = {
    "id",
    "title",
    "category",
    "severity",
    "status",
    "unsafe_claim",
    "source_spans",
    "call_flow_path",
    "production_reachability",
    "current_tests",
    "counterexample_seed",
    "proposed_fca_ipa_repair_class",
}

REQUIRED_SPAN_FIELDS = {"path", "start_line", "end_line", "symbol"}

REQUIRED_CATEGORIES = {
    "mock_worker",
    "mock_hardware",
    "mock_handler",
    "inference_outcome",
    "raw_hash",
    "pseudo_cid",
    "fallback_namespace",
    "success_support_field",
}

REQUIRED_DEFECT_IDS = {
    "defect:accelerate-mock-worker-cuda-true",
    "defect:accelerate-mock-multiformats-raw-sha256-cid",
    "defect:accelerate-test-hardware-hardcoded-support",
    "defect:accelerate-mock-handler-labeled-real",
    "defect:accelerate-legacy-pseudo-cid-store",
    "defect:accelerate-mcp-mock-ipfs-random-cid",
    "defect:accelerate-shared-tools-success-pseudo-cid",
    "defect:accelerate-skillset-mock-model-fallback",
    "defect:accelerate-fallback-compat-mock-namespaces",
}


def _gitlink_commit() -> str:
    result = subprocess.run(
        ["git", "ls-tree", "HEAD", GITLINK],
        cwd=WORKSPACE,
        check=True,
        capture_output=True,
        text=True,
    )
    # Example: "160000 commit a7942...\\texternal/ipfs_accelerate"
    parts = result.stdout.strip().split()
    assert len(parts) >= 3, result.stdout
    assert parts[1] == "commit", result.stdout
    return parts[2]


@pytest.fixture(scope="module")
def report() -> dict:
    assert REPORT_PATH.is_file(), f"missing inventory report: {REPORT_PATH}"
    data = json.loads(REPORT_PATH.read_text(encoding="utf-8"))
    assert isinstance(data, dict)
    return data


def test_report_exists_and_is_object(report: dict):
    assert report["schema"] == SCHEMA
    assert report["task_id"] == TASK_ID
    assert report["goal_id"] == "FACP-G010"
    missing = REQUIRED_TOP_LEVEL - set(report)
    assert not missing, f"missing top-level fields: {sorted(missing)}"


def test_policy_treats_discovery_as_non_completion(report: dict):
    policy = report["policy"]
    assert policy.get("discovery_is_not_completion") is True
    assert policy.get("correctness_from_presence") is False


def test_source_binding_matches_gitlink(report: dict):
    binding = report["source_binding"]
    assert binding["repository"] == GITLINK
    assert binding["gitlink_path"] == GITLINK
    expected = _gitlink_commit()
    assert binding["commit"] == expected
    assert binding["commit"].startswith(binding.get("commit_short", binding["commit"][:7]))


def test_evidence_subset_and_category_coverage(report: dict):
    subset = set(report["evidence_subset"])
    assert REQUIRED_CATEGORIES <= subset
    categories = {d["category"] for d in report["confirmed_defects"]}
    assert REQUIRED_CATEGORIES <= categories
    assert set(report.get("category_coverage", [])) == categories


def test_confirmed_defects_have_required_fields(report: dict):
    defects = report["confirmed_defects"]
    assert isinstance(defects, list)
    assert len(defects) >= 8
    assert report.get("defect_count") == len(defects)

    seen_ids: set[str] = set()
    for defect in defects:
        missing = REQUIRED_DEFECT_FIELDS - set(defect)
        assert not missing, f"{defect.get('id')}: missing {sorted(missing)}"
        assert defect["id"] not in seen_ids
        seen_ids.add(defect["id"])
        assert defect["id"].startswith("defect:")
        assert defect["status"] in {"confirmed", "confirmed-observation"}
        assert isinstance(defect["source_spans"], list) and defect["source_spans"]
        assert isinstance(defect["call_flow_path"], list) and len(defect["call_flow_path"]) >= 2
        reach = defect["production_reachability"]
        assert isinstance(reach, dict)
        assert "reachable" in reach and "via" in reach and "entrypoints" in reach
        assert isinstance(reach["entrypoints"], list) and reach["entrypoints"]
        assert isinstance(defect["current_tests"], list) and defect["current_tests"]
        seed = defect["counterexample_seed"]
        assert isinstance(seed, dict)
        for key in ("seed_id", "scenario", "expected_illegal_promotion", "mutation_oracle"):
            assert seed.get(key), f"{defect['id']} missing counterexample field {key}"
        repair = defect["proposed_fca_ipa_repair_class"]
        assert isinstance(repair, dict)
        for key in ("fca", "ipa", "rse_grammar", "migration_tasks"):
            assert repair.get(key), f"{defect['id']} missing repair field {key}"
        assert isinstance(repair["migration_tasks"], list) and repair["migration_tasks"]


def test_required_seed_defects_present(report: dict):
    present = {d["id"] for d in report["confirmed_defects"]}
    missing = REQUIRED_DEFECT_IDS - present
    assert not missing, f"missing required seed defects: {sorted(missing)}"


def test_source_spans_resolve_to_exact_lines(report: dict):
    for defect in report["confirmed_defects"]:
        for span in defect["source_spans"]:
            missing = REQUIRED_SPAN_FIELDS - set(span)
            assert not missing, f"{defect['id']}: span missing {sorted(missing)}"
            path = WORKSPACE / span["path"]
            assert path.is_file(), f"{defect['id']}: missing path {span['path']}"
            assert span["path"].startswith("external/ipfs_accelerate/"), span["path"]
            lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
            start = span["start_line"]
            end = span["end_line"]
            assert isinstance(start, int) and isinstance(end, int)
            assert 1 <= start <= end <= len(lines), (
                f"{defect['id']}: bad span {start}-{end} for {span['path']} ({len(lines)} lines)"
            )
            excerpt = span.get("excerpt")
            if excerpt:
                window = "\n".join(lines[start - 1 : end])
                assert excerpt in window, (
                    f"{defect['id']}: excerpt not found in {span['path']}:{start}-{end}"
                )


def test_repair_classes_are_closed_vocabulary(report: dict):
    allowed_fca = {
        "reject_simulated_to_live_promotion",
        "reject_unchecked_hash_as_integrity",
        "require_probe_backed_capability",
        "require_observed_outcome",
        "isolate_simulation_namespace",
    }
    allowed_ipa = {
        "mock_to_production_flow",
        "pseudo_cid_construction",
        "success_without_observation",
    }
    allowed_rse = {
        "mock_capability",
        "false_success",
        "pseudo_cid",
    }
    for defect in report["confirmed_defects"]:
        repair = defect["proposed_fca_ipa_repair_class"]
        assert repair["fca"] in allowed_fca, (defect["id"], repair["fca"])
        assert repair["ipa"] in allowed_ipa, (defect["id"], repair["ipa"])
        assert repair["rse_grammar"] in allowed_rse, (defect["id"], repair["rse_grammar"])


def test_counterexample_seeds_are_unique(report: dict):
    seeds = [d["counterexample_seed"]["seed_id"] for d in report["confirmed_defects"]]
    assert len(seeds) == len(set(seeds))
    for seed_id in seeds:
        assert re.match(r"^seed:[a-z0-9-]+$", seed_id), seed_id


def test_production_reachable_defects_name_entrypoints(report: dict):
    reachable = [
        d for d in report["confirmed_defects"] if d["production_reachability"]["reachable"]
    ]
    assert reachable, "expected at least one production-reachable defect"
    for defect in reachable:
        assert defect["production_reachability"]["via"].strip()
        assert all(isinstance(e, str) and e.strip() for e in defect["production_reachability"]["entrypoints"])
