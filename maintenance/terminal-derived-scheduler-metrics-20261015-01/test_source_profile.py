"""Pure source-inventory checks; public source is parsed, never imported."""
import ast
import base64
import copy
from fractions import Fraction
import hashlib
from pathlib import Path

import pytest

from source_profile import (
    DEFAULTS, DOMAIN, EXPECTED_AST_SHA256, EXPECTED_SOURCE_BYTES,
    EXPECTED_SOURCE_PATH, EXPECTED_SOURCE_SHA256, FALSE_CLAIMS, FUNCTION_AST_PINS,
    LITERALS, SCHEMA, SourceProfileError, build_source_profile,
    validate_source_profile, validate_source_profile_shape,
)


@pytest.fixture(scope="module")
def raw():
    # Exact selected public body from the immutable predecessor; no source import.
    path = (Path(__file__).resolve().parent.parent / "terminal-lean-jsonl-decoder-20261015-01"
            / "experiment-01/source-repository" / EXPECTED_SOURCE_PATH)
    result = path.read_bytes()
    assert len(result) == EXPECTED_SOURCE_BYTES
    assert hashlib.sha256(result).hexdigest() == EXPECTED_SOURCE_SHA256
    return result


@pytest.fixture(scope="module")
def head():
    # Authored identity fixture, deliberately not represented as a current owner.
    return {"schema": "codebase-head@1", "repository_id": "authored-profile-test-fixture",
            "snapshot_cid": "authored-snapshot", "manifest_cid": "authored-manifest",
            "receipt_cid": "authored-receipt", "ast_revision_id": "authored-revision",
            "generation": 1}


@pytest.fixture(scope="module")
def profile(raw, head):
    return build_source_profile(raw, source_path=EXPECTED_SOURCE_PATH, head=head)


def test_complete_public_body_and_ast_are_bound(raw, head, profile):
    assert profile["schema"] == SCHEMA
    assert profile["source_bytes"] == EXPECTED_SOURCE_BYTES
    assert profile["source_sha256"] == EXPECTED_SOURCE_SHA256
    assert profile["ast_sha256"] == EXPECTED_AST_SHA256
    assert base64.b64decode(profile["source_payload_b64"], validate=True) == raw
    assert validate_source_profile(profile, raw=raw, source_path=EXPECTED_SOURCE_PATH, head=head)
    assert validate_source_profile_shape(profile)


def test_exact_thirteen_defaults_and_two_numeric_interpretations(profile):
    assert len(profile["constants"]) == 13
    assert set(profile["constants"]) == set(LITERALS)
    assert profile["defaults"] == DEFAULTS
    assert profile["domain"] == DOMAIN
    for name, record in profile["constants"].items():
        assert record["literal"] == LITERALS[name]
        value = float(record["literal"].replace("_", ""))
        assert value.hex() == record["binary64_hex"]
        assert Fraction(*value.as_integer_ratio()) == Fraction(**record["binary64_ratio"])
    tp = profile["constants"]["Tp_attn"]
    assert tp["decimal_ratio"] == {"numerator": 1, "denominator": 500}
    assert tp["binary64_ratio"] != tp["decimal_ratio"]
    assert profile["constants"]["Td_mlp"]["binary64_ratio"]["denominator"] > 10**18


def test_all_method_bodies_and_nested_helpers_are_pinned(profile):
    assert len(profile["functions"]) == 13
    for name, digest in FUNCTION_AST_PINS.items():
        assert profile["functions"][name]["ast_sha256"] == digest
    assert {name for name in profile["functions"] if ".sum_" in name} == {
        "CostModel.batch_metrics.sum_cost_for_g", "CostModel.batch_metrics.sum_lat_for_g"}


def test_formula_control_and_call_citations_reference_exact_bytes(raw, profile):
    for family in ("formula_nodes", "control_nodes", "call_nodes"):
        assert profile[family]
        for row in profile[family]:
            span = row["source_span"]
            text = raw[span["start_byte"]:span["end_byte"]]
            assert text.decode("utf-8") == row["source_text"]
            assert hashlib.sha256(text).hexdigest() == row["source_sha256"]
    formulas = "\n".join(row["source_text"] for row in profile["formula_nodes"])
    assert "n*a + n*(n-1)/2" in formulas
    assert "n*(a*a) + a*n*(n-1) + (n*(n-1)*(2*n-1))//6" in formulas
    calls = "\n".join(row["callee_ast"] for row in profile["call_nodes"])
    assert "id='sum'" in calls and "id='set'" in calls
    assert "attr='ceil'" in calls


