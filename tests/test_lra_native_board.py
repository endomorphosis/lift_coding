"""Parse-only checks for the Lean Refactor Arena native board."""
from __future__ import annotations

import json
import os
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]


def _parsers():
    os.environ.setdefault("IPFS_ACCEL_SKIP_CORE", "1")
    os.environ.setdefault("IPFS_AUTO_INSTALL", "false")
    sys.path.insert(0, str(ROOT / "external/ipfs_accelerate"))
    from ipfs_accelerate_py.agent_supervisor.objectives.objective_graph import parse_goal_heap
    from ipfs_accelerate_py.agent_supervisor.todo_daemon.implementation_daemon import parse_task_file
    return parse_goal_heap, parse_task_file


class LRANativeBoardTests(unittest.TestCase):
    def test_goals_and_tasks_parse_with_parallel_ready_set(self):
        parse_goals, parse_tasks = _parsers()
        folder = ROOT / "papers/completion/lean_refactor_arena"
        goals = parse_goals((folder / "paper.objectives.md").read_text())
        tasks = parse_tasks(folder / "paper.todo.md", "LRA-")
        manifest = json.loads((folder / "tasks.json").read_text())
        self.assertEqual([g.goal_id for g in goals][0], "LRA-G000")
        self.assertEqual({g.goal_id for g in goals[1:]}, {s["id"] for s in manifest["subgoals"]})
        self.assertEqual({t.task_id for t in tasks}, {row["id"] for row in manifest["tasks"]})
        completed = {t.task_id for t in tasks if t.status == "completed"}
        ready = [
            t.task_id
            for t in tasks
            if t.status in {"todo", "ready", "needed"} and set(t.depends_on).issubset(completed)
        ]
        self.assertEqual(sorted(ready), ["LRA-010", "LRA-011", "LRA-012"])
        self.assertEqual(
            {t.task_id for t in tasks if t.status == "blocked"},
            {"LRA-024", "LRA-025", "LRA-027"},
        )
        for task in tasks:
            self.assertEqual(task.board_namespace, "vericodegen-2026-lean_refactor_arena")
            self.assertTrue(task.validation and task.outputs and task.acceptance)
            seed = next(row for row in manifest["tasks"] if row["id"] == task.task_id)
            self.assertEqual(task.acceptance, "; ".join(seed["acceptance_criteria"]))
            self.assertEqual(task.metadata.get("goal id"), seed["subgoal_id"])


if __name__ == "__main__":
    unittest.main()
