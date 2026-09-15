#!/usr/bin/python3.12
"""Read-only preparation verifier. Completeness of readiness, not scientific execution."""
from __future__ import annotations

import argparse
import json
import random
import sys
from collections import Counter
from pathlib import Path

HERE = Path(__file__).resolve()
STUDY = HERE.parent
ROOT = HERE.parents[5]
for _path in (STUDY, STUDY / "preparation", STUDY / "qualification"):
    text = str(_path)
    if text not in sys.path:
        sys.path.insert(0, text)
from study_common import (  # noqa: E402
    ARMS,
    ATTEMPT_WALL_SECONDS,
    MAX_CALLS,
    MAX_INPUT_TOKENS,
    MAX_OUTPUT_TOKENS,
    PAID_BUDGET,
    POPULATIONS,
    PROMPT_PROFILE,
    QUOTAS,
    SEEDS,
    SPLIT_SALT,
    SPLITS,
    digest,
    ranking_digest,
    read_json,
    require,
    sha_file,
)


def load_study(path: Path) -> dict:
    study = read_json(path)
    require(study.get("schema") == "la-closed-loop-study/v1", "study schema")
    require(study.get("split_salt") == SPLIT_SALT, "split salt")
    require(study.get("arms") == list(ARMS) and study.get("seeds") == list(SEEDS), "arms/seeds")
    return study


def check_sources(study: dict) -> None:
    manifest = read_json(STUDY / "preparation" / "source_manifest.json")
    splits = read_json(STUDY / "preparation" / "splits.json")
    audit = read_json(STUDY / "preparation" / "lineage_audit.json")
    old = read_json(ROOT / "papers/completion/law_to_action/benchmark/manifests/sources.json")
    old_families = {r["lineage_family_id"] for r in old["source_records"]}
    old_repos = {r["ancestry_key"][1] for r in old["source_records"] if r["ancestry_key"][0] == "repository"}
    old_legal = {tuple(r["ancestry_key"]) for r in old["source_records"] if r["population"] == "legal"}
    families = manifest["families"]
    require(len(families) == 30, "missing sources: expected 30 families")
    require(len({f["id"] for f in families}) == 30, "duplicate families")
    require(not {f["id"] for f in families} & old_families, "LA-004/LA-029 family overlap")
    require(audit["status"] == "PASS" and audit["canonical_identity_not_sufficient"] is True, "fork audit")
    require(audit["la004_families_excluded"] == 30, "exclusion count")
    counts = Counter(f["population"] for f in families)
    require(counts["legal"] == 6 and counts["cve"] == 12 and counts["skill"] == 12, "population counts")
    for family in families:
        if family["population"] == "legal":
            require(tuple(family["ancestry_key"]) not in old_legal, "legal derivative of LA-004")
        else:
            require(family["ancestry_key"][1] not in old_repos, "repository overlap with LA-004")
        require(family.get("independent_human_annotation") is not True, "skill human-annotation claim")
    require(splits["salt"] == SPLIT_SALT, "split salt")
    by_id = {f["id"]: f for f in families}
    for population, quotas in QUOTAS.items():
        ranked = sorted(
            (ranking_digest(population, f["id"]), f["id"].encode(), f)
            for f in families
            if f["population"] == population
        )
        expected = ["development"] * quotas[0] + ["calibration"] * quotas[1] + ["final"] * quotas[2]
        require([row[2]["split"] for row in ranked] == expected, "ranked split differs")
    require(len(splits["assignments"]) == 30, "split assignments")
    require(manifest["redistributed_third_party_source_bytes"] == 0, "source body export")


def check_schedule(study: dict) -> list[dict]:
    schedule_doc = read_json(STUDY / "schedule.json")
    require(sha_file(STUDY / "schedule.json") == study["schedule_binding"]["sha256"], "schedule binding")
    schedule = schedule_doc["identities"]
    families = study["families"]
    cases = study["cases"]
    require(len(families) == 30 and len(cases) == 60 and len(schedule) == 900, "900 identities")
    require(len({c["id"] for c in cases}) == 60, "unique cases")
    family_by_id = {f["id"]: f for f in families}
    for case in cases:
        require(case["split"] == family_by_id[case["source_family"]]["split"], "case split inheritance")
        require(case.get("constructed_development") is False, "constructed case labeled scientific")
    expected = {(c["id"], arm, seed) for c in cases for arm in ARMS for seed in SEEDS}
    actual = {(row["case_id"], row["arm"], row["seed"]) for row in schedule}
    require(actual == expected, "schedule identity mismatch")
    case_ids = [c["id"] for c in cases]
    rebuilt = []
    index = 0
    for seed in SEEDS:
        rng = random.Random(seed)
        shuffled_cases = list(case_ids)
        rng.shuffle(shuffled_cases)
        shuffled_arms = list(ARMS)
        rng.shuffle(shuffled_arms)
        for case_index, case_id in enumerate(shuffled_cases):
            rotate = case_index % 5
            rotated = shuffled_arms[rotate:] + shuffled_arms[:rotate]
            for arm_id in rotated:
                rebuilt.append((seed, arm_id, case_id, rotated.index(arm_id), index))
                index += 1
    require(
        [(r["seed"], r["arm"], r["case_id"], r["arm_position"], r["schedule_index"]) for r in schedule] == rebuilt,
        "original arm/seed schedule changed",
    )
    return schedule


