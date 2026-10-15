"""Experimental source-bound scheduler candidates using actual native logic IRs.

The finite contract remains authoritative for this experiment.  Typed FOL and
SMT compilation check representation; neither interprets the prompt, observes
the task, proves source behavior, or permits dispatch.  All carrier/field
interpretations and the missing finite-case correspondence are explicit.
"""
from __future__ import annotations

import hashlib
import importlib
import json
from pathlib import Path
import re

from ipfs_datasets_py.logic.syntax_core import ast as fol
from ipfs_datasets_py.logic.syntax_core import signatures as sig
from ipfs_datasets_py.logic.backends.smt import compiler as smt

SCHEMA = "terminal-scheduler-native-constraint-projections@1"
FALSE = {key: False for key in (
    "proof_authority", "execution_authority", "completion_authority",
    "source_semantics_verified", "source_model_equivalence_proved",
    "full_task_coverage", "original_task_admitted", "task_satisfaction",
    "training_convergence_proved", "interpretation_correspondence_proved",
    "smt_backend_executed", "lean_backend_executed",
)}
_NAME = re.compile(r"[a-z][a-z0-9_]{0,47}\Z")
_INT = re.compile(r"(?:0|[1-9][0-9]*|-[1-9][0-9]*)\Z")
MAX_INTEGER = 10**18


class ConstraintProjectionError(ValueError):
    """Unsupported candidate, malformed native term, or changed binding."""


def _wire(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"),
                      ensure_ascii=True, allow_nan=False).encode("ascii")


def _sha(value):
    return hashlib.sha256(_wire(value)).hexdigest()


def producer_paths():
    """Selected public implementation files; not a transitive dependency claim."""
    names = (
        "ipfs_datasets_py.logic.syntax_core.ast",
        "ipfs_datasets_py.logic.syntax_core.signatures",
        "ipfs_datasets_py.logic.syntax_core.contracts",
        "ipfs_datasets_py.logic.backends.smt.compiler",
        "ipfs_datasets_py.logic.software_verification.receipts",
        "ipfs_datasets_py.logic.software_verification.translations",
        "ipfs_datasets_py.logic.ir_core.identity",
        "ipfs_datasets_py.logic.ir_core.canonical",
        "ipfs_datasets_py.logic.ir_core.claims",
        "ipfs_datasets_py.logic.families.registry",
    )
    return sorted({str(Path(__file__).resolve()), *(
        str(Path(importlib.import_module(name).__file__).resolve()) for name in names)})


def _validate_contract(contract):
    from scheduler_constraints import validate_scheduler_contract
    if type(contract) is not dict:
        raise ConstraintProjectionError("closed scheduler contract required")
    try:
        validate_scheduler_contract(contract,
            instruction=contract["instruction"]["source_text"].encode("utf-8"),
            head=contract["head"], source_records=contract["sources"])
    except (KeyError, TypeError, ValueError, RecursionError) as error:
        raise ConstraintProjectionError("source-bound scheduler contract does not replay") from error


