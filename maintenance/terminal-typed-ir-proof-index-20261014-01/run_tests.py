"""Explicit native-IR, model-checker, grounding and cache regression selection."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import time
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parent
TESTS = ["test_native_structural_ir.py", "test_align_projection.py", "test_intent_structural_grounding.py", "test_proof_index.py", "test_scheduler_overlay.py", "test_result_scope.py"]
SOURCES = [*TESTS, "native_structural_ir.py", "align_projection.py", "intent_structural_grounding.py",
    "proof_index.py", "run_successor.py", "run_experiment.py", "run_tests.py", "env_run.py",
    "scheduler_overlay.py", "launch.py", "verify_successor.py", "run_native_faults.py"]


def pins():
    return [{"path": str(ROOT / name), "sha256": hashlib.sha256((ROOT / name).read_bytes()).hexdigest()}
            for name in SOURCES]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--name", required=True)
    args = parser.parse_args()
    if not args.name or Path(args.name).name != args.name or args.name in {".", ".."}:
        raise ValueError("one exclusive local report name required")
    xml = ROOT / (args.name + ".xml")
    if xml.exists():
        raise ValueError("test namespace already exists")
    before = pins()
    started = time.monotonic()
    with (ROOT / (args.name + ".log")).open("xb") as log:
        run = subprocess.run([sys.executable, "-B", str(ROOT / "launch.py"), "--module", "pytest", "-q", "-p", "no:cacheprovider",
            "--confcutdir", str(ROOT), "--junitxml", str(xml), *TESTS], cwd=ROOT,
            stdout=log, stderr=subprocess.STDOUT, timeout=240)
    counts = {key: 0 for key in ("tests", "failures", "errors", "skipped")}
    cases = []
    tree = ET.parse(xml).getroot()
    for suite in tree.iter("testsuite"):
        for key in counts:
            counts[key] += int(suite.get(key, "0"))
    for case in tree.iter("testcase"):
        cases.append(case.get("classname", "") + "::" + case.get("name", ""))
    after = pins()
    qualified = run.returncode == 0 and counts["tests"] > 0 and before == after and len(cases) == len(set(cases))
    qualified &= not any(counts[key] for key in ("failures", "errors", "skipped"))
    report = {"schema": "terminal-typed-ir-proof-tests@1", "exit_code": run.returncode,
        "counts": counts, "unique_case_count": len(set(cases)), "qualified": qualified,
        "selected_sources_unchanged": before == after, "before": before, "after": after,
        "seconds": time.monotonic() - started}
    with (ROOT / (args.name + "-report.json")).open("x") as stream:
        json.dump(report, stream, indent=2, allow_nan=False)
        stream.write("\n")
    print(json.dumps({key: report[key] for key in ("counts", "qualified", "selected_sources_unchanged")}))
    raise SystemExit(0 if qualified else 1)


if __name__ == "__main__":
    main()
