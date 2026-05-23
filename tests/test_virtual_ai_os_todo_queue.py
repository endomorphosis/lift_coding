from __future__ import annotations

import json
import importlib.util
import subprocess
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
IPFS_DATASETS_ROOT = REPO_ROOT / "external" / "ipfs_datasets"
TODO_PATH = REPO_ROOT / "implementation_plan" / "docs" / "19-virtual-ai-os-submodule-integration.todo.md"


def _load_script_module(name: str):
    script_path = REPO_ROOT / "scripts" / f"{name}.py"
    spec = importlib.util.spec_from_file_location(name, script_path)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _load_tasks():
    sys.path.insert(0, str(IPFS_DATASETS_ROOT))
    from ipfs_datasets_py.optimizers.todo_daemon.implementation_daemon import parse_task_file

    return parse_task_file(TODO_PATH, "## VAI-")


def test_virtual_ai_os_todo_board_is_daemon_parseable():
    tasks = _load_tasks()
    task_ids = {task.task_id for task in tasks}

    assert "VAI-000" in task_ids
    assert "VAI-014" in task_ids
    assert len(tasks) >= 12
    assert all(task.priority in {"P0", "P1", "P2", "P3"} for task in tasks)
    assert all(task.track for task in tasks)


def test_virtual_ai_os_todo_dependencies_are_declared_tasks():
    tasks = _load_tasks()
    task_ids = {task.task_id for task in tasks}

    for task in tasks:
        missing = [dependency for dependency in task.depends_on if dependency not in task_ids]
        assert not missing, f"{task.task_id} has missing dependencies: {missing}"


def test_virtual_ai_os_discovery_task_waits_for_initial_backlog():
    tasks = {task.task_id: task for task in _load_tasks()}
    discovery = tasks["VAI-014"]

    for task_id in (
        "VAI-003",
        "VAI-004",
        "VAI-005",
        "VAI-006",
        "VAI-007",
        "VAI-008",
        "VAI-009",
        "VAI-010",
        "VAI-011",
        "VAI-012",
        "VAI-013",
    ):
        assert task_id in discovery.depends_on
    assert "unknowns" in discovery.acceptance.lower()


def test_virtual_ai_os_mcplusplus_source_task_is_explicit():
    tasks = {task.task_id: task for task in _load_tasks()}
    source_task = tasks["VAI-013"]

    assert source_task.depends_on == ["VAI-001"]
    assert "canonical source" in source_task.acceptance.lower()
    assert "repository not found" in source_task.acceptance.lower() or "distributed protocol surface" in source_task.acceptance.lower()


def test_virtual_ai_os_llm_router_preflight_does_not_call_model():
    completed = subprocess.run(
        [
            sys.executable,
            "scripts/virtual_ai_os_llm_router.py",
            "--task-id",
            "VAI-003",
        ],
        cwd=REPO_ROOT,
        text=True,
        capture_output=True,
        check=False,
    )

    assert completed.returncode == 0, completed.stderr
    payload = json.loads(completed.stdout)
    assert payload["task_id"] == "VAI-003"
    assert payload["generate"] is False
    assert payload["llm_router_importable"] is True


def test_virtual_ai_os_supervisor_bootstrap_paths_can_be_overridden(tmp_path, monkeypatch):
    supervisor_module = _load_script_module("virtual_ai_os_todo_supervisor")
    custom_todo = tmp_path / "custom.todo.md"
    custom_state = tmp_path / "custom-state"
    custom_worktrees = tmp_path / "custom-worktrees"

    monkeypatch.setenv("HANDSFREE_VAI_OS_TODO_PATH", str(custom_todo))
    monkeypatch.setenv("HANDSFREE_VAI_OS_STATE_DIR", str(custom_state))
    monkeypatch.setenv("HANDSFREE_VAI_OS_WORKTREE_ROOT", str(custom_worktrees))

    paths = supervisor_module.virtual_ai_os_bootstrap_paths()

    assert paths["todo_path"] == custom_todo
    assert paths["state_dir"] == custom_state
    assert paths["worktree_root"] == custom_worktrees


def test_virtual_ai_os_supervisor_creates_bootstrap_directories(tmp_path):
    supervisor_module = _load_script_module("virtual_ai_os_todo_supervisor")
    paths = {
        "repo_root": tmp_path,
        "todo_path": tmp_path / "board.todo.md",
        "state_dir": tmp_path / "state",
        "worktree_root": tmp_path / "worktrees",
    }

    supervisor_module.ensure_virtual_ai_os_bootstrap_paths(paths)

    assert paths["state_dir"].exists()
    assert paths["worktree_root"].exists()