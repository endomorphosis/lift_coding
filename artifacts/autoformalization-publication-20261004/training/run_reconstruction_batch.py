"""Run nine frozen CPU reconstruction arms with independent parent wall bounds."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import signal
import subprocess
import time
from pathlib import Path

BASE = Path(__file__).resolve().parents[1]
LAUNCHER = BASE / "huggingface/launch_reconstruction.py"
LAUNCHER_SHA = "910ff61a235d6e988e78b34a3b27d7ae7520f2bb10722881ab532c934be1199e"
PLAN = BASE / "training/run-plan-02.json"
PLAN_SHA = "b02b0b35a9f2d82abd5422643f9034bea30e1d83f0c21772aa0a609c234ead3b"


def bound(path):
    data = path.read_bytes()
    return {"path": str(path), "bytes": len(data), "sha256": hashlib.sha256(data).hexdigest()}


def save(path, value):
    with path.open("xb") as stream:
        os.chmod(path, 0o600)
        stream.write(json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False).encode() + b"\n")
        stream.flush()
        os.fsync(stream.fileno())
    return bound(path)


def stop(process):
    try:
        os.killpg(process.pid, signal.SIGTERM)
        process.wait(timeout=3)
    except ProcessLookupError:
        process.wait()
    except subprocess.TimeoutExpired:
        os.killpg(process.pid, signal.SIGKILL)
        process.wait(timeout=3)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--publication-gate", type=Path, required=True)
    parser.add_argument("--publication-gate-sha256", required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    selected = {"launcher": bound(LAUNCHER), "plan": bound(PLAN), "gate": bound(args.publication_gate)}
    if (selected["launcher"]["sha256"], selected["plan"]["sha256"], selected["gate"]["sha256"]) != (
            LAUNCHER_SHA, PLAN_SHA, args.publication_gate_sha256):
        raise ValueError("externally selected launcher, plan or publication gate differs")
    if args.output.exists():
        raise ValueError("fresh batch output required")
    args.output.mkdir(parents=True, mode=0o700)
    logs = args.output / "parent"
    logs.mkdir(mode=0o700)
    environment = {**os.environ, "CUDA_VISIBLE_DEVICES": "", "OMP_NUM_THREADS": "1",
                   "OPENBLAS_NUM_THREADS": "1", "MKL_NUM_THREADS": "1", "PYTHONDONTWRITEBYTECODE": "1"}
    records = []
    for lane in ("legacy8", "native384", "native768"):
        for seed in (1729, 1730, 1731):
            name = lane + "-seed" + str(seed)
            command = ["/home/barberb/.local/bin/python", "-I", "-B", str(LAUNCHER), "--lane", lane,
                       "--seed", str(seed), "--output-directory", str(args.output / name),
                       "--publication-gate", str(args.publication_gate),
                       "--publication-gate-sha256", args.publication_gate_sha256]
            save(logs / (name + "-command.json"), {"command": command, "selected": selected,
                 "parent_wall_deadline_seconds": 120, "environment_overrides": {key: environment[key] for key in
                 ("CUDA_VISIBLE_DEVICES", "OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS", "PYTHONDONTWRITEBYTECODE")}})
            print(json.dumps({"arm": name, "status": "starting"}), flush=True)
            process = None
            started = time.monotonic()
            failure = None
            stdout = logs / (name + ".stdout")
            stderr = logs / (name + ".stderr")
            try:
                with stdout.open("xb") as out, stderr.open("xb") as err:
                    os.chmod(stdout, 0o600)
                    os.chmod(stderr, 0o600)
                    process = subprocess.Popen(command, stdout=out, stderr=err, env=environment, start_new_session=True)
                    process.wait(timeout=120)
            except subprocess.TimeoutExpired:
                failure = "parent_wall_deadline_exceeded"
                stop(process)
            except BaseException as error:
                if process is not None and process.poll() is None:
                    stop(process)
                failure = type(error).__name__ + ": " + str(error)
                if isinstance(error, KeyboardInterrupt | SystemExit):
                    save(logs / (name + "-interrupted.json"), {"failure": failure, "seconds": time.monotonic() - started})
                    raise
            result_path = args.output / name / "training-report.json"
            record = {"arm": name, "lane": lane, "seed": seed, "returncode": process.returncode if process is not None else None,
                      "failure": failure, "seconds": time.monotonic() - started,
                      "stdout": bound(stdout) if stdout.exists() else None, "stderr": bound(stderr) if stderr.exists() else None,
                      "report_binding": bound(result_path) if result_path.exists() else None}
            record["succeeded"] = record["returncode"] == 0 and failure is None and record["report_binding"] is not None
            records.append(record)
            save(logs / (name + "-result.json"), record)
            print(json.dumps({key: record[key] for key in ("arm", "succeeded", "seconds", "failure")}), flush=True)
    unchanged = all(bound(Path(value["path"])) == value for value in selected.values())
    summary = {"schema": "nine-arm-source-reconstruction-parent/v1", "selected": selected,
               "arms": records, "successful_arms": sum(record["succeeded"] for record in records),
               "selected_inputs_unchanged": unchanged, "parent_wall_bound_seconds_per_arm": 120,
               "proof_or_semantic_qualification": False}
    print(json.dumps({"summary_binding": save(args.output / "batch-report.json", summary)}), flush=True)
    if summary["successful_arms"] != 9 or not unchanged:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
