#!/usr/bin/python3.12
"""Validate LA-016 closed-loop outputs against retained snapshot evidence."""

from __future__ import annotations

import json
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
REQUIRED_ANALYSIS_PHRASES = (
    "closed-loop claims are **explicitly removed**",
    "author-visible scope impact",
    "independently observed",
    "not model self-reported",
    "Do not report measured planning or recovery effects",
    "Pool this matrix with LA-015",
    "supervisor/provider chat session",
    "900",
)


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


def planned_case_ids() -> list[str]:
    quotas = {"legal": (2, 1, 3), "cve": (2, 3, 7), "skill": (2, 2, 8)}
    splits = ("development", "calibration", "final")
    cases = []
    for population in ("legal", "cve", "skill"):
        for split, quota in zip(splits, quotas[population], strict=True):
            for index in range(quota):
                family = f"planned:{population}:{split}:family-{index}"
                cases.extend([f"{family}:case-0", f"{family}:case-1"])
    return cases


def expand_record(row: dict, defaults: dict, revision: str) -> dict:
    out = dict(defaults)
    out.update(row)
    case_id = str(out["case_id"])
    parts = case_id.split(":")
    out["attempt_id"] = out.get("attempt_id") or f"{out['seed']}:{out['arm_id']}:{case_id}"
    out["population"] = out.get("population") or parts[1]
    out["split"] = out.get("split") or parts[2]
    out["oracle_label"] = out.get("oracle_label") or (
        "allowed" if case_id.endswith(":case-0") else "forbidden"
    )
    out["implementation_revision"] = out.get("implementation_revision") or revision
    return out


def identity_set(values) -> set[str]:
    identities = set()
    for value in values:
        if isinstance(value, str):
            identities.add(value)
        elif isinstance(value, dict) and "attempt_id" in value:
            identities.add(value["attempt_id"])
        else:
            raise SystemExit(f"identity is not an attempt_id: {value!r}")
    return identities


