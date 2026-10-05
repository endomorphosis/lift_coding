"""Pure compiler/refusal tests. Never import or run the captured ranker module."""
import ast
import copy
import hashlib
import os
from fractions import Fraction
from pathlib import Path

import pytest

from typed_slice_compiler import (
    CompileRefusal, DIFFERENCE_SHA256, DOT_AST_SHA256, SOURCE_SHA256,
    TRAINING_AST_SHA256, compile_ranker_slices, compile_scalar_ast,
    compile_zip_ast, eval_synthetic_scalar, eval_synthetic_zip,
    render_generated_lean, render_source_scalar, validate_original_shape, validate_scalar_ir,
    validate_zip_ir,
)


def expression(text):
    return ast.parse(text, mode="eval").body


@pytest.fixture
def pinned_source():
    # The owned harness must provide the separately frozen exact fixture path.
    data = Path(os.environ["RANKER_AST_SOURCE"]).read_bytes()
    assert len(data) == 16391
    assert hashlib.sha256(data).hexdigest() == SOURCE_SHA256
    return data


def compile_original(data, **kwargs):
    pins = {"expected_source_sha256": SOURCE_SHA256,
            "expected_dot_ast_sha256": DOT_AST_SHA256,
            "expected_training_ast_sha256": TRAINING_AST_SHA256}
    pins.update(kwargs)
    return compile_ranker_slices(data, **pins)


def synthetic_fold():
    return compile_zip_ast(expression("(p*q for p,q in zip(left,right))"),
                           kind="zipFold", vector_names=("left", "right"), binder_names=("p", "q"))


def synthetic_map():
    return compile_zip_ast(expression("[p-eta*q for p,q in zip(left,right)]"),
                           kind="zipMap", vector_names=("left", "right"),
                           binder_names=("p", "q"), external_names=("eta",))


def test_original_slices_keep_actual_arithmetic_and_context(pinned_source):
    result = compile_original(pinned_source)
    assert result["dot"]["ir"]["scalar"]["body"] == {
        "kind": "mul", "left": {"kind": "var", "slot": 0}, "right": {"kind": "var", "slot": 1}}
    assert result["update"]["ir"]["scalar"]["body"] == {
        "kind": "sub", "left": {"kind": "var", "slot": 0},
        "right": {"kind": "mul", "left": {"kind": "var", "slot": 2}, "right": {"kind": "var", "slot": 1}}}
    assert result["dot"]["lean_source_scalar"] == '(.mul (.var "x") (.var "y"))'
    assert result["update"]["lean_source_scalar"] == '(.sub (.var "w") (.mul (.var "step") (.var "g")))'
    module = ast.parse(pinned_source)
    training = next(x for x in module.body if isinstance(x, ast.FunctionDef) and x.name == "train_terminal_codebase_intent_ranker")
    loop, guard = training.body[5], training.body[5].body[2]
    for key, node in (("function_ast_sha256", training), ("loop_ast_sha256", loop),
                      ("guard_ast_sha256", guard), ("assignment_ast_sha256", guard.body[0]),
                      ("expression_ast_sha256", guard.body[0].value)):
        assert result["update"][key] == hashlib.sha256(ast.dump(node, include_attributes=False).encode()).hexdigest()
    assert result["update"]["path"].endswith("body[5].body[2].body[0]")


def test_original_receipt_preserves_open_frontiers(pinned_source):
    result = compile_original(pinned_source)
    assert result["status"] == "compiled_source_only_kernel_pending"
    for key in ("source_shape_frontier_proved", "python_ranker_source_equivalence_proved", "binary64_error_bound_proved",
                "full_objective_semantics_proved", "full_training_semantics_proved", "kernel_compiler_correctness_qualified",
                "proof_authority", "execution_authority", "completion_authority", "planner_authority", "planner_activation",
                "authority_activation", "AE_authority", "global_autoencoder_convergence_proved"):
        assert result[key] is False
    assert result["full_task_satisfaction"] == "unknown"
    assert result["official_benchmark_score"] is None
    assert "full objective and gradient" in result["open_frontiers"]
    assert "original shape provenance and corpus preparation" in result["open_frontiers"]


