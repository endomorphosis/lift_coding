"""Reconcile fixed admitted ambient-budget metadata without native execution.

Owned Python transport stop observations remain distinct from normally completed
Lean/Rocq kernel checks. No current behavior, proof, source or process origin is
attested by this bounded standalone stdlib custody receiver.
"""

from __future__ import annotations

import argparse
import json
import math
import os
import re
import stat
import time
from hashlib import sha256
from pathlib import Path

INPUT_SCHEMA = "codebase-ir-native-operation-inheritance-custody-input@1"
SCHEMA = "codebase-ir-native-operation-inheritance-custody@1"
PROFILE = "recorded-admitted-ambient-inheritance@1"
MAX_FILE = 1024 * 1024
MAX_BYTES = 8 * 1024 * 1024
MAX_FILES = 32
MAX_MANIFEST = 128 * 1024
MAX_REPORT = 4 * 1024 * 1024
MAX_SECONDS = 120
MAX_DEPTH = 32
MAX_VALUES = 100000
ROLES = (
    "qualification",
    "prior_registry_qualification",
    "source_evolution",
    "test_source_evolution",
    "benchmark_source_evolution",
    "initial_execution_freeze",
    "selected_execution_freeze",
    "selected_preflight",
    "initial_native_command_result",
    "initial_native_command",
    "initial_native_log",
    "selected_native_command_result",
    "selected_native_command",
    "native_result",
    "native_requests",
    "native_invocations",
    "native_launches",
    "native_live_processes",
    "native_lifecycles",
    "scheduler_configuration",
    "focused_initial_test_result",
    "focused_selected_test_result",
    "joined_selected_test_result",
    "focused_final_test_result",
    "joined_final_test_result",
    "preservation_before",
    "preservation_after",
)
PUBLIC_PINS = {
    "benchmark_source_evolution": "3aa45dd9c3e343343efaea20cfecbde2f6e8c6a810837c1f7f8f4a6a74b52f18",
    "focused_final_test_result": "5648f6089c062dfebbcd79b95c052535c68becd7045a6293153b63c8695ddc2b",
    "focused_initial_test_result": "882b1d60c8f6275ba256bc196284f58b90c3132979716c1f9ef36eed7b43f689",
    "focused_selected_test_result": "9162548ca2f37d6b6350624abbf19e5429c487b2e3c7356d1f17c68d00279923",
    "initial_execution_freeze": "5fdbadac1c90ff461f01d6d0c619c48dfb659dc493e995462aa58d61d2c492d4",
    "initial_native_command": "a7b7fb5ad04b20eea3433c83760926c12f64839f204e1a979f6cfa8dbf578751",
    "initial_native_command_result": "be30b163d3ccc2b4df33d7180aa4e47a4b028dcaa2cb2daeb4e89c3b32d8e5ca",
    "initial_native_log": "db2fa64820653b76887bbd4b3dbf22ede070831bb716f4321173ee9ce92b6ad0",
    "joined_final_test_result": "9a0e760d98e37ec2b8b24437a259f74d08709c89134106e091d80dabd893b070",
    "joined_selected_test_result": "a1ee1e4c2278be9de252165497237bb7236409719b78e0f45471b7442b386f88",
    "native_invocations": "e9f0734f50ee12f2013d978ce96ad2a8da47b890b026eed1b3eecbdd63f849d4",
    "native_launches": "db9ec4fac5085418b98a73320fb635d62bac99edd7cb85f761658650f3651832",
    "native_lifecycles": "50f395157de6a54ca40a17345f90386466b2cdb22f699561e884dac21c93dc5b",
    "native_live_processes": "6987ce889ac2fa51ff66522e8cb5efe5a78832e117500445d58e856587328069",
    "native_requests": "9e7b5b927dde66a97ce9eabdb6752b57b0314f7fba6fff7b8720d072a7c52c8d",
    "native_result": "37a3ba7358590cf92abbd171158a50b76079a011ba4486f99fccfef9380c30c0",
    "preservation_after": "57cc8b474f7f26552ae7a6df19aba66aa806e8d921f18238bb454681c4739f34",
    "preservation_before": "a714cffb555eb7a41e4d6b4da9d81a471e38ec6747ce636271e2bd09dcc6fe5f",
    "prior_registry_qualification": "fbc3214bce59e8d995a35eae9508429062e77c260ab083b3d3486045fe137de8",
    "qualification": "37ed743edcdd3433896367d65d6b30adf2a11fce2bb187f6803194ae8d7b388f",
    "scheduler_configuration": "c88d589aa53fdd0ca5450c2091311bd0230d7f016b839194ff10ede75b302279",
    "selected_execution_freeze": "343b1ffe4813c45bee7832de58e57c78789e3f125a2316f1867e427ebd59cae3",
    "selected_native_command": "8913894a37689b3203ddc8e63bafd5aca8123f09c89e73332a281939b833b4f3",
    "selected_native_command_result": "b6b4bb133b05c033b500ef644692f2ad7c4d2d94b6a790c44cdc70a6b2524cd9",
    "selected_preflight": "dc3b280623405a9df5886d556ac220cc7cbd1a00b38454416c7edfc4b29a328b",
    "source_evolution": "99c394fde0818ae00cd4a063305f919777d50d48e0d05fe85407d5b5e348c36f",
    "test_source_evolution": "ca9a108a804137b38c48068af5cfe6448510c5d436a2c420a3340069589d2b17",
}
ARTIFACT_KEYS = {
    "benchmark_source_evolution": "benchmark-source-evolution.json",
    "focused_final_test_result": "focused-final.result.json",
    "focused_initial_test_result": "focused-initial.result.json",
    "focused_selected_test_result": "focused-selected.result.json",
    "initial_execution_freeze": "execution-freeze.json",
    "initial_native_command": "native/command.json",
    "initial_native_command_result": "native-command-result.json",
    "initial_native_log": "native.log",
    "joined_final_test_result": "joined-final.result.json",
    "joined_selected_test_result": "joined-selected.result.json",
    "native_invocations": "native-selected/invocation-audit.json",
    "native_launches": "native-selected/launch-audit.json",
    "native_lifecycles": "native-selected/lifecycle-audit.json",
    "native_live_processes": "native-selected/live-process-audit.json",
    "native_requests": "native-selected/request-audit.json",
    "native_result": "native-selected/result.json",
    "preservation_after": "preservation-after.json",
    "preservation_before": "preservation-before.json",
    "scheduler_configuration": "native-selected/saved-scheduler-config.json",
    "selected_execution_freeze": "execution-freeze-selected.json",
    "selected_native_command": "native-selected/command.json",
    "selected_native_command_result": "native-selected-command-result.json",
    "selected_preflight": "benchmark-preflight-selected.json",
    "source_evolution": "source-evolution.json",
    "test_source_evolution": "test-source-evolution.json",
}
TRUE_FLAGS = (
    "retained_ambient_native_inheritance_custody_conformance",
    "six_admitted_phase_population_reconciled",
    "earlier_deadline_and_cpu_tightening_reconciled",
    "inherited_signal_without_explicit_forwarding_preserved",
    "python_transport_logical_stops_preserved",
    "normally_completed_kernel_population_preserved",
    "historical_native_request_limits_preserved",
    "recorded_scoped_cleanup_reconciled",
    "whole_failed_attempt_metadata_preserved",
    "prior_selected_case_population_reconciled",
    "overlapping_test_counts_not_added",
    "source_evolution_declarations_retained",
    "input_files_unchanged",
)
FALSE_FLAGS = (
    "native_execution_performed",
    "training_executed",
    "current_authority_claimed",
    "owner_sources_imported",
    "owner_database_opened",
    "profile_keys_read",
    "network_access_performed",
    "git_executable_invoked",
    "native_transport_reexecuted",
    "current_admitted_runner_behavior_qualified",
    "native_kernel_cancellation_qualified",
    "native_isabelle_execution_qualified",
    "atp_proverif_tamarin_admission_qualified",
    "plain_injected_runner_behavior_qualified",
    "hard_callback_preemption_qualified",
    "hard_aggregate_containment_qualified",
    "whole_installer_cancellation_qualified",
    "parallel_speedup_qualified",
    "semantic_trace_replay_qualified",
    "proof_authority",
    "model_truth_qualified",
    "producer_authentication_verified",
    "process_origin_attested",
    "current_live_pid_reobserved",
    "live_cleanup_reobserved",
    "source_bodies_authenticated",
    "test_source_assertions_unchanged_verified",
    "benchmark_import_order_reexecuted",
    "selected_tools_authenticated",
    "shared_libraries_attested",
    "signature_authentication_performed",
    "signed_worker_qualified",
    "output_digest_algorithm_rederived",
    "production_default_activated",
)
ZERO_FIELDS = ("runtime_fact_count", "tasks_omitted_count", "additional_attempted_training_epochs")
CASE_IDS = (
    "kernel:lean:true",
    "kernel:lean:false",
    "kernel:rocq:true",
    "kernel:rocq:false",
    "transport:timeout",
    "transport:cancelled",
)
NATIVE_SCOPE = {
    "atp_proverif_tamarin_included": False,
    "benchmark_operation_scope_injected": False,
    "hard_aggregate_containment": False,
    "installation": False,
    "native_runner_or_probe_injected": False,
    "parallel_scaling_claim": False,
    "production_registry_scope": True,
    "python_transport_smoke": True,
    "real_kernel_cancellation_tested": False,
    "resource_sampler_injected": False,
}
SHAPES = {
    "attempt": (
        "artifact_digests",
        "attempt_id",
        "backend_id",
        "backend_version",
        "bounds",
        "diagnostics",
        "output_digest",
        "request_digest",
        "schema_version",
        "status",
        "usage",
    ),
    "case_native": ("invocation", "launch", "lifecycle", "live", "request"),
    "focused_final_test_result": (
        "after",
        "argv",
        "before",
        "cwd",
        "env_overrides",
        "returncode",
        "seconds",
        "suite",
        "test_snapshots",
    ),
    "focused_initial_test_result": (
        "after",
        "argv",
        "before",
        "cwd",
        "env_overrides",
        "returncode",
        "seconds",
        "suite",
        "test_snapshots",
    ),
    "focused_selected_test_result": (
        "after",
        "argv",
        "before",
        "cwd",
        "env_overrides",
        "returncode",
        "seconds",
        "suite",
        "test_snapshots",
    ),
    "generic_authority": (
        "configuration_digest",
        "evidence_digests",
        "issuer",
        "kind",
        "method",
        "schema_version",
        "scope_digest",
    ),
    "generic_payload": ("adapter_return_type", "result", "result_authority", "result_status"),
    "generic_result": (
        "assumption_ids",
        "attempt_digest",
        "authority",
        "backend_id",
        "backend_version",
        "bounds",
        "claim_digest",
        "declaration_id",
        "diagnostics",
        "obligation_digest",
        "obligation_id",
        "output_digest",
        "payload",
        "request_digest",
        "result_id",
        "result_type",
        "schema_version",
        "status",
        "usage",
    ),
    "initial_execution_freeze": (
        "benchmark_sha256",
        "focused_regression_sha256",
        "native_runner_sha256",
        "native_sources",
        "scope",
        "selected_regression_sha256",
        "selected_sources",
        "source_evolution_sha256",
        "static_preflight_sha256",
        "test_source_evolution_sha256",
    ),
    "initial_native_command": ("argv", "benchmark_sha256", "cwd"),
    "initial_native_command_result": (
        "after",
        "argv",
        "before",
        "cwd",
        "env_overrides",
        "freeze_sha256",
        "returncode",
        "seconds",
    ),
    "joined_final_test_result": (
        "after",
        "argv",
        "before",
        "cwd",
        "env_overrides",
        "returncode",
        "seconds",
        "suite",
        "test_snapshots",
    ),
    "joined_selected_test_result": (
        "after",
        "argv",
        "before",
        "cwd",
        "env_overrides",
        "returncode",
        "seconds",
        "suite",
        "test_snapshots",
    ),
    "kernel_case": (
        "ambient_absent_before_and_after",
        "attempt",
        "attempt_digest",
        "case",
        "default_runner_and_probes",
        "dispatch",
        "elapsed_seconds",
        "factory_override",
        "factory_scopes",
        "native",
        "observer_and_factory_restored",
        "operation_scope_owner",
        "original_outcome",
        "provider",
        "request",
        "request_digest",
        "result",
        "valid",
    ),
    "native_cancel_live": (
        "at_monotonic",
        "cancel_requested_at_monotonic",
        "case",
        "deadline",
        "live_at_cancel",
        "observed_live",
        "pid",
    ),
    "native_checks": (
        "four_real_kernel_cases",
        "no_explicit_native_cancellation",
        "no_generic_authority_promotion",
        "observer_and_factory_restored",
        "owned_work_drained",
        "selected_tools_unchanged",
        "shared_config_unchanged",
        "six_real_native_phases",
        "sources_stable",
        "two_transport_stop_controls",
    ),
    "native_invocation": (
        "argv",
        "at_monotonic",
        "case",
        "deadline",
        "environment",
        "inherited_signal_present",
        "limits",
        "remaining_seconds",
        "workspace",
    ),
    "native_launch": (
        "argv",
        "at_monotonic",
        "case",
        "launch_lease_id",
        "owned_leases",
        "root_allocations",
        "thread",
        "waiting",
    ),
    "native_lease": (
        "acquired_at",
        "cancelled",
        "child_process_slots",
        "cpu_slots",
        "expires_at",
        "gpu_memory_mb",
        "heartbeat_at",
        "lane",
        "lease_id",
        "lease_key",
        "memory_mb",
        "owner_birth_marker",
        "owner_boot_id",
        "owner_pid",
        "parent_lease_id",
        "request_id",
        "requires_gpu",
        "sequence",
        "unified_memory_mb",
        "wait_seconds",
    ),
    "native_lifecycle": ("case", "result", "shared_backoff_after"),
    "native_limits": (
        "cpu_seconds",
        "enforce_file_size_limit",
        "max_argument_bytes",
        "max_arguments",
        "max_environment_bytes",
        "max_file_bytes",
        "max_input_bytes",
        "max_output_bytes",
        "max_output_files",
        "max_path_bytes",
        "max_workspace_bytes",
        "memory_bytes",
        "resident_memory_bytes",
        "termination_grace_seconds",
        "timeout_seconds",
    ),
    "native_live": ("at_monotonic", "case", "deadline", "observed_live", "pid"),
    "native_request": (
        "argv",
        "at_monotonic",
        "case",
        "deadline",
        "environment",
        "explicit_cancellation_forwarded",
        "input_files",
        "limits",
    ),
    "native_result": (
        "audit_sha256",
        "checks",
        "child_usage",
        "elapsed_seconds",
        "kernel_cases",
        "launches",
        "runtime",
        "schema",
        "scope",
        "shared_after",
        "shared_before",
        "shared_pool_compatibility",
        "source_pins_after",
        "source_pins_before",
        "status",
        "tool_files_after",
        "tool_files_before",
        "tool_selection",
        "tool_selection_provenance",
        "transport_cases",
    ),
    "native_result_body": (
        "cancelled",
        "command",
        "elapsed_seconds",
        "error",
        "interface_version",
        "output_files",
        "output_truncated",
        "pid",
        "process_tree_terminated",
        "resource_exhausted",
        "returncode",
        "runtime",
        "stderr",
        "stdout",
        "termination_reason",
        "timed_out",
        "unavailable",
        "workspace_cleaned",
        "workspace_limit_exceeded",
    ),
    "native_scope": (
        "atp_proverif_tamarin_included",
        "benchmark_operation_scope_injected",
        "hard_aggregate_containment",
        "installation",
        "native_runner_or_probe_injected",
        "parallel_scaling_claim",
        "production_registry_scope",
        "python_transport_smoke",
        "real_kernel_cancellation_tested",
        "resource_sampler_injected",
    ),
    "original_outcome": (
        "capability",
        "interface_version",
        "receipt",
        "request_digest",
        "result",
        "source_binding",
    ),
    "preservation_after": (
        "benchmark_direct_script_import_order_corrected",
        "existing_test_files_changed",
        "historical_hash_aliases_added",
        "initial_native_attempt",
        "prior_artifacts",
        "prior_qualifications",
        "production_files_changed",
    ),
    "preservation_before": (
        "prior_native_sources",
        "prior_selected_sources",
        "qualifications",
        "source_evolution",
        "verified_prior_artifacts",
    ),
    "prior_registry_qualification": (
        "artifact_sha256",
        "checks",
        "deselected_legacy_native_tests",
        "focused_tests",
        "native_phases",
        "native_seconds",
        "native_success_cases",
        "native_wrapper_seconds",
        "new_cache_replay",
        "new_codebase_smt_execution",
        "new_operation_budget_tests",
        "preservation",
        "production_tasks_closed",
        "recorded_at_utc",
        "schema",
        "selected_test_cases",
        "selected_tests",
        "status",
        "test_attempts",
        "test_counts_summed",
    ),
    "qualification": (
        "additional_existing_test_cases",
        "additionally_selected_existing_tests",
        "artifact_sha256",
        "checks",
        "deselected_legacy_native_tests",
        "focused_tests",
        "native_kernel_cases",
        "native_phases",
        "native_seconds",
        "native_transport_controls",
        "native_wrapper_seconds",
        "new_cache_replay",
        "new_codebase_smt_execution",
        "new_operation_budget_tests",
        "preservation",
        "production_tasks_closed",
        "recorded_at_utc",
        "schema",
        "selected_test_cases",
        "selected_tests",
        "status",
        "test_attempts",
        "test_counts_summed",
    ),
    "qualification_checks": (
        "four_real_kernel_cases",
        "no_explicit_native_cancellation",
        "no_generic_authority_promotion",
        "observer_and_factory_restored",
        "owned_work_drained",
        "selected_tools_unchanged",
        "shared_config_unchanged",
        "six_real_native_phases",
        "sources_stable",
        "two_transport_stop_controls",
    ),
    "request": (
        "assumption_ids",
        "bounds",
        "claim_digest",
        "claim_id",
        "declaration_id",
        "logic_family",
        "obligation_digest",
        "obligation_id",
        "payload",
        "query_kind",
        "request_id",
        "requested_backend_id",
        "schema_version",
    ),
    "request_payload": ("encoding", "source"),
    "scheduler_configuration": (
        "allow_foreign_work",
        "config",
        "runtime",
        "schema",
        "state_before",
        "state_path",
    ),
    "selected_execution_freeze": (
        "benchmark_sha256",
        "benchmark_source_evolution_sha256",
        "focused_regression_sha256",
        "native_runner_sha256",
        "native_sources",
        "scope",
        "selected_regression_sha256",
        "selected_sources",
        "source_evolution_sha256",
        "static_preflight_sha256",
        "test_source_evolution_sha256",
    ),
    "selected_native_command": ("argv", "benchmark_sha256", "cwd"),
    "selected_native_command_result": (
        "after",
        "argv",
        "before",
        "cwd",
        "env_overrides",
        "freeze_sha256",
        "returncode",
        "seconds",
    ),
    "selected_preflight": (
        "ambient_operation_absent",
        "benchmark_has_no_operation_scope_call",
        "benchmark_script_sibling_first",
        "benchmark_sha256",
        "expected_native_kernel_cases",
        "expected_native_launches",
        "expected_transport_controls",
        "helper_sha256",
        "kernel_fixtures",
        "native_solver_cancellation_claim",
        "native_v2_execution",
        "registry_discovery_loaded_delegates",
        "scope",
        "sleep_source",
        "source_count",
        "source_pins",
        "source_pins_unchanged",
        "status",
        "tool_files",
        "tool_selection",
        "tool_selection_provenance",
        "transport_requests",
    ),
    "source_binding": ("request_digest", "schema_version", "source_digest", "source_format"),
    "transport_case": (
        "ambient_absent_before_and_after",
        "attempt",
        "attempt_digest",
        "case",
        "dispatch",
        "elapsed_seconds",
        "explicit_runner_cancellation_forwarded",
        "kind",
        "native",
        "operation_scope_owner",
        "request",
        "request_digest",
        "result",
        "scope",
        "solver_output_injected",
    ),
    "typed_receipt": (
        "accepted",
        "authority_disposition",
        "axiom_report",
        "diagnostics",
        "generated_proof",
        "generated_proof_digest",
        "imports",
        "plane",
        "receipt_id",
        "request_digest",
        "schema_version",
        "source_binding",
        "source_tree",
        "theorem_digest",
        "theorem_name",
        "toolchain",
        "translation",
    ),
    "typed_result": (
        "assumptions",
        "authority",
        "backend_id",
        "backend_version",
        "bounds",
        "diagnostics",
        "metadata",
        "reason",
        "result_id",
        "result_type",
        "schema_version",
        "status",
        "translation_ceiling",
        "usage",
        "witness",
    ),
}


