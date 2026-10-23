"""Bounded, source-only Python AST transport; no numerical interpreter or proof.

Only the explicitly pinned five-assignment internal observation is source-bound.
Generic expression transport is a syntax-control API, not codebase admission.
Neither API executes Python source, the old emitter, a model, or a Lean prover.
"""
from __future__ import annotations

import ast
import hashlib
import json
import math
import re
import struct
import sys

SCHEMA = "ranker-supported-python-ast-source-transport@1"
GRAMMAR = "ranker-supported-python-ast-scoped-syntax@1"
PARSER = "CPython-3.12-ast-fields@1"
RULES = {
    "scoped-name-resolution@1": "Resolve the nearest lexical binding by identity; spelling alone is not identity.",
    "dot-name-inline@1": "Pinned _dot body; immutable Name-only arguments read once in positional order; fresh callee/comprehension scopes. Semantic preservation is unproved.",
    "l2-binary64-projection@1": "Pinned L2 Name is replaced by its original finite binary64 literal and exact ratio. Semantic global transport is unproved.",
    "fsum-generator-materialization@1": "Proposed ordered pure exact-real generator-to-list materialization. No rewriting or semantic preservation is performed by this host API.",
}
RULE_DIGEST = hashlib.sha256(json.dumps(RULES, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
# The math candidate is still source-only. This is a wire/API source pin, not an
# accepted dependency or grammar/parser correctness certificate.
LEAN_API_PIN = {"bytes": 3916, "sha256": "11baa458c201926c3a6e02b8ec7ca35213c336a30da199ce0390e3f1d7972faf"}
LIMITS = {"bytes": 262144, "depth": 96, "nodes": 12000, "width": 256,
          "integer_bits": 4096, "string_bytes": 65536, "shape": 4096,
          "output_bytes": 1048576}
SOURCE_PIN = {"bytes": 16391, "sha256": "3661027d12c40002db6cd0766fcc834619a956a67bda8c844aba820d3389263a"}
BINDINGS_PIN = {"bytes": 25170, "sha256": "d6cb9f35169351848198d3919a7e794cee89429b07a2879ea680cb8511bfa8b8"}
DRAFT_PIN = {"bytes": 13910, "sha256": "4a7067a4797891740734fa7eae9ad46c02bc3410a4d4fff73ba43445a5a4ae17"}
MODULE_AST_PIN = "61ae9578f4a087b1b181af6fe4f78c3d811bbaa09368f833f6240384d085407b"
OBJECTIVE_AST_PIN = "129da31ae6856167478c7f030a059d0f477b8362bb8fa478221eac7bac6031c2"
DOT_AST_PIN = "3ff8d47ab6f2e375b3bd4b81c6a39e364cd5a15ec859ca383b5e41504250de1e"
L2_RATIO = ["5764607523034235", "576460752303423488"]
ASSIGNMENTS = ["margins", "data", "regularizer", "factors", "gradient"]
BUILTINS = {"abs": 1, "max": 2, "len": 1, "zip": 2, "range": 1}
ATTRIBUTES = {"exp": 1, "log1p": 1, "fsum": 1}
RESERVED_BINDINGS = set(BUILTINS) | {"math", "_dot", "L2"}
AUTHORITY = {"execution_authority": False, "mutation_authority": False,
             "formalization_authority": False, "completion_authority": False,
             "kernel_checked": False, "source_parser_correctness_proved": False,
             "AST_lowering_preservation_proved": False, "normalization_preservation_proved": False,
             "Python_Float_refinement_proved": False, "original_source_semantics_proved": False,
             "original_suffix_compiled": False, "original_loop_convergence_proved": False,
             "global_autoencoder_convergence_proved": False, "strict_cache_admission": False,
             "planner_activation": False, "metadata_hydration": False,
             "full_task_satisfaction": "unknown", "all32_governing_RPI_exits": "OPEN"}


class TransportRefusal(ValueError):
    """Deterministic static refusal, explicitly distinct from Python runtime errors."""
    def __init__(self, code, path="$", detail="", span=None):
        self.code, self.path, self.detail, self.span = code, path, detail, span
        super().__init__(f"{code} at {path}: {detail}")

    def record(self):
        return {"phase": "static_transport", "code": self.code, "path": self.path,
                "detail": self.detail, "span": self.span, "runtime_error_claim": False}


def _refuse(code, path="$", detail="", span=None):
    raise TransportRefusal(code, path, detail, span)


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True, allow_nan=False).encode("utf-8")


def digest(value):
    return hashlib.sha256(canonical(value)).hexdigest()


def buffer_pin(value):
    if type(value) is not bytes:
        _refuse("buffer_type", detail="exact bytes required")
    return {"bytes": len(value), "sha256": hashlib.sha256(value).hexdigest()}


def _bounds(value, path="$", limit=None):
    """Check cycles, depth, width, primitive types and integer/string bounds."""
    limits = LIMITS if limit is None else limit
    active, count = set(), [0]

    def visit(node, here, depth):
        count[0] += 1
        if count[0] > limits["nodes"] or depth > limits["depth"]:
            _refuse("structure_bound", here)
        if type(node) in (dict, list):
            if id(node) in active:
                _refuse("cycle", here)
            if len(node) > limits["width"]:
                _refuse("width_bound", here)
            active.add(id(node))
            for key, child in (node.items() if type(node) is dict else enumerate(node)):
                if type(node) is dict and type(key) is not str:
                    _refuse("field_type", here)
                visit(child, f"{here}.{key}" if type(node) is dict else f"{here}[{key}]", depth + 1)
            active.remove(id(node))
        elif type(node) is str:
            if len(node.encode("utf-8")) > limits["string_bytes"]:
                _refuse("string_bound", here)
        elif type(node) is int:
            if node.bit_length() > limits["integer_bits"]:
                _refuse("integer_bound", here)
        elif node is None or type(node) is bool:
            pass
        else:
            _refuse("primitive_type", here, "wire floats/protocol objects are forbidden")

    visit(value, path, 0)
    return count[0]


def _decode_json(data, limits):
    if type(data) is not bytes or len(data) > limits["bytes"]:
        _refuse("json_bytes_bound")

    def pairs(items):
        result = {}
        for key, value in items:
            if key in result:
                _refuse("duplicate_json_key", f"$.{key}")
            result[key] = value
        return result

    try:
        value = json.loads(data.decode("utf-8"), object_pairs_hook=pairs,
                           parse_constant=lambda s: _refuse("nonfinite_json", detail=s),
                           parse_float=lambda s: _refuse("wire_float", detail=s))
    except TransportRefusal:
        raise
    except (ValueError, UnicodeError, RecursionError) as exc:
        _refuse("invalid_json", detail=type(exc).__name__)
    _bounds(value, limit=limits)
    return value


def decode_json(data):
    return _decode_json(data, LIMITS)


def _parse(data, mode="exec"):
    if sys.implementation.name != "cpython" or sys.version_info[:2] != (3, 12):
        _refuse("parser_version", detail="declared CPython 3.12 grammar required")
    if type(data) is not bytes or len(data) > LIMITS["bytes"]:
        _refuse("source_bytes_bound")
    try:
        text = data.decode("utf-8")
        root = ast.parse(text, mode=mode, type_comments=True, feature_version=(3, 12))
    except (UnicodeError, SyntaxError, ValueError, RecursionError) as exc:
        _refuse("source_parse", detail=type(exc).__name__)
    # Iterative check runs before recursive raw transport/normalization.
    stack, count = [(root, "module" if mode == "exec" else "expression", 0)], 0
    while stack:
        node, path, depth = stack.pop()
        count += 1
        if count > LIMITS["nodes"] or depth > LIMITS["depth"]:
            _refuse("ast_bound", path)
        children = []
        for field, value in ast.iter_fields(node):
            if isinstance(value, list):
                if len(value) > LIMITS["width"]:
                    _refuse("ast_width", path + "." + field)
                for ordinal, child in enumerate(value):
                    if isinstance(child, ast.AST):
                        children.append((child, f"{path}.{field}[{ordinal}]", depth + 1))
            elif isinstance(value, ast.AST):
                children.append((value, path + "." + field, depth + 1))
        stack.extend(reversed(children))
    return text, root, count


def _ast_hash(node):
    return hashlib.sha256(ast.dump(node, include_attributes=False).encode()).hexdigest()


def _span(node):
    return [getattr(node, name, None) for name in ("lineno", "col_offset", "end_lineno", "end_col_offset")]


def _descriptor(text, node, path):
    segment = ast.get_source_segment(text, node)
    encoded = (segment or "").encode("utf-8")
    return {"ast_path": path, "node_kind": type(node).__name__, "span": _span(node),
            "ast_dump": ast.dump(node, include_attributes=False), "ast_sha256": _ast_hash(node),
            "source_segment": segment, "source_segment_utf8_bytes": len(encoded),
            "source_segment_utf8_sha256": hashlib.sha256(encoded).hexdigest()}


def _float(value, token, path):
    if type(value) is not float or not math.isfinite(value):
        _refuse("finite_float_required", path)
    numerator, denominator = value.as_integer_ratio()
    if max(abs(numerator).bit_length(), denominator.bit_length()) > LIMITS["integer_bits"]:
        _refuse("ratio_bound", path)
    return {"token": token, "binary64_hex": struct.pack(">d", value).hex(),
            "numerator": str(numerator), "denominator": str(denominator)}


def _raw(text, node, path, occurrences):
    """Retain ordered CPython fields, including contexts/operators/unsupported tags."""
    desc = _descriptor(text, node, path)
    occurrences[path] = desc
    fields = []
    for field, value in ast.iter_fields(node):
        here = path + "." + field
        if isinstance(value, ast.AST):
            wire = _raw(text, value, here, occurrences)
        elif isinstance(value, list):
            wire = [_raw(text, child, f"{here}[{i}]", occurrences) if isinstance(child, ast.AST)
                    else child for i, child in enumerate(value)]
        elif type(value) is float:
            wire = {"primitive": "binary64", **_float(value, desc["source_segment"], here)}
        elif type(value) in (str, int, bool) or value is None:
            wire = value
        elif type(value) is complex:
            wire = {"primitive": "unsupported_complex", "spelling": desc["source_segment"]}
        else:
            _refuse("raw_primitive", here)
        fields.append([field, wire])
    return {"tag": type(node).__name__, "fields": fields, "occurrence": path}


def _name(scope, spelling):
    return {"scope": scope, "spelling": spelling}


def _id(spelling, path):
    if type(spelling) is not str or not re.fullmatch(r"[A-Za-z_][A-Za-z_0-9]{0,127}", spelling):
        _refuse("identifier", path)
    return spelling


def _context(names):
    if type(names) is not dict or len(names) > 64:
        _refuse("context", "$.context")
    _bounds(names, "$.context")
    result, identities = {}, set()
    for spelling, entry in names.items():
        path = "$.context." + str(spelling)
        _id(spelling, path)
        if spelling in RESERVED_BINDINGS:
            _refuse("reserved_binding", path)
        if type(entry) is not dict or set(entry) != {"scope", "kind", "dimensions", "immutable"}:
            _refuse("context_fields", path)
        scope, kind, dimensions = entry["scope"], entry["kind"], entry["dimensions"]
        if type(scope) is not int or scope < 1 or scope > LIMITS["shape"] or entry["immutable"] is not True:
            _refuse("context_identity", path)
        if type(kind) is not str or kind not in {"scalar", "integer", "vector", "matrix"} or type(dimensions) is not list:
            _refuse("context_kind", path)
        expected = {"scalar": 0, "integer": 0, "vector": 1, "matrix": 2}[kind]
        if len(dimensions) != expected or any(type(d) is not int or d < 0 or d > LIMITS["shape"] for d in dimensions):
            _refuse("context_dimensions", path)
        identity = (scope, spelling)
        if identity in identities:
            _refuse("context_collision", path)
        identities.add(identity)
        result[spelling] = _name(scope, spelling)
    return result


class _Transport:
    def __init__(self, text, context, normalized, dot=None, l2=None):
        self.text, self.env = text, dict(context)
        self.normalized, self.dot, self.l2 = normalized, dot, l2
        self.next_scope = max([1] + [v["scope"] for v in context.values()]) + 1
        self.rules, self.bindings, self.materializations = [], [], []

    def fresh(self):
        result = self.next_scope
        self.next_scope += 1
        if result > LIMITS["shape"]:
            _refuse("scope_bound")
        return result

    def made(self, tag, path, via=None, **fields):
        origin = {"raw_path": path, **(via or {})}
        if tag == "PyName":
            origin["binding_rule"] = "scoped-name-resolution@1"
            origin["binding_rule_digest"] = RULE_DIGEST
        return {"tag": tag, **fields, "__origin": origin}

    def expr(self, node, path, env=None, via=None):
        env = self.env if env is None else env
        def walk(child, suffix):
            return self.expr(child, path + suffix, env, via)
        if isinstance(node, ast.Name):
            if not isinstance(node.ctx, ast.Load):
                _refuse("name_context", path, span=_span(node))
            if node.id == "L2":
                if not self.normalized:
                    return self.made("name", path, via, name=self.made("PyName", path, via, **_name(0, "L2")))
                if self.l2 is None:
                    _refuse("unbound_l2", path)
                literal, literal_path = self.l2
                info = _float(literal.value, ast.get_source_segment(self.text, literal), literal_path)
                result = self.made("floatLiteral", path, {**(via or {}), "definition_path": literal_path,
                                                        "rule": "l2-binary64-projection@1"}, **info)
                self.rules.append({"rule": "l2-binary64-projection@1", "source_occurrence": path,
                                   "definition_occurrence": literal_path, "exact_ratio": [info["numerator"], info["denominator"]],
                                   "semantic_preservation_proved": False})
                return result
            if node.id not in env:
                _refuse("unbound_name", path, node.id, _span(node))
            name_via = dict(via or {})
            if node.id in name_via.get("substitutions", {}):
                name_via["argument_occurrence"] = name_via["substitutions"][node.id]
            return self.made("name", path, name_via, name=self.made("PyName", path, name_via, **env[node.id]))
        if isinstance(node, ast.Constant):
            token = ast.get_source_segment(self.text, node)
            if type(node.value) is int:
                if node.value.bit_length() > LIMITS["integer_bits"]:
                    _refuse("integer_bound", path)
                return self.made("integer", path, via, value=str(node.value), token=token)
            if type(node.value) is float:
                return self.made("floatLiteral", path, via, **_float(node.value, token, path))
            _refuse("literal_kind", path, type(node.value).__name__, _span(node))
        if isinstance(node, ast.UnaryOp):
            if not isinstance(node.op, ast.USub):
                _refuse("unary_operator", path + ".op")
            return self.made("unary", path, via, operator="neg", operand=walk(node.operand, ".operand"))
        if isinstance(node, ast.BinOp):
            operators = {ast.Add: "add", ast.Sub: "sub", ast.Mult: "mul", ast.Div: "div"}
            if type(node.op) not in operators:
                _refuse("binary_operator", path + ".op")
            # This is deterministic static field validation, not evaluation.
            left = walk(node.left, ".left")
            right = walk(node.right, ".right")
            return self.made("binary", path, via, operator=operators[type(node.op)], left=left, right=right)
        if isinstance(node, ast.Compare):
            if len(node.ops) != 1 or not isinstance(node.ops[0], ast.GtE) or len(node.comparators) != 1:
                _refuse("comparison_shape", path)
            comparator = node.comparators[0]
            if not isinstance(comparator, ast.Constant) or type(comparator.value) is not int or comparator.value != 0:
                _refuse("comparison_zero_integer", path + ".comparators[0]")
            return self.made("compare", path, via, operator="ge", left=walk(node.left, ".left"),
                             right=walk(comparator, ".comparators[0]"))
        if isinstance(node, ast.IfExp):
            test = walk(node.test, ".test")
            if test["tag"] != "compare":
                _refuse("conditional_test", path + ".test")
            then = walk(node.body, ".body")
            otherwise = walk(node.orelse, ".orelse")
            return self.made("ifExp", path, via, test=test, then=then, otherwise=otherwise)
        if isinstance(node, ast.Subscript):
            if not isinstance(node.ctx, ast.Load) or not isinstance(node.slice, (ast.Name, ast.Constant)):
                _refuse("index_shape", path)
            if isinstance(node.slice, ast.Constant) and (type(node.slice.value) is not int or node.slice.value < 0):
                _refuse("index_literal", path + ".slice")
            return self.made("subscript", path, via, value=walk(node.value, ".value"), index=walk(node.slice, ".slice"))
        if isinstance(node, (ast.ListComp, ast.GeneratorExp)):
            if len(node.generators) != 1:
                _refuse("generator_count", path + ".generators")
            comp, cp = node.generators[0], path + ".generators[0]"
            if comp.is_async != 0 or comp.ifs:
                _refuse("generator_filter_or_async", cp)
            # Iterable setup is resolved in the outer scope before target binding.
            iterable = self.iterable(comp.iter, cp + ".iter", env, via)
            local, scope = dict(env), self.fresh()
            target = self.target(comp.target, cp + ".target", scope, local, via)
            if target["tag"] == "tuple" and not (iterable["tag"] == "call" and iterable["callee"]["tag"] == "name"
                                                      and iterable["callee"]["identifier"]["spelling"] == "zip"):
                _refuse("tuple_requires_zip", cp + ".target")
            self.bindings.append({"scope": scope, "target_occurrence": cp + ".target", "iterable_occurrence": cp + ".iter",
                                  "body_occurrence": path + ".elt", "kind": type(node).__name__,
                                  "iterable_resolved_before_binding": True, "runtime_order_proved": False})
            body = self.expr(node.elt, path + ".elt", local, via)
            comprehension = self.made("forIn", cp, via, target=target, iterable=iterable, filters=[], asynchronous=False)
            return self.made("listComp" if isinstance(node, ast.ListComp) else "generatorExp", path, via,
                             body=body, generators=[comprehension])
        if isinstance(node, ast.Call):
            if node.keywords:
                _refuse("keyword_call", path + ".keywords")
            if any(isinstance(arg, ast.Starred) for arg in node.args):
                _refuse("starred_call", path + ".args")
            callee = self.callee(node.func, path + ".func", env, via)
            spelling = callee["identifier"]["spelling"] if callee["tag"] == "name" else None
            if spelling == "_dot":
                if len(node.args) != 2:
                    _refuse("dot_arity", path)
                if self.normalized:
                    return self.inline_dot(node, path, env, via)
            expected = BUILTINS[spelling] if spelling in BUILTINS else (
                ATTRIBUTES[callee["member"]] if callee["tag"] == "attribute" else 2)
            if len(node.args) != expected:
                _refuse("call_arity", path)
            arguments = [walk(arg, f".args[{i}]") for i, arg in enumerate(node.args)]
            result = self.made("call", path, via, callee=callee, arguments=arguments)
            if callee["tag"] == "attribute" and callee["member"] == "fsum" and arguments[0]["tag"] == "generatorExp":
                self.materializations.append({"rule": "fsum-generator-materialization@1", "call_occurrence": path,
                    "generator_occurrence": path + ".args[0]", "kind_retained": "GeneratorExp",
                    "source_constructor": "generatorExp", "proposed_target_constructor": "listComp",
                    "iterable_setup_before_body": True, "tuple_target_order_retained": True,
                    "materialization_performed": False, "exact_real_total_addition_required": True,
                    "purity_and_error_order_preservation_proved": False, "CPython_fsum_refinement_proved": False,
                    "via_call": (via or {}).get("via_call")})
            return result
        _refuse("unsupported_syntax", path, type(node).__name__, _span(node))

    def callee(self, node, path, env, via):
        if isinstance(node, ast.Name) and isinstance(node.ctx, ast.Load):
            if node.id in env:
                _refuse("shadowed_callee", path, node.id)
            if node.id in BUILTINS:
                return self.made("name", path, via, identifier=self.made("PyName", path, via, **_name(0, node.id)))
            if node.id == "_dot":
                return self.made("name", path, via, identifier=self.made("PyName", path, via, **_name(0, "_dot")))
        if isinstance(node, ast.Attribute) and isinstance(node.ctx, ast.Load) and isinstance(node.value, ast.Name):
            if node.value.id == "math" and node.value.id not in env and node.attr in ATTRIBUTES:
                return self.made("attribute", path, via, base=self.made("PyName", path + ".value", via, **_name(0, "math")), member=node.attr)
        _refuse("callee_registry", path, type(node).__name__, _span(node))

    def iterable(self, node, path, env, via):
        if isinstance(node, ast.Name):
            return self.expr(node, path, env, via)
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name):
            if node.func.id == "zip":
                result = self.expr(node, path, env, via)
                if not all(a["tag"] == "name" for a in result["arguments"]):
                    _refuse("zip_name_inputs", path)
                return result
            if node.func.id == "range":
                result = self.expr(node, path, env, via)
                child = result["arguments"][0]
                if not (child["tag"] == "call" and child["callee"]["tag"] == "name" and child["callee"]["identifier"]["spelling"] == "len"
                        and child["arguments"][0]["tag"] == "name"):
                    _refuse("range_len_name", path)
                return result
        _refuse("iterable_shape", path, type(node).__name__)

    def target(self, node, path, scope, env, via):
        if isinstance(node, ast.Name) and isinstance(node.ctx, ast.Store):
            _id(node.id, path)
            if node.id in RESERVED_BINDINGS:
                _refuse("reserved_binding", path)
            identity = _name(scope, node.id)
            env[node.id] = identity
            return self.made("name", path, via, identifier=self.made("PyName", path, via, **identity))
        if isinstance(node, ast.Tuple) and isinstance(node.ctx, ast.Store) and len(node.elts) == 2:
            if not all(isinstance(v, ast.Name) for v in node.elts) or node.elts[0].id == node.elts[1].id:
                _refuse("tuple_target", path)
            left = self.target(node.elts[0], path + ".elts[0]", scope, env, via)
            right = self.target(node.elts[1], path + ".elts[1]", scope, env, via)
            return self.made("tuple", path, via, elements=[left, right])
        _refuse("target_shape", path)

    def inline_dot(self, call, path, env, via):
        if self.dot is None:
            _refuse("dot_definition_required", path)
        if len(call.args) != 2 or not all(isinstance(a, ast.Name) and isinstance(a.ctx, ast.Load) for a in call.args):
            _refuse("dot_name_only", path)
        arguments = [self.expr(a, path + f".args[{i}]", env, via) for i, a in enumerate(call.args)]
        function, dp = self.dot
        # Signature/body checked independently before admitting substitution.
        if not (isinstance(function, ast.FunctionDef) and function.name == "_dot" and len(function.body) == 1
                and isinstance(function.body[0], ast.Return) and not function.decorator_list
                and not function.args.posonlyargs and not function.args.defaults and not function.args.kwonlyargs
                and function.args.vararg is None and function.args.kwarg is None
                and [a.arg for a in function.args.args] == ["a", "b"]):
            _refuse("dot_definition_shape", dp)
        fresh_scope = self.fresh()
        local = {"a": {k: arguments[0]["name"][k] for k in ("scope", "spelling")},
                 "b": {k: arguments[1]["name"][k] for k in ("scope", "spelling")}}
        provenance = {"via_call": path, "rule": "dot-name-inline@1", "fresh_function_scope": fresh_scope,
                      "substitutions": {"a": path + ".args[0]", "b": path + ".args[1]"}}
        result = self.expr(function.body[0].value, dp + ".body[0].value", local, provenance)
        self.rules.append({"rule": "dot-name-inline@1", "source_occurrence": path, "callee_occurrence": dp,
            "callee_ast_sha256": _ast_hash(function), "fresh_function_scope": fresh_scope,
            "argument_reads": [{"ordinal": i, "raw_path": path + f".args[{i}]",
                                "binding": {k: arguments[i]["name"][k] for k in ("scope", "spelling")}}
                               for i in range(2)],
            "name_only_arguments": True, "immutable_context_required": True, "argument_once_order_preservation_proved": False,
            "semantic_preservation_proved": False})
        return result

    def statement(self, node, path):
        if not isinstance(node, ast.Assign) or len(node.targets) != 1 or not isinstance(node.targets[0], ast.Name) or node.type_comment:
            _refuse("statement_shape", path)
        target = node.targets[0]
        if target.id in self.env or target.id in RESERVED_BINDINGS:
            _refuse("reassignment_or_reserved", path + ".targets[0]")
        rhs = self.expr(node.value, path + ".value")
        identity = _name(1, _id(target.id, path + ".targets[0]"))
        self.env[target.id] = identity
        return self.made("assign", path, targets=[self.made("name", path + ".targets[0]",
            identifier=self.made("PyName", path + ".targets[0]", **identity))], rhs=rhs)


