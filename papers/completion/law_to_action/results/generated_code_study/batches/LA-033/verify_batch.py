#!/usr/bin/python3.12
"""Read-only verification of one frozen generated-code family-batch execution."""
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

import sys

HERE = Path(__file__).resolve().parent
ROOT = HERE
while not (ROOT / "papers/completion/law_to_action/benchmark/generated_code_study/driver.py").is_file():
    if ROOT.parent == ROOT:
        raise SystemExit("family-batch verifier failed: repository root not found")
    ROOT = ROOT.parent
STUDY = ROOT / "papers/completion/law_to_action/benchmark/generated_code_study"
sys.path.insert(0, str(STUDY))
from driver import (  # noqa: E402
    ARMS,
    ATTEMPT_WALL,
    BATCH_ATTEMPT_SECONDS,
    MAX_CALLS,
    MAX_INPUT,
    MAX_OUTPUT,
    PAID_BUDGET,
    PROFILE_ID,
    PROMPT_PROFILE,
    SEEDS,
    WEIGHTS_FILE,
    build_schedule,
    digest,
    file_sha,
    load_json,
)


def fail(message: str) -> None:
    raise SystemExit("family-batch verifier failed: " + message)


def require(condition: bool, message: str) -> None:
    if not condition:
        fail(message)


def load_freeze(path: Path) -> dict:
    study = load_json(path)
    require(study.get("schema") == "la-closed-loop-study/v1", "unexpected study schema")
    require(study.get("mock") is False, "mock freeze")
    require(study.get("permissive_availability_flag") is False, "permissive availability flag")
    return study


def batch_identities(study_dir: Path, batch_id: str) -> tuple[dict, list[dict]]:
    batches = load_json(study_dir / "family_batches.json")
    schedule_doc = load_json(study_dir / "schedule.json")
    cases = {row["id"]: row for row in load_json(study_dir / "cohort/cases.json")["cases"]}
    batch = next((row for row in batches["batches"] if row["id"] == batch_id), None)
    require(batch is not None, "unknown batch task")
    expected = build_schedule(schedule_doc["case_ids"])
    family_cases = set(batch["paired_cases"])
    cells = []
    for row in expected:
        if row["case_id"] not in family_cases:
            continue
        info = cases[row["case_id"]]
        item = dict(row)
        item["family_id"] = info["source_family"]
        item["population"] = info["population"]
        item["split"] = info["split"]
        item["batch_id"] = batch_id
        cells.append(item)
    require(len(cells) == 30, "batch is not 30 original identities")
    require(len({row["attempt_id"] for row in cells}) == 30, "duplicate identities")
    require(all(row["arm"] in ARMS and row["seed"] in SEEDS for row in cells), "arm/seed identity")
    require(all(row["family_id"] == batch["family_binding"] for row in cells), "family binding")
    return batch, cells


