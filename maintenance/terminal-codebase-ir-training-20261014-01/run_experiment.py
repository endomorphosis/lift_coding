"""Bound the complete experiment process and preserve explicit producer pins."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import signal
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parent
BASELINE = ROOT.parent / "terminal-dispatch-evidence-20261014-01" / "checkout"
DATASETS = ROOT.parent / "terminal-compact-retrieval-20261011-01" / "pinned-dependencies-v10" / "datasets" / "ipfs_datasets_py"
SELECTED = [ROOT / name for name in ("train_codebase_ir.py", "metadata_projections.py",
    "independent_training_review.py", "verify_checkpoint_readback.py", "env_run.py", "run_experiment.py",
    "corpus-manifest-01.json", "corpus-review-01.json")]
SELECTED += [DATASETS / name for name in (
    "logic/formalization/autoencoder/security/codebase_autoencoder.py",
    "logic/formalization/autoencoder/source_screening.py",
    "optimizers/logic_theorem_optimizer/modal_autoencoder_cuda.py",
    "optimizers/logic_theorem_optimizer/modal_autoencoder_batching.py",
    "ducklake/autoencoder_history.py")]
SELECTED += [BASELINE / name for name in (
    "ipfs_accelerate_py/agent_supervisor/analysis/program_ast_adapters.py",
    "ipfs_accelerate_py/agent_supervisor/runtime/semantic_context_runtime.py",
    "benchmarks/agent_supervisor/container_coding/terminal_codebase_logic_qualification.py",
    "benchmarks/agent_supervisor/container_coding/codebase_ir_metadata.py")]


def pins():
    result = []
    for path in SELECTED:
        if path.resolve(strict=True) != path or not path.is_file() or path.stat().st_nlink != 1:
            raise ValueError("selected producer aliased or not regular")
        body = path.read_bytes()
        result.append({"path": str(path), "bytes": len(body), "sha256": hashlib.sha256(body).hexdigest()})
    return result


def write(path, value):
    with path.open("x") as stream:
        json.dump(value, stream, indent=2, sort_keys=True, allow_nan=False)
        stream.write("\n")
        stream.flush()
        os.fchmod(stream.fileno(), 0o444)
        os.fsync(stream.fileno())


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--run", required=True)
    args = parser.parse_args()
    if not args.run or Path(args.run).name != args.run or args.run in {".", ".."}:
        raise ValueError("one fresh run name required")
    output = ROOT / args.run
    if output.exists():
        raise ValueError("experiment output already exists")
    before = pins()
    frozen = ROOT / (args.run + "-frozen-sources")
    frozen.mkdir(mode=0o700)
    copies = []
    for index, pin in enumerate(before):
        source = Path(pin["path"])
        body = source.read_bytes()
        if hashlib.sha256(body).hexdigest() != pin["sha256"] or len(body) != pin["bytes"]:
            raise ValueError("selected producer changed before frozen copy")
        target = frozen / (f"{index:03d}-" + source.name)
        with target.open("xb") as stream:
            stream.write(body)
            stream.flush()
            os.fchmod(stream.fileno(), 0o444)
            os.fsync(stream.fileno())
        copies.append({**pin, "retained_copy": str(target)})
    write(ROOT / (args.run + "-source-pins.json"), {"schema": "terminal-codebase-ir-selected-producer-pins@1",
        "pins": before, "retained_producer_copies": copies, "complete_transitive_dependency_closure": False})
    started = time.monotonic()
    timed_out = False
    with (ROOT / (args.run + "-stdout.log")).open("xb") as stdout, (ROOT / (args.run + "-stderr.log")).open("xb") as stderr:
        process = subprocess.Popen([sys.executable, "-B", str(ROOT / "env_run.py"),
            "train_codebase_ir.py", "--output", str(output)], cwd=ROOT,
            stdout=stdout, stderr=stderr, start_new_session=True)
        try:
            code = process.wait(timeout=300)
        except subprocess.TimeoutExpired:
            timed_out = True
            os.killpg(process.pid, signal.SIGKILL)
            code = process.wait(timeout=10)
    after = pins()
    report = {"schema": "terminal-codebase-ir-experiment-process@1", "run": args.run,
        "exit_code": code, "timed_out": timed_out, "outer_deadline_seconds": 300,
        "whole_process_wall_seconds": time.monotonic() - started, "selected_sources_unchanged": before == after,
        "before": before, "after": after, "qualified_process_completion": code == 0 and not timed_out and before == after}
    write(ROOT / (args.run + "-process-report.json"), report)
    print(json.dumps({key: report[key] for key in ("run", "exit_code", "timed_out",
        "whole_process_wall_seconds", "selected_sources_unchanged", "qualified_process_completion")}))
    raise SystemExit(0 if report["qualified_process_completion"] else 1)


if __name__ == "__main__":
    main()
