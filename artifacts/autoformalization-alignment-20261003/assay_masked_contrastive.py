"""Bounded synthetic numerical checks; this runner does not admit training labels.

``prepare_numerical_assay`` is a no-write replay helper.  The command-line
driver runs it in a fresh CPU subprocess and publishes only engineering
diagnostics.  No historical vector, target, encoder, prover, trained model or
checkpoint is an input to the numerical objective.
"""
from __future__ import annotations

import argparse
import hashlib
import importlib.abc
import json
import math
import os
import resource
import signal
import subprocess
import sys
import time
import traceback
import types
from datetime import UTC, datetime
from pathlib import Path

WORKSPACE = Path(__file__).resolve().parents[2]
REPOSITORY = WORKSPACE / "external/ipfs_datasets"
CAMPAIGN = Path(__file__).resolve().parent
DEFAULT_OUTPUT = CAMPAIGN / "masked-contrastive-01/numerical"
NATIVE_PYTHON = Path("/home/barberb/.local/bin/python")
MAX_RSS_KIB = 2 * 1024**2
CPU_SOFT_SECONDS = 30
CPU_HARD_SECONDS = 35
WALL_SECONDS = 60
MAX_OUTPUT_BYTES = 8 * 1024**2
FORBIDDEN_IMPORTS = {
    "transformers", "sentence_transformers", "spacy", "safetensors", "tensorflow",
    "jax", "lean", "z3", "cvc5", "torchvision", "torchaudio",
}
MASK_NAMES = (
    "weak_decoder_fit", "strong_semantic_fit", "contrastive_supervision",
    "proof_supervision", "fidelity_evaluation",
)
FALSE_FLAGS = dict.fromkeys((
    "accepted", "qualified", "source_fidelity_established", "proof_authority",
    "semantic_label_admission", "semantic_equivalence_verified",
    "relation_identity_authenticated", "training_executed", "optimizer_executed",
    "encoder_executed", "prover_executed", "checkpoint_promoted",
    "integration_into_legacy_profile", "os_sandbox",
), False)
CODE_FILES = {
    "runner": Path(__file__).resolve(),
    "masked_owner": REPOSITORY / "ipfs_datasets_py/logic/formalization/autoencoder/alignment_masked_contrastive.py",
    "legacy_projection_owner": REPOSITORY / "ipfs_datasets_py/logic/formalization/autoencoder/alignment_projection.py",
    "legacy_relation_configuration_source_only": REPOSITORY / "ipfs_datasets_py/optimizers/logic_theorem_optimizer/legal_ir_loss_configuration.py",
}


def require(condition, message):
    if not condition:
        raise ValueError(message)


def raw(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False,
                      allow_nan=False).encode("utf-8")


def digest(value):
    return hashlib.sha256(raw(value)).hexdigest()


def sealed(value):
    require("content_sha256" not in value, "new unsealed object required")
    return {**value, "content_sha256": digest(value)}


def binding(path):
    data = Path(path).read_bytes()
    require(len(data) <= MAX_OUTPUT_BYTES, "bounded implementation or output file required")
    return {"path": str(Path(path).resolve()), "bytes": len(data),
            "sha256": hashlib.sha256(data).hexdigest()}


def implementation_bindings(repository_root=None):
    repo = Path(repository_root).resolve() if repository_root is not None else REPOSITORY
    result = {}
    for role, path in CODE_FILES.items():
        selected = path if role == "runner" else repo / path.relative_to(REPOSITORY)
        result[role] = binding(selected)
    return result


def _namespace(repository_root):
    """Expose exact source modules without importing repository initializers."""
    base = Path(repository_root).resolve()
    names = (
        "ipfs_datasets_py", "ipfs_datasets_py.logic",
        "ipfs_datasets_py.logic.formalization",
        "ipfs_datasets_py.logic.formalization.autoencoder",
    )
    for name in names:
        if name not in sys.modules:
            module = types.ModuleType(name)
            module.__path__ = [str(base.joinpath(*name.split(".")))]
            sys.modules[name] = module


def _tensor_sha256(tensor):
    contiguous = tensor.detach().cpu().contiguous()
    header = raw({"dtype": str(contiguous.dtype), "shape": list(contiguous.shape),
                  "recipe": "contiguous_cpu_tensor_native_bytes/v1"})
    data = bytes(contiguous.reshape(-1).view(dtype=__import__("torch").uint8).tolist())
    return hashlib.sha256(header + b"\n" + data).hexdigest()


