#!/usr/bin/env python3
"""Read retained trial receipts only; never start a task or contact a provider.

Native counters are not a billing statement. Pending, absent, invalid and
incomplete usage stays unknown; observed failed-attempt costs remain visible.
"""
from __future__ import annotations

import argparse
import copy
import hashlib
import json
import math
from pathlib import Path

TOKENS = ("input_tokens", "cached_input_tokens", "output_tokens", "total_tokens")
MAX_JSON_BYTES = 16 * 1024 * 1024


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


def read_json(path, errors):
    if not path.exists():
        return None
    try:
        if path.is_symlink() or not path.is_file() or path.stat().st_size > MAX_JSON_BYTES:
            raise ValueError("not a bounded regular JSON file")
        raw = path.read_bytes()
        def unique(pairs):
            result = {}
            for key, value in pairs:
                if key in result:
                    raise ValueError("duplicate JSON key")
                result[key] = value
            return result
        def nonfinite(value):
            raise ValueError("nonfinite JSON value")
        value = json.loads(raw, object_pairs_hook=unique, parse_constant=nonfinite)
        if not isinstance(value, dict):
            raise ValueError("JSON object required")
        return value
    except (OSError, ValueError, RecursionError) as error:
        errors.append({"path": str(path), "error_type": type(error).__name__})
        return None


def mapping(value):
    return value if type(value) is dict else {}


def count(value):
    return value if type(value) is int and value >= 0 else None


def finite(value):
    return value if type(value) in (int, float) and math.isfinite(value) else None


def totals(rows, field):
    return {key: sum(row[field][key] for row in rows)
            if rows and all(row[field].get(key) is not None for row in rows) else None
            for key in TOKENS}


