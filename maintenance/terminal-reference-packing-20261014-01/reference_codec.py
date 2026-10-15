"""Experimental token-aware, lossless references over bounded ordinary JSON.

Only representation changes. All original containers, keys and scalar values
are restored exactly. Selection measures each complete codec envelope with the
preserved offline BPE; it does not predict provider usage or session savings.
"""
from __future__ import annotations

from collections import Counter
import hashlib
import json
import re

SCHEMA = "terminal-generic-json-reference-packet@1"
PROFILE = "experimental-lossless-json-string-references@1"
MAX_DECODED_BYTES = 256000
MAX_ENCODED_BYTES = 1024 * 1024
MAX_NODES = 100000
MAX_DEPTH = 64
MAX_INTEGER_BITS = 4096
MAX_TABLE_ENTRIES = 256
MAX_TABLE_BYTES = 65536
MAX_CANDIDATE_EVALUATIONS = 64
GUIDANCE = (
    "Lossless JSON display encoding. In body keys and string values only, $N refers to dictionary[N] "
    "with canonical zero-based decimal N. A string starting $$ is literal: remove exactly one leading $. "
    "Other strings and every container, Boolean, integer and null retain their values. Dictionary entries "
    "are original literal strings, never recursively decoded. Reject unknown references and duplicate "
    "decoded keys. Restore sorted compact UTF-8 JSON and verify decoded_bytes/decoded_sha256. "
    "This representation and its checksums confer no semantic, proof or execution authority."
)
CLAIMS = {"proof_authority": False, "execution_authority": False, "completion_authority": False,
    "omission_authority": False, "source_authentication_proved": False,
    "semantic_equivalence_proved": False, "provider_usage_measured": False,
    "provider_token_savings_measured": False}
FIELDS = {"schema", "profile", "guidance", "decoded_sha256", "decoded_bytes", "dictionary",
    "body", "claims", "packet_sha256"}
_DIAGNOSTICS = {}


class ReferenceCodecError(ValueError):
    """The exact JSON, reference table, bounded expansion or token check differs."""


def _need(ok, message):
    if not ok:
        raise ReferenceCodecError(message)


def _sha(raw):
    return hashlib.sha256(raw).hexdigest()


def _wire(value):
    try:
        return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False,
            allow_nan=False).encode("utf-8")
    except (TypeError, ValueError, UnicodeError, RecursionError) as error:
        raise ReferenceCodecError("canonical strict UTF-8 ordinary JSON required") from error


def _plain(value, *, maximum=MAX_DECODED_BYTES, depth_limit=MAX_DEPTH, node_limit=MAX_NODES):
    nodes, strings = 0, Counter()
    def visit(item, depth=0):
        nonlocal nodes
        nodes += 1
        _need(nodes <= node_limit and depth <= depth_limit, "JSON depth or node bound exceeded")
        if type(item) is dict:
            for key, child in item.items():
                _need(type(key) is str, "exact string JSON keys required")
                visit(key, depth + 1)
                visit(child, depth + 1)
        elif type(item) is list:
            for child in item: visit(child, depth + 1)
        elif type(item) is str:
            try:
                length = len(item.encode("utf-8"))
            except UnicodeError as error:
                raise ReferenceCodecError("strict UTF-8 scalar required") from error
            _need(length <= maximum, "individual JSON string exceeds byte bound")
            strings[item] += 1
        elif type(item) is int:
            _need(item.bit_length() <= MAX_INTEGER_BITS, "exact integer exceeds bounded numerical profile")
        else:
            _need(type(item) in {bool, type(None)}, "JSON profile excludes floats and nonordinary values")
    try:
        visit(value)
    except RecursionError as error:
        raise ReferenceCodecError("JSON recursion bound exceeded") from error
    raw = _wire(value)
    _need(len(raw) <= maximum, "canonical JSON byte bound exceeded")
    return raw, strings, nodes


def canonical_packet_bytes(packet):
    """The precise finite dictionary-packet identity used by both directions."""
    _need(type(packet) is dict, "ordinary dictionary packet required")
    return _plain(packet)[0]


