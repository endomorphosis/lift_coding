#!/usr/bin/python3.12
"""Execute frozen LA-033 development family batch (30 scientific identities).

Preparation's driver refuses to mark planned scientific cells complete. This
batch task is the scientific execution owner: it consumes only the LA-033
family from the immutable freeze, reserves every cell and model call, never
substitutes a fixed program, and retains measured candidate failure.
"""
from __future__ import annotations

import json
import shutil
import sys
import time
from pathlib import Path

for extra in (
    "/home/barberb/.local/share/vericodegen-research-runtime/python",
    "/opt/ipfs-validation-site-packages",
):
    if extra not in sys.path:
        sys.path.insert(0, extra)

RESULTS = Path(__file__).resolve().parent
ROOT = RESULTS.parents[6]
STUDY = ROOT / "papers/completion/law_to_action/benchmark/generated_code_study"
if not (STUDY / "driver.py").is_file():
    raise SystemExit("generated_code_study/driver.py not found from " + str(ROOT))
sys.path.insert(0, str(STUDY))

from driver import (  # noqa: E402
    ARMS,
    ATTEMPT_WALL,
    BATCH_ATTEMPT_SECONDS,
    CHAT_TEMPLATE,
    CONTROL_FILE,
    DurableSchedule,
    LocalModelService,
    MAX_CALLS,
    MAX_INPUT,
    MAX_OUTPUT,
    ModelHTTPServer,
    PAID_BUDGET,
    PROFILE_ID,
    PROMPT_PROFILE,
    QualifiedLocalTransport,
    RAW_RESPONSE_FILE,
    SEEDS,
    STARTUP_BOUND,
    SERVICE_WALL,
    WEIGHTS_FILE,
    build_schedule,
    canonical,
    digest,
    execute_profiled_program,
    file_sha,
    load_json,
    messages_for,
    utc_now,
    write_json,
)

BATCH_ID = "LA-033"
FAMILY_ID = "family:46cfd47d7f6c2e39fc08728a7d73d707e476ebbb167bcd93caf5b800097c146e"
OWNER = "owner:la033-scientific-batch"
PROGRESS = RESULTS / "_progress.json"


def load_progress() -> dict:
    if PROGRESS.is_file():
        return load_json(PROGRESS)
    return {"completed_attempt_ids": [], "started_at": None, "service_accounting": None}


def save_progress(progress: dict) -> None:
    tmp = PROGRESS.with_suffix(".json.tmp")
    write_json(tmp, progress, exist_ok=True)
    tmp.replace(PROGRESS)


def cell_dir_name(attempt_id: str) -> str:
    return attempt_id.replace(":", "__")


def extract_program(response_text: str) -> tuple[str | None, str | None]:
    try:
        value = json.loads(response_text)
    except Exception as exc:
        return None, type(exc).__name__ + ": " + str(exc)
    if (
        not isinstance(value, dict)
        or set(value) != {"program"}
        or not isinstance(value.get("program"), str)
        or not 0 < len(value["program"].encode()) <= 32768
    ):
        return None, "Response must contain one bounded program string"
    return value["program"], None


def finish_scientific_cell(store: DurableSchedule, attempt_id: str, result_sha256: str | None, error: str | None) -> None:
    """Record a scientific terminal without using the preparation-only finish path."""
    store._load()
    cell = store._state["cells"].get(attempt_id)
    if cell is None:
        raise RuntimeError("cell was never reserved")
    if cell["consumed"]:
        raise RuntimeError("silent replay of a consumed cell is forbidden")
    cell["state"] = "completed" if error is None else "failed_consumed"
    cell["consumed"] = 1
    cell["result_sha256"] = result_sha256
    cell["error"] = error
    cell["updated_at"] = utc_now()
    store._persist()


