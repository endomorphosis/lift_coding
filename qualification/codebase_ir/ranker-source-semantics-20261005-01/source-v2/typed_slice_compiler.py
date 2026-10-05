"""Bounded, inert AST translation of two pinned ranker numeric expressions.

This module never opens files, imports project code, or executes source ASTs.
Its backend is an explicit exact-real projection, not Python/Float semantics.
"""
import ast
import hashlib
import json
import math
import re
from fractions import Fraction


SOURCE_SHA256 = "3661027d12c40002db6cd0766fcc834619a956a67bda8c844aba820d3389263a"
DOT_AST_SHA256 = "3ff8d47ab6f2e375b3bd4b81c6a39e364cd5a15ec859ca383b5e41504250de1e"
TRAINING_AST_SHA256 = "5b87aa5ce21daf1439ed8d51f37557e6aba962130fd4f8732d149cea7ca2ac5a"
DIFFERENCE_SHA256 = "d2b691805cddd5ba8a46f733589e4d09424a06d67a6a2bb09b61e7f727d9c739"
MAX_SOURCE_BYTES = 262144
MAX_MODULE_NODES = 4096
MAX_SLICE_NODES = 512
MAX_DEPTH = 32
MAX_SCALAR_NODES = 128
MAX_INTEGER_BITS = 256
MAX_RECEIPT_BYTES = 65536
_NAME = re.compile(r"[A-Za-z_][A-Za-z_0-9]{0,63}\Z")
_HEX = re.compile(r"[0-9a-f]{64}\Z")


class CompileRefusal(ValueError):
    """A closed-schema, source-pin, shape, or unsupported-syntax refusal."""


def _need(ok, reason):
    if ok is not True:
        raise CompileRefusal(reason)


def _exact_keys(value, keys, reason):
    _need(type(value) is dict and set(value) == set(keys), reason)


def _name(value):
    _need(type(value) is str and _NAME.fullmatch(value) is not None, "invalid name")
    return value


def _cap(value, maximum, label):
    _need(type(value) is int and 1 <= value <= maximum, "invalid " + label)
    return value


def _hash(value):
    _need(type(value) is str and _HEX.fullmatch(value) is not None, "invalid digest")
    return value


def _ast_sha(node):
    return hashlib.sha256(ast.dump(node, include_attributes=False).encode()).hexdigest()


def _ast_bounds(node, nodes, depth):
    _need(isinstance(node, ast.AST), "AST required")
    todo, count = [(node, 1)], 0
    while todo:
        current, level = todo.pop()
        count += 1
        _need(count <= nodes and level <= depth, "AST budget exceeded")
        for child in ast.iter_child_nodes(current):
            _need(count + len(todo) < nodes, "AST pending-node budget exceeded")
            todo.append((child, level + 1))
    return count


def _scope(bindings):
    _need(type(bindings) is dict and 1 <= len(bindings) <= 8, "closed lexical scope required")
    for name, slot in bindings.items():
        _name(name)
        _need(type(slot) is int and 0 <= slot < len(bindings), "invalid lexical slot")
    _need(set(bindings.values()) == set(range(len(bindings))), "duplicate lexical slots")
    return dict(bindings)


def _number(value):
    _need(type(value) in (int, float), "only real numeric constants accepted")
    if type(value) is float:
        _need(math.isfinite(value), "nonfinite constant")
        numerator, denominator = value.as_integer_ratio()
    else:
        numerator, denominator = value, 1
    _need(abs(numerator).bit_length() <= MAX_INTEGER_BITS and denominator.bit_length() <= MAX_INTEGER_BITS,
          "numeric literal budget exceeded")
    return {"kind": "num", "numerator": str(numerator), "denominator": str(denominator)}


