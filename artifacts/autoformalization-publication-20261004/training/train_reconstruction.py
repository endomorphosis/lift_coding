"""Isolated native-vector reconstruction; no semantic or contrastive labels.

Each arm fits the exact selected TRAIN16 vectors, saves 0/100/200 steps,
restores Adam at100, and performs a separately counted private two-step replay.
No query files, formal targets, encoders, parser, prover or old models are read.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import random
import resource
import sys
import time
import types
from pathlib import Path

SCHEMA = "source-vector-reconstruction-checkpoint/v1"
MAX_BYTES = 32 * 1024 * 1024
LANES = {"legacy8": (8, 16, 4), "native384": (384, 128, 32), "native768": (768, 128, 64)}
MASKS = ("weak_decoder_fit", "strong_semantic_fit", "contrastive_supervision", "proof_supervision", "fidelity_evaluation")


def require(condition, message):
    if not condition:
        raise ValueError(message)


def raw(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False).encode("utf-8")


def digest(value):
    return hashlib.sha256(raw(value)).hexdigest()


def sealed(value):
    value["content_sha256"] = digest({key: item for key, item in value.items() if key != "content_sha256"})
    return value


def closed(value, fields, label):
    require(type(value) is dict and set(value) == set(fields), "closed " + label + " required")


def sha(value):
    require(type(value) is str and len(value) == 64 and all(c in "0123456789abcdef" for c in value), "lowercase SHA256 required")


def binding(path):
    path = Path(path).absolute()
    require(all(not parent.is_symlink() for parent in (path, *path.parents)) and path.is_file(), "regular nonsymlink input required")
    require(0 < path.stat().st_size <= MAX_BYTES, "bounded nonempty file required")
    data = path.read_bytes()
    return {"path": str(path), "sha256": hashlib.sha256(data).hexdigest(), "bytes": len(data)}


def read_bound(reference):
    closed(reference, {"path", "sha256", "bytes"}, "file binding")
    sha(reference["sha256"])
    require(type(reference["bytes"]) is int and 0 < reference["bytes"] <= MAX_BYTES, "bounded file bytes required")
    path = Path(reference["path"])
    require(path.is_absolute() and all(not parent.is_symlink() for parent in (path, *path.parents)), "absolute nonsymlink path required")
    before = path.stat()
    require(path.is_file() and before.st_size == reference["bytes"], "regular file byte size differs")
    data = path.read_bytes()
    after = path.stat()
    require((before.st_dev, before.st_ino, before.st_size, before.st_mtime_ns) ==
            (after.st_dev, after.st_ino, after.st_size, after.st_mtime_ns), "input changed during read")
    require(len(data) == reference["bytes"] and hashlib.sha256(data).hexdigest() == reference["sha256"], "file SHA differs")

    def pairs(items):
        result = {}
        for key, value in items:
            require(key not in result, "duplicate JSON key")
            result[key] = value
        return result

    value = json.loads(data.decode("utf-8"), object_pairs_hook=pairs,
                       parse_constant=lambda _: (_ for _ in ()).throw(ValueError("nonfinite JSON")))
    require(len(raw(value)) <= MAX_BYTES, "bounded JSON required")
    return value


def write_json(path, value):
    data = json.dumps(value, sort_keys=True, indent=2, ensure_ascii=False, allow_nan=False).encode("utf-8") + b"\n"
    require(len(data) <= MAX_BYTES, "output JSON byte bound")
    with Path(path).open("xb") as stream:
        os.chmod(path, 0o600)
        stream.write(data)
        stream.flush()
        os.fsync(stream.fileno())
    return binding(path)


def lane_owner(repo):
    for name, relative in (("ipfs_datasets_py", "ipfs_datasets_py"), ("ipfs_datasets_py.logic", "ipfs_datasets_py/logic"),
        ("ipfs_datasets_py.logic.formalization", "ipfs_datasets_py/logic/formalization"),
        ("ipfs_datasets_py.logic.formalization.autoencoder", "ipfs_datasets_py/logic/formalization/autoencoder")):
        if name not in sys.modules:
            module = types.ModuleType(name)
            module.__path__ = [str(Path(repo) / relative)]
            module.__package__ = name
            sys.modules[name] = module
    from ipfs_datasets_py.logic.formalization.autoencoder import alignment_lane_bundle
    return alignment_lane_bundle


def preflight(plan, lane_id, seed):
    closed(plan, {"schema", "repo", "helper_binding", "lane_owner_binding", "train_selection", "seeds", "config", "lanes",
                  "authorization_scope", "content_sha256"}, "reconstruction plan")
    require(plan["schema"] == "source-vector-reconstruction-run-plan/v1", "plan schema differs")
    require(plan["content_sha256"] == digest({k: v for k, v in plan.items() if k != "content_sha256"}), "plan seal differs")
    require(lane_id in LANES and type(seed) is int and seed in plan["seeds"] == [1729, 1730, 1731], "selected lane/seed differs")
    require(plan["authorization_scope"] == "user_authorized_source_vector_reconstruction_only_no_semantic_mask_promotion", "fit policy differs")
    closed(plan["config"], {"steps", "midpoint", "learning_rate", "batch_size", "dtype", "device", "cpu_threads",
        "normalization", "gradient_clip", "private_resume_comparison_updates"}, "fixed fit config")
    require(plan["config"] == {"steps": 200, "midpoint": 100, "learning_rate": .003, "batch_size": 8, "dtype": "float32",
        "device": "cpu", "cpu_threads": 1, "normalization": "train_coordinate_mean_and_global_rms/v1",
        "gradient_clip": 5., "private_resume_comparison_updates": 3}, "predeclared fit config differs")
    require(binding(__file__) == plan["helper_binding"], "helper source pin differs")
    require(binding(plan["lane_owner_binding"]["path"]) == plan["lane_owner_binding"], "lane owner source pin differs")
    owner = lane_owner(plan["repo"])
    selected = plan["lanes"][lane_id]
    closed(selected, {"architecture", "bundle_binding", "expected_lane_binding"}, "selected lane")
    require(selected["architecture"] == list(LANES[lane_id]), "native architecture differs")
    bundle, expected = read_bound(selected["bundle_binding"]), read_bound(selected["expected_lane_binding"])
    receipt = owner.validate_lane_bundle(bundle, expected_bindings=expected)
    require(receipt["lane_id"] == lane_id and receipt["dimension"] == LANES[lane_id][0], "native lane width differs")
    selection = plan["train_selection"]
    require(type(selection) is list and len(selection) == 16, "exact TRAIN16 required")
    require(len({row["id"] for row in selection}) == 16, "duplicate TRAIN identity")
    require(len(bundle["rows"]) == 16, "complete TRAIN16 bundle required")
    require([row["id"] for row in bundle["rows"]] == [row["id"] for row in selection], "ordered TRAIN IDs differ")
    indexed = {row["id"]: row for row in selection}
    for row in bundle["rows"]:
        meta = indexed[row["id"]]
        closed(meta, {"id", "group_id", "source_sha256", "split", "original_masks"}, "TRAIN selection")
        require(meta["split"] == "train" and type(meta["group_id"]) is str and meta["group_id"], "TRAIN/group scope required")
        require(meta["original_masks"] == {**dict.fromkeys(MASKS, 0), "weak_decoder_fit": 1}
                and all(type(meta["original_masks"][key]) is int for key in MASKS), "original weak masks differ")
        require(row["status"] == "available" and row["input"]["context"]["role"] == "none_required", "unavailable/context-training row rejected")
        require(hashlib.sha256(row["input"]["source_text"].encode("utf-8")).hexdigest() == meta["source_sha256"], "TRAIN source SHA differs")
    require(len({row["group_id"] for row in selection}) == 4, "original four TRAIN groups required")
    return bundle, receipt


def model(torch, dimension, hidden, latent, seed):
    with torch.random.fork_rng(devices=[]):
        torch.manual_seed(seed)
        module = torch.nn.ModuleDict({"encoder": torch.nn.Sequential(torch.nn.Linear(dimension, hidden), torch.nn.Tanh(),
            torch.nn.Linear(hidden, latent)), "decoder": torch.nn.Sequential(torch.nn.Linear(latent, hidden), torch.nn.Tanh(),
            torch.nn.Linear(hidden, dimension))})
    return module.to(dtype=torch.float32, device="cpu")


def state_digest(module):
    return digest({name: value.detach().cpu().tolist() for name, value in module.state_dict().items()})


def finite(torch, tensors):
    require(all(value.device.type == "cpu" and value.dtype == torch.float32 and bool(torch.isfinite(value).all()) for value in tensors),
            "finite CPU float32 tensors required")


def optimizer_tensors(torch, module, optimizer):
    result = {}
    for name, parameter in module.named_parameters():
        for field, value in optimizer.state.get(parameter, {}).items():
            require(field in {"step", "exp_avg", "exp_avg_sq"} and torch.is_tensor(value), "closed Adam state required")
            result[name + "/" + field] = value.detach().clone()
    return result or {"__empty__": torch.zeros(0, dtype=torch.float32)}


def save_checkpoint(torch, module, optimizer, directory, config, normalization, steps, parent=None):
    from safetensors.torch import save_file
    directory = Path(directory)
    directory.mkdir(mode=0o700)
    model_values = {name: value.detach().clone().contiguous() for name, value in module.state_dict().items()}
    optim_values = optimizer_tensors(torch, module, optimizer)
    finite(torch, [*model_values.values(), *optim_values.values()])
    for name, values in (("model.safetensors", model_values), ("optimizer.safetensors", optim_values)):
        target = directory / name
        require(not target.exists(), "checkpoint output exists")
        save_file(values, str(target))
        os.chmod(target, 0o600)
        with target.open("rb") as stream:
            os.fsync(stream.fileno())
    checkpoint = sealed({"schema": SCHEMA, "config": config, "normalization": normalization, "optimizer_steps": steps,
        "parent_checkpoint_sha256": parent, "model_file": {**binding(directory / "model.safetensors"), "path": "model.safetensors"},
        "optimizer_file": {**binding(directory / "optimizer.safetensors"), "path": "optimizer.safetensors"}, "model_state_sha256": state_digest(module),
        "optimizer_state_sha256": digest({key: value.tolist() for key, value in optim_values.items()}),
        "masks": dict.fromkeys(MASKS, 0), "semantic_fit_authorized": False, "contrastive_fit_authorized": False,
        "source_fidelity_established": False, "proof_authority": False, "qualified": False,
        "reconstruction_fit_scope": "selected_TRAIN_vectors_only"})
    reference = write_json(directory / "checkpoint.json", checkpoint)
    return checkpoint, reference


def load_checkpoint(torch, reference, expected_config):
    from safetensors.torch import load_file
    checkpoint = read_bound(reference)
    closed(checkpoint, {"schema", "config", "normalization", "optimizer_steps", "parent_checkpoint_sha256", "model_file",
        "optimizer_file", "model_state_sha256", "optimizer_state_sha256", "masks", "semantic_fit_authorized",
        "contrastive_fit_authorized", "source_fidelity_established", "proof_authority", "qualified", "reconstruction_fit_scope",
        "content_sha256"}, "AE checkpoint")
    require(checkpoint["schema"] == SCHEMA and raw(checkpoint["config"]) == raw(expected_config), "checkpoint profile differs")
    require(type(expected_config) is dict and "helper_binding" in expected_config
            and binding(__file__)["sha256"] == expected_config["helper_binding"]["sha256"], "checkpoint implementation pin differs")
    require(checkpoint["content_sha256"] == digest({k: v for k, v in checkpoint.items() if k != "content_sha256"}), "checkpoint seal differs")
    require(type(checkpoint["optimizer_steps"]) is int and 0 <= checkpoint["optimizer_steps"] <= 202, "checkpoint steps differ")
    require(all(checkpoint[key] is False for key in ("semantic_fit_authorized", "contrastive_fit_authorized",
        "source_fidelity_established", "proof_authority", "qualified")), "checkpoint authority forbidden")
    require(checkpoint["masks"] == dict.fromkeys(MASKS, 0) and all(type(value) is int for value in checkpoint["masks"].values()), "checkpoint supervision masks forbidden")
    files = {}
    for key, filename in (("model_file", "model.safetensors"), ("optimizer_file", "optimizer.safetensors")):
        closed(checkpoint[key], {"path", "sha256", "bytes"}, "checkpoint tensor binding")
        require(checkpoint[key]["path"] == filename, "fixed checkpoint-local tensor path required")
        files[key] = Path(reference["path"]).parent / filename
        observed = binding(files[key])
        require(observed["sha256"] == checkpoint[key]["sha256"] and observed["bytes"] == checkpoint[key]["bytes"], "tensor file pin differs")
    d, h, z = expected_config["architecture"]
    module = model(torch, d, h, z, expected_config["seed"])
    values = load_file(str(files["model_file"]), device="cpu")
    require(set(values) == set(module.state_dict()), "model tensor names differ")
    require(all(values[key].shape == value.shape for key, value in module.state_dict().items()), "model tensor shape differs")
    finite(torch, values.values())
    module.load_state_dict(values, strict=True)
    require(state_digest(module) == checkpoint["model_state_sha256"], "model tensor digest differs")
    optimizer = torch.optim.Adam(module.parameters(), lr=.003, foreach=False)
    values = load_file(str(files["optimizer_file"]), device="cpu")
    finite(torch, values.values())
    require(digest({key: value.tolist() for key, value in values.items()}) == checkpoint["optimizer_state_sha256"], "Adam tensor digest differs")
    if checkpoint["optimizer_steps"] == 0:
        require(set(values) == {"__empty__"} and values["__empty__"].shape == (0,), "zero-step optimizer differs")
    else:
        expected_keys = {name + "/" + field for name, _ in module.named_parameters() for field in ("step", "exp_avg", "exp_avg_sq")}
        require(set(values) == expected_keys, "Adam tensor names differ")
        for name, parameter in module.named_parameters():
            state = {field: values[name + "/" + field].clone() for field in ("step", "exp_avg", "exp_avg_sq")}
            require(state["step"].shape == () and float(state["step"]) == checkpoint["optimizer_steps"], "Adam step differs")
            require(state["exp_avg"].shape == state["exp_avg_sq"].shape == parameter.shape
                    and bool((state["exp_avg_sq"] >= 0).all()), "Adam moment shape/domain differs")
            optimizer.state[parameter] = state
    norm = checkpoint["normalization"]
    closed(norm, {"recipe", "mean", "rms"}, "TRAIN normalization")
    require(norm["recipe"] == "train_coordinate_mean_and_global_rms/v1" and type(norm["mean"]) is list and len(norm["mean"]) == d
            and all(type(value) in (int, float) and math.isfinite(value) for value in norm["mean"])
            and type(norm["rms"]) in (int, float) and math.isfinite(norm["rms"]) and norm["rms"] > 1e-8, "normalization bounds differ")
    require(digest(norm) == expected_config["normalization_sha256"], "normalization generation differs")
    return module, optimizer, checkpoint


def fit_steps(torch, module, optimizer, inputs, seed, start, stop, deadline):
    losses, norms = [], []
    for step in range(start, stop):
        require(time.monotonic() < deadline, "soft fit deadline reached before batch")
        order = list(range(16))
        random.Random(seed + step // 2).shuffle(order)
        selected = order[(step % 2) * 8:(step % 2 + 1) * 8]
        target = inputs[selected]
        optimizer.zero_grad(set_to_none=True)
        output = module["decoder"](module["encoder"](target))
        finite(torch, (output,))
        loss = torch.nn.functional.mse_loss(output, target)
        require(bool(torch.isfinite(loss)), "nonfinite reconstruction loss")
        loss.backward()
        require(all(parameter.grad is not None for parameter in module.parameters()), "missing AE gradients")
        finite(torch, (parameter.grad for parameter in module.parameters()))
        norm = float(torch.nn.utils.clip_grad_norm_(module.parameters(), 5., error_if_nonfinite=True))
        optimizer.step()
        finite(torch, module.parameters())
        finite(torch, optimizer_tensors(torch, module, optimizer).values())
        losses.append(float(loss.detach()))
        norms.append(norm)
    return {"optimizer_updates": stop - start, "losses": losses, "maximum_preclip_gradient_norm": max(norms, default=0.)}


def observations(torch, module, values, normalization):
    with torch.inference_mode():
        mean = torch.tensor(normalization["mean"], dtype=torch.float32)
        inputs = (values - mean) / normalization["rms"]
        latent = module["encoder"](inputs)
        reconstructed = module["decoder"](latent) * normalization["rms"] + mean
        finite(torch, (latent, reconstructed))
        return {"latent_vectors": latent.tolist(), "reconstructed_vectors": reconstructed.tolist(),
                "raw_coordinate_mse": float(torch.nn.functional.mse_loss(reconstructed, values)),
                "raw_identity_reconstruction_mse": 0., "row_count": len(values)}


def run_arm(plan, lane_id, seed, output, gate_reference):
    bundle, lane_receipt = preflight(plan, lane_id, seed)
    gate = read_bound(gate_reference)
    closed(gate, {"schema", "published_artifact_receipts_sha256", "training_release_authorized", "content_sha256"}, "publication gate")
    require(gate["schema"] == "reconstruction-publication-gate/v1" and gate["training_release_authorized"] is True,
            "root publication release required")
    sha(gate["published_artifact_receipts_sha256"])
    require(gate["content_sha256"] == digest({k: v for k, v in gate.items() if k != "content_sha256"}), "publication gate seal differs")
    output = Path(output).absolute()
    require(not output.exists() and output.parent.is_dir() and all(not p.is_symlink() for p in output.parents), "fresh output directory required")
    output.mkdir(mode=0o700)
    resource.setrlimit(resource.RLIMIT_CPU, (90, 100))
    resource.setrlimit(resource.RLIMIT_AS, (8 * 1024 ** 3, 8 * 1024 ** 3))
    resource.setrlimit(resource.RLIMIT_FSIZE, (32 * 1024 ** 2, 32 * 1024 ** 2))
    started = time.monotonic()
    import torch
    torch.set_num_threads(1)
    torch.set_num_interop_threads(1)
    require(torch.__version__ == plan["config"].get("torch_version", "2.13.0+cu130"), "selected Torch version differs")
    rng_before = torch.get_rng_state().clone()
    values = torch.tensor([row["vector"] for row in bundle["rows"]], dtype=torch.float32)
    finite(torch, (values,))
    mean = values.mean(dim=0)
    rms = float(torch.sqrt(((values - mean) ** 2).mean()))
    require(math.isfinite(rms) and rms > 1e-8, "nonconstant finite TRAIN vectors required")
    normalization = {"recipe": plan["config"]["normalization"], "mean": mean.tolist(), "rms": rms}
    inputs = (values - mean) / rms
    finite(torch, (inputs,))
    config = {"lane_id": lane_id, "architecture": list(LANES[lane_id]), "seed": seed, "dtype": "float32", "device": "cpu",
        "optimizer": {"kind": "Adam", "learning_rate": .003, "betas": [.9, .999], "eps": 1e-8, "weight_decay": 0., "foreach": False},
        "native_profile": bundle["profile"], "lane_receipt_sha256": digest(lane_receipt), "plan_sha256": digest(plan),
        "normalization_sha256": digest(normalization),
        "helper_binding": plan["helper_binding"], "bundle_binding": plan["lanes"][lane_id]["bundle_binding"],
        "training_ids": [row["id"] for row in bundle["rows"]], "input_sha256s": [row["input_sha256"] for row in bundle["rows"]]}
    module = model(torch, *LANES[lane_id], seed)
    optimizer = torch.optim.Adam(module.parameters(), lr=.003, foreach=False)
    initial = observations(torch, module, values, normalization)
    initial_state, initial_ref = save_checkpoint(torch, module, optimizer, output / "step000", config, normalization, 0)
    deadline = started + 60
    first = fit_steps(torch, module, optimizer, inputs, seed, 0, 100, deadline)
    middle_state, middle_ref = save_checkpoint(torch, module, optimizer, output / "step100", config, normalization, 100, digest(initial_state))
    restored, restored_optimizer, loaded = load_checkpoint(torch, middle_ref, config)
    require(digest(loaded) == digest(middle_state) and state_digest(restored) == state_digest(module), "100-step private restore differs")
    require(all(a.data_ptr() != b.data_ptr() for a, b in zip(module.parameters(), restored.parameters(), strict=True)), "private parameter storage shared")
    second = fit_steps(torch, restored, restored_optimizer, inputs, seed, 100, 200, deadline)
    final_state, final_ref = save_checkpoint(torch, restored, restored_optimizer, output / "step200", config, normalization, 200, digest(middle_state))
    final = observations(torch, restored, values, normalization)
    private, private_optimizer, loaded = load_checkpoint(torch, final_ref, config)
    require(observations(torch, private, values, normalization) == final and digest(loaded) == digest(final_state), "final private outputs differ")
    master_before = state_digest(restored)
    fit_steps(torch, private, private_optimizer, inputs, seed, 200, 201, deadline)
    scratch_state, scratch_ref = save_checkpoint(torch, private, private_optimizer, output / "resume_check_step201", config, normalization, 201, digest(final_state))
    fit_steps(torch, private, private_optimizer, inputs, seed, 201, 202, deadline)
    branch, branch_optimizer, _ = load_checkpoint(torch, scratch_ref, config)
    fit_steps(torch, branch, branch_optimizer, inputs, seed, 201, 202, deadline)
    require(state_digest(branch) == state_digest(private), "private two-step resumed weights differ")
    require(digest({k: v.tolist() for k, v in optimizer_tensors(torch, branch, branch_optimizer).items()}) ==
            digest({k: v.tolist() for k, v in optimizer_tensors(torch, private, private_optimizer).items()}), "private resumed Adam moments differ")
    require(master_before == state_digest(restored), "selected200 master changed in private checks")
    require(torch.equal(rng_before, torch.get_rng_state()), "global CPU RNG changed")
    for reference in (plan["helper_binding"], plan["lane_owner_binding"], plan["lanes"][lane_id]["bundle_binding"],
                      plan["lanes"][lane_id]["expected_lane_binding"], gate_reference, initial_ref, middle_ref, final_ref, scratch_ref):
        require(binding(reference["path"]) == reference, "bound bytes changed before report")
    report = sealed({"schema": "source-vector-reconstruction-training-report/v1", "status": "completed_fixed_budget_reconstruction_only",
        "lane_id": lane_id, "seed": seed, "config": config, "normalization": normalization,
        "selected_checkpoint": final_ref, "initial_checkpoint": initial_ref, "midpoint_checkpoint": middle_ref,
        "scratch_resume_checkpoint": scratch_ref, "selected_optimizer_updates": 200, "additional_private_optimizer_updates": 3,
        "actual_total_optimizer_updates": 203, "training_rows": 16, "query_or_dev_rows_read": 0,
        "initial_observations": initial, "final_observations": final, "training_segments": [first, second],
        "saved_reload_exact": True, "private_resume_weights_and_adam_exact": True, "master_state_preserved": True,
        "global_cpu_rng_preserved": True, "finite_loss_gradients_parameters_and_adam": True,
        "parameter_count": sum(value.numel() for value in restored.parameters()), "torch_version": torch.__version__,
        "wall_seconds": time.monotonic() - started, "peak_rss_kib": resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,
        "worker_cpu_seconds": resource.getrusage(resource.RUSAGE_SELF).ru_utime + resource.getrusage(resource.RUSAGE_SELF).ru_stime,
        "publication_gate_binding": gate_reference, "publication_gate_scope": "externally_selected_root_release_declaration_not_child_publication_authentication",
        "masks": dict.fromkeys(MASKS, 0), "reconstruction_fit_authorized": True, "semantic_fit_authorized": False,
        "contrastive_fit_authorized": False, "source_fidelity_established": False, "proof_authority": False, "qualified": False,
        "os_sandbox": False, "device": "cpu", "cpu_threads": 1, "optimizer": "Adam", "encoder_backbone_calls": 0,
        "formal_target_bodies_read": False, "prover_calls": 0, "old_checkpoints_modified": False})
    return write_json(output / "training-report.json", report)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--plan", required=True)
    parser.add_argument("--plan-sha256", required=True)
    parser.add_argument("--lane", choices=LANES, required=True)
    parser.add_argument("--seed", type=int, choices=(1729, 1730, 1731), required=True)
    parser.add_argument("--preflight", action="store_true")
    parser.add_argument("--output-directory")
    parser.add_argument("--publication-gate")
    parser.add_argument("--publication-gate-sha256")
    args = parser.parse_args()
    reference = binding(args.plan)
    require(reference["sha256"] == args.plan_sha256, "external plan bytes differ")
    plan = read_bound(reference)
    if args.preflight:
        bundle, receipt = preflight(plan, args.lane, args.seed)
        result = {"status": "ready_reconstruction_inputs_only_no_training", "lane_id": args.lane, "training_rows": len(bundle["rows"]),
                  "dimension": receipt["dimension"], "training_executed": False, "plan_binding": reference}
    else:
        require(args.output_directory and args.publication_gate and args.publication_gate_sha256, "publication gate and output required")
        gate = binding(args.publication_gate)
        require(gate["sha256"] == args.publication_gate_sha256, "external publication gate pin differs")
        result = run_arm(plan, args.lane, args.seed, args.output_directory, gate)
    print(json.dumps(result, sort_keys=True))


if __name__ == "__main__":
    main()
