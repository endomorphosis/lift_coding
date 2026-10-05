"""Compare old and expanded AEs on exposed authored TRAIN32/DEV32 sources.

No formal references are accepted. Controls fit only expanded TRAIN vectors,
before any DEV vector file is opened. Neighborhood agreement measures the raw
encoder's neighborhoods, without making a claim about semantic relevance.
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
from collections import Counter
from pathlib import Path

MAX_BYTES = 32 * 1024**2
BOOTSTRAP_SHA = "910ff61a235d6e988e78b34a3b27d7ae7520f2bb10722881ab532c934be1199e"
OLD_HELPER_SHA = "387c0335549374a98e1d5458d9746733fe385dd760584fdf059f6266c44873d3"
NEW_HELPER_SHA = "9d5dca6c6a07d60956eb9da3c874b9df65e8cd8ad965ed16090bbc70738c1182"
CONTROL_OWNER_SHA = "0c65247d19430dec78395fe591c60994b2a4b9ec054d8c20c10b067ede994c44"
LANE_OWNER_SHA = "d7d2e1303e15d46b70997e5880df6fb9a690bfebde63666cad04db516f3ef3a8"
OLD_MANIFEST_SHA = "30e2fe3b112f60fd7f8d9494f88caaba674efdc8424a3c174a0e34570282cbf5"
LANES = {"legacy8": (8, 16, 4), "native384": (384, 128, 32), "native768": (768, 128, 64)}
SEEDS = (1729, 1730, 1731)
MASKS = ("weak_decoder_fit", "strong_semantic_fit", "contrastive_supervision", "proof_supervision", "fidelity_evaluation")
VIEWS = ("raw_source", "new_latent", "new_reconstructed", "old_latent", "old_reconstructed",
         "mean_reconstructed", "pca_latent", "pca_reconstructed")
SOURCE_POLICY = {"scope": "exposed_authored_composition_source_reconstruction_only",
    "source_reconstruction_fit_authorized": True, "semantic_masks": dict.fromkeys(MASKS, 0),
    "semantic_label_admission": False, "independent_semantic_review_completed": False,
    "source_fidelity_established": False, "natural_sources": False, "pristine_holdout": False,
    "reused_exposed_components": True, "formal_targets_read": False, "proof_authority": False, "qualified": False}


def require(value, message):
    if not value:
        raise ValueError(message)


def raw(value):
    return json.dumps(value, sort_keys=True, ensure_ascii=False, separators=(",", ":"),
                      allow_nan=False).encode("utf-8")


def digest(value):
    return hashlib.sha256(raw(value)).hexdigest()


def closed(value, keys, label):
    require(type(value) is dict and set(value) == set(keys), "closed " + label + " required")


def sha(value):
    require(type(value) is str and len(value) == 64 and
            all(c in "0123456789abcdef" for c in value), "lowercase SHA256 required")


def binding(path):
    path = Path(path)
    require(path.is_absolute() and path.is_file() and
            not any(p.is_symlink() for p in (path, *path.parents)), "absolute nonsymlink file required")
    before = path.stat()
    require(0 < before.st_size <= MAX_BYTES, "bounded nonempty file required")
    data = path.read_bytes()
    after = path.stat()
    require((before.st_dev, before.st_ino, before.st_size, before.st_mtime_ns) ==
            (after.st_dev, after.st_ino, after.st_size, after.st_mtime_ns), "file changed during read")
    return dict(path=str(path), bytes=len(data), sha256=hashlib.sha256(data).hexdigest())


def captured(reference):
    closed(reference, {"path", "bytes", "sha256"}, "file binding")
    sha(reference["sha256"])
    require(binding(reference["path"]) == reference, "external file pin differs")
    data = Path(reference["path"]).read_bytes()
    require(len(data) == reference["bytes"] and hashlib.sha256(data).hexdigest() == reference["sha256"],
            "captured file pin differs")
    return data


def read(reference):
    def pairs(items):
        result = {}
        for key, value in items:
            require(key not in result, "duplicate JSON key")
            result[key] = value
        return result
    return json.loads(captured(reference).decode("utf-8"), object_pairs_hook=pairs,
                      parse_constant=lambda _: (_ for _ in ()).throw(ValueError("nonfinite JSON")))


def seal_check(value):
    require(type(value) is dict and value.get("content_sha256") == digest(
        {k: v for k, v in value.items() if k != "content_sha256"}), "JSON seal differs")


def compiled_owner(reference, expected_sha, name):
    require(reference["sha256"] == expected_sha, "selected implementation generation differs")
    data = captured(reference)
    namespace = {"__name__": name, "__file__": reference["path"]}
    exec(compile(data, reference["path"], "exec"), namespace)
    return namespace


def write(path, value):
    data = json.dumps({**value, "content_sha256": digest(value)}, sort_keys=True, indent=2,
                      ensure_ascii=False, allow_nan=False).encode("utf-8") + b"\n"
    require(len(data) <= MAX_BYTES, "bounded output required")
    with path.open("xb") as stream:
        os.chmod(path, 0o600)
        stream.write(data)
        stream.flush()
        os.fsync(stream.fileno())
    return binding(path)


def validate_cohort(value, selection):
    closed(value, {"schema", "rows", "contains_formal_targets", "policy", "content_sha256"}, "source cohort")
    seal_check(value)
    require(value["schema"] == "source-only-authored-expansion-cohort/v1" and
            value["contains_formal_targets"] is False and raw(value["policy"]) == raw(SOURCE_POLICY),
            "exposed source-only policy differs")
    require(type(value["rows"]) is list and len(value["rows"]) == 64, "complete64 source cohort required")
    indexed = {}
    for row in value["rows"]:
        closed(row, {"id", "split", "group_id", "source_sha256", "input_sha256", "context_role"}, "source row")
        sha(row["source_sha256"])
        sha(row["input_sha256"])
        require(row["id"] == "sha256:" + row["input_sha256"] and row["id"] not in indexed and
                row["split"] in {"train", "development"} and row["context_role"] == "none_required" and
                type(row["group_id"]) is str and row["group_id"], "source identity/split/context differs")
        indexed[row["id"]] = row
    train = [r for r in value["rows"] if r["split"] == "train"]
    dev = [r for r in value["rows"] if r["split"] == "development"]
    require(len(train) == len(dev) == 32, "fixed TRAIN32/DEV32 required")
    for rows in (train, dev):
        counts = Counter(r["group_id"] for r in rows)
        require(len(counts) == 8 and set(counts.values()) == {4}, "eight four-variant groups required")
    for key in ("id", "source_sha256", "input_sha256", "group_id"):
        require(not ({r[key] for r in train} & {r[key] for r in dev}), "TRAIN/DEV " + key + " overlap")
    expected = [{k: r[k] for k in ("id", "group_id", "source_sha256", "split")}
                | {"original_masks": dict.fromkeys(MASKS, 0)} for r in train]
    require(raw(selection) == raw(expected), "ordered TRAIN selection or zero masks differs")
    return indexed


def validate_bundle(bundle, expected, lane_owner, lane, split, cohort, profile=None):
    receipt = lane_owner["validate_lane_bundle"](bundle, expected_bindings=expected)
    require(receipt["lane_id"] == lane and receipt["dimension"] == LANES[lane][0] and
            receipt["available_count"] == receipt["row_count"] == 32, "complete native32 rows required")
    ids = [r["id"] for r in cohort.values() if r["split"] == split]
    require([r["id"] for r in bundle["rows"]] == ids, "ordered native source identities differ")
    if profile is not None:
        require(raw(bundle["profile"]) == raw(profile), "full original native profile differs")
    for row in bundle["rows"]:
        meta = cohort[row["id"]]
        require(meta["source_sha256"] == hashlib.sha256(row["input"]["source_text"].encode("utf-8")).hexdigest()
                and meta["input_sha256"] == row["input_sha256"] == digest(row["input"])
                and row["input"]["context"]["role"] == "none_required", "native source/context join differs")
    return receipt


def pca_metadata(control):
    require(type(control["rank"]) is int and 1 <= control["rank"] <= 31 and
            type(control["retained"]) is int and 1 <= control["retained"] <= control["rank"] and
            math.isfinite(control["threshold"]) and control["threshold"] > 0, "TRAIN32 PCA rank differs")
    return dict(effective_train_rank=control["rank"], retained_axes=control["retained"],
                threshold=control["threshold"], basis_sha256=digest(control["basis"].tolist()),
                fit_rows=32, development_rows_read_before_fit=0, recipe="TRAIN_centered_SVD/v1")


def cosine_ranking(query, bank):
    """Full fixed bank, deterministic score/ID order; zero vectors are unavailable."""
    require(type(query) is list and query and all(type(x) in (int, float) and math.isfinite(x) for x in query),
            "finite nonempty query vector required")
    require(type(bank) is list and bank and len({row[0] for row in bank}) == len(bank), "unique fixed bank required")
    qnorm = math.sqrt(math.fsum(x * x for x in query))
    scores = []
    for item_id, vector in bank:
        require(type(item_id) is str and type(vector) is list and len(vector) == len(query) and
                all(type(x) in (int, float) and math.isfinite(x) for x in vector), "matched finite bank width required")
        norm = math.sqrt(math.fsum(x * x for x in vector))
        if qnorm == 0 or norm == 0:
            return None
        score = math.fsum(a * b for a, b in zip(query, vector, strict=True)) / (qnorm * norm)
        require(math.isfinite(score), "finite cosine required")
        scores.append((item_id, max(-1., min(1., score))))
    return [item_id for item_id, _ in sorted(scores, key=lambda row: (-row[1], row[0]))]


def neighborhood_agreement(rows):
    train = [r for r in rows if r["split"] == "train"]
    dev = [r for r in rows if r["split"] == "development"]
    require(len(train) == len(dev) == 32 and len({r["id"] for r in rows}) == 64,
            "fixed32 TRAIN bank and32 DEV queries required")
    for key in ("id", "group_id", "source_sha256", "panel_input_sha256"):
        require(not ({r[key] for r in train} & {r[key] for r in dev}), "neighborhood split overlap")
    require(all(set(r["endpoints"]) == set(VIEWS) for r in rows), "all eight endpoint views required")
    banks = {view: [(r["id"], r["endpoints"][view]) for r in train] for view in VIEWS}
    results = {view: [] for view in VIEWS}
    for query in dev:
        baseline = cosine_ranking(query["endpoints"]["raw_source"], banks["raw_source"])
        require(baseline is not None, "raw source neighborhood must be defined")
        for view in VIEWS:
            ranked = cosine_ranking(query["endpoints"][view], banks[view])
            if ranked is not None:
                results[view].append((int(ranked[0] == baseline[0]), len(set(ranked[:5]) & set(baseline[:5])) / 5.))
    return {view: dict(fixed_train_candidates=32, development_queries=32, fully_defined_queries=len(values),
        undefined_queries=32 - len(values), mean_top1_agreement_with_raw=math.fsum(v[0] for v in values) / len(values) if values else None,
        mean_top5_set_overlap_fraction_with_raw=math.fsum(v[1] for v in values) / len(values) if values else None,
        source_neighborhood_measure_only=True, semantic_relevance_measured=False,
        tie_rule="descending_cosine_then_lexicographic_id") for view, values in results.items()}


def checkpoint_file_bindings(checkpoint_reference, checkpoint):
    result = []
    for key, filename in (("model_file", "model.safetensors"), ("optimizer_file", "optimizer.safetensors")):
        closed(checkpoint[key], {"path", "bytes", "sha256"}, "tensor file declaration")
        require(checkpoint[key]["path"] == filename, "fixed checkpoint-local filename required")
        selected = {**checkpoint[key], "path": str(Path(checkpoint_reference["path"]).parent / filename)}
        require(binding(selected["path"]) == selected, "selected tensor bytes differ")
        result.append(selected)
    return result


def check_plan(plan):
    closed(plan, {"schema", "helper_binding", "bootstrap_binding", "lane_owner_binding", "cohort_binding",
        "new_training_plan_binding", "new_training_report_bindings", "old_release_manifest_binding",
        "old_helper_binding", "new_helper_binding", "numeric_control_owner_binding", "lanes",
        "authorization_scope", "content_sha256"}, "expanded evaluation plan")
    seal_check(plan)
    require(plan["schema"] == "source-only-expanded-numeric-evaluation-plan/v1" and
            plan["authorization_scope"] == "source_only_expanded_frozen_evaluation_no_semantic_admission",
            "source-only frozen evaluation scope differs")
    require(binding(Path(__file__).absolute()) == plan["helper_binding"], "worker implementation differs")
    for key, expected in (("bootstrap_binding", BOOTSTRAP_SHA), ("lane_owner_binding", LANE_OWNER_SHA),
                          ("old_helper_binding", OLD_HELPER_SHA), ("new_helper_binding", NEW_HELPER_SHA),
                          ("numeric_control_owner_binding", CONTROL_OWNER_SHA),
                          ("old_release_manifest_binding", OLD_MANIFEST_SHA)):
        require(plan[key]["sha256"] == expected, "pinned generation differs: " + key)
    require(type(plan["new_training_report_bindings"]) is list and len(plan["new_training_report_bindings"]) == 9,
            "complete nine new training reports required")
    closed(plan["lanes"], set(LANES), "complete native lanes")
    for lane in LANES:
        closed(plan["lanes"][lane], {"train_bundle_binding", "train_expected_binding",
                                   "development_bundle_binding", "development_expected_binding"}, "native lane selection")


def run(reference, output):
    require(sys.flags.isolated and sys.dont_write_bytecode, "selected native interpreter -I -B required")
    plan = read(reference)
    check_plan(plan)
    output = Path(output)
    require(output.is_absolute() and output.parent.is_dir() and not output.exists() and
            not any(p.is_symlink() for p in (output, *output.parents)), "fresh absolute output required")
    output.mkdir(mode=0o700)
    resource.setrlimit(resource.RLIMIT_CPU, (90, 100))
    resource.setrlimit(resource.RLIMIT_AS, (8 * 1024**3, 8 * 1024**3))
    resource.setrlimit(resource.RLIMIT_FSIZE, (32 * 1024**2, 32 * 1024**2))
    started = time.monotonic()
    controls_owner = compiled_owner(plan["numeric_control_owner_binding"], CONTROL_OWNER_SHA, "frozen_numeric_control_owner")
    old_helper = compiled_owner(plan["old_helper_binding"], OLD_HELPER_SHA, "old_reconstruction_owner")
    new_helper = compiled_owner(plan["new_helper_binding"], NEW_HELPER_SHA, "expanded_reconstruction_owner")
    lane_owner = compiled_owner(plan["lane_owner_binding"], LANE_OWNER_SHA, "native_lane_owner")
    training_plan = read(plan["new_training_plan_binding"])
    seal_check(training_plan)
    require(training_plan["schema"] == "source-vector-expanded-reconstruction-run-plan/v1" and
            training_plan["helper_binding"] == plan["new_helper_binding"] and
            training_plan["cohort_binding"] == plan["cohort_binding"] and
            training_plan["bootstrap_binding"] == plan["bootstrap_binding"] and
            training_plan["lane_owner_binding"] == plan["lane_owner_binding"], "new training generation differs")
    cohort = validate_cohort(read(plan["cohort_binding"]), training_plan["train_selection"])
    manifest = read(plan["old_release_manifest_binding"])
    seal_check(manifest)
    require(manifest["schema"] == "source-vector-reconstruction-public-release/v1", "old release schema differs")
    release = Path(plan["old_release_manifest_binding"]["path"]).parent
    release_bindings = []
    for item in manifest["files"]:
        closed(item, {"path", "bytes", "sha256"}, "old release file")
        require(type(item["path"]) is str and not Path(item["path"]).is_absolute() and
                ".." not in Path(item["path"]).parts, "release-local path required")
        selected = {**item, "path": str(release / item["path"])}
        require(binding(selected["path"]) == selected, "downloaded release file differs")
        release_bindings.append(selected)
    require(plan["old_helper_binding"] in release_bindings, "old helper must come from pinned downloaded release")
    arms = [(lane, seed) for lane in LANES for seed in SEEDS]
    require([(a["lane_id"], a["seed"]) for a in manifest["arms"]] == arms, "ordered nine old arms differ")
    reports = [read(r) for r in plan["new_training_report_bindings"]]
    require([(r["lane_id"], r["seed"]) for r in reports] == arms, "ordered nine new arms differ")
    train_bundles, train_receipts, new_checkpoints, old_checkpoints, watched = {}, {}, {}, {}, []
    for lane in LANES:
        selected = plan["lanes"][lane]
        require(selected["train_bundle_binding"] == training_plan["lanes"][lane]["bundle_binding"] and
                selected["train_expected_binding"] == training_plan["lanes"][lane]["expected_lane_binding"],
                "new TRAIN vector generation differs")
        train_bundles[lane] = read(selected["train_bundle_binding"])
        train_receipts[lane] = validate_bundle(train_bundles[lane], read(selected["train_expected_binding"]),
                                              lane_owner, lane, "train", cohort)
    for report, old_arm in zip(reports, manifest["arms"], strict=True):
        seal_check(report)
        require(report["schema"] == "source-vector-reconstruction-training-report/v1" and
                report["status"] == "completed_fixed_budget_reconstruction_only" and
                report["training_rows"] == 32 and report["query_or_dev_rows_read"] == 0 and
                report["selected_optimizer_updates"] == 200 and report["actual_total_optimizer_updates"] == 203 and
                report["masks"] == dict.fromkeys(MASKS, 0) and
                all(type(v) is int for v in report["masks"].values()) and
                all(report[k] is False for k in ("semantic_fit_authorized", "contrastive_fit_authorized",
                    "source_fidelity_established", "proof_authority", "qualified", "formal_target_bodies_read")),
                "new training authority/scope differs")
        key = (report["lane_id"], report["seed"])
        lane = key[0]
        new_ref = report["selected_checkpoint"]
        new_checkpoint = read(new_ref)
        seal_check(new_checkpoint)
        require(new_checkpoint["optimizer_steps"] == 200 and
                raw(new_checkpoint["config"]) == raw(report["config"]) and
                new_checkpoint["normalization"] == report["normalization"], "new selected model generation differs")
        config = report["config"]
        require(config["plan_sha256"] == digest(training_plan) and
                config["helper_binding"] == plan["new_helper_binding"] and
                config["lane_receipt_sha256"] == digest(train_receipts[lane]) and
                config["bundle_binding"] == plan["lanes"][lane]["train_bundle_binding"] and
                raw(config["native_profile"]) == raw(train_bundles[lane]["profile"]) and
                config["training_ids"] == [row["id"] for row in train_bundles[lane]["rows"]] and
                config["input_sha256s"] == [row["input_sha256"] for row in train_bundles[lane]["rows"]],
                "new model/native TRAIN profile differs")
        old_ref = next((r for r in release_bindings if r["path"] == str(release / old_arm["checkpoint_path"])), None)
        require(old_ref is not None, "old selected checkpoint absent")
        old_checkpoint = read(old_ref)
        seal_check(old_checkpoint)
        require(old_checkpoint["optimizer_steps"] == 200 and
                raw(old_checkpoint["config"]) == raw(old_arm["config"]) and
                raw(old_arm["config"]["native_profile"]) == raw(train_bundles[lane]["profile"]) and
                not set(old_arm["config"]["training_ids"]) & set(cohort), "old profile/source identity overlap differs")
        new_checkpoints[key] = (new_ref, new_checkpoint)
        old_checkpoints[key] = (old_ref, old_checkpoint)
        watched.extend([new_ref, *checkpoint_file_bindings(new_ref, new_checkpoint),
                        old_ref, *checkpoint_file_bindings(old_ref, old_checkpoint)])
    bootstrap = compiled_owner(plan["bootstrap_binding"], BOOTSTRAP_SHA, "pinned_native_bootstrap")
    providers = bootstrap["select_native_site"]()
    for name in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS"):
        os.environ[name] = "1"
    os.environ["CUDA_VISIBLE_DEVICES"] = ""
    import torch
    require(torch.__version__ == "2.13.0+cu130", "selected numerical runtime differs")
    torch.set_num_threads(1)
    torch.set_num_interop_threads(1)
    rng_before = torch.get_rng_state().clone()
    train_values, controls = {}, {}
    # No DEV binding has been opened or hashed before all three TRAIN fits.
    with torch.inference_mode():
        for lane in LANES:
            train_values[lane] = torch.tensor([r["vector"] for r in train_bundles[lane]["rows"]], dtype=torch.float32)
            norm = new_checkpoints[(lane, SEEDS[0])][1]["normalization"]
            require(all(new_checkpoints[(lane, seed)][1]["normalization"] == norm for seed in SEEDS),
                    "seed TRAIN normalization differs")
            mean = train_values[lane].mean(dim=0)
            rms = float(torch.sqrt(((train_values[lane] - mean) ** 2).mean()))
            require(mean.tolist() == norm["mean"] and rms == norm["rms"], "new normalization is not exactly TRAIN-derived")
            controls[lane] = controls_owner["fit_pca_control"](torch, train_values[lane], norm, LANES[lane][2])
            pca_metadata(controls[lane])
    dev_bundles, dev_values = {}, {}
    for lane in LANES:
        selected = plan["lanes"][lane]
        dev_bundles[lane] = read(selected["development_bundle_binding"])
        validate_bundle(dev_bundles[lane], read(selected["development_expected_binding"]), lane_owner,
                        lane, "development", cohort, train_bundles[lane]["profile"])
        dev_values[lane] = torch.tensor([r["vector"] for r in dev_bundles[lane]["rows"]], dtype=torch.float32)
    results = []
    for index, (lane, seed) in enumerate(arms):
        require(time.monotonic() - started < 90, "evaluation soft wall budget expired")
        new_ref, new_checkpoint = new_checkpoints[(lane, seed)]
        old_ref, old_checkpoint = old_checkpoints[(lane, seed)]
        models = {}
        for generation, helper, checkpoint_ref, checkpoint in (("new", new_helper, new_ref, new_checkpoint),
                                                              ("old", old_helper, old_ref, old_checkpoint)):
            module, optimizer, loaded = helper["load_checkpoint"](torch, checkpoint_ref, checkpoint["config"])
            module.eval()
            require(raw(loaded) == raw(checkpoint), "loaded checkpoint metadata differs")
            models[generation] = dict(module=module, optimizer=optimizer, helper=helper,
                model_before=helper["state_digest"](module),
                adam_before=digest({k: v.tolist() for k, v in helper["optimizer_tensors"](torch, module, optimizer).items()}))
        views, metrics = [], {}
        with torch.inference_mode():
            for split, values, bundle in (("train", train_values[lane], train_bundles[lane]),
                                          ("development", dev_values[lane], dev_bundles[lane])):
                observed = {generation: state["helper"]["observations"](torch, state["module"], values,
                    (new_checkpoint if generation == "new" else old_checkpoint)["normalization"])
                    for generation, state in models.items()}
                if split == "train":
                    require(raw(observed["new"]) == raw(reports[index]["final_observations"]),
                            "new restored TRAIN outputs differ from saved selected outputs")
                pca_latent, pca_reconstructed, mean_reconstructed = controls_owner["project_pca_control"](torch, controls[lane], values)
                table = dict(raw_source=[row["vector"] for row in bundle["rows"]],
                    new_latent=observed["new"]["latent_vectors"], new_reconstructed=observed["new"]["reconstructed_vectors"],
                    old_latent=observed["old"]["latent_vectors"], old_reconstructed=observed["old"]["reconstructed_vectors"],
                    mean_reconstructed=mean_reconstructed.tolist(), pca_latent=pca_latent.tolist(),
                    pca_reconstructed=pca_reconstructed.tolist())
                for row_index, row in enumerate(bundle["rows"]):
                    meta = cohort[row["id"]]
                    views.append(dict(id=row["id"], group_id=meta["group_id"], split=split,
                        source_sha256=meta["source_sha256"], panel_input_sha256=meta["input_sha256"],
                        lane_input_sha256=row["input_sha256"], context_role=meta["context_role"],
                        endpoints={name: vector_rows[row_index] for name, vector_rows in table.items()}))
                predictions = dict(raw_identity=values,
                    new_reconstructed=torch.tensor(table["new_reconstructed"], dtype=torch.float32),
                    old_reconstructed=torch.tensor(table["old_reconstructed"], dtype=torch.float32),
                    mean_reconstructed=mean_reconstructed, pca_reconstructed=pca_reconstructed)
                metrics[split] = {name: controls_owner["reconstruction_metrics"](torch, values, prediction)
                                  for name, prediction in predictions.items()}
        for state in models.values():
            helper, module, optimizer = state["helper"], state["module"], state["optimizer"]
            require(state["model_before"] == helper["state_digest"](module) and state["adam_before"] ==
                    digest({k: v.tolist() for k, v in helper["optimizer_tensors"](torch, module, optimizer).items()}),
                    "inference changed model or Adam state")
            require(all(parameter.grad is None for parameter in module.parameters()), "inference created parameter gradients")
        neighborhood = neighborhood_agreement(views)
        directory = output / (lane + "-seed" + str(seed))
        directory.mkdir(mode=0o700)
        endpoint_ref = write(directory / "endpoints.json", dict(
            schema="source-only-expanded-reconstruction-endpoints/v1", lane_id=lane, seed=seed,
            architecture=list(LANES[lane]), source_profile_sha256=digest(train_bundles[lane]["profile"]),
            new_checkpoint_binding=new_ref, old_checkpoint_binding=old_ref,
            new_training_report_binding=plan["new_training_report_bindings"][index],
            native_train_bundle_binding=plan["lanes"][lane]["train_bundle_binding"],
            native_development_bundle_binding=plan["lanes"][lane]["development_bundle_binding"],
            rows=views, pca_control=pca_metadata(controls[lane]), model_inference_executed=True,
            optimizer_updates=0, semantic_relevance_measured=False))
        numeric_ref = write(directory / "numeric-report.json", dict(
            schema="source-only-expanded-reconstruction-numeric-report/v1", lane_id=lane, seed=seed,
            architecture=list(LANES[lane]), endpoint_binding=endpoint_ref,
            new_checkpoint_binding=new_ref, old_checkpoint_binding=old_ref,
            new_training_report_binding=plan["new_training_report_bindings"][index],
            cohorts=metrics, source_neighborhood_agreement=neighborhood,
            pca_control=pca_metadata(controls[lane]), new_train_original_outputs_exact=True,
            old_normalization_retained=True, new_normalization_exact_train_only=True,
            restored_models_and_adam_preserved=True, parameter_gradients_created=False,
            model_loads=2, encoder_forward_calls=4, decoder_forward_calls=4, optimizer_updates=0,
            source_vector_tables_included=False, masks=dict.fromkeys(MASKS, 0),
            semantic_relevance_measured=False, independent_semantic_accuracy_measured=False,
            source_fidelity_established=False, proof_authority=False, qualified=False))
        results.append(dict(lane_id=lane, seed=seed, endpoint_binding=endpoint_ref, numeric_report_binding=numeric_ref))
    require(torch.equal(rng_before, torch.get_rng_state()), "global CPU RNG changed")
    watched.extend([reference, *release_bindings, plan["old_release_manifest_binding"], plan["helper_binding"],
        plan["bootstrap_binding"], plan["lane_owner_binding"], plan["cohort_binding"], plan["new_training_plan_binding"],
        plan["new_helper_binding"], plan["old_helper_binding"], plan["numeric_control_owner_binding"],
        *plan["new_training_report_bindings"], *(ref for lane in plan["lanes"].values() for ref in lane.values())])
    for selected in watched:
        require(binding(selected["path"]) == selected, "bound checkpoint/master/source bytes changed")
    for provider in providers.values():
        bootstrap["checked_bytes"](Path(provider["path"]), provider["sha256"], provider["bytes"])
    return write(output / "evaluation-report.json", dict(
        schema="source-only-expanded-reconstruction-evaluation-batch/v1", status="completed_frozen_source_only_evaluation",
        evaluation_plan_binding=reference, arms=results, successful_arms=9, model_loads=18,
        pca_control_fit_count=3, mean_control_fit_count=3, train_rows_per_fit=32,
        development_rows_read_before_all_control_fits=0, development_rows_per_arm=32,
        encoder_forward_calls=36, decoder_forward_calls=36, optimizer_updates=0,
        encoder_backbone_calls=0, network_calls=0, prover_calls=0, formal_target_bodies_read=False,
        all_new_train_outputs_exact=True, all_restored_models_and_adam_preserved=True,
        all_master_and_source_files_preserved=True, global_cpu_rng_preserved=True,
        masks=dict.fromkeys(MASKS, 0), independent_reviews_created=0, semantic_labels_admitted=0,
        independent_semantic_accuracy_measured=False, semantic_relevance_measured=False,
        source_fidelity_established=False, proof_authority=False, qualified=False,
        torch_version=torch.__version__, device="cpu", dtype="float32", cpu_threads=1,
        wall_seconds=time.monotonic() - started,
        worker_cpu_seconds=resource.getrusage(resource.RUSAGE_SELF).ru_utime + resource.getrusage(resource.RUSAGE_SELF).ru_stime,
        peak_rss_kib=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss, os_sandbox=False,
        scope="exposed_authored_compositions_reusing_exposed_components_not_pristine_holdout_or_broad_family_study",
        producer_neighborhoods_are_not_semantic_gold=True, best_development_seed_selected=False))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--plan", required=True)
    parser.add_argument("--plan-sha256", required=True)
    parser.add_argument("--output-directory", required=True)
    args = parser.parse_args()
    reference = binding(Path(args.plan))
    require(reference["sha256"] == args.plan_sha256, "external plan digest differs")
    print(json.dumps(run(reference, args.output_directory), sort_keys=True))


if __name__ == "__main__":
    main()
