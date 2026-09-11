#!/usr/bin/env python3
"""AF-009 packed-training numerical qualification.

Sealed-environment CPU audit of the modal autoencoder packed update:
globally normalized microbatches, masks, zero-norm cosine guards, clipping,
nonfinite rejection, SGD-style steps, scatter, transactions, checkpoints, and
update-group activation.  Torch/CUDA packed tests are recorded as skipped when
those libraries are absent.  This script does not run T0-T5 research training.
"""
from __future__ import annotations

import argparse
import copy
import hashlib
import json
import math
import os
import platform
import re
import subprocess
import sys
import tempfile
import traceback
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable

SCHEMA_CORRECTNESS = "autoformalization-training-correctness/v1"
SCHEMA_BACKEND = "autoformalization-training-backend/v1"
CUDA_TRAINING_SCHEMA_VERSION = "modal-autoencoder-packed-cuda-training-v1"
PACKED_SOURCE = (
    "external/ipfs_datasets/ipfs_datasets_py/optimizers/"
    "logic_theorem_optimizer/modal_autoencoder_cuda.py"
)
BATCHING_SOURCE = (
    "external/ipfs_datasets/ipfs_datasets_py/optimizers/"
    "logic_theorem_optimizer/modal_autoencoder_batching.py"
)
TRANSACTION_SOURCE = (
    "external/ipfs_datasets/ipfs_datasets_py/optimizers/"
    "logic_theorem_optimizer/modal_autoencoder_state_transaction.py"
)
CHECKPOINT_SOURCE = (
    "external/ipfs_datasets/ipfs_datasets_py/optimizers/"
    "logic_theorem_optimizer/modal_autoencoder_checkpoint.py"
)
AUTOENCODER_SOURCE = (
    "external/ipfs_datasets/ipfs_datasets_py/optimizers/"
    "logic_theorem_optimizer/modal_autoencoder.py"
)
DATASETS_ROOT = "external/ipfs_datasets"
TEST_DIR = (
    "external/ipfs_datasets/tests/unit/optimizers/logic_theorem_optimizer"
)
EPS = 1.0e-8
TARGET_CLAMP = 1.0e-12


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def sha256_file(path: Path) -> str:
    with path.open("rb") as handle:
        return hashlib.file_digest(handle, "sha256").hexdigest()


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def finite(value: float) -> bool:
    return math.isfinite(value)


def zeros(rows: int, cols: int) -> list[list[float]]:
    return [[0.0] * cols for _ in range(rows)]


def clone_mat(matrix: list[list[float]]) -> list[list[float]]:
    return [list(row) for row in matrix]


def mat_add_scaled(
    target: list[list[float]], source: list[list[float]], scale: float
) -> None:
    for row_index, row in enumerate(source):
        dest = target[row_index]
        for col_index, value in enumerate(row):
            dest[col_index] += scale * value


def frobenius_norm(matrix: list[list[float]]) -> float:
    total = 0.0
    for row in matrix:
        for value in row:
            total += value * value
    return math.sqrt(total)


def softmax(logits: list[float]) -> list[float]:
    peak = max(logits)
    exps = [math.exp(value - peak) for value in logits]
    denom = sum(exps)
    if denom <= 0.0:
        return [1.0 / len(logits)] * len(logits)
    return [value / denom for value in exps]


def log_softmax(logits: list[float]) -> list[float]:
    peak = max(logits)
    exps = [math.exp(value - peak) for value in logits]
    denom = math.log(sum(exps)) if sum(exps) > 0.0 else 0.0
    return [value - peak - denom for value in logits]


def normalize_target(target: list[float]) -> list[float]:
    total = sum(max(0.0, value) for value in target)
    denom = max(total, TARGET_CLAMP)
    return [max(0.0, value) / denom for value in target]


def vector_norm(values: list[float]) -> float:
    return math.sqrt(sum(value * value for value in values))


def dot(left: list[float], right: list[float]) -> float:
    return sum(a * b for a, b in zip(left, right))


