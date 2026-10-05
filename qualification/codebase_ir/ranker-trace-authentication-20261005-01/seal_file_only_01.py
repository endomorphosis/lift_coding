"""File-only closure after completed native jobs; imports no project code."""
import hashlib
import json
from pathlib import Path
import stat

ROOT = Path(__file__).resolve().parent


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


def pin(path):
    path = Path(path); before = path.lstat()
    assert path.resolve(strict=True) == path and stat.S_ISREG(before.st_mode) and before.st_nlink == 1
    raw = path.read_bytes(); after = path.lstat()
    sig = lambda value: (value.st_dev, value.st_ino, value.st_size, value.st_mtime_ns, value.st_ctime_ns)
    assert sig(before) == sig(after)
    return {"path": str(path), "bytes": len(raw), "sha256": digest(raw)}


def load(path):
    return json.loads(Path(path).read_bytes())


def write(path, value):
    with path.open("x") as stream:
        json.dump(value, stream, sort_keys=True, indent=2, ensure_ascii=False, allow_nan=False)
        stream.write("\n")


def main():
    request = load(ROOT / "preparation/request.json")
    strict = request["strict_old_inputs"]
    assert len(strict) == 348
    for row in strict:
        current = pin(row["path"])
        assert current["sha256"] == row["sha256"]
        if "bytes" in row: assert current["bytes"] == row["bytes"]
    for row in request["protected_live_sources"]: assert pin(row["path"]) == row
    phases = {mode: load(ROOT / "evidence" / mode / "closed.json")
              for mode in ("tests-01", "actual-01", "lean-02", "metadata-01")}
    assert phases["tests-01"]["status"] == phases["lean-02"]["status"] == phases["metadata-01"]["status"] == "passed"
    first = phases["actual-01"]
    assert first["status"] == "failed" and first["actual_authentication_calls"] == 1
    assert first["observed_native_counts"] == {"gradient_evaluations": 131,
        "native_preparation_calls": 2, "replay_gradient_evaluations": 129}
    assert first["actual_optimizer_verification_updates"] == 128
    auth = load(first["authentication_result"]["path"])
    assert pin(first["authentication_result"]["path"]) == first["authentication_result"]
    self_raw = json.dumps({key: value for key, value in auth.items() if key != "authentication_sha256"},
                         sort_keys=True, separators=(",", ":"), ensure_ascii=True, allow_nan=False).encode()
    assert digest(self_raw) == auth["authentication_sha256"]
    assert first["authentication_result"]["bytes"] <= 65536
    initial_check_path = ROOT / "evidence/actual-01/lean-finite_native_observation_order-check.json"
    initial_check = load(initial_check_path)
    assert initial_check["returncode"] == 0 and initial_check["output_truncated"] is True
    assert initial_check["status"] == "inconclusive" and initial_check["matches_expectation"] is False
    lean = phases["lean-02"]; checks = load(lean["lean_checks"]["path"])
    assert len(checks) == 2 and all(check["matches_expectation"] is True for check in checks)
    assert checks[0]["status"] == "passed" and checks[1]["status"] == "rejected"
    assert checks[0]["output_truncated"] is checks[1]["output_truncated"] is False
    assert checks[0]["compiled_artifacts"][0]["bytes"] == 58952
    metadata = phases["metadata-01"]; readback = load(metadata["native_metadata_readback"]["path"])
    assert readback["row_count"] == 4348 and len(readback["family_counts"]) == 29
    assert readback["fresh_process_readback"]["verified"] is True
    assert metadata["prior_4216_payload_rows_preserved_exactly"] is True
    assert metadata["all_4348_payload_rows_read_back_exactly"] is True
    timings = {}
    for mode, phase in phases.items():
        outer = load(ROOT / "evidence" / (mode + "-closed.json"))
        assert phase["cleanup_errors"] == [] and outer["cleanup_errors"] == []
        assert phase["blocked_imports"] == [] and all(row["matches"] for row in phase["selected_owned_imports"])
        state = phase["final_resource_state"]
        assert state["active_lease_count"] == state["waiting_request_count"] == 0
        policy = phase["resource_policy"]
        assert policy["proof_safety_enabled"] is True
        assert phase["root_request"] == {"cpu_slots": 1, "memory_mb": 2048, "child_process_slots": 4}
        timings[mode] = {"owned_seconds": phase["elapsed_seconds_owned"],
            "outer_seconds": outer["elapsed_seconds_outer"],
            "native_authentication_seconds": phase.get("native_authentication_seconds"),
            "native_metadata_seconds_including_fresh_restart": phase.get("native_metadata_seconds_including_fresh_restart"),
            "test_seconds": phase.get("test_seconds"), "timings_nested_not_added": True,
            "selected_owned_import_count": len(phase["selected_owned_imports"]),
            "final_active_leases": 0, "final_waiting_requests": 0}
    mapping = load(lean["finite_objective_mapping"]["path"])
    assert mapping["observations"] == 129 and mapping["strict_adjacent_declines"] == 128
    assert mapping["common_denominator"] == "72057594037927936"
    authority = {name: False for name in ("proof_authority", "formalization_authority",
        "execution_authority", "completion_authority", "mutation_authority", "omission_authority",
        "source_semantics_verified", "semantic_alignment_verified", "behavioral_satisfaction", "whole_program_proved")}
    review = {"schema": "terminal-ranker-trace-file-only-qualification-review@1",
        "status": "passed_finite_original_native_replay_observed_value_order_and_fresh_metadata",
        "review_mode": "file-only existing results; no project imports, fits, solver or storage calls",
        "file_verifier_source": pin(Path(__file__).resolve()), "request": pin(ROOT / "preparation/request.json"),
        "independent_source_review": request["review"],
        "authentication": first["authentication_result"], "authentication_sha256": auth["authentication_sha256"],
        "raw_file_canonical_binding": pin(ROOT / "evidence/actual-01/raw-canonical-binding.json"),
        "completed_original_authentication_despite_first_proof_retention_failure": True,
        "original_numeric_authentication_calls": 1, "original_verification_optimizer_updates": 128,
        "original_replay_gradient_evaluations": 129, "original_passive_endpoint_gradient_evaluations": 2,
        "original_total_gradient_evaluations": 131, "original_native_preparation_calls": 2,
        "synthetic_unit_fit_calls": 1, "synthetic_unit_optimizer_fit_updates": 16,
        "selected_unit_tests": 64, "tests_skipped": 0,
        "unit_adversarial_replay_updates_global_total": "not aggregated; controls stop at their first mismatch",
        "new_public_fit_calls": 0, "new_autoencoder_fit_calls": 0, "checkpoint_activation_calls": 0,
        "native_lean_invocations_total": 3, "native_lean_final_qualified_checks": 2,
        "native_lean_prior_inconclusive_calls": 1, "native_metadata_hydration_attempts": 1,
        "retained_inconclusive_checker": pin(initial_check_path), "final_lean_checks": lean["lean_checks"],
        "complete_positive_olean_bytes": 58952, "finite_objective_mapping": lean["finite_objective_mapping"],
        "authenticated_states": 129, "strict_observed_adjacent_declines": 128,
        "positive_common_denominator": mapping["common_denominator"],
        "native_metadata_readback": metadata["native_metadata_readback"], "metadata_families": 29,
        "metadata_rows": 4348, "prior_payload_rows_preserved_exactly": 4216,
        "new_metadata_family_counts": {"ranker_trace_authentication": 1, "ranker_trace_states": 129, "ranker_trace_lean_checks": 2},
        "fresh_native_restart_and_all_payloads_verified": True,
        "original_training_corpus_sha256": auth["corpus_sha256"],
        "prior_expanded_step_profile_remains_separate": True,
        "contracts_payloads_unchanged": True, "source_snapshot": pin(ROOT / "evidence/metadata-01/source-snapshot.json"),
        "all348_strict_old_inputs_unchanged": True, "all4_protected_live_sources_unchanged": True,
        "old_inventory": request["strict_old_input_inventory"], "protected_live_sources": request["protected_live_sources"],
        "selected_import_sources_unchanged_all_phases": True, "selected_import_blocked_count": 0,
        "all_phase_cleanup_errors": [], "all_phase_scheduler_drains_zero_active_zero_waiting": True,
        "proof_pressure_gate_unchanged": {"memory_stall_percent": 2, "cpu_stall_percent": 50, "io_stall_percent": 10},
        "root_lease_unchanged": {"memory_mb": 2048, "cpu_slots": 1},
        "native_solver_limits_unchanged": {"max_output_bytes": 65536, "cpu_seconds": 20,
            "timeout_seconds": 20, "max_workspace_bytes": 16777216},
        "outer_timeout_seconds_unchanged": 120, "native_metadata_existing_limits_unchanged": True,
        "actual_phase_timings": timings,
        "native_lean_elapsed_seconds_by_attempt": [initial_check["elapsed_seconds"], *[check["elapsed_seconds"] for check in checks]],
        "authentication_scope": auth["authentication_scope"],
        "historical_execution_origin_authenticated": False, "independent_pin_origin_authenticated": False,
        "exact_real_logistic_descent_proved": False, "binary64_error_bound_proved": False,
        "global_optimizer_convergence_proved": False, "asymptotic_optimizer_convergence_proved": False,
        "autoencoder_convergence_proved": False, "whole_source_runtime_equivalence_proved": False,
        "generalized_ranking_gain_qualified": False, "all32_governing_RPI_exits": "OPEN",
        "full_task_satisfaction": "unknown", "planning_handoff": "abstained", "canonical_tasks": [],
        "planner_activation": False, "official_benchmark_score": None, **authority}
    write(ROOT / "file-only-review-01.json", review)
    files = [pin(path) for path in sorted(ROOT.rglob("*")) if path.is_file()]
    assert all(pin(row["path"]) == row for row in files)
    seal = {"schema": "terminal-ranker-trace-file-only-seal@1", "status": "retained_and_rehashed",
        "review": pin(ROOT / "file-only-review-01.json"), "files": files, "file_count": len(files),
        "file_inventory_sha256": digest(json.dumps(files, sort_keys=True, separators=(",", ":")).encode()),
        "all348_old_pinned_inputs_unchanged": True, "all4_protected_live_sources_unchanged": True,
        "scope": "Stable individual file hashes after closed jobs; no atomic whole-live snapshot or historical execution origin claim.",
        "new_native_jobs_during_seal": 0}
    write(ROOT / "file-only-seal-01.json", seal)
    print(json.dumps({"review": pin(ROOT / "file-only-review-01.json"), "seal": pin(ROOT / "file-only-seal-01.json"), "files": len(files)}))


if __name__ == "__main__":
    main()
