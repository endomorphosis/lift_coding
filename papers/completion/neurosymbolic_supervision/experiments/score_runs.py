#!/usr/bin/env python3
"""Independent cold scorer for NS-006 attempt receipts.

The scorer is a separate process and principal. It does not trust arm
`accepted` / `closes_claim` / queue-completion flags, does not remount
hidden oracles into the proposal sandbox, and never fabricates a live
historical pass from a development stub.
"""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import os
import shutil
import sys
import tempfile
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def load_runner():
    path = Path(__file__).resolve().with_name("run_comparison.py")
    spec = importlib.util.spec_from_file_location("ns006_run_comparison", path)
    if spec is None or spec.loader is None:
        raise RuntimeError("cannot load run_comparison.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


RUNNER = load_runner()


def utcnow() -> str:
    return datetime.now(timezone.utc).isoformat()


def atomic_write(path: Path, obj: Any) -> None:
    RUNNER.atomic_write(path, obj)


def hidden_leak(sandbox_files: dict[str, str], hidden_tests: dict[str, str]) -> list[str]:
    leaks = []
    blob = "\n".join(sandbox_files.values())
    for rel, content in hidden_tests.items():
        if content.strip() and content.strip() in blob:
            leaks.append(rel)
        if "assert add(1, 2) == 3" in blob:
            leaks.append("hidden-assertion")
    markers = RUNNER.hidden_markers_in(blob)
    leaks.extend(markers)
    return sorted(set(leaks))


def run_hidden_tests(tree: Path, timeout: float) -> dict[str, Any]:
    import subprocess

    started = time.perf_counter()
    env = dict(os.environ)
    env["PYTHONPATH"] = str(tree) + os.pathsep + env.get("PYTHONPATH", "")
    pytest_mod = shutil.which("pytest")
    argv = [sys.executable, "-m", "pytest", "-q", "--tb=line", str(tree / "tests" / "test_hidden.py")]
    try:
        result = subprocess.run(
            argv,
            cwd=str(tree),
            capture_output=True,
            text=True,
            timeout=timeout,
            env=env,
            check=False,
        )
        method = "python -m pytest"
        code = result.returncode
        stdout = result.stdout
        stderr = result.stderr
    except subprocess.TimeoutExpired as exc:
        return {
            "status": "timed_out",
            "candidate_valid": None,
            "reason": f"pytest exceeded {timeout}s",
            "elapsed": time.perf_counter() - started,
            "method": "python -m pytest",
            "stdout": (exc.stdout or b"").decode("utf-8", "replace") if isinstance(exc.stdout, bytes) else (exc.stdout or ""),
        }
    except Exception as exc:  # noqa: BLE001
        # Fallback: execute the hidden test file under unittest-style asserts.
        method = f"exec-fallback after {type(exc).__name__}"
        stdout = ""
        stderr = f"{type(exc).__name__}: {exc}"
        code = 2
        test_path = tree / "tests" / "test_hidden.py"
        try:
            ns: dict[str, Any] = {"__name__": "test_hidden"}
            sys.path.insert(0, str(tree))
            try:
                exec(test_path.read_text(encoding="utf-8"), ns, ns)
                ran = 0
                for name, fn in list(ns.items()):
                    if name.startswith("test_") and callable(fn):
                        fn()
                        ran += 1
                code = 0 if ran else 1
                stdout = f"executed {ran} hidden tests via exec"
            finally:
                if sys.path and sys.path[0] == str(tree):
                    sys.path.pop(0)
        except AssertionError as assert_exc:
            code = 1
            stderr = f"AssertionError: {assert_exc}"
        except Exception as exec_exc:  # noqa: BLE001
            code = 2
            stderr = f"{type(exec_exc).__name__}: {exec_exc}"
    elapsed = time.perf_counter() - started
    if code == 0:
        return {
            "status": "passed",
            "candidate_valid": True,
            "reason": "hidden tests passed on the patched tree",
            "elapsed": elapsed,
            "method": method,
            "stdout": stdout[-2000:],
            "stderr": stderr[-2000:],
        }
    if code == 1:
        return {
            "status": "failed",
            "candidate_valid": False,
            "reason": "hidden tests failed on the patched tree",
            "elapsed": elapsed,
            "method": method,
            "stdout": stdout[-2000:],
            "stderr": stderr[-2000:],
        }
    return {
        "status": "unavailable",
        "candidate_valid": None,
        "reason": f"hidden tests could not be executed (exit {code}): {stderr[-500:]}",
        "elapsed": elapsed,
        "method": method,
        "stdout": stdout[-2000:],
        "stderr": stderr[-2000:],
    }


def score_attempt(attempt: dict[str, Any], *, timeout: float = 30.0) -> dict[str, Any]:
    if attempt.get("schema") != RUNNER.SCHEMA_WRAPPER:
        raise SystemExit("attempt is not paper-ns-runner-attempt/v1")
    measurement = attempt["measurement"]
    runner = attempt["runner"]
    task_id = attempt["bindings"]["task_id"]
    scorer_id = "ns-006-independent-scorer"
    live = bool(runner.get("live_repair_admitted"))
    sandbox_files = runner.get("sandbox_files") or {}
    candidate = runner.get("candidate")
    isolation = runner.get("isolation") or {}

    hidden_tests: dict[str, str] = {}
    if task_id in RUNNER.DEV_TASKS:
        hidden_tests = dict(RUNNER.DEV_TASKS[task_id]["hidden_tests"])

    leaks = hidden_leak(sandbox_files if isinstance(sandbox_files, dict) else {}, hidden_tests)
    if isolation.get("hidden_store_mounted") or isolation.get("hidden_markers_found") or leaks:
        oracle = {
            "status": "failed",
            "independent_scorer_id": scorer_id,
            "receipt_id": None,
            "cold_full_validation": True,
            "candidate_valid": False,
            "hidden_access_incident": True,
            "reason": "hidden oracle material observed on the proposal principal: " + ", ".join(leaks or isolation.get("hidden_markers_found") or ["mounted-store"]),
        }
        return apply_oracle(attempt, oracle, elapsed=0.0)

    if live:
        oracle = {
            "status": "unavailable",
            "independent_scorer_id": scorer_id,
            "receipt_id": None,
            "cold_full_validation": False,
            "candidate_valid": None,
            "hidden_access_incident": False,
            "reason": (
                "Live hidden FAIL_TO_PASS payloads are scorer-principal reconstruction "
                "recipes and are not materialized in this NS-006 environment. "
                "Refusing to load NS-005 scorer_only payloads into a proposal-adjacent tree."
            ),
        }
        return apply_oracle(attempt, oracle, elapsed=0.0)

    if not candidate or not candidate.get("files"):
        oracle = {
            "status": "not_run",
            "independent_scorer_id": scorer_id,
            "receipt_id": None,
            "cold_full_validation": False,
            "candidate_valid": None,
            "hidden_access_incident": False,
            "reason": "no candidate files to score",
        }
        return apply_oracle(attempt, oracle, elapsed=0.0)

    if not hidden_tests:
        oracle = {
            "status": "unavailable",
            "independent_scorer_id": scorer_id,
            "receipt_id": None,
            "cold_full_validation": False,
            "candidate_valid": None,
            "hidden_access_incident": False,
            "reason": f"no independent hidden tests registered for {task_id}",
        }
        return apply_oracle(attempt, oracle, elapsed=0.0)

    work = Path(tempfile.mkdtemp(prefix="ns006-score-"))
    try:
        RUNNER.write_tree(work, sandbox_files)
        RUNNER.apply_candidate(
            work,
            candidate["files"],
            list(RUNNER.DEV_TASKS[task_id]["allowed_paths"]),
        )
        # Hidden tests are written only into this scorer tree.
        RUNNER.write_tree(work, hidden_tests)
        result = run_hidden_tests(work, timeout=timeout)
        receipt_body = {
            "schema": "paper-ns-independent-score/v1",
            "task_id": task_id,
            "schedule_unit_id": attempt["bindings"]["schedule_unit_id"],
            "candidate_sha256": hashlib.sha256(
                RUNNER.canonical_dumps(candidate).encode("utf-8")
            ).hexdigest(),
            "status": result["status"],
            "method": result.get("method"),
            "scored_at": utcnow(),
        }
        oracle = {
            "status": result["status"],
            "independent_scorer_id": scorer_id,
            "receipt_id": "sha256:" + hashlib.sha256(
                RUNNER.canonical_dumps(receipt_body).encode("utf-8")
            ).hexdigest(),
            "cold_full_validation": True,
            "candidate_valid": result["candidate_valid"],
            "hidden_access_incident": False,
            "reason": result["reason"],
        }
        return apply_oracle(attempt, oracle, elapsed=float(result.get("elapsed") or 0.0))
    finally:
        shutil.rmtree(work, ignore_errors=True)


def apply_oracle(attempt: dict[str, Any], oracle: dict[str, Any], *, elapsed: float) -> dict[str, Any]:
    scored = json.loads(RUNNER.canonical_dumps(attempt))
    scored["measurement"]["oracle"] = oracle
    scored["measurement"]["finished_at"] = utcnow()
    scored["runner"]["command"] = "rescore"
    measures = scored["measurement"]["measurements"]
    measures["independent_scoring_elapsed_seconds"] = RUNNER.measurement(
        "actual", "seconds", value=elapsed, source="time.perf_counter"
    )
    state = scored["measurement"]["terminal_state"]
    live = bool(scored["runner"].get("live_repair_admitted"))
    passed = oracle.get("status") == "passed" and oracle.get("candidate_valid") is True
    if state == "solved" and not passed:
        scored["measurement"]["terminal_state"] = "unsolved"
        scored["measurement"]["terminal_reason"] = (
            "rescore did not confirm the prior solved decision: " + (oracle.get("reason") or "oracle not passed")
        )
        scored["measurement"]["admission"]["admitted"] = False
        scored["measurement"]["admission"]["mandatory_evidence_current"] = False
    elif state == "unsolved" and passed and not live and scored.get("path_class") != "production":
        scored["measurement"]["terminal_state"] = "solved"
        scored["measurement"]["terminal_reason"] = "independent rescore passed on the development fixture"
        scored["measurement"]["admission"]["admitted"] = True
        scored["measurement"]["admission"]["mandatory_evidence_current"] = True
    return scored


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--attempt", required=True, help="runner attempt receipt to score")
    parser.add_argument("--out", required=True, help="where to write the scored receipt")
    parser.add_argument("--timeout", type=float, default=30.0)
    args = parser.parse_args(argv)
    attempt = json.loads(Path(args.attempt).read_text(encoding="utf-8"))
    scored = score_attempt(attempt, timeout=args.timeout)
    atomic_write(Path(args.out), scored)
    json.dump(scored["measurement"]["oracle"], sys.stdout, indent=2, sort_keys=True)
    sys.stdout.write("\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
