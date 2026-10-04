"""Input and zero-update safe checkpoint tests; no training before publication."""
import importlib.util
import json
import shutil
from copy import deepcopy
from pathlib import Path

import pytest

DIRECTORY = Path(__file__).resolve().parent
SPEC = importlib.util.spec_from_file_location("reconstruction_isolated_helper", DIRECTORY / "train_reconstruction.py")
subject = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(subject)


def plan():
    return json.loads((DIRECTORY / "run-plan-02.json").read_text())


@pytest.mark.parametrize("lane", subject.LANES)
def test_reconstruction_preflight_accepts_complete_native_train16_without_models(lane):
    bundle, receipt = subject.preflight(plan(), lane, 1729)
    assert len(bundle["rows"]) == 16 and receipt["dimension"] == subject.LANES[lane][0]
    assert receipt["model_calls"] == receipt["optimizer_updates"] == 0


@pytest.mark.parametrize("mutation", ["holdout", "dev_split", "reorder", "strong_mask", "bool_mask", "wrong_width", "extra_steps"])
def test_reconstruction_foreign_selection_scope_or_budget_cannot_enable_training(mutation):
    value = plan()
    if mutation == "holdout":
        value["train_selection"][0]["id"] = "invented-withheld-query"
    elif mutation == "dev_split":
        value["train_selection"][0]["split"] = "dev"
    elif mutation == "reorder":
        value["train_selection"].reverse()
    elif mutation == "strong_mask":
        value["train_selection"][0]["original_masks"]["strong_semantic_fit"] = 1
    elif mutation == "bool_mask":
        value["train_selection"][0]["original_masks"]["weak_decoder_fit"] = True
    elif mutation == "wrong_width":
        value["lanes"]["legacy8"]["architecture"] = [384, 128, 32]
    else:
        value["config"]["steps"] = 201
    subject.sealed(value)
    with pytest.raises(ValueError):
        subject.preflight(value, "legacy8", 1729)


def zero_checkpoint(tmp_path, lane="legacy8"):
    import torch

    d, h, z = subject.LANES[lane]
    normalization = {"recipe": "train_coordinate_mean_and_global_rms/v1", "mean": [0.] * d, "rms": 1.}
    config = {"architecture": [d, h, z], "seed": 1729, "normalization_sha256": subject.digest(normalization),
              "helper_binding": subject.binding(subject.__file__),
              "native_profile": {"lane_id": lane, "dimension": d, "pooling": "fixture-pooling-declaration"}}
    module = subject.model(torch, d, h, z, 1729)
    optimizer = torch.optim.Adam(module.parameters(), lr=.003, foreach=False)
    checkpoint, reference = subject.save_checkpoint(torch, module, optimizer, tmp_path / "zero", config, normalization, 0)
    return torch, module, optimizer, checkpoint, reference, config


@pytest.mark.parametrize("lane", subject.LANES)
def test_reconstruction_zero_update_reload_preserves_exact_native_tensor_shape_rng_and_private_storage(tmp_path, lane):
    torch, original, optimizer, checkpoint, reference, config = zero_checkpoint(tmp_path, lane)
    state = torch.get_rng_state().clone()
    loaded, loaded_optimizer, observed = subject.load_checkpoint(torch, reference, config)
    assert observed == checkpoint and observed["optimizer_steps"] == 0
    assert subject.state_digest(loaded) == subject.state_digest(original)
    assert all(a.data_ptr() != b.data_ptr() for a, b in zip(original.parameters(), loaded.parameters(), strict=True))
    assert not optimizer.state and not loaded_optimizer.state
    assert torch.equal(state, torch.get_rng_state())


