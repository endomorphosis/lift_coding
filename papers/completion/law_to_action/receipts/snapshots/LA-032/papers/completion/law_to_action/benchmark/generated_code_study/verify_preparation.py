#!/usr/bin/python3.12
"""Read-only recomputation of the LA-032 prospective freeze."""
from __future__ import annotations

import argparse
import hashlib
import json
import random
import re
import sys
from collections import Counter
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[4]
sys.path.insert(0, str(HERE))
from driver import (  # noqa: E402
    ARMS,
    BATCH_ATTEMPT_SECONDS,
    MAX_INPUT,
    MAX_OUTPUT,
    PAID_BUDGET,
    POPULATION_ORDER,
    PROFILE_ID,
    PROMPT_PROFILE,
    QUOTAS,
    SALT,
    SEEDS,
    SPLIT_ORDER,
    WORKER_CEILING,
    arm_position_counts,
    assign_splits,
    build_schedule,
    digest,
    file_sha,
    load_json,
    ranking_sha,
)


def fail(message: str) -> None:
    raise SystemExit("LA-032 preparation verifier failed: " + message)


def require(condition: bool, message: str) -> None:
    if not condition:
        fail(message)


def load_study(path: Path) -> dict:
    study = load_json(path)
    require(study.get("schema") == "la-closed-loop-study/v1", "unexpected study schema")
    require(study.get("split_salt") == SALT, "split salt is not LA016-v1")
    require(study.get("scientific_cells_executed") == 0, "scientific cells were executed")
    require(study.get("scientific_execution_allowed") is False, "scientific execution was allowed")
    require(study.get("final_release_gate") is False, "final gate already released")
    require(study.get("la031_completed") is False, "LA-031 marked complete by the freeze")
    require(study.get("mock") is False, "mock mechanism recorded")
    require(study.get("permissive_availability_flag") is False, "permissive availability flag")
    return study