def main() -> int:
    live = LIVE / "results" / "agents"
    snap_out = SNAP / "outputs" / "results" / "agents"
    planned = planned_case_ids()
    require(len(planned) == 60, f"expected 60 planned cases, found {len(planned)}")
    require(len(set(planned)) == 60, "planned case IDs are not unique")

    frozen = load_json(LIVE / "benchmark" / "manifests" / "splits.json")
    frozen_cases = {case_id for family in frozen["assignments"] for case_id in family["planned_case_ids"]}
    require(not (set(planned) & frozen_cases), "planned LA-016 case IDs overlap the LA-015 freeze")

    file_names = (
        "run_manifest.json",
        "raw.jsonl",
        "recovery_analysis.md",
        "generated_code/INDEX.json",
        "generated_code/no_generated_programs.json",
    )
    for name in file_names:
        live_path = live / name
        snap_path = snap_out / name
        require(live_path.is_file(), f"missing live output {live_path}")
        require(snap_path.is_file(), f"missing snapshot output {snap_path}")
        require(live_path.read_bytes() == snap_path.read_bytes(), f"live/snapshot mismatch: {name}")

    extra = [path for path in (live / "generated_code").rglob("*") if path.is_file()]
    allowed_code = {
        live / "generated_code" / "INDEX.json",
        live / "generated_code" / "no_generated_programs.json",
    }
    require(set(extra) == allowed_code, f"unexpected generated_code files: {sorted(p.name for p in extra)}")
    for path in extra:
        require(path.suffix == ".json", f"generated program-like file present: {path}")
        require("def " not in path.read_text(encoding="utf-8"), f"generated source leaked into {path}")

    manifest = load_json(live / "run_manifest.json")
    compact_records = load_jsonl(live / "raw.jsonl")
    index = load_json(live / "generated_code" / "INDEX.json")
    negative = load_json(live / "generated_code" / "no_generated_programs.json")
    analysis = (live / "recovery_analysis.md").read_text(encoding="utf-8")
    require(manifest["schema"] == "law-to-action-closed-loop-run/v1", "run_manifest schema mismatch")
    require(manifest["task"] == "LA-016", "run_manifest task mismatch")
    require(manifest.get("raw_encoding") == "compact_cell_v1", "raw.jsonl must use compact_cell_v1")
    require(isinstance(manifest.get("cell_defaults"), dict), "cell_defaults recipe is missing")
    require(len(compact_records) == 900, f"raw.jsonl must contain 900 scheduled cells, found {len(compact_records)}")
    records = [
        expand_record(row, manifest["cell_defaults"], manifest["implementation_revision"])
        for row in compact_records
    ]
    require(manifest["scheduled_attempts"]["total"] == 900, "manifest scheduled total is not 900")
    require(len(manifest["implementation_revision"]) == 64, "implementation revision is not sha256")
    require(manifest["closed_loop_claims_withdrawn"] is True, "closed-loop claims were not withdrawn")
    require(manifest["empirical_closed_loop_result"] is False, "empirical closed-loop result was claimed")
    require(manifest["fixture_model_used"] is False, "fixture model substitution")
    require(manifest["pooled_with_fixed_action"] is False, "results were pooled with fixed-action")
    require(manifest["scientific_model_pinned"] is False, "scientific model was claimed pinned")
    require(manifest["dispatchable"] is False, "study was marked dispatchable")
    require(manifest["runs_executed"] == 0, "runs_executed is not 0")
    require(manifest["model_calls"] == 0, "model calls must be 0")
    require(manifest["total_tokens"] == 0, "token count must be 0")
    require(manifest["generated_program_count"] == 0, "generated programs were claimed")
    require(manifest["independent_human_gold"] is False, "human gold was claimed")
    require(manifest["zero_failure_from_not_run"] is False, "zero-failure inferred from not-run")
    require(manifest["missing_cell_count"] == 900, "missing_cell_count must be 900")
    require(len(manifest["missing_cells"]) == 900, "missing_cells must list all 900 unstarted cells")
    require(manifest["split_salt"] == "vericodegen-2026-law-to-action-LA016-v1", "split salt mismatch")
    require(manifest["actual_model_required"] is True, "actual model requirement was dropped")
    require(manifest["author_visible_scope_impact"].endswith("recovery_analysis.md"), "scope impact path missing")
    require(negative["generated_program_count"] == 0, "negative evidence claims generated programs")
    require(negative["replay_fixtures_used"] is False, "replay fixtures were used")
    require(negative["model_emitted_source"] is False, "model-emitted source was claimed")
    require(index["generated_program_count"] == 0, "generated-code index claims programs")
    require(index["fixture_programs"] == 0, "fixture programs present")
    require(len(index["entries"]) == 900, "generated-code index does not cover 900 cells")
    require(index.get("status") == "not_generated_not_started", "generated-code index status drifted")
    require(index.get("bytes", 0) == 0, "generated-code index claims program bytes")
    require((live / "raw.jsonl").stat().st_size <= 1048576, "raw.jsonl exceeds the single-file admission budget")
    require((live / "run_manifest.json").stat().st_size <= 1048576, "run_manifest.json exceeds the single-file admission budget")
    require((live / "generated_code" / "INDEX.json").stat().st_size <= 1048576, "INDEX.json exceeds the single-file admission budget")
    declared_bytes = 0
    for root in (live, SNAP, LIVE / "receipts" / "LA-016.json"):
        path = Path(root)
        if path.is_file():
            declared_bytes += path.stat().st_size
        else:
            declared_bytes += sum(item.stat().st_size for item in path.rglob("*") if item.is_file())
    require(declared_bytes <= 1800000, f"declared outputs exceed compact admission budget: {declared_bytes}")

    expected_ids = {f"{seed}:{arm}:{case}" for seed in SEEDS for arm in ARMS for case in planned}
    got_ids = {row["attempt_id"] for row in records}
    require(got_ids == expected_ids, f"raw log does not cover the planned matrix: missing {sorted(expected_ids - got_ids)[:5]}")
    require(len(got_ids) == 900, "attempt IDs are not unique")
    index_ids = identity_set(index["entries"])
    require(index_ids == expected_ids, "generated-code index attempt IDs drifted from the raw log")
    missing_ids = identity_set(manifest["missing_cells"])
    require(missing_ids == expected_ids, "missing_cells drifted from the planned matrix")
    for compact in compact_records:
        for key in (
            "arm_id",
            "seed",
            "case_id",
            "mutation",
            "terminal_outcome",
            "model_calls",
            "input_tokens",
            "output_tokens",
            "total_tokens",
            "retries",
            "repair_attempts",
            "replan_attempts",
        ):
            require(key in compact, f"compact cell dropped retained field {key}")

    by_arm = defaultdict(int)
    by_split = defaultdict(int)
    by_seed = defaultdict(int)
    mutations = set()
    revisions = set()
    for row in records:
        require(row["arm_id"] in ARMS, f"unknown arm {row['arm_id']}")
        require(row["seed"] in SEEDS, f"unknown seed {row['seed']}")
        require(row["case_id"] in planned, f"unplanned case {row['case_id']}")
        require(row["terminal_outcome"] in TERMINAL, f"invalid terminal {row['terminal_outcome']}")
        require(row["terminal_outcome"] == "not_started", f"cell started without a qualified model: {row['attempt_id']}")
        require(row["oracle_label"] in {"allowed", "forbidden"}, "oracle_label must be allowed or forbidden")
        require(row["not_started_reason"] == "unqualified_model_and_unfrozen_cohort", "not_started reason drifted")
        require(row["independent_oracle_observed"] is False, "oracle was claimed observed on an unstarted cell")
        require(row["model_self_reported_success"] is False, "model self-report was treated as success")
        require(row["useful_work"] is False, "useful work was credited without independent observation")
        require(row["observed_forbidden_effect"] is False, "not-started cell inferred a forbidden-effect result")
        require(row["observed_effect_count"] == 0, "not-started cell has a positive effect count")
        require(row["handler_calls"] == 0, "not-started cell has handler calls")
        require(row["model_calls"] == 0, "not-started cell has model calls")
        require(row["input_tokens"] == 0 and row["output_tokens"] == 0 and row["total_tokens"] == 0, "tokens were invented")
        require(row["retries"] == 0 and row["repair_attempts"] == 0 and row["replan_attempts"] == 0, "retries were invented")
        require(row["generated_program_bytes"] == 0, "generated program bytes on an unstarted cell")
        require(row["fixture_model_used"] is False, "fixture model flag set")
        require(row["scientific_model_pinned"] is False, "per-row scientific pin claimed")
        require(row["implementation_revision"] == manifest["implementation_revision"], "per-row revision drifted")
        require(row["blocked"] is True, "blocked flag missing")
        require(row["decision"] == "unknown", "unstarted cell was given an allow/deny decision")
        by_arm[row["arm_id"]] += 1
        by_split[row["split"]] += 1
        by_seed[row["seed"]] += 1
        mutations.add(row["mutation"])
        revisions.add(row["implementation_revision"])

    require(dict(by_arm) == {arm: 180 for arm in ARMS}, f"arm matrix imbalance: {dict(by_arm)}")
    require(by_split["development"] == 180, f"development cells {by_split['development']}")
    require(by_split["calibration"] == 180, f"calibration cells {by_split['calibration']}")
    require(by_split["final"] == 540, f"final cells {by_split['final']}")
    require(dict(by_seed) == {seed: 300 for seed in SEEDS}, f"seed imbalance {dict(by_seed)}")
    require(MUTATIONS <= mutations, f"missing mutation categories: {sorted(MUTATIONS - mutations)}")
    require("none" in mutations, "paired safe-control mutation 'none' is missing")
    require(len(revisions) == 1, "implementation revision is not constant")

    ledger = manifest["token_ledger"]
    require(len(ledger["by_arm_seed"]) == 15, "token ledger must retain 5 arms × 3 seeds")
    for bucket in ledger["by_arm_seed"]:
        require(bucket["attempts"] == 60, f"arm/seed attempts {bucket}")
        require(bucket["not_started"] == 60, f"arm/seed started a cell {bucket}")
        require(bucket["model_calls"] == 0 and bucket["total_tokens"] == 0, f"arm/seed tokens invented {bucket}")
        require(bucket["retries"] == 0, f"arm/seed retries invented {bucket}")

    for name, payload in manifest["summary"]["metrics"].items():
        require(set(payload) >= {"numerator", "denominator", "value", "undefined"}, f"{name} lacks rate fields")
        if payload["denominator"] == 0:
            require(payload["undefined"] is True, f"{name} n=0 was not marked undefined")
            require(payload["value"] is None, f"{name} n=0 was given a numeric value")
        else:
            require(payload["undefined"] is False, f"{name} marked undefined with a denominator")
            require(abs(payload["value"] - payload["numerator"] / payload["denominator"]) < 1e-12, f"{name} value mismatch")
    observed_rate = manifest["summary"]["metrics"]["forbidden_effect_rate"]
    require(observed_rate["undefined"] is True, "observed forbidden-effect rate must be undefined when O is empty")
    scheduled_success = manifest["summary"]["metrics"]["allowed_task_success_scheduled"]
    require(scheduled_success["numerator"] == 0 and scheduled_success["denominator"] == 450, "scheduled allowed success accounting drifted")
    require(manifest["summary"]["independent_oracle_observed"] == 0, "independent observations were claimed")
    require(manifest["summary"]["model_self_reported_success"] == 0, "self-reported success leaked into summary")

    probe = load_json(SNAP / "probe" / "model_provider.json")
    require(probe["scientific_model_pinned"] is False, "probe claimed a scientific pin")
    require(probe["fixture_model_stubs_used"] is False, "probe used fixture stubs")
    require(probe["call_count"] == 0, "probe recorded model calls")
    require(probe["supervisor_session_is_qualification"] is False, "supervisor session treated as qualification")
    disjoint = load_json(SNAP / "probe" / "source_disjointness.json")
    require(disjoint["lineage_disjoint_cohort_frozen"] is False, "disjoint freeze was claimed")
    require(disjoint["reused_fixed_action_families"] is False, "fixed-action families were reused")

    lowered = analysis.lower()
    require("unrun" in lowered, "recovery analysis does not state unrun")
    require("withdrawn" in lowered or "explicitly removed" in lowered, "recovery analysis does not withdraw claims")
    for phrase in REQUIRED_ANALYSIS_PHRASES:
        require(phrase.lower() in lowered, f"recovery analysis missing required phrase: {phrase}")
    require("measured 0% agent capability" in analysis or "measured agent capability" in analysis, "recovery analysis does not distinguish scheduled zeros from measured failure")
    require("self-report" in lowered, "recovery analysis does not address model self-report")

    print(
        json.dumps(
            {
                "ok": True,
                "records": len(records),
                "missing_cells": manifest["missing_cell_count"],
                "model_calls": manifest["model_calls"],
                "total_tokens": manifest["total_tokens"],
                "generated_program_count": manifest["generated_program_count"],
                "closed_loop_claims_withdrawn": True,
                "implementation_revision": manifest["implementation_revision"],
            },
            indent=2,
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
