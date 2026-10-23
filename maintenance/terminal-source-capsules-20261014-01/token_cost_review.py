"""Exact offline BPE costs for paired caller-supplied complete message scripts.

Counts describe the provided serialized strings. They do not establish provider
protocol equivalence, actual calls/usage, completeness of a live session or task
satisfaction. Historical inputs are charged again at every scripted call.
"""
from __future__ import annotations

import base64
import bisect
from copy import deepcopy
import hashlib
import importlib.metadata
import json
import os
from pathlib import Path
import stat

SCHEMA = "terminal-full-message-local-token-cost@1"
MAX_EVENTS, MAX_PAYLOAD_BYTES, MAX_TOTAL_BYTES = 32, 500_000, 16 * 1024 * 1024
PARTITIONS = ("setup", "history", "retrieval", "capsule", "expansion", "retry", "output", "framing", "task")
ENCODING, VERSION = "o200k_base", "0.13.0"
BPE_SHA256 = "446a9538cb6c348e3516120d7c08b09f57c36495e2acfffe59a5bf8b0cfb1a2d"
DEFINITION_SHA256 = "a6557bbd3ceb299981ac87fd86a51fa8f0e9505be18ed608c5ada94bdfd0f63f"
BPE_ASSET = Path("/home/barberb/lift_coding/maintenance/terminal-dispatch-evidence-20261014-01/public-tokenizer-cache/fb374d419588a4632f3f557e76b4b70aebbca790")
TOKENIZER_ROOT = Path("/home/barberb/lift_coding/maintenance/terminal-token-pairing-20261012-01/pinned-host-tokenizer/tiktoken")
IMPLEMENTATION = {
    "__init__.py": "3feb6a819185a05dc4112d0a826f16c92079eda97dd54b0982fb196ffce06f11",
    "core.py": "3c136f06b05992855dc329216dfa1fa5b6718cccd3d79f658262de8f871f45f0",
    "_tiktoken.cpython-312-aarch64-linux-gnu.so": "caa29bc388c82b8948ce88b5c69f3594533224deb905cbc1d116f7eb009d064a",
}
PATTERN = "|".join([
    r"[^\r\n\p{L}\p{N}]?[\p{Lu}\p{Lt}\p{Lm}\p{Lo}\p{M}]*[\p{Ll}\p{Lm}\p{Lo}\p{M}]+(?i:'s|'t|'re|'ve|'m|'ll|'d)?",
    r"[^\r\n\p{L}\p{N}]?[\p{Lu}\p{Lt}\p{Lm}\p{Lo}\p{M}]+[\p{Ll}\p{Lm}\p{Lo}\p{M}]*(?i:'s|'t|'re|'ve|'m|'ll|'d)?",
    r"\p{N}{1,3}", r" ?[^\s\p{L}\p{N}]+[\r\n/]*", r"\s*[\r\n]+", r"\s+(?!\S)", r"\s+",
])
CLAIMS = {"provider_usage_measured": False, "provider_output_measured": False,
    "provider_savings_measured": False, "provider_tokenizer_equivalence_established": False,
    "actual_provider_calls_attested": False, "actual_live_history_completeness_verified": False,
    "source_equivalence_proved": False, "full_task_satisfaction_established": False,
    "proof_authority": False, "execution_authority": False, "completion_authority": False}
_CACHE = None


class TokenCostError(ValueError):
    """The offline definition, complete script or declared partition differs."""


def _need(condition, message):
    if not condition:
        raise TokenCostError(message)


def _json(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False)


def _sha(raw):
    return hashlib.sha256(raw).hexdigest()


def _read(path, maximum):
    path = Path(path)
    _need(path.is_absolute() and path.resolve(strict=True) == path, "canonical named offline asset required")
    descriptor = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
    with os.fdopen(descriptor, "rb") as stream:
        before = os.fstat(stream.fileno())
        _need(stat.S_ISREG(before.st_mode) and before.st_nlink == 1 and 0 < before.st_size <= maximum,
              "bounded single-link regular offline asset required")
        raw = stream.read(maximum + 1)
        after = os.fstat(stream.fileno())
    witness = lambda item: (item.st_dev, item.st_ino, item.st_size, item.st_mtime_ns, item.st_ctime_ns)
    _need(len(raw) <= maximum and len(raw) == before.st_size and witness(before) == witness(after)
          and witness(after) == witness(path.lstat()), "offline asset changed during acquisition")
    return raw


def _definition(encoding):
    digest = hashlib.sha256(_json({"name": encoding.name, "pattern": encoding._pat_str,
                                 "special_tokens": encoding._special_tokens}).encode())
    for token, rank in sorted(encoding._mergeable_ranks.items(), key=lambda item: item[1]):
        digest.update(rank.to_bytes(4, "big"))
        digest.update(len(token).to_bytes(4, "big"))
        digest.update(token)
    return digest.hexdigest()