def test_candidate_renderer_uses_actual_bodies_and_seven_explicit_kernel_gates(pinned_source):
    result = compile_original(pinned_source)
    text = render_generated_lean(result, pinned_source)
    assert 'def emittedDotBody : SourceScalar := ' + result["dot"]["lean_source_scalar"] in text
    assert 'def emittedUpdateBody : SourceScalar := ' + result["update"]["lean_source_scalar"] in text
    assert result["update"]["assignment_ast_sha256"] in text
    assert TRAINING_AST_SHA256 in text
    assert text.count("#print axioms ") == 7
    assert "emitted_originalRealStep_join" in text
    assert "No Python/Float, objective, preparation, or full training equivalence" in text
    assert "sorry" not in text and "axiom " not in text


@pytest.mark.parametrize("mutator", [
    lambda x: x.update(extra=0), lambda x: x.update(proof_authority=True),
    lambda x: x["source"].update(sha256="0" * 64),
    lambda x: x["update"].update(function_ast_sha256=DOT_AST_SHA256),
    lambda x: x["dot"].update(lean_source_scalar='(.unsupported "injected")'),
    lambda x: x["dot"]["ir"]["scalar"]["body"].update(kind="div"),
    lambda x: x["external_shape_assumptions"].update(gradient_length=79),
    lambda x: x["source"].update(bytes=16391.0), lambda x: x["source"].update(bytes=True),
    lambda x: x["source"].update(module_ast_nodes=2930.0), lambda x: x["source"].update(module_ast_nodes=True),
])
def test_renderer_rejects_receipt_scope_pin_schema_and_constructor_drift(pinned_source, mutator):
    result = compile_original(pinned_source)
    mutator(result)
    with pytest.raises(CompileRefusal):
        render_generated_lean(result, pinned_source)


def test_renderer_rejects_consistently_changed_ir_and_literal_with_old_source_pins(pinned_source):
    result = compile_original(pinned_source)
    result["dot"]["ir"]["scalar"]["body"]["kind"] = "add"
    result["dot"]["lean_source_scalar"] = '(.add (.var "x") (.var "y"))'
    with pytest.raises(CompileRefusal):
        render_generated_lean(result, pinned_source)
    result = compile_original(pinned_source)
    result["update"]["assignment_ast_sha256"] = "0" * 64
    with pytest.raises(CompileRefusal):
        render_generated_lean(result, pinned_source)
    with pytest.raises(CompileRefusal):
        render_generated_lean(compile_original(pinned_source), pinned_source + b"\n")


@pytest.mark.parametrize("part,key", [(None, "open_frontiers"), ("dot", "expression_ast_sha256"),
                                      ("update", "guard_ast_sha256"), ("source", "module_ast_sha256")])
def test_renderer_rejects_missing_context_fields(pinned_source, part, key):
    result = compile_original(pinned_source)
    (result if part is None else result[part]).pop(key)
    with pytest.raises(CompileRefusal):
        render_generated_lean(result, pinned_source)


@pytest.mark.parametrize("mutator", [
    lambda b: b + b"\n",
    lambda b: b.replace(b"w - step * g", b"w + step * g", 1),
    lambda b: b.replace(b"math.fsum(x * y", b"sum(x * y", 1),
    lambda b: b.replace(b"if epoch < epochs:", b"if epoch <= epochs:", 1),
    lambda b: b.replace(b"range(epochs + 1)", b"range(epochs)", 1),
    lambda b: b.replace(b"zip(weights, gradient)", b"zip(gradient, weights)", 1),
    lambda b: b.replace(b"L2 = 0.01", b"L2 = 0.02", 1),
    lambda b: b + b"\ndef _dot(a,b):\n    return 0\n",
    lambda b: b.replace(b"weights = [w - step * g", b"weights = other = [w - step * g", 1),
])
def test_original_raw_source_drift_refused_even_if_context_looks_similar(pinned_source, mutator):
    changed = mutator(pinned_source)
    assert changed != pinned_source
    with pytest.raises(CompileRefusal):
        compile_original(changed)
    with pytest.raises(CompileRefusal):
        compile_original(changed, expected_source_sha256=hashlib.sha256(changed).hexdigest())


