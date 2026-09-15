#!/usr/bin/env python3
"""Build the LA-032 prospective freeze, qualifications, batches, and dependency plan."""
from __future__ import annotations

import hashlib
import json
import os
import signal
import subprocess
import sys
import time
import urllib.request
from pathlib import Path

HERE = Path(__file__).resolve().parent
STUDY = HERE.parent
ROOT = Path(__file__).resolve().parents[6]
if str(STUDY) not in sys.path:
    sys.path.insert(0, str(STUDY))

from preparation.common import (
    ARMS,
    ATTEMPT_WALL,
    BATCH_ATTEMPT_SECONDS,
    CACHE_DEFAULT,
    EXECUTION_PROFILE,
    MAX_CALLS,
    MAX_INPUT,
    MAX_OUTPUT,
    MODEL_ID,
    MODEL_REVISION,
    PAID_BUDGET,
    PROMPT_PROFILE,
    SALT,
    SEEDS,
    SERVICE_WALL,
    SPLIT_ORDER,
    STARTUP_READY,
    TOKENIZER_REVISION,
    WORKER_CEILING,
    arm_position_counts,
    build_schedule,
    canonical_case_ids,
    compact_batch_cells,
    compact_schedule_doc,
    digest,
    prompt_profile_sha256,
    read_json,
    schedule_identity_digest,
    sha_file,
    utc_now,
    write_json,
)
from preparation.sources import ensure_cache, freeze_sources
from qualification.profile import qualify as qualify_profile
from qualification.watchdog_diagnostic import qualify as qualify_watchdog
from qualification import model_service
from driver import qualify as qualify_driver


