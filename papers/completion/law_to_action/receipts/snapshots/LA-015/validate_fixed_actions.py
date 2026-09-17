#!/usr/bin/python3.12
"""Validate LA-015 frozen fixed-action outputs against retained snapshot evidence."""

from __future__ import annotations

import json
import sys
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[6]
LIVE = ROOT / "papers" / "completion" / "law_to_action"
SNAP = Path(__file__).resolve().parent
SEEDS = (104729, 104759, 104761)
ARMS = ("A0", "A1", "A2", "A3", "A4")
MUTATIONS = {
    "omitted_legal_exception",
    "wrong_date_or_jurisdiction",
    "no_applicable_record",
    "misleading_cve_similarity",
    "fixed_negative_control",
    "skill_claims_authorization",
    "undeclared_handler_effect",
    "forged_receipt",
    "wrong_audience",
    "widened_path_or_tenant",
    "expired_or_revoked_capability",
    "replay",
    "changed_root_clock_or_environment",
}
TERMINAL = {
    "success",
    "denial",
    "abstention",
    "execution_failure",
    "timeout",
    "infrastructure_invalid",
    "not_started",
}


def load_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def load_jsonl(path: Path) -> list[dict]:
    rows = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.strip():
            rows.append(json.loads(line))
    return rows


def require(condition: bool, message: str) -> None:
    if not condition:
        raise SystemExit(message)


