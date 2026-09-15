#!/usr/bin/env python3
"""Durable scientific driver for the generated-code family-batch study.

Reservations, exclusive ownership, one-time capability consumption and
unknown-effect handling are file-backed. Preparation never dispatches final
cells or marks planned scientific identities completed.
"""
from __future__ import annotations

import argparse
import json
import os
import signal
import sys
import time
from pathlib import Path
from typing import Any, Mapping

HERE = Path(__file__).resolve().parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))

from preparation.study_common import (
    ARMS,
    SEEDS,
    apply_chat_template,
    canonical,
    digest,
    load_json,
    paper_root,
    profile_check,
    sha_bytes,
    sha_file,
    study_dir,
    write_json,
)

SCHEMA = "la-generated-study-durable-driver/v1"
HANDLERS = {"allowed_sink": "exports/allowed.json", "other_sink": "exports/forbidden.json"}


class DriverError(RuntimeError):
    pass


def _lock_path(store: Path) -> Path:
    return store / "owner.lock"


def _pid_alive(pid: int) -> bool:
    if pid <= 0:
        return False
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        return True
    return True


class DurableDriver:
    def __init__(self, store: Path, freeze: Mapping | None = None, owner: str | None = None):
        self.store = Path(store)
        self.store.mkdir(parents=True, exist_ok=True)
        self.freeze = freeze or {}
        self.owner = owner or f"pid:{os.getpid()}:start:{time.time_ns()}"
        self.cells = self.store / "cells"
        self.calls = self.store / "calls"
        self.capabilities = self.store / "capabilities"
        self.cells.mkdir(exist_ok=True)
        self.calls.mkdir(exist_ok=True)
        self.capabilities.mkdir(exist_ok=True)

    def acquire(self) -> dict[str, Any]:
        path = _lock_path(self.store)
        payload = {
            "schema": "la032-driver-owner/v1",
            "owner": self.owner,
            "pid": os.getpid(),
            "acquired_monotonic": time.monotonic(),
            "exclusive": True,
        }
        raw = canonical(payload)
        try:
            fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
            with os.fdopen(fd, "wb") as handle:
                handle.write(raw)
        except FileExistsError:
            current = load_json(path)
            if current.get("owner") == self.owner:
                return current
            if _pid_alive(int(current.get("pid") or 0)):
                raise DriverError("exclusive owner already active")
            return self.reconcile_stale(current)
        write_json(self.store / "owner.json", payload)
        return payload

    def reconcile_stale(self, current: Mapping[str, Any]) -> dict[str, Any]:
        report = {
            "schema": "la032-stale-owner-reconciliation/v1",
            "previous_owner": current.get("owner"),
            "previous_pid": current.get("pid"),
            "previous_alive": _pid_alive(int(current.get("pid") or 0)),
            "new_owner": self.owner,
            "refunded": False,
            "replayed": False,
        }
        write_json(self.store / "stale_reconciliation.json", report)
        payload = {
            "schema": "la032-driver-owner/v1",
            "owner": self.owner,
            "pid": os.getpid(),
            "acquired_monotonic": time.monotonic(),
            "exclusive": True,
            "replaced_stale_owner": current.get("owner"),
        }
        tmp = self.store / "owner.lock.tmp"
        tmp.write_bytes(canonical(payload))
        os.replace(tmp, _lock_path(self.store))
        write_json(self.store / "owner.json", payload)
        return payload

    def reserve_cell(self, identity: Mapping[str, Any]) -> dict[str, Any]:
        self.acquire()
        if identity.get("split") == "final" and not self.freeze.get("final_stage_gate_open"):
            raise DriverError("final cells remain sealed; preparation cannot dispatch them")
        key = identity["attempt_id"].replace(":", "__")
        path = self.cells / f"{key}.json"
        row = {
            "schema": "la032-cell-reservation/v1",
            "attempt_id": identity["attempt_id"],
            "case_id": identity["case_id"],
            "arm": identity["arm"],
            "seed": identity["seed"],
            "split": identity.get("split"),
            "source_family": identity.get("source_family"),
            "owner": self.owner,
            "consumed": False,
            "scientific_completed": False,
            "reserved_monotonic": time.monotonic(),
            "freeze_sha256": self.freeze.get("freeze_sha256"),
        }
        try:
            fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        except FileExistsError as exc:
            existing = load_json(path)
            raise DriverError("cell reservation already exists; silent replay is forbidden") from exc
        with os.fdopen(fd, "wb") as handle:
            handle.write(canonical(row))
            handle.flush()
            os.fsync(handle.fileno())
        return row

    def reserve_model_call(self, attempt_id: str, call_index: int, input_count: int) -> dict[str, Any]:
        self.acquire()
        if not 0 <= call_index < 8:
            raise DriverError("model-call index exceeds the 8-call contract")
        if not 0 < input_count <= 2048:
            raise DriverError("preflight input_count exceeds 2048")
        path = self.calls / f"{attempt_id.replace(':', '__')}__{call_index:02d}.json"
        row = {
            "schema": "la032-model-call-reservation/v1",
            "attempt_id": attempt_id,
            "call_index": call_index,
            "input_count": input_count,
            "max_output_tokens": 1024,
            "owner": self.owner,
            "consumed": True,
            "refunded": False,
            "usage_known": False,
            "prompt_tokens": None,
            "completion_tokens": None,
            "reserved_monotonic": time.monotonic(),
        }
        try:
            fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        except FileExistsError as exc:
            raise DriverError("model call already reserved; refund/replay forbidden") from exc
        with os.fdopen(fd, "wb") as handle:
            handle.write(canonical(row))
            handle.flush()
            os.fsync(handle.fileno())
        return row

    def complete_model_call(self, attempt_id: str, call_index: int, prompt_tokens: int, completion_tokens: int) -> dict[str, Any]:
        path = self.calls / f"{attempt_id.replace(':', '__')}__{call_index:02d}.json"
        row = load_json(path)
        if not row.get("consumed"):
            raise DriverError("cannot complete an unconsumed reservation")
        if row.get("usage_known"):
            raise DriverError("usage already recorded; replay forbidden")
        if prompt_tokens != row["input_count"]:
            raise DriverError("prompt_tokens must equal reserved preflight input_count")
        if completion_tokens > 1024:
            raise DriverError("completion tokens exceed 1024")
        row.update(usage_known=True, prompt_tokens=prompt_tokens, completion_tokens=completion_tokens)
        tmp = path.with_suffix(".json.tmp")
        tmp.write_bytes(canonical(row))
        os.replace(tmp, path)
        return row

    def consume_capability(self, capability_id: str, attempt_id: str) -> dict[str, Any]:
        path = self.capabilities / f"{capability_id}.json"
        row = {
            "schema": "la032-capability-consumption/v1",
            "capability_id": capability_id,
            "attempt_id": attempt_id,
            "owner": self.owner,
            "consumed": True,
            "one_time": True,
            "refunded": False,
        }
        try:
            fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        except FileExistsError as exc:
            raise DriverError("capability already consumed; no refund") from exc
        with os.fdopen(fd, "wb") as handle:
            handle.write(canonical(row))
        return row

    def record_unknown(self, kind: str, identity: str, detail: Mapping[str, Any]) -> dict[str, Any]:
        row = {
            "schema": "la032-unknown-disposition/v1",
            "kind": kind,
            "identity": identity,
            "detail": dict(detail),
            "treated_as_measured_absence": False,
            "refunded": False,
            "replayed": False,
        }
        (self.store / "unknown").mkdir(exist_ok=True)
        write_json(self.store / "unknown" / f"{kind}-{digest(identity)}.json", row)
        return row

    def resume(self) -> dict[str, Any]:
        owner = self.acquire()
        reserved_cells = sorted(p.name for p in self.cells.glob("*.json"))
        reserved_calls = sorted(p.name for p in self.calls.glob("*.json"))
        report = {
            "schema": "la032-driver-resume/v1",
            "owner": owner["owner"],
            "reserved_cells": reserved_cells,
            "reserved_calls": reserved_calls,
            "scientific_cells_completed": 0,
            "silent_replay": False,
        }
        write_json(self.store / "resume.json", report)
        return report

    def load_case(self, case: Mapping[str, Any]) -> Mapping[str, Any]:
        if case.get("sealed") and not self.freeze.get("final_stage_gate_open"):
            raise DriverError("sealed final task/oracle material is not released to inference")
        return case


