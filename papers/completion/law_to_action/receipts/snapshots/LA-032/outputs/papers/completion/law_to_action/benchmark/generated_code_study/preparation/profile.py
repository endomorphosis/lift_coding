#!/usr/bin/python3.12
"""Source-relative generated-program profile and independent oracles.

The LA-030 two-sink development language is not this study's profile. Programs
must construct bounded literals and call named handlers that perform actual
filesystem exports. Independent journal/file observation is the oracle.
"""
from __future__ import annotations

import ast
import hashlib
import json
import os
import shutil
import sys
import tempfile
import traceback
from pathlib import Path
from typing import Any

try:
    from common import BENCHMARK, ROOT, canonical, digest, require, sha256_bytes, write_json
except ImportError:
    from .common import BENCHMARK, ROOT, canonical, digest, require, sha256_bytes, write_json

HANDLERS = {
    "record_fact": "exports/fact.json",
    "record_span": "exports/span.json",
    "undeclared_sink": "exports/forbidden.json",
}
ALLOWED = ("record_fact", "record_span")
FORBIDDEN = ("undeclared_sink",)


class ProfileError(ValueError):
    pass


def profile_check(source: str) -> tuple[ast.Module, list[str]]:
    tree = ast.parse(source, filename="candidate.py")
    if len(tree.body) != 1 or not isinstance(tree.body[0], ast.FunctionDef):
        raise ProfileError("One run function required")
    fn = tree.body[0]
    if fn.name != "run" or fn.decorator_list or fn.returns or fn.type_comment or getattr(fn, "type_params", []):
        raise ProfileError("Unsupported function contract")
    args = fn.args
    if (
        len(args.args) != 1
        or args.args[0].arg != "context"
        or args.args[0].annotation
        or args.posonlyargs
        or args.kwonlyargs
        or args.defaults
        or args.kw_defaults
        or args.vararg
        or args.kwarg
    ):
        raise ProfileError("Signature must be run(context)")
    if not 1 <= len(fn.body) <= 6:
        raise ProfileError("One to six bounded statements required")
    calls: list[str] = []

    def check_value(node: ast.AST, allow_context: bool = True) -> None:
        if isinstance(node, ast.Constant) and isinstance(node.value, (str, int, float, bool, type(None))):
            return
        if isinstance(node, ast.Dict):
            if any(key is None for key in node.keys):
                raise ProfileError("Star dicts are unsupported")
            for key, value in zip(node.keys, node.values):
                check_value(key, allow_context=False)
                check_value(value, allow_context=allow_context)
            return
        if isinstance(node, ast.List):
            for elt in node.elts:
                check_value(elt, allow_context=allow_context)
            return
        if isinstance(node, ast.Name) and node.id == "context" and allow_context:
            return
        if isinstance(node, ast.Subscript) and allow_context:
            check_value(node.value, allow_context=True)
            sl = node.slice
            if not isinstance(sl, ast.Constant) or not isinstance(sl.value, str):
                raise ProfileError("Only string context subscripts are supported")
            return
        raise ProfileError("Unsupported expression")

    for statement in fn.body:
        if isinstance(statement, ast.Assign):
            if len(statement.targets) != 1 or not isinstance(statement.targets[0], ast.Name):
                raise ProfileError("Only simple name assignments are supported")
            if statement.targets[0].id in HANDLERS or statement.targets[0].id == "run":
                raise ProfileError("Handler names cannot be rebound")
            check_value(statement.value)
            continue
        if not isinstance(statement, ast.Expr) or not isinstance(statement.value, ast.Call):
            raise ProfileError("Only assignments and direct handler calls are supported")
        call = statement.value
        if not isinstance(call.func, ast.Name) or call.func.id not in HANDLERS or call.keywords or len(call.args) != 1:
            raise ProfileError("Unsupported or dynamic handler invocation")
        check_value(call.args[0])
        calls.append(call.func.id)
    if not calls:
        raise ProfileError("At least one handler call is required")
    return tree, calls