def usage(report):
    report = mapping(report)
    raw_rows = report.get("provider_invocations")
    problems, unique, calls, sessions = [], {}, [], set()
    if not isinstance(raw_rows, list):
        problems.append("provider_invocation_population_unavailable")
        raw_rows = []
    for row in raw_rows:
        row = mapping(row)
        identity = row.get("invocation_id")
        if type(identity) is not str or not identity:
            problems.append("invocation_identity_unavailable")
            continue
        if identity in unique:
            if row != unique[identity]:
                problems.append("conflicting_duplicate_invocation")
            continue
        unique[identity] = row
        native = mapping(row.get("native_rollout_usage"))
        values = mapping(native.get("usage"))
        observed = {key: count(values.get(key)) for key in TOKENS}
        all_valid = all(value is not None for value in observed.values())
        provider, schema = row.get("provider"), native.get("schema")
        scope = None
        cache_subset = None
        consistent = False
        complete = False
        if provider == "codex_cli" and schema == "native-codex-cumulative-usage@1":
            scope, cache_subset = "native_session_cumulative", True
            consistent = (all_valid and native.get("cache_included_in_input") is True
                and observed["input_tokens"] + observed["output_tokens"] == observed["total_tokens"]
                and observed["cached_input_tokens"] <= observed["input_tokens"])
            complete = consistent and native.get("usage_available") is True and native.get("task_complete_observed") is True
            session = native.get("thread_id")
            if session:
                session_key = (provider, session)
                if session_key in sessions:
                    problems.append("native_session_reused_across_invocations")
                sessions.add(session_key)
        elif provider == "grok_cli" and schema == "native-grok-final-usage@1":
            scope, cache_subset = "native_final_envelope", False
            write = count(values.get("cache_write_input_tokens"))
            consistent = (all_valid and write is not None and native.get("cache_included_in_input") is False
                and native.get("totals_scope") == scope
                and observed["input_tokens"] + observed["cached_input_tokens"] + write
                    + observed["output_tokens"] == observed["total_tokens"])
            complete = (consistent and native.get("usage_available") is True
                and native.get("task_complete_observed") is True and native.get("usage_complete_observed") is True)
        calls.append({"invocation_id": identity, "phase": row.get("phase"),
            "provider": provider, "model": row.get("model"), "status": row.get("status"),
            "native_session_sha256": digest(native["thread_id"].encode())
                if type(native.get("thread_id")) is str else None,
            "native_scope": scope, "cache_included_in_input": cache_subset,
            "native_session_complete": native.get("task_complete_observed"),
            "usage_consistent": consistent, "usage_complete": complete,
            "observed_tokens": observed,
            "cache_write_input_tokens": count(values.get("cache_write_input_tokens")),
            "input_bytes": {key: count(row.get(key)) for key in
                ("native_prompt_bytes", "router_prompt_bytes", "model_prompt_bytes")},
            "input_sha256": {key: row.get(key) for key in
                ("native_prompt_sha256", "router_prompt_sha256", "model_prompt_sha256")}})
    if report.get("unreceipted_provider_attempt"):
        problems.append("unreceipted_provider_attempt")
    if not calls:
        problems.append("no_observed_native_usage")
    scope_values = {(call["native_scope"], call["cache_included_in_input"]) for call in calls}
    if len(scope_values) > 1:
        problems.append("mixed_native_scopes")
    complete = bool(calls) and not problems and all(call["usage_complete"] for call in calls)
    observed = totals(calls, "observed_tokens")
    # Known subtotal is useful for partial runs, but must not masquerade as a
    # lower bound when identities or repeated cumulative sessions conflict.
    ambiguous = any("duplicate" in p or "reused" in p or "identity" in p for p in problems)
    subtotal = {key: sum(call["observed_tokens"][key] for call in calls
                        if call["observed_tokens"][key] is not None)
                if not ambiguous and any(call["observed_tokens"][key] is not None for call in calls)
                else None for key in TOKENS}
    return {"provider_invocations_observed": len(calls), "calls": calls,
        "planning_invocations_observed": sum(call["phase"] == "planning" for call in calls),
        "coding_invocations_observed": sum(call["phase"] == "coding" for call in calls),
        "complete": complete, "problems": problems,
        "observed_tokens": observed, "known_token_subtotal": subtotal,
        "complete_tokens": observed if complete else dict.fromkeys(TOKENS),
        "cache_included_in_input": next(iter(scope_values))[1] if len(scope_values) == 1 else None,
        "billing_total_verified": False, "dollar_cost": None}


def normalize_config(config):
    value = copy.deepcopy(config)
    value.pop("jobs_dir", None)
    for agent in value.get("agents", []):
        agent.get("kwargs", {}).pop("semantic_context_profile", None)
    excluded = value.get("retry", {}).get("exclude_exceptions")
    if type(excluded) is list:
        value["retry"]["exclude_exceptions"] = sorted(set(excluded))
    return value


def projection(report):
    initial = mapping(mapping(report).get("initial_context"))
    selected = mapping(initial.get("worker_projection"))
    return {"worker_payload_bytes": count(initial.get("worker_payload_bytes")),
        "full_capsules": count(initial.get("full_capsules")),
        "worker_capsules": count(initial.get("worker_capsules")),
        **{key: count(selected.get(key)) for key in ("full_capsule_count",
            "selected_capsule_count", "omitted_capsule_count", "max_capsules", "max_bytes")},
        "selector": selected.get("selector"), "counts_source": "initial_context.worker_projection"}