def verify_sources(study_dir: Path) -> dict:
    manifests = ROOT / "papers/completion/law_to_action/benchmark/manifests"
    old = load_json(manifests / "sources.json")
    exclusions = load_json(study_dir / "cohort/exclusions.json")
    families_doc = load_json(study_dir / "cohort/families.json")
    splits = load_json(study_dir / "cohort/splits.json")
    artifacts = load_json(study_dir / "cohort/source_artifacts.json")
    audit = load_json(study_dir / "cohort/ancestry_audit.json")
    families = families_doc["families"]
    require(len(families) == 30, "not exactly 30 families")
    require(Counter(row["population"] for row in families) == {"legal": 6, "cve": 12, "skill": 12}, "population counts")
    old_ids = {row["lineage_family_id"] for row in old["source_records"]}
    old_repos = {row["ancestry_key"][1] for row in old["source_records"] if row["ancestry_key"][0] == "repository"}
    old_legal = {row["ancestry_key"][1] for row in old["source_records"] if row["population"] == "legal"}
    new_ids = {row["lineage_family_id"] for row in families}
    require(not (new_ids & old_ids), "LA-004/LA-029 family overlap")
    require(not (new_ids & set(exclusions["la004_families"])), "exclusion list overlap")
    require(all(row["bytes_verified"] for row in families), "source bytes not verified")
    require(len({row["normalized_source_sha256"] for row in families}) == 30, "normalized hash collision")
    require(len({tuple(row["ancestry_key"]) for row in families}) == 30, "ancestry collision")
    for row in families:
        require(row["lineage_family_id"] == "family:" + digest(row["ancestry_key"]), "family id is not ancestry digest")
        require(row["independent_human_annotation"] is False, "human annotation claimed")
        if row["population"] == "legal":
            require(row["ancestry_key"][1] not in old_legal, "legal section overlap")
            require(row["source_record_sha256"] and row["bytes_verified"] is True, "legal bytes not verified")
            artifact = next((item for item in artifacts["legal"] if item["artifact_id"] == row["artifact_id"]), None)
            require(artifact is not None and artifact["sha256"] == row["source_record_sha256"] and artifact["size_bytes"] > 1000, "legal artifact pin missing")
            pdf = study_dir / "cohort/legal_raw" / (row["artifact_id"] + ".pdf")
            if pdf.is_file():
                require(file_sha(pdf) == row["source_record_sha256"], "legal PDF hash mismatch")
        else:
            require(row["ancestry_key"][1] not in old_repos, "repository overlap with LA-004")
    skill = [row for row in families if row["population"] == "skill"]
    require(all(row.get("generated_skillcenter_procedure_not_human_annotation") for row in skill), "SkillCenter procedures counted as human annotations")
    require(audit.get("canonical_repository_identity_only") is False, "fork audit reduced to canonical repo identity")
    require(audit.get("generated_skillcenter_counted_as_human_annotation") is False, "generated skills treated as human labels")
    require(artifacts["cve"]["sha256"] == "2e25e84e85e1560d41acacbfc7eb359349f5417bc9bf31318cdf0c4aafccb7d1", "CVE shard hash")
    require(artifacts["skill"]["sha256"] == "8b763be5896b12510c38b92459325d9568770d99cf38aa53ab17485b456d82a4", "skill bundle hash")
    require(artifacts["cve"]["redistribution"]["status"] == "retrieval_only", "CVE redistribution")
    require(splits["salt"] == SALT, "split salt")
    recomputed = assign_splits([{k: row[k] for k in row if k != "split" and k != "ranking_sha256"} for row in families])
    require([row["lineage_family_id"] for row in recomputed] == [row["lineage_family_id"] for row in assign_splits(recomputed)], "split recompute identity")
    expected_assignments = []
    for population, quota in QUOTAS.items():
        rows = [row for row in families if row["population"] == population]
        rows.sort(key=lambda row: (ranking_sha(population, row["lineage_family_id"]), row["lineage_family_id"].encode()))
        offset = 0
        for split, amount in zip(SPLIT_ORDER, quota):
            for row in rows[offset:offset + amount]:
                require(row["split"] == split, "descendant split mismatch")
                require(row["ranking_sha256"] == ranking_sha(population, row["lineage_family_id"]), "ranking hash")
                expected_assignments.append(row["lineage_family_id"])
            offset += amount
    require([row["lineage_family_id"] for row in splits["assignments"]] == expected_assignments, "split assignment order")
    counts = Counter((row["population"], row["split"]) for row in families)
    for population, quota in QUOTAS.items():
        for split, amount in zip(SPLIT_ORDER, quota):
            require(counts[(population, split)] == amount, f"quota {population}/{split}")
    return {"families": 30, "legal_pdfs": 6}


def verify_cases(study_dir: Path, require_unexecuted: bool) -> None:
    cases = load_json(study_dir / "cohort/cases.json")["cases"]
    families = load_json(study_dir / "cohort/families.json")["families"]
    sealed = load_json(study_dir / "cohort/sealed_final_oracles.json")
    require(len(cases) == 60, "not 60 cases")
    require(len({row["id"] for row in cases}) == 60, "duplicate cases")
    by_family = Counter(row["source_family"] for row in cases)
    require(all(count == 2 for count in by_family.values()), "each family needs two cases")
    family_split = {row["lineage_family_id"]: row["split"] for row in families}
    for case in cases:
        require(case["split"] == family_split[case["source_family"]], "case did not inherit parent split")
        require(case["independent_human_annotation"] is False, "human annotation on case")
        require("instruction" in case and case["retrieval"], "missing source-relative task")
        for context in case["retrieval"]:
            require(context["contains_oracle"] is False, "hidden oracle in retrieval")
            require(context["contains_target_patch"] is False, "target patch in retrieval")
            require(context["contains_sibling_final_label"] is False, "sibling final label in retrieval")
            require(context["source_family"] == case["source_family"], "retrieval lineage")
        if case["split"] == "final":
            require(case["oracle_sealed"] is True, "final oracle not sealed")
            require("expected_payload" not in case.get("policy", {}), "final expected payload released")
            require(case["id"] in sealed["oracles"], "sealed oracle missing")
        else:
            require(case["policy"].get("expected_payload"), "open oracle missing")
            require("emit_allowed" in case["policy"]["allowed_handlers"], "policy mapping")
    require(sealed.get("sealed") is True and sealed.get("release_gate") is False, "final seal")
    require(sealed.get("inference_forbidden_until") == "LA-063", "final inference gate")
    if require_unexecuted:
        require(all(not case.get("executed") for case in cases), "case executed")


