#!/usr/bin/python3.12
"""Read-only completeness verifier for one frozen generated-code family batch."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent


def repository_root(start: Path) -> Path:
    for path in [start, *start.parents]:
        if (path / "papers/completion/law_to_action/benchmark/generated_code_study/driver.py").is_file():
            return path
    raise SystemExit("LA family-batch verifier failed: repository root not found")


ROOT = repository_root(HERE)
STUDY = ROOT / "papers/completion/law_to_action/benchmark/generated_code_study"
sys.path.insert(0, str(STUDY))
from driver import (  # noqa: E402
    ATTEMPT_WALL,
    BATCH_ATTEMPT_SECONDS,
    MAX_INPUT,
    MAX_OUTPUT,
    PAID_BUDGET,
    PROFILE_ID,
    build_schedule,
    digest,
    file_sha,
    load_json,
)


def fail(message: str) -> None:
    raise SystemExit("LA family-batch verifier failed: " + message)


def require(condition: bool, message: str) -> None:
    if not condition:
        fail(message)


def cell_dir(results: Path, attempt_id: str) -> Path:
    direct = results / "cells" / attempt_id
    if direct.is_dir():
        return direct
    fail("missing cell directory for " + attempt_id)


def verify_batch(freeze: Path, batch_id: str, require_complete: bool) -> dict:
    study = load_json(freeze)
    study_dir = freeze.parent
    require(study.get("schema") == "la-closed-loop-study/v1", "unexpected study schema")
    require(study.get("mock") is False, "mock freeze")
    batches = load_json(study_dir / "family_batches.json")
    schedule_doc = load_json(study_dir / "schedule.json")
    model_profile = load_json(study_dir / "model_profile.json")
    runtime = load_json(study_dir / "qualification/runtime.json")
    cases = {row["id"]: row for row in load_json(study_dir / "cohort/cases.json")["cases"]}
    batch = next((row for row in batches["batches"] if row["id"] == batch_id), None)
    require(batch is not None, "unknown batch-task " + batch_id)
    expected = build_schedule(schedule_doc["case_ids"])
    cells = [row for row in expected if row["case_id"] in set(batch["paired_cases"])]
    require(len(cells) == 30, "batch is not 30 original identities")
    require(len({row["attempt_id"] for row in cells}) == 30, "duplicate identities")
    for row in cells:
        info = cases[row["case_id"]]
        row["family_id"] = info["source_family"]
        row["population"] = info["population"]
        row["split"] = info["split"]
        require(info["source_family"] == batch["family_binding"], "cell escaped family binding")
        require(row["arm"] in batch["arms"] and row["seed"] in batch["seeds"], "arm/seed not frozen")
    results = ROOT / "papers/completion/law_to_action/results/generated_code_study/batches" / batch_id
    require(results.is_dir(), "batch results directory missing")
    manifest = load_json(results / "batch.json")
    identities = load_json(results / "identities.json")
    control = load_json(results / "control.json")
    summary = load_json(results / "summary.json")
    require(manifest.get("batch_id") == batch_id, "batch.json id")
    require(manifest.get("family_binding") == batch["family_binding"], "family binding")
    require(manifest.get("freeze_sha256") == study["freeze_sha256"], "freeze identity")
    require(manifest.get("schedule_identity_digest") == schedule_doc["identity_digest"], "schedule digest")
    require(manifest.get("constructed_program_substituted") is False, "fixed program substituted")
    require(identities.get("attempt_ids") == [row["attempt_id"] for row in cells], "identity order")
    require(file_sha(study_dir / "driver.py") == runtime["source_files"]["papers/completion/law_to_action/benchmark/generated_code_study/driver.py"], "runtime/driver")
    require(file_sha(study_dir / "qualification/model/model.json") == model_profile["weights_sha256"], "weights")
    require(digest(model_profile) == study["model_profile_sha256"], "model profile freeze")
    require(control.get("freeze_sha256") == study["freeze_sha256"], "control freeze")
    require(summary.get("paid_budget") == PAID_BUDGET, "paid budget")
    require(summary.get("constructed_program_substituted") is False, "summary substitution")
    require(summary.get("silent_replay") is False, "silent replay")
    require(summary.get("maximum_scientific_attempt_seconds", BATCH_ATTEMPT_SECONDS) == BATCH_ATTEMPT_SECONDS, "batch wall")
    require(summary.get("wall_seconds", 0) <= BATCH_ATTEMPT_SECONDS, "scientific attempt allowance")
    missing = []
    unadmitted = []
    terminals = []
    for cell in cells:
        attempt_id = cell["attempt_id"]
        directory = cell_dir(results, attempt_id)
        result_path = directory / "result.json"
        if not result_path.is_file():
            missing.append(attempt_id)
            continue
        result = load_json(result_path)
        stored = (control.get("cells") or {}).get(attempt_id)
        admitted = (
            result.get("scientific_benchmark") is True
            and result.get("protocol_accounted") is True
            and result.get("resource_admitted") is True
            and result.get("constructed_program_substituted") is False
            and result.get("fixed_program_substituted") is False
            and result.get("silent_replay") is False
            and result.get("paid_budget") == PAID_BUDGET
            and result.get("overrun") is False
            and result.get("unknown_costs") is False
            and result.get("model_generated") is True
            and result.get("wall_seconds", ATTEMPT_WALL + 1) <= ATTEMPT_WALL
            and result.get("bindings", {}).get("freeze_sha256") == study["freeze_sha256"]
            and result.get("bindings", {}).get("weights_sha256") == model_profile["weights_sha256"]
            and result.get("bindings", {}).get("runtime_driver_sha256") == runtime["source_files"]["papers/completion/law_to_action/benchmark/generated_code_study/driver.py"]
            and result.get("attempt_id") == attempt_id
            and result.get("case_id") == cell["case_id"]
            and result.get("arm") == cell["arm"]
            and int(result.get("seed")) == int(cell["seed"])
            and stored
            and stored.get("consumed")
            and stored.get("scientific") in (1, True)
            and stored.get("state") in {"completed", "failed_consumed"}
            and stored.get("result_sha256") == file_sha(result_path)
            and bool(result.get("iterations"))
        )
        generated = False
        effects = False
        for row in result.get("iterations") or []:
            iter_dir = directory / f"iteration-{int(row['iteration']):02d}"
            require(iter_dir.is_dir() and (iter_dir / "iteration_result.json").is_file(), "iteration record " + attempt_id)
            if row.get("model_generated"):
                generated = True
                require(row.get("origin") == "qualified-local-model", "non-qualified origin")
                require(row.get("constructed_program_substituted") is False, "constructed substitution")
                require(row.get("prompt_tokens") == row.get("preflight_input_count"), "prompt_tokens != preflight")
                require(isinstance(row.get("prompt_tokens"), int) and row["prompt_tokens"] <= MAX_INPUT, "input ceiling")
                require(isinstance(row.get("completion_tokens"), int) and row["completion_tokens"] <= MAX_OUTPUT, "output ceiling")
                require((iter_dir / "raw_response.json").is_file(), "raw response missing")
                require((iter_dir / "candidate.py").is_file(), "generated candidate missing")
                require((iter_dir / "preflight.json").is_file(), "preflight missing")
                require((iter_dir / "transport_result.json").is_file(), "transport missing")
                raw = load_json(iter_dir / "raw_response.json")
                require(raw.get("usage", {}).get("prompt_tokens") == row["prompt_tokens"], "raw usage mismatch")
            if (iter_dir / "result.json").is_file() or row.get("terminal") in {"useful_work", "candidate_failed"}:
                effects = True
                if (iter_dir / "result.json").is_file():
                    observed = load_json(iter_dir / "result.json")
                    require(observed.get("profile") == PROFILE_ID, "profile")
                    require("useful_work" in observed and "forbidden_effect" in observed, "effect fields")
        if not generated or not effects:
            admitted = False
        if result.get("terminal") not in {"useful_work", "candidate_failed", "budget_exhausted", "budget_exhausted_before_full_execution_allowance", "transport_or_format_failure", "input_ceiling"}:
            admitted = False
        if not admitted:
            unadmitted.append(attempt_id)
        terminals.append(result.get("terminal"))
    if require_complete:
        require(not missing, "missing/unrun identities: " + ",".join(missing[:5]))
        require(not unadmitted, "unadmitted identities: " + ",".join(unadmitted[:5]))
        require(len(cells) - len(missing) == 30, "incomplete terminal set")
        require(summary.get("all_resource_admitted") is True, "summary unadmitted")
        require(manifest.get("status") == "complete", "batch not complete")
        require(manifest.get("scientific_cells_completed") == 30, "scientific cells not completed")
        require(summary.get("scientific_cells_completed") == 30, "summary scientific count")
    report = {
        "status": "PASS",
        "batch_id": batch_id,
        "planned_cells": 30,
        "terminal_records": 30 - len(missing),
        "missing": missing,
        "unadmitted": unadmitted,
        "terminals": {name: terminals.count(name) for name in sorted(set(terminals))},
        "family_binding": batch["family_binding"],
        "freeze_sha256": study["freeze_sha256"],
        "require_complete": require_complete,
        "legitimate_candidate_failure_retained": "candidate_failed" in terminals or any(
            True for cell in cells
            for row in load_json(cell_dir(results, cell["attempt_id"]) / "result.json").get("iterations") or []
            if row.get("terminal") == "candidate_failed"
        ),
        "constructed_program_substituted": False,
    }
    print(json.dumps(report, sort_keys=True))
    return report


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--freeze", type=Path, required=True)
    parser.add_argument("--batch-task", required=True)
    parser.add_argument("--require-complete", action="store_true")
    args = parser.parse_args()
    verify_batch(args.freeze, args.batch_task, args.require_complete)


if __name__ == "__main__":
    main()
