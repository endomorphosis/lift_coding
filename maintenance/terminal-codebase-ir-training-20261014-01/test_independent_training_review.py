"""Adversarial joins for the independent data-only training evidence review."""
from __future__ import annotations

import copy
import hashlib
import importlib.util
import json
from pathlib import Path

import pytest

_path = Path(__file__).with_name("independent_training_review.py")
_spec = importlib.util.spec_from_file_location("independent_training_review_for_tests", _path)
review = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(review)


def sha(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, ensure_ascii=True,
        separators=(",", ":"), allow_nan=False).encode()).hexdigest()


def feature(task_id, path, index):
    identity = {"path": path, "symbol": "fn" + str(index), "line": index + 1,
                "ast_sha256": sha(["ast", task_id, index])}
    # Distinct sources deliberately share coarse native features. This is
    # representational loss, separate from exact source/AST leakage.
    return {**identity, "row_id": sha(identity), "features": [1.] + [0.] * 43}


def ranking(rows, errors, latent):
    ranks = [{"row_id": row["row_id"], "path": row["path"], "symbol": row["symbol"],
              "line": row["line"], "reconstruction_error": error, "latent": [latent] * 8}
             for row, error in zip(rows, errors)]
    ranks.sort(key=lambda row: (-row["reconstruction_error"], row["row_id"]))
    return {"mean_reconstruction_error": sum(errors) / len(errors), "ranks": ranks}


def fixture():
    manifest = {"captured_repository": "/experiment/captured-sources", "tasks": []}
    features, evaluations = {}, []
    for split, task_id, count in (("train", "task-a", 2), ("validation", "task-b", 1),
                                  ("evaluation", "task-c", 3)):
        path = task_id + "/environment/module.py"
        manifest["tasks"].append({"task_id": task_id, "split": split,
            "sources": [{"path": path, "sha256": sha(["source", task_id]), "bytes": 100}]})
        rows = [feature(task_id, path, index) for index in range(count)]
        features[task_id] = rows
        trained = ranking(rows, [.004 + index * .001 for index in range(count)], .1)
        untrained = ranking(rows, [.04 + index * .01 for index in range(count)], .2)
        zero = ranking(rows, [1 / 44] * count, 0.)
        evaluations.append({"run_id": "primary", "task_id": task_id, "split": split,
            "feature_count": count, "trained": trained, "untrained": untrained,
            "zero_weights": zero, "deterministic_identity": {"mean_reconstruction_error": 0},
            "initial_weights_sha256": sha("initial")})
    train_eval = evaluations[0]
    source = manifest["tasks"][0]["sources"][0]
    ranks = [{key: row[key] for key in ("row_id", "path", "symbol", "line", "reconstruction_error")}
             for row in train_eval["trained"]["ranks"]]
    run = {"schema": "supervisor-code-autoencoder-descriptor@1", "domain": review.DOMAIN,
        "repository": manifest["captured_repository"], "run_id": "primary",
        "source_hashes": {source["path"]: source["sha256"]}, "paths": [source["path"]],
        "source_count": 1, "sample_count": 2, "checkpoint_sha256": sha("checkpoint"),
        "receipt_sha256": sha("receipt"), "epochs_completed": 2,
        "authority": "unverified_candidate_only", "proof_authority": False, "provider_calls": 0,
        "ranks": ranks,
        "metrics": {"epochs": 2, "seed": 1729, "initial_weights_sha256": sha("initial"),
            "final_weights_sha256": sha("final"), "microbatch_count": 1, "native_kernel_calls": 2,
            "native_objective_losses": [.3, .4], "native_gradient_norms": [.1, .2],
            "before_reconstruction_loss": train_eval["untrained"]["mean_reconstruction_error"],
            "after_reconstruction_loss": train_eval["trained"]["mean_reconstruction_error"],
            "holdout_evaluated": False, "training_scope": "transductive_admitted_code_functions"},
        "observed_steps": [{"step": 1, "before_weights_sha256": sha("initial"),
                            "after_weights_sha256": sha("middle")},
                           {"step": 2, "before_weights_sha256": sha("middle"),
                            "after_weights_sha256": sha("final")}],
        "validation": {"status": "verified", "domain": review.DOMAIN,
            "receipt_sha256": sha("receipt"), "source_count": 1, "sample_count": 2,
            "authority": "unverified_candidate_only", "proof_authority": False,
            "formalization_authority": False, "omission_authority": False,
            "ranks": copy.deepcopy(train_eval["trained"]["ranks"])}}
    return {"manifest": manifest, "task_features": features,
            "training_runs": [run], "evaluations": evaluations}


