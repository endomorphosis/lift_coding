"""Exact ordinary JSON reference restoration and real complete-envelope costs."""
import copy
import hashlib
import json

import pytest

import reference_codec as subject


def make(packet, entries=()):
    return subject._envelope(packet, subject.canonical_packet_bytes(packet), list(entries))


def resign(value):
    value = copy.deepcopy(value)
    value.pop("packet_sha256", None)
    value["packet_sha256"] = hashlib.sha256(subject._wire(value)).hexdigest()
    return subject._wire(value).decode()


def decode(text, original=None):
    expected = None if original is None else hashlib.sha256(subject.canonical_packet_bytes(original)).hexdigest()
    return subject.decode_reference_packet(text, expected_packet_sha256=expected)


@pytest.mark.parametrize("original", [{}, {"data": [True, False, 0, 1, None, -9, 2**256]},
    {"$0": "$0", "$$0": "$$0", "$01": "$01", "$ref": "$ref", "$": "$", "normal": ""},
    {"雪": ["é", "e\u0301", "<|endoftext|>", "\\\n\t\u0000", {"key": "value"}]},
    {"nested": [{"nested": [{"nested": "leaf"}]}]}])
def test_empty_table_lossless_types_unicode_and_reserved_prefix(original):
    text = make(original)
    restored = decode(text, original)
    assert subject.canonical_packet_bytes(restored) == subject.canonical_packet_bytes(original)
    assert type(restored) is dict
    if "data" in original:
        assert [type(v) for v in restored["data"]] == [bool, bool, int, int, type(None), int, int]


def test_table_literal_values_are_never_recursively_decoded():
    original = {"payload": ["$0", "$0", "$$0", "$$0"]}
    entries = sorted(["$0", "$$0"], key=lambda value: value.encode())
    text = make(original, entries)
    assert decode(text, original) == original
    assert json.loads(text)["body"]["payload"] == ["$1", "$1", "$0", "$0"]


def test_repeated_keys_and_values_share_exact_table_without_key_collisions():
    original = {"rows": [{"identifier": "identifier", "$0": "$0"} for _ in range(3)]}
    text = make(original, ["$0", "identifier"])
    assert decode(text, original) == original
    assert json.loads(text)["body"]["rows"][0] == {"$0": "$0", "$1": "$1"}


def test_table_sorted_by_utf8_and_not_unicode_normalized():
    original = {"values": ["é", "é", "e\u0301", "e\u0301", "雪", "雪"]}
    entries = sorted(["雪", "é", "e\u0301"], key=lambda value: value.encode())
    assert decode(make(original, entries), original) == original
    with pytest.raises(subject.ReferenceCodecError, match="sorted and unique"):
        make(original, list(reversed(entries)))


@pytest.mark.parametrize("value", [1.0, float("nan"), float("inf"), b"binary", (1, 2), {1, 2}])
def test_nonordinary_scalar_and_container_types_refused(value):
    with pytest.raises(subject.ReferenceCodecError):
        subject.canonical_packet_bytes({"value": value})


@pytest.mark.parametrize("key", [True, False, 1, None, b"key"])
def test_non_string_keys_refused(key):
    with pytest.raises(subject.ReferenceCodecError, match="exact string"):
        subject.canonical_packet_bytes({key: 1})


def test_numerical_bound_and_bool_integer_identity():
    original = {"truth": True, "one": 1, "false": False, "zero": 0, "large": -(2**4095)}
    assert subject.canonical_packet_bytes(decode(make(original))) == subject.canonical_packet_bytes(original)
    with pytest.raises(subject.ReferenceCodecError, match="numerical profile"):
        subject.canonical_packet_bytes({"too_large": 2**4096})


def test_literal_dollar_spellings_are_all_escaped_before_reference_parser():
    original = {"values": ["$0", "$01", "$-1", "$256", "$A", "$$", "$$$0"]}
    encoded = json.loads(make(original))["body"]["values"]
    assert encoded == ["$$0", "$$01", "$$-1", "$$256", "$$A", "$$$", "$$$$0"]
    assert decode(make(original)) == original


@pytest.mark.parametrize("reference", ["$0", "$1", "$01", "$-1", "$256", "$000", "$A", "$", "$1 "])
def test_unknown_and_noncanonical_references_refused(reference):
    value = json.loads(make({"key": "value"}))
    value["body"]["key"] = reference
    with pytest.raises(subject.ReferenceCodecError, match="reference"):
        decode(resign(value))


