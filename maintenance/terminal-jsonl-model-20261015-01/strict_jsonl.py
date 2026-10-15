"""Bounded, byte-cited JSONL projection into the authored scheduler row model.

This module only parses supplied bytes.  It does not open files, import a
repository under test, observe runtime cost metrics, or authorize execution.
The accepted grammar is deliberately narrower than general JSON/JSONL.
"""
from __future__ import annotations

import hashlib
import json
import re

SCHEMA = "terminal-strict-jsonl-byte-projection@1"
MAX_BYTES = 65536
MAX_RECORDS = 256
MAX_LINE_BYTES = 8192
MAX_DEPTH = 8
MAX_INTEGER = 10**18
MAX_IDENTIFIER_BYTES = 512
MAX_REPORT_BYTES = 2 * 1024 * 1024
LIMITS = {
    "max_file_bytes": MAX_BYTES,
    "max_records": MAX_RECORDS,
    "max_physical_line_bytes": MAX_LINE_BYTES,
    "max_container_depth": MAX_DEPTH,
    "max_integer": MAX_INTEGER,
    "max_identifier_utf8_bytes": MAX_IDENTIFIER_BYTES,
}
FALSE_CLAIMS = {
    "original_semantic_coverage_complete": False,
    "full_task_satisfaction_proved": False,
    "source_model_equivalence_proved": False,
    "source_runtime_semantics_verified": False,
    "physical_input_immutability_proved": False,
    "runtime_metrics_observed": False,
    "formal_proof": False,
    "convergence_proved": False,
    "planning_or_dispatch_authority": False,
}
_NAT = re.compile(r"(?:0|[1-9][0-9]{0,18})\Z", re.ASCII)


class StrictJSONLError(ValueError):
    """Supplied bytes or a retained projection exceed the closed profile."""


def _sha(raw):
    return hashlib.sha256(raw).hexdigest()


def _integer(lexeme):
    # Check length/grammar before conversion, including Python's large-int path.
    if not _NAT.fullmatch(lexeme):
        raise StrictJSONLError("integer lexeme must be an ASCII bounded natural")
    value = int(lexeme)
    if value > MAX_INTEGER:
        raise StrictJSONLError("integer exceeds the finite row model")
    return value


def _not_number(_lexeme):
    raise StrictJSONLError("floating point and non-finite numbers are outside the row model")


def _object(pairs):
    row = {}
    for key, value in pairs:
        if key in row:
            raise StrictJSONLError("duplicate decoded JSON object key")
        row[key] = value
    return row


def _preflight(record):
    """Bound structural nesting before json.loads allocates hydrated values."""
    stack = []
    quoted = escaped = False
    for byte in record:
        if quoted:
            if escaped:
                escaped = False
            elif byte == 92:
                escaped = True
            elif byte == 34:
                quoted = False
            elif byte < 32:
                raise StrictJSONLError("unescaped control byte in JSON string")
            continue
        if byte == 34:
            quoted = True
        elif byte in (123, 91):
            stack.append(125 if byte == 123 else 93)
            if len(stack) > MAX_DEPTH:
                raise StrictJSONLError("JSON container nesting exceeds the preflight bound")
        elif byte in (125, 93):
            if not stack or stack.pop() != byte:
                raise StrictJSONLError("JSON containers are unbalanced")
    if quoted or stack:
        raise StrictJSONLError("JSON string or container is unfinished")


def _identifier(value):
    if type(value) is not str:
        raise StrictJSONLError("identifiers must be plain UTF-8 strings")
    try:
        raw = value.encode("utf-8", errors="strict")
    except UnicodeError as exc:
        raise StrictJSONLError("identifier contains a non-Unicode scalar") from exc
    if len(raw) > MAX_IDENTIFIER_BYTES or b"\x00" in raw:
        raise StrictJSONLError("identifier exceeds the bounded UTF-8 profile")


def _natural(value):
    if type(value) is not int or not 0 <= value <= MAX_INTEGER:
        raise StrictJSONLError("row dimensions must be exact bounded natural integers")


def _row(value, kind):
    fields = ({"request_id", "prompt_len", "gen_len"} if kind == "requests"
              else {"request_id", "batch_id", "shape"})
    if type(value) is not dict or set(value) != fields:
        raise StrictJSONLError("record has an unknown or missing field")
    _identifier(value["request_id"])
    if kind == "requests":
        _natural(value["prompt_len"])
        _natural(value["gen_len"])
    else:
        _identifier(value["batch_id"])
        shape = value["shape"]
        if type(shape) is not dict or set(shape) != {"seq_align", "heads_align", "hidden_align"}:
            raise StrictJSONLError("shape has an unknown or missing field")
        for item in shape.values():
            _natural(item)
    return value


