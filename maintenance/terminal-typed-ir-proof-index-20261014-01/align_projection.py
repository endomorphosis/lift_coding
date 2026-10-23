"""Exact-source scheduler alignment fragment and bounded native Lean checks.

The admitted mathematical domain is built-in integers with g = 64. Source
annotations, captured bytes, parsed ASTs and native ProgramIR are provenance
observations, not a proof of CPython execution or physical source origin.
"""
from __future__ import annotations

import ast
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import re

SCHEMA = "terminal-alignment-typed-projection@1"
PROFILE = "python-align-int-positive-granularity-64@1"
MAX_SOURCE_BYTES = 262144
MAX_AST_NODES = 32768
MAX_RECORD_BYTES = 16000000
AUTHORITY = {name: False for name in (
    "proof_authority", "execution_authority", "completion_authority",
    "formalization_authority", "source_semantics_verified",
    "source_origin_proved", "source_parser_correctness_proved",
    "cpython_equivalence_proved", "source_model_equivalence_proved",
    "whole_program_semantics_verified", "full_task_satisfaction_proved",
    "optimizer_convergence_proved", "training_convergence_proved",
    "training_executed", "learned_latents_as_predicates")}


class AlignmentProjectionError(ValueError):
    """The exact source, admitted grammar, native correspondence or check differs."""


def _need(condition, message):
    if not condition:
        raise AlignmentProjectionError(message)


def _wire(value):
    try:
        result = json.dumps(value, sort_keys=True, separators=(",", ":"),
            ensure_ascii=False, allow_nan=False).encode("utf-8")
    except (TypeError, ValueError, UnicodeError, RecursionError) as exc:
        raise AlignmentProjectionError("bounded finite ordinary JSON required") from exc
    _need(len(result) <= MAX_RECORD_BYTES, "projection record exceeds bound")
    return result


def _copy(value):
    return json.loads(_wire(value))


def _sha(raw):
    return hashlib.sha256(raw).hexdigest()


def _source(source_bytes, source_path, source_sha256):
    _need(type(source_bytes) is bytes and 0 < len(source_bytes) <= MAX_SOURCE_BYTES,
        "bounded exact source bytes required")
    _need(type(source_path) is str and bool(source_path) and len(source_path) <= 1024
        and "\\" not in source_path and "\x00" not in source_path,
        "canonical relative source path required")
    path = PurePosixPath(source_path)
    _need(not path.is_absolute() and str(path) == source_path and path.suffix == ".py"
        and all(part not in {".", "..", ".git"} for part in path.parts),
        "canonical relative Python source path required")
    _need(type(source_sha256) is str and re.fullmatch(r"[0-9a-f]{64}", source_sha256)
        and _sha(source_bytes) == source_sha256, "exact parent source SHA-256 differs")
    try:
        text = source_bytes.decode("utf-8")
        tree = ast.parse(text, filename=source_path, type_comments=True)
    except (UnicodeError, SyntaxError, ValueError, RecursionError) as exc:
        raise AlignmentProjectionError("bounded UTF-8 Python AST required") from exc
    _need(sum(1 for _ in ast.walk(tree)) <= MAX_AST_NODES, "source AST exceeds bound")
    functions = [item for item in tree.body if type(item) is ast.FunctionDef and item.name == "align"]
    _need(len(functions) == 1, "one original top-level align function required")
    function = functions[0]
    # Reject module rebinding: the fragment is the declared original function,
    # not an arbitrary last-writer interpretation of the name `align`.
    for node in tree.body:
        if node is function:
            continue
        targets = []
        if isinstance(node, (ast.Assign, ast.AnnAssign, ast.AugAssign)):
            targets = node.targets if isinstance(node, ast.Assign) else [node.target]
        _need(not any(isinstance(part, ast.Name) and part.id == "align"
            for target in targets for part in ast.walk(target)), "module rebinds align")
        _need(not isinstance(node, (ast.AsyncFunctionDef, ast.ClassDef)) or node.name != "align",
            "module redefines align")
    args = function.args
    annotated = lambda node: type(node) is ast.Name and node.id == "int"
    _need(not function.decorator_list and not function.type_comment
        and not getattr(function, "type_params", ()) and annotated(function.returns)
        and len(args.args) == 2 and [arg.arg for arg in args.args] == ["x", "g"]
        and all(annotated(arg.annotation) and not arg.type_comment for arg in args.args)
        and not args.posonlyargs and not args.kwonlyargs and not args.vararg
        and not args.kwarg and not args.defaults and not args.kw_defaults
        and len(function.body) == 1 and type(function.body[0]) is ast.Return,
        "closed typed two-argument single-return align syntax required")
    return text, tree, function


