"""Bounded offline custody of retained serialized TLA artifact metadata.

This receiver never imports producer code, executes a checker, or interprets a
source map as semantic evidence. All native observations are historical.
"""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
import math
import os
import re
import stat
from pathlib import Path

INPUT_SCHEMA = "codebase-ir-artifact-payload-controls-input@1"
REPORT_SCHEMA = "codebase-ir-artifact-payload-controls@1"
REPORT_NAME = "artifact_payload_controls.json"
MAX_FILES, MAX_FILE, MAX_TOTAL = 128, 1024 * 1024, 8 * 1024 * 1024
MAX_ORIGINALS, MAX_MANIFEST, MAX_REPORT = 64, 128 * 1024, 4 * 1024 * 1024
CASE_IDS = ("artifact-payload:apalache:true", "artifact-payload:apalache:false")
ROLES = (
    "qualification",
    "source_evolution",
    "source_snapshot",
    "execution_freeze",
    "benchmark_preflight",
    "joined_selected_result",
    "native_command_result",
    "native_command",
    "native_result",
    "native_fixtures",
    "native_request_audit",
    "native_phase_budget_audit",
    "native_lifecycle_audit",
    "native_apalache_environment_audit",
    "native_launch_audit",
    "historical_foreign_outcome_reference",
)

TRUE = (
    "retained_artifact_payload_custody_conformance",
    "serialized_artifact_identity_rederived",
    "serialized_text_digests_rederived",
    "complete_artifact_metadata_preserved",
    "three_step_native_command_binding_reconciled",
    "static_v2_projection_preserved",
    "generic_unknown_authority_preserved",
    "exact_typed_payload_preserved",
    "recorded_phase_bindings_reconciled",
    "historical_raw_witness_scope_preserved",
    "historical_foreign_reference_preserved",
    "input_files_unchanged",
)
FALSE = (
    "native_execution_performed",
    "training_executed",
    "current_authority_claimed",
    "owner_database_opened",
    "profile_keys_read",
    "owner_sources_imported",
    "checker_executions_replayed",
    "source_execution_replayed",
    "signature_authentication_performed",
    "process_origin_attested",
    "original_request_custody_qualified",
    "model_check_authority_qualified",
    "proof_authority_qualified",
    "counterexample_replay_qualified",
    "structural_replay_qualified",
    "semantic_replay_qualified",
    "source_map_semantic_truth_qualified",
    "translation_correctness_qualified",
    "unbounded_proof_qualified",
    "native_v2_execution_qualified",
    "legacy_fallback_decoder_qualified",
    "default_registry_operation_budget_qualified",
    "registry_native_success_qualified",
    "resource_enforcement_qualified",
    "hard_aggregate_containment_qualified",
    "whole_install_cancellation_qualified",
    "live_eligibility_qualified",
    "production_acceptance_qualified",
    "native_export_adoption_qualified",
    "throughput_improvement_qualified",
    "model_quality_qualified",
    "output_digest_algorithm_rederived",
    "nested_source_or_tool_bodies_opened",
)
ZERO = ("runtime_fact_count", "tasks_omitted_count", "additional_attempted_training_epochs")

DIAGNOSTIC = (
    "foreign outcome recorded without authority upgrade; generic conclusions remain non-conclusive"
)

TRACE_NOTE = "counterexample contained no parseable State blocks"

RESULT_FIELDS = {
    "audit_sha256",
    "cases",
    "checks",
    "child_usage",
    "dispatches",
    "elapsed_seconds",
    "launches",
    "lifecycles",
    "native_lifecycles",
    "packaged_native_entries",
    "phase_counts",
    "prelaunch_lifecycles",
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
}

CASE_FIELDS = {
    "aggregate_scope_owner",
    "attempt",
    "attempt_digest",
    "case",
    "default_lazy_factory_used",
    "dispatch",
    "elapsed_seconds",
    "factory_restored",
    "operation_timeout_ms",
    "original_outcome",
    "original_return_observer_restored",
    "phase_count",
    "projection_checks",
    "raw_witness",
    "request",
    "request_digest",
    "result",
    "selected_delegate_count",
    "valid",
}

REQUEST_FIELDS = {
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
}

ATTEMPT_FIELDS = {
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
}

GENERIC_FIELDS = {
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
}

TYPED_FIELDS = {
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
}

ARTIFACT_FIELDS = {
    "apalache_config_digest",
    "apalache_config_text",
    "artifact_digest",
    "bounded",
    "bounds",
    "fairness_limitations",
    "interface_version",
    "liveness_properties",
    "losses",
    "model_digest",
    "model_text",
    "module_name",
    "safety_properties",
    "schema_version",
    "source_document_id",
    "source_kind",
    "source_map",
    "tlc_config_digest",
    "tlc_config_text",
    "translator",
    "unbounded_proof",
}

RECEIPT_FIELDS = {
    "artifact_digest",
    "bounded",
    "capability",
    "checked_liveness_properties",
    "checked_safety_properties",
    "command",
    "configuration_digest",
    "configuration_text",
    "counterexample",
    "elapsed_ms",
    "executable",
    "fairness_limitations",
    "jvm_available",
    "model_digest",
    "output_truncated",
    "reason",
    "receipt_id",
    "returncode",
    "schema_version",
    "status",
    "stderr",
    "stdout",
    "timeout_seconds",
    "tool",
    "tool_version",
    "unbounded_proof",
}

LIFE_FALSE = (
    "cancelled",
    "output_truncated",
    "process_tree_terminated",
    "resource_exhausted",
    "timed_out",
    "unavailable",
    "workspace_limit_exceeded",
)

CASE_FIELDS |= {"complete_artifact_equal", "decoded_artifact", "submitted_artifact"}

METADATA_SHAPES = {
    "benchmark_preflight": 48,
    "execution_freeze": 25,
    "historical_foreign_outcome_reference": 162,
    "joined_selected_result": 52,
    "native_apalache_environment_audit": 132,
    "native_command": 55,
    "native_command_result": 54,
    "native_fixtures": 107,
    "native_launch_audit": 141,
    "native_lifecycle_audit": 130,
    "native_phase_budget_audit": 117,
    "native_request_audit": 115,
    "native_result": 106,
    "qualification": 12,
    "source_evolution": 14,
    "source_snapshot": 23,
}

