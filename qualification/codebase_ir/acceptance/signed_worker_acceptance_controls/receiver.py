"""Bounded offline receiving of retained signed successor worker metadata.

Signature declarations and historical native observations retain their original
scope. This reader authenticates no signature, process, source or native result.
"""

from __future__ import annotations

import argparse
import base64
import binascii
import copy
import hashlib
import json
import math
import os
import re
import stat
from pathlib import Path

INPUT_SCHEMA = "codebase-ir-signed-worker-acceptance-controls-input@1"
REPORT_SCHEMA = "codebase-ir-signed-worker-acceptance-controls@1"
REPORT_NAME = "signed_worker_acceptance_controls.json"
MAX_FILES, MAX_FILE, MAX_TOTAL = 128, 4 * 1024 * 1024, 32 * 1024 * 1024
MAX_ORIGINALS, MAX_MANIFEST, MAX_REPORT = 64, 128 * 1024, 4 * 1024 * 1024
TRUE = (
    "retained_signed_worker_metadata_custody_conformance",
    "signed_task_population_preserved",
    "public_artifact_transport_preserved",
    "signed_declaration_bindings_reconciled",
    "prerequisite_and_completion_bindings_reconciled",
    "worker_output_receipt_bindings_reconciled",
    "publication_checks_reconciled",
    "typed_stale_observation_preserved",
    "historical_qualification_scopes_preserved",
    "input_files_unchanged",
)
FALSE = (
    "native_execution_performed",
    "training_executed",
    "current_authority_claimed",
    "owner_database_opened",
    "profile_keys_read",
    "owner_sources_imported",
    "signature_authentication_performed",
    "public_signatures_cryptographically_verified",
    "process_origin_attested",
    "worker_identity_authenticated",
    "worker_execution_qualified",
    "native_admission_reperformed",
    "native_task_completion_authenticated",
    "proposal_policy_executed",
    "source_execution_replayed",
    "source_semantics_verified",
    "intent_correspondence_verified",
    "physical_worker_absence_verified",
    "container_enforcement_qualified",
    "resource_enforcement_qualified",
    "native_git_publication_reperformed",
    "public_checks_executed",
    "source_generation_invalidation_reperformed",
    "complete_scan_reexecuted",
    "numerical_execution_reperformed",
    "model_quality_qualified",
    "live_eligibility_qualified",
    "production_acceptance_qualified",
    "production_default_activated",
    "throughput_improvement_qualified",
    "general_crash_recovery_qualified",
    "full_archive_custody_qualified",
    "nested_referenced_bodies_opened",
    "proof_authority_qualified",
    "behavioral_satisfaction_qualified",
    "task_omission_authority_qualified",
)
ZERO = (
    "runtime_fact_count",
    "tasks_omitted_count",
    "additional_attempted_training_epochs",
    "additional_fit_attempt_count",
    "additional_inference_attempt_count",
    "additional_scan_page_count",
    "additional_reference_page_count",
    "additional_provider_call_count",
)
AUTHORITY_FIELDS = (
    "admission_authority",
    "authoritative_cache_eligible",
    "behavioral_satisfaction",
    "completion_authority",
    "decoded_formulas_generated",
    "execution_authority",
    "mutation_authority",
    "proof_authority",
    "repository_code_executed",
    "runtime_behavior_verified",
    "scan_execution_attested",
    "source_execution_attested",
    "source_semantics_verified",
    "training_executed",
)
TASK_IDS = ("SUCCESSOR-TYPE", "SUCCESSOR-FORMAT")
CHECK_IDS = ("public-type", "public-offset")
CHECK_PATHS = ("check_type.py", "check_offset.py")
SCOPE_PATHS = {"README.md", "calc.py", "check_type.py", "check_offset.py"}

ROLES = (
    "historical_source_successor_review",
    "successor_expansion_review",
    "native_result",
    "native_admission",
    "current_admission_verification",
    "signed_manifest",
    "raw_public_worker_artifact",
    "decoded_public_worker_artifact",
    "public_worker_context",
    "authored_worker_receipt",
    "execution_scope_before",
    "execution_scope_after_stop",
    "native_lifecycle",
    "worker_candidate",
    "prerequisite_claim",
    "prerequisite_validation",
    "published_public_checks",
    "published_source_receipt",
    "container_boundary",
    "worker_stdout_log",
)

