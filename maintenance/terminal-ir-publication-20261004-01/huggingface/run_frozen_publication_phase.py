"""Durable wrapper for one frozen archive classification or publication phase."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import signal
import stat
import subprocess
import sys
import time


def pin(path):
    path = Path(path).absolute()
    fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW)
    try:
        before = os.fstat(fd)
        if not stat.S_ISREG(before.st_mode):
            raise ValueError("wrapper input is not a regular file")
        digest = hashlib.sha256()
        size = 0
        while block := os.read(fd, 8 * 1024**2):
            digest.update(block)
            size += len(block)
        after = os.fstat(fd)
        identity = lambda s: (s.st_dev, s.st_ino, s.st_size, s.st_mtime_ns)
        if identity(before) != identity(after) or identity(after) != identity(path.stat()):
            raise ValueError("wrapper input changed during read")
        return {"path": str(path), "bytes": size, "sha256": digest.hexdigest()}
    finally:
        os.close(fd)


def save(path, value):
    with path.open("xb") as stream:
        stream.write((json.dumps(value, sort_keys=True, allow_nan=False) + "\n").encode())
        stream.flush()
        os.fsync(stream.fileno())


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--invocation", type=Path, required=True)
    parser.add_argument("--expected-invocation-sha256", required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    start = time.monotonic()
    output = args.output.absolute()
    output.mkdir(parents=True, exist_ok=False)
    state = {"schema": "terminal-ir-frozen-publication-phase-outer-attempt@1",
             "status": "started", "started_wall_time": time.time(),
             "returncode": None, "primary_error_type": None,
             "cleanup_errors": [], "complete_descendant_cleanup_qualified": False,
             "enclosing_invocation_before_wrapper_main_elapsed_seconds": None}
    child = None
    expected = None
    primary = None
    save(output / "started.json", state)
    try:
        invocation_pin = pin(args.invocation)
        if invocation_pin["sha256"] != args.expected_invocation_sha256:
            raise ValueError("invocation digest mismatch")
        invocation_bytes = args.invocation.read_bytes()
        if len(invocation_bytes) != invocation_pin["bytes"] or hashlib.sha256(invocation_bytes).hexdigest() != invocation_pin["sha256"]:
            raise ValueError("invocation bytes changed after pin")
        invocation = json.loads(invocation_bytes)
        if invocation["schema"] != "terminal-ir-frozen-publication-phase-invocation@1":
            raise ValueError("invocation schema mismatch")
        argv = invocation["argv"]
        if not isinstance(argv, list) or not argv or not all(isinstance(x, str) for x in argv):
            raise ValueError("invalid argument vector")
        expected = invocation["pinned_inputs"]
        if not isinstance(expected, list) or not expected:
            raise ValueError("missing expected input pins")
        before = [pin(item["path"]) for item in expected]
        if before != expected:
            raise ValueError("phase expected input pin mismatch")
        state["phase"] = invocation["phase"]
        state["remote_mutation_scope"] = invocation["remote_mutation_scope"]
        save(output / "invocation.json", {"argv": argv, "wrapper": pin(__file__),
             "frozen_invocation": invocation_pin, "requested_wall_seconds": invocation["wall_seconds"]})
        save(output / "inputs-before.json", before)
        with (output / "stdout.log").open("xb") as stdout, (output / "stderr.log").open("xb") as stderr:
            child = subprocess.Popen(argv, stdout=stdout, stderr=stderr, start_new_session=True,
                                     cwd=invocation["cwd"])
            state["child_pid"] = child.pid
            state["returncode"] = child.wait(timeout=invocation["wall_seconds"] + 60)
        state["status"] = "closed_phase" if state["returncode"] == 0 else "failed_phase_preserved"
    except BaseException as error:
        primary = error
        state["primary_error_type"] = type(error).__name__
        state["status"] = "failed_outer_preserved"
        if child is not None and child.poll() is None:
            try:
                os.killpg(child.pid, signal.SIGTERM)
                try:
                    child.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    os.killpg(child.pid, signal.SIGKILL)
                    child.wait()
            except ProcessLookupError:
                child.wait()
            except BaseException as cleanup:
                state["cleanup_errors"].append({"operation": "own_child_process_group", "error_type": type(cleanup).__name__})
            state["returncode"] = child.returncode
    finally:
        if expected is not None:
            try:
                after = [pin(item["path"]) for item in expected]
                save(output / "inputs-after.json", after)
                state["input_pins_unchanged"] = after == expected
                if after != expected:
                    state["status"] = "failed_input_drift_preserved"
            except BaseException as error:
                state["final_input_check_error_type"] = type(error).__name__
                state["status"] = "failed_input_check_preserved"
        state["elapsed_seconds"] = time.monotonic() - start
        save(output / "closed.json", state)
    if primary is not None:
        raise primary
    return state["returncode"] if state["status"] == "closed_phase" else (state["returncode"] or 1)


if __name__ == "__main__":
    raise SystemExit(main())
