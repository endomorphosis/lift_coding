"""Diagnostic attempt watchdog with retained OSError identity.

The historical LA-030 v2 receipt records resource_observation_OSError without
operation, path, or errno. This implementation retains those fields plus leaf
and parent identity snapshots. It does not suppress OSError broadly and does
not rewrite the failed v2 receipt.
"""
from __future__ import annotations

import errno
import os
import threading
import time
from pathlib import Path

BENIGN_OSERROR_TYPES = (FileNotFoundError, ProcessLookupError)


def _text(path: Path) -> str:
    return path.read_text()


def sample_fields(root: Path, names: tuple[str, ...]) -> dict:
    fields = {}
    for name in names:
        path = root / name
        fields[name] = _text(path).strip()
    return fields


def parse_stat_map(text: str) -> dict[str, str]:
    return dict(line.split() for line in text.splitlines() if line.strip())


def parent_empty(reading: dict) -> bool:
    events = parse_stat_map(reading.get("cgroup.events", ""))
    return reading.get("pids.current") == "0" and events.get("populated") == "0"


class DiagnosticWatchdog:
    """Observe a private parent/leaf pair. OSError is retained, not swallowed."""

    def __init__(self, start, parent: Path, leaf: Path | None, *, clock=time.monotonic, wall_seconds=120):
        self.start = start
        self.parent = Path(parent)
        self.leaf = Path(leaf) if leaf is not None else None
        self.clock = clock
        self.wall_seconds = wall_seconds
        self.stop = threading.Event()
        self.thread = threading.Thread(target=self.loop, daemon=True)
        self.parent_inode = None
        self.parent_samples = []
        self.leaf_samples = []
        self.error = None
        self.last_oserror = None

    def _identity(self, root: Path | None) -> dict | None:
        if root is None or not root.exists():
            return {"path": None if root is None else str(root), "exists": False}
        stat = root.stat()
        return {"path": str(root), "exists": True, "inode": stat.st_ino, "mode": stat.st_mode}

    def fail(self, reason: str, **extra) -> None:
        if self.error is not None:
            return
        self.error = {
            "reason": reason,
            "at_monotonic": self.clock(),
            "parent_identity": self._identity(self.parent),
            "leaf_identity": self._identity(self.leaf),
            **extra,
        }

    def _read_parent(self) -> dict:
        reading = sample_fields(
            self.parent,
            ("cpu.stat", "memory.current", "memory.peak", "memory.events", "pids.current", "pids.events", "cgroup.events"),
        )
        counters = parse_stat_map(reading["cpu.stat"])
        reading.update(
            cpu_usage_seconds=int(counters.get("usage_usec", "0")) / 1_000_000,
            inode=self.parent.stat().st_ino,
            observed_monotonic=self.clock(),
            path=str(self.parent),
        )
        return reading

    def _read_leaf(self) -> dict:
        reading = sample_fields(
            self.leaf,
            ("cpu.stat", "cpu.max", "memory.current", "memory.peak", "memory.max", "pids.current", "pids.events", "pids.max"),
        )
        counters = parse_stat_map(reading["cpu.stat"])
        reading.update(
            cpu_usage_seconds=int(counters.get("usage_usec", "0")) / 1_000_000,
            inode=self.leaf.stat().st_ino,
            observed_monotonic=self.clock(),
            path=str(self.leaf),
        )
        return reading

    def _handle_oserror(self, operation: str, path: Path, exc: BaseException) -> None:
        snapshot = {
            "operation": operation,
            "path": str(path),
            "errno": getattr(exc, "errno", None),
            "strerror": os.strerror(exc.errno) if getattr(exc, "errno", None) is not None else str(exc),
            "error_type": type(exc).__name__,
            "filename": getattr(exc, "filename", None),
            "parent_identity": self._identity(self.parent),
            "leaf_identity": self._identity(self.leaf),
        }
        self.last_oserror = snapshot
        if isinstance(exc, BENIGN_OSERROR_TYPES):
            self._revalidate_benign_disappearance(snapshot)
            return
        self.fail("resource_observation_" + type(exc).__name__, oserror=snapshot)

    def _revalidate_benign_disappearance(self, snapshot: dict) -> None:
        if self.parent_inode is None:
            self.fail("leaf_disappeared_before_parent_identity", oserror=snapshot)
            return
        if not self.parent.exists():
            self.fail("persistent_parent_disappeared", oserror=snapshot)
            return
        try:
            reading = self._read_parent()
        except OSError as exc:
            self.fail(
                "resource_observation_" + type(exc).__name__,
                oserror={
                    "operation": "revalidate_parent_after_leaf_disappearance",
                    "path": str(self.parent),
                    "errno": exc.errno,
                    "strerror": os.strerror(exc.errno) if exc.errno is not None else str(exc),
                    "error_type": type(exc).__name__,
                    "parent_identity": self._identity(self.parent),
                    "leaf_identity": self._identity(self.leaf),
                },
            )
            return
        if reading["inode"] != self.parent_inode:
            self.fail("parent_identity_changed_after_leaf_disappearance", oserror=snapshot, parent=reading)
            return
        if self.parent_samples and reading["cpu_usage_seconds"] < self.parent_samples[-1]["cpu_usage_seconds"]:
            self.fail("parent_cpu_counter_regressed", oserror=snapshot, parent=reading)
            return
        if not parent_empty(reading):
            self.fail("parent_not_empty_after_leaf_disappearance", oserror=snapshot, parent=reading)
            return
        self.parent_samples.append(reading)

    def check(self) -> None:
        if self.clock() - self.start >= self.wall_seconds:
            self.fail("complete_attempt_wall_budget")
            return
        try:
            if self.parent.exists():
                reading = self._read_parent()
                if self.parent_inode not in (None, reading["inode"]):
                    self.fail("parent_counter_identity_changed", parent=reading)
                    return
                if self.parent_samples and reading["cpu_usage_seconds"] < self.parent_samples[-1]["cpu_usage_seconds"]:
                    self.fail("parent_cpu_counter_regressed", parent=reading)
                    return
                self.parent_inode = reading["inode"]
                self.parent_samples.append(reading)
            elif self.parent_inode is not None:
                self.fail("persistent_parent_disappeared")
            if self.leaf is not None and self.leaf.exists():
                reading = self._read_leaf()
                self.leaf_samples.append(reading)
        except OSError as exc:
            path = Path(exc.filename) if getattr(exc, "filename", None) else self.parent
            leaf_hit = self.leaf is not None and (path == self.leaf or self.leaf in path.parents or path.name and str(path).startswith(str(self.leaf)))
            operation = "leaf_sample" if leaf_hit else "parent_sample"
            self._handle_oserror(operation, path, exc)

    def loop(self) -> None:
        while not self.stop.is_set() and self.error is None:
            self.check()
            self.stop.wait(0.02)

    def start_thread(self) -> None:
        self.thread.start()

    def finish(self) -> None:
        self.stop.set()
        self.thread.join(timeout=6)
        if self.thread.is_alive():
            raise RuntimeError("Watchdog did not stop")


