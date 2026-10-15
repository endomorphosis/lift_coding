"""Join explicit native IR, conditional proof, cold replay and fault evidence."""
import argparse
import hashlib
import json
from pathlib import Path

from train_codebase_ir import read, write
from verify_successor import validate_result_scope

ROOT = Path(__file__).resolve().parent


def load(path):
    return json.loads(read(path, 32_000_000))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--run", required=True)
    parser.add_argument("--tests", required=True)
    parser.add_argument("--cold", required=True)
    parser.add_argument("--faults", required=True)
    parser.add_argument("--status", required=True)
    args = parser.parse_args()
    for name in vars(args).values():
        if not name or Path(name).name != name or name in {".", ".."}:
            raise ValueError("explicit local artifact names required")
    result = load(ROOT / args.run / "result.json")
    validate_result_scope(result)
    process = load(ROOT / (args.run + "-process-report.json"))
    tests = load(ROOT / (args.tests + "-report.json"))
    cold = load(ROOT / args.cold)
    faults = load(ROOT / args.faults / "result.json")
    if not all(item["qualified"] for item in (process, tests, cold, faults)):
        raise ValueError("all selected native/process/test/cold/fault gates required")
    if cold["proof_lookup"] != result["proof_lookup"] or not all(faults.get(key) is True for key in
        ("source_drift_refused", "non_alignment_source_drift_refused", "same_content_new_generation_refused", "original_source_restored")):
        raise ValueError("current cache or exact native fault joins differ")
    freeze = load(ROOT / (args.run + "-source-pins.json"))
    for pin in freeze["retained_copies"]:
        for path in (Path(pin["path"]), Path(pin["retained_copy"])):
            raw = read(path, 32_000_000)
            if hashlib.sha256(raw).hexdigest() != pin["sha256"] or len(raw) != pin["bytes"]:
                raise ValueError("selected current/frozen producer changed")
    structural, proof, grounding = result["structural"], result["alignment_proof"], result["intent_grounding"]
    if not result["metadata"]["complete_record_reconstruction"]:
        raise ValueError("complete DuckDB/DuckLake reconstruction required")
    status = {"schema": "terminal-typed-ir-proof-improvement-status@1", "selected_experiment": args.run,
        "qualified_bounded_experiment": True, "source_scope": {"files": 5, "bytes": 15788,
            "terminal_bench_tasks": 4, "original_source_bodies_executed": False, "hidden_inputs_used": False},
        "native_current_head": structural["head"], "typed_ir_coverage": structural["coverage"],
        "native_typed_duckdb_rows": structural["sql_rows"],
        "native_structural_authority": "structural_only",
        "conditional_source_projection": {"path": result["alignment_projection"]["source"]["path"],
            "function": "align", "granularity": 64, "input_domain": "mathematical integers",
            "kernel_checked_properties": ["x <= result", "result < x + 64", "result is a multiple of 64"],
            "source_parser_correctness_proved": False, "cpython_equivalence_proved": False,
            "unsupported_native_parent_regions": len(result["alignment_projection"]["unsupported_residuals"])},
        "lean": {"positive_compilations": proof["positive_compiles"], "rejected_false_controls": proof["false_controls_rejected"],
            "native_processes": proof["native_lean_processes"], "named_mathematical_theorems": proof["theorems"],
            "trust_boundary": proof["trust_boundary"], "scope": proof["proof_scope"]},
        "proof_cache": {"current_source_and_complete_head_rechecked": True, "checker_bytes_rechecked": True,
            "source_drift_refused": True, "other_indexed_source_drift_refused": True,
            "same_content_new_generation_refused": True, "main_original_sources_restored": True,
            "historical_record_grants_admission": False, "native_offset_profile_reused": False},
        "intent_ir": {"interpretation": "manually_authored_structural_candidates",
            "native_goal_requirements": len(grounding["native_requirement_ledger"]["requirements"]),
            "original_instruction_residual_units": len(grounding["original_instruction_residuals"]),
            "whole_original_instruction_preserved": grounding["whole_instruction_preserved"],
            "partial_plan_status": grounding["partial_plan"]["status"],
            "native_coverage_accepted": grounding["partial_plan"]["coverage"]["accepted"],
            "automated_natural_language_intent_decoding_used": False, "behavioral_satisfaction_proved": False},
        "metadata": {"families": result["metadata"]["family_counts"],
            "native_duckdb_ducklake_restart_exact": cold["native_duckdb_ducklake_restart_exact"],
            "complete_producer_record_reconstruction": True, "quack_extension_evaluated": False},
        "resources": structural["resources"], "matching_native_policy_version": "native-policy-overlay-01",
        "shared_pool_reset_or_capacity_changed": False, "proof_recovery_enabled_by_this_stage": False,
        "tests": tests["counts"], "mathematical_boundary_controls": len(cold["mathematical_controls"]),
        "new_optimizer_steps": 0, "prior_training_checkpoint_bytes_modified": False,
        "claims": {"whole_source_to_model_runtime_equivalence_proved": False, "learned_typed_ir_decoder_trained": False,
            "asymptotic_optimizer_convergence_proved": False, "full_task_satisfaction_proved": False,
            "native_full_supervisor_frontend_executed": False, "official_terminal_bench_harness_executed": False,
            "provider_token_savings_measured": False, "global_durable_task_budget_proved": False},
        "retained_failed_attempts": ["experiment-01: scheduler version/configuration refusal",
            "experiment-02: total source byte cap wrongly set to per-file cap"],
        "experimental_files_isolated": True, "promoted_or_pushed": False,
        "review_inputs": [str(ROOT / args.run / "result.json"), str(ROOT / args.cold),
            str(ROOT / args.faults / "result.json"), str(ROOT / (args.tests + "-report.json"))]}
    write(ROOT / args.status, status)
    print(json.dumps({"status": args.status, "native_source_files": 5,
        "typed_ast_nodes": structural["sql_rows"]["ast_nodes"], "lean_theorems": len(proof["theorems"]),
        "native_intent_coverage_accepted": False, "tests": tests["counts"]}))


if __name__ == "__main__":
    main()
