"""Reversible lifting of the source-capsule profile's known JSON string slots.

The adapter changes a data representation only. It never parses Python source,
infers intent, observes a repository owner, admits requirements, or authenticates
a caller's original context. Callers must compare restoration with their actual
native compiler output and keep the native current-source checks.
"""
from __future__ import annotations

import base64
from copy import deepcopy
import hashlib
import json
from pathlib import PurePosixPath
import re

SCHEMA = "terminal-native-context-string-lift@1"
PROFILE = "source-complete-display-context-known-json-slots@1"
ENCODING = "canonical-json-ascii@1"
GUIDANCE = (
    "Lossless native context string-slot display encoding. In context, only goal.instruction_json and "
    "each evidence[i].summary are lifted objects. For every restoration_ledger path, serialize that "
    "object as sorted-key compact JSON with ensure_ascii=true and no spaces, and replace the object "
    "with that JSON string. Verify its UTF-8 byte count and SHA-256 against original_bytes and "
    "original_sha256. Then serialize the entire context as sorted-key compact UTF-8 JSON with "
    "ensure_ascii=false and verify original_rendered_bytes and original_rendered_sha256. Retain every "
    "native field, required evidence item, head binding and unresolved requirement. Instruction prose "
    "and source view_text remain opaque strings; never parse, execute, normalize or recursively lift "
    "them. Reject unknown, duplicate or out-of-order ledger paths, floats, changed checksums or "
    "promoted authority claims. The restored bytes must equal the caller's actual native context "
    "before existing native source checks; this encoding grants no proof, task or source-omission authority."
)
LIMITS = {"rendered_bytes": 1_048_576, "document_bytes": 4_194_304,
          "slot_bytes": 262_144, "depth": 64, "nodes": 100_000,
          "evidence": 128, "sources": 2, "capsules": 57}
CLAIMS = {name: False for name in (
    "proof_authority", "execution_authority", "completion_authority",
    "task_satisfaction", "requirement_discharge", "source_omission_authority",
    "source_runtime_equivalence_proved", "source_model_equivalence_proved",
    "native_current_head_observed", "provider_usage_observed")}
_AUTHORITY = {name: False for name in (
    "asymptotic_optimizer_convergence_proved", "completion_authority",
    "execution_authority", "full_task_satisfaction", "global_durable_budget",
    "native_full_supervisor_invoked", "neural_candidate_promoted",
    "official_terminal_bench_harness_executed", "proof_authority",
    "provider_token_savings_measured", "source_model_equivalence_proved",
    "source_runtime_equivalence_proved")}
_CORE_FIELDS = {"acceptance", "authority", "caller", "contract_version", "evidence",
    "goal", "objective_id", "objective_revision", "policy_id", "policy_revision",
    "repository_id", "scope", "stage", "tree_id"}
_REFERENCE_FIELDS = {"byte_count", "content_id", "contract_version", "kind", "metadata",
    "path", "reference_id", "referenced_content_id", "repository_id", "schema", "summary",
    "tier", "token_count", "tree_id"}
_HEAD_FIELDS = {"ast_revision_id", "generation", "manifest_cid", "receipt_cid",
                "repository_id", "schema", "snapshot_cid"}
_SOURCE_FIELDS = {"display_only", "full_source_bytes", "path",
    "raw_source_required_before_edit", "runtime_equivalence_claimed", "source_cid",
    "source_sha256", "view_kind", "view_text"}
_SUMMARY_FIELDS = {"all_task_sources_represented", "capsules", "current_head",
    "native_capsules_are_structural_only", "proof_authority",
    "raw_source_required_before_edit", "schema"}


class NestedContextError(ValueError):
    """An input is outside the closed, reversible source-context profile."""


def _need(value, message):
    if not value:
        raise NestedContextError(message)


def _sha(raw):
    return hashlib.sha256(raw).hexdigest()


def _bytes(text):
    _need(type(text) is str, "exact text string required")
    try:
        return text.encode("utf-8")
    except UnicodeError as error:
        raise NestedContextError("strict UTF-8 text required") from error


