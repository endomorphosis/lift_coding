import copy
import hashlib
import json

import pytest

import strict_jsonl as module
from strict_jsonl import (MAX_BYTES, MAX_DEPTH, MAX_IDENTIFIER_BYTES, MAX_INTEGER,
                          MAX_LINE_BYTES, MAX_RECORDS, StrictJSONLError,
                          parse_jsonl, validate_jsonl_report)


def request(request_id="r", prompt_len=65, gen_len=2):
    return {"request_id": request_id, "prompt_len": prompt_len, "gen_len": gen_len}


def plan(request_id="r", batch_id="b", seq=128):
    return {"request_id": request_id, "batch_id": batch_id,
            "shape": {"seq_align": seq, "heads_align": 32, "hidden_align": 4096}}


def encoded(row, *, ascii=False):
    return json.dumps(row, ensure_ascii=ascii, separators=(",", ":")).encode("utf-8")


@pytest.mark.parametrize("kind,row", [("requests", request()), ("plan", plan())])
@pytest.mark.parametrize("terminator", [b"", b"\n", b"\r\n"])
def test_exact_row_and_half_open_byte_citations(kind, row, terminator):
    record = b" \t" + encoded(row) + b"\t "
    raw = record + terminator
    report = parse_jsonl(raw, kind=kind)
    assert report["rows"] == [row]
    assert report["raw_bytes"] == len(raw)
    assert report["raw_sha256"] == hashlib.sha256(raw).hexdigest()
    item = report["records"][0]
    assert item["record_index"] == 0 and item["physical_line"] == 1
    assert item["line_span"] == {"start_byte": 0, "end_byte": len(raw)}
    assert item["record_span"] == {"start_byte": 0, "end_byte": len(record)}
    assert item["line_ending"] == {b"": "none", b"\n": "lf", b"\r\n": "crlf"}[terminator]
    assert item["line_sha256"] == hashlib.sha256(raw).hexdigest()
    assert item["record_sha256"] == hashlib.sha256(record).hexdigest()
    assert item["row"] == row
    assert not any(report["claims"].values())
    assert validate_jsonl_report(report, raw=raw, kind=kind) == report


def test_mixed_line_endings_and_unicode_spans_are_bytes_not_characters():
    row1, row2, row3 = request("é🐍"), request("other"), request("final")
    first, second, third = encoded(row1) + b"\r\n", encoded(row2) + b"\n", encoded(row3)
    raw = first + second + third
    report = parse_jsonl(raw, kind="requests")
    assert report["rows"] == [row1, row2, row3]
    for item, start, part in zip(report["records"], [0, len(first), len(first + second)],
                                 [first, second, third]):
        assert item["line_span"] == {"start_byte": start, "end_byte": start + len(part)}
        assert raw[item["line_span"]["start_byte"]:item["line_span"]["end_byte"]] == part
    assert len(first) > len(first.decode("utf-8"))
    assert [r["line_ending"] for r in report["records"]] == ["crlf", "lf", "none"]


@pytest.mark.parametrize("kind", ["requests", "plan"])
def test_empty_files_explicitly_project_to_zero_rows(kind):
    report = parse_jsonl(b"", kind=kind)
    assert report["rows"] == [] and report["records"] == []
    assert report["raw_bytes"] == 0
    validate_jsonl_report(report, raw=b"", kind=kind)


def test_decoded_row_projections_do_not_alias_mutable_dicts():
    report = parse_jsonl(encoded(plan()), kind="plan")
    report["rows"][0]["shape"]["seq_align"] = 900
    assert report["records"][0]["row"]["shape"]["seq_align"] == 128


@pytest.mark.parametrize("raw", [b"\n", b"\r\n", b" \t", b" \t\n",
                                  encoded(request()) + b"\n\n",
                                  b"\n" + encoded(request()),
                                  encoded(request()) + b"\n \t\n"])
def test_blank_physical_records_reject(raw):
    with pytest.raises(StrictJSONLError):
        parse_jsonl(raw, kind="requests")


@pytest.mark.parametrize("raw", [b"\xef\xbb\xbf" + encoded(request()),
                                  encoded(request()) + b"\n\xef\xbb\xbf" + encoded(request("s")),
                                  b"\xff", b"\xc0\xaf", b"\xed\xa0\x80",
                                  encoded(request()) + b"\x00",
                                  encoded(request()) + b"\r",
                                  encoded(request()).replace(b'"r"', b'"r\r"'),
                                  encoded(request()).replace(b'"r"', b'"r\n"')])
def test_invalid_utf8_bom_nul_and_physical_control_characters_reject(raw):
    with pytest.raises(StrictJSONLError):
        parse_jsonl(raw, kind="requests")


@pytest.mark.parametrize("identifier", ["\x00", "r\x00s", "\ud800", "\udfff"])
def test_escaped_nul_and_unpaired_surrogate_identifiers_reject(identifier):
    with pytest.raises(StrictJSONLError):
        parse_jsonl(encoded(request(identifier), ascii=True), kind="requests")


