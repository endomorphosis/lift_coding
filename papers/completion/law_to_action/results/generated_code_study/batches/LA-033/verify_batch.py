#!/usr/bin/python3.12
"""Read-only verifier for one frozen generated-code family batch."""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE
while ROOT != ROOT.parent and not (
    ROOT / "papers/completion/law_to_action/benchmark/generated_code_study/driver.py"
).is_file():
    ROOT = ROOT.parent
STUDY = ROOT / "papers/completion/law_to_action/benchmark/generated_code_study"
RESULTS_ROOT = ROOT / "papers/completion/law_to_action/results/generated_code_study/batches"
sys.path.insert(0, str(STUDY))
from driver import (  # noqa: E402
    ARMS,
    BATCH_ATTEMPT_SECONDS,
    MAX_CALLS,
    MAX_INPUT,
    MAX_OUTPUT,
    PAID_BUDGET,
    PROFILE_ID,
    SEEDS,
    build_schedule,
    digest,
    file_sha,
    load_json,
    messages_for,
)

TERMINALS = {
    "useful_work",
    "candidate_failed",
    "transport_or_format_failure",
    "budget_exhausted",
    "budget_exhausted_before_full_execution_allowance",
}


def fail(message: str) -> None:
    raise SystemExit("family-batch verifier failed: " + message)


def require(condition: bool, message: str) -> None:
    if not condition:
        fail(message)


def identities_for(batch: dict, schedule_doc: dict, cases: dict) -> list[dict]:
    expected = build_schedule(schedule_doc["case_ids"])
    rows = []
    for row in expected:
        info = cases[row["case_id"]]
        if info["source_family"] != batch["family_binding"]:
            continue
        item = dict(row)
        item["family_id"] = info["source_family"]
        item["population"] = info["population"]
        item["split"] = info["split"]
        item["batch_id"] = batch["id"]
        rows.append(item)
    require(len(rows) == 30, f"{batch['id']} does not own 30 original identities")
    require(len({row["attempt_id"] for row in rows}) == 30, "duplicate batch identities")
    return rows


def verify_freeze(study: dict, batch: dict) -> str:
    require(study.get("schema") == "la-closed-loop-study/v1", "unexpected study schema")
    require(study.get("mock") is False, "mock freeze")
    require(study.get("permissive_availability_flag") is False, "permissive availability flag")
    require(study.get("la031_completed") is False, "LA-031 marked complete by freeze")
    model_profile = load_json(STUDY / "model_profile.json")
    require(digest(model_profile) == study["model_profile_sha256"], "model profile digest")
    require(model_profile["paid_budget"] == PAID_BUDGET, "paid budget")
    require(file_sha(STUDY / "qualification/model/model.json") == model_profile["weights_sha256"], "weights pin")
    require(study["execution_profile"] == PROFILE_ID, "execution profile")
    require(batch["family_binding"].startswith("family:"), "family binding")
    require(batch["planned_cells"] == 30, "planned cell count")
    require(list(batch["arms"]) == list(ARMS) and list(batch["seeds"]) == list(SEEDS), "arms/seeds")
    require(batch["maximum_scientific_attempt_seconds"] == BATCH_ATTEMPT_SECONDS, "attempt bound")
    require(batch.get("registered_success") is False, "freeze registered future success")
    return digest(model_profile)