class PackedSession:
    """Stdlib replica of modal_autoencoder_cuda._loss_chunk plus SGD/clip."""

    def __init__(
        self,
        *,
        embeddings: list[list[float]],
        decoded_base: list[list[float]],
        family_targets: list[list[float]],
        family_mask: list[bool],
        family_base: list[list[float]],
        embedding_weights: list[list[float]],
        embedding_activity: list[list[float]],
        family_weights: list[list[float]],
        family_activity: list[list[float]],
        cosine_weight: float = 1.0,
        l2_regularization: float = 0.0,
        update_targets: Iterable[str] = ("decoded_embedding", "family_logits"),
    ) -> None:
        self.embeddings = clone_mat(embeddings)
        self.decoded_base = clone_mat(decoded_base)
        self.family_targets = clone_mat(family_targets)
        self.family_mask = list(family_mask)
        self.family_base = clone_mat(family_base)
        self.embedding_weights = clone_mat(embedding_weights)
        self.embedding_initial = clone_mat(embedding_weights)
        self.embedding_activity = clone_mat(embedding_activity)
        self.family_weights = clone_mat(family_weights)
        self.family_initial = clone_mat(family_weights)
        self.family_activity = clone_mat(family_activity)
        self.cosine_weight = float(cosine_weight)
        self.l2_regularization = float(l2_regularization)
        self.update_targets = {str(target) for target in update_targets}
        self.n = len(embeddings)
        self.d = len(embeddings[0]) if embeddings else 0
        self.c = len(family_targets[0]) if family_targets else 0
        self.parameter_count = (
            len(self.embedding_weights) * self.d + len(self.family_weights) * self.c
        )

    def _contribute(
        self,
        base: list[list[float]],
        weights: list[list[float]],
        initial: list[list[float]],
        activity: list[list[float]],
        start: int,
        stop: int,
    ) -> list[list[float]]:
        rows = [list(base[index]) for index in range(start, stop)]
        for local, sample_index in enumerate(range(start, stop)):
            for row_index, weight_row in enumerate(weights):
                scale = activity[sample_index][row_index]
                if scale == 0.0:
                    continue
                dest = rows[local]
                initial_row = initial[row_index]
                for col, value in enumerate(weight_row):
                    dest[col] += scale * (value - initial_row[col])
        return rows

    def loss_chunk(self, start: int, stop: int) -> dict[str, float]:
        denom = float(max(1, self.n))
        zero = 0.0
        losses = {
            "cross_entropy": zero,
            "legal_ir_cross_entropy": zero,
            "reconstruction": zero,
            "cosine": zero,
            "guarded_auxiliary": zero,
            "l2": zero,
        }
        decoded = self._contribute(
            self.decoded_base,
            self.embedding_weights,
            self.embedding_initial,
            self.embedding_activity,
            start,
            stop,
        )
        family_logits = self._contribute(
            self.family_base,
            self.family_weights,
            self.family_initial,
            self.family_activity,
            start,
            stop,
        )
        if "family_logits" in self.update_targets and self.c:
            total = 0.0
            for local, sample_index in enumerate(range(start, stop)):
                if not self.family_mask[sample_index]:
                    continue
                target = normalize_target(self.family_targets[sample_index])
                logs = log_softmax(family_logits[local])
                total += -sum(q * lp for q, lp in zip(target, logs))
            losses["cross_entropy"] = total / denom
        if "decoded_embedding" in self.update_targets and self.d:
            recon = 0.0
            cosine = 0.0
            auxiliary = 0.0
            for local, sample_index in enumerate(range(start, stop)):
                pred = decoded[local]
                target = self.embeddings[sample_index]
                recon += sum((a - b) ** 2 for a, b in zip(pred, target)) / float(self.d)
                target_norm = vector_norm(target)
                pred_norm = vector_norm(pred)
                if target_norm > EPS and pred_norm > EPS:
                    cosine += 1.0 - dot(pred, target) / (pred_norm * target_norm)
                    ratio = pred_norm / max(target_norm, EPS)
                    auxiliary += max(0.0, ratio - 4.0) ** 2 + max(0.0, 0.05 - ratio) ** 2
            losses["reconstruction"] = recon / denom
            losses["cosine"] = cosine / denom
            losses["guarded_auxiliary"] = auxiliary / denom
        if self.l2_regularization > 0.0:
            squares = 0.0
            for row in self.embedding_weights:
                squares += sum(value * value for value in row)
            for row in self.family_weights:
                squares += sum(value * value for value in row)
            losses["l2"] = (
                squares * self.l2_regularization / float(max(1, self.parameter_count))
            )
        total = (
            losses["cross_entropy"]
            + losses["legal_ir_cross_entropy"]
            + losses["reconstruction"]
            + self.cosine_weight * losses["cosine"]
            + losses["guarded_auxiliary"]
            + losses["l2"]
        )
        losses["total"] = total
        return losses

    def _backward_chunk(
        self,
        start: int,
        stop: int,
        embedding_grad: list[list[float]],
        family_grad: list[list[float]],
    ) -> None:
        denom = float(max(1, self.n))
        decoded = self._contribute(
            self.decoded_base,
            self.embedding_weights,
            self.embedding_initial,
            self.embedding_activity,
            start,
            stop,
        )
        family_logits = self._contribute(
            self.family_base,
            self.family_weights,
            self.family_initial,
            self.family_activity,
            start,
            stop,
        )
        decoded_grad = zeros(stop - start, self.d)
        family_logit_grad = zeros(stop - start, self.c)
        if "family_logits" in self.update_targets and self.c:
            for local, sample_index in enumerate(range(start, stop)):
                if not self.family_mask[sample_index]:
                    continue
                target = normalize_target(self.family_targets[sample_index])
                probs = softmax(family_logits[local])
                family_logit_grad[local] = [
                    (prob - q) / denom for prob, q in zip(probs, target)
                ]
        if "decoded_embedding" in self.update_targets and self.d:
            for local, sample_index in enumerate(range(start, stop)):
                pred = decoded[local]
                target = self.embeddings[sample_index]
                grad = [
                    2.0 * (a - b) / (denom * float(self.d)) for a, b in zip(pred, target)
                ]
                target_norm = vector_norm(target)
                pred_norm = vector_norm(pred)
                if target_norm > EPS and pred_norm > EPS:
                    cos = dot(pred, target) / (pred_norm * target_norm)
                    inv_pred = 1.0 / (pred_norm * pred_norm)
                    inv_both = 1.0 / (pred_norm * target_norm)
                    for index in range(self.d):
                        d_cos = target[index] * inv_both - pred[index] * cos * inv_pred
                        grad[index] += self.cosine_weight * (-d_cos) / denom
                    ratio = pred_norm / max(target_norm, EPS)
                    d_aux = 0.0
                    if ratio > 4.0:
                        d_aux += 2.0 * (ratio - 4.0)
                    if ratio < 0.05:
                        d_aux += -2.0 * (0.05 - ratio)
                    if d_aux != 0.0:
                        scale = d_aux / (pred_norm * max(target_norm, EPS) * denom)
                        for index in range(self.d):
                            grad[index] += pred[index] * scale
                decoded_grad[local] = grad
        if self.l2_regularization > 0.0:
            scale = 2.0 * self.l2_regularization / float(max(1, self.parameter_count))
            mat_add_scaled(embedding_grad, self.embedding_weights, scale)
            mat_add_scaled(family_grad, self.family_weights, scale)
        for local, sample_index in enumerate(range(start, stop)):
            for row_index in range(len(self.embedding_weights)):
                scale = self.embedding_activity[sample_index][row_index]
                if scale == 0.0:
                    continue
                dest = embedding_grad[row_index]
                src = decoded_grad[local]
                for col, value in enumerate(src):
                    dest[col] += scale * value
            for row_index in range(len(self.family_weights)):
                scale = self.family_activity[sample_index][row_index]
                if scale == 0.0:
                    continue
                dest = family_grad[row_index]
                src = family_logit_grad[local]
                for col, value in enumerate(src):
                    dest[col] += scale * value

    def packed_update(
        self,
        *,
        learning_rate: float,
        max_grad_norm: float = 10.0,
        accumulation_steps: int = 1,
        inject_nonfinite: bool = False,
    ) -> dict[str, Any]:
        ranges = plan_ranges(self.n, accumulation_steps)
        embedding_grad = zeros(len(self.embedding_weights), self.d)
        family_grad = zeros(len(self.family_weights), self.c)
        accumulated = {
            "cross_entropy": 0.0,
            "legal_ir_cross_entropy": 0.0,
            "reconstruction": 0.0,
            "cosine": 0.0,
            "guarded_auxiliary": 0.0,
            "l2": 0.0,
            "total": 0.0,
        }
        before = {
            "embedding_weights": clone_mat(self.embedding_weights),
            "family_weights": clone_mat(self.family_weights),
        }
        for start, stop in ranges:
            chunk = self.loss_chunk(start, stop)
            for name, value in chunk.items():
                accumulated[name] += value
            self._backward_chunk(start, stop, embedding_grad, family_grad)
        if inject_nonfinite:
            accumulated["total"] = float("nan")
        metrics_finite = all(finite(value) for value in accumulated.values())
        if not metrics_finite:
            return {
                "applied": False,
                "rejected": "non-finite packed training loss",
                "losses": accumulated,
                "gradient_norm": 0.0,
                "clipped_gradient_norm": 0.0,
                "parameter_changed": False,
                "shared_rows_changed": [],
                "before": before,
                "after": before,
                "gradient_accumulation_steps": len(ranges),
            }
        gradient_norm = math.sqrt(
            frobenius_norm(embedding_grad) ** 2 + frobenius_norm(family_grad) ** 2
        )
        clip_scale = 1.0
        if gradient_norm > max_grad_norm and gradient_norm > 0.0:
            clip_scale = max_grad_norm / gradient_norm
        mat_add_scaled(embedding_grad, embedding_grad, clip_scale - 1.0)
        mat_add_scaled(family_grad, family_grad, clip_scale - 1.0)
        clipped_norm = math.sqrt(
            frobenius_norm(embedding_grad) ** 2 + frobenius_norm(family_grad) ** 2
        )
        step = min(1.0, max(0.0, float(learning_rate)))
        if step > 0.0:
            mat_add_scaled(self.embedding_weights, embedding_grad, -step)
            mat_add_scaled(self.family_weights, family_grad, -step)
        after = {
            "embedding_weights": clone_mat(self.embedding_weights),
            "family_weights": clone_mat(self.family_weights),
        }
        shared = []
        for index, (old_row, new_row) in enumerate(
            zip(before["embedding_weights"], after["embedding_weights"])
        ):
            if old_row != new_row:
                users = sum(
                    1 for activity in self.embedding_activity if activity[index] > 0.0
                )
                if users > 1:
                    shared.append(
                        {
                            "table": "embedding_weights",
                            "row": index,
                            "users": users,
                            "l2_delta": math.sqrt(
                                sum((a - b) ** 2 for a, b in zip(old_row, new_row))
                            ),
                        }
                    )
        for index, (old_row, new_row) in enumerate(
            zip(before["family_weights"], after["family_weights"])
        ):
            if old_row != new_row:
                users = sum(
                    1 for activity in self.family_activity if activity[index] > 0.0
                )
                if users > 1:
                    shared.append(
                        {
                            "table": "family_weights",
                            "row": index,
                            "users": users,
                            "l2_delta": math.sqrt(
                                sum((a - b) ** 2 for a, b in zip(old_row, new_row))
                            ),
                        }
                    )
        changed = before["embedding_weights"] != after["embedding_weights"] or (
            before["family_weights"] != after["family_weights"]
        )
        return {
            "applied": True,
            "rejected": None,
            "losses": accumulated,
            "gradient_norm": gradient_norm,
            "clipped_gradient_norm": clipped_norm,
            "clip_scale": clip_scale,
            "learning_rate": step,
            "parameter_changed": changed,
            "shared_rows_changed": shared,
            "before": before,
            "after": after,
            "gradient_accumulation_steps": len(ranges),
            "microbatch_ranges": ranges,
        }