def _state_sha256(model):
    state = {name: _tensor_sha256(tensor)
             for name, tensor in sorted(model.state_dict().items())}
    return digest(state)


def _finite_nonzero(torch, values):
    return all(bool(torch.isfinite(value).all()) for value in values) and all(
        bool((value != 0).any()) for value in values)


def _manual_log_mass(scores, positives, negatives, weights):
    """Independent Python-float reference, without tensor masked reductions."""
    def lse(values):
        require(bool(values), "reference reduction needs a positive")
        maximum = max(values)
        return maximum + math.log(math.fsum(math.exp(value - maximum) for value in values))

    def direction(lines):
        losses = []
        for entries in lines:
            numerator = [score for score, positive, _negative, _weight in entries if positive]
            denominator = [score + (math.log(weight) if negative else 0.0)
                           for score, positive, negative, weight in entries if positive or negative]
            losses.append(lse(denominator) - lse(numerator))
        return math.fsum(losses) / len(losses)

    rows = [[(scores[i][j], positives[i][j], negatives[i][j], weights[i][j])
             for j in range(len(scores[0]))] for i in range(len(scores))]
    columns = [[(scores[i][j], positives[i][j], negatives[i][j], weights[i][j])
                for i in range(len(scores))] for j in range(len(scores[0]))]
    return (direction(rows) + direction(columns)) / 2