METADATA_SHAPES = {
    "historical_source_successor_review": 36,
    "successor_expansion_review": 93,
    "native_result": 198,
    "native_admission": 241,
    "current_admission_verification": 242,
    "signed_manifest": 171,
    "raw_public_worker_artifact": 281,
    "decoded_public_worker_artifact": 281,
    "public_worker_context": 282,
    "authored_worker_receipt": 107,
    "execution_scope_before": 322,
    "execution_scope_after_stop": 322,
    "native_lifecycle": 323,
    "worker_candidate": 324,
    "prerequisite_claim": 327,
    "prerequisite_validation": 330,
    "published_public_checks": 89,
    "published_source_receipt": 258,
    "container_boundary": 331,
    "worker_boundary_receipt": 97,
    "worker_output_receipt": 104,
}
SHAPE_NODES = [
    ("bool",),
    ("int",),
    ("str",),
    ("dict", {"bytes": 1, "path": 2, "sha256": 2}),
    ("list", 6, (3,)),
    ("float",),
    (
        "dict",
        {
            "actual_current_source_delta_plan_preview": 5,
            "author_fresh_300_member_repository": 5,
            "build_default_source_delta": 5,
            "cold_current_source_delta_plan_preview": 5,
            "cold_receive_fresh_prefix_page": 5,
            "cold_receive_successor_selection": 5,
            "explicit_current_head_child_training": 5,
            "explicit_previous_head_root_training": 5,
            "infer_default_fresh_32_member_prefix": 5,
            "infer_opt_out_fresh_32_member_prefix": 5,
            "publish_current_source": 5,
            "publish_previous_source": 5,
            "refuse_old_model_for_new_head": 5,
            "refuse_precancelled_selection_receiving": 5,
            "select_default_fresh_successor_root": 5,
            "select_opt_out_successor_root": 5,
        },
    ),
    (
        "dict",
        {
            "benchmark_new_fitting_epochs_across_two_attempts": 1,
            "failed_native_seconds": 5,
            "independent_reader_seconds": 5,
            "inherited_benchmark_fitting_epochs": 1,
            "qualified_native_seconds": 5,
            "qualified_phase_seconds": 6,
            "unit_fixture_new_fitting_epochs_separate": 1,
        },
    ),
    (
        "dict",
        {"errors": 1, "failures": 1, "junit": 3, "seconds_decimal": 2, "skipped": 1, "tests": 1},
    ),
    ("dict", {"active_lease_count": 1, "waiting_request_count": 1}),
    ("dict", {"elapsed_seconds": 5, "name": 2, "status": 2}),
    ("list", 8, (10,)),
    (
        "dict",
        {
            "error": 2,
            "error_type": 2,
            "final_resources": 9,
            "new_fitting_epochs": 1,
            "new_scan_pages_created": 1,
            "phases": 11,
            "qualified": 0,
            "recorded_seconds": 5,
            "result": 3,
        },
    ),
    ("list", 9, (2,)),
    ("list", 4, (1,)),
    ("dict", {"bytes": 1, "sha256": 2}),
    (
        "dict",
        {
            "adam_steps": 14,
            "artifact": 15,
            "completed_epochs": 1,
            "feature_columns": 1,
            "latent_width": 1,
            "report_sha256": 2,
            "state_sha256": 2,
        },
    ),
    ("dict", {"child": 16, "root": 16}),
    ("dict", {"elapsed_seconds": 5, "error": 2, "error_type": 2, "name": 2, "refused": 0}),
    ("list", 2, (18,)),
    ("dict", {"different": 1, "equal": 1, "unavailable": 1}),
    ("dict", {"added": 1, "changed": 1, "removed": 1, "retained": 1}),
    (
        "dict",
        {
            "ast_identity_comparisons": 20,
            "classifications": 21,
            "current_entries": 1,
            "previous_entries": 1,
            "source_bytes_comparisons": 20,
            "union_entries": 1,
        },
    ),
    (
        "dict",
        {
            "ast_revision_id": 2,
            "generation": 1,
            "manifest_cid": 2,
            "receipt_cid": 2,
            "repository_id": 2,
            "schema": 2,
            "snapshot_cid": 2,
        },
    ),
    (
        "dict",
        {
            "default_selection": 1,
            "existing_repository_preview": 1,
            "inference_page": 1,
            "planning_adapter": 1,
            "reference_override_is_qualification_only": 0,
            "reference_selection": 5,
        },
    ),
    (
        "dict",
        {
            "entries_coverage_and_inference_exact": 0,
            "optimized_page_cid": 2,
            "optimized_root_cid": 2,
            "reference_page_cid": 2,
            "reference_root_cid": 2,
            "scope": 2,
            "throughput_qualified": 0,
        },
    ),
    ("dict", {"deferred_budget": 1, "inferred": 1, "unindexed": 1}),
    ("dict", {"dispositions": 26, "inferred_rows": 1, "inventory_entries": 1}),
    (
        "dict",
        {
            "checkpoint_states": 17,
            "controls": 19,
            "coverage": 22,
            "current_head": 23,
            "final_resources": 9,
            "inference_attempts_during_selection_or_cold_receiving": 1,
            "inherited_scan_pages": 1,
            "inherited_setup_epochs": 1,
            "model_owner_reopens": 1,
            "new_fitting_epochs": 1,
            "new_scan_pages_created": 1,
            "operation_deadline_seconds": 24,
            "opt_out_equivalence": 25,
            "planning_result_cid": 2,
            "prefix_coverage": 27,
            "prefix_page_cid": 2,
            "previous_head": 23,
            "root_cid": 2,
            "source_delta_cid": 2,
            "source_owner_reopens": 1,
            "successor_selection_cid": 2,
            "training_attempts_after_setup": 1,
        },
    ),
    ("dict", {"bytes": 1, "imports": 2, "sha256": 2}),
    ("dict", {"errors": 1, "failures": 1, "skipped": 1, "tests": 1}),
    ("list", 4, (3,)),
    ("dict", {"current": 3, "name": 2, "retained": 3}),
    ("list", 34, (32,)),
    (
        "dict",
        {
            "combined_distinct": 1,
            "known_unit_fixture_new_fitting_epochs": 1,
            "new_unique": 1,
            "overlap_prior": 1,
            "prior_distinct": 1,
            "successful_final_junit_seconds_decimal": 2,
        },
    ),
    ("list", 2, (8,)),
    (
        "dict",
        {
            "384d_qualified": 0,
            "checkpoint_6_producers_unchanged": 4,
            "complete_successor_scan_qualified": 0,
            "costs": 7,
            "cuda_qualified": 0,
            "distinct_test_receipt": 3,
            "failed_initial_planning_tests": 8,
            "failed_native_attempt": 12,
            "independent_closed_audit": 3,
            "limitations": 13,
            "native_namespace": 2,
            "native_result": 3,
            "native_work": 28,
            "prior_source_runtime_review": 3,
            "production_default_activated": 0,
            "production_open_tasks": 1,
            "production_task_status_changed": 0,
            "proof_authority": 0,
            "qualified": 0,
            "reader": 29,
            "reader_guard_counts": 30,
            "reader_guard_receipt": 3,
            "reader_retained_copy": 3,
            "reader_source": 3,
            "recorded_at_utc": 2,
            "report": 3,
            "review_builder": 3,
            "runtime_core_observations": 31,
            "runtime_reexecuted_here": 0,
            "scan_execution_attested": 0,
            "schema": 2,
            "selected_producers": 33,
            "selected_source_generation": 3,
            "signed_successor_worker_qualified": 0,
            "source_22_producers_unchanged": 0,
            "source_execution_attested": 0,
            "status": 2,
            "targeted_planning_repeat": 8,
            "test_accounting": 34,
            "tests": 35,
        },
    ),
    (
        "dict",
        {
            "affected_native_runtime": 3,
            "harness": 3,
            "paired_receiving": 3,
            "public_worker_reader": 3,
            "reservation": 3,
            "signed_routing": 3,
        },
    ),
    (
        "dict",
        {
            "all_tiny_completed_fit_calls": 1,
            "all_tiny_new_epochs": 1,
            "cpu_test_completed_epochs": 1,
            "cpu_test_completed_fit_calls": 1,
            "first_cpu_test_completed_fit_calls": 1,
            "first_cpu_test_failed_training_attempts": 1,
            "inference_training_calls": 1,
            "selected_published_inherited_adam_steps": 1,
            "selected_published_inherited_epochs": 1,
            "selected_published_new_fit_calls": 1,
            "selected_tiny_adam_steps": 1,
            "selected_tiny_completed_fit_calls": 1,
            "selected_tiny_new_epochs": 1,
        },
    ),
    (
        "dict",
        {
            "all_own_native_leases_released": 0,
            "codebase_feature_cuda_qualification": 0,
            "full_transitive_source_attestation": 0,
            "general_codebase_384d_qualification": 0,
            "global_host_idle_claimed": 0,
            "production_admission": 0,
            "proof_authority": 0,
            "public_download_cache_in_closed_primary_inventory": 0,
            "released_core_device": 2,
            "selected_source_inventory_scope": 2,
            "source_semantics_verified": 0,
            "whole_model_cuda": 0,
        },
    ),
    ("dict", {"cpu_seconds": 5, "cuda_seconds": 5, "speedup": 5}),
    ("dict", {"cpu_seconds": 5, "cuda_seconds": 5, "dimension": 1, "rows": 1, "speedup": 5}),
    ("list", 2, (41,)),
    (
        "dict",
        {
            "gte_32_rows_cpu_median_seconds": 5,
            "gte_32_rows_cuda_median_seconds": 5,
            "gte_speedup": 5,
            "published_128_rows": 40,
            "singleton_cuda_slower": 0,
            "tiny_128_rows": 42,
        },
    ),
    ("dict", {"counts": 30, "junit": 3, "junit_seconds": 5, "namespace": 2, "result": 3}),
    ("list", 5, (44,)),
    (
        "dict",
        {"distinct_current_cases": 1, "history": 45, "selected": 44, "total_case_executions": 1},
    ),
    (
        "dict",
        {
            "distinct_current_cases": 1,
            "errors": 1,
            "failed": 1,
            "published_cases": 1,
            "skipped": 1,
            "tiny_cases": 1,
        },
    ),
    (
        "dict",
        {
            "actual_costs": 38,
            "handoff": 3,
            "limitations": 39,
            "measurements": 43,
            "product_controls": 46,
            "reader_controls": 47,
        },
    ),
    ("list", 7, (3,)),
    ("dict", {"handoff": 3, "new_fitting_epochs": 1, "new_inference_pages": 1, "scope": 2}),
    (
        "dict",
        {
            "deferred_budget": 1,
            "inferred": 1,
            "opaque": 1,
            "parse_failed": 1,
            "unindexed": 1,
            "unsupported_target": 1,
        },
    ),
    ("dict", {"dispositions": 51, "inferred_rows": 1, "inventory_entries": 1, "pages": 1}),
    ("list", 1, (1,)),
    (
        "dict",
        {
            "active_lease_count": 1,
            "global_active_lease_count": 1,
            "global_waiting_request_count": 1,
            "owner_pids": 53,
            "scope": 2,
            "waiting_request_count": 1,
        },
    ),
    ("dict", {"next_offset": 1, "previous_page_cid": 2, "root_cid": 2, "schema": 2}),
    ("list", 2, (2,)),
    ("dict", {}),
    ("NoneType",),
    (
        "dict",
        {
            "lane_reservations": 57,
            "max_gpu_memory_percent": 58,
            "max_memory_percent": 58,
            "max_swap_percent": 58,
            "max_waiting_requests": 1,
            "proof_backoff_seconds": 5,
            "proof_cpu_stall_percent": 5,
            "proof_io_stall_percent": 5,
            "proof_memory_headroom_mb": 1,
            "proof_memory_stall_percent": 5,
            "proof_safety_enabled": 0,
            "require_known_gpu_for_gpu_work": 0,
            "reserved_gpu_memory_mb": 1,
            "reserved_memory_mb": 1,
            "total_child_process_slots": 1,
            "total_cpu_slots": 1,
            "total_gpu_memory_mb": 1,
            "total_memory_mb": 1,
            "total_unified_memory_mb": 1,
        },
    ),
    (
        "dict",
        {
            "complete": 0,
            "final_resources": 54,
            "fit_guard_scope": 2,
            "helper_sha256": 2,
            "materialization_receipt_sha256": 2,
            "max_pages": 1,
            "new_fitting_epochs": 1,
            "next_cursor": 55,
            "numerical_after": 17,
            "numerical_before": 17,
            "pages_created": 56,
            "pid": 1,
            "post_setup_fit_attempt_count": 1,
            "prefix_tail_cid": 2,
            "proof_authority": 0,
            "qualified": 0,
            "recorded_seconds": 5,
            "registry_owner_generation_after": 1,
            "registry_owner_generation_before": 1,
            "request_cursor": 55,
            "request_sha256": 2,
            "root_cid": 2,
            "run_number": 1,
            "scan_execution_attested": 0,
            "scheduler_configuration": 59,
            "scheduler_state_path": 2,
            "schema": 2,
            "source_execution_attested": 0,
            "source_model_owner_preservation": 0,
            "timeout_seconds": 1,
            "version_id": 2,
        },
    ),
    (
        "dict",
        {
            "complete": 0,
            "completion_cid": 2,
            "coverage": 52,
            "final_resources": 54,
            "fit_guard_scope": 2,
            "helper_sha256": 2,
            "materialization_receipt_sha256": 2,
            "max_pages": 1,
            "new_fitting_epochs": 1,
            "next_cursor": 58,
            "numerical_after": 17,
            "numerical_before": 17,
            "pages_created": 56,
            "pid": 1,
            "post_setup_fit_attempt_count": 1,
            "prefix_tail_cid": 2,
            "proof_authority": 0,
            "qualified": 0,
            "recorded_seconds": 5,
            "registry_owner_generation_after": 1,
            "registry_owner_generation_before": 1,
            "request_cursor": 55,
            "request_sha256": 2,
            "root_cid": 2,
            "run_number": 1,
            "scan_execution_attested": 0,
            "scheduler_configuration": 59,
            "scheduler_state_path": 2,
            "schema": 2,
            "source_execution_attested": 0,
            "source_model_owner_preservation": 0,
            "timeout_seconds": 1,
            "version_id": 2,
        },
    ),
    ("list", 4, (60, 61)),
    (
        "dict",
        {
            "coverage": 52,
            "fresh_process_count": 1,
            "fresh_processes": 62,
            "independent_audit": 3,
            "inherited_setup_epochs": 1,
            "namespace": 2,
            "new_default_scan_pages": 1,
            "new_fitting_epochs": 1,
            "new_reference_scan_pages": 1,
            "owner_open_count": 1,
            "reader_controls": 3,
            "recorded_seconds": 5,
            "result": 3,
        },
    ),
    ("list", 4, (2,)),
    ("list", 32, (2,)),
    ("dict", {"mnt": 2, "net": 2, "pid": 2}),
    ("dict", {"cpu.max": 2, "memory.max": 2, "pids.max": 2}),
    ("dict", {"euid": 1, "namespaces": 66, "schema": 2, "uid": 1, "values": 67}),
    ("dict", {"Memory": 1, "NanoCpus": 1, "NetworkMode": 2, "PidsLimit": 1, "Privileged": 0}),
    ("dict", {"Destination": 2, "Mode": 2, "Propagation": 2, "RW": 0, "Source": 2, "Type": 2}),
    ("list", 6, (70,)),
    ("dict", {"HostConfig": 69, "Id": 2, "Mounts": 71, "Name": 2}),
    (
        "dict",
        {
            "cgroup": 68,
            "cgroup_returncode": 1,
            "cgroup_stderr": 2,
            "cgroup_stdout": 2,
            "inspection": 72,
            "inspection_returncode": 1,
            "inspection_stderr": 2,
            "inspection_stdout": 2,
            "process_origin_attested": 0,
        },
    ),
    ("dict", {"cpu_slots": 1, "memory_mb": 1}),
    (
        "dict",
        {
            "child_process_slots": 1,
            "cpu_slots": 1,
            "gpu_memory_mb": 1,
            "memory_mb": 1,
            "unified_memory_mb": 1,
        },
    ),
    (
        "dict",
        {
            "child_process_slots": 1,
            "cpu_slots": 1,
            "gpu_memory_mb": 1,
            "memory_mb": 1,
            "reserved_gpu_memory_mb": 1,
            "reserved_memory_mb": 1,
            "unified_memory_mb": 1,
            "usable_gpu_memory_mb": 1,
            "usable_memory_mb": 1,
        },
    ),
    (
        "dict",
        {
            "acquisitions_total": 1,
            "cancellations_total": 1,
            "recovered_leases_total": 1,
            "recoveries_total": 1,
            "releases_total": 1,
            "saturation_events_total": 1,
            "timeouts_total": 1,
        },
    ),
    (
        "dict",
        {
            "acquisitions_total": 1,
            "cancellations_total": 1,
            "timeouts_total": 1,
            "wait_count": 1,
            "wait_seconds_max": 5,
            "wait_seconds_mean": 5,
            "wait_seconds_total": 5,
        },
    ),
    ("dict", {"allocated": 75, "reservation": 74, "telemetry": 78}),
    ("dict", {"orchestration": 79, "snapshot_evaluation": 79, "trainer": 79}),
    (
        "dict",
        {
            "child_process_slots_saturated": 0,
            "cpu_saturated": 0,
            "events_total": 1,
            "gpu_memory_saturated": 0,
            "memory_saturated": 0,
            "saturated": 0,
            "unified_memory_saturated": 0,
        },
    ),
    ("dict", {"count": 1, "max": 5, "mean": 5, "p50": 5, "p95": 5, "p99": 5, "total": 5}),
    (
        "dict",
        {
            "active_child_lease_count": 1,
            "active_lease_count": 1,
            "active_root_lease_count": 1,
            "allocated": 74,
            "allocated_child_process_slots": 1,
            "allocated_gpu_memory_mb": 1,
            "allocated_unified_memory_mb": 1,
            "available": 75,
            "capacity": 76,
            "counters": 77,
            "lanes": 80,
            "proof_backoff": 57,
            "saturation": 81,
            "schema_version": 2,
            "state_path": 2,
            "wait_time_seconds": 82,
            "waiting_request_count": 1,
        },
    ),
    ("dict", {"SUCCESSOR-FORMAT": 2, "SUCCESSOR-TYPE": 2}),
    (
        "dict",
        {
            "admission": 1,
            "default_receiving": 1,
            "native_start_ms": 1,
            "public_receivers_reference_close": 1,
            "resource_admission": 1,
            "worker_lifetime": 1,
        },
    ),
    ("list", 3, (2,)),
    ("list", 1, (2,)),
    (
        "dict",
        {
            "argv": 86,
            "cwd": 2,
            "path": 2,
            "returncode": 1,
            "schema": 2,
            "source_after": 15,
            "source_before": 15,
            "stderr": 2,
            "stderr_bytes": 1,
            "stderr_sha256": 2,
            "stdout": 2,
            "stdout_bytes": 1,
            "stdout_sha256": 2,
            "timeout_seconds": 1,
        },
    ),
    ("list", 2, (88,)),
    (
        "dict",
        {
            "baseline_commit": 2,
            "changed_paths": 87,
            "parents": 56,
            "public_checks": 89,
            "public_checks_passed": 0,
            "published_commit": 2,
        },
    ),
    (
        "dict",
        {
            "budget_refused": 0,
            "completed": 0,
            "deadline_seconds": 1,
            "elapsed_seconds": 5,
            "error": 2,
            "error_type": 2,
            "integrity_refusal_claimed": 0,
        },
    ),
    (
        "dict",
        {
            "actual_container_limits": 73,
            "container_execution": 3,
            "host_global_resources_observed_after_cleanup": 83,
            "host_owned_resources_after_cleanup": 54,
            "independent_audit": 3,
            "inherited_reference_pages": 1,
            "inherited_scan_pages": 1,
            "inherited_setup_epochs": 1,
            "namespace": 2,
            "native_result": 3,
            "native_task_statuses": 84,
            "new_fitting_epochs": 1,
            "new_scan_pages": 1,
            "operation_deadlines": 85,
            "original_selected_source_changes_observed": 86,
            "paired_close_seconds": 5,
            "paired_entry_seconds": 5,
            "publication": 90,
            "reader_controls": 3,
            "recorded_seconds": 5,
            "reference_close": 91,
            "source_snapshot_scope": 2,
        },
    ),
    (
        "dict",
        {
            "codebase_feature_cuda_qualified": 0,
            "control_receipts": 37,
            "cuda": 48,
            "failed_worker_attempts": 49,
            "failed_worker_native_owner_pairs": 1,
            "fresh_transport": 50,
            "full_scan": 63,
            "full_successor_scan_qualified": 0,
            "full_transitive_dependency_attestation": 0,
            "general_codebase_384d_qualified": 0,
            "gte_small_actual_cuda_qualified": 0,
            "historical_closed_state": 3,
            "legal_384d_formula_actual_cuda_qualified": 0,
            "legal_8d_formula_actual_cuda_qualified": 0,
            "next_work": 64,
            "process_origin_attested": 0,
            "production_default_activated": 0,
            "production_tasks_open": 65,
            "proof_authority": 0,
            "published_legal_384d_private_head_actual_cuda_qualified": 0,
            "recorded_at_utc": 2,
            "released_published_core_device": 2,
            "report": 3,
            "resource_configuration": 3,
            "review_builder": 3,
            "schema": 2,
            "scope": 2,
            "signed_successor_dispatch_qualified": 0,
            "signed_worker": 92,
            "source_semantics_verified": 0,
            "test_counts_are_not_additive": 0,
            "unchanged_production_table": 15,
            "whole_published_model_cuda": 0,
        },
    ),
    (
        "dict",
        {
            "completion_authority": 0,
            "container_id": 2,
            "image_id": 2,
            "manifest_sha256": 2,
            "namespaces": 66,
            "owner_uid": 1,
            "purpose": 2,
            "schema": 2,
            "worker_uid": 1,
        },
    ),
    ("dict", {"execute": 0, "read": 0, "write": 0}),
    (
        "dict",
        {
            "/home/barberb/lift_coding/artifacts/codebase_ir_terminal_bench/signed-successor-worker-qualification-20261003-08/setup-seed": 95,
            "/opt/ipfs-supervisor/state": 95,
            "/results/native/private": 95,
        },
    ),
    (
        "dict",
        {
            "boundary": 94,
            "boundary_artifact": 2,
            "boundary_sha256": 2,
            "euid": 1,
            "gid": 1,
            "groups": 53,
            "pid": 1,
            "private_access": 96,
            "provider_calls": 1,
            "schema": 2,
            "training_steps": 1,
            "uid": 1,
            "workspace": 2,
        },
    ),
    ("dict", {"line": 1, "log": 3, "receipt": 97}),
    (
        "dict",
        {
            "admission_authority": 0,
            "authoritative_cache_eligible": 0,
            "behavioral_satisfaction": 0,
            "completion_authority": 0,
            "decoded_formulas_generated": 0,
            "execution_authority": 0,
            "mutation_authority": 0,
            "proof_authority": 0,
            "repository_code_executed": 0,
            "runtime_behavior_verified": 0,
            "scan_execution_attested": 0,
            "source_execution_attested": 0,
            "source_semantics_verified": 0,
            "training_executed": 0,
        },
    ),
    ("list", 0, ()),
    (
        "dict",
        {
            "administrator_task_cids": 56,
            "authority": 99,
            "codebase_inventory_context_cid": 2,
            "completion_cid": 2,
            "context_cid": 2,
            "current_facts": 100,
            "membership_cid": 2,
            "native_inventory_current_verified_here": 0,
            "native_persistence_verified_here": 0,
            "pending_cid": 2,
            "planning_receipt_cid": 2,
            "removed_task_cids": 100,
            "root_cid": 2,
            "runtime_requirements_preserved": 0,
        },
    ),
    (
        "dict",
        {
            "authority": 99,
            "completion_cid": 2,
            "context_cid": 2,
            "current_head": 23,
            "native_inventory_current_verified_here": 0,
            "native_successor_current_verified_here": 0,
            "previous_head": 23,
            "root_cid": 2,
            "selection_cid": 2,
            "source_delta_cid": 2,
        },
    ),
    (
        "dict",
        {
            "artifact": 2,
            "artifact_sha256": 2,
            "block_bytes": 1,
            "block_sha256": 2,
            "codebase_inventory": 101,
            "codebase_successor": 102,
            "completion_authority": 0,
            "context_cid": 2,
            "extra_provider_calls": 1,
            "historical_replay": 0,
            "manifest_cid": 2,
            "manifest_signature_verified": 0,
            "schema": 2,
            "scope_expansion_authority": 0,
            "semantic_minification_applied": 0,
            "source_bytes": 1,
            "source_freshness_verified": 0,
            "source_path": 2,
            "source_sha256": 2,
            "task_cid": 2,
            "task_id": 2,
            "verbatim_utf8": 0,
        },
    ),
    (
        "dict",
        {
            "after_sha256": 2,
            "before_sha256": 2,
            "completion_authority": 0,
            "native_completion_recorded_here": 0,
            "path": 2,
            "pid": 1,
            "proof_authority": 0,
            "provider_calls": 1,
            "public_instruction": 103,
            "schema": 2,
            "status": 2,
            "task_cid": 2,
            "training_steps": 1,
            "uid": 1,
        },
    ),
    ("dict", {"line": 1, "log": 3, "receipt": 104}),
    (
        "dict",
        {
            "bytes": 1,
            "declared_staged_directory_opened": 0,
            "original_source_archive_opened": 0,
            "path": 2,
            "sha256": 2,
            "staged_destination": 2,
            "transport_qualification_reperformed_here": 0,
        },
    ),
    (
        "dict",
        {
            "actual_boundary_stdout_observation": 98,
            "actual_stdout_observation": 105,
            "completion_authority": 0,
            "context_cid": 2,
            "guarded_read_bytes": 1,
            "native_formal_compilation_reperformed_here": 0,
            "native_inventory_freshness_verified_here": 0,
            "native_registry_opened": 0,
            "numerical_execution_reperformed_here": 0,
            "original_artifact": 3,
            "private_evidence_epoch_verified_here": 0,
            "process_origin_attested": 0,
            "proof_authority": 0,
            "public_signatures_verified": 0,
            "retained_root_boundary": 3,
            "retained_staged_seed_binding": 106,
            "schema": 2,
            "selection_cid": 2,
            "source_delta_cid": 2,
            "successor_context_cid": 2,
            "task_cid": 2,
            "verified": 0,
            "worker_context_cid": 2,
        },
    ),
    (
        "dict",
        {"error": 2, "error_type": 2, "integrity_refusal_claimed": 0, "name": 2, "refused": 0},
    ),
    ("list", 1, (108,)),
    ("dict", {"bytes": 1, "mode": 1, "path": 2, "sha256": 2, "source_path": 2}),
    ("list", 1631, (110,)),
    ("dict", {"bytes": 1, "name": 2, "path": 2, "sha256": 2}),
    ("list", 31, (112,)),
    (
        "dict",
        {
            "audit": 15,
            "checkpoint_states": 17,
            "completion_cid": 2,
            "copied_bytes": 1,
            "copied_files": 1,
            "copied_members": 111,
            "current_head": 23,
            "fresh_native_receiving_required": 0,
            "inherited_reference_pages": 1,
            "inherited_scan_pages": 1,
            "inherited_setup_epochs": 1,
            "native_owners_opened": 0,
            "native_result": 15,
            "new_fitting_epochs": 1,
            "new_scan_pages": 1,
            "previous_head": 23,
            "previous_version_id": 2,
            "proof_authority": 0,
            "qualified": 0,
            "reader": 15,
            "reader_control_scope": 2,
            "reader_control_source_namespace": 2,
            "reader_controls": 15,
            "root_cid": 2,
            "scan_execution_attested": 0,
            "schema": 2,
            "selected_producers": 113,
            "selected_version_id": 2,
            "selection_cid": 2,
            "source_archive_inventory_cid": 2,
            "source_delta_cid": 2,
            "source_execution_attested": 0,
            "source_namespace": 2,
            "staged_destination": 2,
        },
    ),
    (
        "dict",
        {
            "fresh_native_receiving_required": 0,
            "native_owners_opened": 0,
            "new_fitting_epochs": 1,
            "new_scan_pages": 1,
            "output": 2,
            "proof_authority": 0,
            "qualified": 0,
            "schema": 2,
            "seed": 2,
            "staged_receipt": 114,
            "staged_receipt_sha256": 2,
        },
    ),
    ("dict", {"schema": 2, "selection_idle_reason": 2}),
    ("dict", {"schema": 2}),
    ("dict", {"daemon_pid": 58, "schema": 2, "status": 2, "supervisor_pid": 1}),
    (
        "dict",
        {
            "exception_types": 100,
            "git_dubious_ownership": 0,
            "log_bytes": 1,
            "path": 2,
            "tail_sha256": 2,
            "traceback_frames": 100,
        },
    ),
    ("list", 2, (119,)),
    (
        "dict",
        {
            "admitted_database_daemon_pass_heartbeat.json": 116,
            "admitted_native_owner_heartbeat.json": 117,
            "admitted_supervisor_status.json": 118,
            "exception_types": 100,
            "git_dubious_ownership": 0,
            "logs": 120,
            "schema": 2,
            "traceback_frames": 100,
        },
    ),
    ("dict", {"SUCCESSOR-FORMAT": 1, "SUCCESSOR-TYPE": 1}),
    ("dict", {"boot_id": 2, "parent_pid": 1, "pid": 1, "start_time_ticks": 1}),
    (
        "dict",
        {
            "attempt": 1,
            "branch": 2,
            "canonical_task_cid": 2,
            "created_at": 5,
            "expires_at": 5,
            "fence": 1,
            "lane_id": 2,
            "lease_id": 2,
            "merge_target": 2,
            "owner": 123,
            "record_id": 2,
            "repo_root": 2,
            "schema": 2,
            "state": 2,
            "state_dir": 2,
            "task_id": 2,
            "terminal_reason": 2,
            "updated_at": 5,
            "workspace_path": 2,
        },
    ),
    ("list", 2, (124,)),
    ("list", 18, (10,)),
    (
        "dict",
        {
            "attempt_id": 2,
            "authoritative_task_store": 2,
            "binding_id": 2,
            "claim_id": 2,
            "control_binding_id": 2,
            "control_expected_revision": 1,
            "control_portal_binding_basis_cid": 2,
            "control_task_projection_cid": 2,
            "fence_epoch": 1,
            "fencing_token": 1,
            "goal_cid": 2,
            "interface": 2,
            "lease_id": 2,
            "plan_cid": 2,
            "projection_authority": 0,
            "projection_immutable_digest": 2,
            "projection_seed_digest": 2,
            "schema": 2,
            "task_alias": 2,
            "task_body_digest": 2,
            "task_cid": 2,
            "task_revision": 1,
        },
    ),
    (
        "dict",
        {
            "exists": 0,
            "path": 2,
            "reason": 2,
            "repository": 2,
            "repository_ref": 2,
            "task_id": 2,
            "tracked": 0,
            "tracked_path": 2,
        },
    ),
    ("list", 1, (128,)),
    (
        "dict",
        {
            "checks": 129,
            "missing_outputs": 100,
            "mode": 2,
            "passed": 0,
            "reason": 2,
            "repository_ref": 2,
            "task_ids": 87,
            "unsafe_outputs": 100,
            "untracked_outputs": 100,
        },
    ),
    (
        "dict",
        {
            "implementation_commit": 2,
            "integration_commit": 2,
            "integration_ref": 2,
            "passed": 0,
            "reasons": 100,
            "target_branch": 2,
        },
    ),
    (
        "dict",
        {
            "attempt_id": 2,
            "attempt_number": 1,
            "authority": 2,
            "baseline_ref": 2,
            "board_namespace": 2,
            "canonical_task_cid": 2,
            "canonical_task_key": 2,
            "changed_path_diff_sha256": 2,
            "claim_id": 2,
            "configured_board_admission_cid": 2,
            "database_attempt_binding": 127,
            "database_task_cid": 2,
            "declared_output_invariant": 130,
            "fencing_token": 1,
            "implementation_commit": 2,
            "implementation_tree": 2,
            "integration_commit_proof": 131,
            "merge_commit": 2,
            "merge_request_dedupe_key": 2,
            "merge_request_digest": 2,
            "merge_tree": 2,
            "portal_attempt_number": 1,
            "portal_event_log_sha256": 2,
            "request_id": 2,
            "schema": 2,
            "target_branch": 2,
            "target_repository_id": 2,
            "task_alias": 2,
            "task_completion_authority": 0,
            "transition_cid": 2,
            "worker_self_approval": 0,
        },
    ),
    (
        "dict",
        {
            "accepted_source_transition": 132,
            "argv": 87,
            "attempt_id": 2,
            "evidence_digest": 2,
            "outcome": 2,
            "portal_receipt_id": 2,
            "task_cid": 2,
            "validator": 2,
        },
    ),
    ("dict", {"validation": 133}),
    (
        "dict",
        {
            "attempt_id": 2,
            "attempt_number": 1,
            "body": 134,
            "claim_id": 2,
            "control_expected_revision": 1,
            "control_expected_status": 2,
            "evidence_digest": 2,
            "fence_epoch": 1,
            "fencing_token": 1,
            "lease_id": 2,
            "owner_session_id": 2,
            "preparation_digest": 2,
            "prepared_at_ms": 1,
            "replayed": 0,
            "schema": 2,
            "status": 2,
            "task_cid": 2,
        },
    ),
    (
        "dict",
        {
            "attempt_id": 2,
            "claim_id": 2,
            "coordination_preparation": 135,
            "evidence_digest": 2,
            "fence_epoch": 1,
            "fencing_token": 1,
            "lease_id": 2,
            "operation": 2,
            "owner_session_id": 2,
            "validation": 133,
        },
    ),
    ("dict", {"identity": 2, "profile_id": 2, "signature": 2}),
    (
        "dict",
        {
            "ipfs_datasets_py.logic.software_contracts.codebase_inventory_lineage": 2,
            "ipfs_datasets_py.logic.software_contracts.codebase_inventory_projection_replay": 2,
            "ipfs_datasets_py.logic.software_contracts.codebase_inventory_receiving": 2,
            "ipfs_datasets_py.logic.software_contracts.codebase_inventory_resume": 2,
            "ipfs_datasets_py.logic.software_contracts.codebase_inventory_scan": 2,
            "ipfs_datasets_py.logic.software_contracts.codebase_inventory_targets": 2,
            "ipfs_datasets_py.logic.software_contracts.codebase_ir": 2,
            "ipfs_datasets_py.logic.software_contracts.codebase_ir_targets": 2,
            "ipfs_datasets_py.logic.software_contracts.codebase_source_training": 2,
            "ipfs_datasets_py.logic.software_contracts.duckdb_ast_store": 2,
            "ipfs_datasets_py.logic.software_contracts.semantic_index.snapshot": 2,
            "ipfs_datasets_py.optimizers.logic_theorem_optimizer.autoencoder_projection_features": 2,
            "ipfs_datasets_py.optimizers.logic_theorem_optimizer.autoencoder_runtime_registry": 2,
            "ipfs_datasets_py.optimizers.logic_theorem_optimizer.codebase_feature_worker": 2,
            "ipfs_datasets_py.optimizers.logic_theorem_optimizer.codebase_inventory_feature_worker": 2,
            "ipfs_datasets_py.optimizers.logic_theorem_optimizer.codebase_inventory_resume_worker": 2,
            "ipfs_datasets_py.optimizers.logic_theorem_optimizer.modal_autoencoder_cuda": 2,
        },
    ),
    ("dict", {"files": 138, "scope": 2, "sha256": 2}),
    (
        "dict",
        {
            "max_file_bytes": 1,
            "max_inferred_rows": 1,
            "max_input_bytes": 1,
            "max_inventory_entries": 1,
            "max_manifest_bytes": 1,
            "max_output_bytes": 1,
            "max_pages": 1,
            "max_target_bytes": 1,
            "page_entries": 1,
        },
    ),
    ("list", 300, (2,)),
    ("dict", {"artifact": 15, "version_id": 2}),
    ("list", 2, (142,)),
    ("dict", {"codebase_ir.contracts@1": 1, "codebase_ir.program@1": 1}),
    (
        "dict",
        {
            "ancestry": 143,
            "artifact": 15,
            "artifact_cid": 2,
            "contract_sha256": 2,
            "feature_columns": 1,
            "feature_space_sha256": 2,
            "latent_width": 1,
            "projection_ids": 56,
            "projection_widths": 144,
            "state_sha256": 2,
            "variant_id": 2,
            "version_id": 2,
        },
    ),
    (
        "dict",
        {
            "dispositions": 26,
            "end": 1,
            "inferred_rows": 1,
            "membership_cid": 2,
            "page_cid": 2,
            "start": 1,
        },
    ),
    ("dict", {"deferred_budget": 1, "inferred": 1}),
    (
        "dict",
        {
            "dispositions": 147,
            "end": 1,
            "inferred_rows": 1,
            "membership_cid": 2,
            "page_cid": 2,
            "start": 1,
        },
    ),
    ("dict", {"inferred": 1, "opaque": 1, "parse_failed": 1, "unsupported_target": 1}),
    (
        "dict",
        {
            "dispositions": 149,
            "end": 1,
            "inferred_rows": 1,
            "membership_cid": 2,
            "page_cid": 2,
            "start": 1,
        },
    ),
    ("list", 10, (146, 148, 150)),
    (
        "dict",
        {
            "authority": 99,
            "completion_cid": 2,
            "coverage": 52,
            "head": 23,
            "head_cid": 2,
            "implementation": 139,
            "limits": 140,
            "member_paths": 141,
            "membership_cid": 2,
            "model": 145,
            "pages": 151,
            "root_cid": 2,
            "schema": 2,
        },
    ),
    ("dict", {"authority": 99, "evidence": 58, "full_context_cid": 2, "scan": 152, "schema": 2}),
    ("list", 1, (142,)),
    (
        "dict",
        {
            "ancestry": 154,
            "artifact": 15,
            "artifact_cid": 2,
            "contract_sha256": 2,
            "feature_columns": 1,
            "feature_space_sha256": 2,
            "latent_width": 1,
            "projection_ids": 56,
            "projection_widths": 144,
            "state_sha256": 2,
            "variant_id": 2,
            "version_id": 2,
        },
    ),
    (
        "dict",
        {
            "authority": 99,
            "completion_cid": 2,
            "current_head": 23,
            "current_membership_cid": 2,
            "full_context_cid": 2,
            "inventory_context_cid": 2,
            "model": 145,
            "previous_head": 23,
            "previous_membership_cid": 2,
            "previous_model": 155,
            "root_cid": 2,
            "schema": 2,
            "selection_cid": 2,
            "source_delta_cid": 2,
        },
    ),
    ("dict", {"program_root": 2, "request_cid": 2, "scan_cid": 2}),
    (
        "dict",
        {
            "explicit_proof_obligations": 100,
            "external_ir_roots": 100,
            "pending_assurance": 2,
            "production_activation": 0,
            "schema": 2,
            "scope": 2,
        },
    ),
    ("dict", {"executable": 0, "sha256": 2}),
    (
        "dict",
        {
            "README.md": 159,
            "added.py": 159,
            "bulk002.py": 159,
            "bulk003.py": 159,
            "bulk004.py": 159,
            "bulk005.py": 159,
            "bulk006.py": 159,
            "bulk007.py": 159,
            "bulk008.py": 159,
            "bulk009.py": 159,
            "bulk010.py": 159,
            "bulk011.py": 159,
            "bulk012.py": 159,
            "bulk013.py": 159,
            "bulk014.py": 159,
            "bulk015.py": 159,
            "bulk016.py": 159,
            "bulk017.py": 159,
            "bulk018.py": 159,
            "bulk019.py": 159,
            "bulk020.py": 159,
            "bulk021.py": 159,
            "bulk022.py": 159,
            "bulk023.py": 159,
            "bulk024.py": 159,
            "bulk025.py": 159,
            "bulk026.py": 159,
            "bulk027.py": 159,
            "bulk028.py": 159,
            "bulk029.py": 159,
            "bulk030.py": 159,
            "bulk031.py": 159,
            "bulk032.py": 159,
            "bulk033.py": 159,
            "bulk034.py": 159,
            "bulk035.py": 159,
            "bulk036.py": 159,
            "bulk037.py": 159,
            "bulk038.py": 159,
            "bulk039.py": 159,
            "bulk040.py": 159,
            "bulk041.py": 159,
            "bulk042.py": 159,
            "bulk043.py": 159,
            "bulk044.py": 159,
            "bulk045.py": 159,
            "bulk046.py": 159,
            "bulk047.py": 159,
            "bulk048.py": 159,
            "bulk049.py": 159,
            "bulk050.py": 159,
            "bulk051.py": 159,
            "bulk052.py": 159,
            "bulk053.py": 159,
            "bulk054.py": 159,
            "bulk055.py": 159,
            "bulk056.py": 159,
            "bulk057.py": 159,
            "bulk058.py": 159,
            "bulk059.py": 159,
            "bulk060.py": 159,
            "bulk061.py": 159,
            "bulk062.py": 159,
            "bulk063.py": 159,
            "bulk064.py": 159,
            "bulk065.py": 159,
            "bulk066.py": 159,
            "bulk067.py": 159,
            "bulk068.py": 159,
            "bulk069.py": 159,
            "bulk070.py": 159,
            "bulk071.py": 159,
            "bulk072.py": 159,
            "bulk073.py": 159,
            "bulk074.py": 159,
            "bulk075.py": 159,
            "bulk076.py": 159,
            "bulk077.py": 159,
            "bulk078.py": 159,
            "bulk079.py": 159,
            "bulk080.py": 159,
            "bulk081.py": 159,
            "bulk082.py": 159,
            "bulk083.py": 159,
            "bulk084.py": 159,
            "bulk085.py": 159,
            "bulk086.py": 159,
            "bulk087.py": 159,
            "bulk088.py": 159,
            "bulk089.py": 159,
            "bulk090.py": 159,
            "bulk091.py": 159,
            "bulk092.py": 159,
            "bulk093.py": 159,
            "bulk094.py": 159,
            "bulk095.py": 159,
            "bulk096.py": 159,
            "bulk097.py": 159,
            "bulk098.py": 159,
            "bulk099.py": 159,
            "bulk100.py": 159,
            "bulk101.py": 159,
            "bulk102.py": 159,
            "bulk103.py": 159,
            "bulk104.py": 159,
            "bulk105.py": 159,
            "bulk106.py": 159,
            "bulk107.py": 159,
            "bulk108.py": 159,
            "bulk109.py": 159,
            "bulk110.py": 159,
            "bulk111.py": 159,
            "bulk112.py": 159,
            "bulk113.py": 159,
            "bulk114.py": 159,
            "bulk115.py": 159,
            "bulk116.py": 159,
            "bulk117.py": 159,
            "bulk118.py": 159,
            "bulk119.py": 159,
            "bulk120.py": 159,
            "bulk121.py": 159,
            "bulk122.py": 159,
            "bulk123.py": 159,
            "bulk124.py": 159,
            "bulk125.py": 159,
            "bulk126.py": 159,
            "bulk127.py": 159,
            "bulk128.py": 159,
            "bulk129.py": 159,
            "bulk130.py": 159,
            "bulk131.py": 159,
            "bulk132.py": 159,
            "bulk133.py": 159,
            "bulk134.py": 159,
            "bulk135.py": 159,
            "bulk136.py": 159,
            "bulk137.py": 159,
            "bulk138.py": 159,
            "bulk139.py": 159,
            "bulk140.py": 159,
            "bulk141.py": 159,
            "bulk142.py": 159,
            "bulk143.py": 159,
            "bulk144.py": 159,
            "bulk145.py": 159,
            "bulk146.py": 159,
            "bulk147.py": 159,
            "bulk148.py": 159,
            "bulk149.py": 159,
            "bulk150.py": 159,
            "bulk151.py": 159,
            "bulk152.py": 159,
            "bulk153.py": 159,
            "bulk154.py": 159,
            "bulk155.py": 159,
            "bulk156.py": 159,
            "bulk157.py": 159,
            "bulk158.py": 159,
            "bulk159.py": 159,
            "bulk160.py": 159,
            "bulk161.py": 159,
            "bulk162.py": 159,
            "bulk163.py": 159,
            "bulk164.py": 159,
            "bulk165.py": 159,
            "bulk166.py": 159,
            "bulk167.py": 159,
            "bulk168.py": 159,
            "bulk169.py": 159,
            "bulk170.py": 159,
            "bulk171.py": 159,
            "bulk172.py": 159,
            "bulk173.py": 159,
            "bulk174.py": 159,
            "bulk175.py": 159,
            "bulk176.py": 159,
            "bulk177.py": 159,
            "bulk178.py": 159,
            "bulk179.py": 159,
            "bulk180.py": 159,
            "bulk181.py": 159,
            "bulk182.py": 159,
            "bulk183.py": 159,
            "bulk184.py": 159,
            "bulk185.py": 159,
            "bulk186.py": 159,
            "bulk187.py": 159,
            "bulk188.py": 159,
            "bulk189.py": 159,
            "bulk190.py": 159,
            "bulk191.py": 159,
            "bulk192.py": 159,
            "bulk193.py": 159,
            "bulk194.py": 159,
            "bulk195.py": 159,
            "bulk196.py": 159,
            "bulk197.py": 159,
            "bulk198.py": 159,
            "bulk199.py": 159,
            "bulk200.py": 159,
            "bulk201.py": 159,
            "bulk202.py": 159,
            "bulk203.py": 159,
            "bulk204.py": 159,
            "bulk205.py": 159,
            "bulk206.py": 159,
            "bulk207.py": 159,
            "bulk208.py": 159,
            "bulk209.py": 159,
            "bulk210.py": 159,
            "bulk211.py": 159,
            "bulk212.py": 159,
            "bulk213.py": 159,
            "bulk214.py": 159,
            "bulk215.py": 159,
            "bulk216.py": 159,
            "bulk217.py": 159,
            "bulk218.py": 159,
            "bulk219.py": 159,
            "bulk220.py": 159,
            "bulk221.py": 159,
            "bulk222.py": 159,
            "bulk223.py": 159,
            "bulk224.py": 159,
            "bulk225.py": 159,
            "bulk226.py": 159,
            "bulk227.py": 159,
            "bulk228.py": 159,
            "bulk229.py": 159,
            "bulk230.py": 159,
            "bulk231.py": 159,
            "bulk232.py": 159,
            "bulk233.py": 159,
            "bulk234.py": 159,
            "bulk235.py": 159,
            "bulk236.py": 159,
            "bulk237.py": 159,
            "bulk238.py": 159,
            "bulk239.py": 159,
            "bulk240.py": 159,
            "bulk241.py": 159,
            "bulk242.py": 159,
            "bulk243.py": 159,
            "bulk244.py": 159,
            "bulk245.py": 159,
            "bulk246.py": 159,
            "bulk247.py": 159,
            "bulk248.py": 159,
            "bulk249.py": 159,
            "bulk250.py": 159,
            "bulk251.py": 159,
            "bulk252.py": 159,
            "bulk253.py": 159,
            "bulk254.py": 159,
            "bulk255.py": 159,
            "bulk256.py": 159,
            "bulk257.py": 159,
            "bulk258.py": 159,
            "bulk259.py": 159,
            "bulk260.py": 159,
            "bulk261.py": 159,
            "bulk262.py": 159,
            "bulk263.py": 159,
            "bulk264.py": 159,
            "bulk265.py": 159,
            "bulk266.py": 159,
            "bulk267.py": 159,
            "bulk268.py": 159,
            "bulk269.py": 159,
            "bulk270.py": 159,
            "bulk271.py": 159,
            "bulk272.py": 159,
            "bulk273.py": 159,
            "bulk274.py": 159,
            "bulk275.py": 159,
            "bulk276.py": 159,
            "bulk277.py": 159,
            "bulk278.py": 159,
            "bulk279.py": 159,
            "bulk280.py": 159,
            "bulk281.py": 159,
            "bulk282.py": 159,
            "bulk283.py": 159,
            "bulk284.py": 159,
            "bulk285.py": 159,
            "bulk286.py": 159,
            "bulk287.py": 159,
            "bulk288.py": 159,
            "bulk289.py": 159,
            "bulk290.py": 159,
            "calc.py": 159,
            "canary.py": 159,
            "check_offset.py": 159,
            "check_type.py": 159,
            "malformed.py": 159,
            "non_utf8.py": 159,
            "oversized.dat": 159,
            "renamed.py": 159,
            "tune.py": 159,
        },
    ),
    ("dict", {"criterion": 2, "criterion_key": 2, "evidence_cids": 100, "validation_keys": 87}),
    ("list", 1, (161,)),
    ("dict", {"effect": 2, "media_type": 2, "path": 2}),
    ("list", 1, (163,)),
    (
        "dict",
        {"argv": 86, "cwd": 2, "expected_exit_codes": 53, "policy_cid": 2, "validation_key": 2},
    ),
    ("list", 1, (165,)),
    (
        "dict",
        {
            "acceptance": 162,
            "dependencies": 100,
            "outputs": 164,
            "scope_paths": 64,
            "task_key": 2,
            "validations": 166,
        },
    ),
    (
        "dict",
        {
            "acceptance": 162,
            "dependencies": 87,
            "outputs": 164,
            "scope_paths": 64,
            "task_key": 2,
            "validations": 166,
        },
    ),
    ("list", 2, (167, 168)),
    (
        "dict",
        {
            "baseline_commit": 2,
            "codebase_inventory_context": 153,
            "codebase_successor_context": 156,
            "created_outputs": 100,
            "lifecycle_dir": 2,
            "planning_roots": 157,
            "policy": 158,
            "profile_content_id": 2,
            "profile_dir": 2,
            "repository": 2,
            "repository_cid": 2,
            "schema": 2,
            "sources": 160,
            "tasks": 169,
        },
    ),
    ("dict", {"binding": 137, "payload": 170}),
    ("dict", {"check_ids": 87, "id": 2, "kind": 2, "source_scope_ids": 64}),
    ("dict", {"criterion": 172, "policy_ids": 87}),
    (
        "dict",
        {
            "contract_version": 1,
            "fallback_check_ids": 56,
            "freshness_seconds": 58,
            "kind": 2,
            "metadata": 173,
            "minimum_code_assurance": 2,
            "phase": 2,
            "required": 0,
            "requirement_id": 2,
            "schema": 2,
            "source_scope_ids": 87,
            "subject_ids": 87,
        },
    ),
    (
        "dict",
        {
            "contract_version": 1,
            "fallback_check_ids": 87,
            "freshness_seconds": 58,
            "kind": 2,
            "metadata": 173,
            "minimum_code_assurance": 2,
            "phase": 2,
            "required": 0,
            "requirement_id": 2,
            "schema": 2,
            "source_scope_ids": 64,
            "subject_ids": 87,
        },
    ),
    ("list", 4, (174, 175)),
    (
        "dict",
        {
            "dependencies": 87,
            "graph_cid": 2,
            "intent_owner_id": 2,
            "manifest": 171,
            "manifest_cid": 2,
            "pending_cid": 2,
            "pending_requirements": 176,
            "plan_id": 2,
            "planning_receipt_cid": 2,
            "schema": 2,
            "task_cid": 2,
            "task_key": 2,
            "task_spec": 168,
        },
    ),
    ("dict", {"binding": 137, "payload": 177}),
    ("dict", {"completion_receipt": 136, "local_planning_contract": 178, "title": 2}),
    ("dict", {"body": 179, "revision": 1, "status": 2, "task_cid": 2}),
    (
        "dict",
        {
            "child_process_slots": 1,
            "cpu_slots": 1,
            "gpu_memory_mb": 58,
            "memory_mb": 1,
            "unified_memory_mb": 1,
        },
    ),
    (
        "dict",
        {
            "child_process_slots": 1,
            "cpu_slots": 1,
            "gpu_memory_mb": 58,
            "memory_mb": 1,
            "reserved_gpu_memory_mb": 1,
            "reserved_memory_mb": 1,
            "unified_memory_mb": 1,
            "usable_gpu_memory_mb": 58,
            "usable_memory_mb": 1,
        },
    ),
    ("dict", {"orchestration": 79, "snapshot_evaluation": 79}),
    (
        "dict",
        {
            "active_child_lease_count": 1,
            "active_lease_count": 1,
            "active_root_lease_count": 1,
            "allocated": 74,
            "allocated_child_process_slots": 1,
            "allocated_gpu_memory_mb": 1,
            "allocated_unified_memory_mb": 1,
            "available": 181,
            "capacity": 182,
            "counters": 77,
            "lanes": 183,
            "proof_backoff": 57,
            "saturation": 81,
            "schema_version": 2,
            "state_path": 2,
            "wait_time_seconds": 82,
            "waiting_request_count": 1,
        },
    ),
    (
        "dict",
        {
            "lane_reservations": 57,
            "max_gpu_memory_percent": 58,
            "max_memory_percent": 58,
            "max_swap_percent": 58,
            "max_waiting_requests": 1,
            "proof_backoff_seconds": 5,
            "proof_cpu_stall_percent": 5,
            "proof_io_stall_percent": 5,
            "proof_memory_headroom_mb": 1,
            "proof_memory_stall_percent": 5,
            "proof_safety_enabled": 0,
            "require_known_gpu_for_gpu_work": 0,
            "reserved_gpu_memory_mb": 1,
            "reserved_memory_mb": 1,
            "total_child_process_slots": 1,
            "total_cpu_slots": 1,
            "total_gpu_memory_mb": 58,
            "total_memory_mb": 1,
            "total_unified_memory_mb": 1,
        },
    ),
    (
        "dict",
        {
            "content_id": 2,
            "contract_version": 1,
            "max_depth": 1,
            "max_effects": 1,
            "max_items": 1,
            "max_paths": 1,
            "max_serialized_bytes": 1,
            "max_text_bytes": 1,
            "schema": 2,
            "timeout_ms": 1,
        },
    ),
    ("list", 66, (2,)),
    (
        "dict",
        {
            "argv": 187,
            "boot_id": 2,
            "configuration_root": 2,
            "cwd": 2,
            "executable": 2,
            "fencing_epoch": 1,
            "identity_id": 2,
            "parent_pid": 1,
            "pid": 1,
            "process_group_id": 1,
            "profile_id": 2,
            "repository_root": 2,
            "run_id": 2,
            "run_root": 2,
            "schema": 2,
            "session_id": 1,
            "start_time_ticks": 1,
            "state_root": 2,
            "target_id": 2,
        },
    ),
    (
        "dict",
        {
            "health_window_ms": 1,
            "new_process_identity": 188,
            "old_tree_fenced": 0,
            "receipt_id": 2,
            "transition_artifact_sha256": 2,
            "transition_id": 2,
        },
    ),
    (
        "dict",
        {
            "applied": 0,
            "authority": 2,
            "content_id": 2,
            "contract_version": 1,
            "effect_id": 2,
            "kind": 2,
            "paths": 56,
            "receipt_id": 2,
            "resource": 2,
            "schema": 2,
        },
    ),
    ("list", 1, (190,)),
    (
        "dict",
        {
            "audit_receipt_id": 2,
            "authority": 2,
            "bounds": 186,
            "caller": 2,
            "contract_version": 1,
            "data": 189,
            "effects": 191,
            "error": 58,
            "idempotency_key": 2,
            "objective_id": 2,
            "operation": 2,
            "policy_id": 2,
            "preview": 58,
            "repository_id": 2,
            "request_id": 2,
            "schema": 2,
            "status": 2,
            "tree_id": 2,
        },
    ),
    (
        "dict",
        {
            "completion_authority": 0,
            "namespaces": 66,
            "returncode": 1,
            "schema": 2,
            "single_worker": 0,
            "worker_uid": 1,
        },
    ),
    (
        "dict",
        {
            "health_window_ms": 1,
            "isolated_worker_cleanup": 193,
            "new_process_identity": 58,
            "old_tree_fenced": 0,
            "receipt_id": 2,
            "transition_artifact_sha256": 2,
            "transition_id": 2,
        },
    ),
    (
        "dict",
        {
            "audit_receipt_id": 2,
            "authority": 2,
            "bounds": 186,
            "caller": 2,
            "contract_version": 1,
            "data": 194,
            "effects": 191,
            "error": 58,
            "idempotency_key": 2,
            "objective_id": 2,
            "operation": 2,
            "policy_id": 2,
            "preview": 58,
            "repository_id": 2,
            "request_id": 2,
            "schema": 2,
            "status": 2,
            "tree_id": 2,
        },
    ),
    ("dict", {"revision": 1, "status": 2}),
    ("list", 2, (196,)),
    (
        "dict",
        {
            "384d_qualified": 0,
            "authored_worker_receipt": 107,
            "bootstrap_errors": 100,
            "complete_scan_reexecuted_here": 0,
            "completion_cid": 2,
            "container_resource_authority_pin": 15,
            "controls": 109,
            "cuda_qualified": 0,
            "current_head": 23,
            "elapsed_seconds_so_far": 5,
            "final_resource_cleanup_verified": 0,
            "final_resources": 54,
            "full_administrator_population_completed": 0,
            "inference_attempt_count": 1,
            "inherited_reference_pages": 1,
            "inherited_scan_pages": 1,
            "inherited_setup_epochs": 1,
            "local_pool_bounded_by_host_envelope": 0,
            "materialization": 115,
            "native_diagnostics": 121,
            "native_source_generation_advanced": 0,
            "native_task_body_bytes": 122,
            "native_task_statuses": 84,
            "native_worker_qualified": 0,
            "new_fitting_epochs": 1,
            "new_reference_pages": 1,
            "new_scan_pages": 1,
            "numerical_after": 17,
            "numerical_before": 17,
            "observed_worker_allocations": 125,
            "operation_deadlines": 85,
            "original_source_artifacts_preserved": 0,
            "overall_deadline_seconds": 5,
            "paired_close_seconds": 5,
            "paired_entry_seconds": 5,
            "phases": 126,
            "pid": 1,
            "post_setup_fit_attempt_count": 1,
            "previous_head": 23,
            "previous_version_id": 2,
            "production_default_activated": 0,
            "proof_authority": 0,
            "provider_calls": 1,
            "public_receivers_reference_close": 91,
            "publication": 90,
            "qualified": 0,
            "recorded_seconds": 5,
            "reference_scope": 2,
            "remaining_processes": 1,
            "residual_task": 180,
            "resource_after_native_owner_close": 54,
            "resource_before_stop": 184,
            "root_cid": 2,
            "scan_coverage": 52,
            "scan_execution_attested": 0,
            "scheduler_configuration": 185,
            "scheduler_state_path": 2,
            "schema": 2,
            "scope": 2,
            "selected_version_id": 2,
            "selection_cid": 2,
            "shares_host_pid_state": 0,
            "source_delta_cid": 2,
            "source_execution_attested": 0,
            "start": 192,
            "stop": 195,
            "task_observations": 197,
            "worker_launched": 0,
        },
    ),
    (
        "dict",
        {
            "content_id": 2,
            "contract_version": 1,
            "criterion": 2,
            "criterion_key": 2,
            "evidence_cids": 100,
            "schema": 2,
            "validation_keys": 87,
        },
    ),
    ("list", 2, (199,)),
    (
        "dict",
        {
            "acceptance": 200,
            "assumptions": 100,
            "content_id": 2,
            "contract_version": 1,
            "created_at_ms": 1,
            "dependency_goal_cids": 100,
            "evidence_cids": 100,
            "goal_key": 2,
            "objective": 2,
            "parent_goal_cid": 2,
            "provenance": 57,
            "rationale": 2,
            "risks": 100,
            "schema": 2,
            "scope_paths": 64,
            "status": 2,
            "title": 2,
            "updated_at_ms": 1,
        },
    ),
    ("list", 1, (201,)),
    ("list", 1, (199,)),
    (
        "dict",
        {
            "content_id": 2,
            "contract_version": 1,
            "effect": 2,
            "media_type": 2,
            "path": 2,
            "schema": 2,
        },
    ),
    ("list", 1, (204,)),
    (
        "dict",
        {
            "argv": 86,
            "content_id": 2,
            "contract_version": 1,
            "cwd": 2,
            "expected_exit_codes": 53,
            "policy_cid": 2,
            "schema": 2,
            "validation_key": 2,
        },
    ),
    ("list", 1, (206,)),
    (
        "dict",
        {
            "acceptance": 203,
            "assumptions": 100,
            "bundle": 2,
            "content_id": 2,
            "contract_version": 1,
            "created_at_ms": 1,
            "dependency_task_cids": 100,
            "evidence_cids": 100,
            "fallback_behavior": 2,
            "goal_cid": 2,
            "objective": 2,
            "outputs": 205,
            "parallel_lane": 2,
            "policy_roots": 87,
            "predicted_files": 87,
            "priority": 2,
            "provenance": 57,
            "rationale": 2,
            "resource_class": 2,
            "risks": 100,
            "schema": 2,
            "scope_paths": 64,
            "status": 2,
            "task_key": 2,
            "track": 2,
            "updated_at_ms": 1,
            "validations": 207,
        },
    ),
    (
        "dict",
        {
            "acceptance": 203,
            "assumptions": 100,
            "bundle": 2,
            "content_id": 2,
            "contract_version": 1,
            "created_at_ms": 1,
            "dependency_task_cids": 87,
            "evidence_cids": 100,
            "fallback_behavior": 2,
            "goal_cid": 2,
            "objective": 2,
            "outputs": 205,
            "parallel_lane": 2,
            "policy_roots": 87,
            "predicted_files": 87,
            "priority": 2,
            "provenance": 57,
            "rationale": 2,
            "resource_class": 2,
            "risks": 100,
            "schema": 2,
            "scope_paths": 64,
            "status": 2,
            "task_key": 2,
            "track": 2,
            "updated_at_ms": 1,
            "validations": 207,
        },
    ),
    ("list", 2, (208, 209)),
    (
        "dict",
        {
            "contract_version": 1,
            "created_at_ms": 1,
            "evidence": 100,
            "goals": 202,
            "policy_roots": 87,
            "program_root": 2,
            "request_cid": 2,
            "scan_cid": 2,
            "schema": 2,
            "status": 2,
            "tasks": 210,
            "uncertainty_debt": 100,
            "unresolved_questions": 100,
            "updated_at_ms": 1,
        },
    ),
    ("dict", {"max_annotations": 1, "max_depth": 1, "max_edges": 1, "max_nodes": 1}),
    ("list", 303, (2,)),
    ("list", 304, (2,)),
    (
        "dict",
        {
            "baguqeera23hjcye5cappcsorf5wrb4epuezc5e4htfjruobq3fa3aki7hyma": 56,
            "baguqeera24rohvhbyzoxsofrzejfoytpahx2m243bbc72fa3xe4pz3nltfna": 56,
            "baguqeera2aitbsouorjwo73h2gi2st6ipgfam5e7kp4k4ujxjgrebnibff6a": 56,
            "baguqeera2m3tunntteqcj4p4luarzyx4kgqwyjsa7vj4r2lwk57rdxpilcja": 56,
            "baguqeera2vp5weposi7qeprdklotsifskfiuoyynxrv463k24hd5qq3altcq": 56,
            "baguqeera2wq7koxpblq2qr24wsyyhzmxdy3cevssfi3yay2npxfpsexbd6ca": 56,
            "baguqeera367ezccsp2iywv6n3s4ovxpmyfanhhbtqnyks7gz7klpwlrhma6a": 56,
            "baguqeera36ccoojxnwbyf4jfe54hdu5kyra6uuommiafgam5xgupy3hia5bq": 56,
            "baguqeera37m7u5th4dzhpl26gwf6oqpurh4hznvk7gaba2k6wdakb57mjjyq": 56,
            "baguqeera3cwkpm3ut3ckzgk35qtn2goxuj7opd6erwvngzfpgdoizm2v7coq": 56,
            "baguqeera3gbl7qkicorqf43bcv4vxfgey25vnzcno6d5vont3p5xsijszv7q": 56,
            "baguqeera3o6gcjsfijui6orhcyzrhzx3gvgou4j2veymxmxyalhvjt7l5n6a": 56,
            "baguqeera3rfo3k2curg4dvlf7ujmljn4v3r7ilqlgyxe6ud4vsztomfcxyka": 56,
            "baguqeera3snvpafwsp7eiyefht6mtuuuvuhd4a4cdldzoejynwbhax7wh7gq": 56,
            "baguqeera3u56u64r2fhdehkwfml6huoijelyh3xv34efrwa6wb4mqimksqra": 56,
            "baguqeera3ujdvd42c3bsj5iexoxj5pneqs3loirmplqs3f452gb5fawxcpxq": 56,
            "baguqeera3yexy2xfb3p6wnfhlrd6xq47khuuwylvypvw3uhxw4el44lveqja": 56,
            "baguqeera3zkftytq4hk3px723nwipozmijttos4736vewczzfafp3hugfyea": 56,
            "baguqeera44bsfosmio7iccc3ibfv2iyz7ilt5nffunmlwvkflkstk74fj6rq": 56,
            "baguqeera46vwso5zy6nqe5ciqdqhie7fuc6zmvmjpyciwnmm6tegrp766odq": 56,
            "baguqeera47h3gtoim5eu4l77o3w2sszfb4fmndzsf7homhmcvzs3ro6o3ysq": 56,
            "baguqeera4f3vc2folmoq7ttou2quvqfzyngxwfrgxdpmc5raewvw6wpwmvfq": 56,
            "baguqeera4kzbynrqpqzbibs3uh6o2qrxn3mls5siqylzootmow2wiwge6gaq": 56,
            "baguqeera4msyjvhi6aie5egpgfluz2drvud7qdvej6ypjhll6xyedv6zhloq": 56,
            "baguqeera4plk4gzjz5whmpnwu7oehxb77pwhd5kqz2ja7cbvy5jc4geobo3q": 56,
            "baguqeera4vswhxqfqtlkdawkmga6hdrlzw5adnlhoi4saw4cuwwemafa6rrq": 56,
            "baguqeera4xfukw45hujsur4gwdvhkblabhcvzmeyuilms53eg4div75fdqka": 56,
            "baguqeera4ytc7ye5bqxyj5ejj3t6bkifo647ah6gorshc2k3h7j2z5hj75da": 56,
            "baguqeera55366iipu4vcrskoa3xtgntb2thf7t2blxqwvyzqqlcbbqxvs5pq": 56,
            "baguqeera56puay3z3lckmhxwngbb3xi2mpee63hvidxxnskksj5sjyf72niq": 56,
            "baguqeera5a4ldlfz4fznvlievcdzfaen4ez4ll7ifybirlsthd4vracrwenq": 56,
            "baguqeera5bthofqxrfub3q42myfh2g4pqvtak3lkbeqlbwdusbjubqapoefq": 56,
            "baguqeera5eir5qbelhawvwqmw7jxfdbeogcnjebxs6s6l6oclljclng25hka": 56,
            "baguqeera5ejjmipztqflmtmmippepzzotaxc5atwxdvzof4q6c25c2ehha2q": 56,
            "baguqeera5fjuegwu2a42nf3jmnlqf3bnuror7kr5w7ambrbqriubxcvmfg3a": 56,
            "baguqeera5jefljwzo6vnwl5qvwfvlfem3urcvxhzubcsqkdpbqiqzbsyy36a": 56,
            "baguqeera5ni7ispstwijggvrwq2hloxgnksi6ztrjiksndbss5r6g5x4vpjq": 56,
            "baguqeera5oo47opruqxcd7ljhwqpg3lo2sr5473sd6rki73yh2ui3gdc6xva": 56,
            "baguqeera6eyo4se3ezj2r6g3uyyctdcvwps3flklok2nk6534n7ogmxuvvwq": 56,
            "baguqeera6gtfk4dvkyxatmjgalmpkoxc2oe7frhmczmynjajuvslmvaqmffa": 56,
            "baguqeera6ilzxmypgrqdpe6xtzgaftwv4rteny2eiq4k7b73svpfionrbvna": 56,
            "baguqeera6j2yx635zz4by5cv7nhbpzn6rwjeizsmha5c2vuibfy4l4kxosfq": 56,
            "baguqeera6mlaac4u5k7vurgogewnnxv3va7tlrynh5onctvos6n2nohsafpa": 56,
            "baguqeera6pygzctdufqtuqa7ac24ftorrpc5ssepafdiudoys77t6hljd3qa": 56,
            "baguqeera6syusoyubpok7fqaof7brnrrseseismkgj4yvxvl6ffvprm3u5wq": 56,
            "baguqeera6xrjywv7y7gylitspgwlgyuapbfa3jvnd7crkc73yw2rd6nybfxq": 56,
            "baguqeera6zndph3whzaoidgehapzpimhrq6rykarqt2iqv5hffvkjkqxvg2a": 56,
            "baguqeera76h2uckb7p2j52y72lmhu4i6hwajdvxjjyslbqqgni7av6hrmhmq": 56,
            "baguqeera776ft57tfkgh5ulq3ard4trukyoojox3rvyyqyc76stwyhs3eyaq": 56,
            "baguqeera7bjbbg42eyp67sz6j5ztcdtlaiekrymd5rxfyq727fhqamhmxglq": 56,
            "baguqeera7bsvjshztlzwiimnz7sptep5afhxqlcbrm3itsiqcdvj5dbnio4a": 56,
            "baguqeera7fvhdong2cykkxlerf3bwnpnxuoadk3eyywhszg2wcs7sftbto3q": 56,
            "baguqeera7irhgxpbwtcivez2yyxkx44vpyapmr6wcz63rz4bawzbd3qsypga": 56,
            "baguqeera7jqsj3hix75dkapk7htir2e555hqmumcei5ab52dp7fkhsak5zyq": 56,
            "baguqeera7krcrymmepydzsjfzycgwndpuq3cdcvhzso4ojqokzx5fcrug3va": 56,
            "baguqeera7pyuzvxutv7j5sc55jhk67xp6rdhylv2lsf2swccmjiii24h2w7q": 56,
            "baguqeera7uyd2ddbto2ospxcsc4mlsq37w3alu3ggj7rnfn2gr4fsshjikdq": 56,
            "baguqeeraa4zfa5u7arfbcanfajydulmsp2xd7i5axlsddgt3s36cxws7w4ba": 56,
            "baguqeeraa6p3i6uhni5b3a2ty5riamqtrcsscy5a55gdadylvfk773k57anq": 56,
            "baguqeeraabjuu2e26k3wzdnaq7hrhyibj5tp4ywgbyvisq56cxcwdrmdzn2a": 56,
            "baguqeeraaikjfzcbg4cm4xahkk3ndbrjnfzqexkll4novnjzxoiweyynrruq": 56,
            "baguqeeraatr62twa47sh4g6wszcalsgpab6k3y4gqpug6ku4gtr54xddz6oa": 56,
            "baguqeeraawgo6uetfs66pjzlu3e24glfqmljfrihe6shwozg2gfmq3hpzumq": 56,
            "baguqeerab3acckdf2voqu4vw6ybm2mfdyecx5kwn2cgvrpkobjqcmihlgymq": 56,
            "baguqeerab6ut5e2dvph6guu2b5jdgy74wmbv6jwfzdd4f7mrrjs4ys7m35ma": 56,
            "baguqeerabepxysbshzoudwja7cr36v435zciwq3tvua3prcjww74rfjghfdq": 56,
            "baguqeerabes4hz7equfjih55zlycbrmi4vv2atwwmmemtsh5b2pwj7f2z6qa": 56,
            "baguqeerabf5rmn5xodceyffhtuyr2ej4hdzhvswzac36uk6csqpc2ehf3cva": 56,
            "baguqeerablb3z7ucrv6aigve24axv2rewrq6syim6p2jyk6h2had53nxjf6a": 56,
            "baguqeerabmdnziu6s4lijl6jyrxv7uqcciu5c4ejkj4ittvumidbascb7nrq": 56,
            "baguqeerabomgu2ys5t7fyfhpk6jwwoc3ptfexv2hesw5yre7ehsdsydsrb7a": 56,
            "baguqeerabpbc2gveps3n4e5jimppkcvdd3e7hlzbjd7kzawzpfa4a2mnubhq": 56,
            "baguqeerabucag4tcwwtl74j2wpsx2ai3tdr45rwikqfcmfqzw2pz6tz6rora": 56,
            "baguqeerabulay3fhwzdhg6mjxhnlthbpuezmauaoge3o4azcgmwgwns2lhha": 56,
            "baguqeerac4vw3q7adlyptgsc62un74cbpdd5rgaoxcc5pcmjrvuczd2kzi6a": 56,
            "baguqeerac5fwpcir3ylbtrgzjsukytdmrkig3eckbyvcpov6bvdut3o46a7a": 56,
            "baguqeeracar67m6y2j3fejo5v6pmdgeym7nby2sbttjm33m3cocyvrxku2ea": 56,
            "baguqeeracbhmjncmnxvfo6zlolxjv2ecactzcq2n3ivxwrowbjoorvtgtoea": 56,
            "baguqeeracelep6md6jgg7matspdqcuvxpoczvx45dygcmgrvweuo72izeoya": 56,
            "baguqeeracfg2ehpzhyn57rrmfa26qehlxmcrlrfmoo6ahgmr2x5jxuv7uipq": 56,
            "baguqeerach7nbguvfa47wz4dbl3cblq23y4vwdfjoxcjwzt4swtt7465tzxq": 56,
            "baguqeerackobeohlykedsdf7ud6lrn64xllrq2leoqnhaqz7gaxiuowyvgha": 56,
            "baguqeeracm2zjmou23azye52qkmvm264owpswqgbufj4n7a37buv5yek5fca": 56,
            "baguqeeracnbh2smlm7kuuqffuxmwgc4zeae6w3xgnzo24ejtl6qyc42bn7oq": 56,
            "baguqeeracqx7rienm3hcewofbxrayhoclclmt7hpiqbz72t34xlacg372j4q": 56,
            "baguqeeracuwrcvbzc6isin73s5tkkz2dhwzik2pdigbmvfsca7zp7twvpela": 56,
            "baguqeeracz3oh2jzdl7bsck4xmfylve4kf7xovcpdwroirwdgk7olqww3eaq": 56,
            "baguqeerad7wc4gioatlztbegga3wkyptr5cyxwvqlvmyeo3oa7tp53ygvyfq": 56,
            "baguqeeradcylskb6lwetumquk4zzrzbklazvlwcp3jcjy7nus3k57mmfu6hq": 56,
            "baguqeeradd76z6izxbov2u6qvo2xwforwwr63jawccqzsog2r22naafj5c6a": 56,
            "baguqeeraddwsny45m7zvvqpjdkgrzlxtgclehhcmhuuo4sssm7t7thq3icvq": 56,
            "baguqeeradietg2skdfb2k7ahx77vp65he4ykiceydnfrfda57rfeocebei6a": 56,
            "baguqeeradodjwsf3otnphci5ypd2gfhzvjnxef2dsqdivlpkntul3q6uukiq": 56,
            "baguqeeradrhxo5ejvqwfx367xbpz6yfwjmbrv3kdfoipqo7i4juivwqoiv5a": 56,
            "baguqeeradta23jcxrpg4ki2yrumr2ee4pnwhe4q5avdtubsobgblqzbo2sgq": 56,
            "baguqeerae4m2t2ypncwyb7t73jrllgi7gsz2hmjkvpmanuvcby7ebwsmfhyq": 56,
            "baguqeeraeb3extxrwztlxt4u2r2udsqf2jzanweiu56famy73u3acdc67pgq": 56,
            "baguqeeraefuulssnvxgm2t6243p2rz5zkjwu33et7ts7whi3y224xxjca4iq": 56,
            "baguqeeraeg6ukozg7x7z6hhs4u7f2mv3zd252ozqiyp3juk675hiae7qewea": 56,
            "baguqeeraeh3nfd7p35yxkw5xm45qbx2dal4hk5tchpephharz7tclakz6i4q": 56,
            "baguqeeraeov7hlb36fwcd2vacqbwknllfwqnbd6r3us65td3jwkv57qlbwnq": 56,
            "baguqeeraeqvzuknffgfayy7hfwqifdywtbsjyf4bcelflttyxej766vbw3ga": 56,
            "baguqeeraeuk3j4r7rth5j6b5beooom5coestj2ztcn2gmzdw4z6fufagl3ua": 56,
            "baguqeeraevjc3nkkzjilit5hoyrgib7llndv3lvauaghquwlhcn3twzb3dsq": 56,
            "baguqeeraewlgbvnkqssqpszp3oyx2r7tkhongyfqruronbc6xfkmg7ehbrnq": 56,
            "baguqeeraezk2e46oq5u3ntwc5tb7tihdmkgy3u6lnhv4nuxwvsr2z37moywa": 56,
            "baguqeeraf6fmwlrd2wj7o2fgojqf4mpoczxldo6nu6srirgvkly7nw5x5xkq": 56,
            "baguqeerafcrtu66zv34c2yjmmg2oyxnkfheq6z6ixqnhxm37agdvwd4ssbaq": 56,
            "baguqeerafd7asg4ntsrr27sosiqpcipzybqknffdmdeewffvqcnmfsn46c6a": 56,
            "baguqeerafezek3q7jkt7lb3mh5zlhgfwt7i2cxpc4d4crsdwn7kokqx3l4uq": 56,
            "baguqeerafm3oufkpvqv5vmbjdlmp7ezdnuhz3d5sbomnloaxhq6gf6yrofdq": 56,
            "baguqeerafo3a4lwqczwvt7yiqcgw3bvey77ees7er7eshgczsc7j5tkmh3dq": 56,
            "baguqeerafoqr5rpxekp5tlwswinoewbdgg2ff574ld4b5qhzrwadbezxkoxq": 56,
            "baguqeerafqtt4n5r4wr5a6yctz6bga3visy7bxz55roadpfg2bpqazilmoea": 56,
            "baguqeerafrlqvzptfaxzgty4hb45hbw64pzdc6buzs3aguq56hgxmfyyvthq": 56,
            "baguqeerag46f5dcapl2aurwy7fr5fwkmkcb7n4n7632rzaelsm2k2e6r2i4a": 56,
            "baguqeeragab327yb5o2b4esg6humpdwymqeqqhnrznble7veq5z4ruiutona": 56,
            "baguqeeragcml4tk4bnpkfaj34lmi3vgpendg27iwbmynglui67hjksds4bhq": 56,
            "baguqeeragcwb5lt3b45tkmdqh2zcujnhfu7bh4ygmydeo6eqkmkczstr5dpq": 56,
            "baguqeeragf42sliign5a4yxjobcrj5fdzcttqq5tv5ffoi26p25gzunvbyzq": 56,
            "baguqeeraggo5qaf7pltuwrgwfd7cdfqrf233nyt7gsfmyl65r747uy4yimwa": 56,
            "baguqeeragj4cnukzws4yds2gccaac6odt5hsdaakrzszkqdoxvwmziyvxcaq": 56,
            "baguqeeragjexjycjmjowzthnhsfmdik3ey73waifdvjuxs4iykgy7kmvu5ha": 56,
            "baguqeeragkcygilt343jha5gwdlgjur374gg5sdzbfsnv5mvkyge7vo4exzq": 56,
            "baguqeeragl2bwlqwmreyxpkdptkpsqegxlsvsj2mylfrrgxdg7poshpxsdoa": 56,
            "baguqeeragmsbfnerdkdc3gosx2ywpjueab5o5d36jee7jb7klqkyyt2vh72q": 56,
            "baguqeeragn5mxmidi6gheq65qjtig66543rjymlh3f7asp444xsu4h4xbxqq": 56,
            "baguqeeragsalevdphhtdjrgq5okyi4dagqu633xgqqs2aodguyre3lt3nowa": 56,
            "baguqeeraguebnbm6dorbzvwb6hmlkpt7rd2475xt3cgtespif35kexkkkhjq": 56,
            "baguqeeragz4wlm6hbxxamoiyv4fkw2vce5m37asnpc2il2jv7fzx3ouha4ka": 56,
            "baguqeerah3erbrjnmb46pwjloa44npftamhiuarwmhgr5tuvsukrgwt46z2q": 56,
            "baguqeerah4bxz2r2jytlbw3uqjfd7cs6jtbiv3wrklpu5xodw5qrubvp54pa": 56,
            "baguqeerah7jizvk2ga53ntpv7pyzknoffdbmdnii5b3n4olkh3xedngg7kxa": 56,
            "baguqeerahanqmujfnnhzvfusaxnh4kk5w64e7ggf7jwcsoxx66cy66yjcuoa": 56,
            "baguqeerahbgo4z5nu2kkv2v252x36pkljqnsliallwhkpjp2sdkgpx3jqtpa": 56,
            "baguqeerahcffu3swlrhoi5upv2yya3r6uvo6yezktvrqzlatfs6dwtycnraa": 56,
            "baguqeerahcmritbavd2biaeydtnme5lxfux5hmspoe4kpyea3evlnyizf53a": 56,
            "baguqeerahhytymg7ggm3rx6kffomooeb4z6gcenx6j7j76xeudstxlqy7dga": 56,
            "baguqeerahjj3bdxjmbuuubhhd55tdguejr2jcbpms2sjga7vuditfob5r2ma": 56,
            "baguqeerahjvj6xgbjdq7uzhyhgvmqmajf7tmz2utywslolbbi3kkkghps55a": 56,
            "baguqeerahn3txnst5br52pannmb2u3bbbjklf7e35rffhzka26vo4umumyga": 56,
            "baguqeerahqicw33djuookbkzjaqsdzlrnnjd6lmr2bjwrhyx4edhzfx34pdq": 56,
            "baguqeerahsygjuh6qdewhusqeqzzrbi6fgyvzrhazegmxrhyjnkdfd6cglrq": 56,
            "baguqeerai54ot7n6pruenehpne4sepxv43ksuolrebamwpk4wocnsczpdzia": 56,
            "baguqeeraickqpkx4dqefdo5cvok4s3nv3g7vj564vfg4f2gkbkrhbn2yyhiq": 56,
            "baguqeeraidftkj3a6ruomfy5jdp4sm6mqjvgorq4cucfu3tsiz47alhiapoq": 56,
            "baguqeeraidvgdvf2olukm6kyyxmz445walmshch7psuskyvmwvmqcc33f2yq": 56,
            "baguqeeraiqvb4fw6xcncx3yehtdm6f5wmkpfdbkcsvi6fs4275uwexxtmw2a": 56,
            "baguqeeraitzz7m3ooqjb6u42agxaplz6qtr3dj7zvthlfrb54q6coiiffm5a": 56,
            "baguqeeraiull34rmxbny4hc7jkzlkdwc5m4t6lyc55m7zwjzr5pezi52yn7a": 56,
            "baguqeerajckrqcshgv54bxnflbvredcvmzln5bgcsph4kmia7useshmmflya": 56,
            "baguqeerajkujrhdy4zys5f5r54vuqaeujuhbl63ulws6nb3aylyw4lqfplya": 56,
            "baguqeerajl2a72cnuexlq77zwpocsqatnadvcddsj4l4zxv34tbf5nj63x3a": 56,
            "baguqeerajrg2xkgq25au7t76gn4lyljrfwmkumje5dtqxktis4tuogldl6jq": 56,
            "baguqeerajtfjcrgo42om6j4uekipyiz7gfju3vppzxtnbgre655jvdvau6la": 56,
            "baguqeerajywi7xokvhrhjfdka352hfcpt53gzjewiku56jznl72f3klr3jca": 56,
            "baguqeerakax332va623qvj2vvh4nn5niavlt4gy5wg6myyudbrglz4pgx4va": 56,
            "baguqeerakcvzcv2g7kngqfs2pnob7zg2lecpmdlwhaox2rekzvjr6ghn5xiq": 56,
            "baguqeerakfb5ycpbjw3mfwvbp7v3dcp4unz353inubsi2gjzqoee2wkydykq": 56,
            "baguqeerakgiowyl4yni36fzfafmcsxjdpg4pobu7di555jwcdxjact4b2cqq": 56,
            "baguqeerakidye7a3ekbqmiqrf23ztvwv62ubsnnxkua4dn7qbbtuqxuhyrjq": 56,
            "baguqeerakiymxuwas44p4r4flubcjdsglpjaxl3m7p62imbnr3iy3vat7haa": 56,
            "baguqeerakmd5zmy4gorbjd2hzzonklu76hdytlpap77cukzm4wpw3f22ucjq": 56,
            "baguqeerakozkkpa5m3mjnficfqhxhe6xtd4dnk756ecr4o2w5uvdtaw4nc7q": 56,
            "baguqeerakq34vjtrz6edr2gsla7uvumalh2abmpxca277w6zoujqachksk4q": 56,
            "baguqeerakrlw3ycbrqwlbqm4noyb34jdz2z7taf3frrzxbxeofaycgdmuodq": 56,
            "baguqeeraktayndyaenols5r5zgrgu7ylaegr6t5w6yt5rxe7hmdcxpinx7zq": 56,
            "baguqeerakupdlmzehvtifm3k7ozl3eykuuvkng5ncg6p5za2jr62v4pm7dba": 56,
            "baguqeerakyndq6u57lcxphy4vmfryqgyegkzb42ykuezbqsjrbrgjkd43yaq": 56,
            "baguqeeral2zmoo72mzwom32aaozlighbewoprc33ru2qg4kbaqbwn6amhbsa": 56,
            "baguqeeral4upa5ts2iuz3ev4urpowcsihzf3dewavg5ohdssznzbqbjbip4a": 56,
            "baguqeeralediy5i6d3lvgcdcsz2dx75cxebnnvqj7ytzh6ro7cnlsuubbpaq": 56,
            "baguqeeraleyvy6yjsycqr3kgzo5cdsxuvbrjgvf3zzd3lvv36r7pdk6agwqq": 56,
            "baguqeeralgdhi2iyta6pca5fsgxw2jeyzpqs3jees75ejfalauw3ssg4222q": 56,
            "baguqeeralmyezbkadl2u3tdotldwkn7q4pwftzq3hlphcxaqcswrrsdrwahq": 56,
            "baguqeeralo4y73h3rp2bntinrjaxdnsuevb345a23vcheusyw377zy2ead5a": 56,
            "baguqeeralsv7qiwp5snj6sqzj6ulzfkyigcpkwhfw63gzaileazrkorf65ga": 56,
            "baguqeeralswybuagtgvneqmeszmaay2stfotfq6wtjeahbegx66y6tnjcuxq": 56,
            "baguqeeralwv66agycqsh7sadkls7ly6vg2seamaq7kdlvav7glndcdexksaa": 56,
            "baguqeeram6su2v33ztkohl7ew63drmk2wwgb65z7qe2ubgo35cwypdspjfla": 56,
            "baguqeeram7p73vsbhwcwp26eylcqs7lf4ic4mxecigdnfndhsqxzehkk3l4a": 56,
            "baguqeeram7psdkpbxpygqlwwknlhsgvrh5nb3swn3mmcfajprxzhbb5qkhxq": 56,
            "baguqeerame4zqozownciwcazqidrsy6fwk5x2jkz2nunoehdijlhhiqt4qsa": 56,
            "baguqeeramheo2byxgvordocnroobb7ecczctd5ypeoiqj6vrgwhnipunivpa": 56,
            "baguqeerami7dbdw72aerte74rlqg4o62rsrgenfx37v5u65ma3qczmkzmbfa": 56,
            "baguqeeramiya3gjrykyj4iagz42ufl5o5wu24q5ihh3yomelxczcogg4qlxq": 56,
            "baguqeerammbq6zsqn7l77nnsasdce7fz2od4otbtzewdb3wjgwcva45k657q": 56,
            "baguqeeramrvrzlm3mordjdwcmard7molnhtybj5b6n4rzf6ev733kgyd3ika": 56,
            "baguqeeramsg7mctl5j2vna4i2zcv7o46npkbxmwer3gfnf4h2txwilihsora": 56,
            "baguqeeramtgqts37zdactwsytsv6clqn65lt6vmdtiletogw5xlt4ltbdvga": 56,
            "baguqeeramu74arr5p2agdzyw5z5n275ty3re5alwkuwexzqsy4r73mf4wibq": 56,
            "baguqeeramuhd2ba2pkwsc7gh4nwotdr456sojr6slrxbn34twjosoy6nhfkq": 56,
            "baguqeeramusk2klqsmxbdd2dwysbbthmlptdrtxt6kmphjyminfpygph4rla": 56,
            "baguqeeramx7m4suiaovfs6xjw7u52wkfoodalgh4ie2qo4vlbor25kezmpuq": 56,
            "baguqeeramzwlgftxlq3q6japkxfp5ubc2srgcvuucciqcpzqer5tqm5fbfgq": 56,
            "baguqeeranjhmx6jgq2hlr25l5teo42viny7q7jzrr5tf5uswf4sogpefhcva": 56,
            "baguqeerannva66ywf7dxjwcy6at5mqiz5inxz3w4m5lwqqsnax6lv4l5d5pq": 56,
            "baguqeeranr4jwkrhqdsfyzvtsbtvxz56zlhbe7m5qqitwi6dginsqgs67v5a": 56,
            "baguqeeranrm6ahwjholbyqrns2fqstl3rwath5nvat3jqe5pz66huvkuvhlq": 56,
            "baguqeeranwiobznpo3wndxim7q5z5dj466ncpqexgopvpfbh2oclp66b3vkq": 56,
            "baguqeeranwldnga3s54vzjc6wh35jaxefcly2hk2vuenkvo27qlylr6fsomq": 56,
            "baguqeeranyns6mdv3m4mxm6pa2kqcbtfh53c7hcegkv2sp7jzcjssv37v4pq": 56,
            "baguqeerao2v4ozwfjm4pqob276zho734t3tuiqz5qv7kudtums4gagd67n7q": 56,
            "baguqeerao36exvfepmmkimhddsn4oztti4x7ook6yzp672klk73zxk6xvp2q": 56,
            "baguqeerao4fjpfkhy3zn5gf7qtdgajdno3x4cquyp5vujy3oweufkoidwb7a": 56,
            "baguqeerao6yuxx2f2u6yuldier4xk53trolfdg6abytw4r76jkdggalh362a": 56,
            "baguqeeraob6xozp2hyd6bvxygvnieohmmgzzu3hyrjk2trlcgqmqvf2x5stq": 56,
            "baguqeeraoc3zesdpdqmdht72nnrc2mbzcfhzhlc7fyv55lnqp7fea2fc6dnq": 56,
            "baguqeeraoffkf6gqrfnvm7n6asakrlneva43ek2oeoc3oqwjo32noy6iltrq": 56,
            "baguqeeraondgcwglythzijafnv7s5l3yfrw37dct5wtfs2l3n5v3njyefn3a": 56,
            "baguqeeraotgjtubabnv6vme7uo5mkro3ner3c3sn2a3h6t56jakluytjptua": 56,
            "baguqeerap7vl4tyvwfryag5a2pxbbeyz5irbu63gsjmhjvmpwcouka4jnh7q": 56,
            "baguqeerapdkn2veplm3xj6pvt3agtc5lgjot47gwuumyueikwrq7zbgpj4pa": 56,
            "baguqeerapn6b44v46o2nlzks4glno4p5bzt4gjhf72cb4oedylprqcntprtq": 56,
            "baguqeerappzbdfponcrygah2kt7xesqlgzeihd2vkbgminnwz3nzgifenfeq": 56,
            "baguqeerapue4eeyhnwt4mykewleycc4wpceuewzdjeqszrskdxnk6dk62r2q": 56,
            "baguqeerapvkbjc43nfix35jwljtljisivfafup2rn5cn5dtsuhetppdsydsq": 56,
            "baguqeerapwjx7pqszeh5eg5udchgww242ntvu4k4ys7zacjaq2ynm3ikkbfq": 56,
            "baguqeeraq3o2g4ikn3exsxstg6j2n74atp36cdnc6dswhnjcby74gdvetsaa": 56,
            "baguqeeraq45xlkcmwnqju7lt6vlf4td4yjax4loo5p4ycfecq5nexx4plola": 56,
            "baguqeeraq5m2purpc7wmmvl7npqacpnnzqacmbratoqnm77dnxd7ir4b3fea": 56,
            "baguqeeraq6ot4y6wpo6wx6vio64gvy7hkthyi7fihmz2qxpzmmlgqv2e4aqa": 56,
            "baguqeeraqfxfrqw7qhv6cq2dho5k7apsgw7ggjhneqvpoefynxqwtipanluq": 56,
            "baguqeeraqkdsujktsdjomt7i2nxn7wior7nuz63nayvenyygaisdanks47dq": 56,
            "baguqeeraql2flvgegguwrzs6iww7oo2j2khyctjh4k7zugi3xoollfpl2itq": 56,
            "baguqeeraqq6vhqizrgbeqhk45l7sgqxas5yl2h22vf7vv5rcpik23mzwct2a": 56,
            "baguqeeraqwvo7oeytz37meuxjlumbpp6d5ecp7lhiq66qh2wcza7f2zp5qda": 56,
            "baguqeerar2ctcyms24h4vlbzl4fahpuiom2d2uukmhay4y66e6txyskupvxa": 56,
            "baguqeerar3osmlijt6g7r6bnpyiqbonpxfehwdytydjrowqwfepal4afur3q": 56,
            "baguqeerar5tfglrbp33ksz7alakt25kk742cnlwhyxrlcmarr6sobhxm424q": 56,
            "baguqeerar7zs7qtzdhnkj6qke5i2dyk6sojkvh6vsellrb42wfmsdctejgzq": 56,
            "baguqeerarjzlwqb2fisscxfc6dy67lzoirz332x6tj2dgkfsz7wmea4s6r3q": 56,
            "baguqeerarmthg72zpohyjz6slxe2vcrxcaerd7rnssnxih4p2fe7xdvp2tda": 56,
            "baguqeerarozbkyeb2k6mmovimt2222tg5g4myuibwz2bl4yehabqkitnrrla": 56,
            "baguqeerarrfoztuxqewe2zvltqo5voeuhyzxevjyg6un7x3po4sqnbm7phdq": 56,
            "baguqeeraryqyyrbyww3oobmeub4dudgd7pn35exfpwtjxgxflgq3elnzc3wa": 56,
            "baguqeeras2q5m33egdmhzkdcodng3h52vrijpvl5kv4qmdu63x36wwknogbq": 87,
            "baguqeerasb4nts7l4popqfyaw7bwqmprwqs5zx2qzgrfmfnjdg4nmagjxt2q": 56,
            "baguqeerasbg4uqdor3wn4gpre2q6jyf5bfljbciow67ywapvxfw7twoj26ka": 56,
            "baguqeerasbolptlititybr6keqvj3ltkzmaqxv4ygprzax63kygu6cg5ds3a": 56,
            "baguqeerasmyzheagvpalp6qjcghenk3cg25evakvum4ccv5hcw6rm52lqfza": 56,
            "baguqeerasv7gnaajvnfzw46amwqa3kgzgcn6gj6inn5sbqo6dyvf3ekjbroq": 56,
            "baguqeerat6uzuhodhqpsattiwcrl6pomvlya3t2eoidwthmsjkmpfph6cdta": 56,
            "baguqeerataorxv5pzlpyqugmrzcfoxrfu7kgidamkdp5rvojk3tnlxdwfsia": 56,
            "baguqeeratiq5j2kxvigjtmqxpms2kj7cfikt7jiw6eluf23bocabcqlijq2q": 56,
            "baguqeeratppqdszvcbxf45szr4fxtuue2tz746z5lenxkk3rjho6trwgw3ba": 56,
            "baguqeeratqveppe2km63sb7olhaqkulebob4cj4rtljz7xsnh6uzs3jeczaa": 56,
            "baguqeeratwrkenmwdvrp5z2shfaw3t5dz4z37or2klufdqu2qjxrqhyjh6wa": 56,
            "baguqeerau2risyjdrp7iugimumdjxe6lgswxwlewtosdhlsswspdj5utfj6q": 56,
            "baguqeerau4vwnhfh77qx5hkacs2mav76rvqm25ymvf4owi2svwtknctapvwq": 56,
            "baguqeerau7fvx35653zmmxsb7d4tar2kq4wgfeyr5xgjfia3odaphw6j677a": 56,
            "baguqeeraufcyzyotpyu4wlrq5fep7fp3uhcuejhwx5lyizrmdirnssoqnqtq": 56,
            "baguqeeraui4e373roagipz24onxiiuuhkyn5j6oz67pieetzddlthdbakpsq": 56,
            "baguqeerauiokpibavmfnwwviefn3mcqydyjexr23lm3lvkv2jg2l3rfeziaa": 56,
            "baguqeeraul2sssl5plbfnbj77sgao24r5wslgry2qbnrptqptbhrzeh5ve3q": 56,
            "baguqeerauntgqmpdrlh2avytnxxnsiw4acv4hwokr4vhgzrudh5jf5vleila": 56,
            "baguqeerausdddbjz3atlfhx3k7wpea5bmf74o3wyc6ba7u2woeokcviue43a": 56,
            "baguqeerautapd5a2aswspljjngsrnx4zfbjf4lagtvr2s3i3pg3c6pnuvwrq": 56,
            "baguqeerauz7eh77luxctxxs6kj2gk6zn5dtagkqq7jiwgsgjss2fnmmqj5ha": 56,
            "baguqeerauzzrm6zkmitgk3jwikqhmitz3hpmypvsy7rzb5ues3z66re4uvra": 56,
            "baguqeerav2tlbgfvuvbrk54az67wawdk4rbd7264dqfnbmug46zzzlqexu2q": 56,
            "baguqeeravfipls7eklotgxys4dkkzdbgewabsafac4sj2yfek64d3xxptlwq": 56,
            "baguqeeravjavp7wm4rhno33jxppxhhvbccpirhmedktglip3lciamg42b2vq": 56,
            "baguqeeravkv5ys6pef7vjdup4irxwyyq75ipykc6g47klwyjlhqtrtgptnza": 56,
            "baguqeeravnprkfvo2sqe5mwlzks6pjlkgisgcplhq3xqfyu5cxsfew4nutcq": 56,
            "baguqeeravrwzu2qtawalx3ti7t2ex5wxq3hojck7shf6c4lodumhow6saxhq": 56,
            "baguqeeravsbf4hlyxhbckice7dzmanvxckty63zrnfmq5rh46g3wbuecmxra": 56,
            "baguqeeravszyr3jkubmarhse2zlwklytzj6yvnzh4wlf2cq6mwjko7socvba": 56,
            "baguqeeraw53rqnedx7u4epurrk5xfbbkdx5ktx54vphp2qev6lifkwvpjjwa": 56,
            "baguqeeraweqvvg25fzvj3kytuw4hnvcc5esrmjctjlao7shsjoahmyn5rzca": 56,
            "baguqeerawi3hny3rttv7e4jbvp7gmb4ipoeoga2laziyzllhwexpu3fsqtpq": 56,
            "baguqeerawmieqkeyxqwyskb5mc57eyvn44uc7fpcfa75g7ql27mxtkew7ksa": 56,
            "baguqeerawue6dwd6rl3jywkjly74nmmh6vwnkfrl2m7skvgws4wrocnmkv2a": 56,
            "baguqeerawuqp7oth5joxe5d3nu2fwfigxtqqko4hfsa4wzbkyhd4ihlqq6ra": 56,
            "baguqeeraww6hhhdxt5g6ou36c6b7wex7anxyzfrmu6zamfejjh56nkvul2ma": 56,
            "baguqeerax4li7tbekf5evygnydhzszwiv4t7v2342dlahawmkze32uv44fqa": 56,
            "baguqeeraxclkggcbwjqnb7etuxut5jnud3aodifl5q5mqa2a5kupy2u5mada": 56,
            "baguqeeraxhedavzrzhxm7f3vj4qsaeqbblb6kcwt7f3uyt2muovofv4id2bq": 56,
            "baguqeeraxjwmdouiamm6jskkk7baffpl323abrcbmbrq4s7incm4b5a5kosq": 56,
            "baguqeeraxlbhkbjdzucnxxdd6s3kp3b2sqyanw3awhazhlnpr7dcgqatdyaa": 56,
            "baguqeeraxlxpzoatkfhrajl55i3enhdolpk2zpmxrsdvif7osrgbczxcqlia": 56,
            "baguqeeraxmjwceutozqksh6cccttfywtox3m5dvuthtaob6raofklvh254ga": 56,
            "baguqeeraxnfaxgu6xhc3qkbsiih7vd4pmdolg74e6tbkky3n6lil3yemtrma": 56,
            "baguqeeraxrizg5yklgfa3o5cpni737r5ysav32gjmb24tmdrti535c66bqeq": 56,
            "baguqeeraxvphphj2vbpp3nielkhb3trpnxz74ubdu4ugl3enkkth2mk3cixq": 56,
            "baguqeeraxxsq3hdje5bwa3vw7sgyge3fkyi46tcvswegv2qf4v5xjhecs6va": 56,
            "baguqeeray7xrskdipjef3zg44xdn2jqil7u4r5z4kro5ycclnbqnqecj4qza": 56,
            "baguqeerayfxxezpjrppuyrxfrpjnjxckipf5schralogkjcfhiwytdarjfaq": 56,
            "baguqeeraygg5peuxqbbw5sntveaxyh4lxtv35bdkypmdvojyvbdm54rfvp3q": 56,
            "baguqeerayi3kunp5etliplw5cfxubwonh2usvbs5sl3pdtw6vgacoonpoxta": 56,
            "baguqeerayil5fdkghgtnpmip6sbkame6xoiusmbx3tsfmgri5ar5ib53ghpq": 56,
            "baguqeerayq23k6dsx4bolv3lwmnooalpcj47gl5uyppkdfajbbz2aag2diwa": 56,
            "baguqeerayqswing6nothryudjsut3lzv4zxnkwrbns7h2ei5upxpudzuxq4a": 56,
            "baguqeerays3moqj3ffaj3mzggbz4b6me6fyhvahmc75ntjdwii24rui4r2lq": 56,
            "baguqeerayw7sl547mn5c6q2twkhx5mlvszmyxfmxcucqsxweuf67fha4xqaq": 56,
            "baguqeeraz2dx5a7mlrxbslt7nc6mjpp2q7j3g6spqnd5yq4dq475poa7teyq": 56,
            "baguqeeraz52jgbc4dbrl5gdcshyytq54ksdzitzypzjvxlj6tjglleoixd4a": 56,
            "baguqeeraz6rcajun573bu3c43px3pacrjg34r4f6nvrv2qxro3wiywauepkq": 56,
            "baguqeerazcf2d2afpgyhf5tojlbfykyzwd6ji4nhawvkz3fayec725xqxysq": 56,
            "baguqeerazjr6icvukexhotnzztastzvro7rfjuxcrquhgf6fzacea4iloh3q": 56,
            "baguqeerazpwgiuv6ahraplsx5hqukuwa52mx6ksicx7uyvffqrev6ycnrkqa": 56,
            "baguqeerazpyh6leayl76227rqdjwws5ffypc5pkwm3rkp7pxabln542x6kaq": 56,
            "baguqeerazryors3fhn2wzfkdj3dg476ebfehllwobkcytyblkya346zgxffq": 56,
            "baguqeerazzwi7kdbwziag52coc5rnqzevmvjkrxfuqxri4yaqgzegeojdhya": 56,
        },
    ),
    (
        "dict",
        {
            "annotation_edge_ids": 100,
            "annotation_node_ids": 100,
            "bounds": 212,
            "closure_id": 2,
            "complete": 0,
            "decision_id": 2,
            "edge_ids": 213,
            "node_ids": 214,
            "paths": 215,
            "root_id": 2,
            "schema": 2,
            "truncated": 0,
        },
    ),
    (
        "dict",
        {
            "authoritative": 0,
            "authority": 2,
            "edge_id": 2,
            "kind": 2,
            "mandatory": 0,
            "provenance": 2,
            "provenance_id": 2,
            "record": 57,
            "root_id": 2,
            "schema": 2,
            "source": 2,
            "source_root_id": 2,
            "target": 2,
            "trust": 2,
            "version": 2,
        },
    ),
    ("list", 303, (217,)),
    ("dict", {"executable": 0, "path": 2, "sha256": 2}),
    (
        "dict",
        {
            "authoritative": 0,
            "authority": 2,
            "content_id": 2,
            "kind": 2,
            "node_id": 2,
            "provenance": 2,
            "provenance_id": 2,
            "record": 219,
            "root_id": 2,
            "schema": 2,
            "source_root_id": 2,
            "trust": 2,
            "version": 2,
        },
    ),
    (
        "dict",
        {
            "authoritative": 0,
            "authority": 2,
            "content_id": 2,
            "kind": 2,
            "node_id": 2,
            "provenance": 2,
            "provenance_id": 2,
            "record": 167,
            "root_id": 2,
            "schema": 2,
            "source_root_id": 2,
            "trust": 2,
            "version": 2,
        },
    ),
    ("dict", {"policy": 158, "profile_content_id": 2}),
    (
        "dict",
        {
            "authoritative": 0,
            "authority": 2,
            "content_id": 2,
            "kind": 2,
            "node_id": 2,
            "provenance": 2,
            "provenance_id": 2,
            "record": 222,
            "root_id": 2,
            "schema": 2,
            "source_root_id": 2,
            "trust": 2,
            "version": 2,
        },
    ),
    (
        "dict",
        {
            "authoritative": 0,
            "authority": 2,
            "content_id": 2,
            "kind": 2,
            "node_id": 2,
            "provenance": 2,
            "provenance_id": 2,
            "record": 168,
            "root_id": 2,
            "schema": 2,
            "source_root_id": 2,
            "trust": 2,
            "version": 2,
        },
    ),
    ("dict", {"graph_cid": 2}),
    (
        "dict",
        {
            "authoritative": 0,
            "authority": 2,
            "content_id": 2,
            "kind": 2,
            "node_id": 2,
            "provenance": 2,
            "provenance_id": 2,
            "record": 225,
            "root_id": 2,
            "schema": 2,
            "source_root_id": 2,
            "trust": 2,
            "version": 2,
        },
    ),
    ("list", 304, (220, 221, 223, 224, 226)),
    (
        "dict",
        {
            "edge_count": 1,
            "edges": 218,
            "graph_id": 2,
            "node_count": 1,
            "nodes": 227,
            "root_id": 2,
            "schema": 2,
        },
    ),
    (
        "dict",
        {
            "closure": 216,
            "code_semantic_closure_claimed": 0,
            "proof_authority": 0,
            "scope": 2,
            "semantic_dependency_graph": 228,
        },
    ),
    ("dict", {"assumption_id": 2, "kind": 2, "statement": 2, "subject_ids": 87}),
    ("dict", {"assumption_id": 2, "kind": 2, "statement": 2, "subject_ids": 56}),
    ("list", 9, (230, 231)),
    (
        "dict",
        {
            "max_actors": 1,
            "max_countermodel_steps": 1,
            "max_events": 1,
            "max_evidence_requirements": 1,
            "max_fluents": 1,
            "max_formula_depth": 1,
            "max_formula_records": 1,
            "max_formulas": 1,
            "max_goals": 1,
            "max_norms": 1,
            "max_provider_evidence": 1,
            "max_search_nodes": 1,
            "max_subgoals": 1,
            "max_tasks": 1,
            "max_temporal_constraints": 1,
            "max_trace_steps": 1,
            "schema": 2,
            "timeout_ms": 1,
        },
    ),
    (
        "dict",
        {
            "actors": 1,
            "events": 1,
            "evidence_requirements": 1,
            "fluents": 1,
            "formulas": 1,
            "goals": 1,
            "norms": 1,
            "provider_evidence": 1,
            "subgoals": 1,
            "tasks": 1,
            "temporal_constraints": 1,
        },
    ),
    (
        "dict",
        {
            "configured": 233,
            "domain_sizes": 234,
            "effective_trace_bound": 1,
            "plan_trace_bound": 1,
            "schema": 2,
            "search_nodes_explored": 1,
            "truncated_dimensions": 100,
        },
    ),
    ("list", 15, (2,)),
    ("list", 5, (2,)),
    (
        "dict",
        {
            "assumptions": 232,
            "bounds": 235,
            "checks_performed": 236,
            "consistency_level": 2,
            "countermodel": 58,
            "evidence": 100,
            "findings": 100,
            "formula_ids": 237,
            "outcome": 2,
            "plan_check_only": 0,
            "plan_id": 2,
            "schema": 2,
            "status": 2,
            "validator_version": 1,
        },
    ),
    (
        "dict",
        {
            "administrator_task_cids": 56,
            "code_proof_authority": 0,
            "codebase_inventory_context_cid": 2,
            "codebase_successor_context_cid": 2,
            "completion_authority": 0,
            "current_facts": 100,
            "declared_input_closure": 229,
            "graph_cid": 2,
            "manifest_cid": 2,
            "owner_profile_id": 2,
            "pending_cid": 2,
            "pending_requirements": 176,
            "plan_evidence": 238,
            "plan_id": 2,
            "planning_permitted": 0,
            "production_activation": 0,
            "removed_task_cids": 100,
            "runtime_requirements_preserved": 0,
            "schema": 2,
            "source_delta_cid": 2,
            "source_tree_id": 2,
            "successor_selection_cid": 2,
        },
    ),
    ("dict", {"binding": 137, "payload": 239}),
    ("dict", {"graph": 211, "manifest": 171, "receipt": 240}),
    (
        "dict",
        {
            "administrator_task_cids": 56,
            "admission_cid": 2,
            "authority": 99,
            "codebase_inventory_context_cid": 2,
            "codebase_successor_context_cid": 2,
            "completion_cid": 2,
            "current_facts": 100,
            "graph_cid": 2,
            "head": 23,
            "manifest_cid": 2,
            "native_persistence_verified_here": 0,
            "observed_current": 0,
            "pending_cid": 2,
            "plan_id": 2,
            "previous_head": 23,
            "removed_task_cids": 100,
            "root_cid": 2,
            "runtime_requirements_preserved": 0,
            "schema": 2,
            "source_delta_cid": 2,
            "successor_selection_cid": 2,
        },
    ),
    (
        "dict",
        {
            "authority": 99,
            "coverage": 52,
            "head_cid": 2,
            "membership_cid": 2,
            "model_artifact_cid": 2,
            "pages": 151,
            "root_cid": 2,
            "schema": 2,
        },
    ),
    (
        "dict",
        {
            "ast_cid": 58,
            "entry_cid": 2,
            "opaque_reason": 58,
            "parse_status": 2,
            "path": 2,
            "raw_path_hex": 2,
            "source_cid": 2,
            "source_key": 2,
            "source_size_bytes": 1,
        },
    ),
    (
        "dict",
        {
            "ast_cid": 2,
            "entry_cid": 2,
            "opaque_reason": 58,
            "parse_status": 2,
            "path": 2,
            "raw_path_hex": 2,
            "source_cid": 2,
            "source_key": 2,
            "source_size_bytes": 1,
        },
    ),
    (
        "dict",
        {
            "ast_cid": 58,
            "entry_cid": 2,
            "opaque_reason": 2,
            "parse_status": 2,
            "path": 2,
            "raw_path_hex": 2,
            "source_cid": 2,
            "source_key": 2,
            "source_size_bytes": 1,
        },
    ),
    (
        "dict",
        {
            "ast_cid": 58,
            "entry_cid": 2,
            "opaque_reason": 2,
            "parse_status": 2,
            "path": 2,
            "raw_path_hex": 2,
            "source_cid": 58,
            "source_key": 2,
            "source_size_bytes": 1,
        },
    ),
    ("list", 300, (244, 245, 246, 247)),
    (
        "dict",
        {
            "authority": 99,
            "head": 23,
            "head_cid": 2,
            "implementation": 139,
            "limits": 140,
            "members": 248,
            "membership_cid": 2,
            "model": 145,
            "optimized": 0,
            "schema": 2,
        },
    ),
    (
        "dict",
        {
            "authority": 99,
            "completion_cid": 2,
            "completion_record": 243,
            "coverage": 52,
            "head": 23,
            "head_cid": 2,
            "implementation": 139,
            "limits": 140,
            "members": 248,
            "membership_cid": 2,
            "model": 145,
            "pages": 151,
            "root_cid": 2,
            "root_record": 249,
            "schema": 2,
        },
    ),
    ("dict", {"authority": 99, "evidence": 58, "scan": 250, "schema": 2}),
    (
        "dict",
        {
            "ipfs_datasets_py.duckdb_control.codebase_catalog": 2,
            "ipfs_datasets_py.logic.software_contracts.codebase_inventory_lineage": 2,
            "ipfs_datasets_py.logic.software_contracts.codebase_inventory_projection_replay": 2,
            "ipfs_datasets_py.logic.software_contracts.codebase_inventory_receiving": 2,
            "ipfs_datasets_py.logic.software_contracts.codebase_inventory_resume": 2,
            "ipfs_datasets_py.logic.software_contracts.codebase_inventory_scan": 2,
            "ipfs_datasets_py.logic.software_contracts.codebase_inventory_successor": 2,
            "ipfs_datasets_py.logic.software_contracts.codebase_inventory_successor_model": 2,
            "ipfs_datasets_py.logic.software_contracts.codebase_inventory_targets": 2,
            "ipfs_datasets_py.logic.software_contracts.codebase_ir": 2,
            "ipfs_datasets_py.logic.software_contracts.codebase_ir_targets": 2,
            "ipfs_datasets_py.logic.software_contracts.codebase_resources": 2,
            "ipfs_datasets_py.logic.software_contracts.codebase_source_training": 2,
            "ipfs_datasets_py.logic.software_contracts.duckdb_ast_store": 2,
            "ipfs_datasets_py.logic.software_contracts.duckdb_ingest": 2,
            "ipfs_datasets_py.logic.software_contracts.semantic_index.scanner": 2,
            "ipfs_datasets_py.logic.software_contracts.semantic_index.snapshot": 2,
            "ipfs_datasets_py.optimizers.logic_theorem_optimizer.autoencoder_projection_features": 2,
            "ipfs_datasets_py.optimizers.logic_theorem_optimizer.autoencoder_runtime_registry": 2,
            "ipfs_datasets_py.optimizers.logic_theorem_optimizer.codebase_feature_worker": 2,
            "ipfs_datasets_py.optimizers.logic_theorem_optimizer.codebase_inventory_feature_worker": 2,
            "ipfs_datasets_py.optimizers.logic_theorem_optimizer.codebase_inventory_resume_worker": 2,
            "ipfs_datasets_py.optimizers.logic_theorem_optimizer.modal_autoencoder_cuda": 2,
        },
    ),
    ("dict", {"files": 252, "scope": 2, "sha256": 2}),
    (
        "dict",
        {
            "authority": 99,
            "current_head": 23,
            "current_membership_cid": 2,
            "implementation": 253,
            "inference_performed_here": 0,
            "model": 145,
            "model_head_promoted": 0,
            "numerical_reuse": 0,
            "optimized": 0,
            "previous_head": 23,
            "previous_membership_cid": 2,
            "previous_model": 155,
            "previous_training_record_cid": 2,
            "root_cid": 2,
            "scan_limits": 140,
            "schema": 2,
            "source_delta_cid": 2,
            "training_performed_here": 0,
            "training_record_cid": 2,
        },
    ),
    ("dict", {"artifact_cid": 2, "value": 254}),
    ("list", 27, (2,)),
    ("dict", {"exclusions": 256, "max_entries": 1, "max_file_bytes": 1}),
    (
        "dict",
        {
            "ast_revision_id": 2,
            "generation": 1,
            "manifest_cid": 2,
            "operation_id": 2,
            "previous_head": 23,
            "repository_id": 2,
            "request_cid": 2,
            "schema": 2,
            "snapshot_cid": 2,
        },
    ),
    (
        "dict",
        {
            "ipfs_datasets_py.duckdb_control.codebase_catalog": 2,
            "ipfs_datasets_py.logic.software_contracts.codebase_inventory_lineage": 2,
            "ipfs_datasets_py.logic.software_contracts.codebase_inventory_projection_replay": 2,
            "ipfs_datasets_py.logic.software_contracts.codebase_inventory_receiving": 2,
            "ipfs_datasets_py.logic.software_contracts.codebase_inventory_resume": 2,
            "ipfs_datasets_py.logic.software_contracts.codebase_inventory_scan": 2,
            "ipfs_datasets_py.logic.software_contracts.codebase_inventory_successor": 2,
            "ipfs_datasets_py.logic.software_contracts.codebase_inventory_targets": 2,
            "ipfs_datasets_py.logic.software_contracts.codebase_ir": 2,
            "ipfs_datasets_py.logic.software_contracts.codebase_ir_targets": 2,
            "ipfs_datasets_py.logic.software_contracts.codebase_resources": 2,
            "ipfs_datasets_py.logic.software_contracts.codebase_source_training": 2,
            "ipfs_datasets_py.logic.software_contracts.duckdb_ast_store": 2,
            "ipfs_datasets_py.logic.software_contracts.duckdb_ingest": 2,
            "ipfs_datasets_py.logic.software_contracts.semantic_index.scanner": 2,
            "ipfs_datasets_py.logic.software_contracts.semantic_index.snapshot": 2,
            "ipfs_datasets_py.optimizers.logic_theorem_optimizer.autoencoder_projection_features": 2,
            "ipfs_datasets_py.optimizers.logic_theorem_optimizer.autoencoder_runtime_registry": 2,
            "ipfs_datasets_py.optimizers.logic_theorem_optimizer.codebase_feature_worker": 2,
            "ipfs_datasets_py.optimizers.logic_theorem_optimizer.codebase_inventory_feature_worker": 2,
            "ipfs_datasets_py.optimizers.logic_theorem_optimizer.codebase_inventory_resume_worker": 2,
            "ipfs_datasets_py.optimizers.logic_theorem_optimizer.modal_autoencoder_cuda": 2,
        },
    ),
    ("dict", {"files": 259, "scope": 2, "sha256": 2}),
    (
        "dict",
        {
            "acquisition": 2,
            "disposition": 2,
            "entry_cid": 2,
            "git_blob_oid": 2,
            "head_blob_oid": 2,
            "index_blob_oids": 57,
            "kind": 2,
            "opaque_reason": 58,
            "path": 2,
            "raw_path_hex": 2,
            "schema": 2,
            "size_bytes": 1,
            "source_cid": 2,
        },
    ),
    ("dict", {"entry": 261, "member": 244}),
    (
        "dict",
        {
            "ast_identity_comparison": 2,
            "classification": 2,
            "current": 262,
            "previous": 262,
            "source_bytes_comparison": 2,
            "source_key": 2,
        },
    ),
    ("dict", {"entry": 261, "member": 245}),
    (
        "dict",
        {
            "ast_identity_comparison": 2,
            "classification": 2,
            "current": 264,
            "previous": 58,
            "source_bytes_comparison": 2,
            "source_key": 2,
        },
    ),
    (
        "dict",
        {
            "ast_identity_comparison": 2,
            "classification": 2,
            "current": 58,
            "previous": 264,
            "source_bytes_comparison": 2,
            "source_key": 2,
        },
    ),
    (
        "dict",
        {
            "ast_identity_comparison": 2,
            "classification": 2,
            "current": 264,
            "previous": 264,
            "source_bytes_comparison": 2,
            "source_key": 2,
        },
    ),
    (
        "dict",
        {
            "acquisition": 2,
            "disposition": 2,
            "entry_cid": 2,
            "git_blob_oid": 2,
            "head_blob_oid": 2,
            "index_blob_oids": 57,
            "kind": 2,
            "opaque_reason": 2,
            "path": 2,
            "raw_path_hex": 2,
            "schema": 2,
            "size_bytes": 1,
            "source_cid": 2,
        },
    ),
    ("dict", {"entry": 268, "member": 246}),
    (
        "dict",
        {
            "ast_identity_comparison": 2,
            "classification": 2,
            "current": 269,
            "previous": 269,
            "source_bytes_comparison": 2,
            "source_key": 2,
        },
    ),
    (
        "dict",
        {
            "acquisition": 2,
            "disposition": 2,
            "entry_cid": 2,
            "git_blob_oid": 2,
            "head_blob_oid": 2,
            "index_blob_oids": 57,
            "kind": 2,
            "opaque_reason": 2,
            "path": 2,
            "raw_path_hex": 2,
            "schema": 2,
            "size_bytes": 1,
            "source_cid": 58,
        },
    ),
    ("dict", {"entry": 271, "member": 247}),
    (
        "dict",
        {
            "ast_identity_comparison": 2,
            "classification": 2,
            "current": 272,
            "previous": 272,
            "source_bytes_comparison": 2,
            "source_key": 2,
        },
    ),
    ("list", 302, (263, 265, 266, 267, 270, 273)),
    (
        "dict",
        {
            "max_delta_bytes": 1,
            "max_file_bytes": 1,
            "max_inventory_entries": 1,
            "max_manifest_bytes": 1,
            "max_union_entries": 1,
        },
    ),
    (
        "dict",
        {
            "ast_revision_id": 2,
            "generation": 1,
            "manifest_cid": 2,
            "operation_id": 2,
            "previous_head": 58,
            "repository_id": 2,
            "request_cid": 2,
            "schema": 2,
            "snapshot_cid": 2,
        },
    ),
    (
        "dict",
        {
            "authority": 99,
            "capture_policy": 257,
            "coverage": 22,
            "current_head": 23,
            "current_membership_cid": 2,
            "current_publication_receipt": 258,
            "implementation": 260,
            "ledger": 274,
            "limits": 275,
            "model_advanced": 0,
            "numerical_reuse": 0,
            "optimized": 0,
            "physical_absence_verified": 0,
            "previous_head": 23,
            "previous_membership_cid": 2,
            "previous_publication_receipt": 276,
            "removal_scope": 2,
            "schema": 2,
        },
    ),
    ("dict", {"artifact_cid": 2, "value": 277}),
    (
        "dict",
        {"authority": 99, "inventory": 251, "schema": 2, "selection": 255, "source_delta": 278},
    ),
    ("dict", {"graph": 211, "receipt": 240}),
    (
        "dict",
        {
            "codebase_inventory_context": 251,
            "codebase_successor_context": 279,
            "completion_authority": 0,
            "context_cid": 2,
            "inventory_plan_admission": 280,
            "manifest": 171,
            "manifest_cid": 2,
            "owner_identity": 2,
            "owner_profile_id": 2,
            "publication_authority": 0,
            "repository": 2,
            "schema": 2,
            "scope_expansion_authority": 0,
            "source_bytes": 1,
            "source_path": 2,
            "source_sha256": 2,
            "task_cid": 2,
            "task_id": 2,
        },
    ),
    (
        "dict",
        {
            "artifact": 2,
            "codebase_inventory_context_cid": 2,
            "codebase_successor_context_cid": 2,
            "completion_authority": 0,
            "context_cid": 2,
            "inventory_context_cid": 2,
            "manifest_cid": 2,
            "scope_expansion_authority": 0,
            "sha256": 2,
            "source_bytes": 1,
            "source_delta_cid": 2,
            "source_path": 2,
            "source_sha256": 2,
            "successor_selection_cid": 2,
            "task_cid": 2,
        },
    ),
    ("list", 13, (2,)),
    (
        "dict",
        {"argv": 283, "implementation_command": 2, "public_instruction": 282, "task_revision": 1},
    ),
    (
        "dict",
        {
            "ipfs_accelerate_py.agent_supervisor.entrypoints.admitted_benchmark_runtime": 2,
            "ipfs_accelerate_py.agent_supervisor.runtime.candidate_execution": 2,
            "ipfs_accelerate_py.agent_supervisor.runtime.codebase_inventory_evidence_admission": 2,
            "ipfs_accelerate_py.agent_supervisor.runtime.codebase_inventory_evidence_worker_context": 2,
            "ipfs_accelerate_py.agent_supervisor.runtime.codebase_inventory_execution": 2,
            "ipfs_accelerate_py.agent_supervisor.runtime.codebase_successor_dispatch_admission": 2,
            "ipfs_accelerate_py.agent_supervisor.runtime.codebase_successor_dispatch_context": 2,
            "ipfs_accelerate_py.agent_supervisor.runtime.local_completion_bridge": 2,
            "ipfs_accelerate_py.agent_supervisor.runtime.local_planning_admission": 2,
            "ipfs_accelerate_py.agent_supervisor.runtime.router_public_instruction": 2,
            "ipfs_accelerate_py.agent_supervisor.task_sources.typed_state_owner": 2,
            "ipfs_datasets_py.logic.software_contracts.codebase_inventory_receiving": 2,
            "ipfs_datasets_py.logic.software_contracts.codebase_inventory_successor_receiving": 2,
        },
    ),
    (
        "dict",
        {
            "child_process_slots": 1,
            "cpu_slots": 1,
            "lane": 2,
            "lease_id": 2,
            "memory_mb": 1,
            "owner_pid": 1,
            "parent_lease_id": 58,
        },
    ),
    ("list", 8, (2,)),
    ("list", 1, (287,)),
    ("list", 6, (56,)),
    ("list", 6, (2,)),
    ("list", 1, (290,)),
    ("list", 11, (2,)),
    ("list", 1, (292,)),
    (
        "dict",
        {
            "goals": 288,
            "metadata": 289,
            "plans": 288,
            "store_generation": 291,
            "validation_evidence": 293,
        },
    ),
    (
        "dict",
        {
            "completion_evidence_digest": 2,
            "completion_receipt_cid": 2,
            "control_receipt_id": 2,
            "task_alias": 2,
            "task_cid": 2,
            "task_revision": 1,
        },
    ),
    ("dict", {"baguqeeraqs244v4okkpdcdt2uptlvlpdv7riunksd2jtkihlauif5fn764fq": 295}),
    ("list", 10, (1, 2)),
    ("list", 1, (297,)),
    ("dict", {"baguqeeraqs244v4okkpdcdt2uptlvlpdv7riunksd2jtkihlauif5fn764fq": 298}),
    (
        "dict",
        {
            "execution_mode": 2,
            "task_alias": 2,
            "task_cid": 2,
            "task_contract_cid": 2,
            "task_revision": 1,
        },
    ),
    ("list", 2, (300,)),
    (
        "dict",
        {
            "entries": 301,
            "plan_root_cid": 2,
            "policy_id": 2,
            "repository_tree_id": 2,
            "schema": 2,
            "source_projection_cid": 2,
            "source_revision": 1,
        },
    ),
    (
        "dict",
        {
            "contract_version": 1,
            "credential_generation": 1,
            "database_uuid": 2,
            "extension_fingerprint": 2,
            "fence_epoch": 1,
            "generation": 1,
            "interface": 2,
            "listen_uri": 2,
            "process_birth": 123,
            "process_birth_id": 2,
            "repository_id": 2,
            "revision": 1,
            "schema": 2,
            "schema_fingerprint": 2,
            "schema_revision": 1,
            "secret_handle": 2,
            "server_id": 2,
            "started_at": 2,
            "startup_epoch": 1,
            "status": 2,
            "store_id": 2,
        },
    ),
    ("dict", {"criterion": 2, "evidence_policy": 161, "ordinal": 1}),
    ("list", 1, (304,)),
    (
        "dict",
        {
            "attempt_id": 2,
            "claim_id": 2,
            "evidence_digest": 2,
            "fence_epoch": 1,
            "fencing_token": 1,
            "lease_id": 2,
            "operation": 2,
            "owner_session_id": 2,
        },
    ),
    (
        "dict",
        {
            "dependencies": 100,
            "graph_cid": 2,
            "intent_owner_id": 2,
            "manifest": 171,
            "manifest_cid": 2,
            "pending_cid": 2,
            "pending_requirements": 176,
            "plan_id": 2,
            "planning_receipt_cid": 2,
            "schema": 2,
            "task_cid": 2,
            "task_key": 2,
            "task_spec": 167,
        },
    ),
    ("dict", {"binding": 137, "payload": 307}),
    ("dict", {"completion_receipt": 306, "local_planning_contract": 308, "title": 2}),
    ("dict", {"local_contract_cid": 2, "repository_tree_id": 2, "task_alias": 2, "task_cid": 2}),
    ("dict", {"effect": 163, "ordinal": 1, "path": 2}),
    ("list", 1, (311,)),
    ("dict", {"cwd": 2, "expected_exit_codes": 53, "policy_cid": 2, "validation_key": 2}),
    ("dict", {"argv": 86, "ordinal": 1, "policy": 313}),
    ("list", 1, (314,)),
    (
        "dict",
        {
            "acceptance": 305,
            "body": 309,
            "created_at": 2,
            "dependencies": 100,
            "goal_cid": 2,
            "identity": 310,
            "objective_id": 2,
            "ordinal": 1,
            "outputs": 312,
            "plan_cid": 2,
            "priority": 2,
            "revision": 1,
            "status": 2,
            "task_alias": 2,
            "task_cid": 2,
            "updated_at": 2,
            "validations": 315,
        },
    ),
    ("dict", {"local_planning_contract": 178, "title": 2}),
    (
        "dict",
        {
            "acceptance": 305,
            "body": 317,
            "created_at": 2,
            "dependencies": 87,
            "goal_cid": 2,
            "identity": 310,
            "objective_id": 2,
            "ordinal": 1,
            "outputs": 312,
            "plan_cid": 2,
            "priority": 2,
            "revision": 1,
            "status": 2,
            "task_alias": 2,
            "task_cid": 2,
            "updated_at": 2,
            "validations": 315,
        },
    ),
    ("list", 2, (316, 318)),
    (
        "dict",
        {
            "authority_rows": 294,
            "completed_prerequisites": 296,
            "completion_rows": 299,
            "execution_route_policy": 302,
            "owner_identity": 303,
            "selected_task_cids": 87,
            "tasks": 319,
        },
    ),
    (
        "dict",
        {
            "admission_cid": 2,
            "candidate": 284,
            "completion_authority": 0,
            "current_facts": 100,
            "current_inventory": 242,
            "freshness_scope": 2,
            "future_claim_and_fence": 2,
            "head": 23,
            "implementation": 285,
            "inventory_features_are_advisory": 0,
            "lease": 286,
            "native_population": 320,
            "production_activation": 0,
            "profile": 2,
            "proof_authority": 0,
            "publication_authority": 0,
            "removed_task_cids": 100,
            "resource_scope": 2,
            "schema": 2,
            "task_omission_authority": 0,
            "task_population_preserved": 0,
            "worker_freshness_scope": 2,
        },
    ),
    ("dict", {"binding": 137, "payload": 321}),
    (
        "dict",
        {
            "bootstrap_errors": 100,
            "native_diagnostics": 121,
            "observed_worker_allocations": 125,
            "remaining_processes": 1,
            "residual_task": 180,
            "start": 192,
            "stop": 195,
            "task_observations": 197,
            "worker_launched": 0,
        },
    ),
    ("dict", {"argv": 283, "public_instruction": 282, "task_revision": 1}),
    (
        "dict",
        {
            "boot_id": 2,
            "client_id": 2,
            "grant_id": 2,
            "parent_pid": 1,
            "pid": 1,
            "process_birth_id": 2,
            "schema": 2,
            "start_time_ticks": 1,
            "uid": 1,
        },
    ),
    (
        "dict",
        {
            "execution_mode": 2,
            "plan_root_cid": 2,
            "policy_id": 2,
            "repository_tree_id": 2,
            "schema": 2,
            "source_revision": 1,
            "task_alias": 2,
            "task_cid": 2,
            "task_contract_cid": 2,
            "task_revision": 1,
        },
    ),
    (
        "dict",
        {
            "admitted_from_revision": 1,
            "attempt_execution_phase": 2,
            "attempt_execution_revision": 1,
            "attempt_id": 2,
            "attempt_number": 1,
            "claim_id": 2,
            "claim_phase_schema": 2,
            "claim_process_attestation": 325,
            "claimed_from_revision": 1,
            "execution_route_binding": 326,
            "execution_route_origin_revision": 1,
            "execution_route_policy_id": 2,
            "fence_epoch": 1,
            "fencing_token": 1,
            "idle_lane_work_stealing": 2,
            "lease_id": 2,
            "operation": 2,
            "owner_session_id": 2,
            "strict_task_sharding": 0,
            "task_prefix": 2,
            "task_shard_count": 1,
            "task_shard_index": 1,
        },
    ),
    ("dict", {"evidence_digest": 2, "outcome": 2, "validation_key": 2}),
    ("list", 1, (328,)),
    ("dict", {"passed": 0, "results": 329, "source_tree_id": 2, "task_cid": 2}),
    (
        "dict",
        {
            "allowed_worktree_roots": 87,
            "container_id": 2,
            "image_id": 2,
            "namespaces": 66,
            "owner_private_paths": 86,
            "owner_uid": 1,
            "schema": 2,
            "single_worker": 0,
            "validation_repository_roots": 87,
            "worker_uid": 1,
        },
    ),
]


