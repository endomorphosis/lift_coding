"""Contract and tiny numerical fixtures; no campaign fitting or encoders."""
from __future__ import annotations

import hashlib
import importlib.util
import json
import random
import shutil
import time
from copy import deepcopy
from pathlib import Path

import pytest

DIRECTORY = Path(__file__).resolve().parent
BASE = DIRECTORY.parent
ROOT = BASE.parents[1]
SPEC = importlib.util.spec_from_file_location("expanded_reconstruction_fixture_subject", DIRECTORY / "train_expanded_reconstruction.py")
subject = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(subject)


def fixture_cohort():
    rows, inputs = [], {}
    for index in range(64):
        source = "Explicit numerical fixture source " + str(index)
        request = {"source_text": source, "context": {"role": "none_required", "text": "", "bindings": {},
                    "sha256": hashlib.sha256(b"").hexdigest()}}
        request_sha = subject.digest(request)
        item_id = "sha256:" + request_sha
        rows.append({"id": item_id, "group_id": "fixture-group-" + str(index // 4),
            "source_sha256": hashlib.sha256(source.encode()).hexdigest(), "input_sha256": request_sha,
            "split": "train" if index < 32 else "development", "context_role": "none_required"})
        inputs[item_id] = request
    cohort = subject.sealed({"schema": "source-only-authored-expansion-cohort/v1", "rows": rows,
        "contains_formal_targets": False, "policy": deepcopy(subject.SOURCE_POLICY)})
    selection = [{k: row[k] for k in ("id", "group_id", "source_sha256", "split")}
                 | {"original_masks": dict.fromkeys(subject.MASKS, 0)} for row in rows[:32]]
    return cohort, selection, inputs


def fixture_plan(tmp_path):
    cohort, selection, requests = fixture_cohort()
    cohort_binding = subject.write_json(tmp_path / "cohort.json", cohort)
    lanes = {}
    owner = subject.source_owner(subject.binding(ROOT / "external/ipfs_datasets/ipfs_datasets_py/logic/formalization/autoencoder/alignment_lane_bundle.py"),
                                 subject.LANE_OWNER_SHA, "pinned_test_lane_owner")
    for lane, (width, hidden, latent) in subject.LANES.items():
        original = ROOT / ("artifacts/autoformalization-alignment-20261003/stage-workflow-01/inputs/" + lane + "_raw_train_bundle.json")
        profile = json.loads(original.read_text())["profile"]
        rows, producer_rows = [], []
        for index, selected in enumerate(selection):
            vector = [0.] * width
            vector[index % width] = 1.
            request = requests[selected["id"]]
            source = request["source_text"]
            row = {"id": selected["id"], "input_sha256": subject.digest(request), "encoder_text": source,
                "encoder_text_sha256": hashlib.sha256(source.encode()).hexdigest(), "input": request,
                "status": "available", "reason": None, "vector": vector, "vector_sha256": subject.digest(vector),
                "upstream_vector_sha256": None, "token_receipt_sha256": None}
            bound = {key: row[key] for key in owner["ROW_BINDING_FIELDS"]}
            row["producer_row_sha256"] = subject.digest(bound)
            rows.append(row)
            producer_rows.append(bound)
        producer = subject.sealed({"schema": "alignment-producer-row-bindings/v1", "profile_sha256": subject.digest(profile),
            "artifact_binding": cohort_binding, "rows": producer_rows})
        bundle = subject.sealed({"schema": "alignment-lane-bundle/v1", "profile": profile, "producer_receipt": producer, "rows": rows})
        expected = {"profile_sha256": subject.digest(profile), "producer_receipt_sha256": subject.digest(producer),
                    "inputs": [{"id": r["id"], "input_sha256": r["input_sha256"]} for r in rows]}
        lanes[lane] = {"architecture": [width, hidden, latent],
            "bundle_binding": subject.write_json(tmp_path / (lane + ".json"), bundle),
            "expected_lane_binding": subject.write_json(tmp_path / (lane + "-expected.json"), expected)}
    return subject.sealed({"schema": "source-vector-expanded-reconstruction-run-plan/v1", "repo": str(ROOT / "external/ipfs_datasets"),
        "helper_binding": subject.binding(subject.__file__), "baseline_helper_binding": subject.binding(BASE / "training/train_reconstruction.py"),
        "bootstrap_binding": subject.binding(BASE / "huggingface/launch_reconstruction.py"),
        "lane_owner_binding": subject.binding(ROOT / "external/ipfs_datasets/ipfs_datasets_py/logic/formalization/autoencoder/alignment_lane_bundle.py"),
        "cohort_binding": cohort_binding, "train_selection": selection, "seeds": [1729, 1730, 1731],
        "config": deepcopy(subject.CONFIG), "lanes": lanes,
        "authorization_scope": "user_authorized_source_vector_reconstruction_only_no_semantic_mask_promotion"})


@pytest.mark.parametrize("lane", subject.LANES)
def test_complete_native_train32_preflight_reads_no_development_vector_files(tmp_path, lane):
    value = fixture_plan(tmp_path)
    bundle, receipt = subject.preflight(value, lane, 1729)
    assert len(bundle["rows"]) == 32 and receipt["dimension"] == subject.LANES[lane][0]
    assert receipt["model_calls"] == receipt["optimizer_updates"] == 0
    assert not list(tmp_path.glob("*development*"))


@pytest.mark.parametrize("mutation", ["train16", "reverse", "weak_mask", "bool_mask", "dev_selection", "extra_steps", "bool_steps", "old_schedule"])
def test_wrong_selection_mask_or_budget_cannot_enable_expanded_fit(tmp_path, mutation):
    value = fixture_plan(tmp_path)
    if mutation == "train16":
        value["train_selection"] = value["train_selection"][:16]
    elif mutation == "reverse":
        value["train_selection"].reverse()
    elif mutation == "weak_mask":
        value["train_selection"][0]["original_masks"]["weak_decoder_fit"] = 1
    elif mutation == "bool_mask":
        value["train_selection"][0]["original_masks"]["weak_decoder_fit"] = False
    elif mutation == "dev_selection":
        value["train_selection"][0]["split"] = "development"
    elif mutation == "extra_steps":
        value["config"]["steps"] = 201
    elif mutation == "bool_steps":
        value["config"]["batch_size"] = True
    else:
        value["config"]["batch_schedule"] = "old_two_batches/v1"
    subject.sealed(value)
    with pytest.raises(ValueError):
        subject.preflight(value, "legacy8", 1729)


@pytest.mark.parametrize("mutation", ["group", "source", "input", "targets", "promoted_policy", "pristine", "bool_policy_mask", "extra_target_field"])
def test_cohort_leakage_or_semantic_authority_rejected(mutation):
    value, selection, _ = fixture_cohort()
    if mutation in {"group", "source", "input"}:
        key = {"group": "group_id", "source": "source_sha256", "input": "input_sha256"}[mutation]
        value["rows"][32][key] = value["rows"][0][key]
        if mutation == "input":
            value["rows"][32]["id"] = value["rows"][0]["id"]
    elif mutation == "targets":
        value["contains_formal_targets"] = True
    elif mutation == "promoted_policy":
        value["policy"]["semantic_label_admission"] = True
    elif mutation == "pristine":
        value["policy"]["pristine_holdout"] = True
    elif mutation == "bool_policy_mask":
        value["policy"]["semantic_masks"]["weak_decoder_fit"] = False
    else:
        value["rows"][0]["formal_target"] = "fixture target must be rejected"
    subject.sealed(value)
    with pytest.raises(ValueError):
        subject.validate_cohort(value, selection)


@pytest.mark.parametrize("seed", [1729, 1730, 1731])
def test_scheduler_covers_every_train_row_once_each_four_batch_epoch_and_preserves_rng(seed):
    before = random.getstate()
    for epoch in (0, 1, 24, 49):
        batches = [subject.batch_indices(seed, epoch * 4 + batch) for batch in range(4)]
        assert all(len(batch) == 8 for batch in batches)
        assert sorted(item for batch in batches for item in batch) == list(range(32))
    assert subject.batch_indices(seed, 100) == subject.batch_indices(seed, 100)
    assert random.getstate() == before


def test_scheduler_rejects_foreign_seed_step_and_boolean_aliases():
    for seed, step in [(1728, 0), (True, 0), (1729, -1), (1729, 202), (1729, False)]:
        with pytest.raises(ValueError):
            subject.batch_indices(seed, step)


@pytest.fixture(scope="module")
def torch_provider():
    # The isolated pytest process can select the pinned native numerical site.
    bootstrap = subject.source_owner(subject.binding(BASE / "huggingface/launch_reconstruction.py"), subject.BOOTSTRAP_SHA,
                                     "pinned_expansion_fixture_bootstrap")
    bootstrap["select_native_site"]()
    import torch
    torch.set_num_threads(1)
    return torch


def zero_checkpoint(tmp_path, torch, lane="legacy8"):
    d, h, z = subject.LANES[lane]
    norm = {"recipe": "train_coordinate_mean_and_global_rms/v1", "mean": [0.] * d, "rms": 1.}
    config = {"lane_id": lane, "architecture": [d, h, z], "seed": 1729,
        "normalization_sha256": subject.digest(norm), "helper_binding": subject.binding(subject.__file__),
        "training_rows": 32, "batch_schedule": subject.SCHEDULE, "fit_policy": subject.FIT_POLICY,
        "native_profile": {"lane_id": lane, "dimension": d, "pooling": "explicit_numerical_fixture"}}
    module = subject.model(torch, d, h, z, 1729)
    optimizer = torch.optim.Adam(module.parameters(), lr=.003, foreach=False)
    checkpoint, reference = subject.save_checkpoint(torch, module, optimizer, tmp_path / "zero", config, norm, 0)
    return module, optimizer, checkpoint, reference, config, norm


@pytest.mark.parametrize("lane", subject.LANES)
def test_zero_update_safe_reload_is_exact_and_disjoint_with_unchanged_global_rng(tmp_path, torch_provider, lane):
    torch = torch_provider
    original, optimizer, checkpoint, reference, config, _ = zero_checkpoint(tmp_path, torch, lane)
    before = torch.get_rng_state().clone()
    restored, restored_optimizer, observed = subject.load_checkpoint(torch, reference, config)
    assert observed == checkpoint and observed["optimizer_steps"] == 0
    assert subject.state_digest(restored) == subject.state_digest(original)
    assert all(a.data_ptr() != b.data_ptr() for a, b in zip(original.parameters(), restored.parameters(), strict=True))
    assert not optimizer.state and not restored_optimizer.state
    assert torch.equal(before, torch.get_rng_state())


def test_tiny_fixture_resume_crosses_four_batch_epoch_exactly_and_preserves_master(tmp_path, torch_provider):
    torch = torch_provider
    master, optimizer, _, _, config, norm = zero_checkpoint(tmp_path, torch)
    inputs = torch.arange(256, dtype=torch.float32).reshape(32, 8) / 256
    before = torch.get_rng_state().clone()
    subject.fit_steps(torch, master, optimizer, inputs, 1729, 0, 4, time.monotonic() + 30)
    _, ref = subject.save_checkpoint(torch, master, optimizer, tmp_path / "step4", config, norm, 4)
    frozen = subject.state_digest(master)
    branch_a, optim_a, _ = subject.load_checkpoint(torch, ref, config)
    branch_b, optim_b, _ = subject.load_checkpoint(torch, ref, config)
    subject.fit_steps(torch, branch_a, optim_a, inputs, 1729, 4, 5, time.monotonic() + 30)
    subject.fit_steps(torch, branch_b, optim_b, inputs, 1729, 4, 5, time.monotonic() + 30)
    assert subject.state_digest(branch_a) == subject.state_digest(branch_b)
    assert subject.digest({k: v.tolist() for k, v in subject.optimizer_tensors(torch, branch_a, optim_a).items()}) == \
           subject.digest({k: v.tolist() for k, v in subject.optimizer_tensors(torch, branch_b, optim_b).items()})
    assert frozen == subject.state_digest(master)
    assert torch.equal(before, torch.get_rng_state())


@pytest.mark.parametrize("mutation", ["old_rows", "old_schedule", "old_policy", "architecture", "seed_bool"])
def test_checkpoint_configuration_transplants_rejected(tmp_path, torch_provider, mutation):
    _, _, _, ref, config, _ = zero_checkpoint(tmp_path, torch_provider)
    expected = deepcopy(config)
    if mutation == "old_rows":
        expected["training_rows"] = 16
    elif mutation == "old_schedule":
        expected["batch_schedule"] = "old_schedule"
    elif mutation == "old_policy":
        expected["fit_policy"] = "semantic_fit"
    elif mutation == "architecture":
        expected["architecture"] = [768, 128, 64]
    else:
        expected["seed"] = True
    with pytest.raises(ValueError):
        subject.load_checkpoint(torch_provider, ref, expected)


def test_download_relocation_needs_no_original_source_files(tmp_path, torch_provider):
    original, _, checkpoint, ref, config, _ = zero_checkpoint(tmp_path, torch_provider)
    download = tmp_path / "download"
    shutil.copytree(Path(ref["path"]).parent, download)
    shutil.rmtree(Path(ref["path"]).parent)
    loaded, _, observed = subject.load_checkpoint(torch_provider, subject.binding(download / "checkpoint.json"), config)
    assert observed == checkpoint and subject.state_digest(loaded) == subject.state_digest(original)


def test_publication_gate_rejection_happens_before_provider_import_or_output(tmp_path):
    value = fixture_plan(tmp_path)
    gate = subject.sealed({"schema": "reconstruction-publication-gate/v1", "published_artifact_receipts_sha256": "a" * 64,
                           "training_release_authorized": False})
    ref = subject.write_json(tmp_path / "gate.json", gate)
    output = tmp_path / "forbidden-output"
    with pytest.raises(ValueError, match="root publication release"):
        subject.run_arm(value, "legacy8", 1729, output, ref)
    assert not output.exists()


def test_verified_owner_rejects_changed_source_before_execution(tmp_path):
    source = tmp_path / "owner.py"
    source.write_text("raise AssertionError('must not execute')\n")
    ref = subject.binding(source)
    with pytest.raises(ValueError, match="selected implementation"):
        subject.source_owner(ref, "0" * 64, "fixture")
    source.write_text("raise AssertionError('changed file must not execute')\n")
    with pytest.raises(ValueError, match="binding"):
        subject.source_owner(ref, ref["sha256"], "fixture")
