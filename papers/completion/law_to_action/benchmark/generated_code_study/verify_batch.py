#!/usr/bin/python3.12
"""Read-only verifier for one frozen generated-code family-batch execution.

Tiny-byte-lm dumps, missing identities, unrun cells, transport failures, and
loopback owners fail closed. Measured candidate failure is a retained outcome.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

HERE = Path(__file__).resolve().parent
CANDIDATES = [
    HERE,
    HERE.parent if (HERE.parent / "driver.py").is_file() else HERE,
    Path("/home/barberb/lift_coding/.worktrees/vericodegen-law_to_action-2026/papers/completion/law_to_action/benchmark/generated_code_study"),
]
STUDY = next(path for path in CANDIDATES if (path / "driver.py").is_file())
sys.path.insert(0, str(STUDY))
from driver import MAX_INPUT, PAID_BUDGET, build_schedule, load_json  # noqa: E402

TINY = "tiny-byte"
DOCKER0 = "172.17.0.1"


def fail(message: str) -> int:
    print("FAIL: " + message)
    return 2


def cell_relpath(attempt_id: str) -> str:
    seed, arm, rest = attempt_id.split(":", 2)
    case = rest.rsplit(":", 1)[-1]
    return f"cells/{seed}/{arm}/{case}"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--freeze", type=Path, required=True)
    parser.add_argument("--batch-task", required=True)
    parser.add_argument("--require-complete", action="store_true")
    parser.add_argument("--results", type=Path)
    args = parser.parse_args()
    freeze = load_json(args.freeze)
    batches = load_json(STUDY / "family_batches.json")
    schedule_doc = load_json(STUDY / "schedule.json")
    batch = next((row for row in batches["batches"] if row["id"] == args.batch_task), None)
    if batch is None:
        return fail("unknown batch " + args.batch_task)
    expected = [row for row in build_schedule(schedule_doc["case_ids"]) if row["case_id"] in batch["paired_cases"]]
    if len(expected) != 30:
        return fail("schedule does not yield 30 identities")
    results = args.results or (args.freeze.resolve().parents[2] / "results/generated_code_study/batches" / args.batch_task)
    batch_json = results / "batch.json"
    if not batch_json.is_file():
        return fail("missing batch.json")
    summary = load_json(batch_json)
    binding = load_json(results / "freeze_binding.json") if (results / "freeze_binding.json").is_file() else {}
    model = str(summary.get("model_revision") or binding.get("model_id") or "")
    origin = str(binding.get("base_url") or "") + str(summary.get("service_accounting") or {})
    if TINY in model.lower() or TINY in origin.lower() or binding.get("tiny_byte_lm") is True:
        return fail("tiny-byte-lm is not the docker0 scientific owner")
    if DOCKER0 not in origin and binding.get("bind") != "docker0":
        return fail("owner is not docker0 172.17.0.1")
    if summary.get("mock") or summary.get("fixed_program_substituted") or summary.get("silent_replay"):
        return fail("mock/fixed-program/silent-replay batch")
    if int(summary.get("transport_failure_cells") or 0) != 0:
        return fail("transport failures are not a complete batch")
    if int(summary.get("paid_budget") or 0) != PAID_BUDGET:
        return fail("paid budget is not zero")
    missing = []
    unadmitted = []
    for row in expected:
        directory = results / cell_relpath(row["attempt_id"])
        result_path = directory / "result.json"
        admitted_path = directory / "admitted.json"
        reservation = directory / "reservation.json"
        if not result_path.is_file() or not admitted_path.is_file() or not reservation.is_file():
            missing.append(row["attempt_id"])
            continue
        result = load_json(result_path)
        admitted = load_json(admitted_path)
        generated = False
        for item in result.get("iterations") or []:
            if not item.get("model_generated"):
                continue
            generated = True
            iteration = directory / f"iteration-{int(item['iteration']):02d}"
            preflight = load_json(iteration / "preflight.json") if (iteration / "preflight.json").is_file() else {}
            transport = load_json(iteration / "transport_result.json") if (iteration / "transport_result.json").is_file() else {}
            if not (iteration / "candidate.py").is_file() or not (iteration / "raw_response.json").is_file():
                unadmitted.append(row["attempt_id"] + ":missing_candidate_or_raw")
            if transport.get("prompt_tokens") != preflight.get("input_count"):
                unadmitted.append(row["attempt_id"] + ":prompt_token_mismatch")
            if int(preflight.get("input_count") or 0) > MAX_INPUT:
                unadmitted.append(row["attempt_id"] + ":input_ceiling")
        if not generated or admitted.get("admitted") is not True:
            unadmitted.append(row["attempt_id"] + ":not_admitted")
        if result.get("terminal") in (None, "", "started", "unrun", "transport_or_format_failure"):
            unadmitted.append(row["attempt_id"] + ":nonterminal")
    if missing:
        return fail("missing identities: " + ",".join(missing[:5]))
    if unadmitted:
        return fail("unadmitted identities: " + ",".join(unadmitted[:8]))
    complete = (
        summary.get("complete") is True and summary.get("status") == "COMPLETE"
        and int(summary.get("planned_cells") or 0) == 30
        and int(summary.get("terminal_cells") or 0) == 30
        and int(summary.get("admitted_cells") or 0) == 30
        and not missing and not unadmitted
    )
    if args.require_complete and not complete:
        return fail("batch is not complete")
    print(json.dumps({
        "status": "PASS" if complete else "INCOMPLETE",
        "batch_task": args.batch_task,
        "terminal_cells": 30 - len(missing),
        "useful_work_cells": summary.get("useful_work_cells"),
        "model_revision": model,
        "tiny_byte_lm": False,
    }, sort_keys=True))
    return 0 if complete or not args.require_complete else 2


if __name__ == "__main__":
    raise SystemExit(main())
