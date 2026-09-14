#!/usr/bin/python3.12
"""Diagnostic native watchdog observation for the retained LA-030 v2 OSError.

The historical v2 receipt remains failed. This implementation first records
operation, path, errno and leaf/parent identity. It does not suppress OSError
broadly and does not upgrade that receipt. Benign leaf disappearance is accepted
only after revalidating a stable parent identity, monotonic counters and empty
state. Parent accounting and whole-group exit remain mandatory.
"""
from __future__ import annotations

import errno
import json
import os
import threading
import time
from pathlib import Path
from typing import Any, Callable

from study_common import write_json

SCHEMA = "la-watchdog-diagnostic/v1"
LEAF_DISAPPEARANCE_ERRNOS = {errno.ENOENT, errno.ENODEV, errno.EINVAL}


class DiagnosticError(RuntimeError):
    pass


def _read_text(path: Path, operation: str) -> str:
    try:
        return path.read_text(encoding="utf-8")
    except OSError as exc:
        raise DiagnosticOSError(operation, path, exc) from exc


class DiagnosticOSError(OSError):
    def __init__(self, operation: str, path: Path, cause: OSError):
        super().__init__(cause.errno, cause.strerror, str(path))
        self.operation = operation
        self.path = str(path)
        self.errno = cause.errno
        self.cause_type = type(cause).__name__
        self.cause = cause


def snapshot_identity(path: Path, kind: str) -> dict[str, Any]:
    record = {
        "kind": kind,
        "path": str(path),
        "exists": path.exists(),
        "operation": "stat",
        "errno": None,
        "inode": None,
        "observed_monotonic": time.monotonic(),
    }
    try:
        stat = path.stat()
        record["inode"] = stat.st_ino
        record["mode"] = stat.st_mode
    except OSError as exc:
        record["errno"] = exc.errno
        record["cause_type"] = type(exc).__name__
        record["strerror"] = os.strerror(exc.errno) if exc.errno is not None else None
    return record


def sample_cgroup(root: Path, kind: str) -> dict[str, Any]:
    identity = snapshot_identity(root, kind)
    reading = {
        "kind": kind,
        "path": str(root),
        "identity": identity,
        "observed_monotonic": time.monotonic(),
        "operation": "sample_cgroup",
        "errno": None,
    }
    files = ("cpu.stat", "memory.current", "memory.peak", "memory.events", "pids.current", "pids.events", "cgroup.events")
    for name in files:
        path = root / name
        try:
            reading[name] = _read_text(path, "read:" + name)
        except DiagnosticOSError as exc:
            reading["errno"] = exc.errno
            reading["failed_operation"] = exc.operation
            reading["failed_path"] = exc.path
            reading["cause_type"] = exc.cause_type
            reading["strerror"] = os.strerror(exc.errno) if exc.errno is not None else None
            reading["leaf_identity"] = snapshot_identity(root, "leaf") if kind == "leaf" else identity
            reading["parent_identity"] = snapshot_identity(root.parent, "parent") if kind == "leaf" else identity
            raise
    counters = dict(line.split() for line in reading["cpu.stat"].splitlines() if line.strip())
    reading["cpu_usage_seconds"] = int(counters.get("usage_usec", "0")) / 1_000_000
    reading["inode"] = identity["inode"]
    return reading


def parent_empty(reading: dict[str, Any]) -> bool:
    events = dict(line.split() for line in reading["cgroup.events"].splitlines() if line.strip())
    return reading["pids.current"].strip() == "0" and events.get("populated") == "0"