def _unpack(tree, raw_occurrences, root_path):
    joins = []
    def walk(value, path):
        if type(value) is dict:
            origin = value.get("__origin")
            if origin is not None:
                source = origin["raw_path"]
                if source not in raw_occurrences:
                    _refuse("missing_occurrence_join", path, source)
                joined = {"output_path": path, "constructor": value["tag"], "source": origin,
                          "raw_ast_sha256": raw_occurrences[source]["ast_sha256"],
                          "raw_segment_sha256": raw_occurrences[source]["source_segment_utf8_sha256"]}
                joins.append(joined)
            output = {k: walk(v, path + "." + k) for k, v in value.items() if k != "__origin"}
            if origin is not None:
                joined["output_subtree_sha256"] = digest(output)
            return output
        if type(value) is list:
            return [walk(v, path + f"[{i}]") for i, v in enumerate(value)]
        return value
    result = walk(tree, root_path)
    return result, joins


def _finish(result):
    result.update(AUTHORITY)
    result["receipt_sha256"] = digest(result)
    encoded = canonical(result)
    if len(encoded) > LIMITS["output_bytes"]:
        _refuse("output_bytes_bound")
    return result


def transport_expression(source, context, *, normalized=False, whole_objective=False):
    """Independent generic syntax controls. It never admits codebase/source proofs."""
    if whole_objective:
        _refuse("whole_objective_unsupported", detail="guard/return/finite control are outside phase one")
    env = _context(context)
    text, root, count = _parse(source, "eval")
    occurrences = {}
    raw = _raw(text, root.body, "expression.body", occurrences)
    worker = _Transport(text, env, normalized)
    decorated = worker.expr(root.body, "expression.body")
    syntax, joins = _unpack(decorated, occurrences, "$.expression")
    return _finish({"schema": SCHEMA, "grammar": GRAMMAR, "parser": PARSER,
        "parser_runtime": list(sys.version_info[:3]), "rule_digest": RULE_DIGEST,
        "status": "SOURCE_ONLY_GENERIC_SYNTAX_UNQUALIFIED", "source": buffer_pin(source),
        "context": json.loads(canonical(context)), "ast_node_count": count, "raw": raw, "raw_occurrences": occurrences,
        "expression": syntax, "occurrence_joins": joins,
        "normalization_steps": worker.rules, "binding_steps": worker.bindings,
        "materialization_obligations": worker.materializations, "source_bound_actual_prefix": False,
        "source_execution_calls": 0, "target_evaluator_calls": 0, "new_qualified_queries": 0})