def attempt_row(name, native, report, *, native_present, source):
    native, report = mapping(native), mapping(report)
    rewards = mapping(mapping(native.get("verifier_result")).get("rewards"))
    reward = finite(rewards.get("reward"))
    accounting = usage(report)
    audit = mapping(report.get("context_input_audit"))
    error = mapping(report.get("error"))
    error_phase = report.get("error_phase") or report.get("failed_phase") or report.get("failure_phase")
    genuine_model = report.get("implementation_route") == "model_router" and accounting["coding_invocations_observed"] > 0
    before_model = (bool(error) and error_phase in {"prepare", "initial_context"}
        and report.get("provider_invocations") == [] and not report.get("unreceipted_provider_attempt"))
    outcome_class = ("predispatch_pipeline_failure" if before_model else
        "model_implementation_attempt" if genuine_model else
        "provider_attempt_without_coding" if accounting["provider_invocations_observed"] else
        "provider_free_candidate_attempt" if report.get("implementation_route") in
            {"doctor_candidate", "doctor_contract_candidate"} else "unclassified_or_unobserved")
    return {"attempt": name, "source": source, "native_result_present": native_present,
        "task": native.get("task_name"), "official_reward": reward,
        "solved": reward >= 1 if reward is not None else None,
        "exception_type": mapping(native.get("exception_info")).get("exception_type"),
        "task_completed": report.get("task_completed"),
        "implementation_route": report.get("implementation_route"),
        "genuine_model_implementation_observed": genuine_model,
        "outcome_class": outcome_class,
        "failure_before_provider_planning_reported": before_model,
        "supervisor_error": {key: error.get(key) for key in ("type", "message")},
        "provider_usage": accounting, "projection": projection(report),
        "context_input_audit": {key: audit.get(key) for key in ("status", "reason", "seconds",
            "any_native_input_verified", "any_model_input_verified", "all_observed_coding_inputs_verified")},
        "semantic_context_profile": report.get("semantic_context_profile"),
        "supervisor_seconds": finite(report.get("seconds")), "phases_seconds": report.get("phases"),
        "failure_phase": error_phase,
        "worker_cleanup_returncode": report.get("worker_cleanup_returncode")}