def compile_scalar_ast(node, bindings, *, max_nodes=MAX_SCALAR_NODES, max_depth=MAX_DEPTH):
    """Lower a closed Name/Constant/Add/Sub/Mul tree, with explicit lexical slots."""
    scope = _scope(bindings)
    max_nodes = _cap(max_nodes, MAX_SCALAR_NODES, "scalar node cap")
    max_depth = _cap(max_depth, MAX_DEPTH, "depth cap")
    _ast_bounds(node, max_nodes, max_depth)

    def lower(current):
        if type(current) is ast.Name:
            _need(type(current.ctx) is ast.Load and current.id in scope, "unbound or non-load name")
            return {"kind": "var", "slot": scope[current.id]}
        if type(current) is ast.Constant:
            return _number(current.value)
        if type(current) is ast.BinOp:
            op = {ast.Add: "add", ast.Sub: "sub", ast.Mult: "mul"}.get(type(current.op))
            _need(op is not None, "unsupported scalar operator")
            return {"kind": op, "left": lower(current.left), "right": lower(current.right)}
        raise CompileRefusal("unsupported scalar AST: " + type(current).__name__)

    result = {"schema": "ranker-typed-scalar-ir@1", "slots": len(scope), "body": lower(node)}
    validate_scalar_ir(result)
    return result


def validate_scalar_ir(ir):
    """Validate all keys/types and bounds before interpreting or rendering any IR."""
    _exact_keys(ir, ("schema", "slots", "body"), "scalar IR keys")
    _need(type(ir["schema"]) is str and ir["schema"] == "ranker-typed-scalar-ir@1", "scalar IR schema")
    slots = _cap(ir["slots"], 8, "slot count")
    todo, count = [(ir["body"], 1)], 0
    while todo:
        node, depth = todo.pop()
        count += 1
        _need(count <= MAX_SCALAR_NODES and depth <= MAX_DEPTH, "IR budget exceeded")
        _need(type(node) is dict and type(node.get("kind")) is str, "scalar node required")
        kind = node["kind"]
        if kind == "var":
            _exact_keys(node, ("kind", "slot"), "variable IR keys")
            _need(type(node["slot"]) is int and 0 <= node["slot"] < slots, "unbound IR slot")
        elif kind == "num":
            _exact_keys(node, ("kind", "numerator", "denominator"), "number IR keys")
            n, d = node["numerator"], node["denominator"]
            _need(type(n) is str and type(d) is str and len(n) <= 79 and len(d) <= 78,
                  "rational text budget")
            _need(re.fullmatch(r"0|-?[1-9][0-9]*", n) is not None and
                  re.fullmatch(r"[1-9][0-9]*", d) is not None, "noncanonical rational text")
            nn, dd = int(n), int(d)
            _need(abs(nn).bit_length() <= MAX_INTEGER_BITS and dd.bit_length() <= MAX_INTEGER_BITS,
                  "rational bit budget")
            q = Fraction(nn, dd)
            _need(q.numerator == nn and q.denominator == dd, "unreduced rational")
        elif kind in ("add", "sub", "mul"):
            _exact_keys(node, ("kind", "left", "right"), "binary IR keys")
            todo.extend(((node["right"], depth + 1), (node["left"], depth + 1)))
        else:
            raise CompileRefusal("unknown scalar IR kind")
    return True


def compile_zip_ast(node, *, kind, vector_names, binder_names, external_names=()):
    """Translate a single unfiltered zip comprehension; zip length is explicitly min."""
    _need(type(kind) is str and kind in ("zipFold", "zipMap"), "unsupported container kind")
    _need(type(vector_names) is tuple and type(binder_names) is tuple and
          len(vector_names) == len(binder_names) == 2 and type(external_names) is tuple,
          "closed zip scope")
    names = vector_names + binder_names + external_names
    for name in names:
        _name(name)
    _need(len(set(names)) == len(names) and len(external_names) <= 6, "shadowed zip binding")
    _need(type(node) is (ast.GeneratorExp if kind == "zipFold" else ast.ListComp), "wrong comprehension kind")
    _ast_bounds(node, MAX_SLICE_NODES, MAX_DEPTH)
    _need(len(node.generators) == 1, "multiple comprehension generators")
    generator = node.generators[0]
    _need(not generator.ifs and type(generator.is_async) is int and generator.is_async == 0, "filtered or async zip")
    target = generator.target
    _need(type(target) is ast.Tuple and type(target.ctx) is ast.Store and len(target.elts) == 2,
          "zip pair target required")
    _need(all(type(x) is ast.Name and type(x.ctx) is ast.Store for x in target.elts) and
          tuple(x.id for x in target.elts) == binder_names, "zip target binding mismatch")
    call = generator.iter
    _need(type(call) is ast.Call and type(call.func) is ast.Name and type(call.func.ctx) is ast.Load and
          call.func.id == "zip" and not call.keywords and len(call.args) == 2,
          "only positional two-input builtin zip accepted")
    _need(all(type(x) is ast.Name and type(x.ctx) is ast.Load for x in call.args) and
          tuple(x.id for x in call.args) == vector_names, "zip input binding mismatch")
    lexical = binder_names + external_names
    scalar = compile_scalar_ast(node.elt, {name: i for i, name in enumerate(lexical)})
    ir = {"schema": "ranker-typed-zip-ir@1", "kind": kind, "inputs": list(vector_names),
          "binders": list(binder_names), "externals": list(external_names),
          "zip_length": "min", "scalar": scalar}
    if kind == "zipFold":
        ir["fold"] = "ordered-real-sum"
    validate_zip_ir(ir)
    return ir