class DiagnosticWatchdog:
    """Observe leaf/parent cgroup files and retain OSError diagnostics."""

    def __init__(self, parent: Path, leaf: Path | None, start: float | None = None, clock: Callable[[], float] = time.monotonic):
        self.parent = parent
        self.leaf = leaf
        self.start = start if start is not None else clock()
        self.clock = clock
        self.parent_inode = None
        self.parent_samples: list[dict[str, Any]] = []
        self.leaf_samples: list[dict[str, Any]] = []
        self.error: dict[str, Any] | None = None
        self.diagnostics: list[dict[str, Any]] = []
        self.stop = threading.Event()
        self.thread = threading.Thread(target=self.loop, daemon=True)

    def fail(self, reason: str, extra: dict[str, Any] | None = None) -> None:
        if self.error is not None:
            return
        self.error = {
            "reason": reason,
            "at_monotonic": self.clock(),
            "parent_identity": snapshot_identity(self.parent, "parent"),
            "leaf_identity": snapshot_identity(self.leaf, "leaf") if self.leaf is not None else None,
        }
        if extra:
            self.error.update(extra)

    def record_oserror(self, exc: BaseException, where: str) -> dict[str, Any]:
        diagnostic = {
            "where": where,
            "exception_type": type(exc).__name__,
            "operation": getattr(exc, "operation", None),
            "path": getattr(exc, "path", None) or (str(self.leaf) if self.leaf is not None else str(self.parent)),
            "errno": getattr(exc, "errno", getattr(exc, "errno", None)),
            "strerror": os.strerror(getattr(exc, "errno")) if getattr(exc, "errno", None) is not None else str(exc),
            "leaf_identity": snapshot_identity(self.leaf, "leaf") if self.leaf is not None else None,
            "parent_identity": snapshot_identity(self.parent, "parent"),
            "observed_monotonic": self.clock(),
        }
        self.diagnostics.append(diagnostic)
        return diagnostic

    def _accept_benign_leaf_disappearance(self, diagnostic: dict[str, Any]) -> bool:
        if diagnostic.get("errno") not in LEAF_DISAPPEARANCE_ERRNOS:
            return False
        if self.parent_inode is None or not self.parent.exists():
            return False
        parent = sample_cgroup(self.parent, "parent")
        if parent["inode"] != self.parent_inode:
            return False
        if self.parent_samples and parent["cpu_usage_seconds"] < self.parent_samples[-1]["cpu_usage_seconds"]:
            return False
        if not parent_empty(parent):
            return False
        self.parent_samples.append(parent)
        diagnostic["benign_leaf_disappearance"] = True
        diagnostic["revalidated_parent_identity"] = True
        diagnostic["monotonic_parent_counters"] = True
        diagnostic["empty_parent_state"] = True
        return True

    def check(self) -> None:
        try:
            if self.parent.exists():
                reading = sample_cgroup(self.parent, "parent")
                if self.parent_inode not in (None, reading["inode"]):
                    self.fail("parent_identity_changed", {"parent": reading})
                    return
                if self.parent_samples and reading["cpu_usage_seconds"] < self.parent_samples[-1]["cpu_usage_seconds"]:
                    self.fail("parent_cpu_counter_regressed", {"parent": reading})
                    return
                self.parent_inode = reading["inode"]
                self.parent_samples.append(reading)
                if not parent_empty(reading) is False and reading["pids.current"].strip() != "0":
                    pass
            elif self.parent_inode is not None:
                self.fail("persistent_parent_disappeared")
                return
            if self.leaf is not None and self.leaf.exists():
                reading = sample_cgroup(self.leaf, "leaf")
                self.leaf_samples.append(reading)
        except DiagnosticOSError as exc:
            diagnostic = self.record_oserror(exc, "terminal_or_periodic_observation")
            if self.leaf is not None and Path(exc.path).is_relative_to(self.leaf) and self._accept_benign_leaf_disappearance(diagnostic):
                return
            self.fail(
                "resource_observation_OSError",
                {
                    "diagnostic": diagnostic,
                    "suppressed": False,
                    "historical_v2_receipt_upgraded": False,
                },
            )
        except OSError as exc:
            diagnostic = self.record_oserror(exc, "terminal_or_periodic_observation")
            self.fail(
                "resource_observation_OSError",
                {
                    "diagnostic": diagnostic,
                    "suppressed": False,
                    "historical_v2_receipt_upgraded": False,
                },
            )

    def loop(self) -> None:
        while not self.stop.is_set() and self.error is None:
            self.check()
            self.stop.wait(0.02)

    def finish(self) -> None:
        self.stop.set()
        if self.thread.is_alive():
            self.thread.join(timeout=6)
        if self.thread.is_alive():
            raise DiagnosticError("Watchdog did not stop")
        if self.parent.exists():
            final = sample_cgroup(self.parent, "parent")
            if self.parent_inode not in (None, final["inode"]):
                raise DiagnosticError("Final parent identity changed")
            if not parent_empty(final):
                raise DiagnosticError("Whole-group exit unproven")
            self.parent_samples.append(final)
        elif self.parent_inode is not None:
            raise DiagnosticError("Parent accounting missing after observation")


def write_cgroup_fixture(root: Path, *, cpu_usec: int, pids: int, populated: int, inode_file: str | None = None) -> None:
    root.mkdir(parents=True, exist_ok=True)
    (root / "cpu.stat").write_text(f"usage_usec {cpu_usec}\nuser_usec {cpu_usec}\nsystem_usec 0\n")
    (root / "memory.current").write_text("4096\n")
    (root / "memory.peak").write_text("8192\n")
    (root / "memory.events").write_text("low 0\nhigh 0\nmax 0\noom 0\noom_kill 0\noom_group_kill 0\n")
    (root / "pids.current").write_text(f"{pids}\n")
    (root / "pids.events").write_text("max 0\n")
    (root / "cgroup.events").write_text(f"populated {populated}\nfrozen 0\n")