def _bounded(value):
    """Bound depth/nodes/types before copying, encoding or expanding a tree."""
    stack, count, seen, text_bytes = [(value, 0)], 0, set(), 0
    while stack:
        item, depth = stack.pop()
        count += 1
        _need(depth <= LIMITS["depth"] and count <= LIMITS["nodes"],
              "bounded context depth and node count required")
        kind = type(item)
        if kind in (dict, list):
            _need(count + len(stack) + len(item) <= LIMITS["nodes"],
                  "bounded context node count required before container expansion")
            _need(id(item) not in seen, "cyclic or shared container references are unsupported")
            seen.add(id(item))
            if kind is dict:
                _need(all(type(key) is str for key in item), "exact string object keys required")
                for key, child in item.items():
                    size = len(_bytes(key))
                    _need(size <= LIMITS["slot_bytes"], "bounded object key required")
                    text_bytes += size
                    stack.append((child, depth + 1))
            else:
                stack.extend((child, depth + 1) for child in item)
        elif kind is str:
            size = len(_bytes(item))
            _need(size <= LIMITS["rendered_bytes"], "bounded text value required")
            text_bytes += size
        elif kind is int:
            _need(item.bit_length() <= 256, "bounded exact native integer required")
        else:
            _need(item is None or kind is bool, "native core must contain no floats or unsupported values")
        _need(text_bytes <= LIMITS["document_bytes"], "cumulative text byte bound exceeded before encoding")


def _wire(value, *, ascii=False):
    _bounded(value)
    try:
        return json.dumps(value, sort_keys=True, separators=(",", ":"),
                          ensure_ascii=ascii, allow_nan=False).encode("utf-8")
    except (ValueError, TypeError, UnicodeError, RecursionError) as error:
        raise NestedContextError("bounded canonical native JSON required") from error


def _pairs(items):
    result = {}
    for key, value in items:
        _need(key not in result, "duplicate JSON object key")
        result[key] = value
    return result


def _parse(text, *, ascii=False, maximum=None):
    raw = _bytes(text)
    _need(0 < len(raw) <= (maximum or LIMITS["rendered_bytes"]), "JSON byte bound exceeded")
    # Limit JSON container depth before invoking the decoder. Brackets within
    # strings are opaque, including source code and escaped nested JSON text.
    depth, quoted, escaped = 0, False, False
    for character in text:
        if quoted:
            if escaped:
                escaped = False
            elif character == "\\":
                escaped = True
            elif character == '"':
                quoted = False
        elif character == '"':
            quoted = True
        elif character in "[{":
            depth += 1
            _need(depth <= LIMITS["depth"], "JSON depth bound exceeded before decoding")
        elif character in "]}":
            depth -= 1
    try:
        value = json.loads(text, object_pairs_hook=_pairs,
                           parse_constant=lambda _: (_ for _ in ()).throw(NestedContextError("nonfinite JSON")))
    except (ValueError, RecursionError) as error:
        if isinstance(error, NestedContextError):
            raise
        raise NestedContextError("ordinary canonical JSON required") from error
    _need(type(value) is dict, "known JSON slot must contain an object")
    _need(_wire(value, ascii=ascii) == raw, "exact canonical JSON encoding required")
    return value


def _hash(value):
    _need(type(value) is str and re.fullmatch(r"[0-9a-f]{64}", value), "exact SHA-256 required")
    return value


def _cid(value):
    _need(type(value) is str and re.fullmatch(r"b[a-z2-7]{20,128}", value), "bounded CID spelling required")
    return value


def _dag_cid(value):
    raw = b"\x01\xa9\x02\x12\x20" + hashlib.sha256(_wire(value)).digest()
    return "b" + base64.b32encode(raw).decode("ascii").rstrip("=").lower()


def _raw_cid(raw):
    encoded = b"\x01\x55\x12\x20" + hashlib.sha256(raw).digest()
    return "b" + base64.b32encode(encoded).decode("ascii").rstrip("=").lower()


def _path(value):
    _need(type(value) is str and value and "\\" not in value, "canonical relative source path required")
    path = PurePosixPath(value)
    _need(not path.is_absolute() and str(path) == value and
          not any(part in {".", "..", ".git"} for part in path.parts),
          "canonical relative source path required")
    return value


def _head(value, core):
    _need(type(value) is dict and set(value) == _HEAD_FIELDS and value["schema"] == "codebase-head@1",
          "complete typed native head fields required")
    _need(type(value["generation"]) is int and value["generation"] > 0,
          "exact positive native generation required")
    _need(value["repository_id"] == core["repository_id"] and value["snapshot_cid"] == core["tree_id"],
          "native repository/tree/head joins differ")
    for field in ("manifest_cid", "receipt_cid", "snapshot_cid"):
        _cid(value[field])
    _need(type(value["ast_revision_id"]) is str and value["ast_revision_id"], "native AST revision required")


