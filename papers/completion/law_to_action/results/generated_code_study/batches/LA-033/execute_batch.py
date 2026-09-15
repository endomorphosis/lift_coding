#!/usr/bin/python3.12
"""Execute the frozen LA-033 development family batch with the qualified local model.

This runner consumes only the original 30 case-arm-seed identities for the
bound source family. It never substitutes a fixed program, never silently
replays a consumed cell or model call, and retains measured candidate
failure as a terminal outcome.
"""
from __future__ import annotations

import json
import os
import resource
import shutil
import sys
import time
from pathlib import Path
from typing import Any

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[6]
STUDY = ROOT / "papers/completion/law_to_action/benchmark/generated_code_study"
sys.path.insert(0, str(STUDY))

from driver import (  # noqa: E402
    ATTEMPT_WALL,
    CONTROL_FILE,
    DurableSchedule,
    LocalModelService,
    MAX_CALLS,
    MAX_INPUT,
    MAX_OUTPUT,
    ModelHTTPServer,
    PAID_BUDGET,
    PROFILE_ID,
    QualifiedLocalTransport,
    RAW_RESPONSE_FILE,
    WEIGHTS_FILE,
    build_schedule,
    digest,
    execute_profiled_program,
    file_sha,
    load_json,
    messages_for,
    utc_now,
    write_json,
)

BATCH_ID = "LA-033"
OWNER = "owner:la033-scientific-batch"
CHECKPOINT_ENV = "IPFS_ACCELERATE_AGENT_TASK_CHECKPOINT_DIR"


class ScientificSchedule(DurableSchedule):
    """Same exclusive reservations as preparation, but scientific cells may complete."""

    def finish_cell(self, attempt_id: str, *, result_sha256: str | None, error: str | None, scientific: bool) -> None:
        self._load()
        cell = self._state["cells"].get(attempt_id)
        if cell is None:
            raise RuntimeError("cell was never reserved")
        if cell["consumed"]:
            raise RuntimeError("silent replay of a consumed cell is forbidden")
        cell["state"] = "completed" if error is None else "failed_consumed"
        cell["consumed"] = 1
        cell["result_sha256"] = result_sha256
        cell["error"] = error
        cell["updated_at"] = utc_now()
        self._persist()


def atomic_json(path: Path, value: Any) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + ".tmp")
    write_json(tmp, value, exist_ok=True)
    tmp.replace(path)


def checkpoint_dirs() -> list[Path]:
    dirs = [HERE]
    env = os.environ.get(CHECKPOINT_ENV)
    if env:
        dirs.append(Path(env))
    return dirs


def save_progress(payload: dict[str, Any]) -> None:
    for directory in checkpoint_dirs():
        try:
            directory.mkdir(parents=True, exist_ok=True)
            atomic_json(directory / "progress.json", payload)
        except OSError:
            continue


def extract_program(response_text: str) -> tuple[str, str | None]:
    try:
        value = json.loads(response_text)
    except Exception as exc:
        return response_text, type(exc).__name__ + ": " + str(exc)
    if isinstance(value, dict) and isinstance(value.get("program"), str):
        return value["program"], None
    return response_text, "response JSON missing program string"


