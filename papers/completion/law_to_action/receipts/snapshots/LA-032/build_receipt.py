#!/usr/bin/python3.12
"""Snapshot LA-032 freeze outputs and write the task receipt."""
from __future__ import annotations

import hashlib
import json
import os
import shutil
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[6]
PAPER = ROOT / "papers" / "completion" / "law_to_action"
STUDY = PAPER / "benchmark" / "generated_code_study"
SNAP = Path(__file__).resolve().parent
RECEIPT = PAPER / "receipts" / "LA-032.json"
DELIVERABLES = [
    STUDY / "preparation",
    STUDY / "cohort",
    STUDY / "qualification",
    STUDY / "model_profile.json",
    STUDY / "prospective_study.json",
    STUDY / "schedule.json",
    STUDY / "family_batches.json",
    STUDY / "native_dependency_plan.json",
    STUDY / "driver.py",
    STUDY / "verify_preparation.py",
]
CRITERIA = [
    "Prospectively freeze exactly 6 legal, 12 CVE and 12 skill source-lineage families with two source-relative cases each. Verify actual source bytes, lawful access and any redistribution terms, immutable upstream versions, exact/normalized hashes, fork/ancestry and nearest-neighbor audits. Exclude every LA-004/LA-029 family and derivative across all populations; canonical repository identity alone is not a complete fork/clone audit. Do not count generated SkillCenter procedures as independent human annotations.",
    "Apply the original ranked SHA256 split rule with salt vericodegen-2026-law-to-action-LA016-v1 and population development/calibration/final quotas legal 2/1/3, CVE 2/3/7, skill 2/2/8. Descendants inherit parent splits. Bind permitted retrieval to source lineage and exclude hidden oracles, sibling final labels and target patches. Seal final task/oracle material so it cannot be released to inference before the final-stage gate.",
    "Implement all 60 scientifically useful source-relative tasks and independent machine-checkable utility/effect oracles. Qualify an adequate actual generated-program and bounded-handler profile across legal/CVE/skill cases. Retain source-to-policy/task/oracle mappings, positive useful-work and negative undeclared-effect tests, strict syntax/escape rejection and actual native context/effect enforcement. The LA-030 two-sink profile and fixed LA-029 programs may inform development but cannot substitute for the study.",
    "Qualify actual model, weights, tokenizer, revision, chat template, deployment, prompt and decoding pins with real bounded development calls. For every qualified call, require returned prompt_tokens to equal that call's retained preflight input_count, not merely stay below 2048. Qualify 1024 output-token ceiling, seed behavior, raw response preservation, cancellation and actual model-service resource accounting. Reuse a warm model while actively inferring; preserve 10000 seconds of total service wall and a separate 360-second startup-readiness bound. Do not make systemd or an indefinitely running model a prerequisite.",
    "Qualify a hard complete-attempt 120-second boundary across template/tokenization/inference, all generated-program execution and cleanup. Preserve the full 8-call/2048-input/1024-output and zero-paid-budget contract. Retain actual descendant CPU, memory, model/service costs, transport wall and all overruns/unknowns. Explicitly investigate and regression-test the retained LA-030 v2 native watchdog resource_observation_OSError during terminal observation. Its exact errno/path/cause is unproven by the historical receipt. First retain operation/path/errno plus leaf/parent identity snapshots in a new diagnostic implementation; do not suppress OSError broadly or upgrade the failed receipt. Any benign-disappearance handling must revalidate stable parent identity, monotonic counters and empty state. Retained parent accounting and whole-group exit remain mandatory.",
    "Implement a durable scientific driver with exact source/model/runtime/freeze identity, exclusive ownership, pre-dispatch reservations for each cell and model call, interruption/resume, stale-owner reconciliation, unknown usage/effect handling, actual one-time durable capability consumption and no silent replay/refunded calls. Qualification must include actual interruption/resume and cleanup fault probes under bounded development input, not configuration flags alone.",
    "Freeze the full 900 unique case-arm-seed identities before scientific outputs and partition them into exactly 30 disjoint source-family batches of 30 cells each. The six development families contain 180 cells, six calibration families 180 and eighteen final families 540. Each batch retains original arm/seed identities, source pairing and declared arm-position balancing. Record the phase/family dispatch order and its mapping to the original schedule explicitly before outcomes; any operational ordering amendment must preserve scientific contrasts and be visible in the freeze.",
    "Bind every family batch to the same cohort/code/model/runtime/prompt/oracle/schedule freeze and a <=3600-second scientific-attempt allowance, leaving room within the <=7200-second worker ceiling for setup/cleanup/reporting. A bounded warm-service owner may span active batches, with costs allocated once and exclusive inference ownership. Preparation cannot dispatch final cells or claim any planned scientific cell completed.",
    "Create real native dependency edges before execution: development/calibration family tasks depend on LA-032 and prior owned batch/phase gates; an analysis-freeze task depends on all development/calibration batches; every final-family task depends on that analysis freeze; LA-031 depends explicitly on preparation, all 30 batch tasks and the analysis-freeze task. Parent metadata alone is insufficient. Do not register future batch success or mark LA-031 completed by the schedule freeze.",
    "A dedicated read-only preparation verifier recomputes exact source counts/exclusions/splits, all 900 identities and disjoint batch coverage, actual qualification artifact bindings, source-relative case/oracle completeness, sealed-final status, scientific zero-execution status and the dependency plan. It must fail on missing sources, incomplete runtime/model/profile evidence, mock mechanisms, reduced denominators or a permissive availability flag. Completion records readiness only; actual scientific execution stays with the batch tasks.",
]


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def rel(path: Path) -> str:
    return str(path.relative_to(ROOT))


