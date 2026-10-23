"""Freeze explicit producers and bound the complete successor process group."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import signal
import subprocess
import sys
import time

from run_successor import ROOT, PRIOR, BASELINE, DATASETS, pin
from train_codebase_ir import read, write

SELECTED = [ROOT / name for name in ("env_run.py", "run_successor.py", "run_experiment.py",
    "native_structural_ir.py", "align_projection.py", "intent_structural_grounding.py", "proof_index.py",
    "scheduler_overlay.py", "launch.py", "verify_successor.py", "run_native_faults.py",
    "native-policy-overlay-01/source-pins.json", "native-policy-overlay-01/proof_resource_safety.py",
    "native-policy-overlay-01/resource_scheduler.py")]
SELECTED += [PRIOR / name for name in ("corpus-manifest-01.json", "evidence-manifest.json",
    "train_codebase_ir.py", "metadata_projections.py")]
SELECTED += [DATASETS / name for name in ("logic/software_contracts/codebase_ir.py",
    "logic/software_contracts/semantic_index/snapshot.py", "logic/software_contracts/duckdb_ast_store.py",
    "logic/software_contracts/duckdb_ingest.py", "logic/software_contracts/cache.py", "logic/software_contracts/codebase_resources.py",
    "duckdb_control/codebase_catalog.py", "logic/software_verification/codebase_source_adapters.py",
    "logic/software_verification/program.py", "logic/intent_ir/formalize/requirements.py",
    "logic/backends/process.py")]
SELECTED += [BASELINE / name for name in ("ipfs_accelerate_py/agent_supervisor/prompt/intent_plan_coverage.py",
    "benchmarks/agent_supervisor/container_coding/codebase_ir_metadata.py")]


def pins():
    return [pin(path) for path in SELECTED]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--run", required=True)
    args = parser.parse_args()
    if not args.run or Path(args.run).name != args.run or args.run in {".", ".."}:
        raise ValueError("one fresh experiment name required")
    if (ROOT / args.run).exists():
        raise ValueError("experiment namespace already exists")
    before = pins()
    frozen = ROOT / (args.run + "-frozen-sources")
    frozen.mkdir(mode=0o700)
    retained = []
    for ordinal, entry in enumerate(before):
        body = read(Path(entry["path"]), 32_000_000)
        if hashlib.sha256(body).hexdigest() != entry["sha256"]:
            raise ValueError("producer changed before immutable copy")
        target = frozen / (f"{ordinal:03d}-" + Path(entry["path"]).name)
        with target.open("xb") as stream:
            stream.write(body)
            stream.flush()
            os.fchmod(stream.fileno(), 0o444)
            os.fsync(stream.fileno())
        retained.append({**entry, "retained_copy": str(target)})
    write(ROOT / (args.run + "-source-pins.json"), {"schema": "typed-ir-proof-producer-freeze@1",
        "pins": before, "retained_copies": retained, "complete_transitive_loaded_code_closure": False})
    started = time.monotonic()
    timed_out = False
    with (ROOT / (args.run + "-stdout.log")).open("xb") as stdout, (ROOT / (args.run + "-stderr.log")).open("xb") as stderr:
        process = subprocess.Popen([sys.executable, "-B", str(ROOT / "env_run.py"), "run_successor.py",
            "--output", str(ROOT / args.run)], cwd=ROOT, stdout=stdout, stderr=stderr, start_new_session=True)
        try:
            code = process.wait(timeout=300)
        except subprocess.TimeoutExpired:
            timed_out = True
            os.killpg(process.pid, signal.SIGKILL)
            code = process.wait(timeout=10)
    after = pins()
    report = {"schema": "typed-ir-proof-native-process@1", "run": args.run, "exit_code": code,
        "timed_out": timed_out, "whole_process_seconds": time.monotonic() - started,
        "outer_deadline_seconds": 300, "selected_sources_unchanged": before == after,
        "qualified": code == 0 and not timed_out and before == after, "before": before, "after": after}
    write(ROOT / (args.run + "-process-report.json"), report)
    print(json.dumps({key: report[key] for key in ("run", "exit_code", "timed_out", "whole_process_seconds",
        "selected_sources_unchanged", "qualified")}))
    raise SystemExit(0 if report["qualified"] else 1)


if __name__ == "__main__":
    main()
