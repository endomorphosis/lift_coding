#!/usr/bin/env python3
"""Thin entrypoint for the monorepo CI deferred suite re-enable (CIG) board.

Parses and (optionally) drives `ipfs_accelerate_py.agent_supervisor` against:

  implementation_plan/docs/47-monorepo-ci-deferred-suite-reenables.todo.md

Examples
--------
Parse/list claimable tasks (default --once dry inventory)::

    PYTHONPATH=external/ipfs_accelerate \\
      python3 scripts/monorepo_ci_reenables_todo_supervisor.py --once

Hand off to the full implementation supervisor::

    PYTHONPATH=src:external/ipfs_accelerate \\
      python3 -m ipfs_accelerate_py.agent_supervisor.todo_daemon.implementation_supervisor \\
        --todo-path implementation_plan/docs/47-monorepo-ci-deferred-suite-reenables.todo.md \\
        --task-prefix '## CIG-'
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_TODO_PATH = (
    REPO_ROOT / "implementation_plan" / "docs" / "47-monorepo-ci-deferred-suite-reenables.todo.md"
)
TASK_PREFIX = "## CIG-"
ACCELERATE_ROOT = REPO_ROOT / "external" / "ipfs_accelerate"


def _ensure_accelerate_path() -> None:
    if not ACCELERATE_ROOT.is_dir():
        raise SystemExit(
            f"error: {ACCELERATE_ROOT} is missing; run "
            "`git submodule update --init external/ipfs_accelerate`"
        )
    accelerate = str(ACCELERATE_ROOT)
    if accelerate not in sys.path:
        sys.path.insert(0, accelerate)


def _parse_tasks(todo_path: Path):
    _ensure_accelerate_path()
    from ipfs_accelerate_py.agent_supervisor.todo_daemon.implementation_daemon import (
        parse_task_file,
    )

    return parse_task_file(todo_path, TASK_PREFIX)


def _claimable(tasks) -> list:
    """Tasks that are open and not blocked by incomplete dependencies."""
    by_id = {task.task_id: task for task in tasks}
    open_ids = {
        task.task_id
        for task in tasks
        if str(task.status).lower() not in {"complete", "completed", "done", "succeeded"}
    }
    claimable = []
    for task in tasks:
        status = str(task.status).lower()
        if status in {"complete", "completed", "done", "succeeded"}:
            continue
        meta = task.metadata or {}
        if str(meta.get("is schedulable", meta.get("is_schedulable", "true"))).lower() in {
            "false",
            "0",
            "no",
        }:
            continue
        blocked = [dep for dep in task.depends_on if dep in open_ids or dep not in by_id]
        # Dependencies still open (not completed) block claim.
        blocked = [
            dep
            for dep in task.depends_on
            if dep not in by_id
            or str(by_id[dep].status).lower() not in {"complete", "completed", "done", "succeeded"}
        ]
        if blocked:
            continue
        claimable.append(task)
    return claimable


def _summarize(tasks) -> dict:
    claimable = _claimable(tasks)
    by_status: dict[str, int] = {}
    for task in tasks:
        by_status[task.status] = by_status.get(task.status, 0) + 1
    lanes: dict[str, list[str]] = {}
    for task in claimable:
        meta = task.metadata or {}
        lane = meta.get("parallel lane") or meta.get("parallel_lane") or "default"
        lanes.setdefault(lane, []).append(task.task_id)
    return {
        "todo_path": str(DEFAULT_TODO_PATH.relative_to(REPO_ROOT)),
        "task_prefix": TASK_PREFIX,
        "task_count": len(tasks),
        "status_counts": by_status,
        "claimable_count": len(claimable),
        "claimable_task_ids": [task.task_id for task in claimable],
        "parallel_lanes": lanes,
        "predicted_file_overlap": _predicted_overlap(claimable),
    }


def _predicted_overlap(tasks) -> list[dict]:
    """Report pairwise predicted_files intersections among claimable tasks."""
    owners: dict[str, list[str]] = {}
    for task in tasks:
        meta = task.metadata or {}
        raw = meta.get("predicted files") or meta.get("predicted_files") or ""
        paths = [part.strip() for part in raw.split(",") if part.strip()]
        if not paths:
            paths = list(task.outputs or [])
        for path in paths:
            owners.setdefault(path, []).append(task.task_id)
    return [
        {"path": path, "task_ids": task_ids}
        for path, task_ids in sorted(owners.items())
        if len(task_ids) > 1
    ]


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--todo-path",
        type=Path,
        default=DEFAULT_TODO_PATH,
        help="Path to the CIG todo board",
    )
    parser.add_argument(
        "--once",
        action="store_true",
        help="Parse the board once, print claimable inventory as JSON, and exit",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Always emit JSON (default with --once)",
    )
    parser.add_argument(
        "--implement",
        action="store_true",
        help="Delegate to implementation_supervisor after printing inventory",
    )
    args = parser.parse_args(argv)

    todo_path = args.todo_path
    if not todo_path.is_file():
        print(f"error: board missing: {todo_path}", file=sys.stderr)
        return 2

    tasks = _parse_tasks(todo_path)
    summary = _summarize(tasks)
    if args.once or args.json or not args.implement:
        print(json.dumps(summary, indent=2, sort_keys=True))
        if summary["predicted_file_overlap"]:
            print(
                f"warning: claimable predicted_files overlap {summary['predicted_file_overlap']}",
                file=sys.stderr,
            )

    if args.implement:
        _ensure_accelerate_path()
        from ipfs_accelerate_py.agent_supervisor.todo_daemon.implementation_supervisor import (
            main as implementation_supervisor_main,
        )

        # Forward remaining argv style flags via a minimal argv rebuild.
        implement_argv = [
            "--todo-path",
            str(todo_path),
            "--task-prefix",
            TASK_PREFIX,
        ]
        return int(implementation_supervisor_main(implement_argv) or 0)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