class OfflineTokenizer:
    """Ordinary-text adapter around the pinned native BPE implementation."""
    def __init__(self, encoding):
        self._encoding = encoding

    def encode(self, text):
        _text(text)
        tokens = self._encoding.encode(text, allowed_special=set(), disallowed_special=())
        _need(self._encoding.decode(tokens) == text, "complete UTF-8 tokenizer roundtrip differs")
        return tokens

    def decode(self, tokens):
        return self._encoding.decode(tokens)

    def decode_single_token_bytes(self, token):
        return self._encoding.decode_single_token_bytes(token)


def load_tokenizer(tokenizer_descriptor=None):
    """Construct directly from checked offline ranks; never call a registry/fetch."""
    global _CACHE
    raw = _read(BPE_ASSET, 8_000_000)
    _need(_sha(raw) == BPE_SHA256, "offline BPE rank asset differs from its pin")
    import tiktoken
    import tiktoken.core
    import tiktoken._tiktoken
    _need(importlib.metadata.version("tiktoken") == VERSION, "exact pinned tiktoken version required")
    modules = (tiktoken, tiktoken.core, tiktoken._tiktoken)
    pins = []
    for module in modules:
        path = Path(module.__file__)
        _need(path.parent == TOKENIZER_ROOT and path.name in IMPLEMENTATION,
              "loaded tokenizer is outside the explicit preserved implementation")
        body = _read(path, 8_000_000)
        _need(_sha(body) == IMPLEMENTATION[path.name], "tokenizer implementation file differs")
        pins.append({"path": str(path), "bytes": len(body), "sha256": _sha(body)})
    descriptor = {"schema": "terminal-offline-bpe-definition@1", "library": "tiktoken", "version": VERSION,
        "encoding": ENCODING, "definition_sha256": DEFINITION_SHA256,
        "bpe_asset": {"path": str(BPE_ASSET), "bytes": len(raw), "sha256": BPE_SHA256},
        "implementation_files": pins, "offline": True, "network_fallback": False,
        "ordinary_text_special_spellings": True, "algorithm_independent": False,
        "provider_tokenizer_equivalence_established": False}
    if tokenizer_descriptor is not None:
        _need(type(tokenizer_descriptor) is dict and _json(tokenizer_descriptor) == _json(descriptor),
              "tokenizer descriptor differs from the exact local definition")
    if _CACHE is None:
        ranks = {}
        for line in raw.splitlines():
            token, rank = line.split()
            decoded, rank = base64.b64decode(token, validate=True), int(rank)
            _need(decoded not in ranks, "duplicate offline BPE token")
            ranks[decoded] = rank
        encoding = tiktoken.Encoding(ENCODING, pat_str=PATTERN, mergeable_ranks=ranks,
            special_tokens={"<|endoftext|>": 199999, "<|endofprompt|>": 200018})
        _need(_definition(encoding) == DEFINITION_SHA256, "BPE vocabulary/pattern/special-token definition differs")
        _CACHE = OfflineTokenizer(encoding)
    _need(_definition(_CACHE._encoding) == DEFINITION_SHA256, "cached tokenizer definition changed")
    return _CACHE, deepcopy(descriptor)


def tokenizer_count(text):
    tokenizer, _ = load_tokenizer()
    return len(tokenizer.encode(text))


def _text(text):
    _need(type(text) is str, "exact payload string required")
    try:
        raw = text.encode("utf-8")
    except UnicodeError as error:
        raise TokenCostError("strict UTF-8 input required") from error
    _need(len(raw) <= MAX_PAYLOAD_BYTES, "whole payload byte bound exceeded")
    return raw


