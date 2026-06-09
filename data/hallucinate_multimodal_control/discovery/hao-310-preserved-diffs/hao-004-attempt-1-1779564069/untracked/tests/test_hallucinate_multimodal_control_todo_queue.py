from __future__ import annotations

import importlib.util
import json
import sys
from datetime import UTC, datetime
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
IPFS_DATASETS_ROOT = REPO_ROOT / "external" / "ipfs_datasets"
TODO_PATH = REPO_ROOT / "hallucinate_app" / "docs" / "MULTIMODAL_CONTROL_SURFACE_LOGIC_IDL.todo.md"


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

    return parse_task_file(TODO_PATH, "## HAO-")


def test_hallucinate_multimodal_todo_board_is_daemon_parseable():
    tasks = _load_tasks()
    task_ids = {task.task_id for task in tasks}

    assert "HAO-000" in task_ids
    assert "HAO-013" in task_ids
    assert len(tasks) >= 14
    assert all(task.priority in {"P0", "P1", "P2", "P3"} for task in tasks)
    assert all(task.track for task in tasks)


def test_hallucinate_multimodal_todo_dependencies_are_declared_tasks():
    tasks = _load_tasks()
    task_ids = {task.task_id for task in tasks}

    for task in tasks:
        missing = [dependency for dependency in task.depends_on if dependency not in task_ids]
        assert not missing, f"{task.task_id} has missing dependencies: {missing}"


def test_discovery_expansion_task_waits_for_initial_backlog():
    tasks = {task.task_id: task for task in _load_tasks()}
    discovery = tasks["HAO-013"]

    for index in range(2, 13):
        assert f"HAO-{index:03d}" in discovery.depends_on
    assert "HAO-000" not in discovery.depends_on
    assert "HAO-001" not in discovery.depends_on
    assert "unknowns" in discovery.title.lower()


def test_hallucinate_autopilot_defaults_to_implement():
    autopilot = _load_script_module("hallucinate_multimodal_control_autopilot")

    assert autopilot.with_autopilot_defaults([]) == ["--implement"]
    assert autopilot.with_autopilot_defaults(["--once"]) == ["--implement", "--once"]
    assert autopilot.with_autopilot_defaults(["--no-implement", "--once"]) == [
        "--no-implement",
        "--once",
    ]


def test_retry_budget_finding_appends_daemon_parseable_followup(tmp_path):
    daemon_module = _load_script_module("hallucinate_multimodal_control_todo_daemon")
    todo_path = tmp_path / "todo.md"
    events_path = tmp_path / "events.jsonl"
    strategy_path = tmp_path / "strategy.json"
    discovery_dir = tmp_path / "discovery"
    todo_path.write_text(
        """# Temporary Board

## HAO-003 Normalize interaction inputs

- Status: todo
- Completion: manual
- Priority: P0
- Track: runtime
- Depends on:
- Outputs: hallucinate_app/python/hallucinate_app/control_surface_intents.py
- Validation: pytest tests/test_control_surface_intents.py
- Acceptance: Normalize interaction inputs.

## HAO-013 Investigate implementation unknowns and expand the backlog

- Status: completed
- Completion: manual
- Priority: P2
- Track: ops
- Depends on:
- Outputs: data/hallucinate_multimodal_control/discovery
- Validation: true
- Acceptance: Discovery expansion is available.
""",
        encoding="utf-8",
    )
    failed_command = "pytest tests/test_control_surface_intents.py"
    events = [
        {
            "type": "implementation_finished",
            "timestamp": f"2026-05-23T00:0{index}:00+00:00",
            "task_id": "HAO-003",
            "attempt": index,
            "returncode": 1,
            "log_path": str(tmp_path / f"hao-003-attempt-{index}.log"),
            "validation_result": {
                "attempted": True,
                "passed": False,
                "returncode": 1,
                "failed_command": failed_command,
                "results": [{"command": failed_command, "returncode": 1}],
            },
        }
        for index in range(1, 4)
    ]
    events_path.write_text(
        "\n".join(json.dumps(event) for event in events) + "\n", encoding="utf-8"
    )

    findings = daemon_module.record_retry_budget_findings(
        todo_path=todo_path,
        events_path=events_path,
        strategy_path=strategy_path,
        discovery_dir=discovery_dir,
        retry_budget=3,
    )

    expected_discovery = (
        discovery_dir / f"{datetime.now(UTC).date().isoformat()}-hao-014-hao-003-retry-budget.md"
    )
    assert findings == [
        {
            "source_task_id": "HAO-003",
            "follow_up_task_id": "HAO-014",
            "failure_count": 3,
            "failed_command": failed_command,
            "discovery_path": str(expected_discovery),
        }
    ]
    updated = todo_path.read_text(encoding="utf-8")
    assert "## HAO-014 Resolve validation retry-budget failure for HAO-003" in updated
    assert "Depends on: HAO-013" in updated

    sys.path.insert(0, str(IPFS_DATASETS_ROOT))
    from ipfs_datasets_py.optimizers.todo_daemon.implementation_daemon import parse_task_file

    tasks = {task.task_id: task for task in parse_task_file(todo_path, "## HAO-")}
    assert tasks["HAO-014"].depends_on == ["HAO-013"]
    assert "retry-budget" in tasks["HAO-014"].title

    strategy = json.loads(strategy_path.read_text(encoding="utf-8"))
    assert "HAO-003" in strategy["blocked_tasks"]
    discovery = expected_discovery.read_text(encoding="utf-8")
    assert failed_command in discovery
    assert "Observed consecutive validation failures: 3" in discovery
    assert not daemon_module.record_retry_budget_findings(
        todo_path=todo_path,
        events_path=events_path,
        strategy_path=strategy_path,
        discovery_dir=discovery_dir,
        retry_budget=3,
    )