def _binding_nodes(objective):
    b = objective.body
    return {"margins": b[0], "data": b[1], "regularizer": b[2], "factors": b[3], "gradient": b[4],
        "nonfinite_guard": b[5], "return_tuple": b[6], "margin_body": b[0].value.elt,
        "loss_body": b[1].value.left.args[0].elt, "loss_denominator": b[1].value.right,
        "regularizer_body": b[2].value, "factor_body": b[3].value.elt,
        "gradient_coordinate": b[4].value.elt, "gradient_sum_body": b[4].value.elt.right.left.args[0].elt,
        "gradient_sum_zip": b[4].value.elt.right.left.args[0].generators[0].iter,
        "gradient_denominator": b[4].value.elt.right.right, "coordinate_range": b[4].value.generators[0].iter}


def _join_descriptor(text, node, expected, path):
    if type(expected) is not dict:
        _refuse("binding_descriptor", path)
    actual = _descriptor(text, node, expected["ast_path"])
    for field in ("node_kind", "span", "ast_dump", "ast_sha256", "source_segment",
                  "source_segment_utf8_bytes", "source_segment_utf8_sha256"):
        if actual[field] != expected[field]:
            _refuse("binding_join", path + "." + field)
    return actual


def transport_prefix(source, bindings, draft, *, whole_objective=False):
    """Parse exact three immutable byte buffers and transport actual first five RHSs.

    The historical draft is joined as context only; its tree is never interpreted,
    imported, or reused to construct the independent Py syntax.
    """
    if whole_objective:
        _refuse("whole_objective_unsupported", detail="five bindings are an internal observation, not Python return")
    for name, value, expected in (("source", source, SOURCE_PIN), ("bindings", bindings, BINDINGS_PIN), ("draft", draft, DRAFT_PIN)):
        if buffer_pin(value) != expected:
            _refuse("source_pin", "$." + name)
    bound, prior = decode_json(bindings), decode_json(draft)
    text, module, count = _parse(source)
    if _ast_hash(module) != MODULE_AST_PIN or bound["module_ast_sha256"] != MODULE_AST_PIN or prior["module_AST_sha256"] != MODULE_AST_PIN:
        _refuse("module_ast_join")
    objective, dot, l2 = module.body[24], module.body[23], module.body[11]
    if _ast_hash(objective) != OBJECTIVE_AST_PIN or _ast_hash(dot) != DOT_AST_PIN:
        _refuse("function_ast_join")
    if not (isinstance(objective, ast.FunctionDef) and objective.name == "_objective" and len(objective.body) == 7
            and [a.arg for a in objective.args.args] == ["weights", "differences"]):
        _refuse("objective_shape")
    joined = {"objective": _join_descriptor(text, objective, bound["objective"], "$.objective"),
              "dot_callee": _join_descriptor(text, dot, bound["dot_callee"], "$.dot_callee"),
              "source_L2": _join_descriptor(text, l2, bound["source_L2"], "$.source_L2")}
    nodes = _binding_nodes(objective)
    if set(nodes) != set(bound["bindings"]) or len(nodes) != 17:
        _refuse("binding_cohort")
    for name, node in nodes.items():
        joined[name] = _join_descriptor(text, node, bound["bindings"][name], "$.bindings." + name)
        check = prior["checked_bindings"][name]
        if check != {"AST_sha256": joined[name]["ast_sha256"], "segment_sha256": joined[name]["source_segment_utf8_sha256"], "span": joined[name]["span"]}:
            _refuse("draft_binding_join", "$.draft." + name)
    if not (isinstance(l2, ast.Assign) and len(l2.targets) == 1 and isinstance(l2.targets[0], ast.Name)
            and l2.targets[0].id == "L2" and isinstance(l2.value, ast.Constant) and type(l2.value.value) is float):
        _refuse("l2_definition")
    ratio = [str(v) for v in l2.value.value.as_integer_ratio()]
    if ratio != L2_RATIO or bound["source_L2"]["literal_exact_ratio"] != dict(zip(("numerator", "denominator"), ratio)):
        _refuse("l2_ratio")
    if prior["checked_context_statements"] != 7 or len(prior["assignments"]) != 5 or prior["shape"] != {"rows": 4, "columns": 80, "weights": 80}:
        _refuse("draft_context_shape")
    for i, node in enumerate(objective.body[:5]):
        if node.targets[0].id != ASSIGNMENTS[i] or prior["assignments"][i]["name"] != ASSIGNMENTS[i] or prior["assignments"][i]["assignment_AST_sha256"] != _ast_hash(node):
            _refuse("assignment_order", f"$.assignments[{i}]")
    occurrences = {}
    raw = {"objective": _raw(text, objective, "module.body[24]", occurrences),
           "dot": _raw(text, dot, "module.body[23]", occurrences),
           "l2": _raw(text, l2, "module.body[11]", occurrences)}
    context = {"weights": {"scope": 1, "kind": "vector", "dimensions": [80], "immutable": True},
               "differences": {"scope": 1, "kind": "matrix", "dimensions": [4, 80], "immutable": True}}
    env = _context(context)
    raw_worker = _Transport(text, env, False)
    normal_worker = _Transport(text, env, True, (dot, "module.body[23]"), (l2.value, "module.body[11].value"))
    scoped = [raw_worker.statement(node, f"module.body[24].body[{i}]") for i, node in enumerate(objective.body[:5])]
    normalized = [normal_worker.statement(node, f"module.body[24].body[{i}]") for i, node in enumerate(objective.body[:5])]
    scoped, scoped_joins = _unpack(scoped, occurrences, "$.raw_program")
    normalized, normalized_joins = _unpack(normalized, occurrences, "$.normalized_program")
    normalization_steps = normal_worker.rules
    for i, step in enumerate(normalization_steps):
        step["ordinal"] = i
        step["rule_digest"] = RULE_DIGEST
        step["input_ast_sha256"] = occurrences[step["source_occurrence"]]["ast_sha256"]
        step["input_segment_sha256"] = occurrences[step["source_occurrence"]]["source_segment_utf8_sha256"]
        step["output_occurrences"] = [j["output_path"] for j in normalized_joins
            if j["source"].get("rule") == step["rule"] and (
                j["source"].get("via_call") == step["source_occurrence"] if step["rule"] == "dot-name-inline@1"
                else j["source"]["raw_path"] == step["source_occurrence"])]
        step["output_subtree_sha256s"] = [j["output_subtree_sha256"] for j in normalized_joins
                                           if j["output_path"] in step["output_occurrences"]]
        step["step_sha256"] = digest(step)
    if len([s for s in normalization_steps if s["rule"] == "dot-name-inline@1"]) != 2 or len([s for s in normalization_steps if s["rule"] == "l2-binary64-projection@1"]) != 2:
        _refuse("normalization_cohort")
    return _finish({"schema": SCHEMA, "grammar": GRAMMAR, "parser": PARSER,
        "parser_runtime": list(sys.version_info[:3]), "rule_digest": RULE_DIGEST,
        "status": "SOURCE_ONLY_ACTUAL_PREFIX_SYNTAX_UNQUALIFIED", "inputs": {"source": dict(SOURCE_PIN), "bindings": dict(BINDINGS_PIN), "draft": dict(DRAFT_PIN)},
        "source_bound_actual_prefix": True, "context": context, "module_ast_sha256": _ast_hash(module),
        "module_ast_node_count": count, "context_statement_count": 7, "prefix_statement_count": 5,
        "assignment_order": list(ASSIGNMENTS), "binding_joins": joined, "raw": raw, "raw_occurrences": occurrences,
        "raw_program": scoped, "raw_program_sha256": digest(scoped), "normalized_program": normalized,
        "normalized_program_sha256": digest(normalized), "raw_occurrence_joins": scoped_joins,
        "normalized_occurrence_joins": normalized_joins, "normalization_steps": normalization_steps,
        "raw_binding_steps": raw_worker.bindings, "normalized_binding_steps": normal_worker.bindings,
        "materialization_obligations": normal_worker.materializations,
        "source_execution_calls": 0, "target_evaluator_calls": 0, "old_emitter_import_or_calls": 0,
        "new_qualified_queries": 0, "source_suffix_context_only": [joined["nonfinite_guard"], joined["return_tuple"]],
        "observation": "ordered five internal bindings; not actual Python return",
        "scope_limitations": ["No Python/parser correctness proof", "No _dot normalization preservation proof",
                              "No container/zip/range lowering preservation", "No generator materialization proof",
                              "No Float/libm/fsum refinement", "No guard/return/loop/preparation/task/cache admission"]})


