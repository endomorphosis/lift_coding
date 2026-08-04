#!/usr/bin/env python3
"""Run dependency-aware SwissKnife implementation supervisors in parallel."""

from __future__ import annotations

import argparse
import fcntl
import json
import math
import os
import signal
import subprocess
import sys
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from lift_ipfs_accelerate_bootstrap import bootstrap_ipfs_accelerate
from swissknife_checkout_lease_guard import require_swissknife_checkout_lease

_PREIMPORT_BOOTSTRAP = bootstrap_ipfs_accelerate(__file__, include_script_dir=True)

from ipfs_accelerate_py.agent_supervisor.todo_daemon.implementation_daemon import (  # noqa: E402
    parse_task_file,
    retry_budget_repair_source,
)


LANE_ID = "symbolic-contract-assurance"
BOARD_PATH = "implementation_plan/docs/44-swissknife-symbolic-contract-assurance.todo.md"
ALLOWED_LANES = {LANE_ID: BOARD_PATH}
IMPLEMENTATION_PROVIDER_ENV = "IPFS_ACCELERATE_AGENT_IMPLEMENTATION_PROVIDER"
ALLOWED_PROVIDER_ASSIGNMENTS = {"auto", "grok", "codex"}
ALLOWED_PROVIDER_ENVIRONMENT = {
    "IPFS_ACCELERATE_AGENT_CODEX_CONTEXT_WINDOW",
    "IPFS_ACCELERATE_AGENT_CODEX_MAX_THREADS",
    "IPFS_ACCELERATE_AGENT_CODEX_MAX_DEPTH",
    "IPFS_ACCELERATE_AGENT_DISABLE_SUBAGENTS",
    "IPFS_ACCELERATE_AGENT_GROK_BIN",
    "IPFS_ACCELERATE_AGENT_GROK_CONTEXT_WINDOW",
    "IPFS_ACCELERATE_AGENT_IMPLEMENTATION_CONTEXT_OUTPUT_RESERVE",
    "IPFS_ACCELERATE_AGENT_IMPLEMENTATION_CONTEXT_TOOL_RESERVE",
    "IPFS_ACCELERATE_AGENT_REQUIRE_TASK_EXECUTION_METADATA",
    "IPFS_ACCELERATE_AGENT_TODO_VECTOR_CONTEXT_TOKEN_BUDGET",
}
LANE_STATUS_STARTUP_GRACE_SECONDS = 300.0
LANE_STATUS_MIN_STALE_SECONDS = 60.0
LANE_STATUS_MAX_STALE_SECONDS = 300.0
LANE_STATUS_HEARTBEAT_MULTIPLIER = 4.0
LANE_FAILURE_EXIT_CODE = 1


@dataclass
class Lane:
    index: int
    state_dir: Path
    log_path: Path
    command: list[str]
    provider: str
    environment: dict[str, str]
    supervisor_status_path: Path
    process: subprocess.Popen[bytes] | None = None
    restarts: int = 0
    spawned_at: float = 0.0


def _read_json(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"{path} must contain a JSON object")
    return payload


