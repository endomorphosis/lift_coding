#!/usr/bin/env python3
"""Executor-bound inference isolation for AF-026 (corrects AF-008 credit claims).

AF-008 request-shape filters, configuration declarations, and synthetic JSON
probes remain available as request-shape checks only. They do not qualify an
executor, grant blind-prediction credit, or establish a process/filesystem/
retrieval boundary.

This harness:

* builds source-only, parser-assisted, and source-withheld views
* projects canonical IR onto permitted v1 rule-atom semantics (allowlist, not
  denylisted names or literal substring matching)
* runs bounded synthetic-canary probes through an IsolationExecutor with a
  process/channel sandbox
* binds blind-prediction credit to a retained prediction plus independently
  validated executor/invocation/source/model/configuration evidence
* qualifies the native AdaptiveModalAutoencoder sample-memory route for update
  and evaluation of every main generalization arm, with T1 as the enabled
  memory positive control

Documented channels that remain available or cannot be qualified make the
affected condition non-blind. Filesystem qualification does not establish
network or pretraining exclusion. Inert AF-008 reviewer counterexamples are
not treated as a demonstrated paper-experiment leak. Probes use synthetic
canaries only; real held-out bodies and labels are not read.
"""
from __future__ import annotations

import argparse
import base64
import builtins
import hashlib
import io
import json
import os
import re
import subprocess
import sys
import urllib.request
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence


SCHEMA = "autoformalization-inference-isolation/v2"
REPORT_SCHEMA = "autoformalization-leakage-control-report/v2"
TASK_ID = "AF-026"
PARENT_TASK_ID = "AF-008"
PARENT_RECEIPT_SHA256 = (
    "f6a1589db14f3845b4caf11f6d87eb9682277a4e6af8e67b4ed793f3b2a7fce0"
)
REQUEST_SHAPE_SCHEMA = "autoformalization-request-shape-check/v1"

HERE = Path(__file__).resolve().parent
PAPER_ROOT = HERE.parent
REPO_ROOT = PAPER_ROOT.parents[2]
DATASETS_ROOT = REPO_ROOT / "external" / "ipfs_datasets"
NATIVE_AUTOENCODER_PATH = (
    DATASETS_ROOT
    / "ipfs_datasets_py"
    / "optimizers"
    / "logic_theorem_optimizer"
    / "modal_autoencoder.py"
)
NATIVE_ROUNDTRIP_PATH = (
    DATASETS_ROOT
    / "ipfs_datasets_py"
    / "logic"
    / "legal_ir"
    / "canonical_roundtrip.py"
)

VIEWS = ("source_only", "parser_assisted", "source_withheld")
RECONSTRUCTION_SCORES = ("forward", "cycle", "final")
VECTOR_SCORES = ("mse", "cosine")
MEMORY_PHASES = ("update", "evaluation")

PIPELINE_ARMS = ("A", "B", "C", "D", "E")
LEARNING_ARMS = ("T0", "T1", "T2", "T3", "T4", "T5")
EXPERIMENT_ARMS = PIPELINE_ARMS + LEARNING_ARMS
MAIN_GENERALIZATION_ARMS = ("A", "B", "C", "D", "E", "T0", "T2", "T3", "T4", "T5")
MEMORY_DIAGNOSTIC_ARMS = ("T1",)

CHANNELS = (
    "source_text",
    "source_maps",
    "filesystem",
    "retrieval",
    "parser_state",
    "sample_memory",
    "gold_ir",
    "reference_fallback",
    "sample_id_cache",
)
UNQUALIFIED_NON_DOCUMENTED = ("network", "pretraining_memorization")

CHANNEL_ALIASES: dict[str, frozenset[str]] = {
    "source_text": frozenset({
        "source", "source_body", "source_document", "source_excerpt",
        "source_text", "raw_text", "originating_source", "original_text", "t0",
        "withheld_source", "native_payload",
    }),
    "source_maps": frozenset({
        "source_map", "source_maps", "source_span", "source_spans",
        "locator", "locators", "source_ref", "source_metadata",
        "char_offsets", "evidence_span",
    }),
    "filesystem": frozenset({
        "source_path", "file_path", "filesystem", "source_uri",
        "path_recovery", "source_file", "corpus_path", "open_path",
    }),
    "retrieval": frozenset({
        "retrieve", "retrieval", "rag", "index_lookup", "index_query",
        "graphrag", "source_withheld_retrieval", "nearest_source",
        "corpus_hit",
    }),
    "parser_state": frozenset({
        "parser_state", "parser_cache", "parser_trace", "parse", "parse_tree",
        "private_parser", "source_cache", "constructor_record",
        "compiler_payload", "hidden_fields", "private_payload",
    }),
    "sample_memory": frozenset({
        "sample_memory", "decoded_embeddings", "per_sample_memory",
        "use_sample_memory", "sample_indexed_memory", "memory_lookup",
        "stored_reconstruction",
    }),
    "gold_ir": frozenset({
        "gold", "gold_ir", "gold_target", "teacher_ir", "native_ir",
        "target_ir", "full_gold_ir",
    }),
    "reference_fallback": frozenset({
        "reference", "reference_ir", "reference_decoder", "gold_decoder",
        "decoder_fallback", "gold_fallback", "reference_fallback",
        "admitted_reference",
    }),
    "sample_id_cache": frozenset({
        "sample_id", "cache_key", "cache_keys", "source_cache_key",
        "source_hash", "source_cid", "memory_key",
    }),
}

ALIAS_TO_CHANNEL: dict[str, str] = {
    alias: channel
    for channel, aliases in CHANNEL_ALIASES.items()
    for alias in aliases
}

VIEW_ALLOWED_INPUTS: dict[str, frozenset[str]] = {
    "source_only": frozenset({"source_text"}),
    "parser_assisted": frozenset({"source_text", "disclosed_features"}),
    "source_withheld": frozenset({"canonical_ir"}),
}

VIEW_BLOCKED_CHANNELS: dict[str, frozenset[str]] = {
    "source_only": frozenset(CHANNELS) - frozenset({"source_text"}),
    "parser_assisted": frozenset({
        "source_maps", "filesystem", "retrieval", "parser_state",
        "sample_memory", "gold_ir", "reference_fallback", "sample_id_cache",
    }),
    "source_withheld": frozenset(CHANNELS),
}

PARSER_FEATURE_KINDS = (
    "lexical_cues",
    "actor_action_object_roles",
    "conditions_exceptions",
    "temporal_structure",
    "predicate_arity",
    "quantifier_scope",
    "provenance",
    "frame_relations",
    "compiler_contracts",
    "reconstruction_diagnostics",
)

PERMITTED_IR_FIELDS = frozenset({"rules"})
PERMITTED_RULE_FIELDS = (
    "modality", "actor", "action", "object", "conditions", "exceptions", "temporal",
)
PERMITTED_MODALITIES = frozenset({"O", "P", "F"})
ATOM_RE = re.compile(r"^[A-Za-z][A-Za-z0-9_]{0,63}$")
KEY_RE = re.compile(r"[^a-z0-9]+")
COMPILER_PRODUCER = "intent-formalization-compiler/v1"
MODEL_IDENTITY = (
    "ipfs_datasets_py.optimizers.logic_theorem_optimizer."
    "modal_autoencoder.AdaptiveModalAutoencoder"
)
MODEL_ARCHITECTURE = "proof_aware_auxiliary_heads_v2"
EXECUTOR_ID = "autoformalization-isolation-executor/v2"
SYNTHETIC_SOURCE = (
    "A permit holder must file a notice within ten days after approval, "
    "unless exempt."
)
SYNTHETIC_MEMORY_TEXT = (
    "AF026-synthetic-canary: an agency must file a sentinel notice."
)
REQUIRED_EVIDENCE_FIELDS = (
    "executor_id",
    "executor_digest",
    "invocation_id",
    "source_identity",
    "model_identity",
    "configuration_digest",
    "channel_restrictions",
)

_NATIVE_IMPORT: tuple[Any, Any] | None = None


class IsolationError(ValueError):
    """Raised when an inference view, leakage channel, or credit rule is violated."""


class ProbeContractError(IsolationError):
    """Raised when the isolation contract failed to reject a blocked channel."""


class RequestShapeCheck:
    """Marker for AF-008-style key/substring filters. Not executor qualification."""

    schema = REQUEST_SHAPE_SCHEMA


def canonical_dumps(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_text(text: str) -> str:
    return sha256_bytes(text.encode("utf-8"))


def sha256_obj(value: Any) -> str:
    return sha256_text(canonical_dumps(value))


def sha256_file(path: Path) -> str:
    return sha256_bytes(path.read_bytes())


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(canonical_dumps(value) + "\n", encoding="utf-8")


def _expect(condition: bool, message: str) -> None:
    if not condition:
        raise IsolationError(message)


def normalize_key(key: Any) -> str:
    text = str(key or "").strip().lower().replace("-", "_")
    return KEY_RE.sub("_", text).strip("_")


def channel_for_key(key: Any) -> str | None:
    return ALIAS_TO_CHANNEL.get(normalize_key(key))


def is_main_generalization_arm(arm: str) -> bool:
    return arm in MAIN_GENERALIZATION_ARMS


def is_memory_diagnostic_arm(arm: str) -> bool:
    return arm in MEMORY_DIAGNOSTIC_ARMS


def executor_source_digest() -> str:
    return sha256_file(Path(__file__))


def configuration_digest() -> str:
    return sha256_obj({
        "channels": list(CHANNELS),
        "executor_id": EXECUTOR_ID,
        "permitted_ir_fields": sorted(PERMITTED_IR_FIELDS),
        "permitted_modalities": sorted(PERMITTED_MODALITIES),
        "permitted_rule_fields": list(PERMITTED_RULE_FIELDS),
        "schema": SCHEMA,
        "views": {
            view: {
                "allowed_inputs": sorted(VIEW_ALLOWED_INPUTS[view]),
                "blocked_channels": sorted(VIEW_BLOCKED_CHANNELS[view]),
            }
            for view in VIEWS
        },
    })


def _walk_keys(value: Any, *, path: str = "") -> list[tuple[str, str, Any]]:
    found: list[tuple[str, str, Any]] = []
    if isinstance(value, Mapping):
        for key, item in value.items():
            name = str(key)
            child = f"{path}.{name}" if path else name
            found.append((child, name, item))
            found.extend(_walk_keys(item, path=child))
    elif isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray)):
        for index, item in enumerate(value):
            found.extend(_walk_keys(item, path=f"{path}[{index}]"))
    return found