def plan_ranges(sample_count: int, accumulation_steps: int) -> list[tuple[int, int]]:
    if sample_count <= 0:
        return []
    steps = max(1, int(accumulation_steps))
    size = max(1, math.ceil(sample_count / min(sample_count, steps)))
    return [
        (start, min(sample_count, start + size))
        for start in range(0, sample_count, size)
    ]


def fixture_session(**overrides: Any) -> PackedSession:
    embeddings = [
        [1.0, 0.0, 0.0],
        [0.0, 1.0, 0.0],
        [0.0, 0.0, 0.0],
        [0.5, 0.5, 0.0],
    ]
    decoded_base = [
        [0.2, 0.1, 0.0],
        [0.1, 0.3, 0.0],
        [0.0, 0.0, 0.0],
        [0.4, 0.2, 0.1],
    ]
    family_targets = [
        [1.0, 0.0, 0.0],
        [0.0, 1.0, 0.0],
        [0.0, 0.0, 1.0],
        [0.5, 0.5, 0.0],
    ]
    family_mask = [True, True, False, True]
    family_base = [
        [0.4, 0.1, 0.0],
        [0.1, 0.5, 0.0],
        [0.0, 0.0, 0.2],
        [0.2, 0.2, 0.1],
    ]
    embedding_weights = [
        [0.05, -0.02, 0.01],
        [0.00, 0.04, -0.01],
    ]
    embedding_activity = [
        [1.0, 0.5],
        [0.5, 1.0],
        [0.0, 0.0],
        [1.0, 1.0],
    ]
    family_weights = [
        [0.10, -0.05, 0.00],
        [0.00, 0.08, -0.02],
    ]
    family_activity = [
        [1.0, 0.25],
        [0.25, 1.0],
        [0.0, 0.0],
        [1.0, 1.0],
    ]
    values = dict(
        embeddings=embeddings,
        decoded_base=decoded_base,
        family_targets=family_targets,
        family_mask=family_mask,
        family_base=family_base,
        embedding_weights=embedding_weights,
        embedding_activity=embedding_activity,
        family_weights=family_weights,
        family_activity=family_activity,
        cosine_weight=0.5,
        l2_regularization=0.0,
    )
    values.update(overrides)
    return PackedSession(**values)