def require(condition, message):
    if not condition:
        raise ValueError(message)


def wire(value):
    return json.dumps(
        value, sort_keys=True, separators=(",", ":"), ensure_ascii=True, allow_nan=False
    ).encode("utf-8")


def same(left, right):
    """JSON type-sensitive equality, including bool/int and int/float distinctions."""
    return wire(left) == wire(right)


def canonical(value):
    return (
        json.dumps(value, sort_keys=True, indent=2, ensure_ascii=True, allow_nan=False) + "\n"
    ).encode("utf-8")


def bounded_canonical(value, maximum):
    chunks, size = [], 0
    for token in json.JSONEncoder(
        sort_keys=True, indent=2, ensure_ascii=True, allow_nan=False
    ).iterencode(value):
        raw = token.encode("utf-8")
        require(size + len(raw) + 1 <= maximum, "serialized report allocation bound")
        chunks.append(raw)
        size += len(raw)
    return b"".join(chunks) + b"\n"


def document(raw):
    depth, quoted, escape, containers, tokens, bare = 0, False, False, 0, 0, False
    for token in raw:
        if quoted:
            if escape:
                escape = False
            elif token == 92:
                escape = True
            elif token == 34:
                quoted = False
        elif token == 34:
            quoted = True
            bare = False
            tokens += 1
        elif token in (91, 123):
            depth += 1
            containers += 1
            tokens += 1
            bare = False
            require(
                depth <= MAX_DEPTH and containers <= MAX_VALUES, "JSON structure allocation bound"
            )
        elif token in (93, 125):
            depth -= 1
            bare = False
            require(depth >= 0, "JSON nesting mismatch")
        elif token in (9, 10, 13, 32, 44, 58):
            bare = False
        elif not bare:
            tokens += 1
            bare = True
        require(tokens <= MAX_VALUES, "JSON lexical value allocation bound")

    def pairs(items):
        value = {}
        for key, child in items:
            require(key not in value, "duplicate JSON key")
            value[key] = child
        return value

    def integer(token):
        require(len(token) <= 20, "JSON integer allocation bound")
        value = int(token)
        require(abs(value) <= 2**63 - 1, "JSON integer magnitude bound")
        return value

    def floating(token):
        require(len(token) <= 64, "JSON float allocation bound")
        value = float(token)
        require(math.isfinite(value), "nonfinite JSON number")
        return value

    def constant(_):
        raise ValueError("nonfinite JSON number")

    value = json.loads(
        raw.decode("utf-8", errors="strict"),
        object_pairs_hook=pairs,
        parse_int=integer,
        parse_float=floating,
        parse_constant=constant,
    )
    require(type(value) in (dict, list), "JSON object or array required")
    pending, count = [(value, 0)], 0
    while pending:
        child, level = pending.pop()
        count += 1
        require(count <= MAX_VALUES and level <= MAX_DEPTH, "JSON value allocation bound")
        if type(child) is str:
            require(
                len(child) <= MAX_FILE
                and "\x00" not in child
                and not any(0xD800 <= ord(char) <= 0xDFFF for char in child),
                "bounded JSON text required",
            )
        elif type(child) is dict:
            pending.extend((key, level + 1) for key in child)
            pending.extend((item, level + 1) for item in child.values())
        elif type(child) is list:
            pending.extend((item, level + 1) for item in child)
    return value