def _run_checks(torch, masked, legacy, observe):
    checks = {}
    updates = 0
    fixture_model_count = 0
    fixture_parameter_count = 0
    fixture_linear_forward_count = 0
    tau = 0.07

    parity = []
    for dtype in (torch.float32, torch.float64):
        source_values = [[0.4, -0.1, 0.7], [0.2, 0.8, -0.2], [-0.3, 0.5, 0.6]]
        formal_values = [[0.6, 0.1, -0.3], [-0.1, 0.9, 0.4], [0.5, -0.4, 0.7]]
        identities = ["fixture-alpha", "fixture-alpha", "fixture-beta"]
        positives = torch.tensor([[a == b for b in identities] for a in identities], dtype=torch.bool)
        negatives = ~positives
        weights = torch.tensor([[float("nan"), float("nan"), 2.0],
                                [float("nan"), float("nan"), 3.0],
                                [2.0, 3.0, float("nan")]], dtype=dtype)
        old_source = torch.tensor(source_values, dtype=dtype, requires_grad=True)
        old_formal = torch.tensor(formal_values, dtype=dtype, requires_grad=True)
        new_source = torch.tensor(source_values, dtype=dtype, requires_grad=True)
        new_formal = torch.tensor(formal_values, dtype=dtype, requires_grad=True)
        old_loss = legacy.multi_positive_contrastive_loss(
            old_source, old_formal, identities, temperature=tau, hard_negative_weights=weights)
        new_loss = masked.masked_multi_positive_contrastive_loss(
            new_source, new_formal, positive_mask=positives,
            permitted_negative_mask=negatives, temperature=tau, negative_weights=weights)
        old_gradients = torch.autograd.grad(old_loss, (old_source, old_formal))
        new_gradients = torch.autograd.grad(new_loss, (new_source, new_formal))
        require(torch.equal(old_loss, new_loss), "legacy value parity failed")
        require(all(torch.equal(a, b) for a, b in zip(old_gradients, new_gradients, strict=True)),
                "legacy representation-gradient parity failed")
        require(_finite_nonzero(torch, new_gradients), "parity gradients must be finite and nonzero")
        parity.append({"dtype": str(dtype), "legacy_loss": old_loss.item(), "masked_loss": new_loss.item(),
                       "value_bitwise_equal": True, "both_representation_gradients_bitwise_equal": True,
                       "source_gradient_sha256": _tensor_sha256(new_gradients[0]),
                       "formal_gradient_sha256": _tensor_sha256(new_gradients[1]),
                       "positive_pair_count": int(positives.sum()),
                       "permitted_negative_pair_count": int(negatives.sum()),
                       "identity_equality_used_only_for_legacy_numerical_parity_fixture": True})
        observe("legacy_parity_" + str(dtype))
    checks["legacy_parity"] = parity

    source = torch.tensor([[0.1, -0.2], [0.3, 0.4]], dtype=torch.float64, requires_grad=True)
    formal = torch.tensor([[0.5, 0.1], [-0.2, 0.6], [0.2, -0.3]], dtype=torch.float64, requires_grad=True)
    positive = torch.tensor([[True, True, False], [False, False, True]])
    negative = torch.tensor([[False, False, True], [True, False, False]])
    weights = torch.tensor([[float("nan"), float("inf"), 2.0], [3.0, float("nan"), -2.0]], dtype=torch.float64)
    loss = masked.masked_multi_positive_contrastive_loss(
        source, formal, positive_mask=positive, permitted_negative_mask=negative,
        temperature=tau, negative_weights=weights)
    expected = _manual_log_mass((source @ formal.T / tau).detach().tolist(),
                               positive.tolist(), negative.tolist(), weights.tolist())
    require(math.isclose(loss.item(), expected, rel_tol=1e-12, abs_tol=1e-12),
            "rectangular independent reference disagrees")
    gradients = torch.autograd.grad(loss, (source, formal))
    transposed_source = formal.detach().clone().requires_grad_(True)
    transposed_formal = source.detach().clone().requires_grad_(True)
    transposed = masked.masked_multi_positive_contrastive_loss(
        transposed_source, transposed_formal, positive_mask=positive.T,
        permitted_negative_mask=negative.T, temperature=tau, negative_weights=weights.T)
    transposed_gradients = torch.autograd.grad(transposed, (transposed_source, transposed_formal))
    require(torch.equal(loss, transposed), "rectangular direction-swap value parity failed")
    require(torch.allclose(gradients[0], transposed_gradients[1], rtol=1e-12, atol=1e-12)
            and torch.allclose(gradients[1], transposed_gradients[0], rtol=1e-12, atol=1e-12),
            "rectangular direction-swap gradient parity failed")
    require(_finite_nonzero(torch, gradients), "rectangular gradients must be finite and nonzero")
    checks["rectangular_independent_reference"] = {
        "shape": [2, 3], "loss": loss.item(), "python_float_log_mass": expected,
        "absolute_error": abs(loss.item() - expected), "direction_swap_value_bitwise_equal": True,
        "direction_swap_gradients_agree": True,
        "descriptor": masked.describe_masked_contrastive_relations(positive, negative),
        "ignored_nan_inf_negative_weight_entries_sanitized": True,
    }
    observe("rectangular_reference")

    scores = torch.tensor([[0.2, -0.1, 0.7], [0.1, 0.4, -0.2], [-0.6, 0.3, 0.5]], dtype=torch.float64)
    positive = torch.eye(3, dtype=torch.bool)
    negative = torch.tensor([[False, True, False], [True, False, True], [False, True, False]])
    unknown = ~(positive | negative)
    source = torch.eye(3, dtype=torch.float64, requires_grad=True)
    formal = scores.T.clone().requires_grad_(True)
    loss = masked.masked_multi_positive_contrastive_loss(
        source, formal, positive_mask=positive, permitted_negative_mask=negative, temperature=tau)
    source_gradient, formal_gradient = torch.autograd.grad(loss, (source, formal))
    pair_logit_gradient = formal_gradient.T * tau
    require(torch.equal(pair_logit_gradient[unknown], torch.zeros_like(pair_logit_gradient[unknown])),
            "unknown pair-logit gradient is not exactly zero")
    require(bool((pair_logit_gradient[positive] != 0).all())
            and bool((pair_logit_gradient[negative] != 0).all()), "permitted pair signal disappeared")
    require(_finite_nonzero(torch, (source_gradient, formal_gradient)), "isolation fixture gradients invalid")
    perturbed = scores.clone()
    perturbed[0, 2] += 10000.0
    perturbed[2, 0] -= 10000.0
    perturbed_formal = perturbed.T.clone().requires_grad_(True)
    perturbed_loss = masked.masked_multi_positive_contrastive_loss(
        source.detach(), perturbed_formal, positive_mask=positive,
        permitted_negative_mask=negative, temperature=tau)
    perturbed_gradient = torch.autograd.grad(perturbed_loss, perturbed_formal)[0]
    require(torch.equal(loss, perturbed_loss) and torch.equal(formal_gradient, perturbed_gradient),
            "unknown-logit perturbation altered objective or score gradients")
    checks["unknown_pair_gradient_isolation"] = {
        "positive_pair_count": int(positive.sum()), "permitted_negative_pair_count": int(negative.sum()),
        "unknown_pair_count": int(unknown.sum()), "unknown_pair_logit_gradients_exact_zero": True,
        "all_positive_and_permitted_negative_pair_gradients_nonzero": True,
        "unknown_logit_perturbation_magnitude": 10000,
        "perturbation_loss_and_pair_gradients_bitwise_equal": True,
        "loss": loss.item(), "pair_logit_gradient_sha256": _tensor_sha256(pair_logit_gradient),
        "endpoint_gradient_scope": "shared_endpoint_gradients_need_not_vanish_for_an_unknown_pair",
    }
    observe("unknown_pair_isolation")

    source = torch.tensor([[0.1, 0.2], [-0.3, 0.4]], dtype=torch.float64, requires_grad=True)
    formal = torch.tensor([[0.3, -0.1], [0.2, 0.5], [-0.2, 0.6]], dtype=torch.float64, requires_grad=True)
    positive = torch.tensor([[True, True, False], [False, False, True]])
    negative = torch.zeros((2, 3), dtype=torch.bool)
    zero_loss = masked.masked_multi_positive_contrastive_loss(
        source, formal, positive_mask=positive, permitted_negative_mask=negative,
        negative_weights=torch.full((2, 3), float("nan"), dtype=torch.float64))
    zero_gradients = torch.autograd.grad(zero_loss, (source, formal))
    require(zero_loss.item() == 0.0 and all(torch.equal(value, torch.zeros_like(value)) for value in zero_gradients),
            "no-negative case must have exact zero loss and representation gradients")
    descriptor = masked.describe_masked_contrastive_relations(positive, negative)
    require(descriptor["global_no_separation_signal"] is True
            and descriptor["rows_without_permitted_negatives"] == [0, 1]
            and descriptor["columns_without_permitted_negatives"] == [0, 1, 2], "no-signal descriptor disagrees")
    checks["global_no_negative_signal"] = {
        "loss_exact_zero": True, "both_representation_gradients_exact_zero": True,
        "differentiable_connected_zero": zero_loss.requires_grad,
        "ignored_all_nan_weights": True, "descriptor": descriptor,
    }
    observe("global_no_negative_signal")

    source = torch.tensor([[0.1, -0.2], [0.3, 0.2]], dtype=torch.float64, requires_grad=True)
    formal = torch.tensor([[0.4, 0.2], [-0.1, 0.3], [0.2, -0.4]], dtype=torch.float64, requires_grad=True)
    positive = torch.tensor([[True, True, False], [False, False, True]])
    negative = torch.tensor([[False, False, True], [True, False, False]])

    def objective(left, right):
        return masked.masked_multi_positive_contrastive_loss(
            left, right, positive_mask=positive, permitted_negative_mask=negative, temperature=0.3)

    gradcheck_passed = torch.autograd.gradcheck(objective, (source, formal), eps=1e-6,
                                              atol=1e-5, rtol=1e-3, fast_mode=False)
    require(gradcheck_passed is True, "double finite-difference gradcheck failed")
    checks["double_gradcheck"] = {"passed": True, "source_shape": [2, 2], "formal_shape": [3, 2],
                                 "temperature": 0.3, "eps": 1e-6, "atol": 1e-5, "rtol": 1e-3,
                                 "fast_mode": False}
    observe("double_gradcheck")

    head_checks = []
    for shared_dimension in (384, 512):
        heads = legacy.create_projection_heads(384, 27, shared_dimension, seed=1729)
        fixture_model_count += 1
        parameters = dict(heads.named_parameters())
        parameter_count = sum(value.numel() for value in parameters.values())
        fixture_parameter_count += parameter_count
        before = _state_sha256(heads)
        observed_forwards = []
        hooks = [module.register_forward_hook(
            lambda _module, _inputs, _output, observed=observed_forwards: observed.append(True))
            for module in (heads.source_projection, heads.formal_projection)]
        source_inputs = torch.linspace(-0.4, 0.6, 3 * 384, dtype=torch.float32).reshape(3, 384)
        formal_inputs = torch.zeros((3, 27), dtype=torch.float32)
        formal_inputs[0, [0, 4, 8, 12, 16, 20, 24]] = 1
        formal_inputs[1, [1, 5, 9, 13, 17, 21, 25]] = 1
        formal_inputs[2, [2, 6, 10, 14, 18, 22, 26]] = 1
        projected_source = heads.source(source_inputs)
        projected_formal = heads.formal(formal_inputs)
        for hook in hooks:
            hook.remove()
        require(len(observed_forwards) == 2, "fixture linear forward count differs")
        fixture_linear_forward_count += len(observed_forwards)
        source_norms = torch.linalg.vector_norm(projected_source, dim=1)
        formal_norms = torch.linalg.vector_norm(projected_formal, dim=1)
        require(torch.allclose(source_norms, torch.ones_like(source_norms), rtol=1e-6, atol=1e-6)
                and torch.allclose(formal_norms, torch.ones_like(formal_norms), rtol=1e-6, atol=1e-6),
                "legacy head output unit norm differs")
        positive = torch.eye(3, dtype=torch.bool)
        negative = ~positive
        loss = masked.masked_multi_positive_contrastive_loss(
            projected_source, projected_formal, positive_mask=positive,
            permitted_negative_mask=negative, temperature=tau)
        loss.backward()
        source_parameters = [value for name, value in parameters.items() if name.startswith("source_projection.")]
        formal_parameters = [value for name, value in parameters.items() if name.startswith("formal_projection.")]
        require(_finite_nonzero(torch, [value.grad for value in source_parameters])
                and _finite_nonzero(torch, [value.grad for value in formal_parameters]),
                "both untrained projection heads require finite nonzero gradients")
        after = _state_sha256(heads)
        require(before == after, "backward changed parameter or buffer values")
        head_checks.append({
            "shared_dimension": shared_dimension, "source_input_dimension": 384, "formal_input_dimension": 27,
            "parameter_tensor_count": len(parameters), "parameter_scalar_count": parameter_count,
            "initialized_fixture_model": True, "retained_checkpoint_loaded": False, "loss": loss.item(),
            "observed_fixture_linear_forward_count": len(observed_forwards),
            "source_output_max_unit_norm_error": float((source_norms - 1).abs().max()),
            "formal_output_max_unit_norm_error": float((formal_norms - 1).abs().max()),
            "source_parameter_gradients_finite_nonzero": True, "formal_parameter_gradients_finite_nonzero": True,
            "state_sha256_before": before, "state_sha256_after": after,
            "state_hash_scope": "state_dict_parameter_and_buffer_values_excludes_gradient_slots",
            "gradient_sha256": {name: _tensor_sha256(value.grad) for name, value in sorted(parameters.items())},
            "optimizer_updates": 0,
        })
        observe("untrained_shared_head_" + str(shared_dimension))
    checks["untrained_projection_head_backward"] = head_checks

    return {
        "schema": "alignment-masked-contrastive-numerical-checks/v1",
        "fixture_scope": "synthetic_engineering_only_not_historical_train_or_semantic_labels",
        "checks": checks, "all_checks_passed": True,
        "synthetic_untrained_projection_model_count": fixture_model_count,
        "synthetic_untrained_linear_module_count": fixture_model_count * 2,
        "synthetic_initialized_parameter_tensor_count": fixture_model_count * 4,
        "synthetic_initialized_parameter_scalar_count": fixture_parameter_count,
        "observed_fixture_linear_forward_count": fixture_linear_forward_count,
        "production_model_calls": 0,
        "retained_checkpoint_file_inputs": 0, "model_weight_load_calls": 0,
        "historical_training_vector_objective_inputs": 0,
        "actual_numerical_objective_executed": True, "synthetic_backward_executed": True,
        "parameter_initialization_executed": True, "optimizer_updates": updates,
        "encoder_calls": 0, "prover_calls": 0, "semantic_fit_updates": 0,
        "masks": dict.fromkeys(MASK_NAMES, 0), **FALSE_FLAGS,
        "legacy_sampler_finding": {
            "verification_scope": "read_only_static_source_review_not_executed_by_this_assay",
            "owner_role": "legacy_relation_configuration_source_only",
            "function": "filter_false_negatives",
            "counterexample": {
                "records": [{"record_id": "left", "lineage_id": "distinct-A", "pair_ids": [], "false_negative_class": ""},
                            {"record_id": "right", "lineage_id": "distinct-B", "pair_ids": [], "false_negative_class": ""}],
                "admissions": [{"left_id": "left", "right_id": "right", "pair_class": "positive", "admitted": True}],
                "source_implied_kept_negative_ids": ["right"],
            },
            "reason": "admitted_pair_ids_are_built_without_pair_class_filter",
            "normalized_cosine_observation": "all_admitted_classes_are_used_without_pair_class_filter",
            "legacy_owner_modified": False, "new_masked_loss_uses_legacy_sampler": False,
        },
        "finite_gradient_scope": "observed_declared_bounded_fixtures_not_all_finite_forward_inputs_or_temperatures",
    }


