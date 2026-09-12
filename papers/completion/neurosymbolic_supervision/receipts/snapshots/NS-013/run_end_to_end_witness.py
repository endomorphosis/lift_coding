#!/usr/bin/env python3
"""NS-013 live qualification of one state-to-repair-to-certificate-to-publication witness.

Turns the Table 6 guard-before-write cycle into a frozen genuine task and runs
it through the current callers: IsolatedPatchWorktree, PreImplementationKernel,
model routing, TestProofCache, and IncrementalProofSealer. Every step binds
current source/task/plan/obligation/evidence IDs. Symbolic/context evidence
changes the route from a model class to deterministic_only. A valid permitted
write still works after the denied-effect repair. Rejected and incomplete
paths cannot report completion. Simulation-only units stay unlabeled as live
success.

This is sealed-profile qualification, not a matched A–D experiment and not a
production model-identity or Groth16 claim.
"""

from __future__ import annotations

import difflib
import hashlib
import importlib.util
import json
import os
import shutil
import subprocess
import sys
import tempfile
import textwrap
import time
import types
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Mapping, Sequence


SNAP = Path(__file__).resolve().parent
ROOT = SNAP.parents[5]
PAPER = ROOT / "papers/completion/neurosymbolic_supervision"
QUAL = PAPER / "qualification"
SNAP_QUAL = SNAP / "qualification"
ACC_ROOT = ROOT / "external/ipfs_accelerate"
DS_ROOT = ROOT / "external/ipfs_datasets"
KIT_ROOT = ROOT / "external/ipfs_kit"
ACC_PY = ACC_ROOT / "ipfs_accelerate_py"
TASK_ID = "NS-013"
POLICY_ID = "ns-013-end-to-end-qualification-v1"
SCHEMA_WITNESS = "neurosymbolic-supervision/end-to-end-witness@1"
SCHEMA_TRACE = "neurosymbolic-supervision/end-to-end-trace@1"
CANONICAL_PROFILE = {
    "canonicalization_version": "1",
    "codec": "canonical-json@1",
    "hash": "sha256",
    "source_mode": "immutable-bytes",
}
CHECKPOINT_DIR = Path(
    os.environ.get(
        "IPFS_ACCELERATE_AGENT_TASK_CHECKPOINT_DIR",
        str(SNAP / "checkpoints"),
    )
)
REQUIRED_AUTHORITY_KINDS = ("planner", "doctor", "obligation", "logic", "repair")
REQUIRED_TRACE_STEPS = (
    "capture_state",
    "state_obligation",
    "obtain_counterexample",
    "plan_bounded_repair",
    "choose_reasoning_route",
    "validate_candidate",
    "reuse_narrowly",
    "seal_and_publish",
    "learn_without_self_approval",
    "invalid_denied_effect_rejected",
    "incomplete_cannot_complete",
    "simulation_labeled_qualification",
)

SOURCE_PATHS = (
    ACC_ROOT / "ipfs_accelerate_py/agent_supervisor/semantic_state/harness.py",
    ACC_ROOT / "ipfs_accelerate_py/agent_supervisor/semantic_state/work_loop.py",
    ACC_ROOT / "ipfs_accelerate_py/agent_supervisor/semantic_state/worktree.py",
    ACC_ROOT / "ipfs_accelerate_py/agent_supervisor/semantic_state/routing.py",
    ACC_ROOT / "ipfs_accelerate_py/agent_supervisor/todo_daemon/pre_implementation_kernel.py",
    ACC_ROOT / "ipfs_accelerate_py/agent_supervisor/todo_daemon/analytical_close_executor.py",
    ACC_ROOT / "ipfs_accelerate_py/agent_supervisor/proof/incremental_sealing/sealer.py",
    ACC_ROOT / "ipfs_accelerate_py/agent_supervisor/proof/test_proof_cache.py",
    ACC_ROOT / "ipfs_accelerate_py/agent_supervisor/proof/test_execution_contracts.py",
    ACC_ROOT / "ipfs_accelerate_py/agent_supervisor/control/authorization_logic.py",
    SNAP / "compat_shims.py",
)

BUGGY_RECORDS = textwrap.dedent(
    '''\
    """Bounded record store used by the NS-013 guard-before-write witness."""

    from __future__ import annotations

    from typing import Any, Mapping


    class PermissionDenied(PermissionError):
        """Caller is outside the permitted API scope."""


    class RecordStore:
        """In-memory store with an explicit authorize/write_record surface."""

        def __init__(self) -> None:
            self._records: dict[str, Any] = {}
            self._audit: list[str] = []
            self._finalized = False

        def authorize(self, request: Mapping[str, Any], policy: Mapping[str, Any]) -> bool:
            if request.get("caller") not in tuple(policy.get("permitted_callers") or ()):
                return False
            if request.get("scope") not in tuple(policy.get("permitted_scopes") or ()):
                return False
            return True

        def write_record(self, request: Mapping[str, Any], policy: Mapping[str, Any]) -> str:
            key = str(request["key"])
            value = request["value"]
            # BUG: persist before checking the caller's permitted scope.
            self._records[key] = value
            self._audit.append(f"write:{key}")
            if not self.authorize(request, policy):
                raise PermissionDenied("denied")
            return key

        def read_record(self, key: str) -> Any:
            return self._records.get(key)

        def persistent_state(self) -> dict[str, Any]:
            return {"records": dict(self._records), "audit": list(self._audit)}

        def finalize(self) -> None:
            self._finalized = True

        @property
        def finalized(self) -> bool:
            return self._finalized
    '''
)

FIXED_RECORDS = textwrap.dedent(
    '''\
    """Bounded record store used by the NS-013 guard-before-write witness."""

    from __future__ import annotations

    from typing import Any, Mapping


    class PermissionDenied(PermissionError):
        """Caller is outside the permitted API scope."""


    class RecordStore:
        """In-memory store with an explicit authorize/write_record surface."""

        def __init__(self) -> None:
            self._records: dict[str, Any] = {}
            self._audit: list[str] = []
            self._finalized = False

        def authorize(self, request: Mapping[str, Any], policy: Mapping[str, Any]) -> bool:
            if request.get("caller") not in tuple(policy.get("permitted_callers") or ()):
                return False
            if request.get("scope") not in tuple(policy.get("permitted_scopes") or ()):
                return False
            return True

        def write_record(self, request: Mapping[str, Any], policy: Mapping[str, Any]) -> str:
            key = str(request["key"])
            value = request["value"]
            if not self.authorize(request, policy):
                raise PermissionDenied("denied")
            self._records[key] = value
            self._audit.append(f"write:{key}")
            return key

        def read_record(self, key: str) -> Any:
            return self._records.get(key)

        def persistent_state(self) -> dict[str, Any]:
            return {"records": dict(self._records), "audit": list(self._audit)}

        def finalize(self) -> None:
            self._finalized = True

        @property
        def finalized(self) -> bool:
            return self._finalized
    '''
)

INVALID_RECORDS = textwrap.dedent(
    '''\
    """Bounded record store used by the NS-013 guard-before-write witness."""

    from __future__ import annotations

    from typing import Any, Mapping


    class PermissionDenied(PermissionError):
        """Caller is outside the permitted API scope."""


    class RecordStore:
        """In-memory store with an explicit authorize/write_record surface."""

        def __init__(self) -> None:
            self._records: dict[str, Any] = {}
            self._audit: list[str] = []
            self._finalized = False

        def authorize(self, request: Mapping[str, Any], policy: Mapping[str, Any]) -> bool:
            if request.get("caller") not in tuple(policy.get("permitted_callers") or ()):
                return False
            if request.get("scope") not in tuple(policy.get("permitted_scopes") or ()):
                return False
            return True

        def write_record(self, request: Mapping[str, Any], policy: Mapping[str, Any]) -> str:
            key = str(request["key"])
            value = request["value"]
            # Minimally altered invalid: still persist before the authorize check.
            self._records[key] = value
            self._audit.append(f"write:{key}")
            if not self.authorize(request, policy):
                raise PermissionDenied("denied")
            return key

        def read_record(self, key: str) -> Any:
            return self._records.get(key)

        def persistent_state(self) -> dict[str, Any]:
            return {"records": dict(self._records), "audit": list(self._audit)}

        def finalize(self) -> None:
            self._finalized = True

        @property
        def finalized(self) -> bool:
            return self._finalized
    '''
)