def verify_cell(identity: dict, output: Path, task: dict, freeze_sha256: str, model_sha: str, control: dict) -> dict:
    attempt_id = identity["attempt_id"]
    cell_dir = output / "cells" / attempt_id
    require(cell_dir.is_dir(), f"missing cell directory {attempt_id}")
    for name in ("reservation.json", "attempt_start.json", "result.json"):
        require((cell_dir / name).is_file(), f"missing {name} for {attempt_id}")
    reservation = load_json(cell_dir / "reservation.json")
    start = load_json(cell_dir / "attempt_start.json")
    result = load_json(cell_dir / "result.json")
    durable = control["cells"].get(attempt_id)
    require(durable is not None, f"unreserved cell {attempt_id}")
    require(int(durable.get("consumed") or 0) == 1, f"unconsumed cell {attempt_id}")
    require(durable.get("scientific") in (1, True), f"unadmitted scientific cell {attempt_id}")
    require(durable.get("state") in ("completed", "failed_consumed"), f"cell {attempt_id} not terminal")
    require(durable.get("result_sha256") == digest(result), f"result digest mismatch {attempt_id}")
    require(reservation.get("reservation_sha256") == durable.get("reservation_sha256"), f"reservation mismatch {attempt_id}")
    require(start.get("schema") == "la-closed-loop-attempt-start/v1", "attempt start schema")
    require(result.get("schema") == "la-closed-loop-attempt/v1", "attempt result schema")
    require(result.get("attempt_id") == attempt_id, "attempt id")
    require(result.get("case_id") == identity["case_id"] == start.get("case_id") == durable.get("case_id"), "case binding")
    require(result.get("family_id") == identity["family_id"] == start.get("family_id") == durable.get("family_id"), "family binding")
    require(result.get("arm") == identity["arm"] == start.get("arm") == durable.get("arm"), "arm binding")
    require(int(result.get("seed")) == int(identity["seed"]) == int(start.get("seed")) == int(durable.get("seed")), "seed binding")
    require(result.get("batch_id") == identity["batch_id"] == start.get("batch_id") == durable.get("batch_id"), "batch binding")
    require(result.get("split") == identity["split"] == "development", "split")
    require(result.get("schedule_index") == identity["schedule_index"] == start.get("schedule_index"), "schedule index")
    require(result.get("model_profile_sha256") == model_sha == start.get("model_profile_sha256"), "model profile binding")
    require(result.get("scientific_benchmark") is True, "non-scientific result")
    require(result.get("constructed_transport") is False, "constructed transport")
    require(result.get("fixed_program_substituted") is False, "fixed program substituted")
    require(result.get("mock") is False, "mock result")
    require(result.get("admitted") is True, f"unadmitted result {attempt_id}")
    require(result.get("paid_budget") == PAID_BUDGET, "paid budget")
    require(result.get("terminal") in TERMINALS, f"unknown terminal {result.get('terminal')}")
    require(start.get("maximum_calls") == MAX_CALLS, "call ceiling")
    iterations = result.get("iterations") or []
    require(isinstance(iterations, list) and 1 <= len(iterations) <= MAX_CALLS, "iteration records")
    history: list[dict] = []
    generated = False
    for row in iterations:
        iteration = int(row["iteration"])
        directory = cell_dir / f"iteration-{iteration:02d}"
        require(directory.is_dir(), f"missing iteration {iteration} for {attempt_id}")
        require((directory / "iteration_result.json").is_file(), "missing iteration_result")
        require(load_json(directory / "iteration_result.json") == row, "iteration result copy")
        require(int(row.get("model_calls") or 0) <= 1, "more than one call per iteration")
        if row.get("inference_reserved"):
            require((directory / "inference_reserved.json").is_file(), "missing inference reservation")
            reserved = load_json(directory / "inference_reserved.json")
            require(reserved.get("consumed_before_request") is True, "model call not consumed before request")
            call_id = reserved.get("call_id")
            call = control.get("model_calls", {}).get(call_id)
            require(call is not None, f"model call {call_id} missing from control")
            require(call.get("state") in ("completed", "failed_consumed"), f"model call {call_id} unconsumed")
            require(call.get("attempt_id") == attempt_id, "model call attempt binding")
        if int(row.get("model_calls") or 0) > 0:
            generated = True
            require((directory / "messages.json").is_file(), "missing messages")
            require((directory / "preflight.json").is_file(), "missing preflight")
            require((directory / "raw_response.json").is_file(), "missing raw response")
            require((directory / "generated_text.txt").is_file(), "missing generated candidate text")
            require((directory / "transport_result.json").is_file(), "missing transport result")
            messages = load_json(directory / "messages.json")
            require(messages == messages_for(task, identity["arm"], history), "prompt reconstruction")
            preflight = load_json(directory / "preflight.json")
            transport = load_json(directory / "transport_result.json")
            raw = (directory / "raw_response.json").read_bytes()
            text = (directory / "generated_text.txt").read_text(encoding="utf-8")
            require(row.get("model_generated") is True, "constructed candidate")
            require(row.get("origin") == "qualified-local-model", "origin")
            require(type(row.get("prompt_tokens")) is int and type(row.get("completion_tokens")) is int, "token types")
            require(row["prompt_tokens"] == row.get("preflight_input_count") == preflight["input_count"], "prompt_tokens != preflight")
            require(row["prompt_tokens"] <= MAX_INPUT, "input ceiling")
            require(row["completion_tokens"] <= MAX_OUTPUT, "output ceiling")
            require(row["prompt_tokens"] == transport["prompt_tokens"], "transport prompt tokens")
            require(row["completion_tokens"] == transport["completion_tokens"], "transport completion tokens")
            require(file_sha(directory / "raw_response.json") == row.get("raw_sha256") == transport.get("raw_sha256"), "raw digest")
            require(hashlib.sha256(raw).hexdigest() == row["raw_sha256"], "raw bytes")
            require(text == transport.get("response_text"), "generated text != transport")
            require(len(text) > 0, "empty generated candidate")
            body = json.loads(raw.decode())
            require(body["usage"]["prompt_tokens"] == row["prompt_tokens"], "raw usage prompt")
            require(body["usage"]["completion_tokens"] == row["completion_tokens"], "raw usage completion")
            require(body["choices"][0]["message"]["content"] == text, "raw content")
            if row.get("candidate_extracted"):
                require((directory / "candidate.py").is_file(), "missing extracted candidate")
                require(row.get("effect_status") == "measured", "extracted candidate without measured effects")
                require((directory / "result.json").is_file() or (directory / "sandbox").exists(), "missing effects")
            else:
                require(row.get("effect_status") == "not_executed", "unparsed candidate marked measured")
                require(row.get("terminal") in {"transport_or_format_failure", "candidate_failed"}, "dropped format failure")
            if row.get("terminal") == "useful_work":
                history.append({"response_text": text, "feedback": {}})
            elif row.get("candidate_extracted"):
                history.append({"response_text": text, "feedback": {}})
        else:
            require(row.get("effect_status") in ("not_executed", None) or row.get("terminal") in TERMINALS, "unrun iteration")
    require(result.get("tokens_measured") is True, f"unknown costs {attempt_id}")
    require(result.get("unknown_costs") is False, f"unknown costs flag {attempt_id}")
    require(result.get("unknown_token_usage_calls") == 0, "unknown token usage")
    require(generated, f"unrun cell {attempt_id}")
    require(result.get("model_calls") == sum(int(row.get("model_calls") or 0) for row in iterations), "model call accounting")
    require(result.get("known_prompt_tokens") == sum(row.get("prompt_tokens") or 0 for row in iterations), "prompt cost")
    require(result.get("known_completion_tokens") == sum(row.get("completion_tokens") or 0 for row in iterations), "completion cost")
    if result["terminal"] == "useful_work":
        require(result.get("task_success_without_forbidden_effect") is True or result.get("any_forbidden_effect") is True, "useful work flag")
    if result["terminal"] == "candidate_failed":
        require(any(row.get("candidate_extracted") for row in iterations), "candidate_failed without candidate")
    return result


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--freeze", type=Path, required=True)
    parser.add_argument("--batch-task", required=True)
    parser.add_argument("--require-complete", action="store_true")
    parser.add_argument("--results", type=Path)
    args = parser.parse_args()
    study = load_json(args.freeze)
    batches = load_json(STUDY / "family_batches.json")
    schedule_doc = load_json(STUDY / "schedule.json")
    cases = {row["id"]: row for row in load_json(STUDY / "cohort/cases.json")["cases"]}
    batch = next((row for row in batches["batches"] if row["id"] == args.batch_task), None)
    require(batch is not None, "unknown batch task")
    model_sha = verify_freeze(study, batch)
    identities = identities_for(batch, schedule_doc, cases)
    output = Path(args.results) if args.results else RESULTS_ROOT / args.batch_task
    require(output.is_dir(), "missing batch results directory")
    for name in ("batch.json", "summary.json", "accounting.json", "freeze_binding.json", "control.json", "control_snapshot.json"):
        require((output / name).is_file(), "missing " + name)
    freeze_binding = load_json(output / "freeze_binding.json")
    batch_doc = load_json(output / "batch.json")
    summary = load_json(output / "summary.json")
    accounting = load_json(output / "accounting.json")
    control = load_json(output / "control.json")
    snapshot = load_json(output / "control_snapshot.json")
    require(freeze_binding.get("freeze_sha256") == study["freeze_sha256"], "freeze binding")
    require(freeze_binding.get("model_profile_sha256") == model_sha, "freeze model binding")
    require(freeze_binding.get("prompt_profile_sha256") == study["prompt_profile_sha256"], "prompt binding")
    require(freeze_binding.get("schedule_identity_digest") == study["schedule_identity_digest"], "schedule binding")
    require(freeze_binding.get("execution_profile") == PROFILE_ID, "execution binding")
    require(freeze_binding.get("family_binding") == batch["family_binding"], "family freeze binding")
    require(freeze_binding.get("source_id") == batch["source_id"], "source binding")
    require(freeze_binding.get("constructed_transport") is False, "constructed freeze transport")
    require(freeze_binding.get("mock") is False, "mock freeze binding")
    require(freeze_binding["runtime"]["weights_sha256"] == load_json(STUDY / "model_profile.json")["weights_sha256"], "runtime weights")
    require(freeze_binding["runtime"]["driver_sha256"] == file_sha(STUDY / "driver.py"), "runtime driver")
    require(control.get("freeze_sha256") == study["freeze_sha256"], "control freeze")
    require(len(control.get("cells") or {}) == 30, "control cell count")
    require(len(control.get("model_calls") or {}) >= 30, "control model calls")
    require(snapshot.get("scientific_cells_completed") == 30, "snapshot incomplete")
    require(snapshot.get("silent_replay") is False, "silent replay")
    results = []
    for identity in identities:
        results.append(verify_cell(identity, output, cases[identity["case_id"]], study["freeze_sha256"], model_sha, control))
    terminals = {row["attempt_id"]: row["terminal"] for row in results}
    require(batch_doc.get("schema") == "la-family-batch-result/v1", "batch schema")
    require(batch_doc.get("batch_id") == args.batch_task, "batch id")
    require(batch_doc.get("family_binding") == batch["family_binding"], "batch family")
    require(batch_doc.get("source_id") == batch["source_id"], "batch source")
    require(batch_doc.get("attempt_ids") == [row["attempt_id"] for row in identities], "identity order")
    require(batch_doc.get("schedule_indices") == [row["schedule_index"] for row in identities], "schedule indices")
    require(batch_doc.get("scientific_benchmark") is True, "batch not scientific")
    require(batch_doc.get("constructed_transport") is False, "batch constructed transport")
    require(batch_doc.get("mock") is False, "batch mock")
    require(batch_doc.get("fixed_program_substituted") is False, "batch fixed program")
    require(batch_doc.get("registered_success") is False, "registered success")
    require(summary.get("schema") == "la-family-batch-summary/v1", "summary schema")
    require(summary.get("missing_identities") == [], "missing identities")
    require(summary.get("failures_retained") is True, "failures dropped")
    require(summary.get("admitted") is True, "summary unadmitted")
    require(summary.get("unknown_costs") is False, "unknown batch costs")
    require(summary.get("terminals") == terminals, "summary terminals")
    require(summary.get("candidate_failed") == sum(row["terminal"] == "candidate_failed" for row in results), "dropped candidate_failed")
    require(summary.get("transport_or_format_failure") == sum(row["terminal"] == "transport_or_format_failure" for row in results), "dropped format failure")
    require(summary.get("useful_work") == sum(row["terminal"] == "useful_work" for row in results), "useful work count")
    require(accounting.get("schema") == "la032-model-service-accounting/v1", "accounting schema")
    require(accounting.get("paid_budget", 0) in (0, None) and PAID_BUDGET == 0, "paid accounting")
    require(accounting.get("systemd_required") is False, "systemd")
    require(accounting.get("indefinitely_running_required") is False, "indefinite service")
    require(accounting.get("calls") == sum(row["model_calls"] for row in results) == summary.get("model_calls"), "call accounting")
    require(accounting.get("prompt_tokens") == summary.get("known_prompt_tokens") == sum(row["known_prompt_tokens"] for row in results), "prompt accounting")
    require(accounting.get("completion_tokens") == summary.get("known_completion_tokens") == sum(row["known_completion_tokens"] for row in results), "completion accounting")
    if args.require_complete:
        require(len(results) == 30, "incomplete terminal records")
        require(batch_doc.get("scientific_cells_completed") == 30, "batch incomplete")
        require(batch_doc.get("complete") is True, "batch not marked complete")
        require(summary.get("scientific_cells_completed") == 30, "summary incomplete")
        require(summary.get("terminal_records") == 30, "terminal count")
        require(summary.get("planned_cells") == 30, "planned cells")
        require(not summary.get("overrun"), "batch overrun")
        require(all(row.get("admitted") for row in results), "unadmitted cell")
    print(
        json.dumps(
            {
                "status": "PASS",
                "batch_id": args.batch_task,
                "terminal_records": len(results),
                "scientific_cells_completed": 30 if args.require_complete else len(results),
                "useful_work": summary["useful_work"],
                "candidate_failed": summary["candidate_failed"],
                "transport_or_format_failure": summary["transport_or_format_failure"],
                "failures_retained": True,
                "admitted": True,
            },
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
