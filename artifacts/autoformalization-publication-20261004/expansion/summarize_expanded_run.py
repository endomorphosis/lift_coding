"""Create a scalar-only summary of the pinned authored TRAIN32 experiment."""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
from pathlib import Path

LANES = ("legacy8", "native384", "native768")
SEEDS = (1729, 1730, 1731)


def require(condition, reason):
    if not condition:
        raise ValueError(reason)


def raw(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False).encode()


def binding(path):
    path = Path(path).absolute()
    require(not any(p.is_symlink() for p in (path, *path.parents)), "nonsymlink file required")
    data = path.read_bytes()
    require(0 < len(data) <= 32 * 1024**2, "bounded ordinary result required")
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
                       parse_constant=lambda _: (_ for _ in ()).throw(ValueError("nonfinite result")))
    if sealed:
        require(value["content_sha256"] == hashlib.sha256(raw({k: v for k, v in value.items() if k != "content_sha256"})).hexdigest(),
                "result seal differs")
    return value


def stats(values):
    require(len(values) == 3 and all(type(v) in (int, float) and math.isfinite(v) for v in values), "three finite seed outcomes required")
    return {"mean": math.fsum(values) / 3, "minimum": min(values), "maximum": max(values), "seed_values": values}


def summarize(encoding_ref, training_ref, evaluation_ref):
    encoding, training, evaluation = read(encoding_ref), read(training_ref, sealed=False), read(evaluation_ref)
    require(encoding["status"] == "completed" and encoding["native_source_row_encodings"] == 192
            and encoding["optimizer_updates"] == 0, "complete source encoding required")
    require(training["successful_arms"] == 9 and training["actual_optimizer_updates"] == 1827
            and training["selected_optimizer_updates"] == 1800 and training["selected_inputs_unchanged"], "fixed nine fits required")
    require(evaluation["successful_arms"] == 9 and evaluation["model_loads"] == 18 and evaluation["optimizer_updates"] == 0
            and evaluation["pca_control_fit_count"] == 3 and evaluation["development_rows_read_before_all_control_fits"] == 0
            and evaluation["all_new_train_outputs_exact"] and evaluation["all_master_and_source_files_preserved"]
            and evaluation["all_restored_models_and_adam_preserved"] and not evaluation["best_development_seed_selected"],
            "complete frozen comparison required")
    order = [(lane, seed) for lane in LANES for seed in SEEDS]
    require([(a["lane_id"], a["seed"]) for a in training["arms"]] == order
            and [(a["lane_id"], a["seed"]) for a in evaluation["arms"]] == order, "fixed seed order differs")
    arms = []
    for fitted, measured in zip(training["arms"], evaluation["arms"], strict=True):
        fit = read(fitted["training_report_binding"])
        numeric = read(measured["numeric_report_binding"])
        require(numeric["new_training_report_binding"] == fitted["training_report_binding"]
                and fit["training_rows"] == 32 and fit["query_or_dev_rows_read"] == 0
                and fit["source_only_development_metadata_rows_read"] == 32, "TRAIN/DEV scope differs")
        require(all(type(v) is int and v == 0 for v in numeric["masks"].values())
                and all(type(v) is int and v == 0 for v in fit["masks"].values()), "zero semantic masks required")
        require(binding(numeric["endpoint_binding"]["path"]) == numeric["endpoint_binding"], "private endpoint binding differs")
        for cohort in numeric["cohorts"].values():
            require(all(item["row_count"] == 32 for item in cohort.values()), "all numerical outcomes require32 rows")
        require(all(v["development_queries"] == 32 and v["fixed_train_candidates"] == 32
                    and v["semantic_relevance_measured"] is False for v in numeric["source_neighborhood_agreement"].values()),
                "source-neighborhood scope differs")
        arms.append({"lane_id": fit["lane_id"], "seed": fit["seed"], "architecture": numeric["architecture"],
                     "training_report_binding": fitted["training_report_binding"], "numeric_report_binding": measured["numeric_report_binding"],
                     "endpoint_binding": numeric["endpoint_binding"], "selected_checkpoint_binding": fit["selected_checkpoint"],
                     "initial_train_mse": fit["initial_observations"]["raw_coordinate_mse"],
                     "final_train_mse": fit["final_observations"]["raw_coordinate_mse"], "pca_control": numeric["pca_control"],
                     "cohorts": numeric["cohorts"], "source_neighborhood_agreement": numeric["source_neighborhood_agreement"]})
    lanes = {}
    for lane in LANES:
        selected = [a for a in arms if a["lane_id"] == lane]
        views = selected[0]["cohorts"]["development"]
        mse = {view: stats([a["cohorts"]["development"][view]["raw_coordinate_mse"] for a in selected]) for view in views}
        neighborhoods = {view: {metric: stats([a["source_neighborhood_agreement"][view][metric] for a in selected])
                                for metric in ("mean_top1_agreement_with_raw", "mean_top5_set_overlap_fraction_with_raw")}
                         for view in selected[0]["source_neighborhood_agreement"]}
        lanes[lane] = {"development_mse": mse, "source_neighborhood_agreement": neighborhoods,
                       "new_mean_mse_reduction_fraction_against_old_models": 1 - mse["new_reconstructed"]["mean"] / mse["old_reconstructed"]["mean"],
                       "all_new_seeds_better_than_old_same_seed_mse": all(a["cohorts"]["development"]["new_reconstructed"]["raw_coordinate_mse"] <
                           a["cohorts"]["development"]["old_reconstructed"]["raw_coordinate_mse"] for a in selected),
                       "all_new_seeds_worse_than_train_pca_mse": all(a["cohorts"]["development"]["new_reconstructed"]["raw_coordinate_mse"] >
                           a["cohorts"]["development"]["pca_reconstructed"]["raw_coordinate_mse"] for a in selected),
                       "pca_effective_rank": selected[0]["pca_control"]["effective_train_rank"],
                       "pca_retained_axes": selected[0]["pca_control"]["retained_axes"]}
    return {"schema": "authored-source-expanded-reconstruction-summary/v1", "scope": "exposed_authored_composition_source_reconstruction_only",
            "encoding_report_binding": encoding_ref, "training_batch_binding": training_ref, "evaluation_report_binding": evaluation_ref,
            "native_vectors_produced": 192, "source_rows": 64, "source_groups": 16, "train_rows": 32, "development_rows": 32,
            "train_groups": 8, "development_groups": 8, "new_selected_models": 9, "selected_optimizer_updates": 1800,
            "private_comparison_updates": 27, "actual_optimizer_updates": 1827, "evaluation_model_restores": 18,
            "evaluation_optimizer_updates": 0, "source_only_development_metadata_rows_read_during_fit": 32,
            "development_vector_rows_read_during_fit": 0, "arms": arms, "lanes": lanes, "all_three_seeds_reported": True,
            "best_development_seed_selected": False, "masks": evaluation["masks"], "source_vector_tables_included": False,
            "independent_semantic_accuracy_measured": False, "semantic_relevance_measured": False, "proof_authority": False,
            "source_fidelity_established": False, "qualified": False,
            "limitations": ["Sources are exposed authored legal compositions, not natural-source or pristine confirmation evidence.",
                            "Exact source/group separation does not authenticate independent derivative provenance.",
                            "The new and old models use different TRAIN cohorts; this comparison measures adaptation, not an isolated sample-size effect.",
                            "Dense TRAIN rank31 is below the retained neural bottlenecks32/64; PCA retains31 independent axes.",
                            "Raw-neighborhood agreement measures vector preservation rather than semantic retrieval relevance.",
                            "Native numerical scales differ and cannot rank semantic quality across lanes."]}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("encoding-report", "training-batch", "evaluation-report"):
        parser.add_argument("--" + name, required=True)
        parser.add_argument("--" + name + "-sha256", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    references = []
    for name in ("encoding_report", "training_batch", "evaluation_report"):
        selected = binding(getattr(args, name))
        require(selected["sha256"] == getattr(args, name + "_sha256"), "externally selected outcome differs")
        references.append(selected)
    value = summarize(*references)
    value["helper_binding"] = binding(__file__)
    value["content_sha256"] = hashlib.sha256(raw(value)).hexdigest()
    with Path(args.output).open("xb") as stream:
        os.chmod(args.output, 0o600)
        stream.write(json.dumps(value, sort_keys=True, indent=2, allow_nan=False).encode() + b"\n")
    print(json.dumps({"summary_binding": binding(args.output)}, sort_keys=True))


if __name__ == "__main__":
    main()
