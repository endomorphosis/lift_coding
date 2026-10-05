"""Summarize pinned frozen-development results without publishing vector tables."""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
from pathlib import Path

LANES = ("legacy8", "native384", "native768")
SEEDS = (1729, 1730, 1731)
VIEWS = ("raw_source", "latent", "reconstructed", "mean_reconstructed", "pca_reconstructed", "pca_latent")
BASELINES = dict(zip(LANES, (0.9063527830841718, 0.9618966579623486, 0.9838375773719246), strict=True))


def require(condition, reason):
    if not condition:
        raise ValueError(reason)


def raw(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False).encode()


def binding(path):
    path = Path(path).absolute()
    require(not any(p.is_symlink() for p in (path, *path.parents)), "nonsymlink file required")
    data = path.read_bytes()
    require(0 < len(data) <= 32 * 1024**2, "bounded nonempty result required")
    return {"path": str(path), "bytes": len(data), "sha256": hashlib.sha256(data).hexdigest()}


def read(reference, sealed=True):
    require(binding(reference["path"]) == reference, "selected result binding differs")

    def pairs(items):
        result = {}
        for key, value in items:
            require(key not in result, "duplicate result key")
            result[key] = value
        return result

    value = json.loads(Path(reference["path"]).read_bytes(), object_pairs_hook=pairs,
                       parse_constant=lambda _: (_ for _ in ()).throw(ValueError("nonfinite JSON")))
    if sealed:
        require(value["content_sha256"] == hashlib.sha256(raw({k: v for k, v in value.items() if k != "content_sha256"})).hexdigest(),
                "result seal differs")
    return value


def stats(values):
    require(len(values) == 3 and all(type(v) in (int, float) and math.isfinite(v) for v in values), "all three finite seeds required")
    return {"mean": math.fsum(values) / 3, "minimum": min(values), "maximum": max(values), "seed_values": values}