def prepare_numerical_assay(repository_root=None, *, observe=None):
    """Run detached deterministic synthetic checks without writing files.

    The caller supplies any observation callback. Repository namespace bootstrap
    imports the two exact numerical owners only; no package initializer runs.
    Every numerical value is constructed here, including untrained head states.
    The caller must establish one CPU and interop thread before numerical work;
    this helper does not mutate the caller's global thread settings.
    """
    repo = Path(repository_root).resolve() if repository_root is not None else REPOSITORY
    before_bindings = implementation_bindings(repo)
    _namespace(repo)
    import torch

    from ipfs_datasets_py.logic.formalization.autoencoder import (
        alignment_masked_contrastive as masked,
    )
    from ipfs_datasets_py.logic.formalization.autoencoder import alignment_projection as legacy

    require(torch.get_num_threads() == torch.get_num_interop_threads() == 1,
            "one CPU and interop thread must be configured before numerical replay")
    require(Path(masked.__file__).resolve() == Path(before_bindings["masked_owner"]["path"])
            and Path(legacy.__file__).resolve() == Path(before_bindings["legacy_projection_owner"]["path"]),
            "loaded numerical owner paths differ from selected implementation bindings")
    callback = observe if observe is not None else lambda _label: None
    original_rng = torch.get_rng_state().clone()
    with torch.random.fork_rng(devices=[]):
        torch.random.default_generator.manual_seed(1729)
        result = _run_checks(torch, masked, legacy, callback)
    require(torch.equal(original_rng, torch.get_rng_state()), "synthetic checks changed global CPU RNG")
    result["global_cpu_rng_unchanged"] = True
    result["rng_scope"] = "fork_rng_cpu_devices_empty_seed1729_restores_caller_state"
    result["torch_version"] = torch.__version__
    result["device"] = "cpu"
    result["threads"] = torch.get_num_threads()
    result["interop_threads"] = torch.get_num_interop_threads()
    after_bindings = implementation_bindings(repo)
    require(before_bindings == after_bindings, "implementation files changed during numerical replay")
    result["implementation_bindings"] = before_bindings
    result["implementation_files_unchanged"] = True
    return sealed(result)


