#!/usr/bin/python3.12
"""Execute one frozen generated-code family batch with the qualified local model.

Preparation driver methods refuse to mark planned scientific cells complete.
This batch owner reserves, infers, executes, accounts and consumes those
identities into this results tree. Constructed programs are never substituted.
"""
from __future__ import annotations

import json
import os
import resource
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[6]
STUDY = ROOT / "papers/completion/law_to_action/benchmark/generated_code_study"
sys.path.insert(0, str(STUDY))
from driver import (  # noqa: E402
    ARMS,
    ATTEMPT_WALL,
    BATCH_ATTEMPT_SECONDS,
    CONTROL_FILE,
    MAX_CALLS,
    MAX_INPUT,
    MAX_OUTPUT,
    PAID_BUDGET,
    PROFILE_ID,
    RAW_RESPONSE_FILE,
    SEEDS,
    DurableSchedule,
    LocalModelService,
    ModelHTTPServer,
    QualifiedLocalTransport,
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
OWNER = "owner:la033"
def checkpoint_dir() -> Path:
    configured = os.environ.get("IPFS_ACCELERATE_AGENT_TASK_CHECKPOINT_DIR")
    candidates = []
    if configured:
        candidates.append(Path(configured))
    candidates.append(
        Path(
            "/home/barberb/.local/state/ipfs_accelerate_py/vericodegen-2026/law_to_action/"
            "state/paper_law_to_action_database_portal_attempts/cd190edfd2eff7c4fbbda4c2/"
            "implementation_checkpoints/la-033-ce181b44eaaa"
        )
    )
    candidates.append(HERE / "checkpoint")
    for path in candidates:
        try:
            path.mkdir(parents=True, exist_ok=True)
            probe = path / ".write-probe"
            probe.write_text("ok")
            probe.unlink()
            return path
        except OSError:
            continue
    raise RuntimeError("no writable checkpoint directory")


CHECKPOINT = checkpoint_dir()


def write_text(path: Path, text: str, *, exist_ok: bool = False) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    mode = "w" if exist_ok else "x"
    with path.open(mode, encoding="utf-8") as handle:
        handle.write(text)


def atomic_json(path: Path, value: object) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + ".tmp")
    with tmp.open("w", encoding="utf-8") as handle:
        json.dump(value, handle, sort_keys=True, indent=2, allow_nan=False)
        handle.write("\n")
    tmp.replace(path)


def extract_program(response_text: str) -> tuple[str | None, str | None]:
    try:
        value = json.loads(response_text)
    except Exception as exc:
        return None, f"{type(exc).__name__}: {exc}"
    if not isinstance(value, dict) or set(value) != {"program"}:
        return None, "Response must contain one bounded program string"
    program = value.get("program")
    if not isinstance(program, str) or not 0 < len(program.encode()) <= 32768:
        return None, "Response must contain one bounded program string"
    return program, None


class ScientificSchedule(DurableSchedule):
    """Same durable reservations as preparation, but scientific cells may finish."""

    def finish_cell(self, attempt_id: str, *, result_sha256: str | None, error: str | None, scientific: bool) -> None:
        self._load()
        cell = self._state["cells"].get(attempt_id)
        if cell is None:
            raise RuntimeError("cell was never reserved")
        if cell.get("consumed"):
            raise RuntimeError("silent replay of a consumed cell is forbidden")
        cell["state"] = "completed" if error is None else "failed_consumed"
        cell["consumed"] = 1
        cell["scientific"] = int(scientific)
        cell["result_sha256"] = result_sha256
        cell["error"] = error
        cell["updated_at"] = utc_now()
        self._persist()


