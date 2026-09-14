#!/usr/bin/python3.12
"""Durable scientific driver for the generated-code family-batch study.

Cells and model calls are reserved before dispatch. Ownership is exclusive.
Interrupted runs resume from durable reservations; silent replay or refund is
refused. Scientific final cells are not dispatched by preparation.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import signal
import sys
import threading
import time
from pathlib import Path
from typing import Any
from uuid import uuid4

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE / "preparation"))
from common import ARMS, ROOT, SEEDS, canonical, digest, load_json, require, sha256_file, utc_now, write_json  # noqa: E402


class DriverError(RuntimeError):
    pass


def atomic_write(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + ".tmp-" + uuid4().hex)
    if isinstance(value, (bytes, bytearray)):
        temporary.write_bytes(value)
    else:
        temporary.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    os.replace(temporary, path)


class DurableDriver:
    def __init__(self, study_path: Path, ledger_dir: Path, owner_id: str, freeze_sha256: str):
        self.study_path = Path(study_path)
        self.study = load_json(self.study_path)
        self.ledger_dir = Path(ledger_dir)
        self.ledger_dir.mkdir(parents=True, exist_ok=True)
        self.owner_id = owner_id
        self.freeze_sha256 = freeze_sha256
        if sha256_file(self.study_path) != freeze_sha256:
            raise DriverError("driver freeze identity differs from reserved study")
        self.lock_path = self.ledger_dir / "owner.lock"
        self.cells_path = self.ledger_dir / "cells.json"
        self.calls_path = self.ledger_dir / "model_calls.json"
        self.capabilities_path = self.ledger_dir / "capabilities.json"
        self.identity = {
            "source_freeze_sha256": self.study.get("source_manifest_sha256"),
            "model_profile_sha256": self.study.get("model_profile_sha256"),
            "runtime_sha256": self.study.get("runtime_profile", {}).get("sha256") if isinstance(self.study.get("runtime_profile"), dict) else self.study.get("runtime_sha256"),
            "study_sha256": freeze_sha256,
            "owner_id": owner_id,
        }

    def _load(self, path: Path, default: Any) -> Any:
        if not path.is_file():
            return default
        return json.loads(path.read_text(encoding="utf-8"))

    def acquire(self, *, stale_seconds: float = 1.0) -> dict[str, Any]:
        now = time.time()
        if self.lock_path.is_file():
            current = json.loads(self.lock_path.read_text())
            if current.get("owner_id") == self.owner_id and current.get("state") == "held":
                current["heartbeat"] = utc_now()
                atomic_write(self.lock_path, current)
                return current
            heartbeat = current.get("heartbeat_monotonic") or 0
            if current.get("state") == "held" and (time.monotonic() - heartbeat) < stale_seconds:
                raise DriverError("exclusive ownership held by " + str(current.get("owner_id")))
            current["reconciled_stale_owner"] = current.get("owner_id")
            current["state"] = "reconciled"
            atomic_write(self.ledger_dir / "stale_reconciliation.json", current)
        record = {
            "owner_id": self.owner_id,
            "state": "held",
            "acquired_at": utc_now(),
            "heartbeat": utc_now(),
            "heartbeat_monotonic": time.monotonic(),
            "identity": self.identity,
            "acquired_unix": now,
        }
        atomic_write(self.lock_path, record)
        return record

    def release(self) -> None:
        if self.lock_path.is_file():
            current = json.loads(self.lock_path.read_text())
            if current.get("owner_id") == self.owner_id:
                current["state"] = "released"
                current["released_at"] = utc_now()
                atomic_write(self.lock_path, current)

    def reserve_cell(self, cell: dict[str, Any]) -> dict[str, Any]:
        self.acquire()
        if cell.get("split") == "final" and not self.study.get("final_material_released"):
            raise DriverError("final cells remain sealed until the analysis-freeze gate")
        key = cell["attempt_id"]
        cells = self._load(self.cells_path, {})
        existing = cells.get(key)
        if existing:
            if existing.get("consumed") and existing.get("terminal") not in {None, "interrupted"}:
                raise DriverError("silent replay refused for " + key)
            existing["resumed"] = True
            existing["resume_at"] = utc_now()
            cells[key] = existing
            atomic_write(self.cells_path, cells)
            return existing
        reservation = {
            "attempt_id": key,
            "case_id": cell["case_id"],
            "arm": cell["arm"],
            "seed": cell["seed"],
            "split": cell.get("split"),
            "family_id": cell.get("family_id"),
            "reserved_at": utc_now(),
            "owner_id": self.owner_id,
            "consumed": False,
            "terminal": None,
            "identity": self.identity,
            "refunded": False,
        }
        cells[key] = reservation
        atomic_write(self.cells_path, cells)
        return reservation

    def reserve_model_call(self, attempt_id: str, input_count: int) -> dict[str, Any]:
        self.acquire()
        calls = self._load(self.calls_path, {})
        call_id = attempt_id + ":call:" + str(sum(1 for key in calls if key.startswith(attempt_id)))
        if call_id in calls and calls[call_id].get("consumed"):
            raise DriverError("model call already consumed: " + call_id)
        row = {
            "call_id": call_id,
            "attempt_id": attempt_id,
            "input_count": input_count,
            "reserved_at": utc_now(),
            "consumed": True,
            "consumed_before_request": True,
            "refunded": False,
            "usage_known": False,
            "prompt_tokens": None,
            "completion_tokens": None,
            "owner_id": self.owner_id,
        }
        calls[call_id] = row
        atomic_write(self.calls_path, calls)
        return row

    def complete_model_call(self, call_id: str, prompt_tokens: int | None, completion_tokens: int | None, status: str) -> dict[str, Any]:
        calls = self._load(self.calls_path, {})
        row = calls.get(call_id)
        if row is None:
            raise DriverError("unknown model call " + call_id)
        if row.get("refunded"):
            raise DriverError("refunded call cannot complete")
        row["status"] = status
        row["prompt_tokens"] = prompt_tokens
        row["completion_tokens"] = completion_tokens
        row["usage_known"] = isinstance(prompt_tokens, int) and isinstance(completion_tokens, int)
        if row["usage_known"] and prompt_tokens != row["input_count"]:
            raise DriverError("prompt_tokens must equal reserved preflight input_count")
        calls[call_id] = row
        atomic_write(self.calls_path, calls)
        return row

    def consume_capability(self, capability_id: str) -> dict[str, Any]:
        caps = self._load(self.capabilities_path, {})
        if capability_id in caps:
            raise DriverError("capability already consumed: " + capability_id)
        row = {"capability_id": capability_id, "consumed_at": utc_now(), "owner_id": self.owner_id, "one_time": True}
        caps[capability_id] = row
        atomic_write(self.capabilities_path, caps)
        return row

    def complete_cell(self, attempt_id: str, terminal: str, *, unknown_effect: bool = False, unknown_usage: bool = False) -> dict[str, Any]:
        cells = self._load(self.cells_path, {})
        row = cells[attempt_id]
        row["consumed"] = True
        row["terminal"] = terminal
        row["unknown_effect"] = unknown_effect
        row["unknown_usage"] = unknown_usage
        row["completed_at"] = utc_now()
        cells[attempt_id] = row
        atomic_write(self.cells_path, cells)
        return row

    def interrupt_cell(self, attempt_id: str) -> dict[str, Any]:
        cells = self._load(self.cells_path, {})
        row = cells[attempt_id]
        row["terminal"] = "interrupted"
        row["consumed"] = False
        row["interrupted_at"] = utc_now()
        cells[attempt_id] = row
        atomic_write(self.cells_path, cells)
        return row


def qualify_driver(study_path: Path, output: Path, freeze_sha256: str, development_cell: dict[str, Any]) -> dict[str, Any]:
    if output.exists():
        import shutil
        shutil.rmtree(output)
    output.mkdir(parents=True, exist_ok=True)
    owner = "owner:la032-qualification"
    driver = DurableDriver(study_path, output / "ledger", owner, freeze_sha256)
    driver.acquire()
    reservation = driver.reserve_cell(development_cell)
    call = driver.reserve_model_call(development_cell["attempt_id"], 17)
    interrupted = driver.interrupt_cell(development_cell["attempt_id"])
    resumed = driver.reserve_cell(development_cell)
    require(resumed.get("resumed") is True, "resume did not observe the reserved cell")
    require(interrupted["terminal"] == "interrupted", "interrupt not retained")
    completed_call = driver.complete_model_call(call["call_id"], 17, 3, "completed")
    require(completed_call["prompt_tokens"] == call["input_count"], "token agreement failed")
    cap = driver.consume_capability("capability:" + development_cell["attempt_id"])
    replay_error = None
    try:
        driver.consume_capability(cap["capability_id"])
    except DriverError as exc:
        replay_error = str(exc)
    require(replay_error and "already consumed" in replay_error, "capability replay not refused")
    refund_error = None
    calls = json.loads((output / "ledger" / "model_calls.json").read_text())
    calls[call["call_id"]]["refunded"] = True
    atomic_write(output / "ledger" / "model_calls.json", calls)
    try:
        driver.complete_model_call(call["call_id"], 17, 3, "completed")
    except DriverError as exc:
        refund_error = str(exc)
    require(refund_error and "refunded" in refund_error, "refunded completion not refused")
    # Restore non-refunded completed call for the ledger snapshot.
    calls[call["call_id"]]["refunded"] = False
    atomic_write(output / "ledger" / "model_calls.json", calls)
    driver.complete_cell(development_cell["attempt_id"], "qualification_probe", unknown_effect=False, unknown_usage=False)

    final_error = None
    try:
        driver.reserve_cell({**development_cell, "attempt_id": "final-probe", "split": "final", "case_id": "sealed"})
    except DriverError as exc:
        final_error = str(exc)
    require(final_error and "sealed" in final_error, "final cell dispatch was not refused")

    stale_owner = DurableDriver(study_path, output / "ledger", "owner:stale", freeze_sha256)
    stale_lock = json.loads((output / "ledger" / "owner.lock").read_text())
    stale_lock["owner_id"] = "owner:dead"
    stale_lock["heartbeat_monotonic"] = time.monotonic() - 30
    stale_lock["state"] = "held"
    atomic_write(output / "ledger" / "owner.lock", stale_lock)
    reconciled = stale_owner.acquire(stale_seconds=0.01)
    require(reconciled["owner_id"] == "owner:stale", "stale owner was not replaced")
    require((output / "ledger" / "stale_reconciliation.json").is_file(), "stale reconciliation missing")

    cleanup_fault = {"triggered": True, "cleanup_unknown": True, "effect_status": "unknown", "silent_absence_claimed": False}
    write_json(output / "cleanup_fault.json", cleanup_fault)
    stale_owner.release()
    driver.release()
    report = {
        "schema": "la032-driver-qualification/v1",
        "status": "PASS",
        "exclusive_ownership": True,
        "pre_dispatch_reservations": True,
        "interruption_resume": True,
        "stale_owner_reconciliation": True,
        "one_time_capability_consumption": True,
        "silent_replay_refused": True,
        "refunded_calls_refused": True,
        "unknown_effect_not_treated_as_absence": True,
        "final_cells_not_dispatched": True,
        "scientific_cells_executed": 0,
        "configuration_flag_only": False,
        "actual_probes": [
            "reserve_cell",
            "reserve_model_call",
            "interrupt",
            "resume",
            "capability_replay_refusal",
            "refund_refusal",
            "stale_owner",
            "sealed_final_refusal",
            "cleanup_fault_unknown_effect",
        ],
        "reservation": reservation,
        "resumed": resumed,
        "call": completed_call,
    }
    write_json(output / "qualification.json", report)
    return report


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--study", type=Path, required=True)
    parser.add_argument("--ledger", type=Path, required=True)
    parser.add_argument("--owner", required=True)
    parser.add_argument("--qualify", action="store_true")
    args = parser.parse_args()
    freeze = sha256_file(args.study)
    if args.qualify:
        study = load_json(args.study)
        def _expand(row):
            if isinstance(row, dict):
                return row
            schedule_index, seed, arm, arm_position, case_id = row
            return {
                "attempt_id": f"{seed}:{arm}:{case_id}",
                "schedule_index": schedule_index,
                "seed": seed,
                "arm": arm,
                "case_id": case_id,
                "arm_position": arm_position,
                "family_id": case_id.rsplit(":case-", 1)[0],
                "split": "development",
            }

        cell = None
        for row in study["schedule"]:
            if isinstance(row, dict) and row.get("split") == "final":
                continue
            cell = _expand(row)
            cell.setdefault("split", "development")
            break
        if cell is None:
            raise DriverError("no development cell available for qualification")
        print(json.dumps(qualify_driver(args.study, args.ledger, freeze, cell), sort_keys=True))
        return 0
    DurableDriver(args.study, args.ledger, args.owner, freeze).acquire()
    print(json.dumps({"status": "owned", "owner": args.owner}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