@pytest.mark.parametrize("mutation", ["width", "producer", "pooling", "config_bool", "normalization"])
def test_reconstruction_checkpoint_transplants_reject_when_numeric_weights_still_fit(mutation, tmp_path):
    torch, _, _, checkpoint, reference, config = zero_checkpoint(tmp_path)
    expected = deepcopy(config)
    if mutation == "width":
        expected["architecture"] = [384, 128, 32]
    elif mutation == "producer":
        expected["native_profile"]["lane_id"] = "native384"
    elif mutation == "pooling":
        expected["native_profile"]["pooling"] = "another-pooling"
    elif mutation == "config_bool":
        expected["seed"] = True
    else:
        checkpoint["normalization"]["rms"] = 2.
        subject.sealed(checkpoint)
        replaced = Path(reference["path"]).parent / "changed-normalization.json"
        reference = subject.write_json(replaced, checkpoint)
    with pytest.raises(ValueError):
        subject.load_checkpoint(torch, reference, expected)


def test_reconstruction_checkpoint_can_reload_from_a_relocated_download_directory(tmp_path):
    torch, original, _, checkpoint, reference, config = zero_checkpoint(tmp_path)
    download = tmp_path / "downloaded"
    shutil.copytree(Path(reference["path"]).parent, download)
    relocated = subject.binding(download / "checkpoint.json")
    loaded, _, observed = subject.load_checkpoint(torch, relocated, config)
    assert observed == checkpoint and subject.state_digest(loaded) == subject.state_digest(original)


@pytest.mark.parametrize("mutation", ["sha", "nan", "shape"])
def test_reconstruction_safe_tensor_replacement_rejects_digest_nonfinite_and_shape(tmp_path, mutation):
    from safetensors.torch import load_file, save_file

    torch, _, _, checkpoint, reference, config = zero_checkpoint(tmp_path)
    model_path = Path(reference["path"]).parent / checkpoint["model_file"]["path"]
    tensors = load_file(str(model_path))
    name = next(iter(tensors))
    if mutation == "sha":
        tensors[name].reshape(-1)[0] += 1
    elif mutation == "nan":
        tensors[name].reshape(-1)[0] = float("nan")
    else:
        tensors[name] = tensors[name].reshape(-1)[:1]
    save_file(tensors, str(model_path))
    checkpoint["model_file"] = {**subject.binding(model_path), "path": "model.safetensors"}
    subject.sealed(checkpoint)
    reference = subject.write_json(Path(reference["path"]).parent / "changed-checkpoint.json", checkpoint)
    with pytest.raises(ValueError):
        subject.load_checkpoint(torch, reference, config)


def test_reconstruction_checkpoint_authority_or_numeric_mask_alias_cannot_be_resealed(tmp_path):
    torch, _, _, checkpoint, reference, config = zero_checkpoint(tmp_path)
    checkpoint["masks"]["contrastive_supervision"] = False
    subject.sealed(checkpoint)
    reference = subject.write_json(tmp_path / "changed-checkpoint.json", checkpoint)
    with pytest.raises(ValueError, match="supervision"):
        subject.load_checkpoint(torch, reference, config)


def test_reconstruction_fit_requires_root_publication_release_before_import_or_output(tmp_path):
    value = plan()
    gate = subject.sealed({"schema": "reconstruction-publication-gate/v1", "published_artifact_receipts_sha256": "a" * 64,
                           "training_release_authorized": False})
    reference = subject.write_json(tmp_path / "not-released.json", gate)
    output = tmp_path / "must-not-exist"
    with pytest.raises(ValueError, match="root publication release"):
        subject.run_arm(value, "legacy8", 1729, output, reference)
    assert not output.exists()


def test_reconstruction_json_boundary_rejects_duplicate_nonfinite_nonutf8_and_symlink(tmp_path):
    for index, data in enumerate((b'{"x":1,"x":2}', b'{"x":NaN}', b'\xff')):
        path = tmp_path / str(index)
        path.write_bytes(data)
        with pytest.raises((ValueError, UnicodeError)):
            subject.read_bound(subject.binding(path))
    link = tmp_path / "linked"
    link.symlink_to(tmp_path / "0")
    with pytest.raises(ValueError, match="nonsymlink"):
        subject.binding(link)