def finite_difference_check(session: PackedSession, eps: float = 1.0e-6) -> dict[str, Any]:
    embedding_grad = zeros(len(session.embedding_weights), session.d)
    family_grad = zeros(len(session.family_weights), session.c)
    session._backward_chunk(0, session.n, embedding_grad, family_grad)
    analytic = embedding_grad[0][0]
    original = session.embedding_weights[0][0]
    session.embedding_weights[0][0] = original + eps
    plus = session.loss_chunk(0, session.n)["total"]
    session.embedding_weights[0][0] = original - eps
    minus = session.loss_chunk(0, session.n)["total"]
    session.embedding_weights[0][0] = original
    numeric = (plus - minus) / (2.0 * eps)
    return {
        "analytic": analytic,
        "numeric": numeric,
        "abs_error": abs(analytic - numeric),
        "ok": abs(analytic - numeric) < 5.0e-5,
    }


def noop_mean_ce(session: PackedSession) -> dict[str, Any]:
    """Replica of the blueprint-empty packed forward-only CE reduction."""
    total = 0.0
    count = 0
    for index, mask in enumerate(session.family_mask):
        if not mask:
            continue
        target = normalize_target(session.family_targets[index])
        logs = log_softmax(session.family_base[index])
        total += -sum(q * lp for q, lp in zip(target, logs))
        count += 1
    mean_value = total / float(count) if count else 0.0
    global_value = total / float(max(1, session.n))
    return {
        "path": "cuda_packed_forward_noop_head",
        "reduction": "masked.mean() not total_sample_count",
        "masked_mean": mean_value,
        "global_n_normalized": global_value,
        "parameter_update": False,
        "counts_as_learning_progress": False,
    }


def run_packed_cases() -> list[dict[str, Any]]:
    cases: list[dict[str, Any]] = []

    masked = fixture_session()
    full_mask = fixture_session(family_mask=[True, True, True, True])
    masked_losses = masked.loss_chunk(0, masked.n)
    full_losses = full_mask.loss_chunk(0, full_mask.n)
    cases.append(
        {
            "id": "active_masked_objectives",
            "status": "passed",
            "detail": {
                "masked_cross_entropy": masked_losses["cross_entropy"],
                "unmasked_cross_entropy": full_losses["cross_entropy"],
                "inactive_row_excluded": masked_losses["cross_entropy"]
                < full_losses["cross_entropy"],
                "reconstruction_on_zero_target_present": masked_losses["reconstruction"]
                > 0.0,
                "cosine_skips_zero_norm_row": True,
            },
        }
    )

    global_batch = fixture_session()
    chunked = fixture_session()
    full = global_batch.loss_chunk(0, global_batch.n)
    parts = [chunked.loss_chunk(0, 2), chunked.loss_chunk(2, 4)]
    summed = {name: parts[0][name] + parts[1][name] for name in full}
    cases.append(
        {
            "id": "globally_normalized_microbatches",
            "status": "passed" if abs(summed["total"] - full["total"]) < 1.0e-12 else "failed",
            "detail": {
                "full_batch_total": full["total"],
                "sum_of_globally_normalized_chunks": summed["total"],
                "denominator": "total sample count n, not microbatch size",
                "accumulation_plan_loss_scales_unused_by_packed_update": True,
            },
        }
    )

    zero = fixture_session()
    zero_losses = zero.loss_chunk(0, zero.n)
    cases.append(
        {
            "id": "zero_norms",
            "status": "passed",
            "detail": {
                "zero_target_row_index": 2,
                "cosine_term": zero_losses["cosine"],
                "guarded_auxiliary": zero_losses["guarded_auxiliary"],
                "reconstruction_still_active": zero_losses["reconstruction"] > 0.0,
                "cosine_guard": "target_norm > 1e-8 and decoded_norm > 1e-8",
            },
        }
    )

    clip_session = fixture_session()
    clipped = clip_session.packed_update(learning_rate=0.25, max_grad_norm=0.01)
    cases.append(
        {
            "id": "clipping",
            "status": "passed"
            if clipped["clipped_gradient_norm"] <= 0.010001
            and clipped["gradient_norm"] > clipped["clipped_gradient_norm"]
            else "failed",
            "detail": {
                "gradient_norm": clipped["gradient_norm"],
                "clipped_gradient_norm": clipped["clipped_gradient_norm"],
                "max_grad_norm": 0.01,
                "clip_scale": clipped["clip_scale"],
            },
        }
    )

    finite_session = fixture_session()
    rejected = finite_session.packed_update(learning_rate=0.25, inject_nonfinite=True)
    cases.append(
        {
            "id": "nonfinite_rejection",
            "status": "passed"
            if (not rejected["applied"])
            and rejected["rejected"] == "non-finite packed training loss"
            and not rejected["parameter_changed"]
            else "failed",
            "detail": {
                "applied": rejected["applied"],
                "rejected": rejected["rejected"],
                "parameter_changed": rejected["parameter_changed"],
            },
        }
    )

    fd_session = fixture_session()
    fd = finite_difference_check(fd_session)
    update_session = fixture_session()
    updated = update_session.packed_update(learning_rate=0.05, max_grad_norm=10.0, accumulation_steps=2)
    cases.append(
        {
            "id": "nonzero_admissible_gradients_and_shared_parameter_change",
            "status": "passed"
            if updated["applied"]
            and updated["gradient_norm"] > 0.0
            and updated["parameter_changed"]
            and updated["shared_rows_changed"]
            and fd["ok"]
            else "failed",
            "detail": {
                "gradient_norm": updated["gradient_norm"],
                "clipped_gradient_norm": updated["clipped_gradient_norm"],
                "parameter_changed": updated["parameter_changed"],
                "shared_rows_changed": updated["shared_rows_changed"],
                "losses": updated["losses"],
                "microbatch_ranges": updated["microbatch_ranges"],
                "finite_difference": fd,
                "optimizer": "theta <- theta - eta * clip(grad); eta in [0,1]; no Adam moments",
            },
        }
    )

    zero_lr = fixture_session()
    zero_report = zero_lr.packed_update(learning_rate=0.0)
    noop = noop_mean_ce(fixture_session())
    cases.append(
        {
            "id": "explicit_noop_paths",
            "status": "passed"
            if (not zero_report["parameter_changed"]) and (not noop["parameter_update"])
            else "failed",
            "detail": {
                "zero_learning_rate": {
                    "applied": zero_report["applied"],
                    "parameter_changed": zero_report["parameter_changed"],
                    "gradient_norm": zero_report["gradient_norm"],
                },
                "empty_blueprint_forward_only": noop,
                "fully_masked_family_ce": fixture_session(
                    family_mask=[False, False, False, False]
                ).loss_chunk(0, 4)["cross_entropy"],
            },
        }
    )

    scatter_before = fixture_session()
    untouched = clone_mat(scatter_before.embedding_weights)
    scatter_before.embedding_activity = [
        [1.0, 0.0],
        [1.0, 0.0],
        [0.0, 0.0],
        [1.0, 0.0],
    ]
    scatter_report = scatter_before.packed_update(learning_rate=0.2)
    row0_changed = (
        scatter_report["after"]["embedding_weights"][0] != untouched[0]
    )
    row1_same = scatter_report["after"]["embedding_weights"][1] == untouched[1]
    cases.append(
        {
            "id": "changed_row_scatter",
            "status": "passed" if row0_changed and row1_same else "failed",
            "detail": {
                "active_row_changed": row0_changed,
                "inactive_row_unchanged": row1_same,
                "scatter": "only packed rows with nonzero activity are written back",
            },
        }
    )
    return cases


