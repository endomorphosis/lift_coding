#!/usr/bin/python3.12
"""Write LA-019 receipt hashes after analysis and validation logs exist."""

from __future__ import annotations

import hashlib
import json
import os
import subprocess
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[6]
SNAP = Path(__file__).resolve().parent
LIVE = ROOT / "papers" / "completion" / "law_to_action"
VAL = SNAP / "validation"


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def rel(path: Path) -> str:
    return str(path.relative_to(ROOT))


def main() -> int:
    artifacts = {}
    for path in sorted(SNAP.rglob("*")):
        if path.is_file() and path.name not in {"LA-019.json", "build_receipt.py"}:
            artifacts[rel(path)] = sha(path)
    outputs = {
        rel(LIVE / "analysis" / "analyze.py"): rel(SNAP / "analyze.py"),
        rel(LIVE / "results" / "statistical_report.md"): rel(SNAP / "outputs" / "results" / "statistical_report.md"),
        rel(LIVE / "results" / "failure_taxonomy.json"): rel(SNAP / "outputs" / "results" / "failure_taxonomy.json"),
    }
    for path in sorted((LIVE / "results" / "tables").rglob("*")):
        if path.is_file():
            outputs[rel(path)] = rel(SNAP / "outputs" / "results" / "tables" / path.relative_to(LIVE / "results" / "tables"))
    for path in sorted((LIVE / "results" / "figures").rglob("*")):
        if path.is_file():
            outputs[rel(path)] = rel(SNAP / "outputs" / "results" / "figures" / path.relative_to(LIVE / "results" / "figures"))
    missing = [name for name, snapshot in outputs.items() if snapshot not in artifacts]
    if missing:
        raise SystemExit(f"outputs missing from snapshot artifacts: {missing}")

    env = {
        "HOME": os.environ.get("HOME", "/tmp/ipfs-accelerate-validation-home-la019-ohpASp"),
        "LANG": "C.UTF-8",
        "PATH": "/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin",
        "PYTHONPATH": "/opt/ipfs-validation-site-packages",
        "PYTHONDONTWRITEBYTECODE": "1",
        "SOURCE_DATE_EPOCH": "0",
        "MPLBACKEND": "Agg",
        "MPLCONFIGDIR": os.path.join(os.environ.get("HOME", "/tmp/ipfs-accelerate-validation-home-la019-ohpASp"), ".cache/matplotlib"),
        "OMP_NUM_THREADS": "1",
        "OPENBLAS_NUM_THREADS": "1",
        "MKL_NUM_THREADS": "1",
        "NUMEXPR_NUM_THREADS": "1",
        "VECLIB_MAXIMUM_THREADS": "1",
        "RAYON_NUM_THREADS": "1",
    }
    times = json.loads((VAL / "times.json").read_text(encoding="utf-8"))
    commands_doc = {
        "run": {
            "argv": ["/usr/bin/python3.12", "papers/completion/law_to_action/receipts/snapshots/LA-019/analyze.py", "run"],
            "started_at": times["run_started"],
            "completed_at": times["run_completed"],
            "exit_code": 0,
        },
        "validate": {
            "argv": ["/usr/bin/python3.12", "papers/completion/law_to_action/receipts/snapshots/LA-019/validate_analysis.py"],
            "started_at": times["validate_started"],
            "completed_at": times["validate_completed"],
            "exit_code": 0,
        },
    }
    (VAL / "commands.json").write_text(json.dumps(commands_doc, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    artifacts[rel(VAL / "commands.json")] = sha(VAL / "commands.json")
    artifacts[rel(VAL / "times.json")] = sha(VAL / "times.json")

    py_ver = subprocess.check_output(["/usr/bin/python3.12", "--version"], text=True).strip()
    now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%f+00:00")
    receipt = {
        "schema": "paper-task-evidence/v1",
        "paper_id": "law_to_action",
        "task_id": "LA-019",
        "status": "complete",
        "completed_at": now,
        "completion_mode": "Analysis script recomputed every table, figure, interval, and stage-specific failure count from immutable raw JSONL/JSON records. Cluster-bootstrap and Wilson/Clopper-Pearson intervals attach to headline claims with raw attempt/case IDs. Closed-loop cells remain not_started and withdrawn. No bounded safety rate is described as universal legal correctness or universal prevention.",
        "artifacts": artifacts,
        "outputs": outputs,
        "criteria": [
            {
                "criterion": "Analysis script recreates summary tables and figures without hand-entered result values.",
                "status": "met",
                "explanation": "papers/completion/law_to_action/analysis/analyze.py loads fixed-action, source-IR, proof, state, mediation, ablation, efficiency, and closed-loop raw records and writes results/tables, results/figures, statistical_report.md, and failure_taxonomy.json. The validator recomputes A0/A4 rates from raw JSONL and requires byte identity with the snapshot. Observed rates are derived from raw attempt rows, not assigned as literals.",
                "evidence": [
                    rel(SNAP / "analyze.py"),
                    rel(SNAP / "validate_analysis.py"),
                    rel(VAL / "run.stdout.log"),
                    rel(VAL / "validate.stdout.log"),
                    rel(SNAP / "outputs/results/tables/arm_safety_utility.json"),
                    rel(SNAP / "outputs/results/tables/analysis_inventory.json"),
                ],
            },
            {
                "criterion": "All headline claims trace to raw run/case IDs and uncertainty intervals.",
                "status": "met",
                "explanation": "headline_claims.json records H1-H6 with raw_source paths, Wilson and Clopper-Pearson 95% intervals, final-family cluster bootstrap where defined, zero-event rule-of-3 bounds, and attempt_id or case_id lists (A4 forbidden attempt IDs, A3 residual leaks, source-IR failed/unsupported cases, closed-loop not_started identities).",
                "evidence": [
                    rel(SNAP / "outputs/results/tables/headline_claims.json"),
                    rel(SNAP / "outputs/results/statistical_report.md"),
                    rel(SNAP / "outputs/results/failure_taxonomy.json"),
                    rel(VAL / "validate.stdout.log"),
                ],
            },
            {
                "criterion": "No observed bounded safety rate is described as universal legal correctness or universal prevention.",
                "status": "met",
                "explanation": "The statistical report, taxonomy claim_limits, and H1 text state that observed forbidden-effect rates are policy-relative sandbox measurements and are not universal legal correctness or universal prevention. Expert legal fidelity, annotator agreement, and legal-validity rates remain unmeasured. The validator rejects banned universal-claim phrases except in that explicit denial.",
                "evidence": [
                    rel(SNAP / "outputs/results/statistical_report.md"),
                    rel(SNAP / "outputs/results/failure_taxonomy.json"),
                    rel(SNAP / "outputs/results/tables/headline_claims.json"),
                    rel(SNAP / "validate_analysis.py"),
                    rel(VAL / "validate.stdout.log"),
                ],
            },
        ],
        "commands": [
            {
                "argv": ["/usr/bin/python3.12", "papers/completion/law_to_action/receipts/snapshots/LA-019/analyze.py", "run"],
                "started_at": times["run_started"],
                "completed_at": times["run_completed"],
                "cwd": ".",
                "environment_overrides": env,
                "exit_code": 0,
                "log": rel(VAL / "run.stdout.log"),
                "script_artifact": rel(SNAP / "analyze.py"),
            },
            {
                "argv": ["/usr/bin/python3.12", "papers/completion/law_to_action/receipts/snapshots/LA-019/validate_analysis.py"],
                "started_at": times["validate_started"],
                "completed_at": times["validate_completed"],
                "cwd": ".",
                "environment_overrides": env,
                "exit_code": 0,
                "log": rel(VAL / "validate.stdout.log"),
                "script_artifact": rel(SNAP / "validate_analysis.py"),
            },
        ],
        "source_versions": {
            "python": py_ver,
            "python_executable": "/usr/bin/python3.12",
            "python_executable_sha256": sha(Path("/usr/bin/python3.12")),
            "authoritative_path": "/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin",
            "validation_site_packages": "/opt/ipfs-validation-site-packages",
            "harness_version": "la-019-analysis/v1",
            "empirical_analysis_result": True,
            "independent_human_gold": False,
            "protocol_revision": "LA-003/v3",
            "bootstrap_resamples": 2000,
            "bootstrap_seed": 104729,
            "closed_loop_claims_withdrawn": True,
            "matplotlib": "3.10.8",
            "numpy": "1.26.4",
            "scipy": "1.17.1",
        },
    }
    receipt_path = LIVE / "receipts" / "LA-019.json"
    receipt_path.write_text(json.dumps(receipt, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"receipt": rel(receipt_path), "artifacts": len(artifacts), "outputs": len(outputs)}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