def verify_schedule(study_dir: Path, study: dict, require_unexecuted: bool) -> None:
    schedule_doc = load_json(study_dir / "schedule.json")
    batches = load_json(study_dir / "family_batches.json")
    families = load_json(study_dir / "cohort/families.json")["families"]
    cases = load_json(study_dir / "cohort/cases.json")["cases"]
    require(schedule_doc["count"] == 900, "not 900 identities")
    case_ids = []
    for population in POPULATION_ORDER:
        rows = [row for row in families if row["population"] == population]
        rows.sort(key=lambda row: (row["ranking_sha256"], row["lineage_family_id"]))
        for family in rows:
            case_ids.extend([family["lineage_family_id"] + ":case-0", family["lineage_family_id"] + ":case-1"])
    require(schedule_doc.get("case_ids") == case_ids, "frozen case-id order")
    expected = build_schedule(case_ids)
    case_map = {row["id"]: row for row in cases}
    for row in expected:
        info = case_map[row["case_id"]]
        row["family_id"] = info["source_family"]
        row["population"] = info["population"]
        row["split"] = info["split"]
        row["executed"] = False
        row["scientific_completed"] = False
    require(digest([row["attempt_id"] for row in expected]) == schedule_doc["identity_digest"], "schedule identity digest")
    require(len({row["attempt_id"] for row in expected}) == 900, "duplicate identities")
    counts = schedule_doc["balancing"]["arm_position_counts_seed_104729"]
    require(all(value == [12, 12, 12, 12, 12] for value in counts.values()), "arm-position balancing")
    require(arm_position_counts(expected) == counts, "balancing recompute")
    require(batches["count"] == 30, "batch count")
    require(batches["development_cells"] == 180 and batches["calibration_cells"] == 180 and batches["final_cells"] == 540, "phase cell counts")
    covered = []
    for batch in batches["batches"]:
        family_cases = [batch["family_binding"] + ":case-0", batch["family_binding"] + ":case-1"]
        cells = [row for row in expected if row["case_id"] in family_cases]
        require(len(cells) == 30, "batch size")
        require(batch["maximum_scientific_attempt_seconds"] == BATCH_ATTEMPT_SECONDS, "batch attempt bound")
        require(batch["runtime_seconds"] == WORKER_CEILING, "worker ceiling")
        require(batch["scientific_cells_completed"] == 0, "batch claimed complete")
        require(batch["registered_success"] is False, "future batch success registered")
        require(batch["family_binding"].startswith("family:"), "family not bound")
        require(batch.get("attempt_ids", [row["attempt_id"] for row in cells]) == [row["attempt_id"] for row in cells], "batch identities")
        covered.extend(row["attempt_id"] for row in cells)
    require(len(set(covered)) == 900, "batch coverage not disjoint/complete")
    require(set(covered) == {row["attempt_id"] for row in expected}, "batch/schedule mismatch")
    phase_counts = Counter(row["phase"] for row in batches["batches"])
    require(phase_counts == {"development": 6, "calibration": 6, "final": 18}, "phase family counts")
    require(len(batches["dispatch_order"]) == 30, "dispatch order")
    if require_unexecuted:
        require(all(row.get("executed") is False and row.get("scientific_completed") is False for row in expected), "scientific cell executed")
        require(study["scientific_cells_executed"] == 0, "study executed cells")
    require(study.get("schedule_count") == 900 and len(study["families"]) == 30 and len(study["cases"]) == 60, "study denominators reduced")
    require(study.get("schedule_identity_digest") == schedule_doc["identity_digest"], "study/schedule digest")