def test_operator_kinds_and_source_sensitive_decisions_are_explicit(profile):
    raw = base64.b64decode(profile["source_payload_b64"], validate=True)
    tree = ast.parse(raw.decode("utf-8"))
    ops = {type(node.op).__name__ for node in ast.walk(tree) if isinstance(node, ast.BinOp)}
    assert {"Div", "FloorDiv", "Pow", "Add", "Sub", "Mult"} <= ops
    decisions = profile["source_sensitive_decisions"]
    assert "not the declared" in decisions["batch_context"]
    assert "not aligned" in decisions["generation_context"]
    assert "including zero" in decisions["compile_latency"]
    assert "set" in decisions["compile_cost"]
    assert "host Python" in decisions["sum"]
    assert "explicit supported caller" in profile["interpretations"]["granularity"]


def test_scope_does_not_authorize_or_prove_runtime(profile):
    assert profile["claims"] == FALSE_CLAIMS
    assert all(value is False for value in profile["claims"].values())
    assert "not Python runtime equivalence" in profile["interpretations"]["decimal"]


@pytest.mark.parametrize("value", [None, "source", bytearray(b"source"), b"", b"x" * 8193])
def test_source_type_and_size_rejected_before_parse(value, head, monkeypatch):
    def forbidden(*args, **kwargs):
        raise AssertionError("AST hydration must not run for malformed source")
    monkeypatch.setattr(ast, "parse", forbidden)
    with pytest.raises(SourceProfileError):
        build_source_profile(value, head=head)


@pytest.mark.parametrize("old,new", [
    (b"self.c.Kd_attn, self.c.Kd_mlp * HIDDEN", b"self.c.Kd_attn, self.c.Kd_mlp + HIDDEN"),
    (b"A * sum_sq + B * sum_lin", b"A * sum_sq - B * sum_lin"),
    (b"if s <= 0:", b"if s >= 0:"),
    (b"b_list.sort()", b"b_list.copy()"),
    (b"0.0012", b"0.0013"),
    (b"HEADS: int = 32", b"HEADS: int = 33"),
    (b"0.95", b"0.96"),
])
def test_source_operator_control_or_constant_mutation_fails_whole_pin(raw, head, old, new, monkeypatch):
    changed = raw.replace(old, new)
    assert changed != raw and len(changed) == len(raw)
    def forbidden(*args, **kwargs):
        raise AssertionError("changed source must be refused before AST hydration")
    monkeypatch.setattr(ast, "parse", forbidden)
    with pytest.raises(SourceProfileError, match="whole source"):
        build_source_profile(changed, head=head)


@pytest.mark.parametrize("path", [None, 1, "cost_model.py", "/tmp/cost_model.py", "../" + EXPECTED_SOURCE_PATH])
def test_path_must_be_the_exact_selected_public_source(raw, head, path):
    with pytest.raises(SourceProfileError):
        build_source_profile(raw, source_path=path, head=head)


@pytest.mark.parametrize("head", [None, {}, [], {"schema": "codebase-head@1"}])
def test_incomplete_head_rejected(raw, head):
    with pytest.raises(SourceProfileError):
        build_source_profile(raw, head=head)


@pytest.mark.parametrize("field,value", [
    ("schema", "other-head@1"), ("generation", True), ("generation", 0),
    ("generation", 10**9 + 1), ("generation", 1.0), ("repository_id", None),
    ("receipt_cid", ""), ("manifest_cid", "x" * 1025), ("receipt_cid", "\ud800"),
])
def test_malformed_head_fields_are_rejected(raw, head, field, value):
    changed = {**head, field: value}
    with pytest.raises(SourceProfileError):
        build_source_profile(raw, head=changed)


