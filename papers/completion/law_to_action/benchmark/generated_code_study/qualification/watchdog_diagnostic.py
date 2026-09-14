#!/usr/bin/python3.12
"""Diagnose native watchdog OSError without upgrading the failed LA-030 v2 receipt."""
from __future__ import annotations

import errno
import json
import os
import stat
import time
from pathlib import Path
from typing import Any

HISTORICAL_V2 = Path(__file__).resolve().parents[2] / "generated_code_development/development_qualification_v2/full_repair/iteration-01/cell/host/resources.json"


def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n")


class DiagnosticSampleError(RuntimeError):
    def __init__(self, operation: str, path: Path, err: OSError, leaf: dict[str, Any], parent: dict[str, Any]):
        super().__init__(f"{operation} {path}: {err}")
        self.operation = operation
        self.path = str(path)
        self.errno = err.errno
        self.strerror = err.strerror
        self.exception_type = type(err).__name__
        self.leaf = leaf
        self.parent = parent

    def as_dict(self) -> dict[str, Any]:
        return {
            "operation": self.operation,
            "path": self.path,
            "errno": self.errno,
            "strerror": self.strerror,
            "exception_type": self.exception_type,
            "leaf_identity": self.leaf,
            "parent_identity": self.parent,
        }


def identity_snapshot(path: Path) -> dict[str, Any]:
    try:
        st = path.stat()
        return {
            "path": str(path),
            "exists": True,
            "inode": st.st_ino,
            "mode": stat.S_IMODE(st.st_mode),
            "nlink": st.st_nlink,
        }
    except OSError as exc:
        return {"path": str(path), "exists": False, "inode": None, "errno": exc.errno, "strerror": exc.strerror}


def read_text(path: Path, operation: str, leaf: dict[str, Any], parent: dict[str, Any]) -> str:
    try:
        return path.read_text()
    except OSError as exc:
        raise DiagnosticSampleError(operation, path, exc, leaf, parent) from exc


def parse_parent(fields: dict[str, str], inode: int) -> dict[str, Any]:
    counters = dict(line.split() for line in fields["cpu.stat"].splitlines())
    return {
        "cpu_usage_seconds": int(counters["usage_usec"]) / 1_000_000,
        "inode": inode,
        "pids.current": fields["pids.current"].strip(),
        "cgroup.events": fields["cgroup.events"],
        "memory.current": fields["memory.current"].strip(),
    }


def parent_empty(reading: dict[str, Any]) -> bool:
    events = dict(line.split() for line in reading["cgroup.events"].splitlines())
    return reading["pids.current"] == "0" and events.get("populated") == "0"


class DiagnosticWatchdog:
    """Retain operation/path/errno. Do not suppress OSError broadly."""

    def __init__(self, leaf: Path, parent: Path):
        self.leaf = leaf
        self.parent = parent
        self.parent_inode = None
        self.parent_samples: list[dict[str, Any]] = []
        self.leaf_samples: list[dict[str, Any]] = []
        self.error = None
        self.diagnostics: list[dict[str, Any]] = []

    def fail(self, reason: str, diagnostic: dict[str, Any] | None = None) -> None:
        if self.error is not None:
            return
        self.error = {"reason": reason, "diagnostic": diagnostic, "at_monotonic": time.monotonic()}

    def observe(self) -> None:
        leaf_id = identity_snapshot(self.leaf)
        parent_id = identity_snapshot(self.parent)
        try:
            if not self.parent.exists():
                if self.parent_inode is not None:
                    self.fail("persistent_parent_disappeared", {"parent": parent_id, "leaf": leaf_id})
                return
            fields = {
                name: read_text(self.parent / name, "parent_read", leaf_id, parent_id)
                for name in ("cpu.stat", "memory.current", "pids.current", "cgroup.events")
            }
            reading = parse_parent(fields, parent_id["inode"])
            if self.parent_inode not in (None, reading["inode"]):
                self.fail("parent_identity_changed", {"expected_inode": self.parent_inode, "observed": reading, "leaf": leaf_id})
                return
            if self.parent_samples and reading["cpu_usage_seconds"] < self.parent_samples[-1]["cpu_usage_seconds"]:
                self.fail("parent_counter_regressed", {"previous": self.parent_samples[-1], "observed": reading})
                return
            self.parent_inode = reading["inode"]
            self.parent_samples.append(reading)
            if self.leaf.exists():
                cpu = read_text(self.leaf / "cpu.stat", "leaf_read", leaf_id, parent_id)
                self.leaf_samples.append({"cpu.stat": cpu, "identity": leaf_id})
        except DiagnosticSampleError as exc:
            payload = exc.as_dict()
            self.diagnostics.append(payload)
            benign = self._benign_leaf_disappearance(exc, parent_id)
            if benign:
                payload["benign_leaf_disappearance"] = True
                payload["revalidation"] = benign
                return
            self.fail("resource_observation_" + exc.exception_type, payload)

    def _benign_leaf_disappearance(self, exc: DiagnosticSampleError, parent_id: dict[str, Any]) -> dict[str, Any] | None:
        if exc.errno not in {errno.ENOENT, errno.ENODEV}:
            return None
        if Path(exc.path) != self.leaf and not str(exc.path).startswith(str(self.leaf) + os.sep):
            return None
        if self.parent_inode is None or parent_id.get("inode") != self.parent_inode:
            return None
        try:
            fields = {
                name: (self.parent / name).read_text()
                for name in ("cpu.stat", "memory.current", "pids.current", "cgroup.events")
            }
        except OSError:
            return None
        reading = parse_parent(fields, parent_id["inode"])
        if self.parent_samples and reading["cpu_usage_seconds"] < self.parent_samples[-1]["cpu_usage_seconds"]:
            return None
        if not parent_empty(reading):
            return None
        self.parent_samples.append(reading)
        return {
            "stable_parent_identity": True,
            "monotonic_parent_counters": True,
            "empty_parent_state": True,
            "parent": reading,
        }