def load_batch_context() -> dict:
    study = load_json(STUDY / "prospective_study.json")
    families = load_json(STUDY / "cohort/families.json")["families"]
    cases = {row["id"]: row for row in load_json(STUDY / "cohort/cases.json")["cases"]}
    schedule_doc = load_json(STUDY / "schedule.json")
    batches = load_json(STUDY / "family_batches.json")
    model_profile = load_json(STUDY / "model_profile.json")
    runtime = load_json(STUDY / "qualification/runtime.json")
    batch = next(row for row in batches["batches"] if row["id"] == BATCH_ID)
    expected = build_schedule(schedule_doc["case_ids"])
    case_map = cases
    identities = []
    for row in expected:
        info = case_map[row["case_id"]]
        if info["source_family"] != batch["family_binding"]:
            continue
        item = dict(row)
        item["family_id"] = info["source_family"]
        item["population"] = info["population"]
        item["split"] = info["split"]
        item["batch_id"] = BATCH_ID
        identities.append(item)
    if len(identities) != 30:
        raise RuntimeError(f"expected 30 identities, found {len(identities)}")
    return {
        "study": study,
        "batch": batch,
        "cases": cases,
        "families": families,
        "schedule_doc": schedule_doc,
        "model_profile": model_profile,
        "runtime": runtime,
        "identities": identities,
    }