def closed(value, keys, message):
    require(type(value) is dict and set(value) == set(keys), message)


def exact_int(value, maximum=2**63 - 1):
    require(type(value) is int and 0 <= value <= maximum, "bounded exact integer required")
    return value


def number(value):
    require(
        type(value) in (int, float) and math.isfinite(value) and 0 <= value <= 1e9,
        "bounded recorded number required",
    )
    return value


def digest(value):
    require(
        type(value) is str and re.fullmatch(r"[0-9a-f]{64}", value) is not None, "SHA-256 required"
    )
    return value


def identity(value):
    require(
        type(value) is str
        and 0 < len(value) <= 1024
        and "\x00" not in value
        and re.fullmatch(r"[A-Za-z0-9:_./-]+", value) is not None,
        "bounded declared identity required",
    )
    return value


def lexical_path(value, *, absolute=True):
    require(
        type(value) is str and 0 < len(value) <= 8192 and "\x00" not in value,
        "bounded lexical path required",
    )
    path = Path(value)
    require(
        path.is_absolute() is absolute
        and ".." not in path.parts
        and str(path) == value
        and value != ".",
        "canonical lexical path required",
    )
    return path


def descriptor(value):
    closed(value, {"path", "sha256", "size_bytes"}, "closed file descriptor required")
    lexical_path(value["path"])
    digest(value["sha256"])
    exact_int(value["size_bytes"], MAX_FILE)
    return dict(value)


def declared_pin(root, value):
    closed(value, {"path", "sha256", "bytes"}, "closed declared descriptor required")
    return descriptor(
        {
            "path": str(root / lexical_path(value["path"], absolute=False)),
            "sha256": value["sha256"],
            "size_bytes": value["bytes"],
        }
    )


