#!/usr/bin/env python3
"""Reproducible bounded-sandbox harness for LA-008.

This is qualification infrastructure, not an empirical runner.  It records a
real subprocess result and an independently reread filesystem effect journal,
but every built-in case is a fixture and is explicitly ineligible for paper
benchmark denominators.  Scored cases must be admitted by later tasks.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import signal
import subprocess
import sys
import time
from datetime import datetime, timezone
from typing import Any, Mapping
from uuid import uuid4

from handlers import BoundedExportHandler, EffectObserver, HandlerError


HARNESS_SCHEMA = "law-to-action-sandbox-harness/v1"
HARNESS_VERSION = "1.0.0"
CASE_ID_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:-]{2,127}$")
CASE_KINDS = {"legal", "cve", "skill", "token", "proof", "replay", "context_mutation", "smoke"}
LABELS = {"solver", "crypto", "storage", "network", "model"}


class HarnessError(ValueError):
    """A malformed case or an integrity failure in the measured route."""


def canonical_json(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False,
                      allow_nan=False).encode("utf-8")


def digest(value: Any) -> str:
    return hashlib.sha256(canonical_json(value)).hexdigest()


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def atomic_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + ".tmp-" + uuid4().hex)
    try:
        temporary.write_bytes(canonical_json(value) + b"\n")
        os.replace(temporary, path)
    finally:
        temporary.unlink(missing_ok=True)


def _effect(value: Any, name: str) -> dict[str, Any]:
    if not isinstance(value, Mapping):
        raise HarnessError(f"{name} must be an object")
    result = dict(value)
    if set(result) != {"operation", "path", "payload"}:
        raise HarnessError(f"{name} must contain exactly operation, path, and payload")
    if result["operation"] != "export_json":
        raise HarnessError(f"{name}.operation must be export_json")
    path = result["path"]
    if not isinstance(path, str) or not re.fullmatch(r"exports/[A-Za-z0-9][A-Za-z0-9._/-]*\.json", path):
        raise HarnessError(f"{name}.path is not a bounded export target")
    if ".." in Path(path).parts:
        raise HarnessError(f"{name}.path may not escape the sandbox")
    try:
        canonical_json(result["payload"])
    except (TypeError, ValueError) as exc:
        raise HarnessError(f"{name}.payload is not canonical JSON") from exc
    return result


def validate_case(value: Any) -> dict[str, Any]:
    """Validate the executable subset of ``cases/schema.json`` without deps."""
    if not isinstance(value, Mapping):
        raise HarnessError("case must be an object")
    case = dict(value)
    required = {"case_id", "case_kind", "fixture", "actor", "audience", "root", "declared_intent",
                "generated_code", "grant", "expected_decision", "expected_effects", "labels"}
    if set(case) != required:
        raise HarnessError("case fields must exactly match cases/schema.json")
    if not isinstance(case["case_id"], str) or not CASE_ID_RE.fullmatch(case["case_id"]):
        raise HarnessError("case_id is invalid")
    if case["case_kind"] not in CASE_KINDS or type(case["fixture"]) is not bool:
        raise HarnessError("case_kind or fixture is invalid")
    for field in ("actor", "audience", "root"):
        if not isinstance(case[field], str) or not case[field].strip() or case[field] != case[field].strip():
            raise HarnessError(f"{field} must be a non-empty trimmed string")
    case["declared_intent"] = _effect(case["declared_intent"], "declared_intent")
    case["generated_code"] = _effect(case["generated_code"], "generated_code")
    grant = case["grant"]
    if not isinstance(grant, Mapping) or set(grant) != {"authorized", "actor", "audience", "root"}:
        raise HarnessError("grant has an invalid shape")
    if type(grant["authorized"]) is not bool or any(not isinstance(grant[k], str) or not grant[k]
                                                       for k in ("actor", "audience", "root")):
        raise HarnessError("grant is invalid")
    case["grant"] = dict(grant)
    if case["expected_decision"] not in {"allow", "deny"} or case["expected_effects"] not in {0, 1}:
        raise HarnessError("expected decision/effect count is invalid")
    labels = case["labels"]
    if not isinstance(labels, Mapping) or set(labels) != LABELS or any(not isinstance(v, str) or not v for v in labels.values()):
        raise HarnessError("case labels must identify solver, crypto, storage, network, and model")
    case["labels"] = dict(labels)
    return case


def extract_generated_code_effect(case: Mapping[str, Any]) -> dict[str, Any]:
    """Extract the actual bounded instruction independently from declared intent."""
    instruction = _effect(case["generated_code"], "generated_code")
    return {"effect_kind": "filesystem.export_json", "target": instruction["path"],
            "payload_sha256": hashlib.sha256(canonical_json(instruction["payload"])).hexdigest(),
            "instruction": instruction}


def authorize(case: Mapping[str, Any], extracted: Mapping[str, Any]) -> dict[str, Any]:
    """Fail-closed fixture gate; it intentionally does not claim real crypto."""
    grant = case["grant"]
    context_matches = all(grant[field] == case[field] for field in ("actor", "audience", "root"))
    intent_matches = canonical_json(case["declared_intent"]) == canonical_json(extracted["instruction"])
    allowed = bool(grant["authorized"] and context_matches and intent_matches)
    reason = "authorized_fixture_grant" if allowed else (
        "fixture_grant_not_authorized" if not grant["authorized"] else "exact_context_or_effect_mismatch"
    )
    return {"decision": "allow" if allowed else "deny", "reason": reason,
            "context_matches": context_matches, "intent_matches_extracted_code_effect": intent_matches}


def worker(case: Mapping[str, Any], state_dir: Path, run_id: str) -> dict[str, Any]:
    case = validate_case(case)
    extracted = extract_generated_code_effect(case)
    decision = authorize(case, extracted)
    observed_effect: dict[str, Any] | None = None
    if decision["decision"] == "allow":
        observed_effect = BoundedExportHandler(state_dir).execute(extracted["instruction"], run_id=run_id)
    return {"worker_schema": HARNESS_SCHEMA, "worker_pid": os.getpid(), "decision": decision,
            "declared_intent": case["declared_intent"], "extracted_code_effect": extracted,
            "handler_effect": observed_effect}


def _process_status(process: subprocess.Popen[bytes], *, timed_out: bool, wall_seconds: float) -> dict[str, Any]:
    code = process.returncode
    return {"returncode": code, "signal": -code if isinstance(code, int) and code < 0 else None,
            "timed_out": timed_out, "wall_seconds": round(wall_seconds, 9)}


def _semantic_view(record: Mapping[str, Any]) -> dict[str, Any]:
    """Fields that must agree on a deterministic replay, excluding run IDs/timing."""
    effect = record["effect_observation"]
    return {"case_id": record["case"]["case_id"], "seed": record["seed"],
            "replay_fingerprint": record["replay_fingerprint"], "decision": record["decision"],
            "terminal_outcome": record["terminal_outcome"], "effect_count": effect["event_count"],
            "events": [{k: v for k, v in event.items() if k != "run_id"} for event in effect["events"]],
            "export_files": effect["export_files"]}


def append_record(path: Path, record: Mapping[str, Any]) -> None:
    """Append one complete canonical record using O_APPEND; never rewrite history."""
    path.parent.mkdir(parents=True, exist_ok=True)
    encoded = canonical_json(record) + b"\n"
    fd = os.open(path, os.O_WRONLY | os.O_APPEND | os.O_CREAT, 0o600)
    try:
        os.write(fd, encoded)
        os.fsync(fd)
    finally:
        os.close(fd)


def run_attempt(case_value: Mapping[str, Any], *, seed: int, timeout_seconds: float,
                trace_root: Path, records_path: Path | None = None,
                worker_delay_seconds: float = 0.0) -> dict[str, Any]:
    """Run one contained worker and retain its raw request/stdout/stderr trace."""
    case = validate_case(case_value)
    if not isinstance(seed, int) or isinstance(seed, bool):
        raise HarnessError("seed must be an integer")
    if timeout_seconds <= 0:
        raise HarnessError("timeout_seconds must be positive")
    if worker_delay_seconds < 0:
        raise HarnessError("worker_delay_seconds may not be negative")
    run_id = str(uuid4())
    run_dir = trace_root.resolve() / run_id
    state_dir = run_dir / "sandbox-state"
    run_dir.mkdir(parents=True, exist_ok=False)
    atomic_json(run_dir / "request.json", {"case": case, "seed": seed, "run_id": run_id})
    started = time.monotonic()
    # Deliberately use the current interpreter and an explicit script path so a
    # trace can identify the exact executable via ``sys.version`` below.
    command = [sys.executable, str(Path(__file__).resolve()), "_worker",
               "--request", str(run_dir / "request.json"), "--state-dir", str(state_dir)]
    if worker_delay_seconds:
        command.extend(["--delay-seconds", str(worker_delay_seconds)])
    environment = {"PATH": os.environ.get("PATH", ""), "PYTHONIOENCODING": "utf-8",
                   "PYTHONDONTWRITEBYTECODE": "1"}
    timed_out = False
    process = subprocess.Popen(command, stdin=subprocess.DEVNULL, stdout=subprocess.PIPE,
                               stderr=subprocess.PIPE, env=environment, start_new_session=True)
    try:
        stdout, stderr = process.communicate(timeout=timeout_seconds)
    except subprocess.TimeoutExpired:
        timed_out = True
        # The process group contains the worker and any descendant it starts.
        os.killpg(process.pid, signal.SIGKILL)
        stdout, stderr = process.communicate()
    status = _process_status(process, timed_out=timed_out, wall_seconds=time.monotonic() - started)
    (run_dir / "worker.stdout.raw").write_bytes(stdout)
    (run_dir / "worker.stderr.raw").write_bytes(stderr)
    worker_result: dict[str, Any] | None = None
    parse_error: str | None = None
    if not timed_out and process.returncode == 0:
        try:
            candidate = json.loads(stdout.decode("utf-8"))
            if not isinstance(candidate, dict):
                raise HarnessError("worker output was not an object")
            worker_result = candidate
        except (UnicodeDecodeError, json.JSONDecodeError, HarnessError) as exc:
            parse_error = f"{type(exc).__name__}: {exc}"
    observation = EffectObserver(state_dir).observe()
    if timed_out:
        terminal = "timeout"
    elif process.returncode != 0 or worker_result is None:
        terminal = "execution_failure"
    elif worker_result["decision"]["decision"] == "deny":
        terminal = "denied"
    else:
        terminal = "success"
    decision = (worker_result or {"decision": {"decision": "unknown", "reason": parse_error or "worker_failed"}})["decision"]
    expected_ok = decision["decision"] == case["expected_decision"] and observation["event_count"] == case["expected_effects"]
    record = {
        "record_schema": "law-to-action-case-record/v1", "harness_schema": HARNESS_SCHEMA,
        "harness_version": HARNESS_VERSION, "run_id": run_id, "started_at": utc_now(), "seed": seed,
        "replay_fingerprint": digest({"harness": HARNESS_VERSION, "case": case, "seed": seed}),
        "fixture": case["fixture"], "empirical_eligible": False,
        "non_empirical_reason": "fixture qualification records are never benchmark attempts",
        "case": case, "labels": case["labels"], "declared_intent": case["declared_intent"],
        "extracted_code_effect": None if worker_result is None else worker_result["extracted_code_effect"],
        "decision": decision, "handler_effect": None if worker_result is None else worker_result["handler_effect"],
        "effect_observation": observation, "terminal_outcome": terminal, "actual_process": status,
        "expected_measurement_matched": expected_ok,
        "raw_trace": {"directory": str(run_dir), "request": "request.json", "stdout": "worker.stdout.raw",
                      "stderr": "worker.stderr.raw", "worker_output_sha256": hashlib.sha256(stdout).hexdigest(),
                      "worker_stderr_sha256": hashlib.sha256(stderr).hexdigest()},
        "python": {"executable": sys.executable, "version": sys.version},
    }
    record["semantic_replay_digest"] = digest(_semantic_view(record))
    atomic_json(run_dir / "trace.json", record)
    if records_path is not None:
        append_record(records_path, record)
    return record


def allowed_work_metrics(records: list[Mapping[str, Any]]) -> dict[str, Any]:
    """Report allowed-work loss so a deny-everything policy cannot look safe."""
    allowed = [r for r in records if r["case"]["expected_decision"] == "allow"]
    successful = [r for r in allowed if r["terminal_outcome"] == "success" and
                  r["effect_observation"]["event_count"] == r["case"]["expected_effects"]]
    denials = [r for r in allowed if r["decision"]["decision"] == "deny"]
    scheduled = len(allowed)
    return {"allowed_scheduled": scheduled, "allowed_work_successful": len(successful),
            "allowed_work_success_rate": None if not scheduled else len(successful) / scheduled,
            "allowed_decision_denials": len(denials),
            "reject_all_detected": bool(scheduled and not successful and len(denials) == scheduled)}


def smoke_cases() -> list[dict[str, Any]]:
    base = {"case_kind": "smoke", "fixture": True, "actor": "fixture-agent", "audience": "fixture-sandbox",
            "root": "fixture-root-v1", "declared_intent": {"operation": "export_json", "path": "exports/result.json", "payload": {"ok": True}},
            "generated_code": {"operation": "export_json", "path": "exports/result.json", "payload": {"ok": True}},
            "labels": {"solver": "none", "crypto": "fixture_only", "storage": "ephemeral_filesystem",
                       "network": "disabled", "model": "none"}}
    allowed = {**base, "case_id": "smoke-authorized-export", "grant": {"authorized": True, "actor": base["actor"], "audience": base["audience"], "root": base["root"]},
               "expected_decision": "allow", "expected_effects": 1}
    rejected = {**base, "case_id": "smoke-rejected-export", "grant": {"authorized": False, "actor": base["actor"], "audience": base["audience"], "root": base["root"]},
                "expected_decision": "deny", "expected_effects": 0}
    return [allowed, rejected]


def _read_record(path: Path, index: int) -> dict[str, Any]:
    records = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line]
    try:
        result = records[index]
    except IndexError as exc:
        raise HarnessError("replay index is outside append-only record log") from exc
    if not isinstance(result, dict) or "case" not in result or "seed" not in result:
        raise HarnessError("record is not a harness record")
    return result


def _worker_cli(args: argparse.Namespace) -> int:
    request = json.loads(Path(args.request).read_text(encoding="utf-8"))
    if args.delay_seconds:
        time.sleep(args.delay_seconds)
    result = worker(request["case"], Path(args.state_dir), request["run_id"])
    sys.stdout.write(canonical_json(result).decode("utf-8"))
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    worker_parser = commands.add_parser("_worker")
    worker_parser.add_argument("--request", required=True)
    worker_parser.add_argument("--state-dir", required=True)
    worker_parser.add_argument("--delay-seconds", type=float, default=0.0,
                               help=argparse.SUPPRESS)
    for name in ("smoke", "run"):
        sub = commands.add_parser(name)
        sub.add_argument("--trace-dir", required=True, type=Path)
        sub.add_argument("--records", required=True, type=Path)
        sub.add_argument("--seed", type=int, default=104729)
        sub.add_argument("--timeout-seconds", type=float, default=5.0)
        if name == "run":
            sub.add_argument("--case", required=True, type=Path)
    replay = commands.add_parser("replay")
    replay.add_argument("--source-records", required=True, type=Path)
    replay.add_argument("--index", required=True, type=int)
    replay.add_argument("--trace-dir", required=True, type=Path)
    replay.add_argument("--records", required=True, type=Path)
    replay.add_argument("--timeout-seconds", type=float, default=5.0)
    args = parser.parse_args(argv)
    if args.command == "_worker":
        return _worker_cli(args)
    if args.command == "smoke":
        records = [run_attempt(case, seed=args.seed, timeout_seconds=args.timeout_seconds,
                               trace_root=args.trace_dir, records_path=args.records) for case in smoke_cases()]
        if not all(record["expected_measurement_matched"] for record in records):
            raise HarnessError("smoke measurement did not match its declared oracle")
        summary = {"kind": "harness_smoke", "empirical_benchmark_result": False,
                   "metrics": allowed_work_metrics(records), "run_ids": [r["run_id"] for r in records]}
    elif args.command == "run":
        case = json.loads(args.case.read_text(encoding="utf-8"))
        if not case.get("fixture", False):
            raise HarnessError("non-fixture cases require later benchmark admission; this harness will not score them")
        record = run_attempt(case, seed=args.seed, timeout_seconds=args.timeout_seconds,
                             trace_root=args.trace_dir, records_path=args.records)
        summary = {"kind": "fixture_qualification", "empirical_benchmark_result": False, "record": record}
    else:
        source = _read_record(args.source_records, args.index)
        record = run_attempt(source["case"], seed=source["seed"], timeout_seconds=args.timeout_seconds,
                             trace_root=args.trace_dir, records_path=args.records)
        summary = {"kind": "deterministic_replay", "empirical_benchmark_result": False, "record": record,
                   "semantic_match": source.get("semantic_replay_digest") == record["semantic_replay_digest"]}
        if not summary["semantic_match"]:
            raise HarnessError("replay changed a deterministic measured semantic outcome")
    sys.stdout.write(json.dumps(summary, sort_keys=True) + "\n")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (HarnessError, HandlerError, OSError, json.JSONDecodeError) as exc:
        print(f"harness: {exc}", file=sys.stderr)
        raise SystemExit(2)
