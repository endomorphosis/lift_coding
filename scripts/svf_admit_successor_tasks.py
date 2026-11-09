#!/usr/bin/env python3
"""Append missing successor tasks for a parked visual-functional frontier.

Each new task is blocked, depends on none, and names the visual worker.
It is not selectable. Existing headings, statuses, and Depends on lines are
copied unchanged. Parents are not completed and SVF-900 is not selected.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import tempfile
from pathlib import Path


ROOT = Path("/home/barberb/lift_coding")
PLAN = ROOT / "data/agent_supervisor/swissknife_visual_functional/state/proof-ceiling-plan.json"
BOARD = ROOT / "implementation_plan/docs/53-swissknife-visual-functional-mcplusplus.todo.md"
_SUFFIX = {
    "owner_lacks_declared_queue": "C",
    "failed_outcome_not_semantic": "F",
    "exhausted_child_clock": "X",
    "dependency_blocked": "W",
    "bounded_refinement": "L",
}


def heading_id(task_id: str, kind: str) -> str:
    suffix = _SUFFIX[kind]
    if task_id.startswith("SVF-FINAL-R") and task_id[11:].isdigit():
        return f"SVF-GR{task_id[11:]}-{suffix}"
    digits = "".join(character for character in task_id if character.isdigit())
    if not digits:
        raise ValueError(f"task id has no goal digits: {task_id}")
    return f"SVF-G{digits}-{suffix}"


def _existing_ids(text: str) -> set[str]:
    found: set[str] = set()
    for line in text.splitlines():
        if line.startswith("## "):
            found.add(line[3:].strip().split(" ", 1)[0])
    return found


def _section(subgoal: dict) -> str:
    task_id = str(subgoal["blocked_task_id"])
    kind = str(subgoal["ceiling_kind"])
    heading = heading_id(task_id, kind)
    title = " ".join(str(subgoal.get("title") or "").split())
    parent = str(subgoal.get("parent_goal_id") or "")
    acceptance = subgoal.get("acceptance") or []
    if not isinstance(acceptance, list):
        acceptance = []
    joined = " ".join(" ".join(str(item).split()) for item in acceptance)
    command = f"python3 scripts/swissknife_visual_functional_worker.py --task-id {heading}"
    validation = f"python3 scripts/swissknife_visual_functional_worker.py --validate --task-id {heading}"
    return (
        f"\n## {heading} {title}\n\n"
        f"- Status: blocked\n"
        f"- Priority: P1\n"
        f"- Track: successor-subgoal\n"
        f"- Depends on: none\n"
        f"- Goal id: {parent}\n"
        f"- Outputs: data/agent_supervisor/swissknife_visual_functional/state/proof-ceiling-plan.json\n"
        f"- Deterministic command: {command}\n"
        f"- Validation: {validation}\n"
        f"- Predicted files: data/agent_supervisor/swissknife_visual_functional/state/proof-ceiling-plan.json\n"
        f"- Implementation timeout seconds: 120\n"
        f"- Resource class: cpu-small\n"
        f"- Conflict policy: Do not mark the parent completed, drop a dependency, invent owner evidence, or replace a receipt.\n"
        f"- Acceptance: {joined} The parent task is not completed by this task.\n"
    )


def admit_text(todo_text: str, plan: dict) -> tuple[str, list[str]]:
    """Return the board text and the ids appended. The original text is a prefix."""

    subgoals = plan.get("subgoals")
    if not isinstance(subgoals, list):
        return todo_text, []
    existing = _existing_ids(todo_text)
    sections: list[str] = []
    admitted: list[str] = []
    for item in subgoals:
        if not isinstance(item, dict) or item.get("source") != "deterministic":
            continue
        task_id = str(item.get("blocked_task_id") or "")
        kind = str(item.get("ceiling_kind") or "")
        subgoal_id = str(item.get("subgoal_id") or "")
        if kind not in _SUFFIX or not task_id or not subgoal_id:
            continue
        if any(char in subgoal_id for char in ";|&$`<>\n "):
            continue
        heading = heading_id(task_id, kind)
        if heading in existing or heading in admitted:
            continue
        sections.append(_section(item))
        admitted.append(heading)
        existing.add(heading)
    if not sections:
        return todo_text, []
    base = todo_text if todo_text.endswith("\n") else todo_text + "\n"
    return base + "".join(sections), admitted


def _atomic_write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary = tempfile.mkstemp(dir=path.parent, prefix=".svf-successor-")
    try:
        os.write(descriptor, text.encode())
        os.fsync(descriptor)
        os.close(descriptor)
        descriptor = -1
        os.chmod(temporary, 0o644)
        os.replace(temporary, path)
        temporary = ""
    finally:
        if descriptor >= 0:
            os.close(descriptor)
        if temporary:
            try:
                os.unlink(temporary)
            except OSError:
                pass


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--plan", type=Path, default=PLAN)
    parser.add_argument("--todo", type=Path, default=BOARD)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args(argv)
    plan = json.loads(args.plan.read_text(encoding="utf-8"))
    original = args.todo.read_text(encoding="utf-8")
    updated, admitted = admit_text(original, plan)
    if not updated.startswith(original if original.endswith("\n") else original + "\n") and admitted:
        print("refused: admit would rewrite existing board text", file=sys.stderr)
        return 2
    if admitted and not args.dry_run:
        _atomic_write(args.todo, updated)
    print("admitted=" + str(len(admitted)) + " ids=" + ",".join(admitted))
    return 0


if __name__ == "__main__":
    sys.exit(main())