SHAPE_NODES = [
    ("str",),
    (
        "dict",
        {
            "benchmark-preflight.json": 0,
            "benchmark-static/tlc-memory-aware": 0,
            "build_report.py": 0,
            "capture_sources.py": 0,
            "compiler-implementation.diff": 0,
            "execution-freeze.json": 0,
            "execution_v2-implementation.diff": 0,
            "focused-initial-sources/tests/integration/logic/backends/test_tla_model_checkers.py": 0,
            "focused-initial-sources/tests/integration/logic_providers/test_tla_execution_v2.py": 0,
            "focused-initial-sources/tests/unit/logic/backends/test_apalache_resource_admission.py": 0,
            "focused-initial-sources/tests/unit/logic/backends/test_registry_foreign_outcomes.py": 0,
            "focused-initial-sources/tests/unit/logic/backends/test_tla_artifact_payload.py": 0,
            "focused-initial-sources/tests/unit/logic/backends/test_tla_operation_control.py": 0,
            "focused-initial-sources/tests/unit/logic/backends/test_tla_outcome_integrity.py": 0,
            "focused-initial.command.json": 0,
            "focused-initial.log": 0,
            "focused-initial.result.json": 0,
            "focused-initial.xml": 0,
            "joined-selected-sources/tests/conformance/logic/test_authority_boundaries.py": 0,
            "joined-selected-sources/tests/conformance/logic/test_classical_backend_routes.py": 0,
            "joined-selected-sources/tests/conformance/logic/test_registry_closure.py": 0,
            "joined-selected-sources/tests/integration/logic/backends/test_state_model_preparation.py": 0,
            "joined-selected-sources/tests/integration/logic/backends/test_tla_model_checkers.py": 0,
            "joined-selected-sources/tests/integration/logic/backends/test_tla_runner_resource_bounds.py": 0,
            "joined-selected-sources/tests/integration/logic/backends/test_z3_cvc5_software_verification.py": 0,
            "joined-selected-sources/tests/integration/logic/software_verification/test_source_adapter_snapshot_grounding.py": 0,
            "joined-selected-sources/tests/integration/logic/software_verification/test_source_vc_smt_pipeline.py": 0,
            "joined-selected-sources/tests/integration/logic_providers/test_smt_execution_v2.py": 0,
            "joined-selected-sources/tests/integration/logic_providers/test_tla_execution_v2.py": 0,
            "joined-selected-sources/tests/unit/logic/backends/test_apalache_resource_admission.py": 0,
            "joined-selected-sources/tests/unit/logic/backends/test_java_probe_admission.py": 0,
            "joined-selected-sources/tests/unit/logic/backends/test_protocol_v1_adapter.py": 0,
            "joined-selected-sources/tests/unit/logic/backends/test_provider_protocol_v2.py": 0,
            "joined-selected-sources/tests/unit/logic/backends/test_registry.py": 0,
            "joined-selected-sources/tests/unit/logic/backends/test_registry_foreign_outcomes.py": 0,
            "joined-selected-sources/tests/unit/logic/backends/test_resource_admission.py": 0,
            "joined-selected-sources/tests/unit/logic/backends/test_smt_consumer_admission.py": 0,
            "joined-selected-sources/tests/unit/logic/backends/test_smt_operation_benchmark_pool_guard.py": 0,
            "joined-selected-sources/tests/unit/logic/backends/test_smt_operation_control.py": 0,
            "joined-selected-sources/tests/unit/logic/backends/test_smt_resource_admission.py": 0,
            "joined-selected-sources/tests/unit/logic/backends/test_smt_v2_operation_control.py": 0,
            "joined-selected-sources/tests/unit/logic/backends/test_state_model_probe_admission.py": 0,
            "joined-selected-sources/tests/unit/logic/backends/test_tla_artifact_payload.py": 0,
            "joined-selected-sources/tests/unit/logic/backends/test_tla_operation_control.py": 0,
            "joined-selected-sources/tests/unit/logic/backends/test_tla_outcome_integrity.py": 0,
            "joined-selected-sources/tests/unit/logic/software_contracts/test_codebase_smt_execution.py": 0,
            "joined-selected-sources/tests/unit/logic/software_contracts/test_codebase_smt_execution_receipts.py": 0,
            "joined-selected-sources/tests/unit/logic/software_contracts/test_codebase_smt_protocol.py": 0,
            "joined-selected-sources/tests/unit/logic/software_verification/test_bundled_program_ast_mirroring.py": 0,
            "joined-selected-sources/tests/unit/logic/software_verification/test_program_ast_provider_capabilities.py": 0,
            "joined-selected-sources/tests/unit/logic/software_verification/test_source_mirroring_control.py": 0,
            "joined-selected-sources/tests/unit/logic/test_compositional_verification_public_api.py": 0,
            "joined-selected-sources/tests/unit/logic/test_verification_api.py": 0,
            "joined-selected-sources/tests/unit_tests/logic/external_provers/test_lazy_native_solver_installation.py": 0,
            "joined-selected-sources/tests/unit_tests/logic/integration/test_state_model_installer_runtime.py": 0,
            "joined-selected.command.json": 0,
            "joined-selected.log": 0,
            "joined-selected.result.json": 0,
            "joined-selected.xml": 0,
            "native-command-result.json": 0,
            "native-command.json": 0,
            "native.log": 0,
            "native/apalache-environment-audit.json": 0,
            "native/command.json": 0,
            "native/fixtures.json": 0,
            "native/launch-audit.json": 0,
            "native/lifecycle-audit.json": 0,
            "native/partial.json": 0,
            "native/phase-budget-audit.json": 0,
            "native/request-audit.json": 0,
            "native/result.json": 0,
            "native/saved-scheduler-config.json": 0,
            "native/tlc-memory-aware": 0,
            "preimages/compiler.py": 0,
            "preimages/execution_v2.py": 0,
            "preimages/runners.py": 0,
            "preservation-after.json": 0,
            "preservation-before.json": 0,
            "run_native.py": 0,
            "run_static_preflight.py": 0,
            "run_tests.py": 0,
            "runners-implementation.diff": 0,
            "selected-source/bench_tla_artifact_payload.py": 0,
            "selected-source/compiler.py": 0,
            "selected-source/execution_v2.py": 0,
            "selected-source/runners.py": 0,
            "selected-source/test_tla_artifact_payload.py": 0,
            "source-evolution.json": 0,
            "source-snapshot.json": 0,
        },
    ),
    ("bool",),
    (
        "dict",
        {
            "complete_artifact_preserved": 2,
            "exact_foreign_typed_payload": 2,
            "exact_two_serial_cases": 2,
            "expected_real_phases": 2,
            "java_selection_environment_restored": 2,
            "native_environments_sanitized": 2,
            "no_generic_authority_promotion": 2,
            "observer_and_factory_restored": 2,
            "owned_apalache_jvm_environments": 2,
            "owned_work_drained": 2,
            "selected_tool_files_unchanged": 2,
            "shared_config_unchanged": 2,
            "sources_stable": 2,
        },
    ),
    ("int",),
    ("float",),
    (
        "dict",
        {
            "existing_test_files_changed": 4,
            "historical_hash_aliases_added": 2,
            "prior_artifacts": 4,
            "prior_qualifications": 4,
            "production_files_changed": 4,
        },
    ),
    ("list", 0, ()),
    ("list", 2015, (0,)),
    ("dict", {"passed": 4}),
    (
        "dict",
        {
            "accepted": 2,
            "counts": 9,
            "returncode": 4,
            "seconds": 5,
            "sources_stable": 2,
            "suite": 0,
        },
    ),
    ("dict", {"focused-initial": 10, "joined-selected": 10}),
    (
        "dict",
        {
            "artifact_sha256": 1,
            "checks": 3,
            "deselected_legacy_native_tests": 4,
            "focused_tests": 4,
            "native_phases": 4,
            "native_seconds": 5,
            "native_success_cases": 4,
            "native_wrapper_seconds": 5,
            "new_artifact_tests": 4,
            "new_cache_replay": 2,
            "new_codebase_smt_execution": 2,
            "preservation": 6,
            "production_tasks_closed": 7,
            "recorded_at_utc": 0,
            "schema": 0,
            "selected_test_cases": 8,
            "selected_tests": 4,
            "status": 0,
            "test_attempts": 11,
            "test_counts_summed": 2,
        },
    ),
    (
        "dict",
        {
            "after_sha256": 0,
            "after_snapshot": 0,
            "before_sha256": 0,
            "before_snapshot": 0,
            "diff": 0,
            "diff_sha256": 0,
            "kind": 0,
        },
    ),
    (
        "dict",
        {
            "/home/barberb/lift_coding/external/ipfs_datasets/ipfs_datasets_py/logic/backends/tla/compiler.py": 13,
            "/home/barberb/lift_coding/external/ipfs_datasets/ipfs_datasets_py/logic/backends/tla/execution_v2.py": 13,
            "/home/barberb/lift_coding/external/ipfs_datasets/ipfs_datasets_py/logic/backends/tla/runners.py": 13,
        },
    ),
    (
        "dict",
        {
            "/home/barberb/lift_coding/external/ipfs_accelerate/docs/architecture/REPOSITORY_PROOF_INDEX_AND_CODEBASE_IR_PLAN.md": 0,
            "/home/barberb/lift_coding/external/ipfs_accelerate/docs/architecture/REPOSITORY_PROOF_INDEX_AND_CODEBASE_IR_ROADMAP.md": 0,
            "/home/barberb/lift_coding/external/ipfs_accelerate/docs/architecture/repository_proof_index_and_codebase_ir.todo.md": 0,
            "/home/barberb/lift_coding/external/ipfs_datasets/docs/autoencoders/codebase_ir_repository_pipeline_improvement_plan.md": 0,
            "/home/barberb/lift_coding/external/ipfs_datasets/docs/autoencoders/codebase_ir_repository_pipeline_plan.json": 0,
            "/home/barberb/lift_coding/external/ipfs_datasets/docs/implementation/runbooks/resource_aware_proving.md": 0,
            "/home/barberb/lift_coding/external/ipfs_datasets/docs/software_contracts/CODEBASE_IR_FOUNDATION.md": 0,
        },
    ),
    (
        "dict",
        {
            "/home/barberb/lift_coding/external/ipfs_accelerate/ipfs_accelerate_py/__init__.py": 0,
            "/home/barberb/lift_coding/external/ipfs_accelerate/ipfs_accelerate_py/agent_supervisor/__init__.py": 0,
            "/home/barberb/lift_coding/external/ipfs_accelerate/ipfs_accelerate_py/agent_supervisor/planning/__init__.py": 0,
            "/home/barberb/lift_coding/external/ipfs_accelerate/ipfs_accelerate_py/agent_supervisor/planning/conditional_codebase_evidence.py": 0,
            "/home/barberb/lift_coding/external/ipfs_accelerate/ipfs_accelerate_py/agent_supervisor/planning/structural_codebase_context.py": 0,
            "/home/barberb/lift_coding/external/ipfs_datasets/benchmarks/bench_apalache_resource_admission.py": 0,
            "/home/barberb/lift_coding/external/ipfs_datasets/benchmarks/bench_codebase_evidence_queries.py": 0,
            "/home/barberb/lift_coding/external/ipfs_datasets/benchmarks/bench_codebase_restart_safety.py": 0,
            "/home/barberb/lift_coding/external/ipfs_datasets/benchmarks/bench_codebase_smt_execution.py": 0,
            "/home/barberb/lift_coding/external/ipfs_datasets/benchmarks/bench_generic_prover_admission.py": 0,
            "/home/barberb/lift_coding/external/ipfs_datasets/benchmarks/bench_java_probe_admission.py": 0,
            "/home/barberb/lift_coding/external/ipfs_datasets/benchmarks/bench_registry_foreign_outcomes.py": 0,
            "/home/barberb/lift_coding/external/ipfs_datasets/benchmarks/bench_smt_consumer_admission.py": 0,
            "/home/barberb/lift_coding/external/ipfs_datasets/benchmarks/bench_smt_operation_control.py": 0,
            "/home/barberb/lift_coding/external/ipfs_datasets/benchmarks/bench_smt_resource_admission.py": 0,
            "/home/barberb/lift_coding/external/ipfs_datasets/benchmarks/bench_smt_v2_operation_control.py": 0,
            "/home/barberb/lift_coding/external/ipfs_datasets/benchmarks/bench_source_mirroring_compatibility.py": 0,
            "/home/barberb/lift_coding/external/ipfs_datasets/benchmarks/bench_state_model_probe_admission.py": 0,
            "/home/barberb/lift_coding/external/ipfs_datasets/benchmarks/bench_tla_artifact_payload.py": 0,
            "/home/barberb/lift_coding/external/ipfs_datasets/benchmarks/bench_tla_operation_control.py": 0,
            "/home/barberb/lift_coding/external/ipfs_datasets/benchmarks/bench_tla_outcome_integrity.py": 0,
            "/home/barberb/lift_coding/external/ipfs_datasets/ipfs_datasets_py/duckdb_control/codebase_catalog.py": 0,
            "/home/barberb/lift_coding/external/ipfs_datasets/ipfs_datasets_py/duckdb_control/codebase_verification_catalog.py": 0,
            "/home/barberb/lift_coding/external/ipfs_datasets/ipfs_datasets_py/duckdb_control/codebase_verification_projection.py": 0,
            "/home/barberb/lift_coding/external/ipfs_datasets/ipfs_datasets_py/duckdb_control/codebase_verification_queries.py": 0,
            "/home/barberb/lift_coding/external/ipfs_datasets/ipfs_datasets_py/logic/backends/cvc5/__init__.py": 0,
            "/home/barberb/lift_coding/external/ipfs_datasets/ipfs_datasets_py/logic/backends/cvc5/compiler.py": 0,
            "/home/barberb/lift_coding/external/ipfs_datasets/ipfs_datasets_py/logic/backends/installers/state_model.py": 0,
            "/home/barberb/lift_coding/external/ipfs_datasets/ipfs_datasets_py/logic/backends/process.py": 0,
            "/home/barberb/lift_coding/external/ipfs_datasets/ipfs_datasets_py/logic/backends/registry.py": 0,
            "/home/barberb/lift_coding/external/ipfs_datasets/ipfs_datasets_py/logic/backends/resource_admission.py": 0,
            "/home/barberb/lift_coding/external/ipfs_datasets/ipfs_datasets_py/logic/backends/results.py": 0,
            "/home/barberb/lift_coding/external/ipfs_datasets/ipfs_datasets_py/logic/backends/smt/__init__.py": 0,
            "/home/barberb/lift_coding/external/ipfs_datasets/ipfs_datasets_py/logic/backends/smt/admitted.py": 0,
            "/home/barberb/lift_coding/external/ipfs_datasets/ipfs_datasets_py/logic/backends/smt/admitted_differential.py": 0,
            "/home/barberb/lift_coding/external/ipfs_datasets/ipfs_datasets_py/logic/backends/smt/compiler.py": 0,
            "/home/barberb/lift_coding/external/ipfs_datasets/ipfs_datasets_py/logic/backends/smt/differential.py": 0,
            "/home/barberb/lift_coding/external/ipfs_datasets/ipfs_datasets_py/logic/backends/smt/execution_v2.py": 0,
            "/home/barberb/lift_coding/external/ipfs_datasets/ipfs_datasets_py/logic/backends/smt/operation_budget.py": 0,
            "/home/barberb/lift_coding/external/ipfs_datasets/ipfs_datasets_py/logic/backends/tla/compiler.py": 0,
            "/home/barberb/lift_coding/external/ipfs_datasets/ipfs_datasets_py/logic/backends/tla/execution_v2.py": 0,
            "/home/barberb/lift_coding/external/ipfs_datasets/ipfs_datasets_py/logic/backends/tla/runners.py": 0,
            "/home/barberb/lift_coding/external/ipfs_datasets/ipfs_datasets_py/logic/backends/z3/__init__.py": 0,
            "/home/barberb/lift_coding/external/ipfs_datasets/ipfs_datasets_py/logic/backends/z3/compiler.py": 0,
            "/home/barberb/lift_coding/external/ipfs_datasets/ipfs_datasets_py/logic/common/canonical_cache_key.py": 0,
            "/home/barberb/lift_coding/external/ipfs_datasets/ipfs_datasets_py/logic/intent_ir/schema.py": 0,
            "/home/barberb/lift_coding/external/ipfs_datasets/ipfs_datasets_py/logic/ir_core/claims.py": 0,
            "/home/barberb/lift_coding/external/ipfs_datasets/ipfs_datasets_py/logic/ir_core/identity.py": 0,
            "/home/barberb/lift_coding/external/ipfs_datasets/ipfs_datasets_py/logic/ir_core/protocols.py": 0,
            "/home/barberb/lift_coding/external/ipfs_datasets/ipfs_datasets_py/logic/ir_core/provenance.py": 0,
            "/home/barberb/lift_coding/external/ipfs_datasets/ipfs_datasets_py/logic/parsers/classical_adapters.py": 0,
            "/home/barberb/lift_coding/external/ipfs_datasets/ipfs_datasets_py/logic/parsers/smtlib.py": 0,
            "/home/barberb/lift_coding/external/ipfs_datasets/ipfs_datasets_py/logic/software_contracts/cache.py": 0,
            "/home/barberb/lift_coding/external/ipfs_datasets/ipfs_datasets_py/logic/software_contracts/codebase_applicability.py": 0,
            "/home/barberb/lift_coding/external/ipfs_datasets/ipfs_datasets_py/logic/software_contracts/codebase_integer_profile.py": 0,
            "/home/barberb/lift_coding/external/ipfs_datasets/ipfs_datasets_py/logic/software_contracts/codebase_ir.py": 0,
            "/home/barberb/lift_coding/external/ipfs_datasets/ipfs_datasets_py/logic/software_contracts/codebase_resources.py": 0,
            "/home/barberb/lift_coding/external/ipfs_datasets/ipfs_datasets_py/logic/software_contracts/codebase_smt_compat.py": 0,
            "/home/barberb/lift_coding/external/ipfs_datasets/ipfs_datasets_py/logic/software_contracts/codebase_smt_execution.py": 0,
            "/home/barberb/lift_coding/external/ipfs_datasets/ipfs_datasets_py/logic/software_contracts/codebase_smt_protocol.py": 0,
            "/home/barberb/lift_coding/external/ipfs_datasets/ipfs_datasets_py/logic/software_contracts/codebase_verification.py": 0,
            "/home/barberb/lift_coding/external/ipfs_datasets/ipfs_datasets_py/logic/software_contracts/content.py": 0,
            "/home/barberb/lift_coding/external/ipfs_datasets/ipfs_datasets_py/logic/software_contracts/duckdb_ast_store.py": 0,
            "/home/barberb/lift_coding/external/ipfs_datasets/ipfs_datasets_py/logic/software_contracts/duckdb_ingest.py": 0,
            "/home/barberb/lift_coding/external/ipfs_datasets/ipfs_datasets_py/logic/software_verification/__init__.py": 0,
            "/home/barberb/lift_coding/external/ipfs_datasets/ipfs_datasets_py/logic/software_verification/admitted_pipeline.py": 0,
            "/home/barberb/lift_coding/external/ipfs_datasets/ipfs_datasets_py/logic/software_verification/applicability.py": 0,
            "/home/barberb/lift_coding/external/ipfs_datasets/ipfs_datasets_py/logic/software_verification/concurrency.py": 0,
            "/home/barberb/lift_coding/external/ipfs_datasets/ipfs_datasets_py/logic/software_verification/contracts.py": 0,
            "/home/barberb/lift_coding/external/ipfs_datasets/ipfs_datasets_py/logic/software_verification/ir.py": 0,
            "/home/barberb/lift_coding/external/ipfs_datasets/ipfs_datasets_py/logic/software_verification/pipeline.py": 0,
            "/home/barberb/lift_coding/external/ipfs_datasets/ipfs_datasets_py/logic/software_verification/program.py": 0,
            "/home/barberb/lift_coding/external/ipfs_datasets/ipfs_datasets_py/logic/software_verification/properties.py": 0,
            "/home/barberb/lift_coding/external/ipfs_datasets/ipfs_datasets_py/logic/software_verification/receipts.py": 0,
            "/home/barberb/lift_coding/external/ipfs_datasets/ipfs_datasets_py/logic/software_verification/refinement.py": 0,
            "/home/barberb/lift_coding/external/ipfs_datasets/ipfs_datasets_py/logic/software_verification/source_adapters.py": 0,
            "/home/barberb/lift_coding/external/ipfs_datasets/ipfs_datasets_py/logic/software_verification/state.py": 0,
            "/home/barberb/lift_coding/external/ipfs_datasets/ipfs_datasets_py/logic/software_verification/transitions.py": 0,
            "/home/barberb/lift_coding/external/ipfs_datasets/ipfs_datasets_py/logic/software_verification/translations.py": 0,
            "/home/barberb/lift_coding/external/ipfs_datasets/ipfs_datasets_py/logic/software_verification/vc.py": 0,
            "/home/barberb/lift_coding/external/ipfs_datasets/ipfs_datasets_py/logic/syntax_core/contracts.py": 0,
            "/home/barberb/lift_coding/external/ipfs_datasets/ipfs_datasets_py/logic/verification_api.py": 0,
            "/home/barberb/lift_coding/external/ipfs_datasets/ipfs_datasets_py/optimizers/logic_theorem_optimizer/proof_resource_safety.py": 0,
            "/home/barberb/lift_coding/external/ipfs_datasets/ipfs_datasets_py/optimizers/logic_theorem_optimizer/resource_scheduler.py": 0,
        },
    ),
    ("dict", {"module": 0, "sha256": 0}),
    ("list", 29, (17,)),
    ("list", 27, (17,)),
    ("dict", {"applicability": 18, "verification": 19}),
    (
        "dict",
        {
            "/home/barberb/lift_coding/external/ipfs_accelerate/ipfs_accelerate_py/__init__.py": 0,
            "/home/barberb/lift_coding/external/ipfs_accelerate/ipfs_accelerate_py/agent_supervisor/__init__.py": 0,
            "/home/barberb/lift_coding/external/ipfs_accelerate/ipfs_accelerate_py/agent_supervisor/analysis/program_ast_adapters.py": 0,
            "/home/barberb/lift_coding/external/ipfs_accelerate/ipfs_accelerate_py/agent_supervisor/planning/__init__.py": 0,
            "/home/barberb/lift_coding/external/ipfs_accelerate/ipfs_accelerate_py/agent_supervisor/planning/conditional_codebase_evidence.py": 0,
            "/home/barberb/lift_coding/external/ipfs_accelerate/ipfs_accelerate_py/agent_supervisor/planning/structural_codebase_context.py": 0,
            "/home/barberb/lift_coding/external/ipfs_datasets/benchmarks/bench_apalache_resource_admission.py": 0,
            "/home/barberb/lift_coding/external/ipfs_datasets/benchmarks/bench_codebase_evidence_queries.py": 0,
            "/home/barberb/lift_coding/external/ipfs_datasets/benchmarks/bench_codebase_restart_safety.py": 0,
            "/home/barberb/lift_coding/external/ipfs_datasets/benchmarks/bench_codebase_smt_execution.py": 0,
            "/home/barberb/lift_coding/external/ipfs_datasets/benchmarks/bench_generic_prover_admission.py": 0,
            "/home/barberb/lift_coding/external/ipfs_datasets/benchmarks/bench_java_probe_admission.py": 0,
            "/home/barberb/lift_coding/external/ipfs_datasets/benchmarks/bench_registry_foreign_outcomes.py": 0,
            "/home/barberb/lift_coding/external/ipfs_datasets/benchmarks/bench_smt_consumer_admission.py": 0,
            "/home/barberb/lift_coding/external/ipfs_datasets/benchmarks/bench_smt_operation_control.py": 0,
            "/home/barberb/lift_coding/external/ipfs_datasets/benchmarks/bench_smt_resource_admission.py": 0,
            "/home/barberb/lift_coding/external/ipfs_datasets/benchmarks/bench_smt_v2_operation_control.py": 0,
            "/home/barberb/lift_coding/external/ipfs_datasets/benchmarks/bench_source_mirroring_compatibility.py": 0,
            "/home/barberb/lift_coding/external/ipfs_datasets/benchmarks/bench_state_model_probe_admission.py": 0,
            "/home/barberb/lift_coding/external/ipfs_datasets/benchmarks/bench_tla_artifact_payload.py": 0,
            "/home/barberb/lift_coding/external/ipfs_datasets/benchmarks/bench_tla_operation_control.py": 0,
            "/home/barberb/lift_coding/external/ipfs_datasets/benchmarks/bench_tla_outcome_integrity.py": 0,
            "/home/barberb/lift_coding/external/ipfs_datasets/ipfs_accelerate_py/__init__.py": 0,
            "/home/barberb/lift_coding/external/ipfs_datasets/ipfs_accelerate_py/ipfs_accelerate_py/agent_supervisor/__init__.py": 0,
            "/home/barberb/lift_coding/external/ipfs_datasets/ipfs_accelerate_py/ipfs_accelerate_py/agent_supervisor/analysis/__init__.py": 0,
            "/home/barberb/lift_coding/external/ipfs_datasets/ipfs_accelerate_py/ipfs_accelerate_py/agent_supervisor/analysis/analysis_ast_index.py": 0,
            "/home/barberb/lift_coding/external/ipfs_datasets/ipfs_accelerate_py/ipfs_accelerate_py/agent_supervisor/analysis/program_ast_adapters.py": 0,
            "/home/barberb/lift_coding/external/ipfs_datasets/ipfs_accelerate_py/ipfs_accelerate_py/agent_supervisor/analysis/repository_corpus_index.py": 0,
            "/home/barberb/lift_coding/external/ipfs_datasets/ipfs_accelerate_py/ipfs_accelerate_py/agent_supervisor/analysis/repository_forest.py": 0,
            "/home/barberb/lift_coding/external/ipfs_datasets/ipfs_accelerate_py/ipfs_accelerate_py/agent_supervisor/control/__init__.py": 0,
            "/home/barberb/lift_coding/external/ipfs_datasets/ipfs_accelerate_py/ipfs_accelerate_py/agent_supervisor/control/control_contracts.py": 0,
            "/home/barberb/lift_coding/external/ipfs_datasets/ipfs_accelerate_py/ipfs_accelerate_py/agent_supervisor/control/control_plane.py": 0,
            "/home/barberb/lift_coding/external/ipfs_datasets/ipfs_accelerate_py/ipfs_accelerate_py/agent_supervisor/core/__init__.py": 0,
            "/home/barberb/lift_coding/external/ipfs_datasets/ipfs_accelerate_py/ipfs_accelerate_py/agent_supervisor/core/conflict_graph.py": 0,
            "/home/barberb/lift_coding/external/ipfs_datasets/ipfs_accelerate_py/ipfs_accelerate_py/agent_supervisor/core/multiformats_identity.py": 0,
            "/home/barberb/lift_coding/external/ipfs_datasets/ipfs_accelerate_py/ipfs_accelerate_py/agent_supervisor/merge/__init__.py": 0,
            "/home/barberb/lift_coding/external/ipfs_datasets/ipfs_accelerate_py/ipfs_accelerate_py/agent_supervisor/merge/checkout_lock.py": 0,
            "/home/barberb/lift_coding/external/ipfs_datasets/ipfs_accelerate_py/ipfs_accelerate_py/agent_supervisor/objectives/__init__.py": 0,
            "/home/barberb/lift_coding/external/ipfs_datasets/ipfs_accelerate_py/ipfs_accelerate_py/agent_supervisor/objectives/goal_completion.py": 0,
            "/home/barberb/lift_coding/external/ipfs_datasets/ipfs_accelerate_py/ipfs_accelerate_py/agent_supervisor/proof/__init__.py": 0,
            "/home/barberb/lift_coding/external/ipfs_datasets/ipfs_accelerate_py/ipfs_accelerate_py/agent_supervisor/proof/formal_verification_contracts.py": 0,
            "/home/barberb/lift_coding/external/ipfs_datasets/ipfs_accelerate_py/ipfs_accelerate_py/agent_supervisor/self_improvement/__init__.py": 0,
            "/home/barberb/lift_coding/external/ipfs_datasets/ipfs_accelerate_py/ipfs_accelerate_py/agent_supervisor/self_improvement/self_improvement_completion.py": 0,
            "/home/barberb/lift_coding/external/ipfs_datasets/ipfs_accelerate_py/ipfs_accelerate_py/agent_supervisor/task_sources/__init__.py": 0,
            "/home/barberb/lift_coding/external/ipfs_datasets/ipfs_accelerate_py/ipfs_accelerate_py/agent_supervisor/task_sources/task_identity.py": 0,
            "/home/barberb/lift_coding/external/ipfs_datasets/ipfs_accelerate_py/ipfs_accelerate_py/utils/__init__.py": 0,
            "/home/barberb/lift_coding/external/ipfs_datasets/ipfs_accelerate_py/ipfs_accelerate_py/utils/cid_utils.py": 0,
            "/home/barberb/lift_coding/external/ipfs_datasets/ipfs_accelerate_py/ipfs_accelerate_py/utils/mistral_vibe.py": 0,
            "/home/barberb/lift_coding/external/ipfs_datasets/ipfs_datasets_py/duckdb_control/codebase_catalog.py": 0,
            "/home/barberb/lift_coding/external/ipfs_datasets/ipfs_datasets_py/duckdb_control/codebase_verification_catalog.py": 0,
            "/home/barberb/lift_coding/external/ipfs_datasets/ipfs_datasets_py/duckdb_control/codebase_verification_projection.py": 0,
            "/home/barberb/lift_coding/external/ipfs_datasets/ipfs_datasets_py/duckdb_control/codebase_verification_queries.py": 0,
            "/home/barberb/lift_coding/external/ipfs_datasets/ipfs_datasets_py/logic/backends/cvc5/__init__.py": 0,
            "/home/barberb/lift_coding/external/ipfs_datasets/ipfs_datasets_py/logic/backends/cvc5/compiler.py": 0,
            "/home/barberb/lift_coding/external/ipfs_datasets/ipfs_datasets_py/logic/backends/installers/state_model.py": 0,
            "/home/barberb/lift_coding/external/ipfs_datasets/ipfs_datasets_py/logic/backends/process.py": 0,
            "/home/barberb/lift_coding/external/ipfs_datasets/ipfs_datasets_py/logic/backends/protocol_v1_adapter.py": 0,
            "/home/barberb/lift_coding/external/ipfs_datasets/ipfs_datasets_py/logic/backends/protocol_v2.py": 0,
            "/home/barberb/lift_coding/external/ipfs_datasets/ipfs_datasets_py/logic/backends/provider.py": 0,
            "/home/barberb/lift_coding/external/ipfs_datasets/ipfs_datasets_py/logic/backends/registry.py": 0,
            "/home/barberb/lift_coding/external/ipfs_datasets/ipfs_datasets_py/logic/backends/requests_v2.py": 0,
            "/home/barberb/lift_coding/external/ipfs_datasets/ipfs_datasets_py/logic/backends/resource_admission.py": 0,
            "/home/barberb/lift_coding/external/ipfs_datasets/ipfs_datasets_py/logic/backends/results.py": 0,
            "/home/barberb/lift_coding/external/ipfs_datasets/ipfs_datasets_py/logic/backends/smt/__init__.py": 0,
            "/home/barberb/lift_coding/external/ipfs_datasets/ipfs_datasets_py/logic/backends/smt/admitted.py": 0,
            "/home/barberb/lift_coding/external/ipfs_datasets/ipfs_datasets_py/logic/backends/smt/admitted_differential.py": 0,
            "/home/barberb/lift_coding/external/ipfs_datasets/ipfs_datasets_py/logic/backends/smt/compiler.py": 0,
            "/home/barberb/lift_coding/external/ipfs_datasets/ipfs_datasets_py/logic/backends/smt/differential.py": 0,
            "/home/barberb/lift_coding/external/ipfs_datasets/ipfs_datasets_py/logic/backends/smt/execution_v2.py": 0,
            "/home/barberb/lift_coding/external/ipfs_datasets/ipfs_datasets_py/logic/backends/smt/operation_budget.py": 0,
            "/home/barberb/lift_coding/external/ipfs_datasets/ipfs_datasets_py/logic/backends/tla/compiler.py": 0,
            "/home/barberb/lift_coding/external/ipfs_datasets/ipfs_datasets_py/logic/backends/tla/execution_v2.py": 0,
            "/home/barberb/lift_coding/external/ipfs_datasets/ipfs_datasets_py/logic/backends/tla/runners.py": 0,
            "/home/barberb/lift_coding/external/ipfs_datasets/ipfs_datasets_py/logic/backends/toolchain_roles.py": 0,
            "/home/barberb/lift_coding/external/ipfs_datasets/ipfs_datasets_py/logic/backends/z3/__init__.py": 0,
            "/home/barberb/lift_coding/external/ipfs_datasets/ipfs_datasets_py/logic/backends/z3/compiler.py": 0,
            "/home/barberb/lift_coding/external/ipfs_datasets/ipfs_datasets_py/logic/common/canonical_cache_key.py": 0,
            "/home/barberb/lift_coding/external/ipfs_datasets/ipfs_datasets_py/logic/conformance/authority_audit.py": 0,
            "/home/barberb/lift_coding/external/ipfs_datasets/ipfs_datasets_py/logic/conformance/matrix.py": 0,
            "/home/barberb/lift_coding/external/ipfs_datasets/ipfs_datasets_py/logic/families/generated_catalog.py": 0,
            "/home/barberb/lift_coding/external/ipfs_datasets/ipfs_datasets_py/logic/families/models.py": 0,
            "/home/barberb/lift_coding/external/ipfs_datasets/ipfs_datasets_py/logic/families/namespaces.py": 0,
            "/home/barberb/lift_coding/external/ipfs_datasets/ipfs_datasets_py/logic/families/providers.py": 0,
            "/home/barberb/lift_coding/external/ipfs_datasets/ipfs_datasets_py/logic/families/registry.py": 0,
            "/home/barberb/lift_coding/external/ipfs_datasets/ipfs_datasets_py/logic/formalization/proposal_advisors.py": 0,
            "/home/barberb/lift_coding/external/ipfs_datasets/ipfs_datasets_py/logic/intent_ir/schema.py": 0,
            "/home/barberb/lift_coding/external/ipfs_datasets/ipfs_datasets_py/logic/ir_core/claims.py": 0,
            "/home/barberb/lift_coding/external/ipfs_datasets/ipfs_datasets_py/logic/ir_core/identity.py": 0,
            "/home/barberb/lift_coding/external/ipfs_datasets/ipfs_datasets_py/logic/ir_core/protocols.py": 0,
            "/home/barberb/lift_coding/external/ipfs_datasets/ipfs_datasets_py/logic/ir_core/provenance.py": 0,
            "/home/barberb/lift_coding/external/ipfs_datasets/ipfs_datasets_py/logic/parsers/classical_adapters.py": 0,
            "/home/barberb/lift_coding/external/ipfs_datasets/ipfs_datasets_py/logic/parsers/kernel_targets.py": 0,
            "/home/barberb/lift_coding/external/ipfs_datasets/ipfs_datasets_py/logic/parsers/smtlib.py": 0,
            "/home/barberb/lift_coding/external/ipfs_datasets/ipfs_datasets_py/logic/software_contracts/cache.py": 0,
            "/home/barberb/lift_coding/external/ipfs_datasets/ipfs_datasets_py/logic/software_contracts/codebase_applicability.py": 0,
            "/home/barberb/lift_coding/external/ipfs_datasets/ipfs_datasets_py/logic/software_contracts/codebase_integer_profile.py": 0,
            "/home/barberb/lift_coding/external/ipfs_datasets/ipfs_datasets_py/logic/software_contracts/codebase_ir.py": 0,
            "/home/barberb/lift_coding/external/ipfs_datasets/ipfs_datasets_py/logic/software_contracts/codebase_resources.py": 0,
            "/home/barberb/lift_coding/external/ipfs_datasets/ipfs_datasets_py/logic/software_contracts/codebase_smt_compat.py": 0,
            "/home/barberb/lift_coding/external/ipfs_datasets/ipfs_datasets_py/logic/software_contracts/codebase_smt_execution.py": 0,
            "/home/barberb/lift_coding/external/ipfs_datasets/ipfs_datasets_py/logic/software_contracts/codebase_smt_protocol.py": 0,
            "/home/barberb/lift_coding/external/ipfs_datasets/ipfs_datasets_py/logic/software_contracts/codebase_verification.py": 0,
            "/home/barberb/lift_coding/external/ipfs_datasets/ipfs_datasets_py/logic/software_contracts/content.py": 0,
            "/home/barberb/lift_coding/external/ipfs_datasets/ipfs_datasets_py/logic/software_contracts/duckdb_ast_store.py": 0,
            "/home/barberb/lift_coding/external/ipfs_datasets/ipfs_datasets_py/logic/software_contracts/duckdb_ingest.py": 0,
            "/home/barberb/lift_coding/external/ipfs_datasets/ipfs_datasets_py/logic/software_verification/__init__.py": 0,
            "/home/barberb/lift_coding/external/ipfs_datasets/ipfs_datasets_py/logic/software_verification/admitted_pipeline.py": 0,
            "/home/barberb/lift_coding/external/ipfs_datasets/ipfs_datasets_py/logic/software_verification/applicability.py": 0,
            "/home/barberb/lift_coding/external/ipfs_datasets/ipfs_datasets_py/logic/software_verification/concurrency.py": 0,
            "/home/barberb/lift_coding/external/ipfs_datasets/ipfs_datasets_py/logic/software_verification/contracts.py": 0,
            "/home/barberb/lift_coding/external/ipfs_datasets/ipfs_datasets_py/logic/software_verification/ir.py": 0,
            "/home/barberb/lift_coding/external/ipfs_datasets/ipfs_datasets_py/logic/software_verification/pipeline.py": 0,
            "/home/barberb/lift_coding/external/ipfs_datasets/ipfs_datasets_py/logic/software_verification/program.py": 0,
            "/home/barberb/lift_coding/external/ipfs_datasets/ipfs_datasets_py/logic/software_verification/properties.py": 0,
            "/home/barberb/lift_coding/external/ipfs_datasets/ipfs_datasets_py/logic/software_verification/receipts.py": 0,
            "/home/barberb/lift_coding/external/ipfs_datasets/ipfs_datasets_py/logic/software_verification/refinement.py": 0,
            "/home/barberb/lift_coding/external/ipfs_datasets/ipfs_datasets_py/logic/software_verification/source_adapters.py": 0,
            "/home/barberb/lift_coding/external/ipfs_datasets/ipfs_datasets_py/logic/software_verification/state.py": 0,
            "/home/barberb/lift_coding/external/ipfs_datasets/ipfs_datasets_py/logic/software_verification/transitions.py": 0,
            "/home/barberb/lift_coding/external/ipfs_datasets/ipfs_datasets_py/logic/software_verification/translations.py": 0,
            "/home/barberb/lift_coding/external/ipfs_datasets/ipfs_datasets_py/logic/software_verification/vc.py": 0,
            "/home/barberb/lift_coding/external/ipfs_datasets/ipfs_datasets_py/logic/syntax_core/contracts.py": 0,
            "/home/barberb/lift_coding/external/ipfs_datasets/ipfs_datasets_py/logic/verification_api.py": 0,
            "/home/barberb/lift_coding/external/ipfs_datasets/ipfs_datasets_py/optimizers/logic_theorem_optimizer/proof_resource_safety.py": 0,
            "/home/barberb/lift_coding/external/ipfs_datasets/ipfs_datasets_py/optimizers/logic_theorem_optimizer/resource_scheduler.py": 0,
            "/home/barberb/lift_coding/external/ipfs_datasets/tests/conformance/logic/test_authority_boundaries.py": 0,
            "/home/barberb/lift_coding/external/ipfs_datasets/tests/conformance/logic/test_classical_backend_routes.py": 0,
            "/home/barberb/lift_coding/external/ipfs_datasets/tests/conformance/logic/test_registry_closure.py": 0,
            "/home/barberb/lift_coding/external/ipfs_datasets/tests/integration/logic/backends/test_state_model_preparation.py": 0,
            "/home/barberb/lift_coding/external/ipfs_datasets/tests/integration/logic/backends/test_tla_model_checkers.py": 0,
            "/home/barberb/lift_coding/external/ipfs_datasets/tests/integration/logic/backends/test_tla_runner_resource_bounds.py": 0,
            "/home/barberb/lift_coding/external/ipfs_datasets/tests/integration/logic/backends/test_z3_cvc5_software_verification.py": 0,
            "/home/barberb/lift_coding/external/ipfs_datasets/tests/integration/logic/software_verification/test_source_adapter_snapshot_grounding.py": 0,
            "/home/barberb/lift_coding/external/ipfs_datasets/tests/integration/logic/software_verification/test_source_vc_smt_pipeline.py": 0,
            "/home/barberb/lift_coding/external/ipfs_datasets/tests/integration/logic_providers/test_smt_execution_v2.py": 0,
            "/home/barberb/lift_coding/external/ipfs_datasets/tests/integration/logic_providers/test_tla_execution_v2.py": 0,
            "/home/barberb/lift_coding/external/ipfs_datasets/tests/unit/logic/backends/test_apalache_resource_admission.py": 0,
            "/home/barberb/lift_coding/external/ipfs_datasets/tests/unit/logic/backends/test_java_probe_admission.py": 0,
            "/home/barberb/lift_coding/external/ipfs_datasets/tests/unit/logic/backends/test_protocol_v1_adapter.py": 0,
            "/home/barberb/lift_coding/external/ipfs_datasets/tests/unit/logic/backends/test_provider_protocol_v2.py": 0,
            "/home/barberb/lift_coding/external/ipfs_datasets/tests/unit/logic/backends/test_registry.py": 0,
            "/home/barberb/lift_coding/external/ipfs_datasets/tests/unit/logic/backends/test_registry_foreign_outcomes.py": 0,
            "/home/barberb/lift_coding/external/ipfs_datasets/tests/unit/logic/backends/test_resource_admission.py": 0,
            "/home/barberb/lift_coding/external/ipfs_datasets/tests/unit/logic/backends/test_smt_consumer_admission.py": 0,
            "/home/barberb/lift_coding/external/ipfs_datasets/tests/unit/logic/backends/test_smt_operation_benchmark_pool_guard.py": 0,
            "/home/barberb/lift_coding/external/ipfs_datasets/tests/unit/logic/backends/test_smt_operation_control.py": 0,
            "/home/barberb/lift_coding/external/ipfs_datasets/tests/unit/logic/backends/test_smt_resource_admission.py": 0,
            "/home/barberb/lift_coding/external/ipfs_datasets/tests/unit/logic/backends/test_smt_v2_operation_control.py": 0,
            "/home/barberb/lift_coding/external/ipfs_datasets/tests/unit/logic/backends/test_state_model_probe_admission.py": 0,
            "/home/barberb/lift_coding/external/ipfs_datasets/tests/unit/logic/backends/test_tla_artifact_payload.py": 0,
            "/home/barberb/lift_coding/external/ipfs_datasets/tests/unit/logic/backends/test_tla_operation_control.py": 0,
            "/home/barberb/lift_coding/external/ipfs_datasets/tests/unit/logic/backends/test_tla_outcome_integrity.py": 0,
            "/home/barberb/lift_coding/external/ipfs_datasets/tests/unit/logic/software_contracts/test_codebase_smt_execution.py": 0,
            "/home/barberb/lift_coding/external/ipfs_datasets/tests/unit/logic/software_contracts/test_codebase_smt_execution_receipts.py": 0,
            "/home/barberb/lift_coding/external/ipfs_datasets/tests/unit/logic/software_contracts/test_codebase_smt_protocol.py": 0,
            "/home/barberb/lift_coding/external/ipfs_datasets/tests/unit/logic/software_verification/test_bundled_program_ast_mirroring.py": 0,
            "/home/barberb/lift_coding/external/ipfs_datasets/tests/unit/logic/software_verification/test_program_ast_provider_capabilities.py": 0,
            "/home/barberb/lift_coding/external/ipfs_datasets/tests/unit/logic/software_verification/test_source_mirroring_control.py": 0,
            "/home/barberb/lift_coding/external/ipfs_datasets/tests/unit/logic/test_compositional_verification_public_api.py": 0,
            "/home/barberb/lift_coding/external/ipfs_datasets/tests/unit/logic/test_verification_api.py": 0,
            "/home/barberb/lift_coding/external/ipfs_datasets/tests/unit_tests/logic/external_provers/test_lazy_native_solver_installation.py": 0,
            "/home/barberb/lift_coding/external/ipfs_datasets/tests/unit_tests/logic/integration/test_state_model_installer_runtime.py": 0,
        },
    ),
    (
        "dict",
        {
            "/home/barberb/.local/share/ipfs_datasets_py/theorem-provers/Isabelle2025-2-linux-aarch64/Isabelle2025-2/contrib/jdk-21.0.9/arm64-linux/bin/java": 0,
            "/home/barberb/.local/share/ipfs_datasets_py/theorem-provers/apalache-0.58.3/apalache-0.58.3/bin/apalache-mc": 0,
            "/home/barberb/.local/share/ipfs_datasets_py/theorem-provers/apalache-0.58.3/apalache-0.58.3/lib/apalache.jar": 0,
            "/home/barberb/.local/share/ipfs_datasets_py/theorem-provers/bin/apalache-mc": 0,
            "/home/barberb/.local/share/ipfs_datasets_py/theorem-provers/bin/tlc": 0,
            "/home/barberb/.local/share/ipfs_datasets_py/theorem-provers/manifests/apalache.json": 0,
            "/home/barberb/.local/share/ipfs_datasets_py/theorem-provers/manifests/tlc.json": 0,
            "/home/barberb/.local/share/ipfs_datasets_py/theorem-provers/tlc/1.8.0/tla2tools.jar": 0,
            "/home/barberb/lift_coding/external/ipfs_datasets/workspace/tla-artifact-payload-qualification-20261003/native/tlc-memory-aware": 0,
        },
    ),
    (
        "dict",
        {
            "builder_sha256": 0,
            "documentation": 15,
            "native_sources": 16,
            "producer_inventories": 20,
            "retained_producer_result_sha256": 0,
            "selected_test_sources": 21,
            "selected_tools": 22,
        },
    ),
    (
        "dict",
        {
            "/home/barberb/lift_coding/external/ipfs_datasets/benchmarks/bench_tla_artifact_payload.py": 0,
            "/home/barberb/lift_coding/external/ipfs_datasets/ipfs_datasets_py/logic/backends/tla/compiler.py": 0,
            "/home/barberb/lift_coding/external/ipfs_datasets/ipfs_datasets_py/logic/backends/tla/execution_v2.py": 0,
            "/home/barberb/lift_coding/external/ipfs_datasets/ipfs_datasets_py/logic/backends/tla/runners.py": 0,
            "/home/barberb/lift_coding/external/ipfs_datasets/tests/unit/logic/backends/test_tla_artifact_payload.py": 0,
        },
    ),
    (
        "dict",
        {
            "native_runner_sha256": 0,
            "native_sources": 16,
            "retained_sources": 24,
            "review": 0,
            "scope": 0,
            "selected_regression_result_sha256": 0,
            "selected_sources": 21,
            "static_preflight_sha256": 0,
        },
    ),
    (
        "dict",
        {
            "default_integer_lower": 4,
            "default_integer_upper": 4,
            "max_actions": 4,
            "max_enum_members": 4,
            "max_integer_span": 4,
            "max_module_bytes": 4,
            "max_predicates": 4,
            "max_steps": 4,
            "max_variables": 4,
            "schema_version": 0,
        },
    ),
    ("list", 1, (0,)),
    (
        "dict",
        {
            "approximation": 0,
            "construct": 0,
            "handling": 0,
            "loss_id": 0,
            "preservation": 0,
            "projection": 0,
            "schema_version": 0,
            "severity": 0,
            "statement": 0,
        },
    ),
    ("list", 1, (28,)),
    (
        "dict",
        {
            "line_hint": 0,
            "role": 0,
            "schema_version": 0,
            "source_id": 0,
            "source_kind": 0,
            "tla_symbol": 0,
        },
    ),
    ("list", 2, (30,)),
    ("dict", {"id": 0, "version": 0}),
    (
        "dict",
        {
            "apalache_config_digest": 0,
            "apalache_config_text": 0,
            "artifact_digest": 0,
            "bounded": 2,
            "bounds": 26,
            "fairness_limitations": 27,
            "interface_version": 0,
            "liveness_properties": 7,
            "losses": 29,
            "model_digest": 0,
            "model_text": 0,
            "module_name": 0,
            "safety_properties": 27,
            "schema_version": 0,
            "source_document_id": 0,
            "source_kind": 0,
            "source_map": 31,
            "tlc_config_digest": 0,
            "tlc_config_text": 0,
            "translator": 32,
            "unbounded_proof": 2,
        },
    ),
    ("NoneType",),
    ("dict", {"max_memory_bytes": 4, "max_output_bytes": 4, "max_steps": 4, "timeout_ms": 4}),
    ("dict", {}),
    (
        "dict",
        {
            "artifact_digest": 0,
            "available": 34,
            "bounds": 35,
            "confidence_micros": 4,
            "document_digest": 0,
            "document_id": 0,
            "document_kind": 0,
            "document_present": 2,
            "fluent_text_present": 2,
            "has_fallback_output": 2,
            "has_mock_output": 2,
            "interface": 0,
            "metadata": 36,
            "mode": 0,
            "module_name": 0,
            "provider": 0,
            "request_id": 0,
            "schema_version": 0,
            "source_ref_ids": 7,
        },
    ),
    (
        "dict",
        {
            "canonical": 33,
            "compiler_bounds": 26,
            "complete_equality": 2,
            "decoded": 33,
            "native_model_config_unchanged": 2,
            "submitted": 33,
            "v2_compact_request": 37,
            "v2_decoded": 33,
            "valid": 2,
        },
    ),
    ("list", 2, (38,)),
    ("dict", {"help": 4, "model": 4, "setup": 4}),
    ("dict", {"bytes": 4, "elf_machine": 4, "sha256": 0}),
    (
        "dict",
        {
            "com/microsoft/z3/linux/aarch64/libz3.so": 41,
            "com/microsoft/z3/linux/aarch64/libz3java.so": 41,
        },
    ),
    ("dict", {"artifacts": 33}),
    (
        "dict",
        {
            "assumption_ids": 27,
            "bounds": 35,
            "claim_digest": 0,
            "claim_id": 0,
            "declaration_id": 0,
            "logic_family": 0,
            "obligation_digest": 0,
            "obligation_id": 0,
            "payload": 43,
            "query_kind": 0,
            "request_id": 0,
            "requested_backend_id": 0,
            "schema_version": 0,
        },
    ),
    ("list", 2, (44,)),
    (
        "dict",
        {
            "apalache_jar": 0,
            "apalache_java": 0,
            "apalache_launcher": 0,
            "apalache_manifest": 0,
            "apalache_payload": 0,
            "canonical_tlc_launcher_bytes_verified": 2,
            "tlc_jar": 0,
            "tlc_java": 0,
            "tlc_launcher": 0,
            "tlc_launcher_expands_to_direct_java": 2,
            "tlc_manifest": 0,
            "tlc_wrapper": 0,
            "transitive_jvm_library_tree_hashed": 2,
        },
    ),
    (
        "dict",
        {
            "/home/barberb/.local/share/ipfs_datasets_py/theorem-provers/Isabelle2025-2-linux-aarch64/Isabelle2025-2/contrib/jdk-21.0.9/arm64-linux/bin/java": 0,
            "/home/barberb/.local/share/ipfs_datasets_py/theorem-provers/apalache-0.58.3/apalache-0.58.3/bin/apalache-mc": 0,
            "/home/barberb/.local/share/ipfs_datasets_py/theorem-provers/apalache-0.58.3/apalache-0.58.3/lib/apalache.jar": 0,
            "/home/barberb/.local/share/ipfs_datasets_py/theorem-provers/bin/apalache-mc": 0,
            "/home/barberb/.local/share/ipfs_datasets_py/theorem-provers/bin/tlc": 0,
            "/home/barberb/.local/share/ipfs_datasets_py/theorem-provers/manifests/apalache.json": 0,
            "/home/barberb/.local/share/ipfs_datasets_py/theorem-provers/manifests/tlc.json": 0,
            "/home/barberb/.local/share/ipfs_datasets_py/theorem-provers/tlc/1.8.0/tla2tools.jar": 0,
            "/home/barberb/lift_coding/external/ipfs_datasets/workspace/tla-artifact-payload-qualification-20261003/benchmark-static/tlc-memory-aware": 0,
        },
    ),
    (
        "dict",
        {
            "benchmark_sha256": 0,
            "decoder_cases": 39,
            "expected_native_phases": 4,
            "expected_phase_counts": 40,
            "helper_sha256": 0,
            "native_v2_execution": 2,
            "packaged_native_entries": 42,
            "registry_discovery_loaded_delegates": 4,
            "requests": 45,
            "scope": 0,
            "selection": 46,
            "source_count": 4,
            "source_map_structural_replay_claim": 2,
            "source_pins": 16,
            "source_pins_unchanged": 2,
            "status": 0,
            "tool_files": 47,
        },
    ),
    ("list", 55, (0,)),
    (
        "dict",
        {
            "IPFS_DATASETS_AUTO_INSTALL_TEST_DEPS": 0,
            "IPFS_TEST_PROOF_REUSE_MODE": 0,
            "PYTHONPATH": 0,
        },
    ),
    (
        "dict",
        {
            "/home/barberb/lift_coding/external/ipfs_datasets/tests/conformance/logic/test_authority_boundaries.py": 0,
            "/home/barberb/lift_coding/external/ipfs_datasets/tests/conformance/logic/test_classical_backend_routes.py": 0,
            "/home/barberb/lift_coding/external/ipfs_datasets/tests/conformance/logic/test_registry_closure.py": 0,
            "/home/barberb/lift_coding/external/ipfs_datasets/tests/integration/logic/backends/test_state_model_preparation.py": 0,
            "/home/barberb/lift_coding/external/ipfs_datasets/tests/integration/logic/backends/test_tla_model_checkers.py": 0,
            "/home/barberb/lift_coding/external/ipfs_datasets/tests/integration/logic/backends/test_tla_runner_resource_bounds.py": 0,
            "/home/barberb/lift_coding/external/ipfs_datasets/tests/integration/logic/backends/test_z3_cvc5_software_verification.py": 0,
            "/home/barberb/lift_coding/external/ipfs_datasets/tests/integration/logic/software_verification/test_source_adapter_snapshot_grounding.py": 0,
            "/home/barberb/lift_coding/external/ipfs_datasets/tests/integration/logic/software_verification/test_source_vc_smt_pipeline.py": 0,
            "/home/barberb/lift_coding/external/ipfs_datasets/tests/integration/logic_providers/test_smt_execution_v2.py": 0,
            "/home/barberb/lift_coding/external/ipfs_datasets/tests/integration/logic_providers/test_tla_execution_v2.py": 0,
            "/home/barberb/lift_coding/external/ipfs_datasets/tests/unit/logic/backends/test_apalache_resource_admission.py": 0,
            "/home/barberb/lift_coding/external/ipfs_datasets/tests/unit/logic/backends/test_java_probe_admission.py": 0,
            "/home/barberb/lift_coding/external/ipfs_datasets/tests/unit/logic/backends/test_protocol_v1_adapter.py": 0,
            "/home/barberb/lift_coding/external/ipfs_datasets/tests/unit/logic/backends/test_provider_protocol_v2.py": 0,
            "/home/barberb/lift_coding/external/ipfs_datasets/tests/unit/logic/backends/test_registry.py": 0,
            "/home/barberb/lift_coding/external/ipfs_datasets/tests/unit/logic/backends/test_registry_foreign_outcomes.py": 0,
            "/home/barberb/lift_coding/external/ipfs_datasets/tests/unit/logic/backends/test_resource_admission.py": 0,
            "/home/barberb/lift_coding/external/ipfs_datasets/tests/unit/logic/backends/test_smt_consumer_admission.py": 0,
            "/home/barberb/lift_coding/external/ipfs_datasets/tests/unit/logic/backends/test_smt_operation_benchmark_pool_guard.py": 0,
            "/home/barberb/lift_coding/external/ipfs_datasets/tests/unit/logic/backends/test_smt_operation_control.py": 0,
            "/home/barberb/lift_coding/external/ipfs_datasets/tests/unit/logic/backends/test_smt_resource_admission.py": 0,
            "/home/barberb/lift_coding/external/ipfs_datasets/tests/unit/logic/backends/test_smt_v2_operation_control.py": 0,
            "/home/barberb/lift_coding/external/ipfs_datasets/tests/unit/logic/backends/test_state_model_probe_admission.py": 0,
            "/home/barberb/lift_coding/external/ipfs_datasets/tests/unit/logic/backends/test_tla_artifact_payload.py": 0,
            "/home/barberb/lift_coding/external/ipfs_datasets/tests/unit/logic/backends/test_tla_operation_control.py": 0,
            "/home/barberb/lift_coding/external/ipfs_datasets/tests/unit/logic/backends/test_tla_outcome_integrity.py": 0,
            "/home/barberb/lift_coding/external/ipfs_datasets/tests/unit/logic/software_contracts/test_codebase_smt_execution.py": 0,
            "/home/barberb/lift_coding/external/ipfs_datasets/tests/unit/logic/software_contracts/test_codebase_smt_execution_receipts.py": 0,
            "/home/barberb/lift_coding/external/ipfs_datasets/tests/unit/logic/software_contracts/test_codebase_smt_protocol.py": 0,
            "/home/barberb/lift_coding/external/ipfs_datasets/tests/unit/logic/software_verification/test_bundled_program_ast_mirroring.py": 0,
            "/home/barberb/lift_coding/external/ipfs_datasets/tests/unit/logic/software_verification/test_program_ast_provider_capabilities.py": 0,
            "/home/barberb/lift_coding/external/ipfs_datasets/tests/unit/logic/software_verification/test_source_mirroring_control.py": 0,
            "/home/barberb/lift_coding/external/ipfs_datasets/tests/unit/logic/test_compositional_verification_public_api.py": 0,
            "/home/barberb/lift_coding/external/ipfs_datasets/tests/unit/logic/test_verification_api.py": 0,
            "/home/barberb/lift_coding/external/ipfs_datasets/tests/unit_tests/logic/external_provers/test_lazy_native_solver_installation.py": 0,
            "/home/barberb/lift_coding/external/ipfs_datasets/tests/unit_tests/logic/integration/test_state_model_installer_runtime.py": 0,
        },
    ),
    (
        "dict",
        {
            "after": 21,
            "argv": 49,
            "before": 21,
            "cwd": 0,
            "env_overrides": 50,
            "returncode": 4,
            "seconds": 5,
            "suite": 0,
            "test_snapshots": 51,
        },
    ),
    ("list", 4, (0,)),
    (
        "dict",
        {
            "after": 16,
            "argv": 53,
            "before": 16,
            "cwd": 0,
            "env_overrides": 50,
            "freeze_sha256": 0,
            "returncode": 4,
            "seconds": 5,
        },
    ),
    ("dict", {"argv": 53, "benchmark_sha256": 0, "cwd": 0}),
    (
        "dict",
        {
            "apalache-environment-audit.json": 0,
            "launch-audit.json": 0,
            "lifecycle-audit.json": 0,
            "phase-budget-audit.json": 0,
            "request-audit.json": 0,
        },
    ),
    ("dict", {"elapsed_ms": 4, "output_bytes": 4, "peak_memory_bytes": 4, "steps": 4}),
    (
        "dict",
        {
            "artifact_digests": 7,
            "attempt_id": 0,
            "backend_id": 0,
            "backend_version": 0,
            "bounds": 35,
            "diagnostics": 27,
            "output_digest": 0,
            "request_digest": 0,
            "schema_version": 0,
            "status": 0,
            "usage": 57,
        },
    ),
    ("dict", {"child_process_slots": 4, "cpu_slots": 4, "memory_mb": 4}),
    ("dict", {"cpu_slots": 4, "memory_mb": 4}),
    (
        "dict",
        {
            "child_process_slots": 4,
            "cpu_slots": 4,
            "gpu_memory_mb": 34,
            "memory_mb": 4,
            "unified_memory_mb": 34,
        },
    ),
    (
        "dict",
        {
            "child_process_slots": 4,
            "cpu_slots": 4,
            "gpu_memory_mb": 34,
            "memory_mb": 4,
            "reserved_gpu_memory_mb": 4,
            "reserved_memory_mb": 4,
            "unified_memory_mb": 34,
            "usable_gpu_memory_mb": 34,
            "usable_memory_mb": 4,
        },
    ),
    (
        "dict",
        {
            "acquisitions_total": 4,
            "cancellations_total": 4,
            "recovered_leases_total": 4,
            "recoveries_total": 4,
            "releases_total": 4,
            "saturation_events_total": 4,
            "timeouts_total": 4,
        },
    ),
    (
        "dict",
        {
            "child_process_slots": 4,
            "cpu_slots": 4,
            "gpu_memory_mb": 4,
            "memory_mb": 4,
            "unified_memory_mb": 4,
        },
    ),
    (
        "dict",
        {
            "acquisitions_total": 4,
            "cancellations_total": 4,
            "timeouts_total": 4,
            "wait_count": 4,
            "wait_seconds_max": 5,
            "wait_seconds_mean": 5,
            "wait_seconds_total": 5,
        },
    ),
    ("dict", {"allocated": 64, "reservation": 60, "telemetry": 65}),
    ("dict", {"validation": 66}),
    (
        "dict",
        {
            "child_process_slots_saturated": 2,
            "cpu_saturated": 2,
            "events_total": 4,
            "gpu_memory_saturated": 2,
            "memory_saturated": 2,
            "saturated": 2,
            "unified_memory_saturated": 2,
        },
    ),
    ("dict", {"count": 4, "max": 5, "mean": 5, "p50": 5, "p95": 5, "p99": 5, "total": 5}),
    (
        "dict",
        {
            "active_child_lease_count": 4,
            "active_lease_count": 4,
            "active_root_lease_count": 4,
            "allocated": 60,
            "allocated_child_process_slots": 4,
            "allocated_gpu_memory_mb": 4,
            "allocated_unified_memory_mb": 4,
            "available": 61,
            "capacity": 62,
            "counters": 63,
            "lanes": 67,
            "proof_backoff": 36,
            "saturation": 68,
            "schema_version": 0,
            "state_path": 0,
            "wait_time_seconds": 69,
            "waiting_request_count": 4,
        },
    ),
    (
        "dict",
        {
            "at_monotonic": 5,
            "available_to_validation": 59,
            "batch": 0,
            "capacity_snapshot": 70,
            "effective_workers": 4,
            "observed_max_owned_roots": 4,
            "protected_other_lanes": 60,
            "requested_workers": 4,
            "scope": 0,
            "whole_operation_envelope": 59,
        },
    ),
    (
        "dict",
        {
            "apalache_config_digest": 0,
            "artifact_digest": 0,
            "bounded": 2,
            "bounds": 26,
            "fairness_limitations": 27,
            "interface_version": 0,
            "liveness_properties": 7,
            "losses": 29,
            "model_digest": 0,
            "module_name": 0,
            "safety_properties": 27,
            "schema_version": 0,
            "source_document_id": 0,
            "source_kind": 0,
            "source_map": 31,
            "tlc_config_digest": 0,
            "translator": 32,
            "unbounded_proof": 2,
        },
    ),
    ("list", 2, (0,)),
    ("list", 3, (0,)),
    (
        "dict",
        {
            "backend_version": 0,
            "checks_fairness": 2,
            "checks_liveness": 2,
            "checks_safety": 2,
            "executable_candidates": 73,
            "finite_trace_only": 2,
            "limitations": 74,
            "max_declared_steps": 4,
            "requires_jvm": 2,
            "schema_version": 0,
            "tool": 0,
        },
    ),
    ("list", 11, (0,)),
    (
        "dict",
        {
            "artifact_digest": 0,
            "bounded": 2,
            "capability": 75,
            "checked_liveness_properties": 7,
            "checked_safety_properties": 27,
            "command": 76,
            "configuration_digest": 0,
            "configuration_text": 0,
            "counterexample": 34,
            "elapsed_ms": 4,
            "executable": 0,
            "fairness_limitations": 53,
            "jvm_available": 2,
            "model_digest": 0,
            "output_truncated": 2,
            "reason": 0,
            "receipt_id": 0,
            "returncode": 4,
            "schema_version": 0,
            "status": 0,
            "stderr": 0,
            "stdout": 0,
            "timeout_seconds": 5,
            "tool": 0,
            "tool_version": 0,
            "unbounded_proof": 2,
        },
    ),
    ("dict", {"executable": 0, "jvm_available": 2, "tool_version": 0}),
    (
        "dict",
        {
            "artifact_digest": 0,
            "bounded": 2,
            "capability": 75,
            "checked_liveness_properties": 7,
            "checked_safety_properties": 27,
            "configuration_digest": 0,
            "fairness_limitations": 53,
            "model_digest": 0,
            "receipt_id": 0,
            "tool": 0,
            "unbounded_proof": 2,
        },
    ),
    (
        "dict",
        {
            "assumptions": 27,
            "authority": 0,
            "backend_id": 0,
            "backend_version": 0,
            "bounds": 35,
            "diagnostics": 27,
            "metadata": 78,
            "reason": 0,
            "result_id": 0,
            "result_type": 0,
            "schema_version": 0,
            "status": 0,
            "translation_ceiling": 0,
            "usage": 57,
            "witness": 79,
        },
    ),
    (
        "dict",
        {"artifacts": 72, "interface_version": 0, "receipt": 77, "request_digest": 0, "result": 80},
    ),
    (
        "dict",
        {
            "generic_attempt_status": 0,
            "generic_result_status": 0,
            "generic_theorem_authority": 2,
            "original_authority": 0,
            "original_result_status": 0,
            "payload_exact_original_result": 2,
        },
    ),
    (
        "dict",
        {
            "configuration_digest": 0,
            "evidence_digests": 7,
            "issuer": 0,
            "kind": 0,
            "method": 0,
            "schema_version": 0,
            "scope_digest": 0,
        },
    ),
    ("dict", {"adapter_return_type": 0, "result": 80, "result_authority": 0, "result_status": 0}),
    (
        "dict",
        {
            "assumption_ids": 27,
            "attempt_digest": 0,
            "authority": 83,
            "backend_id": 0,
            "backend_version": 0,
            "bounds": 35,
            "claim_digest": 0,
            "declaration_id": 0,
            "diagnostics": 27,
            "obligation_digest": 0,
            "obligation_id": 0,
            "output_digest": 0,
            "payload": 84,
            "request_digest": 0,
            "result_id": 0,
            "result_type": 0,
            "schema_version": 0,
            "status": 0,
            "usage": 57,
        },
    ),
    (
        "dict",
        {
            "aggregate_scope_owner": 0,
            "attempt": 58,
            "attempt_digest": 0,
            "case": 0,
            "complete_artifact_equal": 2,
            "decoded_artifact": 33,
            "default_lazy_factory_used": 2,
            "dispatch": 71,
            "elapsed_seconds": 5,
            "factory_restored": 2,
            "operation_timeout_ms": 4,
            "original_outcome": 81,
            "original_return_observer_restored": 2,
            "phase_count": 4,
            "projection_checks": 82,
            "raw_witness": 34,
            "request": 44,
            "request_digest": 0,
            "result": 85,
            "selected_delegate_count": 4,
            "submitted_artifact": 33,
            "valid": 2,
        },
    ),
    (
        "dict",
        {
            "raw": 0,
            "replay_notes": 27,
            "replayed": 2,
            "schema_version": 0,
            "source": 0,
            "states": 7,
        },
    ),
    (
        "dict",
        {
            "artifact_digest": 0,
            "bounded": 2,
            "capability": 75,
            "checked_liveness_properties": 7,
            "checked_safety_properties": 27,
            "command": 76,
            "configuration_digest": 0,
            "configuration_text": 0,
            "counterexample": 87,
            "elapsed_ms": 4,
            "executable": 0,
            "fairness_limitations": 53,
            "jvm_available": 2,
            "model_digest": 0,
            "output_truncated": 2,
            "reason": 0,
            "receipt_id": 0,
            "returncode": 4,
            "schema_version": 0,
            "status": 0,
            "stderr": 0,
            "stdout": 0,
            "timeout_seconds": 5,
            "tool": 0,
            "tool_version": 0,
            "unbounded_proof": 2,
        },
    ),
    (
        "dict",
        {
            "artifact_digest": 0,
            "bounded": 2,
            "capability": 75,
            "checked_liveness_properties": 7,
            "checked_safety_properties": 27,
            "configuration_digest": 0,
            "counterexample": 87,
            "fairness_limitations": 53,
            "model_digest": 0,
            "receipt_id": 0,
            "tool": 0,
            "unbounded_proof": 2,
        },
    ),
    (
        "dict",
        {
            "assumptions": 27,
            "authority": 0,
            "backend_id": 0,
            "backend_version": 0,
            "bounds": 35,
            "diagnostics": 73,
            "metadata": 78,
            "reason": 0,
            "result_id": 0,
            "result_type": 0,
            "schema_version": 0,
            "status": 0,
            "translation_ceiling": 0,
            "usage": 57,
            "witness": 89,
        },
    ),
    (
        "dict",
        {"artifacts": 72, "interface_version": 0, "receipt": 88, "request_digest": 0, "result": 90},
    ),
    ("dict", {"parsed_state_count": 4, "path": 0, "raw_state_values": 74, "scope": 0, "sha256": 0}),
    ("dict", {"adapter_return_type": 0, "result": 90, "result_authority": 0, "result_status": 0}),
    (
        "dict",
        {
            "assumption_ids": 27,
            "attempt_digest": 0,
            "authority": 83,
            "backend_id": 0,
            "backend_version": 0,
            "bounds": 35,
            "claim_digest": 0,
            "declaration_id": 0,
            "diagnostics": 27,
            "obligation_digest": 0,
            "obligation_id": 0,
            "output_digest": 0,
            "payload": 93,
            "request_digest": 0,
            "result_id": 0,
            "result_type": 0,
            "schema_version": 0,
            "status": 0,
            "usage": 57,
        },
    ),
    (
        "dict",
        {
            "aggregate_scope_owner": 0,
            "attempt": 58,
            "attempt_digest": 0,
            "case": 0,
            "complete_artifact_equal": 2,
            "decoded_artifact": 33,
            "default_lazy_factory_used": 2,
            "dispatch": 71,
            "elapsed_seconds": 5,
            "factory_restored": 2,
            "operation_timeout_ms": 4,
            "original_outcome": 91,
            "original_return_observer_restored": 2,
            "phase_count": 4,
            "projection_checks": 82,
            "raw_witness": 92,
            "request": 44,
            "request_digest": 0,
            "result": 94,
            "selected_delegate_count": 4,
            "submitted_artifact": 33,
            "valid": 2,
        },
    ),
    ("list", 2, (86, 95)),
    ("dict", {"ru_maxrss": 4, "ru_stime": 5, "ru_utime": 5}),
    ("list", 2, (71,)),
    (
        "dict",
        {
            "available_memory_mb": 4,
            "available_pid_tasks": 4,
            "cpu_slots": 4,
            "cpu_stall_percent": 5,
            "io_stall_percent": 5,
            "memory_stall_percent": 5,
            "pid_task_limit": 4,
            "total_memory_mb": 4,
        },
    ),
    (
        "dict",
        {
            "boot_id": 0,
            "host_resources": 99,
            "logical_cpus": 4,
            "pid": 4,
            "platform": 0,
            "python": 0,
            "recorded_at_utc": 0,
        },
    ),
    (
        "dict",
        {
            "aggregate_scope_owner": 0,
            "complete_serialized_artifact_preserved": 2,
            "default_registry_aggregate_budget_claim": 2,
            "factory_override": 0,
            "hard_aggregate_resource_guarantee": 2,
            "installation": 2,
            "jvm_probe_injected": 2,
            "native_transport_injected": 2,
            "native_v2_execution": 2,
            "new_proof_cache_or_replay": 2,
            "raw_counterexample_only": 2,
            "registry_route": 0,
            "source_map_structural_replay_claim": 2,
            "throughput_scaling_claim": 2,
            "tlc_execution": 2,
        },
    ),
    ("dict", {"validation": 60}),
    (
        "dict",
        {
            "lane_reservations": 102,
            "max_gpu_memory_percent": 34,
            "max_memory_percent": 34,
            "max_swap_percent": 34,
            "max_waiting_requests": 4,
            "proof_backoff_seconds": 5,
            "proof_cpu_stall_percent": 5,
            "proof_io_stall_percent": 5,
            "proof_memory_headroom_mb": 4,
            "proof_memory_stall_percent": 5,
            "proof_safety_enabled": 2,
            "require_known_gpu_for_gpu_work": 2,
            "reserved_gpu_memory_mb": 4,
            "reserved_memory_mb": 4,
            "total_child_process_slots": 4,
            "total_cpu_slots": 4,
            "total_gpu_memory_mb": 34,
            "total_memory_mb": 4,
            "total_unified_memory_mb": 34,
        },
    ),
    (
        "dict",
        {
            "active_leases": 4,
            "config": 103,
            "next_sequence": 4,
            "owned_active_leases": 4,
            "owned_waiting_requests": 4,
            "schema_version": 0,
            "waiting_requests": 4,
        },
    ),
    (
        "dict",
        {
            "config_sha256": 0,
            "mode": 0,
            "production_recovery_policy_imported": 2,
            "retained_disabled_fields": 36,
            "reviewed_external_source_sha256": 34,
        },
    ),
    (
        "dict",
        {
            "audit_sha256": 56,
            "cases": 96,
            "checks": 3,
            "child_usage": 97,
            "dispatches": 98,
            "elapsed_seconds": 5,
            "launches": 4,
            "lifecycles": 4,
            "native_lifecycles": 4,
            "packaged_native_entries": 42,
            "phase_counts": 40,
            "prelaunch_lifecycles": 4,
            "runtime": 100,
            "schema": 0,
            "scope": 101,
            "shared_after": 104,
            "shared_before": 104,
            "shared_pool_compatibility": 105,
            "source_pins_after": 16,
            "source_pins_before": 16,
            "status": 0,
            "tool_files_after": 22,
            "tool_files_before": 22,
            "tool_selection": 46,
        },
    ),
    ("dict", {"false": 33, "true": 33}),
    ("list", 10, (0,)),
    (
        "dict",
        {
            "cpu_seconds": 5,
            "enforce_file_size_limit": 2,
            "max_argument_bytes": 4,
            "max_arguments": 4,
            "max_environment_bytes": 4,
            "max_file_bytes": 4,
            "max_input_bytes": 4,
            "max_output_bytes": 4,
            "max_output_files": 4,
            "max_path_bytes": 4,
            "max_workspace_bytes": 4,
            "memory_bytes": 4,
            "resident_memory_bytes": 4,
            "termination_grace_seconds": 5,
            "timeout_seconds": 5,
        },
    ),
    (
        "dict",
        {
            "argv": 108,
            "case": 0,
            "input_bytes": 36,
            "input_sha256": 36,
            "limits": 109,
            "output_paths": 7,
        },
    ),
    ("dict", {"BoundedCounter.tla": 4, "apalache-runtime.json": 4, "apalache.cfg": 4}),
    ("dict", {"BoundedCounter.tla": 0, "apalache-runtime.json": 0, "apalache.cfg": 0}),
    (
        "dict",
        {
            "argv": 76,
            "case": 0,
            "input_bytes": 111,
            "input_sha256": 112,
            "limits": 109,
            "output_paths": 74,
        },
    ),
    (
        "dict",
        {
            "argv": 73,
            "case": 0,
            "input_bytes": 36,
            "input_sha256": 36,
            "limits": 109,
            "output_paths": 7,
        },
    ),
    ("list", 6, (110, 113, 114)),
    (
        "dict",
        {
            "at_monotonic": 5,
            "case": 0,
            "deadline": 5,
            "phase": 0,
            "remaining_seconds": 5,
            "request_timeout_seconds": 5,
        },
    ),
    ("list", 6, (116,)),
    (
        "dict",
        {
            "argv": 108,
            "input_file_count": 4,
            "java_option_environment_absent": 2,
            "max_output_bytes": 4,
            "memory_bytes": 4,
            "output_path_count": 4,
            "resident_memory_bytes": 4,
            "stdin_is_empty": 2,
            "timeout_seconds": 5,
        },
    ),
    (
        "dict",
        {
            "cancelled": 2,
            "command": 108,
            "elapsed_seconds": 5,
            "error": 0,
            "interface_version": 0,
            "output_files": 36,
            "output_truncated": 2,
            "pid": 4,
            "process_tree_terminated": 2,
            "resource_exhausted": 2,
            "returncode": 4,
            "runtime": 0,
            "stderr": 0,
            "stdout": 0,
            "termination_reason": 0,
            "timed_out": 2,
            "unavailable": 2,
            "workspace_cleaned": 2,
            "workspace_limit_exceeded": 2,
        },
    ),
    ("dict", {"case": 0, "request": 118, "result": 119, "shared_backoff_after": 36}),
    (
        "dict",
        {
            "argv": 76,
            "input_file_count": 4,
            "java_option_environment_absent": 2,
            "max_output_bytes": 4,
            "memory_bytes": 4,
            "output_path_count": 4,
            "resident_memory_bytes": 4,
            "stdin_is_empty": 2,
            "timeout_seconds": 5,
        },
    ),
    (
        "dict",
        {
            "cancelled": 2,
            "command": 76,
            "elapsed_seconds": 5,
            "error": 0,
            "interface_version": 0,
            "output_files": 36,
            "output_truncated": 2,
            "pid": 4,
            "process_tree_terminated": 2,
            "resource_exhausted": 2,
            "returncode": 4,
            "runtime": 0,
            "stderr": 0,
            "stdout": 0,
            "termination_reason": 0,
            "timed_out": 2,
            "unavailable": 2,
            "workspace_cleaned": 2,
            "workspace_limit_exceeded": 2,
        },
    ),
    ("dict", {"case": 0, "request": 121, "result": 122, "shared_backoff_after": 36}),
    (
        "dict",
        {
            "argv": 73,
            "input_file_count": 4,
            "java_option_environment_absent": 2,
            "max_output_bytes": 4,
            "memory_bytes": 4,
            "output_path_count": 4,
            "resident_memory_bytes": 4,
            "stdin_is_empty": 2,
            "timeout_seconds": 5,
        },
    ),
    (
        "dict",
        {
            "cancelled": 2,
            "command": 73,
            "elapsed_seconds": 5,
            "error": 0,
            "interface_version": 0,
            "output_files": 36,
            "output_truncated": 2,
            "pid": 4,
            "process_tree_terminated": 2,
            "resource_exhausted": 2,
            "returncode": 4,
            "runtime": 0,
            "stderr": 0,
            "stdout": 0,
            "termination_reason": 0,
            "timed_out": 2,
            "unavailable": 2,
            "workspace_cleaned": 2,
            "workspace_limit_exceeded": 2,
        },
    ),
    ("dict", {"case": 0, "request": 124, "result": 125, "shared_backoff_after": 36}),
    ("dict", {"apalache-run/violation.tla": 0}),
    (
        "dict",
        {
            "cancelled": 2,
            "command": 76,
            "elapsed_seconds": 5,
            "error": 0,
            "interface_version": 0,
            "output_files": 127,
            "output_truncated": 2,
            "pid": 4,
            "process_tree_terminated": 2,
            "resource_exhausted": 2,
            "returncode": 4,
            "runtime": 0,
            "stderr": 0,
            "stdout": 0,
            "termination_reason": 0,
            "timed_out": 2,
            "unavailable": 2,
            "workspace_cleaned": 2,
            "workspace_limit_exceeded": 2,
        },
    ),
    ("dict", {"case": 0, "request": 121, "result": 128, "shared_backoff_after": 36}),
    ("list", 6, (120, 123, 126, 129)),
    (
        "dict",
        {
            "case": 0,
            "foreign_configuration_environment_absent": 2,
            "jvm_args": 0,
            "jvm_gc_args": 0,
            "phase": 0,
            "private_home_and_tmpdir": 2,
        },
    ),
    ("list", 4, (131,)),
    ("list", 16, (0,)),
    (
        "dict",
        {
            "acquired_at": 5,
            "cancelled": 2,
            "child_process_slots": 4,
            "cpu_slots": 4,
            "expires_at": 5,
            "gpu_memory_mb": 4,
            "heartbeat_at": 5,
            "lane": 0,
            "lease_id": 0,
            "lease_key": 0,
            "memory_mb": 4,
            "owner_birth_marker": 0,
            "owner_boot_id": 0,
            "owner_pid": 4,
            "parent_lease_id": 34,
            "request_id": 0,
            "requires_gpu": 2,
            "sequence": 4,
            "unified_memory_mb": 4,
            "wait_seconds": 5,
        },
    ),
    ("list", 1, (134,)),
    (
        "dict",
        {
            "argv": 133,
            "at_monotonic": 5,
            "case": 0,
            "launch_lease_id": 0,
            "owned_leases": 135,
            "root_allocations": 59,
            "thread": 4,
            "waiting": 4,
        },
    ),
    ("list", 17, (0,)),
    (
        "dict",
        {
            "argv": 137,
            "at_monotonic": 5,
            "case": 0,
            "launch_lease_id": 0,
            "owned_leases": 135,
            "root_allocations": 59,
            "thread": 4,
            "waiting": 4,
        },
    ),
    ("list", 8, (0,)),
    (
        "dict",
        {
            "argv": 139,
            "at_monotonic": 5,
            "case": 0,
            "launch_lease_id": 0,
            "owned_leases": 135,
            "root_allocations": 59,
            "thread": 4,
            "waiting": 4,
        },
    ),
    ("list", 6, (136, 138, 140)),
    (
        "dict",
        {
            "case": 0,
            "command": 108,
            "phase": 0,
            "recorded_owned_lease_id": 0,
            "returncode": 4,
            "workspace_cleaned": 2,
        },
    ),
    (
        "dict",
        {
            "case": 0,
            "command": 76,
            "phase": 0,
            "recorded_owned_lease_id": 0,
            "returncode": 4,
            "workspace_cleaned": 2,
        },
    ),
    (
        "dict",
        {
            "case": 0,
            "command": 73,
            "phase": 0,
            "recorded_owned_lease_id": 0,
            "returncode": 4,
            "workspace_cleaned": 2,
        },
    ),
    ("list", 3, (142, 143, 144)),
    (
        "dict",
        {
            "accepted": 2,
            "accepted_case_count": 4,
            "actual_model_command_steps": 4,
            "attempt": 0,
            "benchmark_owned_operation_budget": 2,
            "cases": 7,
            "declared_artifact_steps": 4,
            "default_registry_aggregate_budget_claim": 2,
            "historical_owned_resource_drain": 2,
            "phases": 145,
            "recorded_native_phase_count": 4,
            "resource_enforcement_qualified": 2,
            "status": 0,
            "whole_attempt_failure": 0,
        },
    ),
    (
        "dict",
        {
            "attempt_digest": 0,
            "case": 0,
            "complete_recorded_payload_preserved": 2,
            "generic_attempt_status": 0,
            "generic_result_status": 0,
            "output_digest_algorithm_rederived": 2,
            "parsed_state_count": 4,
            "recorded_output_digest": 0,
            "request_digest": 0,
            "semantic_replay_qualified": 2,
            "typed_authority": 0,
            "typed_result_status": 0,
            "valid": 2,
        },
    ),
    ("list", 2, (147,)),
    ("list", 6, (142, 143, 144)),
    (
        "dict",
        {
            "accepted": 2,
            "accepted_case_count": 4,
            "actual_model_command_steps": 4,
            "attempt": 0,
            "benchmark_owned_operation_budget": 2,
            "cases": 148,
            "declared_artifact_steps": 4,
            "default_registry_aggregate_budget_claim": 2,
            "historical_owned_resource_drain": 2,
            "phases": 149,
            "recorded_native_phase_count": 4,
            "resource_enforcement_qualified": 2,
            "status": 0,
            "whole_attempt_failure": 34,
        },
    ),
    ("list", 2, (146, 150)),
    (
        "dict",
        {
            "control": 0,
            "original_selected_bodies_unchanged": 2,
            "reason": 0,
            "recorded_audit_digests_recomputed": 2,
            "refused": 2,
        },
    ),
    ("list", 20, (152,)),
    ("dict", {"path": 0, "sha256": 0, "size": 4}),
    ("dict", {"exact_output_population": 2, "raw_bodies_reread": 2, "retained_manifest": 154}),
    ("list", 7, (0,)),
    (
        "dict",
        {
            "max_aggregate_bytes": 4,
            "max_body_bytes": 4,
            "max_json_depth": 4,
            "max_json_values": 4,
            "max_manifest_bytes": 4,
            "max_report_bytes": 4,
            "max_selected_files": 4,
        },
    ),
    (
        "dict",
        {
            "accepted_native_phase_count": 4,
            "counts_additive": 2,
            "failed_native_phase_count": 4,
            "focused_test_count": 4,
            "historical_native_phase_count": 4,
            "legacy_native_tests_deselected": 4,
            "nested_preservation_bodies_independently_opened": 2,
            "new_foreign_test_count": 4,
            "producer_declared_preserved_prior_artifacts": 4,
            "producer_declared_preserved_prior_qualifications": 4,
            "production_tasks_closed": 7,
            "selected_test_count": 4,
        },
    ),
    ("dict", {"path": 0, "retained_copy": 154, "role": 0, "sha256": 0, "size": 4}),
    ("list", 20, (159,)),
    (
        "dict",
        {
            "/home/barberb/lift_coding/external/ipfs_datasets/ipfs_datasets_py/logic/backends/registry.py": 13,
            "/home/barberb/lift_coding/external/ipfs_datasets/tests/unit/logic/backends/test_apalache_resource_admission.py": 13,
        },
    ),
    (
        "dict",
        {
            "accepted_command_result_sha256": 0,
            "accepted_result_sha256": 0,
            "additional_attempted_training_epochs": 4,
            "attempts": 151,
            "checker_executions_replayed": 2,
            "controls": 153,
            "counterexample_replay_qualified": 2,
            "current_authority_claimed": 2,
            "custody": 155,
            "exact_typed_payload_preserved": 2,
            "failed_whole_attempt_preserved": 2,
            "fixture_origin": 0,
            "generic_unknown_authority_preserved": 2,
            "hard_aggregate_containment_qualified": 2,
            "historical_raw_witness_scope_preserved": 2,
            "initial_command_result_sha256": 0,
            "initial_result_sha256": 0,
            "input_files_unchanged": 2,
            "limitations": 156,
            "limits": 157,
            "live_eligibility_qualified": 2,
            "manifest_sha256": 0,
            "model_check_authority_qualified": 2,
            "model_quality_qualified": 2,
            "native_execution_performed": 2,
            "native_export_adoption_qualified": 2,
            "original_request_custody_qualified": 2,
            "output_digest_algorithm_rederived": 2,
            "owner_database_opened": 2,
            "owner_sources_imported": 2,
            "process_origin_attested": 2,
            "production_acceptance_qualified": 2,
            "production_tasks_closed": 7,
            "profile_keys_read": 2,
            "proof_authority_qualified": 2,
            "qualification": 158,
            "qualification_sha256": 0,
            "qualified": 2,
            "recorded_phase_bindings_reconciled": 2,
            "registry_native_success_qualified": 2,
            "resource_enforcement_qualified": 2,
            "retained_foreign_outcome_custody_conformance": 2,
            "runtime_fact_count": 4,
            "schema": 0,
            "selected_file_count": 4,
            "selected_files": 160,
            "selected_input_bytes": 4,
            "signature_authentication_performed": 2,
            "source_evolution_metadata": 161,
            "source_evolution_sha256": 0,
            "source_execution_replayed": 2,
            "status": 0,
            "tasks_omitted_count": 4,
            "throughput_improvement_qualified": 2,
            "training_executed": 2,
            "whole_install_cancellation_qualified": 2,
            "workflow": 0,
        },
    ),
]

