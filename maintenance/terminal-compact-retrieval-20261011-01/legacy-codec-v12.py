"""Lossless source-reference projection of an independently verified coding input.

This codec does not authenticate a capsule, signed source, or native retrieval.
The caller must verify those independently before encoding, and compare the
decoded native hash to its own verified input. Only code-retrieval summaries
change representation. No hit, native identity, chunk boundary, or other field
is discarded. A separately rendered literal public instruction stays literal.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
from pathlib import Path
import re
import stat
import sys

SCHEMA = "supervisor-compact-code-retrieval-prompt@1"
RECEIPT_SCHEMA = "supervisor-code-retrieval-prompt-projection@1"
NATIVE_SCHEMA = "supervisor-code-retrieval-context@1"
FRONTIER_SCHEMA = "supervisor-code-retrieval-frontier-context@1"
MAX_PROMPT_BYTES = 256_000
MAX_WIRE_BYTES = 512_000
MAX_SOURCE_BYTES = 32_768
MAX_CONTEXT_BYTES = 65_536
MAX_CHUNKS = 128
MAX_EVIDENCE = 4096
MAX_DEPTH = 40
MAX_NODES = 100_000
AUTHORITY = ("proof_authority", "execution_authority", "completion_authority", "publication_authority")
FIELDS = {"schema", "scope", "native_prompt_sha256", "native_prompt_bytes", "source_sha256",
          "source_bytes", "code_context_sha256", "code_context_bytes", "native_capsule",
          "suffix", "code_context", "code_slices", *AUTHORITY}
CAPSULE_FIELDS = {"contract_version", "repository_id", "tree_id", "objective_id", "objective_revision",
                  "policy_id", "policy_revision", "caller", "stage", "goal", "authority", "scope",
                  "acceptance", "evidence"}
INSTRUCTIONS = (
    "Exact code-retrieval representation projection follows. It is not a native authority. "
    "code_context query_text {$public_source:true} means the complete separately supplied literal "
    "public instruction, preserving UTF-8 and whitespace. Canonicalize the restored code_context "
    "as sorted compact JSON with literal Unicode. Each native_capsule summary {$code_slice:i} "
    "is that text's code_slices[i] start_char:end_char slice. Restore summaries, canonicalize "
    "native_capsule identically, and append suffix unchanged to recover the exact native prompt. "
    "All hits, identities, sidecars and remaining fields retain their original meanings. "
    "Hash consistency is not admission or source authentication; this adds no authority."
)


class CompactCodeRetrievalError(ValueError):
    pass


def _fail(message):
    raise CompactCodeRetrievalError(message)


def _sha(raw):
    return hashlib.sha256(raw).hexdigest()


def _json(value):
    try:
        return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False)
    except (TypeError, ValueError, UnicodeError, RecursionError) as error:
        raise CompactCodeRetrievalError("canonical finite UTF-8 JSON required") from error


def _bounded(value, maximum):
    count, active = 0, set()
    def visit(item, depth):
        nonlocal count
        count += 1
        if depth > MAX_DEPTH or count > MAX_NODES:
            _fail("JSON depth or node bound exceeded")
        if type(item) in (dict, list):
            if id(item) in active:
                _fail("cyclic JSON value")
            active.add(id(item))
            if type(item) is dict and any(type(key) is not str for key in item):
                _fail("exact string JSON keys required")
            for child in item.values() if type(item) is dict else item:
                visit(child, depth + 1)
            active.remove(id(item))
        elif type(item) not in (str, int, float, bool, type(None)):
            _fail("exact JSON types required")
        elif type(item) is float and not math.isfinite(item):
            _fail("nonfinite number")
    visit(value, 0)
    try:
        raw = _json(value).encode("utf-8")
    except UnicodeError as error:
        raise CompactCodeRetrievalError("valid UTF-8 required") from error
    if len(raw) > maximum:
        _fail("JSON byte bound exceeded")
    return raw


def _text(value, maximum, name):
    if type(value) is not str:
        _fail(name + " must be literal text")
    try:
        raw = value.encode("utf-8")
    except UnicodeError as error:
        raise CompactCodeRetrievalError(name + " is not UTF-8") from error
    if not raw or len(raw) > maximum:
        _fail(name + " byte bound exceeded")
    return raw


def _parse(text, maximum):
    _text(text, maximum, "JSON")
    def unique(pairs):
        result = {}
        for key, value in pairs:
            if key in result:
                _fail("duplicate JSON key")
            result[key] = value
        return result
    try:
        parsed = json.loads(text, object_pairs_hook=unique)
    except (ValueError, RecursionError) as error:
        raise CompactCodeRetrievalError("bounded valid JSON required") from error
    _bounded(parsed, maximum)
    return parsed


def _native(prompt):
    _text(prompt, MAX_PROMPT_BYTES, "native prompt")
    try:
        capsule, end = json.JSONDecoder().raw_decode(prompt)
    except (ValueError, RecursionError) as error:
        raise CompactCodeRetrievalError("canonical native capsule required") from error
    if type(capsule) is not dict or _json(capsule) != prompt[:end]:
        _fail("canonical native capsule required")
    capsule = _parse(prompt[:end], MAX_PROMPT_BYTES)
    if (set(capsule) != CAPSULE_FIELDS or capsule["stage"] != "implementation"
            or type(capsule["evidence"]) is not list or len(capsule["evidence"]) > MAX_EVIDENCE
            or not any(type(row) is dict and row.get("kind") == "semantic-context" for row in capsule["evidence"])):
        _fail("native semantic coding capsule required")
    return capsule, prompt[end:]


def _chunks(capsule):
    from ..context.context_contracts import ContextReference
    selected = [(index, row) for index, row in enumerate(capsule["evidence"])
                if type(row) is dict and row.get("kind") == "code-retrieval-context"]
    if not 1 <= len(selected) <= MAX_CHUNKS:
        _fail("complete bounded code retrieval chunk population required")
    paths, summaries = set(), []
    for number, (position, row) in enumerate(selected):
        try:
            ref = ContextReference.from_dict(row)
        except (ValueError, TypeError, KeyError) as error:
            raise CompactCodeRetrievalError("typed native code reference differs") from error
        meta = row.get("metadata")
        if (type(meta) is not dict or type(meta.get("chunk_index")) is not int
                or type(meta.get("chunk_count")) is not int or meta["chunk_index"] != number
                or meta["chunk_count"] != len(selected) or meta.get("required") is not True
                or ref.repository_id != capsule["repository_id"] or ref.tree_id != capsule["tree_id"]
                or not ref.path or not ref.summary or ref.byte_count != len(ref.summary.encode())
                or ref.referenced_content_id != "sha256:" + _sha(ref.summary.encode())
                or _json(ref.to_record()) != _json(row)):
            _fail("native code reference chunk selectors or identities differ")
        paths.add(ref.path)
        summaries.append(ref.summary)
    text = "".join(summaries)
    _text(text, MAX_CONTEXT_BYTES, "code context")
    artifact_id = "sha256:" + _sha(_json({"text": text}).encode())
    if len(paths) != 1 or any(row["metadata"].get("artifact_content_id") != artifact_id for _, row in selected):
        _fail("native code artifact path or complete chunk binding differs")
    return selected, summaries, text


def _retrieval(context, source_text):
    if type(context) is not dict:
        _fail("native code context required")
    if context.get("schema") == FRONTIER_SCHEMA:
        if any(context.get(key) is not False for key in ("proof_authority", "execution_authority", "completion_authority")):
            _fail("frontier authority must remain false")
        native = context.get("retrieval")
    else:
        native = context
    if (type(native) is not dict or native.get("schema") != NATIVE_SCHEMA
            or native.get("nomination_only") is not True
            or any(native.get(key) is not False for key in ("semantic_authority", "execution_authority", "completion_authority"))
            or type(native.get("hits")) is not list or len(native["hits"]) > 20):
        _fail("native code context authority or hit population differs")
    if native.get("query_text") != source_text:
        _fail("native query differs from the complete literal public source")
    return native


def encode_code_retrieval_prompt(prompt: str, source_text: str) -> dict:
    source_raw = _text(source_text, MAX_SOURCE_BYTES, "source")
    capsule, suffix = _native(prompt)
    selected, summaries, text = _chunks(capsule)
    context = _parse(text, MAX_CONTEXT_BYTES)
    if _json(context) != text:
        _fail("canonical native code context required")
    native = _retrieval(context, source_text)
    native["query_text"] = {"$public_source": True}
    slices, offset = [], 0
    for number, ((position, row), summary) in enumerate(zip(selected, summaries)):
        slices.append({"evidence_index": position, "start_char": offset, "end_char": offset + len(summary),
                       "bytes": len(summary.encode()), "sha256": _sha(summary.encode())})
        offset += len(summary)
        row["summary"] = {"$code_slice": number}
    packet = {"schema": SCHEMA, "scope": "representation_only", "native_prompt_sha256": _sha(prompt.encode()),
        "native_prompt_bytes": len(prompt.encode()), "source_sha256": _sha(source_raw), "source_bytes": len(source_raw),
        "code_context_sha256": _sha(text.encode()), "code_context_bytes": len(text.encode()),
        "native_capsule": capsule, "suffix": suffix, "code_context": context, "code_slices": slices,
        **{key: False for key in AUTHORITY}}
    _bounded(packet, MAX_WIRE_BYTES)
    if decode_code_retrieval_prompt(packet, source_text) != prompt:
        _fail("independent exact native reconstruction differs")
    return packet


def decode_code_retrieval_prompt(packet: dict, source_text: str) -> str:
    raw = _bounded(packet, MAX_WIRE_BYTES)
    source_raw = _text(source_text, MAX_SOURCE_BYTES, "source")
    if (type(packet) is not dict or set(packet) != FIELDS or packet["schema"] != SCHEMA
            or packet["scope"] != "representation_only" or any(packet[key] is not False for key in AUTHORITY)):
        _fail("exact representation-only envelope required")
    for key, maximum in (("native_prompt_bytes", MAX_PROMPT_BYTES), ("code_context_bytes", MAX_CONTEXT_BYTES),
                         ("source_bytes", MAX_SOURCE_BYTES)):
        if type(packet[key]) is not int or not 0 < packet[key] <= maximum:
            _fail("exact bounded byte counts required")
    for key in ("native_prompt_sha256", "code_context_sha256", "source_sha256"):
        if type(packet[key]) is not str or not re.fullmatch(r"[0-9a-f]{64}", packet[key]):
            _fail("exact SHA256 bindings required")
    if len(source_raw) != packet["source_bytes"] or _sha(source_raw) != packet["source_sha256"]:
        _fail("literal source bytes or digest differ")
    body = _parse(raw.decode(), MAX_WIRE_BYTES)
    context = body["code_context"]
    if type(context) is not dict:
        _fail("code context object required")
    native = context.get("retrieval") if context.get("schema") == FRONTIER_SCHEMA else context
    ref = native.get("query_text") if type(native) is dict else None
    if type(ref) is not dict or set(ref) != {"$public_source"} or ref["$public_source"] is not True:
        _fail("exact whole-public-source reference required")
    native["query_text"] = source_text
    _retrieval(context, source_text)
    text = _json(context)
    if len(text.encode()) != packet["code_context_bytes"] or _sha(text.encode()) != packet["code_context_sha256"]:
        _fail("complete native code context digest differs")
    slices, capsule = body["code_slices"], body["native_capsule"]
    if (type(slices) is not list or not 1 <= len(slices) <= MAX_CHUNKS or type(capsule) is not dict
            or set(capsule) != CAPSULE_FIELDS or type(capsule["evidence"]) is not list
            or len(capsule["evidence"]) > MAX_EVIDENCE or type(body["suffix"]) is not str):
        _fail("bounded native capsule and slice inventory required")
    positions = [i for i, row in enumerate(capsule["evidence"])
                 if type(row) is dict and row.get("kind") == "code-retrieval-context"]
    if len(positions) != len(slices):
        _fail("complete code slice inventory differs")
    offset = 0
    for number, (position, item) in enumerate(zip(positions, slices)):
        if (type(item) is not dict or set(item) != {"evidence_index", "start_char", "end_char", "bytes", "sha256"}
                or any(type(item[key]) is not int for key in ("evidence_index", "start_char", "end_char", "bytes"))
                or item["evidence_index"] != position or item["start_char"] != offset
                or not offset < item["end_char"] <= len(text) or item["bytes"] > MAX_CONTEXT_BYTES):
            _fail("exact contiguous code character slices required")
        row = capsule["evidence"][position]
        reference = row.get("summary")
        if (type(reference) is not dict or set(reference) != {"$code_slice"}
                or type(reference["$code_slice"]) is not int or reference["$code_slice"] != number):
            _fail("exact code summary slice reference required")
        summary = text[offset:item["end_char"]]
        if len(summary.encode()) != item["bytes"] or _sha(summary.encode()) != item["sha256"]:
            _fail("original native chunk bytes or digest differ")
        row["summary"] = summary
        offset = item["end_char"]
    if offset != len(text):
        _fail("code slices truncate complete native context")
    prompt = _json(capsule) + body["suffix"]
    _text(prompt, MAX_PROMPT_BYTES, "decoded native prompt")
    if len(prompt.encode()) != packet["native_prompt_bytes"] or _sha(prompt.encode()) != packet["native_prompt_sha256"]:
        _fail("exact original native prompt digest differs")
    checked, _ = _native(prompt)
    _, _, joined = _chunks(checked)
    if joined != text:
        _fail("independent native chunk reconstruction differs")
    return prompt


def render_code_retrieval_prompt(packet: dict, *, decoder_command: str | None = None) -> str:
    guidance = INSTRUCTIONS
    if decoder_command is not None:
        _text(decoder_command, 8192, "decoder command")
        guidance += " Read-only exact decoder command: " + decoder_command
    return guidance + "\n" + _bounded(packet, MAX_WIRE_BYTES).decode()


def parse_code_retrieval_prompt(prompt: str, *, decoder_command: str | None = None) -> dict:
    prefix = INSTRUCTIONS + (" Read-only exact decoder command: " + decoder_command if decoder_command is not None else "") + "\n"
    if type(prompt) is not str or not prompt.startswith(prefix):
        _fail("exact compact decoder guidance required")
    return _parse(prompt[len(prefix):], MAX_WIRE_BYTES)


def project_code_retrieval_prompt(prompt: str, source_text: str, *, decoder_command: str | None = None) -> tuple[str, dict]:
    packet = encode_code_retrieval_prompt(prompt, source_text)
    candidate = render_code_retrieval_prompt(packet, decoder_command=decoder_command)
    selected = candidate if len(candidate.encode()) < len(prompt.encode()) else prompt
    context = packet["code_context"]
    native = context["retrieval"] if context["schema"] == FRONTIER_SCHEMA else context
    wire = _bounded(packet, MAX_WIRE_BYTES)
    receipt = {"schema": RECEIPT_SCHEMA, "requested_transport": "compact",
        "selected_transport": "compact" if selected is candidate else "expanded",
        "reason": "complete_projection_smaller" if selected is candidate else "complete_projection_not_smaller",
        "wire_schema": SCHEMA, "wire_sha256": _sha(wire), "wire_bytes": len(wire),
        "native_prompt_sha256": packet["native_prompt_sha256"], "native_prompt_bytes": packet["native_prompt_bytes"],
        "source_sha256": packet["source_sha256"], "source_bytes": packet["source_bytes"],
        "code_context_sha256": packet["code_context_sha256"], "code_context_bytes": packet["code_context_bytes"],
        "code_chunk_count": len(packet["code_slices"]), "code_hit_count": len(native["hits"]),
        "candidate_prompt_bytes": len(candidate.encode()), "selected_prompt_bytes": len(selected.encode()),
        "selected_prompt_sha256": _sha(selected.encode()), "exact_native_roundtrip_verified": True,
        "source_authentication_claimed": False, "native_authentication_claimed": False,
        **{key: False for key in AUTHORITY}}
    return selected, receipt


def _read_file(path: Path, maximum: int, *, source=False) -> bytes:
    path = Path(path)
    if not path.is_absolute() or path.resolve(strict=True) != path:
        _fail("canonical absolute decoder file required")
    if source and any(path.is_relative_to(Path("/opt/ipfs-supervisor") / private)
                      for private in ("state", "home", "codex-auth")):
        _fail("private owner source is outside public decoder scope")
    fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
    with os.fdopen(fd, "rb") as stream:
        before = os.fstat(stream.fileno())
        if (not stat.S_ISREG(before.st_mode) or before.st_nlink != 1 or not 0 < before.st_size <= maximum
                or source and os.access(path, os.W_OK)):
            _fail("bounded regular protected public source required" if source else "bounded regular wire file required")
        raw = stream.read(maximum + 1)
        after = os.fstat(stream.fileno())
    identity = lambda info: (info.st_dev, info.st_ino, info.st_size, info.st_mtime_ns, info.st_ctime_ns)
    if len(raw) > maximum or identity(before) != identity(after) or identity(after) != identity(path.lstat()):
        _fail("decoder input changed during read")
    return raw


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("operation", choices=("decode",))
    parser.add_argument("--wire", type=Path, required=True)
    parser.add_argument("--source", type=Path, required=True)
    for name in ("wire", "source", "native"):
        parser.add_argument("--expected-" + name + "-sha256", required=True)
    args = parser.parse_args()
    for digest in (args.expected_wire_sha256, args.expected_source_sha256, args.expected_native_sha256):
        if re.fullmatch(r"[0-9a-f]{64}", digest) is None:
            _fail("independent decoder SHA256 pins required")
    wire = _read_file(args.wire, MAX_WIRE_BYTES)
    source = _read_file(args.source, MAX_SOURCE_BYTES, source=True)
    if _sha(wire) != args.expected_wire_sha256 or _sha(source) != args.expected_source_sha256:
        _fail("independent wire or source pin differs")
    prompt = decode_code_retrieval_prompt(_parse(wire.decode("utf-8"), MAX_WIRE_BYTES), source.decode("utf-8"))
    if _sha(prompt.encode()) != args.expected_native_sha256:
        _fail("independent native prompt pin differs")
    if _read_file(args.source, MAX_SOURCE_BYTES, source=True) != source:
        _fail("public source changed during decode")
    sys.stdout.buffer.write(prompt.encode())


if __name__ == "__main__":
    main()
