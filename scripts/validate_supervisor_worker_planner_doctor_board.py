#!/usr/bin/env python3
"""Fail-closed preflight for the worker planner–doctor (WPD) board."""

from __future__ import annotations

import argparse
import json
import os
import sys
from collections import defaultdict, deque
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
ACCEL_ROOT = REPO_ROOT / "external" / "ipfs_accelerate"

for key, value in {
    "IPFS_ACCELERATE_DUCKDB_ONLY": "1",
    "IPFS_ACCEL_SKIP_CORE": "1",
    "IPFS_KIT_DISABLE": "1",
    "IPFS_DATASETS_AUTO_INSTALL": "false",
    "IPFS_AUTO_INSTALL": "false",
    "IPFS_DATASETS_PY_MINIMAL_IMPORTS": "1",
    "PYTHONDONTWRITEBYTECODE": "1",
}.items():
    os.environ.setdefault(key, value)

if str(ACCEL_ROOT) not in sys.path:
    sys.path.insert(0, str(ACCEL_ROOT))

from ipfs_accelerate_py.agent_supervisor.objectives.objective_graph import (  # noqa: E402
    parse_goal_heap,
)
from ipfs_accelerate_py.agent_supervisor.todo_daemon.implementation_daemon import (  # noqa: E402
    parse_task_file,
)

PLAN_PATH = (
    REPO_ROOT
    / "implementation_plan"
    / "docs"
    / "47-supervisor-worker-planner-doctor-integration-plan-2026-08-06.md"
)
OBJECTIVE_PATH = (
    REPO_ROOT
    / "implementation_plan"
    / "docs"
    / "47-supervisor-worker-planner-doctor-integration.objectives.md"
)
TODO_PATH = (
    REPO_ROOT
    / "implementation_plan"
    / "docs"
    / "47-supervisor-worker-planner-doctor-integration.todo.md"
)
SCHEDULER_PATH = (
    REPO_ROOT / "config" / "supervisor_worker_planner_doctor_integration_scheduler.json"
)
VALIDATOR_PATH = REPO_ROOT / "scripts" / "validate_supervisor_worker_planner_doctor_board.py"
CONTROLLER_PATH = REPO_ROOT / "scripts" / "supervisor_worker_planner_doctor_supervisor.sh"
SUPERVISOR_CONFIG_PATH = REPO_ROOT / "config" / "supervisor_worker_planner_doctor_supervisor.json"

EXPECTED_GOAL_IDS = frozenset(
    {
        "WPD-G000",
        "WPD-G010",
        "WPD-G020",
        "WPD-G030",
        "WPD-G040",
        "WPD-G050",
        "WPD-G060",
        "WPD-G070",
    }
)
EXPECTED_TASK_IDS = frozenset(
    {
        "WPD-000",
        "WPD-001",
        "WPD-002",
        "WPD-003",
        "WPD-010",
        "WPD-011",
        "WPD-012",
        "WPD-020",
        "WPD-021",
        "WPD-022",
        "WPD-023",
        "WPD-030",
        "WPD-031",
        "WPD-032",
        "WPD-040",
        "WPD-041",
        "WPD-042",
        "WPD-050",
        "WPD-051",
        "WPD-060",
        "WPD-061",
        "WPD-070",
    }
)
READY_AFTER_BOOTSTRAP = frozenset({"WPD-001", "WPD-002", "WPD-003"})
TERMINAL_TASK_ID = "WPD-070"
TASK_PREFIX = "## WPD-"
BOARD_NAMESPACE = "agent-supervisor-worker-planner-doctor-v1"


def _completed_statuses() -> frozenset[str]:
    return frozenset({"completed", "complete", "done", "verified_complete"})


def _is_completed(status: str) -> bool:
    return str(status or "").strip().lower() in _completed_statuses()


def _goal_id(task) -> str:
    meta = getattr(task, "metadata", None) or {}
    if isinstance(meta, dict):
        for key in ("goal id", "goal_id", "Goal id"):
            value = str(meta.get(key) or "").strip()
            if value:
                return value
    return str(getattr(task, "goal_id", "") or "").strip()


