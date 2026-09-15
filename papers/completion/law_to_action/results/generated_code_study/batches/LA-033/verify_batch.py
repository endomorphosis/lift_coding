#!/usr/bin/python3.12
"""Read-only verifier for one frozen generated-code family batch.

Fail closed: every original identity must have a source/model/runtime-bound,
protocol-accounted terminal record with real generated candidates, effects and
costs. Missing, unrun or unadmitted evidence keeps the batch incomplete.
Legitimate measured candidate failure is an admitted outcome.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
if (HERE / "driver.py").is_file():
    ROOT = HERE.parents[4]
    sys.path.insert(0, str(HERE))
else:
    ROOT = HERE.parents[6]
    sys.path.insert(0, str(ROOT / "papers/completion/law_to_action/benchmark/generated_code_study"))
from driver import (  # noqa: E402
    ARMS,
    MAX_INPUT,
    MAX_OUTPUT,
    PAID_BUDGET,
    PROFILE_ID,
    SEEDS,
    build_schedule,
    digest,
    file_sha,
    load_json,
)

CANNED_PROGRAM = "def run(payload):\n    emit_allowed(payload)\n"
RESULTS_ROOT = ROOT / "papers/completion/law_to_action/results/generated_code_study/batches"
SHA_RE = re.compile(r"^[0-9a-f]{64}$")
TERMINALS = {
    "useful_work",
    "candidate_failed",
    "budget_exhausted",
    "budget_exhausted_before_full_execution_allowance",
    "transport_or_format_failure",
}


def fail(message: str) -> None:
    raise SystemExit("LA family-batch verifier failed: " + message)


def require(condition: bool, message: str) -> None:
    if not condition:
        fail(message)


def cell_dir_for(results: Path, attempt_id: str) -> Path:
    direct = results / "cells" / attempt_id
    if direct.is_dir():
        return direct
    index = results / "manifest.json"
    if index.is_file():
        manifest = load_json(index)
        for row in manifest.get("identities") or []:
            if row.get("attempt_id") == attempt_id and row.get("cell_dir"):
                path = results / row["cell_dir"]
                if path.is_dir():
                    return path
    fail("missing cell directory for " + attempt_id)


def load_batch(study_dir: Path, batch_id: str) -> dict:
    batches = load_json(study_dir / "family_batches.json")
    match = next((row for row in batches["batches"] if row["id"] == batch_id), None)
    require(match is not None, "unknown batch-task " + batch_id)
    return match


def planned_identities(study_dir: Path, batch: dict) -> list[dict]:
    schedule_doc = load_json(study_dir / "schedule.json")
    cases = load_json(study_dir / "cohort/cases.json")["cases"]
    case_map = {row["id"]: row for row in cases}
    family_cases = [batch["family_binding"] + ":case-0", batch["family_binding"] + ":case-1"]
    require(batch["paired_cases"] == family_cases, "paired cases drifted from family binding")
    expected = build_schedule(schedule_doc["case_ids"])
    cells = [row for row in expected if row["case_id"] in family_cases]
    require(len(cells) == 30, "batch is not 30 original identities")
    require(len({row["attempt_id"] for row in cells}) == 30, "duplicate identities")
    require(set(row["arm"] for row in cells) == set(ARMS), "arms missing")
    require(set(row["seed"] for row in cells) == set(SEEDS), "seeds missing")
    for row in cells:
        info = case_map[row["case_id"]]
        row["family_id"] = info["source_family"]
        row["population"] = info["population"]
        row["split"] = info["split"]
        row["source_id"] = info["source_id"]
        require(info["source_family"] == batch["family_binding"], "case/family mismatch")
        require(info["split"] == batch["phase"], "case split drifted from batch phase")
    if batch.get("attempt_ids"):
        require(batch["attempt_ids"] == [row["attempt_id"] for row in cells], "batch identities")
    return cells


def require_sha(value: object, message: str) -> str:
    require(isinstance(value, str) and SHA_RE.fullmatch(value), message)
    return value


def iteration_dirs(cell: Path) -> list[Path]:
    rows = sorted(path for path in cell.iterdir() if path.is_dir() and path.name.startswith("iteration-"))
    require(bool(rows), "no iteration evidence in " + cell.name)
    for index, path in enumerate(rows):
        require(path.name == f"iteration-{index:02d}", "iteration directories are not contiguous")
    return rows


def check_no_substitution(iteration: Path) -> None:
    candidate = iteration / "candidate.py"
    require(candidate.is_file() and candidate.stat().st_size > 0, "missing generated candidate")
    program = candidate.read_text()
    raw_path = iteration / "raw_response.json"
    require(raw_path.is_file() and raw_path.stat().st_size > 0, "missing raw model response")
    if program != CANNED_PROGRAM:
        return
    try:
        body = json.loads(raw_path.read_text())
        text = body["choices"][0]["message"]["content"]
        parsed = json.loads(text)
        produced = parsed.get("program")
    except Exception:
        produced = None
    require(produced == CANNED_PROGRAM, "canned emit_allowed program substituted for a non-matching model response")


def check_iteration(iteration: Path, attempt_id: str, call_index: int) -> dict:
    check_no_substitution(iteration)
    require((iteration / "messages.json").is_file(), "missing messages")
    reserved = load_json(iteration / "inference_reserved.json")
    require(reserved.get("consumed_before_request") is True, "model call was not reserved before request")
    preflight = load_json(iteration / "preflight.json")
    transport = load_json(iteration / "transport_result.json")
    iteration_result = load_json(iteration / "iteration_result.json")
    candidate_result = load_json(iteration / "result.json")
    input_count = preflight.get("input_count")
    require(type(input_count) is int and 0 < input_count <= MAX_INPUT, "preflight input_count")
    require(transport.get("model_generated") is True, "constructed or model-free transport")
    require(transport.get("origin") == "qualified-local-model", "transport origin")
    require(type(transport.get("prompt_tokens")) is int and transport["prompt_tokens"] == input_count, "prompt_tokens != preflight input_count")
    require(type(transport.get("completion_tokens")) is int and 0 <= transport["completion_tokens"] <= MAX_OUTPUT, "output ceiling")
    require(SHA_RE.fullmatch(str(transport.get("raw_sha256") or "")), "raw response digest")
    require(file_sha(iteration / "raw_response.json") == transport["raw_sha256"], "raw bytes digest mismatch")
    require(iteration_result.get("model_generated") is True, "iteration not model-generated")
    require(candidate_result.get("profile") == PROFILE_ID, "execution profile")
    require(candidate_result.get("independent_oracle"), "independent oracle missing")
    sandbox = iteration / "sandbox"
    require(sandbox.is_dir(), "missing sandbox/effect observation")
    journal = sandbox / "effects.jsonl"
    executed = candidate_result.get("source_profile_supported") is True or bool(candidate_result.get("handler_calls"))
    if executed:
        require(journal.is_file(), "missing effect journal")
    else:
        require(not journal.is_file(), "effect journal present for a profile-rejected candidate")
    require(iteration_result.get("terminal") in TERMINALS, "iteration terminal")
    call_id = reserved.get("call_id") or (attempt_id + f"-{call_index:02d}")
    return {
        "call_id": call_id,
        "prompt_tokens": transport["prompt_tokens"],
        "completion_tokens": transport["completion_tokens"],
        "useful_work": bool(iteration_result.get("useful_work")),
        "terminal": iteration_result["terminal"],
    }


def check_cell(results: Path, planned: dict, study: dict, runtime: dict, model_profile: dict, batch_id: str) -> dict:
    attempt_id = planned["attempt_id"]
    cell = cell_dir_for(results, attempt_id)
    result = load_json(cell / "result.json")
    require(result.get("schema") == "la-closed-loop-attempt/v1", "attempt schema")
    require(result.get("scientific_benchmark") is True, "scientific_benchmark is not true")
    require(result.get("constructed_transport") is not True, "constructed transport labeled scientific")
    require(result.get("attempt_id") == attempt_id, "attempt_id mismatch")
    require(result.get("case_id") == planned["case_id"], "case_id mismatch")
    require(result.get("arm") == planned["arm"], "arm mismatch")
    require(int(result.get("seed")) == int(planned["seed"]), "seed mismatch")
    require(result.get("family_id") == planned["family_id"], "family binding")
    require(result.get("batch_id") == batch_id, "batch id")
    require(result.get("source_id") == planned["source_id"], "source binding")
    require(result.get("split") == planned["split"], "split binding")
    require(result.get("freeze_sha256") == study["freeze_sha256"], "freeze binding")
    require(result.get("model_profile_sha256") == digest(model_profile), "model profile binding")
    require(result.get("prompt_profile_sha256") == study["prompt_profile_sha256"], "prompt profile binding")
    require(result.get("execution_profile") == PROFILE_ID, "execution profile")
    require(result.get("runtime_sha256") == digest(runtime), "runtime binding")
    driver_pin = runtime["source_files"]["papers/completion/law_to_action/benchmark/generated_code_study/driver.py"]
    handler_pin = runtime["source_files"]["papers/completion/law_to_action/benchmark/handlers/effects.py"]
    require(result.get("driver_sha256") == driver_pin, "driver binding")
    require(result.get("handlers_sha256") == handler_pin, "handler binding")
    require(result.get("paid_budget") == PAID_BUDGET, "paid budget")
    require(result.get("terminal") in TERMINALS, "attempt terminal")
    require(type(result.get("wall_seconds")) in (int, float), "wall cost missing")
    require(type(result.get("cpu_seconds")) in (int, float), "cpu cost missing")
    require(type(result.get("model_calls")) is int and result["model_calls"] >= 1, "no real model calls")
    require(result.get("unknown_costs") in (False, True), "cost accounting missing")
    if result.get("unknown_costs") is True:
        require(result.get("unknown_cost_fields"), "unknown costs not itemized")
    iterations = iteration_dirs(cell)
    measured = [check_iteration(path, attempt_id, index) for index, path in enumerate(iterations)]
    require(result["model_calls"] == sum(1 for _ in measured), "model-call count mismatch")
    require(any(row["terminal"] == result["terminal"] or result["terminal"] == "budget_exhausted" for row in measured), "terminal not protocol-accounted")
    if result["terminal"] == "useful_work":
        require(any(row["useful_work"] for row in measured), "useful_work without measured useful iteration")
    return {
        "attempt_id": attempt_id,
        "terminal": result["terminal"],
        "model_calls": result["model_calls"],
        "useful_work": result["terminal"] == "useful_work",
        "candidate_failed": result["terminal"] == "candidate_failed",
    }


def verify(study_path: Path, batch_id: str, results: Path, require_complete: bool) -> dict:
    study_dir = study_path.parent
    study = load_json(study_path)
    require(study.get("schema") == "la-closed-loop-study/v1", "unexpected study schema")
    require(study.get("freeze_sha256"), "freeze identity missing")
    require(study.get("mock") is False, "mock freeze")
    batch = load_batch(study_dir, batch_id)
    planned = planned_identities(study_dir, batch)
    require(results.is_dir(), "missing results directory " + str(results))
    runtime = load_json(study_dir / "qualification/runtime.json")
    model_profile = load_json(study_dir / "model_profile.json")
    require(runtime.get("status") == "PASS" and runtime.get("mock") is False, "runtime qualification")
    require(file_sha(study_dir / "driver.py") == runtime["source_files"]["papers/completion/law_to_action/benchmark/generated_code_study/driver.py"], "driver bytes")
    require(digest(model_profile) == study["model_profile_sha256"], "model profile freeze")
    manifest = load_json(results / "manifest.json")
    require(manifest.get("batch_id") == batch_id, "manifest batch")
    require(manifest.get("freeze_sha256") == study["freeze_sha256"], "manifest freeze")
    require(manifest.get("family_binding") == batch["family_binding"], "manifest family")
    require(manifest.get("constructed_transport") is False, "manifest constructed transport")
    require(manifest.get("scientific_benchmark") is True, "manifest not scientific")
    require(len(manifest.get("identities") or []) == 30, "manifest identities")
    require([row["attempt_id"] for row in manifest["identities"]] == [row["attempt_id"] for row in planned], "manifest identity order")
    rows = [check_cell(results, item, study, runtime, model_profile, batch_id) for item in planned]
    require(len(rows) == 30, "identity coverage")
    control_path = results / "control.json"
    require(control_path.is_file(), "missing durable control store")
    control = load_json(control_path)
    require(control.get("freeze_sha256") == study["freeze_sha256"], "control freeze")
    cells = control.get("cells") or {}
    calls = control.get("model_calls") or {}
    for item in planned:
        record = cells.get(item["attempt_id"])
        require(isinstance(record, dict), "unreserved cell " + item["attempt_id"])
        require(record.get("consumed") in (1, True), "unconsumed cell " + item["attempt_id"])
        require(record.get("state") in ("completed", "failed_consumed"), "unterminated cell " + item["attempt_id"])
        require(int(record.get("scientific") or 0) == 1, "cell not marked scientific")
        require(record.get("batch_id") == batch_id, "control batch binding")
    require(len(calls) >= 30, "missing reserved model calls")
    for call in calls.values():
        require(call.get("state") in ("completed", "failed_consumed"), "unconsumed model call " + str(call.get("call_id")))
        if call["state"] == "completed":
            require(call.get("prompt_tokens") == call.get("input_count"), "control prompt_tokens != input_count")
    costs_path = results / "costs.jsonl"
    raw_path = results / "raw.jsonl"
    require(costs_path.is_file() and raw_path.is_file(), "missing costs/raw ledgers")
    cost_ids = [json.loads(line)["attempt_id"] for line in costs_path.read_text().splitlines() if line.strip()]
    raw_ids = [json.loads(line)["attempt_id"] for line in raw_path.read_text().splitlines() if line.strip()]
    expected_ids = [row["attempt_id"] for row in planned]
    require(cost_ids == expected_ids, "costs ledger identities")
    require(raw_ids == expected_ids, "raw ledger identities")
    summary = load_json(results / "summary.json")
    require(summary.get("batch_id") == batch_id, "summary batch")
    require(summary.get("planned_cells") == 30, "summary planned")
    require(summary.get("terminal_records") == 30, "summary terminals")
    require(summary.get("unrun") == 0 and summary.get("unadmitted") == 0, "unrun/unadmitted retained as incomplete")
    require(summary.get("constructed_programs_substituted") is False, "program substitution")
    require(summary.get("scientific_benchmark") is True, "summary not scientific")
    require(require_complete, "require-complete was not requested")
    require(all(row["model_calls"] >= 1 for row in rows), "identity without model calls")
    return {
        "status": "PASS",
        "batch_id": batch_id,
        "identities": 30,
        "terminal_records": 30,
        "useful_work": sum(row["useful_work"] for row in rows),
        "candidate_failed": sum(row["candidate_failed"] for row in rows),
        "model_calls": sum(row["model_calls"] for row in rows),
        "unrun": 0,
        "unadmitted": 0,
        "family_binding": batch["family_binding"],
        "freeze_sha256": study["freeze_sha256"],
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--freeze", type=Path, required=True)
    parser.add_argument("--batch-task", required=True)
    parser.add_argument("--results", type=Path)
    parser.add_argument("--require-complete", action="store_true")
    args = parser.parse_args()
    freeze = args.freeze
    if not freeze.is_absolute():
        freeze = (Path.cwd() / freeze).resolve()
    results = args.results
    if results is None:
        results = RESULTS_ROOT / args.batch_task
    elif not results.is_absolute():
        results = (Path.cwd() / results).resolve()
    report = verify(freeze, args.batch_task, results, args.require_complete)
    print(json.dumps(report, sort_keys=True, indent=2))


if __name__ == "__main__":
    main()
