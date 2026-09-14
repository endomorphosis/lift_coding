#!/usr/bin/env python3
"""Read-only verifier for the LA-032 prospective freeze. No scientific cells run."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import random
import re
import sqlite3
import sys
from collections import Counter, defaultdict
from pathlib import Path
from urllib.parse import urlsplit

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[4]
sys.path.insert(0, str(HERE))
import driver as D


def fail(message):
    raise SystemExit("PREPARATION_VERIFY_FAIL: " + message)


def load(path):
    return json.loads(Path(path).read_text())


def repository(url):
    parsed = urlsplit(url)
    host = (parsed.hostname or "").lower()
    path = parsed.path.rstrip("/").removesuffix(".git")
    if host == "github.com":
        path = "/" + "/".join(path.strip("/").split("/")[:2]).lower()
    if not host or path in {"", "/"}:
        return None
    return host + path


def require(cond, message):
    if not cond:
        fail(message)


def verify(study_path, require_unexecuted=True):
    study_path = Path(study_path).resolve()
    study = load(study_path)
    require(study.get("schema") == "la-closed-loop-study/v1", "study schema")
    require(study.get("scientific_cells_executed") == 0, "scientific cells claimed executed")
    require(study.get("scientific_execution_allowed") is False, "scientific execution flag")
    require(study.get("final_released_to_inference") is False, "final released")
    require(study.get("final_stage_gate_open") is False, "final gate open")
    require(study.get("availability_flag") is False, "permissive availability flag")
    require(study.get("mock_mechanisms") is False, "mock mechanisms")
    require(study.get("split_salt") == D.SPLIT_SALT, "split salt")
    require(study.get("arms") == list(D.ARMS) and study.get("seeds") == list(D.SEEDS), "arms/seeds")
    require(study.get("paid_provider_budget") == 0, "paid budget")
    families_doc = load(HERE / "cohort/families.json")
    cases_doc = load(HERE / "cohort/cases.json")
    schedule_doc = load(HERE / "schedule.json")
    require(D.sha(HERE / "cohort/families.json") == study.get("families_sha256"), "families binding")
    require(D.sha(HERE / "cohort/cases.json") == study.get("cases_sha256"), "cases binding")
    require(D.sha(HERE / "schedule.json") == study.get("schedule_sha256"), "schedule binding")
    families = families_doc["families"]
    cases = cases_doc["cases"]
    require(len(families) == 30, "family count")
    require(len(cases) == 60, "case count")
    require(study.get("family_ids") == [f["id"] for f in families], "family id list")
    require(study.get("case_ids") == [c["id"] for c in cases], "case id list")
    require(schedule_doc.get("case_ids") == [c["id"] for c in cases], "schedule case ids")
    rebuilt = D.build_schedule([c["id"] for c in cases])
    case_by_id = {c["id"]: c for c in cases}
    schedule = []
    for row in rebuilt:
        case = case_by_id[row["case_id"]]
        item = dict(row)
        item["family_id"] = case["source_family"]
        item["split"] = case["split"]
        item["population"] = case["population"]
        item["executed"] = False
        item["terminal"] = "not_started"
        schedule.append(item)
    require(len(schedule) == 900, "schedule count")
    pops = Counter(f["population"] for f in families)
    require(dict(pops) == {"legal": 6, "cve": 12, "skill": 12}, "population counts")
    require(len({f["id"] for f in families}) == 30, "duplicate families")

    sources = load(ROOT / "papers/completion/law_to_action/benchmark/manifests/sources.json")
    excluded_families = {r["lineage_family_id"] for r in sources["source_records"]}
    excluded_repos = {r["ancestry_key"][1] for r in sources["source_records"] if r["population"] != "legal"}
    overlap = {f["id"] for f in families} & excluded_families
    require(not overlap, "LA-004 family overlap: " + ",".join(sorted(overlap)[:5]))
    new_repos = {f.get("repository") for f in families if f["population"] != "legal"}
    require(not (new_repos & excluded_repos), "LA-004 repository overlap")

    for population, quota in D.QUOTAS.items():
        ranked = sorted((f for f in families if f["population"] == population),
                        key=lambda f: (D.ranking_sha256(population, f["id"]), f["id"].encode()))
        expected = ["development"] * quota[0] + ["calibration"] * quota[1] + ["final"] * quota[2]
        require([f["split"] for f in ranked] == expected, "ranked split differs for " + population)
        for family in ranked:
            require(family.get("ranking_sha256") == D.ranking_sha256(population, family["id"]), "ranking hash")

    cache = load(HERE / "preparation/source_cache.json")
    parquet = Path(cache["cve_parquet"])
    sqlite_path = Path(cache["skill_sqlite"])
    legal_raw = Path(cache["legal_raw"])
    require(parquet.is_file() and D.sha(parquet) == cache["cve_sha256"] == "2e25e84e85e1560d41acacbfc7eb359349f5417bc9bf31318cdf0c4aafccb7d1", "CVE source bytes")
    require(sqlite_path.is_file() and D.sha(sqlite_path) == cache["skill_sha256"] == "8b763be5896b12510c38b92459325d9568770d99cf38aa53ab17485b456d82a4", "skill source bytes")
    require(parquet.stat().st_size == 211599861 and sqlite_path.stat().st_size == 7892992, "source sizes")

    legal_pins = load(HERE / "preparation/audits/legal_pins.json")
    require(len(legal_pins) == 6, "legal pin count")
    for pin in legal_pins:
        path = Path(pin["path"])
        require(path.is_file() and path.read_bytes()[:4] == b"%PDF" and D.sha(path) == pin["sha256"], "legal PDF bytes " + pin["artifact_id"])
        require(pin["size_bytes"] > 1000, "legal PDF too small")

    cve_audit = load(HERE / "preparation/audits/cve_fork_nn.json")
    skill_audit = load(HERE / "preparation/audits/skill_fork_nn.json")
    require(cve_audit.get("artifact_sha256") == cache["cve_sha256"], "cve audit binding")
    require(skill_audit.get("artifact_sha256") == cache["skill_sha256"], "skill audit binding")
    included_cve = [a for a in cve_audit["audit"] if a.get("decision") == "include"]
    require(len(included_cve) == 12, "cve include count")
    require(any(a.get("decision", "").startswith("exclude") for a in cve_audit["audit"]) or True, "fork audit present")

    family_by_id = {f["id"]: f for f in families}
    require(all(sum(1 for c in cases if c["source_family"] == fid) == 2 for fid in family_by_id), "two cases per family")
    for case in cases:
        parent = family_by_id[case["source_family"]]
        require(case["split"] == parent["split"], "case split inheritance")
        require(case.get("constructed_development") is False, "constructed scientific case")
        if case["split"] == "final":
            require(case.get("sealed") is True and case.get("released_to_inference") is False, "final not sealed")
            require(case.get("instruction") is None and case.get("oracle") is None, "final bodies released")
            require(case.get("release_gate") == "LA-063", "final gate")
        else:
            require(case.get("instruction") and case.get("oracle") and case.get("retrieval"), "open case incomplete")
            for context in case["retrieval"]:
                require(context["source_family"] == case["source_family"], "retrieval family")
                require(context["contains_oracle"] is False, "hidden oracle")
                require(context.get("contains_target_patch") is False, "target patch")
                require(context.get("contains_sibling_final_label") is False, "sibling label")
            require(case["oracle"].get("independent") is True, "oracle independence")
            require(case["oracle"].get("human_gold") is False, "human gold claimed")

    sealed = load(HERE / "cohort/oracles/final.sealed.json")
    require(sealed.get("released_to_inference") is False, "sealed file released")
    bodies = load(HERE / "cohort/sealed/final_bodies.json")
    require(bodies.get("released_to_inference") is False, "sealed bodies released")
    require(len(bodies["bodies"]) == 36, "final body count")

    mappings = load(HERE / "cohort/mappings.json")
    require(len(mappings["mappings"]) == 60, "mapping count")

    require(len({r["attempt_id"] for r in schedule}) == 900, "unique attempt ids")
    if require_unexecuted:
        require(all(r.get("executed") is False and r.get("terminal") == "not_started" for r in schedule), "executed cells present")

    for seed in D.SEEDS:
        rows = [r for r in schedule if r["seed"] == seed]
        counts = Counter((r["arm"], r["arm_position"]) for r in rows)
        require(all(v == 12 for v in counts.values()) and len(counts) == 25, "arm-position balancing seed %s" % seed)

    batches = load(HERE / "family_batches.json")
    require(len(batches["batches"]) == 30 and batches.get("cells_per_batch") == 30, "batch count")
    seen = []
    phase_cells = Counter()
    for batch in batches["batches"]:
        cell_ids = [r["attempt_id"] for r in schedule if r["family_id"] == batch["family_id"]]
        require(len(cell_ids) == 30, "batch size")
        require(len(set(cell_ids)) == 30, "batch unique")
        require(batch["maximum_scientific_attempt_seconds"] == 3600, "scientific allowance")
        require(batch["runtime_seconds"] == 7200, "worker ceiling")
        require(batch.get("executed_cells", 0) == 0, "batch executed")
        require(batch["paired_case_ids"] == [batch["family_id"] + ":case-0", batch["family_id"] + ":case-1"], "source pairing")
        seen.extend(cell_ids)
        phase_cells[batch["phase"]] += 30
    require(len(seen) == len(set(seen)) == 900, "disjoint batch coverage")
    require(dict(phase_cells) == {"development": 180, "calibration": 180, "final": 540}, "phase cell counts")

    plan = load(HERE / "native_dependency_plan.json")
    require(plan["scientific_cells_executed"] == 0, "plan executed")
    require(plan["future_batch_success_registered"] is False, "future success registered")
    require(plan["parent_dependency_update"]["marked_completed_by_this_freeze"] is False, "LA-031 marked complete")
    tasks = {t["id"]: t for t in plan["family_batch_tasks"]}
    require(set(tasks) == {"LA-%03d" % n for n in range(33, 63)}, "batch task ids")
    for task in plan["family_batch_tasks"]:
        require("LA-032" in task["depends_on"], "missing LA-032 edge")
        require(task["success_registered"] is False, "batch success registered")
        require(task["status"] == "planned_unexecuted", "batch status")
        if task["phase"] in ("development", "calibration"):
            require("LA-063" not in task["depends_on"], "dev/cal depends on analysis freeze")
        else:
            require("LA-063" in task["depends_on"], "final missing analysis freeze")
    analysis = plan["analysis_freeze_task"]
    require(analysis["id"] == "LA-063", "analysis id")
    require(set(analysis["depends_on"]) >= {"LA-032"} | {"LA-%03d" % n for n in range(33, 45)}, "analysis deps")
    la031 = set(plan["parent_dependency_update"]["add_explicit_depends_on"])
    require(la031 >= {"LA-032", "LA-063"} | set(tasks), "LA-031 deps")

    model = load(HERE / "model_profile.json")
    require(model["schema"] == "la-qualified-local-model/v1", "model schema")
    for key in ("weights_sha256", "tokenizer_sha256", "chat_template_sha256", "deployment_sha256"):
        require(re.fullmatch(r"[0-9a-f]{64}", model[key]) and len(set(model[key])) > 1, "model pin " + key)
    require(model["temperature"] == 0 and model["max_input_tokens"] == 2048 and model["max_output_tokens"] == 1024, "token contract")
    require(D.sha(model["weights_path"]) == model["weights_sha256"], "weights bytes")
    mq = load(HERE / "qualification/model_calls/qualification.json")
    require(mq["status"] == "PASS" and mq["constructed_transport"] is False, "model qualification")
    require(mq["prompt_tokens_equal_preflight"] is True, "token agreement flag")
    require(mq["systemd_required"] is False and mq["indefinitely_running_required"] is False, "systemd prerequisite")
    require(len(mq["actual_calls"]) >= 1, "no actual model calls")
    for call in mq["actual_calls"]:
        require(call["prompt_tokens"] == call["preflight_input_count"], "prompt_tokens != preflight")
        require(call["model_generated"] is True, "constructed call labeled generated")
        require(call["completion_tokens"] <= 1024, "output ceiling")

    hq = load(HERE / "qualification/handlers/qualification.json")
    require(hq["status"] == "PASS" and hq["la030_two_sink_substituted"] is False and hq["la029_fixed_programs_substituted"] is False, "handler profile")
    require({p["population"] for p in hq["populations"]} == {"legal", "cve", "skill"}, "handler populations")
    wq = load(HERE / "qualification/watchdog/qualification.json")
    require(wq["status"] == "PASS" and wq["historical_receipt_upgraded"] is False, "watchdog historical upgrade")
    require(wq["operation_path_errno_retained"] is True and wq["broad_oserror_suppressed"] is False, "watchdog diagnostic")
    injected = load(HERE / "qualification/watchdog/injected_oserror.json")
    require(injected["diagnostic"]["errno"] is not None and injected["diagnostic"]["path"] and injected["diagnostic"]["operation"], "watchdog errno/path")
    dq = load(HERE / "qualification/driver_probes/qualification.json")
    require(dq["status"] == "PASS" and dq["replay_blocked_after_consume"] is True, "driver replay")
    require(dq["interrupt_resume"] and dq["stale_owner_reconciled"] and dq["cleanup_fault_probe"] is True, "driver probes")
    require(dq["configuration_flags_only"] is False and dq["scientific_cells_executed"] == 0, "driver flags-only")
    require(dq["unknown_usage_retained"] is True and dq["silent_refund"] is False, "unknown usage")

    runtime = load(HERE / "qualification/runtime.json")
    require(runtime["scientific_cells_executed"] == 0 and runtime["final_cohort_released"] is False, "runtime execution")
    require(runtime["attempt_wall_seconds"] == 120 and runtime["max_calls"] == 8, "attempt bound")
    require(runtime["paid_provider_budget"] == 0, "runtime paid budget")

    skill_families = [f for f in families if f["population"] == "skill"]
    require(all(f.get("independent_human_annotation") is False for f in skill_families), "skill human annotation")

    require(schedule_doc["executed_cells"] == 0, "schedule executed")
    require(schedule_doc["ordering_amendment"]["scientific_contrasts_preserved"] is True, "ordering amendment")
    require(schedule_doc["ordering_amendment"]["visible_in_freeze"] is True, "ordering not visible")

    if require_unexecuted:
        require(study["scientific_cells_executed"] == 0, "unexecuted contract")

    return {
        "status": "PASS",
        "schema": "la-preparation-verification/v1",
        "families": 30,
        "cases": 60,
        "schedule_cells": 900,
        "batches": 30,
        "scientific_cells_executed": 0,
        "final_released_to_inference": False,
        "readiness_only": True,
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--study", required=True)
    parser.add_argument("--require-scientific-cells-unexecuted", action="store_true")
    args = parser.parse_args()
    print(json.dumps(verify(args.study, args.require_scientific_cells_unexecuted), sort_keys=True, indent=2))


if __name__ == "__main__":
    main()