def _linux_resource():
    values = {}
    for line in Path("/proc/self/status").read_text(encoding="utf-8").splitlines():
        name, _, value = line.partition(":")
        if name in ("VmRSS", "VmHWM", "VmSize"):
            parts = value.split()
            require(len(parts) == 2 and parts[1] == "kB", "Linux memory unit differs")
            values[name] = int(parts[0])
    usage = resource.getrusage(resource.RUSAGE_SELF)
    return {"linux_current_rss_kib": values["VmRSS"], "linux_peak_hwm_kib": values["VmHWM"],
            "linux_virtual_size_kib": values["VmSize"], "resource_ru_maxrss_kib": usage.ru_maxrss,
            "user_cpu_seconds": usage.ru_utime, "system_cpu_seconds": usage.ru_stime}


def _write_new(path, value):
    payload = raw(value) + b"\n"
    require(len(payload) <= MAX_OUTPUT_BYTES, "bounded diagnostic output required")
    descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(descriptor, "wb") as stream:
        stream.write(payload)
        stream.flush()
        os.fsync(stream.fileno())


class _NoEncoderImports(importlib.abc.MetaPathFinder):
    def __init__(self):
        self.attempts = []

    def find_spec(self, fullname, path=None, target=None):
        if fullname.split(".", 1)[0] in FORBIDDEN_IMPORTS:
            self.attempts.append(fullname)
            raise ImportError("encoder/prover imports prohibited in synthetic numerical assay: " + fullname)
        return None


