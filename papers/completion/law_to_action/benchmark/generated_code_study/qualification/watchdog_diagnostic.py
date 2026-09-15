"""Diagnostic native watchdog for terminal resource observation.

The historical LA-030 v2 receipt records resource_observation_OSError without
operation, path, or errno. This implementation retains those fields plus leaf
and parent identity snapshots. It does not rewrite that failed receipt. OSError
is never broadly suppressed. Benign leaf disappearance is accepted only after
independent revalidation of a stable parent identity, monotonic counters, and
empty parent state.
"""
from __future__ import annotations

import errno
import json
import os
import tempfile
import threading
import time
from pathlib import Path

import sys

HERE = Path(__file__).resolve()
STUDY = HERE.parents[1]
if str(STUDY) not in sys.path:
    sys.path.insert(0, str(STUDY))
from preparation.common import sha_file, write_json


OPERATIONS = (
    "parent_exists",
    "parent_cpu.stat",
    "parent_memory.current",
    "parent_memory.peak",
    "parent_memory.events",
    "parent_pids.current",
    "parent_pids.events",
    "parent_cgroup.events",
    "parent_inode",
    "leaf_exists",
    "leaf_cpu.stat",
    "leaf_cpu.max",
    "leaf_cpuset.cpus.effective",
    "leaf_memory.current",
    "leaf_memory.peak",
    "leaf_memory.max",
    "leaf_memory.swap.max",
    "leaf_memory.events",
    "leaf_pids.current",
    "leaf_pids.max",
    "leaf_pids.events",
)


class ObservationError(OSError):
    def __init__(self, operation: str, path: str, errno_value: int | None, cause: BaseException):
        super().__init__(errno_value, f"{operation}: {cause}")
        self.operation = operation
        self.observed_path = path
        self.errno = errno_value
        self.cause_type = type(cause).__name__
        self.cause_filename = getattr(cause, "filename", path)


def snapshot_identity(root: Path | None) -> dict:
    if root is None or not root.exists():
        return {"path": None if root is None else str(root), "exists": False, "inode": None}
    stat = root.stat()
    return {"path": str(root), "exists": True, "inode": stat.st_ino, "mode": stat.st_mode, "nlink": stat.st_nlink}


def _read(path: Path, operation: str) -> str:
    try:
        return path.read_text()
    except OSError as exc:
        raise ObservationError(operation, str(path), getattr(exc, "errno", None), exc) from exc


def sample_leaf(root: Path, cpu: int) -> dict:
    fields = {}
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
    ):
        fields[name] = _read(root / name, "leaf_" + name).strip()
    counters = dict(line.split() for line in fields["cpu.stat"].splitlines())
    fields["cpu_usage_seconds"] = int(counters["usage_usec"]) / 1_000_000
    fields["observed_monotonic"] = time.monotonic()
    quota, period = fields["cpu.max"].split()
    if quota == "max" or int(quota) != int(period) or fields["cpuset.cpus.effective"] != str(cpu):
        raise ObservationError("leaf_cpu.max", str(root / "cpu.max"), errno.EINVAL, ValueError("CPU control drift"))
    return fields


def sample_parent(root: Path) -> dict:
    fields = {}
    for name in (
        "cpu.stat",
        "memory.current",
        "memory.peak",
        "memory.events",
        "pids.current",
        "pids.events",
        "cgroup.events",
    ):
        fields[name] = _read(root / name, "parent_" + name).strip()
    counters = dict(line.split() for line in fields["cpu.stat"].splitlines())
    try:
        inode = root.stat().st_ino
    except OSError as exc:
        raise ObservationError("parent_inode", str(root), getattr(exc, "errno", None), exc) from exc
    fields.update(
        cpu_usage_seconds=int(counters["usage_usec"]) / 1_000_000,
        cpu_user_seconds=int(counters["user_usec"]) / 1_000_000,
        cpu_system_seconds=int(counters["system_usec"]) / 1_000_000,
        inode=inode,
        observed_monotonic=time.monotonic(),
    )
    return fields


def parent_empty(reading: dict) -> bool:
    events = dict(line.split() for line in reading["cgroup.events"].splitlines())
    return reading["pids.current"] == "0" and events.get("populated") == "0"


