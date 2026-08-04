#!/usr/bin/env python3
"""Operate isolated supervisor lanes for proof-backed test reuse."""

from __future__ import annotations

import argparse
import fcntl
import hashlib
import importlib.util
import json
import os
import shlex
import shutil
import signal
import subprocess
import sys
import tempfile
import time
from collections.abc import Iterator, Mapping, Sequence
from contextlib import contextmanager
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
ACCEL_ROOT = REPO_ROOT / "external" / "ipfs_accelerate"
DATASETS_ROOT = REPO_ROOT / "external" / "ipfs_datasets"
KIT_ROOT = REPO_ROOT / "external" / "ipfs_kit"
CONFIG_PATH = REPO_ROOT / "config" / "proof_backed_test_reuse_supervisor.json"
GROK_CODEX_PROVIDER_POLICIES = frozenset(
    {
        "grok-codex",
        "grok_codex",
        "grok->codex",
        "grok→codex",
        "grok-then-codex",
        "grok_then_codex",
    }
)
LIVE_SUPERVISOR_STATUSES = frozenset(
    {
        "running",
        "agentic_maintenance_started",
        "agentic_maintenance_completed",
    }
)


def _load_config() -> dict[str, object]:
    return json.loads(CONFIG_PATH.read_text(encoding="utf-8"))


CONFIG = _load_config()
PLAN_REL = str(CONFIG["planPath"])
OBJECTIVE_REL = str(CONFIG["objectivePath"])
TODO_REL = str(CONFIG["todoPath"])
VALIDATOR_REL = str(CONFIG["validatorPath"])
CONTROLLER_REL = str(CONFIG["controllerPath"])
TARGET_BRANCH = str(CONFIG["integrationBranch"])
TASK_PREFIX = str(CONFIG["taskPrefix"])
PARALLEL = dict(CONFIG["parallelRuntime"])
PROVIDER_POLICY = dict(CONFIG["providerPolicy"])
PRIMARY_PROVIDER_POLICY = dict(PROVIDER_POLICY["primary"])
FALLBACK_PROVIDER_POLICY = dict(PROVIDER_POLICY["fallback"])
MERGE_RESOLVER_COMMAND_ENV = (
    "IPFS_ACCELERATE_AGENT_LLM_MERGE_RESOLVER_COMMAND"
)
PROVIDER_FALLBACK_RUNNER = (
    ACCEL_ROOT
    / "ipfs_accelerate_py"
    / "agent_supervisor"
    / "provider_fallback_runner.py"
)
GROK_CLI_RUNNER = (
    ACCEL_ROOT
    / "ipfs_accelerate_py"
    / "agent_supervisor"
    / "grok_cli_runner.py"
)

state_override = os.environ.get(str(CONFIG["stateRootEnvironment"]), "").strip()
if state_override:
    STATE_ROOT = Path(state_override).expanduser().resolve()
else:
    state_base = Path(
        os.environ.get("XDG_STATE_HOME", str(Path.home() / ".local" / "state"))
    )
    STATE_ROOT = (state_base / str(CONFIG["defaultStateRootSuffix"])).resolve()

STATE_DIR = STATE_ROOT / "state"
RUNTIME_DIR = STATE_ROOT / "runtime"
LOG_DIR = STATE_ROOT / "logs"
PROJECTION_DIR = STATE_ROOT / "projection"
WORKTREE_DIR = STATE_ROOT / "worktrees"
MERGE_QUEUE_DIR = STATE_ROOT / "merge-queue"
CONTROL_LOCK = STATE_ROOT / "control.lock"
LANES = tuple(
    {
        "name": f"ptr_lane_{index}",
        "shard": index,
        "provider": str(PARALLEL["providers"][index]),
        "primary_provider": (
            "grok"
            if str(PARALLEL["providers"][index])
            in GROK_CODEX_PROVIDER_POLICIES
            else str(PARALLEL["providers"][index])
        ),
        "fallback_provider": (
            "codex"
            if str(PARALLEL["providers"][index])
            in GROK_CODEX_PROVIDER_POLICIES
            else ""
        ),
        "primary_model": str(PRIMARY_PROVIDER_POLICY["model"]),
        "fallback_model": str(FALLBACK_PROVIDER_POLICY["model"]),
        "fallback_model_reasoning_effort": str(
            FALLBACK_PROVIDER_POLICY["modelReasoningEffort"]
        ),
        "fallback_trigger": str(PROVIDER_POLICY["fallbackTrigger"]),
    }
    for index in range(int(PARALLEL["laneCount"]))
)


def _managed_merge_resolver_command() -> str:
    """Build the profile-owned semantic merge resolver provider chain.

    The generic implementation daemon defaults its merge resolver to a direct
    Codex invocation.  That is incompatible with this profile's Grok-primary,
    quota-only fallback contract, so both the supervisor CLI and its runtime
    environment receive this exact no-shell provider runner command.
    """

    grok_binary = shutil.which("grok") or "grok"
    codex_binary = shutil.which("codex") or "codex"
    # invoke_llm_resolver starts this command in the conflicted repository.
    # Keeping the workspace relative preserves that exact target for both
    # main-checkout and isolated-worktree semantic repairs.
    resolver_workspace = "."
    primary_command = [
        sys.executable,
        str(GROK_CLI_RUNNER),
        "--workspace",
        resolver_workspace,
        "--grok-bin",
        grok_binary,
        "--model",
        str(PRIMARY_PROVIDER_POLICY["model"]),
        "--max-turns",
        "100000",
        "--mode",
        "agent",
    ]
    fallback_command = [
        codex_binary,
        "exec",
        "--dangerously-bypass-approvals-and-sandbox",
        "-C",
        resolver_workspace,
        "-m",
        str(FALLBACK_PROVIDER_POLICY["model"]),
        "-c",
        "model_reasoning_effort=\""
        + str(FALLBACK_PROVIDER_POLICY["modelReasoningEffort"])
        + "\"",
        "-",
    ]
    command = [
        sys.executable,
        str(PROVIDER_FALLBACK_RUNNER),
        "--workspace",
        resolver_workspace,
        "--primary-provider",
        str(PRIMARY_PROVIDER_POLICY["provider"]),
        "--fallback-provider",
        str(FALLBACK_PROVIDER_POLICY["provider"]),
        "--primary-command-json",
        json.dumps(primary_command, separators=(",", ":")),
        "--fallback-command-json",
        json.dumps(fallback_command, separators=(",", ":")),
        "--fallback-policy",
        str(PROVIDER_POLICY["fallbackTrigger"]),
    ]
    return shlex.join(command)


def _runtime_environment(provider: str | None = None) -> dict[str, str]:
    environment = dict(os.environ)
    # This dedicated profile owns its provider chain.  The implementation
    # daemon otherwise gives this generic escape hatch precedence over the
    # configured Grok primary and quota-only Codex fallback.
    environment.pop("IMPLEMENTATION_DAEMON_COMMAND", None)
    python_paths = [str(ACCEL_ROOT), str(DATASETS_ROOT), str(KIT_ROOT)]
    if environment.get("PYTHONPATH"):
        python_paths.append(environment["PYTHONPATH"])
    environment["PYTHONPATH"] = os.pathsep.join(python_paths)
    for key, value in dict(PARALLEL["commonEnvironment"]).items():
        environment[str(key)] = str(value)
    # Never inherit or configure the generic direct-Codex semantic merge
    # resolver.  The dedicated profile's managed chain wins last.
    environment[MERGE_RESOLVER_COMMAND_ENV] = (
        _managed_merge_resolver_command()
    )
    dependency_state = STATE_ROOT / "dependencies"
    environment["IPFS_TEST_PROOF_REUSE_NLTK_DATA_DIR"] = str(
        dependency_state / "nltk-data"
    )
    environment["IPFS_TEST_PROOF_REUSE_PROVISION_DIR"] = str(
        dependency_state / "provisioning"
    )
    environment["IPFS_ACCELERATE_AGENT_GROK_MODEL"] = str(
        PRIMARY_PROVIDER_POLICY["model"]
    )
    environment["IPFS_ACCELERATE_AGENT_CODEX_MODEL"] = str(
        FALLBACK_PROVIDER_POLICY["model"]
    )
    environment["IPFS_ACCELERATE_AGENT_CODEX_REASONING_EFFORT"] = str(
        FALLBACK_PROVIDER_POLICY["modelReasoningEffort"]
    )
    environment["IPFS_ACCELERATE_AGENT_PROVIDER_FALLBACK_POLICY"] = str(
        PROVIDER_POLICY["fallbackTrigger"]
    )
    if provider:
        environment["IPFS_ACCELERATE_AGENT_IMPLEMENTATION_PROVIDER"] = provider
        if (
            provider == "grok-build"
            or provider in GROK_CODEX_PROVIDER_POLICIES
        ):
            grok_binary = shutil.which("grok")
            if grok_binary:
                environment["IPFS_ACCELERATE_AGENT_GROK_BIN"] = grok_binary
    return environment


