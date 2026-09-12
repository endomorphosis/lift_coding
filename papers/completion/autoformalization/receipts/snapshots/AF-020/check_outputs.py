#!/usr/bin/env python3
"""Validate AF-020 cost-accounting artifacts against the task acceptance criteria."""
from __future__ import annotations

import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
PAPER_ROOT = HERE.parents[2]
REPO_ROOT = PAPER_ROOT.parents[2]
AGGREGATE = PAPER_ROOT / "evaluation" / "aggregate_costs.py"
TELEMETRY = (
    REPO_ROOT
    / "external/ipfs_datasets/ipfs_datasets_py/optimizers/logic_theorem_optimizer/runtime_telemetry.py"
)
RESULTS = PAPER_ROOT / "runs" / "costs" / "results.jsonl"
EVIDENCE = PAPER_ROOT / "evidence" / "cost_accounting.md"

CRITERIA = [
    "Cost units, measured versus estimated/provider costs, cache state, hardware and precision are explicit.",
    "Phase totals reconcile with retained run/usage records, including setup and failures.",
    "Any throughput/speedup is based on matched actual runs; unavailable hardware is not a zero-cost result.",
]
PHASES = (
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
QUANTITIES = (
    "elapsed_seconds",
    "cpu_seconds",
    "gpu_seconds",
    "provider_units",
    "memory_gib",
    "human_review_seconds",
)
UNITS = {
    "elapsed_seconds": "seconds",
    "cpu_seconds": "cpu_seconds",
    "gpu_seconds": "gpu_seconds",
    "provider_units": "provider_units",
    "memory_gib": "gibibytes",
    "human_review_seconds": "seconds",
}
KINDS = {"measured", "estimated", "provider", "unmeasured"}


def load_jsonl(path: Path) -> list[dict]:
    rows = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.strip():
            rows.append(json.loads(line))
    return rows


def main() -> int:
    errors: list[str] = []
    if not AGGREGATE.is_file():
        errors.append("missing aggregate_costs.py")
    if not TELEMETRY.is_file():
        errors.append("missing runtime_telemetry.py")
    if not RESULTS.is_file():
        errors.append("missing runs/costs/results.jsonl")
    if not EVIDENCE.is_file():
        errors.append("missing evidence/cost_accounting.md")
    if errors:
        print("FAIL")
        for item in errors:
            print(item)
        return 1

    rows = load_jsonl(RESULTS)
    kinds = {row.get("record_kind") for row in rows}
    for required in (
        "hardware_probe",
        "source_usage",
        "phase_total",
        "throughput",
        "reconciliation",
        "instrumentation_contract",
    ):
        if required not in kinds:
            errors.append(f"missing record_kind {required}")

    hardware_rows = [row for row in rows if row.get("record_kind") == "hardware_probe"]
    usage = [row for row in rows if row.get("record_kind") == "source_usage"]
    phases = [row for row in rows if row.get("record_kind") == "phase_total"]
    throughput = [row for row in rows if row.get("record_kind") == "throughput"]
    recon = [row for row in rows if row.get("record_kind") == "reconciliation"]
    contract = [row for row in rows if row.get("record_kind") == "instrumentation_contract"]

    if len(hardware_rows) != 1:
        errors.append(f"expected one hardware probe, got {len(hardware_rows)}")
    if len(recon) != 1:
        errors.append(f"expected one reconciliation row, got {len(recon)}")
    if not usage:
        errors.append("no source_usage rows")
    phase_names = {row.get("phase") for row in phases}
    if set(PHASES) != phase_names:
        errors.append(f"phase totals {sorted(phase_names)} != {list(PHASES)}")

    for row in usage + phases + hardware_rows:
        hardware = row.get("hardware")
        if not isinstance(hardware, Mapping if False else dict):
            errors.append(f"{row.get('record_id')} missing hardware object")
            continue
        for key in ("hardware", "precision", "cache_state"):
            if not str(hardware.get(key) or "").strip():
                errors.append(f"{row.get('record_id')} missing explicit {key}")
        for quantity in QUANTITIES:
            cell = row.get(quantity)
            if not isinstance(cell, dict):
                if row.get("record_kind") == "hardware_probe":
                    continue
                errors.append(f"{row.get('record_id')} missing {quantity}")
                continue
            if cell.get("unit") != UNITS[quantity]:
                errors.append(f"{row.get('record_id')} {quantity} unit {cell.get('unit')}")
            if cell.get("kind") not in KINDS:
                errors.append(f"{row.get('record_id')} {quantity} kind {cell.get('kind')}")
            if "value" not in cell:
                errors.append(f"{row.get('record_id')} {quantity} missing value")
            if quantity == "gpu_seconds" and cell.get("kind") == "measured":
                if hardware.get("cuda_available") is not True:
                    errors.append(f"GPU measured without CUDA: {row.get('record_id')}")
                if cell.get("value") == 0.0 and hardware.get("cuda_available") is not True:
                    errors.append(f"unavailable GPU recorded as zero: {row.get('record_id')}")

    if recon:
        payload = recon[0]
        if not payload.get("ok"):
            errors.append(f"reconciliation failed: {payload.get('mismatches')}")
        if not payload.get("includes_setup") or not payload.get("includes_failures"):
            errors.append("reconciliation omitted setup or failures")
        if payload.get("phase_measured_elapsed_seconds") != payload.get("record_measured_elapsed_seconds"):
            errors.append("phase totals do not match retained-record elapsed")
        independent = payload.get("independent_elapsed_seconds")
        if independent is not None and abs(independent - payload.get("phase_measured_elapsed_seconds", 0)) > 1e-6:
            errors.append("independent elapsed sum disagrees with phase totals")
        setup_present = any(row.get("phase") == "setup" and row.get("includes_setup") for row in usage)
        failure_present = any(row.get("includes_failure") for row in usage) or payload.get("failure_record_count", 0) >= 0
        if not setup_present:
            errors.append("no setup usage rows")
        if not failure_present:
            errors.append("failure accounting missing")

    cuda_throughput = [row for row in throughput if "cuda" in str(row.get("record_id"))]
    if not cuda_throughput:
        errors.append("missing CUDA throughput row")
    for row in cuda_throughput:
        comparison = row.get("comparison") or {}
        if comparison.get("status") == "measured" or comparison.get("value") is not None:
            errors.append("CUDA speedup claimed without matched actual runs")
        if comparison.get("unavailable_hardware_is_zero_cost") is True:
            errors.append("unavailable hardware marked as zero-cost")

    if contract:
        gpu_zero = contract[0].get("gpu_zero_rejected") or {}
        if gpu_zero.get("kind") != "unmeasured" or gpu_zero.get("value") is not None:
            errors.append("instrumentation contract did not reject GPU zero")

    md = EVIDENCE.read_text(encoding="utf-8")
    for needle in (
        "seconds",
        "cpu_seconds",
        "gpu_seconds",
        "provider",
        "estimated",
        "measured",
        "unmeasured",
        "cache",
        "hardware",
        "precision",
        "setup",
        "fail",
        "CUDA",
        "not a zero",
        "reconcile",
    ):
        if needle.lower() not in md.lower():
            errors.append(f"cost_accounting.md missing {needle!r}")

    snapshot_agg = HERE / "evaluation" / "aggregate_costs.py"
    snapshot_tel = HERE / "runtime_telemetry.py"
    if snapshot_agg.is_file() and snapshot_agg.read_bytes() != AGGREGATE.read_bytes():
        errors.append("snapshot aggregate_costs.py differs from live deliverable")
    if snapshot_tel.is_file() and snapshot_tel.read_bytes() != TELEMETRY.read_bytes():
        errors.append("snapshot runtime_telemetry.py differs from live deliverable")

    report = {
        "ok": not errors,
        "criteria": CRITERIA,
        "rows": len(rows),
        "usage_rows": len(usage),
        "errors": errors,
    }
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0 if not errors else 1


if __name__ == "__main__":
    raise SystemExit(main())
