#!/usr/bin/python3.12
"""Read-only verifier for the LA-032 generated-code study freeze."""
from __future__ import annotations

import argparse
import ast
import hashlib
import json
import random
import re
import sys
from collections import Counter
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from preparation.common import ARMS, PROMPT_PROFILE, QUOTAS, SEEDS, SPLIT_SALT, digest, ranking_digest, sha_file
from preparation.code_profile import profile_check, syntax_reject_samples

ROOT = HERE.parents[4]


def fail(message: str) -> None:
    raise SystemExit("verify_preparation: " + message)


def load(path: Path):
    if not path.is_file():
        fail("missing " + str(path))
    return json.loads(path.read_text())


def require(ok, message):
    if not ok:
        fail(message)


def walk_files(directory: Path) -> list[Path]:
    return sorted(p for p in directory.rglob("*") if p.is_file())


def recompute_schedule(case_ids):
    schedule = []
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
                schedule.append(
                    {
                        "attempt_id": f"{seed}:{arm_id}:{case_id}",
                        "schedule_index": index,
                        "seed": seed,
                        "arm": arm_id,
                        "case_id": case_id,
                        "arm_position": rotated.index(arm_id),
                    }
                )
                index += 1
    return schedule


def main(argv=None):
    parser = argparse.ArgumentParser()
    parser.add_argument("--study", type=Path, required=True)
    parser.add_argument("--require-scientific-cells-unexecuted", action="store_true")
    args = parser.parse_args(argv)
    study_path = args.study.resolve()
    study = load(study_path)
    require(study.get("schema") == "la-closed-loop-study/v1", "study schema")
    require(study.get("split_salt") == SPLIT_SALT, "split salt")
    require(study.get("arms") == list(ARMS) and study.get("seeds") == list(SEEDS), "arms/seeds")
    families = study["families"]
    cases = study["cases"]
    schedule = study["schedule"]
    require(len(families) == 30 and len(cases) == 60 and len(schedule) == 900, "denominators")
    require(len({row["id"] for row in families}) == 30, "unique families")
    require(len({row["id"] for row in cases}) == 60, "unique cases")
    require(len({row["attempt_id"] for row in schedule}) == 900, "unique attempts")
    pops = Counter(row["population"] for row in families)
    require(pops == {"legal": 6, "cve": 12, "skill": 12}, "population counts")
    for population, counts in QUOTAS.items():
        ranked = sorted((row for row in families if row["population"] == population), key=lambda row: (ranking_digest(population, row["id"]), row["id"].encode()))
        expected = ["development"] * counts[0] + ["calibration"] * counts[1] + ["final"] * counts[2]
        require([row["split"] for row in ranked] == expected, "ranked split " + population)
    la004 = load(ROOT / "papers/completion/law_to_action/benchmark/manifests/sources.json")
    la029 = load(ROOT / "papers/completion/law_to_action/benchmark/fixed_action_operator/frozen_inputs.json")
    excluded = {row["lineage_family_id"] for row in la004["source_records"]}
    excluded |= {row["lineage_family_id"] for row in la029["candidates"]}
    overlap = {row["id"] for row in families} & excluded
    require(not overlap, "LA-004/LA-029 overlap: " + str(sorted(overlap)[:3]))
    for family in families:
        paired = [row for row in cases if row["source_family"] == family["id"]]
        require(len(paired) == 2, "two cases per family")
        require(all(row["split"] == family["split"] for row in paired), "descendant split")
    expected_schedule = recompute_schedule([row["id"] for row in cases])
    require(
        [(r["attempt_id"], r["arm_position"]) for r in schedule] == [(r["attempt_id"], r["arm_position"]) for r in expected_schedule],
        "schedule identity",
    )
    for seed in SEEDS:
        counts = {arm: [0] * 5 for arm in ARMS}
        for row in schedule:
            if row["seed"] == seed:
                counts[row["arm"]][row["arm_position"]] += 1
        for arm in ARMS:
            require(counts[arm] == [12, 12, 12, 12, 12], f"arm position {seed} {arm}")
    batches = load(HERE / "family_batches.json")
    require(batches["count"] == 30, "batch count")
    require(batches["development_cells"] == 180 and batches["calibration_cells"] == 180 and batches["final_cells"] == 540, "phase cells")
    ids = [attempt for batch in batches["batches"] for attempt in batch["cell_attempt_ids"]]
    require(len(ids) == 900 and len(set(ids)) == 900, "disjoint batch coverage")
    require(set(ids) == {row["attempt_id"] for row in schedule}, "batch/schedule coverage")
    require(all(len(batch["cell_attempt_ids"]) == 30 for batch in batches["batches"]), "batch size")
    require(sum(1 for batch in batches["batches"] if batch["phase"] == "development") == 6, "dev batches")
    require(sum(1 for batch in batches["batches"] if batch["phase"] == "calibration") == 6, "cal batches")
    require(sum(1 for batch in batches["batches"] if batch["phase"] == "final") == 18, "final batches")
    require(batches.get("scientific_cells_executed") == 0, "batches claimed execution")
    plan = load(HERE / "native_dependency_plan.json")
    require(plan["preparation_task"] == "LA-032", "prep task")
    require(plan.get("la031_completed_by_this_freeze") is False, "LA-031 marked complete")
    require(plan.get("scientific_cells_executed") == 0, "plan execution")
    require(plan["parent_dependency_update"]["future_batch_success_registered"] is False, "future success")
    batch_ids = [row["id"] for row in plan["family_batch_tasks"]]
    require(batch_ids == [f"LA-{n:03d}" for n in range(33, 63)], "batch task ids")
    analysis = plan["analysis_freeze_task"]
    require(analysis["id"] == "LA-063", "analysis id")
    require(set(analysis["depends_on"]) >= {"LA-032"} | {f"LA-{n:03d}" for n in range(33, 45)}, "analysis deps")
    for row in plan["family_batch_tasks"]:
        require("LA-032" in row["depends_on"], "batch depends on LA-032")
        if row["phase"] == "final":
            require("LA-063" in row["depends_on"], "final depends on analysis freeze")
        require("family_id" in row and row["family_id"].startswith("family:"), "family binding missing")
    la031 = plan["parent_dependency_update"]["add_explicit_depends_on"]
    require(set(la031) == {"LA-032", "LA-063"} | set(batch_ids), "LA-031 explicit deps")
    require(study.get("prompt_profile_sha256") == digest(PROMPT_PROFILE), "prompt profile")
    require(study.get("independent_effect_oracle_frozen") is True, "oracle freeze")
    require(study.get("final_sealed") is True and study.get("final_cohort_released") is False, "sealed final")
    for row in cases:
        if row["split"] == "final":
            require(row.get("sealed") is True, "final unsealed")
            require(row.get("task") in (None, {}), "final task leaked")
            require(row.get("oracle") in (None, {}), "final oracle leaked")
            require(row.get("task_sha256") and row.get("oracle_sha256"), "final hashes")
        else:
            require(row.get("task") and row.get("oracle"), "open split missing task/oracle")
            require(row["task"]["source_family"] == row["source_family"], "retrieval family")
            for context in row["task"]["retrieval"]:
                require(context["contains_oracle"] is False, "hidden oracle")
                require(context.get("contains_sibling_final_label") is False, "sibling label")
                require(context.get("contains_target_patch") is False, "target patch")
            require(row["oracle"]["machine_checkable"] is True, "oracle")
            require(row["oracle"].get("independent_human_annotation") is False, "human gold")
    sealed = load(HERE / "cohort/final_sealed/material.json")
    require(len(sealed["cases"]) == 36, "sealed final cases")
    require(sealed.get("release") == "final-stage-gate-only", "seal release")
    for row in sealed["cases"]:
        require(row["task"] and row["oracle"], "sealed incomplete")
    legal_dir = HERE / "cohort/sources/legal"
    require(len(list(legal_dir.glob("*.pdf"))) == 6, "legal PDFs")
    lineage = load(HERE / "cohort/lineage_audit.json")
    require(lineage["status"] == "PASS", "lineage")
    require(lineage["canonical_repository_not_sufficient"] is True, "fork audit")
    require(lineage["generated_skillcenter_not_human_annotation"] is True, "skillcenter")
    for name in ("profile", "model", "watchdog", "driver", "runtime"):
        q = load(HERE / "qualification" / name / "qualification.json")
        require(q.get("status") == "PASS", name + " qualification")
        require(q.get("scientific_cells_executed", 0) == 0, name + " executed cells")
    model_q = load(HERE / "qualification/model/qualification.json")
    require(model_q.get("constructed_transport") is False, "constructed transport")
    require(model_q.get("tokenization_agrees_with_usage") is True, "token agreement flag")
    require(model_q.get("every_call_prompt_tokens_equals_preflight") is True, "preflight")
    for call in model_q["calls"]:
        require(call["prompt_tokens"] == call["input_count"], "prompt_tokens != input_count")
        require(call["prompt_tokens"] <= 2048 and call["completion_tokens"] <= 1024, "token ceiling")
    require(re.fullmatch(r"[0-9a-f]{64}", model_q["weights_sha256"]), "weights pin")
    require(len(set(model_q["weights_sha256"])) > 1, "degenerate hash")
    profile = load(HERE / "model_profile.json")
    require(profile["schema"] == "la-qualified-local-model/v1", "model profile schema")
    require(profile.get("paid_provider_budget") == 0, "paid budget")
    require(profile.get("systemd_required") is False, "systemd")
    require(profile.get("total_service_wall_seconds") == 10000, "service wall")
    require(profile.get("startup_readiness_seconds") == 360, "startup")
    watchdog = load(HERE / "qualification/watchdog/oserror/oserror_probe.json")
    require(watchdog["historical_v2_receipt"]["upgraded"] is False, "v2 upgraded")
    require(watchdog["retained_oserror"]["errno"] is not None, "errno")
    require(watchdog["broad_oserror_suppressed"] is False, "oserror suppressed")
    driver = load(HERE / "qualification/driver/qualification.json")
    require(driver.get("configuration_flags_only") is False, "flags only")
    require(driver["interrupt_resume"]["replay_blocked"] is True, "replay")
    profile_q = load(HERE / "qualification/profile/qualification.json")
    require(profile_q.get("la030_two_sink_substituted") is False, "two-sink substitute")
    require(profile_q.get("la029_fixed_programs_substituted") is False, "la029 substitute")
    require(len(profile_q["executions"]) >= 6, "profile executions")
    for sample in syntax_reject_samples("legal"):
        try:
            profile_check(sample, "legal")
            fail("syntax accepted")
        except (ValueError, SyntaxError):
            pass
    mock_markers = json.dumps(study) + json.dumps(profile) + json.dumps(model_q)
    require("permissive_availability" not in mock_markers.lower(), "availability flag")
    require(study.get("scientific_cells_executed") == 0, "study executed")
    if args.require_scientific_cells_unexecuted:
        require(study["scientific_cells_executed"] == 0, "scientific cells executed")
        require(all(batch.get("executed") is False for batch in batches["batches"]), "batch executed")
    results = HERE.parent.parent.parent / "results" / "generated_code_study"
    if results.is_dir():
        raw = results / "raw.jsonl"
        if raw.is_file() and raw.stat().st_size:
            fail("scientific results present")
    require(sha_file(study_path) == sha_file(HERE / "prospective_study.json"), "study path")
    print(
        json.dumps(
            {
                "status": "PASS",
                "families": 30,
                "cases": 60,
                "schedule": 900,
                "batches": 30,
                "scientific_cells_executed": 0,
                "final_sealed": True,
                "readiness_only": True,
            },
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
