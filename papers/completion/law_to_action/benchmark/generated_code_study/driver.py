#!/usr/bin/env python3
"""Durable scientific driver: exclusive ownership, reservation, resume. No model calls.

Scientific dispatch is refused until LA-032 readiness exists. Constructed
development probes may reserve and consume fixture identities only.
"""
from __future__ import annotations

import json
import os
import time
from datetime import datetime, timezone
from pathlib import Path


class DriverError(RuntimeError):
    pass


def canonical(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False)


def utc_now():
    return datetime.now(timezone.utc).isoformat()


def write_excl(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(fd, "w") as handle:
        handle.write(canonical(value) + "\n")
        handle.flush()
        os.fsync(handle.fileno())


def write_replace(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    fd = os.open(tmp, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    with os.fdopen(fd, "w") as handle:
        handle.write(canonical(value) + "\n")
        handle.flush()
        os.fsync(handle.fileno())
    os.replace(tmp, path)


def read_json(path):
    return json.loads(Path(path).read_text())


def pid_alive(pid):
    try:
        os.kill(int(pid), 0)
        return True
    except (OSError, TypeError, ValueError):
        return False


class DurableDriver:
    def __init__(self, root, freeze):
        self.root = Path(root)
        self.freeze = freeze
        self.owner_path = self.root / "owner.json"
        self.reserve_dir = self.root / "reservations"
        self.consume_dir = self.root / "consumed"
        self.reserve_dir.mkdir(parents=True, exist_ok=True)
        self.consume_dir.mkdir(parents=True, exist_ok=True)
        if freeze.get("scientific_cells_executed", 0) != 0:
            raise DriverError("Freeze claims scientific cells executed")
        self.identities = {row["identity"]: row for row in freeze["schedule"]}
        if len(self.identities) != 900:
            raise DriverError("Freeze does not contain 900 identities")

    def _owner(self):
        if not self.owner_path.exists():
            return None
        return read_json(self.owner_path)

    def acquire(self, *, owner_id=None, stale_seconds=30):
        owner_id = owner_id or ("pid:" + str(os.getpid()))
        current = self._owner()
        if current:
            alive = pid_alive(current.get("pid"))
            age = time.time() - float(current.get("heartbeat_unix") or 0)
            if current.get("owner_id") != owner_id and alive and age <= stale_seconds:
                raise DriverError("Exclusive owner is alive: " + current["owner_id"])
            if current.get("owner_id") != owner_id and (not alive or age > stale_seconds):
                write_replace(self.root / "stale_owner_reconciled.json", {
                    "previous": current,
                    "reconciled_at": utc_now(),
                    "reason": "stale_or_dead_owner",
                })
        record = {
            "schema": "la-generated-code-driver-owner/v1",
            "owner_id": owner_id,
            "pid": os.getpid(),
            "acquired_at": utc_now(),
            "heartbeat_at": utc_now(),
            "heartbeat_unix": time.time(),
            "scientific_dispatch_allowed": False,
        }
        if current and current.get("owner_id") == owner_id:
            record["acquired_at"] = current.get("acquired_at") or record["acquired_at"]
            write_replace(self.owner_path, record)
        elif not self.owner_path.exists():
            write_excl(self.owner_path, record)
        else:
            write_replace(self.owner_path, record)
        return record

    def heartbeat(self):
        current = self._owner()
        if not current or current.get("pid") != os.getpid():
            raise DriverError("Heartbeat requires the live exclusive owner")
        current["heartbeat_at"] = utc_now()
        current["heartbeat_unix"] = time.time()
        write_replace(self.owner_path, current)
        return current

    def _safe_name(self, identity):
        if identity not in self.identities:
            raise DriverError("Unknown identity: " + identity)
        return identity.replace("/", "__")

    def reserve(self, identity, *, constructed=False):
        self.heartbeat()
        row = self.identities[identity]
        if row["split"] == "final" and not constructed:
            raise DriverError("Final identities remain sealed")
        if not constructed:
            raise DriverError("Scientific dispatch is not allowed by this driver")
        path = self.reserve_dir / (self._safe_name(identity) + ".json")
        consumed = self.consume_dir / (self._safe_name(identity) + ".json")
        if consumed.exists():
            raise DriverError("Identity already consumed; refusing silent replay: " + identity)
        record = {
            "schema": "la-generated-code-reservation/v1",
            "identity": identity,
            "reserved_at": utc_now(),
            "owner_pid": os.getpid(),
            "constructed": True,
            "consumed": False,
        }
        try:
            write_excl(path, record)
        except FileExistsError as exc:
            raise DriverError("Identity already reserved; refusing silent replay: " + identity) from exc
        return record

    def consume(self, identity, result):
        self.heartbeat()
        reserved = self.reserve_dir / (self._safe_name(identity) + ".json")
        consumed = self.consume_dir / (self._safe_name(identity) + ".json")
        if not reserved.exists():
            raise DriverError("Consume without reservation: " + identity)
        if consumed.exists():
            raise DriverError("One-time consume already used: " + identity)
        reservation = read_json(reserved)
        if reservation.get("consumed") is True:
            raise DriverError("Reservation already consumed: " + identity)
        record = {
            "schema": "la-generated-code-consumption/v1",
            "identity": identity,
            "consumed_at": utc_now(),
            "reservation": reservation,
            "result": result,
            "scientific_cell": False,
        }
        try:
            write_excl(consumed, record)
        except FileExistsError as exc:
            raise DriverError("One-time consume already used: " + identity) from exc
        reservation["consumed"] = True
        write_replace(reserved, reservation)
        return record

    def resume_state(self):
        reserved = []
        consumed = []
        for path in sorted(self.reserve_dir.glob("*.json")):
            reserved.append(read_json(path))
        for path in sorted(self.consume_dir.glob("*.json")):
            consumed.append(read_json(path))
        pending = [row["identity"] for row in reserved if row.get("consumed") is not True]
        return {
            "reserved": len(reserved),
            "consumed": len(consumed),
            "pending_reserved": pending,
            "scientific_cells_executed": 0,
        }

    def dispatch_scientific(self, identity):
        raise DriverError("Scientific dispatch refused: LA-032 readiness is incomplete")
