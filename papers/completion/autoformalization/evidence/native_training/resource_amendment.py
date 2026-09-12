"""Explicit amended resource admission and metadata-only native progress journal."""
from __future__ import annotations

import hashlib
import json
import math
import os
from pathlib import Path
import resource
import stat
import time
from datetime import datetime, timezone

SCHEMA = "af029-resource-amended-run-budget/v1"
LIMITS = {"cpus": 2, "memory_bytes": 68719476736, "pids": 64,
          "wall_seconds": 36000, "t2_seconds_per_seed": 10800}
SEEDS = (104729, 130363, 155921)


def file_sha(path):
    path = Path(path)
    if path.is_symlink() or not stat.S_ISREG(path.stat().st_mode):
        raise ValueError("resource evidence must be a regular file")
    with path.open("rb") as handle:
        return hashlib.file_digest(handle, "sha256").hexdigest()


def bound_json(path, expected):
    if file_sha(path) != expected:
        raise ValueError("resource evidence hash mismatch")
    return json.loads(Path(path).read_bytes())


def admit_amended_budget(budget):
    """Return native soft limit; the host owns the complete-stage hard limit."""
    if (budget.get("schema") != SCHEMA or budget.get("resources") != LIMITS
            or any(type(budget["resources"].get(k)) is not int for k in LIMITS)
            or budget.get("seeds") != list(SEEDS)
            or budget.get("population") != {"train": 69, "selection": 15, "final": 0}
            or budget.get("native_update_family_count") != 5
            or budget.get("hard_cumulative_budget_claimed") is not False
            or budget.get("native_t2_soft_seconds") != 9000
            or type(budget.get("native_t2_soft_seconds")) is not int):
        raise ValueError("invalid common resource budget")
    binding = budget["resource_amendment"]
    amendment = bound_json(binding["path"], binding["sha256"])
    if (amendment.get("schema") != "af029-common-resource-amendment/v1"
            or amendment.get("accepted") is not True
            or amendment.get("resources") != LIMITS
            or amendment.get("comparison_arms") != ["T0", "T1", "T2", "T3"]
            or amendment.get("cohort_unchanged") is not True
            or amendment.get("prior_budget_claim_superseded") is not True):
        raise ValueError("resource amendment not admitted")
    prior_runs = budget.get("prior_oom_runs")
    if not isinstance(prior_runs, list) or len(prior_runs) != 2:
        raise ValueError("both prior OOM runs are required")
    reports = []
    for entry in prior_runs:
        report = bound_json(entry["report"], entry["report_sha256"])
        root = Path(entry["output_root"])
        if root.is_symlink() or not root.is_dir():
            raise ValueError("prior OOM output root invalid")
        root = root.resolve()
        inventory = report["output_hashes"]
        actual = {str(p.relative_to(root)) for p in root.rglob("*") if p.is_file()}
        if actual != set(inventory) or len(actual) != report["output_file_count"]:
            raise ValueError("prior OOM inventory changed")
        for name, expected in inventory.items():
            path = root / name
            if not path.resolve().is_relative_to(root) or file_sha(path) != expected:
                raise ValueError("prior OOM artifact changed")
        if report["failure"]["docker_oom_killed"] is not True:
            raise ValueError("prior record is not the retained OOM")
        reports.append(report)
    allowances = budget.get("per_seed", {})
    if set(allowances) != {str(seed) for seed in SEEDS}:
        raise ValueError("amended budget seed mismatch")
    latest = reports[-1]["cost_reconciliation"]["per_seed"]
    for seed, allowance in allowances.items():
        known = allowance.get("known_prior_wall_seconds")
        if (type(known) not in (int, float) or not math.isfinite(known)
                or known != latest[seed]["known_total_wall_seconds"]
                or latest[seed]["unknown_prior_interruptions_remain"] is not True
                or allowance.get("interrupted_usage_unknown") is not True
                or type(allowance.get("new_t2_wall_seconds")) is not int
                or allowance["new_t2_wall_seconds"] != LIMITS["t2_seconds_per_seed"]):
            raise ValueError("amended budget loses prior costs or changes common allowance")
    return budget["native_t2_soft_seconds"]


def bind_environment_resource_limits(environment, budget):
    if budget.get("schema") != SCHEMA or budget.get("resources") != LIMITS:
        raise ValueError("resource environment lacks admitted amendment")
    environment["legacy_declared_resource_limits"] = environment["resource_limits"]
    environment["resource_limits"] = {
        "memory_gib": 64, "cpu_limit": 2, "pids": 64,
        "complete_T2_wall_seconds": 10800, "native_T2_soft_seconds": 9000,
        "whole_wall_seconds": 36000, "per_seed_total_wall_limit": None,
        "gpu_or_model_service_slots": 1, "compute_device": "cpu",
        "scope": "Amended declared profile; actual host container receipt binds enforcement.",
        "T1_T3_outside_T2_interval": True,
    }
    return environment


class NativeProgressJournal:
    """Scalar events only. Failures are sticky and prevent result admission."""
    ALLOWED = {"stage", "elapsed_seconds", "epoch", "seed", "update", "line_search_attempt",
               "sample_count", "validation_sample_count", "state_entry_count", "hard_example_fraction",
               "component", "kind", "rows", "columns", "parameter_scalars", "activity_scalars",
               "parameter_fp32_bytes", "activity_fp32_bytes", "parameter_count", "block_count",
               "chunk_start", "chunk_stop", "accepted_epochs"}

    def __init__(self, path, seed, binding):
        self.path = Path(path)
        self.seed = int(seed)
        self.binding = dict(binding)
        self.error = None
        self.count = 0
        self._fd = os.open(self.path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
        directory = os.open(self.path.parent, os.O_RDONLY | os.O_DIRECTORY)
        os.fsync(directory)
        os.close(directory)

    def __call__(self, event):
        if self.error is not None:
            raise RuntimeError(self.error)
        try:
            payload = {key: value for key, value in event.items()
                       if key in self.ALLOWED and type(value) in (str, int, float, bool, type(None))}
            row = {"schema": "af029-native-phase-telemetry/v1", "sequence": self.count,
                   "at": datetime.now(timezone.utc).isoformat(), "monotonic_seconds": time.monotonic(),
                   "process_cpu_seconds": time.process_time(),
                   "max_rss_kib": resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,
                   "seed": self.seed, "binding": self.binding, "event": payload}
            data = (json.dumps(row, sort_keys=True, allow_nan=False) + "\n").encode()
            offset = 0
            while offset < len(data):
                written = os.write(self._fd, data[offset:])
                if written <= 0:
                    raise OSError("short telemetry write")
                offset += written
            os.fsync(self._fd)
            self.count += 1
        except Exception as error:
            self.error = "native telemetry failure: " + type(error).__name__
            raise

    def close(self):
        if self._fd is not None:
            os.close(self._fd)
            self._fd = None

    def require_complete(self):
        if self.error is not None or self.count == 0:
            raise ValueError(self.error or "native telemetry is empty")
