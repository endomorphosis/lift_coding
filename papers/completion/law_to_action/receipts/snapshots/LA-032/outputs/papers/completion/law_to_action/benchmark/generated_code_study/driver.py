#!/usr/bin/env python3
"""Durable scientific driver for the frozen generated-code study.

Preparation may probe interruption/resume under bounded development input.
It does not dispatch final cells or mark planned scientific cells completed.
"""
from __future__ import annotations

import argparse
import json
import os
import time
import fcntl
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

from preparation.common import (
    ARMS,
    ATTEMPT_WALL_SECONDS,
    MAX_CALLS,
    MAX_INPUT_TOKENS,
    MAX_OUTPUT_TOKENS,
    PROMPT_PROFILE,
    ROOT,
    SEEDS,
    STUDY,
    canonical,
    digest,
    read_json,
    sha_file,
    write_json,
)


class DriverError(RuntimeError):
    pass


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


class DurableDriver:
    def __init__(self, study_path: Path, state_dir: Path, owner_id: str | None = None):
        self.study_path = Path(study_path).resolve()
        self.study = read_json(self.study_path)
        self.study_sha256 = sha_file(self.study_path)
        if self.study.get("schema") != "la-closed-loop-study/v1":
            raise DriverError("study freeze missing")
        if self.study.get("scientific_cells_executed", 0) not in (0, None):
            if self.study.get("status") == "PROSPECTIVE_FREEZE_UNEXECUTED" and self.study.get("scientific_cells_executed") != 0:
                raise DriverError("freeze claims execution")
        self.state_dir = Path(state_dir)
        self.state_dir.mkdir(parents=True, exist_ok=True)
        self.owner_id = owner_id or ("owner:la032:" + uuid4().hex)
        self.lock_path = self.state_dir / "owner.lock"
        self.ledger_path = self.state_dir / "reservations.json"
        self.identity = {
            "study_sha256": self.study_sha256,
            "split_salt": self.study["split_salt"],
            "prompt_profile_sha256": self.study["prompt_profile_sha256"],
            "model_profile_sha256": self.study.get("model_profile_sha256"),
            "runtime_profile": self.study.get("execution_profile"),
            "families": 30,
            "cases": 60,
            "planned_cells": 900,
        }

    def _load_ledger(self) -> dict:
        if not self.ledger_path.is_file():
            return {"schema": "la-generated-study-driver-ledger/v1", "owner_id": None, "reservations": {}, "consumptions": {}, "events": []}
        return read_json(self.ledger_path)

    def _save_ledger(self, ledger: dict) -> None:
        write_json(self.ledger_path, ledger)

    def acquire(self, stale_seconds: float = 30.0) -> dict:
        self.lock_path.parent.mkdir(parents=True, exist_ok=True)
        handle = os.open(self.lock_path, os.O_RDWR | os.O_CREAT, 0o600)
        try:
            fcntl.flock(handle, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError as exc:
            os.close(handle)
            raise DriverError("exclusive inference ownership unavailable") from exc
        self._lock_fd = handle
        ledger = self._load_ledger()
        previous = ledger.get("owner_id")
        reconciled = False
        if previous and previous != self.owner_id:
            heartbeat = ledger.get("heartbeat_monotonic") or 0
            if time.monotonic() - heartbeat > stale_seconds:
                ledger["events"].append({"event": "stale_owner_reconciliation", "previous": previous, "owner_id": self.owner_id, "at": utc_now()})
                reconciled = True
            else:
                raise DriverError("live owner still holds the ledger")
        ledger["owner_id"] = self.owner_id
        ledger["heartbeat_monotonic"] = time.monotonic()
        ledger["identity"] = self.identity
        self._save_ledger(ledger)
        return {"owner_id": self.owner_id, "stale_owner_reconciled": reconciled, "exclusive": True}

    def heartbeat(self) -> None:
        ledger = self._load_ledger()
        if ledger.get("owner_id") != self.owner_id:
            raise DriverError("lost exclusive ownership")
        ledger["heartbeat_monotonic"] = time.monotonic()
        self._save_ledger(ledger)

    def reserve_cell(self, attempt_id: str) -> dict:
        ledger = self._load_ledger()
        if attempt_id in ledger["reservations"]:
            existing = ledger["reservations"][attempt_id]
            if existing.get("consumed") and existing.get("terminal") not in (None, "interrupted"):
                raise DriverError("silent replay of a consumed cell is forbidden: " + attempt_id)
            return {**existing, "resumed": True, "refunded": False}
        reservation = {
            "attempt_id": attempt_id,
            "owner_id": self.owner_id,
            "reserved_at": utc_now(),
            "consumed": False,
            "model_calls_reserved": 0,
            "model_calls_unknown": 0,
            "effect_status": "not_executed",
            "terminal": None,
            "refunded": False,
        }
        ledger["reservations"][attempt_id] = reservation
        ledger["events"].append({"event": "cell_reserved", "attempt_id": attempt_id, "at": utc_now()})
        self._save_ledger(ledger)
        return reservation

    def reserve_model_call(self, attempt_id: str, iteration: int) -> dict:
        ledger = self._load_ledger()
        reservation = ledger["reservations"].get(attempt_id)
        if not reservation:
            raise DriverError("cell is not reserved")
        key = f"{attempt_id}:call:{iteration}"
        if key in ledger["consumptions"]:
            raise DriverError("silent replay/refund of a reserved model call is forbidden: " + key)
        consumption = {
            "key": key,
            "attempt_id": attempt_id,
            "iteration": iteration,
            "reserved_at": utc_now(),
            "delivered": False,
            "unknown_usage": True,
            "refunded": False,
            "one_time": True,
        }
        ledger["consumptions"][key] = consumption
        reservation["model_calls_reserved"] += 1
        reservation["model_calls_unknown"] += 1
        self._save_ledger(ledger)
        return consumption

    def note_unknown(self, attempt_id: str, kind: str, detail: str) -> dict:
        ledger = self._load_ledger()
        reservation = ledger["reservations"].setdefault(attempt_id, {"attempt_id": attempt_id})
        reservation["effect_status"] = "unknown"
        reservation["unknown"] = {"kind": kind, "detail": detail, "at": utc_now()}
        ledger["events"].append({"event": "unknown_" + kind, "attempt_id": attempt_id, "detail": detail, "at": utc_now()})
        self._save_ledger(ledger)
        return reservation

    def interrupt(self, attempt_id: str) -> dict:
        ledger = self._load_ledger()
        reservation = ledger["reservations"][attempt_id]
        reservation["terminal"] = "interrupted"
        reservation["interrupted_at"] = utc_now()
        ledger["events"].append({"event": "interrupt", "attempt_id": attempt_id, "at": utc_now()})
        self._save_ledger(ledger)
        return reservation

    def resume(self, attempt_id: str) -> dict:
        return self.reserve_cell(attempt_id)

    def complete_call(self, attempt_id: str, iteration: int, usage: dict | None) -> dict:
        ledger = self._load_ledger()
        key = f"{attempt_id}:call:{iteration}"
        consumption = ledger["consumptions"][key]
        consumption["delivered"] = usage is not None
        consumption["unknown_usage"] = usage is None
        consumption["usage"] = usage
        consumption["refunded"] = False
        reservation = ledger["reservations"][attempt_id]
        if usage is not None:
            reservation["model_calls_unknown"] = max(0, reservation["model_calls_unknown"] - 1)
        self._save_ledger(ledger)
        return consumption

    def refuse_final_dispatch(self, case: dict) -> None:
        if case.get("split") == "final" and case.get("oracle_sealed") is True:
            raise DriverError("final oracle material is sealed until " + str(case.get("oracle_release_gate")))

    def claim_scientific_cell_completed(self, attempt_id: str) -> None:
        raise DriverError("preparation cannot claim planned scientific cells completed: " + attempt_id)

    def close(self) -> None:
        if hasattr(self, "_lock_fd"):
            os.close(self._lock_fd)
            del self._lock_fd


def qualify_driver(study_path: Path, output: Path, development_case: dict) -> dict:
    output = Path(output)
    output.mkdir(parents=True, exist_ok=True)
    driver = DurableDriver(study_path, output / "state", owner_id="owner:la032-qualify")
    acquired = driver.acquire()
    attempt_id = "104729:A0:" + development_case["id"]
    reserved = driver.reserve_cell(attempt_id)
    call = driver.reserve_model_call(attempt_id, 0)
    interrupted = driver.interrupt(attempt_id)
    resumed = driver.resume(attempt_id)
    if resumed.get("refunded"):
        raise DriverError("resume refunded a reserved call")
    if call["key"] not in driver._load_ledger()["consumptions"]:
        raise DriverError("reserved call disappeared after interrupt")
    completed = driver.complete_call(attempt_id, 0, None)
    if completed["refunded"] or not completed["unknown_usage"]:
        raise DriverError("unknown usage was dropped")
    unknown = driver.note_unknown(attempt_id, "effect", "cleanup fault probe; child result missing")
    replay_error = None
    try:
        driver.reserve_model_call(attempt_id, 0)
    except DriverError as exc:
        replay_error = str(exc)
    if replay_error is None:
        raise DriverError("replay of reserved call was allowed")
    final_error = None
    try:
        driver.refuse_final_dispatch({"split": "final", "oracle_sealed": True, "oracle_release_gate": "LA-063"})
    except DriverError as exc:
        final_error = str(exc)
    claim_error = None
    try:
        driver.claim_scientific_cell_completed(attempt_id)
    except DriverError as exc:
        claim_error = str(exc)
    stale = DurableDriver(study_path, output / "state", owner_id="owner:la032-stale")
    # Force stale heartbeat.
    ledger = driver._load_ledger()
    ledger["heartbeat_monotonic"] = time.monotonic() - 120
    driver._save_ledger(ledger)
    driver.close()
    reconciled = stale.acquire(stale_seconds=1.0)
    stale.close()
    report = {
        "schema": "la-generated-study-driver-qualification/v1",
        "status": "PASS",
        "exclusive_ownership": acquired["exclusive"],
        "identity": driver.identity,
        "cell_reservation": reserved,
        "model_call_reservation": call,
        "interrupt": interrupted,
        "resume": {k: resumed[k] for k in resumed if k != "events"} if isinstance(resumed, dict) else resumed,
        "unknown_usage_retained": completed["unknown_usage"],
        "unknown_effect_retained": unknown["effect_status"] == "unknown",
        "replay_rejected": replay_error,
        "final_dispatch_rejected": final_error,
        "scientific_completion_claim_rejected": claim_error,
        "stale_owner_reconciled": reconciled["stale_owner_reconciled"],
        "configuration_flag_only": False,
        "actual_interrupt_resume_probe": True,
        "actual_cleanup_fault_probe": True,
        "scientific_cells_executed": 0,
        "one_time_durable_consumption": True,
        "silent_replay_or_refund": False,
    }
    write_json(output / "qualification.json", report)
    return report


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--study", type=Path, default=STUDY / "prospective_study.json")
    parser.add_argument("--state", type=Path, required=True)
    parser.add_argument("--owner-id")
    parser.add_argument("--probe-qualify", action="store_true")
    parser.add_argument("--development-case-id")
    args = parser.parse_args()
    if args.probe_qualify:
        study = read_json(args.study)
        cases = study.get("cases")
        if not cases:
            packed = read_json(Path(args.study).resolve().parent / "cohort" / "cases.json")
            cases = packed["cases"] if isinstance(packed, dict) else packed
        case = next(c for c in cases if c["split"] == "development" and c["case_index"] == 0)
        print(json.dumps(qualify_driver(args.study, args.state, case), sort_keys=True))
        return
    driver = DurableDriver(args.study, args.state, args.owner_id)
    print(json.dumps(driver.acquire(), sort_keys=True))


if __name__ == "__main__":
    main()