def test_collision_after_dictionary_key_expansion_rejected():
    value = json.loads(make({"same_key": None}))
    value["dictionary"] = ["same_key"]
    value["body"] = {"$0": None, "same_key": True}
    value["decoded_bytes"] = 1000
    with pytest.raises(subject.ReferenceCodecError, match="duplicate decoded"):
        decode(resign(value))


@pytest.mark.parametrize("table", [["duplicate", "duplicate"], ["z", "a"], [3], ["x" * 65536],
    [f"value-{index:03d}" for index in range(257)]])
def test_dictionary_order_type_count_and_bytes_refused(table):
    value = json.loads(make({"key": "value"}))
    value["dictionary"] = table
    with pytest.raises(subject.ReferenceCodecError): decode(resign(value))


@pytest.mark.parametrize("occurrences", [0, 1])
def test_unused_and_once_used_table_entries_refused(occurrences):
    value = json.loads(make({"key": "value"}))
    value["dictionary"] = ["long_identifier"]
    value["body"] = {"key": ["$0"] * occurrences}
    value["decoded_bytes"] = 1000
    with pytest.raises(subject.ReferenceCodecError, match="at least twice"):
        decode(resign(value))


def test_literal_reference_value_cannot_bypass_canonical_table_use():
    original = {"key": ["long_identifier", "long_identifier", "long_identifier"]}
    value = json.loads(make(original, ["long_identifier"]))
    value["body"]["key"][0] = "long_identifier"
    with pytest.raises(subject.ReferenceCodecError, match="noncanonical"):
        decode(resign(value))


def test_duplicate_encoded_json_keys_refused_before_checksum():
    text = make({"key": "value"})
    changed = text.replace('{"body":', '{"schema":"duplicate","body":', 1)
    with pytest.raises(subject.ReferenceCodecError, match="duplicate encoded"):
        decode(changed)


def test_noncanonical_spacing_unicode_escaping_and_float_json_refused():
    value = json.loads(make({"雪": "value", "number": 1}))
    with pytest.raises(subject.ReferenceCodecError, match="canonical compact"):
        decode(json.dumps(value, indent=2))
    with pytest.raises(subject.ReferenceCodecError, match="canonical compact"):
        decode(json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True))
    text = subject._wire(value).decode().replace('"number":1', '"number":1.0')
    with pytest.raises(subject.ReferenceCodecError, match="excludes floats"):
        decode(text)


def test_checksum_caller_binding_and_original_length_are_required():
    original = {"key": "value"}
    text = make(original)
    with pytest.raises(subject.ReferenceCodecError, match="caller expected"):
        subject.decode_reference_packet(text, expected_packet_sha256="0" * 64)
    value = json.loads(text);value["body"]["key"] = "changed"
    with pytest.raises(subject.ReferenceCodecError, match="codec packet checksum"):
        decode(subject._wire(value).decode())
    with pytest.raises(subject.ReferenceCodecError): decode(resign(value))
    value = json.loads(text);value["decoded_bytes"] += 1
    with pytest.raises(subject.ReferenceCodecError, match="canonical bytes"):
        decode(resign(value))


@pytest.mark.parametrize("field", list(subject.CLAIMS))
@pytest.mark.parametrize("replacement", [True, 0])
def test_promoted_or_non_boolean_claims_refused(field, replacement):
    value = json.loads(make({"key": "value"}));value["claims"][field] = replacement
    with pytest.raises(subject.ReferenceCodecError, match="gain authority"):
        decode(resign(value))


def test_closed_schema_and_original_packet_type_required():
    value = json.loads(make({"key": "value"}));value["extra"] = "not allowed"
    with pytest.raises(subject.ReferenceCodecError, match="closed reference"):
        decode(resign(value))
    value = json.loads(make({"key": "value"}));value["body"] = ["value"]
    with pytest.raises(subject.ReferenceCodecError, match="dictionary packet body"):
        decode(resign(value))
    with pytest.raises(subject.ReferenceCodecError, match="dictionary packet"):
        subject.canonical_packet_bytes(["value"])


def test_expansion_budget_refused_before_long_reference_assembly():
    value = json.loads(make({"key": "value"}))
    value["dictionary"] = ["x" * 60000]
    value["body"] = {"key": ["$0", "$0"]}
    value["decoded_bytes"] = 100
    with pytest.raises(subject.ReferenceCodecError, match="before assembly"):
        decode(resign(value))


def test_encoded_nesting_preflight_refuses_before_json_hydration():
    text = make({"key": 0})
    text = text.replace('"body":{"key":0}', '"body":{"key":' + '[' * 1000 + '0' + ']' * 1000 + '}')
    with pytest.raises(subject.ReferenceCodecError, match="before hydration"):
        decode(text)