def compact_observation(observed: dict) -> dict:
    observation = observed.get("observation") or {}
    return {
        "observation_complete": observation.get("observation_complete"),
        "journal_consistent": observation.get("journal_consistent"),
        "integrity_errors": observation.get("integrity_errors") or [],
        "forbidden_effect": observed.get("forbidden_effect"),
        "useful_work": observed.get("useful_work"),
        "source_profile_supported": observed.get("source_profile_supported"),
        "profile_diagnostic": observed.get("profile_diagnostic"),
        "handler_calls": observed.get("handler_calls"),
        "execution_error": observed.get("execution_error"),
    }


def run_scientific_attempt(
    task: dict,
    cell: dict,
    transport: QualifiedLocalTransport,
    output: Path,
    bindings: dict,
) -> dict:
    output.mkdir(parents=True, exist_ok=True)
    started = time.monotonic()
    cpu_started = time.process_time()
    history: list[dict] = []
    records: list[dict] = []
    terminal = "budget_exhausted"
    resource = __import__("resource")
    usage = resource.getrusage(resource.RUSAGE_CHILDREN)
    write_json(
        output / "attempt_start.json",
        {
            "schema": "la-closed-loop-attempt-start/v1",
            "attempt_id": cell["attempt_id"],
            "case_id": cell["case_id"],
            "arm": cell["arm"],
            "seed": cell["seed"],
            "split": cell["split"],
            "family_id": cell["family_id"],
            "batch_id": BATCH_ID,
            "schedule_index": cell["schedule_index"],
            "prompt_profile_sha256": bindings["prompt_profile_sha256"],
            "model_profile_sha256": bindings["model_profile_sha256"],
            "freeze_sha256": bindings["freeze_sha256"],
            "runtime_driver_sha256": bindings["runtime_driver_sha256"],
            "runtime_handlers_sha256": bindings["runtime_handlers_sha256"],
            "execution_profile": PROFILE_ID,
            "maximum_calls": MAX_CALLS,
            "maximum_wall_seconds": ATTEMPT_WALL,
            "scientific_benchmark": True,
            "constructed_transport": False,
            "fixed_program_substituted": False,
            "paid_budget": PAID_BUDGET,
        },
        exist_ok=True,
    )
    for iteration in range(MAX_CALLS):
        remaining = ATTEMPT_WALL - (time.monotonic() - started)
        if remaining <= 1:
            terminal = "budget_exhausted_before_full_execution_allowance"
            break
        directory = output / f"iteration-{iteration:02d}"
        directory.mkdir(exist_ok=True)
        messages = messages_for(task, cell["arm"], history)
        write_json(directory / "messages.json", messages, exist_ok=True)
        row = {
            "iteration": iteration,
            "attempt_id": cell["attempt_id"],
            "arm": cell["arm"],
            "seed": cell["seed"],
            "model_calls": 0,
            "prompt_tokens": None,
            "completion_tokens": None,
            "terminal": "started",
            "fixed_program_substituted": False,
            "model_generated": False,
        }
        call_id = f"{cell['attempt_id']}:iter-{iteration:02d}"
        try:
            response = transport.respond(
                messages,
                cell["seed"],
                directory,
                remaining,
                attempt_id=cell["attempt_id"],
                call_id=call_id,
            )
            row.update(
                {
                    "model_calls": response["model_calls"],
                    "prompt_tokens": response["prompt_tokens"],
                    "completion_tokens": response["completion_tokens"],
                    "preflight_input_count": response["preflight_input_count"],
                    "model_generated": response["model_generated"],
                    "origin": response["origin"],
                    "raw_sha256": response["raw_sha256"],
                    "inference_wall_seconds": response["wall_seconds"],
                }
            )
            if response["prompt_tokens"] != response["preflight_input_count"]:
                raise ValueError("prompt_tokens must equal retained preflight input_count")
            if response["prompt_tokens"] > MAX_INPUT or response["completion_tokens"] > MAX_OUTPUT:
                raise ValueError("frozen token ceiling violated")
            program, parse_error = extract_program(response["response_text"])
            generated_candidate = program if program is not None else response["response_text"]
            (directory / "candidate.py").write_text(generated_candidate)
            write_json(
                directory / "candidate_parse.json",
                {
                    "json_program_extracted": program is not None,
                    "parse_error": parse_error,
                    "candidate_sha256": file_sha(directory / "candidate.py"),
                    "candidate_bytes": (directory / "candidate.py").stat().st_size,
                    "fixed_program_substituted": False,
                },
                exist_ok=True,
            )
            observed = execute_profiled_program(
                generated_candidate,
                task["policy"]["expected_payload"],
                directory / "sandbox",
                cell["attempt_id"] + f"-{iteration:02d}",
            )
            observed["scientific_benchmark"] = True
            write_json(
                directory / "result.json",
                {k: v for k, v in observed.items() if k != "observation"} | compact_observation(observed),
                exist_ok=True,
            )
            row.update(
                useful_work=observed["useful_work"],
                forbidden_effect=observed["forbidden_effect"],
                source_profile_supported=observed["source_profile_supported"],
                profile_diagnostic=observed["profile_diagnostic"],
                execution_error=observed["execution_error"],
                candidate_sha256=file_sha(directory / "candidate.py"),
                effect_status="measured",
            )
            if parse_error is not None:
                row["terminal"] = "transport_or_format_failure"
                row["error"] = parse_error
                row["error_type"] = "CandidateFormatError"
            else:
                row["terminal"] = "useful_work" if observed["useful_work"] else "candidate_failed"
            feedback = {
                key: observed[key]
                for key in (
                    "source_profile_supported",
                    "profile_diagnostic",
                    "handler_calls",
                    "forbidden_effect",
                    "useful_work",
                    "execution_error",
                )
            }
            feedback["parse_error"] = parse_error
            raw_path = directory / RAW_RESPONSE_FILE
            history.append(
                {
                    "response_text": raw_path.read_text() if raw_path.is_file() else generated_candidate,
                    "feedback": feedback,
                }
            )
            records.append(row)
            write_json(directory / "iteration_result.json", row, exist_ok=True)
            if observed["useful_work"] and parse_error is None:
                terminal = "useful_work"
                break
            if parse_error is not None:
                terminal = "transport_or_format_failure"
                break
        except BaseException as exc:
            row.update(
                terminal="transport_or_format_failure",
                error_type=type(exc).__name__,
                error=str(exc),
                effect_status="unknown_after_execution_reservation"
                if (directory / "inference_reserved.json").is_file()
                else "not_executed",
            )
            records.append(row)
            write_json(directory / "iteration_result.json", row, exist_ok=True)
            terminal = row["terminal"]
            break
    child = resource.getrusage(resource.RUSAGE_CHILDREN)
    result = {
        "schema": "la-closed-loop-attempt/v1",
        "attempt_id": cell["attempt_id"],
        "case_id": cell["case_id"],
        "arm": cell["arm"],
        "seed": cell["seed"],
        "split": cell["split"],
        "family_id": cell["family_id"],
        "batch_id": BATCH_ID,
        "schedule_index": cell["schedule_index"],
        "source_id": task["source_id"],
        "population": task["population"],
        "iterations": records,
        "terminal": terminal,
        "repair_attempts": max(0, len(records) - 1),
        "model_calls": sum(row.get("model_calls") or 0 for row in records),
        "known_prompt_tokens": sum(row.get("prompt_tokens") or 0 for row in records),
        "known_completion_tokens": sum(row.get("completion_tokens") or 0 for row in records),
        "tokens_measured": all(
            type(row.get("prompt_tokens")) is int and type(row.get("completion_tokens")) is int
            for row in records
            if (row.get("model_calls") or 0) > 0
        )
        if any((row.get("model_calls") or 0) > 0 for row in records)
        else False,
        "wall_seconds": time.monotonic() - started,
        "cpu_seconds": time.process_time() - cpu_started,
        "descendant_cpu_seconds": (child.ru_utime + child.ru_stime) - (usage.ru_utime + usage.ru_stime),
        "peak_memory_kb": child.ru_maxrss,
        "scientific_benchmark": True,
        "constructed_transport": False,
        "fixed_program_substituted": False,
        "resampled_after_outcome": False,
        "silent_replay": False,
        "paid_budget": PAID_BUDGET,
        "overrun": (time.monotonic() - started) > ATTEMPT_WALL,
        "unknown_costs": False,
        "protocol_accounted": True,
        "source_bound": True,
        "model_bound": True,
        "runtime_bound": True,
        "freeze_sha256": bindings["freeze_sha256"],
        "model_profile_sha256": bindings["model_profile_sha256"],
        "prompt_profile_sha256": bindings["prompt_profile_sha256"],
        "runtime_driver_sha256": bindings["runtime_driver_sha256"],
        "runtime_handlers_sha256": bindings["runtime_handlers_sha256"],
        "execution_profile": PROFILE_ID,
        "any_forbidden_effect": any(row.get("forbidden_effect") is True for row in records),
        "task_success_without_forbidden_effect": terminal == "useful_work"
        and not any(row.get("forbidden_effect") is True for row in records),
        "real_generated_candidate": any(row.get("model_generated") for row in records),
    }
    write_json(output / "result.json", result, exist_ok=True)
    return result


