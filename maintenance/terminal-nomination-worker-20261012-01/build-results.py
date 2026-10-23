"""Summarize frozen source, scoped tests and actual isolated public readbacks."""
import hashlib
import json
from pathlib import Path

STAGE = Path(__file__).resolve().parent


def load(name):
    return json.loads((STAGE / name).read_text())


def pin(name):
    raw = (STAGE / name).read_bytes()
    return {"path": name, "bytes": len(raw), "sha256": hashlib.sha256(raw).hexdigest()}


def save(name, value):
    (STAGE / name).write_text(json.dumps(value, sort_keys=True, indent=2) + "\n")


def main():
    source = load("source-manifest.json")
    focused = load("final-focused-validation.json")
    preservation = load("preservation-check.json")
    host = load("host-worker-readback-02/qualification.json")
    installed = load("installed-worker-qualification-03/qualification.json")
    archive = load("runtime-archive-verification.json")
    assert host["qualified"] and installed["qualified"] and preservation["all_checks_passed"]
    assert focused["qualified"] and focused["latest_distinct_classname_name_cases"] == 292
    assert installed["archive_sha256"] == archive["archive_sha256"]
    worker = installed["readback"]["worker"]
    assert worker["uid"] == worker["euid"] == 1001
    assert worker["private_owner_database_open_denied_without_body_read"] is True
    remaining = [
        {"priority": 1, "work": "Qualify the complete same-owner driver and Harbor lifecycle.",
            "implementation": [
                "Exercise the driver's actual prepare-only branch and resumed dispatch in the original public Terminal Bench container, preserving the generated task/index identities and existing training policy.",
                "Implement retained same-container Harbor preparation, public review export and resume; the current fresh adapter deliberately refuses reviewed pairs.",
                "Update the full model-input audit to verify the catalog appendix, required pointer, literal instruction and exact complete rendered prompt before provider trials.",
                "Carry one cumulative budget across preparation/review/resume and include preparation, training, planning, auditing and retries in the total ledger.",
            ], "acceptance": "Actual signed same-owner admission and deployed worker dispatch use the reviewed catalog; old audit formats never silently certify the new appendix and absent defaults remain compatible."},
        {"priority": 2, "work": "Reduce repeated provenance and qualify source-replay caching.",
            "implementation": [
                "Use one independently verified manifest plus parent-bound compact pages and continuation deltas; keep complete byte/token accounting for first-manifest cost and every follow-up.",
                "Key verified structural replay by source/tree/index/extractor/schema/config/dependency identities; reject stale cache records and preserve unknown coverage.",
                "Compare raw source, native facts, semantic capsules and conservative minification using identical unresolved questions and exact reconstruction checks.",
            ], "acceptance": "Complete outputs are smaller at a measured break-even call count while retaining independent bindings, UTF-8 paging, caps and final witness guards; local counts are not promoted to provider savings."},
        {"priority": 3, "work": "Admit checked source observations before symbolic planning.",
            "implementation": [
                "Define an independently admitted pre-plan evidence baseline and typed observation policy; the current attachment remains post-plan descriptive context.",
                "Join IntentIR requirements to current source facts, candidate relevance, checked preconditions and behavioral obligations as separate states.",
                "Implement import/alias/receiver/global/control-data-flow coverage incrementally; keep not_analyzed and unknown counts visible.",
                "Only checker receipts with explicit assumptions may discharge obligations; replan and invalidate affected evidence after edits.",
            ], "acceptance": "The planner uses admitted structural facts without converting symbol existence or learned relevance into behavioral satisfaction."},
        {"priority": 4, "work": "Train and evaluate a typed CodebaseIR with native projections.",
            "implementation": [
                "Use deterministic source-derived IR as the canonical target; project AST/KG/vectors/contracts/effects/dependencies into versioned DuckDB/Quack/DuckLake records.",
                "Train repository-adapted encoders on public Terminal Bench snapshots using source-separated held-out data, bounded adaptation, reproducible seeds and model/data/config identities.",
                "Validate decoded candidates against schema and source joins before use; measure reconstruction, schema validity, candidate recall, compute and all preparation/model costs.",
            ], "acceptance": "Held-out validated reconstruction and retrieval improve against an untrained native baseline; learned candidates remain distinct from checked contracts and mathematical convergence."},
        {"priority": 5, "work": "Qualify logic projections, source refinement and proof-index invalidation.",
            "implementation": [
                "Discover actual pinned ipfs_datasets_py logic-family capabilities and publish a supported/unsupported IR translation matrix.",
                "Generate obligations with stated operational semantics, assumptions and translation receipts; compile/check supported Lean modules without presenting admitted placeholders as proofs.",
                "Prove translation/refinement for a bounded subset and cache receipts by source, IR, obligation, assumptions, translator, prover and toolchain identity.",
            ], "acceptance": "Lean compilation, checked theorems, Python source equivalence, complete task satisfaction and model convergence are independently assessed; unsupported constructs and counterexamples stay visible."},
        {"priority": 6, "work": "Run repeated paired complete-session evaluations.",
            "implementation": [
                "Compare baseline native retrieval, reviewed source access, compact provenance, capsules/minification and trained IR retrieval on matched tasks and pinned runtime/model settings.",
                "Count provider usage from all preparation/planning/training-advice/coding/audit/retry calls; cached input and reasoning output remain subcategories, missing usage remains unknown.",
                "Pair total tokens with existing task verifiers, task success, independent input audits, latency, compute and refusal/failure rates.",
            ], "acceptance": "Prespecified repeated results improve complete provider token use while preserving task success and evidence validity; smaller local packets alone do not pass."},
    ]
    save("next-work.json", {"schema": "reviewed-source-worker-next-work@1",
        "objective": "Reduce total supervisor Terminal Bench session tokens using source-grounded IntentIR/CodebaseIR and checked evidence, while preserving task success.",
        "completed": "Typed required pointer, verified bounded catalog, source/fact CLI readback and same-owner driver review export/resume controls; isolated public worker readback qualified.",
        "ordered_work": remaining, "all_nineteen_task_requirements_residual": True,
        "symbolic_planner_current_facts_added": 0, "full_task_satisfaction_or_convergence_or_source_equivalence_proved": False})
    save("result-summary.json", {"schema": "reviewed-source-worker-stage-result@1",
        "outcome": "Reviewed source nominations now reach native daemon context and a bounded verified catalog with callable source/fact readback; a same-owner prepare/review/resume driver path preserves current bindings.",
        "source": pin("source-manifest.json"), "patch": pin("changes.patch"),
        "files_changed": 6, "new_files": 5, "tests": pin("final-focused-validation.json"),
        "focused_distinct_passed": 292, "whole_repository_tests_passed_claimed": False,
        "preservation": pin("preservation-check.json"), "explicit_preservation_checks": 463,
        "worker_context": {
            "required_typed_artifact_and_digest_reference": True,
            "outer_git_identity_separate_from_semantic_scope_identity": True,
            "actual_signed_task_instruction_contract_ledger_native_query_AST_source_joins": True,
            "complete_catalog_default_byte_cap": 8192, "complete_catalog_hard_byte_cap": 16384,
            "full_contract_or_index_inserted_in_catalog": False,
            "shared_shell_quoted_inspector_prefix_with_independent_pins": True,
            "last_witness_guard_after_materialization_before_provider_dispatch": True,
            "absent_default_behavior_changed": False, "planner_current_facts_added": 0,
        },
        "driver_lifecycle": {
            "prepare_only_exports_empty_template_and_current_bindings_before_context_or_coding": True,
            "resume_reuses_original_signed_owner_task_native_index": True,
            "independent_instruction_contract_model_and_phase_control_checks": True,
            "canonical_bool_int_distinctions_and_final_source_task_fences": True,
            "fresh_Harbor_and_benchmark_review_pairs_refused_before_deployment": True,
            "unit_controls_qualified": True, "full_driver_phase_execution_qualified": False,
            "cumulative_two_phase_agent_budget_accounted": False,
            "production_initial_autoencoder_training_default_changed": False,
        },
        "actual_host_qualification": {"receipt": pin("host-worker-readback-02/qualification.json"),
            "actual_signed_admission_and_context_no_stubs": True,
            "native_daemon_compiler_signed_instruction_semantic_replay": True,
            "complete_catalog_bytes": host["complete_catalog_bytes"],
            "native_prompt_bytes": host["native_prompt_bytes"],
            "public_instruction_block_bytes": host["public_instruction_block_bytes"],
            "scope": "Genuine same-owner public fixture; its exporter execution used the explicitly retained pre-final-task-fence snapshot. Final fence tests and installed final-source execution are separate."},
        "installed_public_worker_qualification": {"receipt": pin("installed-worker-qualification-03/qualification.json"),
            "archive": pin("runtime-archive-verification.json"),
            "archive_sha256": archive["archive_sha256"], "archive_members_verified": archive["files_verified"],
            "installed_python_version": archive["runtime_python_version"],
            "actual_production_runtime_installation_and_worker_namespace_boundary": True,
            "actual_signed_preparation_symbolic_admission_context_and_final_exporter_source": True,
            "actual_native_daemon_compiler_signed_instruction_semantic_replay": True,
            "complete_catalog_bytes": installed["readback"]["complete_catalog_bytes"],
            "worker_UID_EUID": 1001, "private_owner_DB_open_denied_without_body_read": True,
            "actual_advertised_inspector_commands_executed": True,
            "successful_CLI_outputs": len(worker["cases"]), "independent_pin_refusals": len(worker["independent_pin_refusals"]),
            "cases": worker["cases"], "complete_output_bytes": sum(row["complete_output_bytes"] for row in worker["cases"]),
            "public_fixture_source_preserved": True, "original_tracked_source_and_HEAD_preserved": True,
            "external_network_detached_before_context_and_readback": True,
            "qualification_container_removed": installed["fresh_qualification_container_removed"],
            "original_Harbor_task_image_used": False, "task_verifier_or_benchmark_reward_executed": False},
        "retained_failures": {
            "admitted_context_01": "Genuine preparation/admission/context completed; test-driver uppercase metadata assertion failed and remains unqualified.",
            "host_worker_01": "Genuine native compilation/catalog succeeded; test-driver source_span lookup used the wrong level and remains unqualified.",
            "installed_01": "Fresh container harness attempted to create /app while using nonexistent /app as cwd; no runtime installation qualified.",
            "installed_02": "Runtime deployment passed; local fixture wrapper lacked Harbor-specific private container lookup. Corrected by direct production installer/qualification APIs in a fresh container.",
            "exporter_probe_01": "Inherited creation umask002 produced a group-writable new frontier; protected reader refused it. Production driver and qualification explicitly use022.",
            "unit_runner_and_explicit_stub_fixture_failures_retained": True,
            "earlier_failed_attempts_upgraded_to_success": False,
        },
        "limits": {"all_nineteen_requirements_residual": True, "review_authentication_claimed": False,
            "source_authentication_claimed": False, "same_owner_source_immutability_claimed": False,
            "source_semantics_or_source_to_model_equivalence_proved": False,
            "full_task_satisfaction_or_model_convergence_proved": False,
            "proof_or_execution_or_mutation_or_completion_authority": False,
            "provider_total_session_token_savings_established": False,
            "training_steps_in_manual_public_qualifications": 0, "provider_calls": 0,
            "prover_invocations": 0, "target_module_imports": 0, "official_task_verifier_invocations": 0,
            "old_or_live_owner_database_or_private_key_body_inspection": False,
            "internal_fresh_signing_API_operations_occurred": True,
            "historical_full_input_auditor_qualified_for_new_catalog_appendix": False,
            "default_production_training_branch_qualified_as_no_training": False,
            "remote_publication_performed": False, "original_dirty_checkout_or_git_index_mutated": False},
        "next_work": pin("next-work.json")})
    print(json.dumps({"result": pin("result-summary.json"), "next_work": pin("next-work.json")}))


if __name__ == "__main__":
    main()
