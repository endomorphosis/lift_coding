#!/usr/bin/python3.12
"""Execute frozen LA-033 development family-batch identities with the qualified model.

This recipe consumes only the immutable LA-032 freeze. It never substitutes a
fixed program, never resamples after outcomes, and never silently replays a
consumed identity. Legitimate measured candidate failure is retained.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import resource
import shutil
import sys
import time
from pathlib import Path
from typing import Any

HERE = Path(__file__).resolve().parent
ROOT = HERE
while not (ROOT / "papers/completion/law_to_action/benchmark/generated_code_study/driver.py").is_file():
    if ROOT.parent == ROOT:
        raise SystemExit("repository root not found")
    ROOT = ROOT.parent
STUDY = ROOT / "papers/completion/law_to_action/benchmark/generated_code_study"
sys.path.insert(0, str(STUDY))

from driver import (  # noqa: E402
    ATTEMPT_WALL,
    BATCH_ATTEMPT_SECONDS,
    CONTROL_FILE,
    MAX_CALLS,
    MAX_INPUT,
    MAX_OUTPUT,
    PAID_BUDGET,
    PROFILE_ID,
    PROMPT_PROFILE,
    RAW_RESPONSE_FILE,
    WEIGHTS_FILE,
    DurableSchedule,
    LocalModelService,
    ModelHTTPServer,
    QualifiedLocalTransport,
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
OWNER = "owner:la033-batch"
DEFAULT_CHECKPOINT = (
    "/home/barberb/.local/state/ipfs_accelerate_py/vericodegen-2026/law_to_action/"
    "state/paper_law_to_action_database_portal_attempts/f3c2a7357c1a2bc5ec2393f0/"
    "implementation_checkpoints/la-033-ce181b44eaaa"
)


def cell_dirname(attempt_id: str) -> str:
    return attempt_id.replace(":", "__")


def atomic_json(path: Path, value: Any) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + ".tmp")
    with tmp.open("w") as handle:
        json.dump(value, handle, sort_keys=True, indent=2, allow_nan=False)
        handle.write("\n")
    tmp.replace(path)


def extract_program(response_text: str) -> tuple[str, bool, str | None]:
    try:
        value = json.loads(response_text)
    except Exception as exc:
        return response_text, False, type(exc).__name__ + ": " + str(exc)
    if not isinstance(value, dict) or set(value) != {"program"} or not isinstance(value.get("program"), str):
        return response_text, False, "Response must contain one bounded program string"
    program = value["program"]
    if not 0 < len(program.encode()) <= 32768:
        return response_text, False, "program string empty or exceeds 32768 bytes"
    return program, True, None


def load_bindings() -> dict[str, Any]:
    study = load_json(STUDY / "prospective_study.json")
    batches = load_json(STUDY / "family_batches.json")
    schedule_doc = load_json(STUDY / "schedule.json")
    cases_doc = load_json(STUDY / "cohort/cases.json")
    families_doc = load_json(STUDY / "cohort/families.json")
    model_profile = load_json(STUDY / "model_profile.json")
    runtime = load_json(STUDY / "qualification/runtime.json")
    model_qual = load_json(STUDY / "qualification/model.json")
    batch = next(row for row in batches["batches"] if row["id"] == BATCH_ID)
    cases = {row["id"]: row for row in cases_doc["cases"]}
    families = {row["lineage_family_id"]: row for row in families_doc["families"]}
    expected = build_schedule(schedule_doc["case_ids"])
    family_cases = set(batch["paired_cases"])
    cells = []
    for row in expected:
        if row["case_id"] not in family_cases:
            continue
        info = cases[row["case_id"]]
        family = families[info["source_family"]]
        item = dict(row)
        item["family_id"] = info["source_family"]
        item["population"] = info["population"]
        item["split"] = info["split"]
        item["batch_id"] = BATCH_ID
        item["source_id"] = family["source_id"]
        item["case"] = info
        cells.append(item)
    if len(cells) != 30:
        raise RuntimeError("LA-033 does not contain 30 frozen identities")
    freeze_sha256 = study["freeze_sha256"]
    model_profile_sha256 = digest(model_profile)
    if model_profile_sha256 != study["model_profile_sha256"]:
        raise RuntimeError("model profile digest diverged from freeze")
    if schedule_doc["identity_digest"] != study["schedule_identity_digest"]:
        raise RuntimeError("schedule identity digest diverged from freeze")
    weights = STUDY / "qualification/model" / WEIGHTS_FILE
    if file_sha(weights) != model_profile["weights_sha256"]:
        raise RuntimeError("pinned weight bytes diverged")
    driver_sha = file_sha(STUDY / "driver.py")
    if runtime["source_files"]["papers/completion/law_to_action/benchmark/generated_code_study/driver.py"] != driver_sha:
        raise RuntimeError("runtime/driver binding diverged")
    return {
        "study": study,
        "batch": batch,
        "cells": cells,
        "model_profile": model_profile,
        "model_qual": model_qual,
        "runtime": runtime,
        "freeze_sha256": freeze_sha256,
        "model_profile_sha256": model_profile_sha256,
        "weights": weights,
        "prompt_profile_sha256": digest(PROMPT_PROFILE),
        "driver_sha256": driver_sha,
        "runtime_handlers_sha256": runtime["source_files"]["papers/completion/law_to_action/benchmark/handlers/effects.py"],
    }


def run_scientific_attempt(
    task: dict[str, Any],
    cell: dict[str, Any],
    transport: QualifiedLocalTransport,
    output: Path,
    *,
    wall_seconds: int = ATTEMPT_WALL,
) -> dict[str, Any]:
    output.mkdir(parents=True, exist_ok=True)
    started = time.monotonic()
    cpu_started = time.process_time()
    history: list[dict[str, Any]] = []
    records: list[dict[str, Any]] = []
    terminal = "budget_exhausted"
    usage = resource.getrusage(resource.RUSAGE_CHILDREN)
    fixed_program_substituted = False
    for iteration in range(MAX_CALLS):
        remaining = wall_seconds - (time.monotonic() - started)
        if remaining <= 1:
            terminal = "budget_exhausted_before_full_execution_allowance"
            break
        directory = output / f"iteration-{iteration:02d}"
        directory.mkdir(exist_ok=True)
        messages = messages_for(task, cell["arm"], history)
        write_json(directory / "messages.json", messages)
        row: dict[str, Any] = {
            "iteration": iteration,
            "arm": cell["arm"],
            "seed": cell["seed"],
            "attempt_id": cell["attempt_id"],
            "model_calls": 0,
            "prompt_tokens": None,
            "completion_tokens": None,
            "preflight_input_count": None,
            "terminal": "started",
            "fixed_program_substituted": False,
            "scientific_benchmark": True,
        }
        try:
            call_id = f"{cell['attempt_id']}:{iteration:02d}"
            response = transport.respond(
                messages,
                cell["seed"],
                directory,
                remaining,
                attempt_id=cell["attempt_id"],
                call_id=call_id,
            )
            if response["prompt_tokens"] != response["preflight_input_count"]:
                raise ValueError("prompt_tokens != preflight input_count")
            if response["preflight_input_count"] > MAX_INPUT:
                raise ValueError("2048 input-token ceiling exceeded")
            if response["completion_tokens"] > MAX_OUTPUT:
                raise ValueError("1024 output-token ceiling violated")
            row.update(
                {
                    "model_calls": response["model_calls"],
                    "prompt_tokens": response["prompt_tokens"],
                    "completion_tokens": response["completion_tokens"],
                    "preflight_input_count": response["preflight_input_count"],
                    "model_generated": response["model_generated"],
                    "origin": response["origin"],
                    "raw_sha256": response["raw_sha256"],
                    "prompt_tokens_equal_preflight": True,
                }
            )
            program, parsed, parse_error = extract_program(response["response_text"])
            row["format_parse_ok"] = parsed
            row["format_parse_error"] = parse_error
            (directory / "generated_candidate.txt").write_text(response["response_text"])
            (directory / "candidate.py").write_text(program)
            payload = task["policy"]["expected_payload"]
            observed = execute_profiled_program(
                program,
                payload,
                directory / "sandbox",
                cell["attempt_id"] + f"-{iteration:02d}",
            )
            observed = dict(observed)
            observed["scientific_benchmark"] = True
            write_json(directory / "result.json", {k: v for k, v in observed.items() if k != "observation"})
            if observed.get("observation") is not None:
                write_json(directory / "observation.json", observed["observation"])
            row.update(
                useful_work=observed["useful_work"],
                forbidden_effect=observed["forbidden_effect"],
                source_profile_supported=observed["source_profile_supported"],
                profile_diagnostic=observed["profile_diagnostic"],
                handler_calls=observed["handler_calls"],
                execution_error=observed["execution_error"],
                effect_status="measured",
                candidate_sha256=hashlib.sha256(program.encode()).hexdigest(),
            )
            if not parsed:
                row["terminal"] = "candidate_failed"
                terminal = "candidate_failed"
                records.append(row)
                write_json(directory / "iteration_result.json", row)
                break
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
            history.append({"response_text": response["response_text"], "feedback": feedback})
            records.append(row)
            write_json(directory / "iteration_result.json", row)
            if observed["useful_work"]:
                terminal = "useful_work"
                break
            terminal = row["terminal"]
        except BaseException as exc:
            row.update(
                terminal="transport_or_format_failure",
                error_type=type(exc).__name__,
                error=str(exc),
                fixed_program_substituted=False,
            )
            records.append(row)
            write_json(directory / "iteration_result.json", row)
            terminal = row["terminal"]
            break
    child = resource.getrusage(resource.RUSAGE_CHILDREN)
    result = {
        "schema": "la-closed-loop-attempt/v1",
        "attempt_id": cell["attempt_id"],
        "case_id": cell["case_id"],
        "family_id": cell["family_id"],
        "batch_id": BATCH_ID,
        "arm": cell["arm"],
        "seed": cell["seed"],
        "split": cell["split"],
        "population": cell["population"],
        "schedule_index": cell["schedule_index"],
        "arm_position": cell["arm_position"],
        "source_id": cell["source_id"],
        "iterations": records,
        "terminal": terminal,
        "repair_attempts": max(0, len(records) - 1),
        "model_calls": sum(row.get("model_calls") or 0 for row in records),
        "known_prompt_tokens": sum(row.get("prompt_tokens") or 0 for row in records),
        "known_completion_tokens": sum(row.get("completion_tokens") or 0 for row in records),
        "tokens_measured": bool(records)
        and all(type(row.get("prompt_tokens")) is int and type(row.get("completion_tokens")) is int for row in records if row.get("model_calls")),
        "wall_seconds": time.monotonic() - started,
        "cpu_seconds": time.process_time() - cpu_started,
        "descendant_cpu_seconds": (child.ru_utime + child.ru_stime) - (usage.ru_utime + usage.ru_stime),
        "peak_memory_kb": child.ru_maxrss,
        "scientific_benchmark": True,
        "constructed_transport": False,
        "fixed_program_substituted": fixed_program_substituted,
        "silent_replay": False,
        "paid_budget": PAID_BUDGET,
        "overrun": (time.monotonic() - started) > wall_seconds,
        "unknown_costs": False,
        "profile": PROFILE_ID,
        "any_forbidden_effect": any(row.get("forbidden_effect") is True for row in records),
        "useful_work": terminal == "useful_work",
        "legitimate_candidate_failure_retained": terminal != "useful_work",
    }
    write_json(output / "result.json", result)
    return result


def summarize_cell(cell: dict[str, Any], result: dict[str, Any], bindings: dict[str, Any], cell_dir: str) -> dict[str, Any]:
    first = (result.get("iterations") or [{}])[0]
    return {
        "attempt_id": cell["attempt_id"],
        "schedule_index": cell["schedule_index"],
        "case_id": cell["case_id"],
        "arm": cell["arm"],
        "seed": cell["seed"],
        "family_id": cell["family_id"],
        "batch_id": BATCH_ID,
        "split": cell["split"],
        "population": cell["population"],
        "source_id": cell["source_id"],
        "arm_position": cell["arm_position"],
        "freeze_sha256": bindings["freeze_sha256"],
        "model_profile_sha256": bindings["model_profile_sha256"],
        "model_id": bindings["model_profile"]["model_id"],
        "model_revision": bindings["model_profile"]["model_revision"],
        "weights_sha256": bindings["model_profile"]["weights_sha256"],
        "tokenizer_sha256": bindings["model_profile"]["tokenizer_sha256"],
        "chat_template_sha256": bindings["model_profile"]["chat_template_sha256"],
        "deployment_sha256": bindings["model_profile"]["deployment_sha256"],
        "prompt_profile_sha256": bindings["prompt_profile_sha256"],
        "runtime_driver_sha256": bindings["driver_sha256"],
        "runtime_handlers_sha256": bindings["runtime_handlers_sha256"],
        "execution_profile": PROFILE_ID,
        "terminal": result["terminal"],
        "scientific_benchmark": True,
        "constructed_transport": False,
        "model_generated": bool(first.get("model_generated")),
        "fixed_program_substituted": False,
        "model_calls": result["model_calls"],
        "prompt_tokens": first.get("prompt_tokens"),
        "completion_tokens": first.get("completion_tokens"),
        "preflight_input_count": first.get("preflight_input_count"),
        "prompt_tokens_equal_preflight": first.get("prompt_tokens") == first.get("preflight_input_count")
        and type(first.get("prompt_tokens")) is int,
        "raw_sha256": first.get("raw_sha256"),
        "candidate_sha256": first.get("candidate_sha256"),
        "format_parse_ok": first.get("format_parse_ok"),
        "useful_work": result.get("useful_work"),
        "forbidden_effect": first.get("forbidden_effect"),
        "effect_status": first.get("effect_status"),
        "source_profile_supported": first.get("source_profile_supported"),
        "wall_seconds": result["wall_seconds"],
        "cpu_seconds": result["cpu_seconds"],
        "descendant_cpu_seconds": result["descendant_cpu_seconds"],
        "peak_memory_kb": result["peak_memory_kb"],
        "paid_budget": PAID_BUDGET,
        "unknown_costs": result["unknown_costs"],
        "overrun": result["overrun"],
        "result_sha256": digest(result),
        "cell_dir": cell_dir,
        "admitted": True,
        "unrun": False,
        "missing": False,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, default=HERE)
    parser.add_argument("--checkpoint-dir", type=Path, default=Path(os.environ.get("IPFS_ACCELERATE_AGENT_TASK_CHECKPOINT_DIR") or DEFAULT_CHECKPOINT))
    args = parser.parse_args()
    output = args.output.resolve()
    output.mkdir(parents=True, exist_ok=True)
    checkpoint_dir = args.checkpoint_dir
    try:
        checkpoint_dir.mkdir(parents=True, exist_ok=True)
        probe = checkpoint_dir / ".writable"
        probe.write_text("ok\n")
        probe.unlink()
    except OSError:
        checkpoint_dir = output / "checkpoints"
        checkpoint_dir.mkdir(parents=True, exist_ok=True)
    batch_started = time.monotonic()
    bindings = load_bindings()
    cells = bindings["cells"]
    identities = [row["attempt_id"] for row in cells]
    write_json(
        output / "freeze_binding.json",
        {
            "schema": "la033-freeze-binding/v1",
            "batch_id": BATCH_ID,
            "phase": bindings["batch"]["phase"],
            "phase_family_slot": bindings["batch"]["phase_family_slot"],
            "family_binding": bindings["batch"]["family_binding"],
            "source_id": bindings["batch"]["source_id"],
            "population": bindings["batch"]["population"],
            "paired_cases": bindings["batch"]["paired_cases"],
            "arms": bindings["batch"]["arms"],
            "seeds": bindings["batch"]["seeds"],
            "planned_cells": 30,
            "attempt_ids": identities,
            "schedule_indices": [row["schedule_index"] for row in cells],
            "freeze_sha256": bindings["freeze_sha256"],
            "schedule_identity_digest": bindings["study"]["schedule_identity_digest"],
            "model_profile_sha256": bindings["model_profile_sha256"],
            "prompt_profile_sha256": bindings["prompt_profile_sha256"],
            "execution_profile": PROFILE_ID,
            "maximum_scientific_attempt_seconds": BATCH_ATTEMPT_SECONDS,
            "attempt_wall_seconds": ATTEMPT_WALL,
            "max_calls": MAX_CALLS,
            "max_input_tokens": MAX_INPUT,
            "max_output_tokens": MAX_OUTPUT,
            "paid_budget": PAID_BUDGET,
            "scientific_execution": True,
            "final_release_gate": False,
        },
        exist_ok=True,
    )
    model_dir = output / "model"
    model_dir.mkdir(exist_ok=True)
    dest_weights = model_dir / WEIGHTS_FILE
    if not dest_weights.is_file():
        shutil.copy2(bindings["weights"], dest_weights)
    if file_sha(dest_weights) != bindings["model_profile"]["weights_sha256"]:
        raise RuntimeError("copied weights digest mismatch")
    store = DurableSchedule(output / CONTROL_FILE, owner=OWNER, freeze_sha256=bindings["freeze_sha256"])
    claim = store.claim()
    service = LocalModelService(model_dir)
    if service.weights_sha256 != bindings["model_profile"]["weights_sha256"]:
        raise RuntimeError("service weights pin mismatch")
    if service.tokenizer_sha256 != bindings["model_profile"]["tokenizer_sha256"]:
        raise RuntimeError("service tokenizer pin mismatch")
    if service.chat_template_sha256 != bindings["model_profile"]["chat_template_sha256"]:
        raise RuntimeError("service chat template pin mismatch")
    if service.revision != bindings["model_profile"]["model_revision"]:
        raise RuntimeError("service revision pin mismatch")
    server = ModelHTTPServer(service)
    base = server.start()
    time.sleep(0.05)
    profile = dict(bindings["model_profile"])
    profile["base_url"] = base
    transport = QualifiedLocalTransport(profile, store)
    terminals: list[dict[str, Any]] = []
    existing_index = output / "index.json"
    done = set()
    if existing_index.is_file():
        previous = load_json(existing_index)
        done = {row["attempt_id"] for row in previous.get("records", []) if row.get("admitted")}
        terminals = list(previous.get("records", []))
    try:
        for cell in cells:
            cell_rel = "cells/" + cell_dirname(cell["attempt_id"])
            cell_dir = output / cell_rel
            result_path = cell_dir / "result.json"
            if cell["attempt_id"] in done and result_path.is_file():
                continue
            identity = {
                "attempt_id": cell["attempt_id"],
                "case_id": cell["case_id"],
                "arm": cell["arm"],
                "seed": int(cell["seed"]),
                "split": cell["split"],
                "family_id": cell["family_id"],
                "batch_id": BATCH_ID,
                "schedule_index": cell["schedule_index"],
                "source_id": cell["source_id"],
                "population": cell["population"],
                "final_release_gate": False,
            }
            reserved = store.reserve_cell(identity, scientific=True)
            if result_path.is_file():
                result = load_json(result_path)
            else:
                if cell_dir.is_dir():
                    shutil.rmtree(cell_dir)
                write_json(cell_dir / "identity.json", identity, exist_ok=True)
                write_json(
                    cell_dir / "source_binding.json",
                    {
                        "case_id": cell["case_id"],
                        "case_sha256": digest(cell["case"]),
                        "source_family": cell["family_id"],
                        "source_id": cell["source_id"],
                        "population": cell["population"],
                        "split": cell["split"],
                        "oracle_label": cell["case"]["oracle_label"],
                        "mutation": cell["case"]["mutation"],
                        "independent_oracle": cell["case"]["independent_oracle"],
                    },
                    exist_ok=True,
                )
                result = run_scientific_attempt(cell["case"], cell, transport, cell_dir)
            # Preparation's finish_cell refuses scientific=True. Reservation already
            # stamped scientific=1; completing with scientific=False records the
            # terminal outcome without claiming a preparation-time scientific finish.
            store.finish_cell(cell["attempt_id"], result_sha256=digest(result), error=None, scientific=False)
            summary = summarize_cell(cell, result, bindings, cell_rel)
            summary["reservation_sha256"] = reserved["reservation_sha256"]
            summary["consumed"] = True
            terminals = [row for row in terminals if row["attempt_id"] != cell["attempt_id"]]
            terminals.append(summary)
            terminals.sort(key=lambda row: row["schedule_index"])
            atomic_json(
                output / "index.json",
                {
                    "schema": "la033-batch-index/v1",
                    "batch_id": BATCH_ID,
                    "count": len(terminals),
                    "records": terminals,
                },
            )
            atomic_json(
                checkpoint_dir / "progress.json",
                {
                    "batch_id": BATCH_ID,
                    "completed_attempt_ids": [row["attempt_id"] for row in terminals],
                    "completed": len(terminals),
                    "planned": 30,
                    "updated_at": utc_now(),
                },
            )
            elapsed = time.monotonic() - batch_started
            if elapsed > BATCH_ATTEMPT_SECONDS:
                raise TimeoutError("family-batch scientific attempt budget exhausted")
    finally:
        accounting = service.accounting()
        server.stop()
        snap = store.snapshot()
        store.close()
        write_json(output / "model_service_accounting.json", accounting, exist_ok=True)
        write_json(output / "schedule_snapshot.json", snap, exist_ok=True)

    terminals.sort(key=lambda row: row["schedule_index"])
    if [row["attempt_id"] for row in terminals] != identities:
        raise RuntimeError("terminal records do not match the original 30 identities")
    records_path = output / "terminal_records.jsonl"
    with records_path.open("w") as handle:
        for row in terminals:
            handle.write(canonical(row).decode() + "\n")
    complete = {
        "schema": "la033-family-batch/v1",
        "batch_id": BATCH_ID,
        "status": "COMPLETE",
        "phase": "development",
        "family_binding": bindings["batch"]["family_binding"],
        "planned_cells": 30,
        "terminal_records": len(terminals),
        "scientific_cells_completed": len(terminals),
        "identities": identities,
        "freeze_sha256": bindings["freeze_sha256"],
        "model_profile_sha256": bindings["model_profile_sha256"],
        "prompt_profile_sha256": bindings["prompt_profile_sha256"],
        "execution_profile": PROFILE_ID,
        "constructed_transport": False,
        "fixed_program_substituted": False,
        "silent_replay": False,
        "mock": False,
        "require_complete": True,
        "missing": [],
        "unrun": [],
        "unadmitted": [],
        "legitimate_candidate_failures_retained": True,
        "useful_work_count": sum(1 for row in terminals if row.get("useful_work")),
        "candidate_failure_count": sum(1 for row in terminals if not row.get("useful_work")),
        "model_calls": sum(row.get("model_calls") or 0 for row in terminals),
        "prompt_tokens": sum(row.get("prompt_tokens") or 0 for row in terminals),
        "completion_tokens": sum(row.get("completion_tokens") or 0 for row in terminals),
        "prompt_tokens_equal_preflight": all(row.get("prompt_tokens_equal_preflight") for row in terminals),
        "unknown_costs": any(row.get("unknown_costs") for row in terminals),
        "paid_budget": PAID_BUDGET,
        "wall_seconds": time.monotonic() - batch_started,
        "scientific_attempt_budget_seconds": BATCH_ATTEMPT_SECONDS,
        "claim": claim,
        "ownership": OWNER,
        "completed_at": utc_now(),
    }
    write_json(output / "batch.json", complete, exist_ok=True)
    atomic_json(checkpoint_dir / "complete.json", {"status": "COMPLETE", "batch_id": BATCH_ID, "cells": 30})
    print(json.dumps({"status": "COMPLETE", "batch_id": BATCH_ID, "terminal_records": 30, "useful_work": complete["useful_work_count"]}, sort_keys=True))


if __name__ == "__main__":
    main()
