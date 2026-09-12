#!/usr/bin/env python3
"""Validate the frozen NS-005 task/oracle registry. This is not a live A-D run."""
from __future__ import annotations

import hashlib
import json
from collections import defaultdict
from pathlib import Path

ROOT = Path.cwd()
PAPER = ROOT / "papers/completion/neurosymbolic_supervision"
BENCH = PAPER / "benchmark"
AUDIT = PAPER / "audit"
SNAP = PAPER / "receipts/snapshots/NS-005"

TABLE18 = {"provider", "translation", "fixture_lifecycle", "restart_publication"}
TABLE12 = {
    ("state_selection", "deletion"),
    ("state_selection", "rename"),
    ("state_selection", "config_change"),
    ("state_selection", "fixture_change"),
    ("state_selection", "native_change"),
    ("state_selection", "dynamic_change"),
    ("state_selection", "selected_vs_full_regression"),
    ("state_selection", "ambiguity"),
    ("state_selection", "raw_source_fallback"),
    ("state_selection", "cold_incremental_byte_root_parity"),
    ("certificate_reuse", "changed_fixture"),
    ("certificate_reuse", "changed_instance"),
    ("certificate_reuse", "changed_finalizer"),
    ("certificate_reuse", "changed_plugin"),
    ("certificate_reuse", "changed_policy"),
    ("certificate_reuse", "changed_external_snapshot"),
    ("certificate_reuse", "changed_runner_version"),
    ("certificate_reuse", "unchanged_positive_reuse"),
    ("parallel_sealer", "malformed_block"),
    ("parallel_sealer", "cache_corruption"),
    ("parallel_sealer", "interrupted_write"),
    ("parallel_sealer", "stale_parent_race"),
    ("parallel_sealer", "multi_worker_root_parity"),
    ("recovery_local", "duplicate_event"),
    ("recovery_local", "reordered_event"),
    ("recovery_local", "worker_crash"),
    ("recovery_local", "expiry_fencing"),
    ("recovery_local", "unknown_external_effect"),
    ("recovery_local", "store_unavailable"),
}
SWE_BENCH = {
    "astropy/astropy",
    "django/django",
    "pallets/flask",
    "matplotlib/matplotlib",
    "pylint-dev/pylint",
    "pytest-dev/pytest",
    "psf/requests",
    "scikit-learn/scikit-learn",
    "mwaskom/seaborn",
    "sphinx-doc/sphinx",
    "sympy/sympy",
    "pydata/xarray",
}
REQUIRED_TASK_FIELDS = (
    "task_id",
    "role",
    "split",
    "family_id",
    "source_snapshot",
    "baseline",
    "acceptance",
    "provenance",
    "split_assignment",
)


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load_tasks() -> list[dict]:
    rows = []
    for line in (BENCH / "tasks.jsonl").read_text(encoding="utf-8").splitlines():
        if line.strip():
            rows.append(json.loads(line))
    return rows