class Capture:
    """Two separate caches receive only explicitly pinned regular bodies."""

    def __init__(self, remap=None, *, started=None):
        self.remap, self.files, self.total, self.identities, self.inodes = remap, {}, 0, {}, {}
        self.started = time.monotonic() if started is None else started

    def deadline(self):
        require(time.monotonic() - self.started <= MAX_SECONDS, "custody deadline")

    @staticmethod
    def fingerprint(path):
        row = path.lstat()
        return row.st_dev, row.st_ino, row.st_size, row.st_mtime_ns, row.st_ctime_ns

    @staticmethod
    def raw(path, maximum):
        require(
            path.is_absolute() and path.resolve(strict=True) == path,
            "canonical nonsymlink file required",
        )
        fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
        try:
            before = os.fstat(fd)
            require(
                stat.S_ISREG(before.st_mode) and 0 <= before.st_size <= maximum,
                "bounded regular file required",
            )
            with os.fdopen(fd, "rb", closefd=False) as stream:
                raw = stream.read(maximum + 1)
            after, current = os.fstat(fd), path.lstat()

            def fingerprint(row):
                return row.st_dev, row.st_ino, row.st_size, row.st_mtime_ns, row.st_ctime_ns

            require(
                fingerprint(before) == fingerprint(after) == fingerprint(current)
                and len(raw) == before.st_size,
                "file changed during bounded read",
            )
            return raw
        finally:
            os.close(fd)

    def read(self, path, pin=None, *, mapped=True, maximum=MAX_FILE):
        self.deadline()
        logical = lexical_path(str(path))
        if self.remap is not None and mapped:
            require(str(logical) in self.remap, "explicit relocated member unavailable")
            physical = lexical_path(self.remap[str(logical)])
        else:
            physical = logical
        limit = maximum if pin is None else descriptor(pin)["size_bytes"]
        require(limit <= maximum, "preallocation file bound")
        if physical not in self.files:
            require(
                len(self.files) < MAX_FILES and self.total + limit <= MAX_BYTES,
                "preallocation aggregate bound",
            )
            before = self.fingerprint(physical)
            require(before[:2] not in self.inodes, "distinct physical selected bodies")
            self.inodes[before[:2]] = physical
            self.files[physical] = self.raw(physical, limit)
            self.identities[physical] = self.fingerprint(physical)
            require(before == self.identities[physical], "file identity changed during capture")
            self.total += len(self.files[physical])
        raw = self.files[physical]
        if pin is not None:
            require(
                len(raw) == pin["size_bytes"] and sha256(raw).hexdigest() == pin["sha256"],
                "selected raw pin mismatch",
            )
        return raw

    def stable(self):
        for path, raw in self.files.items():
            self.deadline()
            require(
                self.raw(path, len(raw)) == raw and self.fingerprint(path) == self.identities[path],
                "previously captured body or identity changed",
            )
        return True


def scope():
    return {
        **dict.fromkeys(TRUE_FLAGS, True),
        **dict.fromkeys(FALSE_FLAGS, False),
        **dict.fromkeys(ZERO_FIELDS, 0),
    }


def write_new(path, raw):
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
    try:
        with os.fdopen(fd, "wb", closefd=False) as stream:
            require(stream.write(raw) == len(raw), "complete owned write")
        os.fchmod(fd, 0o444)
    finally:
        os.close(fd)


def output_population(root, expected):
    require(
        root.is_absolute()
        and root.resolve(strict=True) == root
        and stat.S_ISDIR(root.lstat().st_mode),
        "canonical output directory",
    )
    files, folders, pending = set(), set(), [root]
    while pending:
        folder = pending.pop()
        with os.scandir(folder) as entries:
            for entry in entries:
                relative = Path(entry.path).relative_to(root).as_posix()
                info = entry.stat(follow_symlinks=False)
                require(
                    len(files) < MAX_FILES and len(folders) <= 1, "bounded owned output population"
                )
                if stat.S_ISDIR(info.st_mode):
                    require(relative == "retained", "only expected retained directory")
                    folders.add(relative)
                    pending.append(Path(entry.path))
                else:
                    require(
                        stat.S_ISREG(info.st_mode) and relative in expected,
                        "exact regular owned output population",
                    )
                    files.add(relative)
    require(
        files == set(expected) and folders == {"retained"} and root.resolve(strict=True) == root,
        "exact final owned output population",
    )


def shaped(value, kind):
    closed(value, SHAPES[kind], "closed " + kind)
    return value


def recorded_number(value):
    require(
        type(value) in (int, float) and math.isfinite(value) and 0 <= value <= 1e12,
        "bounded finite recorded observation",
    )
    return value


def signed_int(value):
    require(type(value) is int and abs(value) < 2**31, "exact signed observed exit integer")
    return value


def declared_digests(value, count):
    require(type(value) is dict and len(value) == count, "complete declared source/tool inventory")
    for path, declared_sha256 in value.items():
        require(type(path) is str and 0 < len(path) <= 8192, "inert declared path")
        digest(declared_sha256)
    return value


def test_and_source_observations(docs, pins):
    q, previous = docs["qualification"], docs["prior_registry_qualification"]
    for role in (
        "qualification",
        "prior_registry_qualification",
        "initial_execution_freeze",
        "selected_execution_freeze",
        "selected_preflight",
        "initial_native_command_result",
        "initial_native_command",
        "selected_native_command_result",
        "selected_native_command",
        "preservation_before",
        "preservation_after",
        "focused_initial_test_result",
        "focused_selected_test_result",
        "joined_selected_test_result",
        "focused_final_test_result",
        "joined_final_test_result",
    ):
        shaped(docs[role], role)
    require(
        q["schema"] == "native-operation-inheritance-qualification@1"
        and q["status"] == "passed_partial_scope"
        and previous["schema"] == "registry-operation-budget-qualification@1"
        and previous["status"] == "passed_partial_scope",
        "fixed current/prior historical partial-scope qualifications",
    )
    shaped(q["checks"], "qualification_checks")
    require(
        all(value is True for value in q["checks"].values()),
        "complete recorded qualification checks",
    )
    require(
        q["test_counts_summed"] is False
        and q["new_cache_replay"] is False
        and q["new_codebase_smt_execution"] is False
        and q["production_tasks_closed"] == [],
        "overlap and no production closure",
    )
    for role, key in ARTIFACT_KEYS.items():
        require(
            q["artifact_sha256"].get(key) == pins[role]["sha256"],
            "selected raw metadata qualification join",
        )
    initial, selected = docs["initial_execution_freeze"], docs["selected_execution_freeze"]
    for freeze in (initial, selected):
        declared_digests(freeze["native_sources"], 91)
        declared_digests(freeze["selected_sources"], 175)
        require(
            freeze["source_evolution_sha256"] == pins["source_evolution"]["sha256"]
            and freeze["test_source_evolution_sha256"] == pins["test_source_evolution"]["sha256"],
            "frozen source declarations joined",
        )
    require(
        selected["benchmark_source_evolution_sha256"]
        == pins["benchmark_source_evolution"]["sha256"]
        and selected["static_preflight_sha256"] == pins["selected_preflight"]["sha256"],
        "selected driver and static metadata joined",
    )
    evolution = docs["benchmark_source_evolution"]
    require(type(evolution) is dict and len(evolution) == 1, "one driver correction declaration")
    benchmark, driver = next(iter(evolution.items()))
    closed(
        driver,
        {
            "before_sha256",
            "after_sha256",
            "before_snapshot",
            "after_snapshot",
            "diff",
            "diff_sha256",
            "initial_selected_snapshot",
            "purpose",
        },
        "closed driver source evolution declaration",
    )
    require(
        initial["benchmark_sha256"] == driver["before_sha256"]
        and selected["benchmark_sha256"] == driver["after_sha256"],
        "two immutable driver generations",
    )
    require(
        initial["native_sources"][benchmark] == driver["before_sha256"]
        and selected["native_sources"][benchmark] == driver["after_sha256"],
        "native source driver hash generations",
    )
    difference = {
        path
        for path in initial["native_sources"]
        if initial["native_sources"][path] != selected["native_sources"].get(path)
    }
    require(
        difference == {benchmark}
        and set(initial["native_sources"]) == set(selected["native_sources"]),
        "only driver evolves between native attempts",
    )
    before, after = docs["preservation_before"], docs["preservation_after"]
    require(
        same(q["preservation"], after)
        and exact_int(before["verified_prior_artifacts"])
        == exact_int(after["prior_artifacts"])
        == 1708
        and type(before["qualifications"]) is dict
        and len(before["qualifications"]) == exact_int(after["prior_qualifications"]) == 20,
        "recorded prior preservation quantities",
    )
    require(
        sum(exact_int(row["verified_artifacts"]) for row in before["qualifications"].values())
        == 1708,
        "independent declared prior artifact sum",
    )
    for row in before["qualifications"].values():
        closed(
            row,
            {"qualification_sha256", "report_sha256", "verified_artifacts"},
            "closed prior qualification declaration",
        )
        digest(row["qualification_sha256"])
        digest(row["report_sha256"])
    require(
        before["qualifications"]["registry-operation-budget-qualification-20261003"][
            "qualification_sha256"
        ]
        == pins["prior_registry_qualification"]["sha256"],
        "selected prior qualification independent raw binding",
    )
    require(
        exact_int(after["production_files_changed"]) == 1
        and exact_int(after["existing_test_files_changed"]) == 3
        and after["historical_hash_aliases_added"] is False
        and after["benchmark_direct_script_import_order_corrected"] is True,
        "limited declared production/test/driver evolution",
    )
    source = docs["source_evolution"]
    require(
        type(source) is dict
        and len(source) == 1
        and set(source) == set(before["source_evolution"]),
        "one production source declaration",
    )
    for path, row in source.items():
        closed(
            row,
            {
                "before_sha256",
                "after_sha256",
                "before_snapshot",
                "after_snapshot",
                "diff",
                "diff_sha256",
            },
            "closed production evolution",
        )
        require(
            path.endswith("/logic/backends/resource_admission.py")
            and before["prior_native_sources"][path] == row["before_sha256"]
            and selected["native_sources"][path]
            == initial["native_sources"][path]
            == row["after_sha256"],
            "production source generation joins",
        )
        require(
            same(
                before["source_evolution"][path],
                {key: row[key] for key in ("before_sha256", "before_snapshot")},
            ),
            "production preimage declaration preserved",
        )
    fixture_changes = docs["test_source_evolution"]
    require(
        type(fixture_changes) is dict and len(fixture_changes) == 3,
        "three clock fixture declarations",
    )
    for path, row in fixture_changes.items():
        closed(
            row,
            {
                "before_sha256",
                "after_sha256",
                "before_snapshot",
                "after_snapshot",
                "diff",
                "diff_sha256",
                "initial_attempt_snapshot",
                "purpose",
            },
            "closed clock fixture evolution declaration",
        )
        require(
            row["purpose"]
            == "Use the same simulated monotonic clock for the new ambient-deadline consumer; preserve all test assertions and cases.",
            "recorded fixture purpose retained without following source",
        )
        require(
            selected["selected_sources"][path]
            == initial["selected_sources"][path]
            == row["after_sha256"],
            "selected fixture postimage declaration",
        )
    for mapping in (source, fixture_changes, evolution):
        for row in mapping.values():
            for key, value in row.items():
                if key.endswith("_sha256"):
                    digest(value)
                elif key != "purpose":
                    lexical_path(value, absolute=False)
    specs = (
        (
            "focused_initial_test_result",
            "focused-initial",
            "focused",
            False,
            1,
            {"passed": 809, "failure": 9},
        ),
        ("focused_selected_test_result", "focused-selected", "focused", False, 0, {"passed": 818}),
        ("joined_selected_test_result", "joined-selected", "joined", False, 0, {"passed": 2314}),
        ("focused_final_test_result", "focused-final", "focused", True, 0, {"passed": 818}),
        ("joined_final_test_result", "joined-final", "joined", True, 0, {"passed": 2314}),
    )
    closed(q["test_attempts"], {row[1] for row in specs}, "complete five historical test attempts")
    observations = []
    for role, name, suite, accepted, code, counts in specs:
        row, observation = docs[role], q["test_attempts"][name]
        closed(
            observation,
            {"accepted", "counts", "returncode", "seconds", "sources_stable", "suite"},
            "closed historical test attempt",
        )
        require(
            observation["accepted"] is accepted
            and signed_int(observation["returncode"]) == signed_int(row["returncode"]) == code
            and observation["suite"] == row["suite"] == suite
            and observation["sources_stable"] is True
            and same(observation["counts"], counts)
            and same(observation["seconds"], row["seconds"])
            and same(row["before"], row["after"]),
            "whole historical passing and failed attempt declaration",
        )
        for value in observation["counts"].values():
            exact_int(value)
        wanted = dict(selected["selected_sources"])
        if name not in ("focused-final", "joined-final"):
            wanted[benchmark] = driver["before_sha256"]
        if name == "focused-initial":
            for path, change in fixture_changes.items():
                wanted[path] = change["before_sha256"]
        require(same(row["before"], wanted), "exact historical test source generation")
        observations.append(
            {
                "attempt": name,
                "suite": suite,
                "accepted": accepted,
                "recorded_counts": counts,
                "recorded_returncode": code,
                "recorded_seconds": recorded_number(row["seconds"]),
                "tests_reexecuted": False,
                "junit_failure_bodies_selected": False,
            }
        )

    def ids(value, count):
        require(
            type(value) is list
            and len(value) == count
            and all(type(x) is str and 0 < len(x) <= 4096 for x in value)
            and len(set(value)) == count,
            "complete unique case identifier population",
        )
        return set(value)

    old, new, additional = (
        ids(previous["selected_test_cases"], 2215),
        ids(q["selected_test_cases"], 2314),
        ids(q["additional_existing_test_cases"], 41),
    )
    controls = {
        value
        for value in new
        if "tests.unit.logic.backends.test_native_operation_inheritance::" in value
    }
    require(
        len(controls) == 58
        and old <= new
        and not old.intersection(controls | additional)
        and not controls.intersection(additional)
        and new - old == controls | additional,
        "exact prior2215 plus disjoint58 new and41 existing cases",
    )
    for key, expected in (
        ("selected_tests", 2314),
        ("focused_tests", 818),
        ("new_operation_budget_tests", 58),
        ("additionally_selected_existing_tests", 41),
        ("deselected_legacy_native_tests", 15),
    ):
        require(exact_int(q[key]) == expected, "typed historical case population count")
    return (
        {
            "previous_selected_case_count": 2215,
            "selected_case_count": 2314,
            "new_inheritance_case_count": 58,
            "additional_existing_case_count": 41,
            "focused_case_count": 818,
            "legacy_native_deselected_count": 15,
            "selected_case_ids_sha256": sha256(wire(q["selected_test_cases"])).hexdigest(),
            "previous_case_ids_sha256": sha256(wire(previous["selected_test_cases"])).hexdigest(),
            "new_inheritance_case_ids_sha256": sha256(wire(sorted(controls))).hexdigest(),
            "additional_existing_case_ids_sha256": sha256(
                wire(q["additional_existing_test_cases"])
            ).hexdigest(),
            "exact_disjoint_additions_rederived": True,
            "focused_and_joined_overlap": True,
            "test_counts_summed": False,
        },
        observations,
        {
            "recorded_prior_artifacts": 1708,
            "recorded_prior_qualifications": 20,
            "production_source_changes": 1,
            "clock_fixture_changes": 3,
            "driver_corrections": 1,
            "production_evolution": source,
            "test_evolution": fixture_changes,
            "benchmark_evolution": evolution,
            "native_source_fingerprint_count": 91,
            "selected_source_fingerprint_count": 175,
            "source_assertions_or_diff_semantics_verified": False,
            "prior_deep_body_closure": "unknown_not_selected",
        },
    )


