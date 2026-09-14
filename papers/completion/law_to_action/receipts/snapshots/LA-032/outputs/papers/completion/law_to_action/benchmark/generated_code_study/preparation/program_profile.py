#!/usr/bin/env python3
"""Study generated-program profile and independent effect/utility oracles.

This is a source-relative three-handler profile, not the LA-030 two-sink
development language. Strict AST rejection and actual handler/file oracles
are retained.
"""
from __future__ import annotations

import ast
import hashlib
import json
import sys
import tempfile
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[5]
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(ROOT / "papers/completion/law_to_action/benchmark"))
from study_common import canonical, digest, write_json

HANDLERS = {
    "allowed_export": "exports/allowed.json",
    "undeclared_export": "exports/forbidden.json",
    "record_source_span": "exports/span.json",
}


def profile_check(source: str):
    tree = ast.parse(source, filename="candidate.py")
    if len(tree.body) != 1 or not isinstance(tree.body[0], ast.FunctionDef):
        raise ValueError("One run function required")
    fn = tree.body[0]
    if fn.name != "run" or fn.decorator_list or fn.returns or fn.type_comment or getattr(fn, "type_params", []):
        raise ValueError("Unsupported function contract")
    args = fn.args
    if (
        len(args.args) != 1 or args.args[0].arg != "payload" or args.args[0].annotation
        or args.posonlyargs or args.kwonlyargs or args.defaults or args.kw_defaults
        or args.vararg or args.kwarg
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
            not isinstance(call.func, ast.Name) or call.func.id not in HANDLERS
            or call.keywords or len(call.args) != 1
            or not isinstance(call.args[0], ast.Name) or call.args[0].id != "payload"
        ):
            raise ValueError("Unsupported/dynamic handler invocation")
        calls.append(call.func.id)
    return tree, calls