def check() -> dict:
    assert (BENCH / "tasks.jsonl").stat().st_size <= 1048576
    tasks = load_tasks()
    splits = json.loads((BENCH / "splits.json").read_text(encoding="utf-8"))
    oracles = json.loads((BENCH / "oracle_manifest.json").read_text(encoding="utf-8"))
    leakage = json.loads((AUDIT / "leakage_audit.json").read_text(encoding="utf-8"))
    provenance = (BENCH / "provenance.md").read_text(encoding="utf-8")
    assert tasks, "empty tasks.jsonl"
    ids = [t["task_id"] for t in tasks]
    assert len(ids) == len(set(ids))
    for task in tasks:
        for field in REQUIRED_TASK_FIELDS:
            assert field in task and task[field] not in (None, "", []), (task.get("task_id"), field)
        assert task["split"] == task["split_assignment"]
        snap = task["source_snapshot"]
        assert "snapshot_sha256" in snap and snap["snapshot_sha256"]
        assert "expected_condition" in task["baseline"]
        acc = task["acceptance"]
        assert acc.get("independent") is True
        assert acc.get("hidden_from_proposal") is True
        assert acc.get("oracle_id")
        assert acc.get("criteria")

    live = [t for t in tasks if t.get("live_repair_admitted")]
    assert all(t["role"] == "live_historical_repair" for t in live)
    families = [t["family_id"] for t in live]
    assert len(families) == len(set(families))
    assert splits["actual_live_families"] == len(live)
    assert splits["replacement_after_freeze"] is False
    assert splits["favorable_case_selection"] is False
    assert splits["shortfall_vs_preregistered_24"] == max(0, 24 - len(live))
    assert set(splits["development_families"]) == {t["family_id"] for t in live if t["split"] == "development"}
    assert set(splits["pilot_families"]) == {t["family_id"] for t in live if t["split"] == "pilot"}
    assert set(splits["final_families"]) == {t["family_id"] for t in live if t["split"] == "final"}
    assert not (set(splits["development_families"]) & set(splits["pilot_families"]))
    assert not (set(splits["development_families"]) & set(splits["final_families"]))
    assert not (set(splits["pilot_families"]) & set(splits["final_families"]))
    assert splits["learning_holdout_families"] == splits["final_families"]

    blob = (BENCH / "tasks.jsonl").read_text(encoding="utf-8")
    assert "diff --git" not in blob
    assert "\n+++ " not in blob
    assert "fail_to_pass" not in blob

    for task in live:
        snap = task["source_snapshot"]
        assert snap.get("pre_fix_commit")
        assert snap.get("kind") == "compact_pre_fix_repair_surface"
        assert task["baseline"]["empty_suite"] is False
        assert task["baseline"]["compile_failure"] is False
        assert task["baseline"]["executed_in_builder"] is True
        assert task["baseline"]["pre_fix_hidden_oracle"] == "fail"
        assert task["baseline"]["reference_fix_hidden_oracle"] == "pass"
        assert task["provenance"]["old_40_fixture"] is False
        assert task["provenance"]["license"]
        assert task["provenance"].get("fix_commit_hidden") is True
        slug = task["family_id"].replace("upstream:", "")
        assert slug not in SWE_BENCH
        issue = task.get("issue") or {}
        assert "commit/" not in str(issue.get("upstream_url") or "")
        recipe_path = Path(snap["content_store"])
        assert recipe_path.is_file(), snap["content_store"]
        assert recipe_path.name == "snapshot_recipe.json"
        recipe = json.loads(recipe_path.read_text(encoding="utf-8"))
        assert recipe["pre_fix_commit"] == snap["pre_fix_commit"]
        assert recipe["snapshot_sha256"] == snap["snapshot_sha256"]
        assert recipe["kind"] == "compact_pre_fix_repair_surface_recipe"
        recipe_files = {item["path"]: item for item in recipe["files"]}
        assert snap["files"], task["task_id"]
        for item in snap["files"]:
            pinned = recipe_files[item["path"]]
            assert item["sha256"] == pinned["sha256"]
            assert len(item["sha256"]) == 64
            assert item["byte_length"] == pinned["byte_length"]
            assert "content_store" not in item
        hidden = SNAP / "scorer_only" / "oracles" / task["task_id"]
        assert (hidden / "oracle.json").is_file()
        assert not (hidden / "reference.patch").exists()
        assert not (hidden / "hidden_test_files").exists()
        oracle_obj = json.loads((hidden / "oracle.json").read_text(encoding="utf-8"))
        assert oracle_obj["proposal_sandbox_may_read"] is False
        assert oracle_obj["payload_stored_in_tree"] is False
        assert oracle_obj["fail_to_pass"]
        assert oracle_obj["reference_patch_sha256"]
        assert oracle_obj["fix_commit"]
        assert oracle_obj["pre_fix_commit"] == snap["pre_fix_commit"]

    recipe_files = [p for p in (SNAP / "proposal_snapshots").rglob("*") if p.is_file()]
    assert recipe_files
    assert {p.name for p in recipe_files} == {"snapshot_recipe.json"}

    fixtures = [t for t in tasks if t["role"] == "preliminary_fixture_only"]
    assert len(fixtures) == 40
    assert all(not t.get("live_repair_admitted") for t in fixtures)
    assert all(t["task_id"].startswith("sch-bench-") for t in fixtures)

    bounds = [t for t in tasks if t["role"] == "boundary_qualification"]
    muts = [t for t in tasks if t["role"] == "table12_mutation_qualification"]
    assert {t["table18_boundary"] for t in bounds} == TABLE18
    polar = defaultdict(set)
    for t in bounds:
        polar[t["table18_boundary"]].add(t["polarity"])
    for boundary in TABLE18:
        assert polar[boundary] == {"valid_progress", "safe_rejection"}, boundary
    assert {(t["table12_cohort"], t["table12_mutation"]) for t in muts} == TABLE12
    mpolar = defaultdict(set)
    for t in muts:
        mpolar[(t["table12_cohort"], t["table12_mutation"])].add(t["polarity"])
    for key in TABLE12:
        assert mpolar[key] == {"valid_progress", "safe_rejection"}, key
    assert all(not t.get("counts_as_live_repair") for t in bounds + muts)
    nsq = SNAP / "scorer_only/qualification_fixture/nsq_fixture_v1"
    assert (nsq / "nsq_fixture/core.py").is_file()
    assert (nsq / "tests/test_nsq.py").is_file()

    assert oracles["proposal_sandbox_may_mount_hidden_store"] is False
    live_oracles = [o for o in oracles["oracles"] if o.get("role") == "live_historical_repair"]
    assert len(live_oracles) == len(live)
    for oracle in live_oracles:
        assert oracle["independent"] is True
        assert oracle["proposal_context_includes_payload"] is False
        assert "fail_to_pass" not in oracle
        assert oracle["reference_patch_sha256"]
        assert oracle["hidden_test_sha256"]
        assert oracle["fail_to_pass_sha256"]
    assert leakage["tasks_jsonl_contains_reference_patch"] is False
    assert leakage["tasks_jsonl_contains_hidden_tests"] is False
    assert leakage["favorable_case_selection"] is False
    assert leakage["population_fixed_before_final_outcomes"] is True
    assert leakage["prior_fixtures"]["admitted_as_live_repair"] is False
    assert leakage["patch_acceptance_leakage"]["hidden_payloads_stored_in_tree"] is False
    assert set(leakage["related_paper_corpora"]["swe_bench"]["excluded_families"]) == SWE_BENCH
    assert "SWE-bench" in provenance
    assert "forbidden" in provenance.lower()
    assert "scorer_only" in provenance
    assert "recipe" in provenance.lower()

    mapping = {
        "benchmark/tasks.jsonl": BENCH / "tasks.jsonl",
        "benchmark/splits.json": BENCH / "splits.json",
        "benchmark/oracle_manifest.json": BENCH / "oracle_manifest.json",
        "benchmark/provenance.md": BENCH / "provenance.md",
        "audit/leakage_audit.json": AUDIT / "leakage_audit.json",
    }
    for rel, current in mapping.items():
        assert sha256_file(SNAP / rel) == sha256_file(current), rel

    return {
        "benchmark_contract_valid": True,
        "live_families": len(live),
        "shortfall_vs_24": splits["shortfall_vs_preregistered_24"],
        "ns016_amendment_required": splits["ns016_amendment_required"],
        "table18_cases": len(bounds),
        "table12_cases": len(muts),
        "preliminary_fixtures": len(fixtures),
        "hidden_oracles": len(live_oracles),
        "observed_live_repair_results": 0,
        "scope": "Frozen population/oracle/leakage registry only; no A-D experiment",
    }


if __name__ == "__main__":
    print(json.dumps(check(), indent=2))