def _source_tree(node, depth=0):
    _need(depth <= 16, "source expression depth exceeds bound")
    if type(node) is ast.Name and node.id in {"x", "g"}:
        return {"kind": "parameter", "index": 0 if node.id == "x" else 1, "type": "Int"}
    if type(node) is ast.Constant and type(node.value) is int and node.value.bit_length() <= 32:
        return {"kind": "literal", "value": node.value, "type": "Int"}
    if type(node) is ast.BinOp and type(node.op) in {ast.Add, ast.Sub, ast.Mult, ast.FloorDiv}:
        kind = {ast.Add: "add", ast.Sub: "sub", ast.Mult: "mul", ast.FloorDiv: "floor_div"}[type(node.op)]
        return {"kind": kind, "left": _source_tree(node.left, depth + 1),
            "right": _source_tree(node.right, depth + 1), "type": "Int"}
    raise AlignmentProjectionError("expression is outside the closed integer alignment grammar")


def _expected_tree():
    parameter = lambda index: {"kind": "parameter", "index": index, "type": "Int"}
    binary = lambda kind, left, right: {"kind": kind, "left": left, "right": right, "type": "Int"}
    return binary("mul", binary("floor_div", binary("sub", binary("add", parameter(0), parameter(1)),
        {"kind": "literal", "value": 1, "type": "Int"}), parameter(1)), parameter(1))


def _native_tree(program):
    _need(type(program) is dict, "native ProgramIR required")
    functions = [row for row in program["functions"] if row["name"] == "align"]
    _need(len(functions) == 1, "native align function missing or ambiguous")
    function = functions[0]
    symbols = {row["symbol_id"]: row for row in program["symbols"]}
    parameters = function["parameter_symbol_ids"]
    _need(len(parameters) == 2 and [symbols[key]["name"] for key in parameters] == ["x", "g"]
        and all(symbols[key]["type_ref"] == "int" for key in parameters)
        and function["return_type"] == "int" and not function["local_symbol_ids"]
        and not function["cfg"]["edges"] and len(function["cfg"]["blocks"]) == 1,
        "native typed align signature or control-flow differs")
    command_ids = function["cfg"]["blocks"][0]["command_ids"]
    commands = {row["command_id"]: row for row in program["commands"]}
    _need(len(command_ids) == 1 and command_ids[0] in commands,
        "one native return command required")
    command = commands[command_ids[0]]
    _need(command["kind"] == "return" and len(command["expression_ids"]) == 1,
        "native return command differs")
    expressions = {row["expression_id"]: row for row in program["expressions"]}
    active, used = set(), set()
    def visit(key, depth=0):
        _need(depth <= 16 and key in expressions and key not in active,
            "bounded acyclic native expression graph required")
        active.add(key)
        used.add(key)
        row = expressions[key]
        _need(row["type_ref"] in {"any", "int"}, "native expression is outside integer profile")
        if row["kind"] == "symbol":
            _need(len(row["symbol_ids"]) == 1 and row["symbol_ids"][0] in parameters
                and not row["operand_ids"] and not row["evaluation_order"]
                and not row["operator"] and not row["attributes"], "native parameter differs")
            result = {"kind": "parameter", "index": parameters.index(row["symbol_ids"][0]), "type": "Int"}
        elif row["kind"] == "literal":
            _need(set(row["attributes"]) == {"value"} and type(row["attributes"]["value"]) is int
                and not row["operand_ids"] and not row["evaluation_order"]
                and not row["symbol_ids"] and not row["operator"], "native integer literal differs")
            result = {"kind": "literal", "value": row["attributes"]["value"], "type": "Int"}
        else:
            _need(row["kind"] == "binary" and row["operator"] in {"add", "sub", "mul", "floordiv"}
                and len(row["operand_ids"]) == 2 and not row["symbol_ids"] and not row["attributes"]
                and row["evaluation_order"] == row["operand_ids"], "native integer operation differs")
            result = {"kind": "floor_div" if row["operator"] == "floordiv" else row["operator"],
                "left": visit(row["operand_ids"][0], depth + 1),
                "right": visit(row["operand_ids"][1], depth + 1), "type": "Int"}
        active.remove(key)
        return result
    return visit(command["expression_ids"][0]), sorted(used), function, command


