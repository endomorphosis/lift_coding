"""Acquisition, task leakage and original-optimizer observation boundaries."""
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import subprocess

import pytest

import train_codebase_ir as pilot


def manifest():
    return json.loads((pilot.ROOT / "corpus-manifest-01.json").read_bytes())


@pytest.mark.parametrize("mutation", ["duplicate_task", "crosssplit_source", "hidden_input", "escaping_input", "missing_evaluation"])
def test_refuses_leaky_or_unscoped_task_manifests(mutation):
    value = manifest()
    if mutation == "duplicate_task":
        value["tasks"][1]["task_id"] = value["tasks"][0]["task_id"]
    elif mutation == "crosssplit_source":
        value["tasks"][2]["sources"][0]["sha256"] = value["tasks"][0]["sources"][0]["sha256"]
    elif mutation == "hidden_input":
        value["tasks"][0]["sources"][0]["path"] = "headless-terminal/tests/test_hidden.py"
    elif mutation == "escaping_input":
        value["tasks"][0]["sources"][0]["path"] = "headless-terminal/../../other.py"
    else:
        value["tasks"][-1]["split"] = "train"
    with pytest.raises(ValueError):
        pilot.validate_manifest(value)


@pytest.mark.parametrize("mutation", ["symlink", "hardlink", "too_large"])
def test_bound_acquisition_refuses_aliases_and_growth(tmp_path, mutation):
    source = tmp_path / "source"
    source.write_bytes(b"public")
    path = source
    if mutation == "symlink":
        path = tmp_path / "alias"
        path.symlink_to(source)
    elif mutation == "hardlink":
        path = tmp_path / "hard"
        path.hardlink_to(source)
    with pytest.raises(ValueError):
        pilot.read(path, 2 if mutation == "too_large" else 100)


def test_frozen_capture_refuses_original_source_drift_before_destination_exists(tmp_path):
    value = manifest()
    root = tmp_path / "public-checkout"
    root.mkdir()
    for task in value["tasks"]:
        for pin in [*task["sources"], task["instruction"], task["environment"]]:
            raw = pilot.read(Path(value["repository"]["path"]) / pin["path"])
            target = root / pin["path"]
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(raw)
    subprocess.run(["git", "init", "-q", str(root)], check=True)
    subprocess.run(["git", "add", "--", *[t["task_id"] for t in value["tasks"]]], cwd=root, check=True)
    subprocess.run(["git", "-c", "user.name=Training test", "-c", "user.email=training-test@localhost", "commit", "-qm", "public input fixture"], cwd=root, check=True)
    value["repository"] = {"path": str(root), "head": subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=root, text=True).strip()}
    source = root / value["tasks"][0]["sources"][0]["path"]
    source.write_bytes(source.read_bytes() + b"\n# drift\n")
    destination = tmp_path / "capture"
    with pytest.raises(ValueError, match="provenance"):
        pilot.capture(value, destination)
    assert not destination.exists()


def test_observer_invokes_original_adam_step_and_restores_it_on_budget_failure():
    import torch
    from ipfs_datasets_py.logic.formalization.autoencoder.security import codebase_autoencoder as ae
    parameter = torch.tensor([1.0], requires_grad=True)
    optimizer = torch.optim.Adam([parameter], lr=0.02)
    # Torch installs its own profiling wrapper when the first optimizer is
    # constructed. The observer must restore the actual current callable.
    original = torch.optim.Adam.step
    initial = pilot.weights_hash(ae, [parameter])
    with pytest.raises(ValueError, match="budget"):
        with pilot.observe_steps(torch, ae, 1) as steps:
            parameter.square().sum().backward()
            optimizer.step()
            optimizer.step()
    assert torch.optim.Adam.step is original
    assert len(steps) == 1
    assert steps[0]["before_weights_sha256"] == initial
    assert steps[0]["after_weights_sha256"] == pilot.weights_hash(ae, [parameter])
    assert steps[0]["after_weights_sha256"] != initial


def test_heldout_control_refuses_initialization_substitution_before_any_inference(tmp_path, monkeypatch):
    import torch
    from ipfs_datasets_py.logic.formalization.autoencoder.security import codebase_autoencoder as ae
    checkpoint = {"input_width": 44, "latent_width": 8,
                  "weights": [p.tolist() for p in pilot.seeded_parameters(torch, 1729, 44, 8)]}
    raw = pilot.wire(checkpoint)
    (tmp_path / "checkpoint.json").write_bytes(raw)
    descriptor = {"output": str(tmp_path), "checkpoint_sha256": pilot.sha(raw),
                  "metrics": {"seed": 1729, "initial_weights_sha256": "0" * 64}}
    def forbidden(*args):
        pytest.fail("unbound control must refuse before heldout inference")
    monkeypatch.setattr(ae, "_inference", forbidden)
    with pytest.raises(ValueError, match="untrained control"):
        pilot.evaluate(ae, torch, descriptor=descriptor, task_features={}, tasks=[])


@pytest.mark.parametrize("weights", [[], [[float("nan")]], [[[0.0] * 8] * 44, [0.0] * 8, [[0.0] * 44] * 8, [float("inf")] * 44]])
def test_heldout_inference_refuses_malformed_or_nonfinite_weights(weights):
    import torch
    with pytest.raises(ValueError):
        pilot.check_parameters(torch, weights, 44, 8)