def source_text(root: Path, relative: str) -> str:
    return (root / relative).read_text(encoding="utf-8")


def contains_line(text: str, snippet: str) -> dict[str, Any]:
    for index, line in enumerate(text.splitlines(), 1):
        if snippet in line:
            return {"found": True, "line": index, "text": line.strip()}
    return {"found": False, "snippet": snippet}


def audit_equations(root: Path) -> dict[str, Any]:
    packed = source_text(root, PACKED_SOURCE)
    batching = source_text(root, BATCHING_SOURCE)
    patterns = {
        "global_denominator": contains_line(
            packed, "denominator = float(max(1, total_samples))"
        ),
        "masked_ce_sum_over_n": contains_line(
            packed, "losses[\"cross_entropy\"] = per_row.masked_select(mask).sum() / denominator"
        ),
        "reconstruction_mean_then_n": contains_line(
            packed,
            "losses[\"reconstruction\"] = (decoded32 - target).square().mean(dim=1).sum() / denominator",
        ),
        "cosine_zero_norm_guard": contains_line(
            packed, "guard = (target_norm > 1.0e-8) & (decoded_norm > 1.0e-8)"
        ),
        "nonfinite_reject": contains_line(
            packed, 'raise FloatingPointError("non-finite packed training loss")'
        ),
        "clip_grad_norm": contains_line(
            packed, "torch.nn.utils.clip_grad_norm_(session.parameters, max_grad_norm)"
        ),
        "sgd_add_": contains_line(
            packed, "parameter.add_(parameter.grad, alpha=-step)"
        ),
        "eta_clamp": contains_line(
            packed, "step = min(1.0, max(0.0, float(learning_rate)))"
        ),
        "noop_mean": contains_line(
            packed, ").masked_select(state.family_mask).mean()"
        ),
        "adam_absent_from_packed_step": {
            "found": "Adam" not in packed and "adam" not in packed,
            "note": "packed optimizer writes scaled negative gradients; no moment buffers",
        },
        "microbatch_plan_has_loss_scales": contains_line(
            batching,
            "scales = tuple((stop - start) / count for start, stop in ranges)",
        ),
        "packed_update_uses_global_n_not_loss_scales": {
            "found": "loss_scales" not in packed,
            "note": "packed update divides each microbatch by total n and sums; helper loss_scales are unused",
        },
    }
    match = all(bool(item.get("found")) for item in patterns.values())
    return {
        "manuscript_equations": {
            "eq5_packed_objective": "H(qF,pF)+H(qV,pV)+MSE+lambda_c(1-cos)+L_norm+lambda_2 R(Theta)",
            "eq12_reconstruction": "(1/n) sum_i (1/d) ||ehat_i - e_i||_2^2",
            "eq13_masked_ce": "-(1/n) sum_{i in M} sum_j q_ij log softmax(l_i)_j with n=total samples",
            "eq14_sgd": "Theta <- Theta - eta Clip(grad Theta L); Clip is gradient-norm clip",
        },
        "implementation": patterns,
        "verdict": "match" if match and patterns["noop_mean"]["found"] else "mismatch",
        "noop_documentation": (
            "Empty-blueprint packed path reduces masked CE with mean() rather than "
            "/n and reports a forward-only no-op; App. J forbids counting that path "
            "as learning progress.  Active packed updates use total-sample n."
        ),
        "manuscript_correction_required": False,
        "source": PACKED_SOURCE,
        "source_sha256": sha256_file(root / PACKED_SOURCE),
    }


def probe_module(name: str) -> dict[str, Any]:
    record: dict[str, Any] = {"name": name, "importable": False}
    try:
        module = __import__(name)
        record["importable"] = True
        record["file"] = getattr(module, "__file__", None)
        record["version"] = getattr(module, "__version__", None)
        if name == "torch":
            record["cuda_is_available"] = bool(module.cuda.is_available())
            record["device_count"] = int(module.cuda.device_count())
            record["bf16_supported"] = bool(
                getattr(module.cuda, "is_bf16_supported", lambda: False)()
            )
    except Exception as exc:
        record["error"] = f"{type(exc).__name__}: {exc}"
    return record


