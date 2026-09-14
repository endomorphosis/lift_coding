#!/usr/bin/python3.12
"""Read-only verifier for the LA-032 generated-code study freeze."""
from __future__ import annotations

import argparse
import json
import random
import sys
from collections import Counter
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE / "preparation"))

from study_common import (  # noqa: E402
    ARMS,
    LIVE,
    POPULATIONS,
    PROMPT_PROFILE,
    QUOTAS,
    ROOT,
    SALT,
    SEEDS,
    SPLIT_ORDER,
    decode_schedule_rows,
    digest,
    load_json,
    ranking_digest,
    retrieve_source_artifact,
    sha_file,
)

MOCK_MARKERS = ("mock", "fake", "stub", "dummy", "availability_ok", "permissive")


class VerifyError(ValueError):
    pass


def require(condition: bool, message: str) -> None:
    if not condition:
        raise VerifyError(message)


def load_study(path: Path) -> dict:
    study = load_json(path)
    require(study.get("schema") == "la-closed-loop-study/v1", "study schema")
    require(study.get("split_salt") == SALT, "split salt")
    require(study.get("arms") == list(ARMS) and study.get("seeds") == list(SEEDS), "arms/seeds")
    require(study.get("scientific_cells_executed") == 0, "scientific cells were executed")
    require(study.get("final_cells_dispatched") == 0, "final cells dispatched")
    require(study.get("availability_flag") is False, "permissive availability flag")
    require(study.get("mock_mechanism") is False, "mock mechanism")
    require(study.get("la030_two_sink_substituted") is False, "LA-030 two-sink substituted")
    require(study.get("sealed_final") is True, "final material not sealed")
    require(study.get("independent_effect_oracle_frozen") is True, "oracles not frozen")
    require(study.get("prompt_profile_sha256") == digest(PROMPT_PROFILE), "prompt profile")
    require(study.get("paid_budget") == 0, "paid budget")
    return study


def verify_sources(study: dict, root: Path) -> None:
    sources = load_json(root / "cohort" / "sources.json")
    old = load_json(LIVE / "benchmark" / "manifests" / "sources.json")
    old_families = {r["lineage_family_id"] for r in old["source_records"]}
    old_repos = {r["ancestry_key"][1] for r in old["source_records"] if r["ancestry_key"][0] == "repository"}
    old_sections = {r["ancestry_key"][1] for r in old["source_records"] if r["population"] == "legal"}
    records = sources["source_records"]
    require(len(records) == 30, "source count")
    counts = Counter(r["population"] for r in records)
    require(counts["legal"] == 6 and counts["cve"] == 12 and counts["skill"] == 12, "population counts")
    families = {r["lineage_family_id"] for r in records}
    require(len(families) == 30, "duplicate families")
    require(not (families & old_families), "LA-004/LA-029 family overlap")
    for record in records:
        require(record["source_id"] not in {r["source_id"] for r in old["source_records"]}, "source id overlap")
        if record["population"] == "legal":
            require(record["ancestry_key"][1] not in old_sections, "legal section overlap")
        else:
            require(record["ancestry_key"][1] not in old_repos, "repository overlap")
            require(record["fork_clone_audit"]["canonical_repository"] == record["ancestry_key"][1], "fork audit missing")
        require("sha256" in str(record["source_record_sha256"]), "source hash missing") if False else None
        require(len(record["source_record_sha256"]) == 64 and len(record["normalized_source_sha256"]) == 64, "source hashes")
        if record["population"] == "skill":
            require(record.get("independent_human_annotation") is False, "skill counted as human annotation")
    require(sources["source_bodies_exported"] == 0, "source bodies exported")
    require(sources["exclusions"]["canonical_identity_not_sufficient"] is True, "fork audit reduced to identity")
    artifacts = {a["artifact_id"]: a for a in sources["source_artifacts"]}
    for artifact in artifacts.values():
        path = retrieve_source_artifact(artifact)
        require(path.is_file(), "missing source artifact: " + artifact["artifact_id"])
        require(sha_file(path) == artifact["sha256"], "source artifact hash changed: " + artifact["artifact_id"])
        require(path.stat().st_size == artifact["size_bytes"], "source artifact size changed")
        require(artifact["redistribution"]["included_bytes"] == 0, "redistributed source bytes")


