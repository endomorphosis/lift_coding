#!/usr/bin/env python3
"""Independently reconcile the four native ABBA trials and exported benchmark.

Standard library only. Does not import campaign accounting or frozen source,
run a provider/container, read hidden task tests, or modify trial evidence.
Absent results/exports are pending by default. --require-complete returns a
nonzero exit status unless every check has passed on completed evidence.
"""
from __future__ import annotations

import argparse
import copy
import csv
import hashlib
import json
import math
from pathlib import Path
import re
import subprocess


TOKEN_KEYS = ("input_tokens", "cached_input_tokens", "output_tokens", "total_tokens")
MAX_JSON_BYTES = 32 * 1024 * 1024
MODES = ("legacy", "common-bindings@1", "common-bindings@1", "legacy")


def require(condition, code):
    if not condition:
        raise ValueError(code)


def digest(path):
    require(path.is_file() and not path.is_symlink(), "regular_hash_input_required")
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def read(path):
    require(path.is_file() and not path.is_symlink() and path.stat().st_size <= MAX_JSON_BYTES,
            "bounded_regular_json_required")
    def pairs(items):
        result = {}
        for key, value in items:
            require(key not in result, "duplicate_json_key")
            result[key] = value
        return result
    def constant(_value):
        raise ValueError("nonfinite_json")
    value = json.loads(path.read_bytes(), object_pairs_hook=pairs, parse_constant=constant)
    require(type(value) is dict, "json_object_required")
    return value


def native_totals(report, seen_sessions):
    """Sum only complete native cumulative receipts, once per invocation."""
    rows = report.get("provider_invocations")
    require(type(rows) is list and 0 < len(rows) <= 4096, "native_receipts_required")
    require(not report.get("unreceipted_provider_attempt"), "unreceipted_provider_attempt")
    unique, totals = {}, dict.fromkeys(TOKEN_KEYS, 0)
    for row in rows:
        require(type(row) is dict, "native_receipt_object_required")
        identity = row.get("invocation_id")
        require(type(identity) is str and 0 < len(identity) <= 4096, "invocation_identity_required")
        if identity in unique:
            require(row == unique[identity], "conflicting_invocation_copy")
            continue
        unique[identity] = row
        native = row.get("native_rollout_usage")
        require(row.get("provider") == "codex_cli" and type(native) is dict
            and native.get("schema") == "native-codex-cumulative-usage@1", "native_codex_usage_required")
        require(native.get("usage_available") is True and native.get("task_complete_observed") is True
            and native.get("cache_included_in_input") is True, "native_usage_incomplete")
        session = native.get("thread_id")
        require(type(session) is str and 0 < len(session) <= 4096, "native_session_identity_required")
        require(session not in seen_sessions, "native_session_reused_across_invocations_or_trials")
        seen_sessions.add(session)
        values = native.get("usage")
        require(type(values) is dict and all(type(values.get(key)) is int and values[key] >= 0
            for key in TOKEN_KEYS), "nonnegative_native_counters_required")
        require(values["input_tokens"] + values["output_tokens"] == values["total_tokens"]
            and values["cached_input_tokens"] <= values["input_tokens"], "native_counter_algebra_differs")
        for key in TOKEN_KEYS:
            totals[key] += values[key]
    return totals, list(unique.values())