def verify_dependencies(study_dir: Path) -> None:
    plan = load_json(study_dir / "native_dependency_plan.json")
    require(plan["status"] == "BOUND_NOT_EXECUTED", "plan executed")
    require(plan["scientific_cells_executed"] == 0, "plan executed cells")
    require(plan["la031_marked_complete"] is False, "LA-031 completed")
    require(plan["future_batch_success_registered"] is False, "future success")
    batches = plan["family_batch_tasks"]
    require(len(batches) == 30, "plan batches")
    require(batches[0]["id"] == "LA-033" and batches[0]["depends_on"] == ["LA-032"], "first development dependency")
    require("LA-032" in batches[1]["depends_on"] and "LA-033" in batches[1]["depends_on"], "owned prior batch gate")
    cal = next(row for row in batches if row["id"] == "LA-039")
    require(cal["depends_on"] == ["LA-032", "LA-038"], "calibration phase gate")
    analysis = plan["analysis_freeze_task"]
    require(analysis["id"] == "LA-063", "analysis id")
    for task_id in [f"LA-{n:03d}" for n in range(33, 45)]:
        require(task_id in analysis["depends_on"], "analysis missing " + task_id)
    require("LA-032" in analysis["depends_on"], "analysis missing preparation")
    final = next(row for row in batches if row["id"] == "LA-045")
    require("LA-063" in final["depends_on"] and "LA-032" in final["depends_on"], "final missing analysis freeze")
    later = next(row for row in batches if row["id"] == "LA-046")
    require("LA-063" in later["depends_on"] and "LA-045" in later["depends_on"], "final chain")
    parent = plan["parent_dependency_update"]
    require(parent["task_id"] == "LA-031", "parent")
    require(parent["la031_completed_by_this_freeze"] is False, "parent completed")
    require(parent["parent_metadata_insufficient"] is True, "parent metadata treated as enough")
    for task_id in ["LA-032", "LA-063"] + [row["id"] for row in batches]:
        require(task_id in parent["add_explicit_depends_on"], "LA-031 missing " + task_id)