def evaluate_alignment(*, projection, x, granularity=64):
    """Evaluate our mathematical Int IR; never evaluate or import target source."""
    _need(type(x) is int and type(granularity) is int and granularity == 64,
        "exact integer x and positive profile granularity 64 required")
    _checked_projection(projection)
    def visit(tree):
        kind = tree["kind"]
        if kind == "parameter":
            return x if tree["index"] == 0 else granularity
        if kind == "literal":
            return tree["value"]
        left, right = visit(tree["left"]), visit(tree["right"])
        if kind == "add": return left + right
        if kind == "sub": return left - right
        if kind == "mul": return left * right
        _need(kind == "floor_div" and right > 0, "only positive floor division is admitted")
        return left // right
    return visit(projection["typed_ir"]["target_expression"])


def project_alignment(*, source_bytes: bytes, source_path: str, source_sha256: str) -> dict:
    """Produce deterministic exact-source candidate IR; no checker is invoked."""
    from ipfs_datasets_py.logic.software_verification.codebase_source_adapters import adapt_source_to_software_verification
    text, _, function = _source(source_bytes, source_path, source_sha256)
    source_syntax = _source_tree(function.body[0].value)
    _need(_wire(source_syntax) == _wire(_expected_tree()), "original alignment expression differs")
    offsets = [0]
    offsets.extend(index + 1 for index, value in enumerate(source_bytes) if value == 10)
    start = offsets[function.lineno - 1] + function.col_offset
    end = offsets[function.end_lineno - 1] + function.end_col_offset
    extracted = source_bytes[start:end]
    try:
        reparsed = ast.parse(extracted.decode("utf-8"), type_comments=True)
    except (SyntaxError, UnicodeError) as exc:
        raise AlignmentProjectionError("exact function byte extraction does not parse") from exc
    _need(len(reparsed.body) == 1 and type(reparsed.body[0]) is ast.FunctionDef
        and ast.dump(reparsed.body[0], include_attributes=False) == ast.dump(function, include_attributes=False),
        "original source extraction AST differs")
    adapted = adapt_source_to_software_verification(text, path=source_path, language="python",
        revision="sha256:" + source_sha256, max_source_bytes=MAX_SOURCE_BYTES,
        include_supervisor_evidence=False, preserve_type_annotations=True)
    native = _copy(adapted.to_dict())
    _need(native["program"] is not None and native["fake_backend_success"] is False,
        "actual native structural ProgramIR missing")
    target_syntax, expression_ids, function_ir, command_ir = _native_tree(native["program"])
    _need(_wire(source_syntax) == _wire(target_syntax), "independent original AST and native target differ")
    sources = native["program"]["sources"]
    _need(len(sources) == 1 and sources[0]["content_sha256"] == source_sha256
        and sources[0]["source_revision"] == "sha256:" + source_sha256
        and sources[0]["metadata"]["path"] == source_path,
        "native complete-parent source binding differs")
    result = {"schema": SCHEMA, "profile": PROFILE,
        "source": {"path": source_path, "sha256": source_sha256, "bytes": len(source_bytes),
            "function_name": "align", "function_bytes_sha256": _sha(extracted),
            "start_byte": start, "end_byte": end, "start_line": function.lineno,
            "end_line": function.end_lineno, "start_column_utf8": function.col_offset,
            "end_column_utf8": function.end_col_offset,
            "function_source": extracted.decode("utf-8"),
            "extraction_relation": "exact_parent_utf8_byte_slice_and_equal_attribute_free_parsed_AST"},
        "typed_ir": {"schema": "terminal-closed-int-expression@1",
            "parameters": [{"index": 0, "name": "x", "type": "Int"},
                {"index": 1, "name": "g", "type": "Int"}], "result_type": "Int",
            "source_expression": source_syntax, "target_expression": target_syntax,
            "native_expression_ids": expression_ids,
            "native_function_id": function_ir["function_id"],
            "native_return_command_id": command_ir["command_id"]},
        "native_full_file_adapter": native,
        "native_full_file_adapter_sha256": _sha(_wire(native)),
        "unsupported_residuals": native["unsupported_constructs"],
        "assumptions": {"x": "mathematical integer; runtime annotation does not establish input type",
            "granularity": 64, "positive_divisor": True,
            "division": "Lean Int Euclidean quotient, equal to mathematical floor for positive divisor",
            "scope": "one original pure arithmetic AST fragment; complete parent module is not modeled",
            "excluded": ["zero or negative granularity", "bool and overloaded Python objects",
                "CPython execution and exceptions", "module imports and initialization",
                "resource exhaustion", "all other functions and unsupported parent regions"]},
        "model_claims": {"source_ast_target_correspondence_observed": True,
            "kernel_checked_lowering": False, "kernel_checked_rounding_properties": False},
        **AUTHORITY}
    result["projection_id"] = _sha(_wire(result))
    return _copy(result)


