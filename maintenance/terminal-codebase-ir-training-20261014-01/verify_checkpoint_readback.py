"""Fresh-process checkpoint/source replay with a separately written forward pass.

No optimizer steps are performed. Torch arithmetic and source extraction share
the pinned dependencies with training; this is independent orchestration and
formula implementation, not independent numerical infrastructure or attestation.
"""
import argparse
import hashlib
import json
from pathlib import Path

import torch
from ipfs_datasets_py.logic.formalization.autoencoder.security import codebase_autoencoder as ae

from train_codebase_ir import RUNS, extract_tasks, read, wire, write
from independent_training_review import verify_training_evidence


def forward(rows, parameters):
    encoder, bias, decoder, output_bias = parameters
    with torch.no_grad():
        data = torch.tensor([row["features"] for row in rows], dtype=torch.float32, device="cpu")
        encoded = torch.tanh(data.matmul(encoder) + bias)
        reconstruction = encoded.matmul(decoder) + output_bias
        mse = ((reconstruction - data) ** 2).mean(dim=1).tolist()
    ranks = sorted([{key: row[key] for key in ("row_id", "path", "symbol", "line")} |
        {"latent": vector, "reconstruction_error": error}
        for row, vector, error in zip(rows, encoded.tolist(), mse)],
        key=lambda row: (-row["reconstruction_error"], row["row_id"]))
    return {"ranks": ranks, "mean_reconstruction_error": sum(mse) / len(mse)}


def initial_parameters(seed):
    generator = torch.Generator(device="cpu").manual_seed(seed)
    return [torch.randn((44, 8), generator=generator, dtype=torch.float32) * 0.1,
            torch.zeros((8,), dtype=torch.float32),
            torch.randn((8, 44), generator=generator, dtype=torch.float32) * 0.1,
            torch.zeros((44,), dtype=torch.float32)]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--experiment", type=Path, required=True)
    parser.add_argument("--report", type=Path, required=True)
    args = parser.parse_args()
    output = args.experiment.absolute()
    manifest_raw = read(output / "captured-manifest.json")
    manifest = json.loads(manifest_raw)
    input_paths = [output / name for name in ("captured-manifest.json", "task-features.json", "training-review.json")]
    input_paths += [output / (run_id + suffix) for run_id, _, _ in RUNS
                    for suffix in ("-report.json", "-evaluation.json")]
    input_bytes = {path: read(path) for path in input_paths}
    repository = Path(manifest["captured_repository"])
    features, _, _ = extract_tasks(ae, manifest, repository)
    if features != json.loads(read(output / "task-features.json")):
        raise ValueError("cold source features differ from experiment")
    reports, evaluations, checks = [], [], []
    torch.set_num_threads(1)
    for run_id, seed, epochs in RUNS:
        report = json.loads(read(output / (run_id + "-report.json")))
        native = {key: value for key, value in report.items()
                  if key not in {"paths", "run_id", "observed_steps", "validation"}}
        ae.validate_codebase_autoencoder(repository=repository, expected_receipt=native)
        checkpoint_path = Path(report["output"]) / "checkpoint.json"
        raw = read(checkpoint_path)
        if hashlib.sha256(raw).hexdigest() != report["checkpoint_sha256"]:
            raise ValueError("checkpoint digest changed")
        checkpoint = json.loads(raw)
        parameters = [torch.tensor(value, dtype=torch.float32, device="cpu") for value in checkpoint["weights"]]
        if hashlib.sha256(wire([p.tolist() for p in parameters])).hexdigest() != report["metrics"]["final_weights_sha256"]:
            raise ValueError("final parameter hash differs")
        initial = initial_parameters(seed)
        if hashlib.sha256(wire([p.tolist() for p in initial])).hexdigest() != report["metrics"]["initial_weights_sha256"]:
            raise ValueError("initial seeded parameter hash differs")
        zeros = [torch.zeros_like(p) for p in parameters]
        training_rows = [row for path in report["paths"] for rows in features.values()
                         for row in rows if row["path"] == path]
        training = {name: forward(training_rows, values)
                    for name, values in (("trained", parameters), ("untrained", initial), ("zero_weights", zeros))}
        panel = json.loads(read(output / (run_id + "-evaluation.json")))
        for task in panel:
            rows = features[task["task_id"]]
            for name, tensors in (("trained", parameters), ("untrained", initial), ("zero_weights", zeros)):
                if task["split"] == "train":
                    identities = {row["row_id"] for row in rows}
                    ranks = [row for row in training[name]["ranks"] if row["row_id"] in identities]
                    observed = {"ranks": ranks, "mean_reconstruction_error":
                                sum(row["reconstruction_error"] for row in ranks) / len(ranks)}
                else:
                    observed = forward(rows, tensors)
                expected = {key: task[name][key] for key in ("ranks", "mean_reconstruction_error")}
                if observed != expected:
                    raise ValueError("cold independent forward differs: " + run_id + "/" + task["task_id"] + "/" + name)
            checks.append({"run_id": run_id, "task_id": task["task_id"], "split": task["split"],
                "feature_count": len(rows), "all_three_model_controls_exact": True})
        if read(checkpoint_path) != raw:
            raise ValueError("checkpoint changed during cold forward")
        reports.append(report)
        evaluations.extend(panel)
    review = verify_training_evidence(manifest=manifest, task_features=features,
                                     training_runs=reports, evaluations=evaluations)
    if review != json.loads(read(output / "training-review.json")):
        raise ValueError("independent review differs from original pinned inputs")
    final_features, _, _ = extract_tasks(ae, manifest, repository)
    if final_features != features or any(read(path) != raw for path, raw in input_bytes.items()):
        raise ValueError("source, frozen manifest, or cold replay input artifact changed")
    write(args.report.absolute(), {"schema": "terminal-codebase-ir-cold-checkpoint-replay@1",
        "qualified": True, "training_run_count": len(reports), "panel_count": len(checks),
        "checks": checks, "review": review, "optimizer_steps_in_this_verifier": 0,
        "separate_forward_implementation": True, "independent_numerical_backend": False,
        "source_model_equivalence_proved": False, "asymptotic_optimizer_convergence_proved": False,
        "full_task_satisfaction": False, "checkpoint_artifact_origin_authenticated": False})
    print(json.dumps({"qualified": True, "training_runs": len(reports), "panels": len(checks)}))


if __name__ == "__main__":
    main()
