"""Run the explicit pilot regression set without modifying preserved checkouts."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import time
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parent
TESTS = ["test_training_custody.py", "test_metadata_projections.py", "test_independent_training_review.py", "test_training_seal.py"]
SOURCES = [*TESTS, "train_codebase_ir.py", "metadata_projections.py", "independent_training_review.py",
           "env_run.py", "run_experiment.py", "run_tests.py", "verify_checkpoint_readback.py",
           "finalize_training_stage.py", "seal_training_evidence.py"]


def pins():
    return [{"path": str(ROOT / name), "sha256": hashlib.sha256((ROOT / name).read_bytes()).hexdigest()}
            for name in SOURCES]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--name", required=True)
    args = parser.parse_args()
    if not args.name or Path(args.name).name != args.name or args.name in {".", ".."}:
        raise ValueError("exclusive local report name required")
    xml = ROOT / (args.name + ".xml")
    if xml.exists():
        raise ValueError("test report already exists")
    before = pins()
    started = time.monotonic()
    with (ROOT / (args.name + ".log")).open("xb") as log:
        process = subprocess.run([sys.executable, "-B", "-m", "pytest", "-q", "-p", "no:cacheprovider",
            "--confcutdir", str(ROOT), "--junitxml", str(xml), *TESTS], cwd=ROOT,
            stdout=log, stderr=subprocess.STDOUT, timeout=180)
    counts = {key: 0 for key in ("tests", "failures", "errors", "skipped")}
    for suite in ET.parse(xml).getroot().iter("testsuite"):
        for key in counts:
            counts[key] += int(suite.get(key, "0"))
    after = pins()
    report = {"schema": "terminal-codebase-ir-training-tests@1", "exit_code": process.returncode,
        "counts": counts, "source_pins_before": before, "source_pins_after": after,
        "selected_sources_unchanged": before == after, "wall_seconds": time.monotonic() - started,
        "qualified": process.returncode == 0 and counts["tests"] > 0
            and not any(counts[k] for k in ("failures", "errors", "skipped")) and before == after}
    with (ROOT / (args.name + "-report.json")).open("x") as stream:
        json.dump(report, stream, indent=2, allow_nan=False)
        stream.write("\n")
    print(json.dumps({key: report[key] for key in ("exit_code", "counts", "selected_sources_unchanged", "qualified")}))
    raise SystemExit(0 if report["qualified"] else 1)


if __name__ == "__main__":
    main()