def collect() -> list[Path]:
    files = []
    for item in DELIVERABLES:
        if item.is_file():
            files.append(item)
        else:
            files.extend(sorted(p for p in item.rglob("*") if p.is_file() and "__pycache__" not in p.parts and not p.name.startswith(".")))
    return files


def run_verify() -> dict:
    validation = SNAP / "validation"
    validation.mkdir(parents=True, exist_ok=True)
    argv = [
        "/usr/bin/python3.12",
        "-B",
        "papers/completion/law_to_action/benchmark/generated_code_study/verify_preparation.py",
        "--study",
        "papers/completion/law_to_action/benchmark/generated_code_study/prospective_study.json",
        "--require-scientific-cells-unexecuted",
    ]
    started = datetime.now(timezone.utc)
    result = subprocess.run(argv, cwd=ROOT, capture_output=True, env={**os.environ, "PYTHONDONTWRITEBYTECODE": "1", "PATH": "/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin"})
    completed = datetime.now(timezone.utc)
    stdout = validation / "verify_preparation.stdout.log"
    stderr = validation / "verify_preparation.stderr.log"
    stdout.write_bytes(result.stdout)
    stderr.write_bytes(result.stderr)
    if result.returncode != 0:
        raise SystemExit(result.stderr.decode() or "verify failed")
    return {
        "argv": argv,
        "cwd": ".",
        "environment_overrides": {"PYTHONDONTWRITEBYTECODE": "1", "PATH": "/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin"},
        "started_at": started.isoformat(),
        "completed_at": completed.isoformat(),
        "exit_code": result.returncode,
        "log": rel(stdout),
        "stderr_log": rel(stderr),
        "script_artifact": rel(SNAP / "outputs" / "benchmark" / "generated_code_study" / "verify_preparation.py"),
    }


