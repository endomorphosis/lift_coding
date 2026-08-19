#!/usr/bin/env python3
"""Fail-closed validator for the reviewed FACP objective/task program."""

from __future__ import annotations

import argparse
import json
import re
import sys
from collections import defaultdict, deque
from pathlib import Path, PurePosixPath
from typing import Iterable


ROOT = Path(__file__).resolve().parents[1]
ACCELERATOR = ROOT / "external" / "ipfs_accelerate"
if str(ACCELERATOR) not in sys.path:
    sys.path.insert(0, str(ACCELERATOR))

from ipfs_accelerate_py.agent_supervisor.entrypoints.plan_lint import (  # noqa: E402
    PlanLintError,
    lint_supervisor_plan,
)
from ipfs_accelerate_py.agent_supervisor.objectives.objective_graph import (  # noqa: E402
    parse_goal_heap,
)
from ipfs_accelerate_py.agent_supervisor.todo_daemon.implementation_daemon import (  # noqa: E402
    parse_task_file,
    split_csv,
)


PLAN = Path(
    "implementation_plan/docs/49-formal-assurance-control-plane-plan-2026-08-19.md"
)
OBJECTIVES = Path(
    "implementation_plan/docs/49-formal-assurance-control-plane.objectives.md"
)
TASKBOARD = Path(
    "implementation_plan/docs/49-formal-assurance-control-plane.todo.md"
)
SCHEDULER = Path("config/formal_assurance_control_plane_scheduler.json")
VALIDATOR = Path("scripts/validate_formal_assurance_control_plane_board.py")
CONTROLLER = Path("scripts/formal_assurance_control_plane_supervisor.sh")
TASK_PREFIX = "FACP-"
GOAL_PREFIX = "FACP-G"
BOARD_NAMESPACE = "formal-assurance-control-plane-v1"
RUNTIME_ROOT = "data/agent_supervisor/formal_assurance_control_plane_v2"
ROOT_GOAL = "FACP-G000"
BOOTSTRAP_TASK = "FACP-000"
INITIAL_READY = tuple(f"FACP-{index:03d}" for index in range(1, 8))
REQUIRED_TASK_FIELDS = (
    "status",
    "completion",
    "is schedulable",
    "review only",
    "priority",
    "track",
    "goal id",
    "owning repository",
    "outputs",
    "predicted files",
    "validation",
    "board namespace",
    "bundle",
    "parallel lane",
    "resource class",
    "implementation mode",
    "provider authority",
    "allowed effects",
    "prohibited effects",
    "conflict policy",
    "preconditions",
    "evidence subset",
    "acceptance",
)
REQUIRED_PROTECTED = (
    PLAN.as_posix(),
    OBJECTIVES.as_posix(),
    TASKBOARD.as_posix(),
    SCHEDULER.as_posix(),
    VALIDATOR.as_posix(),
    CONTROLLER.as_posix(),
)


def safe_relative(value: str) -> bool:
    """Return whether a board path is a normalized repository-relative path."""

    if not value or "\x00" in value or "\\" in value or "://" in value:
        return False
    path = PurePosixPath(value)
    return (
        not path.is_absolute()
        and path.as_posix() not in {".", ".."}
        and ".." not in path.parts
        and all(part not in {"", "."} for part in path.parts)
        and not value.startswith("~")
    )


def cycle_nodes(graph: dict[str, set[str]]) -> list[str]:
    """Return sorted nodes remaining after Kahn reduction."""

    nodes = set(graph)
    for dependencies in graph.values():
        nodes.update(dependencies)
    indegree = {node: 0 for node in nodes}
    dependents: dict[str, set[str]] = defaultdict(set)
    for node, dependencies in graph.items():
        indegree[node] += len(dependencies)
        for dependency in dependencies:
            dependents[dependency].add(node)
    ready = deque(sorted(node for node, degree in indegree.items() if degree == 0))
    visited: set[str] = set()
    while ready:
        node = ready.popleft()
        visited.add(node)
        for dependent in sorted(dependents.get(node, ())):
            indegree[dependent] -= 1
            if indegree[dependent] == 0:
                ready.append(dependent)
    return sorted(nodes - visited)