def _worker(output, repository_root):
    resource.setrlimit(resource.RLIMIT_CPU, (CPU_SOFT_SECONDS, CPU_HARD_SECONDS))
    resource.setrlimit(resource.RLIMIT_CORE, (0, 0))
    resource.setrlimit(resource.RLIMIT_FSIZE, (MAX_OUTPUT_BYTES, MAX_OUTPUT_BYTES))
    started = time.monotonic()
    observations = []
    journal_path = output / "resource_observations.jsonl"
    journal_descriptor = os.open(journal_path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)

    def observe(label):
        row = {"label": label, "elapsed_wall_seconds": time.monotonic() - started,
               "measurement_scope": "fresh_forked_cpu_worker", **_linux_resource()}
        observations.append(row)
        os.write(journal_descriptor, raw(row) + b"\n")
        os.fsync(journal_descriptor)
        require(max(row["linux_current_rss_kib"], row["linux_peak_hwm_kib"], row["resource_ru_maxrss_kib"])
                < MAX_RSS_KIB, "cooperative resident-memory admission exceeded 2GiB")
        require(row["elapsed_wall_seconds"] < WALL_SECONDS, "worker wall admission exceeded")

    guard = _NoEncoderImports()
    sys.meta_path.insert(0, guard)
    load_attempts = []
    try:
        observe("before_torch_import")
        import torch

        torch.set_num_threads(1)
        torch.set_num_interop_threads(1)
        require(not torch.cuda.is_initialized(), "CUDA runtime initialized")

        def no_load(*_args, **_kwargs):
            load_attempts.append("torch_model_checkpoint_or_hub_load")
            raise ValueError("checkpoint/model loading prohibited in synthetic assay")

        torch.load = no_load
        torch.hub.load = no_load
        torch.hub.load_state_dict_from_url = no_load
        observe("after_torch_import")
        checks = prepare_numerical_assay(repository_root, observe=observe)
        require(not load_attempts and not guard.attempts and not torch.cuda.is_initialized(),
                "forbidden loading, imports or CUDA execution observed")
        observe("after_all_numerical_checks")
        os.close(journal_descriptor)
        journal_descriptor = None
        report = sealed({
            "schema": "alignment-masked-contrastive-numerical-assay/v1",
            "status": "completed_synthetic_engineering_checks_no_training_admission",
            "created_utc": datetime.now(UTC).isoformat(), "checks": checks,
            "resource_observations": observations, "resource_journal_binding": binding(journal_path),
            "resource_limits": {"cpu_soft_seconds": CPU_SOFT_SECONDS, "cpu_hard_seconds": CPU_HARD_SECONDS,
                                "parent_wall_seconds": WALL_SECONDS, "cooperative_rss_kib": MAX_RSS_KIB,
                                "rlimit_address_space_enforced": False,
                                "address_space_reason": "CUDA_linked_Torch_virtual_reservation_is_not_resident_model_weights",
                                "max_output_file_bytes": MAX_OUTPUT_BYTES},
            "native_python": sys.executable, "CUDA_VISIBLE_DEVICES": os.environ.get("CUDA_VISIBLE_DEVICES"),
            "thread_environment": {name: os.environ.get(name) for name in
                                   ("OMP_NUM_THREADS", "MKL_NUM_THREADS", "OPENBLAS_NUM_THREADS")},
            "model_checkpoint_load_attempts": load_attempts, "forbidden_import_attempts": guard.attempts,
            "cuda_initialized": False, "trusted_resource_bounded_child": True,
            "masks": dict.fromkeys(MASK_NAMES, 0), **FALSE_FLAGS,
        })
        _write_new(output / "numerical_assay.json", report)
        return 0
    except BaseException as error:
        failure = {"schema": "alignment-masked-contrastive-numerical-failure/v1",
                   "status": "failed_no_training_admission", "error_type": type(error).__name__,
                   "error_message": str(error), "resource_observations": observations,
                   "model_checkpoint_load_attempts": load_attempts, "forbidden_import_attempts": guard.attempts,
                   "optimizer_updates": 0, "masks": dict.fromkeys(MASK_NAMES, 0), **FALSE_FLAGS}
        _write_new(output / "failure.json", sealed(failure))
        traceback.print_exc()
        return 1
    finally:
        if journal_descriptor is not None:
            os.close(journal_descriptor)