def _native_slots(core):
    """Check closed C profile bindings, returning only its declared slot data."""
    _bounded(core)
    _need(type(core) is dict and set(core) == _CORE_FIELDS, "closed native provider core required")
    _need(type(core["contract_version"]) is int and core["contract_version"] == 1,
          "native context version required")
    for field in ("repository_id", "tree_id", "objective_id", "objective_revision", "caller"):
        _need(type(core[field]) is str and core[field] and core[field] == core[field].strip(),
              "native context identifier required")
    _need((core["policy_id"], core["policy_revision"], core["caller"], core["stage"]) ==
          ("source-complete-display-context", "1", "terminal-public-capsule-experiment", "planning-candidate"),
          "known source-complete context profile required")
    _need(type(core["authority"]) is dict and set(core["authority"]) == set(_AUTHORITY)
          and all(value is False for value in core["authority"].values()), "candidate-only native authority required")
    goal, scope, acceptance = core["goal"], core["scope"], core["acceptance"]
    _need(type(goal) is dict and set(goal) == {"instruction_json", "instruction_sha256"}, "closed instruction goal required")
    instruction = _parse(goal["instruction_json"], ascii=True, maximum=LIMITS["slot_bytes"])
    _need(set(instruction) == {"instruction"} and type(instruction["instruction"]) is str,
          "instruction wrapper must contain only opaque text")
    raw_instruction = _bytes(instruction["instruction"])
    _need(raw_instruction and _sha(raw_instruction) == _hash(goal["instruction_sha256"])
          == core["objective_revision"], "complete instruction hash/revision join differs")
    _need(type(scope) is dict and set(scope) == {"all_instruction_requirements_unresolved", "head",
          "raw_source_required_before_edit", "source_paths", "view_only"}, "closed native source scope required")
    _need(all(scope[name] is True for name in ("all_instruction_requirements_unresolved",
          "raw_source_required_before_edit", "view_only")), "unresolved source-only scope required")
    _head(scope["head"], core)
    paths = scope["source_paths"]
    _need(type(paths) is list and 1 <= len(paths) <= LIMITS["sources"] and
          all(type(path) is str for path in paths), "bounded task source path list required")
    _need(paths == sorted(set(paths)), "unique canonical sorted task paths required")
    for path in paths:
        _path(path)
    _need(type(acceptance) is dict and set(acceptance) == {"instruction_sha256",
          "requirement_residual_span_unit", "requirement_residual_spans", "source_semantics_verified", "status"},
          "closed unresolved acceptance required")
    _need(acceptance["instruction_sha256"] == goal["instruction_sha256"] and
          acceptance["requirement_residual_span_unit"] == "utf8_bytes" and
          _wire(acceptance["requirement_residual_spans"]) == _wire([[0, len(raw_instruction)]]) and
          acceptance["source_semantics_verified"] is False and acceptance["status"] == "not_evaluated",
          "complete unresolved instruction residual required")
    evidence = core["evidence"]
    _need(type(evidence) is list and 2 <= len(evidence) <= LIMITS["evidence"], "bounded required native evidence list required")
    slots = [(["goal", "instruction_json"], instruction)]
    sources, capsules, identities, arms = {}, None, [], set()
    for index, reference in enumerate(evidence):
        _need(type(reference) is dict and set(reference) == _REFERENCE_FIELDS,
              "closed native evidence reference required")
        _need(reference["schema"] == "ipfs_accelerate_py/agent-supervisor/context-reference@1" and
              type(reference["contract_version"]) is int and reference["contract_version"] == 1 and
              reference["tier"] == "invariant" and reference["repository_id"] == core["repository_id"] and
              reference["tree_id"] == core["tree_id"], "native evidence identity/binding differs")
        _need(type(reference["metadata"]) is dict and reference["metadata"].get("required") is True,
              "all native source evidence must remain required")
        _need(type(reference["token_count"]) is int and reference["token_count"] == 0,
              "known source-reference token count required")
        text = reference["summary"]
        inner = _parse(text, ascii=True, maximum=LIMITS["slot_bytes"])
        _need(type(reference["byte_count"]) is int and reference["byte_count"] == len(_bytes(text)),
              "native summary byte count differs")
        payload = {key: value for key, value in reference.items() if key != "content_id"}
        _need(reference["content_id"] == _dag_cid(payload), "native evidence content identity differs")
        identities.append(reference["reference_id"])
        if reference["kind"] == "source-view":
            arm = inner.get("view_kind")
            _need(type(arm) is str and arm in {"raw", "minified", "aliased"}, "known whole-source view kind required")
            fields = _SOURCE_FIELDS | ({"alias_dictionary", "alias_guidance"} if arm == "aliased" else set())
            _need(set(inner) == fields, "known whole-source view required")
            path = _path(inner["path"])
            _need(path in paths and path not in sources and reference["path"] == path and
                  reference["reference_id"] == "source:" + _sha(_bytes(path))[:16], "exact unique source path/reference join required")
            _need(reference["referenced_content_id"] == _cid(inner["source_cid"]), "native source CID join differs")
            digest = _hash(inner["source_sha256"])
            _need(_wire(reference["metadata"]) == _wire({"required": True, "coverage_ids": ["source:" + digest],
                  "raw_source_required_before_edit": True, "completion_authority": False}),
                  "required source coverage metadata differs")
            _need(inner["display_only"] is True and inner["raw_source_required_before_edit"] is True and
                  inner["runtime_equivalence_claimed"] is False, "source display must not promote authority")
            _need(type(inner["full_source_bytes"]) is int and 0 < inner["full_source_bytes"] <= LIMITS["slot_bytes"],
                  "whole-source byte bound required")
            raw_view = _bytes(inner["view_text"])
            if arm == "raw":
                _need(len(raw_view) == inner["full_source_bytes"] and _sha(raw_view) == digest and
                      _raw_cid(raw_view) == inner["source_cid"], "raw whole-source byte/hash/CID join differs")
            if arm == "aliased":
                _need(type(inner["alias_dictionary"]) is list and type(inner["alias_guidance"]) is str,
                      "explicit opaque alias display guidance required")
            sources[path] = inner
            arms.add(arm)
        else:
            _need(reference["kind"] == "structural-capsules" and capsules is None and
                  reference["reference_id"] == "native-capsules" and reference["path"] == "" and
                  _wire(reference["metadata"]) == _wire({"required": True}), "one required native capsule summary required")
            _need(set(inner) == _SUMMARY_FIELDS and inner["schema"] == "terminal-native-capsule-task-summary@1",
                  "known native capsule task summary required")
            _need(_wire(inner["current_head"]) == _wire(scope["head"]) and
                  all(inner[key] is True for key in ("all_task_sources_represented", "raw_source_required_before_edit",
                                                    "native_capsules_are_structural_only")) and
                  inner["proof_authority"] is False and reference["referenced_content_id"] == _sha(_bytes(text)),
                  "structural-only capsule summary/head join differs")
            capsules = inner["capsules"]
        slots.append((["evidence", index, "summary"], inner))
    _need(len(set(identities)) == len(identities) and set(sources) == set(paths) and len(arms) == 1,
          "complete unique single-arm source evidence required")
    _need(type(capsules) is list and len(capsules) <= LIMITS["capsules"], "bounded native capsule summary inventory required")
    stable_ids = []
    for capsule in capsules:
        _need(type(capsule) is dict and set(capsule) == {"stable_symbol_id", "capsule_cid", "source_slice_path", "source_cid"},
              "closed native symbol/source capsule summary required")
        path = capsule["source_slice_path"]
        _need(type(path) is str and path in sources and capsule["source_cid"] == sources[path]["source_cid"],
              "native capsule/source path and CID join differs")
        _cid(capsule["capsule_cid"])
        _need(type(capsule["stable_symbol_id"]) is str and capsule["stable_symbol_id"], "native stable symbol identifier required")
        stable_ids.append(capsule["stable_symbol_id"])
    _need(stable_ids == sorted(set(stable_ids)), "unique sorted native capsule summary required")
    return slots, raw_instruction, sources


