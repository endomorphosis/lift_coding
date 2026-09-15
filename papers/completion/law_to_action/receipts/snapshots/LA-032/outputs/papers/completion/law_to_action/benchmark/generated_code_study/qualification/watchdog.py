#!/usr/bin/python3.12
"""Diagnostic terminal-observation watchdog.

The LA-030 v2 receipt records resource_observation_OSError without errno, path,
or operation. This implementation retains those fields plus leaf/parent identity
snapshots. It does not suppress OSError broadly and does not upgrade the failed
v2 receipt. Benign leaf disappearance is accepted only after revalidating a
stable parent identity, monotonic counters, and empty parent state.
"""
from __future__ import annotations

import os
import time
from pathlib import Path
from typing import Any, Callable

import sys
from pathlib import Path as _Path

_STUDY = _Path(__file__).resolve().parents[1]
for _path in (_STUDY, _STUDY / "preparation"):
    _text = str(_path)
    if _text not in sys.path:
        sys.path.insert(0, _text)
from study_common import write_json


def _identity(path: Path) -> dict[str, Any]:
    try:
        st = path.stat()
        return {
            "path": str(path),
            "exists": True,
            "inode": st.st_ino,
            "mode": st.st_mode,
            "nlink": st.st_nlink,
        }
    except OSError as exc:
        return {
            "path": str(path),
            "exists": False,
            "inode": None,
            "oserror": {"errno": exc.errno, "strerror": os.strerror(exc.errno) if exc.errno is not None else None},
        }


def _read_text(path: Path, operation: str) -> str:
    try:
        return path.read_text(encoding="utf-8")
    except OSError as exc:
        raise ObservationOSError(operation, path, exc) from exc


class ObservationOSError(OSError):
    def __init__(self, operation: str, path: Path, cause: OSError):
        super().__init__(cause.errno, cause.strerror, str(path))
        self.operation = operation
        self.observed_path = Path(path)
        self.cause = cause
        self.errno = cause.errno


def parent_sample(root: Path) -> dict[str, Any]:
    fields = {
        name: _read_text(root / name, "read:" + name).strip()
        for name in (
            "cpu.stat",
            "memory.current",
            "memory.peak",
            "memory.events",
            "pids.current",
            "pids.events",
            "cgroup.events",
        )
    }
    counters = dict(line.split() for line in fields["cpu.stat"].splitlines())
    fields.update(
        cpu_usage_seconds=int(counters["usage_usec"]) / 1_000_000,
        cpu_user_seconds=int(counters["user_usec"]) / 1_000_000,
        cpu_system_seconds=int(counters["system_usec"]) / 1_000_000,
        inode=root.stat().st_ino,
        observed_monotonic=time.monotonic(),
        identity=_identity(root),
    )
    return fields


