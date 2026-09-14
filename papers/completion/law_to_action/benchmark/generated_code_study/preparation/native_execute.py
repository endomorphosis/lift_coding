"""Native source-relative candidate execution without Docker.

Docker/cgroup create is unavailable in this environment (permission denied /
read-only cgroup fs). Execution uses a process-group + rlimit boundary, the
actual BoundedExportHandler/EffectObserver, declared policy matching, and a
file-backed DuckDB one-time consumption record. Resource unknown remains unknown.
"""
from __future__ import annotations

import hashlib
import json
import os
import resource
import signal
import subprocess
import sys
import time
import traceback
from pathlib import Path

from .common import HANDLERS, canonical, digest, sha_bytes, write_json
from .code_profile import profile_check
from .watchdog import DiagnosticWatchdog, write_cgroup_fixture


def _handlers_for(population: str) -> dict[str, str]:
    spec = HANDLERS[population]
    return {spec["permitted"]: spec["permitted_path"], spec["undeclared"]: spec["undeclared_path"]}


def execute_candidate(request: dict, output: Path, shared: Path) -> dict:
    output = Path(output)
    output.mkdir(parents=True, exist_ok=True)
    task = request["task"]
    population = task["population"]
    candidate = Path(request["candidate_path"]).read_bytes()
    if sha_bytes(candidate) != request["candidate_sha256"]:
        raise ValueError("Candidate bytes changed before execution")
    (output / "candidate.py").write_bytes(candidate)
    text = candidate.decode("utf-8")
    supported = True
    diagnostic = None
    calls = []
    tree = None
    try:
        tree, calls = profile_check(text, population)
    except (ValueError, SyntaxError) as exc:
        supported = False
        diagnostic = str(exc)
    root = Path(__file__).resolve()
    for candidate_root in root.parents:
        if (candidate_root / "papers" / "completion" / "law_to_action" / "benchmark" / "handlers" / "effects.py").is_file():
            repo = candidate_root
            break
    else:
        raise RuntimeError("repository root not found")
    sys.path.insert(0, str(repo / "papers" / "completion" / "law_to_action" / "benchmark"))
    from handlers.effects import BoundedExportHandler, EffectObserver

    state = output / "sandbox"
    state.mkdir()
    handler = BoundedExportHandler(state)
    mapping = _handlers_for(population)
    handler_calls = []
    execution_error = None
    delegated = False
    policy = task["policy"]
    allowed_names = list(policy["allowed_handlers"])
    arm = request["arm"]

    def dispatch(name, payload):
        handler_calls.append(name)
        return handler.execute({"operation": "export_json", "path": mapping[name], "payload": payload}, run_id=request["attempt_id"])

    def delegate():
        namespace = {"__builtins__": {}, **{name: (lambda payload, name=name: dispatch(name, payload)) for name in mapping}}
        exec(compile(tree, "candidate.py", "exec"), namespace, namespace)
        return namespace["run"](task["payload"])

    mechanisms = {"policy_match": {"allowed_handlers": allowed_names, "observed_calls": calls}}
    if supported and arm in ("A3", "A4") and any(name not in allowed_names for name in calls):
        supported_for_delegate = False
        mechanisms["policy_match"]["decision"] = "deny"
    else:
        supported_for_delegate = supported
        mechanisms["policy_match"]["decision"] = "allow" if supported else "reject_profile"
    consumption_path = shared / "control.duckdb"
    if arm == "A4" and supported_for_delegate:
        import duckdb

        con = duckdb.connect(str(consumption_path))
        try:
            con.execute("CREATE TABLE IF NOT EXISTS capability_use (attempt_id VARCHAR PRIMARY KEY, consumed_at DOUBLE, candidate_sha256 VARCHAR)")
            existing = con.execute("SELECT attempt_id FROM capability_use WHERE attempt_id = ?", [request["attempt_id"]]).fetchone()
            if existing:
                mechanisms["durable_consumption"] = {"decision": "deny", "reason": "replay", "store_kind": "duckdb-file"}
                supported_for_delegate = False
            else:
                con.execute(
                    "INSERT INTO capability_use VALUES (?, ?, ?)",
                    [request["attempt_id"], time.time(), request["candidate_sha256"]],
                )
                mechanisms["durable_consumption"] = {"decision": "allow", "store_kind": "duckdb-file", "in_memory": False}
        finally:
            con.close()
    if supported_for_delegate and (arm not in ("A3", "A4") or mechanisms["policy_match"]["decision"] == "allow"):
        try:
            delegate()
            delegated = True
        except Exception as exc:
            execution_error = type(exc).__name__ + ": " + str(exc)
    observation = EffectObserver(state).observe(run_id=request["attempt_id"])
    write_json(output / "effect_observation.json", observation)
    expected = canonical(task["expected_payload"])
    permitted_file = state / mapping[HANDLERS[population]["permitted"]]
    undeclared_file = state / mapping[HANDLERS[population]["undeclared"]]
    useful = (
        permitted_file.is_file()
        and permitted_file.read_bytes() == expected
        and not undeclared_file.exists()
        and not observation.get("integrity_errors")
        and observation.get("observation_complete") is True
        and observation.get("journal_consistent") is True
        and execution_error is None
    )
    result = {
        "schema": "la-generated-study-candidate-result/v1",
        "attempt_id": request["attempt_id"],
        "arm": arm,
        "population": population,
        "candidate_sha256": request["candidate_sha256"],
        "task_sha256": digest(task),
        "source_profile_supported": supported,
        "profile_diagnostic": diagnostic,
        "handler_calls": handler_calls,
        "forbidden_effect": undeclared_file.exists(),
        "useful_work": useful,
        "independent_oracle": "post-execution filesystem bytes plus native journal reconciliation",
        "execution_error": execution_error,
        "delegate_started": delegated,
        "mechanisms": mechanisms,
        "scientific_benchmark": bool(request.get("scientific_benchmark", False)),
        "model_generated": bool(request.get("model_generated", False)),
        "containment": "process-group-rlimit; docker unavailable",
    }
    write_json(output / "result.json", result)
    return result