class Refusal(ValueError):
    """Selected material does not satisfy this closed historical profile."""


def need(condition, label):
    if not condition:
        raise Refusal(label)


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def canonical(value):
    return json.dumps(
        value, sort_keys=True, separators=(",", ":"), ensure_ascii=True, allow_nan=False
    ).encode("ascii")


def same(left, right):
    return canonical(left) == canonical(right)


def closed(value, fields, label):
    need(type(value) is dict and set(value) == set(fields), label + " closed fields")


def integer(value, low=0, high=2**63 - 1):
    return type(value) is int and low <= value <= high


def number(value, low=0):
    return type(value) in (int, float) and math.isfinite(value) and low <= value <= 1e15


def digest(value):
    return type(value) is str and re.fullmatch("[0-9a-f]{64}", value) is not None


def document(raw):
    def pairs(items):
        result = {}
        for key, value in items:
            need(key not in result, "duplicate JSON field")
            result[key] = value
        return result

    def reject(value):
        raise Refusal("non-finite JSON constant: " + value)

    try:
        text = raw.decode("utf-8", errors="strict")
        # Check depth before the JSON parser can allocate recursive containers.
        depth, quoted, escaped = 0, False, False
        for char in text:
            if quoted:
                if escaped:
                    escaped = False
                elif char == "\\":
                    escaped = True
                elif char == '"':
                    quoted = False
            elif char == '"':
                quoted = True
            elif char in "[{":
                depth += 1
                need(depth <= 32, "JSON nesting bound")
            elif char in "]}":
                depth -= 1
        value = json.loads(text, object_pairs_hook=pairs, parse_constant=reject)
        pending, count = [(value, 0)], 0
        while pending:
            item, depth = pending.pop()
            count += 1
            need(count <= 100000 and depth <= 32, "JSON value/depth bound")
            if type(item) is dict:
                pending.extend((x, depth + 1) for x in item.values())
                pending.extend((x, depth + 1) for x in item)
            elif type(item) is list:
                pending.extend((x, depth + 1) for x in item)
            elif type(item) is str:
                need(not any(0xD800 <= ord(x) <= 0xDFFF for x in item), "JSON surrogate")
            elif type(item) is int:
                need(abs(item) <= 2**63 - 1, "JSON integer bound")
            elif type(item) is float:
                need(math.isfinite(item), "JSON finite number")
        return value
    except (UnicodeError, json.JSONDecodeError, RecursionError, OverflowError) as exc:
        raise Refusal("bounded JSON input") from exc


