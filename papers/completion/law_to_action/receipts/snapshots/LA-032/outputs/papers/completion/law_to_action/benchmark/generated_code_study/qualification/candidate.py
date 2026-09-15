#!/usr/bin/python3.12
"""Scientific generated-program profile: direct handler calls only."""
from __future__ import annotations

import ast
import hashlib
import json
from pathlib import Path
from typing import Any

import sys
from pathlib import Path as _Path

_STUDY = _Path(__file__).resolve().parents[1]
if str(_STUDY) not in sys.path:
    sys.path.insert(0, str(_STUDY))
from qualification.handlers import HANDLERS, POPULATION_HANDLER, ScientificExportAdapter, effects

PROFILE_ID = "direct-calls-scientific-v1"


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


def execute_candidate(source: bytes, payload: dict[str, Any], state_dir: Path, run_id: str, allowed: list[str]) -> dict[str, Any]:
    text = source.decode("utf-8")
    supported = True
    diagnostic = None
    calls: list[str] = []
    tree = None
    try:
        tree, calls = profile_check(text)
    except (ValueError, SyntaxError) as exc:
        supported = False
        diagnostic = str(exc)
    adapter = ScientificExportAdapter(state_dir)
    handler_calls: list[str] = []
    execution_error = None
    if supported:
        namespace = {"__builtins__": {}}
        for name in HANDLERS:
            def _call(payload_value, name=name):
                handler_calls.append(name)
                return adapter.dispatch(name, payload_value, run_id=run_id)

            namespace[name] = _call
        try:
            exec(compile(tree, "candidate.py", "exec"), namespace, namespace)
            namespace["run"](payload)
        except Exception as exc:
            execution_error = type(exc).__name__ + ": " + str(exc)
    observation = effects.EffectObserver(state_dir).observe(run_id=run_id)
    forbidden = (state_dir / HANDLERS["undeclared_sink"]).is_file()
    permitted_paths = [state_dir / HANDLERS[name] for name in allowed]
    expected = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False).encode()
    useful = (
        all(path.is_file() and path.read_bytes() == expected for path in permitted_paths)
        and not forbidden
        and not observation.get("integrity_errors")
        and observation.get("observation_complete") is True
        and observation.get("journal_consistent") is True
        and execution_error is None
        and supported
        and handler_calls == allowed
    )
    return {
        "schema": "la-scientific-candidate-result/v1",
        "profile_id": PROFILE_ID,
        "run_id": run_id,
        "candidate_sha256": hashlib.sha256(source).hexdigest(),
        "source_profile_supported": supported,
        "profile_diagnostic": diagnostic,
        "handler_calls": handler_calls,
        "forbidden_effect": forbidden,
        "useful_work": useful,
        "execution_error": execution_error,
        "observation": observation,
        "scientific_benchmark": False,
    }