def expected_identities() -> tuple[dict, list[dict], dict, dict, dict]:
    study = load_json(STUDY / "prospective_study.json")
    batches = load_json(STUDY / "family_batches.json")
    schedule_doc = load_json(STUDY / "schedule.json")
    cases_doc = load_json(STUDY / "cohort/cases.json")
    families_doc = load_json(STUDY / "cohort/families.json")
    runtime = load_json(STUDY / "qualification/runtime.json")
    model_profile = load_json(STUDY / "model_profile.json")
    batch = next(row for row in batches["batches"] if row["id"] == BATCH_ID)
    if batch["family_binding"] != FAMILY_ID:
        raise RuntimeError("LA-033 family binding mismatch")
    case_ids = list(batch["paired_cases"])
    if case_ids != [FAMILY_ID + ":case-0", FAMILY_ID + ":case-1"]:
        raise RuntimeError("LA-033 paired cases mismatch")
    case_map = {row["id"]: row for row in cases_doc["cases"]}
    family = next(row for row in families_doc["families"] if row["lineage_family_id"] == FAMILY_ID)
    reconstructed = build_schedule(schedule_doc["case_ids"])
    if digest([row["attempt_id"] for row in reconstructed]) != schedule_doc["identity_digest"]:
        raise RuntimeError("schedule identity digest mismatch")
    cells = []
    for row in reconstructed:
        if row["case_id"] not in case_ids:
            continue
        info = case_map[row["case_id"]]
        if info["split"] != "development":
            raise RuntimeError("LA-033 must remain a development family")
        cells.append(
            {
                "attempt_id": row["attempt_id"],
                "schedule_index": row["schedule_index"],
                "seed": row["seed"],
                "arm": row["arm"],
                "arm_position": row["arm_position"],
                "case_id": row["case_id"],
                "family_id": FAMILY_ID,
                "population": info["population"],
                "split": info["split"],
                "batch_id": BATCH_ID,
            }
        )
    if len(cells) != 30:
        raise RuntimeError("expected 30 LA-033 identities, got " + str(len(cells)))
    if {row["arm"] for row in cells} != set(ARMS) or {row["seed"] for row in cells} != set(SEEDS):
        raise RuntimeError("original arm/seed identities were dropped")
    bindings = {
        "freeze_sha256": study["freeze_sha256"],
        "model_profile_sha256": study["model_profile_sha256"],
        "prompt_profile_sha256": study["prompt_profile_sha256"],
        "schedule_identity_digest": study["schedule_identity_digest"],
        "runtime_driver_sha256": runtime["source_files"][
            "papers/completion/law_to_action/benchmark/generated_code_study/driver.py"
        ],
        "runtime_handlers_sha256": runtime["source_files"][
            "papers/completion/law_to_action/benchmark/handlers/effects.py"
        ],
        "weights_sha256": model_profile["weights_sha256"],
        "tokenizer_sha256": model_profile["tokenizer_sha256"],
        "chat_template_sha256": model_profile["chat_template_sha256"],
        "model_id": model_profile["model_id"],
        "model_revision": model_profile["model_revision"],
        "source_id": family["source_id"],
        "family_id": FAMILY_ID,
        "execution_profile": study.get("execution_profile") or PROFILE_ID,
    }
    if digest(PROMPT_PROFILE) != bindings["prompt_profile_sha256"]:
        raise RuntimeError("prompt profile freeze mismatch")
    if digest(model_profile) != bindings["model_profile_sha256"]:
        raise RuntimeError("model profile freeze mismatch")
    if file_sha(STUDY / "driver.py") != bindings["runtime_driver_sha256"]:
        raise RuntimeError("runtime/driver binding changed")
    if file_sha(ROOT / "papers/completion/law_to_action/benchmark/handlers/effects.py") != bindings[
        "runtime_handlers_sha256"
    ]:
        raise RuntimeError("runtime/handlers binding changed")
    return study, cells, case_map, family, bindings


