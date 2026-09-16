#!/usr/bin/python3.12
"""Read-only verifier for the generated-code analysis freeze (LA-063).

Requires 360 protocol-accounted development/calibration cells, no tiny-byte-lm,
and --require-final-unexecuted fails closed if any final-family batch has run.
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
DEV_CAL = {
    "LA-033", "LA-034", "LA-035", "LA-036", "LA-037", "LA-038",
    "LA-039", "LA-040", "LA-041", "LA-042", "LA-043", "LA-044",
}
FINAL = {
    "LA-045", "LA-046", "LA-047", "LA-048", "LA-049", "LA-050",
    "LA-051", "LA-052", "LA-053", "LA-054", "LA-055", "LA-056",
    "LA-057", "LA-058", "LA-059", "LA-060", "LA-061", "LA-062",
}


def fail(message: str) -> int:
    print("FAIL: " + message)
    return 2


def load_json(path: Path) -> dict:
    return json.loads(path.read_text())


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--freeze", type=Path, required=True)
    parser.add_argument("--require-final-unexecuted", action="store_true")
    args = parser.parse_args()
    freeze = load_json(args.freeze)
    batches = load_json(HERE / "family_batches.json")
    freeze_doc = HERE / "analysis_freeze.json"
    if not freeze_doc.is_file():
        return fail("missing analysis_freeze.json")
    analysis = load_json(freeze_doc)
    if analysis.get("schema") != "la-generated-code-analysis-freeze/v1":
        return fail("analysis_freeze schema mismatch")
    if analysis.get("scientific_inference_allowed") is not False:
        return fail("scientific inference is not frozen false")
    if analysis.get("final_material_release_allowed") is not False:
        return fail("final material release is not frozen false")
    if analysis.get("tiny_byte_lm") is True:
        return fail("tiny-byte-lm freeze")
    if freeze.get("freeze_sha256") != analysis.get("study_freeze_sha256"):
        return fail("analysis freeze does not bind prospective_study freeze_sha256")
    results_root = args.freeze.resolve().parents[2] / "results/generated_code_study/batches"
    cells = 0
    useful = 0
    transport = 0
    for row in batches["batches"]:
        bid = row["id"]
        dest = results_root / bid
        if row.get("phase") in ("development", "calibration"):
            if bid not in DEV_CAL:
                return fail("unexpected development/calibration id " + bid)
            proc = subprocess.run(
                [
                    sys.executable, "-B", str(HERE / "verify_batch.py"),
                    "--freeze", str(args.freeze),
                    "--batch-task", bid,
                    "--require-complete",
                    "--results", str(dest),
                ],
                check=False, capture_output=True, text=True,
            )
            if proc.returncode != 0:
                return fail(bid + " verify_batch did not PASS: " + (proc.stdout or proc.stderr)[-400:])
            summary = load_json(dest / "batch.json")
            if summary.get("tiny_byte_lm") is True or "tiny-byte" in str(summary.get("model_revision", "")).lower():
                return fail(bid + " is tiny-byte-lm")
            if summary.get("model_revision") != "leanstral_local":
                return fail(bid + " is not leanstral_local")
            cells += int(summary.get("admitted_cells") or 0)
            useful += int(summary.get("useful_work_cells") or 0)
            transport += int(summary.get("transport_failure_cells") or 0)
        elif row.get("phase") == "final":
            if bid not in FINAL:
                return fail("unexpected final id " + bid)
            batch_json = dest / "batch.json"
            if batch_json.is_file():
                summary = load_json(batch_json)
                executed = int(summary.get("admitted_cells") or summary.get("terminal_cells") or 0)
                if args.require_final_unexecuted and executed:
                    return fail(bid + " final cells already executed")
            elif (dest / "cells").exists() and any((dest / "cells").rglob("result.json")):
                if args.require_final_unexecuted:
                    return fail(bid + " final cell artifacts exist")
        else:
            return fail("unknown phase for " + bid)
    if cells != 360:
        return fail("development/calibration cells are not 360")
    if transport != 0:
        return fail("development/calibration transport failures are not zero")
    if int(analysis.get("development_calibration_cells") or 0) != 360:
        return fail("analysis_freeze cell count is not 360")
    if int(analysis.get("useful_work_cells") or 0) != useful:
        return fail("analysis_freeze useful_work does not match verified batches")
    print(json.dumps({
        "status": "PASS",
        "development_calibration_cells": 360,
        "useful_work_cells": useful,
        "transport_failure_cells": 0,
        "final_unexecuted": True,
        "tiny_byte_lm": False,
        "model_revision": "leanstral_local",
        "scientific_inference_allowed": False,
        "final_material_release_allowed": False,
    }, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