def _write_json_atomic(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    temporary.replace(path)


def _csv(value: str) -> list[str]:
    return [item.strip() for item in value.split(",") if item.strip()]


def _path_overlap(left: str, right: str) -> bool:
    left_parts = Path(left).parts
    right_parts = Path(right).parts
    common = min(len(left_parts), len(right_parts))
    return left_parts[:common] == right_parts[:common]


def _taskboard_validation(todo_path: Path, task_prefix: str) -> dict[str, Any]:
    tasks = parse_task_file(todo_path, task_prefix)
    by_id = {task.task_id: task for task in tasks}
    if len(by_id) != len(tasks):
        raise ValueError("taskboard contains duplicate task IDs")

    missing_dependencies = sorted(
        {dependency for task in tasks for dependency in task.depends_on if dependency not in by_id}
    )
    if missing_dependencies:
        raise ValueError("taskboard has missing dependencies: " + ", ".join(missing_dependencies))

    visiting: set[str] = set()
    visited: set[str] = set()

    def visit(task_id: str) -> None:
        if task_id in visiting:
            raise ValueError(f"task dependency cycle reaches {task_id}")
        if task_id in visited:
            return
        visiting.add(task_id)
        for dependency in by_id[task_id].depends_on:
            visit(dependency)
        visiting.remove(task_id)
        visited.add(task_id)

    for task_id in sorted(by_id):
        visit(task_id)

    ancestors: dict[str, set[str]] = {}

    def task_ancestors(task_id: str) -> set[str]:
        cached = ancestors.get(task_id)
        if cached is not None:
            return cached
        result: set[str] = set()
        for dependency in by_id[task_id].depends_on:
            result.add(dependency)
            result.update(task_ancestors(dependency))
        ancestors[task_id] = result
        return result

    terminal_statuses = {"completed", "blocked"}
    missing_parallel_metadata: list[str] = []
    paths_by_task: dict[str, list[str]] = {}
    for task in tasks:
        metadata = task.metadata
        predicted = _csv(metadata.get("predicted files", ""))
        if task.status not in terminal_statuses and (
            not metadata.get("parallel lane") or not predicted
        ):
            missing_parallel_metadata.append(task.task_id)
        paths_by_task[task.task_id] = predicted
        for allowed in _csv(metadata.get("allow concurrent with", "")):
            if allowed not in by_id:
                raise ValueError(f"{task.task_id} allows unknown concurrent task {allowed}")
    if missing_parallel_metadata:
        raise ValueError(
            "active tasks lack Parallel lane or Predicted files: "
            + ", ".join(missing_parallel_metadata)
        )

    unordered_overlaps: list[dict[str, Any]] = []
    task_ids = sorted(task.task_id for task in tasks if task.status not in terminal_statuses)
    for offset, left_id in enumerate(task_ids):
        for right_id in task_ids[offset + 1 :]:
            if left_id in task_ancestors(right_id) or right_id in task_ancestors(left_id):
                continue
            left_repair_source, _left_failure_kind = retry_budget_repair_source(by_id[left_id])
            right_repair_source, _right_failure_kind = retry_budget_repair_source(by_id[right_id])
            if (
                left_repair_source == right_id
                or right_repair_source == left_id
                or (
                    left_repair_source
                    and (
                        left_repair_source in task_ancestors(right_id)
                        or right_id in task_ancestors(left_repair_source)
                    )
                )
                or (
                    right_repair_source
                    and (
                        right_repair_source in task_ancestors(left_id)
                        or left_id in task_ancestors(right_repair_source)
                    )
                )
            ):
                # The shared taskboard repair fence prevents a source task
                # from being reclaimed while its generated repair is active.
                # Existing dependency relatives remain ordered around that
                # fenced source even though the repair is a sibling node.
                continue
            overlaps = sorted(
                {
                    left_path if len(left_path) >= len(right_path) else right_path
                    for left_path in paths_by_task[left_id]
                    for right_path in paths_by_task[right_id]
                    if _path_overlap(left_path, right_path)
                }
            )
            if overlaps:
                unordered_overlaps.append(
                    {
                        "left": left_id,
                        "right": right_id,
                        "paths": overlaps,
                    }
                )
    if unordered_overlaps:
        raise ValueError(
            "parallel-ready tasks have overlapping declared write scopes: "
            + json.dumps(unordered_overlaps, sort_keys=True)
        )

    return {
        "task_count": len(tasks),
        "completed_count": sum(1 for task in tasks if task.status == "completed"),
        "dependency_edge_count": sum(len(task.depends_on) for task in tasks),
        "parallel_lane_count": len(
            {
                task.metadata.get("parallel lane", "")
                for task in tasks
                if task.metadata.get("parallel lane", "")
            }
        ),
        "unordered_write_scope_overlap_count": 0,
    }


def _append_repeated(
    command: list[str],
    flag: str,
    values: list[str],
) -> None:
    for value in values:
        command.extend([flag, value])


def _lane_command(
    *,
    profile: dict[str, Any],
    repo_root: Path,
    lane_index: int,
    lane_count: int,
    runtime_root: Path,
) -> tuple[list[str], Path]:
    parallel = dict(profile["parallelRuntime"])
    bounds = dict(profile["bounds"])
    artifacts = dict(profile["artifacts"])
    scan_policy = dict(profile["scanPolicy"])

    state_prefix = str(profile["statePrefix"])
    lane_name = f"lane-{lane_index:02d}"
    lane_root = runtime_root / "parallel" / "lanes" / lane_name
    state_dir = lane_root / "state"
    worktree_root = runtime_root / "parallel" / "worktrees" / lane_name
    wrapper = repo_root / "scripts/swissknife_leased_implementation_supervisor.py"

    command = [
        sys.executable,
        str(wrapper),
        "--todo-path",
        str(profile["todoPath"]),
        "--state-dir",
        str(state_dir),
        "--task-prefix",
        str(profile["taskPrefix"]),
        "--state-prefix",
        f"{state_prefix}_{lane_index:02d}",
        "--implement",
        "--implementation-timeout",
        str(bounds["implementationTimeoutSeconds"]),
        "--max-task-attempts",
        str(bounds["maxTaskAttempts"]),
        "--max-restarts",
        str(bounds["maxRestarts"]),
        "--check-interval",
        str(parallel["checkIntervalSeconds"]),
        "--daemon-interval",
        str(parallel["daemonIntervalSeconds"]),
        "--worktree-root",
        str(worktree_root),
        "--merge-target-branch",
        str(parallel["mergeTargetBranch"]),
        "--merge-reconciliation-max-merges",
        "1",
        "--task-shard-count",
        str(lane_count),
        "--task-shard-index",
        str(lane_index),
    ]
    if bool(parallel.get("strictTaskSharding", False)):
        command.append("--strict-task-sharding")
    _append_repeated(
        command,
        "--worktree-submodule-path",
        [str(item) for item in parallel["worktreeSubmodulePaths"]],
    )
    _append_repeated(
        command,
        "--implementation-protected-path",
        [str(item) for item in parallel["protectedPaths"]],
    )

    if lane_index == 0:
        command.extend(
            [
                "--objective-refill-scan",
                "--objective-path",
                str(profile["objectivePath"]),
                "--objective-graph-path",
                str(artifacts["graph"]),
                "--objective-bundle-dir",
                str(artifacts["bundles"]),
                "--objective-dataset-dir",
                str(artifacts["datasets"]),
                "--objective-discovery-dir",
                str(artifacts["discovery"]),
                "--objective-todo-vector-index-path",
                str(Path(artifacts["bundles"]) / "todo_vector_index.json"),
                "--objective-scan-min-open-tasks",
                str(bounds["objectiveRefillMinOpenTasks"]),
                "--objective-scan-max-findings",
                str(bounds["objectiveRefillMaxFindings"]),
                "--objective-scan-cooldown-seconds",
                str(bounds["refillCooldownSeconds"]),
                "--objective-refill-timeout-seconds",
                str(bounds["objectiveRefillTimeoutSeconds"]),
                "--objective-max-refinement-children",
                str(bounds["objectiveMaxRefinementChildren"]),
                "--objective-max-refinement-depth",
                str(bounds["objectiveMaxRefinementDepth"]),
                "--objective-surplus-findings-per-goal",
                "2",
                "--codebase-refill-scan",
                "--codebase-scan-discovery-dir",
                str(artifacts["discovery"]),
                "--codebase-scan-min-open-tasks",
                str(bounds["codebaseRefillMinOpenTasks"]),
                "--codebase-scan-max-findings",
                str(bounds["codebaseRefillMaxFindings"]),
                "--codebase-scan-cooldown-seconds",
                str(bounds["refillCooldownSeconds"]),
                "--codebase-refill-timeout-seconds",
                str(bounds["codebaseRefillTimeoutSeconds"]),
                "--no-objective-goal-migration",
            ]
        )
        _append_repeated(
            command,
            "--codebase-scan-skip-prefix",
            [str(item) for item in scan_policy["skipPrefixes"]],
        )
    else:
        command.extend(
            [
                "--no-objective-task-janitor",
                "--no-objective-goal-migration",
            ]
        )
    return command, state_dir


def _spawn_lane(lane: Lane, *, repo_root: Path) -> None:
    lane.state_dir.mkdir(parents=True, exist_ok=True)
    lane.log_path.parent.mkdir(parents=True, exist_ok=True)
    output = lane.log_path.open("ab")
    try:
        environment = os.environ.copy()
        environment.update(lane.environment)
        environment[IMPLEMENTATION_PROVIDER_ENV] = lane.provider
        lane.process = subprocess.Popen(
            lane.command,
            cwd=repo_root,
            env=environment,
            stdin=subprocess.DEVNULL,
            stdout=output,
            stderr=subprocess.STDOUT,
        )
        lane.spawned_at = time.monotonic()
    finally:
        output.close()


def _all_tasks_completed(todo_path: Path, task_prefix: str) -> bool:
    tasks = parse_task_file(todo_path, task_prefix)
    return bool(tasks) and all(task.status == "completed" for task in tasks)


def _timestamp_epoch(value: Any) -> float | None:
    if isinstance(value, (int, float)) and math.isfinite(float(value)):
        return float(value)
    if not isinstance(value, str) or not value.strip():
        return None
    normalized = value.strip()
    if normalized.endswith("Z"):
        normalized = normalized[:-1] + "+00:00"
    try:
        parsed = datetime.fromisoformat(normalized)
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.timestamp()


def _lane_status_failure(
    lane: Lane,
    *,
    now_epoch: float | None = None,
    now_monotonic: float | None = None,
) -> str | None:
    process = lane.process
    if process is None or process.poll() is not None:
        return None
    monotonic_now = time.monotonic() if now_monotonic is None else now_monotonic
    if lane.spawned_at > 0 and monotonic_now - lane.spawned_at < LANE_STATUS_STARTUP_GRACE_SECONDS:
        return None

    try:
        payload = _read_json(lane.supervisor_status_path)
    except (OSError, ValueError) as exc:
        return (
            f"lane-{lane.index:02d} status unavailable after startup grace: "
            f"{type(exc).__name__}: {exc}"
        )

    try:
        status_pid = int(payload.get("supervisor_pid"))
    except (TypeError, ValueError):
        return f"lane-{lane.index:02d} status has no valid supervisor_pid"
    if status_pid != process.pid:
        return f"lane-{lane.index:02d} status belongs to pid {status_pid}, expected {process.pid}"

    updated_at = _timestamp_epoch(payload.get("updated_at"))
    if updated_at is None:
        return f"lane-{lane.index:02d} status has no valid updated_at"
    try:
        heartbeat_seconds = float(payload.get("supervisor_heartbeat_seconds"))
    except (TypeError, ValueError):
        heartbeat_seconds = LANE_STATUS_MIN_STALE_SECONDS
    if not math.isfinite(heartbeat_seconds) or heartbeat_seconds <= 0:
        heartbeat_seconds = LANE_STATUS_MIN_STALE_SECONDS
    stale_after = max(
        LANE_STATUS_MIN_STALE_SECONDS,
        min(
            LANE_STATUS_MAX_STALE_SECONDS,
            heartbeat_seconds * LANE_STATUS_HEARTBEAT_MULTIPLIER,
        ),
    )
    epoch_now = time.time() if now_epoch is None else now_epoch
    age_seconds = epoch_now - updated_at
    if age_seconds > stale_after:
        return (
            f"lane-{lane.index:02d} status heartbeat is stale by "
            f"{age_seconds:.1f}s (limit {stale_after:.1f}s)"
        )
    return None


def _status_payload(
    lanes: list[Lane],
    *,
    validation: dict[str, Any],
    stopping: bool,
    stop_reason: str = "",
    exit_code: int | None = None,
) -> dict[str, Any]:
    return {
        "schema": ("lift-coding/swissknife-parallel-implementation-supervisor@1"),
        "pid": os.getpid(),
        "process_group": os.getpgrp(),
        "stopping": stopping,
        "stop_reason": stop_reason,
        "exit_code": exit_code,
        "updated_at": time.time(),
        "validation": validation,
        "lanes": [
            {
                "index": lane.index,
                "pid": lane.process.pid if lane.process is not None else 0,
                "provider": lane.provider,
                "running": (lane.process is not None and lane.process.poll() is None),
                "returncode": (None if lane.process is None else lane.process.poll()),
                "restarts": lane.restarts,
                "state_dir": str(lane.state_dir),
                "supervisor_status_path": str(lane.supervisor_status_path),
                "log_path": str(lane.log_path),
            }
            for lane in lanes
        ],
    }


def run(config_path: Path) -> int:
    profile = _read_json(config_path)
    parallel = profile.get("parallelRuntime")
    if not isinstance(parallel, dict) or not parallel.get("enabled"):
        raise ValueError("parallelRuntime.enabled must be true")

    repo_root = Path(profile.get("repositoryRoot") or ".").resolve()
    runtime_root = (repo_root / str(profile["runtimeRoot"])).resolve()
    todo_path = (repo_root / str(profile["todoPath"])).resolve()
    lane_count = int(parallel["laneCount"])
    if lane_count < 2 or lane_count > 8:
        raise ValueError("parallel laneCount must be in [2, 8]")
    providers = profile.get("providers")
    if not isinstance(providers, dict):
        raise ValueError("providers must be a JSON object")
    assignments = providers.get("laneAssignments")
    if not isinstance(assignments, list) or len(assignments) != lane_count:
        raise ValueError("providers.laneAssignments must contain exactly laneCount entries")
    provider_assignments = [str(item).strip().lower() for item in assignments]
    unsupported_assignments = sorted(set(provider_assignments) - ALLOWED_PROVIDER_ASSIGNMENTS)
    if unsupported_assignments:
        raise ValueError(
            "unsupported provider lane assignments: " + ", ".join(unsupported_assignments)
        )
    configured_environment = providers.get("commonEnvironment", {})
    if not isinstance(configured_environment, dict):
        raise ValueError("providers.commonEnvironment must be a JSON object")
    unknown_environment = sorted(set(configured_environment) - ALLOWED_PROVIDER_ENVIRONMENT)
    if unknown_environment:
        raise ValueError(
            "providers.commonEnvironment contains non-allowlisted keys: "
            + ", ".join(unknown_environment)
        )
    provider_environment = {str(key): str(value) for key, value in configured_environment.items()}

    require_swissknife_checkout_lease(
        ["--implement"],
        allowed_lanes=ALLOWED_LANES,
    )
    merge_target = str(parallel["mergeTargetBranch"])
    branch_check = subprocess.run(
        ["git", "rev-parse", "--verify", "--quiet", merge_target],
        cwd=repo_root,
        check=False,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    if branch_check.returncode != 0:
        raise RuntimeError(f"parallel merge target branch does not exist: {merge_target}")

    validation = _taskboard_validation(
        todo_path,
        str(profile["taskPrefix"]),
    )
    validation["strict_task_sharding"] = bool(parallel.get("strictTaskSharding", False))
    validation["provider_lane_assignments"] = list(provider_assignments)
    validation["provider_environment_keys"] = sorted(provider_environment)
    parallel_root = runtime_root / "parallel"
    parallel_root.mkdir(parents=True, exist_ok=True)
    status_path = parallel_root / "parallel_supervisor_status.json"
    lock_path = parallel_root / "parallel_supervisor.lock"
    lock_handle = lock_path.open("a+", encoding="utf-8")
    try:
        fcntl.flock(lock_handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
    except BlockingIOError as exc:
        raise RuntimeError("parallel supervisor is already running") from exc

    lanes: list[Lane] = []
    for index in range(lane_count):
        command, state_dir = _lane_command(
            profile=profile,
            repo_root=repo_root,
            lane_index=index,
            lane_count=lane_count,
            runtime_root=runtime_root,
        )
        lanes.append(
            Lane(
                index=index,
                state_dir=state_dir,
                log_path=(parallel_root / "logs" / f"lane-{index:02d}.log"),
                command=command,
                provider=provider_assignments[index],
                environment=dict(provider_environment),
                supervisor_status_path=(
                    state_dir / (f"{profile['statePrefix']}_{index:02d}_supervisor_status.json")
                ),
            )
        )

    stopping = False
    stop_reason = ""
    exit_code = 0
    operator_signal: int | None = None

    def request_stop(signum: int, _frame: object) -> None:
        nonlocal operator_signal, stop_reason, stopping
        operator_signal = signum
        if not stopping:
            stop_reason = f"operator_signal:{signal.Signals(signum).name}"
            stopping = True

    def fail(reason: str) -> None:
        nonlocal exit_code, stop_reason, stopping
        if operator_signal is not None:
            return
        exit_code = LANE_FAILURE_EXIT_CODE
        stop_reason = reason
        stopping = True
        print(f"parallel supervisor failure: {reason}", file=sys.stderr, flush=True)

    signal.signal(signal.SIGINT, request_stop)
    signal.signal(signal.SIGTERM, request_stop)

    restart_limit = int(profile["bounds"]["maxRestarts"])
    try:
        for lane in lanes:
            if stopping:
                break
            try:
                _spawn_lane(lane, repo_root=repo_root)
            except Exception as exc:
                if operator_signal is None:
                    fail(
                        f"lane-{lane.index:02d} initial launch failed: {type(exc).__name__}: {exc}"
                    )
                break
        _write_json_atomic(
            status_path,
            _status_payload(
                lanes,
                validation=validation,
                stopping=stopping,
                stop_reason=stop_reason,
                exit_code=exit_code if stopping else None,
            ),
        )
        while not stopping:
            if _all_tasks_completed(todo_path, str(profile["taskPrefix"])):
                stop_reason = "backlog_completed"
                stopping = True
                break
            for lane in lanes:
                if stopping:
                    break
                process = lane.process
                if process is None or process.poll() is None:
                    continue
                if lane.restarts >= restart_limit:
                    fail(
                        f"lane-{lane.index:02d} exhausted restart budget "
                        f"after exit {process.poll()}"
                    )
                    break
                lane.restarts += 1
                time.sleep(min(5.0, float(lane.restarts)))
                if stopping:
                    break
                try:
                    _spawn_lane(lane, repo_root=repo_root)
                except Exception as exc:
                    fail(f"lane-{lane.index:02d} restart failed: {type(exc).__name__}: {exc}")
                    break
            if not stopping:
                for lane in lanes:
                    status_failure = _lane_status_failure(lane)
                    if status_failure:
                        fail(status_failure)
                        break
            _write_json_atomic(
                status_path,
                _status_payload(
                    lanes,
                    validation=validation,
                    stopping=stopping,
                    stop_reason=stop_reason,
                    exit_code=exit_code if stopping else None,
                ),
            )
            if not stopping:
                time.sleep(2.0)
    finally:
        for lane in lanes:
            if lane.process is not None and lane.process.poll() is None:
                lane.process.terminate()
        deadline = time.monotonic() + 20.0
        for lane in lanes:
            process = lane.process
            if process is None:
                continue
            remaining = max(0.0, deadline - time.monotonic())
            try:
                process.wait(timeout=remaining)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait(timeout=5)
        _write_json_atomic(
            status_path,
            _status_payload(
                lanes,
                validation=validation,
                stopping=True,
                stop_reason=stop_reason,
                exit_code=exit_code,
            ),
        )
        fcntl.flock(lock_handle.fileno(), fcntl.LOCK_UN)
        lock_handle.close()
    return exit_code


def main() -> None:
    parser = argparse.ArgumentParser(
        description=(
            "Run dependency-aware SwissKnife task shards with isolated "
            "worktrees and a shared merge queue"
        )
    )
    parser.add_argument(
        "--config",
        type=Path,
        required=True,
        help="Parallel supervisor profile JSON",
    )
    args = parser.parse_args()
    raise SystemExit(run(args.config.resolve()))


if __name__ == "__main__":
    main()
