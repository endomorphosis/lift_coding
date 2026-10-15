"""Native elaboration, strict arithmetic adapter, and source replay boundaries."""
from copy import deepcopy
from fractions import Fraction
import hashlib
import json
from pathlib import Path

import pytest

import constraint_projections as p
from ipfs_datasets_py.logic.backends.smt import compiler as smt
from ipfs_datasets_py.logic.syntax_core import ast as fol


@pytest.fixture(scope="module")
def contract():
    from constraint_io import inputs
    from scheduler_constraints import build_scheduler_contract
    _, bodies, instructions, _ = inputs()
    prior = Path(__file__).resolve().parent.parent / "terminal-intent-coverage-20261015-01" / "experiment-02" / "structural-report.json"
    return build_scheduler_contract(instruction=instructions["llm-inference-batching-scheduler"],
        head=json.loads(prior.read_bytes())["head"], source_records=[
            {"path": name, "source_text": raw.decode("utf-8"), "sha256": hashlib.sha256(raw).hexdigest()}
            for name, raw in sorted(bodies.items())])


@pytest.fixture(scope="module")
def report(contract):
    return p.build_constraint_projections(contract=contract)


def test_native_typed_roots_and_numeric_compiler_receipts(report, contract):
    assert p.validate_constraint_projections(report, contract=contract) is report
    assert len(report["first_order"]) == 4
    assert len(report["smt"]) == 9
    assert report["families"] == ["first_order"]
    assert report["native_translation_namespaces"]["target"] == "smt"
    for row in report["first_order"]:
        expression = fol.TypedExpression.from_dict(row["typed_expression"])
        assert expression.to_dict() == row["typed_expression"]
        assert row["native_elaboration_executed"] is True
        assert row["native_round_trip_checked"] is True
        assert row["candidate_asserted_true"] is False
    for row in report["smt"]:
        assert row["compilation"]["interface"] == "SoftwareVerificationSMTCompiler@1"
        assert row["compilation"]["schema_version"] == "software-verification-smt-compilation/v1"
        assert row["compilation"]["source_identity"] != row["compilation"]["target_identity"]
        assert row["compilation"]["receipt"]
        assert "(set-logic UFLIA)" in row["compilation"]["smtlib"]
        assert row["obligation"]["query_mode"] == "satisfiability"
        assert row["native_compiler_executed"] is True
        assert "family_id" not in row
        assert row["namespace_role"] == "native_compiler_translation_labels_not_canonical_semantic_families"
        assert all(row[key] is False for key in p.FALSE)
    assert all(report[key] is False for key in p.FALSE)
    assert report["losses"][0]["requirement_id"] == "scheduler.input_schema"


def test_exact_once_has_coverage_uniqueness_and_bucket_ownership(report):
    row = next(v for v in report["first_order"] if v["kind"] == "exact_once")
    counts = row["operator_counts"]
    assert counts["forall"] == 4 and counts["exists"] == 2
    assert counts["equality"] == 10
    text = json.dumps(row["typed_expression"])
    assert '"request_id"' in text and '"bucket"' in text
    assert '"is_output"' in text and '"is_input"' in text
    assert "distinct finite row occurrences" in report["interpretation"]["record_identity"]


def test_global_shape_cap_has_real_equality_quantifiers_not_cardinality_atom(report):
    row = next(v for v in report["first_order"] if v["kind"] == "global_shape_cap")
    expression = fol.TypedExpression.from_dict(row["typed_expression"])
    assert expression.root.kind is fol.NodeKind.NOT
    assert len(expression.root.arguments[0].binders) == 9
    assert row["operator_counts"]["not"] == 37
    assert row["operator_counts"]["equality"] == 45
    assert row["operator_counts"]["exists"] == 10
    predicates = {n.symbol for n in p._walk_fol(expression.root) if n.kind is fol.NodeKind.PREDICATE}
    assert predicates == {"is_output"}


def test_native_fol_sort_error_cannot_be_promoted_to_typed_formula():
    f = p._FOL()
    changed = f.eq(f.var("record", "Record"), f.var("shape", "Shape"))
    with pytest.raises(ValueError):
        fol.TypedExpression("bad-sort", changed, f.signature)


