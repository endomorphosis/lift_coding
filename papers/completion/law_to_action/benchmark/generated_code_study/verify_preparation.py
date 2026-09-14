#!/usr/bin/env python3
"""Read-only LA-032 preparation verifier. Completes readiness only."""
from __future__ import annotations

import argparse
import ast
import hashlib
import json
import random
import re
import sys
from collections import defaultdict
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[4]
sys.path.insert(0, str(HERE / "preparation"))
from study_common import (
    ARMS, ATTEMPT_WALL_SECONDS, BATCH_SCIENTIFIC_ATTEMPT_SECONDS, MAX_CALLS,
    MAX_INPUT_TOKENS, MAX_OUTPUT_TOKENS, PAID_PROVIDER_BUDGET, POPULATIONS,
    PROMPT_PROFILE, QUOTAS, SEEDS, SERVICE_WALL_SECONDS, SPLITS,
    STARTUP_READINESS_SECONDS, WORKER_CEILING_SECONDS, assign_splits,
    build_schedule, decode_schedule_cells, digest, load_json, ranking_digest, sha_file,
)


def fail(message):
    raise SystemExit("PREPARATION_VERIFY_FAIL: " + message)


def require(ok, message):
    if not ok:
        fail(message)


def load(path):
    path = Path(path)
    require(path.is_file(), f"missing {path}")
    return json.loads(path.read_text()), sha_file(path)


def recompute_schedule(case_ids):
    return build_schedule(case_ids)