def _checked_projection(projection):
    _need(type(projection) is dict and projection.get("schema") == SCHEMA
        and projection.get("profile") == PROFILE, "exact typed alignment projection required")
    value = _copy(projection)
    identity = value.pop("projection_id", None)
    _need(type(identity) is str and _sha(_wire(value)) == identity, "alignment projection identity differs")
    _need(all(value.get(key) is False for key in AUTHORITY), "projection authority differs")
    source = value.get("source")
    _need(type(source) is dict and type(source.get("function_source")) is str,
        "exact source extraction record required")
    _need(_sha(source["function_source"].encode()) == source.get("function_bytes_sha256"),
        "extracted function byte digest differs")
    try:
        _, _, extracted_function = _source(source["function_source"].encode(),
            source["path"], source["function_bytes_sha256"])
    except (KeyError, TypeError) as error:
        raise AlignmentProjectionError("complete extracted-source binding required") from error
    _need(_wire(_source_tree(extracted_function.body[0].value)) == _wire(_expected_tree()),
        "extracted original function expression differs")
    _need(value.get("assumptions", {}).get("granularity") == 64
        and type(value["assumptions"]["granularity"]) is int
        and value["assumptions"].get("positive_divisor") is True,
        "only positive granularity-64 profile admitted")
    ir = value.get("typed_ir", {})
    _need(_wire(ir.get("source_expression")) == _wire(_expected_tree())
        and _wire(ir.get("target_expression")) == _wire(_expected_tree()),
        "closed alignment source or target expression differs")
    native = value.get("native_full_file_adapter")
    _need(type(native) is dict and _sha(_wire(native)) == value.get("native_full_file_adapter_sha256"),
        "native complete-file artifact digest differs")
    from ipfs_datasets_py.logic.software_verification.program import ProgramIR
    try:
        ProgramIR.from_dict(native["program"])
    except (TypeError, ValueError, KeyError) as error:
        raise AlignmentProjectionError("native ProgramIR validation differs") from error
    target, ids, function, command = _native_tree(native["program"])
    _need(_wire(target) == _wire(ir["target_expression"])
        and ids == ir["native_expression_ids"] and function["function_id"] == ir["native_function_id"]
        and command["command_id"] == ir["native_return_command_id"]
        and value.get("unsupported_residuals") == native["unsupported_constructs"],
        "native target or complete residual binding differs")
    parents = native["program"]["sources"]
    _need(len(parents) == 1 and parents[0]["content_sha256"] == source["sha256"]
        and parents[0]["source_revision"] == "sha256:" + source["sha256"]
        and parents[0]["metadata"]["path"] == source["path"]
        and parents[0]["metadata"]["byte_length"] == source["bytes"]
        and native.get("fake_backend_success") is False,
        "native complete parent identity differs")
    spans = {row["span_id"]: row for row in native["program"]["spans"]}
    _need(len(function["span_ids"]) == 1 and function["span_ids"][0] in spans,
        "native original function span required")
    span = spans[function["span_ids"][0]]
    _need(all(type(source.get(key)) is int for key in ("bytes", "start_byte", "end_byte",
        "start_line", "end_line", "start_column_utf8", "end_column_utf8"))
        and 0 <= source["start_byte"] < source["end_byte"] <= source["bytes"]
        and source["end_byte"] - source["start_byte"] == len(source["function_source"].encode())
        and span["start_byte"] == source["start_byte"] and span["end_byte"] == source["end_byte"]
        and span["start_line"] == source["start_line"] and span["end_line"] == source["end_line"]
        and span["start_column"] == source["start_column_utf8"] + 1
        and span["end_column"] == max(1, source["end_column_utf8"]),
        "native and original extracted byte/line spans differ")
    _need(value.get("model_claims") == {"source_ast_target_correspondence_observed": True,
        "kernel_checked_lowering": False, "kernel_checked_rounding_properties": False},
        "candidate projection cannot claim a checked theorem")
    return _copy(projection)