def study_cases(root: Path) -> list:
    return load_json(root / "cohort" / "cases.json")["cases"]


def study_families(study: dict, root: Path) -> list:
    if study.get("families"):
        return study["families"]
    return load_json(root / "cohort" / "families.json")["families"]


def study_schedule(study: dict, root: Path) -> list:
    document = load_json(root / "schedule.json")
    rows = decode_schedule_rows(document)
    if study.get("schedule"):
        require(len(study["schedule"]) == len(rows), "embedded schedule length")
    return rows


def verify_splits(study: dict, root: Path) -> None:
    families = study_families(study, root)
    require(len(families) == 30, "family count")
    for population, counts in QUOTAS.items():
        ranked = sorted((f for f in families if f["population"] == population), key=lambda f: (ranking_digest(population, f["id"]), f["id"].encode("utf-8")))
        expected = ["development"] * counts[0] + ["calibration"] * counts[1] + ["final"] * counts[2]
        require([f["split"] for f in ranked] == expected, "ranked split differs for " + population)
        for family in ranked:
            require(family["ranking_sha256"] == ranking_digest(population, family["id"]), "ranking hash")
    cases = study_cases(root)
    require(len(cases) == 60, "case count")
    by_family = {f["id"]: f for f in families}
    for case in cases:
        require(case["split"] == by_family[case["source_family"]]["split"], "case split inheritance")
    require(sum(1 for f in families if f["split"] == "development") == 6, "development families")
    require(sum(1 for f in families if f["split"] == "calibration") == 6, "calibration families")
    require(sum(1 for f in families if f["split"] == "final") == 18, "final families")


def verify_schedule(study: dict, root: Path) -> None:
    schedule = load_json(root / "schedule.json")
    rows = decode_schedule_rows(schedule)
    require(len(rows) == 900, "900 identities")
    require(schedule["development_cells"] == 180 and schedule["calibration_cells"] == 180 and schedule["final_cells"] == 540, "phase cells")
    require(schedule["scientific_cells_executed"] == 0, "schedule executed")
    case_ids = [c["id"] for c in study_cases(root)]
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
            for position, arm in enumerate(rotated):
                rebuilt.append((f"{seed}:{arm}:{case_id}", index, seed, arm, case_id, position))
                index += 1
    actual_ids = [r["attempt_id"] for r in rows]
    rebuilt_ids = [item[0] for item in rebuilt]
    require(actual_ids == rebuilt_ids, "schedule identities differ from original algorithm")
    ids = actual_ids
    require(len(set(ids)) == 900, "duplicate identities")
    for seed in SEEDS:
        for arm in ARMS:
            counts = schedule["arm_position_balancing"][str(seed)][arm]
            require(counts == [12, 12, 12, 12, 12], f"arm position balancing {seed} {arm}")


def verify_batches(study: dict, root: Path) -> None:
    batches = load_json(root / "family_batches.json")
    require(batches["count"] == 30 and len(batches["batches"]) == 30, "batch count")
    require(batches["development_families"] == 6 and batches["calibration_families"] == 6 and batches["final_families"] == 18, "batch phases")
    require(batches["scientific_cells_executed"] == 0 and batches["preparation_claimed_cells_completed"] == 0, "batches claimed executed")
    covered = []
    schedule_rows = study_schedule(study, root)
    by_family: dict[str, list[str]] = {}
    for row in schedule_rows:
        by_family.setdefault(row["source_family"], []).append(row["attempt_id"])
    for batch in batches["batches"]:
        derived = by_family[batch["family_id"]]
        require(len(derived) == 30, "batch size")
        if "cell_ids" in batch:
            require(batch["cell_ids"] == derived, "batch cell identities")
        require(batch["maximum_scientific_attempt_seconds"] == 3600, "batch attempt allowance")
        require(batch["runtime_seconds"] == 7200, "worker ceiling")
        require(batch["scientific_cells_executed"] == 0, "batch executed")
        covered.extend(derived)
    require(len(set(covered)) == 900, "disjoint coverage")
    require(set(covered) == {r["attempt_id"] for r in schedule_rows}, "batch coverage vs schedule")
    require(batches["dispatch_order"]["scientific_contrasts_preserved"] is True, "contrasts")
    require(batches["dispatch_order"]["operational_amendment_visible"] is True, "order not recorded")