def native_attempts(docs, pins):
    history = []
    for suffix, code in (("initial", 1), ("selected", 0)):
        command, result, freeze = (
            docs[suffix + "_native_command"],
            docs[suffix + "_native_command_result"],
            docs[suffix + "_execution_freeze"],
        )
        require(
            signed_int(result["returncode"]) == code
            and same(result["before"], result["after"])
            and same(result["before"], freeze["native_sources"])
            and same(command["argv"], result["argv"])
            and command["cwd"] == result["cwd"]
            and command["benchmark_sha256"] == freeze["benchmark_sha256"]
            and result["freeze_sha256"] == pins[suffix + "_execution_freeze"]["sha256"],
            "whole selected and initially refused native command",
        )
        require(
            type(command["argv"]) is list
            and len(command["argv"]) == 4
            and all(type(x) is str for x in command["argv"]),
            "inert benchmark argv declaration",
        )
        history.append(
            {
                "attempt": suffix,
                "recorded_returncode": code,
                "recorded_seconds": recorded_number(result["seconds"]),
                "benchmark_sha256": command["benchmark_sha256"],
                "native_execution_reperformed": False,
            }
        )
    log = docs["initial_native_log"]
    require(
        type(log) is str
        and log.startswith("Traceback (most recent call last):")
        and log.rstrip().endswith(
            "AssertionError: conditional consumer resolved outside selected sibling checkout"
        ),
        "whole initial source-import guard traceback retained",
    )
    stopped = docs["preservation_after"]["initial_native_attempt"]
    closed(stopped, {"returncode", "scope", "seconds"}, "closed initial native refusal scope")
    require(
        signed_int(stopped["returncode"]) == 1
        and same(stopped["seconds"], history[0]["recorded_seconds"])
        and stopped["scope"]
        == "source-import guard before runtime capture, shared-pool access or native execution",
        "initial source guard refusal declaration remains separate",
    )
    history[0].update(
        recorded_refusal_scope=stopped["scope"],
        traceback_sha256=pins["initial_native_log"]["sha256"],
        before_pool_or_execution_independently_attested=False,
    )
    return history