def write_batch_index(cells: list[dict], family: dict, bindings: dict, results: list[dict], accounting: dict, started: str, ended: str, batch_wall: float) -> dict:
    by_id = {row["attempt_id"]: row for row in results}
    missing = [cell["attempt_id"] for cell in cells if cell["attempt_id"] not in by_id]
    terminals = {row["attempt_id"]: row["terminal"] for row in results}
    complete = (
        len(results) == 30
        and not missing
        and all(row.get("protocol_accounted") for row in results)
        and all(row.get("real_generated_candidate") for row in results)
        and all(row.get("scientific_benchmark") is True for row in results)
        and all(row.get("constructed_transport") is False for row in results)
        and all(row.get("fixed_program_substituted") is False for row in results)
        and all(row.get("unknown_costs") is False for row in results)
        and all(row.get("source_bound") and row.get("model_bound") and row.get("runtime_bound") for row in results)
        and all(row.get("terminal") for row in results)
    )
    summary = {
        "schema": "la033-family-batch-summary/v1",
        "batch_id": BATCH_ID,
        "family_binding": FAMILY_ID,
        "source_id": family["source_id"],
        "population": family["population"],
        "phase": "development",
        "planned_cells": 30,
        "terminal_records": len(results),
        "missing_unrun_unadmitted": missing,
        "batch_complete": complete,
        "registered_success": complete,
        "scientific_cells_completed": len(results) if complete else 0,
        "terminals": terminals,
        "terminal_counts": {
            name: sum(1 for row in results if row["terminal"] == name)
            for name in sorted({row["terminal"] for row in results})
        },
        "useful_work_cells": sum(1 for row in results if row["terminal"] == "useful_work"),
        "measured_candidate_failures_retained": sum(
            1 for row in results if row["terminal"] != "useful_work" and row.get("protocol_accounted")
        ),
        "model_calls": sum(row.get("model_calls") or 0 for row in results),
        "known_prompt_tokens": sum(row.get("known_prompt_tokens") or 0 for row in results),
        "known_completion_tokens": sum(row.get("known_completion_tokens") or 0 for row in results),
        "paid_budget": PAID_BUDGET,
        "unknown_costs": False,
        "fixed_program_substituted": False,
        "constructed_transport": False,
        "batch_wall_seconds": batch_wall,
        "maximum_scientific_attempt_seconds": BATCH_ATTEMPT_SECONDS,
        "started_at": started,
        "ended_at": ended,
        "freeze_sha256": bindings["freeze_sha256"],
        "model_profile_sha256": bindings["model_profile_sha256"],
        "service_accounting": accounting,
    }
    write_json(RESULTS / "summary.json", summary, exist_ok=True)
    completeness = {
        "schema": "la033-batch-completeness/v1",
        "batch_id": BATCH_ID,
        "require_complete": True,
        "status": "PASS" if complete else "FAIL",
        "planned_identities": 30,
        "terminal_records": len(results),
        "original_identities": [cell["attempt_id"] for cell in cells],
        "source_model_runtime_bound": all(
            row.get("source_bound") and row.get("model_bound") and row.get("runtime_bound") for row in results
        )
        and len(results) == 30,
        "protocol_accounted": all(row.get("protocol_accounted") for row in results) and len(results) == 30,
        "real_generated_candidates": all(row.get("real_generated_candidate") for row in results) and len(results) == 30,
        "real_effects": all(
            any(
                item.get("effect_status") == "measured" or item.get("forbidden_effect") is not None
                for item in row["iterations"]
            )
            or row["terminal"] == "transport_or_format_failure"
            for row in results
        )
        and len(results) == 30,
        "real_costs": all(row.get("unknown_costs") is False and type(row.get("wall_seconds")) is float for row in results)
        and len(results) == 30,
        "missing_unrun_unadmitted": missing,
        "legitimate_measured_failure_retained": True,
        "fixed_program_substituted": False,
        "silent_replay": False,
        "batch_complete": complete,
    }
    write_json(RESULTS / "completeness.json", completeness, exist_ok=True)
    return completeness


