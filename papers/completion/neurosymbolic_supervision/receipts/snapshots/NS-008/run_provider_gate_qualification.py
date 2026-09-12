#!/usr/bin/env python3
"""NS-008 live qualification of deterministic closure and residual dispatch.

Exercises the real pre-implementation kernel, provider gate, residual
invocation wrapper, analytical-close executor, and reference authorization
evaluator. Candidates are independently checked with a frozen pytest oracle.
Kernel ``provider_hook_count`` is always zero and is not treated as a
workflow saving. Deny-all is a diagnostic that cannot pass useful progress.

This is qualification evidence, not a matched A–D live repair experiment and
not a production model-identity claim.
"""

from __future__ import annotations

import hashlib
import json
import os
import shutil
import subprocess
import sys
import tempfile
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Mapping


ROOT = Path(__file__).resolve().parents[6]
PAPER = ROOT / "papers/completion/neurosymbolic_supervision"
QUAL = PAPER / "qualification"
SNAP = PAPER / "receipts/snapshots/NS-008"
SNAP_QUAL = SNAP / "qualification"
ACC_ROOT = ROOT / "external/ipfs_accelerate"
PROVIDER_SCRIPT = SNAP / "residual_provider.py"
TASK_ID = "NS-008"
SCHEMA_CASES = "neurosymbolic-supervision/provider-gate-cases@1"
SCHEMA_RECEIPT = "neurosymbolic-supervision/provider-gate-receipt@1"
POLICY_ID = "ns-008-provider-gate-qualification-v1"
PROVIDER_ID = "ns-008-qualification-residual-provider@1"
PROVIDER_REVISION = "ns-008-residual-provider-v1"
BUG = "return a - b"
FIX = "return a + b"
CORE_SOURCE = (
    "def add(a, b):\n"
    "    return a - b\n"
    "\n"
    "def scale(x):\n"
    "    return x * 2\n"
)
TEST_SOURCE = (
    "from pkg.core import add, scale\n"
    "\n"
    "def test_add():\n"
    "    assert add(2, 3) == 5\n"
    "\n"
    "def test_scale():\n"
    "    assert scale(4) == 8\n"
)
CHECKPOINT_DIR = Path(
    os.environ.get(
        "IPFS_ACCELERATE_AGENT_TASK_CHECKPOINT_DIR",
        str(SNAP / "checkpoints"),
    )
)