def _table(entries):
    _need(type(entries) is list and len(entries) <= MAX_TABLE_ENTRIES
        and all(type(value) is str for value in entries), "bounded literal string reference table required")
    try:
        order = sorted(set(entries), key=lambda value: value.encode("utf-8"))
    except UnicodeError as error:
        raise ReferenceCodecError("reference table must be strict UTF-8") from error
    _need(order == entries, "reference table must be UTF-8 sorted and unique")
    _need(sum(len(value.encode("utf-8")) + 2 for value in entries) <= MAX_TABLE_BYTES,
        "reference table exceeds byte bound")
    _need(len(_wire(entries)) <= MAX_TABLE_BYTES, "serialized reference table exceeds byte bound")
    return entries


def _transform(packet, entries):
    lookup = {value: "$" + str(index) for index, value in enumerate(entries)}
    def text(value):
        if value in lookup:
            return lookup[value]
        return "$" + value if value.startswith("$") else value
    def visit(value):
        if type(value) is dict:
            result = {}
            for key, child in value.items():
                encoded = text(key)
                _need(encoded not in result, "reference key encoding collision")
                result[encoded] = visit(child)
            return result
        if type(value) is list: return [visit(child) for child in value]
        if type(value) is str: return text(value)
        return value
    return visit(packet)


def _envelope(packet, original, entries):
    _table(entries)
    body = {"schema": SCHEMA, "profile": PROFILE, "guidance": GUIDANCE,
        "decoded_sha256": _sha(original), "decoded_bytes": len(original),
        "dictionary": list(entries), "body": _transform(packet, entries), "claims": dict(CLAIMS)}
    body["packet_sha256"] = _sha(_wire(body))
    encoded = _wire(body)
    _need(len(encoded) <= MAX_ENCODED_BYTES, "reference envelope exceeds byte bound")
    return encoded.decode("utf-8")


def optimize_reference_packet(packet, tokenizer_descriptor=None):
    """Select only measured complete-envelope token decreases, within 64 trials.

    Candidate ordering uses a deterministic frequency/byte estimate. Every
    acceptance then counts the actual complete envelope including dictionary,
    decoder guidance and both checksums; this is not a global optimum claim.
    The root caller still compares complete final messages against expanded.
    """
    from token_cost_review import load_tokenizer
    original, frequencies, nodes = _plain(packet)
    _need(type(packet) is dict, "ordinary dictionary packet required")
    tokenizer, descriptor = load_tokenizer(tokenizer_descriptor)
    def count(text):
        result = tokenizer.encode(text)
        _need(type(result) is list and all(type(value) is int for value in result), "actual offline token list required")
        return len(result)
    baseline_text = original.decode("utf-8")
    original_tokens = count(baseline_text)
    best_entries = []
    best_text = _envelope(packet, original, best_entries)
    empty_table_tokens = best_tokens = count(best_text)
    candidates = [value for value, frequency in frequencies.items()
        if frequency >= 2 and value and len(_wire([value])) <= MAX_TABLE_BYTES]
    candidates.sort(key=lambda value: (-((len(value.encode("utf-8")) - 3) * (frequencies[value] - 1)), value.encode("utf-8")))
    trials = []
    for value in candidates[:MAX_CANDIDATE_EVALUATIONS]:
        proposal = sorted([*best_entries, value], key=lambda item: item.encode("utf-8"))
        try:
            proposed_text = _envelope(packet, original, proposal)
        except ReferenceCodecError as error:
            trials.append({"candidate_sha256": _sha(value.encode()), "frequency": frequencies[value],
                "selected": False, "status": "bounded_table_refusal", "reason": str(error)})
            continue
        proposed_tokens = count(proposed_text)
        selected = proposed_tokens < best_tokens
        trials.append({"candidate_sha256": _sha(value.encode()), "frequency": frequencies[value],
            "tokens_before": best_tokens, "tokens_proposed": proposed_tokens, "selected": selected,
            "status": "actual_complete_envelope_bpe_count"})
        if selected:
            best_entries, best_text, best_tokens = proposal, proposed_text, proposed_tokens
    _need(canonical_packet_bytes(decode_reference_packet(best_text, expected_packet_sha256=_sha(original))) == original,
        "exact original packet reconstruction differs")
    final_tokens = count(best_text)
    _need(final_tokens == best_tokens, "whole reference envelope token replay differs")
    diagnostics = {"schema": "terminal-json-reference-optimization-diagnostics@1",
        "codec_schema": SCHEMA, "profile": PROFILE, "original_sha256": _sha(original),
        "original_bytes": len(original), "original_tokens": original_tokens,
        "encoded_sha256": _sha(best_text.encode()), "encoded_bytes": len(best_text.encode()),
        "encoded_tokens": final_tokens, "empty_dictionary_envelope_tokens": empty_table_tokens,
        "strict_local_savings_vs_plain_packet": final_tokens < original_tokens,
        "selected_table_entries": len(best_entries), "candidate_population": len(candidates),
        "candidate_evaluations": len(trials), "candidate_evaluation_limit": MAX_CANDIDATE_EVALUATIONS,
        "candidate_selection": "one-pass bounded frequency-ranked greedy; each acceptance exact full-envelope BPE",
        "global_optimum_claimed": False, "input_nodes": nodes, "tokenizer": descriptor,
        "model_wire_contains_optimizer_trace": False, "trials": trials,
        "whole_final_message_comparison_required": True, **CLAIMS}
    _DIAGNOSTICS[_sha(best_text.encode())] = diagnostics
    while len(_DIAGNOSTICS) > 16:
        _DIAGNOSTICS.pop(next(iter(_DIAGNOSTICS)))
    return {"text": best_text, "diagnostics": json.loads(_wire(diagnostics))}