def validate_alignment_projection(*, source_bytes: bytes, source_path: str,
        source_sha256: str, expected: dict) -> dict:
    """Recompute complete native projection against exact caller-supplied bytes."""
    _checked_projection(expected)
    observed = project_alignment(source_bytes=source_bytes, source_path=source_path,
        source_sha256=source_sha256)
    _need(_wire(observed) == _wire(expected), "complete source-bound alignment projection replay differs")
    return {"schema": "terminal-alignment-projection-validation@1", "verified": True,
        "projection_id": observed["projection_id"], "source": observed["source"],
        "validation_scope": "exact source/AST/native ProgramIR replay; no execution or proof authority",
        **AUTHORITY}


def _lean_tree(tree, prefix):
    kind = tree["kind"]
    if kind == "parameter": return f"({prefix}.parameter {tree['index']})"
    if kind == "literal": return f"({prefix}.literal ({tree['value']} : Int))"
    constructor = "floorDiv" if kind == "floor_div" and prefix == "SourceExpr" else "ediv" if kind == "floor_div" else kind
    return f"({prefix}.{constructor} {_lean_tree(tree['left'], prefix)} {_lean_tree(tree['right'], prefix)})"


def _lean_sources(projection):
    source = _lean_tree(projection["typed_ir"]["source_expression"], "SourceExpr")
    target = _lean_tree(projection["typed_ir"]["target_expression"], "TargetExpr")
    common = '''import Init
namespace TerminalAlignment
set_option autoImplicit false

inductive SourceExpr where
  | parameter (index : Nat)
  | literal (value : Int)
  | add (left right : SourceExpr)
  | sub (left right : SourceExpr)
  | mul (left right : SourceExpr)
  | floorDiv (left right : SourceExpr)

inductive TargetExpr where
  | parameter (index : Nat)
  | literal (value : Int)
  | add (left right : TargetExpr)
  | sub (left right : TargetExpr)
  | mul (left right : TargetExpr)
  | ediv (left right : TargetExpr)

-- Both functions define mathematical integer semantics; no CPython theorem.
-- Euclidean quotient agrees with floor only for positive divisors. The concrete
-- admitted alignment denominator is always 64; zero/negative g are excluded.
def sourceEval : SourceExpr → (Nat → Int) → Int
  | .parameter index, env => env index
  | .literal value, _ => value
  | .add left right, env => sourceEval left env + sourceEval right env
  | .sub left right, env => sourceEval left env - sourceEval right env
  | .mul left right, env => sourceEval left env * sourceEval right env
  | .floorDiv left right, env => sourceEval left env / sourceEval right env

def targetEval : TargetExpr → (Nat → Int) → Int
  | .parameter index, env => env index
  | .literal value, _ => value
  | .add left right, env => targetEval left env + targetEval right env
  | .sub left right, env => targetEval left env - targetEval right env
  | .mul left right, env => targetEval left env * targetEval right env
  | .ediv left right, env => targetEval left env / targetEval right env

def lower : SourceExpr → TargetExpr
  | .parameter index => .parameter index
  | .literal value => .literal value
  | .add left right => .add (lower left) (lower right)
  | .sub left right => .sub (lower left) (lower right)
  | .mul left right => .mul (lower left) (lower right)
  | .floorDiv left right => .ediv (lower left) (lower right)

theorem closed_integer_lowering_correct (expression : SourceExpr) (env : Nat → Int) :
    targetEval (lower expression) env = sourceEval expression env := by
  induction expression <;> simp_all [lower, sourceEval, targetEval]
'''
    common += f"\ndef projectionIdentity : String := \"{projection['projection_id']}\"\n"
    common += f"def parentSourceSHA256 : String := \"{projection['source']['sha256']}\"\n"
    common += f"def capturedSourceExpression : SourceExpr := {source}\n"
    common += f"def nativeTargetExpression : TargetExpr := {target}\n"
    common += '''
theorem native_target_correspondence : nativeTargetExpression = lower capturedSourceExpression := by rfl

theorem captured_ast_target_equivalence (env : Nat → Int) :
    targetEval nativeTargetExpression env = sourceEval capturedSourceExpression env := by
  rw [native_target_correspondence]
  exact closed_integer_lowering_correct capturedSourceExpression env

def inputs (x : Int) (index : Nat) : Int := if index = 0 then x else 64
def run (x : Int) : Int := targetEval nativeTargetExpression (inputs x)
'''
    positive = common + '''
theorem alignment_rounding_bounds : ∀ x : Int, x ≤ run x ∧ run x < x + 64 := by
  intro x
  simp [run, nativeTargetExpression, targetEval, inputs]
  omega

theorem alignment_divisible : ∀ x : Int, run x % 64 = 0 := by
  intro x
  simp [run, nativeTargetExpression, targetEval, inputs]

theorem alignment_negative_input : run (-65) = -64 := by decide
theorem alignment_zero_input : run 0 = 0 := by decide
#print axioms closed_integer_lowering_correct
#print axioms native_target_correspondence
#print axioms captured_ast_target_equivalence
#print axioms alignment_rounding_bounds
#print axioms alignment_divisible
#print axioms alignment_negative_input
#print axioms alignment_zero_input
end TerminalAlignment
'''
    negative = common + '''
-- Deliberately false: truncation toward zero replaces positive floor division.
theorem incorrect_truncation_control : run (-65) = 0 := by decide
end TerminalAlignment
'''
    wrong_offset = common + '''
-- Deliberately false: alignment is incorrectly shifted by one full granule.
theorem incorrect_offset_control : run 0 = 64 := by decide
end TerminalAlignment
'''
    return [("Alignment.lean", positive, True),
        ("IncorrectTruncation.lean", negative, False),
        ("IncorrectOffset.lean", wrong_offset, False)]


