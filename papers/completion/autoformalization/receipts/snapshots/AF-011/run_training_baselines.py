#!/usr/bin/env python3
"""AF-011 T0/T1/T2 training-baseline execution under the sealed validation PATH.

Execute the frozen T0 deterministic codec, T1 adaptive learner with sample
memory, and T2 shared-parameter-only conditions on the AF-004 train and
selection partitions. Final-test bodies and identities are never opened.
Hyperparameters are frozen before any outcome inspection. Selection is an
explicit development split and does not become confirmatory final-test
evidence.

Torch, NumPy, MiniLM, packed_cpu, and native checkers are probed against
PATH=/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin and a fresh HOME.
Missing libraries stay unavailable. Mock embeddings and parser-derived
family targets are teacher diagnostics, never independent source gold.
T1 seen-source reconstruction is labeled as a memory diagnostic. T2
update/evaluation memory is disabled in AdaptiveModalAutoencoder.
train_generalizable_projection and is re-checked on the live state.
"""
from __future__ import annotations

import hashlib
import importlib
import json
import os
import random
import re
import sys
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from shutil import which
from typing import Any, Mapping, Sequence

SCHEMA_RESULT = "autoformalization-training-baseline-result/v1"
SCHEMA_MANIFEST = "autoformalization-training-baselines-manifest/v1"
SCHEMA_CHECKPOINTS = "autoformalization-baseline-checkpoints/v1"
TASK_ID = "AF-011"
SEEDS = (104729, 130363, 155921)
T0_REPLAYS = 3
T1_EPOCHS = 1
T1_LEARNING_RATE = 0.35
T2_EPOCHS = 1
T2_LEARNING_RATE = 0.025
T2_LINE_SEARCH_ATTEMPTS = 1
T2_MAX_SECONDS = 90.0
T2_MAX_UPDATE_FAMILIES = 1
TEXT_WINDOW_CHARS = 1024
REQUESTED_T2_BACKEND = "packed_cpu"
EXECUTED_T2_BACKEND = "native"
COMPUTE_DEVICE = "python"
EMBEDDING_MODEL = "mock:stable-sha256"

HERE = Path(__file__).resolve().parent
PAPER_ROOT = HERE.parents[2]
REPO_ROOT = PAPER_ROOT.parents[2]
TRAIN_PATH = PAPER_ROOT / "receipts" / "snapshots" / "AF-004" / "train.sources.jsonl"
SELECTION_PATH = PAPER_ROOT / "receipts" / "snapshots" / "AF-004" / "selection.sources.jsonl"
SPLITS_PATH = PAPER_ROOT / "data" / "splits.json"
TEACHER_PATH = PAPER_ROOT / "data" / "teacher_manifest.json"
AE_PATH = (
    REPO_ROOT
    / "external"
    / "ipfs_datasets"
    / "ipfs_datasets_py"
    / "optimizers"
    / "logic_theorem_optimizer"
    / "modal_autoencoder.py"
)

sys.path[:0] = [str(REPO_ROOT / "external" / "ipfs_datasets")]


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 16), b""):
            digest.update(chunk)
    return digest.hexdigest()


def canonical_json(value: Any) -> bytes:
    return json.dumps(
        value,
        ensure_ascii=True,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    ).encode("utf-8")


def write_json(path: Path, value: Any) -> str:
    path.parent.mkdir(parents=True, exist_ok=True)
    blob = json.dumps(value, indent=2, ensure_ascii=True, sort_keys=True) + "\n"
    path.write_text(blob, encoding="utf-8")
    return sha256_bytes(blob.encode("utf-8"))


def write_jsonl(path: Path, rows: Sequence[Mapping[str, Any]]) -> str:
    path.parent.mkdir(parents=True, exist_ok=True)
    lines = [json.dumps(row, ensure_ascii=True, sort_keys=True, separators=(",", ":")) for row in rows]
    text = "\n".join(lines) + ("\n" if lines else "")
    path.write_text(text, encoding="utf-8")
    return sha256_bytes(text.encode("utf-8"))


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    with path.open(encoding="utf-8") as handle:
        for line in handle:
            if line.strip():
                rows.append(json.loads(line))
    return rows


def probe_import(name: str) -> dict[str, Any]:
    try:
        module = importlib.import_module(name)
    except Exception as exc:
        return {"ok": False, "error": f"{type(exc).__name__}: {exc}"}
    return {
        "ok": True,
        "file": getattr(module, "__file__", None),
        "version": getattr(module, "__version__", None),
    }


def probe_environment() -> dict[str, Any]:
    home = os.environ.get("HOME") or ""
    return {
        "interpreter": sys.executable,
        "version": sys.version,
        "path": os.environ.get("PATH"),
        "home": home,
        "home_is_validation_private": Path(home).name.startswith("ipfs-accelerate-validation-home-")
        if home
        else False,
        "imports": {
            name: probe_import(name)
            for name in ("numpy", "torch", "transformers", "faiss", "multiformats")
        },
        "binaries": {
            name: which(name) for name in ("lean", "lake", "z3", "cvc5", "vampire", "eprover", "coqc", "isabelle")
        },
        "minilm_cache_present": (
            Path(home, ".cache/huggingface/hub/models--sentence-transformers--all-MiniLM-L6-v2").exists()
            if home
            else False
        ),
    }