def encode_reference_packet(packet, tokenizer_descriptor=None):
    return optimize_reference_packet(packet, tokenizer_descriptor)["text"]


def optimization_diagnostics(text):
    """Detached bounded diagnostics for a packet encoded in this process."""
    _need(type(text) is str, "literal encoded packet required")
    digest = _sha(text.encode("utf-8"))
    _need(digest in _DIAGNOSTICS, "no optimization observation for this exact packet")
    return json.loads(_wire(_DIAGNOSTICS[digest]))


def _preflight(text):
    """Bound nesting and lexical nodes before the ordinary JSON parser hydrates."""
    inside, escaped, depth, nodes, scalar = False, False, 0, 0, False
    for character in text:
        if inside:
            if escaped: escaped = False
            elif character == "\\": escaped = True
            elif character == '"': inside = False
            continue
        if character == '"':
            inside, scalar = True, False
            nodes += 1
        elif character in "[{":
            depth += 1
            nodes += 1
            scalar = False
            _need(depth <= MAX_DEPTH + 4, "encoded JSON nesting exceeds bound before hydration")
        elif character in "]}":
            depth -= 1
            scalar = False
            _need(depth >= 0, "invalid JSON closing structure")
        elif character in ",: \t\r\n": scalar = False
        elif not scalar:
            nodes += 1
            scalar = True
        _need(nodes <= MAX_NODES + 1024, "encoded JSON lexical nodes exceed bound before hydration")
    _need(not inside and depth == 0, "unterminated encoded JSON structure")


def _parse(text):
    def unique(pairs):
        result = {}
        for key, value in pairs:
            _need(key not in result, "duplicate encoded JSON key")
            result[key] = value
        return result
    def integer(value):
        _need(len(value) <= 1235, "JSON integer text exceeds numerical bound")
        parsed = int(value)
        _need(parsed.bit_length() <= MAX_INTEGER_BITS, "JSON integer exceeds numerical bound")
        return parsed
    def excluded(value):
        raise ReferenceCodecError("JSON profile excludes floats and nonfinite constants")
    _preflight(text)
    try:
        value = json.loads(text, object_pairs_hook=unique, parse_int=integer,
            parse_float=excluded, parse_constant=excluded)
    except (TypeError, ValueError, RecursionError) as error:
        if isinstance(error, ReferenceCodecError): raise
        raise ReferenceCodecError("bounded canonical reference JSON required") from error
    _need(_wire(value).decode("utf-8") == text, "canonical compact reference JSON required")
    return value


class _Budget:
    def __init__(self, maximum):
        self.maximum, self.bytes, self.nodes = maximum, 0, 0

    def node(self, depth):
        self.nodes += 1
        _need(self.nodes <= MAX_NODES and depth <= MAX_DEPTH, "decoded structure exceeds bound before hydration")

    def charge(self, count):
        self.bytes += count
        _need(self.bytes <= self.maximum, "decoded byte budget exceeded before assembly")

    def text(self, value):
        _need(len(value) + 2 <= self.maximum - self.bytes, "decoded string exceeds remaining budget before assembly")
        self.charge(len(_wire(value)))