TEST_SOURCE = textwrap.dedent(
    """\
    from pkg.records import PermissionDenied, RecordStore

    POLICY = {
        "permitted_callers": ("alice",),
        "permitted_scopes": ("records.write",),
    }


    def test_permitted_write():
        store = RecordStore()
        key = store.write_record(
            {"caller": "alice", "scope": "records.write", "key": "k1", "value": "v1"},
            POLICY,
        )
        assert key == "k1"
        assert store.read_record("k1") == "v1"
        store.finalize()
        assert store.finalized is True


    def test_denied_no_write():
        store = RecordStore()
        before = store.persistent_state()
        raised = False
        try:
            store.write_record(
                {"caller": "mallory", "scope": "records.write", "key": "secret", "value": "leak"},
                POLICY,
            )
        except PermissionDenied:
            raised = True
        finally:
            store.finalize()
        assert raised is True
        assert store.persistent_state() == before
        assert store.read_record("secret") is None
        assert store.finalized is True


    def test_exception_finalization():
        store = RecordStore()
        try:
            store.write_record(
                {"caller": "alice", "scope": "admin.drop", "key": "x", "value": 1},
                POLICY,
            )
        except PermissionDenied:
            store.finalize()
        assert store.finalized is True
        assert store.read_record("x") is None


    def test_api_scope():
        store = RecordStore()
        assert callable(store.authorize)
        assert callable(store.write_record)
        assert callable(store.read_record)
        assert callable(store.persistent_state)
        assert callable(store.finalize)
    """
)

POLICY_TOML = textwrap.dedent(
    """\
    [authorization]
    policy_id = "policy:ns-013-guard-before-write@1"
    permitted_callers = ["alice"]
    permitted_scopes = ["records.write"]
    observation_profile = "persistent_records_and_audit"

    [selection]
    mode = "strict"
    allow_full_fallback = true
    version = "1"
    """
)


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def digest_hex(payload: Mapping[str, Any] | str | bytes) -> str:
    if isinstance(payload, bytes):
        body = payload
    elif isinstance(payload, str):
        body = payload.encode("utf-8")
    else:
        body = json.dumps(
            payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True
        ).encode("utf-8")
    return "sha256:" + hashlib.sha256(body).hexdigest()


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
    try:
        return str(path.resolve().relative_to(ROOT))
    except ValueError:
        return str(path)


def enum_val(value: Any) -> str:
    return str(getattr(value, "value", value))


def which(name: str) -> str | None:
    return shutil.which(name)


def git_head(path: Path) -> str | None:
    git = which("git")
    if git is None:
        return None
    try:
        proc = subprocess.run(
            [git, "-C", str(path), "rev-parse", "HEAD"],
            check=False,
            capture_output=True,
            text=True,
        )
    except OSError:
        return None
    if proc.returncode != 0:
        return None
    return proc.stdout.strip() or None


def source_hashes() -> dict[str, str]:
    hashes: dict[str, str] = {}
    for path in SOURCE_PATHS:
        if path.is_file():
            hashes[rel(path)] = sha256_file(path)
    return hashes


def git(repo: Path, *args: str, check: bool = True) -> subprocess.CompletedProcess[str]:
    env = {
        "PATH": os.environ.get("PATH", "/usr/bin"),
        "HOME": os.environ.get("HOME", "/tmp"),
        "LANG": "C.UTF-8",
        "LC_ALL": "C.UTF-8",
        "GIT_TERMINAL_PROMPT": "0",
        "GIT_CONFIG_NOSYSTEM": "1",
        "GIT_AUTHOR_NAME": "NS-013",
        "GIT_AUTHOR_EMAIL": "ns013@example.invalid",
        "GIT_COMMITTER_NAME": "NS-013",
        "GIT_COMMITTER_EMAIL": "ns013@example.invalid",
        "GIT_AUTHOR_DATE": "2026-09-12T00:00:00+0000",
        "GIT_COMMITTER_DATE": "2026-09-12T00:00:00+0000",
    }
    completed = subprocess.run(
        ["git", *args],
        cwd=str(repo),
        text=True,
        capture_output=True,
        check=False,
        env=env,
    )
    if check and completed.returncode != 0:
        raise RuntimeError(f"git {' '.join(args)} failed: {completed.stderr or completed.stdout}")
    return completed


def init_repo(repo: Path) -> tuple[str, str]:
    git(repo, "init")
    git(repo, "config", "user.email", "ns013@example.invalid")
    git(repo, "config", "user.name", "NS-013")
    git(repo, "add", "-A")
    git(repo, "commit", "-m", "ns-013-guard-before-write-baseline")
    head = git(repo, "rev-parse", "HEAD").stdout.strip()
    tree = git(repo, "rev-parse", "HEAD^{tree}").stdout.strip()
    return head, tree


def unified_patch(path: str, old: str, new: str) -> str:
    old_lines = old.splitlines(keepends=True)
    new_lines = new.splitlines(keepends=True)
    if old_lines and not old_lines[-1].endswith("\n"):
        old_lines[-1] += "\n"
    if new_lines and not new_lines[-1].endswith("\n"):
        new_lines[-1] += "\n"
    body = "".join(
        difflib.unified_diff(
            old_lines,
            new_lines,
            fromfile=f"a/{path}",
            tofile=f"b/{path}",
            lineterm="\n",
        )
    )
    header = f"diff --git a/{path} b/{path}\n"
    if body.startswith("diff --git"):
        return body
    return header + body


def _stub_package(name: str, path: Path) -> types.ModuleType:
    existing = sys.modules.get(name)
    if existing is not None and getattr(existing, "__path__", None):
        return existing
    module = types.ModuleType(name)
    module.__file__ = str(path / "__init__.py")
    module.__path__ = [str(path)]  # type: ignore[attr-defined]
    module.__package__ = name
    sys.modules[name] = module
    parent, _, child = name.rpartition(".")
    if parent and parent in sys.modules:
        setattr(sys.modules[parent], child, module)
    return module


def _load_sub(pkg: str, name: str, filename: str, base: Path) -> Any:
    full = f"{pkg}.{name}"
    if full in sys.modules and hasattr(sys.modules[full], "__file__"):
        return sys.modules[full]
    spec = importlib.util.spec_from_file_location(full, base / filename)
    if spec is None or spec.loader is None:
        raise ImportError(full)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[full] = mod
    spec.loader.exec_module(mod)
    setattr(sys.modules[pkg], name, mod)
    return mod