COMPILE_BOUNDS = {
    "default_integer_lower": 0,
    "default_integer_upper": 7,
    "max_actions": 128,
    "max_enum_members": 64,
    "max_integer_span": 256,
    "max_module_bytes": 1048576,
    "max_predicates": 256,
    "max_steps": 3,
    "max_variables": 64,
    "schema_version": "tla-compile-bounds/v1",
}

ARTIFACT_METADATA = {
    "false": {
        "bounded": True,
        "bounds": {
            "default_integer_lower": 0,
            "default_integer_upper": 7,
            "max_actions": 128,
            "max_enum_members": 64,
            "max_integer_span": 256,
            "max_module_bytes": 1048576,
            "max_predicates": 256,
            "max_steps": 3,
            "max_variables": 64,
            "schema_version": "tla-compile-bounds/v1",
        },
        "fairness_limitations": [
            "The three-transition fixture establishes no liveness or fairness result."
        ],
        "interface_version": "TLABackend@1",
        "liveness_properties": [],
        "losses": [
            {
                "approximation": "none",
                "construct": "finite_trace_coverage",
                "handling": "abstracted",
                "loss_id": "loss:counter:finite-trace",
                "preservation": "bounded",
                "projection": "state",
                "schema_version": "tla-projection-loss/v1",
                "severity": "disclosed",
                "statement": "This fixture checks three transitions; unbounded trace "
                "behavior is outside its scope.",
            }
        ],
        "module_name": "BoundedCounter",
        "safety_properties": ["Safety"],
        "schema_version": "tla-generated-artifact/v1",
        "source_document_id": "benchmark:tla-artifact-payload:false",
        "source_kind": "state_transition",
        "source_map": [
            {
                "line_hint": "VARIABLE n",
                "role": "variable",
                "schema_version": "tla-source-map/v1",
                "source_id": "variable:counter:n",
                "source_kind": "state_variable",
                "tla_symbol": "n",
            },
            {
                "line_hint": "Safety == n \\in 0..1",
                "role": "safety",
                "schema_version": "tla-source-map/v1",
                "source_id": "property:counter:safety",
                "source_kind": "state_predicate",
                "tla_symbol": "Safety",
            },
        ],
        "translator": {"id": "state-transition-ir-to-tla", "version": "tla-compiler/v1"},
        "unbounded_proof": False,
    },
    "true": {
        "bounded": True,
        "bounds": {
            "default_integer_lower": 0,
            "default_integer_upper": 7,
            "max_actions": 128,
            "max_enum_members": 64,
            "max_integer_span": 256,
            "max_module_bytes": 1048576,
            "max_predicates": 256,
            "max_steps": 3,
            "max_variables": 64,
            "schema_version": "tla-compile-bounds/v1",
        },
        "fairness_limitations": [
            "The three-transition fixture establishes no liveness or fairness result."
        ],
        "interface_version": "TLABackend@1",
        "liveness_properties": [],
        "losses": [
            {
                "approximation": "none",
                "construct": "finite_trace_coverage",
                "handling": "abstracted",
                "loss_id": "loss:counter:finite-trace",
                "preservation": "bounded",
                "projection": "state",
                "schema_version": "tla-projection-loss/v1",
                "severity": "disclosed",
                "statement": "This fixture checks three transitions; unbounded trace "
                "behavior is outside its scope.",
            }
        ],
        "module_name": "BoundedCounter",
        "safety_properties": ["Safety"],
        "schema_version": "tla-generated-artifact/v1",
        "source_document_id": "benchmark:tla-artifact-payload:true",
        "source_kind": "state_transition",
        "source_map": [
            {
                "line_hint": "VARIABLE n",
                "role": "variable",
                "schema_version": "tla-source-map/v1",
                "source_id": "variable:counter:n",
                "source_kind": "state_variable",
                "tla_symbol": "n",
            },
            {
                "line_hint": "Safety == n \\in 0..3",
                "role": "safety",
                "schema_version": "tla-source-map/v1",
                "source_id": "property:counter:safety",
                "source_kind": "state_predicate",
                "tla_symbol": "Safety",
            },
        ],
        "translator": {"id": "state-transition-ir-to-tla", "version": "tla-compiler/v1"},
        "unbounded_proof": False,
    },
}


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
        self.raw, self.total, self.identities = {}, 0, {}

    def take(self, path, cap=MAX_FILE):
        path = Path(path)
        if path in self.raw:
            need(len(self.raw[path]) <= cap, "reused body cap")
            return self.raw[path]
        need(len(self.raw) < MAX_FILES, "selected file population cap")
        raw = bounded(path, cap)
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
        for path, raw in self.raw.items():
            info = path.stat(follow_symlinks=False)
            need(
                self.identities[path]
                == (info.st_dev, info.st_ino, info.st_size, info.st_mtime_ns, info.st_ctime_ns),
                "late selected physical identity changed",
            )
            need(bounded(path, len(raw)) == raw, "late selected raw body changed")


