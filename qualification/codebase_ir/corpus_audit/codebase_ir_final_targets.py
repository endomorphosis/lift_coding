"""Nonexecuting source projection for authored final-evaluation fixtures.

This qualification grammar is not a registered native decoder profile or a
CPython correspondence theorem. Int/Bool annotations are declared assumptions.
"""
from __future__ import annotations

import ast

import codebase_ir_corpus_audit as audit

PROFILE = "qualification/pure-int-bool-expression@1"
TARGET_SCHEMA = "codebase-ir-qualification-expression@1"
SORTS = {"int": "Int", "bool": "Bool"}
BINARY = {"Add", "Sub", "Mult"}
COMPARE = {"Eq", "NotEq", "Lt", "LtE", "Gt", "GtE"}


class UnsupportedSource(ValueError):
    pass


def _sort(node: ast.AST | None) -> str:
    if isinstance(node, ast.Name) and node.id in SORTS:
        return SORTS[node.id]
    raise UnsupportedSource("explicit Int/Bool annotation required")


def _source_expression(node: ast.AST, names: dict[str, str]) -> dict:
    if isinstance(node, ast.Name) and node.id in names:
        return {"kind": "reference", "name": node.id, "sort": names[node.id]}
    if isinstance(node, ast.Constant) and type(node.value) in {int, bool}:
        return {"kind": "literal", "sort": "Bool" if type(node.value) is bool else "Int", "value": node.value}
    if isinstance(node, ast.BinOp) and type(node.op).__name__ in BINARY:
        return {"kind": "binary", "operator": type(node.op).__name__,
                "left": _source_expression(node.left, names), "right": _source_expression(node.right, names)}
    if isinstance(node, ast.UnaryOp) and isinstance(node.op, ast.USub | ast.Not):
        return {"kind": "unary", "operator": type(node.op).__name__, "operand": _source_expression(node.operand, names)}
    if isinstance(node, ast.Compare) and len(node.ops) == 1 and type(node.ops[0]).__name__ in COMPARE:
        return {"kind": "compare", "operator": type(node.ops[0]).__name__,
                "left": _source_expression(node.left, names), "right": _source_expression(node.comparators[0], names)}
    if isinstance(node, ast.BoolOp) and isinstance(node.op, ast.And | ast.Or):
        return {"kind": "boolean", "operator": type(node.op).__name__,
                "values": [_source_expression(value, names) for value in node.values]}
    raise UnsupportedSource("unsupported source construct: " + type(node).__name__)