@pytest.mark.parametrize("kwargs", [
    {"expected_source_sha256": "0" * 64},
    {"expected_dot_ast_sha256": TRAINING_AST_SHA256},
    {"expected_training_ast_sha256": DOT_AST_SHA256},
    {"expected_dot_ast_sha256": "g" * 64},
    {"expected_source_sha256": None},
    {"expected_training_ast_sha256": "0" * 64},
    {"dimension": True}, {"dimension": 79}, {"weights_length": 81},
    {"gradient_length": 0}, {"gradient_length": False}, {"difference_rows": 0},
    {"difference_rows": 5}, {"difference_columns": 79},
    {"difference_artifact_sha256": "0" * 64}, {"difference_artifact_sha256": None},
    {"max_source_bytes": True}, {"max_module_nodes": 4097}, {"max_depth": 33},
    {"max_module_nodes": 1}, {"max_depth": 1},
])
def test_original_pins_shape_and_bounds_refuse(pinned_source, kwargs):
    with pytest.raises(CompileRefusal):
        compile_original(pinned_source, **kwargs)


def test_source_byte_cap_boundary(pinned_source):
    assert compile_original(pinned_source, max_source_bytes=len(pinned_source))["source"]["bytes"] == len(pinned_source)
    with pytest.raises(CompileRefusal):
        compile_original(pinned_source, max_source_bytes=len(pinned_source) - 1)
    with pytest.raises(CompileRefusal):
        compile_original(pinned_source.decode())


def test_original_shape_is_a_separate_external_assumption_gate():
    assert validate_original_shape(dimension=80, weights_length=80, gradient_length=80,
                                   difference_artifact_sha256=DIFFERENCE_SHA256)
    with pytest.raises(CompileRefusal):
        validate_original_shape(dimension=80, weights_length=79, gradient_length=80)


def test_generic_scalar_preserves_order_bindings_and_rationals():
    ir = compile_scalar_ast(expression("p-eta*q+0.5"), {"p": 0, "q": 1, "eta": 2})
    assert eval_synthetic_scalar(ir, (2, 3, Fraction(1, 4))) == Fraction(7, 4)
    assert ir["body"]["left"]["right"]["left"] == {"kind": "var", "slot": 2}
    literal = compile_scalar_ast(expression("0.1"), {"unused": 0})
    assert literal["body"] == {"kind": "num", "numerator": "3602879701896397", "denominator": "36028797018963968"}
    assert render_source_scalar(literal, ("unused",)) == "(.num ((3602879701896397 : ℚ) / (36028797018963968 : ℚ)))"


@pytest.mark.parametrize("text", [
    "f(p)", "math.exp(p)", "p.real", "row[i+1]", "p if flag else q", "p/q", "p**q", "-p",
    "lambda: p", "(p:=q)", "p<q", "[p]", "{p}", "True", "None", "'p'", "unbound*p",
])
def test_unsupported_scalar_nodes_calls_attributes_branches_indices_refuse(text):
    with pytest.raises(CompileRefusal):
        compile_scalar_ast(expression(text), {"p": 0, "q": 1})


@pytest.mark.parametrize("value", [True, False, float("inf"), float("-inf"), float("nan"), 1 << 257])
def test_bool_nonfinite_and_oversized_constants_refuse(value):
    with pytest.raises(CompileRefusal):
        compile_scalar_ast(ast.Constant(value=value), {"p": 0})