def verify_oracles(study: dict, root: Path) -> None:
    cases = study_cases(root)
    sealed = load_json(root / "cohort" / "sealed_final.json")
    require(sealed["released"] is False and sealed["released_to_inference"] is False, "final oracles released")
    mappings = load_json(root / "cohort" / "source_to_oracle_mappings.json")["mappings"]
    require(len(mappings) == 60, "mapping count")
    for case in cases:
        require(case.get("constructed_development") is False, "constructed case in cohort")
        if case["split"] == "final":
            require(case.get("oracle_sealed") is True, "final case unsealed")
            require("expected_payload" not in case, "final expected payload visible")
            require(case["id"] in sealed["oracles"], "missing sealed oracle")
            require(sealed["oracles"][case["id"]]["released_to_inference"] is False, "sealed oracle released")
        else:
            require("expected_payload" in case and "oracle" in case, "dev/cal oracle missing")
            require(case["oracle"]["machine_checkable"] is True, "oracle not machine-checkable")
            require(case["oracle"]["human_annotation"] is False, "human annotation claimed")
        for item in case["retrieval"]:
            require(item["source_family"] == case["source_family"], "retrieval lineage")
            require(item["contains_oracle"] is False, "hidden oracle in retrieval")
            require(item["contains_sibling_final_label"] is False, "sibling final label")
            require(item["contains_target_patch"] is False, "target patch")


def verify_qualification(study: dict, root: Path) -> None:
    profile = load_json(root / "qualification" / "profile" / "qualification.json")
    require(profile["status"] == "PASS", "profile")
    require(profile["two_sink_la030_substituted"] is False, "two-sink substitute")
    require(profile["fixed_la029_programs_substituted"] is False, "LA-029 substitute")
    require(profile["syntax_escape_rejected"] and profile["positive_useful_work"] and profile["negative_undeclared_effect"], "profile controls")
    require(profile["mock_mechanism"] is False, "profile mock")
    require(len(profile["controls"]) == 3, "profile populations")
    model = load_json(root / "model_profile.json")
    require(model["status"] == "PASS", "model profile")
    require(model["constructed_transport"] is False, "constructed model")
    require(model["tokenization_agrees_with_usage"] is True, "prompt_tokens agreement")
    require(model["max_output_tokens"] == 1024 and model["max_input_tokens"] == 2048, "token ceilings")
    require(model["systemd_required"] is False and model["indefinitely_running_required"] is False, "systemd prerequisite")
    require(model["scientific_cells_executed"] == 0, "model scientific cells")
    require(sha_file(root / "model_profile.json") == study["model_profile_sha256"], "model pin")
    mq = load_json(root / "qualification" / "model" / "qualification.json")
    require(mq["tokenization_agrees_with_usage"] is True, "model qualification tokens")
    require(mq["actual_model_calls"] >= 1, "no actual model calls")
    for call in mq["calls"]:
        require(call["prompt_tokens"] == call["input_count"], "prompt_tokens != preflight input_count")
    watchdog = load_json(root / "qualification" / "watchdog" / "qualification.json")
    require(watchdog["status"] == "PASS" and watchdog["historical_v2_upgraded"] is False, "watchdog")
    require(watchdog["oserror_not_broadly_suppressed"] and watchdog["errno_path_operation_retained"], "watchdog diagnostics")
    historical = load_json(root / "qualification" / "watchdog" / "historical_v2_binding.json")
    require(historical["upgraded"] is False and historical["status"] == "FAILED_RETAINED", "v2 upgraded")
    deadline = load_json(root / "qualification" / "deadline" / "qualification.json")
    require(deadline["complete_attempt_wall_seconds"] == 120, "120s bound")
    require(deadline["maximum_model_calls"] == 8 and deadline["paid_budget"] == 0, "attempt contract")
    require(deadline["overrun_retained"] is True, "overruns truncated")
    driver = load_json(root / "qualification" / "driver" / "qualification.json")
    require(driver["status"] == "PASS", "driver")
    require(driver["interrupt_resume"] and driver["cleanup_fault_probe"], "driver probes")
    require(driver["scientific_cells_executed"] == 0 and driver["final_cells_dispatched"] == 0, "driver scientific")
    require(driver["silent_replay"] is False and driver["refunded_calls"] == 0, "replay/refund")
    require(driver["configuration_flag_only"] is False, "driver flags only")
    runtime = load_json(root / "qualification" / "runtime.json")
    require(runtime["la030_v2_receipt_upgraded"] is False, "runtime upgraded v2")
    text = json.dumps({"profile": profile, "model": model, "driver": driver, "watchdog": watchdog})
    for marker in ("MagicMock", "unittest.mock", "fake_model", "always_available"):
        require(marker not in text, "mock marker " + marker)


