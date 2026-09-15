#!/usr/bin/python3.12
"""Read-only verifier for one frozen generated-code family-batch execution.

Accepts either an on-disk cells/ tree or the compact evidence.json recipe.
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


def fail(message: str) -> int:
    print("FAIL: " + message)
    return 2


def load_json(path: Path) -> Any:
    return json.loads(path.read_text())


def cell_relpath(attempt_id: str) -> str:
    seed, arm, rest = attempt_id.split(":", 2)
    case = rest.rsplit(":", 1)[-1]
    return f"cells/{seed}/{arm}/{case}"


def iteration_key(item: dict[str, Any]) -> str:
    return f"{int(item['iteration']):02d}"


def load_cell(results: Path, recipe: dict[str, Any] | None, attempt_id: str) -> dict[str, Any] | None:
    packed = (recipe or {}).get("cells", {}).get(attempt_id)
    directory = results / cell_relpath(attempt_id)
    if packed is not None:
        return packed
    result_path = directory / "result.json"
    admitted_path = directory / "admitted.json"
    reservation = directory / "reservation.json"
    if not result_path.is_file() or not admitted_path.is_file() or not reservation.is_file():
        return None
    packed = {
        "admitted": load_json(admitted_path),
        "reservation": load_json(reservation),
        "result": load_json(result_path),
        "iterations": {},
    }
    for item in packed["result"].get("iterations") or []:
        iteration = directory / f"iteration-{iteration_key(item)}"
        row: dict[str, Any] = {}
        if (iteration / "candidate.py").is_file():
            row["candidate"] = (iteration / "candidate.py").read_text()
        for name in ("raw_response", "preflight", "transport_result"):
            path = iteration / f"{name}.json"
            if path.is_file():
                row[name] = load_json(path)
        packed["iterations"][iteration_key(item)] = row
    return packed


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--freeze", type=Path, required=True)
    parser.add_argument("--batch-task", required=True)
    parser.add_argument("--require-complete", action="store_true")
    parser.add_argument("--results", type=Path)
    args = parser.parse_args()
    freeze_path = args.freeze.resolve()
    study = freeze_path.parent
    sys.path.insert(0, str(study))
    from driver import MAX_INPUT, PAID_BUDGET, build_schedule, load_json as study_load  # noqa: E402

    freeze = study_load(freeze_path)
    batches = study_load(study / "family_batches.json")
    schedule_doc = study_load(study / "schedule.json")
    batch = next((row for row in batches["batches"] if row["id"] == args.batch_task), None)
    if batch is None:
        return fail("unknown batch " + args.batch_task)
    expected = [row for row in build_schedule(schedule_doc["case_ids"]) if row["case_id"] in batch["paired_cases"]]
    if len(expected) != 30:
        return fail("schedule does not yield 30 identities")
    results = args.results or (freeze_path.parents[2] / "results/generated_code_study/batches" / args.batch_task)
    if HERE.name == args.batch_task and (HERE / "batch.json").is_file():
        results = HERE
    batch_json = results / "batch.json"
    if not batch_json.is_file():
        return fail("missing batch.json")
    summary = study_load(batch_json)
    binding = study_load(results / "freeze_binding.json") if (results / "freeze_binding.json").is_file() else {}
    recipe = study_load(results / "evidence.json") if (results / "evidence.json").is_file() else None
    model = str(summary.get("model_revision") or binding.get("model_id") or "")
    origin = str(binding.get("base_url") or "") + str(summary.get("service_accounting") or {})
    if "tiny-byte" in model.lower() or "tiny-byte" in origin.lower() or binding.get("tiny_byte_lm") is True:
        return fail("tiny-byte-lm is not the docker0 scientific owner")
    if "172.17.0.1" not in origin and binding.get("bind") != "docker0":
        return fail("owner is not docker0 172.17.0.1")
    if summary.get("mock") or summary.get("fixed_program_substituted") or summary.get("silent_replay"):
        return fail("mock/fixed-program/silent-replay batch")
    if int(summary.get("transport_failure_cells") or 0) != 0:
        return fail("transport failures are not a complete batch")
    if int(summary.get("paid_budget") or 0) != PAID_BUDGET:
        return fail("paid budget is not zero")
    if freeze.get("freeze_sha256") and binding.get("freeze_sha256") not in (None, freeze["freeze_sha256"]):
        return fail("freeze_sha256 does not match prospective freeze")
    if summary.get("family_binding") != batch["family_binding"] or binding.get("family_binding") not in (None, batch["family_binding"]):
        return fail("family binding mismatch")
    if summary.get("source_id") != batch["source_id"]:
        return fail("source_id mismatch")
    missing = []
    unadmitted = []
    useful = 0
    generated_cells = 0
    for row in expected:
        packed = load_cell(results, recipe, row["attempt_id"])
        if packed is None:
            missing.append(row["attempt_id"])
            continue
        result = packed["result"]
        admitted = packed["admitted"]
        generated = False
        for item in result.get("iterations") or []:
            if not item.get("model_generated"):
                continue
            generated = True
            iteration = packed.get("iterations", {}).get(iteration_key(item), {})
            preflight = iteration.get("preflight") or {}
            transport = iteration.get("transport_result") or {}
            candidate = iteration.get("candidate")
            raw = iteration.get("raw_response")
            if not candidate or raw in (None, {}):
                unadmitted.append(row["attempt_id"] + ":missing_candidate_or_raw")
            if transport.get("prompt_tokens") != preflight.get("input_count"):
                unadmitted.append(row["attempt_id"] + ":prompt_token_mismatch")
            if int(preflight.get("input_count") or 0) > MAX_INPUT:
                unadmitted.append(row["attempt_id"] + ":input_ceiling")
        if not generated or admitted.get("admitted") is not True:
            unadmitted.append(row["attempt_id"] + ":not_admitted")
        if result.get("terminal") in (None, "", "started", "unrun", "transport_or_format_failure"):
            unadmitted.append(row["attempt_id"] + ":nonterminal")
        if generated:
            generated_cells += 1
        if result.get("useful_work") is True:
            useful += 1
    if missing:
        return fail("missing identities: " + ",".join(missing[:5]))
    if unadmitted:
        return fail("unadmitted identities: " + ",".join(unadmitted[:8]))
    costs = results / "costs.jsonl"
    if costs.is_file():
        cost_rows = [json.loads(line) for line in costs.read_text().splitlines() if line.strip()]
        if len(cost_rows) != 30:
            return fail("costs.jsonl does not retain 30 cell cost records")
    complete = (
        summary.get("complete") is True
        and summary.get("status") == "COMPLETE"
        and int(summary.get("planned_cells") or 0) == 30
        and int(summary.get("terminal_cells") or 0) == 30
        and int(summary.get("admitted_cells") or 0) == 30
        and generated_cells == 30
        and not missing
        and not unadmitted
    )
    if args.require_complete and not complete:
        return fail("batch is not complete")
    print(
        json.dumps(
            {
                "status": "PASS" if complete else "INCOMPLETE",
                "batch_task": args.batch_task,
                "terminal_cells": 30 - len(missing),
                "useful_work_cells": summary.get("useful_work_cells", useful),
                "model_revision": model,
                "tiny_byte_lm": False,
            },
            sort_keys=True,
        )
    )
    return 0 if complete or not args.require_complete else 2


if __name__ == "__main__":
    raise SystemExit(main())