def write_cgroup_fixture(root: Path, *, populated: str = "1", pids: str = "1", usage_usec: int = 1000) -> None:
    root.mkdir(parents=True, exist_ok=True)
    (root / "cpu.stat").write_text(f"usage_usec {usage_usec}\nuser_usec {usage_usec}\nsystem_usec 0\n")
    (root / "cpu.max").write_text("100000 100000\n")
    (root / "memory.current").write_text("4096\n")
    (root / "memory.peak").write_text("8192\n")
    (root / "memory.max").write_text("2147483648\n")
    (root / "memory.events").write_text("low 0\nhigh 0\nmax 0\noom 0\noom_kill 0\n")
    (root / "pids.current").write_text(pids + "\n")
    (root / "pids.max").write_text("16\n")
    (root / "pids.events").write_text("max 0\n")
    (root / "cgroup.events").write_text(f"populated {populated}\nfrozen 0\n")


class InjectedOSErrorPath(type(Path())):
    """Path that raises a non-FileNotFound OSError on selected reads."""

    injected = None

    def read_text(self, *args, **kwargs):
        spec = type(self).injected
        if spec and self.name == spec["name"]:
            raise OSError(spec["errno"], spec["strerror"], str(self))
        return Path.read_text(self, *args, **kwargs)


def probe_oserror_terminal_observation(output: Path) -> dict:
    """Regression probe: retain errno/path/cause; do not treat OSError as benign."""
    from .common import write_json

    parent = output / "parent"
    leaf = output / "leaf"
    write_cgroup_fixture(parent, populated="1", pids="1", usage_usec=2000)
    write_cgroup_fixture(leaf, populated="1", pids="1", usage_usec=1500)
    watchdog = DiagnosticWatchdog(time.monotonic(), parent, leaf, wall_seconds=120)
    watchdog.check()
    if watchdog.error is not None:
        raise RuntimeError("fixture parent/leaf must sample cleanly before injection")
    original_read = Path.read_text

    def injected(self, *args, **kwargs):
        if Path(self).name == "cpu.stat" and Path(self).parent == leaf:
            raise OSError(errno.ENODEV, "No such device", str(self))
        return original_read(self, *args, **kwargs)

    Path.read_text = injected
    try:
        watchdog.check()
    finally:
        Path.read_text = original_read
    if watchdog.error is None or watchdog.last_oserror is None:
        raise RuntimeError("injected OSError was suppressed")
    if watchdog.error["reason"] != "resource_observation_OSError":
        raise RuntimeError("injected OSError was recoded: " + watchdog.error["reason"])
    oserror = watchdog.last_oserror
    if oserror.get("errno") != errno.ENODEV or oserror.get("operation") != "leaf_sample":
        raise RuntimeError("OSError identity incomplete: " + repr(oserror))
    historical = {
        "receipt": "papers/completion/law_to_action/benchmark/generated_code_development/development_qualification_v2/full_repair/iteration-01/cell/host/resources.json",
        "status": "FAILED_RETAINED",
        "upgraded": False,
        "errno_path_cause_proven_by_historical_receipt": False,
        "note": "Historical v2 receipt retains reason=resource_observation_OSError without operation/path/errno. This probe does not rewrite that receipt.",
    }
    report = {
        "schema": "la-watchdog-oserror-diagnostic/v1",
        "status": "PASS",
        "historical_v2_receipt": historical,
        "injected": {"errno": errno.ENODEV, "operation": "leaf_sample", "path_basename": "cpu.stat"},
        "retained_oserror": oserror,
        "error": watchdog.error,
        "parent_identity_retained": watchdog.error["parent_identity"],
        "leaf_identity_retained": watchdog.error["leaf_identity"],
        "broad_oserror_suppressed": False,
        "benign_disappearance_used_for_enodev": False,
        "whole_group_exit_still_mandatory": True,
        "parent_accounting_still_mandatory": True,
    }
    write_json(output / "oserror_probe.json", report)
    return report