def inspect_t2_memory_contract(source: str) -> dict[str, Any]:
    """Show that train_generalizable_projection hard-disables sample memory."""
    method = re.search(
        r"def train_generalizable_projection\([\s\S]+?return \{\n(?P<body>[\s\S]+?)\n        \}",
        source,
    )
    kwargs = re.search(
        r"evaluation_kwargs: Dict\[str, Any\] = \{(?P<body>[\s\S]+?)\n        \}",
        source,
    )
    hardcoded = '"use_sample_memory": False' in (kwargs.group("body") if kwargs else "")
    returned_false = '"sample_memory_used": False' in (method.group("body") if method else "")
    nudge = re.search(
        r"def _nudge_decoded_embedding\([\s\S]+?update_sample_memory: bool = (?P<default>True|False)",
        source,
    )
    return {
        "train_generalizable_projection_evaluation_use_sample_memory": False if hardcoded else None,
        "train_generalizable_projection_returns_sample_memory_used_false": returned_false,
        "nudge_decoded_embedding_default_update_sample_memory": (
            nudge.group("default") == "True" if nudge else None
        ),
        "t2_memory_disabled_in_source": hardcoded and returned_false,
        "source_sha256": sha256_bytes(source.encode("utf-8")),
    }


@dataclass
class DiagnosticEvaluation:
    sample_count: int
    embedding_cosine_similarity: float
    cosine_loss: float
    reconstruction_loss: float
    cross_entropy_loss: float
    cross_entropy_entropy_loss: float
    cross_entropy_excess_loss: float
    frame_ranking_loss: float = 0.0
    legal_ir_target_count: int = 0
    decoded_embeddings: dict[str, list[float]] = field(default_factory=dict)
    evaluation_route: str = "encode_decode_family_ce_without_decompiler_structural_targets"

    def to_dict(self) -> dict[str, Any]:
        return {
            "cosine_loss": self.cosine_loss,
            "cross_entropy_entropy_loss": self.cross_entropy_entropy_loss,
            "cross_entropy_excess_loss": self.cross_entropy_excess_loss,
            "cross_entropy_loss": self.cross_entropy_loss,
            "decoded_embedding_count": len(self.decoded_embeddings),
            "embedding_cosine_similarity": self.embedding_cosine_similarity,
            "evaluation_route": self.evaluation_route,
            "frame_ranking_loss": self.frame_ranking_loss,
            "legal_ir_target_count": self.legal_ir_target_count,
            "reconstruction_loss": self.reconstruction_loss,
            "sample_count": self.sample_count,
        }


def mean(values: Sequence[float]) -> float:
    return sum(values) / len(values) if values else 0.0


def diagnostic_eval(model: Any, samples: Sequence[Any], *, use_sample_memory: bool) -> DiagnosticEvaluation:
    from ipfs_datasets_py.optimizers.logic_theorem_optimizer.modal_autoencoder import (
        cosine_similarity,
        cross_entropy_distribution_loss,
        cross_entropy_excess_distribution_loss,
        distribution_entropy_loss,
        mse_loss,
    )

    cosines: list[float] = []
    mses: list[float] = []
    ces: list[float] = []
    ents: list[float] = []
    excesses: list[float] = []
    decoded: dict[str, list[float]] = {}
    for sample in samples:
        encoded = model.encode(sample, use_sample_memory=use_sample_memory)
        vector = model.decode(encoded)
        decoded[sample.sample_id] = vector
        target = list(sample.embedding_vector)
        cosines.append(cosine_similarity(target, vector))
        mses.append(mse_loss(target, vector))
        predicted = encoded["family_distribution"]
        family_target = encoded["target_family_distribution"]
        ces.append(cross_entropy_distribution_loss(predicted, family_target))
        ents.append(distribution_entropy_loss(family_target))
        excesses.append(cross_entropy_excess_distribution_loss(predicted, family_target))
    cosine = mean(cosines)
    return DiagnosticEvaluation(
        sample_count=len(samples),
        embedding_cosine_similarity=cosine,
        cosine_loss=1.0 - cosine,
        reconstruction_loss=mean(mses),
        cross_entropy_loss=mean(ces),
        cross_entropy_entropy_loss=mean(ents),
        cross_entropy_excess_loss=mean(excesses),
        decoded_embeddings=decoded,
    )


def compact_eval(evaluation: Any) -> dict[str, Any]:
    payload = dict(evaluation.to_dict())
    payload.pop("decoded_embeddings", None)
    payload["decoded_embedding_count"] = len(getattr(evaluation, "decoded_embeddings", {}) or {})
    return payload