def phase_observations(docs, native):
    roles = (
        "native_requests",
        "native_invocations",
        "native_launches",
        "native_live_processes",
        "native_lifecycles",
    )
    require(
        all(type(docs[role]) is list and len(docs[role]) == 6 for role in roles),
        "complete six ordered native observation populations",
    )
    rows = []
    leases = set()
    pids = set()
    for index, values in enumerate(zip(*(docs[role] for role in roles), strict=True)):
        request, invoke, launch, live, lifecycle = values
        for value, shape in zip(
            values,
            (
                "native_request",
                "native_invocation",
                "native_launch",
                "native_cancel_live" if index == 5 else "native_live",
                "native_lifecycle",
            ),
            strict=True,
        ):
            shaped(value, shape)
        shaped(request["limits"], "native_limits")
        shaped(invoke["limits"], "native_limits")
        shaped(lifecycle["result"], "native_result_body")
        case = CASE_IDS[index]
        require(all(value["case"] == case for value in values), "fixed six phase case order")
        deadline = recorded_number(request["deadline"])
        require(
            deadline > 0
            and same(invoke["deadline"], deadline)
            and same(live["deadline"], deadline)
            and request["explicit_cancellation_forwarded"] is False
            and invoke["inherited_signal_present"] is True,
            "ambient signal and deadline inherited without explicit forwarding",
        )
        times = [
            recorded_number(value["at_monotonic"]) for value in (request, invoke, launch, live)
        ]
        require(
            times == sorted(times) and times[-1] < deadline,
            "request workspace invocation admitted launch and live observation order",
        )
        remaining = recorded_number(invoke["remaining_seconds"])
        limits = invoke["limits"]
        original = request["limits"]
        timeout = recorded_number(limits["timeout_seconds"])
        cpu = recorded_number(limits["cpu_seconds"])
        require(
            0 < remaining
            and abs(deadline - times[1] - remaining) < 0.002
            and 0 < timeout < original["timeout_seconds"]
            and abs(timeout - min(original["timeout_seconds"], remaining)) < 0.002
            and abs(cpu - min(original["cpu_seconds"], remaining)) < 0.002,
            "earlier effective wall deadline and tightened existing CPU ceiling",
        )
        require(
            same(
                {k: v for k, v in limits.items() if k not in ("timeout_seconds", "cpu_seconds")},
                {k: v for k, v in original.items() if k not in ("timeout_seconds", "cpu_seconds")},
            ),
            "original memory output input storage and process request limits unchanged",
        )
        for key, value in original.items():
            if key in ("timeout_seconds", "cpu_seconds", "termination_grace_seconds"):
                recorded_number(value)
            elif key == "enforce_file_size_limit":
                require(value is True, "original typed file-size limit")
            elif value is not None:
                exact_int(value)
        expected_profile = 512 if index < 2 else (1024 if index < 4 else 128)
        require(
            original["timeout_seconds"] == (15.0 if index < 4 else 10)
            and original["cpu_seconds"] == (15.0 if index < 4 else 2),
            "fixed original kernel/transport local budget profiles",
        )
        require(
            original["memory_bytes"]
            == (4294967296 if index < 2 else (1073741824 if index < 4 else 134217728))
            and original["resident_memory_bytes"] == (536870912 if index < 2 else None),
            "distinct fixed address-space and RSS profiles",
        )
        require(
            type(invoke["workspace"]) is str and invoke["workspace"].startswith("/tmp/logic-tool-"),
            "inert recorded workspace path",
        )
        workspace = invoke["workspace"]
        require(
            same(
                [value.replace("{workspace}", workspace) for value in request["argv"]],
                invoke["argv"],
            ),
            "exact materialized command declaration",
        )
        require(
            type(launch["argv"]) is list
            and launch["argv"][-len(invoke["argv"]) :] == invoke["argv"]
            and "--cpu=" + str(math.ceil(cpu)) + ":" + str(math.ceil(cpu)) in launch["argv"],
            "exact invocation suffix and OS-rounded CPU launch limit",
        )
        require(
            type(launch["owned_leases"]) is list and len(launch["owned_leases"]) == 1,
            "one admitted lease per observed phase",
        )
        lease = launch["owned_leases"][0]
        shaped(lease, "native_lease")
        identity(lease["lease_id"])
        require(
            lease["lease_id"] == launch["launch_lease_id"]
            and lease["lease_id"] not in leases
            and lease["cancelled"] is False
            and lease["parent_lease_id"] is None
            and lease["requires_gpu"] is False
            and lease["lane"] == "validation"
            and exact_int(lease["sequence"]) == index + 1,
            "unique unparented ordered admitted lease",
        )
        leases.add(lease["lease_id"])
        require(
            same(
                launch["root_allocations"],
                {"child_process_slots": 1, "cpu_slots": 1, "memory_mb": expected_profile},
            )
            and exact_int(lease["child_process_slots"]) == exact_int(lease["cpu_slots"]) == 1
            and exact_int(lease["memory_mb"]) == expected_profile,
            "exact recorded one-child one-CPU reservation profile",
        )
        result = lifecycle["result"]
        pid = exact_int(result["pid"])
        require(
            pid > 0
            and pid not in pids
            and exact_int(live["pid"]) == pid
            and live["observed_live"] is True,
            "distinct lifecycle and recorded live PID binding",
        )
        pids.add(pid)
        require(
            same(result["command"], request["argv"])
            and result["interface_version"] == "bounded-tool-runner/v1"
            and result["runtime"] == "native"
            and result["workspace_cleaned"] is True
            and all(
                result[key] is False
                for key in (
                    "output_truncated",
                    "resource_exhausted",
                    "unavailable",
                    "workspace_limit_exceeded",
                )
            ),
            "recorded native request/lifecycle body and cleanup binding",
        )
        elapsed = recorded_number(result["elapsed_seconds"])
        if index < 4:
            exit_code = 0 if index % 2 == 0 else 1
            require(
                signed_int(result["returncode"]) == exit_code
                and result["error"] == ""
                and result["termination_reason"]
                == ("completed" if exit_code == 0 else "nonzero_exit")
                and all(
                    result[key] is False
                    for key in ("timed_out", "cancelled", "process_tree_terminated")
                ),
                "ordinary positive and negative kernel execution has no interruption claim",
            )
        else:
            exit_code = -15
            require(
                signed_int(result["returncode"]) == exit_code
                and result["cancelled"] is True
                and result["timed_out"] is (index == 4)
                and result["process_tree_terminated"] is True
                and result["termination_reason"] == "cancelled"
                and result["stdout"] == "transport-child-started\n",
                "owned Python transport stop preserves native flags and raw startup output",
            )
            expected_error = (
                "native execution exceeded its shared deadline"
                if index == 4
                else "cancelled during native execution"
            )
            require(
                result["error"] == expected_error,
                "native timeout/cancellation stop reason preserved",
            )
            if index == 4:
                require(
                    times[1] + elapsed >= deadline,
                    "timeout cleanup may finish after logical deadline",
                )
            else:
                cancel = recorded_number(live["cancel_requested_at_monotonic"])
                require(
                    live["live_at_cancel"] is True
                    and times[-1] < cancel < deadline
                    and times[1] + elapsed > cancel,
                    "cancellation requested only after owned child observed alive",
                )
        rows.append(
            {
                "case": case,
                "kind": "ordinary_kernel" if index < 4 else "owned_python_transport",
                "recorded_deadline": deadline,
                "recorded_original_wall_seconds": original["timeout_seconds"],
                "recorded_effective_wall_seconds": timeout,
                "recorded_original_cpu_seconds": original["cpu_seconds"],
                "recorded_effective_cpu_seconds": cpu,
                "recorded_rounded_cpu_seconds": math.ceil(cpu),
                "recorded_remaining_seconds": remaining,
                "request_at_monotonic": times[0],
                "invocation_at_monotonic": times[1],
                "launch_at_monotonic": times[2],
                "live_observation_at_monotonic": times[3],
                "recorded_pid": pid,
                "recorded_lease_id": lease["lease_id"],
                "recorded_sequence": index + 1,
                "recorded_memory_mb": expected_profile,
                "recorded_returncode": exit_code,
                "recorded_timed_out": result["timed_out"],
                "recorded_cancelled": result["cancelled"],
                "recorded_tree_terminated": result["process_tree_terminated"],
                "recorded_workspace_cleaned": True,
                "live_process_reobserved": False,
                "hard_wall_containment_qualified": False,
            }
        )
    require(exact_int(native["launches"]) == 6, "six native launch declarations")
    return rows