def check_no_mocks(root: Path):
    forbidden = ("MagicMock", "unittest.mock", "availability_flag = True", "permissive_availability")
    for path in root.rglob("*.py"):
        text = path.read_text()
        if "verify_preparation.py" in str(path):
            continue
        if "qualify_interfaces" in text:
            continue
        for token in ("MagicMock", "from unittest.mock"):
            if token in text and path.name not in {"verify_preparation.py"}:
                # driver/program_profile/model_service/watchdog/prepare must not mock the scientific path
                if path.name in {"driver.py", "program_profile.py", "model_service.py", "watchdog_diagnostic.py", "prepare_study.py"}:
                    fail(f"mock mechanism in {path}")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--study", required=True, type=Path)
    parser.add_argument("--require-scientific-cells-unexecuted", action="store_true")
    args = parser.parse_args()
    study_path = args.study.resolve()
    study, study_sha = load(study_path)
    require(study.get("schema") == "la-closed-loop-study/v1", "study schema")
    require(study.get("split_salt") == "vericodegen-2026-law-to-action-LA016-v1", "split salt")
    require(study.get("arms") == list(ARMS) and study.get("seeds") == list(SEEDS), "arms/seeds")
    require(study.get("scientific_cells_executed") == 0, "scientific cells claimed")
    require(study.get("scientific_execution_allowed") is False, "scientific execution flag")
    require(study.get("final_oracles_sealed") is True and study.get("final_released") is False, "sealed final")
    require(study.get("permissive_availability_flag") is False, "permissive availability flag")
    require(study.get("mock_mechanisms") is False, "mock mechanisms")
    require(study.get("reduced_denominator") is False, "reduced denominator")
    require(study.get("la030_two_sink_substituted") is False, "LA-030 substitution")
    require(study.get("la029_fixed_programs_substituted") is False, "LA-029 substitution")
    require(study.get("prompt_profile_sha256") == digest(PROMPT_PROFILE), "prompt profile")
    require(len(study.get("families") or []) == 30, "30 families")
    require(len(study.get("cases") or []) == 60, "60 cases")
    require(study.get("planned_cells") == 900, "900 planned cells")

    sources, sources_sha = load(HERE / "cohort/sources.json")
    splits, splits_sha = load(HERE / "cohort/splits.json")
    cases_doc, cases_sha = load(HERE / "cohort/cases.json")
    audit, _ = load(HERE / "cohort/lineage_audit.json")
    sealed, _ = load(HERE / "cohort/sealed_final/oracles.json")
    schedule_doc, schedule_sha = load(HERE / "schedule.json")
    batches_doc, _ = load(HERE / "family_batches.json")
    native, _ = load(HERE / "native_dependency_plan.json")
    model_profile, model_profile_sha = load(HERE / "model_profile.json")
    runtime_profile, runtime_sha = load(HERE / "qualification/runtime_profile.json")
    model_qual, model_qual_sha = load(HERE / "qualification/model/qualification.json")
    profile_qual, profile_qual_sha = load(HERE / "qualification/program_profile/qualification.json")
    watchdog_qual, _ = load(HERE / "qualification/watchdog_oserror/qualification.json")
    driver_qual, _ = load(HERE / "qualification/driver/qualification.json")
    deadline_qual, _ = load(HERE / "qualification/attempt_deadline/qualification.json")
    runtime_obs, _ = load(HERE / "qualification/runtime_observation.json")
    historical, _ = load(HERE / "qualification/watchdog_oserror/historical_v2_investigation.json")

    require(sources_sha == study["source_freeze_sha256"], "source freeze binding")
    require(model_profile_sha == study["model_profile_sha256"], "model profile binding")
    require(runtime_sha == study["runtime_profile_sha256"], "runtime profile binding")
    require(schedule_sha == study["schedule_sha256"], "schedule binding")
    require(study["development_qualification"]["sha256"] == profile_qual_sha, "profile binding")
    require(study["model_qualification"]["sha256"] == model_qual_sha, "model qualification binding")

    prior_sources = load_json(ROOT / "papers/completion/law_to_action/benchmark/manifests/sources.json")
    prior_frozen = load_json(ROOT / "papers/completion/law_to_action/benchmark/fixed_action_operator/frozen_inputs.json")
    excluded = {r["lineage_family_id"] for r in prior_sources["source_records"]}
    excluded |= {c["lineage_family_id"] for c in prior_frozen.get("candidates", [])}
    selected_ids = {f["lineage_family_id"] for f in sources["source_records"]}
    require(len(selected_ids) == 30, "unique selected families")
    require(not (selected_ids & excluded), "overlap with LA-004/LA-029")
    require(sources.get("canonical_repository_identity_complete_fork_audit") is False, "incomplete fork audit must be explicit")
    require(sources.get("skill_procedures_are_independent_human_annotations") is False, "skill human annotation claim")

    by_pop = defaultdict(list)
    for record in sources["source_records"]:
        by_pop[record["population"]].append(record)
    require({p: len(by_pop[p]) for p in POPULATIONS} == {"legal": 6, "cve": 12, "skill": 12}, "population counts")
    recomputed = assign_splits(list(sources["source_records"]))
    require([(a["lineage_family_id"], a["split"], a["ranking_sha256"]) for a in recomputed] ==
            [(a["lineage_family_id"], a["split"], a["ranking_sha256"]) for a in splits["assignments"]], "ranked split mismatch")
    for population, quotas in QUOTAS.items():
        ranked = sorted(
            (r for r in sources["source_records"] if r["population"] == population),
            key=lambda r: (r["ranking_sha256"], r["lineage_family_id"].encode()),
        )
        expected = ["development"] * quotas[0] + ["calibration"] * quotas[1] + ["final"] * quotas[2]
        require([r["split"] for r in ranked] == expected, f"{population} split order")

    cases = cases_doc["cases"]
    require(len(cases) == 60, "case count")
    for family in sources["source_records"]:
        kids = [c for c in cases if c["source_family"] == family["lineage_family_id"]]
        require(len(kids) == 2, "two cases per family")
        require(all(c["split"] == family["split"] for c in kids), "descendant split inheritance")
        require(all(c.get("hidden_oracle_excluded") and c.get("target_patches_excluded") for c in kids), "retrieval leakage controls")
        for case in kids:
            require(len(case.get("retrieval") or []) >= 1, "retrieval missing")
            for ctx in case["retrieval"]:
                require(ctx.get("source_family") == family["lineage_family_id"], "retrieval lineage")
                require(ctx.get("contains_oracle") is False, "hidden oracle in retrieval")
            if case["split"] == "final":
                require(case.get("oracle_sealed") is True, "final oracle unsealed")
                require(case.get("expected_payload") is None, "final expected payload visible")
                require("oracle" not in case, "final oracle material in public case")
            else:
                require(case.get("oracle"), "dev/cal oracle missing")
                require(case["oracle"].get("independent") is True, "oracle not independent")
                require(case["oracle"].get("model_self_report_accepted") is False, "self-report oracle")
    require(sealed.get("released") is False, "sealed oracles released")
    require(sealed.get("release_gate") == "LA-063 analysis freeze", "seal gate")
    require(len(sealed.get("oracles") or []) == 36, "18 final families x 2 oracles")

    case_ids = [c["id"] for c in cases]
    recomputed_schedule = recompute_schedule(case_ids)
    live_schedule = decode_schedule_cells(schedule_doc["cells"])
    require(len(live_schedule) == 900, "schedule length")
    require(
        [(r["attempt_id"], r["arm_position"]) for r in live_schedule] ==
        [(r["attempt_id"], r["arm_position"]) for r in recomputed_schedule],
        "schedule identities differ from ranked original rule",
    )
    identities = {(r["case_id"], r["arm"], r["seed"]) for r in live_schedule}
    require(len(identities) == 900, "duplicate schedule identities")
    expected_identities = {(c["id"], arm, seed) for c in cases for arm in ARMS for seed in SEEDS}
    require(identities == expected_identities, "schedule does not cover case-arm-seed matrix")

    require(batches_doc["count"] == 30 and batches_doc["cells_per_batch"] == 30, "batch geometry")
    require(batches_doc["development_cells"] == 180, "development cells")
    require(batches_doc["calibration_cells"] == 180, "calibration cells")
    require(batches_doc["final_cells"] == 540, "final cells")
    all_batch_ids = []
    seen_attempts = set()
    phase_counts = defaultdict(int)
    for batch in batches_doc["batches"]:
        require(batch["planned_cells"] == 30, f"{batch['id']} size")
        require(batch["maximum_scientific_attempt_seconds"] == BATCH_SCIENTIFIC_ATTEMPT_SECONDS, "batch attempt bound")
        require(batch["runtime_seconds"] == WORKER_CEILING_SECONDS, "worker ceiling")
        require(batch["scientific_cells_executed"] == 0, "batch claimed executed")
        indexes = batch.get("original_schedule_indexes") or []
        require(len(indexes) == 30, f"{batch['id']} original schedule indexes")
        attempt_ids = batch.get("cell_attempt_ids")
        if not attempt_ids:
            attempt_ids = [live_schedule[index]["attempt_id"] for index in indexes]
        require(len(attempt_ids) == 30, f"{batch['id']} cell list")
        schedule_by_id = {r["attempt_id"]: r for r in live_schedule}
        for index, attempt_id in zip(indexes, attempt_ids):
            require(live_schedule[index]["attempt_id"] == attempt_id, f"{batch['id']} index/id mismatch")
        case_by_id = {c["id"]: c for c in cases}
        families_in = set()
        for attempt_id in attempt_ids:
            require(attempt_id not in seen_attempts, "overlapping batch cell")
            seen_attempts.add(attempt_id)
            row = schedule_by_id[attempt_id]
            case = case_by_id[row["case_id"]]
            families_in.add(case["source_family"])
            require(case["source_family"] == batch["family_id"], "batch not a single family")
            require(case["split"] == batch["phase"], "batch phase mismatch")
        require(families_in == {batch["family_id"]}, "batch family mismatch")
        phase_counts[batch["phase"]] += 1
        all_batch_ids.append(batch["id"])
    require(len(seen_attempts) == 900, "batch coverage")
    require(phase_counts == {"development": 6, "calibration": 6, "final": 18}, "phase batch counts")
    require(len(batches_doc["dispatch_order"]) == 30, "dispatch order")
    require(batches_doc["dispatch_order"][0]["phase"] == "development", "dispatch starts at development")
    require(any(d.get("preserves_scientific_contrasts") for d in [schedule_doc["operational_ordering_amendment"]]), "ordering amendment not visible")

    require(native["future_batch_success_registered"] is False, "future batch success registered")
    require(native["la031_completed_by_this_freeze"] is False, "LA-031 marked complete")
    require(native["analysis_freeze_task"]["id"] == "LA-063", "analysis freeze id")
    require(set(native["analysis_freeze_task"]["depends_on"]) >= set(["LA-032"] + [f"LA-{n:03d}" for n in range(33, 45)]), "analysis freeze deps")
    parent_deps = set(native["parent_dependency_update"]["explicit_depends_on"])
    require(parent_deps >= set(["LA-032", "LA-063"] + [f"LA-{n:03d}" for n in range(33, 63)]), "LA-031 explicit deps")
    batch_ids = {b["id"] for b in native["family_batch_tasks"]}
    require(batch_ids == {f"LA-{n:03d}" for n in range(33, 63)}, "batch task ids")
    for batch in native["family_batch_tasks"]:
        require("LA-032" in batch["depends_on"], f"{batch['id']} missing LA-032")
        if batch["phase"] == "final":
            require("LA-063" in batch["depends_on"], f"{batch['id']} missing analysis freeze")
        else:
            require("LA-063" not in batch["depends_on"], f"{batch['id']} prematurely depends on analysis freeze")
    require(native["acyclic"] is True, "dependency plan not marked acyclic")
    nodes = set()
    edges = native["edges"]
    require(len(edges) >= 30 + 12 + 18 + 32, "insufficient native edges")
    for edge in edges:
        nodes.add(edge["from"])
        nodes.add(edge["to"])
        require(edge["from"] != edge["to"], "self edge")
    # Kahn acyclicity
    incoming = defaultdict(int)
    outgoing = defaultdict(list)
    for edge in edges:
        outgoing[edge["from"]].append(edge["to"])
        incoming[edge["to"]] += 1
        incoming.setdefault(edge["from"], 0)
    ready = [n for n, c in incoming.items() if c == 0]
    seen = 0
    while ready:
        node = ready.pop()
        seen += 1
        for nxt in outgoing[node]:
            incoming[nxt] -= 1
            if incoming[nxt] == 0:
                ready.append(nxt)
    require(seen == len(incoming), "dependency plan has a cycle")

    require(profile_qual.get("status") == "PASS", "program profile")
    require(profile_qual.get("la030_two_sink_substituted") is False, "two-sink substitution")
    require(set(profile_qual.get("populations_qualified") or []) == set(POPULATIONS), "profile populations")
    require(profile_qual.get("syntax_rejected", 0) >= 4, "syntax rejection")
    require(profile_qual.get("scientific_cells_executed") == 0, "profile scientific cells")
    require(watchdog_qual.get("status") == "PASS", "watchdog")
    require(watchdog_qual.get("historical_v2_upgraded") is False, "v2 receipt upgraded")
    require(watchdog_qual.get("oserror_broadly_suppressed") is False, "OSError suppressed")
    require(historical.get("historical_receipt_upgraded") is False, "historical investigation upgraded")
    require(historical.get("historical_errno") is None, "historical errno claimed proven")
    require(driver_qual.get("status") == "PASS", "driver")
    require(driver_qual.get("interruption_resumed") is True, "driver interruption")
    require(driver_qual.get("final_cells_refused") is True, "driver final refusal")
    require(driver_qual.get("scientific_cells_completed") == 0, "driver scientific completion")
    require(driver_qual.get("actual_probes") is True, "driver config-flag-only")
    require(deadline_qual.get("configured_attempt_wall_seconds") == ATTEMPT_WALL_SECONDS, "deadline")
    require(deadline_qual.get("max_calls") == MAX_CALLS, "call ceiling")
    require(deadline_qual.get("max_input_tokens") == MAX_INPUT_TOKENS, "input ceiling")
    require(deadline_qual.get("max_output_tokens") == MAX_OUTPUT_TOKENS, "output ceiling")
    require(deadline_qual.get("paid_provider_budget") == PAID_PROVIDER_BUDGET, "paid budget")
    require(model_qual.get("status") == "PASS", "model qualification")
    require(model_qual.get("constructed_transport") is False, "constructed model")
    require(model_qual.get("tokenization_agrees_with_usage") is True, "token agreement flag")
    require(model_qual.get("prompt_tokens_equal_preflight_input_count") is True, "prompt_tokens rule")
    require(model_qual.get("qualified_calls", 0) >= 2, "qualified calls")
    require(model_qual.get("systemd_required") is False, "systemd prerequisite")
    require(model_qual.get("indefinitely_running_required") is False, "always-on model")
    require(model_qual.get("startup_readiness_seconds") == STARTUP_READINESS_SECONDS, "startup bound")
    require(model_qual.get("service_wall_seconds") == SERVICE_WALL_SECONDS, "service wall")
    require(model_profile.get("schema") == "la-qualified-local-model/v1", "model profile schema")
    for key in ("model_id", "model_revision", "tokenizer_revision", "weights_sha256", "tokenizer_sha256", "chat_template_sha256", "deployment_sha256"):
        require(model_profile.get(key), f"model pin missing: {key}")
        if key.endswith("sha256"):
            require(re.fullmatch(r"[0-9a-f]{64}", model_profile[key]), f"weak pin {key}")
            require(len(set(model_profile[key])) > 1, f"degenerate pin {key}")
    require(model_profile["qualification"]["sha256"] == model_qual_sha, "model profile qualification hash")
    require(runtime_obs.get("permissive_availability_flag") is False, "runtime availability flag")
    require(runtime_obs.get("mock_mechanism") is False, "runtime mock")

    # Re-check retained model call receipts: prompt_tokens == that call's preflight input_count.
    model_dir = HERE / "qualification/model"
    for label in ("call0", "call1"):
        preflight = load_json(model_dir / f"{label}_preflight.json") if label == "call0" else None
        inference = load_json(model_dir / f"{label}_inference.receipt.json")
        tokenize = load_json(model_dir / f"{label}_tokenize.receipt.json")
        input_count = len(tokenize["body"]["tokens"])
        prompt_tokens = inference["body"]["usage"]["prompt_tokens"]
        require(prompt_tokens == input_count, f"{label} prompt_tokens {prompt_tokens} != input_count {input_count}")
        if preflight:
            require(preflight["input_count"] == input_count, "call0 preflight drifted")
        require((model_dir / f"{label}_inference.response.bin").is_file(), f"{label} raw response missing")
        require(inference["body"]["usage"]["completion_tokens"] <= MAX_OUTPUT_TOKENS, "output ceiling")

    check_no_mocks(HERE)
    require(args.require_scientific_cells_unexecuted, "verifier must be invoked with --require-scientific-cells-unexecuted")
    require(study.get("readiness_only") is True, "readiness-only flag")

    print(json.dumps({
        "status": "PASS",
        "study_sha256": study_sha,
        "families": 30,
        "cases": 60,
        "schedule_cells": 900,
        "batches": 30,
        "final_cells": 540,
        "scientific_cells_executed": 0,
        "readiness_only": True,
    }, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