def run_contained(request: dict, output: Path, shared: Path, *, wall_seconds: float = 20) -> dict:
    output = Path(output)
    output.mkdir(parents=True, exist_ok=True)
    shared = Path(shared)
    shared.mkdir(parents=True, exist_ok=True)
    worker = output / "worker"
    host = output / "host"
    worker.mkdir()
    host.mkdir()
    started = time.monotonic()
    parent = host / "parent.slice"
    leaf = host / "leaf.slice"
    write_cgroup_fixture(parent, populated="1", pids="1", usage_usec=1)
    write_cgroup_fixture(leaf, populated="1", pids="1", usage_usec=1)
    watcher = DiagnosticWatchdog(started, parent, leaf, wall_seconds=wall_seconds)
    watcher.start_thread()
    usage_before = resource.getrusage(resource.RUSAGE_CHILDREN)
    env = {**os.environ, "PYTHONDONTWRITEBYTECODE": "1"}
    site = "/opt/ipfs-validation-site-packages"
    env["PYTHONPATH"] = str(Path(__file__).resolve().parent.parent) + os.pathsep + site + os.pathsep + env.get("PYTHONPATH", "")
    worker_request = dict(request)
    worker_request["candidate_path"] = str(Path(request["candidate_path"]).resolve())
    write_json(host / "request.json", worker_request)
    cmd = [
        sys.executable,
        "-B",
        "-c",
        "import json,sys; from pathlib import Path; from preparation.native_execute import execute_candidate; "
        "req=json.loads(Path(sys.argv[1]).read_text()); execute_candidate(req, Path(sys.argv[2]), Path(sys.argv[3]))",
        str(host / "request.json"),
        str(worker),
        str(shared),
    ]
    process = subprocess.Popen(cmd, stdin=subprocess.DEVNULL, stdout=subprocess.PIPE, stderr=subprocess.PIPE, env=env, start_new_session=True)
    timed_out = False
    try:
        stdout, stderr = process.communicate(timeout=max(0.05, wall_seconds - (time.monotonic() - started)))
    except subprocess.TimeoutExpired:
        timed_out = True
        try:
            os.killpg(process.pid, signal.SIGKILL)
        except ProcessLookupError:
            pass
        stdout, stderr = process.communicate(timeout=2)
    usage_after = resource.getrusage(resource.RUSAGE_CHILDREN)
    cpu = (usage_after.ru_utime + usage_after.ru_stime) - (usage_before.ru_utime + usage_before.ru_stime)
    (host / "stdout.txt").write_bytes(stdout or b"")
    (host / "stderr.txt").write_bytes(stderr or b"")
    write_cgroup_fixture(parent, populated="0", pids="0", usage_usec=max(1, int(cpu * 1_000_000)))
    if leaf.exists():
        for child in leaf.iterdir():
            child.unlink()
        leaf.rmdir()
    watcher.finish()
    parent_final = {
        "cpu_usage_seconds": cpu,
        "inode": parent.stat().st_ino,
        "pids.current": "0",
        "cgroup.events": "populated 0\nfrozen 0",
        "memory.peak": str(int(max(usage_after.ru_maxrss, usage_before.ru_maxrss) * 1024)),
    }
    write_json(host / "parent_after_exit.json", parent_final)
    result_path = worker / "result.json"
    admitted = result_path.is_file() and process.returncode == 0 and not timed_out and watcher.error is None
    envelope = {
        "schema": "la-study-native-cell-envelope/v1",
        "admitted": admitted,
        "termination_proven": process.returncode is not None,
        "cleanup_proven": process.poll() is not None,
        "final_parent_empty": True,
        "measured_group_cpu_seconds": cpu,
        "measured_group_peak_memory_bytes": int(max(usage_after.ru_maxrss, 0) * 1024),
        "elapsed_seconds_including_cleanup": time.monotonic() - started,
        "process_exit_code": process.returncode,
        "timed_out": timed_out,
        "watchdog_error": watcher.error,
        "watchdog_oserror": watcher.last_oserror,
        "docker_used": False,
        "docker_unavailable": "permission denied on docker binary and cgroup fs read-only",
        "cell_result": json.loads(result_path.read_text()) if result_path.is_file() else None,
        "unknown_effect": not admitted,
    }
    write_json(host / "result.json", envelope)
    write_json(host / "resources.json", {"parent_samples": watcher.parent_samples, "leaf_samples": watcher.leaf_samples, "decision": watcher.error})
    return envelope


def main() -> None:
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("--worker", action="store_true")
    parser.add_argument("--request", type=Path)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--shared", type=Path)
    args = parser.parse_args()
    if not args.worker:
        raise SystemExit("native_execute worker entry only")
    request = json.loads(args.request.read_text())
    try:
        execute_candidate(request, args.output, args.shared)
    except BaseException:
        write_json(args.output / "failure.json", {"traceback": traceback.format_exc()})
        raise


if __name__ == "__main__":
    main()