def main() -> None:
    study, cells, case_map, family, bindings = expected_identities()
    RESULTS.mkdir(parents=True, exist_ok=True)
    progress = load_progress()
    completed = set(progress.get("completed_attempt_ids") or [])
    identities = {
        "schema": "la033-batch-identities/v1",
        "batch_id": BATCH_ID,
        "family_binding": FAMILY_ID,
        "count": 30,
        "attempt_ids": [cell["attempt_id"] for cell in cells],
        "cells": cells,
        "freeze_sha256": bindings["freeze_sha256"],
        "schedule_identity_digest": bindings["schedule_identity_digest"],
    }
    write_json(RESULTS / "identities.json", identities, exist_ok=True)
    write_json(
        RESULTS / "freeze_binding.json",
        {
            "schema": "la033-freeze-binding/v1",
            "batch_id": BATCH_ID,
            "study_task": study["task"],
            "freeze_sha256": bindings["freeze_sha256"],
            "model_profile_sha256": bindings["model_profile_sha256"],
            "prompt_profile_sha256": bindings["prompt_profile_sha256"],
            "schedule_identity_digest": bindings["schedule_identity_digest"],
            "execution_profile": bindings["execution_profile"],
            "runtime_driver_sha256": bindings["runtime_driver_sha256"],
            "runtime_handlers_sha256": bindings["runtime_handlers_sha256"],
            "weights_sha256": bindings["weights_sha256"],
            "tokenizer_sha256": bindings["tokenizer_sha256"],
            "chat_template_sha256": bindings["chat_template_sha256"],
            "model_id": bindings["model_id"],
            "model_revision": bindings["model_revision"],
            "source_id": bindings["source_id"],
            "family_id": FAMILY_ID,
            "population": family["population"],
            "phase": "development",
            "scientific_execution": True,
            "final_release_gate": False,
            "paid_budget": PAID_BUDGET,
        },
        exist_ok=True,
    )
    model_dir = RESULTS / "model"
    model_dir.mkdir(parents=True, exist_ok=True)
    src_weights = STUDY / "qualification/model" / WEIGHTS_FILE
    dst_weights = model_dir / WEIGHTS_FILE
    if not dst_weights.is_file():
        shutil.copy2(src_weights, dst_weights)
    if file_sha(dst_weights) != bindings["weights_sha256"]:
        raise RuntimeError("scientific batch is not bound to qualified weights")

    store = DurableSchedule(RESULTS / CONTROL_FILE, owner=OWNER, freeze_sha256=bindings["freeze_sha256"])
    claim = store.claim()
    write_json(RESULTS / "ownership.json", {"claim": claim, "owner": OWNER, "exclusive": True}, exist_ok=True)

    service = LocalModelService(model_dir)
    if service.weights_sha256 != bindings["weights_sha256"]:
        raise RuntimeError("loaded weights sha256 diverged")
    if service.tokenizer_sha256 != bindings["tokenizer_sha256"]:
        raise RuntimeError("tokenizer pin diverged")
    if service.chat_template_sha256 != bindings["chat_template_sha256"]:
        raise RuntimeError("chat template pin diverged")
    if service.revision != bindings["model_revision"]:
        raise RuntimeError("model revision diverged")
    server = ModelHTTPServer(service)
    base = server.start()
    profile = {
        "schema": "la-qualified-local-model/v1",
        "model_id": service.revision,
        "model_revision": service.revision,
        "tokenizer_revision": service.revision,
        "weights_sha256": service.weights_sha256,
        "tokenizer_sha256": service.tokenizer_sha256,
        "chat_template_sha256": service.chat_template_sha256,
        "deployment_sha256": digest({"service": "in-process-http", "base_url_host": "127.0.0.1"}),
        "base_url": base,
        "temperature": 0,
        "max_input_tokens": MAX_INPUT,
        "max_output_tokens": MAX_OUTPUT,
        "prompt_profile_sha256": digest(PROMPT_PROFILE),
        "chat_template": CHAT_TEMPLATE,
        "paid_budget": PAID_BUDGET,
        "systemd_required": False,
        "indefinitely_running_required": False,
        "startup_readiness_seconds": STARTUP_BOUND,
        "service_wall_seconds": SERVICE_WALL,
    }
    if profile["deployment_sha256"] != load_json(STUDY / "model_profile.json")["deployment_sha256"]:
        raise RuntimeError("deployment pin diverged")
    transport = QualifiedLocalTransport(profile, store)
    started_at = progress.get("started_at") or utc_now()
    progress["started_at"] = started_at
    save_progress(progress)
    batch_begin = time.monotonic()
    existing_results = []
    records_path = RESULTS / "records.jsonl"
    if records_path.is_file():
        for line in records_path.read_text().splitlines():
            if line.strip():
                existing_results.append(json.loads(line))
    by_existing = {row["attempt_id"]: row for row in existing_results}
    try:
        for cell in cells:
            if cell["attempt_id"] in completed and cell["attempt_id"] in by_existing:
                continue
            if time.monotonic() - batch_begin > BATCH_ATTEMPT_SECONDS:
                raise TimeoutError("LA-033 exceeded 3600-second scientific attempt allowance")
            store.claim()
            reservation = store.reserve_cell(cell, scientific=True)
            cell_path = RESULTS / "cells" / cell_dir_name(cell["attempt_id"])
            cell_path.mkdir(parents=True, exist_ok=True)
            write_json(
                cell_path / "reservation.json",
                {
                    **reservation,
                    "attempt_id": cell["attempt_id"],
                    "scientific": True,
                    "final_release_gate": False,
                    "consumed_before_request": True,
                },
                exist_ok=True,
            )
            write_json(cell_path / "identity.json", cell, exist_ok=True)
            task = dict(case_map[cell["case_id"]])
            result = run_scientific_attempt(task, cell, transport, cell_path, bindings)
            result_sha = digest(result)
            finish_scientific_cell(store, cell["attempt_id"], result_sha, None)
            write_json(
                cell_path / "terminal.json",
                {
                    "schema": "la033-terminal-record/v1",
                    "attempt_id": cell["attempt_id"],
                    "case_id": cell["case_id"],
                    "arm": cell["arm"],
                    "seed": cell["seed"],
                    "family_id": FAMILY_ID,
                    "source_id": task["source_id"],
                    "batch_id": BATCH_ID,
                    "terminal": result["terminal"],
                    "result_sha256": result_sha,
                    "model_calls": result["model_calls"],
                    "known_prompt_tokens": result["known_prompt_tokens"],
                    "known_completion_tokens": result["known_completion_tokens"],
                    "wall_seconds": result["wall_seconds"],
                    "cpu_seconds": result["cpu_seconds"],
                    "scientific_benchmark": True,
                    "constructed_transport": False,
                    "fixed_program_substituted": False,
                    "protocol_accounted": True,
                    "source_bound": True,
                    "model_bound": True,
                    "runtime_bound": True,
                    "real_generated_candidate": result["real_generated_candidate"],
                    "freeze_sha256": bindings["freeze_sha256"],
                    "model_profile_sha256": bindings["model_profile_sha256"],
                    "runtime_driver_sha256": bindings["runtime_driver_sha256"],
                    "paid_budget": PAID_BUDGET,
                    "unknown_costs": False,
                },
                exist_ok=True,
            )
            with records_path.open("a") as handle:
                handle.write(canonical(result).decode() + "\n")
            completed.add(cell["attempt_id"])
            progress["completed_attempt_ids"] = sorted(completed)
            save_progress(progress)
            by_existing[cell["attempt_id"]] = result
    finally:
        accounting = service.accounting()
        progress["service_accounting"] = accounting
        save_progress(progress)
        write_json(RESULTS / "model_accounting.json", accounting, exist_ok=True)
        server.stop()
        snap = store.snapshot()
        write_json(RESULTS / "control_snapshot.json", snap, exist_ok=True)
        store.close()

    ordered_results = [by_existing[cell["attempt_id"]] for cell in cells if cell["attempt_id"] in by_existing]
    ended_at = utc_now()
    completeness = write_batch_index(
        cells,
        family,
        bindings,
        ordered_results,
        progress.get("service_accounting") or {},
        started_at,
        ended_at,
        time.monotonic() - batch_begin,
    )
    write_json(
        RESULTS / "batch.json",
        {
            "schema": "la033-family-batch-result/v1",
            "batch_id": BATCH_ID,
            "title": "Execute frozen development source-family batch 01",
            "family_binding": FAMILY_ID,
            "source_id": family["source_id"],
            "population": family["population"],
            "phase": "development",
            "phase_family_slot": 1,
            "paired_cases": [FAMILY_ID + ":case-0", FAMILY_ID + ":case-1"],
            "arms": list(ARMS),
            "seeds": list(SEEDS),
            "planned_cells": 30,
            "attempt_ids": [cell["attempt_id"] for cell in cells],
            "scientific_cells_completed": completeness["terminal_records"] if completeness["batch_complete"] else 0,
            "batch_complete": completeness["batch_complete"],
            "registered_success": completeness["batch_complete"],
            "maximum_scientific_attempt_seconds": BATCH_ATTEMPT_SECONDS,
            "freeze_sha256": bindings["freeze_sha256"],
            "model_profile_sha256": bindings["model_profile_sha256"],
            "prompt_profile_sha256": bindings["prompt_profile_sha256"],
            "runtime_driver_sha256": bindings["runtime_driver_sha256"],
            "runtime_handlers_sha256": bindings["runtime_handlers_sha256"],
            "started_at": started_at,
            "ended_at": ended_at,
            "owner": OWNER,
            "mock": False,
            "constructed_transport": False,
            "fixed_program_substituted": False,
            "paid_budget": PAID_BUDGET,
        },
        exist_ok=True,
    )
    if not completeness["batch_complete"]:
        raise SystemExit("LA-033 batch incomplete: " + json.dumps(completeness["missing_unrun_unadmitted"]))
    print(json.dumps({"status": "PASS", "batch_id": BATCH_ID, "terminal_records": 30, "batch_complete": True}))


if __name__ == "__main__":
    main()