def outcome_observations(docs, native, phases):
    kernels, transports = native["kernel_cases"], native["transport_cases"]
    require(
        type(kernels) is list
        and len(kernels) == 4
        and type(transports) is list
        and len(transports) == 2,
        "separate complete four kernel and two transport case populations",
    )
    observations = []
    for index, case in enumerate(kernels + transports):
        shaped(case, "kernel_case" if index < 4 else "transport_case")
        shaped(case["native"], "case_native")
        require(
            case["case"] == CASE_IDS[index]
            and case["operation_scope_owner"] == "production_registry"
            and case["ambient_absent_before_and_after"] is True,
            "production-owned independent per-case ambient scope",
        )
        for field, role in (
            ("request", "native_requests"),
            ("invocation", "native_invocations"),
            ("launch", "native_launches"),
            ("live", "native_live_processes"),
            ("lifecycle", "native_lifecycles"),
        ):
            require(
                same(case["native"][field], docs[role][index]),
                "whole independent native observation joins",
            )
        request, attempt, result = case["request"], case["attempt"], case["result"]
        for value, shape in (
            (request, "request"),
            (request["payload"], "request_payload"),
            (attempt, "attempt"),
            (result, "generic_result"),
            (result["authority"], "generic_authority"),
        ):
            shaped(value, shape)
        rpin = sha256(wire(request)).hexdigest()
        apin = sha256(wire(attempt)).hexdigest()
        require(
            case["request_digest"] == attempt["request_digest"] == result["request_digest"] == rpin
            and case["attempt_digest"] == result["attempt_digest"] == apin,
            "unchanged complete request and attempt wire identities",
        )
        require(
            request["schema_version"] == "proof-backend-request/v1"
            and attempt["schema_version"] == "proof-backend-attempt/v1"
            and result["schema_version"] == "bounded-result/v1"
            and request["query_kind"] == "theorem_proof",
            "historical protocol identities",
        )
        require(
            same(attempt["bounds"], request["bounds"])
            and same(result["bounds"], request["bounds"]),
            "original complete generic bounds retained",
        )
        for record in (attempt, result):
            closed(
                record["usage"],
                {"elapsed_ms", "output_bytes", "peak_memory_bytes", "steps"},
                "complete conservative generic zero usage",
            )
            require(
                all(
                    exact_int(record["usage"][key]) == 0
                    for key in ("output_bytes", "peak_memory_bytes", "steps")
                ),
                "no added generic output memory or steps",
            )
            elapsed_ms = exact_int(record["usage"]["elapsed_ms"])
            require(
                (
                    elapsed_ms == 0
                    if index < 4
                    else 0 < elapsed_ms <= request["bounds"]["timeout_ms"]
                ),
                "original logical interruption accounting stays separate from native cleanup duration",
            )
        require(same(attempt["usage"], result["usage"]), "exact recorded generic usage preserved")
        authority = result["authority"]
        require(
            authority["schema_version"] == "result-authority/v1"
            and authority["kind"] == "theorem_proof"
            and authority["method"] == "proof-backend-adapter/v1"
            and authority["scope_digest"] == rpin
            and authority["evidence_digests"] == [],
            "descriptive generic authority ceiling and empty evidence retained",
        )
        digest(authority["configuration_digest"])
        digest(result["output_digest"])
        require(
            result["output_digest"] == attempt["output_digest"]
            and attempt["artifact_digests"] == [],
            "descriptive output digest without recipe requalification",
        )
        elapsed = recorded_number(case["elapsed_seconds"])
        require(
            elapsed >= docs["native_lifecycles"][index]["result"]["elapsed_seconds"],
            "outer and native durations retained distinctly",
        )
        if index < 4:
            provider = "lean" if index < 2 else "rocq"
            valid = index % 2 == 0
            require(
                case["provider"]
                == request["requested_backend_id"]
                == authority["issuer"]
                == provider
                and case["valid"] is valid
                and case["default_runner_and_probes"] is True
                and case["observer_and_factory_restored"] is True
                and case["factory_override"] == "installed executable only",
                "ordinary default kernel route declarations",
            )
            scope = case["factory_scopes"]
            require(
                type(scope) is list and len(scope) == 1, "one recorded native kernel factory scope"
            )
            closed(scope[0], {"at_monotonic", "deadline"}, "closed kernel factory observation")
            at = recorded_number(scope[0]["at_monotonic"])
            deadline = phases[index]["recorded_deadline"]
            require(
                same(scope[0]["deadline"], deadline)
                and 0 < deadline - at <= 15
                and at < phases[index]["request_at_monotonic"],
                "factory request invocation share production deadline",
            )
            require(
                same(
                    request["bounds"],
                    {
                        "max_memory_bytes": 536870912 if index < 2 else 1073741824,
                        "max_output_bytes": 65536,
                        "max_steps": 100000,
                        "timeout_ms": 15000,
                    },
                ),
                "unchanged kernel outer request bounds",
            )
            original = case["original_outcome"]
            shaped(original, "original_outcome")
            shaped(original["result"], "typed_result")
            receipt_keys = set(SHAPES["typed_receipt"])
            if index >= 2:
                receipt_keys.remove("axiom_report")
                receipt_keys.add("assumption_report")
            closed(original["receipt"], receipt_keys, "closed provider-specific kernel receipt")
            shaped(original["source_binding"], "source_binding")
            shaped(result["payload"], "generic_payload")
            require(
                original["request_digest"]
                == original["receipt"]["request_digest"]
                == original["source_binding"]["request_digest"]
                == rpin
                and same(original["receipt"]["source_binding"], original["source_binding"]),
                "whole typed kernel source/receipt request joins",
            )
            payload, typed, receipt = result["payload"], original["result"], original["receipt"]
            require(
                same(payload["result"], typed)
                and payload["adapter_return_type"]
                == ("LeanKernelOutcome" if index < 2 else "RocqKernelOutcome")
                and typed["status"] == payload["result_status"] == ("proved" if valid else "error")
                and typed["authority"] == payload["result_authority"] == "theorem"
                and receipt["accepted"] is valid
                and result["status"] == ("unknown" if valid else "error")
                and attempt["status"] == ("succeeded" if valid else "failed"),
                "original exact kernel payload without generic authority upgrade",
            )
            observations.append(
                {
                    "case": case["case"],
                    "provider": provider,
                    "valid": valid,
                    "recorded_deadline": deadline,
                    "factory_scope": scope[0],
                    "recorded_attempt_status": attempt["status"],
                    "recorded_generic_status": result["status"],
                    "recorded_typed_status": typed["status"],
                    "recorded_receipt_accepted": valid,
                    "complete_typed_payload_sha256": sha256(wire(typed)).hexdigest(),
                    "request_sha256_rederived": rpin,
                    "attempt_sha256_rederived": apin,
                    "recorded_seconds": elapsed,
                    "kernel_proof_requalified": False,
                    "kernel_interruption_exercised": False,
                }
            )
        else:
            kind = "timeout" if index == 4 else "cancelled"
            require(
                case["kind"] == kind
                and case["explicit_runner_cancellation_forwarded"] is False
                and case["solver_output_injected"] is False
                and case["scope"]
                == "owned Python transport interruption only; no solver cancellation claim"
                and request["requested_backend_id"] == authority["issuer"] == "transport-smoke",
                "owned Python transport scope only",
            )
            require(
                same(
                    request["bounds"],
                    {
                        "max_memory_bytes": 134217728,
                        "max_output_bytes": 65536,
                        "max_steps": 100000,
                        "timeout_ms": 1000 if index == 4 else 3000,
                    },
                ),
                "original transport registry budget retained",
            )
            require(
                attempt["status"] == ("timed_out" if index == 4 else "cancelled")
                and result["status"] == "unknown"
                and same(result["payload"], {"solver_result": kind})
                and same(attempt["diagnostics"], result["diagnostics"]),
                "logical outer stop stays nonconclusive while native flags are retained",
            )
            diagnostic = (
                "ProofOperationTimeout: proof operation timeout during native execution"
                if index == 4
                else "ProofOperationCancelled: proof operation cancelled during native execution"
            )
            require(
                result["diagnostics"] == [diagnostic], "exact historical outer interruption reason"
            )
            observations.append(
                {
                    "case": case["case"],
                    "kind": kind,
                    "recorded_attempt_status": attempt["status"],
                    "recorded_generic_status": "unknown",
                    "recorded_native_timed_out": phases[index]["recorded_timed_out"],
                    "recorded_native_cancelled": True,
                    "recorded_seconds": elapsed,
                    "request_sha256_rederived": rpin,
                    "attempt_sha256_rederived": apin,
                    "recorded_deadline": phases[index]["recorded_deadline"],
                    "cancel_requested_at_monotonic": docs["native_live_processes"][index].get(
                        "cancel_requested_at_monotonic"
                    ),
                    "owned_child_observed_alive_before_cancel": index == 5,
                    "logical_timeout_native_cancel_combination_preserved": index == 4,
                    "native_solver_cancellation_requalified": False,
                    "live_cleanup_reobserved": False,
                }
            )
    return observations[:4], observations[4:]


def derive(docs, pins):
    population, tests, preservation = test_and_source_observations(docs, pins)
    attempts = native_attempts(docs, pins)
    native = docs["native_result"]
    shaped(native, "native_result")
    shaped(native["scope"], "native_scope")
    shaped(native["checks"], "native_checks")
    require(
        native["schema"] == "native-operation-inheritance-benchmark@1"
        and native["status"] == "passed"
        and same(native["scope"], NATIVE_SCOPE)
        and all(value is True for value in native["checks"].values()),
        "historical native qualification partial scope and checks preserved",
    )
    selected = docs["selected_execution_freeze"]
    preflight = docs["selected_preflight"]
    require(
        same(native["source_pins_before"], native["source_pins_after"])
        and same(native["source_pins_before"], selected["native_sources"])
        and same(preflight["source_pins"], selected["native_sources"]),
        "complete native/preflight recorded source freeze",
    )
    declared_digests(native["tool_files_before"], 4)
    require(
        same(native["tool_files_before"], native["tool_files_after"])
        and same(native["tool_files_before"], preflight["tool_files"]),
        "recorded installed tool hashes unchanged without following tools",
    )
    require(
        preflight["status"] == "passed"
        and preflight["ambient_operation_absent"] is True
        and preflight["benchmark_has_no_operation_scope_call"] is True
        and preflight["benchmark_script_sibling_first"] is True
        and preflight["native_solver_cancellation_claim"] is False
        and preflight["native_v2_execution"] is False
        and exact_int(preflight["registry_discovery_loaded_delegates"]) == 0
        and exact_int(preflight["source_count"]) == 91,
        "static discovery/import-order/no native scope declarations",
    )
    for role in (
        "native_requests",
        "native_invocations",
        "native_launches",
        "native_live_processes",
        "native_lifecycles",
    ):
        require(
            native["audit_sha256"].get(ARTIFACT_KEYS[role].split("/")[-1]) == pins[role]["sha256"],
            "independent audit raw digest joins",
        )
    phases = phase_observations(docs, native)
    kernels, transports = outcome_observations(docs, native, phases)
    shared, saved = native["shared_after"], docs["scheduler_configuration"]
    shaped(saved, "scheduler_configuration")
    require(
        saved["schema"] == "codebase-saved-scheduler-config@1"
        and saved["allow_foreign_work"] is True
        and same(saved["config"], native["shared_before"]["config"])
        and same(saved["config"], shared["config"]),
        "saved shared pool configuration retained",
    )
    for field in (
        "active_leases",
        "waiting_requests",
        "owned_active_leases",
        "owned_waiting_requests",
    ):
        require(exact_int(shared[field]) == 0, "recorded scoped owned work drained")
    require(
        exact_int(shared["next_sequence"]) == 7,
        "six recorded acquisitions/releases next sequence seven",
    )
    q = docs["qualification"]
    for field, value in (
        ("native_phases", 6),
        ("native_kernel_cases", 4),
        ("native_transport_controls", 2),
    ):
        require(
            exact_int(q[field]) == value, "complete typed aggregate historical native population"
        )
    require(
        same(q["native_seconds"], native["elapsed_seconds"])
        and same(q["native_wrapper_seconds"], docs["selected_native_command_result"]["seconds"]),
        "native and wrapper durations remain distinct",
    )
    return {
        "phase_observations": phases,
        "kernel_cases": kernels,
        "transport_controls": transports,
        "resources": {
            "recorded_acquisitions": 6,
            "recorded_releases": 6,
            "recorded_next_sequence": 7,
            "recorded_owned_leases_and_waiters_drained": True,
            "saved_shared_configuration": saved["config"],
            "live_cleanup_reobserved": False,
            "hard_aggregate_containment_requalified": False,
        },
        "attempt_history": {
            "test_attempts": tests,
            "native_attempts": attempts,
            "failed_attempts_remain_unaccepted": True,
        },
        "test_population": population,
        "source_preservation": preservation,
        "body_closure": dict.fromkeys(
            (
                "source_preimages_postimages_diffs",
                "test_assertions",
                "native_tools_and_libraries",
                "junit_failure_bodies",
                "prior_artifact_bodies",
                "database_model_or_keys",
            ),
            "unknown_not_selected",
        ),
        "production_tasks_closed": [],
    }