def test_experimental_adapter_closes_typed_native_free_variables():
    f = p._FOL()
    root = f.pred("is_input", "missing")
    # Native typed syntax permits typed free variables.  This experimental
    # whole-constraint profile adds an explicit closure check.
    assert fol.TypedExpression("typed-free-variable", root, f.signature)
    with pytest.raises(ValueError):
        p._closed_fol(root)


@pytest.mark.parametrize("mutation", (
    "drop-formula", "drop-numeric", "alter-operator", "alter-metric", "drop-bucket",
    "assert-candidate", "claim-proof", "change-head", "change-clause", "unknown-field"))
def test_rehashed_candidate_report_forgery_refuses(report, contract, mutation):
    changed = deepcopy(report)
    if mutation == "drop-formula":
        changed["first_order"].pop()
    elif mutation == "drop-numeric":
        changed["smt"].pop()
    elif mutation == "alter-operator":
        changed["smt"][0]["obligation"]["goal"]["kind"] = "exists"
    elif mutation == "alter-metric":
        changed["smt"][1]["metric"] = "fabricated"
    elif mutation == "drop-bucket":
        changed["first_order"][0]["typed_expression"]["metadata"]["requirement_id"] = "unqualified"
    elif mutation == "assert-candidate":
        changed["first_order"][0]["candidate_asserted_true"] = True
    elif mutation == "claim-proof":
        changed["source_model_equivalence_proved"] = True
    elif mutation == "change-head":
        changed["head_sha256"] = "0" * 64
    elif mutation == "change-clause":
        changed["first_order"][0]["clause_sha256"] = "0" * 64
    else:
        changed["dispatch_allowed"] = True
    changed.pop("report_sha256")
    changed["report_sha256"] = p._sha(changed)
    with pytest.raises(ValueError):
        p.validate_constraint_projections(changed, contract=contract)


@pytest.mark.parametrize("mutation", ("instruction", "source", "granularity", "head", "threshold"))
def test_rebound_contract_changes_refuse(contract, mutation):
    changed = deepcopy(contract)
    if mutation == "instruction":
        changed["instruction"]["source_text"] += " "
    elif mutation == "source":
        changed["sources"][0]["source_text"] += "\n# changed\n"
    elif mutation == "head":
        changed["head"]["snapshot_cid"] = "fabricated"
    elif mutation == "granularity":
        next(v for v in changed["clauses"] if v["kind"] == "shape_alignment")["parameters"]["granularity"] = 32
    else:
        next(v for v in changed["clauses"] if v["kind"] == "thresholds")["parameters"]["metrics"]["cost"]["numerator"] -= 1
    with pytest.raises(ValueError):
        p.build_constraint_projections(contract=changed)


def _decls():
    return [smt.SmtFunDecl("x", range=smt.INT_SORT, is_const=True),
            smt.SmtFunDecl("y", range=smt.INT_SORT, is_const=True),
            smt.SmtFunDecl("flag", range=smt.BOOL_SORT, is_const=True)]


@pytest.mark.parametrize("term", (
    smt.SmtTerm("raw", value="(assert false)"),
    smt.SmtTerm("real", value="nan"),
    smt.SmtTerm("real", value="inf"),
    smt.SmtTerm("real", value="0.055"),
    smt.SmtTerm("int", value="+1"),
    smt.SmtTerm("int", value="01"),
    smt.SmtTerm("int", value="1000000000000000001"),
    smt.SmtTerm("symbol", value="undeclared"),
    smt.SmtTerm("symbol", value="x) (assert false"),
    smt.SmtTerm("lt", arguments=(smt.term_symbol("flag"), smt.term_int(1))),
    smt.SmtTerm("add", arguments=(smt.term_symbol("flag"), smt.term_int(1))),
    smt.SmtTerm("mul", arguments=(smt.term_symbol("x"), smt.term_symbol("y"))),
    smt.SmtTerm("div", arguments=(smt.term_symbol("x"), smt.term_symbol("y"))),
    smt.SmtTerm("div", arguments=(smt.term_symbol("x"), smt.term_int(0))),
    smt.SmtTerm("mod", arguments=(smt.term_symbol("x"), smt.term_int(-1))),
    smt.SmtTerm("apply", value="x", arguments=(smt.term_int(1),)),
    smt.SmtTerm("eq", arguments=(smt.term_symbol("x"), smt.term_symbol("flag"))),
    smt.SmtTerm("int", value="1", sort=smt.BOOL_SORT),
    smt.SmtTerm("forall", binders=(smt.SmtBinder("x", smt.INT_SORT),), arguments=(smt.term_true(),)),
    smt.SmtTerm("forall", binders=(smt.SmtBinder("z", smt.INT_SORT),), arguments=(smt.term_int(1),)),
))
def test_strict_native_adapter_rejects_escape_and_wrong_sort(term):
    with pytest.raises(ValueError):
        p.validate_integer_term(term, declarations=_decls())