def validate_zip_ir(ir):
    _need(type(ir) is dict and type(ir.get("kind")) is str and ir.get("kind") in ("zipFold", "zipMap"), "zip IR kind")
    keys = {"schema", "kind", "inputs", "binders", "externals", "zip_length", "scalar"}
    if ir["kind"] == "zipFold":
        keys.add("fold")
    _exact_keys(ir, keys, "zip IR keys")
    _need(type(ir["schema"]) is str and ir["schema"] == "ranker-typed-zip-ir@1" and
          type(ir["zip_length"]) is str and ir["zip_length"] == "min", "zip IR semantics")
    _need(type(ir["inputs"]) is list and type(ir["binders"]) is list and type(ir["externals"]) is list and
          len(ir["inputs"]) == len(ir["binders"]) == 2 and len(ir["externals"]) <= 6, "zip IR scope")
    names = ir["inputs"] + ir["binders"] + ir["externals"]
    for name in names:
        _name(name)
    _need(len(set(names)) == len(names), "shadowed IR bindings")
    validate_scalar_ir(ir["scalar"])
    _need(ir["scalar"]["slots"] == 2 + len(ir["externals"]), "zip IR slot count")
    if ir["kind"] == "zipFold":
        _need(type(ir["fold"]) is str and ir["fold"] == "ordered-real-sum", "unknown fold interpretation")
    return True


def render_source_scalar(ir, names):
    """Render actual lowered constructors for the candidate Lean SourceScalar."""
    validate_scalar_ir(ir)
    _need(type(names) is tuple and len(names) == ir["slots"], "renderer scope")
    for name in names:
        _name(name)
    _need(len(set(names)) == len(names), "renderer shadowing")

    def render(node):
        if node["kind"] == "var":
            return "(.var " + json.dumps(names[node["slot"]]) + ")"
        if node["kind"] == "num":
            return "(.num ((" + node["numerator"] + " : ℚ) / (" + node["denominator"] + " : ℚ)))"
        return "(." + node["kind"] + " " + render(node["left"]) + " " + render(node["right"]) + ")"
    return render(ir["body"])


def validate_original_shape(*, dimension, weights_length, gradient_length,
                            difference_rows=4, difference_columns=80,
                            difference_artifact_sha256=DIFFERENCE_SHA256):
    """Check external shape/pin assumptions; this does not inspect or prove corpus preparation."""
    for value in (dimension, weights_length, gradient_length, difference_rows, difference_columns):
        _need(type(value) is int, "shape must contain exact integers")
    _need(dimension == weights_length == gradient_length == difference_columns == 80 and difference_rows == 4,
          "outside original fixed 80-coordinate, four-pair shape")
    _need(_hash(difference_artifact_sha256) == DIFFERENCE_SHA256, "original difference artifact drift")
    return True


def _function(module, name):
    matches = [n for n in module.body if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef)) and n.name == name]
    _need(len(matches) == 1 and type(matches[0]) is ast.FunctionDef, "unique synchronous function required")
    result = matches[0]
    _need(not result.decorator_list, "decorated function refused")
    return result


def _simple_call(node, name, count):
    _need(type(node) is ast.Call and type(node.func) is ast.Name and node.func.id == name and
          type(node.func.ctx) is ast.Load and len(node.args) == count and not node.keywords,
          "call context mismatch")