def _plain_json(value, depth=0, nodes=None):
    if nodes is None:
        nodes = [0]
    nodes[0] += 1
    if depth > 16 or nodes[0] > 32768:
        raise StrictJSONLError("retained report exceeds its structural bound")
    if value is None or type(value) in (bool, int):
        if type(value) is int and not 0 <= value <= MAX_INTEGER:
            raise StrictJSONLError("retained report integer exceeds its bound")
        return
    if type(value) is str:
        try:
            encoded = value.encode("utf-8", errors="strict")
        except UnicodeError as exc:
            raise StrictJSONLError("retained report string is not strict UTF-8") from exc
        if len(encoded) > MAX_REPORT_BYTES:
            raise StrictJSONLError("retained report string exceeds its byte bound")
        return
    if type(value) is list and len(value) <= 4096:
        for item in value:
            _plain_json(item, depth + 1, nodes)
        return
    if type(value) is dict and len(value) <= 4096 and all(type(key) is str for key in value):
        for key, item in value.items():
            _plain_json(key, depth + 1, nodes)
            _plain_json(item, depth + 1, nodes)
        return
    raise StrictJSONLError("retained report must contain only bounded plain JSON values")


def _canonical(value):
    _plain_json(value)
    raw = json.dumps(value, sort_keys=True, separators=(",", ":"),
                     ensure_ascii=True, allow_nan=False).encode("ascii")
    if len(raw) > MAX_REPORT_BYTES:
        raise StrictJSONLError("retained report exceeds its serialized byte bound")
    return raw


def parse_jsonl(raw: bytes, *, kind: str) -> dict:
    """Project exact supplied JSONL bytes into ordered, source-cited row values.

    Spans use half-open file byte offsets.  A record span excludes its LF/CRLF
    terminator and retains any horizontal JSON whitespace.  A line span includes
    that terminator.  Empty files represent an explicit zero-row finite input.
    """
    if type(raw) is not bytes or len(raw) > MAX_BYTES:
        raise StrictJSONLError("input must be plain bytes within the file byte bound")
    if type(kind) is not str or kind not in {"requests", "plan"}:
        raise StrictJSONLError("kind must select requests or plan")
    if raw.startswith(b"\xef\xbb\xbf") or b"\x00" in raw:
        raise StrictJSONLError("UTF-8 BOM and NUL bytes are outside the JSONL profile")
    try:
        raw.decode("utf-8", errors="strict")
    except UnicodeError as exc:
        raise StrictJSONLError("file must contain strict UTF-8 bytes") from exc
    records, rows, identifiers = [], [], set()
    offset = 0
    parts = raw.split(b"\n") if raw else []
    if parts and raw.endswith(b"\n"):
        parts.pop()  # A terminator does not create a further empty record.
    if len(parts) > MAX_RECORDS:
        raise StrictJSONLError("JSONL record count exceeds the finite model")
    for index, part in enumerate(parts):
        has_lf = offset + len(part) < len(raw)
        ending = "lf" if has_lf else "none"
        physical = part + (b"\n" if has_lf else b"")
        record = part
        if has_lf and record.endswith(b"\r"):
            record = record[:-1]
            ending = "crlf"
        if len(physical) > MAX_LINE_BYTES:
            raise StrictJSONLError("physical JSONL line exceeds its byte bound")
        if b"\r" in record:
            raise StrictJSONLError("bare CR is outside the JSONL line grammar")
        if not record.strip(b" \t"):
            raise StrictJSONLError("blank physical JSONL records are rejected")
        _preflight(record)
        try:
            value = json.loads(record.decode("utf-8", errors="strict"),
                               parse_int=_integer, parse_float=_not_number,
                               parse_constant=_not_number, object_pairs_hook=_object)
        except (json.JSONDecodeError, UnicodeError, RecursionError) as exc:
            raise StrictJSONLError("record is not one strict complete JSON value") from exc
        row = _row(value, kind)
        if row["request_id"] in identifiers:
            raise StrictJSONLError("duplicate decoded request_id within the file")
        identifiers.add(row["request_id"])
        end = offset + len(physical)
        records.append({
            "record_index": index, "physical_line": index + 1,
            "line_span": {"start_byte": offset, "end_byte": end},
            "record_span": {"start_byte": offset, "end_byte": offset + len(record)},
            "line_ending": ending, "line_sha256": _sha(physical),
            "record_sha256": _sha(record), "row": row,
        })
        # Do not share mutable row objects between the two public projections.
        rows.append(json.loads(json.dumps(row, ensure_ascii=True)))
        offset = end
    return {"schema": SCHEMA, "kind": kind, "raw_bytes": len(raw),
            "raw_sha256": _sha(raw), "limits": dict(LIMITS),
            "records": records, "rows": rows, "claims": dict(FALSE_CLAIMS)}


def validate_jsonl_report(report, *, raw: bytes, kind: str) -> dict:
    """Replay a retained public report from the supplied complete byte input."""
    retained = _canonical(report)
    expected = parse_jsonl(raw, kind=kind)
    if retained != _canonical(expected):
        raise StrictJSONLError("retained JSONL report does not match its complete byte input")
    return expected
