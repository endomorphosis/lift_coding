#!/usr/bin/env python3
"""Inference-time and source-withheld leakage controls for AF-008.

The harness builds separate views for source-only prediction, parser-assisted
prediction, and source-withheld realization.  It does not import project
packages or invoke models, compilers, retrievers, or native checkers.

A realizer in the source-withheld view may see the canonical IR and frozen
public identities.  It may not recover originating text through source maps,
locators, filesystem paths, retrieval, parser state, sample memory, gold IR,
or reference/gold decoder fallbacks.  Shared sample IDs and cache keys are
inspected for memory shortcuts.

Main generalization arms disable sample-indexed memory for update and
evaluation.  T1 remains an explicit memory diagnostic, not a generalization
result.  Forward, cycle, and final reconstruction scores stay distinct.
Parser-assisted features must be disclosed with producer and cost; an arm
that receives them is not raw-text prediction.  Gold/reference fallbacks
cannot receive blind-prediction credit.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence


SCHEMA = "autoformalization-inference-isolation/v1"
REPORT_SCHEMA = "autoformalization-leakage-control-report/v1"
TASK_ID = "AF-008"

HERE = Path(__file__).resolve().parent
PAPER_ROOT = HERE.parent
REPO_ROOT = PAPER_ROOT.parents[2]

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

PUBLIC_REQUEST_KEYS = frozenset({
    "view", "request_id", "canonical_ir", "source_text", "features",
    "vocabulary", "rendering_spec_id", "policy_id",
})

KEY_RE = re.compile(r"[^a-z0-9]+")


class IsolationError(ValueError):
    """Raised when an inference view, leakage channel, or credit rule is violated."""


class ProbeContractError(IsolationError):
    """Raised when the isolation contract failed to reject a blocked channel."""


def canonical_dumps(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_text(text: str) -> str:
    return sha256_bytes(text.encode("utf-8"))


def sha256_obj(value: Any) -> str:
    return sha256_text(canonical_dumps(value))


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
    hits: dict[str, list[str]] = {channel: [] for channel in CHANNELS}
    for path, key, _item in _walk_keys(payload):
        channel = channel_for_key(key)
        if channel is not None:
            hits[channel].append(path)
    return {channel: paths for channel, paths in hits.items() if paths}


def source_text_leaked(value: Any, source_text: str | None) -> bool:
    if not source_text:
        return False
    needle = " ".join(source_text.split())
    if not needle:
        return False
    for piece in _flatten_strings(value):
        if needle and needle in " ".join(str(piece).split()):
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
        if channel_for_key("decoded_embeddings") and payload.get("decoded_embeddings"):
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
            "condition_class": "non_blind_sample_memory",
            "claim": "T1 is a seen-source memory diagnostic, not a generalization result.",
        }
    return {
        "arm": arm,
        "role": "main_generalization" if is_main_generalization_arm(arm) else "other",
        "generalization_arm": True,
        "update": {"use_sample_memory": False},
        "evaluation": {"use_sample_memory": False},
        "blind_prediction_credit": True,
        "condition_class": "blind_shared_parameters_only",
        "claim": "Accepted improvements must come from shared parameters, not sample-indexed memory.",
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


def classify_condition(
    *,
    arm: str,
    view: str,
    leaked_channels: Iterable[str] = (),
    fallback_used: bool = False,
    parser_features: Sequence[Mapping[str, Any]] | None = None,
    declared_non_blind: bool = False,
    declared_non_blind_channels: Sequence[str] = (),
) -> dict[str, Any]:
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
    blind = not reasons and view != "parser_assisted"
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
    credit = (
        blind
        and not fallback_used
        and view != "parser_assisted"
        and not leaked
        and policy["blind_prediction_credit"]
    )
    return {
        "arm": arm,
        "view": view,
        "blind": blind,
        "condition_class": "non_blind" if not blind else "blind",
        "blind_prediction_credit": credit,
        "leaked_channels": list(leaked),
        "declared_non_blind_channels": non_blind_channels,
        "reasons": reasons,
        "parser_feature_count": len(features),
    }


def _reject_blocked_channels(view: str, payload: Mapping[str, Any], *, source_text: str | None) -> dict[str, list[str]]:
    hits = scan_channels(payload)
    blocked = VIEW_BLOCKED_CHANNELS[view]
    leaked = {channel: paths for channel, paths in hits.items() if channel in blocked}
    if view == "parser_assisted":
        leaked.pop("source_text", None)
    if view == "source_only":
        leaked.pop("source_text", None)
    if leaked:
        detail = {channel: paths for channel, paths in leaked.items()}
        raise IsolationError(
            f"{view} view rejects withheld channels {sorted(detail)}: {canonical_dumps(detail)}"
        )
    inspected = None
    if view == "source_withheld":
        inspected = inspect_memory_shortcuts(payload)
        if inspected["shortcut"]:
            raise IsolationError(
                "source-withheld view rejects sample-id/cache-key memory shortcut: "
                + ",".join(inspected["reasons"])
            )
        if source_text_leaked(payload, source_text):
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
    disclosed = disclose_parser_features(features if features is not None else payload.get("features"))
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
        ir = working.get("canonical_ir")
        _expect(isinstance(ir, Mapping) and ir, "source-withheld view requires canonical_ir")
        _expect("source_text" not in working or working.get("source_text") in (None, ""),
                "source-withheld view may not include source_text")
        _reject_blocked_channels(view, working, source_text=source_text)
        if disclosed:
            raise IsolationError(
                "source-withheld realization may not consume original-source parser features"
            )
        request = {
            "view": view,
            "request_id": request_id,
            "canonical_ir": dict(ir),
            "vocabulary": working.get("vocabulary") if isinstance(working.get("vocabulary"), Mapping) else {},
            "rendering_spec_id": working.get("rendering_spec_id"),
            "policy_id": working.get("policy_id"),
            "raw_text_prediction": False,
            "parser_assisted": False,
            "source_withheld": True,
            "features": [],
            "fallback_used": False,
        }
        if source_text_leaked(request, source_text):
            raise IsolationError("canonical IR leaked originating source text")
    request["schema"] = SCHEMA
    request["blind_input_digest"] = sha256_obj(
        {key: request[key] for key in request if key != "blind_input_digest"}
    )
    return request


def probe_channel(
    view: str,
    channel: str,
    *,
    base: Mapping[str, Any] | None = None,
    source_text: str = "A permit holder must file a notice within ten days after approval, unless exempt.",
    declare_non_blind: bool = False,
) -> dict[str, Any]:
    """Attempt to recover withheld source/gold through one documented channel."""
    _expect(view in VIEWS, f"unknown inference view {view}")
    _expect(channel in CHANNELS, f"unknown leakage channel {channel}")
    payload = dict(base or _fixture_payload(view, source_text=source_text))
    injection = _channel_injection(channel, source_text=source_text)
    payload.update(injection)
    features = payload.pop("features", None)
    try:
        built = build_inference_view(
            view,
            payload,
            source_text=source_text,
            features=features,
        )
        allowed = (
            (view == "source_only" and channel == "source_text")
            or (view == "parser_assisted" and channel == "source_text")
        )
        if not allowed:
            raise ProbeContractError(
                f"{channel} injection was not rejected by the {view} view"
            )
        if declare_non_blind:
            decision = "non_blind"
            recovered = False
            reason = "caller declared the affected condition non-blind"
        else:
            decision = "allowed_input"
            recovered = False
            reason = f"{channel} is an allowed input of {view}"
        return {
            "view": view,
            "channel": channel,
            "attempted": True,
            "recovered": recovered,
            "decision": decision,
            "blind_prediction_credit": decision == "allowed_input",
            "reason": reason,
            "request_digest": built.get("blind_input_digest"),
        }
    except ProbeContractError:
        raise
    except IsolationError as exc:
        if declare_non_blind:
            return {
                "view": view,
                "channel": channel,
                "attempted": True,
                "recovered": False,
                "decision": "non_blind",
                "blind_prediction_credit": False,
                "reason": f"rejected then declared non-blind: {exc}",
            }
        return {
            "view": view,
            "channel": channel,
            "attempted": True,
            "recovered": False,
            "decision": "rejected",
            "blind_prediction_credit": False,
            "reason": str(exc),
        }


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
            "request_id": "af008-withheld",
            "canonical_ir": _fixture_ir(),
            "vocabulary": {"actors": ["permit_holder"]},
            "rendering_spec_id": "source_withheld_paraphrase",
            "policy_id": "canonical-parity/v1",
        }
    if view == "parser_assisted":
        return {
            "request_id": "af008-parser",
            "source_text": source_text,
            "features": [
                {
                    "name": "actor_action_object_roles",
                    "kind": "actor_action_object_roles",
                    "producer": "typed-deontic-compiler/v1",
                    "depends_on_parse": True,
                    "requires_complete_compilation": True,
                    "cost": {"compile_seconds": 0.4, "extraction_seconds": 0.05},
                }
            ],
        }
    return {
        "request_id": "af008-source",
        "source_text": source_text,
    }


def _channel_injection(channel: str, *, source_text: str) -> dict[str, Any]:
    if channel == "source_text":
        return {"source_text": source_text, "originating_source": source_text}
    if channel == "source_maps":
        return {"source_map": {"notice": {"start": 28, "end": 34}}, "locator": "span:28-34"}
    if channel == "filesystem":
        return {"source_path": "/corpus/legal/permit-holder-notice.txt", "file_path": "./gold/unit-1.txt"}
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
    for view in VIEWS:
        for channel in CHANNELS:
            results.append(probe_channel(view, channel))
    results.append(probe_channel(
        "source_withheld", "filesystem", declare_non_blind=True,
    ))
    return results


def credit_prediction(
    *,
    view: str,
    arm: str,
    fallback_used: bool = False,
    reconstruction: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    if reconstruction is not None:
        validate_reconstruction_scores(reconstruction)
    condition = classify_condition(
        arm=arm,
        view=view,
        leaked_channels=(),
        fallback_used=fallback_used,
        parser_features=() if view != "parser_assisted" else [{"name": "disclosed"}],
    )
    if fallback_used:
        condition["blind_prediction_credit"] = False
        condition["excluded_from_blind_prediction_credit"] = True
        condition["fallback"] = "reference_or_gold_decoder"
    return condition


def load_frozen_arm_ids(root: Path | None = None) -> list[str]:
    root = root or REPO_ROOT
    plan_path = root / "papers/completion/autoformalization/config/experiment_plan.json"
    if not plan_path.is_file():
        return list(EXPERIMENT_ARMS)
    plan = load_json(plan_path)
    arms = [item["id"] for item in plan.get("conditions") or [] if isinstance(item, Mapping)]
    _expect(arms == list(EXPERIMENT_ARMS), "frozen experiment arms drifted from AF-008 isolation contract")
    return arms


def load_feature_flags(root: Path | None = None) -> dict[str, Any]:
    root = root or REPO_ROOT
    path = root / "papers/completion/autoformalization/config/environment_manifest.json"
    if not path.is_file():
        return {
            "source_withheld_retrieval": False,
            "sample_memory_main_generalization": False,
            "final_test_access": False,
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
    }


def build_leakage_control_report(root: Path | None = None) -> dict[str, Any]:
    root = root or REPO_ROOT
    arms = load_frozen_arm_ids(root)
    flags = load_feature_flags(root)
    probes = run_adversarial_probes()
    withheld_rejects = [
        item for item in probes
        if item["view"] == "source_withheld" and item["decision"] in {"rejected", "non_blind"}
    ]
    _expect(len(withheld_rejects) >= len(CHANNELS),
            "each documented channel must be rejected or declared non-blind on the source-withheld view")
    recovered = [item for item in probes if item.get("recovered")]
    _expect(not recovered, "adversarial probe recovered withheld material")
    arm_policies = {arm: sample_memory_policy(arm) for arm in arms}
    for arm, policy in arm_policies.items():
        if arm in MAIN_GENERALIZATION_ARMS:
            _expect(policy["update"]["use_sample_memory"] is False, f"{arm} update memory enabled")
            _expect(policy["evaluation"]["use_sample_memory"] is False, f"{arm} evaluation memory enabled")
        if arm in MEMORY_DIAGNOSTIC_ARMS:
            _expect(policy["generalization_arm"] is False, "T1 labeled as generalization")
            _expect(policy["blind_prediction_credit"] is False, "T1 received blind credit")
    reconstruction = reconstruction_bundle(
        forward={"status": "unmeasured", "score": None, "compares": "gold_to_first_ir"},
        cycle={"status": "unmeasured", "score": None, "compares": "first_ir_to_second_ir"},
        final={"status": "unmeasured", "score": None, "compares": "gold_to_second_ir"},
        vector={"mse": None, "cosine": None},
    )
    report: dict[str, Any] = {
        "schema": REPORT_SCHEMA,
        "task_id": TASK_ID,
        "isolation_schema": SCHEMA,
        "status": "controls_enforced_empirical_runs_unrun",
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
        "channel_aliases": {channel: sorted(aliases) for channel, aliases in CHANNEL_ALIASES.items()},
        "probes": probes,
        "probe_summary": {
            "attempted": len(probes),
            "recovered": 0,
            "rejected": sum(1 for item in probes if item["decision"] == "rejected"),
            "non_blind": sum(1 for item in probes if item["decision"] == "non_blind"),
            "allowed_input": sum(1 for item in probes if item["decision"] == "allowed_input"),
        },
        "arm_memory_policy": arm_policies,
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
        "parser_assisted_disclosure": {
            "required_fields": [
                "name", "producer", "depends_on_parse",
                "requires_complete_compilation", "cost.compile_seconds",
                "cost.extraction_seconds",
            ],
            "feature_kinds": list(PARSER_FEATURE_KINDS),
            "complete_compilation_must_be_charged": True,
            "cannot_be_described_as_raw_text_prediction": True,
        },
        "blind_prediction_credit": {
            "excludes": [
                "reference_decoder_fallback",
                "gold_decoder_fallback",
                "parser_assisted_undisclosed_as_source_only",
                "source_withheld_channel_recovery",
                "sample_memory_on_generalization_arms",
                "T1_seen_source_memory_diagnostic",
            ],
            "rule": "A fallback involving an admitted reference or gold artifact is not an independent blind prediction.",
        },
        "reuse_boundaries": {
            "modal_autoencoder_generalizable_route": "train_generalizable_projection disables use_sample_memory for updates and evaluation",
            "canonical_roundtrip": "DecompilerRequest is built from L1 IR only; originating source does not cross the boundary",
            "semantic_logic_roundtrip": "forward, cycle, and final fidelity are reported separately; source text may not enter the realizer prompt",
            "this_harness": "stdlib isolation contract for paper evaluation; no model, compiler, or checker was invoked",
        },
        "claim_limits": [
            "No A-E or T0-T5 experiment was executed.",
            "No native checker, solver, compiler, retriever, or model was invoked.",
            "Pilot fixtures are not natural held-out evaluation.",
            "Parser-assisted features, when used later, must remain disclosed and costed.",
            "This report enforces isolation controls; it is not an empirical fidelity result.",
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
    report = build_leakage_control_report(Path(args.root).resolve())
    output = Path(args.output)
    _write_json(output, report)
    print(canonical_dumps({
        "schema": report["schema"],
        "task_id": report["task_id"],
        "report_sha256": report["report_sha256"],
        "output": str(output),
        "probes_attempted": report["probe_summary"]["attempted"],
        "probes_recovered": report["probe_summary"]["recovered"],
        "main_generalization_memory_disabled": all(
            report["arm_memory_policy"][arm]["update"]["use_sample_memory"] is False
            and report["arm_memory_policy"][arm]["evaluation"]["use_sample_memory"] is False
            for arm in report["main_generalization_arms"]
        ),
        "reconstruction_scores": report["reconstruction_contract"]["symbolic_scores"],
    }))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except IsolationError as exc:
        print(f"inference_isolation: {exc}", flush=True)
        raise SystemExit(1)