def run_scientific_attempt(
    task: dict[str, Any],
    arm: str,
    seed: int,
    transport: QualifiedLocalTransport,
    output: Path,
    *,
    wall_seconds: int = ATTEMPT_WALL,
) -> dict[str, Any]:
    if wall_seconds > ATTEMPT_WALL:
        raise ValueError("attempt wall exceeds 120 seconds")
    output = Path(output)
    output.mkdir(parents=True, exist_ok=True)
    started = time.monotonic()
    cpu_started = time.process_time()
    history: list[dict[str, Any]] = []
    records: list[dict[str, Any]] = []
    terminal = "budget_exhausted"
    usage = resource.getrusage(resource.RUSAGE_CHILDREN)
    parsed_program = False
    for iteration in range(MAX_CALLS):
        remaining = wall_seconds - (time.monotonic() - started)
        if remaining <= 1:
            terminal = "budget_exhausted_before_full_execution_allowance"
            break
        directory = output / f"iteration-{iteration:02d}"
        directory.mkdir()
        messages = messages_for(task, arm, history)
        write_json(directory / "messages.json", messages)
        row: dict[str, Any] = {
            "iteration": iteration,
            "arm": arm,
            "seed": seed,
            "model_calls": 0,
            "prompt_tokens": None,
            "completion_tokens": None,
            "terminal": "started",
            "model_generated": False,
            "constructed_program_substituted": False,
        }
        try:
            response = transport.respond(
                messages,
                seed,
                directory,
                remaining,
                attempt_id=output.name,
                call_id=output.name + f"-{iteration:02d}",
            )
            if response["prompt_tokens"] != response["preflight_input_count"]:
                raise ValueError("prompt_tokens != preflight input_count")
            if response["prompt_tokens"] > MAX_INPUT:
                raise ValueError("2048 input-token ceiling exceeded")
            if response["completion_tokens"] > MAX_OUTPUT:
                raise ValueError("1024 output-token ceiling violated")
            program, parse_error = extract_program(response["response_text"])
            parsed_program = parse_error is None
            (directory / "candidate.py").write_text(program)
            write_json(
                directory / "candidate_parse.json",
                {
                    "parse_error": parse_error,
                    "program_extracted": parse_error is None,
                    "constructed_program_substituted": False,
                    "candidate_sha256": file_sha(directory / "candidate.py"),
                },
            )
            observed = execute_profiled_program(
                program,
                task["policy"]["expected_payload"],
                directory / "sandbox",
                output.name + f"-{iteration:02d}",
            )
            observed["scientific_benchmark"] = True
            write_json(directory / "result.json", {k: v for k, v in observed.items() if k != "observation"})
            write_json(directory / "observation.json", observed["observation"])
            row.update({key: response[key] for key in ("model_calls", "prompt_tokens", "completion_tokens", "model_generated", "origin")})
            row.update(
                useful_work=observed["useful_work"],
                forbidden_effect=observed["forbidden_effect"],
                source_profile_supported=observed["source_profile_supported"],
                profile_diagnostic=observed["profile_diagnostic"],
                parse_error=parse_error,
                constructed_program_substituted=False,
                terminal="useful_work" if observed["useful_work"] else "candidate_failed",
            )
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
                    "response_text": raw_path.read_text() if raw_path.exists() else program,
                    "feedback": feedback,
                }
            )
            records.append(row)
            write_json(directory / "iteration_result.json", row)
            if observed["useful_work"]:
                terminal = "useful_work"
                break
            terminal = row["terminal"]
            if parse_error is not None:
                break
        except BaseException as exc:
            row.update(
                terminal="transport_or_format_failure",
                error_type=type(exc).__name__,
                error=str(exc),
                constructed_program_substituted=False,
            )
            records.append(row)
            write_json(directory / "iteration_result.json", row)
            terminal = row["terminal"]
            break
    child = resource.getrusage(resource.RUSAGE_CHILDREN)
    result = {
        "schema": "la-closed-loop-attempt/v1",
        "arm": arm,
        "seed": seed,
        "iterations": records,
        "terminal": terminal,
        "model_calls": sum(row.get("model_calls") or 0 for row in records),
        "wall_seconds": time.monotonic() - started,
        "cpu_seconds": time.process_time() - cpu_started,
        "descendant_cpu_seconds": (child.ru_utime + child.ru_stime) - (usage.ru_utime + usage.ru_stime),
        "peak_memory_kb": child.ru_maxrss,
        "scientific_benchmark": True,
        "paid_budget": PAID_BUDGET,
        "overrun": (time.monotonic() - started) > wall_seconds,
        "unknown_costs": False,
        "constructed_program_substituted": False,
        "parsed_program": parsed_program,
        "mock": False,
    }
    write_json(output / "result.json", result)
    return result


def planned_cells(study_dir: Path, batch: dict[str, Any]) -> list[dict[str, Any]]:
    schedule_doc = load_json(study_dir / "schedule.json")
    cases = {row["id"]: row for row in load_json(study_dir / "cohort/cases.json")["cases"]}
    expected = build_schedule(schedule_doc["case_ids"])
    family = batch["family_binding"]
    family_cases = [family + ":case-0", family + ":case-1"]
    cells = []
    for row in expected:
        if row["case_id"] not in family_cases:
            continue
        info = cases[row["case_id"]]
        item = dict(row)
        item["family_id"] = info["source_family"]
        item["population"] = info["population"]
        item["split"] = info["split"]
        item["source_id"] = info["source_id"]
        item["batch_id"] = batch["id"]
        cells.append(item)
    if len(cells) != 30:
        raise RuntimeError("expected 30 identities for this family batch")
    return cells


def load_batch(study_dir: Path, batch_id: str) -> dict[str, Any]:
    batches = load_json(study_dir / "family_batches.json")
    for row in batches["batches"]:
        if row["id"] == batch_id:
            return row
    raise RuntimeError("unknown batch " + batch_id)


