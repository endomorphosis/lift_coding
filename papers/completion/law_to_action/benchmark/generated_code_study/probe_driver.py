#!/usr/bin/env python3
"""Actual interruption/resume and cleanup probes under constructed development input."""
from __future__ import annotations

import json
import os
import tempfile
from datetime import datetime, timezone
from pathlib import Path

from driver import DriverError, DurableDriver, write_replace

HERE = Path(__file__).resolve().parent


def canonical(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False)


def sha_text(value):
    import hashlib
    return hashlib.sha256(value.encode()).hexdigest()


def load_freeze():
    return json.loads((HERE / "prospective_study.json").read_text())


def pick_identity(freeze, split):
    for row in freeze["schedule"]:
        if row["split"] == split:
            return row["identity"]
    raise RuntimeError("No identity for split " + split)


def run_probes(directory, freeze):
    checks = []
    driver = DurableDriver(directory, freeze)
    owner = driver.acquire()
    checks.append({"name": "exclusive_owner_acquired", "pass": owner["pid"] == os.getpid()})

    development = pick_identity(freeze, "development")
    reserved = driver.reserve(development, constructed=True)
    checks.append({"name": "pre_dispatch_reservation", "pass": reserved["consumed"] is False})

    try:
        driver.reserve(development, constructed=True)
        checks.append({"name": "duplicate_reservation_rejected", "pass": False})
    except DriverError as exc:
        checks.append({"name": "duplicate_reservation_rejected",
                       "pass": "already reserved" in str(exc).lower(),
                       "error": str(exc)})

    resume = driver.resume_state()
    checks.append({"name": "interrupt_before_consume_keeps_reservation",
                   "pass": resume["pending_reserved"] == [development] and resume["consumed"] == 0})

    consumed = driver.consume(development, {"constructed": True, "useful_work": False})
    checks.append({"name": "one_time_consume", "pass": consumed["scientific_cell"] is False})
    try:
        driver.consume(development, {"constructed": True})
        checks.append({"name": "silent_replay_rejected", "pass": False})
    except DriverError as exc:
        checks.append({"name": "silent_replay_rejected", "pass": "already" in str(exc).lower(), "error": str(exc)})

    try:
        driver.dispatch_scientific(pick_identity(freeze, "development"))
        checks.append({"name": "scientific_dispatch_refused", "pass": False})
    except DriverError as exc:
        checks.append({"name": "scientific_dispatch_refused", "pass": "refused" in str(exc).lower(), "error": str(exc)})

    try:
        driver.reserve(pick_identity(freeze, "final"), constructed=False)
        checks.append({"name": "final_seal_holds_without_constructed_flag", "pass": False})
    except DriverError as exc:
        checks.append({"name": "final_seal_holds_without_constructed_flag", "pass": True, "error": str(exc)})

    other = DurableDriver(directory, freeze)
    # Simulate a live exclusive owner: the current pid still owns the lock.
    try:
        other.acquire(owner_id="other-owner")
        # Same process is alive, so a distinct owner_id must fail while heartbeat is fresh.
        checks.append({"name": "second_live_owner_rejected", "pass": False})
    except DriverError as exc:
        checks.append({"name": "second_live_owner_rejected", "pass": "alive" in str(exc).lower(), "error": str(exc)})

    stale = json.loads((Path(directory) / "owner.json").read_text())
    stale.update({"pid": 1, "owner_id": "dead-owner", "heartbeat_unix": 0})
    write_replace(Path(directory) / "owner.json", stale)
    reconciled = DurableDriver(directory, freeze).acquire(owner_id="replacement-owner")
    checks.append({"name": "stale_owner_reconciled",
                   "pass": reconciled["owner_id"] == "replacement-owner" and (Path(directory) / "stale_owner_reconciled.json").exists()})
    failed = [item for item in checks if not item["pass"]]
    return {
        "schema": "la-generated-code-driver-probes/v1",
        "status": "PASS" if not failed else "FAIL",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "constructed_development": True,
        "model_calls": 0,
        "scientific_cells_executed": 0,
        "checks": checks,
        "failed": failed,
    }


def main():
    freeze = load_freeze()
    out = HERE / "qualification/driver_interruption_resume.json"
    with tempfile.TemporaryDirectory(prefix="la032-driver-probe-") as tmp:
        report = run_probes(tmp, freeze)
    out.parent.mkdir(parents=True, exist_ok=True)
    if out.exists():
        out.unlink()
    out.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n")
    print(json.dumps({"status": report["status"], "failed": len(report["failed"]),
                      "path": str(out), "sha256": sha_text(out.read_text())}, indent=2))
    if report["status"] != "PASS":
        raise SystemExit(1)


if __name__ == "__main__":
    main()