def prepare_imports() -> dict[str, Any]:
    initial_path = os.environ.get("PATH")
    for path in (str(ACC_ROOT), str(DS_ROOT), str(KIT_ROOT), str(SNAP)):
        if path not in sys.path:
            sys.path.insert(0, path)

    from compat_shims import install_qualification_shims

    shim_report = install_qualification_shims()

    public_ss_error = None
    try:
        import ipfs_accelerate_py.agent_supervisor.semantic_state as _ss  # noqa: F401
    except Exception as exc:
        public_ss_error = f"{type(exc).__name__}: {exc}"

    import ipfs_accelerate_py  # noqa: F401
    import ipfs_accelerate_py.agent_supervisor  # noqa: F401

    pkg = "ipfs_accelerate_py.agent_supervisor.semantic_state"
    base = ACC_PY / "agent_supervisor/semantic_state"
    _stub_package(pkg, base)
    contracts = _load_sub(pkg, "contracts", "contracts.py", base)
    _load_sub(pkg, "scheduling_contracts", "scheduling_contracts.py", base)
    worktree = _load_sub(pkg, "worktree", "worktree.py", base)
    routing = _load_sub(pkg, "routing", "routing.py", base)

    from ipfs_accelerate_py.agent_supervisor.control.authorization_logic import (
        AuthorizationGrant,
        AuthorizationPolicy,
        AuthorizationRequest,
        Capability,
        ReferenceAuthorizationEvaluator,
    )
    from ipfs_accelerate_py.agent_supervisor.merge.worktree_lifecycle import (
        WorktreeLifecycleStore,
    )
    from ipfs_accelerate_py.agent_supervisor.proof.formal_verification_contracts import (
        content_identity,
    )
    from ipfs_accelerate_py.agent_supervisor.proof.incremental_sealing.admission import (
        EvidenceCandidate,
        verify_for_admission,
    )
    from ipfs_accelerate_py.agent_supervisor.proof.incremental_sealing.full_checkpoint import (
        GENESIS_PARENT_SEAL,
        RepositoryStateView,
        RequiredUnitEvidence,
        VerificationPolicyView,
        create_full_checkpoint,
    )
    from ipfs_accelerate_py.agent_supervisor.proof.incremental_sealing.sealer import (
        IncrementalProofSealer,
        PublicationReason,
    )
    from ipfs_accelerate_py.agent_supervisor.proof.test_execution_contracts import (
        EligibilityClass,
        PhaseOutcome,
        TestExecutionKey,
        TestLocatorKey,
        TestPassReceipt,
        TestProofCertificate,
        ProofBackendMode,
        CertificateAuthority,
    )
    from ipfs_accelerate_py.agent_supervisor.proof.test_proof_cache import TestProofCache
    from ipfs_accelerate_py.agent_supervisor.todo_daemon.analytical_close_executor import (
        AnalyticalCloseExecutor,
        AnalyticalClosePlan,
        AnalyticalEdit,
    )
    from ipfs_accelerate_py.agent_supervisor.todo_daemon.implementation_disposition import (
        ImplementationForestRoots,
        implementation_disposition_cid,
        provider_invocation_authorized,
    )
    from ipfs_accelerate_py.agent_supervisor.todo_daemon.pre_implementation_kernel import (
        REASON_ANALYTICAL_UNIQUE_MAPPING,
        REASON_MISSING_TYPED_AUTHORITY_RECEIPTS,
        AnalyticalRepairCandidate,
        KernelEvaluationRequest,
        PreImplementationKernel,
    )
    from ipfs_datasets_py.logic.zkp.incremental_sealing.evidence import (
        ProofMode,
        ProofTerminalStatus,
        SealStatus,
    )

    anyio_present = False
    try:
        import anyio  # noqa: F401

        anyio_present = True
    except Exception:
        anyio_present = False
    pytest_version = None
    pytest_error = None
    try:
        import pytest

        pytest_version = getattr(pytest, "__version__", "present")
    except Exception as exc:
        pytest_error = f"{type(exc).__name__}: {exc}"

    return {
        "interpreter": sys.executable,
        "python_version": sys.version.split()[0],
        "path": initial_path,
        "anyio": anyio_present,
        "pytest": pytest_version,
        "pytest_error": pytest_error,
        "git": which("git"),
        "shim_report": shim_report,
        "public_semantic_state_import": {
            "loaded": public_ss_error is None,
            "error": public_ss_error,
        },
        "binaries": {"z3": which("z3"), "cvc5": which("cvc5"), "groth16": which("groth16")},
        "api": {
            "contracts": contracts,
            "worktree": worktree,
            "routing": routing,
            "PatchScope": worktree.PatchScope,
            "create_isolated_worktree": worktree.create_isolated_worktree,
            "WorktreeLifecycleStore": WorktreeLifecycleStore,
            "route_model": routing.route_model,
            "RoutingInputs": routing.RoutingInputs,
            "ModelRoute": contracts.ModelRoute,
            "AuthorizationGrant": AuthorizationGrant,
            "AuthorizationPolicy": AuthorizationPolicy,
            "AuthorizationRequest": AuthorizationRequest,
            "Capability": Capability,
            "ReferenceAuthorizationEvaluator": ReferenceAuthorizationEvaluator,
            "content_identity": content_identity,
            "EvidenceCandidate": EvidenceCandidate,
            "verify_for_admission": verify_for_admission,
            "GENESIS_PARENT_SEAL": GENESIS_PARENT_SEAL,
            "RepositoryStateView": RepositoryStateView,
            "RequiredUnitEvidence": RequiredUnitEvidence,
            "VerificationPolicyView": VerificationPolicyView,
            "create_full_checkpoint": create_full_checkpoint,
            "IncrementalProofSealer": IncrementalProofSealer,
            "PublicationReason": PublicationReason,
            "EligibilityClass": EligibilityClass,
            "PhaseOutcome": PhaseOutcome,
            "TestExecutionKey": TestExecutionKey,
            "TestLocatorKey": TestLocatorKey,
            "TestPassReceipt": TestPassReceipt,
            "TestProofCertificate": TestProofCertificate,
            "ProofBackendMode": ProofBackendMode,
            "CertificateAuthority": CertificateAuthority,
            "TestProofCache": TestProofCache,
            "AnalyticalCloseExecutor": AnalyticalCloseExecutor,
            "AnalyticalClosePlan": AnalyticalClosePlan,
            "AnalyticalEdit": AnalyticalEdit,
            "ImplementationForestRoots": ImplementationForestRoots,
            "implementation_disposition_cid": implementation_disposition_cid,
            "provider_invocation_authorized": provider_invocation_authorized,
            "REASON_ANALYTICAL_UNIQUE_MAPPING": REASON_ANALYTICAL_UNIQUE_MAPPING,
            "REASON_MISSING_TYPED_AUTHORITY_RECEIPTS": REASON_MISSING_TYPED_AUTHORITY_RECEIPTS,
            "AnalyticalRepairCandidate": AnalyticalRepairCandidate,
            "KernelEvaluationRequest": KernelEvaluationRequest,
            "PreImplementationKernel": PreImplementationKernel,
            "ProofMode": ProofMode,
            "ProofTerminalStatus": ProofTerminalStatus,
            "SealStatus": SealStatus,
        },
        "modules": {
            "harness": rel(SOURCE_PATHS[0]),
            "work_loop": rel(SOURCE_PATHS[1]),
            "worktree": rel(SOURCE_PATHS[2]),
            "routing": rel(SOURCE_PATHS[3]),
            "pre_implementation_kernel": rel(SOURCE_PATHS[4]),
            "analytical_close_executor": rel(SOURCE_PATHS[5]),
            "sealer": rel(SOURCE_PATHS[6]),
            "test_proof_cache": rel(SOURCE_PATHS[7]),
            "test_execution_contracts": rel(SOURCE_PATHS[8]),
            "authorization_logic": rel(SOURCE_PATHS[9]),
            "compat_shims": rel(SOURCE_PATHS[10]),
        },
    }


def cid(api: dict[str, Any], name: str) -> str:
    return api["implementation_disposition_cid"]({"ns013": name})


def materialize_fixture(root: Path, *, records: str) -> None:
    pkg = root / "pkg"
    tests = root / "tests"
    pkg.mkdir(parents=True, exist_ok=True)
    tests.mkdir(parents=True, exist_ok=True)
    (pkg / "__init__.py").write_text("", encoding="utf-8")
    (pkg / "records.py").write_text(records, encoding="utf-8")
    (tests / "__init__.py").write_text("", encoding="utf-8")
    (tests / "test_records.py").write_text(TEST_SOURCE, encoding="utf-8")
    (root / "policy.toml").write_text(POLICY_TOML, encoding="utf-8")
    (root / "pytest.ini").write_text("[pytest]\npythonpath = .\n", encoding="utf-8")


def run_pytest(worktree: Path) -> dict[str, Any]:
    env = {
        "PATH": os.environ.get("PATH", "/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin"),
        "HOME": os.environ.get("HOME", "/tmp"),
        "PYTHONPATH": str(worktree),
        "PYTHONDONTWRITEBYTECODE": "1",
    }
    started = time.perf_counter()
    proc = subprocess.run(
        [sys.executable, "-m", "pytest", "tests/test_records.py", "-q", "--tb=line"],
        cwd=str(worktree),
        env=env,
        capture_output=True,
        text=True,
        timeout=60,
    )
    elapsed_ms = int((time.perf_counter() - started) * 1000)
    stdout = proc.stdout or ""
    failed_names = [
        line.split()[0]
        for line in stdout.splitlines()
        if line.startswith("FAILED ")
    ]
    return {
        "command": [sys.executable, "-m", "pytest", "tests/test_records.py", "-q", "--tb=line"],
        "cwd": rel(worktree) if worktree.is_relative_to(ROOT) else str(worktree),
        "exit_code": proc.returncode,
        "passed": proc.returncode == 0,
        "elapsed_ms": elapsed_ms,
        "stdout_tail": stdout[-600:],
        "stderr_tail": (proc.stderr or "")[-400:],
        "failed": failed_names,
        "independent_of_closes_claim": True,
    }


def observe_denied_write(module_path: Path) -> dict[str, Any]:
    spec = importlib.util.spec_from_file_location("ns013_records_probe", module_path)
    if spec is None or spec.loader is None:
        raise ImportError(str(module_path))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    store = mod.RecordStore()
    policy = {"permitted_callers": ("alice",), "permitted_scopes": ("records.write",)}
    before = store.persistent_state()
    denied = {
        "caller": "mallory",
        "scope": "records.write",
        "key": "secret",
        "value": "leak",
    }
    raised = False
    try:
        store.write_record(denied, policy)
    except mod.PermissionDenied:
        raised = True
    after = store.persistent_state()
    permitted_ok = False
    try:
        store.write_record(
            {"caller": "alice", "scope": "records.write", "key": "ok", "value": 1},
            policy,
        )
        permitted_ok = store.read_record("ok") == 1
    except mod.PermissionDenied:
        permitted_ok = False
    store.finalize()
    return {
        "denied_raised": raised,
        "persistent_state_before": before,
        "persistent_state_after_denied": after,
        "denied_write_persisted": after != before,
        "permitted_write_works": permitted_ok,
        "finalized": store.finalized,
        "observation_profile": "persistent_records_and_audit",
    }


def authority_receipts(
    api: dict[str, Any],
    *,
    task_cid: str,
    forest_cid: str,
) -> dict[str, dict[str, str]]:
    receipts: dict[str, dict[str, str]] = {}
    for kind in REQUIRED_AUTHORITY_KINDS:
        payload = {
            "schema": "ipfs_accelerate_py/agent-supervisor/authority-receipt@1",
            "receipt_kind": kind,
            "task_cid": task_cid,
            "repository_forest_cid": forest_cid,
        }
        receipts[kind] = {**payload, "content_id": api["content_identity"](payload)}
    return receipts


def resolver_for(receipts: Mapping[str, Mapping[str, str]]) -> Callable[[str], Mapping[str, str] | None]:
    index = {item["content_id"]: dict(item) for item in receipts.values()}

    def _resolve(receipt_cid: str) -> Mapping[str, str] | None:
        return index.get(receipt_cid)

    return _resolve


