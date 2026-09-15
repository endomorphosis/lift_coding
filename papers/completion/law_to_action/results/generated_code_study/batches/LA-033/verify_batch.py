#!/usr/bin/python3.12
"""Read-only verifier for a frozen generated-code family batch."""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[6]
STUDY = ROOT / "papers/completion/law_to_action/benchmark/generated_code_study"
sys.path.insert(0, str(STUDY))
from driver import (  # noqa: E402
    BATCH_ATTEMPT_SECONDS,
    MAX_INPUT,
    MAX_OUTPUT,
    PAID_BUDGET,
    PROFILE_ID,
    build_schedule,
    digest,
    file_sha,
    load_json,
    messages_for,
    render_chat,
)

HEX = re.compile(r"^[0-9a-f]{64}$")
TERMINALS = {
    "useful_work",
    "candidate_failed",
    "transport_or_format_failure",
    "budget_exhausted",
    "budget_exhausted_before_full_execution_allowance",
}


def fail(message: str) -> None:
    raise SystemExit("family-batch verifier failed: " + message)


def require(ok: bool, message: str) -> None:
    if not ok:
        fail(message)


def cell_dir(batch_dir: Path, attempt_id: str) -> Path:
    seed, arm, rest = attempt_id.split(":", 2)
    return batch_dir / "cells" / seed / arm / rest.rsplit(":", 1)[-1]


def planned(study: dict, batches: dict, schedule_rows: list[dict], task_id: str) -> tuple[dict, list[dict]]:
    batch = next((row for row in batches["batches"] if row["id"] == task_id), None)
    require(batch is not None, "batch-task missing from family_batches.json")
    cells = [row for row in schedule_rows if row["case_id"] in batch["paired_cases"]]
    require(len(cells) == 30, "batch does not contain exactly 30 original identities")
    require(len({row["attempt_id"] for row in cells}) == 30, "duplicate identities")
    require(batch["family_binding"] in {row["id"] for row in study["families"]}, "family unbound")
    require(set(batch["arms"]) == {"A0", "A1", "A2", "A3", "A4"}, "arms")
    require(batch["seeds"] == [104729, 104759, 104761], "seeds")
    require(batch["planned_cells"] == 30, "planned_cells")
    require(batch.get("maximum_scientific_attempt_seconds", BATCH_ATTEMPT_SECONDS) <= 3600, "attempt budget")
    return batch, cells


def check_bindings(bindings: dict, study: dict, runtime: dict, batch: dict, model_profile: dict) -> None:
    require(bindings.get("freeze_sha256") == study["freeze_sha256"], "freeze binding")
    require(bindings.get("schedule_identity_digest") == study["schedule_identity_digest"], "schedule binding")
    require(bindings.get("model_profile_sha256") == study["model_profile_sha256"], "model profile binding")
    require(bindings.get("prompt_profile_sha256") == study["prompt_profile_sha256"], "prompt binding")
    require(bindings.get("execution_profile") == study["execution_profile"] == PROFILE_ID, "profile binding")
    require(bindings.get("weights_sha256") == model_profile["weights_sha256"], "weights binding")
    require(
        bindings.get("runtime_driver_sha256")
        == runtime["source_files"]["papers/completion/law_to_action/benchmark/generated_code_study/driver.py"],
        "driver binding",
    )
    require(
        bindings.get("runtime_handlers_sha256")
        == runtime["source_files"]["papers/completion/law_to_action/benchmark/handlers/effects.py"],
        "handler binding",
    )
    require(bindings.get("family_id") == batch["family_binding"], "family binding")
    require(bindings.get("source_id") == batch["source_id"], "source binding")
    require(bindings.get("batch_id") == batch["id"], "batch id binding")