def compile_ranker_slices(source_bytes, expected_source_sha256, expected_dot_ast_sha256,
                          expected_training_ast_sha256, dimension=80, *,
                          weights_length=80, gradient_length=80, difference_rows=4,
                          difference_columns=80, difference_artifact_sha256=DIFFERENCE_SHA256,
                          max_source_bytes=MAX_SOURCE_BYTES, max_module_nodes=MAX_MODULE_NODES,
                          max_depth=MAX_DEPTH):
    """Compile only the pinned dot body and guarded train update expression.

    Raw source and lexical AST context are checked before lowering. Full context
    identity authenticates selection; it is not a semantics theorem for the context.
    """
    max_source_bytes = _cap(max_source_bytes, MAX_SOURCE_BYTES, "source byte cap")
    max_module_nodes = _cap(max_module_nodes, MAX_MODULE_NODES, "module node cap")
    max_depth = _cap(max_depth, MAX_DEPTH, "module depth cap")
    _need(type(source_bytes) is bytes and 0 < len(source_bytes) <= max_source_bytes, "source byte budget")
    _need(_hash(expected_source_sha256) == SOURCE_SHA256 and
          _hash(expected_dot_ast_sha256) == DOT_AST_SHA256 and
          _hash(expected_training_ast_sha256) == TRAINING_AST_SHA256, "unsupported original-source pins")
    _need(hashlib.sha256(source_bytes).hexdigest() == expected_source_sha256, "raw source digest mismatch")
    validate_original_shape(dimension=dimension, weights_length=weights_length, gradient_length=gradient_length,
                            difference_rows=difference_rows, difference_columns=difference_columns,
                            difference_artifact_sha256=difference_artifact_sha256)
    try:
        module = ast.parse(source_bytes, filename="<pinned-ranker-source>")
    except (SyntaxError, ValueError, RecursionError) as error:
        raise CompileRefusal("source parse refusal") from error
    module_nodes = _ast_bounds(module, max_module_nodes, max_depth)
    dot = _function(module, "_dot")
    training = _function(module, "train_terminal_codebase_intent_ranker")
    _need(_ast_sha(dot) == expected_dot_ast_sha256 and _ast_sha(training) == expected_training_ast_sha256,
          "selected/context AST digest mismatch")
    args = dot.args
    _need(not args.posonlyargs and not args.kwonlyargs and not args.defaults and not args.kw_defaults and
          args.vararg is None and args.kwarg is None and tuple(x.arg for x in args.args) == ("a", "b") and
          all(x.annotation is None for x in args.args) and dot.returns is None and dot.type_comment is None and
          len(dot.body) == 1 and type(dot.body[0]) is ast.Return, "dot function context mismatch")
    folded = dot.body[0].value
    _need(type(folded) is ast.Call and type(folded.func) is ast.Attribute and
          type(folded.func.value) is ast.Name and folded.func.value.id == "math" and
          folded.func.attr == "fsum" and len(folded.args) == 1 and not folded.keywords,
          "only source math.fsum wrapper accepted")
    dot_ir = compile_zip_ast(folded.args[0], kind="zipFold", vector_names=("a", "b"), binder_names=("x", "y"))
    _need(len(training.body) == 10 and type(training.body[5]) is ast.For, "training selection context")
    loop = training.body[5]
    _need(type(loop.target) is ast.Name and loop.target.id == "epoch" and not loop.orelse and len(loop.body) == 3,
          "epoch loop context mismatch")
    _simple_call(loop.iter, "range", 1)
    interval = loop.iter.args[0]
    _need(type(interval) is ast.BinOp and type(interval.op) is ast.Add and
          type(interval.left) is ast.Name and interval.left.id == "epochs" and
          type(interval.right) is ast.Constant and type(interval.right.value) is int and interval.right.value == 1,
          "epoch interval context mismatch")
    guard = loop.body[2]
    _need(type(guard) is ast.If and not guard.orelse and len(guard.body) == 2 and
          type(guard.test) is ast.Compare and type(guard.test.left) is ast.Name and guard.test.left.id == "epoch" and
          len(guard.test.ops) == len(guard.test.comparators) == 1 and type(guard.test.ops[0]) is ast.Lt and
          type(guard.test.comparators[0]) is ast.Name and guard.test.comparators[0].id == "epochs",
          "update guard context mismatch")
    assignment = guard.body[0]
    _need(type(assignment) is ast.Assign and len(assignment.targets) == 1 and
          type(assignment.targets[0]) is ast.Name and assignment.targets[0].id == "weights" and
          assignment.type_comment is None, "update assignment context mismatch")
    update_ir = compile_zip_ast(assignment.value, kind="zipMap", vector_names=("weights", "gradient"),
                                binder_names=("w", "g"), external_names=("step",))
    result = {"schema": "ranker-source-numeric-slices@1", "status": "compiled_source_only_kernel_pending",
              "source": {"bytes": len(source_bytes), "sha256": expected_source_sha256,
                         "module_ast_sha256": _ast_sha(module), "module_ast_nodes": module_nodes},
              "dimension": dimension, "external_shape_assumptions": {"weights_length": weights_length,
                  "gradient_length": gradient_length, "difference_rows": difference_rows,
                  "difference_columns": difference_columns, "difference_artifact_sha256": difference_artifact_sha256},
              "dot": {"path": "Module._dot.body[0].value.args[0]", "function_ast_sha256": _ast_sha(dot),
                      "expression_ast_sha256": _ast_sha(folded.args[0]), "ir": dot_ir,
                      "lean_source_scalar": render_source_scalar(dot_ir["scalar"], ("x", "y"))},
              "update": {"path": "Module.train_terminal_codebase_intent_ranker.body[5].body[2].body[0]",
                         "function_ast_sha256": _ast_sha(training), "loop_ast_sha256": _ast_sha(loop),
                         "guard_ast_sha256": _ast_sha(guard), "assignment_ast_sha256": _ast_sha(assignment),
                         "expression_ast_sha256": _ast_sha(assignment.value), "ir": update_ir,
                         "lean_source_scalar": render_source_scalar(update_ir["scalar"], ("w", "g", "step"))},
              "interpretation": "ordered finite-list exact-real projection; zip truncates to minimum input length",
              "open_frontiers": ["Python interpreter/evaluation/exception semantics", "binary64 arithmetic and math.fsum",
                  "full objective and gradient", "preparation/features/filter/validation/hash",
                  "full training initialization/loop/trace/receipts", "original shape provenance and corpus preparation",
                  "source interpreter refinement", "whole requested task and authority"],
              "source_shape_frontier_proved": False, "python_ranker_source_equivalence_proved": False,
              "binary64_error_bound_proved": False, "full_objective_semantics_proved": False,
              "full_training_semantics_proved": False, "kernel_compiler_correctness_qualified": False,
              "proof_authority": False, "execution_authority": False, "completion_authority": False,
              "planner_authority": False, "planner_activation": False, "authority_activation": False,
              "AE_authority": False, "global_autoencoder_convergence_proved": False,
              "full_task_satisfaction": "unknown", "official_benchmark_score": None}
    _need(len(json.dumps(result, sort_keys=True, separators=(",", ":")).encode()) <= MAX_RECEIPT_BYTES,
          "compiler receipt budget")
    return result