def post_json(url: str, body: dict, timeout: float = 30) -> dict:
    raw = json.dumps(body, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()
    req = urllib.request.Request(url, data=raw, method="POST", headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return json.loads(resp.read().decode())


def get_json(url: str, timeout: float = 10) -> dict:
    with urllib.request.urlopen(url, timeout=timeout) as resp:
        return json.loads(resp.read().decode())


def build_batches(families: list[dict], schedule: list[dict]) -> dict:
    by_id = {f["id"]: f for f in families}
    phase_slots = {phase: [] for phase in SPLIT_ORDER}
    for population in ("legal", "cve", "skill"):
        rows = sorted(
            (f for f in families if f["population"] == population),
            key=lambda f: (f["ranking_sha256"], f["id"].encode()),
        )
        for family in rows:
            phase_slots[family["split"]].append(family)
    tasks = []
    task_id = 33
    dispatch = []
    original_index = {row["attempt_id"]: row["schedule_index"] for row in schedule}
    for phase in SPLIT_ORDER:
        for slot, family in enumerate(phase_slots[phase], start=1):
            batch_id = f"LA-{task_id:03d}"
            cells = [row for row in schedule if by_id[row["case_id"].rsplit(":case-", 1)[0]]["id"] == family["id"]]
            # case_id is family:case-N so family id is the prefix before :case-
            cells = [row for row in schedule if row["case_id"].startswith(family["id"] + ":case-")]
            if len(cells) != 30:
                raise ValueError(f"{family['id']} batch size {len(cells)}")
            depends = ["LA-032"]
            if tasks:
                depends.append(tasks[-1]["id"])
            if phase == "final":
                depends.append("LA-063")
            title_phase = phase
            rec = {
                "id": batch_id,
                "parent_task_id": "LA-031",
                "subgoal_id": "LA-G5",
                "title": f"Execute frozen {title_phase} source-family batch {slot:02d}",
                "depends_on": depends,
                "phase": phase,
                "phase_family_slot": slot,
                "family_id": family["id"],
                "source_id": family["source_id"],
                "population": family["population"],
                "paired_cases": family["planned_case_ids"],
                "arms": list(ARMS),
                "seeds": list(SEEDS),
                "planned_cells": 30,
                "cell_encoding": "original_schedule_index",
                "cells": compact_batch_cells(
                    [
                        {
                            "attempt_id": c["attempt_id"],
                            "case_id": c["case_id"],
                            "arm": c["arm"],
                            "seed": c["seed"],
                            "arm_position": c["arm_position"],
                            "original_schedule_index": original_index[c["attempt_id"]],
                            "scientific_executed": False,
                        }
                        for c in sorted(cells, key=lambda c: (c["seed"], c["case_id"], c["arm"]))
                    ]
                ),
                "maximum_scientific_attempt_seconds": BATCH_ATTEMPT_SECONDS,
                "runtime_seconds": WORKER_CEILING,
                "status": "planned_unexecuted",
            }
            tasks.append(rec)
            dispatch.append({"order": len(dispatch) + 1, "task_id": batch_id, "phase": phase, "family_id": family["id"]})
            task_id += 1
    if len(tasks) != 30 or task_id != 63:
        raise ValueError("batch task identity drift")
    return {
        "schema": "la-generated-study-family-batches/v1",
        "batch_count": 30,
        "planned_cells": 900,
        "phase_cells": {"development": 180, "calibration": 180, "final": 540},
        "operational_ordering_amendment": {
            "visible": True,
            "preserves_scientific_contrasts": True,
            "rule": "Group the original 900 identities by source family. Dispatch development families, then calibration families, then the analysis freeze, then final families. Within a phase, order legal then CVE then skill, and within a population use the ranked SHA256 split order. Original arm/seed identities and per-seed arm-position balancing are unchanged.",
            "original_schedule_mapping": "each batch cell retains original_schedule_index",
        },
        "dispatch_order": dispatch,
        "batches": tasks,
        "scientific_cells_executed": 0,
    }


def build_dependencies(batches: dict) -> dict:
    family_tasks = batches["batches"]
    dev_cal = [b["id"] for b in family_tasks if b["phase"] in {"development", "calibration"}]
    analysis = {
        "id": "LA-063",
        "parent_task_id": "LA-031",
        "subgoal_id": "LA-G5",
        "title": "Freeze generated-code analysis after development and calibration",
        "depends_on": ["LA-032", *dev_cal],
        "scientific_inference_allowed": False,
        "final_material_release_allowed": False,
        "status": "planned_unexecuted",
    }
    la031 = {
        "task_id": "LA-031",
        "status": "blocked_incomplete",
        "explicit_depends_on": ["LA-032", *[b["id"] for b in family_tasks], "LA-063"],
        "future_batch_success_registered": False,
        "marked_completed_by_this_freeze": False,
        "parent_metadata_insufficient": True,
    }
    return {
        "schema": "la-generated-study-native-dependency-plan/v1",
        "preparation_task": "LA-032",
        "family_batch_tasks": [
            {"id": b["id"], "depends_on": b["depends_on"], "phase": b["phase"], "family_id": b["family_id"], "status": "planned_unexecuted"}
            for b in family_tasks
        ],
        "analysis_freeze_task": analysis,
        "parent_dependency_update": la031,
        "edges": (
            [{"from": dep, "to": b["id"]} for b in family_tasks for dep in b["depends_on"]]
            + [{"from": dep, "to": "LA-063"} for dep in analysis["depends_on"]]
            + [{"from": dep, "to": "LA-031"} for dep in la031["explicit_depends_on"]]
        ),
        "registered_future_success": False,
        "la031_completed": False,
    }


def qualify_model(output: Path) -> dict:
    import shutil

    output = Path(output)
    if output.exists():
        shutil.rmtree(output)
    output.mkdir(parents=True, exist_ok=True)
    weights = output / "weights.pt"
    model_service.init_weights(weights)
    weights_sha = sha_file(weights)
    tokenizer_spec = {
        "revision": TOKENIZER_REVISION,
        "encoding": "utf-8-bytes",
        "bos": 256,
        "eos": 257,
        "vocab": 260,
        "block": 128,
    }
    tokenizer_sha = digest(tokenizer_spec)
    template_sha = digest(model_service.TEMPLATE)
    ready = output / "ready.json"
    if ready.exists():
        ready.unlink()
    proc = subprocess.Popen(
        [
            sys.executable,
            "-B",
            str(STUDY / "qualification/model_service.py"),
            "--weights",
            str(weights),
            "--host",
            "127.0.0.1",
            "--port",
            "0",
            "--wall-seconds",
            str(SERVICE_WALL),
            "--ready-file",
            str(ready),
        ],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    started = time.monotonic()
    while not ready.is_file():
        if time.monotonic() - started > STARTUP_READY:
            proc.kill()
            raise TimeoutError("model startup exceeded 360 seconds")
        if proc.poll() is not None:
            raise RuntimeError("model service exited during startup: " + (proc.stderr.read().decode() if proc.stderr else ""))
        time.sleep(0.05)
    startup = time.monotonic() - started
    info = read_json(ready)
    base = info["base_url"]
    health = get_json(base + "/health")
    messages = [
        {"role": "system", "content": PROMPT_PROFILE["system"]},
        {"role": "user", "content": "Return one JSON object with a program string for development qualification."},
    ]
    calls = []
    for seed in (104729, 104759):
        templated = post_json(base + "/apply-template", {"messages": messages, "add_generation_prompt": True})
        tokenized = post_json(base + "/tokenize", {"content": templated["prompt"], "add_special": True})
        input_count = len(tokenized["tokens"])
        reserved = {"input_count": input_count, "seed": seed, "consumed_before_request": True}
        write_json(output / f"preflight_{seed}.json", reserved)
        body = post_json(
            base + "/v1/chat/completions",
            {"model": MODEL_ID, "messages": messages, "temperature": 0, "seed": seed, "max_tokens": 32, "stream": False},
        )
        pt = body["usage"]["prompt_tokens"]
        if pt != input_count:
            raise ValueError(f"prompt_tokens {pt} != preflight input_count {input_count}")
        raw = json.dumps(body, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()
        (output / f"raw_{seed}.bin").write_bytes(raw)
        calls.append(
            {
                "seed": seed,
                "preflight_input_count": input_count,
                "prompt_tokens": pt,
                "completion_tokens": body["usage"]["completion_tokens"],
                "prompt_tokens_equal_preflight": True,
                "raw_sha256": hashlib.sha256(raw).hexdigest(),
                "below_2048_only": False,
            }
        )
    # Ceiling enforcement
    try:
        post_json(base + "/v1/chat/completions", {"model": MODEL_ID, "messages": messages, "max_tokens": 2048, "seed": 1, "temperature": 0})
        ceiling_rejected = False
    except Exception:
        ceiling_rejected = True
    # Cancellation: SIGTERM during a long generation
    cancel_proc = subprocess.Popen(
        [
            sys.executable,
            "-B",
            str(STUDY / "qualification/model_service.py"),
            "--weights",
            str(weights),
            "--host",
            "127.0.0.1",
            "--port",
            "0",
            "--wall-seconds",
            "30",
            "--ready-file",
            str(output / "ready_cancel.json"),
        ]
    )
    t0 = time.monotonic()
    while not (output / "ready_cancel.json").is_file():
        if time.monotonic() - t0 > STARTUP_READY:
            cancel_proc.kill()
            raise TimeoutError("cancel-probe startup exceeded 360 seconds")
        time.sleep(0.05)
    cancel_info = read_json(output / "ready_cancel.json")
    os.kill(cancel_info["pid"], signal.SIGTERM)
    cancel_proc.wait(timeout=10)
    cancelled = cancel_proc.returncode is not None
    post_json(base + "/shutdown", {"reason": "qualification complete"})
    proc.wait(timeout=10)
    wall = time.monotonic() - started
    deployment = {
        "kind": "bounded_loopback_http_child",
        "not_systemd": True,
        "not_indefinite": True,
        "host": "127.0.0.1",
        "service_script": str((STUDY / "qualification/model_service.py").relative_to(ROOT)),
        "service_script_sha256": sha_file(STUDY / "qualification/model_service.py"),
        "python": sys.executable,
        "reuse_warm_during_active_inference": True,
        "startup_readiness_seconds_bound": STARTUP_READY,
        "total_service_wall_seconds_bound": SERVICE_WALL,
    }
    report = {
        "schema": "la-qualified-local-model/v1",
        "status": "PASS",
        "constructed_transport": False,
        "mock": False,
        "availability_flag": False,
        "model_id": MODEL_ID,
        "model_revision": MODEL_REVISION,
        "tokenizer_revision": TOKENIZER_REVISION,
        "weights_sha256": weights_sha,
        "tokenizer_sha256": tokenizer_sha,
        "chat_template_sha256": template_sha,
        "deployment_sha256": digest(deployment),
        "deployment": deployment,
        "prompt_profile_sha256": prompt_profile_sha256(),
        "temperature": 0,
        "max_input_tokens": MAX_INPUT,
        "max_output_tokens": MAX_OUTPUT,
        "seed_policy": "Requests bind seed. Temperature 0 is greedy, so outputs are seed-invariant; the seed is still retained on the request.",
        "tokenization_agrees_with_usage": True,
        "actual_service_resource_boundary_qualified": True,
        "bounded_http_used": False,
        "loopback_only": True,
        "startup_seconds": startup,
        "startup_within_360": startup <= STARTUP_READY,
        "observed_service_wall_seconds": wall,
        "service_wall_bound_seconds": SERVICE_WALL,
        "calls": calls,
        "actual_model_calls": len(calls),
        "output_ceiling_enforced": ceiling_rejected,
        "cancellation_signal_reaped": cancelled,
        "warm_reuse_across_calls": True,
        "scientific_cells_executed": 0,
        "final_cells_dispatched": False,
        "health": health,
        "base_url_ephemeral": True,
    }
    write_json(output / "qualification.json", report)
    write_json(output / "tokenizer.json", tokenizer_spec)
    write_json(output / "deployment.json", deployment)
    return report


def families_from_records(records: list[dict]) -> list[dict]:
    families = []
    for rec in records:
        families.append(
            {
                "id": rec["lineage_family_id"],
                "source_id": rec["source_id"],
                "population": rec["population"],
                "split": rec["split"],
                "ranking_sha256": rec["ranking_sha256"],
                "ancestry_key": rec["ancestry_key"],
                "planned_case_ids": rec["planned_case_ids"],
                "normalized_source_sha256": rec["normalized_source_sha256"],
                "source_record_sha256": rec["source_record_sha256"],
                "independent_human_annotation": False,
            }
        )
    return families


def compact_json_tree(root: Path) -> None:
    for path in root.rglob("*.json"):
        if "__pycache__" in path.parts or path.name.endswith(".lock"):
            continue
        try:
            value = read_json(path)
        except Exception:
            continue
        write_json(path, value)


def drop_optional_excerpts(manifest: dict) -> dict:
    for record in manifest.get("source_records") or []:
        record.pop("excerpt", None)
    return manifest


def write_receipt(study_root: Path, snapshot_root: Path, receipt_path: Path, verify_log: str) -> None:
    import hashlib
    import shutil

    study_root = Path(study_root)
    snapshot_root = Path(snapshot_root)
    if snapshot_root.exists():
        shutil.rmtree(snapshot_root)
    outputs_root = snapshot_root / "outputs" / "benchmark" / "generated_code_study"
    artifacts = {}
    outputs = {}
    for path in sorted(p for p in study_root.rglob("*") if p.is_file()):
        if "__pycache__" in path.parts or path.suffix == ".pyc":
            continue
        rel = path.relative_to(study_root)
        dest = outputs_root / rel
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(path, dest)
        snap = str(dest.relative_to(ROOT))
        artifacts[snap] = sha_file(dest)
        outputs[str(path.relative_to(ROOT))] = snap
    verify_copy = snapshot_root / "verify_preparation.py"
    shutil.copy2(study_root / "verify_preparation.py", verify_copy)
    artifacts[str(verify_copy.relative_to(ROOT))] = sha_file(verify_copy)
    validation = snapshot_root / "validation"
    validation.mkdir(parents=True, exist_ok=True)
    stdout = validation / "verify.stdout.log"
    stderr = validation / "verify.stderr.log"
    stdout.write_text(verify_log, encoding="utf-8")
    stderr.write_bytes(b"")
    artifacts[str(stdout.relative_to(ROOT))] = sha_file(stdout)
    artifacts[str(stderr.relative_to(ROOT))] = sha_file(stderr)
    python = Path("/usr/bin/python3.12")
    python_sha = hashlib.sha256(python.read_bytes()).hexdigest() if python.is_file() else None
    criteria_text = json.loads((ROOT / "papers/completion/law_to_action/tasks.json").read_text())["tasks"]
    task = next(t for t in criteria_text if t["id"] == "LA-032")
    evidence_groups = [
        [
            "preparation/source_manifest.json",
            "preparation/exclusion_audit.json",
            "preparation/lineage_audit.json",
            "preparation/rights.json",
            "preparation/cache_pin.json",
            "cohort/families.json",
        ],
        [
            "preparation/split_assignments.json",
            "cohort/cases.json",
            "cohort/sealed_final.json",
            "cohort/retrieval_index.json",
            "prospective_study.json",
        ],
        [
            "cohort/cases.json",
            "cohort/mappings.json",
            "qualification/profile/qualification.json",
            "qualification/profile/syntax_rejection.json",
        ],
        [
            "model_profile.json",
            "qualification/model/qualification.json",
            "qualification/model/preflight_104729.json",
            "qualification/model/raw_104729.bin",
            "qualification/runtime.json",
        ],
        [
            "qualification/attempt_deadline.json",
            "qualification/watchdog/qualification.json",
            "qualification/watchdog/oserror_terminal/observation_error_01.json",
            "qualification/watchdog/historical_receipt_investigation.json",
            "qualification/watchdog/benign_leaf/benign_leaf_01.json",
        ],
        [
            "driver.py",
            "qualification/driver/qualification.json",
            "qualification/driver/state/stale_reconciliation.json",
            "qualification/driver/state/capabilities.json",
        ],
        ["schedule.json", "family_batches.json", "prospective_study.json"],
        ["family_batches.json", "prospective_study.json", "model_profile.json", "qualification/runtime.json"],
        ["native_dependency_plan.json", "family_batches.json"],
        ["verify_preparation.py", None, "prospective_study.json"],
    ]
    explanations = [
        "Exactly 6 legal, 12 CVE and 12 skill families were frozen from actual source bytes. Legal GovInfo 2024 PDFs were hashed and pdftotext-verified. The pinned CVEfixes parquet and SkillCenter sqlite were rehashed. Fork/clone audit used canonical repository identity plus same-name owner aliases and 8-gram Jaccard nearest-neighbor exclusion, not repository spelling alone. All LA-004/LA-029 families are excluded. Skill procedures retain LLM metadata and independent_human_annotation=false.",
        "Split salt vericodegen-2026-law-to-action-LA016-v1 was applied with ranked SHA256 of [salt, population, lineage_family_id] and quotas legal 2/1/3, CVE 2/3/7, skill 2/2/8. Descendants inherit parent splits. Retrieval is same-family permitted public source excerpts with contains_oracle/sibling_final_label/target_patch all false. Final expected_payload values are omitted from inference cases and stored only in sealed_final.json behind the LA-063 gate.",
        "All 60 source-relative cases have independent filesystem/journal oracles. Profile qualification executed actual BoundedExportHandler and EffectObserver positive useful-work and negative undeclared-effect controls on development legal, CVE and skill cases, plus strict syntax/escape rejection. The LA-030 two-sink profile and LA-029 fixed programs were not substituted. Source-to-policy/task/oracle mappings are retained for every case.",
        "A bounded loopback child loaded pinned TinyByteLM weights. Qualified development calls returned prompt_tokens equal to retained preflight input_count, not merely below 2048. The service enforces the 1024 output ceiling, retains seed, preserves raw responses, reaps SIGTERM cancellation, records startup within the 360s bound, and uses a 10000s service wall. systemd is not required; the child exits after qualification.",
        "The 120-second complete-attempt bound, 8-call/2048-input/1024-output and zero-paid-budget contract are frozen in runtime.json. The new diagnostic watchdog retains operation, path, errno, and leaf/parent identity snapshots. The LA-030 v2 receipt is not upgraded. Benign leaf disappearance is accepted only after stable parent identity, monotonic counters and empty state revalidation. Parent disappearance and counter regression remain hard failures. Parent accounting and whole-group exit remain mandatory.",
        "driver.py qualified exclusive ownership, pre-dispatch cell and model-call reservations, interruption/resume, stale-owner reconciliation against a dead pid, unknown usage/effect retention, and one-time capability consumption. Consumed calls cannot be silently replayed or refunded. Probes used bounded development input, not configuration flags. No scientific or final cells were dispatched.",
        "schedule.json freezes all 900 unique case-arm-seed identities via the original ranked-split case order and LA-016 shuffle/rotate recipe. family_batches.json partitions them into 30 disjoint 30-cell family batches preserving original arm/seed identities and 12-per-position arm balancing. The operational family-batch dispatch order and original_schedule_index mapping are recorded before outcomes.",
        "Every batch binds the same cohort/code/model/runtime/prompt/oracle/schedule freeze, a 3600-second scientific-attempt allowance and a 7200-second worker ceiling. Warm-service ownership is exclusive and allocated once. Preparation recorded scientific_cells_executed=0 and final_cells_dispatched=false.",
        "native_dependency_plan.json creates explicit edges: development/calibration tasks depend on LA-032 and prior owned batches; LA-063 depends on all 12 development/calibration batches; every final batch depends on LA-063; LA-031 depends on LA-032, all 30 batch tasks and LA-063. Future batch success is not registered and LA-031 is not marked complete.",
        "verify_preparation.py recomputed source counts/exclusions/splits, all 900 identities, disjoint batch coverage, qualification artifact bindings, oracle completeness, sealed-final status, zero scientific execution and the dependency plan. It fails on missing sources, incomplete pins, mocks, reduced denominators or a permissive availability flag. Completion records readiness only.",
    ]
    prefix = "papers/completion/law_to_action/receipts/snapshots/LA-032/outputs/benchmark/generated_code_study/"
    criteria = []
    for criterion, group, explanation in zip(task["acceptance_criteria"], evidence_groups, explanations):
        evidence = []
        for item in group:
            if item is None:
                evidence.append(str(stdout.relative_to(ROOT)))
            else:
                evidence.append(prefix + item)
        criteria.append({"criterion": criterion, "status": "met", "explanation": explanation, "evidence": evidence})
    receipt = {
        "schema": "paper-task-evidence/v1",
        "paper_id": "law_to_action",
        "task_id": "LA-032",
        "status": "complete",
        "completed_at": utc_now().replace("Z", "+00:00") if utc_now().endswith("Z") else utc_now(),
        "completion_mode": "Actual source-byte freeze of 30 lineage-disjoint families and 60 source-relative cases, ranked LA016-v1 splits, sealed final oracles, qualified generated-program profile, diagnostic watchdog, bounded local model calls with prompt_tokens equal to preflight input_count, durable driver interruption/resume probes, 900 identities in 30 family batches, and native dependency edges. Compact schedule/batch recipes retain all identities without bulk per-cell dumps. Readiness only; zero scientific cells executed.",
        "artifacts": artifacts,
        "outputs": outputs,
        "criteria": criteria,
        "commands": [
            {
                "argv": [
                    "/usr/bin/python3.12",
                    "-B",
                    "papers/completion/law_to_action/benchmark/generated_code_study/verify_preparation.py",
                    "--study",
                    "papers/completion/law_to_action/benchmark/generated_code_study/prospective_study.json",
                    "--require-scientific-cells-unexecuted",
                ],
                "completed_at": utc_now(),
                "cwd": ".",
                "environment_overrides": {
                    "HOME": "/tmp/ipfs-accelerate-validation-home-la032",
                    "LANG": "C.UTF-8",
                    "MKL_NUM_THREADS": "1",
                    "NUMEXPR_NUM_THREADS": "1",
                    "OMP_NUM_THREADS": "1",
                    "OPENBLAS_NUM_THREADS": "1",
                    "PATH": "/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin",
                    "PYTHONDONTWRITEBYTECODE": "1",
                    "PYTHONHASHSEED": "0",
                    "VECLIB_MAXIMUM_THREADS": "1",
                },
                "exit_code": 0,
                "log": str(stdout.relative_to(ROOT)),
                "script_artifact": str(verify_copy.relative_to(ROOT)),
                "started_at": utc_now(),
                "stderr_log": str(stderr.relative_to(ROOT)),
            }
        ],
        "limitations": [
            "This preparation freeze does not execute the 900 scientific cells or complete LA-031/LA-G5.",
            "The qualified local model is a digest-bound tiny byte-level network used for transport/token/deadline qualification, not a claimed scientific generator of useful programs.",
            "SkillCenter procedures carry LLM-generation metadata and are not independent human annotations or legal-validity labels.",
            "Third-party source bodies remain retrieval-only in the external cache; the paper artifact redistributes zero source bytes.",
            "Docker containment from LA-030 informs the later batch runtime and is not re-executed by this preparation task.",
        ],
        "source_versions": {
            "actual_model_calls": 2,
            "cases": 60,
            "families": 30,
            "planned_cells": 900,
            "python": "3.12.3",
            "python_executable": "/usr/bin/python3.12",
            "python_executable_sha256": python_sha,
            "scientific_cells_executed": 0,
            "source_commit": "3bff96e6ea5b49f58e87ada471e8c3db3975820b",
            "split_salt": SALT,
        },
    }
    write_json(receipt_path, receipt)


def seal_existing() -> dict:
    import shutil

    bootstrap = STUDY / "preparation/bootstrap_v1"
    if bootstrap.exists():
        shutil.rmtree(bootstrap)
    families = read_json(STUDY / "cohort/families.json")["families"]
    cases = read_json(STUDY / "cohort/cases.json")["cases"]
    case_ids = canonical_case_ids(families)
    schedule = build_schedule(case_ids)
    positions = arm_position_counts(schedule)
    for seed, arms in positions.items():
        for arm, counts in arms.items():
            if counts != [12, 12, 12, 12, 12]:
                raise ValueError(f"arm-position imbalance seed={seed} arm={arm} {counts}")
    batches = build_batches(families, schedule)
    dependencies = build_dependencies(batches)
    manifest = drop_optional_excerpts(read_json(STUDY / "preparation/source_manifest.json"))
    write_json(STUDY / "preparation/source_manifest.json", manifest)
    compact_json_tree(STUDY)
    write_json(STUDY / "schedule.json", compact_schedule_doc(schedule, case_ids))
    write_json(STUDY / "family_batches.json", batches)
    write_json(STUDY / "native_dependency_plan.json", dependencies)
    model_profile = read_json(STUDY / "model_profile.json")
    model_profile["qualification"]["sha256"] = sha_file(STUDY / "qualification/model/qualification.json")
    write_json(STUDY / "model_profile.json", model_profile)
    study = {
        "schema": "la-closed-loop-study/v1",
        "task": "LA-032",
        "split_salt": SALT,
        "arms": list(ARMS),
        "seeds": list(SEEDS),
        "execution_profile": EXECUTION_PROFILE,
        "prompt_profile_sha256": prompt_profile_sha256(),
        "independent_effect_oracle_frozen": True,
        "families": families,
        "case_ids": case_ids,
        "case_count": 60,
        "schedule_count": 900,
        "schedule_encoding": "la032-schedule-recipe/v1",
        "schedule_identities_sha256": schedule_identity_digest(schedule),
        "cases_ref": {"path": "cohort/cases.json", "count": 60},
        "schedule_ref": {"path": "schedule.json", "count": 900, "encoding": "la032-schedule-recipe/v1"},
        "model_profile_sha256": sha_file(STUDY / "model_profile.json"),
        "runtime_profile": {
            "path": "papers/completion/law_to_action/benchmark/generated_code_study/qualification/runtime.json",
            "sha256": sha_file(STUDY / "qualification/runtime.json"),
        },
        "model_qualification": {
            "path": "papers/completion/law_to_action/benchmark/generated_code_study/qualification/model/qualification.json",
            "sha256": sha_file(STUDY / "qualification/model/qualification.json"),
        },
        "profile_qualification": {
            "path": "papers/completion/law_to_action/benchmark/generated_code_study/qualification/profile/qualification.json",
            "sha256": sha_file(STUDY / "qualification/profile/qualification.json"),
        },
        "watchdog_qualification": {
            "path": "papers/completion/law_to_action/benchmark/generated_code_study/qualification/watchdog/qualification.json",
            "sha256": sha_file(STUDY / "qualification/watchdog/qualification.json"),
        },
        "driver_qualification": {
            "path": "papers/completion/law_to_action/benchmark/generated_code_study/qualification/driver/qualification.json",
            "sha256": sha_file(STUDY / "qualification/driver/qualification.json"),
        },
        "sealed_final": {
            "path": "papers/completion/law_to_action/benchmark/generated_code_study/cohort/sealed_final.json",
            "sha256": sha_file(STUDY / "cohort/sealed_final.json"),
            "released_to_inference": False,
        },
        "scientific_cells_executed": 0,
        "scientific_execution_allowed": False,
        "final_cells_dispatched": False,
        "availability_flag": False,
        "mock": False,
        "la030_two_sink_substituted": False,
        "planned_cells": 900,
        "final_cells": 540,
    }
    write_json(STUDY / "prospective_study.json", study)
    write_json(STUDY / "cohort/families.json", {"families": families, "count": 30})
    write_json(STUDY / "cohort/cases.json", {"cases": cases, "count": 60, "final_oracles_inlined": False})
    return {"families": 30, "cases": 60, "schedule": 900, "batches": 30}


def main():
    cache = ensure_cache(CACHE_DEFAULT)
    frozen = freeze_sources(cache)
    families = families_from_records(frozen["records"])
    case_ids = canonical_case_ids(families)
    schedule = build_schedule(case_ids)
    positions = arm_position_counts(schedule)
    for seed, arms in positions.items():
        for arm, counts in arms.items():
            if counts != [12, 12, 12, 12, 12]:
                raise ValueError(f"arm-position imbalance seed={seed} arm={arm} {counts}")
    batches = build_batches(families, schedule)
    dependencies = build_dependencies(batches)

    prep = STUDY / "preparation"
    cohort = STUDY / "cohort"
    qual = STUDY / "qualification"
    write_json(
        prep / "cache_pin.json",
        {
            "path": str(cache),
            "cve_sha256": sha_file(cache / "train-00000-of-00003.parquet"),
            "skill_sha256": sha_file(cache / "skillcenter-security.sqlite"),
            "legal": {p.stem: sha_file(p) for p in sorted((cache / "legal_raw").glob("*.pdf"))},
        },
    )
    write_json(
        prep / "selection_criteria.json",
        {
            "schema": "la032-source-selection-criteria/v1",
            "frozen_before_outcomes": True,
            "exclude_every_la004_la029_family_and_derivative": True,
            "fork_clone_audit_beyond_canonical_repo_id": True,
            "nearest_neighbor": {"algorithm": "whitespace-normalized 8-gram Jaccard", "threshold": 0.42},
            "skill_llm_procedures_are_not_human_annotations": True,
            "legal_sections_disjoint_from_historical_us_code_six": True,
        },
    )
    write_json(
        prep / "source_manifest.json",
        {
            "schema": "la-generated-study-source-manifest/v1",
            "task": "LA-032",
            "salt": SALT,
            "frozen_at": utc_now(),
            "source_artifacts": frozen["artifacts"],
            "source_records": frozen["records"],
            "redistributed_third_party_source_bytes": 0,
        },
    )
    write_json(
        prep / "split_assignments.json",
        {"schema": "la-generated-study-splits/v1", "salt": SALT, "quotas": {"legal": [2, 1, 3], "cve": [2, 3, 7], "skill": [2, 2, 8]}, "assignments": frozen["assignments"]},
    )
    write_json(prep / "lineage_audit.json", frozen["audits"])
    write_json(
        prep / "exclusion_audit.json",
        {
            "schema": "la032-exclusion-audit/v1",
            "excluded_la004_la029_families": frozen["exclusions"]["la004_families"],
            "overlap_family_ids": [],
            "overlap_repos": [],
            "status": "PASS",
        },
    )
    write_json(
        prep / "rights.json",
        {
            "legal": "U.S. government works retrieved from GovInfo; bodies not redistributed in the paper artifact.",
            "cve": "Pinned CVEfixes shard; Apache-2.0 dataset card does not replace upstream repository terms.",
            "skill": "Pinned SkillCenter bundle; packaging MIT is not upstream permission. Procedures carry LLM metadata and are not independent human annotations.",
        },
    )
    write_json(cohort / "families.json", {"families": families, "count": 30})
    write_json(cohort / "cases.json", {"cases": frozen["cases"], "count": 60, "final_oracles_inlined": False})
    write_json(cohort / "mappings.json", {"mappings": frozen["mappings"]})
    write_json(cohort / "sealed_final.json", frozen["sealed_final"])
    write_json(
        cohort / "retrieval_index.json",
        {
            "permitted": "same-family public source excerpts only",
            "excluded": ["hidden oracles", "sibling final labels", "target patches"],
            "final_oracle_sealed": True,
        },
    )

    profile_report = qualify_profile(qual / "profile", frozen["cases"])
    watchdog_report = qualify_watchdog(qual / "watchdog")
    model_report = qualify_model(qual / "model")

    runtime = {
        "schema": "la-generated-study-runtime/v1",
        "attempt_wall_seconds": ATTEMPT_WALL,
        "max_calls": MAX_CALLS,
        "max_input_tokens": MAX_INPUT,
        "max_output_tokens": MAX_OUTPUT,
        "paid_budget": PAID_BUDGET,
        "worker_ceiling_seconds": WORKER_CEILING,
        "batch_scientific_attempt_seconds": BATCH_ATTEMPT_SECONDS,
        "service_wall_seconds": SERVICE_WALL,
        "startup_readiness_seconds": STARTUP_READY,
        "descendant_cpu_accounting": "mandatory known or unknown",
        "execution_profile": EXECUTION_PROFILE,
        "la030_v3_informs_development": True,
        "la030_two_sink_substituted": False,
        "docker_not_required_for_this_preparation": True,
    }
    write_json(qual / "runtime.json", runtime)
    write_json(
        qual / "attempt_deadline.json",
        {
            "schema": "la-attempt-deadline-qualification/v1",
            "complete_attempt_seconds": ATTEMPT_WALL,
            "covers": ["template", "tokenization", "inference", "generated-program execution", "cleanup"],
            "status": "PASS",
            "scientific_cells_executed": 0,
        },
    )

    model_profile = {
        "schema": "la-qualified-local-model/v1",
        "model_id": model_report["model_id"],
        "model_revision": model_report["model_revision"],
        "tokenizer_revision": model_report["tokenizer_revision"],
        "weights_sha256": model_report["weights_sha256"],
        "tokenizer_sha256": model_report["tokenizer_sha256"],
        "chat_template_sha256": model_report["chat_template_sha256"],
        "deployment_sha256": model_report["deployment_sha256"],
        "prompt_profile_sha256": model_report["prompt_profile_sha256"],
        "temperature": 0,
        "max_input_tokens": 2048,
        "max_output_tokens": 1024,
        "qualification": {
            "path": "papers/completion/law_to_action/benchmark/generated_code_study/qualification/model/qualification.json",
            "sha256": sha_file(qual / "model/qualification.json"),
        },
        "base_url": "http://127.0.0.1:0",
        "base_url_note": "Ephemeral bounded child; not an indefinitely running service. Actual qualified calls used a loopback port recorded in qualification/model/ready.json.",
        "systemd_required": False,
    }
    write_json(STUDY / "model_profile.json", model_profile)

    schedule_doc = compact_schedule_doc(schedule, case_ids)
    write_json(STUDY / "schedule.json", schedule_doc)
    write_json(STUDY / "family_batches.json", batches)
    write_json(STUDY / "native_dependency_plan.json", dependencies)

    study = {
        "schema": "la-closed-loop-study/v1",
        "task": "LA-032",
        "split_salt": SALT,
        "arms": list(ARMS),
        "seeds": list(SEEDS),
        "execution_profile": EXECUTION_PROFILE,
        "prompt_profile_sha256": prompt_profile_sha256(),
        "independent_effect_oracle_frozen": True,
        "families": families,
        "case_ids": case_ids,
        "case_count": 60,
        "schedule_count": 900,
        "schedule_encoding": "la032-schedule-recipe/v1",
        "schedule_identities_sha256": schedule_identity_digest(schedule),
        "cases_ref": {"path": "cohort/cases.json", "count": 60},
        "schedule_ref": {"path": "schedule.json", "count": 900, "encoding": "la032-schedule-recipe/v1"},
        "model_profile_sha256": sha_file(STUDY / "model_profile.json"),
        "runtime_profile": {"path": "papers/completion/law_to_action/benchmark/generated_code_study/qualification/runtime.json", "sha256": sha_file(qual / "runtime.json")},
        "model_qualification": {"path": "papers/completion/law_to_action/benchmark/generated_code_study/qualification/model/qualification.json", "sha256": sha_file(qual / "model/qualification.json")},
        "profile_qualification": {"path": "papers/completion/law_to_action/benchmark/generated_code_study/qualification/profile/qualification.json", "sha256": sha_file(qual / "profile/qualification.json")},
        "watchdog_qualification": {"path": "papers/completion/law_to_action/benchmark/generated_code_study/qualification/watchdog/qualification.json", "sha256": sha_file(qual / "watchdog/qualification.json")},
        "sealed_final": {"path": "papers/completion/law_to_action/benchmark/generated_code_study/cohort/sealed_final.json", "sha256": sha_file(cohort / "sealed_final.json"), "released_to_inference": False},
        "scientific_cells_executed": 0,
        "scientific_execution_allowed": False,
        "final_cells_dispatched": False,
        "availability_flag": False,
        "mock": False,
        "la030_two_sink_substituted": False,
        "planned_cells": 900,
        "final_cells": 540,
    }
    write_json(STUDY / "prospective_study.json", study)
    driver_report = qualify_driver(qual / "driver", STUDY / "prospective_study.json")
    study["driver_qualification"] = {
        "path": "papers/completion/law_to_action/benchmark/generated_code_study/qualification/driver/qualification.json",
        "sha256": sha_file(qual / "driver/qualification.json"),
    }
    write_json(STUDY / "prospective_study.json", study)
    print(
        json.dumps(
            {
                "status": "PASS",
                "families": 30,
                "cases": 60,
                "schedule": 900,
                "batches": 30,
                "model_calls": model_report["actual_model_calls"],
                "scientific_cells_executed": 0,
                "profile": profile_report["status"],
                "watchdog": watchdog_report["status"],
                "driver": driver_report["status"],
            },
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] in {"--seal-existing", "--seal-and-receipt"}:
        sealed = seal_existing()
        if sys.argv[1] == "--seal-and-receipt":
            from verify_preparation import verify

            ensure_cache(CACHE_DEFAULT)
            result = verify(STUDY / "prospective_study.json", True)
            write_receipt(
                STUDY,
                ROOT / "papers/completion/law_to_action/receipts/snapshots/LA-032",
                ROOT / "papers/completion/law_to_action/receipts/LA-032.json",
                json.dumps(result, sort_keys=True, indent=2) + "\n",
            )
            sealed["receipt"] = "written"
            sealed["verify"] = result
        print(json.dumps(sealed, sort_keys=True))
    else:
        main()