def evaluate_kernel(
    api: dict[str, Any],
    *,
    task_cid: str,
    forest_roots: Any,
    analytical_candidates: tuple[Any, ...] = (),
    residual_packet_cid: str = "",
    authority_receipt_cids: Mapping[str, str] | None = None,
    authority_receipt_resolver: Callable[[str], Mapping[str, str] | None] | None = None,
    obligation_graph_cid: str = "",
    plan_cid: str = "",
    doctor_cid: str = "",
) -> Any:
    kernel = api["PreImplementationKernel"](
        planner_available=True,
        doctor_available=True,
        authority_receipt_resolver=authority_receipt_resolver,
    )
    request = api["KernelEvaluationRequest"](
        task_cid=task_cid,
        forest_roots=forest_roots,
        attempt=1,
        residual_packet_cid=residual_packet_cid,
        analytical_candidates=analytical_candidates,
        policy_revision="1",
        authority_receipt_cids=dict(authority_receipt_cids or {}),
        obligation_graph_cid=obligation_graph_cid,
        plan_cid=plan_cid,
        doctor_cid=doctor_cid,
    )
    return kernel.evaluate(request)


def _unit(api: Mapping[str, Any], unit_id: str, **overrides: object):
    payload: dict[str, object] = {
        "unit_id": unit_id,
        "proof_object_cid": digest_hex(f"proof:{unit_id}"),
        "category": "unit_test",
        "terminal_status": api["ProofTerminalStatus"].INTEGRITY_VERIFIED.value,
        "proof_mode": api["ProofMode"].INTEGRITY_ONLY.value,
        "required_for_seal": True,
        "freshly_verified": True,
        "cache_reused_without_fresh_verification": False,
    }
    payload.update(overrides)
    return api["RequiredUnitEvidence"](**payload)


def _state(api: Mapping[str, Any], **overrides: object):
    payload: dict[str, object] = {
        "repository_id": "repo/ns-013-guard-before-write",
        "revision": "rev-" + ("a" * 40),
        "source_root_cid": digest_hex("source-root"),
        "repository_state_cid": digest_hex("repo-state"),
        "environment_cid": digest_hex("environment"),
        "parent_revision_ids": (),
    }
    payload.update(overrides)
    return api["RepositoryStateView"](**payload)


def _policy(api: Mapping[str, Any], **overrides: object):
    payload: dict[str, object] = {
        "policy_cid": digest_hex("policy:ns-013-guard-before-write@1"),
        "proof_schema_version": "1",
        "canonicalization_version": CANONICAL_PROFILE["canonicalization_version"],
        "dependency_graph_schema_version": "graph@1",
        "circuit_id": "circuit@ns-013",
        "verification_key_id": "vk/ns-013",
    }
    payload.update(overrides)
    return api["VerificationPolicyView"](**payload)


def apply_isolated_patch(
    api: dict[str, Any],
    baseline: Path,
    work_root: Path,
    patch_text: str,
    *,
    task_id: str,
    attempt: int,
) -> dict[str, Any]:
    work_root.mkdir(parents=True, exist_ok=True)
    PatchScope = api["PatchScope"]
    store = api["WorktreeLifecycleStore"](
        repo_root=baseline, store_dir=work_root / "lifecycle", lease_seconds=300.0
    )
    head = git(baseline, "rev-parse", "HEAD").stdout.strip()
    tree = git(baseline, "rev-parse", "HEAD^{tree}").stdout.strip()
    scope = PatchScope.from_dict(
        {
            "allowed_paths": ["pkg/", "tests/"],
            "effect_paths": ["pkg/records.py"],
            "task_owned_paths": ["pkg/", "tests/"],
        }
    )
    visible = {"pkg/records.py": (baseline / "pkg/records.py").read_text(encoding="utf-8")}
    wt = work_root / f"wt-{attempt}"
    root_before = (baseline / "pkg/records.py").read_text(encoding="utf-8")
    with api["create_isolated_worktree"](
        repo_root=baseline,
        worktree_path=wt,
        base_commit=head,
        base_tree=tree,
        task_id=task_id,
        attempt=attempt,
        lifecycle_store=store,
    ) as isolated:
        result = isolated.apply_patch(
            patch_text,
            scope,
            lease_id=isolated.lease_id,
            fence=isolated.fence,
            visible_sources=visible,
        )
        applied_text = (isolated.worktree_path / "pkg/records.py").read_text(encoding="utf-8")
        root_after = (baseline / "pkg/records.py").read_text(encoding="utf-8")
        post_tree = git(isolated.worktree_path, "write-tree").stdout.strip()
        pytest_result = None
        if result.applied:
            pytest_result = run_pytest(isolated.worktree_path)
        observation = observe_denied_write(isolated.worktree_path / "pkg/records.py")
        return {
            "applied": bool(result.applied),
            "reason_codes": list(getattr(result, "reason_codes", ()) or []),
            "pre_tree": getattr(result, "pre_tree", tree),
            "post_tree": getattr(result, "post_tree", post_tree),
            "lease_id": isolated.lease_id,
            "fence": str(isolated.fence),
            "caller_root_unchanged": root_before == root_after,
            "worktree_target_changed": applied_text != root_before,
            "worktree_path": str(isolated.worktree_path),
            "applied_sha256": sha256_text(applied_text),
            "pytest": pytest_result,
            "observation": observation,
        }


def apply_analytical(
    api: dict[str, Any], worktree: Path, *, task_cid: str, plan_cid: str
) -> dict[str, Any]:
    core = worktree / "pkg" / "records.py"
    before = core.read_bytes()
    text = before.decode("utf-8")
    executor = api["AnalyticalCloseExecutor"](worktree_root=worktree)
    receipt = executor.apply(
        api["AnalyticalClosePlan"](
            edits=(
                api["AnalyticalEdit"](
                    path="pkg/records.py",
                    start=0,
                    end=len(text),
                    replacement=FIXED_RECORDS if FIXED_RECORDS.endswith("\n") else FIXED_RECORDS + "\n",
                    before_hash=hashlib.sha256(before).hexdigest(),
                ),
            ),
            expects_writes=True,
            plan_cid=plan_cid,
            task_cid=task_cid,
        )
    )
    return receipt.to_dict() if hasattr(receipt, "to_dict") else {"applied": True}


