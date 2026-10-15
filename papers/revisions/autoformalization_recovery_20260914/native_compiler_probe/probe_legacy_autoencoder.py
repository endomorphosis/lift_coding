#!/usr/bin/env python3
"""Load the existing pinned legacy AE and export global learned features."""
from __future__ import annotations

import argparse
import faulthandler
import hashlib
import importlib
import json
import os
from pathlib import Path
import resource
import signal
import sys
import time
import traceback

from probe import ENVIRONMENT


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", type=Path, required=True)
    parser.add_argument("--checkpoint", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    os.environ.update(ENVIRONMENT)
    sys.dont_write_bytecode = True
    cpus = sorted(os.sched_getaffinity(0))[-2:]
    os.sched_setaffinity(0, cpus)
    resource.setrlimit(resource.RLIMIT_AS, (8 * 1024**3, 8 * 1024**3))
    resource.setrlimit(resource.RLIMIT_CPU, (55, 60))
    resource.setrlimit(resource.RLIMIT_CORE, (0, 0))

    def timed_out(_signum: int, _frame: object) -> None:
        raise TimeoutError("Legacy AE load/export exceeded 55 seconds")

    signal.signal(signal.SIGALRM, timed_out)
    signal.alarm(55)
    faulthandler.dump_traceback_later(25, repeat=False)
    sys.path.insert(0, str(args.repo.resolve()))
    denied: list[str] = []

    def no_external_effects(event: str, _arguments: tuple) -> None:
        if event in {"socket.connect", "socket.bind", "subprocess.Popen", "os.system", "os.posix_spawn"}:
            denied.append(event)
            raise PermissionError(f"Legacy AE qualification forbids {event}")

    sys.addaudithook(no_external_effects)
    report: dict = {
        "schema": "autoformalization-legacy-autoencoder-load-probe/v1",
        "scope": "checkpoint_load_and_global_export_only_no_efficacy_claim",
        "executable": sys.executable,
        "repo": str(args.repo.resolve()),
        "checkpoint": str(args.checkpoint.resolve()),
        "dataset_examples_opened": False,
        "training_performed": False,
        "inference_on_examples_performed": False,
        "environment": ENVIRONMENT,
        "limits": {"wall_seconds": 60, "cpu_seconds": 55, "address_space_bytes": 8 * 1024**3, "cpu_affinity": cpus},
    }
    started = time.monotonic()
    exit_code = 0
    try:
        checkpoint_bytes = args.checkpoint.read_bytes()
        report["checkpoint_bytes"] = len(checkpoint_bytes)
        report["checkpoint_sha256"] = hashlib.sha256(checkpoint_bytes).hexdigest()
        del checkpoint_bytes
        module = importlib.import_module("benchmarks.semantic_roundtrip.constructors.autoencoder_guided")
        guidance = module.load_frozen_autoencoder_guidance(args.checkpoint)
        stable = guidance.stable_export
        report["loaded"] = True
        report["state_cid"] = guidance.state_cid
        report["state_sha256"] = guidance.state_sha256
        report["state_schema"] = guidance.state_schema
        report["declared_architecture"] = guidance.declared_architecture
        report["effective_architecture"] = guidance.effective_architecture
        report["export_id"] = stable["export_id"]
        report["feature_count"] = stable["feature_count"]
        report["sample_count"] = stable["sample_count"]
        report["sample_memory_used"] = guidance.sample_memory_used
        report["target_embedding_selection_used"] = guidance.target_embedding_selection_used
        report["excluded_categories"] = list(stable["excluded_categories"])
        report["feature_ids"] = [row["feature_id"] for row in stable["stable_features"]]
        report["checkpoint_sha256_after"] = hashlib.sha256(args.checkpoint.read_bytes()).hexdigest()
        report["checkpoint_unchanged"] = report["checkpoint_sha256_after"] == report["checkpoint_sha256"]
    except Exception as exc:
        report["loaded"] = False
        report["error"] = {"type": type(exc).__name__, "message": str(exc), "traceback": traceback.format_exc()}
        exit_code = 1
    finally:
        report["denied_external_effects"] = denied
        report["elapsed_seconds"] = time.monotonic() - started
        usage = resource.getrusage(resource.RUSAGE_SELF)
        report["peak_rss_bytes"] = usage.ru_maxrss * 1024
        report["cpu_seconds"] = usage.ru_utime + usage.ru_stime
        report["module_origins"] = {}
        for name in ("multiformats", "ipfs_datasets_py", "benchmarks.semantic_roundtrip.constructors.autoencoder_guided", "ipfs_datasets_py.optimizers.logic_theorem_optimizer.modal_autoencoder"):
            module = sys.modules.get(name)
            filename = getattr(module, "__file__", None)
            if filename:
                path = Path(filename)
                report["module_origins"][name] = {"path": str(path), "sha256": hashlib.sha256(path.read_bytes()).hexdigest()}
        report["script_sha256"] = hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(report, indent=2) + "\n")
        signal.alarm(0)
        faulthandler.cancel_dump_traceback_later()
        print(json.dumps({"output": str(args.output), "loaded": report.get("loaded"), "features": report.get("feature_count"), "error": report.get("error", {}).get("message"), "elapsed_seconds": report["elapsed_seconds"], "peak_rss_bytes": report["peak_rss_bytes"]}))
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