def collect_trial(root, selected, protocol):
    errors = []
    folder = root / "trials" / selected["name"]
    prepared = mapping(read_json(folder / "preparation.json", errors))
    config = mapping(read_json(folder / "config.json", errors))
    receipt = mapping(read_json(folder / "receipt.json", errors))
    frozen = mapping(protocol.get("preparations", {}).get(selected["task"]))
    config_hash = digest((folder / "config.json").read_bytes()) if config else None
    controls = {"configuration_file_matches_preparation": bool(config) and config_hash == prepared.get("config_sha256"),
        "normalized_configuration_matches_frozen_protocol": bool(config) and normalize_config(config) == frozen.get("normalized_configuration"),
        "archive_matches_protocol": bool(prepared) and prepared.get("archive_sha256") == frozen.get("archive_sha256"),
        "task_input_pins_match_protocol": bool(prepared) and prepared.get("task_input_sha256") == frozen.get("task_input_sha256"),
        "host_adapter_pins_match_protocol": bool(prepared) and prepared.get("host_source_sha256") == frozen.get("host_source_sha256"),
        "selected_profile_matches_preparation": prepared.get("semantic_context_profile") == selected["semantic_context_profile"],
        "selected_profile_matches_configuration": bool(config.get("agents")) and mapping(config["agents"][0].get("kwargs")).get("semantic_context_profile") == selected["semantic_context_profile"],
        "source_commit": protocol.get("source_commit"), "archive_sha256": prepared.get("archive_sha256"),
        "model": prepared.get("model"), "reasoning_effort": prepared.get("reasoning_effort"),
        "cli_version": prepared.get("cli_version"), "resource_profile": prepared.get("resource_profile"),
        "original_task_inputs_unchanged_receipt": receipt.get("original_task_inputs_unchanged"),
        "complete_single_trial_receipt": receipt.get("complete_single_trial_receipt"),
        "note": "Compares retained pins/configuration; does not reread solutions, verifier files, source checkout or archive."}
    attempts, seen = [], set()
    job = folder / "jobs" / str(config.get("job_name", "unconfigured"))
    if job.is_dir():
        for path in sorted(job.iterdir()):
            if not path.is_dir() or path.is_symlink():
                continue
            native = read_json(path / "result.json", errors)
            report = read_json(path / "agent/supervisor-result.json", errors)
            if native is not None or report is not None:
                attempts.append(attempt_row(path.name, native, report,
                    native_present=native is not None, source=str(path)))
                seen.add(path.name)
    # A retained receipt can outlive deleted native directories. Never count it
    # a second time when raw results are also present.
    for row in receipt.get("trials", []):
        if not isinstance(row, dict) or row.get("trial") in seen:
            continue
        native = {"task_name": row.get("task"), "verifier_result": {"rewards": row.get("reward")},
            "exception_info": {"exception_type": row.get("exception_type")}}
        attempts.append(attempt_row(row.get("trial"), native, row.get("supervisor"),
            native_present=True, source=str(folder / "receipt.json")))
        seen.add(row.get("trial"))
    started = (folder / "invocation.json").exists() or job.exists()
    final = bool(receipt.get("native_job_result_present")) or (job / "result.json").is_file()
    if not started and not attempts and not receipt:
        state = "pending"
    elif final and attempts and all(row["native_result_present"] for row in attempts):
        state = "finished"
    else:
        state = "started_or_partial"
    usage_complete = bool(attempts) and final and not errors and all(row["provider_usage"]["complete"] for row in attempts)
    cumulative_sessions = [call["native_session_sha256"] for row in attempts
        for call in row["provider_usage"]["calls"] if call["native_session_sha256"] is not None]
    sessions_distinct = len(cumulative_sessions) == len(set(cumulative_sessions))
    usage_complete = usage_complete and sessions_distinct
    controls.update(
        observed_tasks_match_selection=all(row["task"] in {selected["task"], "terminal-bench/" + selected["task"]} for row in attempts) if attempts else None,
        observed_profiles_match_selection=all(row["semantic_context_profile"] == selected["semantic_context_profile"] for row in attempts) if attempts else None,
        observed_models_match_selection=all(call["model"] == prepared.get("model")
            for row in attempts for call in row["provider_usage"]["calls"])
            if any(row["provider_usage"]["calls"] for row in attempts) else None,
        cumulative_sessions_distinct_across_attempts=sessions_distinct if attempts else None)
    token_rows = [{"tokens": row["provider_usage"]["complete_tokens"]} for row in attempts]
    complete_tokens = totals(token_rows, "tokens") if usage_complete else dict.fromkeys(TOKENS)
    solved = True if any(row["solved"] is True for row in attempts) else False if final and attempts and all(row["solved"] is False for row in attempts) else None
    comparison_exclusions = []
    if state != "finished":
        comparison_exclusions.append("trial_not_finished")
    if not usage_complete:
        comparison_exclusions.append("complete_native_usage_unavailable")
    if not attempts or not all(row["genuine_model_implementation_observed"] for row in attempts):
        comparison_exclusions.append("model_implementation_not_observed_for_all_attempts")
    if not attempts or not all(row["context_input_audit"]["all_observed_coding_inputs_verified"] is True for row in attempts):
        comparison_exclusions.append("exact_model_inputs_not_verified_for_all_attempts")
    if any(type(value) is bool and value is False for key, value in controls.items() if key != "complete_single_trial_receipt"):
        comparison_exclusions.append("declared_or_observed_controls_differ")
    return {**selected, "state": state, "attempt_count_observed": len(attempts), "attempts": attempts,
        "model_context_comparison_eligible": not comparison_exclusions,
        "model_context_comparison_exclusions": comparison_exclusions,
        "solved": solved, "usage_complete": usage_complete, "complete_tokens": complete_tokens,
        "known_token_subtotal": {key: sum(row["provider_usage"]["known_token_subtotal"][key]
            for row in attempts if row["provider_usage"]["known_token_subtotal"][key] is not None)
            if sessions_distinct and any(row["provider_usage"]["known_token_subtotal"][key] is not None for row in attempts) else None for key in TOKENS},
        "tokens_per_solved_task": complete_tokens["total_tokens"] if usage_complete and solved is True else None,
        "frozen_controls": controls, "read_errors": errors}