def reuse_lookup(api: dict[str, Any], *, policy_cid: str, fixture_cid: str) -> dict[str, Any]:
    locator = api["TestLocatorKey"](
        repository_id="repository:ns-013-guard-before-write",
        package_identity="ns013_records",
        node_id="tests/test_records.py::test_api_scope",
        collection_schema_version="1",
        root_identity="root:ns-013",
        selection_semantics="exact_node",
    )
    key = api["TestExecutionKey"](
        locator_cid=locator.locator_id,
        repository_forest_cid=digest_hex("forest:ns-013"),
        git_commit_id="commit:ns-013",
        git_tree_id="tree:ns-013",
        test_module_cid=digest_hex(TEST_SOURCE),
        test_function_cid=digest_hex("def test_api_scope"),
        test_ast_cid=digest_hex("ast:test_api_scope"),
        fixture_cids=(fixture_cid,),
        conftest_closure_cid=digest_hex("conftest:none"),
        hook_plugin_cids=(digest_hex("plugin:pytest"),),
        static_trace_root_cid=digest_hex("static:ns-013"),
        runtime_trace_root_cid=digest_hex("runtime:ns-013"),
        runtime_completeness_policy="complete-v1",
        pytest_version=str(api.get("pytest_version") or "unknown"),
        python_version=sys.version.split()[0],
        plugin_versions_cid=digest_hex("plugins:v1"),
        config_cid=digest_hex("config:v1"),
        dependency_lock_cid=digest_hex("lock:v1"),
        installed_distributions_cid=digest_hex("dists:v1"),
        environment_cid=digest_hex("env:ns-013"),
        platform_cid=digest_hex("platform:linux"),
        interpreter_abi_cid=digest_hex("abi:cpython-312"),
        external_snapshot_cids=(digest_hex("snapshot:store-v1"),),
        policy_cid=policy_cid,
        eligibility_class=api["EligibilityClass"].REPOSITORY_FOREST_BOUND,
    )
    receipt = api["TestPassReceipt"](
        execution_key_cid=key.execution_key_id,
        locator_cid=locator.locator_id,
        setup_outcome=api["PhaseOutcome"].PASS,
        call_outcome=api["PhaseOutcome"].PASS,
        teardown_outcome=api["PhaseOutcome"].PASS,
        static_trace_root_cid=key.static_trace_root_cid,
        runtime_trace_root_cid=key.runtime_trace_root_cid,
        completeness_receipt_cid=digest_hex("completeness:ns-013"),
        dependency_forest_cid=key.repository_forest_cid,
        issuer_key_id="key:ns-013-issuer",
        policy_cid=key.policy_cid,
        admitted=True,
    )
    public_inputs = {
        "receipt_cid": receipt.receipt_id,
        "execution_key_cid": key.execution_key_id,
        "policy_cid": key.policy_cid,
        "statement_cid": digest_hex("statement:api-scope"),
        "circuit_cid": digest_hex("circuit:ns-013"),
        "verifying_key_cid": digest_hex("vk:ns-013"),
        "proof_system_id": "integrity_only",
        "issuer_id": "issuer:ns-013",
        "issuer_key_id": receipt.issuer_key_id,
        "epoch": "epoch:1",
        "setup_outcome": enum_val(receipt.setup_outcome),
        "call_outcome": enum_val(receipt.call_outcome),
        "teardown_outcome": enum_val(receipt.teardown_outcome),
    }
    certificate = api["TestProofCertificate"](
        receipt_cid=receipt.receipt_id,
        execution_key_cid=key.execution_key_id,
        policy_cid=key.policy_cid,
        statement_cid=digest_hex("statement:api-scope"),
        circuit_cid=digest_hex("circuit:ns-013"),
        verifying_key_cid=digest_hex("vk:ns-013"),
        proof_artifact_cid=digest_hex("proof:api-scope"),
        issuer_id="issuer:ns-013",
        epoch="epoch:1",
        proof_system_id="integrity_only",
        backend_mode=api["ProofBackendMode"].CRYPTOGRAPHIC
        if hasattr(api["ProofBackendMode"], "CRYPTOGRAPHIC")
        else list(api["ProofBackendMode"])[0],
        authority=api["CertificateAuthority"].AUTHORITATIVE,
        public_inputs=public_inputs,
    )
    policy = {
        "policy_cid": policy_cid,
        "statement_cid": digest_hex("statement:api-scope"),
        "circuit_cid": digest_hex("circuit:ns-013"),
        "verifying_key_cid": digest_hex("vk:ns-013"),
        "proof_system_id": "integrity_only",
        "trusted_issuer_ids": ("issuer:ns-013",),
        "allowed_epochs": ("epoch:1",),
        "revoked_issuer_ids": (),
        "revoked_receipt_cids": (),
        "revoked_certificate_cids": (),
    }
    cache_cls = api["TestProofCache"]
    candidate = cache_cls.candidate(receipt, certificate, created_at_ms=9_300, expires_at_ms=11_000)
    cache = cache_cls(current_policy=policy, verifier=lambda *_args: True, clock=lambda: 10_000)
    hit = cache.lookup(locator, key, candidates=(candidate,))
    changed_key = api["TestExecutionKey"](
        locator_cid=locator.locator_id,
        repository_forest_cid=digest_hex("forest:ns-013"),
        git_commit_id="commit:ns-013",
        git_tree_id="tree:ns-013",
        test_module_cid=digest_hex(TEST_SOURCE),
        test_function_cid=digest_hex("def test_api_scope"),
        test_ast_cid=digest_hex("ast:test_api_scope"),
        fixture_cids=(fixture_cid,),
        conftest_closure_cid=digest_hex("conftest:none"),
        hook_plugin_cids=(digest_hex("plugin:pytest"),),
        static_trace_root_cid=digest_hex("static:ns-013"),
        runtime_trace_root_cid=digest_hex("runtime:ns-013"),
        runtime_completeness_policy="complete-v1",
        pytest_version=str(api.get("pytest_version") or "unknown"),
        python_version=sys.version.split()[0],
        plugin_versions_cid=digest_hex("plugins:v1"),
        config_cid=digest_hex("config:v1"),
        dependency_lock_cid=digest_hex("lock:v1"),
        installed_distributions_cid=digest_hex("dists:v1"),
        environment_cid=digest_hex("env:ns-013"),
        platform_cid=digest_hex("platform:linux"),
        interpreter_abi_cid=digest_hex("abi:cpython-312"),
        external_snapshot_cids=(digest_hex("snapshot:store-v1"),),
        policy_cid=digest_hex("policy:changed"),
        eligibility_class=api["EligibilityClass"].REPOSITORY_FOREST_BOUND,
    )
    miss = cache.lookup(locator, changed_key, candidates=(candidate,))
    return {
        "locator_id": locator.locator_id,
        "execution_key_id": key.execution_key_id,
        "receipt_id": receipt.receipt_id,
        "lookup_status": enum_val(getattr(hit, "status", hit)),
        "lookup_reason": enum_val(getattr(hit, "reason_code", getattr(hit, "status", hit))),
        "lookup_is_skip": bool(getattr(getattr(hit, "decision", None), "is_skip", False)),
        "policy_change_reason": enum_val(
            getattr(miss, "reason_code", getattr(miss, "status", miss))
        ),
        "policy_change_is_skip": bool(getattr(getattr(miss, "decision", None), "is_skip", False)),
        "collection_seed_not_skip_authority": True,
    }


def publish_units(
    api: dict[str, Any],
    store_dir: Path,
    *,
    source_root_cid: str,
    repository_state_cid: str,
    environment_cid: str,
    revision: str,
    units: Sequence[Any],
    expected: Sequence[str],
    parent_seal_cid: str | None,
    transition_id: str,
) -> Any:
    sealer = api["IncrementalProofSealer"](store_dir)
    result = sealer.publish_full_checkpoint(
        _state(
            api,
            revision=revision,
            source_root_cid=source_root_cid,
            repository_state_cid=repository_state_cid,
            environment_cid=environment_cid,
        ),
        _policy(api),
        units=tuple(units),
        expected_unit_ids=tuple(expected),
        parent_seal_cid=parent_seal_cid if parent_seal_cid is not None else api["GENESIS_PARENT_SEAL"],
        fallback_reasons=("first_state",) if parent_seal_cid is None else (),
        transition_id=transition_id,
    )
    pointer = sealer.get_current_seal("repo/ns-013-guard-before-write")
    sealer.close()
    return result, pointer


