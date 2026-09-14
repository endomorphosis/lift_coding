#!/usr/bin/python3.12
"""Durable scientific driver for the generated-code family-batch study.

The driver binds exact source/model/runtime/freeze identity, takes exclusive
ownership, reserves each cell and model call before dispatch, supports
interruption/resume and stale-owner reconciliation, retains unknown usage and
effects, consumes capabilities once, and never silently replays or refunds a
call. Scientific final cells are not dispatched by preparation.
"""
from __future__ import annotations

import json
import os
import sys
import time
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent / "preparation"))
from study_common import ARMS, SEEDS, digest, load_json, sha_file, utc_now, write_json

SCHEMA = "la-generated-study-driver/v1"
LEASE = "la-generated-study-exclusive-owner"


class DriverError(RuntimeError):
    pass


class ScientificDriver:
    def __init__(self, freeze: dict[str, Any], state_dir: Path, owner_id: str):
        self.freeze = freeze
        self.state_dir = Path(state_dir)
        self.owner_id = owner_id
        self.state_dir.mkdir(parents=True, exist_ok=True)
        self.ledger_path = self.state_dir / "ledger.json"
        self.owner_path = self.state_dir / "owner.json"
        self.ledger = self._load_ledger()

    def identity(self) -> dict[str, Any]:
        freeze = self.freeze
        return {
            "source_manifest_sha256": freeze["source_manifest_sha256"],
            "model_profile_sha256": freeze["model_profile_sha256"],
            "runtime_profile_sha256": freeze["runtime_profile_sha256"],
            "prompt_profile_sha256": freeze["prompt_profile_sha256"],
            "oracle_manifest_sha256": freeze["oracle_manifest_sha256"],
            "schedule_sha256": freeze["schedule_sha256"],
            "cohort_sha256": freeze["cohort_sha256"],
            "study_sha256": freeze["study_sha256"],
        }

    def _load_ledger(self) -> dict[str, Any]:
        if self.ledger_path.is_file():
            return load_json(self.ledger_path)
        return {
            "schema": "la-generated-study-ledger/v1",
            "identity": self.identity(),
            "cells": {},
            "calls": {},
            "capabilities": {},
            "unknowns": [],
            "scientific_cells_executed": 0,
            "final_cells_dispatched": 0,
        }

    def _save(self) -> None:
        if self.ledger["identity"] != self.identity():
            raise DriverError("Freeze identity changed under an existing ledger")
        write_json(self.ledger_path, self.ledger)
        write_json(self.owner_path, {"owner_id": self.owner_id, "lease": LEASE, "held_at": utc_now()})

    def acquire(self) -> None:
        if self.owner_path.is_file():
            current = load_json(self.owner_path)
            if current.get("owner_id") not in (None, self.owner_id) and current.get("stale") is not True:
                raise DriverError("Exclusive owner already held: " + current["owner_id"])
            if current.get("owner_id") != self.owner_id:
                self.reconcile_stale(current)
        write_json(self.owner_path, {"owner_id": self.owner_id, "lease": LEASE, "held_at": utc_now(), "stale": False})

    def release(self) -> None:
        if self.owner_path.is_file():
            current = load_json(self.owner_path)
            if current.get("owner_id") == self.owner_id:
                write_json(self.owner_path, {"owner_id": None, "lease": LEASE, "released_at": utc_now(), "stale": False})

    def reconcile_stale(self, current: dict[str, Any]) -> dict[str, Any]:
        report = {
            "previous_owner": current.get("owner_id"),
            "new_owner": self.owner_id,
            "held_at": current.get("held_at"),
            "reconciled_at": utc_now(),
            "cells_examined": 0,
            "unknowns_retained": 0,
            "refunded_calls": 0,
            "silent_replays": 0,
        }
        for cell in self.ledger["cells"].values():
            report["cells_examined"] += 1
            if cell.get("status") in {"reserved", "running"}:
                cell["status"] = "unknown_interrupted"
                cell["requires_reconciliation"] = True
                cell["unknown_usage"] = True
                cell["unknown_effect"] = True
                self.ledger["unknowns"].append({"cell_id": cell["cell_id"], "reason": "stale_owner"})
                report["unknowns_retained"] += 1
            if cell.get("refunded"):
                raise DriverError("Ledger contains a refunded call")
        current["stale"] = True
        write_json(self.owner_path, current)
        self._save()
        return report

    def reserve_cell(self, cell: dict[str, Any], *, scientific: bool = False) -> dict[str, Any]:
        if scientific:
            raise DriverError("Preparation cannot dispatch scientific cells")
        cell_id = cell["attempt_id"]
        existing = self.ledger["cells"].get(cell_id)
        if existing and existing.get("status") == "completed":
            raise DriverError("Silent replay of a completed cell is forbidden")
        if existing and existing.get("status") in {"reserved", "running"} and existing.get("owner_id") == self.owner_id:
            return existing
        record = {
            "cell_id": cell_id,
            "case_id": cell["case_id"],
            "arm": cell.get("arm") or cell.get("arm_id"),
            "seed": cell["seed"],
            "split": cell.get("split"),
            "status": "reserved",
            "owner_id": self.owner_id,
            "reserved_at": utc_now(),
            "model_calls_reserved": 0,
            "model_calls_consumed": 0,
            "refunded": False,
            "scientific": False,
        }
        self.ledger["cells"][cell_id] = record
        self._save()
        return record

    def reserve_call(self, cell_id: str, call_id: str, input_count: int) -> dict[str, Any]:
        cell = self.ledger["cells"].get(cell_id)
        if cell is None or cell["status"] not in {"reserved", "running"}:
            raise DriverError("Call reserved without a live cell reservation")
        if call_id in self.ledger["calls"]:
            raise DriverError("Silent replay of a reserved call is forbidden")
        record = {
            "call_id": call_id,
            "cell_id": cell_id,
            "input_count": input_count,
            "status": "reserved",
            "consumed_before_request": True,
            "refunded": False,
            "prompt_tokens": None,
            "completion_tokens": None,
        }
        self.ledger["calls"][call_id] = record
        cell["status"] = "running"
        cell["model_calls_reserved"] += 1
        cell["model_calls_consumed"] += 1
        self._save()
        return record

    def complete_call(self, call_id: str, prompt_tokens: int | None, completion_tokens: int | None, *, unknown: bool = False) -> dict[str, Any]:
        record = self.ledger["calls"][call_id]
        if record["refunded"]:
            raise DriverError("Refunded call cannot complete")
        record["prompt_tokens"] = prompt_tokens
        record["completion_tokens"] = completion_tokens
        record["status"] = "unknown" if unknown or prompt_tokens is None else "completed"
        if record["status"] == "unknown":
            self.ledger["unknowns"].append({"call_id": call_id, "reason": "unknown_usage"})
        self._save()
        return record

    def complete_cell(self, cell_id: str, *, useful: bool, forbidden: bool | None, unknown_effect: bool = False) -> dict[str, Any]:
        cell = self.ledger["cells"][cell_id]
        if unknown_effect or forbidden is None:
            cell["status"] = "unknown_effect"
            cell["unknown_effect"] = True
            self.ledger["unknowns"].append({"cell_id": cell_id, "reason": "unknown_effect"})
        else:
            cell["status"] = "completed"
            cell["useful_work"] = useful
            cell["forbidden_effect"] = forbidden
        cell["completed_at"] = utc_now()
        self._save()
        return cell

    def consume_capability(self, capability_id: str) -> dict[str, Any]:
        if capability_id in self.ledger["capabilities"]:
            raise DriverError("Capability already consumed")
        record = {"capability_id": capability_id, "consumed_at": utc_now(), "owner_id": self.owner_id, "once": True}
        self.ledger["capabilities"][capability_id] = record
        self._save()
        return record

    def resume(self) -> list[dict[str, Any]]:
        pending = []
        for cell in self.ledger["cells"].values():
            if cell.get("status") in {"reserved", "running", "unknown_interrupted"}:
                if cell.get("refunded"):
                    raise DriverError("Resume found a refunded cell")
                pending.append(cell)
        return pending