def audit(manifest, output, *, relocated_sources=None):
    started = time.monotonic()
    original, copies = Capture(relocated_sources, started=started), Capture(started=started)
    manifest, output = lexical_path(str(manifest)), lexical_path(str(output))
    require(
        output.parent.resolve(strict=True) == output.parent
        and not output.exists()
        and not output.is_symlink(),
        "fresh canonical output directory",
    )
    raw_manifest = original.read(manifest, maximum=MAX_MANIFEST)
    selection = document(raw_manifest)
    closed(
        selection,
        {"schema", "selected_profile", "selected_files"},
        "closed deadline input manifest",
    )
    require(
        selection["schema"] == INPUT_SCHEMA
        and selection["selected_profile"] == PROFILE
        and type(selection["selected_files"]) is list
        and len(selection["selected_files"]) == len(ROLES),
        "fixed selected profile and population",
    )
    pins = {}
    for role, row in zip(ROLES, selection["selected_files"], strict=True):
        closed(row, {"role", "path", "sha256", "size_bytes"}, "closed selected descriptor")
        require(row["role"] == role, "fixed ordered selected roles")
        pins[role] = descriptor({key: row[key] for key in ("path", "sha256", "size_bytes")})
        require(
            pins[role]["sha256"] == PUBLIC_PINS[role], "fixed independent retained public selection"
        )
    paths = {pin["path"] for pin in pins.values()}
    require(
        len(paths) == len(ROLES) and str(manifest) not in paths,
        "disjoint original input population",
    )
    if relocated_sources is not None:
        require(
            type(relocated_sources) is dict and set(relocated_sources) == {str(manifest), *paths},
            "closed explicit relocated input population",
        )
        require(
            len(set(relocated_sources.values())) == len(relocated_sources),
            "distinct relocated physical inputs",
        )
    physical = [
        Path(relocated_sources.get(path, path)) if relocated_sources else Path(path)
        for path in [str(manifest), *paths]
    ]
    require(
        all(
            output != path and output not in path.parents and path not in output.parents
            for path in physical
        ),
        "disjoint physical inputs and owned output",
    )
    bodies = {role: original.read(Path(pins[role]["path"]), pins[role]) for role in ROLES}
    docs = {
        role: raw.decode("utf-8", errors="strict")
        if role == "initial_native_log"
        else document(raw)
        for role, raw in bodies.items()
    }
    findings = derive(docs, pins)
    original.stable()
    output.mkdir(mode=0o755)
    root_identity = (output.lstat().st_dev, output.lstat().st_ino)
    retained = output / "retained"
    retained.mkdir(mode=0o755)
    retained_identity = (retained.lstat().st_dev, retained.lstat().st_ino)
    copy_rows, members = [], ["retained/input.json"]
    write_new(retained / "input.json", raw_manifest)
    copies.read(retained / "input.json", maximum=MAX_MANIFEST)
    for index, role in enumerate(ROLES):
        path = retained / (
            f"{index:02}-" + role + (".log" if role == "initial_native_log" else ".json")
        )
        write_new(path, bodies[role])
        pin = {
            "path": str(path),
            "sha256": pins[role]["sha256"],
            "size_bytes": pins[role]["size_bytes"],
        }
        require(copies.read(path, pin) == bodies[role], "original and retained copy raw bytes")
        copy_rows.append({"role": role, **pins[role], "retained_copy": pin})
        members.append(path.relative_to(output).as_posix())
    nested = {
        "schema": "codebase-ir-native-operation-inheritance-selected-custody@1",
        "status": "passed",
        "qualified": True,
        "selected_files": copy_rows,
        "manifest_sha256": sha256(raw_manifest).hexdigest(),
        "scope": scope(),
        "original_capture_bytes": original.total,
        "copy_capture_bytes": copies.total,
        **findings,
    }
    nested_path = output / "selected_custody.json"
    nested_raw = bounded_canonical(nested, MAX_REPORT)
    write_new(nested_path, nested_raw)
    nested_identity = Capture.fingerprint(nested_path)
    members.append(nested_path.name)
    report = {
        "schema": SCHEMA,
        "workflow": "native_operation_inheritance_custody",
        "selected_profile": PROFILE,
        "status": "passed",
        "qualified": True,
        "selected_files": copy_rows,
        "selected_file_count": len(ROLES),
        "selected_input_bytes": sum(pin["size_bytes"] for pin in pins.values()),
        "manifest_sha256": sha256(raw_manifest).hexdigest(),
        **{role + "_sha256": pins[role]["sha256"] for role in ROLES},
        **scope(),
        "scope": scope(),
        **findings,
        "limits": {
            "max_file_bytes": MAX_FILE,
            "max_original_bytes": MAX_BYTES,
            "max_copy_bytes": MAX_BYTES,
            "max_files_per_cache": MAX_FILES,
            "max_manifest_bytes": MAX_MANIFEST,
            "max_report_bytes": MAX_REPORT,
            "max_seconds": MAX_SECONDS,
            "max_depth": MAX_DEPTH,
            "max_values": MAX_VALUES,
        },
        "custody": {
            "original_file_count": len(original.files),
            "copy_file_count": len(copies.files),
            "original_capture_bytes": original.total,
            "copy_capture_bytes": copies.total,
            "local_receipt": {
                "path": str(nested_path),
                "sha256": sha256(nested_raw).hexdigest(),
                "size_bytes": len(nested_raw),
            },
        },
        "elapsed_seconds": time.monotonic() - started,
    }
    report_path = output / "native_operation_inheritance_custody.json"
    report_raw = bounded_canonical(report, MAX_REPORT)
    write_new(report_path, report_raw)
    report_identity = Capture.fingerprint(report_path)
    members.append(report_path.name)
    original.stable()
    copies.stable()
    require(
        Capture.raw(nested_path, len(nested_raw)) == nested_raw
        and same(document(nested_raw), nested),
        "final local nested raw body",
    )
    require(
        Capture.raw(report_path, len(report_raw)) == report_raw
        and same(document(report_raw), report),
        "final main raw report body",
    )
    require(
        (output.lstat().st_dev, output.lstat().st_ino) == root_identity,
        "owned output directory identity unchanged",
    )
    output_population(output, members)
    # This is bounded filesystem custody, not an atomic filesystem snapshot.
    # Reopen every selected body after population observations, including the
    # receipts already read above, so late observed drift cannot be accepted.
    for _ in range(2):
        output_population(output, members)
        original.stable()
        copies.stable()
        require(Capture.raw(nested_path, len(nested_raw)) == nested_raw, "closing nested raw body")
        require(Capture.raw(report_path, len(report_raw)) == report_raw, "closing main raw body")
        require(
            Capture.fingerprint(nested_path) == nested_identity
            and Capture.fingerprint(report_path) == report_identity,
            "closing receipt identities unchanged",
        )
        require(
            (output.lstat().st_dev, output.lstat().st_ino) == root_identity,
            "closing output directory identity unchanged",
        )
        require(
            (retained.lstat().st_dev, retained.lstat().st_ino) == retained_identity,
            "closing retained directory identity unchanged",
        )
    original.deadline()
    return report


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args(argv)
    report = audit(args.manifest, args.output)
    print(
        json.dumps(
            {
                "qualified": report["qualified"],
                "report": str(args.output / "native_operation_inheritance_custody.json"),
            },
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