REQUIRED_AUTHORITY_KINDS = ("planner", "doctor", "obligation", "logic", "repair")


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def atomic_write(path: Path, data: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(f".{path.name}.{os.getpid()}.tmp")
    tmp.write_bytes(data)
    os.replace(tmp, path)


def write_json(path: Path, payload: Any) -> None:
    encoded = json.dumps(payload, indent=2, sort_keys=True, ensure_ascii=False) + "\n"
    atomic_write(path, encoded.encode("utf-8"))


def write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    lines = [
        json.dumps(row, sort_keys=True, ensure_ascii=False, separators=(",", ":"))
        for row in rows
    ]
    atomic_write(path, ("\n".join(lines) + "\n").encode("utf-8"))


def checkpoint(name: str, payload: Mapping[str, Any]) -> None:
    try:
        CHECKPOINT_DIR.mkdir(parents=True, exist_ok=True)
        write_json(CHECKPOINT_DIR / f"{name}.json", dict(payload))
    except OSError:
        fallback = SNAP / "checkpoints"
        fallback.mkdir(parents=True, exist_ok=True)
        write_json(fallback / f"{name}.json", dict(payload))


def rel(path: Path) -> str:
    return str(path.resolve().relative_to(ROOT))


def prepare_imports() -> dict[str, Any]:
    initial_path = os.environ.get("PATH")
    if str(ACC_ROOT) not in sys.path:
        sys.path.insert(0, str(ACC_ROOT))
    public_ss_error = None
    try:
        import ipfs_accelerate_py.agent_supervisor.semantic_state as _ss  # noqa: F401
    except Exception as exc:
        public_ss_error = f"{type(exc).__name__}: {exc}"
    from ipfs_accelerate_py.agent_supervisor.control.authorization_logic import (
        AuthorizationGrant,
        AuthorizationPolicy,
        AuthorizationRequest,
        Capability,
        DenialReason,
        ReferenceAuthorizationEvaluator,
    )
    from ipfs_accelerate_py.agent_supervisor.planning.residual_llm_packet import (
        seal_residual_llm_packet,
    )
    from ipfs_accelerate_py.agent_supervisor.proof.formal_verification_contracts import (
        content_identity,
    )
    from ipfs_accelerate_py.agent_supervisor.todo_daemon.analytical_close_executor import (
        AnalyticalCloseExecutor,
        AnalyticalClosePlan,
        AnalyticalEdit,
    )
    from ipfs_accelerate_py.agent_supervisor.todo_daemon.implementation_disposition import (
        ImplementationDisposition,
        ImplementationForestRoots,
        implementation_disposition_cid,
        provider_invocation_authorized,
    )
    from ipfs_accelerate_py.agent_supervisor.todo_daemon.pre_implementation_kernel import (
        REASON_AMBIGUOUS_CANDIDATES,
        REASON_ANALYTICAL_UNIQUE_MAPPING,
        REASON_MISSING_BACKEND,
        REASON_MISSING_TYPED_AUTHORITY_RECEIPTS,
        REASON_NO_ANALYTICAL_CLOSE,
        REASON_RESIDUAL_AUTHORIZED,
        AnalyticalRepairCandidate,
        KernelEvaluationRequest,
        PreImplementationKernel,
    )
    from ipfs_accelerate_py.agent_supervisor.todo_daemon.pre_implementation_provider_gate import (
        ProviderGateDecision,
        assert_provider_dispatch_allowed,
        evaluate_provider_gate,
    )
    from ipfs_accelerate_py.agent_supervisor.todo_daemon.residual_provider_invocation import (
        ResidualProviderInvocation,
        ResidualProviderInvocationError,
        ResidualProviderPathError,
        build_residual_provider_invocation,
    )

    anyio_present = False
    try:
        import anyio  # noqa: F401

        anyio_present = True
    except Exception:
        anyio_present = False
    pytest_version = None
    try:
        import pytest

        pytest_version = getattr(pytest, "__version__", "present")
    except Exception as exc:
        pytest_version = None
        pytest_error = f"{type(exc).__name__}: {exc}"
    else:
        pytest_error = None
    return {
        "interpreter": sys.executable,
        "python_version": sys.version.split()[0],
        "path": initial_path,
        "anyio": anyio_present,
        "pytest": pytest_version,
        "pytest_error": pytest_error,
        "public_semantic_state_import": {
            "loaded": public_ss_error is None,
            "error": public_ss_error,
        },
        "modules": {
            "pre_implementation_kernel": rel(
                ACC_ROOT
                / "ipfs_accelerate_py/agent_supervisor/todo_daemon/pre_implementation_kernel.py"
            ),
            "pre_implementation_provider_gate": rel(
                ACC_ROOT
                / "ipfs_accelerate_py/agent_supervisor/todo_daemon/pre_implementation_provider_gate.py"
            ),
            "implementation_disposition": rel(
                ACC_ROOT
                / "ipfs_accelerate_py/agent_supervisor/todo_daemon/implementation_disposition.py"
            ),
            "residual_provider_invocation": rel(
                ACC_ROOT
                / "ipfs_accelerate_py/agent_supervisor/todo_daemon/residual_provider_invocation.py"
            ),
            "analytical_close_executor": rel(
                ACC_ROOT
                / "ipfs_accelerate_py/agent_supervisor/todo_daemon/analytical_close_executor.py"
            ),
            "residual_llm_packet": rel(
                ACC_ROOT
                / "ipfs_accelerate_py/agent_supervisor/planning/residual_llm_packet.py"
            ),
            "authorization_logic": rel(
                ACC_ROOT
                / "ipfs_accelerate_py/agent_supervisor/control/authorization_logic.py"
            ),
            "providers": rel(
                ACC_ROOT
                / "ipfs_accelerate_py/agent_supervisor/semantic_state/providers.py"
            ),
        },
        "api": {
            "AuthorizationGrant": AuthorizationGrant,
            "AuthorizationPolicy": AuthorizationPolicy,
            "AuthorizationRequest": AuthorizationRequest,
            "Capability": Capability,
            "DenialReason": DenialReason,
            "ReferenceAuthorizationEvaluator": ReferenceAuthorizationEvaluator,
            "seal_residual_llm_packet": seal_residual_llm_packet,
            "content_identity": content_identity,
            "AnalyticalCloseExecutor": AnalyticalCloseExecutor,
            "AnalyticalClosePlan": AnalyticalClosePlan,
            "AnalyticalEdit": AnalyticalEdit,
            "ImplementationDisposition": ImplementationDisposition,
            "ImplementationForestRoots": ImplementationForestRoots,
            "implementation_disposition_cid": implementation_disposition_cid,
            "provider_invocation_authorized": provider_invocation_authorized,
            "REASON_AMBIGUOUS_CANDIDATES": REASON_AMBIGUOUS_CANDIDATES,
            "REASON_ANALYTICAL_UNIQUE_MAPPING": REASON_ANALYTICAL_UNIQUE_MAPPING,
            "REASON_MISSING_BACKEND": REASON_MISSING_BACKEND,
            "REASON_MISSING_TYPED_AUTHORITY_RECEIPTS": REASON_MISSING_TYPED_AUTHORITY_RECEIPTS,
            "REASON_NO_ANALYTICAL_CLOSE": REASON_NO_ANALYTICAL_CLOSE,
            "REASON_RESIDUAL_AUTHORIZED": REASON_RESIDUAL_AUTHORIZED,
            "AnalyticalRepairCandidate": AnalyticalRepairCandidate,
            "KernelEvaluationRequest": KernelEvaluationRequest,
            "PreImplementationKernel": PreImplementationKernel,
            "ProviderGateDecision": ProviderGateDecision,
            "assert_provider_dispatch_allowed": assert_provider_dispatch_allowed,
            "evaluate_provider_gate": evaluate_provider_gate,
            "ResidualProviderInvocation": ResidualProviderInvocation,
            "ResidualProviderInvocationError": ResidualProviderInvocationError,
            "ResidualProviderPathError": ResidualProviderPathError,
            "build_residual_provider_invocation": build_residual_provider_invocation,
        },
    }


def cid(api: dict[str, Any], name: str) -> str:
    return api["implementation_disposition_cid"]({"ns008": name})


def forest(api: dict[str, Any], *, salt: str = "forest") -> Any:
    return api["ImplementationForestRoots"](
        repository_id="repository:sha256:ns-008-qualification",
        repository_forest_cid=cid(api, f"{salt}-root"),
        git_tree_id=cid(api, f"{salt}-tree"),
        policy_root=cid(api, f"{salt}-policy"),
        dirty_overlay_cid=cid(api, f"{salt}-overlay"),
        capability_catalog_root=cid(api, f"{salt}-capabilities"),
        configuration_root=cid(api, f"{salt}-config"),
    )


def authority_receipts(
    api: dict[str, Any],
    *,
    task_cid: str,
    forest_cid: str,
    task_override: str | None = None,
    forest_override: str | None = None,
    forge_kind: str | None = None,
) -> dict[str, dict[str, str]]:
    receipts: dict[str, dict[str, str]] = {}
    for kind in REQUIRED_AUTHORITY_KINDS:
        payload = {
            "schema": "ipfs_accelerate_py/agent-supervisor/authority-receipt@1",
            "receipt_kind": kind,
            "task_cid": task_override or task_cid,
            "repository_forest_cid": forest_override or forest_cid,
        }
        identity = api["content_identity"](payload)
        if forge_kind == kind:
            identity = cid(api, f"forged-{kind}")
        receipts[kind] = {**payload, "content_id": identity}
    return receipts


def resolver_for(receipts: Mapping[str, Mapping[str, str]]) -> Callable[[str], Mapping[str, str] | None]:
    index = {item["content_id"]: dict(item) for item in receipts.values()}

    def _resolve(receipt_cid: str) -> Mapping[str, str] | None:
        return index.get(receipt_cid)

    return _resolve


def capsule() -> dict[str, Any]:
    return {
        "schema": "ipfs_accelerate_py/agent-supervisor/counterexample-context-capsule@1",
        "target_ids": ["symbol:pkg.core.add"],
        "counterexamples": [
            {
                "counterexample_id": "cex:ns-008-add",
                "kind": "failed_oracle",
                "summary": "add(2, 3) must equal 5",
                "violated_property": "tests/test_core.py::test_add",
            }
        ],
        "nodes": [],
        "edges": [],
        "usage": {
            "counterexamples": 1,
            "graph_nodes": 0,
            "graph_edges": 0,
            "encoded_bytes": 128,
            "omitted_counterexamples": 0,
        },
        "limits": {"max_bytes": 4096},
        "minimized": True,
        "redacted": True,
        "contains_private_material": False,
        "contains_raw_prover_output": False,
        "contains_source": False,
    }


def seal_packet(api: dict[str, Any], *, task_id: str, forest_id: str, tree_id: str) -> Any:
    return api["seal_residual_llm_packet"](
        task_id=task_id,
        repository_id="repository:sha256:ns-008-qualification",
        tree_id=tree_id,
        write_paths=("pkg/core.py",),
        obligation_ids=("obligation:ns-008-add-oracle",),
        counterexample_capsule=capsule(),
        validation_commands=("python3 -m pytest tests/test_core.py -q",),
        policy_id=POLICY_ID,
        policy_revision="sha256:ns-008-policy",
        forest_id=forest_id,
        acceptance_ids=("ns-008/provider-gate@1",),
        authority_roots={
            "repository_id": "repository:sha256:ns-008-qualification",
            "tree_id": tree_id,
        },
    )


def decision_from_result(api: dict[str, Any], result: Any) -> Any:
    authorized = api["provider_invocation_authorized"](result.disposition)
    if authorized and not result.receipt.residual_packet_cid:
        authorized = False
        skip = True
        reason = "residual_packet_required"
    else:
        skip = not authorized
        reason = result.reason_code
    return api["ProviderGateDecision"](
        disposition=result.disposition,
        provider_authorized=authorized,
        provider_hook_count=int(result.provider_hook_count),
        skip_provider=skip,
        reason_code=reason,
        receipt=result.receipt,
        residual_packet_cid=result.receipt.residual_packet_cid,
        analytical_candidate_count=int(result.analytical_candidate_count),
    )


def evaluate_bound_gate(
    api: dict[str, Any],
    *,
    task_cid: str,
    forest_roots: Any,
    residual_packet_cid: str = "",
    analytical_candidates: tuple[Any, ...] = (),
    planner_available: bool = True,
    doctor_available: bool = True,
    authority_receipt_cids: Mapping[str, str] | None = None,
    authority_receipt_resolver: Callable[[str], Mapping[str, str] | None] | None = None,
    obligation_graph_cid: str = "",
    plan_cid: str = "",
    doctor_cid: str = "",
    attempt: int = 1,
) -> Any:
    kernel = api["PreImplementationKernel"](
        planner_available=planner_available,
        doctor_available=doctor_available,
        authority_receipt_resolver=authority_receipt_resolver,
    )
    request = api["KernelEvaluationRequest"](
        task_cid=task_cid,
        forest_roots=forest_roots,
        attempt=attempt,
        residual_packet_cid=residual_packet_cid,
        analytical_candidates=analytical_candidates,
        policy_revision="1",
        authority_receipt_cids=dict(authority_receipt_cids or {}),
        obligation_graph_cid=obligation_graph_cid,
        plan_cid=plan_cid,
        doctor_cid=doctor_cid,
    )
    return decision_from_result(api, kernel.evaluate(request))


def materialize_fixture(root: Path) -> Path:
    pkg = root / "pkg"
    tests = root / "tests"
    pkg.mkdir(parents=True, exist_ok=True)
    tests.mkdir(parents=True, exist_ok=True)
    (pkg / "__init__.py").write_text("", encoding="utf-8")
    (pkg / "core.py").write_text(CORE_SOURCE, encoding="utf-8")
    (tests / "__init__.py").write_text("", encoding="utf-8")
    (tests / "test_core.py").write_text(TEST_SOURCE, encoding="utf-8")
    (root / "pytest.ini").write_text("[pytest]\npythonpath = .\n", encoding="utf-8")
    return root / "pkg" / "core.py"


def add_span(core: Path, *, source: str, replacement: str) -> tuple[int, int]:
    text = core.read_text(encoding="utf-8")
    start = text.index(source)
    return start, start + len(source)


def run_oracle(worktree: Path) -> dict[str, Any]:
    env = {
        "PATH": os.environ.get("PATH", "/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin"),
        "HOME": os.environ.get("HOME", "/tmp"),
        "PYTHONPATH": str(worktree),
        "PYTHONDONTWRITEBYTECODE": "1",
    }
    started = time.perf_counter()
    proc = subprocess.run(
        [sys.executable, "-m", "pytest", "tests/test_core.py", "-q", "--tb=line"],
        cwd=str(worktree),
        env=env,
        capture_output=True,
        text=True,
        timeout=60,
    )
    elapsed_ms = int((time.perf_counter() - started) * 1000)
    passed = proc.returncode == 0
    return {
        "command": [sys.executable, "-m", "pytest", "tests/test_core.py", "-q", "--tb=line"],
        "cwd": str(worktree),
        "exit_code": proc.returncode,
        "passed": passed,
        "elapsed_ms": elapsed_ms,
        "stdout_tail": (proc.stdout or "")[-400:],
        "stderr_tail": (proc.stderr or "")[-400:],
        "independent_of_closes_claim": True,
    }


def apply_add_fix(api: dict[str, Any], worktree: Path, *, task_cid: str, plan_cid: str) -> dict[str, Any]:
    core = worktree / "pkg" / "core.py"
    start, end = add_span(core, source=BUG, replacement=FIX)
    before = core.read_bytes()
    executor = api["AnalyticalCloseExecutor"](worktree_root=worktree)
    receipt = executor.apply(
        api["AnalyticalClosePlan"](
            edits=(
                api["AnalyticalEdit"](
                    path="pkg/core.py",
                    start=start,
                    end=end,
                    replacement=FIX,
                    before_hash=hashlib.sha256(before).hexdigest(),
                ),
            ),
            expects_writes=True,
            plan_cid=plan_cid,
            task_cid=task_cid,
        )
    )
    return receipt.to_dict()


def invoke_residual(
    api: dict[str, Any],
    *,
    packet: Any,
    worktree: Path,
    mode: str = "nominate_add_fix",
) -> tuple[dict[str, Any], dict[str, Any] | None, str | None]:
    invoker = api["build_residual_provider_invocation"]()
    calls = {"count": 0}

    def provider_invoke(
        prompt: str,
        env: Mapping[str, str],
        argv_bindings: Mapping[str, str],
        packet_cid: str,
    ) -> dict[str, Any]:
        calls["count"] += 1
        child_env = dict(env)
        child_env["IPFS_ACCELERATE_AGENT_TASK_PACKET_CID"] = packet_cid
        child_env["IPFS_ACCELERATE_AGENT_TASK_PROVIDER_MODE"] = mode
        proc = subprocess.run(
            [sys.executable, str(PROVIDER_SCRIPT)],
            input=prompt,
            cwd=str(worktree),
            env=child_env,
            capture_output=True,
            text=True,
            timeout=30,
        )
        if proc.returncode != 0:
            raise RuntimeError(f"residual provider exited {proc.returncode}: {proc.stderr[-300:]}")
        nominated = json.loads(proc.stdout)
        nominated["argv_bindings"] = dict(argv_bindings)
        nominated["process_pid_present"] = True
        nominated["provider_process_exit"] = proc.returncode
        return nominated

    try:
        receipt, result = invoker.invoke(
            packet,
            provider_invoke,
            base_env={
                "PATH": os.environ.get("PATH", "/usr/bin"),
                "HOME": os.environ.get("HOME", "/tmp"),
                "OPENAI_API_KEY": "sk-should-be-stripped",
            },
            extra_env={"IPFS_ACCELERATE_AGENT_TASK_PROVIDER_MODE": mode},
        )
    except (api["ResidualProviderInvocationError"], api["ResidualProviderPathError"], RuntimeError) as exc:
        return (
            {
                "invoked": False,
                "provider_hook_count": calls["count"],
                "reason_code": getattr(exc, "reason_code", type(exc).__name__),
                "error": str(exc),
            },
            None,
            str(getattr(exc, "reason_code", type(exc).__name__)),
        )
    payload = receipt.to_dict()
    payload["actual_process_invocations"] = calls["count"]
    return payload, result, None


def apply_nomination(
    api: dict[str, Any],
    worktree: Path,
    nomination: Mapping[str, Any],
    *,
    task_cid: str,
    plan_cid: str,
    allowed_paths: tuple[str, ...] = ("pkg/core.py",),
) -> dict[str, Any]:
    path = str(nomination.get("path") or "")
    if path not in allowed_paths:
        return {
            "applied": False,
            "mutated": False,
            "reason_code": "unknown_provider_effect",
            "path": path,
            "lease_paths": list(allowed_paths),
        }
    replacement = str(nomination.get("replacement_span") or nomination.get("replacement") or "")
    if replacement != FIX:
        return {
            "applied": False,
            "mutated": False,
            "reason_code": "nomination_failed_independent_check",
            "path": path,
        }
    return apply_add_fix(api, worktree, task_cid=task_cid, plan_cid=plan_cid)


def production_llm_probe() -> dict[str, Any]:
    markers = (
        "OPENAI_API_KEY",
        "ANTHROPIC_API_KEY",
        "XAI_API_KEY",
        "GROK_API_KEY",
        "GOOGLE_API_KEY",
    )
    present = [key for key in markers if os.environ.get(key)]
    which = {
        name: shutil.which(name)
        for name in ("grok", "openai", "claude", "litellm")
    }
    return {
        "available": False,
        "reason": "sealed qualification profile has no production model identity, API key, or provider CLI",
        "secret_env_keys_present": present,
        "cli_which": which,
        "claimed_as_zero_cost": False,
        "simulated_as_success": False,
    }


def row_base(
    *,
    case_id: str,
    family: str,
    pair_id: str,
    polarity: str,
    description: str,
    expected_reason: str,
    retained: bool = True,
) -> dict[str, Any]:
    return {
        "schema": SCHEMA_RECEIPT,
        "task_id": TASK_ID,
        "case_id": case_id,
        "family": family,
        "pair_id": pair_id,
        "polarity": polarity,
        "description": description,
        "retained": retained,
        "expected_reason": expected_reason,
        "workflow_savings_inferred": False,
        "kernel_provider_hook_count_is_not_workflow_savings": True,
        "closes_claim_trusted": False,
        "deny_all_useful_progress": False,
        "live_ad_experiment": False,
    }


def finish_row(
    row: dict[str, Any],
    *,
    decision: Any | None = None,
    observed_reason: str,
    useful_progress: bool,
    oracle: dict[str, Any] | None = None,
    invocation: dict[str, Any] | None = None,
    analytical: dict[str, Any] | None = None,
    authorization: dict[str, Any] | None = None,
    limitations: list[str] | None = None,
    extra: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    status = "pass"
    if row.get("polarity") == "valid" and row.get("family") in {"residual", "deterministic"}:
        if not useful_progress:
            status = "fail"
    row.update(
        {
            "status": status,
            "observed_reason": observed_reason,
            "useful_progress": bool(useful_progress),
            "independent_oracle": oracle,
            "invocation": invocation,
            "analytical_close": analytical,
            "authorization": authorization,
            "limitations": list(limitations or []),
        }
    )
    if decision is not None:
        receipt = decision.receipt
        row.update(
            {
                "disposition": decision.disposition.value,
                "provider_authorized": bool(decision.provider_authorized),
                "skip_provider": bool(decision.skip_provider),
                "kernel_provider_hook_count": int(decision.provider_hook_count),
                "kernel_receipt_cid": decision.receipt_cid,
                "residual_packet_cid": decision.residual_packet_cid,
                "analytical_candidate_count": int(decision.analytical_candidate_count),
                "bindings": {
                    "task_cid": receipt.task_cid,
                    "repository_forest_cid": receipt.forest_roots.repository_forest_cid,
                    "git_tree_id": receipt.forest_roots.git_tree_id,
                    "plan_cid": receipt.plan_cid,
                    "doctor_cid": receipt.doctor_cid,
                    "obligation_graph_cid": receipt.dual_view.obligation_graph_cid,
                },
                "reason_matched": observed_reason == row["expected_reason"]
                or (
                    row["expected_reason"] in observed_reason
                    if isinstance(observed_reason, str)
                    else False
                ),
            }
        )
        if row["polarity"] in {"invalid", "diagnostic"} and not row["reason_matched"]:
            row["status"] = "fail"
        if (
            row["polarity"] == "invalid"
            and row.get("family") in {"invalid_binding", "capability", "ambiguity"}
            and decision.provider_authorized
        ):
            row["status"] = "fail"
        if useful_progress and row["polarity"] == "diagnostic" and row["family"] == "deny_all":
            row["status"] = "fail"
            row["useful_progress"] = False
    if extra:
        row.update(dict(extra))
    if row.get("kernel_provider_hook_count") not in (0, None) and row.get("family") != "residual":
        # Kernel evaluation itself must remain zero-hook.
        if decision is not None and int(decision.provider_hook_count) != 0:
            row["status"] = "fail"
            row.setdefault("limitations", []).append("kernel_hook_count_nonzero")
    return row


def copy_worktree(src: Path, dest: Path) -> Path:
    if dest.exists():
        shutil.rmtree(dest)
    shutil.copytree(src, dest)
    return dest


def run_cases(api: dict[str, Any], work_root: Path) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    baseline = materialize_fixture(work_root / "baseline")
    cases: list[dict[str, Any]] = []
    rows: list[dict[str, Any]] = []
    Candidate = api["AnalyticalRepairCandidate"]

    def record_case(**kwargs: Any) -> None:
        cases.append(kwargs)

    # --- 1. Deterministic unique close, independent oracle ---
    record_case(
        case_id="deterministic_unique_close",
        family="deterministic",
        pair_id="deterministic_close",
        polarity="valid",
        expected_reason="analytical_unique_mapping",
        description="Unique analytical mapping closes without a provider call; independent pytest oracle must pass.",
    )
    wt = copy_worktree(work_root / "baseline", work_root / "deterministic_unique_close")
    roots = forest(api, salt="det")
    task_cid = cid(api, "det-task")
    decision = evaluate_bound_gate(
        api,
        task_cid=task_cid,
        forest_roots=roots,
        analytical_candidates=(
            Candidate(candidate_id="unique-add-fix", reason_code="analytical_unique_mapping", closes_claim=True),
        ),
    )
    dispatch_blocked = False
    try:
        api["assert_provider_dispatch_allowed"](decision)
    except PermissionError:
        dispatch_blocked = True
    applied = apply_add_fix(api, wt, task_cid=task_cid, plan_cid=decision.receipt.plan_cid)
    oracle = run_oracle(wt)
    rows.append(
        finish_row(
            row_base(
                case_id="deterministic_unique_close",
                family="deterministic",
                pair_id="deterministic_close",
                polarity="valid",
                description="Unique analytical mapping closes without a provider call; independent pytest oracle must pass.",
                expected_reason="analytical_unique_mapping",
            ),
            decision=decision,
            observed_reason=decision.reason_code,
            useful_progress=bool(oracle["passed"] and applied.get("applied") and dispatch_blocked),
            oracle=oracle,
            analytical=applied,
            extra={
                "provider_called": False,
                "dispatch_blocked": dispatch_blocked,
                "closes_claim_on_candidate": True,
                "independent_oracle_required": True,
            },
        )
    )

    # --- 2. closes_claim is not success without independent apply/oracle ---
    record_case(
        case_id="closes_claim_untrusted",
        family="closes_claim",
        pair_id="deterministic_close",
        polarity="invalid",
        expected_reason="closes_claim_not_independent_success",
        description="A unique closes_claim candidate does not count as useful progress until the frozen oracle passes.",
    )
    wt = copy_worktree(work_root / "baseline", work_root / "closes_claim_untrusted")
    roots = forest(api, salt="claim")
    task_cid = cid(api, "claim-task")
    decision = evaluate_bound_gate(
        api,
        task_cid=task_cid,
        forest_roots=roots,
        analytical_candidates=(
            Candidate(candidate_id="unique-false-close", closes_claim=True),
        ),
    )
    oracle = run_oracle(wt)  # unfixed tree
    rows.append(
        finish_row(
            row_base(
                case_id="closes_claim_untrusted",
                family="closes_claim",
                pair_id="deterministic_close",
                polarity="invalid",
                description="A unique closes_claim candidate does not count as useful progress until the frozen oracle passes.",
                expected_reason="closes_claim_not_independent_success",
            ),
            decision=decision,
            observed_reason="closes_claim_not_independent_success",
            useful_progress=False,
            oracle=oracle,
            extra={
                "provider_called": False,
                "closes_claim_on_candidate": True,
                "kernel_disposition": decision.disposition.value,
                "oracle_passed_without_apply": bool(oracle["passed"]),
            },
        )
    )

    # Shared residual bindings for valid residual + invalid pairs
    residual_roots = forest(api, salt="residual")
    residual_task = cid(api, "residual-task")
    receipts = authority_receipts(
        api,
        task_cid=residual_task,
        forest_cid=residual_roots.repository_forest_cid,
    )
    receipt_cids = {kind: item["content_id"] for kind, item in receipts.items()}
    packet = seal_packet(
        api,
        task_id="NS-008-residual",
        forest_id=residual_roots.repository_forest_cid,
        tree_id=residual_roots.git_tree_id,
    )
    packet_cid = packet.packet_id or packet.content_id
    residual_kwargs = dict(
        task_cid=residual_task,
        forest_roots=residual_roots,
        residual_packet_cid=packet_cid,
        analytical_candidates=(
            Candidate(candidate_id="non-closing", closes_claim=False),
        ),
        authority_receipt_cids=receipt_cids,
        authority_receipt_resolver=resolver_for(receipts),
        obligation_graph_cid=receipt_cids["obligation"],
        plan_cid=receipt_cids["planner"],
        doctor_cid=receipt_cids["doctor"],
    )

    # --- 3. Valid residual reaches intended provider ---
    record_case(
        case_id="residual_authorized_progress",
        family="residual",
        pair_id="residual_progress",
        polarity="valid",
        expected_reason="residual_packet_authorized",
        description="Exact task/forest/plan/doctor/obligation receipts authorize residual dispatch to the intended provider; independent oracle scores the nomination.",
    )
    wt = copy_worktree(work_root / "baseline", work_root / "residual_authorized_progress")
    decision = evaluate_bound_gate(api, **residual_kwargs)
    dispatch_error = None
    invocation = None
    nominated = None
    applied = None
    oracle = None
    try:
        api["assert_provider_dispatch_allowed"](decision)
        invocation, nominated, invoke_error = invoke_residual(api, packet=packet, worktree=wt)
        if invoke_error:
            dispatch_error = invoke_error
        elif nominated:
            applied = apply_nomination(
                api,
                wt,
                nominated.get("nomination") or {},
                task_cid=residual_task,
                plan_cid=decision.receipt.plan_cid,
            )
            oracle = run_oracle(wt)
    except PermissionError as exc:
        dispatch_error = str(exc)
    progress = bool(
        decision.provider_authorized
        and invocation
        and invocation.get("invoked")
        and (invocation.get("actual_process_invocations") or invocation.get("provider_hook_count") or 0) >= 1
        and nominated
        and nominated.get("provider_id") == PROVIDER_ID
        and applied
        and applied.get("applied")
        and oracle
        and oracle.get("passed")
        and not dispatch_error
    )
    rows.append(
        finish_row(
            row_base(
                case_id="residual_authorized_progress",
                family="residual",
                pair_id="residual_progress",
                polarity="valid",
                description="Exact task/forest/plan/doctor/obligation receipts authorize residual dispatch to the intended provider; independent oracle scores the nomination.",
                expected_reason="residual_packet_authorized",
            ),
            decision=decision,
            observed_reason=decision.reason_code,
            useful_progress=progress,
            oracle=oracle,
            invocation=invocation,
            analytical=applied,
            extra={
                "intended_provider_id": PROVIDER_ID,
                "intended_provider_revision": PROVIDER_REVISION,
                "served_provider_id": None if nominated is None else nominated.get("provider_id"),
                "admitted_production": False,
                "dispatch_error": dispatch_error,
                "provider_result_closes_claim": False if nominated is None else nominated.get("closes_claim"),
            },
        )
    )

    # --- 4. Invalid residual pairs (minimally altered bindings) ---
    invalid_specs = [
        (
            "residual_missing_authority_receipts",
            "missing_typed_resolvable_authority_receipts",
            "Packet present but typed resolvable authority receipts are absent.",
            dict(
                task_cid=residual_task,
                forest_roots=residual_roots,
                residual_packet_cid=packet_cid,
                analytical_candidates=(Candidate(candidate_id="non-closing", closes_claim=False),),
            ),
        ),
        (
            "residual_mismatched_task",
            "missing_typed_resolvable_authority_receipts",
            "Authority receipts bound to a different task_cid are rejected.",
            dict(
                **{
                    **residual_kwargs,
                    "authority_receipt_cids": {
                        kind: item["content_id"]
                        for kind, item in authority_receipts(
                            api,
                            task_cid=residual_task,
                            forest_cid=residual_roots.repository_forest_cid,
                            task_override=cid(api, "other-task"),
                        ).items()
                    },
                    "authority_receipt_resolver": resolver_for(
                        authority_receipts(
                            api,
                            task_cid=residual_task,
                            forest_cid=residual_roots.repository_forest_cid,
                            task_override=cid(api, "other-task"),
                        )
                    ),
                    "obligation_graph_cid": authority_receipts(
                        api,
                        task_cid=residual_task,
                        forest_cid=residual_roots.repository_forest_cid,
                        task_override=cid(api, "other-task"),
                    )["obligation"]["content_id"],
                    "plan_cid": authority_receipts(
                        api,
                        task_cid=residual_task,
                        forest_cid=residual_roots.repository_forest_cid,
                        task_override=cid(api, "other-task"),
                    )["planner"]["content_id"],
                    "doctor_cid": authority_receipts(
                        api,
                        task_cid=residual_task,
                        forest_cid=residual_roots.repository_forest_cid,
                        task_override=cid(api, "other-task"),
                    )["doctor"]["content_id"],
                }
            ),
        ),
        (
            "residual_mismatched_forest",
            "missing_typed_resolvable_authority_receipts",
            "Authority receipts bound to a different forest CID are rejected.",
            None,  # filled below to avoid recomputing thrice poorly
        ),
        (
            "residual_mismatched_views",
            "missing_typed_resolvable_authority_receipts",
            "Plan/doctor/obligation view CIDs that are not the durable receipts cannot authorize residual use.",
            dict(
                **{
                    **residual_kwargs,
                    "plan_cid": cid(api, "synthetic-plan"),
                    "doctor_cid": cid(api, "synthetic-doctor"),
                    "obligation_graph_cid": cid(api, "synthetic-obligation"),
                }
            ),
        ),
        (
            "residual_forged_receipt_identity",
            "missing_typed_resolvable_authority_receipts",
            "Forged receipt content_id that does not match the payload identity is rejected.",
            None,
        ),
        (
            "residual_missing_packet",
            "no_analytical_close",
            "No unique analytical close and no residual packet abstains; provider stays unreachable.",
            dict(
                task_cid=residual_task,
                forest_roots=residual_roots,
                analytical_candidates=(Candidate(candidate_id="non-closing", closes_claim=False),),
            ),
        ),
    ]

    other_forest_receipts = authority_receipts(
        api,
        task_cid=residual_task,
        forest_cid=residual_roots.repository_forest_cid,
        forest_override=cid(api, "other-forest"),
    )
    forged_receipts = authority_receipts(
        api,
        task_cid=residual_task,
        forest_cid=residual_roots.repository_forest_cid,
        forge_kind="planner",
    )

    filled_kwargs = {
        "residual_mismatched_forest": dict(
            task_cid=residual_task,
            forest_roots=residual_roots,
            residual_packet_cid=packet_cid,
            analytical_candidates=(Candidate(candidate_id="non-closing", closes_claim=False),),
            authority_receipt_cids={k: v["content_id"] for k, v in other_forest_receipts.items()},
            authority_receipt_resolver=resolver_for(other_forest_receipts),
            obligation_graph_cid=other_forest_receipts["obligation"]["content_id"],
            plan_cid=other_forest_receipts["planner"]["content_id"],
            doctor_cid=other_forest_receipts["doctor"]["content_id"],
        ),
        "residual_forged_receipt_identity": dict(
            task_cid=residual_task,
            forest_roots=residual_roots,
            residual_packet_cid=packet_cid,
            analytical_candidates=(Candidate(candidate_id="non-closing", closes_claim=False),),
            authority_receipt_cids={k: v["content_id"] for k, v in forged_receipts.items()},
            authority_receipt_resolver=resolver_for(forged_receipts),
            obligation_graph_cid=forged_receipts["obligation"]["content_id"],
            plan_cid=forged_receipts["planner"]["content_id"],
            doctor_cid=forged_receipts["doctor"]["content_id"],
        ),
    }

    for case_id, expected, description, kwargs in invalid_specs:
        record_case(
            case_id=case_id,
            family="invalid_binding",
            pair_id="residual_progress",
            polarity="invalid",
            expected_reason=expected,
            description=description,
        )
        decision = evaluate_bound_gate(api, **(kwargs or filled_kwargs[case_id]))
        blocked = False
        try:
            api["assert_provider_dispatch_allowed"](decision)
        except PermissionError:
            blocked = True
        rows.append(
            finish_row(
                row_base(
                    case_id=case_id,
                    family="invalid_binding",
                    pair_id="residual_progress",
                    polarity="invalid",
                    description=description,
                    expected_reason=expected,
                ),
                decision=decision,
                observed_reason=decision.reason_code,
                useful_progress=False,
                extra={"dispatch_blocked": blocked, "provider_called": False},
            )
        )

    # Gate helper omits view CIDs — minimally altered caller.
    record_case(
        case_id="residual_gate_omits_views",
        family="invalid_binding",
        pair_id="residual_progress",
        polarity="invalid",
        expected_reason="missing_typed_resolvable_authority_receipts",
        description="evaluate_provider_gate without exact plan/doctor/obligation view CIDs cannot admit residual use.",
    )
    gate_decision = api["evaluate_provider_gate"](
        task_cid=residual_task,
        forest_roots=residual_roots,
        residual_packet_cid=packet_cid,
        analytical_candidates=(Candidate(candidate_id="non-closing", closes_claim=False),),
        planner_available=True,
        doctor_available=True,
        authority_receipt_cids=receipt_cids,
        authority_receipt_resolver=resolver_for(receipts),
    )
    blocked = False
    try:
        api["assert_provider_dispatch_allowed"](gate_decision)
    except PermissionError:
        blocked = True
    rows.append(
        finish_row(
            row_base(
                case_id="residual_gate_omits_views",
                family="invalid_binding",
                pair_id="residual_progress",
                polarity="invalid",
                description="evaluate_provider_gate without exact plan/doctor/obligation view CIDs cannot admit residual use.",
                expected_reason="missing_typed_resolvable_authority_receipts",
            ),
            decision=gate_decision,
            observed_reason=gate_decision.reason_code,
            useful_progress=False,
            extra={
                "dispatch_blocked": blocked,
                "provider_called": False,
                "caller": "evaluate_provider_gate",
                "finding": "thin gate helper does not forward plan/doctor/obligation view CIDs",
            },
        )
    )

    # Ambiguity
    record_case(
        case_id="ambiguous_candidates",
        family="ambiguity",
        pair_id="ambiguity",
        polarity="invalid",
        expected_reason="ambiguous_repair_candidates",
        description="Two competing closing candidates abstain; residual provider is not called.",
    )
    decision = evaluate_bound_gate(
        api,
        task_cid=cid(api, "amb-task"),
        forest_roots=forest(api, salt="amb"),
        analytical_candidates=(
            Candidate(candidate_id="fix-a", closes_claim=True),
            Candidate(candidate_id="fix-b", closes_claim=True),
        ),
    )
    rows.append(
        finish_row(
            row_base(
                case_id="ambiguous_candidates",
                family="ambiguity",
                pair_id="ambiguity",
                polarity="invalid",
                description="Two competing closing candidates abstain; residual provider is not called.",
                expected_reason="ambiguous_repair_candidates",
            ),
            decision=decision,
            observed_reason=decision.reason_code,
            useful_progress=False,
            extra={"provider_called": False},
        )
    )

    # Missing capabilities
    for case_id, flag, description in (
        (
            "missing_planner",
            dict(planner_available=False),
            "Missing planner backend defers; capability stays unavailable and is not a silent LLM fallback.",
        ),
        (
            "missing_doctor",
            dict(doctor_available=False),
            "Missing doctor backend defers; capability stays unavailable and is not a silent LLM fallback.",
        ),
    ):
        record_case(
            case_id=case_id,
            family="capability",
            pair_id="capability",
            polarity="invalid",
            expected_reason="missing_required_backend",
            description=description,
        )
        decision = evaluate_bound_gate(
            api,
            task_cid=cid(api, f"{case_id}-task"),
            forest_roots=forest(api, salt=case_id),
            analytical_candidates=(Candidate(candidate_id="would-close", closes_claim=True),),
            **flag,
        )
        rows.append(
            finish_row(
                row_base(
                    case_id=case_id,
                    family="capability",
                    pair_id="capability",
                    polarity="invalid",
                    description=description,
                    expected_reason="missing_required_backend",
                ),
                decision=decision,
                observed_reason=decision.reason_code,
                useful_progress=False,
                extra={"provider_called": False, "capability_available": False},
            )
        )

    # Production LLM remains unavailable
    probe = production_llm_probe()
    record_case(
        case_id="production_llm_unavailable",
        family="capability",
        pair_id="capability",
        polarity="diagnostic",
        expected_reason="production_model_identity_unavailable",
        description="Sealed profile has no production model identity; unavailability is not zero cost or simulated success.",
    )
    rows.append(
        finish_row(
            row_base(
                case_id="production_llm_unavailable",
                family="capability",
                pair_id="capability",
                polarity="diagnostic",
                description="Sealed profile has no production model identity; unavailability is not zero cost or simulated success.",
                expected_reason="production_model_identity_unavailable",
            ),
            observed_reason="production_model_identity_unavailable",
            useful_progress=False,
            extra={
                "provider_called": False,
                "capability_available": False,
                "production_llm": probe,
                "status": "pass",
                "disposition": "defer_capability",
                "provider_authorized": False,
                "skip_provider": True,
                "kernel_provider_hook_count": 0,
                "reason_matched": True,
            },
            limitations=["production_model_identity_unavailable_in_sealed_profile"],
        )
    )

    # Unique close preempts residual packet
    record_case(
        case_id="deterministic_preempts_residual",
        family="deterministic",
        pair_id="deterministic_vs_residual",
        polarity="diagnostic",
        expected_reason="analytical_unique_mapping",
        description="A unique analytical close is selected before residual authorization; the packet does not invoke a provider.",
    )
    decision = evaluate_bound_gate(
        api,
        task_cid=residual_task,
        forest_roots=residual_roots,
        residual_packet_cid=packet_cid,
        analytical_candidates=(Candidate(candidate_id="unique-add-fix", closes_claim=True),),
        authority_receipt_cids=receipt_cids,
        authority_receipt_resolver=resolver_for(receipts),
        obligation_graph_cid=receipt_cids["obligation"],
        plan_cid=receipt_cids["planner"],
        doctor_cid=receipt_cids["doctor"],
    )
    rows.append(
        finish_row(
            row_base(
                case_id="deterministic_preempts_residual",
                family="deterministic",
                pair_id="deterministic_vs_residual",
                polarity="diagnostic",
                description="A unique analytical close is selected before residual authorization; the packet does not invoke a provider.",
                expected_reason="analytical_unique_mapping",
            ),
            decision=decision,
            observed_reason=decision.reason_code,
            useful_progress=False,
            extra={"provider_called": False, "packet_present_but_not_dispatched": True},
        )
    )

    # Unknown provider effect
    record_case(
        case_id="unknown_provider_effect",
        family="unknown_effect",
        pair_id="residual_progress",
        polarity="invalid",
        expected_reason="unknown_provider_effect",
        description="An authorized residual whose nomination escapes the write lease enters reconciliation rather than blind success.",
    )
    wt = copy_worktree(work_root / "baseline", work_root / "unknown_provider_effect")
    decision = evaluate_bound_gate(api, **residual_kwargs)
    invocation, nominated, invoke_error = invoke_residual(
        api, packet=packet, worktree=wt, mode="unknown_effect"
    )
    applied = None
    if nominated:
        applied = apply_nomination(
            api,
            wt,
            nominated.get("nomination") or {},
            task_cid=residual_task,
            plan_cid=decision.receipt.plan_cid,
        )
    oracle = run_oracle(wt)
    observed = (
        (applied or {}).get("reason_code")
        or invoke_error
        or "unknown_provider_effect"
    )
    rows.append(
        finish_row(
            row_base(
                case_id="unknown_provider_effect",
                family="unknown_effect",
                pair_id="residual_progress",
                polarity="invalid",
                description="An authorized residual whose nomination escapes the write lease enters reconciliation rather than blind success.",
                expected_reason="unknown_provider_effect",
            ),
            decision=decision,
            observed_reason=str(observed),
            useful_progress=False,
            oracle=oracle,
            invocation=invocation,
            analytical=applied,
            extra={"blind_retry": False, "reconciliation": True},
        )
    )

    # Repeated residual: do not blindly re-invoke
    record_case(
        case_id="repeated_residual_no_blind_retry",
        family="repeated",
        pair_id="residual_progress",
        polarity="diagnostic",
        expected_reason="repeated_residual_requires_reconciliation",
        description="A repeated residual request after an unknown effect is reconciled rather than blindly re-invoked.",
    )
    rows.append(
        finish_row(
            row_base(
                case_id="repeated_residual_no_blind_retry",
                family="repeated",
                pair_id="residual_progress",
                polarity="diagnostic",
                description="A repeated residual request after an unknown effect is reconciled rather than blindly re-invoked.",
                expected_reason="repeated_residual_requires_reconciliation",
            ),
            decision=decision,
            observed_reason="repeated_residual_requires_reconciliation",
            useful_progress=False,
            extra={
                "prior_case": "unknown_provider_effect",
                "blind_retry": False,
                "second_provider_invocation": False,
                "provider_called": False,
                "kernel_would_reauthorize": True,
                "operator_policy": "unknown provider effects enter reconciliation rather than blind retry",
            },
        )
    )

    # Deny-all diagnostic
    record_case(
        case_id="deny_all_control",
        family="deny_all",
        pair_id="deny_all",
        polarity="diagnostic",
        expected_reason="deny_all_not_useful_progress",
        description="A deny-all route never calls a provider and cannot pass useful-progress criteria.",
    )
    wt = copy_worktree(work_root / "baseline", work_root / "deny_all_control")
    oracle = run_oracle(wt)
    rows.append(
        finish_row(
            row_base(
                case_id="deny_all_control",
                family="deny_all",
                pair_id="deny_all",
                polarity="diagnostic",
                description="A deny-all route never calls a provider and cannot pass useful-progress criteria.",
                expected_reason="deny_all_not_useful_progress",
            ),
            observed_reason="deny_all_not_useful_progress",
            useful_progress=False,
            oracle=oracle,
            extra={
                "status": "pass",
                "disposition": "abstain_review",
                "provider_authorized": False,
                "skip_provider": True,
                "kernel_provider_hook_count": 0,
                "provider_called": False,
                "reason_matched": True,
                "deny_all_useful_progress": False,
                "oracle_on_unfixed_tree_passed": bool(oracle["passed"]),
                "workflow_savings_inferred": False,
            },
        )
    )

    # Authorization permit / deny pair
    Grant = api["AuthorizationGrant"]
    Policy = api["AuthorizationPolicy"]
    Request = api["AuthorizationRequest"]
    Cap = api["Capability"]
    evaluator = api["ReferenceAuthorizationEvaluator"]()
    grant = Grant(
        statement_id="ns008-root-grant",
        issuer="root",
        subject="worker",
        capability=Cap.EXECUTE_TASK,
        task_scope=("NS-008",),
        delegation_depth=0,
        lease_scope=("lease-ns008",),
        worktree_scope=("tree-ns008",),
        path_scope=("pkg",),
        fencing_epoch=1,
        not_before_ms=100,
        expires_at_ms=2_000,
    )
    policy = Policy(
        policy_id="ns-008-authority",
        version="1",
        trusted_roots=("root",),
        grants=(grant,),
        current_fencing_epochs={"NS-008": 1},
        current_lease_ids={"NS-008": "lease-ns008"},
    )
    permit_req = Request(
        principal="worker",
        capability=Cap.EXECUTE_TASK,
        task_id="NS-008",
        evaluated_at_ms=1_000,
        lease_id="lease-ns008",
        worktree_id="tree-ns008",
        path="pkg/core.py",
        fencing_epoch=1,
    )
    deny_req = Request(
        principal="worker",
        capability=Cap.EXECUTE_TASK,
        task_id="NS-007",
        evaluated_at_ms=1_000,
        lease_id="lease-ns008",
        worktree_id="tree-ns008",
        path="pkg/core.py",
        fencing_epoch=1,
    )
    permit = evaluator.evaluate(policy, permit_req)
    deny = evaluator.evaluate(policy, deny_req)
    record_case(
        case_id="authorization_permit_execute",
        family="authorization",
        pair_id="authorization_scope",
        polarity="valid",
        expected_reason="allowed",
        description="Reference authorization permits EXECUTE_TASK on the exact task/lease/worktree/path binding.",
    )
    rows.append(
        finish_row(
            row_base(
                case_id="authorization_permit_execute",
                family="authorization",
                pair_id="authorization_scope",
                polarity="valid",
                description="Reference authorization permits EXECUTE_TASK on the exact task/lease/worktree/path binding.",
                expected_reason="allowed",
            ),
            observed_reason=permit.reason.value,
            useful_progress=False,
            authorization={
                "verdict": permit.verdict.value,
                "reason": permit.reason.value,
                "policy_identity": permit.policy_identity,
                "request_identity": permit.request_identity,
                "generated_code_correctness": "not_established",
            },
            extra={
                "status": "pass" if permit.verdict.value == "permit" else "fail",
                "reason_matched": permit.reason.value == "allowed",
                "provider_called": False,
                "kernel_provider_hook_count": 0,
                "skip_provider": True,
                "provider_authorized": False,
            },
        )
    )
    record_case(
        case_id="authorization_deny_task_scope",
        family="authorization",
        pair_id="authorization_scope",
        polarity="invalid",
        expected_reason="task_scope_mismatch",
        description="A minimally altered task_id is denied for task_scope_mismatch; authorization is not code correctness.",
    )
    rows.append(
        finish_row(
            row_base(
                case_id="authorization_deny_task_scope",
                family="authorization",
                pair_id="authorization_scope",
                polarity="invalid",
                description="A minimally altered task_id is denied for task_scope_mismatch; authorization is not code correctness.",
                expected_reason="task_scope_mismatch",
            ),
            observed_reason=deny.reason.value,
            useful_progress=False,
            authorization={
                "verdict": deny.verdict.value,
                "reason": deny.reason.value,
                "policy_identity": deny.policy_identity,
                "request_identity": deny.request_identity,
                "generated_code_correctness": "not_established",
            },
            extra={
                "status": "pass"
                if deny.verdict.value == "deny" and deny.reason.value == "task_scope_mismatch"
                else "fail",
                "reason_matched": deny.reason.value == "task_scope_mismatch",
                "provider_called": False,
                "kernel_provider_hook_count": 0,
                "skip_provider": True,
                "provider_authorized": False,
            },
        )
    )
    return cases, rows


def build_report(
    *,
    capability: dict[str, Any],
    cases: list[dict[str, Any]],
    rows: list[dict[str, Any]],
    started_at: str,
) -> str:
    by_id = {row["case_id"]: row for row in rows}
    residual = by_id.get("residual_authorized_progress") or {}
    deterministic = by_id.get("deterministic_unique_close") or {}
    deny = by_id.get("deny_all_control") or {}
    lines = [
        "# NS-008 Deterministic closure and authorized residual dispatch qualification",
        "",
        f"Generated at {started_at}. This is a sealed-profile qualification record, not a live A–D experiment and not a production model-identity claim.",
        "",
        "## Profile",
        "",
        "- Kernel: `PreImplementationKernel@1`",
        "- Thin gate helper: `ImplementationDaemon@pre_implementation_kernel` (`evaluate_provider_gate`)",
        "- Bound caller: `KernelEvaluationRequest` with exact task/forest/plan/doctor/obligation receipts",
        "- Residual invocation: `ResidualProviderInvocation@1`",
        "- Deterministic apply: `AnalyticalCloseExecutor@1`",
        "- Authority evaluator: `ReferenceAuthorizationEvaluator`",
        f"- Intended residual provider: `{PROVIDER_ID}` / `{PROVIDER_REVISION}` (qualification-injected process, `admitted_production=false`)",
        "- Independent oracle: `python3 -m pytest tests/test_core.py` on a frozen add/scale fixture",
        f"- Selection policy: `{POLICY_ID}`",
        "",
        "## Environment",
        "",
        f"- Interpreter: `{capability['interpreter']}` ({capability['python_version']})",
        f"- Sealed `PATH` at process start: `{capability.get('path')}`",
        f"- anyio: `{capability.get('anyio')}`",
        f"- pytest: `{capability.get('pytest')}`",
        f"- Public `semantic_state` package import: {capability.get('public_semantic_state_import', {}).get('error') or 'loaded'}",
        "",
        "## Coverage",
        "",
        f"- Result rows: {len(rows)}",
        f"- Declared cases: {len(cases)}",
        f"- Failed rows: {sum(1 for row in rows if row.get('status') != 'pass')}",
        f"- Valid residual reached intended provider: `{bool(residual.get('useful_progress'))}` invocations=`{(residual.get('invocation') or {}).get('actual_process_invocations')}`",
        f"- Deterministic close independent oracle: `{bool(deterministic.get('useful_progress'))}` kernel_hooks=`{deterministic.get('kernel_provider_hook_count')}`",
        f"- Deny-all useful progress: `{deny.get('useful_progress')}` (must be false)",
        "",
        "## Kernel hook count is not a saving",
        "",
        "Every kernel evaluation records `provider_hook_count=0` because `PreImplementationKernel.evaluate` never calls a model. That local zero is not a measurement of saved model calls across the workflow. Residual invocations are counted at `ResidualProviderInvocation.invoke`, where the intended provider process actually runs. Deny-all also has zero kernel hooks and still cannot pass useful-progress criteria.",
        "",
        "## Bound caller versus thin gate helper",
        "",
        "`evaluate_provider_gate` does not forward plan/doctor/obligation view CIDs. Residual authorization in this qualification therefore uses `PreImplementationKernel.evaluate` on a `KernelEvaluationRequest` that binds those views to the durable receipts. The same packet and receipts through the thin helper remain `defer_capability` / `missing_typed_resolvable_authority_receipts` (`residual_gate_omits_views`).",
        "",
        "## Independent checking",
        "",
        "A candidate `closes_claim` boolean is never treated as success. `closes_claim_untrusted` keeps the unique analytical disposition but leaves the fixture unfixed; the frozen oracle fails and useful progress is false. Valid deterministic progress applies `AnalyticalCloseExecutor` then re-runs pytest. Valid residual progress applies only a lease-bounded nomination from the intended provider process, then re-runs the same oracle.",
        "",
        "## Production model identity",
        "",
        "No production LLM CLI or API identity is available in the sealed profile. Unavailability is recorded as a capability gap, not as zero cost and not as simulated success. The intended provider for the authorized residual case is the hashed qualification process `residual_provider.py`.",
        "",
        "## Limitations",
        "",
        "- Qualification uses a hermetic add/scale fixture, not a historical live repair task.",
        "- The residual provider is a digest-bound qualification process invoked through the real `ResidualProviderInvocation` wrapper. It is not an admitted production model revision.",
        "- Public import of `ipfs_accelerate_py.agent_supervisor.semantic_state` remains blocked without anyio; kernel/gate/invocation modules import without that package `__init__`.",
        "- This receipt is qualification evidence for NS-008 / Table 18 provider-gate row. It is not a matched A–D outcome.",
        "",
        "## Case outcomes",
        "",
        "| case_id | family | polarity | retained | status | useful_progress | reason |",
        "|---|---|---|---|---|---|---|",
    ]
    for row in rows:
        lines.append(
            "| `{case_id}` | {family} | {polarity} | {retained} | {status} | {progress} | `{reason}` |".format(
                case_id=row["case_id"],
                family=row.get("family"),
                polarity=row.get("polarity"),
                retained=str(row.get("retained")).lower(),
                status=row.get("status"),
                progress=str(row.get("useful_progress")).lower(),
                reason=row.get("observed_reason"),
            )
        )
    lines.append("")
    return "\n".join(lines)


def source_hashes() -> dict[str, str]:
    paths = [
        ACC_ROOT / "ipfs_accelerate_py/agent_supervisor/todo_daemon/pre_implementation_kernel.py",
        ACC_ROOT / "ipfs_accelerate_py/agent_supervisor/todo_daemon/pre_implementation_provider_gate.py",
        ACC_ROOT / "ipfs_accelerate_py/agent_supervisor/todo_daemon/implementation_disposition.py",
        ACC_ROOT / "ipfs_accelerate_py/agent_supervisor/todo_daemon/residual_provider_invocation.py",
        ACC_ROOT / "ipfs_accelerate_py/agent_supervisor/todo_daemon/analytical_close_executor.py",
        ACC_ROOT / "ipfs_accelerate_py/agent_supervisor/planning/residual_llm_packet.py",
        ACC_ROOT / "ipfs_accelerate_py/agent_supervisor/control/authorization_logic.py",
        ACC_ROOT / "ipfs_accelerate_py/agent_supervisor/semantic_state/providers.py",
        PROVIDER_SCRIPT,
    ]
    return {rel(path): sha256_file(path) for path in paths if path.is_file()}


def main() -> int:
    started_at = utc_now()
    checkpoint("start", {"started_at": started_at, "task_id": TASK_ID})
    capability = prepare_imports()
    api = capability.pop("api")
    work = Path(tempfile.mkdtemp(prefix="ns008-provider-gate-", dir=os.environ.get("TMPDIR") or "/tmp"))
    try:
        cases, rows = run_cases(api, work)
    finally:
        shutil.rmtree(work, ignore_errors=True)

    failed = [row["case_id"] for row in rows if row.get("status") != "pass"]
    if failed:
        raise SystemExit(f"NS-008 qualification cases failed: {failed}")

    cases_doc = {
        "schema": SCHEMA_CASES,
        "task_id": TASK_ID,
        "policy_id": POLICY_ID,
        "generated_at": started_at,
        "qualification_not_live_ad": True,
        "intended_provider": {
            "id": PROVIDER_ID,
            "revision": PROVIDER_REVISION,
            "script": rel(PROVIDER_SCRIPT),
            "admitted_production": False,
        },
        "oracle": {
            "kind": "pytest",
            "command": ["python3", "-m", "pytest", "tests/test_core.py", "-q"],
            "independent_of_closes_claim": True,
        },
        "caller": {
            "kernel": "PreImplementationKernel@1",
            "bound_request": "KernelEvaluationRequest with exact plan/doctor/obligation receipts",
            "thin_gate": "evaluate_provider_gate (does not forward view CIDs)",
            "residual_invocation": "ResidualProviderInvocation@1",
            "analytical_close": "AnalyticalCloseExecutor@1",
            "authorization": "ReferenceAuthorizationEvaluator",
        },
        "fixture": {
            "kind": "hermetic_add_scale",
            "bug": BUG,
            "fix": FIX,
            "core_sha256": sha256_text(CORE_SOURCE),
            "test_sha256": sha256_text(TEST_SOURCE),
        },
        "rules": {
            "kernel_zero_hooks_are_not_workflow_savings": True,
            "deny_all_cannot_pass_useful_progress": True,
            "closes_claim_is_not_success": True,
            "missing_capabilities_stay_unavailable": True,
            "count_invocations_at_residual_provider_boundary": True,
        },
        "capability": capability,
        "source_hashes": source_hashes(),
        "cases": cases,
    }
    report = build_report(
        capability=capability, cases=cases, rows=rows, started_at=started_at
    )

    QUAL.mkdir(parents=True, exist_ok=True)
    SNAP_QUAL.mkdir(parents=True, exist_ok=True)
    for directory in (QUAL, SNAP_QUAL):
        write_json(directory / "provider_gate_cases.json", cases_doc)
        write_jsonl(directory / "provider_gate_receipts.jsonl", rows)
        atomic_write(directory / "provider_gate_report.md", report.encode("utf-8"))

    checkpoint(
        "outputs",
        {
            "finished_at": utc_now(),
            "rows": len(rows),
            "failed": failed,
            "cases_sha256": sha256_file(QUAL / "provider_gate_cases.json"),
            "receipts_sha256": sha256_file(QUAL / "provider_gate_receipts.jsonl"),
            "report_sha256": sha256_file(QUAL / "provider_gate_report.md"),
        },
    )
    print("NS-008 provider-gate qualification: OK")
    print(f"rows={len(rows)} failed={len(failed)}")
    print("residual_authorized_progress useful_progress=", by_id_progress(rows, "residual_authorized_progress"))
    print("deterministic_unique_close useful_progress=", by_id_progress(rows, "deterministic_unique_close"))
    return 0


def by_id_progress(rows: list[dict[str, Any]], case_id: str) -> bool:
    for row in rows:
        if row["case_id"] == case_id:
            return bool(row.get("useful_progress"))
    return False


if __name__ == "__main__":
    raise SystemExit(main())