def main() -> int:
    live = LIVE / "results" / "fixed_actions"
    snap_out = SNAP / "outputs" / "results" / "fixed_actions"
    splits = load_json(LIVE / "benchmark" / "manifests" / "splits.json")
    families = splits["assignments"]
    planned = [case_id for family in families for case_id in family["planned_case_ids"]]
    require(len(families) == 30, f"expected 30 families, found {len(families)}")
    require(len(planned) == 60, f"expected 60 cases, found {len(planned)}")
    require(len(set(planned)) == 60, "planned case IDs are not unique")

    for name in ("run_manifest.json", "raw.jsonl", "summary.json"):
        live_path = live / name
        snap_path = snap_out / name
        require(live_path.is_file(), f"missing live output {live_path}")
        require(snap_path.is_file(), f"missing snapshot output {snap_path}")
        require(live_path.read_bytes() == snap_path.read_bytes(), f"live/snapshot mismatch: {name}")

    manifest = load_json(live / "run_manifest.json")
    summary = load_json(live / "summary.json")
    records = load_jsonl(live / "raw.jsonl")
    require(manifest["schema"] == "law-to-action-fixed-action-run/v1", "run_manifest schema mismatch")
    require(manifest["task"] == "LA-015", "run_manifest task mismatch")
    require(summary["task"] == "LA-015", "summary task mismatch")
    require(len(records) == 900, f"raw.jsonl must contain 900 scheduled cells, found {len(records)}")
    require(manifest["scheduled_attempts"]["total"] == 900, "manifest scheduled total is not 900")
    require(summary["scheduled"]["S"] == 900, "summary scheduled S is not 900")
    require(manifest["implementation_revision"] == summary["implementation_revision"], "revision mismatch")
    require(len(manifest["implementation_revision"]) == 64, "implementation revision is not sha256")
    require(manifest["final_labels_inspected"] is False, "final labels were inspected")
    require(manifest["held_out_tuning"] is False, "calibration/final used for tuning")
    require(manifest["independent_human_gold"] is False, "human gold was claimed")
    require(manifest["model_calls"] == 0, "model calls must be 0")
    require(summary["zero_failure_inferred_from_not_run"] is False, "zero-failure inferred from not-run")
    require(summary["safety_uses_effect_counters_not_decision_labels_alone"] is True, "safety must use effect counters")
    require("missing_cells" in manifest and "missing_cells" in summary, "missing cells not explicit")
    require(isinstance(manifest["missing_cells"], list), "manifest missing_cells must be a list")
    require(manifest["missing_cell_count"] == len(manifest["missing_cells"]), "missing cell count mismatch")
    require(summary["missing_cell_count"] == len(summary["missing_cells"]), "summary missing cell count mismatch")

    expected_ids = {f"{seed}:{arm}:{case}" for seed in SEEDS for arm in ARMS for case in planned}
    got_ids = {row["attempt_id"] for row in records}
    require(got_ids == expected_ids, f"raw log does not cover the frozen matrix: missing {sorted(expected_ids - got_ids)[:5]}")
    require(len(got_ids) == 900, "attempt IDs are not unique")

    by_arm = defaultdict(int)
    by_split = defaultdict(int)
    by_seed = defaultdict(int)
    mutations = set()
    revisions = set()
    identity = defaultdict(set)
    for row in records:
        require(row["arm_id"] in ARMS, f"unknown arm {row['arm_id']}")
        require(row["seed"] in SEEDS, f"unknown seed {row['seed']}")
        require(row["case_id"] in planned, f"unfrozen case {row['case_id']}")
        require(row["terminal_outcome"] in TERMINAL, f"invalid terminal {row['terminal_outcome']}")
        require(row["oracle_label"] in {"allowed", "forbidden"}, "oracle_label must be allowed or forbidden")
        require("observed_effect_count" in row, "effect counter missing")
        require("handler_calls" in row, "handler_calls missing")
        require("journal_event_count" in row, "journal_event_count missing")
        require("observed_forbidden_effect" in row, "observed_forbidden_effect missing")
        require("implementation_revision" in row, "implementation revision missing from a result")
        require(row["implementation_revision"] == manifest["implementation_revision"], "per-row revision drifted")
        require(row["independent_human_gold"] is False, "row claimed human gold")
        require(type(row["observed_effect_count"]) is int, "effect count is not an integer")
        require(row["decision"] in {"allow", "deny", "abstain", "unknown"} or row["terminal_outcome"] == "not_started", "invalid decision")
        if row["terminal_outcome"] == "not_started":
            require(row.get("not_started_reason"), "not_started cell lacks an explicit reason")
            require(row["observed_forbidden_effect"] is False, "not-started cell inferred a forbidden-effect result")
        if row["terminal_outcome"] == "denial":
            require(row["observed_effect_count"] == 0, "denial recoded over a positive effect counter")
        by_arm[row["arm_id"]] += 1
        by_split[row["split"]] += 1
        by_seed[row["seed"]] += 1
        mutations.add(row["mutation"])
        revisions.add(row["implementation_revision"])
        identity[row["case_id"]].add(row["identity_digest"])

    require(dict(by_arm) == {arm: 180 for arm in ARMS}, f"arm matrix imbalance: {dict(by_arm)}")
    require(by_split["development"] == 180, f"development cells {by_split['development']}")
    require(by_split["calibration"] == 180, f"calibration cells {by_split['calibration']}")
    require(by_split["final"] == 540, f"final cells {by_split['final']}")
    require(dict(by_seed) == {seed: 300 for seed in SEEDS}, f"seed imbalance {dict(by_seed)}")
    require(MUTATIONS <= mutations, f"missing mutation categories: {sorted(MUTATIONS - mutations)}")
    require("none" in mutations, "paired safe-control mutation 'none' is missing")
    require(len(revisions) == 1, "implementation revision is not constant")
    require(all(len(values) == 1 for values in identity.values()), "candidate identity changed across arms or seeds")
    require(summary["identical_candidate_identity_across_arms"] is True, "summary identity check failed")

    for name, payload in summary["metrics"].items():
        require(set(payload) >= {"numerator", "denominator", "value", "undefined"}, f"{name} lacks rate fields")
        require(payload["denominator"] >= 0, f"{name} negative denominator")
        if payload["denominator"] == 0:
            require(payload["undefined"] is True, f"{name} n=0 was not marked undefined")
            require(payload["value"] is None, f"{name} n=0 was given a numeric value")
            require(payload["value"] != 0, f"{name} inferred zero from an empty denominator")
        else:
            require(payload["undefined"] is False, f"{name} marked undefined with a denominator")
            expected = payload["numerator"] / payload["denominator"]
            require(abs(payload["value"] - expected) < 1e-12, f"{name} value does not match numerator/denominator")

    a0 = [row for row in records if row["arm_id"] == "A0"]
    a3 = [row for row in records if row["arm_id"] == "A3"]
    a4 = [row for row in records if row["arm_id"] == "A4"]
    executed_a3 = [row for row in a3 if row["terminal_outcome"] != "not_started"]
    executed_a4 = [row for row in a4 if row["terminal_outcome"] != "not_started"]
    if executed_a3:
        require(any(row.get("crypto") == "real-ed25519" for row in executed_a3), "A3 did not record real Ed25519")
    if executed_a4:
        require(any(row.get("enforce_mode") == "enforce" for row in executed_a4), "A4 did not record ENFORCE")
        require(any(row.get("store_kind") == "duckdb-file-typed-quack-owner" for row in executed_a4), "A4 did not use DuckDB store")
        require(any(row.get("sat_status") in {"sat", "unsat"} for row in executed_a4), "A4 did not record SAT status")
    require(all(row.get("sandbox") is True for row in records if row["terminal_outcome"] != "not_started"), "executed cells lost sandbox flag")

    forbidden_unguarded_effects = sum(
        row["observed_effect_count"]
        for row in a0
        if row["oracle_label"] == "forbidden" and row["terminal_outcome"] != "not_started"
    )
    require(
        "observed_effect_count" in summary["by_arm"]["A0"] or summary["by_arm"]["A0"]["effect_sum"] >= 0,
        "arm summary lacks effect sums",
    )
    require(
        summary["counts"]["effect_sum"] == sum(row["observed_effect_count"] for row in records),
        "summary effect_sum does not match raw counters",
    )
    require(
        summary["counts"]["observed_forbidden_effects"]
        == sum(1 for row in records if row["observed_forbidden_effect"]),
        "summary forbidden-effect count does not match raw flags",
    )
    require(isinstance(forbidden_unguarded_effects, int), "unguarded forbidden effects were not counted")
    if any(row["terminal_outcome"] == "not_started" for row in records):
        bound = summary["metrics"]["forbidden_effect_scheduled_bound"]
        observed_rate = summary["metrics"]["forbidden_effect_rate"]
        require(bound["denominator"] > 0, "scheduled forbidden bound lost its denominator")
        if observed_rate["undefined"]:
            require(observed_rate["value"] is None, "undefined observed rate was numeric")
    resources = load_json(SNAP / "probe" / "resources.json")
    require("scored_attempts_admitted" in resources, "resource probe missing scored admission flag")
    require(manifest["protocol_scored_admission"] == resources["scored_attempts_admitted"], "admission flag drifted")
    if not resources["scored_attempts_admitted"]:
        require(summary["protocol_compliant_scored_result"] is False, "unadmitted run claimed protocol-scored success")
        require("cgroup" in (resources.get("reason") or "").lower() or "cgroup" in (summary.get("resource_gate_reason") or "").lower(), "resource gate reason is not explicit")
        require(manifest["protocol_scored_unadmitted_cells"]["count"] == 900, "unadmitted scored matrix is not explicit")
        require(manifest["protocol_scored_unadmitted_cells"]["zero_failure_inferred"] is False, "unadmitted cells inferred zero-failure")
        require(summary["protocol_scored_unadmitted_cells"]["count"] == 900, "summary unadmitted count is not explicit")

    print(
        json.dumps(
            {
                "ok": True,
                "records": len(records),
                "missing_cells": manifest["missing_cell_count"],
                "implementation_revision": manifest["implementation_revision"],
                "protocol_scored_admission": manifest["protocol_scored_admission"],
                "mutations": sorted(mutations),
                "effect_sum": summary["counts"]["effect_sum"],
                "observed_forbidden_effects": summary["counts"]["observed_forbidden_effects"],
            },
            indent=2,
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