def verify_record(root: Path, cell: dict, study: dict, model_profile: dict, batch: dict) -> dict:
    index = load_json(root / "index.json")
    by_id = {row["attempt_id"]: row for row in index["records"]}
    require(cell["attempt_id"] in by_id, "missing terminal index record for " + cell["attempt_id"])
    summary = by_id[cell["attempt_id"]]
    cell_dir = root / summary["cell_dir"]
    require(cell_dir.is_dir(), "cell directory missing")
    result = load_json(cell_dir / "result.json")
    identity = load_json(cell_dir / "identity.json")
    source = load_json(cell_dir / "source_binding.json")
    require(result.get("schema") == "la-closed-loop-attempt/v1", "attempt schema")
    require(result.get("scientific_benchmark") is True, "scientific_benchmark not bound")
    require(result.get("constructed_transport") is False, "constructed transport substituted")
    require(result.get("fixed_program_substituted") is False, "fixed program substituted")
    require(result.get("silent_replay") is False, "silent replay")
    require(result.get("paid_budget") == PAID_BUDGET, "paid budget")
    require(result.get("unknown_costs") is False, "unknown costs")
    require(result["attempt_id"] == cell["attempt_id"], "attempt_id mismatch")
    require(result["case_id"] == cell["case_id"], "case_id mismatch")
    require(result["arm"] == cell["arm"] and result["seed"] == cell["seed"], "arm/seed mismatch")
    require(result["family_id"] == batch["family_binding"], "family mismatch")
    require(result["batch_id"] == batch["id"], "batch_id mismatch")
    require(result["split"] == batch["phase"], "split/phase mismatch")
    require(identity["attempt_id"] == cell["attempt_id"], "identity")
    require(source["source_family"] == batch["family_binding"], "source family")
    require(source["case_id"] == cell["case_id"], "source case")
    require(summary.get("freeze_sha256") == study["freeze_sha256"], "freeze binding")
    require(summary.get("model_profile_sha256") == study["model_profile_sha256"], "model binding")
    require(summary.get("prompt_profile_sha256") == digest(PROMPT_PROFILE), "prompt binding")
    require(summary.get("execution_profile") == PROFILE_ID, "runtime profile")
    require(summary.get("weights_sha256") == model_profile["weights_sha256"], "weights pin")
    require(summary.get("model_revision") == model_profile["model_revision"], "model revision")
    require(summary.get("admitted") is True, "unadmitted evidence")
    require(summary.get("unrun") is False and summary.get("missing") is False, "unrun/missing evidence")
    require(summary.get("consumed") is True, "reservation not consumed")
    iterations = result.get("iterations") or []
    require(1 <= len(iterations) <= MAX_CALLS, "iteration count")
    require(result["terminal"] in {"useful_work", "candidate_failed", "transport_or_format_failure", "budget_exhausted", "budget_exhausted_before_full_execution_allowance"}, "unknown terminal")
    model_calls = 0
    for row in iterations:
        idx = row["iteration"]
        directory = cell_dir / f"iteration-{idx:02d}"
        require(directory.is_dir(), "iteration directory missing")
        require((directory / "messages.json").is_file(), "messages missing")
        require((directory / "iteration_result.json").is_file(), "iteration result missing")
        generated = (directory / "generated_candidate.txt").is_file() or (directory / "candidate.py").is_file()
        require(generated, "generated candidate missing")
        if row.get("model_calls"):
            model_calls += int(row["model_calls"])
            require((directory / "inference_reserved.json").is_file(), "model reservation missing")
            require((directory / "preflight.json").is_file(), "preflight missing")
            require((directory / "raw_response.json").is_file(), "raw response missing")
            require((directory / "transport_result.json").is_file(), "transport result missing")
            preflight = load_json(directory / "preflight.json")
            transport = load_json(directory / "transport_result.json")
            require(type(row.get("prompt_tokens")) is int and type(row.get("completion_tokens")) is int, "token costs missing")
            require(row["prompt_tokens"] == preflight["input_count"], "prompt_tokens != preflight input_count")
            require(row["prompt_tokens"] == transport["preflight_input_count"], "transport preflight mismatch")
            require(row["prompt_tokens"] <= MAX_INPUT, "input ceiling")
            require(row["completion_tokens"] <= MAX_OUTPUT, "output ceiling")
            require(transport.get("model_generated") is True, "not model-generated")
            require(transport.get("origin") == "qualified-local-model", "origin")
            require(re.fullmatch(r"[0-9a-f]{64}", row.get("raw_sha256") or ""), "raw sha")
            require(file_sha(directory / "raw_response.json") == row["raw_sha256"], "raw bytes")
            require(row.get("fixed_program_substituted") is not True, "iteration substituted a fixed program")
        require(row.get("effect_status") in {"measured", "not_executed", "unknown_after_execution_reservation"}, "effect status")
        if row.get("effect_status") == "measured":
            require((directory / "result.json").is_file(), "effect result missing")
            observed = load_json(directory / "result.json")
            require("useful_work" in observed and "forbidden_effect" in observed, "effect fields")
            require((directory / "observation.json").is_file() or (directory / "sandbox").exists(), "effect observation missing")
        if result["terminal"] != "useful_work":
            require(result.get("legitimate_candidate_failure_retained") is True or result["terminal"] != "candidate_failed", "candidate failure dropped")
    require(result["model_calls"] == model_calls, "model-call accounting")
    require(result.get("wall_seconds", 0) <= ATTEMPT_WALL or result.get("overrun") is True, "attempt wall unaccounted")
    return summary


