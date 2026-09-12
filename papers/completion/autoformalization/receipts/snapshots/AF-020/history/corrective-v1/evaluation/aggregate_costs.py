#!/usr/bin/env python3
"""AF-020 cost accounting over retained autoformalization runs.

The aggregator reads frozen run/usage records and command logs.  It does not
train models, call providers, or invent CUDA speedups.  Cost cells stay
explicit about units and about measured versus estimated/provider/unmeasured
status.  Unavailable hardware is never rewritten as a measured zero.
"""
from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import math
import os
import platform
import shutil
import statistics
import subprocess
import sys
import time
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable, Mapping, Optional, Sequence

SCHEMA = "autoformalization-cost-accounting-result/v1"
PAPER_COST_PHASES = (
    "setup",
    "preparation",
    "annotation",
    "target_construction",
    "features",
    "indexing",
    "updates_selection",
    "model_calls",
    "failed_attempts",
    "proof_reconstruction",
    "validation",
    "review",
)
COST_QUANTITIES = (
    "elapsed_seconds",
    "cpu_seconds",
    "gpu_seconds",
    "provider_units",
    "memory_gib",
    "human_review_seconds",
)
COST_UNITS = {
    "elapsed_seconds": "seconds",
    "cpu_seconds": "cpu_seconds",
    "gpu_seconds": "gpu_seconds",
    "provider_units": "provider_units",
    "memory_gib": "gibibytes",
    "human_review_seconds": "seconds",
}
SEALED_PATH = "/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin"
SEALED_TOOLS = (
    "nvidia-smi",
    "nvcc",
    "lean",
    "lake",
    "elan",
    "z3",
    "cvc5",
    "vampire",
    "eprover",
    "coqc",
    "isabelle",
)


def find_repo_root(start: Path) -> Path:
    marker = Path("papers/completion/autoformalization/config/environment_manifest.json")
    for path in (start, *start.parents):
        if (path / marker).is_file():
            return path
    raise SystemExit("cannot locate repository root from aggregate_costs.py")


HERE = Path(__file__).resolve().parent
REPO_ROOT = find_repo_root(HERE)
PAPER_ROOT = REPO_ROOT / "papers/completion/autoformalization"
TELEMETRY_PATH = (
    REPO_ROOT
    / "external/ipfs_datasets/ipfs_datasets_py/optimizers/logic_theorem_optimizer/runtime_telemetry.py"
)
RESULTS_PATH = PAPER_ROOT / "runs/costs/results.jsonl"
EVIDENCE_PATH = PAPER_ROOT / "evidence/cost_accounting.md"


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def canonical_dumps(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False)


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_text(text: str) -> str:
    return sha256_bytes(text.encode("utf-8"))


def sha256_file(path: Path) -> str:
    return sha256_bytes(path.read_bytes())


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    if not path.is_file():
        return rows
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.strip():
            rows.append(json.loads(line))
    return rows


def parse_iso(value: Any) -> Optional[datetime]:
    if not isinstance(value, str) or not value.strip():
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None


def elapsed_from_bounds(started: Any, finished: Any) -> Optional[float]:
    start = parse_iso(started)
    end = parse_iso(finished)
    if start is None or end is None:
        return None
    seconds = (end - start).total_seconds()
    return seconds if seconds >= 0.0 and math.isfinite(seconds) else None


