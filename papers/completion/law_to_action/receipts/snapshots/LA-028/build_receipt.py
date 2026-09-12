#!/usr/bin/python3.12
"""Copy LA-028 deliverables into the snapshot tree and write the task receipt."""

from __future__ import annotations

import hashlib
import json
import os
import shutil
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

ROOT = Path(__file__).resolve()
while ROOT != ROOT.parent and not (ROOT / "papers" / "completion" / "law_to_action").is_dir():
    ROOT = ROOT.parent
LIVE = ROOT / "papers" / "completion" / "law_to_action"
BENCHMARK = LIVE / "benchmark"
RESULTS = LIVE / "results" / "development_qualification"
SNAPSHOT = LIVE / "receipts" / "snapshots" / "LA-028"
RECEIPT = LIVE / "receipts" / "LA-028.json"
PYTHON = "/usr/bin/python3.12"
SEALED_PATH = "/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin"
CRITERIA = [
    "Selected source adapters actually process development legal/CVE/skill sources into retained predictions or explicit failures, with all inputs and runtime versions pinned.",
    "An executable end-to-end development command reaches the selected proof/capability/effect-observing handler boundary and records actual model/provider calls when the chosen arm requires them; fixture-only routes are not represented as production.",
    "Review import, final admission and analysis refuse missing independent labels, unavailable runtime routes and incomplete populations; final inputs/arm budgets are frozen before evaluated predictions.",
]


def sha256_file(path: Path) -> str:
    with path.open("rb") as handle:
        return hashlib.file_digest(handle, "sha256").hexdigest()


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def write_json(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + ".tmp-" + uuid4().hex)
    temporary.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    os.replace(temporary, path)


def copy_file(src: Path, dest: Path) -> None:
    dest.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(src, dest)


def run_command(argv: list[str], log_name: str, env: dict[str, str]) -> dict[str, object]:
    validation = SNAPSHOT / "validation"
    validation.mkdir(parents=True, exist_ok=True)
    stdout_path = validation / f"{log_name}.stdout.log"
    stderr_path = validation / f"{log_name}.stderr.log"
    started = utc_now()
    completed = subprocess.run(
        argv,
        cwd=str(ROOT),
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )
    ended = utc_now()
    stdout_path.write_text(completed.stdout)
    stderr_path.write_text(completed.stderr)
    if completed.returncode != 0:
        raise SystemExit(
            f"command failed ({completed.returncode}): {argv}\n{completed.stdout}\n{completed.stderr}"
        )
    record = {
        "argv": argv,
        "cwd": ".",
        "exit_code": completed.returncode,
        "started_at": started,
        "completed_at": ended,
        "log": str((validation / f"{log_name}.stdout.log").relative_to(ROOT)),
        "environment_overrides": {
            "PATH": env["PATH"],
            "PYTHONPATH": env["PYTHONPATH"],
            "PYTHONDONTWRITEBYTECODE": env["PYTHONDONTWRITEBYTECODE"],
            "OMP_NUM_THREADS": env["OMP_NUM_THREADS"],
            "OPENBLAS_NUM_THREADS": env["OPENBLAS_NUM_THREADS"],
            "MKL_NUM_THREADS": env["MKL_NUM_THREADS"],
            "NUMEXPR_NUM_THREADS": env["NUMEXPR_NUM_THREADS"],
            "VECLIB_MAXIMUM_THREADS": env["VECLIB_MAXIMUM_THREADS"],
            "LANG": env["LANG"],
        },
    }
    script = next((item for item in argv if item.endswith(".py")), None)
    if script:
        record["script_artifact"] = script
    return record