def item_rows(
    *,
    arm_id: str,
    seed: int | None,
    replay: int | None,
    split: str,
    split_role: str,
    samples: Sequence[Any],
    records: Sequence[Mapping[str, Any]],
    evaluation: Any,
    use_sample_memory: bool,
    sample_memory_entry_count: int,
    checkpoint: Mapping[str, Any],
    termination_reason: str,
    update_count: int,
    elapsed_seconds: float,
    config_id: str,
    dataset_id: str,
    cosine_similarity,
    mse_loss,
) -> list[dict[str, Any]]:
    decoded = getattr(evaluation, "decoded_embeddings", {}) or {}
    rows: list[dict[str, Any]] = []
    for sample, record in zip(samples, records):
        vector = decoded.get(sample.sample_id) or []
        target = list(sample.embedding_vector)
        rows.append(
            {
                "schema": SCHEMA_RESULT,
                "arm_id": arm_id,
                "checkpoint": {"final": checkpoint.get("final"), "initial": checkpoint.get("initial")},
                "claim_admissible": False,
                "config_id": config_id,
                "dataset_id": dataset_id,
                "execution_status": "measured",
                "metrics": {
                    "source_fidelity": None,
                    "vector_cosine": cosine_similarity(target, vector) if vector else None,
                    "vector_mse": mse_loss(target, vector) if vector else None,
                },
                "record_id": f"{arm_id}:{seed if seed is not None else replay}:{split}:{record['record_id']}",
                "record_kind": "item",
                "replay": replay,
                "result_kind": "bounded_observation",
                "sample_memory_used": use_sample_memory,
                "seed": seed,
                "source_record_id": record["record_id"],
                "split": split,
                "termination_reason": termination_reason,
                "update_count": update_count,
            }
        )
    return rows