def summarize(evaluation_reference, retrieval_reference):
    evaluation = read(evaluation_reference)
    retrieval = read(retrieval_reference)
    require(evaluation["schema"] == "source-reconstruction-frozen-evaluation-batch/v1"
            and evaluation["successful_arms"] == 9 and evaluation["optimizer_updates"] == 0
            and evaluation["pca_control_fit_count"] == 3 and evaluation["query_rows_read_before_all_control_fits"] == 0
            and evaluation["all_original_train_outputs_exact"] and evaluation["all_master_and_source_files_preserved"],
            "completed frozen nine-arm evaluation required")
    expected_order = [(lane, seed) for lane in LANES for seed in SEEDS]
    require([(a["lane_id"], a["seed"]) for a in evaluation["arms"]] == expected_order, "fixed nine-arm order differs")
    # The command receipt is separate from the numeric worker: ranking completed
    # for every arm before the first reference-scoring command was invoked.
    require(retrieval["all_rankings_persisted_before_scoring"] is True and retrieval["successful_rank_commands"] == 9
            and retrieval["successful_score_commands"] == 9, "separate completed rank and score stages required")
    arms = []
    for arm in evaluation["arms"]:
        lane, seed = arm["lane_id"], arm["seed"]
        numeric = read(arm["numeric_report_binding"])
        endpoint_binding = arm["endpoint_binding"]
        require(binding(endpoint_binding["path"]) == endpoint_binding and numeric["endpoint_binding"] == endpoint_binding,
                "numeric endpoint join differs")
        directory = Path(endpoint_binding["path"]).parent
        rank_reference, score_reference = binding(directory / "rankings.json"), binding(directory / "scores.json")
        rankings, scores = read(rank_reference), read(score_reference)
        require(scores["rankings_file_binding"] == rank_reference and scores["ranking_content_sha256"] == rankings["content_sha256"]
                and scores["endpoints_content_sha256"] == rankings["endpoints_content_sha256"], "persisted ranking/score join differs")
        require(numeric["lane_id"] == rankings["lane_id"] == lane and numeric["seed"] == rankings["seed"] == seed,
                "lane/seed result join differs")
        require(numeric["optimizer_updates"] == 0 and numeric["train_original_outputs_exact"]
                and numeric["restored_model_and_adam_preserved"] and not numeric["parameter_gradients_created"],
                "inference state preservation differs")
        require(scores["scored_positive_queries"] == 8 and scores["negative_diagnostic_queries"] == 8
                and scores["context_diagnostic_queries"] == 2 and not scores["query_reference_consumed_in_ranking"],
                "fixed8/8/2 exposed cohort differs")
        require(all(value == 0 for value in numeric["masks"].values()) and all(value == 0 for value in scores["masks"].values()),
                "semantic masks must remain zero")
        require(set(scores["arms"]) == set(VIEWS), "all six matched views required")
        authored = {view: scores["arms"][view]["summary"] for view in VIEWS}
        require(abs(authored["raw_source"]["mean_graded_facet_ndcg"] - BASELINES[lane]) < 1e-14,
                "historical native raw baseline differs")
        require(all(metrics["row_count"] == 16 for metrics in numeric["cohorts"]["validation_source_only"].values()),
                "sixteen source-only numerical queries required")
        arms.append({"lane_id": lane, "seed": seed, "architecture": numeric["architecture"], "pca_control": numeric["pca_control"],
                     "numeric_report_binding": arm["numeric_report_binding"], "endpoint_binding": endpoint_binding,
                     "ranking_binding": rank_reference, "scoring_binding": score_reference,
                     "train_metrics": numeric["cohorts"]["train"], "development_metrics": numeric["cohorts"]["validation_source_only"],
                     "authored_retrieval_aggregates": authored})
    lanes = {}
    for lane in LANES:
        selected = [a for a in arms if a["lane_id"] == lane]
        mse = {view: stats([a["development_metrics"][view]["raw_coordinate_mse"] for a in selected])
               for view in ("raw_identity", "reconstructed", "mean_reconstructed", "pca_reconstructed")}
        ndcg = {view: stats([a["authored_retrieval_aggregates"][view]["mean_graded_facet_ndcg"] for a in selected]) for view in VIEWS}
        lanes[lane] = {"development_raw_coordinate_mse": mse, "authored_positive_mean_graded_facet_ndcg_at_5": ndcg,
                       "all_neural_seeds_better_than_train_mean_mse": all(a["development_metrics"]["reconstructed"]["raw_coordinate_mse"] <
                           a["development_metrics"]["mean_reconstructed"]["raw_coordinate_mse"] for a in selected),
                       "all_neural_seeds_worse_than_train_pca_mse": all(a["development_metrics"]["reconstructed"]["raw_coordinate_mse"] >
                           a["development_metrics"]["pca_reconstructed"]["raw_coordinate_mse"] for a in selected),
                       "pca_effective_rank": selected[0]["pca_control"]["effective_train_rank"],
                       "pca_retained_axes": selected[0]["pca_control"]["retained_axes"]}
    return {"schema": "source-reconstruction-frozen-development-summary/v1", "evaluation_report_binding": evaluation_reference,
            "retrieval_receipt_binding": retrieval_reference, "arms": arms, "lanes": lanes,
            "scope": "historical_exposed_authored_legal_development_not_pristine_holdout_or_semantic_accuracy",
            "train_sources": 16, "train_groups": 4, "development_sources": 18, "development_groups": 11,
            "source_only_numerical_queries": 16, "authored_positive_retrieval_queries": 8,
            "negative_diagnostic_queries": 8, "context_diagnostic_queries": 2,
            "all_three_preselected_seeds_reported": True, "seed_selected_on_development": False,
            "model_loads": evaluation["model_loads"], "optimizer_updates": 0, "pca_control_fit_count": 3,
            "encoder_backbone_calls": 0, "prover_calls": 0, "all_original_train_outputs_exact": True,
            "all_master_and_source_files_preserved": True, "semantic_or_proof_qualification": False,
            "masks": evaluation["masks"], "vector_row_tables_included": False,
            "limitations": ["Authored reference relevance is a development diagnostic, not an independent semantic label.",
                            "Training retrieval pool lacks exact counterparts and complete rule/qualifier coverage.",
                            "The two declared-context rows use raw source vectors and cannot establish contextual fidelity.",
                            "Dense centered TRAIN rank is fifteen; neural bottlenecks thirty-two and sixty-four exceed it.",
                            "MSE scales differ across native lanes; cross-lane error does not rank semantic quality."]}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--evaluation-report", required=True)
    parser.add_argument("--evaluation-report-sha256", required=True)
    parser.add_argument("--retrieval-receipt", required=True)
    parser.add_argument("--retrieval-receipt-sha256", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    evaluation_reference, retrieval_reference = binding(args.evaluation_report), binding(args.retrieval_receipt)
    require(evaluation_reference["sha256"] == args.evaluation_report_sha256
            and retrieval_reference["sha256"] == args.retrieval_receipt_sha256, "externally selected result differs")
    value = summarize(evaluation_reference, retrieval_reference)
    value["helper_binding"] = binding(__file__)
    value["content_sha256"] = hashlib.sha256(raw(value)).hexdigest()
    with Path(args.output).open("xb") as stream:
        os.chmod(args.output, 0o600)
        stream.write(json.dumps(value, sort_keys=True, indent=2, allow_nan=False).encode() + b"\n")
        stream.flush()
        os.fsync(stream.fileno())
    print(json.dumps({"summary_binding": binding(args.output)}, sort_keys=True))


if __name__ == "__main__":
    main()