def _prepare_state_dirs() -> None:
    old_umask = os.umask(0o077)
    try:
        for path in (
            STATE_DIR,
            RUNTIME_DIR,
            LOG_DIR,
            PROJECTION_DIR / "discovery",
            PROJECTION_DIR / "bundles",
            PROJECTION_DIR / "datasets",
            WORKTREE_DIR,
            MERGE_QUEUE_DIR,
            STATE_DIR / "preflight" / "board",
            STATE_DIR / "preflight" / "reconciliation",
            WORKTREE_DIR / "preflight",
        ):
            path.mkdir(parents=True, exist_ok=True)
        for lane in LANES:
            (STATE_DIR / lane["name"]).mkdir(parents=True, exist_ok=True)
            (WORKTREE_DIR / lane["name"]).mkdir(parents=True, exist_ok=True)
            (
                STATE_DIR
                / "preflight"
                / "reconciliation"
                / lane["name"]
            ).mkdir(parents=True, exist_ok=True)
    finally:
        os.umask(old_umask)


@contextmanager
def _control_lock() -> Iterator[None]:
    _prepare_state_dirs()
    with CONTROL_LOCK.open("a+", encoding="utf-8") as handle:
        try:
            fcntl.flock(handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError as exc:
            raise RuntimeError(
                f"another PTR control operation owns {CONTROL_LOCK}"
            ) from exc
        yield


def _run(
    command: Sequence[str],
    *,
    environment: dict[str, str] | None = None,
    check: bool = True,
    timeout: int = 300,
) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        list(command),
        cwd=REPO_ROOT,
        env=environment or _runtime_environment(),
        check=check,
        text=True,
        capture_output=True,
        timeout=timeout,
    )


def _git_output(*arguments: str, cwd: Path = REPO_ROOT) -> str:
    result = subprocess.run(
        ["git", *arguments],
        cwd=cwd,
        check=True,
        text=True,
        capture_output=True,
        timeout=120,
    )
    return result.stdout.strip()


def _git_raw_output(*arguments: str, cwd: Path = REPO_ROOT) -> str:
    result = subprocess.run(
        ["git", *arguments],
        cwd=cwd,
        check=True,
        text=True,
        capture_output=True,
        timeout=120,
    )
    return result.stdout


def _initialize_configured_submodules() -> tuple[str, ...]:
    """Register only configured submodules without fetching or checking out."""

    paths = tuple(str(item) for item in PARALLEL["worktreeSubmodulePaths"])
    result = subprocess.run(
        ["git", "submodule", "init", "--", *paths],
        cwd=REPO_ROOT,
        check=False,
        text=True,
        capture_output=True,
        timeout=120,
    )
    if result.returncode != 0:
        raise RuntimeError(
            "could not initialize configured submodule metadata: "
            + (result.stderr.strip() or result.stdout.strip())
        )
    return paths


def _require_isolated_clean_checkout() -> dict[str, object]:
    branch = _git_output("branch", "--show-current")
    if branch != TARGET_BRANCH:
        raise RuntimeError(
            f"refusing branch {branch!r}; expected {TARGET_BRANCH!r}"
        )
    _initialize_configured_submodules()
    dirty = _git_output("status", "--porcelain=v1", "--untracked-files=all")
    if dirty:
        raise RuntimeError(f"refusing dirty integration checkout:\n{dirty}")
    submodule_status = _git_raw_output(
        "submodule",
        "status",
        *[str(item) for item in PARALLEL["worktreeSubmodulePaths"]],
    )
    bad_lines = [
        line
        for line in submodule_status.splitlines()
        if not line or line[0] != " "
    ]
    if bad_lines:
        raise RuntimeError(
            "submodule gitlinks are not exact/initialized: " + repr(bad_lines)
        )
    submodules: dict[str, str] = {}
    for relative in PARALLEL["worktreeSubmodulePaths"]:
        relative_text = str(relative)
        submodule_root = REPO_ROOT / relative_text
        submodule_dirty = _git_output(
            "status",
            "--porcelain=v1",
            "--untracked-files=all",
            cwd=submodule_root,
        )
        if submodule_dirty:
            raise RuntimeError(
                f"refusing dirty submodule {relative_text}:\n{submodule_dirty}"
            )
        submodules[relative_text] = _git_output("rev-parse", "HEAD", cwd=submodule_root)
    return {
        "branch": branch,
        "commit": _git_output("rev-parse", "HEAD"),
        "tree": _git_output("rev-parse", "HEAD^{tree}"),
        "submodules": submodules,
    }


def _proof_reuse_capability_discovery() -> dict[str, object]:
    """Return inert shadow-mode capability and dependency-plan reports."""

    original_sys_path = list(sys.path)
    for root in reversed((ACCEL_ROOT, DATASETS_ROOT, KIT_ROOT)):
        root_text = str(root)
        if root_text not in sys.path:
            sys.path.insert(0, root_text)
    discovery_environment = _runtime_environment()
    discovery_environment.update(
        {
            "IPFS_TEST_PROOF_REUSE_MODE": "shadow",
            "IPFS_TEST_PROOF_REUSE_AUTO_INSTALL": "0",
            "IPFS_TEST_PROOF_REUSE_DATASETS_SOURCE": str(DATASETS_ROOT),
            "IPFS_DATASETS_AUTO_INSTALL": "false",
            "IPFS_AUTO_INSTALL": "false",
            "IPFS_DATASETS_PY_AUTO_GROTH16_BUILD": "0",
            "IPFS_DATASETS_PY_AUTO_NLTK_DOWNLOAD": "0",
            "IPFS_DATASETS_PY_INCLUDE_VCS_DEPENDENCIES": "0",
        }
    )
    policy = {
        "mode": "shadow",
        "environment_is_copy": True,
        "automatic_install_enabled": False,
        "installer_invoked": False,
        "process_started": False,
        "network_attempted": False,
        "cache_created": False,
        "completion_authority": False,
    }
    try:
        try:
            from ipfs_accelerate_py.agent_supervisor.integrations.test_reuse_capabilities import (
                TestReuseCapabilityProbe,
            )

            capability_report = TestReuseCapabilityProbe(
                environ=discovery_environment
            ).probe().to_dict()
        except Exception as exc:
            capability_report = {
                "schema_version": "TestReuseCapabilityReport@1",
                "mode": "shadow",
                "available": False,
                "reason_code": "capability_probe_unavailable",
                "error_kind": type(exc).__name__,
                "side_effect_free": True,
                "network_attempted": False,
                "daemon_started": False,
                "cache_created": False,
                "unavailable_is_non_blocking": True,
            }

        try:
            from ipfs_accelerate_py.testing.proof_reuse.services import (
                proof_reuse_dependency_plan,
            )

            dependency_plan = proof_reuse_dependency_plan(
                discovery_environment
            )
        except Exception as exc:
            dependency_plan = {
                "interface": "ProofReuseDependencyPlan@1",
                "available": False,
                "reason_code": "dependency_plan_unavailable",
                "error_kind": type(exc).__name__,
                "lazy": True,
                "cold_import_inert": True,
                "automatic_install_enabled": False,
                "external_capability_absence_action": "run",
            }
    finally:
        sys.path[:] = original_sys_path

    return {
        "discovery_policy": policy,
        "capability_report": capability_report,
        "dependency_plan": dependency_plan,
    }


