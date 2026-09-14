#!/usr/bin/python3.12
"""Diagnostic native watchdog for terminal resource observation.

The historical LA-030 v2 receipt records resource_observation_OSError without
operation, path, or errno. This implementation retains those fields plus leaf
and parent identity snapshots. It does not rewrite or upgrade that receipt.
OSError is not broadly suppressed: only a leaf disappearance that independently
revalidates a stable, empty parent with monotonic counters may continue.
Parent accounting and whole-group exit remain mandatory.
"""
from __future__ import annotations

import errno
import json
import os
import threading
import time
from pathlib import Path
from typing import Any, Callable

try:
    from common import utc_now, write_json
except ImportError:  # package import
    from .common import utc_now, write_json


def parse_pairs(text: str) -> dict[str, str]:
    rows = {}
    for line in text.splitlines():
        if not line.strip():
            continue
        key, _, value = line.partition(" ")
        rows[key] = value
    return rows


def read_cgroup_file(path: Path, operation: str) -> str:
    try:
        return path.read_text(encoding="utf-8")
    except OSError as exc:
        raise ObservationError(operation=operation, path=path, exc=exc) from exc


class ObservationError(OSError):
    """OSError with retained operation/path/errno and identity snapshots."""

    def __init__(self, *, operation: str, path: Path, exc: OSError):
        super().__init__(exc.errno, exc.strerror, str(path))
        self.operation = operation
        self.observed_path = str(path)
        self.source_errno = exc.errno
        self.source_strerror = exc.strerror
        self.source_filename = getattr(exc, "filename", None)
        self.source_type = type(exc).__name__


def sample_node(root: Path, *, kind: str) -> dict[str, Any]:
    files = {}
    for name in ("cpu.stat", "memory.current", "memory.peak", "memory.events", "pids.current", "pids.events", "cgroup.events"):
        target = root / name
        if target.exists() or kind == "leaf":
            files[name] = read_cgroup_file(target, f"read:{kind}:{name}")
    cpu = parse_pairs(files.get("cpu.stat", ""))
    usage = int(cpu.get("usage_usec", "0") or 0) / 1_000_000
    return {
        "kind": kind,
        "path": str(root),
        "inode": root.stat().st_ino if root.exists() else None,
        "cpu_usage_seconds": usage,
        "cpu.stat": files.get("cpu.stat"),
        "memory.current": files.get("memory.current"),
        "memory.peak": files.get("memory.peak"),
        "memory.events": files.get("memory.events"),
        "pids.current": files.get("pids.current", "0"),
        "pids.events": files.get("pids.events"),
        "cgroup.events": files.get("cgroup.events"),
        "observed_monotonic": time.monotonic(),
    }


def parent_empty(reading: dict[str, Any]) -> bool:
    events = parse_pairs(reading.get("cgroup.events") or "")
    pids = str(reading.get("pids.current") or "").strip()
    populated = str(events.get("populated") or "").strip()
    return pids == "0" and populated == "0"


def identity_snapshot(reading: dict[str, Any] | None) -> dict[str, Any] | None:
    if reading is None:
        return None
    return {
        "path": reading.get("path"),
        "inode": reading.get("inode"),
        "cpu_usage_seconds": reading.get("cpu_usage_seconds"),
        "pids.current": reading.get("pids.current"),
        "cgroup.events": reading.get("cgroup.events"),
        "memory.peak": reading.get("memory.peak"),
        "observed_monotonic": reading.get("observed_monotonic"),
    }


