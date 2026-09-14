#!/usr/bin/env python3
"""Read-only preparation verifier. Recomputes freeze identity; executes no scientific cells."""
from __future__ import annotations

import argparse
import json
import random
import sys
from collections import Counter
from pathlib import Path

PREP = Path(__file__).resolve().parent / "preparation"
if str(PREP) not in sys.path:
    sys.path.insert(0, str(PREP))

from common import (
    ARMS,
    POPULATIONS,
    PROMPT_PROFILE,
    QUOTAS,
    SALT,
    SEEDS,
    SPLIT_ORDER,
    digest,
    ranking_sha256,
    read_json,
    sha_file,
    study_root,
)


def require(condition, message):
    if not condition:
        raise ValueError(message)


def expand_identities(schedule, cases=None):
    if schedule.get("encoding") == "compact_identity_v1":
        keys = schedule["keys"]
        case_index = {c["id"]: c for c in (cases or [])}
        identities = []
        for row in schedule["rows"]:
            item = dict(zip(keys, row))
            item["attempt_id"] = f"{item['seed']}:{item['arm']}:{item['case_id']}"
            item["executed"] = False
            item["scientific"] = True
            item["scientific_status"] = "not_started"
            case = case_index.get(item["case_id"])
            if case:
                item.setdefault("source_family", case["source_family"])
                item.setdefault("population", case["population"])
                item.setdefault("split", case["split"])
            identities.append(item)
        return identities
    return schedule["identities"]


def rebuild_schedule(case_ids):
    schedule = []
    index = 0
    for seed in SEEDS:
        rng = random.Random(seed)
        shuffled_cases = list(case_ids)
        rng.shuffle(shuffled_cases)
        shuffled_arms = list(ARMS)
        rng.shuffle(shuffled_arms)
        for case_index, case_id in enumerate(shuffled_cases):
            rotate = case_index % len(ARMS)
            rotated = shuffled_arms[rotate:] + shuffled_arms[:rotate]
            for arm_id in rotated:
                schedule.append((seed, arm_id, case_id, rotated.index(arm_id), index))
                index += 1
    return schedule


