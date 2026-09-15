#!/usr/bin/env python3
"""Diagnostic native watchdog for terminal observation.

The historical LA-030 v2 receipt records resource_observation_OSError without
operation, path or errno. This implementation retains those fields plus leaf
and parent identity snapshots. It does not suppress OSError and does not
upgrade the failed v2 receipt.
"""
from __future__ import annotations

import errno
import json
import os
import sys
import threading
import time
from pathlib import Path
from typing import Any, Mapping

HERE = Path(__file__).resolve().parent.parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))

PARENT_FILES = (
    "cpu.stat",
    "memory.current",
    "memory.peak",
    "memory.events",
    "pids.current",
    "pids.events",
    "cgroup.events",
)
LEAF_FILES = (
    "cpu.stat",
    "cpu.max",
    "cpuset.cpus.effective",
    "memory.current",
    "memory.peak",
    "memory.max",
    "memory.swap.max",
    "memory.events",
    "pids.current",
    "pids.max",
    "pids.events",
)


def _read_text(path: Path, operation: str) -> str:
    try:
        return path.read_text()
    except OSError as exc:
        raise DiagnosticOSError(operation, path, exc) from exc


def _stat(path: Path, operation: str) -> os.stat_result:
    try:
        return path.stat()
    except OSError as exc:
        raise DiagnosticOSError(operation, path, exc) from exc


class DiagnosticOSError(OSError):
    def __init__(self, operation: str, path: Path, cause: OSError):
        super().__init__(cause.errno, cause.strerror, str(path))
        self.operation = operation
        self.observed_path = str(path)
        self.cause_type = type(cause).__name__
        self.cause_errno = cause.errno
        self.identity_snapshot = {
            "operation": operation,
            "path": str(path),
            "errno": cause.errno,
            "strerror": cause.strerror,
            "oserror_type": type(cause).__name__,
        }


def parse_stat(text: str) -> dict[str, int]:
    return {line.split()[0]: int(line.split()[1]) for line in text.splitlines() if line.strip()}


def parent_sample(root: Path) -> dict[str, Any]:
    fields = {name: _read_text(root / name, "read_parent_" + name).strip() for name in PARENT_FILES}
    counters = parse_stat(fields["cpu.stat"])
    identity = _stat(root, "stat_parent")
    fields.update(
        cpu_usage_seconds=counters.get("usage_usec", 0) / 1_000_000,
        cpu_user_seconds=counters.get("user_usec", 0) / 1_000_000,
        cpu_system_seconds=counters.get("system_usec", 0) / 1_000_000,
        inode=identity.st_ino,
        device=identity.st_dev,
        observed_monotonic=time.monotonic(),
    )
    return fields


def leaf_sample(root: Path) -> dict[str, Any]:
    fields = {name: _read_text(root / name, "read_leaf_" + name).strip() for name in LEAF_FILES}
    counters = parse_stat(fields["cpu.stat"])
    identity = _stat(root, "stat_leaf")
    fields.update(
        cpu_usage_seconds=counters.get("usage_usec", 0) / 1_000_000,
        inode=identity.st_ino,
        device=identity.st_dev,
        observed_monotonic=time.monotonic(),
    )
    return fields


def parent_empty(reading: Mapping) -> bool:
    events = parse_stat(reading["cgroup.events"])
    return reading["pids.current"] == "0" and events.get("populated", 1) == 0