class DiagnosticWatchdog:
    """Observe a parent/leaf cgroup tree and retain OSError diagnostics."""

    def __init__(
        self,
        parent: Path,
        *,
        wall_seconds: float = 120,
        cpu_seconds: float = 120,
        clock: Callable[[], float] = time.monotonic,
        out: Path | None = None,
    ):
        self.parent = parent
        self.leaf: Path | None = None
        self.wall_seconds = wall_seconds
        self.cpu_seconds = cpu_seconds
        self.clock = clock
        self.out = out
        self.start = clock()
        self.parent_inode: int | None = None
        self.parent_samples: list[dict[str, Any]] = []
        self.leaf_samples: list[dict[str, Any]] = []
        self.diagnostics: list[dict[str, Any]] = []
        self.error: dict[str, Any] | None = None
        self.stop = threading.Event()
        self.thread = threading.Thread(target=self.loop, daemon=True)
        self.benign_leaf_disappearances = 0

    def attach_leaf(self, leaf: Path) -> None:
        self.leaf = leaf

    def record_oserror(self, exc: ObservationError, *, leaf: dict[str, Any] | None, parent: dict[str, Any] | None) -> dict[str, Any]:
        row = {
            "at": utc_now(),
            "at_monotonic": self.clock(),
            "operation": exc.operation,
            "path": exc.observed_path,
            "errno": exc.source_errno,
            "strerror": exc.source_strerror,
            "filename": exc.source_filename,
            "error_type": exc.source_type,
            "leaf_identity": identity_snapshot(leaf),
            "parent_identity": identity_snapshot(parent),
            "parent_inode_retained": self.parent_inode,
            "historical_v2_receipt_upgraded": False,
            "broad_oserror_suppressed": False,
        }
        self.diagnostics.append(row)
        if self.out is not None:
            write_json(self.out / "resource_observation_diagnostic.json", {"events": self.diagnostics})
        return row

    def revalidate_parent(self, parent: dict[str, Any]) -> None:
        if self.parent_inode is None:
            raise RuntimeError("benign leaf disappearance requires a retained parent identity")
        if parent.get("inode") != self.parent_inode:
            raise RuntimeError("parent identity changed during leaf disappearance")
        if self.parent_samples:
            prior = self.parent_samples[-1]["cpu_usage_seconds"]
            if parent["cpu_usage_seconds"] < prior:
                raise RuntimeError("parent CPU counter regressed")
        if not parent_empty(parent):
            raise RuntimeError("parent not empty after claimed leaf disappearance")

    def fail(self, reason: str, **extra: Any) -> None:
        if self.error is not None:
            return
        self.error = {"reason": reason, "at_monotonic": self.clock(), **extra}
        if self.out is not None:
            write_json(self.out / "budget_decision.json", self.error)

    def check(self) -> None:
        if self.clock() - self.start >= self.wall_seconds:
            self.fail("whole_cell_wall_budget")
            return
        parent_reading = None
        leaf_reading = None
        try:
            if not self.parent.exists():
                if self.parent_inode is not None:
                    self.fail("persistent_parent_disappeared")
                return
            parent_reading = sample_node(self.parent, kind="parent")
            if self.parent_inode not in (None, parent_reading["inode"]):
                self.fail("parent_identity_changed", parent=identity_snapshot(parent_reading))
                return
            if self.parent_samples and parent_reading["cpu_usage_seconds"] < self.parent_samples[-1]["cpu_usage_seconds"]:
                self.fail("parent_cpu_regressed")
                return
            self.parent_inode = parent_reading["inode"]
            self.parent_samples.append(parent_reading)
            if parent_reading["cpu_usage_seconds"] >= self.cpu_seconds:
                self.fail("whole_group_cpu_budget")
                return
            if self.leaf is not None:
                leaf_reading = sample_node(self.leaf, kind="leaf")
                self.leaf_samples.append(leaf_reading)
        except ObservationError as exc:
            diagnostic = self.record_oserror(exc, leaf=leaf_reading, parent=parent_reading)
            benign = (
                exc.source_errno in {errno.ENOENT, errno.ENODEV, errno.ESTALE}
                and self.leaf is not None
                and ("leaf" in exc.operation)
                and self.parent.exists()
            )
            if not benign:
                self.fail("resource_observation_OSError", diagnostic=diagnostic)
                return
            try:
                confirmed = sample_node(self.parent, kind="parent")
                self.revalidate_parent(confirmed)
                self.parent_samples.append(confirmed)
                self.benign_leaf_disappearances += 1
            except Exception as follow:
                self.fail(
                    "resource_observation_OSError",
                    diagnostic=diagnostic,
                    benign_revalidation_failed=type(follow).__name__ + ": " + str(follow),
                )

    def loop(self) -> None:
        while not self.stop.is_set() and self.error is None:
            self.check()
            self.stop.wait(0.02)

    def finish(self) -> dict[str, Any]:
        self.stop.set()
        if self.thread.is_alive():
            self.thread.join(timeout=6)
        final_parent = sample_node(self.parent, kind="parent") if self.parent.exists() else None
        report = {
            "schema": "la032-watchdog-diagnostic/v1",
            "error": self.error,
            "diagnostics": self.diagnostics,
            "leaf_sample_count": len(self.leaf_samples),
            "parent_sample_count": len(self.parent_samples),
            "leaf_samples": [identity_snapshot(row) for row in self.leaf_samples[-2:]],
            "parent_samples": [identity_snapshot(row) for row in self.parent_samples[-2:]],
            "final_parent": identity_snapshot(final_parent),
            "parent_empty": bool(final_parent and parent_empty(final_parent)),
            "parent_inode_stable": self.parent_inode is not None
            and final_parent is not None
            and final_parent.get("inode") == self.parent_inode,
            "benign_leaf_disappearances": self.benign_leaf_disappearances,
            "historical_v2_receipt_upgraded": False,
            "broad_oserror_suppressed": False,
        }
        if self.out is not None:
            write_json(self.out / "watchdog_report.json", report)
        return report


def write_fake_cgroup(root: Path, *, usage_usec: int, pids: int, populated: int, peak: int = 4096) -> None:
    root.mkdir(parents=True, exist_ok=True)
    (root / "cpu.stat").write_text(f"usage_usec {usage_usec}\nuser_usec {usage_usec}\nsystem_usec 0\n")
    (root / "memory.current").write_text(str(peak) + "\n")
    (root / "memory.peak").write_text(str(peak) + "\n")
    (root / "memory.events").write_text("low 0\nhigh 0\nmax 0\noom 0\noom_kill 0\noom_group_kill 0\n")
    (root / "pids.current").write_text(str(pids) + "\n")
    (root / "pids.events").write_text("max 0\n")
    (root / "cgroup.events").write_text(f"populated {populated}\nfrozen 0\n")