def lift_context_strings(rendered: str) -> dict:
    """Lift only C's instruction wrapper and evidence summary string slots."""
    core = _parse(rendered)
    slots, _, _ = _native_slots(core)
    context, ledger = deepcopy(core), []
    for path, inner in slots:
        parent = context["goal"] if path[0] == "goal" else context["evidence"][path[1]]
        original = _bytes(parent[path[-1]])
        ledger.append({"path": path, "encoding": ENCODING, "original_bytes": len(original),
                       "original_sha256": _sha(original)})
        parent[path[-1]] = inner
    raw = _bytes(rendered)
    result = {"schema": SCHEMA, "profile": PROFILE, "guidance": GUIDANCE, "context": context,
        "restoration_ledger": ledger, "original_rendered_bytes": len(raw),
        "original_rendered_sha256": _sha(raw), "claims": dict(CLAIMS)}
    _need(len(_wire(result)) <= LIMITS["document_bytes"], "complete lift document byte bound exceeded")
    _need(restore_context_strings(result) == rendered, "internal complete native restoration differs")
    return result


def restore_context_strings(doc: dict) -> str:
    """Restore the exact native JSON, refusing unknown or duplicate slot paths."""
    _bounded(doc)
    _need(type(doc) is dict and set(doc) == {"schema", "profile", "guidance", "context", "restoration_ledger",
          "original_rendered_bytes", "original_rendered_sha256", "claims"}, "closed lift document required")
    _need(doc["schema"] == SCHEMA and doc["profile"] == PROFILE and doc["guidance"] == GUIDANCE,
          "known lossless lift profile and exact guidance required")
    _need(type(doc["claims"]) is dict and set(doc["claims"]) == set(CLAIMS)
          and all(value is False for value in doc["claims"].values()), "lift data must not grant authority")
    _need(type(doc["original_rendered_bytes"]) is int and 0 < doc["original_rendered_bytes"] <= LIMITS["rendered_bytes"],
          "original rendered byte bound required")
    _hash(doc["original_rendered_sha256"])
    _need(len(_wire(doc)) <= LIMITS["document_bytes"], "complete lift document byte bound exceeded")
    context = doc["context"]
    _need(type(context) is dict and type(context.get("goal")) is dict and type(context.get("evidence")) is list
          and len(context["evidence"]) <= LIMITS["evidence"], "known lifted native slot containers required")
    paths = [["goal", "instruction_json"]] + [["evidence", index, "summary"] for index in range(len(context["evidence"]))]
    ledger = doc["restoration_ledger"]
    _need(type(ledger) is list and len(ledger) == len(paths), "complete restoration ledger required")
    core = deepcopy(context)
    for expected_path, row in zip(paths, ledger):
        _need(type(row) is dict and set(row) == {"path", "encoding", "original_bytes", "original_sha256"},
              "closed restoration ledger slot required")
        _need(type(row["path"]) is list and len(row["path"]) == len(expected_path) and
              all(type(a) is type(b) and a == b for a, b in zip(row["path"], expected_path)) and row["encoding"] == ENCODING,
              "unknown, duplicate or out-of-order restoration slot path")
        _need(type(row["original_bytes"]) is int and 0 < row["original_bytes"] <= LIMITS["slot_bytes"],
              "slot byte bound required before expansion")
        _hash(row["original_sha256"])
        parent = core["goal"] if expected_path[0] == "goal" else core["evidence"][expected_path[1]]
        _need(type(parent) is dict and type(parent.get(expected_path[-1])) is dict, "known lifted slot object required")
        encoded = _wire(parent[expected_path[-1]], ascii=True)
        _need(len(encoded) == row["original_bytes"] and _sha(encoded) == row["original_sha256"],
              "original slot byte/hash witness differs")
        parent[expected_path[-1]] = encoded.decode("ascii")
    _native_slots(core)
    raw = _wire(core)
    _need(len(raw) == doc["original_rendered_bytes"] and _sha(raw) == doc["original_rendered_sha256"],
          "complete native provider byte/hash witness differs")
    return raw.decode("utf-8")


