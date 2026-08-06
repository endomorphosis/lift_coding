"""Parser/smoke tests for the monorepo CI deferred suite re-enable (CIG) board."""

from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
IPFS_ACCELERATE_ROOT = REPO_ROOT / "external" / "ipfs_accelerate"
SCRIPTS_DIR = REPO_ROOT / "scripts"
TODO_PATH = (
    REPO_ROOT / "implementation_plan" / "docs" / "47-monorepo-ci-deferred-suite-reenables.todo.md"
)
PLAN_PATH = (
    REPO_ROOT / "implementation_plan" / "docs" / "47-monorepo-ci-deferred-suite-reenables.md"
)
TASK_PREFIX = "## CIG-"

WAVE_A = [
    "CIG-010",
    "CIG-011",
    "CIG-012",
    "CIG-013",
    "CIG-014",
    "CIG-015",
    "CIG-016",
    "CIG-017",
    "CIG-018",
    "CIG-019",
    "CIG-020",
]
WAVE_B = ["CIG-030", "CIG-031"]
CLOSEOUT = "CIG-040"


def _load_tasks():
    if str(IPFS_ACCELERATE_ROOT) not in sys.path:
        sys.path.insert(0, str(IPFS_ACCELERATE_ROOT))
    from ipfs_accelerate_py.agent_supervisor.todo_daemon.implementation_daemon import (
        parse_task_file,
    )

    return parse_task_file(TODO_PATH, TASK_PREFIX)


def test_cig_board_and_plan_exist():
    assert TODO_PATH.is_file()
    assert PLAN_PATH.is_file()
    assert "CIG-" in TODO_PATH.read_text(encoding="utf-8")


def test_cig_board_is_daemon_parseable():
    tasks = _load_tasks()
    task_ids = {task.task_id for task in tasks}

    assert "CIG-000" in task_ids
    for task_id in WAVE_A + WAVE_B + [CLOSEOUT]:
        assert task_id in task_ids, f"missing {task_id}"
    assert len(tasks) >= 1 + len(WAVE_A) + len(WAVE_B) + 1
    assert all(task.priority in {"P0", "P1", "P2", "P3"} for task in tasks)
    assert all(task.track for task in tasks)
    assert all(task.acceptance for task in tasks)


def test_cig_dependencies_are_declared_tasks():
    tasks = _load_tasks()
    task_ids = {task.task_id for task in tasks}

    for task in tasks:
        missing = [dependency for dependency in task.depends_on if dependency not in task_ids]
        assert not missing, f"{task.task_id} has missing dependencies: {missing}"


def test_cig_wave_a_depends_only_on_bootstrap():
    tasks = {task.task_id: task for task in _load_tasks()}
    for task_id in WAVE_A:
        assert tasks[task_id].depends_on == ["CIG-000"], task_id
        assert str(tasks[task_id].status).lower() == "todo"


def test_cig_closeout_depends_on_all_work_items():
    tasks = {task.task_id: task for task in _load_tasks()}
    closeout = tasks[CLOSEOUT]
    for task_id in WAVE_A + WAVE_B:
        assert task_id in closeout.depends_on


def test_cig_claimable_wave_a_has_no_predicted_file_overlap():
    tasks = {
        task.task_id: task
        for task in _load_tasks()
        if task.task_id in WAVE_A and str(task.status).lower() == "todo"
    }
    owners: dict[str, list[str]] = {}
    for task_id, task in tasks.items():
        meta = task.metadata or {}
        raw = meta.get("predicted files") or meta.get("predicted_files") or ""
        paths = [part.strip() for part in raw.split(",") if part.strip()]
        # Makefile is intentionally shared for ignore-line removal; allow it
        # only if every owner lists Makefile (serial merge on that path is ok
        # as long as primary suite files do not overlap).
        for path in paths:
            if path == "Makefile":
                continue
            owners.setdefault(path, []).append(task_id)
    overlaps = {path: ids for path, ids in owners.items() if len(ids) > 1}
    assert not overlaps, f"Wave A predicted_files overlap: {overlaps}"


def test_cig_wave_a_declares_parallel_lanes():
    tasks = {task.task_id: task for task in _load_tasks()}
    lanes = set()
    for task_id in WAVE_A:
        meta = tasks[task_id].metadata or {}
        lane = meta.get("parallel lane") or meta.get("parallel_lane")
        assert lane, f"{task_id} missing parallel lane"
        lanes.add(lane)
    # Prefer unique lanes for true parallel claim
    assert len(lanes) == len(WAVE_A)


def test_supervisor_wrapper_lists_claimable_wave_a():
    script = SCRIPTS_DIR / "monorepo_ci_reenables_todo_supervisor.py"
    assert script.is_file()
    result = subprocess.run(
        [sys.executable, str(script), "--once"],
        cwd=REPO_ROOT,
        text=True,
        capture_output=True,
        check=False,
        env={
            **dict(**{k: v for k, v in __import__("os").environ.items()}),
            "PYTHONPATH": str(IPFS_ACCELERATE_ROOT),
        },
    )
    assert result.returncode == 0, result.stderr
    payload = json.loads(result.stdout)
    claimable = set(payload["claimable_task_ids"])
    for task_id in WAVE_A + WAVE_B:
        assert task_id in claimable
    assert CLOSEOUT not in claimable  # blocked until waves complete
    assert payload["claimable_count"] >= len(WAVE_A)
    # No non-Makefile predicted_file overlaps among claimable tasks
    assert payload["predicted_file_overlap"] == [] or all(
        item["path"] == "Makefile" for item in payload["predicted_file_overlap"]
    )