def _write(path, value):
    with path.open("xb") as stream:
        stream.write(_wire(value))
        stream.flush()
        os.fsync(stream.fileno())


def _compile_alignment_lean(*, executable, filename, source, output, expected_success):
    """A separate bounded semantic-proof profile retains complete larger oleans."""
    from ipfs_datasets_py.logic.backends.process import BoundedToolRunner, ToolRunRequest, ToolRunLimits
    raw_source = source.encode("utf-8")
    with (output / filename).open("xb") as stream:
        stream.write(raw_source)
    pin = {"path": str(output / filename), "sha256": _sha(raw_source), "bytes": len(raw_source)}
    object_file = str(PurePosixPath(filename).with_suffix(".olean"))
    command = ((str(executable), "-j", "1", "-o", object_file, filename) if expected_success
        else (str(executable), "-j", "1", filename))
    executable_pin = _sha(executable.read_bytes())
    # The semantic lowering object is larger than the predecessor's recorded-
    # loss object. This declared profile uses 1 MiB, without accepting truncation.
    limits = ToolRunLimits(timeout_seconds=20, cpu_seconds=20,
        max_input_bytes=262144, max_output_bytes=1048576,
        max_workspace_bytes=16 * 1024 * 1024)
    run = BoundedToolRunner().run(ToolRunRequest(argv=command,
        input_files={filename: source}, output_paths=(object_file,) if expected_success else (),
        limits=limits))
    executable_unchanged = _sha(executable.read_bytes()) == executable_pin
    exact_command = tuple(run.command) == command
    bounded_result = (not any((run.timed_out, run.cancelled, run.unavailable,
        run.resource_exhausted, run.output_truncated, run.workspace_limit_exceeded))
        and executable_unchanged and exact_command)
    passed = run.ok and bounded_result
    rejected = (run.returncode is not None and run.returncode != 0 and bounded_result
        and "Tactic `decide` proved that the proposition" in run.stdout and "is false" in run.stdout)
    artifacts = []
    for name, raw in run.output_files.items():
        with (output / name).open("xb") as stream:
            stream.write(raw)
        artifacts.append({"path": str(output / name), "sha256": _sha(raw), "bytes": len(raw)})
    if expected_success and not artifacts:
        passed = False
    return {"schema": "terminal-codebase-lean-check@1", "file": filename, "artifact": pin,
        "status": "passed" if passed else "rejected" if rejected else "inconclusive",
        "expected_success": expected_success, "matches_expectation": passed if expected_success else rejected,
        "compiled_artifacts": artifacts, "backend_executed": run.pid is not None, "pid": run.pid,
        "executable": str(executable), "executable_sha256": executable_pin,
        "executable_unchanged": executable_unchanged,
        "requested_command": list(command), "command": list(run.command), "exact_command": exact_command,
        "lean_threads": 1, "limits": {"timeout_seconds": limits.timeout_seconds,
            "cpu_seconds": limits.cpu_seconds, "max_input_bytes": limits.max_input_bytes,
            "max_output_bytes": limits.max_output_bytes, "max_workspace_bytes": limits.max_workspace_bytes},
        "returncode": run.returncode, "stdout": run.stdout, "stderr": run.stderr,
        "timed_out": run.timed_out, "cancelled": run.cancelled, "unavailable": run.unavailable,
        "output_truncated": run.output_truncated, "workspace_limit_exceeded": run.workspace_limit_exceeded,
        "resource_exhausted": run.resource_exhausted, "workspace_cleaned": run.workspace_cleaned,
        "termination_reason": run.termination_reason, "error": run.error,
        "elapsed_seconds": run.elapsed_seconds,
        "process_profile": "terminal-alignment-semantic-lean-single-thread-1MiB@1",
        "proof_scope": "closed_mathematical_integer_AST_lowering_and_original_alignment_fragment_g64", **AUTHORITY}