def aggregate_row(
    *,
    arm_id: str,
    seed: int | None,
    replay: int | None,
    split: str,
    split_role: str,
    evaluation: Any,
    use_sample_memory: bool,
    sample_memory_entry_count: int,
    checkpoint: Mapping[str, Any],
    termination_reason: str,
    update_count: int,
    elapsed_seconds: float,
    config_id: str,
    dataset_id: str,
    n_records: int,
    extra: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    payload = {
        "schema": SCHEMA_RESULT,
        "arm_id": arm_id,
        "checkpoint": dict(checkpoint),
        "claim_admissible": False,
        "config_id": config_id,
        "counts": {
            "eligible": n_records,
            "measured": int(evaluation.sample_count),
            "teacher_targets": int(evaluation.legal_ir_target_count),
        },
        "dataset_id": dataset_id,
        "elapsed_seconds": elapsed_seconds,
        "embedding_model": EMBEDDING_MODEL,
        "evaluation": compact_eval(evaluation),
        "execution_status": "measured",
        "metrics": {
            "excess_ce": evaluation.cross_entropy_excess_loss,
            "family_ce": evaluation.cross_entropy_loss,
            "frame_ranking_loss": evaluation.frame_ranking_loss,
            "native_proof_coverage": None,
            "native_proof_coverage_status": "unmeasured_no_native_checker",
            "source_fidelity": None,
            "source_fidelity_status": "unmeasured_pending_independent_review",
            "target_entropy": evaluation.cross_entropy_entropy_loss,
            "vector_cosine": evaluation.embedding_cosine_similarity,
            "vector_mse": evaluation.reconstruction_loss,
        },
        "record_id": f"{arm_id}:{seed if seed is not None else replay}:{split}:aggregate",
        "record_kind": "aggregate",
        "replay": replay,
        "result_kind": "bounded_observation",
        "sample_memory_entry_count": sample_memory_entry_count,
        "sample_memory_used": use_sample_memory,
        "seed": seed,
        "seen_source": split == "train",
        "semantic_gold": "unmeasured_pending_AF-005",
        "split": split,
        "split_role": split_role,
        "teacher_targets": 0,
        "termination_reason": termination_reason,
        "update_count": update_count,
    }
    if extra:
        payload.update(extra)
    return payload


def locked_split_row(arm_id: str, split: str, n_units: int, reason: str) -> dict[str, Any]:
    return {
        "schema": SCHEMA_RESULT,
        "arm_id": arm_id,
        "bodies_opened": False,
        "claim_admissible": False,
        "counts": {"eligible": n_units, "measured": 0},
        "execution_status": "unrun",
        "ids_inspected": False,
        "metrics": {
            "family_ce": None,
            "native_proof_coverage": None,
            "source_fidelity": None,
            "vector_cosine": None,
            "vector_mse": None,
        },
        "record_id": f"{arm_id}:{split}:locked",
        "record_kind": "coverage",
        "result_kind": "no_run",
        "split": split,
        "termination_reason": reason,
    }


def state_blob(autoencoder: Any) -> tuple[str, bytes, dict[str, Any]]:
    payload = autoencoder.state.to_dict()
    blob = canonical_json(payload)
    return sha256_bytes(blob), blob, payload


def save_state(path: Path, payload: Mapping[str, Any], identity: str, extra: Mapping[str, Any] | None = None) -> None:
    blob = canonical_json(payload)
    record: dict[str, Any] = {
        "byte_count": len(blob),
        "identity_sha256": identity,
        "schema": "autoformalization-baseline-state-identity/v1",
    }
    if extra:
        record.update(extra)
    if len(blob) <= 65536:
        record["state"] = payload
        record["retained"] = "canonical_state"
    else:
        record["retained"] = "identity_only"
        record["omitted"] = "full_shared_parameter_and_sample_memory_tables"
    write_json(path, record)


@dataclass(frozen=True)
class Todo:
    action: str
    sample_ids: tuple[str, ...]
    todo_id: str
    loss_name: str = ""
    metadata: dict[str, Any] | None = None


def bound_text(text: str) -> tuple[str, int, bool]:
    original = str(text)
    if len(original) <= TEXT_WINDOW_CHARS:
        return original, len(original), False
    return original[:TEXT_WINDOW_CHARS], len(original), True


def build_samples(rows: Sequence[Mapping[str, Any]], build_us_code_sample):
    samples = []
    bounds = []
    for row in rows:
        window, original_chars, truncated = bound_text(row["text"])
        sample = build_us_code_sample(
            title=str(row.get("title") or "CFR"),
            section=str(row.get("section_id") or row["record_id"]),
            text=window,
            citation=str(row.get("citation") or row["record_id"]),
        )
        samples.append(sample)
        bounds.append(
            {
                "original_chars": original_chars,
                "record_id": row["record_id"],
                "truncated": truncated,
                "window_chars": len(window),
            }
        )
    return samples, bounds


def main() -> int:
    started = time.time()
    env = probe_environment()
    splits = json.loads(SPLITS_PATH.read_text(encoding="utf-8"))
    teacher = json.loads(TEACHER_PATH.read_text(encoding="utf-8"))
    ae_source = AE_PATH.read_text(encoding="utf-8")
    t2_contract = inspect_t2_memory_contract(ae_source)
    if not t2_contract["t2_memory_disabled_in_source"]:
        raise SystemExit("T2 source contract no longer disables sample memory")

    frozen_inputs = {
        "corpus_manifest_sha256": sha256_file(PAPER_ROOT / "data" / "corpus_manifest.json"),
        "environment_manifest_sha256": sha256_file(PAPER_ROOT / "config" / "environment_manifest.json"),
        "experiment_plan_sha256": sha256_file(PAPER_ROOT / "config" / "experiment_plan.json"),
        "metrics_sha256": sha256_file(PAPER_ROOT / "config" / "metrics.json"),
        "modal_autoencoder_sha256": sha256_file(AE_PATH),
        "selection_sources_sha256": sha256_file(SELECTION_PATH),
        "splits_sha256": sha256_file(SPLITS_PATH),
        "teacher_manifest_sha256": sha256_file(TEACHER_PATH),
        "train_sources_sha256": sha256_file(TRAIN_PATH),
        "training_backend_sha256": sha256_file(PAPER_ROOT / "config" / "training_backend.json"),
    }
    if frozen_inputs["splits_sha256"] != "d4989a3ea15f7035a4e85621bc220b4567828537733c4de4947fd17637bc0b27":
        raise SystemExit("splits.json identity drifted from AF-004 freeze")
    if frozen_inputs["train_sources_sha256"] != splits["exports"]["train"]["sha256"]:
        raise SystemExit("train export digest mismatch")
    if frozen_inputs["selection_sources_sha256"] != splits["exports"]["selection"]["sha256"]:
        raise SystemExit("selection export digest mismatch")

    train_rows = load_jsonl(TRAIN_PATH)
    selection_rows = load_jsonl(SELECTION_PATH)
    if len(train_rows) != splits["counts"]["train"]["natural_source_records"]:
        raise SystemExit("train count mismatch")
    if len(selection_rows) != splits["counts"]["selection"]["natural_source_records"]:
        raise SystemExit("selection count mismatch")
    final_test_n = int(splits["counts"]["final_test"]["natural_source_units"])
    canary_n = int(splits["counts"]["fixed_canary"]["natural_source_units"])

    datasets_path = str(REPO_ROOT / "external" / "ipfs_datasets")
    if datasets_path not in sys.path:
        sys.path.insert(0, datasets_path)
    from ipfs_datasets_py.optimizers.logic_theorem_optimizer.legal_samples import (
        build_us_code_sample,
    )
    from ipfs_datasets_py.optimizers.logic_theorem_optimizer.modal_autoencoder import (
        AdaptiveModalAutoencoder,
        cosine_similarity,
        mse_loss,
    )

    train_samples, train_bounds = build_samples(train_rows, build_us_code_sample)
    selection_samples, selection_bounds = build_samples(selection_rows, build_us_code_sample)
    dataset_id = sha256_bytes(
        canonical_json(
            {
                "selection": [row["record_id"] for row in selection_rows],
                "selection_sha256": frozen_inputs["selection_sources_sha256"],
                "train": [row["record_id"] for row in train_rows],
                "train_sha256": frozen_inputs["train_sources_sha256"],
            }
        )
    )
    config = {
        "compute_device": COMPUTE_DEVICE,
        "embedding_model": EMBEDDING_MODEL,
        "legal_ir_evaluate_provers": False,
        "requested_t2_backend": REQUESTED_T2_BACKEND,
        "seeds": list(SEEDS),
        "t0_replays": T0_REPLAYS,
        "t1_epochs": T1_EPOCHS,
        "t1_learning_rate": T1_LEARNING_RATE,
        "t2_epochs": T2_EPOCHS,
        "t2_executed_backend": EXECUTED_T2_BACKEND,
        "t2_learning_rate": T2_LEARNING_RATE,
        "t2_line_search_attempts": T2_LINE_SEARCH_ATTEMPTS,
        "t2_max_seconds": T2_MAX_SECONDS,
        "t2_max_update_families": T2_MAX_UPDATE_FAMILIES,
        "t2_use_sample_memory": False,
        "text_window_chars": TEXT_WINDOW_CHARS,
    }
    config_id = sha256_bytes(canonical_json(config))

    packed_cpu_probe: dict[str, Any]
    probe_model = AdaptiveModalAutoencoder(compute_device=COMPUTE_DEVICE)
    try:
        probe_model.train_generalizable_projection(
            train_samples[:1],
            validation_samples=selection_samples[:1],
            epochs=1,
            learning_rate=T2_LEARNING_RATE,
            projection_update_backend=REQUESTED_T2_BACKEND,
            max_line_search_attempts=1,
            legal_ir_evaluate_provers=False,
            legal_ir_targets={},
            max_seconds=8,
        )
        packed_cpu_probe = {"ok": True, "unexpected_success": True}
    except Exception as exc:
        packed_cpu_probe = {
            "ok": False,
            "error": f"{type(exc).__name__}: {exc}",
            "executed_backend": EXECUTED_T2_BACKEND,
            "requested_backend": REQUESTED_T2_BACKEND,
        }

    results: list[dict[str, Any]] = []
    checkpoints: list[dict[str, Any]] = []
    t0_metric_hashes: list[str] = []
    state_dir = HERE / "checkpoints" / "states"

    def evaluate(model, samples, use_memory: bool):
        return diagnostic_eval(model, samples, use_sample_memory=use_memory)

    def emit_split(
        model,
        arm_id,
        seed,
        replay,
        split,
        split_role,
        samples,
        records,
        use_memory,
        checkpoint,
        reason,
        updates,
        elapsed,
        extra=None,
        include_items=False,
    ):
        evaluation = evaluate(model, samples, use_memory)
        memory_count = len(model.state.decoded_embeddings)
        results.append(
            aggregate_row(
                arm_id=arm_id,
                seed=seed,
                replay=replay,
                split=split,
                split_role=split_role,
                evaluation=evaluation,
                use_sample_memory=use_memory,
                sample_memory_entry_count=memory_count,
                checkpoint=checkpoint,
                termination_reason=reason,
                update_count=updates,
                elapsed_seconds=elapsed,
                config_id=config_id,
                dataset_id=dataset_id,
                n_records=len(records),
                extra=extra,
            )
        )
        # Item rows are stored once per arm (first replay/seed, primary eval)
        # so the jsonl stays within admission size; aggregates cover every seed.
        if include_items:
            results.extend(
                item_rows(
                    arm_id=arm_id,
                    seed=seed,
                    replay=replay,
                    split=split,
                    split_role=split_role,
                    samples=samples,
                    records=records,
                    evaluation=evaluation,
                    use_sample_memory=use_memory,
                    sample_memory_entry_count=memory_count,
                    checkpoint=checkpoint,
                    termination_reason=reason,
                    update_count=updates,
                    elapsed_seconds=elapsed,
                    config_id=config_id,
                    dataset_id=dataset_id,
                    cosine_similarity=cosine_similarity,
                    mse_loss=mse_loss,
                )
            )
        return evaluation

    # T0 deterministic codec, three replays, no updates.
    for replay in range(1, T0_REPLAYS + 1):
        model = AdaptiveModalAutoencoder(compute_device=COMPUTE_DEVICE)
        initial_sha, initial_blob, initial_state = state_blob(model)
        t0 = time.time()
        train_eval = emit_split(
            model, "T0", None, replay, "train", "seen_training_partition",
            train_samples, train_rows, False,
            {"initial": initial_sha, "final": initial_sha},
            "deterministic_codec_no_update", 0, 0.0,
            include_items=(replay == 1),
        )
        sel_eval = emit_split(
            model, "T0", None, replay, "selection", "development_unseen_not_final_test",
            selection_samples, selection_rows, False,
            {"initial": initial_sha, "final": initial_sha},
            "deterministic_codec_no_update", 0, 0.0,
            include_items=(replay == 1),
        )
        elapsed = round(time.time() - t0, 3)
        results[-1]["elapsed_seconds"] = elapsed
        final_sha, _, final_state = state_blob(model)
        save_state(state_dir / f"T0-replay{replay}-initial.json", initial_state, initial_sha)
        save_state(state_dir / f"T0-replay{replay}-final.json", final_state, final_sha)
        metric_hash = sha256_bytes(
            canonical_json(
                {
                    "selection_cosine": sel_eval.embedding_cosine_similarity,
                    "selection_mse": sel_eval.reconstruction_loss,
                    "train_cosine": train_eval.embedding_cosine_similarity,
                    "train_mse": train_eval.reconstruction_loss,
                }
            )
        )
        t0_metric_hashes.append(metric_hash)
        checkpoints.append(
            {
                "arm_id": "T0",
                "config_id": config_id,
                "dataset_id": dataset_id,
                "elapsed_seconds": elapsed,
                "final_checkpoint_sha256": final_sha,
                "initial_checkpoint_sha256": initial_sha,
                "replay": replay,
                "sample_memory_enabled_for_update": False,
                "sample_memory_enabled_for_evaluation": False,
                "seed": None,
                "state_unchanged": initial_sha == final_sha,
                "termination_reason": "deterministic_codec_no_update",
                "update_count": 0,
            }
        )

    # T1 adaptive learner with sample memory.
    for seed in SEEDS:
        model = AdaptiveModalAutoencoder(compute_device=COMPUTE_DEVICE)
        initial_sha, _, initial_state = state_blob(model)
        rng = random.Random(seed)
        order = list(range(len(train_samples)))
        rng.shuffle(order)
        updates = 0
        t1 = time.time()
        for epoch in range(T1_EPOCHS):
            for index in order:
                sample = train_samples[index]
                for action, loss_name, todo_id in (
                    ("improve_encoder_decoder_reconstruction", "reconstruction_loss", f"t1-{seed}-{epoch}-rec-{sample.sample_id}"),
                    ("improve_modal_family_classifier", "cross_entropy_loss", f"t1-{seed}-{epoch}-fam-{sample.sample_id}"),
                ):
                    report = model.apply_todo(
                        Todo(action=action, sample_ids=(sample.sample_id,), todo_id=todo_id, loss_name=loss_name, metadata={}),
                        {sample.sample_id: sample},
                        learning_rate=T1_LEARNING_RATE,
                    )
                    if report.get("changed"):
                        updates += 1
        elapsed = round(time.time() - t1, 3)
        final_sha, _, final_state = state_blob(model)
        save_state(state_dir / f"T1-{seed}-initial.json", initial_state, initial_sha)
        save_state(state_dir / f"T1-{seed}-final.json", final_state, final_sha)
        memory_count = len(model.state.decoded_embeddings)
        checkpoint = {
            "initial": initial_sha,
            "final": final_sha,
            "sample_memory_entry_count": memory_count,
        }
        emit_split(
            model, "T1", seed, None, "train", "seen_training_partition",
            train_samples, train_rows, True, checkpoint,
            "completed_sample_memory_updates", updates, elapsed,
            extra={"memory_diagnostic": True, "generalization_claim": False},
            include_items=(seed == SEEDS[0]),
        )
        emit_split(
            model, "T1", seed, None, "train", "seen_training_partition_memory_ablation",
            train_samples, train_rows, False, checkpoint,
            "completed_sample_memory_updates", updates, elapsed,
            extra={"memory_diagnostic": True, "evaluation_memory_forced_off": True},
        )
        emit_split(
            model, "T1", seed, None, "selection", "development_unseen_not_final_test",
            selection_samples, selection_rows, True, checkpoint,
            "completed_sample_memory_updates", updates, elapsed,
            extra={"memory_diagnostic": True, "generalization_claim": False},
            include_items=(seed == SEEDS[0]),
        )
        checkpoints.append(
            {
                "arm_id": "T1",
                "config_id": config_id,
                "dataset_id": dataset_id,
                "elapsed_seconds": elapsed,
                "final_checkpoint_sha256": final_sha,
                "initial_checkpoint_sha256": initial_sha,
                "sample_memory_enabled_for_evaluation": True,
                "sample_memory_enabled_for_update": True,
                "sample_memory_entry_count": memory_count,
                "seed": seed,
                "termination_reason": "completed_sample_memory_updates",
                "update_count": updates,
            }
        )

    # T2 shared-parameter-only; memory disabled.
    t2_live_memory_checks: list[dict[str, Any]] = []
    for seed in SEEDS:
        model = AdaptiveModalAutoencoder(compute_device=COMPUTE_DEVICE)
        initial_sha, _, initial_state = state_blob(model)
        rng = random.Random(seed)
        order = list(range(len(train_samples)))
        rng.shuffle(order)
        ordered_train = [train_samples[i] for i in order]
        t2 = time.time()
        report = model.train_generalizable_projection(
            ordered_train,
            validation_samples=selection_samples,
            epochs=T2_EPOCHS,
            learning_rate=T2_LEARNING_RATE,
            projection_update_backend=EXECUTED_T2_BACKEND,
            max_line_search_attempts=T2_LINE_SEARCH_ATTEMPTS,
            legal_ir_evaluate_provers=False,
            legal_ir_targets={},
            max_seconds=T2_MAX_SECONDS,
            projection_max_update_families=T2_MAX_UPDATE_FAMILIES,
        )
        elapsed = round(time.time() - t2, 3)
        final_sha, _, final_state = state_blob(model)
        save_state(state_dir / f"T2-{seed}-initial.json", initial_state, initial_sha)
        save_state(state_dir / f"T2-{seed}-final.json", final_state, final_sha)
        memory_count = len(model.state.decoded_embeddings)
        memory_used = bool(report.get("sample_memory_used"))
        memory_changed = initial_state.get("decoded_embeddings") != final_state.get("decoded_embeddings")
        if memory_used or memory_changed or memory_count != 0:
            raise SystemExit("T2 sample memory was not disabled")
        updates = int(report.get("accepted_epochs") or 0)
        reason = str(
            report.get("stopped_reason")
            or (
                "shared_parameter_trainer_completed_zero_accepted_epochs"
                if updates == 0
                else "completed_shared_parameter_updates"
            )
        )
        checkpoint = {
            "initial": initial_sha,
            "final": final_sha,
            "sample_memory_entry_count": memory_count,
            "sample_memory_used": False,
        }
        extra = {
            "accepted_epochs": report.get("accepted_epochs"),
            "projection_update_backend": report.get("projection_update_backend"),
            "sample_memory_used_in_trainer": report.get("sample_memory_used"),
            "selection_used_for_line_search": True,
            "final_test_used_for_line_search": False,
        }
        train_off = emit_split(
            model, "T2", seed, None, "train", "seen_training_partition",
            train_samples, train_rows, False, checkpoint, reason, updates, elapsed, extra=extra,
            include_items=(seed == SEEDS[0]),
        )
        train_on = emit_split(
            model, "T2", seed, None, "train", "seen_training_partition_memory_probe",
            train_samples, train_rows, True, checkpoint, reason, updates, elapsed,
            extra={**extra, "evaluation_memory_requested": True},
        )
        emit_split(
            model, "T2", seed, None, "selection", "development_unseen_not_final_test",
            selection_samples, selection_rows, False, checkpoint, reason, updates, elapsed, extra=extra,
            include_items=(seed == SEEDS[0]),
        )
        t2_live_memory_checks.append(
            {
                "seed": seed,
                "decoded_embeddings_unchanged": not memory_changed,
                "evaluate_with_memory_matches_without": (
                    train_on.embedding_cosine_similarity == train_off.embedding_cosine_similarity
                    and train_on.reconstruction_loss == train_off.reconstruction_loss
                ),
                "sample_memory_entry_count": memory_count,
                "trainer_sample_memory_used": report.get("sample_memory_used"),
            }
        )
        checkpoints.append(
            {
                "arm_id": "T2",
                "config_id": config_id,
                "dataset_id": dataset_id,
                "elapsed_seconds": elapsed,
                "final_checkpoint_sha256": final_sha,
                "initial_checkpoint_sha256": initial_sha,
                "sample_memory_enabled_for_evaluation": False,
                "sample_memory_enabled_for_update": False,
                "sample_memory_entry_count": memory_count,
                "seed": seed,
                "stopped_reason": report.get("stopped_reason"),
                "termination_reason": reason,
                "update_count": updates,
            }
        )

    for arm_id in ("T0", "T1", "T2"):
        results.append(
            locked_split_row(
                arm_id,
                "final_test",
                final_test_n,
                "final_test_locked_until_model_freeze; identities and bodies were not opened",
            )
        )
        results.append(
            locked_split_row(
                arm_id,
                "fixed_canary",
                canary_n,
                "fixed_canary_not_used_for_training_or_hyperparameter_selection",
            )
        )

    narrowed = {
        "author_decision_required_for_manuscript_claim_edit": True,
        "executed_scope": (
            "T0 three deterministic codec replays and T1/T2 three seeds on 69 train "
            "plus 15 selection CFR units using AdaptiveModalAutoencoder python backend, "
            f"a {TEXT_WINDOW_CHARS}-character source window, and mock:stable-sha256 embeddings."
        ),
        "not_claimed": [
            "Table 11 held-out all-facet source fidelity",
            "native checked useful-proof coverage",
            "shared-learner generalization to unseen final-test source-family/time groups",
            "MiniLM or other semantic-encoder quality",
            "packed_cpu or CUDA training gain",
            "compiler/view teacher CE against generated targets",
            "T1 seen-source reconstruction as generalization",
            "full-document unwindowed training",
        ],
        "reason": (
            "Sealed PATH lacks torch/NumPy/MiniLM and native checkers; packed_cpu raises; "
            f"teacher targets_produced={teacher['compiler_and_view_targets']['targets_produced']}; "
            "independent AF-005 gold is pending; final test remains locked; mock embeddings "
            "are excluded from semantic claims; autoencoder inputs use a frozen "
            f"{TEXT_WINDOW_CHARS}-character window because full-statute evaluate/decompiler "
            "targets exceeded the sealed-PATH wall clock. T1 seen-source cosine improvement "
            "is a memory diagnostic. No training gain is admitted for the paper's primary hypotheses."
        ),
        "route": "budget_and_capability_constrained_development_diagnostics",
        "status": "narrowed_methods_and_development_diagnostics",
    }

    manifest = {
        "schema": SCHEMA_MANIFEST,
        "task_id": TASK_ID,
        "created_at": utc_now(),
        "arms": {
            "T0": {
                "condition": "deterministic codec and view adapters",
                "executed": True,
                "replays": T0_REPLAYS,
                "deterministic_metric_hashes": t0_metric_hashes,
                "deterministic_across_replays": len(set(t0_metric_hashes)) == 1,
                "update_count": 0,
            },
            "T1": {
                "condition": "adaptive learner with sample memory",
                "executed": True,
                "seeds": list(SEEDS),
                "sample_memory_enabled_for_update": True,
                "sample_memory_enabled_for_evaluation": True,
                "memory_diagnostic_not_generalization": True,
            },
            "T2": {
                "condition": "shared parameters only",
                "executed": True,
                "seeds": list(SEEDS),
                "sample_memory_enabled_for_update": False,
                "sample_memory_enabled_for_evaluation": False,
                "requested_backend": REQUESTED_T2_BACKEND,
                "executed_backend": EXECUTED_T2_BACKEND,
                "live_memory_checks": t2_live_memory_checks,
            },
        },
        "budget_constrained_alternative": narrowed,
        "capability_probe": env,
        "config": config,
        "config_id": config_id,
        "dataset_id": dataset_id,
        "elapsed_seconds": round(time.time() - started, 3),
        "final_test_access": {
            "bodies_opened": False,
            "ids_inspected": False,
            "membership_disclosed": splits["exports"]["final_test"]["membership_disclosed"],
            "n_units": final_test_n,
            "private_owner_only": splits["exports"]["final_test"]["private_owner_only"],
            "sha256_from_splits_manifest": splits["exports"]["final_test"]["sha256"],
            "status": "locked",
            "used_to_select_model_settings": False,
        },
        "frozen_inputs": frozen_inputs,
        "packed_cpu_probe": packed_cpu_probe,
        "partitions": {
            "fixed_canary": {"n": canary_n, "used": False},
            "selection": {
                "n": len(selection_rows),
                "n_truncated": sum(1 for item in selection_bounds if item["truncated"]),
                "path": str(SELECTION_PATH.relative_to(REPO_ROOT)),
                "used_as": "T2_line_search_validation_and_development_unseen_eval",
            },
            "train": {
                "n": len(train_rows),
                "n_truncated": sum(1 for item in train_bounds if item["truncated"]),
                "path": str(TRAIN_PATH.relative_to(REPO_ROOT)),
                "used_as": "updates_and_seen_eval",
            },
        },
        "text_window": {
            "chars": TEXT_WINDOW_CHARS,
            "selection_truncated": sum(1 for item in selection_bounds if item["truncated"]),
            "train_truncated": sum(1 for item in train_bounds if item["truncated"]),
        },
        "t2_source_memory_contract": t2_contract,
        "teacher": {
            "compiler_view_targets_produced": teacher["compiler_and_view_targets"]["targets_produced"],
            "semantic_gold": teacher["semantic_gold"]["status"],
        },
    }
    checkpoint_manifest = {
        "schema": SCHEMA_CHECKPOINTS,
        "task_id": TASK_ID,
        "created_at": utc_now(),
        "config_id": config_id,
        "dataset_id": dataset_id,
        "runs": checkpoints,
        "t2_memory_disabled": all(
            item["arm_id"] != "T2"
            or (
                item["sample_memory_enabled_for_update"] is False
                and item["sample_memory_enabled_for_evaluation"] is False
                and item["sample_memory_entry_count"] == 0
            )
            for item in checkpoints
        ),
        "final_test_used_to_select_settings": False,
    }

    run_manifest_path = PAPER_ROOT / "runs" / "training_baselines" / "manifest.json"
    run_results_path = PAPER_ROOT / "runs" / "training_baselines" / "results.jsonl"
    ckpt_manifest_path = PAPER_ROOT / "checkpoints" / "baselines" / "manifest.json"
    write_json(run_manifest_path, manifest)
    write_jsonl(run_results_path, results)
    write_json(ckpt_manifest_path, checkpoint_manifest)
    write_json(HERE / "capability_probe.json", {"environment": env, "packed_cpu_probe": packed_cpu_probe, "t2_source_memory_contract": t2_contract})

    summary = {
        "arms_executed": ["T0", "T1", "T2"],
        "config_id": config_id,
        "dataset_id": dataset_id,
        "elapsed_seconds": manifest["elapsed_seconds"],
        "n_result_rows": len(results),
        "t0_deterministic": manifest["arms"]["T0"]["deterministic_across_replays"],
        "t2_memory_disabled": checkpoint_manifest["t2_memory_disabled"],
        "t2_live_memory_checks": t2_live_memory_checks,
    }
    print(json.dumps(summary, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