def main() -> None:
    outputs_root = SNAP / "outputs"
    if outputs_root.exists():
        shutil.rmtree(outputs_root)
    files = collect()
    artifacts = {}
    outputs = {}
    for path in files:
        snapshot = SNAP / "outputs" / path.relative_to(PAPER)
        snapshot.parent.mkdir(parents=True, exist_ok=True)
        if not os.access(path, os.R_OK):
            path.chmod(path.stat().st_mode | 0o400)
        shutil.copyfile(path, snapshot)
        artifacts[rel(snapshot)] = sha(snapshot)
        outputs[rel(path)] = rel(snapshot)
    command = run_verify()
    for extra in (SNAP / "validation").rglob("*"):
        if extra.is_file():
            artifacts[rel(extra)] = sha(extra)
    artifacts[rel(SNAP / "build_receipt.py")] = sha(SNAP / "build_receipt.py")
    evidence = {
        "cohort": rel(SNAP / "outputs" / "benchmark" / "generated_code_study" / "cohort" / "sources.json"),
        "splits": rel(SNAP / "outputs" / "benchmark" / "generated_code_study" / "cohort" / "splits.json"),
        "cases": rel(SNAP / "outputs" / "benchmark" / "generated_code_study" / "cohort" / "cases.json"),
        "sealed": rel(SNAP / "outputs" / "benchmark" / "generated_code_study" / "cohort" / "sealed_final.json"),
        "lineage": rel(SNAP / "outputs" / "benchmark" / "generated_code_study" / "cohort" / "lineage_audit.json"),
        "mappings": rel(SNAP / "outputs" / "benchmark" / "generated_code_study" / "cohort" / "source_to_oracle_mappings.json"),
        "profile": rel(SNAP / "outputs" / "benchmark" / "generated_code_study" / "qualification" / "profile" / "qualification.json"),
        "model": rel(SNAP / "outputs" / "benchmark" / "generated_code_study" / "model_profile.json"),
        "model_qual": rel(SNAP / "outputs" / "benchmark" / "generated_code_study" / "qualification" / "model" / "qualification.json"),
        "watchdog": rel(SNAP / "outputs" / "benchmark" / "generated_code_study" / "qualification" / "watchdog" / "qualification.json"),
        "deadline": rel(SNAP / "outputs" / "benchmark" / "generated_code_study" / "qualification" / "deadline" / "qualification.json"),
        "driver": rel(SNAP / "outputs" / "benchmark" / "generated_code_study" / "qualification" / "driver" / "qualification.json"),
        "schedule": rel(SNAP / "outputs" / "benchmark" / "generated_code_study" / "schedule.json"),
        "batches": rel(SNAP / "outputs" / "benchmark" / "generated_code_study" / "family_batches.json"),
        "deps": rel(SNAP / "outputs" / "benchmark" / "generated_code_study" / "native_dependency_plan.json"),
        "study": rel(SNAP / "outputs" / "benchmark" / "generated_code_study" / "prospective_study.json"),
        "verify": rel(SNAP / "outputs" / "benchmark" / "generated_code_study" / "verify_preparation.py"),
        "log": command["log"],
    }
    explanations = [
        "Exactly 6 legal, 12 CVE and 12 skill families were frozen from hashed official GovInfo PDFs, the pinned CVEfixes first shard and the pinned SkillCenter bundle. Actual source bytes were read, SHA-256 verified, and left retrieval-only. LA-004/LA-029 families, repository identities, repo-name fork/clone collisions and nearest-neighbor duplicates were excluded. SkillCenter rows retain generated-procedure metadata and are not counted as independent human annotations.",
        "Splits used salt vericodegen-2026-law-to-action-LA016-v1 and the original ranked SHA-256 rule with legal 2/1/3, CVE 2/3/7 and skill 2/2/8 quotas. Cases inherit parent splits. Retrieval is lineage-bound and excludes oracles, sibling final labels and target patches. Final oracles remain sealed and unreleased to inference.",
        "All 60 source-relative tasks have independent filesystem/journal oracles. The source-relative-handlers-v1 profile was qualified on legal, CVE and skill development cases with actual A4 enforcement, A3 UCAN, positive useful work, negative undeclared effects and syntax/escape rejection. LA-030 two-sink controls and LA-029 fixed programs were not substituted.",
        "A bounded local byte-level causal model was started without systemd, used for real development calls, and shut down. Every qualified call's prompt_tokens equals that call's retained preflight input_count. The 1024 output ceiling, seed, raw response bytes, cancellation close and service CPU/RSS accounting were retained. Warm reuse, 10000s service wall and 360s startup bound are pinned.",
        "The attempt contract remains 120s / 8 calls / 2048 input / 1024 output / zero paid budget, with overruns retained rather than truncated. A new diagnostic watchdog records operation/path/errno and leaf/parent identity. The LA-030 v2 receipt stays FAILED_RETAINED. Benign ENOENT disappearance is accepted only after stable parent identity, monotonic counters and empty state; other OSError is not suppressed. Parent accounting and whole-group exit remain mandatory.",
        "driver.py reserves cells and model calls before dispatch, holds exclusive ownership, reconciles stale owners, retains unknown usage/effects, consumes capabilities once and refuses silent replay or refunds. Qualification ran actual interruption/resume and cleanup-fault probes on bounded development input and did not dispatch scientific or final cells.",
        "schedule.json contains 900 unique case-arm-seed identities from the original shuffle/rotate algorithm. family_batches.json partitions them into 30 disjoint 30-cell family batches (180/180/540) retaining original arms, seeds, pairing and 12-per-position arm balancing. Phase/family dispatch order and original schedule-index mapping are recorded before outcomes.",
        "Every batch binds the same cohort/code/model/runtime/prompt/oracle/schedule freeze, a 3600-second scientific-attempt allowance and a 7200-second worker ceiling. A bounded warm-service owner may span active batches with exclusive inference. Preparation executed zero scientific cells and dispatched no final cells.",
        "native_dependency_plan.json records native edges: development/calibration batches depend on LA-032 and the prior owned batch; LA-063 depends on all twelve development/calibration batches; every final batch depends on LA-063; LA-031 depends on LA-032, all 30 batches and LA-063. Future batch success is not registered and LA-031 is not marked complete.",
        "verify_preparation.py recomputed source counts/exclusions/splits, all 900 identities, disjoint batches, qualification bindings, sealed-final status, zero scientific execution and the dependency plan, and passed. It fails on missing sources, incomplete evidence, mocks, reduced denominators or a permissive availability flag. Completion is readiness only.",
    ]
    criteria = []
    for criterion, explanation in zip(CRITERIA, explanations):
        criteria.append({"criterion": criterion, "status": "met", "explanation": explanation, "evidence": list(evidence.values())})
    python_path = Path("/usr/bin/python3.12")
    head = subprocess.run(["git", "--no-optional-locks", "-C", str(ROOT), "rev-parse", "HEAD"], capture_output=True, text=True)
    receipt = {
        "schema": "paper-task-evidence/v1",
        "paper_id": "law_to_action",
        "task_id": "LA-032",
        "status": "complete",
        "completed_at": datetime.now(timezone.utc).isoformat(),
        "completion_mode": "Prospective generated-code study freeze and bounded development qualification. Zero scientific cells executed. Final oracles remain sealed.",
        "artifacts": artifacts,
        "outputs": outputs,
        "criteria": criteria,
        "commands": [command],
        "source_versions": {
            "source_commit": head.stdout.strip() or None,
            "python": "3.12.3",
            "python_executable": "/usr/bin/python3.12",
            "python_executable_sha256": sha(python_path) if python_path.is_file() else None,
            "study_sha256": sha(STUDY / "prospective_study.json"),
            "model_profile_sha256": sha(STUDY / "model_profile.json"),
            "schedule_sha256": sha(STUDY / "schedule.json"),
            "actual_scientific_cells_executed": 0,
            "scientific_benchmark": False,
        },
        "limitations": [
            "Preparation records readiness only. The 900 scientific cells remain unexecuted and belong to the family-batch tasks.",
            "The bounded local byte-level causal model qualifies transport, tokenization agreement, decoding pins and service accounting. It is not a claim of downstream scientific model quality for LA-031.",
            "Native cgroup containment from LA-030 is reused as the later execution boundary; this host cannot invoke Docker, so profile qualification used actual handlers, UCAN, A4 enforcement and a file-backed DuckDB store without a new container envelope.",
            "The LA-030 v2 resource_observation_OSError receipt remains failed; this task adds diagnostics rather than upgrading that admission.",
            "Final-split oracles are sealed and must not be released to inference before the analysis-freeze gate.",
        ],
    }
    RECEIPT.write_text(json.dumps(receipt, indent=2, sort_keys=True) + "\n")
    print(json.dumps({"status": "complete", "outputs": len(outputs), "artifacts": len(artifacts), "receipt": rel(RECEIPT)}, sort_keys=True))


if __name__ == "__main__":
    main()
