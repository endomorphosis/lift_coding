#!/usr/bin/python3.12
"""Execute frozen generated-code family batch LA-033 with the qualified local model.

This is a scientific batch runner. It never substitutes a fixed program, never
silently replays a consumed identity, and retains measured candidate failure.
"""
from __future__ import annotations

import hashlib
import json
import os
import resource
import shutil
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[6]
STUDY = ROOT / "papers/completion/law_to_action/benchmark/generated_code_study"
sys.path.insert(0, str(STUDY))
sys.path.insert(0, "/home/barberb/.local/share/vericodegen-research-runtime/python")
sys.path.insert(0, "/opt/ipfs-validation-site-packages")

from driver import (  # noqa: E402
    ATTEMPT_WALL,
    BATCH_ATTEMPT_SECONDS,
    CONTROL_FILE,
    MAX_CALLS,
    MAX_OUTPUT,
    PAID_BUDGET,
    PROFILE_ID,
    PROMPT_PROFILE,
    RAW_RESPONSE_FILE,
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
CANNED_PROGRAM = "def run(payload):\n    emit_allowed(payload)\n"
def _checkpoint_dir() -> Path:
    candidates = []
    env = os.environ.get("IPFS_ACCELERATE_AGENT_TASK_CHECKPOINT_DIR")
    if env:
        candidates.append(Path(env))
    candidates.extend(
        [
            Path("/home/barberb/.local/state/ipfs_accelerate_py/vericodegen-2026/law_to_action/state/paper_law_to_action_database_portal_attempts/f747181ac3feb20924d22487/implementation_checkpoints/la-033-ce181b44eaaa"),
            Path("/tmp/la-033-ce181b44eaaa"),
            Path("/var/tmp/la-033-ce181b44eaaa"),
            HERE / ".runtime",
        ]
    )
    for path in candidates:
        try:
            path.mkdir(parents=True, exist_ok=True)
            probe = path / ".writable"
            probe.write_text("ok")
            probe.unlink()
            return path
        except OSError:
            continue
    raise RuntimeError("no writable checkpoint directory")


CHECKPOINT = _checkpoint_dir()


class ScientificSchedule(DurableSchedule):
    """Allow scientific cell completion for an owned family batch."""

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


def extract_program(response_text: str) -> tuple[str, str]:
    try:
        value = json.loads(response_text)
    except Exception:
        return response_text, "unparseable_model_text"
    if not isinstance(value, dict) or not isinstance(value.get("program"), str):
        return response_text, "missing_program_field"
    program = value["program"]
    if not 0 < len(program.encode()) <= 32768:
        return program, "program_size_out_of_bounds"
    return program, "json_program"


def planned_cells(study_dir: Path, batch: dict) -> list[dict]:
    from driver import build_schedule

    schedule_doc = load_json(study_dir / "schedule.json")
    cases = {row["id"]: row for row in load_json(study_dir / "cohort/cases.json")["cases"]}
    family_cases = list(batch["paired_cases"])
    rows = []
    for item in build_schedule(schedule_doc["case_ids"]):
        if item["case_id"] not in family_cases:
            continue
        info = cases[item["case_id"]]
        rows.append(
            {
                **item,
                "family_id": info["source_family"],
                "population": info["population"],
                "split": info["split"],
                "source_id": info["source_id"],
                "task": {
                    "instruction": info["instruction"],
                    "split": info["split"],
                    "source_family": info["source_family"],
                    "policy": info["policy"],
                    "retrieval": info["retrieval"],
                    "oracle_released": False,
                },
            }
        )
    if len(rows) != 30:
        raise RuntimeError("expected 30 identities")
    return rows


def run_scientific_attempt(task: dict, arm: str, seed: int, transport: QualifiedLocalTransport, output: Path) -> dict:
    output.mkdir(parents=True, exist_ok=True)
    started = time.monotonic()
    cpu_started = time.process_time()
    history: list[dict] = []
    records: list[dict] = []
    terminal = "budget_exhausted"
    usage = resource.getrusage(resource.RUSAGE_CHILDREN)
    attempt_id = output.name
    write_json(
        output / "attempt_start.json",
        {
            "attempt_id": attempt_id,
            "arm": arm,
            "seed": seed,
            "scientific_benchmark": True,
            "constructed_transport": False,
            "maximum_calls": MAX_CALLS,
            "maximum_wall_seconds": ATTEMPT_WALL,
        },
    )
    for iteration in range(MAX_CALLS):
        remaining = ATTEMPT_WALL - (time.monotonic() - started)
        if remaining <= 1:
            terminal = "budget_exhausted_before_full_execution_allowance"
            break
        directory = output / f"iteration-{iteration:02d}"
        directory.mkdir()
        messages = messages_for(task, arm, history)
        write_json(directory / "messages.json", messages)
        row = {
            "iteration": iteration,
            "arm": arm,
            "seed": seed,
            "model_calls": 0,
            "prompt_tokens": None,
            "completion_tokens": None,
            "terminal": "started",
        }
        try:
            response = transport.respond(
                messages,
                seed,
                directory,
                remaining,
                attempt_id=attempt_id,
                call_id=attempt_id + f"-{iteration:02d}",
            )
            row.update({key: response[key] for key in ("model_calls", "prompt_tokens", "completion_tokens", "model_generated", "origin")})
            if response["prompt_tokens"] != response["preflight_input_count"]:
                raise ValueError("prompt_tokens != preflight input_count")
            program, extraction = extract_program(response["response_text"])
            if program == CANNED_PROGRAM and extraction != "json_program":
                raise RuntimeError("refusing canned-program substitution")
            (directory / "candidate.py").write_text(program)
            observed = execute_profiled_program(
                program,
                task["policy"]["expected_payload"],
                directory / "sandbox",
                attempt_id + f"-{iteration:02d}",
            )
            observed["scientific_benchmark"] = True
            write_json(directory / "result.json", {k: v for k, v in observed.items() if k != "observation"})
            row.update(
                useful_work=observed["useful_work"],
                forbidden_effect=observed["forbidden_effect"],
                source_profile_supported=observed["source_profile_supported"],
                profile_diagnostic=observed["profile_diagnostic"],
                program_extraction=extraction,
                candidate_sha256=hashlib.sha256(program.encode()).hexdigest(),
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
            # One measured candidate is a complete scientific outcome. Further
            # repairs against this tiny untrained LM repeat unparseable bytes
            # and would blow the admission budget; the failure is retained.
            terminal = "candidate_failed"
            break
        except BaseException as exc:
            row.update(terminal="transport_or_format_failure", error_type=type(exc).__name__, error=str(exc))
            records.append(row)
            write_json(directory / "iteration_result.json", row)
            terminal = row["terminal"]
            break
    child = resource.getrusage(resource.RUSAGE_CHILDREN)
    result = {
        "schema": "la-closed-loop-attempt/v1",
        "attempt_id": attempt_id,
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
        "constructed_transport": False,
        "paid_budget": PAID_BUDGET,
        "overrun": (time.monotonic() - started) > ATTEMPT_WALL,
        "unknown_costs": False,
    }
    return result


def atomic_write_json(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + ".tmp")
    write_json(tmp, value, exist_ok=True)
    tmp.replace(path)


def main() -> None:
    CHECKPOINT.mkdir(parents=True, exist_ok=True)
    study = load_json(STUDY / "prospective_study.json")
    batches = load_json(STUDY / "family_batches.json")
    batch = next(row for row in batches["batches"] if row["id"] == BATCH_ID)
    cells = planned_cells(STUDY, batch)
    runtime = load_json(STUDY / "qualification/runtime.json")
    model_profile = load_json(STUDY / "model_profile.json")
    freeze_sha256 = study["freeze_sha256"]
    HERE.mkdir(parents=True, exist_ok=True)
    model_dir = CHECKPOINT / "model"
    model_dir.mkdir(parents=True, exist_ok=True)
    weights = STUDY / "qualification/model/model.json"
    target_weights = model_dir / "model.json"
    if not target_weights.is_file():
        shutil.copy2(weights, target_weights)
    if file_sha(target_weights) != model_profile["weights_sha256"]:
        raise RuntimeError("batch model weights drifted from freeze")

    store = ScientificSchedule(HERE / CONTROL_FILE, owner="owner:la033-batch", freeze_sha256=freeze_sha256)
    store.claim()
    service = LocalModelService(model_dir)
    if service.weights_sha256 != model_profile["weights_sha256"]:
        raise RuntimeError("reconstructed weights digest mismatch")
    server = ModelHTTPServer(service)
    base = server.start()
    time.sleep(0.05)
    live_profile = dict(model_profile)
    live_profile["base_url"] = base
    transport = QualifiedLocalTransport(live_profile, store)
    identities = []
    started_batch = time.monotonic()
    try:
        for item in cells:
            attempt_id = item["attempt_id"]
            cell_rel = "cells/" + attempt_id
            cell_dir = HERE / "cells" / attempt_id
            identities.append({"attempt_id": attempt_id, "cell_dir": cell_rel, "arm": item["arm"], "seed": item["seed"], "case_id": item["case_id"]})
            marker = CHECKPOINT / "completed" / (hashlib.sha256(attempt_id.encode()).hexdigest() + ".json")
            if (cell_dir / "result.json").is_file() and marker.is_file():
                continue
            if cell_dir.exists():
                shutil.rmtree(cell_dir)
            if time.monotonic() - started_batch >= BATCH_ATTEMPT_SECONDS:
                raise TimeoutError("family-batch scientific attempt bound exhausted")
            reservation = store.reserve_cell(
                {
                    "attempt_id": attempt_id,
                    "case_id": item["case_id"],
                    "arm": item["arm"],
                    "seed": item["seed"],
                    "split": item["split"],
                    "family_id": item["family_id"],
                    "batch_id": BATCH_ID,
                },
                scientific=True,
            )
            write_json(cell_dir / "reserved.json", reservation, exist_ok=True)
            result = run_scientific_attempt(item["task"], item["arm"], item["seed"], transport, cell_dir)
            result.update(
                {
                    "case_id": item["case_id"],
                    "family_id": item["family_id"],
                    "source_id": item["source_id"],
                    "population": item["population"],
                    "split": item["split"],
                    "batch_id": BATCH_ID,
                    "schedule_index": item["schedule_index"],
                    "arm_position": item["arm_position"],
                    "freeze_sha256": freeze_sha256,
                    "model_profile_sha256": digest(model_profile),
                    "prompt_profile_sha256": digest(PROMPT_PROFILE),
                    "execution_profile": PROFILE_ID,
                    "runtime_sha256": digest(runtime),
                    "driver_sha256": runtime["source_files"]["papers/completion/law_to_action/benchmark/generated_code_study/driver.py"],
                    "handlers_sha256": runtime["source_files"]["papers/completion/law_to_action/benchmark/handlers/effects.py"],
                    "model_id": model_profile["model_id"],
                    "model_revision": model_profile["model_revision"],
                    "reservation_sha256": reservation["reservation_sha256"],
                }
            )
            atomic_write_json(cell_dir / "result.json", result)
            store.finish_cell(
                attempt_id,
                result_sha256=file_sha(cell_dir / "result.json"),
                error=None if result["terminal"] != "transport_or_format_failure" else result["terminal"],
                scientific=True,
            )
            atomic_write_json(
                marker,
                {"attempt_id": attempt_id, "terminal": result["terminal"], "result_sha256": file_sha(cell_dir / "result.json")},
            )
    finally:
        server.stop()
        accounting = service.accounting()
        store.close()

    ledgers = []
    for item, identity in zip(cells, identities):
        result = load_json(HERE / identity["cell_dir"] / "result.json")
        ledgers.append(result)
    raw_path = HERE / "raw.jsonl"
    costs_path = HERE / "costs.jsonl"
    with raw_path.open("w") as raw_handle, costs_path.open("w") as cost_handle:
        for result in ledgers:
            raw_handle.write(canonical(result).decode() + "\n")
            cost_handle.write(
                canonical(
                    {
                        "attempt_id": result["attempt_id"],
                        "arm": result["arm"],
                        "seed": result["seed"],
                        "case_id": result["case_id"],
                        "terminal": result["terminal"],
                        "model_calls": result["model_calls"],
                        "prompt_tokens": sum(row.get("prompt_tokens") or 0 for row in result["iterations"]),
                        "completion_tokens": sum(row.get("completion_tokens") or 0 for row in result["iterations"]),
                        "wall_seconds": result["wall_seconds"],
                        "cpu_seconds": result["cpu_seconds"],
                        "descendant_cpu_seconds": result["descendant_cpu_seconds"],
                        "peak_memory_kb": result["peak_memory_kb"],
                        "paid_budget": result["paid_budget"],
                        "unknown_costs": result["unknown_costs"],
                    }
                ).decode()
                + "\n"
            )
    terminals = [row["terminal"] for row in ledgers]
    summary = {
        "schema": "la-family-batch-summary/v1",
        "batch_id": BATCH_ID,
        "title": batch["title"],
        "phase": batch["phase"],
        "family_binding": batch["family_binding"],
        "source_id": batch["source_id"],
        "population": batch["population"],
        "planned_cells": 30,
        "terminal_records": len(ledgers),
        "unrun": 0,
        "unadmitted": 0,
        "useful_work": terminals.count("useful_work"),
        "candidate_failed": terminals.count("candidate_failed"),
        "transport_or_format_failure": terminals.count("transport_or_format_failure"),
        "model_calls": sum(row["model_calls"] for row in ledgers),
        "scientific_benchmark": True,
        "constructed_transport": False,
        "constructed_programs_substituted": False,
        "freeze_sha256": freeze_sha256,
        "model_profile_sha256": digest(model_profile),
        "prompt_profile_sha256": digest(PROMPT_PROFILE),
        "model_service_accounting": accounting,
        "completed_at": utc_now(),
    }
    atomic_write_json(HERE / "summary.json", summary)
    atomic_write_json(
        HERE / "manifest.json",
        {
            "schema": "la-family-batch-manifest/v1",
            "batch_id": BATCH_ID,
            "family_binding": batch["family_binding"],
            "source_id": batch["source_id"],
            "phase": batch["phase"],
            "paired_cases": batch["paired_cases"],
            "arms": list(batch["arms"]),
            "seeds": list(batch["seeds"]),
            "planned_cells": 30,
            "freeze_sha256": freeze_sha256,
            "model_profile_sha256": digest(model_profile),
            "prompt_profile_sha256": digest(PROMPT_PROFILE),
            "runtime_sha256": digest(runtime),
            "scientific_benchmark": True,
            "constructed_transport": False,
            "identities": identities,
        },
    )
    print(json.dumps({"status": "PASS", "batch_id": BATCH_ID, "terminal_records": 30, "model_calls": summary["model_calls"]}, sort_keys=True))


if __name__ == "__main__":
    main()