def render_generated_lean(compilation, source_bytes):
    """Emit candidate source gates from actual translated bodies, without file I/O.

    The kernel must check these gates separately. Host parsing/emission remains
    a trust frontier even after a successful native check.
    """
    _exact_keys(compilation, ("schema", "status", "source", "dimension", "external_shape_assumptions", "dot", "update",
        "interpretation", "open_frontiers", "source_shape_frontier_proved", "python_ranker_source_equivalence_proved",
        "binary64_error_bound_proved", "full_objective_semantics_proved", "full_training_semantics_proved",
        "kernel_compiler_correctness_qualified", "proof_authority", "execution_authority", "completion_authority",
        "planner_authority", "planner_activation", "authority_activation", "AE_authority",
        "global_autoencoder_convergence_proved", "full_task_satisfaction", "official_benchmark_score"), "emitter receipt keys")
    _need(type(compilation.get("schema")) is str and compilation["schema"] == "ranker-source-numeric-slices@1" and
          type(compilation.get("status")) is str and compilation["status"] == "compiled_source_only_kernel_pending",
          "compiler receipt required")
    for flag in ("source_shape_frontier_proved", "python_ranker_source_equivalence_proved", "binary64_error_bound_proved",
                 "full_objective_semantics_proved", "full_training_semantics_proved", "kernel_compiler_correctness_qualified",
                 "proof_authority", "execution_authority", "completion_authority", "planner_authority", "planner_activation",
                 "authority_activation", "AE_authority", "global_autoencoder_convergence_proved"):
        _need(compilation[flag] is False, "emitter scope flag")
    _need(type(compilation["full_task_satisfaction"]) is str and compilation["full_task_satisfaction"] == "unknown" and
          compilation["official_benchmark_score"] is None,
          "emitter full-task frontier")
    source = compilation.get("source")
    _exact_keys(source, ("bytes", "sha256", "module_ast_sha256", "module_ast_nodes"), "emitter source keys")
    _hash(source["module_ast_sha256"])
    _cap(source["module_ast_nodes"], MAX_MODULE_NODES, "emitter module nodes")
    _need(type(source["bytes"]) is int and source["bytes"] == 16391 and source.get("sha256") == SOURCE_SHA256,
          "emitter source identity")
    shape = compilation["external_shape_assumptions"]
    _exact_keys(shape, ("weights_length", "gradient_length", "difference_rows", "difference_columns",
                       "difference_artifact_sha256"), "emitter shape keys")
    validate_original_shape(dimension=compilation["dimension"], **shape)
    dot, update = compilation.get("dot"), compilation.get("update")
    _exact_keys(dot, ("path", "function_ast_sha256", "expression_ast_sha256", "ir", "lean_source_scalar"), "emitter dot keys")
    _exact_keys(update, ("path", "function_ast_sha256", "loop_ast_sha256", "guard_ast_sha256", "assignment_ast_sha256",
                        "expression_ast_sha256", "ir", "lean_source_scalar"), "emitter update keys")
    for part in (dot, update):
        for key, value in part.items():
            if key.endswith("sha256"):
                _hash(value)
    _need(dot.get("function_ast_sha256") == DOT_AST_SHA256 and
          update.get("function_ast_sha256") == TRAINING_AST_SHA256, "emitter context identity")
    validate_zip_ir(dot.get("ir"))
    validate_zip_ir(update.get("ir"))
    _need(dot["ir"]["kind"] == "zipFold" and dot["ir"]["binders"] == ["x", "y"] and
          dot["ir"]["inputs"] == ["a", "b"] and dot["ir"]["externals"] == [] and
          update["ir"]["kind"] == "zipMap" and update["ir"]["binders"] == ["w", "g"] and
          update["ir"]["inputs"] == ["weights", "gradient"] and update["ir"]["externals"] == ["step"],
          "emitter lexical scope")
    dot_body = render_source_scalar(dot["ir"]["scalar"], ("x", "y"))
    update_body = render_source_scalar(update["ir"]["scalar"], ("w", "g", "step"))
    _need(dot.get("lean_source_scalar") == dot_body and update.get("lean_source_scalar") == update_body,
          "emitter constructor binding")
    # Echoed digest strings cannot authenticate an untrusted or modified receipt.
    # Recompile the same byte buffer and compare the complete selected population.
    fresh = compile_ranker_slices(source_bytes, SOURCE_SHA256, DOT_AST_SHA256, TRAINING_AST_SHA256,
                                  dimension=compilation["dimension"], **shape)
    _need(compilation == fresh, "emitter complete same-source compilation binding")
    header = "-- SOURCE-ONLY CANDIDATE: original raw source SHA256 " + SOURCE_SHA256 + "\n"
    header += "-- dot expression AST SHA256 " + dot["expression_ast_sha256"] + "\n"
    header += "-- update assignment AST SHA256 " + update["assignment_ast_sha256"] + "\n"
    header += "-- update function context AST SHA256 " + TRAINING_AST_SHA256 + "\n"
    header += "-- No Python/Float, objective, preparation, or full training equivalence is asserted.\n"
    text = header + '''import TypedNumericSlice

namespace RankerSourceSemanticsGenerated
noncomputable section
open RankerSourceSemantics

def emittedDotBody : SourceScalar := ''' + dot_body + '''
def emittedUpdateBody : SourceScalar := ''' + update_body + '''

theorem emitted_dot_compiles :
    compile dotScope emittedDotBody = some compiledDotBody := by rfl

theorem emitted_update_compiles :
    compile updateScope emittedUpdateBody = some compiledUpdateBody := by rfl

theorem emitted_dot_compiler_commutes (environment : Fin 2 → ℝ) :
    (compile dotScope emittedDotBody).map (fun body => eval body environment) =
      evalSource (fun name => (dotScope name).map environment) emittedDotBody := by
  exact compile_eval_commutes dotScope environment emittedDotBody

theorem emitted_update_compiler_commutes (environment : Fin 3 → ℝ) :
    (compile updateScope emittedUpdateBody).map (fun body => eval body environment) =
      evalSource (fun name => (updateScope name).map environment) emittedUpdateBody := by
  exact compile_eval_commutes updateScope environment emittedUpdateBody

theorem emitted_dot_projection {m : ℕ} (left right : Fin m → ℝ) :
    runDotSource emittedDotBody (List.ofFn left) (List.ofFn right) =
      some (RankerRealCurvature.dot left right) := by
  exact source_dot_literal_eq emittedDotBody emitted_dot_compiles left right

theorem emitted_update_projection {m : ℕ} (step : ℝ) (weights gradient : Fin m → ℝ) :
    runUpdateSource emittedUpdateBody step (List.ofFn weights) (List.ofFn gradient) =
      some (List.ofFn (fun i => weights i - step * gradient i)) := by
  exact source_update_literal_eq emittedUpdateBody emitted_update_compiles step weights gradient

theorem emitted_originalRealStep_join (weights : Fin 80 → ℝ) :
    runUpdateSource emittedUpdateBody RankerRealCurvature.originalRealEta
      (List.ofFn weights)
      (List.ofFn (RankerRealCurvature.realCoordinateGradient
        RankerRealCurvature.originalRealMu RankerRealCurvature.originalRealDifferences weights)) =
      some (List.ofFn (RankerRealCurvature.realGradientStep
        RankerRealCurvature.originalRealMu RankerRealCurvature.originalRealEta
        RankerRealCurvature.originalRealDifferences weights)) := by
  rw [emitted_update_projection]
  rfl

#print axioms emitted_dot_compiles
#print axioms emitted_update_compiles
#print axioms emitted_dot_compiler_commutes
#print axioms emitted_update_compiler_commutes
#print axioms emitted_dot_projection
#print axioms emitted_update_projection
#print axioms emitted_originalRealStep_join

end
end RankerSourceSemanticsGenerated
'''
    _need(len(text.encode()) <= MAX_RECEIPT_BYTES, "Lean source output budget")
    return text


