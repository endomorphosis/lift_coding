"""Closed, byte-cited AST inventory for the public scheduler cost model.

Only the pinned public file is accepted.  Parsing a file into Python AST nodes
does not execute it or prove that a separately written evaluator implements
Python.  The profile retains both decimal-token and binary64 interpretations
so downstream calculations must state which one they use.
"""
from __future__ import annotations

import ast
import base64
from decimal import Decimal
from fractions import Fraction
import hashlib
import json
import math

SCHEMA = "terminal-source-derived-scheduler-profile@1"
EXPECTED_SOURCE_PATH = "llm-inference-batching-scheduler/environment/task_file/scripts/cost_model.py"
EXPECTED_SOURCE_BYTES = 8096
EXPECTED_SOURCE_SHA256 = "0cf417fd5ff0112defcd46970d37a290c0763c5a9092e91cb3ebb86c3f20e6ce"
EXPECTED_AST_SHA256 = "98785b7b730642925facce20e4a222b8f5df81ef17f0026bf7b0513064fc5201"
DEFAULTS = {"HEADS": 32, "HIDDEN": 4096, "granularity": 64}
DOMAIN = {"max_prompt_len": 4096, "max_gen_len": 1024,
          "max_seq_align": 8192, "max_rows_per_bucket": 256}
LITERALS = {
    "Kp_attn": "2.0", "Kp_mlp": "1.0", "Kd_attn": "1.0",
    "Kd_mlp": "0.5", "Tp_attn": "0.002", "Tp_mlp": "0.0015",
    "Td_attn": "0.0012", "Td_mlp": "0.0006", "Kshape_attn": "500.0",
    "Kshape_mlp": "2.0", "Tshape_compile_ms": "1500.0",
    "Kbatch_overhead_cost": "10_000_000.0", "Tbatch_overhead_ms": "8.0",
}
FUNCTION_AST_PINS = {
    "align": "77e103782a7752530177eda70353ddf890db6a05061ec6bdc17b41150d0d5875",
    "CostModel.__init__": "a90df5fdf88c49d3e6486f4acb40ea8eadacb91a1403a4ee629a526d697fe0b3",
    "CostModel._prefill_cost": "728c84958ce11ca09d189918afb15e3e63d0884253ceb4e3818fdfa9952f0e08",
    "CostModel._prefill_lat": "d76d1f978eb3b40a1a701be788deb6c5932103cf9310cdf677a680cde5f19de1",
    "CostModel._decode_step_cost": "32f3893f90690c051aa210120edfabb1ae24b503631a145c3f72375d68ff2d39",
    "CostModel._decode_step_lat": "b11a3570c48cd2625ef58199a3cc292a6ca41cca21dca18147465f299c104fac",
    "CostModel._sum_sq_arith": "1632925525c9ec76109d1c9f8b0048fd909eadbaf05d53d705cc2801fad0193e",
    "CostModel.batch_metrics": "3c8e2250f16a20cbe6b068b10ce3ae5d8638f9945d40e91aa09a298ff658051e",
    "CostModel.plan_metrics": "1f03c0162e1cb68271c874d774bf4e71607ad885f6f0a1ca4c845e4886903831",
    "CostModel._calculate_sequential_timecost": "6b32a1d4d8e7eed46c8891e2c9d079dceaa4434bb100e9ca7326af8291fdf646",
    "CostModel.pxx_latency": "56f6e08f71faad3e4812d22d4d9841a51b8912693a1995741eaf3120eb05ca6e",
}
FALSE_CLAIMS = {
    "source_body_execution": False,
    "ast_to_runtime_equivalence_proved": False,
    "decimal_and_binary64_equivalent": False,
    "runtime_metrics_observed": False,
    "original_semantic_coverage_complete": False,
    "full_task_satisfaction_proved": False,
    "source_model_equivalence_proved": False,
    "formal_proof": False,
    "convergence_proved": False,
    "planning_or_dispatch_authority": False,
}
_HEAD_FIELDS = {"schema", "repository_id", "snapshot_cid", "manifest_cid",
                "receipt_cid", "ast_revision_id", "generation"}


class SourceProfileError(ValueError):
    """The supplied source/profile is outside this one closed profile."""


def _sha(raw):
    return hashlib.sha256(raw).hexdigest()


def _ast(node):
    return ast.dump(node, annotate_fields=True, include_attributes=False)


def _plain(value, depth=0, count=None):
    if count is None:
        count = [0]
    count[0] += 1
    if count[0] > 65536 or depth > 32:
        raise SourceProfileError("profile exceeds the plain-JSON structural bound")
    if value is None or type(value) in (bool, int):
        if type(value) is int and value.bit_length() > 128:
            raise SourceProfileError("profile integer exceeds its representation bound")
        return
    if type(value) is str:
        try:
            raw = value.encode("utf-8", "strict")
        except UnicodeError as exc:
            raise SourceProfileError("profile contains a non-scalar string") from exc
        if len(raw) > 131072:
            raise SourceProfileError("profile string exceeds its representation bound")
        return
    if type(value) is list and len(value) <= 4096:
        for item in value:
            _plain(item, depth + 1, count)
        return
    if type(value) is dict and len(value) <= 4096 and all(type(k) is str for k in value):
        for key, item in value.items():
            _plain(key, depth + 1, count)
            _plain(item, depth + 1, count)
        return
    raise SourceProfileError("profile must contain bounded plain JSON without floats")


