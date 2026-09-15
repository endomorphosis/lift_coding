#!/usr/bin/python3.12
"""Read-only verification of frozen family-batch LA-033 scientific records."""
from __future__ import annotations

import argparse
import gzip
import json
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[6]
STUDY = ROOT / "papers/completion/law_to_action/benchmark/generated_code_study"
sys.path.insert(0, str(STUDY))
from driver import (  # noqa: E402
    MAX_INPUT,
    MAX_OUTPUT,
    PAID_BUDGET,
    PROFILE_ID,
    build_schedule,
    file_sha,
    load_json,
)

BATCH_ID = "LA-033"
PACK = "cells.jsonl.gz"
TERMINALS = {
    "useful_work",
    "candidate_failed",
    "transport_or_format_failure",
    "budget_exhausted",
    "budget_exhausted_before_full_execution_allowance",
}


def fail(message: str) -> None:
    raise SystemExit("family-batch verifier failed: " + message)


def require(condition: bool, message: str) -> None:
    if not condition:
        fail(message)


def materialize(pack: Path, dest: Path) -> None:
    dest.mkdir(parents=True, exist_ok=True)
    with gzip.open(pack, "rt", encoding="utf-8") as handle:
        for line in handle:
            rec = json.loads(line)
            path = dest / rec["p"]
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(rec["b"].encode("latin-1"))


def cell_dir(root: Path, attempt_id: str) -> Path:
    seed, arm, rest = attempt_id.split(":", 2)
    case = rest.rsplit(":", 1)[-1]
    return root / "cells" / seed / arm / case


def verify_cell(root: Path, control: dict, attempt_id: str, expected: dict, binding: dict) -> dict:
    directory = cell_dir(root, attempt_id)
    require(directory.is_dir(), "missing cell " + attempt_id)
    admitted = load_json(directory / "admitted.json")
    reservation = load_json(directory / "reservation.json")
    result = load_json(directory / "result.json")
    require(admitted.get("admitted") is True, "unadmitted " + attempt_id)
    require(admitted.get("terminal") not in {None, "", "started", "unrun"}, "unrun " + attempt_id)
    require(result.get("schema") == "la-closed-loop-attempt/v1", "result schema " + attempt_id)
    require(file_sha(directory / "result.json") == admitted["result_sha256"], "result hash " + attempt_id)
    ctrl = control["cells"][attempt_id]
    require(ctrl["consumed"] == 1 and ctrl["scientific"] == 1, "unconsumed " + attempt_id)
    require(ctrl["result_sha256"] == admitted["result_sha256"], "control hash " + attempt_id)
    require(ctrl["reservation_sha256"] == reservation["reservation_sha256"], "reservation hash " + attempt_id)
    require(ctrl["state"] in {"completed", "failed_consumed"}, "control state " + attempt_id)
    require(result["attempt_id"] == attempt_id == expected["attempt_id"], "attempt identity")
    require(result["case_id"] == expected["case_id"], "case identity")
    require(result["arm"] == expected["arm"] and result["seed"] == expected["seed"], "arm/seed")
    require(result["family_id"] == expected["family_id"], "family identity")
    require(result["split"] == "development", "split")
    require(result["terminal"] in TERMINALS, "terminal " + attempt_id)
    require(result["unknown_costs"] is False, "unknown costs " + attempt_id)
    require(result["paid_budget"] == PAID_BUDGET, "paid budget")
    require(result["mock"] is False and result["constructed_outputs"] is False, "constructed/mock")
    require(result["fixed_program_substituted"] is False, "fixed program")
    require(result["scientific_benchmark"] is True, "not scientific")
    require(result["origin"] == "qualified-local-model", "origin")
    require(result.get("bindings") == binding, "bindings " + attempt_id)
    generated = False
    for row in result["iterations"]:
        it = directory / f"iteration-{int(row['iteration']):02d}"
        require(it.is_dir(), "missing iteration " + attempt_id)
        require((it / "inference_reserved.json").is_file(), "unreserved call " + attempt_id)
        reserved = load_json(it / "inference_reserved.json")
        require(reserved.get("consumed") is True or reserved.get("consumed_before_request") is True, "call not consumed")
        call_id = f"{attempt_id}:{int(row['iteration']):02d}"
        call = control["model_calls"][call_id]
        require(call["reservation_sha256"] == reserved["reservation_sha256"], "call reservation")
        require(call["state"] in {"completed", "failed_consumed"}, "call state")
        if row.get("model_generated"):
            generated = True
            require((it / "candidate.py").is_file() and (it / "candidate.py").stat().st_size > 0, "missing candidate")
            require((it / "raw_response.json").is_file(), "missing raw response")
            require(file_sha(it / "raw_response.json") == call["raw_sha256"], "raw hash")
            transport = load_json(it / "transport_result.json")
            require(transport["prompt_tokens"] == transport["preflight_input_count"], "token equality")
            require(transport["preflight_input_count"] <= MAX_INPUT, "input ceiling")
            require(transport["completion_tokens"] <= MAX_OUTPUT, "output ceiling")
            require(transport["origin"] == "qualified-local-model", "transport origin")
            require(row["terminal"] in TERMINALS, "iteration terminal")
            if row["terminal"] == "candidate_failed":
                require(row.get("useful_work") is False, "dropped failure")
        else:
            require(row["terminal"] == "transport_or_format_failure" or row.get("error"), "silent empty iteration")
    require(generated or result["terminal"] == "transport_or_format_failure", "no generated candidate")
    return result