class DiagnosticWatchdog:
    """Observe leaf/parent cgroup files and retain OSError identity."""

    def __init__(self, parent: Path, leaf: Path | None = None, wall_seconds: float = 20, cpu_seconds: float = 20):
        self.parent = Path(parent)
        self.leaf = Path(leaf) if leaf is not None else None
        self.wall_seconds = wall_seconds
        self.cpu_seconds = cpu_seconds
        self.parent_inode = None
        self.parent_device = None
        self.parent_samples: list[dict[str, Any]] = []
        self.leaf_samples: list[dict[str, Any]] = []
        self.diagnostics: list[dict[str, Any]] = []
        self.error: dict[str, Any] | None = None
        self.stop = threading.Event()
        self.thread = threading.Thread(target=self.loop, daemon=True)
        self.started = time.monotonic()

    def snapshot_oserror(self, exc: DiagnosticOSError, leaf_identity: dict[str, Any] | None, parent_identity: dict[str, Any] | None) -> dict[str, Any]:
        row = {
            **exc.identity_snapshot,
            "leaf_identity": leaf_identity,
            "parent_identity": parent_identity,
            "at_monotonic": time.monotonic(),
        }
        self.diagnostics.append(row)
        return row

    def fail(self, reason: str, **extra: Any) -> None:
        if self.error is not None:
            return
        self.error = {"reason": reason, "at_monotonic": time.monotonic(), **extra}

    def _parent_identity(self) -> dict[str, Any] | None:
        if not self.parent.exists():
            return None
        try:
            st = self.parent.stat()
            return {"path": str(self.parent), "inode": st.st_ino, "device": st.st_dev}
        except OSError:
            return None

    def _leaf_identity(self) -> dict[str, Any] | None:
        if self.leaf is None or not self.leaf.exists():
            return None
        try:
            st = self.leaf.stat()
            return {"path": str(self.leaf), "inode": st.st_ino, "device": st.st_dev}
        except OSError:
            return None

    def revalidate_parent(self) -> dict[str, Any]:
        reading = parent_sample(self.parent)
        if self.parent_inode not in (None, reading["inode"]) or self.parent_device not in (None, reading["device"]):
            self.fail("parent_identity_changed", previous_inode=self.parent_inode, observed=reading)
            raise RuntimeError("Parent counter identity changed")
        if self.parent_samples and reading["cpu_usage_seconds"] < self.parent_samples[-1]["cpu_usage_seconds"]:
            self.fail("parent_cpu_regressed", observed=reading)
            raise RuntimeError("Parent CPU counter regressed")
        self.parent_inode = reading["inode"]
        self.parent_device = reading["device"]
        self.parent_samples.append(reading)
        return reading

    def handle_leaf_disappearance(self, exc: DiagnosticOSError) -> None:
        snapshot = self.snapshot_oserror(exc, self._leaf_identity(), self._parent_identity())
        if exc.cause_errno not in (errno.ENOENT, errno.ENODEV):
            self.fail("resource_observation_OSError", diagnostic=snapshot)
            raise
        if not self.parent.exists():
            self.fail("persistent_parent_disappeared", diagnostic=snapshot)
            raise RuntimeError("Parent disappeared with leaf")
        reading = self.revalidate_parent()
        if not parent_empty(reading):
            self.fail("resource_observation_OSError", diagnostic=snapshot, parent=reading)
            raise exc
        snapshot["benign_leaf_disappearance_revalidated"] = True
        snapshot["parent_empty"] = True
        snapshot["parent_identity_stable"] = True
        snapshot["cpu_monotonic"] = True

    def check(self) -> None:
        if time.monotonic() - self.started >= self.wall_seconds:
            self.fail("whole_cell_wall_budget")
            return
        try:
            if self.parent.exists():
                reading = self.revalidate_parent()
                events = parse_stat(reading["memory.events"])
                if reading["cpu_usage_seconds"] >= self.cpu_seconds:
                    self.fail("whole_group_cpu_budget")
                elif any(events.get(key, 0) for key in ("oom", "oom_kill", "max")):
                    self.fail("memory_limit_event")
            elif self.parent_inode is not None:
                self.fail("persistent_parent_disappeared")
            if self.leaf is not None and self.leaf.exists():
                self.leaf_samples.append(leaf_sample(self.leaf))
        except DiagnosticOSError as exc:
            if exc.operation.startswith("read_leaf_") or exc.operation == "stat_leaf":
                self.handle_leaf_disappearance(exc)
            else:
                snapshot = self.snapshot_oserror(exc, self._leaf_identity(), self._parent_identity())
                self.fail("resource_observation_OSError", diagnostic=snapshot)
                raise

    def loop(self) -> None:
        while not self.stop.is_set() and self.error is None:
            self.check()
            self.stop.wait(0.02)

    def finish(self) -> None:
        self.stop.set()
        if self.thread.is_alive():
            self.thread.join(timeout=6)


def write_cgroup_tree(root: Path, *, usage_usec: int = 1000, populated: int = 1, pids: int = 1) -> None:
    root.mkdir(parents=True, exist_ok=True)
    (root / "cpu.stat").write_text(f"usage_usec {usage_usec}\nuser_usec {usage_usec}\nsystem_usec 0\n")
    (root / "cpu.max").write_text("100000 100000\n")
    (root / "cpuset.cpus.effective").write_text("0\n")
    (root / "memory.current").write_text("4096\n")
    (root / "memory.peak").write_text("4096\n")
    (root / "memory.max").write_text("2147483648\n")
    (root / "memory.swap.max").write_text("0\n")
    (root / "memory.events").write_text("low 0\nhigh 0\nmax 0\noom 0\noom_kill 0\n")
    (root / "pids.current").write_text(f"{pids}\n")
    (root / "pids.max").write_text("16\n")
    (root / "pids.events").write_text("max 0\n")
    (root / "cgroup.events").write_text(f"populated {populated}\nfrozen 0\n")