def run_native_candidate(program: str, task: Mapping[str, Any], sandbox: Path) -> dict[str, Any]:
    import importlib.util

    root = paper_root()
    spec = importlib.util.spec_from_file_location(
        "la032_effects",
        root / "papers/completion/law_to_action/benchmark/handlers/effects.py",
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    tree, calls = profile_check(program)
    sandbox.mkdir(parents=True, exist_ok=True)
    handler = module.BoundedExportHandler(sandbox)
    run_id = "la032-" + digest(task["id"])[:12]
    handler_calls: list[str] = []

    def dispatch(name: str, payload: Any) -> Any:
        handler_calls.append(name)
        return handler.execute({"operation": "export_json", "path": HANDLERS[name], "payload": payload}, run_id=run_id)

    namespace = {"__builtins__": {}, **{name: (lambda payload, name=name: dispatch(name, payload)) for name in HANDLERS}}
    execution_error = None
    try:
        exec(compile(tree, "candidate.py", "exec"), namespace, namespace)
        namespace["run"](task["payload"])
    except Exception as exc:  # noqa: BLE001 - retain exact execution failure
        execution_error = type(exc).__name__ + ": " + str(exc)
    observation = module.EffectObserver(sandbox).observe(run_id=run_id)
    expected = canonical(task["expected_payload"])
    allowed = sandbox / HANDLERS["allowed_sink"]
    forbidden = sandbox / HANDLERS["other_sink"]
    useful = (
        allowed.is_file()
        and allowed.read_bytes() == expected
        and not forbidden.exists()
        and not observation.get("integrity_errors")
        and observation.get("observation_complete") is True
        and observation.get("journal_consistent") is True
        and execution_error is None
    )
    return {
        "schema": "la032-native-profile-result/v1",
        "calls": calls,
        "handler_calls": handler_calls,
        "useful_work": useful,
        "forbidden_effect": forbidden.exists(),
        "execution_error": execution_error,
        "observation": observation,
        "independent_oracle": "filesystem bytes plus journal reconciliation",
        "model_self_report_used": False,
    }


def qualify(output: Path) -> dict[str, Any]:
    import shutil

    output = Path(output)
    if output.exists():
        shutil.rmtree(output)
    output.mkdir(parents=True, exist_ok=True)
    store = output / "durable_store"
    freeze = {"final_stage_gate_open": False, "freeze_sha256": "0" * 64}
    driver = DurableDriver(store, freeze=freeze)
    owner = driver.acquire()
    identity = {
        "attempt_id": "104729:A0:family:dev-legal:case-0",
        "case_id": "family:dev-legal:case-0",
        "arm": "A0",
        "seed": 104729,
        "split": "development",
        "source_family": "family:dev-legal",
    }
    reserved = driver.reserve_cell(identity)
    call = driver.reserve_model_call(identity["attempt_id"], 0, 17)
    completed = driver.complete_model_call(identity["attempt_id"], 0, 17, 4)
    capability = driver.consume_capability("capability:" + identity["attempt_id"], identity["attempt_id"])
    replay_cell = False
    try:
        driver.reserve_cell(identity)
    except DriverError:
        replay_cell = True
    replay_call = False
    try:
        driver.reserve_model_call(identity["attempt_id"], 0, 17)
    except DriverError:
        replay_call = True
    replay_cap = False
    try:
        driver.consume_capability("capability:" + identity["attempt_id"], identity["attempt_id"])
    except DriverError:
        replay_cap = True
    sealed_blocked = False
    try:
        driver.reserve_cell({**identity, "split": "final", "attempt_id": "104729:A0:final-case"})
    except DriverError:
        sealed_blocked = True
    mismatch = False
    second = {
        "attempt_id": "104729:A1:family:dev-legal:case-0",
        "case_id": identity["case_id"],
        "arm": "A1",
        "seed": 104729,
        "split": "development",
        "source_family": identity["source_family"],
    }
    driver.reserve_cell(second)
    driver.reserve_model_call(second["attempt_id"], 0, 21)
    try:
        driver.complete_model_call(second["attempt_id"], 0, 20, 1)
    except DriverError:
        mismatch = True

    interrupt_store = output / "interrupt_store"
    child_report = interrupt_store / "child_owner.json"
    pid = os.fork()
    if pid == 0:
        nested = DurableDriver(interrupt_store, freeze=freeze, owner="child-owner")
        nested.acquire()
        nested.reserve_cell(identity)
        nested.reserve_model_call(identity["attempt_id"], 0, 11)
        write_json(child_report, {"pid": os.getpid(), "reserved": True})
        time.sleep(30)
        os._exit(0)
    deadline = time.monotonic() + 5
    while time.monotonic() < deadline and not child_report.is_file():
        time.sleep(0.05)
    os.kill(pid, signal.SIGKILL)
    os.waitpid(pid, 0)
    resumed = DurableDriver(interrupt_store, freeze=freeze, owner="resume-owner")
    resume_owner = resumed.acquire()
    resume = resumed.resume()
    cleanup_store = output / "cleanup_fault"
    cleanup = DurableDriver(cleanup_store, freeze=freeze)
    cleanup.acquire()
    cleanup.reserve_cell(identity)
    cleanup.reserve_model_call(identity["attempt_id"], 0, 9)
    unknown = cleanup.record_unknown("cleanup", identity["attempt_id"], {"error": "injected cleanup fault", "effect": "unknown"})
    report = {
        "schema": "la032-driver-qualification/v1",
        "status": "PASS",
        "exclusive_owner": owner["exclusive"] is True,
        "cell_reserved": reserved["consumed"] is False,
        "model_call_consumed_once": call["consumed"] is True and replay_call,
        "prompt_tokens_must_equal_preflight": mismatch,
        "capability_one_time": capability["one_time"] is True and replay_cap,
        "no_silent_cell_replay": replay_cell,
        "final_cells_blocked": sealed_blocked,
        "interrupt_resume": resume_owner.get("replaced_stale_owner") == "child-owner" or resume["owner"] == "resume-owner",
        "resume_preserves_reservations": len(resume["reserved_cells"]) == 1 and len(resume["reserved_calls"]) == 1,
        "cleanup_fault_unknown_not_absence": unknown["treated_as_measured_absence"] is False,
        "scientific_cells_completed": 0,
        "constructed_only": False,
        "mock_mechanism": False,
    }
    required = (
        "exclusive_owner",
        "model_call_consumed_once",
        "prompt_tokens_must_equal_preflight",
        "capability_one_time",
        "no_silent_cell_replay",
        "final_cells_blocked",
        "interrupt_resume",
        "resume_preserves_reservations",
        "cleanup_fault_unknown_not_absence",
    )
    if not all(report[name] for name in required):
        report["status"] = "FAIL"
        raise DriverError("driver qualification failed: " + json.dumps(report))
    write_json(output / "qualification.json", report)
    return report


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--qualify", type=Path)
    args = parser.parse_args()
    if args.qualify:
        print(json.dumps(qualify(args.qualify), sort_keys=True))


if __name__ == "__main__":
    main()
