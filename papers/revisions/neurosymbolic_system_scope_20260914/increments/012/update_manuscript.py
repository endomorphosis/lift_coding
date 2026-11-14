"""Render measured incremental results and retain a numbered evidence snapshot.

Never runs experiments or overwrites the historical final manuscript.
"""
import argparse
import hashlib
import json
from pathlib import Path
import shutil

ROOT = Path(__file__).resolve().parent


def load(relative):
    return json.loads((ROOT / relative).read_text())


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--increment", required=True)
    args = parser.parse_args()
    assert args.increment.isdigit()
    snapshot = ROOT / "increments" / args.increment
    snapshot.mkdir(parents=True)
    sources = ["evals/context/results/summary.json", "evals/context/results/rows.json",
               "evals/routing_v2/summary.json", "evals/routing_v2/metering_audit.json",
               "evals/reuse/runs/development-v6/summary.json",
               "evals/reuse/runs/development-v6/cases.json",
               "evals/reuse/runs/development-v6/timing.json",
               "evals/compositional_v2/summary.json"]
    ctx, routing, reuse, native = [load(p) for p in (
        sources[0], sources[2], sources[4], sources[7])]
    sources.extend(["evals/persistence/summary.json", "evals/context/native_development/results_v1/summary.json"])
    persistence, dependency = load(sources[-2]), load(sources[-1])
    sources.append("evals/context/live_v1/summary.json")
    live_context = load(sources[-1])
    assert live_context["complete"] and live_context["observed_cells"] == 6
    sources.extend(["evals/procedures/summary.json", "evals/procedures/control_summary.json",
                    "evals/native_proof/runs/source-built-v1/summary.json"])
    procedures, procedure_control, native_proof = [load(p) for p in sources[-3:]]
    sources.extend(["evals/scorer_integrity/summary.json", "evals/scorer_integrity/saved_rescore.json",
                    "evals/native_proof/runs/horn-v1/honest_only_summary.json",
                    "evals/publication_baseline/run-v1/summary.json"])
    scorer, rescores, horn, publication = [load(p) for p in sources[-4:]]
    assert scorer["frozen_files_match"] and scorer["saved_records"] == len(rescores) == 14
    assert scorer["categories"]["adversarial"]["old_false_admissions"] == 5
    assert scorer["categories"]["adversarial"]["stronger_false_admissions"] == 0
    assert all(r["stronger_scorer_success"] == r["original_success"] for r in rescores)
    for row in rescores:
        path = ROOT.parents[2] / row["source_record"]
        assert hashlib.sha256(path.read_bytes()).hexdigest() == row["source_record_sha256"]
    assert horn["checks_passed"] and len(horn["positive_rows"]) == 3
    assert not horn["incomplete_investigation"]["custom_executable_run"]
    assert publication["returncode"] == 0 and publication["counts"]["passed"] == 47
    sources.extend(["evals/scorer_integrity/freeze.json", "evals/scorer_integrity/artifact_audit.json",
                    "evals/native_proof/runs/horn-v1/freeze.json",
                    "evals/publication_baseline/run-v1/freeze.json",
                    "evals/publication_baseline/run-v1/loaded_sources.json",
                    "evals/publication_baseline/run-v1/results.xml"])
    for row in horn["positive_rows"]:
        sources.extend(str(Path(row[k]).relative_to(ROOT)) for k in ("proof", "witness", "prove_receipt", "verify_receipt"))
    sources.extend(["evals/world_memory_development/runs/development-v1/summary.json",
                    "evals/world_memory_development/runs/development-v1/validation.json",
                    "evals/world_memory_development/runs/development-v1/compiler_identity_audit.json",
                    "evals/sealing_development/run-v1/summary.json",
                    "evals/sealing_development/run-v1/artifact_audit.json",
                    "evals/sealing_development/continuation-v1/summary.json"])
    world, world_validation, world_compiler, sealing, seal_validation, continuation = [load(p) for p in sources[-6:]]
    assert all(t["passed"] == t["cases"] == 11 for t in world["totals"].values())
    assert len([r for r in world["rows"] if r["arm"] != "producer"]) == 44
    assert sealing["complete"] and sealing["main_publications"] == 3
    assert continuation["complete"] and continuation["original_run_unchanged"]
    assert continuation["fresh_next_event_consumed_recovered_root"]
    assert world_validation["passed"] and world_validation["check_count"] == 893
    assert world_compiler["candidate_identity_mismatches"] == world_compiler["observation_identity_mismatches"] == 11
    assert seal_validation["checks_passed"] == 181
    sources.extend(["evals/sealing_development/preparation-timing-v1/summary.json",
                    "evals/sealing_development/phase_artifact_audit.json"])
    seal_timing = load(sources[-2])
    assert seal_timing["all_evidence_content_identical"]
    assert all(a["accepted"] == a["trials"] == 4 for a in seal_timing["arms"].values())
    sources.extend(["evals/world_memory_development/runs/compiler-continuation-v1/summary.json",
                    "evals/world_memory_development/runs/compiler-continuation-v1/validation.json",
                    "evals/world_memory_development/source_profiles/compiler_identity_v1/source.diff",
                    "evals/integrated_v1/context_qualification/results_v6_bounded_index/summary.json",
                    "evals/integrated_v1/context_qualification/audit_v6_bounded_index.json",
                    "evals/integrated_v1/context_qualification/results_v6_bounded_index/freeze.json",
                    "evals/integrated_v1/context_qualification/results_v5/outcome.json",
                    "evals/integrated_v1/context_qualification/results_v7_full_index/outcome.json",
                    "evals/integrated_v1/context_qualification/comparison_v5_v7_xml.json",
                    "evals/integrated_v1/context_qualification/merkle_node_index_v1.patch",
                    "evals/integrated_v1/public_issue_reproduction_v1/summary.json",
                    "evals/recruitment/verified_metadata_v1/summary.json",
                    "evals/recruitment/ancestry_v1/summary.json",
                    "evals/recruitment/repository_identity_v2/summary.json",
                    "evals/recruitment/repository_identity_audit.json"])
    world_cont = load("evals/world_memory_development/runs/compiler-continuation-v1/summary.json")
    world_cont_audit = load("evals/world_memory_development/runs/compiler-continuation-v1/validation.json")
    context_roundtrip = load("evals/integrated_v1/context_qualification/results_v6_bounded_index/summary.json")
    context_audit = load("evals/integrated_v1/context_qualification/audit_v6_bounded_index.json")
    assert world_cont["passed"] == world_cont["case_count_including_seed"] == 12
    assert world_cont["action_calls_including_seed"] == 19 and world_cont["service_process_count"] == 25
    assert world_cont_audit["passed"] and world_cont_audit["check_count"] == 1183
    assert context_roundtrip["all_roundtrips_passed"] and context_audit["all_checks_passed"]
    assert sum(r["cold_incremental_equal_cases"] for r in context_audit["cases"]) == 4
    assert sum(r["native_negative_controls"] for r in context_audit["cases"]) == 22
    full_context = load("evals/integrated_v1/context_qualification/results_v7_full_index/outcome.json")
    xml_comparison = load("evals/integrated_v1/context_qualification/comparison_v5_v7_xml.json")
    assert full_context["pyparsing_process"]["timed_out"]
    assert full_context["pyparsing_process"]["bound_seconds"] == 600
    assert xml_comparison["baseline_native_state_cid"] == xml_comparison["variant_native_state_cid"]
    assert xml_comparison["baseline_semantic_root_cid"] == xml_comparison["variant_semantic_root_cid"]
    assert xml_comparison["all_public_file_bytes_modes_equal"]
    for task in ("ns-hist-01-xmltodict", "ns-hist-02-pyparsing"):
        prefix = "evals/integrated_v1/context_qualification/results_v6_bounded_index/" + task + "/"
        sources.extend(prefix + name for name in ("producer.json", "consumer.json", "semantic_scope.json",
                       "retained_raw_inventory.json", "cold_incremental_identity_checks.json"))
    sources.extend(["evals/recruitment/arm64_qualification/run-v1/scoring-v2/score_summary.json",
                    "evals/recruitment/arm64_qualification/run-v1/artifact_audit.json",
                    "evals/recruitment/arm64_qualification/run-v1/nonexpected_error_triage.json"])
    benchmark = load(sources[-3])
    benchmark_audit = load(sources[-2])
    assert benchmark["qualified"] and benchmark["ordinary_native_imports"]
    assert not benchmark["native_algorithms_modified"] and not benchmark["initializer_bypass_used"]
    assert benchmark_audit["checks_passed"] == 180
    assert benchmark_audit["nonexpected_setup_errors_per_control"] == 8
    assert not benchmark_audit["all_collected_tests_error_free"]
    controls = {r["control"]: r for r in benchmark["controls"]}
    assert controls["gold"]["native_resolved"] and not controls["unfixed"]["native_resolved"]
    assert all(r["expected_checks_completed"] == 187 and r["expected_missing"] == 0
               and r["expected_errors"] == 0 for r in controls.values())
    sources.extend(["evals/integrated_v1/controller_qualification/development-v2/summary.json",
                    "evals/integrated_v1/controller_qualification/development-v2/audit.json",
                    "evals/integrated_v1/controller_qualification/development-v2/profile.json",
                    "evals/integrated_v1/context_qualification/routing_enrollment_v1/summary.json",
                    "evals/integrated_v1/context_qualification/routing_context_audit_v1.json",
                    "evals/recruitment/literature_exposure_v1.json"])
    controller = load(sources[-6])
    controller_audit = load(sources[-5])
    assert controller_audit["passed"] and not controller_audit["failed"]
    assert controller["event_count"] == 13 and controller["controller_invocations"] == 16
    assert controller["terminal_status_counts"] == {"accepted": 9, "effect_unknown": 1, "residual_pending": 2, "stale_parent": 1}
    assert controller["provider_dispatches"] == controller["native_sealing_calls"] == 0
    assert controller_audit["operation_counts"]["scorer_attempts"] == 30
    assert controller_audit["operation_counts"]["scorer_terminal_receipts"] == 29
    sources.extend([
        "evals/integrated_v1/controller_qualification/development-v3-attempt2/summary.json",
        "evals/integrated_v1/controller_qualification/development-v3-attempt2/audit_v3.json",
        "evals/integrated_v1/controller_qualification/development-v3-attempt2/REPORT.md",
        "evals/integrated_v1/controller_qualification/development-v3-attempt2-artifact-manifest.json",
        "evals/integrated_v1/context_qualification/repository_service_qualification_v1/qualification.json",
        "evals/integrated_v1/context_qualification/requests_public_enrollment_v1/summary.json",
        "evals/recruitment/arm64_qualification/requests5414/run-v4/score_summary.json",
        "evals/recruitment/arm64_qualification/requests5414/run-v4/artifact_audit.json",
        "evals/recruitment/arm64_qualification/requests5414/run-v4/environment_port.json",
        "evals/recruitment/arm64_qualification/requests5414/run-v4/distribution_continuity.json",
        "evals/recruitment/candidate_scoring_v1/qualification-v2/summary.json",
        "evals/recruitment/candidate_scoring_v1/endpoint_v2_network_diagnosis.json",
        "evals/recruitment/additional_metadata_v1/summary.json",
        "evals/recruitment/rebench_screen_v1/queue.json",
        "evals/recruitment/rebench_screen_v1/freeze.json",
        "evals/recruitment/rebench_ancestry_v1/summary.json",
        "evals/recruitment/rebench_identity_v1/summary.json",
        "evals/recruitment/rebench_screen_audit.json",
        "evals/recruitment/ADDITIONAL_RECRUITMENT.md",
    ])
    joined = load("evals/integrated_v1/controller_qualification/development-v3-attempt2/summary.json")
    joined_audit = load("evals/integrated_v1/controller_qualification/development-v3-attempt2/audit_v3.json")
    assert joined["events"] == 8 and joined["controller_invocations"] == 9
    assert joined["status_counts"] == {"accepted": 6, "residual_pending": 1, "stale_parent": 1}
    assert joined["native_publication_attempts"] == 7 and joined["native_recovery_CAS_calls"] == 1
    assert joined_audit["all_passed"] and joined_audit["check_count"] == 6424
    assert joined_audit["all_actual_scorer_processes"] == 42
    assert joined["provider_dispatches"] == joined["provider_tokens"] == 0
    repository_context = load("evals/integrated_v1/context_qualification/repository_service_qualification_v1/qualification.json")
    requests_context = load("evals/integrated_v1/context_qualification/requests_public_enrollment_v1/summary.json")
    assert repository_context["all_checks_passed"] and len(repository_context["checks"]) == 12
    assert requests_context["all_roundtrips_passed"] and len(requests_context["rows"]) == 2
    assert requests_context["source_substitutions"] == requests_context["provider_calls"] == 0
    for row in requests_context["rows"]:
        result = row["summary"]
        assert result["producer"]["declared_files"] == 97
        assert result["producer"]["python_files"] == 35
        assert result["consumer"]["all_checks_passed"]
        assert len(result["consumer"]["negative_controls"]) == 11
        prefix = "evals/integrated_v1/context_qualification/requests_public_enrollment_v1/" + row["id"] + "/"
        sources.append(prefix + "freeze.json")
        sources.extend(prefix + result["producer"]["task_id"] + "/" + name
                       for name in ("producer.json", "consumer.json"))
    benchmark5414 = load("evals/recruitment/arm64_qualification/requests5414/run-v4/score_summary.json")
    assert benchmark5414["qualified"] and benchmark5414["ordinary_native_imports"]
    controls5414 = {r["control"]: r for r in benchmark5414["controls"]}
    assert controls5414["gold"]["native_resolved"] and not controls5414["unfixed"]["native_resolved"]
    assert all(r["expected_checks_completed"] == 131 and r["expected_missing"] == 0
               and r["expected_errors"] == 0 and r["parsed_status_counts"].get("ERROR", 0) == 0
               for r in controls5414.values())
    candidate_endpoint = load("evals/recruitment/candidate_scoring_v1/qualification-v2/summary.json")
    assert not candidate_endpoint["qualified"]
    assert sum(r["control_passed"] for r in candidate_endpoint["native_controls"]) == 3
    assert all(r["passed"] for r in candidate_endpoint["negative_controls"])
    additional = load("evals/recruitment/additional_metadata_v1/summary.json")
    screen = load("evals/recruitment/rebench_screen_v1/queue.json")
    screen_audit = load("evals/recruitment/rebench_screen_audit.json")
    assert additional["candidate_rows_not_deduplicated_across_datasets"] == 22067
    assert not any(r["protected_columns_decoded"] for r in additional["datasets"])
    assert screen["metadata_pair_candidates"] == 53 and screen["primary_count"] == 16
    assert screen_audit["all_checks_passed"] and screen_audit["candidate_pairs"] == 16
    assert screen_audit["actual_forward_ancestry_results"] == 16
    assert screen_audit["current_identity_comparisons_to_prior"] == 448
    assert screen_audit["confirmatory_enrolled_families"] == 0
    assert all("x86_64" in task["image_name"]
               for row in screen["ranked_candidates"][:16] for task in row["tasks"])
    context_prefix = "evals/integrated_v1/context_qualification/"
    sources.extend(context_prefix + name for name in (
        "full_context_profiles_v11_audit.json", "audit_full_context_profiles_v11.py"))
    full_profiles = load(context_prefix + "full_context_profiles_v11_audit.json")
    assert full_profiles["all_checks_passed"] and len(full_profiles["profiles"]) == 5
    assert not full_profiles["full_pyparsing_roundtrip_complete"]
    assert full_profiles["literal_union_actual_predicates"]["all_equal"]
    assert full_profiles["literal_union_actual_predicates"]["actual_link_payloads_compared"] == 55859
    for relative, digest in full_profiles["input_sha256"].items():
        source = context_prefix + relative
        assert hashlib.sha256((ROOT / source).read_bytes()).hexdigest() == digest
        sources.append(source)
    sources.extend(context_prefix + name for name in (
        "full_state_identity_v12_audit.json", "audit_full_state_identity_v12.py",
        "state_identity_validation_v5/summary.json", "state_identity_v5.patch",
        "state_identity_cache_design_v5.md", "requests_public_reads_v1/summary.json"))
    full_state = load(context_prefix + "full_state_identity_v12_audit.json")
    assert full_state["all_audit_checks_passed"] and full_state["all_roundtrips_complete"]
    assert full_state["runtime_files_rehashed"] == 7255 and full_state["runtime_unchanged"]
    assert full_state["native_regressions_passed"] == 159
    for relative, digest in full_state["input_sha256"].items():
        source = context_prefix + relative
        assert hashlib.sha256((ROOT / source).read_bytes()).hexdigest() == digest
        sources.append(source)
    full_state_rows = {row["producer"]["task_id"]: row for row in full_state["rows"]}
    assert full_state_rows["ns-hist-02-pyparsing"]["producer"]["python_files"] == 154
    assert sum(len(row["consumer"]["negative_controls"]) for row in full_state_rows.values()) == 22
    assert sum(row["producer"]["declared_files"] for row in full_state_rows.values()) == 302
    assert all(row["consumer"]["all_checks_passed"] for row in full_state_rows.values())
    source_reads = load(context_prefix + "requests_public_reads_v1/summary.json")
    assert source_reads["all_checks_passed"] and source_reads["native_source_expansions"] == 4
    assert sum(row["exact_raw_bytes_returned"] for row in source_reads["rows"]) == 79942
    endpoint_prefix = "evals/recruitment/candidate_scoring_v1/"
    sources.extend(endpoint_prefix + name for name in (
        "qualification-v3/summary.json", "qualification-v3/audit.json",
        "qualification-v3/artifact_manifest.json", "registry_v3.json", "CONTRACT_V3.md",
        "cumulative_source_qualification_v1/summary.json"))
    endpoint3 = load(endpoint_prefix + "qualification-v3/summary.json")
    endpoint3_audit = load(endpoint_prefix + "qualification-v3/audit.json")
    assert endpoint3["qualified"] and all(row["control_passed"] for row in endpoint3["native_controls"])
    assert len(endpoint3["native_controls"]) == 4 and len(endpoint3["negative_controls"]) == 10
    assert endpoint3_audit["passed"] and endpoint3_audit["check_count"] == 94
    assert endpoint3_audit["artifact_count"] == 1175
    assert not endpoint3["adversarial_candidate_oracle_integrity_qualified"]
    cumulative_source = load(endpoint_prefix + "cumulative_source_qualification_v1/summary.json")
    assert cumulative_source["qualified"] and cumulative_source["actual_source_tree_matches_expected"]
    assert cumulative_source["source_files"] == 98 and cumulative_source["changed_paths"] == 3
    repository_seal_prefix = endpoint_prefix + "repository_sealing_qualification_v1/"
    sources.extend(repository_seal_prefix + name for name in (
        "summary.json", "audit.json", "freeze.json", "qualification_admission_v1.json",
        "qualified_source_inventory_v1.json", "scope_addendum.json", "SCOPE_ADDENDUM.md",
        "timing_projection_v1.json"))
    repository_seal = load(repository_seal_prefix + "summary.json")
    repository_seal_audit = load(repository_seal_prefix + "audit.json")
    repository_seal_scope = load(repository_seal_prefix + "scope_addendum.json")
    repository_seal_admission = load(repository_seal_prefix + "qualification_admission_v1.json")
    repository_seal_timing = load(repository_seal_prefix + "timing_projection_v1.json")
    assert repository_seal["qualified"] and repository_seal_audit["passed"]
    assert repository_seal_audit["check_count"] == 275
    assert all(row["passed"] for row in repository_seal_audit["checks"])
    assert repository_seal["actual_native_scorer_invocations"] == 6
    assert repository_seal["complete_source_files_each"] == [97, 97]
    assert repository_seal["actual_crash_exit"] == 94 and repository_seal["final_generation"] == 1
    assert repository_seal["fresh_native_parent_read_and_exact_source_restoration"]
    assert len(repository_seal["negative_controls"]) == 4
    assert all(row["rejected_before_scorer_replay"] for row in repository_seal["negative_controls"])
    assert repository_seal["proof_mode"] == "integrity_only" and not repository_seal["signed_receipts"]
    assert repository_seal_scope["instance_id"] == "psf__requests-6028"
    assert not repository_seal_scope["requests_5414_to_6028_model_trajectory_executed"]
    assert repository_seal["provider_calls"] == repository_seal_timing["provider_calls"] == 0
    for field, name in (("qualification_summary_sha256", "summary.json"),
                        ("qualification_audit_sha256", "audit.json"),
                        ("qualification_freeze_sha256", "freeze.json")):
        assert repository_seal_admission[field] == hashlib.sha256((ROOT / repository_seal_prefix / name).read_bytes()).hexdigest()
    for field, name in (("admission_sha256", "qualification_admission_v1.json"),
                        ("addendum_sha256", "SCOPE_ADDENDUM.md")):
        assert repository_seal_scope[field] == hashlib.sha256((ROOT / repository_seal_prefix / name).read_bytes()).hexdigest()
    for identities in ("service_sources", "native_loaded_sources"):
        for path, digest in repository_seal_admission[identities].items():
            assert hashlib.sha256(Path(path).read_bytes()).hexdigest() == digest
    for phase, value in repository_seal_timing["effect_phases"].items():
        observations = [row for row in repository_seal_timing["effect_receipt_bindings"] if row["stage"] == phase]
        assert len(observations) == value["count"]
        assert abs(sum(row["elapsed_seconds"] for row in observations) - value["seconds"]) < 1e-9
    phase_seconds = sum(row["seconds"] for row in repository_seal_timing["effect_phases"].values())
    operation_seconds = sum(row["elapsed_seconds"] for row in repository_seal["operations"])
    assert abs(operation_seconds - repository_seal_timing["native_service_process_seconds_sum"]) < 1e-9
    assert abs(phase_seconds + operation_seconds - repository_seal_timing["measured_sequential_phase_interval_sum_seconds"]) < 1e-9
    assert not repository_seal_timing["nested_native_grading"]["add_to_phase_total"]
    assert repository_seal_timing["nested_native_grading"]["container_seconds_sum"] == repository_seal_audit["native_scorer_container_seconds_sum"]
    sources.extend(["evals/recruitment/replay_rebench_screen_audit.py",
                    "evals/recruitment/rebench_screen_replay_audit_v2.json"])
    replay_screen = load(sources[-1])
    assert replay_screen["all_checks_passed"] and replay_screen["check_count"] == 629
    zarr_prefix = "evals/recruitment/rebench_environment_v1/zarr/"
    sources.extend(zarr_prefix + name for name in (
        "native_qualification_v1/summary.json", "native_qualification_v1/audit.json",
        "native_qualification_v1/execution-freeze.json", "native_qualification_v1/qualified_native_source_inventory.json",
        "NATIVE_QUALIFICATION_REPORT.md", "arm-port-v1-summary.json", "arm-port-v2-summary.json",
        "arm-port-v3-summary.json", "installed-metadata-v2-summary.json", "public-collection-diagnosis-v1.json",
        "git_port_v1/summary.json", "git_port_v2/summary.json"))
    zarr = load(zarr_prefix + "native_qualification_v1/summary.json")
    zarr_audit = load(zarr_prefix + "native_qualification_v1/audit.json")
    assert zarr["qualified"] and zarr_audit["all_checks_passed"]
    assert zarr["actual_control_attempts"] == zarr_audit["actual_native_control_calls"] == 4
    assert not zarr["candidate_endpoint_qualified"] and not zarr["confirmatory_enrolled"]
    assert zarr["provider_calls"] == 0 and all(row["control_matched_expectation"] for row in zarr["receipts"])
    assert zarr_audit["summary_sha256"] == hashlib.sha256((ROOT / zarr_prefix / "native_qualification_v1/summary.json").read_bytes()).hexdigest()
    assert zarr["freeze_sha256"] == hashlib.sha256((ROOT / zarr_prefix / "native_qualification_v1/execution-freeze.json").read_bytes()).hexdigest()
    assert abs(sum(row["container_elapsed_seconds"] for row in zarr["receipts"]) - zarr_audit["grader_container_wall_seconds_sum"]) < 1e-9
    for row in zarr["receipts"]:
        assert row["designated_completed"] == row["designated_total"]
        assert row["candidate_source_stable_during_grading"] and row["environment_versions_unchanged"] and row["protected_inputs_unchanged"]
    zarr_endpoint_prefix = zarr_prefix + "candidate_endpoint_v1/"
    sources.extend(zarr_endpoint_prefix + name for name in (
        "admission_v2.json", "CONTRACT_V2.md", "service_v2.py", "inventory_v1.py",
        "qualification_v3/summary.json", "qualification_v3/audit.json",
        "qualification_v1/summary.json", "endpoint_v1_failure_diagnosis.json",
        "qualification_v2/preparation_failure.json"))
    zarr_endpoint = load(zarr_endpoint_prefix + "admission_v2.json")
    zarr_endpoint_summary = load(zarr_endpoint_prefix + "qualification_v3/summary.json")
    zarr_endpoint_audit = load(zarr_endpoint_prefix + "qualification_v3/audit.json")
    assert zarr_endpoint["qualified"] and zarr_endpoint_summary["qualified"] and zarr_endpoint_audit["all_checks_passed"]
    assert zarr_endpoint["checks_passed"] == len(zarr_endpoint_audit["checks"]) == 190
    assert zarr_endpoint_summary["attempted_service_controls"] == 19
    assert zarr_endpoint_audit["actual_native_grader_calls"] == 6
    assert zarr_endpoint_audit["predispatch_negative_controls"] == 10
    assert zarr_endpoint_audit["pregrader_wrong_tree_containers"] == 2
    assert zarr_endpoint_audit["duplicate_id_controls"] == 1
    assert not zarr_endpoint["confirmatory_enrolled"] and not zarr_endpoint["non_python_candidate_edit_transport_qualified"]
    assert zarr_endpoint["provider_calls"] == zarr_endpoint_summary["automatic_retries"] == 0
    for key, name in (("audit_sha256", "audit.json"), ("summary_sha256", "summary.json")):
        assert zarr_endpoint[key] == hashlib.sha256((ROOT / zarr_endpoint_prefix / "qualification_v3" / name).read_bytes()).hexdigest()
    for path, digest in zarr_endpoint["service_sources"].items():
        assert hashlib.sha256(Path(path).read_bytes()).hexdigest() == digest
    for row in zarr_endpoint["reference_projection_scope"]:
        assert row["full_reference_production_and_base_public_state_equal"]
        assert row["original_designated_checks_rerun_on_projection"] and not row["full_patch_transport_qualified"]
    assert abs(sum(row["container_elapsed_seconds"] for row in zarr_endpoint_audit["native_controls"]) - 14.426196047919802) < 1e-9
    requests_prefix = "evals/integrated_v1/controller_qualification/requests-cold-v1/"
    sources.extend(["evals/integrated_v1/controller_qualification/analyze_requests_cold_v1.py",
                    requests_prefix + "root_fixed_cohort_analysis_v1.json",
                    requests_prefix + "root_merge_bound_reconstruction_v1.json",
                    requests_prefix + "driver_interruption_v1.json",
                    requests_prefix + "driver_reconciliation_freeze.json",
                    requests_prefix + "root_final_ledger_audit_v2.json",
                    "evals/integrated_v1/controller_qualification/audit_repository_run_v2.py"])
    requests_cold = load(requests_prefix + "root_fixed_cohort_analysis_v1.json")
    assert requests_cold["all_checks_passed"] and requests_cold["all_usage_complete"]
    assert requests_cold["actual_provider_posts"] == 7 and requests_cold["provider_total_tokens"] == 108981
    requests_ledger_audit = load(requests_prefix + "root_final_ledger_audit_v2.json")
    assert requests_ledger_audit["all_checks_passed"] and requests_ledger_audit["cohort_terminal"]
    assert requests_ledger_audit["provider_accounting_complete"] and requests_ledger_audit["effect_accounting_complete"]
    assert not requests_ledger_audit["invocation_wall_accounting_complete"]
    assert len(requests_ledger_audit["checks"]) == 1769 and requests_ledger_audit["unique_scorer_service_receipts"] == 16
    for arm in requests_ledger_audit["arms"]:
        independently_projected = next(row for row in requests_cold["arms"] if row["arm"] == arm["arm"])
        assert arm["usage"] == independently_projected["usage"]
    assert len(requests_cold["events"]) == 8 and not requests_cold["all_invocation_timing_complete"]
    requests_arms = {row["arm"]: row for row in requests_cold["arms"]}
    assert all(row["accepted_nodes"] == 1 and not row["complete_trajectory"] for row in requests_arms.values())
    for relative, digest in requests_cold["inputs_sha256"].items():
        source = requests_prefix + relative
        assert hashlib.sha256((ROOT / source).read_bytes()).hexdigest() == digest
        sources.append(source)
    incremental_failure_prefix = context_prefix + "results_v13_full_pyparsing_incremental/"
    sources.extend([context_prefix + "full_pyparsing_failure_v13_audit.json",
                    context_prefix + "audit_full_pyparsing_failure_v13_v2.py",
                    context_prefix + "full_pyparsing_incremental_v13.py",
                    incremental_failure_prefix + "terminal_outcome.json",
                    incremental_failure_prefix + "runtime_source_manifest.json"])
    incremental_failure = load(context_prefix + "full_pyparsing_failure_v13_audit.json")
    assert incremental_failure["all_audit_checks_passed"] and not incremental_failure["qualification_passed"]
    assert incremental_failure["outcome"]["changed_edge_records"] == 1568
    assert incremental_failure["blocks"]["shared_byte_equal"] == 65856
    assert incremental_failure["blocks"]["cold_only_cids"] == incremental_failure["blocks"]["incremental_only_cids"] == 2016
    assert incremental_failure["runtime_files_rehashed"] == 7255
    for relative, digest in incremental_failure["inputs_sha256"].items():
        source = incremental_failure_prefix + relative
        assert hashlib.sha256((ROOT / source).read_bytes()).hexdigest() == digest
        # Full immutable block/state stores stay in the retained experiment;
        # each paper snapshot carries their verified hash manifest and receipts.
        if Path(relative).name not in ("blocks.sqlite", "state.json"):
            sources.append(source)
    guard_prefix = context_prefix + "results_v14_full_pyparsing_resolution_guard/"
    sources.extend([guard_prefix + "summary.json", context_prefix + "full_pyparsing_resolution_guard_v14_audit.json",
                    context_prefix + "audit_full_pyparsing_resolution_guard_v14.py", context_prefix + "REPORT_V14.md"])
    guard = load(guard_prefix + "summary.json")
    guard_audit = load(context_prefix + "full_pyparsing_resolution_guard_v14_audit.json")
    assert guard["cold_incremental_equivalence_passed"] and guard_audit["all_audit_checks_passed"]
    assert guard["every_actual_block_byte_equal"] and guard_audit["earlier_v5_cold_output_also_exactly_equal"]
    assert guard["blocks_compared"] == guard_audit["blocks_compared_per_output"] == 67872
    assert guard["block_bytes_compared"] == guard_audit["block_bytes_compared_per_output"] == 112728034
    assert guard_audit["reuse"]["reused_paths"] == 20 and guard_audit["reuse"]["rescanned_paths"] == 134
    assert guard_audit["reuse"]["reused_symbols"] == 172 and guard_audit["reuse"]["reused_frontend_edges"] == 1428
    assert guard_audit["source_controls_passed_new_workers"] == 9 and guard_audit["runtime_files_rehashed"] == 7255
    assert guard_audit["qualification_controls_per_profile"] == 7 and guard_audit["native_regression"]["returncode"] == 1
    assert guard_audit["provider_calls"] == guard_audit["raw_substitutions"] == 0
    for relative, digest in guard_audit["inputs_sha256"].items():
        source = context_prefix + relative
        assert hashlib.sha256((ROOT / source).read_bytes()).hexdigest() == digest
        if Path(relative).name not in ("blocks.sqlite", "state.json"):
            sources.append(source)
    archive_prefix = "evals/native_proof/archive_integration_v1/"
    sources.extend(archive_prefix + name for name in (
        "run.py", "reader.py", "validate.py", "README.md", "run-v1/summary.json", "run-v1/audit.json",
        "run-v1/freeze.json", "run-v1/statement_freeze.json", "run-v1/statement.json", "run-v1/events.json"))
    archive_proof = load(archive_prefix + "run-v1/summary.json")
    archive_audit = load(archive_prefix + "run-v1/audit.json")
    assert archive_proof["status"] == "qualified_bounded_archive_consumption"
    assert archive_proof["accepted_events"] == 4 and archive_proof["receipt_units_per_event"] == 5
    assert archive_proof["honest_proofs"] == archive_proof["native_pairing_verifications"] == 1
    assert archive_proof["provider_calls"] == archive_proof["fresh_scorer_calls"] == 0
    assert len(archive_proof["controls"]) == 7 and all(row["rejected"] for row in archive_proof["controls"])
    assert archive_audit["all_checks_passed"] and archive_audit["check_count"] == 218
    assert archive_audit["native_pairing_verifications_added"] == 1
    for relative, digest in archive_audit["input_sha256"].items():
        source = archive_prefix + "run-v1/" + relative
        assert hashlib.sha256((ROOT / source).read_bytes()).hexdigest() == digest
        sources.append(source)
    assert procedure_control["independently_replayed_cells"] == 16
    assert native_proof["positive_proofs"] == 3 and native_proof["ordinary_rejections"] == 8
    assert persistence["observations"]["same_attempt_not_executed_twice"]
    assert dependency["cold_incremental_root_matches"] == dependency["cold_incremental_comparisons"] == 12
    # Regenerate routing totals from all terminal cells, preserving zero-call paths.
    cells = [json.loads(p.read_text()) for p in sorted((ROOT / "evals/routing_v2/results").glob("*.json"))
             if not p.name.endswith(".local.json")]
    assert len(cells) == routing["scheduled_cells"] == 8
    for arm in ("baseline", "system"):
        rows = [r for r in cells if r["arm"] == arm]
        assert sum(r["success"] for r in rows) == routing["arms"][arm]["successes"]
        assert sum(r["provider_calls"] for r in rows) == routing["arms"][arm]["provider_calls"]
        assert sum(r["normalized_usage"]["total_tokens"] for r in rows) == routing["arms"][arm]["total_tokens"]
        sources.extend(str(p.relative_to(ROOT)) for p in (ROOT / "evals/routing_v2/results").glob(arm + "-*.json"))
    receipts = list((ROOT / "evals/routing_v2/results/provider").glob("*/result.json"))
    assert len(receipts) == 6
    for p in receipts:
        r = json.loads(p.read_text())
        assert r["status"] == "response" and r["served_model"] == "grok-4.6"
        assert r["usage"]["total_tokens"] == r["normalized_usage"]["total_tokens"]
        sources.extend([str(p.relative_to(ROOT)), str(p.with_name("request.json").relative_to(ROOT))])
    # The paired residual requests are byte-identical canonical envelopes.
    for name in ("clamp_interval", "stable_deduplication"):
        folder = ROOT / "evals/routing_v2/results/provider"
        assert (folder / ("baseline-" + name) / "request.json").read_bytes() == (folder / ("system-" + name) / "request.json").read_bytes()
    assert ctx["total_substituted_windows"] == 0
    assert native["artifact_verification"]["valid"]
    assert reuse["matched_cases"] == reuse["case_count"] == 14
    counts = ctx["message_content_token_totals"]
    a, b = routing["arms"]["baseline"], routing["arms"]["system"]
    reduction = 100 * (1 - b["total_tokens"] / a["total_tokens"])
    text = r"""\section{Incremental system evaluation}
\label{sec:incremental-evaluation}

The following evaluations extend the original architecture questions. They are
development measurements and local qualification, separate from the historical
cold experiment and from any future confirmatory population. Their profiles
and source versions are explicit; a partial combined controller is qualified
below, while the complete matched system comparison remains open.

\paragraph{Context substitution opportunity.}
We reconstructed all sixteen historical A/B request commitments across eight
unique families and checked the selected public source against its hashes.
All 254 selected windows were protected editable or test source; there were
zero eligible unchanged-dependency files and zero substituted windows.
The guarded substitution adapter therefore retained the raw source. Saved
native packets contained no explicit obligation CIDs and 14,471 unresolved
dependency-edge occurrences. Instruction text was retained, but this cohort
cannot establish explicit obligation preservation or dependency compression.

Using \texttt{tiktoken} 0.12.0 with \texttt{o200k\_base}, exact tokenization of
system/user message content totaled @RAW@ for A, @ADD@ for B, and @SUB@ for
guarded substitution C: increases of @ADDINC@\% and @SUBINC@\% over A.
These counts exclude chat-template overhead and output, and are not Grok
provider usage. A second named encoding gives the same direction.
Eighteen constructed adapter controls separately check expansion and rejection;
they do not qualify a native producer. This result identifies a population
requirement: a compression experiment must include unchanged dependencies that
can actually be replaced under its stated policy.

\paragraph{Native dependency context and bounded projection.}
Three authored multi-module repositories supply six fresh native exact
dependency admissions. Twelve cold/incremental index and semantic-bundle root
comparisons agree; dependency edits invalidate prior capsules and unknown-call
mutations require raw fallback. Full transported native capsules total
@FULLCAPSULES@ serialized context-content
tokens versus @DEPROW@ for raw source. A new restricted projection instead
transports source-bound integer equations. Six separate Z3 equivalence checks
and 252 concrete source executions check that projection; its @EQUATIONS@
tokens are @EQUATIONRED@\% below raw. Plain AST source compaction totals
@ASTTOKENS@ tokens. These are named-encoding offline counts, not provider savings.
The equation profile excludes floats, custom objects, side effects and unsupported
syntax. The compact projection is an evaluated addition; the full native capsule
payload itself is larger than raw source in these examples.

\paragraph{Repository context custody and preparation cost.}
A separate native producer/consumer qualification retains all 302 regular files
across the XML and pyparsing development snapshots, including unparsed source.
Its bounded semantic scope analyzes one of six and five of 154 Python files,
respectively; four dependency capsules grant no source omission. Four
cold/incremental root-and-block comparisons agree, four exact source expansions
execute, and 22 negative controls reject. An added caller checks required-source
CIDs and current bytes because native freshness omits that mapping; native
``sufficient'' flags are not behavioral authority. Full pyparsing scanning
produces 3,957 symbols and 55,859 edges, but the unmodified producer process does
not finish within its 600-second bound. Hoisting a repeated immutable
node-CID index preserves the full XML state/root and reduces its preparation
from @XMLBASE@ to @XMLOPT@ seconds in one observation per profile. Full pyparsing
still reaches the 600-second bound after that change. Source retention and
bounded integration therefore do not establish affordable whole-repository
preparation, context compression or repair efficacy. Three later isolated
profiles add a fixed-profile CID encoder, cached syntax validation and an exact
literal-union predicate. Across all five profiles XML state/root identity is
unchanged and every native consumer passes; each full pyparsing producer still
hits the process deadline. In the last profile the producer writes its result
at 597.222 seconds before the 600.202-second termination; the native consumer
does not run. An earlier stage diagnostic had also assembled and verified a
full bundle before timing out in source-binding reads. Missing final output
therefore does not prove that bundle construction itself failed.

The literal-union change preserves all 55,859 actual link predicates against
3,957 node CIDs, an embedded-CID rejection, 1,235 constructed comparisons and
64 native regressions. The independently validated full bundle has 67,872
blocks and agrees with the last producer's state/root. Its 72.358 versus 2.834
seconds measure only one diagnostic predicate pass per implementation on a
shared host; they are not a whole-pipeline speedup estimate.

A generic current-repository service separately checks exact source inventory,
file modes and objective/request identities. Twelve controls pass across three
XML preparations: a source change requires new state/root/pack identities,
whereas an objective-only change retains state/root and creates a new pack.
Both public Requests nodes then complete actual native producer/consumer
roundtrips, retaining 97 files each and scanning all 35 declared Python files.
Eleven negative controls pass per node; neither node permits any raw-source
omission. These are context and custody checks, with zero provider calls and
no repair-quality or compression comparison.
Four subsequent Requests API expansions return 79,942 exact raw bytes across
two real read processes, preserving source, request, freeze and objective
identities. They add no omissions or model calls.

A sixth isolated profile memoizes identity only within an exact immutable
native state instance under frozen codec/runtime bindings. Both full producer
processes and their separate native consumers now complete. XML preparation
takes @FULLXMLPREP@ seconds; pyparsing takes @FULLPYPREP@ seconds, with
@FULLPYCPU@ CPU seconds. The latter producer process takes @FULLPYPROCESS@
seconds and its consumer @FULLPYCONSUMER@ seconds. All 302 regular files and
11,781,935 bytes are materialized; pyparsing's additional opaque symlink is
retained without following it. Both sources' previous available state/root
identities agree, including the independently checked 67,872-block pyparsing
bundle. All 22 binding/tampering controls pass and all 7,255 frozen runtime
source files remain unchanged. Zero source omissions and zero signed receipts
are retained, along with the unresolved semantic frontier.

The profile passes 159 native regressions. Separate full XML unchanged,
comment-change cold and comment-change incremental states preserve serialized
identities and all 1,992 reachable blocks across the parent and memoized
profiles. Each profile performs twenty actual source materializations and
rejects twenty corrupt-source reads. This qualifies immutable-object identity
caching, not execution/proof reuse or a defense against reflective mutation of
frozen objects. The successful full run establishes completion within the bound, not a
replicated speedup or token benefit; the five previous deadlines remain results.

A subsequent frozen full-pyparsing comment-change comparison fails cold versus
incremental equality. Its three workers complete within a separately declared
900-second bound: baseline 656.008 seconds, changed cold 609.801 seconds and
changed incremental 784.021 seconds. Baseline and changed-cold workers run
concurrently on the shared host; incremental restoration, full source guards,
native previous-state/bundle loading, persistence and process exit are included
in its worker interval. Earlier driver enrollment copy/freeze creation is not
separately timed. These observations establish no incremental speedup.

The changed snapshot, symbols and artifacts agree, but 1,568 of 55,859 edge
records differ: 1,564 ambiguous candidate edges change resolution metadata from
\texttt{finite\_may} to \texttt{definite}, and four derived references change
with their edge identities. All retain conservative confidence and multiple
candidates. Consequently state and semantic-root identities differ. Independent
comparison reads every persisted block: 65,856 shared CIDs have identical bytes,
with 2,016 distinct CIDs on each side, covering links, capsules and their indexes
and roots. Both stores contain 67,872 blocks; their payloads total 112,728,034
cold versus 112,724,906 incremental bytes. Ten source-read controls pass and
7,255 runtime files remain unchanged. The driver exits one at the equality
assertion after all workers exit zero; this is a retained graph-metadata failure,
not another preparation timeout. Downstream authorization consequences require
separate consumer tracing; the mismatch alone does not establish an execution
soundness failure. This result motivates the separate correction below.

A subsequent isolated guard refuses previous-state frontend reuse when graph
projection has already replaced a lexical target with a concrete symbol.
Such paths are reanalyzed from current source before whole-inventory resolution;
the guard does not simply preserve stale resolution metadata. Seven changing
inventory controls preserve state, roots, all block bytes and explanations.
The full pyparsing comment-change comparison then restores exact serialized
state/root equality and all 67,872 block payloads (112,728,034 bytes), also
matching the earlier cold output. It reuses 20 of 154 Python paths, 172 symbols
and 1,428 original frontend edges, while rescanning 134 paths. These counts
are not omitted source bytes or avoided execution checks.

The two fresh workers run concurrently under unchanged 900-second bounds:
cold takes 437.699 seconds and guarded incremental 614.522 seconds. The latter
includes 107.173 seconds of prior-state restore/reverification and 55.736
seconds of scanning; graph construction and full verification still execute.
The earlier 656.008-second baseline preparation is reused as an artifact and
remains a separately incurred cost. Enrollment copying/freezing is not timed;
the subsequent independent byte audit takes 3.625 seconds. Nine new source
controls pass and 7,255 runtime file digests remain unchanged. Native regression
tests retain 187 passes and one failure: an existing performance expectation
requires reuse of a path that this correctness guard deliberately rescans.
An earlier invalid authored fixture is also retained. The native explanation
consumer loses an ambiguity limitation in the failed earlier profile, but no
execution-authorization consequence is established. This is a conservative
correctness fallback, with zero source omissions or provider calls. Lossless
frontend observations and useful incremental economics remain separate work.

\paragraph{Live context substitution.}
The three dependency-bearing development repositories also support a matched
raw-versus-equation repair pilot. Both arms pass all three separate cold
behavioral checks; all six requests return usage. Provider input totals are
@LIVEINPUTRAW@ raw versus @LIVEINPUTCOMPACT@ compact (@LIVEINPUTRED@\% fewer),
and total usage is @LIVETOTALRAW@ versus @LIVETOTALCOMPACT@ (@LIVETOTALRED@\%
fewer). Both arms use three requests with the same Grok 4.6 low-effort profile
and resource ceilings as the routing pilot. Cached-input totals differ, so
charge differences cannot be attributed solely to compaction. This tests a
restricted, verified representation on trivial constructed repairs; dynamic
source expansion and broader repository quality remain unmeasured. The result
is separate from, and must not be added to, the routing reduction.

\paragraph{Checked symbolic closure and live residuals.}
A new development caller invokes the native Python analyzer, bounded CEGIS
repair, visible behavioral checks and native routing. Four constructed tasks
include false success without observation, swallowed backend failure, interval
clamping and stable deduplication. Both arms receive the same source, objective
and public checks; separate Docker execution scores broader behavioral checks.
The first two defects fit the declared deterministic grammar. The remaining two
require the same model residual in both arms. Internal CEGIS marker gates are
not counted as theorem proofs; behavioral checks justify only these bounded
obligations.

\begin{table}[htbp]
\centering
\caption{Constructed four-task routing development comparison. One observation
per task and arm; no population inference.}
\label{tab:routing-development}
\begin{tabular}{lrrr}
\toprule
Arm & Independently passed & Model calls & Total provider tokens \\
\midrule
Model first & @ASUCCESS@/4 & @ACALLS@ & @ATOKENS@ \\
Symbolic first plus residual & @BSUCCESS@/4 & @BCALLS@ & @BTOKENS@ \\
\bottomrule
\end{tabular}
\end{table}

All six Grok 4.6 requests returned usage, under the same low-effort profile,
\texttt{max\_tokens=2048} request parameter and 240-second deadline, without retries.
The observed reduction is @REDUCTION@\% on this suite. Eliminating two requests
accounts for 2,282 baseline tokens; response variation on the residual tasks
accounts for the remaining 153-token net difference. Provider cache state was
not controlled. There were no auxiliary workflow model calls or model-assisted
setup in this caller; experiment authoring and implementation effort are outside
that runtime denominator. The initial expired-credential attempt dispatched
zero requests and remains a separate development record. General repository
performance and full-system setup amortization remain unmeasured.

\paragraph{Supplementary scorer validation.}
A post-development audit exposes five false admissions among six crafted
incorrect candidates in the original pilot scorers. Candidate interference
with oracle helpers or premature process termination could masquerade as
passing execution. A new isolated scorer separates the oracle from the candidate
worker, restricts public dependency imports and requires observed calls and
positive completion. It rejects all six crafted candidates and all seven
unrepaired controls. All ten unique saved candidate bodies still pass, preserving
the eight routing and six context record outcomes above. This supplementary
rescore supports these saved outcomes; the small control set does not establish
general scorer robustness. Original scorers and observations remain retained.

\paragraph{Lifecycle-preserving test reuse.}
A proposed local evaluation adapter uses native cache admission and Ed25519
runner attestations issued only after actual passing setup/call/teardown.
Its explicitly enrolled pure workload and immutable fixture profile support
valid call-phase reuse while setup and teardown still execute. Fourteen
prespecified cases cover unchanged work, source/test/fixture/configuration/
environment mutations, missing or tampered evidence, revocation, unsupported
fixture values and lifecycle failure. All fourteen match separate cold-process
outcomes. Reuse followed by failing teardown correctly fails the whole item;
the result is not zero-error evidence for arbitrary pytest programs.

Five alternating warm/cold timing pairs omit all five warm test-body executions
while retaining five setups and teardowns in each arm. Total host wall time was
@COLD@ seconds cold and @WARM@ seconds warm, excluding the separately recorded
prime and issuance costs. This small descriptive difference does not establish
a reliable net speedup or token savings. The default production plugin probe
executed the body in both write and read/write modes and produced no positive
reuse. Thus the result qualifies the proposed bounded adapter, not deployment
of the native default reuse path. Earlier failed development invocations and
the historical false-reuse observation remain retained.
The measured @PRIME@-second cold prime and @ISSUANCE@-second issuance exceed
the observed wall-time saving over these five repetitions; a net benefit at
that horizon is not demonstrated.

\paragraph{Persistent work across process termination.}
Three actual processes exercise the native session journal/checkpoint with
the same checked deterministic caller. Duplicate pending notifications coalesce.
The first process exits abruptly after one completion; the next resumes exactly
one unfinished scan, and a third restart finds no pending work. Each actual
execution passes the independent behavioral oracle, and no original attempt
executes twice. However, a fresh notification for a completed snapshot schedules
and executes analysis again. Journal continuity is supported by this case;
completed-result memoization, accepted-root publication and cross-task token
savings are not established.

\paragraph{Publication and recovery qualification.}
Forty-seven existing source-shipped tests pass in a fresh compatible native
profile. They cover immutable-root publication, stale writers, competing CAS
updates, seal storage and restart recovery at injected persistence boundaries.
These are constructed software qualifications, including placeholder proof
records and exception-based interruptions. They do not establish a newly
integrated evidence-producing workflow, actual process-kill tolerance at each
boundary, or measured parallel-sealing savings.

\paragraph{Evidence-backed sealing and completed recovery.}
A new caller independently replays finite computation receipts, checks exact
source/input/policy bindings and complete coverage, then invokes native
integrity-only seal verification and publication. A full checkpoint and two
delta seals become successive current roots; a competing delta loses stale
parent CAS. Four prepared states cover 700 independently checked state/input
observations, using five computation subprocesses and three unchanged-receipt
reuses. Five constructed mutations reject. Native digest verification alone
accepts three internally consistent but semantically wrong or stale receipts;
the caller's independent replay and bindings are therefore substantive gates.

Two real process terminations preserve the expected accepted roots. Native
recovery recognizes a valid pre-CAS seal but leaves its transition pending;
retrying the same publication is refused. A separately evaluated recovery
caller rechecks the persisted evidence and completes native CAS/WAL phases
with zero new computation calls. A subsequent fresh process consumes that
accepted root and publishes the next changed state, reaching a four-seal chain.
This establishes bounded continuation under an explicit added caller. It does
not establish native automatic recovery, theorem proofs, power-loss tolerance
or a compute saving: the independent receipt checker still runs on reuse.
Four paired trials separately compare actual preparation of two cold operations:
all eight preparations pass with identical receipt and seal content. Median
preparation time is @SEALSEQ@ ms sequential versus @SEALPAR@ ms parallel;
maximum sampled aggregate process RSS rises from @RSSSEQ@ to @RSSPAR@ MiB.
The host is not exclusive, sampled RSS counts shared pages per process, and
these tiny preparation trials measure neither publication latency nor a
whole-system speedup.

\paragraph{Procedure synthesis and stored candidates.}
Native ProcedureCegis adds missing validation operations to a bounded scaffold;
a new evaluation executor performs those checks on concrete integer-sequence
inputs. A development body store reuses candidates only under matching native
request bindings, including actual source-catalog bytes and policy. In eight
units, cold synthesis and stored-candidate arms each complete seven units with
3,883 correct fresh-query decisions and zero false admissions. The unsupported
parity unit yields 554 abstentions in each arm. Stored candidates reduce search
from eight to six synthesis calls and from 29 to 23 tried candidates. However,
a separately frozen post-development fixed-template control matches the same
quality with no synthesis. These cases demonstrate reusable search results,
not an advantage over simple templates. Fresh-process replay, source-binding
changes and scaffold sensitivity are checked independently. This is a new
bounded executor/store integration, not a production-certified procedure
runtime, and uses no model calls.

\paragraph{World-state memory and actual subsequent actions.}
A native typed transition producer, persistent block/SQLite store and admission
path are connected by a new evaluation dispatcher. Eleven tasks per arm run in
fresh interpreters against a closed three-action integer service; selected
actions always execute and their current outputs are independently checked.
All 44 task/arm outcomes pass. Native memory uses 16 action executions versus
27 without memory, but exact JSON retrieval and complete-condition templates
also use 16. Charging each arm the common three-action seed gives 19 versus
30. Changed state, source and declared environment invalidate prior observations;
fallback creates fresh evidence consumed by the next process.
Native total process time is @WORLDNATIVE@ seconds versus @WORLDNONE@ without
memory, including common import/storage work and excluding the separately
recorded shared seed. Thus fewer search attempts do not establish a wall-time
advantage. The frozen dispatcher uses retrieved typed records directly: an
audit finds that the native compiler emits incorrect record identifiers in
all eleven compiled proposals, so compiler-mediated dispatch is not qualified
by this run. These results establish bounded storage/lookup consumption, not
learned world-model benefit, transfer, production integration or token savings.
A separately frozen compiler correction selects each record's own identity.
The ensuing consumer resolves compiler-selected records from the native store
before actual execution: the seed and eleven later cases pass, using 19 actions
and 25 fresh service processes. Changed source, state and environment still
invalidate prior observations. Independent checks preserve all original
comparison artifacts. This qualifies the corrected compiler-mediated path;
it does not change the original simple-retrieval/template parity or supply
learned transfer and token-savings evidence.

\paragraph{Native compositional reasoning.}
An existing original-source vertical slice was run with its compatible nested
datasets tree. A baseline component contract discharged, an injected fault was
refuted, and repair restored discharge. Localization produced an UNSAT core and
a cvc5 interpolant separately checked by Z3; the final artifact was verified by
semantic rescanning, composition redischarge and test replay. Selected and full
tests passed. Host elapsed time was @NATIVETIME@ seconds. This is one existing
constructed fixture with a prescribed fault and expected repair, not a held-out
synthesis experiment. Internal benchmark estimates are not counted as measured
token or compute savings. An earlier source profile failed to import the
required composition module and is preserved separately. Solver validation
does not imply kernel reconstruction or all-language correctness.

\paragraph{A real native proof relation.}
The copied native backend was built offline with locked dependencies because
the bundled binary did not implement the source's v3 circuit. Isolated
development keys support a four-leaf Event-DAG Merkle/count relation. Three
actual proofs for counts 1, 2 and 4 verify; eight witness, public-input,
proof and key mutations reject. Primary setup takes @PROOFSETUP@ seconds,
proof generation @PROVEMIN@--@PROVEMAX@ seconds, and verification
@VERIFYMIN@--@VERIFYMAX@ milliseconds; serialized proof JSON is 1,484 bytes.
The raw verifier accepts a different outer root that maps to the same field
element. The evaluation caller's exact-root/count and key/binary checks reject
that alternate statement before dispatch. This boundary is part of the result:
the native relation alone does not bind arbitrary outer metadata. Development
setup is not production trust admission, and a Merkle relation is not proof
that arbitrary tests executed. The v5 pytest-attestation circuit remains
unsupported in this backend.

\paragraph{The original bounded Horn profile.}
The source-built v2 backend also produces and verifies three honest implication
chains of lengths 1, 2 and 4. Setup takes @HORNSETUP@ seconds, proving
@HORNPROVEMIN@--@HORNPROVEMAX@ seconds, and verification
@HORNVERIFYMIN@--@HORNVERIFYMAX@ milliseconds; each proof JSON is 1,700 bytes.
The honest prover rejects the tested incomplete or inconsistent inputs.
When the scalar public inputs remain unchanged, the raw verifier accepts three
changed outer metadata fields; exact statement and source/key checks at the
evaluation caller reject them before dispatch. Honest examples and wrapper
checks do not establish that every satisfying circuit witness corresponds to
the advertised textual axioms. That stronger assurance remains unconfirmed.

\paragraph{First combined controller qualification.}
A new caller joins actual native context reads, source-bound semantic analysis,
symbolic routing, compiler-mediated world memory, isolated behavioral scoring
and a durable effect journal. On the four existing constructed routing tasks,
two supported initial repairs pass and two remain residual-pending with the
provider disabled. Authored follow-up events consume accepted source, recheck
a comment change and reject a stale local parent. Ordinary no-op detection
receives the same current behavioral checks as the memory path.
Three actual process interruptions exercise validated continuation, durable
receipt reconciliation and an executed effect whose completion remains unknown;
the unknown effect is held without redispatch. Across thirteen events there are
nine local acceptances, two pending residuals, one stale parent and one unknown
effect. These event counts are not thirteen independent repair tasks. Thirty
scorer attempts yield 29 durable terminal receipts. Local ledger CAS is not
native Kit publication; sealing, lifecycle reuse and certified procedures are
not yet combined here. With zero provider calls this qualification establishes
no integrated token-savings effect.

\paragraph{Remaining system questions.}
These increments establish local mechanisms and expose limitations. They leave
open matched context-substitution efficacy, persistent multi-task quality/cost,
procedure and world-memory utility on real tasks, production reuse, governed
publication, integrated native proof admission, and a held-out comparison with complete
startup, fallback, failed-attempt and recovery accounting.
Additional benchmark recruitment and environment qualification are reported in
Appendix~\ref{sec:incremental-recruitment}; they add no model-quality outcomes.
"""
    proof_begin = text.index(r"\paragraph{A real native proof relation.}")
    proof_end = text.index(r"\paragraph{First combined controller qualification.}")
    proof_details = text[proof_begin:proof_end]
    text = text[:proof_begin] + r"""\paragraph{Native proof production and statement binding.}
The source-built native backend produces three v3 Merkle/count proofs and three
honest v2 implication-chain proofs. For v3, primary setup takes @PROOFSETUP@
seconds, proving @PROVEMIN@--@PROVEMAX@ seconds and verification
@VERIFYMIN@--@VERIFYMAX@ milliseconds. Tested malformed witnesses, proofs and
keys reject. Both profiles require exact outer-statement checks at the caller:
the raw verifier can accept changed displayed metadata when its scalar public
inputs remain unchanged. These are measured bounded circuit relations, not
proofs that arbitrary tests executed or production trust admission. Stronger
v2 textual-binding assurance remains unconfirmed, and the v5 pytest-attestation
profile is unsupported. Appendix~\ref{sec:incremental-native-proof} retains the
separate profiles, mutation observations and v2 costs. A subsequent native
archive producer/consumer binds four actual accepted controller events to one
honest v3 proof, with seven mutation rejections. Proving takes 12.618 seconds;
original local receipts still supply execution evidence, and no token benefit
is established.

""" + text[proof_end:]
    context_begin = text.index(r"\paragraph{Repository context custody and preparation cost.}")
    context_end = text.index(r"\paragraph{Live context substitution.}")
    context_details = text[context_begin:context_end]
    text = text[:context_begin] + r"""\paragraph{Repository context and preparation.}
Native repository custody, current-source expansion and invalidation checks
pass on bounded XML/pyparsing scopes and on both full declared Requests
inventories (97 files each); these profiles permit zero raw-source omissions.
Five full pyparsing producer processes reach their 600-second deadline. A
subsequent immutable-state identity profile completes full preparation in
@FULLPYPREP@ seconds, followed by a passing independent native consumer; all
302 XML/pyparsing regular files are retained and 22 negative controls pass.
This establishes completion under the bound in one shared-host run. Preparation
is still substantial, and these profiles establish no compression or replicated
speedup. A subsequent full comment-change comparison exposes 1,568 differing
graph records. A conservative guard restores complete byte equality by
rescanning 134 of 154 Python paths, taking 614.522 seconds versus 437.699 for
cold preparation. Useful incremental economics remain open.
Appendix~\ref{sec:incremental-context-preparation} retains source scopes,
identity checks, earlier failures and actual costs.

""" + text[context_end:]
    controller_begin = text.index(r"\paragraph{First combined controller qualification.}")
    controller_end = text.index(r"\paragraph{Remaining system questions.}")
    controller_details = text[controller_begin:controller_end]
    text = text[:controller_begin] + r"""\paragraph{Combined controller and native publication.}
Constructed thirteen-event reasoning and eight-event publication profiles join
the actual native services and exercise real interruptions, native full/delta
publication and fresh accepted-source consumption. A separate Requests curator
fixture measures @REPOSEALWALL@ seconds of phases including full context
preparation. These zero-provider controls establish bounded continuation,
not token savings. Appendix~\ref{sec:incremental-controller-publication} retains
their complete costs, failures and unsigned integrity-only trust boundary.

\paragraph{First natural two-issue comparison.}
A new frozen Requests 5414-to-6028 development sequence executes all four
arms with equal public access and a four-call trajectory ceiling. Every arm
accepts the first issue; none completes both. First model requests are
byte-identical: B permits no source omissions, and C/D's native candidate
fails independent grading before the common residual. Partial D additionally
publishes and retrieves its accepted source. A/C/D then halt because appending
a merge-conflict module makes the request exceed its frozen bound; B's
different first repair merges cleanly but its three later model candidates
all fail. Table~\ref{tab:requests-cold} retains all seven calls and costs.
Server prompt caching is uncontrolled. These dependent observations from one
family establish no whole-system savings; a cheaper failed continuation is
not avoided successful work.

\begin{table}[htbp]
\centering
\caption{First natural Requests cold cohort. Each arm accepts 1/2 issue nodes
and completes 0/1 trajectories. Outer wall time includes nested services;
B's outer timing is unavailable after driver interruption.}
\label{tab:requests-cold}
\begin{tabular}{lrrr}
\toprule
Arm & Calls & Provider tokens & Outer seconds \\
\midrule
@REQUESTSROWS@
\bottomrule
\end{tabular}
\end{table}

""" + text[controller_end:]
    values = {
        "RAW": f"{counts['A_raw']['o200k_base']:,}", "ADD": f"{counts['B_additive']['o200k_base']:,}",
        "SUB": f"{counts['C_substitution']['o200k_base']:,}",
        "ADDINC": f"{-100 * ctx['reductions_relative_to_A']['B_additive']['o200k_base']:.2f}",
        "SUBINC": f"{-100 * ctx['reductions_relative_to_A']['C_substitution']['o200k_base']:.2f}",
        "ASUCCESS": a["successes"], "BSUCCESS": b["successes"], "ACALLS": a["provider_calls"],
        "BCALLS": b["provider_calls"], "ATOKENS": f"{a['total_tokens']:,}", "BTOKENS": f"{b['total_tokens']:,}",
        "REDUCTION": f"{reduction:.2f}", "COLD": f"{reuse['cold_wall_total_seconds']:.3f}",
        "WARM": f"{reuse['warm_wall_total_seconds']:.3f}", "NATIVETIME": f"{native['host_elapsed_seconds']:.3f}"}
    dtokens = dependency["message_content_token_totals"]
    values.update(PROOFSETUP=f"{native_proof['setup_primary_seconds']:.3f}",
                  PROVEMIN=f"{min(native_proof['prove_wall_seconds']):.3f}",
                  PROVEMAX=f"{max(native_proof['prove_wall_seconds']):.3f}",
                  VERIFYMIN=f"{1000*min(native_proof['verify_wall_seconds']):.3f}",
                  VERIFYMAX=f"{1000*max(native_proof['verify_wall_seconds']):.3f}")
    values.update(HORNSETUP=f"{horn['setup_seconds']:.3f}",
                  HORNPROVEMIN=f"{min(r['prove_seconds'] for r in horn['positive_rows']):.3f}",
                  HORNPROVEMAX=f"{max(r['prove_seconds'] for r in horn['positive_rows']):.3f}",
                  HORNVERIFYMIN=f"{1000*min(r['verify_seconds'] for r in horn['positive_rows']):.3f}",
                  HORNVERIFYMAX=f"{1000*max(r['verify_seconds'] for r in horn['positive_rows']):.3f}")
    values.update(WORLDNATIVE=f"{world['totals']['native_memory']['process_elapsed_seconds']:.3f}",
                  WORLDNONE=f"{world['totals']['no_memory']['process_elapsed_seconds']:.3f}")
    values.update(XMLBASE=f"{xml_comparison['baseline_preparation_wall_seconds_excluding_import']:.3f}",
                  XMLOPT=f"{xml_comparison['variant_preparation_wall_seconds_excluding_import']:.3f}")
    values.update(SEALSEQ=f"{1000*seal_timing['arms']['sequential']['median_prepare_seconds']:.2f}",
                  SEALPAR=f"{1000*seal_timing['arms']['parallel']['median_prepare_seconds']:.2f}",
                  RSSSEQ=f"{seal_timing['arms']['sequential']['max_sampled_aggregate_rss_bytes']/2**20:.2f}",
                  RSSPAR=f"{seal_timing['arms']['parallel']['max_sampled_aggregate_rss_bytes']/2**20:.2f}")
    lcraw = live_context["arms"]["raw"]["usage_totals"]
    lccompact = live_context["arms"]["compact"]["usage_totals"]
    values.update(LIVEINPUTRAW=f"{lcraw['input_tokens']:,}",
                  LIVEINPUTCOMPACT=f"{lccompact['input_tokens']:,}",
                  LIVEINPUTRED=f"{100 * live_context['reduction_vs_raw']['input_tokens']:.2f}",
                  LIVETOTALRAW=f"{lcraw['total_tokens']:,}",
                  LIVETOTALCOMPACT=f"{lccompact['total_tokens']:,}",
                  LIVETOTALRED=f"{100 * live_context['reduction_vs_raw']['total_tokens']:.2f}")
    values.update(FULLCAPSULES=f"{dtokens['C_full_native_substitution']['o200k_base']:,}",
                  DEPROW=f"{dtokens['A_raw']['o200k_base']:,}",
                  EQUATIONS=f"{dtokens['D_verified_equations']['o200k_base']:,}",
                  EQUATIONRED=f"{100 * dependency['reduction_vs_raw']['D_verified_equations']['o200k_base']:.2f}",
                  ASTTOKENS=f"{dtokens['E_plain_ast_source']['o200k_base']:,}",
                  PRIME=f"{reuse['prime_wall_seconds']:.3f}",
                  ISSUANCE=f"{reuse['issuance_wall_seconds']:.3f}")
    values["JOINEDWALL"] = f"{joined['controller_elapsed_seconds']:.3f}"
    values["REPOSEALWALL"] = f"{repository_seal_timing['measured_sequential_phase_interval_sum_seconds']:.3f}"
    values["REQUESTSROWS"] = "\n".join(
        f"{arm if arm != 'D' else 'D (partial)'} & {row['provider_posts']} & {row['usage']['total_tokens']:,} & "
        + ("unavailable" if row["invocation_seconds"] is None else f"{row['invocation_seconds']:.3f}")
        + r" \\" for arm, row in requests_arms.items())
    full_py = full_state_rows["ns-hist-02-pyparsing"]["producer"]
    values.update(FULLXMLPREP=f"{full_state_rows['ns-hist-01-xmltodict']['producer']['preparation_wall_seconds_excluding_import']:.3f}",
                  FULLPYPREP=f"{full_py['preparation_wall_seconds_excluding_import']:.3f}",
                  FULLPYCPU=f"{full_py['preparation_cpu_seconds_excluding_import']:.3f}",
                  FULLPYPROCESS=f"{load(context_prefix + 'results_v12_full_state_identity/ns-hist-02-pyparsing/produce_process.json')['wall_seconds']:.3f}",
                  FULLPYCONSUMER=f"{load(context_prefix + 'results_v12_full_state_identity/ns-hist-02-pyparsing/consume_process.json')['wall_seconds']:.3f}")
    for key, value in values.items():
        text = text.replace("@" + key + "@", str(value))
        proof_details = proof_details.replace("@" + key + "@", str(value))
        context_details = context_details.replace("@" + key + "@", str(value))
        controller_details = controller_details.replace("@" + key + "@", str(value))
    assert all("@" not in s for s in (text, proof_details, context_details, controller_details))
    generated = ROOT / "manuscript/fragments/incremental_results.tex"
    generated.write_text(text)
    shutil.copyfile(generated, snapshot / "incremental_results.tex")
    qualification_text = r"""\section{Additional benchmark qualification}
\label{sec:incremental-recruitment}
An independently pinned SWE-bench Verified metadata projection~\citep{swebench2024,swebenchverified2024} supplies 500
candidate repairs from twelve repository names. Ten of eleven prospectively
selected two-issue pairs have forward base-commit ancestry; one has reverse
ancestry in PR-date order. A separate current GitHub identity audit checks all
192 candidate/original repository pairs, finds no shared repository or declared
fork identities, and flags two shared-owner groups. This does not establish
historical code independence, portfolio separation or absence from model
training. A later audit reports test-specification problems in a selected hard
subset and evidence of solution exposure in tested frontier models~\citep{swebenchverifiedaudit2026}.
Its selected-subset rate is not a whole-dataset error estimate, and it does not
measure contamination in our provider profile. Public examples exposed during
this literature review are separately recorded before any prospective split.
No new confirmatory family or complete natural trajectory is enrolled.

Requests 6028 has a separately named ARM environment preserving its
public Python version and thirteen listed Python package versions. The unchanged
native SWE-bench 5.0.2 parser/grader observes all 187 designated checks in both
controls: unfixed source passes 185 and fails the two required failing checks;
reference source passes all 187 and is the only resolved control. Both collected
outputs also contain eight missing-fixture setup errors outside the designated
set. The original script lacks a test-exit marker, so a zero container exit
cannot establish acceptance. This is designated-check qualification, not an
error-free full-suite result or equivalence to the published x86 environment.
Protected reference/test content remains in curator custody; model-facing
selection reads public metadata only. Earlier import and decoding failures are
retained. Infrastructure qualification contributes no provider-token or repair
success observation for either treatment.

Requests 5414 subsequently qualifies in a new named ARM profile
using its public development dependencies and Docker's default bridge network.
Both controls complete all 131 designated checks: unfixed source passes 130
and the reference passes all 131. The full parsed outputs have 288 versus 289
passes, respectively, with one expected failure each and no setup errors.
The original offline port, a dependency-build failure and a plugin-startup
failure remain retained; the successful profile is a development correction.
This does not make the original failed port successful. A later candidate
grading service version fails its four-control qualification: three controls
behave as expected, but this node's reference is not accepted despite all
designated checks completing. Four existing public network-timeout checks
instead encounter a network-unreachable condition; the earlier standalone
run used the same image, package versions and evaluation bytes. The unique
cause and a reliable remedy are not established by this discrepancy.
Eight service rejection controls pass. This retained discrepancy illustrates
why standalone benchmark qualification alone does not qualify a new endpoint.
A subsequently frozen service version passes one attempt at each of its four
native controls and all ten rejection controls. It preserves exact objective,
profile, cumulative patch and resulting source-tree bindings. Public network
readiness probes bracket Requests 5414's evaluation, with no automatic retries;
an incomplete grade remains unavailable for repair decisions. All eight
qualification probes pass. The 94-check audit retains 1,175 artifacts; the four
control containers take 87.429894 seconds in total. This qualifies the named
service and its observed controls, without proving the unique cause or remedy
of the previous network failure or stability throughout future test runs.
Candidate and benchmark tests still share the original test process; adversarial
oracle integrity is not established. Requests 6028 retains its eight
outside-set fixture errors.

An additive public-only cumulative-source control changes two production files
and adds one Git-ignored Python file. The service inventories all 98 resulting
files, matches the independently expected tree, and returns the unchanged
unfixed grade of 185/187 in 6.048 seconds. This checks complete source-carry
transport into grading, not successful repair or an accepted multi-issue
trajectory. Earlier four-control cohorts remain unchanged.

A further pinned metadata-only projection yields 21,336 SWE-rebench
rows~\citep{swerebenchmetadata2026} from 3,468 repository names and 731
SWE-bench Pro rows~\citep{swebenchprometadata2026} from eleven names.
The 22,067-row sum is not deduplicated across datasets; protected issue,
reference and test fields are not decoded in this projection. A prospectively
seeded screen uses 2025 metadata dates, available image fields, distinct base
commits and exclusion of prior repository/owner names. It yields 53 candidate
pairs. All first sixteen pairs have actual forward Git ancestry, and 448
comparisons against the 28 prior current repository identities find no
repository, declared-fork or owner match. Each candidate has a distinct current
repository and owner identity. These checks do not prove historical code
independence, portfolio separation or training novelty. Image-field eligibility
is a convenience filter; all 32 selected image names specify x86\_64, whereas
the evaluation host is ARM. Source/environment/scorer qualification and a
prospective confirmatory split remain open; zero new families are enrolled.

The first frozen additional pair, Zarr 2996 and 3015, subsequently passes four
original native grading controls on explicitly ported ARM environments. Unfixed
source passes 16/22 and 157/158 designated checks, respectively; each reference
passes its complete set. Every control runs once, with zero retries or provider
calls. The native test-spec factory, test commands, parser and designated
criteria remain unchanged; the script port removes four Conda activation
commands. The environments preserve Python 3.11.11/3.11.14 and all 50/67
observed installed distribution versions, while architecture, platform binaries
and system-library builds differ. The local native fork reports version 4.0.3.
Its complete declared dependency installation failed because an ARM YSON
binary distribution was unavailable; a separately named local Docker backend
uses the available Python implementation, leaving cloud backends unsupported.

The four native grader container intervals total 10.647 seconds, excluding
environment acquisition, builds, Git preparation and audit. Earlier missing
build-helper, project-version and Git-image-reference failures remain retained.
The full public collection probe collected 3,045 tests for 2996 and exited zero;
3015 collected 3,123 but exited one during teardown with resource/unraisable
warnings. The targeted controls do not reproduce that teardown failure, and
their success does not erase it. As with Requests, the original script lacks
a separate test-exit marker, and native shared-process execution does not
establish adversarial oracle integrity. These results qualify the four original
controls; candidate endpoint, complete trajectory and token economics require
separate evaluation. No confirmatory family is enrolled by these controls.

A subsequent Zarr candidate endpoint qualifies all nineteen frozen controls,
with 190 audit checks: six actual native grading calls, ten rejections before
dispatch, two wrong-source containers stopped before hidden grading, and one
duplicate-ID rejection. Empty and cumulative-public candidates retain the
unfixed grades; reference production projections pass 22/22 and 158/158.
Each projection preserves the full original reference's production and
base-public bytes while omitting one ancillary added document, then reruns
the unchanged designated checks. This qualifies the projected candidates,
not transport of the full original patches. Non-Python edits remain outside
this endpoint's admitted scope.

Exact public base inventories contain 189/181 files, including the editable
installation's generated version module. Cumulative controls make three
production edits, including a Git-ignored addition, and retain all 190/182
resulting files. The initial endpoint attempt failed before hidden grading
because of raw mode differences and its rejection of the ancillary document;
a later preparation attempt caught a no-op Git apply in a nested checkout.
Both failures remain retained. The qualified revision preserves image-exact
modes and verifies actual edits in isolated Git repositories.
Six grader containers total 14.426 seconds within 30.363 seconds of outer
service calls, including the duplicate-ID control. Preparation, environment
acquisition and audit are separate. There are zero retries or provider calls.
Context, accepted-source trajectory carry, publication and model efficacy are
not enrolled by this endpoint qualification; adversarial oracle integrity
and non-Python transport remain unqualified.

For a later development experiment on the existing pyparsing snapshot, the
current public issue report supplies a concrete objective. Its nine examples
reproduce the reported recursive-whitespace defect on unchanged public source:
eight conform to the reported expectation and one fails. The report is frozen
for that new experiment; its exact bytes at the original base date remain
unverified. A reproduced public example is not complete hidden acceptance.
"""
    qualification_text += r"""
\section{Repository preparation and source custody}
\label{sec:incremental-context-preparation}
""" + context_details
    qualification_text += r"""
\section{Combined controller, publication and recovery}
\label{sec:incremental-controller-publication}
""" + controller_details + r"""
\paragraph{Subsequent native publication profile.}
The separately frozen eight-event sequence yields six acceptances, one stale
branch and one pending residual. A full checkpoint at generation 0 is followed
by a delta at generation 1. A real service exits with code 94 after native
seal persistence and before CAS. A fresh process loads the pending seal,
rechecks the entire parent chain and exact local evidence, replays visible
and audit behavior, then completes native CAS/WAL through an explicitly added
development adapter, reaching generation 2. Another fresh event consumes the
native stored accepted source and publishes generation 3. A branch based on
generation 0 reaches native publication and loses with a generation mismatch.

\begin{table}[htbp]
\centering
\caption{Actual work in the eight-event native publication qualification.
Event outcomes are dependent continuation observations.}
\begin{tabular}{lr}
\toprule
Operation & Count \\
\midrule
Controller invocations / terminal effects & 9 / 68 \\
Native context reads / source expansions & 4 / 8 \\
Input scans / accepted-candidate scans & 8 / 3 \\
Symbolic attempts / produced candidates & 4 / 3 \\
Native routing calls & 8 \\
World-memory service calls / compiled actions & 11 / 2 \\
Publication attempts / native reads / recovery & 7 / 4 / 1 \\
Controller / additional admission scorer processes & 18 / 24 \\
Provider requests / provider tokens & 0 / 0 \\
\bottomrule
\end{tabular}
\end{table}

Invocation wall time is 60.906438 seconds; the additional 24 behavioral
replays consume 13.759197 seconds within that total, not as a separate additive
cost. Context enrollment, inventory freezing, implementation and read-only
audit are outside this runtime denominator. Crash-time work is retained through
a durable receipt, and recovery does not double-count its aliased completion.
Both ordinary and memory paths run the same cheap current-source check and
accept no-op revisits without symbolic or model repair. The compiled memory
action dispatches an actual check; no reduction in checks is demonstrated.

The complete required leaf set is externally frozen: accepted source,
semantic preparation, effect inventory, visible behavior and audit behavior.
Every changed candidate receives a new native scan. All five leaves are
replaced per delta. Native integrity verification checks content and digests;
unsigned local receipts additionally depend on trusted controller/scorer
execution, a durable effect ledger and an evaluation-owned CID index. This
is neither a theorem about arbitrary Python nor production trust admission.
Stored parent chains are recursively checked and the requested source is
behaviorally replayed on read. Broader crash phases, concurrent publication,
provider effects, real repository edits and lifecycle reuse remain open.

The read-only audit passes 6,424 checks. The archive retains 504 source and
metadata files, including 483 native source files across the loaded closure
and preceding context enrollment. The first profile's omitted imported wrapper
and the first audit's pointer-envelope parser failure are retained. Correcting
the audit did not rerun behavioral outcomes; the archived previous controller
still passes its original 9,188 checks.
"""
    repository_seal_details = r"""
\paragraph{Full-repository service fixture and measured cost.}
A separate curator-held Requests 6028 fixture begins with its reference
candidate and then adds a neutral comment to the same accepted production
source. Both states contain all 97 source files. It executes two full native
context preparations, four world-memory service calls and six original native
grader invocations: two initial checks and four fresh publication, interruption,
recovery and read replays. All six complete the 187 designated checks.
Reference and hidden test payloads remain in curator custody. This fixture
does not execute the Requests 5414-to-6028 upstream transition or any model
repair, and it does not establish adversarial oracle integrity.

The first full checkpoint reaches generation 0. The second process constructs
a delta and actually exits with code 94 after seal persistence but before CAS.
A fresh process recovers generation 1; another fresh process reads and restores
the exact second accepted source. Wrong-tree, wrong-receipt, source-drift and
incomplete-effect controls all reject before grader replay. All four required
leaves---accepted source, semantic preparation, observed non-sealing effects
and native behavior---are replaced on transition. The effect leaf excludes
all sealing operations, including prior reads; the outer workflow ledger must
still count their actual work. Parent/source admission and fresh grading are
additional checks. Unsigned local receipts and native integrity mode establish
neither a theorem of execution nor verification reuse.

\begin{table}[htbp]
\centering
\caption{Measured disjoint sequential intervals for the Requests 6028 curator
fixture. Grader processes are nested in these phases and are not added again.}
\begin{tabular}{lrr}
\toprule
Phase & Count & Wall seconds \\
\midrule
Full native context preparation & 2 & @RSCTX@ \\
Initial accepted-candidate checks & 2 & @RSCHECK@ \\
World-memory service calls & 4 & @RSMEM@ \\
Publication/recovery/read and rejection controls & 8 & @RSNATIVE@ \\
\midrule
Sum of measured intervals & & @RSTOTAL@ \\
\bottomrule
\end{tabular}
\end{table}

The six grader containers consume @RSGRADER@ seconds within the measured
intervals. Their four replay service wrappers are also nested, not independent
extra costs. The frozen-start-to-result artifact span is 377.640 seconds;
this is not a separately instrumented whole-process timer and excludes earlier
imports and profile creation. Later code archival and read-only audit take
0.275 seconds together, outside the fixture intervals. There is one
shared-host observation, no parallel comparison and no provider calls.
The 275-check audit retains 33 public code snapshots and hashes 1,136
private artifacts. This closes the stated service controls while leaving
multi-issue model efficacy, token savings and broader crash coverage open.
"""
    repository_seal_values = {
        "RSCTX": repository_seal_timing["effect_phases"]["accepted_context_prepare"]["seconds"],
        "RSCHECK": repository_seal_timing["effect_phases"]["accepted_check"]["seconds"],
        "RSMEM": sum(repository_seal_timing["effect_phases"][k]["seconds"] for k in ("world_propose", "world_record")),
        "RSNATIVE": repository_seal_timing["native_service_process_seconds_sum"],
        "RSTOTAL": repository_seal_timing["measured_sequential_phase_interval_sum_seconds"],
        "RSGRADER": repository_seal_timing["nested_native_grading"]["container_seconds_sum"],
    }
    for key, value in repository_seal_values.items():
        repository_seal_details = repository_seal_details.replace("@" + key + "@", f"{value:.3f}")
    assert "@" not in repository_seal_details
    qualification_text += repository_seal_details
    qualification_text += r"""
\paragraph{Natural Requests sequence: intervention and failure paths.}
The first live repository cohort contains one development family, two genuine
public issue nodes and four arms, executed in frozen D/C/A/B order with
independent local cold stores. Each trajectory has at most four provider
requests, with at most two at its first issue; unused slots carry forward.
All planning, proposal, expansion and recovery purposes share that ceiling.
The common Grok 4.6 low-reasoning profile has a 2,048-output-token limit and
a 65,536-byte request limit. Source retrieval selects whole production modules
with three-file/48,000-raw-byte limits, and exact requested expansions replace
the earlier selection. Accepted first-node source is committed on its exact
public base and carried through a real three-way merge with the next base.
No reference patch enters the model or its public history.

A uses ordinary lexical retrieval and the common current-source check. B
actually prepares and reads native context, but zero omissions qualify, so its
model context falls back to the same raw source. C additionally runs native
analysis, bounded synthesis and routing; its native candidate fails before
the model repairs the first issue. D adds actual world-memory services,
accepted-source context preparation, native publication and stored-source
read. It remains partial: lifecycle reuse, certified procedures, learned
world utility and integrated theorem proof are absent. Native permitted model
routes share the same fixed provider profile, so model-tier selection cannot
explain cost differences. Each arm retains its own histories and state; the
effect journal provides durable identities for every arm.

All four initial requests have identical canonical bytes and 13,693 provider
input tokens. Each returns one independently passing first-node repair. A and
B receive 13,568 cached input tokens each, versus 512 each for C/D; local cold
state therefore does not imply equal remote cache state. Returned reasoning
and output lengths vary. Small first-node total-token differences cannot be
attributed to source compression or a witnessed avoided model call.

A/C/D's accepted edits each conflict in the next public source merge.
Their retriever appends the required conflict module to its ordinary selection,
yielding four modules, 80,552 raw source bytes and a 91,202-byte request. The
frozen 65,536-byte gate halts before dispatch. B's different initial edit
merges without a conflict and its next request fits at 53,319 bytes. Its
three subsequent candidate grades are 184/187, 185/187 and 185/187, all
unsuccessful; the original current source passed 185/187. The second node
thus fails in every arm, through different observed paths. Source-bound
halts are retained failures, not successful symbolic closures.

The complete fixed-cohort provider totals are 14,428 (A), 65,695 (B),
14,589 (C) and 14,269 (D), summing to 108,981 across seven actual posts.
Each arm has one accepted node, so tokens per accepted node equal those
fixed-cohort totals; tokens per completed trajectory are undefined. All
unsuccessful model attempts remain charged. The first-horizon totals are
14,428/14,192/14,589/14,269 in A/B/C/D order. These are observed cumulative
costs, not counterfactual quality-versus-budget curves or independent repeats.
Charges, cached input, visible output and reasoning components remain separate
in the retained provider receipts; account settlement is not inferred.

The original driver terminates with exit 143 while B's first controller is
still running. That same worker finishes and commits its accepted event.
A separately frozen reconciliation checks the exact terminal output, journal,
source/profile identities and absence of pending effects, then executes only
the original remaining B6028 event. B5414 is never restarted. Its outer
invocation time, waited CPU and exit status remain unavailable; the controller's
own 209.770-second timer survives. B's two controller intervals sum to
408.510 seconds, which is a different timing scope from other arms' enclosing
invocation intervals. Docker workload CPU is unavailable throughout. Preparation,
grading, memory and publication/read phases are nested within runtime and must
not be added twice. Development qualification and source/environment acquisition
remain separately scoped overhead.

The separate ledger audit passes 1,769 source, journal, request, attribution and
budget checks. It joins all seven model receipts to their actual effects and
dispatch intents, with no unknown provider effects. Sixteen unique native
grader receipts include the two additional D publication/read replays; repeated
appearances of saved completions are not new calls. Model and effect accounting
are complete for this cohort, while outer runtime accounting remains incomplete
because B5414's enclosing timer is missing. The source archive contains 504
files. Preparation records include observed native imports; the source-expansion
process lacks a separate actual import receipt, which limits the demonstrated
execution closure. The quantitative result is not a production trust admission.

One family with implementation failures and uncontrolled server caching cannot
identify a general mechanism effect. Equal accepted-node counts also conceal
the different second-node opportunities. No arm completes the intended natural
trajectory, and the broader cache, warm-horizon, ablation and independent-family
program remains required. Subsequent transport corrections receive a new profile;
these outcomes and request bounds remain unchanged.
"""
    qualification_text += r"""
\section{Native proof profiles and exact statement checks}
\label{sec:incremental-native-proof}
""" + proof_details
    qualification_text += r"""
\paragraph{Actual accepted-history archive integration.}
A separately frozen producer/consumer profile follows the constructed
controller's native generation-3 pointer through four accepted seals, each
with five required receipt units. It excludes the stale unaccepted branch and
the separate ordinary trajectory. Producer and fresh consumer use native Kit
verified reads on exact archive clones, reconstruct the original local effect
receipts and check the complete source, parent and leaf bindings. The original
archive and controller ledger remain unchanged. No behavioral checker is rerun;
the original local execution remains the authority for its recorded observations.

Each canonical event commits its seal/parent, source and original binding,
complete receipt-CID map and verified pack digest. The already qualified
standard v3 backend proves their four-leaf archive relation. The consumer
checks the externally expected full root/count and exact binary/key, in addition
to the accepted pointer and chain. The raw scalar-root limitation still applies;
the proof does not establish that arbitrary code or tests executed correctly.
The stopped custom-v2 investigation is not used.

One honest proof and one runtime pairing verification complete. Producer and
fresh-consumer read processes take 0.325531 and 0.342170 seconds, proving
12.617511 seconds and verification 0.006725 seconds. The measured driver
totals 14.749495 seconds, including source/key/archive hashing, clones and
negative controls. These phases are nested. Earlier backend compilation, the
original 7.810198-second development key setup and historical controller
execution are separately scoped costs. A later audit adds a 0.006085-second
native verification. This is one shared-host observation with existing keys,
not a replicated speed comparison or evidence that proving beats direct hashing.

All seven frozen controls reject: missing/corrupt receipt bytes, incomplete
leaf inventory, stale parent, reordered events, changed event source commitment
and changed full root. Four exercise the native reader; the last three reject
at exact statement binding before pairing. The proof JSON is 1,484 bytes;
the original 69-file store contains 2,010,722 bytes, including additional
unselected records. A small proof does not replace the original source/receipt
custody that the consumer still reads. The separate audit passes 218 checks,
recomputes all event digests and the full Merkle root, and archives 34 observed
source files. The audit shares the cryptographic backend. This establishes
no new behavioral check, model call, execution reuse, token saving or
production admission.
"""
    qualification = ROOT / "manuscript/appendix/incremental_qualification_details.tex"
    qualification.write_text(qualification_text)
    shutil.copyfile(qualification, snapshot / "incremental_qualification_details.tex")
    shutil.copyfile(Path(__file__), snapshot / "update_manuscript.py")
    sources.extend([str(generated.relative_to(ROOT)), str(qualification.relative_to(ROOT)), "update_manuscript.py"])
    manifest = {}
    for source in sorted(set(sources)):
        p = ROOT / source
        manifest[source] = hashlib.sha256(p.read_bytes()).hexdigest()
        retained = snapshot / "inputs" / source
        retained.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(p, retained)
    (snapshot / "evidence_manifest.json").write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n")
    (snapshot / "checks.json").write_text(json.dumps({"routing_totals_recomputed": True,
        "all_six_live_usage_receipts_checked": True, "paired_residual_requests_identical": True,
        "all_fourteen_saved_outcomes_preserved_on_rescore": True,
        "native_horn_honest_only_boundary_checked": True,
        "historical_cells_relabelled": False, "whole_goal_complete": False}, indent=2) + "\n")
    print(f"Generated working manuscript increment {args.increment}; full research objective remains open.")


if __name__ == "__main__":
    main()