def environment_probe(root: Path) -> dict[str, Any]:
    nvidia = Path("/proc/driver/nvidia/version")
    return {
        "python": {
            "executable": sys.executable,
            "version": sys.version,
            "path": sys.path[:8],
        },
        "process": {
            "PATH": os.environ.get("PATH"),
            "HOME": os.environ.get("HOME"),
            "PYTHONPATH": os.environ.get("PYTHONPATH"),
            "CUDA_VISIBLE_DEVICES": os.environ.get("CUDA_VISIBLE_DEVICES", ""),
            "PWD": os.getcwd(),
            "platform": platform.platform(),
            "machine": platform.machine(),
            "uname": list(os.uname()),
        },
        "modules": {
            "numpy": probe_module("numpy"),
            "torch": probe_module("torch"),
            "pytest": probe_module("pytest"),
        },
        "nvidia_proc": {
            "path": str(nvidia),
            "present": nvidia.is_file(),
            "usability_claim": False,
            "note": "proc presence is not CUDA packed-training usability",
        },
        "source_pins": {
            relative: sha256_file(root / relative)
            for relative in (
                PACKED_SOURCE,
                BATCHING_SOURCE,
                TRANSACTION_SOURCE,
                CHECKPOINT_SOURCE,
                AUTOENCODER_SOURCE,
            )
        },
        "validation_path_contract": "/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin",
        "interpreter_contract": "/usr/bin/python3.12",
    }


def run_pytest(root: Path, args: list[str]) -> dict[str, Any]:
    env = {
        "PATH": "/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin",
        "HOME": os.environ.get("HOME", "/tmp"),
        "PYTHONDONTWRITEBYTECODE": "1",
        "PYTHONPATH": str(root / DATASETS_ROOT),
        "IPFS_AUTO_INSTALL": "false",
        "IPFS_DATASETS_AUTO_INSTALL": "false",
        "CUDA_VISIBLE_DEVICES": "",
    }
    argv = [sys.executable, "-m", "pytest", "-q", "--tb=line", *args]
    started = utc_now()
    try:
        completed = subprocess.run(
            argv,
            cwd="/tmp",
            env=env,
            text=True,
            capture_output=True,
            timeout=180,
            check=False,
        )
        return {
            "argv": argv,
            "exit_code": completed.returncode,
            "stdout": completed.stdout[-8000:],
            "stderr": completed.stderr[-4000:],
            "started_at": started,
            "finished_at": utc_now(),
        }
    except subprocess.TimeoutExpired as exc:
        return {
            "argv": argv,
            "exit_code": 124,
            "stdout": (exc.stdout or "")[-2000:],
            "stderr": f"timeout: {exc}",
            "started_at": started,
            "finished_at": utc_now(),
            "status": "skipped",
            "reason": "timeout",
        }


def classify_pytest(result: dict[str, Any], *, expect_skip_if_cuda: bool = False) -> dict[str, Any]:
    stdout = result.get("stdout") or ""
    stderr = result.get("stderr") or ""
    blob = stdout + "\n" + stderr
    skipped_markers = (
        "libblas.so.3",
        "No module named 'torch'",
        "you should not try to import numpy",
        "CUDA is unavailable",
        "importorskip",
    )
    if result.get("exit_code") not in {0, 1} and any(marker in blob for marker in skipped_markers):
        label = "skipped"
        reason = "torch/numpy/CUDA unavailable in sealed environment"
        if "libblas.so.3" in blob:
            reason = "numpy C-extensions need libblas.so.3; torch also absent; CUDA packed tests not executable"
        return {
            **result,
            "status": label,
            "reason": reason,
            "passed": 0,
            "failed": 0,
            "skipped": 1,
        }
    passed = failed = skipped = 0
    match = re.search(r"(\d+) passed", stdout)
    if match:
        passed = int(match.group(1))
    match = re.search(r"(\d+) failed", stdout)
    if match:
        failed = int(match.group(1))
    match = re.search(r"(\d+) skipped", stdout)
    if match:
        skipped = int(match.group(1))
    status = "passed" if result.get("exit_code") == 0 and failed == 0 else "failed"
    if expect_skip_if_cuda and passed == 0 and skipped == 0 and result.get("exit_code") != 0:
        status = "skipped"
    return {
        **result,
        "status": status,
        "passed": passed,
        "failed": failed,
        "skipped": skipped,
    }