def verify(batch_dir: Path, freeze: dict, require_complete: bool) -> dict:
    batches = load_json(STUDY / "family_batches.json")
    schedule_doc = load_json(STUDY / "schedule.json")
    runtime = load_json(STUDY / "qualification/runtime.json")
    model_profile = load_json(STUDY / "model_profile.json")
    batch = next(row for row in batches["batches"] if row["id"] == BATCH_ID)
    require(batch["id"] == BATCH_ID and batch["phase"] == "development", "batch identity")
    require(batch["planned_cells"] == 30, "planned cells")
    family = next(row for row in freeze["families"] if row["id"] == batch["family_binding"])
    require(family["split"] == "development" and family["population"] == "legal", "family split")
    expected = [row for row in build_schedule(schedule_doc["case_ids"]) if row["case_id"] in set(batch["paired_cases"])]
    require(len(expected) == 30, "expected 30 identities")
    for row in expected:
        row["family_id"] = row["case_id"].rsplit(":", 1)[0]
        require(row["family_id"] == batch["family_binding"], "identity family")
    summary = load_json(batch_dir / "batch.json")
    manifest = load_json(batch_dir / "manifest.json")
    binding = load_json(batch_dir / "freeze_binding.json")
    control = load_json(batch_dir / "control.json")
    require(summary["schema"] == "la-family-batch-result/v1", "batch schema")
    require(summary["batch_id"] == BATCH_ID, "batch id")
    require(summary["freeze_sha256"] == freeze["freeze_sha256"] == binding["freeze_sha256"], "freeze")
    require(binding["schedule_identity_digest"] == freeze["schedule_identity_digest"], "schedule digest")
    require(binding["model_profile_sha256"] == freeze["model_profile_sha256"], "model profile")
    require(binding["prompt_profile_sha256"] == freeze["prompt_profile_sha256"], "prompt profile")
    require(binding["execution_profile"] == PROFILE_ID, "profile")
    require(binding["weights_sha256"] == model_profile["weights_sha256"], "weights")
    require(binding["runtime_driver_sha256"] == runtime["source_files"]["papers/completion/law_to_action/benchmark/generated_code_study/driver.py"], "driver")
    require(binding["runtime_handlers_sha256"] == runtime["source_files"]["papers/completion/law_to_action/benchmark/handlers/effects.py"], "handlers")
    require(binding["mock"] is False and binding["constructed_transport"] is False, "mock transport")
    require(binding["fixed_program_substituted"] is False and binding["scientific_execution"] is True, "scientific")
    require(binding["source_id"] == batch["source_id"] == summary["source_id"], "source")
    require(binding["family_binding"] == batch["family_binding"] == summary["family_binding"], "family")
    require(summary["mock"] is False and summary["constructed_outputs"] is False, "constructed batch")
    require(summary["fixed_program_substituted"] is False and summary["silent_replay"] is False, "replay")
    require(summary["paid_budget"] == PAID_BUDGET, "paid")
    pack = batch_dir / PACK
    require(pack.is_file(), "missing packed cell evidence")
    with tempfile.TemporaryDirectory(prefix="la033-cells-") as tmp_name:
        tmp = Path(tmp_name)
        materialize(pack, tmp)
        results = [verify_cell(tmp, control, row["attempt_id"], row, binding) for row in expected]
    require(len(results) == 30, "not 30 terminal records")
    require(set(manifest["cells"]) == {row["attempt_id"] for row in expected}, "manifest coverage")
    costs = [json.loads(line) for line in (batch_dir / "costs.jsonl").read_text().splitlines() if line]
    raw = [json.loads(line) for line in (batch_dir / "raw.jsonl").read_text().splitlines() if line]
    require(len(costs) == 30 and len(raw) == 30, "cost/raw ledgers")
    require({row["attempt_id"] for row in costs} == {row["attempt_id"] for row in expected}, "cost identities")
    require(all(row["unknown_costs"] is False and row["paid_budget"] == 0 for row in costs), "cost unknowns")
    if require_complete:
        require(summary["complete"] is True and summary["status"] == "COMPLETE", "incomplete")
        require(summary["terminal_cells"] == 30 and summary["admitted_cells"] == 30, "admitted")
        require(summary["planned_cells"] == 30, "planned")
        require(summary["scientific_wall_seconds"] <= 3600, "scientific wall")
        require(summary["model_calls"] == sum(row["model_calls"] for row in results), "model calls")
        require(summary["useful_work_cells"] == sum(1 for row in results if row.get("useful_work")), "useful-work count")
        require(
            summary["transport_failure_cells"]
            == sum(1 for row in results if row["terminal"] == "transport_or_format_failure"),
            "transport-failure count",
        )
        require(
            summary["candidate_failed_cells"]
            == sum(
                1
                for row in results
                if row["terminal"] == "candidate_failed"
                or any(item.get("terminal") == "candidate_failed" for item in row["iterations"])
            ),
            "candidate-failed count",
        )
    return {
        "status": "PASS",
        "batch_id": BATCH_ID,
        "terminal_cells": 30,
        "admitted_cells": 30,
        "useful_work_cells": summary["useful_work_cells"],
        "candidate_failed_cells": summary["candidate_failed_cells"],
        "transport_failure_cells": summary["transport_failure_cells"],
        "model_calls": summary["model_calls"],
        "complete": True,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--freeze", type=Path, required=True)
    parser.add_argument("--batch-task", required=True)
    parser.add_argument("--require-complete", action="store_true")
    args = parser.parse_args()
    require(args.batch_task == BATCH_ID, "unexpected batch task")
    freeze = load_json(args.freeze)
    require(freeze["schema"] == "la-closed-loop-study/v1", "freeze schema")
    require(freeze["freeze_sha256"] == "7822e0da434ec0e221b19a663e7ac0656b2f1af1c8f9a5911207e06afb048c8c", "freeze pin")
    print(json.dumps(verify(HERE, freeze, args.require_complete), sort_keys=True))


if __name__ == "__main__":
    main()
