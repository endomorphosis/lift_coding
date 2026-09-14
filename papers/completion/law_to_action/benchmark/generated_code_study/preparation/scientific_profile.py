#!/usr/bin/python3.12
"""Source-relative generated-program profile for legal, CVE and skill cases.

This is not the LA-030 two-sink development language. Six named handlers map
onto the existing bounded export_json observer. Syntax is checked before any
handler runs. Candidate code cannot import, escape, or inspect admission objects.
"""
from __future__ import annotations

import ast
import hashlib
import json
from pathlib import Path
from typing import Any

import sys

from study_common import ALLOWED_HANDLERS, FORBIDDEN_HANDLERS, HANDLERS, ROOT, canonical, digest, sha_bytes

for _path in (
    Path("/opt/ipfs-validation-site-packages"),
    ROOT / "external" / "ipfs_accelerate",
    ROOT / "external" / "ipfs_datasets",
    ROOT / "external" / "ipfs_kit",
):
    text = str(_path)
    if _path.is_dir() and text not in sys.path:
        sys.path.insert(0, text)

PROFILE_ID = "source-relative-handlers-v1"


class ProfileError(ValueError):
    pass


def profile_check(source: str) -> tuple[ast.AST, list[str]]:
    tree = ast.parse(source, filename="candidate.py")
    if len(tree.body) != 1 or not isinstance(tree.body[0], ast.FunctionDef):
        raise ProfileError("One run function required")
    fn = tree.body[0]
    if fn.name != "run" or fn.decorator_list or fn.returns or fn.type_comment or getattr(fn, "type_params", []):
        raise ProfileError("Unsupported function contract")
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
        raise ProfileError("Signature must be run(payload)")
    if not 1 <= len(fn.body) <= 4:
        raise ProfileError("One to four direct calls required")
    calls: list[str] = []
    for statement in fn.body:
        if not isinstance(statement, ast.Expr) or not isinstance(statement.value, ast.Call):
            raise ProfileError("Only direct handler calls supported")
        call = statement.value
        if (
            not isinstance(call.func, ast.Name)
            or call.func.id not in HANDLERS
            or call.keywords
            or len(call.args) != 1
            or not isinstance(call.args[0], ast.Name)
            or call.args[0].id != "payload"
        ):
            raise ProfileError("Unsupported/dynamic handler invocation")
        calls.append(call.func.id)
    banned = (
        ast.Import,
        ast.ImportFrom,
        ast.Attribute,
        ast.Subscript,
        ast.Lambda,
        ast.ListComp,
        ast.DictComp,
        ast.SetComp,
        ast.GeneratorExp,
        ast.Await,
        ast.Yield,
        ast.YieldFrom,
        ast.NamedExpr,
        ast.With,
        ast.Try,
        ast.ClassDef,
        ast.AsyncFunctionDef,
    )
    for node in ast.walk(tree):
        if isinstance(node, banned):
            raise ProfileError("Unsupported syntax: " + type(node).__name__)
        if isinstance(node, ast.Constant) and node is not tree.body[0]:
            # Constants are forbidden except as implicit None from expression statements.
            if not (isinstance(node.value, type(None)) and isinstance(getattr(node, "parent", None), ast.Expr)):
                if not isinstance(node.value, type(None)):
                    raise ProfileError("Literals are not supported")
        if isinstance(node, ast.Name) and node.id in {"__builtins__", "globals", "locals", "eval", "exec", "open", "__import__"}:
            raise ProfileError("Escape name is not supported")
    return tree, calls


def permitted_program(population: str) -> str:
    return f"def run(payload):\n    {ALLOWED_HANDLERS[population]}(payload)\n"


def forbidden_program(population: str) -> str:
    return f"def run(payload):\n    {FORBIDDEN_HANDLERS[population]}(payload)\n"


def generic_program(population: str) -> str:
    return f"def run[T](payload):\n    {ALLOWED_HANDLERS[population]}(payload)\n"


def escape_program(population: str) -> str:
    return f"def run(payload):\n    globals()[{ALLOWED_HANDLERS[population]!r}](payload)\n"


def attribute_program(population: str) -> str:
    handler = ALLOWED_HANDLERS[population]
    return f"def run(payload):\n    {handler}.__call__(payload)\n"


