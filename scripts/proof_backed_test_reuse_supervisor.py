#!/usr/bin/env python3
"""Operate isolated supervisor lanes for proof-backed test reuse."""

from __future__ import annotations

import argparse
import fcntl
import importlib.util
import json
import os
import shutil
import signal
import subprocess
import sys
import time
from contextlib import contextmanager
from pathlib import Path
from typing import Iterator, Sequence


REPO_ROOT = Path(__file__).resolve().parents[1]
ACCEL_ROOT = REPO_ROOT / "external" / "ipfs_accelerate"
DATASETS_ROOT = REPO_ROOT / "external" / "ipfs_datasets"
KIT_ROOT = REPO_ROOT / "external" / "ipfs_kit"
CONFIG_PATH = REPO_ROOT / "config" / "proof_backed_test_reuse_supervisor.json"


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
    }
    for index in range(int(PARALLEL["laneCount"]))
)


def _runtime_environment(provider: str | None = None) -> dict[str, str]:
    environment = dict(os.environ)
    python_paths = [str(ACCEL_ROOT), str(DATASETS_ROOT), str(KIT_ROOT)]
    if environment.get("PYTHONPATH"):
        python_paths.append(environment["PYTHONPATH"])
    environment["PYTHONPATH"] = os.pathsep.join(python_paths)
    for key, value in dict(PARALLEL["commonEnvironment"]).items():
        environment[str(key)] = str(value)
    if provider:
        environment["IPFS_ACCELERATE_AGENT_IMPLEMENTATION_PROVIDER"] = provider
        if provider == "grok-build":
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


def _require_isolated_clean_checkout() -> dict[str, object]:
    branch = _git_output("branch", "--show-current")
    if branch != TARGET_BRANCH:
        raise RuntimeError(
            f"refusing branch {branch!r}; expected {TARGET_BRANCH!r}"
        )
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


def _provider_preflight() -> dict[str, object]:
    try:
        import duckdb  # type: ignore
    except ImportError as exc:
        raise RuntimeError("Python cannot import required DuckDB") from exc
    codex_binary = shutil.which("codex")
    grok_binary = shutil.which("grok")
    if not codex_binary:
        raise RuntimeError("Codex CLI is required by configured PTR lanes")
    if not grok_binary:
        raise RuntimeError("Grok CLI is required by configured PTR lanes")
    codex_status = _run(
        [codex_binary, "login", "status"],
        environment=_runtime_environment(),
        timeout=30,
    )
    grok_version = _run(
        [grok_binary, "--version"],
        environment=_runtime_environment(),
        timeout=30,
    )
    if "logged in" not in (codex_status.stdout + codex_status.stderr).lower():
        raise RuntimeError("Codex CLI did not report an authenticated session")

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
        raise RuntimeError("Grok CLI is configured for a lane but is not authenticated")

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
    return {
        "python": sys.executable,
        "duckdb": duckdb.__version__,
        "codex": codex_binary,
        "codex_status": (codex_status.stdout + codex_status.stderr).strip(),
        "grok": grok_binary,
        "grok_version": (grok_version.stdout + grok_version.stderr).strip(),
        "grok_authenticated": grok_authenticated,
        "optional_non_blocking_capabilities": optional,
    }


def _validate_board() -> dict[str, object]:
    result = _run(
        [sys.executable, str(REPO_ROOT / VALIDATOR_REL)],
        environment=_runtime_environment(),
        timeout=180,
    )
    payload = json.loads(result.stdout)
    if payload.get("valid") is not True:
        raise RuntimeError("PTR board validator did not report valid")
    (PROJECTION_DIR / "native_board_preflight.json").write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return payload


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
    receipt_path = PROJECTION_DIR / "objective_daemon_receipt.json"
    receipt_path.write_text(result.stdout, encoding="utf-8")
    try:
        payload = json.loads(result.stdout)
    except ValueError:
        payload = {"stdout": result.stdout.strip()}
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
    if int(payload.get("selectable_ready_count") or 0) < 1:
        raise RuntimeError(
            "board readiness has no selectable task: "
            f"{payload.get('selection_idle_reason')!r}"
        )
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
    if status.get("status") != "running":
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
    work_complete = bool(lanes) and all(
        int(item.get("task_count") or 0) > 0
        and int(item.get("completed_count") or 0)
        >= int(item.get("task_count") or 0)
        for item in lanes
    )
    globally_progressable = any(
        bool(item.get("active_task_id"))
        or int(item.get("selectable_ready_count") or 0) > 0
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
        "command", choices=("validate", "project", "preflight", "start", "status", "stop")
    )
    args = parser.parse_args()
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