class _FOL:
    """Generate unique native node identities and elaborate every expression."""

    def __init__(self):
        self.count = 0
        self.sorts = {name: sig.atomic_sort(name) for name in (
            "Record", "RequestId", "Bucket", "Batch", "Shape", "FilePath", "Bytes")}
        s = self.sorts
        self.signature = sig.many_sorted_fol_signature(
            "scheduler-constraint-signature", sorts=tuple(s.values()),
            functions=(("request_id", (s["Record"],), s["RequestId"]),
                       ("bucket", (s["Record"],), s["Bucket"]),
                       ("batch", (s["Record"],), s["Batch"]),
                       ("shape", (s["Record"],), s["Shape"]),
                       ("before", (s["FilePath"],), s["Bytes"]),
                       ("after", (s["FilePath"],), s["Bytes"])),
            predicates=(("is_input", (s["Record"],)),
                        ("is_output", (s["Record"],)),
                        ("is_input_file", (s["FilePath"],))),
            family="first_order", profile="many_sorted")

    def ident(self):
        self.count += 1
        return "scheduler-node:" + str(self.count)

    def var(self, name, sort="Record"):
        return fol.mk_variable(self.ident(), name, self.sorts[sort])

    def app(self, function, name, sort="Record"):
        return fol.mk_application(self.ident(), function, (self.var(name, sort),))

    def pred(self, predicate, name, sort="Record"):
        return fol.mk_predicate(self.ident(), predicate, (self.var(name, sort),))

    def eq(self, left, right):
        return fol.mk_equality(self.ident(), left, right)

    def negate(self, body):
        return fol.mk_not(self.ident(), body)

    def conjunction(self, *nodes):
        return fol.mk_and(self.ident(), *nodes)

    def imply(self, left, right):
        return fol.mk_implies(self.ident(), left, right)

    def quantify(self, kind, variables, body):
        binders = tuple(fol.Binder(name, self.sorts[sort]) for name, sort in variables)
        constructor = fol.mk_forall if kind == "forall" else fol.mk_exists
        return constructor(self.ident(), binders, body)

    def matching(self, left, right):
        return self.conjunction(
            self.eq(self.app("request_id", left), self.app("request_id", right)),
            self.eq(self.app("bucket", left), self.app("bucket", right)))

    def used_shape(self, shape, record):
        return self.quantify("exists", ((record, "Record"),), self.conjunction(
            self.pred("is_output", record),
            self.eq(self.app("shape", record), self.var(shape, "Shape"))))


def _fol_root(kind, f):
    if kind == "exact_once":
        coverage = f.quantify("forall", (("r", "Record"),), f.imply(
            f.pred("is_input", "r"),
            f.quantify("exists", (("o", "Record"),), f.conjunction(
                f.pred("is_output", "o"), f.matching("r", "o"),
                f.quantify("forall", (("p", "Record"),), f.imply(
                    f.conjunction(f.pred("is_output", "p"), f.matching("r", "p")),
                    f.eq(f.var("p"), f.var("o"))))))))
        no_invented = f.quantify("forall", (("o", "Record"),), f.imply(
            f.pred("is_output", "o"),
            f.quantify("exists", (("r", "Record"),), f.conjunction(
                f.pred("is_input", "r"), f.matching("r", "o")))))
        input_unique = f.quantify("forall", (("r", "Record"), ("s", "Record")), f.imply(
            f.conjunction(f.pred("is_input", "r"), f.pred("is_input", "s"), f.matching("r", "s")),
            f.eq(f.var("r"), f.var("s"))))
        return f.conjunction(coverage, no_invented, input_unique)
    if kind == "batch_shape_equality":
        return f.quantify("forall", (("o", "Record"), ("p", "Record")), f.imply(
            f.conjunction(f.pred("is_output", "o"), f.pred("is_output", "p"),
                f.eq(f.app("bucket", "o"), f.app("bucket", "p")),
                f.eq(f.app("batch", "o"), f.app("batch", "p"))),
            f.eq(f.app("shape", "o"), f.app("shape", "p"))))
    if kind == "global_shape_cap":
        names = ["s" + str(i) for i in range(9)]
        nodes = [f.used_shape(name, "record" + str(i)) for i, name in enumerate(names)]
        nodes += [f.negate(f.eq(f.var(names[i], "Shape"), f.var(names[j], "Shape")))
                  for i in range(9) for j in range(i + 1, 9)]
        return f.negate(f.quantify("exists", tuple((name, "Shape") for name in names),
                                  f.conjunction(*nodes)))
    if kind == "input_unchanged":
        return f.quantify("forall", (("file", "FilePath"),), f.imply(
            f.pred("is_input_file", "file", "FilePath"),
            f.eq(f.app("before", "file", "FilePath"),
                 f.app("after", "file", "FilePath"))))
    raise ConstraintProjectionError("unsupported FOL constraint kind")


def _walk_fol(node):
    yield node
    for child in node.arguments:
        yield from _walk_fol(child)


def _closed_fol(root):
    """Native typed expressions allow typed free variables; this profile does not."""
    seen = 0

    def check(node, bound, depth):
        nonlocal seen
        seen += 1
        if type(node) is not fol.LogicNode or seen > 1024 or depth > 32:
            raise ConstraintProjectionError("bounded native closed FOL tree required")
        local = dict(bound)
        for binder in node.binders:
            if binder.name in local:
                raise ConstraintProjectionError("shadowed native FOL binder")
            local[binder.name] = binder.sort
        if node.kind is fol.NodeKind.VARIABLE:
            if node.symbol not in local or node.sort != local[node.symbol]:
                raise ConstraintProjectionError("free or wrong-sort native FOL variable")
        for child in node.arguments:
            check(child, local, depth + 1)

    check(root, {}, 0)


