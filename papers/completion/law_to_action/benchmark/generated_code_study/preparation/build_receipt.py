#!/usr/bin/python3.12
"""Snapshot LA-032 deliverables and write the task receipt."""
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
STUDY = LIVE / "benchmark" / "generated_code_study"
SNAPSHOT = LIVE / "receipts" / "snapshots" / "LA-032"
RECEIPT = LIVE / "receipts" / "LA-032.json"
PYTHON = "/usr/bin/python3.12"
SEALED_PATH = "/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin"
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
DELIVERABLE_PATHS = [
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
sys.path.insert(0, str(STUDY / "preparation"))
from common import dumps_compact  # noqa: E402


def sha256_file(path: Path) -> str:
    with path.open("rb") as handle:
        return hashlib.file_digest(handle, "sha256").hexdigest()


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def write_json(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + ".tmp-" + uuid4().hex)
    temporary.write_text(dumps_compact(value) + "\n", encoding="utf-8")
    os.replace(temporary, path)


def iter_files(path: Path):
    if path.is_file():
        yield path
        return
    for item in sorted(path.rglob("*")):
        if item.is_file() and "__pycache__" not in item.parts and item.suffix != ".pyc":
            yield item


def copy_tree() -> dict[str, str]:
    if SNAPSHOT.exists():
        shutil.rmtree(SNAPSHOT)
    SNAPSHOT.mkdir(parents=True)
    outputs = {}
    for source in DELIVERABLE_PATHS:
        for path in iter_files(source):
            relative = path.relative_to(ROOT)
            dest = SNAPSHOT / "outputs" / relative
            dest.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(path, dest)
            outputs[str(relative)] = str(dest.relative_to(ROOT))
    shutil.copy2(STUDY / "verify_preparation.py", SNAPSHOT / "verify_preparation.py")
    return outputs


def run_command(argv: list[str], log_name: str, env: dict[str, str]) -> dict[str, object]:
    validation = SNAPSHOT / "validation"
    validation.mkdir(parents=True, exist_ok=True)
    stdout_path = validation / f"{log_name}.stdout.log"
    stderr_path = validation / f"{log_name}.stderr.log"
    started = utc_now()
    completed = subprocess.run(argv, cwd=str(ROOT), env=env, capture_output=True, text=True, check=False)
    ended = utc_now()
    stdout_path.write_text(completed.stdout)
    stderr_path.write_text(completed.stderr)
    if completed.returncode != 0:
        raise SystemExit(f"command failed ({completed.returncode}): {argv}\n{completed.stdout}\n{completed.stderr}")
    record = {
        "argv": argv,
        "cwd": ".",
        "exit_code": completed.returncode,
        "started_at": started,
        "completed_at": ended,
        "log": str((validation / f"{log_name}.stdout.log").relative_to(ROOT)),
        "environment_overrides": {
            "PATH": env["PATH"],
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
    snapshot_prefix = str(SNAPSHOT.relative_to(ROOT)).rstrip("/") + "/"
    if isinstance(script, str) and script.startswith(snapshot_prefix):
        record["script_artifact"] = script
    return record


def git_rev(path: Path) -> str | None:
    result = subprocess.run(
        ["git", "--no-optional-locks", "-C", str(path), "rev-parse", "HEAD"],
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode != 0:
        return None
    return result.stdout.strip() or None


def main() -> int:
    env = os.environ.copy()
    env.update(
        {
            "PATH": SEALED_PATH,
            "PYTHONDONTWRITEBYTECODE": "1",
            "OMP_NUM_THREADS": "1",
            "OPENBLAS_NUM_THREADS": "1",
            "MKL_NUM_THREADS": "1",
            "NUMEXPR_NUM_THREADS": "1",
            "VECLIB_MAXIMUM_THREADS": "1",
            "LANG": "C.UTF-8",
            "PYTHONHASHSEED": "0",
        }
    )
    outputs = copy_tree()
    commands = []
    commands.append(
        run_command(
            [
                PYTHON,
                "-B",
                "papers/completion/law_to_action/benchmark/generated_code_study/verify_preparation.py",
                "--study",
                "papers/completion/law_to_action/benchmark/generated_code_study/prospective_study.json",
                "--require-scientific-cells-unexecuted",
            ],
            "verify",
            env,
        )
    )
    artifacts = {}
    for path in sorted(SNAPSHOT.rglob("*")):
        if not path.is_file():
            continue
        artifacts[str(path.relative_to(ROOT))] = sha256_file(path)
    snap = "papers/completion/law_to_action/receipts/snapshots/LA-032/"
    out = snap + "outputs/papers/completion/law_to_action/benchmark/generated_code_study/"
    evidence = {
        "sources": out + "cohort/sources.json",
        "splits": out + "cohort/splits.json",
        "audit": out + "cohort/lineage_audit.json",
        "cases": out + "cohort/cases.jsonl",
        "mappings": out + "cohort/source_task_oracle_mappings.json",
        "seal": out + "cohort/sealed/SEAL.json",
        "profile": out + "qualification/profile/qualification.json",
        "model": out + "qualification/model/qualification.json",
        "model_profile": out + "model_profile.json",
        "watchdog": out + "qualification/watchdog/qualification.json",
        "deadline": out + "qualification/deadline/qualification.json",
        "driver": out + "qualification/driver/qualification.json",
        "study": out + "prospective_study.json",
        "schedule": out + "schedule.json",
        "batches": out + "family_batches.json",
        "plan": out + "native_dependency_plan.json",
        "verify": snap + "validation/verify.stdout.log",
        "verifier": snap + "verify_preparation.py",
    }
    criterion_evidence = {
        0: ["sources", "audit", "cases", "seal"],
        1: ["splits", "cases", "seal", "study"],
        2: ["cases", "mappings", "profile", "seal"],
        3: ["model", "model_profile", "verify"],
        4: ["deadline", "watchdog", "study"],
        5: ["driver", "study"],
        6: ["schedule", "batches", "study"],
        7: ["batches", "study", "model_profile"],
        8: ["plan", "batches"],
        9: ["verify", "verifier", "study", "sources", "splits", "schedule", "batches", "plan"],
    }
    for value in evidence.values():
        if value not in artifacts:
            raise SystemExit("missing snapshot evidence: " + value)
    explanations = [
        "cohort/sources.json freezes 6 legal, 12 CVE and 12 skill families with actual cache bytes, SHA-256, upstream revisions, retrieval-only terms and lawful-access marks. lineage_audit.json records same-name fork/clone exclusion, cross-population repository exclusion, exact/normalized hashes and shingle nearest-neighbor review. Every LA-004/LA-029 family is excluded. SkillCenter procedures with model-generation metadata are not counted as independent human annotations.",
        "cohort/splits.json reapplies salt vericodegen-2026-law-to-action-LA016-v1 with legal 2/1/3, CVE 2/3/7 and skill 2/2/8. Cases inherit parent splits. Retrieval is family-bound and marked contains_oracle/sibling_final_label/target_patch false. Final oracles are sealed in cohort/sealed with released=false.",
        "60 source-relative cases and independent filesystem/journal oracles are in cases.jsonl and source_task_oracle_mappings.json. qualification/profile records positive useful-work and negative undeclared-effect executions for legal, CVE and skill development cases, syntax/escape rejection, and a native UCAN/obligation probe. The LA-030 two-sink profile is not substituted.",
        "qualification/model/qualification.json records two bounded loopback development calls whose prompt_tokens equal retained preflight input_count, 1024 output ceiling, seed application, raw response bytes, cancellation, startup under 360s and a 10000s service wall pin. systemd is not required. model_profile.json pins weights, tokenizer, chat template, deployment and decoding.",
        "qualification/deadline/qualification.json binds the scientific 120s complete-attempt envelope across template/tokenize/inference/execution/cleanup and the 8/2048/1024/zero-paid contract, retaining overrun and unknown cgroup memory. qualification/watchdog retains operation/path/errno plus leaf/parent identities for a reconstructed resource_observation_OSError; the historical v2 receipt is not upgraded and OSError is not broadly suppressed. Benign leaf disappearance revalidates stable empty parent identity and monotonic counters.",
        "qualification/driver/qualification.json runs actual reserve/interrupt/resume, stale-owner reconciliation, one-time capability consumption, refund/replay refusal, unknown cleanup-effect handling and sealed-final refusal under bounded development input rather than flags alone.",
        "schedule.json and family_batches.json freeze 900 unique identities as 30 disjoint family batches of 30 cells (180/180/540). Dispatch order records each batch's mapping onto the original seed/arm-position schedule without resampling contrasts.",
        "Every batch is bound to the same freeze, a 3600-second scientific-attempt allowance and a 7200-second worker ceiling. Warm-service ownership is exclusive. prospective_study.json records scientific_cells_executed=0, final_material_released=false and no final-cell dispatch.",
        "native_dependency_plan.json binds actual family IDs. Development/calibration tasks depend on LA-032 and prior batch/phase gates; LA-063 depends on all twelve development/calibration batches; every final batch depends on LA-063; LA-031 receives explicit edges to LA-032, LA-033–LA-062 and LA-063. future_batch_success_registered and la031_marked_complete are false.",
        "verify_preparation.py recomputed source counts/exclusions/splits, 900 identities, disjoint batches, qualification bindings, sealed-final status, zero scientific execution and the dependency plan. It fails closed on missing sources, incomplete pins, mocks, reduced denominators or a permissive availability flag. Completion is readiness only.",
    ]
    criteria = []
    for index, (criterion, explanation) in enumerate(zip(CRITERIA, explanations)):
        criteria.append(
            {
                "criterion": criterion,
                "status": "met",
                "explanation": explanation,
                "evidence": [evidence[key] for key in criterion_evidence[index]],
            }
        )
    receipt = {
        "schema": "paper-task-evidence/v1",
        "paper_id": "law_to_action",
        "task_id": "LA-032",
        "status": "complete",
        "completed_at": utc_now(),
        "completion_mode": "Prospective qualification and freeze of the generated-code study. 30 source families, 60 source-relative cases, 900 identities and 30 family batches are frozen. Model/runtime/profile/driver/watchdog qualification used bounded development inputs. Scientific cells executed: 0. Final material remains sealed. This is readiness for family-batch execution, not LA-031 completion.",
        "artifacts": artifacts,
        "outputs": outputs,
        "criteria": criteria,
        "commands": commands,
        "limitations": [
            "Readiness only; the 900 scientific cells remain unrun for LA-033–LA-062.",
            "Kernel cgroup parent creation and Docker were unavailable; watchdog diagnostics used a reconstructed cgroup file tree while native handler effects ran in-process.",
            "The bounded development transformer is a digest-bound local model for transport/tokenization qualification, not a claim of scientific code-generation quality.",
            "SkillCenter procedures carry model-generation metadata and are not independent human annotations.",
            "GitHub parent/fork graph was not retrieved; fork/clone audit used identity, same-name collisions, commits, hashes and nearest-neighbor text.",
            "Historical LA-030 v2 resource_observation_OSError receipt is retained unupgraded; its original errno/path remain unproven.",
        ],
        "source_versions": {
            "repository_head": git_rev(ROOT),
            "ipfs_accelerate": git_rev(ROOT / "external" / "ipfs_accelerate"),
            "ipfs_datasets": git_rev(ROOT / "external" / "ipfs_datasets"),
            "ipfs_kit": git_rev(ROOT / "external" / "ipfs_kit"),
            "authoritative_python": PYTHON,
            "authoritative_path": SEALED_PATH,
            "study_files": {
                "prospective_study.json": sha256_file(STUDY / "prospective_study.json"),
                "model_profile.json": sha256_file(STUDY / "model_profile.json"),
                "verify_preparation.py": sha256_file(STUDY / "verify_preparation.py"),
                "driver.py": sha256_file(STUDY / "driver.py"),
            },
        },
    }
    write_json(RECEIPT, receipt)
    print(json.dumps({"status": "complete", "artifacts": len(artifacts), "outputs": len(outputs)}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
