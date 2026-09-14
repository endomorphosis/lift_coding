#!/usr/bin/python3.12
"""Read-only verifier for the LA-032 prospective freeze. Completes readiness only."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

STUDY_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(STUDY_DIR / "preparation"))
from common import (  # noqa: E402
    ARMS,
    QUOTAS,
    ROOT,
    SEEDS,
    SPLIT_SALT,
    build_schedule,
    digest,
    load_json,
    load_study,
    ranking_digest,
    sha_file,
)

MOCK_MARKERS = ("mock", "MagicMock", "unittest.mock", "availability_flag", "permissive")


def require(condition: bool, message: str) -> None:
    if not condition:
        raise SystemExit("FAIL: " + message)


def verify(study_path: Path, require_unexecuted: bool) -> dict[str, Any]:
    study = load_study(study_path)
    families = study["families"]
    cases = study["cases"]
    schedule = study["schedule"]
    require(study["schema"] == "la-closed-loop-study/v1", "study schema")
    require(study["split_salt"] == SPLIT_SALT, "split salt")
    require(study["arms"] == list(ARMS) and study["seeds"] == list(SEEDS), "arms/seeds")
    require(len(families) == 30 and len(cases) == 60 and len(schedule) == 900, "counts")
    require(study.get("scientific_cells_executed") == 0, "scientific execution claimed")
    require(study.get("scientific_cells_claimed_executed") == 0, "claimed executed")
    require(study.get("final_cohort_released") is False, "final cohort released")
    require(study.get("paid_provider_budget") == 0, "paid budget")
    require(study.get("maximum_model_calls_per_attempt") == 8, "call ceiling")
    require(study.get("maximum_input_tokens_per_call") == 2048, "input ceiling")
    require(study.get("maximum_output_tokens_per_call") == 1024, "output ceiling")
    require(study.get("maximum_wall_seconds_per_attempt") == 120, "attempt wall")

    exclusions = load_json(STUDY_DIR / "cohort/exclusions.json")
    old_families = set(exclusions["families"])
    ids = [row["id"] for row in families]
    require(len(set(ids)) == 30, "duplicate families")
    require(not (set(ids) & old_families), "LA-004/LA-029 family overlap")
    old_repos = set(exclusions["repositories"])
    old_names = set(exclusions["repository_names"])
    old_legal = set(exclusions["legal_sections"])
    for family in families:
        if family["population"] == "legal":
            require(family["ancestry_key"][1] not in old_legal, "legal section overlap")
        else:
            repo = family["ancestry_key"][1]
            require(repo not in old_repos, "repository overlap " + repo)
            require(repo.rsplit("/", 1)[-1] not in old_names, "fork name overlap " + repo)
            require(family["fork_audit"]["canonical_identity_insufficient"] is True, "incomplete fork audit")
            require(family["fork_audit"]["status"] == "PASS", "fork audit status")
        require(family["source_record_sha256"] and family["normalized_source_sha256"], "source hashes")
        require(len(family["source_record_sha256"]) == 64, "exact hash")
        require("lawful_access" in json.dumps(family) or family["artifact_id"], "lawful access pin")

    for population, counts in QUOTAS.items():
        group = [row for row in families if row["population"] == population]
        require(len(group) == sum(counts), population + " quota")
        ranked = sorted(group, key=lambda row: (ranking_digest(SPLIT_SALT, population, row["id"]), row["id"].encode("utf-8")))
        expected = ["development"] * counts[0] + ["calibration"] * counts[1] + ["final"] * counts[2]
        require([row["split"] for row in ranked] == expected, population + " ranked split")
        for row in ranked:
            require(row["ranking_sha256"] == ranking_digest(SPLIT_SALT, population, row["id"]), "ranking digest")

    family_by_id = {row["id"]: row for row in families}
    require(len(cases) == 60, "cases")
    require(len({case["id"] for case in cases}) == 60, "unique cases")
    for family in families:
        pair = [case for case in cases if case["source_family"] == family["id"]]
        require(len(pair) == 2, "two cases per family")
        require({case["split"] for case in pair} == {family["split"]}, "descendant split inheritance")
        polarities = {case["polarity"] for case in pair}
        require(polarities == {"allowed", "undeclared_trap"}, "polarity pair")
        for case in pair:
            require(case["constructed_development"] is False, "constructed case")
            require(case["oracle_kind"] == "independent_filesystem_and_journal", "oracle kind")
            if case["split"] == "final":
                require(case["sealed"] is True, "final not sealed")
                require(case.get("retrieval") == [], "final retrieval leaked")
                require(case.get("expected_payload") is None, "final oracle leaked")
                require(case.get("instruction_release") == "final-stage-gate", "final instruction gate")
            else:
                require(case.get("instruction"), "missing instruction")
                require(case.get("expected_payload") is not None, "missing expected payload")
                require(case.get("oracle", {}).get("machine_checkable") is True, "oracle")
                for item in case.get("retrieval") or []:
                    require(item["source_family"] == case["source_family"], "retrieval lineage")
                    require(item["contains_oracle"] is False, "hidden oracle")
                    require(item.get("contains_sibling_final_label") is False, "sibling final")
                    require(item.get("contains_target_patch") is False, "target patch")
            if family["population"] == "skill":
                require(family.get("independent_human_annotation") is False, "skill human annotation claim")

    case_ids = [case_id for family in families for case_id in family["planned_case_ids"]]
    rebuilt = build_schedule(case_ids)
    require(rebuilt == schedule, "schedule reconstruction")
    require(len({row["attempt_id"] for row in schedule}) == 900, "unique identities")
    for seed in SEEDS:
        counts = {arm: [0] * 5 for arm in ARMS}
        for row in schedule:
            if row["seed"] == seed:
                counts[row["arm_id"]][row["arm_position"]] += 1
        for arm, values in counts.items():
            require(values == [12, 12, 12, 12, 12], f"arm balance {seed} {arm}")

    batches_doc = load_json(STUDY_DIR / "family_batches.json")
    require(batches_doc["batch_count"] == 30, "batch count")
    require(batches_doc["development_cells"] == 180, "dev cells")
    require(batches_doc["calibration_cells"] == 180, "cal cells")
    require(batches_doc["final_cells"] == 540, "final cells")
    require(batches_doc["scientific_cells_executed"] == 0, "batch execution")
    require(batches_doc["preparation_may_dispatch_final_cells"] is False, "final dispatch")
    seen = []
    for batch in batches_doc["batches"]:
        family = family_by_id[batch["family_id"]]
        cells = batch.get("cells")
        if not cells:
            wanted = set(family["planned_case_ids"])
            cells = [row for row in schedule if row["case_id"] in wanted]
            cells.sort(key=lambda row: row["schedule_index"])
        require(len(cells) == 30, "batch size")
        require(batch["maximum_scientific_attempt_seconds"] <= 3600, "attempt allowance")
        require(batch["runtime_seconds"] <= 7200, "worker ceiling")
        require(batch["family_id"] in family_by_id, "batch family")
        require(batch["split"] == family["split"], "batch split")
        seen.extend(cell["attempt_id"] for cell in cells)
    require(sorted(seen) == sorted(row["attempt_id"] for row in schedule), "disjoint coverage")

    plan = load_json(STUDY_DIR / "native_dependency_plan.json")
    require(plan["status"] == "BOUND_NOT_REGISTERED", "plan status")
    require(plan["scientific_cells_executed"] == 0, "plan execution")
    require(plan["parent_dependency_update"]["completed_by_this_schedule_freeze"] is False, "LA-031 marked complete")
    require(plan["parent_dependency_update"]["future_batch_success_registered"] is False, "future success")
    require(len(plan["family_batch_tasks"]) == 30, "plan batches")
    require(plan["analysis_freeze_task"]["id"] == "LA-063", "analysis freeze")
    cal_dev = [row["id"] for row in plan["family_batch_tasks"] if row["phase"] in {"development", "calibration"}]
    require(set(plan["analysis_freeze_task"]["depends_on"]) >= set(["LA-032", *cal_dev]), "analysis deps")
    for row in plan["family_batch_tasks"]:
        require("LA-032" in row["depends_on"], "batch depends on preparation")
        if row["phase"] == "final":
            require("LA-063" in row["depends_on"], "final depends on analysis freeze")
        require(row["success_registered"] is False, "batch success registered")
    require("LA-032" in plan["parent_dependency_update"]["depends_on_explicit"], "LA-031 prep dep")
    require("LA-063" in plan["parent_dependency_update"]["depends_on_explicit"], "LA-031 analysis dep")
    require(len(plan["parent_dependency_update"]["depends_on_explicit"]) == 32, "LA-031 dep count")
    require(plan["warm_service"]["systemd_required"] is False, "systemd")
    require(plan["warm_service"]["indefinitely_running_model_required"] is False, "always-on model")

    model = load_json(STUDY_DIR / "model_profile.json")
    require(model["schema"] == "la-qualified-local-model/v1", "model schema")
    require(model["status"] == "PASS", "model status")
    require(model["constructed_transport"] is False, "constructed model")
    for key in ("weights_sha256", "tokenizer_sha256", "chat_template_sha256", "deployment_sha256"):
        require(len(model[key]) == 64 and len(set(model[key])) > 1, "model pin " + key)
    require(model["tokenization_agrees_with_usage"] is True, "token agreement flag")
    qmodel = load_json(STUDY_DIR / "qualification/model/qualification.json")
    require(qmodel["status"] == "PASS", "model qualification")
    require(sha_file(STUDY_DIR / "qualification/model/qualification.json") == model["qualification"]["sha256"], "model binding")
    for call in qmodel["calls"]:
        require(call["prompt_tokens"] == call["input_count"], "prompt_tokens != preflight")
        require(call["prompt_tokens_equal_preflight"] is True, "preflight flag")
        require(call["completion_tokens"] <= 1024, "output ceiling")
    require(qmodel["systemd_required"] is False, "model systemd")
    require(model["scientific_cells_executed"] == 0, "model scientific cells")

    profile = load_json(STUDY_DIR / "qualification/profile/qualification.json")
    require(profile["status"] == "PASS", "profile")
    require(profile["two_sink_la030_substituted"] is False, "two-sink substitute")
    require(profile["fixed_la029_programs_substituted"] is False, "fixed-program substitute")
    require(set(profile["populations"]) == {"legal", "cve", "skill"}, "profile populations")
    watchdog = load_json(STUDY_DIR / "qualification/watchdog/qualification.json")
    require(watchdog["status"] == "PASS", "watchdog")
    require(watchdog["historical_v2_upgraded"] is False, "v2 upgraded")
    require(watchdog["oserror_suppressed_broadly"] is False, "oserror suppressed")
    driver = load_json(STUDY_DIR / "qualification/driver_probes/qualification.json")
    require(driver["status"] == "PASS", "driver")
    require(driver["interrupt_resume"] is True, "interrupt/resume")
    require(driver["scientific_cells_executed"] == 0, "driver cells")
    deadline = load_json(STUDY_DIR / "qualification/deadline/qualification.json")
    require(deadline["status"] == "PASS" and deadline["hard_complete_attempt_seconds"] == 120, "deadline")
    runtime = load_json(STUDY_DIR / "qualification/runtime.json")
    require(runtime["status"] == "PASS", "runtime")
    require(runtime["historical_v2_watchdog_upgraded"] is False, "runtime v2")
    summary = load_json(STUDY_DIR / "qualification/qualification.json")
    require(summary["status"] == "PASS", "summary")
    require(summary["mock_mechanisms"] is False, "mocks")
    require(summary["availability_flag_permitted"] is False, "availability flag")

    sealed = load_json(STUDY_DIR / "cohort/sealed/final_oracles.json")
    require(sealed["released"] is False, "sealed released")
    require(len(sealed["records"]) == 36, "sealed final case count")
    for case in cases:
        if case["split"] == "final":
            require(case["id"] in sealed["records"], "missing sealed record")
            require(digest(sealed["records"][case["id"]]) == case["sealed_material_sha256"], "sealed hash")

    if require_unexecuted:
        require(study["scientific_cells_executed"] == 0, "unexecuted study")
        results = ROOT / "papers/completion/law_to_action/results/generated_code_study"
        if results.exists():
            raw = results / "raw.jsonl"
            require(not raw.exists() or raw.read_text().strip() == "", "scientific raw results present")

    text = json.dumps(study) + json.dumps(summary)
    for marker in ("MagicMock", "permissive availability"):
        require(marker not in text, "mock marker " + marker)

    return {
        "status": "PASS",
        "families": 30,
        "cases": 60,
        "schedule": 900,
        "batches": 30,
        "scientific_cells_executed": 0,
        "readiness_only": True,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--study", type=Path, required=True)
    parser.add_argument("--require-scientific-cells-unexecuted", action="store_true")
    args = parser.parse_args()
    print(json.dumps(verify(args.study, args.require_scientific_cells_unexecuted), sort_keys=True))


if __name__ == "__main__":
    main()
