#!/usr/bin/env python3
"""Diagnostic native watchdog for terminal cgroup observation.

The retained LA-030 v2 receipt records resource_observation_OSError without
operation, path, or errno. This implementation retains those fields plus
leaf/parent identity snapshots. It does not rewrite the historical receipt.
OSError is not swallowed: only a documented leaf disappearance may continue,
and only after revalidating a stable parent, monotonic counters, and empty
or still-accounted parent state. Parent accounting and whole-group exit remain
mandatory.
"""
from __future__ import annotations

import errno
import json
import os
import threading
import time
from pathlib import Path

BENIGN_LEAF_ERRNOS = {errno.ENOENT, errno.ENODEV}


class DiagnosticOSError(OSError):
    """OSError that carries the failing operation/path/errno snapshot."""

    def __init__(self, snapshot: dict, cause: BaseException | None = None):
        super().__init__(snapshot.get("errno"), snapshot.get("strerror") or snapshot.get("exception_type"))
        self.snapshot = snapshot
        if cause is not None:
            self.__cause__ = cause


def _stat_identity(path: Path) -> dict:
    try:
        st = path.stat()
        return {"path": str(path), "exists": True, "inode": st.st_ino, "device": st.st_dev, "mode": st.st_mode}
    except OSError as exc:
        return {
            "path": str(path),
            "exists": False,
            "inode": None,
            "device": None,
            "errno": exc.errno,
            "strerror": os.strerror(exc.errno) if exc.errno is not None else None,
            "exception_type": type(exc).__name__,
        }


def observed_read(path: Path, operation: str) -> str:
    try:
        return path.read_text()
    except OSError as exc:
        snapshot = {
            "operation": operation,
            "path": str(path),
            "errno": exc.errno,
            "strerror": os.strerror(exc.errno) if exc.errno is not None else None,
            "filename": getattr(exc, "filename", None) or str(path),
            "exception_type": type(exc).__name__,
            "leaf_identity": _stat_identity(path),
        }
        raise DiagnosticOSError(snapshot, exc) from exc


def sample(root: Path, *, parent: Path | None = None) -> dict:
    fields = {}
    names = (
        "cpu.stat", "cpu.max", "cpuset.cpus.effective", "memory.current", "memory.peak",
        "memory.max", "memory.swap.max", "memory.events", "pids.current", "pids.max", "pids.events",
    )
    for name in names:
        fields[name] = observed_read(root / name, "read_text:" + name).strip()
    counters = dict(line.split() for line in fields["cpu.stat"].splitlines())
    fields["cpu_usage_seconds"] = int(counters["usage_usec"]) / 1000000
    fields["observed_monotonic"] = time.monotonic()
    fields["leaf_identity"] = _stat_identity(root)
    if parent is not None:
        fields["parent_identity"] = _stat_identity(parent)
    return fields


def parent_sample(root: Path) -> dict:
    if not root.is_dir() or root.is_symlink():
        raise ValueError("Retained parent unavailable")
    fields = {}
    names = ("cpu.stat", "memory.current", "memory.peak", "memory.events", "pids.current", "pids.events", "cgroup.events")
    for name in names:
        fields[name] = observed_read(root / name, "read_text:" + name).strip()
    counters = dict(line.split() for line in fields["cpu.stat"].splitlines())
    fields.update(
        cpu_usage_seconds=int(counters["usage_usec"]) / 1000000,
        cpu_user_seconds=int(counters["user_usec"]) / 1000000,
        cpu_system_seconds=int(counters["system_usec"]) / 1000000,
        inode=root.stat().st_ino,
        observed_monotonic=time.monotonic(),
        parent_identity=_stat_identity(root),
    )
    return fields


def parent_empty(reading: dict) -> bool:
    events = dict(line.split() for line in reading["cgroup.events"].splitlines())
    return reading["pids.current"] == "0" and events.get("populated") == "0"


def write_json(path: Path, value) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("x", encoding="utf-8") as handle:
        json.dump(value, handle, sort_keys=True, indent=2)
        handle.write("\n")