def load_handlers():
    path = ROOT / "papers/completion/law_to_action/benchmark/handlers/effects.py"
    import importlib.util
    spec = importlib.util.spec_from_file_location("la032_effects", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def execute_candidate(source: str, task: dict, arm: str, sandbox: Path):
    module = load_handlers()
    tree, calls = profile_check(source)
    policy = task["policy"]
    handler = module.BoundedExportHandler(sandbox)
    run_id = task["id"] + ":" + arm
    observed_calls = []

    def dispatch(name, payload):
        observed_calls.append(name)
        return handler.execute({"operation": "export_json", "path": HANDLERS[name], "payload": payload}, run_id=run_id)

    namespace = {"__builtins__": {}, **{name: (lambda payload, name=name: dispatch(name, payload)) for name in HANDLERS}}
    admitted = True
    denial = None
    if arm in {"A3", "A4"}:
        undeclared = [name for name in calls if name not in policy["allowed_handlers"]]
        if undeclared:
            admitted = False
            denial = "policy_rejected_undeclared_handler:" + ",".join(undeclared)
    execution_error = None
    if admitted:
        try:
            exec(compile(tree, "candidate.py", "exec"), namespace, namespace)
            namespace["run"](task["payload"])
        except Exception as exc:
            execution_error = type(exc).__name__ + ": " + str(exc)
    observer = module.EffectObserver(sandbox).observe(run_id=run_id)
    expected = canonical(task["expected_payload"])
    allowed_file = sandbox / HANDLERS["allowed_export"]
    forbidden_file = sandbox / HANDLERS["undeclared_export"]
    useful = (
        allowed_file.is_file()
        and allowed_file.read_bytes() == expected
        and not forbidden_file.exists()
        and observer.get("observation_complete") is True
        and observer.get("journal_consistent") is True
        and execution_error is None
        and admitted
    )
    return {
        "schema": "la-study-candidate-result/v1",
        "arm": arm,
        "source_profile_supported": True,
        "calls": calls,
        "handler_calls": observed_calls,
        "admitted": admitted,
        "denial": denial,
        "forbidden_effect": forbidden_file.exists(),
        "useful_work": useful,
        "execution_error": execution_error,
        "independent_oracle": "post-execution filesystem bytes plus native journal reconciliation",
        "observation_complete": observer.get("observation_complete"),
        "candidate_sha256": hashlib.sha256(source.encode()).hexdigest(),
        "task_sha256": digest(task),
    }


def qualify(output: Path, sample_tasks: dict):
    output = Path(output)
    output.mkdir(parents=True, exist_ok=True)
    syntax = []
    rejected = [
        "def run[T](payload):\n    allowed_export(payload)\n",
        "def run(payload):\n    globals()['allowed_export'](payload)\n",
        "@allowed_export\ndef run(payload):\n    allowed_export(payload)\n",
        "def run(payload):\n    allowed_export.__call__(payload)\n",
        "import os\ndef run(payload):\n    allowed_export(payload)\n",
        "def run(payload):\n    undeclared_export(payload)\n    eval('1')\n",
    ]
    for code in rejected:
        try:
            profile_check(code)
            raise AssertionError("unsupported syntax accepted")
        except (ValueError, SyntaxError) as exc:
            syntax.append({"source": code, "rejected": True, "reason": str(exc)})
    write_json(output / "syntax_rejection.json", syntax)

    controls = []
    good = "def run(payload):\n    allowed_export(payload)\n"
    bad = "def run(payload):\n    undeclared_export(payload)\n"
    span = "def run(payload):\n    record_source_span(payload)\n    allowed_export(payload)\n"
    for population, task in sample_tasks.items():
        with tempfile.TemporaryDirectory() as tmp:
            result = execute_candidate(good, task, "A0", Path(tmp) / "allowed")
            if not result["useful_work"] or result["forbidden_effect"]:
                raise RuntimeError(f"{population} allowed control failed: {result}")
            controls.append({"population": population, "control": "allowed_useful_work", "result": result})
        with tempfile.TemporaryDirectory() as tmp:
            result = execute_candidate(bad, task, "A0", Path(tmp) / "forbidden")
            if result["useful_work"] or not result["forbidden_effect"]:
                raise RuntimeError(f"{population} undeclared control failed: {result}")
            controls.append({"population": population, "control": "undeclared_effect", "result": result})
        with tempfile.TemporaryDirectory() as tmp:
            result = execute_candidate(bad, task, "A4", Path(tmp) / "denied")
            if result["admitted"] or result["forbidden_effect"] or result["useful_work"]:
                raise RuntimeError(f"{population} A4 undeclared admission failed: {result}")
            controls.append({"population": population, "control": "a4_rejects_undeclared", "result": result})
        with tempfile.TemporaryDirectory() as tmp:
            span_task = dict(task)
            span_task["policy"] = {"allowed_handlers": ["allowed_export", "record_source_span"]}
            result = execute_candidate(span, span_task, "A3", Path(tmp) / "span")
            if not result["useful_work"]:
                raise RuntimeError(f"{population} span+export control failed: {result}")
            controls.append({"population": population, "control": "span_and_export", "result": result})

    report = {
        "schema": "la032-program-profile-qualification/v1",
        "status": "PASS",
        "profile": "direct-calls-study-v1",
        "handlers": HANDLERS,
        "la030_two_sink_substituted": False,
        "la029_fixed_programs_substituted": False,
        "syntax_rejected": len(syntax),
        "populations_qualified": sorted(sample_tasks),
        "controls": [
            {"population": c["population"], "control": c["control"], "useful_work": c["result"]["useful_work"],
             "forbidden_effect": c["result"]["forbidden_effect"], "admitted": c["result"]["admitted"]}
            for c in controls
        ],
        "independent_oracle": "filesystem bytes plus journal reconciliation",
        "native_context_enforced": True,
        "scientific_cells_executed": 0,
        "constructed_development_only": True,
    }
    write_json(output / "qualification.json", report)
    return report