def _fol_projection(clause, contract_sha256):
    f = _FOL()
    root = _fol_root(clause["kind"], f)
    _closed_fol(root)
    expression = fol.TypedExpression(
        "scheduler-expression:" + clause["kind"], root, f.signature,
        metadata={"contract_sha256": contract_sha256, "clause_sha256": _sha(clause),
                  "requirement_id": clause["requirement_id"],
                  "status": "source_bound_interpretation_candidate",
                  "proof_authority": False, "interpretation_correspondence_proved": False})
    # Independent native serialization/elaboration is exercised, not just a
    # caller-supplied typecheck flag or a string that resembles a formula.
    payload = expression.to_dict()
    if _wire(fol.TypedExpression.from_dict(payload).to_dict()) != _wire(payload):
        raise ConstraintProjectionError("native typed expression round trip differs")
    kinds = {}
    for node in _walk_fol(expression.root):
        kinds[node.kind.value] = kinds.get(node.kind.value, 0) + 1
    return {"requirement_id": clause["requirement_id"], "kind": clause["kind"],
            "family_id": "first_order", "profile_id": "many_sorted",
            "clause_sha256": _sha(clause), "source_spans": clause["source_spans"],
            "typed_expression": payload, "native_elaboration_executed": True,
            "native_round_trip_checked": True, "operator_counts": kinds,
            "candidate_asserted_true": False, **FALSE}


def _sort_name(sort):
    if type(sort) is not smt.SmtSort or sort.arity != 0 or sort.parameters:
        raise ConstraintProjectionError("scalar native SMT sort required")
    if sort.name not in {"Bool", "Int", "Record", "Measurement"}:
        raise ConstraintProjectionError("unsupported native SMT sort")
    return sort.name