@pytest.mark.parametrize("scope", [{}, {"p": True}, {"p": 1}, {"p": 0, "q": 0}, {"p": 0, "q": 2}, {"p-q": 0}])
def test_bad_lexical_scope_refuses(scope):
    with pytest.raises(CompileRefusal):
        compile_scalar_ast(expression("p"), scope)


def test_ast_node_and_depth_caps_are_preflighted():
    node = expression("p*q")
    count = sum(1 for _ in ast.walk(node))
    assert compile_scalar_ast(node, {"p": 0, "q": 1}, max_nodes=count)
    with pytest.raises(CompileRefusal):
        compile_scalar_ast(node, {"p": 0, "q": 1}, max_nodes=count - 1)
    with pytest.raises(CompileRefusal):
        compile_scalar_ast(node, {"p": 0, "q": 1}, max_nodes=True)
    deep = ast.Name(id="p", ctx=ast.Load())
    for _ in range(40):
        deep = ast.BinOp(left=deep, op=ast.Mult(), right=ast.Constant(value=1))
    with pytest.raises(CompileRefusal):
        compile_scalar_ast(deep, {"p": 0})


def test_wide_and_cyclic_unsupported_ast_refuses_with_bounded_pending_stack():
    wide = ast.List(elts=[ast.Name(id="p", ctx=ast.Load()) for _ in range(2000)], ctx=ast.Load())
    with pytest.raises(CompileRefusal):
        compile_scalar_ast(wide, {"p": 0})
    cyclic = ast.BinOp(op=ast.Mult(), right=ast.Constant(value=1))
    cyclic.left = cyclic
    with pytest.raises(CompileRefusal):
        compile_scalar_ast(cyclic, {"p": 0})


@pytest.mark.parametrize("text", [
    "(p*q for q,p in zip(left,right))", "(p*q for p,q in zip(right,left))",
    "(p*q for p,q in zip(left,right,strict=True))", "(p*q for p,q in zip(left,right,left))",
    "(p*q for p,q in other(left,right))", "(p*q for p,q in zip(left,right) if p)",
    "(p*q for p,q in zip(left,right) for z in left)", "(p*q async for p,q in zip(left,right))",
    "(p*q for p,p in zip(left,right))", "(p*q for p in zip(left,right))",
    "(left*q for p,q in zip(left,right))", "(p*q[0] for p,q in zip(left,right))",
    "(p*q if p else q for p,q in zip(left,right))", "[p*q for p,q in zip(left,right)]",
])
def test_zip_scope_and_unsupported_comprehensions_refuse(text):
    with pytest.raises(CompileRefusal):
        compile_zip_ast(expression(text), kind="zipFold", vector_names=("left", "right"), binder_names=("p", "q"))


def test_zip_binder_cannot_shadow_vector_or_external_slot():
    with pytest.raises(CompileRefusal):
        compile_zip_ast(expression("[p-eta*q for p,q in zip(left,right)]"), kind="zipMap",
                        vector_names=("left", "right"), binder_names=("p", "q"), external_names=("p",))
    with pytest.raises(CompileRefusal):
        compile_zip_ast(expression("(left*q for left,q in zip(left,right))"), kind="zipFold",
                        vector_names=("left", "right"), binder_names=("left", "q"))


@pytest.mark.parametrize("left,right,expected", [
    ((), (), Fraction(0)), ((2, 7), (), Fraction(0)), ((), (3,), Fraction(0)),
    ((2, 7), (3,), Fraction(6)), ((2,), (3, 99), Fraction(6)),
    ((2, 7), (3, 5), Fraction(41)),
])
def test_synthetic_fold_empty_and_unequal_zip_is_min_length(left, right, expected):
    assert eval_synthetic_zip(synthetic_fold(), left, right) == expected