def check_iteration(directory: Path, row: dict, case: dict, cell: dict) -> None:
    require((directory / "candidate.py").is_file(), "missing generated candidate")
    require((directory / "raw_response.json").is_file(), "missing raw response")
    raw = (directory / "raw_response.json").read_bytes()
    require(hashlib.sha256(raw).hexdigest() == row.get("raw_sha256"), "raw sha")
    require(HEX.fullmatch(row.get("raw_sha256") or ""), "raw sha format")
    transport = load_json(directory / "transport_result.json")
    require(transport.get("model_generated") is True, "model origin")
    require(transport.get("origin") == "qualified-local-model", "model origin")
    require(transport.get("prompt_tokens") == transport.get("preflight_input_count"), "token pair")
    require(transport.get("prompt_tokens") == row.get("prompt_tokens") == row.get("preflight_input_count"), "iteration tokens")
    require(type(transport["prompt_tokens"]) is int and 0 < transport["prompt_tokens"] <= MAX_INPUT, "input ceiling")
    require(type(transport["completion_tokens"]) is int and 0 < transport["completion_tokens"] <= MAX_OUTPUT, "output ceiling")
    preflight_path = directory / "preflight.json"
    require(preflight_path.is_file(), "retained preflight missing")
    preflight = load_json(preflight_path)
    require(preflight.get("input_count") == transport["prompt_tokens"], "retained preflight input_count")
    expected_prompt = render_chat(load_json(directory / "messages.json"))
    require(preflight.get("prompt") == expected_prompt, "preflight prompt mismatch")
    admission = load_json(directory / "candidate_admission.json")
    require(admission.get("constructed_program_substituted") is False, "constructed program")
    require(admission.get("fixed_program_substituted") is False, "fixed program")
    require(admission.get("model_generated") is True, "candidate not model-generated")
    candidate = (directory / "candidate.py").read_text()
    require(admission.get("candidate_sha256") == digest(candidate) == row.get("candidate_sha256"), "candidate sha")
    require(admission.get("raw_sha256") == row.get("raw_sha256"), "admission raw sha")
    reserved = load_json(directory / "inference_reserved.json")
    require(reserved.get("consumed_before_request") is True, "call reserved after request")
    messages = load_json(directory / "messages.json")
    task = {
        "instruction": case["instruction"],
        "policy": case["policy"],
        "retrieval": case["retrieval"],
        "split": case["split"],
        "source_family": case["source_family"],
        "oracle_released": False,
    }
    require(messages == messages_for(task, cell["arm"], []), "messages drifted from freeze")
    sandbox = directory / "sandbox"
    require(sandbox.is_dir(), "sandbox missing")
    if row.get("handler_calls"):
        require((sandbox / "effects.jsonl").is_file(), "effects journal missing for handler calls")
    else:
        require(not (sandbox / "exports").exists(), "undeclared export without handler call")
    iteration_disk = load_json(directory / "iteration_result.json")
    require(iteration_disk.get("terminal") in TERMINALS, "iteration terminal")
    require(iteration_disk.get("model_generated") is True, "iteration not model-generated")
    require(iteration_disk.get("constructed_program_substituted") is False, "iteration substitution")


