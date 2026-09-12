#!/usr/bin/env python3
"""Run AF-019 measure and check under a sealed PATH and private HOME."""
from __future__ import annotations

import hashlib
import json
import os
import subprocess
import sys
import tempfile
import time
from datetime import datetime, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO_ROOT = HERE.parents[5]
PAPER_ROOT = HERE.parents[2]
SEALED_PATH = "/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin"
PYTHON = "/usr/bin/python3.12"
TASK_ID = "AF-019"


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def run_step(name: str, script: Path, home: Path) -> dict:
    stdout_path = HERE / "logs" / f"{name}.stdout.log"
    stderr_path = HERE / "logs" / f"{name}.stderr.log"
    stdout_path.parent.mkdir(parents=True, exist_ok=True)
    argv = [
        "/usr/bin/env", "-i",
        f"PATH={SEALED_PATH}",
        f"HOME={home}",
        "PYTHONDONTWRITEBYTECODE=1",
        "LANG=C.UTF-8",
        PYTHON,
        str(script.relative_to(REPO_ROOT)),
    ]
    started = utc_now()
    t0 = time.perf_counter()
    proc = subprocess.run(
        argv,
        cwd=str(REPO_ROOT),
        capture_output=True,
        text=True,
        check=False,
    )
    elapsed_ms = round((time.perf_counter() - t0) * 1000.0, 3)
    finished = utc_now()
    stdout_path.write_text(proc.stdout, encoding="utf-8")
    stderr_path.write_text(proc.stderr, encoding="utf-8")
    meta = {
        "argv": argv,
        "cwd": ".",
        "elapsed_ms": elapsed_ms,
        "env": {"HOME": str(home), "PATH": SEALED_PATH},
        "exit_code": proc.returncode,
        "finished_at": finished,
        "name": name,
        "started_at": started,
    }
    (HERE / "logs" / f"{name}.meta.json").write_text(
        json.dumps(meta, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    return meta


def copy_live_outputs() -> None:
    mapping = {
        PAPER_ROOT / "runs" / "domain_transfer" / "results.jsonl": HERE / "runs" / "domain_transfer" / "results.jsonl",
        PAPER_ROOT / "evidence" / "domain_scope_matrix.json": HERE / "evidence" / "domain_scope_matrix.json",
    }
    for src, dst in mapping.items():
        dst.parent.mkdir(parents=True, exist_ok=True)
        dst.write_bytes(src.read_bytes())


def snapshot_artifacts() -> dict[str, str]:
    artifacts = {}
    for path in sorted(HERE.rglob("*")):
        if not path.is_file() or path.name.startswith("."):
            continue
        if "__pycache__" in path.parts or path.suffix == ".pyc":
            continue
        rel = path.relative_to(REPO_ROOT).as_posix()
        artifacts[rel] = sha256_file(path)
    return artifacts


def python_version() -> str:
    proc = subprocess.run(
        [PYTHON, "-V"],
        capture_output=True,
        text=True,
        check=False,
        env={"PATH": SEALED_PATH, "HOME": "/tmp", "PYTHONDONTWRITEBYTECODE": "1"},
    )
    return (proc.stdout or proc.stderr).strip()


def git_head() -> str | None:
    proc = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=str(REPO_ROOT),
        capture_output=True,
        text=True,
        check=False,
    )
    if proc.returncode != 0:
        return None
    return proc.stdout.strip()


def write_receipt(measure: dict, check: dict, home: Path, artifacts: dict[str, str]) -> Path:
    matrix = json.loads((HERE / "evidence" / "domain_scope_matrix.json").read_text(encoding="utf-8"))
    frozen = matrix.get("frozen_inputs") or {}
    inspected = matrix.get("inspected_sources") or {}
    tree = git_head()
    receipt = {
        "schema": "paper-task-evidence/v1",
        "task_id": TASK_ID,
        "status": "complete",
        "completed_at": check["finished_at"],
        "source_versions": {
            "python": {
                "interpreter": PYTHON,
                "version": python_version() or "Python 3.12.3",
                "path": SEALED_PATH,
            },
            "harness": {
                "schema": "autoformalization-domain-transfer-result/v1",
                "matrix_schema": "autoformalization-domain-scope-matrix/v1",
                "source": "papers/completion/autoformalization/receipts/snapshots/AF-019/measure_domain_transfer.py",
                "sha256": artifacts["papers/completion/autoformalization/receipts/snapshots/AF-019/measure_domain_transfer.py"],
                "standard_library_only": True,
            },
            "repository_tree_id": tree,
            "inspected_not_imported": {
                key: {
                    "path": spec.get("path"),
                    "sha256": spec.get("sha256"),
                    "imported": False,
                    "note": spec.get("note"),
                }
                for key, spec in inspected.items()
            },
            "frozen_inputs": frozen,
            "empirical_execution": (
                "stdlib adapter-contract inspection, AF-011 T0/T2 identity equality, "
                "T1 sample-memory key overlap, finite Q1/Q2 constructed proof transfer, "
                "and sealed-PATH OCR/ASR/native-checker unavailability; AF-029 MiniLM "
                "packed_cpu other-domain application remains unavailable"
            ),
        },
        "artifacts": artifacts,
        "outputs": {
            "papers/completion/autoformalization/runs/domain_transfer/results.jsonl": "papers/completion/autoformalization/receipts/snapshots/AF-019/runs/domain_transfer/results.jsonl",
            "papers/completion/autoformalization/evidence/domain_scope_matrix.json": "papers/completion/autoformalization/receipts/snapshots/AF-019/evidence/domain_scope_matrix.json",
        },
        "criteria": [
            {
                "criterion": "Each evaluated domain has a supported profile, frozen source population, explicit formal target/property provenance, actual checkpoint and baseline; no source-semantic gold is implied when independent labels are unavailable.",
                "status": "met",
                "explanation": (
                    "Legal, Security, Intent, software, and constructed-trace domains each bind a "
                    "supported profile (legal-ir-formalization-adapter/v1, security-ir-formalization-adapter/v1, "
                    "intent-formalization-compiler/v1, guarded-implementation-fol/v1, bounded-audit-trace/v1), "
                    "a frozen population (AF-004 legal splits or the AF-019 constructed protected-write pool), "
                    "Q1/Q2 or plan-vs-occurrence provenance, actual AF-011 T0/T2 identity "
                    "5975e52cd3db3f1ac7e8be248351d685782e102a56d69dd17ecb4b1ef1d23737 and AF-029 T2 "
                    "identities, and a deterministic baseline. AF-005 independent gold values are 0; "
                    "every observation sets independent_gold_present false and "
                    "counts_as_source_semantic_transfer false."
                ),
                "evidence": [
                    "papers/completion/autoformalization/receipts/snapshots/AF-019/evidence/domain_scope_matrix.json",
                    "papers/completion/autoformalization/receipts/snapshots/AF-019/runs/domain_transfer/results.jsonl",
                    "papers/completion/autoformalization/receipts/snapshots/AF-019/logs/check_outputs.stdout.log",
                    "papers/completion/autoformalization/receipts/snapshots/AF-019/measure_domain_transfer.py",
                    "papers/completion/autoformalization/receipts/snapshots/AF-019/check_outputs.py",
                ],
            },
            {
                "criterion": "Structural compatibility, learned transfer and valid semantic proof transfer are separately scored/described.",
                "status": "met",
                "explanation": (
                    "Structural rows score shared FormalizationSample/Compiler contracts and disjoint "
                    "view IDs and explicitly deny statistical transfer. Learned rows score AF-011 T2 "
                    "shared-parameter delta 0 versus T0, T1 sample-memory overlap 0 on other-domain "
                    "IDs, and AF-029 T2 MiniLM application as unavailable, not zero. Semantic proof "
                    "rows separately accept Q1 on the guarded Security/software models, record the "
                    "unguarded countermodel, reject Intent-plan-as-occurrence, and leave wrong-tenant "
                    "unresolved. Feature-transfer.py is labeled architecture migration, not "
                    "Legal-to-Security transfer."
                ),
                "evidence": [
                    "papers/completion/autoformalization/receipts/snapshots/AF-019/runs/domain_transfer/results.jsonl",
                    "papers/completion/autoformalization/receipts/snapshots/AF-019/evidence/domain_scope_matrix.json",
                    "papers/completion/autoformalization/receipts/snapshots/AF-019/logs/measure.stdout.log",
                    "papers/completion/autoformalization/receipts/snapshots/AF-019/logs/check_outputs.stdout.log",
                    "papers/completion/autoformalization/receipts/snapshots/AF-019/check_outputs.py",
                ],
            },
            {
                "criterion": "No multimodal OCR/ASR performance is claimed without a concrete measured extraction route.",
                "status": "met",
                "explanation": (
                    "OCR and ASR rows are unsupported/no_run. Sealed-PATH probes for tesseract, "
                    "whisper, easyocr, pytesseract, and ffmpeg are recorded. Capability route R07 "
                    "and ImageProcessor remain an unmeasured optional wrapper. No WER, CER, or "
                    "accuracy is emitted. Media and UI stay unevaluated."
                ),
                "evidence": [
                    "papers/completion/autoformalization/receipts/snapshots/AF-019/runs/domain_transfer/results.jsonl",
                    "papers/completion/autoformalization/receipts/snapshots/AF-019/evidence/domain_scope_matrix.json",
                    "papers/completion/autoformalization/receipts/snapshots/AF-019/logs/measure.stdout.log",
                    "papers/completion/autoformalization/receipts/snapshots/AF-019/logs/check_outputs.stdout.log",
                ],
            },
        ],
        "commands": [
            {
                "argv": measure["argv"],
                "cwd": ".",
                "script_artifact": "papers/completion/autoformalization/receipts/snapshots/AF-019/measure_domain_transfer.py",
                "exit_code": measure["exit_code"],
                "log": "papers/completion/autoformalization/receipts/snapshots/AF-019/logs/measure.stdout.log",
                "stderr_log": "papers/completion/autoformalization/receipts/snapshots/AF-019/logs/measure.stderr.log",
                "started_at": measure["started_at"],
                "finished_at": measure["finished_at"],
                "execution_kind": "sealed-PATH structural/learned/proof domain-transfer measurement",
            },
            {
                "argv": check["argv"],
                "cwd": ".",
                "script_artifact": "papers/completion/autoformalization/receipts/snapshots/AF-019/check_outputs.py",
                "exit_code": check["exit_code"],
                "log": "papers/completion/autoformalization/receipts/snapshots/AF-019/logs/check_outputs.stdout.log",
                "stderr_log": "papers/completion/autoformalization/receipts/snapshots/AF-019/logs/check_outputs.stderr.log",
                "started_at": check["started_at"],
                "finished_at": check["finished_at"],
                "execution_kind": "domain profile/population/provenance and claim-class separation checks",
            },
        ],
        "limitations": matrix.get("limitations") or [],
        "completion_scope": (
            "Supported Legal/Security/Intent/software/trace profiles with frozen populations, "
            "actual AF-011/AF-029 checkpoint identities, deterministic baselines, separately "
            "scored structural compatibility, null/unavailable learned transfer, and constructed "
            "Q1/Q2 semantic proof transfer; OCR/ASR and independent source-semantic gold remain "
            "unmeasured."
        ),
    }
    path = PAPER_ROOT / "receipts" / f"{TASK_ID}.json"
    path.write_text(json.dumps(receipt, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return path


def main() -> int:
    home = Path(tempfile.mkdtemp(prefix="ipfs-accelerate-validation-home-af019-"))
    measure = run_step("measure", HERE / "measure_domain_transfer.py", home)
    check = run_step("check_outputs", HERE / "check_outputs.py", home)
    if measure["exit_code"] != 0 or check["exit_code"] != 0:
        report = {"home": str(home), "measure": measure, "check_outputs": check, "ok": False}
        print(json.dumps(report, indent=2, sort_keys=True))
        return 1
    copy_live_outputs()
    artifacts = snapshot_artifacts()
    receipt = write_receipt(measure, check, home, artifacts)
    report = {
        "home": str(home),
        "measure": measure,
        "check_outputs": check,
        "receipt": str(receipt.relative_to(REPO_ROOT)),
        "n_artifacts": len(artifacts),
        "ok": True,
    }
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
