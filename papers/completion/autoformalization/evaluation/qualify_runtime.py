#!/usr/bin/env python3
"""Worker-boundary runtime/input qualification smoke for AF-027.

This command is the executable smoke that reproduces qualification in the
actual worker: Python/Torch/checker visibility, model budgets, scientific
gateway model-to-target calls, independent native checker receipts, A–D
development routes, E unavailability, and review-binding commitments.

It does not assume host ``~/.elan`` or ``~/.local/bin`` visibility. It records
the process PATH, optional operator validation PATH, and default sealed PATH
separately. Standard library plus optional Torch/NumPy probes.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import subprocess
import sys
import tempfile
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping, Sequence


HERE = Path(__file__).resolve().parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))

from pipeline_arms import (  # noqa: E402
    DEVELOPMENT_BRIDGE_SOURCE,
    DEVELOPMENT_SOURCE,
    IsolationError,
    PIPELINE_ARMS,
    build_config,
    build_environment,
    execute_arm,
    inspect_sources,
    isolation_tests,
    materialize as materialize_arms,
    probe_native_checkers,
    probe_python_packages,
    run_native_checker,
    sample_bridge_evidence,
    sha256_file,
    sha256_obj,
    sha256_text,
    write_json,
)
from review_import import materialize as materialize_review  # noqa: E402
from scientific_gateway import (  # noqa: E402
    gateway_identity,
    model_to_target,
    public_credential_status,
)


SCHEMA_MANIFEST = "autoformalization-runtime-input-manifest/v1"
SCHEMA_QUALIFICATION = "autoformalization-runtime-qualification/v1"
TASK_ID = "AF-027"
SEALED_PATH = "/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin"
PAPER_ROOT = HERE.parent
REPO_ROOT = PAPER_ROOT.parents[2]
QUAL_DIR = PAPER_ROOT / "evidence" / "runtime_qualification"


def canonical_dumps(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False)


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.tmp-{os.getpid()}")
    temporary.write_text(text, encoding="utf-8")
    temporary.replace(path)


def write_jsonl(path: Path, rows: Sequence[Mapping[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = "".join(canonical_dumps(row) + "\n" for row in rows)
    temporary = path.with_name(f".{path.name}.tmp-{os.getpid()}")
    temporary.write_text(payload, encoding="utf-8")
    temporary.replace(path)


def capture_command(argv: Sequence[str], *, log_stem: str, cwd: Path) -> dict[str, Any]:
    started_at = utc_now()
    t0 = time.perf_counter()
    completed = subprocess.run(
        list(argv),
        cwd=str(cwd),
        capture_output=True,
        text=True,
        check=False,
    )
    finished_at = utc_now()
    stdout_path = QUAL_DIR / "logs" / f"{log_stem}.stdout.log"
    stderr_path = QUAL_DIR / "logs" / f"{log_stem}.stderr.log"
    meta_path = QUAL_DIR / "logs" / f"{log_stem}.meta.json"
    write_text(stdout_path, completed.stdout or "")
    write_text(stderr_path, completed.stderr or "")
    record = {
        "argv": list(argv),
        "cwd": ".",
        "exit_code": completed.returncode,
        "started_at": started_at,
        "finished_at": finished_at,
        "elapsed_ms": round((time.perf_counter() - t0) * 1000.0, 3),
        "log": str(stdout_path.relative_to(REPO_ROOT)),
        "stderr_log": str(stderr_path.relative_to(REPO_ROOT)),
    }
    write_json(meta_path, record)
    record["meta"] = str(meta_path.relative_to(REPO_ROOT))
    return record


def probe_runtime() -> dict[str, Any]:
    checkers = probe_native_checkers()
    packages = probe_python_packages()
    path = os.environ.get("PATH", "")
    validation_path = os.environ.get("IPFS_ACCELERATE_AGENT_VALIDATION_PATH")
    return {
        "schema": "autoformalization-worker-runtime/v1",
        "observed_at": utc_now(),
        "python": {
            "executable": sys.executable,
            "version": sys.version.split()[0],
            "version_string": sys.version,
            "path": sys.path[:8],
        },
        "process": {
            "path": path,
            "home": os.environ.get("HOME"),
            "validation_path": validation_path,
            "default_sealed_path": SEALED_PATH,
            "process_path_equals_default_sealed": path == SEALED_PATH,
            "process_path_equals_validation_path": bool(validation_path) and path == validation_path,
        },
        "packages": packages,
        "native_checkers": checkers,
        "host_assumed_paths_probed": {
            "elan_lean": "/home/barberb/.elan/toolchains/leanprover--lean4---v4.33.1/bin/lean",
            "local_z3": "/home/barberb/.local/bin/z3",
            "elan_lean_exists": Path("/home/barberb/.elan/toolchains/leanprover--lean4---v4.33.1/bin/lean").is_file(),
            "local_z3_exists": Path("/home/barberb/.local/bin/z3").is_file(),
            "used": False,
            "note": "Host AF-003 paths are recorded as not worker-visible; qualification uses worker-resolved binaries.",
        },
        "model_budget": {
            "gpu_or_model_service_slots": 1,
            "memory_gib": 16,
            "cached_leanstral_excluded": True,
            "served_grok_primary": "grok-4.6",
            "codex_fallback": "gpt-5.6-terra/high quota-only",
        },
    }


def independent_checker_suite() -> list[dict[str, Any]]:
    lean = shutil.which("lean") or "/home/barberb/.local/share/vericodegen-research-runtime/bin/lean"
    z3 = shutil.which("z3") or "/home/barberb/.local/share/vericodegen-research-runtime/bin/z3"
    ok = "theorem AF027_ok (P : Prop) (h : P) : P := h\n"
    bad = "example : False := trivial\n"
    smt = (
        "(set-logic QF_LIA)\n"
        "(declare-const x Int)\n"
        "(assert (> x 1))\n"
        "(assert (< x 0))\n"
        "(check-sat)\n"
    )
    receipts = []
    with tempfile.TemporaryDirectory(prefix="af027-checker-") as tmp:
        tmp_path = Path(tmp)
        ok_path = tmp_path / "ok.lean"
        bad_path = tmp_path / "fail.lean"
        ok_path.write_text(ok, encoding="utf-8")
        bad_path.write_text(bad, encoding="utf-8")
        write_text(QUAL_DIR / "development" / "ok.lean", ok)
        write_text(QUAL_DIR / "development" / "fail.lean", bad)
        write_text(QUAL_DIR / "development" / "sentinel.smt2", smt)
        receipts.append(run_native_checker(
            name="lean",
            argv=[lean, str(ok_path)],
            source_text=ok,
            purpose="independent_native_checker_success",
        ))
        receipts.append(run_native_checker(
            name="lean",
            argv=[lean, str(bad_path)],
            source_text=bad,
            purpose="independent_native_checker_explicit_failure",
        ))
        receipts.append(run_native_checker(
            name="z3",
            argv=[z3, "-in", "-smt2"],
            stdin_text=smt,
            source_text=smt,
            purpose="independent_solver_local_unsat",
        ))
    return receipts


def qualify(root: Path) -> dict[str, Any]:
    QUAL_DIR.mkdir(parents=True, exist_ok=True)
    (QUAL_DIR / "logs").mkdir(parents=True, exist_ok=True)
    (QUAL_DIR / "development").mkdir(parents=True, exist_ok=True)
    runtime = probe_runtime()
    write_json(QUAL_DIR / "worker_runtime.json", runtime)
    write_json(QUAL_DIR / "development" / "source.json", {
        "natural_selection": {
            "source_id": DEVELOPMENT_SOURCE["source_id"],
            "split": DEVELOPMENT_SOURCE["split"],
            "record_id": DEVELOPMENT_SOURCE["record_id"],
            "citation": DEVELOPMENT_SOURCE["citation"],
            "path": DEVELOPMENT_SOURCE["path"],
            "text_sha256": sha256_text(DEVELOPMENT_SOURCE["text"]),
            "final_test": False,
        },
        "constructed_control": {
            "source_id": DEVELOPMENT_BRIDGE_SOURCE["source_id"],
            "split": DEVELOPMENT_BRIDGE_SOURCE["split"],
            "text_sha256": sha256_text(DEVELOPMENT_BRIDGE_SOURCE["text"]),
            "final_test": False,
        },
        "gold_exposed": False,
        "holdout_labels_exposed": False,
    })
    environment = build_environment(root)
    inspected = inspect_sources(root)
    isolation = isolation_tests(environment)
    config_summary = materialize_arms(root, config_path=PAPER_ROOT / "config" / "pipeline_arms.json")
    review_summary = materialize_review(root)
    identity = gateway_identity()
    credential = public_credential_status()
    write_json(QUAL_DIR / "scientific_gateway_identity.json", {
        "identity": identity,
        "credential": credential,
    })
    checker_receipts = independent_checker_suite()
    write_jsonl(QUAL_DIR / "native_checker_receipts.jsonl", checker_receipts)
    arm_rows = []
    for arm_id in PIPELINE_ARMS:
        request: dict[str, Any] = {"source_id": f"qualify-{arm_id.lower()}", "experiment_arm": arm_id}
        if arm_id in {"B", "C"}:
            request.update({
                "source_id": DEVELOPMENT_SOURCE["source_id"],
                "source_text": DEVELOPMENT_SOURCE["text"],
            })
        if arm_id in {"A", "D"}:
            request.update({
                "source_id": DEVELOPMENT_BRIDGE_SOURCE["source_id"],
                "source_text": DEVELOPMENT_BRIDGE_SOURCE["text"],
            })
        if arm_id == "D":
            request["bridge_evidence"] = sample_bridge_evidence()
        result = execute_arm(arm_id, request, environment=environment)
        arm_rows.append(result)
    a_row = next(row for row in arm_rows if row["arm"] == "A")
    model_receipt = dict(a_row.get("gateway_receipt") or {})
    if not model_receipt:
        raise RuntimeError("arm A did not retain a scientific-gateway receipt")
    write_json(QUAL_DIR / "model_call_receipt.json", model_receipt)
    write_text(
        QUAL_DIR / "development" / "model_target.lean",
        str(model_receipt.get("output_text") or "") + "\n",
    )
    write_json(QUAL_DIR / "arm_development_runs.json", {
        "schema": "autoformalization-arm-development-runs/v1",
        "task_id": TASK_ID,
        "observed_at": utc_now(),
        "table6_cells_measured": 0,
        "any_performance_claim_admitted": any(row.get("claim_admissible") for row in arm_rows),
        "arms": arm_rows,
    })
    write_json(QUAL_DIR / "isolation_report.json", {
        "all_isolation_passed": all(item["passed"] for item in isolation),
        "tests": isolation,
        "inspected_sources": inspected,
    })
    write_json(QUAL_DIR / "review_binding_verification.json", review_summary["verification"])
    smoke = {
        "command": [
            sys.executable,
            "papers/completion/autoformalization/evaluation/qualify_runtime.py",
            "smoke",
        ],
        "cwd": ".",
        "reproduces": [
            "worker_runtime",
            "python_torch_numpy_visibility",
            "native_checker_visibility",
            "scientific_gateway_model_to_target",
            "independent_native_checker",
            "A_D_development_routes",
            "E_unavailable",
            "review_binding",
            "receipt_accounting",
        ],
        "worker_boundary": True,
        "default_sealed_path": SEALED_PATH,
    }
    write_json(QUAL_DIR / "smoke.json", smoke)
    failures = []
    if model_receipt.get("execution_status") != "measured":
        failures.append("model_to_target_not_measured")
    if not any(row.get("purpose") == "independent_native_checker_explicit_failure" and row.get("execution_status") == "failure" for row in checker_receipts):
        failures.append("missing_explicit_checker_failure")
    if not any(row.get("purpose") == "independent_native_checker_success" and row.get("execution_status") == "measured" for row in checker_receipts):
        failures.append("missing_independent_checker_success")
    e_row = next(row for row in arm_rows if row["arm"] == "E")
    if e_row.get("execution_status") != "unavailable" or e_row.get("measured_credit"):
        failures.append("E_received_credit_or_ran")
    for arm_id in ("A", "B", "C", "D"):
        row = next(item for item in arm_rows if item["arm"] == arm_id)
        if row.get("execution_status") in {"unavailable", "no_run"} and not row.get("preprocessing"):
            failures.append(f"{arm_id}_unconditional_unavailable")
        if row.get("claim_admissible") or row.get("synthetic_success"):
            failures.append(f"{arm_id}_admitted_claim")
        if not row.get("preprocessing", {}).get("charged"):
            failures.append(f"{arm_id}_preprocessing_not_charged")
    if not runtime["packages"]["torch"]["available"] or not runtime["packages"]["numpy"]["available"]:
        failures.append("torch_or_numpy_not_worker_visible")
    if not runtime["native_checkers"]["any_native_checker_usable"]:
        failures.append("no_worker_visible_native_checker")
    input_manifest = {
        "schema": SCHEMA_MANIFEST,
        "task_id": TASK_ID,
        "created_at": utc_now(),
        "worker_runtime": str((QUAL_DIR / "worker_runtime.json").relative_to(REPO_ROOT)),
        "scientific_gateway": str((QUAL_DIR / "scientific_gateway_identity.json").relative_to(REPO_ROOT)),
        "model_call": str((QUAL_DIR / "model_call_receipt.json").relative_to(REPO_ROOT)),
        "native_checkers": str((QUAL_DIR / "native_checker_receipts.jsonl").relative_to(REPO_ROOT)),
        "arm_runs": str((QUAL_DIR / "arm_development_runs.json").relative_to(REPO_ROOT)),
        "review_binding": "papers/completion/autoformalization/data/review_binding_manifest.json",
        "review_packet_schema": "papers/completion/autoformalization/data/review_packet_schema.json",
        "smoke_command": smoke["command"],
        "python": runtime["python"],
        "packages": {
            "torch": runtime["packages"]["torch"].get("version"),
            "numpy": runtime["packages"]["numpy"].get("version"),
        },
        "model_budget": runtime["model_budget"],
        "receipt_accounting": {
            "model_call_receipt_sha256": model_receipt.get("receipt_sha256"),
            "served_model": (model_receipt.get("served_identity") or {}).get("served_model"),
            "response_id": (model_receipt.get("served_identity") or {}).get("response_id"),
            "native_checker_receipts": len(checker_receipts),
            "arm_results": {row["arm"]: row["result_sha256"] for row in arm_rows},
        },
        "final_test_used": False,
        "gold_used": False,
    }
    write_json(QUAL_DIR / "input_manifest.json", input_manifest)
    qualification = {
        "schema": SCHEMA_QUALIFICATION,
        "task_id": TASK_ID,
        "observed_at": utc_now(),
        "passed": not failures,
        "failures": failures,
        "model_call": {
            "execution_status": model_receipt.get("execution_status"),
            "served_model": (model_receipt.get("served_identity") or {}).get("served_model"),
            "response_id": (model_receipt.get("served_identity") or {}).get("response_id"),
            "elapsed_ms": (model_receipt.get("timing") or {}).get("elapsed_ms"),
            "failures": model_receipt.get("failures") or [],
            "receipt_sha256": model_receipt.get("receipt_sha256"),
        },
        "independent_native_checker": {
            "receipts": len(checker_receipts),
            "success": any(row.get("purpose") == "independent_native_checker_success" and row.get("execution_status") == "measured" for row in checker_receipts),
            "explicit_failure": any(row.get("purpose") == "independent_native_checker_explicit_failure" and row.get("execution_status") == "failure" for row in checker_receipts),
        },
        "arms": {
            row["arm"]: {
                "execution_status": row["execution_status"],
                "result_kind": row["result_kind"],
                "measured_credit": row.get("measured_credit"),
                "preprocessing_charged": bool((row.get("preprocessing") or {}).get("charged")),
            }
            for row in arm_rows
        },
        "config_sha256": config_summary["config_sha256"],
        "review_binding_sha256": review_summary["binding_sha256"],
        "table6_cells_measured": 0,
    }
    write_json(QUAL_DIR / "qualification.json", qualification)
    return qualification


def smoke(root: Path) -> dict[str, Any]:
    qualification = qualify(root)
    smoke_path = QUAL_DIR / "smoke.json"
    payload = json.loads(smoke_path.read_text(encoding="utf-8")) if smoke_path.is_file() else {}
    payload["last_run"] = {
        "passed": qualification["passed"],
        "observed_at": qualification["observed_at"],
        "model_call": qualification["model_call"],
        "independent_native_checker": qualification["independent_native_checker"],
    }
    write_json(smoke_path, payload)
    return qualification


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    probe = sub.add_parser("probe", help="Record worker-visible runtime only")
    probe.add_argument("--root", type=Path, default=REPO_ROOT)
    qual = sub.add_parser("qualify", help="Run full development qualification")
    qual.add_argument("--root", type=Path, default=REPO_ROOT)
    smk = sub.add_parser("smoke", help="Executable smoke reproducing qualification")
    smk.add_argument("--root", type=Path, default=REPO_ROOT)
    args = parser.parse_args(argv)
    root = Path(args.root).resolve()
    if args.command == "probe":
        runtime = probe_runtime()
        QUAL_DIR.mkdir(parents=True, exist_ok=True)
        write_json(QUAL_DIR / "worker_runtime.json", runtime)
        print(canonical_dumps({
            "python": runtime["python"]["version"],
            "torch": runtime["packages"]["torch"].get("version"),
            "numpy": runtime["packages"]["numpy"].get("version"),
            "any_native_checker_usable": runtime["native_checkers"]["any_native_checker_usable"],
            "path": runtime["process"]["path"],
        }))
        return 0
    qualification = smoke(root) if args.command == "smoke" else qualify(root)
    print(canonical_dumps({
        "passed": qualification["passed"],
        "failures": qualification["failures"],
        "model_call": qualification["model_call"],
        "independent_native_checker": qualification["independent_native_checker"],
        "arms": qualification["arms"],
        "table6_cells_measured": 0,
    }))
    return 0 if qualification["passed"] else 1


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except IsolationError as exc:
        print(f"qualify_runtime: isolation: {exc}", flush=True)
        raise SystemExit(1)