def serialize_messages(messages, message_partitions=None):
    """Render complete role/content messages and classify every framing byte.

    Optional message ``segments`` subdivide content without changing the actual
    serialized role/content fields. Labels/IDs stay outside the delivered JSON.
    """
    _need(type(messages) is list and 1 <= len(messages) <= 128, "bounded full message list required")
    if message_partitions is not None:
        _need(type(message_partitions) is list and len(message_partitions) == len(messages), "one partition per message required")
    segments = [{"partition": "framing", "text": '{"messages":['}]
    actual, manifest = [], []
    for index, message in enumerate(messages):
        _need(type(message) is dict and message.get("role") in {"system", "developer", "user", "assistant", "tool"},
              "explicit bounded message role required")
        content = message.get("content")
        _text(content)
        category = message.get("partition", "task") if message_partitions is None else message_partitions[index]
        pieces = message.get("segments", [{"partition": category, "text": content}])
        _need(type(pieces) is list and 1 <= len(pieces) <= 128, "bounded message content segments required")
        _need("".join(piece.get("text", "") for piece in pieces) == content, "complete message content segment cover required")
        header = ("," if index else "") + '{"role":' + _json(message["role"]) + ',"content":"'
        segments.append({"partition": "framing", "text": header})
        for piece in pieces:
            _need(type(piece) is dict and set(piece) == {"partition", "text"} and piece["partition"] in PARTITIONS,
                  "known exact content partition required")
            _text(piece["text"])
            segments.append({"partition": piece["partition"], "text": _json(piece["text"])[1:-1]})
        segments.append({"partition": "framing", "text": '"}'})
        actual.append({"role": message["role"], "content": content})
        if "message_id" in message:
            _need(type(message["message_id"]) is str and 0 < len(message["message_id"]) <= 128, "bounded message ID required")
            manifest.append({"message_id": message["message_id"], "role": message["role"],
                             "message_index": index, "content_sha256": _sha(content.encode())})
    segments.append({"partition": "framing", "text": "]}"})
    payload = "".join(piece["text"] for piece in segments)
    _text(payload)
    _need(json.loads(payload) == {"messages": actual}, "full serialized messages differ")
    return {"payload": payload, "segments": segments, "messages": actual, "message_manifest": manifest}


def _event(event, tokenizer, earlier):
    _need(type(event) is dict and type(event.get("event_id")) is str
          and 0 < len(event["event_id"]) <= 128 and event["event_id"] not in earlier,
          "unique bounded event identity required")
    allowed = {"event_id", "kind", "payload", "segments", "retry_of", "messages", "message_manifest", "required_history_ids"}
    _need(set(event) <= allowed, "event has undeclared fields or unsupported provider claims")
    kind = {"model_input": "input", "model_output": "output", "local_setup": "setup"}.get(event.get("kind"), event.get("kind"))
    _need(kind in {"input", "output", "setup"}, "closed local event kind required")
    payload, retry = event.get("payload"), event.get("retry_of")
    raw = _text(payload)
    _need(retry is None or (kind == "input" and retry in earlier and earlier[retry]["kind"] == "input"),
          "retry must name a previously counted full input")
    segments = event.get("segments", [{"partition": "output" if kind == "output" else "setup" if kind == "setup" else "task", "text": payload}])
    _need(type(segments) is list and 1 <= len(segments) <= 1024, "bounded complete partition list required")
    ends, partition_bytes, normalized = [], CounterDict(), []
    offset = 0
    for piece in segments:
        _need(type(piece) is dict and set(piece) == {"partition", "text"} and piece["partition"] in PARTITIONS,
              "exact known full-payload partition required")
        body = _text(piece["text"])
        offset += len(body)
        ends.append(offset)
        partition_bytes[piece["partition"]] += len(body)
        normalized.append(piece)
    _need("".join(piece["text"] for piece in normalized) == payload, "partition cover omits or changes delivered payload bytes")
    if "messages" in event:
        _need(json.loads(payload) == {"messages": event["messages"]}, "full serialized message population differs")
    required = event.get("required_history_ids", [])
    manifest = event.get("message_manifest", [])
    _need(type(required) is list and type(manifest) is list
          and set(required) <= {message["message_id"] for message in manifest}, "declared required history messages are omitted")
    _need(len({message["message_id"] for message in manifest}) == len(manifest), "duplicate declared message ID")
    messages = event.get("messages", [])
    prior_messages = {item["message_id"]: item for row in earlier.values() for item in row["message_manifest"]}
    for item in manifest:
        _need(type(item) is dict and set(item) == {"message_id", "message_index", "role", "content_sha256"}
              and type(item["message_index"]) is int and 0 <= item["message_index"] < len(messages),
              "exact indexed message provenance required")
        message = messages[item["message_index"]]
        _need(item["role"] == message["role"] and item["content_sha256"] == _sha(message["content"].encode()),
              "message hash or role differs from full serialization")
        previous = prior_messages.get(item["message_id"])
        _need(previous is None or (previous["role"] == item["role"]
              and previous["content_sha256"] == item["content_sha256"]), "declared historical message identity changed")
    tokens = tokenizer.encode(payload)
    pieces = [tokenizer.decode_single_token_bytes(token) for token in tokens]
    _need(b"".join(pieces) == raw, "whole-input token byte reconstruction differs")
    attributed, offset = CounterDict(), 0
    for piece in pieces:
        index = bisect.bisect_right(ends, offset)
        _need(index < len(normalized), "token starts outside complete partition inventory")
        attributed[normalized[index]["partition"]] += 1
        offset += len(piece)
    _need(sum(attributed.values()) == len(tokens) and sum(partition_bytes.values()) == len(raw), "partition totals do not conserve full cost")
    return {"event_id": event["event_id"], "kind": kind, "retry_of": retry,
        "sha256": _sha(raw), "bytes": len(raw), "tokens": len(tokens),
        "partition_tokens": dict(attributed), "partition_bytes": dict(partition_bytes),
        "messages": len(event.get("messages", [])), "declared_required_history_ids": list(required),
        "message_manifest": deepcopy(manifest),
        "token_attribution": "entire BPE token charged to partition containing its first UTF-8 byte",
        "cross_partition_merges_counted_once": True}