def _fresh_worker(output, repository_root):
    # Linux ru_maxrss may carry pre-exec high-water accounting into the launcher.
    # Fork before Torch import so the assayed worker starts its own RSS/HWM scope.
    worker_pid = os.fork()
    if worker_pid == 0:
        os._exit(_worker(output, repository_root))
    _pid, status = os.waitpid(worker_pid, 0)
    if os.WIFEXITED(status):
        return os.WEXITSTATUS(status)
    return 128 + os.WTERMSIG(status)


def run_bounded(output_directory=DEFAULT_OUTPUT, repository_root=REPOSITORY):
    """Publish one fresh child-run engineering receipt; never overwrite outputs."""
    output = Path(output_directory).resolve()
    require(not output.exists(), "fresh numerical output directory required")
    output.parent.mkdir(parents=True, exist_ok=True)
    output.mkdir(mode=0o700)
    before = implementation_bindings(repository_root)
    environment = {
        "PATH": "/usr/local/bin:/usr/bin:/bin", "LANG": "C.UTF-8",
        "CUDA_VISIBLE_DEVICES": "", "OMP_NUM_THREADS": "1", "MKL_NUM_THREADS": "1",
        "OPENBLAS_NUM_THREADS": "1", "PYTHONDONTWRITEBYTECODE": "1",
        "IPFS_DATASETS_AUTO_INSTALL_TEST_DEPS": "0", "PYTEST_DISABLE_PLUGIN_AUTOLOAD": "1",
    }
    command = [str(NATIVE_PYTHON), "-I", "-B", str(Path(__file__).resolve()), "--worker",
               "--output-directory", str(output), "--repository-root", str(Path(repository_root).resolve())]
    process = subprocess.Popen(command, cwd=output, env=environment, stdout=subprocess.PIPE,
                               stderr=subprocess.PIPE, start_new_session=True)
    try:
        stdout, stderr = process.communicate(timeout=WALL_SECONDS)
    except subprocess.TimeoutExpired:
        os.killpg(process.pid, signal.SIGKILL)
        stdout, stderr = process.communicate()
        _write_new(output / "parent_timeout.json", sealed({
            "status": "parent_wall_timeout", "wall_seconds": WALL_SECONDS,
            "process_group_killed": True, "optimizer_updates": 0, **FALSE_FLAGS,
        }))
        raise TimeoutError("synthetic numerical worker exceeded parent wall limit") from None
    _write_new(output / "child_exit.json", sealed({
        "status": "completed" if process.returncode == 0 else "failed",
        "command": command, "returncode": process.returncode,
        "stdout_utf8": stdout[:65536].decode("utf-8", errors="replace"),
        "stderr_utf8": stderr[:65536].decode("utf-8", errors="replace"),
        "stdout_bytes": len(stdout), "stderr_bytes": len(stderr),
        "implementation_bindings": before, "optimizer_updates": 0,
        "masks": dict.fromkeys(MASK_NAMES, 0), **FALSE_FLAGS,
    }))
    require(process.returncode == 0, "bounded numerical child failed; preserved diagnostic files")
    require(before == implementation_bindings(repository_root), "implementation changed during bounded child execution")
    report_path = output / "numerical_assay.json"
    report = json.loads(report_path.read_text(encoding="utf-8"))
    require(report["content_sha256"] == digest({name: value for name, value in report.items() if name != "content_sha256"}),
            "numerical report seal differs")
    require(report["checks"]["all_checks_passed"] is True and report["checks"]["optimizer_updates"] == 0,
            "numerical report must pass without updates")
    return {"report_binding": binding(report_path), "child_exit_binding": binding(output / "child_exit.json"),
            "status": report["status"]}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-directory", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--repository-root", type=Path, default=REPOSITORY)
    parser.add_argument("--worker", action="store_true")
    arguments = parser.parse_args()
    if arguments.worker:
        raise SystemExit(_fresh_worker(arguments.output_directory.resolve(), arguments.repository_root.resolve()))
    print(json.dumps(run_bounded(arguments.output_directory, arguments.repository_root), sort_keys=True))


if __name__ == "__main__":
    main()
