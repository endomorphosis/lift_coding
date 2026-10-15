"""Current structured phase usage and tool-event shape; safe during a campaign.

Only protocol, retained reports and accounting receipts are read. This never
loads provider transcripts, raw prompts, benchmark tests, solutions or auth.
Rerun after remaining trials finish; earlier prior-campaign analysis is intact.
"""
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path

from aggregate_trials import aggregate

ROOT = Path(__file__).resolve().parent
TOKEN_FIELDS = ("input_tokens", "cached_input_tokens", "output_tokens", "total_tokens")


def percentage(numerator, denominator):
    return round(100 * numerator / denominator, 6) if denominator else None


def load_report(path):
    if not path.is_file() or path.is_symlink() or path.stat().st_size > 2_000_000:
        raise ValueError("bounded regular supervisor report required")
    raw = path.read_bytes()
    return json.loads(raw), {"path": str(path.relative_to(ROOT)), "sha256": hashlib.sha256(raw).hexdigest()}


def phase_shape(invocation, expected_usage):
    rollout = invocation.get("native_rollout_usage") or {}
    native = rollout.get("usage") or {}
    usage = {key: native.get(key) for key in TOKEN_FIELDS}
    known = (rollout.get("usage_available") is True and rollout.get("cache_included_in_input") is True
        and all(type(value) is int and value >= 0 for value in usage.values())
        and usage == expected_usage)
    if known:
        if (usage["input_tokens"] + usage["output_tokens"] != usage["total_tokens"]
                or usage["cached_input_tokens"] > usage["input_tokens"]):
            raise ValueError("native arithmetic differs from verified accounting")
    tools = rollout.get("tool_diagnostics")
    available = isinstance(tools, dict)
    tools = tools if available else {}
    metadata = invocation.get("semantic_metadata_view")
    view = None
    if isinstance(metadata, dict):
        view = {key: metadata.get(key) for key in ("schema", "selected_mode", "fallback_reason",
            "native_complete_bytes", "candidate_complete_bytes", "selected_complete_bytes",
            "native_complete_sha256", "selected_complete_sha256")}
        view["within_invocation_selected_bytes_saved"] = (
            view["native_complete_bytes"] - view["selected_complete_bytes"]
            if type(view["native_complete_bytes"]) is int and type(view["selected_complete_bytes"]) is int else None)
    return {"phase": invocation.get("phase"), "purpose": invocation.get("purpose"),
        "invocation_id": invocation.get("invocation_id"), "elapsed_seconds": invocation.get("seconds"),
        "native_usage_matches_verified_accounting": known, "usage": usage,
        "input_tokens_excluding_reported_cache": usage["input_tokens"] - usage["cached_input_tokens"] if known else None,
        "cached_share_of_input_percent": percentage(usage["cached_input_tokens"], usage["input_tokens"]) if known else None,
        "observed_token_count_records": rollout.get("observed_token_count_records"),
        "token_count_records_are_verified_distinct_provider_requests": False,
        "initial_router_model_prompt_bytes": invocation.get("model_prompt_bytes"),
        "metadata_factoring": view,
        "tools": {"diagnostics_available": available, "event_counts_complete": tools.get("tool_event_counts_complete"),
            "observed_tool_call_events": tools.get("observed_tool_call_events"),
            "observed_tool_output_events": tools.get("observed_tool_output_events"),
            "malformed_json_records": tools.get("malformed_json_records"),
            "unclassified_tool_calls": tools.get("unclassified_tool_calls"),
            "unclassified_tool_outputs": tools.get("unclassified_tool_outputs"),
            "lexical_output_indicators": tools.get("observed_output_indicator_counts"),
            "output_size_measurements_available": False, "per_tool_usage_deltas_available": False,
            "per_tool_latency_available": False, "root_cause_established": False}}


def count_phase(rows, phase, field):
    selected = [item for row in rows for item in row["phases"] if item["phase"] == phase]
    values = [item["tools"].get(field) for item in selected]
    return (sum(values) if selected and all(type(value) is int for value in values)
            and all(item["tools"]["event_counts_complete"] is True for item in selected) else None)


