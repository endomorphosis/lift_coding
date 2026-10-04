#!/usr/bin/env python3
"""Run the independent CodebaseIR lanes from a private implementation snapshot."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import re
import signal
import stat
import subprocess
import sys
import tempfile
import time
from datetime import UTC, datetime
from pathlib import Path

LANES = ("acceptance", "corpus_audit", "release_audit")
MAX_REPORT_BYTES = 16 * 1024 * 1024
ISOLATED_WORKFLOWS = {
    "advisory_evidence": {
        "script": "acceptance/codebase_ir_advisory_evidence.py",
        "report": "advisory_evidence.json",
        "schema": "codebase-ir-advisory-retained-audit@1",
        "false_flags": ("full_join_qualified", "signature_authentication_performed",
                        "git_object_verification_performed", "owner_database_opened", "profile_keys_read"),
        "summary_fields": ("returned_epochs", "unknown_epoch_attempts", "failed_attempt_returned_epochs",
                           "cost_accounting", "bound_stage_facts", "controls_count", "controls_refused",
                           "full_join_qualified", "signature_authentication_performed", "git_object_verification_performed",
                           "read_file_count", "read_bytes"),
    },
    "final_evaluation": {
        "script": "corpus_audit/codebase_ir_final_evaluation.py",
        "report": "final_evaluation.json",
        "schema": "codebase-ir-final-evaluation@1",
        "false_flags": ("model_selection_performed", "promotion_performed", "independence_verified",
                        "producer_authentication_verified", "numerical_provenance_verified",
                        "learned_weight_dependence_verified", "native_decoder_compatibility_verified",
                        "candidate_model_qualified", "teacher_semantics_certified", "native_closure_certified"),
        "true_flags": ("unknown_pretraining_exposure", "raw_outputs_retained_unmodified"),
        "relative_inputs": True,
        "summary_fields": ("protocol_id", "prediction_origin", "case_count", "supported_case_count",
                           "unsupported_case_count", "source_unit_count", "prediction_count", "scores",
                           "prediction_coverage", "finding_count", "split_audit_status", "split_issue_count",
                           "final_exposure_observed"),
    },
    "release_matrix": {
        "script": "release_audit/release_matrix.py",
        "report": "release_matrix.json",
        "schema": "codebase-ir-release-matrix@1",
        "false_flags": ("production_acceptance_requalified",),
        "summary_fields": ("repositories", "declared_counts", "reconstructed_claim_counts",
                           "declared_summary_matches", "criterion_source", "evidence_dispositions",
                           "source_dispositions", "snapshot_identity_stable", "portability", "bounds"),
    },
    "frozen_auxiliary_evidence": {
        "script": "acceptance/codebase_ir_frozen_auxiliary.py",
        "report": "frozen_auxiliary_evidence.json",
        "schema": "codebase-ir-frozen-auxiliary-retained-audit@1",
        "false_flags": ("full_join_qualified", "signature_authentication_performed",
                        "owner_database_opened", "profile_keys_read", "numerical_state_replayed",
                        "worker_receipt_authenticated", "worker_protocol_output_digest_rederived"),
        "true_flags": ("frozen_auxiliary_artifact_bodies_verified",),
        "zero_fields": ("additional_attempted_training_epochs",),
        "summary_fields": ("selected_auxiliary_body_count", "selected_frozen_context_count", "controls_count",
                           "controls_refused", "read_file_count", "read_bytes", "selections",
                           "additional_attempted_training_epochs", "frozen_auxiliary_artifact_bodies_verified",
                           "full_join_qualified", "numerical_state_replayed"),
    },
    "final_input_lock": {
        "script": "corpus_audit/codebase_ir_final_lock.py",
        "report": "final_lock_report.json",
        "schema": "codebase-ir-final-input-lock-report@1",
        "false_flags": ("model_selection_performed", "promotion_performed", "independence_verified",
                        "producer_authentication_verified", "numerical_provenance_verified",
                        "learned_weight_dependence_verified", "native_decoder_compatibility_verified",
                        "candidate_model_qualified", "teacher_semantics_certified", "native_closure_certified",
                        "prediction_bodies_read"),
        "true_flags": ("unknown_pretraining_exposure",),
        "relative_inputs": True,
        "summary_fields": ("locked_identity_sha256", "lock_sha256", "protocol_id", "source_unit_count",
                           "case_count", "source_file_count", "input_bytes", "prediction_bodies_read"),
    },
    "portable_release_review": {
        "script": "release_audit/portable_review.py",
        "report": "portable_review.json",
        "schema": "codebase-ir-portable-release-review-verification@1",
        "manifest_binding_field": "bundle_manifest_sha256",
        "false_flags": ("production_acceptance_requalified", "git_executable_invoked", "original_paths_read",
                        "runtime_environment_qualified", "runtime_dependency_closure_qualified"),
        "relative_inputs": True,
        "command_mode": "portable_verify",
        "manifest_filename": "bundle_manifest.json",
        "summary_fields": ("declared_counts", "evidence_dispositions", "source_dispositions",
                           "object_count", "file_count", "bytes", "portable_scope_complete", "omissions",
                           "git_executable_invoked", "original_paths_read"),
    },
}
ISOLATED_WORKFLOWS["locked_final_evaluation"] = {
    **ISOLATED_WORKFLOWS["final_evaluation"],
    "script": "corpus_audit/codebase_ir_locked_final_evaluation.py",
    "binding_fields": ("lock_sha256",),
    "true_flags": (*ISOLATED_WORKFLOWS["final_evaluation"]["true_flags"], "lock_enforced"),
    "summary_fields": (*ISOLATED_WORKFLOWS["final_evaluation"]["summary_fields"],
                       "lock_sha256", "lock_enforced", "locked_identity_sha256"),
}
ISOLATED_WORKFLOWS["worker_protocol_evidence"] = {
    "script": "acceptance/codebase_ir_worker_protocol.py",
    "report": "worker_protocol_evidence.json",
    "schema": "codebase-ir-worker-protocol-retained-audit@1",
    "false_flags": ("full_join_qualified", "signature_authentication_performed",
                    "owner_database_opened", "profile_keys_read", "numerical_state_replayed",
                    "worker_receipt_authenticated", "worker_protocol_input_digest_rederived",
                    "original_worker_output_envelopes_retained"),
    "true_flags": ("worker_protocol_output_digest_rederived", "frozen_auxiliary_artifact_bodies_verified"),
    "zero_fields": ("additional_attempted_training_epochs",),
    "binding_fields": ("protocol_worker_source_sha256",),
    "manifest_binding_paths": {"protocol_worker_source_sha256": ("protocol_worker_source", "sha256")},
    "summary_fields": ("selected_frozen_context_count", "rederived_output_digest_count",
                       "distinct_rederived_output_digest_count", "unrederived_input_digest_count",
                       "reconstructed_output_bytes", "read_file_count", "read_bytes", "controls_count",
                       "controls_refused", "prior_frozen_manifest_sha256", "prior_frozen_report_sha256",
                       "protocol_worker_source_sha256", "worker_protocol_output_digest_rederived"),
}
ISOLATED_WORKFLOWS["paired_final_evaluation"] = {
    "script": "corpus_audit/codebase_ir_paired_final_evaluation.py",
    "report": "paired_final_evaluation.json",
    "schema": "codebase-ir-paired-final-evaluation@1",
    # Preserve the original input directory used by its output-scope preflight.
    "relative_inputs": True,
    "false_flags": (*ISOLATED_WORKFLOWS["final_evaluation"]["false_flags"],
                    "learned_quality_improvement_verified", "independent_samples_established",
                    "paired_records_are_independent_samples"),
    "true_flags": ("lock_enforced", "source_reports_independently_rederived", "raw_outputs_retained_unmodified",
                   "unknown_pretraining_exposure"),
    "binding_fields": ("lock_sha256",),
    "manifest_binding_paths": {"lock_sha256": ("lock", "sha256")},
    "summary_fields": ("lock_sha256", "locked_identity_sha256", "protocol_id", "case_count", "row_count",
                       "paired_record_count", "before_prediction_count", "after_prediction_count",
                       "changed_output_counts", "missing_before_prediction_ids", "missing_after_prediction_ids",
                       "record_metric_transitions", "case_mode_populations", "unique_case_summaries",
                       "prediction_origins", "source_report_sha256", "source_manifest_sha256"),
}
ISOLATED_WORKFLOWS["portable_release_archive"] = {
    "script": "release_audit/portable_archive.py",
    "report": "portable_archive.json",
    "schema": "codebase-ir-portable-release-archive-verification@1",
    "command_mode": "archive_verify",
    "false_flags": (*ISOLATED_WORKFLOWS["portable_release_review"]["false_flags"], "network_access_performed"),
    "true_flags": ("archive_roundtrip_verified", "portable_scope_complete"),
    "binding_fields": ("archive_sha256", "bundle_manifest_sha256"),
    "manifest_binding_paths": {"archive_sha256": ("archive", "sha256"),
                               "bundle_manifest_sha256": ("bundle_manifest_sha256",)},
    "summary_fields": ("archive_sha256", "bundle_manifest_sha256", "archive_bytes", "file_count",
                       "directory_count", "object_count", "bundle_bytes", "source_dispositions",
                       "evidence_dispositions", "restored_verification", "archive_roundtrip_verified"),
}
ISOLATED_WORKFLOWS["inventory_query_controls"] = {
    "script": "acceptance/inventory_query_controls/receiver.py",
    "report": "inventory_query_controls.json",
    "schema": "codebase-ir-inventory-query-controls-report@1",
    "false_flags": ("owner_database_opened", "profile_keys_read", "production_acceptance_claimed",
                    "native_export_adoption_qualified", "signature_authentication_performed",
                    "numerical_state_replayed"),
    "true_flags": ("authored_receiver_conformance",),
    "zero_fields": ("runtime_fact_count", "tasks_omitted_count", "additional_attempted_training_epochs"),
    "binding_fields": ("fixture_sha256",),
    "manifest_binding_paths": {"fixture_sha256": ("fixture", "sha256")},
    "summary_fields": ("fixture_sha256", "fixture_origin", "inventory_unit_count", "retained_source_count",
                       "inferred_unit_count", "deferred_unit_count", "opaque_unit_count", "query_case_count",
                       "complete_query_case_count", "partial_query_case_count", "empty_budget_query_case_count",
                       "retained_page_count", "ambiguous_member_count", "mutation_control_count",
                       "input_file_count", "input_bytes", "runtime_fact_count", "tasks_omitted_count",
                       "native_export_adoption_qualified"),
}
ISOLATED_WORKFLOWS["released_evidence_children"] = {
    "script": "release_audit/evidence_children.py",
    "report": "evidence_children.json",
    "schema": "codebase-ir-released-evidence-children-audit@1",
    "relative_inputs": True,
    "false_flags": ("production_acceptance_requalified", "producer_signatures_authenticated",
                    "checker_executions_replayed", "numerical_outputs_replayed",
                    "runtime_dependency_closure_qualified", "runtime_environment_qualified",
                    "transitive_child_expansion_performed"),
    "true_flags": ("child_evidence_custody_inventory_produced", "git_object_verification_performed"),
    "binding_fields": ("ledger_sha256",),
    "manifest_binding_paths": {"ledger_sha256": ("ledger", "sha256")},
    "summary_fields": ("ledger_sha256", "repositories", "manifest_count", "declared_child_count",
                       "verified_child_count", "unique_child_body_count", "declared_child_bytes",
                       "manifest_dispositions", "child_dispositions", "all_selected_children_verified",
                       "retained_after", "expansion_policy", "bounds"),
}
ISOLATED_WORKFLOWS["contrast_final_input_lock"] = {
    **ISOLATED_WORKFLOWS["final_input_lock"],
}
ISOLATED_WORKFLOWS["native_source384_diagnostics"] = {
    "script": "corpus_audit/codebase_ir_native_source384_diagnostics.py",
    "report": "native_source384_diagnostics.json",
    "schema": "codebase-ir-native-source384-diagnostics@1",
    "relative_inputs": True,
    "false_flags": ("model_selection_performed", "promotion_performed", "candidate_model_qualified",
                    "producer_authentication_verified", "numerical_provenance_verified",
                    "source_semantics_verified", "source_derived_accuracy_available",
                    "heldout_independence_verified", "learned_weight_dependence_verified",
                    "git_object_custody_verified", "preconstraint_raw_output_available",
                    "checker_execution_replayed", "source_bytes_available"),
    "true_flags": ("native_outputs_retained_unmodified", "source_label_baseline_separate",
                   "selection_complete_for_declared_four_roles", "unknown_pretraining_exposure"),
    "binding_fields": ("public_manifest_sha256",),
    "manifest_binding_paths": {"public_manifest_sha256": ("public_manifest", "sha256")},
    "summary_fields": ("public_manifest_sha256", "release_provenance_claim", "row_counts", "record_count",
                       "complete_three_role_record_count", "codec_counts", "mode_summaries",
                       "source_bytes_available", "source_bytes_disposition", "row_pairing_policy",
                       "source_only_handoff",
                       "source_label_baseline_separate", "preconstraint_raw_output_available",
                       "recorded_qualification", "unselected_public_children", "input_bytes", "limits"),
}
ISOLATED_WORKFLOWS["native_source_comparison"] = {
    "script": "corpus_audit/codebase_ir_native_source_comparison.py",
    "report": "native_source_comparison.json",
    "schema": "codebase-ir-native-source-comparison@1",
    "relative_inputs": True,
    "false_flags": ("model_selection_performed", "promotion_performed", "candidate_model_qualified",
                    "producer_authentication_verified", "numerical_provenance_verified", "source_semantics_verified",
                    "source_runtime_equivalence_verified", "heldout_independence_verified", "independent_samples_established",
                    "learned_weight_dependence_verified", "learned_quality_improvement_verified",
                    "preconstraint_raw_output_available", "source_head_authority_verified", "model_head_state_validated",
                    "native_execution_admission_qualified"),
    "true_flags": ("source_structural_comparison_available", "source_labels_rederived", "source_only_byte_bindings_verified",
                   "raw_native_outputs_retained_unmodified", "native_source_diagnostics_independently_rederived",
                   "source_label_baseline_separate", "unknown_pretraining_exposure"),
    "binding_fields": ("diagnostics_input_sha256", "diagnostics_report_sha256", "source_replay_sha256",
                       "public_manifest_sha256"),
    "manifest_binding_paths": {"diagnostics_input_sha256": ("diagnostics_input", "sha256"),
                               "diagnostics_report_sha256": ("diagnostics", "sha256"),
                               "source_replay_sha256": ("source_replay", "sha256"),
                               "public_manifest_sha256": ("public_manifest", "sha256")},
    "summary_fields": ("diagnostics_input_sha256", "diagnostics_report_sha256", "source_replay_sha256",
                       "public_manifest_sha256", "historical_case_count", "source_byte_count",
                       "source_structural_comparison_available", "source_label_baseline_separate",
                       "mode_metrics", "source_label_baseline_metrics", "captured_source_head",
                       "captured_source_head_canonical_sha256", "claimed_checkpoint_sha256", "head_identity_policy",
                       "native_output_stage", "exposure", "training_cost", "input_bytes", "limits"),
}
ISOLATED_WORKFLOWS["portable_evidence_children"] = {
    "script": "release_audit/portable_evidence_children.py",
    "report": "portable_evidence_children.json",
    "schema": "codebase-ir-portable-evidence-children-verification@1",
    "relative_inputs": True,
    "command_mode": "child_archive_verify",
    "false_flags": (*ISOLATED_WORKFLOWS["released_evidence_children"]["false_flags"],
                    "git_executable_invoked", "original_paths_read", "network_access_performed"),
    "true_flags": ("archive_roundtrip_verified", "portable_child_scope_complete", "git_object_verification_performed",
                   "child_evidence_custody_inventory_produced"),
    "binding_fields": ("archive_sha256", "capsule_manifest_sha256"),
    "manifest_binding_paths": {"archive_sha256": ("archive", "sha256"),
                               "capsule_manifest_sha256": ("capsule_manifest_sha256",)},
    "summary_fields": ("archive_sha256", "capsule_manifest_sha256", "source_manifest_sha256", "source_report_sha256",
                       "ledger_sha256", "manifest_count", "declared_child_count", "verified_child_count",
                       "unique_child_body_count", "declared_child_bytes", "manifest_dispositions", "child_dispositions",
                       "file_count", "directory_count", "object_count", "capsule_bytes", "archive_bytes",
                       "restored_verification", "omissions"),
}
ISOLATED_WORKFLOWS["native_inventory_query"] = {
    "script": "acceptance/inventory_query_controls/native_receiver.py",
    "report": "native_inventory_query.json",
    "schema": "codebase-ir-native-inventory-query-receiving-report@1",
    "false_flags": ("owner_database_opened", "profile_keys_read", "signature_authentication_performed",
                    "numerical_state_replayed", "source_execution_replayed", "checker_executions_replayed",
                    "live_eligibility_qualified", "production_acceptance_qualified", "native_export_adoption_qualified"),
    "true_flags": ("native_export_receiving_conformance",),
    "zero_fields": ("runtime_fact_count", "tasks_omitted_count", "additional_attempted_training_epochs"),
    "binding_fields": ("prior_primary_audit_sha256",),
    "manifest_binding_paths": {"prior_primary_audit_sha256": ("prior_primary_audit", "sha256")},
    "summary_fields": ("prior_primary_audit_sha256", "native_profile_count", "inventory_member_count",
                       "native_evidence_record_count", "native_preview_count", "runtime_requirement_count",
                       "runtime_task_count", "retained_page_count", "mutation_control_count", "input_file_count",
                       "input_bytes", "profiles", "runtime_fact_count", "tasks_omitted_count",
                       "native_export_receiving_conformance", "native_export_adoption_qualified"),
}


ISOLATED_WORKFLOWS["native_batch_query"] = {
    "script": "acceptance/inventory_query_controls/native_batch_receiver.py",
    "report": "native_batch_query.json",
    "schema": "codebase-ir-native-batch-query-receiving-report@1",
    "false_flags": (*ISOLATED_WORKFLOWS["native_inventory_query"]["false_flags"],
                    "review_custody_verified", "request_execution_custody_verified",
                    "batch_resource_execution_qualified", "throughput_improvement_qualified"),
    "true_flags": ("native_batch_receiving_conformance", "original_requirement_custody_reconciled",
                   "restart_request_response_bindings_reconciled"),
    "zero_fields": ("runtime_fact_count", "tasks_omitted_count", "additional_attempted_training_epochs"),
    "binding_fields": ("prior_qualification_sha256", "native_result_sha256", "restart_request_sha256",
                       "restart_response_sha256", "source_snapshot_sha256"),
    "manifest_binding_paths": {"prior_qualification_sha256": ("prior_qualification", "sha256"),
                               "native_result_sha256": ("native_result", "sha256"),
                               "restart_request_sha256": ("restart_request", "sha256"),
                               "restart_response_sha256": ("restart_response", "sha256"),
                               "source_snapshot_sha256": ("source_snapshot", "sha256")},
    "summary_fields": ("prior_qualification_sha256", "native_result_sha256", "restart_request_sha256",
                       "restart_response_sha256", "source_snapshot_sha256", "native_unit_count", "measurement_count",
                       "batch_page_count", "individual_page_count", "cold_batch_page_count", "resumed_page_count",
                       "requirement_count", "clause_count", "runtime_residual_count", "supported_lookup_requirement_count",
                       "unsupported_lookup_requirement_count", "mutation_control_count", "input_file_count", "input_bytes",
                       "runtime_fact_count", "tasks_omitted_count", "native_batch_receiving_conformance"),
}
ISOLATED_WORKFLOWS["native_program_graph"] = {
    "script": "corpus_audit/codebase_ir_native_program_graph.py",
    "report": "native_program_graph.json",
    "schema": "codebase-ir-native-program-graph@1",
    "relative_inputs": True,
    "false_flags": (*ISOLATED_WORKFLOWS["native_source_comparison"]["false_flags"],
                    "learned_full_program_prediction_verified", "free_running_full_program_quality_verified",
                    "graph_effect_runtime_truth_verified", "complete_ancestral_exposure_verified",
                    "native_compiler_execution_performed", "checker_execution_performed"),
    "true_flags": ("source_projection_graph_conformance_available", "source_graph_bindings_rederived",
                   "source_graph_effect_footprints_rederived", "source_comparison_independently_rederived",
                   "raw_native_graphs_retained_unmodified", "source_label_baseline_separate", "unknown_pretraining_exposure"),
    "binding_fields": ("source_comparison_input_sha256", "source_comparison_report_sha256"),
    "manifest_binding_paths": {"source_comparison_input_sha256": ("source_comparison_input", "sha256"),
                               "source_comparison_report_sha256": ("source_comparison", "sha256")},
    "summary_fields": ("source_comparison_input_sha256", "source_comparison_report_sha256", "source_replay_sha256",
                       "public_manifest_sha256", "historical_case_count", "role_graph_metrics", "source_graph_count",
                       "source_byte_count", "native_graph_stage", "exposure", "source_projection_graph_conformance_available"),
}
ISOLATED_WORKFLOWS["producer_source_bindings"] = {
    "script": "release_audit/producer_source_bindings.py",
    "report": "producer_source_bindings.json",
    "schema": "codebase-ir-producer-source-bindings-verification@1",
    "relative_inputs": True,
    "command_mode": "archive_verify",
    "false_flags": (*ISOLATED_WORKFLOWS["portable_evidence_children"]["false_flags"],
                    "producer_source_imports_performed", "current_working_source_compared", "source_semantics_verified",
                    "producer_execution_authenticated", "source_dependency_closure_qualified"),
    "true_flags": ("producer_source_inventory_produced", "git_object_verification_performed",
                   "portable_producer_scope_complete", "archive_roundtrip_verified"),
    "binding_fields": ("archive_sha256", "capsule_manifest_sha256", "custody_capsule_manifest_sha256"),
    "manifest_binding_paths": {"archive_sha256": ("archive", "sha256"),
                               "capsule_manifest_sha256": ("capsule_manifest_sha256",),
                               "custody_capsule_manifest_sha256": ("custody_capsule_manifest_sha256",)},
    "summary_fields": ("archive_sha256", "capsule_manifest_sha256", "custody_capsule_manifest_sha256", "release_commit",
                       "ledger_sha256", "source_manifest_sha256", "source_report_sha256", "receipt_count",
                       "claim_membership_count", "unique_source_path_count", "captured_source_count",
                       "verified_source_membership_count", "source_dispositions", "all_selected_sources_verified",
                       "declared_size_membership_count", "undeclared_size_membership_count", "file_count", "directory_count",
                       "object_count", "capsule_bytes", "archive_bytes", "restored_verification", "omissions"),
}
ISOLATED_WORKFLOWS["native_lean_projection"] = {
    "script": "corpus_audit/codebase_ir_native_lean_projection.py",
    "report": "native_lean_projection.json",
    "schema": "codebase-ir-native-lean-projection@1",
    "relative_inputs": True,
    "false_flags": (*ISOLATED_WORKFLOWS["native_program_graph"]["false_flags"],
                    "compiler_output_semantics_verified", "operational_semantics_verified",
                    "native_checker_results_replayed", "universal_semantics_verified",
                    "semantic_projection_loss_certified", "producer_execution_authenticated"),
    "true_flags": ("lean_projection_conformance_available", "program_graph_independently_rederived",
                   "projection_evidence_reconciled", "raw_lean_bodies_retained_unmodified",
                   "source_label_baseline_separate", "unknown_pretraining_exposure"),
    "binding_fields": ("program_graph_input_sha256", "program_graph_report_sha256",
                       "learned_lake_receipt_sha256", "learned_lean_sha256",
                       "source_label_baseline_lake_receipt_sha256", "source_label_baseline_lean_sha256"),
    "manifest_binding_paths": {"program_graph_input_sha256": ("program_graph_input", "sha256"),
                               "program_graph_report_sha256": ("program_graph_report", "sha256"),
                               "learned_lake_receipt_sha256": ("learned_lake_receipt", "sha256"),
                               "learned_lean_sha256": ("learned_lean", "sha256"),
                               "source_label_baseline_lake_receipt_sha256": ("source_label_baseline_lake_receipt", "sha256"),
                               "source_label_baseline_lean_sha256": ("source_label_baseline_lean", "sha256")},
    "summary_fields": ("program_graph_input_sha256", "program_graph_report_sha256", "public_manifest_sha256",
                       "source_replay_sha256", "historical_case_count", "source_byte_count",
                       "role_projection_metrics", "compiler_output_body_equal", "projection_stage",
                       "projection_coverage", "projection_losses", "exposure", "lean_projection_conformance_available"),
}
SMT_V2_INPUT_ROLES = ("prior_qualification", "native_result", "native_command", "launch_audit", "lifecycle_audit",
                      "control_audit", "wire_before", "wire_after", "wire_comparison", "runtime_before", "runtime_after")
ISOLATED_WORKFLOWS["smt_v2_custody"] = {
    "script": "acceptance/smt_v2_controls/receiver.py",
    "report": "smt_v2_custody.json",
    "schema": "codebase-ir-smt-v2-custody-report@1",
    "relative_inputs": True,
    "false_flags": ("owner_database_opened", "profile_keys_read", "signature_authentication_performed",
                    "numerical_state_replayed", "source_execution_replayed", "checker_executions_replayed",
                    "live_eligibility_qualified", "production_acceptance_qualified", "solver_verdict_authenticated",
                    "runtime_resource_enforcement_verified", "raw_phase_stdin_custody_verified",
                    "raw_caller_request_custody_verified", "unique_phase_execution_attestation_verified",
                    "behavioral_evidence_admission_qualified", "proof_certificate_verified"),
    "true_flags": ("smt_v2_structural_custody_conformance", "retained_request_evidence_bindings_reconciled",
                   "wire_fixture_compatibility_reconciled", "frozen_wire_definitions_unchanged"),
    "zero_fields": ("runtime_fact_count", "tasks_omitted_count", "additional_attempted_training_epochs"),
    "binding_fields": tuple(role + "_sha256" for role in SMT_V2_INPUT_ROLES),
    "manifest_binding_paths": {role + "_sha256": (role, "sha256") for role in SMT_V2_INPUT_ROLES},
    "summary_fields": ("prior_qualification_sha256", "native_result_sha256", "baseline_case_count", "nested_case_count",
                       "interruption_control_count", "native_launch_count", "native_lifecycle_count", "baseline_phase_count",
                       "nested_phase_count", "interruption_phase_count", "wire_fixture_case_count",
                       "unchanged_wire_definition_count", "input_file_count", "input_bytes", "mutation_control_count",
                       "runtime_fact_count", "tasks_omitted_count", "additional_attempted_training_epochs"),
}
ISOLATED_WORKFLOWS["producer_source_provenance"] = {
    "script": "release_audit/producer_source_provenance.py",
    "report": "producer_source_provenance.json",
    "schema": "codebase-ir-producer-source-provenance-verification@1",
    "relative_inputs": True,
    "command_mode": "archive_verify",
    "false_flags": (*ISOLATED_WORKFLOWS["producer_source_bindings"]["false_flags"],
                    "historical_source_substitution_performed", "historical_source_execution_authenticated",
                    "historical_original_path_commit_authenticated"),
    "true_flags": ("producer_source_provenance_inventory_produced", "git_object_verification_performed",
                   "committed_source_dispositions_preserved", "portable_selected_provenance_verified",
                   "archive_roundtrip_verified"),
    "binding_fields": ("archive_sha256", "capsule_manifest_sha256", "producer_capsule_manifest_sha256",
                       "custody_capsule_manifest_sha256", "producer_source_input_sha256", "producer_source_report_sha256"),
    "manifest_binding_paths": {"archive_sha256": ("archive", "sha256"),
                               "capsule_manifest_sha256": ("capsule_manifest_sha256",),
                               "producer_capsule_manifest_sha256": ("producer_capsule_manifest_sha256",),
                               "custody_capsule_manifest_sha256": ("custody_capsule_manifest_sha256",),
                               "producer_source_input_sha256": ("producer_source_input_sha256",),
                               "producer_source_report_sha256": ("producer_source_report_sha256",)},
    "summary_fields": ("archive_sha256", "capsule_manifest_sha256", "producer_capsule_manifest_sha256",
                       "custody_capsule_manifest_sha256", "producer_source_input_sha256", "producer_source_report_sha256",
                       "selected_source_count", "historical_dispositions", "recovered_historical_source_count",
                       "unavailable_historical_source_count", "committed_source_dispositions",
                       "committed_all_selected_sources_verified", "historical_sources", "release_commit", "ledger_sha256",
                       "file_count", "directory_count", "object_count", "capsule_bytes", "archive_bytes", "restored_verification"),
}
ISOLATED_WORKFLOWS["native_feature_coverage"] = {
    "script": "corpus_audit/codebase_ir_native_feature_coverage.py",
    "report": "native_feature_coverage.json",
    "schema": "codebase-ir-native-feature-coverage@1",
    "relative_inputs": True,
    "false_flags": (*ISOLATED_WORKFLOWS["native_source_comparison"]["false_flags"],
                    "native_feature_vector_execution_replayed", "model_predictions_evaluated", "optimizer_state_replayed",
                    "training_absence_certified", "feature_recipe_execution_authenticated", "heldout_quality_verified",
                    "feature_model_decoder_qualified", "complete_ancestral_exposure_verified",
                    "normalized_feature_vectors_rederived"),
    "true_flags": ("source_bound_feature_coverage_available", "source_labels_rederived",
                   "frozen_basis_signatures_rederived", "raw_exports_retained_unmodified",
                   "all_declared_target_roles_preserved", "unknown_pretraining_exposure"),
    "binding_fields": ("provenance_input_sha256", "parent_export_sha256", "child_export_sha256"),
    "zero_fields": ("additional_attempted_training_epochs", "new_final_assignments"),
    "manifest_binding_paths": {"provenance_input_sha256": ("provenance_input", "sha256"),
                               "parent_export_sha256": ("parent_export", "sha256"),
                               "child_export_sha256": ("child_export", "sha256")},
    "summary_fields": ("provenance_input_sha256", "parent_export_sha256", "child_export_sha256",
                       "historical_target_count", "unique_source_count", "frozen_basis_column_count",
                       "frozen_basis_column_sha256", "role_counts", "out_of_vocabulary_target_count",
                       "out_of_vocabulary_atom_count", "distinguishing_collision_group_count",
                       "cross_role_literal_collision_group_count", "unknown_sort_occurrence_count", "collision_groups"),
}
ISOLATED_WORKFLOWS["jvm_probe_custody"] = {
    "script": "acceptance/jvm_probe_controls/receiver.py",
    "report": "jvm_probe_custody.json",
    "schema": "codebase-ir-jvm-probe-custody-report@1",
    "relative_inputs": True,
    "false_flags": ("owner_database_opened", "profile_keys_read", "signature_authentication_performed",
                    "numerical_state_replayed", "source_execution_replayed", "checker_executions_replayed",
                    "live_eligibility_qualified", "production_acceptance_qualified", "runtime_resource_enforcement_verified",
                    "raw_phase_stdin_custody_verified", "raw_caller_request_custody_verified",
                    "unique_phase_execution_attestation_verified", "behavioral_evidence_admission_qualified",
                    "proof_certificate_verified", "model_checker_execution_qualified", "jvm_binary_identity_authenticated",
                    "launcher_body_custody_verified", "parent_constructor_propagation_qualified",
                    "throughput_improvement_qualified", "native_deadline_expiry_observed", "native_pressure_backoff_observed"),
    "true_flags": ("jvm_probe_structural_custody_conformance", "recorded_probe_phase_bindings_reconciled",
                   "wire_fixture_compatibility_reconciled", "frozen_wire_definitions_unchanged"),
    "zero_fields": ("runtime_fact_count", "tasks_omitted_count", "additional_attempted_training_epochs"),
    "binding_fields": tuple(role + "_sha256" for role in SMT_V2_INPUT_ROLES),
    "manifest_binding_paths": {role + "_sha256": (role, "sha256") for role in SMT_V2_INPUT_ROLES},
    "summary_fields": ("prior_qualification_sha256", "native_result_sha256", "baseline_case_count", "nested_case_count",
                       "successful_probe_count", "interruption_control_count", "prelaunch_stop_count", "live_stop_count",
                       "native_launch_count", "native_lifecycle_count", "root_probe_phase_count", "parent_owned_probe_phase_count",
                       "wire_fixture_case_count", "wire_field_count", "unchanged_wire_definition_count",
                       "input_file_count", "input_bytes", "mutation_control_count",
                       "runtime_fact_count", "tasks_omitted_count", "additional_attempted_training_epochs"),
}
ISOLATED_WORKFLOWS["finite_proof_toolchain_custody"] = {
    "script": "release_audit/finite_proof_toolchain_custody.py",
    "report": "finite_proof_toolchain_custody.json",
    "schema": "codebase-ir-finite-proof-toolchain-custody@1",
    "relative_inputs": True,
    "false_flags": (*ISOLATED_WORKFLOWS["portable_evidence_children"]["false_flags"],
                    "native_tool_bytes_available", "transitive_toolchain_dependencies_attested",
                    "checker_execution_authenticated", "kernel_proof_replayed", "historical_execution_environment_authenticated",
                    "proof_reuse_eligibility_qualified", "source_semantics_verified", "source_execution_replayed",
                    "owner_sources_imported", "domain_cid_recipe_qualified"),
    "true_flags": ("finite_proof_toolchain_custody_inventory_produced", "selected_artifact_bindings_reconciled",
                   "git_object_verification_performed"),
    "binding_fields": ("custody_capsule_manifest_sha256",),
    "manifest_binding_paths": {"custody_capsule_manifest_sha256": ("custody_capsule_manifest", "sha256")},
    "summary_fields": ("custody_capsule_manifest_sha256", "ledger_sha256", "release_commit", "group_count",
                       "artifact_membership_count", "unique_body_count", "selected_artifact_bytes",
                       "selected_git_object_count", "groups", "dependency_frontiers", "tool_declarations", "recorded_versions",
                       "input_stability", "retained_copy_stability"),
}


ISOLATED_WORKFLOWS["finite_match_controls"] = {
    "script": "acceptance/finite_match_controls/receiver.py",
    "report": "finite_match_controls.json",
    "schema": "codebase-ir-finite-match-controls@1",
    "relative_inputs": True,
    "true_flags": ("authored_requirement_matching_conformance", "retained_finite_rows_reconciled",
                   "original_requirements_and_tasks_preserved"),
    "false_flags": ("checker_executions_replayed", "kernel_proof_replayed", "source_execution_replayed",
                    "source_semantics_verified", "runtime_behavior_verified", "producer_signatures_authenticated",
                    "original_request_authenticated", "historical_execution_environment_authenticated",
                    "resource_enforcement_authenticated", "domain_cid_recipe_qualified", "proof_reuse_eligibility_qualified",
                    "owner_database_opened", "profile_keys_read", "native_export_adoption_qualified",
                    "production_acceptance_qualified"),
    "zero_fields": ("runtime_fact_count", "tasks_omitted_count", "additional_attempted_training_epochs"),
    "binding_fields": ("requirements_sha256", "prior_manifest_sha256", "prior_report_sha256", "prior_selected_custody_sha256"),
    "manifest_binding_paths": {role + "_sha256": (role, "sha256")
                               for role in ("requirements", "prior_manifest", "prior_report", "prior_selected_custody")},
    "summary_fields": ("requirements_sha256", "prior_manifest_sha256", "prior_report_sha256", "prior_selected_custody_sha256",
                       "group_count", "retained_finite_row_count", "requirement_count", "task_count",
                       "recorded_supported_count", "recorded_refuted_count", "uncovered_count", "unsupported_count",
                       "runtime_deferred_count", "runtime_residual_task_count", "authored_incompatible_pair_count",
                       "runtime_fact_count", "tasks_omitted_count", "additional_attempted_training_epochs"),
}
ISOLATED_WORKFLOWS["feature_separation"] = {
    "script": "corpus_audit/codebase_ir_feature_separation.py",
    "report": "feature_separation.json",
    "schema": "codebase-ir-feature-separation@1",
    "relative_inputs": True,
    "true_flags": (*ISOLATED_WORKFLOWS["native_feature_coverage"]["true_flags"],
                   "frozen_basis_retained_unmodified", "counterfactual_separation_available", "minimality_exhaustively_checked"),
    "false_flags": (*ISOLATED_WORKFLOWS["native_feature_coverage"]["false_flags"],
                    "feature_basis_modified", "augmentation_applied_to_native_feature_space", "candidate_tensors_modified",
                    "model_quality_gain_verified", "universal_source_label_separation_verified",
                    "open_world_literal_coverage_verified", "source_runtime_truth_verified"),
    "zero_fields": ("additional_attempted_training_epochs", "new_final_assignments"),
    "binding_fields": ("feature_coverage_input_sha256", "feature_coverage_report_sha256"),
    "manifest_binding_paths": {role + "_sha256": (role, "sha256")
                               for role in ("feature_coverage_input", "feature_coverage_report")},
    "summary_fields": ("feature_coverage_input_sha256", "feature_coverage_report_sha256",
                       "provenance_input_sha256", "parent_export_sha256", "child_export_sha256",
                       "historical_target_count", "frozen_basis_column_count", "frozen_basis_column_sha256",
                       "candidate_oov_column_count", "minimal_extra_column_count", "minimal_separating_subset_count",
                       "exhaustive_subset_count", "full_oov_extra_column_count", "unknown_sort_occurrence_count",
                       "projection_source_span_loss_count", "counterfactual_selection_exposure",
                       "new_final_assignments", "additional_attempted_training_epochs"),
}
ISOLATED_WORKFLOWS["admission_declaration_custody"] = {
    "script": "release_audit/admission_declaration_custody.py",
    "report": "admission_declaration_custody.json",
    "schema": "codebase-ir-admission-declaration-custody@1",
    "relative_inputs": True,
    "true_flags": ("admission_declaration_custody_inventory_produced", "selected_artifact_bindings_reconciled",
                   "git_object_verification_performed", "recorded_qualification_history_reconciled",
                   "recorded_control_population_reconciled"),
    "false_flags": (*ISOLATED_WORKFLOWS["portable_evidence_children"]["false_flags"],
                    "signature_envelope_custody_verified", "signed_admission_bindings_complete",
                    "signature_authentication_performed", "owner_authorization_authenticated",
                    "historical_checker_execution_authenticated", "recorded_controls_replayed",
                    "native_task_population_verified", "live_admission_eligibility_verified", "proof_reuse_eligibility_qualified",
                    "source_semantics_verified", "owner_sources_imported", "model_off_execution_authenticated",
                    "training_absence_certified", "full_daemon_lifecycle_custody_verified", "producer_source_bodies_retained"),
    "zero_fields": ("runtime_fact_count", "tasks_omitted_count", "additional_attempted_training_epochs"),
    "binding_fields": ("custody_capsule_manifest_sha256",),
    "manifest_binding_paths": {"custody_capsule_manifest_sha256": ("custody_capsule_manifest", "sha256")},
    "summary_fields": ("custody_capsule_manifest_sha256", "ledger_sha256", "release_commit", "selected_parent_sha256",
                       "artifact_membership_count", "selected_artifact_bytes", "selected_git_object_count",
                       "producer_source_claim_count", "recorded_run_count", "adverse_recorded_run_count",
                       "final_recorded_test_count", "resigned_control_count", "fresh_checker_per_control",
                       "collected_cases_without_retained_outcome",
                       "run_history", "final_controls", "envelope_frontiers", "lifecycle_scope",
                       "runtime_fact_count", "tasks_omitted_count", "additional_attempted_training_epochs"),
}


ISOLATED_WORKFLOWS["resumed_inventory_controls"] = {
    "script": "acceptance/resumed_inventory_controls/receiver.py",
    "report": "resumed_inventory_controls.json",
    "schema": "codebase-ir-resumed-inventory-controls@1",
    "relative_inputs": True,
    "true_flags": ("retained_resumed_inventory_conformance", "ordered_complete_membership_reconciled",
                   "historical_resumption_records_reconciled", "failed_and_composed_outcomes_preserved"),
    "false_flags": ("owner_database_opened", "profile_keys_read", "signature_authentication_performed",
                    "numerical_state_replayed", "source_execution_replayed", "checker_executions_replayed",
                    "runtime_execution_replayed", "resource_enforcement_qualified", "process_origin_attested",
                    "live_eligibility_qualified", "production_acceptance_qualified", "native_export_adoption_qualified"),
    "zero_fields": ("runtime_fact_count", "tasks_omitted_count", "additional_attempted_training_epochs"),
    "binding_fields": ("historical_scan_audit_sha256", "historical_scan_result_sha256", "composed_worker_result_sha256"),
    "manifest_binding_paths": {role + "_sha256": (role, "sha256")
                               for role in ("historical_scan_audit", "historical_scan_result", "composed_worker_result")},
    "summary_fields": ("historical_scan_audit_sha256", "historical_scan_result_sha256", "composed_worker_result_sha256",
                       "root_cid", "completion_cid", "inventory_member_count", "page_count", "historical_resumption_count",
                       "inferred_member_count", "deferred_member_count", "unsupported_member_count",
                       "new_scan_page_count", "new_fitting_epoch_count", "inherited_setup_epoch_count",
                       "historical_scan_overall_qualified", "composed_worker_overall_qualified", "coverage", "frontiers",
                       "runtime_fact_count", "tasks_omitted_count", "additional_attempted_training_epochs"),
}
ISOLATED_WORKFLOWS["resumed_cohort_audit"] = {
    "script": "corpus_audit/codebase_ir_resumed_cohort_audit.py",
    "report": "resumed_cohort_audit.json",
    "schema": "codebase-ir-resumed-cohort-audit@1",
    "relative_inputs": True,
    "true_flags": ("source_artifact_body_pins_verified", "source_ast_membership_accounting_available",
                   "complete_paged_disposition_accounting_available", "normalized_ast_groups_rederived",
                   "declared_exposure_roles_preserved", "retained_training_selections_accounted", "unknown_pretraining_exposure",
                   "input_files_stable"),
    "false_flags": ("model_selection_performed", "promotion_performed", "candidate_model_qualified",
                    "producer_authentication_verified", "numerical_provenance_verified", "source_semantics_verified",
                    "source_derived_accuracy_available", "heldout_independence_verified", "learned_weight_dependence_verified",
                    "git_object_custody_verified", "preconstraint_raw_output_available", "checker_execution_replayed",
                    "source_runtime_truth_verified", "training_population_equals_inventory", "complete_pretraining_exposure_verified",
                    "model_predictions_evaluated", "optimizer_state_replayed", "final_population_modified",
                    "scan_execution_attested", "source_execution_attested", "runtime_behavior_verified", "source_ast_semantics_verified",
                    "native_target_recipe_replayed"),
    "zero_fields": ("additional_attempted_training_epochs", "new_final_assignments"),
    "binding_fields": ("qualification_review_sha256", "native_result_sha256"),
    "manifest_binding_paths": {role + "_sha256": (role, "sha256") for role in ("qualification_review", "native_result")},
    "summary_fields": ("qualification_review_sha256", "native_result_sha256", "inventory_member_count", "page_count",
                       "disposition_counts", "inferred_row_count", "source_artifact_body_count", "captured_input_file_count",
                       "captured_input_bytes", "source_bytes_available_member_count", "ast_record_available_member_count",
                       "normalized_ast_group_count", "clone_group_count", "declared_training_paths", "declared_tuning_paths",
                       "declared_canary_paths", "source_missing_members", "recorded_inherited_setup_epochs",
                       "additional_attempted_training_epochs", "new_final_assignments"),
}
ISOLATED_WORKFLOWS["dispatch_attempt_custody"] = {
    "script": "release_audit/dispatch_attempt_custody.py",
    "report": "dispatch_attempt_custody.json",
    "schema": "codebase-ir-dispatch-attempt-custody@1",
    "relative_inputs": True,
    "true_flags": ("dispatch_attempt_custody_inventory_produced", "recorded_attempt_population_reconciled",
                   "recorded_test_phase_populations_reconciled", "recorded_costs_reconciled",
                   "original_outcomes_and_generations_preserved"),
    "false_flags": ("owner_sources_imported", "owner_database_opened", "profile_keys_read", "git_executable_invoked",
                    "network_access_performed", "signature_authentication_performed", "producer_authentication_verified",
                    "native_publication_reconstructed", "live_attempt_eligibility_verified", "historical_process_origin_authenticated",
                    "complete_runtime_generation_custody_qualified", "whole_current_live_runtime_qualified",
                    "whole_same_generation_host_suite_qualified", "external_effect_absence_qualified", "unique_cpu_time_measured",
                    "total_elapsed_wall_time_measured", "training_absence_certified", "complete_os_launch_census_verified",
                    "proof_authority_qualified", "production_acceptance_requalified"),
    "zero_fields": ("new_native_jobs_launched", "additional_attempted_training_epochs"),
    "binding_fields": ("machine_review_sha256", "attempt_ledger_sha256", "postledger_supplement_sha256"),
    "manifest_binding_paths": {role + "_sha256": (role, "sha256")
                               for role in ("machine_review", "attempt_ledger", "postledger_supplement")},
    "summary_fields": ("machine_review_sha256", "attempt_ledger_sha256", "postledger_supplement_sha256",
                       "selected_file_count", "selected_input_bytes", "host_attempt_count", "docker_attempt_count",
                       "stream_attempt_count", "adverse_host_attempt_count", "unqualified_docker_driver_count",
                       "metadata_audit_attempt_count", "non_native_preparation_count", "host_phase_population", "driver_costs",
                       "null_cost_frontiers", "matched_generation12_recorded_outcomes", "whole_suite_generation_frontiers",
                       "raw_body_frontiers", "selected_custody", "new_native_jobs_launched", "additional_attempted_training_epochs"),
}


ISOLATED_WORKFLOWS["tla_operation_controls"] = {
    "script": "acceptance/tla_operation_controls/receiver.py",
    "report": "tla_operation_controls.json",
    "schema": "codebase-ir-tla-operation-controls@1",
    "relative_inputs": True,
    "true_flags": ("retained_tla_operation_custody_conformance", "recorded_phase_bindings_reconciled",
                   "failed_whole_attempts_preserved", "partial_results_not_promoted"),
    "false_flags": ("owner_database_opened", "profile_keys_read", "owner_sources_imported", "source_execution_replayed",
                    "checker_executions_replayed", "signature_authentication_performed", "process_origin_attested",
                    "resource_enforcement_qualified", "original_request_custody_qualified", "aggregate_operation_success_qualified",
                    "model_check_authority_qualified", "proof_authority_qualified", "live_eligibility_qualified",
                    "production_acceptance_qualified", "native_export_adoption_qualified", "throughput_improvement_qualified"),
    "zero_fields": ("runtime_fact_count", "tasks_omitted_count", "additional_attempted_training_epochs"),
    "binding_fields": tuple(attempt + "_" + role + "_sha256" for attempt in ("initial", "final", "accepted")
                            for role in ("result", "command_result", "source_freeze")),
    "manifest_binding_paths": {attempt + "_" + role + "_sha256": ("attempts", index, role, "sha256")
                               for index, attempt in enumerate(("initial", "final", "accepted"))
                               for role in ("result", "command_result", "source_freeze")},
    "summary_fields": ("attempt_count", "failed_whole_attempt_count", "recorded_native_phase_count", "completed_batch_count",
                       "completed_case_count", "recorded_no_result_control_count", "attempts", "frontiers",
                       "runtime_fact_count", "tasks_omitted_count", "additional_attempted_training_epochs"),
}
ISOLATED_WORKFLOWS["source_delta_analysis"] = {
    "script": "corpus_audit/codebase_ir_source_delta_analysis.py",
    "report": "source_delta_analysis.json",
    "schema": "codebase-ir-source-delta-analysis@1",
    "relative_inputs": True,
    "true_flags": ("source_delta_accounting_produced", "complete_union_accounting_available", "source_bytes_comparisons_rederived",
                   "source_syntax_comparisons_rederived", "captured_ast_bindings_rederived", "clone_and_template_impact_rederived",
                   "syntactic_dependency_frontier_rederived", "historical_content_exposure_accounted",
                   "original_failed_observation_preserved", "unknown_pretraining_exposure", "current_exposure_unknown"),
    "false_flags": ("owner_sources_imported", "git_executable_invoked", "owner_database_opened", "profile_keys_read",
                    "model_predictions_evaluated", "optimizer_state_replayed", "source_execution_attested", "scan_execution_attested",
                    "source_semantics_verified", "source_runtime_truth_verified", "physical_absence_verified", "semantic_rename_verified",
                    "numerical_reuse_authorized", "model_advanced", "candidate_model_qualified", "producer_authentication_verified",
                    "numerical_provenance_verified", "heldout_independence_verified", "complete_pretraining_exposure_verified",
                    "current_training_roles_transferred", "historical_exposure_roles_transferred", "full_ancestry_verified",
                    "current_model_eligibility_qualified", "proof_reuse_eligibility_qualified", "learned_weight_dependence_verified",
                    "learned_quality_improvement_verified", "universal_source_label_equivalence_verified", "model_selection_performed",
                    "promotion_performed", "final_population_modified"),
    "zero_fields": ("additional_attempted_training_epochs", "new_final_assignments"),
    "binding_fields": tuple(role + "_sha256" for role in ("review", "source_result", "source_audit", "ignored_result",
                                                        "failed_ignore_result", "historical_cohort_report", "checkpoint_result")),
    "manifest_binding_paths": {role + "_sha256": (role, "sha256") for role in (
        "review", "source_result", "source_audit", "ignored_result", "failed_ignore_result", "historical_cohort_report", "checkpoint_result")},
    "summary_fields": ("previous_member_count", "current_member_count", "union_member_count", "entry_transition_counts",
                       "source_bytes_comparison_counts", "captured_ast_comparison_counts", "source_syntax_comparison_counts",
                       "structural_label_comparison_counts", "cross_path_content_pair_count", "previous_clone_group_count",
                       "current_clone_group_count", "previous_template_group_count", "current_template_group_count",
                       "syntactic_dependency_edge_count", "historical_content_match_member_count", "historical_content_match_role_counts",
                       "current_exposure_unknown_member_count", "affected_head_binding_count", "ignored_removed_count",
                       "additional_attempted_training_epochs", "new_final_assignments"),
}


ISOLATED_WORKFLOWS["current_runtime_cleanup_custody"] = {
    "script": "release_audit/current_runtime_cleanup_custody.py",
    "report": "current_runtime_cleanup_custody.json",
    "schema": "codebase-ir-current-runtime-cleanup-custody@1",
    "relative_inputs": True,
    "true_flags": ("current_runtime_cleanup_custody_produced", "recorded_cleanup_bindings_reconciled",
                   "recorded_test_identity_populations_reconciled", "failed_trial_receipts_preserved",
                   "declared_source_generation_metadata_reconciled", "recorded_costs_reconciled"),
    "false_flags": ("owner_sources_imported", "owner_database_opened", "profile_keys_read", "git_executable_invoked",
                    "network_access_performed", "signature_authentication_performed", "producer_authentication_verified",
                    "historical_process_origin_authenticated", "current_resource_cleanup_verified", "current_live_eligibility_verified",
                    "selected_source_bodies_replayed", "full_dependency_custody_qualified", "checkpoint_state_reconstructed",
                    "whole_current_runtime_qualified", "external_effect_absence_qualified", "training_absence_certified",
                    "unique_cpu_time_measured", "total_elapsed_wall_time_measured", "proof_authority_qualified",
                    "production_acceptance_requalified"),
    "zero_fields": ("new_native_jobs_launched", "additional_attempted_training_epochs", "source_bodies_read"),
    "binding_fields": tuple(role + "_sha256" for role in ("machine_review", "historical_review", "current_worker_result",
        "container_result", "cleanup_receipt", "independent_worker_audit", "selected_source_receipt", "authored_verification")),
    "manifest_binding_paths": {role + "_sha256": ("selected_files", index, "sha256") for index, role in (
        (0, "machine_review"), (1, "historical_review"), (2, "current_worker_result"), (3, "container_result"),
        (4, "cleanup_receipt"), (5, "independent_worker_audit"), (6, "selected_source_receipt"), (34, "authored_verification"))},
    "summary_fields": ("selected_file_count", "selected_input_bytes", "test_accounting", "failed_trial_distinct_identities",
                       "failed_trial_executions", "stdlib_reader_case_count", "stdlib_cases_in_pytest_total",
                       "declared_source_generation", "recorded_native_task_statuses", "recorded_cleanup", "recorded_costs",
                       "selected_custody", "new_native_jobs_launched", "additional_attempted_training_epochs", "source_bodies_read"),
}


ISOLATED_WORKFLOWS["apalache_admission_controls"] = {
    "script": "acceptance/apalache_admission_controls/receiver.py",
    "report": "apalache_admission_controls.json",
    "schema": "codebase-ir-apalache-admission-controls@1",
    "relative_inputs": True,
    "true_flags": ("retained_apalache_admission_custody_conformance", "recorded_phase_bindings_reconciled",
                   "failed_whole_attempts_preserved", "raw_witness_only_scope_preserved",
                   "registry_error_regression_preserved"),
    "false_flags": ("owner_database_opened", "profile_keys_read", "owner_sources_imported", "source_execution_replayed",
                    "checker_executions_replayed", "signature_authentication_performed", "process_origin_attested",
                    "resource_enforcement_qualified", "original_request_custody_qualified", "model_check_authority_qualified",
                    "proof_authority_qualified", "counterexample_replay_qualified", "registry_native_success_qualified",
                    "whole_install_cancellation_qualified", "hard_aggregate_containment_qualified", "live_eligibility_qualified",
                    "production_acceptance_qualified", "native_export_adoption_qualified", "throughput_improvement_qualified",
                    "model_quality_qualified"),
    "zero_fields": ("runtime_fact_count", "tasks_omitted_count", "additional_attempted_training_epochs"),
    "binding_fields": ("qualification_sha256", *(attempt + "_" + role + "_sha256"
        for attempt in ("capacity_failed", "resource_failed", "accepted_smoke", "accepted_full")
        for role in ("result", "command_result"))),
    "manifest_binding_paths": {"qualification_sha256": ("qualification", "sha256"),
        **{attempt + "_" + role + "_sha256": ("attempts", index, role, "sha256")
           for index, attempt in enumerate(("capacity_failed", "resource_failed", "accepted_smoke", "accepted_full"))
           for role in ("result", "command_result")}},
    "summary_fields": ("selected_attempt_count", "accepted_attempt_count", "failed_attempt_count",
                       "selected_native_phase_count", "selected_lifecycle_count", "selected_prelaunch_refusal_count",
                       "accepted_native_phase_count", "accepted_success_case_count", "accepted_stop_control_count",
                       "historical_completed_stop_control_count", "declared_all_attempt_native_phase_count",
                       "declared_all_attempt_lifecycle_count", "selected_case_count", "registry_native_result_available",
                       "runtime_fact_count", "tasks_omitted_count", "additional_attempted_training_epochs"),
}


ISOLATED_WORKFLOWS["successor_cohort_audit"] = {
    "script": "corpus_audit/codebase_ir_successor_cohort_audit.py",
    "report": "successor_cohort_audit.json",
    "schema": "codebase-ir-successor-cohort-audit@1",
    "relative_inputs": True,
    "true_flags": ("successor_cohort_accounting_produced", "prefix_population_rederived", "source_bytes_bindings_rederived",
                   "captured_ast_bindings_rederived", "child_selection_roles_rederived", "source_clone_exposure_accounted",
                   "declaration_lineage_accounted", "historical_failed_attempt_preserved", "unknown_pretraining_exposure"),
    "false_flags": ("owner_sources_imported", "owner_database_opened", "git_executable_invoked", "profile_keys_read",
                    "source_execution_attested", "scan_execution_attested", "source_semantics_verified", "source_runtime_truth_verified",
                    "snapshot_schema_verified", "snapshot_entry_schema_verified", "native_target_digest_rederived",
                    "numerical_execution_reperformed", "numerical_provenance_verified", "inference_correctness_verified",
                    "optimizer_state_replayed", "checkpoint_states_verified", "full_ancestry_verified", "root_training_population_verified",
                    "replay_population_verified", "complete_pretraining_exposure_verified", "heldout_independence_verified",
                    "learned_weight_dependence_verified", "learned_quality_improvement_verified", "model_selection_performed",
                    "candidate_model_qualified", "promotion_performed", "model_advanced", "numerical_reuse_authorized",
                    "complete_scan_verified", "final_population_modified", "producer_authentication_verified"),
    "zero_fields": ("runtime_fact_count", "tasks_omitted_count", "additional_attempted_training_epochs", "new_final_assignments"),
    "binding_fields": tuple(role + "_sha256" for role in ("review", "native_result", "independent_audit", "failed_result")),
    "manifest_binding_paths": {role + "_sha256": (role, "sha256") for role in
                               ("review", "native_result", "independent_audit", "failed_result")},
    "summary_fields": ("complete_member_count", "unique_prefix_member_count", "prefix_page_count", "outside_prefix_member_count",
                       "selected_path_count", "source_body_count", "ast_body_count", "declared_child_role_counts", "prefix_dispositions",
                       "exact_source_role_overlap_count", "normalized_clone_role_overlap_count", "normalized_ast_group_count",
                       "declared_parent_version_id", "declared_child_version_id", "declared_feature_columns",
                       "claimed_successful_setup_epochs", "claimed_failed_setup_epochs", "claimed_total_native_setup_epochs",
                       "root_exposure_disposition", "replay_exposure_disposition"),
}


ISOLATED_WORKFLOWS["successor_planning_custody"] = {
    "script": "release_audit/successor_planning_custody.py",
    "report": "successor_planning_custody.json",
    "schema": "codebase-ir-successor-planning-custody@1",
    "relative_inputs": True,
    "true_flags": ("successor_planning_custody_produced", "recorded_task_residuals_reconciled", "recorded_stage_outcomes_reconciled",
                   "typed_preimage_population_reconciled", "semantic_material_byte_digests_rederived", "reused_cold_preimages_disclosed",
                   "declared_prefix_scope_reconciled", "failed_deadline_attempt_preserved", "recorded_costs_reconciled",
                   "recorded_resource_drain_reconciled"),
    "false_flags": ("owner_sources_imported", "owner_database_opened", "profile_keys_read", "git_executable_invoked", "network_access_performed",
                    "checkpoint_state_reconstructed", "model_bodies_read", "source_bodies_replayed", "semantic_digest_replay_qualified",
                    "semantic_meanings_independently_replayed", "critic_body_closure_qualified", "obligation_graph_body_closure_qualified",
                    "execution_plan_body_closure_qualified", "whole_planner_solver_free_qualified", "complete_successor_scan_qualified",
                    "two_prefixes_are_64_distinct_members_qualified", "cold_process_restart_qualified", "current_resource_cleanup_verified",
                    "kernel_resource_enforcement_qualified", "numerical_execution_independently_reperformed", "historical_process_origin_authenticated",
                    "signature_authentication_performed", "proof_authority_qualified", "production_acceptance_requalified", "worker_admission_qualified",
                    "unique_cpu_time_measured", "total_elapsed_wall_time_measured", "throughput_qualified"),
    "zero_fields": ("runtime_fact_count", "tasks_omitted_count", "additional_attempted_training_epochs"),
    "binding_fields": tuple(role + "_sha256" for role in ("machine_review", "closed_audit", "native_result", "failed_native_result",
        "authored_planning_inputs", "planning_preview", "cold_planning_preview", "planning_semantic_preimages",
        "cold_planning_semantic_preimages", "resource_admission")),
    "manifest_binding_paths": {role + "_sha256": ("selected_files", index, "sha256") for index, role in enumerate((
        "machine_review", "closed_audit", "native_result", "failed_native_result", "authored_planning_inputs", "planning_preview",
        "cold_planning_preview", "planning_semantic_preimages", "cold_planning_semantic_preimages", "resource_admission"))},
    "summary_fields": ("selected_file_count", "selected_input_bytes", "planning", "frontier", "receiving", "costs", "resources",
                       "declared_missing_closure", "runtime_fact_count", "tasks_omitted_count", "additional_attempted_training_epochs"),
}


ISOLATED_WORKFLOWS['foreign_outcome_controls'] = {'script': 'acceptance/foreign_outcome_controls/receiver.py',
 'report': 'foreign_outcome_controls.json',
 'schema': 'codebase-ir-foreign-outcome-controls@1',
 'relative_inputs': True,
 'manifest_binding_field': 'manifest_sha256',
 'true_flags': ('retained_foreign_outcome_custody_conformance',
                'generic_unknown_authority_preserved',
                'exact_typed_payload_preserved',
                'recorded_phase_bindings_reconciled',
                'failed_whole_attempt_preserved',
                'historical_raw_witness_scope_preserved'),
 'false_flags': ('owner_database_opened',
                 'profile_keys_read',
                 'owner_sources_imported',
                 'checker_executions_replayed',
                 'source_execution_replayed',
                 'signature_authentication_performed',
                 'process_origin_attested',
                 'original_request_custody_qualified',
                 'model_check_authority_qualified',
                 'proof_authority_qualified',
                 'counterexample_replay_qualified',
                 'registry_native_success_qualified',
                 'resource_enforcement_qualified',
                 'hard_aggregate_containment_qualified',
                 'whole_install_cancellation_qualified',
                 'live_eligibility_qualified',
                 'production_acceptance_qualified',
                 'native_export_adoption_qualified',
                 'throughput_improvement_qualified',
                 'model_quality_qualified',
                 'output_digest_algorithm_rederived'),
 'zero_fields': ('runtime_fact_count', 'tasks_omitted_count', 'additional_attempted_training_epochs'),
 'binding_fields': ('qualification_sha256',
                    'initial_result_sha256',
                    'initial_command_result_sha256',
                    'accepted_result_sha256',
                    'accepted_command_result_sha256',
                    'source_evolution_sha256'),
 'manifest_binding_paths': {'qualification_sha256': ('qualification', 'sha256'),
                            'source_evolution_sha256': ('source_evolution', 'sha256'),
                            'initial_result_sha256': ('attempts', 0, 'result', 'sha256'),
                            'initial_command_result_sha256': ('attempts', 0, 'command_result', 'sha256'),
                            'accepted_result_sha256': ('attempts', 1, 'result', 'sha256'),
                            'accepted_command_result_sha256': ('attempts', 1, 'command_result', 'sha256')},
 'summary_fields': ('selected_file_count',
                    'selected_input_bytes',
                    'attempts',
                    'qualification',
                    'controls',
                    'source_evolution_metadata',
                    'limitations',
                    'runtime_fact_count',
                    'tasks_omitted_count',
                    'additional_attempted_training_epochs')}

ISOLATED_WORKFLOWS['full_successor_cohort_audit'] = {'script': 'corpus_audit/codebase_ir_full_successor_cohort_audit.py',
 'report': 'full_successor_cohort_audit.json',
 'schema': 'codebase-ir-full-successor-cohort-audit@1',
 'relative_inputs': True,
 'manifest_binding_field': 'selected_manifest_sha256',
 'true_flags': ('full_successor_cohort_accounting_produced',
                'complete_default_page_population_rederived',
                'complete_member_dispositions_rederived',
                'snapshot_schema_verified',
                'snapshot_entry_schema_verified',
                'current_manifest_membership_reconciled',
                'previous_manifest_membership_reconciled',
                'source_delta_metadata_reconciled',
                'reference_first32_scope_preserved',
                'historical_no_fit_declarations_preserved',
                'declared_role_membership_reconciled',
                'fresh_process_declarations_reconciled',
                'unknown_pretraining_exposure'),
 'false_flags': ('owner_sources_imported',
                 'owner_database_opened',
                 'git_executable_invoked',
                 'profile_keys_read',
                 'raw_source_bytes_replayed',
                 'captured_ast_bindings_rederived',
                 'source_execution_attested',
                 'scan_execution_attested',
                 'source_semantics_verified',
                 'source_runtime_truth_verified',
                 'semantic_state_identity_rederived',
                 'native_target_digest_rederived',
                 'numerical_execution_reperformed',
                 'complete_inference_reperformed',
                 'numerical_provenance_verified',
                 'inference_correctness_verified',
                 'optimizer_state_replayed',
                 'checkpoint_states_verified',
                 'full_ancestry_verified',
                 'root_training_population_verified',
                 'replay_population_verified',
                 'complete_pretraining_exposure_verified',
                 'heldout_independence_verified',
                 'learned_weight_dependence_verified',
                 'learned_quality_improvement_verified',
                 'model_selection_performed',
                 'candidate_model_qualified',
                 'promotion_performed',
                 'model_advanced',
                 'numerical_reuse_authorized',
                 'full_reference_scan_verified',
                 'all_members_numerically_inferred',
                 'final_population_modified',
                 'producer_authentication_verified',
                 'process_origin_independently_attested',
                 'kernel_resource_enforcement_verified',
                 'whole_repository_coverage',
                 'physical_absence_verified',
                 'production_default_activated'),
 'zero_fields': ('runtime_fact_count',
                 'tasks_omitted_count',
                 'additional_attempted_training_epochs',
                 'new_final_assignments'),
 'binding_fields': ('full_scan_result_sha256',
                    'independent_audit_sha256',
                    'prior_review_sha256',
                    'previous_manifest_sha256',
                    'current_manifest_sha256',
                    'previous_publication_sha256',
                    'current_publication_sha256',
                    'source_delta_sha256',
                    'optimized_selection_sha256',
                    'reference_selection_sha256',
                    'optimized_root_sha256',
                    'reference_root_sha256',
                    'completion_sha256',
                    'reference_page_sha256',
                    'default_page_00_sha256',
                    'default_page_01_sha256',
                    'default_page_02_sha256',
                    'default_page_03_sha256',
                    'default_page_04_sha256',
                    'default_page_05_sha256',
                    'default_page_06_sha256',
                    'default_page_07_sha256',
                    'default_page_08_sha256',
                    'default_page_09_sha256',
                    'process_run_01_sha256',
                    'process_run_02_sha256',
                    'process_run_03_sha256',
                    'process_run_04_sha256',
                    'process_request_01_sha256',
                    'process_request_02_sha256',
                    'process_request_03_sha256',
                    'process_request_04_sha256',
                    'process_launch_01_sha256',
                    'process_launch_02_sha256',
                    'process_launch_03_sha256',
                    'process_launch_04_sha256',
                    'checkpoint_before_sha256',
                    'checkpoint_after_sha256',
                    'owners_before_sha256',
                    'owners_after_parent_sha256',
                    'owners_after_cold_sha256',
                    'materialization_sha256'),
 'manifest_binding_paths': {'full_scan_result_sha256': ('selected_files', 0, 'sha256'),
                            'independent_audit_sha256': ('selected_files', 1, 'sha256'),
                            'prior_review_sha256': ('selected_files', 2, 'sha256'),
                            'previous_manifest_sha256': ('selected_files', 3, 'sha256'),
                            'current_manifest_sha256': ('selected_files', 4, 'sha256'),
                            'previous_publication_sha256': ('selected_files', 5, 'sha256'),
                            'current_publication_sha256': ('selected_files', 6, 'sha256'),
                            'source_delta_sha256': ('selected_files', 7, 'sha256'),
                            'optimized_selection_sha256': ('selected_files', 8, 'sha256'),
                            'reference_selection_sha256': ('selected_files', 9, 'sha256'),
                            'optimized_root_sha256': ('selected_files', 10, 'sha256'),
                            'reference_root_sha256': ('selected_files', 11, 'sha256'),
                            'completion_sha256': ('selected_files', 12, 'sha256'),
                            'reference_page_sha256': ('selected_files', 13, 'sha256'),
                            'default_page_00_sha256': ('selected_files', 14, 'sha256'),
                            'default_page_01_sha256': ('selected_files', 15, 'sha256'),
                            'default_page_02_sha256': ('selected_files', 16, 'sha256'),
                            'default_page_03_sha256': ('selected_files', 17, 'sha256'),
                            'default_page_04_sha256': ('selected_files', 18, 'sha256'),
                            'default_page_05_sha256': ('selected_files', 19, 'sha256'),
                            'default_page_06_sha256': ('selected_files', 20, 'sha256'),
                            'default_page_07_sha256': ('selected_files', 21, 'sha256'),
                            'default_page_08_sha256': ('selected_files', 22, 'sha256'),
                            'default_page_09_sha256': ('selected_files', 23, 'sha256'),
                            'process_run_01_sha256': ('selected_files', 24, 'sha256'),
                            'process_run_02_sha256': ('selected_files', 25, 'sha256'),
                            'process_run_03_sha256': ('selected_files', 26, 'sha256'),
                            'process_run_04_sha256': ('selected_files', 27, 'sha256'),
                            'process_request_01_sha256': ('selected_files', 28, 'sha256'),
                            'process_request_02_sha256': ('selected_files', 29, 'sha256'),
                            'process_request_03_sha256': ('selected_files', 30, 'sha256'),
                            'process_request_04_sha256': ('selected_files', 31, 'sha256'),
                            'process_launch_01_sha256': ('selected_files', 32, 'sha256'),
                            'process_launch_02_sha256': ('selected_files', 33, 'sha256'),
                            'process_launch_03_sha256': ('selected_files', 34, 'sha256'),
                            'process_launch_04_sha256': ('selected_files', 35, 'sha256'),
                            'checkpoint_before_sha256': ('selected_files', 36, 'sha256'),
                            'checkpoint_after_sha256': ('selected_files', 37, 'sha256'),
                            'owners_before_sha256': ('selected_files', 38, 'sha256'),
                            'owners_after_parent_sha256': ('selected_files', 39, 'sha256'),
                            'owners_after_cold_sha256': ('selected_files', 40, 'sha256'),
                            'materialization_sha256': ('selected_files', 41, 'sha256')},
 'summary_fields': ('complete_member_count',
                    'default_page_count',
                    'default_dispositions',
                    'reference_observed_member_count',
                    'reference_first32_page',
                    'outside_reference_prefix_member_count',
                    'fresh_process_count',
                    'current_snapshot',
                    'previous_snapshot',
                    'source_delta',
                    'declared_child_role_counts',
                    'recorded_default_inferred_rows',
                    'recorded_reference_inferred_rows',
                    'runtime_fact_count',
                    'tasks_omitted_count',
                    'additional_attempted_training_epochs',
                    'new_final_assignments')}

ISOLATED_WORKFLOWS['full_successor_cohort_audit']['report_binding_paths'] = dict(
    ISOLATED_WORKFLOWS['full_successor_cohort_audit']['manifest_binding_paths'])
ISOLATED_WORKFLOWS['full_successor_cohort_audit']['report_binding_roles'] = tuple(
    field.removesuffix('_sha256') for field in ISOLATED_WORKFLOWS['full_successor_cohort_audit']['binding_fields'])

ISOLATED_WORKFLOWS['successor_receiving_custody'] = {'script': 'release_audit/successor_receiving_custody.py',
 'report': 'successor_receiving_custody.json',
 'schema': 'codebase-ir-successor-receiving-custody@1',
 'relative_inputs': True,
 'manifest_binding_field': 'manifest_sha256',
 'true_flags': ('retained_receiving_custody_conformance',
                'receiving_bindings_reconciled',
                'copied_path_relocations_reconciled',
                'native_pair_generation_advance_reconciled',
                'declared_archive_metadata_only_scope_preserved',
                'failed_whole_signed_attempts_preserved',
                'retained_cleanup_observations_reconciled',
                'unsigned_receiving_scope_preserved'),
 'false_flags': ('owner_sources_imported',
                 'owner_database_opened',
                 'profile_keys_read',
                 'network_access_performed',
                 'git_executable_invoked',
                 'source_bodies_verified',
                 'model_bodies_verified',
                 'database_bodies_verified',
                 'complete_archive_body_closure',
                 'independent_native_receiving_reperformed',
                 'numerical_execution_independently_reperformed',
                 'optimizer_replay_qualified',
                 'signed_successor_worker_qualified',
                 'signed_admission_qualified',
                 'worker_dispatch_qualified',
                 'proof_authority',
                 'source_semantics_verified',
                 'source_execution_attested',
                 'scan_execution_attested',
                 'kernel_resource_enforcement_independently_verified',
                 'live_cleanup_reobserved',
                 'process_origin_attested',
                 'production_default_activated',
                 'complete_scan_independently_reperformed',
                 'cuda_qualified',
                 '384d_qualified',
                 'signature_authentication_performed',
                 'throughput_qualified',
                 'whole_host_resource_pool_recreated'),
 'zero_fields': ('runtime_fact_count', 'tasks_omitted_count', 'additional_attempted_training_epochs'),
 'binding_fields': ('full_scan_native_sha256',
                    'full_scan_audit_sha256',
                    'actual_receiving_sha256',
                    'host_configuration_sha256',
                    'transport_controls_sha256',
                    'signed_reader_controls_sha256',
                    'failed_worker_02_native_sha256',
                    'failed_worker_02_container_sha256',
                    'failed_worker_03_native_sha256',
                    'failed_worker_03_container_sha256'),
 'manifest_binding_paths': {'full_scan_native_sha256': ('selected_files', 0, 'sha256'),
                            'full_scan_audit_sha256': ('selected_files', 1, 'sha256'),
                            'actual_receiving_sha256': ('selected_files', 2, 'sha256'),
                            'host_configuration_sha256': ('selected_files', 3, 'sha256'),
                            'transport_controls_sha256': ('selected_files', 4, 'sha256'),
                            'signed_reader_controls_sha256': ('selected_files', 5, 'sha256'),
                            'failed_worker_02_native_sha256': ('selected_files', 6, 'sha256'),
                            'failed_worker_02_container_sha256': ('selected_files', 7, 'sha256'),
                            'failed_worker_03_native_sha256': ('selected_files', 8, 'sha256'),
                            'failed_worker_03_container_sha256': ('selected_files', 9, 'sha256')},
 'summary_fields': ('selected_file_count',
                    'selected_input_bytes',
                    'receiving',
                    'failed_signed_attempts',
                    'recorded_controls',
                    'missing_body_closure',
                    'resources',
                    'runtime_fact_count',
                    'tasks_omitted_count',
                    'additional_attempted_training_epochs')}


ISOLATED_WORKFLOWS['artifact_payload_controls'] = {'script': 'acceptance/artifact_payload_controls/receiver.py',
 'report': 'artifact_payload_controls.json',
 'schema': 'codebase-ir-artifact-payload-controls@1',
 'relative_inputs': True,
 'manifest_binding_field': 'manifest_sha256',
 'true_flags': ('retained_artifact_payload_custody_conformance',
                'serialized_artifact_identity_rederived',
                'serialized_text_digests_rederived',
                'complete_artifact_metadata_preserved',
                'three_step_native_command_binding_reconciled',
                'static_v2_projection_preserved',
                'generic_unknown_authority_preserved',
                'exact_typed_payload_preserved',
                'recorded_phase_bindings_reconciled',
                'historical_raw_witness_scope_preserved',
                'historical_foreign_reference_preserved'),
 'false_flags': ('owner_database_opened',
                 'profile_keys_read',
                 'owner_sources_imported',
                 'checker_executions_replayed',
                 'source_execution_replayed',
                 'signature_authentication_performed',
                 'process_origin_attested',
                 'original_request_custody_qualified',
                 'model_check_authority_qualified',
                 'proof_authority_qualified',
                 'counterexample_replay_qualified',
                 'structural_replay_qualified',
                 'semantic_replay_qualified',
                 'source_map_semantic_truth_qualified',
                 'translation_correctness_qualified',
                 'unbounded_proof_qualified',
                 'native_v2_execution_qualified',
                 'legacy_fallback_decoder_qualified',
                 'default_registry_operation_budget_qualified',
                 'registry_native_success_qualified',
                 'resource_enforcement_qualified',
                 'hard_aggregate_containment_qualified',
                 'whole_install_cancellation_qualified',
                 'live_eligibility_qualified',
                 'production_acceptance_qualified',
                 'native_export_adoption_qualified',
                 'throughput_improvement_qualified',
                 'model_quality_qualified',
                 'output_digest_algorithm_rederived',
                 'nested_source_or_tool_bodies_opened'),
 'zero_fields': ('runtime_fact_count', 'tasks_omitted_count', 'additional_attempted_training_epochs'),
 'binding_fields': ('qualification_sha256',
                    'source_evolution_sha256',
                    'source_snapshot_sha256',
                    'execution_freeze_sha256',
                    'benchmark_preflight_sha256',
                    'joined_selected_result_sha256',
                    'native_command_result_sha256',
                    'native_command_sha256',
                    'native_result_sha256',
                    'native_fixtures_sha256',
                    'native_request_audit_sha256',
                    'native_phase_budget_audit_sha256',
                    'native_lifecycle_audit_sha256',
                    'native_apalache_environment_audit_sha256',
                    'native_launch_audit_sha256',
                    'historical_foreign_outcome_reference_sha256'),
 'manifest_binding_paths': {'qualification_sha256': ('selected_files', 0, 'sha256'),
                            'source_evolution_sha256': ('selected_files', 1, 'sha256'),
                            'source_snapshot_sha256': ('selected_files', 2, 'sha256'),
                            'execution_freeze_sha256': ('selected_files', 3, 'sha256'),
                            'benchmark_preflight_sha256': ('selected_files', 4, 'sha256'),
                            'joined_selected_result_sha256': ('selected_files', 5, 'sha256'),
                            'native_command_result_sha256': ('selected_files', 6, 'sha256'),
                            'native_command_sha256': ('selected_files', 7, 'sha256'),
                            'native_result_sha256': ('selected_files', 8, 'sha256'),
                            'native_fixtures_sha256': ('selected_files', 9, 'sha256'),
                            'native_request_audit_sha256': ('selected_files', 10, 'sha256'),
                            'native_phase_budget_audit_sha256': ('selected_files', 11, 'sha256'),
                            'native_lifecycle_audit_sha256': ('selected_files', 12, 'sha256'),
                            'native_apalache_environment_audit_sha256': ('selected_files', 13, 'sha256'),
                            'native_launch_audit_sha256': ('selected_files', 14, 'sha256'),
                            'historical_foreign_outcome_reference_sha256': ('selected_files', 15, 'sha256')},
 'report_binding_paths': {'qualification_sha256': ('selected_files', 0, 'sha256'),
                          'source_evolution_sha256': ('selected_files', 1, 'sha256'),
                          'source_snapshot_sha256': ('selected_files', 2, 'sha256'),
                          'execution_freeze_sha256': ('selected_files', 3, 'sha256'),
                          'benchmark_preflight_sha256': ('selected_files', 4, 'sha256'),
                          'joined_selected_result_sha256': ('selected_files', 5, 'sha256'),
                          'native_command_result_sha256': ('selected_files', 6, 'sha256'),
                          'native_command_sha256': ('selected_files', 7, 'sha256'),
                          'native_result_sha256': ('selected_files', 8, 'sha256'),
                          'native_fixtures_sha256': ('selected_files', 9, 'sha256'),
                          'native_request_audit_sha256': ('selected_files', 10, 'sha256'),
                          'native_phase_budget_audit_sha256': ('selected_files', 11, 'sha256'),
                          'native_lifecycle_audit_sha256': ('selected_files', 12, 'sha256'),
                          'native_apalache_environment_audit_sha256': ('selected_files', 13, 'sha256'),
                          'native_launch_audit_sha256': ('selected_files', 14, 'sha256'),
                          'historical_foreign_outcome_reference_sha256': ('selected_files', 15, 'sha256')},
 'report_binding_roles': ('qualification',
                          'source_evolution',
                          'source_snapshot',
                          'execution_freeze',
                          'benchmark_preflight',
                          'joined_selected_result',
                          'native_command_result',
                          'native_command',
                          'native_result',
                          'native_fixtures',
                          'native_request_audit',
                          'native_phase_budget_audit',
                          'native_lifecycle_audit',
                          'native_apalache_environment_audit',
                          'native_launch_audit',
                          'historical_foreign_outcome_reference'),
 'summary_fields': ('selected_file_count',
                    'selected_input_bytes',
                    'runtime_fact_count',
                    'tasks_omitted_count',
                    'additional_attempted_training_epochs')}


ISOLATED_WORKFLOWS['trace_binding_audit'] = {'script': 'corpus_audit/codebase_ir_trace_binding_audit.py',
 'report': 'trace_binding_audit.json',
 'schema': 'codebase-ir-trace-binding-audit@1',
 'relative_inputs': True,
 'manifest_binding_field': 'selected_manifest_sha256',
 'true_flags': ('retained_trace_binding_accounting_produced',
                'scalar_assignment_projection_rederived',
                'original_labels_and_positive_ordinals_preserved',
                'declared_source_symbol_bindings_reconciled',
                'historical_zero_state_gap_preserved',
                'failed_duplicate_diagnostic_trial_preserved',
                'complete_selected_test_population_reconciled'),
 'false_flags': ('owner_sources_imported',
                 'owner_database_opened',
                 'profile_keys_read',
                 'git_executable_invoked',
                 'native_parser_imported',
                 'source_execution_performed',
                 'model_execution_performed',
                 'checker_execution_reperformed',
                 'arbitrary_tla_expression_evaluated',
                 'transition_semantics_verified',
                 'invariant_semantics_verified',
                 'source_map_semantics_verified',
                 'semantic_counterexample_replay_qualified',
                 'solver_replay_performed',
                 'liveness_verified',
                 'fairness_verified',
                 'theorem_authority_qualified',
                 'generic_authority_promoted',
                 'process_origin_attested',
                 'resource_enforcement_qualified',
                 'producer_authentication_verified',
                 'whole_repository_coverage',
                 'production_default_activated',
                 'historical_receipts_rewritten',
                 'unmapped_negative_original_mapping_replayed',
                 'test_counts_additive'),
 'zero_fields': ('runtime_fact_count', 'tasks_omitted_count', 'additional_attempted_training_epochs'),
 'binding_fields': ('qualification_sha256',
                    'native_result_sha256',
                    'native_lifecycle_sha256',
                    'native_fixtures_sha256',
                    'native_request_sha256',
                    'preflight_initial_sha256',
                    'preflight_selected_sha256',
                    'historical_native_result_sha256',
                    'focused_initial_result_sha256',
                    'focused_initial_junit_sha256',
                    'focused_initial_log_sha256',
                    'focused_selected_result_sha256',
                    'focused_selected_junit_sha256',
                    'joined_selected_result_sha256',
                    'joined_selected_junit_sha256',
                    'source_evolution_sha256',
                    'report_sha256'),
 'manifest_binding_paths': {'qualification_sha256': ('selected_files', 0, 'sha256'),
                            'native_result_sha256': ('selected_files', 1, 'sha256'),
                            'native_lifecycle_sha256': ('selected_files', 2, 'sha256'),
                            'native_fixtures_sha256': ('selected_files', 3, 'sha256'),
                            'native_request_sha256': ('selected_files', 4, 'sha256'),
                            'preflight_initial_sha256': ('selected_files', 5, 'sha256'),
                            'preflight_selected_sha256': ('selected_files', 6, 'sha256'),
                            'historical_native_result_sha256': ('selected_files', 7, 'sha256'),
                            'focused_initial_result_sha256': ('selected_files', 8, 'sha256'),
                            'focused_initial_junit_sha256': ('selected_files', 9, 'sha256'),
                            'focused_initial_log_sha256': ('selected_files', 10, 'sha256'),
                            'focused_selected_result_sha256': ('selected_files', 11, 'sha256'),
                            'focused_selected_junit_sha256': ('selected_files', 12, 'sha256'),
                            'joined_selected_result_sha256': ('selected_files', 13, 'sha256'),
                            'joined_selected_junit_sha256': ('selected_files', 14, 'sha256'),
                            'source_evolution_sha256': ('selected_files', 15, 'sha256'),
                            'report_sha256': ('selected_files', 16, 'sha256')},
 'report_binding_paths': {'qualification_sha256': ('selected_files', 0, 'sha256'),
                          'native_result_sha256': ('selected_files', 1, 'sha256'),
                          'native_lifecycle_sha256': ('selected_files', 2, 'sha256'),
                          'native_fixtures_sha256': ('selected_files', 3, 'sha256'),
                          'native_request_sha256': ('selected_files', 4, 'sha256'),
                          'preflight_initial_sha256': ('selected_files', 5, 'sha256'),
                          'preflight_selected_sha256': ('selected_files', 6, 'sha256'),
                          'historical_native_result_sha256': ('selected_files', 7, 'sha256'),
                          'focused_initial_result_sha256': ('selected_files', 8, 'sha256'),
                          'focused_initial_junit_sha256': ('selected_files', 9, 'sha256'),
                          'focused_initial_log_sha256': ('selected_files', 10, 'sha256'),
                          'focused_selected_result_sha256': ('selected_files', 11, 'sha256'),
                          'focused_selected_junit_sha256': ('selected_files', 12, 'sha256'),
                          'joined_selected_result_sha256': ('selected_files', 13, 'sha256'),
                          'joined_selected_junit_sha256': ('selected_files', 14, 'sha256'),
                          'source_evolution_sha256': ('selected_files', 15, 'sha256'),
                          'report_sha256': ('selected_files', 16, 'sha256')},
 'report_binding_roles': ('qualification',
                          'native_result',
                          'native_lifecycle',
                          'native_fixtures',
                          'native_request',
                          'preflight_initial',
                          'preflight_selected',
                          'historical_native_result',
                          'focused_initial_result',
                          'focused_initial_junit',
                          'focused_initial_log',
                          'focused_selected_result',
                          'focused_selected_junit',
                          'joined_selected_result',
                          'joined_selected_junit',
                          'source_evolution',
                          'report'),
 'summary_fields': ('selected_file_count',
                    'selected_input_bytes',
                    'runtime_fact_count',
                    'tasks_omitted_count',
                    'additional_attempted_training_epochs')}


ISOLATED_WORKFLOWS['registry_operation_deadline_custody'] = {'script': 'release_audit/registry_operation_deadline_custody.py',
 'report': 'registry_operation_deadline_custody.json',
 'schema': 'codebase-ir-registry-operation-deadline-custody@1',
 'relative_inputs': True,
 'manifest_binding_field': 'manifest_sha256',
 'true_flags': ('retained_registry_deadline_custody_conformance',
                'recorded_production_deadline_bindings_reconciled',
                'complete_factory_native_phase_population_reconciled',
                'historical_request_payload_preserved',
                'generic_unknown_authority_preserved',
                'recorded_lease_cleanup_reconciled',
                'historical_test_counts_overlap_preserved',
                'historical_source_preservation_declarations_retained',
                'no_benchmark_outer_scope_declaration_preserved'),
 'false_flags': ('owner_sources_imported',
                 'owner_database_opened',
                 'profile_keys_read',
                 'network_access_performed',
                 'git_executable_invoked',
                 'source_execution_attested',
                 'process_origin_attested',
                 'live_cleanup_reobserved',
                 'automatic_current_registry_behavior_qualified',
                 'native_cancellation_execution_qualified',
                 'hard_callback_preemption_qualified',
                 'hard_aggregate_containment_qualified',
                 'standalone_availability_propagation_verified',
                 'other_native_adapter_propagation_verified',
                 'installation_cancellation_qualified',
                 'proof_authority',
                 'model_truth_qualified',
                 'source_semantics_verified',
                 'source_bodies_authenticated',
                 'selected_test_sources_authenticated',
                 'tool_bodies_authenticated',
                 'producer_authentication_verified',
                 'signature_authentication_performed',
                 'output_digest_algorithm_rederived',
                 'semantic_counterexample_replay_qualified',
                 'structural_counterexample_replay_requalified',
                 'whole_host_resources_requalified',
                 'throughput_qualified',
                 'signed_worker_qualified',
                 'production_default_activated'),
 'zero_fields': ('runtime_fact_count', 'tasks_omitted_count', 'additional_attempted_training_epochs'),
 'binding_fields': ('qualification_sha256',
                    'source_evolution_sha256',
                    'execution_freeze_sha256',
                    'native_result_sha256',
                    'native_command_result_sha256',
                    'native_command_sha256',
                    'phase_requests_sha256',
                    'phase_launches_sha256',
                    'phase_lifecycles_sha256',
                    'phase_budgets_sha256',
                    'phase_environments_sha256',
                    'fixtures_sha256',
                    'scheduler_configuration_sha256',
                    'focused_test_result_sha256',
                    'selected_test_result_sha256',
                    'preservation_before_sha256',
                    'preservation_after_sha256',
                    'source_snapshot_sha256'),
 'manifest_binding_paths': {'qualification_sha256': ('selected_files', 0, 'sha256'),
                            'source_evolution_sha256': ('selected_files', 1, 'sha256'),
                            'execution_freeze_sha256': ('selected_files', 2, 'sha256'),
                            'native_result_sha256': ('selected_files', 3, 'sha256'),
                            'native_command_result_sha256': ('selected_files', 4, 'sha256'),
                            'native_command_sha256': ('selected_files', 5, 'sha256'),
                            'phase_requests_sha256': ('selected_files', 6, 'sha256'),
                            'phase_launches_sha256': ('selected_files', 7, 'sha256'),
                            'phase_lifecycles_sha256': ('selected_files', 8, 'sha256'),
                            'phase_budgets_sha256': ('selected_files', 9, 'sha256'),
                            'phase_environments_sha256': ('selected_files', 10, 'sha256'),
                            'fixtures_sha256': ('selected_files', 11, 'sha256'),
                            'scheduler_configuration_sha256': ('selected_files', 12, 'sha256'),
                            'focused_test_result_sha256': ('selected_files', 13, 'sha256'),
                            'selected_test_result_sha256': ('selected_files', 14, 'sha256'),
                            'preservation_before_sha256': ('selected_files', 15, 'sha256'),
                            'preservation_after_sha256': ('selected_files', 16, 'sha256'),
                            'source_snapshot_sha256': ('selected_files', 17, 'sha256')},
 'report_binding_paths': {'qualification_sha256': ('selected_files', 0, 'sha256'),
                          'source_evolution_sha256': ('selected_files', 1, 'sha256'),
                          'execution_freeze_sha256': ('selected_files', 2, 'sha256'),
                          'native_result_sha256': ('selected_files', 3, 'sha256'),
                          'native_command_result_sha256': ('selected_files', 4, 'sha256'),
                          'native_command_sha256': ('selected_files', 5, 'sha256'),
                          'phase_requests_sha256': ('selected_files', 6, 'sha256'),
                          'phase_launches_sha256': ('selected_files', 7, 'sha256'),
                          'phase_lifecycles_sha256': ('selected_files', 8, 'sha256'),
                          'phase_budgets_sha256': ('selected_files', 9, 'sha256'),
                          'phase_environments_sha256': ('selected_files', 10, 'sha256'),
                          'fixtures_sha256': ('selected_files', 11, 'sha256'),
                          'scheduler_configuration_sha256': ('selected_files', 12, 'sha256'),
                          'focused_test_result_sha256': ('selected_files', 13, 'sha256'),
                          'selected_test_result_sha256': ('selected_files', 14, 'sha256'),
                          'preservation_before_sha256': ('selected_files', 15, 'sha256'),
                          'preservation_after_sha256': ('selected_files', 16, 'sha256'),
                          'source_snapshot_sha256': ('selected_files', 17, 'sha256')},
 'report_binding_roles': ('qualification',
                          'source_evolution',
                          'execution_freeze',
                          'native_result',
                          'native_command_result',
                          'native_command',
                          'phase_requests',
                          'phase_launches',
                          'phase_lifecycles',
                          'phase_budgets',
                          'phase_environments',
                          'fixtures',
                          'scheduler_configuration',
                          'focused_test_result',
                          'selected_test_result',
                          'preservation_before',
                          'preservation_after',
                          'source_snapshot'),
 'summary_fields': ('selected_file_count',
                    'selected_input_bytes',
                    'runtime_fact_count',
                    'tasks_omitted_count',
                    'additional_attempted_training_epochs')}


ISOLATED_WORKFLOWS['signed_worker_acceptance_controls'] = {'script': 'acceptance/signed_worker_acceptance_controls/receiver.py',
 'report': 'signed_worker_acceptance_controls.json',
 'schema': 'codebase-ir-signed-worker-acceptance-controls@1',
 'relative_inputs': True,
 'manifest_binding_field': 'manifest_sha256',
 'true_flags': ('retained_signed_worker_metadata_custody_conformance',
                'signed_task_population_preserved',
                'public_artifact_transport_preserved',
                'signed_declaration_bindings_reconciled',
                'prerequisite_and_completion_bindings_reconciled',
                'worker_output_receipt_bindings_reconciled',
                'publication_checks_reconciled',
                'typed_stale_observation_preserved',
                'historical_qualification_scopes_preserved',
                'input_files_unchanged'),
 'false_flags': ('native_execution_performed',
                 'training_executed',
                 'current_authority_claimed',
                 'owner_database_opened',
                 'profile_keys_read',
                 'owner_sources_imported',
                 'signature_authentication_performed',
                 'public_signatures_cryptographically_verified',
                 'process_origin_attested',
                 'worker_identity_authenticated',
                 'worker_execution_qualified',
                 'native_admission_reperformed',
                 'native_task_completion_authenticated',
                 'proposal_policy_executed',
                 'source_execution_replayed',
                 'source_semantics_verified',
                 'intent_correspondence_verified',
                 'physical_worker_absence_verified',
                 'container_enforcement_qualified',
                 'resource_enforcement_qualified',
                 'native_git_publication_reperformed',
                 'public_checks_executed',
                 'source_generation_invalidation_reperformed',
                 'complete_scan_reexecuted',
                 'numerical_execution_reperformed',
                 'model_quality_qualified',
                 'live_eligibility_qualified',
                 'production_acceptance_qualified',
                 'production_default_activated',
                 'throughput_improvement_qualified',
                 'general_crash_recovery_qualified',
                 'full_archive_custody_qualified',
                 'nested_referenced_bodies_opened',
                 'proof_authority_qualified',
                 'behavioral_satisfaction_qualified',
                 'task_omission_authority_qualified'),
 'zero_fields': ('runtime_fact_count',
                 'tasks_omitted_count',
                 'additional_attempted_training_epochs',
                 'additional_fit_attempt_count',
                 'additional_inference_attempt_count',
                 'additional_scan_page_count',
                 'additional_reference_page_count',
                 'additional_provider_call_count'),
 'binding_fields': ('historical_source_successor_review_sha256',
                    'successor_expansion_review_sha256',
                    'native_result_sha256',
                    'native_admission_sha256',
                    'current_admission_verification_sha256',
                    'signed_manifest_sha256',
                    'raw_public_worker_artifact_sha256',
                    'decoded_public_worker_artifact_sha256',
                    'public_worker_context_sha256',
                    'authored_worker_receipt_sha256',
                    'execution_scope_before_sha256',
                    'execution_scope_after_stop_sha256',
                    'native_lifecycle_sha256',
                    'worker_candidate_sha256',
                    'prerequisite_claim_sha256',
                    'prerequisite_validation_sha256',
                    'published_public_checks_sha256',
                    'published_source_receipt_sha256',
                    'container_boundary_sha256',
                    'worker_stdout_log_sha256'),
 'manifest_binding_paths': {'historical_source_successor_review_sha256': ('selected_files',
                                                                          0,
                                                                          'sha256'),
                            'successor_expansion_review_sha256': ('selected_files',
                                                                  1,
                                                                  'sha256'),
                            'native_result_sha256': ('selected_files',
                                                     2,
                                                     'sha256'),
                            'native_admission_sha256': ('selected_files',
                                                        3,
                                                        'sha256'),
                            'current_admission_verification_sha256': ('selected_files',
                                                                      4,
                                                                      'sha256'),
                            'signed_manifest_sha256': ('selected_files',
                                                       5,
                                                       'sha256'),
                            'raw_public_worker_artifact_sha256': ('selected_files',
                                                                  6,
                                                                  'sha256'),
                            'decoded_public_worker_artifact_sha256': ('selected_files',
                                                                      7,
                                                                      'sha256'),
                            'public_worker_context_sha256': ('selected_files',
                                                             8,
                                                             'sha256'),
                            'authored_worker_receipt_sha256': ('selected_files',
                                                               9,
                                                               'sha256'),
                            'execution_scope_before_sha256': ('selected_files',
                                                              10,
                                                              'sha256'),
                            'execution_scope_after_stop_sha256': ('selected_files',
                                                                  11,
                                                                  'sha256'),
                            'native_lifecycle_sha256': ('selected_files',
                                                        12,
                                                        'sha256'),
                            'worker_candidate_sha256': ('selected_files',
                                                        13,
                                                        'sha256'),
                            'prerequisite_claim_sha256': ('selected_files',
                                                          14,
                                                          'sha256'),
                            'prerequisite_validation_sha256': ('selected_files',
                                                               15,
                                                               'sha256'),
                            'published_public_checks_sha256': ('selected_files',
                                                               16,
                                                               'sha256'),
                            'published_source_receipt_sha256': ('selected_files',
                                                                17,
                                                                'sha256'),
                            'container_boundary_sha256': ('selected_files',
                                                          18,
                                                          'sha256'),
                            'worker_stdout_log_sha256': ('selected_files',
                                                         19,
                                                         'sha256')},
 'report_binding_paths': {'historical_source_successor_review_sha256': ('selected_files',
                                                                        0,
                                                                        'sha256'),
                          'successor_expansion_review_sha256': ('selected_files',
                                                                1,
                                                                'sha256'),
                          'native_result_sha256': ('selected_files',
                                                   2,
                                                   'sha256'),
                          'native_admission_sha256': ('selected_files',
                                                      3,
                                                      'sha256'),
                          'current_admission_verification_sha256': ('selected_files',
                                                                    4,
                                                                    'sha256'),
                          'signed_manifest_sha256': ('selected_files',
                                                     5,
                                                     'sha256'),
                          'raw_public_worker_artifact_sha256': ('selected_files',
                                                                6,
                                                                'sha256'),
                          'decoded_public_worker_artifact_sha256': ('selected_files',
                                                                    7,
                                                                    'sha256'),
                          'public_worker_context_sha256': ('selected_files',
                                                           8,
                                                           'sha256'),
                          'authored_worker_receipt_sha256': ('selected_files',
                                                             9,
                                                             'sha256'),
                          'execution_scope_before_sha256': ('selected_files',
                                                            10,
                                                            'sha256'),
                          'execution_scope_after_stop_sha256': ('selected_files',
                                                                11,
                                                                'sha256'),
                          'native_lifecycle_sha256': ('selected_files',
                                                      12,
                                                      'sha256'),
                          'worker_candidate_sha256': ('selected_files',
                                                      13,
                                                      'sha256'),
                          'prerequisite_claim_sha256': ('selected_files',
                                                        14,
                                                        'sha256'),
                          'prerequisite_validation_sha256': ('selected_files',
                                                             15,
                                                             'sha256'),
                          'published_public_checks_sha256': ('selected_files',
                                                             16,
                                                             'sha256'),
                          'published_source_receipt_sha256': ('selected_files',
                                                              17,
                                                              'sha256'),
                          'container_boundary_sha256': ('selected_files',
                                                        18,
                                                        'sha256'),
                          'worker_stdout_log_sha256': ('selected_files',
                                                       19,
                                                       'sha256')},
 'report_binding_roles': ('historical_source_successor_review',
                          'successor_expansion_review',
                          'native_result',
                          'native_admission',
                          'current_admission_verification',
                          'signed_manifest',
                          'raw_public_worker_artifact',
                          'decoded_public_worker_artifact',
                          'public_worker_context',
                          'authored_worker_receipt',
                          'execution_scope_before',
                          'execution_scope_after_stop',
                          'native_lifecycle',
                          'worker_candidate',
                          'prerequisite_claim',
                          'prerequisite_validation',
                          'published_public_checks',
                          'published_source_receipt',
                          'container_boundary',
                          'worker_stdout_log'),
 'summary_fields': ('selected_file_count',
                    'selected_input_bytes',
                    'runtime_fact_count',
                    'tasks_omitted_count',
                    'additional_attempted_training_epochs')}

ISOLATED_WORKFLOWS['publication_dependency_audit'] = {'script': 'corpus_audit/codebase_ir_publication_dependency_audit.py',
 'report': 'publication_dependency_audit.json',
 'schema': 'codebase-ir-publication-dependency-audit@1',
 'relative_inputs': True,
 'manifest_binding_field': 'manifest_sha256',
 'true_flags': ('retained_publication_dependency_accounting_produced',
                'complete_selected_capture_population_reconciled',
                'stable_symbol_population_reconciled',
                'declared_reverse_dependency_frontier_rederived',
                'fixed_archived_source_syntax_rederived',
                'inherited_scan_head_staleness_reconciled',
                'legacy_catalog_count_observations_preserved',
                'input_files_unchanged'),
 'false_flags': ('native_execution_performed',
                 'training_executed',
                 'current_authority_claimed',
                 'owner_sources_imported',
                 'owner_database_opened',
                 'profile_keys_read',
                 'git_executable_invoked',
                 'source_execution_performed',
                 'model_execution_performed',
                 'native_parser_imported',
                 'source_semantics_verified',
                 'source_intent_verified',
                 'behavioral_equivalence_verified',
                 'behavioral_difference_verified',
                 'native_invalidation_completeness_verified',
                 'semantic_state_identity_recipe_verified',
                 'stable_symbol_identity_recipe_verified',
                 'dependency_semantics_verified',
                 'unresolved_dependency_frontiers_closed',
                 'stale_head_refusal_reperformed',
                 'new_scan_performed',
                 'all_source_bodies_reopened',
                 'physical_published_worktree_verified',
                 'whole_repository_coverage',
                 'model_quality_qualified',
                 'full_transitive_dependency_attestation',
                 'producer_authentication_verified',
                 'process_origin_attested',
                 'production_default_activated',
                 'production_acceptance_closed',
                 'historical_receipts_rewritten'),
 'zero_fields': ('runtime_fact_count',
                 'tasks_omitted_count',
                 'additional_attempted_training_epochs'),
 'binding_fields': ('native_result_sha256',
                    'published_source_receipt_sha256',
                    'owners_before_sha256',
                    'owners_after_sha256',
                    'inherited_scan_root_sha256',
                    'inherited_scan_completion_sha256',
                    'generation2_manifest_sha256',
                    'generation3_manifest_sha256',
                    'generation2_calc_source_sha256',
                    'generation3_calc_source_sha256',
                    'generation2_calc_ast_sha256',
                    'generation3_calc_ast_sha256',
                    'expansion_review_sha256'),
 'manifest_binding_paths': {'native_result_sha256': ('selected_files',
                                                     0,
                                                     'sha256'),
                            'published_source_receipt_sha256': ('selected_files',
                                                                1,
                                                                'sha256'),
                            'owners_before_sha256': ('selected_files',
                                                     2,
                                                     'sha256'),
                            'owners_after_sha256': ('selected_files',
                                                    3,
                                                    'sha256'),
                            'inherited_scan_root_sha256': ('selected_files',
                                                           4,
                                                           'sha256'),
                            'inherited_scan_completion_sha256': ('selected_files',
                                                                 5,
                                                                 'sha256'),
                            'generation2_manifest_sha256': ('selected_files',
                                                            6,
                                                            'sha256'),
                            'generation3_manifest_sha256': ('selected_files',
                                                            7,
                                                            'sha256'),
                            'generation2_calc_source_sha256': ('selected_files',
                                                               8,
                                                               'sha256'),
                            'generation3_calc_source_sha256': ('selected_files',
                                                               9,
                                                               'sha256'),
                            'generation2_calc_ast_sha256': ('selected_files',
                                                            10,
                                                            'sha256'),
                            'generation3_calc_ast_sha256': ('selected_files',
                                                            11,
                                                            'sha256'),
                            'expansion_review_sha256': ('selected_files',
                                                        12,
                                                        'sha256')},
 'report_binding_paths': {'native_result_sha256': ('selected_files',
                                                   0,
                                                   'sha256'),
                          'published_source_receipt_sha256': ('selected_files',
                                                              1,
                                                              'sha256'),
                          'owners_before_sha256': ('selected_files',
                                                   2,
                                                   'sha256'),
                          'owners_after_sha256': ('selected_files',
                                                  3,
                                                  'sha256'),
                          'inherited_scan_root_sha256': ('selected_files',
                                                         4,
                                                         'sha256'),
                          'inherited_scan_completion_sha256': ('selected_files',
                                                               5,
                                                               'sha256'),
                          'generation2_manifest_sha256': ('selected_files',
                                                          6,
                                                          'sha256'),
                          'generation3_manifest_sha256': ('selected_files',
                                                          7,
                                                          'sha256'),
                          'generation2_calc_source_sha256': ('selected_files',
                                                             8,
                                                             'sha256'),
                          'generation3_calc_source_sha256': ('selected_files',
                                                             9,
                                                             'sha256'),
                          'generation2_calc_ast_sha256': ('selected_files',
                                                          10,
                                                          'sha256'),
                          'generation3_calc_ast_sha256': ('selected_files',
                                                          11,
                                                          'sha256'),
                          'expansion_review_sha256': ('selected_files',
                                                      12,
                                                      'sha256')},
 'report_binding_roles': ('native_result',
                          'published_source_receipt',
                          'owners_before',
                          'owners_after',
                          'inherited_scan_root',
                          'inherited_scan_completion',
                          'generation2_manifest',
                          'generation3_manifest',
                          'generation2_calc_source',
                          'generation3_calc_source',
                          'generation2_calc_ast',
                          'generation3_calc_ast',
                          'expansion_review'),
 'summary_fields': ('selected_file_count',
                    'selected_input_bytes',
                    'runtime_fact_count',
                    'tasks_omitted_count',
                    'additional_attempted_training_epochs')}

ISOLATED_WORKFLOWS['native_operation_inheritance_custody'] = {'script': 'release_audit/native_operation_inheritance_custody.py',
 'report': 'native_operation_inheritance_custody.json',
 'schema': 'codebase-ir-native-operation-inheritance-custody@1',
 'relative_inputs': True,
 'manifest_binding_field': 'manifest_sha256',
 'true_flags': ('retained_ambient_native_inheritance_custody_conformance',
                'six_admitted_phase_population_reconciled',
                'earlier_deadline_and_cpu_tightening_reconciled',
                'inherited_signal_without_explicit_forwarding_preserved',
                'python_transport_logical_stops_preserved',
                'normally_completed_kernel_population_preserved',
                'historical_native_request_limits_preserved',
                'recorded_scoped_cleanup_reconciled',
                'whole_failed_attempt_metadata_preserved',
                'prior_selected_case_population_reconciled',
                'overlapping_test_counts_not_added',
                'source_evolution_declarations_retained',
                'input_files_unchanged'),
 'false_flags': ('native_execution_performed',
                 'training_executed',
                 'current_authority_claimed',
                 'owner_sources_imported',
                 'owner_database_opened',
                 'profile_keys_read',
                 'network_access_performed',
                 'git_executable_invoked',
                 'native_transport_reexecuted',
                 'current_admitted_runner_behavior_qualified',
                 'native_kernel_cancellation_qualified',
                 'native_isabelle_execution_qualified',
                 'atp_proverif_tamarin_admission_qualified',
                 'plain_injected_runner_behavior_qualified',
                 'hard_callback_preemption_qualified',
                 'hard_aggregate_containment_qualified',
                 'whole_installer_cancellation_qualified',
                 'parallel_speedup_qualified',
                 'semantic_trace_replay_qualified',
                 'proof_authority',
                 'model_truth_qualified',
                 'producer_authentication_verified',
                 'process_origin_attested',
                 'current_live_pid_reobserved',
                 'live_cleanup_reobserved',
                 'source_bodies_authenticated',
                 'test_source_assertions_unchanged_verified',
                 'benchmark_import_order_reexecuted',
                 'selected_tools_authenticated',
                 'shared_libraries_attested',
                 'signature_authentication_performed',
                 'signed_worker_qualified',
                 'output_digest_algorithm_rederived',
                 'production_default_activated'),
 'zero_fields': ('runtime_fact_count',
                 'tasks_omitted_count',
                 'additional_attempted_training_epochs'),
 'binding_fields': ('qualification_sha256',
                    'prior_registry_qualification_sha256',
                    'source_evolution_sha256',
                    'test_source_evolution_sha256',
                    'benchmark_source_evolution_sha256',
                    'initial_execution_freeze_sha256',
                    'selected_execution_freeze_sha256',
                    'selected_preflight_sha256',
                    'initial_native_command_result_sha256',
                    'initial_native_command_sha256',
                    'initial_native_log_sha256',
                    'selected_native_command_result_sha256',
                    'selected_native_command_sha256',
                    'native_result_sha256',
                    'native_requests_sha256',
                    'native_invocations_sha256',
                    'native_launches_sha256',
                    'native_live_processes_sha256',
                    'native_lifecycles_sha256',
                    'scheduler_configuration_sha256',
                    'focused_initial_test_result_sha256',
                    'focused_selected_test_result_sha256',
                    'joined_selected_test_result_sha256',
                    'focused_final_test_result_sha256',
                    'joined_final_test_result_sha256',
                    'preservation_before_sha256',
                    'preservation_after_sha256'),
 'manifest_binding_paths': {'qualification_sha256': ('selected_files',
                                                     0,
                                                     'sha256'),
                            'prior_registry_qualification_sha256': ('selected_files',
                                                                    1,
                                                                    'sha256'),
                            'source_evolution_sha256': ('selected_files',
                                                        2,
                                                        'sha256'),
                            'test_source_evolution_sha256': ('selected_files',
                                                             3,
                                                             'sha256'),
                            'benchmark_source_evolution_sha256': ('selected_files',
                                                                  4,
                                                                  'sha256'),
                            'initial_execution_freeze_sha256': ('selected_files',
                                                                5,
                                                                'sha256'),
                            'selected_execution_freeze_sha256': ('selected_files',
                                                                 6,
                                                                 'sha256'),
                            'selected_preflight_sha256': ('selected_files',
                                                          7,
                                                          'sha256'),
                            'initial_native_command_result_sha256': ('selected_files',
                                                                     8,
                                                                     'sha256'),
                            'initial_native_command_sha256': ('selected_files',
                                                              9,
                                                              'sha256'),
                            'initial_native_log_sha256': ('selected_files',
                                                          10,
                                                          'sha256'),
                            'selected_native_command_result_sha256': ('selected_files',
                                                                      11,
                                                                      'sha256'),
                            'selected_native_command_sha256': ('selected_files',
                                                               12,
                                                               'sha256'),
                            'native_result_sha256': ('selected_files',
                                                     13,
                                                     'sha256'),
                            'native_requests_sha256': ('selected_files',
                                                       14,
                                                       'sha256'),
                            'native_invocations_sha256': ('selected_files',
                                                          15,
                                                          'sha256'),
                            'native_launches_sha256': ('selected_files',
                                                       16,
                                                       'sha256'),
                            'native_live_processes_sha256': ('selected_files',
                                                             17,
                                                             'sha256'),
                            'native_lifecycles_sha256': ('selected_files',
                                                         18,
                                                         'sha256'),
                            'scheduler_configuration_sha256': ('selected_files',
                                                               19,
                                                               'sha256'),
                            'focused_initial_test_result_sha256': ('selected_files',
                                                                   20,
                                                                   'sha256'),
                            'focused_selected_test_result_sha256': ('selected_files',
                                                                    21,
                                                                    'sha256'),
                            'joined_selected_test_result_sha256': ('selected_files',
                                                                   22,
                                                                   'sha256'),
                            'focused_final_test_result_sha256': ('selected_files',
                                                                 23,
                                                                 'sha256'),
                            'joined_final_test_result_sha256': ('selected_files',
                                                                24,
                                                                'sha256'),
                            'preservation_before_sha256': ('selected_files',
                                                           25,
                                                           'sha256'),
                            'preservation_after_sha256': ('selected_files',
                                                          26,
                                                          'sha256')},
 'report_binding_paths': {'qualification_sha256': ('selected_files',
                                                   0,
                                                   'sha256'),
                          'prior_registry_qualification_sha256': ('selected_files',
                                                                  1,
                                                                  'sha256'),
                          'source_evolution_sha256': ('selected_files',
                                                      2,
                                                      'sha256'),
                          'test_source_evolution_sha256': ('selected_files',
                                                           3,
                                                           'sha256'),
                          'benchmark_source_evolution_sha256': ('selected_files',
                                                                4,
                                                                'sha256'),
                          'initial_execution_freeze_sha256': ('selected_files',
                                                              5,
                                                              'sha256'),
                          'selected_execution_freeze_sha256': ('selected_files',
                                                               6,
                                                               'sha256'),
                          'selected_preflight_sha256': ('selected_files',
                                                        7,
                                                        'sha256'),
                          'initial_native_command_result_sha256': ('selected_files',
                                                                   8,
                                                                   'sha256'),
                          'initial_native_command_sha256': ('selected_files',
                                                            9,
                                                            'sha256'),
                          'initial_native_log_sha256': ('selected_files',
                                                        10,
                                                        'sha256'),
                          'selected_native_command_result_sha256': ('selected_files',
                                                                    11,
                                                                    'sha256'),
                          'selected_native_command_sha256': ('selected_files',
                                                             12,
                                                             'sha256'),
                          'native_result_sha256': ('selected_files',
                                                   13,
                                                   'sha256'),
                          'native_requests_sha256': ('selected_files',
                                                     14,
                                                     'sha256'),
                          'native_invocations_sha256': ('selected_files',
                                                        15,
                                                        'sha256'),
                          'native_launches_sha256': ('selected_files',
                                                     16,
                                                     'sha256'),
                          'native_live_processes_sha256': ('selected_files',
                                                           17,
                                                           'sha256'),
                          'native_lifecycles_sha256': ('selected_files',
                                                       18,
                                                       'sha256'),
                          'scheduler_configuration_sha256': ('selected_files',
                                                             19,
                                                             'sha256'),
                          'focused_initial_test_result_sha256': ('selected_files',
                                                                 20,
                                                                 'sha256'),
                          'focused_selected_test_result_sha256': ('selected_files',
                                                                  21,
                                                                  'sha256'),
                          'joined_selected_test_result_sha256': ('selected_files',
                                                                 22,
                                                                 'sha256'),
                          'focused_final_test_result_sha256': ('selected_files',
                                                               23,
                                                               'sha256'),
                          'joined_final_test_result_sha256': ('selected_files',
                                                              24,
                                                              'sha256'),
                          'preservation_before_sha256': ('selected_files',
                                                         25,
                                                         'sha256'),
                          'preservation_after_sha256': ('selected_files',
                                                        26,
                                                        'sha256')},
 'report_binding_roles': ('qualification',
                          'prior_registry_qualification',
                          'source_evolution',
                          'test_source_evolution',
                          'benchmark_source_evolution',
                          'initial_execution_freeze',
                          'selected_execution_freeze',
                          'selected_preflight',
                          'initial_native_command_result',
                          'initial_native_command',
                          'initial_native_log',
                          'selected_native_command_result',
                          'selected_native_command',
                          'native_result',
                          'native_requests',
                          'native_invocations',
                          'native_launches',
                          'native_live_processes',
                          'native_lifecycles',
                          'scheduler_configuration',
                          'focused_initial_test_result',
                          'focused_selected_test_result',
                          'joined_selected_test_result',
                          'focused_final_test_result',
                          'joined_final_test_result',
                          'preservation_before',
                          'preservation_after'),
 'summary_fields': ('selected_file_count',
                    'selected_input_bytes',
                    'runtime_fact_count',
                    'tasks_omitted_count',
                    'additional_attempted_training_epochs')}


def workflow_report_binding(workflow: str, payload: dict, field: str):
    """Read a report digest from its declared field or nested selected row."""
    path = ISOLATED_WORKFLOWS[workflow].get("report_binding_paths", {}).get(field)
    if path is None:
        return payload.get(field)
    value = payload
    for selector in path:
        if type(selector) is str and type(value) is dict and selector in value:
            value = value[selector]
        elif type(selector) is int and type(value) is list and 0 <= selector < len(value):
            value = value[selector]
        else:
            return None
    return value


def isolated_workflow_passed(payload: dict, workflow: str, manifest_sha256: str,
                             additional_bindings: dict | None = None) -> bool:
    """Bind private qualification results to their inputs and limited scope."""
    profile = ISOLATED_WORKFLOWS[workflow]
    if (type(payload) is not dict
            or not isinstance(manifest_sha256, str)
            or not re.fullmatch(r"[0-9a-f]{64}", manifest_sha256)):
        return False
    bindings = {} if additional_bindings is None else additional_bindings
    roles = profile.get("report_binding_roles")
    if roles is not None:
        rows = payload.get("selected_files")
        if (type(rows) is not list or len(rows) != len(roles)
                or any(type(row) is not dict or row.get("role") != role for row, role in zip(rows, roles, strict=True))):
            return False
    if (type(bindings) is not dict or set(bindings) != set(profile.get("binding_fields", ()))
            or any(type(value) is not str or not re.fullmatch(r"[0-9a-f]{64}", value)
                   or workflow_report_binding(workflow, payload, field) != value for field, value in bindings.items())):
        return False
    return (payload.get("schema") == profile["schema"]
            and payload.get("status") == "passed"
            and payload.get(profile.get("manifest_binding_field", "manifest_sha256")) == manifest_sha256
            and payload.get("input_files_unchanged") is True
            and all(payload.get(field) is True for field in profile.get("true_flags", ()))
            and all(type(payload.get(field)) is int and payload[field] == 0
                    for field in profile.get("zero_fields", ()))
            and all(payload.get(field) is False for field in (
                "native_execution_performed", "training_executed", "current_authority_claimed",
                *profile["false_flags"])))


def workflow_manifest_bindings(workflow: str, manifest: dict) -> dict[str, str]:
    """Read expected result pins from the retained input, independently of its report."""
    bindings = {}
    for field, path in ISOLATED_WORKFLOWS[workflow].get("manifest_binding_paths", {}).items():
        value = manifest
        for component in path:
            if type(value) is dict and type(component) is str and component in value:
                value = value[component]
            elif type(value) is list and type(component) is int and 0 <= component < len(value):
                value = value[component]
            else:
                raise ValueError(f"missing manifest binding: {field}")
        if type(value) is not str or not re.fullmatch(r"[0-9a-f]{64}", value):
            raise ValueError(f"invalid manifest SHA256 binding: {field}")
        bindings[field] = value
    return bindings


def file_hash(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read_report(path: Path) -> tuple[bytes, dict]:
    """Read one stable, bounded regular JSON object without ambiguous fields."""
    def object_pairs(pairs):
        result = {}
        for key, value in pairs:
            if key in result:
                raise ValueError("duplicate report field")
            result[key] = value
        return result

    def reject_constant(value):
        raise ValueError(f"non-finite report constant: {value}")

    def finite_float(value):
        parsed = float(value)
        if not math.isfinite(parsed):
            raise ValueError("non-finite report number")
        return parsed

    descriptor = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
    with os.fdopen(descriptor, "rb") as stream:
        before = os.fstat(stream.fileno())
        if not stat.S_ISREG(before.st_mode) or before.st_size > MAX_REPORT_BYTES:
            raise ValueError("report must be a regular JSON file of at most 16 MiB")
        raw = stream.read(MAX_REPORT_BYTES + 1)
        after = os.fstat(stream.fileno())
    if (len(raw) > MAX_REPORT_BYTES or len(raw) != before.st_size
            or (before.st_dev, before.st_ino, before.st_size, before.st_mtime_ns, before.st_ctime_ns)
            != (after.st_dev, after.st_ino, after.st_size, after.st_mtime_ns, after.st_ctime_ns)):
        raise ValueError("report changed during its bounded read")
    value = json.loads(raw, object_pairs_hook=object_pairs, parse_constant=reject_constant,
                       parse_float=finite_float)
    if type(value) is not dict:
        raise ValueError("report must contain a JSON object")
    return raw, value


def retain_input(path: Path, target: Path) -> dict:
    """Copy a bounded JSON workflow input and pin the exact retained bytes."""
    raw, _ = read_report(path)
    target.write_bytes(raw)
    return {"path": str(path.absolute()), "retained_as": target.name,
            "sha256": hashlib.sha256(raw).hexdigest()}


def input_pin_unchanged(pin: dict) -> bool:
    """Recheck an original spec when its relative inputs require that location."""
    try:
        raw, _ = read_report(Path(pin["path"]))
        return hashlib.sha256(raw).hexdigest() == pin["sha256"]
    except (OSError, ValueError, RecursionError):
        return False


def changed_workflow_pins(pins: dict) -> list[str]:
    """Include the separate original FINAL lock in completion-time stability checks."""
    return [name for name, pin in pins.items()
            if name in {*ISOLATED_WORKFLOWS, "final_protocol_lock"} and not input_pin_unchanged(pin)]


def historical_replay_passed(history: dict, roots: list[Path] | None, identity: str | None) -> bool:
    """Keep a requested historical check bound to its source and limited authority."""
    if (type(history) is not dict or history.get("status") != "passed"
            or any(history.get(field) is not False for field in (
                "observed_current", "current_launch_permission_claimed", "task_store_opened",
                "native_observation_or_proof_invoked", "worker_launched"))
            or type(history.get("training_steps")) is not int or history["training_steps"] != 0):
        return False
    if not roots:
        return True
    expected_roots = [str(root.absolute()) for root in roots]
    if (history.get("runtime_source_mode") != "sealed_snapshot_read_only"
            or history.get("runtime_snapshot_roots") != expected_roots
            or history.get("requested_runtime_snapshot_sha256") != identity
            or history.get("runtime_snapshot_identity_stable") is not True
            or history.get("read_files_unchanged") is not True):
        return False
    before, after = history.get("runtime_snapshot_before"), history.get("runtime_snapshot_after")
    if (type(before) is not dict or before != after or before.get("verified") is not True
            or before.get("snapshot_sha256") != identity or before.get("snapshot_roots") != expected_roots):
        return False
    comparison = history.get("retained_producer_comparison")
    if type(comparison) is not dict or set(comparison) != {"signed_producer", "model_frontend"}:
        return False
    for name, count in (("signed_producer", 6), ("model_frontend", 9)):
        group = comparison[name]
        if (type(group) is not dict or type(group.get("expected_count")) is not int
                or group["expected_count"] != count or group.get("all_match") is not True
                or type(group.get("pins")) is not list or len(group["pins"]) != count):
            return False
        modules = [pin.get("module") for pin in group["pins"] if type(pin) is dict]
        if any(type(module) is not str or not module for module in modules) or len(set(modules)) != count:
            return False
        for pin in group["pins"]:
            if (type(pin) is not dict or pin.get("matches_retained_pin") is not True
                    or type(pin.get("actual_preexec_pin")) is not dict
                    or not isinstance(pin.get("expected_sha256"), str)
                    or not re.fullmatch(r"[0-9a-f]{64}", pin["expected_sha256"])
                    or pin["actual_preexec_pin"].get("sha256") != pin["expected_sha256"]):
                return False
    return True


def run_step(name: str, argv: list[str], cwd: Path, output: Path,
             expected_returncode: int = 0, timeout: int = 180) -> dict:
    """Retain command output and terminate the entire child group on timeout."""
    start = time.monotonic()
    log = output / f"{name}.log"
    env = dict(os.environ)
    env.pop("PYTHONPATH", None)
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    env["OMP_NUM_THREADS"] = "1"
    env["OPENBLAS_NUM_THREADS"] = "1"
    timed_out = False
    with log.open("wb") as stream:
        child = subprocess.Popen(argv, cwd=cwd, env=env, stdout=stream,
                                 stderr=subprocess.STDOUT, start_new_session=True)
        try:
            returncode = child.wait(timeout=timeout)
        except subprocess.TimeoutExpired:
            timed_out = True
            os.killpg(child.pid, signal.SIGKILL)
            returncode = child.wait()
    row = {"name": name, "argv": argv, "returncode": returncode,
           "expected_returncode": expected_returncode, "timed_out": timed_out,
           "seconds": round(time.monotonic() - start, 3), "log": log.name,
           "passed": not timed_out and returncode == expected_returncode}
    if name.endswith("-tests"):
        captured = log.read_text(errors="replace")
        match = re.search(r"Ran (\d+) tests? in", captured)
        row["test_count"] = int(match.group(1)) if match else 0
        skipped = re.search(r"skipped=(\d+)", captured)
        row["skipped_count"] = int(skipped.group(1)) if skipped else 0
        row["passed"] = row["passed"] and row["test_count"] > 0
    print(f"{name}: {'passed' if row['passed'] else 'failed'} ({row['seconds']}s)", flush=True)
    return row


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, help="New output directory; existing paths are refused")
    parser.add_argument("--release-audit", action="store_true",
                        help="Also scan working dependency closures and reviewed releases")
    parser.add_argument("--probe-imports", action="store_true",
                        help="Probe release-audit snapshots in isolated bounded children")
    parser.add_argument("--runtime-demand", action="store_true",
                        help="Qualify service imports using bounded demand-captured snapshots")
    parser.add_argument("--runtime-config", type=Path,
                        help="Explicit runtime probe config; default is the service import profile")
    parser.add_argument("--runtime-observed-report", type=Path,
                        help="Generate a source-pinned invocation config from a retained planning report")
    parser.add_argument("--runtime-initial-snapshot", type=Path,
                        help="Reuse an explicitly pinned sealed generation during runtime demand capture")
    parser.add_argument("--runtime-initial-snapshot-sha256",
                        help="Exact generation identity required for --runtime-initial-snapshot")
    parser.add_argument("--external-from-report", type=Path,
                        help="Generate external dependency pins from a retained planning report without imports")
    parser.add_argument("--external-python", type=Path,
                        help="Interpreter whose site-package roots must match the external pin report")
    parser.add_argument("--source-metadata-manifest", type=Path,
                        help="Reconstruct candidate metadata from this pinned corpus audit manifest")
    parser.add_argument("--source-metadata-supplement", type=Path,
                        help="Additional captured sources/final fixtures for metadata reconstruction")
    parser.add_argument("--accept-supplied-scope", action="store_true",
                        help="Declare completeness only within the supplied corpus snapshots")
    parser.add_argument("--closure-requests", action="store_true",
                        help="Generate owner closure requests from reconstructed corpus metadata")
    parser.add_argument("--closure-source-cas", type=Path,
                        help="Read-only retained source/AST CAS for closure corroboration")
    parser.add_argument("--closure-git-repository", type=Path,
                        help="Read-only retained source-owner Git repository for closure corroboration")
    parser.add_argument("--closure-qualification-report", type=Path,
                        help="Retained source-owner qualification report for closure corroboration")
    parser.add_argument("--closure-response-requests", type=Path,
                        help="Review responses to this retained native closure request inventory")
    parser.add_argument("--closure-response", type=Path,
                        help="Proposed owner response; omission generates an explicitly unreviewed template")
    parser.add_argument("--closure-cohort-inventory", action="store_true",
                        help="Enumerate all connected groups in the generated closure response review")
    parser.add_argument("--admission-retained-fixture", type=Path,
                        help="Audit retained finite admission population and selected source provenance")
    parser.add_argument("--admission-historical-replay", action="store_true",
                        help="Also execute the public historical verifier under read-only restrictions")
    parser.add_argument("--admission-replay-python", type=Path,
                        help="Interpreter with the dependencies for the read-only historical verifier")
    parser.add_argument("--admission-snapshot-root", type=Path, action="append",
                        help="Sealed historical core import root; repeat for each repository")
    parser.add_argument("--admission-snapshot-sha256",
                        help="Canonical generation identity required for sealed historical replay")
    parser.add_argument("--worker-retained-fixture", type=Path,
                        help="Audit the retained native worker lifecycle and complete task population")
    parser.add_argument("--retained-join-manifest", type=Path,
                        help="Capture and audit the selected native corpus from a hash-bound retained join spec")
    parser.add_argument("--advisory-evidence-manifest", type=Path,
                        help="Audit pinned advisory stages and failed-attempt accounting without native execution")
    parser.add_argument("--final-evaluation-manifest", type=Path,
                        help="Validate a frozen final protocol and score separately retained prediction exports")
    parser.add_argument("--release-matrix-manifest", type=Path,
                        help="Reconcile a commit-pinned acceptance ledger and selected release evidence")
    parser.add_argument("--frozen-auxiliary-evidence-manifest", type=Path,
                        help="Verify explicitly selected retained frozen invocation/inference/metrics bodies")
    parser.add_argument("--final-input-lock-manifest", type=Path,
                        help="Seal fixed FINAL protocol/cohort/targets/source inputs independently of predictions")
    parser.add_argument("--locked-final-evaluation-manifest", type=Path,
                        help="Score exports against an explicitly pinned preexisting FINAL input lock")
    parser.add_argument("--final-protocol-lock", type=Path,
                        help="Original FINAL lock receipt location required by locked evaluation")
    parser.add_argument("--final-protocol-lock-sha256",
                        help="Explicit raw lock receipt SHA256 required by locked evaluation")
    parser.add_argument("--portable-release-review-manifest", type=Path,
                        help="Verify a portable selected release review bundle without its original repositories")
    parser.add_argument("--worker-protocol-evidence-manifest", type=Path,
                        help="Reconstruct retained worker response digests under an inert pinned protocol source")
    parser.add_argument("--paired-final-evaluation-manifest", type=Path,
                        help="Compare pinned before/after locked FINAL exports without counting controls as samples")
    parser.add_argument("--portable-release-archive-manifest", type=Path,
                        help="Restore and verify a pinned portable release review archive offline")
    parser.add_argument("--inventory-query-controls-manifest", type=Path,
                        help="Check authored complete/partial inventory-query receiver fixtures without live catalogs")
    parser.add_argument("--released-evidence-children-manifest", type=Path,
                        help="Audit explicitly declared public child evidence at immutable release commits")
    parser.add_argument("--contrast-final-input-lock-manifest", type=Path,
                        help="Seal a separately declared source-only contrast cohort before prediction exports")
    parser.add_argument("--native-source384-diagnostics-manifest", type=Path,
                        help="Retain selected native source384 exports as diagnostics without source accuracy claims")
    parser.add_argument("--native-source-comparison-manifest", type=Path,
                        help="Compare retained native fragments to independently derived exact-source labels")
    parser.add_argument("--portable-evidence-children-manifest", type=Path,
                        help="Restore and verify the separate one-level released child-evidence capsule offline")
    parser.add_argument("--native-inventory-query-manifest", type=Path,
                        help="Reconcile retained native inventory/query exports with their separately pinned evidence")
    parser.add_argument("--native-batch-query-manifest", type=Path,
                        help="Receive retained ordered native batch queries and original requirement dispositions")
    parser.add_argument("--native-program-graph-manifest", type=Path,
                        help="Verify retained source-bound ProgramIR graph and syntactic effect conformance")
    parser.add_argument("--producer-source-bindings-manifest", type=Path,
                        help="Restore and verify selected claimed producer source bytes at pinned release commits")
    parser.add_argument("--native-lean-projection-manifest", type=Path,
                        help="Check retained ProgramIR-to-Lean projection structure and explicit semantic losses")
    parser.add_argument("--smt-v2-custody-manifest", type=Path,
                        help="Receive privately frozen SMT phase records while preserving invocation and verdict gaps")
    parser.add_argument("--producer-source-provenance-manifest", type=Path,
                        help="Verify declared historical producer sources without substituting them for committed files")
    parser.add_argument("--native-feature-coverage-manifest", type=Path,
                        help="Audit retained frozen feature vocabulary coverage and distinct target collisions")
    parser.add_argument("--jvm-probe-custody-manifest", type=Path,
                        help="Receive frozen JVM support-probe records without executing Java or model checks")
    parser.add_argument("--finite-proof-toolchain-custody-manifest", type=Path,
                        help="Reconcile retained finite proof artifacts and unresolved toolchain dependencies offline")
    parser.add_argument("--finite-match-controls-manifest", type=Path,
                        help="Match authored requirements to retained finite tables while preserving all tasks")
    parser.add_argument("--feature-separation-manifest", type=Path,
                        help="Measure diagnostic feature-column separation without changing the frozen vocabulary")
    parser.add_argument("--admission-declaration-custody-manifest", type=Path,
                        help="Audit released admission test declarations and explicit missing signed envelope bodies")
    parser.add_argument("--resumed-inventory-controls-manifest", type=Path,
                        help="Reconcile complete resumed inventory membership and historical worker records")
    parser.add_argument("--resumed-cohort-audit-manifest", type=Path,
                        help="Account for retained source syntax and declared training exposure in the resumed inventory")
    parser.add_argument("--dispatch-attempt-custody-manifest", type=Path,
                        help="Reconcile recorded dispatch attempts, test phases, generations and separate costs")
    parser.add_argument("--tla-operation-controls-manifest", type=Path,
                        help="Receive retained failed whole TLA operation attempts without promoting partial results")
    parser.add_argument("--source-delta-analysis-manifest", type=Path,
                        help="Compare captured source entries, bytes, syntax and historical exposure without authorizing reuse")
    parser.add_argument("--current-runtime-cleanup-custody-manifest", type=Path,
                        help="Reconcile retained runtime cleanup records, source metadata and distinct regression identities")
    parser.add_argument("--evidence-report", action="append", default=[], type=Path,
                        help="Retain an existing lane report and its hash without rerunning it")
    parser.add_argument("--apalache-admission-controls-manifest", type=Path,
                        help="Retained Apalache admission phases, failures and witness scope")
    parser.add_argument("--successor-cohort-audit-manifest", type=Path,
                        help="Retained successor prefix source and declared child exposure input")
    parser.add_argument("--successor-planning-custody-manifest", type=Path,
                        help="Retained successor planning, residual task and cost custody input")
    parser.add_argument("--foreign-outcome-controls-manifest", type=Path,
                        help="Retained foreign result conversion, bounded authority and failed attempt input")
    parser.add_argument("--full-successor-cohort-audit-manifest", type=Path,
                        help="Retained full default successor pages and complete snapshot metadata input")
    parser.add_argument("--successor-receiving-custody-manifest", type=Path,
                        help="Retained unsigned successor receiving and failed signed attempt input")
    parser.add_argument("--artifact-payload-controls-manifest", type=Path,
                        help="Pinned retained serialized TLA artifact metadata")
    parser.add_argument("--trace-binding-audit-manifest", type=Path,
                        help="Pinned retained scalar trace and declared source-symbol metadata")
    parser.add_argument("--registry-operation-deadline-custody-manifest", type=Path,
                        help="Pinned retained production-created registry deadline metadata")
    parser.add_argument("--signed-worker-acceptance-controls-manifest", type=Path,
                        help="Pinned retained signed worker task and publication metadata")
    parser.add_argument("--publication-dependency-audit-manifest", type=Path,
                        help="Pinned retained publication source and declared dependency metadata")
    parser.add_argument("--native-operation-inheritance-custody-manifest", type=Path,
                        help="Pinned retained admitted native ambient budget metadata")
    args = parser.parse_args()
    if args.probe_imports and not args.release_audit:
        parser.error("--probe-imports requires --release-audit")
    if (args.source_metadata_supplement is not None or args.accept_supplied_scope) and args.source_metadata_manifest is None:
        parser.error("metadata supplement/scope requires --source-metadata-manifest")
    if args.runtime_config is not None and not (args.runtime_demand or args.runtime_observed_report):
        parser.error("--runtime-config requires --runtime-demand or --runtime-observed-report")
    if (args.runtime_initial_snapshot is None) != (args.runtime_initial_snapshot_sha256 is None):
        parser.error("runtime initial snapshot requires both its path and explicit SHA256")
    if args.runtime_initial_snapshot is not None and not args.runtime_demand:
        parser.error("runtime initial snapshot requires --runtime-demand")
    if args.external_python is not None and args.external_from_report is None:
        parser.error("--external-python requires --external-from-report")
    if args.closure_requests and args.source_metadata_manifest is None:
        parser.error("--closure-requests requires --source-metadata-manifest")
    if any(value is not None for value in (args.closure_source_cas, args.closure_git_repository,
                                          args.closure_qualification_report)) and not args.closure_requests:
        parser.error("closure owner inputs require --closure-requests")
    if args.closure_response is not None and args.closure_response_requests is None:
        parser.error("--closure-response requires --closure-response-requests")
    if args.closure_cohort_inventory and args.closure_response_requests is None:
        parser.error("--closure-cohort-inventory requires --closure-response-requests")
    if args.admission_historical_replay and args.admission_retained_fixture is None:
        parser.error("--admission-historical-replay requires --admission-retained-fixture")
    if args.admission_replay_python is not None and not args.admission_historical_replay:
        parser.error("--admission-replay-python requires --admission-historical-replay")
    if bool(args.admission_snapshot_root) != (args.admission_snapshot_sha256 is not None):
        parser.error("admission snapshot requires both roots and explicit SHA256")
    if args.admission_snapshot_root and not args.admission_historical_replay:
        parser.error("admission snapshot requires --admission-historical-replay")
    if args.admission_snapshot_sha256 is not None and not re.fullmatch(r"[0-9a-f]{64}", args.admission_snapshot_sha256):
        parser.error("admission snapshot requires a lowercase SHA256 identity")
    if (args.final_protocol_lock is None) != (args.final_protocol_lock_sha256 is None):
        parser.error("FINAL protocol lock requires both its path and explicit SHA256")
    if args.locked_final_evaluation_manifest is not None and args.final_protocol_lock is None:
        parser.error("locked FINAL evaluation requires --final-protocol-lock and --final-protocol-lock-sha256")
    if args.final_protocol_lock is not None and args.locked_final_evaluation_manifest is None:
        parser.error("FINAL protocol lock requires --locked-final-evaluation-manifest")
    if (args.final_protocol_lock_sha256 is not None
            and not re.fullmatch(r"[0-9a-f]{64}", args.final_protocol_lock_sha256)):
        parser.error("FINAL protocol lock requires a lowercase SHA256 identity")
    source = Path(__file__).resolve().parent
    workspace = source.parents[1]
    for lane in LANES:
        if not list((source / lane).glob("test_*.py")):
            parser.error(f"missing tests for {lane}")
    if args.output is None:
        base = workspace / "artifacts/codebase_ir_parallel_qualification"
        base.mkdir(parents=True, exist_ok=True)
        output = Path(tempfile.mkdtemp(prefix="joined-", dir=base))
    else:
        output = args.output.resolve()
        if output == source or source in output.parents:
            parser.error("output must be outside the implementation directory")
        output.mkdir(parents=True, exist_ok=False)
    snapshot = output / "implementation"
    inputs = {}
    for path in sorted(source.rglob("*")):
        if not path.is_file() or path.suffix not in {".py", ".md", ".json", ".toml", ".source"}:
            continue
        if "__pycache__" in path.parts:
            continue
        relative = path.relative_to(source)
        copied = snapshot / relative
        copied.parent.mkdir(parents=True, exist_ok=True)
        raw = path.read_bytes()
        copied.write_bytes(raw)
        inputs[str(relative)] = hashlib.sha256(raw).hexdigest()
    roadmap = workspace / "external/ipfs_accelerate/docs/architecture/REPOSITORY_PROOF_INDEX_AND_CODEBASE_IR_ROADMAP.md"
    roadmap_identity = None
    if roadmap.is_file():
        raw = roadmap.read_bytes()
        (output / "reviewed-roadmap.md").write_bytes(raw)
        roadmap_identity = {"path": str(roadmap), "sha256": hashlib.sha256(raw).hexdigest()}
    evidence_reports = []
    for index, evidence_path in enumerate(args.evidence_report):
        try:
            raw, payload = read_report(evidence_path)
        except (OSError, ValueError, RecursionError) as error:
            parser.error(f"invalid evidence report: {error}")
        copied = output / f"evidence-{index:02d}-{evidence_path.name}"
        copied.write_bytes(raw)
        evidence_reports.append({"path": str(evidence_path.absolute()), "retained_as": copied.name,
                                 "sha256": hashlib.sha256(raw).hexdigest(),
                                 "schema": payload.get("schema"), "status": payload.get("status"),
                                 "disposition": payload.get("disposition"),
                                 "candidate_audit_status": payload.get("candidate_audit_status"),
                                 "scope": "retained separate lane execution; not rerun by this command"})
    steps = []
    findings = {}
    workflow_inputs = {}
    for lane in LANES:
        steps.append(run_step(f"{lane}-tests", [sys.executable, "-I", "-B", "-m", "unittest",
                              "discover", "-s", str(snapshot / lane), "-p", "test_*.py", "-v"],
                              workspace, output))
    steps.append(run_step("runner-tests", [sys.executable, "-I", "-B", "-m", "unittest",
                          "discover", "-s", str(snapshot), "-p", "test_run_qualification.py", "-v"],
                          workspace, output))
    steps.append(run_step("acceptance-fixtures", [sys.executable, "-I", "-B",
                          str(snapshot / "acceptance/codebase_ir_acceptance.py"),
                          "--output", str(output / "acceptance-fixtures")], workspace, output))
    cohort = output / "acceptance-fixtures/corpus_audit_input.json"
    if cohort.is_file():
        steps.append(run_step("cross-lane-leakage-control", [sys.executable, "-I", "-B",
                              str(snapshot / "corpus_audit/codebase_ir_corpus_audit.py"),
                              str(cohort), "--output", str(output / "corpus-leakage-report.json")],
                              workspace, output, expected_returncode=1))
        leakage_path = output / "corpus-leakage-report.json"
        if leakage_path.is_file():
            leakage = json.loads(leakage_path.read_text())
            required_kinds = {"normalized_ast", "related_revision", "dependency_connected"}
            found_kinds = {row["kind"] for row in leakage["leaks"]}
            steps[-1]["passed"] = (steps[-1]["passed"]
                                   and leakage["complete_for_declared_scope"]
                                   and required_kinds <= found_kinds)
            steps[-1]["detected_leakage_kinds"] = sorted(found_kinds)
        else:
            steps[-1]["passed"] = False
        clean = json.loads(cohort.read_text())
        roles = {"baseline:calc.py": "train", "baseline:decoy.py": "tune",
                 "baseline:helpers.py": "canary", "baseline:effectful.py": "final"}
        clean["units"] = [row for row in clean["units"] if row["id"] in roles]
        for row in clean["units"]:
            row["role"] = roles[row["id"]]
        clean_path = output / "corpus-clean-input.json"
        clean_path.write_text(json.dumps(clean, sort_keys=True, indent=2) + "\n")
        steps.append(run_step("cross-lane-clean-control", [sys.executable, "-I", "-B",
                              str(snapshot / "corpus_audit/codebase_ir_corpus_audit.py"),
                              str(clean_path), "--output", str(output / "corpus-clean-report.json")],
                              workspace, output))
        clean_report_path = output / "corpus-clean-report.json"
        if clean_report_path.is_file():
            clean_report = json.loads(clean_report_path.read_text())
            steps[-1]["passed"] = steps[-1]["passed"] and clean_report["leak_free_within_declared_scope"]
        else:
            steps[-1]["passed"] = False
    else:
        steps.append({"name": "cross-lane-leakage-control", "passed": False,
                      "reason": "acceptance fixtures did not export the corpus audit input"})
    final_lock_ready = args.final_protocol_lock is None
    if args.final_protocol_lock is not None:
        try:
            pin = retain_input(args.final_protocol_lock, output / "final-protocol-lock-input.json")
            workflow_inputs["final_protocol_lock"] = pin
            final_lock_ready = pin["sha256"] == args.final_protocol_lock_sha256
            if not final_lock_ready:
                steps.append({"name": "final-protocol-lock-input", "passed": False,
                              "reason": "FINAL lock bytes differ from the explicit raw SHA256"})
        except (OSError, ValueError, RecursionError) as error:
            steps.append({"name": "final-protocol-lock-input", "passed": False,
                          "reason": f"invalid FINAL protocol lock: {error}"})
    for workflow in ISOLATED_WORKFLOWS:
        manifest = getattr(args, workflow + "_manifest")
        if manifest is None:
            continue
        profile = ISOLATED_WORKFLOWS[workflow]
        if workflow == "locked_final_evaluation" and not final_lock_ready:
            steps.append({"name": workflow, "passed": False,
                          "reason": "locked evaluation requires its exact retained FINAL protocol lock"})
            continue
        if (profile.get("manifest_filename") is not None
                and manifest.name != profile["manifest_filename"]):
            steps.append({"name": workflow, "passed": False,
                          "reason": "bundle manifest filename differs from the verifier's selected manifest"})
            continue
        retained = output / (workflow.replace("_", "-") + "-input.json")
        try:
            pin = retain_input(manifest, retained)
            bindings = workflow_manifest_bindings(workflow, read_report(retained)[1])
        except (OSError, ValueError, RecursionError) as error:
            steps.append({"name": workflow, "passed": False, "reason": f"invalid manifest: {error}"})
            continue
        workflow_inputs[workflow] = pin
        destination = output / workflow.replace("_", "-")
        source_manifest = manifest.absolute() if profile.get("relative_inputs") else retained
        command = [sys.executable, "-B", str(snapshot / profile["script"])]
        if profile.get("command_mode") == "portable_verify":
            command.extend(["verify", "--bundle", str(source_manifest.parent),
                            "--bundle-manifest-sha256", pin["sha256"]])
        else:
            if profile.get("command_mode") in {"archive_verify", "child_archive_verify"}:
                command.append("verify")
            command.extend(["--manifest", str(source_manifest)])
        if workflow == "locked_final_evaluation":
            command.extend(["--lock", str(args.final_protocol_lock.absolute()),
                            "--lock-sha256", args.final_protocol_lock_sha256])
            bindings = {"lock_sha256": args.final_protocol_lock_sha256}
        command.extend(["--output", str(destination)])
        step = run_step(workflow.replace("_", "-"), command, workspace, output)
        steps.append(step)
        report_path = destination / profile["report"]
        try:
            raw, payload = read_report(report_path)
            step["passed"] = (step["passed"]
                              and isolated_workflow_passed(payload, workflow, pin["sha256"], bindings)
                              and input_pin_unchanged(pin)
                              and (workflow != "locked_final_evaluation"
                                   or input_pin_unchanged(workflow_inputs["final_protocol_lock"])))
            findings[workflow] = {
                **{key: payload[key] for key in profile["summary_fields"] if key in payload},
                "status": payload.get("status"), "scope": payload.get("scope"),
                "report": str(report_path.relative_to(output)),
                "sha256": hashlib.sha256(raw).hexdigest(),
                "manifest_sha256": payload.get(profile.get("manifest_binding_field", "manifest_sha256")),
                "current_authority_claimed": payload.get("current_authority_claimed"),
                "result_kind": "scoped offline qualification; no production exit requalified",
            }
        except (OSError, ValueError, RecursionError) as error:
            step["passed"] = False
            step["report_error"] = str(error)
    if args.release_audit:
        command = [sys.executable, "-I", "-B", str(snapshot / "release_audit/audit.py"),
                   "--config", str(snapshot / "release_audit/codebase_ir.json"),
                   "--output", str(output / "release-closure"), "--snapshot"]
        if args.probe_imports:
            command.extend(["--probe-imports", "--import-timeout", "5"])
        steps.append(run_step("release-closure", command, workspace, output, timeout=300))
    runtime_config = args.runtime_config.resolve() if args.runtime_config else snapshot / "release_audit/runtime_service.json"
    if args.runtime_observed_report is not None:
        retained = output / "runtime-observed-input.json"
        workflow_inputs["runtime_observed_report"] = retain_input(args.runtime_observed_report, retained)
        command = [sys.executable, "-B", str(snapshot / "release_audit/observed_profile.py"),
                   "--report", str(retained), "--report-sha256", workflow_inputs["runtime_observed_report"]["sha256"],
                   "--config", str(runtime_config), "--output", str(output / "invocation-config.json")]
        for module in ("ipfs_accelerate_py.agent_supervisor.planning.finite_integer_plan_service",
                       "ipfs_accelerate_py.agent_supervisor.planning.finite_integer_capacity",
                       "ipfs_accelerate_py.agent_supervisor.planning.finite_integer_source_custody",
                       "ipfs_datasets_py.logic.software_contracts.codebase_integer_model_lean",
                       "ipfs_accelerate_py.agent_supervisor.planning.codebase_feature_context"):
            command.extend(["--seed", module])
        steps.append(run_step("runtime-observed-profile", command, workspace, output))
        runtime_config = output / "invocation-config.json"
        if runtime_config.is_file():
            invocation = json.loads(runtime_config.read_bytes()).get("observed_profile", {})
            findings["runtime_observed_profile"] = {
                "observed_file_count": invocation.get("observed_file_count"),
                "source_report_sha256": invocation.get("source_report_sha256"),
                "function_invocation_closure_proven": False,
                "report": str(runtime_config.relative_to(output)),
            }
        else:
            steps[-1]["passed"] = False
    if args.runtime_demand and (args.runtime_observed_report is None or runtime_config.is_file()):
        command = [sys.executable, "-B", str(snapshot / "release_audit/runtime_demand.py"),
                   "--config", str(runtime_config),
                   "--output", str(output / "runtime-demand"), "--import-timeout", "5"]
        if args.runtime_initial_snapshot is not None:
            command.extend(["--initial-snapshot", str(args.runtime_initial_snapshot.resolve()),
                            "--initial-snapshot-sha256", args.runtime_initial_snapshot_sha256])
        steps.append(run_step("runtime-demand", command, workspace, output, timeout=300))
        demand_report = output / "runtime-demand/summary.json"
        if demand_report.is_file():
            demand = json.loads(demand_report.read_text())
            findings["runtime_demand"] = {
                "disposition": demand.get("disposition"),
                "importability_qualified": demand.get("importability_qualified", False),
                "scope": demand.get("qualification_scope"),
                "report": str(demand_report.relative_to(output)),
            }
        else:
            steps[-1]["passed"] = False
    if args.external_from_report is not None:
        retained = output / "external-observed-input.json"
        workflow_inputs["external_observed_report"] = retain_input(args.external_from_report, retained)
        interpreter = str(args.external_python.absolute()) if args.external_python else sys.executable
        command = [interpreter, "-B", str(snapshot / "acceptance/codebase_ir_external_pins.py"),
                   "--from-report", str(retained), "--output", str(output / "external_manifest.json")]
        steps.append(run_step("external-dependency-pins", command, workspace, output))
        external_manifest = output / "external_manifest.json"
        if external_manifest.is_file():
            external = json.loads(external_manifest.read_bytes())
            findings["external_dependency_pins"] = {
                "file_count": len(external.get("files", [])),
                "source_report_sha256": external.get("source_report_sha256"),
                "imports_performed": False, "runtime_closure_proven": False,
                "manifest_sha256": file_hash(external_manifest),
                "report": str(external_manifest.relative_to(output)),
            }
        else:
            steps[-1]["passed"] = False
    if args.source_metadata_manifest is not None:
        command = [sys.executable, "-B", str(snapshot / "corpus_audit/codebase_ir_source_metadata.py"),
                   "--manifest", str(args.source_metadata_manifest.resolve()),
                   "--output", str(output / "source-metadata")]
        if args.source_metadata_supplement is not None:
            command.extend(["--supplement", str(args.source_metadata_supplement.resolve())])
        if args.accept_supplied_scope:
            command.append("--accept-supplied-scope")
        steps.append(run_step("source-metadata", command, workspace, output, timeout=180))
        metadata_report = output / "source-metadata/reconstruction_report.json"
        if metadata_report.is_file():
            metadata = json.loads(metadata_report.read_text())
            findings["source_metadata"] = {
                "candidate_audit_status": metadata.get("candidate_audit_status"),
                "candidate_complete_for_declared_scope": metadata.get("candidate_complete_for_declared_scope", False),
                "whole_repository_coverage": metadata.get("whole_repository_coverage", False),
                "report": str(metadata_report.relative_to(output)),
            }
        else:
            steps[-1]["passed"] = False
        if args.closure_requests and metadata_report.is_file():
            command = [sys.executable, "-B", str(snapshot / "corpus_audit/codebase_ir_closure_requests.py"),
                       "--manifest", str(output / "source-metadata/candidate_manifest.json"),
                       "--output", str(output / "closure-requests")]
            for option, value in (("--source-cas", args.closure_source_cas),
                                  ("--git-repository", args.closure_git_repository),
                                  ("--qualification-report", args.closure_qualification_report)):
                if value is not None:
                    command.extend([option, str(value.resolve())])
            steps.append(run_step("native-closure-requests", command, workspace, output))
            request_report = output / "closure-requests/closure_requests.json"
            if request_report.is_file():
                requests = json.loads(request_report.read_bytes())
                findings["native_closure_requests"] = {
                    key: requests.get(key) for key in ("status", "baseline_closure_issue_count",
                        "closure_request_count", "owner_fact_count", "comparison_audit_status",
                        "comparison_closure_issue_count", "native_closure_certification_verified",
                        "closure_claims_applied", "whole_repository_coverage")}
                findings["native_closure_requests"]["report"] = str(request_report.relative_to(output))
            else:
                steps[-1]["passed"] = False
    if args.retained_join_manifest is not None:
        retained = output / "retained-join-spec-input.json"
        workflow_inputs["retained_join_spec"] = retain_input(args.retained_join_manifest, retained)
        capture_spec = read_report(retained)[1]
        command = [sys.executable, "-B", str(snapshot / "corpus_audit/codebase_ir_retained_join.py"),
                   "--manifest", str(retained), "--output", str(output / "retained-join-corpus")]
        steps.append(run_step("retained-join-corpus", command, workspace, output))
        capture_report = output / "retained-join-corpus/retained_join_report.json"
        if capture_report.is_file():
            capture = read_report(capture_report)[1]
            findings["retained_join_corpus"] = {key: capture.get(key) for key in (
                "disposition", "primary_pin_inventory_count", "selected_artifact_count", "selected_artifact_bytes",
                "native_version_count", "native_target_membership_count", "ancestral_training_exposure_count",
                "selected_native_paths", "recorded_metadata_only_paths", "baseline_audit_status",
                "baseline_issue_count", "baseline_leakage_count", "reconstructed_audit_status",
                "reconstructed_issue_count", "closure_request_count", "group_count", "cross_role_group_count",
                "final_connected_group_count", "template_disposition", "independence_verified")}
            findings["retained_join_corpus"]["report"] = str(capture_report.relative_to(output))
            steps[-1]["passed"] = (steps[-1]["passed"]
                and capture.get("schema") == "codebase-ir-retained-join-corpus@1"
                and capture.get("disposition") == "captured_subset_produced"
                and capture.get("capture_spec_sha256") == workflow_inputs["retained_join_spec"]["sha256"]
                and all(capture.get(field) == capture_spec.get(field) for field in (
                    "result_sha256", "independent_audit_sha256", "artifact_pins_sha256", "path_mapping"))
                and all(capture.get(field) is False for field in (
                    "all_primary_artifacts_reverified", "independent_audit_executed", "numerical_state_replayed",
                    "registry_opened", "training_executed", "producer_authentication_verified",
                    "native_closure_certification_verified", "independence_verified", "whole_repository_coverage",
                    "proof_authority", "promotion_decisions_made"))
                and type(capture.get("closure_claims_applied")) is int
                and capture.get("closure_claims_applied") == 0)
        else:
            steps[-1]["passed"] = False
    if args.admission_retained_fixture is not None:
        fixture = args.admission_retained_fixture.absolute()
        workflow_inputs["admission_fixture_result"] = retain_input(
            fixture / "result.json", output / "admission-fixture-result-input.json")
        command = [sys.executable, "-B", str(snapshot / "acceptance/codebase_ir_admission_evidence.py"),
                   "--fixture-root", str(fixture), "--workspace", str(workspace), "--output", str(output / "admission-evidence")]
        if args.admission_historical_replay:
            command.append("--historical-replay")
        if args.admission_replay_python is not None:
            command.extend(["--replay-python", str(args.admission_replay_python.absolute())])
        for root in args.admission_snapshot_root or []:
            command.extend(["--snapshot-root", str(root.absolute())])
        if args.admission_snapshot_sha256 is not None:
            command.extend(["--snapshot-sha256", args.admission_snapshot_sha256])
        steps.append(run_step("retained-admission-evidence", command, workspace, output))
        admission_report = output / "admission-evidence/admission_evidence.json"
        if admission_report.is_file():
            admission = read_report(admission_report)[1]
            findings["retained_admission_evidence"] = {key: admission.get(key) for key in (
                "status", "manifest_version_coverage", "actual_preserved_task_population",
                "structural_control_count", "structural_controls_refused", "historical_verification")}
            findings["retained_admission_evidence"]["report"] = str(admission_report.relative_to(output))
            steps[-1]["passed"] = (steps[-1]["passed"]
                and admission.get("schema") == "codebase-ir-retained-admission-audit@1"
                and admission.get("status") == "passed"
                and admission.get("input_result_sha256") == workflow_inputs["admission_fixture_result"]["sha256"])
            if args.admission_historical_replay:
                history = admission.get("historical_verification", {})
                steps[-1]["passed"] = steps[-1]["passed"] and historical_replay_passed(
                    history, args.admission_snapshot_root, args.admission_snapshot_sha256)
        else:
            steps[-1]["passed"] = False
        command = [sys.executable, "-B", str(snapshot / "release_audit/retained_provenance.py"),
                   "--fixture", str(fixture), "--config", str(snapshot / "release_audit/runtime_service.json"),
                   "--workspace", str(workspace), "--output", str(output / "admission-provenance")]
        steps.append(run_step("retained-admission-provenance", command, workspace, output))
        provenance_report = output / "admission-provenance/ledger.json"
        if provenance_report.is_file():
            provenance = read_report(provenance_report)[1]
            findings["retained_admission_provenance"] = {key: provenance.get(key) for key in (
                "disposition", "counts", "declarations", "runtime_closure_proven",
                "signature_verification_performed", "current_freshness_verified", "production_qualified")}
            findings["retained_admission_provenance"]["source_view_counts"] = {
                key: value.get("counts") for key, value in provenance.get("source_views", {}).items()}
            findings["retained_admission_provenance"]["source_stable"] = provenance.get("source_stability", {}).get("stable")
            findings["retained_admission_provenance"]["report"] = str(provenance_report.relative_to(output))
            steps[-1]["passed"] = (steps[-1]["passed"]
                and provenance.get("schema") == "codebase-ir-retained-source-provenance/v1"
                and provenance.get("disposition") == "ledger_produced"
                and provenance.get("raw_result_sha256") == workflow_inputs["admission_fixture_result"]["sha256"])
        else:
            steps[-1]["passed"] = False
    if args.worker_retained_fixture is not None:
        fixture = args.worker_retained_fixture.absolute()
        workflow_inputs["worker_fixture_result"] = retain_input(
            fixture / "result.json", output / "worker-fixture-result-input.json")
        command = [sys.executable, "-B", str(snapshot / "acceptance/codebase_ir_worker_evidence.py"),
                   "--fixture-root", str(fixture), "--output", str(output / "worker-evidence")]
        steps.append(run_step("retained-worker-evidence", command, workspace, output))
        worker_report = output / "worker-evidence/worker_evidence.json"
        if worker_report.is_file():
            worker = read_report(worker_report)[1]
            findings["retained_worker_evidence"] = {key: worker.get(key) for key in (
                "status", "preserved_task_population", "structural_control_count", "structural_controls_refused",
                "historical_native_worker_observed", "worker_execution_during_audit",
                "signature_authentication_performed_by_structural_audit", "current_launch_permission_claimed",
                "publication_verified", "git_publication", "read_file_count", "read_bytes",
                "held_full_fresh_evidence_cid_rederived", "unknowns")}
            findings["retained_worker_evidence"]["report"] = str(worker_report.relative_to(output))
            steps[-1]["passed"] = (steps[-1]["passed"]
                and worker.get("schema") == "codebase-ir-retained-worker-audit@1"
                and worker.get("status") == "passed"
                and worker.get("input_result_sha256") == workflow_inputs["worker_fixture_result"]["sha256"]
                and worker.get("historical_native_worker_observed") is True
                and worker.get("publication_verified") is True
                and worker.get("retained_files_unchanged") is True
                and all(worker.get(field) is False for field in (
                    "worker_execution_during_audit", "signature_authentication_performed_by_structural_audit",
                    "current_launch_permission_claimed", "worker_launched", "historical_replay_performed_during_audit",
                    "task_database_opened", "profile_keys_read", "native_proof_invoked", "git_invoked", "network_invoked",
                    "held_full_fresh_evidence_cid_rederived"))
                and type(worker.get("training_steps")) is int and worker.get("training_steps") == 0
                and worker.get("production_tasks_closed") == [])
        else:
            steps[-1]["passed"] = False
    if args.closure_response_requests is not None:
        retained = output / "closure-response-requests-input.json"
        workflow_inputs["closure_response_requests"] = retain_input(args.closure_response_requests, retained)
        command = [sys.executable, "-B", str(snapshot / "corpus_audit/codebase_ir_closure_response.py"),
                   "--requests", str(args.closure_response_requests.absolute()),
                   "--output", str(output / "closure-response")]
        if args.closure_response is not None:
            retained_response = output / "closure-response-input.json"
            workflow_inputs["closure_response"] = retain_input(args.closure_response, retained_response)
            command.extend(["--response", str(args.closure_response.absolute())])
        steps.append(run_step("native-closure-response", command, workspace, output))
        response_report = output / "closure-response/response_review_report.json"
        if response_report.is_file():
            response = read_report(response_report)[1]
            findings["native_closure_response"] = {key: response.get(key) for key in (
                "disposition", "baseline_issue_count", "proposed_audit_issue_count",
                "response_request_count", "proposed_relation_count", "contradiction_count", "leakage_count",
                "native_closure_certification_verified", "closure_claims_applied", "whole_repository_coverage")}
            findings["native_closure_response"]["report"] = str(response_report.relative_to(output))
            steps[-1]["passed"] = (steps[-1]["passed"]
                and response.get("schema") == "codebase-ir-owner-response-review@1"
                and response.get("binding", {}).get("requests_sha256")
                == workflow_inputs["closure_response_requests"]["sha256"]
                and response.get("native_closure_certification_verified") is False
                and type(response.get("closure_claims_applied")) is int
                and response.get("closure_claims_applied") == 0)
            if args.closure_response is not None:
                steps[-1]["passed"] = (steps[-1]["passed"] and response.get("response_sha256")
                    == workflow_inputs["closure_response"]["sha256"])
        else:
            steps[-1]["passed"] = False
        if args.closure_cohort_inventory:
            if steps[-1]["passed"]:
                workflow_inputs["cohort_review"] = retain_input(
                    response_report, output / "cohort-review-input.json")
                command = [sys.executable, "-B", str(snapshot / "corpus_audit/codebase_ir_cohort_inventory.py"),
                           "--review", str(response_report), "--output", str(output / "cohort-inventory")]
                steps.append(run_step("captured-cohort-inventory", command, workspace, output))
                inventory_path = output / "cohort-inventory/cohort_inventory.json"
                if inventory_path.is_file():
                    inventory = read_report(inventory_path)[1]
                    findings["captured_cohort_inventory"] = {key: inventory.get(key) for key in (
                        "disposition", "review_disposition", "unit_count", "group_count", "cross_role_group_count",
                        "final_group_count", "final_connected_group_count", "ancestral_training_exposure_count",
                        "native_target_membership_count", "baseline_issue_count", "inventory_issue_count",
                        "owner_frontier_count", "contradiction_count", "independence_verified",
                        "native_closure_certification_verified", "closure_claims_applied")}
                    findings["captured_cohort_inventory"]["report"] = str(inventory_path.relative_to(output))
                    steps[-1]["passed"] = (steps[-1]["passed"]
                        and inventory.get("schema") == "codebase-ir-captured-cohort-inventory@1"
                        and inventory.get("disposition") == "inventory_produced"
                        and inventory.get("review_sha256") == workflow_inputs["cohort_review"]["sha256"]
                        and inventory.get("binding") == response.get("binding")
                        and all(inventory.get(field) is False for field in (
                            "independence_verified", "native_closure_certification_verified", "proof_authority",
                            "training_executed", "promotion_decisions_made", "producer_authentication_verified",
                            "relationship_truth_verified", "whole_repository_coverage", "unseen_rename_ancestry_verified"))
                        and type(inventory.get("closure_claims_applied")) is int
                        and inventory.get("closure_claims_applied") == 0)
                else:
                    steps[-1]["passed"] = False
            else:
                steps.append({"name": "captured-cohort-inventory", "passed": False,
                              "reason": "closure response review did not pass its binding checks"})
    changed = [name for name, digest in inputs.items()
               if not (source / name).is_file() or file_hash(source / name) != digest]
    changed_manifests = changed_workflow_pins(workflow_inputs)
    passed = all(step["passed"] for step in steps) and not changed and not changed_manifests
    report = {"schema": "codebase-ir-independent-lanes-run@1",
              "recorded_at": datetime.now(UTC).isoformat(),
              "implementation": inputs, "roadmap": roadmap_identity,
              "evidence_reports": evidence_reports,
              "workflow_inputs": workflow_inputs,
              "qualification_findings": findings,
              "steps": steps, "source_changes_during_run": changed,
              "workflow_manifest_changes_during_run": changed_manifests,
              "tests_passed": passed,
              "test_count": sum(step.get("test_count", 0) for step in steps),
              "skipped_count": sum(step.get("skipped_count", 0) for step in steps),
              "production_tasks_closed": [], "signed_admission_executed": False,
              "historical_admission_verification_requested": args.admission_historical_replay,
              "native_worker_successor_executed": False,
              "training_executed": False}
    (output / "results.json").write_text(json.dumps(report, indent=2, sort_keys=True) + "\n")
    print(f"Results: {output / 'results.json'}", flush=True)
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
