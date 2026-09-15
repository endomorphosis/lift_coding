#!/usr/bin/python3.12
"""Execute frozen family-batch LA-033 with the qualified local model.

Every original identity is reserved before dispatch. Model calls are reserved
before the HTTP request. Generated candidates are the actual model bytes; a
fixed program is never substituted. Measured candidate failure is retained.
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
    BATCH_ATTEMPT_SECONDS,
    CONTROL_FILE,
    MAX_CALLS,
    MAX_INPUT,
    PAID_BUDGET,
    PROFILE_ID,
    WEIGHTS_FILE,
    DurableSchedule,
    LocalModelService,
    ModelHTTPServer,
    QualifiedLocalTransport,
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
OWNER = "owner:la033"


def resolve_checkpoint() -> Path:
    configured = os.environ.get("IPFS_ACCELERATE_AGENT_TASK_CHECKPOINT_DIR")
    fallback = Path(
        "/home/barberb/.local/state/ipfs_accelerate_py/vericodegen-2026/law_to_action/state/paper_law_to_action_database_portal_attempts/f4708b604a85cb1a71909e24/implementation_checkpoints/la-033-ce181b44eaaa"
    )
    for candidate in (Path(configured) if configured else None, fallback, HERE / "checkpoints"):
        if candidate is None:
            continue
        try:
            candidate.mkdir(parents=True, exist_ok=True)
            probe = candidate / ".writable"
            probe.write_text("ok")
            probe.unlink()
            return candidate
        except OSError:
            continue
    return HERE / "checkpoints"


CHECKPOINT = resolve_checkpoint()


def cell_relpath(attempt_id: str) -> str:
    seed, arm, rest = attempt_id.split(":", 2)
    case = rest.rsplit(":", 1)[-1]
    return f"cells/{seed}/{arm}/{case}"


def atomic_write_json(path: Path, value: Any) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + ".tmp")
    write_json(tmp, value, exist_ok=True)
    tmp.replace(path)


class ScientificSchedule(DurableSchedule):
    def finish_cell(self, attempt_id: str, *, result_sha256: str | None, error: str | None, scientific: bool) -> None:
        self._load()
        cell = self._state["cells"].get(attempt_id)
        if cell is None:
            raise RuntimeError("cell was never reserved")
        if cell["consumed"]:
            raise RuntimeError("silent replay of a consumed cell is forbidden")
        cell["state"] = "completed" if error is None else "failed_consumed"
        cell["consumed"] = 1
        cell["scientific"] = int(scientific)
        cell["result_sha256"] = result_sha256
        cell["error"] = error
        cell["updated_at"] = utc_now()
        self._persist()


def extract_candidate(response_text: str) -> tuple[str, str | None]:
    try:
        value = json.loads(response_text)
    except Exception as exc:
        return response_text, "json_parse:" + type(exc).__name__
    program = value.get("program") if isinstance(value, dict) else None
    if isinstance(program, str) and program != "":
        return program, None
    return response_text, "missing_program_field"


def load_context() -> dict[str, Any]:
    study = load_json(STUDY / "prospective_study.json")
    batches = load_json(STUDY / "family_batches.json")
    schedule_doc = load_json(STUDY / "schedule.json")
    cases = {row["id"]: row for row in load_json(STUDY / "cohort/cases.json")["cases"]}
    model_profile = load_json(STUDY / "model_profile.json")
    runtime = load_json(STUDY / "qualification/runtime.json")
    batch = next(row for row in batches["batches"] if row["id"] == BATCH_ID)
    from driver import build_schedule

    expected = build_schedule(schedule_doc["case_ids"])
    cells = [row for row in expected if row["case_id"] in batch["paired_cases"]]
    if len(cells) != 30:
        raise RuntimeError("expected 30 identities")
    for row in cells:
        info = cases[row["case_id"]]
        row["family_id"] = info["source_family"]
        row["population"] = info["population"]
        row["split"] = info["split"]
        row["source_id"] = info["source_id"]
        row["task"] = info
    return {
        "study": study,
        "batch": batch,
        "cells": cells,
        "cases": cases,
        "model_profile": model_profile,
        "runtime": runtime,
        "schedule_doc": schedule_doc,
    }


def bindings_for(ctx: dict[str, Any]) -> dict[str, Any]:
    study = ctx["study"]
    runtime = ctx["runtime"]
    model_profile = ctx["model_profile"]
    batch = ctx["batch"]
    return {
        "batch_id": BATCH_ID,
        "family_binding": batch["family_binding"],
        "source_id": batch["source_id"],
        "phase": batch["phase"],
        "freeze_sha256": study["freeze_sha256"],
        "schedule_identity_digest": study["schedule_identity_digest"],
        "model_profile_sha256": study["model_profile_sha256"],
        "prompt_profile_sha256": study["prompt_profile_sha256"],
        "execution_profile": PROFILE_ID,
        "weights_sha256": model_profile["weights_sha256"],
        "tokenizer_sha256": model_profile["tokenizer_sha256"],
        "chat_template_sha256": model_profile["chat_template_sha256"],
        "model_id": model_profile["model_id"],
        "model_revision": model_profile["model_revision"],
        "tokenizer_revision": model_profile["tokenizer_revision"],
        "deployment_sha256": model_profile["deployment_sha256"],
        "paid_budget": PAID_BUDGET,
        "runtime_driver_sha256": runtime["source_files"]["papers/completion/law_to_action/benchmark/generated_code_study/driver.py"],
        "runtime_handlers_sha256": runtime["source_files"]["papers/completion/law_to_action/benchmark/handlers/effects.py"],
        "mock": False,
        "constructed_transport": False,
        "fixed_program_substituted": False,
        "scientific_execution": True,
    }


def run_attempt(
    task: dict[str, Any],
    cell: dict[str, Any],
    transport: QualifiedLocalTransport,
    output: Path,
    remaining_batch: float,
) -> dict[str, Any]:
    output.mkdir(parents=True, exist_ok=True)
    started = time.monotonic()
    cpu_started = time.process_time()
    usage = resource.getrusage(resource.RUSAGE_CHILDREN)
    history: list[dict[str, Any]] = []
    records: list[dict[str, Any]] = []
    terminal = "budget_exhausted"
    wall_limit = min(ATTEMPT_WALL, max(1.0, remaining_batch))
    attempt_id = cell["attempt_id"]
    for iteration in range(MAX_CALLS):
        remaining = wall_limit - (time.monotonic() - started)
        if remaining <= 1:
            terminal = "budget_exhausted_before_full_execution_allowance"
            break
        directory = output / f"iteration-{iteration:02d}"
        directory.mkdir(exist_ok=True)
        messages = messages_for(task, cell["arm"], history)
        write_json(directory / "messages.json", messages, exist_ok=True)
        row: dict[str, Any] = {
            "iteration": iteration,
            "arm": cell["arm"],
            "seed": cell["seed"],
            "model_calls": 0,
            "prompt_tokens": None,
            "completion_tokens": None,
            "terminal": "started",
            "origin": None,
            "model_generated": False,
        }
        call_id = f"{attempt_id}:{iteration:02d}"
        try:
            response = transport.respond(messages, cell["seed"], directory, remaining, attempt_id, call_id)
            if response["prompt_tokens"] != response["preflight_input_count"]:
                raise ValueError("prompt_tokens != preflight input_count")
            if response["preflight_input_count"] > MAX_INPUT:
                raise ValueError("2048 input-token ceiling exceeded")
            candidate, parse_error = extract_candidate(response["response_text"])
            (directory / "candidate.py").write_text(candidate)
            observed = execute_profiled_program(
                candidate,
                task["policy"]["expected_payload"],
                directory / "sandbox",
                f"{attempt_id}:{iteration:02d}",
            )
            write_json(directory / "result.json", {k: v for k, v in observed.items() if k != "observation"}, exist_ok=True)
            write_json(directory / "sandbox" / "observation.json", observed["observation"], exist_ok=True)
            row.update(
                {
                    "model_calls": response["model_calls"],
                    "prompt_tokens": response["prompt_tokens"],
                    "completion_tokens": response["completion_tokens"],
                    "model_generated": True,
                    "origin": "qualified-local-model",
                    "useful_work": observed["useful_work"],
                    "forbidden_effect": observed["forbidden_effect"],
                    "source_profile_supported": observed["source_profile_supported"],
                    "profile_diagnostic": observed["profile_diagnostic"],
                    "parse_error": parse_error,
                    "terminal": "useful_work" if observed["useful_work"] else "candidate_failed",
                }
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
            history.append({"response_text": response["response_text"], "feedback": feedback})
            records.append(row)
            write_json(directory / "iteration_result.json", row, exist_ok=True)
            if observed["useful_work"]:
                terminal = "useful_work"
                break
            terminal = "candidate_failed"
        except BaseException as exc:
            row.update(
                {
                    "terminal": "transport_or_format_failure",
                    "error_type": type(exc).__name__,
                    "error": str(exc),
                    "model_calls": 1 if (directory / "inference_reserved.json").is_file() else 0,
                    "origin": "qualified-local-model",
                }
            )
            records.append(row)
            write_json(directory / "iteration_result.json", row, exist_ok=True)
            terminal = "transport_or_format_failure"
            break
    child = resource.getrusage(resource.RUSAGE_CHILDREN)
    result = {
        "schema": "la-closed-loop-attempt/v1",
        "attempt_id": attempt_id,
        "batch_id": BATCH_ID,
        "case_id": cell["case_id"],
        "family_id": cell["family_id"],
        "arm": cell["arm"],
        "seed": cell["seed"],
        "split": cell["split"],
        "schedule_index": cell["schedule_index"],
        "arm_position": cell["arm_position"],
        "iterations": records,
        "terminal": terminal,
        "useful_work": terminal == "useful_work",
        "model_calls": sum(int(row.get("model_calls") or 0) for row in records),
        "wall_seconds": time.monotonic() - started,
        "cpu_seconds": time.process_time() - cpu_started,
        "descendant_cpu_seconds": (child.ru_utime + child.ru_stime) - (usage.ru_utime + usage.ru_stime),
        "peak_memory_kb": child.ru_maxrss,
        "scientific_benchmark": True,
        "paid_budget": PAID_BUDGET,
        "overrun": (time.monotonic() - started) > wall_limit,
        "unknown_costs": False,
        "origin": "qualified-local-model",
        "constructed_outputs": False,
        "fixed_program_substituted": False,
        "mock": False,
    }
    return result


def admit_cell(directory: Path, result: dict[str, Any], reservation: dict[str, Any]) -> dict[str, Any]:
    result_sha = file_sha(directory / "result.json")
    generated = any(row.get("model_generated") for row in result["iterations"])
    reserved_calls = any((directory / f"iteration-{row['iteration']:02d}" / "inference_reserved.json").is_file() for row in result["iterations"])
    candidates = any((directory / f"iteration-{row['iteration']:02d}" / "candidate.py").is_file() for row in result["iterations"] if row.get("model_generated"))
    admitted = (
        reservation.get("reservation_sha256")
        and result["scientific_benchmark"] is True
        and result["unknown_costs"] is False
        and result["paid_budget"] == PAID_BUDGET
        and result["fixed_program_substituted"] is False
        and result["constructed_outputs"] is False
        and (generated or result["terminal"] == "transport_or_format_failure")
        and (candidates or result["terminal"] == "transport_or_format_failure")
        and (reserved_calls or result["model_calls"] == 0)
        and result["terminal"] not in {None, "", "started", "unrun"}
    )
    record = {
        "schema": "la-family-batch-admission/v1",
        "attempt_id": result["attempt_id"],
        "admitted": bool(admitted),
        "result_sha256": result_sha,
        "reservation_sha256": reservation.get("reservation_sha256"),
        "terminal": result["terminal"],
        "model_calls": result["model_calls"],
        "scientific": True,
        "reason": "protocol-accounted terminal scientific record" if admitted else "missing reservation/candidate/cost evidence",
    }
    write_json(directory / "admitted.json", record, exist_ok=True)
    if not admitted:
        raise RuntimeError("cell unadmitted: " + result["attempt_id"])
    return record


def write_ledgers(output: Path, rows: list[dict[str, Any]]) -> None:
    costs = output / "costs.jsonl"
    raw = output / "raw.jsonl"
    with costs.open("w") as cost_handle, raw.open("w") as raw_handle:
        for row in rows:
            cost = {
                "attempt_id": row["attempt_id"],
                "batch_id": BATCH_ID,
                "case_id": row["case_id"],
                "arm": row["arm"],
                "seed": row["seed"],
                "wall_seconds": row["wall_seconds"],
                "cpu_seconds": row["cpu_seconds"],
                "descendant_cpu_seconds": row["descendant_cpu_seconds"],
                "peak_memory_kb": row["peak_memory_kb"],
                "model_calls": row["model_calls"],
                "prompt_tokens": sum(int(item.get("prompt_tokens") or 0) for item in row["iterations"]),
                "completion_tokens": sum(int(item.get("completion_tokens") or 0) for item in row["iterations"]),
                "paid_budget": PAID_BUDGET,
                "unknown_costs": False,
                "terminal": row["terminal"],
            }
            cost_handle.write(json.dumps(cost, sort_keys=True, separators=(",", ":")) + "\n")
            raw_handle.write(json.dumps({"attempt_id": row["attempt_id"], "terminal": row["terminal"], "useful_work": row["useful_work"], "model_calls": row["model_calls"], "result_sha256": row["result_sha256"]}, sort_keys=True, separators=(",", ":")) + "\n")


def main() -> None:
    ctx = load_context()
    output = HERE
    output.mkdir(parents=True, exist_ok=True)
    CHECKPOINT.mkdir(parents=True, exist_ok=True)
    binding = bindings_for(ctx)
    atomic_write_json(output / "freeze_binding.json", binding)
    model_dir = output / "model"
    model_dir.mkdir(parents=True, exist_ok=True)
    src_weights = STUDY / "qualification/model" / WEIGHTS_FILE
    dst_weights = model_dir / WEIGHTS_FILE
    if not dst_weights.is_file():
        shutil.copy2(src_weights, dst_weights)
    if file_sha(dst_weights) != ctx["model_profile"]["weights_sha256"]:
        raise RuntimeError("pinned model weights mismatch")
    store = ScientificSchedule(output / CONTROL_FILE, owner=OWNER, freeze_sha256=ctx["study"]["freeze_sha256"])
    store.claim()
    service = LocalModelService(model_dir)
    if service.weights_sha256 != ctx["model_profile"]["weights_sha256"]:
        raise RuntimeError("service weights mismatch")
    if service.revision != ctx["model_profile"]["model_revision"]:
        raise RuntimeError("service revision mismatch")
    server = ModelHTTPServer(service)
    profile = dict(ctx["model_profile"])
    profile["base_url"] = server.start()
    transport = QualifiedLocalTransport(profile, store)
    batch_started = time.monotonic()
    completed: list[dict[str, Any]] = []
    manifest_cells = {row["attempt_id"]: cell_relpath(row["attempt_id"]) for row in ctx["cells"]}
    atomic_write_json(
        output / "manifest.json",
        {
            "schema": "la-family-batch-manifest/v1",
            "batch_id": BATCH_ID,
            "family_binding": ctx["batch"]["family_binding"],
            "attempt_ids": [row["attempt_id"] for row in ctx["cells"]],
            "cells": manifest_cells,
        },
    )
    try:
        for cell in ctx["cells"]:
            elapsed = time.monotonic() - batch_started
            remaining = BATCH_ATTEMPT_SECONDS - elapsed
            if remaining <= 1:
                raise RuntimeError("batch scientific wall exhausted before all identities")
            rel = manifest_cells[cell["attempt_id"]]
            directory = output / rel
            result_path = directory / "result.json"
            if result_path.is_file() and (directory / "admitted.json").is_file():
                existing = load_json(result_path)
                existing["result_sha256"] = file_sha(result_path)
                completed.append(existing)
                continue
            reservation = store.reserve_cell(
                {
                    "attempt_id": cell["attempt_id"],
                    "case_id": cell["case_id"],
                    "arm": cell["arm"],
                    "seed": cell["seed"],
                    "split": cell["split"],
                    "family_id": cell["family_id"],
                    "batch_id": BATCH_ID,
                },
                scientific=True,
            )
            directory.mkdir(parents=True, exist_ok=True)
            write_json(directory / "reservation.json", reservation, exist_ok=True)
            result = run_attempt(cell["task"], cell, transport, directory, remaining)
            result["bindings"] = dict(binding)
            write_json(result_path, result, exist_ok=True)
            admitted = admit_cell(directory, result, reservation)
            store.finish_cell(cell["attempt_id"], result_sha256=admitted["result_sha256"], error=None, scientific=True)
            result["result_sha256"] = admitted["result_sha256"]
            completed.append(result)
            atomic_write_json(
                CHECKPOINT / "progress.json",
                {
                    "batch_id": BATCH_ID,
                    "completed": [row["attempt_id"] for row in completed],
                    "count": len(completed),
                    "updated_at": utc_now(),
                },
            )
        scientific_wall = time.monotonic() - batch_started
        if scientific_wall > BATCH_ATTEMPT_SECONDS:
            raise RuntimeError("batch scientific wall exceeded")
        write_ledgers(output, completed)
        summary = {
            "schema": "la-family-batch-result/v1",
            "batch_id": BATCH_ID,
            "status": "COMPLETE",
            "complete": True,
            "family_binding": ctx["batch"]["family_binding"],
            "source_id": ctx["batch"]["source_id"],
            "phase": ctx["batch"]["phase"],
            "planned_cells": 30,
            "terminal_cells": len(completed),
            "admitted_cells": len(completed),
            "useful_work_cells": sum(1 for row in completed if row.get("useful_work")),
            "candidate_failed_cells": sum(1 for row in completed if row.get("terminal") == "candidate_failed"),
            "transport_failure_cells": sum(1 for row in completed if row.get("terminal") == "transport_or_format_failure"),
            "model_calls": sum(row["model_calls"] for row in completed),
            "scientific_wall_seconds": scientific_wall,
            "service_accounting": service.accounting(),
            "paid_budget": PAID_BUDGET,
            "mock": False,
            "constructed_outputs": False,
            "fixed_program_substituted": False,
            "silent_replay": False,
            "freeze_sha256": ctx["study"]["freeze_sha256"],
            "model_revision": ctx["model_profile"]["model_revision"],
            "updated_at": utc_now(),
        }
        atomic_write_json(output / "batch.json", summary)
        atomic_write_json(CHECKPOINT / "complete.json", {"status": "COMPLETE", "batch_sha256": file_sha(output / "batch.json"), "cells": 30})
        print(json.dumps({"status": "COMPLETE", "cells": 30, "model_calls": summary["model_calls"], "scientific_wall_seconds": scientific_wall}, sort_keys=True))
    finally:
        server.stop()
        store.close()


if __name__ == "__main__":
    main()