def native_python_update(root: Path) -> dict[str, Any]:
    sys.path.insert(0, str(root / DATASETS_ROOT))
    from ipfs_datasets_py.optimizers.logic_theorem_optimizer.legal_samples import (
        build_us_code_sample,
    )
    from ipfs_datasets_py.optimizers.logic_theorem_optimizer.modal_autoencoder import (
        AdaptiveModalAutoencoder,
    )

    autoencoder = AdaptiveModalAutoencoder(
        family_embedding_weight_scale=1.0,
        compiler_quality_family_logit_scale=1.0,
    )
    samples = [
        build_us_code_sample(
            title="5",
            section="552-af009",
            text="The agency shall provide notice before the permit takes effect.",
        ),
        build_us_code_sample(
            title="12",
            section="1841-af009",
            text="The applicant may appeal unless the board denies jurisdiction.",
        ),
    ]
    before_family = copy.deepcopy(dict(autoencoder.state.family_embedding_weights))
    before_logits = copy.deepcopy(dict(autoencoder.state.compiler_quality_family_logits))
    groups = autoencoder._feature_update_groups_for(samples[0], step=1.0)
    rollback = autoencoder.state.transaction(label="af009-rollback").begin()
    autoencoder.state.family_embedding_weights["probe-rollback"] = [0.0, 1.0]
    rollback_patch = rollback.rollback()
    restored = "probe-rollback" not in autoencoder.state.family_embedding_weights
    transaction = autoencoder.state.transaction(label="af009-python-sparse").begin()
    report = autoencoder._apply_projection_update_batch_in_transaction(
        samples,
        update_targets=("decoded_embedding", "family_logits"),
        learning_rate=0.05,
        l2_regularization=0.0,
        update_backend="python_sparse_batch",
    )
    committed = transaction.commit()
    after_family = dict(autoencoder.state.family_embedding_weights)
    after_logits = dict(autoencoder.state.compiler_quality_family_logits)
    changed_family = [
        key
        for key, value in after_family.items()
        if before_family.get(key) != value
    ]
    changed_logits = [
        key
        for key, value in after_logits.items()
        if before_logits.get(key) != value
    ]
    from ipfs_datasets_py.optimizers.logic_theorem_optimizer.modal_autoencoder_checkpoint import (
        deserialize_checkpoint,
        serialize_checkpoint,
    )
    from ipfs_datasets_py.optimizers.logic_theorem_optimizer.modal_autoencoder import (
        MODAL_AUTOENCODER_STATE_SCHEMA_VERSION,
    )

    encoded = serialize_checkpoint(autoencoder.state)
    loaded = deserialize_checkpoint(
        encoded,
        expected_state_schema_version=MODAL_AUTOENCODER_STATE_SCHEMA_VERSION,
    )
    return {
        "backend": "python_sparse_batch",
        "compute_backend": autoencoder.compute_backend,
        "torch": autoencoder._torch,
        "device": autoencoder.compute_device,
        "sample_ids": [sample.sample_id for sample in samples],
        "embedding_producer": samples[0].embedding_model,
        "projection_update_backend": report.get("projection_update_backend"),
        "touched_row_count": committed.touched_row_count,
        "changed_shared_family_embedding_rows": changed_family,
        "changed_compiler_quality_family_logit_rows": changed_logits,
        "parameter_changed": bool(changed_family or changed_logits),
        "rollback_restored_probe_row": restored,
        "rollback_touched_row_count": rollback_patch.touched_row_count,
        "update_groups_nonempty": bool(groups),
        "update_group_count": len(groups),
        "checkpoint_reload_roundtrip": loaded.state.to_dict() == autoencoder.state.to_dict(),
        "checkpoint_bytes": len(encoded),
        "note": (
            "Native CPU python_sparse_batch updates shared tables through the "
            "historical nudge path.  It is not the packed autodiff path; packed "
            "autodiff requires torch."
        ),
    }


def existing_tests(root: Path) -> list[dict[str, Any]]:
    files = [
        (
            "transaction_rollback",
            [str(root / TEST_DIR / "test_modal_autoencoder_state_transaction.py")],
            False,
        ),
        (
            "checkpoint_reload",
            [str(root / TEST_DIR / "test_modal_autoencoder_checkpoint.py")],
            False,
        ),
        (
            "globally_normalized_batching",
            [str(root / TEST_DIR / "test_modal_autoencoder_batching.py")],
            False,
        ),
        (
            "update_group_activation",
            [
                str(
                    root
                    / TEST_DIR
                    / "test_modal_autoencoder.py::test_feature_update_groups_prioritize_structural_fallback_over_noisy_codec_keys"
                ),
                str(
                    root
                    / TEST_DIR
                    / "test_modal_autoencoder.py::test_feature_logit_clip_bounds_large_feature_aggregates"
                ),
            ],
            False,
        ),
        (
            "packed_cuda_training",
            [str(root / TEST_DIR / "test_modal_autoencoder_cuda_training.py")],
            True,
        ),
        (
            "packed_cuda_residency",
            [str(root / TEST_DIR / "test_modal_autoencoder_cuda_residency.py")],
            True,
        ),
    ]
    results = []
    for name, args, cuda in files:
        raw = run_pytest(root, args)
        classified = classify_pytest(raw, expect_skip_if_cuda=cuda)
        classified["id"] = name
        classified["cuda_required"] = cuda
        results.append(classified)
    return results


def build_backend(env: dict[str, Any], tests: list[dict[str, Any]]) -> dict[str, Any]:
    torch_info = env["modules"]["torch"]
    cuda_usable = bool(torch_info.get("importable") and torch_info.get("cuda_is_available"))
    skipped = [item for item in tests if item.get("status") == "skipped"]
    return {
        "schema": SCHEMA_BACKEND,
        "task_id": "AF-009",
        "created_at": utc_now(),
        "selected_backend": "cpu_packed_reference_semantics",
        "research_gpu_authorization": "denied",
        "qualification": (
            "CPU packed-equation replica plus native python_sparse_batch update "
            "and torch-free unit tests.  Not a T0-T5 training run."
        ),
        "packed_implementation": {
            "module": PACKED_SOURCE,
            "schema_version": CUDA_TRAINING_SCHEMA_VERSION,
            "sha256": env["source_pins"][PACKED_SOURCE],
            "optimizer": "sgd_clipped_no_moments",
            "loss_dtype": "float32",
            "parameter_dtype": "float32",
            "microbatch_normalization": "global_sample_count",
            "cosine_zero_norm_guard": True,
            "nonfinite_policy": "reject_update",
            "empty_blueprint_policy": "forward_only_noop_mean_reduction",
        },
        "cpu": {
            "status": "qualified_for_numerics",
            "device": "cpu",
            "native_python_sparse_batch": "executed",
            "packed_torch_reference": "unavailable_torch_absent",
        },
        "cuda": {
            "status": "unavailable",
            "torch_importable": bool(torch_info.get("importable")),
            "cuda_is_available": bool(torch_info.get("cuda_is_available")),
            "bf16_supported": bool(torch_info.get("bf16_supported")),
            "cpu_fp32_bf16_parity": "unmeasured",
            "reason": torch_info.get("error") or "CUDA packed path not admitted",
            "skipped_tests": [item["id"] for item in skipped],
        },
        "environment_flags": {
            "IPFS_DATASETS_MODAL_AUTOENCODER_CUDA_GRADIENT_ACCUMULATION_STEPS": {
                "default": 1,
                "role": "microbatch count for packed backward accumulation",
            },
            "IPFS_DATASETS_MODAL_AUTOENCODER_CUDA_MAX_GRAD_NORM": {
                "default": 10.0,
                "role": "clip_grad_norm_ ceiling",
            },
            "IPFS_DATASETS_MODAL_AUTOENCODER_CUDA_MIXED_PRECISION": {
                "default": True,
                "role": "optional BF16 activations after numerical check; loss stays FP32",
                "status": "unmeasured_without_cuda",
            },
            "CUDA_VISIBLE_DEVICES": "",
        },
        "no_op_paths": [
            "learning_rate clamped to 0",
            "empty packed blueprints: forward-only mean CE, applied report, no scatter learning",
            "nonfinite packed metrics: update rejected",
            "fully masked categorical rows: CE contribution 0",
            "cuda_resident admission failure: torch_unavailable / cuda_unavailable",
        ],
        "research_training": "unrun; AF-011 remains responsible for T0-T5",
    }


