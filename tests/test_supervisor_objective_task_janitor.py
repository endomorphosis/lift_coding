from __future__ import annotations

import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
IPFS_ACCELERATE_ROOT = REPO_ROOT / "external" / "ipfs_accelerate"


def _imports():
    sys.path.insert(0, str(IPFS_ACCELERATE_ROOT))
    from ipfs_accelerate_py.agent_supervisor.objective_graph import ObjectiveGoal
    from ipfs_accelerate_py.agent_supervisor.objective_task_janitor import (
        JANITOR_RECEIPT_SCHEMA,
        reconcile_objective_task_strategy,
    )
    from ipfs_accelerate_py.agent_supervisor.todo_daemon.implementation_daemon import PortalTask

    return ObjectiveGoal, PortalTask, JANITOR_RECEIPT_SCHEMA, reconcile_objective_task_strategy


def test_objective_task_janitor_blocks_orphans_deprioritizes_noise_and_reopens_launch_goal():
    ObjectiveGoal, PortalTask, schema, reconcile = _imports()
    goals = [
        ObjectiveGoal(
            "VAIOS-G697",
            "Production launch readiness gate",
            {
                "status": "active",
                "fib_priority": "1",
                "priority": "P0",
                "track": "launch",
                "goal": "Phone-hosted Swissknife virtual desktop with desktop offload and Meta glasses terminal.",
            },
        ),
        ObjectiveGoal(
            "VAIOS-G111",
            "Completed scanner churn",
            {"status": "completed", "fib_priority": "8", "priority": "P3", "track": "ops"},
        ),
    ]
    tasks = [
        PortalTask(
            "VAI-001",
            "Old generated task",
            "todo",
            "manual",
            "P2",
            "ops",
            metadata={"goal id": "VAIOS-G111"},
        ),
        PortalTask(
            "VAI-002",
            "Objective scan: generic AST scrape",
            "todo",
            "manual",
            "P3",
            "ops",
            metadata={"missing evidence": "generic symbol match", "bundle shard": "data/old.todo.md"},
        ),
    ]
    strategy = {
        "blocked_tasks": ["VAI-KEEP", "VAI-OLD"],
        "deprioritized_tasks": ["VAI-KEEP-D", "VAI-OLD-D"],
        "objective_task_janitor_receipts": [
            {"schema": schema, "action": "block", "task_id": "VAI-OLD"},
            {"schema": schema, "action": "deprioritize", "task_id": "VAI-OLD-D"},
        ],
    }

    result = reconcile(goals=goals, tasks=tasks, strategy=strategy, now="2026-06-23T00:00:00+00:00")
    updated = result["strategy"]

    assert result["changed"]
    assert updated["blocked_tasks"] == ["VAI-KEEP", "VAI-001"]
    assert updated["deprioritized_tasks"] == ["VAI-KEEP-D", "VAI-002"]
    assert updated["objective_task_janitor_reopen_goal_ids"] == ["VAIOS-G697"]
    assert updated["objective_task_janitor_force_goal_ids"] == ["VAIOS-G697"]
    assert updated["heap_goal_retirement_receipt"][0]["retired_task_reason"] == "goal_completed"
    assert all(receipt["schema"] == schema for receipt in updated["objective_task_janitor_receipts"])


def test_objective_task_janitor_releases_owned_blocks_when_goal_has_open_work():
    ObjectiveGoal, PortalTask, schema, reconcile = _imports()
    goals = [
        ObjectiveGoal(
            "VAIOS-G697",
            "Production launch readiness gate",
            {
                "status": "active",
                "fib_priority": "1",
                "priority": "P0",
                "track": "launch",
                "goal": "Phone-hosted Swissknife virtual desktop with desktop offload and Meta glasses terminal.",
            },
        )
    ]
    tasks = [
        PortalTask(
            "VAI-003",
            "Launch gate implementation",
            "todo",
            "manual",
            "P0",
            "launch",
            metadata={"goal id": "VAIOS-G697"},
        )
    ]
    strategy = {
        "blocked_tasks": ["VAI-003", "VAI-KEEP"],
        "objective_task_janitor_receipts": [
            {"schema": schema, "action": "block", "task_id": "VAI-003"},
        ],
    }

    result = reconcile(goals=goals, tasks=tasks, strategy=strategy, now="2026-06-23T00:00:00+00:00")
    updated = result["strategy"]

    assert result["changed"]
    assert updated["blocked_tasks"] == ["VAI-KEEP"]
    assert updated["objective_task_janitor_reopen_goal_ids"] == []
    assert result["open_goal_ids"] == ["VAIOS-G697"]
