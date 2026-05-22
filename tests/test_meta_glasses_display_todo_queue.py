from __future__ import annotations

import importlib.util
import subprocess
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
IPFS_DATASETS_ROOT = REPO_ROOT / "external" / "ipfs_datasets"
TODO_PATH = REPO_ROOT / "implementation_plan" / "docs" / "18-swissknife-meta-glasses-display-widgets.todo.md"


def _load_tasks():
    sys.path.insert(0, str(IPFS_DATASETS_ROOT))
    from ipfs_datasets_py.optimizers.todo_daemon.implementation_daemon import parse_task_file

    return parse_task_file(TODO_PATH, "## MGW-")


def test_meta_glasses_display_todo_board_is_daemon_parseable():
    tasks = _load_tasks()
    task_ids = {task.task_id for task in tasks}

    assert "MGW-000" in task_ids
    assert "MGW-012" in task_ids
    assert "MGW-013" in task_ids
    assert "MGW-014" in task_ids
    assert len(tasks) >= 15
    assert all(task.priority in {"P0", "P1", "P2", "P3"} for task in tasks)
    assert all(task.track for task in tasks)


def test_meta_glasses_display_todo_dependencies_are_declared_tasks():
    tasks = _load_tasks()
    task_ids = {task.task_id for task in tasks}

    for task in tasks:
        missing = [dependency for dependency in task.depends_on if dependency not in task_ids]
        assert not missing, f"{task.task_id} has missing dependencies: {missing}"


def test_discovery_expansion_task_waits_for_initial_backlog():
    tasks = {task.task_id: task for task in _load_tasks()}
    discovery = tasks["MGW-013"]

    for index in range(1, 13):
        assert f"MGW-{index:03d}" in discovery.depends_on
    assert "MGW-000" not in discovery.depends_on
    assert "unknowns" in discovery.title.lower()


def test_discovered_supervisor_guardrail_depends_on_discovery_task():
    tasks = {task.task_id: task for task in _load_tasks()}
    guardrail = tasks["MGW-014"]

    assert guardrail.depends_on == ["MGW-013"]
    assert "retry" in guardrail.title.lower()
    assert "JDK 17" in guardrail.acceptance


def test_supervisor_bootstrap_adds_post_initial_discovery_tasks(tmp_path):
    supervisor_path = REPO_ROOT / "scripts" / "meta_glasses_display_todo_supervisor.py"
    spec = importlib.util.spec_from_file_location("meta_glasses_display_todo_supervisor", supervisor_path)
    assert spec is not None
    assert spec.loader is not None
    supervisor_module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(supervisor_module)
    ensure_post_initial_discovery_backlog = supervisor_module.ensure_post_initial_discovery_backlog

    todo_path = tmp_path / "todo.md"
    todo_path.write_text(
        """# Temporary Board

## MGW-001 Initial task

- Status: completed
- Completion: manual
- Priority: P0
- Track: ops
- Depends on:
- Outputs: docs/example.md
- Validation: true
- Acceptance: Example task.
""",
        encoding="utf-8",
    )

    assert ensure_post_initial_discovery_backlog(todo_path)
    updated = todo_path.read_text(encoding="utf-8")

    assert "## MGW-013 Investigate implementation unknowns and expand the backlog" in updated
    assert "Depends on: MGW-001, MGW-002, MGW-003" in updated
    assert "MGW-012" in updated
    assert "## MGW-014 Add supervisor validation-environment and retry-budget guardrails" in updated
    assert "Depends on: MGW-013" in updated
    assert not ensure_post_initial_discovery_backlog(todo_path)


def test_meta_glasses_llm_router_preflight_does_not_call_model():
    completed = subprocess.run(
        [
            sys.executable,
            "scripts/meta_glasses_display_llm_router.py",
            "--task-id",
            "MGW-001",
        ],
        cwd=REPO_ROOT,
        text=True,
        capture_output=True,
        check=False,
    )

    assert completed.returncode == 0, completed.stderr
    assert '"generate": false' in completed.stdout
    assert '"llm_router_importable": true' in completed.stdout