def verify(study_path: Path, require_unexecuted: bool = True) -> dict:
    study_path = Path(study_path).resolve()
    root = study_path.parent
    require(root == study_root(), "study path is not the generated_code_study root")
    study = read_json(study_path)
    require(study["schema"] == "la-closed-loop-study/v1", "study schema")
    require(study["split_salt"] == SALT, "split salt")
    require(study["arms"] == ARMS and study["seeds"] == SEEDS, "arms/seeds")
    require(study["scientific_execution_allowed"] is False, "scientific execution flag")
    require(study["scientific_cells_executed"] == 0, "scientific cells claimed")
    require(study["final_stage_gate"] is False and study["final_cohort_released"] is False, "final gate")
    require(study["prompt_profile_sha256"] == digest(PROMPT_PROFILE), "prompt profile")
    require(study["independent_effect_oracle_frozen"] is True, "oracle freeze")

    sources = read_json(root / "cohort/sources.json")
    families = read_json(root / "cohort/families.json")["families"]
    cases = read_json(root / "cohort/cases.json")["cases"]
    splits = read_json(root / "cohort/splits.json")
    audit = read_json(root / "cohort/lineage_audit.json")
    schedule = read_json(root / "schedule.json")
    batches = read_json(root / "family_batches.json")
    plan = read_json(root / "native_dependency_plan.json")
    model = read_json(root / "model_profile.json")
    runtime = read_json(root / "qualification/runtime.json")
    profile_q = read_json(root / "qualification/generated_program_profile/qualification.json")
    model_q = read_json(root / "qualification/model/qualification.json")
    watchdog_q = read_json(root / "qualification/watchdog_diagnostic/qualification.json")
    driver_q = read_json(root / "qualification/driver_probes/qualification.json")
    deadline_q = read_json(root / "qualification/attempt_deadline/qualification.json")
    sealed = read_json(root / "cohort/sealed_final/material.json")

    require(len(sources["source_records"]) == 30, "missing sources")
    require(len(families) == 30 and len(cases) == 60, "family/case counts")
    require(Counter(f["population"] for f in families) == {"legal": 6, "cve": 12, "skill": 12}, "population counts")
    require(sources["redistributed_third_party_source_bytes"] == 0, "redistributed bodies")
    old = {row["lineage_family_id"] for row in sources["exclusions"]["la004_la029_families"]}
    require(len(old) == 30, "old family exclusion set")
    require(not ({f["id"] for f in families} & old), "LA-004/LA-029 family overlap")
    require(audit["overlap_with_la004_la029"] is False, "lineage overlap")
    require(audit["canonical_repository_identity_only"] is False, "fork audit incomplete")
    require(audit["skill_generated_procedures_as_human_annotations"] is False, "skill human-annotation misuse")
    require(len(audit["fork_clone_audit"]) >= 24, "fork/clone lookups")
    require(len(audit["nearest_neighbor"]) == 30, "nearest-neighbor audit")

    require(splits["salt"] == SALT and splits["quotas"] == QUOTAS, "split rule")
    expected_assignments = []
    for population, quotas in QUOTAS.items():
        ranked = sorted(
            (ranking_sha256(population, r["lineage_family_id"]), r["lineage_family_id"].encode(), r)
            for r in sources["source_records"] if r["population"] == population
        )
        offset = 0
        for split, count in zip(SPLIT_ORDER, quotas):
            for digest_hex, _, record in ranked[offset:offset + count]:
                expected_assignments.append({
                    "population": population,
                    "source_id": record["source_id"],
                    "lineage_family_id": record["lineage_family_id"],
                    "split": split,
                    "ranking_sha256": digest_hex,
                    "planned_case_ids": record["source_to_ir"]["planned_case_ids"],
                })
            offset += count
    require(splits["assignments"] == expected_assignments, "ranked SHA256 split mismatch")
    family_by_id = {f["id"]: f for f in families}
    for family in families:
        record = next(r for r in sources["source_records"] if r["lineage_family_id"] == family["id"])
        require(family["split"] == record["split"] == next(a["split"] for a in expected_assignments if a["lineage_family_id"] == family["id"]), "family split")
    for population, quotas in QUOTAS.items():
        for split, count in zip(SPLIT_ORDER, quotas):
            require(sum(f["population"] == population and f["split"] == split for f in families) == count, "quota")

    require(len({c["id"] for c in cases}) == 60, "unique cases")
    for family in families:
        pair = [c for c in cases if c["source_family"] == family["id"]]
        require(len(pair) == 2, "two cases per family")
        require({c["polarity"] for c in pair} == {"positive_useful_work", "negative_undeclared_effect"}, "case polarities")
        for case in pair:
            require(case["split"] == family["split"], "descendant split")
            if family["split"] == "final":
                require(case["sealed"] is True and case["released_to_inference"] is False, "final unsealed")
                require(case.get("instruction") is None and case.get("expected_payload") is None and case.get("oracle") is None, "final oracle leaked")
                require(case["id"] in sealed["cases"], "sealed material missing")
            else:
                require(case["sealed"] is False, "non-final sealed")
                require(case["instruction"] and case["expected_payload"] and case["oracle"], "case/oracle incomplete")
                require(all(item.get("contains_oracle") is False and item.get("contains_target_patch") is False and item.get("contains_sibling_final_label") is False and item.get("source_family") == case["source_family"] for item in case["retrieval"]), "retrieval leak")
    require(sealed["released_to_inference"] is False and sealed["final_stage_gate"] is False, "sealed-final status")
    require(len(sealed["cases"]) == 36, "final sealed case count")

    identities = expand_identities(schedule, cases)
    require(len(identities) == 900, "900 identities")
    require(len({s["attempt_id"] for s in identities}) == 900, "unique identities")
    rebuilt = rebuild_schedule([c["id"] for c in cases])
    actual = [(s["seed"], s["arm"], s["case_id"], s["arm_position"], s["schedule_index"]) for s in identities]
    require(actual == rebuilt, "schedule reconstruction")
    require(sum(s["split"] == "development" for s in identities) == 180, "development cells")
    require(sum(s["split"] == "calibration" for s in identities) == 180, "calibration cells")
    require(sum(s["split"] == "final" for s in identities) == 540, "final cells")
    if require_unexecuted:
        require(all(s["executed"] is False and s["scientific_status"] == "not_started" for s in identities), "scientific cell executed")
        require(schedule["scientific_cells_executed"] == 0, "schedule executed count")

    require(len(batches["batches"]) == 30, "batch count")
    require(batches["phase_cells"] == {"development": 180, "calibration": 180, "final": 540}, "phase cells")
    covered = []
    seen_families = []
    by_index = {s["schedule_index"]: s for s in identities}
    for batch in batches["batches"]:
        indices = batch["original_schedule_indices"]
        require(len(indices) == 30, "batch size")
        require(batch["maximum_scientific_attempt_seconds"] <= 3600, "batch attempt allowance")
        require(batch["runtime_seconds"] <= 7200, "worker ceiling")
        require(batch["scientific_cells_executed"] == 0, "batch executed")
        require(batch["registered_success"] is False, "future batch success registered")
        seen_families.append(batch["family_id"])
        ids = [by_index[i]["attempt_id"] for i in indices]
        require(all(by_index[i]["source_family"] == batch["family_id"] for i in indices), "batch family cells")
        covered.extend(ids)
        family = family_by_id[batch["family_id"]]
        require(batch["phase"] == family["split"], "batch phase")
        require(set(batch["paired_cases"]) == set(family["case_ids"]), "source pairing")
        require(set(batch.get("arms", ARMS)) == set(ARMS) and set(batch.get("seeds", SEEDS)) == set(SEEDS), "arm/seed identities")
    require(len(set(seen_families)) == 30, "disjoint families")
    require(len(set(covered)) == 900 and set(covered) == {s["attempt_id"] for s in identities}, "disjoint batch coverage")

    require(plan["status"] == "FROZEN_DEPENDENCY_PLAN_NOT_EXECUTED", "plan status")
    require(plan["la031_marked_complete"] is False, "LA-031 marked complete")
    require(plan["future_batch_success_registered"] is False, "future success")
    require(plan["scientific_cells_executed"] == 0, "plan executed")
    tasks = {b["id"]: b for b in plan["family_batch_tasks"]}
    require(set(tasks) == {b["id"] for b in batches["batches"]}, "plan/batch binding")
    for batch in plan["family_batch_tasks"]:
        require("LA-032" in batch["depends_on"], "batch depends on preparation")
        if batch["phase"] in {"development", "calibration"}:
            require(batch["depends_on"][0] == "LA-032", "dev/cal gate")
        if batch["phase"] == "final":
            require("LA-063" in batch["depends_on"], "final depends on analysis freeze")
    analysis = plan["analysis_freeze_task"]
    require(analysis["id"] == "LA-063", "analysis freeze id")
    cal_dev = [b["id"] for b in plan["family_batch_tasks"] if b["phase"] in {"development", "calibration"}]
    require(set(cal_dev) <= set(analysis["depends_on"]), "analysis freeze missing batch edges")
    parent = plan["parent_dependency_update"]
    require(parent["task_id"] == "LA-031", "parent")
    require("LA-032" in parent["add_explicit_depends_on"] and "LA-063" in parent["add_explicit_depends_on"], "LA-031 edges")
    require(set(tasks) <= set(parent["add_explicit_depends_on"]), "LA-031 missing batches")
    require(parent["native_edges_not_parent_metadata_alone"] is True, "parent metadata only")
    require(plan["phase_family_dispatch_order"], "dispatch order missing")

    for report, label in (
        (profile_q, "profile"),
        (model_q, "model"),
        (watchdog_q, "watchdog"),
        (driver_q, "driver"),
        (deadline_q, "deadline"),
    ):
        require(report.get("status") == "PASS", f"{label} qualification failed")
        require(report.get("scientific_cells_executed", 0) == 0, f"{label} executed scientific cells")
    require(profile_q["la030_two_sink_substituted"] is False and profile_q["la029_fixed_programs_substituted"] is False, "profile substitution")
    require(model_q["constructed_transport"] is False, "mock/constructed model")
    require(model_q["tokenization_agrees_with_usage"] is True, "prompt_tokens agreement")
    require(all(call["prompt_tokens"] == call["input_count"] for call in model_q["calls"]), "prompt_tokens != preflight")
    require(model_q["max_output_tokens"] if False else model_q["output_token_ceiling"] == 1024, "output ceiling")
    require(model.get("max_output_tokens") == 1024 and model.get("max_input_tokens") == 2048, "model ceilings")
    for key in ("weights_sha256", "tokenizer_sha256", "chat_template_sha256", "deployment_sha256"):
        require(isinstance(model.get(key), str) and len(model[key]) == 64 and len(set(model[key])) > 1, "model pin " + key)
    require(model_q["systemd_required"] is False and model_q["indefinitely_running_required"] is False, "systemd prerequisite")
    require(watchdog_q["historical_v2_upgraded"] is False and watchdog_q["broad_oserror_suppressed"] is False, "watchdog policy")
    require(watchdog_q["errno_retained"] and watchdog_q["operation_path_retained"], "watchdog diagnostics")
    require(driver_q["interrupt_resume"] and driver_q["configuration_flags_only"] is False, "driver probes")
    require(driver_q["silent_replay_blocked"] and driver_q["final_cells_blocked"], "driver contract")
    require(runtime["scientific_execution_allowed"] is False, "runtime execution")
    require(runtime["complete_attempt_wall_seconds"] == 120, "attempt deadline")
    require(runtime["paid_provider_budget"] == 0, "paid budget")
    require(sha_file(root / "model_profile.json") == study["model_profile_sha256"], "model profile binding")
    require(sha_file(root / "qualification/runtime.json") == study["runtime_sha256"], "runtime binding")
    for blob in (model_q, profile_q, driver_q, runtime, study):
        text = json.dumps(blob).lower()
        require("mock_mechanism" not in text and "permissive_availability" not in text, "mock or permissive availability flag")
    require(model_q.get("availability_flag_permissive") is not True, "permissive availability flag")
    require(len(identities) == 900 and len(cases) == 60, "reduced denominators")

    results_dir = root.parents[2] / "results" / "generated_code_study"
    if results_dir.is_dir():
        raw = results_dir / "raw.jsonl"
        if raw.is_file() and raw.stat().st_size:
            raise ValueError("scientific results already present")

    return {
        "status": "PASS",
        "schema": "la-preparation-verification/v1",
        "families": 30,
        "cases": 60,
        "identities": 900,
        "batches": 30,
        "scientific_cells_executed": 0,
        "readiness_only": True,
        "study_sha256": sha_file(study_path),
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--study", type=Path, required=True)
    parser.add_argument("--require-scientific-cells-unexecuted", action="store_true")
    args = parser.parse_args()
    print(json.dumps(verify(args.study, args.require_scientific_cells_unexecuted), sort_keys=True, indent=2))


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print(json.dumps({"status": "FAIL", "error_type": type(exc).__name__, "error": str(exc)}), file=sys.stderr)
        raise
