"""Successor tasks append without completing a parked parent."""

from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path("/home/barberb/lift_coding")
sys.path.insert(0, str(ROOT / "scripts"))

from svf_admit_successor_tasks import admit_text  # noqa: E402
from svf_successor_subgoal_check import check_subgoal  # noqa: E402


PLAN = {
    "subgoals": [
        {
            "subgoal_id": "ceiling-abc",
            "parent_goal_id": "SVF-G623",
            "blocked_task_id": "SVF-1023",
            "ceiling_kind": "owner_lacks_declared_queue",
            "title": "Align the declared postcondition",
            "acceptance": ["The parent visual task stays blocked."],
            "source": "deterministic",
        }
    ]
}

BOARD = """## SVF-900 Rerun

- Status: ready
- Depends on: SVF-1023, SVF-1032

## SVF-1023 Training Manager

- Status: blocked
- Depends on: SVF-100
"""


class SuccessorTaskTests(unittest.TestCase):
    def test_admit_appends_and_keeps_parent_lines(self) -> None:
        updated, admitted = admit_text(BOARD, PLAN)
        self.assertEqual(admitted, ["SVF-G1023-C"])
        self.assertTrue(updated.startswith(BOARD if BOARD.endswith("\n") else BOARD + "\n"))
        section = updated.split("## SVF-G1023-C", 1)[1]
        self.assertIn("- Status: blocked\n", section)
        self.assertIn("- Depends on: SVF-1023, SVF-1032", updated)
        self.assertIn(
            "python3 scripts/swissknife_visual_functional_worker.py --task-id SVF-G1023-C",
            section,
        )
        self.assertIn(
            "python3 scripts/swissknife_visual_functional_worker.py --validate --task-id SVF-G1023-C",
            section,
        )
        self.assertNotIn("svf_successor_subgoal_check.py", section)
        self.assertNotIn("- Satisfies:", updated)
        again, more = admit_text(updated, PLAN)
        self.assertEqual(more, [])
        self.assertEqual(again, updated)

    def test_check_passes_while_parent_is_blocked(self) -> None:
        self.assertEqual(check_subgoal(PLAN, BOARD, "ceiling-abc"), 0)

    def test_check_refuses_a_completed_protected_parent(self) -> None:
        completed = BOARD.replace("- Status: blocked", "- Status: completed")
        self.assertEqual(check_subgoal(PLAN, completed, "ceiling-abc"), 1)

    def test_cli_check_writes_nothing(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            plan = root / "plan.json"
            board = root / "board.md"
            plan.write_text(json.dumps(PLAN), encoding="utf-8")
            board.write_text(BOARD, encoding="utf-8")
            before = board.read_bytes()
            result = subprocess.run(
                [
                    sys.executable,
                    str(ROOT / "scripts" / "svf_successor_subgoal_check.py"),
                    "--subgoal-id",
                    "ceiling-abc",
                    "--plan",
                    str(plan),
                    "--board",
                    str(board),
                ],
                check=False,
                capture_output=True,
                text=True,
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(board.read_bytes(), before)


if __name__ == "__main__":
    unittest.main()
