#!/usr/bin/env python3
"""Paired A-D comparison runner for the neurosymbolic supervision core (NS-026/NS-027).

The runner is confined to this paper worktree. It never edits protected
acceptance oracles, never relabels a simulated observation as production,
and never completes a live historical repair without an admitted production
dispatch plus independent cold scoring. Development stubs remain labeled
stubs. Actual development dispatch uses the frozen NS-026 amendment and
`production_gateway.py`. NS-027 removed unsupported retained-byte reuse:
unless a later admitted reuse amendment sets qualified_reuse, every arm
executes full cold without reuse credit.
"""

from __future__ import annotations

import argparse
import ast
import hashlib
import importlib.util
import json
import os
import resource
import shutil
import subprocess
import sys
import tempfile
import threading
import time
import traceback
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping

SCHEMA_WRAPPER = "paper-ns-runner-attempt/v1"
SCHEMA_MEASUREMENT = "paper-ns-attempt-measurement/v1"
RUNNER_INTERFACE = "NSPairedRunner@1"
PROTOCOL_ID = "ns-core-v1"
HIDDEN_MARKERS = (
    "receipts/snapshots/NS-005/scorer_only",
    "scorer_only/oracles",
    "fail_to_pass",
    "reference_patch",
    "/.git/",
    "git/objects",
)
TERMINAL_STATES = (
    "solved",
    "unsolved",
    "rejected",
    "abstained",
    "timed_out",
    "unavailable",
    "cancelled",
    "missing",
)
PATH_CLASSES = ("production", "development", "simulated")
MAIN_ARMS = ("A", "B", "C", "D")
ALL_ARMS = MAIN_ARMS + ("C-no-route", "C-no-reuse")
CACHE_PROFILES = ("local_cold", "local_warm", "not_applicable")
RECORD_KINDS = (
    "development",
    "pilot",
    "final",
    "boundary_qualification",
    "sealer_replay",
    "schema_validation_fixture",
)
MEASUREMENT_KEYS = (
    "input_tokens",
    "output_tokens",
    "cached_input_tokens",
    "reasoning_tokens",
    "provider_charge",
    "host_cpu_seconds",
    "remote_gpu_seconds",
    "peak_aggregate_memory_bytes",
    "scratch_bytes",
    "retained_storage_bytes",
    "bytes_read",
    "bytes_written",
    "active_elapsed_seconds",
    "queue_wait_seconds",
    "human_wait_seconds",
    "human_active_seconds",
    "independent_scoring_cpu_seconds",
    "independent_scoring_elapsed_seconds",
    "prime_cpu_seconds",
    "prime_elapsed_seconds",
)
STAGE_NAMES = (
    "index_context",
    "provider",
    "fixture_setup",
    "fixture_call",
    "fixture_teardown",
    "proof_generate",
    "proof_verify",
    "persist_seal",
    "publication",
    "retry_recovery",
    "cold_scoring",
    "warm_prime",
)
PAPER_REL = Path("papers/completion/neurosymbolic_supervision")
DEFAULT_BUDGETS = {
    "request_serialized_bytes_max": 65536,
    "admitted_patch_bytes_max": 16384,
    "provider_wall_seconds_max": 180,
    "active_unit_wall_seconds_max": 300,
    "aggregate_unit_host_cpu_seconds_max": 240,
    "independent_cold_scoring_wall_seconds_max": 120,
    "scratch_bytes_per_unit": 2147483648,
    "aggregate_memory_bytes": 2147483648,
    "proposal_effects_per_unit": 1,
    "pre_final_boundary_provider_effects_reserved": 64,
}

_BUGGY_ADD = "def add(a, b):\n    return a\n"
_FIXED_ADD = "def add(a, b):\n    return a + b\n"
_WRONG_ADD = "def add(a, b):\n    return a - b\n"
_VISIBLE_TEST = (
    "from pkg.core import add\n"
    "def test_visible_callable():\n"
    "    assert callable(add)\n"
)
_HIDDEN_TEST = (
    "from pkg.core import add\n"
    "def test_hidden_add():\n"
    "    assert add(1, 2) == 3\n"
    "    assert add(-1, 1) == 0\n"
)
_INIT = ""
_SOLVED_PATCH = (
    "diff --git a/pkg/core.py b/pkg/core.py\n"
    "--- a/pkg/core.py\n"
    "+++ b/pkg/core.py\n"
    "@@ -1,2 +1,2 @@\n"
    " def add(a, b):\n"
    "-    return a\n"
    "+    return a + b\n"
)

DEV_TASKS: dict[str, dict[str, Any]] = {
    "ns-dev-boundary-add": {
        "task_id": "ns-dev-boundary-add",
        "family_id": "ns-dev:boundary-add",
        "role": "boundary_qualification",
        "split": "development",
        "live_repair_admitted": False,
        "counts_as_live_repair": False,
        "language": "python",
        "issue": {
            "title": "NS-006 development fixture: restore integer addition",
            "specification": (
                "pkg.core.add currently returns the left operand. Restore "
                "a + b. Do not edit tests or hidden oracles."
            ),
        },
        "acceptance": {
            "independent": True,
            "hidden_from_proposal": True,
            "oracle_id": "oracle:ns-dev-boundary-add",
            "criteria": "Hidden tests require add(1,2)==3 on the patched tree.",
        },
        "source_snapshot": {
            "kind": "embedded_development_fixture",
            "snapshot_sha256": None,
            "admitted_paths": ["pkg/__init__.py", "pkg/core.py", "tests/test_visible.py"],
        },
        "files": {
            "pkg/__init__.py": _INIT,
            "pkg/core.py": _BUGGY_ADD,
            "tests/test_visible.py": _VISIBLE_TEST,
        },
        "hidden_tests": {"tests/test_hidden.py": _HIDDEN_TEST},
        "allowed_paths": ["pkg/core.py"],
    }
}


class RunnerError(Exception):
    def __init__(self, message: str, *, terminal: str = "unavailable") -> None:
        super().__init__(message)
        self.terminal = terminal


class CrashAfter(Exception):
    """Test-only interruption after durable reservation or provider receipt."""


def utcnow() -> str:
    return datetime.now(timezone.utc).isoformat()


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_text(text: str) -> str:
    return sha256_bytes(text.encode("utf-8"))


def sha256_file(path: Path) -> str:
    return sha256_bytes(path.read_bytes())


def sha256_json(obj: Any) -> str:
    return sha256_bytes(canonical_dumps(obj).encode("utf-8"))


def canonical_dumps(obj: Any) -> str:
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=True)