def test_strict_native_adapter_accepts_exact_linear_integer_formula():
    term = smt.SmtTerm("lt", arguments=(
        smt.SmtTerm("mul", arguments=(smt.term_int(200), smt.term_symbol("x"))),
        smt.SmtTerm("mul", arguments=(smt.term_int(11), smt.term_symbol("y")))))
    assert p.validate_integer_term(term, declarations=_decls()) == "Bool"


def _evaluate_native_integer_formula(node, *, fields, selected=True):
    """Independent fixture evaluator, not a proof or an interpretation bridge."""
    kind = node.kind.value
    if kind == "int":
        return int(node.value)
    if kind == "symbol":
        return "one-authored-fixture-object"
    if kind == "apply":
        return selected if node.value.startswith("is_") else fields[node.value]
    if kind in {"forall", "exists"}:
        return _evaluate_native_integer_formula(node.arguments[0], fields=fields, selected=selected)
    args = [_evaluate_native_integer_formula(v, fields=fields, selected=selected) for v in node.arguments]
    if kind == "and":return all(args)
    if kind == "implies":return not args[0] or args[1]
    if kind == "eq":return args[0] == args[1]
    if kind == "ge":return args[0] >= args[1]
    if kind == "le":return args[0] <= args[1]
    if kind == "gt":return args[0] > args[1]
    if kind == "lt":return args[0] < args[1]
    if kind == "add":return args[0] + args[1]
    if kind == "mul":return args[0] * args[1]
    if kind == "div":return args[0] // args[1]
    if kind == "mod":return args[0] % args[1]
    raise AssertionError("unexpected generated operator: " + kind)


@pytest.mark.parametrize("prompt", (0, 1, 63, 64, 65, 127, 128, 129))
def test_actual_numeric_rounding_formula_at_boundaries(report, prompt):
    row = next(v for v in report["smt"] if v["kind"] == "shape_alignment")
    goal = smt.SmtTerm.from_dict(row["obligation"]["goal"])
    rounded = ((prompt + 63) // 64) * 64
    fields = {"prompt_len": prompt, "seq_align": rounded, "heads_align": 32, "hidden_align": 4096}
    assert _evaluate_native_integer_formula(goal, fields=fields) is True
    if rounded:
        fields["seq_align"] = rounded - 64
        assert _evaluate_native_integer_formula(goal, fields=fields) is False
    fields["seq_align"] = rounded + 1
    assert _evaluate_native_integer_formula(goal, fields=fields) is False
    fields.update(seq_align=rounded, heads_align=31)
    assert _evaluate_native_integer_formula(goal, fields=fields) is False


def test_actual_numeric_metric_formula_uses_strict_exact_rational_boundary(report, contract):
    clauses = {row["requirement_id"]: row for row in contract["clauses"]}
    for row in report["smt"]:
        if row["kind"] != "thresholds":continue
        threshold = clauses[row["requirement_id"]]["parameters"]["metrics"][row["metric"]]
        bound = Fraction(threshold["numerator"], threshold["denominator"])
        goal = smt.SmtTerm.from_dict(row["obligation"]["goal"])
        for value, passed in ((bound - min(bound / 2, Fraction(1,1000)), True),
                              (bound, False), (bound + Fraction(1,1000), False)):
            assert _evaluate_native_integer_formula(goal, fields={
                "numerator": value.numerator, "denominator": value.denominator}) is passed
        assert _evaluate_native_integer_formula(goal, fields={"numerator": 0, "denominator": 0}) is False
        assert _evaluate_native_integer_formula(goal, fields={"numerator": -1, "denominator": 1}) is False
        assert _evaluate_native_integer_formula(goal, fields={"numerator": 1, "denominator": 1}, selected=False) is True