def _wire(value):
    _plain(value)
    raw = json.dumps(value, sort_keys=True, separators=(",", ":"),
                     ensure_ascii=True, allow_nan=False).encode("ascii")
    if len(raw) > 2 * 1024 * 1024:
        raise SourceProfileError("profile exceeds its serialized bound")
    return raw


def _head(head):
    if type(head) is not dict or set(head) != _HEAD_FIELDS:
        raise SourceProfileError("head must be one complete native codebase-head descriptor")
    if head.get("schema") != "codebase-head@1":
        raise SourceProfileError("unknown codebase-head schema")
    if type(head.get("generation")) is not int or not 1 <= head["generation"] <= 10**9:
        raise SourceProfileError("head generation must be a positive bounded integer")
    for name in _HEAD_FIELDS - {"generation"}:
        value = head[name]
        if type(value) is not str or not value:
            raise SourceProfileError("head string is absent or exceeds its representation bound")
        try:
            encoded = value.encode("utf-8", "strict")
        except UnicodeError as exc:
            raise SourceProfileError("head contains a non-scalar string") from exc
        if len(encoded) > 1024:
            raise SourceProfileError("head string exceeds its representation bound")
    return json.loads(_wire(head))


def _ratio(value):
    return {"numerator": value.numerator, "denominator": value.denominator}