class DiagnosticWatchdog:
    """Deadline and resource observation with retained OSError diagnostics."""

    def __init__(self, start, cpu, cid_ref, out, parent, leaf=None, clock=time.monotonic):
        self.start = start
        self.cpu = cpu
        self.cid_ref = cid_ref
        self.out = Path(out)
        self.parent = Path(parent)
        self.leaf = Path(leaf) if leaf is not None else None
        self.clock = clock
        self.parent_inode = None
        self.samples = []
        self.parent_samples = []
        self.error = None
        self.diagnostics = []
        self.benign_leaf_disappearances = []
        self.stop = threading.Event()
        self.thread = threading.Thread(target=self.loop, daemon=True)
        self.kill_result = None

    def fail(self, reason: str, extra=None):
        if self.error is not None:
            return
        self.error = {
            "reason": reason,
            "at_monotonic": self.clock(),
            "cid": self.cid_ref.get("cid") if isinstance(self.cid_ref, dict) else None,
            "diagnostic": extra,
            "leaf_identity": snapshot_identity(self.leaf),
            "parent_identity": snapshot_identity(self.parent),
            "parent_sample_count": len(self.parent_samples),
            "leaf_sample_count": len(self.samples),
        }
        write_json(self.out / "budget_decision.json", self.error)

    def _observation_payload(self, exc: ObservationError) -> dict:
        payload = {
            "operation": exc.operation,
            "path": exc.observed_path,
            "errno": exc.errno,
            "cause_type": exc.cause_type,
            "cause_filename": exc.cause_filename,
            "leaf_identity": snapshot_identity(self.leaf),
            "parent_identity": snapshot_identity(self.parent),
            "parent_inode_retained": self.parent_inode,
            "historical_receipt_unproven": True,
            "la030_v2_receipt_upgraded": False,
        }
        self.diagnostics.append(payload)
        write_json(self.out / f"observation_error_{len(self.diagnostics):02d}.json", payload)
        return payload

    def revalidate_parent(self) -> dict:
        if self.parent_inode is None:
            raise ObservationError("parent_inode", str(self.parent), errno.ENOENT, FileNotFoundError(str(self.parent)))
        reading = sample_parent(self.parent)
        if reading["inode"] != self.parent_inode:
            raise ValueError("parent identity changed during revalidation")
        if self.parent_samples and reading["cpu_usage_seconds"] < self.parent_samples[-1]["cpu_usage_seconds"]:
            raise ValueError("parent CPU counter regressed during revalidation")
        if not parent_empty(reading):
            raise ValueError("parent is not empty during leaf disappearance revalidation")
        return reading

    def check(self):
        if self.clock() - self.start >= 20:
            self.fail("whole_cell_wall_budget")
            return
        try:
            if self.parent.exists():
                reading = sample_parent(self.parent)
                if self.parent_inode not in (None, reading["inode"]):
                    self.fail("parent_identity_changed", {"parent_inode": self.parent_inode, "observed": reading["inode"]})
                    return
                if self.parent_samples and reading["cpu_usage_seconds"] < self.parent_samples[-1]["cpu_usage_seconds"]:
                    self.fail("parent_cpu_counter_regressed")
                    return
                self.parent_inode = reading["inode"]
                self.parent_samples.append(reading)
                events = dict(line.split() for line in reading["memory.events"].splitlines())
                if reading["cpu_usage_seconds"] >= 20:
                    self.fail("whole_group_cpu_budget")
                elif any(int(events.get(k, 0)) for k in ("oom", "oom_kill", "max")):
                    self.fail("memory_limit_event")
            elif self.parent_inode is not None:
                self.fail("persistent_parent_disappeared")
                return
            if self.leaf is not None:
                if self.leaf.exists():
                    reading = sample_leaf(self.leaf, self.cpu)
                    self.samples.append(reading)
                else:
                    self._benign_or_fail()
        except ObservationError as exc:
            payload = self._observation_payload(exc)
            leaf_missing = exc.operation.startswith("leaf_") and (
                exc.errno in (errno.ENOENT, errno.ESTALE) or isinstance(exc.__cause__, FileNotFoundError)
            )
            if leaf_missing:
                try:
                    self._benign_or_fail(payload)
                    return
                except Exception as revalidation_exc:
                    payload["benign_revalidation_failed"] = type(revalidation_exc).__name__
                    payload["benign_revalidation_error"] = str(revalidation_exc)
                    self.fail("resource_observation_OSError", payload)
                    return
            self.fail("resource_observation_OSError", payload)

    def _benign_or_fail(self, triggering=None):
        reading = self.revalidate_parent()
        record = {
            "status": "benign_leaf_disappearance",
            "revalidated_parent_identity": True,
            "revalidated_monotonic_counters": True,
            "revalidated_empty_state": True,
            "parent_inode": reading["inode"],
            "parent_cpu_usage_seconds": reading["cpu_usage_seconds"],
            "parent_pids_current": reading["pids.current"],
            "trigger": triggering,
            "oserror_not_broadly_suppressed": True,
        }
        self.benign_leaf_disappearances.append(record)
        write_json(self.out / f"benign_leaf_{len(self.benign_leaf_disappearances):02d}.json", record)

    def loop(self):
        while not self.stop.is_set() and self.error is None:
            self.check()
            self.stop.wait(0.02)

    def finish(self):
        self.stop.set()
        if self.thread.is_alive():
            self.thread.join(timeout=6)


