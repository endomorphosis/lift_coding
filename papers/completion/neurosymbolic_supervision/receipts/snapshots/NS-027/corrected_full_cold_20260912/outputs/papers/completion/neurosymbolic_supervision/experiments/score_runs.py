#!/usr/bin/env python3
"""Independent cold scorer for NS-026 attempt receipts.

The scorer is a separate process and principal. It does not trust arm
`accepted` / `closes_claim` / queue-completion flags, does not remount
hidden oracles into the proposal sandbox, and never fabricates a live
historical pass from a development stub. Historical oracles are loaded
from the NS-005 scorer-only store only after the proposal is sealed.
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
from typing import Any, Mapping


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


def hidden_pytest_targets(tree: Path, hidden_tests: Mapping[str, str] | None = None) -> list[str]:
    targets = []
    if hidden_tests:
        for rel in hidden_tests:
            targets.append(str(tree / rel))
    hidden = tree / "tests" / "test_hidden.py"
    if hidden.is_file() and str(hidden) not in targets:
        targets.append(str(hidden))
    if not targets:
        tests_dir = tree / "tests"
        if tests_dir.is_dir():
            targets.append(str(tests_dir))
    return targets


def run_hidden_tests(
    tree: Path,
    timeout: float,
    hidden_tests: dict[str, str] | None = None,
    nodeids: list[str] | None = None,
) -> dict[str, Any]:
    import subprocess

    started = time.perf_counter()
    env = dict(os.environ)
    env["PYTHONPATH"] = str(tree) + os.pathsep + env.get("PYTHONPATH", "")
    targets = hidden_pytest_targets(tree, hidden_tests)
    argv = [sys.executable, "-m", "pytest", "-q", "--tb=line"]
    if nodeids:
        argv.extend(nodeids)
    else:
        argv.extend(targets)
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
        if not test_path.is_file() and hidden_tests:
            first = next(iter(hidden_tests))
            test_path = tree / first
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


def verify_bindings(attempt: dict[str, Any], *, reconstructed: dict[str, Any] | None = None) -> list[str]:
    errors: list[str] = []
    bindings = attempt.get("bindings") or {}
    measurement = attempt.get("measurement") or {}
    identity = measurement.get("identity") or {}
    provider = attempt.get("provider_receipt") or {}
    for key in (
        "protocol_bundle_sha256",
        "source_preimage_id",
        "schedule_unit_id",
        "task_id",
        "family_id",
        "runner_source_id",
    ):
        if not bindings.get(key):
            errors.append(f"missing binding {key}")
    if identity.get("source_preimage_id") and identity.get("source_preimage_id") != bindings.get("source_preimage_id"):
        errors.append("identity/source_preimage_id does not match bindings")
    if identity.get("schedule_unit_id") and identity.get("schedule_unit_id") != bindings.get("schedule_unit_id"):
        errors.append("identity/schedule_unit_id does not match bindings")
    if provider.get("dispatched") and not provider.get("logical_effect_id"):
        errors.append("dispatched provider receipt missing logical_effect_id")
    if provider.get("dispatched") and not provider.get("runtime_receipt_id"):
        errors.append("dispatched provider receipt missing runtime_receipt_id")
    candidate = (attempt.get("runner") or {}).get("candidate")
    if candidate and reconstructed and reconstructed.get("pre_fix_commit"):
        if reconstructed.get("task_mismatch"):
            errors.append(reconstructed["task_mismatch"])
    return errors


def load_historical_hidden(attempt: dict[str, Any]) -> dict[str, Any]:
    task_id = attempt["bindings"]["task_id"]
    root = RUNNER.repo_root()
    gateway = RUNNER.load_gateway()
    store = RUNNER.default_upstream_store(root)
    reconstructed = gateway.reconstruct_hidden_oracle(task_id, root=root, store=store)
    reconstructed["task_id"] = task_id
    return reconstructed


def score_host_attempt(attempt: dict[str, Any]) -> dict[str, Any]:
    """Reverify durable signed development evidence; no provider or scorer effect."""
    gateway = RUNNER.load_gateway()
    previous = attempt["provider_receipt"]["host_verified"]
    verified = gateway.verify_host_response(RUNNER.repo_root(), previous["binding"])
    if verified != previous:
        raise ValueError("retained host receipt/binding changed")
    receipt = verified["receipt"]
    identity = attempt["measurement"]["identity"]
    binding = verified["binding"]
    if attempt["measurement"]["record_kind"] != "development" or any(identity.get(key) != binding.get(key) for key in ("task_id", "arm", "cache", "repetition")):
        raise ValueError("host receipt schedule differs")
    if attempt["bindings"]["source_preimage_id"] != receipt["source_sha256"] or identity["source_preimage_id"] != receipt["source_sha256"] or (attempt["runner"].get("candidate") or {}).get("host_candidate_sha256") != receipt["candidate_sha256"]:
        raise ValueError("host source/candidate binding differs")
    oracle = gateway.host_oracle(verified)
    scored = json.loads(RUNNER.canonical_dumps(attempt))
    scored["measurement"]["oracle"] = oracle
    scored["runner"]["command"] = "rescore"
    scored["runner"]["host_rescore"] = {"signed_evidence_reverified": True, "new_provider_calls": 0, "new_scorer_calls": 0, "hidden_oracle_loaded": False, "response_sha256": verified["response_sha256"]}
    admitted = receipt.get("historical_development_unit_admitted") is True and receipt.get("served_profile_admitted") is True
    passed = admitted and oracle["status"] == "passed"
    scored["measurement"]["terminal_state"] = "solved" if passed else "unsolved" if admitted and oracle["status"] == "failed" else "unavailable"
    scored["measurement"]["terminal_reason"] = oracle["reason"]
    scored["measurement"]["admission"].update(admitted=passed, mandatory_evidence_current=passed)
    return scored


def reuse_skip_is_not_oracle_pass(attempt: dict[str, Any]) -> bool:
    """Reuse SKIP/text cannot count as independent cold scoring or safe agreement."""

    measurement = attempt.get("measurement") or {}
    oracle = measurement.get("oracle") or {}
    control = measurement.get("control") or {}
    if control.get("reuse_credit") is True:
        return False
    if oracle.get("status") == "skipped":
        return False
    if str(oracle.get("reason") or "").lower() in {"proof_cache_hit"}:
        return False
    return True


def score_attempt(attempt: dict[str, Any], *, timeout: float = 30.0) -> dict[str, Any]:
    if attempt.get("schema") != RUNNER.SCHEMA_WRAPPER:
        raise SystemExit("attempt is not paper-ns-runner-attempt/v1")
    if not reuse_skip_is_not_oracle_pass(attempt) and (attempt.get("provider_receipt") or {}).get("host_verified"):
        raise SystemExit("reuse skip or unavailable scoring cannot count as an oracle pass")
    if (attempt.get("provider_receipt") or {}).get("host_verified"):
        return score_host_attempt(attempt)
    runner = attempt["runner"]
    task_id = attempt["bindings"]["task_id"]
    scorer_id = "ns-026-independent-historical-scorer"
    live = bool(runner.get("live_repair_admitted"))
    sandbox_files = runner.get("sandbox_files") or {}
    candidate = runner.get("candidate")
    isolation = runner.get("isolation") or {}

    hidden_tests: dict[str, str] = {}
    reconstructed: dict[str, Any] | None = None
    allowed_paths: list[str] = []
    if task_id in RUNNER.DEV_TASKS:
        hidden_tests = dict(RUNNER.DEV_TASKS[task_id]["hidden_tests"])
        allowed_paths = list(RUNNER.DEV_TASKS[task_id]["allowed_paths"])
    elif live or str(task_id).startswith("ns-hist-"):
        reconstructed = load_historical_hidden(attempt)
        if reconstructed.get("ok"):
            hidden_tests = dict(reconstructed.get("hidden_files") or {})
            allowed_paths = list((sandbox_files or {}).keys())
            if candidate and candidate.get("files"):
                allowed_paths = sorted(set(allowed_paths) | set(candidate["files"]))

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

    binding_errors = verify_bindings(attempt, reconstructed=reconstructed)
    if binding_errors:
        oracle = {
            "status": "unavailable",
            "independent_scorer_id": scorer_id,
            "receipt_id": None,
            "cold_full_validation": False,
            "candidate_valid": None,
            "hidden_access_incident": False,
            "reason": "source/prediction/receipt binding failed: " + "; ".join(binding_errors),
        }
        return apply_oracle(attempt, oracle, elapsed=0.0)

    if reconstructed is not None and not reconstructed.get("ok"):
        oracle = {
            "status": "unavailable",
            "independent_scorer_id": scorer_id,
            "receipt_id": None,
            "cold_full_validation": False,
            "candidate_valid": None,
            "hidden_access_incident": False,
            "reason": "historical oracle reconstruction failed: " + str(reconstructed.get("reason")),
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

    work = Path(tempfile.mkdtemp(prefix="ns026-score-"))
    try:
        RUNNER.write_tree(work, sandbox_files)
        try:
            RUNNER.apply_candidate(work, candidate["files"], allowed_paths or list(candidate["files"]))
        except Exception as exc:  # noqa: BLE001
            oracle = {
                "status": "failed",
                "independent_scorer_id": scorer_id,
                "receipt_id": None,
                "cold_full_validation": True,
                "candidate_valid": False,
                "hidden_access_incident": False,
                "reason": f"candidate rejected during scorer apply: {exc}",
            }
            return apply_oracle(attempt, oracle, elapsed=0.0)
        # Hidden tests are written only into this scorer tree after the proposal is sealed.
        RUNNER.write_tree(work, hidden_tests)
        nodeids = None
        if reconstructed and reconstructed.get("fail_to_pass"):
            nodeids = list(reconstructed["fail_to_pass"])
        result = run_hidden_tests(work, timeout=timeout, hidden_tests=hidden_tests, nodeids=nodeids)
        receipt_body = {
            "schema": "paper-ns-independent-score/v1",
            "scorer_id": scorer_id,
            "task_id": task_id,
            "schedule_unit_id": attempt["bindings"]["schedule_unit_id"],
            "source_preimage_id": attempt["bindings"].get("source_preimage_id"),
            "logical_effect_id": (attempt.get("provider_receipt") or {}).get("logical_effect_id"),
            "candidate_sha256": hashlib.sha256(
                RUNNER.canonical_dumps(candidate).encode("utf-8")
            ).hexdigest(),
            "status": result["status"],
            "method": result.get("method"),
            "historical_oracle": bool(reconstructed and reconstructed.get("ok")),
            "oracle_id": None if not reconstructed else (reconstructed.get("oracle") or {}).get("oracle_id"),
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
    elif passed:
        admitted_prod = bool(scored.get("provider_receipt", {}).get("admitted_production"))
        if scored.get("path_class") == "production" and admitted_prod:
            scored["measurement"]["terminal_state"] = "solved"
            scored["measurement"]["terminal_reason"] = "independent rescore passed on admitted production outcome"
            scored["measurement"]["admission"]["admitted"] = True
            scored["measurement"]["admission"]["mandatory_evidence_current"] = True
        elif not live and scored.get("path_class") != "production":
            scored["measurement"]["terminal_state"] = "solved"
            scored["measurement"]["terminal_reason"] = "independent rescore passed on the development unit"
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
