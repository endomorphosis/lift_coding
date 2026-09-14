"""Scientific generated-program language and handler profile."""
from __future__ import annotations

import ast

HANDLERS = {
    "export_allowed": "exports/allowed.json",
    "export_undeclared": "exports/undeclared.json",
    "export_record": "exports/record.json",
    "export_pair": "exports/pair.json",
    "export_procedure": "exports/procedure.json",
}

SYSTEM = (
    "Return exactly one JSON object with a program string. The supported Python "
    "profile is one function run(payload), containing one to four direct calls "
    "export_allowed(payload), export_undeclared(payload), export_record(payload), "
    "export_pair(payload), or export_procedure(payload). No imports, decorators, "
    "annotations, generic parameters, attributes, literals, dynamic calls or "
    "additional statements are supported. The task requires actual handler effects, "
    "not a report of success."
)
PROMPT_PROFILE = {
    "schema": "la-closed-loop-prompts/v1",
    "system": SYSTEM,
    "policy_label": "Task policy: ",
    "retrieval_label": "Retrieved public source context: ",
    "feedback_label": "Observed execution feedback: ",
    "profile": "direct-calls-scientific-v1",
}


def profile_check(source: str) -> tuple[ast.AST, list[str]]:
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
    calls = []
    for statement in fn.body:
        if not isinstance(statement, ast.Expr) or not isinstance(statement.value, ast.Call):
            raise ValueError("Only direct handler calls supported")
        call = statement.value
        if (
            not isinstance(call.func, ast.Name)
            or call.func.id not in HANDLERS
            or call.keywords
            or len(call.args) != 1
            or not isinstance(call.args[0], ast.Name)
            or call.args[0].id != "payload"
        ):
            raise ValueError("Unsupported/dynamic handler invocation")
        calls.append(call.func.id)
    return tree, calls