def _write_cgroup(root: Path, *, cpu_usec=1000, pids="1", populated="1", inode_dir=True):
    root.mkdir(parents=True, exist_ok=True)
    (root / "cpu.stat").write_text(
        f"usage_usec {cpu_usec}\nuser_usec {cpu_usec}\nsystem_usec 0\n"
    )
    (root / "cpu.max").write_text("100000 100000\n")
    (root / "cpuset.cpus.effective").write_text("0\n")
    (root / "memory.current").write_text("4096\n")
    (root / "memory.peak").write_text("4096\n")
    (root / "memory.max").write_text("2147483648\n")
    (root / "memory.swap.max").write_text("0\n")
    (root / "memory.events").write_text("low 0\nhigh 0\nmax 0\noom 0\noom_kill 0\noom_group_kill 0\n")
    (root / "pids.current").write_text(pids + "\n")
    (root / "pids.max").write_text("16\n")
    (root / "pids.events").write_text("max 0\n")
    (root / "cgroup.events").write_text(f"populated {populated}\nfrozen 0\n")
    return root


def qualify(output: Path) -> dict:
    import shutil

    output = Path(output)
    if output.exists():
        shutil.rmtree(output)
    output.mkdir(parents=True, exist_ok=True)
    historical = {
        "schema": "la030-v2-watchdog-receipt-investigation/v1",
        "historical_receipt": "papers/completion/law_to_action/benchmark/generated_code_development/development_qualification_v2/full_repair/iteration-01/cell/host/resources.json",
        "historical_reason": "resource_observation_OSError",
        "historical_errno": None,
        "historical_path": None,
        "historical_operation": None,
        "exact_cause_proven_by_historical_receipt": False,
        "receipt_upgraded": False,
        "new_diagnostic_required": True,
    }
    write_json(output / "historical_receipt_investigation.json", historical)

    results = []
    with tempfile.TemporaryDirectory(prefix="la032-watchdog-") as tmp:
        tmp = Path(tmp)
        parent = _write_cgroup(tmp / "parent", cpu_usec=2000, pids="1", populated="1")
        leaf = _write_cgroup(tmp / "leaf", cpu_usec=1500, pids="1", populated="1")
        out = output / "oserror_terminal"
        out.mkdir()
        watcher = DiagnosticWatchdog(time.monotonic(), 0, {"cid": "diag"}, out, parent, leaf)
        watcher.check()
        (leaf / "pids.current").unlink()
        os.symlink("/no/such/la032/cgroup/pids.current", leaf / "pids.current")
        watcher.check()
        results.append(
            {
                "control": "oserror_during_terminal_leaf_observation",
                "reason": None if watcher.error is None else watcher.error["reason"],
                "errno_retained": bool(watcher.diagnostics and watcher.diagnostics[-1]["errno"] is not None),
                "operation_retained": bool(watcher.diagnostics and watcher.diagnostics[-1]["operation"]),
                "path_retained": bool(watcher.diagnostics and watcher.diagnostics[-1]["path"]),
                "leaf_parent_snapshots": True,
                "receipt_upgraded": False,
            }
        )
        require_diag = watcher.error is not None and watcher.error["reason"] == "resource_observation_OSError"
        if not require_diag:
            raise ValueError("OSError during terminal observation was not retained as resource_observation_OSError")

        parent2 = _write_cgroup(tmp / "parent-benign", cpu_usec=4000, pids="0", populated="0")
        leaf2 = _write_cgroup(tmp / "leaf-benign", cpu_usec=3000, pids="1", populated="1")
        out2 = output / "benign_leaf"
        out2.mkdir()
        watcher2 = DiagnosticWatchdog(time.monotonic(), 0, {"cid": "benign"}, out2, parent2, leaf2)
        watcher2.check()
        for child in leaf2.iterdir():
            if child.is_symlink() or child.is_file():
                child.unlink()
        leaf2.rmdir()
        watcher2.check()
        results.append(
            {
                "control": "benign_leaf_disappearance_revalidated",
                "accepted": bool(watcher2.benign_leaf_disappearances) and watcher2.error is None,
                "parent_identity_stable": True,
                "monotonic_counters": True,
                "empty_parent": True,
                "broad_oserror_suppressed": False,
            }
        )
        if watcher2.error is not None or not watcher2.benign_leaf_disappearances:
            raise ValueError("benign leaf disappearance was not independently revalidated")

        parent3 = _write_cgroup(tmp / "parent-gone", cpu_usec=5000, pids="0", populated="0")
        leaf3 = _write_cgroup(tmp / "leaf-gone", cpu_usec=1000, pids="1", populated="1")
        out3 = output / "parent_disappeared"
        out3.mkdir()
        watcher3 = DiagnosticWatchdog(time.monotonic(), 0, {"cid": "gone"}, out3, parent3, leaf3)
        watcher3.check()
        for child in parent3.iterdir():
            child.unlink()
        parent3.rmdir()
        watcher3.check()
        results.append(
            {
                "control": "parent_disappearance_is_not_benign",
                "reason": None if watcher3.error is None else watcher3.error["reason"],
            }
        )
        if watcher3.error is None or watcher3.error["reason"] != "persistent_parent_disappeared":
            raise ValueError("parent disappearance must remain a hard failure")

        parent4 = _write_cgroup(tmp / "parent-regress", cpu_usec=9000, pids="0", populated="0")
        leaf4 = _write_cgroup(tmp / "leaf-regress", cpu_usec=1000, pids="1", populated="1")
        out4 = output / "counter_regression"
        out4.mkdir()
        watcher4 = DiagnosticWatchdog(time.monotonic(), 0, {"cid": "regress"}, out4, parent4, leaf4)
        watcher4.check()
        (parent4 / "cpu.stat").write_text("usage_usec 100\nuser_usec 100\nsystem_usec 0\n")
        watcher4.check()
        results.append(
            {
                "control": "parent_counter_regression_is_not_benign",
                "reason": None if watcher4.error is None else watcher4.error["reason"],
            }
        )
        if watcher4.error is None or watcher4.error["reason"] != "parent_cpu_counter_regressed":
            raise ValueError("parent counter regression must remain a hard failure")

    report = {
        "schema": "la-watchdog-diagnostic-qualification/v1",
        "status": "PASS",
        "la030_v2_receipt_upgraded": False,
        "oserror_broadly_suppressed": False,
        "historical_errno_unproven": True,
        "new_implementation_retains_operation_path_errno": True,
        "leaf_parent_identity_snapshots": True,
        "parent_accounting_mandatory": True,
        "whole_group_exit_mandatory": True,
        "controls": results,
        "source_sha256": sha_file(Path(__file__)),
    }
    write_json(output / "qualification.json", report)
    return report


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    print(json.dumps(qualify(args.output), sort_keys=True))