def phase(argv):
    need(type(argv) is list and argv and all(type(x) is str for x in argv), "recorded argv")
    if argv[-1] == "-version":
        return "setup"
    if "check" in argv:
        return "model"
    if "version" in argv:
        return "help"
    raise Refusal("unselected phase")


def bounds_record(value):
    closed(
        value, ("max_memory_bytes", "max_output_bytes", "max_steps", "timeout_ms"), "request bounds"
    )
    need(all(integer(x, 1) for x in value.values()), "typed positive request bounds")


def usage_record(value):
    closed(value, ("elapsed_ms", "output_bytes", "peak_memory_bytes", "steps"), "usage")
    need(all(integer(x) for x in value.values()), "typed usage quantities")


def reconcile_case(case, fixture, model_life):
    closed(case, CASE_FIELDS, "foreign case")
    valid = case["valid"]
    need(
        type(valid) is bool and case["case"] == CASE_IDS[0 if valid else 1],
        "ordered selected case identity",
    )
    for key in (
        "default_lazy_factory_used",
        "factory_restored",
        "original_return_observer_restored",
    ):
        need(case[key] is True, "historical factory/observer restoration")
    need(
        case["aggregate_scope_owner"] == "benchmark"
        and integer(case["operation_timeout_ms"])
        and case["operation_timeout_ms"] == 30000,
        "benchmark-owned historical operation scope",
    )
    need(
        integer(case["selected_delegate_count"])
        and case["selected_delegate_count"] == 1
        and integer(case["phase_count"])
        and case["phase_count"] == 3
        and number(case["elapsed_seconds"]),
        "historical case counts",
    )
    need(case["complete_artifact_equal"] is True, "declared full artifact equality")
    need(
        same(case["submitted_artifact"], fixture) and same(case["decoded_artifact"], fixture),
        "independent complete serialized artifact equality",
    )
    request, attempt, result, original = (
        case[x] for x in ("request", "attempt", "result", "original_outcome")
    )
    closed(request, REQUEST_FIELDS, "protocol request")
    closed(attempt, ATTEMPT_FIELDS, "protocol attempt")
    closed(result, GENERIC_FIELDS, "generic result")
    closed(
        original,
        ("artifacts", "interface_version", "receipt", "request_digest", "result"),
        "captured original outcome",
    )
    need(
        request["schema_version"] == "proof-backend-request/v1"
        and request["requested_backend_id"] == "apalache"
        and request["logic_family"] == "state_transition"
        and request["query_kind"] == "satisfiability",
        "selected protocol route",
    )
    bounds_record(request["bounds"])
    request_digest, attempt_digest = sha(canonical(request)), sha(canonical(attempt))
    need(
        request_digest
        == case["request_digest"]
        == original["request_digest"]
        == attempt["request_digest"]
        == result["request_digest"],
        "independent request digest binding",
    )
    need(
        attempt_digest == case["attempt_digest"] == result["attempt_digest"],
        "independent attempt digest binding",
    )
    need(
        attempt["schema_version"] == "proof-backend-attempt/v1"
        and attempt["status"] == "succeeded"
        and result["schema_version"] == "bounded-result/v1"
        and result["status"] == "unknown",
        "generic non-conclusive conversion",
    )
    need(
        attempt["backend_id"] == result["backend_id"] == "apalache"
        and attempt["backend_version"] == result["backend_version"] == "matrix-declared/v1",
        "generic backend declaration",
    )
    need(
        attempt["attempt_id"] == "attempt:apalache:" + request_digest[:24]
        and result["result_id"] == "result:apalache:" + request_digest[:24],
        "generic deterministic recorded IDs",
    )
    need(
        same(request["bounds"], attempt["bounds"]) and same(request["bounds"], result["bounds"]),
        "request/attempt/result exact bounds",
    )
    for key in (
        "claim_digest",
        "declaration_id",
        "obligation_digest",
        "obligation_id",
        "assumption_ids",
    ):
        need(same(request[key], result[key]), "generic original request field binding")
    need(result["result_type"] == request["query_kind"], "generic result type binding")
    for value in (
        request["claim_digest"],
        request["obligation_digest"],
        attempt["output_digest"],
        result["output_digest"],
    ):
        need(digest(value), "recorded protocol digest form")
    need(
        attempt["output_digest"] == result["output_digest"],
        "recorded generic output digest preserved",
    )
    need(attempt["artifact_digests"] == [], "no generic evidence artifacts minted")
    need(
        attempt["diagnostics"] == result["diagnostics"] == [DIAGNOSTIC],
        "mandatory no-upgrade diagnostic",
    )
    usage_record(attempt["usage"])
    usage_record(result["usage"])
    need(
        same(attempt["usage"], result["usage"])
        and all(integer(v) and v == 0 for v in result["usage"].values()),
        "generic usage not inferred from native execution",
    )
    authority = result["authority"]
    closed(
        authority,
        (
            "configuration_digest",
            "evidence_digests",
            "issuer",
            "kind",
            "method",
            "schema_version",
            "scope_digest",
        ),
        "generic declared authority",
    )
    need(
        authority["schema_version"] == "result-authority/v1"
        and authority["issuer"] == "apalache"
        and authority["kind"] == "satisfiability"
        and authority["method"] == "proof-backend-adapter/v1",
        "generic authority declaration profile",
    )
    need(
        authority["scope_digest"] == request_digest
        and digest(authority["configuration_digest"])
        and authority["evidence_digests"] == [],
        "generic authority scope remains descriptive",
    )
    closed(request["payload"], ("artifacts",), "request payload")
    need(same(request["payload"]["artifacts"], fixture), "request equals selected full fixture")
    artifact_record(fixture, 3)
    artifact_without_text = {
        k: v
        for k, v in fixture.items()
        if k not in ("model_text", "apalache_config_text", "tlc_config_text")
    }
    need(
        same(original["artifacts"], artifact_without_text)
        and original["interface_version"] == "ApalacheBackend@1",
        "original outcome exact nontext artifact",
    )
    typed, receipt, payload = original["result"], original["receipt"], result["payload"]
    closed(
        payload,
        ("adapter_return_type", "result", "result_authority", "result_status"),
        "foreign descriptive payload",
    )
    closed(typed, TYPED_FIELDS, "original typed result")
    closed(receipt, RECEIPT_FIELDS, "original bounded receipt")
    need(
        same(payload["result"], typed) and payload["adapter_return_type"] == "ModelCheckOutcome",
        "exact original typed result preservation",
    )
    expected_status = "satisfied" if valid else "violated"
    need(
        typed["status"] == payload["result_status"] == expected_status
        and typed["authority"] == payload["result_authority"] == "model_check",
        "typed status and bounded authority preserved",
    )
    need(
        typed["schema_version"] == "typed-backend-result/v1"
        and typed["result_type"] == "model_check"
        and typed["translation_ceiling"] == "bounded",
        "typed evidence ceiling",
    )
    need(
        typed["backend_id"] == "apalache"
        and typed["backend_version"] == "ApalacheBackend@1"
        and same(typed["bounds"], request["bounds"])
        and same(typed["assumptions"], request["assumption_ids"]),
        "typed original protocol binding",
    )
    need(typed["result_id"] == result["result_id"], "typed result identity preserved")
    usage_record(typed["usage"])
    need(
        receipt["schema_version"] == "tla-model-check-receipt/v1"
        and receipt["tool"] == "apalache"
        and receipt["bounded"] is True
        and receipt["unbounded_proof"] is False,
        "bounded receipt ceiling",
    )
    witness = typed["witness"]
    fields = (
        "artifact_digest",
        "bounded",
        "capability",
        "checked_liveness_properties",
        "checked_safety_properties",
        "configuration_digest",
        "fairness_limitations",
        "model_digest",
        "receipt_id",
        "tool",
        "unbounded_proof",
    ) + (() if valid else ("counterexample",))
    closed(witness, fields, "typed witness")
    need(all(same(witness[k], receipt[k]) for k in fields), "exact original witness receipt fields")
    need(
        receipt["artifact_digest"] == fixture["artifact_digest"] == request["obligation_digest"]
        and receipt["model_digest"] == fixture["model_digest"] == request["claim_digest"]
        and receipt["configuration_digest"] == fixture["apalache_config_digest"],
        "artifact/request/receipt digests",
    )
    need(
        receipt["configuration_text"] == fixture["apalache_config_text"]
        and receipt["command"] == model_life["command"],
        "configuration and actual recorded command",
    )
    need(
        receipt["stdout"] == model_life["stdout"]
        and receipt["stderr"] == model_life["stderr"]
        and receipt["returncode"] == model_life["returncode"]
        and integer(receipt["returncode"]),
        "original native output preserved",
    )
    need(
        receipt["status"] == ("passed" if valid else "counterexample")
        and receipt["returncode"] == (0 if valid else 12),
        "original tool classification",
    )
    need(
        receipt["jvm_available"] is True
        and receipt["output_truncated"] is False
        and number(receipt["timeout_seconds"], 0.001)
        and integer(receipt["elapsed_ms"]),
        "original receipt measurements",
    )
    capability = receipt["capability"]
    closed(
        capability,
        (
            "backend_version",
            "checks_fairness",
            "checks_liveness",
            "checks_safety",
            "executable_candidates",
            "finite_trace_only",
            "limitations",
            "max_declared_steps",
            "requires_jvm",
            "schema_version",
            "tool",
        ),
        "historical capability",
    )
    need(
        capability["checks_safety"] is True
        and capability["checks_liveness"] is False
        and capability["checks_fairness"] is False
        and capability["finite_trace_only"] is True
        and capability["requires_jvm"] is True,
        "retained Apalache capability limitations",
    )
    need(
        capability["schema_version"] == "tla-model-checker-capability/v1"
        and capability["backend_version"] == "ApalacheBackend@1"
        and capability["tool"] == "apalache"
        and integer(capability["max_declared_steps"])
        and capability["max_declared_steps"] == 200,
        "historical declared capability identity",
    )
    need(
        capability["executable_candidates"] == ["apalache-mc", "apalache"]
        and type(capability["limitations"]) is list
        and capability["limitations"],
        "declared tool limitations",
    )
    metadata = typed["metadata"]
    closed(metadata, ("executable", "jvm_available", "tool_version"), "typed tool metadata")
    need(
        metadata["jvm_available"] is True
        and metadata["executable"] == receipt["executable"]
        and metadata["tool_version"] == receipt["tool_version"],
        "original tool metadata bound to receipt",
    )
    need(
        receipt["checked_safety_properties"] == ["Safety"]
        and receipt["checked_liveness_properties"] == [],
        "no checked liveness",
    )
    need(
        type(receipt["fairness_limitations"]) is list and receipt["fairness_limitations"],
        "explicit bounded limitations",
    )
    projection = {
        "generic_attempt_status": "succeeded",
        "generic_result_status": "unknown",
        "generic_theorem_authority": False,
        "original_authority": "model_check",
        "original_result_status": expected_status,
        "payload_exact_original_result": True,
    }
    need(same(case["projection_checks"], projection), "independent projection checks")
    if valid:
        need(
            receipt["counterexample"] is None and case["raw_witness"] is None,
            "valid case no counterexample",
        )
    else:
        ce = receipt["counterexample"]
        closed(
            ce,
            ("raw", "replay_notes", "replayed", "schema_version", "source", "states"),
            "historical raw counterexample",
        )
        need(
            ce["schema_version"] == "tla-counterexample/v1"
            and ce["source"] == "checker_counterexample_file"
            and ce["states"] == []
            and ce["replayed"] is True
            and ce["replay_notes"] == [TRACE_NOTE],
            "historical zero-state legacy replay observation",
        )
        need(
            type(ce["raw"]) is str
            and model_life["output_files"].get("apalache-run/violation.tla") == ce["raw"],
            "raw counterexample exact retained output",
        )
        values = ["0", "1", "2"]
        need(
            sha(ce["raw"].encode())
            == "31e06e2ad86080012a129a630636da3770d753b52bc8de7761f047bf6190f333",
            "fixed historical raw trace bytes, not structural interpretation",
        )
        need(
            same(
                case["raw_witness"],
                {
                    "parsed_state_count": 0,
                    "path": "apalache-run/violation.tla",
                    "raw_state_values": values,
                    "scope": "Original raw Apalache file retained; no structural replay attestation",
                    "sha256": sha(ce["raw"].encode()),
                },
            ),
            "raw-only witness descriptor",
        )
        need(TRACE_NOTE in typed["diagnostics"], "raw-only diagnostic retained")
    return {
        "case": case["case"],
        "valid": valid,
        "generic_attempt_status": "succeeded",
        "generic_result_status": "unknown",
        "typed_result_status": expected_status,
        "typed_authority": "model_check",
        "request_digest": request_digest,
        "attempt_digest": attempt_digest,
        "recorded_output_digest": result["output_digest"],
        "output_digest_algorithm_rederived": False,
        "parsed_state_count": 0,
        "semantic_replay_qualified": False,
        "complete_recorded_payload_preserved": True,
    }


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


