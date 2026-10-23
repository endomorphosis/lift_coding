"""Join the explicit successful experiment, cold replay and selected tests."""
import argparse
import hashlib
import json
from pathlib import Path

import duckdb

from train_codebase_ir import RUNS, read, wire, write

ROOT = Path(__file__).resolve().parent


def load(path):
    return json.loads(read(path, 32_000_000))


def require(condition, message):
    if not condition:
        raise ValueError(message)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--run", required=True)
    parser.add_argument("--tests", required=True)
    parser.add_argument("--cold-report", required=True)
    parser.add_argument("--status", required=True)
    args = parser.parse_args()
    require(all(Path(name).name == name and name not in {".", ".."} for name in
        (args.run, args.tests, args.cold_report, args.status)), "explicit local artifact names required")
    experiment = ROOT / args.run
    result = load(experiment / "result.json")
    process = load(ROOT / (args.run + "-process-report.json"))
    test = load(ROOT / (args.tests + "-report.json"))
    cold = load(ROOT / args.cold_report)
    freeze = load(ROOT / (args.run + "-source-pins.json"))
    require(result["completed"] and process["qualified_process_completion"]
        and test["qualified"] and cold["qualified"], "all selected qualification boundaries required")
    require(result["optimizer_steps"] == sum(row[2] for row in RUNS) == 136,
        "predeclared selected training step budget differs")
    require(cold["optimizer_steps_in_this_verifier"] == 0 and cold["panel_count"] == 20
        and cold["review"] == result["training_review"], "cold replay joins differ")
    for pin in freeze["retained_producer_copies"]:
        for path in (Path(pin["path"]), Path(pin["retained_copy"])):
            body = read(path, 32_000_000)
            require(len(body) == pin["bytes"] and hashlib.sha256(body).hexdigest() == pin["sha256"],
                "selected current/retained producer differs")
    native = result["metadata"]["native_metadata"]
    require(native["fresh_process_readback"]["verified"] and result["metadata"]["complete_record_reconstruction"],
        "complete native metadata restart required")
    queries = {}
    with duckdb.connect(str(experiment / "metadata" / "metadata.duckdb"), read_only=True,
            config={"autoinstall_known_extensions": "false", "autoload_known_extensions": "false",
                    "enable_external_access": "false", "threads": "1"}) as connection:
        queries["families"] = connection.execute("SELECT family, count(*) FROM metadata_rows GROUP BY family ORDER BY family").fetchall()
        queries["vector_dimensions"] = connection.execute("SELECT json_extract_string(payload_json,'$.task_id'), "
            "json_array_length(payload_json,'$.record.latent'), count(*) FROM family_vectors GROUP BY 1,2 ORDER BY 1,2").fetchall()
        queries["feature_vector_joins"] = connection.execute("SELECT count(*) FROM family_features f "
            "JOIN family_vectors v ON json_extract_string(f.payload_json,'$.record.row_id')="
            "json_extract_string(v.payload_json,'$.source_row_id') AND "
            "json_extract_string(f.payload_json,'$.task_id')=json_extract_string(v.payload_json,'$.task_id')").fetchone()[0]
        queries["unresolved_contracts"] = connection.execute("SELECT count(*) FROM family_contracts WHERE "
            "json_extract_string(payload_json,'$.status')='unresolved_task_requirement'").fetchone()[0]
    require(queries["feature_vector_joins"] == 28 and queries["unresolved_contracts"] == 4
        and all(row[1] == 8 for row in queries["vector_dimensions"]), "native metadata feature/contract joins differ")
    write(ROOT / (Path(args.status).stem + "-native-query-readback.json"), queries)
    primary = next(row for row in result["training_review"]["runs"] if row["run_id"] == "primary-1729")
    panel = primary["splits"]["evaluation"]["function_weighted_mean_reconstruction_error"]
    observed_attempts = []
    for name in ("experiment-01", "experiment-02", "experiment-03", "experiment-04", args.run):
        if name in {item["name"] for item in observed_attempts}:
            continue
        attempt = ROOT / name
        observations = [load(attempt / (run_id + "-report.json")) for run_id, _, _ in RUNS]
        observed_attempts.append({"name": name, "optimizer_steps": sum(len(row["observed_steps"]) for row in observations),
            "selected": name == args.run, "qualified_full_process": load(ROOT / (name + "-process-report.json"))["qualified_process_completion"],
            "historical_producer_copies_retained": (ROOT / (name + "-frozen-sources")).is_dir()})
    status = {"schema": "terminal-codebase-ir-training-improvement-status@1", "selected_experiment": args.run,
        "selected_process_qualified": True, "source_scope": {"terminal_bench_commit": "2fd12b88aafdd04a52c298e3940bcb189f9766d6",
            "tasks": 4, "public_python_files": 5, "public_python_bytes": 15788,
            "training_tasks": 2, "training_functions": 8, "validation_tasks": 1, "validation_functions": 1,
            "evaluation_tasks": 1, "evaluation_functions": 19, "hidden_verifier_inputs_used": False,
            "historically_unseen_holdout_established": False, "source_body_execution": False,
            "unsupported_source_frontier": "modernize-scientific-stack Python 2 syntax, not trained"},
        "representation": "44 AST count features trained into 8-dimensional advisory latent vectors",
        "native_optimizer": "Adam lr=0.02 with pinned datasets modal reconstruction kernel",
        "selected_optimizer_steps": 136, "all_attempt_optimizer_steps": sum(item["optimizer_steps"] for item in observed_attempts),
        "attempts": observed_attempts, "exact_same_seed_checkpoint_and_task_numeric_replay": True,
        "cold_checkpoint_replay": {"panels": 20, "models": 5, "separate_forward_implementation": True,
            "independent_numerical_backend": False, "authenticated_step_observer": False},
        "evaluation_mse": panel, "evaluation_mse_reduction_vs_untrained_percent":
            100 * (1 - panel["trained"] / panel["untrained"]),
        "native_metadata_families": result["metadata"]["family_counts"],
        "native_duckdb_ducklake_exact_restart_and_complete_reconstruction": True,
        "native_quack_extension_evaluated": False, "typed_native_vector_columns": False,
        "metadata_proof_authority": False, "unresolved_task_contracts": 4,
        "lean": {"processes": result["logic"]["native_lean_processes"],
            "positive_compiles": result["logic"]["positive_compiles"],
            "rejected_reverse_controls": result["logic"]["rejected_reverse_controls"],
            "scope": "exact rational order of finite recorded loss endpoints only"},
        "tests": test["counts"], "claims": {"source_model_equivalence_proved": False,
            "learned_typed_logic_family_decoder_trained": False, "asymptotic_optimizer_convergence_proved": False,
            "full_task_satisfaction_proved": False, "contract_intent_recall_measured": False,
            "admitted_supervisor_planning_evaluated": False, "terminal_bench_task_harness_executed": False,
            "provider_token_savings_measured": False, "global_durable_training_budget": False,
            "generalization_beyond_measured_tasks_proved": False},
        "review_inputs": [str(experiment / "result.json"), str(ROOT / args.cold_report),
            str(ROOT / (args.tests + "-report.json")), str(ROOT / (args.run + "-source-pins.json"))],
        "changes_promoted_or_pushed": False, "sealed_predecessor_mutated": False}
    write(ROOT / args.status, status)
    print(json.dumps({"status": args.status, "selected_optimizer_steps": status["selected_optimizer_steps"],
        "all_attempt_optimizer_steps": status["all_attempt_optimizer_steps"], "heldout_evaluation_mse": panel,
        "metadata_rows": sum(status["native_metadata_families"].values()), "tests": status["tests"]}))


if __name__ == "__main__":
    main()