def validate_integer_term(term, *, declarations, bound=None):
    """Strict adapter checker before native compilation; no RAW/REAL escape.

    Declarations are native SmtFunDecl objects.  No parsed text is trusted as a
    typed term.  Multiplication/division/modulo are the bounded constant forms
    used here; a successful check is not a satisfiability or proof result.
    """
    if type(declarations) not in (tuple, list) or len(declarations) > 32:
        raise ConstraintProjectionError("bounded native declarations required")
    symbols = {}
    for declaration in declarations:
        if type(declaration) is not smt.SmtFunDecl or not _NAME.fullmatch(declaration.name):
            raise ConstraintProjectionError("safe native declaration required")
        if declaration.name in symbols:
            raise ConstraintProjectionError("duplicate native declaration")
        symbols[declaration.name] = (tuple(_sort_name(v) for v in declaration.domain),
                                     _sort_name(declaration.range))
    locals_ = {} if bound is None else dict(bound)
    if any(type(k) is not str or not _NAME.fullmatch(k) or v not in {
            "Bool", "Int", "Record", "Measurement"} for k, v in locals_.items()):
        raise ConstraintProjectionError("closed bound variable sorts required")
    if set(symbols) & set(locals_):
        raise ConstraintProjectionError("bound symbol shadows declaration")
    visited = 0

    def inspect(node, local, depth):
        nonlocal visited
        visited += 1
        if type(node) is not smt.SmtTerm or visited > 1024 or depth > 32:
            raise ConstraintProjectionError("bounded exact native SMT term required")
        kind = node.kind.value
        args = node.arguments
        if type(node.value) is not str:
            raise ConstraintProjectionError("exact native term value required")
        if kind == "int":
            if (args or node.binders or not _INT.fullmatch(node.value)
                    or len(node.value) > 20 or abs(int(node.value)) > MAX_INTEGER):
                raise ConstraintProjectionError("bounded canonical exact integer required")
            result = "Int"
        elif kind == "symbol":
            if args or node.binders or not _NAME.fullmatch(node.value):
                raise ConstraintProjectionError("declared scalar variable required")
            if node.value in local:
                result = local[node.value]
            elif node.value in symbols and not symbols[node.value][0]:
                result = symbols[node.value][1]
            else:
                raise ConstraintProjectionError("undeclared native scalar")
        elif kind == "apply":
            if node.binders or node.value not in symbols:
                raise ConstraintProjectionError("undeclared native function")
            domain, result = symbols[node.value]
            if len(args) != len(domain) or tuple(inspect(v, local, depth + 1) for v in args) != domain:
                raise ConstraintProjectionError("native function arity or argument sort differs")
        elif kind in {"forall", "exists"}:
            if node.value or len(args) != 1 or not 0 < len(node.binders) <= 12:
                raise ConstraintProjectionError("closed bounded native quantifier required")
            nested = dict(local)
            for binder in node.binders:
                if (type(binder) is not smt.SmtBinder or not _NAME.fullmatch(binder.name)
                        or binder.name in nested or binder.name in symbols):
                    raise ConstraintProjectionError("duplicate or shadowed native binder")
                nested[binder.name] = _sort_name(binder.sort)
            if inspect(args[0], nested, depth + 1) != "Bool":
                raise ConstraintProjectionError("quantifier body must be Boolean")
            result = "Bool"
        else:
            if node.value or node.binders:
                raise ConstraintProjectionError("unexpected native operator payload")
            kinds = tuple(inspect(v, local, depth + 1) for v in args)
            if kind == "not" and kinds == ("Bool",):
                result = "Bool"
            elif kind in {"and", "or"} and 2 <= len(kinds) <= 64 and set(kinds) == {"Bool"}:
                result = "Bool"
            elif kind == "implies" and kinds == ("Bool", "Bool"):
                result = "Bool"
            elif kind == "eq" and len(kinds) == 2 and kinds[0] == kinds[1]:
                result = "Bool"
            elif kind in {"lt", "le", "gt", "ge"} and kinds == ("Int", "Int"):
                result = "Bool"
            elif kind in {"add", "sub"} and kinds == ("Int", "Int"):
                result = "Int"
            elif kind == "mul" and kinds == ("Int", "Int") and any(v.kind is smt.SmtTermKind.INT for v in args):
                result = "Int"
            elif (kind in {"div", "mod"} and kinds == ("Int", "Int")
                    and args[1].kind is smt.SmtTermKind.INT and int(args[1].value) > 0):
                result = "Int"
            else:
                raise ConstraintProjectionError("unsupported operator, arity, or sort")
        if node.sort is not None and _sort_name(node.sort) != result:
            raise ConstraintProjectionError("native term annotation sort differs")
        return result

    return inspect(term, locals_, 0)


def _t(kind, *arguments):
    return smt.SmtTerm(kind, arguments=tuple(arguments))


def _i(value):
    if type(value) is not int or not -MAX_INTEGER <= value <= MAX_INTEGER:
        raise ConstraintProjectionError("bounded exact integer required")
    return smt.SmtTerm("int", value=str(value))


def _a(function, variable):
    return smt.SmtTerm("apply", value=function,
                       arguments=(smt.SmtTerm("symbol", value=variable),))


def _domain(term, *, positive=False):
    return (_t("gt" if positive else "ge", term, _i(0)),
            _t("le", term, _i(MAX_INTEGER)))


