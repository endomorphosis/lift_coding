"""Toy linear controls and metadata rejection; no published model inference."""
from __future__ import annotations

import hashlib
import importlib.util
import math
from pathlib import Path

import pytest

DIRECTORY = Path(__file__).resolve().parent
SPEC = importlib.util.spec_from_file_location("frozen_evaluation_worker", DIRECTORY / "evaluate_published_reconstruction.py")
subject = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(subject)


@pytest.fixture(scope="module")
def torch_cpu():
    import torch
    torch.set_num_threads(1)
    torch.set_num_interop_threads(1)
    return torch


def normalization(torch, values):
    mean = values.mean(dim=0)
    return {"mean": mean.tolist(), "rms": float(torch.sqrt(((values - mean)**2).mean()))}


def test_train_line_pca_preserves_line_and_cannot_reconstruct_unseen_orthogonal_component(torch_cpu):
    torch = torch_cpu
    train = torch.tensor([[x, 2., 3.] for x in (-3., -2., -1., 1., 2., 3.)], dtype=torch.float32)
    fixed = normalization(torch, train)
    with torch.inference_mode():
        control = subject.fit_pca_control(torch, train, fixed, 2)
        latent, reconstructed, mean_prediction = subject.project_pca_control(torch, control, train)
        assert control["rank"] == control["retained"] == 1
        assert latent.shape == (6, 1) and control["basis"].shape == (1, 3)
        assert torch.allclose(reconstructed, train, atol=1e-6, rtol=0)
        assert torch.equal(mean_prediction, torch.tensor(fixed["mean"]).expand_as(train))
        query = torch.tensor([[50., 200., -300.]], dtype=torch.float32)
        _, prediction, mean_prediction = subject.project_pca_control(torch, control, query)
        assert torch.allclose(prediction, torch.tensor([[50., 2., 3.]]), atol=1e-5, rtol=0)
        assert torch.equal(mean_prediction, torch.tensor([[0., 2., 3.]]))
        assert subject.reconstruction_metrics(torch, query, prediction)["raw_coordinate_mse"] > 10000
        assert control["mean"].tolist() == fixed["mean"]


def test_wide_train16_control_has_at_most15_actual_axes_even_when_latent_budget64(torch_cpu):
    torch = torch_cpu
    train = torch.tensor([[math.sin((i + 1)*(j + 3)*.123) for j in range(32)] for i in range(16)], dtype=torch.float32)
    with torch.inference_mode():
        control = subject.fit_pca_control(torch, train, normalization(torch, train), 64)
        latent, reconstructed, _ = subject.project_pca_control(torch, control, train)
        assert control["rank"] == control["retained"] == 15
        assert latent.shape == (16, 15) and control["basis"].shape == (15, 32)
        assert subject.reconstruction_metrics(torch, train, reconstructed)["raw_coordinate_mse"] < 1e-10
        expected = max(train.shape)*torch.finfo(torch.float32).eps*torch.linalg.svdvals((train - train.mean(dim=0))/normalization(torch, train)["rms"])[0]
        assert math.isclose(control["threshold"], float(expected), rel_tol=1e-5)


def test_constant_toy_control_has_zero_actual_axes_without_padding(torch_cpu):
    torch = torch_cpu
    train = torch.ones((4, 3), dtype=torch.float32)
    with torch.inference_mode():
        control = subject.fit_pca_control(torch, train, {"mean": [1., 1., 1.], "rms": 1.}, 5)
        latent, reconstructed, _ = subject.project_pca_control(torch, control, train)
        assert control["rank"] == control["retained"] == 0
        assert latent.shape == (4, 0) and control["basis"].shape == (0, 3)
        assert torch.equal(reconstructed, train)


def test_reconstruction_cosine_undefined_rows_are_visible_and_not_invented(torch_cpu):
    torch = torch_cpu
    source = torch.tensor([[1., 0.], [0., 0.], [0., 1.]], dtype=torch.float32)
    reconstructed = torch.tensor([[1., 0.], [0., 0.], [0., 0.]], dtype=torch.float32)
    metrics = subject.reconstruction_metrics(torch, source, reconstructed)
    assert metrics["cosine_defined_rows"] == 1 and metrics["cosine_undefined_rows"] == 2
    assert metrics["mean_cosine_distortion"] == 0.
    zeros = subject.reconstruction_metrics(torch, source*0., reconstructed*0.)
    assert zeros["mean_cosine_distortion"] is None and zeros["maximum_cosine_distortion"] is None


def toy_cohort():
    rows = []
    for index in range(34):
        input_sha = hashlib.sha256(("input" + str(index)).encode()).hexdigest()
        rows.append({"id": "sha256:" + input_sha, "input_sha256": input_sha,
                     "source_sha256": hashlib.sha256(("source" + str(index)).encode()).hexdigest(),
                     "split": "train" if index < 16 else "validation", "group_id": "group" + str(index//4),
                     "context_role": "none_required" if index < 32 else "explicit_assumptions"})
    value = subject.sealed({"schema": "source-only-frozen-evaluation-cohort/v1", "rows": rows, "contains_formal_targets": False})
    run_plan = {"train_selection": [{k: row[k] for k in ("id", "group_id", "source_sha256", "split")} for row in rows[:16]]}
    return value, run_plan


def test_source_only_metadata_accepts_declared_group_disjoint_cohorts_without_numeric_or_target_access():
    value, run_plan = toy_cohort()
    assert len(subject.validate_cohort(value, run_plan)) == 34


@pytest.mark.parametrize("mutation", ["source_overlap", "group_overlap", "panel_id_alias", "targets_present", "extra_target_field"])
def test_resealed_metadata_cannot_hide_overlap_aliases_or_target_access(mutation):
    value, run_plan = toy_cohort()
    if mutation == "source_overlap":
        value["rows"][16]["source_sha256"] = value["rows"][0]["source_sha256"]
    elif mutation == "group_overlap":
        value["rows"][16]["group_id"] = value["rows"][0]["group_id"]
    elif mutation == "panel_id_alias":
        value["rows"][16]["input_sha256"] = value["rows"][0]["input_sha256"]
    elif mutation == "targets_present":
        value["contains_formal_targets"] = True
    else:
        value["rows"][16]["formal_target"] = "forbidden toy declaration"
    value = subject.sealed({k: v for k, v in value.items() if k != "content_sha256"})
    with pytest.raises(ValueError):
        subject.validate_cohort(value, run_plan)


def test_frozen_owner_executes_checked_captured_source_not_a_subsequent_file_read(tmp_path, monkeypatch):
    path = tmp_path / "toy_owner.py"
    selected = b"VALUE = 42\n"
    path.write_bytes(selected)
    reference = subject.binding(path)
    actual_capture = subject.captured
    def capture_then_change(bound):
        data = actual_capture(bound)
        path.write_bytes(b"raise RuntimeError('unselected replacement executed')\n")
        return data
    monkeypatch.setattr(subject, "captured", capture_then_change)
    owner = subject.compiled_owner(reference, reference["sha256"], "toy_frozen_owner")
    assert owner["VALUE"] == 42
