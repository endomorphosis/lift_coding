#!/usr/bin/env python3
"""Durable scientific driver for the generated-code family-batch study.

Reserves each case-arm-seed cell and each model call before dispatch. Exclusive
ownership, interruption/resume, stale-owner reconciliation, unknown usage/effect
handling, and one-time durable capability consumption are mandatory. Silent
replay and refunded calls are refused. Preparation never dispatches final cells
or marks planned scientific cells completed.
"""
from __future__ import annotations

import argparse
import fcntl
import json
import os
import signal
import time
from pathlib import Path
import sys

PREP = Path(__file__).resolve().parent / "preparation"
if str(PREP) not in sys.path:
    sys.path.insert(0, str(PREP))

from common import ARMS, SEEDS, digest, read_json, sha_file, study_root, write_json
from study_profile import execute_candidate, messages_for, permitted_program, forbidden_program


SCHEMA = "la-generated-study-driver/v1"


class DriverError(RuntimeError):
    pass


class DurableDriver:
    def __init__(self, freeze: dict, state_dir: Path, owner_id: str, *, allow_final: bool = False):
        self.freeze = freeze
        self.state_dir = Path(state_dir)
        self.state_dir.mkdir(parents=True, exist_ok=True)
        self.owner_id = owner_id
        self.allow_final = allow_final
        self.lock_path = self.state_dir / "owner.lock"
        self.owner_path = self.state_dir / "owner.json"
        self.ledger_path = self.state_dir / "ledger.jsonl"
        self.cells_dir = self.state_dir / "cells"
        self.calls_dir = self.state_dir / "calls"
        self.cells_dir.mkdir(exist_ok=True)
        self.calls_dir.mkdir(exist_ok=True)
        self.lock_handle = None
        self.freeze_sha256 = digest({
            "prospective": freeze.get("freeze_identity"),
            "model": freeze.get("model_profile_sha256"),
            "runtime": freeze.get("runtime_sha256"),
            "schedule": freeze.get("schedule_sha256"),
        })

    def acquire(self) -> dict:
        self.lock_handle = self.lock_path.open("a+")
        fcntl.flock(self.lock_handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        existing = read_json(self.owner_path) if self.owner_path.is_file() else None
        if existing and existing.get("owner_id") not in (None, self.owner_id) and existing.get("alive"):
            raise DriverError("stale or foreign exclusive owner holds the schedule")
        record = {
            "schema": SCHEMA,
            "owner_id": self.owner_id,
            "pid": os.getpid(),
            "alive": True,
            "freeze_sha256": self.freeze_sha256,
            "acquired_monotonic": time.monotonic(),
            "allow_final": self.allow_final,
            "scientific_execution_allowed": False if not self.allow_final else True,
        }
        write_json(self.owner_path, record)
        self._ledger({"event": "acquire", "owner_id": self.owner_id, "pid": os.getpid()})
        return record

    def reconcile_stale_owner(self, expected_owner: str) -> dict:
        existing = read_json(self.owner_path) if self.owner_path.is_file() else None
        if not existing:
            return {"status": "no_owner"}
        pid = existing.get("pid")
        alive = False
        if isinstance(pid, int) and pid > 0:
            try:
                os.kill(pid, 0)
                alive = True
            except OSError:
                alive = False
        if alive and existing.get("owner_id") != expected_owner:
            raise DriverError("live foreign owner cannot be stolen")
        if not alive:
            existing["alive"] = False
            existing["reconciled_stale"] = True
            existing["reconciled_by"] = expected_owner
            write_json(self.owner_path, existing)
            self._ledger({"event": "stale_owner_reconciled", "previous": existing.get("owner_id"), "pid": pid})
        return {"status": "reconciled" if not alive else "live_self", "previous": existing}

    def release(self) -> None:
        if self.owner_path.is_file():
            owner = read_json(self.owner_path)
            owner["alive"] = False
            owner["released"] = True
            write_json(self.owner_path, owner)
        self._ledger({"event": "release", "owner_id": self.owner_id})
        if self.lock_handle:
            fcntl.flock(self.lock_handle.fileno(), fcntl.LOCK_UN)
            self.lock_handle.close()
            self.lock_handle = None

    def _ledger(self, row: dict) -> None:
        row = dict(row)
        row["monotonic"] = time.monotonic()
        with self.ledger_path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(row, sort_keys=True, separators=(",", ":")) + "\n")

    def cell_path(self, attempt_id: str) -> Path:
        return self.cells_dir / attempt_id.replace(":", "_")

    def reserve_cell(self, slot: dict) -> dict:
        if slot["arm"] not in ARMS or slot["seed"] not in SEEDS:
            raise DriverError("identity outside original arm/seed contract")
        family = slot.get("family") or {}
        if family.get("split") == "final" and not self.allow_final:
            raise DriverError("preparation cannot dispatch final cells")
        if slot.get("scientific") and not self.allow_final:
            raise DriverError("preparation cannot claim planned scientific cells")
        directory = self.cell_path(slot["attempt_id"])
        directory.mkdir(exist_ok=True)
        reservation_path = directory / "reservation.json"
        if reservation_path.is_file():
            existing = read_json(reservation_path)
            if existing.get("consumed"):
                raise DriverError("silent replay of a consumed cell is forbidden")
            if existing.get("owner_id") != self.owner_id and existing.get("consumed"):
                raise DriverError("foreign consumed reservation cannot be refunded")
            return existing
        reservation = {
            "schema": "la-cell-reservation/v1",
            "attempt_id": slot["attempt_id"],
            "case_id": slot["case_id"],
            "arm": slot["arm"],
            "seed": slot["seed"],
            "schedule_index": slot.get("schedule_index"),
            "owner_id": self.owner_id,
            "freeze_sha256": self.freeze_sha256,
            "consumed": False,
            "scientific": bool(slot.get("scientific")),
            "split": family.get("split") or slot.get("split"),
        }
        write_json(reservation_path, reservation)
        self._ledger({"event": "reserve_cell", "attempt_id": slot["attempt_id"]})
        return reservation

    def reserve_model_call(self, attempt_id: str, iteration: int, input_count: int) -> dict:
        if not 0 <= iteration < 8:
            raise DriverError("original 8-call contract exceeded")
        if input_count > 2048:
            raise DriverError("original 2048 input-token contract exceeded")
        directory = self.calls_dir / f"{attempt_id.replace(':', '_')}-{iteration:02d}"
        directory.mkdir(exist_ok=True)
        path = directory / "reservation.json"
        if path.is_file():
            existing = read_json(path)
            if existing.get("consumed"):
                raise DriverError("silent replay of a consumed model call is forbidden")
            return existing
        reservation = {
            "schema": "la-model-call-reservation/v1",
            "attempt_id": attempt_id,
            "iteration": iteration,
            "input_count": input_count,
            "max_output_tokens": 1024,
            "owner_id": self.owner_id,
            "consumed": False,
            "paid_budget": 0,
        }
        write_json(path, reservation)
        self._ledger({"event": "reserve_model_call", "attempt_id": attempt_id, "iteration": iteration, "input_count": input_count})
        return reservation

    def consume(self, path: Path, extra: dict) -> dict:
        record = read_json(path)
        if record.get("consumed"):
            raise DriverError("one-time durable capability already consumed")
        record["consumed"] = True
        record.update(extra)
        write_json(path, record)
        self._ledger({"event": "consume", "path": str(path), **{k: extra.get(k) for k in ("attempt_id", "status", "unknown") if k in extra}})
        return record

    def run_constructed_cell(self, slot: dict, task: dict, program: str, interrupt_after: float | None = None) -> dict:
        reservation = self.reserve_cell(slot)
        directory = self.cell_path(slot["attempt_id"])
        started = time.monotonic()
        if interrupt_after is not None:
            def _stop(*_args):
                raise KeyboardInterrupt("driver interruption probe")
            signal.signal(signal.SIGALRM, _stop)
            signal.setitimer(signal.ITIMER_REAL, interrupt_after)
        try:
            result = execute_candidate(task, slot["arm"], program, directory / "execution")
            status = "completed"
            unknown = False
            self.consume(directory / "reservation.json", {
                "status": status,
                "unknown": unknown,
                "useful_work": result["useful_work"],
                "forbidden_effect": result["forbidden_effect"],
                "wall_seconds": time.monotonic() - started,
                "model_calls": 0,
                "paid_budget": 0,
            })
            write_json(directory / "result.json", result)
            return read_json(directory / "reservation.json")
        except KeyboardInterrupt:
            self.consume(directory / "reservation.json", {
                "status": "interrupted",
                "unknown": True,
                "effect_status": "unknown",
                "wall_seconds": time.monotonic() - started,
                "model_calls": 0,
                "requires_reconciliation": True,
            })
            self._ledger({"event": "interrupted", "attempt_id": slot["attempt_id"]})
            raise
        finally:
            signal.setitimer(signal.ITIMER_REAL, 0)

    def resume_unconsumed(self, slots, tasks, programs) -> list:
        results = []
        for slot in slots:
            path = self.cell_path(slot["attempt_id"]) / "reservation.json"
            if path.is_file() and read_json(path).get("consumed"):
                results.append(read_json(path))
                continue
            task = tasks[slot["case_id"]]
            program = programs[slot["case_id"]]
            results.append(self.run_constructed_cell(slot, task, program))
        return results


def load_freeze(study_path: Path) -> dict:
    study = read_json(study_path)
    return {
        "study": study,
        "freeze_identity": study.get("freeze_identity"),
        "model_profile_sha256": study.get("model_profile_sha256"),
        "runtime_sha256": study.get("runtime_sha256"),
        "schedule_sha256": study.get("schedule_sha256"),
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--study", type=Path, required=True)
    parser.add_argument("--state", type=Path, required=True)
    parser.add_argument("--owner-id", required=True)
    parser.add_argument("--probe", choices=("none", "interrupt-resume", "stale-owner", "cleanup-fault"), default="none")
    args = parser.parse_args()
    freeze = load_freeze(args.study)
    driver = DurableDriver(freeze, args.state, args.owner_id, allow_final=False)
    if args.probe == "stale-owner":
        print(json.dumps(driver.reconcile_stale_owner(args.owner_id), sort_keys=True))
        return
    driver.acquire()
    try:
        print(json.dumps({"status": "owned", "owner_id": args.owner_id, "freeze_sha256": driver.freeze_sha256}, sort_keys=True))
    finally:
        if args.probe != "interrupt-resume":
            driver.release()


if __name__ == "__main__":
    main()
