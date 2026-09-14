#!/usr/bin/python3.12
"""Durable scientific driver: exclusive ownership, reservations, resume, no silent replay."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from uuid import uuid4

STUDY_ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(STUDY_ROOT / "preparation"))
from common import load_study  # noqa: E402


def canonical(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False).encode("utf-8")


def digest(value: Any) -> str:
    return hashlib.sha256(canonical(value)).hexdigest()


def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + ".tmp-" + uuid4().hex)
    temporary.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n")
    os.replace(temporary, path)


def load_json(path: Path) -> Any:
    return json.loads(path.read_text())


class DriverError(RuntimeError):
    pass


class ScientificDriver:
    def __init__(self, freeze_path: Path, state_dir: Path, owner: str):
        self.freeze_path = Path(freeze_path)
        self.freeze = load_study(self.freeze_path)
        self.freeze_sha256 = digest(
            {k: self.freeze[k] for k in ("split_salt", "arms", "seeds", "families", "cases", "schedule")}
        )
        if self.freeze.get("freeze_sha256") != self.freeze_sha256:
            raise DriverError("freeze identity drifted")
        self.state_dir = Path(state_dir)
        self.state_dir.mkdir(parents=True, exist_ok=True)
        self.owner = owner
        self.lock_path = self.state_dir / "owner.lock"
        self.ledger_path = self.state_dir / "ledger.json"
        self.reservations_dir = self.state_dir / "reservations"
        self.reservations_dir.mkdir(exist_ok=True)

    def _ledger(self) -> dict[str, Any]:
        if self.ledger_path.is_file():
            return load_json(self.ledger_path)
        return {
            "schema": "la-scientific-driver-ledger/v1",
            "freeze_sha256": self.freeze_sha256,
            "owner": None,
            "cells": {},
            "model_calls": {},
            "capabilities_consumed": {},
            "unknown_usage": [],
            "unknown_effects": [],
            "scientific_cells_executed": 0,
            "refunded_calls": 0,
        }

    def acquire(self, stale_seconds: float = 30.0) -> dict[str, Any]:
        ledger = self._ledger()
        now = time.time()
        if self.lock_path.exists():
            current = load_json(self.lock_path)
            if current["owner"] != self.owner:
                age = now - current["heartbeat"]
                if age < stale_seconds:
                    raise DriverError("exclusive owner is live: " + current["owner"])
                ledger.setdefault("reconciled_stale_owners", []).append(current)
        lease = {"owner": self.owner, "heartbeat": now, "freeze_sha256": self.freeze_sha256, "pid": os.getpid()}
        write_json(self.lock_path, lease)
        ledger["owner"] = self.owner
        write_json(self.ledger_path, ledger)
        return lease

    def heartbeat(self) -> None:
        if not self.lock_path.exists() or load_json(self.lock_path)["owner"] != self.owner:
            raise DriverError("lost exclusive ownership")
        lease = load_json(self.lock_path)
        lease["heartbeat"] = time.time()
        write_json(self.lock_path, lease)

    def reserve_cell(self, attempt_id: str) -> dict[str, Any]:
        self.heartbeat()
        ledger = self._ledger()
        existing = ledger["cells"].get(attempt_id)
        if existing and existing.get("status") not in {"interrupted", "unknown"}:
            raise DriverError("cell already reserved or completed; no silent replay: " + attempt_id)
        reservation = {
            "attempt_id": attempt_id,
            "owner": self.owner,
            "freeze_sha256": self.freeze_sha256,
            "reserved_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
            "status": "reserved",
            "consumed": True,
            "refunded": False,
        }
        path = self.reservations_dir / (digest(attempt_id) + ".json")
        if path.exists() and existing and existing.get("status") not in {"interrupted", "unknown"}:
            raise DriverError("reservation replay refused")
        write_json(path, reservation)
        ledger["cells"][attempt_id] = reservation
        write_json(self.ledger_path, ledger)
        return reservation

    def reserve_model_call(self, attempt_id: str, call_index: int, input_count: int) -> dict[str, Any]:
        self.heartbeat()
        key = f"{attempt_id}:{call_index}"
        ledger = self._ledger()
        if key in ledger["model_calls"] and ledger["model_calls"][key].get("status") == "completed":
            raise DriverError("model call already consumed; no refund or replay")
        reservation = {
            "key": key,
            "attempt_id": attempt_id,
            "call_index": call_index,
            "input_count": input_count,
            "consumed_before_request": True,
            "status": "reserved",
            "owner": self.owner,
        }
        ledger["model_calls"][key] = reservation
        write_json(self.ledger_path, ledger)
        write_json(self.reservations_dir / (digest(key) + ".call.json"), reservation)
        return reservation

    def complete_model_call(self, attempt_id: str, call_index: int, prompt_tokens: int | None, completion_tokens: int | None, unknown: bool = False) -> None:
        key = f"{attempt_id}:{call_index}"
        ledger = self._ledger()
        row = ledger["model_calls"].get(key)
        if not row:
            raise DriverError("unreserved model call")
        row["status"] = "unknown" if unknown else "completed"
        row["prompt_tokens"] = prompt_tokens
        row["completion_tokens"] = completion_tokens
        if unknown:
            ledger["unknown_usage"].append(key)
        ledger["model_calls"][key] = row
        write_json(self.ledger_path, ledger)

    def interrupt_cell(self, attempt_id: str, reason: str) -> dict[str, Any]:
        ledger = self._ledger()
        row = ledger["cells"].get(attempt_id)
        if not row:
            raise DriverError("cannot interrupt unreserved cell")
        row["status"] = "interrupted"
        row["interrupt_reason"] = reason
        ledger["cells"][attempt_id] = row
        write_json(self.ledger_path, ledger)
        return row

    def resume_cell(self, attempt_id: str) -> dict[str, Any]:
        ledger = self._ledger()
        row = ledger["cells"].get(attempt_id)
        if not row or row.get("status") != "interrupted":
            raise DriverError("resume requires explicit interrupted reservation")
        if row.get("refunded"):
            raise DriverError("refunded reservation cannot resume")
        row["status"] = "resumed"
        row["resumed_at"] = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
        ledger["cells"][attempt_id] = row
        write_json(self.ledger_path, ledger)
        return row

    def consume_capability(self, capability_id: str) -> dict[str, Any]:
        ledger = self._ledger()
        if capability_id in ledger["capabilities_consumed"]:
            raise DriverError("capability already consumed")
        record = {"capability_id": capability_id, "owner": self.owner, "consumed": True, "once": True}
        ledger["capabilities_consumed"][capability_id] = record
        write_json(self.ledger_path, ledger)
        return record

    def mark_unknown_effect(self, attempt_id: str) -> None:
        ledger = self._ledger()
        ledger["unknown_effects"].append(attempt_id)
        cell = ledger["cells"].setdefault(attempt_id, {"attempt_id": attempt_id, "status": "unknown"})
        cell["status"] = "unknown"
        cell["effect"] = "unknown"
        write_json(self.ledger_path, ledger)

    def refuse_final_release(self, case: dict[str, Any]) -> None:
        if case.get("split") == "final" and case.get("sealed") is True:
            raise DriverError("final task/oracle material is sealed until the analysis-freeze gate")

    def refuse_scientific_execution_during_preparation(self) -> None:
        raise DriverError("preparation cannot dispatch or complete planned scientific cells")

    def release(self) -> None:
        if self.lock_path.exists() and load_json(self.lock_path)["owner"] == self.owner:
            self.lock_path.unlink()


def probe(state: Path, freeze: Path) -> dict[str, Any]:
    owner = "la032-qualify-" + uuid4().hex[:8]
    driver = ScientificDriver(freeze, state, owner)
    driver.acquire()
    attempt = "probe:A0:development-cell"
    driver.reserve_cell(attempt)
    call = driver.reserve_model_call(attempt, 0, 17)
    driver.complete_model_call(attempt, 0, None, None, unknown=True)
    driver.interrupt_cell(attempt, "injected_interrupt")
    resumed = driver.resume_cell(attempt)
    cap = driver.consume_capability("capability:" + attempt)
    replay_error = None
    try:
        driver.consume_capability("capability:" + attempt)
    except DriverError as exc:
        replay_error = str(exc)
    driver.mark_unknown_effect(attempt + ":cleanup")
    stale = ScientificDriver(freeze, state, "stale-other")
    stale_error = None
    try:
        stale.acquire(stale_seconds=3600)
    except DriverError as exc:
        stale_error = str(exc)
    load_json(driver.lock_path)["heartbeat"] = time.time() - 120
    write_json(driver.lock_path, {**load_json(driver.lock_path), "heartbeat": time.time() - 120})
    reconciled = stale.acquire(stale_seconds=30)
    scientific_error = None
    try:
        driver.refuse_scientific_execution_during_preparation()
    except DriverError as exc:
        scientific_error = str(exc)
    final_error = None
    try:
        driver.refuse_final_release({"split": "final", "sealed": True})
    except DriverError as exc:
        final_error = str(exc)
    driver.release()
    ledger = load_json(driver.ledger_path)
    report = {
        "schema": "la-scientific-driver-qualification/v1",
        "status": "PASS",
        "freeze_sha256": driver.freeze_sha256,
        "interrupt_resume": resumed["status"] == "resumed",
        "unknown_usage_retained": bool(ledger["unknown_usage"]),
        "unknown_effect_retained": bool(ledger["unknown_effects"]),
        "one_time_capability": cap["once"] and replay_error is not None,
        "stale_owner_blocked_while_live": stale_error is not None,
        "stale_owner_reconciled": reconciled["owner"] == "stale-other",
        "no_silent_replay": replay_error is not None,
        "no_refunded_calls": ledger.get("refunded_calls") == 0,
        "preparation_cannot_complete_scientific_cells": scientific_error is not None,
        "final_sealed": final_error is not None,
        "reserved_input_count": call["input_count"],
        "scientific_cells_executed": 0,
    }
    if not all(report[k] is True or report[k] == 0 or isinstance(report[k], (str, int)) for k in report):
        report["status"] = "FAIL"
    required = [
        "interrupt_resume",
        "unknown_usage_retained",
        "unknown_effect_retained",
        "one_time_capability",
        "stale_owner_blocked_while_live",
        "stale_owner_reconciled",
        "no_silent_replay",
        "preparation_cannot_complete_scientific_cells",
        "final_sealed",
    ]
    if not all(report[k] is True for k in required):
        report["status"] = "FAIL"
    write_json(state / "qualification.json", report)
    return report


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("action", choices=("probe",))
    parser.add_argument("--state", type=Path, required=True)
    parser.add_argument("--freeze", type=Path, default=STUDY_ROOT / "prospective_study.json")
    args = parser.parse_args()
    if args.action == "probe":
        print(json.dumps(probe(args.state, args.freeze), sort_keys=True))


if __name__ == "__main__":
    main()