def validate_source_complete(*, rendered: str, doc: dict, instruction_bytes: bytes | None = None,
                             source_views: dict | None = None) -> dict:
    """Compare with caller-held native data; qualify representation only.

    For compact source arms, exact source-view restoration is conditional on the
    caller's existing native codec checks. This adapter does not decode aliases
    or minification into source, and it grants no behavioral or owner authority.
    """
    restored = restore_context_strings(doc)
    _need(_bytes(restored) == _bytes(rendered), "caller native provider bytes differ from restoration")
    _, instruction, sources = _native_slots(_parse(restored))
    if instruction_bytes is not None:
        _need(type(instruction_bytes) is bytes and instruction == instruction_bytes,
              "caller complete raw instruction differs")
    if source_views is not None:
        _bounded(source_views)
        _need(type(source_views) is dict and _wire(sources) == _wire(source_views),
              "caller complete source display inventory differs")
    return {"schema": "terminal-native-context-string-lift-validation@1", "data_verified": True,
        "native_provider_bytes_identical": True, "full_native_core_and_requiredness_unchanged": True,
        "whole_instruction_utf8_bytes_retained": True, "whole_instruction_residual_unchanged": True,
        "all_source_display_syntax_unchanged": True, "source_paths": sorted(sources),
        "instruction_sha256": _sha(instruction), "native_rendered_sha256": _sha(_bytes(rendered)),
        "caller_instruction_compared": instruction_bytes is not None,
        "caller_source_views_compared": source_views is not None,
        "all_source_views_raw": all(value["view_kind"] == "raw" for value in sources.values()),
        "raw_source_required_before_edit": True, **CLAIMS}


__all__ = ["NestedContextError", "lift_context_strings", "restore_context_strings",
           "validate_source_complete", "SCHEMA", "PROFILE", "ENCODING", "GUIDANCE", "LIMITS", "CLAIMS"]