def verify_prefix_receipt(receipt, source, bindings, draft):
    """Recompute from buffers; mutable annotations or receipt stamps confer no trust."""
    if type(receipt) is not dict:
        _refuse("receipt_type")
    _bounds(receipt, limit={**LIMITS, "width": 4096, "nodes": 200000})
    # The receipt is bigger than an input JSON; enforce its own exact output bound.
    if len(canonical(receipt)) > LIMITS["output_bytes"]:
        _refuse("receipt_bytes_bound")
    fresh = transport_prefix(source, bindings, draft)
    if receipt != fresh:
        _refuse("receipt_join", detail="complete independently recomputed receipt differs")
    return True


def decode_prefix_receipt(data, source, bindings, draft):
    """Exact canonical receipt decoding followed by complete source recomputation."""
    receipt = _decode_json(data, {**LIMITS, "bytes": LIMITS["output_bytes"], "width": 4096, "nodes": 200000})
    if canonical(receipt) != data:
        _refuse("noncanonical_receipt")
    verify_prefix_receipt(receipt, source, bindings, draft)
    return receipt


def _lean_string(value):
    # Admitted names/tokens are ASCII; this is also safe for escaped newlines.
    return json.dumps(value, ensure_ascii=False)


def _lean_name(value):
    return "⟨" + str(value["scope"]) + ", " + _lean_string(value["spelling"]) + "⟩"