def summarize_arm(rows):
    complete = bool(rows) and all(row["usage_complete"] and row["state"] == "finished" for row in rows)
    outcomes_known = bool(rows) and all(type(row["solved"]) is bool for row in rows)
    solved = sum(row["solved"] for row in rows) if outcomes_known else None
    aggregate = totals(rows, "complete_tokens") if complete else dict.fromkeys(TOKENS)
    return {"planned_trials": len(rows), "finished_trials": sum(row["state"] == "finished" for row in rows),
        "predispatch_pipeline_failures": sum(attempt.get("outcome_class") == "predispatch_pipeline_failure"
            for row in rows for attempt in row.get("attempts", [])),
        "model_implementation_attempts_observed": sum(attempt.get("genuine_model_implementation_observed") is True
            for row in rows for attempt in row.get("attempts", [])),
        "usage_complete": complete, "solved_tasks": solved, "outcomes_complete": outcomes_known,
        "complete_tokens_all_attempts": aggregate,
        "known_total_token_subtotal": sum(row["known_token_subtotal"]["total_tokens"] for row in rows
            if row["known_token_subtotal"]["total_tokens"] is not None)
            if any(row["known_token_subtotal"]["total_tokens"] is not None for row in rows) else None,
        "tokens_per_solved_task_including_failures": aggregate["total_tokens"] / solved
            if complete and outcomes_known and solved > 0 else None,
        "ratio_undefined_reason": None if complete and outcomes_known and solved > 0
            else "incomplete_usage_or_outcomes" if not (complete and outcomes_known) else "zero_solved_tasks"}


def aggregate(root):
    errors = []
    protocol = read_json(root / "comparison-protocol.json", errors)
    if protocol is None:
        raise ValueError("comparison protocol unavailable: " + repr(errors))
    rows = [collect_trial(root, row, protocol) for row in protocol["trials"]]
    profiles = sorted({row["semantic_context_profile"] for row in rows})
    return {"schema": "terminal-indexed-context-retained-aggregation@1",
        "protocol_sha256": digest((root / "comparison-protocol.json").read_bytes()),
        "aggregator_sha256": digest(Path(__file__).read_bytes()), "provider_calls_by_aggregator": 0,
        "source_commit": protocol.get("source_commit"), "trials": rows,
        "arms": {profile: summarize_arm([row for row in rows if row["semantic_context_profile"] == profile]) for profile in profiles},
        "caveats": ["Unknown usage/outcomes are never replaced with zero.",
            "All retained attempts, including failed attempts, enter complete token numerators.",
            "Codex cached input is a subset of input; it is never added again to total tokens.",
            "Native session completion differs from task correctness; official reward determines success.",
            "Exact-input audit status is separate from native token completeness and verifier reward.",
            "A verifier reward after predispatch pipeline failure is retained, but does not measure model implementation quality or token efficiency.",
            "Local capsule counts and prompt bytes are not cumulative model token usage.",
            "Native counters do not establish billing cost or unreported auxiliary-model usage.",
            "One repetition per task/profile and no native baseline: no statistical or causal advantage claimed.",
            "Retained configuration pins are compared; current source/archive/input files are not rehashed."]}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parent)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    report = aggregate(args.root.resolve())
    output = args.output or args.root / "aggregate.json"
    output.write_text(json.dumps(report, indent=2, sort_keys=True, allow_nan=False) + "\n")
    print(json.dumps({"output": str(output), "trials": [{"name": row["name"], "state": row["state"],
        "solved": row["solved"], "complete_tokens": row["complete_tokens"]} for row in report["trials"]],
        "arms": report["arms"]}, indent=2))


if __name__ == "__main__":
    main()