def _synthetic_fraction(value):
    _need(type(value) in (int, Fraction), "synthetic rational values only")
    q = Fraction(value)
    _need(abs(q.numerator).bit_length() <= 32 and q.denominator.bit_length() <= 32, "synthetic rational budget")
    return q


def eval_synthetic_scalar(ir, values):
    """Small rational test oracle only; never invoke on ranker data or Float values."""
    validate_scalar_ir(ir)
    _need(type(values) is tuple and len(values) == ir["slots"], "synthetic slot arity")
    env = tuple(_synthetic_fraction(x) for x in values)

    def evaluate(node):
        if node["kind"] == "var":
            return env[node["slot"]]
        if node["kind"] == "num":
            return _synthetic_fraction(Fraction(int(node["numerator"]), int(node["denominator"])))
        left, right = evaluate(node["left"]), evaluate(node["right"])
        return {"add": lambda: left + right, "sub": lambda: left - right, "mul": lambda: left * right}[node["kind"]]()
    return evaluate(ir["body"])


def eval_synthetic_zip(ir, left, right, external_values=()):
    """At most eight synthetic rational coordinates; explicit min-length zip semantics."""
    validate_zip_ir(ir)
    _need(type(left) is tuple and type(right) is tuple and len(left) <= 8 and len(right) <= 8 and
          type(external_values) is tuple and len(external_values) == len(ir["externals"]), "synthetic zip bounds")
    a = tuple(_synthetic_fraction(x) for x in left)
    b = tuple(_synthetic_fraction(x) for x in right)
    ext = tuple(_synthetic_fraction(x) for x in external_values)
    outputs = tuple(eval_synthetic_scalar(ir["scalar"], (x, y) + ext) for x, y in zip(a, b))
    if ir["kind"] == "zipFold":
        return sum(outputs, Fraction(0))
    return outputs
