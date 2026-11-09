#!/usr/bin/env python3
"""Confirm one recorded successor subgoal without completing its parent.

The check reads the proof-ceiling plan and the task board. It does not write
either file, drop a dependency, or mark a parent task completed.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


ROOT = Path("/home/barberb/lift_coding")
PLAN = ROOT / "data/agent_supervisor/swissknife_visual_functional/state/proof-ceiling-plan.json"
BOARD = ROOT / "implementation_plan/docs/53-swissknife-visual-functional-mcplusplus.todo.md"
PROTECTED = frozenset({
    "owner_lacks_declared_queue",
    "failed_outcome_not_semantic",
    "dependency_blocked",
})
COMPLETED = frozenset({"completed", "complete", "done"})


def _load(path: Path) -> dict:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    return payload if isinstance(payload, dict) else {}


def _status(board_text: str, task_id: str) -> str:
    current = ""
    for line in board_text.splitlines():
        if line.startswith("## "):
            current = line[3:].strip().split(" ", 1)[0]
            continue
        if current == task_id and line.strip().lower().startswith("- status:"):
            return line.split(":", 1)[1].strip().lower()
    return ""


def check_subgoal(plan: dict, board_text: str, subgoal_id: str) -> int:
    """Return 0 when the subgoal is recorded and its protected parent is open."""

    subgoals = plan.get("subgoals")
    if not isinstance(subgoals, list):
        print("subgoal plan missing", file=sys.stderr)
        return 1
    found = None
    for item in subgoals:
        if isinstance(item, dict) and str(item.get("subgoal_id") or "") == subgoal_id:
            found = item
            break
    if found is None or found.get("source") != "deterministic":
        print(f"subgoal {subgoal_id} is not a recorded deterministic successor", file=sys.stderr)
        return 1
    blocked = str(found.get("blocked_task_id") or "")
    if not blocked or blocked == subgoal_id:
        print("subgoal does not name a distinct blocked task", file=sys.stderr)
        return 1
    if f"## {blocked} " not in board_text and f"## {blocked}\n" not in board_text:
        print(f"blocked task {blocked} is not on the board", file=sys.stderr)
        return 1
    status = _status(board_text, blocked)
    if str(found.get("ceiling_kind") or "") in PROTECTED and status in COMPLETED:
        print(f"protected parent {blocked} is completed", file=sys.stderr)
        return 1
    print(
        f"subgoal ok {subgoal_id} blocked_task={blocked} "
        "parent_not_completed_by_this_check"
    )
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--subgoal-id", required=True)
    parser.add_argument("--plan", type=Path, default=PLAN)
    parser.add_argument("--board", type=Path, default=BOARD)
    args = parser.parse_args(argv)
    board_text = args.board.read_text(encoding="utf-8") if args.board.is_file() else ""
    return check_subgoal(_load(args.plan), board_text, args.subgoal_id)


if __name__ == "__main__":
    sys.exit(main())