def test_head_binding_rebuilt_from_external_head(raw, head, profile):
    with pytest.raises(SourceProfileError):
        validate_source_profile(profile, raw=raw, head={**head, "generation": 2})
    changed = copy.deepcopy(profile)
    changed["head"]["generation"] = 2
    with pytest.raises(SourceProfileError):
        validate_source_profile_shape(changed)


def _set_path(value, path, replacement):
    for key in path[:-1]:
        value = value[key]
    value[path[-1]] = replacement


@pytest.mark.parametrize("path,replacement", [
    (("schema",), "forged@1"), (("source_sha256",), "0" * 64),
    (("ast_sha256",), "0" * 64), (("source_bytes",), True),
    (("source_path",), "cost_model.py"), (("head_sha256",), "0" * 64),
    (("defaults", "granularity"), 32), (("defaults", "HEADS"), 33),
    (("domain", "max_prompt_len"), 8192), (("domain", "max_gen_len"), 2048),
    (("domain", "max_seq_align"), 16384), (("domain", "max_rows_per_bucket"), 257),
    (("constants", "Tp_attn", "decimal_ratio", "numerator"), 2),
    (("constants", "Tp_attn", "binary64_ratio", "denominator"), 500),
    (("constants", "Tp_attn", "literal"), "0.003"),
    (("constants", "Tp_attn", "binary64_hex"), "0x1.0p+0"),
    (("functions", "align", "ast_sha256"), "0" * 64),
    (("functions", "align", "source_span", "start_byte"), 0),
    (("formula_nodes", 0, "source_text"), "forged formula"),
    (("control_nodes", 0, "control_ast"), "forged control flow"),
    (("call_nodes", 0, "callee_ast"), "forged call"),
    (("claims", "source_body_execution"), True),
    (("claims", "ast_to_runtime_equivalence_proved"), True),
    (("claims", "planning_or_dispatch_authority"), 0),
])
def test_every_bound_projection_rejects_tampering(profile, path, replacement):
    changed = copy.deepcopy(profile)
    _set_path(changed, path, replacement)
    with pytest.raises(SourceProfileError):
        validate_source_profile_shape(changed)


@pytest.mark.parametrize("mutation", ["drop_constant", "extra_constant", "drop_function", "drop_formula", "reorder_calls", "extra_field"])
def test_inventories_and_top_level_schema_are_closed(profile, mutation):
    changed = copy.deepcopy(profile)
    if mutation == "drop_constant":
        changed["constants"].pop("Kp_attn")
    elif mutation == "extra_constant":
        changed["constants"]["custom"] = copy.deepcopy(changed["constants"]["Kp_attn"])
    elif mutation == "drop_function":
        changed["functions"].pop("align")
    elif mutation == "drop_formula":
        changed["formula_nodes"].pop()
    elif mutation == "reorder_calls":
        changed["call_nodes"].reverse()
    else:
        changed["unreviewed_authority"] = True
    with pytest.raises(SourceProfileError):
        validate_source_profile_shape(changed)


@pytest.mark.parametrize("payload", [None, "!", "eA==", "A" * 11001])
def test_retained_source_payload_is_closed(profile, payload):
    changed = copy.deepcopy(profile)
    changed["source_payload_b64"] = payload
    with pytest.raises(SourceProfileError):
        validate_source_profile_shape(changed)


@pytest.mark.parametrize("value", [None, [], {}, {"source_payload_b64": "x", "bad": float("nan")}, {"bad": object()}])
def test_non_plain_or_absent_report_rejected(value):
    with pytest.raises(SourceProfileError):
        validate_source_profile_shape(value)


def test_report_validation_rejects_cyclic_data(profile):
    changed = copy.deepcopy(profile)
    changed["cycle"] = changed
    with pytest.raises(SourceProfileError):
        validate_source_profile_shape(changed)


def test_caller_mutation_does_not_retroactively_change_profile(raw, head):
    supplied = copy.deepcopy(head)
    report = build_source_profile(raw, head=supplied)
    supplied["repository_id"] = "mutated"
    assert report["head"] == head
    report["defaults"]["granularity"] = 32
    report["domain"]["max_prompt_len"] = 1
    assert DEFAULTS["granularity"] == 64
    assert DOMAIN["max_prompt_len"] == 4096