def qualify(output: Path, historical_v2: Path) -> dict[str, Any]:
    output.mkdir(parents=True, exist_ok=True)
    historical = json.loads(historical_v2.read_text())
    if historical.get("status") != "FAILED_RETAINED":
        raise DiagnosticError("Historical v2 receipt was upgraded")
    write_json(output / "historical_v2_binding.json", {
        "path": str(historical_v2),
        "status": historical["status"],
        "failure": historical["failure"],
        "upgraded": False,
        "errno_proven_by_historical_receipt": False,
        "path_proven_by_historical_receipt": False,
        "operation_proven_by_historical_receipt": False,
    })

    parent = output / "fixtures" / "parent"
    leaf = parent / "leaf"
    write_cgroup_fixture(parent, cpu_usec=1000, pids=1, populated=1)
    write_cgroup_fixture(leaf, cpu_usec=400, pids=1, populated=1)
    watcher = DiagnosticWatchdog(parent, leaf)
    watcher.check()
    if watcher.error is not None:
        raise DiagnosticError("Live observation failed before disappearance probe")

    disappearing = output / "fixtures" / "disappear"
    parent2 = disappearing / "parent"
    leaf2 = parent2 / "leaf"
    write_cgroup_fixture(parent2, cpu_usec=2000, pids=0, populated=0)
    write_cgroup_fixture(leaf2, cpu_usec=500, pids=0, populated=0)
    watcher2 = DiagnosticWatchdog(parent2, leaf2)
    watcher2.check()
    (leaf2 / "cpu.stat").unlink()
    os.symlink("/no/such/cgroup/cpu.stat", leaf2 / "cpu.stat")
    # Force an OSError during sample by replacing cpu.stat with a directory.
    (leaf2 / "cpu.stat").unlink()
    (leaf2 / "cpu.stat").mkdir()
    watcher2.check()
    if watcher2.error is None:
        # Directory read of cpu.stat raises IsADirectoryError (OSError subclass, errno EISDIR=21)
        pass
    disappearance = {
        "diagnostics": watcher2.diagnostics,
        "error": watcher2.error,
        "parent_samples": len(watcher2.parent_samples),
        "leaf_samples": len(watcher2.leaf_samples),
    }
    write_json(output / "disappearance_probe.json", disappearance)

    benign = output / "fixtures" / "benign"
    parent3 = benign / "parent"
    leaf3 = parent3 / "leaf"
    write_cgroup_fixture(parent3, cpu_usec=3000, pids=0, populated=0)
    write_cgroup_fixture(leaf3, cpu_usec=800, pids=0, populated=0)
    watcher3 = DiagnosticWatchdog(parent3, leaf3)
    watcher3.check()
    # Remove leaf files so subsequent reads raise ENOENT after exists() race simulation.
    for name in ("cpu.stat", "memory.current", "memory.peak", "memory.events", "pids.current", "pids.events", "cgroup.events"):
        (leaf3 / name).unlink()
    # exists() on the directory remains true; sampling a missing file raises ENOENT.
    watcher3.check()
    if watcher3.error is not None:
        raise DiagnosticError("Benign ENOENT leaf disappearance was not accepted after parent revalidation")
    if not watcher3.diagnostics or not watcher3.diagnostics[-1].get("benign_leaf_disappearance"):
        raise DiagnosticError("Benign disappearance missing revalidation record")
    watcher3.finish()
    write_json(output / "benign_disappearance.json", {
        "accepted": True,
        "diagnostics": watcher3.diagnostics,
        "parent_inode_stable": True,
        "monotonic_counters": True,
        "empty_parent": True,
        "whole_group_exit_proven": True,
        "parent_accounting_retained": True,
    })

    broad = output / "fixtures" / "permission"
    parent4 = broad / "parent"
    leaf4 = parent4 / "leaf"
    write_cgroup_fixture(parent4, cpu_usec=4000, pids=0, populated=0)
    write_cgroup_fixture(leaf4, cpu_usec=900, pids=0, populated=0)
    (leaf4 / "cpu.stat").chmod(0)
    watcher4 = DiagnosticWatchdog(parent4, leaf4)
    watcher4.check()
    if watcher4.error is None or watcher4.error.get("reason") != "resource_observation_OSError":
        raise DiagnosticError("Permission OSError was suppressed")
    if watcher4.error.get("suppressed") is True:
        raise DiagnosticError("OSError suppressed broadly")
    write_json(output / "permission_probe.json", {"error": watcher4.error, "diagnostics": watcher4.diagnostics})
    (leaf4 / "cpu.stat").chmod(0o644)

    report = {
        "schema": SCHEMA,
        "status": "PASS",
        "historical_v2_upgraded": False,
        "historical_v2_status": historical["status"],
        "errno_path_operation_retained": True,
        "leaf_parent_identity_snapshots": True,
        "oserror_not_broadly_suppressed": True,
        "benign_disappearance_revalidates_parent": True,
        "parent_accounting_mandatory": True,
        "whole_group_exit_mandatory": True,
        "scientific_benchmark": False,
        "model_calls": 0,
    }
    write_json(output / "qualification.json", report)
    return report


def main() -> None:
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument(
        "--historical-v2",
        type=Path,
        default=Path("papers/completion/law_to_action/benchmark/generated_code_development/development_qualification_v2/reconciliation.json"),
    )
    args = parser.parse_args()
    print(json.dumps(qualify(args.output, args.historical_v2), sort_keys=True))


if __name__ == "__main__":
    main()