def artifact_record(value, expected_steps):
    closed(value, ARTIFACT_FIELDS, "serialized artifact")
    need(expected_steps == 3, "only the selected three-step artifact profile")
    valid = value["source_document_id"].removeprefix("benchmark:tla-artifact-payload:")
    need(valid in ("true", "false"), "artifact selected document identity")
    projection = {
        k: v
        for k, v in value.items()
        if k
        not in (
            "artifact_digest",
            "model_digest",
            "model_text",
            "tlc_config_digest",
            "tlc_config_text",
            "apalache_config_digest",
            "apalache_config_text",
        )
    }
    need(same(projection, ARTIFACT_METADATA[valid]), "complete bounded artifact metadata")
    need(same(value["bounds"], COMPILE_BOUNDS), "exact serialized compile bounds")
    for prefix in ("model", "tlc_config", "apalache_config"):
        text, expected = value[prefix + "_text"], value[prefix + "_digest"]
        need(type(text) is str and digest(expected), "typed serialized text/digest")
        need(sha(text.encode("utf-8")) == expected, "independent serialized text digest")
    model = (
        "---- MODULE BoundedCounter ----\nEXTENDS Integers\nVARIABLE\n"
        "    \\* @type: Int;\n    n\nInit == n = 0\n"
        "Next == n' = IF n < 3 THEN n + 1 ELSE n\nSpec == Init /\\ [][Next]_n\n"
        + "Safety == n \\in 0.."
        + ("3" if valid == "true" else "1")
        + "\n====\n"
    )
    need(value["model_text"] == model, "selected literal model bytes, not semantic truth")
    need(
        value["apalache_config_text"] == "INIT Init\nNEXT Next\nINVARIANT Safety\n",
        "selected invariant configuration",
    )
    need(
        value["tlc_config_text"] == "SPECIFICATION Spec\nINVARIANT Safety\nCHECK_DEADLOCK FALSE\n",
        "selected TLC metadata, no TLC execution",
    )
    nontext = {
        k: v
        for k, v in value.items()
        if k not in ("artifact_digest", "model_text", "tlc_config_text", "apalache_config_text")
    }
    need(
        digest(value["artifact_digest"]) and sha(canonical(nontext)) == value["artifact_digest"],
        "independent canonical artifact identity",
    )
    return {
        "artifact_digest": value["artifact_digest"],
        "model_digest": value["model_digest"],
        "apalache_config_digest": value["apalache_config_digest"],
        "tlc_config_digest": value["tlc_config_digest"],
        "compile_max_steps": 3,
        "source_map_count": 2,
        "loss_disclosure_count": 1,
        "source_map": value["source_map"],
        "losses": value["losses"],
        "fairness_limitations": value["fairness_limitations"],
        "safety_properties": value["safety_properties"],
        "liveness_properties": [],
        "bounded": True,
        "unbounded_proof": False,
        "translator": value["translator"],
        "source_document_id": value["source_document_id"],
        "source_kind": value["source_kind"],
        "schema_version": value["schema_version"],
        "interface_version": value["interface_version"],
        "module_name": value["module_name"],
        "bounds": value["bounds"],
        "text_digests_rederived": True,
        "canonical_artifact_identity_rederived": True,
        "source_map_semantic_truth_qualified": False,
    }


