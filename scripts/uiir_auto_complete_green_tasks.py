#!/usr/bin/env python3
"""Mark UIIR board tasks completed when validation is already green.

The UIIR board uses Completion: manual and protects the todo path from agent
edits. Implementers can land green code without promoting Status: completed,
which stalls dependency unlock. This companion re-reads the board, runs each
ready task's Validation command from the monorepo root, and marks Status:
completed when validation exits 0.

Intended for unattended board drain alongside launch_uiir_grok_lanes.sh.
Safe: only upgrades todo -> completed; never reopens completed tasks.
"""

from __future__ import annotations

import argparse
import os
import re
import subprocess
import sys
from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class Task:
    task_id: str
    title: str
    status: str
    depends: list[str] = field(default_factory=list)
    validation: str = ""
    start: int = 0  # line index of ## header
    status_line: int = -1


def parse_board(text: str) -> list[Task]:
    lines = text.splitlines()
    tasks: list[Task] = []
    cur: Task | None = None
    for i, line in enumerate(lines):
        m = re.match(r"^## (UIR-\d+)\s+(.*)$", line)
        if m:
            cur = Task(task_id=m.group(1), title=m.group(2).strip(), status="", start=i)
            tasks.append(cur)
            continue
        if cur is None:
            continue
        if line.startswith("- Status:"):
            cur.status = line.split(":", 1)[1].strip()
            cur.status_line = i
        elif line.startswith("- Depends on:"):
            deps = line.split(":", 1)[1].strip()
            cur.depends = [
                d.strip() for d in deps.split(",") if d.strip() and d.strip().lower() != "none"
            ]
        elif line.startswith("- Validation:"):
            cur.validation = line.split(":", 1)[1].strip()
    return tasks


def ready_tasks(tasks: list[Task]) -> list[Task]:
    done = {t.task_id for t in tasks if t.status == "completed"}
    out: list[Task] = []
    for t in tasks:
        if t.status != "todo":
            continue
        if all(d in done for d in t.depends):
            out.append(t)
    return out


def run_validation(root: Path, command: str, timeout: int) -> tuple[bool, str]:
    if not command.strip():
        return False, "empty validation"
    env = os.environ.copy()
    env.setdefault("PYTHONPATH", str(root / "external" / "ipfs_accelerate"))
    # Board Validation commands often use bare `python`; ensure it resolves.
    python3 = env.get("PYTHON") or env.get("PYTHON3") or "/usr/bin/python3"
    if Path(python3).exists():
        env["PATH"] = f"{Path(python3).parent}:{env.get('PATH', '')}"
        # Rewrite leading `python ` / `python -m` to python3 for hermetic envs.
        rewritten = command
        if rewritten.startswith("python "):
            rewritten = python3 + rewritten[6:]
        rewritten = rewritten.replace("&& python ", f"&& {python3} ")
        rewritten = rewritten.replace("; python ", f"; {python3} ")
        command = rewritten
    try:
        proc = subprocess.run(
            command,
            shell=True,
            cwd=str(root),
            env=env,
            capture_output=True,
            text=True,
            timeout=timeout,
        )
    except subprocess.TimeoutExpired:
        return False, f"timeout after {timeout}s"
    if proc.returncode == 0:
        return True, "ok"
    tail = (proc.stdout or "")[-400:] + (proc.stderr or "")[-400:]
    return False, f"exit={proc.returncode} {tail.strip()[:300]}"


def mark_completed(text: str, task: Task) -> str:
    lines = text.splitlines()
    if task.status_line < 0 or task.status_line >= len(lines):
        raise RuntimeError(f"no status line for {task.task_id}")
    line = lines[task.status_line]
    if not line.startswith("- Status:"):
        raise RuntimeError(f"bad status line for {task.task_id}: {line!r}")
    lines[task.status_line] = "- Status: completed"
    return "\n".join(lines) + ("\n" if text.endswith("\n") else "")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--root",
        type=Path,
        default=Path(__file__).resolve().parents[1],
        help="Monorepo / worktree root",
    )
    parser.add_argument(
        "--todo-path",
        default="implementation_plan/docs/45-ipfs-datasets-ui-ux-ir.todo.md",
    )
    parser.add_argument("--timeout", type=int, default=600)
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Report what would complete without writing the board",
    )
    parser.add_argument(
        "--once",
        action="store_true",
        help="Single pass (default). Use with systemd/cron for loops.",
    )
    args = parser.parse_args()
    root = args.root.resolve()
    board_path = root / args.todo_path
    if not board_path.is_file():
        print(f"board missing: {board_path}", file=sys.stderr)
        return 2

    text = board_path.read_text(encoding="utf-8")
    tasks = parse_board(text)
    ready = ready_tasks(tasks)
    if not ready:
        print("no ready todo tasks")
        return 0

    completed_ids: list[str] = []
    for task in ready:
        print(f"check {task.task_id}: {task.title[:60]}")
        ok, detail = run_validation(root, task.validation, args.timeout)
        if not ok:
            print(f"  skip ({detail[:120]})")
            continue
        print("  validation green -> complete")
        if not args.dry_run:
            text = mark_completed(text, task)
            # re-parse status_line positions after mutation
            tasks = parse_board(text)
            # keep completed set updated for subsequent deps in same pass
            for t in tasks:
                if t.task_id == task.task_id:
                    t.status = "completed"
        completed_ids.append(task.task_id)
        # After marking, more tasks may become ready in a follow-up pass.
        # Single pass only marks currently-ready greens; operator/cron re-runs.

    if completed_ids and not args.dry_run:
        board_path.write_text(text, encoding="utf-8")
        print(f"wrote {board_path} marked={','.join(completed_ids)}")
    elif completed_ids:
        print(f"dry-run would mark: {','.join(completed_ids)}")
    else:
        print("no green ready tasks to complete")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