def test_valid_surrogate_pair_decodes_without_unicode_normalization():
    escaped = encoded(request("🐍"), ascii=True)
    literal = encoded(request("🐍"))
    assert parse_jsonl(escaped, kind="requests")["rows"] == parse_jsonl(literal, kind="requests")["rows"]
    composed, decomposed = request("é"), request("e\u0301")
    assert parse_jsonl(encoded(composed) + b"\n" + encoded(decomposed), kind="requests")["rows"] == [composed, decomposed]


@pytest.mark.parametrize("raw,kind", [
    (b'{"request_id":"r","request_id":"s","prompt_len":1,"gen_len":2}', "requests"),
    (b'{"request_id":"r","\\u0072equest_id":"r","prompt_len":1,"gen_len":2}', "requests"),
    (b'{"request_id":"r","batch_id":"b","shape":{"seq_align":64,"heads_align":32,"hidden_align":4096,"\\u0073eq_align":128}}', "plan"),
])
def test_duplicate_decoded_object_keys_reject_even_when_values_agree(raw, kind):
    with pytest.raises(StrictJSONLError, match="duplicate decoded JSON object key"):
        parse_jsonl(raw, kind=kind)


@pytest.mark.parametrize("kind,row", [("requests", request("é")), ("plan", plan("é"))])
def test_duplicate_decoded_request_id_rejects_across_escaped_representation(kind, row):
    raw = encoded(row) + b"\n" + encoded(row, ascii=True)
    with pytest.raises(StrictJSONLError, match="duplicate decoded request_id"):
        parse_jsonl(raw, kind=kind)


def test_empty_id_is_explicitly_within_existing_finite_model():
    assert parse_jsonl(encoded(request("")), kind="requests")["rows"] == [request("")]
    assert parse_jsonl(encoded(plan("", "")), kind="plan")["rows"] == [plan("", "")]


@pytest.mark.parametrize("lexeme", [b"-0", b"-1", b"1.0", b"0.0", b"1e0", b"1E+0",
                                      b"NaN", b"Infinity", b"-Infinity", b"true", b"false", b"null",
                                      b"01", b"+1", b"0x10", b"1000000000000000001", b"9" * 4096])
def test_non_natural_or_non_integer_number_lexemes_reject(lexeme):
    raw = b'{"request_id":"r","prompt_len":' + lexeme + b',"gen_len":0}'
    with pytest.raises(StrictJSONLError):
        parse_jsonl(raw, kind="requests")


def test_integer_model_boundaries_remain_exact():
    row = request("r", MAX_INTEGER, 0)
    assert parse_jsonl(encoded(row), kind="requests")["rows"] == [row]
    row = plan(seq=MAX_INTEGER)
    assert parse_jsonl(encoded(row), kind="plan")["rows"] == [row]


@pytest.mark.parametrize("row,kind", [
    ({"request_id": "r", "prompt_len": 1}, "requests"),
    ({**request(), "extra": 1}, "requests"),
    ({**request(), "request_id": 4}, "requests"),
    ({**request(), "request_id": False}, "requests"),
    ({**request(), "request_id": []}, "requests"),
    ({**plan(), "batch_id": 7}, "plan"),
    ({**plan(), "shape": [128, 32, 4096]}, "plan"),
    ({**plan(), "shape": {"seq_align": 128, "heads_align": 32}}, "plan"),
    ({**plan(), "shape": {**plan()["shape"], "extra": 0}}, "plan"),
    ({**plan(), "shape": {**plan()["shape"], "heads_align": True}}, "plan"),
    ([], "requests"), ([request()], "requests"), (None, "requests"), ("r", "requests"),
])
def test_closed_row_schema_and_exact_types_reject(row, kind):
    with pytest.raises(StrictJSONLError):
        parse_jsonl(encoded(row), kind=kind)


@pytest.mark.parametrize("suffix", [b" {}", b" []", b" 0", b" garbage", b"\v", b"\f"])
def test_trailing_non_json_whitespace_or_second_value_reject(suffix):
    with pytest.raises(StrictJSONLError):
        parse_jsonl(encoded(request()) + suffix, kind="requests")