def check_cell(batch_dir: Path, cell: dict, case: dict, study: dict, runtime: dict, batch: dict, model_profile: dict, costs: dict) -> dict:
    path = cell_dir(batch_dir, cell["attempt_id"])
    require(path.is_dir(), "unrun identity " + cell["attempt_id"])
    result = load_json(path / "result.json")
    admitted = load_json(path / "admitted.json")
    reserved = load_json(path / "reservation.json")
    require(admitted.get("admitted") is True, "unadmitted " + cell["attempt_id"])
    require(result.get("admitted") is True, "result unadmitted")
    require(result.get("attempt_id") == cell["attempt_id"], "attempt id")
    require(result.get("case_id") == cell["case_id"] == case["id"], "case id")
    require(result.get("arm") == cell["arm"], "arm")
    require(result.get("seed") == cell["seed"], "seed")
    require(result.get("batch_id") == batch["id"], "batch id")
    require(result.get("family_id") == batch["family_binding"] == case["source_family"], "family")
    require(result.get("source_id") == batch["source_id"], "source")
    require(result.get("split") == "development", "development split")
    require(result.get("scientific_benchmark") is True, "scientific flag")
    require(result.get("mock") is False, "mock cell")
    require(result.get("constructed_program_substituted") is False, "constructed substitution")
    require(result.get("fixed_program_substituted") is False, "fixed substitution")
    require(result.get("la029_fixed_program_substituted") is False, "LA-029 substitution")
    require(result.get("la030_two_sink_substituted") is False, "LA-030 substitution")
    require(result.get("paid_budget") == PAID_BUDGET, "paid budget")
    require(result.get("unknown_costs") is False, "unknown costs")
    require(result.get("model_calls") >= 1, "no model call")
    require(result.get("iterations"), "no iterations")
    require(result.get("terminal") in TERMINALS, "terminal")
    require(isinstance(result.get("wall_seconds"), (int, float)), "wall cost")
    require(isinstance(result.get("cpu_seconds"), (int, float)), "cpu cost")
    check_bindings(result.get("bindings") or {}, study, runtime, batch, model_profile)
    check_bindings(reserved.get("bindings") or {}, study, runtime, batch, model_profile)
    require(reserved.get("consumed_before_dispatch") is True, "cell reserved after dispatch")
    require(reserved.get("scientific") is True, "non-scientific reservation")
    first = result["iterations"][0]
    require(first.get("model_generated") is True, "first iteration not generated")
    check_iteration(path / "iteration-00", first, case, cell)
    cost = costs.get(cell["attempt_id"])
    require(cost is not None, "cost row missing")
    require(cost.get("model_calls") == result["model_calls"], "cost model_calls")
    require(cost.get("terminal") == result["terminal"], "cost terminal")
    require(cost.get("unknown_costs") is False, "cost unknown")
    require(cost.get("paid_budget") == 0, "cost paid")
    return result


