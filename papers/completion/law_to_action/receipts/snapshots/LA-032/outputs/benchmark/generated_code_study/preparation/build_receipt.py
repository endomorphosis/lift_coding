#!/usr/bin/env python3
"""Snapshot deliverables and write the LA-032 evidence receipt."""
from __future__ import annotations

import hashlib
import json
import os
import shutil
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

HERE = Path(__file__).resolve()
STUDY = HERE.parents[1]
ROOT = STUDY.parents[4]
PAPER = STUDY.parents[1]
SNAPSHOT = PAPER / "receipts/snapshots/LA-032"
RECEIPT = PAPER / "receipts/LA-032.json"
PYTHON = "/usr/bin/python3.12"

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

DELIVERABLE_DIRS = [
    STUDY / "preparation",
    STUDY / "cohort",
    STUDY / "qualification",
]
DELIVERABLE_FILES = [
    STUDY / "model_profile.json",
    STUDY / "prospective_study.json",
    STUDY / "schedule.json",
    STUDY / "family_batches.json",
    STUDY / "native_dependency_plan.json",
    STUDY / "driver.py",
    STUDY / "verify_preparation.py",
]


def sha_file(path: Path) -> str:
    with path.open("rb") as handle:
        return hashlib.file_digest(handle, "sha256").hexdigest()


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def copy_file(src: Path, dest: Path) -> None:
    dest.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(src, dest)


def iter_deliverables():
    seen = set()
    for directory in DELIVERABLE_DIRS:
        for path in sorted(directory.rglob("*")):
            if path.is_file():
                rel = path.relative_to(ROOT)
                if rel not in seen:
                    seen.add(rel)
                    yield path
    for path in DELIVERABLE_FILES:
        rel = path.relative_to(ROOT)
        if rel not in seen:
            seen.add(rel)
            yield path


def git_head() -> str:
    result = subprocess.run(["git", "rev-parse", "HEAD"], cwd=ROOT, capture_output=True, text=True, check=False)
    return result.stdout.strip() if result.returncode == 0 else "unknown"