def repeated(values: Iterable[str]) -> list[str]:
    counts: dict[str, int] = defaultdict(int)
    for value in values:
        counts[value] += 1
    return sorted(value for value, count in counts.items() if count > 1)


def validate() -> dict[str, object]:
    errors: list[str] = []
    warnings: list[str] = []
    required_paths = (PLAN, OBJECTIVES, TASKBOARD, SCHEDULER, VALIDATOR, CONTROLLER)
    for relative in required_paths:
        if not (ROOT / relative).is_file():
            errors.append(f"missing control artifact: {relative.as_posix()}")

    if not (ROOT / OBJECTIVES).is_file() or not (ROOT / TASKBOARD).is_file():
        return {
            "schema": "facp/board-validation@1",
            "valid": False,
            "errors": errors,
            "warnings": warnings,
            "goal_count": 0,
            "task_count": 0,
            "ready_task_ids": [],
            "completed_task_ids": [],
        }

    goals = parse_goal_heap((ROOT / OBJECTIVES).read_text(encoding="utf-8"))
    tasks = parse_task_file(ROOT / TASKBOARD, task_header_prefix=TASK_PREFIX)
    goal_ids = [goal.goal_id for goal in goals]
    task_ids = [task.task_id for task in tasks]
    goal_set = set(goal_ids)
    task_set = set(task_ids)

    if duplicate_goals := repeated(goal_ids):
        errors.append(f"duplicate goal IDs: {duplicate_goals}")
    if duplicate_tasks := repeated(task_ids):
        errors.append(f"duplicate task IDs: {duplicate_tasks}")
    if ROOT_GOAL not in goal_set:
        errors.append(f"missing root goal: {ROOT_GOAL}")
    if BOOTSTRAP_TASK not in task_set:
        errors.append(f"missing bootstrap task: {BOOTSTRAP_TASK}")
    if len(goals) < 20:
        errors.append(f"objective heap is unexpectedly shallow: {len(goals)} goals")
    if len(tasks) != 61:
        errors.append(f"expected 61 reviewed tasks, found {len(tasks)}")

    goal_graph: dict[str, set[str]] = {}
    for goal in goals:
        if not goal.goal_id.startswith(GOAL_PREFIX):
            errors.append(f"invalid goal prefix: {goal.goal_id}")
        parents = set(goal.parent_goal_ids)
        dependencies = set(goal.dependencies)
        unknown_parents = sorted(parents - goal_set)
        unknown_dependencies = sorted(dependencies - goal_set)
        if unknown_parents:
            errors.append(f"unknown goal parents {goal.goal_id}: {unknown_parents}")
        if unknown_dependencies:
            errors.append(
                f"unknown goal dependencies {goal.goal_id}: {unknown_dependencies}"
            )
        if goal.goal_id == ROOT_GOAL and parents:
            errors.append("root goal must not have a parent")
        if goal.goal_id != ROOT_GOAL and len(parents) != 1:
            errors.append(f"subgoal must have exactly one parent: {goal.goal_id}")
        if not str(goal.fields.get("goal") or "").strip():
            errors.append(f"goal statement missing: {goal.goal_id}")
        if not str(goal.fields.get("acceptance") or "").strip():
            errors.append(f"goal acceptance missing: {goal.goal_id}")
        goal_graph[goal.goal_id] = parents | dependencies
    if goal_cycles := cycle_nodes(goal_graph):
        errors.append(f"goal graph cycle: {goal_cycles}")

    task_graph: dict[str, set[str]] = {}
    tasks_by_goal: dict[str, list[str]] = defaultdict(list)
    predicted_owner: dict[str, str] = {}
    plan_tasks: list[dict[str, object]] = []
    for task in tasks:
        if not task.task_id.startswith(TASK_PREFIX):
            errors.append(f"invalid task prefix: {task.task_id}")
        missing_fields = [field for field in REQUIRED_TASK_FIELDS if not task.metadata.get(field)]
        if missing_fields:
            errors.append(f"task {task.task_id} missing fields: {missing_fields}")
        dependencies = set(task.depends_on)
        unknown_dependencies = sorted(dependencies - task_set)
        if unknown_dependencies:
            errors.append(
                f"unknown task dependencies {task.task_id}: {unknown_dependencies}"
            )
        task_graph[task.task_id] = dependencies
        goal_id = task.metadata.get("goal id", "")
        if goal_id not in goal_set:
            errors.append(f"unknown task goal {task.task_id}: {goal_id}")
        else:
            tasks_by_goal[goal_id].append(task.task_id)
        if task.metadata.get("board namespace") != BOARD_NAMESPACE:
            errors.append(f"board namespace mismatch: {task.task_id}")
        predicted = split_csv(task.metadata.get("predicted files", ""))
        if set(predicted) != set(task.outputs):
            errors.append(f"outputs/predicted-files mismatch: {task.task_id}")
        for path in predicted:
            if not safe_relative(path):
                errors.append(f"unsafe predicted path {task.task_id}: {path}")
            previous = predicted_owner.get(path)
            if previous is not None and previous != task.task_id:
                errors.append(
                    f"predicted path has multiple owners: {path}: {previous}, {task.task_id}"
                )
            predicted_owner[path] = task.task_id
        if not task.validation:
            errors.append(f"task validation missing: {task.task_id}")
        plan_tasks.append(
            {
                "task_id": task.task_id,
                "title": task.title,
                "goal_id": goal_id,
                "acceptance": task.acceptance,
                "outputs": list(task.outputs),
                "predicted_files": predicted,
                "validation_commands": list(task.validation),
                "depends_on": list(task.depends_on),
            }
        )
    if task_cycles := cycle_nodes(task_graph):
        errors.append(f"task graph cycle: {task_cycles}")

    goal_children: dict[str, list[str]] = defaultdict(list)
    for goal in goals:
        for parent_goal_id in goal.parent_goal_ids:
            goal_children[parent_goal_id].append(goal.goal_id)
    for goal_id in sorted(goal_set):
        if not tasks_by_goal.get(goal_id) and not goal_children.get(goal_id):
            errors.append(f"leaf goal has no producing task: {goal_id}")

    completed = {
        task.task_id for task in tasks if task.status == "completed"
    }
    in_progress = {
        task.task_id for task in tasks if task.status == "in_progress"
    }
    ready = sorted(
        task.task_id
        for task in tasks
        if task.status == "todo" and set(task.depends_on).issubset(completed)
    )
    incomplete = task_set - completed
    if incomplete and not ready and not in_progress:
        errors.append("incomplete board has no ready or in-progress task")
    if completed == {BOOTSTRAP_TASK} and tuple(ready) != INITIAL_READY:
        errors.append(
            f"initial ready wave mismatch: expected {list(INITIAL_READY)}, found {ready}"
        )

    plan_goals = [
        {
            "goal_id": goal.goal_id,
            "title": goal.title,
            "acceptance": str(goal.fields.get("acceptance") or ""),
            "parent": goal.parent_goal_ids[0] if goal.parent_goal_ids else "",
            "depends_on": list(goal.dependencies),
        }
        for goal in goals
    ]
    lint_report: dict[str, object] = {}
    try:
        lint = lint_supervisor_plan(
            {
                "schema": (
                    "ipfs_accelerate_py/agent-supervisor/entrypoints/"
                    "supervisor-plan-document@1"
                ),
                "plan_id": BOARD_NAMESPACE,
                "goals": plan_goals,
                "tasks": plan_tasks,
            },
            require_profile=False,
        )
        lint_report = lint.to_dict()
        if not lint.accepted:
            errors.append(
                "strict plan lint rejected: "
                + ", ".join(
                    sorted(
                        {
                            str(item.get("code") or "unknown")
                            for item in lint_report.get("findings", [])
                            if isinstance(item, dict)
                        }
                    )
                )
            )
    except (PlanLintError, TypeError, ValueError) as exc:
        errors.append(f"strict plan lint failed to load: {type(exc).__name__}: {exc}")

    scheduler: dict[str, object] = {}
    if (ROOT / SCHEDULER).is_file():
        try:
            loaded = json.loads((ROOT / SCHEDULER).read_text(encoding="utf-8"))
            if isinstance(loaded, dict):
                scheduler = loaded
            else:
                errors.append("scheduler root must be an object")
        except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
            errors.append(f"scheduler is unreadable: {type(exc).__name__}: {exc}")
    if scheduler:
        expected = {
            "taskboard_path": TASKBOARD.as_posix(),
            "objectives_path": OBJECTIVES.as_posix(),
            "plan_path": PLAN.as_posix(),
            "validator_path": VALIDATOR.as_posix(),
            "task_prefix": TASK_PREFIX,
            "board_namespace": BOARD_NAMESPACE,
            "merge_target_branch": "agent/formal-assurance-control-plane",
        }
        for field, value in expected.items():
            if scheduler.get(field) != value:
                errors.append(f"scheduler {field} mismatch")
        if scheduler.get("max_lanes") != 4:
            errors.append("scheduler must configure four lanes")
        lanes = scheduler.get("lanes")
        if not isinstance(lanes, list) or [item.get("index") for item in lanes if isinstance(item, dict)] != [0, 1, 2, 3]:
            errors.append("scheduler lane indexes must be 0,1,2,3")
        if scheduler.get("strict_task_sharding") is not True:
            errors.append("strict task sharding must be enabled")
        if scheduler.get("objective_refill_enabled") is not False:
            errors.append("objective refill must be disabled")
        if scheduler.get("codebase_refill_enabled") is not False:
            errors.append("codebase refill must be disabled")
        runtime_paths = scheduler.get("runtime_paths")
        expected_runtime = {
            "root": RUNTIME_ROOT,
            "state": f"{RUNTIME_ROOT}/state",
            "worktrees": f"{RUNTIME_ROOT}/worktrees",
            "merge_queue": f"{RUNTIME_ROOT}/merge_queue",
            "logs": f"{RUNTIME_ROOT}/logs",
        }
        if runtime_paths != expected_runtime:
            errors.append("scheduler runtime namespace mismatch")
        provider = scheduler.get("provider")
        expected_provider = {
            "primary_provider_id": "grok_cli",
            "primary_model_id": "grok-4.5",
            "fallback_provider_id": "codex",
            "fallback_model_id": "gpt-5.6-terra",
            "fallback_trigger": "primary_quota_exhausted",
            "fallback_reasoning_effort": "high",
            "max_concurrency": 4,
        }
        if provider != expected_provider:
            errors.append("scheduler ordered provider route mismatch")
        protected = scheduler.get("protected_paths")
        if not isinstance(protected, list) or not set(REQUIRED_PROTECTED).issubset(
            set(str(item) for item in protected)
        ):
            errors.append("scheduler does not protect all FACP control artifacts")
        safety = scheduler.get("safety_floors")
        if not isinstance(safety, dict) or any(value != 0 for value in safety.values()):
            errors.append("all declared safety floors must be zero")

    return {
        "schema": "facp/board-validation@1",
        "valid": not errors,
        "errors": errors,
        "warnings": warnings,
        "goal_count": len(goals),
        "task_count": len(tasks),
        "completed_count": len(completed),
        "in_progress_count": len(in_progress),
        "ready_task_ids": ready,
        "completed_task_ids": sorted(completed),
        "initial_ready_task_ids": list(INITIAL_READY),
        "strict_plan_lint": lint_report,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check-all", action="store_true", help="validate the complete program")
    args = parser.parse_args()
    if not args.check_all:
        parser.error("--check-all is required")
    report = validate()
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0 if report["valid"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