def _restore_tree(body, table, budget):
    references = Counter()
    def text(value, depth):
        budget.node(depth)
        if value.startswith("$$"):
            result = value[1:]
        elif value.startswith("$"):
            _need(re.fullmatch(r"\$(?:0|[1-9][0-9]*)", value), "unknown or noncanonical reserved reference syntax")
            _need(len(value) <= 4, "numeric reference index exceeds table bound")
            index = int(value[1:])
            _need(index < len(table), "unknown reference table index")
            references[index] += 1
            result = table[index]
        else:
            result = value
        budget.text(result)
        return result
    def visit(value, depth=0):
        if type(value) is str:
            return text(value, depth)
        budget.node(depth)
        if type(value) is dict:
            budget.charge(2)
            result = {}
            for number, (key, child) in enumerate(value.items()):
                decoded_key = text(key, depth + 1)
                _need(decoded_key not in result, "duplicate decoded dictionary key")
                budget.charge(1 + int(number > 0))
                result[decoded_key] = visit(child, depth + 1)
            return result
        if type(value) is list:
            budget.charge(2 + max(0, len(value) - 1))
            return [visit(child, depth + 1) for child in value]
        _need(type(value) in {bool, int, type(None)}, "unsupported scalar in encoded body")
        if type(value) is int:
            _need(value.bit_length() <= MAX_INTEGER_BITS, "decoded integer exceeds bound")
        budget.charge(len(_wire(value)))
        return value
    result = visit(body)
    _need(all(references[index] >= 2 for index in range(len(table))),
        "every dictionary entry must be referenced at least twice")
    return result, references


def decode_reference_packet(text, expected_packet_sha256=None):
    """Restore without tokenizer/training/optimization or executable inputs."""
    _need(type(text) is str, "literal reference packet text required")
    try:
        raw = text.encode("utf-8")
    except UnicodeError as error:
        raise ReferenceCodecError("strict UTF-8 reference text required") from error
    _need(0 < len(raw) <= MAX_ENCODED_BYTES, "encoded reference byte bound exceeded")
    value = _parse(text)
    _need(type(value) is dict and set(value) == FIELDS and value["schema"] == SCHEMA
        and value["profile"] == PROFILE and value["guidance"] == GUIDANCE,
        "closed reference codec envelope required")
    _need(type(value["claims"]) is dict and set(value["claims"]) == set(CLAIMS)
        and all(value["claims"][name] is False for name in CLAIMS), "reference codec cannot gain authority")
    claimed = value["packet_sha256"]
    _need(type(claimed) is str and re.fullmatch("[0-9a-f]{64}", claimed), "canonical codec checksum required")
    checksum_body = {key: child for key, child in value.items() if key != "packet_sha256"}
    _need(_sha(_wire(checksum_body)) == claimed, "codec packet checksum differs")
    decoded_hash = value["decoded_sha256"]
    _need(type(decoded_hash) is str and re.fullmatch("[0-9a-f]{64}", decoded_hash), "canonical decoded checksum required")
    if expected_packet_sha256 is not None:
        _need(type(expected_packet_sha256) is str and re.fullmatch("[0-9a-f]{64}", expected_packet_sha256)
            and decoded_hash == expected_packet_sha256, "caller expected packet checksum differs")
    count = value["decoded_bytes"]
    _need(type(count) is int and 2 <= count <= MAX_DECODED_BYTES, "bounded exact original byte count required")
    table = _table(value["dictionary"])
    _need(type(value["body"]) is dict, "preserved dictionary packet body required")
    budget = _Budget(count)
    decoded, _ = _restore_tree(value["body"], table, budget)
    original = canonical_packet_bytes(decoded)
    _need(len(original) == count == budget.bytes and _sha(original) == decoded_hash,
        "complete decoded canonical bytes or hash differs")
    # Structural canonicality is checked without rerunning greedy optimization.
    _need(_wire(_transform(decoded, table)) == _wire(value["body"]),
        "reference escape or table-use representation is noncanonical")
    return decoded