def verify_qualification(study_dir: Path, study: dict) -> None:
    model = load_json(study_dir / "qualification/model.json")
    runtime = load_json(study_dir / "qualification/runtime.json")
    profile = load_json(study_dir / "qualification/profile.json")
    watchdog = load_json(study_dir / "qualification/watchdog.json")
    driver = load_json(study_dir / "qualification/driver.json")
    deadline = load_json(study_dir / "qualification/attempt_deadline.json")
    model_profile = load_json(study_dir / "model_profile.json")
    for document in (model, runtime, profile, watchdog, driver, deadline):
        require(document.get("status") == "PASS", "qualification not PASS")
        require(document.get("mock") is not True, "mock qualification")
    require(model.get("constructed_transport") is False, "constructed transport used as model")
    require(model.get("availability_flag_only") is False, "availability flag")
    require(model.get("tokenization_agrees_with_usage") is True, "token agreement missing")
    require(len(model["calls"]) >= 3, "insufficient real model calls")
    for call in model["calls"]:
        require(call["prompt_tokens"] == call["preflight_input_count"], "prompt_tokens != preflight input_count")
        require(call["prompt_tokens"] <= MAX_INPUT, "input ceiling")
        require(call["completion_tokens"] <= MAX_OUTPUT, "output ceiling")
        require(call.get("raw_sha256") and re.fullmatch(r"[0-9a-f]{64}", call["raw_sha256"]), "raw response not preserved")
    require(model["output_ceiling_respected"] is True, "1024 ceiling")
    require(model["cancellation_observed"] is True, "cancellation")
    require(model["warm_reuse"] is True, "warm reuse")
    require(model["systemd_required"] is False, "systemd prerequisite")
    require(model_profile["weights_sha256"] == model["weights_sha256"], "weights pin")
    require(model_profile["tokenizer_sha256"] == model["tokenizer_sha256"], "tokenizer pin")
    require(model_profile["chat_template_sha256"] == model["chat_template_sha256"], "template pin")
    require(model_profile["model_revision"] == model["model_revision"], "revision pin")
    require(model_profile["paid_budget"] == PAID_BUDGET, "paid budget")
    require((study_dir / "qualification/model/model.json").is_file(), "model weights missing")
    require(file_sha(study_dir / "qualification/model/model.json") == model["weights_sha256"], "weight bytes")
    require(profile["profile"] == PROFILE_ID, "profile id")
    require(profile["two_sink_profile_substituted"] is False if "two_sink_profile_substituted" in profile else all(not row["la030_two_sink_substituted"] for row in profile["rows"]), "LA-030 profile substituted")
    require(all(row["positive_useful_work"] and row["negative_undeclared_effect"] and row["generic_rejected"] for row in profile["rows"]), "profile tests")
    require(set(row["population"] for row in profile["rows"]) == set(POPULATION_ORDER), "profile populations")
    require(watchdog["historical_v2_receipt_upgraded"] is False, "v2 receipt upgraded")
    require(watchdog["broad_oserror_suppressed"] is False, "OSError suppressed")
    require(watchdog.get("enoent") == 2, "ENOENT not retained")
    require(watchdog.get("parent_revalidated") is True, "parent revalidation")
    require(driver["interrupt_resume"] is True and driver["configuration_flag_only"] is False, "driver probes")
    require(driver["silent_replay"] is False, "silent replay")
    require(driver["scientific_cells_completed"] == 0, "scientific cell completed in driver probe")
    require(deadline["max_calls"] == 8 and deadline["max_input_tokens"] == MAX_INPUT and deadline["max_output_tokens"] == MAX_OUTPUT, "attempt contract")
    require(deadline["paid_budget"] == 0, "paid budget")
    require(runtime["source_files"]["papers/completion/law_to_action/benchmark/generated_code_study/driver.py"] == file_sha(study_dir / "driver.py"), "runtime/driver binding")
    require(study["prompt_profile_sha256"] == digest(PROMPT_PROFILE), "prompt freeze")
    require(study["execution_profile"] == PROFILE_ID, "execution profile")
    require(study["model_profile_sha256"] == digest(model_profile), "model profile freeze")
    for name in ("model.json", "runtime.json", "profile.json", "watchdog.json", "driver.json"):
        text = (study_dir / "qualification" / name).read_text().lower()
        require("availability_flag" not in text or "false" in text, "permissive flag text")


def verify_driver_source(study_dir: Path) -> None:
    source = (study_dir / "driver.py").read_text()
    require("DiagnosticWatchdog" in source and "errno" in source, "watchdog diagnostic missing")
    require("broad_oserror_suppressed" in source or "Broad OSError suppression is forbidden" in source, "suppression policy")
    require("reserve_cell" in source and "reserve_model_call" in source, "reservations")
    require("silent replay" in source.lower() or "silent replay" in source, "replay guard")
    require("preparation cannot dispatch final cells" in source, "final dispatch guard")
    require("prompt_tokens must equal retained preflight input_count" in source, "token equality")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--study", type=Path, required=True)
    parser.add_argument("--require-scientific-cells-unexecuted", action="store_true")
    args = parser.parse_args()
    study_path = args.study
    study_dir = study_path.parent
    study = load_study(study_path)
    verify_sources(study_dir)
    verify_cases(study_dir, args.require_scientific_cells_unexecuted)
    verify_schedule(study_dir, study, args.require_scientific_cells_unexecuted)
    verify_dependencies(study_dir)
    verify_qualification(study_dir, study)
    verify_driver_source(study_dir)
    print(json.dumps({
        "status": "PASS",
        "families": 30,
        "cases": 60,
        "identities": 900,
        "batches": 30,
        "scientific_cells_executed": 0,
        "readiness_only": True,
    }))


if __name__ == "__main__":
    main()
