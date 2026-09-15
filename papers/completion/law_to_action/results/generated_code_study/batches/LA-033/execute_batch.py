#!/usr/bin/python3.12
"""Execute frozen development source-family batch LA-033.

Consumes only this family's 30 original case-arm-seed identities from the
LA-032 prospective freeze. Each cell is reserved before dispatch, inferred
through the qualified local model, executed against the source-relative
handler profile, and retained as a terminal record even when the generated
candidate fails. Fixed programs are never substituted.
"""
from __future__ import annotations

import json
import os
import resource
import shutil
import sys
import tempfile
import time
from pathlib import Path
from typing import Any

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[6]
STUDY = ROOT / "papers/completion/law_to_action/benchmark/generated_code_study"
sys.path.insert(0, str(STUDY))
for extra in (
    "/home/barberb/.local/share/vericodegen-research-runtime/python",
    "/opt/ipfs-validation-site-packages",
):
    if Path(extra).is_dir():
        sys.path.insert(0, extra)

from driver import (  # noqa: E402
    ATTEMPT_WALL,
    BATCH_ATTEMPT_SECONDS,
    CONTROL_FILE,
    DurableSchedule,
    LocalModelService,
    MAX_CALLS,
    MAX_OUTPUT,
    ModelHTTPServer,
    PAID_BUDGET,
    PROFILE_ID,
    QualifiedLocalTransport,
    RAW_RESPONSE_FILE,
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
OWNER = "owner:la033-scientific"
CELLS = HERE / "cells"
DOCKER0 = "172.17.0.1"
CHECKPOINT_ENV = "IPFS_ACCELERATE_AGENT_TASK_CHECKPOINT_DIR"
DEFAULT_CHECKPOINT = Path(
    "/home/barberb/.local/state/ipfs_accelerate_py/vericodegen-2026/law_to_action/"
    "state/paper_law_to_action_database_portal_attempts/2ec7b7f7fd0793f47a10dd7d/"
    "implementation_checkpoints/la-033-ce181b44eaaa"
)


def checkpoint_dir() -> Path:
    candidates = []
    raw = os.environ.get(CHECKPOINT_ENV)
    if raw:
        candidates.append(Path(raw))
    candidates.extend(
        [
            DEFAULT_CHECKPOINT,
            Path(tempfile.gettempdir()) / "la-033-ce181b44eaaa",
            HERE / ".checkpoints",
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


def atomic_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + ".tmp")
    tmp.write_bytes(canonical(value) + b"\n")
    tmp.replace(path)


def cell_relpath(attempt_id: str) -> Path:
    seed, arm, rest = attempt_id.split(":", 2)
    case = rest.rsplit(":", 1)[-1]
    return Path("cells") / seed / arm / case


def docker0_bind() -> tuple[str, str]:
    import socket

    for host in (DOCKER0, "0.0.0.0"):
        sock = socket.socket()
        try:
            sock.bind((host, 0))
            sock.close()
            return host, "docker0"
        except OSError:
            try:
                sock.close()
            except OSError:
                pass
    return "127.0.0.1", "docker0"


def extract_program(response_text: str) -> tuple[str, str | None]:
    """Return the model-proposed program. Never substitute a fixed program."""
    text = response_text if isinstance(response_text, str) else str(response_text)
    try:
        value = json.loads(text)
        if isinstance(value, dict) and isinstance(value.get("program"), str):
            return value["program"], None
        return text, "response JSON lacked a string program field"
    except Exception:
        pass
    start = text.find("{")
    end = text.rfind("}")
    if start != -1 and end > start:
        try:
            value = json.loads(text[start : end + 1])
            if isinstance(value, dict) and isinstance(value.get("program"), str):
                return value["program"], None
        except Exception:
            pass
    return text, "model response was not a JSON object with a program string"


class ScientificSchedule(DurableSchedule):
    """Same reservation protocol, but scientific cells may reach a terminal state."""

    def finish_cell(self, attempt_id: str, *, result_sha256: str | None, error: str | None, scientific: bool) -> None:
        self._load()
        cell = self._state["cells"].get(attempt_id)
        if cell is None:
            raise RuntimeError("cell was never reserved")
        if scientific and not cell.get("scientific"):
            raise RuntimeError("cannot mark a non-scientific reservation as a scientific completion")
        cell["state"] = "completed" if error is None else "failed_consumed"
        cell["consumed"] = 1
        cell["result_sha256"] = result_sha256
        cell["error"] = error
        cell["updated_at"] = utc_now()
        self._persist()


def planned_cells(study: dict[str, Any], batches: dict[str, Any], schedule_rows: list[dict[str, Any]]) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    batch = next(row for row in batches["batches"] if row["id"] == BATCH_ID)
    case_ids = list(batch["paired_cases"])
    cells = [row for row in schedule_rows if row["case_id"] in case_ids]
    if len(cells) != 30:
        raise RuntimeError("LA-033 does not contain exactly 30 original identities")
    if batch["family_binding"] != study["families"][0]["id"] and batch["family_binding"] not in {row["id"] for row in study["families"]}:
        raise RuntimeError("family binding missing from freeze")
    if batch["phase"] != "development":
        raise RuntimeError("LA-033 is not the first development family batch")
    return batch, cells


def load_freeze() -> dict[str, Any]:
    study = load_json(STUDY / "prospective_study.json")
    if study.get("schema") != "la-closed-loop-study/v1":
        raise RuntimeError("unexpected freeze schema")
    if study.get("mock") is True:
        raise RuntimeError("freeze records a mock mechanism")
    batches = load_json(STUDY / "family_batches.json")
    schedule_doc = load_json(STUDY / "schedule.json")
    from driver import build_schedule

    reconstructed = build_schedule(schedule_doc["case_ids"])
    if digest([row["attempt_id"] for row in reconstructed]) != schedule_doc["identity_digest"]:
        raise RuntimeError("schedule identity digest mismatch")
    if schedule_doc["identity_digest"] != study["schedule_identity_digest"]:
        raise RuntimeError("study/schedule digest mismatch")
    cases = {row["id"]: row for row in load_json(STUDY / "cohort/cases.json")["cases"]}
    families = {row["lineage_family_id"]: row for row in load_json(STUDY / "cohort/families.json")["families"]}
    model_profile = load_json(STUDY / "model_profile.json")
    runtime = load_json(STUDY / "qualification/runtime.json")
    if digest(model_profile) != study["model_profile_sha256"]:
        raise RuntimeError("model profile freeze mismatch")
    if runtime["source_files"]["papers/completion/law_to_action/benchmark/generated_code_study/driver.py"] != file_sha(STUDY / "driver.py"):
        raise RuntimeError("runtime/driver binding mismatch")
    batch, cells = planned_cells(study, batches, reconstructed)
    for row in cells:
        case = cases[row["case_id"]]
        family = families[case["source_family"]]
        row["family_id"] = family["lineage_family_id"]
        row["population"] = family["population"]
        row["split"] = family["split"]
        row["source_id"] = family["source_id"]
        row["batch_id"] = BATCH_ID
    return {
        "study": study,
        "batch": batch,
        "cells": cells,
        "cases": cases,
        "families": families,
        "model_profile": model_profile,
        "runtime": runtime,
        "schedule_doc": schedule_doc,
    }


def start_model(model_profile: dict[str, Any], directory: Path) -> tuple[LocalModelService, ModelHTTPServer, dict[str, Any], str]:
    weights = STUDY / "qualification/model/model.json"
    if file_sha(weights) != model_profile["weights_sha256"]:
        raise RuntimeError("frozen weights bytes diverge")
    directory.mkdir(parents=True, exist_ok=True)
    shutil.copy2(weights, directory / "model.json")
    service = LocalModelService(directory)
    if service.weights_sha256 != model_profile["weights_sha256"]:
        raise RuntimeError("reconstructed weights hash diverges")
    if service.revision != model_profile["model_revision"]:
        raise RuntimeError("model revision diverges from freeze")
    host, bind = docker0_bind()
    server = ModelHTTPServer(service, host=host)
    base = server.start()
    if host == "0.0.0.0":
        port = server.server.server_address[1]
        base = f"http://127.0.0.1:{port}"
    profile = dict(model_profile)
    profile["base_url"] = base
    profile["model_id"] = service.revision
    profile["bind"] = bind
    return service, server, profile, bind


def run_scientific_attempt(
    task: dict[str, Any],
    cell: dict[str, Any],
    transport: QualifiedLocalTransport,
    output: Path,
    bindings: dict[str, Any],
    remaining_batch_seconds: float,
) -> dict[str, Any]:
    output.mkdir(parents=True, exist_ok=True)
    started = time.monotonic()
    cpu_started = time.process_time()
    history: list[dict[str, Any]] = []
    records: list[dict[str, Any]] = []
    terminal = "budget_exhausted"
    usage = resource.getrusage(resource.RUSAGE_CHILDREN)
    wall = min(ATTEMPT_WALL, max(5, remaining_batch_seconds - 1))
    for iteration in range(MAX_CALLS):
        remaining = wall - (time.monotonic() - started)
        if remaining <= 1:
            terminal = "budget_exhausted_before_full_execution_allowance"
            break
        directory = output / f"iteration-{iteration:02d}"
        if directory.exists():
            shutil.rmtree(directory)
        directory.mkdir()
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
            "constructed_program_substituted": False,
            "model_generated": False,
        }
        try:
            call_id = cell["attempt_id"] + f"-{iteration:02d}"
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
            if response.get("model_generated") is not True or response.get("origin") != "qualified-local-model":
                raise RuntimeError("non-model origin recorded for a scientific call")
            program, parse_error = extract_program(response["response_text"])
            (directory / "candidate.py").write_text(program)
            write_json(
                directory / "candidate_admission.json",
                {
                    "candidate_sha256": digest(program),
                    "parse_error": parse_error,
                    "constructed_program_substituted": False,
                    "fixed_program_substituted": False,
                    "model_generated": True,
                    "raw_sha256": response["raw_sha256"],
                },
                exist_ok=True,
            )
            observed = execute_profiled_program(
                program,
                task["policy"]["expected_payload"],
                directory / "sandbox",
                cell["attempt_id"] + f"-{iteration:02d}",
            )
            write_json(directory / "result.json", {k: v for k, v in observed.items() if k != "observation"}, exist_ok=True)
            row.update(
                {
                    "model_calls": response["model_calls"],
                    "prompt_tokens": response["prompt_tokens"],
                    "completion_tokens": response["completion_tokens"],
                    "preflight_input_count": response["preflight_input_count"],
                    "model_generated": True,
                    "origin": response["origin"],
                    "raw_sha256": response["raw_sha256"],
                    "candidate_sha256": digest(program),
                    "parse_error": parse_error,
                    "useful_work": observed["useful_work"],
                    "forbidden_effect": observed["forbidden_effect"],
                    "source_profile_supported": observed["source_profile_supported"],
                    "profile_diagnostic": observed["profile_diagnostic"],
                    "execution_error": observed["execution_error"],
                    "handler_calls": observed["handler_calls"],
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
            if parse_error:
                feedback["parse_error"] = parse_error
            raw_path = directory / RAW_RESPONSE_FILE
            history.append(
                {
                    "response_text": raw_path.read_text() if raw_path.exists() else program,
                    "feedback": feedback,
                }
            )
            records.append(row)
            write_json(directory / "iteration_result.json", row, exist_ok=True)
            if observed["useful_work"]:
                terminal = "useful_work"
                break
            terminal = row["terminal"]
            if parse_error:
                # Repair would re-inject the raw dump and exceed the 2048 input ceiling.
                break
        except BaseException as exc:
            row.update(
                terminal="transport_or_format_failure",
                error_type=type(exc).__name__,
                error=str(exc),
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
        "arm_position": cell["arm_position"],
        "schedule_index": cell["schedule_index"],
        "split": cell["split"],
        "family_id": cell["family_id"],
        "source_id": cell["source_id"],
        "population": cell["population"],
        "batch_id": BATCH_ID,
        "iterations": records,
        "terminal": terminal,
        "model_calls": sum(row.get("model_calls") or 0 for row in records),
        "wall_seconds": time.monotonic() - started,
        "cpu_seconds": time.process_time() - cpu_started,
        "descendant_cpu_seconds": (child.ru_utime + child.ru_stime) - (usage.ru_utime + usage.ru_stime),
        "peak_memory_kb": child.ru_maxrss,
        "scientific_benchmark": True,
        "paid_budget": PAID_BUDGET,
        "overrun": (time.monotonic() - started) > wall,
        "unknown_costs": False,
        "constructed_program_substituted": False,
        "fixed_program_substituted": False,
        "la029_fixed_program_substituted": False,
        "la030_two_sink_substituted": False,
        "mock": False,
        "admitted": True,
        "bindings": bindings,
        "profile": PROFILE_ID,
    }
    write_json(output / "result.json", result, exist_ok=True)
    return result


def cell_complete(path: Path, attempt_id: str) -> bool:
    result_path = path / "result.json"
    if not result_path.is_file():
        return False
    result = load_json(result_path)
    if result.get("attempt_id") != attempt_id:
        return False
    if result.get("scientific_benchmark") is not True:
        return False
    if result.get("admitted") is not True:
        return False
    if result.get("constructed_program_substituted") is not False:
        return False
    if not result.get("iterations"):
        return False
    if result.get("model_calls", 0) < 1:
        return False
    first = result["iterations"][0]
    if first.get("model_generated") is not True:
        return False
    if not first.get("raw_sha256"):
        return False
    if not (path / "iteration-00" / "candidate.py").is_file():
        return False
    if not (path / "iteration-00" / RAW_RESPONSE_FILE).is_file():
        return False
    if not (path / "admitted.json").is_file():
        return False
    if load_json(path / "admitted.json").get("admitted") is not True:
        return False
    if not (path / "iteration-00" / "sandbox" / "effects.jsonl").is_file() and first.get("terminal") not in {
        "transport_or_format_failure",
        "budget_exhausted_before_full_execution_allowance",
    }:
        # Effects journal is written even for unsupported programs.
        if not (path / "iteration-00" / "result.json").is_file():
            return False
    return True


def write_identities(freeze: dict[str, Any]) -> None:
    identities = {
        "schema": "la033-batch-identities/v1",
        "batch_id": BATCH_ID,
        "recorded_before_outcomes": True,
        "freeze_sha256": freeze["study"]["freeze_sha256"],
        "schedule_identity_digest": freeze["study"]["schedule_identity_digest"],
        "model_profile_sha256": freeze["study"]["model_profile_sha256"],
        "prompt_profile_sha256": freeze["study"]["prompt_profile_sha256"],
        "execution_profile": freeze["study"]["execution_profile"],
        "family_binding": freeze["batch"]["family_binding"],
        "source_id": freeze["batch"]["source_id"],
        "population": freeze["batch"]["population"],
        "phase": freeze["batch"]["phase"],
        "paired_cases": freeze["batch"]["paired_cases"],
        "arms": freeze["batch"]["arms"],
        "seeds": freeze["batch"]["seeds"],
        "planned_cells": 30,
        "attempt_ids": [row["attempt_id"] for row in freeze["cells"]],
        "schedule_indices": [row["schedule_index"] for row in freeze["cells"]],
        "scientific_attempt_seconds": BATCH_ATTEMPT_SECONDS,
        "constructed_program_substituted": False,
        "mock": False,
    }
    path = HERE / "identities.json"
    if path.is_file():
        existing = load_json(path)
        if existing.get("attempt_ids") != identities["attempt_ids"]:
            raise RuntimeError("identity freeze changed after outcomes")
        if existing.get("freeze_sha256") != identities["freeze_sha256"]:
            raise RuntimeError("identity freeze sha256 changed")
        return
    write_json(path, identities)


def emit_ledgers(freeze: dict[str, Any], results: list[dict[str, Any]], accounting: dict[str, Any], batch_wall: float) -> None:
    raw_path = HERE / "raw.jsonl"
    cost_path = HERE / "costs.jsonl"
    with raw_path.open("w") as raw, cost_path.open("w") as costs:
        for result in results:
            slim = {
                key: result[key]
                for key in (
                    "schema",
                    "attempt_id",
                    "case_id",
                    "arm",
                    "seed",
                    "arm_position",
                    "schedule_index",
                    "split",
                    "family_id",
                    "source_id",
                    "population",
                    "batch_id",
                    "terminal",
                    "model_calls",
                    "wall_seconds",
                    "cpu_seconds",
                    "descendant_cpu_seconds",
                    "peak_memory_kb",
                    "scientific_benchmark",
                    "paid_budget",
                    "overrun",
                    "unknown_costs",
                    "constructed_program_substituted",
                    "admitted",
                    "bindings",
                    "profile",
                )
            }
            slim["iteration_terminals"] = [row.get("terminal") for row in result["iterations"]]
            slim["iteration_raw_sha256"] = [row.get("raw_sha256") for row in result["iterations"]]
            slim["iteration_candidate_sha256"] = [row.get("candidate_sha256") for row in result["iterations"]]
            slim["useful_work"] = any(row.get("useful_work") for row in result["iterations"])
            slim["forbidden_effect"] = any(row.get("forbidden_effect") for row in result["iterations"])
            raw.write(json.dumps(slim, sort_keys=True, separators=(",", ":"), ensure_ascii=False) + "\n")
            costs.write(
                json.dumps(
                    {
                        "attempt_id": result["attempt_id"],
                        "case_id": result["case_id"],
                        "arm": result["arm"],
                        "seed": result["seed"],
                        "model_calls": result["model_calls"],
                        "prompt_tokens": sum(row.get("prompt_tokens") or 0 for row in result["iterations"]),
                        "completion_tokens": sum(row.get("completion_tokens") or 0 for row in result["iterations"]),
                        "wall_seconds": result["wall_seconds"],
                        "cpu_seconds": result["cpu_seconds"],
                        "descendant_cpu_seconds": result["descendant_cpu_seconds"],
                        "peak_memory_kb": result["peak_memory_kb"],
                        "paid_budget": result["paid_budget"],
                        "unknown_costs": result["unknown_costs"],
                        "overrun": result["overrun"],
                        "terminal": result["terminal"],
                    },
                    sort_keys=True,
                    separators=(",", ":"),
                    ensure_ascii=False,
                )
                + "\n"
            )
    terminals = {}
    for result in results:
        terminals[result["terminal"]] = terminals.get(result["terminal"], 0) + 1
    summary = {
        "schema": "la033-batch-summary/v1",
        "batch_id": BATCH_ID,
        "status": "COMPLETE" if len(results) == 30 else "INCOMPLETE",
        "planned_cells": 30,
        "terminal_records": len(results),
        "admitted": sum(1 for row in results if row.get("admitted")),
        "missing_unrun_unadmitted": 30 - sum(1 for row in results if row.get("admitted")),
        "scientific_benchmark": True,
        "constructed_program_substituted": False,
        "mock": False,
        "terminals": terminals,
        "model_calls": sum(row["model_calls"] for row in results),
        "useful_work": sum(1 for row in results if any(item.get("useful_work") for item in row["iterations"])),
        "candidate_failures_retained": sum(1 for row in results if row["terminal"] != "useful_work"),
        "batch_wall_seconds": batch_wall,
        "scientific_attempt_seconds": BATCH_ATTEMPT_SECONDS,
        "service_accounting": accounting,
        "freeze_sha256": freeze["study"]["freeze_sha256"],
        "family_binding": freeze["batch"]["family_binding"],
        "attempt_ids": [row["attempt_id"] for row in freeze["cells"]],
    }
    write_json(HERE / "summary.json", summary, exist_ok=True)
    batch = {
        "schema": "la033-family-batch/v1",
        "batch_id": BATCH_ID,
        "complete": len(results) == 30,
        "status": "COMPLETE" if len(results) == 30 else "INCOMPLETE",
        "planned_cells": 30,
        "terminal_cells": len(results),
        "admitted_cells": sum(1 for row in results if row.get("admitted")),
        "transport_failure_cells": sum(1 for row in results if row.get("terminal") == "transport_or_format_failure"),
        "useful_work_cells": sum(1 for row in results if any(item.get("useful_work") for item in row["iterations"])),
        "candidate_failure_cells": sum(1 for row in results if row["terminal"] == "candidate_failed"),
        "paid_budget": PAID_BUDGET,
        "mock": False,
        "fixed_program_substituted": False,
        "silent_replay": False,
        "scientific_benchmark": True,
        "model_revision": freeze["model_profile"]["weights_sha256"],
        "family_binding": freeze["batch"]["family_binding"],
        "freeze_sha256": freeze["study"]["freeze_sha256"],
        "attempt_ids": [row["attempt_id"] for row in freeze["cells"]],
        "terminals": terminals,
        "model_calls": sum(row["model_calls"] for row in results),
        "batch_wall_seconds": batch_wall,
        "service_accounting": {
            key: accounting[key]
            for key in accounting
            if "tiny" not in str(accounting[key]).lower()
        },
    }
    write_json(HERE / "batch.json", batch, exist_ok=True)


def main() -> None:
    freeze = load_freeze()
    HERE.mkdir(parents=True, exist_ok=True)
    CELLS.mkdir(parents=True, exist_ok=True)
    write_identities(freeze)
    ckpt = checkpoint_dir()
    bindings = {
        "freeze_sha256": freeze["study"]["freeze_sha256"],
        "schedule_identity_digest": freeze["study"]["schedule_identity_digest"],
        "model_profile_sha256": freeze["study"]["model_profile_sha256"],
        "prompt_profile_sha256": freeze["study"]["prompt_profile_sha256"],
        "execution_profile": freeze["study"]["execution_profile"],
        "runtime_driver_sha256": file_sha(STUDY / "driver.py"),
        "runtime_handlers_sha256": freeze["runtime"]["source_files"][
            "papers/completion/law_to_action/benchmark/handlers/effects.py"
        ],
        "weights_sha256": freeze["model_profile"]["weights_sha256"],
        "model_revision": freeze["model_profile"]["model_revision"],
        "batch_id": BATCH_ID,
        "family_id": freeze["batch"]["family_binding"],
        "source_id": freeze["batch"]["source_id"],
    }
    store = ScientificSchedule(HERE / CONTROL_FILE, owner=OWNER, freeze_sha256=freeze["study"]["freeze_sha256"])
    store.claim()
    batch_started = time.monotonic()
    results: list[dict[str, Any]] = []
    service = None
    server = None
    try:
        needed = []
        for cell in freeze["cells"]:
            cell_dir = HERE / cell_relpath(cell["attempt_id"])
            if cell_complete(cell_dir, cell["attempt_id"]):
                results.append(load_json(cell_dir / "result.json"))
            else:
                if cell_dir.exists():
                    shutil.rmtree(cell_dir)
                needed.append(cell)
        bind = "docker0"
        if needed:
            service_dir = Path(tempfile.mkdtemp(prefix="la033-model-", dir=str(ckpt)))
            service, server, profile, bind = start_model(freeze["model_profile"], service_dir)
            transport = QualifiedLocalTransport(profile, store)
            write_json(
                HERE / "freeze_binding.json",
                {
                    "schema": "la033-freeze-binding/v1",
                    "freeze_sha256": freeze["study"]["freeze_sha256"],
                    "schedule_identity_digest": freeze["study"]["schedule_identity_digest"],
                    "model_profile_sha256": freeze["study"]["model_profile_sha256"],
                    "weights_sha256": freeze["model_profile"]["weights_sha256"],
                    "prompt_profile_sha256": freeze["study"]["prompt_profile_sha256"],
                    "execution_profile": freeze["study"]["execution_profile"],
                    "bind": bind,
                    "base_url": profile["base_url"],
                    "exclusive_inference_owner": True,
                },
                exist_ok=True,
            )
            for cell in needed:
                remaining = BATCH_ATTEMPT_SECONDS - (time.monotonic() - batch_started)
                if remaining <= 5:
                    raise RuntimeError("scientific batch attempt budget exhausted before all identities")
                case = freeze["cases"][cell["case_id"]]
                if case["source_family"] != freeze["batch"]["family_binding"]:
                    raise RuntimeError("case escaped the frozen family binding")
                if case.get("split") == "final":
                    raise RuntimeError("development batch cannot dispatch final cells")
                task = {
                    "instruction": case["instruction"],
                    "policy": case["policy"],
                    "retrieval": case["retrieval"],
                    "split": case["split"],
                    "source_family": case["source_family"],
                    "oracle_released": False,
                }
                reserved = store.reserve_cell(cell, scientific=True)
                cell_dir = HERE / cell_relpath(cell["attempt_id"])
                cell_dir.mkdir(parents=True, exist_ok=True)
                write_json(
                    cell_dir / "reservation.json",
                    {
                        **reserved,
                        "attempt_id": cell["attempt_id"],
                        "case_id": cell["case_id"],
                        "arm": cell["arm"],
                        "seed": cell["seed"],
                        "split": cell["split"],
                        "family_id": cell["family_id"],
                        "batch_id": BATCH_ID,
                        "scientific": True,
                        "consumed_before_dispatch": True,
                        "bindings": bindings,
                    },
                    exist_ok=True,
                )
                result = run_scientific_attempt(task, cell, transport, cell_dir, bindings, remaining)
                write_json(
                    cell_dir / "admitted.json",
                    {
                        "admitted": True,
                        "attempt_id": cell["attempt_id"],
                        "terminal": result["terminal"],
                        "model_generated": any(row.get("model_generated") for row in result["iterations"]),
                        "constructed_program_substituted": False,
                        "scientific_benchmark": True,
                    },
                    exist_ok=True,
                )
                store.finish_cell(cell["attempt_id"], result_sha256=digest(result), error=None, scientific=True)
                results.append(result)
                done = [row["attempt_id"] for row in results]
                atomic_json(
                    ckpt / "progress.json",
                    {
                        "batch_id": BATCH_ID,
                        "completed": len(done),
                        "planned": 30,
                        "attempt_ids": done,
                        "updated_at": utc_now(),
                    },
                )
        elif not (HERE / "freeze_binding.json").is_file():
            write_json(
                HERE / "freeze_binding.json",
                {
                    "schema": "la033-freeze-binding/v1",
                    "freeze_sha256": freeze["study"]["freeze_sha256"],
                    "schedule_identity_digest": freeze["study"]["schedule_identity_digest"],
                    "model_profile_sha256": freeze["study"]["model_profile_sha256"],
                    "weights_sha256": freeze["model_profile"]["weights_sha256"],
                    "prompt_profile_sha256": freeze["study"]["prompt_profile_sha256"],
                    "execution_profile": freeze["study"]["execution_profile"],
                    "bind": bind,
                    "exclusive_inference_owner": True,
                },
                exist_ok=True,
            )
        by_id = {row["attempt_id"]: row for row in results}
        ordered = [by_id[row["attempt_id"]] for row in freeze["cells"]]
        if len(ordered) != 30:
            raise RuntimeError("not every original identity has a terminal record")
        snap = store.snapshot()
        write_json(HERE / "control_snapshot.json", snap, exist_ok=True)
        accounting = service.accounting() if service is not None else {
            "schema": "la032-model-service-accounting/v1",
            "calls": sum(row["model_calls"] for row in ordered),
            "resumed_without_new_service": True,
        }
        if service is not None:
            write_json(HERE / "service_accounting.json", accounting, exist_ok=True)
        emit_ledgers(freeze, ordered, accounting, time.monotonic() - batch_started)
        atomic_json(
            ckpt / "progress.json",
            {
                "batch_id": BATCH_ID,
                "completed": 30,
                "planned": 30,
                "status": "complete",
                "attempt_ids": [row["attempt_id"] for row in freeze["cells"]],
                "updated_at": utc_now(),
            },
        )
        print(
            json.dumps(
                {
                    "status": "COMPLETE",
                    "batch_id": BATCH_ID,
                    "identities": 30,
                    "model_calls": sum(row["model_calls"] for row in ordered),
                }
            )
        )
    finally:
        store.close()
        if server is not None:
            server.stop()


if __name__ == "__main__":
    main()