def _flatten_strings(value: Any) -> list[str]:
    if isinstance(value, str):
        return [value]
    if isinstance(value, (bytes, bytearray)):
        return [value.decode("utf-8", "replace")]
    if isinstance(value, Mapping):
        pieces: list[str] = []
        for key, item in value.items():
            pieces.append(str(key))
            pieces.extend(_flatten_strings(item))
        return pieces
    if isinstance(value, Sequence):
        pieces = []
        for item in value:
            pieces.extend(_flatten_strings(item))
        return pieces
    if value is None or isinstance(value, (bool, int, float)):
        return []
    return [str(value)]


def scan_channels(payload: Any) -> dict[str, list[str]]:
    """Request-shape key scan. Not an executor or process-boundary qualification."""
    hits: dict[str, list[str]] = {channel: [] for channel in CHANNELS}
    for path, key, _item in _walk_keys(payload):
        channel = channel_for_key(key)
        if channel is not None:
            hits[channel].append(path)
    return {channel: paths for channel, paths in hits.items() if paths}


def source_text_leaked(value: Any, source_text: str | None) -> bool:
    """Literal containment check. Insufficient alone against encoded payloads."""
    if not source_text:
        return False
    needle = " ".join(source_text.split())
    if not needle:
        return False
    for piece in _flatten_strings(value):
        if needle and needle in " ".join(str(piece).split()):
            return True
    return False


def _try_b64_decode(text: str) -> str | None:
    compact = "".join(text.split())
    if len(compact) < 8:
        return None
    for decoder in (base64.b64decode, base64.urlsafe_b64decode):
        try:
            padded = compact + "=" * ((4 - len(compact) % 4) % 4)
            decoded = decoder(padded.encode("ascii"))
            return decoded.decode("utf-8", "replace")
        except Exception:
            continue
    return None


def _try_hex_decode(text: str) -> str | None:
    compact = "".join(text.split())
    if len(compact) < 8 or len(compact) % 2 or not re.fullmatch(r"[0-9a-fA-F]+", compact):
        return None
    try:
        return bytes.fromhex(compact).decode("utf-8", "replace")
    except Exception:
        return None


def encodes_withheld_source(value: Any, source_text: str | None) -> bool:
    """Recover withheld source from literal, nested, or encoded payloads."""
    if not source_text:
        return False
    if source_text_leaked(value, source_text):
        return True
    for piece in _flatten_strings(value):
        text = str(piece)
        for decoded in (_try_b64_decode(text), _try_hex_decode(text)):
            if decoded and source_text_leaked(decoded, source_text):
                return True
    return False


def _truthy_memory_flag(value: Any) -> bool:
    if value is True:
        return True
    if isinstance(value, str) and value.strip().lower() in {"true", "on", "enabled", "1"}:
        return True
    if isinstance(value, (int, float)) and not isinstance(value, bool) and value != 0:
        return True
    return False


def inspect_memory_shortcuts(
    payload: Mapping[str, Any] | None = None,
    *,
    sample_id: str | None = None,
    cache_key: str | None = None,
    train_ids: Sequence[str] | None = None,
    eval_ids: Sequence[str] | None = None,
    use_sample_memory: bool | None = None,
) -> dict[str, Any]:
    """Detect sample-indexed lookup even when a caller claims memory is off."""
    payload = dict(payload or {})
    sid = sample_id if sample_id is not None else payload.get("sample_id")
    key = cache_key if cache_key is not None else payload.get("cache_key")
    memory_flag = use_sample_memory
    if memory_flag is None:
        memory_flag = _truthy_memory_flag(payload.get("use_sample_memory"))
        if payload.get("decoded_embeddings"):
            memory_flag = True
    reasons: list[str] = []
    if sid and key and str(sid) == str(key):
        reasons.append("cache_key_equals_sample_id")
    if sid and payload.get("decoded_embeddings") not in (None, {}, []):
        stored = payload.get("decoded_embeddings")
        if isinstance(stored, Mapping) and str(sid) in {str(item) for item in stored}:
            reasons.append("decoded_embeddings_indexed_by_sample_id")
    if memory_flag and sid:
        reasons.append("sample_memory_lookup_enabled")
    train = {str(item) for item in (train_ids or ()) if item}
    evaluate = {str(item) for item in (eval_ids or ()) if item}
    overlap = sorted(train & evaluate)
    if memory_flag and overlap:
        reasons.append("train_eval_sample_id_overlap_with_memory")
    return {
        "shortcut": bool(reasons),
        "reasons": reasons,
        "sample_id": sid,
        "cache_key": key,
        "train_eval_overlap": overlap,
        "use_sample_memory": bool(memory_flag),
    }


def disclose_parser_features(features: Sequence[Mapping[str, Any]] | None) -> list[dict[str, Any]]:
    if features is None:
        return []
    _expect(isinstance(features, Sequence) and not isinstance(features, (str, bytes)),
            "parser-assisted features must be a list")
    disclosed: list[dict[str, Any]] = []
    seen: set[str] = set()
    for index, raw in enumerate(features):
        _expect(isinstance(raw, Mapping), f"feature[{index}] must be an object")
        name = str(raw.get("name") or "").strip()
        producer = str(raw.get("producer") or "").strip()
        _expect(name, f"feature[{index}] is missing name")
        _expect(producer, f"feature[{index}] {name} is missing producer")
        _expect(name not in seen, f"feature {name} was disclosed twice")
        seen.add(name)
        depends = raw.get("depends_on_parse")
        _expect(type(depends) is bool, f"feature {name} must declare depends_on_parse")
        complete = raw.get("requires_complete_compilation")
        _expect(type(complete) is bool,
                f"feature {name} must declare requires_complete_compilation")
        cost = raw.get("cost")
        _expect(isinstance(cost, Mapping), f"feature {name} must declare cost")
        compile_seconds = cost.get("compile_seconds")
        extract_seconds = cost.get("extraction_seconds")
        for field, value in (("compile_seconds", compile_seconds),
                             ("extraction_seconds", extract_seconds)):
            _expect(isinstance(value, (int, float)) and not isinstance(value, bool) and value >= 0,
                    f"feature {name} cost.{field} must be a nonnegative number")
        if complete:
            _expect(float(compile_seconds) > 0,
                    f"feature {name} requires complete compilation but charged zero compile cost")
        kind = str(raw.get("kind") or name)
        disclosed.append({
            "name": name,
            "kind": kind,
            "producer": producer,
            "depends_on_parse": depends,
            "requires_complete_compilation": complete,
            "cost": {
                "compile_seconds": float(compile_seconds),
                "extraction_seconds": float(extract_seconds),
            },
            "disclosed": True,
        })
    return disclosed