def test_complete_review_preserves_lossy_feature_collisions_and_scope():
    evidence = fixture()
    result = review.verify_training_evidence(**evidence)
    assert result["qualified"] is True
    assert result["optimizer_steps_total"] == 2
    assert result["normalized_feature_cross_split_collisions"]
    assert result["feature_collision_is_source_leakage"] is False
    assert result["native_objective_monotonicity_required"] is False
    assert all(value is False for value in result["claims"].values())
    assert result["tensor_forward_independently_reexecuted"] is False
    panel = result["runs"][0]["splits"]["evaluation"]
    assert panel["feature_count"] == 3
    assert panel["trained_improves_untrained"] is True
    assert panel["trained_matches_uncompressed_identity"] is False


def test_failed_empirical_improvement_remains_a_valid_observation():
    evidence = fixture()
    evaluation = evidence["evaluations"][2]
    evaluation["trained"] = ranking(evidence["task_features"]["task-c"], [.2, .3, .4], .1)
    result = review.verify_training_evidence(**evidence)
    panel = result["runs"][0]["splits"]["evaluation"]
    assert result["qualified"] is True
    assert panel["trained_improves_untrained"] is False
    assert panel["trained_improves_zero_weights"] is False


@pytest.mark.parametrize("mutation", [
    "heldout_in_training_ledger", "source_hash_changed", "source_path_changed", "source_duplicate",
    "ast_duplicate", "feature_identity_changed", "feature_wrong_width", "feature_nonfinite",
    "feature_wrong_normalization", "step_missing", "step_chain_changed", "step_no_update",
    "final_hash_changed", "gradient_nonfinite", "no_gradient", "kernel_count_changed",
    "evaluation_row_missing", "evaluation_row_duplicate", "evaluation_source_join_changed",
    "evaluation_mean_changed", "evaluation_latent_nonfinite", "evaluation_split_changed",
    "untrained_hash_changed", "zero_control_changed", "identity_control_changed",
    "native_validation_receipt_changed", "native_validation_rank_changed", "authority_changed",
    "captured_repository_changed", "native_holdout_relabeled",
])
def test_mutated_evidence_is_rejected(mutation):
    evidence = fixture()
    manifest, run, evaluation = evidence["manifest"], evidence["training_runs"][0], evidence["evaluations"][2]
    if mutation == "heldout_in_training_ledger":
        source = manifest["tasks"][2]["sources"][0]
        run["source_hashes"][source["path"]] = source["sha256"]
        run["paths"].append(source["path"])
    elif mutation == "source_hash_changed":
        run["source_hashes"][run["paths"][0]] = sha("changed")
    elif mutation == "source_path_changed":
        manifest["tasks"][2]["sources"][0]["path"] = "../outside.py"
    elif mutation == "source_duplicate":
        manifest["tasks"][2]["sources"][0]["sha256"] = manifest["tasks"][0]["sources"][0]["sha256"]
    elif mutation == "ast_duplicate":
        row = evidence["task_features"]["task-c"][0]
        row["ast_sha256"] = evidence["task_features"]["task-a"][0]["ast_sha256"]
        row["row_id"] = sha({key: row[key] for key in ("path", "symbol", "line", "ast_sha256")})
    elif mutation == "feature_identity_changed":
        evidence["task_features"]["task-c"][0]["row_id"] = sha("foreign")
    elif mutation == "feature_wrong_width":
        evidence["task_features"]["task-c"][0]["features"].pop()
    elif mutation == "feature_nonfinite":
        evidence["task_features"]["task-c"][0]["features"][0] = float("nan")
    elif mutation == "feature_wrong_normalization":
        evidence["task_features"]["task-c"][0]["features"][0] = .5
    elif mutation == "step_missing":
        run["observed_steps"].pop()
    elif mutation == "step_chain_changed":
        run["observed_steps"][1]["before_weights_sha256"] = sha("foreign")
    elif mutation == "step_no_update":
        run["observed_steps"][0]["after_weights_sha256"] = sha("initial")
    elif mutation == "final_hash_changed":
        run["metrics"]["final_weights_sha256"] = sha("foreign")
    elif mutation == "gradient_nonfinite":
        run["metrics"]["native_gradient_norms"][0] = float("inf")
    elif mutation == "no_gradient":
        run["metrics"]["native_gradient_norms"] = [0., 0.]
    elif mutation == "kernel_count_changed":
        run["metrics"]["native_kernel_calls"] += 1
    elif mutation == "evaluation_row_missing":
        evaluation["trained"]["ranks"].pop()
    elif mutation == "evaluation_row_duplicate":
        evaluation["trained"]["ranks"][0] = copy.deepcopy(evaluation["trained"]["ranks"][1])
    elif mutation == "evaluation_source_join_changed":
        evaluation["trained"]["ranks"][0]["path"] = run["paths"][0]
    elif mutation == "evaluation_mean_changed":
        evaluation["trained"]["mean_reconstruction_error"] += .1
    elif mutation == "evaluation_latent_nonfinite":
        evaluation["trained"]["ranks"][0]["latent"][0] = float("nan")
    elif mutation == "evaluation_split_changed":
        evaluation["split"] = "train"
    elif mutation == "untrained_hash_changed":
        evaluation["initial_weights_sha256"] = sha("foreign")
    elif mutation == "zero_control_changed":
        evaluation["zero_weights"]["ranks"][0]["latent"][0] = .1
    elif mutation == "identity_control_changed":
        evaluation["deterministic_identity"]["mean_reconstruction_error"] = .001
    elif mutation == "native_validation_receipt_changed":
        run["validation"]["receipt_sha256"] = sha("foreign")
    elif mutation == "native_validation_rank_changed":
        run["validation"]["ranks"][0]["line"] += 1
    elif mutation == "authority_changed":
        run["proof_authority"] = True
    elif mutation == "captured_repository_changed":
        run["repository"] = "/foreign/source"
    elif mutation == "native_holdout_relabeled":
        run["metrics"]["holdout_evaluated"] = True
    with pytest.raises(review.TrainingEvidenceError):
        review.verify_training_evidence(**evidence)