def _compile_smt(clause, contract_sha256, *, metric=None):
    functions, custom = [], []
    if clause["kind"] == "shape_alignment":
        parameters = clause["parameters"]
        if parameters != {"granularity": 64, "heads_align": 32, "hidden_align": 4096}:
            raise ConstraintProjectionError("closed scheduler shape semantics required")
        carrier = smt.SmtSort("Record")
        custom.append(carrier)
        functions = [smt.SmtFunDecl("is_output", (carrier,), smt.BOOL_SORT)]
        fields = ("prompt_len", "seq_align", "heads_align", "hidden_align")
        functions += [smt.SmtFunDecl(name, (carrier,), smt.INT_SORT) for name in fields]
        terms = {name: _a(name, "row") for name in fields}
        minimum = _t("mul", _i(64), _t("div", _t("add", terms["prompt_len"], _i(63)), _i(64)))
        constraints = [v for name in fields for v in _domain(terms[name])]
        constraints += [_t("eq", _t("mod", terms["seq_align"], _i(64)), _i(0)),
                        _t("ge", terms["seq_align"], minimum),
                        _t("eq", terms["heads_align"], _i(32)),
                        _t("eq", terms["hidden_align"], _i(4096))]
        body = _t("implies", _a("is_output", "row"), _t("and", *constraints))
        goal = smt.SmtTerm("forall", arguments=(body,),
                           binders=(smt.SmtBinder("row", carrier),))
        interpretation = "Record denotes individual input/output occurrences; is_output selects plan rows. prompt_len is the matching bucket-qualified input prompt. seq_align/heads_align/hidden_align are that row's concrete fields. The input/output matching and field bridge is required and unproved."
        suffix = "shape_alignment"
    elif clause["kind"] == "thresholds":
        parameters = clause["parameters"]
        if (parameters["bucket_id"] not in (1, 2) or parameters["comparison"] != "strict_lt"
                or metric not in parameters["metrics"]):
            raise ConstraintProjectionError("closed bucket strict threshold required")
        threshold = parameters["metrics"][metric]
        numerator, denominator = threshold["numerator"], threshold["denominator"]
        if type(numerator) is not int or type(denominator) is not int or denominator <= 0:
            raise ConstraintProjectionError("positive-denominator exact rational threshold required")
        carrier = smt.SmtSort("Measurement")
        custom.append(carrier)
        selector = "is_bucket_" + str(parameters["bucket_id"]) + "_" + metric
        functions = [smt.SmtFunDecl(selector, (carrier,), smt.BOOL_SORT),
                     smt.SmtFunDecl("numerator", (carrier,), smt.INT_SORT),
                     smt.SmtFunDecl("denominator", (carrier,), smt.INT_SORT)]
        n, d = _a("numerator", "measurement"), _a("denominator", "measurement")
        constraints = [*_domain(n), *_domain(d, positive=True),
                       _t("lt", _t("mul", _i(denominator), n),
                          _t("mul", _i(numerator), d))]
        goal = smt.SmtTerm("forall", binders=(smt.SmtBinder("measurement", carrier),),
            arguments=(_t("implies", _a(selector, "measurement"), _t("and", *constraints)),))
        interpretation = "Measurement denotes exact numerator/positive-denominator observations for the named bucket and metric. The selector chooses that metric's actual measurement, not arbitrary integer pairs. Cross multiplication is exact Int arithmetic. Derivation from cost_model/runtime, and correspondence to finite-case measurements, remain unproved."
        suffix = "bucket_" + str(parameters["bucket_id"]) + "_" + metric
    else:
        raise ConstraintProjectionError("unsupported numeric constraint")
    if validate_integer_term(goal, declarations=functions) != "Bool":
        raise ConstraintProjectionError("Boolean native SMT goal required")
    attributes = {"contract_sha256": contract_sha256, "clause_sha256": _sha(clause),
                  "requirement_id": clause["requirement_id"], "metric": metric,
                  "source_spans": clause["source_spans"], "candidate_asserted_true": False,
                  "interpretation_correspondence_proved": False}
    obligation = smt.SmtObligation(
        obligation_id="scheduler-constraint:" + suffix,
        query_mode=smt.SmtQueryMode.SATISFIABILITY,
        features=(smt.SmtFeature.ARITHMETIC, smt.SmtFeature.EQUALITY, smt.SmtFeature.QUANTIFIERS),
        goal=goal, functions=tuple(functions), sorts=tuple(custom),
        property_ids=(clause["requirement_id"],), attributes=attributes)
    compilation = smt.SoftwareVerificationSMTCompiler().compile(obligation)
    return {"requirement_id": clause["requirement_id"], "kind": clause["kind"],
            "metric": metric, "clause_sha256": _sha(clause),
            "source_spans": clause["source_spans"],
            "target_namespace_id": smt.SMT_TARGET_FAMILY_ID,
            "source_namespace_id": smt.SMT_SOURCE_FAMILY_ID,
            "namespace_role": "native_compiler_translation_labels_not_canonical_semantic_families",
            "interpretation": interpretation,
            "obligation": obligation.to_dict(), "compilation": compilation.to_dict(),
            "adapter_sort_check_executed": True, "native_compiler_executed": True,
            "candidate_asserted_true": False, **FALSE}