def leaf_sample(root: Path) -> dict[str, Any]:
    fields = {
        name: _read_text(root / name, "read:" + name).strip()
        for name in (
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
    }
    counters = dict(line.split() for line in fields["cpu.stat"].splitlines())
    fields.update(
        cpu_usage_seconds=int(counters["usage_usec"]) / 1_000_000,
        observed_monotonic=time.monotonic(),
        identity=_identity(root),
    )
    return fields


def parent_empty(reading: dict[str, Any]) -> bool:
    events = dict(line.split() for line in reading["cgroup.events"].splitlines())
    return reading["pids.current"] == "0" and events.get("populated") == "0"


class DiagnosticWatchdog:
    def __init__(self, parent: Path, leaf: Path | None = None):
        self.parent = Path(parent)
        self.leaf = Path(leaf) if leaf is not None else None
        self.parent_inode = None
        self.parent_samples: list[dict[str, Any]] = []
        self.leaf_samples: list[dict[str, Any]] = []
        self.diagnostics: list[dict[str, Any]] = []
        self.error: dict[str, Any] | None = None

    def _fail(self, reason: str, extra: dict[str, Any] | None = None) -> None:
        if self.error is not None:
            return
        payload = {
            "reason": reason,
            "at_monotonic": time.monotonic(),
            "parent_identity": _identity(self.parent),
            "leaf_identity": _identity(self.leaf) if self.leaf is not None else None,
        }
        if extra:
            payload.update(extra)
        self.error = payload

    def _record_oserror(self, operation: str, path: Path, exc: OSError) -> dict[str, Any]:
        record = {
            "schema": "la032-resource-observation-diagnostic/v1",
            "operation": operation,
            "path": str(path),
            "errno": exc.errno,
            "strerror": os.strerror(exc.errno) if exc.errno is not None else None,
            "exception_type": type(exc).__name__,
            "leaf_identity": _identity(self.leaf) if self.leaf is not None else None,
            "parent_identity": _identity(self.parent),
            "at_monotonic": time.monotonic(),
            "historical_v2_receipt_upgraded": False,
            "broad_oserror_suppressed": False,
        }
        self.diagnostics.append(record)
        return record

    def observe_once(self) -> None:
        try:
            if self.parent.exists():
                reading = parent_sample(self.parent)
                if self.parent_inode not in (None, reading["inode"]):
                    self._fail("parent_identity_changed", {"previous_inode": self.parent_inode, "observed": reading})
                    return
                if self.parent_samples and reading["cpu_usage_seconds"] < self.parent_samples[-1]["cpu_usage_seconds"]:
                    self._fail("parent_cpu_counter_regressed", {"observed": reading})
                    return
                self.parent_inode = reading["inode"]
                self.parent_samples.append(reading)
            elif self.parent_inode is not None:
                self._fail("persistent_parent_disappeared")
                return
            if self.leaf is not None and self.leaf.exists():
                self.leaf_samples.append(leaf_sample(self.leaf))
        except ObservationOSError as exc:
            diagnostic = self._record_oserror(exc.operation, exc.observed_path, exc)
            if self.leaf is not None and exc.observed_path.is_relative_to(self.leaf):
                accepted, reason = self._maybe_benign_leaf_disappearance(diagnostic)
                if accepted:
                    return
                self._fail("resource_observation_OSError", {"diagnostic": diagnostic, "benign_rejected": reason})
                return
            self._fail("resource_observation_OSError", {"diagnostic": diagnostic})
        except OSError as exc:
            path = Path(getattr(exc, "filename", self.leaf or self.parent) or self.parent)
            diagnostic = self._record_oserror("unclassified_oserror", path, exc)
            self._fail("resource_observation_OSError", {"diagnostic": diagnostic})

    def _maybe_benign_leaf_disappearance(self, diagnostic: dict[str, Any]) -> tuple[bool, str]:
        if diagnostic.get("errno") not in {os.errno.ENOENT if hasattr(os, "errno") else 2, 2}:
            return False, "errno_not_enoent"
        if not self.parent.exists():
            return False, "parent_missing"
        try:
            reading = parent_sample(self.parent)
        except ObservationOSError as exc:
            self._record_oserror(exc.operation, exc.observed_path, exc)
            return False, "parent_revalidation_oserror"
        if self.parent_inode not in (None, reading["inode"]):
            return False, "parent_identity_changed"
        if self.parent_samples and reading["cpu_usage_seconds"] < self.parent_samples[-1]["cpu_usage_seconds"]:
            return False, "parent_cpu_counter_regressed"
        if not parent_empty(reading):
            return False, "parent_not_empty"
        self.parent_inode = reading["inode"]
        self.parent_samples.append(reading)
        diagnostic["benign_leaf_disappearance_accepted"] = True
        diagnostic["parent_revalidated"] = {
            "identity_stable": True,
            "counters_monotonic": True,
            "empty": True,
            "inode": reading["inode"],
        }
        return True, "accepted"

    def finish(self, out: Path | None = None) -> dict[str, Any]:
        report = {
            "schema": "la032-watchdog-observation/v1",
            "error": self.error,
            "diagnostics": self.diagnostics,
            "parent_samples": self.parent_samples,
            "leaf_samples": self.leaf_samples,
            "parent_accounting_retained": bool(self.parent_samples),
            "whole_group_exit_required": True,
            "historical_v2_receipt_upgraded": False,
        }
        if out is not None:
            write_json(Path(out), report)
        return report


def _write_cgroup_fixture(root: Path, kind: str) -> Path:
    root.mkdir(parents=True, exist_ok=True)
    parent = root / "parent"
    leaf = root / "leaf"
    parent.mkdir(exist_ok=True)
    leaf.mkdir(exist_ok=True)
    for name, body in {
        "cpu.stat": "usage_usec 10\nuser_usec 8\nsystem_usec 2\n",
        "memory.current": "1",
        "memory.peak": "1",
        "memory.events": "low 0\nhigh 0\nmax 0\noom 0\noom_kill 0\noom_group_kill 0\n",
        "pids.current": "0",
        "pids.events": "max 0\n",
        "cgroup.events": "populated 0\nfrozen 0\n",
    }.items():
        (parent / name).write_text(body)
    for name, body in {
        "cpu.stat": "usage_usec 10\nuser_usec 8\nsystem_usec 2\n",
        "cpu.max": "100000 100000",
        "cpuset.cpus.effective": "0",
        "memory.current": "1",
        "memory.peak": "1",
        "memory.max": "2147483648",
        "memory.swap.max": "0",
        "memory.events": "low 0\nhigh 0\nmax 0\noom 0\noom_kill 0\noom_group_kill 0\n",
        "pids.current": "0",
        "pids.max": "16",
        "pids.events": "max 0\n",
    }.items():
        (leaf / name).write_text(body)
    return parent, leaf


def regression_tests(output: Path) -> dict[str, Any]:
    """Inject observation faults without touching the historical v2 receipt."""
    output = Path(output)
    output.mkdir(parents=True, exist_ok=True)
    results = []
    original_read = Path.read_text

    parent, leaf = _write_cgroup_fixture(output / "healthy", "healthy")
    watcher = DiagnosticWatchdog(parent, leaf)
    watcher.observe_once()
    results.append({"name": "healthy_sample", "error": watcher.error, "parent_samples": len(watcher.parent_samples)})

    parent, leaf = _write_cgroup_fixture(output / "benign", "benign")
    vanished = DiagnosticWatchdog(parent, leaf)
    vanished.observe_once()
    (leaf / "cpu.stat").unlink()

    def boom(self, *args, **kwargs):
        if self.parent == leaf and self.name == "cpu.stat":
            raise OSError(2, "No such file or directory", str(self))
        return original_read(self, *args, **kwargs)

    Path.read_text = boom  # type: ignore[method-assign]
    try:
        vanished.observe_once()
    finally:
        Path.read_text = original_read  # type: ignore[method-assign]
    results.append(
        {
            "name": "benign_leaf_enoent",
            "error": vanished.error,
            "diagnostics": vanished.diagnostics,
            "accepted": bool(vanished.diagnostics and vanished.diagnostics[-1].get("benign_leaf_disappearance_accepted")),
        }
    )

    parent, leaf = _write_cgroup_fixture(output / "identity", "identity")
    identity = DiagnosticWatchdog(parent, leaf)
    identity.observe_once()
    identity.parent_inode = identity.parent_inode + 1 if identity.parent_inode else 1
    identity.observe_once()
    results.append({"name": "parent_identity_change", "error": identity.error})

    parent, leaf = _write_cgroup_fixture(output / "ebusy", "ebusy")
    unknown = DiagnosticWatchdog(parent, leaf)
    unknown.observe_once()

    def ebusy(self, *args, **kwargs):
        if self.parent == leaf:
            raise OSError(16, "Device or resource busy", str(self))
        return original_read(self, *args, **kwargs)

    Path.read_text = ebusy  # type: ignore[method-assign]
    try:
        unknown.observe_once()
    finally:
        Path.read_text = original_read  # type: ignore[method-assign]
    results.append(
        {
            "name": "ebusy_not_suppressed",
            "error": unknown.error,
            "diagnostics": unknown.diagnostics,
            "errno": unknown.diagnostics[-1]["errno"] if unknown.diagnostics else None,
        }
    )

    report = {
        "schema": "la032-watchdog-regression/v1",
        "status": "PASS",
        "historical_v2_receipt_upgraded": False,
        "broad_oserror_suppressed": False,
        "unproven_historical_errno_path_cause": True,
        "results": results,
        "invariants": {
            "benign_requires_stable_parent_monotonic_empty": True,
            "parent_accounting_mandatory": True,
            "whole_group_exit_mandatory": True,
        },
    }
    if not results[1]["accepted"] or results[1]["error"] is not None:
        report["status"] = "FAIL"
        report["reason"] = "benign leaf disappearance was not independently revalidated"
    if results[2]["error"] is None or results[2]["error"]["reason"] != "parent_identity_changed":
        report["status"] = "FAIL"
        report["reason"] = "parent identity change was not retained as failure"
    if results[3]["errno"] != 16 or results[3]["error"] is None:
        report["status"] = "FAIL"
        report["reason"] = "non-ENOENT OSError was suppressed or missing errno"
    write_json(output / "watchdog_regression.json", report)
    import shutil
    for leftover in output.iterdir():
        if leftover.name == "watchdog_regression.json":
            continue
        if leftover.is_dir():
            shutil.rmtree(leftover)
        else:
            leftover.unlink()
    return report
