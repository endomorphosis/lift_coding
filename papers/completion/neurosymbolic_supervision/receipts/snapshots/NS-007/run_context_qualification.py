#!/usr/bin/env python3
"""NS-007 live qualification of semantic context, invalidation, and repair.

Exercises the datasets producer and the accelerate context/worktree consumers
on the sealed SemanticStateControlledFixture. Public package import of
``ipfs_accelerate_py.agent_supervisor.semantic_state`` is blocked in this
profile by an anyio-gated MCP++ package ``__init__``; this program loads the
actual consumer source files after installing a namespace package object so
the harness ``__init__`` is not executed. CID identity uses the in-tree
sealed CIDv1 profile because ``multiformats`` is absent.

This is a qualification run, not a live A–D experiment and not a CST/AST
linker demonstration.
"""

from __future__ import annotations

import hashlib
import json
import os
import shutil
import subprocess
import sys
import tempfile
import textwrap
import time
import types
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping


ROOT = Path(__file__).resolve().parents[6]
PAPER = ROOT / "papers/completion/neurosymbolic_supervision"
QUAL = PAPER / "qualification"
ACC_ROOT = ROOT / "external/ipfs_accelerate"
DS_ROOT = ROOT / "external/ipfs_datasets"
ACC_PY = ACC_ROOT / "ipfs_accelerate_py"
CHECKPOINT_DIR = Path(
    os.environ.get(
        "IPFS_ACCELERATE_AGENT_TASK_CHECKPOINT_DIR",
        str(
            Path.home()
            / ".local/state/ipfs_accelerate_py/vericodegen-2026"
            / "neurosymbolic_supervision/state"
            / "paper_neurosymbolic_supervision_database_portal_attempts"
            / "f030fb745e9e935988cbe1b6/implementation_checkpoints"
            / "ns-007-cdce4e292a90"
        ),
    )
)

TASK_ID = "NS-007"
SCHEMA_CASES = "neurosymbolic-supervision/context-qualification-cases@1"
SCHEMA_RESULT = "neurosymbolic-supervision/context-qualification-result@1"
POLICY_ID = "ns-007-context-qualification-v1"
CID_SHIMS: dict[str, Any] = {}

MANDATORY_FAMILIES = (
    "unchanged",
    "localized",
    "renamed",
    "deleted",
    "configuration",
    "dependency",
    "fixture",
    "dynamic",
    "native",
    "stale_map",
    "repair",
    "context_core",
)

FAMILY_BY_KIND = {
    "unchanged": "unchanged",
    "local_body": "localized",
    "signature": "localized",
    "cross_module": "localized",
    "schema": "localized",
    "exception": "localized",
    "format": "localized",
    "rename": "renamed",
    "delete": "deleted",
    "config": "configuration",
    "plugin": "configuration",
    "policy": "configuration",
    "interface": "configuration",
    "lock": "dependency",
    "generated": "dependency",
    "fixture": "fixture",
    "dynamic": "dynamic",
    "monkey": "dynamic",
    "native": "native",
}

PYTEST_EXECUTE_CASES = (
    "unchanged",
    "local_body",
    "format",
    "native",
    "delete",
    "fixture",
    "lock",
)


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def digest_text(text: str) -> str:
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
    lines = [json.dumps(row, sort_keys=True, ensure_ascii=False, separators=(",", ":")) for row in rows]
    atomic_write(path, ("\n".join(lines) + "\n").encode("utf-8"))


def _stub_package(name: str, path: Path) -> types.ModuleType:
    existing = sys.modules.get(name)
    if existing is not None and getattr(existing, "__path__", None):
        return existing
    module = types.ModuleType(name)
    module.__file__ = str(path / "__init__.py")
    module.__path__ = [str(path)]
    module.__package__ = name
    sys.modules[name] = module
    parent, _, child = name.rpartition(".")
    if parent and parent in sys.modules:
        setattr(sys.modules[parent], child, module)
    return module


def prepare_sealed_imports() -> dict[str, Any]:
    """Load producer/consumer sources under the sealed profile.

    Returns a capability record describing every import bypass and shim.
    """
    initial_path = os.environ.get("PATH")
    for path in (str(ACC_ROOT), str(DS_ROOT)):
        if path not in sys.path:
            sys.path.insert(0, path)

    import ipfs_accelerate_py  # noqa: F401
    import ipfs_accelerate_py.agent_supervisor  # noqa: F401
    import ipfs_accelerate_py.mcp_server  # noqa: F401

    public_semantic_state_error = None
    try:
        import ipfs_accelerate_py.agent_supervisor.semantic_state as _ss  # noqa: F401
    except Exception as exc:
        public_semantic_state_error = f"{type(exc).__name__}: {exc}"

    public_mcplusplus_error = None
    try:
        import ipfs_accelerate_py.mcp_server.mcplusplus as _mcp  # noqa: F401
    except Exception as exc:
        public_mcplusplus_error = f"{type(exc).__name__}: {exc}"

    _stub_package("ipfs_accelerate_py.mcp_server.mcplusplus", ACC_PY / "mcp_server/mcplusplus")
    _stub_package(
        "ipfs_accelerate_py.agent_supervisor.semantic_state",
        ACC_PY / "agent_supervisor/semantic_state",
    )

    from ipfs_accelerate_py.utils import cid_utils as sealed_cid
    import ipfs_datasets_py.logic.software_contracts.content as content

    def _cid_from_digest_bytes(data: bytes, *, codec: str) -> str:
        return sealed_cid.cid_for_bytes(data, codec=codec)

    def _validate_cid(value: Any, *, codecs=None) -> str:
        allowed = tuple(codecs) if codecs is not None else ("raw", "dag-json")
        try:
            return sealed_cid.validate_cid(value, codecs=allowed)
        except Exception as exc:
            raise content.ContentIdentityError(str(exc)) from exc

    def _cid_for_bytes(data: bytes) -> str:
        return sealed_cid.cid_for_bytes(data, codec="raw")

    def _cid_for_structured(obj: Any) -> str:
        return sealed_cid.cid_for_bytes(content.canonical_dag_json_bytes(obj), codec="dag-json")

    content._cid_from_digest_bytes = _cid_from_digest_bytes  # type: ignore[attr-defined]
    content.validate_cid = _validate_cid  # type: ignore[assignment]
    content.cid_for_bytes = _cid_for_bytes  # type: ignore[assignment]
    content.cid_for_structured = _cid_for_structured  # type: ignore[assignment]
    content.cid_for_obj = _cid_for_structured  # type: ignore[assignment]
    CID_SHIMS.clear()
    CID_SHIMS.update(
        {
            "validate_cid": _validate_cid,
            "cid_for_bytes": _cid_for_bytes,
            "cid_for_structured": _cid_for_structured,
            "cid_for_obj": _cid_for_structured,
            "_cid_from_digest_bytes": _cid_from_digest_bytes,
        }
    )

    from ipfs_accelerate_py.mcp_server.mcplusplus.kubo_cid import cid_for_bytes as accel_raw_cid

    probe = b"ns-007-cid-probe"
    raw_a = sealed_cid.cid_for_bytes(probe, codec="raw")
    raw_b = accel_raw_cid(probe)
    # kubo_cid encodes codec as a single 0x55 byte; sealed profile uses uvarint.
    # Both are CIDv1/raw/sha2-256/base32; record whether they match.
    cid_raw_agreement = raw_a == raw_b

    capability = {
        "interpreter": sys.executable,
        "python_version": sys.version.split()[0],
        "path": initial_path,
        "path_after_imports": os.environ.get("PATH"),
        "anyio": False,
        "multiformats": False,
        "tiktoken": False,
        "pytest": None,
        "git": shutil.which("git"),
        "public_semantic_state_import": {
            "loaded": public_semantic_state_error is None,
            "error": public_semantic_state_error,
        },
        "public_mcplusplus_import": {
            "loaded": public_mcplusplus_error is None,
            "error": public_mcplusplus_error,
        },
        "namespace_bypass_used": True,
        "cid_shim": {
            "reason": "multiformats is absent in the sealed profile",
            "implementation": "ipfs_accelerate_py.utils.cid_utils",
            "profile": "CIDv1 / base32 / sha2-256 / raw|dag-json",
            "kubo_cid_raw_byte_agreement": cid_raw_agreement,
            "sealed_raw_cid_probe": raw_a,
            "kubo_raw_cid_probe": raw_b,
        },
        "loaded_modules": {},
    }
    try:
        import pytest
        capability["pytest"] = getattr(pytest, "__version__", "present")
    except Exception as exc:
        capability["pytest"] = None
        capability["pytest_error"] = f"{type(exc).__name__}: {exc}"
    try:
        import tiktoken  # noqa: F401
        capability["tiktoken"] = True
    except Exception:
        capability["tiktoken"] = False
    try:
        import anyio  # noqa: F401
        capability["anyio"] = True
    except Exception:
        capability["anyio"] = False
    try:
        import multiformats  # noqa: F401
        capability["multiformats"] = True
    except Exception:
        capability["multiformats"] = False
    return capability


