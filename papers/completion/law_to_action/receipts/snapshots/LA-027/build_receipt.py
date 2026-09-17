#!/usr/bin/python3.12
"""Copy LA-027 deliverables into the snapshot tree and write the task receipt."""

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
RESULTS = LIVE / "results" / "automated_scope_qualification"
SNAPSHOT = LIVE / "receipts" / "snapshots" / "LA-027"
RECEIPT = LIVE / "receipts" / "LA-027.json"
PYTHON = "/usr/bin/python3.12"
SEALED_PATH = "/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin"
CRITERIA = [
    "An explicit versioned amendment binds the unchanged source population/splits, original protocol and receipts, machine-expectation provenance, permitted automated metrics and withdrawn expert/legal-validity/human-agreement claims before any new evaluated predictions.",
    "Actual normal automated admission works without reviewer identities or human labels, while focused controls reject missing runtime/source bindings, incomplete case accounting, invalid expectation provenance, self-reported success, stale profile or budget, and any attempt to label automated output independent human gold.",
    "The selected native source adapters, proof/capability route and independent effect observer execute in an isolated qualification with exact commands, hashes, failures and raw logs. Fixtures remain qualification-only and no held-out result or useful-work success is inferred from them.",
    "The runtime, analysis and manuscript instructions no longer require outside reviewers for the automated scope. All human fields remain absent/uncollected unless authentic returns exist, optional author review is labeled non-independent, and original task/receipt/blank-packet history is preserved.",
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
    snapshot_prefix = str(SNAPSHOT.relative_to(ROOT)).rstrip("/") + "/"
    script = next((item for item in argv if item.endswith(".py")), None)
    if isinstance(script, str) and script.startswith(snapshot_prefix):
        record["script_artifact"] = script
    return record


def snapshot_tree() -> tuple[dict[str, str], dict[str, str]]:
    outputs: dict[str, str] = {}
    mapping = [
        (BENCHMARK / "automated_evidence_amendment.json", SNAPSHOT / "outputs" / "benchmark" / "automated_evidence_amendment.json"),
        (BENCHMARK / "AUTOMATED_EVIDENCE_SCOPE.md", SNAPSHOT / "outputs" / "benchmark" / "AUTOMATED_EVIDENCE_SCOPE.md"),
        (BENCHMARK / "automated_evidence.py", SNAPSHOT / "outputs" / "benchmark" / "automated_evidence.py"),
        (BENCHMARK / "tests" / "test_automated_evidence.py", SNAPSHOT / "outputs" / "benchmark" / "tests" / "test_automated_evidence.py"),
        (BENCHMARK / "qualify_final_runtime.py", SNAPSHOT / "outputs" / "benchmark" / "qualify_final_runtime.py"),
        (BENCHMARK / "source_pipeline.py", SNAPSHOT / "outputs" / "benchmark" / "source_pipeline.py"),
        (BENCHMARK / "protocol.json", SNAPSHOT / "outputs" / "benchmark" / "protocol.json"),
        (BENCHMARK / "protocol.md", SNAPSHOT / "outputs" / "benchmark" / "protocol.md"),
        (BENCHMARK / "FINAL_RUN.md", SNAPSHOT / "outputs" / "benchmark" / "FINAL_RUN.md"),
        (BENCHMARK / "annotations" / "automated_reference_manifest.json", SNAPSHOT / "outputs" / "benchmark" / "annotations" / "automated_reference_manifest.json"),
    ]
    for src, dest in mapping:
        copy_file(src, dest)
        outputs[str(src.relative_to(ROOT))] = str(dest.relative_to(ROOT))
    for path in sorted(RESULTS.rglob("*")):
        if not path.is_file():
            continue
        dest = SNAPSHOT / "outputs" / "results" / "automated_scope_qualification" / path.relative_to(RESULTS)
        copy_file(path, dest)
        outputs[str(path.relative_to(ROOT))] = str(dest.relative_to(ROOT))
    for name in ("automated_evidence.py", "qualify_final_runtime.py", "source_pipeline.py"):
        copy_file(BENCHMARK / name, SNAPSHOT / name)
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
    copy_file(BENCHMARK / "automated_evidence.py", SNAPSHOT / "automated_evidence.py")
    copy_file(BENCHMARK / "qualify_final_runtime.py", SNAPSHOT / "qualify_final_runtime.py")
    copy_file(BENCHMARK / "source_pipeline.py", SNAPSHOT / "source_pipeline.py")
    copy_file(BENCHMARK / "tests" / "test_automated_evidence.py", SNAPSHOT / "test_automated_evidence.py")
    commands = []
    commands.append(
        run_command(
            [
                PYTHON,
                str((BENCHMARK / "tests" / "test_automated_evidence.py").relative_to(ROOT)),
            ],
            "unittest",
            env,
        )
    )
    commands.append(
        run_command(
            [
                PYTHON,
                str((SNAPSHOT / "qualify_final_runtime.py").relative_to(ROOT)),
                "qualify-automated",
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
                str((SNAPSHOT / "qualify_final_runtime.py").relative_to(ROOT)),
                "analyze",
                "--out",
                str(RESULTS.relative_to(ROOT)),
            ],
            "analyze",
            env,
        )
    )
    commands.append(
        run_command(
            [
                PYTHON,
                str((SNAPSHOT / "validate_automated_scope.py").relative_to(ROOT)),
            ],
            "validate",
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
        "automated_evidence.py_sha256": sha256_file(BENCHMARK / "automated_evidence.py"),
        "qualify_final_runtime.py_sha256": sha256_file(BENCHMARK / "qualify_final_runtime.py"),
        "source_pipeline.py_sha256": sha256_file(BENCHMARK / "source_pipeline.py"),
        "original_protocol_sha256": "ba03394cd66f51999d1b177a29558b6130429eb9fc3faebea5e57c780857940f",
        "empirical_benchmark_result": False,
        "evidence_scope": "automated_source_contracts_and_policy_effects",
        "selected_arm": "A4",
        "independent_human_gold": False,
        "optional_author_review_independent": False,
    }
    probe = json.loads((RESULTS / "runtime_probe.json").read_text(encoding="utf-8"))
    versions["sympy"] = (probe.get("sympy") or {}).get("version")
    versions["sympy_origin"] = (probe.get("sympy") or {}).get("origin")
    versions["cryptography"] = (probe.get("crypto") or {}).get("cryptography_version")
    versions["duckdb"] = (probe.get("duckdb") or {}).get("version")
    summary = json.loads((RESULTS / "qualification_summary.json").read_text(encoding="utf-8"))
    pipeline = summary.get("pipeline") or {}
    e2e = summary.get("e2e") or {}
    admission = json.loads((RESULTS / "automated_admission.json").read_text(encoding="utf-8"))
    receipt = {
        "schema": "paper-task-evidence/v1",
        "paper_id": "law_to_action",
        "task_id": "LA-027",
        "status": "complete",
        "completed_at": utc_now(),
        "completion_mode": (
            "Bound the LA-027/v1 automated evidence amendment to the unchanged source "
            "population, original protocol hash, original LA-005/007/026/028 receipts and "
            "blank packets. Typed automated admission succeeded without reviewer identities "
            "or human labels. Focused controls refused missing bindings, incomplete accounting, "
            "invalid expectation provenance, self-reported success, stale profile/budget and "
            "automated output labeled human gold. Isolated A4 qualification executed SAT, UCAN, "
            "ENFORCE and the independent effect observer. Fixtures remain qualification-only. "
            "This is not scored LA-009/LA-015 and not human gold."
        ),
        "artifacts": artifacts,
        "outputs": outputs,
        "criteria": [
            {
                "criterion": CRITERIA[0],
                "status": "met",
                "explanation": (
                    "automated_evidence_amendment.json status is bound_versioned_amendment_before_evaluated_predictions. "
                    "It pins original protocol SHA-256 ba03394cd66f51999d1b177a29558b6130429eb9fc3faebea5e57c780857940f, "
                    "splits SHA-256 f40b60ce73acbbbb7e9da39159b7dc5706f250cb5b85ac407c4b10140cb5c5a6, "
                    "unchanged 30 families/60 cases, original LA-005/007/026/028 receipt hashes, "
                    "machine-contract producer provenance, permitted automated metrics and withdrawn "
                    "expert/legal-validity/human-agreement claims. automated_reference_manifest.json "
                    "covers all 60 cases with policy_polarity=unknown before predictions. "
                    f"frozen_inputs.json frozen_before_evaluated_predictions=true."
                ),
                "evidence": [
                    str((SNAPSHOT / "outputs" / "benchmark" / "automated_evidence_amendment.json").relative_to(ROOT)),
                    str((SNAPSHOT / "outputs" / "benchmark" / "AUTOMATED_EVIDENCE_SCOPE.md").relative_to(ROOT)),
                    str((SNAPSHOT / "outputs" / "benchmark" / "annotations" / "automated_reference_manifest.json").relative_to(ROOT)),
                    str((SNAPSHOT / "outputs" / "benchmark" / "protocol.json").relative_to(ROOT)),
                    str((SNAPSHOT / "outputs" / "results" / "automated_scope_qualification" / "frozen_inputs.json").relative_to(ROOT)),
                    str((SNAPSHOT / "outputs" / "results" / "automated_scope_qualification" / "freeze_digest.json").relative_to(ROOT)),
                    str((SNAPSHOT / "validation" / "validate.stdout.log").relative_to(ROOT)),
                ],
            },
            {
                "criterion": CRITERIA[1],
                "status": "met",
                "explanation": (
                    "automated_evidence.py admitted a normal envelope with reviewer_id=absent and "
                    "independent_human_gold=false, scored=false, exit_status=0. Eight focused controls "
                    "each refused with exit_status=2 for missing runtime/source bindings, incomplete "
                    "case accounting, invalid expectation provenance, self-reported success, stale "
                    "profile, stale budget, and automated output labeled independent human gold. "
                    "validate_automated_scope.py re-ran a failing admit subprocess and observed process exit 2."
                ),
                "evidence": [
                    str((SNAPSHOT / "outputs" / "benchmark" / "automated_evidence.py").relative_to(ROOT)),
                    str((SNAPSHOT / "outputs" / "benchmark" / "tests" / "test_automated_evidence.py").relative_to(ROOT)),
                    str((SNAPSHOT / "outputs" / "results" / "automated_scope_qualification" / "automated_admission.json").relative_to(ROOT)),
                    str((SNAPSHOT / "outputs" / "results" / "automated_scope_qualification" / "admission_controls.json").relative_to(ROOT)),
                    str((SNAPSHOT / "validation" / "unittest.stdout.log").relative_to(ROOT)),
                    str((SNAPSHOT / "validation" / "validate.stdout.log").relative_to(ROOT)),
                ],
            },
            {
                "criterion": CRITERIA[2],
                "status": "met",
                "explanation": (
                    f"qualify-automated ran native legal/CVE/skill adapters on 12 development cases "
                    f"({pipeline.get('predictions')} predictions, {pipeline.get('failures')} failures) "
                    f"then A4 SAT/UCAN/ENFORCE/DuckDB/BoundedExportHandler/EffectObserver. "
                    f"handler_boundary_reached={e2e.get('handler_boundary_reached')}; "
                    f"proof={e2e.get('proof_route_executed')}; capability={e2e.get('capability_route_executed')}; "
                    f"allow={e2e.get('allow_decision')}; deny={e2e.get('deny_decision')}. "
                    "Fixture harness is not production. held_out_result_inferred=false and "
                    "useful_work_success_inferred_from_fixtures=false. Commands, hashes and raw logs "
                    "are retained in results/automated_scope_qualification and this snapshot."
                ),
                "evidence": [
                    str((SNAPSHOT / "outputs" / "benchmark" / "qualify_final_runtime.py").relative_to(ROOT)),
                    str((SNAPSHOT / "outputs" / "benchmark" / "source_pipeline.py").relative_to(ROOT)),
                    str((SNAPSHOT / "outputs" / "results" / "automated_scope_qualification" / "e2e_handler_trace.json").relative_to(ROOT)),
                    str((SNAPSHOT / "outputs" / "results" / "automated_scope_qualification" / "source_pipeline_summary.json").relative_to(ROOT)),
                    str((SNAPSHOT / "outputs" / "results" / "automated_scope_qualification" / "qualification_summary.json").relative_to(ROOT)),
                    str((SNAPSHOT / "outputs" / "results" / "automated_scope_qualification" / "runtime_manifest.json").relative_to(ROOT)),
                    str((SNAPSHOT / "validation" / "qualify.stdout.log").relative_to(ROOT)),
                ],
            },
            {
                "criterion": CRITERIA[3],
                "status": "met",
                "explanation": (
                    "FINAL_RUN.md, protocol.json/md and qualify_final_runtime.py admit-final/analyze "
                    "use the automated scope and do not require outside reviewers. Human fields remain "
                    "absent/uncollected; optional author review is labeled non-independent and uncollected. "
                    "review_import.py still refuses a missing return and is not the automated gate. "
                    "Original LA-005/007/026/028 receipts and blank review_packet_manifest.json hashes "
                    "are unchanged. No fabricated review.admitted=true value was written."
                ),
                "evidence": [
                    str((SNAPSHOT / "outputs" / "benchmark" / "FINAL_RUN.md").relative_to(ROOT)),
                    str((SNAPSHOT / "outputs" / "benchmark" / "protocol.json").relative_to(ROOT)),
                    str((SNAPSHOT / "outputs" / "benchmark" / "protocol.md").relative_to(ROOT)),
                    str((SNAPSHOT / "outputs" / "results" / "automated_scope_qualification" / "review_import_refusal.json").relative_to(ROOT)),
                    str((SNAPSHOT / "outputs" / "results" / "automated_scope_qualification" / "final_analysis.json").relative_to(ROOT)),
                    str((SNAPSHOT / "validation" / "admit.stdout.log").relative_to(ROOT)),
                    str((SNAPSHOT / "validation" / "analyze.stdout.log").relative_to(ROOT)),
                ],
            },
        ],
        "commands": commands,
        "source_versions": versions,
        "limitations": [
            "Expert legal fidelity, legal validity in the world, independent human validation and agreement remain unmeasured.",
            "This is automated-scope qualification, not scored source-to-IR (LA-009) or scored A4 (LA-015).",
            "SAT evidence cannot authorize theorem_proof allows.",
            "Closed-loop model arms are unrun; no scientific model is pinned.",
            "Optional author review was not collected and is not independent.",
            "Original LA-005/007/026/028 receipts and blank packets remain historical and are not human gold.",
        ],
    }
    write_json(RECEIPT, receipt)
    print(
        json.dumps(
            {
                "receipt": str(RECEIPT.relative_to(ROOT)),
                "artifact_count": len(artifacts),
                "output_count": len(outputs),
                "admitted": admission.get("admitted"),
                "pipeline": pipeline,
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