def build_source_profile(raw: bytes, *, source_path: str = EXPECTED_SOURCE_PATH,
                         head: dict) -> dict:
    """Inventory supplied source bytes; no filesystem access or source imports.

    The caller must separately establish that ``head`` is current and that
    ``raw`` is the actual file belonging to that native owner.
    """
    if type(raw) is not bytes or len(raw) != EXPECTED_SOURCE_BYTES:
        raise SourceProfileError("the complete pinned public source bytes are required")
    if type(source_path) is not str or source_path != EXPECTED_SOURCE_PATH:
        raise SourceProfileError("source path is outside the pinned scheduler profile")
    if _sha(raw) != EXPECTED_SOURCE_SHA256:
        raise SourceProfileError("whole source SHA256 differs from the retained public source")
    checked_head = _head(head)
    text = raw.decode("utf-8", "strict")
    tree = ast.parse(text, filename=source_path, mode="exec", type_comments=False)
    ast_sha = _sha(_ast(tree).encode("utf-8"))
    if ast_sha != EXPECTED_AST_SHA256:
        raise SourceProfileError("Python AST profile differs from the retained closed grammar")
    offsets = [0]
    for line in raw.splitlines(keepends=True):
        offsets.append(offsets[-1] + len(line))

    def citation(node):
        start = offsets[node.lineno - 1] + node.col_offset
        end = offsets[node.end_lineno - 1] + node.end_col_offset
        segment = raw[start:end]
        return {"source_span": {"start_byte": start, "end_byte": end},
                "source_sha256": _sha(segment), "source_text": segment.decode("utf-8"),
                "ast_sha256": _sha(_ast(node).encode("utf-8"))}

    classes = {node.name: node for node in tree.body if type(node) is ast.ClassDef}
    if set(classes) != {"CostConsts", "CostModel"}:
        raise SourceProfileError("source classes differ from the pinned profile")
    const_nodes = classes["CostConsts"].body
    if len(const_nodes) != len(LITERALS):
        raise SourceProfileError("exactly thirteen default cost constants are required")
    constants = {}
    for node in const_nodes:
        if (type(node) is not ast.AnnAssign or type(node.target) is not ast.Name
                or type(node.annotation) is not ast.Name or node.annotation.id != "float"
                or type(node.value) is not ast.Constant or type(node.value.value) is not float):
            raise SourceProfileError("cost defaults must be direct annotated float literals")
        name = node.target.id
        item = citation(node.value)
        literal = item.pop("source_text")
        if LITERALS.get(name) != literal or not math.isfinite(node.value.value):
            raise SourceProfileError("cost default token differs from the thirteen pinned constants")
        binary = Fraction(*node.value.value.as_integer_ratio())
        constants[name] = {
            "literal": literal, "decimal_ratio": _ratio(Fraction(Decimal(literal.replace("_", "")))),
            "binary64_ratio": _ratio(binary), "binary64_hex": node.value.value.hex(), **item,
        }
    if set(constants) != set(LITERALS):
        raise SourceProfileError("cost defaults have missing or repeated names")
    source_defaults = {node.target.id: node.value.value for node in tree.body
                       if type(node) is ast.AnnAssign and type(node.target) is ast.Name
                       and type(node.value) is ast.Constant}
    if source_defaults != {"HEADS": 32, "HIDDEN": 4096}:
        raise SourceProfileError("HEADS and HIDDEN differ from their pinned defaults")

    functions = {}
    formula_nodes, control_nodes, call_nodes = [], [], []

    def visit(node, scope=""):
        current = scope
        if isinstance(node, (ast.ClassDef, ast.FunctionDef)):
            current = (scope + "." if scope else "") + node.name
        if type(node) is ast.FunctionDef:
            record = citation(node)
            record.pop("source_text")
            record.update({"name": current, "signature_ast": _ast(node.args),
                           "decorators_ast": [_ast(item) for item in node.decorator_list]})
            functions[current] = record
        if isinstance(node, (ast.Assign, ast.AnnAssign, ast.AugAssign, ast.Return)):
            formula_nodes.append({"scope": current, "kind": type(node).__name__, **citation(node)})
        if isinstance(node, (ast.If, ast.For, ast.IfExp, ast.comprehension)):
            # Comprehensions do not have their own complete location metadata.
            located = node if hasattr(node, "lineno") else node.iter
            control_nodes.append({"scope": current, "kind": type(node).__name__,
                                  "control_ast": _ast(node), **citation(located)})
        if type(node) is ast.Call:
            call_nodes.append({"scope": current, "callee_ast": _ast(node.func), **citation(node)})
        for child in ast.iter_child_nodes(node):
            visit(child, current)

    visit(tree)
    for name, expected in FUNCTION_AST_PINS.items():
        if functions.get(name, {}).get("ast_sha256") != expected:
            raise SourceProfileError("a pinned source method body differs")
    if set(functions) != set(FUNCTION_AST_PINS) | {
            "CostModel.batch_metrics.sum_cost_for_g", "CostModel.batch_metrics.sum_lat_for_g"}:
        raise SourceProfileError("source contains an unexpected callable")
    return {
        "schema": SCHEMA, "source_path": source_path, "source_bytes": len(raw),
        "source_sha256": _sha(raw), "source_payload_b64": base64.b64encode(raw).decode("ascii"),
        "head": checked_head, "head_sha256": _sha(_wire(checked_head)),
        "ast_format": "python-ast.dump-annotate_fields-true-include_attributes-false@1",
        "ast_sha256": ast_sha, "constants": constants, "defaults": dict(DEFAULTS),
        "domain": dict(DOMAIN), "functions": functions, "formula_nodes": formula_nodes,
        "control_nodes": control_nodes, "call_nodes": call_nodes,
        "interpretations": {
            "decimal": "exact rational arithmetic over decimal literal tokens; not Python runtime equivalence",
            "binary64": "exact binary64 literal values retained; ordered shadow calculations require their own evidence",
            "granularity": "64 is an explicit supported caller profile, not a CostModel constructor default",
        },
        "source_sensitive_decisions": {
            "request_order": "plan row encounter order within each bucket-local batch",
            "batch_order": "insertion order for batch metrics; sorted batch identifiers for sequential time and latency flattening",
            "batch_context": "maximum aligned request prompt, not the declared plan sequence shape",
            "generation_context": "maximum raw generation length; generation is not aligned",
            "declared_shape": "last declaration wins per batch in source; a separate scheduler contract checks shape consistency",
            "compile_cost": "unique declared shape tuples per bucket; source iterates a set; sequence <= 0 skips cost only",
            "compile_latency": "first request in lexicographically first batch for each declared shape, including zero sequence shape",
            "padding": "aligned prompt padding plus generation-to-batch-maximum padding, divided by max(1, real tokens)",
            "percentile": "sorted latencies at clamp(ceil(binary64(0.95) * count) - 1)",
            "sum": "source builtin sum has host Python implementation semantics; exact cost under bounded integer intermediates is a separate argument",
            "division": "source / uses binary64; // uses integer floor; decimal interpretation replaces / with exact rational division",
            "constants": "default CostConsts only; supplied overrides are unsupported",
        },
        "claims": dict(FALSE_CLAIMS),
    }


def validate_source_profile(report, *, raw: bytes, source_path: str = EXPECTED_SOURCE_PATH,
                            head: dict) -> bool:
    """Rebuild every source citation and field against separately supplied inputs."""
    actual = _wire(report)
    expected = _wire(build_source_profile(raw, source_path=source_path, head=head))
    if actual != expected:
        raise SourceProfileError("retained profile differs from the complete source-derived rebuild")
    return True


def validate_source_profile_shape(report) -> bool:
    """Validate retained data against the one source pin, without freshness claims."""
    _wire(report)
    if type(report) is not dict or type(report.get("source_payload_b64")) is not str:
        raise SourceProfileError("profile must retain its pinned source payload")
    encoded = report["source_payload_b64"]
    if len(encoded) > 11000:
        raise SourceProfileError("source payload exceeds its closed bound")
    try:
        raw = base64.b64decode(encoded, validate=True)
    except (ValueError, TypeError) as exc:
        raise SourceProfileError("source payload is not canonical base64") from exc
    if base64.b64encode(raw).decode("ascii") != encoded:
        raise SourceProfileError("source payload is not canonical base64")
    return validate_source_profile(report, raw=raw, source_path=report.get("source_path"),
                                   head=report.get("head"))