def verify_control(root: Path, cells: list[dict], freeze_sha256: str) -> None:
    control = load_json(root / "control.json")
    require(control.get("schema") == "la032-durable-schedule/v1", "control schema")
    require(control.get("freeze_sha256") == freeze_sha256, "control freeze")
    stored = control.get("cells") or {}
    calls = control.get("model_calls") or {}
    require(len(stored) == 30, "control cell count")
    for cell in cells:
        row = stored.get(cell["attempt_id"])
        require(row is not None, "control missing " + cell["attempt_id"])
        require(row.get("consumed") == 1, "cell not consumed")
        require(row.get("scientific") == 1, "cell not scientific")
        require(row.get("state") in {"completed", "failed_consumed"}, "cell not terminal")
        require(row.get("batch_id") == cell["batch_id"], "control batch")
        require(row.get("arm") == cell["arm"] and int(row.get("seed")) == int(cell["seed"]), "control identity")
    for call in calls.values():
        require(call.get("state") in {"completed", "failed_consumed"}, "model call not consumed")
        if call.get("error") is None:
            require(type(call.get("prompt_tokens")) is int and call["prompt_tokens"] == call.get("input_count"), "control prompt_tokens")
            require(type(call.get("completion_tokens")) is int and call["completion_tokens"] <= MAX_OUTPUT, "control completion")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--freeze", type=Path, required=True)
    parser.add_argument("--batch-task", required=True)
    parser.add_argument("--require-complete", action="store_true")
    parser.add_argument("--results", type=Path)
    args = parser.parse_args()
    freeze_path = args.freeze
    study_dir = freeze_path.parent
    study = load_freeze(freeze_path)
    batch, cells = batch_identities(study_dir, args.batch_task)
    require(batch["planned_cells"] == 30, "planned cells")
    require(batch["maximum_scientific_attempt_seconds"] == BATCH_ATTEMPT_SECONDS, "scientific attempt bound")
    results = args.results or (ROOT / "papers/completion/law_to_action/results/generated_code_study/batches" / args.batch_task)
    require(results.is_dir(), "batch results directory missing")
    binding = load_json(results / "freeze_binding.json")
    complete = load_json(results / "batch.json")
    model_profile = load_json(study_dir / "model_profile.json")
    require(binding["batch_id"] == args.batch_task, "binding batch")
    require(binding["freeze_sha256"] == study["freeze_sha256"], "binding freeze")
    require(binding["attempt_ids"] == [row["attempt_id"] for row in cells], "binding identities")
    require(digest(model_profile) == study["model_profile_sha256"], "model profile freeze")
    require(file_sha(study_dir / "qualification/model" / WEIGHTS_FILE) == model_profile["weights_sha256"], "weight bytes")
    records_path = results / "terminal_records.jsonl"
    require(records_path.is_file(), "terminal_records.jsonl missing")
    lines = [json.loads(line) for line in records_path.read_text().splitlines() if line.strip()]
    require(len(lines) == 30, "terminal record count")
    require([row["attempt_id"] for row in lines] == [row["attempt_id"] for row in cells], "terminal identity order")
    summaries = []
    for cell, line in zip(cells, lines):
        summary = verify_record(results, cell, study, model_profile, batch)
        require(line["attempt_id"] == summary["attempt_id"], "jsonl/index mismatch")
        require(line.get("scientific_benchmark") is True, "jsonl not scientific")
        require(line.get("constructed_transport") is False, "jsonl constructed")
        require(line.get("model_generated") is True, "jsonl not generated")
        require(line.get("fixed_program_substituted") is False, "jsonl substitution")
        summaries.append(summary)
    verify_control(results, cells, study["freeze_sha256"])
    missing = [row["attempt_id"] for row in cells if not any(s["attempt_id"] == row["attempt_id"] and s.get("admitted") for s in summaries)]
    unrun = [row["attempt_id"] for row in summaries if row.get("unrun")]
    unadmitted = [row["attempt_id"] for row in summaries if not row.get("admitted")]
    if args.require_complete:
        require(complete.get("status") == "COMPLETE", "batch not marked complete")
        require(complete.get("terminal_records") == 30, "complete count")
        require(complete.get("scientific_cells_completed") == 30, "scientific completed count")
        require(complete.get("missing") == [] and complete.get("unrun") == [] and complete.get("unadmitted") == [], "gaps retained as complete")
        require(not missing and not unrun and not unadmitted, "missing/unrun/unadmitted evidence")
        require(complete.get("legitimate_candidate_failures_retained") is True, "failures dropped")
        require(complete.get("constructed_transport") is False, "complete constructed")
        require(complete.get("fixed_program_substituted") is False, "complete substitution")
        require(complete.get("unknown_costs") is False, "complete unknown costs")
        require(complete.get("prompt_tokens_equal_preflight") is True, "complete token agreement")
    failures = sum(1 for row in summaries if not row.get("useful_work"))
    print(
        json.dumps(
            {
                "status": "PASS",
                "batch_id": args.batch_task,
                "terminal_records": len(summaries),
                "scientific_cells_completed": len(summaries),
                "useful_work": sum(1 for row in summaries if row.get("useful_work")),
                "candidate_failures_retained": failures,
                "missing": missing,
                "unrun": unrun,
                "unadmitted": unadmitted,
                "require_complete": bool(args.require_complete),
            },
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
