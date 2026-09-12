#!/usr/bin/env python3
"""AF-029 teacher-bound native T0–T3 training on frozen train/selection inputs.

Uses the qualified research toolchain (Torch/NumPy CPU packed autograd and
native Lean/Z3/CVC5). Stripping that profile is treated as an error, not as
proof that the dependencies are unavailable. Encoder vectors are the committed
AF029 MiniLM artifacts; compiler/view targets and native checker feedback are
produced here. E remains locked until a later AF-013 receipt names these
checkpoint identities.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import random
import re
import resource
import shutil
import subprocess
import sys
sys.dont_write_bytecode = True
os.environ["PYTHONDONTWRITEBYTECODE"] = "1"
import tempfile
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from types import SimpleNamespace
from typing import Any, Mapping, Sequence

SCHEMA_RESULT = "autoformalization-native-training-result/v1"
SCHEMA_MANIFEST = "autoformalization-native-training-manifest/v1"
SCHEMA_CHECKPOINTS = "autoformalization-native-training-checkpoints/v1"
SCHEMA_TEACHER = "autoformalization-native-training-teacher-manifest/v1"
SCHEMA_COST = "autoformalization-cost-accounting-result/v1"
TASK_ID = "AF-029"
SEEDS = (104729, 130363, 155921)
T0_REPLAYS = 3
T1_EPOCHS = 1
T1_LEARNING_RATE = 0.35
T2_EPOCHS = 1
T2_LEARNING_RATE = 0.05
T2_LINE_SEARCH_ATTEMPTS = 1
T2_MAX_SECONDS = 240.0
T2_MAX_UPDATE_FAMILIES = 0  # all five native candidate families; never truncate after outcomes
T2_REQUIRED_FAMILIES = ("legal_ir_view_global_logits", "legal_ir_view_logits", "family_logits", "decoded_embedding", "combined")
T3_LEARNING_RATE = 0.10
PARSER_TEXT_CHARS = 4096
REQUESTED_T2_BACKEND = "packed_cpu"
SEALED_PATH = "/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin"
RESEARCH_TOOLCHAIN_SHA256 = "babc2ef29c2e4328b4a7ebb13f639b35a3e24c2c79abd8aa16ee3f6e70943bc7"
LAUNCHER = "/opt/ipfs-accelerate/provider-command-env"
RESEARCH_BIN = Path("/home/barberb/.local/share/vericodegen-research-runtime/bin")
RESEARCH_PYTHON = Path("/home/barberb/.local/share/vericodegen-research-runtime/python")
INPUTS_SHA256 = "6177c6e0957502d22012aef4555a35bb30d137f64a185e41546cae0a5dcb964a"
PACKAGE_SHA256 = "595fe3c2b6b7339d967cfbf21de28f07de8fe03d819f625b999740d1c3038b15"
PROTECTED_STATE_KEYS = (
    "decoded_embeddings",
    "family_logits",
    "feature_embedding_weights",
    "feature_family_logits",
    "legal_ir_view_logits",
    "legal_ir_view_embedding_weights",
    "semantic_slot_embedding_weights",
    "compiler_quality_embedding_weights",
    "compiler_quality_family_logits",
)
PROOF_STATE_KEYS = (
    "applied_proof_feedback_ids",
    "proof_auxiliary_head_logits",
    "proof_auxiliary_head_schema_version",
    "proof_feedback_version_fingerprint",
)
VIEW_FAMILY_MAP = {
    "intent-ir-view/facts/v1": "knowledge_graphs.neo4j_compat",
    "intent-ir-view/intention-deontic/v1": "deontic.ir",
    "intent-ir-view/action-hoare/v1": "CEC.native",
    "intent-ir-view/workflow-temporal/v1": "modal.frame_logic",
    "intent-ir-view/invariant/v1": "modal.frame_logic",
    "intent-ir-view/verification/v1": "TDFOL.prover",
    "intent-ir-view/failure/v1": "external_provers.router",
}

HERE = Path(__file__).resolve().parent
PAPER_ROOT = HERE.parent
REPO_ROOT = PAPER_ROOT.parents[2]
INPUT_EVIDENCE_DIR = PAPER_ROOT / "evidence" / "native_training"
OUTPUT_ROOT = PAPER_ROOT
EVIDENCE_DIR = INPUT_EVIDENCE_DIR
SAVED_CHECKPOINTS: list[dict[str, Any]] = []
JOURNAL_ROWS: dict[str, list[Any]] = {"results": [], "costs": [], "checkpoints": []}
JOURNAL_OFFSETS = {"results": 0, "costs": 0, "checkpoints": 0}
ACTIVE_STAGE: dict[str, Any] | None = None
FEEDBACK_SCOPE = "native_compiler_structural_contracts_only"
TRAIN_PATH = PAPER_ROOT / "receipts" / "snapshots" / "AF-004" / "train.sources.jsonl"
SELECTION_PATH = PAPER_ROOT / "receipts" / "snapshots" / "AF-004" / "selection.sources.jsonl"

sys.path[:0] = [str(HERE), str(REPO_ROOT / "external" / "ipfs_datasets")]


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def sha256_text(text: str) -> str:
    return sha256_bytes(text.encode("utf-8"))


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 16), b""):
            digest.update(chunk)
    return digest.hexdigest()


def canonical_json(value: Any) -> bytes:
    return json.dumps(
        value, ensure_ascii=True, sort_keys=True, separators=(",", ":"), allow_nan=False
    ).encode("utf-8")


def sha256_obj(value: Any) -> str:
    return sha256_bytes(canonical_json(value))


def write_json(path: Path, value: Any) -> str:
    path.parent.mkdir(parents=True, exist_ok=True)
    blob = json.dumps(value, indent=2, ensure_ascii=True, sort_keys=True) + "\n"
    temporary = path.with_name(f".{path.name}.tmp-{os.getpid()}")
    temporary.write_text(blob, encoding="utf-8")
    temporary.replace(path)
    return sha256_bytes(blob.encode("utf-8"))


def write_jsonl(path: Path, rows: Sequence[Mapping[str, Any]]) -> str:
    path.parent.mkdir(parents=True, exist_ok=True)
    lines = [
        json.dumps(row, ensure_ascii=True, sort_keys=True, separators=(",", ":"))
        for row in rows
    ]
    text = "\n".join(lines) + ("\n" if lines else "")
    temporary = path.with_name(f".{path.name}.tmp-{os.getpid()}")
    temporary.write_text(text, encoding="utf-8")
    temporary.replace(path)
    return sha256_bytes(text.encode("utf-8"))


def write_text(path: Path, text: str) -> str:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.tmp-{os.getpid()}")
    temporary.write_text(text, encoding="utf-8")
    temporary.replace(path)
    return sha256_bytes(text.encode("utf-8"))


def _children_cpu() -> float:
    usage = resource.getrusage(resource.RUSAGE_CHILDREN)
    return usage.ru_utime + usage.ru_stime


def _stage_event(body: Mapping[str, Any]) -> None:
    path = EVIDENCE_DIR / "stage_events.jsonl"
    path.parent.mkdir(parents=True, exist_ok=True)
    event = {"schema": "af029-append-only-stage-event/v1", "at": utc_now(), **body}
    blob = canonical_json(event) + b"\n"
    with path.open("ab") as handle:
        handle.write(blob)
        handle.flush()
        os.fsync(handle.fileno())
    directory = os.open(path.parent, os.O_RDONLY | os.O_DIRECTORY)
    try:
        os.fsync(directory)
    finally:
        os.close(directory)


def end_stage(status: str = "completed", **details: Any) -> None:
    global ACTIVE_STAGE
    if ACTIVE_STAGE is None:
        return
    stage = ACTIVE_STAGE
    wall = time.monotonic() - stage.pop("monotonic_start")
    parent_cpu = time.process_time() - stage.pop("parent_cpu_start")
    child_cpu = _children_cpu() - stage.pop("child_cpu_start")
    deltas = {}
    for name, rows in JOURNAL_ROWS.items():
        deltas[name] = rows[JOURNAL_OFFSETS[name]:]
        JOURNAL_OFFSETS[name] = len(rows)
    _stage_event({**stage, "event": "terminal", "status": status,
        "stage_cost": {"wall_seconds": wall, "parent_cpu_seconds": parent_cpu,
                       "child_cpu_seconds": child_cpu, "scope": "exclusive_stage_interval_including_evaluation",
                       "not_additive_to_corresponding_cost_ledger_rows": True},
        "new_rows": deltas, "cumulative_row_counts": {name: len(rows) for name, rows in JOURNAL_ROWS.items()},
        **details})
    ACTIVE_STAGE = None


def begin_stage(stage: str, **identity: Any) -> None:
    global ACTIVE_STAGE
    end_stage()
    ACTIVE_STAGE = {"stage": stage, **identity, "monotonic_start": time.monotonic(),
                    "parent_cpu_start": time.process_time(), "child_cpu_start": _children_cpu()}
    _stage_event({"stage": stage, **identity, "event": "start",
                  "unfinished_terminal_means_usage_and_outcome_require_reconciliation": True})

def load_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    with path.open(encoding="utf-8") as handle:
        for line in handle:
            if line.strip():
                rows.append(json.loads(line))
    return rows


def jsonable(value: Any) -> Any:
    if isinstance(value, dict):
        return {str(key): jsonable(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [jsonable(item) for item in value]
    if isinstance(value, (str, bool)) or value is None:
        return value
    if isinstance(value, int) and not isinstance(value, bool):
        return int(value)
    if isinstance(value, float):
        return float(value)
    to_dict = getattr(value, "to_dict", None)
    if callable(to_dict):
        return jsonable(to_dict())
    return str(value)


def refuse_stripped_profile() -> None:
    path = os.environ.get("PATH") or ""
    home = os.environ.get("HOME") or ""
    sealed = path == SEALED_PATH
    research_on_path = str(RESEARCH_BIN) in path.split(":")
    try:
        import numpy  # noqa: F401
        import torch  # noqa: F401
    except Exception as exc:
        if sealed or not research_on_path:
            raise SystemExit(
                "Stripping the declared research profile is an error, not proof "
                f"that Torch/NumPy/native checkers are unavailable ({type(exc).__name__}: {exc}). "
                "Re-run inside the qualified research toolchain "
                f"(profile {RESEARCH_TOOLCHAIN_SHA256})."
            ) from exc
        raise


def which_checker(name: str) -> str | None:
    found = shutil.which(name)
    if found:
        return found
    candidate = RESEARCH_BIN / name
    if candidate.is_file() and os.access(candidate, os.X_OK):
        return str(candidate)
    return None


def file_origin(path: str | None) -> dict[str, Any]:
    if not path:
        return {"path": None, "sha256": None, "exists": False}
    resolved = Path(path)
    return {
        "path": str(resolved),
        "sha256": sha256_file(resolved) if resolved.is_file() else None,
        "exists": resolved.exists(),
    }


def probe_package(name: str) -> dict[str, Any]:
    try:
        module = __import__(name)
    except Exception as exc:
        return {"ok": False, "error": f"{type(exc).__name__}: {exc}"}
    file_name = getattr(module, "__file__", None)
    record = {
        "ok": True,
        "version": getattr(module, "__version__", None),
        "file": file_name,
        "sha256": sha256_file(Path(file_name)) if file_name and Path(file_name).is_file() else None,
    }
    if name == "torch":
        record["cuda_available"] = bool(getattr(module, "cuda").is_available())
        record["cpu"] = True
    return record


def probe_environment() -> dict[str, Any]:
    home = os.environ.get("HOME") or ""
    path = os.environ.get("PATH") or ""
    checkers = {}
    for name in ("lean", "lake", "z3", "cvc5", "vampire", "eprover", "coqc", "isabelle"):
        resolved = which_checker(name)
        origin = file_origin(resolved)
        version = None
        if resolved:
            try:
                completed = subprocess.run(
                    [resolved, "--version"], capture_output=True, text=True, timeout=10, check=False
                )
                version = (completed.stdout or completed.stderr or "").strip().splitlines()[:1]
                version = version[0] if version else None
            except (OSError, subprocess.TimeoutExpired) as exc:
                version = f"version_probe_failed:{exc}"
        checkers[name] = {
            "resolved_path": resolved,
            "sha256": origin["sha256"],
            "version": version,
            "on_process_path": bool(shutil.which(name)),
            "usable": bool(resolved),
        }
    return {
        "interpreter": sys.executable,
        "version": sys.version,
        "path": path,
        "home": home,
        "pythonpath": os.environ.get("PYTHONPATH"),
        "research_toolchain_sha256": os.environ.get(
            "IPFS_ACCELERATE_AGENT_RESEARCH_TOOLCHAIN_SHA256", RESEARCH_TOOLCHAIN_SHA256
        ),
        "launcher": LAUNCHER if Path(LAUNCHER).is_file() else None,
        "home_is_validation_private": Path(home).name.startswith("ipfs-accelerate-validation-home-")
        if home
        else False,
        "process_path_equals_sealed": path == SEALED_PATH,
        "research_bin_on_path": str(RESEARCH_BIN) in path.split(":"),
        "packages": {name: probe_package(name) for name in ("numpy", "torch")},
        "native_checkers": checkers,
        "any_native_checker_usable": any(item["usable"] for item in checkers.values()),
        "resource_limits": {
            "memory_gib": 16,
            "per_seed_wall_minutes": 30,
            "gpu_or_model_service_slots": 1,
            "compute_device": "cpu",
        },
        "stripped_profile_is_error": True,
    }


def inspect_t2_memory_contract(source: str) -> dict[str, Any]:
    kwargs = re.search(
        r"evaluation_kwargs: Dict\[str, Any\] = \{(?P<body>[\s\S]+?)\n        \}",
        source,
    )
    method = re.search(
        r"def train_generalizable_projection\([\s\S]+?return \{\n(?P<body>[\s\S]+?)\n        \}",
        source,
    )
    hardcoded = '"use_sample_memory": False' in (kwargs.group("body") if kwargs else "")
    returned_false = '"sample_memory_used": False' in (method.group("body") if method else "")
    return {
        "train_generalizable_projection_evaluation_use_sample_memory": False if hardcoded else None,
        "train_generalizable_projection_returns_sample_memory_used_false": returned_false,
        "t2_memory_disabled_in_source": hardcoded and returned_false,
        "source_sha256": sha256_text(source),
    }


@dataclass(frozen=True)
class Todo:
    action: str
    sample_ids: tuple[str, ...]
    todo_id: str
    loss_name: str = ""
    metadata: dict[str, Any] | None = None


@dataclass
class DiagnosticEvaluation:
    sample_count: int
    embedding_cosine_similarity: float
    cosine_loss: float
    reconstruction_loss: float
    cross_entropy_loss: float
    cross_entropy_entropy_loss: float
    cross_entropy_excess_loss: float
    legal_ir_target_count: int = 0
    decoded_embeddings: dict[str, list[float]] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "cosine_loss": self.cosine_loss,
            "cross_entropy_entropy_loss": self.cross_entropy_entropy_loss,
            "cross_entropy_excess_loss": self.cross_entropy_excess_loss,
            "cross_entropy_loss": self.cross_entropy_loss,
            "decoded_embedding_count": len(self.decoded_embeddings),
            "embedding_cosine_similarity": self.embedding_cosine_similarity,
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


def compact_eval(evaluation: DiagnosticEvaluation) -> dict[str, Any]:
    payload = dict(evaluation.to_dict())
    payload.pop("decoded_embeddings", None)
    return payload


def bound_text(text: str, limit: int = PARSER_TEXT_CHARS) -> tuple[str, int, bool]:
    original = str(text)
    if len(original) <= limit:
        return original, len(original), False
    return original[:limit], len(original), True


def infer_modality(text: str) -> tuple[str, str]:
    lowered = text.lower()
    if "must not" in lowered or "shall not" in lowered or "may not" in lowered:
        return "PROHIBITED", "F"
    if re.search(r"\b(must|shall)\b", lowered):
        return "REQUIRED", "O"
    if re.search(r"\bmay\b", lowered):
        return "PERMITTED", "P"
    return "ASSERTED", "I"


class CompactLegalTarget:
    def __init__(self, payload: Mapping[str, Any]):
        self.view_distribution = dict(payload["view_distribution"])
        self.losses = dict(payload.get("losses") or {})
        digest = str(payload["document_hash"])
        self.document = SimpleNamespace(canonical_hash=lambda digest=digest: digest)


def state_blob(autoencoder: Any) -> tuple[str, dict[str, Any]]:
    payload = autoencoder.state.to_dict()
    return sha256_obj(payload), payload


def state_fingerprint(payload: Mapping[str, Any], *, exclude: Sequence[str] = ()) -> str:
    clipped = {key: value for key, value in payload.items() if key not in set(exclude)}
    return sha256_obj(clipped)


def shared_parameter_change(before: Mapping[str, Any], after: Mapping[str, Any]) -> dict[str, Any]:
    from ipfs_datasets_py.optimizers.logic_theorem_optimizer.modal_autoencoder_cuda import _COMPONENT_ROW_KIND
    components = sorted(set(_COMPONENT_ROW_KIND) | {"legal_ir_view_logits"})
    left = {key: before.get(key, {}) for key in components}
    right = {key: after.get(key, {}) for key in components}
    def numbers(value: Any, prefix: tuple[str, ...] = ()) -> dict[tuple[str, ...], float]:
        if isinstance(value, dict):
            return {p: v for key, item in value.items() for p, v in numbers(item, (*prefix, str(key))).items()}
        if isinstance(value, (list, tuple)):
            return {p: v for key, item in enumerate(value) for p, v in numbers(item, (*prefix, str(key))).items()}
        if type(value) not in (int, float) or not math.isfinite(value):
            raise ValueError("shared parameter is not a finite number")
        return {prefix: float(value)}
    changed = {}
    for component in components:
        old, new = numbers(left[component]), numbers(right[component])
        count = sum(old.get(key, 0.0) != new.get(key, 0.0) for key in old.keys() | new.keys())
        if count:
            changed[component] = count
    return {"before_sha256": sha256_obj(left), "after_sha256": sha256_obj(right),
            "changed_numeric_parameter_count": sum(changed.values()),
            "changed_components": changed, "components": components}


def load_state_checkpoint(path: Path) -> Any:
    """Read retained bytes and rebuild the actual native state, checking every value."""
    from ipfs_datasets_py.optimizers.logic_theorem_optimizer.modal_autoencoder import ModalAutoencoderTrainingState
    record = json.loads(path.read_bytes())
    if record.get("schema") != "autoformalization-native-state-checkpoint/v2":
        raise ValueError("identity-only checkpoint is not reloadable")
    payload = record["state"]
    if sha256_obj(payload) != record["identity_sha256"]:
        raise ValueError("checkpoint payload identity mismatch")
    state = ModalAutoencoderTrainingState.from_dict(payload)
    if state.to_dict() != payload or sha256_obj(state.to_dict()) != record["identity_sha256"]:
        raise ValueError("native checkpoint reload changed parameters")
    if state_fingerprint(payload, exclude=PROOF_STATE_KEYS) != record["protected_fingerprint"]:
        raise ValueError("checkpoint protected fingerprint mismatch")
    return state


def save_state(path: Path, payload: Mapping[str, Any], identity: str, extra: Mapping[str, Any] | None = None) -> None:
    if sha256_obj(payload) != identity:
        raise ValueError("checkpoint input identity mismatch")
    record: dict[str, Any] = {
        "byte_count": len(canonical_json(payload)),
        "identity_sha256": identity,
        "protected_fingerprint": state_fingerprint(payload, exclude=PROOF_STATE_KEYS),
        "retained": "complete_native_state_with_exact_reload",
        "schema": "autoformalization-native-state-checkpoint/v2",
        "state": payload,
    }
    if extra:
        if set(extra) & set(record):
            raise ValueError("checkpoint metadata overrides payload binding")
        record.update(extra)
    write_json(path, record)
    reloaded = load_state_checkpoint(path)
    SAVED_CHECKPOINTS.append({
        "path": str(path.relative_to(OUTPUT_ROOT)),
        "file_sha256": sha256_file(path),
        "identity_sha256": identity,
        "reloaded_identity_sha256": sha256_obj(reloaded.to_dict()),
        "all_parameters_equal": reloaded.to_dict() == payload,
        "loader": "ModalAutoencoderTrainingState.from_dict",
        **dict(extra or {}),
    })


def run_checker(*, name: str, argv: Sequence[str], stdin_text: str | None, source_text: str, purpose: str) -> dict[str, Any]:
    resolved = which_checker(name)
    started_at = utc_now()
    t0 = time.perf_counter()
    if not resolved:
        return {
            "schema": "autoformalization-native-checker-receipt/v2",
            "checker": name,
            "purpose": purpose,
            "resolved_path": None,
            "execution_status": "unavailable",
            "result_kind": "no_run",
            "failures": [f"{name} not visible in the research runtime"],
            "started_at": started_at,
            "finished_at": utc_now(),
            "elapsed_ms": round((time.perf_counter() - t0) * 1000.0, 3),
            "independent": True,
        }
    try:
        completed = subprocess.run(
            list(argv),
            input=stdin_text,
            capture_output=True,
            text=True,
            timeout=30,
            check=False,
        )
    except subprocess.TimeoutExpired:
        return {
            "schema": "autoformalization-native-checker-receipt/v2",
            "checker": name,
            "purpose": purpose,
            "resolved_path": resolved,
            "execution_status": "timeout",
            "result_kind": "failure",
            "failures": ["timeout"],
            "started_at": started_at,
            "finished_at": utc_now(),
            "elapsed_ms": round((time.perf_counter() - t0) * 1000.0, 3),
            "independent": True,
        }
    status = "measured" if completed.returncode == 0 else "failure"
    receipt = {
        "schema": "autoformalization-native-checker-receipt/v2",
        "checker": name,
        "purpose": purpose,
        "resolved_path": resolved,
        "argv": list(argv),
        "exit_code": completed.returncode,
        "stdout": (completed.stdout or "")[:2000],
        "stderr": (completed.stderr or "")[:2000],
        "execution_status": status,
        "result_kind": (
            "native_checked_proof"
            if name == "lean" and completed.returncode == 0
            else "solver_local_result"
            if name in {"z3", "cvc5"} and completed.returncode == 0
            else "failure"
        ),
        "failures": [] if completed.returncode == 0 else [f"exit_code={completed.returncode}"],
        "started_at": started_at,
        "finished_at": utc_now(),
        "elapsed_ms": round((time.perf_counter() - t0) * 1000.0, 3),
        "independent": True,
        "source_sha256": sha256_text(source_text),
        "binary_sha256": sha256_file(Path(resolved)),
    }
    receipt["receipt_sha256"] = sha256_obj({key: receipt[key] for key in receipt if key != "receipt_sha256"})
    return receipt


def compile_intent_document(source: Mapping[str, Any], window: str) -> dict[str, Any]:
    from ipfs_datasets_py.logic.intent_ir.formalize.compiler import (
        INTENT_FORMALIZATION_COMPILER_VERSION,
        INTENT_FORMALIZATION_PRODUCER_ID,
        IntentFormalizationCompiler,
    )
    from ipfs_datasets_py.logic.intent_ir.schema import (
        IntentIRDocument,
        IntentKind,
        IntentModality,
        IntentStatement,
        NodeGrounding,
        ReviewStatus,
        SourceRef,
        StatementKind,
    )

    record_id = source["record_id"]
    ref_id = f"src-{record_id}"
    modality_name, _code = infer_modality(window)
    modality = getattr(IntentModality, modality_name)
    document = IntentIRDocument(
        document_id=f"af029-{record_id}",
        title=str(source.get("citation") or record_id),
        intent_kind=IntentKind.POLICY,
        sources=(
            SourceRef(
                ref_id=ref_id,
                source_uri=str((source.get("source_lineage") or {}).get("source_uri") or f"af004://{record_id}"),
                source_id=record_id,
                source_revision=str((source.get("source_lineage") or {}).get("source_revision") or "AF-004-frozen"),
                content_sha256=source["document_sha256"],
                review_status=ReviewStatus.MACHINE_EXTRACTED,
            ),
        ),
        statements=(
            IntentStatement(
                statement_id=f"goal-{record_id}",
                kind=StatementKind.GOAL,
                modality=modality,
                normalized_text=window[:240] or str(source.get("citation") or record_id),
                source_ref_ids=(ref_id,),
                grounding=NodeGrounding.GROUNDED,
                confidence=1.0,
            ),
        ),
        tags=("af029", "train-or-selection", source.get("family") or "unknown"),
    )
    compiler = IntentFormalizationCompiler()
    artifact = compiler.compile(document)
    view_ids = sorted({item.view_id for item in artifact.formulas})
    weights = {VIEW_FAMILY_MAP.get(view_id, view_id): 1.0 for view_id in view_ids} or {"deontic.ir": 1.0}
    total = sum(weights.values())
    view_distribution = {key: value / total for key, value in sorted(weights.items())}
    payload = {
        "producer": INTENT_FORMALIZATION_PRODUCER_ID,
        "producer_version": INTENT_FORMALIZATION_COMPILER_VERSION,
        "vocabulary": "intent-ir-view-registry/v1",
        "artifact_sha256": artifact.sha256,
        "declaration_digest": artifact.declaration_digest,
        "formula_count": len(artifact.formulas),
        "obligation_count": len(artifact.proof_obligations),
        "view_ids": view_ids,
        "view_distribution": view_distribution,
        "proof_backend_execution": False,
        "input_record_id": record_id,
        "input_document_sha256": source["document_sha256"],
        "source_ref_id": ref_id,
        "goal_id": f"goal-{record_id}",
        "premise_id": ref_id,
        "failures": [item.to_dict() if hasattr(item, "to_dict") else str(item) for item in artifact.diagnostics.errors]
        if getattr(artifact.diagnostics, "errors", None)
        else [],
    }
    payload["output_binding_sha256"] = sha256_obj(payload)
    return payload


def quantity(kind: str, observed: bool, unit: str, value: Any, reason: str) -> dict[str, Any]:
    return {
        "kind": kind,
        "observed": observed,
        "quantity": unit if unit.endswith("seconds") or unit.endswith("units") else unit,
        "reason": reason,
        "unit": unit,
        "value": value,
    }


def cost_row(**fields: Any) -> dict[str, Any]:
    payload = {
        "schema": SCHEMA_COST,
        "task_id": TASK_ID,
        "cpu_seconds": quantity(
            "unmeasured", False, "cpu_seconds", None, "process CPU seconds are not inferred from wall time"
        ),
        "gpu_seconds": quantity(
            "unmeasured", False, "gpu_seconds", None, "CPU packed training; GPU seconds unmeasured, not zero"
        ),
        "human_review_seconds": quantity(
            "unmeasured", False, "seconds", None, "independent human review has not been executed"
        ),
        "memory_gib": quantity(
            "unmeasured", False, "gibibytes", None, "RSS snapshots are not converted into billed memory-GiB"
        ),
        "provider_units": quantity(
            "provider", True, "provider_units", 0.0, "no provider model calls in AF-029 training"
        ),
        "hardware": {
            "cache_state": "unused",
            "cuda_available": False,
            "device": "cpu",
            "gpu_telemetry_available": False,
            "hardware": "cpu",
            "notes": "research-runtime Torch CPU packed autograd",
            "precision": "float32",
        },
        "claim_admissible": False,
    }
    payload.update(fields)
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
        "task_id": TASK_ID,
        "termination_reason": reason,
    }


def aggregate_row(**fields: Any) -> dict[str, Any]:
    evaluation: DiagnosticEvaluation = fields.pop("evaluation")
    payload = {
        "schema": SCHEMA_RESULT,
        "task_id": TASK_ID,
        "claim_admissible": False,
        "evaluation": compact_eval(evaluation),
        "execution_status": "measured",
        "metrics": {
            "excess_ce": evaluation.cross_entropy_excess_loss,
            "family_ce": evaluation.cross_entropy_loss,
            "native_proof_coverage": None,
            "native_proof_coverage_status": "teacher_checker_receipts_not_source_gold",
            "source_fidelity": None,
            "source_fidelity_status": "unmeasured_pending_AF-028",
            "target_entropy": evaluation.cross_entropy_entropy_loss,
            "vector_cosine": evaluation.embedding_cosine_similarity,
            "vector_mse": evaluation.reconstruction_loss,
        },
        "record_kind": "aggregate",
        "result_kind": "bounded_observation",
        "semantic_gold": "unmeasured_pending_AF-028",
    }
    payload.update(fields)
    return payload


def item_rows(
    *,
    arm_id: str,
    seed: int | None,
    replay: int | None,
    split: str,
    samples: Sequence[Any],
    records: Sequence[Mapping[str, Any]],
    evaluation: DiagnosticEvaluation,
    checkpoint: Mapping[str, Any],
    termination_reason: str,
    update_count: int,
    config_id: str,
    dataset_id: str,
    cosine_similarity,
    mse_loss,
) -> list[dict[str, Any]]:
    decoded = evaluation.decoded_embeddings
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
                "seed": seed,
                "source_record_id": record["record_id"],
                "split": split,
                "task_id": TASK_ID,
                "termination_reason": termination_reason,
                "update_count": update_count,
            }
        )
    return rows


def verify_prepared_inputs() -> dict[str, Any]:
    script = INPUT_EVIDENCE_DIR / "preparation" / "verify_prepared_inputs.py"
    completed = subprocess.run(
        [sys.executable, "-B", str(script), "--paper-root", str(PAPER_ROOT)],
        cwd=str(REPO_ROOT),
        capture_output=True,
        text=True,
        check=False,
    )
    if completed.returncode != 0:
        raise SystemExit(
            "prepared-input verification failed: "
            + (completed.stderr or completed.stdout or str(completed.returncode))
        )
    payload = json.loads(completed.stdout.strip().splitlines()[-1])
    inputs_path = PAPER_ROOT / "data" / "native_training_inputs.json"
    package_path = INPUT_EVIDENCE_DIR / "preparation" / "package_manifest.json"
    if sha256_file(inputs_path) != INPUTS_SHA256:
        raise SystemExit("native_training_inputs.json digest drifted from the admitted AF-029 input")
    if sha256_file(package_path) != PACKAGE_SHA256:
        raise SystemExit("package_manifest.json digest drifted from the admitted AF-029 inventory")
    if payload.get("rows") != 84 or payload.get("splits") != {"train": 69, "selection": 15}:
        raise SystemExit("prepared input population drifted from 69 train / 15 selection")
    return payload


def build_samples(rows: Sequence[Mapping[str, Any]], encoder_by_id: Mapping[str, Mapping[str, Any]], build_us_code_sample):
    samples = []
    bounds = []
    for row in rows:
        encoder = encoder_by_id[row["record_id"]]
        if encoder.get("source_gold") or encoder.get("independent_gold"):
            raise SystemExit(f"encoder row claims gold for {row['record_id']}")
        if encoder["embedding_model"].startswith("mock"):
            raise SystemExit(f"mock embedding for {row['record_id']}")
        window, original_chars, truncated = bound_text(row["text"])
        sample = build_us_code_sample(
            title=str(row.get("title") or "CFR"),
            section=str(row.get("section_id") or row["record_id"]),
            text=window,
            citation=str(row.get("citation") or row["record_id"]),
            embedding_model=encoder["embedding_model"],
            embedding_vector=encoder["embedding_vector"],
        )
        samples.append(sample)
        bounds.append(
            {
                "embedding_model": encoder["embedding_model"],
                "embedding_revision": encoder["embedding_revision"],
                "embedding_vector_sha256": encoder["embedding_vector_sha256"],
                "original_chars": original_chars,
                "parser_window_chars": len(window),
                "record_id": row["record_id"],
                "sample_id": sample.sample_id,
                "truncated_parser_text": truncated,
            }
        )
    return samples, bounds


def admit_repair(argv: Sequence[str] | None = None) -> dict[str, Any]:
    global OUTPUT_ROOT, EVIDENCE_DIR, T2_MAX_SECONDS
    parser = argparse.ArgumentParser(description="One fresh AF029 corrective run; originals are read-only inputs")
    parser.add_argument("--output-root", required=True, type=Path)
    parser.add_argument("--prior-failure-manifest", required=True, type=Path)
    parser.add_argument("--prior-failure-manifest-sha256", required=True)
    parser.add_argument("--repair-budget", required=True, type=Path)
    parser.add_argument("--repair-budget-sha256", required=True)
    args = parser.parse_args(argv)
    prior_path = args.prior_failure_manifest.resolve()
    if sha256_file(prior_path) != args.prior_failure_manifest_sha256:
        raise ValueError("prior failure manifest changed")
    prior = json.loads(prior_path.read_bytes())
    if prior.get("schema") != "af029-failed-training-preservation/v1" or prior.get("failed_seeds") != list(SEEDS):
        raise ValueError("prior failure cohort mismatch")
    for name, item in prior["files"].items():
        retained = (prior_path.parent / name).resolve()
        if not retained.is_relative_to(prior_path.parent) or sha256_file(retained) != item["sha256"]:
            raise ValueError("prior failure artifact changed")
    budget_path = args.repair_budget.resolve()
    if sha256_file(budget_path) != args.repair_budget_sha256:
        raise ValueError("pre-execution repair budget changed")
    budget = json.loads(budget_path.read_bytes())
    if (budget.get("schema") != "af029-corrective-run-budget/v1"
            or budget.get("prior_failure_manifest_sha256") != args.prior_failure_manifest_sha256
            or budget.get("seeds") != list(SEEDS)
            or budget.get("population") != {"train": 69, "selection": 15, "final": 0}
            or budget.get("native_update_family_count") != 5
            or budget.get("hard_cumulative_budget_claimed") is not False):
        raise ValueError("repair budget/profile binding mismatch")
    allowances = budget.get("per_seed") or {}
    if set(allowances) != {str(seed) for seed in SEEDS}:
        raise ValueError("repair budget missing a fixed seed")
    for allowance in allowances.values():
        known = allowance.get("known_prior_wall_seconds")
        fresh = allowance.get("new_t2_wall_seconds")
        if (type(known) not in (int, float) or type(fresh) not in (int, float)
                or not math.isfinite(known) or not math.isfinite(fresh)
                or known < 0 or not 0 < fresh <= 1200 or known + fresh > 1800
                or type(allowance.get("interrupted_usage_unknown")) is not bool):
            raise ValueError("invalid or over-budget corrective allowance")
    if len({v["new_t2_wall_seconds"] for v in allowances.values()}) != 1:
        raise ValueError("fixed seeds require the same predeclared T2 allowance")
    T2_MAX_SECONDS = next(iter(allowances.values()))["new_t2_wall_seconds"]
    OUTPUT_ROOT = args.output_root.resolve()
    if OUTPUT_ROOT.exists() or OUTPUT_ROOT == PAPER_ROOT.resolve():
        raise ValueError("corrective output root must be fresh; never overwrite an earlier run")
    OUTPUT_ROOT.mkdir(parents=True, exist_ok=False)
    EVIDENCE_DIR = OUTPUT_ROOT / "evidence" / "native_training"
    EVIDENCE_DIR.mkdir(parents=True, exist_ok=False)
    prior_costs = prior_path.parent / "paper/runs/native_training/costs.jsonl"
    retained_costs = EVIDENCE_DIR / "prior_failed_run_costs.jsonl"
    with retained_costs.open("xb") as handle:
        handle.write(prior_costs.read_bytes())
        handle.flush()
        os.fsync(handle.fileno())
    evidence = {
        "prior_failure_manifest": str(prior_path),
        "prior_failure_manifest_sha256": args.prior_failure_manifest_sha256,
        "repair_budget": budget,
        "repair_budget_sha256": args.repair_budget_sha256,
        "original_costs": prior["files"]["paper/runs/native_training/costs.jsonl"],
        "preserved_cost_ledger": str(retained_costs.relative_to(OUTPUT_ROOT)),
        "preserved_cost_ledger_sha256": sha256_file(retained_costs),
        "prior_interrupted_usage_remains_unknown_where_unobserved": True,
        "new_run_costs_accounted_separately": True,
        "hard_cumulative_budget_claimed": False,
    }
    write_json(EVIDENCE_DIR / "repair_admission.json", evidence)
    return evidence


def main() -> int:
    repair_provenance = admit_repair()
    begin_stage("setup")
    refuse_stripped_profile()
    started = time.time()
    cpu_started = time.process_time()
    env = probe_environment()
    if env["process_path_equals_sealed"] and not env["packages"]["torch"]["ok"]:
        raise SystemExit(
            "Stripping the declared research profile is an error, not proof that "
            "Torch/NumPy/native checkers are unavailable."
        )
    if not env["packages"]["torch"]["ok"] or not env["packages"]["numpy"]["ok"]:
        raise SystemExit("research-runtime Torch/NumPy are required for AF-029 packed_cpu training")
    if not env["any_native_checker_usable"]:
        raise SystemExit("research-runtime native checkers are required for AF-029 T3 feedback")

    prepared = verify_prepared_inputs()
    splits = json.loads((PAPER_ROOT / "data" / "splits.json").read_text(encoding="utf-8"))
    experiment_plan = json.loads((PAPER_ROOT / "config" / "experiment_plan.json").read_text(encoding="utf-8"))
    environment_manifest = json.loads(
        (PAPER_ROOT / "config" / "environment_manifest.json").read_text(encoding="utf-8")
    )
    ae_path = (
        REPO_ROOT
        / "external"
        / "ipfs_datasets"
        / "ipfs_datasets_py"
        / "optimizers"
        / "logic_theorem_optimizer"
        / "modal_autoencoder.py"
    )
    t2_contract = inspect_t2_memory_contract(ae_path.read_text(encoding="utf-8"))
    if not t2_contract["t2_memory_disabled_in_source"]:
        raise SystemExit("T2 source contract no longer disables sample memory")

    frozen_inputs = {
        "environment_manifest_sha256": sha256_file(PAPER_ROOT / "config" / "environment_manifest.json"),
        "experiment_plan_sha256": sha256_file(PAPER_ROOT / "config" / "experiment_plan.json"),
        "metrics_sha256": sha256_file(PAPER_ROOT / "config" / "metrics.json"),
        "modal_autoencoder_sha256": sha256_file(ae_path),
        "native_training_inputs_sha256": sha256_file(PAPER_ROOT / "data" / "native_training_inputs.json"),
        "package_manifest_sha256": sha256_file(INPUT_EVIDENCE_DIR / "preparation" / "package_manifest.json"),
        "preprocessing_manifest_sha256": sha256_file(INPUT_EVIDENCE_DIR / "preparation" / "preprocessing_manifest.json"),
        "selection_sources_sha256": sha256_file(SELECTION_PATH),
        "splits_sha256": sha256_file(PAPER_ROOT / "data" / "splits.json"),
        "train_sources_sha256": sha256_file(TRAIN_PATH),
        "training_backend_sha256": sha256_file(PAPER_ROOT / "config" / "training_backend.json"),
    }
    if frozen_inputs["splits_sha256"] != "d4989a3ea15f7035a4e85621bc220b4567828537733c4de4947fd17637bc0b27":
        raise SystemExit("splits.json identity drifted from AF-004 freeze")
    if frozen_inputs["native_training_inputs_sha256"] != INPUTS_SHA256:
        raise SystemExit("admitted encoder input digest mismatch")

    train_rows = load_jsonl(TRAIN_PATH)
    selection_rows = load_jsonl(SELECTION_PATH)
    if len(train_rows) != 69 or len(selection_rows) != 15:
        raise SystemExit("AF-004 train/selection counts drifted")
    encoder_inputs = json.loads((PAPER_ROOT / "data" / "native_training_inputs.json").read_text(encoding="utf-8"))
    encoder_by_id = {row["record_id"]: row for row in encoder_inputs["rows"]}
    if set(encoder_by_id) != {row["record_id"] for row in train_rows + selection_rows}:
        raise SystemExit("encoder rows do not match AF-004 train/selection identities")

    from ipfs_datasets_py.logic.integration.reasoning.legal_ir_hammer_translation import (
        LEGAL_IR_HAMMER_RECONSTRUCTION_RECEIPT_SCHEMA_VERSION,
        LEGAL_IR_HAMMER_TRANSLATION_SCHEMA_VERSION,
    )
    from ipfs_datasets_py.logic.integration.reasoning.legal_ir_obligations import (
        LEGAL_IR_OBLIGATION_SCHEMA_VERSION,
    )
    from ipfs_datasets_py.logic.integration.reasoning.legal_ir_premises import (
        LEGAL_IR_PREMISE_LIBRARY_VERSION,
    )
    from ipfs_datasets_py.logic.integration.reasoning.legal_ir_proof_feedback import (
        KernelReconstructionFeedback,
        LegalIRProofFeedbackRecord,
        ProofFeedbackPartitionPolicy,
        ProofFeedbackVersions,
    )
    from ipfs_datasets_py.logic.integration.reasoning.legal_ir_proof_router import (
        LEGAL_IR_PROOF_ROUTER_SCHEMA_VERSION,
    )
    from ipfs_datasets_py.logic.integration.reasoning.legal_ir_view_contracts import (
        LEGAL_IR_VIEW_CONTRACT_REGISTRY_VERSION,
    )
    from ipfs_datasets_py.logic.intent_ir.formalize.compiler import INTENT_FORMALIZATION_COMPILER_VERSION
    from ipfs_datasets_py.optimizers.logic_theorem_optimizer.legal_samples import build_us_code_sample
    from ipfs_datasets_py.optimizers.logic_theorem_optimizer.modal_autoencoder import (
        AdaptiveModalAutoencoder,
        cosine_similarity,
        mse_loss,
    )

    print(json.dumps({"stage": "start", "path": env["path"], "torch": env["packages"]["torch"]["version"]}), flush=True)
    train_samples, train_bounds = build_samples(train_rows, encoder_by_id, build_us_code_sample)
    selection_samples, selection_bounds = build_samples(selection_rows, encoder_by_id, build_us_code_sample)
    print(json.dumps({"stage": "samples", "train": len(train_samples), "selection": len(selection_samples)}), flush=True)
    sample_by_record = {
        bound["record_id"]: sample
        for bound, sample in list(zip(train_bounds, train_samples)) + list(zip(selection_bounds, selection_samples))
    }

    begin_stage("compiler_targets")
    target_started = time.time()
    teacher_rows: list[dict[str, Any]] = []
    legal_ir_targets: dict[str, CompactLegalTarget] = {}
    compile_failures = 0
    for row, bound in list(zip(train_rows, train_bounds)) + list(zip(selection_rows, selection_bounds)):
        window, _chars, _trunc = bound_text(row["text"])
        compiled = compile_intent_document(row, window)
        if compiled.get("failures"):
            compile_failures += 1
        if not compiled["view_distribution"] or not compiled["artifact_sha256"]:
            raise SystemExit(f"empty compiler/view target for {row['record_id']}")
        target_payload = {
            "document_hash": compiled["artifact_sha256"],
            "losses": {"legal_ir_multiview_total_loss": 0.0},
            "view_distribution": compiled["view_distribution"],
        }
        legal_ir_targets[sample_by_record[row["record_id"]].sample_id] = CompactLegalTarget(target_payload)
        teacher_rows.append(
            {
                "artifact_sha256": compiled["artifact_sha256"],
                "declaration_digest": compiled["declaration_digest"],
                "embedding_model": bound["embedding_model"],
                "embedding_revision": bound["embedding_revision"],
                "embedding_vector_sha256": bound["embedding_vector_sha256"],
                "goal_id": compiled["goal_id"],
                "input_document_sha256": compiled["input_document_sha256"],
                "output_binding_sha256": compiled["output_binding_sha256"],
                "premise_id": compiled["premise_id"],
                "producer": compiled["producer"],
                "producer_version": compiled["producer_version"],
                "proof_backend_execution": False,
                "record_id": row["record_id"],
                "sample_id": bound["sample_id"],
                "source_gold": False,
                "independent_gold": False,
                "split": "train" if row in train_rows else "selection",
                "view_distribution": compiled["view_distribution"],
                "view_ids": compiled["view_ids"],
                "vocabulary": compiled["vocabulary"],
            }
        )
    target_elapsed = round(time.time() - target_started, 3)
    if len(legal_ir_targets) != 84:
        raise SystemExit("compiler/view targets missing for the frozen 84-row population")
    _stage_event({"stage": "compiler_targets", "event": "artifact",
                  "teacher_rows": teacher_rows, "train_count": 69, "selection_count": 15,
                  "final_count": 0, "elapsed_seconds": target_elapsed})
    print(json.dumps({"stage": "compiler_targets", "count": len(teacher_rows), "elapsed": target_elapsed}), flush=True)

    begin_stage("native_source_contract_feedback")
    checker_started = time.time()
    checker_receipts: list[dict[str, Any]] = []
    admitted_records: list[Any] = []
    lean_version = (env["native_checkers"].get("lean") or {}).get("version") or "lean-unknown"
    z3_version = (env["native_checkers"].get("z3") or {}).get("version") or "z3-unknown"
    pinned_versions = ProofFeedbackVersions(
        compiler_version=INTENT_FORMALIZATION_COMPILER_VERSION,
        obligation_schema_version=LEGAL_IR_OBLIGATION_SCHEMA_VERSION,
        contract_registry_version=LEGAL_IR_VIEW_CONTRACT_REGISTRY_VERSION,
        premise_library_version=LEGAL_IR_PREMISE_LIBRARY_VERSION,
        proof_router_version=LEGAL_IR_PROOF_ROUTER_SCHEMA_VERSION,
        translation_schema_version=LEGAL_IR_HAMMER_TRANSLATION_SCHEMA_VERSION,
        reconstruction_schema_version=LEGAL_IR_HAMMER_RECONSTRUCTION_RECEIPT_SCHEMA_VERSION,
        solver_toolchain_version=re.sub(r"[^A-Za-z0-9._:/@+-]+", "-", z3_version)[:96] or "z3",
        lean_toolchain_version=re.sub(r"[^A-Za-z0-9._:/@+-]+", "-", lean_version)[:96] or "lean",
        theorem_registry_version="autoformalization-theorem-registry/v1",
        repair_taxonomy_version="legal-ir-repair-labels-v1",
    )
    import importlib.util
    feedback_source = INPUT_EVIDENCE_DIR / "source_obligation_feedback.py"
    spec = importlib.util.spec_from_file_location("af029_source_obligation_feedback", feedback_source)
    feedback_module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = feedback_module
    spec.loader.exec_module(feedback_module)
    lean_path = which_checker("lean")
    if not lean_path:
        raise SystemExit("qualified native Lean compiler-contract checker unavailable")
    admitted_records, checker_receipts, feedback_coverage = feedback_module.produce_source_feedback(
        train_rows=train_rows, train_samples=train_samples, teacher_rows=teacher_rows,
        versions=pinned_versions, output_dir=EVIDENCE_DIR / "source_obligation_feedback",
        lean_path=Path(lean_path))
    frozen_inputs["source_feedback_producer_sha256"] = sha256_file(feedback_source)
    write_json(EVIDENCE_DIR / "source_obligation_feedback_coverage.json", feedback_coverage)
    if not admitted_records:
        raise SystemExit("no admitted actual compiler-contract feedback; T3 remains unresolved")
    checker_elapsed = round(time.time() - checker_started, 3)
    print(json.dumps({"stage": "native_checker", "receipts": len(checker_receipts), "admitted": len(admitted_records), "elapsed": checker_elapsed}), flush=True)

    dataset_id = sha256_obj(
        {
            "encoder_inputs": frozen_inputs["native_training_inputs_sha256"],
            "selection": [row["record_id"] for row in selection_rows],
            "selection_sha256": frozen_inputs["selection_sources_sha256"],
            "teacher_targets": [row["artifact_sha256"] for row in teacher_rows],
            "train": [row["record_id"] for row in train_rows],
            "train_sha256": frozen_inputs["train_sources_sha256"],
        }
    )
    config = {
        "compute_device": "cpu",
        "embedding_model": encoder_inputs["model_id"],
        "embedding_revision": encoder_inputs["model_revision"],
        "legal_ir_evaluate_provers": False,
        "parser_text_chars": PARSER_TEXT_CHARS,
        "projection_update_backend": REQUESTED_T2_BACKEND,
        "seeds": list(SEEDS),
        "t0_replays": T0_REPLAYS,
        "t1_epochs": T1_EPOCHS,
        "t1_learning_rate": T1_LEARNING_RATE,
        "t2_epochs": T2_EPOCHS,
        "t2_learning_rate": T2_LEARNING_RATE,
        "t2_line_search_attempts": T2_LINE_SEARCH_ATTEMPTS,
        "t2_max_seconds": T2_MAX_SECONDS,
        "t2_max_update_families": T2_MAX_UPDATE_FAMILIES,
        "t2_use_sample_memory": False,
        "t3_learning_rate": T3_LEARNING_RATE,
    }
    config_id = sha256_obj(config)

    results: list[dict[str, Any]] = []
    checkpoints: list[dict[str, Any]] = []
    costs: list[dict[str, Any]] = []
    JOURNAL_ROWS.update(results=results, costs=costs, checkpoints=checkpoints)
    t0_metric_hashes: list[str] = []
    state_dir = EVIDENCE_DIR / "states"
    logs_dir = EVIDENCE_DIR / "logs"
    state_dir.mkdir(parents=True, exist_ok=True)
    logs_dir.mkdir(parents=True, exist_ok=True)

    def emit_split(model, arm_id, seed, replay, split, split_role, samples, records, use_memory, checkpoint, reason, updates, elapsed, extra=None, include_items=False):
        evaluation = diagnostic_eval(model, samples, use_sample_memory=use_memory)
        evaluation.legal_ir_target_count = sum(1 for sample in samples if sample.sample_id in legal_ir_targets)
        memory_count = len(model.state.decoded_embeddings)
        row = aggregate_row(
            arm_id=arm_id,
            seed=seed,
            replay=replay,
            split=split,
            split_role=split_role,
            evaluation=evaluation,
            use_sample_memory=use_memory,
            sample_memory_entry_count=memory_count,
            checkpoint=dict(checkpoint),
            termination_reason=reason,
            update_count=updates,
            elapsed_seconds=elapsed,
            config_id=config_id,
            dataset_id=dataset_id,
            counts={"eligible": len(records), "measured": int(evaluation.sample_count), "teacher_targets": int(evaluation.legal_ir_target_count)},
            embedding_model=encoder_inputs["model_id"],
            record_id=f"{arm_id}:{seed if seed is not None else replay}:{split}:aggregate",
            seen_source=split == "train",
            teacher_targets=int(evaluation.legal_ir_target_count),
        )
        if extra:
            row.update(extra)
        results.append(row)
        if include_items:
            results.extend(
                item_rows(
                    arm_id=arm_id,
                    seed=seed,
                    replay=replay,
                    split=split,
                    samples=samples,
                    records=records,
                    evaluation=evaluation,
                    checkpoint=checkpoint,
                    termination_reason=reason,
                    update_count=updates,
                    config_id=config_id,
                    dataset_id=dataset_id,
                    cosine_similarity=cosine_similarity,
                    mse_loss=mse_loss,
                )
            )
        return evaluation

    # T0
    for replay in range(1, T0_REPLAYS + 1):
        begin_stage("T0", replay=replay)
        model = AdaptiveModalAutoencoder(compute_device="cpu")
        initial_sha, initial_state = state_blob(model)
        t0 = time.time()
        include = replay == 1
        train_eval = emit_split(
            model, "T0", None, replay, "train", "seen_training_partition",
            train_samples, train_rows, False,
            {"initial": initial_sha, "final": initial_sha},
            "deterministic_codec_no_update", 0, 0.0, include_items=include,
        )
        sel_eval = emit_split(
            model, "T0", None, replay, "selection", "development_unseen_not_final_test",
            selection_samples,
            selection_rows, False,
            {"initial": initial_sha, "final": initial_sha},
            "deterministic_codec_no_update", 0, 0.0, include_items=include,
        )
        elapsed = round(time.time() - t0, 3)
        results[-1]["elapsed_seconds"] = elapsed
        final_sha, final_state = state_blob(model)
        save_state(state_dir / f"T0-replay{replay}-initial.json", initial_state, initial_sha, {"arm_id": "T0", "replay": replay})
        save_state(state_dir / f"T0-replay{replay}-final.json", final_state, final_sha, {"arm_id": "T0", "replay": replay})
        t0_metric_hashes.append(
            sha256_obj(
                {
                    "selection_cosine": sel_eval.embedding_cosine_similarity,
                    "selection_mse": sel_eval.reconstruction_loss,
                    "train_cosine": train_eval.embedding_cosine_similarity,
                    "train_mse": train_eval.reconstruction_loss,
                }
            )
        )
        checkpoints.append(
            {
                "arm_id": "T0",
                "config_id": config_id,
                "dataset_id": dataset_id,
                "elapsed_seconds": elapsed,
                "final_checkpoint_sha256": final_sha,
                "initial_checkpoint_sha256": initial_sha,
                "projection_update_backend": None,
                "replay": replay,
                "sample_memory_enabled_for_evaluation": False,
                "sample_memory_enabled_for_update": False,
                "seed": None,
                "state_unchanged": initial_sha == final_sha,
                "termination_reason": "deterministic_codec_no_update",
                "update_count": 0,
            }
        )
        print(json.dumps({"stage": "T0", "replay": replay, "elapsed": elapsed}), flush=True)
        costs.append(
            cost_row(
                record_id=f"AF-029:T0:replay{replay}",
                record_kind="source_usage",
                experiment_arm="T0",
                phase="target_construction",
                replay=replay,
                execution_status="measured",
                elapsed_seconds=quantity("measured", True, "seconds", elapsed, "T0 codec wall time"),
                update_count=0,
                notes="deterministic_codec_no_update",
            )
        )

    # T1 uses native sample-memory updates. Shared embedding-head scales are
    # disabled so the 384-d MiniLM reconstruction does not expand into the
    # full feature-weight tables; T2 owns shared packed-parameter learning.
    t1_kwargs = {
        "compute_device": "cpu",
        "compiler_quality_embedding_weight_scale": 0.0,
        "logic_signature_embedding_weight_scale": 0.0,
        "round_trip_signal_embedding_weight_scale": 0.0,
        "decompiler_plan_embedding_weight_scale": 0.0,
        "predicate_argument_embedding_weight_scale": 0.0,
        "feature_embedding_weight_scale": 0.0,
        "family_embedding_weight_scale": 0.0,
        "family_semantic_slot_embedding_weight_scale": 0.0,
        "family_legal_ir_view_embedding_weight_scale": 0.0,
        "semantic_slot_embedding_weight_scale": 0.0,
        "legal_ir_view_embedding_weight_scale": 0.0,
        "semantic_slot_legal_ir_view_embedding_weight_scale": 0.0,
        "family_semantic_slot_legal_ir_view_embedding_weight_scale": 0.0,
    }
    for seed in SEEDS:
        begin_stage("T1", seed=seed)
        model = AdaptiveModalAutoencoder(**t1_kwargs)
        initial_sha, initial_state = state_blob(model)
        rng = random.Random(seed)
        order = list(range(len(train_samples)))
        rng.shuffle(order)
        updates = 0
        t1 = time.time()
        for epoch in range(T1_EPOCHS):
            for index in order:
                sample = train_samples[index]
                before_mem = sample.sample_id in model.state.decoded_embeddings
                model._nudge_decoded_embedding(
                    sample, learning_rate=T1_LEARNING_RATE, update_sample_memory=True
                )
                if sample.sample_id in model.state.decoded_embeddings:
                    updates += 1
                report = model.apply_todo(
                    Todo(
                        action="improve_modal_family_classifier",
                        sample_ids=(sample.sample_id,),
                        todo_id=f"t1-{seed}-{epoch}-fam-{sample.sample_id}",
                        loss_name="cross_entropy_loss",
                        metadata={},
                    ),
                    {sample.sample_id: sample},
                    learning_rate=T1_LEARNING_RATE,
                )
                if report.get("changed"):
                    updates += 1
                del before_mem
        elapsed = round(time.time() - t1, 3)
        final_sha, final_state = state_blob(model)
        save_state(state_dir / f"T1-{seed}-initial.json", initial_state, initial_sha, {"arm_id": "T1", "seed": seed})
        save_state(state_dir / f"T1-{seed}-final.json", final_state, final_sha, {"arm_id": "T1", "seed": seed})
        memory_count = len(model.state.decoded_embeddings)
        checkpoint = {"initial": initial_sha, "final": final_sha, "sample_memory_entry_count": memory_count}
        emit_split(
            model, "T1", seed, None, "train", "seen_training_partition",
            train_samples,
            train_rows,
            True, checkpoint, "completed_sample_memory_updates", updates, elapsed,
            extra={"memory_diagnostic": True, "generalization_claim": False},
            include_items=(seed == SEEDS[0]),
        )
        emit_split(
            model, "T1", seed, None, "selection", "development_unseen_not_final_test",
            selection_samples,
            selection_rows,
            True, checkpoint, "completed_sample_memory_updates", updates, elapsed,
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
        print(json.dumps({"stage": "T1", "seed": seed, "updates": updates, "elapsed": elapsed}), flush=True)
        costs.append(
            cost_row(
                record_id=f"AF-029:T1:{seed}",
                record_kind="source_usage",
                experiment_arm="T1",
                phase="updates_selection",
                seed=seed,
                execution_status="measured",
                elapsed_seconds=quantity("measured", True, "seconds", elapsed, "T1 sample-memory wall time"),
                update_count=updates,
                notes="completed_sample_memory_updates",
            )
        )

    # T2 packed_cpu, then matched T3 on the same live state.
    t2_live_memory_checks: list[dict[str, Any]] = []
    packed_summaries: list[dict[str, Any]] = []
    t3_by_seed: list[dict[str, Any]] = []
    t3_gate = "empty_or_untrusted_feedback" if not admitted_records else "admitted_native_feedback"
    for seed in SEEDS:
        begin_stage("T2", seed=seed)
        model = AdaptiveModalAutoencoder(compute_device="cpu")
        initial_sha, initial_state = state_blob(model)
        rng = random.Random(seed)
        order = list(range(len(train_samples)))
        rng.shuffle(order)
        ordered_train = [train_samples[i] for i in order]
        t2 = time.time()
        try:
            report = model.train_generalizable_projection(
                ordered_train,
                validation_samples=selection_samples,
                epochs=T2_EPOCHS,
                learning_rate=T2_LEARNING_RATE,
                projection_update_backend=REQUESTED_T2_BACKEND,
                max_line_search_attempts=T2_LINE_SEARCH_ATTEMPTS,
                legal_ir_evaluate_provers=False,
                legal_ir_targets=legal_ir_targets,
                max_seconds=T2_MAX_SECONDS,
                projection_max_update_families=T2_MAX_UPDATE_FAMILIES,
                max_cosine_regression=1.0,
                max_reconstruction_regression=1.0,
                max_cross_entropy_regression=1.0,
                max_legal_ir_loss_regression=1.0,
            )
            failure = None
        except Exception as exc:
            report = {
                "accepted_epochs": 0,
                "projection_update_backend": REQUESTED_T2_BACKEND,
                "sample_memory_used": False,
                "stopped_reason": f"{type(exc).__name__}: {exc}",
                "projection_packed_cpu": {"enabled": True, "reports": list(getattr(model, "_packed_cpu_reports", []))},
            }
            failure = f"{type(exc).__name__}: {exc}"
        elapsed = round(time.time() - t2, 3)
        final_sha, final_state = state_blob(model)
        shared_change = shared_parameter_change(initial_state, final_state)
        save_state(state_dir / f"T2-{seed}-initial.json", initial_state, initial_sha, {"arm_id": "T2", "seed": seed})
        save_state(state_dir / f"T2-{seed}-final.json", final_state, final_sha, {"arm_id": "T2", "seed": seed})
        memory_count = len(model.state.decoded_embeddings)
        memory_used = bool(report.get("sample_memory_used"))
        memory_changed = initial_state.get("decoded_embeddings") != final_state.get("decoded_embeddings")
        if memory_used or memory_changed or memory_count != 0:
            raise SystemExit("T2 sample memory was not disabled")
        packed = report.get("projection_packed_cpu") or {}
        packed_reports = packed.get("reports") or []
        applied = sum(1 for item in packed_reports if item.get("applied"))
        updates = int(report.get("accepted_epochs") or 0)
        backend = report.get("projection_update_backend")
        if backend != REQUESTED_T2_BACKEND:
            raise SystemExit(f"T2 did not execute packed_cpu (got {backend})")
        reason = str(
            report.get("stopped_reason")
            or (
                "shared_parameter_trainer_completed_zero_accepted_epochs"
                if updates == 0
                else "completed_shared_parameter_updates"
            )
        )
        if failure:
            reason = "packed_cpu_update_failure"
        checkpoint = {
            "initial": initial_sha,
            "final": final_sha,
            "sample_memory_entry_count": memory_count,
            "sample_memory_used": False,
        }
        norms = [item.get("gradient_norm") for item in packed_reports]
        considered_families = {candidate.get("update")
            for epoch in report.get("epoch_reports", [])
            for candidate in epoch.get("candidate_reports", [])}
        full_family_search = (report.get("candidate_update_order") == list(T2_REQUIRED_FAMILIES)
                              and considered_families == set(T2_REQUIRED_FAMILIES))
        qualification = {
            "backend": backend,
            "accepted_epochs": updates,
            "parameter_changed": initial_sha != final_sha,
            "gradient_norms": norms,
            "failure": failure,
            "initial_checkpoint_sha256": initial_sha,
            "final_checkpoint_sha256": final_sha,
            "seed": seed,
            "elapsed_seconds": elapsed,
            "training_population": 69,
            "selection_population": 15,
            "full_native_report": report,
            "shared_parameter_change": shared_change,
            "full_family_search": full_family_search,
            "considered_families": sorted(considered_families),
        }
        write_json(EVIDENCE_DIR / f"T2-{seed}-outer-result.json", qualification)
        if (failure or not full_family_search or type(report.get("accepted_epochs")) is not int or updates <= 0
                or initial_sha == final_sha or shared_change["changed_numeric_parameter_count"] <= 0 or not norms
                or any(type(n) not in (int, float) or not math.isfinite(n) or n < 0 for n in norms)
                or not any(n > 0 for n in norms)):
            raise SystemExit(f"T2 seed {seed} did not commit a valid shared update; retained failure, no T3 or promotion")
        extra = {
            "accepted_epochs": report.get("accepted_epochs"),
            "packed_cpu_applied_updates": applied,
            "projection_update_backend": backend,
            "sample_memory_used_in_trainer": report.get("sample_memory_used"),
            "selection_used_for_line_search": True,
            "final_test_used_for_line_search": False,
            "failure": failure,
        }
        train_off = emit_split(
            model, "T2", seed, None, "train", "seen_training_partition",
            train_samples,
            train_rows,
            False, checkpoint, reason, updates, elapsed, extra=extra,
            include_items=(seed == SEEDS[0]),
        )
        probe_on = diagnostic_eval(model, train_samples[:4], use_sample_memory=True)
        probe_off = diagnostic_eval(model, train_samples[:4], use_sample_memory=False)
        emit_split(
            model, "T2", seed, None, "selection", "development_unseen_not_final_test",
            selection_samples,
            selection_rows,
            False, checkpoint, reason, updates, elapsed, extra=extra,
            include_items=(seed == SEEDS[0]),
        )
        train_on = probe_on
        t2_live_memory_checks.append(
            {
                "seed": seed,
                "decoded_embeddings_unchanged": not memory_changed,
                "evaluate_with_memory_matches_without": (
                    probe_on.embedding_cosine_similarity == probe_off.embedding_cosine_similarity
                    and probe_on.reconstruction_loss == probe_off.reconstruction_loss
                ),
                "sample_memory_entry_count": memory_count,
                "trainer_sample_memory_used": report.get("sample_memory_used"),
            }
        )
        packed_summaries.append(
            {
                "seed": seed,
                "accepted_epochs": updates,
                "applied_packed_updates": applied,
                "backend": backend,
                "gradient_norms": [item.get("gradient_norm") for item in packed_reports],
                "losses": [item.get("losses") for item in packed_reports],
                "parameter_changed": initial_sha != final_sha,
                "shared_parameter_change": shared_change,
                "full_family_search": full_family_search,
                "considered_families": sorted(considered_families),
                "report_count": len(packed_reports),
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
                "packed_cpu_applied_updates": applied,
                "parameter_changed": initial_sha != final_sha,
                "shared_parameter_change": shared_change,
                "full_family_search": full_family_search,
                "considered_families": sorted(considered_families),
                "projection_update_backend": backend,
                "sample_memory_enabled_for_evaluation": False,
                "sample_memory_enabled_for_update": False,
                "sample_memory_entry_count": memory_count,
                "seed": seed,
                "stopped_reason": report.get("stopped_reason"),
                "termination_reason": reason,
                "update_count": updates,
            }
        )
        print(json.dumps({"stage": "T2", "seed": seed, "updates": updates, "applied": applied, "elapsed": elapsed, "backend": backend}), flush=True)
        costs.append(
            cost_row(
                record_id=f"AF-029:T2:{seed}",
                record_kind="source_usage",
                experiment_arm="T2",
                phase="updates_selection",
                seed=seed,
                execution_status="measured" if not failure else "failure",
                elapsed_seconds=quantity("measured", True, "seconds", elapsed, "T2 packed_cpu wall time"),
                update_count=updates,
                accepted_epochs=updates,
                notes=reason,
                includes_failure=bool(failure),
            )
        )

        t3_model = AdaptiveModalAutoencoder(state=load_state_checkpoint(state_dir / f"T2-{seed}-final.json"), compute_device="cpu")
        t3_before = t3_model.state.to_dict()
        t3_protected_before = state_fingerprint(t3_before, exclude=PROOF_STATE_KEYS)
        begin_stage("T3", seed=seed)
        t3_started = time.time()
        t3_report = t3_model.train_proof_auxiliary_heads(
            admitted_records,
            expected_versions=pinned_versions,
            learning_rate=T3_LEARNING_RATE,
        )
        t3_elapsed = round(time.time() - t3_started, 3)
        t3_after = t3_model.state.to_dict()
        t3_protected_after = state_fingerprint(t3_after, exclude=PROOF_STATE_KEYS)
        t3_sha = sha256_obj(t3_after)
        t3_initial = sha256_obj(t3_before)
        save_state(
            state_dir / f"T3-{seed}-initial.json",
            t3_before,
            t3_initial,
            {"arm_id": "T3", "matched_t2": final_sha, "seed": seed},
        )
        save_state(
            state_dir / f"T3-{seed}-final.json",
            t3_after,
            t3_sha,
            {"arm_id": "T3", "matched_t2": final_sha, "seed": seed},
        )
        t3_eval = t3_model.evaluate_proof_auxiliary_heads(
            admitted_records, expected_versions=pinned_versions
        )
        isolation = t3_report.get("objective_isolation") or {}
        if isolation.get("protected_parameters_unchanged") is not True or t3_protected_before != t3_protected_after:
            raise SystemExit("T3 mutated protected primary/anti-copy state")
        t3_status = "measured" if admitted_records and t3_report.get("applied_count") else "partial"
        t3_reason = (
            "completed_isolated_proof_head_updates"
            if t3_report.get("applied_count")
            else "no_admitted_native_feedback"
            if not admitted_records
            else str(t3_report.get("status") or "no_applicable_feedback")
        )
        t3_seed = {
            "feedback_scope": FEEDBACK_SCOPE,
            "semantic_fidelity_measured": False,
            "applied_count": t3_report.get("applied_count"),
            "eligible_count": t3_report.get("eligible_count"),
            "execution_status": t3_status,
            "matched_t2_checkpoint_sha256": final_sha,
            "protected_fingerprint_after": t3_protected_after,
            "protected_fingerprint_before": t3_protected_before,
            "protected_parameters_unchanged": t3_protected_before == t3_protected_after,
            "seed": seed,
            "t3_final_checkpoint_sha256": t3_sha,
            "t3_initial_checkpoint_sha256": t3_initial,
            "t3_status": t3_report.get("status"),
            "termination_reason": t3_reason,
            "unresolved_gate": None if admitted_records else t3_gate,
            "update_count": int(t3_report.get("applied_count") or 0),
        }
        t3_by_seed.append(t3_seed)
        results.append(
            {
                "schema": SCHEMA_RESULT,
                "arm_id": "T3",
                "checkpoint": {
                    "final": t3_sha,
                    "initial": t3_initial,
                    "matched_t2": final_sha,
                },
                "claim_admissible": False,
                "config_id": config_id,
                "dataset_id": dataset_id,
                "elapsed_seconds": t3_elapsed,
                "execution_status": t3_status,
                "metrics": {
                    "applied_count": t3_report.get("applied_count"),
                    "calibration_error": t3_eval.get("calibration_error"),
                    "eligible_native_label_count": len(admitted_records),
                    "native_proof_coverage": None,
                    "source_fidelity": None,
                },
                "record_id": f"T3:{seed}:attempt",
                "record_kind": "t3_attempt",
                "result_kind": "bounded_observation" if t3_status == "measured" else "failure",
                "seed": seed,
                "split": "train",
                "task_id": TASK_ID,
                "termination_reason": t3_reason,
                "update_count": int(t3_report.get("applied_count") or 0),
                "detail": t3_seed,
            }
        )
        checkpoints.append(
            {
                "arm_id": "T3",
                "config_id": config_id,
                "dataset_id": dataset_id,
                "elapsed_seconds": t3_elapsed,
                "final_checkpoint_sha256": t3_sha,
                "initial_checkpoint_sha256": t3_initial,
                "matched_t2_checkpoint_sha256": final_sha,
                "protected_parameters_unchanged": True,
                "sample_memory_enabled_for_evaluation": False,
                "sample_memory_enabled_for_update": False,
                "seed": seed,
                "termination_reason": t3_reason,
                "update_count": int(t3_report.get("applied_count") or 0),
            }
        )
        print(json.dumps({"stage": "T3", "seed": seed, "applied": t3_report.get("applied_count"), "elapsed": t3_elapsed}), flush=True)
        costs.append(
            cost_row(
                record_id=f"AF-029:T3:{seed}",
                record_kind="source_usage",
                experiment_arm="T3",
                phase="updates_selection",
                seed=seed,
                execution_status=t3_status,
                elapsed_seconds=quantity("measured", True, "seconds", t3_elapsed, "T3 isolated proof-head wall time"),
                update_count=int(t3_report.get("applied_count") or 0),
                notes=t3_reason,
            )
        )

    final_test_n = int(splits["counts"]["final_test"]["natural_source_units"])
    canary_n = int(splits["counts"]["fixed_canary"]["natural_source_units"])
    for arm_id in ("T0", "T1", "T2", "T3"):
        results.append(
            locked_split_row(
                arm_id, "final_test", final_test_n,
                "final_test_locked_until_model_freeze; identities and bodies were not opened",
            )
        )
        results.append(
            locked_split_row(
                arm_id, "fixed_canary", canary_n,
                "fixed_canary_not_used_for_training_or_hyperparameter_selection",
            )
        )

    begin_stage("publish")
    preparation = json.loads((INPUT_EVIDENCE_DIR / "preparation" / "cost_receipt.json").read_text(encoding="utf-8"))
    costs.append(
        cost_row(
            record_id="AF-029:preparation:encoder",
            record_kind="source_usage",
            experiment_arm="encoder_preparation",
            phase="preparation",
            execution_status="measured",
            elapsed_seconds=quantity(
                "measured",
                True,
                "seconds",
                preparation["sum_nonoverlapping_process_wall_seconds"],
                "five preparation attempts charged once; container-attach wall is overlapping and not added",
            ),
            cpu_seconds=quantity(
                "measured",
                True,
                "cpu_seconds",
                preparation["sum_process_cpu_seconds"],
                "sum of five preparation process CPU seconds, charged once",
            ),
            notes="Carry-forward of evidence/native_training/preparation/cost_receipt.json; not an AF-020 rewrite",
            preparation_attempts=preparation["attempts"],
            asset_copy_setup_cost=preparation["asset_copy_setup_cost"],
        ),
    )
    costs.append(
        cost_row(
            record_id="AF-029:target_construction",
            record_kind="source_usage",
            experiment_arm="compiler_targets",
            phase="target_construction",
            execution_status="measured",
            elapsed_seconds=quantity("measured", True, "seconds", target_elapsed, "IntentFormalizationCompiler train/selection targets"),
            unit_count=84,
            notes=f"compile_failures={compile_failures}",
        )
    )
    costs.append(
        cost_row(
            record_id="AF-029:native_checker_feedback",
            record_kind="source_usage",
            experiment_arm="T3-feedback",
            phase="proof_reconstruction",
            execution_status="measured",
            elapsed_seconds=quantity("measured", True, "seconds", checker_elapsed, "Lean/Z3 feedback on train obligations"),
            unit_count=len(checker_receipts),
            notes=f"admitted={len(admitted_records)}",
        )
    )

    teacher_manifest = {
        "schema": SCHEMA_TEACHER,
        "task_id": TASK_ID,
        "created_at": utc_now(),
        "encoder": {
            "model_id": encoder_inputs["model_id"],
            "revision": encoder_inputs["model_revision"],
            "tokenization": "WordPiece without truncation; 254-content-token windows plus specials",
            "window_aggregation": "attention-mask mean pool, L2 per window, content-token-weighted average, document L2",
            "inputs_sha256": INPUTS_SHA256,
            "preprocessing_manifest_sha256": frozen_inputs["preprocessing_manifest_sha256"],
            "source_gold": False,
            "independent_gold": False,
            "mock": False,
        },
        "producer": {
            "entry_point": "ipfs_datasets_py.logic.intent_ir.formalize.compiler.IntentFormalizationCompiler",
            "source": "external/ipfs_datasets/ipfs_datasets_py/logic/intent_ir/formalize/compiler.py",
            "source_sha256": sha256_file(
                REPO_ROOT / "external/ipfs_datasets/ipfs_datasets_py/logic/intent_ir/formalize/compiler.py"
            ),
            "vocabulary": "intent-ir-view-registry/v1",
            "version": INTENT_FORMALIZATION_COMPILER_VERSION,
            "proof_backend_execution": False,
        },
        "population": {"train": 69, "selection": 15, "final_test": 0},
        "targets_produced": len(teacher_rows),
        "compile_failures": compile_failures,
        "empty_target_map": False,
        "rows": teacher_rows,
        "native_checker_feedback": {
            "feedback_scope": FEEDBACK_SCOPE,
            "semantic_fidelity_measured": False,
            "coverage": feedback_coverage,
            "previous_constant_138_checks_excluded": True,
            "admitted_records": len(admitted_records),
            "receipts": len(checker_receipts),
            "unresolved_gate": None if admitted_records else "empty_or_untrusted_feedback",
            "constructed_isolation_probes_are_not_t3_labels": True,
        },
        "final_test_access": False,
        "human_review": "pending_AF-028",
    }
    write_json(OUTPUT_ROOT / "data" / "native_training_teacher_manifest.json", teacher_manifest)
    write_jsonl(EVIDENCE_DIR / "native_checker_receipts.jsonl", checker_receipts)
    write_json(
        EVIDENCE_DIR / "admitted_feedback.json",
        {
            "admitted_count": len(admitted_records),
            "records": [jsonable(record.to_dict()) for record in admitted_records],
            "version_fingerprint": pinned_versions.fingerprint,
        },
    )
    write_json(EVIDENCE_DIR / "packed_cpu_reports.json", packed_summaries)
    write_json(EVIDENCE_DIR / "t2_memory_checks.json", t2_live_memory_checks)
    write_json(EVIDENCE_DIR / "prepared_input_verification.json", prepared)
    write_json(EVIDENCE_DIR / "runtime_identity.json", env)
    write_json(EVIDENCE_DIR / "t3_protected_state.json", t3_by_seed)

    t2_changed = all(item.get("parameter_changed") for item in packed_summaries)
    run_manifest = {
        "schema": SCHEMA_MANIFEST,
        "task_id": TASK_ID,
        "created_at": utc_now(),
        "config_id": config_id,
        "dataset_id": dataset_id,
        "frozen_inputs": frozen_inputs,
        "environment": {
            "research_toolchain_sha256": env["research_toolchain_sha256"],
            "torch": env["packages"]["torch"],
            "numpy": env["packages"]["numpy"],
            "native_checkers": {
                name: env["native_checkers"][name]
                for name in ("lean", "z3", "cvc5")
            },
            "resource_limits": env["resource_limits"],
            "projection_update_backend": REQUESTED_T2_BACKEND,
            "stripped_profile_is_error": True,
            "narrow_validator_is_separate": True,
        },
        "config": config,
        "arms": {
            "T0": {
                "executed": True,
                "replays": T0_REPLAYS,
                "deterministic_metric_hashes": t0_metric_hashes,
                "deterministic_across_replays": len(set(t0_metric_hashes)) == 1,
                "update_count": 0,
            },
            "T1": {
                "executed": True,
                "seeds": list(SEEDS),
                "memory_diagnostic": True,
            },
            "T2": {
                "executed": True,
                "seeds": list(SEEDS),
                "projection_update_backend": REQUESTED_T2_BACKEND,
                "sample_memory_disabled": True,
                "parameter_changed": t2_changed,
                "packed_cpu": packed_summaries,
            },
            "T3": {
                "feedback_scope": FEEDBACK_SCOPE,
                "semantic_fidelity_measured": False,
                "executed": bool(admitted_records),
                "partial": not admitted_records,
                "seeds": list(SEEDS),
                "admitted_feedback": len(admitted_records),
                "unresolved_gate": None if admitted_records else t3_gate,
            },
        },
        "final_test_locked": True,
        "promotion": {
            "e_locked": True,
            "requires_af013_identity_bound_canary": True,
            "generic_file_existence_insufficient": True,
        },
        "repair_provenance": repair_provenance,
        "checkpoint_reload_verification": SAVED_CHECKPOINTS,
        "preserved_prior": {
            "AF-011": "papers/completion/autoformalization/receipts/AF-011.json",
            "AF-012": "papers/completion/autoformalization/receipts/AF-012.json",
            "AF-020": "papers/completion/autoformalization/receipts/AF-020.json",
        },
        "t2_memory_contract": t2_contract,
        "t2_live_memory_checks": t2_live_memory_checks,
        "wall_seconds": round(time.time() - started, 3),
        "cpu_seconds": round(time.process_time() - cpu_started, 3),
    }
    write_json(OUTPUT_ROOT / "runs" / "native_training" / "manifest.json", run_manifest)
    write_jsonl(OUTPUT_ROOT / "runs" / "native_training" / "results.jsonl", results)
    write_jsonl(OUTPUT_ROOT / "runs" / "native_training" / "costs.jsonl", costs)

    t2_identities = [item["final_checkpoint_sha256"] for item in checkpoints if item["arm_id"] == "T2"]
    t3_identities = [item["final_checkpoint_sha256"] for item in checkpoints if item["arm_id"] == "T3"]
    checkpoint_manifest = {
        "schema": SCHEMA_CHECKPOINTS,
        "task_id": TASK_ID,
        "created_at": utc_now(),
        "config_id": config_id,
        "dataset_id": dataset_id,
        "encoder": teacher_manifest["encoder"],
        "teacher_manifest": "papers/completion/autoformalization/data/native_training_teacher_manifest.json",
        "teacher_manifest_sha256": sha256_file(OUTPUT_ROOT / "data" / "native_training_teacher_manifest.json"),
        "mock_teacher": False,
        "promotion_unlocked": False,
        "e_locked_until": "AF-013 canary/consumer receipt naming these exact identities",
        "generic_file_existence_insufficient": True,
        "completed_task_status_insufficient": True,
        "export_alone_insufficient": True,
        "eligible_checkpoint_identities": t2_identities + t3_identities,
        "t2_identities": t2_identities,
        "t3_identities": t3_identities,
        "native_update_receipts": packed_summaries,
        "repair_provenance": repair_provenance,
        "checkpoint_reload_verification": SAVED_CHECKPOINTS,
        "native_feedback_receipts": len(checker_receipts),
        "feedback_scope": FEEDBACK_SCOPE,
        "semantic_fidelity_measured": False,
        "feedback_coverage": feedback_coverage,
        "admitted_feedback": len(admitted_records),
        "protected_state_comparisons": t3_by_seed,
        "final_test_used_to_select_settings": False,
        "runs": checkpoints,
    }
    write_json(OUTPUT_ROOT / "checkpoints" / "native_training" / "manifest.json", checkpoint_manifest)
    write_json(
        EVIDENCE_DIR / "eligible_checkpoint_binding.json",
        {
            "eligible_checkpoint_identities": t2_identities + t3_identities,
            "t2_identities": t2_identities,
            "t3_identities": t3_identities,
            "teacher_manifest_sha256": checkpoint_manifest["teacher_manifest_sha256"],
            "e_locked": True,
        },
    )
    summary = {
        "admitted_feedback": len(admitted_records),
        "checker_receipts": len(checker_receipts),
        "config_id": config_id,
        "dataset_id": dataset_id,
        "packed_cpu": packed_summaries,
        "t2_changed": t2_changed,
        "targets": len(teacher_rows),
        "wall_seconds": run_manifest["wall_seconds"],
    }
    write_json(EVIDENCE_DIR / "execution_summary.json", summary)
    print(json.dumps(summary, sort_keys=True))
    end_stage()
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except BaseException as exc:
        if ACTIVE_STAGE is not None:
            end_stage("failed", error_type=type(exc).__name__, error=str(exc)[:1000])
        raise