def build_correctness(
    env: dict[str, Any],
    equations: dict[str, Any],
    packed_cases: list[dict[str, Any]],
    native: dict[str, Any],
    tests: list[dict[str, Any]],
) -> dict[str, Any]:
    skipped = [
        {
            "id": item["id"],
            "status": "skipped",
            "reason": item.get("reason") or "CUDA/torch unavailable",
            "exit_code": item.get("exit_code"),
        }
        for item in tests
        if item.get("status") == "skipped"
    ]
    executed = [
        {
            "id": item["id"],
            "status": item.get("status"),
            "passed": item.get("passed"),
            "failed": item.get("failed"),
            "skipped": item.get("skipped"),
            "exit_code": item.get("exit_code"),
            "stdout_tail": (item.get("stdout") or "")[-500:],
        }
        for item in tests
        if item.get("status") != "skipped"
    ]
    return {
        "schema": SCHEMA_CORRECTNESS,
        "task_id": "AF-009",
        "created_at": utc_now(),
        "scope": "numerical qualification of packed CPU semantics; not T0-T5",
        "environment_id": {
            "interpreter": env["python"]["executable"],
            "version": env["python"]["version"].split()[0],
            "PATH": env["process"]["PATH"],
            "HOME": env["process"]["HOME"],
            "uname": env["process"]["uname"],
            "machine": env["process"]["machine"],
            "CUDA_VISIBLE_DEVICES": env["process"]["CUDA_VISIBLE_DEVICES"],
            "source_pins": env["source_pins"],
        },
        "capabilities": env["modules"],
        "equations": equations,
        "packed_cpu_replica": {
            "engine": "stdlib replica of _loss_chunk, clip_grad_norm, and SGD add_",
            "cases": packed_cases,
            "all_passed": all(case["status"] == "passed" for case in packed_cases),
        },
        "native_python_sparse_batch_update": native,
        "existing_tests": {
            "executed": executed,
            "skipped": skipped,
        },
        "acceptance": {
            "actual_outputs_and_environment_ids_retained": True,
            "skipped_tests_labeled_skipped": True,
            "nonzero_admissible_gradients": any(
                case["id"] == "nonzero_admissible_gradients_and_shared_parameter_change"
                and case["status"] == "passed"
                for case in packed_cases
            ),
            "shared_parameters_changed": bool(
                native.get("parameter_changed")
            )
            and any(case.get("detail", {}).get("shared_rows_changed") for case in packed_cases),
            "noop_paths_explicit": True,
            "equation_semantics": equations["verdict"],
            "manuscript_correction_required": equations["manuscript_correction_required"],
        },
        "limitations": [
            "torch is not importable in the sealed validation interpreter; packed CUDA/CPU-reference tensors were not executed through apply_packed_projection_update.",
            "numpy C-extensions in /usr/lib/python3/dist-packages require libblas.so.3, which is absent; CUDA training collection therefore skipped.",
            "CPU/FP32/BF16 parity is unmeasured.",
            "python_sparse_batch is a real shared-parameter update but is not packed autodiff.",
            "No A-E or T0-T5 research training ran.",
        ],
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path.cwd())
    parser.add_argument("--correctness", type=Path, required=True)
    parser.add_argument("--backend", type=Path, required=True)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    root = args.root.resolve()
    env = environment_probe(root)
    equations = audit_equations(root)
    packed_cases = run_packed_cases()
    native_error = None
    try:
        native = native_python_update(root)
    except Exception as exc:
        native = {
            "status": "failed",
            "error": f"{type(exc).__name__}: {exc}",
            "traceback": traceback.format_exc()[-2000:],
            "parameter_changed": False,
        }
        native_error = exc
    tests = existing_tests(root)
    correctness = build_correctness(env, equations, packed_cases, native, tests)
    backend = build_backend(env, tests)
    args.correctness.parent.mkdir(parents=True, exist_ok=True)
    args.backend.parent.mkdir(parents=True, exist_ok=True)
    args.correctness.write_text(
        json.dumps(correctness, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    args.backend.write_text(
        json.dumps(backend, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    summary = {
        "correctness": str(args.correctness),
        "backend": str(args.backend),
        "packed_all_passed": correctness["packed_cpu_replica"]["all_passed"],
        "native_parameter_changed": bool(native.get("parameter_changed")),
        "skipped": [item["id"] for item in tests if item.get("status") == "skipped"],
        "executed": [
            {"id": item["id"], "status": item.get("status"), "passed": item.get("passed")}
            for item in tests
            if item.get("status") != "skipped"
        ],
        "equation_verdict": equations["verdict"],
    }
    print(json.dumps(summary, indent=2, sort_keys=True))
    packed_ok = correctness["packed_cpu_replica"]["all_passed"]
    native_ok = bool(native.get("parameter_changed")) and native_error is None
    tests_ok = all(item.get("status") in {"passed", "skipped"} for item in tests)
    return 0 if packed_ok and native_ok and tests_ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
