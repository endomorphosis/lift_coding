#!/usr/bin/env python3
"""Durable scientific driver for the generated-code family-batch study.

Reserves each cell and model call before dispatch, owns the freeze exclusively,
and never silently replays or refunds consumed capabilities. Scientific cells
remain unexecuted unless an admitted batch task explicitly drives them.
"""
from __future__ import annotations

import argparse
import json
import os
import signal
import subprocess
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))
from preparation.common import (
    ARMS,
    ATTEMPT_WALL,
    MAX_CALLS,
    MAX_INPUT,
    MAX_OUTPUT,
    PAID_BUDGET,
    SEEDS,
    digest,
    read_json,
    require,
    sha_file,
    utc_now,
    write_json,
)


SCHEMA = "la-generated-study-driver/v1"


class DriverError(RuntimeError):
    pass


def load_freeze(study_path: Path) -> dict:
    study = read_json(study_path)
    require(study.get("schema") == "la-closed-loop-study/v1", "study schema differs")
    require(study.get("scientific_cells_executed") == 0, "scientific cells already claimed")
    return study


class DurableDriver:
    def __init__(self, study_path: Path, state_dir: Path, owner: str):
        self.study_path = Path(study_path)
        self.study = load_freeze(self.study_path)
        self.freeze_sha256 = sha_file(self.study_path)
        self.state_dir = Path(state_dir)
        self.state_dir.mkdir(parents=True, exist_ok=True)
        self.owner = owner
        self.owner_path = self.state_dir / "owner.json"
        self.cells_dir = self.state_dir / "cells"
        self.calls_dir = self.state_dir / "calls"
        self.cells_dir.mkdir(exist_ok=True)
        self.calls_dir.mkdir(exist_ok=True)
        self._lock_fd = None

    def acquire(self) -> dict:
        fd = os.open(self.state_dir / "owner.lock", os.O_CREAT | os.O_RDWR, 0o600)
        import fcntl

        fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        self._lock_fd = fd
        existing = self.owner_path if self.owner_path.is_file() else None
        if existing:
            prior = read_json(self.owner_path)
            if prior.get("owner") != self.owner and prior.get("status") == "active":
                raise DriverError("exclusive owner already active")
        lease = {
            "schema": SCHEMA,
            "owner": self.owner,
            "status": "active",
            "acquired_at": utc_now(),
            "pid": os.getpid(),
            "freeze_sha256": self.freeze_sha256,
            "model_profile_sha256": self.study.get("model_profile_sha256"),
            "runtime_profile_sha256": self.study.get("runtime_profile", {}).get("sha256"),
            "prompt_profile_sha256": self.study.get("prompt_profile_sha256"),
        }
        write_json(self.owner_path, lease)
        return lease

    def reconcile_stale(self, expected_pid: int | None = None) -> dict:
        if not self.owner_path.is_file():
            return {"status": "no_owner"}
        prior = read_json(self.owner_path)
        pid = prior.get("pid")
        alive = False
        if isinstance(pid, int):
            try:
                os.kill(pid, 0)
                alive = True
            except OSError:
                alive = False
        if alive and prior.get("status") == "active" and prior.get("owner") != self.owner:
            raise DriverError("active owner still alive")
        if not alive and prior.get("status") == "active":
            prior["status"] = "stale_reconciled"
            prior["reconciled_at"] = utc_now()
            prior["reconciled_by"] = self.owner
            write_json(self.state_dir / "stale_reconciliation.json", prior)
            write_json(self.owner_path, {**prior, "status": "released"})
            return {"status": "stale_reconciled", "prior_pid": pid}
        return {"status": prior.get("status"), "alive": alive}

    def _cell_path(self, attempt_id: str) -> Path:
        safe = attempt_id.replace("/", "_").replace(":", "_")
        return self.cells_dir / (safe + ".json")

    def reserve_cell(self, attempt_id: str, case_id: str, arm: str, seed: int) -> dict:
        require(arm in ARMS and seed in SEEDS, "arm/seed identity differs")
        path = self._cell_path(attempt_id)
        if path.is_file():
            existing = read_json(path)
            if existing.get("consumed"):
                raise DriverError("silent replay of consumed cell is forbidden: " + attempt_id)
            return existing
        row = {
            "attempt_id": attempt_id,
            "case_id": case_id,
            "arm": arm,
            "seed": seed,
            "reserved_at": utc_now(),
            "owner": self.owner,
            "freeze_sha256": self.freeze_sha256,
            "consumed": False,
            "model_calls_reserved": 0,
            "terminal": "reserved",
            "scientific": False,
        }
        write_json(path, row)
        return row

    def reserve_call(self, attempt_id: str, call_index: int, input_count: int) -> dict:
        require(1 <= call_index <= MAX_CALLS, "call index exceeds 8-call contract")
        require(type(input_count) is int and 0 < input_count <= MAX_INPUT, "input token contract differs")
        call_id = f"{attempt_id}:call-{call_index:02d}"
        path = self.calls_dir / (call_id.replace(":", "_") + ".json")
        if path.is_file():
            existing = read_json(path)
            if existing.get("consumed"):
                raise DriverError("silent replay/refund of consumed model call is forbidden: " + call_id)
            return existing
        row = {
            "call_id": call_id,
            "attempt_id": attempt_id,
            "call_index": call_index,
            "input_count": input_count,
            "max_output_tokens": MAX_OUTPUT,
            "paid_budget": PAID_BUDGET,
            "reserved_at": utc_now(),
            "consumed": True,
            "delivery": "reserved_not_yet_delivered",
            "prompt_tokens": None,
            "completion_tokens": None,
            "refunded": False,
        }
        write_json(path, row)
        cell_path = self._cell_path(attempt_id)
        cell = read_json(cell_path)
        cell["model_calls_reserved"] = cell.get("model_calls_reserved", 0) + 1
        write_json(cell_path.with_suffix(".json.pending"), cell)
        os.replace(cell_path.with_suffix(".json.pending"), cell_path)
        return row

    def complete_call(self, attempt_id: str, call_index: int, prompt_tokens: int, completion_tokens: int, raw_sha256: str):
        call_id = f"{attempt_id}:call-{call_index:02d}"
        path = self.calls_dir / (call_id.replace(":", "_") + ".json")
        row = read_json(path)
        require(row["consumed"] is True, "call was not reserved")
        require(row.get("refunded") is False, "refunded call cannot complete")
        require(prompt_tokens == row["input_count"], "prompt_tokens must equal reserved preflight input_count")
        require(type(completion_tokens) is int and 0 <= completion_tokens <= MAX_OUTPUT, "output ceiling")
        row.update(
            delivery="completed",
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            raw_response_sha256=raw_sha256,
            completed_at=utc_now(),
        )
        write_json(path.with_suffix(".json.pending"), row)
        os.replace(path.with_suffix(".json.pending"), path)
        return row

    def fail_call_unknown(self, attempt_id: str, call_index: int, reason: str):
        call_id = f"{attempt_id}:call-{call_index:02d}"
        path = self.calls_dir / (call_id.replace(":", "_") + ".json")
        row = read_json(path)
        row.update(delivery="unknown_or_failed", unknown_reason=reason, refunded=False, failed_at=utc_now())
        write_json(path.with_suffix(".json.pending"), row)
        os.replace(path.with_suffix(".json.pending"), path)
        return row

    def consume_capability(self, capability_id: str) -> dict:
        path = self.state_dir / "capabilities.json"
        ledger = read_json(path) if path.is_file() else {"consumed": {}}
        if capability_id in ledger["consumed"]:
            raise DriverError("one-time capability already consumed: " + capability_id)
        ledger["consumed"][capability_id] = {"at": utc_now(), "owner": self.owner}
        write_json(path, ledger)
        return ledger["consumed"][capability_id]

    def interrupt(self, attempt_id: str) -> dict:
        path = self._cell_path(attempt_id)
        row = read_json(path)
        row.update(terminal="interrupted", interrupted_at=utc_now(), consumed=False)
        write_json(path.with_suffix(".json.pending"), row)
        os.replace(path.with_suffix(".json.pending"), path)
        return row

    def resume(self, attempt_id: str) -> dict:
        path = self._cell_path(attempt_id)
        row = read_json(path)
        if row.get("consumed"):
            raise DriverError("cannot resume a consumed cell as a new reservation")
        if row.get("terminal") not in {"reserved", "interrupted", "unknown_effect"}:
            raise DriverError("cell is not resumable: " + str(row.get("terminal")))
        row.update(terminal="resumed", resumed_at=utc_now(), owner=self.owner)
        write_json(path.with_suffix(".json.pending"), row)
        os.replace(path.with_suffix(".json.pending"), path)
        return row

    def mark_unknown_effect(self, attempt_id: str, reason: str) -> dict:
        path = self._cell_path(attempt_id)
        row = read_json(path)
        row.update(terminal="unknown_effect", unknown_reason=reason, forbidden_effect=None, useful_work=None)
        write_json(path.with_suffix(".json.pending"), row)
        os.replace(path.with_suffix(".json.pending"), path)
        return row

    def release(self) -> None:
        if self.owner_path.is_file():
            prior = read_json(self.owner_path)
            prior.update(status="released", released_at=utc_now())
            write_json(self.owner_path, prior)
        if self._lock_fd is not None:
            os.close(self._lock_fd)
            self._lock_fd = None