def probe_benign_disappearance(output: Path) -> dict:
    """Leaf FileNotFoundError is accepted only after parent identity/empty/monotonic checks."""
    from .common import write_json

    original_read = Path.read_text

    def inject(watchdog, parent, leaf, *, empty_parent: bool):
        write_cgroup_fixture(parent, populated="0" if empty_parent else "1", pids="0" if empty_parent else "1", usage_usec=4000 if empty_parent else 4500)
        write_cgroup_fixture(leaf, populated="1", pids="1", usage_usec=2500)
        watchdog.error = None
        watchdog.last_oserror = None
        if watchdog.parent_inode is None:
            watchdog.check()
        def injected(self, *args, **kwargs):
            path = Path(self)
            if path.name == "cpu.stat" and path.parent == leaf:
                raise FileNotFoundError(errno.ENOENT, "No such file or directory", str(path))
            return original_read(self, *args, **kwargs)
        Path.read_text = injected
        try:
            watchdog.check()
        finally:
            Path.read_text = original_read

    parent = output / "parent"
    leaf = output / "leaf"
    write_cgroup_fixture(parent, populated="1", pids="1", usage_usec=3000)
    write_cgroup_fixture(leaf, populated="1", pids="1", usage_usec=2000)
    watchdog = DiagnosticWatchdog(time.monotonic(), parent, leaf, wall_seconds=120)
    inject(watchdog, parent, leaf, empty_parent=True)
    if watchdog.error is not None:
        raise RuntimeError("stable empty parent should accept leaf FileNotFoundError: " + repr(watchdog.error))
    inject(watchdog, parent, leaf, empty_parent=False)
    if watchdog.error is None or watchdog.error["reason"] != "parent_not_empty_after_leaf_disappearance":
        raise RuntimeError("non-empty parent must fail benign disappearance: " + repr(watchdog.error))
    report = {
        "schema": "la-watchdog-benign-disappearance/v1",
        "status": "PASS",
        "requires_stable_parent_identity": True,
        "requires_monotonic_counters": True,
        "requires_empty_parent": True,
        "non_empty_parent_rejected": True,
        "oserror_not_used_as_benign_shortcut": True,
        "final_error_reason": watchdog.error["reason"],
    }
    write_json(output / "benign_disappearance_probe.json", report)
    return report