def main():
    if SNAPSHOT.exists():
        shutil.rmtree(SNAPSHOT)
    SNAPSHOT.mkdir(parents=True)
    validation = SNAPSHOT / "validation"
    validation.mkdir()
    argv = [
        PYTHON, "-B",
        "papers/completion/law_to_action/benchmark/generated_code_study/verify_preparation.py",
        "--study", "papers/completion/law_to_action/benchmark/generated_code_study/prospective_study.json",
        "--require-scientific-cells-unexecuted",
    ]
    started = utc_now()
    proc = subprocess.run(argv, cwd=ROOT, capture_output=True)
    completed = utc_now()
    (validation / "verify.stdout.log").write_bytes(proc.stdout)
    (validation / "verify.stderr.log").write_bytes(proc.stderr)
    if proc.returncode != 0:
        sys.stderr.write(proc.stderr.decode())
        raise SystemExit(f"verify_preparation failed: {proc.returncode}")

    artifacts = {}
    outputs = {}
    for path in iter_deliverables():
        rel = path.relative_to(ROOT)
        dest = SNAPSHOT / "outputs" / rel.relative_to("papers/completion/law_to_action")
        copy_file(path, dest)
        snap_rel = dest.relative_to(ROOT)
        artifacts[str(snap_rel)] = sha_file(dest)
        outputs[str(rel)] = str(snap_rel)

    for extra in [
        validation / "verify.stdout.log",
        validation / "verify.stderr.log",
        SNAPSHOT / "outputs" / "benchmark/generated_code_study/verify_preparation.py",
    ]:
        rel = extra.relative_to(ROOT)
        artifacts[str(rel)] = sha_file(extra)

    evidence = [
        str((SNAPSHOT / "outputs" / "benchmark/generated_code_study/cohort/sources.json").relative_to(ROOT)),
        str((SNAPSHOT / "outputs" / "benchmark/generated_code_study/cohort/lineage_audit.json").relative_to(ROOT)),
        str((SNAPSHOT / "outputs" / "benchmark/generated_code_study/cohort/splits.json").relative_to(ROOT)),
        str((SNAPSHOT / "outputs" / "benchmark/generated_code_study/cohort/cases.json").relative_to(ROOT)),
        str((SNAPSHOT / "outputs" / "benchmark/generated_code_study/cohort/sealed_final/material.json").relative_to(ROOT)),
        str((SNAPSHOT / "outputs" / "benchmark/generated_code_study/prospective_study.json").relative_to(ROOT)),
        str((SNAPSHOT / "outputs" / "benchmark/generated_code_study/schedule.json").relative_to(ROOT)),
        str((SNAPSHOT / "outputs" / "benchmark/generated_code_study/family_batches.json").relative_to(ROOT)),
        str((SNAPSHOT / "outputs" / "benchmark/generated_code_study/native_dependency_plan.json").relative_to(ROOT)),
        str((SNAPSHOT / "outputs" / "benchmark/generated_code_study/model_profile.json").relative_to(ROOT)),
        str((SNAPSHOT / "outputs" / "benchmark/generated_code_study/qualification/generated_program_profile/qualification.json").relative_to(ROOT)),
        str((SNAPSHOT / "outputs" / "benchmark/generated_code_study/qualification/model/qualification.json").relative_to(ROOT)),
        str((SNAPSHOT / "outputs" / "benchmark/generated_code_study/qualification/watchdog_diagnostic/qualification.json").relative_to(ROOT)),
        str((SNAPSHOT / "outputs" / "benchmark/generated_code_study/qualification/driver_probes/qualification.json").relative_to(ROOT)),
        str((SNAPSHOT / "outputs" / "benchmark/generated_code_study/driver.py").relative_to(ROOT)),
        str((SNAPSHOT / "outputs" / "benchmark/generated_code_study/verify_preparation.py").relative_to(ROOT)),
        str((validation / "verify.stdout.log").relative_to(ROOT)),
    ]
    explanations = [
        "Frozen 6 legal, 12 CVE and 12 skill families with actual source bytes, GovInfo/CVE-shard/SkillCenter pins, exact and normalized hashes, owner-alias and repository-name fork/clone audit plus GitHub parent lookups, and nearest-neighbor review. Every LA-004/LA-029 family is excluded. SkillCenter procedures are labeled generated and are not human annotations. Redistributed third-party bytes are 0.",
        "Ranked SHA256 split with salt vericodegen-2026-law-to-action-LA016-v1 assigns legal 2/1/3, CVE 2/3/7, skill 2/2/8. Cases inherit parent splits. Retrieval is lineage-bound and excludes oracles, sibling final labels and target patches. 36 final task/oracle bodies are sealed and not released to inference.",
        "All 60 cases have independent filesystem oracles. Profile qualification ran actual permitted, undeclared, and A4-denied constructed programs for legal, CVE and skill handlers, plus syntax and path-escape rejection. LA-030 two-sink and LA-029 fixed programs were not substituted.",
        "sshleifer/tiny-gpt2 was loaded in-process, not via systemd. Two warm development calls recorded prompt_tokens equal to retained preflight input_count. 1024 output ceiling, seed, raw response, cancellation, and CPU/RSS accounting are retained. Startup was under 360s; service wall bound is 10000s.",
        "Attempt contract remains 120s/8 calls/2048 input/1024 output/zero paid budget. New diagnostic watchdog retains operation/path/errno and leaf/parent identity. Historical v2 receipt was not upgraded and OSError is not broadly suppressed. Benign leaf disappearance revalidates parent identity, monotonic counters and empty state.",
        "DurableDriver reserves cells and model calls before dispatch, consumes once, blocks silent replay, reconciles stale owners, retains unknown interrupted effects, and refuses final/scientific dispatch during preparation. Interrupt/resume and cleanup-fault probes actually ran.",
        "schedule.json contains 900 unique identities. family_batches.json partitions them into 30 disjoint 30-cell family batches (180/180/540) with original arm/seed identities and schedule_index mapping. Dispatch order is recorded before outcomes.",
        "Every batch binds the same freeze and a 3600-second scientific-attempt allowance inside the 7200-second worker ceiling. Warm-service ownership is exclusive. Preparation executed zero scientific cells and cannot dispatch final cells.",
        "native_dependency_plan.json records explicit depends_on edges: development/calibration batches on LA-032 and prior gates; LA-063 on all twelve of those batches; final batches on LA-063; LA-031 on LA-032, all 30 batches and LA-063. No future batch success is registered and LA-031 is not marked complete.",
        "verify_preparation.py recomputed source counts, exclusions, ranked splits, 900 identities, disjoint batches, qualification bindings, sealed-final status, zero scientific execution and the dependency plan. It is fail-closed on missing sources, incomplete model/profile evidence, mocks and reduced denominators. Completion is readiness only.",
    ]
    receipt = {
        "schema": "paper-task-evidence/v1",
        "paper_id": "law_to_action",
        "task_id": "LA-032",
        "status": "complete",
        "completed_at": completed,
        "completion_mode": "Prospective qualification and freeze of the 30-family/60-case/900-cell generated-code study. Actual source bytes, ranked splits, source-relative oracles, generated-program profile, local model calls, diagnostic watchdog, durable driver probes and native dependency edges are retained. Zero scientific cells were executed. LA-031 remains incomplete.",
        "artifacts": artifacts,
        "outputs": outputs,
        "criteria": [
            {"criterion": criterion, "status": "met", "explanation": explanation, "evidence": evidence}
            for criterion, explanation in zip(CRITERIA, explanations)
        ],
        "commands": [
            {
                "argv": argv,
                "cwd": ".",
                "exit_code": 0,
                "started_at": started,
                "completed_at": completed,
                "log": str((validation / "verify.stdout.log").relative_to(ROOT)),
                "script_artifact": str((SNAPSHOT / "outputs" / "benchmark/generated_code_study/verify_preparation.py").relative_to(ROOT)),
                "environment_overrides": {
                    "LANG": "C.UTF-8",
                    "PATH": "/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin",
                    "PYTHONDONTWRITEBYTECODE": "1",
                    "PYTHONHASHSEED": "0",
                },
            }
        ],
        "source_versions": {
            "git_head": git_head(),
            "authoritative_python": PYTHON,
            "authoritative_path": "/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin",
            "split_salt": "vericodegen-2026-law-to-action-LA016-v1",
        },
        "limitations": [
            "This task freezes readiness. The 900 scientific cells remain unexecuted and LA-031 is incomplete.",
            "Policy-relative oracles are not expert legal validity or independent human semantic-fidelity labels.",
            "SkillCenter procedures carry model-generation metadata and are not independent human annotations.",
            "The historical LA-030 v2 resource_observation_OSError errno remains unproven; the new diagnostic path retains operation/path/errno without upgrading that receipt.",
            "Model qualification used a pinned tiny causal LM for bounded development calls, not the 900-cell study.",
        ],
    }
    RECEIPT.write_text(json.dumps(receipt, indent=2, sort_keys=True) + "\n")
    print(json.dumps({"status": "RECEIPT_WRITTEN", "outputs": len(outputs), "artifacts": len(artifacts), "receipt": str(RECEIPT.relative_to(ROOT))}, sort_keys=True))


if __name__ == "__main__":
    main()