def _lean_target(value):
    if value["tag"] == "name":
        return "(PyTarget.name " + _lean_name(value["identifier"]) + ")"
    return "(PyTarget.tuple [" + ", ".join(_lean_target(v) for v in value["elements"]) + "])"


def _lean_args(values):
    result = "PyArgs.nil"
    for child in reversed(values):
        result = "(PyArgs.cons " + _lean_expr(child) + " " + result + ")"
    return result


def _lean_expr(value):
    tag = value["tag"]
    if tag == "name":
        return "(PyExpr.name " + _lean_name(value["name"]) + ")"
    if tag == "integer":
        return "(PyExpr.integer (" + value["value"] + " : ℤ))"
    if tag == "floatLiteral":
        ratio = "((" + value["numerator"] + " : ℚ) / " + value["denominator"] + ")"
        return "(PyExpr.floatLiteral " + _lean_string(value["token"]) + " " + ratio + ")"
    if tag == "unary":
        return "(PyExpr.unary PyUnary.usub " + _lean_expr(value["operand"]) + ")"
    if tag == "binary":
        return "(PyExpr.binary PyBinary." + value["operator"] + " " + _lean_expr(value["left"]) + " " + _lean_expr(value["right"]) + ")"
    if tag == "call":
        callee = value["callee"]
        if callee["tag"] == "name":
            ref = "(PyCalleeRef.name " + _lean_name(callee["identifier"]) + ")"
        else:
            ref = "(PyCalleeRef.attribute " + _lean_name(callee["base"]) + " " + _lean_string(callee["member"]) + ")"
        return "(PyExpr.call " + ref + " " + _lean_args(value["arguments"]) + ")"
    if tag == "compare":
        return "(PyExpr.compare PyCompare.ge " + _lean_expr(value["left"]) + " " + _lean_expr(value["right"]) + ")"
    if tag == "ifExp":
        return "(PyExpr.ifExp " + " ".join(_lean_expr(value[k]) for k in ("test", "then", "otherwise")) + ")"
    if tag == "subscript":
        return "(PyExpr.subscript " + _lean_expr(value["value"]) + " " + _lean_expr(value["index"]) + ")"
    if tag in {"listComp", "generatorExp"}:
        generators = []
        for generator in value["generators"]:
            generators.append("(PyComprehension.forIn " + _lean_target(generator["target"]) + " " +
                _lean_expr(generator["iterable"]) + " " + _lean_args(generator["filters"]) + " false)")
        return "(PyExpr." + tag + " " + _lean_expr(value["body"]) + " [" + ", ".join(generators) + "])"
    _refuse("lean_constructor", detail=tag)