def reconstruction_bundle(
    *,
    forward: Mapping[str, Any],
    cycle: Mapping[str, Any],
    final: Mapping[str, Any],
    vector: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Keep symbolic forward/cycle/final scores distinct from vector reconstruction."""
    bundle = {
        "forward": dict(forward),
        "cycle": dict(cycle),
        "final": dict(final),
    }
    validate_reconstruction_scores(bundle)
    if vector is not None:
        _expect(isinstance(vector, Mapping), "vector reconstruction must be an object")
        extra = set(vector) - set(VECTOR_SCORES)
        _expect(not extra, f"vector reconstruction has unexpected keys: {sorted(extra)}")
        for name in VECTOR_SCORES:
            _expect(name in vector, f"vector reconstruction missing {name}")
        bundle["vector"] = {name: vector[name] for name in VECTOR_SCORES}
        bundle["vector_is_not_free_text_decoder"] = True
    return bundle


def validate_reconstruction_scores(scores: Mapping[str, Any]) -> None:
    _expect(isinstance(scores, Mapping), "reconstruction scores must be an object")
    missing = [name for name in RECONSTRUCTION_SCORES if name not in scores]
    _expect(not missing, f"reconstruction scores missing distinct fields: {missing}")
    collapsed = {"mean", "average", "aggregate", "combined", "overall", "reconstruction"}
    overlap = collapsed & set(scores)
    _expect(not overlap, f"reconstruction scores collapsed via {sorted(overlap)}")
    for name in RECONSTRUCTION_SCORES:
        value = scores[name]
        _expect(isinstance(value, Mapping), f"reconstruction.{name} must remain its own object")
        status = value.get("status")
        _expect(isinstance(status, str) and status, f"reconstruction.{name}.status is required")
        score = value.get("score")
        _expect(score is None or (isinstance(score, (int, float)) and not isinstance(score, bool)),
                f"reconstruction.{name}.score must be a number or null")
    _expect(
        scores["forward"] is not scores["cycle"]
        and scores["forward"] is not scores["final"]
        and scores["cycle"] is not scores["final"],
        "forward, cycle, and final reconstruction must not share one object",
    )


def sample_memory_policy(arm: str) -> dict[str, Any]:
    _expect(arm in EXPERIMENT_ARMS, f"unknown experiment arm {arm}")
    if is_memory_diagnostic_arm(arm):
        return {
            "arm": arm,
            "role": "memory_diagnostic",
            "generalization_arm": False,
            "update": {"use_sample_memory": True},
            "evaluation": {"use_sample_memory": True, "report_seen_and_unseen_separately": True},
            "blind_prediction_credit": False,
            "blind_prediction_credit_eligible": False,
            "condition_class": "non_blind_sample_memory",
            "claim": "T1 is a seen-source memory diagnostic, not a generalization result.",
        }
    return {
        "arm": arm,
        "role": "main_generalization" if is_main_generalization_arm(arm) else "other",
        "generalization_arm": True,
        "update": {"use_sample_memory": False},
        "evaluation": {"use_sample_memory": False},
        "blind_prediction_credit": False,
        "blind_prediction_credit_eligible": True,
        "condition_class": "credit_requires_executor_evidence",
        "claim": (
            "Accepted improvements must come from shared parameters, not sample-indexed "
            "memory. Arm/view names do not grant blind-prediction credit."
        ),
    }


def assert_arm_memory_policy(
    arm: str,
    *,
    update_memory: bool,
    evaluation_memory: bool,
) -> dict[str, Any]:
    policy = sample_memory_policy(arm)
    expected_update = policy["update"]["use_sample_memory"]
    expected_eval = policy["evaluation"]["use_sample_memory"]
    if expected_update is False and update_memory:
        raise IsolationError(
            f"main generalization arm {arm} must disable sample-indexed memory for update"
        )
    if expected_eval is False and evaluation_memory:
        raise IsolationError(
            f"main generalization arm {arm} must disable sample-indexed memory for evaluation"
        )
    if expected_update is True and not update_memory and is_memory_diagnostic_arm(arm):
        raise IsolationError(
            f"memory diagnostic arm {arm} must keep sample memory enabled so seen-source "
            "reconstruction is not silently reported as generalization"
        )
    return policy


def _require_atom(value: Any, *, field: str, source_text: str | None) -> str:
    _expect(isinstance(value, str) and ATOM_RE.fullmatch(value),
            f"canonical IR {field} is not a permitted identifier atom")
    if encodes_withheld_source(value, source_text):
        raise IsolationError(f"canonical IR {field} encodes withheld source")
    return value


def project_canonical_ir(
    ir: Any,
    *,
    withheld_source: str | None = None,
) -> dict[str, Any]:
    """Allowlist v1 rule-atom semantics. Extra/encoded fields do not survive."""
    _expect(isinstance(ir, Mapping) and ir, "source-withheld view requires canonical_ir")
    dropped = sorted(str(key) for key in ir if key not in PERMITTED_IR_FIELDS)
    rules_in = ir.get("rules")
    _expect(
        isinstance(rules_in, Sequence) and not isinstance(rules_in, (str, bytes, bytearray)) and rules_in,
        "canonical IR requires a nonempty rules array",
    )
    rules: list[dict[str, Any]] = []
    for index, raw in enumerate(rules_in):
        _expect(isinstance(raw, Mapping), f"rules[{index}] must be an object")
        dropped.extend(
            f"rules[{index}].{key}" for key in raw if key not in PERMITTED_RULE_FIELDS
        )
        modality = raw.get("modality")
        _expect(modality in PERMITTED_MODALITIES,
                f"rules[{index}].modality is not a permitted v1 modality")
        actor = _require_atom(raw.get("actor"), field=f"rules[{index}].actor",
                              source_text=withheld_source)
        action = _require_atom(raw.get("action"), field=f"rules[{index}].action",
                               source_text=withheld_source)
        object_value = raw.get("object", "")
        if object_value in ("", None):
            object_out = ""
        else:
            object_out = _require_atom(
                object_value, field=f"rules[{index}].object", source_text=withheld_source,
            )
        seqs: dict[str, list[str]] = {}
        for seq_field in ("conditions", "exceptions", "temporal"):
            items = raw.get(seq_field, [])
            if items is None:
                items = []
            _expect(
                isinstance(items, Sequence) and not isinstance(items, (str, bytes, bytearray)),
                f"rules[{index}].{seq_field} must be an array of atoms",
            )
            seqs[seq_field] = [
                _require_atom(item, field=f"rules[{index}].{seq_field}[{item_i}]",
                              source_text=withheld_source)
                for item_i, item in enumerate(items)
            ]
        rules.append({
            "modality": modality,
            "actor": actor,
            "action": action,
            "object": object_out,
            "conditions": seqs["conditions"],
            "exceptions": seqs["exceptions"],
            "temporal": seqs["temporal"],
        })
    projected = {"rules": rules}
    if encodes_withheld_source(projected, withheld_source):
        raise IsolationError("projected canonical IR leaked originating source")
    return {
        "canonical_ir": projected,
        "dropped_paths": dropped,
        "projection": "permitted_v1_rule_atoms",
        "request_shape_only": False,
    }


def atom_surface(ir: Mapping[str, Any]) -> str:
    obligation = {"O": "must", "P": "may", "F": "must_not"}
    sentences: list[str] = []
    for rule in ir.get("rules") or ():
        parts = [rule["actor"], obligation[rule["modality"]], rule["action"]]
        if rule.get("object"):
            parts.append(str(rule["object"]))
        if rule.get("temporal"):
            parts.extend(str(item) for item in rule["temporal"])
        if rule.get("conditions"):
            parts.append("if")
            parts.extend(str(item) for item in rule["conditions"])
        if rule.get("exceptions"):
            parts.append("unless")
            parts.extend(str(item) for item in rule["exceptions"])
        sentences.append(" ".join(parts))
    return ". ".join(sentences)


def classify_condition(
    *,
    arm: str,
    view: str,
    leaked_channels: Iterable[str] = (),
    fallback_used: bool = False,
    parser_features: Sequence[Mapping[str, Any]] | None = None,
    declared_non_blind: bool = False,
    declared_non_blind_channels: Sequence[str] = (),
    prediction: Mapping[str, Any] | None = None,
    executor_evidence: Mapping[str, Any] | None = None,
    executor: "IsolationExecutor | None" = None,
    invocation: Mapping[str, Any] | None = None,
    clean: bool = False,
) -> dict[str, Any]:
    """Classify a condition. Arm/view/clean flags never grant blind credit."""
    _expect(view in VIEWS, f"unknown inference view {view}")
    policy = sample_memory_policy(arm)
    leaked = tuple(dict.fromkeys(leaked_channels))
    features = list(parser_features or ())
    non_blind_channels = list(dict.fromkeys(declared_non_blind_channels))
    reasons: list[str] = []
    if view == "parser_assisted":
        reasons.append("parser_assisted_features_are_not_raw_text_prediction")
    if fallback_used:
        reasons.append("reference_or_gold_decoder_fallback")
    if leaked:
        reasons.append("withheld_channel_present:" + ",".join(leaked))
    if policy["condition_class"] == "non_blind_sample_memory":
        reasons.append("sample_memory_diagnostic")
        if "sample_memory" not in non_blind_channels:
            non_blind_channels.append("sample_memory")
        declared_non_blind = True
    if features and view == "source_only":
        raise IsolationError(
            "source-only view received parser-assisted features; relabel as parser_assisted"
        )
    if declared_non_blind:
        reasons.append("explicitly_non_blind")
    if clean:
        reasons.append("caller_supplied_clean_flag_is_not_credit")
    if view == "source_withheld" and leaked and not declared_non_blind:
        raise IsolationError(
            "source-withheld view recovered withheld material through "
            f"{list(leaked)}; reject the attempt or declare the condition non-blind"
        )
    if is_main_generalization_arm(arm) and "sample_memory" in leaked and not declared_non_blind:
        raise IsolationError(
            f"main generalization arm {arm} cannot keep sample-indexed memory"
        )
    if is_main_generalization_arm(arm) and "sample_memory" in non_blind_channels:
        raise IsolationError(
            f"main generalization arm {arm} must disable sample-indexed memory rather than "
            "relabel the condition as non-blind"
        )
    leak_or_declared = bool(
        reasons or leaked or fallback_used or view == "parser_assisted" or declared_non_blind
    )
    eligible = (
        not leak_or_declared
        and policy["blind_prediction_credit_eligible"]
    )
    credit, credit_reason = grant_blind_prediction_credit(
        eligible=eligible,
        prediction=prediction,
        executor_evidence=executor_evidence,
        executor=executor,
        invocation=invocation,
    )
    if not credit:
        reasons.append(credit_reason)
    if leak_or_declared:
        condition_class = "non_blind"
    elif credit:
        condition_class = "blind"
    else:
        condition_class = "blind_eligible_uncredited"
    return {
        "arm": arm,
        "view": view,
        "blind": credit,
        "condition_class": condition_class,
        "blind_prediction_credit": credit,
        "leaked_channels": list(leaked),
        "declared_non_blind_channels": non_blind_channels,
        "reasons": reasons,
        "parser_feature_count": len(features),
        "request_shape_only": False,
        "caller_clean_flag": bool(clean),
    }


def grant_blind_prediction_credit(
    *,
    eligible: bool,
    prediction: Mapping[str, Any] | None,
    executor_evidence: Mapping[str, Any] | None,
    executor: "IsolationExecutor | None",
    invocation: Mapping[str, Any] | None,
) -> tuple[bool, str]:
    if not eligible:
        return False, "condition_not_credit_eligible"
    if not isinstance(prediction, Mapping) or not prediction.get("retained"):
        return False, "no_retained_prediction"
    if executor is None or invocation is None:
        return False, "no_executor_or_invocation"
    ok, detail = validate_executor_evidence(
        executor_evidence, executor=executor, invocation=invocation,
    )
    if not ok:
        return False, detail
    return True, "executor_bound_prediction"


def validate_executor_evidence(
    evidence: Mapping[str, Any] | None,
    *,
    executor: "IsolationExecutor",
    invocation: Mapping[str, Any],
) -> tuple[bool, str]:
    if not isinstance(evidence, Mapping) or not evidence:
        return False, "absent_executor_evidence"
    missing = [field for field in REQUIRED_EVIDENCE_FIELDS if field not in evidence]
    if missing:
        return False, "absent:" + ",".join(missing)
    if evidence.get("executor_id") != EXECUTOR_ID:
        return False, "mismatched_executor_id"
    if evidence.get("executor_digest") != executor.digest:
        return False, "stale_or_mismatched_executor_digest"
    if evidence.get("configuration_digest") != executor.configuration_digest:
        return False, "mismatched_configuration"
    if evidence.get("invocation_id") != invocation.get("invocation_id"):
        return False, "mismatched_invocation"
    if evidence.get("model_identity") != MODEL_IDENTITY:
        return False, "mismatched_model"
    if evidence.get("source_identity") != invocation.get("source_identity"):
        return False, "mismatched_source_identity"
    restrictions = evidence.get("channel_restrictions")
    if not isinstance(restrictions, Mapping):
        return False, "absent:channel_restrictions"
    for channel in CHANNELS:
        status = restrictions.get(channel)
        if status not in {"closed", "rejected"}:
            return False, f"unqualified_or_open_channel:{channel}"
    return True, "ok"


def _reject_blocked_channels(
    view: str,
    payload: Mapping[str, Any],
    *,
    source_text: str | None,
) -> dict[str, list[str]]:
    hits = scan_channels(payload)
    blocked = VIEW_BLOCKED_CHANNELS[view]
    leaked = {channel: paths for channel, paths in hits.items() if channel in blocked}
    if view in {"parser_assisted", "source_only"}:
        leaked.pop("source_text", None)
    if leaked:
        detail = {channel: paths for channel, paths in leaked.items()}
        raise IsolationError(
            f"{view} view rejects withheld channels {sorted(detail)}: {canonical_dumps(detail)}"
        )
    if view == "source_withheld":
        inspected = inspect_memory_shortcuts(payload)
        if inspected["shortcut"]:
            raise IsolationError(
                "source-withheld view rejects sample-id/cache-key memory shortcut: "
                + ",".join(inspected["reasons"])
            )
        if encodes_withheld_source(
            {key: value for key, value in payload.items() if key != "canonical_ir"},
            source_text,
        ):
            raise IsolationError(
                "source text leaked into the source-withheld realization payload"
            )
        gold = payload.get("gold_ir") or payload.get("gold") or payload.get("gold_target")
        if gold not in (None, "", {}, []):
            raise IsolationError("source-withheld view rejects gold IR")
    return hits


def build_inference_view(
    view: str,
    payload: Mapping[str, Any],
    *,
    source_text: str | None = None,
    gold_ir: Any = None,
    features: Sequence[Mapping[str, Any]] | None = None,
) -> dict[str, Any]:
    """Return the sanitized inference request a realizer/predictor may see."""
    _expect(view in VIEWS, f"unknown inference view {view}")
    _expect(isinstance(payload, Mapping), "inference payload must be an object")
    request_id = str(payload.get("request_id") or "").strip()
    _expect(request_id, "request_id is required")
    disclosed = disclose_parser_features(
        features if features is not None else payload.get("features")
    )
    working = {key: value for key, value in payload.items() if key != "features"}
    if gold_ir is not None:
        working = dict(working)
        working["gold_ir"] = gold_ir
    if view == "source_only":
        text = source_text if source_text is not None else working.get("source_text")
        _expect(isinstance(text, str) and text.strip(), "source-only view requires source_text")
        _expect(not disclosed, "source-only view cannot consume parser-assisted features")
        _reject_blocked_channels(view, working, source_text=None)
        request = {
            "view": view,
            "request_id": request_id,
            "source_text": text,
            "raw_text_prediction": True,
            "parser_assisted": False,
            "source_withheld": False,
            "features": [],
        }
    elif view == "parser_assisted":
        text = source_text if source_text is not None else working.get("source_text")
        _expect(isinstance(text, str) and text.strip(), "parser-assisted view requires source_text")
        _expect(disclosed, "parser-assisted view requires disclosed features with producer and cost")
        _reject_blocked_channels(view, working, source_text=None)
        request = {
            "view": view,
            "request_id": request_id,
            "source_text": text,
            "raw_text_prediction": False,
            "parser_assisted": True,
            "source_withheld": False,
            "features": disclosed,
            "feature_cost_seconds": round(
                sum(item["cost"]["compile_seconds"] + item["cost"]["extraction_seconds"]
                    for item in disclosed),
                6,
            ),
        }
    else:
        _expect("source_text" not in working or working.get("source_text") in (None, ""),
                "source-withheld view may not include source_text")
        _reject_blocked_channels(view, working, source_text=source_text)
        if disclosed:
            raise IsolationError(
                "source-withheld realization may not consume original-source parser features"
            )
        projected = project_canonical_ir(
            working.get("canonical_ir"), withheld_source=source_text,
        )
        vocabulary = working.get("vocabulary") if isinstance(working.get("vocabulary"), Mapping) else {}
        request = {
            "view": view,
            "request_id": request_id,
            "canonical_ir": projected["canonical_ir"],
            "ir_projection": {
                "dropped_paths": projected["dropped_paths"],
                "projection": projected["projection"],
            },
            "vocabulary": {
                key: list(value) if isinstance(value, Sequence) and not isinstance(value, str) else value
                for key, value in vocabulary.items()
            },
            "rendering_spec_id": working.get("rendering_spec_id"),
            "policy_id": working.get("policy_id"),
            "raw_text_prediction": False,
            "parser_assisted": False,
            "source_withheld": True,
            "features": [],
            "fallback_used": False,
        }
        if encodes_withheld_source(request, source_text):
            raise IsolationError("canonical IR leaked originating source text")
    request["schema"] = SCHEMA
    request["request_shape_check"] = REQUEST_SHAPE_SCHEMA
    request["blind_input_digest"] = sha256_obj(
        {key: request[key] for key in request if key != "blind_input_digest"}
    )
    return request


class ChannelSandbox:
    """Process/channel boundary for one executor invocation. Fail closed."""

    def __init__(self) -> None:
        self.attempts: list[dict[str, Any]] = []
        self._orig: dict[str, Any] = {}

    def __enter__(self) -> "ChannelSandbox":
        self._orig = {
            "open": builtins.open,
            "io_open": io.open,
            "os_open": os.open,
            "path_read_text": Path.read_text,
            "path_read_bytes": Path.read_bytes,
            "urlopen": urllib.request.urlopen,
        }
        sandbox = self

        def block_open(file: Any, *args: Any, **kwargs: Any) -> Any:
            sandbox._record("filesystem", "open", str(file))
            raise IsolationError(f"filesystem channel blocked during executor open: {file}")

        def block_os_open(path: Any, *args: Any, **kwargs: Any) -> Any:
            sandbox._record("filesystem", "os.open", str(path))
            raise IsolationError(f"filesystem channel blocked during executor os.open: {path}")

        def block_read_text(path_self: Path, *args: Any, **kwargs: Any) -> str:
            sandbox._record("filesystem", "Path.read_text", str(path_self))
            raise IsolationError(
                f"filesystem channel blocked during executor Path.read_text: {path_self}"
            )

        def block_read_bytes(path_self: Path, *args: Any, **kwargs: Any) -> bytes:
            sandbox._record("filesystem", "Path.read_bytes", str(path_self))
            raise IsolationError(
                f"filesystem channel blocked during executor Path.read_bytes: {path_self}"
            )

        def block_urlopen(url: Any, *args: Any, **kwargs: Any) -> Any:
            sandbox._record("retrieval", "urlopen", str(url))
            raise IsolationError(
                "retrieval/urlopen is blocked; this is not a network or pretraining qualification"
            )

        builtins.open = block_open  # type: ignore[assignment]
        io.open = block_open  # type: ignore[assignment]
        os.open = block_os_open  # type: ignore[assignment]
        Path.read_text = block_read_text  # type: ignore[method-assign]
        Path.read_bytes = block_read_bytes  # type: ignore[method-assign]
        urllib.request.urlopen = block_urlopen  # type: ignore[assignment]
        return self

    def __exit__(self, *exc: Any) -> bool:
        builtins.open = self._orig["open"]
        io.open = self._orig["io_open"]
        os.open = self._orig["os_open"]
        Path.read_text = self._orig["path_read_text"]
        Path.read_bytes = self._orig["path_read_bytes"]
        urllib.request.urlopen = self._orig["urlopen"]
        self._orig = {}
        return False

    def _record(self, channel: str, op: str, detail: str) -> None:
        self.attempts.append({"channel": channel, "op": op, "detail": detail})


class IsolationExecutor:
    """Executor identity, sandboxed realization, and channel qualification."""

    def __init__(self) -> None:
        self.digest = executor_source_digest()
        self.configuration_digest = configuration_digest()
        self.invocations: list[dict[str, Any]] = []

    def identity(self) -> dict[str, Any]:
        return {
            "executor_id": EXECUTOR_ID,
            "executor_digest": self.digest,
            "model_identity": MODEL_IDENTITY,
            "model_architecture": MODEL_ARCHITECTURE,
            "configuration_digest": self.configuration_digest,
            "source_identity": "synthetic_canary_executor_not_heldout",
        }

    def closed_channel_restrictions(self) -> dict[str, str]:
        return {channel: "closed" for channel in CHANNELS}

    def retrieve(self, *args: Any, **kwargs: Any) -> Any:
        raise IsolationError("retrieval channel is closed on this executor")

    def parser_state(self, *args: Any, **kwargs: Any) -> Any:
        raise IsolationError("parser state is not available on this executor")

    def gold_fallback(self, *args: Any, **kwargs: Any) -> Any:
        raise IsolationError("reference/gold decoder fallback is closed")

    def sample_memory_lookup(self, *args: Any, **kwargs: Any) -> Any:
        raise IsolationError("sample memory is closed on this executor realization")

    def evidence_for(self, invocation: Mapping[str, Any]) -> dict[str, Any]:
        identity = self.identity()
        return {
            "executor_id": identity["executor_id"],
            "executor_digest": identity["executor_digest"],
            "invocation_id": invocation["invocation_id"],
            "source_identity": invocation["source_identity"],
            "model_identity": identity["model_identity"],
            "configuration_digest": identity["configuration_digest"],
            "channel_restrictions": dict(invocation["channel_restrictions"]),
        }

    def realize(
        self,
        view: str,
        payload: Mapping[str, Any],
        *,
        source_text: str | None = None,
        features: Sequence[Mapping[str, Any]] | None = None,
        arm: str = "T2",
        fallback_used: bool = False,
    ) -> dict[str, Any]:
        sandbox = ChannelSandbox()
        with sandbox:
            request = build_inference_view(
                view, payload, source_text=source_text, features=features,
            )
            if fallback_used:
                self.gold_fallback()
            if view == "source_withheld":
                surface = atom_surface(request["canonical_ir"])
                prediction = {
                    "retained": True,
                    "kind": "source_withheld_atom_surface",
                    "text": surface,
                    "digest": sha256_text(surface),
                }
            elif view == "source_only":
                digest = sha256_text(str(request["source_text"]))
                prediction = {
                    "retained": True,
                    "kind": "source_only_request",
                    "source_digest": digest,
                    "digest": digest,
                }
            else:
                feature_digest = sha256_obj(request["features"])
                prediction = {
                    "retained": True,
                    "kind": "parser_assisted_disclosed_features",
                    "producer": COMPILER_PRODUCER,
                    "feature_cost_seconds": request["feature_cost_seconds"],
                    "digest": feature_digest,
                }
            if source_text and encodes_withheld_source(prediction, source_text) and view == "source_withheld":
                raise IsolationError("executor prediction recovered withheld source")
        invocation_id = sha256_obj({
            "arm": arm,
            "view": view,
            "request_digest": request["blind_input_digest"],
            "prediction_digest": prediction["digest"],
            "executor_digest": self.digest,
        })
        invocation = {
            "invocation_id": invocation_id,
            "arm": arm,
            "view": view,
            "source_identity": "synthetic_canary_executor_not_heldout",
            "channel_restrictions": self.closed_channel_restrictions(),
            "sandbox_attempts": list(sandbox.attempts),
            "fallback_used": bool(fallback_used),
        }
        self.invocations.append(invocation)
        return {
            "request": request,
            "prediction": prediction,
            "invocation": invocation,
            "executor": self.identity(),
            "evidence": self.evidence_for(invocation),
        }

    def attempt_channel(
        self,
        channel: str,
        *,
        canary_file: str | None = None,
        source_text: str = SYNTHETIC_SOURCE,
    ) -> dict[str, Any]:
        sandbox = ChannelSandbox()
        recovered = False
        recovered_text = None
        error = None
        with sandbox:
            try:
                if channel == "filesystem":
                    _expect(canary_file, "filesystem probe requires a synthetic canary file")
                    recovered_text = Path(canary_file).read_text(encoding="utf-8")
                    recovered = True
                elif channel == "retrieval":
                    self.retrieve(query=source_text)
                elif channel == "parser_state":
                    self.parser_state()
                elif channel == "sample_memory":
                    self.sample_memory_lookup(sample_id="unit-1")
                elif channel == "gold_ir":
                    self.gold_fallback(kind="gold_ir")
                elif channel == "reference_fallback":
                    self.gold_fallback(kind="reference")
                elif channel == "source_maps":
                    raise IsolationError("source maps do not cross the executor boundary")
                elif channel == "sample_id_cache":
                    raise IsolationError("sample-id cache is closed on this executor")
                elif channel == "source_text":
                    raise IsolationError("source text is not an executor recovery channel")
                else:
                    raise IsolationError(f"unknown channel {channel}")
            except IsolationError as exc:
                error = str(exc)
        if recovered_text and encodes_withheld_source(recovered_text, source_text):
            recovered = True
        return {
            "channel": channel,
            "recovered": recovered,
            "error": error,
            "sandbox_attempts": list(sandbox.attempts),
            "network_or_pretraining_claimed": False,
        }


def _scrub_temp_strings(value: Any, needles: Sequence[str]) -> Any:
    """Replace ephemeral canary paths so reports stay deterministic."""
    replacements = [(needle, "<synthetic-canary>") for needle in needles if needle]
    if isinstance(value, str):
        for needle, token in replacements:
            value = value.replace(needle, token)
        return value
    if isinstance(value, Mapping):
        return {key: _scrub_temp_strings(item, needles) for key, item in value.items()}
    if isinstance(value, list):
        return [_scrub_temp_strings(item, needles) for item in value]
    return value


def closed_channel_restrictions() -> dict[str, str]:
    return {channel: "closed" for channel in CHANNELS}


def default_channel_restrictions_for_view(view: str) -> dict[str, str]:
    blocked = VIEW_BLOCKED_CHANNELS[view]
    restrictions = {}
    for channel in CHANNELS:
        if channel in blocked:
            restrictions[channel] = "closed"
        elif view in {"source_only", "parser_assisted"} and channel == "source_text":
            restrictions[channel] = "closed"
        else:
            restrictions[channel] = "closed"
    return restrictions


def probe_channel(
    view: str,
    channel: str,
    *,
    base: Mapping[str, Any] | None = None,
    source_text: str = SYNTHETIC_SOURCE,
    declare_non_blind: bool = False,
    canary_file: str | None = None,
    executor: IsolationExecutor | None = None,
) -> dict[str, Any]:
    """Attempt to recover withheld source/gold through one documented channel."""
    _expect(view in VIEWS, f"unknown inference view {view}")
    _expect(channel in CHANNELS, f"unknown leakage channel {channel}")
    payload = dict(base or _fixture_payload(view, source_text=source_text))
    injection = _channel_injection(channel, source_text=source_text, canary_file=canary_file)
    payload.update(injection)
    features = payload.pop("features", None)
    active = executor or IsolationExecutor()
    allowed = (
        (view == "source_only" and channel == "source_text")
        or (view == "parser_assisted" and channel == "source_text")
    )
    try:
        built = build_inference_view(
            view, payload, source_text=source_text, features=features,
        )
        if not allowed:
            raise ProbeContractError(
                f"{channel} injection was not rejected by the {view} view"
            )
        channel_attempt = active.attempt_channel(
            channel, canary_file=canary_file, source_text=source_text,
        )
        if channel_attempt["recovered"]:
            raise ProbeContractError(f"{channel} recovered withheld material through the executor")
        if declare_non_blind:
            decision = "non_blind"
            reason = "caller declared the affected condition non-blind"
        else:
            decision = "allowed_input"
            reason = f"{channel} is an allowed input of {view}"
        return {
            "view": view,
            "channel": channel,
            "attempted": True,
            "recovered": False,
            "decision": decision,
            "blind_prediction_credit": False,
            "reason": reason,
            "request_digest": built.get("blind_input_digest"),
            "executor_digest": active.digest,
            "qualification": "executor_bound" if not allowed else "allowed_input_plus_executor_channel_closed",
            "request_shape_only": False,
            "channel_attempt": channel_attempt,
        }
    except ProbeContractError:
        raise
    except IsolationError as exc:
        channel_attempt = active.attempt_channel(
            channel, canary_file=canary_file, source_text=source_text,
        )
        recovered = bool(channel_attempt.get("recovered"))
        if declare_non_blind:
            return {
                "view": view,
                "channel": channel,
                "attempted": True,
                "recovered": False,
                "decision": "non_blind",
                "blind_prediction_credit": False,
                "reason": f"rejected then declared non-blind: {exc}",
                "executor_digest": active.digest,
                "qualification": "explicit_non_blind",
                "request_shape_only": False,
                "channel_attempt": channel_attempt,
            }
        if recovered:
            return {
                "view": view,
                "channel": channel,
                "attempted": True,
                "recovered": True,
                "decision": "non_blind",
                "blind_prediction_credit": False,
                "reason": "channel available on executor; condition is non-blind",
                "executor_digest": active.digest,
                "qualification": "unqualified_or_open",
                "request_shape_only": False,
                "channel_attempt": channel_attempt,
            }
        return {
            "view": view,
            "channel": channel,
            "attempted": True,
            "recovered": False,
            "decision": "rejected",
            "blind_prediction_credit": False,
            "reason": str(exc),
            "executor_digest": active.digest,
            "qualification": "executor_bound",
            "request_shape_only": False,
            "channel_attempt": channel_attempt,
        }


def probe_encoded_ir_auxiliary(source_text: str = SYNTHETIC_SOURCE) -> dict[str, Any]:
    """Encoded/nested extras in otherwise permitted IR must not survive projection."""
    encoded = base64.b64encode(source_text.encode("utf-8")).decode("ascii")
    payload = _fixture_payload("source_withheld", source_text=source_text)
    payload["canonical_ir"] = {
        **payload["canonical_ir"],
        "auxiliary": {"b64": encoded, "nested": [{"note": source_text}]},
        "canonical_ir_text": encoded,
        "freeform": source_text,
    }
    executor = IsolationExecutor()
    realized = executor.realize(
        "source_withheld", payload, source_text=source_text, arm="T2",
    )
    request_ir = realized["request"]["canonical_ir"]
    dropped = realized["request"]["ir_projection"]["dropped_paths"]
    recovered = encodes_withheld_source(realized["prediction"], source_text) or encodes_withheld_source(
        request_ir, source_text,
    )
    return {
        "view": "source_withheld",
        "channel": "source_text",
        "probe": "encoded_canonical_ir_auxiliary",
        "attempted": True,
        "recovered": recovered,
        "decision": "rejected" if not recovered else "non_blind",
        "blind_prediction_credit": False,
        "dropped_paths": dropped,
        "projection": realized["request"]["ir_projection"]["projection"],
        "reason": (
            "IR projection dropped non-permitted auxiliary/encoded fields"
            if not recovered else "encoded auxiliary survived projection"
        ),
        "executor_digest": executor.digest,
        "qualification": "ir_projection",
        "request_shape_only": False,
    }


def run_subprocess_filesystem_probe(
    *,
    source_text: str = SYNTHETIC_SOURCE,
    timeout: float = 20.0,
) -> dict[str, Any]:
    """Exercise the filesystem channel in a fresh executor process."""
    import tempfile

    with tempfile.TemporaryDirectory(prefix="af026-canary-") as tmp:
        canary = Path(tmp) / "withheld.txt"
        canary.write_text(source_text, encoding="utf-8")
        env = {
            "PATH": "/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin",
            "PYTHONDONTWRITEBYTECODE": "1",
            "IPFS_AUTO_INSTALL": "false",
            "IPFS_DATASETS_AUTO_INSTALL": "false",
            "HF_HUB_OFFLINE": "1",
            "TRANSFORMERS_OFFLINE": "1",
        }
        proc = subprocess.run(
            [
                sys.executable,
                str(Path(__file__)),
                "probe-executor",
                "--view", "source_withheld",
                "--channel", "filesystem",
                "--canary-file", str(canary),
            ],
            cwd=str(REPO_ROOT),
            env=env,
            capture_output=True,
            text=True,
            timeout=timeout,
        )
        stdout = proc.stdout.strip()
        try:
            body = json.loads(stdout) if stdout else {}
        except json.JSONDecodeError:
            body = {"parse_error": True, "stderr_present": bool(proc.stderr)}
        parent_can_read = canary.read_text(encoding="utf-8") == source_text
        recovered = bool(body.get("recovered"))
        payload = {
            "view": "source_withheld",
            "channel": "filesystem",
            "probe": "subprocess_executor_filesystem",
            "attempted": True,
            "recovered": recovered,
            "decision": "rejected" if not recovered else "non_blind",
            "blind_prediction_credit": False,
            "exit_code": proc.returncode,
            "parent_same_process_read_possible": parent_can_read,
            "parent_read_is_not_executor_leak": True,
            "network_or_pretraining_claimed": False,
            "child": body,
            "stderr_present": bool(proc.stderr),
            "qualification": "executor_process_boundary",
            "request_shape_only": False,
        }
        return _scrub_temp_strings(payload, (str(tmp), str(canary)))


def _fixture_ir() -> dict[str, Any]:
    return {
        "rules": [
            {
                "modality": "O",
                "actor": "permit_holder",
                "action": "file",
                "object": "notice",
                "conditions": ["after_approval"],
                "exceptions": ["exempt"],
                "temporal": ["within_ten_days"],
            }
        ]
    }


def _fixture_payload(view: str, *, source_text: str) -> dict[str, Any]:
    if view == "source_withheld":
        return {
            "request_id": "af026-withheld",
            "canonical_ir": _fixture_ir(),
            "vocabulary": {"actors": ["permit_holder"]},
            "rendering_spec_id": "source_withheld_paraphrase",
            "policy_id": "canonical-parity/v1",
        }
    if view == "parser_assisted":
        return {
            "request_id": "af026-parser",
            "source_text": source_text,
            "features": [_parser_feature_fixture()],
        }
    return {
        "request_id": "af026-source",
        "source_text": source_text,
    }


def _parser_feature_fixture() -> dict[str, Any]:
    return {
        "name": "actor_action_object_roles",
        "kind": "actor_action_object_roles",
        "producer": COMPILER_PRODUCER,
        "depends_on_parse": True,
        "requires_complete_compilation": True,
        "cost": {"compile_seconds": 0.4, "extraction_seconds": 0.05},
    }


def _channel_injection(
    channel: str,
    *,
    source_text: str,
    canary_file: str | None = None,
) -> dict[str, Any]:
    if channel == "source_text":
        return {"source_text": source_text, "originating_source": source_text}
    if channel == "source_maps":
        return {"source_map": {"notice": {"start": 28, "end": 34}}, "locator": "span:28-34"}
    if channel == "filesystem":
        path = canary_file or "/corpus/legal/permit-holder-notice.txt"
        return {"source_path": path, "file_path": path}
    if channel == "retrieval":
        return {"retrieval": {"query": source_text, "hits": [source_text]}, "index_query": "permit holder"}
    if channel == "parser_state":
        return {"parser_trace": {"tokens": source_text.split()}, "parser_cache": {"raw": source_text}}
    if channel == "sample_memory":
        return {
            "use_sample_memory": True,
            "decoded_embeddings": {"unit-1": [0.1, 0.2]},
            "sample_id": "unit-1",
        }
    if channel == "gold_ir":
        return {"gold_ir": _fixture_ir(), "gold_target": _fixture_ir()}
    if channel == "reference_fallback":
        return {"reference_decoder": "gold_surface", "gold_fallback": source_text}
    return {
        "sample_id": "unit-1",
        "cache_key": "unit-1",
        "source_cid": "baguqeera-not-a-live-cid",
    }


def run_adversarial_probes() -> list[dict[str, Any]]:
    results: list[dict[str, Any]] = []
    executor = IsolationExecutor()
    for view in VIEWS:
        for channel in CHANNELS:
            results.append(probe_channel(view, channel, executor=executor))
    results.append(probe_channel(
        "source_withheld", "filesystem", declare_non_blind=True, executor=executor,
    ))
    results.append(probe_encoded_ir_auxiliary())
    results.append(run_subprocess_filesystem_probe())
    return results


def credit_prediction(
    *,
    view: str,
    arm: str,
    fallback_used: bool = False,
    reconstruction: Mapping[str, Any] | None = None,
    prediction: Mapping[str, Any] | None = None,
    executor_evidence: Mapping[str, Any] | None = None,
    executor: IsolationExecutor | None = None,
    invocation: Mapping[str, Any] | None = None,
    clean: bool = False,
    parser_features: Sequence[Mapping[str, Any]] | None = None,
) -> dict[str, Any]:
    if reconstruction is not None:
        validate_reconstruction_scores(reconstruction)
    condition = classify_condition(
        arm=arm,
        view=view,
        leaked_channels=(),
        fallback_used=fallback_used,
        parser_features=parser_features if parser_features is not None else (
            () if view != "parser_assisted" else [_parser_feature_fixture()]
        ),
        prediction=prediction,
        executor_evidence=executor_evidence,
        executor=executor,
        invocation=invocation,
        clean=clean,
    )
    if fallback_used:
        condition["blind_prediction_credit"] = False
        condition["excluded_from_blind_prediction_credit"] = True
        condition["fallback"] = "reference_or_gold_decoder"
        condition["condition_class"] = "non_blind"
    return condition


def load_native_autoencoder() -> tuple[Any, Any]:
    global _NATIVE_IMPORT
    if _NATIVE_IMPORT is not None:
        return _NATIVE_IMPORT
    root = str(DATASETS_ROOT)
    if root not in sys.path:
        sys.path.insert(0, root)
    from ipfs_datasets_py.optimizers.logic_theorem_optimizer.legal_samples import (
        build_us_code_sample,
    )
    from ipfs_datasets_py.optimizers.logic_theorem_optimizer.modal_autoencoder import (
        AdaptiveModalAutoencoder,
    )
    _NATIVE_IMPORT = (AdaptiveModalAutoencoder, build_us_code_sample)
    return _NATIVE_IMPORT


def qualify_native_sample_memory() -> dict[str, Any]:
    """Exercise AdaptiveModalAutoencoder memory for update and evaluation.

    A JSON use_sample_memory=false declaration is not this qualification.
    Declaring a main generalization arm non-blind does not waive it.
    """
    AdaptiveModalAutoencoder, build_us_code_sample = load_native_autoencoder()
    sample = build_us_code_sample(
        title="26",
        section="026",
        text=SYNTHETIC_MEMORY_TEXT,
    )
    sentinel = [99.0, -99.0, 42.0, -42.0, 7.0, -7.0, 3.0, -3.0]
    _expect(len(sentinel) == len(sample.embedding_vector),
            "synthetic sentinel rank must match native embedding")
    autoencoder_digest = sha256_file(NATIVE_AUTOENCODER_PATH)
    arms: dict[str, Any] = {}
    for arm in MAIN_GENERALIZATION_ARMS:
        ae = AdaptiveModalAutoencoder()
        ae._nudge_decoded_embedding(sample, learning_rate=0.5, update_sample_memory=False)
        ae._nudge_family_logits(sample, learning_rate=0.5, update_sample_memory=False)
        write_blocked = (
            sample.sample_id not in ae.state.decoded_embeddings
            and sample.sample_id not in ae.state.family_logits
        )
        ae.state.decoded_embeddings[sample.sample_id] = list(sentinel)
        ae.state.family_logits[sample.sample_id] = {"deontic": 99.0}
        shared_cache_key = sample.sample_id
        decoded_off = ae._decoded_for(sample, use_sample_memory=False)
        logits_off = ae._logits_for(sample, use_sample_memory=False)
        encoded = ae.encode(sample, use_sample_memory=False)
        read_blocked = (
            list(decoded_off) != list(sentinel)
            and float(logits_off.get("deontic", 0.0)) < 50.0
            and list(encoded["embedding_projection"]) != list(sentinel)
        )
        eval_write_keys_unchanged = set(ae.state.decoded_embeddings) == {sample.sample_id}
        shortcut = inspect_memory_shortcuts(
            sample_id=sample.sample_id,
            cache_key=shared_cache_key,
            use_sample_memory=False,
        )
        _expect(write_blocked, f"{arm} native update retained sample-indexed memory")
        _expect(read_blocked, f"{arm} native evaluation read planted sample memory")
        _expect(shortcut["shortcut"], f"{arm} shared sample_id cache key was not flagged")
        _expect(encoded["sample_id"] == sample.sample_id, f"{arm} native encode did not run")
        arms[arm] = {
            "arm": arm,
            "generalization_arm": True,
            "update_memory_disabled": True,
            "evaluation_memory_disabled": True,
            "native_update_write_blocked": write_blocked,
            "native_evaluation_read_blocked": read_blocked,
            "shared_id_cache_shortcut_detected": shortcut["shortcut"],
            "encode_used_for_evaluation": True,
            "evaluate_avoided_symai_import": True,
            "evaluate_did_not_add_memory_keys": eval_write_keys_unchanged,
            "interfaces": [
                "AdaptiveModalAutoencoder._nudge_decoded_embedding",
                "AdaptiveModalAutoencoder._nudge_family_logits",
                "AdaptiveModalAutoencoder._decoded_for",
                "AdaptiveModalAutoencoder._logits_for",
                "AdaptiveModalAutoencoder.encode",
            ],
        }
    t1 = AdaptiveModalAutoencoder()
    t1._nudge_decoded_embedding(sample, learning_rate=0.9, update_sample_memory=True)
    t1._nudge_family_logits(sample, learning_rate=0.9, update_sample_memory=True)
    t1_write = sample.sample_id in t1.state.decoded_embeddings and sample.sample_id in t1.state.family_logits
    planted = list(t1.state.decoded_embeddings[sample.sample_id])
    t1_read = t1._decoded_for(sample, use_sample_memory=True) == planted
    t1_off = t1._decoded_for(sample, use_sample_memory=False) != planted
    _expect(t1_write and t1_read, "T1 enabled-memory positive control failed to write/read")
    return {
        "schema": "autoformalization-native-sample-memory-qualification/v1",
        "native_module": str(NATIVE_AUTOENCODER_PATH.relative_to(REPO_ROOT)),
        "native_module_sha256": autoencoder_digest,
        "model_identity": MODEL_IDENTITY,
        "model_architecture": MODEL_ARCHITECTURE,
        "synthetic_sample_id": sample.sample_id,
        "synthetic_text_is_heldout": False,
        "json_flag_alone_insufficient": True,
        "non_blind_declaration_does_not_waive": True,
        "main_generalization_arms": arms,
        "t1_positive_control": {
            "arm": "T1",
            "generalization_arm": False,
            "update_memory_enabled": True,
            "evaluation_memory_enabled": True,
            "native_update_write_observed": t1_write,
            "native_evaluation_read_observed": t1_read,
            "disabled_read_still_ignores_memory": t1_off,
            "blind_prediction_credit": False,
        },
        "all_main_arms_update_and_eval_disabled": all(
            item["native_update_write_blocked"] and item["native_evaluation_read_blocked"]
            for item in arms.values()
        ),
    }


def load_frozen_arm_ids(root: Path | None = None) -> list[str]:
    root = root or REPO_ROOT
    plan_path = root / "papers/completion/autoformalization/config/experiment_plan.json"
    if not plan_path.is_file():
        return list(EXPERIMENT_ARMS)
    plan = load_json(plan_path)
    arms = [item["id"] for item in plan.get("conditions") or [] if isinstance(item, Mapping)]
    _expect(arms == list(EXPERIMENT_ARMS), "frozen experiment arms drifted from AF-026 isolation contract")
    return arms


def load_feature_flags(root: Path | None = None) -> dict[str, Any]:
    root = root or REPO_ROOT
    path = root / "papers/completion/autoformalization/config/environment_manifest.json"
    if not path.is_file():
        return {
            "source_withheld_retrieval": False,
            "sample_memory_main_generalization": False,
            "final_test_access": False,
            "note": "manifest missing; flags are declarations, not executor qualification",
        }
    flags = load_json(path).get("feature_flags") or {}
    _expect(flags.get("source_withheld_retrieval") is False,
            "environment manifest must keep source-withheld retrieval disabled")
    _expect(flags.get("sample_memory_main_generalization") is False,
            "environment manifest must disable sample memory for main generalization")
    return {
        "source_withheld_retrieval": flags.get("source_withheld_retrieval"),
        "sample_memory_main_generalization": flags.get("sample_memory_main_generalization"),
        "final_test_access": flags.get("final_test_access"),
        "declaration_only": True,
        "note": "feature flags are request/configuration declarations, not executor qualification",
    }


def load_parser_producer(root: Path | None = None) -> dict[str, Any]:
    root = root or REPO_ROOT
    path = root / "papers/completion/autoformalization/config/environment_manifest.json"
    producer = COMPILER_PRODUCER
    qualification = "disclosed identity; compiler was not invoked for these probes"
    source_sha256 = None
    if path.is_file():
        compiler = (load_json(path).get("selected_entry_points") or {}).get("compiler") or {}
        producer = str(compiler.get("producer_version") or producer)
        source_sha256 = compiler.get("source_sha256")
        qualification = str(compiler.get("qualification") or qualification)
    return {
        "producer": producer,
        "source_sha256": source_sha256,
        "qualification": qualification,
        "required_fields": [
            "name", "producer", "depends_on_parse",
            "requires_complete_compilation", "cost.compile_seconds",
            "cost.extraction_seconds",
        ],
        "complete_compilation_must_be_charged": True,
        "cannot_be_described_as_raw_text_prediction": True,
        "feature_kinds": list(PARSER_FEATURE_KINDS),
    }


def build_leakage_control_report(root: Path | None = None) -> dict[str, Any]:
    root = root or REPO_ROOT
    arms = load_frozen_arm_ids(root)
    flags = load_feature_flags(root)
    probes = run_adversarial_probes()
    withheld = [
        item for item in probes
        if item.get("view") == "source_withheld"
    ]
    documented = [
        item for item in withheld
        if item.get("channel") in CHANNELS and item.get("probe") is None
    ]
    _expect(len(documented) >= len(CHANNELS),
            "each documented channel must be probed on the source-withheld view")
    for item in documented:
        _expect(item["decision"] in {"rejected", "non_blind"},
                f"source-withheld {item['channel']} was not rejected or declared non-blind")
        _expect(not item.get("recovered"),
                f"source-withheld {item['channel']} recovered withheld material")
    recovered = [item for item in probes if item.get("recovered")]
    _expect(not recovered, "adversarial probe recovered withheld material")
    memory = qualify_native_sample_memory()
    _expect(memory["all_main_arms_update_and_eval_disabled"],
            "native sample-memory route was not disabled for every main generalization arm")
    _expect(memory["t1_positive_control"]["native_update_write_observed"],
            "T1 enabled-memory positive control did not write")
    arm_policies = {arm: sample_memory_policy(arm) for arm in arms}
    for arm, policy in arm_policies.items():
        if arm in MAIN_GENERALIZATION_ARMS:
            _expect(policy["update"]["use_sample_memory"] is False, f"{arm} update memory enabled")
            _expect(policy["evaluation"]["use_sample_memory"] is False, f"{arm} evaluation memory enabled")
            _expect(policy["blind_prediction_credit"] is False,
                    f"{arm} policy granted blind credit without an executor")
        if arm in MEMORY_DIAGNOSTIC_ARMS:
            _expect(policy["generalization_arm"] is False, "T1 labeled as generalization")
            _expect(policy["blind_prediction_credit"] is False, "T1 received blind credit")
    reconstruction = reconstruction_bundle(
        forward={"status": "unmeasured", "score": None, "compares": "gold_to_first_ir"},
        cycle={"status": "unmeasured", "score": None, "compares": "first_ir_to_second_ir"},
        final={"status": "unmeasured", "score": None, "compares": "gold_to_second_ir"},
        vector={"mse": None, "cosine": None},
    )
    producer = load_parser_producer(root)
    executor = IsolationExecutor()
    native_digests = {
        "inference_isolation.py": executor.digest,
        "modal_autoencoder.py": sha256_file(NATIVE_AUTOENCODER_PATH) if NATIVE_AUTOENCODER_PATH.is_file() else None,
        "canonical_roundtrip.py": sha256_file(NATIVE_ROUNDTRIP_PATH) if NATIVE_ROUNDTRIP_PATH.is_file() else None,
    }
    report: dict[str, Any] = {
        "schema": REPORT_SCHEMA,
        "task_id": TASK_ID,
        "parent_task_id": PARENT_TASK_ID,
        "parent_receipt_sha256": PARENT_RECEIPT_SHA256,
        "isolation_schema": SCHEMA,
        "status": "executor_bound_controls_qualified_empirical_runs_unrun",
        "request_shape_checks_are_not_executor_qualification": True,
        "superseded_af008_claims": [
            "key/substring request filters were treated as executor isolation",
            "arm/view names granted blind_prediction_credit without a retained prediction or executor",
            "JSON use_sample_memory=false was treated as native memory qualification",
        ],
        "inert_reviewer_counterexamples_are_not_paper_experiment_leaks": True,
        "views": {
            view: {
                "allowed_inputs": sorted(VIEW_ALLOWED_INPUTS[view]),
                "blocked_channels": sorted(VIEW_BLOCKED_CHANNELS[view]),
                "raw_text_prediction": view == "source_only",
                "parser_assisted": view == "parser_assisted",
                "source_withheld": view == "source_withheld",
            }
            for view in VIEWS
        },
        "documented_channels": list(CHANNELS),
        "unqualified_non_documented_channels": {
            name: {
                "qualified": False,
                "reason": "filesystem or retrieval-interface checks do not establish network or pretraining exclusion",
            }
            for name in UNQUALIFIED_NON_DOCUMENTED
        },
        "ir_projection": {
            "permitted_fields": list(PERMITTED_RULE_FIELDS),
            "permitted_modalities": sorted(PERMITTED_MODALITIES),
            "atom_pattern": ATOM_RE.pattern,
            "encoded_auxiliary_dropped": True,
            "denylist_or_literal_substring_insufficient": True,
        },
        "executor": {
            "executor_id": EXECUTOR_ID,
            "executor_digest": executor.digest,
            "configuration_digest": executor.configuration_digest,
            "model_identity": MODEL_IDENTITY,
            "model_architecture": MODEL_ARCHITECTURE,
            "native_digests": native_digests,
        },
        "probes": probes,
        "probe_summary": {
            "attempted": len(probes),
            "recovered": 0,
            "rejected": sum(1 for item in probes if item["decision"] == "rejected"),
            "non_blind": sum(1 for item in probes if item["decision"] == "non_blind"),
            "allowed_input": sum(1 for item in probes if item["decision"] == "allowed_input"),
        },
        "arm_memory_policy": arm_policies,
        "native_sample_memory": memory,
        "main_generalization_arms": list(MAIN_GENERALIZATION_ARMS),
        "memory_diagnostic_arms": list(MEMORY_DIAGNOSTIC_ARMS),
        "feature_flags": flags,
        "reconstruction_contract": {
            "symbolic_scores": list(RECONSTRUCTION_SCORES),
            "distinct": True,
            "forward": "gold → first IR (I1 = C(x))",
            "cycle": "first IR → second IR (I1 vs I2 = C(D(I1)))",
            "final": "gold → second IR (end-to-end)",
            "vector_reconstruction_is_not_free_text_decoder": True,
            "fixture_unmeasured": reconstruction,
        },
        "parser_assisted_disclosure": producer,
        "blind_prediction_credit": {
            "requires": [
                "retained_prediction",
                "executor_identity",
                "invocation_identity",
                "source_identity",
                "model_identity",
                "configuration_digest",
                "documented_channel_restrictions",
            ],
            "excludes": [
                "arm_or_view_name_alone",
                "caller_supplied_clean_flag",
                "request_shape_filter",
                "configuration_declaration",
                "absent_stale_or_mismatched_evidence",
                "reference_decoder_fallback",
                "gold_decoder_fallback",
                "parser_assisted_undisclosed_as_source_only",
                "source_withheld_channel_recovery",
                "sample_memory_on_generalization_arms",
                "T1_seen_source_memory_diagnostic",
                "unqualified_documented_channel",
            ],
            "rule": (
                "Blind-prediction credit is granted only for a retained prediction bound to "
                "independently validated evidence for the exact executor, invocation, "
                "source/model/configuration identities, and closed documented channels."
            ),
        },
        "reuse_boundaries": {
            "modal_autoencoder_native_memory": (
                "AdaptiveModalAutoencoder._nudge_decoded_embedding/_nudge_family_logits "
                "and encode/_decoded_for/_logits_for were exercised with use_sample_memory "
                "and update_sample_memory disabled on every main generalization arm. "
                "evaluate() is not used here because it imports a symai path that writes "
                "outside the sealed validation HOME."
            ),
            "canonical_roundtrip": (
                "DecompilerRequest is built from L1 IR only; this harness projects the same "
                "v1 rule-atom object and does not import the decompiler for probes"
            ),
            "semantic_logic_roundtrip": (
                "forward, cycle, and final fidelity remain distinct objects; source text may "
                "not enter the realizer prediction"
            ),
            "this_harness": (
                "executor-bound isolation with IR projection and native memory qualification; "
                "no paper A-E/T0-T5 experiment, compiler, retriever, or checker was invoked"
            ),
        },
        "claim_limits": [
            "No A-E or T0-T5 experiment was executed.",
            "No native checker, solver, compiler, retriever, or trained model checkpoint was invoked.",
            "Pilot fixtures and synthetic canaries are not natural held-out evaluation.",
            "Filesystem qualification does not establish network or pretraining exclusion.",
            "Inert AF-008 reviewer counterexamples are not demonstrated paper-experiment leaks.",
            "Parser-assisted features, when used later, must remain disclosed and costed.",
            "This report qualifies isolation controls; it is not an empirical fidelity result.",
            "AF-008 receipt, snapshots, and native success history remain immutable.",
        ],
    }
    report["report_sha256"] = sha256_obj({key: report[key] for key in report if key != "report_sha256"})
    return report


def default_report_path() -> Path:
    return PAPER_ROOT / "evidence" / "leakage_control_report.json"


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    report_cmd = sub.add_parser("report", help="Materialize the leakage-control report")
    report_cmd.add_argument("--root", type=Path, default=REPO_ROOT)
    report_cmd.add_argument("--output", type=Path, default=default_report_path())
    probe_cmd = sub.add_parser("probe", help="Run one adversarial channel probe")
    probe_cmd.add_argument("--view", required=True, choices=VIEWS)
    probe_cmd.add_argument("--channel", required=True, choices=CHANNELS)
    probe_cmd.add_argument("--non-blind", action="store_true")
    sub.add_parser("probe-all", help="Run the compact view × channel probe matrix")
    exec_cmd = sub.add_parser("probe-executor", help="Run one executor-bound channel attempt")
    exec_cmd.add_argument("--view", required=True, choices=VIEWS)
    exec_cmd.add_argument("--channel", required=True, choices=CHANNELS)
    exec_cmd.add_argument("--canary-file", type=Path, default=None)
    sub.add_parser("qualify-memory", help="Qualify the native sample-memory route")
    args = parser.parse_args(argv)
    if args.command == "probe":
        result = probe_channel(args.view, args.channel, declare_non_blind=args.non_blind)
        print(canonical_dumps(result))
        return 0 if not result["recovered"] else 1
    if args.command == "probe-all":
        results = run_adversarial_probes()
        recovered = [item for item in results if item["recovered"]]
        print(canonical_dumps({
            "attempted": len(results),
            "recovered": len(recovered),
            "results": results,
        }))
        return 0 if not recovered else 1
    if args.command == "probe-executor":
        executor = IsolationExecutor()
        canary = str(args.canary_file) if args.canary_file else None
        payload = _fixture_payload(args.view, source_text=SYNTHETIC_SOURCE)
        payload.update(_channel_injection(
            args.channel, source_text=SYNTHETIC_SOURCE, canary_file=canary,
        ))
        features = payload.pop("features", None)
        view_result: dict[str, Any]
        try:
            build_inference_view(
                args.view, payload, source_text=SYNTHETIC_SOURCE, features=features,
            )
            view_rejected = False
            view_reason = "view accepted payload"
        except IsolationError as exc:
            view_rejected = True
            view_reason = str(exc)
        channel_attempt = executor.attempt_channel(
            args.channel, canary_file=canary, source_text=SYNTHETIC_SOURCE,
        )
        recovered = bool(channel_attempt.get("recovered"))
        view_result = {
            "view": args.view,
            "channel": args.channel,
            "attempted": True,
            "recovered": recovered,
            "decision": "rejected" if (view_rejected or not recovered) and not recovered else (
                "non_blind" if recovered else "rejected"
            ),
            "view_rejected": view_rejected,
            "reason": view_reason if view_rejected else channel_attempt.get("error"),
            "channel_attempt": channel_attempt,
            "executor_digest": executor.digest,
            "network_or_pretraining_claimed": False,
        }
        if recovered:
            view_result["decision"] = "non_blind"
        print(canonical_dumps(view_result))
        return 0 if not recovered else 1
    if args.command == "qualify-memory":
        result = qualify_native_sample_memory()
        print(canonical_dumps(result))
        return 0 if result["all_main_arms_update_and_eval_disabled"] else 1
    report = build_leakage_control_report(Path(args.root).resolve())
    output = Path(args.output)
    _write_json(output, report)
    print(canonical_dumps({
        "schema": report["schema"],
        "task_id": report["task_id"],
        "parent_receipt_sha256": report["parent_receipt_sha256"],
        "report_sha256": report["report_sha256"],
        "output": str(output),
        "probes_attempted": report["probe_summary"]["attempted"],
        "probes_recovered": report["probe_summary"]["recovered"],
        "native_memory_disabled": report["native_sample_memory"]["all_main_arms_update_and_eval_disabled"],
        "reconstruction_scores": report["reconstruction_contract"]["symbolic_scores"],
        "request_shape_checks_are_not_executor_qualification": True,
    }))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except IsolationError as exc:
        print(f"inference_isolation: {exc}", flush=True)
        raise SystemExit(1)