def verify_dependencies(root: Path) -> None:
    plan = load_json(root / "native_dependency_plan.json")
    require(plan["future_batch_success_registered"] is False, "future success registered")
    require(plan["la031_marked_complete"] is False, "LA-031 marked complete")
    batches = plan["family_batch_tasks"]
    require(len(batches) == 30, "dependency batches")
    development = [b for b in batches if b["phase"] == "development"]
    calibration = [b for b in batches if b["phase"] == "calibration"]
    final = [b for b in batches if b["phase"] == "final"]
    require(len(development) == 6 and len(calibration) == 6 and len(final) == 18, "phase tasks")
    for batch in development + calibration:
        require("LA-032" in batch["depends_on"], "dev/cal missing LA-032")
    analysis = plan["analysis_freeze_task"]
    for ident in [b["id"] for b in development + calibration]:
        require(ident in analysis["depends_on"], "analysis missing " + ident)
    require("LA-032" in analysis["depends_on"], "analysis missing LA-032")
    for batch in final:
        require("LA-063" in batch["depends_on"] and "LA-032" in batch["depends_on"], "final dependencies")
    parent = plan["parent_dependency_update"]
    expected = ["LA-032", *[b["id"] for b in batches], "LA-063"]
    require(parent["depends_on"] == expected, "LA-031 dependencies")
    require(parent["marked_complete_by_schedule_freeze"] is False, "LA-031 completed by freeze")
    require(parent["registered_future_batch_success"] is False, "future batch success")


def verify_zero_execution(root: Path) -> None:
    results = ROOT / "papers" / "completion" / "law_to_action" / "results" / "generated_code_study"
    if results.is_dir():
        raw = results / "raw.jsonl"
        if raw.is_file() and raw.stat().st_size:
            raise VerifyError("scientific results already present")
    for path in (root / "family_batches.json", root / "prospective_study.json", root / "schedule.json"):
        doc = load_json(path)
        require(doc.get("scientific_cells_executed", 0) == 0, "executed flag in " + path.name)


def verify(study_path: Path, require_unexecuted: bool) -> dict:
    study = load_study(study_path)
    root = HERE
    verify_sources(study, root)
    verify_splits(study, root)
    verify_schedule(study, root)
    verify_batches(study, root)
    verify_oracles(study, root)
    verify_qualification(study, root)
    verify_dependencies(root)
    if require_unexecuted:
        verify_zero_execution(root)
        require(study["scientific_cells_executed"] == 0, "scientific execution claimed")
    return {
        "status": "PASS",
        "schema": "la-generated-study-preparation-verification/v1",
        "families": 30,
        "cases": 60,
        "cells": 900,
        "batches": 30,
        "scientific_cells_executed": 0,
        "readiness_only": True,
        "study_sha256": sha_file(study_path),
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--study", type=Path, required=True)
    parser.add_argument("--require-scientific-cells-unexecuted", action="store_true")
    args = parser.parse_args()
    print(json.dumps(verify(args.study, args.require_scientific_cells_unexecuted), indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