def main():
    retained = aggregate(ROOT)
    rows, bindings = [], []
    for trial in retained["trials"]:
        row = {key: trial.get(key) for key in ("name", "task", "repeat", "state", "semantic_metadata_view",
            "semantic_context_profile", "usage_complete", "solved", "complete_tokens",
            "requested_arm_comparison_eligible", "effective_treatment_comparison_eligible", "effective_treatment_observed")}
        row.update(attempts=[], complete_phase_usage_known=False)
        if trial["state"] != "finished":
            row["reason"] = "Trial is pending or active; missing usage and event counts remain unknown."
            rows.append(row)
            continue
        for attempt in trial["attempts"]:
            path = Path(attempt["source"]) / "agent/supervisor-result.json"
            if not path.is_relative_to(ROOT / "trials"):
                raise ValueError("attempt report must belong to this campaign")
            report, binding = load_report(path)
            bindings.append(binding)
            expected_calls = {call["invocation_id"]: call for call in attempt["provider_usage"]["calls"]}
            native_invocations = report.get("provider_invocations") or []
            if (len(native_invocations) > 16 or len({call["invocation_id"] for call in native_invocations}) != len(native_invocations)):
                raise ValueError("bounded unique invocation population required")
            phases = [phase_shape(inv, expected_calls.get(inv["invocation_id"], {}).get("observed_tokens"))
                      for inv in native_invocations]
            projection = attempt.get("projection") or {}
            row["attempts"].append({"attempt": attempt["attempt"], "official_reward": attempt.get("official_reward"),
                "selected_capsules": projection.get("selected_capsule_count"),
                "worker_payload_bytes": projection.get("worker_payload_bytes"),
                "input_audit_status": attempt.get("context_input_audit", {}).get("status"),
                "metadata_dispatch_status": attempt.get("semantic_metadata_dispatch", {}).get("status"),
                "phases": phases})
        phases = [phase for attempt in row["attempts"] for phase in attempt["phases"]]
        row["complete_phase_usage_known"] = (bool(phases) and row["usage_complete"] is True
            and all(phase["native_usage_matches_verified_accounting"] for phase in phases))
        if row["complete_phase_usage_known"]:
            if any(sum(phase["usage"][key] for phase in phases) != row["complete_tokens"][key] for key in TOKEN_FIELDS):
                raise ValueError("phase totals differ from verified trial accounting")
            row["complete_tokens"]["input_tokens_excluding_reported_cache"] = (
                row["complete_tokens"]["input_tokens"] - row["complete_tokens"]["cached_input_tokens"])
            for phase in phases:
                phase["share_of_trial_total_tokens_percent"] = percentage(phase["usage"]["total_tokens"], row["complete_tokens"]["total_tokens"])
        row["coding_tool_call_events"] = count_phase(row["attempts"], "coding", "observed_tool_call_events")
        row["coding_tool_output_events"] = count_phase(row["attempts"], "coding", "observed_tool_output_events")
        row["fixed_three_capsules_observed"] = bool(row["attempts"]) and all(item["selected_capsules"] == 3 for item in row["attempts"])
        rows.append(row)
    pairs = []
    for task, repeat in sorted({(row["task"], row["repeat"]) for row in rows}):
        selected = [row for row in rows if row["task"] == task and row["repeat"] == repeat]
        by_mode = {row["semantic_metadata_view"]: row for row in selected}
        if set(by_mode) != {"legacy", "common-bindings@1"}:
            raise ValueError("both declared arms required for each repeat")
        baseline, factored = by_mode["legacy"], by_mode["common-bindings@1"]
        complete = all(row["complete_phase_usage_known"] and row["effective_treatment_comparison_eligible"] for row in selected)
        pair = {"task": task, "repeat": repeat, "both_trials_complete_and_eligible": complete,
            "baseline_trial": baseline["name"], "factored_trial": factored["name"]}
        if complete:
            delta = {key: factored["complete_tokens"][key] - baseline["complete_tokens"][key]
                     for key in (*TOKEN_FIELDS, "input_tokens_excluding_reported_cache")}
            if delta["total_tokens"] != sum(delta[key] for key in ("cached_input_tokens", "input_tokens_excluding_reported_cache", "output_tokens")):
                raise ValueError("pair delta arithmetic differs")
            pair.update(factored_minus_baseline_tokens=delta,
                total_token_change_percent=percentage(delta["total_tokens"], baseline["complete_tokens"]["total_tokens"]),
                coding_tool_calls={"baseline": baseline["coding_tool_call_events"], "factored": factored["coding_tool_call_events"]},
                fixed_three_capsules_preserved=all(row["fixed_three_capsules_observed"] for row in selected),
                both_solved=all(row["solved"] is True for row in selected), causal_improvement_established=False)
        else:
            pair["reason"] = "Incomplete or ineligible pair; no token-change estimate is assigned."
        pairs.append(pair)
    complete = all(row["state"] == "finished" and row["complete_phase_usage_known"] for row in rows)
    report = {"schema": "terminal-current-native-cost-shape@1", "observed_at": datetime.now(timezone.utc).isoformat(),
        "protocol_sha256": retained["protocol_sha256"], "source_commit": retained["source_commit"],
        "aggregator_sha256": retained["aggregator_sha256"], "report_bindings": bindings,
        "planned_trials": len(rows), "finished_trials": sum(row["state"] == "finished" for row in rows),
        "remaining_trials": [row["name"] for row in rows if row["state"] != "finished"],
        "all_trial_phase_usage_complete": complete, "trials": rows, "repeat_pairs": pairs,
        "interpretation": [
            "Compare cumulative coding usage alongside observed tool events; one native CLI invocation can contain multiple model/tool interactions.",
            "Within-invocation metadata factoring bytes compare a candidate against its own verified baseline. Between-run initial prompts may differ because independent planner output and opaque identities differ.",
            "Fewer observed tool events accompanying lower cumulative tokens do not establish which operations were avoided or why the trajectory differed.",
            "Keep three selected capsules and literal requirements fixed; metadata factoring does not authorize source or instruction omission.",
            "Separate cached input from input excluding reported cache when interpreting trajectory changes; cached tokens remain included in total input."],
        "limitations": [
            "Two repeats on one task are observational and do not establish statistical or causal improvement.",
            "Pending trials and absent usage/tool metrics are unknown, never zero; incomplete pairs receive no delta.",
            "Token-count records are not verified distinct provider request counts, and tool events can batch operations.",
            "No raw transcript, per-tool output size, tool latency or per-turn usage deltas were inspected or reconstructed.",
            "Structured lexical error indicators do not establish root cause or the token cost of any command.",
            "Initial router task-input auditing excludes the CLI system prompt and subsequent tool turns; cumulative native usage has a broader scope.",
            "Billing totals and monetary costs remain unverified; lower total tokens need not imply the same proportional dollar reduction."],
        "provider_calls": 0, "containers_queried": 0, "source_files_modified": False,
        "transcripts_read": False, "authentication_read": False, "hidden_task_inputs_read": False}
    target = ROOT / "current-cost-shape-analysis.json"
    temporary = target.with_suffix(".tmp")
    temporary.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n")
    temporary.replace(target)
    print(json.dumps({"output": str(target), "finished_trials": report["finished_trials"],
        "remaining_trials": report["remaining_trials"], "repeat_pairs": pairs}, sort_keys=True))


if __name__ == "__main__":
    main()