class CounterDict(dict):
    def __missing__(self, key):
        return 0


def _arm(events, tokenizer):
    _need(type(events) is list and 1 <= len(events) <= MAX_EVENTS, "bounded explicit complete event script required")
    rows, earlier = [], {}
    totals = {"input_tokens": 0, "output_tokens": 0, "setup_tokens": 0, "total_tokens": 0,
              "input_bytes": 0, "output_bytes": 0, "setup_bytes": 0, "total_bytes": 0,
              "input_events": 0, "output_events": 0, "setup_events": 0, "retry_input_tokens": 0, "retry_events": 0}
    partitions, byte_partitions = CounterDict(), CounterDict()
    for event in events:
        row = _event(event, tokenizer, earlier)
        earlier[row["event_id"]] = row
        kind = row["kind"]
        for unit in ("tokens", "bytes"):
            totals[kind + "_" + unit] += row[unit]
            totals["total_" + unit] += row[unit]
        totals[kind + "_events"] += 1
        _need(totals["total_bytes"] <= MAX_TOTAL_BYTES, "cumulative full-script byte bound exceeded")
        if row["retry_of"] is not None:
            totals["retry_input_tokens"] += row["tokens"]
            totals["retry_events"] += 1
        for name, count in row["partition_tokens"].items():
            partitions[name] += count
        for name, count in row["partition_bytes"].items():
            byte_partitions[name] += count
        row["cumulative_tokens"] = totals["total_tokens"]
        row["cumulative_bytes"] = totals["total_bytes"]
        rows.append(row)
    return {"events": rows, "totals": totals,
        "partition_totals": {name: {"tokens": partitions[name], "bytes": byte_partitions[name]} for name in PARTITIONS},
        "whole_input_counted_each_call": True, "history_deduplicated": False,
        "scripted_output_counted_separately": True, "local_setup_materialization_included": True,
        "setup_materialization_equals_provider_input": False}


def evaluate_token_costs(baseline_events, compact_events, tokenizer_descriptor=None):
    """Count full serialized scripts and their exact local cumulative difference."""
    tokenizer, descriptor = load_tokenizer(tokenizer_descriptor)
    baseline, compact = _arm(baseline_events, tokenizer), _arm(compact_events, tokenizer)
    base_rows = {row["event_id"]: row for row in baseline["events"]}
    prefixes = []
    for row in compact["events"]:
        other = base_rows.get(row["event_id"])
        if other is not None:
            _need(other["kind"] == row["kind"], "common event anchors have different cost kind")
            prefixes.append({"event_id": row["event_id"], "baseline_cumulative_tokens": other["cumulative_tokens"],
                "compact_cumulative_tokens": row["cumulative_tokens"],
                "signed_local_token_difference": other["cumulative_tokens"] - row["cumulative_tokens"]})
    first = next((row["event_id"] for row in prefixes if row["signed_local_token_difference"] >= 0), None)
    difference = baseline["totals"]["total_tokens"] - compact["totals"]["total_tokens"]
    # Revalidate bytes/implementation/definition after every measurement.
    _, after = load_tokenizer(descriptor)
    _need(after == descriptor, "offline tokenizer changed during paired measurement")
    return {"schema": SCHEMA, "qualified_local_accounting": True,
        "baseline": baseline, "compact": compact, "tokenizer": descriptor,
        "paired_cumulative_anchors": prefixes,
        "break_even": {"first_nonnegative_common_anchor": first,
            "final_full_cost_signed_difference": difference, "compact_full_cost_is_lower": difference > 0,
            "includes_setup_history_retrieval_expansion_retries_scripted_output": True,
            "additional_expansion_requires_rerendering_all_affected_full_inputs": True},
        "signed_local_token_difference": difference,
        "signed_local_byte_difference": baseline["totals"]["total_bytes"] - compact["totals"]["total_bytes"],
        "accounting_scope": "exact supplied full serialized input/output and explicit setup-materialization strings",
        "partition_counts_add_to_whole": True, "partition_attribution_is_provider_billing": False,
        "provider_usage": None, "provider_token_savings": None, "provider_money_savings": None,
        "actual_provider_invocations_created": 0, "raw_payloads_exported": False, **CLAIMS}