def load_telemetry():
    spec = importlib.util.spec_from_file_location("af020_runtime_telemetry", TELEMETRY_PATH)
    if spec is None or spec.loader is None:
        raise SystemExit(f"cannot load telemetry module: {TELEMETRY_PATH}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def which(name: str) -> Optional[str]:
    return shutil.which(name)


def probe_hardware(telemetry) -> dict[str, Any]:
    binaries = {name: which(name) for name in SEALED_TOOLS}
    smi: dict[str, Any] = {
        "path": binaries.get("nvidia-smi"),
        "exit_code": None,
        "stdout": "",
        "usable": False,
        "reason": "nvidia-smi not on PATH",
    }
    if binaries.get("nvidia-smi"):
        try:
            completed = subprocess.run(
                [
                    binaries["nvidia-smi"],
                    "--query-gpu=name,driver_version,memory.total",
                    "--format=csv,noheader",
                ],
                check=False,
                capture_output=True,
                text=True,
                timeout=2.0,
            )
            smi["exit_code"] = completed.returncode
            smi["stdout"] = (completed.stdout or "").strip()[:500]
            smi["stderr"] = (completed.stderr or "").strip()[:300]
            smi["usable"] = completed.returncode == 0 and bool(smi["stdout"])
            if not smi["usable"]:
                smi["reason"] = smi["stdout"] or smi.get("stderr") or f"nvidia-smi exit {completed.returncode}"
        except (OSError, subprocess.SubprocessError, TimeoutError) as exc:
            smi["reason"] = f"{type(exc).__name__}: {exc}"
    imports: dict[str, Any] = {}
    for name in ("torch", "numpy", "pynvml"):
        try:
            module = __import__(name)
            info: dict[str, Any] = {"ok": True, "version": getattr(module, "__version__", None)}
            if name == "torch":
                cuda = getattr(module, "cuda", None)
                info["cuda_available"] = bool(cuda is not None and cuda.is_available())
                info["device_count"] = int(cuda.device_count()) if info["cuda_available"] else 0
            imports[name] = info
        except Exception as exc:
            imports[name] = {"ok": False, "error": f"{type(exc).__name__}: {exc}"}
    snapshot = telemetry.collect_resource_snapshot()
    snapshot_dict = snapshot.to_dict() if hasattr(snapshot, "to_dict") else dict(snapshot)
    cuda_available = False
    if imports.get("torch", {}).get("cuda_available") is True:
        cuda_available = True
    if snapshot_dict.get("cuda_available") is True and smi["usable"]:
        cuda_available = True
    if not smi["usable"]:
        cuda_available = False
    precision = "unmeasured"
    if imports.get("torch", {}).get("ok"):
        precision = "fp32_host_default_unverified_for_training"
    hardware = "cuda" if cuda_available else "cpu"
    return {
        "schema": SCHEMA,
        "record_kind": "hardware_probe",
        "record_id": "AF-020:hardware_probe",
        "task_id": "AF-020",
        "phase": "setup",
        "interpreter": sys.executable,
        "python_version": sys.version.split()[0],
        "platform": platform.platform(),
        "machine": platform.machine(),
        "path": os.environ.get("PATH", ""),
        "home": os.environ.get("HOME", ""),
        "home_is_validation_private": str(os.environ.get("HOME") or "").startswith(
            "/tmp/ipfs-accelerate-validation-home-"
        )
        or Path(os.environ.get("HOME") or "").name.startswith("ipfs-accelerate-validation-home-"),
        "cuda_visible_devices": os.environ.get("CUDA_VISIBLE_DEVICES"),
        "binaries": binaries,
        "nvidia_smi": smi,
        "imports": imports,
        "resource_snapshot": {
            "cuda_available": snapshot_dict.get("cuda_available"),
            "gpu_telemetry_available": snapshot_dict.get("gpu_telemetry_available"),
            "gpu_device_count": snapshot_dict.get("gpu_device_count"),
            "collector_status": snapshot_dict.get("collector_status"),
        },
        "hardware": telemetry.hardware_precision_record(
            hardware=hardware,
            precision=precision,
            cache_state="unused",
            cuda_available=cuda_available,
            gpu_telemetry_available=bool(snapshot_dict.get("gpu_telemetry_available") and smi["usable"]),
            device=hardware,
            notes="Sealed-PATH probe; operator ~/.local torch/CUDA is out of scope.",
        ),
        "cuda_available": cuda_available,
        "gpu_usable": bool(smi["usable"] and cuda_available),
        "notes": "CUDA speedup/residency remain unmeasured unless matched CPU/CUDA actual runs exist.",
    }


def cell(telemetry, value: Any, quantity: str, **kwargs: Any) -> dict[str, Any]:
    if quantity == "gpu_seconds":
        return telemetry.gpu_cost_from_observation(value, **kwargs)
    return telemetry.classify_cost_quantity(value, quantity=quantity, **kwargs)


def usage_record(
    telemetry,
    *,
    record_id: str,
    task_id: str,
    experiment_arm: str,
    phase: str,
    source_path: str,
    source_sha256: str,
    elapsed: Any,
    elapsed_observed: bool,
    elapsed_reason: str,
    hardware: str,
    precision: str,
    cache_state: str,
    cuda_available: Optional[bool],
    execution_status: str,
    includes_failure: bool = False,
    includes_setup: bool = False,
    provider_units: Any = None,
    provider_observed: bool = False,
    provider_kind: Optional[str] = None,
    human_review: Any = None,
    human_review_observed: bool = False,
    unit_count: Any = None,
    notes: str = "",
    extra: Optional[Mapping[str, Any]] = None,
) -> dict[str, Any]:
    gpu = cell(
        telemetry,
        None,
        "gpu_seconds",
        cuda_available=cuda_available if cuda_available is True else False,
        gpu_telemetry_available=False,
    )
    record = {
        "schema": SCHEMA,
        "record_kind": "source_usage",
        "record_id": record_id,
        "task_id": task_id,
        "experiment_arm": experiment_arm,
        "phase": telemetry.canonical_paper_cost_phase(phase),
        "source_path": source_path,
        "source_sha256": source_sha256,
        "execution_status": execution_status,
        "includes_failure": bool(includes_failure),
        "includes_setup": bool(includes_setup) or telemetry.canonical_paper_cost_phase(phase) == "setup",
        "elapsed_seconds": cell(
            telemetry,
            elapsed,
            "elapsed_seconds",
            observed=elapsed_observed,
            reason=elapsed_reason,
        ),
        "cpu_seconds": cell(
            telemetry,
            None,
            "cpu_seconds",
            observed=False,
            reason="process CPU seconds are not inferred from wall time",
        ),
        "gpu_seconds": gpu,
        "provider_units": cell(
            telemetry,
            provider_units,
            "provider_units",
            observed=provider_observed,
            kind=provider_kind,
            reason="provider units are billed/call counts, not wall-clock measurements"
            if provider_kind == "provider"
            else "",
        ),
        "memory_gib": cell(
            telemetry,
            None,
            "memory_gib",
            observed=False,
            reason="RSS snapshots are not converted into billed memory-GiB",
        ),
        "human_review_seconds": cell(
            telemetry,
            human_review,
            "human_review_seconds",
            observed=human_review_observed,
            reason="independent human review has not been executed"
            if not human_review_observed
            else "retained review timing",
        ),
        "hardware": telemetry.hardware_precision_record(
            hardware=hardware,
            precision=precision,
            cache_state=cache_state,
            cuda_available=cuda_available if isinstance(cuda_available, bool) else None,
            gpu_telemetry_available=False,
        ),
        "unit_count": unit_count,
        "notes": notes,
    }
    if extra:
        record.update(dict(extra))
    return record


def meta_elapsed(path: Path) -> tuple[Optional[float], str]:
    if not path.is_file():
        return None, f"missing command log {path}"
    meta = load_json(path)
    if isinstance(meta.get("elapsed_ms"), (int, float)) and math.isfinite(meta["elapsed_ms"]):
        return float(meta["elapsed_ms"]) / 1000.0, "command log elapsed_ms"
    if isinstance(meta.get("elapsed_seconds"), (int, float)) and math.isfinite(meta["elapsed_seconds"]):
        return float(meta["elapsed_seconds"]), "command log elapsed_seconds"
    bounds = elapsed_from_bounds(meta.get("started_at"), meta.get("finished_at"))
    if bounds is not None:
        return bounds, "command log started_at/finished_at"
    return None, "command log has no elapsed timing"


def collect_training(telemetry) -> list[dict[str, Any]]:
    path = PAPER_ROOT / "receipts/snapshots/AF-011/checkpoints/baselines/manifest.json"
    live = PAPER_ROOT / "runs/training_baselines/manifest.json"
    records: list[dict[str, Any]] = []
    if not path.is_file():
        return records
    data = load_json(path)
    digest = sha256_file(path)
    arm_elapsed: dict[str, list[float]] = defaultdict(list)
    for run in data.get("runs") or []:
        arm = str(run.get("arm_id") or "unknown")
        elapsed = run.get("elapsed_seconds")
        observed = isinstance(elapsed, (int, float)) and math.isfinite(elapsed) and elapsed >= 0
        if observed:
            arm_elapsed[arm].append(float(elapsed))
        phase = "target_construction" if arm == "T0" else "updates_selection"
        cache = "sample_memory" if run.get("sample_memory_enabled_for_update") else "unused"
        seed = run.get("seed")
        replay = run.get("replay")
        ident = f"{arm}:{seed if seed is not None else f'replay{replay}'}"
        records.append(
            usage_record(
                telemetry,
                record_id=f"AF-011:{ident}",
                task_id="AF-011",
                experiment_arm=arm,
                phase=phase,
                source_path=str(path.relative_to(REPO_ROOT)),
                source_sha256=digest,
                elapsed=float(elapsed) if observed else None,
                elapsed_observed=observed,
                elapsed_reason="AF-011 sealed training wall time from checkpoint manifest",
                hardware="cpu",
                precision="python_backend_unquantized",
                cache_state=cache,
                cuda_available=False,
                execution_status="measured" if observed else "unavailable",
                unit_count=None,
                notes=str(run.get("termination_reason") or ""),
                extra={
                    "seed": seed,
                    "replay": replay,
                    "update_count": run.get("update_count"),
                    "accepted_epochs": run.get("accepted_epochs"),
                },
            )
        )
    command = PAPER_ROOT / "receipts/snapshots/AF-011/logs/run.meta.json"
    wall, reason = meta_elapsed(command)
    arm_sum = sum(sum(values) for values in arm_elapsed.values())
    setup = None if wall is None else max(0.0, wall - arm_sum)
    records.append(
        usage_record(
            telemetry,
            record_id="AF-011:setup:sealed_training_command",
            task_id="AF-011",
            experiment_arm="T0-T2",
            phase="setup",
            source_path=str(command.relative_to(REPO_ROOT)) if command.is_file() else str(live.relative_to(REPO_ROOT)),
            source_sha256=sha256_file(command) if command.is_file() else sha256_file(live),
            elapsed=setup,
            elapsed_observed=setup is not None,
            elapsed_reason=f"{reason}; residual after subtracting per-arm wall {arm_sum:.6f}s",
            hardware="cpu",
            precision="python_backend_unquantized",
            cache_state="unused",
            cuda_available=False,
            execution_status="measured" if setup is not None else "unavailable",
            includes_setup=True,
            notes="Sealed-PATH T0/T1/T2 command overhead including imports and capability probe.",
            extra={"command_wall_seconds": wall, "per_arm_elapsed_sum": arm_sum},
        )
    )
    return records


def collect_command_setup(
    telemetry, task_id: str, rel_path: str, arm: str, notes: str,
    *, nested_usage: Sequence[Mapping[str, Any]] = (),
) -> Optional[dict[str, Any]]:
    path = PAPER_ROOT / rel_path
    elapsed, reason = meta_elapsed(path)
    if elapsed is None and not path.is_file():
        return None
    outer_elapsed = elapsed
    children = [
        {"record_id": row["record_id"], "source_path": row["source_path"],
         "source_sha256": row["source_sha256"], "elapsed_seconds": measured_elapsed(row)}
        for row in nested_usage if measured_elapsed(row) is not None
    ]
    child_elapsed = math.fsum(child["elapsed_seconds"] for child in children)
    if children:
        if elapsed is not None:
            if child_elapsed > elapsed + 1e-9:
                raise ValueError(f"{task_id}: nested measured phases exceed enclosing command time")
            elapsed = max(0.0, elapsed - child_elapsed)
        reason += f"; command remainder after subtracting separately counted nested phases ({child_elapsed:.9f}s)"
        notes += " The enclosing command also contains the separately reported nested phases; only its remaining time is charged here."
    return usage_record(
        telemetry,
        record_id=f"{task_id}:setup:{path.stem}",
        task_id=task_id,
        experiment_arm=arm,
        phase="setup",
        source_path=str(path.relative_to(REPO_ROOT)) if path.is_file() else rel_path,
        source_sha256=sha256_file(path) if path.is_file() else "0" * 64,
        elapsed=elapsed,
        elapsed_observed=elapsed is not None,
        elapsed_reason=reason,
        hardware="cpu",
        precision="unmeasured",
        cache_state="unused",
        cuda_available=False,
        execution_status="measured" if elapsed is not None else "unavailable",
        includes_setup=True,
        notes=notes,
        extra={"elapsed_coverage": {
            "policy": "outer_command_minus_separately_counted_nested_phases",
            "outer_elapsed_seconds": outer_elapsed,
            "nested_elapsed_seconds": child_elapsed,
            "nested_records": children,
            "remainder_includes_unmeasured_command_work": True,
        }} if children else None,
    )


def shared_af018_policy_scans(rows: Sequence[Mapping[str, Any]]) -> tuple[dict[str, str], list[dict[str, Any]]]:
    """Attribute each frozen AF018 fixture scan once, without changing raw rows.

    The retained producer times the scan before its two-arm loop. This is a
    source-specific reduction, not generic deduplication of similar timings.
    """
    groups: dict[tuple[str, str], list[Mapping[str, Any]]] = defaultdict(list)
    for row in rows:
        if row.get("stage") != "policy_scan":
            continue
        detail = row.get("detail") or {}
        identities = row.get("identities") or {}
        value = (row.get("cost") or {}).get("elapsed_seconds")
        if not (
            row.get("fixture") is True and row.get("constructed_control") is True
            and detail.get("not_a_model_output") is True
            and identities.get("tool") == "lean-policy-scan/v1"
            and isinstance(row.get("goal_id"), str) and row["goal_id"]
            and isinstance(detail.get("source_sha256"), str) and len(detail["source_sha256"]) == 64
            and type(value) in (int, float) and math.isfinite(value) and value >= 0
        ):
            raise ValueError("AF018 policy scan lacks the frozen shared-fixture provenance")
        groups[(row["goal_id"], detail["source_sha256"])].append(row)
    attribution: dict[str, str] = {}
    scans = []
    for (goal, source_hash), pair in sorted(groups.items()):
        if len(pair) != 2 or {r.get("experiment_arm") for r in pair} != {"hammer", "leanstral"}:
            raise ValueError("AF018 shared policy scan requires its exact two-arm pair")
        values = [(r.get("cost") or {})["elapsed_seconds"] for r in pair]
        if values[0] != values[1] or pair[0].get("execution_status") != pair[1].get("execution_status"):
            raise ValueError("AF018 shared policy scan pair has inconsistent timing/status")
        charge = "AF-018:shared-policy-scan:" + sha256_text(canonical_dumps([goal, source_hash]))[:16] + ":validation"
        originals = []
        for row in pair:
            rid = row.get("record_id")
            if not isinstance(rid, str) or rid in attribution:
                raise ValueError("AF018 duplicate or missing policy record identity")
            attribution[rid] = charge
            originals.append({"record_id": rid, "record_sha256": sha256_text(canonical_dumps(row)),
                              "experiment_arm": row["experiment_arm"], "execution_status": row.get("execution_status"),
                              "elapsed_seconds": values[0]})
        scans.append({"record_id": charge, "goal_id": goal, "source_sha256": source_hash,
                      "elapsed_seconds": values[0], "original_records": originals,
                      "execution_status": pair[0].get("execution_status")})
    return attribution, scans


def collect_jsonl_costs(
    telemetry,
    *,
    task_id: str,
    rel_path: str,
    phase: str,
    arm_field: str,
    cache_state: str,
    notes: str,
    include_failures: bool = True,
) -> list[dict[str, Any]]:
    path = PAPER_ROOT / rel_path
    rows = load_jsonl(path)
    if not rows:
        return []
    digest = sha256_file(path)
    shared_attribution: dict[str, str] = {}
    shared_scans: list[dict[str, Any]] = []
    if task_id == "AF-018" and rel_path == "runs/proof_assistance/results.jsonl":
        producer = PAPER_ROOT / "receipts/snapshots/AF-018/measure_assistance.py"
        if sha256_file(producer) != "f7ed70294c1982a5aea5d5440d50411f9c09f617e531b6a27bbdf9a3073aea9b":
            raise ValueError("AF018 shared timing reduction requires the reviewed original producer")
        shared_attribution, shared_scans = shared_af018_policy_scans(rows)
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        if row.get("kind") == "summary" or row.get("record_kind") in {"summary", "coverage", "capability"}:
            continue
        arm = str(row.get(arm_field) or row.get("experiment_arm") or row.get("arm_id") or row.get("route_id") or "unknown")
        grouped[arm].append(row)
    records: list[dict[str, Any]] = []
    for arm, items in sorted(grouped.items()):
        elapsed_values = []
        failures = 0
        provider_values = []
        for item in items:
            cost = item.get("cost") if isinstance(item.get("cost"), Mapping) else {}
            value = cost.get("elapsed_seconds") if cost else item.get("elapsed_seconds")
            shared_charge = shared_attribution.get(item.get("record_id"))
            unavailable_zero = (
                task_id == "AF-018" and rel_path == "runs/proof_assistance/results.jsonl"
                and value == 0.0 and item.get("execution_status") in {"unavailable", "unsupported"}
            )
            if not shared_charge and not unavailable_zero and isinstance(value, (int, float)) and math.isfinite(value) and value >= 0:
                elapsed_values.append(float(value))
            status = str(item.get("execution_status") or item.get("status") or "")
            if status in {"failure", "timeout", "invalid", "error", "failed"} or item.get("includes_failure"):
                failures += 1
            provider = cost.get("provider_units") if cost else None
            if isinstance(provider, (int, float)) and math.isfinite(provider):
                provider_values.append(float(provider))
        observed = bool(elapsed_values)
        total = sum(elapsed_values) if elapsed_values else None
        records.append(
            usage_record(
                telemetry,
                record_id=f"{task_id}:{arm}:{phase}",
                task_id=task_id,
                experiment_arm=arm,
                phase=phase,
                source_path=rel_path,
                source_sha256=digest,
                elapsed=total,
                elapsed_observed=observed,
                elapsed_reason="sum of retained per-record elapsed_seconds"
                if observed
                else "retained rows have no elapsed_seconds; per-item latency unmeasured",
                hardware="cpu",
                precision="unmeasured",
                cache_state=cache_state,
                cuda_available=False,
                execution_status="measured" if observed else "partial",
                includes_failure=bool(failures) if include_failures else False,
                provider_units=sum(provider_values) if provider_values else 0.0 if observed else None,
                provider_observed=bool(provider_values) or observed,
                provider_kind="provider" if provider_values or observed else None,
                unit_count=len(items),
                notes=notes,
                extra={
                    "row_count": len(items),
                    "shared_elapsed_attribution": [
                        {"original_record_id": item["record_id"], "charge_record_id": shared_attribution[item["record_id"]]}
                        for item in items if item.get("record_id") in shared_attribution
                    ],
                    "raw_rows_preserved": True,
                    "failure_row_count": failures,
                    "elapsed_min": min(elapsed_values) if elapsed_values else None,
                    "elapsed_max": max(elapsed_values) if elapsed_values else None,
                    "elapsed_median": statistics.median(elapsed_values) if elapsed_values else None,
                },
            )
        )
        if failures:
            records.append(
                usage_record(
                    telemetry,
                    record_id=f"{task_id}:{arm}:failed_attempts",
                    task_id=task_id,
                    experiment_arm=arm,
                    phase="failed_attempts",
                    source_path=rel_path,
                    source_sha256=digest,
                    elapsed=None,
                    elapsed_observed=False,
                    elapsed_reason="failure rows counted; their elapsed remains in the parent phase total",
                    hardware="cpu",
                    precision="unmeasured",
                    cache_state=cache_state,
                    cuda_available=False,
                    execution_status="measured",
                    includes_failure=True,
                    unit_count=failures,
                    notes=f"{failures} retained failure/timeout/invalid rows; elapsed is not double-counted here.",
                )
            )
    for scan in shared_scans:
        records.append(usage_record(
            telemetry, record_id=scan["record_id"], task_id=task_id,
            experiment_arm="shared_policy_fixture_scan", phase="validation",
            source_path=rel_path, source_sha256=digest,
            elapsed=scan["elapsed_seconds"], elapsed_observed=True,
            elapsed_reason="one actual pre-arm-loop policy scan; duplicated raw arm timings attributed once",
            hardware="cpu", precision="unmeasured", cache_state="unused", cuda_available=False,
            execution_status="measured", unit_count=1,
            notes="Shared constructed policy-validation cost, not a provider call or executed native proof; raw arm statuses remain unchanged.",
            extra={"shared_scan_attribution": scan,
                   "raw_producer_source_sha256": "f7ed70294c1982a5aea5d5440d50411f9c09f617e531b6a27bbdf9a3073aea9b"},
        ))
    return records


def collect_af009(telemetry) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    executions = PAPER_ROOT / "receipts/snapshots/AF-009/native-packed-cpu-20260912/executions"
    if executions.is_dir():
        for path in sorted(executions.glob("*.json")):
            data = load_json(path)
            elapsed = data.get("elapsed_seconds")
            observed = isinstance(elapsed, (int, float)) and math.isfinite(elapsed)
            cuda_env = ""
            env = data.get("environment") if isinstance(data.get("environment"), Mapping) else {}
            cuda_env = str(env.get("CUDA_VISIBLE_DEVICES", ""))
            records.append(
                usage_record(
                    telemetry,
                    record_id=f"AF-009:packed_cpu:{path.stem}",
                    task_id="AF-009",
                    experiment_arm="packed_cpu",
                    phase="validation",
                    source_path=str(path.relative_to(REPO_ROOT)),
                    source_sha256=sha256_file(path),
                    elapsed=float(elapsed) if observed else None,
                    elapsed_observed=observed,
                    elapsed_reason="AF-009 native packed-CPU qualification wall time",
                    hardware="cpu",
                    precision="float32",
                    cache_state="unused",
                    cuda_available=False,
                    execution_status="measured" if observed and data.get("exit_code") == 0 else (
                        "failure" if observed else "unavailable"
                    ),
                    includes_failure=data.get("exit_code") not in (0, None),
                    notes="CUDA_VISIBLE_DEVICES empty; CUDA tests skipped. Packed-CPU float32 qualification only.",
                    extra={
                        "exit_code": data.get("exit_code"),
                        "cuda_visible_devices": cuda_env,
                        "research_run": data.get("research_run"),
                    },
                )
            )
    backend = PAPER_ROOT / "config/training_backend.json"
    if backend.is_file():
        data = load_json(backend)
        cuda = data.get("cuda") if isinstance(data.get("cuda"), Mapping) else {}
        records.append(
            usage_record(
                telemetry,
                record_id="AF-009:cuda:status",
                task_id="AF-009",
                experiment_arm="cuda",
                phase="updates_selection",
                source_path=str(backend.relative_to(REPO_ROOT)),
                source_sha256=sha256_file(backend),
                elapsed=None,
                elapsed_observed=False,
                elapsed_reason=str(cuda.get("parity") or "unmeasured")
                + "; AF-009 records CUDA unavailable with skipped tests",
                hardware="cuda",
                precision="unmeasured",
                cache_state="unmeasured",
                cuda_available=False,
                execution_status="unavailable",
                notes="Host torch reported cuda_available on operator profile; sealed CUDA training/residency were not executed.",
                extra={"cuda_status": cuda, "selected_backend": data.get("selected_backend")},
            )
        )
    return records


def collect_unmeasured_phases(telemetry, probe: Mapping[str, Any]) -> list[dict[str, Any]]:
    records = []
    records.append(
        usage_record(
            telemetry,
            record_id="AF-005:annotation:unmeasured",
            task_id="AF-005",
            experiment_arm="independent_gold",
            phase="annotation",
            source_path="papers/completion/autoformalization/data/gold_facets.jsonl",
            source_sha256=sha256_file(PAPER_ROOT / "data/gold_facets.jsonl")
            if (PAPER_ROOT / "data/gold_facets.jsonl").is_file()
            else "0" * 64,
            elapsed=None,
            elapsed_observed=False,
            elapsed_reason="independent gold/annotation is pending; not a zero-cost result",
            hardware="cpu",
            precision="unmeasured",
            cache_state="unused",
            cuda_available=False,
            execution_status="unavailable",
            notes="AF-005 independent facet adjudication has not produced review timings.",
        )
    )
    records.append(
        usage_record(
            telemetry,
            record_id="AF-020:review:unmeasured",
            task_id="AF-020",
            experiment_arm="human_review",
            phase="review",
            source_path="papers/completion/autoformalization/evidence/human_review_handoff.md",
            source_sha256=sha256_file(PAPER_ROOT / "evidence/human_review_handoff.md")
            if (PAPER_ROOT / "evidence/human_review_handoff.md").is_file()
            else "0" * 64,
            elapsed=None,
            elapsed_observed=False,
            elapsed_reason="human review seconds are unmeasured pending independent adjudication",
            hardware="cpu",
            precision="unmeasured",
            cache_state="unused",
            cuda_available=False,
            execution_status="unavailable",
            notes="Zero is not recorded for unperformed review.",
        )
    )
    records.append(
        usage_record(
            telemetry,
            record_id="AF-018:model_calls:leanstral",
            task_id="AF-018",
            experiment_arm="leanstral",
            phase="model_calls",
            source_path="papers/completion/autoformalization/runs/proof_assistance/results.jsonl",
            source_sha256=sha256_file(PAPER_ROOT / "runs/proof_assistance/results.jsonl")
            if (PAPER_ROOT / "runs/proof_assistance/results.jsonl").is_file()
            else "0" * 64,
            elapsed=None,
            elapsed_observed=False,
            elapsed_reason="no Leanstral/model-service wall time; model was not served",
            hardware="cpu",
            precision="unmeasured",
            cache_state="unused",
            cuda_available=False,
            execution_status="unavailable",
            provider_units=0.0,
            provider_observed=True,
            provider_kind="provider",
            notes="Measured zero provider calls; GPU/model-service seconds remain unmeasured.",
        )
    )
    records.append(
        usage_record(
            telemetry,
            record_id="AF-020:features:indexing_unmeasured_minilm",
            task_id="AF-017",
            experiment_arm="minilm",
            phase="features",
            source_path="papers/completion/autoformalization/config/environment_manifest.json",
            source_sha256=sha256_file(PAPER_ROOT / "config/environment_manifest.json"),
            elapsed=None,
            elapsed_observed=False,
            elapsed_reason="MiniLM/FAISS embeddings were unavailable under sealed PATH",
            hardware="cpu",
            precision="unmeasured",
            cache_state="unused",
            cuda_available=False,
            execution_status="unavailable",
            notes="Hashed-trigram vector route in AF-017 is not a MiniLM embedding cost.",
        )
    )
    if not probe.get("gpu_usable"):
        records.append(
            usage_record(
                telemetry,
                record_id="AF-020:cuda:unmeasured",
                task_id="AF-020",
                experiment_arm="cuda",
                phase="updates_selection",
                source_path="papers/completion/autoformalization/evaluation/aggregate_costs.py",
                source_sha256=sha256_file(Path(__file__)),
                elapsed=None,
                elapsed_observed=False,
                elapsed_reason="no matched CPU/CUDA/precision actual training run in the sealed environment",
                hardware="cuda",
                precision="unmeasured",
                cache_state="unmeasured",
                cuda_available=False,
                execution_status="unavailable",
                notes="Unavailable CUDA is not a zero-cost or 1.0x speedup result.",
            )
        )
    return records


def instrumentation_contract(telemetry, probe: Mapping[str, Any]) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    class Clock:
        def __init__(self) -> None:
            self.value = 10.0

        def __call__(self) -> float:
            self.value += 0.5
            return self.value

    def sampler(queue_depth: int = 0):
        return telemetry.ResourceSnapshot(
            captured_at="2026-09-12T00:00:00+00:00",
            cpu_percent=1.0,
            process_cpu_percent=1.0,
            memory_used_bytes=1,
            gpu_device_count=0,
            gpu_telemetry_available=False,
            cuda_available=False,
            queue_depth=queue_depth,
            collector_status="contract_sampler",
        )

    collector = telemetry.RuntimeTelemetry(
        "af-020-contract",
        resource_sampler=sampler,
        clock=Clock(),
        resource_sample_interval_seconds=0.0,
    )
    setup_span = collector.start_span("merge", attributes={"stage": "setup"})
    collector.finish_span(setup_span, status="ok")
    fail = collector.start_span("solver_execution", unit_count=1)
    collector.finish_span(fail, status="failure", error_type="UnavailableSolver")
    val = collector.start_span("validation", unit_count=1)
    collector.finish_span(val, status="ok")
    ledger = collector.cost_ledger()
    recon = ledger.reconcile()
    if not recon["ok"]:
        raise SystemExit(f"telemetry cost ledger failed to reconcile: {recon['mismatches']}")
    gpu_zero = telemetry.gpu_cost_from_observation(0.0, cuda_available=False)
    if gpu_zero.get("value") == 0.0 or gpu_zero.get("kind") != "unmeasured":
        raise SystemExit("unavailable GPU was converted into a measured zero")
    speedup = telemetry.matched_throughput(
        None,
        {"elapsed_seconds": 1.0, "hardware": "cuda", "precision": "fp16", "cache_state": "warm", "execution_status": "measured"},
    )
    if speedup.get("value") is not None or speedup.get("status") != "unmeasured":
        raise SystemExit("CUDA speedup was invented without a matched baseline run")
    record = {
        "schema": SCHEMA,
        "record_kind": "instrumentation_contract",
        "record_id": "AF-020:telemetry_contract",
        "task_id": "AF-020",
        "phase": "validation",
        "execution_status": "measured",
        "hardware": probe["hardware"],
        "reconciliation": recon,
        "gpu_zero_rejected": gpu_zero,
        "unmatched_cuda_speedup": speedup,
        "phase_catalog": list(telemetry.PAPER_COST_PHASES),
        "notes": "Contract check of runtime_telemetry cost APIs; not a CUDA economics result.",
    }
    return record, list(ledger.records)


def measured_elapsed(record: Mapping[str, Any]) -> Optional[float]:
    cell_obj = record.get("elapsed_seconds")
    if isinstance(cell_obj, Mapping) and cell_obj.get("kind") == "measured":
        value = cell_obj.get("value")
        if isinstance(value, (int, float)) and math.isfinite(value):
            return float(value)
    return None


def build_ledger(telemetry, usage: Sequence[Mapping[str, Any]]):
    ledger = telemetry.CostLedger()
    independent = 0.0
    for record in usage:
        elapsed = measured_elapsed(record)
        if elapsed is not None:
            independent += elapsed
        ledger.add(
            {
                "phase": record.get("phase"),
                "status": record.get("execution_status"),
                "includes_failure": record.get("includes_failure"),
                "includes_setup": record.get("includes_setup"),
                "elapsed_seconds": record.get("elapsed_seconds"),
                "cpu_seconds": record.get("cpu_seconds"),
                "gpu_seconds": record.get("gpu_seconds"),
                "provider_units": record.get("provider_units"),
                "memory_gib": record.get("memory_gib"),
                "human_review_seconds": record.get("human_review_seconds"),
                "hardware": record.get("hardware"),
                "record_id": record.get("record_id"),
            }
        )
    recon = ledger.reconcile(independent_elapsed_sum=independent)
    if not recon["ok"]:
        raise SystemExit(f"phase totals do not reconcile: {recon['mismatches']}")
    return ledger, recon, independent


def phase_total_records(telemetry, recon: Mapping[str, Any], probe: Mapping[str, Any]) -> list[dict[str, Any]]:
    records = []
    totals = recon.get("phase_totals") or {}
    for phase in PAPER_COST_PHASES:
        payload = totals.get(phase) or {}
        present = bool(payload.get("present"))
        measured = bool(payload.get("measured_elapsed_present"))
        elapsed = payload.get("measured_elapsed_seconds") if measured else None
        records.append(
            {
                "schema": SCHEMA,
                "record_kind": "phase_total",
                "record_id": f"AF-020:phase:{phase}",
                "task_id": "AF-020",
                "phase": phase,
                "execution_status": "measured" if measured else "unmeasured",
                "elapsed_seconds": cell(
                    telemetry,
                    elapsed,
                    "elapsed_seconds",
                    observed=measured,
                    reason="sum of retained measured usage in this phase"
                    if measured
                    else "no measured usage retained for this phase; not a zero-cost claim",
                ),
                "cpu_seconds": cell(telemetry, None, "cpu_seconds", observed=False),
                "gpu_seconds": cell(
                    telemetry,
                    None,
                    "gpu_seconds",
                    cuda_available=False,
                    gpu_telemetry_available=False,
                ),
                "provider_units": cell(telemetry, None, "provider_units", observed=False),
                "memory_gib": cell(telemetry, None, "memory_gib", observed=False),
                "human_review_seconds": cell(telemetry, None, "human_review_seconds", observed=False),
                "hardware": probe["hardware"],
                "record_count": payload.get("record_count", 0),
                "failure_record_count": payload.get("failure_record_count", 0),
                "setup_record_count": payload.get("setup_record_count", 0),
                "includes_setup": True,
                "includes_failures": True,
            }
        )
    return records


def throughput_records(telemetry, usage: Sequence[Mapping[str, Any]], probe: Mapping[str, Any]) -> list[dict[str, Any]]:
    t0 = [
        row
        for row in usage
        if row.get("task_id") == "AF-011" and row.get("experiment_arm") == "T0" and measured_elapsed(row) is not None
    ]
    cpu_matched = None
    if len(t0) >= 2:
        baseline = {
            "elapsed_seconds": measured_elapsed(t0[0]),
            "hardware": "cpu",
            "precision": "python_backend_unquantized",
            "cache_state": "unused",
            "execution_status": "measured",
            "unit_count": 1.0,
            "matched_identity": "AF-011:T0:codec_replay",
        }
        treatment = dict(baseline)
        treatment["elapsed_seconds"] = measured_elapsed(t0[1])
        cpu_matched = telemetry.matched_throughput(baseline, treatment, comparison="t0_replay_ratio")
    cuda = telemetry.matched_throughput(
        {
            "elapsed_seconds": measured_elapsed(t0[0]) if t0 else 1.0,
            "hardware": "cpu",
            "precision": "python_backend_unquantized",
            "cache_state": "unused",
            "execution_status": "measured",
            "matched_identity": "AF-011:T0",
        }
        if t0
        else None,
        None,
        comparison="cpu_vs_cuda_speedup",
    )
    return [
        {
            "schema": SCHEMA,
            "record_kind": "throughput",
            "record_id": "AF-020:throughput:cpu_t0_replays",
            "task_id": "AF-020",
            "phase": "target_construction",
            "execution_status": "measured" if cpu_matched and cpu_matched.get("status") == "measured" else "unmeasured",
            "hardware": probe["hardware"],
            "comparison": cpu_matched,
            "notes": "T0 codec replays are matched CPU actual runs of the same identity; this is not a CUDA speedup.",
        },
        {
            "schema": SCHEMA,
            "record_kind": "throughput",
            "record_id": "AF-020:throughput:cuda_unmeasured",
            "task_id": "AF-020",
            "phase": "updates_selection",
            "execution_status": "unavailable",
            "hardware": telemetry.hardware_precision_record(
                hardware="cuda",
                precision="unmeasured",
                cache_state="unmeasured",
                cuda_available=False,
                gpu_telemetry_available=False,
            ),
            "comparison": cuda,
            "notes": "No matched cold/warm CPU/CUDA/precision actual runs. Unavailable CUDA is not a 0.0s or 1.0x result.",
        },
    ]


def render_markdown(
    *,
    probe: Mapping[str, Any],
    recon: Mapping[str, Any],
    usage: Sequence[Mapping[str, Any]],
    throughput: Sequence[Mapping[str, Any]],
    versions: Mapping[str, Any],
) -> str:
    lines = [
        "# AF-020 cost accounting",
        "",
        "This note accounts for retained autoformalization preparation, annotation, target construction,",
        "features, indexing, updates/selection, model calls, failed attempts, proof reconstruction,",
        "validation, review, and setup costs.  Values come from frozen run/usage records and command",
        "logs.  Dry-run synthetic throughput is not used as CUDA or residency evidence.",
        "",
        "## Cost units and observation kinds",
        "",
        "| Quantity | Unit | Measured meaning | Unmeasured / other |",
        "| --- | --- | --- | --- |",
        "| elapsed_seconds | seconds | Wall time from a retained command or per-record timer | Null if no timer was kept |",
        "| cpu_seconds | cpu_seconds | Independently observed process CPU time | Never inferred from elapsed wall time |",
        "| gpu_seconds | gpu_seconds | Seconds on actually running CUDA/GPU | Null when CUDA is unavailable; not a measured 0.0 |",
        "| provider_units | provider_units | Executed provider/model-call units | Estimated/provider rates stay labeled; unused calls may be a measured 0 |",
        "| memory_gib | gibibytes | Billed or independently metered GiB | RSS snapshots are not converted into billed GiB |",
        "| human_review_seconds | seconds | Independently timed review | Pending review is unmeasured, not 0.0 |",
        "",
        "Observation kinds are `measured`, `estimated`, `provider`, and `unmeasured`.",
        "Estimated and provider figures are never relabeled as measured wall-clock costs.",
        "",
        "## Current reducer environment and retained-run hardware",
        "",
        "This hardware probe describes the current accounting process only. It neither changes the retained historical run hardware nor demonstrates CUDA training.",
        "",
        f"- Sealed PATH: `{probe.get('path')}`",
        f"- Interpreter: `{probe.get('interpreter')}` ({probe.get('python_version')})",
        f"- Machine: `{probe.get('machine')}`",
        f"- CUDA_VISIBLE_DEVICES: `{probe.get('cuda_visible_devices')}`",
        f"- nvidia-smi usable: `{probe.get('nvidia_smi', {}).get('usable')}`",
        f"- nvidia-smi reason: {probe.get('nvidia_smi', {}).get('reason')}",
        f"- torch import: `{json.dumps(probe.get('imports', {}).get('torch'), sort_keys=True)}`",
        f"- CUDA available in this process: `{probe.get('cuda_available')}`",
        f"- Hardware record: `{canonical_dumps(probe.get('hardware'))}`",
        "",
        "AF-009 selected `packed_cpu` with float32 parameters/losses on the operator host and recorded",
        "CUDA status `unavailable` (skipped tests, `CUDA_VISIBLE_DEVICES` empty).  AF-011 sealed T0–T2",
        "ran the python autoencoder backend because torch/NumPy were absent from the private HOME.",
        "Those are distinct hardware/precision conditions and are not a matched CPU/CUDA pair.",
        "",
        "Cache state is explicit per usage row: `unused`, `hit`, `miss`, `sample_memory`, or `unmeasured`.",
        "T1 sample-memory updates are labeled `sample_memory` and are not treated as a CUDA residency win.",
        "",
        "## Phase totals",
        "",
        "| Phase | Records | Measured elapsed (s) | Failures | Setup rows | Present |",
        "| --- | ---: | ---: | ---: | ---: | --- |",
    ]
    totals = recon.get("phase_totals") or {}
    for phase in PAPER_COST_PHASES:
        payload = totals.get(phase) or {}
        elapsed = payload.get("measured_elapsed_seconds")
        elapsed_text = (
            f"{elapsed:.6f}"
            if payload.get("measured_elapsed_present") and isinstance(elapsed, (int, float))
            else "unmeasured"
        )
        lines.append(
            f"| {phase} | {payload.get('record_count', 0)} | {elapsed_text} | "
            f"{payload.get('failure_record_count', 0)} | {payload.get('setup_record_count', 0)} | "
            f"{payload.get('present', False)} |"
        )
    lines.extend(
        [
            "",
            f"Measured elapsed summed across phases: {recon.get('phase_measured_elapsed_seconds')} s.",
            f"Measured elapsed summed across retained records: {recon.get('record_measured_elapsed_seconds')} s.",
            f"Independent usage sum: {recon.get('independent_elapsed_seconds')} s.",
            f"Reconciliation ok: `{recon.get('ok')}`. Setup included: `{recon.get('includes_setup')}`. Failures included: `{recon.get('includes_failures')}`.",
            "Phase totals reconcile with retained run/usage records, including setup and failures.",
            "AF018's enclosing command is charged once: separately timed planning, candidate-generation and unique shared policy scans are subtracted from the command remainder. Each policy fixture was scanned once before the hammer/Leanstral loop; its duplicated raw arm timings are charged once as shared validation. Original rows/statuses are retained and mapped by exact goal, source hash and original producer hash. Unavailable-stage zero placeholders are not measured proof execution.",
            "",
            "## Retained sources",
            "",
            "Usage rows keep the source path and SHA-256 of the frozen record they were reduced from.",
            "Item-level training rows are not re-emitted; AF-011 arm/replay wall times come from the",
            "checkpoint manifest.  Planning and assistance elapsed values are sums of retained",
            "`cost.elapsed_seconds` cells.  Retrieval/premise rows without timers contribute setup from",
            "the sealed command log and leave per-query latency unmeasured.",
            "",
            f"Source usage rows: {sum(1 for row in usage if row.get('record_kind') == 'source_usage')}.",
            "",
            "## Throughput and speedup",
            "",
        ]
    )
    for row in throughput:
        comparison = row.get("comparison") or {}
        lines.append(
            f"- `{row.get('record_id')}`: status `{comparison.get('status') or row.get('execution_status')}`"
            f" value `{comparison.get('value')}` — {row.get('notes')}"
        )
    lines.extend(
        [
            "",
            "Any CUDA or residency benefit remains unmeasured.  Unavailable hardware is not a zero-cost result,",
            "and it is not reported as 0.0 seconds or a 1.0x speedup.",
            "",
            "## Limitations",
            "",
            "- The current reducer's observed hardware probe is scoped to this rerender; retained source-run CUDA and precision limitations remain unchanged.",
            "- CPU seconds, billed memory-GiB, MiniLM/FAISS embedding cost, Leanstral GPU time, and human review are unmeasured.",
            "- Annotation cost is unmeasured while AF-005 independent gold is pending.",
            "- AF-011 `elapsed_seconds: 0.0` on some aggregate jsonl rows is ignored; wall times are taken from the checkpoint manifest.",
            "- Planning/assistance records that stored `gpu_seconds: 0.0` without CUDA are reclassified as unmeasured GPU cost.",
            "- Packed-CPU qualification (AF-009) is CPU float32 evidence, not a CUDA matched run.",
            "- This accounting is provenance over retained records, not independent scientific replication.",
            "",
            "## Versions",
            "",
            f"- Generated at: {versions.get('generated_at')}",
            f"- aggregate_costs.py sha256: `{versions.get('aggregate_costs_sha256')}`",
            f"- runtime_telemetry.py sha256: `{versions.get('runtime_telemetry_sha256')}`",
            f"- environment_manifest sha256: `{versions.get('environment_manifest_sha256')}`",
            f"- experiment_plan sha256: `{versions.get('experiment_plan_sha256')}`",
            "",
        ]
    )
    return "\n".join(lines)


def collect_all(telemetry, probe: Mapping[str, Any]) -> list[dict[str, Any]]:
    usage: list[dict[str, Any]] = []
    usage.extend(collect_training(telemetry))
    usage.extend(collect_af009(telemetry))
    # Both result files are written within AF018's retained measure.meta
    # command. Normalize the shared fixture scans first; then its remaining
    # item timers are disjoint components of that outer interval.
    # Keep those measurements and charge only the remaining command time as
    # setup; adding the entire command would count the item timers twice.
    assistance_usage = collect_jsonl_costs(
        telemetry, task_id="AF-018", rel_path="runs/planning/results.jsonl",
        phase="preparation", arm_field="experiment_arm", cache_state="unused",
        notes="Deterministic plan replay wall time; not proof execution.",
    ) + collect_jsonl_costs(
        telemetry, task_id="AF-018", rel_path="runs/proof_assistance/results.jsonl",
        phase="proof_reconstruction", arm_field="experiment_arm", cache_state="unused",
        notes="Hammer/Leanstral assistance attempts including unsupported and unavailable stages.",
    )
    for item in (
        collect_command_setup(
            telemetry, "AF-007", "receipts/snapshots/AF-007/logs/test_result_accounting.meta.json",
            "evaluation_harness", "AF-007 accounting-test setup wall time.",
        ),
        collect_command_setup(
            telemetry, "AF-007", "receipts/snapshots/AF-007/logs/check_schema.meta.json",
            "evaluation_harness", "AF-007 schema-check setup wall time.",
        ),
        collect_command_setup(
            telemetry, "AF-015", "receipts/snapshots/AF-015/logs/bridge_cases.meta.json",
            "AF-015-bridge-validation", "AF-015 bridge-case command wall time (setup + constructed checks).",
        ),
        collect_command_setup(
            telemetry, "AF-017", "receipts/snapshots/AF-017/logs/measure.meta.json",
            "retrieval", "AF-017 sealed retrieval/indexing command wall time.",
        ),
        collect_command_setup(
            telemetry, "AF-018", "receipts/snapshots/AF-018/logs/measure.meta.json",
            "planning_assistance", "AF-018 sealed planning/assistance command wall time.",
            nested_usage=assistance_usage,
        ),
        collect_command_setup(
            telemetry, "AF-012", "receipts/snapshots/AF-012/logs/run.meta.json"
            if (PAPER_ROOT / "receipts/snapshots/AF-012/logs/run.meta.json").is_file()
            else "receipts/snapshots/AF-012/logs/measure.meta.json",
            "proof_heads", "AF-012 proof-head command wall time if retained.",
        ),
    ):
        if item is not None:
            usage.append(item)
    usage.extend(assistance_usage)
    usage.extend(
        collect_jsonl_costs(
            telemetry,
            task_id="AF-017",
            rel_path="runs/retrieval/results.jsonl",
            phase="indexing",
            arm_field="route_id",
            cache_state="unused",
            notes="Retrieval rows have no per-query timers; command setup is retained separately.",
        )
    )
    usage.extend(
        collect_jsonl_costs(
            telemetry,
            task_id="AF-017",
            rel_path="runs/premise_selection/results.jsonl",
            phase="indexing",
            arm_field="experiment_arm",
            cache_state="unused",
            notes="Premise-selection rows; per-item latency unmeasured unless elapsed_seconds is present.",
        )
    )
    usage.extend(
        collect_jsonl_costs(
            telemetry,
            task_id="AF-015",
            rel_path="runs/bridge_validation/results.jsonl",
            phase="validation",
            arm_field="experiment_arm",
            cache_state="unused",
            notes="Constructed bridge cases; native checkers were unavailable.",
        )
    )
    usage.extend(collect_unmeasured_phases(telemetry, probe))
    return usage


def write_outputs(rows: Sequence[Mapping[str, Any]], markdown: str) -> None:
    RESULTS_PATH.parent.mkdir(parents=True, exist_ok=True)
    EVIDENCE_PATH.parent.mkdir(parents=True, exist_ok=True)
    payload = "".join(canonical_dumps(row) + "\n" for row in rows)
    RESULTS_PATH.write_text(payload, encoding="utf-8")
    EVIDENCE_PATH.write_text(markdown if markdown.endswith("\n") else markdown + "\n", encoding="utf-8")


def validate_outputs(telemetry) -> dict[str, Any]:
    errors: list[str] = []
    rows = load_jsonl(RESULTS_PATH)
    if not rows:
        errors.append("results.jsonl is empty")
    kinds = {row.get("record_kind") for row in rows}
    for required in ("hardware_probe", "source_usage", "phase_total", "throughput", "reconciliation", "instrumentation_contract"):
        if required not in kinds:
            errors.append(f"missing record_kind {required}")
    phases = {row.get("phase") for row in rows if row.get("record_kind") == "phase_total"}
    if set(PAPER_COST_PHASES) - phases:
        errors.append(f"missing phase totals: {sorted(set(PAPER_COST_PHASES) - phases)}")
    for row in rows:
        if row.get("schema") != SCHEMA:
            errors.append(f"bad schema {row.get('record_id')}")
            break
        hardware = row.get("hardware")
        if row.get("record_kind") in {"source_usage", "phase_total", "hardware_probe"} and not isinstance(hardware, Mapping):
            errors.append(f"hardware missing on {row.get('record_id')}")
        if isinstance(hardware, Mapping):
            for key in ("hardware", "precision", "cache_state"):
                if not hardware.get(key):
                    errors.append(f"{row.get('record_id')} missing {key}")
        for quantity in COST_QUANTITIES:
            cell_obj = row.get(quantity)
            if not isinstance(cell_obj, Mapping):
                continue
            if cell_obj.get("unit") != COST_UNITS[quantity]:
                errors.append(f"{row.get('record_id')} {quantity} unit {cell_obj.get('unit')}")
            if cell_obj.get("kind") not in {"measured", "estimated", "provider", "unmeasured"}:
                errors.append(f"{row.get('record_id')} {quantity} kind {cell_obj.get('kind')}")
            if quantity == "gpu_seconds" and cell_obj.get("kind") == "measured" and cell_obj.get("value") == 0.0:
                cuda = hardware.get("cuda_available") if isinstance(hardware, Mapping) else None
                if cuda is not True:
                    errors.append(f"unavailable GPU recorded as measured zero: {row.get('record_id')}")
    recon_rows = [row for row in rows if row.get("record_kind") == "reconciliation"]
    if not recon_rows or not recon_rows[0].get("ok"):
        errors.append("reconciliation record missing or not ok")
    else:
        recon = recon_rows[0]
        if not recon.get("includes_setup") or not recon.get("includes_failures"):
            errors.append("reconciliation does not include setup and failures")
    cuda_rows = [row for row in rows if row.get("record_id") == "AF-020:throughput:cuda_unmeasured"]
    if not cuda_rows:
        errors.append("missing CUDA unmeasured throughput row")
    else:
        comparison = cuda_rows[0].get("comparison") or {}
        if comparison.get("value") is not None or comparison.get("status") == "measured":
            errors.append("CUDA speedup was claimed without matched actual runs")
    md = EVIDENCE_PATH.read_text(encoding="utf-8")
    for needle in (
        "seconds",
        "measured",
        "estimated",
        "provider",
        "cache",
        "hardware",
        "precision",
        "setup",
        "fail",
        "CUDA",
        "unmeasured",
        "not a zero",
    ):
        if needle.lower() not in md.lower():
            errors.append(f"cost_accounting.md missing {needle!r}")
    if errors:
        raise SystemExit("output validation failed:\n- " + "\n- ".join(errors))
    return {"ok": True, "rows": len(rows), "kinds": sorted(kinds)}


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true", help="validate existing cost outputs")
    args = parser.parse_args(argv)
    telemetry = load_telemetry()
    if args.check:
        report = validate_outputs(telemetry)
        print(canonical_dumps(report))
        return 0
    generated_at = utc_now()
    t0 = time.perf_counter()
    probe = probe_hardware(telemetry)
    contract, _contract_spans = instrumentation_contract(telemetry, probe)
    usage = collect_all(telemetry, probe)
    ledger, recon, independent = build_ledger(telemetry, usage)
    phases = phase_total_records(telemetry, recon, probe)
    throughput = throughput_records(telemetry, usage, probe)
    versions = {
        "generated_at": generated_at,
        "aggregate_costs_sha256": sha256_file(Path(__file__)),
        "runtime_telemetry_sha256": sha256_file(TELEMETRY_PATH),
        "environment_manifest_sha256": sha256_file(PAPER_ROOT / "config/environment_manifest.json"),
        "experiment_plan_sha256": sha256_file(PAPER_ROOT / "config/experiment_plan.json"),
        "telemetry_schema": telemetry.COST_ACCOUNTING_SCHEMA_VERSION,
        "python": sys.version.split()[0],
        "elapsed_seconds": round(time.perf_counter() - t0, 6),
    }
    recon_row = {
        "schema": SCHEMA,
        "record_kind": "reconciliation",
        "record_id": "AF-020:reconciliation",
        "task_id": "AF-020",
        "phase": "setup",
        "execution_status": "measured",
        "hardware": probe["hardware"],
        "ok": recon["ok"],
        "includes_setup": True,
        "includes_failures": True,
        "phase_measured_elapsed_seconds": recon["phase_measured_elapsed_seconds"],
        "record_measured_elapsed_seconds": recon["record_measured_elapsed_seconds"],
        "independent_elapsed_seconds": recon["independent_elapsed_seconds"],
        "record_count": recon["record_count"],
        "failure_record_count": recon["failure_record_count"],
        "setup_record_count": recon["setup_record_count"],
        "unmeasured_quantity_counts": recon["unmeasured_quantity_counts"],
        "mismatches": recon["mismatches"],
        "versions": versions,
    }
    rows: list[dict[str, Any]] = [probe, contract, *usage, *phases, *throughput, recon_row]
    markdown = render_markdown(
        probe=probe, recon=recon, usage=usage, throughput=throughput, versions=versions
    )
    write_outputs(rows, markdown)
    report = validate_outputs(telemetry)
    print(
        canonical_dumps(
            {
                "ok": True,
                "results": str(RESULTS_PATH.relative_to(REPO_ROOT)),
                "evidence": str(EVIDENCE_PATH.relative_to(REPO_ROOT)),
                "rows": report["rows"],
                "measured_elapsed_seconds": recon["phase_measured_elapsed_seconds"],
                "reconciliation_ok": recon["ok"],
                "cuda_available": probe["cuda_available"],
                "versions": versions,
            }
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
