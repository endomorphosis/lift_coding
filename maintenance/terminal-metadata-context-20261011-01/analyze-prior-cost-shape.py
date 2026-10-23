"""Read only structured prior receipts; do not inspect transcripts or task files."""
from pathlib import Path
import hashlib
import json

OUT = Path(__file__).resolve().parent
PRIOR = OUT.with_name("terminal-indexed-context-live-20261011-02")
MAX_BYTES = 2_000_000


def read(path):
    if not path.is_file() or path.is_symlink() or path.stat().st_size > MAX_BYTES:
        raise ValueError("bounded regular evidence required")
    raw = path.read_bytes()
    return json.loads(raw), {"path": str(path), "sha256": hashlib.sha256(raw).hexdigest(), "bytes": len(raw)}


def percent(numerator, denominator):
    return round(100 * numerator / denominator, 6) if denominator else None


def main():
    benchmark, benchmark_evidence = read(PRIOR / "benchmark.json")
    known = {row["trial"]: row for row in benchmark["trials"]}
    result, evidence = [], [benchmark_evidence]
    for trial_name in ("mjcf-default-01", "mjcf-compact-01"):
        files = list((PRIOR / "trials" / trial_name / "jobs").glob("*/*/agent/supervisor-result.json"))
        if len(files) != 1:
            raise ValueError("one prior structured supervisor report required")
        report, binding = read(files[0])
        evidence.append(binding)
        benchmark_row = known[trial_name]
        if (benchmark_row["comparison_eligible"] is not True or benchmark_row["usage_complete"] is not True
                or benchmark_row["input_audit"] != "verified_all_observed_model_inputs"):
            raise ValueError("qualified prior benchmark accounting required")
        invocations = report["provider_invocations"]
        if len(invocations) > 16 or len({row["invocation_id"] for row in invocations}) != len(invocations):
            raise ValueError("bounded unique prior invocation population required")
        phases = []
        for invocation in invocations:
            native = invocation["native_rollout_usage"]
            if (native["schema"] != "native-codex-cumulative-usage@1" or native["usage_available"] is not True
                    or native["cache_included_in_input"] is not True):
                raise ValueError("qualified native cumulative counters required")
            usage = {name: native["usage"][name] for name in
                ("input_tokens", "cached_input_tokens", "output_tokens", "reasoning_output_tokens", "total_tokens")}
            if (any(type(value) is not int or value < 0 for value in usage.values())
                    or usage["input_tokens"] + usage["output_tokens"] != usage["total_tokens"]
                    or usage["cached_input_tokens"] > usage["input_tokens"]):
                raise ValueError("invalid cumulative usage arithmetic")
            diagnostics = native.get("tool_diagnostics")
            available = type(diagnostics) is dict
            complete = available and diagnostics.get("tool_event_counts_complete") is True
            observation_fields = ("observed_tool_call_events", "observed_tool_output_events",
                "malformed_json_records", "unclassified_tool_calls", "unclassified_tool_outputs",
                "observed_output_indicator_counts", "complete_output_indicator_counts")
            tool = ({name: diagnostics.get(name) for name in observation_fields} if available else {})
            tool.update(available=available, event_counts_complete=complete,
                output_byte_or_token_sizes_available=False, per_tool_latency_available=False,
                categorized_success_or_exit_status_available=False, root_cause_established=False)
            phases.append({"phase": invocation["phase"], "purpose": invocation["purpose"],
                "status": invocation["status"], "invocation_id": invocation["invocation_id"],
                "elapsed_seconds": invocation["seconds"],
                "initial_router_model_prompt_bytes": invocation["model_prompt_bytes"],
                "usage": usage,
                "input_tokens_excluding_reported_cache": usage["input_tokens"] - usage["cached_input_tokens"],
                "share_of_trial_total_tokens_percent": percent(usage["total_tokens"], benchmark_row["total_tokens"]),
                "cached_share_of_phase_input_tokens_percent": percent(usage["cached_input_tokens"], usage["input_tokens"]),
                "observed_token_count_records": native.get("observed_token_count_records"),
                "token_count_records_are_provider_request_count": False,
                "tools": tool})
        totals = {key: sum(row["usage"][key] for row in phases) for key in
            ("input_tokens", "cached_input_tokens", "output_tokens", "total_tokens")}
        if any(totals[key] != benchmark_row[key] for key in totals):
            raise ValueError("prior aggregate differs from unique native invocation counters")
        totals.update(input_tokens_excluding_reported_cache=totals["input_tokens"]-totals["cached_input_tokens"],
            cached_share_of_input_tokens_percent=percent(totals["cached_input_tokens"], totals["input_tokens"]),
            cached_share_of_total_tokens_percent=percent(totals["cached_input_tokens"], totals["total_tokens"]),
            output_share_of_total_tokens_percent=percent(totals["output_tokens"], totals["total_tokens"]))
        result.append({"trial": trial_name, "profile": benchmark_row["profile"],
            "official_reward": benchmark_row["official_reward"], "solved": benchmark_row["solved"],
            "usage_complete": True, "totals": totals, "phases": phases})
    default, compact = result
    delta_fields = ("total_tokens", "input_tokens", "cached_input_tokens", "input_tokens_excluding_reported_cache", "output_tokens")
    deltas = {key: compact["totals"][key] - default["totals"][key] for key in delta_fields}
    assert deltas["total_tokens"] == sum(deltas[key] for key in ("cached_input_tokens", "input_tokens_excluding_reported_cache", "output_tokens"))
    findings = [
        "Coding accounts for 94.52% and 96.03% of observed total tokens; planning is 5.48% and 3.97% on this pair.",
        "The initial compact coding prompt is smaller, yet its cumulative coding input is larger; one CLI invocation includes an ongoing model/tool session.",
        "Coding has 10 versus 13 observed tool call/output events and 11 versus 14 token-count records. Records are not independently established distinct model requests.",
        "Of the 166,296-token compact increase, 128,768 are cached input, 36,327 input excluding reported cache, and 1,201 output. Cached input is already included in input and total.",
        "Both sessions have one permission_denied lexical output indicator. These summaries do not establish which command emitted it, whether it caused a retry, or its token cost."]
    report = {"schema": "terminal-prior-native-cost-shape@1", "evidence": evidence,
        "measurement_scope": "Unique recorded planning and coding native CLI session cumulative counters; no transcript bodies or hidden benchmark inputs read.",
        "trials": result, "compact_minus_default": deltas, "findings": findings,
        "recommended_next_target": {
            "priority": "Coding interaction and tool-output volume while preserving source and instruction coverage.",
            "reason": "This phase accounts for approximately 95% of total tokens and varies with the session trajectory; metadata factoring changes roughly 1% of a fresh initial task prompt.",
            "first_step": "Retain bounded aggregate tool name/category, output byte counts, exit/status category, duration, and usage-observation deltas without raw tool text, credentials, or task oracle content.",
            "subsequent_experiment": "Evaluate bounded source/retrieval queries and output summarization with explicit truncation and exact expansion access; retain task correctness and complete native session usage as evaluation outcomes.",
            "capsule_policy": "Hold the three currently selected capsules and literal requirements fixed while comparing metadata-only factoring. Do not infer that fewer capsules reduces the number of coding turns.",
            "planning_priority": "Planning context is a secondary target on this pair because its complete observed phase contributes about 24,000 tokens per trial; that is an observational ceiling, not achievable savings.",
            "current_abba_interpretation": "Report both requested and effective metadata profile, complete input size, coding tool/event counts when available, cumulative input/cache/output tokens and success. Two repeats on one task remain observational."},
        "limitations": [
            "One prior pair on one task; no causal attribution to capsule selection or stable mean task cost.",
            "Native session counters aggregate multiple model/tool interactions; the initial router input digest does not cover subsequent prompts or CLI system context.",
            "No per-turn token delta or tool-output byte distribution is available in these structured summaries. Missing metrics remain unknown, not zero.",
            "Observed tool events can contain parallel operations; counts are not a count of independent model turns or evidence of unnecessary work.",
            "Cached tokens count toward the user's total-token metric but do not establish equal monetary cost; billing totals and dollar cost were not verified.",
            "Permission indicators are lexical observations, not evidence of a specific faulty action or root cause.",
            "Local tokenizer/byte reductions cannot be extrapolated directly to cumulative provider-native tokens or task success."],
        "provider_calls": 0, "containers_queried": 0, "source_files_modified": False,
        "transcripts_read": False, "authentication_read": False, "hidden_task_inputs_read": False}
    path = OUT / "cost-shape-analysis.json"
    path.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n")
    print(json.dumps({"output": str(path), "trials": len(result), "deltas": deltas}, sort_keys=True))


if __name__ == "__main__":
    main()
