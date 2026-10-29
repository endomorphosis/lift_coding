#!/usr/bin/env python3
"""Bounded real accelerator SDK health/metrics observations; no inference."""
from __future__ import annotations

import argparse
import asyncio
import datetime as dt
import hashlib
import importlib.util
import json
import math
import os
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
SCHEMA = "swissknife.native-accelerate-observation-result.v1"
SDK_FILES = {
    "HealthChecker.check_detailed": (
        "external/ipfs_accelerate/ipfs_accelerate_py/hf_model_server/monitoring/health.py",
        "ipfs_accelerate_py.hf_model_server.monitoring.health", "HealthChecker", "check_detailed"),
    "PrometheusMetrics.generate_metrics": (
        "external/ipfs_accelerate/ipfs_accelerate_py/hf_model_server/monitoring/metrics.py",
        "ipfs_accelerate_py.hf_model_server.monitoring.metrics", "PrometheusMetrics", "generate_metrics"),
}
MAX_OUTPUT_BYTES = 65536


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def load_sdk(root, tool):
    relative, module_name, class_name, method = SDK_FILES[tool]
    path = root / relative
    if path.is_symlink() or path.resolve() != path.absolute() or not path.is_file():
        raise ValueError("SDK observation source must be its regular pinned checkout file")
    before = sha(path)
    spec = importlib.util.spec_from_file_location(module_name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError("Actual SDK observation module is unavailable")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    if Path(module.__file__).resolve() != path or sha(path) != before:
        raise RuntimeError("SDK observation source identity changed during import")
    return module, class_name, method, relative, before


def observe(tool, *, root=ROOT):
    if tool not in SDK_FILES:
        raise ValueError("Unsupported bounded SDK observation")
    root = Path(root).resolve()
    module, class_name, method, relative, before = load_sdk(root, tool)
    if tool == "HealthChecker.check_detailed":
        # No fake model loader or detector is injected. This is the SDK's
        # actual liveness check; the service adds its separate real readiness.
        payload = asyncio.run(module.HealthChecker().check_detailed())
        if (not isinstance(payload, dict) or payload.get("status") not in {"healthy", "degraded"}
                or not isinstance(payload.get("timestamp"), str)):
            raise RuntimeError("SDK detailed health returned an invalid observation")
        scope = "sdk_liveness; model_loading_and_hardware_capacity_not_measured"
    else:
        import psutil
        if module.HAVE_PROMETHEUS_CLIENT is not True:
            raise RuntimeError("The actual Prometheus client is required; noop metrics are forbidden")
        utilization = psutil.cpu_percent(interval=0.1)
        memory = psutil.virtual_memory()
        if (type(utilization) not in {int, float} or not math.isfinite(utilization)
                or not 0 <= utilization <= 100 or not math.isfinite(memory.percent)
                or not 0 <= memory.percent <= 100 or memory.total <= 0):
            raise RuntimeError("OS telemetry returned invalid measurements")
        metrics = module.PrometheusMetrics()
        metrics.update_hardware_utilization("cpu", "host_aggregate", utilization)
        raw = metrics.generate_metrics()
        if not isinstance(raw, bytes) or not 0 < len(raw) <= 49152:
            raise RuntimeError("Actual SDK Prometheus output exceeds its bounded size")
        payload = {"utilization": float(utilization), "cpu_percent": float(utilization),
                   "memory_percent": float(memory.percent), "memory_used_bytes": memory.used,
                   "memory_total_bytes": memory.total, "gpu_utilization": None,
                   "metrics": raw.decode("utf-8"), "metrics_content_type": metrics.get_content_type(),
                   "timestamp": dt.datetime.now(dt.timezone.utc).isoformat(),
                   "measurement_source": "psutil host CPU/memory plus actual SDK Prometheus exporter",
                   "utilization_unit": "percent", "memory_unit": "bytes",
                   "prometheus_process_scope": "this bounded observation subprocess; not the inference worker"}
        scope = "host_cpu_memory_and_observation_process"
    if sha(root / relative) != before:
        raise RuntimeError("SDK observation source changed during execution")
    return {"schema": SCHEMA, "tool": tool, "result": payload,
            "sdk_class": SDK_FILES[tool][1] + "." + class_name,
            "sdk_method": method, "sdk_source_path": relative, "sdk_source_sha256": before,
            "observation_source_sha256": sha(Path(__file__)), "pid": os.getpid(), "parent_pid": os.getppid(),
            "scope": scope, "inference_executed": False, "simulated": False, "external_provider_called": False}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--tool", choices=list(SDK_FILES), required=True)
    args = parser.parse_args()
    value = observe(args.tool)
    encoded = json.dumps(value, ensure_ascii=False, allow_nan=False).encode()
    if len(encoded) > MAX_OUTPUT_BYTES:
        raise ValueError("SDK observation exceeds its response bound")
    sys.stdout.write(encoded.decode() + "\n")


if __name__ == "__main__":
    main()
