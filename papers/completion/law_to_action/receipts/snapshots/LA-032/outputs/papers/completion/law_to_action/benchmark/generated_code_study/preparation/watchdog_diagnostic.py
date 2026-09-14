#!/usr/bin/env python3
"""Diagnostic watchdog that retains OSError operation/path/errno snapshots.

The historical LA-030 v2 receipt remains FAILED_RETAINED. This module does not
upgrade it or suppress OSError. Benign leaf disappearance is allowed only after
independent parent-identity, monotonic-counter and empty-state revalidation.
"""
from __future__ import annotations

import errno
import json
import os
import threading
import time
from pathlib import Path

from study_common import digest, write_json

HISTORICAL_V2_RESOURCES = Path(__file__).resolve().parents[1].parent / (
    "generated_code_development/development_qualification_v2/full_repair/iteration-01/cell/host/resources.json"
)
HISTORICAL_V2_RECONCILIATION = Path(__file__).resolve().parents[1].parent / (
    "generated_code_development/development_qualification_v2/reconciliation.json"
)


def _parse_events(text):
    return dict(line.split() for line in (text or "").splitlines() if line.strip())


def _cpu_seconds(text):
    fields = _parse_events(text)
    return int(fields.get("usage_usec", "0")) / 1_000_000


def snapshot_identity(path: Path, *, operation: str):
    path = Path(path)
    try:
        stat = path.stat()
        return {
            "path": str(path),
            "operation": operation,
            "exists": True,
            "inode": stat.st_ino,
            "mode": stat.st_mode,
            "observed_monotonic": time.monotonic(),
        }
    except OSError as exc:
        return {
            "path": str(path),
            "operation": operation,
            "exists": False,
            "inode": None,
            "oserror": format_oserror(exc, operation, path),
            "observed_monotonic": time.monotonic(),
        }


def format_oserror(exc: OSError, operation: str, path):
    return {
        "error_type": type(exc).__name__,
        "operation": operation,
        "path": None if path is None else str(path),
        "errno": exc.errno,
        "errno_name": errno.errorcode.get(exc.errno, "UNKNOWN"),
        "strerror": os.strerror(exc.errno) if exc.errno is not None else None,
        "filename": None if exc.filename is None else str(exc.filename),
        "filename2": None if getattr(exc, "filename2", None) is None else str(exc.filename2),
        "cause": repr(exc.__cause__) if exc.__cause__ is not None else None,
        "unproven_historical_receipt": True,
    }


def read_cgroup_file(path: Path, operation: str):
    path = Path(path)
    try:
        return path.read_text(), snapshot_identity(path, operation=operation)
    except OSError as exc:
        raise DiagnosticOSError(format_oserror(exc, operation, path)) from exc


class DiagnosticOSError(OSError):
    def __init__(self, record):
        super().__init__(record.get("errno") or errno.EIO, record.get("strerror") or "resource observation failed")
        self.record = record