def reconcile_native(docs):
    result, command = docs["native_result"], docs["native_command_result"]
    need(
        result["schema"] == "tla-artifact-payload-benchmark@1" and result["status"] == "passed",
        "selected historical native result",
    )
    need(all(v is True for v in result["checks"].values()), "historical native producer checks")
    need(
        all(
            integer(result[k]) and result[k] == 6
            for k in ("launches", "lifecycles", "native_lifecycles")
        ),
        "six historical native phases",
    )
    need(
        result["prelaunch_lifecycles"] == 0
        and same(result["phase_counts"], {"help": 2, "model": 2, "setup": 2}),
        "exact historical phase populations",
    )
    scope = result["scope"]
    need(
        scope["aggregate_scope_owner"] == "benchmark"
        and scope["registry_route"] == "default_backend_registry/LazyMatrixProofBackend"
        and scope["complete_serialized_artifact_preserved"] is True
        and scope["raw_counterexample_only"] is True,
        "retained benchmark scope",
    )
    need(
        all(
            scope[k] is False
            for k in scope
            if k
            not in (
                "aggregate_scope_owner",
                "registry_route",
                "factory_override",
                "complete_serialized_artifact_preserved",
                "raw_counterexample_only",
            )
        ),
        "no producer scope promotion",
    )
    need(command["returncode"] == 0 and number(command["seconds"]), "native wrapper success")
    need(
        same(command["before"], command["after"])
        and same(result["source_pins_before"], result["source_pins_after"])
        and same(result["tool_files_before"], result["tool_files_after"]),
        "historical source/tool declarations stable",
    )
    need(
        same(result["shared_before"]["config"], result["shared_after"]["config"])
        and result["shared_after"]["owned_active_leases"] == 0
        and result["shared_after"]["owned_waiting_requests"] == 0,
        "historical owned drain",
    )
    requests, launches, lives, budgets, environments = (
        docs[role]
        for role in (
            "native_request_audit",
            "native_launch_audit",
            "native_lifecycle_audit",
            "native_phase_budget_audit",
            "native_apalache_environment_audit",
        )
    )
    need(
        all(len(rows) == 6 for rows in (requests, launches, lives, budgets))
        and len(environments) == 4,
        "complete six phase bodies",
    )
    phases, models, jvm_index = [], {}, 0
    for index, (request, launch, life, budget) in enumerate(
        zip(requests, launches, lives, budgets, strict=True)
    ):
        ph, case = ("setup", "model", "help")[index % 3], CASE_IDS[index // 3]
        label = case + ":constructor" if ph == "setup" else case
        native, limits = life["result"], request["limits"]
        argv = request["argv"]
        need(
            request["case"] == launch["case"] == life["case"] == label
            and budget["case"] == case
            and budget["phase"] == ph
            and phase(argv) == ph,
            "ordered historical case/phase ledger",
        )
        need(
            same(argv, native["command"])
            and same(argv, life["request"]["argv"])
            and launch["argv"][-len(argv) :] == argv
            and launch["argv"][0] == "/usr/bin/prlimit"
            and launch["argv"][-len(argv) - 1] == "--",
            "logical/native/actual argv binding",
        )
        need(
            native["returncode"] == (12 if ph == "model" and index // 3 == 1 else 0)
            and native["workspace_cleaned"] is True
            and all(native[k] is False for k in LIFE_FALSE),
            "historical phase result/cleanup",
        )
        need(
            native["interface_version"] == "bounded-tool-runner/v1"
            and native["termination_reason"]
            == ("nonzero_exit" if ph == "model" and index // 3 == 1 else "completed")
            and native["error"] == ""
            and integer(native["pid"], 1)
            and number(native["elapsed_seconds"]),
            "typed historical lifecycle",
        )
        need(
            life["request"]["stdin_is_empty"] is True
            and life["request"]["java_option_environment_absent"] is True,
            "recorded isolated Java request",
        )
        need(
            all(
                number(budget[k], 0.001)
                for k in (
                    "deadline",
                    "at_monotonic",
                    "remaining_seconds",
                    "request_timeout_seconds",
                )
            ),
            "typed benchmark deadline declarations",
        )
        need(
            abs(budget["deadline"] - budget["at_monotonic"] - budget["remaining_seconds"]) < 0.02
            and budget["request_timeout_seconds"] <= budget["remaining_seconds"] + 0.02,
            "bounded benchmark-owned phase declarations",
        )
        need(
            budget["deadline"] == budgets[index // 3 * 3]["deadline"]
            and budget["remaining_seconds"] <= 30.0,
            "single benchmark-owned thirty-second deadline",
        )
        need(
            limits["timeout_seconds"]
            == budget["request_timeout_seconds"]
            == life["request"]["timeout_seconds"],
            "phase timeout propagation",
        )
        need(len(launch["owned_leases"]) == 1, "one historical owned root")
        lease = launch["owned_leases"][0]
        allocation = {
            "cpu_slots": 1,
            "memory_mb": 256 if ph == "setup" else 512,
            "child_process_slots": 1 if ph == "setup" else 3,
        }
        need(
            lease["lease_id"] == launch["launch_lease_id"]
            and lease["cancelled"] is False
            and lease["parent_lease_id"] is None
            and same(launch["root_allocations"], allocation)
            and all(lease[k] == v for k, v in allocation.items()),
            "historical owned lease bindings",
        )
        if ph == "model":
            fixture = docs["native_fixtures"]["true" if index // 3 == 0 else "false"]
            expected_argv = [
                result["tool_selection"]["apalache_launcher"],
                "check",
                "--config-file=apalache-runtime.json",
                "--run-dir=apalache-run",
                "--out-dir=apalache-out",
                "--smt-solver=z3",
                "--config=apalache.cfg",
                "--length=3",
                "--inv=Safety",
                "--no-deadlock",
                "BoundedCounter.tla",
            ]
            need(argv == expected_argv, "actual three-step artifact command")
            inputs = {
                "BoundedCounter.tla": fixture["model_text"].encode(),
                "apalache.cfg": fixture["apalache_config_text"].encode(),
                "apalache-runtime.json": b"{}\n",
            }
            need(
                same(request["input_sha256"], {k: sha(v) for k, v in inputs.items()})
                and same(request["input_bytes"], {k: len(v) for k, v in inputs.items()}),
                "exact native artifact text/configuration inputs",
            )
            need(
                request["output_paths"]
                == [
                    "apalache-run/counterexample.tla",
                    "apalache-run/violation.tla",
                    "apalache-run/example.tla",
                ],
                "declared bounded counterexample outputs",
            )
            models[case] = native
        else:
            need(
                request["input_sha256"] == request["input_bytes"] == {}
                and request["output_paths"] == [],
                "no undeclared setup/help inputs",
            )
            if ph == "setup":
                need(argv[0] == result["tool_selection"]["apalache_java"], "recorded selected Java")
            else:
                need(
                    argv == [result["tool_selection"]["apalache_launcher"], "version"],
                    "recorded selected help command",
                )
        if ph != "setup":
            env = environments[jvm_index]
            jvm_index += 1
            need(
                env["case"] == case
                and env["phase"] == ph
                and env["foreign_configuration_environment_absent"] is True
                and env["private_home_and_tmpdir"] is True
                and "-Xmx256m" in env["jvm_args"].split()
                and "-XX:ActiveProcessorCount=1" in env["jvm_args"].split()
                and env["jvm_gc_args"] == "-XX:+UseSerialGC",
                "recorded private JVM environment",
            )
        phases.append(
            {
                "case": case,
                "phase": ph,
                "command": argv,
                "recorded_owned_lease_id": lease["lease_id"],
                "returncode": native["returncode"],
                "workspace_cleaned": True,
                "benchmark_owned_deadline": budget["deadline"],
                "request_timeout_seconds": budget["request_timeout_seconds"],
            }
        )
    need([c["case"] for c in result["cases"]] == list(CASE_IDS), "two ordered artifact cases")
    cases = [
        reconcile_case(c, docs["native_fixtures"]["true" if i == 0 else "false"], models[c["case"]])
        for i, c in enumerate(result["cases"])
    ]
    for index, case in enumerate(result["cases"]):
        need(
            same(case["dispatch"], result["dispatches"][index]), "case dispatch metadata preserved"
        )
        need(
            case["dispatch"]["batch"] == case["case"]
            and case["dispatch"]["effective_workers"] == 1
            and same(
                case["dispatch"]["whole_operation_envelope"],
                {"child_process_slots": 3, "cpu_slots": 1, "memory_mb": 512},
            ),
            "recorded serial advisory dispatch",
        )
    return {
        "status": "passed",
        "accepted": True,
        "accepted_case_count": 2,
        "recorded_native_phase_count": 6,
        "phases": phases,
        "cases": cases,
        "declared_artifact_steps": 3,
        "actual_model_command_steps": 3,
        "benchmark_owned_operation_budget": True,
        "operation_timeout_ms": 30000,
        "default_registry_aggregate_budget_claim": False,
        "historical_owned_resource_drain": True,
        "resource_enforcement_qualified": False,
    }


LEAF_BINDINGS = {
    "source_evolution": "source-evolution.json",
    "source_snapshot": "source-snapshot.json",
    "execution_freeze": "execution-freeze.json",
    "benchmark_preflight": "benchmark-preflight.json",
    "joined_selected_result": "joined-selected.result.json",
    "native_command_result": "native-command-result.json",
    "native_command": "native/command.json",
    "native_result": "native/result.json",
    "native_fixtures": "native/fixtures.json",
    "native_request_audit": "native/request-audit.json",
    "native_phase_budget_audit": "native/phase-budget-audit.json",
    "native_lifecycle_audit": "native/lifecycle-audit.json",
    "native_apalache_environment_audit": "native/apalache-environment-audit.json",
    "native_launch_audit": "native/launch-audit.json",
}
HISTORICAL_REFERENCE_SHA256 = "f8cfa4853b2a69d227782cb6efaa67913fd260e1c2b01d565a8d94be096ec073"


def reconcile(docs, pins):
    need(set(docs) == set(pins) == set(ROLES), "exact selected metadata roles")
    for role in ROLES:
        profile_shape(docs[role], METADATA_SHAPES[role], role)
    q = docs["qualification"]
    need(
        q["schema"] == "tla-artifact-payload-qualification@1"
        and q["status"] == "passed_partial_scope",
        "historical artifact qualification",
    )
    for key, expected in (
        ("selected_tests", 2015),
        ("focused_tests", 531),
        ("new_artifact_tests", 101),
        ("native_phases", 6),
        ("native_success_cases", 2),
        ("deselected_legacy_native_tests", 15),
    ):
        need(integer(q[key]) and q[key] == expected, "separate producer qualification counts")
    need(
        q["test_counts_summed"] is False
        and q["new_cache_replay"] is False
        and q["new_codebase_smt_execution"] is False
        and q["production_tasks_closed"] == [],
        "partial scope; producer counts overlap",
    )
    need(all(v is True for v in q["checks"].values()), "historical qualification checks")
    need(
        len(q["selected_test_cases"]) == len(set(q["selected_test_cases"])) == 2015,
        "distinct historical selected test identities",
    )
    need(
        same(
            q["preservation"],
            {
                "existing_test_files_changed": 0,
                "historical_hash_aliases_added": False,
                "prior_artifacts": 1420,
                "prior_qualifications": 17,
                "production_files_changed": 3,
            },
        ),
        "producer declared preservation, no nested body audit",
    )
    for ident, suite, count in (
        ("focused-initial", "focused", 531),
        ("joined-selected", "joined", 2015),
    ):
        attempt = q["test_attempts"][ident]
        need(
            attempt["accepted"] is True
            and attempt["sources_stable"] is True
            and attempt["returncode"] == 0
            and attempt["suite"] == suite
            and same(attempt["counts"], {"passed": count})
            and number(attempt["seconds"]),
            "separate accepted test attempts",
        )
    for role, leaf in LEAF_BINDINGS.items():
        need(
            q["artifact_sha256"][leaf] == pins[role], "qualification selected raw binding: " + role
        )
    need(
        pins["historical_foreign_outcome_reference"] == HISTORICAL_REFERENCE_SHA256,
        "immutable historical reference selected independently",
    )
    native = docs["native_result"]
    for role in (
        "native_request_audit",
        "native_phase_budget_audit",
        "native_lifecycle_audit",
        "native_apalache_environment_audit",
        "native_launch_audit",
    ):
        need(
            native["audit_sha256"][Path(LEAF_BINDINGS[role]).name] == pins[role],
            "native selected audit raw binding",
        )
    preflight, freeze, snapshot = (
        docs[x] for x in ("benchmark_preflight", "execution_freeze", "source_snapshot")
    )
    need(
        preflight["status"] == "passed"
        and preflight["native_v2_execution"] is False
        and preflight["source_map_structural_replay_claim"] is False
        and preflight["registry_discovery_loaded_delegates"] == 0
        and preflight["source_pins_unchanged"] is True
        and preflight["source_count"] == 84
        and preflight["expected_native_phases"] == 6
        and same(preflight["expected_phase_counts"], native["phase_counts"]),
        "static-only decoder preflight",
    )
    need(
        freeze["selected_regression_result_sha256"] == pins["joined_selected_result"]
        and freeze["static_preflight_sha256"] == pins["benchmark_preflight"]
        and docs["native_command_result"]["freeze_sha256"] == pins["execution_freeze"],
        "frozen test/preflight/native wrapper joins",
    )
    need(
        same(freeze["native_sources"], snapshot["native_sources"])
        and same(freeze["selected_sources"], snapshot["selected_test_sources"])
        and same(snapshot["native_sources"], native["source_pins_before"])
        and same(snapshot["native_sources"], preflight["source_pins"])
        and same(snapshot["native_sources"], docs["native_command_result"]["before"])
        and same(snapshot["selected_tools"], native["tool_files_before"])
        and same(
            {
                k: v
                for k, v in snapshot["selected_tools"].items()
                if k != native["tool_selection"]["tlc_wrapper"]
            },
            {
                k: v
                for k, v in preflight["tool_files"].items()
                if k != preflight["selection"]["tlc_wrapper"]
            },
        )
        and snapshot["selected_tools"][native["tool_selection"]["tlc_wrapper"]]
        == preflight["tool_files"][preflight["selection"]["tlc_wrapper"]],
        "selected source/tool metadata joins",
    )
    joined = docs["joined_selected_result"]
    need(
        joined["returncode"] == 0
        and same(joined["before"], joined["after"])
        and same(joined["before"], snapshot["selected_test_sources"]),
        "selected joined test source metadata",
    )
    need(
        same(
            {k: v for k, v in native["tool_selection"].items() if k != "tlc_wrapper"},
            {k: v for k, v in preflight["selection"].items() if k != "tlc_wrapper"},
        )
        and same(native["packaged_native_entries"], preflight["packaged_native_entries"]),
        "native selection metadata only",
    )
    command = docs["native_command"]
    need(
        command["argv"] == docs["native_command_result"]["argv"]
        and command["cwd"] == docs["native_command_result"]["cwd"]
        and command["benchmark_sha256"] == preflight["benchmark_sha256"],
        "native wrapper metadata binding",
    )
    evolution = docs["source_evolution"]
    need(len(evolution) == 3, "three declared production source changes")
    for path, row in evolution.items():
        need(
            row["kind"] == "production"
            and all(digest(row[k]) for k in ("before_sha256", "after_sha256", "diff_sha256")),
            "declared source evolution digests",
        )
        need(
            snapshot["selected_test_sources"][path] == row["after_sha256"]
            and q["artifact_sha256"][row["diff"]] == row["diff_sha256"],
            "source evolution metadata joins",
        )
    for map_name in ("native_sources", "selected_test_sources", "selected_tools", "documentation"):
        need(
            all(digest(x) for x in snapshot[map_name].values()),
            "typed source/tool/document pin declarations",
        )
    artifacts, decoder_summaries = [], []
    for index, valid in enumerate(("true", "false")):
        fixture = docs["native_fixtures"][valid]
        artifacts.append({"case": CASE_IDS[index], **artifact_record(fixture, 3)})
        decoder = preflight["decoder_cases"][index]
        need(
            decoder["valid"] is (valid == "true")
            and decoder["complete_equality"] is True
            and decoder["native_model_config_unchanged"] is True,
            "static equality declarations",
        )
        for key in ("canonical", "submitted", "decoded", "v2_decoded"):
            need(same(decoder[key], fixture), "independent canonical/submitted/decoded/V2 equality")
        defaults = {**COMPILE_BOUNDS, "max_steps": 64}
        need(same(decoder["compiler_bounds"], defaults), "default64 distinct from artifact3")
        compact = decoder["v2_compact_request"]
        expected = {
            "artifact_digest": fixture["artifact_digest"],
            "available": None,
            "bounds": {
                "max_memory_bytes": 536870912,
                "max_output_bytes": 65536,
                "max_steps": 100000,
                "timeout_ms": 30000,
            },
            "confidence_micros": 0,
            "document_digest": "",
            "document_id": "",
            "document_kind": "",
            "document_present": False,
            "fluent_text_present": False,
            "has_fallback_output": False,
            "has_mock_output": False,
            "interface": "StateExecutionRequest@2",
            "metadata": {},
            "mode": "engine",
            "module_name": "BoundedCounter",
            "provider": "apalache",
            "request_id": "static:artifact:" + valid,
            "schema_version": "state-execution-request/v2",
            "source_ref_ids": [],
        }
        need(same(compact, expected), "exact static compact V2 projection, no native V2")
        need(
            same(preflight["requests"][index], native["cases"][index]["request"]),
            "static/full native request preservation",
        )
        decoder_summaries.append(
            {
                "case": CASE_IDS[index],
                "compiler_default_max_steps": 64,
                "serialized_artifact_max_steps": 3,
                "canonical_submitted_decoded_v2_equal": True,
                "v2_compact_request": compact,
                "native_v2_execution": False,
            }
        )
    retained = docs["historical_foreign_outcome_reference"]
    need(
        retained["schema"] == "codebase-ir-foreign-outcome-controls@1"
        and retained["status"] == "passed"
        and retained["generic_unknown_authority_preserved"] is True
        and retained["current_authority_claimed"] is False
        and retained["counterexample_replay_qualified"] is False,
        "historical foreign reference remains bounded/inert",
    )
    need(
        len(retained["attempts"]) == 2
        and retained["attempts"][0]["accepted"] is False
        and retained["attempts"][0]["declared_artifact_steps"] == 3
        and retained["attempts"][0]["actual_model_command_steps"] == 64
        and retained["attempts"][0]["recorded_native_phase_count"] == 3
        and retained["attempts"][1]["accepted"] is True
        and retained["attempts"][1]["declared_artifact_steps"] == 64
        and retained["attempts"][1]["recorded_native_phase_count"] == 6,
        "earlier failed3-to64 and accepted64 preserved as separate reference",
    )
    return {
        "artifacts": artifacts,
        "decoder_cases": decoder_summaries,
        "native_attempt": reconcile_native(docs),
        "qualification": {
            "selected_test_count": 2015,
            "focused_test_count": 531,
            "new_artifact_test_count": 101,
            "counts_additive": False,
            "legacy_native_tests_deselected": 15,
            "accepted_native_phase_count": 6,
            "producer_declared_prior_artifact_count": 1420,
            "producer_declared_prior_qualification_count": 17,
            "nested_preservation_bodies_independently_opened": False,
            "test_attempts": q["test_attempts"],
            "production_tasks_closed": [],
        },
        "source_evolution_metadata": evolution,
        "source_snapshot_metadata_counts": {
            "native_sources": 84,
            "selected_test_sources": 162,
            "selected_tools": 9,
            "documentation": 7,
            "producer_verification": 27,
            "producer_applicability": 29,
        },
        "historical_foreign_reference": {
            "reference_only": True,
            "nested_selected_bodies_opened": False,
            "initial_failed": {
                "accepted": False,
                "declared_artifact_steps": 3,
                "actual_model_command_steps": 64,
                "native_phase_count": 3,
            },
            "accepted": {
                "accepted": True,
                "declared_artifact_steps": 64,
                "actual_model_command_steps": 64,
                "native_phase_count": 6,
            },
            "phase_counts_added_to_artifact_increment": False,
        },
    }


CONTROL_FAULTS = (
    ("generic positive conclusion", "native_result", ("cases", 0, "result", "status"), "proved"),
    (
        "typed theorem promotion",
        "native_result",
        ("cases", 0, "original_outcome", "result", "authority"),
        "proof",
    ),
    (
        "typed unbounded ceiling",
        "native_result",
        ("cases", 1, "original_outcome", "result", "translation_ceiling"),
        "unbounded",
    ),
    ("no-upgrade diagnostic removed", "native_result", ("cases", 0, "attempt", "diagnostics"), []),
    (
        "typed payload altered",
        "native_result",
        ("cases", 0, "result", "payload", "result", "reason"),
        "forged",
    ),
    ("request digest forged", "native_result", ("cases", 0, "request_digest"), "0" * 64),
    ("attempt digest forged", "native_result", ("cases", 1, "attempt_digest"), "0" * 64),
    ("canonical artifact digest forged", "native_fixtures", ("true", "artifact_digest"), "0" * 64),
    ("model text digest forged", "native_fixtures", ("false", "model_digest"), "0" * 64),
    ("compile bound widened", "native_fixtures", ("true", "bounds", "max_steps"), 64),
    ("compile bound boolean", "native_fixtures", ("true", "bounds", "max_steps"), True),
    ("source map removed", "native_fixtures", ("false", "source_map"), []),
    ("loss disclosure removed", "native_fixtures", ("true", "losses"), []),
    ("fairness limitation removed", "native_fixtures", ("false", "fairness_limitations"), []),
    (
        "decoded record lost metadata",
        "native_result",
        ("cases", 0, "decoded_artifact", "source_map"),
        [],
    ),
    (
        "default64 conflated with artifact3",
        "benchmark_preflight",
        ("decoder_cases", 1, "compiler_bounds", "max_steps"),
        3,
    ),
    ("native V2 scope promotion", "benchmark_preflight", ("native_v2_execution",), True),
    (
        "structural replay scope promotion",
        "native_result",
        ("scope", "source_map_structural_replay_claim"),
        True,
    ),
    (
        "production budget promotion",
        "native_result",
        ("scope", "default_registry_aggregate_budget_claim"),
        True,
    ),
    (
        "raw parsed states invented",
        "native_result",
        ("cases", 1, "original_outcome", "receipt", "counterexample", "states"),
        [{"n": 2}],
    ),
    ("phase ownership altered", "native_launch_audit", (1, "launch_lease_id"), "forged"),
    ("phase deadline exceeded", "native_phase_budget_audit", (4, "request_timeout_seconds"), 99.0),
    ("artifact command rebound to64", "native_request_audit", (1, "argv", 7), "--length=64"),
    (
        "setup environment unsanitized",
        "native_lifecycle_audit",
        (0, "request", "java_option_environment_absent"),
        False,
    ),
    (
        "original model returncode forged",
        "native_result",
        ("cases", 1, "original_outcome", "receipt", "returncode"),
        0,
    ),
    ("overlapping tests summed", "qualification", ("test_counts_summed",), True),
    (
        "source evolution promoted",
        "source_evolution",
        (
            "/home/barberb/lift_coding/external/ipfs_datasets/ipfs_datasets_py/logic/backends/tla/compiler.py",
            "kind",
        ),
        "proved",
    ),
)


def repaired_pins(docs):
    """Repair raw descriptor joins for negative controls, then run semantic checks."""
    pins = {r: sha(canonical(docs[r])) for r in ROLES}
    pins["historical_foreign_outcome_reference"] = HISTORICAL_REFERENCE_SHA256
    for role in (
        "native_request_audit",
        "native_phase_budget_audit",
        "native_lifecycle_audit",
        "native_apalache_environment_audit",
        "native_launch_audit",
    ):
        docs["native_result"]["audit_sha256"][Path(LEAF_BINDINGS[role]).name] = pins[role]
    pins["native_result"] = sha(canonical(docs["native_result"]))
    docs["execution_freeze"]["selected_regression_result_sha256"] = pins["joined_selected_result"]
    docs["execution_freeze"]["static_preflight_sha256"] = pins["benchmark_preflight"]
    pins["execution_freeze"] = sha(canonical(docs["execution_freeze"]))
    docs["native_command_result"]["freeze_sha256"] = pins["execution_freeze"]
    pins["native_command_result"] = sha(canonical(docs["native_command_result"]))
    for role, leaf in LEAF_BINDINGS.items():
        docs["qualification"]["artifact_sha256"][leaf] = pins[role]
    pins["qualification"] = sha(canonical(docs["qualification"]))
    return pins


def mutation_controls(docs):
    positive = copy.deepcopy(docs)
    reconcile(positive, repaired_pins(positive))
    rows = []
    for label, role, path, forged in CONTROL_FAULTS:
        changed = copy.deepcopy(docs)
        target = changed[role]
        for key in path[:-1]:
            target = target[key]
        target[path[-1]] = copy.deepcopy(forged)
        repaired = repaired_pins(changed)
        try:
            reconcile(changed, repaired)
        except Refusal as exc:
            rows.append(
                {
                    "control": label,
                    "status": "refused",
                    "reason": str(exc),
                    "descriptor_bindings_repaired": True,
                }
            )
        else:
            raise Refusal("repaired forgery accepted: " + label)
    return {
        "positive_repaired_projection_passed": True,
        "negative_control_count": len(rows),
        "all_repaired_forgeries_refused": True,
        "negative_controls": rows,
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
    docs, pins, selections, identities = {}, {}, [], set()
    for role, row in zip(ROLES, manifest["selected_files"], strict=True):
        closed(row, ("role", "path", "sha256", "size_bytes"), "selected descriptor")
        need(
            row["role"] == role
            and type(row["path"]) is str
            and digest(row["sha256"])
            and integer(row["size_bytes"], 1, MAX_FILE),
            "typed ordered selected descriptor",
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
        docs[role], pins[role] = document(raw), sha(raw)
        selections.append(dict(row))
    need(
        not os.path.lexists(output) and output.parent.resolve(strict=True) == output.parent,
        "fresh output under canonical parent",
    )
    need(
        not any(
            output == p.parent or output.is_relative_to(p.parent) or p.is_relative_to(output)
            for p in capture.raw
        ),
        "output separated from selected input directories",
    )
    capture.stable()
    summary = reconcile(docs, pins)
    controls = mutation_controls(docs)
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
        relative = f"retained/{index:02d}-{row['role']}.json"
        path = output / relative
        publish(path, capture.raw[Path(row["path"])])
        need(
            capture.take(path) == capture.raw[Path(row["path"])],
            "published retained bytes unchanged",
        )
        row["retained_copy"] = {
            "path": str(path),
            "sha256": row["sha256"],
            "size_bytes": row["size_bytes"],
        }
        expected.add(relative)
    report = {
        "schema": REPORT_SCHEMA,
        "workflow": "artifact_payload_controls",
        "status": "passed",
        "qualified": True,
        "fixture_origin": "retained_serialized_tla_artifact_payload_metadata",
        "manifest_sha256": sha(manifest_raw),
        **{k: True for k in TRUE},
        **{k: False for k in FALSE},
        **{k: 0 for k in ZERO},
        **{role + "_sha256": pins[role] for role in ROLES},
        "selected_file_count": 16,
        "selected_input_bytes": sum(x["size_bytes"] for x in selections),
        "selected_files": selections,
        **summary,
        "controls": controls,
        "production_tasks_closed": [],
        "custody": {
            "retained_manifest": {
                "path": str(local_manifest),
                "sha256": sha(manifest_raw),
                "size_bytes": len(manifest_raw),
            },
            "raw_bodies_reread": True,
            "exact_output_population": True,
            "original_metadata_body_count": 16,
            "retained_metadata_body_count": 16,
            "output_regular_file_count": 18,
            "output_directory_count": 1,
            "closing_raw_body_count": 35,
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
            "Selected raw metadata bytes only; no owner program, parser, native checker, database or key is opened.",
            "Source-map and loss metadata equality establishes custody, not source semantics or translation correctness.",
            "Three-step artifact bounds bind this later retained native command; compiler default64 remains a separate declaration.",
            "Controlled static V2 equality preserves a supplied digest; neither native V2 nor missing-digest legacy fallback is qualified.",
            "Generic UNKNOWN preserves original bounded model_check satisfied/violated payload without authority upgrade; output digests are bound, not rederived.",
            "Raw State0/1/2 historical bytes, empty parsed states and replayed=True remain inert observations, without structural or semantic replay.",
            "Earlier failed3-to64 and accepted64 attempts are a fixed historical reference, with no phase or test count added to this increment.",
            "The artifact benchmark supplied30-second operation budgets; production-created default registry deadlines are outside this workflow.",
            "Producer source, tool, test and preservation inventories are declarations only; nested owner/artifact bodies are not followed.",
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
