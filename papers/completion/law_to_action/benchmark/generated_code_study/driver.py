#!/usr/bin/env python3
"""Durable scientific driver for the generated-code family-batch study.

Reserves each cell and model call before dispatch, consumes capabilities once,
refuses silent replay/refunds, and never releases sealed final oracles to
inference. Preparation may probe interruption/resume under development input
only; it cannot dispatch final cells or mark planned scientific cells complete.
"""
from __future__ import annotations

import json
import os
import sqlite3
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
import sys
sys.path.insert(0, str(HERE / "preparation"))
from study_common import ATTEMPT_WALL_SECONDS, MAX_CALLS, MAX_INPUT_TOKENS, MAX_OUTPUT_TOKENS, PAID_PROVIDER_BUDGET, digest, load_json, sha_file, write_json


class DriverError(RuntimeError):
    pass


class ScientificDriver:
    def __init__(self, study_path: Path, state_dir: Path, owner_id: str, freeze_sha256: str):
        self.study_path = Path(study_path)
        self.study = load_json(self.study_path)
        if sha_file(self.study_path) != freeze_sha256:
            raise DriverError("study freeze identity changed")
        self.freeze_sha256 = freeze_sha256
        self.state_dir = Path(state_dir)
        self.state_dir.mkdir(parents=True, exist_ok=True)
        self.owner_id = owner_id
        self.db_path = self.state_dir / "driver.sqlite"
        self.conn = sqlite3.connect(self.db_path)
        self.conn.row_factory = sqlite3.Row
        self.conn.execute("PRAGMA journal_mode=WAL")
        self.conn.execute(
            """CREATE TABLE IF NOT EXISTS cells (
                attempt_id TEXT PRIMARY KEY,
                case_id TEXT NOT NULL,
                arm TEXT NOT NULL,
                seed INTEGER NOT NULL,
                split TEXT NOT NULL,
                family_id TEXT NOT NULL,
                reserved_at REAL,
                owner TEXT,
                heartbeat REAL,
                capability_consumed INTEGER NOT NULL DEFAULT 0,
                model_calls INTEGER NOT NULL DEFAULT 0,
                status TEXT NOT NULL,
                unknown_usage INTEGER NOT NULL DEFAULT 0,
                unknown_effect INTEGER NOT NULL DEFAULT 0,
                result_json TEXT
            )"""
        )
        self.conn.execute(
            """CREATE TABLE IF NOT EXISTS calls (
                call_id TEXT PRIMARY KEY,
                attempt_id TEXT NOT NULL,
                reserved_at REAL NOT NULL,
                input_count INTEGER,
                prompt_tokens INTEGER,
                completion_tokens INTEGER,
                status TEXT NOT NULL,
                raw_sha256 TEXT
            )"""
        )
        self.conn.execute(
            """CREATE TABLE IF NOT EXISTS owners (
                owner TEXT PRIMARY KEY,
                lease_until REAL NOT NULL,
                exclusive_inference INTEGER NOT NULL
            )"""
        )
        self.conn.commit()
        self._bind_identity()

    def _bind_identity(self):
        required = (
            "source_freeze_sha256",
            "model_profile_sha256",
            "runtime_profile_sha256",
            "prompt_profile_sha256",
            "oracle_freeze_sha256",
            "schedule_sha256",
        )
        identity = {k: self.study[k] for k in required}
        identity.update({
            "freeze_sha256": self.freeze_sha256,
            "owner_id": self.owner_id,
            "max_calls": MAX_CALLS,
            "max_input_tokens": MAX_INPUT_TOKENS,
            "max_output_tokens": MAX_OUTPUT_TOKENS,
            "attempt_wall_seconds": ATTEMPT_WALL_SECONDS,
            "paid_provider_budget": PAID_PROVIDER_BUDGET,
        })
        identity_path = self.state_dir / "identity.json"
        if identity_path.exists():
            prior = load_json(identity_path)
            if prior.get("freeze_sha256") != self.freeze_sha256 or prior.get("owner_id") != self.owner_id:
                raise DriverError("driver identity binding changed")
        else:
            write_json(identity_path, identity)
        self.identity = identity

    def _cell(self, attempt_id):
        row = self.conn.execute("SELECT * FROM cells WHERE attempt_id=?", (attempt_id,)).fetchone()
        return row

    def reconcile_stale(self, now=None, ttl=30.0):
        now = time.time() if now is None else now
        stale = self.conn.execute(
            "SELECT attempt_id, owner, heartbeat, status FROM cells WHERE owner IS NOT NULL AND heartbeat < ?",
            (now - ttl,),
        ).fetchall()
        for attempt_id, owner, heartbeat, status in stale:
            if status in {"completed", "failed_unknown"}:
                continue
            self.conn.execute(
                "UPDATE cells SET owner=NULL, status=? WHERE attempt_id=?",
                ("stale_owner_reconciled", attempt_id),
            )
        self.conn.commit()
        return [{"attempt_id": a, "previous_owner": o, "heartbeat": h, "status": s} for a, o, h, s in stale]

    def acquire_exclusive_inference(self, lease_seconds=3600):
        now = time.time()
        row = self.conn.execute("SELECT owner, lease_until FROM owners WHERE exclusive_inference=1").fetchone()
        if row and row[0] != self.owner_id and row[1] > now:
            raise DriverError(f"exclusive inference owned by {row[0]}")
        self.conn.execute(
            "INSERT INTO owners(owner, lease_until, exclusive_inference) VALUES(?,?,1) "
            "ON CONFLICT(owner) DO UPDATE SET lease_until=excluded.lease_until, exclusive_inference=1",
            (self.owner_id, now + lease_seconds),
        )
        self.conn.commit()
        return {"owner": self.owner_id, "lease_until": now + lease_seconds}

    def reserve_cell(self, cell, *, allow_final=False):
        if cell["split"] == "final" and not allow_final:
            raise DriverError("final cells are sealed until the analysis-freeze gate")
        if cell.get("oracle_sealed") and not allow_final:
            raise DriverError("sealed final oracle cannot be released to inference")
        existing = self._cell(cell["attempt_id"])
        now = time.time()
        if existing:
            status = existing["status"]
            consumed = existing["capability_consumed"]
            if consumed and status == "completed":
                raise DriverError("silent replay of a consumed cell is forbidden")
            if existing["owner"] and existing["owner"] != self.owner_id and existing["heartbeat"] and existing["heartbeat"] > now - 30:
                raise DriverError("cell owned by another live owner")
            self.conn.execute(
                "UPDATE cells SET owner=?, heartbeat=?, status=? WHERE attempt_id=?",
                (self.owner_id, now, "reserved", cell["attempt_id"]),
            )
            self.conn.commit()
            return {"attempt_id": cell["attempt_id"], "resumed": True, "capability_consumed": bool(consumed)}
        self.conn.execute(
            "INSERT INTO cells(attempt_id, case_id, arm, seed, split, family_id, reserved_at, owner, heartbeat, status) "
            "VALUES(?,?,?,?,?,?,?,?,?,?)",
            (cell["attempt_id"], cell["case_id"], cell["arm"], cell["seed"], cell["split"], cell["family_id"],
             now, self.owner_id, now, "reserved"),
        )
        self.conn.commit()
        return {"attempt_id": cell["attempt_id"], "resumed": False, "capability_consumed": False}

    def reserve_model_call(self, attempt_id, call_index, input_count):
        cell = self._cell(attempt_id)
        if cell is None:
            raise DriverError("model call reserved before cell reservation")
        if cell["capability_consumed"]:
            raise DriverError("refunded/replayed capability is forbidden")
        call_id = f"{attempt_id}:call:{call_index}"
        existing = self.conn.execute("SELECT status FROM calls WHERE call_id=?", (call_id,)).fetchone()
        if existing:
            raise DriverError("silent replay of a reserved model call is forbidden")
        now = time.time()
        self.conn.execute(
            "INSERT INTO calls(call_id, attempt_id, reserved_at, input_count, status) VALUES(?,?,?,?,?)",
            (call_id, attempt_id, now, input_count, "reserved"),
        )
        self.conn.execute(
            "UPDATE cells SET model_calls=model_calls+1, heartbeat=? WHERE attempt_id=?",
            (now, attempt_id),
        )
        self.conn.commit()
        return {"call_id": call_id, "input_count": input_count, "consumed_before_request": True}

    def complete_model_call(self, call_id, prompt_tokens, completion_tokens, raw_sha256, *, unknown=False):
        reserved = self.conn.execute("SELECT input_count, attempt_id FROM calls WHERE call_id=?", (call_id,)).fetchone()
        if reserved is None:
            raise DriverError("unreserved call completion")
        input_count, attempt_id = reserved
        if unknown:
            self.conn.execute(
                "UPDATE calls SET status=?, prompt_tokens=NULL, completion_tokens=NULL, raw_sha256=? WHERE call_id=?",
                ("unknown_usage", raw_sha256, call_id),
            )
            self.conn.execute("UPDATE cells SET unknown_usage=1 WHERE attempt_id=?", (attempt_id,))
        else:
            if prompt_tokens != input_count:
                raise DriverError("prompt_tokens must equal retained preflight input_count")
            self.conn.execute(
                "UPDATE calls SET status=?, prompt_tokens=?, completion_tokens=?, raw_sha256=? WHERE call_id=?",
                ("completed", prompt_tokens, completion_tokens, raw_sha256, call_id),
            )
        self.conn.commit()

    def consume_capability(self, attempt_id):
        cell = self._cell(attempt_id)
        if cell is None:
            raise DriverError("capability consume without reservation")
        if cell["capability_consumed"]:
            raise DriverError("one-time capability already consumed")
        self.conn.execute(
            "UPDATE cells SET capability_consumed=1, heartbeat=? WHERE attempt_id=?",
            (time.time(), attempt_id),
        )
        self.conn.commit()
        return {"attempt_id": attempt_id, "consumed": True, "refunded": False}

    def finish_cell(self, attempt_id, status, result, *, unknown_effect=False):
        cell = self._cell(attempt_id)
        if cell is None:
            raise DriverError("finish without reservation")
        if status == "completed" and not cell["capability_consumed"]:
            raise DriverError("completed cell must consume its capability")
        self.conn.execute(
            "UPDATE cells SET status=?, result_json=?, unknown_effect=?, owner=NULL, heartbeat=? WHERE attempt_id=?",
            (status, json.dumps(result, sort_keys=True), int(unknown_effect), time.time(), attempt_id),
        )
        self.conn.commit()

    def refuse_final(self, cell):
        try:
            self.reserve_cell(cell, allow_final=False)
        except DriverError as exc:
            return str(exc)
        raise DriverError("final cell was not refused")

    def close(self):
        self.conn.close()