def _write_cgroup(root: Path, cpu_usec: int, pids: str, populated: str) -> None:
    root.mkdir(parents=True, exist_ok=True)
    (root / "cpu.stat").write_text(f"usage_usec {cpu_usec}\nuser_usec {cpu_usec}\nsystem_usec 0\n")
    (root / "memory.current").write_text("4096\n")
    (root / "pids.current").write_text(pids + "\n")
    (root / "cgroup.events").write_text(f"populated {populated}\nfrozen 0\n")


def run_probes(output: Path) -> dict[str, Any]:
    if output.exists():
        import shutil
        shutil.rmtree(output)
    output.mkdir(parents=True, exist_ok=True)
    historical = json.loads(HISTORICAL_V2.read_text())
    historical_report = {
        "path": str(HISTORICAL_V2),
        "reason": historical["decision"]["reason"],
        "errno_retained_in_historical_receipt": False,
        "operation_retained_in_historical_receipt": False,
        "path_retained_in_historical_receipt": False,
        "status": "FAILED_RETAINED_NOT_UPGRADED",
        "whole_group_termination_proven_historically": True,
    }
    write_json(output / "historical_v2_receipt.json", historical_report)

    base = output / "cgroups"
    parent = base / "parent"
    leaf = parent / "leaf"
    _write_cgroup(parent, 1000, "1", "1")
    _write_cgroup(leaf, 500, "1", "1")
    watcher = DiagnosticWatchdog(leaf, parent)
    watcher.observe()
    (leaf / "cpu.stat").unlink()
    _write_cgroup(parent, 1500, "0", "0")
    watcher.observe()
    benign = {
        "error": watcher.error,
        "diagnostics": watcher.diagnostics,
        "parent_samples": watcher.parent_samples,
        "status": "PASS" if watcher.error is None and watcher.diagnostics else "FAIL",
    }
    write_json(output / "benign_leaf_disappearance.json", benign)

    parent2 = base / "parent2"
    leaf2 = parent2 / "leaf"
    _write_cgroup(parent2, 1000, "1", "1")
    _write_cgroup(leaf2, 500, "1", "1")
    watcher2 = DiagnosticWatchdog(leaf2, parent2)
    watcher2.observe()
    (leaf2 / "cpu.stat").write_text("")
    os.chmod(leaf2 / "cpu.stat", 0)
    try:
        os.chmod(leaf2, 0)
        watcher2.observe()
    finally:
        os.chmod(leaf2, 0o755)
        os.chmod(leaf2 / "cpu.stat", 0o644)
    non_benign = {
        "error": watcher2.error,
        "diagnostics": watcher2.diagnostics,
        "status": "PASS" if watcher2.error and watcher2.diagnostics else "FAIL",
    }
    write_json(output / "nonbenign_oserror_retained.json", non_benign)

    parent3 = base / "parent3"
    leaf3 = parent3 / "leaf"
    _write_cgroup(parent3, 1000, "1", "1")
    _write_cgroup(leaf3, 500, "1", "1")
    watcher3 = DiagnosticWatchdog(leaf3, parent3)
    watcher3.observe()
    _write_cgroup(parent3, 900, "0", "0")
    (leaf3 / "cpu.stat").unlink()
    watcher3.observe()
    regression = {
        "error": watcher3.error,
        "status": "PASS" if watcher3.error and watcher3.error["reason"] == "parent_counter_regressed" else "FAIL",
    }
    write_json(output / "parent_counter_regression.json", regression)

    report = {
        "schema": "la-watchdog-oserror-diagnostic/v1",
        "status": "PASS" if benign["status"] == non_benign["status"] == regression["status"] == "PASS" else "FAIL",
        "historical_v2_upgraded": False,
        "oserror_suppressed_broadly": False,
        "parent_accounting_mandatory": True,
        "whole_group_exit_mandatory": True,
        "benign_requires_stable_parent_monotonic_counters_empty_state": True,
        "historical": historical_report,
        "probes": {
            "benign_leaf_disappearance": benign["status"],
            "nonbenign_oserror_retained": non_benign["status"],
            "parent_counter_regression": regression["status"],
        },
    }
    write_json(output / "qualification.json", report)
    return report


if __name__ == "__main__":
    print(json.dumps(run_probes(Path(__file__).resolve().parent / "watchdog"), sort_keys=True))