def _provider_preflight() -> dict[str, object]:
    try:
        import duckdb  # type: ignore
    except ImportError as exc:
        raise RuntimeError("Python cannot import required DuckDB") from exc
    codex_binary = shutil.which("codex")
    grok_binary = shutil.which("grok")
    if not grok_binary:
        raise RuntimeError(
            "Grok CLI is required as the PTR supervisor primary provider; "
            "Codex fallback is permitted only after confirmed Grok quota "
            "exhaustion"
        )
    if not codex_binary:
        raise RuntimeError(
            "Codex CLI is required as the PTR supervisor fallback provider"
        )
    codex_status = _run(
        [codex_binary, "login", "status"],
        environment=_runtime_environment(),
        timeout=30,
    )
    if "logged in" not in (codex_status.stdout + codex_status.stderr).lower():
        raise RuntimeError(
            "Codex fallback CLI did not report an authenticated session"
        )

    try:
        grok_version = _run(
            [grok_binary, "--version"],
            environment=_runtime_environment(),
            check=False,
            timeout=30,
        )
    except (OSError, subprocess.SubprocessError) as exc:
        raise RuntimeError(
            "Grok primary CLI could not execute during preflight"
        ) from exc
    grok_version_text = (grok_version.stdout + grok_version.stderr).strip()
    if grok_version.returncode != 0:
        raise RuntimeError(
            "Grok primary CLI --version failed during preflight: "
            + (grok_version_text or f"exit {grok_version.returncode}")
        )

    if str(ACCEL_ROOT) not in sys.path:
        sys.path.insert(0, str(ACCEL_ROOT))
    try:
        from ipfs_accelerate_py.agent_supervisor.todo_daemon.implementation_daemon import (  # noqa: E501
            _grok_cli_available,
        )

        grok_authenticated = bool(_grok_cli_available())
    except Exception:
        grok_authenticated = False
    if not grok_authenticated:
        raise RuntimeError(
            "Grok primary CLI did not report headless authentication; "
            "Codex fallback is not allowed for authentication failures"
        )

    optional = {
        "multiformats": importlib.util.find_spec("multiformats") is not None,
        "datasets_zkp": (
            DATASETS_ROOT / "ipfs_datasets_py" / "logic" / "zkp"
        ).is_dir(),
        "groth16_endpoint_configured": bool(
            os.environ.get("IPFS_DATASETS_GROTH16_ENDPOINT", "").strip()
        ),
        "provekit_binary": shutil.which("provekit") or "",
        "ipfs_binary": shutil.which("ipfs") or "",
        "snarkjs_binary": shutil.which("snarkjs") or "",
    }
    proof_reuse_discovery = _proof_reuse_capability_discovery()
    return {
        "python": sys.executable,
        "duckdb": duckdb.__version__,
        "codex": codex_binary,
        "codex_status": (codex_status.stdout + codex_status.stderr).strip(),
        "grok": grok_binary or "",
        "grok_version": grok_version_text,
        "grok_authenticated": grok_authenticated,
        "provider_policy": {
            "primary": {
                "provider": str(PRIMARY_PROVIDER_POLICY["provider"]),
                "model": str(PRIMARY_PROVIDER_POLICY["model"]),
            },
            "fallback": {
                "provider": str(FALLBACK_PROVIDER_POLICY["provider"]),
                "model": str(FALLBACK_PROVIDER_POLICY["model"]),
                "model_reasoning_effort": str(
                    FALLBACK_PROVIDER_POLICY["modelReasoningEffort"]
                ),
            },
            "fallback_trigger": str(PROVIDER_POLICY["fallbackTrigger"]),
            "primary_unavailable_action": str(
                PROVIDER_POLICY["primaryUnavailableAction"]
            ),
            "non_quota_failure_action": str(
                PROVIDER_POLICY["nonQuotaFailureAction"]
            ),
            "applies_to": list(PROVIDER_POLICY["appliesTo"]),
            "semantic_merge_resolver": dict(
                PARALLEL["semanticMergeResolver"]
            ),
            "fallback_forbidden_on": list(
                PROVIDER_POLICY["fallbackForbiddenOn"]
            ),
        },
        "optional_non_blocking_capabilities": optional,
        "test_reuse_discovery_policy": proof_reuse_discovery[
            "discovery_policy"
        ],
        "test_reuse_capability_report": proof_reuse_discovery[
            "capability_report"
        ],
        "proof_reuse_dependency_plan": proof_reuse_discovery[
            "dependency_plan"
        ],
    }