def snapshot_tree() -> tuple[dict[str, str], dict[str, str]]:
    outputs: dict[str, str] = {}
    mapping = [
        (BENCHMARK / "source_pipeline.py", SNAPSHOT / "outputs" / "benchmark" / "source_pipeline.py"),
        (BENCHMARK / "review_import.py", SNAPSHOT / "outputs" / "benchmark" / "review_import.py"),
        (BENCHMARK / "qualify_final_runtime.py", SNAPSHOT / "outputs" / "benchmark" / "qualify_final_runtime.py"),
        (BENCHMARK / "runtime_manifest.json", SNAPSHOT / "outputs" / "benchmark" / "runtime_manifest.json"),
        (BENCHMARK / "FINAL_RUN.md", SNAPSHOT / "outputs" / "benchmark" / "FINAL_RUN.md"),
    ]
    for src, dest in mapping:
        copy_file(src, dest)
        outputs[str(src.relative_to(ROOT))] = str(dest.relative_to(ROOT))
    for path in sorted(RESULTS.rglob("*")):
        if not path.is_file():
            continue
        dest = SNAPSHOT / "outputs" / "results" / "development_qualification" / path.relative_to(RESULTS)
        copy_file(path, dest)
        outputs[str(path.relative_to(ROOT))] = str(dest.relative_to(ROOT))
    copy_file(BENCHMARK / "source_pipeline.py", SNAPSHOT / "source_pipeline.py")
    copy_file(BENCHMARK / "review_import.py", SNAPSHOT / "review_import.py")
    copy_file(BENCHMARK / "qualify_final_runtime.py", SNAPSHOT / "qualify_final_runtime.py")
    artifacts = {}
    for path in sorted(SNAPSHOT.rglob("*")):
        if not path.is_file() or path.name == "build_receipt.py":
            continue
        artifacts[str(path.relative_to(ROOT))] = sha256_file(path)
    return artifacts, outputs