class DiagnosticWatchdog:
    """Observe leaf/parent files without broadly swallowing OSError."""

    def __init__(self, start, parent: Path, leaf: Path | None, clock=time.monotonic, wall_seconds=120):
        self.start = start
        self.parent = Path(parent)
        self.leaf = Path(leaf) if leaf is not None else None
        self.clock = clock
        self.wall_seconds = wall_seconds
        self.parent_inode = None
        self.leaf_inode = None
        self.parent_samples = []
        self.leaf_samples = []
        self.error = None
        self.diagnostics = []
        self.stop = threading.Event()
        self.thread = threading.Thread(target=self.loop, daemon=True)

    def fail(self, reason, extra=None):
        if self.error is not None:
            return
        record = {
            "reason": reason,
            "at_monotonic": self.clock(),
            "parent_identity": snapshot_identity(self.parent, operation="fail.parent"),
            "leaf_identity": None if self.leaf is None else snapshot_identity(self.leaf, operation="fail.leaf"),
        }
        if extra:
            record.update(extra)
        self.error = record

    def sample_parent(self):
        cpu_text, cpu_id = read_cgroup_file(self.parent / "cpu.stat", "parent.read:cpu.stat")
        events_text, events_id = read_cgroup_file(self.parent / "cgroup.events", "parent.read:cgroup.events")
        pids_text, pids_id = read_cgroup_file(self.parent / "pids.current", "parent.read:pids.current")
        identity = snapshot_identity(self.parent, operation="parent.stat")
        reading = {
            "cpu.stat": cpu_text,
            "cgroup.events": events_text,
            "pids.current": pids_text.strip(),
            "cpu_usage_seconds": _cpu_seconds(cpu_text),
            "inode": identity.get("inode"),
            "identities": {"cpu.stat": cpu_id, "cgroup.events": events_id, "pids.current": pids_id, "parent": identity},
            "observed_monotonic": self.clock(),
        }
        if self.parent_inode not in (None, reading["inode"]):
            self.fail("parent_identity_changed", {"previous_inode": self.parent_inode, "current": reading})
            return reading
        if self.parent_samples and reading["cpu_usage_seconds"] < self.parent_samples[-1]["cpu_usage_seconds"]:
            self.fail("parent_counter_regressed", {"previous": self.parent_samples[-1], "current": reading})
            return reading
        self.parent_inode = reading["inode"]
        self.parent_samples.append(reading)
        return reading

    def sample_leaf(self):
        if self.leaf is None:
            return None
        if not self.leaf.exists():
            return self.handle_leaf_disappearance()
        cpu_text, cpu_id = read_cgroup_file(self.leaf / "cpu.stat", "leaf.read:cpu.stat")
        identity = snapshot_identity(self.leaf, operation="leaf.stat")
        if self.leaf_inode not in (None, identity.get("inode")):
            self.fail("leaf_identity_changed", {"previous_inode": self.leaf_inode, "current": identity})
        self.leaf_inode = identity.get("inode")
        reading = {
            "cpu.stat": cpu_text,
            "cpu_usage_seconds": _cpu_seconds(cpu_text),
            "inode": identity.get("inode"),
            "identities": {"cpu.stat": cpu_id, "leaf": identity},
            "observed_monotonic": self.clock(),
        }
        self.leaf_samples.append(reading)
        return reading

    def handle_leaf_disappearance(self):
        parent_now = snapshot_identity(self.parent, operation="leaf_gone.parent")
        parent_reading = None
        try:
            parent_reading = self.sample_parent()
        except DiagnosticOSError as exc:
            self.fail("parent_observation_OSError_during_leaf_disappearance", {"oserror": exc.record})
            return None
        events = _parse_events((parent_reading or {}).get("cgroup.events", ""))
        empty = (parent_reading or {}).get("pids.current") == "0" and events.get("populated") == "0"
        stable = parent_now.get("inode") == self.parent_inode and self.parent_inode is not None
        monotonic = True
        if len(self.parent_samples) >= 2:
            monotonic = self.parent_samples[-1]["cpu_usage_seconds"] >= self.parent_samples[-2]["cpu_usage_seconds"]
        record = {
            "kind": "benign_leaf_disappearance_candidate",
            "leaf_identity": snapshot_identity(self.leaf, operation="leaf_gone.leaf"),
            "parent_identity": parent_now,
            "parent_empty": empty,
            "parent_identity_stable": stable,
            "counters_monotonic": monotonic,
            "accepted": bool(empty and stable and monotonic and parent_reading is not None),
        }
        self.diagnostics.append(record)
        if not record["accepted"]:
            self.fail("leaf_disappeared_without_parent_revalidation", record)
        return record

    def check(self):
        if self.clock() - self.start >= self.wall_seconds:
            self.fail("whole_attempt_wall_budget")
            return
        try:
            if self.parent.exists():
                self.sample_parent()
            elif self.parent_inode is not None:
                self.fail("persistent_parent_disappeared")
            if self.leaf is not None:
                self.sample_leaf()
        except DiagnosticOSError as exc:
            self.fail("resource_observation_OSError", {
                "oserror": exc.record,
                "leaf_identity": None if self.leaf is None else snapshot_identity(self.leaf, operation="error.leaf"),
                "parent_identity": snapshot_identity(self.parent, operation="error.parent"),
                "historical_v2_errno_unproven": True,
            })
        except OSError as exc:
            # Retain the exact OSError. Do not convert it into a silent skip.
            self.fail("resource_observation_OSError", {
                "oserror": format_oserror(exc, "unclassified.read", getattr(exc, "filename", None)),
                "leaf_identity": None if self.leaf is None else snapshot_identity(self.leaf, operation="error.leaf"),
                "parent_identity": snapshot_identity(self.parent, operation="error.parent"),
                "historical_v2_errno_unproven": True,
            })

    def loop(self):
        while not self.stop.is_set() and self.error is None:
            self.check()
            self.stop.wait(0.02)

    def finish(self):
        self.stop.set()
        if self.thread.is_alive():
            self.thread.join(timeout=6)