def atomic_write(path: Path, obj: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = obj if isinstance(obj, str) else canonical_dumps(obj) + "\n"
    tmp = path.with_name(path.name + ".tmp")
    tmp.write_text(payload, encoding="utf-8")
    os.replace(tmp, path)


def cpu_seconds() -> float:
    usage = resource.getrusage(resource.RUSAGE_SELF)
    child = resource.getrusage(resource.RUSAGE_CHILDREN)
    return float(usage.ru_utime + usage.ru_stime + child.ru_utime + child.ru_stime)


def peak_rss_bytes() -> int:
    usage = resource.getrusage(resource.RUSAGE_SELF)
    rss = int(usage.ru_maxrss)
    if sys.platform == "darwin":
        return rss
    return rss * 1024


def repo_root(start: Path | None = None) -> Path:
    cur = (start or Path(__file__)).resolve()
    for candidate in [cur, *cur.parents]:
        marker = candidate / PAPER_REL / "protocol" / "experiment_manifest.json"
        if marker.is_file():
            return candidate
    raise RunnerError("cannot locate neurosymbolic_supervision protocol")


def paper_dir(root: Path) -> Path:
    return root / PAPER_REL


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def load_reuse_admission(root: Path | None = None) -> dict[str, Any]:
    """Load the NS-027 source-bound reuse amendment. Missing means reuse is not admitted."""

    path = paper_dir(root or repo_root()) / "protocol" / "reuse_admission_amendment.json"
    if not path.is_file():
        return {
            "schema": "paper-ns-reuse-admission-amendment/v1",
            "accepted_route": "enforced_full_cold_removal",
            "reuse_admitted": False,
            "final_admission_enabled": False,
            "old_unsupported_profile_rejected": True,
            "missing_amendment": True,
        }
    return load_json(path)


def reuse_credit_permitted(admission: Mapping[str, Any] | None = None) -> bool:
    data = dict(admission) if admission is not None else load_reuse_admission()
    if data.get("reuse_admitted") is True or data.get("accepted_route") == "qualified_reuse":
        raise RunnerError("NS027 removal has no admitted verifier; a future reuse mechanism requires separately reviewed source and qualification")
    return False


def reject_unsupported_reuse_profile(admission: Mapping[str, Any] | None = None) -> bool:
    """Return True when the NS-010/NS-011 unsupported profile is rejected."""

    data = dict(admission) if admission is not None else load_reuse_admission()
    if data.get("accepted_route") in {"enforced_full_cold_removal", "qualified_reuse"}:
        return data.get("old_unsupported_profile_rejected", True) is True
    return True


def run_public_cold_qualification(*, root: Path, source_tree: Path, source_files: Mapping[str, Any], expected_nodes: list[str], output: Path) -> dict[str, Any]:
    """Execute the removed-reuse route on an unchanged public pre-fix baseline.

    This is a public baseline qualification, never a provider or hidden-oracle
    entry point. Actual native lookup/skip validation and command execution are
    retained. No prior pass, cryptographic certificate or reuse benefit is made.
    """
    import shlex
    from ipfs_accelerate_py.agent_supervisor.proof.test_execution_contracts import TestLocatorKey, TestExecutionKey
    from ipfs_accelerate_py.agent_supervisor.proof.test_proof_cache import TestProofCache
    from ipfs_accelerate_py.agent_supervisor.proof.test_certificate_store import TestCertificateStore
    from ipfs_accelerate_py.agent_supervisor.integrations.ipfs_datasets_test_certificate_provider import IpfsDatasetsTestCertificateProvider
    from ipfs_accelerate_py.agent_supervisor.validation.proof_cached_test_validation import ProofCachedTestValidation
    from ipfs_accelerate_py.agent_supervisor.validation.validation_commands import ValidationCommand
    from ipfs_accelerate_py.agent_supervisor.validation.validation_scheduler import run_validation_command
    def required(ok: bool, why: str) -> None:
        if not ok:
            raise RunnerError(why)
    def save_once(path: Path, value: Any) -> None:
        raw = (canonical_dumps(value) + "\n").encode()
        fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
        with os.fdopen(fd, "wb") as stream:
            stream.write(raw); stream.flush(); os.fsync(stream.fileno())
        fd = os.open(path.parent, os.O_RDONLY | os.O_DIRECTORY)
        try: os.fsync(fd)
        finally: os.close(fd)
    def inventory() -> dict[str, Any]:
        result = {}
        for path in sorted(source_tree.rglob("*")):
            required(not path.is_symlink(), "public baseline symlink refused")
            if path.is_file():
                result[str(path.relative_to(source_tree))] = {"sha256": hashlib.sha256(path.read_bytes()).hexdigest(), "mode": path.stat().st_mode & 0o777}
        return result
    required(output.is_absolute() and source_tree.is_absolute(), "absolute reviewed roots required")
    required(not output.exists(), "each qualification requires a new output directory")
    required(not output.is_relative_to(source_tree) and not source_tree.is_relative_to(output), "baseline and observations must be separate")
    required(len(expected_nodes) == 34 and len(set(expected_nodes)) == 34, "whole frozen XMLtodict baseline required")
    required(inventory() == dict(source_files), "unchanged public pre-fix inventory differs")
    admission = load_reuse_admission(root)
    required(not reuse_credit_permitted(admission), "this public route never admits reuse")
    output.mkdir(parents=True, mode=0o700)
    environment = dict(os.environ)  # Preserve qualified research PATH/PYTHONPATH.
    checker_origins = {name: shutil.which(name, path=environment.get("PATH")) for name in ("lean", "lake", "z3", "cvc5")}
    required(all(checker_origins.values()) and environment.get("IPFS_ACCELERATE_AGENT_RESEARCH_TOOLCHAIN_SHA256"), "admitted research runtime/checker bindings must remain available")
    import pytest
    source_digest = sha256_json(dict(source_files))
    runtime = {"python": sys.executable, "python_version": sys.version, "pytest": pytest.__version__, "pytest_origin": pytest.__file__, "PATH": environment.get("PATH"), "PYTHONPATH": environment.get("PYTHONPATH"), "checker_origins": checker_origins, "research_profile_sha256": environment.get("IPFS_ACCELERATE_AGENT_RESEARCH_TOOLCHAIN_SHA256"), "formal_toolchain_sha256": environment.get("FORMAL_TOOLCHAIN_CONTRACT_SHA256")}
    save_once(output / "freeze.json", {"schema": "ns027-actual-public-cold-freeze/v1", "created_at": utcnow(), "source_sha256": source_digest, "source_files": dict(source_files), "expected_nodes": expected_nodes, "runtime": runtime, "runner_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(), "reuse_credit": False, "provider_calls": 0, "hidden_oracle_access": False, "pilot_or_final_admission": False})
    store = TestCertificateStore(output / "empty_native_certificate_store")
    locator = TestLocatorKey(repository_id="historical:martinblech/xmltodict@75a17701db20d5d3ec2ea1f6c901cf2211011eb5", package_identity="public-source-sha256:" + source_digest, node_id="tests/test_xmltodict.py")
    # No runtime proof/trace exists: an explicit missing-cache RUN is required.
    key = TestExecutionKey(locator_cid=locator.locator_id, repository_forest_cid="sha256:" + source_digest, static_trace_root_cid="", runtime_trace_root_cid="", runtime_completeness_policy="public-full-cold-no-reuse/v1", policy_cid="ns027-removed-reuse/v2", test_function_cid="sha256:" + source_files["tests/test_xmltodict.py"]["sha256"], fixture_cids=())
    lookup = TestProofCache(verifier=None).lookup(locator, key, candidates=())
    required(lookup.decision.is_run, "native cache must select cold execution")
    provider = IpfsDatasetsTestCertificateProvider()
    validation = ProofCachedTestValidation(certificate_provider=provider, repository_root=root).validate(task_id="NS-027", goal_id="NS-SG3", validation_command=shlex.join([sys.executable, "-m", "pytest", "tests/test_xmltodict.py"]), decision="SKIPPED: proof cache hit", execution_key=key, certificate=None, pass_receipt=None)
    required(not validation.is_completion_evidence() and "plain_skip_not_evidence" in validation.reason_codes, "native completion validator must reject unsupported skip")
    save_once(output / "native_route.json", {"lookup": lookup.decision.to_dict(), "skip_validation": validation.to_dict(), "certificate_store": str(store.root), "store_has_no_prior_certificate": True, "reuse_credit": False, "fake_pass_receipt_created": False})
    plugin = output / "public_observer.py"
    plugin.write_text('''import json,os,time,resource,sys,hashlib
from pathlib import Path
nodes=[];reports=[];errors=[]
def pytest_collection_modifyitems(session,config,items):nodes.extend(item.nodeid for item in items)
def pytest_collectreport(report):
 if report.failed:errors.append(str(report.nodeid))
def pytest_runtest_logreport(report):reports.append({'nodeid':report.nodeid,'when':report.when,'outcome':report.outcome,'duration':report.duration})
def pytest_sessionfinish(session,exitstatus):
 r=resource.getrusage(resource.RUSAGE_SELF)
 Path(os.environ['NS027_PUBLIC_OBSERVATION']).write_text(json.dumps({'collected':nodes,'reports':reports,'collection_errors':errors,'exitstatus':int(exitstatus),'cpu_seconds':r.ru_utime+r.ru_stime,'maxrss_kib':r.ru_maxrss,'xmltodict_origin':sys.modules['xmltodict'].__file__,'xmltodict_sha256':hashlib.sha256(Path(sys.modules['xmltodict'].__file__).read_bytes()).hexdigest()}))
''')
    environment.setdefault("PYTHON", sys.executable)  # Current admitted interpreter; native sealed launcher remains authoritative.
    environment["PYTHONDONTWRITEBYTECODE"] = "1"
    environment["PYTEST_DISABLE_PLUGIN_AUTOLOAD"] = "1"
    # Append only the observer; never replace the declared research/module roots.
    environment["PYTHONPATH"] = os.pathsep.join(filter(None, [environment.get("PYTHONPATH", ""), str(output), str(source_tree)]))
    stages = []
    for name, extra in (("collect", ["--collect-only"]), ("run", [])):
        command = shlex.join(["python", "-m", "pytest", "-q", "-p", "no:cacheprovider", "-p", "public_observer", *extra, "tests/test_xmltodict.py"])
        stage_env = {**environment, "NS027_PUBLIC_OBSERVATION": str(output / (name + ".observation.json"))}
        save_once(output / (name + ".pending.json"), {"command": command, "started_at": utcnow(), "source_sha256": source_digest})
        result = run_validation_command(spec=ValidationCommand(command=command, cacheable=False, validation_id="NS027-public-" + name), workspace_path=source_tree, timeout_seconds=60, environment=stage_env)
        save_once(output / (name + ".native_command.json"), result)
        observation_path = output / (name + ".observation.json")
        observed = json.loads(observation_path.read_text()) if observation_path.is_file() else None
        stages.append({"stage": name, "command_result_sha256": hashlib.sha256((output / (name + ".native_command.json")).read_bytes()).hexdigest(), "observation": observed})
        required(result.get("returncode") == 0 and result.get("timed_out") is not True, "actual native public command failed: " + name)
        required(observed is not None and observed["collected"] == expected_nodes and not observed["collection_errors"], "whole unchanged public collection differs")
        required(Path(observed["xmltodict_origin"]).resolve() == source_tree / "xmltodict.py" and observed["xmltodict_sha256"] == source_files["xmltodict.py"]["sha256"], "tests imported a different installed XMLtodict version")
        if name == "run":
            reports = observed["reports"]
            required(len(reports) == 3 * len(expected_nodes) and all(r["outcome"] == "passed" for r in reports), "every public setup/call/teardown must pass")
    required(inventory() == dict(source_files), "public source changed during baseline")
    result = {"schema": "ns027-actual-native-public-cold/v1", "success": True, "source_sha256": source_digest, "expected_count": 34, "collected": 34, "passed": 34, "stages": stages, "runtime": runtime, "native_cache_action": str(lookup.decision.action), "skip_completion_evidence": False, "reuse_credit": False, "provider_calls": 0, "hidden_scorer_calls": 0, "pilot_or_final_admission": False, "boundary": "whole unchanged public baseline via actual native scheduler; not a scored provider repair or a reuse witness"}
    save_once(output / "result.json", result)
    return result


class EvidenceLog:
    def __init__(self) -> None:
        self.ids: list[str] = []
        self.bytes_read = 0
        self.bytes_written = 0

    def add_file(self, path: Path) -> str:
        digest = sha256_file(path)
        ident = f"sha256:{path.as_posix()}:{digest}"
        if ident not in self.ids:
            self.ids.append(ident)
        self.bytes_read += path.stat().st_size
        return digest

    def add_blob(self, name: str, data: bytes) -> str:
        digest = sha256_bytes(data)
        ident = f"sha256:{name}:{digest}"
        if ident not in self.ids:
            self.ids.append(ident)
        self.bytes_read += len(data)
        return digest


def measurement(
    status: str,
    unit: str,
    *,
    value: float | int | None = None,
    source: str | None = None,
    reason: str | None = None,
) -> dict[str, Any]:
    if status == "unavailable":
        return {
            "status": "unavailable",
            "value": None,
            "unit": unit,
            "source": source,
            "reason": reason or "unavailable",
        }
    return {
        "status": status,
        "value": value if value is not None else 0,
        "unit": unit,
        "source": source or "runner",
        "reason": reason,
    }


def try_import_semantic_state(root: Path | None = None) -> dict[str, Any]:
    extra = []
    if root is not None:
        extra = [
            str(root / "external" / "ipfs_accelerate"),
            str(root / "external" / "ipfs_datasets"),
            str(root / "external" / "ipfs_kit"),
        ]
    saved = list(sys.path)
    try:
        for path in reversed(extra):
            if path not in sys.path:
                sys.path.insert(0, path)
        import ipfs_accelerate_py.agent_supervisor.semantic_state as mod  # type: ignore

        return {
            "imported": True,
            "module": getattr(mod, "__name__", "semantic_state"),
            "file": getattr(mod, "__file__", None),
            "reason": None,
        }
    except Exception as exc:  # noqa: BLE001 — import boundary
        return {
            "imported": False,
            "module": "ipfs_accelerate_py.agent_supervisor.semantic_state",
            "file": None,
            "reason": f"{type(exc).__name__}: {exc}",
        }
    finally:
        sys.path[:] = saved


def probe_container() -> dict[str, Any]:
    docker = shutil.which("docker")
    cgroup = Path("/sys/fs/cgroup")
    return {
        "docker_available": bool(docker),
        "docker_path": docker,
        "cgroup_available": cgroup.is_dir(),
        "enforced": False,
        "reason": (
            "Docker is absent from PATH and this runner does not create "
            "cgroups; process rlimits and byte/wall caps remain in force."
        ),
    }


_GATEWAY = None


def load_gateway():
    global _GATEWAY
    if _GATEWAY is not None:
        return _GATEWAY
    path = Path(__file__).resolve().with_name("production_gateway.py")
    spec = importlib.util.spec_from_file_location("ns026_production_gateway", path)
    if spec is None or spec.loader is None:
        raise RunnerError("cannot load production_gateway.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    _GATEWAY = module
    return module


def probe_production_provider(root: Path | None = None) -> dict[str, Any]:
    """Fail-closed production identity probe. Never dispatches a paid call."""
    semantic = try_import_semantic_state(root)
    try:
        info = load_gateway().probe(root)
        production = info.get("production") or {}
        development = info.get("development") or {}
        reason = production.get("revision_availability_reason") or "production not admitted"
        return {
            "admitted": bool(production.get("admitted")),
            "served_provider": production.get("served_provider"),
            "served_model": production.get("served_model"),
            "served_revision": production.get("served_revision"),
            "revision_availability_reason": reason,
            "reasoning_effort": (production.get("terra") or {}).get("reasoning_effort"),
            "sampling_seed_supported": bool(development.get("sampling_seed_supported")),
            "temperature_supported": bool(development.get("temperature_supported")),
            "provider_cache_observed": None,
            "credential_names_present": [
                name
                for name in ("XAI_API_KEY", "GROK_API_KEY", "OPENAI_API_KEY", "CODEX_API_KEY")
                if os.environ.get(name)
            ],
            "semantic_state": semantic,
            "development_admitted": bool(development.get("admitted")),
            "amendment_id": info.get("amendment_id"),
            "probe": info,
        }
    except Exception as exc:  # noqa: BLE001
        reason = (
            "Production probe failed closed: "
            f"{type(exc).__name__}: {exc}. "
            "No admitted Terra HIGH reservation is bound."
        )
        return {
            "admitted": False,
            "served_provider": None,
            "served_model": None,
            "served_revision": None,
            "revision_availability_reason": reason,
            "reasoning_effort": None,
            "sampling_seed_supported": False,
            "temperature_supported": False,
            "provider_cache_observed": None,
            "credential_names_present": [],
            "semantic_state": semantic,
            "development_admitted": False,
        }


def load_protocol(root: Path, evidence: EvidenceLog) -> dict[str, Any]:
    folder = paper_dir(root) / "protocol"
    manifest_path = folder / "experiment_manifest.json"
    schema_path = folder / "measurement_schema.json"
    protocol_path = folder / "preregistered_protocol.md"
    manifest = load_json(manifest_path)
    evidence.add_file(manifest_path)
    evidence.add_file(schema_path)
    evidence.add_file(protocol_path)
    return {
        "manifest": manifest,
        "manifest_sha256": sha256_file(manifest_path),
        "schema_sha256": sha256_file(schema_path),
        "protocol_sha256": sha256_file(protocol_path),
        "schema_path": schema_path,
        "budgets": dict(manifest.get("budgets") or DEFAULT_BUDGETS),
        "arms": manifest.get("arms") or {},
    }


def load_bindings_inputs(root: Path, evidence: EvidenceLog) -> dict[str, str]:
    forest = paper_dir(root) / "artifacts" / "source_forest.json"
    oracle = paper_dir(root) / "benchmark" / "oracle_manifest.json"
    runner = Path(__file__).resolve()
    scorer = runner.with_name("score_runs.py")
    return {
        "source_forest_sha256": evidence.add_file(forest) if forest.is_file() else sha256_text("missing-source-forest"),
        "oracle_manifest_sha256": evidence.add_file(oracle) if oracle.is_file() else sha256_text("missing-oracle-manifest"),
        "runner_source_id": "sha256:" + sha256_bytes(runner.read_bytes() + (scorer.read_bytes() if scorer.is_file() else b"")),
    }


def load_task(root: Path, task_id: str, evidence: EvidenceLog) -> dict[str, Any]:
    if task_id in DEV_TASKS:
        task = json.loads(canonical_dumps(DEV_TASKS[task_id]))
        files = task["files"]
        preimage = sha256_json(files)
        task["source_snapshot"]["snapshot_sha256"] = preimage
        evidence.add_blob(f"dev-fixture:{task_id}", canonical_dumps(files).encode("utf-8"))
        return task
    path = paper_dir(root) / "benchmark" / "tasks.jsonl"
    evidence.add_file(path)
    with path.open(encoding="utf-8") as handle:
        for line in handle:
            if not line.strip():
                continue
            row = json.loads(line)
            if row.get("task_id") == task_id:
                return row
    raise RunnerError(f"unknown task_id {task_id}", terminal="unavailable")


def iter_tasks(root: Path, *, split: str | None = None, family_id: str | None = None, live_only: bool = False):
    path = paper_dir(root) / "benchmark" / "tasks.jsonl"
    with path.open(encoding="utf-8") as handle:
        for line in handle:
            if not line.strip():
                continue
            row = json.loads(line)
            if split and row.get("split") != split:
                continue
            if family_id and row.get("family_id") != family_id:
                continue
            if live_only and not row.get("live_repair_admitted"):
                continue
            yield row


def arm_schedule_order(family_id: str, repetition: int, cache: str, arms: list[str]) -> list[str]:
    def key(arm: str) -> tuple[str, str]:
        material = f"{PROTOCOL_ID}|{family_id}|{repetition}|{cache}|{arm}"
        return sha256_text(material), arm

    return sorted(arms, key=key)


def schedule_unit_id(
    task_id: str,
    arm: str,
    cache: str,
    repetition: int,
    record_kind: str,
    path_class: str,
    scenario: str,
) -> str:
    material = f"{PROTOCOL_ID}|{task_id}|{arm}|{cache}|{repetition}|{record_kind}|{path_class}|{scenario}"
    return sha256_text(material)


def logical_effect_id(unit_id: str) -> str:
    return sha256_text(f"effect|{unit_id}")


class DurableLedger:
    def __init__(self, path: Path) -> None:
        self.path = path
        self.path.mkdir(parents=True, exist_ok=True)
        self._lock = threading.RLock()
        self._campaign_path = self.path / "campaign.json"
        if not self._campaign_path.is_file():
            atomic_write(
                self._campaign_path,
                {
                    "schema": "paper-ns-runner-campaign/v1",
                    "provider_effects_reserved": 0,
                    "provider_effects_dispatched": 0,
                    "provider_calls_by_effect": {},
                    "unknown_effects": [],
                    "units": {},
                },
            )

    def campaign(self) -> dict[str, Any]:
        return load_json(self._campaign_path)

    def _save_campaign(self, data: dict[str, Any]) -> None:
        atomic_write(self._campaign_path, data)

    def internal_path(self, unit_id: str) -> Path:
        return self.path / "units" / f"{unit_id}.json"

    def get_internal(self, unit_id: str) -> dict[str, Any] | None:
        path = self.internal_path(unit_id)
        if not path.is_file():
            return None
        return load_json(path)

    def put_internal(self, unit_id: str, payload: dict[str, Any]) -> None:
        atomic_write(self.internal_path(unit_id), payload)

    def reserve_effect(self, unit_id: str, *, path_class: str, production: bool, cap: int) -> str:
        with self._lock:
            campaign = self.campaign()
            existing = (campaign.get("units") or {}).get(unit_id) or {}
            if existing.get("logical_effect_id"):
                return str(existing["logical_effect_id"])
            if int(campaign.get("provider_effects_reserved") or 0) >= cap:
                raise RunnerError(
                    "NS-006 boundary provider-effect cap exhausted",
                    terminal="rejected",
                )
            effect_id = logical_effect_id(unit_id)
            campaign["provider_effects_reserved"] = int(campaign.get("provider_effects_reserved") or 0) + 1
            units = dict(campaign.get("units") or {})
            units[unit_id] = {
                "logical_effect_id": effect_id,
                "path_class": path_class,
                "production": production,
                "dispatch_confirmed": False,
                "provider_calls": 0,
            }
            campaign["units"] = units
            self._save_campaign(campaign)
            return effect_id

    def note_dispatch(self, unit_id: str, effect_id: str) -> None:
        with self._lock:
            campaign = self.campaign()
            calls = dict(campaign.get("provider_calls_by_effect") or {})
            prior = int(calls.get(effect_id) or 0)
            if prior >= 1:
                raise RunnerError(
                    "refusing duplicate provider dispatch for a reserved effect",
                    terminal="unavailable",
                )
            calls[effect_id] = prior + 1
            campaign["provider_calls_by_effect"] = calls
            campaign["provider_effects_dispatched"] = int(campaign.get("provider_effects_dispatched") or 0) + 1
            units = dict(campaign.get("units") or {})
            row = dict(units.get(unit_id) or {})
            row["dispatch_confirmed"] = True
            row["provider_calls"] = int(row.get("provider_calls") or 0) + 1
            row["logical_effect_id"] = effect_id
            units[unit_id] = row
            campaign["units"] = units
            self._save_campaign(campaign)

    def note_unknown(self, unit_id: str, effect_id: str) -> None:
        with self._lock:
            campaign = self.campaign()
            unknown = list(campaign.get("unknown_effects") or [])
            if effect_id not in unknown:
                unknown.append(effect_id)
            campaign["unknown_effects"] = unknown
            self._save_campaign(campaign)


def apply_rlimits(memory_bytes: int) -> dict[str, Any]:
    applied: dict[str, Any] = {}
    for name, value in (
        ("RLIMIT_AS", memory_bytes),
        ("RLIMIT_FSIZE", memory_bytes),
        ("RLIMIT_CORE", 0),
    ):
        limit = getattr(resource, name, None)
        if limit is None:
            applied[name] = {"applied": False, "reason": "limit name absent"}
            continue
        try:
            resource.setrlimit(limit, (value, value))
            applied[name] = {"applied": True, "value": value}
        except (ValueError, OSError) as exc:
            applied[name] = {"applied": False, "reason": f"{type(exc).__name__}: {exc}"}
    return applied


def hidden_markers_in(text: str) -> list[str]:
    found = []
    lowered = text.replace("\\", "/").lower()
    for marker in HIDDEN_MARKERS:
        if marker.lower() in lowered:
            found.append(marker)
    return found


def write_tree(root: Path, files: Mapping[str, str]) -> None:
    for rel, content in files.items():
        dest = (root / rel).resolve()
        if not str(dest).startswith(str(root.resolve())):
            raise RunnerError(f"path escapes sandbox: {rel}", terminal="rejected")
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_text(content, encoding="utf-8")


def collect_tree(root: Path) -> dict[str, str]:
    out: dict[str, str] = {}
    for path in sorted(root.rglob("*")):
        if path.is_file():
            out[path.relative_to(root).as_posix()] = path.read_text(encoding="utf-8")
    return out


def inspect_isolation(sandbox: Path, repo: Path) -> dict[str, Any]:
    hidden_store = paper_dir(repo) / "receipts" / "snapshots" / "NS-005" / "scorer_only"
    mounted = False
    markers: list[str] = []
    for path in sandbox.rglob("*"):
        if not path.is_file():
            continue
        text = path.read_text(encoding="utf-8", errors="replace")
        markers.extend(hidden_markers_in(text))
        markers.extend(hidden_markers_in(path.as_posix()))
        try:
            if hidden_store.exists() and path.resolve().is_relative_to(hidden_store.resolve()):
                mounted = True
        except AttributeError:
            if hidden_store.exists() and str(path.resolve()).startswith(str(hidden_store.resolve())):
                mounted = True
    # Deduplicate while preserving order.
    seen: list[str] = []
    for item in markers:
        if item not in seen:
            seen.append(item)
    return {
        "proposal_sandbox_root": str(sandbox),
        "hidden_store_mounted": mounted,
        "hidden_markers_found": seen,
        "scope_preserved": (not mounted) and not seen,
    }


def pack_context(task: dict[str, Any], arm: str, sandbox: Path) -> dict[str, Any]:
    files = collect_tree(sandbox)
    issue = task.get("issue") or {}
    raw = {
        "mode": "raw_lexical",
        "issue": issue,
        "files": files,
        "admitted_paths": sorted(files),
    }
    symbols: list[dict[str, Any]] = []
    for rel, content in files.items():
        if not rel.endswith(".py"):
            continue
        try:
            tree = ast.parse(content)
        except SyntaxError:
            symbols.append({"path": rel, "parse": "syntax_error"})
            continue
        names = [
            node.name
            for node in ast.walk(tree)
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef))
        ]
        symbols.append({"path": rel, "names": names, "sha256": sha256_text(content)})
    semantic = {
        "mode": "development_ast_name_index",
        "issue": issue,
        "symbols": symbols,
        "admitted_paths": sorted(files),
        "note": (
            "Local AST/name index only. This is not the production datasets "
            "semantic pack (anyio/semantic_state import is independent)."
        ),
    }
    spec = {
        "A": {"context": raw, "routing": "model_first", "reuse": False, "governed_lifecycle": False},
        "B": {"context": semantic, "routing": "model_first", "reuse": False, "governed_lifecycle": False},
        "C": {"context": semantic, "routing": "obligation_aware", "reuse": True, "governed_lifecycle": False},
        "D": {"context": semantic, "routing": "obligation_aware", "reuse": True, "governed_lifecycle": True},
        "C-no-route": {"context": semantic, "routing": "model_first", "reuse": True, "governed_lifecycle": False},
        "C-no-reuse": {"context": semantic, "routing": "obligation_aware", "reuse": False, "governed_lifecycle": False},
    }
    packed = dict(spec[arm])
    packed["arm"] = arm
    admission = load_reuse_admission()
    if not reuse_credit_permitted(admission):
        packed["reuse"] = False
        packed["reuse_credit"] = False
        packed["reuse_profile"] = "removed_full_cold"
        packed["unsupported_reuse_profile_rejected"] = reject_unsupported_reuse_profile(admission)
    else:
        packed["reuse_credit"] = bool(packed.get("reuse"))
        packed["unsupported_reuse_profile_rejected"] = reject_unsupported_reuse_profile(admission)
    packed["byte_length"] = len(canonical_dumps(packed).encode("utf-8"))
    return packed


def default_upstream_store(root: Path) -> Path:
    env = os.environ.get("NS_NS026_UPSTREAM_STORE")
    if env:
        return Path(env)
    return paper_dir(root) / "qualification" / "production_provider" / "upstream_store"


def materialize_live_task(task: dict[str, Any], dest: Path, *, root: Path | None = None, store: Path | None = None) -> dict[str, Any]:
    """Materialize exact pinned upstream pre-fix sources. Never uses caller git."""
    root = root or repo_root()
    store = store or default_upstream_store(root)
    gateway = load_gateway()
    return gateway.materialize_pinned_snapshot(task, dest, root=root, store=store, mode="proposal")


def proposal_safe_files(files: Mapping[str, str] | None) -> dict[str, str] | None:
    if files is None:
        return None
    out = {}
    for rel, content in files.items():
        norm = rel.replace("\\", "/")
        if norm == ".git" or norm.startswith(".git/") or "/.git/" in f"/{norm}/":
            continue
        blob = content if isinstance(content, str) else ""
        if hidden_markers_in(norm) or hidden_markers_in(blob):
            continue
        out[rel] = content
    return out


def development_candidate(scenario: str) -> dict[str, Any] | None:
    if scenario in {"abstain", "cancel", "timeout-no-candidate"}:
        return None
    if scenario == "unsolved":
        return {
            "kind": "generated_patch",
            "files": {"pkg/core.py": _WRONG_ADD},
            "patch_text": _SOLVED_PATCH.replace("a + b", "a - b"),
        }
    if scenario == "reject-scope":
        return {
            "kind": "generated_patch",
            "files": {"tests/test_hidden.py": _HIDDEN_TEST, "pkg/core.py": _FIXED_ADD},
            "patch_text": "illegal hidden-test edit",
        }
    if scenario == "oversize-patch":
        blob = "x" * 20000
        return {
            "kind": "generated_patch",
            "files": {"pkg/core.py": f"def add(a, b):\n    return a + b  # {blob}\n"},
            "patch_text": blob,
        }
    return {
        "kind": "generated_patch",
        "files": {"pkg/core.py": _FIXED_ADD},
        "patch_text": _SOLVED_PATCH,
    }


def apply_candidate(sandbox: Path, candidate: Mapping[str, str], allowed: list[str]) -> None:
    allowed_set = {item.replace("\\", "/") for item in allowed}
    for rel, content in candidate.items():
        norm = rel.replace("\\", "/").lstrip("./")
        if norm not in allowed_set:
            raise RunnerError(f"candidate path not in admitted scope: {norm}", terminal="rejected")
        dest = (sandbox / norm).resolve()
        if not str(dest).startswith(str(sandbox.resolve())):
            raise RunnerError(f"candidate path escapes sandbox: {norm}", terminal="rejected")
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_text(content, encoding="utf-8")


def dir_size(path: Path) -> int:
    total = 0
    if not path.exists():
        return 0
    for child in path.rglob("*"):
        if child.is_file():
            total += child.stat().st_size
    return total


def invoke_independent_scorer(attempt_path: Path, out_path: Path, timeout: float) -> dict[str, Any]:
    scorer = Path(__file__).resolve().with_name("score_runs.py")
    import subprocess

    cpu0 = cpu_seconds()
    wall0 = time.perf_counter()
    result = subprocess.run(
        [sys.executable, str(scorer), "--attempt", str(attempt_path), "--out", str(out_path)],
        capture_output=True,
        text=True,
        timeout=timeout,
        check=False,
    )
    wall = time.perf_counter() - wall0
    cpu = max(0.0, cpu_seconds() - cpu0)
    if result.returncode != 0:
        raise RunnerError(
            f"independent scorer failed: {result.stderr.strip() or result.stdout.strip() or result.returncode}",
            terminal="unavailable",
        )
    scored = load_json(out_path)
    scored.setdefault("runner_meta", {})
    scored["runner_meta"]["scoring_wall_seconds"] = wall
    scored["runner_meta"]["scoring_cpu_seconds"] = cpu
    scored["runner_meta"]["scorer_exit_code"] = result.returncode
    return scored


def stage_record(
    name: str,
    started: float,
    origin: float,
    evidence_id: str,
    cpu: float | None,
    cpu_reason: str | None = None,
) -> dict[str, Any]:
    finished = time.perf_counter()
    if cpu is None:
        host = measurement("unavailable", "seconds", reason=cpu_reason or "stage cpu not separately accounted")
    else:
        host = measurement("actual", "seconds", value=max(0.0, cpu), source="resource.getrusage")
    return {
        "stage": name,
        "started_monotonic_seconds": max(0.0, started - origin),
        "finished_monotonic_seconds": max(0.0, finished - origin),
        "process_accounting_ids": [f"pid:{os.getpid()}"],
        "host_cpu_seconds": host,
        "overlaps_stage_ids": [],
        "evidence_id": evidence_id,
    }


def empty_measurements() -> dict[str, Any]:
    unavailable = {
        "input_tokens": ("tokens", "Provider did not return tokenizer counts; bytes are not token counts."),
        "output_tokens": ("tokens", "Provider did not return tokenizer counts; bytes are not token counts."),
        "cached_input_tokens": ("tokens", "Provider cache tokens were not exposed."),
        "reasoning_tokens": ("tokens", "Provider reasoning tokens were not exposed."),
        "provider_charge": ("currency", "No billing receipt; tariff-derived money is not treated as measured."),
        "remote_gpu_seconds": ("seconds", "No GPU was reserved or observed."),
    }
    out: dict[str, Any] = {}
    for key, (unit, reason) in unavailable.items():
        out[key] = measurement("unavailable", unit, reason=reason)
    return out


class AttemptExecutor:
    def __init__(self, args: argparse.Namespace) -> None:
        self.args = args
        self.root = repo_root(Path(args.repo).resolve() if getattr(args, "repo", None) else None)
        self.evidence = EvidenceLog()
        self.protocol = load_protocol(self.root, self.evidence)
        extra = load_bindings_inputs(self.root, self.evidence)
        self.source_forest_sha256 = extra["source_forest_sha256"]
        self.oracle_manifest_sha256 = extra["oracle_manifest_sha256"]
        self.runner_source_id = extra["runner_source_id"]
        self.semantic = try_import_semantic_state(self.root)
        self.container = probe_container()
        self.ledger = DurableLedger(Path(args.ledger).resolve())
        budgets = dict(DEFAULT_BUDGETS)
        budgets.update({k: self.protocol["budgets"].get(k, v) for k, v in DEFAULT_BUDGETS.items()})
        if args.request_bytes_max is not None:
            budgets["request_serialized_bytes_max"] = args.request_bytes_max
        if args.patch_bytes_max is not None:
            budgets["admitted_patch_bytes_max"] = args.patch_bytes_max
        if args.provider_wall_seconds is not None:
            budgets["provider_wall_seconds_max"] = args.provider_wall_seconds
        if args.active_unit_wall_seconds is not None:
            budgets["active_unit_wall_seconds_max"] = args.active_unit_wall_seconds
        self.budgets = budgets
        self.rlimits = apply_rlimits(int(budgets["aggregate_memory_bytes"]))
        self.provider_usage: dict[str, Any] | None = None
        self.upstream_store = (
            Path(args.upstream_store).resolve()
            if getattr(args, "upstream_store", None)
            else default_upstream_store(self.root)
        )

    def execute(self) -> dict[str, Any]:
        args = self.args
        origin = time.perf_counter()
        cpu0 = cpu_seconds()
        started_at = utcnow()
        stages: list[dict[str, Any]] = []
        scenario = args.scenario
        path_class = args.path
        task = load_task(self.root, args.task_id, self.evidence)
        live = bool(task.get("live_repair_admitted"))
        arm = args.arm
        cache = args.cache
        repetition = int(args.repetition)
        record_kind = args.record_kind
        unit_id = schedule_unit_id(
            task["task_id"], arm, cache, repetition, record_kind, path_class, scenario
        )
        existing = self.ledger.get_internal(unit_id)
        if existing and existing.get("published_attempt"):
            published = existing["published_attempt"]
            retained = (published.get("provider_receipt") or {}).get("host_verified")
            if retained:
                current = load_gateway().verify_host_response(self.root, retained["binding"])
                if current != retained:
                    raise RunnerError("published host result changed; do not replay or redispatch")
            published["runner"]["interruption"]["resumed"] = True
            published["runner"]["interruption"]["duplicate_dispatch_prevented"] = True
            published["provider_receipt"]["replayed"] = True
            return published

        work = Path(tempfile.mkdtemp(prefix="ns006-unit-"))
        sandbox = work / "proposal"
        scorer_tmp = work / "score"
        sandbox.mkdir()
        scorer_tmp.mkdir()
        prime_cpu = 0.0
        prime_elapsed = 0.0
        limit_triggered = None
        candidate = None
        provider_receipt = None
        isolation = {
            "proposal_sandbox_root": str(sandbox),
            "hidden_store_mounted": False,
            "hidden_markers_found": [],
            "scope_preserved": True,
        }
        context: dict[str, Any] = {}
        publication = {
            "required": arm == "D",
            "admitted": None,
            "receipt_id": None,
            "parent_id": None,
        }
        resumed = bool(existing)
        unknown_effect = False
        dispatch_confirmed = False
        effect_id = None
        oracle = {
            "status": "not_run",
            "independent_scorer_id": None,
            "receipt_id": None,
            "cold_full_validation": False,
            "candidate_valid": None,
            "hidden_access_incident": False,
            "reason": "scoring not started",
        }
        scoring_cpu = 0.0
        scoring_elapsed = 0.0
        terminal = "unsolved"
        reason = "attempt started"
        bytes_written = 0
        base_files: dict[str, str] = {}

        def finish(state: str, why: str, **more: Any) -> dict[str, Any]:
            nonlocal terminal, reason
            terminal = state
            reason = why
            return self._publish(
                task=task,
                arm=arm,
                cache=cache,
                repetition=repetition,
                record_kind=record_kind,
                path_class=path_class,
                scenario=scenario,
                unit_id=unit_id,
                origin=origin,
                cpu0=cpu0,
                started_at=started_at,
                stages=stages,
                isolation=isolation,
                context=context,
                candidate=candidate,
                provider_receipt=provider_receipt,
                oracle=oracle,
                publication=publication,
                live=live,
                resumed=resumed,
                unknown_effect=unknown_effect,
                dispatch_confirmed=dispatch_confirmed,
                effect_id=effect_id,
                sandbox_files=base_files,
                limit_triggered=limit_triggered,
                prime_cpu=prime_cpu,
                prime_elapsed=prime_elapsed,
                scoring_cpu=scoring_cpu,
                scoring_elapsed=scoring_elapsed,
                bytes_written=bytes_written,
                sandbox=sandbox,
                work=work,
                terminal=state,
                reason=why,
                extra=more,
            )

        try:
            if path_class == "production" and record_kind in ("development", "pilot", "final"):
                gateway = load_gateway()
                gw = gateway.dispatch({"path_class": path_class, "record_kind": record_kind, "task_id": task["task_id"], "arm": arm, "cache": cache, "repetition": repetition}, root=self.root)
                if gw.get("schema") == "paper-ns-host-handoff-pending/v1":
                    # Pending transport is not a scientific outcome or terminal ledger row.
                    return {**gw, "path_class": path_class, "schedule_unit_id": unit_id, "task_id": task["task_id"], "record_kind": record_kind, "terminal_published": False}
                if gw.get("schema") != f"paper-ns-host-historical-{record_kind}/v1":
                    raise RunnerError("unrecognized historical host response")
                verified = gw["host_verified"]
                signed = verified["receipt"]
                effect_id = "operator-grant:" + signed["grant_sha256"]
                provider_receipt = self._receipt_from_gateway(gw, path_class=path_class, effect_id=effect_id)
                dispatch_confirmed = bool(gw.get("dispatch_confirmed"))
                self.provider_usage = (signed.get("provider_stream_metadata") or {}).get("usage")
                candidate = {"host_candidate_sha256": signed.get("candidate_sha256"), "patch_bytes": signed.get("patch_bytes"), "files_retained_host_only": True} if signed.get("candidate_sha256") else None
                context = {"arm": arm, "routing": "fixed_operator_host_http_request", "request_binding": signed.get("request_binding"), "client_reads_hidden_oracle": False}
                isolation = {"scope_preserved": True, "hidden_store_mounted": False, "hidden_markers_found": [], "boundary_scope": "fixed_host_http_request_and_reviewed_sealed_candidate", "provider_termination": signed.get("provider_termination"), "scorer_boundary_sha256": (signed.get("scorer") or {}).get("boundary_sha256"), "automatic_adversarial_scorer_integrity_qualified": False, "human_annotation": False}
                if record_kind in ("pilot", "final") and verified.get("terminal_failure") is True:
                    oracle = gateway.host_oracle(verified)
                    return finish("unavailable", oracle["reason"])
                if not gw.get("admitted_historical_" + record_kind):
                    return finish("unavailable", f"Signed result does not admit this historical {record_kind} pipeline; no final result inferred.")
                oracle = gateway.host_oracle(verified)
                return finish("solved" if oracle["status"] == "passed" else "unsolved" if oracle["status"] == "failed" else "unavailable", oracle["reason"])
            t_index = time.perf_counter()
            if live:
                material = materialize_live_task(
                    task, sandbox, root=self.root, store=self.upstream_store
                )
                if not material["ok"]:
                    stages.append(stage_record("index_context", t_index, origin, "evidence:index", cpu_seconds() - cpu0))
                    return finish(
                        "unavailable",
                        f"pre-fix snapshot not materialized: {material['reason']}",
                    )
            else:
                write_tree(sandbox, task["files"])
            base_files = proposal_safe_files(collect_tree(sandbox)) or {}
            isolation = inspect_isolation(sandbox, self.root)
            if isolation["hidden_store_mounted"] or isolation["hidden_markers_found"]:
                isolation["scope_preserved"] = False
                oracle["hidden_access_incident"] = True
                stages.append(stage_record("index_context", t_index, origin, "evidence:index", cpu_seconds() - cpu0))
                return finish("rejected", "hidden oracle material present in proposal sandbox")

            if cache == "local_warm":
                t_prime = time.perf_counter()
                cpu_prime0 = cpu_seconds()
                context = pack_context(task, arm, sandbox)
                if not reuse_credit_permitted():
                    context = dict(context)
                    context["reuse"] = False
                    context["reuse_credit"] = False
                prime_elapsed = time.perf_counter() - t_prime
                prime_cpu = max(0.0, cpu_seconds() - cpu_prime0)
                stages.append(
                    stage_record(
                        "warm_prime",
                        t_prime,
                        origin,
                        "evidence:warm-prime:" + sha256_json(context)[:16],
                        prime_cpu,
                    )
                )
            else:
                cache_dir = self.ledger.path / "cache" / unit_id
                if cache_dir.exists():
                    shutil.rmtree(cache_dir)

            context = pack_context(task, arm, sandbox)
            if scenario == "oversize-request":
                context = dict(context)
                context["pad"] = "x" * (int(self.budgets["request_serialized_bytes_max"]) + 8)
            request_bytes = len(canonical_dumps(context).encode("utf-8"))
            stages.append(
                stage_record(
                    "index_context",
                    t_index,
                    origin,
                    "evidence:index:" + sha256_json({"paths": sorted(collect_tree(sandbox))})[:16],
                    cpu_seconds() - cpu0,
                )
            )
            if request_bytes > int(self.budgets["request_serialized_bytes_max"]):
                limit_triggered = "serialized_request_bytes"
                return finish("rejected", f"serialized request {request_bytes} exceeds cap")

            if scenario == "cancel":
                return finish("cancelled", "cancellation observed before provider dispatch")

            if live and path_class != "production":
                return finish(
                    "unavailable",
                    "live historical tasks require the admitted production path; "
                    f"requested path_class={path_class}",
                )

            production_probe = probe_production_provider(self.root) if path_class == "production" else None
            if path_class == "production" and not production_probe["admitted"]:
                return finish(
                    "unavailable",
                    production_probe["revision_availability_reason"],
                )

            if time.perf_counter() - origin > float(self.budgets["active_unit_wall_seconds_max"]):
                limit_triggered = "active_unit_wall_seconds"
                return finish("timed_out", "active unit wall budget exhausted before provider")

            will_dispatch = scenario not in {"cancel"} and not (
                existing and existing.get("provider_receipt")
            )
            if existing and existing.get("provider_receipt"):
                provider_receipt = existing["provider_receipt"]
                candidate = (existing.get("candidate") or None)
                effect_id = existing.get("logical_effect_id")
                dispatch_confirmed = True
                resumed = True
                t_rec = time.perf_counter()
                stages.append(stage_record("retry_recovery", t_rec, origin, "evidence:resume", cpu_seconds() - cpu0))
            elif will_dispatch:
                cap = int(self.budgets["pre_final_boundary_provider_effects_reserved"])
                t_prov = time.perf_counter()
                effect_id = self.ledger.reserve_effect(
                    unit_id,
                    path_class=path_class,
                    production=path_class == "production",
                    cap=cap,
                )
                if args.crash_after == "reserve":
                    self.ledger.put_internal(
                        unit_id,
                        {
                            "logical_effect_id": effect_id,
                            "path_class": path_class,
                            "provider_receipt": None,
                            "dispatch_confirmed": False,
                        },
                    )
                    if path_class == "production":
                        self.ledger.note_unknown(unit_id, effect_id)
                    raise CrashAfter("reserved without confirmed dispatch")
                if scenario == "timeout":
                    deadline = t_prov + float(self.budgets["provider_wall_seconds_max"])
                    while time.perf_counter() < deadline + 0.05:
                        time.sleep(0.01)
                        if time.perf_counter() - origin > float(self.budgets["active_unit_wall_seconds_max"]):
                            break
                    limit_triggered = "provider_wall_seconds"
                    stages.append(stage_record("provider", t_prov, origin, "evidence:provider-timeout", None, "timed out"))
                    return finish("timed_out", "provider wall budget exhausted")
                use_admitted = bool(getattr(args, "admitted_provider", False) or scenario == "admitted-development")
                if path_class == "production":
                    if not production_probe or not production_probe.get("admitted"):
                        raise RunnerError("production dispatch reached without admission", terminal="unavailable")
                    gw = self._gateway_dispatch(
                        task=task,
                        path_class=path_class,
                        files=base_files,
                        context=context,
                        timeout=float(self.budgets["provider_wall_seconds_max"]),
                    )
                    candidate = gw.get("candidate")
                    provider_receipt = self._receipt_from_gateway(gw, path_class=path_class, effect_id=effect_id)
                    self.provider_usage = gw.get("usage") if isinstance(gw.get("usage"), dict) else None
                elif use_admitted and scenario in {"default", "admitted-development"}:
                    gw = self._gateway_dispatch(
                        task=task,
                        path_class="development",
                        files=base_files,
                        context=context,
                        timeout=float(self.budgets["provider_wall_seconds_max"]),
                    )
                    candidate = gw.get("candidate")
                    provider_receipt = self._receipt_from_gateway(gw, path_class=path_class, effect_id=effect_id)
                    self.provider_usage = gw.get("usage") if isinstance(gw.get("usage"), dict) else None
                    if gw.get("stage_failure") == "provider" and not gw.get("dispatched"):
                        stages.append(
                            stage_record(
                                "provider",
                                t_prov,
                                origin,
                                "evidence:provider-unavailable",
                                cpu_seconds() - cpu0,
                            )
                        )
                        return finish(str(gw.get("terminal") or "unavailable"), str(gw.get("reason") or "gateway refused"))
                else:
                    candidate = development_candidate(scenario)
                    runtime_id = "sha256:" + sha256_json(
                        {"effect": effect_id, "candidate": candidate, "path_class": path_class}
                    )
                    provider_receipt = {
                        "path_class": path_class,
                        "simulated": True,
                        "admitted_production": False,
                        "dispatched": True,
                        "dispatch_confirmed": True,
                        "logical_effect_id": effect_id,
                        "served_provider": (
                            "ns-006-injected-development" if path_class != "simulated" else "ns-006-simulated"
                        ),
                        "served_model": "ns-006-deterministic-dev-stub",
                        "served_revision": "ns-006-dev-stub-v1",
                        "revision_availability_reason": None,
                        "reasoning_effort": None,
                        "runtime_receipt_id": runtime_id,
                        "usage_receipt_id": None,
                        "possibly_charged": False,
                        "sampling_seed_supported": False,
                        "temperature_supported": False,
                        "proposal_effect_count": 1,
                        "provider_cache_observed": None,
                        "unknown_effect": False,
                        "replayed": False,
                    }
                self.ledger.note_dispatch(unit_id, effect_id)
                dispatch_confirmed = True
                if provider_receipt is not None:
                    provider_receipt = dict(provider_receipt)
                    provider_receipt["logical_effect_id"] = effect_id
                    provider_receipt["dispatched"] = True
                    provider_receipt["dispatch_confirmed"] = True
                    provider_receipt["proposal_effect_count"] = 1
                    provider_receipt["unknown_effect"] = False
                    provider_receipt["replayed"] = False
                    if path_class != "simulated":
                        provider_receipt["path_class"] = path_class
                    if not provider_receipt.get("runtime_receipt_id"):
                        provider_receipt["runtime_receipt_id"] = "sha256:" + sha256_json(
                            {"effect": effect_id, "candidate": candidate, "path_class": path_class}
                        )
                if path_class == "simulated":
                    provider_receipt["simulated"] = True
                    provider_receipt["served_provider"] = "ns-006-simulated"
                evidence_token = str(
                    (provider_receipt or {}).get("runtime_receipt_id")
                    or effect_id
                    or "provider"
                )
                stages.append(
                    stage_record(
                        "provider",
                        t_prov,
                        origin,
                        "evidence:provider:" + evidence_token[-16:],
                        cpu_seconds() - cpu0,
                    )
                )
                if args.crash_after == "provider":
                    self.ledger.put_internal(
                        unit_id,
                        {
                            "logical_effect_id": effect_id,
                            "path_class": path_class,
                            "provider_receipt": provider_receipt,
                            "candidate": candidate,
                            "dispatch_confirmed": True,
                            "context": context,
                            "isolation": isolation,
                        },
                    )
                    raise CrashAfter("provider receipt stored; scoring not started")
            else:
                t_prov = time.perf_counter()
                stages.append(stage_record("provider", t_prov, origin, "evidence:provider-skip", cpu_seconds() - cpu0))

            if candidate is None:
                if scenario == "abstain" or (provider_receipt and provider_receipt.get("served_provider") == "xai"):
                    return finish("abstained", (provider_receipt or {}).get("revision_availability_reason") or "provider returned no candidate")
                return finish("unsolved", "no candidate produced")

            patch_bytes = len((candidate.get("patch_text") or "").encode("utf-8"))
            file_bytes = sum(len(v.encode("utf-8")) for v in (candidate.get("files") or {}).values())
            admitted_bytes = max(patch_bytes, file_bytes)
            if admitted_bytes > int(self.budgets["admitted_patch_bytes_max"]):
                limit_triggered = "admitted_patch_bytes"
                return finish("rejected", f"admitted patch {admitted_bytes} exceeds cap")

            t_fix = time.perf_counter()
            try:
                apply_candidate(sandbox, candidate.get("files") or {}, task.get("allowed_paths") or list((candidate.get("files") or {})))
            except RunnerError as exc:
                limit_triggered = "scope"
                stages.append(stage_record("fixture_setup", t_fix, origin, "evidence:scope-reject", cpu_seconds() - cpu0))
                return finish(exc.terminal, str(exc))
            stages.append(stage_record("fixture_setup", t_fix, origin, "evidence:fixture-setup", cpu_seconds() - cpu0))
            stages.append(stage_record("fixture_call", time.perf_counter(), origin, "evidence:fixture-call", cpu_seconds() - cpu0))
            stages.append(stage_record("fixture_teardown", time.perf_counter(), origin, "evidence:fixture-teardown", cpu_seconds() - cpu0))

            t_proof = time.perf_counter()
            stages.append(
                stage_record(
                    "proof_generate",
                    t_proof,
                    origin,
                    "evidence:proof-generate",
                    None,
                    "native prover unavailable in this profile; stage is a probe only",
                )
            )
            stages.append(
                stage_record(
                    "proof_verify",
                    time.perf_counter(),
                    origin,
                    "evidence:proof-verify",
                    None,
                    "native prover unavailable in this profile; stage is a probe only",
                )
            )

            if arm == "D":
                t_pub = time.perf_counter()
                parent = "bootstrap:none"
                pub_body = {
                    "schema": "paper-ns-development-publication/v1",
                    "unit_id": unit_id,
                    "parent": parent,
                    "path_class": path_class,
                    "admitted_production": False,
                }
                pub_id = "sha256:" + sha256_json(pub_body)
                atomic_write(self.ledger.path / "publications" / f"{unit_id}.json", pub_body)
                publication = {
                    "required": True,
                    "admitted": True,
                    "receipt_id": pub_id,
                    "parent_id": parent,
                }
                stages.append(stage_record("publication", t_pub, origin, pub_id, cpu_seconds() - cpu0))
                bytes_written += len(canonical_dumps(pub_body).encode("utf-8"))
            else:
                publication = {
                    "required": False,
                    "admitted": None,
                    "receipt_id": None,
                    "parent_id": None,
                }

            t_seal = time.perf_counter()
            draft = self._measurement_draft(
                task=task,
                arm=arm,
                cache=cache,
                repetition=repetition,
                record_kind=record_kind,
                unit_id=unit_id,
                started_at=started_at,
                live=live,
                candidate=candidate,
                publication=publication,
                provider_receipt=provider_receipt,
                oracle=oracle,
                isolation=isolation,
                limit_triggered=limit_triggered,
                origin=origin,
                cpu0=cpu0,
                stages=stages,
                prime_cpu=prime_cpu,
                prime_elapsed=prime_elapsed,
                scoring_cpu=0.0,
                scoring_elapsed=0.0,
                bytes_written=bytes_written,
                sandbox=sandbox,
                terminal="unsolved",
                reason="awaiting independent score",
                context=context,
            )
            wrapper_draft = self._wrapper(
                command=args.command,
                path_class=path_class,
                task=task,
                unit_id=unit_id,
                measurement=draft,
                isolation=isolation,
                context=context,
                candidate=candidate,
                provider_receipt=provider_receipt or self._null_provider(path_class),
                live=live,
                resumed=resumed,
                unknown_effect=False,
                limit_triggered=limit_triggered,
                sandbox_files=base_files,
            )
            draft_path = scorer_tmp / "attempt-draft.json"
            atomic_write(draft_path, wrapper_draft)
            bytes_written += draft_path.stat().st_size
            stages.append(stage_record("persist_seal", t_seal, origin, "evidence:persist:" + sha256_file(draft_path)[:16], cpu_seconds() - cpu0))

            t_score = time.perf_counter()
            cpu_s0 = cpu_seconds()
            scored_path = scorer_tmp / "attempt-scored.json"
            scored = invoke_independent_scorer(
                draft_path,
                scored_path,
                float(self.budgets["independent_cold_scoring_wall_seconds_max"]),
            )
            scoring_elapsed = time.perf_counter() - t_score
            scoring_cpu = max(0.0, cpu_seconds() - cpu_s0)
            oracle = scored["measurement"]["oracle"]
            stages.append(
                stage_record(
                    "cold_scoring",
                    t_score,
                    origin,
                    "evidence:score:" + (oracle.get("receipt_id") or "none")[-16:],
                    scoring_cpu,
                )
            )

            if isolation["hidden_markers_found"] or oracle.get("hidden_access_incident"):
                return finish("rejected", "hidden oracle access incident")
            if oracle.get("status") == "passed" and oracle.get("candidate_valid") is True:
                admitted_prod = bool((provider_receipt or {}).get("admitted_production"))
                if live and path_class == "production" and admitted_prod:
                    return finish("solved", "independent cold oracle passed on admitted production repair")
                if live and path_class == "production" and not admitted_prod:
                    return finish(
                        "unsolved",
                        "independent score passed but production admission is missing; not counting as solved",
                    )
                if live:
                    return finish(
                        "unsolved",
                        "live historical tasks require the admitted production path; "
                        f"requested path_class={path_class}",
                    )
                if path_class == "production" and not admitted_prod:
                    return finish("unavailable", "production admission missing; refusing solved")
                if path_class == "production" and admitted_prod:
                    return finish("solved", "independent cold oracle passed on admitted production unit")
                return finish("solved", "independent cold oracle passed on the development unit")
            if oracle.get("status") == "failed":
                return finish("unsolved", oracle.get("reason") or "independent oracle failed")
            if oracle.get("status") == "timed_out":
                return finish("timed_out", oracle.get("reason") or "independent scoring timed out")
            if oracle.get("status") == "unavailable":
                return finish("unavailable", oracle.get("reason") or "independent scoring unavailable")
            return finish("unsolved", oracle.get("reason") or "candidate not independently solved")
        except CrashAfter:
            raise
        except subprocess.TimeoutExpired:
            limit_triggered = "independent_cold_scoring_wall_seconds"
            return finish("timed_out", "independent scoring exceeded wall budget")
        except RunnerError as exc:
            return finish(exc.terminal, str(exc))
        except KeyboardInterrupt:
            return finish("cancelled", "keyboard interrupt")
        except Exception as exc:  # noqa: BLE001 — attempt boundary
            return finish("unavailable", f"{type(exc).__name__}: {exc}\n{traceback.format_exc(limit=2)}")
        finally:
            if not getattr(self.args, "keep_work", False):
                shutil.rmtree(work, ignore_errors=True)

    def _gateway_dispatch(
        self,
        *,
        task: dict[str, Any],
        path_class: str,
        files: Mapping[str, str],
        context: dict[str, Any],
        timeout: float,
    ) -> dict[str, Any]:
        gateway = load_gateway()
        request = {
            "task_id": task.get("task_id"),
            "family_id": task.get("family_id"),
            "path_class": path_class,
            "issue": task.get("issue") or {},
            "allowed_paths": list(task.get("allowed_paths") or (task.get("source_snapshot") or {}).get("admitted_paths") or files),
            "files": dict(files),
            "arm": context.get("arm"),
        }
        return gateway.dispatch(request, root=self.root, timeout=timeout)

    def _receipt_from_gateway(self, gw: Mapping[str, Any], *, path_class: str, effect_id: str) -> dict[str, Any]:
        return {
            "path_class": path_class,
            "simulated": False,
            "admitted_production": bool(gw.get("admitted_production")),
            "admitted_historical_development": bool(gw.get("admitted_historical_development")),
            **({"admitted_historical_pilot": bool(gw.get("admitted_historical_pilot"))} if gw.get("schema") == "paper-ns-host-historical-pilot/v1" else {}),
            **({"admitted_historical_final": bool(gw.get("admitted_historical_final")), "proposal_effect_count": gw.get("proposal_effect_count")} if gw.get("schema") == "paper-ns-host-historical-final/v1" else {}),
            "host_verified": gw.get("host_verified"),
            "dispatched": bool(gw.get("dispatched")),
            "dispatch_confirmed": bool(gw.get("dispatch_confirmed")),
            "logical_effect_id": effect_id,
            "served_provider": gw.get("served_provider"),
            "served_model": gw.get("served_model"),
            "served_revision": gw.get("served_revision"),
            "revision_availability_reason": gw.get("revision_availability_reason") or gw.get("reason"),
            "reasoning_effort": gw.get("reasoning_effort"),
            "runtime_receipt_id": gw.get("runtime_receipt_id") or ((gw.get("host_verified") or {}).get("response_sha256")),
            "usage_receipt_id": gw.get("usage_receipt_id"),
            "possibly_charged": bool(gw.get("possibly_charged")),
            "sampling_seed_supported": bool(gw.get("sampling_seed_supported")),
            "temperature_supported": bool(gw.get("temperature_supported")),
            "proposal_effect_count": int(gw.get("proposal_effect_count") or 0),
            "provider_cache_observed": gw.get("provider_cache_observed"),
            "unknown_effect": False,
            "replayed": False,
        }

    def _null_provider(self, path_class: str) -> dict[str, Any]:
        production = path_class == "production"
        probe = probe_production_provider(self.root) if production else None
        reason = None if not production else probe["revision_availability_reason"]
        if not production:
            reason = "No provider dispatched for this unit."
        return {
            "path_class": path_class,
            "simulated": path_class == "simulated",
            "admitted_production": False,
            "dispatched": False,
            "dispatch_confirmed": False,
            "logical_effect_id": None,
            "served_provider": None,
            "served_model": None,
            "served_revision": None,
            "revision_availability_reason": reason,
            "reasoning_effort": None,
            "runtime_receipt_id": None,
            "usage_receipt_id": None,
            "possibly_charged": False,
            "sampling_seed_supported": False if not production else probe["sampling_seed_supported"],
            "temperature_supported": False if not production else probe["temperature_supported"],
            "proposal_effect_count": 0,
            "provider_cache_observed": None,
            "unknown_effect": False,
            "replayed": False,
        }

    def _measurement_draft(self, **kw: Any) -> dict[str, Any]:
        task = kw["task"]
        snap = task.get("source_snapshot") or {}
        preimage = snap.get("snapshot_sha256") or sha256_json(task.get("files") or {"task": task["task_id"]})
        provider_receipt = kw["provider_receipt"] or self._null_provider(self.args.path)
        host = provider_receipt.get("host_verified")
        if host:
            preimage = host["receipt"]["source_sha256"]
        oracle = kw["oracle"]
        publication = kw["publication"]
        candidate = kw["candidate"]
        isolation = kw["isolation"]
        elapsed = max(0.0, time.perf_counter() - kw["origin"])
        cpu = max(0.0, cpu_seconds() - kw["cpu0"])
        rss = peak_rss_bytes()
        scratch = dir_size(kw["sandbox"])
        measures = empty_measurements()
        usage = self.provider_usage or {}
        if usage.get("prompt_tokens") is not None:
            measures["input_tokens"] = measurement(
                "actual", "tokens", value=int(usage["prompt_tokens"]), source="provider.usage"
            )
        if usage.get("completion_tokens") is not None:
            measures["output_tokens"] = measurement(
                "actual", "tokens", value=int(usage["completion_tokens"]), source="provider.usage"
            )
        details = usage.get("prompt_tokens_details") or {}
        if details.get("cached_tokens") is not None:
            measures["cached_input_tokens"] = measurement(
                "actual", "tokens", value=int(details["cached_tokens"]), source="provider.usage"
            )
        completion_details = usage.get("completion_tokens_details") or {}
        if completion_details.get("reasoning_tokens") is not None:
            measures["reasoning_tokens"] = measurement(
                "actual", "tokens", value=int(completion_details["reasoning_tokens"]), source="provider.usage"
            )
        if usage.get("cost_in_usd_ticks") is not None:
            measures["provider_charge"] = measurement(
                "unavailable",
                "currency",
                reason=(
                    "API reported cost_in_usd_ticks="
                    + str(usage.get("cost_in_usd_ticks"))
                    + " but that is not a settlement billing receipt."
                ),
            )
        measures["host_cpu_seconds"] = measurement("actual", "seconds", value=cpu, source="resource.getrusage")
        measures["peak_aggregate_memory_bytes"] = measurement(
            "actual", "bytes", value=rss, source="resource.ru_maxrss"
        )
        measures["scratch_bytes"] = measurement("actual", "bytes", value=scratch, source="du-sandbox")
        measures["retained_storage_bytes"] = measurement(
            "actual", "bytes", value=dir_size(self.ledger.path), source="du-ledger"
        )
        measures["bytes_read"] = measurement("actual", "bytes", value=self.evidence.bytes_read, source="evidence-log")
        measures["bytes_written"] = measurement("actual", "bytes", value=kw["bytes_written"], source="ledger-writes")
        measures["active_elapsed_seconds"] = measurement(
            "actual", "seconds", value=elapsed, source="time.perf_counter"
        )
        measures["queue_wait_seconds"] = measurement(
            "actual", "seconds", value=0, source="runner_process_had_no_queue"
        )
        measures["human_wait_seconds"] = measurement(
            "actual", "seconds", value=0, source="runner_process_had_no_human_channel"
        )
        measures["human_active_seconds"] = measurement(
            "actual", "seconds", value=0, source="runner_process_had_no_human_channel"
        )
        measures["independent_scoring_cpu_seconds"] = measurement(
            "actual", "seconds", value=kw["scoring_cpu"], source="resource.getrusage"
        )
        measures["independent_scoring_elapsed_seconds"] = measurement(
            "actual", "seconds", value=kw["scoring_elapsed"], source="time.perf_counter"
        )
        measures["prime_cpu_seconds"] = measurement(
            "actual", "seconds", value=kw["prime_cpu"], source="resource.getrusage"
        )
        measures["prime_elapsed_seconds"] = measurement(
            "actual", "seconds", value=kw["prime_elapsed"], source="time.perf_counter"
        )
        if host:
            # Local client resource counters do not measure remote provider/scorer work.
            for key, item in list(measures.items()):
                if key not in {"input_tokens", "output_tokens", "cached_input_tokens", "reasoning_tokens", "provider_charge"}:
                    measures[key] = measurement("unavailable", item["unit"], reason="Aggregate host proposal/review/scorer measurement is absent from the signed receipt; client counters are not a substitute.")
        candidate_kind = "none"
        candidate_id = None
        if candidate:
            candidate_kind = "generated_patch"
            candidate_id = "sha256:" + sha256_json(candidate)
        if host and candidate:
            candidate_id = "sha256:" + host["receipt"]["candidate_sha256"]
        admitted = None
        if kw["terminal"] == "solved":
            admitted = True
        elif candidate and kw["terminal"] in {"unsolved", "rejected"}:
            admitted = False
        elif publication.get("admitted") is True and kw["terminal"] != "solved":
            admitted = publication.get("admitted")
        if kw["terminal"] == "solved":
            admitted = True
        interpretation = [
            "NS028 fixed final A/B cold comparison; no A-D, routing, reuse or publication comparison claim." if host and kw["record_kind"] == "final" else "NS-026 runner/provider qualification; not a frozen final A-D scientific result.",
        ]
        if host:
            interpretation.append("Historical final A/B cold only; exact retained original eight families and two nested repetitions, fixed32 cells. Only signed reviewed scalar results are imported; no C/D, routing, reuse or publication comparison claim." if kw["record_kind"] == "final" else "Historical pilot A/B cold only; one exact operator grant and reviewed candidate within the frozen24-cell plan. Historical48 identities remain separately retained (8 retained,40 removed,16 added). One cell does not establish a paired result or final admission. Rescore verifies the signed result without another score." if kw["record_kind"] == "pilot" else "Historical development only, one operator grant and AI-reviewed candidate; no native campaign reservation, final-profile admission or adversarial scorer-integrity qualification. Rescore verifies the retained signed result without another score.")
        if not kw["live"]:
            interpretation.append(
                "Development/simulated path is not an admitted production repair and is excluded from live-repair denominators."
            )
        if not host and not self.semantic["imported"]:
            interpretation.append(
                f"semantic_state import unavailable ({self.semantic['reason']}); development AST pack is not the production semantic index."
            )
        if not self.container["docker_available"]:
            interpretation.append(self.container["reason"])
        identity = {
            "protocol_bundle_sha256": self.protocol["manifest"]["protocol_bundle_sha256"],
            "final_freeze_sha256": host["receipt"].get("final_freeze_sha256") if host and kw["record_kind"] == "final" else None,
            "task_id": task["task_id"],
            "family_id": task["family_id"],
            "source_preimage_id": preimage,
            "runner_source_id": self.runner_source_id,
            "oracle_manifest_id": self.oracle_manifest_sha256,
            "schedule_unit_id": kw["unit_id"],
            "arm": kw["arm"],
            "cache": kw["cache"],
            "repetition": kw["repetition"],
        }
        provider = {
            "dispatched": bool(provider_receipt.get("dispatched")),
            "logical_effect_id": provider_receipt.get("logical_effect_id"),
            "served_provider": provider_receipt.get("served_provider"),
            "served_model": provider_receipt.get("served_model"),
            "served_revision": provider_receipt.get("served_revision"),
            "revision_availability_reason": provider_receipt.get("revision_availability_reason"),
            "reasoning_effort": provider_receipt.get("reasoning_effort"),
            "runtime_receipt_id": provider_receipt.get("runtime_receipt_id"),
            "usage_receipt_id": provider_receipt.get("usage_receipt_id"),
            "possibly_charged": bool(provider_receipt.get("possibly_charged")),
            "sampling_seed_supported": bool(provider_receipt.get("sampling_seed_supported")),
            "temperature_supported": bool(provider_receipt.get("temperature_supported")),
            "proposal_effect_count": int(provider_receipt.get("proposal_effect_count") or 0),
            "provider_cache_observed": provider_receipt.get("provider_cache_observed"),
        }
        admission = {
            "attempted": candidate is not None,
            "admitted": admitted,
            "mandatory_evidence_current": bool(kw["terminal"] == "solved"),
            "scope_preserved": bool(isolation.get("scope_preserved")),
            "publication_required": bool(publication.get("required")),
            "publication_admitted": publication.get("admitted"),
            "publication_receipt_id": publication.get("receipt_id"),
            "current_parent_id": publication.get("parent_id"),
            "candidate_kind": candidate_kind,
            "candidate_artifact_id": candidate_id,
            "target_patch_exposed": False,
        }
        return {
            "schema": SCHEMA_MEASUREMENT,
            "record_kind": kw["record_kind"],
            "identity": identity,
            "terminal_state": kw["terminal"],
            "terminal_reason": kw["reason"],
            "scheduled": True,
            "started_at": kw["started_at"],
            "finished_at": utcnow(),
            "provider": provider,
            "oracle": oracle,
            "admission": admission,
            "measurements": measures,
            "stages": kw["stages"],
            "budget": {
                "serialized_request_bytes": (
                    (host["receipt"].get("request_binding") or {}).get("request_bytes") if host else len(canonical_dumps(kw.get("context") or {}).encode("utf-8"))
                    if kw.get("context")
                    else None
                ),
                "patch_bytes": (
                    host["receipt"].get("patch_bytes") if host else len(((candidate or {}).get("patch_text") or "").encode("utf-8"))
                    if candidate
                    else None
                ),
                "limit_triggered": kw["limit_triggered"],
                "observed_overshoot": {},
                "reconciliation_required": bool(provider_receipt.get("unknown_effect")),
            },
            "control": {
                "consumed_evidence_ids": list(self.evidence.ids),
                "next_action": "stop",
                "fallback_count": 0,
                "replan_count": 0,
                "manual_intervention_count": 0,
                "reuse_cold_disagreement": None,
                "reuse_credit": False if not reuse_credit_permitted() else None,
                "unsupported_reuse_profile_rejected": reject_unsupported_reuse_profile(),
            },
            "deviation_ids": [],
            "interpretation_limits": interpretation,
        }

    def _wrapper(
        self,
        *,
        command: str,
        path_class: str,
        task: dict[str, Any],
        unit_id: str,
        measurement: dict[str, Any],
        isolation: dict[str, Any],
        context: dict[str, Any],
        candidate: dict[str, Any] | None,
        provider_receipt: dict[str, Any],
        live: bool,
        resumed: bool,
        unknown_effect: bool,
        limit_triggered: str | None,
        sandbox_files: dict[str, str] | None = None,
    ) -> dict[str, Any]:
        snap = task.get("source_snapshot") or {}
        preimage = measurement["identity"]["source_preimage_id"] if provider_receipt.get("host_verified") else snap.get("snapshot_sha256") or measurement["identity"]["source_preimage_id"]
        campaign = self.ledger.campaign()
        hidden_in_proposal = bool(isolation.get("hidden_markers_found") or isolation.get("hidden_store_mounted"))
        return {
            "schema": SCHEMA_WRAPPER,
            "path_class": path_class,
            "measurement": measurement,
            "bindings": {
                "protocol_bundle_sha256": self.protocol["manifest"]["protocol_bundle_sha256"],
                "protocol_document_sha256": self.protocol["protocol_sha256"],
                "measurement_schema_sha256": self.protocol["schema_sha256"],
                "source_forest_sha256": self.source_forest_sha256,
                "oracle_manifest_sha256": self.oracle_manifest_sha256,
                "runner_source_id": self.runner_source_id,
                "task_id": task["task_id"],
                "family_id": task["family_id"],
                "source_preimage_id": preimage,
                "schedule_unit_id": unit_id,
                "evidence_ids": list(self.evidence.ids),
            },
            "provider_receipt": provider_receipt,
            "runner": {
                "interface": RUNNER_INTERFACE,
                "command": command,
                "ledger_id": sha256_text(str(self.ledger.path)),
                "isolation": isolation,
                "resource_enforcement": {
                    "request_serialized_bytes_max": int(self.budgets["request_serialized_bytes_max"]),
                    "admitted_patch_bytes_max": int(self.budgets["admitted_patch_bytes_max"]),
                    "provider_wall_seconds_max": float(self.budgets["provider_wall_seconds_max"]),
                    "active_unit_wall_seconds_max": float(self.budgets["active_unit_wall_seconds_max"]),
                    "process_rlimits_applied": self.rlimits,
                    "cgroup_available": bool(self.container["cgroup_available"]),
                    "docker_available": bool(self.container["docker_available"]),
                    "limit_triggered": limit_triggered,
                },
                "interruption": {
                    "resumed": resumed,
                    "duplicate_dispatch_prevented": resumed,
                    "unknown_effect_reconciled": unknown_effect,
                },
                "semantic_state_import": self.semantic,
                "container_enforcement": self.container,
                "campaign": {
                    "accounting_scope": "local_runner_ledger_only_excludes_distinct_operator_grant" if provider_receipt.get("host_verified") else "local_runner_ledger",
                    "operator_grant_sha256": ((provider_receipt.get("host_verified") or {}).get("receipt") or {}).get("grant_sha256"),
                    "operator_grant_provider_effect_count": provider_receipt.get("proposal_effect_count") if provider_receipt.get("host_verified") else None,
                    "provider_effects_reserved": campaign.get("provider_effects_reserved"),
                    "provider_effects_dispatched": campaign.get("provider_effects_dispatched"),
                    "provider_calls_for_unit": (campaign.get("provider_calls_by_effect") or {}).get(
                        provider_receipt.get("logical_effect_id") or ""
                    ),
                    "unknown_effects": list(campaign.get("unknown_effects") or []),
                },
                "proposal_context": {
                    "arm": context.get("arm") if context else None,
                    "routing": context.get("routing") if context else None,
                    "byte_length": context.get("byte_length") if context else None,
                    "admitted_paths": (context.get("context") or {}).get("admitted_paths") if context else None,
                    "issue_title": ((context.get("context") or {}).get("issue") or {}).get("title") if context else None,
                },
                "sandbox_files": proposal_safe_files(sandbox_files),
                "candidate": candidate,
                "live_repair_admitted": live,
                "hidden_oracle_in_proposal": hidden_in_proposal,
            },
        }

    def _publish(self, **kw: Any) -> dict[str, Any]:
        provider_receipt = kw["provider_receipt"] or self._null_provider(kw["path_class"])
        if kw.get("unknown_effect"):
            provider_receipt = dict(provider_receipt)
            provider_receipt["unknown_effect"] = True
            provider_receipt["possibly_charged"] = kw["path_class"] == "production"
            if kw["path_class"] == "production":
                provider_receipt["dispatched"] = True
                provider_receipt["dispatch_confirmed"] = False
                provider_receipt["proposal_effect_count"] = 1
        measurement = self._measurement_draft(
            task=kw["task"],
            arm=kw["arm"],
            cache=kw["cache"],
            repetition=kw["repetition"],
            record_kind=kw["record_kind"],
            unit_id=kw["unit_id"],
            started_at=kw["started_at"],
            live=kw["live"],
            candidate=kw["candidate"],
            publication=kw["publication"],
            provider_receipt=provider_receipt,
            oracle=kw["oracle"],
            isolation=kw["isolation"],
            limit_triggered=kw["limit_triggered"],
            origin=kw["origin"],
            cpu0=kw["cpu0"],
            stages=kw["stages"],
            prime_cpu=kw["prime_cpu"],
            prime_elapsed=kw["prime_elapsed"],
            scoring_cpu=kw["scoring_cpu"],
            scoring_elapsed=kw["scoring_elapsed"],
            bytes_written=kw["bytes_written"],
            sandbox=kw["sandbox"],
            terminal=kw["terminal"],
            reason=kw["reason"],
            context=kw.get("context"),
        )
        wrapper = self._wrapper(
            command=self.args.command,
            path_class=kw["path_class"],
            task=kw["task"],
            unit_id=kw["unit_id"],
            measurement=measurement,
            isolation=kw["isolation"],
            context=kw.get("context") or {},
            candidate=kw["candidate"],
            provider_receipt=provider_receipt,
            live=kw["live"],
            resumed=kw["resumed"],
            unknown_effect=kw["unknown_effect"],
            limit_triggered=kw["limit_triggered"],
            sandbox_files=kw.get("sandbox_files") or {},
        )
        self.ledger.put_internal(
            kw["unit_id"],
            {
                "logical_effect_id": kw.get("effect_id") or provider_receipt.get("logical_effect_id"),
                "path_class": kw["path_class"],
                "provider_receipt": provider_receipt if provider_receipt.get("dispatch_confirmed") else None,
                "candidate": kw["candidate"],
                "dispatch_confirmed": kw["dispatch_confirmed"],
                "published_attempt": wrapper,
            },
        )
        return wrapper


def run_one_task(args: argparse.Namespace) -> dict[str, Any]:
    executor = AttemptExecutor(args)
    attempt = executor.execute()
    if getattr(args, "out", None):
        out = Path(args.out)
        atomic_write(out, attempt)
    return attempt


def run_many(args: argparse.Namespace, specs: list[dict[str, Any]]) -> dict[str, Any]:
    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    rows = []
    for spec in specs:
        sub = argparse.Namespace(**{**vars(args), **spec})
        sub.out = str(out_dir / f"{sub.task_id}-{sub.arm}-{sub.cache}-{sub.repetition}.json")
        attempt = run_one_task(sub)
        if attempt.get("schema") == "paper-ns-host-handoff-pending/v1":
            rows.append({"task_id": sub.task_id, "arm": sub.arm, "path": sub.out, "status": "pending_operator", "terminal_state": None, "path_class": sub.path, "schedule_unit_id": attempt["schedule_unit_id"]})
            continue
        rows.append(
            {
                "task_id": sub.task_id,
                "arm": sub.arm,
                "path": sub.out,
                "terminal_state": attempt["measurement"]["terminal_state"],
                "path_class": attempt["path_class"],
                "schedule_unit_id": attempt["bindings"]["schedule_unit_id"],
            }
        )
    summary = {"schema": "paper-ns-runner-batch/v1", "command": args.command, "units": rows}
    atomic_write(out_dir / "summary.json", summary)
    return summary


def cmd_one_task(args: argparse.Namespace) -> int:
    args.command = "one-task"
    attempt = run_one_task(args)
    json.dump(attempt, sys.stdout, indent=2, sort_keys=True)
    sys.stdout.write("\n")
    return 75 if attempt.get("schema") == "paper-ns-host-handoff-pending/v1" else 0


def cmd_one_arm(args: argparse.Namespace) -> int:
    args.command = "one-arm"
    root = repo_root(Path(args.repo).resolve() if args.repo else None)
    specs: list[dict[str, Any]] = []
    if args.registry == "ns-006-boundary":
        specs.append(
            {
                "task_id": "ns-dev-boundary-add",
                "arm": args.arm,
                "cache": args.cache,
                "repetition": args.repetition,
                "scenario": "default",
            }
        )
    elif args.split:
        for row in iter_tasks(root, split=args.split, live_only=True):
            specs.append(
                {
                    "task_id": row["task_id"],
                    "arm": args.arm,
                    "cache": args.cache,
                    "repetition": args.repetition,
                    "scenario": "default",
                    "path": "production",
                }
            )
    else:
        raise RunnerError("one-arm requires --registry ns-006-boundary or --split")
    summary = run_many(args, specs)
    json.dump(summary, sys.stdout, indent=2, sort_keys=True)
    sys.stdout.write("\n")
    return 0


def cmd_paired(args: argparse.Namespace) -> int:
    args.command = "paired"
    root = repo_root(Path(args.repo).resolve() if args.repo else None)
    arms = [item.strip() for item in args.arms.split(",") if item.strip()]
    if args.family_id.startswith("ns-dev:"):
        task_id = "ns-dev-boundary-add"
        family = args.family_id
        ordered = arm_schedule_order(family, args.repetition, args.cache, arms)
        specs = [
            {
                "task_id": task_id,
                "arm": arm,
                "cache": args.cache,
                "repetition": args.repetition,
                "scenario": "default",
            }
            for arm in ordered
        ]
    else:
        live = list(iter_tasks(root, family_id=args.family_id, live_only=True))
        if not live:
            raise RunnerError(f"no live task for family {args.family_id}")
        task_id = live[0]["task_id"]
        ordered = arm_schedule_order(args.family_id, args.repetition, args.cache, arms)
        specs = [
            {
                "task_id": task_id,
                "arm": arm,
                "cache": args.cache,
                "repetition": args.repetition,
                "scenario": "default",
                "path": "production",
            }
            for arm in ordered
        ]
    summary = run_many(args, specs)
    json.dump(summary, sys.stdout, indent=2, sort_keys=True)
    sys.stdout.write("\n")
    return 0


def cmd_rescore(args: argparse.Namespace) -> int:
    scorer = Path(__file__).resolve().with_name("score_runs.py")
    import subprocess

    argv = [sys.executable, str(scorer), "--attempt", args.attempt, "--out", args.out]
    result = subprocess.run(argv, check=False)
    return int(result.returncode)


def add_shared_flags(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--repo", default=None, help="repository root; default: discover from this file")
    parser.add_argument("--ledger", required=True, help="durable attempt/effect directory")
    parser.add_argument("--arm", default="A", choices=list(ALL_ARMS))
    parser.add_argument("--cache", default="local_cold", choices=list(CACHE_PROFILES))
    parser.add_argument("--repetition", type=int, default=0)
    parser.add_argument("--record-kind", default="development", choices=list(RECORD_KINDS))
    parser.add_argument("--path", default="development", choices=list(PATH_CLASSES))
    parser.add_argument("--scenario", default="default")
    parser.add_argument("--crash-after", default=None, choices=["reserve", "provider"])
    parser.add_argument("--request-bytes-max", type=int, default=None)
    parser.add_argument("--patch-bytes-max", type=int, default=None)
    parser.add_argument("--provider-wall-seconds", type=float, default=None)
    parser.add_argument("--active-unit-wall-seconds", type=float, default=None)
    parser.add_argument("--keep-work", action="store_true")
    parser.add_argument(
        "--admitted-provider",
        action="store_true",
        help="dispatch through the frozen development amendment / production gateway instead of the NS-006 stub",
    )
    parser.add_argument(
        "--upstream-store",
        default=None,
        help="pinned upstream tarball cache; default: qualification/production_provider/upstream_store",
    )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)

    one = sub.add_parser("one-task", help="run one scheduled unit")
    add_shared_flags(one)
    one.add_argument("--task-id", required=True)
    one.add_argument("--out", required=True)
    one.set_defaults(func=cmd_one_task)

    arm = sub.add_parser("one-arm", help="run one arm across a registry or split")
    add_shared_flags(arm)
    arm.add_argument("--registry", default=None)
    arm.add_argument("--split", default=None)
    arm.add_argument("--out-dir", required=True)
    arm.set_defaults(func=cmd_one_arm)

    paired = sub.add_parser("paired", help="run matched arms for one family")
    add_shared_flags(paired)
    paired.add_argument("--family-id", required=True)
    paired.add_argument("--arms", default="A,B,C,D")
    paired.add_argument("--out-dir", required=True)
    paired.set_defaults(func=cmd_paired)

    rescore = sub.add_parser("rescore", help="independently rescore an attempt")
    rescore.add_argument("--attempt", required=True)
    rescore.add_argument("--out", required=True)
    rescore.add_argument("--ledger", default=None)
    rescore.set_defaults(func=cmd_rescore)
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    if getattr(args, "crash_after", None) == "None":
        args.crash_after = None
    try:
        return int(args.func(args))
    except CrashAfter as exc:
        print(canonical_dumps({"schema": "paper-ns-runner-interrupt/v1", "reason": str(exc)}), file=sys.stderr)
        return 75
    except RunnerError as exc:
        print(f"run_comparison: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