def build_constraint_projections(*, contract):
    """Replay the closed source-bound contract and compile actual native IRs."""
    _validate_contract(contract)
    contract_sha256 = _sha(contract)
    first_order, numeric, losses = [], [], []
    for clause in contract["clauses"]:
        kind = clause["kind"]
        if kind in {"exact_once", "global_shape_cap", "batch_shape_equality", "input_unchanged"}:
            first_order.append(_fol_projection(clause, contract_sha256))
        elif kind == "shape_alignment":
            numeric.append(_compile_smt(clause, contract_sha256))
        elif kind == "thresholds":
            for metric in sorted(clause["parameters"]["metrics"]):
                numeric.append(_compile_smt(clause, contract_sha256, metric=metric))
        elif kind == "input_schema":
            losses.append({"requirement_id": clause["requirement_id"],
                           "source_spans": clause["source_spans"],
                           "reason": "finite_schema_validation_is_retained_in_the_contract; no proof that observed bytes instantiate these mathematical carriers"})
        else:
            raise ConstraintProjectionError("unsupported scheduler clause")
    report = {"schema": SCHEMA, "contract_sha256": contract_sha256,
              "head_sha256": _sha(contract["head"]),
              "instruction_sha256": contract["instruction"]["sha256"],
              "families": ["first_order"], "status": "source_bound_candidates_compiled",
              "native_translation_namespaces": {"source": smt.SMT_SOURCE_FAMILY_ID,
                  "target": smt.SMT_TARGET_FAMILY_ID,
                  "role": "retained_native_SMT_compiler_labels; not canonical semantic family routes"},
              "first_order": first_order, "smt": numeric, "losses": losses,
              "interpretation": {
                  "record_identity": "distinct finite row occurrences; equality is occurrence identity, never mere request-id equality",
                  "request_identity": "request-id strings qualified by input/output bucket; repeated IDs in different buckets are distinct requests",
                  "batch_identity": "batch-id strings qualified by bucket",
                  "shape_identity": "extensional (seq_align,heads_align,hidden_align) integer tuple equality across both buckets",
                  "bytes": "exact captured UTF-8 input bytes before and after; equal observations do not prove uninterrupted immutability",
                  "sorts": "abstract typed carriers and explicitly selected input/output members; generated syntax does not observe or verify these interpretations",
                  "bridge": "Finite contract evaluator, FOL carriers and SMT field interpretations are independently stated. Their semantic correspondence to each other, Lean and source execution remains unproved."},
              "limitations": [
                  "IntentIR complete original-task semantic coverage remains unsupported; these candidates do not change admission.",
                  "The maximum-shape formula forbids nine pairwise distinct used shapes; it asserts no witness, nonempty carrier, or execution fact.",
                  "SMT declarations use actual Int operators with bounded literals and positive constant divisors; compilation is not solving or proof.",
                  "Numeric domains are the explicitly bounded experiment, not a claim about unbounded task inputs.",
                  "Native family route/typecheck and translation receipts grant no task, model, runtime or execution authority."],
              "producer_pins": [{"path": path, "sha256": hashlib.sha256(Path(path).read_bytes()).hexdigest()}
                                for path in producer_paths()],
              "provider_calls": 0, "training_executed": False, **FALSE}
    report["report_sha256"] = _sha(report)
    return report


def validate_constraint_projections(report, *, contract):
    """Full deterministic replay, including source bindings and native receipts."""
    if type(report) is not dict:
        raise ConstraintProjectionError("exact candidate report required")
    expected = build_constraint_projections(contract=contract)
    try:
        same = _wire(report) == _wire(expected)
    except (TypeError, ValueError, RecursionError) as error:
        raise ConstraintProjectionError("bounded canonical candidate report required") from error
    if not same:
        raise ConstraintProjectionError("native constraint projection differs from source-bound replay")
    return report


__all__ = ["build_constraint_projections", "validate_constraint_projections",
           "validate_integer_term", "producer_paths", "ConstraintProjectionError"]
