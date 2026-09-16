#!/usr/bin/python3.12
"""Read-only packing verifier for LA-031.

Requires all 30 family batches to dedicated-verify PASS (900 child cells) and
the analysis freeze document. Does not execute inference. Parent claims 0 cells.
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
BATCHES = tuple(f"LA-{n:03d}" for n in range(33, 63))


def fail(message: str) -> int:
    print("FAIL: " + message)
    return 2


def load_json(path: Path) -> dict:
    return json.loads(path.read_text())


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--study", type=Path, required=True)
    parser.add_argument("--results", type=Path, required=True)
    args = parser.parse_args()
    study = args.study.resolve()
    results = args.results.resolve()
    freeze = load_json(study)
    freeze_path = HERE / "prospective_study.json"
    if study != freeze_path.resolve() and freeze_path.is_file():
        bound = load_json(freeze_path)
        if bound.get("freeze_sha256") != freeze.get("freeze_sha256"):
            return fail("study freeze_sha256 differs from committed prospective_study.json")
    analysis_path = HERE / "analysis_freeze.json"
    if not analysis_path.is_file():
        return fail("missing analysis_freeze.json")
    analysis = load_json(analysis_path)
    if analysis.get("tiny_byte_lm") is True:
        return fail("tiny-byte-lm freeze")
    admitted = 0
    useful = 0
    failed = 0
    transport = 0
    for bid in BATCHES:
        dest = results / "batches" / bid
        proc = subprocess.run(
            [
                sys.executable,
                "-B",
                str(HERE / "verify_batch.py"),
                "--freeze",
                str(study),
                "--batch-task",
                bid,
                "--require-complete",
                "--results",
                str(dest),
            ],
            check=False,
            capture_output=True,
            text=True,
        )
        if proc.returncode != 0:
            return fail(bid + " verify_batch did not PASS: " + (proc.stdout or proc.stderr)[-400:])
        summary = load_json(dest / "batch.json")
        if summary.get("tiny_byte_lm") is True:
            return fail(bid + " tiny-byte-lm")
        if int(summary.get("admitted_cells") or 0) != 30:
            return fail(bid + " admitted_cells is not 30")
        if int(summary.get("transport_failure_cells") or 0) != 0:
            return fail(bid + " transport failures")
        admitted += int(summary["admitted_cells"])
        useful += int(summary.get("useful_work_cells") or 0)
        failed += int(summary.get("candidate_failed_cells") or 0)
        transport += int(summary.get("transport_failure_cells") or 0)
    if admitted != 900:
        return fail("child admitted_cells is not 900")
    payload = {
        "status": "PASS",
        "parent_task": "LA-031",
        "parent_cells_claimed": 0,
        "child_batches": 30,
        "child_admitted_cells": admitted,
        "useful_work_cells": useful,
        "candidate_failed_cells": failed,
        "transport_failure_cells": transport,
        "tiny_byte_lm": False,
        "analysis_freeze": True,
        "scientific_inference_allowed": analysis.get("scientific_inference_allowed"),
    }
    print(json.dumps(payload, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