def compile_alignment_proofs(*, projection: dict, output: Path, lean_executable: Path) -> dict:
    """Run real bounded -j1 Lean checks and retain every completed diagnostic."""
    value = _checked_projection(projection)
    _need(type(output) is Path or isinstance(output, Path), "fresh external output Path required")
    _need(output.is_absolute() and output.resolve() == output and not output.exists()
        and output.parent.is_dir(), "fresh canonical output directory required")
    _need(isinstance(lean_executable, Path) and lean_executable.is_absolute()
        and lean_executable.resolve() == lean_executable and lean_executable.is_file(),
        "canonical installed Lean executable required")
    output.mkdir(mode=0o700)
    _write(output / "projection.json", value)
    checks = []
    _write(output / "process-policy.json", {"lean_threads": 1, "timeout_seconds": 20,
        "cpu_seconds": 20, "max_input_bytes": 262144, "max_output_bytes": 1048576,
        "max_workspace_bytes": 16 * 1024 * 1024,
        "source_execution": False, "runner": "ipfs_datasets_py.logic.backends.process.BoundedToolRunner",
        "process_profile": "terminal-alignment-semantic-lean-single-thread-1MiB@1"})
    for number, (filename, source, expected_success) in enumerate(_lean_sources(value), 1):
        try:
            checked = _compile_alignment_lean(executable=lean_executable, filename=filename,
                source=source, output=output, expected_success=expected_success)
            checked["proof_scope"] = "closed_mathematical_integer_AST_lowering_and_original_alignment_fragment_g64"
            checked.update(AUTHORITY)
        except Exception as error:
            diagnostic = {"schema": "terminal-alignment-runner-error@1", "file": filename,
                "class": type(error).__name__, "message": str(error)[:8192],
                "process_result_observed": False, "matches_expectation": False, **AUTHORITY}
            _write(output / f"check-{number:02d}-runner-error.json", diagnostic)
            raise AlignmentProjectionError("bounded Lean runner failed; diagnostic retained") from error
        _write(output / f"check-{number:02d}.json", checked)
        checks.append(checked)
    qualified = all(check["matches_expectation"] is True for check in checks)
    result = {"schema": "terminal-alignment-lean-proof-report@1", "profile": PROFILE,
        "projection_id": value["projection_id"], "source": value["source"],
        "qualified": qualified, "checks": checks, "native_lean_processes": len(checks),
        "positive_compiles": sum(check["expected_success"] and check["status"] == "passed" for check in checks),
        "false_controls_rejected": sum(not check["expected_success"] and check["status"] == "rejected" for check in checks),
        "theorems": ["closed_integer_lowering_correct", "native_target_correspondence",
            "captured_ast_target_equivalence", "alignment_rounding_bounds", "alignment_divisible",
            "alignment_negative_input", "alignment_zero_input"],
        "mathematical_fragment_claims": {"kernel_checked_lowering": qualified,
            "kernel_checked_g64_rounding_bounds": qualified, "kernel_checked_g64_divisibility": qualified},
        "proof_scope": "defined closed Int grammar and source-bound alignment fragment at g64",
        "trust_boundary": "Lean Init; frontend parsing/extraction/native adapter and source capture remain unproved",
        "unsupported_residuals": value["unsupported_residuals"], **AUTHORITY}
    _write(output / "proof-report.json", result)
    _need(qualified, "alignment proof or false control inconclusive; all process diagnostics retained")
    return result