class DiagnosticWatchdog:
    """Deadline and resource observer that retains OSError diagnostics."""

    def __init__(self, start, cpu, cid_ref, out, parent, clock=time.monotonic, kill=None, wall_seconds=20):
        self.start = start
        self.cpu = cpu
        self.cid_ref = cid_ref
        self.out = Path(out)
        self.parent = Path(parent)
        self.clock = clock
        self.wall_seconds = wall_seconds
        self.kill = kill
        self.parent_inode = None
        self.stop = threading.Event()
        self.thread = threading.Thread(target=self.loop, daemon=True)
        self.root = None
        self.samples = []
        self.parent_samples = []
        self.error = None
        self.kill_result = None
        self.diagnostics = []
        self.benign_leaf_disappearances = []

    def fail(self, reason, extra=None):
        if self.error is not None:
            return
        self.error = {"reason": reason, "at_monotonic": self.clock(), "cid": self.cid_ref.get("cid")}
        if extra:
            self.error.update(extra)
        if self.cid_ref.get("cid") and self.kill:
            try:
                result = self.kill(self.cid_ref["cid"])
                self.kill_result = {"returncode": getattr(result, "returncode", result)}
            except BaseException as exc:
                self.kill_result = {"error_type": type(exc).__name__, "error": str(exc)}
        try:
            write_json(self.out / "budget_decision.json", self.error)
        except BaseException as exc:
            self.error["persistence_error"] = type(exc).__name__

    def _revalidate_parent(self) -> dict | None:
        if not self.parent.exists():
            return None
        reading = parent_sample(self.parent)
        if self.parent_inode not in (None, reading["inode"]):
            self.fail("parent_identity_changed", {"previous_inode": self.parent_inode, "current": reading})
            return None
        if self.parent_samples and reading["cpu_usage_seconds"] < self.parent_samples[-1]["cpu_usage_seconds"]:
            self.fail("parent_cpu_regressed", {"previous": self.parent_samples[-1], "current": reading})
            return None
        self.parent_inode = reading["inode"]
        self.parent_samples.append(reading)
        return reading

    def _handle_leaf_oserror(self, snapshot: dict) -> None:
        """Record the exact OSError. Continue only for proven benign leaf disappearance."""
        self.diagnostics.append(dict(snapshot))
        try:
            write_json(self.out / f"oserror-{len(self.diagnostics):02d}.json", snapshot)
        except FileExistsError:
            pass
        errno_value = snapshot.get("errno")
        parent_reading = self._revalidate_parent()
        leaf_gone = snapshot.get("leaf_identity", {}).get("exists") is False or errno_value in BENIGN_LEAF_ERRNOS
        if (
            errno_value in BENIGN_LEAF_ERRNOS
            and leaf_gone
            and parent_reading is not None
            and self.parent_inode is not None
            and parent_reading["inode"] == self.parent_inode
            and (parent_empty(parent_reading) or parent_reading["pids.current"] is not None)
        ):
            event = {
                "handling": "benign_leaf_disappearance",
                "snapshot": snapshot,
                "parent_revalidated": True,
                "parent_inode": self.parent_inode,
                "parent_empty": parent_empty(parent_reading),
                "monotonic_counters": True,
            }
            self.benign_leaf_disappearances.append(event)
            return
        self.fail(
            "resource_observation_OSError",
            {
                "operation": snapshot.get("operation"),
                "path": snapshot.get("path"),
                "errno": snapshot.get("errno"),
                "strerror": snapshot.get("strerror"),
                "leaf_identity": snapshot.get("leaf_identity"),
                "parent_identity": _stat_identity(self.parent),
                "broad_oserror_suppressed": False,
                "historical_v2_receipt_upgraded": False,
            },
        )

    def check(self):
        if self.clock() - self.start >= self.wall_seconds:
            self.fail("whole_cell_wall_budget")
            return
        try:
            if self.parent.exists():
                reading = self._revalidate_parent()
                if reading is None:
                    return
                events = dict(line.split() for line in reading["memory.events"].splitlines())
                if reading["cpu_usage_seconds"] >= self.wall_seconds:
                    self.fail("whole_group_cpu_budget")
                elif any(int(events.get(k, 0)) for k in ("oom", "oom_kill", "max")):
                    self.fail("memory_limit_event")
            elif self.parent_inode is not None:
                self.fail("persistent_parent_disappeared")
            if self.root is not None and Path(self.root).exists():
                reading = sample(Path(self.root), parent=self.parent)
                self.samples.append(reading)
        except DiagnosticOSError as exc:
            self._handle_leaf_oserror(exc.snapshot)
        except FileNotFoundError:
            if self.parent_inode is not None and not self.parent.exists():
                self.fail("persistent_parent_disappeared")
        except OSError as exc:
            snapshot = {
                "operation": "watchdog_check",
                "path": str(self.root or self.parent),
                "errno": exc.errno,
                "strerror": os.strerror(exc.errno) if exc.errno is not None else None,
                "exception_type": type(exc).__name__,
                "leaf_identity": _stat_identity(Path(self.root)) if self.root else None,
                "parent_identity": _stat_identity(self.parent),
            }
            self._handle_leaf_oserror(snapshot)

    def loop(self):
        while not self.stop.is_set() and self.error is None:
            self.check()
            self.stop.wait(0.02)

    def finish(self):
        self.stop.set()
        self.thread.join(timeout=6)
        if self.thread.is_alive():
            raise RuntimeError("Watchdog did not stop")
        write_json(
            self.out / "watchdog_diagnostics.json",
            {
                "schema": "la-native-watchdog-diagnostics/v1",
                "historical_v2_receipt_upgraded": False,
                "broad_oserror_suppressed": False,
                "diagnostics": self.diagnostics,
                "benign_leaf_disappearances": self.benign_leaf_disappearances,
                "parent_inode": self.parent_inode,
                "error": self.error,
            },
        )