def validate() -> dict[str, object]:
    errors: list[str] = []
    for path in (
        PLAN_PATH,
        OBJECTIVE_PATH,
        TODO_PATH,
        SCHEDULER_PATH,
        VALIDATOR_PATH,
    ):
        if not path.is_file():
            errors.append(f"missing control artifact: {path.relative_to(REPO_ROOT)}")

    tasks = parse_task_file(TODO_PATH, TASK_PREFIX)
    task_ids = [task.task_id for task in tasks]
    task_set = set(task_ids)
    if len(task_ids) != len(task_set):
        errors.append("duplicate task ids in todo board")
    if task_set != EXPECTED_TASK_IDS:
        missing = sorted(EXPECTED_TASK_IDS - task_set)
        extra = sorted(task_set - EXPECTED_TASK_IDS)
        if missing:
            errors.append(f"missing tasks: {missing}")
        if extra:
            errors.append(f"unexpected tasks: {extra}")

    goals = parse_goal_heap(OBJECTIVE_PATH.read_text(encoding="utf-8"))
    goal_ids = {goal.goal_id for goal in goals}
    if goal_ids != EXPECTED_GOAL_IDS:
        errors.append(
            "goal id mismatch: "
            f"missing={sorted(EXPECTED_GOAL_IDS - goal_ids)} "
            f"extra={sorted(goal_ids - EXPECTED_GOAL_IDS)}"
        )

    dep_graph: dict[str, list[str]] = {}
    for task in tasks:
        deps = [str(item) for item in (task.depends_on or [])]
        dep_graph[task.task_id] = deps
        for dep in deps:
            if dep not in EXPECTED_TASK_IDS:
                errors.append(f"{task.task_id} depends on unknown task {dep}")
        goal = _goal_id(task)
        if goal and goal not in EXPECTED_GOAL_IDS:
            errors.append(f"{task.task_id} references unknown goal {goal}")
        ns = str(getattr(task, "board_namespace", "") or "")
        if ns and ns != BOARD_NAMESPACE:
            errors.append(f"{task.task_id} board_namespace {ns!r} != {BOARD_NAMESPACE!r}")

    # Acyclicity via Kahn
    indegree: dict[str, int] = {tid: 0 for tid in dep_graph}
    children: dict[str, list[str]] = defaultdict(list)
    for tid, deps in dep_graph.items():
        for dep in deps:
            if dep in indegree:
                children[dep].append(tid)
                indegree[tid] += 1
    queue = deque(sorted(tid for tid, deg in indegree.items() if deg == 0))
    seen = 0
    while queue:
        node = queue.popleft()
        seen += 1
        for child in children[node]:
            indegree[child] -= 1
            if indegree[child] == 0:
                queue.append(child)
    if seen != len(dep_graph):
        errors.append("dependency graph contains a cycle")

    completed = {
        task.task_id
        for task in tasks
        if _is_completed(str(getattr(task, "status", "") or ""))
        or _is_completed(str((getattr(task, "metadata", {}) or {}).get("status") or ""))
    }
    # Prefer metadata status when parser maps active -> in_progress
    meta_completed = set()
    for task in tasks:
        meta = getattr(task, "metadata", None) or {}
        if isinstance(meta, dict) and _is_completed(str(meta.get("status") or "")):
            meta_completed.add(task.task_id)
    completed |= meta_completed

    ready = sorted(
        task.task_id
        for task in tasks
        if task.task_id not in completed
        and all(dep in completed for dep in (task.depends_on or []))
    )

    bootstrap_done = "WPD-000" in completed
    if bootstrap_done:
        expected_ready = READY_AFTER_BOOTSTRAP - completed
        if not expected_ready.issubset(set(ready)):
            errors.append(
                "after WPD-000 complete, expected ready tasks "
                f"{sorted(expected_ready)}; got {ready}"
            )
    else:
        if set(ready) != {"WPD-000"}:
            errors.append(f"before bootstrap, only WPD-000 should be ready; got {ready}")

    if TERMINAL_TASK_ID not in task_set:
        errors.append(f"missing terminal task {TERMINAL_TASK_ID}")

    scheduler: dict[str, object] = {}
    if SCHEDULER_PATH.is_file():
        scheduler = json.loads(SCHEDULER_PATH.read_text(encoding="utf-8"))
        if scheduler.get("boardNamespace") != BOARD_NAMESPACE:
            errors.append("scheduler boardNamespace mismatch")
        if scheduler.get("taskPrefix") not in {"WPD-", "## WPD-"}:
            errors.append("scheduler taskPrefix mismatch")

    payload = {
        "schema": "ipfs_accelerate_py/worker-planner-doctor-board-validation@1",
        "valid": not errors,
        "errors": errors,
        "task_count": len(task_ids),
        "total_task_count": len(task_ids),
        "expected_task_count": len(EXPECTED_TASK_IDS),
        "goal_count": len(goal_ids),
        "expected_goal_ids": sorted(EXPECTED_GOAL_IDS),
        "task_ids": task_ids,
        "completed_task_ids": sorted(completed),
        "completed_task_count": len(completed),
        "ready_task_ids": ready,
        "ready_after_bootstrap": sorted(READY_AFTER_BOOTSTRAP),
        "bootstrap_completed": bootstrap_done,
        "terminal_task_id": TERMINAL_TASK_ID,
        "board_namespace": BOARD_NAMESPACE,
        "control_artifacts": {
            "plan": str(PLAN_PATH.relative_to(REPO_ROOT)),
            "objectives": str(OBJECTIVE_PATH.relative_to(REPO_ROOT)),
            "todo": str(TODO_PATH.relative_to(REPO_ROOT)),
            "scheduler": str(SCHEDULER_PATH.relative_to(REPO_ROOT)),
            "validator": str(VALIDATOR_PATH.relative_to(REPO_ROOT)),
            "controller": str(CONTROLLER_PATH.relative_to(REPO_ROOT)),
            "supervisor_config": str(SUPERVISOR_CONFIG_PATH.relative_to(REPO_ROOT)),
        },
    }
    return payload


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check-all", action="store_true", help="Full board validation")
    parser.add_argument("--json", action="store_true", help="Emit JSON only")
    parser.parse_args(argv)
    payload = validate()
    text = json.dumps(payload, indent=2, sort_keys=True)
    print(text)
    if not payload["valid"]:
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