def historical_v2_investigation():
    resources = json.loads(HISTORICAL_V2_RESOURCES.read_text())
    reconciliation = json.loads(HISTORICAL_V2_RECONCILIATION.read_text())
    decision = resources.get("decision") or {}
    return {
        "schema": "la032-watchdog-historical-investigation/v1",
        "historical_receipt_upgraded": False,
        "historical_status": reconciliation.get("status"),
        "historical_reason": decision.get("reason"),
        "historical_errno": None,
        "historical_path": None,
        "historical_operation": None,
        "historical_cause": None,
        "unproven_fields": ["errno", "path", "operation", "filename", "cause"],
        "whole_group_termination_proven": reconciliation.get("whole_group_termination_proven"),
        "exact_owned_cleanup_proven": reconciliation.get("exact_owned_cleanup_proven"),
        "effect_disposition_preserved": reconciliation.get("effect_disposition_preserved"),
        "resources_sha256": digest(resources),
        "reconciliation_sha256": digest(reconciliation),
        "interpretation": (
            "The retained v2 receipt records resource_observation_OSError during terminal "
            "leaf observation after child exit 0. It does not retain errno, path, operation "
            "or cause. This investigation does not upgrade that failed receipt."
        ),
    }


def _write_cgroup(root: Path, cpu_usec: int, pids: int, populated: int, *, files=True):
    root.mkdir(parents=True, exist_ok=True)
    if files:
        (root / "cpu.stat").write_text(f"usage_usec {cpu_usec}\nuser_usec {cpu_usec}\nsystem_usec 0\n")
        (root / "cgroup.events").write_text(f"populated {populated}\nfrozen 0\n")
        (root / "pids.current").write_text(f"{pids}\n")