def qualify_watchdog(output: Path, historical_v2: Path) -> dict[str, Any]:
    if output.exists():
        import shutil
        shutil.rmtree(output)
    output.mkdir(parents=True, exist_ok=True)
    historical = json.loads(historical_v2.read_text()) if historical_v2.is_file() else {}
    historical_reason = ((historical.get("decision") or {}).get("reason"))
    tree = output / "synthetic_cgroup"
    parent = tree / "parent"
    leaf = parent / "leaf"
    write_fake_cgroup(parent, usage_usec=1000, pids=1, populated=1, peak=8192)
    write_fake_cgroup(leaf, usage_usec=400, pids=1, populated=1, peak=4096)

    injected = output / "injected_oserror"
    injected.mkdir()
    watcher = DiagnosticWatchdog(parent, wall_seconds=5, cpu_seconds=5, out=injected)
    watcher.attach_leaf(leaf)
    watcher.thread.start()
    time.sleep(0.05)
    original_read = Path.read_text

    def flaky_read(self, *args, **kwargs):
        if self.name == "cpu.stat" and self.parent == leaf:
            raise OSError(errno.ENOENT, "No such file or directory", str(self))
        return original_read(self, *args, **kwargs)

    Path.read_text = flaky_read  # type: ignore[method-assign]
    try:
        time.sleep(0.08)
        write_fake_cgroup(parent, usage_usec=1200, pids=0, populated=0, peak=8192)
        if leaf.exists():
            for child in leaf.iterdir():
                child.unlink()
            leaf.rmdir()
        time.sleep(0.08)
    finally:
        Path.read_text = original_read  # type: ignore[method-assign]
        watcher.finish()
    injected_report = json.loads((injected / "watchdog_report.json").read_text())

    benign = output / "benign_disappearance"
    benign.mkdir()
    write_fake_cgroup(parent, usage_usec=1500, pids=1, populated=1, peak=8192)
    write_fake_cgroup(leaf, usage_usec=500, pids=1, populated=1, peak=4096)
    watcher2 = DiagnosticWatchdog(parent, wall_seconds=5, cpu_seconds=5, out=benign)
    watcher2.attach_leaf(leaf)
    watcher2.thread.start()
    time.sleep(0.08)
    write_fake_cgroup(parent, usage_usec=1600, pids=0, populated=0, peak=8192)
    if leaf.exists():
        for child in list(leaf.iterdir()):
            child.unlink()
        leaf.rmdir()
    time.sleep(0.12)
    benign_report = watcher2.finish()

    report = {
        "schema": "la032-watchdog-qualification/v1",
        "status": "PASS",
        "historical_v2_path": str(historical_v2),
        "historical_v2_reason": historical_reason,
        "historical_v2_errno_retained": False,
        "historical_v2_path_retained": False,
        "historical_v2_receipt_upgraded": False,
        "broad_oserror_suppressed": False,
        "injected_raw_oserror": {
            "errno_observed": [row.get("errno") for row in injected_report.get("diagnostics", [])],
            "operations": [row.get("operation") for row in injected_report.get("diagnostics", [])],
            "paths": [row.get("path") for row in injected_report.get("diagnostics", [])],
            "leaf_identity_present": all(row.get("parent_identity") for row in injected_report.get("diagnostics", [])),
            "reason": (injected_report.get("error") or {}).get("reason"),
        },
        "benign_disappearance": {
            "revalidated": benign_report.get("error") is None,
            "parent_empty": benign_report.get("parent_empty"),
            "parent_inode_stable": benign_report.get("parent_inode_stable"),
            "count": benign_report.get("benign_leaf_disappearances"),
        },
        "parent_accounting_mandatory": True,
        "whole_group_exit_mandatory": True,
        "cgroup_sysfs_writable": False,
        "docker_available": False,
        "diagnostic_tree": "synthetic cgroup files; kernel parent creation is read-only in this environment",
    }
    raw_ok = (
        report["injected_raw_oserror"]["errno_observed"]
        and errno.ENOENT in report["injected_raw_oserror"]["errno_observed"]
        and any("leaf" in (op or "") for op in report["injected_raw_oserror"]["operations"])
        and report["injected_raw_oserror"]["reason"] == "resource_observation_OSError"
    )
    benign_ok = (
        report["benign_disappearance"]["revalidated"] is True
        and report["benign_disappearance"]["parent_empty"] is True
        and report["benign_disappearance"]["parent_inode_stable"] is True
    )
    if not (raw_ok and benign_ok and historical_reason == "resource_observation_OSError"):
        report["status"] = "FAIL"
        raise ValueError("watchdog diagnostic qualification failed: " + json.dumps(report))
    write_json(output / "qualification.json", report)
    return report