def check_batches(study: dict, schedule: list[dict]) -> None:
    batches = read_json(STUDY / "family_batches.json")
    require(batches["batch_count"] == 30 and batches["cells_per_batch"] == 30, "batch shape")
    require(batches["development_cells"] == 180 and batches["calibration_cells"] == 180 and batches["final_cells"] == 540, "phase cells")
    by_index = {row["schedule_index"]: row for row in schedule}
    seen = set()
    for batch in batches["batches"]:
        require(len(batch["cells"]) == 30, "batch cells")
        require(batch["maximum_scientific_attempt_seconds"] <= 3600, "batch attempt bound")
        require(batch["runtime_seconds"] <= 7200, "worker ceiling")
        for item in batch["cells"]:
            cell = by_index[item] if isinstance(item, int) else item
            ident = (cell["case_id"], cell["arm"], cell["seed"])
            require(ident not in seen, "overlapping batch cell")
            seen.add(ident)
    require(len(seen) == 900, "disjoint coverage")
    require(len(batches["dispatch_order"]) == 30, "dispatch order")
    require(batches["scientific_cells_executed"] == 0, "batch execution claimed")
    require(study["family_batches"]["sha256"] == sha_file(STUDY / "family_batches.json"), "batch binding")


def check_sealed(study: dict) -> None:
    require(study.get("final_stage_released") is False, "final released during preparation")
    sealed = read_json(STUDY / "cohort" / "sealed" / "final_oracles.json")
    require(sealed["released"] is False and sealed["release_gate"] == "final-stage-only", "seal")
    final_cases = [c for c in study["cases"] if c["split"] == "final"]
    require(len(final_cases) == 36, "18 families * 2 cases")
    for case in final_cases:
        require("expected_payload" not in case and "oracle" not in case, "final oracle leaked into inference material")
        require(case.get("oracle_sealed") is True, "final not sealed")
        for context in case.get("retrieval") or []:
            require(context.get("contains_oracle") is False, "hidden oracle in retrieval")
            require(context.get("contains_target_patch") is not True, "target patch in retrieval")
            require(context.get("contains_sibling_final_label") is not True, "sibling final label")
    require(len(sealed["oracles"]) == 36, "sealed oracle completeness")


def check_oracles(study: dict) -> None:
    mappings = read_json(STUDY / "cohort" / "mappings.json")
    require(len(mappings["cases"]) == 60, "mappings")
    for case in study["cases"]:
        require(case.get("handler") in {"record_obligation", "record_finding", "record_procedure"}, "handler")
        require(case["policy"]["allowed_handlers"] == [case["handler"]], "policy")
        require("undeclared_sink" in case["policy"]["forbidden_handlers"], "negative effect")
        if case["split"] != "final":
            require(case.get("expected_payload") == case["payload"], "oracle payload")
            require(case["oracle"]["negative_undeclared_effect"], "negative test")


def check_qualification(study: dict) -> None:
    for name in ("model_profile", "runtime_profile", "cohort", "development_qualification", "cohort_qualification", "runtime_qualification", "model_qualification"):
        ref = study[name] if name != "schedule_binding" else study["schedule"]
        path = ROOT / ref["path"]
        require(path.is_file(), "missing qualification " + name)
        require(sha_file(path) == ref["sha256"], "qualification binding changed: " + name)
        if name.endswith("qualification") or name in {"cohort_qualification", "runtime_qualification", "model_qualification", "development_qualification"}:
            payload = read_json(path)
            require(payload.get("status") == "PASS", "qualification failed: " + name)
            require(payload.get("mock_mechanisms") is not True, "mock mechanism")
            require(payload.get("scientific_cells_executed", 0) == 0, "scientific execution in qualification")
    model = read_json(ROOT / study["model_qualification"]["path"])
    require(model["constructed_transport"] is False, "constructed transport labeled model")
    require(model["tokenization_agrees_with_usage"] is True, "token agreement")
    require(model["prompt_tokens_equal_preflight_input_count"] is True, "prompt_tokens equality")
    require(model["systemd_required"] is False, "systemd prerequisite")
    require(model["indefinitely_running_model_required"] is False, "always-on model")
    for call in model["calls"]:
        if "preflight_input_count" in call:
            require(call["prompt_tokens"] == call["preflight_input_count"], "call token mismatch")
    profile = read_json(ROOT / study["model_profile"]["path"])
    for key in ("weights_sha256", "tokenizer_sha256", "chat_template_sha256", "deployment_sha256"):
        require(len(profile[key]) == 64 and len(set(profile[key])) > 1, "weak pin " + key)
    runtime = read_json(ROOT / study["runtime_profile"]["path"])
    require(runtime["attempt_wall_seconds"] == ATTEMPT_WALL_SECONDS, "120s bound")
    require(runtime["max_calls"] == MAX_CALLS, "8-call contract")
    require(runtime["max_input_tokens"] == MAX_INPUT_TOKENS, "2048 input")
    require(runtime["max_output_tokens"] == MAX_OUTPUT_TOKENS, "1024 output")
    require(runtime["paid_budget"] == PAID_BUDGET, "paid budget")
    watchdog = read_json(STUDY / "qualification" / "watchdog" / "watchdog_regression.json")
    require(watchdog["status"] == "PASS" and watchdog["historical_v2_receipt_upgraded"] is False, "watchdog")
    require(watchdog["broad_oserror_suppressed"] is False, "OSError suppressed")
    v2 = read_json(ROOT / "papers/completion/law_to_action/benchmark/generated_code_development/development_qualification_v2/reconciliation.json")
    require(v2["status"] == "FAILED_RETAINED", "historical v2 upgraded")
    profile_q = read_json(ROOT / study["development_qualification"]["path"])
    require(profile_q["la030_two_sink_substituted"] is False, "LA-030 substituted")
    require(profile_q["la029_fixed_programs_substituted"] is False, "LA-029 substituted")
    pops = {c["population"] for c in profile_q["controls"]}
    require(pops == {"legal", "cve", "skill"}, "profile populations")
    driver = read_json(STUDY / "qualification" / "driver_probes" / "interrupt_resume.json")
    require(driver["status"] == "PASS" and driver["replay_refused"] is True, "driver probe")
    require(driver["scientific_cells_executed"] == 0, "driver scientific execution")