def exact_input_modes(report, calls, requested):
    """Correlate the independently retained audit to each actual coding input."""
    coding = [row for row in calls if row.get("phase") == "coding"]
    require(coding and report.get("implementation_route") == "model_router", "model_coding_required")
    audit = report.get("context_input_audit")
    require(type(audit) is dict and audit.get("status") == "verified_all_observed_model_inputs"
        and audit.get("all_observed_coding_inputs_verified") is True
        and audit.get("read_errors") == [], "exact_input_audit_required")
    ids = {row["invocation_id"] for row in coding}
    observed, matches = audit.get("invocations"), audit.get("matches")
    require(type(observed) is list and type(matches) is list, "audit_invocation_population_required")
    require(len(observed) == len(coding) and all(type(row) is dict for row in observed)
        and {row.get("invocation_id") for row in observed} == ids
        and type(audit.get("coding_receipts_seen")) is int and audit["coding_receipts_seen"] == len(coding)
        and type(audit.get("usable_coding_receipts")) is int and audit["usable_coding_receipts"] == len(coding),
        "audit_population_differs")
    declaration = report.get("semantic_metadata_view")
    require((declaration is None if requested == "legacy" else type(declaration) is dict
        and declaration.get("requested_mode") == requested), "requested_metadata_mode_differs")
    modes, fallback_reasons = [], []
    for row in coding:
        identity = row["invocation_id"]
        require(type(row.get("model_prompt_sha256")) is str
            and re.fullmatch("[a-f0-9]{64}", row["model_prompt_sha256"]) is not None
            and type(row.get("model_prompt_bytes")) is int and 0 < row["model_prompt_bytes"] <= 2_000_000,
            "bounded_coding_input_identity_required")
        records = [item for item in observed if item.get("invocation_id") == identity]
        evidence = [item for item in matches if type(item) is dict and item.get("invocation_id") == identity]
        require(len(records) == 1 and records[0].get("status") == "verified_exact_model_input"
            and records[0].get("model_input_verified") is True and evidence, "audited_coding_invocation_missing")
        for item in evidence:
            checks = item.get("model_input_checks")
            require(item.get("model_input_verified") is True and type(checks) is dict and checks
                and all(value is True for value in checks.values())
                and item.get("model_prompt_sha256") == row.get("model_prompt_sha256")
                and type(item.get("model_prompt_bytes")) is int
                and item.get("model_prompt_bytes") == row.get("model_prompt_bytes"), "audit_input_binding_differs")
        selection = row.get("semantic_metadata_view")
        if requested == "legacy":
            require(selection is None, "unexpected_metadata_treatment_in_baseline")
            modes.append("legacy")
            continue
        require(type(selection) is dict and selection.get("schema") == "supervisor-semantic-metadata-selection@1"
            and selection.get("selected_complete_sha256") == row.get("model_prompt_sha256")
            and type(selection.get("selected_complete_bytes")) is int
            and selection["selected_complete_bytes"] == row.get("model_prompt_bytes"), "metadata_input_binding_differs")
        require(all(item["model_input_checks"].get("semantic_metadata_selection_receipt") is True for item in evidence),
            "metadata_selection_not_independently_reconstructed")
        mode, fallback = selection.get("selected_mode"), selection.get("fallback_reason")
        require(mode in ("legacy", "common-bindings@1"), "unknown_effective_mode")
        require(fallback == (None if mode == "common-bindings@1" else
            "complete_input_not_smaller_under_bytes_and_proxy"), "fallback_reason_differs")
        modes.append(mode)
        if fallback is not None:
            fallback_reasons.append(fallback)
    return coding, sorted(set(modes)), sorted(set(fallback_reasons))


def fixed_config(config):
    normalized = copy.deepcopy(config)
    normalized.pop("jobs_dir", None)
    normalized.pop("job_name", None)
    require(type(normalized.get("agents")) is list and len(normalized["agents"]) == 1, "one_agent_required")
    normalized["agents"][0]["kwargs"].pop("semantic_metadata_view", None)
    excluded = normalized.get("retry", {}).get("exclude_exceptions")
    if type(excluded) is list:
        normalized["retry"]["exclude_exceptions"] = sorted(set(excluded))
    return normalized