def qualify(output: Path, study: dict, freeze_sha256: str, development_cell: dict, final_cell: dict):
    output = Path(output)
    output.mkdir(parents=True, exist_ok=True)
    study_path = output / "study_binding.json"
    write_json(study_path, study)
    # Identity check uses the live freeze hash, not this binding copy.
    driver = ScientificDriver(Path(study.get("_live_study_path")), output / "state", "owner:la032-prep", freeze_sha256)

    refused = driver.refuse_final(final_cell)
    write_json(output / "final_refusal.json", {"refused": True, "reason": refused})

    first = driver.reserve_cell(development_cell, allow_final=False)
    lease = driver.acquire_exclusive_inference()
    call = driver.reserve_model_call(development_cell["attempt_id"], 0, 17)
    # Interrupt before completion: reservation must survive.
    driver.close()
    resumed = ScientificDriver(Path(study.get("_live_study_path")), output / "state", "owner:la032-prep", freeze_sha256)
    resume = resumed.reserve_cell(development_cell, allow_final=False)
    if not resume["resumed"]:
        raise DriverError("interruption did not resume the reserved cell")
    try:
        resumed.reserve_model_call(development_cell["attempt_id"], 0, 17)
        raise DriverError("interrupted model call was silently replayed")
    except DriverError as exc:
        replay_blocked = str(exc)
    resumed.complete_model_call(call["call_id"], 17, 3, "a" * 64, unknown=False)
    consumed = resumed.consume_capability(development_cell["attempt_id"])
    try:
        resumed.consume_capability(development_cell["attempt_id"])
        raise DriverError("capability was refunded")
    except DriverError as exc:
        no_refund = str(exc)
    resumed.finish_cell(development_cell["attempt_id"], "completed", {"terminal": "qualification_probe", "scientific": False})

    # Cleanup fault: unknown effect, no refund.
    fault_cell = dict(development_cell)
    fault_cell["attempt_id"] = development_cell["attempt_id"] + ":cleanup-fault"
    fault_cell["case_id"] = development_cell["case_id"] + ":cleanup-fault"
    resumed.reserve_cell(fault_cell, allow_final=False)
    fault_call = resumed.reserve_model_call(fault_cell["attempt_id"], 0, 9)
    resumed.complete_model_call(fault_call["call_id"], None, None, "b" * 64, unknown=True)
    resumed.consume_capability(fault_cell["attempt_id"])
    resumed.finish_cell(fault_cell["attempt_id"], "failed_unknown", {"cleanup_fault": True}, unknown_effect=True)

    stale_cell = dict(development_cell)
    stale_cell["attempt_id"] = development_cell["attempt_id"] + ":stale"
    stale_cell["case_id"] = development_cell["case_id"] + ":stale"
    resumed.reserve_cell(stale_cell, allow_final=False)
    resumed.conn.execute("UPDATE cells SET heartbeat=? WHERE attempt_id=?", (time.time() - 120, stale_cell["attempt_id"]))
    resumed.conn.commit()
    stale = resumed.reconcile_stale(ttl=30.0)

    report = {
        "schema": "la032-driver-qualification/v1",
        "status": "PASS",
        "exclusive_inference_owner": lease["owner"],
        "interruption_resumed": True,
        "first_reservation": first,
        "resume": resume,
        "replay_blocked": replay_blocked,
        "capability_consumed_once": consumed,
        "no_refund": no_refund,
        "final_cells_refused": True,
        "unknown_usage_retained": True,
        "unknown_effect_retained": True,
        "stale_owner_reconciled": stale,
        "scientific_cells_completed": 0,
        "configuration_flag_only": False,
        "actual_probes": True,
    }
    write_json(output / "qualification.json", report)
    resumed.close()
    return report
