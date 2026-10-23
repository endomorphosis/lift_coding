#!/usr/bin/env python3
"""Bounded native compiler qualification on newly constructed inputs only."""
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


ENVIRONMENT = {
    "IPFS_DATASETS_AUTO_INSTALL": "false",
    "IPFS_KIT_AUTO_INSTALL_DEPS": "0",
    "IPFS_DATASETS_PY_MINIMAL_IMPORTS": "1",
    "IPFS_DATASETS_PY_BENCHMARK": "1",
    "IPFS_DATASETS_PY_ENABLE_LLM_IMPORTS": "0",
    "HF_HUB_OFFLINE": "1",
    "TRANSFORMERS_OFFLINE": "1",
    "CUDA_VISIBLE_DEVICES": "",
    "OMP_NUM_THREADS": "1",
    "OPENBLAS_NUM_THREADS": "1",
    "MKL_NUM_THREADS": "1",
    "NUMEXPR_NUM_THREADS": "1",
    "PYTHONDONTWRITEBYTECODE": "1",
}

CASES = (
    ("constructed_obligation", "Company A shall submit backup report.", "O"),
    ("constructed_permission", "Company A may submit backup report.", "P"),
    ("constructed_prohibition", "Company A must not submit backup report.", "F"),
    ("constructed_shall_not", "The agency shall not file notice.", "F"),
    ("constructed_no_obligation", "The agency is not required to file notice.", "not_O"),
    ("constructed_exception_window", "Company A shall submit backup report within 10 days unless emergency.", "O"),
)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--extra-python-path", type=Path)
    args = parser.parse_args()
    for key, value in ENVIRONMENT.items():
        os.environ[key] = value
    sys.dont_write_bytecode = True
    cpus = sorted(os.sched_getaffinity(0))[-2:]
    os.sched_setaffinity(0, cpus)
    resource.setrlimit(resource.RLIMIT_AS, (8 * 1024**3, 8 * 1024**3))
    resource.setrlimit(resource.RLIMIT_CPU, (55, 60))
    resource.setrlimit(resource.RLIMIT_CORE, (0, 0))
    def timed_out(_signum: int, _frame: object) -> None:
        raise TimeoutError("Native compiler qualification exceeded 55 seconds")

    signal.signal(signal.SIGALRM, timed_out)
    signal.alarm(55)
    faulthandler.dump_traceback_later(25, repeat=False)
    sys.path.insert(0, str(args.repo.resolve()))
    if args.extra_python_path:
        sys.path.insert(1, str(args.extra_python_path.resolve()))
    denied: list[str] = []

    def no_external_effects(event: str, _arguments: tuple) -> None:
        if event in {"socket.connect", "socket.bind", "subprocess.Popen", "os.system", "os.posix_spawn"}:
            denied.append(event)
            raise PermissionError(f"Native compiler probe forbids {event}")

    sys.addaudithook(no_external_effects)
    started = time.monotonic()
    report: dict = {
        "schema": "autoformalization-native-compiler-probe/v1",
        "scope": "constructed_development_qualification_only",
        "final_dataset_opened": False,
        "checkpoint_loaded": False,
        "replica_used": False,
        "executable": sys.executable,
        "repo": str(args.repo.resolve()),
        "extra_python_path": str(args.extra_python_path) if args.extra_python_path else None,
        "environment": ENVIRONMENT,
        "limits": {"wall_seconds": 60, "cpu_seconds": 55, "address_space_bytes": 8 * 1024**3, "cpu_affinity": cpus},
        "cases": [],
    }
    exit_code = 0
    try:
        importlib.import_module("multiformats")
        compiler_module = importlib.import_module("ipfs_datasets_py.logic.legal_ir.canonical_compiler")
        contracts = importlib.import_module("ipfs_datasets_py.logic.legal_ir.canonical_contracts")
        # Import explicitly so a dependency error is retained rather than hidden
        # behind the public compiler's intentionally generic unavailable result.
        importlib.import_module("ipfs_datasets_py.logic.deontic.converter")
        vocabulary = contracts.CanonicalAtomVocabulary(
            actors=("agency", "company_a"),
            actions=("file", "submit", "withdraw"),
            objects=("backup_report", "notice"),
            qualifiers=("emergency", "natural_disaster", "within_10_days"),
        )
        report["atom_vocabulary"] = vocabulary.to_dict()
        report["compiler_config"] = compiler_module.compiler_configuration()
        compiler = compiler_module.TypedDeonticCanonicalCompiler()
        report["compiler_identity"] = compiler.identity
        for case_id, source, expected in CASES:
            began = time.monotonic()
            case = {"case_id": case_id, "source_text": source, "expected_modality_check": expected}
            try:
                request = contracts.CompilerRequest(source_text=source, request_id=case_id, atom_vocabulary=vocabulary)
                result = compiler.compile(request)
                payload = result.to_dict()
                case["result"] = payload
                ir = payload.get("canonical_ir") or {}
                modalities = [rule.get("modality") for rule in ir.get("rules", [])]
                case["observed_modalities"] = modalities
                case["constructed_modality_check_passed"] = (
                    bool(modalities) and set(modalities) == {expected}
                    if expected != "not_O" else "O" not in modalities
                )
            except Exception as exc:
                case["error"] = {"type": type(exc).__name__, "message": str(exc), "traceback": traceback.format_exc()}
                exit_code = 1
            case["elapsed_seconds"] = time.monotonic() - began
            report["cases"].append(case)
    except Exception as exc:
        report["initialization_error"] = {"type": type(exc).__name__, "message": str(exc), "traceback": traceback.format_exc()}
        exit_code = 1
    finally:
        report["denied_external_effects"] = denied
        report["elapsed_seconds"] = time.monotonic() - started
        usage = resource.getrusage(resource.RUSAGE_SELF)
        report["peak_rss_bytes"] = usage.ru_maxrss * 1024
        report["cpu_seconds"] = usage.ru_utime + usage.ru_stime
        report["module_origins"] = {}
        for name in ("multiformats", "ipfs_datasets_py", "ipfs_datasets_py.logic.legal_ir.canonical_compiler", "ipfs_datasets_py.logic.legal_ir.canonical_contracts", "ipfs_datasets_py.logic.deontic.converter", "ipfs_datasets_py.logic.deontic.utils.deontic_parser"):
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
        print(json.dumps({"output": str(args.output), "cases": len(report["cases"]), "error": report.get("initialization_error", {}).get("message"), "elapsed_seconds": report["elapsed_seconds"], "peak_rss_bytes": report["peak_rss_bytes"]}))
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