def bounded(path, cap):
    path = Path(path)
    need(path.is_absolute() and path.resolve(strict=True) == path, "canonical selected path")
    before = path.stat(follow_symlinks=False)
    need(stat.S_ISREG(before.st_mode) and before.st_size <= cap, "regular selected body/cap")
    fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
    try:
        start = os.fstat(fd)
        need(stat.S_ISREG(start.st_mode), "selected descriptor regular file")
        need(
            (start.st_dev, start.st_ino) == (before.st_dev, before.st_ino),
            "selected descriptor identity",
        )
        chunks, total = [], 0
        while True:
            chunk = os.read(fd, min(65536, cap + 1 - total))
            if not chunk:
                break
            chunks.append(chunk)
            total += len(chunk)
            need(total <= cap, "selected read cap")
        end = os.fstat(fd)
    finally:
        os.close(fd)

    def signature(s):
        return s.st_dev, s.st_ino, s.st_size, s.st_mtime_ns, s.st_ctime_ns

    need(signature(before) == signature(start) == signature(end), "selected descriptor changed")
    need(
        path.resolve(strict=True) == path
        and signature(path.stat(follow_symlinks=False)) == signature(end),
        "selected path changed",
    )
    raw = b"".join(chunks)
    need(len(raw) == end.st_size, "complete bounded selected body")
    return raw