def verify(freeze_path: Path, task_id: str, require_complete: bool) -> dict:
    study = load_json(freeze_path)
    require(study.get("schema") == "la-closed-loop-study/v1", "freeze schema")
    require(study.get("mock") is not True, "mock freeze")
    require(isinstance(study.get("freeze_sha256"), str) and HEX.fullmatch(study["freeze_sha256"]), "freeze sha256")
    batches = load_json(STUDY / "family_batches.json")
    schedule_doc = load_json(STUDY / "schedule.json")
    reconstructed = build_schedule(schedule_doc["case_ids"])
    require(digest([row["attempt_id"] for row in reconstructed]) == schedule_doc["identity_digest"], "schedule digest")
    require(schedule_doc["identity_digest"] == study["schedule_identity_digest"], "study schedule digest")
    model_profile = load_json(STUDY / "model_profile.json")
    runtime = load_json(STUDY / "qualification/runtime.json")
    require(digest(model_profile) == study["model_profile_sha256"], "model profile freeze")
    require(
        runtime["source_files"]["papers/completion/law_to_action/benchmark/generated_code_study/driver.py"]
        == file_sha(STUDY / "driver.py"),
        "runtime/driver",
    )
    batch, cells = planned(study, batches, reconstructed, task_id)
    require(batch.get("registered_success") is False, "future success pre-registered")
    require(batch.get("scientific_cells_completed") == 0, "freeze claimed execution")
    batch_dir = ROOT / "papers/completion/law_to_action/results/generated_code_study/batches" / task_id
    if HERE.name == task_id:
        batch_dir = HERE
    require(batch_dir.is_dir(), "batch results missing")
    identities = load_json(batch_dir / "identities.json")
    require(identities.get("recorded_before_outcomes") is True, "identities recorded after outcomes")
    require(identities.get("attempt_ids") == [row["attempt_id"] for row in cells], "identity order")
    require(identities.get("freeze_sha256") == study["freeze_sha256"], "identity freeze")
    require(identities.get("family_binding") == batch["family_binding"], "identity family")
    require(identities.get("constructed_program_substituted") is False, "identity substitution")
    require(identities.get("mock") is False, "identity mock")
    cases = {row["id"]: row for row in load_json(STUDY / "cohort/cases.json")["cases"]}
    costs = {json.loads(line)["attempt_id"]: json.loads(line) for line in (batch_dir / "costs.jsonl").read_text().splitlines()}
    require(len(costs) == 30, "cost ledger incomplete")
    raw_ids = []
    for line in (batch_dir / "raw.jsonl").read_text().splitlines():
        row = json.loads(line)
        raw_ids.append(row["attempt_id"])
        require(row.get("scientific_benchmark") is True, "raw scientific")
        require(row.get("constructed_program_substituted") is False, "raw substitution")
        require(row.get("admitted") is True, "raw unadmitted")
    require(raw_ids == [row["attempt_id"] for row in cells], "raw ledger order")
    results = []
    for cell in cells:
        case = cases[cell["case_id"]]
        require(case.get("split") != "final", "final cell in development batch")
        results.append(check_cell(batch_dir, cell, case, study, runtime, batch, model_profile, costs))
    summary = load_json(batch_dir / "summary.json")
    batch_doc = load_json(batch_dir / "batch.json")
    accounting = load_json(batch_dir / "service_accounting.json")
    binding = load_json(batch_dir / "freeze_binding.json")
    control = load_json(batch_dir / "control.json")
    terminals: dict[str, int] = {}
    for result in results:
        terminals[result["terminal"]] = terminals.get(result["terminal"], 0) + 1
    admitted = sum(1 for row in results if row.get("admitted"))
    require(admitted == 30, "missing/unrun/unadmitted evidence")
    require(summary.get("terminal_records") == 30, "summary terminals")
    require(summary.get("admitted") == 30, "summary admitted")
    require(summary.get("missing_unrun_unadmitted") == 0, "summary missing")
    require(summary.get("constructed_program_substituted") is False, "summary substitution")
    require(summary.get("mock") is False, "summary mock")
    require(summary.get("scientific_benchmark") is True, "summary scientific")
    require(summary.get("model_calls") == sum(row["model_calls"] for row in results), "summary calls")
    require(summary.get("candidate_failures_retained") == sum(1 for row in results if row["terminal"] != "useful_work"), "failures dropped")
    require(batch_doc.get("complete") is True, "batch incomplete")
    require(batch_doc.get("terminal_cells") == 30, "batch terminals")
    require(batch_doc.get("admitted_cells") == 30, "batch admitted")
    require(batch_doc.get("fixed_program_substituted") is False, "batch substitution")
    require(batch_doc.get("silent_replay") is False, "silent replay")
    require(batch_doc.get("mock") is False, "batch mock")
    require(batch_doc.get("paid_budget") == 0, "batch paid")
    require(batch_doc.get("model_revision") == model_profile["weights_sha256"], "model revision")
    require(accounting.get("calls") == 30, "service calls")
    require(accounting.get("systemd_required") is False, "systemd")
    require(accounting.get("indefinitely_running_required") is False, "indefinite service")
    require(binding.get("freeze_sha256") == study["freeze_sha256"], "binding freeze")
    require(binding.get("exclusive_inference_owner") is True, "exclusive owner")
    require((control.get("ownership") or {}).get("freeze_sha256") == study["freeze_sha256"], "control freeze")
    require(len(control.get("cells") or {}) == 30, "control cells")
    for cell in cells:
        row = control["cells"][cell["attempt_id"]]
        require(row.get("consumed") in (1, True), "unconsumed reservation")
        require(row.get("scientific") in (1, True), "control not scientific")
        require(row.get("state") in {"completed", "failed_consumed"}, "control not terminal")
        require(row.get("error") is None, "dropped as error")
    if require_complete:
        require(summary.get("status") == "COMPLETE" and batch_doc.get("status") == "COMPLETE", "not complete")
    return {
        "status": "PASS",
        "batch_id": task_id,
        "identities": 30,
        "admitted": admitted,
        "terminal_records": 30,
        "model_calls": sum(row["model_calls"] for row in results),
        "terminals": terminals,
        "candidate_failures_retained": sum(1 for row in results if row["terminal"] != "useful_work"),
        "constructed_program_substituted": False,
        "mock": False,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--freeze", type=Path, required=True)
    parser.add_argument("--batch-task", required=True)
    parser.add_argument("--require-complete", action="store_true")
    args = parser.parse_args()
    print(json.dumps(verify(args.freeze, args.batch_task, args.require_complete), sort_keys=True))


if __name__ == "__main__":
    main()
