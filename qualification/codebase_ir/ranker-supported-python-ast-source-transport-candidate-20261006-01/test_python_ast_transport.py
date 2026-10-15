"""Twenty host-control groups; root alone may execute these tests.

Expected constructors below are hand-written independent syntax observations.
No test claims numerical/error semantics, parser correctness or Lean admission.
"""
import copy
import importlib.util
import json
import os
from pathlib import Path

import pytest


@pytest.fixture(scope="module")
def impl():
    path = Path(os.environ["RANKER_PY_AST_TRANSPORT"])
    spec = importlib.util.spec_from_file_location("reviewed_python_ast_transport", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.fixture(scope="module")
def buffers():
    return tuple(Path(os.environ[name]).read_bytes() for name in
                 ("RANKER_AST_SOURCE", "RANKER_PREFIX_BINDINGS", "RANKER_PREFIX_DRAFT"))


@pytest.fixture(scope="module")
def receipt(impl, buffers):
    return impl.transport_prefix(*buffers)


def context(**names):
    return {name: {"scope": 1, "kind": kind, "dimensions": {"scalar": [], "integer": [], "vector": [3], "matrix": [2, 3]}[kind],
                   "immutable": True} for name, kind in names.items()}


def name(scope, spelling):
    return {"tag": "name", "name": {"tag": "PyName", "scope": scope, "spelling": spelling}}


def integer(value, token=None):
    return {"tag": "integer", "value": str(value), "token": str(value) if token is None else token}


def callee(spelling):
    return {"tag": "name", "identifier": {"tag": "PyName", "scope": 0, "spelling": spelling}}


def attr(member):
    return {"tag": "attribute", "base": {"tag": "PyName", "scope": 0, "spelling": "math"}, "member": member}


def binary(operator, left, right):
    return {"tag": "binary", "operator": operator, "left": left, "right": right}


def call(reference, *arguments):
    return {"tag": "call", "callee": reference, "arguments": list(arguments)}


def refuses(impl, code, function, *args, **kwargs):
    with pytest.raises(impl.TransportRefusal) as rejected:
        function(*args, **kwargs)
    assert rejected.value.code == code
    assert rejected.value.record()["runtime_error_claim"] is False
    return rejected.value


def test_01_same_buffer_five_seven_seventeen_joins(impl, buffers, receipt):
    assert receipt["assignment_order"] == ["margins", "data", "regularizer", "factors", "gradient"]
    assert receipt["context_statement_count"] == 7 and receipt["prefix_statement_count"] == 5
    assert len(receipt["binding_joins"]) == 20  # seventeen original components plus function/callee/L2
    assert receipt["module_ast_node_count"] == 2930
    assert receipt["raw_program"][0]["rhs"]["tag"] == "listComp"
    assert receipt["raw_program"][0]["rhs"]["body"]["callee"] == callee("_dot")
    assert receipt["raw_program"][2]["rhs"]["right"] == integer(2)
    assert impl.verify_prefix_receipt(receipt, *buffers) is True


def test_02_source_grouping_and_stale_buffer_refusal(impl, buffers):
    source, bindings, draft = buffers
    for changed in (source + b"\n", source.replace(b" / len(margins)", b" * len(margins)"),
                    source.replace(b"L2 * _dot", b"L2 + _dot")):
        error = refuses(impl, "source_pin", impl.transport_prefix, changed, bindings, draft)
        assert error.path == "$.source"
    refuses(impl, "source_pin", impl.transport_prefix, source, bindings + b" ", draft)


def test_03_decoder_duplicate_noncanonical_forged_schema(impl, buffers, receipt):
    refuses(impl, "duplicate_json_key", impl.decode_json, b'{"schema":"a","schema":"b"}')
    refuses(impl, "nonfinite_json", impl.decode_json, b'{"n":NaN}')
    for field, value in (("schema", "forged"), ("parser", "other"), ("rule_digest", "0" * 64),
                         ("unknown_field", True)):
        mutated = copy.deepcopy(receipt)
        mutated[field] = value
        refuses(impl, "receipt_join", impl.verify_prefix_receipt, mutated, *buffers)
    refuses(impl, "noncanonical_receipt", impl.decode_prefix_receipt,
            json.dumps(receipt, indent=1).encode(), *buffers)


def test_04_callee_and_lexical_registry_refusals(impl, buffers, receipt):
    c = context(z="scalar")
    for source in (b"numpy.exp(z)", b"math.sqrt(z)", b"z(z)", b"math.exp.real(z)"):
        error = refuses(impl, "callee_registry" if source != b"z(z)" else "shadowed_callee",
                         impl.transport_expression, source, c)
        assert error.path.startswith("expression.body.func")
    mutated = copy.deepcopy(receipt)
    mutated["binding_joins"]["dot_callee"]["ast_sha256"] = "0" * 64
    refuses(impl, "receipt_join", impl.verify_prefix_receipt, mutated, *buffers)


def test_05_hygienic_dot_name_substitution_and_order(receipt):
    steps = [step for step in receipt["normalization_steps"] if step["rule"] == "dot-name-inline@1"]
    assert len(steps) == 2
    assert [[v["binding"]["spelling"] for v in s["argument_reads"]] for s in steps] == [["weights", "row"], ["weights", "weights"]]
    assert [[v["ordinal"] for v in s["argument_reads"]] for s in steps] == [[0, 1], [0, 1]]
    margins = receipt["normalized_program"][0]["rhs"]
    outer_row = margins["generators"][0]["target"]["identifier"]
    dot_gen = margins["body"]["arguments"][0]
    pair = dot_gen["generators"][0]["target"]["elements"]
    assert [v["identifier"]["spelling"] for v in pair] == ["x", "y"]
    assert pair[0]["identifier"]["scope"] != outer_row["scope"]
    assert dot_gen["generators"][0]["iterable"] == call(callee("zip"), name(1, "weights"), name(outer_row["scope"], "row"))
    assert all(step["argument_once_order_preservation_proved"] is False for step in steps)


def test_06_literal_kind_token_bits_and_exact_ratio(impl, receipt):
    zero = impl.transport_expression(b"0.0", {})["expression"]
    assert zero == {"tag": "floatLiteral", "token": "0.0", "binary64_hex": "0000000000000000", "numerator": "0", "denominator": "1"}
    assert impl.transport_expression(b"0", {})["expression"] == integer(0)
    l2 = receipt["normalized_program"][2]["rhs"]["left"]["left"]
    assert [l2["numerator"], l2["denominator"]] == ["5764607523034235", "576460752303423488"]
    assert l2["token"] == "0.01" and l2["binary64_hex"] == "3f847ae147ae147b"
    refuses(impl, "literal_kind", impl.transport_expression, b"True", {})
    refuses(impl, "finite_float_required", impl.transport_expression, b"1e999", {})


def test_07_binary_operand_tree_retains_left_right_static_order(impl):
    expression = impl.transport_expression(b"(a / b) - (b / a)", context(a="scalar", b="scalar"))["expression"]
    assert expression == binary("sub", binary("div", name(1, "a"), name(1, "b")), binary("div", name(1, "b"), name(1, "a")))
    error = refuses(impl, "unbound_name", impl.transport_expression, b"missing_left + missing_right", {})
    assert error.path == "expression.body.left"
    assert error.record()["phase"] == "static_transport"


def test_08_domain_syntax_is_not_evaluated_or_certified(impl):
    for source in (b"1 / 0", b"math.log1p(-2)", b"math.fsum(z for z in values) / len(values)"):
        result = impl.transport_expression(source, context(values="vector"))
        assert result["source_execution_calls"] == 0 and result["target_evaluator_calls"] == 0
        assert result["AST_lowering_preservation_proved"] is False
    assert impl.transport_expression(b"1 / 0", {})["expression"] == binary("div", integer(1), integer(0))


def test_09_conditional_branches_retained_and_static_dead_refusal(impl):
    result = impl.transport_expression(b"1 if z >= 0 else 1 / 0", context(z="scalar"))["expression"]
    assert result == {"tag": "ifExp", "test": {"tag": "compare", "operator": "ge", "left": name(1, "z"), "right": integer(0)},
                      "then": integer(1), "otherwise": binary("div", integer(1), integer(0))}
    error = refuses(impl, "unsupported_syntax", impl.transport_expression,
                     b"1 if z >= 0 else (lambda: 1)", context(z="scalar"))
    assert error.path == "expression.body.orelse"
    refuses(impl, "comparison_zero_integer", impl.transport_expression, b"1 if z >= 0.0 else 2", context(z="scalar"))


def test_10_generator_list_distinction_materialization_unproved(impl, receipt):
    c = context(values="vector")
    eager = impl.transport_expression(b"math.fsum([z for z in values])", c)
    lazy = impl.transport_expression(b"math.fsum(z for z in values)", c)
    assert eager["expression"]["arguments"][0]["tag"] == "listComp"
    assert lazy["expression"]["arguments"][0]["tag"] == "generatorExp"
    assert eager["materialization_obligations"] == []
    assert len(lazy["materialization_obligations"]) == 1
    assert len(receipt["materialization_obligations"]) == 4
    assert all(o["materialization_performed"] is False and o["purity_and_error_order_preservation_proved"] is False
               for o in receipt["materialization_obligations"])


def test_11_filters_async_keywords_starred_arbitrary_attributes(impl):
    c = context(values="vector", a="vector", b="vector", z="scalar")
    for source, code in ((b"[z for z in values if z]", "generator_filter_or_async"),
                         (b"[z async for z in values]", "generator_filter_or_async"),
                         (b"[z for z in a for y in b]", "generator_count"),
                         (b"math.exp(x=z)", "keyword_call"), (b"max(*values)", "starred_call"),
                         (b"z.real", "unsupported_syntax")):
        refuses(impl, code, impl.transport_expression, source, c)


def test_12_zip_tuple_binding_order_without_numerical_claim(impl):
    result = impl.transport_expression(b"[x * y for y, x in zip(a, b)]", context(a="vector", b="vector"))
    syntax = result["expression"]
    assert syntax["generators"][0]["iterable"] == call(callee("zip"), name(1, "a"), name(1, "b"))
    assert [e["identifier"]["spelling"] for e in syntax["generators"][0]["target"]["elements"]] == ["y", "x"]
    assert syntax["body"] == binary("mul", name(2, "x"), name(2, "y"))
    refuses(impl, "tuple_target", impl.transport_expression, b"[x for x, x in zip(a, b)]", context(a="vector", b="vector"))
    refuses(impl, "tuple_requires_zip", impl.transport_expression, b"[x for x, y in a]", context(a="vector"))
    assert result["AST_lowering_preservation_proved"] is False


def test_13_index_and_dimension_static_refusals(impl):
    c = context(weights="vector", i="integer")
    assert impl.transport_expression(b"weights[i]", c)["expression"] == {"tag": "subscript", "value": name(1, "weights"), "index": name(1, "i")}
    refuses(impl, "index_shape", impl.transport_expression, b"weights[-1]", c)
    refuses(impl, "index_shape", impl.transport_expression, b"weights[0:2]", c)
    refuses(impl, "index_literal", impl.transport_expression, b"weights[True]", c)
    for dimensions in ([True], [-1], [4097], [2, 3]):
        broken = copy.deepcopy(c)
        broken["weights"]["dimensions"] = dimensions
        refuses(impl, "context_dimensions", impl.transport_expression, b"weights[i]", broken)


def test_14_range_len_bound_name_retained_and_other_range_refused(impl, receipt):
    gradient = receipt["normalized_program"][4]["rhs"]
    assert gradient["generators"][0]["iterable"] == call(callee("range"), call(callee("len"), name(1, "weights")))
    for source in (b"[i for i in range(80)]", b"[i for i in range(len(weights) + 1)]"):
        refuses(impl, "range_len_name", impl.transport_expression, source, context(weights="vector"))
    refuses(impl, "call_arity", impl.transport_expression, b"[i for i in range(0, 80)]", {})


def test_15_shadowing_capture_and_forged_context(impl):
    syntax = impl.transport_expression(b"[x + math.fsum(x * y for x, y in zip(a, b)) for x in a]", context(a="vector", b="vector"))["expression"]
    assert syntax["body"]["left"] == name(2, "x")
    inner = syntax["body"]["right"]["arguments"][0]
    assert inner["body"] == binary("mul", name(3, "x"), name(3, "y"))
    error = refuses(impl, "unbound_name", impl.transport_expression, b"[z for z in z]", {})
    assert error.path.endswith(".generators[0].iter")
    refuses(impl, "reserved_binding", impl.transport_expression, b"[math for math in a]", context(a="vector"))
    for field, value in (("scope", 0), ("scope", True), ("immutable", False)):
        c = context(a="vector")
        c["a"][field] = value
        refuses(impl, "context_identity", impl.transport_expression, b"a", c)


def test_16_assignment_target_rhs_joins_and_order(receipt):
    for index, spelling in enumerate(["margins", "data", "regularizer", "factors", "gradient"]):
        statement = receipt["normalized_program"][index]
        assert statement["tag"] == "assign" and len(statement["targets"]) == 1
        assert statement["targets"][0]["identifier"] == {"tag": "PyName", "scope": 1, "spelling": spelling}
        joins = [j for j in receipt["normalized_occurrence_joins"] if j["output_path"] == f"$.normalized_program[{index}]"]
        assert len(joins) == 1 and joins[0]["source"]["raw_path"] == f"module.body[24].body[{index}]"
    data_denominator = receipt["normalized_program"][1]["rhs"]["right"]
    assert data_denominator == call(callee("len"), name(1, "margins"))


def test_17_byte_depth_width_cycle_and_protocol_bounds(impl, buffers, receipt):
    refuses(impl, "source_bytes_bound", impl.transport_expression, b" " * 262145, {})
    refuses(impl, "json_bytes_bound", impl.decode_json, b" " * 262145)
    deep = []
    for _ in range(100):
        deep = [deep]
    refuses(impl, "structure_bound", impl._bounds, deep)
    refuses(impl, "width_bound", impl._bounds, [None] * 257)
    cyclic = []
    cyclic.append(cyclic)
    refuses(impl, "cycle", impl._bounds, cyclic)
    refuses(impl, "primitive_type", impl._bounds, object())
    mutated = copy.deepcopy(receipt)
    mutated["raw_program"].append(mutated)
    refuses(impl, "cycle", impl.verify_prefix_receipt, mutated, *buffers)


def test_18_whole_objective_guard_return_context_refusal(impl, buffers, receipt):
    refuses(impl, "whole_objective_unsupported", impl.transport_prefix, *buffers, whole_objective=True)
    assert [node["node_kind"] for node in receipt["source_suffix_context_only"]] == ["Expr", "Return"]
    assert receipt["observation"] == "ordered five internal bindings; not actual Python return"
    refuses(impl, "unsupported_syntax", impl.transport_expression, b"{'objective': 1}", {})
    refuses(impl, "callee_registry", impl.transport_expression, b"_need(True, 'bad')", {})


def test_19_loop_mutation_and_source_semantics_remain_open(impl, receipt):
    refuses(impl, "unsupported_syntax", impl.transport_expression, b"(weights := 1)", {})
    for flag in ("original_source_semantics_proved", "original_loop_convergence_proved", "Python_Float_refinement_proved",
                 "global_autoencoder_convergence_proved", "AST_lowering_preservation_proved"):
        assert receipt[flag] is False
    assert receipt["source_execution_calls"] == 0 and receipt["old_emitter_import_or_calls"] == 0


def test_20_full_occurrence_receipt_and_api_source_join(impl, buffers, receipt):
    joins = receipt["normalized_occurrence_joins"]
    assert len({j["output_path"] for j in joins}) == len(joins)
    assert all(j["source"]["raw_path"] in receipt["raw_occurrences"] for j in joins)
    assert all(len(j["output_subtree_sha256"]) == 64 for j in joins)
    for change in ("normalized_program_sha256", "receipt_sha256"):
        mutated = copy.deepcopy(receipt)
        mutated[change] = "0" * 64
        refuses(impl, "receipt_join", impl.verify_prefix_receipt, mutated, *buffers)
    assert receipt["strict_cache_admission"] is False and receipt["planner_activation"] is False
    if impl.LEAN_API_PIN is None:
        refuses(impl, "lean_constructor_api_pending", impl.emit_lean_prefix, receipt, *buffers, b"not an API")
    else:
        api = Path(os.environ["RANKER_PY_AST_API"]).read_bytes()
        result = impl.emit_lean_prefix(receipt, *buffers, api)
        assert "def rawPrefix : List PyStmt" in result["module_text"]
        assert "def normalizedPrefix : List PyStmt" in result["module_text"]
        assert "PyExpr.generatorExp" in result["module_text"] and "PyExpr.listComp" in result["module_text"]
        assert "5764607523034235 : ℚ" in result["module_text"]
        assert "SourceExpr" not in result["module_text"] and "SourceTerm" not in result["module_text"]
        assert result["actual_prefix_native_checked"] is False and result["semantic_preservation_proved"] is False
        refuses(impl, "lean_api_pin", impl.emit_lean_prefix, receipt, *buffers, api + b"\n")
        keyword = impl.emit_lean_prefix(receipt, *buffers, api, namespace="end")
        assert "namespace «end»" in keyword["module_text"]
        refuses(impl, "identifier", impl.emit_lean_prefix, receipt, *buffers, api, namespace="x\nend")