def check_zero_execution(study: dict) -> None:
    require(study.get("scientific_cells_executed") == 0, "scientific cells executed")
    require(study.get("scientific_cells_claimed_executed") == 0, "claimed executed")
    require(study.get("scientific_execution_allowed") is False, "execution allowed")
    require(study.get("availability_flag") in {None, False}, "permissive availability flag")
    require(study.get("mock_mechanisms") is False, "mock flag")
    results = ROOT / "papers/completion/law_to_action/results/generated_code_study"
    if results.exists():
        raw = results / "raw.jsonl"
        if raw.exists() and raw.stat().st_size:
            raise ValueError("scientific results already present")


def check_dependencies(study: dict) -> None:
    plan = read_json(STUDY / "native_dependency_plan.json")
    require(plan["future_batch_success_registered"] is False, "future success registered")
    require(plan["la031_marked_complete"] is False, "LA-031 marked complete")
    require(plan["native_edges_are_explicit"] is True, "edges")
    tasks = plan["family_batch_tasks"]
    require(len(tasks) == 30, "30 batch tasks")
    analysis = plan["analysis_freeze_task"]
    require(analysis["id"] == "LA-063", "analysis freeze id")
    devcal = [t["id"] for t in tasks if t["phase"] in {"development", "calibration"}]
    require(set(devcal) <= set(analysis["depends_on"]), "analysis freeze missing batch gates")
    require("LA-032" in analysis["depends_on"], "analysis missing preparation")
    for task in tasks:
        require("LA-032" in task["depends_on"], "batch missing LA-032")
        if task["phase"] in {"development", "calibration"}:
            require("LA-063" not in task.get("depends_on", []), "dev/cal depends on analysis freeze")
        if task["phase"] == "final":
            require("LA-063" in task["depends_on"], "final missing analysis freeze")
        require(task["registered_success"] is False, "batch success registered")
    parent = plan["parent_dependency_update"]
    require(parent["mark_complete"] is False, "parent marked complete")
    require("LA-032" in parent["add_explicit_depends_on"] and "LA-063" in parent["add_explicit_depends_on"], "parent edges")
    require(len(parent["add_explicit_depends_on"]) == 32, "preparation + 30 batches + analysis freeze")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--study", type=Path, required=True)
    parser.add_argument("--require-scientific-cells-unexecuted", action="store_true")
    args = parser.parse_args()
    study = load_study(args.study)
    check_sources(study)
    schedule = check_schedule(study)
    check_batches(study, schedule)
    check_sealed(study)
    check_oracles(study)
    check_qualification(study)
    check_zero_execution(study)
    check_dependencies(study)
    if args.require_scientific_cells_unexecuted:
        require(study["scientific_cells_executed"] == 0, "scientific cells executed")
    payload = {k: study[k] for k in ("families", "cases", "split_salt", "arms", "seeds")}
    payload["schedule"] = schedule
    cohort_q = read_json(ROOT / study["cohort_qualification"]["path"])
    require(cohort_q["cohort_payload_sha256"] == digest(payload), "cohort payload binding")
    require(study["prompt_profile_sha256"] == digest(PROMPT_PROFILE), "prompt profile")
    print(
        json.dumps(
            {
                "status": "PASS",
                "readiness_only": True,
                "families": 30,
                "cases": 60,
                "cells": 900,
                "final_cells": 540,
                "scientific_cells_executed": 0,
                "final_stage_released": False,
            },
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print(json.dumps({"status": "FAIL", "error": type(exc).__name__, "detail": str(exc)}), file=sys.stderr)
        raise