class Capture:
    def __init__(self):
        self.raw, self.total, self.identities, self.directories = {}, 0, {}, {}

    def take(self, path, cap=MAX_FILE):
        path = Path(path)
        for parent in path.parents:
            info = parent.stat(follow_symlinks=False)
            need(
                parent.resolve(strict=True) == parent and stat.S_ISDIR(info.st_mode),
                "canonical selected ancestor",
            )
            generation = (info.st_dev, info.st_ino)
            need(
                parent not in self.directories or self.directories[parent] == generation,
                "selected ancestor changed",
            )
            self.directories[parent] = generation
        if path in self.raw:
            need(len(self.raw[path]) <= cap, "reused body cap")
            return self.raw[path]
        need(len(self.raw) < MAX_FILES, "selected file population cap")
        raw = bounded(path, min(cap, MAX_TOTAL - self.total))
        need(self.total + len(raw) <= MAX_TOTAL, "selected byte aggregate cap")
        self.raw[path], self.total = raw, self.total + len(raw)
        info = path.stat(follow_symlinks=False)
        self.identities[path] = (
            info.st_dev,
            info.st_ino,
            info.st_size,
            info.st_mtime_ns,
            info.st_ctime_ns,
        )
        return raw

    def stable(self):
        for folder, expected in self.directories.items():
            info = folder.stat(follow_symlinks=False)
            need(
                folder.resolve(strict=True) == folder
                and stat.S_ISDIR(info.st_mode)
                and (info.st_dev, info.st_ino) == expected,
                "late selected directory identity changed",
            )
        for path, raw in self.raw.items():
            info = path.stat(follow_symlinks=False)
            need(
                self.identities[path]
                == (info.st_dev, info.st_ino, info.st_size, info.st_mtime_ns, info.st_ctime_ns),
                "late selected physical identity changed",
            )
            need(bounded(path, len(raw)) == raw, "late selected raw body changed")


