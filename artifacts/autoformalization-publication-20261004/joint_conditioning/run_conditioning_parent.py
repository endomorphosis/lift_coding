"""Launch a pinned joint conditioning worker with independent parent bounds."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import signal
import subprocess
import time
from pathlib import Path


def binding(path):
    path = Path(path).absolute()
    data = path.read_bytes()
    return {"path": str(path), "bytes": len(data), "sha256": hashlib.sha256(data).hexdigest()}


def write(path, value):
    data = json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False).encode() + b"\n"
    with path.open("xb") as stream:
        os.chmod(path, 0o600)
        stream.write(data)
        stream.flush()
        os.fsync(stream.fileno())
    return binding(path)


def stop_group(process):
    """Also reap the direct child when a deadline or signal interrupts us."""
    try:
        os.killpg(process.pid, signal.SIGTERM)
    except ProcessLookupError:
        pass
    try:
        process.wait(timeout=3)
    except subprocess.TimeoutExpired:
        pass
    # A direct child can exit while leaving descendants in the same group.
    try:
        os.killpg(process.pid, signal.SIGKILL)
    except ProcessLookupError:
        pass
    process.wait(timeout=3)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--plan", type=Path, required=True)
    parser.add_argument("--plan-sha256", required=True)
    parser.add_argument("--worker", type=Path, required=True)
    parser.add_argument("--worker-sha256", required=True)
    parser.add_argument("--seed", type=int, choices=(1729, 1730, 1731), required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    plan_binding = binding(args.plan)
    if plan_binding["sha256"] != args.plan_sha256:
        raise ValueError("externally selected downstream plan differs")
    plan = json.loads(args.plan.read_bytes())
    worker_binding = binding(args.worker)
    if worker_binding != plan["helper_binding"] or worker_binding["sha256"] != args.worker_sha256:
        raise ValueError("externally selected downstream worker differs")
    output = args.output.absolute()
    if output.exists() or any(p.is_symlink() for p in (output, *output.parents)):
        raise ValueError("fresh nonsymlink parent output required")
    output.mkdir(mode=0o700)
    logs = output / "parent"
    logs.mkdir(mode=0o700)
    environment_overrides = {"CUDA_VISIBLE_DEVICES": "", "OMP_NUM_THREADS": "1", "OPENBLAS_NUM_THREADS": "1",
                             "MKL_NUM_THREADS": "1", "PYTHONDONTWRITEBYTECODE": "1", "HF_HUB_OFFLINE": "1", "TRANSFORMERS_OFFLINE": "1"}
    environment = {**os.environ, **environment_overrides}
    command = ["/home/barberb/.local/bin/python", "-I", "-B", worker_binding["path"], "--plan", plan_binding["path"],
               "--plan-sha256", args.plan_sha256, "--seed", str(args.seed), "--output", str(output / "worker")]
    selected = {"plan": plan_binding, "worker": worker_binding}
    if plan["schema"] != "source-only-joint-conditioning-plan/v1" or args.seed not in [row["seed"] for row in plan["baseline_receipts"]]:
        raise ValueError("selected downstream seed or plan schema differs")
    wall_limit = 180
    if plan["resource_limits"]["parent_wall_seconds"] != wall_limit:
        raise ValueError("selected parent wall bound differs")
    write(logs / "command.json", {"command": command, "selected": selected, "parent_wall_deadline_seconds": wall_limit,
                                   "environment_overrides": environment_overrides})
    stdout, stderr = logs / "worker.stdout", logs / "worker.stderr"
    process = None
    failure = None
    started = time.monotonic()
    previous_handlers = {}

    def interrupted(signum, _frame):
        raise KeyboardInterrupt("parent interrupted by signal " + str(signum))

    for signum in (signal.SIGTERM, signal.SIGINT):
        previous_handlers[signum] = signal.signal(signum, interrupted)
    try:
        with stdout.open("xb") as out, stderr.open("xb") as err:
            os.chmod(stdout, 0o600)
            os.chmod(stderr, 0o600)
            process = subprocess.Popen(command, stdout=out, stderr=err, env=environment, start_new_session=True)
            process.wait(timeout=wall_limit)
    except subprocess.TimeoutExpired:
        failure = "parent_wall_deadline_exceeded"
    except BaseException as error:
        failure = type(error).__name__ + ": " + str(error)
    finally:
        try:
            if process is not None:
                stop_group(process)
        except BaseException as error:
            failure = (failure + "; " if failure else "") + "cleanup_failed: " + type(error).__name__ + ": " + str(error)
        finally:
            for signum, previous in previous_handlers.items():
                signal.signal(signum, previous)
    try:
        unchanged = all(binding(value["path"]) == value for value in selected.values())
    except Exception as error:
        unchanged = False
        failure = (failure + "; " if failure else "") + "selected_input_recheck_failed: " + type(error).__name__ + ": " + str(error)
    succeeded = process is not None and process.returncode == 0 and failure is None and unchanged
    result = {"schema": "source-only-joint-conditioning-worker-parent/v1", "selected": selected, "seed": args.seed,
              "parent_wall_deadline_seconds": wall_limit, "wall_seconds": time.monotonic() - started,
              "returncode": process.returncode if process is not None else None, "failure": failure,
              "stdout_binding": binding(stdout) if stdout.exists() else None,
              "stderr_binding": binding(stderr) if stderr.exists() else None,
              "selected_inputs_unchanged": unchanged, "process_group_cleanup_attempted": process is not None,
              "succeeded": succeeded, "proof_or_semantic_qualification": False}
    result_binding = write(output / "parent-report.json", result)
    print(json.dumps({"succeeded": succeeded, "parent_report_binding": result_binding}), flush=True)
    if not succeeded:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