def qualify(output: Path):
    output = Path(output)
    output.mkdir(parents=True, exist_ok=True)
    investigation = historical_v2_investigation()
    write_json(output / "historical_v2_investigation.json", investigation)
    if investigation["historical_status"] != "FAILED_RETAINED" or investigation["historical_receipt_upgraded"]:
        raise RuntimeError("historical v2 receipt must remain failed and un-upgraded")

    cases = []
    # Case 1: injected ENOENT on leaf cpu.stat retains errno/path/operation.
    root = output / "injected_enoent"
    parent = root / "parent"
    leaf = root / "leaf"
    _write_cgroup(parent, 1000, 0, 0)
    _write_cgroup(leaf, 500, 1, 1)
    (leaf / "cpu.stat").unlink()
    watcher = DiagnosticWatchdog(time.monotonic(), parent, leaf, wall_seconds=120)
    watcher.check()
    if not watcher.error or watcher.error.get("reason") != "resource_observation_OSError":
        raise RuntimeError("injected ENOENT was not retained as resource_observation_OSError")
    oserror = watcher.error["oserror"]
    if oserror.get("errno") != errno.ENOENT or oserror.get("operation") != "leaf.read:cpu.stat":
        raise RuntimeError(f"diagnostic OSError record incomplete: {oserror}")
    cases.append({"name": "injected_enoent", "error": watcher.error, "diagnostics": watcher.diagnostics})
    write_json(root / "result.json", cases[-1])

    # Case 2: benign leaf disappearance with stable empty parent is accepted.
    root = output / "benign_disappearance"
    parent = root / "parent"
    leaf = root / "leaf"
    _write_cgroup(parent, 2000, 0, 0)
    _write_cgroup(leaf, 1500, 1, 1)
    watcher = DiagnosticWatchdog(time.monotonic(), parent, leaf, wall_seconds=120)
    watcher.sample_parent()
    watcher.sample_leaf()
    for child in leaf.iterdir():
        child.unlink()
    leaf.rmdir()
    watcher.check()
    if watcher.error is not None:
        raise RuntimeError(f"stable empty parent should accept leaf disappearance: {watcher.error}")
    if not watcher.diagnostics or not watcher.diagnostics[-1]["accepted"]:
        raise RuntimeError("benign disappearance was not revalidated")
    cases.append({"name": "benign_disappearance", "error": watcher.error, "diagnostics": watcher.diagnostics})
    write_json(root / "result.json", cases[-1])

    # Case 3: leaf disappearance with parent identity change is not accepted.
    root = output / "unstable_parent"
    parent = root / "parent"
    leaf = root / "leaf"
    _write_cgroup(parent, 3000, 0, 0)
    _write_cgroup(leaf, 1000, 1, 1)
    watcher = DiagnosticWatchdog(time.monotonic(), parent, leaf, wall_seconds=120)
    watcher.sample_parent()
    replacement = root / "parent-replaced"
    _write_cgroup(replacement, 3000, 0, 0)
    watcher.parent = replacement
    for child in leaf.iterdir():
        child.unlink()
    leaf.rmdir()
    watcher.check()
    if watcher.error is None:
        raise RuntimeError("parent identity change must fail")
    if watcher.error.get("reason") not in {
        "parent_identity_changed", "leaf_disappeared_without_parent_revalidation", "resource_observation_OSError"
    }:
        raise RuntimeError(f"unexpected failure mode: {watcher.error}")
    cases.append({"name": "unstable_parent", "error": watcher.error, "diagnostics": watcher.diagnostics})
    write_json(root / "result.json", cases[-1])

    # Case 4: counter regression fails closed.
    root = output / "counter_regression"
    parent = root / "parent"
    _write_cgroup(parent, 8000, 0, 0)
    watcher = DiagnosticWatchdog(time.monotonic(), parent, None, wall_seconds=120)
    watcher.sample_parent()
    (parent / "cpu.stat").write_text("usage_usec 100\nuser_usec 100\nsystem_usec 0\n")
    watcher.check()
    if not watcher.error or watcher.error.get("reason") != "parent_counter_regressed":
        raise RuntimeError(f"counter regression was not retained: {watcher.error}")
    cases.append({"name": "counter_regression", "error": watcher.error, "diagnostics": watcher.diagnostics})
    write_json(root / "result.json", cases[-1])

    # Case 5: whole-attempt 120s bound fires.
    root = output / "wall_bound"
    parent = root / "parent"
    _write_cgroup(parent, 0, 0, 0)
    clock = {"t": 0.0}

    def fake_clock():
        return clock["t"]

    watcher = DiagnosticWatchdog(0.0, parent, None, clock=fake_clock, wall_seconds=120)
    clock["t"] = 120.0
    watcher.check()
    if not watcher.error or watcher.error.get("reason") != "whole_attempt_wall_budget":
        raise RuntimeError(f"120s bound did not fire: {watcher.error}")
    cases.append({"name": "wall_bound", "error": watcher.error, "diagnostics": watcher.diagnostics})
    write_json(root / "result.json", cases[-1])

    report = {
        "schema": "la032-watchdog-diagnostic-qualification/v1",
        "status": "PASS",
        "historical_v2_upgraded": False,
        "oserror_broadly_suppressed": False,
        "parent_accounting_mandatory": True,
        "whole_group_exit_mandatory": True,
        "controls": [c["name"] for c in cases],
        "injected_enoent_errno": errno.ENOENT,
        "injected_enoent_operation": "leaf.read:cpu.stat",
        "historical_investigation_sha256": digest(investigation),
    }
    write_json(output / "qualification.json", report)
    return report


if __name__ == "__main__":
    qualify(Path("qualification/watchdog_oserror"))