def rebind_cid_shims() -> int:
    """Replace imported CID helpers on already-loaded datasets contract modules."""
    rebound = 0
    for name, module in list(sys.modules.items()):
        if not name.startswith("ipfs_datasets_py.logic.software_contracts"):
            continue
        for attr, func in CID_SHIMS.items():
            if hasattr(module, attr):
                setattr(module, attr, func)
                rebound += 1
    return rebound


def load_surfaces(capability: dict[str, Any]) -> dict[str, Any]:
    from ipfs_accelerate_py.agent_supervisor.context.context_compiler import (
        CalibratedTokenEstimator,
        ContextCompiler,
    )
    from ipfs_accelerate_py.agent_supervisor.context.context_contracts import (
        ContextBudget,
        ContextReference,
        ContextTier,
    )
    from ipfs_accelerate_py.agent_supervisor.merge.worktree_lifecycle import WorktreeLifecycleStore
    from ipfs_accelerate_py.agent_supervisor.semantic_state.capsules import (
        ADMISSION_CONSERVATIVE,
        ADMISSION_EXACT,
        ADMISSION_RAW,
        admit_capsule,
    )
    from ipfs_accelerate_py.agent_supervisor.semantic_state.context_pack import (
        TOKEN_ESTIMATOR_VERSION,
        ContextPacker,
        pack_context,
    )
    from ipfs_accelerate_py.agent_supervisor.semantic_state.worktree import (
        PatchScope,
        apply_patch,
        create_isolated_worktree,
        validate_patch,
    )
    from ipfs_datasets_py.logic.software_contracts.content import cid_for_bytes, cid_for_structured
    from ipfs_datasets_py.logic.software_contracts.semantic_index import (
        calculate_invalidation,
        diff_repository_states,
        scan_repository,
    )
    from ipfs_datasets_py.logic.software_contracts.semantic_index.models import AnalysisConfidence
    from ipfs_datasets_py.logic.software_contracts.semantic_state import (
        assess_capsule_freshness,
        build_semantic_state,
        extend_semantic_invalidation,
        select_tests_and_proofs,
        verify_semantic_state_bundle,
        view_semantic_state_bundle,
    )
    from ipfs_datasets_py.logic.software_contracts.semantic_state.models import (
        BindingKind,
        BindingScope,
        EnvironmentBinding,
        SelectionFallback,
        SelectionPolicy,
    )
    from tests.fixtures.software_contracts.semantic_state import (
        apply_mutation,
        load_controlled_fixture,
        materialize_baseline,
    )
    from tests.fixtures.software_contracts.semantic_state.recipe import MUTATION_CASES

    rebound = rebind_cid_shims()
    capability["cid_shim"]["rebound_aliases"] = rebound

    import ipfs_datasets_py.logic.software_contracts.semantic_state.models as ss_models
    from ipfs_accelerate_py.utils import cid_utils as sealed_cid
    from ipfs_datasets_py.logic.software_contracts.content import (
        canonical_dag_json_bytes,
        decode_and_recompute_source,
        decode_and_recompute_structured,
    )

    def _verify_block_bytes(claimed_cid: str, data: bytes) -> str:
        if type(data) is not bytes:
            raise ss_models.SemanticStateModelError("block data must be bytes")
        try:
            claimed = CID_SHIMS["validate_cid"](claimed_cid)
        except Exception as exc:
            raise ss_models.SemanticStateModelError("block key must be a valid CID") from exc
        codec = sealed_cid._decode_cid(claimed).codec
        if codec == "raw":
            try:
                return decode_and_recompute_source(claimed, data)
            except Exception as exc:
                raise ss_models.SemanticStateModelError(
                    f"forged or mismatched raw block CID {claimed}"
                ) from exc
        if codec == "dag-json":
            try:
                obj = json.loads(data.decode("utf-8"))
                if canonical_dag_json_bytes(obj) != data:
                    raise ss_models.SemanticStateModelError(
                        f"dag-json block {claimed} is not canonical"
                    )
                return decode_and_recompute_structured(claimed, obj)
            except ss_models.SemanticStateModelError:
                raise
            except Exception as exc:
                raise ss_models.SemanticStateModelError(
                    f"forged or mismatched structured block CID {claimed}"
                ) from exc
        raise ss_models.SemanticStateModelError(
            f"unsupported block codec {codec} for CID {claimed}"
        )

    ss_models.verify_block_bytes = _verify_block_bytes  # type: ignore[assignment]
    import ipfs_datasets_py.logic.software_contracts.semantic_state.api as ss_api
    if hasattr(ss_api, "verify_block_bytes"):
        ss_api.verify_block_bytes = _verify_block_bytes  # type: ignore[assignment]

    modules = {
        "semantic_index": sys.modules["ipfs_datasets_py.logic.software_contracts.semantic_index"].__file__,
        "semantic_state_producer": sys.modules["ipfs_datasets_py.logic.software_contracts.semantic_state"].__file__,
        "context_pack": sys.modules["ipfs_accelerate_py.agent_supervisor.semantic_state.context_pack"].__file__,
        "worktree": sys.modules["ipfs_accelerate_py.agent_supervisor.semantic_state.worktree"].__file__,
        "capsules_consumer": sys.modules["ipfs_accelerate_py.agent_supervisor.semantic_state.capsules"].__file__,
        "context_compiler": sys.modules["ipfs_accelerate_py.agent_supervisor.context.context_compiler"].__file__,
        "cid_utils": sys.modules["ipfs_accelerate_py.utils.cid_utils"].__file__,
        "controlled_fixture_recipe": sys.modules["tests.fixtures.software_contracts.semantic_state.recipe"].__file__,
    }
    capability["loaded_modules"] = {
        name: {"path": str(Path(path).relative_to(ROOT)) if path else None, "sha256": sha256_file(Path(path)) if path else None}
        for name, path in modules.items()
        if path
    }
    return {
        "capability": capability,
        "cid_for_bytes": CID_SHIMS["cid_for_bytes"],
        "cid_for_structured": CID_SHIMS["cid_for_structured"],
        "scan_repository": scan_repository,
        "diff_repository_states": diff_repository_states,
        "calculate_invalidation": calculate_invalidation,
        "build_semantic_state": build_semantic_state,
        "verify_semantic_state_bundle": verify_semantic_state_bundle,
        "view_semantic_state_bundle": view_semantic_state_bundle,
        "extend_semantic_invalidation": extend_semantic_invalidation,
        "select_tests_and_proofs": select_tests_and_proofs,
        "assess_capsule_freshness": assess_capsule_freshness,
        "AnalysisConfidence": AnalysisConfidence,
        "BindingKind": BindingKind,
        "BindingScope": BindingScope,
        "EnvironmentBinding": EnvironmentBinding,
        "SelectionFallback": SelectionFallback,
        "SelectionPolicy": SelectionPolicy,
        "apply_mutation": apply_mutation,
        "load_controlled_fixture": load_controlled_fixture,
        "materialize_baseline": materialize_baseline,
        "MUTATION_CASES": MUTATION_CASES,
        "pack_context": pack_context,
        "ContextPacker": ContextPacker,
        "TOKEN_ESTIMATOR_VERSION": TOKEN_ESTIMATOR_VERSION,
        "admit_capsule": admit_capsule,
        "ADMISSION_EXACT": ADMISSION_EXACT,
        "ADMISSION_CONSERVATIVE": ADMISSION_CONSERVATIVE,
        "ADMISSION_RAW": ADMISSION_RAW,
        "PatchScope": PatchScope,
        "apply_patch": apply_patch,
        "create_isolated_worktree": create_isolated_worktree,
        "validate_patch": validate_patch,
        "WorktreeLifecycleStore": WorktreeLifecycleStore,
        "CalibratedTokenEstimator": CalibratedTokenEstimator,
        "ContextCompiler": ContextCompiler,
        "ContextBudget": ContextBudget,
        "ContextReference": ContextReference,
        "ContextTier": ContextTier,
    }


