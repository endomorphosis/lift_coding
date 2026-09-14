"""Source-relative generated-program profile for legal, CVE, and skill cases."""
from __future__ import annotations

import ast

from .common import HANDLERS

ALLOWED_CALLS = {
    spec["permitted"] for spec in HANDLERS.values()
} | {spec["undeclared"] for spec in HANDLERS.values()}


def profile_check(source: str, population: str) -> tuple[ast.AST, list[str]]:
    if population not in HANDLERS:
        raise ValueError("Unknown source population")
    tree = ast.parse(source, filename="candidate.py")
    if len(tree.body) != 1 or not isinstance(tree.body[0], ast.FunctionDef):
        raise ValueError("One run function required")
    fn = tree.body[0]
    if fn.name != "run" or fn.decorator_list or fn.returns or fn.type_comment or getattr(fn, "type_params", []):
        raise ValueError("Unsupported function contract")
    args = fn.args
    if (
        len(args.args) != 1
        or args.args[0].arg != "payload"
        or args.args[0].annotation
        or args.posonlyargs
        or args.kwonlyargs
        or args.defaults
        or args.kw_defaults
        or args.vararg
        or args.kwarg
    ):
        raise ValueError("Signature must be run(payload)")
    if not 1 <= len(fn.body) <= 4:
        raise ValueError("One to four direct calls required")
    permitted = {HANDLERS[population]["permitted"], HANDLERS[population]["undeclared"]}
    calls = []
    for statement in fn.body:
        if not isinstance(statement, ast.Expr) or not isinstance(statement.value, ast.Call):
            raise ValueError("Only direct handler calls supported")
        call = statement.value
        if (
            not isinstance(call.func, ast.Name)
            or call.func.id not in permitted
            or call.keywords
            or len(call.args) != 1
            or not isinstance(call.args[0], ast.Name)
            or call.args[0].id != "payload"
        ):
            raise ValueError("Unsupported/dynamic handler invocation")
        calls.append(call.func.id)
    return tree, calls


def program_for(population: str, *, permitted: bool) -> str:
    name = HANDLERS[population]["permitted" if permitted else "undeclared"]
    return f"def run(payload):\n    {name}(payload)\n"


def syntax_reject_samples(population: str) -> list[str]:
    good = HANDLERS[population]["permitted"]
    return [
        f"def run[T](payload):\n    {good}(payload)\n",
        f"def run(payload):\n    globals()[{good!r}](payload)\n",
        f"@{good}\ndef run(payload):\n    {good}(payload)\n",
        f"def run(payload):\n    {good}.__call__(payload)\n",
        "import os\ndef run(payload):\n    os.system('true')\n",
        f"def run(payload):\n    allowed_sink(payload)\n",
    ]