def population(output, expected):
    need(
        output.is_absolute()
        and output.resolve(strict=True) == output
        and stat.S_ISDIR(output.stat(follow_symlinks=False).st_mode),
        "canonical output directory",
    )
    identity = output.stat(follow_symlinks=False)
    files, dirs = set(), set()
    for folder in (output, output / "retained"):
        need(
            folder.resolve(strict=True) == folder
            and stat.S_ISDIR(folder.stat(follow_symlinks=False).st_mode),
            "canonical retained directory",
        )
        with os.scandir(folder) as rows:
            for row in rows:
                info = row.stat(follow_symlinks=False)
                relative = Path(row.path).relative_to(output).as_posix()
                if stat.S_ISREG(info.st_mode):
                    need(relative in expected, "unexpected output body")
                    files.add(relative)
                else:
                    need(
                        stat.S_ISDIR(info.st_mode) and relative == "retained",
                        "unexpected output directory or alias",
                    )
                    dirs.add(relative)
    end = output.stat(follow_symlinks=False)
    need(
        files == set(expected)
        and dirs == {"retained"}
        and (identity.st_dev, identity.st_ino) == (end.st_dev, end.st_ino),
        "exact final output population",
    )


def final_fence(capture, output, expected):
    capture.stable()
    population(output, expected)
    capture.stable()
    population(output, expected)