def test_synthetic_update_empty_truncation_and_simultaneous_arithmetic():
    ir = synthetic_map()
    assert eval_synthetic_zip(ir, (), (2,), (Fraction(1, 2),)) == ()
    assert eval_synthetic_zip(ir, (2, 9), (3,), (Fraction(1, 2),)) == (Fraction(1, 2),)
    assert eval_synthetic_zip(ir, (2, 9), (3, 4), (Fraction(1, 2),)) == (Fraction(1, 2), Fraction(7))
    assert eval_synthetic_zip(ir, (2,), (3, 4), (Fraction(1, 2),)) == (Fraction(1, 2),)


@pytest.mark.parametrize("values", [(True, 1), (1.0, 2), (1 << 33, 2), (1,), (1, 2, 3)])
def test_synthetic_oracle_refuses_nonrational_values_and_wrong_arity(values):
    ir = compile_scalar_ast(expression("p*q"), {"p": 0, "q": 1})
    with pytest.raises(CompileRefusal):
        eval_synthetic_scalar(ir, values)


def test_synthetic_oracle_cannot_replay_original_dimension():
    with pytest.raises(CompileRefusal):
        eval_synthetic_zip(synthetic_fold(), tuple(range(80)), tuple(range(80)))


@pytest.mark.parametrize("mutator", [
    lambda x: x.update(extra=0), lambda x: x.update(schema="other"),
    lambda x: x.update(slots=True), lambda x: x.update(slots=0),
    lambda x: x["body"].update(extra=0), lambda x: x["body"].update(kind="gradient"),
    lambda x: x["body"]["left"].update(slot=2), lambda x: x["body"]["left"].update(slot=True),
    lambda x: x["body"].pop("right"),
])
def test_unknown_missing_extra_scalar_ir_keys_and_slots_refuse(mutator):
    ir = compile_scalar_ast(expression("p*q"), {"p": 0, "q": 1})
    mutator(ir)
    with pytest.raises(CompileRefusal):
        validate_scalar_ir(ir)


@pytest.mark.parametrize("number", [
    {"kind": "num", "numerator": "01", "denominator": "1"},
    {"kind": "num", "numerator": "-0", "denominator": "1"},
    {"kind": "num", "numerator": "1", "denominator": "0"},
    {"kind": "num", "numerator": "2", "denominator": "4"},
    {"kind": "num", "numerator": 1, "denominator": "1"},
    {"kind": "num", "numerator": "1" * 80, "denominator": "1"},
])
def test_noncanonical_or_unbounded_rational_ir_refuses(number):
    with pytest.raises(CompileRefusal):
        validate_scalar_ir({"schema": "ranker-typed-scalar-ir@1", "slots": 1, "body": number})


def test_cycle_in_untrusted_ir_refuses_without_recursion():
    body = {"kind": "mul", "right": {"kind": "var", "slot": 0}}
    body["left"] = body
    with pytest.raises(CompileRefusal):
        validate_scalar_ir({"schema": "ranker-typed-scalar-ir@1", "slots": 1, "body": body})


@pytest.mark.parametrize("mutator", [
    lambda x: x.update(extra=0), lambda x: x.update(kind="dot"), lambda x: x.update(zip_length="equal"),
    lambda x: x.update(fold="Python-fsum"), lambda x: x.update(inputs=["left"]),
    lambda x: x.update(binders=["p", "p"]), lambda x: x.update(externals=["p"]),
    lambda x: x["scalar"].update(slots=3), lambda x: x.pop("scalar"),
])
def test_unknown_or_malformed_zip_ir_refuses_before_oracle(mutator):
    ir = copy.deepcopy(synthetic_fold())
    mutator(ir)
    with pytest.raises(CompileRefusal):
        validate_zip_ir(ir)


def test_wrong_objective_gradient_index_is_unsupported_and_objective_stays_open():
    with pytest.raises(CompileRefusal):
        compile_scalar_ast(expression("row[i+1]"), {"row": 0, "i": 1})
    # This refusal is syntax coverage, not an objective-gradient correctness theorem.
