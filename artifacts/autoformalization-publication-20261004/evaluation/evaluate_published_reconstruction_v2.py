"""Frozen CPU reconstruction diagnostics, with TRAIN-only linear controls.

The CLI restores published selected200 checkpoints and runs inference only.
It reads no formal targets, executes no encoder backbone or prover, and never
calls the training helper's CLI, preflight, run_arm, or fit_steps functions.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import resource
import sys
import time
from pathlib import Path

MAX_BYTES = 32 * 1024**2
MANIFEST_SHA = "30e2fe3b112f60fd7f8d9494f88caaba674efdc8424a3c174a0e34570282cbf5"
RUN_PLAN_SHA = "b02b0b35a9f2d82abd5422643f9034bea30e1d83f0c21772aa0a609c234ead3b"
BOOTSTRAP_SHA = "910ff61a235d6e988e78b34a3b27d7ae7520f2bb10722881ab532c934be1199e"
TRAIN_HELPER_SHA = "387c0335549374a98e1d5458d9746733fe385dd760584fdf059f6266c44873d3"
CHECKER_SHA = "21816a6540b8e02f7dadcdf7efdf04c071f62b9e90e29199e8e878bcb9cc59e2"
LANE_OWNER_SHA = "d7d2e1303e15d46b70997e5880df6fb9a690bfebde63666cad04db516f3ef3a8"
LANES = {"legacy8": (8, 16, 4), "native384": (384, 128, 32), "native768": (768, 128, 64)}
SEEDS = (1729, 1730, 1731)
MASKS = ("weak_decoder_fit", "strong_semantic_fit", "contrastive_supervision", "proof_supervision", "fidelity_evaluation")


def require(value, reason):
    if not value:
        raise ValueError(reason)


def raw(value):
    return json.dumps(value, sort_keys=True, ensure_ascii=False, separators=(",", ":"), allow_nan=False).encode("utf-8")


def digest(value):
    return hashlib.sha256(raw(value)).hexdigest()


def sealed(value):
    return {**value, "content_sha256": digest(value)}


def closed(value, keys, label):
    require(type(value) is dict and set(value) == set(keys), "closed " + label + " required")


def sha(value):
    require(type(value) is str and len(value) == 64 and all(c in "0123456789abcdef" for c in value), "lowercase SHA256 required")


def binding(path):
    path = Path(path)
    require(path.is_absolute() and not any(p.is_symlink() for p in (path, *path.parents)) and path.is_file(), "absolute regular nonsymlink file required")
    before = path.stat()
    require(0 < before.st_size <= MAX_BYTES, "bounded nonempty file required")
    data = path.read_bytes()
    after = path.stat()
    require((before.st_dev, before.st_ino, before.st_size, before.st_mtime_ns) ==
            (after.st_dev, after.st_ino, after.st_size, after.st_mtime_ns), "file changed during read")
    return {"path": str(path), "bytes": len(data), "sha256": hashlib.sha256(data).hexdigest()}


def captured(reference):
    closed(reference, {"path", "bytes", "sha256"}, "file binding")
    sha(reference["sha256"])
    require(binding(reference["path"]) == reference, "externally selected file pin differs")
    data = Path(reference["path"]).read_bytes()
    require(len(data) == reference["bytes"] and hashlib.sha256(data).hexdigest() == reference["sha256"], "captured file pin differs")
    return data


def decode(data):
    def pairs(items):
        result = {}
        for key, value in items:
            require(key not in result, "duplicate JSON key")
            result[key] = value
        return result
    return json.loads(data.decode("utf-8", "strict"), object_pairs_hook=pairs,
                      parse_constant=lambda _: (_ for _ in ()).throw(ValueError("nonfinite JSON")))


def read(reference):
    return decode(captured(reference))


def seal_check(value):
    require(type(value) is dict and value.get("content_sha256") == digest({k: v for k, v in value.items() if k != "content_sha256"}), "JSON seal differs")


def compiled_owner(reference, expected_sha, name):
    require(reference["sha256"] == expected_sha, "externally selected implementation differs")
    data = captured(reference)
    namespace = {"__name__": name, "__file__": reference["path"]}
    exec(compile(data, reference["path"], "exec"), namespace)
    return namespace


def write(path, value):
    data = json.dumps(sealed(value), sort_keys=True, indent=2, ensure_ascii=False, allow_nan=False).encode("utf-8") + b"\n"
    require(len(data) <= MAX_BYTES, "bounded output JSON required")
    with path.open("xb") as stream:
        os.chmod(path, 0o600)
        stream.write(data)
        stream.flush()
        os.fsync(stream.fileno())
    return binding(path)


def validate_cohort(value, run_plan):
    closed(value, {"schema", "rows", "contains_formal_targets", "content_sha256"}, "source-only cohort")
    seal_check(value)
    require(value["schema"] == "source-only-frozen-evaluation-cohort/v1" and value["contains_formal_targets"] is False, "source-only metadata scope differs")
    require(type(value["rows"]) is list and len(value["rows"]) == 34, "exact34 metadata rows required")
    indexed = {}
    for row in value["rows"]:
        closed(row, {"id", "split", "group_id", "source_sha256", "input_sha256", "context_role"}, "source-only cohort row")
        sha(row["source_sha256"])
        sha(row["input_sha256"])
        require(row["id"] == "sha256:" + row["input_sha256"] and row["id"] not in indexed, "unique panel input identity required")
        require(row["split"] in {"train", "validation"} and type(row["group_id"]) is str and bool(row["group_id"]), "declared split/group required")
        require(row["context_role"] in {"none_required", "explicit_assumptions"}, "known context role required")
        indexed[row["id"]] = row
    train = [row for row in indexed.values() if row["split"] == "train"]
    query = [row for row in indexed.values() if row["split"] == "validation"]
    require(len(train) == 16 and len(query) == 18 and sum(r["context_role"] == "none_required" for r in query) == 16
            and all(r["context_role"] == "none_required" for r in train), "fixedTRAIN16/source-only16/context2 cohort required")
    for key in ("id", "source_sha256", "input_sha256", "group_id"):
        require(not ({r[key] for r in train} & {r[key] for r in query}), "TRAIN/query " + key + " overlap")
    selected = {r["id"]: r for r in run_plan["train_selection"]}
    require(set(selected) == {r["id"] for r in train}, "historical TRAIN IDs differ")
    for row in train:
        require(all(row[k] == selected[row["id"]][k] for k in ("id", "group_id", "source_sha256", "split")), "historical TRAIN metadata differs")
    return indexed


def validate_bundle(bundle, expected, owner, lane, split, cohort, profile=None):
    receipt = owner["validate_lane_bundle"](bundle, expected_bindings=expected)
    require(receipt["lane_id"] == lane and receipt["dimension"] == LANES[lane][0]
            and receipt["available_count"] == receipt["row_count"] == (16 if split == "train" else 18), "complete native cohort differs")
    if profile is not None:
        require(raw(bundle["profile"]) == raw(profile), "full frozen native profile differs")
    require({r["id"] for r in bundle["rows"]} == {r["id"] for r in cohort.values() if r["split"] == split}, "native cohort IDs differ")
    for row in bundle["rows"]:
        meta = cohort[row["id"]]
        require(meta["split"] == split and meta["source_sha256"] == hashlib.sha256(row["input"]["source_text"].encode("utf-8")).hexdigest()
                and meta["context_role"] == row["input"]["context"]["role"], "source/context metadata join differs")
    return receipt


def finite(torch, values):
    require(all(v.dtype == torch.float32 and v.device.type == "cpu" and bool(torch.isfinite(v).all()) for v in values), "finite CPU float32 tensors required")


def fit_pca_control(torch, train, normalization, latent_width):
    """Use only TRAIN tensors; return actual rank axes without padding."""
    finite(torch, (train,))
    require(train.ndim == 2 and train.shape[0] >= 2 and type(latent_width) is int and latent_width > 0, "bounded control shape required")
    mean = torch.tensor(normalization["mean"], dtype=torch.float32)
    rms = normalization["rms"]
    require(mean.shape == (train.shape[1],) and math.isfinite(rms) and rms > 1e-8, "fixed TRAIN normalization required")
    normalized = (train - mean) / rms
    center = normalized.mean(dim=0)
    centered = normalized - center
    _, singular, axes = torch.linalg.svd(centered, full_matrices=False)
    threshold = float(max(centered.shape) * torch.finfo(torch.float32).eps * singular[0])
    rank = int((singular > threshold).sum()) if threshold > 0 else 0
    require(rank <= min(train.shape[1], train.shape[0] - 1), "centered TRAIN rank exceeds available independent rows")
    retained = min(latent_width, rank)
    basis = axes[:retained].clone()
    finite(torch, (mean, center, basis))
    return {"mean": mean, "rms": rms, "center": center, "basis": basis, "rank": rank,
            "retained": retained, "threshold": threshold}


def project_pca_control(torch, control, values):
    finite(torch, (values,))
    centered = (values - control["mean"]) / control["rms"] - control["center"]
    latent = centered @ control["basis"].T
    reconstructed = (latent @ control["basis"] + control["center"]) * control["rms"] + control["mean"]
    mean_reconstructed = control["mean"].expand_as(values).clone()
    finite(torch, (latent, reconstructed, mean_reconstructed))
    return latent, reconstructed, mean_reconstructed


def reconstruction_metrics(torch, source, reconstructed):
    finite(torch, (source, reconstructed))
    require(source.shape == reconstructed.shape and source.ndim == 2 and source.shape[0] > 0, "complete metric cohort required")
    norms = torch.linalg.vector_norm(source, dim=1) * torch.linalg.vector_norm(reconstructed, dim=1)
    defined = norms > 0
    cosine = ((source[defined] * reconstructed[defined]).sum(dim=1) / norms[defined]).clamp(-1., 1.)
    distortion = 1. - cosine
    return {"row_count": int(source.shape[0]), "raw_coordinate_mse": float(torch.nn.functional.mse_loss(reconstructed, source)),
            "cosine_defined_rows": int(defined.sum()), "cosine_undefined_rows": int((~defined).sum()),
            "mean_cosine_distortion": float(distortion.mean()) if len(distortion) else None,
            "maximum_cosine_distortion": float(distortion.max()) if len(distortion) else None}


def pca_metadata(control):
    return {"effective_train_rank": control["rank"], "retained_axes": control["retained"], "threshold": control["threshold"],
            "basis_sha256": digest(control["basis"].tolist()), "fit_rows": 16, "query_rows_read_before_fit": 0,
            "recipe": "TRAIN_centered_SVD/v1"}


def check_plan(plan, reference):
    closed(plan, {"schema", "helper_binding", "bootstrap_binding", "release_manifest_binding", "run_plan_binding", "lane_owner_binding",
                  "cohort_metadata_binding", "training_report_bindings", "lanes", "authorization_scope", "content_sha256"}, "evaluation plan")
    seal_check(plan)
    require(plan["schema"] == "source-reconstruction-frozen-evaluation-plan/v1"
            and plan["authorization_scope"] == "source_only_frozen_reconstruction_evaluation_no_semantic_admission", "evaluation scope differs")
    require(binding(Path(__file__).absolute()) == plan["helper_binding"], "worker implementation differs")
    require(plan["release_manifest_binding"]["sha256"] == MANIFEST_SHA and plan["run_plan_binding"]["sha256"] == RUN_PLAN_SHA,
            "selected publication/training generation differs")
    require(set(plan["lanes"]) == set(LANES) and len(plan["training_report_bindings"]) == 9, "complete ordered nine arms required")
    for lane in LANES:
        closed(plan["lanes"][lane], {"train_bundle_binding", "train_expected_binding", "query_bundle_binding", "query_expected_binding"}, "selected native lane")
    require(binding(reference["path"]) == reference, "evaluation plan changed")


def run(reference, output):
    require(sys.flags.isolated and sys.dont_write_bytecode, "native interpreter -I -B required")
    plan = read(reference)
    check_plan(plan, reference)
    output = Path(output)
    require(output.is_absolute() and output.parent.is_dir() and not output.exists()
            and not any(p.is_symlink() for p in (output, *output.parents)), "fresh absolute nonsymlink output directory required")
    output.mkdir(mode=0o700)
    resource.setrlimit(resource.RLIMIT_CPU, (90, 100))
    resource.setrlimit(resource.RLIMIT_AS, (8 * 1024**3, 8 * 1024**3))
    resource.setrlimit(resource.RLIMIT_FSIZE, (32 * 1024**2, 32 * 1024**2))
    started = time.monotonic()
    manifest = read(plan["release_manifest_binding"])
    seal_check(manifest)
    require(manifest["schema"] == "source-vector-reconstruction-public-release/v1" and len(manifest["arms"]) == 9, "selected release schema differs")
    release = Path(plan["release_manifest_binding"]["path"]).parent
    release_bindings = []
    for item in manifest["files"]:
        require(type(item["path"]) is str and not Path(item["path"]).is_absolute() and ".." not in Path(item["path"]).parts,
                "release relative path required")
        selected = {**item, "path": str(release / item["path"])}
        require(binding(selected["path"]) == selected, "downloaded release file differs")
        release_bindings.append(selected)
    checker_reference = next(b for b in release_bindings if Path(b["path"]).name == "verify_reconstruction_release.py")
    checker = compiled_owner(checker_reference, CHECKER_SHA, "frozen_published_integrity_checker")
    integrity = checker["verify"](release, MANIFEST_SHA)
    require(integrity["selected_checkpoints_verified"] == 9, "complete selected checkpoint integrity required")
    train_reference = next(b for b in release_bindings if Path(b["path"]).name == "train_reconstruction.py")
    helper = compiled_owner(train_reference, TRAIN_HELPER_SHA, "frozen_published_training_helper")
    owner = compiled_owner(plan["lane_owner_binding"], LANE_OWNER_SHA, "frozen_native_lane_owner")
    run_plan = read(plan["run_plan_binding"])
    seal_check(run_plan)
    cohort = validate_cohort(read(plan["cohort_metadata_binding"]), run_plan)
    reports = [read(b) for b in plan["training_report_bindings"]]
    for report in reports:
        seal_check(report)
        require(report["masks"] == dict.fromkeys(MASKS, 0) and all(type(v) is int for v in report["masks"].values())
                and all(report[k] is False for k in ("semantic_fit_authorized", "contrastive_fit_authorized", "source_fidelity_established", "proof_authority", "qualified")),
                "historical training authority differs")
    require([(a["lane_id"], a["seed"]) for a in manifest["arms"]] == [(lane, seed) for lane in LANES for seed in SEEDS], "ordered release arms differ")
    require([(r["lane_id"], r["seed"]) for r in reports] == [(lane, seed) for lane in LANES for seed in SEEDS], "ordered historical reports differ")
    train_bundles, train_receipts, checkpoints, checkpoint_bindings = {}, {}, {}, {}
    for lane in LANES:
        selected = plan["lanes"][lane]
        require(selected["train_bundle_binding"] == run_plan["lanes"][lane]["bundle_binding"]
                and selected["train_expected_binding"] == run_plan["lanes"][lane]["expected_lane_binding"], "original TRAIN generation differs")
        train_bundles[lane] = read(selected["train_bundle_binding"])
        train_receipts[lane] = validate_bundle(train_bundles[lane], read(selected["train_expected_binding"]), owner, lane, "train", cohort)
    for arm, report in zip(manifest["arms"], reports, strict=True):
        key = (arm["lane_id"], arm["seed"])
        checkpoint_binding = next(b for b in release_bindings if b["path"] == str(release / arm["checkpoint_path"]))
        checkpoint = read(checkpoint_binding)
        seal_check(checkpoint)
        require(raw(checkpoint["config"]) == raw(arm["config"]) == raw(report["config"]), "selected checkpoint/historical config differs")
        require(report["schema"] == "source-vector-reconstruction-training-report/v1" and report["query_or_dev_rows_read"] == 0
                and report["selected_optimizer_updates"] == 200 and report["actual_total_optimizer_updates"] == 203,
                "historical fit scope differs")
        require(report["selected_checkpoint"]["sha256"] == checkpoint_binding["sha256"]
                and report["selected_checkpoint"]["bytes"] == checkpoint_binding["bytes"]
                and report["normalization"] == checkpoint["normalization"], "historical selected checkpoint bytes/normalization differ")
        require(arm["config"]["plan_sha256"] == digest(run_plan)
                and arm["config"]["lane_receipt_sha256"] == digest(train_receipts[arm["lane_id"]])
                and raw(arm["config"]["native_profile"]) == raw(train_bundles[arm["lane_id"]]["profile"]), "source producer/training generation differs")
        checkpoints[key], checkpoint_bindings[key] = checkpoint, checkpoint_binding
    bootstrap = compiled_owner(plan["bootstrap_binding"], BOOTSTRAP_SHA, "frozen_native_site_bootstrap")
    providers = bootstrap["select_native_site"]()
    for name in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS"):
        os.environ[name] = "1"
    os.environ["CUDA_VISIBLE_DEVICES"] = ""
    import torch
    require(torch.__version__ == "2.13.0+cu130", "selected Torch runtime differs")
    torch.set_num_threads(1)
    torch.set_num_interop_threads(1)
    rng_before = torch.get_rng_state().clone()
    controls, train_values = {}, {}
    # All three TRAIN-only fits precede the first opening of any query bundle.
    with torch.inference_mode():
        for lane in LANES:
            train_values[lane] = torch.tensor([r["vector"] for r in train_bundles[lane]["rows"]], dtype=torch.float32)
            normalization = checkpoints[(lane, SEEDS[0])]["normalization"]
            require(all(checkpoints[(lane, seed)]["normalization"] == normalization for seed in SEEDS), "seed normalization reuse differs")
            mean = train_values[lane].mean(dim=0)
            rms = float(torch.sqrt(((train_values[lane] - mean) ** 2).mean()))
            require(mean.tolist() == normalization["mean"] and rms == normalization["rms"], "saved normalization was not exactly TRAIN-derived")
            controls[lane] = fit_pca_control(torch, train_values[lane], normalization, LANES[lane][2])
            require(controls[lane]["rank"] >= 1 and controls[lane]["threshold"] > 0, "nonconstant actual TRAIN control required")
    query_bundles, query_values = {}, {}
    for lane in LANES:
        selected = plan["lanes"][lane]
        query_bundles[lane] = read(selected["query_bundle_binding"])
        validate_bundle(query_bundles[lane], read(selected["query_expected_binding"]), owner, lane, "validation", cohort, train_bundles[lane]["profile"])
        query_values[lane] = torch.tensor([r["vector"] for r in query_bundles[lane]["rows"]], dtype=torch.float32)
    results = []
    for index, (arm, report) in enumerate(zip(manifest["arms"], reports, strict=True)):
        require(time.monotonic() - started < 90, "evaluation soft wall budget expired")
        lane, seed = arm["lane_id"], arm["seed"]
        key = (lane, seed)
        module, optimizer, checkpoint = helper["load_checkpoint"](torch, checkpoint_bindings[key], arm["config"])
        module.eval()
        before_model = helper["state_digest"](module)
        before_adam = helper["digest"]({k: v.tolist() for k, v in helper["optimizer_tensors"](torch, module, optimizer).items()})
        require(checkpoint["optimizer_steps"] == 200, "selected200 restore required")
        with torch.inference_mode():
            train_observed = helper["observations"](torch, module, train_values[lane], checkpoint["normalization"])
            require(raw(train_observed) == raw(report["final_observations"]), "published TRAIN outputs differ from original selected outputs")
            query_observed = helper["observations"](torch, module, query_values[lane], checkpoint["normalization"])
            views = []
            cohort_metrics = {}
            for split, values, bundle, observed in (("train", train_values[lane], train_bundles[lane], train_observed),
                                                    ("validation", query_values[lane], query_bundles[lane], query_observed)):
                pca_latent, pca_reconstructed, mean_reconstructed = project_pca_control(torch, controls[lane], values)
                reconstructed = torch.tensor(observed["reconstructed_vectors"], dtype=torch.float32)
                # Preserve exact producer JSON for the raw retrieval control.
                # Float32 conversion is only the numerical AE/PCA input contract.
                table = {"raw_source": [row["vector"] for row in bundle["rows"]], "latent": observed["latent_vectors"], "reconstructed": observed["reconstructed_vectors"],
                         "mean_reconstructed": mean_reconstructed.tolist(), "pca_reconstructed": pca_reconstructed.tolist(), "pca_latent": pca_latent.tolist()}
                for row_index, row in enumerate(bundle["rows"]):
                    meta = cohort[row["id"]]
                    views.append({"id": row["id"], "group_id": meta["group_id"], "split": split, "source_sha256": meta["source_sha256"],
                                  "panel_input_sha256": meta["input_sha256"], "lane_input_sha256": row["input_sha256"], "context_role": meta["context_role"],
                                  "endpoints": {name: rows[row_index] for name, rows in table.items()}})
                selected_indices = list(range(len(values))) if split == "train" else [i for i, r in enumerate(bundle["rows"]) if cohort[r["id"]]["context_role"] == "none_required"]
                cohort_metrics["train" if split == "train" else "validation_source_only"] = {
                    name: reconstruction_metrics(torch, values[selected_indices], prediction[selected_indices])
                    for name, prediction in (("raw_identity", values), ("reconstructed", reconstructed), ("mean_reconstructed", mean_reconstructed), ("pca_reconstructed", pca_reconstructed))}
        require(before_model == helper["state_digest"](module) and before_adam == helper["digest"]({k: v.tolist() for k, v in helper["optimizer_tensors"](torch, module, optimizer).items()}),
                "inference changed restored weights or Adam state")
        require(all(parameter.grad is None for parameter in module.parameters()), "inference produced parameter gradients")
        arm_directory = output / (lane + "-seed" + str(seed))
        arm_directory.mkdir(mode=0o700)
        model_reference = next(b for b in release_bindings if b["path"] == str(Path(checkpoint_bindings[key]["path"]).parent / "model.safetensors"))
        endpoint = {"schema": "source-reconstruction-evaluation-endpoints/v1", "lane_id": lane, "seed": seed, "architecture": list(LANES[lane]),
                    "source_profile_sha256": digest(train_bundles[lane]["profile"]), "checkpoint_binding": checkpoint_bindings[key], "model_file_binding": model_reference,
                    "training_report_binding": plan["training_report_bindings"][index], "native_train_bundle_binding": plan["lanes"][lane]["train_bundle_binding"],
                    "native_query_bundle_binding": plan["lanes"][lane]["query_bundle_binding"], "rows": views, "pca_control": pca_metadata(controls[lane]),
                    "model_inference_executed": True, "optimizer_updates": 0}
        endpoint_reference = write(arm_directory / "endpoints.json", endpoint)
        numeric = {"schema": "source-reconstruction-frozen-numeric-evaluation/v1", "lane_id": lane, "seed": seed, "architecture": list(LANES[lane]),
                   "endpoint_binding": endpoint_reference, "checkpoint_binding": checkpoint_bindings[key], "training_report_binding": plan["training_report_bindings"][index],
                   "cohorts": cohort_metrics, "context_dependent_query_rows_excluded": 2, "train_original_outputs_exact": True,
                   "pca_control": pca_metadata(controls[lane]), "restored_model_and_adam_preserved": True, "parameter_gradients_created": False,
                   "model_loads": 1, "encoder_forward_calls": 2, "decoder_forward_calls": 2, "optimizer_updates": 0,
                   "semantic_or_proof_authority_established": False, "source_vector_tables_included": False, "masks": dict.fromkeys(MASKS, 0)}
        numeric_reference = write(arm_directory / "numeric-report.json", numeric)
        results.append({"lane_id": lane, "seed": seed, "endpoint_binding": endpoint_reference, "numeric_report_binding": numeric_reference})
    require(torch.equal(rng_before, torch.get_rng_state()), "global CPU RNG changed")
    for bound in [reference, *release_bindings, plan["release_manifest_binding"], plan["run_plan_binding"], plan["helper_binding"], plan["bootstrap_binding"],
                  plan["lane_owner_binding"], plan["cohort_metadata_binding"], *plan["training_report_bindings"],
                  *(bound for selected in plan["lanes"].values() for bound in selected.values())]:
        require(binding(bound["path"]) == bound, "bound master/source bytes changed during evaluation")
    for provider in providers.values():
        bootstrap["checked_bytes"](Path(provider["path"]), provider["sha256"], provider["bytes"])
    return write(output / "evaluation-report.json", {"schema": "source-reconstruction-frozen-evaluation-batch/v1", "status": "completed_frozen_source_only_evaluation",
                 "evaluation_plan_binding": reference, "release_manifest_binding": plan["release_manifest_binding"], "arms": results, "successful_arms": 9,
                 "pca_control_fit_count": 3, "train_rows_per_fit": 16, "query_rows_read_before_all_control_fits": 0,
                 "model_loads": 9, "encoder_forward_calls": 18, "decoder_forward_calls": 18, "optimizer_updates": 0,
                 "encoder_backbone_calls": 0, "prover_calls": 0, "formal_target_bodies_read": False,
                 "all_original_train_outputs_exact": True, "all_master_and_source_files_preserved": True, "global_cpu_rng_preserved": True,
                 "torch_version": torch.__version__, "device": "cpu", "dtype": "float32", "cpu_threads": 1,
                 "wall_seconds": time.monotonic() - started, "worker_cpu_seconds": resource.getrusage(resource.RUSAGE_SELF).ru_utime + resource.getrusage(resource.RUSAGE_SELF).ru_stime,
                 "peak_rss_kib": resource.getrusage(resource.RUSAGE_SELF).ru_maxrss, "os_sandbox": False,
                 "source_fidelity_established": False, "proof_authority": False, "qualified": False, "masks": dict.fromkeys(MASKS, 0),
                 "scope": "historical_exposed_development_sources_not_pristine_holdout_or_semantic_accuracy"})


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--plan", required=True)
    parser.add_argument("--plan-sha256", required=True)
    parser.add_argument("--output-directory", required=True)
    args = parser.parse_args()
    reference = binding(Path(args.plan))
    require(reference["sha256"] == args.plan_sha256, "externally selected evaluation plan differs")
    print(json.dumps(run(reference, args.output_directory), sort_keys=True))


if __name__ == "__main__":
    main()
