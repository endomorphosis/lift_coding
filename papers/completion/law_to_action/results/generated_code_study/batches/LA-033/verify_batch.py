#!/usr/bin/python3.12
"""Read-only recomputation of a frozen generated-code family batch.

Official command path:
  papers/completion/law_to_action/benchmark/generated_code_study/verify_batch.py
This copy is retained with the LA-033 evidence tree and is path-adaptive.
"""
from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from pathlib import Path

HERE = Path(__file__).resolve().parent
if (HERE / "driver.py").is_file():
    STUDY = HERE
    PAPER = HERE.parents[1]
else:
    PAPER = HERE.parents[3]
    STUDY = PAPER / "benchmark/generated_code_study"
sys.path.insert(0, str(STUDY))
from driver import (  # noqa: E402
    ARMS,
    BATCH_ATTEMPT_SECONDS,
    PAID_BUDGET,
    PROFILE_ID,
    PROMPT_PROFILE,
    SEEDS,
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


def results_dir(batch_id: str) -> Path:
    target = PAPER / "results/generated_code_study/batches" / batch_id
    if not target.is_dir() and HERE.name == batch_id:
        return HERE
    return target


def cell_dir(batch: Path, attempt_id: str) -> Path:
    return batch / "cells" / attempt_id.replace(":", "__")


def expected_identities(batch: dict, cases: dict, reconstructed: list[dict]) -> list[dict]:
    expected = []
    for row in reconstructed:
        if row["case_id"] not in batch["paired_cases"]:
            continue
        info = cases[row["case_id"]]
        expected.append(
            {
                "attempt_id": row["attempt_id"],
                "schedule_index": row["schedule_index"],
                "seed": row["seed"],
                "arm": row["arm"],
                "case_id": row["case_id"],
                "family_id": info["source_family"],
                "population": info["population"],
                "split": info["split"],
            }
        )
    return expected


def verify(batch_id: str, freeze_path: Path, require_complete: bool) -> dict:
    study = load_json(freeze_path)
    require(study.get("schema") == "la-closed-loop-study/v1", "unexpected study schema")
    require(study.get("freeze_sha256"), "missing freeze identity")
    batches = load_json(STUDY / "family_batches.json")
    schedule_doc = load_json(STUDY / "schedule.json")
    cases = {row["id"]: row for row in load_json(STUDY / "cohort/cases.json")["cases"]}
    runtime = load_json(STUDY / "qualification/runtime.json")
    model_profile = load_json(STUDY / "model_profile.json")
    batch = next((row for row in batches["batches"] if row["id"] == batch_id), None)
    require(batch is not None, "unknown batch task")
    reconstructed = build_schedule(schedule_doc["case_ids"])
    require(digest([row["attempt_id"] for row in reconstructed]) == schedule_doc["identity_digest"], "schedule identity")
    expected = expected_identities(batch, cases, reconstructed)
    require(len(expected) == 30, "batch is not 30 original identities")
    require({row["arm"] for row in expected} == set(ARMS), "arm identities dropped")
    require({row["seed"] for row in expected} == set(SEEDS), "seed identities dropped")
    require(batch["family_binding"] == expected[0]["family_id"], "family binding")
    require(batch["maximum_scientific_attempt_seconds"] == BATCH_ATTEMPT_SECONDS, "scientific attempt bound")
    output = results_dir(batch_id)
    require(output.is_dir(), "missing batch results directory")
    identities = load_json(output / "identities.json")
    completeness = load_json(output / "completeness.json")
    summary = load_json(output / "summary.json")
    freeze_binding = load_json(output / "freeze_binding.json")
    batch_doc = load_json(output / "batch.json")
    control = load_json(output / "control_snapshot.json")
    require(identities["attempt_ids"] == [row["attempt_id"] for row in expected], "identity order")
    require(freeze_binding["freeze_sha256"] == study["freeze_sha256"], "freeze binding")
    require(freeze_binding["model_profile_sha256"] == study["model_profile_sha256"], "model freeze")
    require(freeze_binding["prompt_profile_sha256"] == digest(PROMPT_PROFILE), "prompt freeze")
    require(freeze_binding["runtime_driver_sha256"] == file_sha(STUDY / "driver.py"), "driver runtime")
    require(
        freeze_binding["runtime_handlers_sha256"]
        == runtime["source_files"]["papers/completion/law_to_action/benchmark/handlers/effects.py"],
        "handlers runtime",
    )
    require(file_sha(output / "model/model.json") == model_profile["weights_sha256"], "weights pin")
    require(control["scientific_cells_completed"] == 30, "durable scientific completion")
    require(len(control["cells"]) == 30 and len(control["model_calls"]) == 30, "reservation coverage")
    require(batch_doc["paid_budget"] == PAID_BUDGET, "paid budget")
    records_by_id = {}
    for line in (output / "records.jsonl").read_text().splitlines():
        if line.strip():
            row = json.loads(line)
            records_by_id[row["attempt_id"]] = row
    missing = []
    terminals = []
    for identity in expected:
        attempt_id = identity["attempt_id"]
        directory = cell_dir(output, attempt_id)
        terminal_path = directory / "terminal.json"
        result_path = directory / "result.json"
        if not terminal_path.is_file() or not result_path.is_file() or attempt_id not in records_by_id:
            missing.append(attempt_id)
            continue
        terminal = load_json(terminal_path)
        result = load_json(result_path)
        require(terminal["attempt_id"] == attempt_id, "terminal identity")
        require(result["attempt_id"] == attempt_id, "result identity")
        require(result["case_id"] == identity["case_id"], "case binding")
        require(result["arm"] == identity["arm"] and result["seed"] == identity["seed"], "arm/seed binding")
        require(result["family_id"] == batch["family_binding"], "family binding")
        require(result["split"] == identity["split"] == "development", "development split")
        require(result["freeze_sha256"] == study["freeze_sha256"], "cell freeze")
        require(result["model_profile_sha256"] == study["model_profile_sha256"], "cell model")
        require(result["runtime_driver_sha256"] == freeze_binding["runtime_driver_sha256"], "cell runtime")
        require(result["scientific_benchmark"] is True, "scientific flag")
        require(result["constructed_transport"] is False, "constructed transport")
        require(result["fixed_program_substituted"] is False, "fixed program")
        require(result["protocol_accounted"] is True, "protocol accounting")
        require(result["source_bound"] and result["model_bound"] and result["runtime_bound"], "bindings")
        require(result["unknown_costs"] is False, "unknown costs")
        require(result["paid_budget"] == 0, "paid budget on cell")
        require(result["real_generated_candidate"] is True, "missing generated candidate")
        require(result["terminal"], "missing terminal")
        require(type(result["wall_seconds"]) is float and result["model_calls"] >= 1, "costs")
        require(type(result["known_prompt_tokens"]) is int and type(result["known_completion_tokens"]) is int, "tokens")
        candidate = directory / "iteration-00/candidate.py"
        raw = directory / "iteration-00/raw_response.json"
        reserved = directory / "iteration-00/inference_reserved.json"
        effects = directory / "iteration-00/result.json"
        require(candidate.is_file() and candidate.stat().st_size > 0, "generated candidate missing")
        require(raw.is_file() and reserved.is_file(), "model reservation/raw missing")
        require(effects.is_file(), "effect record missing")
        iteration = load_json(directory / "iteration-00/iteration_result.json")
        require(iteration.get("model_generated") is True, "model_generated")
        require(iteration.get("origin") == "qualified-local-model", "origin")
        require(iteration.get("fixed_program_substituted") is False, "iteration substitution")
        require(iteration.get("prompt_tokens") == iteration.get("preflight_input_count"), "token agreement")
        require(iteration.get("effect_status") == "measured", "effects unmeasured")
        control_cell = next(row for row in control["cells"] if row["attempt_id"] == attempt_id)
        require(control_cell["scientific"] == 1 and control_cell["consumed"] == 1, "unconsumed cell")
        require(control_cell["state"] in {"completed", "failed_consumed"}, "cell not terminal")
        terminals.append(result["terminal"])
    if require_complete:
        require(not missing, "missing/unrun/unadmitted identities: " + json.dumps(missing))
        require(completeness.get("batch_complete") is True, "completeness document")
        require(completeness.get("status") == "PASS", "completeness status")
        require(summary.get("terminal_records") == 30, "summary count")
        require(summary.get("fixed_program_substituted") is False, "summary substitution")
        require(batch_doc.get("batch_complete") is True, "batch document")
        require(len(set(identities["attempt_ids"])) == 30, "duplicate identities")
        require(PROFILE_ID == freeze_binding["execution_profile"], "execution profile")
    report = {
        "status": "PASS" if not missing else "FAIL",
        "batch_id": batch_id,
        "planned_identities": 30,
        "terminal_records": 30 - len(missing),
        "missing_unrun_unadmitted": missing,
        "terminal_counts": dict(Counter(terminals)),
        "batch_complete": not missing,
        "require_complete": require_complete,
        "legitimate_measured_failure_retained": True,
        "fixed_program_substituted": False,
        "scientific_cells_completed": control["scientific_cells_completed"],
    }
    require(report["status"] == "PASS" or not require_complete, "batch incomplete")
    return report


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--freeze", type=Path, required=True)
    parser.add_argument("--batch-task", required=True)
    parser.add_argument("--require-complete", action="store_true")
    args = parser.parse_args()
    report = verify(args.batch_task, args.freeze, args.require_complete)
    print(json.dumps(report, sort_keys=True))


if __name__ == "__main__":
    main()