def run_scientific_attempt(
    task: dict,
    identity: dict,
    transport: QualifiedLocalTransport,
    output: Path,
    store: ScientificSchedule,
    remaining_batch: float,
) -> dict:
    arm = identity["arm"]
    seed = int(identity["seed"])
    attempt_id = identity["attempt_id"]
    wall_seconds = min(ATTEMPT_WALL, max(1.0, remaining_batch))
    output.mkdir(parents=True, exist_ok=True)
    started = time.monotonic()
    cpu_started = time.process_time()
    usage = resource.getrusage(resource.RUSAGE_CHILDREN)
    history: list[dict] = []
    records: list[dict] = []
    terminal = "budget_exhausted"
    write_json(
        output / "attempt_start.json",
        {
            "schema": "la-closed-loop-attempt-start/v1",
            "attempt_id": attempt_id,
            "arm": arm,
            "seed": seed,
            "case_id": identity["case_id"],
            "family_id": identity["family_id"],
            "batch_id": BATCH_ID,
            "split": identity["split"],
            "schedule_index": identity["schedule_index"],
            "arm_position": identity["arm_position"],
            "task": {
                "id": task["id"],
                "source_family": task["source_family"],
                "split": task["split"],
                "instruction": task["instruction"],
                "policy": {k: v for k, v in task["policy"].items() if k != "expected_payload"},
                "retrieval": task.get("retrieval") or [],
            },
            "maximum_calls": MAX_CALLS,
            "maximum_wall_seconds": ATTEMPT_WALL,
            "scientific_benchmark": True,
            "constructed_transport": False,
            "fixed_program_substituted": False,
            "model_profile_sha256": transport.model_profile_sha256,
        },
    )
    for iteration in range(MAX_CALLS):
        remaining = wall_seconds - (time.monotonic() - started)
        if remaining <= 1:
            terminal = "budget_exhausted_before_full_execution_allowance"
            break
        directory = output / f"iteration-{iteration:02d}"
        directory.mkdir()
        messages = messages_for(task, arm, history)
        write_json(directory / "messages.json", messages)
        row = {
            "iteration": iteration,
            "attempt_id": attempt_id,
            "arm": arm,
            "seed": seed,
            "model_calls": 0,
            "prompt_tokens": None,
            "completion_tokens": None,
            "terminal": "started",
            "effect_status": "not_executed",
            "forbidden_effect": False,
            "useful_work": False,
            "inference_reserved": False,
            "token_usage_known": False,
        }
        try:
            response = transport.respond(
                messages,
                seed,
                directory,
                remaining,
                attempt_id=attempt_id,
                call_id=f"{attempt_id}-{iteration:02d}",
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
                    "inference_reserved": True,
                    "token_usage_known": isinstance(response["prompt_tokens"], int)
                    and isinstance(response["completion_tokens"], int),
                }
            )
            if response["prompt_tokens"] != response["preflight_input_count"]:
                raise ValueError("prompt_tokens != preflight input_count")
            if response["prompt_tokens"] > MAX_INPUT or response["completion_tokens"] > MAX_OUTPUT:
                raise ValueError("frozen token ceiling violated")
            write_text(directory / "generated_text.txt", response["response_text"])
            program, parse_error = extract_program(response["response_text"])
            if program is None:
                row.update(
                    terminal="transport_or_format_failure",
                    error=parse_error,
                    candidate_extracted=False,
                    effect_status="not_executed",
                )
                records.append(row)
                write_json(directory / "iteration_result.json", row)
                terminal = row["terminal"]
                break
            write_text(directory / "candidate.py", program)
            observed = execute_profiled_program(
                program,
                task["policy"]["expected_payload"],
                directory / "sandbox",
                f"{attempt_id}-{iteration:02d}",
            )
            observed["scientific_benchmark"] = True
            write_json(directory / "result.json", {k: v for k, v in observed.items() if k != "observation"})
            row.update(
                candidate_extracted=True,
                candidate_sha256=file_sha(directory / "candidate.py"),
                useful_work=observed["useful_work"],
                forbidden_effect=observed["forbidden_effect"],
                source_profile_supported=observed["source_profile_supported"],
                profile_diagnostic=observed["profile_diagnostic"],
                execution_error=observed["execution_error"],
                handler_calls=observed["handler_calls"],
                effect_status="measured",
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
            history.append({"response_text": response["response_text"], "feedback": feedback})
            records.append(row)
            write_json(directory / "iteration_result.json", row)
            if observed["useful_work"]:
                terminal = "useful_work"
                break
        except BaseException as exc:
            row.update(
                terminal="transport_or_format_failure",
                error_type=type(exc).__name__,
                error=str(exc),
                effect_status="not_executed" if not row.get("inference_reserved") else row.get("effect_status") or "unknown_after_execution_reservation",
            )
            if (directory / "inference_reserved.json").is_file():
                row["inference_reserved"] = True
                row["model_calls"] = max(int(row.get("model_calls") or 0), 1)
            records.append(row)
            write_json(directory / "iteration_result.json", row)
            terminal = row["terminal"]
            break
    child = resource.getrusage(resource.RUSAGE_CHILDREN)
    unknown_usage = sum(int(row.get("model_calls") or 0) > 0 and not row.get("token_usage_known") for row in records)
    result = {
        "schema": "la-closed-loop-attempt/v1",
        "attempt_id": attempt_id,
        "case_id": identity["case_id"],
        "family_id": identity["family_id"],
        "batch_id": BATCH_ID,
        "split": identity["split"],
        "population": identity["population"],
        "schedule_index": identity["schedule_index"],
        "arm_position": identity["arm_position"],
        "arm": arm,
        "seed": seed,
        "iterations": records,
        "terminal": terminal,
        "repair_attempts": max(0, len(records) - 1),
        "model_calls": sum(int(row.get("model_calls") or 0) for row in records),
        "tokens_measured": bool(records) and unknown_usage == 0,
        "unknown_token_usage_calls": unknown_usage,
        "known_prompt_tokens": sum(row.get("prompt_tokens") or 0 for row in records),
        "known_completion_tokens": sum(row.get("completion_tokens") or 0 for row in records),
        "wall_seconds": time.monotonic() - started,
        "cpu_seconds": time.process_time() - cpu_started,
        "descendant_cpu_seconds": (child.ru_utime + child.ru_stime) - (usage.ru_utime + usage.ru_stime),
        "peak_memory_kb": child.ru_maxrss,
        "paid_budget": PAID_BUDGET,
        "scientific_benchmark": True,
        "constructed_transport": False,
        "fixed_program_substituted": False,
        "mock": False,
        "admitted": True,
        "overrun": (time.monotonic() - started) > wall_seconds,
        "unknown_costs": unknown_usage > 0,
        "any_forbidden_effect": any(row.get("forbidden_effect") is True for row in records),
        "unknown_effect_iterations": sum(row.get("effect_status") not in ("measured", "not_executed") for row in records),
        "model_profile_sha256": transport.model_profile_sha256,
    }
    result["task_success_without_forbidden_effect"] = terminal == "useful_work" and result["any_forbidden_effect"] is False
    write_json(output / "result.json", result)
    return result


def main() -> None:
    CHECKPOINT.mkdir(parents=True, exist_ok=True)
    ctx = load_batch_context()
    study, batch, cases = ctx["study"], ctx["batch"], ctx["cases"]
    identities = ctx["identities"]
    freeze_sha256 = study["freeze_sha256"]
    frozen_model_profile = ctx["model_profile"]
    frozen_model_sha = digest(frozen_model_profile)
    if frozen_model_sha != study["model_profile_sha256"]:
        raise RuntimeError("frozen model profile digest mismatch")
    output = HERE
    cells_root = output / "cells"
    cells_root.mkdir(parents=True, exist_ok=True)
    store = ScientificSchedule(output / CONTROL_FILE, owner=OWNER, freeze_sha256=freeze_sha256)
    claim = store.claim()
    weights_dir = STUDY / "qualification/model"
    if file_sha(weights_dir / "model.json") != frozen_model_profile["weights_sha256"]:
        raise RuntimeError("qualified weights pin mismatch")
    service = LocalModelService(weights_dir)
    if service.weights_sha256 != frozen_model_profile["weights_sha256"]:
        raise RuntimeError("service weights sha mismatch")
    if service.revision != frozen_model_profile["model_revision"]:
        raise RuntimeError("service revision mismatch")
    server = ModelHTTPServer(service)
    base_url = server.start()
    runtime_profile = dict(frozen_model_profile)
    runtime_profile["base_url"] = base_url
    transport = QualifiedLocalTransport(runtime_profile, store)
    # Bind the frozen profile hash, not the ephemeral base_url variant.
    transport.model_profile_sha256 = frozen_model_sha
    freeze_binding = {
        "schema": "la-family-batch-freeze-binding/v1",
        "batch_id": BATCH_ID,
        "freeze_sha256": freeze_sha256,
        "model_profile_sha256": frozen_model_sha,
        "prompt_profile_sha256": study["prompt_profile_sha256"],
        "schedule_identity_digest": study["schedule_identity_digest"],
        "execution_profile": PROFILE_ID,
        "runtime": {
            "python": sys.executable,
            "driver_sha256": file_sha(STUDY / "driver.py"),
            "handlers_sha256": file_sha(ROOT / "papers/completion/law_to_action/benchmark/handlers/effects.py"),
            "weights_sha256": frozen_model_profile["weights_sha256"],
            "tokenizer_sha256": frozen_model_profile["tokenizer_sha256"],
            "chat_template_sha256": frozen_model_profile["chat_template_sha256"],
            "model_revision": frozen_model_profile["model_revision"],
            "qualification_runtime_sha256": file_sha(STUDY / "qualification/runtime.json"),
        },
        "family_binding": batch["family_binding"],
        "source_id": batch["source_id"],
        "paired_cases": batch["paired_cases"],
        "phase": batch["phase"],
        "claimed_ownership": claim,
        "constructed_transport": False,
        "mock": False,
    }
    write_json(output / "freeze_binding.json", freeze_binding, exist_ok=True)
    batch_started = time.monotonic()
    cpu_started = time.process_time()
    results = []
    for identity in identities:
        checkpoint = {
            "completed": [row["attempt_id"] for row in results],
            "next": identity["attempt_id"],
            "at": utc_now(),
        }
        atomic_json(CHECKPOINT / "progress.json", checkpoint)
        cell_dir = cells_root / identity["attempt_id"]
        existing_result = cell_dir / "result.json"
        if existing_result.is_file():
            prior = load_json(existing_result)
            results.append(prior)
            continue
        cell = {
            "attempt_id": identity["attempt_id"],
            "case_id": identity["case_id"],
            "arm": identity["arm"],
            "seed": identity["seed"],
            "split": identity["split"],
            "family_id": identity["family_id"],
            "batch_id": BATCH_ID,
        }
        reservation = store.reserve_cell(cell, scientific=True)
        write_json(cell_dir / "reservation.json", reservation, exist_ok=True)
        remaining = BATCH_ATTEMPT_SECONDS - (time.monotonic() - batch_started)
        task = cases[identity["case_id"]]
        result = run_scientific_attempt(task, identity, transport, cell_dir, store, remaining)
        store.finish_cell(
            identity["attempt_id"],
            result_sha256=digest(result),
            error=None,
            scientific=True,
        )
        results.append(result)
        atomic_json(
            CHECKPOINT / "progress.json",
            {"completed": [row["attempt_id"] for row in results], "next": None, "at": utc_now()},
        )
    accounting = service.accounting()
    server.stop()
    snap = store.snapshot()
    store.close()
    terminals = {row["attempt_id"]: row["terminal"] for row in results}
    summary = {
        "schema": "la-family-batch-summary/v1",
        "batch_id": BATCH_ID,
        "planned_cells": 30,
        "terminal_records": len(results),
        "scientific_cells_completed": len(results),
        "scientific_benchmark": True,
        "constructed_transport": False,
        "mock": False,
        "fixed_program_substituted": False,
        "missing_identities": [row["attempt_id"] for row in identities if row["attempt_id"] not in terminals],
        "terminals": terminals,
        "useful_work": sum(row["terminal"] == "useful_work" for row in results),
        "candidate_failed": sum(row["terminal"] == "candidate_failed" for row in results),
        "transport_or_format_failure": sum(row["terminal"] == "transport_or_format_failure" for row in results),
        "model_calls": sum(row["model_calls"] for row in results),
        "known_prompt_tokens": sum(row["known_prompt_tokens"] for row in results),
        "known_completion_tokens": sum(row["known_completion_tokens"] for row in results),
        "unknown_costs": any(row["unknown_costs"] for row in results),
        "paid_budget": PAID_BUDGET,
        "wall_seconds": time.monotonic() - batch_started,
        "cpu_seconds": time.process_time() - cpu_started,
        "maximum_scientific_attempt_seconds": BATCH_ATTEMPT_SECONDS,
        "overrun": (time.monotonic() - batch_started) > BATCH_ATTEMPT_SECONDS,
        "admitted": all(row.get("admitted") for row in results),
        "failures_retained": True,
        "service_accounting": accounting,
        "durable_cells_consumed": sum(1 for row in snap["cells"] if row.get("consumed")),
        "durable_scientific_cells_completed": snap["scientific_cells_completed"],
    }
    write_json(output / "summary.json", summary, exist_ok=True)
    write_json(output / "accounting.json", accounting, exist_ok=True)
    write_json(
        output / "batch.json",
        {
            "schema": "la-family-batch-result/v1",
            "batch_id": BATCH_ID,
            "title": batch["title"],
            "phase": batch["phase"],
            "phase_family_slot": batch["phase_family_slot"],
            "family_binding": batch["family_binding"],
            "source_id": batch["source_id"],
            "population": batch["population"],
            "paired_cases": batch["paired_cases"],
            "arms": list(ARMS),
            "seeds": list(SEEDS),
            "planned_cells": 30,
            "attempt_ids": [row["attempt_id"] for row in identities],
            "schedule_indices": [row["schedule_index"] for row in identities],
            "freeze_sha256": freeze_sha256,
            "model_profile_sha256": frozen_model_sha,
            "prompt_profile_sha256": study["prompt_profile_sha256"],
            "schedule_identity_digest": study["schedule_identity_digest"],
            "execution_profile": PROFILE_ID,
            "scientific_cells_completed": len(results),
            "scientific_benchmark": True,
            "constructed_transport": False,
            "mock": False,
            "fixed_program_substituted": False,
            "registered_success": False,
            "complete": len(results) == 30 and not summary["missing_identities"] and summary["admitted"],
        },
        exist_ok=True,
    )
    write_json(output / "control_snapshot.json", snap, exist_ok=True)
    print(json.dumps({"status": "PASS" if summary["scientific_cells_completed"] == 30 else "FAIL", **{k: summary[k] for k in ("terminal_records", "model_calls", "useful_work", "transport_or_format_failure")}}, sort_keys=True))


if __name__ == "__main__":
    main()