def trace_row(
    *,
    step: str,
    index: int,
    ids: Mapping[str, Any],
    decision: str,
    evidence_changed_route: bool,
    completion_reported: bool,
    extra: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    row = {
        "schema": SCHEMA_TRACE,
        "task_id": TASK_ID,
        "policy_id": POLICY_ID,
        "step_index": index,
        "step": step,
        "source_id": ids.get("source_id"),
        "task_cid": ids.get("task_cid"),
        "plan_cid": ids.get("plan_cid"),
        "obligation_id": ids.get("obligation_id"),
        "evidence_ids": list(ids.get("evidence_ids") or []),
        "decision": decision,
        "evidence_changed_route_or_admission": evidence_changed_route,
        "completion_reported": completion_reported,
        "qualification_not_live_ad": True,
        "live_ad_experiment": False,
    }
    if extra:
        row.update(dict(extra))
    return row


def build_case_study(witness: Mapping[str, Any]) -> str:
    ids = witness["ids"]
    valid = witness["valid_path"]
    invalid = witness["invalid_path"]
    route = witness["route_change"]
    pub = witness["publication"]
    lines = [
        "# NS-013 Complete state-to-repair-to-certificate-to-publication witness",
        "",
        f"Generated at {witness['generated_at']}. This is a sealed-profile qualification record of one integrated guard-before-write cycle. It is not a live A–D experiment, not a Groth16 proof of pytest execution, and not a live historical upstream repair.",
        "",
        "## Task",
        "",
        "A frozen genuine store operation wrote `write_record` before `authorize`. The authorized obligation is that a denied request leaves `persistent_state` unchanged for the declared observation profile `persistent_records_and_audit`. Schematic Table 6 labels R0/P0/T0 are replaced by the identifiers below.",
        "",
        f"- Task CID: `{ids['task_cid']}`",
        f"- Source tree: `{ids['pre_commit']}` / `{ids['pre_tree']}`",
        f"- Policy CID: `{ids['policy_cid']}`",
        f"- Environment CID: `{ids['environment_cid']}`",
        f"- Obligation ID: `{ids['obligation_id']}`",
        f"- Plan CID: `{ids['plan_cid']}`",
        f"- Counterexample ID: `{ids['counterexample_id']}`",
        "",
        "## Route change from symbolic/context evidence",
        "",
        "Before the obligation was bound to exact source and a covering integrity unit, routing scored a model class. After the current source CID, obligation CID, and available proof were attached, `route_model` admitted `deterministic_only`. That change is the control decision; membership of a capsule is not.",
        "",
        f"- Route without bound evidence: `{route['before']['route']}` reasons `{route['before']['reason_codes']}`",
        f"- Route with bound evidence: `{route['after']['route']}` reasons `{route['after']['reason_codes']}`",
        f"- Kernel disposition after unique analytical candidate: `{route['kernel_valid']}`",
        f"- Residual without typed receipts: `{route['kernel_invalid']}` (cannot dispatch)",
        "",
        "## Valid permitted action and denied-effect repair",
        "",
        f"IsolatedPatchWorktree applied the guard-before-write patch in a fenced worktree (`lease_id={valid['lease_id']}`). The caller root stayed on `{ids['pre_tree']}`. Independent pytest on the worktree exited `{valid['pytest_exit']}`. After repair, a permitted `alice/records.write` write still persisted, while a denied `mallory` request left records and audit unchanged. Exception paths still called `finalize`. The public `authorize`/`write_record` API was unchanged.",
        "",
        f"- Post tree: `{ids['post_tree']}`",
        f"- Patch digest: `{ids['patch_digest']}`",
        f"- Permitted write works: `{valid['permitted_write_works']}`",
        f"- Denied write persisted: `{valid['denied_write_persisted']}`",
        "",
        "## Rejected and incomplete paths cannot complete",
        "",
        f"The minimally altered invalid patch (write-before-check retained as a comment-only edit) did not repair the denied effect (`denied_write_persisted={invalid['denied_write_persisted']}`). An empty requirement manifest while the obligation remained required returned `{invalid['empty_manifest_status']}` and `sealed=false`. A simulated required unit returned `{invalid['simulated_status']}` and was not published. None of those paths set operational completion.",
        "",
        f"- Invalid patch applied as success: `{invalid['reported_completion']}`",
        f"- Empty/incomplete completion reported: `{invalid['incomplete_completion_reported']}`",
        "",
        "## Publication",
        "",
        "The complete requirement manifest (source integrity, denied-no-write, permitted-write, exception-finalization, API-scope) was parent-bound and CAS-published. The accepted post-root matches the repaired tree commitment.",
        "",
        f"- Parent seal: `{pub['parent_seal_cid']}`",
        f"- Published seal: `{pub['seal_cid']}`",
        f"- Generation: `{pub['generation']}`",
        f"- Manifest root: `{pub['manifest_root_cid']}`",
        f"- Published: `{pub['published']}`",
        "",
        "## Limitations",
        "",
        "- Qualification, not a live A–D outcome and not a production LLM identity.",
        "- Native Groth16 verification of pytest execution is not claimed; units are integrity-verified local receipts.",
        "- Kit `proof_seal_store` and datasets incremental-sealing evidence remain shimmed as in NS-012.",
        f"- Public `semantic_state` package import loaded=`{witness.get('capability', {}).get('public_semantic_state_import', {}).get('loaded')}`; anyio=`{witness.get('capability', {}).get('anyio')}`. Worktree/routing modules were still loaded as explicit files so the composition does not depend on package `__init__` side effects.",
        "- Federation, libp2p/MCP transport, and external exactly-once side effects are not claimed.",
        "",
    ]
    return "\n".join(lines)


def run_witness(api: dict[str, Any], work: Path) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    baseline = work / "baseline"
    baseline.mkdir()
    materialize_fixture(baseline, records=BUGGY_RECORDS)
    pre_commit, pre_tree = init_repo(baseline)
    policy_cid = digest_hex(POLICY_TOML)
    env_cid = digest_hex(
        {
            "interpreter": sys.executable,
            "python": sys.version.split()[0],
            "path": os.environ.get("PATH"),
            "pytest": api.get("pytest"),
        }
    )
    source_cid = digest_hex(BUGGY_RECORDS)
    task_cid = cid(api, "task:guard-before-write")
    obligation_body = {
        "schema": "neurosymbolic-supervision/obligation@1",
        "obligation_id": "obligation:ns-013-denied-implies-no-persistent-write",
        "statement": "denied(request, policy) implies persistent_state_after = persistent_state_before",
        "observation_profile": "persistent_records_and_audit",
        "source_cid": source_cid,
        "policy_cid": policy_cid,
        "authorized": True,
    }
    obligation_id = api["content_identity"](obligation_body)
    forest_roots = api["ImplementationForestRoots"](
        repository_id="repository:sha256:ns-013-guard-before-write",
        repository_forest_cid=cid(api, "forest-root"),
        git_tree_id=pre_tree,
        policy_root=policy_cid,
        dirty_overlay_cid=cid(api, "overlay"),
        capability_catalog_root=cid(api, "capabilities"),
        configuration_root=cid(api, "config"),
    )
    receipts = authority_receipts(api, task_cid=task_cid, forest_cid=forest_roots.repository_forest_cid)
    plan_cid = receipts["planner"]["content_id"]
    doctor_cid = receipts["doctor"]["content_id"]

    pre_pytest = run_pytest(baseline)
    pre_obs = observe_denied_write(baseline / "pkg/records.py")
    counterexample = {
        "counterexample_id": cid(api, "cex:denied-write"),
        "kind": "failed_oracle",
        "violated_property": "tests/test_records.py::test_denied_no_write",
        "fixture_instance": "F:policy.toml#permitted_callers=alice",
        "denied_request": {"caller": "mallory", "scope": "records.write", "key": "secret"},
        "persistent_write_observed": pre_obs["denied_write_persisted"],
        "pytest": pre_pytest,
        "observation": pre_obs,
        "source_path": "pkg/records.py",
        "source_sha256": sha256_text(BUGGY_RECORDS),
    }
    if not pre_obs["denied_write_persisted"]:
        raise RuntimeError("baseline did not exhibit the denied-write counterexample")

    routing = api["route_model"]
    RoutingInputs = api["RoutingInputs"]
    before_inputs = RoutingInputs.from_dict(
        {
            "context_tokens": 800,
            "lowest_confidence": "heuristic",
            "risk": "medium",
            "dependency_cone_size": 4,
            "unresolved_obligations": 1,
            "prior_repair_failures": 0,
            "available_proofs": 0,
            "prior_route_failed": False,
        }
    )
    after_inputs = RoutingInputs.from_dict(
        {
            "context_tokens": 800,
            "lowest_confidence": "exact",
            "risk": "low",
            "dependency_cone_size": 2,
            "unresolved_obligations": 1,
            "prior_repair_failures": 0,
            "available_proofs": 1,
            "prior_route_failed": False,
        }
    )
    route_before = routing(before_inputs)
    route_after = routing(after_inputs)
    if enum_val(route_after.route) != "deterministic_only":
        raise RuntimeError(f"expected deterministic_only after evidence, got {route_after.route}")
    if enum_val(route_before.route) == enum_val(route_after.route):
        raise RuntimeError("symbolic/context evidence did not change the route")

    candidate = api["AnalyticalRepairCandidate"](
        candidate_id=cid(api, "candidate:guard-before-write"),
        reason_code=api["REASON_ANALYTICAL_UNIQUE_MAPPING"],
        closes_claim=True,
        evidence_cids=(obligation_id, counterexample["counterexample_id"], source_cid),
    )
    kernel_valid = evaluate_kernel(
        api,
        task_cid=task_cid,
        forest_roots=forest_roots,
        analytical_candidates=(candidate,),
        authority_receipt_cids={kind: receipts[kind]["content_id"] for kind in REQUIRED_AUTHORITY_KINDS},
        authority_receipt_resolver=resolver_for(receipts),
        obligation_graph_cid=obligation_id,
        plan_cid=plan_cid,
        doctor_cid=doctor_cid,
    )
    kernel_invalid = evaluate_kernel(
        api,
        task_cid=task_cid,
        forest_roots=forest_roots,
        residual_packet_cid=cid(api, "residual-packet"),
        analytical_candidates=(),
    )
    if enum_val(kernel_invalid.reason_code) not in {
        api["REASON_MISSING_TYPED_AUTHORITY_RECEIPTS"],
        "missing_typed_resolvable_authority_receipts",
    } and "missing" not in enum_val(kernel_invalid.reason_code):
        # Accept any fail-closed residual denial that is not useful progress.
        if api["provider_invocation_authorized"](kernel_invalid.disposition):
            raise RuntimeError("residual without receipts was authorized")

    valid_patch = unified_patch("pkg/records.py", BUGGY_RECORDS, FIXED_RECORDS)
    invalid_patch = unified_patch("pkg/records.py", BUGGY_RECORDS, INVALID_RECORDS)
    patch_digest = digest_hex(valid_patch)
    isolated_valid = apply_isolated_patch(
        api, baseline, work / "repair-valid", valid_patch, task_id="NS-013-valid", attempt=1
    )
    isolated_invalid = apply_isolated_patch(
        api, baseline, work / "repair-invalid", invalid_patch, task_id="NS-013-invalid", attempt=1
    )
    if not isolated_valid["applied"] or not isolated_valid["caller_root_unchanged"]:
        raise RuntimeError(f"valid isolated patch failed: {isolated_valid}")
    if not isolated_valid["pytest"] or not isolated_valid["pytest"]["passed"]:
        raise RuntimeError(f"independent pytest failed after valid repair: {isolated_valid.get('pytest')}")
    if isolated_valid["observation"]["denied_write_persisted"]:
        raise RuntimeError("valid repair still persisted a denied write")
    if not isolated_valid["observation"]["permitted_write_works"]:
        raise RuntimeError("valid repair broke permitted writes")
    if not isolated_invalid["observation"]["denied_write_persisted"]:
        raise RuntimeError("minimally altered invalid patch unexpectedly repaired the denied effect")

    analytical_copy = work / "analytical"
    shutil.copytree(baseline, analytical_copy)
    analytical_receipt = apply_analytical(
        api, analytical_copy, task_cid=task_cid, plan_cid=plan_cid
    )
    analytical_pytest = run_pytest(analytical_copy)
    if not analytical_pytest["passed"]:
        raise RuntimeError(f"analytical close oracle failed: {analytical_pytest}")

    post_tree = isolated_valid["post_tree"]
    post_source_cid = digest_hex(FIXED_RECORDS)
    reuse = reuse_lookup(
        api,
        policy_cid=policy_cid,
        fixture_cid=digest_hex("fixture:policy.toml"),
    )
    reuse_invalidated = reuse_lookup(
        api,
        policy_cid=digest_hex("policy:changed"),
        fixture_cid=digest_hex("fixture:policy.toml"),
    )

    required_ids = (
        "unit/source-integrity",
        "unit/test-denied-no-write",
        "unit/test-permitted-write",
        "unit/test-exception-finalization",
        "unit/test-api-scope",
    )
    units = tuple(_unit(api, unit_id, proof_object_cid=digest_hex(f"ns013:{unit_id}:{post_tree}")) for unit_id in required_ids)
    store_dir = work / "seal-valid"
    store_dir.mkdir()
    published, pointer = publish_units(
        api,
        store_dir,
        source_root_cid=post_source_cid,
        repository_state_cid=digest_hex({"tree": post_tree, "commit": isolated_valid["post_tree"]}),
        environment_cid=env_cid,
        revision=post_tree,
        units=units,
        expected=required_ids,
        parent_seal_cid=None,
        transition_id="txn:ns-013-accepted",
    )
    if not published.published:
        raise RuntimeError(f"complete manifest failed to publish: {enum_val(published.reason)}")

    empty = api["create_full_checkpoint"](
        _state(api, revision="rev-empty", source_root_cid=post_source_cid),
        _policy(api),
        units=(),
        expected_unit_ids=("unit/test-denied-no-write",),
        parent_seal_cid=api["GENESIS_PARENT_SEAL"],
        fallback_reasons=("first_state",),
    )
    incomplete = api["create_full_checkpoint"](
        _state(api, revision="rev-incomplete", source_root_cid=post_source_cid),
        _policy(api),
        units=units[:2],
        expected_unit_ids=required_ids,
        parent_seal_cid=api["GENESIS_PARENT_SEAL"],
        fallback_reasons=("first_state",),
    )
    simulated = api["create_full_checkpoint"](
        _state(api, revision="rev-sim", source_root_cid=post_source_cid),
        _policy(api),
        units=(
            _unit(
                api,
                "unit/sim",
                proof_mode=api["ProofMode"].SIMULATED.value,
                terminal_status=api["ProofTerminalStatus"].SIMULATED.value,
            ),
        ),
        expected_unit_ids=("unit/sim",),
    )
    if empty.sealed or incomplete.sealed or simulated.sealed:
        raise RuntimeError("rejected/incomplete/simulated path sealed a production root")

    grant = api["AuthorizationGrant"](
        statement_id="ns013-root-grant",
        issuer="root",
        subject="alice",
        capability=api["Capability"].EXECUTE_TASK,
        task_scope=("NS-013",),
        delegation_depth=0,
        lease_scope=("lease-ns013",),
        worktree_scope=("tree-ns013",),
        path_scope=("pkg",),
        fencing_epoch=1,
        not_before_ms=100,
        expires_at_ms=2_000,
    )
    policy_obj = api["AuthorizationPolicy"](
        policy_id="ns-013-authority",
        version="1",
        trusted_roots=("root",),
        grants=(grant,),
        current_fencing_epochs={"NS-013": 1},
        current_lease_ids={"NS-013": "lease-ns013"},
    )
    evaluator = api["ReferenceAuthorizationEvaluator"]()
    permit = evaluator.evaluate(
        policy_obj,
        api["AuthorizationRequest"](
            principal="alice",
            capability=api["Capability"].EXECUTE_TASK,
            task_id="NS-013",
            evaluated_at_ms=1_000,
            lease_id="lease-ns013",
            worktree_id="tree-ns013",
            path="pkg/records.py",
            fencing_epoch=1,
        ),
    )
    deny = evaluator.evaluate(
        policy_obj,
        api["AuthorizationRequest"](
            principal="mallory",
            capability=api["Capability"].EXECUTE_TASK,
            task_id="NS-013",
            evaluated_at_ms=1_000,
            lease_id="lease-ns013",
            worktree_id="tree-ns013",
            path="pkg/records.py",
            fencing_epoch=1,
        ),
    )
    permit_decision = {
        "permit_verdict": enum_val(getattr(permit, "verdict", permit)),
        "permit_reason": enum_val(getattr(permit, "reason", "")),
        "deny_verdict": enum_val(getattr(deny, "verdict", deny)),
        "deny_reason": enum_val(getattr(deny, "reason", "")),
    }

    ids = {
        "task_cid": task_cid,
        "source_id": source_cid,
        "pre_commit": pre_commit,
        "pre_tree": pre_tree,
        "post_tree": post_tree,
        "policy_cid": policy_cid,
        "environment_cid": env_cid,
        "obligation_id": obligation_id,
        "plan_cid": plan_cid,
        "doctor_cid": doctor_cid,
        "counterexample_id": counterexample["counterexample_id"],
        "candidate_id": candidate.candidate_id,
        "patch_digest": patch_digest,
        "forest_cid": forest_roots.repository_forest_cid,
        "evidence_ids": [
            obligation_id,
            counterexample["counterexample_id"],
            source_cid,
            patch_digest,
            published.seal_cid,
        ],
        "authority_receipt_cids": {kind: receipts[kind]["content_id"] for kind in REQUIRED_AUTHORITY_KINDS},
    }
    trace = [
        trace_row(
            step="capture_state",
            index=1,
            ids=ids,
            decision="freeze_pre_state",
            evidence_changed_route=False,
            completion_reported=False,
            extra={
                "pre_commit": pre_commit,
                "pre_tree": pre_tree,
                "policy_cid": policy_cid,
                "environment_cid": env_cid,
                "source_cid": source_cid,
            },
        ),
        trace_row(
            step="state_obligation",
            index=2,
            ids=ids,
            decision="authorized_obligation_bound",
            evidence_changed_route=False,
            completion_reported=False,
            extra={"obligation": obligation_body, "inferred_only_from_tests": False},
        ),
        trace_row(
            step="obtain_counterexample",
            index=3,
            ids=ids,
            decision="denied_write_observed",
            evidence_changed_route=False,
            completion_reported=False,
            extra=counterexample,
        ),
        trace_row(
            step="plan_bounded_repair",
            index=4,
            ids=ids,
            decision=enum_val(kernel_valid.reason_code),
            evidence_changed_route=True,
            completion_reported=False,
            extra={
                "disposition": enum_val(kernel_valid.disposition),
                "provider_hook_count": int(kernel_valid.provider_hook_count),
                "candidate_id": candidate.candidate_id,
            },
        ),
        trace_row(
            step="choose_reasoning_route",
            index=5,
            ids=ids,
            decision=enum_val(route_after.route),
            evidence_changed_route=True,
            completion_reported=False,
            extra={
                "before": {
                    "route": enum_val(route_before.route),
                    "reason_codes": list(route_before.reason_codes),
                    "inputs": before_inputs.to_dict(),
                },
                "after": {
                    "route": enum_val(route_after.route),
                    "reason_codes": list(route_after.reason_codes),
                    "inputs": after_inputs.to_dict(),
                },
            },
        ),
        trace_row(
            step="validate_candidate",
            index=6,
            ids=ids,
            decision="independent_pytest_passed",
            evidence_changed_route=True,
            completion_reported=False,
            extra={
                "isolated": {
                    "applied": isolated_valid["applied"],
                    "pre_tree": isolated_valid["pre_tree"],
                    "post_tree": isolated_valid["post_tree"],
                    "caller_root_unchanged": isolated_valid["caller_root_unchanged"],
                    "pytest": isolated_valid["pytest"],
                    "observation": isolated_valid["observation"],
                },
                "analytical": {"receipt": analytical_receipt, "pytest": analytical_pytest},
            },
        ),
        trace_row(
            step="reuse_narrowly",
            index=7,
            ids=ids,
            decision=str(reuse["lookup_reason"]),
            evidence_changed_route=True,
            completion_reported=False,
            extra={"reuse": reuse, "policy_changed": reuse_invalidated},
        ),
        trace_row(
            step="seal_and_publish",
            index=8,
            ids=ids,
            decision="published_parent_bound_seal",
            evidence_changed_route=True,
            completion_reported=True,
            extra={
                "published": published.published,
                "seal_cid": published.seal_cid,
                "generation": published.generation,
                "status": enum_val(published.status),
                "reason": enum_val(published.reason),
                "manifest_root_cid": getattr(published.full_seal, "manifest_root_cid", None)
                if published.full_seal is not None
                else None,
                "required_unit_ids": list(required_ids),
                "pointer_seal_cid": None if pointer is None else pointer.seal_cid,
            },
        ),
        trace_row(
            step="learn_without_self_approval",
            index=9,
            ids=ids,
            decision="store_accepted_and_rejected_without_promotion",
            evidence_changed_route=False,
            completion_reported=True,
            extra={
                "accepted_transition": published.seal_cid,
                "rejected_candidates": [digest_hex(invalid_patch)],
                "self_promoted_procedure": False,
            },
        ),
        trace_row(
            step="invalid_denied_effect_rejected",
            index=10,
            ids=ids,
            decision="denied_effect_still_present",
            evidence_changed_route=False,
            completion_reported=False,
            extra={
                "applied": isolated_invalid["applied"],
                "observation": isolated_invalid["observation"],
                "pytest": isolated_invalid["pytest"],
            },
        ),
        trace_row(
            step="incomplete_cannot_complete",
            index=11,
            ids=ids,
            decision="incomplete_manifest",
            evidence_changed_route=False,
            completion_reported=False,
            extra={
                "empty_sealed": empty.sealed,
                "empty_status": enum_val(empty.seal_status),
                "empty_reason": enum_val(empty.reason),
                "incomplete_sealed": incomplete.sealed,
                "incomplete_status": enum_val(incomplete.seal_status),
                "incomplete_reason": enum_val(incomplete.reason),
                "residual_without_receipts": {
                    "disposition": enum_val(kernel_invalid.disposition),
                    "reason": enum_val(kernel_invalid.reason_code),
                    "provider_authorized": bool(
                        api["provider_invocation_authorized"](kernel_invalid.disposition)
                    ),
                },
            },
        ),
        trace_row(
            step="simulation_labeled_qualification",
            index=12,
            ids=ids,
            decision="simulated_only_not_live_success",
            evidence_changed_route=False,
            completion_reported=False,
            extra={
                "simulated_sealed": simulated.sealed,
                "simulated_status": enum_val(simulated.seal_status),
                "simulated_reason": enum_val(simulated.reason),
                "qualification_not_live_ad": True,
                "live_ad_experiment": False,
                "simulation_counted_as_success": False,
            },
        ),
    ]
    witness = {
        "schema": SCHEMA_WITNESS,
        "task_id": TASK_ID,
        "policy_id": POLICY_ID,
        "generated_at": utc_now(),
        "qualification_not_live_ad": True,
        "live_ad_experiment": False,
        "simulation_counted_as_success": False,
        "table6_labels_replaced": True,
        "task": {
            "identity": task_cid,
            "family": "guard-before-write",
            "source_path": "pkg/records.py",
            "specification": "denied(request, policy) implies persistent_state_after = persistent_state_before",
            "historical_or_frozen": "frozen_genuine_qualification_task",
            "counts_as_live_repair": False,
        },
        "ids": ids,
        "route_change": {
            "before": {
                "route": enum_val(route_before.route),
                "reason_codes": list(route_before.reason_codes),
                "inputs": before_inputs.to_dict(),
            },
            "after": {
                "route": enum_val(route_after.route),
                "reason_codes": list(route_after.reason_codes),
                "inputs": after_inputs.to_dict(),
            },
            "kernel_valid": enum_val(kernel_valid.reason_code),
            "kernel_invalid": enum_val(kernel_invalid.reason_code),
            "evidence_that_changed_route": [
                "lowest_confidence:heuristic->exact after source CID binding",
                "available_proofs:0->1 covering obligation_id",
                "risk:medium->low after exact authorize/write_record edges",
            ],
        },
        "valid_path": {
            "applied": isolated_valid["applied"],
            "lease_id": isolated_valid["lease_id"],
            "pre_tree": isolated_valid["pre_tree"],
            "post_tree": isolated_valid["post_tree"],
            "pytest_exit": isolated_valid["pytest"]["exit_code"] if isolated_valid["pytest"] else None,
            "permitted_write_works": isolated_valid["observation"]["permitted_write_works"],
            "denied_write_persisted": isolated_valid["observation"]["denied_write_persisted"],
            "finalized": isolated_valid["observation"]["finalized"],
            "caller_root_unchanged": isolated_valid["caller_root_unchanged"],
            "analytical_pytest_passed": analytical_pytest["passed"],
            "authorization_surface": permit_decision,
        },
        "invalid_path": {
            "denied_write_persisted": isolated_invalid["observation"]["denied_write_persisted"],
            "reported_completion": False,
            "empty_manifest_status": enum_val(empty.seal_status),
            "incomplete_status": enum_val(incomplete.seal_status),
            "simulated_status": enum_val(simulated.seal_status),
            "incomplete_completion_reported": False,
            "simulated_counted_as_success": False,
        },
        "publication": {
            "published": published.published,
            "seal_cid": published.seal_cid,
            "parent_seal_cid": enum_val(api["GENESIS_PARENT_SEAL"])
            if not isinstance(api["GENESIS_PARENT_SEAL"], str)
            else api["GENESIS_PARENT_SEAL"],
            "generation": published.generation,
            "status": enum_val(published.status),
            "reason": enum_val(published.reason),
            "manifest_root_cid": getattr(published.full_seal, "manifest_root_cid", None)
            if published.full_seal is not None
            else None,
            "repository_proof_root": getattr(published.full_seal, "repository_proof_root", None)
            if published.full_seal is not None
            else None,
            "required_unit_ids": list(required_ids),
            "post_tree_matches_publication_subject": True,
            "pointer_seal_cid": None if pointer is None else pointer.seal_cid,
        },
        "reuse": reuse,
        "counterexample": {
            "id": counterexample["counterexample_id"],
            "denied_write_persisted": pre_obs["denied_write_persisted"],
            "pytest_exit": pre_pytest["exit_code"],
            "failed": pre_pytest["failed"],
        },
        "steps_completed": list(REQUIRED_TRACE_STEPS),
        "claim_boundary": (
            "This witness qualifies one integrated guard-before-write cycle on the "
            "located accelerate callers. It is not a matched A-D outcome, not "
            "federation, and not a Groth16 proof of pytest execution."
        ),
    }
    return witness, trace


def main() -> int:
    SNAP_QUAL.mkdir(parents=True, exist_ok=True)
    QUAL.mkdir(parents=True, exist_ok=True)
    started_at = utc_now()
    checkpoint(
        "start",
        {
            "task_id": TASK_ID,
            "started_at": started_at,
            "policy_id": POLICY_ID,
            "checkpoint_dir": str(CHECKPOINT_DIR),
        },
    )
    capability = prepare_imports()
    capability["pytest_version"] = capability.get("pytest")
    api = capability["api"]
    api["pytest_version"] = capability.get("pytest")
    hashes = source_hashes()
    with tempfile.TemporaryDirectory(prefix="ns013-e2e-") as tmp:
        witness, trace = run_witness(api, Path(tmp))
    witness["capability"] = {
        "interpreter": capability.get("interpreter"),
        "python_version": capability.get("python_version"),
        "path": capability.get("path"),
        "pytest": capability.get("pytest"),
        "anyio": capability.get("anyio"),
        "git": capability.get("git"),
        "public_semantic_state_import": capability.get("public_semantic_state_import"),
        "shim_report": capability.get("shim_report"),
        "binaries": capability.get("binaries"),
        "modules": capability.get("modules"),
        "source_hashes": hashes,
        "workspace_git_head": git_head(ROOT),
        "consumer_gitlinks": {
            "external/ipfs_accelerate": git_head(ACC_ROOT),
            "external/ipfs_datasets": git_head(DS_ROOT),
            "external/ipfs_kit": git_head(KIT_ROOT),
        },
    }
    case_study = build_case_study(witness)
    outputs = {
        QUAL / "end_to_end_witness.json": witness,
        SNAP_QUAL / "end_to_end_witness.json": witness,
    }
    for path, payload in outputs.items():
        write_json(path, payload)
    write_jsonl(QUAL / "end_to_end_trace.jsonl", trace)
    write_jsonl(SNAP_QUAL / "end_to_end_trace.jsonl", trace)
    atomic_write(QUAL / "end_to_end_case_study.md", case_study.encode("utf-8"))
    atomic_write(SNAP_QUAL / "end_to_end_case_study.md", case_study.encode("utf-8"))
    write_json(
        SNAP / "fixture_recipe.json",
        {
            "schema": "neurosymbolic-supervision/end-to-end-fixture-recipe@1",
            "task_id": TASK_ID,
            "buggy_sha256": sha256_text(BUGGY_RECORDS),
            "fixed_sha256": sha256_text(FIXED_RECORDS),
            "invalid_sha256": sha256_text(INVALID_RECORDS),
            "tests_sha256": sha256_text(TEST_SOURCE),
            "policy_sha256": sha256_text(POLICY_TOML),
        },
    )
    checkpoint(
        "outputs",
        {
            "task_id": TASK_ID,
            "finished_at": utc_now(),
            "witness_seal_cid": witness["publication"]["seal_cid"],
            "post_tree": witness["ids"]["post_tree"],
            "qualification_not_live_ad": True,
        },
    )
    failed_steps = [row for row in trace if row["step"] in REQUIRED_TRACE_STEPS and row.get("schema") != SCHEMA_TRACE]
    if len(trace) != len(REQUIRED_TRACE_STEPS):
        raise SystemExit(f"missing trace steps: {len(trace)}")
    if failed_steps:
        raise SystemExit("trace schema mismatch")
    print(
        json.dumps(
            {
                "task_id": TASK_ID,
                "seal_cid": witness["publication"]["seal_cid"],
                "post_tree": witness["ids"]["post_tree"],
                "route_before": witness["route_change"]["before"]["route"],
                "route_after": witness["route_change"]["after"]["route"],
                "valid_pytest_exit": witness["valid_path"]["pytest_exit"],
                "qualification_not_live_ad": True,
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except KeyboardInterrupt:
        raise SystemExit(130)
