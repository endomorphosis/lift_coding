"""Durable outer timing and failure retention around the owned public-model run."""
from pathlib import Path
import hashlib
import json
import os
import subprocess
import sys
import time
import traceback

BASE = Path(__file__).resolve().parent


def save(path, value):
    with path.open("xb") as stream:
        stream.write((json.dumps(value, sort_keys=True, indent=2) + "\n").encode())
        stream.flush()
        os.fsync(stream.fileno())


def main():
    start = time.monotonic()
    name = sys.argv[1]
    assert name.startswith("metrics-") and name[8:].isdigit()
    out = BASE / "outer" / name
    out.mkdir(parents=True, exist_ok=False)
    record = {"schema": "terminal-authored-reference-metrics-outer-attempt@1", "status": "started",
              "cleanup_errors": [], "training_calls": 0, "prover_calls": 0, "remote_mutations": 0}
    source = BASE / "run_owned.py"
    raw = source.read_bytes()
    producer = {"path": str(source), "bytes": len(raw), "sha256": hashlib.sha256(raw).hexdigest()}
    command = [sys.executable, "-B", str(source), name]
    save(out / "started.json", {"argv": command, "producer": producer, "outer_timeout_seconds": 120})
    child = None
    try:
        with (out / "stdout.log").open("xb") as output, (out / "stderr.log").open("xb") as errors:
            child = subprocess.Popen(command, stdout=output, stderr=errors, start_new_session=True)
            record["returncode"] = child.wait(timeout=120)
        assert source.read_bytes() == raw
        closed_path = BASE / "evidence" / name / "closed.json"
        body = closed_path.read_bytes()
        record["owned_closed"] = {"path": str(closed_path), "bytes": len(body), "sha256": hashlib.sha256(body).hexdigest()}
        record["owned_status"] = json.loads(body)["status"]
        record["status"] = "completed" if record["returncode"] == 0 else "failed_retained"
    except BaseException as problem:
        record.update(status="failed_retained", primary_error_type=type(problem).__name__, traceback=traceback.format_exc())
    finally:
        if child is not None and child.poll() is None:
            try:
                os.killpg(child.pid, 9)
                child.wait()
            except BaseException as problem:
                record["cleanup_errors"].append(type(problem).__name__)
        record["actual_outer_elapsed_seconds"] = time.monotonic() - start
        save(out / "closed.json", record)
    print(json.dumps(record))
    return 0 if record["status"] == "completed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