def validate_target(target: object, *, max_nodes: int = 256, max_depth: int = 32) -> dict[str, list]:
    """Validate typed candidate structure; preserve operator/literal/reference paths."""
    audit._closed(target, {"schema", "function", "body"}, "expression target")
    audit._require(target["schema"] == TARGET_SCHEMA, "qualification target schema required")
    function = audit._closed(target["function"], {"name", "parameters", "returns"}, "target function")
    name = audit._text(function["name"], "function name")
    audit._require(name.isidentifier(), "identifier function name required")
    params = function["parameters"]
    audit._require(type(params) is list and 1 <= len(params) <= 8, "bounded nonempty parameters required")
    names = {}
    for param in params:
        audit._closed(param, {"name", "sort"}, "target parameter")
        name = audit._text(param["name"], "parameter name")
        audit._require(name.isidentifier() and name not in names
                       and type(param["sort"]) is str and param["sort"] in {"Int", "Bool"}, "unique typed parameter required")
        names[name] = param["sort"]
    audit._require(type(function["returns"]) is str and function["returns"] in {"Int", "Bool"}, "typed return required")
    details, count = {"references": [], "operators": [], "literals": []}, 0

    def visit(node, path, depth):
        nonlocal count
        count += 1
        audit._require(count <= max_nodes and depth <= max_depth, "candidate expression work budget exceeded")
        audit._require(type(node) is dict and type(node.get("kind")) is str, "typed expression object required")
        kind = node["kind"]
        if kind == "reference":
            audit._closed(node, {"kind", "name", "sort"}, "reference")
            audit._require(type(node["name"]) is str and node["name"] in names
                           and node["sort"] == names[node["name"]], "unresolved or mistyped reference")
            details["references"].append([path, node["name"], node["sort"]])
            return node["sort"]
        if kind == "literal":
            audit._closed(node, {"kind", "sort", "value"}, "literal")
            audit._require((node["sort"] == "Int" and type(node["value"]) is int and abs(node["value"]) <= 2**63 - 1)
                           or (node["sort"] == "Bool" and type(node["value"]) is bool), "exact bounded typed literal required")
            details["literals"].append([path, node["sort"], node["value"]])
            return node["sort"]
        if kind in {"binary", "compare"}:
            audit._closed(node, {"kind", "operator", "left", "right"}, kind)
            allowed = BINARY if kind == "binary" else COMPARE
            audit._require(type(node["operator"]) is str and node["operator"] in allowed, "unsupported operator")
            left, right = visit(node["left"], path + ".left", depth + 1), visit(node["right"], path + ".right", depth + 1)
            audit._require(left == right and (left == "Int" or kind == "compare" and node["operator"] in {"Eq", "NotEq"}),
                           "operator operand sort mismatch")
            details["operators"].append([path, node["operator"]])
            return "Int" if kind == "binary" else "Bool"
        if kind == "unary":
            audit._closed(node, {"kind", "operator", "operand"}, "unary")
            audit._require(type(node["operator"]) is str and node["operator"] in {"USub", "Not"}, "unsupported unary operator")
            sort = visit(node["operand"], path + ".operand", depth + 1)
            audit._require(sort == ("Int" if node["operator"] == "USub" else "Bool"), "unary operand sort mismatch")
            details["operators"].append([path, node["operator"]])
            return sort
        if kind == "boolean":
            audit._closed(node, {"kind", "operator", "values"}, "boolean")
            audit._require(type(node["operator"]) is str and node["operator"] in {"And", "Or"}
                           and type(node["values"]) is list and 2 <= len(node["values"]) <= 8, "bounded Boolean operator required")
            for index, value in enumerate(node["values"]):
                audit._require(visit(value, f"{path}.values[{index}]", depth + 1) == "Bool", "Boolean operand sort mismatch")
            details["operators"].append([path, node["operator"]])
            return "Bool"
        raise audit.AuditInputError("unsupported expression kind")

    audit._require(visit(target["body"], "body", 0) == function["returns"], "return annotation/target sort mismatch")
    return details


def derive_source(raw: bytes, limits: audit.Limits = audit.DEFAULT_LIMITS) -> tuple[dict, dict | None, str | None]:
    """Project only captured source, never a desired instruction or prediction."""
    audit._require(b"\r" not in raw, "qualification source profile requires physical LF lines")
    audit.normalized_ast_digest(raw, limits)
    tree = ast.parse(raw.decode("utf-8"), type_comments=True)
    functions = [node for node in tree.body if isinstance(node, ast.FunctionDef)]
    audit._require(len(functions) == 1, "one selected top-level function required")
    function = functions[0]
    # This deliberately narrow qualification source profile uses physical LF lines.
    lines = raw.split(b"\n")
    start = sum(len(line) + 1 for line in lines[:function.lineno - 1]) + function.col_offset
    end = sum(len(line) + 1 for line in lines[:function.end_lineno - 1]) + function.end_col_offset
    audit._require(0 <= start < end <= len(raw), "function byte span outside captured source")
    selected = ast.parse(raw[start:end].decode("utf-8"), type_comments=True)
    audit._require(len(selected.body) == 1 and ast.dump(selected.body[0], include_attributes=False)
                   == ast.dump(function, include_attributes=False), "function byte span does not reproduce selected AST")
    binding = {"source_sha256": audit._sha(raw), "function_name": function.name,
               "start_byte": start, "end_byte": end, "source_slice_sha256": audit._sha(raw[start:end])}
    try:
        if len(tree.body) != 1 or function.decorator_list or function.type_comment:
            raise UnsupportedSource("only LF standalone undecorated function supported")
        args = function.args
        if args.posonlyargs or args.kwonlyargs or args.vararg or args.kwarg or args.defaults or args.kw_defaults:
            raise UnsupportedSource("only ordinary required parameters supported")
        if len(function.body) != 1 or not isinstance(function.body[0], ast.Return):
            raise UnsupportedSource("only one return expression supported")
        parameters = [{"name": arg.arg, "sort": _sort(arg.annotation)} for arg in args.args]
        target = {"schema": TARGET_SCHEMA, "function": {"name": function.name, "parameters": parameters,
                  "returns": _sort(function.returns)}, "body": _source_expression(function.body[0].value, {p["name"]: p["sort"] for p in parameters})}
        validate_target(target)
        return binding, target, None
    except (UnsupportedSource, audit.AuditInputError) as exc:
        return binding, None, str(exc)