def verify(root):
    result = {"schema": "terminal-metadata-independent-benchmark-verification@1", "status": "pending",
        "provider_calls": 0, "containers_launched": 0, "hidden_task_inputs_read": False,
        "source_imported": False, "source_audit_rerun": False, "archive_members_reextracted": False,
        "pending": [], "failures": [], "trials": [], "checks": {}}
    try:
        protocol = read(root / "comparison-protocol.json")
        launcher = read(root / "launcher-protocol.json")
        selected = protocol["trials"]
        require(len(selected) == 4 and tuple(row["semantic_metadata_view"] for row in selected) == MODES
            and [row["repeat"] for row in selected] == [1, 1, 2, 2]
            and len({row["name"] for row in selected}) == 4
            and len({row["task"] for row in selected}) == 1, "four_trial_abba_protocol_required")
        require(protocol["source_commit"] == launcher["source_head"]
            and protocol["archive_sha256"] == launcher["archive_sha256"], "launcher_protocol_pins_differ")
        result["protocol_sha256"] = digest(root / "comparison-protocol.json")
        result["source_commit"] = protocol["source_commit"]
        result["checks"]["four_trial_abba_protocol"] = True
        available = {}
        for item in selected:
            folder = root / "trials" / item["name"]
            config = read(folder / "config.json")
            prepared = read(folder / "preparation.json")
            frozen = protocol["preparations"][item["task"]]
            require(digest(folder / "config.json") == prepared["config_sha256"], "configuration_hash_differs")
            require(fixed_config(config) == frozen["normalized_configuration"], "nonexperimental_configuration_differs")
            require(config["jobs_dir"] == str(folder / "jobs")
                and re.fullmatch(r"[A-Za-z0-9_-]+", config["job_name"]), "trial_output_path_differs")
            require(prepared["archive_sha256"] == frozen["archive_sha256"] == protocol["archive_sha256"]
                and prepared["host_source_sha256"] == frozen["host_source_sha256"]
                and prepared["task_input_sha256"] == frozen["task_input_sha256"], "frozen_preparation_pins_differ")
            kwargs = config["agents"][0]["kwargs"]
            require(prepared.get("semantic_metadata_view", "legacy") == kwargs.get("semantic_metadata_view", "legacy")
                == item["semantic_metadata_view"], "prepared_metadata_axis_differs")
            require(prepared["semantic_context_profile"] == kwargs["semantic_context_profile"]
                == item["semantic_context_profile"] == "indexed-default@1", "fixed_context_profile_differs")
            require(prepared["model"] == config["agents"][0]["model_name"] == protocol["model"]
                and prepared["reasoning_effort"] == protocol["reasoning_effort"]
                and prepared["cli_version"] == protocol["codex_version"]
                and prepared["resource_profile"] == protocol["resource_profile"], "provider_resource_pins_differ")
            job = folder / "jobs" / config["job_name"]
            attempt_paths = sorted(path for path in job.iterdir() if path.is_dir() and not path.is_symlink()) if job.is_dir() else []
            required = [folder / "receipt.json", job / "result.json"]
            required += [path / "result.json" for path in attempt_paths]
            required += [path / "agent/supervisor-result.json" for path in attempt_paths]
            if not attempt_paths or not all(path.is_file() for path in required):
                result["pending"].append("native_trial_incomplete:" + item["name"])
            else:
                available[item["name"]] = (folder, prepared, attempt_paths)
        for name in ("aggregate.json", "benchmark.json", "benchmark.csv"):
            if not (root / name).is_file():
                result["pending"].append("export_unavailable:" + name)
        result["checks"]["all_prepared_configuration_and_control_pins"] = True
        # Avoid reading a gigabyte archive while the live campaign is pending.
        if result["pending"]:
            return result
        aggregate, benchmark = read(root / "aggregate.json"), read(root / "benchmark.json")
        with (root / "benchmark.csv").open(newline="") as stream:
            csv_rows = list(csv.DictReader(stream))
        names = [item["name"] for item in selected]
        require([row["name"] for row in aggregate["trials"]] == names
            and [row["trial"] for row in benchmark["trials"]] == names
            and [row["trial"] for row in csv_rows] == names, "exported_trial_order_or_population_differs")
        require(benchmark["aggregate_sha256"] == digest(root / "aggregate.json")
            and aggregate["protocol_sha256"] == result["protocol_sha256"]
            and benchmark["source_commit"] == aggregate["source_commit"] == protocol["source_commit"], "export_provenance_differs")
        sessions, independent_arms, semantic_projections = set(), {}, []
        archive_paths, source_pins = set(), {}
        for item, aggregate_row, exported, csv_row in zip(selected, aggregate["trials"], benchmark["trials"], csv_rows):
            folder, prepared, paths = available[item["name"]]
            require(all(aggregate_row.get(key) == value for key, value in item.items()), "aggregate_declared_trial_differs")
            archive_paths.add(prepared["archive"])
            source_pins.update(prepared["host_source_sha256"])
            receipt = read(folder / "receipt.json")
            require(receipt.get("original_task_inputs_unchanged") is True
                and receipt.get("native_job_result_present") is True, "retained_task_integrity_or_completion_unverified")
            require(len(receipt["trials"]) == len(paths) == len(aggregate_row["attempts"]), "attempt_population_differs")
            retained = {row["trial"]: row for row in receipt["trials"]}
            require(len(retained) == len(paths), "duplicate_retained_attempt")
            totals, rewards, modes, fallbacks, coding_bytes = dict.fromkeys(TOKEN_KEYS, 0), [], set(), set(), []
            input_audits = []
            effective = item["semantic_metadata_view"] != "legacy"
            coding_count = 0
            for path in paths:
                raw, report = read(path / "result.json"), read(path / "agent/supervisor-result.json")
                record = retained[path.name]
                require(record["native_result_sha256"] == digest(path / "result.json") and record["supervisor"] == report,
                    "retained_native_result_or_supervisor_copy_differs")
                require(raw.get("task_name") in (item["task"], "terminal-bench/" + item["task"])
                    and record.get("exact_trial_task_matches") is True, "native_task_identity_differs")
                verifier = raw.get("verifier_result")
                require(type(verifier) is dict and type(verifier.get("rewards")) is dict, "official_reward_unavailable")
                reward = verifier["rewards"].get("reward")
                require(type(reward) in (int, float) and math.isfinite(reward), "official_reward_unavailable")
                require(record["reward"] == raw["verifier_result"]["rewards"], "retained_reward_differs")
                rewards.append(reward)
                observed, calls = native_totals(report, sessions)
                require(all(row.get("model") == protocol["model"] for row in calls), "observed_model_differs")
                require(report.get("semantic_context_profile") == "indexed-default@1", "observed_context_profile_differs")
                projection = report["initial_context"]["worker_projection"]
                require(projection.get("max_capsules") == 8 and projection.get("max_bytes") == 32768
                    and projection.get("selector") == "duckdb-query-symbol-name@1", "observed_semantic_budget_differs")
                semantic_projections.append({key: projection[key] for key in (
                    "max_capsules", "max_bytes", "selector", "full_capsule_count", "selected_capsule_count",
                    "omitted_capsule_count", "query", "raw_source_fetch_required")})
                semantic_projections[-1]["selected_symbols"] = [{key: row[key] for key in ("path", "qualified_name")}
                    for row in projection["selected_symbols"]]
                coding, effective_modes, reasons = exact_input_modes(report, calls, item["semantic_metadata_view"])
                input_audits.append(report["context_input_audit"]["status"])
                if item["semantic_metadata_view"] != "legacy":
                    collector = record.get("semantic_metadata_dispatch")
                    actual_effective = effective_modes == ["common-bindings@1"]
                    require(type(collector) is dict and collector.get("requested_mode_matches_report") is True
                        and collector.get("requested_mode") == item["semantic_metadata_view"]
                        and collector.get("coding_receipts_seen") == len(coding)
                        and collector.get("all_selection_receipts_bound_to_model_inputs") is True
                        and collector.get("all_coding_inputs_verified_by_retained_audit") is True
                        and collector.get("selected_modes") == effective_modes
                        and collector.get("fallback_reasons") == reasons
                        and collector.get("effective_treatment_observed") is actual_effective,
                        "collector_metadata_observation_differs")
                    effective = effective and actual_effective
                for key in TOKEN_KEYS:
                    totals[key] += observed[key]
                coding_count += len(coding)
                coding_bytes.extend(row["model_prompt_bytes"] for row in coding)
                modes.update(effective_modes)
                fallbacks.update(reasons)
            solved = any(reward >= 1 for reward in rewards)
            require(aggregate_row["complete_tokens"] == totals
                and aggregate_row["usage_complete"] is True and aggregate_row["solved"] is solved,
                "aggregate_native_totals_or_outcome_differs")
            require(all(exported.get(key) == totals[key] for key in TOKEN_KEYS)
                and exported.get("usage_complete") is True and exported.get("solved") is solved
                and exported.get("repeat") == item["repeat"] and exported.get("task") == item["task"]
                and exported.get("requested_metadata_view") == item["semantic_metadata_view"]
                and exported.get("context_profile") == "indexed-default@1"
                and exported.get("effective_treatment_observed") is effective
                and exported.get("attempts_observed") == len(paths)
                and exported.get("coding_invocations") == coding_count
                and exported.get("coding_model_prompt_bytes_sum") == sum(coding_bytes)
                and exported.get("effective_modes") == ";".join(sorted(modes))
                and exported.get("fallback_reasons") == ";".join(sorted(fallbacks)), "benchmark_native_summary_differs")
            expected_eligible = item["semantic_metadata_view"] == "legacy" or effective
            require(aggregate_row.get("state") == exported.get("state") == "finished"
                and aggregate_row.get("effective_treatment_observed") is effective
                and aggregate_row.get("effective_treatment_comparison_eligible") is expected_eligible
                and exported.get("effective_treatment_comparison_eligible") is expected_eligible
                and exported.get("input_audits") == ";".join(input_audits)
                and exported.get("selected_capsules") == report["initial_context"]["worker_projection"]["selected_capsule_count"]
                and exported.get("tokens_per_solved_trial") == (totals["total_tokens"] if solved else None),
                "benchmark_outcome_or_effective_comparison_differs")
            require(set(csv_row) == set(exported) and all(csv_row[key] == ("" if value is None else str(value))
                for key, value in exported.items()), "csv_json_row_differs")
            require(exported.get("requested_arm_comparison_eligible") is True
                and aggregate_row.get("requested_arm_comparison_eligible") is True,
                "requested_arm_comparison_unqualified")
            result["trials"].append({"trial": item["name"], "repeat": item["repeat"],
                "requested_mode": item["semantic_metadata_view"], "official_rewards": rewards, "solved": solved,
                "native_tokens": totals, "effective_modes": sorted(modes), "effective_treatment_observed": effective,
                "coding_invocations": coding_count, "exact_input_audit_correlated": True})
            arm = independent_arms.setdefault(item["semantic_metadata_view"],
                {"tokens": dict.fromkeys(TOKEN_KEYS, 0), "solved": 0, "trials": 0, "effective_treatment_trials": 0})
            for key in TOKEN_KEYS:
                arm["tokens"][key] += totals[key]
            arm["solved"] += solved
            arm["trials"] += 1
            arm["effective_treatment_trials"] += effective
        require(all(row == semantic_projections[0] for row in semantic_projections), "retained_capsule_or_source_population_differs")
        require(set(aggregate["arms"]) == set(benchmark["arms"]) == set(independent_arms) == {"legacy", "common-bindings@1"},
            "exported_arm_population_differs")
        for mode, observed in independent_arms.items():
            for owner in (aggregate, benchmark):
                arm = owner["arms"][mode]
                require(arm["complete_tokens_all_attempts"] == observed["tokens"]
                    and arm["solved_trial_repeats"] == observed["solved"]
                    and arm["planned_trials"] == arm["finished_trials"] == observed["trials"] == 2,
                    "arm_native_totals_or_repeat_counts_differ")
                ratio = observed["tokens"]["total_tokens"] / observed["solved"] if observed["solved"] else None
                require(arm["tokens_per_solved_task_including_failures"] == ratio, "arm_failure_inclusive_ratio_differs")
                require(arm["effective_treatment_trials"] == observed["effective_treatment_trials"], "arm_effective_treatment_count_differs")
        require(aggregate.get("requested_arm_populations_match") is True
            and benchmark.get("requested_arm_populations_match") is True, "matched_repeat_populations_unverified")
        require(set(benchmark["observed_requested_arm_comparison"]) == {
            "complete_tokens_all_attempts", "tokens_per_solved_task_including_failures"}, "comparative_metric_population_differs")
        for metric, comparison in benchmark["observed_requested_arm_comparison"].items():
            require(metric in ("complete_tokens_all_attempts", "tokens_per_solved_task_including_failures"),
                "unexpected_comparison_metric")
            values = []
            for mode in ("legacy", "common-bindings@1"):
                arm = independent_arms[mode]
                values.append(arm["tokens"]["total_tokens"] if metric == "complete_tokens_all_attempts" else
                    arm["tokens"]["total_tokens"] / arm["solved"] if arm["solved"] else None)
            before, after = values
            numeric = before is not None and before > 0 and after is not None
            require(comparison["legacy"] == before and comparison["requested_common_bindings"] == after
                and comparison["candidate_minus_legacy"] == (after - before if numeric else None)
                and comparison["candidate_change_percent"] == ((after - before) * 100 / before if numeric else None)
                and comparison["requested_arm_comparison_eligible"] is True,
                "exported_comparative_delta_differs")
        require(len(archive_paths) == 1, "multiple_runtime_archives")
        archive = Path(next(iter(archive_paths)))
        manifest, build = read(archive / "manifest.json"), read(archive / "verification.json")
        require(digest(archive / "runtime.tar.gz") == manifest["archive_sha256"] == build["archive_sha256"]
            == protocol["archive_sha256"], "runtime_archive_digest_differs")
        require(all(available[row["name"]][1]["manifest_sha256"] == digest(archive / "manifest.json") for row in selected)
            and build["all_archive_entries_match_inventory"] is True
            and build["all_packaged_source_matches_checkout_after_build"] is True,
            "archive_manifest_or_retained_build_verification_differs")
        for name, launcher_key in (("source", "source_head"), ("datasets", "datasets_head"), ("kit", "kit_head")):
            pin = build["source_repositories"][name]
            path = Path(pin["path"])
            head = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=path, text=True, timeout=30).strip()
            status = subprocess.check_output(["git", "status", "--porcelain"], cwd=path, text=True, timeout=30).strip()
            require(head == pin["head"] == launcher[launcher_key] and not status, "current_source_repository_pin_differs")
        require(all(digest(Path(path)) == expected for path, expected in source_pins.items()), "current_host_adapter_pin_differs")
        result["independent_arms"] = independent_arms
        result["checks"].update(native_session_identities_unique=True, native_usage_algebra_and_all_attempt_totals=True,
            csv_json_aggregate_protocol_order_and_population=True, official_rewards_and_exact_input_audits=True,
            requested_and_effective_metadata_modes=True, failure_inclusive_arm_totals=True,
            capsule_names_counts_budgets_and_raw_source_bindings_fixed=True,
            runtime_archive_and_manifest_hashes=True, current_clean_source_and_dependency_pins=True,
            current_host_adapter_hashes=True)
        result["artifact_sha256"] = {name: digest(root / name) for name in
            ("aggregate.json", "benchmark.json", "benchmark.csv", "comparison-protocol.json")}
        result["status"] = "verified"
    except (OSError, ValueError, TypeError, KeyError, IndexError, subprocess.SubprocessError) as error:
        result["failures"].append({"type": type(error).__name__, "reason": str(error)[:300]})
        result["status"] = "failed"
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parent)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--require-complete", action="store_true")
    args = parser.parse_args()
    root = args.root.resolve()
    result = verify(root)
    result["verifier_sha256"] = digest(Path(__file__).resolve())
    destination = args.output or root / "benchmark-verification.json"
    destination.write_text(json.dumps(result, indent=2, sort_keys=True, allow_nan=False) + "\n")
    print(json.dumps({"status": result["status"], "verified_trials": len(result["trials"]),
        "pending": result["pending"], "failures": result["failures"], "artifact": str(destination)}, indent=2))
    return 1 if result["status"] == "failed" or args.require_complete and result["status"] != "verified" else 0


if __name__ == "__main__":
    raise SystemExit(main())
