#!/usr/bin/env python3
"""Read-only preparation verifier. Recomputes freeze identity; executes no scientific cells."""
from __future__ import annotations

import argparse
import hashlib
import json
import random
import sys
from pathlib import Path

ARMS = ("A0", "A1", "A2", "A3", "A4")
SEEDS = (104729, 104759, 104761)
SALT = "vericodegen-2026-law-to-action-LA016-v1"
QUOTAS = {"legal": (2, 1, 3), "cve": (2, 3, 7), "skill": (2, 2, 8)}
POPULATION_ORDER = ("legal", "cve", "skill")
SPLIT_ORDER = ("development", "calibration", "final")
BATCH_TASKS = [f"LA-{n:03d}" for n in range(33, 63)]
ANALYSIS_TASK = "LA-063"


def canonical(value) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False).encode()


def digest(value) -> str:
    return hashlib.sha256(canonical(value)).hexdigest()


def sha_file(path: Path) -> str:
    with Path(path).open("rb") as handle:
        return hashlib.file_digest(handle, "sha256").hexdigest()


def read(path: Path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def require(condition, message):
    if not condition:
        raise ValueError(message)


def ranking_digest(population: str, family_id: str) -> str:
    return hashlib.sha256(json.dumps([SALT, population, family_id], ensure_ascii=False, separators=(",", ":")).encode("utf-8")).hexdigest()


def rebuild_schedule(case_ids: list[str]) -> list[dict]:
    case_ids = sorted(case_ids)
    require(len(case_ids) == 60, "schedule requires 60 case ids")
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
            for position, arm in enumerate(rotated):
                schedule.append(
                    {
                        "attempt_id": f"{seed}:{arm}:{case_id}",
                        "schedule_index": index,
                        "seed": seed,
                        "arm": arm,
                        "case_id": case_id,
                        "arm_position": position,
                    }
                )
                index += 1
    require(len(schedule) == 900, "rebuilt schedule size")
    return schedule


def load_cases(root: Path, study: dict) -> list[dict]:
    if isinstance(study.get("cases"), list) and len(study["cases"]) == 60:
        return study["cases"]
    packed = read(root / "cohort" / "cases.json")
    cases = packed["cases"] if isinstance(packed, dict) else packed
    require(len(cases) == 60, "cohort case count")
    return cases


def load_families(root: Path, study: dict) -> list[dict]:
    if isinstance(study.get("families"), list) and len(study["families"]) == 30:
        return study["families"]
    packed = read(root / "cohort" / "families.json")
    families = packed["families"] if isinstance(packed, dict) else packed
    require(len(families) == 30, "cohort family count")
    return families


def verify(study_path: Path, require_unexecuted: bool = True) -> dict:
    study_path = Path(study_path).resolve()
    root = study_path.parent
    study = read(study_path)
    require(study["schema"] == "la-closed-loop-study/v1", "study schema")
    require(study["split_salt"] == SALT, "split salt")
    require(study["arms"] == list(ARMS) and study["seeds"] == list(SEEDS), "arms/seeds")
    families = load_families(root, study)
    cases = load_cases(root, study)
    schedule_doc = read(root / "schedule.json")
    case_ids = schedule_doc.get("case_ids") or [case["id"] for case in cases]
    require(sorted(case_ids) == sorted(case["id"] for case in cases), "schedule case ids")
    schedule = study["schedule"] if isinstance(study.get("schedule"), list) and len(study["schedule"]) == 900 else rebuild_schedule(case_ids)
    require(len(families) == 30 and len(cases) == 60 and len(schedule) == 900, "denominators")
    require(study.get("scientific_cells_executed") == 0, "scientific execution claimed")
    require(study.get("scientific_execution_admitted") is False, "scientific admission")
    require(study.get("final_cohort_released") is False, "final cohort released")
    require(study.get("paid_budget") == 0, "paid budget")
    require(study.get("independent_effect_oracle_frozen") is True, "oracle freeze")
    require(study.get("final_oracles_sealed") is True, "final seal")
    if require_unexecuted:
        require(study.get("status") == "PROSPECTIVE_FREEZE_UNEXECUTED", "status")
    ids = [row["id"] for row in families]
    require(len(set(ids)) == 30, "duplicate families")
    old = read(Path(__file__).resolve().parents[1] / "manifests" / "sources.json")
    old_ids = {row["lineage_family_id"] for row in old["source_records"]}
    old_repos = {row["ancestry_key"][1] for row in old["source_records"] if row["ancestry_key"][0] == "repository"}
    old_legal = {row["ancestry_key"][1] for row in old["source_records"] if row["population"] == "legal"}
    require(not (set(ids) & old_ids), "LA-004/LA-029 family overlap")
    counts = {}
    for population, quota in QUOTAS.items():
        ranked = sorted((row for row in families if row["population"] == population), key=lambda row: (ranking_digest(population, row["id"]), row["id"].encode("utf-8")))
        require(len(ranked) == sum(quota), "population count " + population)
        expected = (["development"] * quota[0]) + (["calibration"] * quota[1]) + (["final"] * quota[2])
        require([row["split"] for row in ranked] == expected, "ranked split " + population)
        counts[population] = {split: sum(row["split"] == split for row in ranked) for split in ("development", "calibration", "final")}
        for row in ranked:
            require(row["ranking_sha256"] == ranking_digest(population, row["id"]), "ranking hash")
            require(row.get("source_record_sha256") and row.get("normalized_source_sha256"), "source hashes")
            require(row["source_record_sha256"] != row.get("normalized_source_sha256") or population == "never", "exact/normalized")
            if population == "legal":
                require(row["ancestry_key"][1] not in old_legal, "legal section overlap")
            else:
                require(row["ancestry_key"][1] not in old_repos, "repository overlap")
    require(counts["legal"] == {"development": 2, "calibration": 1, "final": 3}, "legal quotas")
    require(counts["cve"] == {"development": 2, "calibration": 3, "final": 7}, "cve quotas")
    require(counts["skill"] == {"development": 2, "calibration": 2, "final": 8}, "skill quotas")
    cve_repos = {row["ancestry_key"][1] for row in families if row["population"] == "cve"}
    skill_repos = {row["ancestry_key"][1] for row in families if row["population"] == "skill"}
    require(not (cve_repos & skill_repos), "cross-population repository overlap")
    require(len({case["id"] for case in cases}) == 60, "case ids")
    family_by_id = {row["id"]: row for row in families}
    for family in families:
        pair = [case for case in cases if case["source_family"] == family["id"]]
        require(len(pair) == 2, "pair missing")
        for case in pair:
            require(case["split"] == family["split"], "split inheritance")
            require(case.get("constructed_development") is False, "constructed case")
            retrieval = case.get("retrieval") or []
            require(retrieval, "retrieval missing")
            for item in retrieval:
                require(item.get("source_family") == family["id"], "retrieval lineage")
                require(item.get("kind") == "permitted_public_source", "retrieval kind")
                require(item.get("contains_oracle") is False, "hidden oracle")
                require(item.get("contains_sibling_final_label") is False, "sibling label")
                require(item.get("contains_target_patch") is False, "target patch")
            if family["split"] == "final":
                require(case.get("oracle_sealed") is True, "final unsealed")
                require(case.get("expected_payload") in (None, {}), "final oracle leaked")
                require(case.get("oracle_release_gate") == "LA-063", "final gate")
            else:
                expected = case.get("expected_payload") or case.get("payload")
                require(expected, "open oracle missing")
                require(case.get("oracle", {}).get("human_annotation") is False, "human gold")
                if family["population"] == "skill":
                    require(case["oracle"].get("skillcenter_procedure_is_not_human_gold") is True, "skill gold")
    sealed = read(root / "cohort" / "sealed" / "final_oracles.json")
    require(sealed["sealed"] is True and sealed["inference_release_allowed"] is False, "sealed file")
    require(len(sealed["oracles"]) == 36, "sealed oracle count")
    expected = {(case["id"], arm, seed) for case in cases for arm in ARMS for seed in SEEDS}
    actual = {(row["case_id"], row["arm"], row["seed"]) for row in schedule}
    require(actual == expected, "900 identities")
    rebuilt = rebuild_schedule([case["id"] for case in cases])
    for row, rebuilt_row in zip(schedule, rebuilt):
        require(
            (row["seed"], row["arm"], row["case_id"], row["arm_position"], row["schedule_index"])
            == (rebuilt_row["seed"], rebuilt_row["arm"], rebuilt_row["case_id"], rebuilt_row["arm_position"], rebuilt_row["schedule_index"]),
            "schedule rebuild",
        )
    for seed in SEEDS:
        positions = {arm: [0] * 5 for arm in ARMS}
        for row in schedule:
            if row["seed"] == seed:
                positions[row["arm"]][row["arm_position"]] += 1
        require(all(counts == [12] * 5 for counts in positions.values()), "arm-position balance")
    batches = read(root / "family_batches.json")
    require(batches["scientific_cells_executed"] == 0, "batch execution")
    require(len(batches["batches"]) == 30, "batch count")
    case_by_id = {case["id"]: case for case in cases}
    seen = []
    for batch in batches["batches"]:
        require(batch.get("cell_count", len(batch.get("cells") or [])) == 30, "batch size")
        require(batch["maximum_scientific_attempt_seconds"] <= 3600, "batch allowance")
        require(batch["runtime_seconds"] <= 7200, "worker ceiling")
        require(batch["scientific_cells_completed"] == 0, "batch completed")
        require(batch["family_id"] in family_by_id, "batch family")
        if batch.get("cells"):
            cells = batch["cells"]
        else:
            cells = [row for row in schedule if case_by_id[row["case_id"]]["source_family"] == batch["family_id"]]
        require(len(cells) == 30, "batch pairing size")
        seen.extend(cell["attempt_id"] for cell in cells)
        for cell in cells:
            case = case_by_id[cell["case_id"]]
            require(case["source_family"] == batch["family_id"], "batch pairing")
    require(len(seen) == 900 and len(set(seen)) == 900, "disjoint coverage")
    phase_cells = batches["phase_cells"]
    require(phase_cells == {"development": 180, "calibration": 180, "final": 540}, "phase cells")
    plan = read(root / "native_dependency_plan.json")
    require(plan["future_batch_success_registered"] is False, "future success")
    require(plan["la031_marked_complete"] is False, "LA-031 marked complete")
    require(plan["parent_metadata_only"] is False, "parent metadata only")
    require(len(plan["development_batch_tasks"]) == 6 and len(plan["calibration_batch_tasks"]) == 6, "phase tasks")
    require(len(plan["final_batch_tasks"]) == 18, "final tasks")
    analysis = plan["analysis_freeze_task"]
    require(set(plan["development_batch_tasks"] + plan["calibration_batch_tasks"]).issubset(set(analysis["depends_on"])), "analysis deps")
    for batch in plan["family_batch_tasks"]:
        require("LA-032" in batch["depends_on"], "prep dep")
        if batch["phase"] == "final":
            require(ANALYSIS_TASK in batch["depends_on"], "final analysis dep")
    require(set(plan["parent_dependency_update"]["add_explicit_depends_on"]) >= set(["LA-032", *plan["development_batch_tasks"], *plan["calibration_batch_tasks"], *plan["final_batch_tasks"], ANALYSIS_TASK]), "LA-031 deps")
    model = read(root / "model_profile.json")
    require(model["schema"] == "la-qualified-local-model/v1", "model schema")
    for key in ("weights_sha256", "tokenizer_sha256", "chat_template_sha256", "deployment_sha256"):
        require(isinstance(model.get(key), str) and len(model[key]) == 64 and len(set(model[key])) > 1, "model pin " + key)
    require(model.get("model_id") and model.get("model_revision") not in (None, "latest", "tbd"), "model identity")
    require(model.get("systemd_required") is False, "systemd")
    require(model.get("indefinitely_running_model_required") is False, "indefinite model")
    mq = read(root / "qualification" / "model" / "qualification.json")
    require(mq["status"] == "PASS", "model qualification")
    require(mq.get("constructed_transport") is False, "constructed transport")
    require(mq.get("mock") is False, "mock model")
    require(mq.get("tokenization_agrees_with_usage") is True, "tokenization")
    require(mq.get("prompt_tokens_equal_preflight_for_every_call") is True, "prompt token equality")
    require(mq.get("call_count", 0) >= 1, "no actual calls")
    for call in mq["calls"]:
        require(call["prompt_tokens"] == call["preflight_input_count"], "per-call token equality")
        require(call["prompt_tokens"] <= 2048 and call["completion_tokens"] <= 1024, "token ceilings")
    profile_q = read(root / "qualification" / "profile" / "qualification.json")
    require(profile_q["status"] == "PASS" and profile_q["la030_two_sink_substituted"] is False, "profile")
    require({row["population"] for row in profile_q["controls"]} == {"legal", "cve", "skill"}, "profile populations")
    watchdog = read(root / "qualification" / "watchdog" / "qualification.json")
    require(watchdog["status"] == "PASS", "watchdog")
    require(watchdog["historical"]["la030_v2_receipt_upgraded"] is False, "historical receipt upgraded")
    require(watchdog["historical"]["broad_oserror_suppression"] is False, "OSError suppressed")
    oserror = read(root / "qualification" / "watchdog" / "oserror_snapshot.json")
    require(oserror.get("operation") and oserror.get("path") and oserror.get("errno") is not None, "oserror fields")
    require(oserror.get("leaf_identity") and oserror.get("parent_identity"), "identity snapshots")
    driver_q = read(root / "qualification" / "driver" / "qualification.json")
    require(driver_q["status"] == "PASS", "driver")
    require(driver_q["actual_interrupt_resume_probe"] is True and driver_q["configuration_flag_only"] is False, "driver probes")
    require(driver_q["scientific_cells_executed"] == 0, "driver execution")
    runtime_q = read(root / "qualification" / "runtime" / "qualification.json")
    require(runtime_q["complete_attempt_wall_seconds"] == 120, "attempt bound")
    require(runtime_q["max_calls"] == 8 and runtime_q["max_input_tokens"] == 2048 and runtime_q["max_output_tokens"] == 1024, "token contract")
    require(runtime_q["paid_budget"] == 0, "runtime paid")
    freeze = read(root / "cohort" / "source_freeze.json")
    require(freeze["status"] == "PASS", "source freeze")
    require(freeze["canonical_repository_identity_treated_as_complete_fork_audit"] is False, "fork audit")
    require(freeze["skill_procedures_are_independent_human_annotations"] is False, "skill human")
    require(len(freeze["families"]) == 30, "freeze families")
    for family in freeze["families"]:
        require(family.get("source_record_sha256") and (family.get("local_path") or family.get("cve_id") or family.get("skill_id") or family.get("excerpt") or family.get("excerpt_sha256")), "missing source fields")
        if family["population"] == "legal":
            require(len(family.get("source_record_sha256") or "") == 64, "legal hash")
            path = Path(family.get("local_path") or "")
            if path.is_file():
                require(sha_file(path) == family["source_record_sha256"], "legal bytes")
            else:
                require(family.get("excerpt_sha256") or family.get("excerpt"), "missing legal source " + family["id"])
    permissive = study.get("availability_flag") or mq.get("availability_flag_only")
    require(not permissive, "permissive availability flag")
    results = Path(__file__).resolve().parents[2] / "results" / "generated_code_study"
    require(not results.exists() or not any(results.rglob("raw.jsonl")), "scientific outputs present")
    return {
        "status": "PASS",
        "schema": "la-generated-study-preparation-verification/v1",
        "families": 30,
        "cases": 60,
        "schedule_cells": 900,
        "batches": 30,
        "scientific_cells_executed": 0,
        "final_oracles_sealed": True,
        "readiness_only": True,
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--study", type=Path, required=True)
    parser.add_argument("--require-scientific-cells-unexecuted", action="store_true")
    args = parser.parse_args()
    report = verify(args.study, args.require_scientific_cells_unexecuted)
    print(json.dumps(report, sort_keys=True, indent=2))


if __name__ == "__main__":
    main()