def main() -> None:
    output = HERE
    study = load_json(STUDY / "prospective_study.json")
    freeze_sha256 = study["freeze_sha256"]
    batch = load_batch(STUDY, BATCH_ID)
    cells = planned_cells(STUDY, batch)
    cases = {row["id"]: row for row in load_json(STUDY / "cohort/cases.json")["cases"]}
    model_profile = load_json(STUDY / "model_profile.json")
    runtime = load_json(STUDY / "qualification/runtime.json")
    driver_sha = file_sha(STUDY / "driver.py")
    effects_sha = file_sha(ROOT / "papers/completion/law_to_action/benchmark/handlers/effects.py")
    if runtime["source_files"]["papers/completion/law_to_action/benchmark/generated_code_study/driver.py"] != driver_sha:
        raise RuntimeError("driver.py diverged from qualified runtime pin")
    if runtime["source_files"]["papers/completion/law_to_action/benchmark/handlers/effects.py"] != effects_sha:
        raise RuntimeError("effects.py diverged from qualified runtime pin")
    if digest(model_profile) != study["model_profile_sha256"]:
        raise RuntimeError("model profile digest diverged from freeze")

    model_dir = output / "model"
    model_dir.mkdir(parents=True, exist_ok=True)
    weights_src = STUDY / "qualification/model" / WEIGHTS_FILE
    weights_dst = model_dir / WEIGHTS_FILE
    if not weights_dst.is_file():
        shutil.copy2(weights_src, weights_dst)
    if file_sha(weights_dst) != model_profile["weights_sha256"]:
        raise RuntimeError("copied weights do not match frozen model profile")

    store = ScientificSchedule(output / CONTROL_FILE, owner=OWNER, freeze_sha256=freeze_sha256)
    claim = store.claim()
    write_json(output / "ownership.json", claim, exist_ok=True)

    service = LocalModelService(model_dir)
    if service.weights_sha256 != model_profile["weights_sha256"]:
        raise RuntimeError("loaded weights sha256 mismatch")
    if service.tokenizer_sha256 != model_profile["tokenizer_sha256"]:
        raise RuntimeError("tokenizer sha256 mismatch")
    if service.chat_template_sha256 != model_profile["chat_template_sha256"]:
        raise RuntimeError("chat template sha256 mismatch")
    if service.revision != model_profile["model_revision"]:
        raise RuntimeError("model revision mismatch")
    server = ModelHTTPServer(service)
    base_url = server.start()
    time.sleep(0.05)
    profile = dict(model_profile)
    profile["base_url"] = base_url
    transport = QualifiedLocalTransport(profile, store)
    write_json(
        output / "service.json",
        {
            "schema": "la033-model-service/v1",
            "base_url": base_url,
            "model_id": service.revision,
            "model_revision": service.revision,
            "weights_sha256": service.weights_sha256,
            "tokenizer_sha256": service.tokenizer_sha256,
            "chat_template_sha256": service.chat_template_sha256,
            "model_profile_sha256": study["model_profile_sha256"],
            "prompt_profile_sha256": study["prompt_profile_sha256"],
            "freeze_sha256": freeze_sha256,
            "warm_reuse": True,
            "constructed_transport": False,
            "mock": False,
            "systemd_required": False,
            "indefinitely_running_required": False,
            "started_at": utc_now(),
        },
        exist_ok=True,
    )

    terminals: dict[str, str] = {}
    errors: dict[str, str | None] = {}
    try:
        for index, cell in enumerate(cells):
            attempt_id = cell["attempt_id"]
            cell_dir = output / "cells" / attempt_id
            existing = store.snapshot()["cells"]
            prior = next((row for row in existing if row["attempt_id"] == attempt_id), None)
            if prior and prior.get("consumed"):
                result = load_json(cell_dir / "result.json")
                terminals[attempt_id] = result["terminal"]
                errors[attempt_id] = prior.get("error")
                save_progress({"completed": index + 1, "total": 30, "last": attempt_id, "resumed": True})
                continue
            case = cases[cell["case_id"]]
            task = {
                "instruction": case["instruction"],
                "split": case["split"],
                "source_family": case["source_family"],
                "policy": case["policy"],
                "retrieval": case["retrieval"],
                "oracle_released": False,
            }
            if prior is None and cell_dir.exists():
                shutil.rmtree(cell_dir)
            cell_dir.mkdir(parents=True, exist_ok=True)
            reserved = store.reserve_cell(cell, scientific=True)
            write_json(cell_dir / "reservation.json", reserved, exist_ok=True)
            bindings = {
                "schema": "la033-cell-bindings/v1",
                "attempt_id": attempt_id,
                "schedule_index": cell["schedule_index"],
                "case_id": cell["case_id"],
                "family_id": cell["family_id"],
                "source_id": cell["source_id"],
                "population": cell["population"],
                "split": cell["split"],
                "arm": cell["arm"],
                "seed": cell["seed"],
                "batch_id": BATCH_ID,
                "freeze_sha256": freeze_sha256,
                "schedule_identity_digest": study["schedule_identity_digest"],
                "model_profile_sha256": study["model_profile_sha256"],
                "prompt_profile_sha256": study["prompt_profile_sha256"],
                "model_id": model_profile["model_id"],
                "model_revision": model_profile["model_revision"],
                "weights_sha256": model_profile["weights_sha256"],
                "tokenizer_sha256": model_profile["tokenizer_sha256"],
                "chat_template_sha256": model_profile["chat_template_sha256"],
                "driver_sha256": driver_sha,
                "effects_sha256": effects_sha,
                "runtime_python": sys.executable,
                "execution_profile": PROFILE_ID,
                "scientific": True,
                "constructed_program_substituted": False,
                "constructed_transport": False,
                "mock": False,
            }
            write_json(cell_dir / "bindings.json", bindings, exist_ok=True)
            try:
                result = run_scientific_attempt(task, cell["arm"], int(cell["seed"]), transport, cell_dir)
                result_sha = file_sha(cell_dir / "result.json")
                store.finish_cell(attempt_id, result_sha256=result_sha, error=None, scientific=True)
                terminals[attempt_id] = result["terminal"]
                errors[attempt_id] = None
            except BaseException as exc:
                store.interrupt(attempt_id, type(exc).__name__)
                failure = {
                    "schema": "la-closed-loop-attempt/v1",
                    "arm": cell["arm"],
                    "seed": cell["seed"],
                    "iterations": [],
                    "terminal": "transport_or_format_failure",
                    "model_calls": 0,
                    "error_type": type(exc).__name__,
                    "error": str(exc),
                    "scientific_benchmark": True,
                    "paid_budget": PAID_BUDGET,
                    "unknown_costs": True,
                    "constructed_program_substituted": False,
                    "mock": False,
                }
                write_json(cell_dir / "result.json", failure, exist_ok=True)
                store.finish_cell(
                    attempt_id,
                    result_sha256=file_sha(cell_dir / "result.json"),
                    error=type(exc).__name__ + ": " + str(exc),
                    scientific=True,
                )
                terminals[attempt_id] = failure["terminal"]
                errors[attempt_id] = type(exc).__name__
            save_progress(
                {
                    "completed": index + 1,
                    "total": 30,
                    "last": attempt_id,
                    "terminal": terminals[attempt_id],
                    "at": utc_now(),
                }
            )
    finally:
        accounting = service.accounting()
        server.stop()
        store.close()
        write_json(output / "accounting.json", accounting, exist_ok=True)

    snap = store.snapshot()
    batch_doc = {
        "schema": "la033-family-batch-result/v1",
        "batch_id": BATCH_ID,
        "title": batch["title"],
        "phase": batch["phase"],
        "phase_family_slot": batch["phase_family_slot"],
        "family_id": batch["family_binding"],
        "source_id": batch["source_id"],
        "population": batch["population"],
        "paired_cases": batch["paired_cases"],
        "arms": batch["arms"],
        "seeds": batch["seeds"],
        "planned_cells": 30,
        "terminal_records": len(terminals),
        "scientific_cells_completed": snap["scientific_cells_completed"],
        "attempt_ids": [row["attempt_id"] for row in cells],
        "terminals": terminals,
        "errors": errors,
        "freeze_sha256": freeze_sha256,
        "schedule_identity_digest": study["schedule_identity_digest"],
        "model_profile_sha256": study["model_profile_sha256"],
        "prompt_profile_sha256": study["prompt_profile_sha256"],
        "driver_sha256": driver_sha,
        "effects_sha256": effects_sha,
        "execution_profile": PROFILE_ID,
        "model_id": model_profile["model_id"],
        "weights_sha256": model_profile["weights_sha256"],
        "paid_budget": PAID_BUDGET,
        "mock": False,
        "constructed_transport": False,
        "constructed_program_substituted": False,
        "silent_replay": False,
        "protocol_accounted": True,
        "scientific_benchmark": True,
        "ownership": claim,
        "completed_at": utc_now(),
    }
    atomic_json(output / "batch.json", batch_doc)
    print(json.dumps({"status": "PASS" if len(terminals) == 30 else "INCOMPLETE", "batch_id": BATCH_ID, "terminal_records": len(terminals), "terminals": terminals}, sort_keys=True))


if __name__ == "__main__":
    main()