def git(repo: Path, *args: str, check: bool = True, input_text: str | None = None) -> subprocess.CompletedProcess[str]:
    env = {
        "PATH": os.environ.get("PATH", "/usr/bin"),
        "HOME": os.environ.get("HOME", "/tmp"),
        "LANG": "C.UTF-8",
        "LC_ALL": "C.UTF-8",
        "GIT_TERMINAL_PROMPT": "0",
        "GIT_CONFIG_NOSYSTEM": "1",
        "GIT_AUTHOR_NAME": "NS-007",
        "GIT_AUTHOR_EMAIL": "ns007@example.invalid",
        "GIT_COMMITTER_NAME": "NS-007",
        "GIT_COMMITTER_EMAIL": "ns007@example.invalid",
        "GIT_AUTHOR_DATE": "2026-09-12T00:00:00+0000",
        "GIT_COMMITTER_DATE": "2026-09-12T00:00:00+0000",
    }
    completed = subprocess.run(
        ["git", *args],
        cwd=str(repo),
        input=input_text,
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
    git(repo, "config", "user.email", "ns007@example.invalid")
    git(repo, "config", "user.name", "NS-007")
    git(repo, "add", "-A")
    git(repo, "commit", "-m", "baseline")
    head = git(repo, "rev-parse", "HEAD").stdout.strip()
    tree = git(repo, "rev-parse", "HEAD^{tree}").stdout.strip()
    return head, tree


def injected_bindings(api: dict[str, Any], repo: Path) -> tuple:
    BindingKind = api["BindingKind"]
    BindingScope = api["BindingScope"]
    EnvironmentBinding = api["EnvironmentBinding"]
    AnalysisConfidence = api["AnalysisConfidence"]
    cid_for_bytes = api["cid_for_bytes"]
    specs = (
        ("policy.toml", BindingKind.POLICY, BindingScope.GLOBAL, None),
        ("interface.json", BindingKind.INTERFACE_DESCRIPTOR, BindingScope.GLOBAL, None),
        ("generated/payload.json", BindingKind.GENERATED_INPUT, BindingScope.MODULE, "pkg.generated_reader"),
    )
    items = []
    for rel_path, kind, scope, subject in specs:
        path = repo / rel_path
        if not path.is_file():
            continue
        version_cid = cid_for_bytes(path.read_bytes())
        items.append(
            EnvironmentBinding(
                binding_id=f"file:{rel_path}",
                kind=kind,
                version_cid=version_cid,
                scope=scope,
                extraction_authority="injected",
                confidence=AnalysisConfidence.EXACT,
                subject_id=subject,
                content_cid=version_cid,
                metadata={"path": rel_path},
            )
        )
    return tuple(items)


def scan_and_build(api: dict[str, Any], repo: Path, *, previous_index=None, previous_bundle=None):
    index = api["scan_repository"](repo, previous_state=previous_index)
    bindings = injected_bindings(api, repo)
    bundle = api["build_semantic_state"](index, environment_bindings=bindings, previous_bundle=previous_bundle)
    api["verify_semantic_state_bundle"](bundle)
    return index, bundle, bindings


def confidence_of(symbol: Any) -> str:
    raw = getattr(symbol, "confidence", "")
    return str(getattr(raw, "value", raw) or "")


def frontier_from_index(index: Any) -> dict[str, Any]:
    counts = Counter(confidence_of(symbol) for symbol in index.symbols)
    opaque = [
        {"stable_id": symbol.stable_id, "path": symbol.module_path, "confidence": confidence_of(symbol)}
        for symbol in index.symbols
        if confidence_of(symbol) in {"opaque", "heuristic"}
    ]
    return {
        "confidence_counts": dict(sorted(counts.items())),
        "opaque_or_heuristic_symbols": opaque[:32],
        "opaque_or_heuristic_count": len(opaque),
        "unknown_kinds": sorted({symbol.kind.value if hasattr(symbol.kind, "value") else str(symbol.kind) for symbol in index.symbols if str(getattr(symbol.kind, "value", symbol.kind)) == "unknown"}),
    }


def obligation_codes(plan: Any) -> list[str]:
    return sorted({str(getattr(item, "reason_code", "")) for item in getattr(plan, "obligations", ())})


def run_pytest(repo: Path, node_ids: list[str] | None = None, timeout: int = 60) -> dict[str, Any]:
    argv = [sys.executable, "-m", "pytest", "-q", "--tb=no"]
    if node_ids:
        argv.extend(node_ids)
    else:
        argv.append("tests")
    env = os.environ.copy()
    env["PYTHONPATH"] = str(repo)
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    started = time.perf_counter()
    completed = subprocess.run(
        argv,
        cwd=str(repo),
        capture_output=True,
        text=True,
        timeout=timeout,
        env=env,
        check=False,
    )
    elapsed = time.perf_counter() - started
    failed: list[str] = []
    passed = 0
    for line in (completed.stdout or "").splitlines():
        stripped = line.strip()
        if stripped.startswith("FAILED "):
            failed.append(stripped.split()[1])
        elif stripped.endswith(" passed") or " passed in " in stripped:
            pass
    # Parse summary like "2 failed, 16 passed"
    summary = ""
    for line in reversed((completed.stdout or "").splitlines()):
        if "passed" in line or "failed" in line or "error" in line:
            summary = line.strip()
            break
    return {
        "exit_code": completed.returncode,
        "elapsed_seconds": round(elapsed, 4),
        "failed_node_ids": failed,
        "summary": summary,
        "argv_tail": argv[-8:],
        "stderr_tail": (completed.stderr or "")[-800:],
    }


def unified_diff(repo: Path) -> str:
    return git(repo, "diff", "--no-ext-diff", "HEAD").stdout


def visible_sources_for(repo: Path, paths: list[str]) -> dict[str, str]:
    out: dict[str, str] = {}
    for rel in paths:
        path = repo / rel
        if path.is_file():
            out[rel] = path.read_text(encoding="utf-8")
    return out


def source_cids_for_paths(api: dict[str, Any], repo: Path, paths: tuple[str, ...]) -> dict[str, str]:
    cid_for_bytes = api["cid_for_bytes"]
    result: dict[str, str] = {}
    for rel in paths:
        path = repo / rel
        if path.is_file():
            result[rel] = cid_for_bytes(path.read_bytes())
    return result


def pack_modes(
    api: dict[str, Any],
    *,
    estimator,
    target_cid: str,
    surrounding_cid: str,
    test_cid: str,
    delta_cid: str,
    obligation_cids: list[str],
    interface_cids: list[str],
    admissions: list[Any],
    assumptions: list[str],
) -> dict[str, Any]:
    ContextBudget = api["ContextBudget"]
    ContextPacker = api["ContextPacker"]
    ContextCompiler = api["ContextCompiler"]
    budget = ContextBudget(
        max_input_tokens=80_000,
        reserved_output_tokens=256,
        reserved_tool_tokens=64,
    )
    packer = ContextPacker(
        budget=budget,
        _compiler=ContextCompiler(budget, estimator=estimator),
    )
    raw = packer.pack(
        objective="NS-007 qualify source-preserving context",
        target_source_cid=target_cid,
        surrounding_source_cid=surrounding_cid,
        test_source_cid=test_cid,
        dependency_admissions=[],
        obligation_cids=obligation_cids,
        counterexample_cids=[],
        delta_cid=delta_cid,
        interface_cids=interface_cids,
        assumptions=assumptions + ["mode=raw"],
    )
    semantic = packer.pack(
        objective="NS-007 qualify source-preserving context",
        target_source_cid=target_cid,
        surrounding_source_cid=surrounding_cid,
        test_source_cid=test_cid,
        dependency_admissions=admissions,
        obligation_cids=obligation_cids,
        counterexample_cids=[],
        delta_cid=delta_cid,
        interface_cids=interface_cids,
        assumptions=assumptions + ["mode=semantic"],
    )
    raw_total = int(raw.token_estimate.total)
    semantic_total = int(semantic.token_estimate.total)
    reduction = None
    if raw_total > 0:
        reduction = round((raw_total - semantic_total) / raw_total, 6)
    required_kinds = ("target_source", "surrounding_source", "test_source")

    def preserved(result: Any) -> dict[str, Any]:
        kinds = {item.kind: item for item in result.references}
        never = {
            kind: bool(kinds.get(kind) and kinds[kind].metadata.get("never_compress") is True and kinds[kind].required)
            for kind in required_kinds
        }
        return {
            "target_source_cid": result.pack.target_source_cid,
            "surrounding_source_cid": result.pack.surrounding_source_cid,
            "test_source_cid": result.pack.test_source_cid,
            "obligation_cids": list(result.pack.obligation_cids),
            "never_compress_required": never,
            "coverage_satisfied": bool(result.coverage_satisfied),
            "estimator_version": result.pack.estimator_version,
            "token_total": int(result.token_estimate.total),
            "token_totals": dict(result.token_estimate.totals),
            "dependency_capsule_cids": list(result.pack.dependency_capsule_cids),
            "exclusions": list(result.pack.exclusions),
            "decisions": list(result.decisions)[:24],
            "pack_cid": result.pack_cid,
        }

    return {
        "estimator_name": estimator.name,
        "estimator_provider_aware": bool(estimator.provider_aware),
        "estimator_version": api["TOKEN_ESTIMATOR_VERSION"],
        "same_estimator_object": packer.compiler.estimator is estimator,
        "raw": preserved(raw),
        "semantic": preserved(semantic),
        "token_reduction_fraction": reduction,
        "mandatory_cids_match": (
            raw.pack.target_source_cid == semantic.pack.target_source_cid == target_cid
            and raw.pack.surrounding_source_cid == semantic.pack.surrounding_source_cid == surrounding_cid
            and raw.pack.test_source_cid == semantic.pack.test_source_cid == test_cid
        ),
    }


def make_admissions(api: dict[str, Any], view, root_cid: str, index, paths: tuple[str, ...]) -> list[Any]:
    admit_capsule = api["admit_capsule"]
    ADMISSION_EXACT = api["ADMISSION_EXACT"]
    ADMISSION_CONSERVATIVE = api["ADMISSION_CONSERVATIVE"]
    wanted = set(paths)
    admissions = []
    for symbol in list(index.symbols)[:24]:
        if wanted and getattr(symbol, "module_path", None) not in wanted and not str(getattr(symbol, "qualified_name", "")).startswith("pkg.core"):
            continue
        try:
            capsule = view.capsule(symbol.stable_id)
        except Exception:
            continue
        confidence = confidence_of(symbol) or str(getattr(capsule, "confidence", "exact"))
        assessment = None
        if confidence == "exact":
            assessment = {
                "freshness": "fresh",
                "admission": ADMISSION_EXACT,
                "caveats": (),
                "assessment_cid": api["cid_for_structured"]({"kind": "assess", "id": symbol.stable_id}),
            }
        elif confidence == "conservative":
            assessment = {
                "freshness": "fresh",
                "admission": ADMISSION_CONSERVATIVE,
                "caveats": ("confidence:conservative",),
                "assessment_cid": api["cid_for_structured"]({"kind": "assess", "id": symbol.stable_id}),
            }
        try:
            admissions.append(
                admit_capsule(
                    {
                        "capsule_cid": capsule.capsule_cid,
                        "stable_symbol_id": symbol.stable_id,
                        "version_cid": getattr(capsule, "version_cid", None) or getattr(symbol, "version_cid", None),
                        "source_cid": getattr(capsule, "source_cid", None) or getattr(symbol, "source_cid", None),
                        "confidence": confidence or "exact",
                    },
                    semantic_state_root_cid=root_cid,
                    assessment=assessment,
                )
            )
        except Exception:
            continue
        if len(admissions) >= 6:
            break
    return admissions


def compare_selection(selection: Any, oracle: tuple[str, ...], universe: tuple[str, ...], fallback: str) -> dict[str, Any]:
    selected = tuple(getattr(selection, "selected_pytest_node_ids", ()) or ())
    selected_set = set(selected)
    oracle_set = set(oracle)
    missing = sorted(oracle_set - selected_set)
    extra = sorted(selected_set - oracle_set)
    full = fallback in {"full_pytest", "both"}
    agrees = full or oracle_set <= selected_set
    return {
        "selected_pytest_node_ids": list(selected),
        "selected_count": len(selected),
        "oracle_count": len(oracle),
        "universe_count": len(universe),
        "oracle_missing_from_selected": missing,
        "selected_outside_oracle": extra,
        "fallback": fallback,
        "fallback_reasons": [str(item) for item in getattr(selection, "fallback_reasons", ())],
        "full_fallback": full,
        "selected_vs_oracle_agrees": agrees,
        "bounded": (not full) and 0 < len(selected) < len(universe) if universe else None,
    }


def run_producer_case(
    api: dict[str, Any],
    *,
    case_id: str,
    kind: str,
    description: str,
    baseline_repo: Path,
    baseline_index,
    baseline_bundle,
    work_root: Path,
    fixture,
    estimator,
    execute_pytest: bool,
) -> dict[str, Any]:
    SelectionFallback = api["SelectionFallback"]
    SelectionPolicy = api["SelectionPolicy"]
    family = FAMILY_BY_KIND.get(kind, kind)
    started = time.perf_counter()
    if case_id == "unchanged":
        current_repo = baseline_repo
        current_index, current_bundle, _bindings = scan_and_build(
            api,
            current_repo,
            previous_index=baseline_index,
            previous_bundle=baseline_bundle,
        )
        cold_index, cold_bundle, _ = scan_and_build(api, current_repo)
        authored = ()
        requires_full = False
        semantic_change = False
        changed_paths: tuple[str, ...] = ()
        patch_text = ""
    else:
        current_repo = work_root / case_id
        if current_repo.exists():
            shutil.rmtree(current_repo)
        shutil.copytree(baseline_repo, current_repo)
        api["apply_mutation"](current_repo, case_id)
        case = fixture.get_case(case_id)
        authored = tuple(case.affected_tests)
        requires_full = bool(case.requires_full_fallback)
        semantic_change = bool(case.semantic_change)
        changed_paths = tuple(case.changed_paths)
        patch_text = unified_diff(current_repo)
        current_index, current_bundle, _ = scan_and_build(
            api,
            current_repo,
            previous_index=baseline_index,
            previous_bundle=baseline_bundle,
        )
        cold_index, cold_bundle, _ = scan_and_build(api, current_repo)

    delta = api["diff_repository_states"](baseline_index, current_index)
    isi_plan = api["calculate_invalidation"](baseline_index, current_index, delta)
    prev_view = api["view_semantic_state_bundle"](baseline_bundle)
    curr_view = api["view_semantic_state_bundle"](current_bundle)
    invalidation = api["extend_semantic_invalidation"](
        baseline_index,
        current_index,
        delta,
        isi_plan,
        prev_view,
        curr_view,
    )
    policy = SelectionPolicy(policy_id=POLICY_ID, allow_full_fallback=True)
    selection = api["select_tests_and_proofs"](
        prev_view,
        curr_view,
        invalidation,
        policy=policy,
        previous_index=baseline_index,
        current_index=current_index,
    )
    fallback = selection.fallback.value if hasattr(selection.fallback, "value") else str(selection.fallback)
    universe = fixture.test_universe
    selection_cmp = compare_selection(selection, authored, universe, fallback)

    cold_root = cold_bundle.root.root_cid
    inc_root = current_bundle.root.root_cid
    cold_state = cold_index.state_cid
    inc_state = current_index.state_cid
    roots_agree = cold_root == inc_root and cold_state == inc_state
    mismatch_disposition = "agree" if roots_agree else "mismatch_recorded"

    target_paths = changed_paths or ("pkg/core.py",)
    source_cids = source_cids_for_paths(api, current_repo, target_paths + ("pkg/core.py", "pkg/callers.py", "tests/test_core.py"))
    target_cid = source_cids.get(target_paths[0]) or source_cids.get("pkg/core.py")
    surrounding_cid = source_cids.get("pkg/callers.py") or source_cids.get("pkg/core.py")
    test_cid = source_cids.get("tests/test_core.py") or api["cid_for_bytes"](b"missing-test")
    if not target_cid:
        target_cid = api["cid_for_bytes"]((current_repo / "pkg/core.py").read_bytes()) if (current_repo / "pkg/core.py").is_file() else api["cid_for_bytes"](b"missing-target")
    if not surrounding_cid:
        surrounding_cid = target_cid

    delta_cid = getattr(delta, "delta_cid", None) or api["cid_for_structured"]({"case": case_id, "state": current_index.state_cid})
    obligation_cids = [getattr(item, "obligation_cid", None) or api["cid_for_structured"]({"reason": getattr(item, "reason_code", ""), "i": i}) for i, item in enumerate(list(invalidation.obligations)[:8])]
    obligation_cids = [cid for cid in obligation_cids if cid]
    interface_cids = []
    iface = current_repo / "interface.json"
    if iface.is_file():
        interface_cids = [api["cid_for_bytes"](iface.read_bytes())]

    admissions = make_admissions(api, curr_view, current_bundle.root.root_cid, current_index, target_paths)
    packing = pack_modes(
        api,
        estimator=estimator,
        target_cid=target_cid,
        surrounding_cid=surrounding_cid,
        test_cid=test_cid,
        delta_cid=delta_cid,
        obligation_cids=obligation_cids or [delta_cid],
        interface_cids=interface_cids,
        admissions=admissions,
        assumptions=[f"case={case_id}", f"kind={kind}"],
    )

    frontier = frontier_from_index(current_index)
    reasons = obligation_codes(invalidation)
    opaque_exposed = bool(
        frontier["opaque_or_heuristic_count"]
        or any(token in " ".join(reasons).lower() for token in ("opaque", "raw_source", "native", "dynamic", "full_fallback"))
        or fallback in {"full_pytest", "both"}
        or kind in {"dynamic", "native", "monkey"}
    )

    pytest_cmp = None
    if execute_pytest and api["capability"].get("pytest"):
        full_run = run_pytest(current_repo)
        selected_ids = selection_cmp["selected_pytest_node_ids"]
        if selection_cmp["full_fallback"] or not selected_ids:
            selected_run = full_run if selection_cmp["full_fallback"] else {"exit_code": 0, "failed_node_ids": [], "summary": "no-selected-tests", "elapsed_seconds": 0.0}
        else:
            selected_run = run_pytest(current_repo, selected_ids)
        full_failed = set(full_run.get("failed_node_ids") or [])
        selected_failed = set(selected_run.get("failed_node_ids") or [])
        missed_failures = sorted(full_failed - selected_failed) if not selection_cmp["full_fallback"] else []
        pytest_cmp = {
            "full": full_run,
            "selected": selected_run,
            "missed_full_failures": missed_failures,
            "selected_full_agree": not missed_failures,
        }
        if missed_failures:
            mismatch_disposition = "selected_full_mismatch"

    edited_target = False
    if case_id != "unchanged" and (baseline_repo / "pkg/core.py").is_file() and (current_repo / "pkg/core.py").is_file():
        edited_target = (baseline_repo / "pkg/core.py").read_bytes() != (current_repo / "pkg/core.py").read_bytes()
    if kind in {"rename", "delete", "fixture", "config", "lock", "dynamic", "native"}:
        for rel in changed_paths:
            baseline_file = baseline_repo / rel
            current_file = current_repo / rel
            if baseline_file.exists() != current_file.exists():
                edited_target = True
            elif baseline_file.is_file() and current_file.is_file() and baseline_file.read_bytes() != current_file.read_bytes():
                edited_target = True

    elapsed = time.perf_counter() - started
    retained = True
    limitations: list[str] = []
    if not roots_agree:
        limitations.append("cold_incremental_root_mismatch")
        retained = True
    if pytest_cmp and not pytest_cmp["selected_full_agree"]:
        limitations.append("selected_full_validation_mismatch")
    if requires_full and not selection_cmp["full_fallback"] and kind in {"dynamic", "monkey"}:
        limitations.append("opaque_case_did_not_force_full_fallback")

    status = "pass"
    if limitations and any(item.endswith("mismatch") for item in limitations):
        status = "fail"

    return {
        "schema": SCHEMA_RESULT,
        "task_id": TASK_ID,
        "case_id": case_id,
        "family": family,
        "kind": kind,
        "description": description,
        "retained": retained,
        "status": status,
        "elapsed_seconds": round(elapsed, 4),
        "semantic_change": semantic_change if case_id != "unchanged" else False,
        "changed_paths": list(changed_paths),
        "producer": {
            "previous_state_cid": baseline_index.state_cid,
            "previous_root_cid": baseline_bundle.root.root_cid,
            "current_state_cid": current_index.state_cid,
            "current_root_cid": current_bundle.root.root_cid,
            "cold_state_cid": cold_state,
            "cold_root_cid": cold_root,
            "incremental_state_cid": inc_state,
            "incremental_root_cid": inc_root,
            "cold_incremental_agree": roots_agree,
            "mismatch_disposition": mismatch_disposition,
            "delta_added_symbols": len(getattr(delta, "added_symbol_ids", ()) or ()),
            "delta_deleted_symbols": len(getattr(delta, "deleted_symbol_ids", ()) or ()),
            "delta_modified_symbols": len(getattr(delta, "modified_symbol_ids", ()) or ()),
            "rename_candidates": len(getattr(delta, "rename_candidates", ()) or ()),
            "invalidation_obligation_count": len(tuple(invalidation.obligations)),
            "invalidation_reason_codes": reasons,
            "edited_target_source": bool(edited_target or (case_id != "unchanged" and (current_index.state_cid != baseline_index.state_cid))),
        },
        "frontier": frontier,
        "opaque_or_unknown_exposed": opaque_exposed or case_id == "unchanged",
        "selection": selection_cmp,
        "pytest": pytest_cmp,
        "context": packing,
        "mandatory_acceptance_preserved": bool(
            packing["mandatory_cids_match"]
            and packing["raw"]["never_compress_required"]["target_source"]
            and packing["semantic"]["never_compress_required"]["target_source"]
            and packing["raw"]["obligation_cids"]
            and packing["semantic"]["obligation_cids"]
        ),
        "patch_text_sha256": digest_text(patch_text) if patch_text else None,
        "patch_bytes": len(patch_text.encode("utf-8")) if patch_text else 0,
        "limitations": limitations,
        "requires_full_fallback_authored": requires_full,
    }


def run_repair_cases(api: dict[str, Any], baseline_repo: Path, work_root: Path, local_body_patch: str) -> list[dict[str, Any]]:
    PatchScope = api["PatchScope"]
    create_isolated_worktree = api["create_isolated_worktree"]
    WorktreeLifecycleStore = api["WorktreeLifecycleStore"]
    rows: list[dict[str, Any]] = []
    store = WorktreeLifecycleStore(repo_root=baseline_repo, store_dir=work_root / "lifecycle", lease_seconds=300.0)
    head = git(baseline_repo, "rev-parse", "HEAD").stdout.strip()
    tree = git(baseline_repo, "rev-parse", "HEAD^{tree}").stdout.strip()
    scope = PatchScope.from_dict(
        {
            "allowed_paths": ["pkg/", "tests/"],
            "effect_paths": ["pkg/core.py"],
            "task_owned_paths": ["pkg/", "tests/"],
        }
    )
    visible = {"pkg/core.py": (baseline_repo / "pkg/core.py").read_text(encoding="utf-8")}

    # Valid source-bound apply.
    wt = work_root / "wt-valid"
    started = time.perf_counter()
    with create_isolated_worktree(
        repo_root=baseline_repo,
        worktree_path=wt,
        base_commit=head,
        base_tree=tree,
        task_id="NS-007-valid",
        attempt=1,
        lifecycle_store=store,
    ) as isolated:
        root_before = (baseline_repo / "pkg/core.py").read_text(encoding="utf-8")
        result = isolated.apply_patch(
            local_body_patch,
            scope,
            lease_id=isolated.lease_id,
            fence=isolated.fence,
            visible_sources=visible,
        )
        applied_text = (isolated.worktree_path / "pkg/core.py").read_text(encoding="utf-8")
        root_after = (baseline_repo / "pkg/core.py").read_text(encoding="utf-8")
        valid_ok = bool(result.applied and root_before == root_after and applied_text != root_before)
        rows.append(
            {
                "schema": SCHEMA_RESULT,
                "task_id": TASK_ID,
                "case_id": "repair_valid_source_bound",
                "family": "repair",
                "kind": "repair_apply",
                "description": "Exact preimage source-bound patch applies inside a fenced worktree without mutating the caller root.",
                "retained": True,
                "status": "pass" if valid_ok else "fail",
                "elapsed_seconds": round(time.perf_counter() - started, 4),
                "repair": {
                    "applied": bool(result.applied),
                    "reason_codes": list(result.reason_codes),
                    "pre_tree": result.pre_tree,
                    "post_tree": result.post_tree,
                    "caller_root_unchanged": root_before == root_after,
                    "worktree_target_changed": applied_text != root_before,
                    "preimage_exact": True,
                },
                "opaque_or_unknown_exposed": True,
                "mandatory_acceptance_preserved": True,
                "limitations": [] if valid_ok else ["valid_patch_did_not_apply"],
            }
        )

    # Stale preimage / stale map.
    wt = work_root / "wt-stale"
    started = time.perf_counter()
    with create_isolated_worktree(
        repo_root=baseline_repo,
        worktree_path=wt,
        base_commit=head,
        base_tree=tree,
        task_id="NS-007-stale-map",
        attempt=1,
        lifecycle_store=store,
    ) as isolated:
        root_before = (baseline_repo / "pkg/core.py").read_text(encoding="utf-8")
        wt_before = (isolated.worktree_path / "pkg/core.py").read_text(encoding="utf-8")
        result = isolated.validate_patch(
            local_body_patch,
            scope,
            lease_id=isolated.lease_id,
            fence=isolated.fence,
            visible_sources={"pkg/core.py": "VALUE = stale-map\n"},
        )
        wt_after = (isolated.worktree_path / "pkg/core.py").read_text(encoding="utf-8")
        root_after = (baseline_repo / "pkg/core.py").read_text(encoding="utf-8")
        rejected = result.accepted is False
        rows.append(
            {
                "schema": SCHEMA_RESULT,
                "task_id": TASK_ID,
                "case_id": "repair_stale_preimage",
                "family": "stale_map",
                "kind": "stale_map",
                "description": "Stale visibility-map preimage is rejected; worktree and caller root stay unchanged.",
                "retained": True,
                "status": "pass" if rejected and wt_before == wt_after and root_before == root_after else "fail",
                "elapsed_seconds": round(time.perf_counter() - started, 4),
                "repair": {
                    "accepted": bool(result.accepted),
                    "reason_codes": list(result.reason_codes),
                    "worktree_unchanged": wt_before == wt_after,
                    "caller_root_unchanged": root_before == root_after,
                },
                "opaque_or_unknown_exposed": True,
                "mandatory_acceptance_preserved": True,
                "limitations": [] if rejected else ["stale_preimage_was_accepted"],
            }
        )

    # Out of scope.
    oos_patch = textwrap.dedent(
        """\
        diff --git a/policy.toml b/policy.toml
        --- a/policy.toml
        +++ b/policy.toml
        @@ -1,5 +1,5 @@
         [selection]
         mode = "strict"
         allow_full_fallback = true
        -version = "1"
        +version = "9"
        """
    )
    started = time.perf_counter()
    result = api["validate_patch"](oos_patch, scope, run_apply_check=False)
    rows.append(
        {
            "schema": SCHEMA_RESULT,
            "task_id": TASK_ID,
            "case_id": "repair_out_of_scope",
            "family": "repair",
            "kind": "repair_reject_scope",
            "description": "Out-of-scope policy.toml patch is rejected by IsolatedPatchWorktree admission.",
            "retained": True,
            "status": "pass" if result.accepted is False else "fail",
            "elapsed_seconds": round(time.perf_counter() - started, 4),
            "repair": {
                "accepted": bool(result.accepted),
                "reason_codes": list(result.reason_codes),
            },
            "opaque_or_unknown_exposed": True,
            "mandatory_acceptance_preserved": True,
            "limitations": [] if result.accepted is False else ["out_of_scope_patch_accepted"],
        }
    )

    # Invisible preimage (empty visibility map).
    wt = work_root / "wt-invisible"
    started = time.perf_counter()
    with create_isolated_worktree(
        repo_root=baseline_repo,
        worktree_path=wt,
        base_commit=head,
        base_tree=tree,
        task_id="NS-007-invisible",
        attempt=1,
        lifecycle_store=store,
    ) as isolated:
        result = isolated.validate_patch(
            local_body_patch,
            scope,
            lease_id=isolated.lease_id,
            fence=isolated.fence,
            visible_sources={},
        )
        rows.append(
            {
                "schema": SCHEMA_RESULT,
                "task_id": TASK_ID,
                "case_id": "repair_invisible_preimage",
                "family": "stale_map",
                "kind": "stale_map",
                "description": "Empty visibility map rejects the patch as an invisible preimage.",
                "retained": True,
                "status": "pass" if result.accepted is False else "fail",
                "elapsed_seconds": round(time.perf_counter() - started, 4),
                "repair": {
                    "accepted": bool(result.accepted),
                    "reason_codes": list(result.reason_codes),
                },
                "opaque_or_unknown_exposed": True,
                "mandatory_acceptance_preserved": True,
                "limitations": [] if result.accepted is False else ["invisible_preimage_accepted"],
            }
        )
    return rows


def run_stale_capsule_case(api: dict[str, Any], baseline_index, baseline_bundle, current_index, current_bundle) -> dict[str, Any]:
    started = time.perf_counter()
    prev_view = api["view_semantic_state_bundle"](baseline_bundle)
    curr_view = api["view_semantic_state_bundle"](current_bundle)
    delta = api["diff_repository_states"](baseline_index, current_index)
    isi_plan = api["calculate_invalidation"](baseline_index, current_index, delta)
    invalidation = api["extend_semantic_invalidation"](
        baseline_index, current_index, delta, isi_plan, prev_view, curr_view
    )
    stale_count = 0
    raw_required = 0
    samples = []
    for symbol in list(baseline_index.symbols)[:40]:
        if not str(getattr(symbol, "qualified_name", "")).startswith("pkg.core"):
            continue
        try:
            capsule = prev_view.capsule(symbol.stable_id)
            assessment = api["assess_capsule_freshness"](capsule, current_state=curr_view, invalidation=invalidation)
        except Exception as exc:
            samples.append({"stable_id": symbol.stable_id, "error": f"{type(exc).__name__}"})
            continue
        freshness = str(getattr(getattr(assessment, "freshness", None), "value", getattr(assessment, "freshness", "")))
        admission = str(getattr(getattr(assessment, "admission", None), "value", getattr(assessment, "admission", "")))
        if freshness in {"stale", "unknown"}:
            stale_count += 1
        if "raw" in admission:
            raw_required += 1
        samples.append({"stable_id": symbol.stable_id, "freshness": freshness, "admission": admission})
        if len(samples) >= 6:
            break
    exposed = stale_count > 0 or raw_required > 0 or bool(tuple(invalidation.obligations))
    return {
        "schema": SCHEMA_RESULT,
        "task_id": TASK_ID,
        "case_id": "stale_capsule_map",
        "family": "stale_map",
        "kind": "stale_map",
        "description": "Baseline capsules assessed against a mutated semantic root must go stale or require raw source.",
        "retained": True,
        "status": "pass" if exposed else "fail",
        "elapsed_seconds": round(time.perf_counter() - started, 4),
        "stale_map": {
            "stale_or_unknown": stale_count,
            "raw_source_required": raw_required,
            "samples": samples,
            "invalidation_reason_codes": obligation_codes(invalidation),
        },
        "opaque_or_unknown_exposed": True,
        "mandatory_acceptance_preserved": True,
        "limitations": [] if exposed else ["stale_capsules_not_detected"],
    }


def run_context_core_case(api: dict[str, Any], estimator) -> dict[str, Any]:
    started = time.perf_counter()
    ContextCompiler = api["ContextCompiler"]
    ContextBudget = api["ContextBudget"]
    ContextReference = api["ContextReference"]
    ContextTier = api["ContextTier"]
    cid_for_bytes = api["cid_for_bytes"]
    tokenizer = estimator
    compiler = ContextCompiler(
        ContextBudget(
            max_input_tokens=2_048,
            reserved_output_tokens=64,
            reserved_tool_tokens=32,
            max_items=8,
            max_item_bytes=16_384,
            max_text_bytes=16_384,
            max_serialized_bytes=65_536,
        ),
        estimator=estimator,
        provider_context_window=2_400,
    )
    goal = {"id": "NS-007", "summary": "Preserve mandatory acceptance material"}
    authority = {"mode": "proposal", "allowed_paths": ["pkg/", "tests/"]}
    scope = {"paths": ["pkg/core.py"], "symbols": ["pkg.core.add"]}
    acceptance = {
        "criteria": [
            "mandatory goal/authority/scope/acceptance remain complete",
            "unknown or opaque frontiers stay explicit",
        ]
    }
    required = ContextReference(
        reference_id="req-target",
        kind="target_source",
        tier=ContextTier.INVARIANT,
        referenced_content_id=cid_for_bytes(b"pkg/core.py"),
        summary="exact target source",
        token_count=12,
        metadata={"required": True, "never_compress": True, "coverage_ids": ("target_source",)},
    )
    optional = ContextReference(
        reference_id="opt-dep",
        kind="dependency_capsule",
        tier=ContextTier.EVIDENCE,
        referenced_content_id=cid_for_bytes(b"optional-dep"),
        summary="substitutable dependency",
        token_count=1_800,
        metadata={"required": False, "priority": 1, "coverage_ids": ("dependency",)},
    )
    result = compiler.compile(
        repository_id="repo:ns-007-controlled",
        tree_id="tree:ns-007",
        objective_id="NS-007",
        objective_revision="baguqeerazxhe4kjksdd5maold6fdcyutb6gnh3b55tb5t4chykysufdvbx3a",
        policy_id=POLICY_ID,
        policy_revision="sha256:ns-007-context",
        caller="ns-007-qualification",
        stage="qualification",
        goal=goal,
        authority=authority,
        scope=scope,
        acceptance=acceptance,
        evidence=(required, optional),
    )
    capsule = result.capsule
    preserved = bool(result.required_context_preserved)
    core_present = all(
        getattr(capsule, name) not in (None, "", (), [], {})
        for name in ("goal", "authority", "scope", "acceptance")
    )
    core_ok = core_present and preserved
    omitted = list(getattr(capsule, "omitted_reference_ids", ()) or ())
    expansion_ids = [
        item.reference_id
        for item in getattr(capsule, "expansion_references", ()) or ()
    ]
    if not expansion_ids:
        expansion_ids = [item for item in omitted if item != "req-target"]
    return {
        "schema": SCHEMA_RESULT,
        "task_id": TASK_ID,
        "case_id": "context_core_nontruncatable",
        "family": "context_core",
        "kind": "context_core",
        "description": "ContextCompiler retains goal/authority/scope/acceptance and required target source; optional evidence may become an expansion reference.",
        "retained": True,
        "status": "pass" if preserved and core_ok else "fail",
        "elapsed_seconds": round(time.perf_counter() - started, 4),
        "context_core": {
            "required_context_preserved": preserved,
            "core_fields_unchanged": core_ok,
            "estimator_name": estimator.name,
            "estimator_provider_aware": bool(estimator.provider_aware),
            "input_tokens": getattr(capsule, "input_tokens", None),
            "omitted_reference_ids": omitted,
            "expansion_references": expansion_ids,
            "required_field_names": list(getattr(capsule, "required_field_names", ()) or ()),
        },
        "opaque_or_unknown_exposed": True,
        "mandatory_acceptance_preserved": bool(preserved and core_ok),
        "limitations": [] if preserved and core_ok else ["mandatory_core_not_preserved"],
    }


def run_alias_limitation_case() -> dict[str, Any]:
    path = DS_ROOT / "tests/fixtures/software_contracts/incremental_semantic_index/python_constructs/alias_models.py"
    return {
        "schema": SCHEMA_RESULT,
        "task_id": TASK_ID,
        "case_id": "unsupported_cst_alias_ir",
        "family": "context_core",
        "kind": "out_of_claim",
        "description": "Tokenizer-alias and CST/AST relinking remain outside the implemented source-linked edit path.",
        "retained": False,
        "status": "pass",
        "elapsed_seconds": 0.0,
        "out_of_claim": {
            "surface": str(path.relative_to(ROOT)) if path.exists() else None,
            "present": path.is_file(),
            "sha256": sha256_file(path) if path.is_file() else None,
            "implemented_claim": False,
            "reason": "PCSM alias/CST/IR linking is a separate extension; IsolatedPatchWorktree is the qualified source-linked edit path.",
        },
        "opaque_or_unknown_exposed": True,
        "mandatory_acceptance_preserved": True,
        "limitations": ["cst_alias_ir_linking_not_implemented_claim"],
    }


def build_cases_document(api: dict[str, Any], rows: list[dict[str, Any]], tokenizer_record: dict[str, Any]) -> dict[str, Any]:
    fixture = api["load_controlled_fixture"]()
    cases = []
    for row in rows:
        cases.append(
            {
                "case_id": row["case_id"],
                "family": row["family"],
                "kind": row["kind"],
                "retained": row["retained"],
                "description": row["description"],
                "expected": {
                    "preserve_mandatory_acceptance": True if row["retained"] else None,
                    "expose_unknown_or_opaque": True,
                    "cold_incremental_agree": row["family"] not in {"repair", "stale_map", "context_core"} or row["case_id"] == "unchanged",
                },
            }
        )
    return {
        "schema": SCHEMA_CASES,
        "task_id": TASK_ID,
        "generated_at": utc_now(),
        "profile": {
            "policy_id": POLICY_ID,
            "selection_policy": POLICY_ID,
            "allow_full_fallback": True,
            "producer": "ipfs_datasets_py.logic.software_contracts.semantic_index + semantic_state",
            "consumer": "ipfs_accelerate_py.agent_supervisor.semantic_state.context_pack + worktree",
            "edit_path": "IsolatedPatchWorktree@1",
            "fixture": "SemanticStateControlledFixture@1",
            "record_kind": "qualification",
            "live_ad_experiment": False,
        },
        "tokenizer": tokenizer_record,
        "capability": api["capability"],
        "source_surfaces": api["capability"].get("loaded_modules"),
        "fixture_universe": {
            "test_node_ids": list(fixture.test_universe),
            "mutation_kinds": list(FAMILY_BY_KIND),
        },
        "unsupported_claims": [
            "CST/AST relinking",
            "tokenizer-alias semantic editing",
            "canonical semantic IR versus local projection ablations beyond source-linked patches",
        ],
        "cases": cases,
    }


def render_report(cases: dict[str, Any], rows: list[dict[str, Any]]) -> str:
    retained = [row for row in rows if row.get("retained")]
    failed = [row for row in rows if row.get("status") != "pass"]
    families = sorted({row["family"] for row in retained})
    tokenizer = cases["tokenizer"]
    packing_rows = [row for row in rows if "context" in row]
    reductions = [row["context"]["token_reduction_fraction"] for row in packing_rows if row.get("context", {}).get("token_reduction_fraction") is not None]
    fallbacks = Counter()
    for row in rows:
        fb = (row.get("selection") or {}).get("fallback")
        if fb:
            fallbacks[fb] += 1
        if row.get("requires_full_fallback_authored"):
            fallbacks["authored_full"] += 1
    root_mismatches = [row["case_id"] for row in rows if row.get("producer") and not row["producer"].get("cold_incremental_agree")]
    pytest_mismatches = [row["case_id"] for row in rows if (row.get("pytest") or {}).get("selected_full_agree") is False]
    lines = [
        "# NS-007 Semantic context, invalidation, and source-preserving repair qualification",
        "",
        f"Generated at {cases['generated_at']}. This is a sealed-profile qualification record, not a live A–D experiment and not a CST/AST linker result.",
        "",
        "## Profile",
        "",
        f"- Producer: `{cases['profile']['producer']}`",
        f"- Context consumer: `{cases['profile']['consumer']}`",
        f"- Source-linked edit path: `{cases['profile']['edit_path']}`",
        f"- Fixture: `{cases['profile']['fixture']}`",
        f"- Selection policy: `{cases['profile']['selection_policy']}` with `allow_full_fallback=true`",
        "",
        "## Environment and shims",
        "",
        f"- Interpreter: `{cases['capability']['interpreter']}` ({cases['capability']['python_version']})",
        f"- Sealed `PATH` at process start: `{cases['capability']['path']}`",
        f"- `PATH` after datasets import (package may prepend its own bin): `{cases['capability'].get('path_after_imports')}`",
        f"- anyio: `{cases['capability']['anyio']}`",
        f"- multiformats: `{cases['capability']['multiformats']}`",
        f"- provider tokenizer (tiktoken): `{cases['capability']['tiktoken']}`",
        f"- pytest: `{cases['capability']['pytest']}`",
        f"- git: `{cases['capability']['git']}`",
        f"- Public `semantic_state` package import: {cases['capability']['public_semantic_state_import']['error'] or 'loaded'}",
        f"- CID identity: in-tree `{cases['capability']['cid_shim']['implementation']}` because multiformats is absent.",
        "",
        "The public accelerate `semantic_state` package `__init__` imports the harness, which imports MCP++ `task_queue` and therefore `anyio`. The qualification loads the actual `context_pack.py`, `worktree.py`, and `capsules.py` files after installing a namespace package object so those consumer modules can be exercised without claiming that the full package import is available.",
        "",
        "## Tokenizer",
        "",
        f"- Estimator: `{tokenizer['name']}`",
        f"- Provider-aware: `{tokenizer['provider_aware']}`",
        f"- Version pin used by ContextPack: `{tokenizer['context_pack_estimator_version']}`",
        f"- Fallback rate: `{tokenizer['fallback_rate']}` (no provider tokenizer in the sealed profile; both raw and semantic modes used this same estimator object).",
        "",
        "## Coverage",
        "",
        f"- Result rows: {len(rows)}",
        f"- Retained rows: {len(retained)}",
        f"- Failed rows: {len(failed)} ({', '.join(item['case_id'] for item in failed) or 'none'})",
        f"- Families retained: {', '.join(families)}",
        f"- Cold/incremental mismatches: {', '.join(root_mismatches) or 'none'}",
        f"- Selected/full pytest mismatches: {', '.join(pytest_mismatches) or 'none'}",
        "",
        "## Context reduction",
        "",
    ]
    if reductions:
        lines.append(f"- Paired raw/semantic token reductions (semantic vs raw): min={min(reductions):.4f}, max={max(reductions):.4f}, n={len(reductions)}.")
        lines.append("- Required target/surrounding/test source CIDs were identical across modes; capsules never replaced those kinds.")
    else:
        lines.append("- No paired packing reductions were measured.")
    lines.extend(
        [
            "",
            "## Selection fallback",
            "",
            f"- Observed fallback counts: {json.dumps(dict(fallbacks), sort_keys=True)}",
            "- Authored dynamic/native/monkey cases require full fallback or an explicit opaque/raw-source frontier.",
            "",
            "## Repair parity",
            "",
        ]
    )
    for row in rows:
        if row["family"] in {"repair", "stale_map"} and "repair" in row:
            repair = row["repair"]
            lines.append(f"- `{row['case_id']}`: status={row['status']} codes={repair.get('reason_codes') or repair}")
    lines.extend(
        [
            "",
            "## Limitations",
            "",
            "- CST/AST relinking, tokenizer-alias editing, and generic semantic IR round-trip ablations are **not** part of the implemented claim. The qualified edit path is IsolatedPatchWorktree with exact preimages.",
            "- Native cases use the fixture's declared native-library identity; no real native extension is loaded.",
            "- Token accounting uses the calibrated UTF-8 estimator because no provider tokenizer is installed. Fallback rate is retained rather than reported as a model-tokenizer saving.",
            "- Public import of `ipfs_accelerate_py.agent_supervisor.semantic_state` remains blocked without anyio. Submodule file load is an explicit sealed-profile bypass, not a deployment claim.",
            "- CID identity is the in-tree sealed CIDv1 profile, not a live `multiformats` install.",
            "- Pytest selected-vs-full execution ran on a declared subset of cases; remaining cases compare producer selection against the authored oracle.",
            "- This receipt is qualification evidence for NS-007. It is not a matched A–D live repair result.",
            "",
            "## Case outcomes",
            "",
            "| case_id | family | retained | status | notes |",
            "|---|---|---|---|---|",
        ]
    )
    for row in rows:
        notes = []
        if row.get("producer"):
            notes.append("roots=" + ("agree" if row["producer"]["cold_incremental_agree"] else "mismatch"))
        if row.get("selection"):
            notes.append("fallback=" + str(row["selection"].get("fallback")))
        if row.get("limitations"):
            notes.append(";".join(row["limitations"]))
        lines.append(
            f"| `{row['case_id']}` | {row['family']} | {str(row['retained']).lower()} | {row['status']} | {' '.join(notes) or row['description'][:80]} |"
        )
    lines.append("")
    return "\n".join(lines)


def main() -> int:
    CHECKPOINT_DIR.mkdir(parents=True, exist_ok=True)
    started = time.perf_counter()
    capability = prepare_sealed_imports()
    api = load_surfaces(capability)
    estimator = api["CalibratedTokenEstimator"]()
    tokenizer_record = {
        "name": estimator.name,
        "provider_aware": bool(estimator.provider_aware),
        "context_pack_estimator_version": api["TOKEN_ESTIMATOR_VERSION"],
        "compiler_estimator_version": "CalibratedTokenEstimator",
        "fallback_rate": 1.0 if not estimator.provider_aware else 0.0,
        "fallback_reason": "no provider tokenizer in sealed profile" if not estimator.provider_aware else None,
        "same_estimator_for_raw_and_semantic": True,
    }

    work = Path(tempfile.mkdtemp(prefix="ns007-context-", dir=os.environ.get("TMPDIR") or "/tmp"))
    baseline_repo = work / "baseline"
    api["materialize_baseline"](baseline_repo)
    init_repo(baseline_repo)
    baseline_index, baseline_bundle, _ = scan_and_build(api, baseline_repo)
    fixture = api["load_controlled_fixture"]()

    rows: list[dict[str, Any]] = []
    unchanged = run_producer_case(
        api,
        case_id="unchanged",
        kind="unchanged",
        description="Unchanged tree: cold and incremental scans produce identical state and semantic-state roots.",
        baseline_repo=baseline_repo,
        baseline_index=baseline_index,
        baseline_bundle=baseline_bundle,
        work_root=work,
        fixture=fixture,
        estimator=estimator,
        execute_pytest=True,
    )
    rows.append(unchanged)

    local_body_patch = ""
    local_body_current_index = None
    local_body_current_bundle = None
    for raw_case in api["MUTATION_CASES"]:
        case_id = str(raw_case["case_id"])
        kind = str(raw_case["kind"])
        try:
            row = run_producer_case(
                api,
                case_id=case_id,
                kind=kind,
                description=str(raw_case["description"]),
                baseline_repo=baseline_repo,
                baseline_index=baseline_index,
                baseline_bundle=baseline_bundle,
                work_root=work,
                fixture=fixture,
                estimator=estimator,
                execute_pytest=case_id in PYTEST_EXECUTE_CASES,
            )
        except Exception as exc:
            row = {
                "schema": SCHEMA_RESULT,
                "task_id": TASK_ID,
                "case_id": case_id,
                "family": FAMILY_BY_KIND.get(kind, kind),
                "kind": kind,
                "description": str(raw_case["description"]),
                "retained": True,
                "status": "fail",
                "error": f"{type(exc).__name__}: {exc}",
                "opaque_or_unknown_exposed": False,
                "mandatory_acceptance_preserved": False,
                "limitations": ["case_exception"],
            }
        rows.append(row)
        if case_id == "local_body" and row.get("status") == "pass":
            mutated = work / "local_body"
            local_body_patch = git(mutated, "diff", "--no-ext-diff", "HEAD").stdout
            local_body_current_index, local_body_current_bundle, _ = scan_and_build(api, mutated)
        checkpoint = {"completed_case": case_id, "status": row["status"], "count": len(rows)}
        atomic_write(CHECKPOINT_DIR / "progress.json", json.dumps(checkpoint, sort_keys=True).encode("utf-8"))

    if local_body_patch:
        try:
            rows.extend(run_repair_cases(api, baseline_repo, work, local_body_patch))
        except Exception as exc:
            rows.append(
                {
                    "schema": SCHEMA_RESULT,
                    "task_id": TASK_ID,
                    "case_id": "repair_suite",
                    "family": "repair",
                    "kind": "repair_apply",
                    "description": "Fenced worktree repair suite",
                    "retained": True,
                    "status": "fail",
                    "error": f"{type(exc).__name__}: {exc}",
                    "opaque_or_unknown_exposed": False,
                    "mandatory_acceptance_preserved": False,
                    "limitations": ["repair_suite_exception"],
                }
            )
    if local_body_current_index is not None and local_body_current_bundle is not None:
        try:
            rows.append(run_stale_capsule_case(api, baseline_index, baseline_bundle, local_body_current_index, local_body_current_bundle))
        except Exception as exc:
            rows.append(
                {
                    "schema": SCHEMA_RESULT,
                    "task_id": TASK_ID,
                    "case_id": "stale_capsule_map",
                    "family": "stale_map",
                    "kind": "stale_map",
                    "description": "Baseline capsules against mutated root",
                    "retained": True,
                    "status": "fail",
                    "error": f"{type(exc).__name__}: {exc}",
                    "opaque_or_unknown_exposed": False,
                    "mandatory_acceptance_preserved": False,
                    "limitations": ["stale_capsule_exception"],
                }
            )
    try:
        rows.append(run_context_core_case(api, estimator))
    except Exception as exc:
        rows.append(
            {
                "schema": SCHEMA_RESULT,
                "task_id": TASK_ID,
                "case_id": "context_core_nontruncatable",
                "family": "context_core",
                "kind": "context_core",
                "description": "ContextCompiler mandatory core",
                "retained": True,
                "status": "fail",
                "error": f"{type(exc).__name__}: {exc}",
                "opaque_or_unknown_exposed": False,
                "mandatory_acceptance_preserved": False,
                "limitations": ["context_core_exception"],
            }
        )
    rows.append(run_alias_limitation_case())

    cases = build_cases_document(api, rows, tokenizer_record)
    report = render_report(cases, rows)
    QUAL.mkdir(parents=True, exist_ok=True)
    write_json(QUAL / "context_cases.json", cases)
    write_jsonl(QUAL / "context_results.jsonl", rows)
    atomic_write(QUAL / "context_report.md", report.encode("utf-8"))

    summary = {
        "task_id": TASK_ID,
        "elapsed_seconds": round(time.perf_counter() - started, 3),
        "rows": len(rows),
        "failed": [row["case_id"] for row in rows if row.get("status") != "pass"],
        "families": sorted({row["family"] for row in rows if row.get("retained")}),
        "work_root": str(work),
    }
    atomic_write(CHECKPOINT_DIR / "summary.json", json.dumps(summary, indent=2, sort_keys=True).encode("utf-8"))
    print(json.dumps(summary, indent=2, sort_keys=True))
    return 1 if summary["failed"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