def _validate_board(*, persist_projection: bool = True) -> dict[str, object]:
    result = _run(
        [sys.executable, str(REPO_ROOT / VALIDATOR_REL)],
        environment=_runtime_environment(),
        timeout=180,
    )
    payload = json.loads(result.stdout)
    if payload.get("valid") is not True:
        raise RuntimeError("PTR board validator did not report valid")
    if persist_projection:
        (PROJECTION_DIR / "native_board_preflight.json").write_text(
            json.dumps(payload, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
    return payload


def _required_closeout_artifact_presence() -> dict[str, object]:
    """Project configured artifact presence without claiming authority."""

    configured = {
        "gate": _completion_state_path("gatePathSuffix"),
        "evidence": _completion_state_path("evidencePathSuffix"),
    }
    artifacts = {
        name: {
            "path": str(path),
            "present": path.is_file(),
        }
        for name, path in configured.items()
    }
    missing = [
        name for name, item in artifacts.items() if not item["present"]
    ]
    return {
        "required_artifacts": artifacts,
        "missing_required_artifacts": missing,
        "artifact_presence_ready": not missing,
        "artifact_presence_is_completion_authority": False,
    }


def _git_commit_is_ancestor(commit: str) -> bool:
    """Return whether *commit* is in the current integration history."""

    if not commit.strip():
        return False
    result = subprocess.run(
        ["git", "merge-base", "--is-ancestor", commit, "HEAD"],
        cwd=REPO_ROOT,
        check=False,
        text=True,
        capture_output=True,
        timeout=120,
    )
    return result.returncode == 0


def _record_identifier(
    record: Mapping[str, object], *names: str
) -> str:
    for name in names:
        value = record.get(name)
        if value is not None and str(value).strip():
            return str(value).strip()
    return ""


def _record_population(
    value: object,
    *,
    id_names: Sequence[str],
) -> set[str]:
    """Extract identifiers from a retained list or keyed population."""

    if isinstance(value, Mapping):
        return {str(item).strip() for item in value if str(item).strip()}
    if not isinstance(value, Sequence) or isinstance(value, (str, bytes)):
        return set()
    found: set[str] = set()
    for item in value:
        if isinstance(item, Mapping):
            identifier = _record_identifier(item, *id_names)
        else:
            identifier = str(item).strip()
        if identifier:
            found.add(identifier)
    return found


def _managed_merge_input_inventory(
    tasks: Sequence[object],
) -> dict[str, object]:
    """Inventory usable historical merge candidates without granting authority."""

    task_cids = {
        str(getattr(task, "task_id", "")): str(
            getattr(task, "canonical_task_cid", "")
        )
        for task in tasks
        if str(getattr(task, "task_id", "")).strip()
    }
    latest: dict[str, tuple[float, Mapping[str, object]]] = {}
    completed_dir = MERGE_QUEUE_DIR / "completed"
    for path in sorted(completed_dir.glob("*.json")):
        record = _load_json(path)
        task_id = _record_identifier(record, "task_id")
        if task_id not in task_cids:
            continue
        try:
            order = float(record.get("enqueued_at") or path.stat().st_mtime)
        except (OSError, TypeError, ValueError):
            order = 0.0
        prior = latest.get(task_id)
        if prior is None or order > prior[0]:
            latest[task_id] = (order, record)

    accepted: set[str] = set()
    rejected: dict[str, str] = {}
    for task_id, (_order, record) in sorted(latest.items()):
        status = _record_identifier(record, "status", "state").lower()
        claimed_cid = _record_identifier(
            record,
            "task_cid",
            "canonical_task_cid",
            "canonical_task_id",
        )
        commit = _record_identifier(
            record, "merged_commit_id", "commit_sha", "commit_id"
        )
        if status not in {"completed", "merged"}:
            rejected[task_id] = "merge_not_completed"
        elif claimed_cid != task_cids[task_id]:
            rejected[task_id] = "canonical_task_cid_mismatch"
        elif not commit:
            rejected[task_id] = "merged_commit_missing"
        elif not _git_commit_is_ancestor(commit):
            rejected[task_id] = "merged_commit_not_current_ancestor"
        else:
            accepted.add(task_id)

    expected = set(task_cids)
    return {
        "source_directory": str(completed_dir),
        "required_count": len(expected),
        "observed_record_task_count": len(latest),
        "usable_candidate_count": len(accepted),
        "usable_candidate_task_ids": sorted(accepted),
        "missing_candidate_task_ids": sorted(expected - accepted),
        "rejected_candidates": dict(sorted(rejected.items())),
        "current_head_ancestry_checked": True,
        "historical_merge_candidate_is_current_tree_validation": False,
        "presence_is_completion_authority": False,
    }


def _inventory_requirement(
    *,
    stage: str,
    name: str,
    expected_ids: Sequence[str] = (),
    expected_count: int | None = None,
    observed_ids: Sequence[str] = (),
    observed_count: int | None = None,
    source: str = "not_configured",
) -> dict[str, object]:
    expected = tuple(sorted({str(item) for item in expected_ids if str(item)}))
    observed = tuple(sorted({str(item) for item in observed_ids if str(item)}))
    required_count = len(expected) if expected_count is None else expected_count
    if expected:
        matched = tuple(sorted(set(expected) & set(observed)))
        missing_ids = tuple(sorted(set(expected) - set(observed)))
        unexpected_ids = tuple(sorted(set(observed) - set(expected)))
        present_count = len(matched)
        missing_count = len(missing_ids)
    else:
        matched = observed
        missing_ids = ()
        unexpected_ids = ()
        present_count = len(observed) if observed_count is None else observed_count
        missing_count = max(0, required_count - present_count)
    result: dict[str, object] = {
        "stage": stage,
        "name": name,
        "required_count": required_count,
        "present_count": present_count,
        "missing_count": missing_count,
        "source": source,
        "presence_is_completion_authority": False,
    }
    if expected:
        result["required_ids"] = list(expected)
        result["present_ids"] = list(matched)
        result["missing_ids"] = list(missing_ids)
        result["unexpected_ids"] = list(unexpected_ids)
    return result


def _closeout_production_input_inventory(
    tasks: Sequence[object] | None = None,
) -> dict[str, object]:
    """Describe every retained input still needed by PTR-110/111/120/122.

    Presence inventory is owned by the agent supervisor
    (``proof_test_reuse_closeout_autorecover.inventory_closeout_inputs``).
    This wrapper supplies monorepo paths and attaches runtime-activation
    diagnostics that remain monorepo-local.
    """

    if str(ACCEL_ROOT) not in sys.path:
        sys.path.insert(0, str(ACCEL_ROOT))
    from ipfs_accelerate_py.agent_supervisor.todo_daemon.implementation_daemon import (
        parse_task_file,
    )
    from ipfs_accelerate_py.agent_supervisor.validation.proof_test_reuse_closeout_autorecover import (
        inventory_closeout_inputs,
    )
    from ipfs_accelerate_py.agent_supervisor.validation.proof_test_reuse_goal_evidence import (
        goal_requirements_by_id,
        load_objective_goals,
    )

    parsed_tasks = tuple(tasks or parse_task_file(REPO_ROOT / TODO_REL, TASK_PREFIX))
    task_ids = tuple(
        sorted(str(getattr(task, "task_id", "")) for task in parsed_tasks)
    )
    goals = load_objective_goals(REPO_ROOT / OBJECTIVE_REL)
    goal_ids = tuple(sorted(goal.goal_id for goal in goals))
    requirement_ids = tuple(
        sorted(
            {
                requirement
                for values in goal_requirements_by_id(goals).values()
                for requirement in values
            }
        )
    )
    gate_path = _completion_state_path("gatePathSuffix")
    evidence_path = _completion_state_path("evidencePathSuffix")
    inventory = inventory_closeout_inputs(
        state_root=STATE_ROOT,
        task_ids=task_ids,
        goal_ids=goal_ids,
        requirement_ids=requirement_ids,
        merge_completed_dir=MERGE_QUEUE_DIR / "completed",
        approval_dir=STATE_ROOT / "projection" / "completion" / "operator_approvals",
        gate_path=gate_path,
        evidence_path=evidence_path,
    )
    inventory["managed_merge_history"] = _managed_merge_input_inventory(parsed_tasks)
    inventory["authoritative_materializer"] = {
        "configured": True,
        "module": (
            "ipfs_accelerate_py.agent_supervisor.validation."
            "proof_test_reuse_closeout_autorecover"
        ),
        "required_call_sequence": [
            "run_closeout_autorecover_cycle",
            "PTR-110 ProofTestReuseTaskEvidenceCollector.collect",
            "PTR-111 GoalAssuranceRunner.collect",
            "PTR-120 ProofTestReuseObjectiveEvidenceAssembler.assemble",
            "PTR-122 ProofTestReuseCurrentTreeGate.evaluate",
            "PTR-122 ProofTestReuseCurrentTreeGate.persist_bundle",
        ],
        "may_synthesize_approvals": False,
        "may_treat_task_status_as_authority": False,
        "auto_repair_kinds": [
            "validation_receipt_freshness_refresh",
            "managed_merge_git_recovery",
            "managed_merge_recovery_persist",
            "contradictory_approval_merge_strip",
            "task_evidence_rematerialize",
            "goal_coverage_projection",
            "objective_evidence_assemble",
            "inventory_recompute",
        ],
    }
    # Runtime activation remains intentionally fail-closed; presence inventory
    # never promotes production warm-skip authority.
    inventory["runtime_reuse_activation"] = {
        "automatic_plugin_discovery": True,
        "ordinary_enabled_run_effective_action": "run_test",
        "default_identity_services_injected": False,
        "default_identity_service_factory_configured": False,
        "production_identity_injector_configured": False,
        "missing_production_providers": [
            "repository_forest_provider",
            "analysis_index_provider",
            "component_inputs_provider",
            "policy_inputs_provider",
            "runtime_evidence_provider",
        ],
        "candidate_context_store_configured": False,
        "two_stage_candidate_revalidation_configured": False,
        "lookup_requires_exact_execution_key_before_candidate_read": True,
        "runtime_trace_attribute_producer_configured": False,
        "post_pass_runtime_trace_capture_configured": False,
        "post_pass_receipt_requires_runtime_trace": False,
        "deferred_request_builder_configured": False,
        "deferred_request_transport_compatible": False,
        "deferred_certificate_issuer_configured": False,
        "issuer_in_lazy_service_bundle": False,
        "issuer_in_lazy_service_resolution": False,
        "candidate_certificate_publication_configured": False,
        "authoritative_candidate_publication_configured": False,
        "receipt_content_identity_profiles_conformant": False,
        "receipt_content_identity_gap": (
            "accelerator_cidv1_dag_json_vs_datasets_sha256"
        ),
        "receipt_content_identity_profiles": {
            "accelerator": "cidv1-base32-dag-json-sha2-256",
            "datasets_statement": "sha256-canonical-json-v1",
            "exact_conformance": False,
        },
        "ordinary_warm_skip_path_complete": False,
        "missing_activation_action": "run_test",
        "implementation_gap_is_completion_authority": False,
        "activation_blocker_codes": [
            "identity_services_unconfigured",
            "candidate_lookup_identity_cycle",
            "post_pass_runtime_trace_unproduced",
            "runtime_trace_not_required_for_receipt",
            "receipt_cid_profile_mismatch",
            "deferred_request_builder_unconfigured",
            "deferred_request_transport_type_mismatch",
            "issuer_unconfigured",
            "authoritative_candidate_not_published",
        ],
        "required_implementation_sequence": [
            {
                "goals": ["PTR-G020", "PTR-G030", "PTR-G060"],
                "work": "production_current_identity_provider_factory",
            },
            {
                "goals": ["PTR-G030", "PTR-G060"],
                "work": "controlled_current_runtime_preflight_provider",
            },
            {
                "goals": ["PTR-G010", "PTR-G040", "PTR-G050"],
                "work": "cross_package_receipt_cid_profile_conformance",
            },
            {
                "goals": ["PTR-G040", "PTR-G050", "PTR-G060"],
                "work": "deferred_request_issuer_and_candidate_publication",
            },
            {
                "goals": [
                    "PTR-G060",
                    "PTR-G080",
                    "PTR-G090",
                    "PTR-G100",
                ],
                "work": "unwired_cross_repository_cold_warm_e2e",
            },
            {
                "goals": ["PTR-G110"],
                "work": "activated_warm_benchmark_and_rollout_evidence",
            },
        ],
    }
    return inventory


def _reviewed_completion_projection() -> dict[str, object]:
    """Project implementation progress separately from goal authority."""

    if str(ACCEL_ROOT) not in sys.path:
        sys.path.insert(0, str(ACCEL_ROOT))
    from ipfs_accelerate_py.agent_supervisor.objectives.objective_graph import (
        parse_goal_heap,
    )
    from ipfs_accelerate_py.agent_supervisor.todo_daemon.implementation_daemon import (
        parse_task_file,
    )

    tasks = parse_task_file(REPO_ROOT / TODO_REL, TASK_PREFIX)
    completed_task_ids = {
        task.task_id for task in tasks if task.status == "completed"
    }
    open_task_ids = sorted(
        task.task_id for task in tasks if task.status != "completed"
    )
    claimable_task_ids = sorted(
        task.task_id
        for task in tasks
        if task.status == "todo"
        and set(task.depends_on).issubset(completed_task_ids)
    )
    goals = parse_goal_heap(
        (REPO_ROOT / OBJECTIVE_REL).read_text(encoding="utf-8")
    )
    goal_state_counts: dict[str, int] = {}
    for goal in goals:
        goal_state_counts[goal.status] = goal_state_counts.get(goal.status, 0) + 1
    projection = dict(CONFIG["objectiveProjection"])
    artifact_presence = _required_closeout_artifact_presence()
    input_inventory = _closeout_production_input_inventory(tasks)
    if open_task_ids:
        next_action = "execute_reviewed_expansion"
    elif not artifact_presence["artifact_presence_ready"]:
        next_action = "materialize_current_tree_completion_artifacts"
    else:
        next_action = "invoke_operator_closeout"
    return {
        "schema": (
            "ipfs_accelerate_py/proof-backed-test-reuse-"
            "reviewed-objective-projection@1"
        ),
        "implementation": {
            "task_count": len(tasks),
            "completed_task_count": len(completed_task_ids),
            "open_task_count": len(open_task_ids),
            "open_task_ids": open_task_ids,
            "claimable_task_ids": claimable_task_ids,
        },
        "authority": {
            "goal_count": len(goals),
            "goal_state_counts": dict(sorted(goal_state_counts.items())),
            "verified_goal_count": goal_state_counts.get(
                "verified_complete", 0
            ),
            "task_status_is_completion_authority": False,
        },
        "reviewed_expansion": {
            "task_ids": list(projection["implementationTaskIds"]),
            "initial_claimable_task_ids": list(
                projection["initialClaimableTaskIds"]
            ),
            "authority_writer": projection["authorityWriter"],
            "reconciliation_phases": projection["reconciliationPhases"],
            "autonomous_gap_generation_enabled": projection[
                "autonomousGapGenerationEnabled"
            ],
        },
        "closeout_readiness": artifact_presence,
        "closeout_input_inventory": input_inventory,
        "next_action": next_action,
    }


def _project_objectives() -> dict[str, object]:
    command = [
        sys.executable,
        "-m",
        "ipfs_accelerate_py.agent_supervisor.objectives.objective_daemon",
        "--repo-root",
        str(REPO_ROOT),
        "--objective-path",
        str(REPO_ROOT / OBJECTIVE_REL),
        "--todo-path",
        str(REPO_ROOT / TODO_REL),
        "--discovery-dir",
        str(PROJECTION_DIR / "discovery"),
        "--bundle-dir",
        str(PROJECTION_DIR / "bundles"),
        "--dataset-dir",
        str(PROJECTION_DIR / "datasets"),
        "--graph-path",
        str(PROJECTION_DIR / "objective_graph.json"),
        "--todo-vector-index-path",
        str(PROJECTION_DIR / "todo_vector_index.json"),
        "--analysis-escalation-path",
        str(PROJECTION_DIR / "analysis_escalation.json"),
        "--plan-evaluation-path",
        str(PROJECTION_DIR / "plan_evaluations.json"),
        "--objective-generation-path",
        str(PROJECTION_DIR / "objective_generation.json"),
        "--task-prefix",
        "PTR-",
        "--max-findings",
        "0",
        "--no-generate-bounded-work",
        "--no-reconcile-goal-completion",
        "--log-level",
        "INFO",
    ]
    result = _run(command, environment=_runtime_environment(), timeout=600)
    try:
        payload = json.loads(result.stdout)
    except ValueError:
        payload = {"stdout": result.stdout.strip()}
    payload["reviewed_completion_projection"] = (
        _reviewed_completion_projection()
    )
    receipt_path = PROJECTION_DIR / "objective_daemon_receipt.json"
    receipt_path.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    if _git_output("status", "--porcelain=v1", "--untracked-files=all"):
        raise RuntimeError("objective projection dirtied the integration checkout")
    return payload


def _protected_arguments() -> list[str]:
    arguments: list[str] = []
    for relative in PARALLEL["protectedPaths"]:
        arguments.extend(["--implementation-protected-path", str(relative)])
    return arguments


def _submodule_arguments() -> list[str]:
    arguments: list[str] = []
    for relative in PARALLEL["worktreeSubmodulePaths"]:
        arguments.extend(["--worktree-submodule-path", str(relative)])
    return arguments


def _task_state_work_complete(payload: dict[str, object]) -> bool:
    task_count = int(payload.get("task_count") or 0)
    completed_count = int(payload.get("completed_count") or 0)
    return task_count > 0 and completed_count >= task_count


def _current_board_task_ids() -> tuple[str, ...]:
    """Read the exact task population represented by the current TODO file.

    Status is intentionally derived from the live control-plane file instead
    of trusting a persisted lane count.  A stopped lane can retain a perfectly
    valid completion snapshot for an older board revision.
    """

    try:
        lines = (REPO_ROOT / TODO_REL).read_text(encoding="utf-8").splitlines()
    except OSError:
        return ()
    task_ids: list[str] = []
    heading_prefix = TASK_PREFIX.strip()
    task_id_prefix = heading_prefix.lstrip("# ").rstrip("-") + "-"
    for line in lines:
        if not line.startswith(heading_prefix):
            continue
        task_id = line[3:].split(maxsplit=1)[0]
        suffix = task_id.removeprefix(task_id_prefix)
        if task_id.startswith(task_id_prefix) and suffix.isdigit():
            task_ids.append(task_id)
    return tuple(task_ids)


def _task_ids_sha256(task_ids: Sequence[str]) -> str:
    canonical = "\n".join(sorted({str(task_id) for task_id in task_ids}))
    return "sha256:" + hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def _no_agent_readiness() -> dict[str, object]:
    state_dir = STATE_DIR / "preflight" / "board"
    command = [
        sys.executable,
        "-m",
        "ipfs_accelerate_py.agent_supervisor.todo_daemon.implementation_daemon",
        "--once",
        "--todo-path",
        str(REPO_ROOT / TODO_REL),
        "--task-prefix",
        TASK_PREFIX,
        "--state-dir",
        str(state_dir),
        "--state-prefix",
        "ptr_preflight",
        "--max-task-attempts",
        str(PARALLEL["maxTaskAttempts"]),
        "--worktree-root",
        str(WORKTREE_DIR / "preflight"),
        "--merge-target-branch",
        TARGET_BRANCH,
        "--merge-queue-dir",
        str(MERGE_QUEUE_DIR),
        *_submodule_arguments(),
        *_protected_arguments(),
        "--log-level",
        "INFO",
    ]
    result = _run(command, environment=_runtime_environment(), timeout=600)
    (LOG_DIR / "board_readiness.log").write_text(
        result.stdout + result.stderr, encoding="utf-8"
    )
    task_state_path = state_dir / "ptr_preflight_task_state.json"
    payload = json.loads(task_state_path.read_text(encoding="utf-8"))
    if int(payload.get("blocked_count") or 0) != 0:
        raise RuntimeError(
            f"board readiness has blocked tasks: {payload.get('blocked_task_ids')}"
        )
    work_complete = _task_state_work_complete(payload)
    if int(payload.get("selectable_ready_count") or 0) < 1 and not work_complete:
        raise RuntimeError(
            "board readiness has no selectable task: "
            f"{payload.get('selection_idle_reason')!r}"
        )
    payload["work_complete"] = work_complete
    return payload


def _lane_common_arguments(lane: dict[str, object], *, live: bool) -> list[str]:
    lane_name = str(lane["name"])
    if live:
        lane_state = STATE_DIR / lane_name
        lane_worktree = WORKTREE_DIR / lane_name
    else:
        lane_state = STATE_DIR / "preflight" / "reconciliation" / lane_name
        lane_worktree = WORKTREE_DIR / "preflight" / lane_name
    return [
        "--todo-path",
        str(REPO_ROOT / TODO_REL),
        "--task-prefix",
        TASK_PREFIX,
        "--state-dir",
        str(lane_state),
        "--state-prefix",
        lane_name,
        "--implement",
        "--max-task-attempts",
        str(PARALLEL["maxTaskAttempts"]),
        "--implementation-retry-budget",
        str(PARALLEL["implementationRetryBudget"]),
        "--validation-retry-budget",
        str(PARALLEL["validationRetryBudget"]),
        "--merge-retry-budget",
        str(PARALLEL["mergeRetryBudget"]),
        "--implementation-timeout",
        str(PARALLEL["implementationTimeoutSeconds"]),
        "--implementation-max-timeout",
        str(PARALLEL["implementationMaxTimeoutSeconds"]),
        "--implementation-log-stall-seconds",
        str(PARALLEL["implementationLogStallSeconds"]),
        "--daemon-interval",
        str(PARALLEL["daemonIntervalSeconds"]),
        "--check-interval",
        str(PARALLEL["checkIntervalSeconds"]),
        "--stale-seconds",
        str(PARALLEL["staleSeconds"]),
        "--watchdog-startup-grace-seconds",
        str(PARALLEL["watchdogStartupGraceSeconds"]),
        "--task-shard-count",
        str(PARALLEL["laneCount"]),
        "--task-shard-index",
        str(lane["shard"]),
        "--strict-task-sharding",
        "--worktree-root",
        str(lane_worktree),
        "--merge-target-branch",
        TARGET_BRANCH,
        "--merge-queue-dir",
        str(MERGE_QUEUE_DIR),
        "--merge-reconciliation-max-merges",
        str(PARALLEL["mergeReconciliationMaxMerges"]),
        "--llm-merge-resolver-command",
        _managed_merge_resolver_command(),
        *_submodule_arguments(),
        *_protected_arguments(),
        "--no-retry-budget-guardrail",
        "--no-dependency-guardrail",
        "--no-reconciliation-guardrail",
        "--no-objective-task-janitor",
        "--no-objective-goal-refinement",
        "--no-objective-goal-completion-reconcile",
        "--no-objective-goal-migration",
        "--log-level",
        "INFO",
    ]


def _reconciliation_preflight(lane: dict[str, object]) -> None:
    command = [
        sys.executable,
        "-m",
        "ipfs_accelerate_py.agent_supervisor.todo_daemon.implementation_supervisor",
        *_lane_common_arguments(lane, live=False),
        "--once",
        "--reconciliation-only",
    ]
    result = _run(
        command,
        environment=_runtime_environment(str(lane["provider"])),
        check=False,
        timeout=600,
    )
    output = result.stdout + result.stderr
    log_path = LOG_DIR / f"{lane['name']}_reconciliation_preflight.log"
    log_path.write_text(output, encoding="utf-8")
    if result.returncode != 0:
        diagnostic = output.strip()
        if len(diagnostic) > 4000:
            diagnostic = diagnostic[-4000:]
        raise RuntimeError(
            f"{lane['name']} reconciliation preflight exited "
            f"{result.returncode}; log={log_path}\n{diagnostic}"
        )


def _pid_path(lane_name: str) -> Path:
    return RUNTIME_DIR / f"{lane_name}_supervisor.pid"


def _read_pid(path: Path) -> int:
    try:
        return int(path.read_text(encoding="utf-8").strip())
    except (OSError, ValueError):
        return 0


def _pid_alive(pid: object) -> bool:
    if not isinstance(pid, int) or pid <= 0:
        return False
    try:
        os.kill(pid, 0)
    except OSError:
        return False
    try:
        process_state = Path(f"/proc/{pid}/stat").read_text(
            encoding="utf-8"
        ).split()[2]
    except (OSError, IndexError):
        return False
    if process_state == "Z":
        return False
    return True


def _lane_process_owned(lane_name: str, pid: int) -> bool:
    if not _pid_alive(pid):
        return False
    try:
        command_line = Path(f"/proc/{pid}/cmdline").read_bytes().replace(
            b"\0", b" "
        )
    except OSError:
        return False
    return (
        b"implementation_supervisor" in command_line
        and f"--state-prefix {lane_name}".encode() in command_line
        and str(REPO_ROOT / TODO_REL).encode() in command_line
    )


def _launch_lane(lane: dict[str, object]) -> int:
    lane_name = str(lane["name"])
    existing_pid = _read_pid(_pid_path(lane_name))
    if _lane_process_owned(lane_name, existing_pid):
        return existing_pid
    log_path = LOG_DIR / f"{lane_name}_supervisor.log"
    command = [
        sys.executable,
        "-m",
        "ipfs_accelerate_py.agent_supervisor.todo_daemon.implementation_supervisor",
        *_lane_common_arguments(lane, live=True),
    ]
    log_handle = log_path.open("ab", buffering=0)
    try:
        process = subprocess.Popen(
            command,
            cwd=REPO_ROOT,
            env=_runtime_environment(str(lane["provider"])),
            stdin=subprocess.DEVNULL,
            stdout=log_handle,
            stderr=subprocess.STDOUT,
            start_new_session=True,
        )
    finally:
        log_handle.close()
    _pid_path(lane_name).write_text(f"{process.pid}\n", encoding="utf-8")
    return process.pid


def _load_json(path: Path) -> dict[str, object]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}
    return value if isinstance(value, dict) else {}


def _lane_status(lane: dict[str, object]) -> dict[str, object]:
    lane_name = str(lane["name"])
    supervisor_pid = _read_pid(_pid_path(lane_name))
    status_path = STATE_DIR / lane_name / f"{lane_name}_supervisor_status.json"
    task_state_path = STATE_DIR / lane_name / f"{lane_name}_task_state.json"
    status = _load_json(status_path)
    task_state = _load_json(task_state_path)
    task_identities = task_state.get("task_identities")
    task_statuses = task_state.get("task_statuses")
    if isinstance(task_identities, Mapping):
        observed_task_ids = tuple(str(value) for value in task_identities)
    elif isinstance(task_statuses, Mapping):
        observed_task_ids = tuple(str(value) for value in task_statuses)
    else:
        observed_task_ids = ()
    daemon_pid = status.get("daemon_pid")
    supervisor_owned = _lane_process_owned(lane_name, supervisor_pid)
    daemon_alive = _pid_alive(daemon_pid)
    blocked_count = int(task_state.get("blocked_count") or 0)
    maintenance_error = str(
        status.get("last_agentic_maintenance_error") or ""
    ).strip()
    control_plane_update_pending = bool(
        status.get("control_plane_update_pending")
    )
    selection_idle_reason = str(
        task_state.get("selection_idle_reason") or ""
    )
    attempts_exhausted = (
        selection_idle_reason
        == "all_selectable_ready_tasks_reached_max_task_attempts"
    )
    unhealthy_reasons = []
    if not supervisor_owned:
        unhealthy_reasons.append("supervisor_not_owned_or_alive")
    if status.get("status") not in LIVE_SUPERVISOR_STATUSES:
        unhealthy_reasons.append("supervisor_not_running")
    if not daemon_alive:
        unhealthy_reasons.append("daemon_not_alive")
    if not task_state:
        unhealthy_reasons.append("task_state_missing")
    if blocked_count:
        unhealthy_reasons.append("blocked_tasks")
    if maintenance_error:
        unhealthy_reasons.append("agentic_maintenance_failed")
    if control_plane_update_pending:
        unhealthy_reasons.append("control_plane_update_pending")
    if attempts_exhausted:
        unhealthy_reasons.append("task_attempts_exhausted")
    healthy = bool(
        not unhealthy_reasons
    )
    return {
        "lane": lane_name,
        "shard": lane["shard"],
        "provider": lane["provider"],
        "primary_provider": lane["primary_provider"],
        "primary_model": lane["primary_model"],
        "fallback_provider": lane["fallback_provider"],
        "fallback_model": lane["fallback_model"],
        "fallback_model_reasoning_effort": lane[
            "fallback_model_reasoning_effort"
        ],
        "fallback_trigger": lane["fallback_trigger"],
        "healthy": healthy,
        "supervisor_pid": supervisor_pid or None,
        "supervisor_owned_and_alive": supervisor_owned,
        "status": status.get("status"),
        "status_updated_at": status.get("updated_at"),
        "daemon_pid": daemon_pid,
        "daemon_pid_alive": daemon_alive,
        "restart_count": status.get("restart_count"),
        "last_exit_code": status.get("last_exit_code"),
        "last_recycle_reason": status.get("last_recycle_reason"),
        "last_agentic_maintenance_error": status.get(
            "last_agentic_maintenance_error"
        ),
        "control_plane_source_id": status.get(
            "control_plane_source_id"
        ),
        "control_plane_current_source_id": status.get(
            "control_plane_current_source_id"
        ),
        "control_plane_source_revision": status.get(
            "control_plane_source_revision"
        ),
        "control_plane_current_source_revision": status.get(
            "control_plane_current_source_revision"
        ),
        "control_plane_update_pending": control_plane_update_pending,
        "control_plane_reload_deferred": status.get(
            "control_plane_reload_deferred"
        ),
        "control_plane_reload_deferred_reason": status.get(
            "control_plane_reload_deferred_reason"
        ),
        "unhealthy_reasons": unhealthy_reasons,
        "active_task_id": task_state.get(
            "active_task_id", status.get("active_task_id")
        ),
        "active_task_title": task_state.get("active_task_title"),
        "active_phase": task_state.get("active_phase"),
        "implementation_in_progress": task_state.get(
            "implementation_in_progress"
        ),
        "task_count": task_state.get("task_count"),
        "task_ids_sha256": (
            _task_ids_sha256(observed_task_ids) if observed_task_ids else None
        ),
        "completed_count": task_state.get("completed_count"),
        "ready_count": task_state.get("ready_count"),
        "selectable_ready_count": task_state.get("selectable_ready_count"),
        "waiting_count": task_state.get("waiting_count"),
        "blocked_count": blocked_count,
        "blocked_task_ids": task_state.get("blocked_task_ids"),
        "selection_idle_reason": selection_idle_reason,
        "heartbeat_at": task_state.get("heartbeat_at"),
        "active_log_path": task_state.get(
            "active_log_path", status.get("last_log_path")
        ),
        "supervisor_log_path": str(LOG_DIR / f"{lane_name}_supervisor.log"),
    }


def _status_payload() -> dict[str, object]:
    lanes = [_lane_status(lane) for lane in LANES]
    current_board_task_ids = _current_board_task_ids()
    current_board_task_count = len(current_board_task_ids)
    current_board_task_ids_sha256 = (
        _task_ids_sha256(current_board_task_ids)
        if current_board_task_ids
        else None
    )
    for item in lanes:
        count_matches = (
            current_board_task_count > 0
            and int(item.get("task_count") or 0) == current_board_task_count
        )
        observed_sha256 = item.get("task_ids_sha256")
        identity_matches = (
            observed_sha256 == current_board_task_ids_sha256
            if observed_sha256
            else count_matches
        )
        item["current_board_matches"] = bool(count_matches and identity_matches)
        if not item["current_board_matches"]:
            reasons = list(item.get("unhealthy_reasons") or [])
            if "task_state_board_mismatch" not in reasons:
                reasons.append("task_state_board_mismatch")
            item["unhealthy_reasons"] = reasons
            item["healthy"] = False
    work_complete = bool(lanes) and all(
        bool(item.get("healthy"))
        and bool(item.get("current_board_matches"))
        and _task_state_work_complete(item)
        for item in lanes
    )
    globally_progressable = any(
        bool(item.get("healthy"))
        and bool(item.get("current_board_matches"))
        and (
            bool(item.get("active_task_id"))
            or int(item.get("selectable_ready_count") or 0) > 0
        )
        for item in lanes
    ) or work_complete
    blocked_task_ids = sorted(
        {
            str(task_id)
            for item in lanes
            for task_id in (item.get("blocked_task_ids") or [])
        }
    )
    return {
        "schema": "ipfs_accelerate_py/proof-backed-test-reuse-control-status@1",
        "profile_id": CONFIG["profileId"],
        "repository_root": str(REPO_ROOT),
        "state_root": str(STATE_ROOT),
        "target_branch": TARGET_BRANCH,
        "current_board_task_count": current_board_task_count,
        "current_board_task_ids_sha256": current_board_task_ids_sha256,
        "provider_policy": {
            "primary": {
                "provider": PRIMARY_PROVIDER_POLICY["provider"],
                "model": PRIMARY_PROVIDER_POLICY["model"],
            },
            "fallback": {
                "provider": FALLBACK_PROVIDER_POLICY["provider"],
                "model": FALLBACK_PROVIDER_POLICY["model"],
                "model_reasoning_effort": FALLBACK_PROVIDER_POLICY[
                    "modelReasoningEffort"
                ],
            },
            "fallback_trigger": PROVIDER_POLICY["fallbackTrigger"],
            "non_quota_failure_action": PROVIDER_POLICY[
                "nonQuotaFailureAction"
            ],
            "applies_to": list(PROVIDER_POLICY["appliesTo"]),
            "semantic_merge_resolver": dict(
                PARALLEL["semanticMergeResolver"]
            ),
        },
        "healthy": bool(
            lanes
            and all(bool(item["healthy"]) for item in lanes)
            and globally_progressable
            and not blocked_task_ids
        ),
        "globally_progressable": globally_progressable,
        "work_complete": work_complete,
        "unhealthy_lanes": [
            {
                "lane": item["lane"],
                "reasons": list(item.get("unhealthy_reasons") or []),
            }
            for item in lanes
            if not item.get("healthy")
        ],
        "blocked_task_ids": blocked_task_ids,
        "lanes": lanes,
    }


def _verify_started(timeout_seconds: int = 55) -> dict[str, object]:
    deadline = time.monotonic() + timeout_seconds
    healthy_observations = 0
    last_payload: dict[str, object] = {}
    while time.monotonic() < deadline:
        last_payload = _status_payload()
        lanes = list(last_payload.get("lanes") or [])
        dead = [
            item
            for item in lanes
            if not item.get("supervisor_owned_and_alive")
        ]
        if dead:
            raise RuntimeError(f"PTR supervisor exited during startup: {dead}")
        if last_payload.get("healthy"):
            healthy_observations += 1
            if healthy_observations >= 3:
                return last_payload
        else:
            healthy_observations = 0
        time.sleep(1)
    raise RuntimeError(
        "PTR lanes did not publish three consecutive healthy observations: "
        + json.dumps(last_payload, sort_keys=True)
    )


def _stop_lane(lane: dict[str, object]) -> dict[str, object]:
    lane_name = str(lane["name"])
    pid = _read_pid(_pid_path(lane_name))
    if not pid:
        return {"lane": lane_name, "stopped": True, "reason": "no_pid"}
    if not _lane_process_owned(lane_name, pid):
        return {
            "lane": lane_name,
            "stopped": False,
            "reason": "pid_not_owned_or_not_alive",
            "pid": pid,
        }
    os.kill(pid, signal.SIGTERM)
    deadline = time.monotonic() + 30
    while time.monotonic() < deadline:
        if not _pid_alive(pid):
            return {"lane": lane_name, "stopped": True, "pid": pid}
        time.sleep(0.5)
    return {
        "lane": lane_name,
        "stopped": False,
        "reason": "sigterm_timeout",
        "pid": pid,
    }


def _completion_state_path(field: str) -> Path:
    projection = dict(CONFIG["objectiveProjection"])
    suffix = Path(str(projection[field]))
    if suffix.is_absolute() or ".." in suffix.parts:
        raise RuntimeError(
            f"objectiveProjection.{field} must be a safe state-root suffix"
        )
    path = (STATE_ROOT / suffix).resolve()
    try:
        path.relative_to(STATE_ROOT)
    except ValueError as exc:
        raise RuntimeError(
            f"objectiveProjection.{field} escapes the state root"
        ) from exc
    return path


def _closeout_health_input(
    *,
    checkout: dict[str, object],
    status: dict[str, object],
) -> dict[str, object]:
    config_bytes = CONFIG_PATH.read_bytes()
    return {
        "schema": (
            "ipfs_accelerate_py/proof-backed-test-reuse-"
            "supervisor-health-input@1"
        ),
        "captured_at_unix_ns": time.time_ns(),
        "configuration_sha256": (
            "sha256:" + hashlib.sha256(config_bytes).hexdigest()
        ),
        "checkout": checkout,
        "status": status,
    }


def _closeout_command(
    *,
    module_path: Path,
    gate_path: Path,
    evidence_path: Path,
    lifecycle_path: Path,
    candidate_path: Path,
    health_path: Path,
    status_path: Path,
    report_only: bool,
) -> list[str]:
    phase_count = int(
        dict(CONFIG["objectiveProjection"])["reconciliationPhases"]
    )
    command = [
        sys.executable,
        str(module_path),
        "--repo-root",
        str(REPO_ROOT),
        "--objective-path",
        str(REPO_ROOT / OBJECTIVE_REL),
        "--todo-path",
        str(REPO_ROOT / TODO_REL),
        "--gate-path",
        str(gate_path),
        "--evidence-path",
        str(evidence_path),
        "--lifecycle-projection-path",
        str(lifecycle_path),
        "--candidate-objective-path",
        str(candidate_path),
        "--supervisor-health-input-path",
        str(health_path),
        "--status-path",
        str(status_path),
        "--phase-count",
        str(phase_count),
    ]
    if report_only:
        command.append("--report-only")
    return command


def _decoded_closeout_result(
    result: subprocess.CompletedProcess[str],
) -> object:
    try:
        return json.loads(result.stdout)
    except ValueError:
        return {
            "stdout": result.stdout.strip(),
            "stderr": result.stderr.strip(),
        }


def _run_closeout_diagnosis(
    *,
    module_path: Path,
    checkout: dict[str, object],
    before: dict[str, object],
    gate_path: Path,
    evidence_path: Path,
    lifecycle_path: Path,
    candidate_path: Path,
    status_path: Path,
) -> tuple[subprocess.CompletedProcess[str], object]:
    """Run the documented no-lane-stop, no-state-output diagnosis."""

    with tempfile.TemporaryDirectory(prefix="ptr-closeout-report-") as temp_dir:
        health_path = Path(temp_dir) / "supervisor_health_input.json"
        health_path.write_text(
            json.dumps(
                _closeout_health_input(checkout=checkout, status=before),
                indent=2,
                sort_keys=True,
            )
            + "\n",
            encoding="utf-8",
        )
        command = _closeout_command(
            module_path=module_path,
            gate_path=gate_path,
            evidence_path=evidence_path,
            lifecycle_path=lifecycle_path,
            candidate_path=candidate_path,
            health_path=health_path,
            status_path=status_path,
            report_only=True,
        )
        result = _run(
            command,
            environment=_runtime_environment(),
            check=False,
            timeout=1800,
        )
    return result, _decoded_closeout_result(result)


def _closeout(*, report_only: bool = False) -> dict[str, object]:
    """Run the reviewed single-writer closeout after all implementation work."""

    checkout = _require_isolated_clean_checkout()
    _validate_board(persist_projection=not report_only)
    projection = _reviewed_completion_projection()
    implementation = dict(projection["implementation"])
    input_inventory = projection.get("closeout_input_inventory")
    if not isinstance(input_inventory, Mapping):
        input_inventory = _closeout_production_input_inventory()
    open_task_ids = list(implementation["open_task_ids"])
    if open_task_ids:
        raise RuntimeError(
            "objective closeout requires every implementation task to be "
            "completed; open tasks: " + ", ".join(open_task_ids)
        )
    before = _status_payload()
    if before.get("healthy") is not True or before.get("work_complete") is not True:
        raise RuntimeError(
            "objective closeout requires healthy, work-complete supervisor "
            "lanes so launch health can be captured"
        )

    module_path = (
        REPO_ROOT
        / "scripts"
        / "proof_backed_test_reuse_objective_reconciliation.py"
    )
    if not module_path.is_file():
        raise RuntimeError(
            "objective closeout implementation is not installed; "
            "PTR-121 must complete first"
        )

    gate_path = _completion_state_path("gatePathSuffix")
    evidence_path = _completion_state_path("evidencePathSuffix")
    lifecycle_path = _completion_state_path("lifecycleProjectionPathSuffix")
    candidate_path = _completion_state_path("candidateObjectivePathSuffix")
    health_path = _completion_state_path("supervisorHealthInputPathSuffix")
    status_path = _completion_state_path("statusPathSuffix")
    diagnosis_result, diagnosis = _run_closeout_diagnosis(
        module_path=module_path,
        checkout=checkout,
        before=before,
        gate_path=gate_path,
        evidence_path=evidence_path,
        lifecycle_path=lifecycle_path,
        candidate_path=candidate_path,
        status_path=status_path,
    )
    diagnosis_passed = (
        diagnosis_result.returncode == 0
        and isinstance(diagnosis, dict)
        and diagnosis.get("passed") is True
    )
    if report_only:
        return {
            "schema": (
                "ipfs_accelerate_py/"
                "proof-backed-test-reuse-closeout-diagnosis@1"
            ),
            "report_only": True,
            "diagnosis_passed": diagnosis_passed,
            "closeout_passed": False,
            "returncode": diagnosis_result.returncode,
            "lanes_stopped": False,
            "operator_commit_required": False,
            "input_inventory": input_inventory,
            "result": diagnosis,
        }
    if not diagnosis_passed:
        return {
            "schema": (
                "ipfs_accelerate_py/proof-backed-test-reuse-closeout@1"
            ),
            "closeout_passed": False,
            "precloseout_diagnosis_passed": False,
            "returncode": diagnosis_result.returncode,
            "lanes_stopped": [],
            "operator_commit_required": False,
            "input_inventory": input_inventory,
            "result": diagnosis,
        }

    for path in (
        gate_path,
        evidence_path,
        lifecycle_path,
        candidate_path,
        health_path,
        status_path,
    ):
        path.parent.mkdir(parents=True, exist_ok=True)

    health_input = _closeout_health_input(checkout=checkout, status=before)
    health_path.write_text(
        json.dumps(health_input, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )

    stopped = [_stop_lane(lane) for lane in LANES]
    if not all(item["stopped"] for item in stopped):
        raise RuntimeError(f"could not fence all PTR lanes: {stopped}")

    command = _closeout_command(
        module_path=module_path,
        gate_path=gate_path,
        evidence_path=evidence_path,
        lifecycle_path=lifecycle_path,
        candidate_path=candidate_path,
        health_path=health_path,
        status_path=status_path,
        report_only=False,
    )
    result = _run(
        command,
        environment=_runtime_environment(),
        check=False,
        timeout=10800,
    )
    (LOG_DIR / "objective_closeout.log").write_text(
        result.stdout + result.stderr,
        encoding="utf-8",
    )
    closeout_result = _decoded_closeout_result(result)
    payload = {
        "schema": (
            "ipfs_accelerate_py/proof-backed-test-reuse-closeout@1"
        ),
        "closeout_passed": result.returncode == 0,
        "returncode": result.returncode,
        "lanes_stopped": stopped,
        "candidate_objective_path": str(candidate_path),
        "status_path": str(status_path),
        "operator_commit_required": result.returncode == 0,
        "input_inventory": input_inventory,
        "result": closeout_result,
    }
    if result.returncode == 0 and not candidate_path.is_file():
        payload["closeout_passed"] = False
        payload["operator_commit_required"] = False
        payload["error"] = "closeout did not produce the candidate objective"
    return payload


def _preflight() -> dict[str, object]:
    checkout = _require_isolated_clean_checkout()
    providers = _provider_preflight()
    board = _validate_board()
    objective_projection = _project_objectives()
    readiness = _no_agent_readiness()
    for lane in LANES:
        _reconciliation_preflight(lane)
    if _git_output("status", "--porcelain=v1", "--untracked-files=all"):
        raise RuntimeError("preflight dirtied the integration checkout")
    payload = {
        "schema": "ipfs_accelerate_py/proof-backed-test-reuse-launch-preflight@1",
        "valid": True,
        "checkout": checkout,
        "providers": providers,
        "board": board,
        "objective_projection": objective_projection,
        "readiness": {
            key: readiness.get(key)
            for key in (
                "task_count",
                "completed_count",
                "ready_count",
                "selectable_ready_count",
                "waiting_count",
                "blocked_count",
                "blocked_task_ids",
                "selection_idle_reason",
                "work_complete",
            )
        },
        "optional_proof_infrastructure_is_launch_gate": False,
    }
    (PROJECTION_DIR / "launch_preflight.json").write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return payload


def _start() -> dict[str, object]:
    preflight = _preflight()
    launched: list[dict[str, object]] = []
    try:
        for lane in LANES:
            launched.append(
                {
                    "lane": lane["name"],
                    "pid": _launch_lane(lane),
                    "provider": lane["provider"],
                    "primary_provider": lane["primary_provider"],
                    "primary_model": lane["primary_model"],
                    "fallback_provider": lane["fallback_provider"],
                    "fallback_model": lane["fallback_model"],
                    "fallback_model_reasoning_effort": lane[
                        "fallback_model_reasoning_effort"
                    ],
                    "fallback_trigger": lane["fallback_trigger"],
                }
            )
        status = _verify_started()
    except Exception:
        for lane in LANES:
            _stop_lane(lane)
        raise
    return {
        "schema": "ipfs_accelerate_py/proof-backed-test-reuse-start@1",
        "started": True,
        "preflight_path": str(PROJECTION_DIR / "launch_preflight.json"),
        "preflight_valid": preflight["valid"],
        "launched": launched,
        "status": status,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "command",
        choices=(
            "validate",
            "project",
            "preflight",
            "start",
            "status",
            "stop",
            "closeout",
        ),
    )
    parser.add_argument(
        "--report-only",
        action="store_true",
        help=(
            "with closeout, diagnose readiness without stopping lanes or "
            "writing configured closeout outputs"
        ),
    )
    args = parser.parse_args()
    if args.report_only and args.command != "closeout":
        parser.error("--report-only is valid only with closeout")
    try:
        if args.command == "status":
            payload = _status_payload()
            exit_code = 0 if payload["healthy"] else 1
        elif args.command == "validate":
            _prepare_state_dirs()
            payload = _validate_board()
            exit_code = 0
        elif args.command == "project":
            with _control_lock():
                _require_isolated_clean_checkout()
                payload = _project_objectives()
            exit_code = 0
        elif args.command == "preflight":
            with _control_lock():
                payload = _preflight()
            exit_code = 0
        elif args.command == "start":
            with _control_lock():
                payload = _start()
            exit_code = 0
        elif args.command == "closeout":
            with _control_lock():
                payload = _closeout(report_only=args.report_only)
            success_field = (
                "diagnosis_passed" if args.report_only else "closeout_passed"
            )
            exit_code = 0 if payload[success_field] else 1
        else:
            with _control_lock():
                stopped = [_stop_lane(lane) for lane in LANES]
                payload = {
                    "schema": "ipfs_accelerate_py/proof-backed-test-reuse-stop@1",
                    "stopped": stopped,
                    "status": _status_payload(),
                }
            exit_code = 0 if all(item["stopped"] for item in stopped) else 1
    except (OSError, RuntimeError, subprocess.SubprocessError, ValueError) as exc:
        payload = {
            "schema": "ipfs_accelerate_py/proof-backed-test-reuse-control-error@1",
            "command": args.command,
            "error": str(exc),
        }
        exit_code = 2
    print(json.dumps(payload, indent=2, sort_keys=True))
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