def report_bytes(value):
    chunks, total = [], 0
    for text in json.JSONEncoder(
        sort_keys=True, indent=2, ensure_ascii=True, allow_nan=False
    ).iterencode(value):
        raw = text.encode("ascii")
        total += len(raw)
        need(total + 1 <= MAX_REPORT, "report serialization cap")
        chunks.append(raw)
    return b"".join(chunks) + b"\n"


def profile_shape(value, node, label):
    """Enforce this finite profile's closed nested fields, lengths and scalar types."""
    spec = SHAPE_NODES[node]
    kind = spec[0]
    if kind == "dict":
        closed(value, spec[1], label)
        for key, child in spec[1].items():
            profile_shape(value[key], child, label + "." + key)
    elif kind == "list":
        need(type(value) is list and len(value) == spec[1], label + " closed list length")
        for item in value:
            for child in spec[2]:
                try:
                    profile_shape(item, child, label + "[]")
                    break
                except Refusal:
                    pass
            else:
                raise Refusal(label + " closed list element type")
    else:
        need(type(value).__name__ == kind, label + " exact scalar type")
        if kind == "float":
            need(math.isfinite(value), label + " finite scalar")
        elif kind == "int":
            need(abs(value) <= 2**63 - 1, label + " bounded integer")


def byte_cid(value):
    """CIDv1 DAG-JSON/SHA256 label of an already supplied complete record."""
    raw = json.dumps(
        value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False
    ).encode("utf-8")
    return "b" + base64.b32encode(
        bytes.fromhex("01a9021220") + hashlib.sha256(raw).digest()
    ).decode("ascii").lower().rstrip("=")


def signature_declaration(envelope, owner, profile, label):
    closed(envelope, ("binding", "payload"), label)
    binding = envelope["binding"]
    closed(binding, ("identity", "profile_id", "signature"), label + " binding")
    need(
        binding["identity"] == owner and binding["profile_id"] == profile,
        label + " owner/profile declaration",
    )
    try:
        signature = base64.b64decode(binding["signature"], validate=True)
    except (binascii.Error, ValueError, TypeError) as exc:
        raise Refusal(label + " signature encoding") from exc
    need(
        len(signature) == 64
        and base64.b64encode(signature).decode("ascii") == binding["signature"],
        label + " canonical signature declaration",
    )
    return dict(binding)


def authority(value, label):
    closed(value, AUTHORITY_FIELDS, label)
    need(all(value[key] is False for key in AUTHORITY_FIELDS), label + " no authority promotion")


def worker_log(raw):
    try:
        lines = raw.decode("utf-8", errors="strict").splitlines()
    except UnicodeError as exc:
        raise Refusal("bounded UTF8 worker log") from exc
    need(len(lines) <= 128 and len(lines) >= 10, "bounded worker log line population")
    records = []
    for line in lines:
        if line.startswith("{"):
            value = document(line.encode("utf-8"))
            need(type(value) is dict, "worker log object")
            if value.get("schema") in (
                "successor-authored-worker-boundary@1",
                "source-successor-authored-native-worker@1",
            ):
                records.append((lines.index(line) + 1, value))
    need([n for n, _ in records] == [9, 10], "exact worker receipt line positions/population")
    return records[0][1], records[1][1]