def test_same_seed_and_epoch_replay_is_checked():
    evidence = fixture()
    replay = copy.deepcopy(evidence["training_runs"][0])
    replay["run_id"] = "replay"
    evidence["training_runs"].append(replay)
    for evaluation in list(evidence["evaluations"]):
        other = copy.deepcopy(evaluation)
        other["run_id"] = "replay"
        evidence["evaluations"].append(other)
    result = review.verify_training_evidence(**evidence)
    assert result["reproducibility"]["exact_replay_pairs_observed"] is True
    replay["metrics"]["final_weights_sha256"] = sha("different-final")
    replay["observed_steps"][-1]["after_weights_sha256"] = sha("different-final")
    with pytest.raises(review.TrainingEvidenceError, match="replay changed parameter"):
        review.verify_training_evidence(**evidence)


def test_weighted_metrics_use_function_counts_across_tasks():
    evidence = fixture()
    extra = copy.deepcopy(evidence["manifest"]["tasks"][2])
    extra["task_id"] = "task-d"
    extra["sources"] = [{"path": "task-d/environment/module.py", "sha256": sha("source-d"), "bytes": 100}]
    evidence["manifest"]["tasks"].append(extra)
    rows = [feature("task-d", extra["sources"][0]["path"], 0)]
    evidence["task_features"]["task-d"] = rows
    evaluation = copy.deepcopy(evidence["evaluations"][2])
    evaluation.update(task_id="task-d", feature_count=1, trained=ranking(rows, [.025], .1),
        untrained=ranking(rows, [.04], .2), zero_weights=ranking(rows, [1 / 44], 0.))
    evidence["evaluations"].append(evaluation)
    result = review.verify_training_evidence(**evidence)
    panel = result["runs"][0]["splits"]["evaluation"]
    assert panel["function_weighted_mean_reconstruction_error"]["trained"] == pytest.approx(.01)
    assert panel["task_macro_mean_reconstruction_error"]["trained"] == pytest.approx(.015)


def test_replay_rejects_latent_drift_even_when_means_match():
    evidence = fixture()
    replay = copy.deepcopy(evidence["training_runs"][0])
    replay["run_id"] = "replay"
    evidence["training_runs"].append(replay)
    for evaluation in list(evidence["evaluations"]):
        other = copy.deepcopy(evaluation)
        other["run_id"] = "replay"
        evidence["evaluations"].append(other)
    evidence["evaluations"][-1]["trained"]["ranks"][0]["latent"][0] = .11
    with pytest.raises(review.TrainingEvidenceError, match="replay changed task inference"):
        review.verify_training_evidence(**evidence)