def test_decoded_depth_and_cycle_bounds():
    value = 1
    for _ in range(subject.MAX_DEPTH + 1): value = [value]
    with pytest.raises(subject.ReferenceCodecError, match="depth or node"):
        subject.canonical_packet_bytes({"key": value})
    value = {};value["cycle"] = value
    with pytest.raises(subject.ReferenceCodecError, match="depth or node"):
        subject.canonical_packet_bytes(value)


def test_structural_node_bound_and_utf8_byte_bounds():
    with pytest.raises(subject.ReferenceCodecError, match="node bound"):
        subject.canonical_packet_bytes({"values": [None] * subject.MAX_NODES})
    with pytest.raises(subject.ReferenceCodecError, match="byte bound"):
        subject.canonical_packet_bytes({"value": "x" * (subject.MAX_DECODED_BYTES + 1)})
    with pytest.raises(subject.ReferenceCodecError, match="encoded reference byte"):
        decode(" " * (subject.MAX_ENCODED_BYTES + 1))
    with pytest.raises(subject.ReferenceCodecError, match="UTF-8"):
        subject.canonical_packet_bytes({"value": "\ud800"})


def test_actual_bpe_greedy_packing_preserves_repeated_long_cids_and_paths():
    cid = "bafyreid" + "abcdef0123456789" * 4
    path = "public-task/environment/subdirectory/repeated_source_module.py"
    original = {"records": [{"source_cid": cid, "source_path": path, "required": True,
        "source_sha256": "1a2b3c4d" * 8} for _ in range(40)]}
    result = subject.optimize_reference_packet(original)
    assert decode(result["text"], original) == original
    envelope = json.loads(result["text"])
    diagnostics = result["diagnostics"]
    assert len(envelope["dictionary"]) > 0
    assert diagnostics["strict_local_savings_vs_plain_packet"] is True
    assert diagnostics["encoded_tokens"] < diagnostics["original_tokens"]
    assert diagnostics["encoded_tokens"] <= diagnostics["empty_dictionary_envelope_tokens"]
    assert diagnostics["candidate_evaluations"] <= 64
    assert diagnostics["global_optimum_claimed"] is False
    assert "trials" not in envelope and envelope["guidance"] == subject.GUIDANCE
    assert subject.optimization_diagnostics(result["text"]) == diagnostics
    from token_cost_review import load_tokenizer
    tokenizer, _ = load_tokenizer(diagnostics["tokenizer"])
    assert len(tokenizer.encode(result["text"])) == diagnostics["encoded_tokens"]
    assert len(tokenizer.encode(subject.canonical_packet_bytes(original).decode())) == diagnostics["original_tokens"]


def test_short_packet_keeps_complete_overhead_and_root_can_choose_expanded():
    original = {"id": "CID", "ok": True}
    result = subject.optimize_reference_packet(original)
    assert decode(result["text"], original) == original
    assert result["diagnostics"]["strict_local_savings_vs_plain_packet"] is False
    assert result["diagnostics"]["encoded_tokens"] > result["diagnostics"]["original_tokens"]
    assert result["diagnostics"]["whole_final_message_comparison_required"] is True


def test_encoder_interface_and_detached_diagnostics_are_reproducible():
    original = {"rows": [{"long_identifier": "constant-long-source-identifier"} for _ in range(15)]}
    first = subject.optimize_reference_packet(original)
    assert subject.encode_reference_packet(original, first["diagnostics"]["tokenizer"]) == first["text"]
    retrieved = subject.optimization_diagnostics(first["text"])
    retrieved["encoded_tokens"] = -1
    assert subject.optimization_diagnostics(first["text"])["encoded_tokens"] >= 0


def test_mismatched_tokenizer_descriptor_refused_without_network():
    from token_cost_review import load_tokenizer, TokenCostError
    _, descriptor = load_tokenizer()
    descriptor["encoding"] = "other"
    with pytest.raises(TokenCostError, match="descriptor differs"):
        subject.encode_reference_packet({"key": "value"}, descriptor)


def test_decode_does_not_load_tokenizer_or_optimize(monkeypatch):
    import token_cost_review
    text = make({"$0": [True, 1, "literal"]})
    monkeypatch.setattr(token_cost_review, "load_tokenizer", lambda *_: pytest.fail("decoder loaded tokenizer"))
    monkeypatch.setattr(subject, "optimize_reference_packet", lambda *_: pytest.fail("decoder optimized"))
    assert decode(text) == {"$0": [True, 1, "literal"]}