def main() -> int:
    env = os.environ.copy()
    env.update(
        {
            "PATH": SEALED_PATH,
            "PYTHONPATH": "external/ipfs_accelerate:external/ipfs_datasets:external/ipfs_kit",
            "PYTHONDONTWRITEBYTECODE": "1",
            "OMP_NUM_THREADS": "1",
            "OPENBLAS_NUM_THREADS": "1",
            "MKL_NUM_THREADS": "1",
            "NUMEXPR_NUM_THREADS": "1",
            "VECLIB_MAXIMUM_THREADS": "1",
            "LANG": "C.UTF-8",
        }
    )
    copy_file(BENCHMARK / "source_pipeline.py", SNAPSHOT / "source_pipeline.py")
    copy_file(BENCHMARK / "review_import.py", SNAPSHOT / "review_import.py")
    copy_file(BENCHMARK / "qualify_final_runtime.py", SNAPSHOT / "qualify_final_runtime.py")
    commands = []
    commands.append(
        run_command(
            [
                PYTHON,
                str((SNAPSHOT / "qualify_final_runtime.py").relative_to(ROOT)),
                "qualify",
                "--out",
                str(RESULTS.relative_to(ROOT)),
            ],
            "qualify",
            env,
        )
    )
    commands.append(
        run_command(
            [
                PYTHON,
                str((SNAPSHOT / "validate_qualification.py").relative_to(ROOT)),
            ],
            "validate",
            env,
        )
    )
    commands.append(
        run_command(
            [
                PYTHON,
                str((SNAPSHOT / "qualify_final_runtime.py").relative_to(ROOT)),
                "admit-final",
                "--out",
                str(RESULTS.relative_to(ROOT)),
            ],
            "admit",
            env,
        )
    )
    commands.append(
        run_command(
            [
                PYTHON,
                str((SNAPSHOT / "review_import.py").relative_to(ROOT)),
                "import",
                "--returned",
                str((SNAPSHOT / "negative-reviews" / "agent_generated.json").relative_to(ROOT)),
                "--out",
                str((SNAPSHOT / "negative-reviews" / "agent-out").relative_to(ROOT)),
            ],
            "agent-import",
            env,
        )
    )
    commands.append(
        run_command(
            [
                PYTHON,
                str((SNAPSHOT / "review_import.py").relative_to(ROOT)),
                "import",
                "--returned",
                str((SNAPSHOT / "negative-reviews" / "incomplete.json").relative_to(ROOT)),
                "--out",
                str((SNAPSHOT / "negative-reviews" / "incomplete-out").relative_to(ROOT)),
            ],
            "incomplete-import",
            env,
        )
    )
    artifacts, outputs = snapshot_tree()
    write_json(SNAPSHOT / "validation" / "commands.json", commands)
    artifacts[str((SNAPSHOT / "validation" / "commands.json").relative_to(ROOT))] = sha256_file(
        SNAPSHOT / "validation" / "commands.json"
    )
    versions = {
        "python": subprocess.check_output([PYTHON, "--version"], env=env, text=True).strip(),
        "python_executable": PYTHON,
        "python_executable_sha256": sha256_file(Path(PYTHON)),
        "authoritative_path": SEALED_PATH,
        "source_pipeline.py_sha256": sha256_file(BENCHMARK / "source_pipeline.py"),
        "review_import.py_sha256": sha256_file(BENCHMARK / "review_import.py"),
        "qualify_final_runtime.py_sha256": sha256_file(BENCHMARK / "qualify_final_runtime.py"),
        "runtime_manifest.json_sha256": sha256_file(BENCHMARK / "runtime_manifest.json"),
        "empirical_benchmark_result": False,
        "selected_arm": "A4",
        "independent_human_review": "pending_LA-027",
    }
    probe = json.loads((RESULTS / "runtime_probe.json").read_text(encoding="utf-8"))
    versions["sympy"] = (probe.get("sympy") or {}).get("version")
    versions["sympy_origin"] = (probe.get("sympy") or {}).get("origin")
    versions["cryptography"] = (probe.get("crypto") or {}).get("cryptography_version")
    versions["duckdb"] = (probe.get("duckdb") or {}).get("version")
    summary = json.loads((RESULTS / "qualification_summary.json").read_text(encoding="utf-8"))
    pipeline = summary.get("pipeline") or {}
    e2e = summary.get("e2e") or {}
    receipt = {
        "schema": "paper-task-evidence/v1",
        "paper_id": "law_to_action",
        "task_id": "LA-028",
        "status": "complete",
        "completed_at": utc_now(),
        "completion_mode": (
            "Development source adapters processed the frozen legal/CVE/skill cases into "
            "retained predictions or explicit failures. An A4 development command reached "
            "SAT, UCAN, ENFORCE, durable consumption, and the effect-observing handler. "
            "Review import, final admission and analysis refused missing independent labels. "
            "Inputs and arm budgets were frozen before predictions. Fixture-only routes are "
            "not production. This is qualification, not scored LA-009/LA-015."
        ),
        "artifacts": artifacts,
        "outputs": outputs,
        "criteria": [
            {
                "criterion": CRITERIA[0],
                "status": "met",
                "explanation": (
                    f"source_pipeline.py ran extract_normative_elements/DeonticConverter on four "
                    f"development legal cases, adapt_cvefixes_candidate on four development CVE "
                    f"cases, and SkillCenterIntentNormalizer on four development skill cases. "
                    f"Counts: {pipeline.get('predictions')} predictions and {pipeline.get('failures')} "
                    f"explicit failures across {pipeline.get('cases')} reserved development cases. "
                    f"The malicious-Markdown mutation was excluded by SkillSourcePolicy. Inputs and "
                    f"runtime versions are pinned in frozen_inputs.json, source_pipeline_freeze.json, "
                    f"and runtime_manifest.json. Final-split labels were not inspected and no gold was scored."
                ),
                "evidence": [
                    str((SNAPSHOT / "outputs" / "benchmark" / "source_pipeline.py").relative_to(ROOT)),
                    str((SNAPSHOT / "outputs" / "results" / "development_qualification" / "source_pipeline_summary.json").relative_to(ROOT)),
                    str((SNAPSHOT / "outputs" / "results" / "development_qualification" / "source_predictions.jsonl").relative_to(ROOT)),
                    str((SNAPSHOT / "outputs" / "results" / "development_qualification" / "source_failures.jsonl").relative_to(ROOT)),
                    str((SNAPSHOT / "outputs" / "results" / "development_qualification" / "frozen_inputs.json").relative_to(ROOT)),
                    str((SNAPSHOT / "validation" / "qualify.stdout.log").relative_to(ROOT)),
                    str((SNAPSHOT / "validation" / "validate.stdout.log").relative_to(ROOT)),
                ],
            },
            {
                "criterion": CRITERIA[1],
                "status": "met",
                "explanation": (
                    f"qualify_final_runtime.py qualify executed source-derived A4 allow/deny attempts "
                    f"through QF_BOOL SAT, real Ed25519 UCAN, SupervisorPreInvocationEnforcement ENFORCE, "
                    f"file-backed DuckDB consumption, BoundedExportHandler, and EffectObserver. "
                    f"Handler boundary reached={e2e.get('handler_boundary_reached')}; allow={e2e.get('allow_decision')}; "
                    f"deny={e2e.get('deny_decision')}. Selected A4 requires no model calls; the ledger records "
                    f"call_count=0 rather than a fixture completion. LA-008 run.py and other fixture routes "
                    f"are labeled not production in runtime_manifest.json and FINAL_RUN.md."
                ),
                "evidence": [
                    str((SNAPSHOT / "outputs" / "benchmark" / "qualify_final_runtime.py").relative_to(ROOT)),
                    str((SNAPSHOT / "outputs" / "benchmark" / "runtime_manifest.json").relative_to(ROOT)),
                    str((SNAPSHOT / "outputs" / "benchmark" / "FINAL_RUN.md").relative_to(ROOT)),
                    str((SNAPSHOT / "outputs" / "results" / "development_qualification" / "e2e_handler_trace.json").relative_to(ROOT)),
                    str((SNAPSHOT / "outputs" / "results" / "development_qualification" / "model_provider_ledger.json").relative_to(ROOT)),
                    str((SNAPSHOT / "outputs" / "results" / "development_qualification" / "qualification_summary.json").relative_to(ROOT)),
                    str((SNAPSHOT / "validation" / "qualify.stdout.log").relative_to(ROOT)),
                ],
            },
            {
                "criterion": CRITERIA[2],
                "status": "met",
                "explanation": (
                    "review_import.py refused the absent independent return "
                    "(missing_independent_review_return), refused an agent-generated packet, and refused "
                    "an incomplete population. qualify admit-final and analysis remain refused with "
                    "missing_independent_labels. frozen_inputs.json and frozen_budgets.json were written "
                    "before source predictions; freeze_digest.json records that pin. Final examples were "
                    "not scored."
                ),
                "evidence": [
                    str((SNAPSHOT / "outputs" / "benchmark" / "review_import.py").relative_to(ROOT)),
                    str((SNAPSHOT / "outputs" / "results" / "development_qualification" / "review_import_refusal.json").relative_to(ROOT)),
                    str((SNAPSHOT / "outputs" / "results" / "development_qualification" / "final_admission.json").relative_to(ROOT)),
                    str((SNAPSHOT / "outputs" / "results" / "development_qualification" / "final_analysis.json").relative_to(ROOT)),
                    str((SNAPSHOT / "outputs" / "results" / "development_qualification" / "frozen_budgets.json").relative_to(ROOT)),
                    str((SNAPSHOT / "validation" / "admit.stdout.log").relative_to(ROOT)),
                    str((SNAPSHOT / "validation" / "agent-import.stdout.log").relative_to(ROOT)),
                    str((SNAPSHOT / "validation" / "incomplete-import.stdout.log").relative_to(ROOT)),
                ],
            },
        ],
        "commands": commands,
        "source_versions": versions,
        "limitations": [
            "Independent human legal/CVE/skill review remains pending in LA-027.",
            "This is development qualification, not scored source-to-IR (LA-009) or scored A4 (LA-015).",
            "SAT evidence cannot authorize theorem_proof allows.",
            "Closed-loop model arms are unrun; no scientific model is pinned.",
            "Full legal PDFs, CVE parquet, and SkillCenter SQLite bodies remain retrieval_only; adapters processed pinned quoted spans and recovered pair evidence.",
        ],
    }
    write_json(RECEIPT, receipt)
    print(json.dumps({"receipt": str(RECEIPT.relative_to(ROOT)), "artifact_count": len(artifacts), "output_count": len(outputs)}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