def test_identifier_bound_uses_utf8_bytes():
    identifier = "é" * (MAX_IDENTIFIER_BYTES // 2)
    row = request(identifier)
    assert parse_jsonl(encoded(row), kind="requests")["rows"] == [row]
    with pytest.raises(StrictJSONLError):
        parse_jsonl(encoded(request(identifier + "x")), kind="requests")
    with pytest.raises(StrictJSONLError):
        parse_jsonl(encoded(plan(batch_id=identifier + "x")), kind="plan")


def test_record_count_bound_and_order_are_exact():
    rows = [request(str(index)) for index in range(MAX_RECORDS)]
    raw = b"\n".join(encoded(row) for row in rows)
    assert parse_jsonl(raw, kind="requests")["rows"] == rows
    with pytest.raises(StrictJSONLError):
        parse_jsonl(raw + b"\n" + encoded(request("overflow")), kind="requests")


def test_physical_line_bound_includes_terminator():
    body = encoded(request())
    raw = body + b" " * (MAX_LINE_BYTES - len(body) - 2) + b"\r\n"
    assert parse_jsonl(raw, kind="requests")["raw_bytes"] == MAX_LINE_BYTES
    with pytest.raises(StrictJSONLError):
        parse_jsonl(raw + b" ", kind="requests")
    with pytest.raises(StrictJSONLError):
        parse_jsonl(raw[:-2] + b" \r\n", kind="requests")


def test_complete_file_byte_bound_at_exact_boundary():
    lines = []
    for index in range(MAX_BYTES // MAX_LINE_BYTES):
        body = encoded(request(str(index)))
        lines.append(body + b" " * (MAX_LINE_BYTES - len(body) - 1) + b"\n")
    raw = b"".join(lines)
    assert len(raw) == MAX_BYTES
    assert len(parse_jsonl(raw, kind="requests")["rows"]) == len(lines)
    with pytest.raises(StrictJSONLError):
        parse_jsonl(raw + b" ", kind="requests")


def test_container_depth_is_checked_before_json_hydration(monkeypatch):
    called = []

    def forbidden_load(*args, **kwargs):
        called.append(True)
        raise AssertionError("deep bytes reached the JSON decoder")

    monkeypatch.setattr(module.json, "loads", forbidden_load)
    with pytest.raises(StrictJSONLError, match="preflight"):
        parse_jsonl(b"[" * (MAX_DEPTH + 1) + b"0" + b"]" * (MAX_DEPTH + 1), kind="requests")
    assert called == []


def test_nesting_and_quote_characters_inside_id_do_not_count_as_containers():
    row = request('[' * 30 + '{"quoted": "escaped\\"}' + ']' * 30)
    assert parse_jsonl(encoded(row), kind="requests")["rows"] == [row]


@pytest.mark.parametrize("raw", [b"{", b'"unterminated', b"{]", b"]", b"[}", b'{"a": [1}'])
def test_unbalanced_or_unfinished_preflight_rejects(raw):
    with pytest.raises(StrictJSONLError):
        parse_jsonl(raw, kind="requests")


def test_parser_refuses_non_plain_input_and_kind_values():
    class BytesChild(bytes):
        pass

    class StrChild(str):
        pass

    for raw in ("", bytearray(), memoryview(b""), BytesChild(b""), None):
        with pytest.raises(StrictJSONLError):
            parse_jsonl(raw, kind="requests")
    for kind in (None, "request", "plans", StrChild("requests"), [], 0):
        with pytest.raises(StrictJSONLError):
            parse_jsonl(b"", kind=kind)


@pytest.mark.parametrize("change", ["row", "cited_row", "span", "digest", "kind", "claim", "limit", "unknown"])
def test_replay_rejects_changed_public_projection(change):
    raw = encoded(request()) + b"\r\n"
    report = copy.deepcopy(parse_jsonl(raw, kind="requests"))
    if change == "row":
        report["rows"][0]["prompt_len"] += 1
    elif change == "cited_row":
        report["records"][0]["row"]["request_id"] = "other"
    elif change == "span":
        report["records"][0]["record_span"]["end_byte"] += 1
    elif change == "digest":
        report["raw_sha256"] = "0" * 64
    elif change == "kind":
        report["kind"] = "plan"
    elif change == "claim":
        report["claims"]["formal_proof"] = True
    elif change == "limit":
        report["limits"]["max_records"] += 1
    else:
        report["unknown"] = False
    with pytest.raises(StrictJSONLError):
        validate_jsonl_report(report, raw=raw, kind="requests")


def test_replay_binds_lexical_bytes_even_for_equal_decoded_rows():
    original = encoded(request("é"))
    same_rows = encoded(request("é"), ascii=True) + b"\n"
    report = parse_jsonl(original, kind="requests")
    assert parse_jsonl(same_rows, kind="requests")["rows"] == report["rows"]
    with pytest.raises(StrictJSONLError):
        validate_jsonl_report(report, raw=same_rows, kind="requests")


@pytest.mark.parametrize("value", [float("nan"), 1.0, (), b"", {1: "key"}])
def test_replay_rejects_non_plain_json_before_comparison(value):
    report = parse_jsonl(b"", kind="requests")
    report["extra"] = value
    with pytest.raises(StrictJSONLError):
        validate_jsonl_report(report, raw=b"", kind="requests")


def test_replay_rejects_container_and_integer_subclasses():
    class DictChild(dict):
        pass

    class IntChild(int):
        pass

    raw = encoded(request())
    report = parse_jsonl(raw, kind="requests")
    with pytest.raises(StrictJSONLError):
        validate_jsonl_report(DictChild(report), raw=raw, kind="requests")
    report["raw_bytes"] = IntChild(report["raw_bytes"])
    with pytest.raises(StrictJSONLError):
        validate_jsonl_report(report, raw=raw, kind="requests")