def reconcile(docs, pins, raw_bodies):
    for role, node in METADATA_SHAPES.items():
        profile_shape(docs[role], node, role)
    old, review, result = (
        docs[key]
        for key in (
            "historical_source_successor_review",
            "successor_expansion_review",
            "native_result",
        )
    )
    need(
        old["schema"] == "repository-proof-index-source-successor-review@1"
        and old["qualified"] is True
        and old["signed_successor_worker_qualified"] is False,
        "historical unsigned successor scope",
    )
    need(
        review["schema"] == "codebase-successor-expansion-closed-review@1"
        and review["signed_successor_dispatch_qualified"] is True,
        "later completed signed milestone",
    )
    for body in (old, review):
        need(
            body["proof_authority"] is False and body["production_default_activated"] is False,
            "historical milestone no production authority",
        )
    declared = review["signed_worker"]
    need(
        declared["native_result"]["sha256"] == pins["native_result"]
        and declared["native_result"]["bytes"] == len(raw_bodies["native_result"]),
        "review native result raw binding",
    )
    need(
        result["schema"] == "codebase-signed-successor-native-qualification@1"
        and result["scope"]
        == "fresh_signed_complete_300_member_successor_cpu8d_authored_format_worker",
        "completed selected signed scope",
    )
    for key in (
        "qualified",
        "native_worker_qualified",
        "worker_launched",
        "full_administrator_population_completed",
        "native_source_generation_advanced",
        "original_source_artifacts_preserved",
        "final_resource_cleanup_verified",
        "local_pool_bounded_by_host_envelope",
    ):
        need(result[key] is True, "recorded native completion: " + key)
    for key in (
        "proof_authority",
        "production_default_activated",
        "source_execution_attested",
        "scan_execution_attested",
        "complete_scan_reexecuted_here",
        "cuda_qualified",
        "384d_qualified",
        "shares_host_pid_state",
    ):
        need(result[key] is False, "native record limited scope: " + key)
    for key in (
        "new_fitting_epochs",
        "new_scan_pages",
        "new_reference_pages",
        "post_setup_fit_attempt_count",
        "inference_attempt_count",
        "provider_calls",
        "remaining_processes",
    ):
        need(integer(result[key], 0, 0), "recorded exact zero: " + key)
    for key, count in (
        ("inherited_setup_epochs", 2),
        ("inherited_scan_pages", 10),
        ("inherited_reference_pages", 1),
    ):
        need(
            integer(result[key], count, count) and declared[key] == count,
            "inherited separate setup: " + key,
        )
    need(
        same(result["numerical_before"], result["numerical_after"]),
        "recorded checkpoint/Adam preservation",
    )
    need(result["bootstrap_errors"] == [], "accepted native bootstrap population")
    need(
        result["native_task_statuses"] == {key: "completed" for key in TASK_IDS}
        and same(result["native_task_statuses"], declared["native_task_statuses"]),
        "two original recorded task completions",
    )
    for row in review["failed_worker_attempts"]:
        closed(row, ("bytes", "path", "sha256"), "unfollowed failure declaration")
        need(
            integer(row["bytes"], 1) and digest(row["sha256"]), "bounded failed attempt declaration"
        )
    need(
        len(review["failed_worker_attempts"]) == 7
        and len({row["path"] for row in review["failed_worker_attempts"]}) == 7,
        "seven historical failure descriptors only",
    )

    admission, manifest = docs["native_admission"], docs["signed_manifest"]
    public, decoded, context = (
        docs[key]
        for key in (
            "raw_public_worker_artifact",
            "decoded_public_worker_artifact",
            "public_worker_context",
        )
    )
    current = docs["current_admission_verification"]
    need(same(public, decoded), "raw and decoded public artifact complete equality")
    need(
        same(manifest, admission["manifest"]) and same(manifest, public["manifest"]),
        "complete signed manifest projections",
    )
    need(
        set(public["inventory_plan_admission"]) == {"graph", "receipt"},
        "public plan is graph/receipt only",
    )
    need(
        same(
            public["inventory_plan_admission"],
            {"graph": admission["graph"], "receipt": admission["receipt"]},
        ),
        "native/public admission projections",
    )
    need(
        public["schema"] == "supervisor-public-instruction@4"
        and current["schema"] == "supervisor-current-successor-admission-verification@1",
        "closed current public schemas",
    )
    owner, profile = public["owner_identity"], public["owner_profile_id"]
    need(
        type(owner) is str
        and owner.startswith("did:key:")
        and type(profile) is str
        and re.fullmatch("[0-9a-f]{32}", profile),
        "typed owner/profile labels",
    )
    signatures = [
        signature_declaration(manifest, owner, profile, "manifest"),
        signature_declaration(admission["receipt"], owner, profile, "planning receipt"),
    ]
    need(
        manifest["payload"]["schema"] == "supervisor-local-benchmark-manifest@6", "manifest schema"
    )
    manifest_cid = byte_cid(manifest)
    need(
        manifest_cid
        == public["manifest_cid"]
        == context["manifest_cid"]
        == current["manifest_cid"],
        "whole signed manifest byte CID",
    )
    need(
        digest(manifest["payload"]["profile_content_id"].removeprefix("sha256:"))
        and manifest["payload"]["profile_content_id"].startswith("sha256:"),
        "profile identity is native SHA256 label",
    )
    for key in ("completion_authority", "publication_authority", "scope_expansion_authority"):
        need(public[key] is False, "public instruction no authority: " + key)
    need(
        context["completion_authority"] is context["scope_expansion_authority"] is False,
        "worker context no authority",
    )
    need(
        context["sha256"] == pins["raw_public_worker_artifact"]
        and context["artifact"].endswith("/" + pins["raw_public_worker_artifact"] + ".json"),
        "raw public artifact original filename/hash",
    )
    for key in ("task_cid", "context_cid", "source_path", "source_sha256", "source_bytes"):
        need(same(public[key], context[key]), "public context join: " + key)
    need(
        public["source_path"] == "README.md"
        and integer(public["source_bytes"], 131, 131)
        and digest(public["source_sha256"]),
        "verbatim instruction source declaration",
    )
    inventory, successor = (
        public["codebase_inventory_context"],
        public["codebase_successor_context"],
    )
    authority(inventory["authority"], "inventory authority")
    authority(successor["authority"], "successor authority")
    authority(current["authority"], "current admission authority")
    need(
        current["current_facts"] == current["removed_task_cids"] == [],
        "current admission no facts or removed tasks",
    )
    need(
        current["observed_current"] is current["runtime_requirements_preserved"] is True
        and current["native_persistence_verified_here"] is False,
        "recorded current receiving scope",
    )
    receipt = admission["receipt"]["payload"]
    need(
        receipt["schema"] == "supervisor-local-planning-receipt@4"
        and receipt["planning_permitted"] is receipt["runtime_requirements_preserved"] is True,
        "planning receipt scope",
    )
    for key in ("code_proof_authority", "completion_authority", "production_activation"):
        need(receipt[key] is False, "planning no authority: " + key)
    need(
        receipt["current_facts"] == receipt["removed_task_cids"] == [],
        "planning no facts or removed tasks",
    )
    graph_tasks, task_specs = admission["graph"]["tasks"], manifest["payload"]["tasks"]
    need(
        len(graph_tasks) == len(task_specs) == 2 and len(admission["graph"]["goals"]) == 1,
        "complete original task/goal population",
    )
    task_cids = [task["content_id"] for task in graph_tasks]
    need(
        len(set(task_cids)) == 2
        and task_cids == receipt["administrator_task_cids"] == current["administrator_task_cids"],
        "ordered administrator task identity",
    )
    need(
        public["task_cid"] == task_cids[1] and public["task_id"] == TASK_IDS[1],
        "selected FORMAT task",
    )
    for index, (task, spec) in enumerate(zip(graph_tasks, task_specs, strict=True)):
        need(task["task_key"] == spec["task_key"] == TASK_IDS[index], "original task alias")
        need(
            task["dependency_task_cids"] == ([] if index == 0 else [task_cids[0]])
            and spec["dependencies"] == ([] if index == 0 else [TASK_IDS[0]]),
            "TYPE prerequisite retained",
        )
        need(
            set(task["scope_paths"]) == set(spec["scope_paths"]) == SCOPE_PATHS,
            "complete original scope paths",
        )
        need(task["predicted_files"] == ["calc.py"], "declared task predicted path")
        need(
            same(
                [
                    {
                        k: value
                        for k, value in row.items()
                        if k not in ("content_id", "contract_version", "schema")
                    }
                    for row in task["outputs"]
                ],
                spec["outputs"],
            ),
            "complete declared outputs",
        )
        need(
            len(spec["outputs"]) == 1
            and spec["outputs"][0]
            == {"effect": "modify", "media_type": "text/x-python", "path": "calc.py"},
            "finite output contract",
        )
        need(
            len(task["validations"]) == len(spec["validations"]) == 1,
            "complete task validation population",
        )
        # Prompt records add immutable field labels to their original validation.
        validation = spec["validations"][0]
        need(
            validation["argv"] == ["python3", "-B", CHECK_PATHS[index]]
            and validation["cwd"] == "."
            and validation["expected_exit_codes"] == [0]
            and validation["validation_key"] == CHECK_IDS[index],
            "original public validation",
        )
        need(
            len(spec["acceptance"]) == 1
            and spec["acceptance"][0]["validation_keys"] == [CHECK_IDS[index]],
            "acceptance requirements preserved",
        )
    pending = receipt["pending_requirements"]
    need(
        len(pending) == 4
        and [row["kind"] for row in pending] == ["test", "test", "review", "review"],
        "complete four pending requirements",
    )
    for index, requirement in enumerate(pending):
        need(
            requirement["required"] is True
            and requirement["phase"] == "post_execution"
            and requirement["minimum_code_assurance"] == "candidate",
            "unchanged mandatory evidence phase/ceiling",
        )
        need(
            requirement["fallback_check_ids"][0] == CHECK_IDS[index % 2],
            "original fallback evidence",
        )
        if index < 2:
            need(requirement["subject_ids"] == [task_cids[index]], "test requirement original task")

    scope, after = docs["execution_scope_before"], docs["execution_scope_after_stop"]
    need(
        raw_bodies["execution_scope_before"] == raw_bodies["execution_scope_after_stop"]
        and same(scope, after),
        "complete signed scope bytes before/after STOP",
    )
    signatures.append(signature_declaration(scope, owner, profile, "execution scope"))
    payload = scope["payload"]
    need(
        payload["schema"] == "supervisor-codebase-inventory-execution-scope@1",
        "execution scope schema",
    )
    for key in (
        "completion_authority",
        "proof_authority",
        "publication_authority",
        "production_activation",
        "task_omission_authority",
    ):
        need(payload[key] is False, "execution scope no authority: " + key)
    need(
        payload["task_population_preserved"] is payload["inventory_features_are_advisory"] is True
        and payload["current_facts"] == payload["removed_task_cids"] == [],
        "complete advisory scope",
    )
    need(
        payload["admission_cid"] == current["admission_cid"]
        and same(payload["head"], current["head"])
        and same(payload["head"], result["current_head"]),
        "prelaunch current head/admission",
    )
    population_record = payload["native_population"]
    native_tasks = population_record["tasks"]
    need(
        len(native_tasks) == 2
        and [row["task_cid"] for row in native_tasks] == task_cids
        and population_record["selected_task_cids"] == [task_cids[1]],
        "complete prelaunch native task population",
    )
    need(
        [row["task_alias"] for row in native_tasks] == list(TASK_IDS)
        and [row["status"] for row in native_tasks] == ["completed", "ready"]
        and [row["revision"] for row in native_tasks] == [4, 1],
        "prelaunch prerequisite vs residual statuses",
    )
    for index, task in enumerate(native_tasks):
        need(
            task["dependencies"] == ([] if index == 0 else [task_cids[0]]),
            "native prerequisite identity",
        )
        contract = task["body"]["local_planning_contract"]
        signatures.append(signature_declaration(contract, owner, profile, "task contract"))
        need(
            same(contract["payload"]["manifest"], manifest)
            and same(contract["payload"]["task_spec"], task_specs[index]),
            "complete original native task contract",
        )
        need(
            same(contract["payload"]["pending_requirements"], pending)
            and contract["payload"]["task_cid"] == task_cids[index],
            "native pending requirements and task join",
        )
        need(
            task["validations"][0]["argv"] == task_specs[index]["validations"][0]["argv"]
            and task["outputs"][0]["path"] == "calc.py",
            "native public validation/output",
        )
    prerequisite, validation = docs["prerequisite_claim"], docs["prerequisite_validation"]
    binding = prerequisite["execution_route_binding"]
    need(
        prerequisite["operation"] == "database_attempt_admitted"
        and prerequisite["claim_phase_schema"]
        == "ipfs_accelerate_py/agent-supervisor/typed-database-attempt-admission@1"
        and prerequisite["strict_task_sharding"] is True,
        "recorded typed prerequisite admission",
    )
    need(
        binding["task_alias"] == TASK_IDS[0]
        and binding["task_cid"] == validation["task_cid"] == task_cids[0],
        "prerequisite claim/validation task identity",
    )
    need(
        validation["passed"] is True
        and len(validation["results"]) == 1
        and validation["results"][0]["validation_key"] == CHECK_IDS[0]
        and validation["results"][0]["outcome"] == "passed",
        "recorded prerequisite public validation",
    )
    completed = population_record["completed_prerequisites"]
    need(
        set(completed) == {task_cids[0]}
        and completed[task_cids[0]]["task_revision"] == 4
        and completed[task_cids[0]]["task_alias"] == TASK_IDS[0],
        "single completed TYPE prerequisite",
    )

    candidate = docs["worker_candidate"]
    need(
        same(candidate, payload["candidate"])
        or (
            same(candidate["public_instruction"], payload["candidate"]["public_instruction"])
            and same(candidate["argv"], payload["candidate"]["argv"])
            and candidate["task_revision"] == payload["candidate"]["task_revision"]
        ),
        "candidate scope projection",
    )
    need(
        same(candidate["public_instruction"], context)
        and integer(candidate["task_revision"], 1, 1),
        "candidate public context/task revision",
    )
    need(
        candidate["argv"]
        == [
            "/opt/ipfs-supervisor/bin/owner-worker",
            "--model",
            "successor-authored-format-fixture",
            "--purpose",
            "coding",
            "--public-instruction-artifact",
            context["artifact"],
            "--public-instruction-sha256",
            context["sha256"],
            "--public-instruction-task-cid",
            task_cids[1],
            "--timeout",
            "90",
        ],
        "exact declared candidate command",
    )
    authored = docs["authored_worker_receipt"]
    need(same(authored, result["authored_worker_receipt"]), "complete authored receipt projection")
    need(
        authored["schema"] == "source-successor-authored-worker-receipt-verification@1"
        and authored["verified"] is authored["public_signatures_verified"] is True,
        "historical receipt verification declarations",
    )
    for key in (
        "completion_authority",
        "proof_authority",
        "process_origin_attested",
        "native_registry_opened",
        "native_inventory_freshness_verified_here",
        "private_evidence_epoch_verified_here",
        "native_formal_compilation_reperformed_here",
        "numerical_execution_reperformed_here",
    ):
        need(authored[key] is False, "authored receiving scope: " + key)
    need(
        authored["original_artifact"]["sha256"] == pins["raw_public_worker_artifact"]
        and authored["original_artifact"]["bytes"] == len(raw_bodies["raw_public_worker_artifact"])
        and authored["original_artifact"]["path"] == context["artifact"],
        "worker original artifact wire binding",
    )
    need(
        authored["retained_root_boundary"]["sha256"] == pins["container_boundary"]
        and authored["retained_root_boundary"]["bytes"] == len(raw_bodies["container_boundary"]),
        "recorded boundary artifact binding",
    )
    boundary_record, worker = docs["worker_boundary_receipt"], docs["worker_output_receipt"]
    for key, record, line in (
        ("actual_boundary_stdout_observation", boundary_record, 9),
        ("actual_stdout_observation", worker, 10),
    ):
        observation = authored[key]
        need(
            integer(observation["line"], line, line)
            and same(record, observation["receipt"])
            and observation["log"]["sha256"] == pins["worker_stdout_log"]
            and observation["log"]["bytes"] == len(raw_bodies["worker_stdout_log"]),
            "actual selected stdout receipt join",
        )
    need(
        worker["uid"] == boundary_record["uid"] == boundary_record["euid"] == 1001
        and integer(worker["pid"], 1)
        and worker["pid"] == boundary_record["pid"],
        "recorded UID/PID receipt join",
    )
    for record in (worker, boundary_record):
        need(
            integer(record["provider_calls"], 0, 0) and integer(record["training_steps"], 0, 0),
            "worker exact zero provider/training declarations",
        )
    need(
        worker["status"] == "materialized"
        and worker["path"] == "calc.py"
        and worker["task_cid"] == task_cids[1]
        and worker["completion_authority"]
        is worker["proof_authority"]
        is worker["native_completion_recorded_here"]
        is False,
        "worker edits without self-completion authority",
    )
    need(
        digest(worker["before_sha256"])
        and digest(worker["after_sha256"])
        and worker["before_sha256"] != worker["after_sha256"],
        "recorded changed output byte digests",
    )
    need(
        boundary_record["boundary_sha256"] == pins["container_boundary"]
        and boundary_record["boundary"]["manifest_sha256"] == pins["container_boundary"],
        "boundary raw declaration binding",
    )
    boundary = docs["container_boundary"]
    need(
        boundary["schema"] == "supervisor-container-worker-boundary@1"
        and boundary["worker_uid"] == 1001
        and boundary["owner_uid"] == 1000
        and boundary["single_worker"] is True,
        "recorded container boundary profile",
    )
    for key in ("container_id", "image_id", "namespaces", "worker_uid", "owner_uid"):
        need(
            same(boundary_record["boundary"][key], boundary[key]),
            "worker/root boundary join: " + key,
        )
    need(
        set(boundary_record["private_access"]) == set(boundary["owner_private_paths"]),
        "exact recorded private path population",
    )
    for access in boundary_record["private_access"].values():
        need(
            all(access[key] is False for key in ("read", "write", "execute")),
            "recorded private denial only",
        )
    instruction = worker["public_instruction"]
    need(
        instruction["schema"] == "supervisor-public-instruction-inclusion@4"
        and instruction["manifest_signature_verified"]
        is instruction["verbatim_utf8"]
        is instruction["source_freshness_verified"]
        is True,
        "retained public instruction declarations",
    )
    for key in (
        "completion_authority",
        "scope_expansion_authority",
        "semantic_minification_applied",
        "historical_replay",
    ):
        need(instruction[key] is False, "instruction no promotion: " + key)
    need(integer(instruction["extra_provider_calls"], 0, 0), "instruction extra provider zero")
    for key in (
        "artifact",
        "task_cid",
        "context_cid",
        "manifest_cid",
        "source_path",
        "source_sha256",
        "source_bytes",
    ):
        expected = context[key] if key != "artifact" else context["artifact"]
        need(same(instruction[key], expected), "instruction exact context: " + key)
    need(
        instruction["artifact_sha256"] == pins["raw_public_worker_artifact"],
        "instruction raw artifact digest",
    )
    authority(instruction["codebase_inventory"]["authority"], "worker inventory authority")
    authority(instruction["codebase_successor"]["authority"], "worker successor authority")
    need(
        instruction["codebase_inventory"]["planning_receipt_cid"] == byte_cid(admission["receipt"]),
        "whole signed planning receipt byte CID",
    )
    for key in ("source_delta_cid", "selection_cid"):
        need(
            authored[key] == result[key] == instruction["codebase_successor"][key],
            "worker successor binding: " + key,
        )

    life = docs["native_lifecycle"]
    need(same(life, {key: result[key] for key in life}), "complete lifecycle projection")
    need(
        len(life["task_observations"]) == 2
        and life["task_observations"][-1]["status"] == "completed",
        "recorded residual task observations",
    )
    for operation in ("start", "stop"):
        row = life[operation]
        need(
            row["schema"] == "ipfs_accelerate_py/agent-supervisor/operation-result@1"
            and row["operation"] == operation
            and row["status"] == "succeeded"
            and row["error"] is None,
            "recorded START/STOP result",
        )
        need(
            row["caller"] == owner
            and row["authority"] == "mutation"
            and len(row["effects"]) == 1
            and row["effects"][0]["applied"] is True,
            "recorded operation effects",
        )
    need(
        life["stop"]["data"]["isolated_worker_cleanup"]["returncode"] == 0
        and life["stop"]["data"]["isolated_worker_cleanup"]["completion_authority"] is False,
        "descriptive native STOP cleanup",
    )
    residual = life["residual_task"]
    need(
        residual["task_cid"] == task_cids[1]
        and residual["status"] == "completed"
        and integer(residual["revision"], 4, 4),
        "FORMAT final native task identity/revision",
    )
    final_contract = residual["body"]["local_planning_contract"]
    need(
        same(final_contract, native_tasks[1]["body"]["local_planning_contract"]),
        "unchanged original final task contract",
    )
    completion = residual["body"]["completion_receipt"]
    validation = completion["validation"]
    need(
        validation["outcome"] == "passed"
        and validation["task_cid"] == task_cids[1]
        and validation["validator"] == "DatabasePortalExecutionBridge@1"
        and validation["argv"] == ["portal-supervisor-gates"],
        "recorded ordinary proposal/validation gate",
    )
    transition = validation["accepted_source_transition"]
    need(
        transition["schema"] == "ipfs_accelerate_py/agent-supervisor/accepted-source-transition@1"
        and transition["worker_self_approval"] is transition["task_completion_authority"] is False,
        "accepted source transition no worker authority",
    )
    need(
        transition["database_task_cid"]
        == validation["task_cid"]
        == transition["database_attempt_binding"]["task_cid"]
        == task_cids[1]
        and transition["task_alias"] == TASK_IDS[1],
        "portal accepted task identity",
    )
    for key in ("attempt_id", "claim_id", "fencing_token"):
        need(
            same(completion[key], transition[key])
            and same(completion[key], transition["database_attempt_binding"][key]),
            "completion/portal binding: " + key,
        )
    need(
        completion["attempt_id"] == validation["attempt_id"]
        and completion["lease_id"] == transition["database_attempt_binding"]["lease_id"],
        "completion lease and attempt",
    )
    need(
        same(completion["coordination_preparation"]["body"]["validation"], validation),
        "coordination/validation exact projection",
    )
    invariant, publication = transition["declared_output_invariant"], result["publication"]
    need(
        invariant["passed"] is True
        and invariant["missing_outputs"]
        == invariant["unsafe_outputs"]
        == invariant["untracked_outputs"]
        == []
        and invariant["task_ids"] == [TASK_IDS[1]],
        "recorded declared output invariant",
    )
    need(
        len(invariant["checks"]) == 1
        and invariant["checks"][0]["path"] == "calc.py"
        and invariant["checks"][0]["tracked"] is invariant["checks"][0]["exists"] is True,
        "recorded tracked output",
    )
    need(
        publication["changed_paths"] == ["calc.py"]
        and publication["public_checks_passed"] is True
        and same(publication, declared["publication"]),
        "selected publication output/cross-review",
    )
    need(
        publication["parents"]
        == [publication["baseline_commit"], transition["implementation_commit"]]
        and publication["baseline_commit"] == transition["baseline_ref"]
        and publication["published_commit"]
        == transition["merge_commit"]
        == invariant["repository_ref"],
        "two-parent merge/transition binding",
    )
    proof = transition["integration_commit_proof"]
    need(
        proof["passed"] is True
        and proof["reasons"] == []
        and proof["integration_commit"] == publication["published_commit"]
        and proof["implementation_commit"] == publication["parents"][1],
        "recorded integration proof metadata",
    )
    checks = docs["published_public_checks"]
    need(
        same(checks, publication["public_checks"]) and len(checks) == 2,
        "two complete published public checks",
    )
    for row, path in zip(checks, CHECK_PATHS, strict=True):
        need(
            row["schema"] == "source-successor-published-public-check@1"
            and row["path"] == path
            and integer(row["returncode"], 0, 0),
            "recorded public check identity/outcome",
        )
        need(
            row["argv"] == ["/opt/ipfs-supervisor/venv/bin/python", "-B", path]
            and row["cwd"] == "/results/native/repository"
            and integer(row["timeout_seconds"], 10, 10),
            "recorded public check command/bound",
        )
        need(
            same(row["source_before"], row["source_after"])
            and digest(row["source_before"]["sha256"]),
            "recorded public check source preservation",
        )
        for stream in ("stdout", "stderr"):
            raw = row[stream].encode("utf-8")
            need(
                integer(row[stream + "_bytes"], len(raw), len(raw))
                and row[stream + "_sha256"] == sha(raw),
                "public check output bytes/digest",
            )
    published = docs["published_source_receipt"]
    need(
        published["schema"] == "codebase-publication-receipt@1"
        and integer(published["generation"], 3, 3)
        and integer(result["current_head"]["generation"], 2, 2)
        and same(published["previous_head"], result["current_head"]),
        "declared generation2 to3 publication",
    )
    need(
        published["repository_id"] == result["current_head"]["repository_id"]
        and published["operation_id"] == "signed-successor-format-publication",
        "declared publication source namespace",
    )
    need(
        result["controls"]
        == [
            {
                "error": "resume catalog head changed",
                "error_type": "StaleCodebaseError",
                "integrity_refusal_claimed": True,
                "name": "published_source_rejects_old_completion",
                "refused": True,
            }
        ],
        "exact typed stale-head observation",
    )
    need(
        same(result["public_receivers_reference_close"], declared["reference_close"]),
        "retained reference close projection",
    )
    reference = result["public_receivers_reference_close"]
    need(
        reference["budget_refused"] is True
        and reference["completed"] is reference["integrity_refusal_claimed"] is False
        and reference["error_type"] == "LeaseTimeoutError",
        "reference timeout is not completed baseline or integrity refusal",
    )
    return {
        "historical_scopes": {
            "source_successor_signed_worker_qualified": False,
            "later_signed_dispatch_recorded_qualified": True,
            "failed_attempt_count": 7,
            "failed_attempts": copy.deepcopy(review["failed_worker_attempts"]),
            "failed_archive_bodies_opened": False,
        },
        "admission": {
            "administrator_task_ids": list(TASK_IDS),
            "administrator_task_cids": task_cids,
            "pending_requirement_count": 4,
            "manifest_cid": manifest_cid,
            "planning_receipt_cid": byte_cid(admission["receipt"]),
            "manifest_profile_content_id": manifest["payload"]["profile_content_id"],
            "signature_declarations": signatures,
            "signatures_authenticated_here": False,
            "current_facts": [],
            "removed_task_cids": [],
        },
        "worker": {
            "recorded_boundary_receipt": copy.deepcopy(boundary_record),
            "recorded_output_receipt": copy.deepcopy(worker),
            "public_artifact_raw_sha256": pins["raw_public_worker_artifact"],
            "raw_and_decoded_artifacts_equal": True,
            "recorded_public_signature_verification": True,
            "public_signature_verification_performed_here": False,
        },
        "completion": {
            "prelaunch_task_statuses": ["completed", "ready"],
            "recorded_final_task_statuses": dict(result["native_task_statuses"]),
            "recorded_format_completion_receipt": copy.deepcopy(completion),
            "recorded_prerequisite_claim": copy.deepcopy(prerequisite),
            "recorded_prerequisite_validation": copy.deepcopy(docs["prerequisite_validation"]),
            "completion_authenticated_here": False,
        },
        "publication": {
            "recorded_merge": copy.deepcopy(publication),
            "recorded_source_receipt": copy.deepcopy(published),
            "recorded_stale_control": copy.deepcopy(result["controls"][0]),
            "public_checks_executed_here": False,
            "source_invalidation_reperformed_here": False,
        },
        "historical_costs": {
            "recorded_native_seconds": result["recorded_seconds"],
            "inherited_setup_epochs": 2,
            "inherited_default_pages": 10,
            "inherited_reference_pages": 1,
            "new_fitting_epochs": 0,
            "new_scan_pages": 0,
            "reference_close": copy.deepcopy(reference),
            "completed_reference_speed_baseline": False,
        },
    }


def publish(path, raw):
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
    try:
        offset = 0
        while offset < len(raw):
            count = os.write(fd, raw[offset:])
            need(count > 0, "complete exclusive publication")
            offset += count
    finally:
        os.close(fd)


def audit(manifest_path, output):
    manifest_path, output = Path(manifest_path).absolute(), Path(output).absolute()
    capture = Capture()
    manifest_raw = capture.take(manifest_path, MAX_MANIFEST)
    manifest = document(manifest_raw)
    closed(manifest, ("schema", "selected_files"), "input manifest")
    need(
        manifest["schema"] == INPUT_SCHEMA
        and type(manifest["selected_files"]) is list
        and len(manifest["selected_files"]) == len(ROLES) <= MAX_ORIGINALS,
        "finite ordered input profile",
    )
    docs, pins, raw_bodies, selections, identities = {}, {}, {}, [], set()
    for role, row in zip(ROLES, manifest["selected_files"], strict=True):
        closed(row, ("role", "path", "sha256", "size_bytes"), "selected descriptor")
        need(
            row["role"] == role
            and type(row["path"]) is str
            and digest(row["sha256"])
            and integer(row["size_bytes"], 1, MAX_FILE),
            "typed ordered descriptor",
        )
        path = Path(row["path"])
        need(
            path.is_absolute() and path != manifest_path and path not in capture.raw,
            "distinct absolute selected body",
        )
        raw = capture.take(path)
        identity = path.stat(follow_symlinks=False)
        key = (identity.st_dev, identity.st_ino)
        need(key not in identities, "no selected physical aliases")
        identities.add(key)
        need(
            sha(raw) == row["sha256"] and len(raw) == row["size_bytes"],
            "exact selected raw descriptor",
        )
        pins[role], raw_bodies[role] = sha(raw), raw
        if role != "worker_stdout_log":
            docs[role] = document(raw)
        selections.append(dict(row))
    docs["worker_boundary_receipt"], docs["worker_output_receipt"] = worker_log(
        raw_bodies["worker_stdout_log"]
    )
    need(
        not os.path.lexists(output) and output.parent.resolve(strict=True) == output.parent,
        "fresh output under canonical parent",
    )
    need(
        not any(
            output == path.parent
            or output.is_relative_to(path.parent)
            or path.is_relative_to(output)
            for path in capture.raw
        ),
        "output separated from input directories",
    )
    capture.stable()
    summary = reconcile(docs, pins, raw_bodies)
    capture.stable()
    output.mkdir()
    retained = output / "retained"
    retained.mkdir()
    local_manifest = retained / "input_manifest.json"
    publish(local_manifest, manifest_raw)
    need(
        capture.take(local_manifest, MAX_MANIFEST) == manifest_raw,
        "published manifest bytes unchanged",
    )
    expected = {REPORT_NAME, "retained/input_manifest.json"}
    for index, row in enumerate(selections):
        relative = f"retained/{index:02d}-{row['role']}.body"
        path = output / relative
        original = capture.raw[Path(row["path"])]
        publish(path, original)
        need(capture.take(path) == original, "published retained bytes unchanged")
        row["retained_copy"] = {
            "path": str(path),
            "sha256": row["sha256"],
            "size_bytes": row["size_bytes"],
        }
        expected.add(relative)
    report = {
        "schema": REPORT_SCHEMA,
        "workflow": "signed_worker_acceptance_controls",
        "status": "passed",
        "qualified": True,
        "fixture_origin": "retained_signed_successor_worker_metadata",
        "manifest_sha256": sha(manifest_raw),
        **{key: True for key in TRUE},
        **{key: False for key in FALSE},
        **{key: 0 for key in ZERO},
        **{role + "_sha256": pins[role] for role in ROLES},
        "selected_file_count": 20,
        "selected_input_bytes": sum(row["size_bytes"] for row in selections),
        "selected_files": selections,
        **summary,
        "production_tasks_closed": [],
        "custody": {
            "retained_manifest": {
                "path": str(local_manifest),
                "sha256": sha(manifest_raw),
                "size_bytes": len(manifest_raw),
            },
            "raw_bodies_reread": True,
            "exact_output_population": True,
            "original_metadata_body_count": 20,
            "retained_metadata_body_count": 20,
            "output_regular_file_count": 22,
            "output_directory_count": 1,
            "closing_raw_body_count": 43,
        },
        "limits": {
            "max_selected_files": MAX_ORIGINALS,
            "max_captured_files": MAX_FILES,
            "max_body_bytes": MAX_FILE,
            "max_aggregate_bytes": MAX_TOTAL,
            "max_manifest_bytes": MAX_MANIFEST,
            "max_report_bytes": MAX_REPORT,
            "max_json_depth": 32,
            "max_json_values": 100000,
        },
        "limitations": [
            "Twenty explicit metadata bodies only; nested archive, source, key, database and model references are not opened.",
            "Signature syntax, identity declarations and complete envelope byte CIDs are reconciled; signatures and historical process origins are not authenticated.",
            "Two complete administrator tasks and all mandatory evidence remain; recorded native completion creates no new behavioral, proof or task-omission authority.",
            "Worker output, accepted source transition, merge parents and public check bytes are retained observations; no proposal policy, Git, native worker or public checker runs here.",
            "Generation2-to3 and exact StaleCodebaseError are recorded scope bindings; full corpus/dependency invalidation is a separate receiving workflow.",
            "Seven failed archive descriptors and the former unsigned source-plan scope remain historical declarations; their bodies and the 23202-file closed archive are not followed.",
            "UID/private-denial/STOP metadata grants no physical process absence, cgroup enforcement, cleanup authentication or general crash-recovery authority.",
            "Two setup epochs and ten default plus one reference pages are inherited; dispatch and this receiver perform zero new fits, inference, scan pages or provider calls.",
            "The public reference close timed out; it supplies neither completed speed baseline nor an integrity-refusal or throughput claim.",
            "Original and retained bytes, file and directory generations and exact populations are closed sequentially; no atomic filesystem snapshot is claimed.",
        ],
    }
    target = output / REPORT_NAME
    serialized = report_bytes(report)
    publish(target, serialized)
    need(capture.take(target, MAX_REPORT) == serialized, "published report bytes unchanged")
    final_fence(capture, output, expected)
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    try:
        report = audit(args.manifest, args.output)
    except (Refusal, OSError, ValueError, KeyError, TypeError) as exc:
        print("refused: " + str(exc))
        return 1
    print(
        json.dumps(
            {
                "status": report["status"],
                "report": str(args.output / REPORT_NAME),
                "selected_file_count": report["selected_file_count"],
            },
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