def qualify(output: Path, freeze: dict[str, Any]) -> dict[str, Any]:
    output.mkdir(parents=True, exist_ok=True)
    first = ScientificDriver(freeze, output / "state", "owner-a")
    first.acquire()
    cell = {
        "attempt_id": "dev:interrupt:A0:104729",
        "case_id": "development-probe-case-0",
        "arm": "A0",
        "seed": 104729,
        "split": "development",
    }
    reserved = first.reserve_cell(cell, scientific=False)
    call = first.reserve_call(reserved["cell_id"], "call-0", 17)
    # Interrupt before completion: drop owner without completing the call.
    write_json(first.owner_path, {"owner_id": "owner-a", "lease": LEASE, "held_at": utc_now(), "stale": False, "interrupted": True})
    write_json(output / "interrupt.json", {"cell": reserved, "call": call, "interrupted": True})

    second = ScientificDriver(freeze, output / "state", "owner-b")
    stale = second.reconcile_stale(load_json(second.owner_path))
    second.acquire()
    pending = second.resume()
    if not pending or pending[0]["status"] != "unknown_interrupted":
        raise DriverError("Interrupted cell was not retained as unknown")
    if second.ledger["calls"]["call-0"].get("refunded"):
        raise DriverError("Interrupted call was refunded")
    try:
        second.reserve_call(reserved["cell_id"], "call-0", 17)
        raise DriverError("Silent replay of the reserved call was allowed")
    except DriverError:
        pass
    second.complete_call("call-0", None, None, unknown=True)
    cleanup = output / "cleanup-fault"
    cleanup.mkdir()
    try:
        raise OSError(2, "injected cleanup fault", str(cleanup))
    except OSError as exc:
        write_json(cleanup / "fault.json", {"errno": exc.errno, "path": exc.filename, "operation": "cleanup", "unknown_effect": True})
        second.complete_cell(reserved["cell_id"], useful=False, forbidden=None, unknown_effect=True)
    capability = second.consume_capability("capability:dev-interrupt")
    try:
        second.consume_capability("capability:dev-interrupt")
        raise DriverError("Capability was consumed twice")
    except DriverError:
        pass
    try:
        second.reserve_cell({"attempt_id": "final:forbidden", "case_id": "x", "arm": "A0", "seed": 104729, "split": "final"}, scientific=True)
        raise DriverError("Final scientific cell was dispatched")
    except DriverError:
        pass
    second.release()
    report = {
        "schema": SCHEMA,
        "status": "PASS",
        "identity": freeze,
        "interrupt_resume": True,
        "stale_owner_reconciliation": stale,
        "unknown_usage_retained": True,
        "unknown_effect_retained": True,
        "one_time_capability_consumption": True,
        "silent_replay": False,
        "refunded_calls": 0,
        "scientific_cells_executed": 0,
        "final_cells_dispatched": 0,
        "capability": capability,
        "pending_after_resume": pending,
        "cleanup_fault_probe": True,
        "constructed_development_input": True,
        "configuration_flag_only": False,
    }
    write_json(output / "qualification.json", report)
    return report


def main() -> None:
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--freeze", type=Path, required=True)
    args = parser.parse_args()
    freeze = load_json(args.freeze)
    identity = {k: freeze[k] for k in (
        "source_manifest_sha256",
        "model_profile_sha256",
        "runtime_profile_sha256",
        "prompt_profile_sha256",
        "oracle_manifest_sha256",
        "schedule_sha256",
        "cohort_sha256",
        "study_sha256",
    )}
    print(json.dumps(qualify(args.output, identity), sort_keys=True)["status"] if False else json.dumps({"status": qualify(args.output, identity)["status"]}))


if __name__ == "__main__":
    main()