def _lean_program(values):
    return "[\n  " + ",\n  ".join("PyStmt.assign [" + ", ".join(_lean_target(t) for t in value["targets"]) +
                                  "] " + _lean_expr(value["rhs"]) for value in values) + "\n]"


def emit_lean_prefix(receipt, source, bindings, draft, api_source, *, namespace="GeneratedSupportedPythonAstPrefix"):
    """Emit only recomputed raw/normalized Py syntax, never a proof or evaluator.

    The independent grammar body is separately pinned. Native typechecking and
    every semantic preservation step remain required external qualifications.
    """
    verify_prefix_receipt(receipt, source, bindings, draft)
    _id(namespace, "$.namespace")
    if LEAN_API_PIN is None:
        _refuse("lean_constructor_api_pending", detail="no placeholder API pin is admitted")
    if buffer_pin(api_source) != LEAN_API_PIN:
        _refuse("lean_api_pin")
    module = ("import PyAstNumericSubset\n\nopen RankerSupportedPythonAstReal\n\n"
        "/- Source-only syntax literals. No parser, normalization or lowering theorem is asserted. -/\n"
        "namespace «" + namespace + "»\n\n"
        "def rawPrefix : List PyStmt := " + _lean_program(receipt["raw_program"]) + "\n\n"
        "def normalizedPrefix : List PyStmt := " + _lean_program(receipt["normalized_program"]) + "\n\n"
        "end «" + namespace + "»\n")
    encoded = module.encode("utf-8")
    if len(encoded) > LIMITS["output_bytes"]:
        _refuse("lean_output_bound")
    return {"schema": "ranker-supported-python-ast-lean-syntax-emission@1", "module_text": module,
            "module": buffer_pin(encoded), "grammar_api": dict(LEAN_API_PIN),
            "source_receipt_sha256": receipt["receipt_sha256"], "raw_program_sha256": receipt["raw_program_sha256"],
            "normalized_program_sha256": receipt["normalized_program_sha256"], "assignment_order": receipt["assignment_order"],
            "source_suffix_compiled": False, "actual_prefix_native_checked": False,
            "semantic_preservation_proved": False, **AUTHORITY}