def qualify(output: Path) -> dict[str, Any]:
    import shutil

    from preparation.study_common import load_json, paper_root, sha_file, write_json

    output = Path(output)
    if output.exists():
        shutil.rmtree(output)
    output.mkdir(parents=True, exist_ok=True)
    historical = (
        paper_root()
        / "papers/completion/law_to_action/benchmark/generated_code_development/development_qualification_v2/full_repair/iteration-01/cell/host"
    )
    historical_resources = load_json(historical / "resources.json")
    historical_result = load_json(historical / "result.json")
    historical_reconciliation = load_json(
        paper_root()
        / "papers/completion/law_to_action/benchmark/generated_code_development/development_qualification_v2/reconciliation.json"
    )
    historical_report = {
        "schema": "la032-historical-watchdog-investigation/v1",
        "historical_receipt_upgraded": False,
        "historical_status_preserved": historical_reconciliation["status"],
        "reason": historical_resources["decision"]["reason"],
        "errno_proven": False,
        "operation_proven": False,
        "path_proven": False,
        "cause_proven": False,
        "whole_group_termination_proven": historical_result.get("termination_proven") is True,
        "cleanup_proven": historical_result.get("cleanup_proven") is True,
        "resources_sha256": sha_file(historical / "resources.json"),
        "result_sha256": sha_file(historical / "result.json"),
        "reconciliation_sha256": sha_file(
            paper_root()
            / "papers/completion/law_to_action/benchmark/generated_code_development/development_qualification_v2/reconciliation.json"
        ),
        "note": "The v2 watchdog classified an OSError without retaining operation/path/errno. This investigation does not change that failed admission.",
    }
    write_json(output / "historical_v2_investigation.json", historical_report)

    workspace = output / "synthetic_cgroup"
    parent = workspace / "parent"
    leaf = parent / "leaf"
    write_cgroup_tree(parent, usage_usec=2000, populated=1, pids=1)
    write_cgroup_tree(leaf, usage_usec=1500, populated=1, pids=1)
    watcher = DiagnosticWatchdog(parent, leaf)
    watcher.check()
    (leaf / "cpu.stat").unlink()
    captured = None
    try:
        watcher.check()
    except DiagnosticOSError as exc:
        captured = exc.identity_snapshot
        watcher.fail("resource_observation_OSError", diagnostic=watcher.diagnostics[-1])
    oserror_probe = {
        "schema": "la032-watchdog-oserror-probe/v1",
        "broad_oserror_suppressed": False,
        "captured": captured,
        "diagnostics": watcher.diagnostics,
        "error": watcher.error,
        "leaf_samples": watcher.leaf_samples,
        "parent_samples": watcher.parent_samples,
    }
    write_json(output / "oserror_probe.json", oserror_probe)

    workspace2 = output / "benign_cgroup"
    parent2 = workspace2 / "parent"
    leaf2 = parent2 / "leaf"
    write_cgroup_tree(parent2, usage_usec=3000, populated=0, pids=0)
    write_cgroup_tree(leaf2, usage_usec=2500, populated=0, pids=0)
    watcher2 = DiagnosticWatchdog(parent2, leaf2)
    watcher2.check()
    first_inode = watcher2.parent_inode
    first_cpu = watcher2.parent_samples[-1]["cpu_usage_seconds"]
    for child in list(leaf2.iterdir()):
        child.unlink()
    leaf2.rmdir()
    watcher2.check()
    benign = {
        "schema": "la032-watchdog-benign-disappearance/v1",
        "parent_identity_stable": watcher2.parent_inode == first_inode,
        "cpu_monotonic": watcher2.parent_samples[-1]["cpu_usage_seconds"] >= first_cpu,
        "parent_empty": parent_empty(watcher2.parent_samples[-1]),
        "error": watcher2.error,
        "diagnostics": watcher2.diagnostics,
        "retained_parent_accounting": True,
        "whole_group_exit_required": True,
    }
    write_json(output / "benign_disappearance.json", benign)

    workspace3 = output / "parent_loss"
    parent3 = workspace3 / "parent"
    write_cgroup_tree(parent3, usage_usec=1000, populated=0, pids=0)
    watcher3 = DiagnosticWatchdog(parent3, None)
    watcher3.check()
    for child in list(parent3.iterdir()):
        child.unlink()
    parent3.rmdir()
    watcher3.check()
    parent_loss = {
        "schema": "la032-watchdog-parent-loss/v1",
        "error": watcher3.error,
        "parent_accounting_unknown_without_parent": True,
        "broad_suppression": False,
    }
    write_json(output / "parent_loss.json", parent_loss)

    for leftover in (workspace, workspace2, workspace3):
        if leftover.exists():
            shutil.rmtree(leftover)

    report = {
        "schema": "la032-watchdog-diagnostic-qualification/v1",
        "status": "PASS",
        "historical_receipt_upgraded": False,
        "oserror_errno_retained": captured is not None and captured.get("errno") == errno.ENOENT,
        "oserror_path_retained": captured is not None and captured.get("path", "").endswith("cpu.stat"),
        "oserror_operation_retained": captured is not None and captured.get("operation") == "read_leaf_cpu.stat",
        "benign_revalidation": benign["parent_identity_stable"] and benign["cpu_monotonic"] and benign["parent_empty"] and benign["error"] is None,
        "parent_loss_not_suppressed": parent_loss["error"] is not None,
        "broad_oserror_suppressed": False,
    }
    if not all(report[k] is True for k in ("oserror_errno_retained", "oserror_path_retained", "oserror_operation_retained", "benign_revalidation", "parent_loss_not_suppressed")):
        report["status"] = "FAIL"
        raise RuntimeError("Watchdog diagnostic qualification failed: " + json.dumps(report))
    write_json(output / "qualification.json", report)
    return report
