#!/usr/bin/env python3
"""Read-only recomputation of the LA-032 prospective freeze."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Mapping

HERE = Path(__file__).resolve().parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))

from preparation.study_common import (
    ARMS,
    CVE_ARTIFACT,
    MODEL_PIN,
    POPULATION_ORDER,
    PROMPT_PROFILE,
    QUOTAS,
    SEEDS,
    SKILL_ARTIFACT,
    SPLIT_SALT,
    arm_position_counts,
    assign_splits,
    build_schedule,
    digest,
    expand_batch_identities,
    expand_schedule,
    load_json,
    locate_model_cache,
    locate_source_cache,
    paper_root,
    ranking_sha,
    sha_file,
    study_dir,
)


def require(condition: bool, message: str) -> None:
    if not condition:
        raise SystemExit("LA-032 preparation verification failed: " + message)


def load_exclusions(root: Path) -> set[str]:
    sources = load_json(root / "papers/completion/law_to_action/benchmark/manifests/sources.json")
    frozen = load_json(root / "papers/completion/law_to_action/benchmark/fixed_action_operator/frozen_inputs.json")
    families = {row["lineage_family_id"] for row in sources["source_records"]}
    families |= {row["lineage_family_id"] for row in frozen.get("candidates", []) if row.get("lineage_family_id")}
    return families


def verify(study_path: Path, require_unexecuted: bool = True) -> dict[str, Any]:
    root = paper_root()
    study = study_dir()
    require(study_path.resolve() == (study / "prospective_study.json").resolve(), "study path is not the frozen prospective_study.json")
    freeze = load_json(study_path)
    require(freeze["schema"] == "la-closed-loop-study/v1", "unexpected study schema")
    require(freeze.get("availability_flag") is False, "permissive availability flag")
    require(freeze.get("mock_mechanism") is False, "mock mechanism")
    require(freeze.get("reduced_denominator") is False, "reduced denominator")
    require(freeze.get("scientific_execution_allowed") is False, "scientific execution must remain closed")
    require(freeze.get("final_stage_gate_open") is False, "final-stage gate must stay closed")
    require(freeze.get("scientific_cells_claimed_executed") == 0, "preparation claimed scientific cells")
    require(freeze["split_salt"] == SPLIT_SALT, "split salt differs")
    require(freeze["arms"] == list(ARMS) and freeze["seeds"] == list(SEEDS), "arm/seed contract differs")
    require(freeze["prompt_profile_sha256"] == digest(PROMPT_PROFILE), "prompt profile differs")
    require(freeze["independent_effect_oracle_frozen"] is True, "oracle freeze missing")
    families = freeze["families"]
    freeze_cases = freeze["cases"]
    cases_path = study / "cohort" / "cases.jsonl"
    cases = [json.loads(line) for line in cases_path.read_text(encoding="utf-8").splitlines() if line.strip()]
    require({row["id"] for row in freeze_cases} == {row["id"] for row in cases}, "freeze case ids differ from cases.jsonl")
    require(all(row["split"] == next(item["split"] for item in cases if item["id"] == row["id"]) for row in freeze_cases), "freeze case splits differ")
    schedule_path = study / "schedule.json"
    schedule_doc = load_json(schedule_path)
    require(freeze.get("schedule_count") == 900, "schedule count")
    require(freeze.get("schedule_sha256") == sha_file(schedule_path), "schedule binding")
    if isinstance(freeze.get("schedule"), list) and freeze["schedule"]:
        schedule = freeze["schedule"]
    else:
        schedule = expand_schedule(schedule_doc)
    require(schedule_doc["planned_cells"] == 900 and schedule_doc["scientific_cells_completed"] == 0, "schedule document")
    require(len(expand_schedule(schedule_doc)) == 900, "expanded schedule count")
    require(len(families) == 30 and len({row["id"] for row in families}) == 30, "family count")
    require(len(cases) == 60 and len({row["id"] for row in cases}) == 60, "case count")
    require(len(schedule) == 900 and len({row["attempt_id"] for row in schedule}) == 900, "identity count")
    excluded = load_exclusions(root)
    overlap = {row["id"] for row in families} & excluded
    require(not overlap, "LA-004/LA-029 family overlap: " + ",".join(sorted(overlap)[:8]))
    recomputed = assign_splits([{"id": row["id"], "population": row["population"]} for row in families])
    expected_split = {row["id"]: row["split"] for row in recomputed}
    for row in families:
        require(row["split"] == expected_split[row["id"]], "ranked split differs for " + row["id"])
        require(row["ranking_sha256"] == ranking_sha(row["population"], row["id"]), "ranking sha differs")
    for population, counts in QUOTAS.items():
        require(sum(row["population"] == population and row["split"] == "development" for row in families) == counts[0], population + " development quota")
        require(sum(row["population"] == population and row["split"] == "calibration" for row in families) == counts[1], population + " calibration quota")
        require(sum(row["population"] == population and row["split"] == "final" for row in families) == counts[2], population + " final quota")
    family_by_id = {row["id"]: row for row in families}
    for case in cases:
        parent = family_by_id[case["source_family"]]
        require(case["split"] == parent["split"], "case split does not inherit parent")
        require(case.get("independent_human_annotation") is False, "human annotation claim")
        require(sum(item["source_family"] == case["source_family"] for item in cases) == 2, "family pairing")
        if parent["split"] == "final":
            require(case.get("sealed") is True and case.get("released_to_inference") is False, "final case not sealed")
        else:
            require("instruction" in case and "expected_payload" in case and "oracle" in case, "unsealed case incomplete")
            require(
                case["retrieval"]
                and all(
                    item.get("contains_oracle") is False
                    and item.get("contains_target_patch") is False
                    and item.get("contains_sibling_final_label") is False
                    and item.get("source_family") == case["source_family"]
                    for item in case["retrieval"]
                ),
                "retrieval lineage/oracle",
            )
    sealed = load_json(study / "cohort" / "sealed_final.json")
    require(sealed["gate"] == "closed", "sealed gate open")
    require(sha_file(study / "cohort" / "sealed_final.json") == freeze["sealed_final"]["sha256"], "sealed binding")
    final_ids = {row["id"] for row in cases if row["split"] == "final"}
    require(set(sealed["cases"]) == final_ids, "sealed final coverage")
    for case_id, body in sealed["cases"].items():
        require(set(body) >= {"instruction", "payload", "expected_payload", "oracle", "policy", "retrieval"}, "sealed body incomplete")
        require(all(item.get("contains_oracle") is False for item in body["retrieval"]), "sealed retrieval leaked oracle")
    recomputed_schedule = build_schedule([row["id"] for row in cases])
    require(
        [(row["attempt_id"], row["arm"], row["seed"], row["case_id"], row["arm_position"]) for row in schedule]
        == [(row["attempt_id"], row["arm"], row["seed"], row["case_id"], row["arm_position"]) for row in recomputed_schedule],
        "schedule identities differ from original shuffle rule",
    )
    require(all(counts == [12, 12, 12, 12, 12] for counts in arm_position_counts(schedule).values()), "arm-position balancing")
    require(sum(1 for row in schedule if family_by_id[next(case["source_family"] for case in cases if case["id"] == row["case_id"])]["split"] == "development") == 180, "development cells")
    require(sum(1 for row in schedule if row.get("split") == "calibration" or family_by_id[next(c["source_family"] for c in cases if c["id"] == row["case_id"])]["split"] == "calibration") == 180, "calibration cells")
    require(sum(1 for row in schedule if family_by_id[next(c["source_family"] for c in cases if c["id"] == row["case_id"])]["split"] == "final") == 540, "final cells")
    if require_unexecuted:
        require(all(row.get("scientific_completed") is False for row in schedule), "scientific cell marked completed")

    cache = locate_source_cache()
    require(sha_file(cache / CVE_ARTIFACT["filename"]) == CVE_ARTIFACT["sha256"], "CVE shard missing or changed")
    require(sha_file(cache / SKILL_ARTIFACT["filename"]) == SKILL_ARTIFACT["sha256"], "skill bundle missing or changed")
    pins = load_json(study / "cohort" / "source_pins.json")
    for document in pins["legal_documents"]:
        path = cache / "legal" / f"{document['section']}.pdf"
        require(path.is_file() and sha_file(path) == document["sha256"] and path.read_bytes()[:4] == b"%PDF", "legal source missing")
        require(document["section"] not in {row["ancestry_key"][1] for row in load_json(root / "papers/completion/law_to_action/benchmark/manifests/sources.json")["source_records"] if row["population"] == "legal"}, "legal section reuse")

    model_cache = locate_model_cache()
    require(sha_file(model_cache / MODEL_PIN["weights_file"]) == MODEL_PIN["weights_sha256"], "model weights missing or changed")
    for name, expected in MODEL_PIN["tokenizer_files"].items():
        require(sha_file(model_cache / name) == expected, "tokenizer pin missing: " + name)

    model_profile = load_json(study / "model_profile.json")
    require(model_profile["schema"] == "la-qualified-local-model/v1", "model profile schema")
    require(sha_file(study / "model_profile.json") == freeze["model_profile_sha256"], "model profile binding")
    require(model_profile["systemd_required"] is False and model_profile["indefinitely_running_required"] is False, "service prerequisite")
    model_q = load_json(study / "qualification" / "model" / "qualification.json")
    require(model_q["status"] == "PASS" and model_q["constructed_transport"] is False and model_q["mock_mechanism"] is False, "model qualification")
    require(model_q["tokenization_agrees_with_usage"] is True, "token agreement flag")
    for call in model_q["calls"]:
        require(call["prompt_tokens"] == call["input_count"], "prompt_tokens != preflight input_count")
    require(sha_file(study / "qualification" / "model" / "qualification.json") == freeze["model_qualification"]["sha256"], "model qualification binding")

    profile_q = load_json(study / "qualification" / "generated_program_profile" / "qualification.json")
    require(profile_q["status"] == "PASS" and profile_q["la030_two_sink_substituted"] is False and profile_q["la029_fixed_programs_substituted"] is False, "profile qualification")
    require(set(profile_q["populations"]) == {"legal", "cve", "skill"}, "profile populations")
    require(sha_file(study / "qualification" / "generated_program_profile" / "qualification.json") == freeze["generated_program_profile"]["sha256"], "profile binding")

    watchdog_q = load_json(study / "qualification" / "watchdog" / "qualification.json")
    require(watchdog_q["status"] == "PASS" and watchdog_q["historical_receipt_upgraded"] is False, "watchdog qualification")
    require(watchdog_q["broad_oserror_suppressed"] is False, "OSError suppressed")
    require(watchdog_q["oserror_errno_retained"] and watchdog_q["oserror_path_retained"] and watchdog_q["oserror_operation_retained"], "watchdog diagnostic fields")
    historical = load_json(study / "qualification" / "watchdog" / "historical_v2_investigation.json")
    require(historical["historical_receipt_upgraded"] is False and historical["errno_proven"] is False, "v2 receipt upgraded")

    driver_q = load_json(study / "qualification" / "driver" / "qualification.json")
    require(driver_q["status"] == "PASS" and driver_q["scientific_cells_completed"] == 0, "driver qualification")
    require(driver_q["mock_mechanism"] is False and driver_q["final_cells_blocked"] is True, "driver final/mock")
    require(driver_q["interrupt_resume"] is True and driver_q["cleanup_fault_unknown_not_absence"] is True, "driver probes")

    batches = load_json(study / "family_batches.json")
    require(batches["batch_count"] == 30 and len(batches["batches"]) == 30, "batch count")
    require(batches["development_cells"] == 180 and batches["calibration_cells"] == 180 and batches["final_cells"] == 540, "phase cells")
    require(batches["scientific_contrasts_preserved"] is True, "scientific contrasts")
    seen_attempts: set[str] = set()
    seen_families: set[str] = set()
    for batch in batches["batches"]:
        cells = expand_batch_identities(batch, schedule)
        require(len(cells) == 30 and len(batch["original_schedule_indexes"]) == 30, "batch size")
        require(batch["maximum_scientific_attempt_seconds"] == 3600, "batch scientific allowance")
        require(batch["runtime_seconds"] == 7200, "worker ceiling")
        require(batch["family_id"] not in seen_families, "duplicate family batch")
        seen_families.add(batch["family_id"])
        for cell, index in zip(cells, batch["original_schedule_indexes"]):
            require(cell["attempt_id"] not in seen_attempts, "overlapping batch cell")
            require(schedule[index]["attempt_id"] == cell["attempt_id"], "batch schedule index")
            require(cell["case_id"] in batch["case_ids"], "batch case pairing")
            seen_attempts.add(cell["attempt_id"])
    require(seen_attempts == {row["attempt_id"] for row in schedule}, "batch coverage of 900 identities")
    require(seen_families == {row["id"] for row in families}, "batch coverage of 30 families")
    require(sha_file(study / "family_batches.json") == freeze["family_batches"]["sha256"], "batch binding")

    plan = load_json(study / "native_dependency_plan.json")
    require(plan["status"] == "BOUND_NOT_EXECUTED", "dependency plan executed")
    require(plan["scientific_cells_executed"] == 0 and plan["la031_marked_complete"] is False, "LA-031 marked complete")
    require(plan["future_batch_success_registered"] is False, "future batch success registered")
    require(len(plan["family_batch_tasks"]) == 30, "batch tasks")
    require(plan["analysis_freeze_task"]["id"] == "LA-063", "analysis freeze id")
    dev_cal = [row["id"] for row in plan["family_batch_tasks"] if row["phase"] in ("development", "calibration")]
    require(set(plan["analysis_freeze_task"]["depends_on"]) >= set(["LA-032", *dev_cal]), "analysis freeze deps")
    for row in plan["family_batch_tasks"]:
        require("LA-032" in row["depends_on"], "batch missing LA-032")
        require(row["registered_success"] is False and row["scientific_cells_completed"] == 0, "batch success registered")
        if row["phase"] in ("development", "calibration"):
            require("LA-032" in row["depends_on"], "dev/cal gate")
        if row["phase"] == "final":
            require("LA-063" in row["depends_on"], "final missing analysis freeze")
    require(set(plan["parent_dependency_update"]["add_explicit_depends_on"]) == {"LA-032", "LA-063", *[row["id"] for row in plan["family_batch_tasks"]]}, "LA-031 explicit deps")
    require(plan["parent_dependency_update"]["mark_complete"] is False, "LA-031 completion by freeze")
    require(sha_file(study / "native_dependency_plan.json") == freeze["native_dependency_plan"]["sha256"], "dependency binding")

    driver_text = (study / "driver.py").read_text()
    require("reserve_cell" in driver_text and "reserve_model_call" in driver_text, "driver reservations")
    require("silent replay" in driver_text.lower() or "replay forbidden" in driver_text.lower() or "refund/replay forbidden" in driver_text, "driver replay contract")

    mappings = load_json(study / "cohort" / "source_task_oracle_mappings.json")["mappings"]
    require(len(mappings) == 60, "mapping completeness")
    require(all(row.get("sealed") is (family_by_id[row["source_family"]]["split"] == "final") for row in mappings), "mapping seal")

    report = {
        "status": "PASS",
        "schema": "la032-preparation-verification/v1",
        "families": 30,
        "cases": 60,
        "identities": 900,
        "batches": 30,
        "scientific_cells_executed": 0,
        "final_stage_gate_open": False,
        "availability_flag": False,
        "mock_mechanism": False,
        "study_sha256": sha_file(study_path),
    }
    return report


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--study", required=True, type=Path)
    parser.add_argument("--require-scientific-cells-unexecuted", action="store_true")
    args = parser.parse_args()
    print(json.dumps(verify(args.study, args.require_scientific_cells_unexecuted), indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