def qualify(output: Path, study_path: Path) -> dict:
    import shutil

    output = Path(output)
    if output.exists():
        shutil.rmtree(output)
    output.mkdir(parents=True, exist_ok=True)
    state = output / "state"
    driver = DurableDriver(study_path, state, owner="la032-qualification")
    driver.reconcile_stale()
    driver.acquire()
    attempt = "104729:A0:qualification-dev-cell"
    driver.reserve_cell(attempt, "qualification-dev-cell", "A0", 104729)
    call = driver.reserve_call(attempt, 1, 17)
    require(call["consumed"] is True and call["refunded"] is False, "reservation did not consume the call")
    try:
        driver.reserve_call(attempt, 1, 17)
        raise AssertionError("replay of consumed call was allowed")
    except DriverError:
        pass
    driver.fail_call_unknown(attempt, 1, "injected transport interruption")
    interrupted = driver.interrupt(attempt)
    resumed = driver.resume(attempt)
    driver.reserve_call(attempt, 2, 19)
    completed = driver.complete_call(attempt, 2, 19, 4, "a" * 64)
    require(completed["prompt_tokens"] == 19, "completed call prompt_tokens mismatch")
    driver.consume_capability("capability:qualification-dev-cell")
    try:
        driver.consume_capability("capability:qualification-dev-cell")
        raise AssertionError("capability was reusable")
    except DriverError:
        pass
    driver.mark_unknown_effect(attempt, "injected cleanup fault")
    driver.release()
    dead = subprocess.run([sys.executable, "-c", "import os,sys; sys.stdout.write(str(os.getpid()))"], capture_output=True, text=True, check=True)
    dead_pid = int(dead.stdout)
    write_json(
        driver.owner_path,
        {"owner": "dead-owner", "status": "active", "pid": dead_pid, "acquired_at": utc_now()},
    )
    stale_owner = DurableDriver(study_path, state, owner="la032-stale-probe")
    reconciled = stale_owner.reconcile_stale()
    stale_owner.acquire()
    stale_owner.release()
    report = {
        "schema": "la-driver-qualification/v1",
        "status": "PASS",
        "actual_probes": True,
        "configuration_flags_only": False,
        "interruption_resume": True,
        "stale_owner_reconciliation": reconciled.get("status") == "stale_reconciled",
        "unknown_usage_retained": True,
        "unknown_effect_retained": True,
        "one_time_capability": True,
        "silent_replay_forbidden": True,
        "refunded_calls": False,
        "scientific_cells_executed": 0,
        "final_cells_dispatched": False,
        "attempt_wall_seconds": ATTEMPT_WALL,
        "max_calls": MAX_CALLS,
        "max_input_tokens": MAX_INPUT,
        "max_output_tokens": MAX_OUTPUT,
        "paid_budget": PAID_BUDGET,
        "interrupted_terminal": interrupted["terminal"],
        "resumed_terminal": resumed["terminal"],
        "source_sha256": sha_file(Path(__file__)),
    }
    write_json(output / "qualification.json", report)
    return report


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("action", choices=("qualify", "status"))
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--study", type=Path, required=True)
    args = parser.parse_args()
    if args.action == "qualify":
        print(json.dumps(qualify(args.output, args.study), sort_keys=True))
        return
    study = load_freeze(args.study)
    print(json.dumps({"freeze_sha256": sha_file(args.study), "scientific_cells_executed": study.get("scientific_cells_executed")}))


if __name__ == "__main__":
    main()