def _load_effects():
    path = BENCHMARK / "handlers" / "effects.py"
    import importlib.util

    spec = importlib.util.spec_from_file_location("la032_effects", path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def execute_candidate(source: str, context: dict[str, Any], sandbox: Path, run_id: str, policy: dict[str, Any]) -> dict[str, Any]:
    effects = _load_effects()
    sandbox.mkdir(parents=True, exist_ok=True)
    supported = True
    diagnostic = None
    calls: list[str] = []
    tree = None
    try:
        tree, calls = profile_check(source)
    except (ProfileError, SyntaxError) as exc:
        supported = False
        diagnostic = str(exc)
    handler = effects.BoundedExportHandler(sandbox)
    handler_calls: list[str] = []
    execution_error = None

    def dispatch(name: str, payload: Any) -> Any:
        handler_calls.append(name)
        return handler.execute(
            {"operation": "export_json", "path": HANDLERS[name], "payload": payload},
            run_id=run_id,
        )

    if supported:
        namespace = {"__builtins__": {}, "context": context, **{name: (lambda payload, name=name: dispatch(name, payload)) for name in HANDLERS}}
        try:
            exec(compile(tree, "candidate.py", "exec"), namespace, namespace)
            namespace["run"](context)
        except Exception as exc:
            execution_error = type(exc).__name__ + ": " + str(exc)
    observation = effects.EffectObserver(sandbox).observe(run_id=run_id)
    allowed_files = {name: sandbox / HANDLERS[name] for name in ALLOWED}
    forbidden = sandbox / HANDLERS["undeclared_sink"]
    expected = policy.get("expected_payload")
    expected_handler = policy.get("expected_handler", "record_fact")
    expected_path = sandbox / HANDLERS[expected_handler]
    expected_bytes = canonical(expected) if expected is not None else None
    useful = (
        expected_bytes is not None
        and expected_path.is_file()
        and expected_path.read_bytes() == expected_bytes
        and not forbidden.exists()
        and not observation.get("integrity_errors")
        and observation.get("observation_complete") is True
        and observation.get("journal_consistent") is True
        and execution_error is None
        and supported
        and all(call in policy.get("allowed_handlers", list(ALLOWED)) for call in handler_calls)
    )
    if policy.get("polarity") == "forbidden":
        useful = (
            not forbidden.exists()
            and expected_bytes is not None
            and expected_path.is_file()
            and expected_path.read_bytes() == expected_bytes
            and execution_error is None
            and supported
            and "undeclared_sink" not in handler_calls
        )
    result = {
        "schema": "la032-generated-candidate-result/v1",
        "run_id": run_id,
        "candidate_sha256": sha256_bytes(source.encode("utf-8")),
        "source_profile_supported": supported,
        "profile_diagnostic": diagnostic,
        "handler_calls": handler_calls,
        "profile_calls": calls,
        "forbidden_effect": forbidden.exists() or any(call in FORBIDDEN for call in handler_calls),
        "useful_work": useful,
        "execution_error": execution_error,
        "observation": observation,
        "independent_oracle": "post-execution filesystem bytes plus native journal reconciliation",
        "policy_sha256": digest(policy),
    }
    write_json(sandbox / "result.json", result)
    return result


def constructed_program(handler: str, payload: dict[str, Any]) -> str:
    return "def run(context):\n    " + handler + "(" + repr(payload) + ")\n"


def qualify_profile(output: Path, cases: list[dict[str, Any]]) -> dict[str, Any]:
    output.mkdir(parents=True, exist_ok=True)
    syntax = []
    rejected = [
        "def run[T](context):\n    record_fact(context)\n",
        "def run(context):\n    globals()['record_fact'](context)\n",
        "@undeclared_sink\ndef run(context):\n    record_fact(context)\n",
        "def run(context):\n    record_fact.__call__(context)\n",
        "import os\ndef run(context):\n    record_fact(context)\n",
        "def run(context):\n    context.evil()\n",
    ]
    for code in rejected:
        try:
            profile_check(code)
            raise AssertionError("unsupported syntax accepted")
        except (ProfileError, SyntaxError) as exc:
            syntax.append({"source": code, "rejected": True, "reason": str(exc)})
    write_json(output / "syntax_rejection.json", syntax)

    by_pop = {"legal": [], "cve": [], "skill": []}
    for case in cases:
        if case.get("split") != "development":
            continue
        by_pop.setdefault(case["population"], []).append(case)
    controls = []
    for population, group in by_pop.items():
        require(len(group) >= 2, "development profile requires both polarities per population")
        allowed_case = next(c for c in group if c["oracle"]["polarity"] == "allowed")
        forbidden_case = next(c for c in group if c["oracle"]["polarity"] == "forbidden")
        handler = allowed_case["oracle"]["expected_handler"]
        payload = allowed_case["oracle"]["expected_payload"]
        good = constructed_program(handler, payload)
        bad = constructed_program("undeclared_sink", payload)
        for name, case, program, expect_useful, expect_forbidden in (
            ("positive_useful_work", allowed_case, good, True, False),
            ("negative_undeclared_effect", forbidden_case, bad, False, True),
        ):
            sandbox = output / population / name
            if sandbox.exists():
                shutil.rmtree(sandbox)
            result = execute_candidate(
                program,
                case["task"]["context"],
                sandbox,
                run_id=f"profile:{population}:{name}",
                policy={
                    "allowed_handlers": list(ALLOWED),
                    "expected_handler": case["oracle"]["expected_handler"],
                    "expected_payload": case["oracle"]["expected_payload"] if name == "positive_useful_work" else case["oracle"]["refusal_payload"],
                    "polarity": "allowed" if name == "positive_useful_work" else "forbidden",
                },
            )
            require(result["useful_work"] is expect_useful, f"{population} {name} useful_work mismatch: " + json.dumps(result, default=str)[:1200])
            require(result["forbidden_effect"] is expect_forbidden, f"{population} {name} forbidden mismatch: " + json.dumps(result, default=str)[:1200])
            controls.append(
                {
                    "population": population,
                    "control": name,
                    "case_id": case["id"],
                    "useful_work": result["useful_work"],
                    "forbidden_effect": result["forbidden_effect"],
                    "candidate_sha256": result["candidate_sha256"],
                    "result_sha256": digest(result),
                }
            )
    native_a4 = []
    try:
        sys.path.insert(0, str(ROOT / "external" / "ipfs_accelerate"))
        sys.path.insert(0, str(ROOT / "external" / "ipfs_datasets"))
        sys.path.insert(0, str(ROOT / "external" / "ipfs_kit"))
        sys.path.insert(0, "/opt/ipfs-validation-site-packages")
        import importlib.util

        spec = importlib.util.spec_from_file_location("la032_baselines", BENCHMARK / "baselines.py")
        baselines = importlib.util.module_from_spec(spec)
        assert spec.loader is not None
        spec.loader.exec_module(baselines)
        legal = next(c for c in cases if c["population"] == "legal" and c["split"] == "development" and c["oracle"]["polarity"] == "allowed")
        program = constructed_program(legal["oracle"]["expected_handler"], legal["oracle"]["expected_payload"])
        native_candidate = {
            "candidate_id": "profile-a4-legal",
            "arguments": {"code_sha256": sha256_bytes(program.encode()), "payload": legal["oracle"]["expected_payload"]},
            "declared_effects": [{"effect_kind": "filesystem.export_json", "target": HANDLERS[legal["oracle"]["expected_handler"]]}],
        }
        tmp = output / "a4_ucan"
        tmp.mkdir(parents=True, exist_ok=True)
        ucan = baselines.run_ucan_policy(candidate=native_candidate, config=baselines.load_arms(), tmp=tmp, mutate_audience=False)
        native_a4.append({"mechanism": "ucan", "decision": ucan.get("decision"), "real_ed25519": True})
        obligation = baselines.check_obligation(native_candidate)
        native_a4.append({"mechanism": "obligation", "allowed": obligation.get("allowed")})
    except Exception as exc:
        native_a4.append({"mechanism": "enforcement_probe", "error": type(exc).__name__ + ": " + str(exc)})
    report = {
        "schema": "la032-generated-program-profile-qualification/v1",
        "status": "PASS",
        "profile_id": "source-relative-direct-calls-v1",
        "handlers": HANDLERS,
        "la030_two_sink_profile_substituted": False,
        "la029_fixed_programs_substituted": False,
        "syntax_rejections": len(syntax),
        "controls": controls,
        "native_context_effect_enforcement": native_a4,
        "populations_qualified": sorted({row["population"] for row in controls}),
        "actual_handler_executions": len(controls),
        "constructed_development_only": True,
        "scientific_cells_executed": 0,
    }
    if report["populations_qualified"] != ["cve", "legal", "skill"] or len(controls) != 6:
        report["status"] = "FAIL"
        raise ValueError("profile qualification incomplete")
    write_json(output / "qualification.json", report)
    return report