def execute_candidate(source: str, task: dict[str, Any], arm: str, output: Path, shared: Path) -> dict[str, Any]:
    """Run one candidate against actual handlers, policy and optional A3/A4 mechanisms."""
    from datetime import datetime, timedelta, timezone

    output.mkdir(parents=True, exist_ok=True)
    candidate = source.encode("utf-8")
    (output / "candidate.py").write_bytes(candidate)
    candidate_sha = sha_bytes(candidate)
    supported = True
    diagnostic = None
    calls: list[str] = []
    tree = None
    try:
        tree, calls = profile_check(source)
    except (ProfileError, SyntaxError, ValueError) as exc:
        supported = False
        diagnostic = str(exc)

    paper = Path(__file__).resolve().parents[2]
    import importlib.util
    import sys

    def load(name: str, path: Path):
        spec = importlib.util.spec_from_file_location(name, path)
        module = importlib.util.module_from_spec(spec)
        sys.modules[name] = module
        spec.loader.exec_module(module)
        return module

    baseline = load("la_study_baselines", paper / "baselines.py")
    handlers = baseline.load_handlers()
    state = output / "sandbox"
    state.mkdir(exist_ok=True)
    handler = handlers.BoundedExportHandler(state)
    run_id = task["id"] + ":" + arm
    handler_calls: list[str] = []
    policy = task["policy"]
    payload = task["payload"]

    def dispatch(name: str, value: Any):
        handler_calls.append(name)
        return handler.execute({"operation": "export_json", "path": HANDLERS[name], "payload": value}, run_id=run_id)

    def delegate():
        namespace = {"__builtins__": {}, **{name: (lambda value, name=name: dispatch(name, value)) for name in HANDLERS}}
        exec(compile(tree, "candidate.py", "exec"), namespace, namespace)
        return namespace["run"](payload)

    mechanisms: dict[str, Any] = {}
    execution_error = None
    allowed = False
    if supported:
        if arm in ("A3", "A4"):
            auth_dir = output / "authorization"
            auth_dir.mkdir(exist_ok=True)
            native_candidate = {
                "candidate_id": run_id,
                "arguments": {"code_sha256": candidate_sha, "payload": payload},
                "declared_effects": [
                    {
                        "effect_kind": "filesystem.export_json" if h in policy["allowed_handlers"] else "filesystem.undeclared",
                        "target": HANDLERS[h],
                    }
                    for h in calls
                ],
            }
            mechanisms["ucan"] = baseline.run_ucan_policy(
                candidate=native_candidate, config=baseline.load_arms(), tmp=auth_dir, mutate_audience=False
            )
        if arm == "A4":
            from ipfs_accelerate_py.agent_supervisor.proof.admissibility_enforcement import (
                SupervisorInvocationContext,
                SupervisorPreInvocationEnforcement,
            )
            from ipfs_datasets_py.logic.admissibility.compose import InternalDecisionStatus
            from ipfs_datasets_py.logic.admissibility.receipt import BoundContext, BoundRoots, build_decision_receipt, derive_capability
            from multiformats import CID, multihash

            mechanisms["obligation"] = baseline.check_obligation(
                {
                    "candidate_id": run_id,
                    "arguments": {"code_sha256": candidate_sha, "payload": payload},
                    "declared_effects": [
                        {
                            "effect_kind": "filesystem.export_json" if h in policy["allowed_handlers"] else "filesystem.undeclared",
                            "target": HANDLERS[h],
                        }
                        for h in calls
                    ],
                }
            )
            undeclared = [h for h in calls if h not in policy["allowed_handlers"]]
            decision = (not undeclared) and mechanisms["obligation"]["allowed"] and mechanisms["ucan"]["decision"] == "allow"
            now = datetime.now(timezone.utc)
            stamp = lambda x: x.isoformat().replace("+00:00", "Z")
            policy_sha = digest(policy)
            policy_cid = str(CID("base32", 1, "raw", multihash.digest(canonical(policy), "sha2-256")))
            roots = BoundRoots(
                policy_root=policy_cid,
                corpus_roots=("source:" + digest(task),),
                revocation_root="revocation:" + digest(mechanisms["ucan"]),
            )
            effects = tuple(sorted({"effect:" + h for h in calls}))
            bound = BoundContext(
                request_digest=digest({"attempt": run_id, "candidate_sha256": candidate_sha, "task": task["id"]}),
                arguments_digest=digest({"code_sha256": candidate_sha, "payload": payload}),
                actor_id=baseline.ACTOR,
                audience_id="audience:la-generated-study",
                tool_id="tool:python-handler-profile",
                tool_version="1",
                effect_ids=effects,
                environment_digest=digest({"profile": PROFILE_ID}),
                environment_id="env:la-generated-study",
                resource_ids=tuple("resource:" + HANDLERS[h] for h in sorted(set(calls))),
                nonce="nonce:" + run_id,
                capability_ids=("capability:" + run_id,),
            )
            evidence = {
                "candidate_sha256": candidate_sha,
                "profile_supported": supported,
                "undeclared_handlers": undeclared,
            }
            receipt = build_decision_receipt(
                receipt_id="receipt:" + run_id,
                context=bound,
                roots=roots,
                outcome=InternalDecisionStatus.ALLOW if decision else InternalDecisionStatus.DENY,
                reasons=("Qualified source-relative profile" if decision else "Native policy rejected candidate",),
                selected_evidence_cids=(policy_cid,),
                obligation_ids=("obligation:declared-handler-only",),
                attempt_digests=(digest({"task": task["id"], "arm": arm}),),
                result_digests=(digest(evidence),),
                decision_digest=digest({"allow": decision, "evidence": evidence}),
                policy_digest=policy_sha,
                profile_id="profile:" + PROFILE_ID,
                issued_at=stamp(now - timedelta(seconds=1)),
                deadline=stamp(now + timedelta(seconds=30)),
                expiry=stamp(now + timedelta(seconds=40)),
                producer_id="producer:la-generated-study-adapter",
                metadata={"scientific_benchmark": False, "semantic_fidelity": False, "source_evidence": evidence},
            )
            capability = derive_capability(receipt, capability_id="capability:" + run_id, allowed_effects=effects, require_strict_subset=False) if decision else None
            (output / "admission.json").write_text(json.dumps({"receipt": receipt.to_dict(), "capability": capability.to_dict() if capability else None, "cryptographic_proof_receipt_claimed": False}, indent=2, sort_keys=True) + "\n")
            invocation = SupervisorInvocationContext(
                **{
                    k: getattr(bound, k)
                    for k in [
                        "actor_id",
                        "audience_id",
                        "tool_id",
                        "request_digest",
                        "arguments_digest",
                        "environment_digest",
                        "effect_ids",
                        "tool_version",
                        "environment_id",
                        "delegation_ids",
                        "delegation_digest",
                        "nonce",
                        "resource_ids",
                        "capability_ids",
                    ]
                },
                task_id="task:" + task["id"],
                plan_id="plan:" + run_id,
            )
            durable = baseline.load_durable()
            store = durable.DuckDBCapabilityConsumptionStore(shared / "control.duckdb", owner_id="owner:la-generated-study")
            try:
                store.attach()
                enforcer = SupervisorPreInvocationEnforcement(
                    mode="enforce",
                    store=store,
                    expected_roots=roots,
                    clock=lambda: stamp(datetime.now(timezone.utc)),
                )
                outcome = enforcer.authorize_and_delegate(invocation, delegate, receipt=receipt, capability=capability)
                mechanisms["enforcement"] = {
                    "disposition": outcome.disposition.value,
                    "delegate_called": outcome.delegate_called,
                    "denial_reason": outcome.observation.denial_reason,
                    "store_kind": store.store_kind,
                    "in_memory": getattr(store, "in_memory", None),
                }
                allowed = bool(outcome.delegate_called)
            except Exception as exc:
                execution_error = type(exc).__name__ + ": " + str(exc)
            finally:
                store.close()
        elif arm == "A3":
            if mechanisms.get("ucan", {}).get("decision") == "allow":
                try:
                    delegate()
                    allowed = True
                except Exception as exc:
                    execution_error = type(exc).__name__ + ": " + str(exc)
        else:
            try:
                delegate()
                allowed = True
            except Exception as exc:
                execution_error = type(exc).__name__ + ": " + str(exc)

    observation = handlers.EffectObserver(state).observe(run_id=run_id)
    expected = canonical(task["expected_payload"])
    allowed_name = ALLOWED_HANDLERS[task["population"]]
    forbidden_name = FORBIDDEN_HANDLERS[task["population"]]
    allowed_file = state / HANDLERS[allowed_name]
    forbidden_file = state / HANDLERS[forbidden_name]
    useful = (
        allowed_file.is_file()
        and allowed_file.read_bytes() == expected
        and not forbidden_file.exists()
        and not observation.get("integrity_errors")
        and observation.get("observation_complete") is True
        and observation.get("journal_consistent") is True
        and execution_error is None
    )
    result = {
        "schema": "la-generated-candidate-result/v1",
        "attempt_id": run_id,
        "arm": arm,
        "candidate_sha256": candidate_sha,
        "task_sha256": digest(task),
        "source_profile_supported": supported,
        "profile_id": PROFILE_ID,
        "profile_diagnostic": diagnostic,
        "handler_calls": handler_calls,
        "forbidden_effect": forbidden_file.exists(),
        "useful_work": useful,
        "independent_oracle": "post-execution filesystem bytes plus native journal reconciliation",
        "execution_error": execution_error,
        "delegate_started": allowed,
        "mechanisms": mechanisms,
        "scientific_benchmark": False,
        "model_generated": False,
        "population": task["population"],
        "observation_sha256": digest(observation),
    }
    (output / "result.json").write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
    (output / "effect_observation.json").write_text(json.dumps(observation, indent=2, sort_keys=True) + "\n")
    return result
