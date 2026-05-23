from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
from datetime import datetime, timezone
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


def _git(cwd: Path, *args: str) -> str:
    result = subprocess.run(
        ["git", *args],
        cwd=cwd,
        text=True,
        capture_output=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr or result.stdout
    return result.stdout.strip()


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
    discovery = tasks["HAO-025"]

    for index in range(4, 25):
        assert f"HAO-{index:03d}" in discovery.depends_on
    assert "HAO-000" not in discovery.depends_on
    assert "HAO-001" not in discovery.depends_on
    assert "unknowns" in discovery.title.lower()


def test_hallucinate_autopilot_defaults_to_implement():
    autopilot = _load_script_module("hallucinate_multimodal_control_autopilot")

    assert autopilot.with_autopilot_defaults([]) == ["--implement"]
    assert autopilot.with_autopilot_defaults(["--once"]) == ["--implement", "--once"]
    assert autopilot.with_autopilot_defaults(["--no-implement", "--once"]) == ["--no-implement", "--once"]


def test_implementation_daemon_branch_changed_paths_use_merge_base(tmp_path):
    sys.path.insert(0, str(IPFS_DATASETS_ROOT))
    from ipfs_datasets_py.optimizers.todo_daemon.implementation_daemon import PortalImplementationDaemon

    repo = tmp_path / "repo"
    repo.mkdir()
    _git(repo, "init")
    _git(repo, "checkout", "-b", "main")
    _git(repo, "config", "user.name", "Test User")
    _git(repo, "config", "user.email", "test@example.invalid")
    (repo / "base.txt").write_text("base\n", encoding="utf-8")
    _git(repo, "add", "base.txt")
    _git(repo, "commit", "-m", "base")

    _git(repo, "checkout", "-b", "implementation/task")
    (repo / "feature.txt").write_text("feature\n", encoding="utf-8")
    _git(repo, "add", "feature.txt")
    _git(repo, "commit", "-m", "feature")

    _git(repo, "checkout", "main")
    (repo / "main-only.txt").write_text("main\n", encoding="utf-8")
    _git(repo, "add", "main-only.txt")
    _git(repo, "commit", "-m", "main only")

    daemon = PortalImplementationDaemon(
        todo_path=repo / "todo.md",
        state_path=repo / "state.json",
        strategy_path=repo / "strategy.json",
        events_path=repo / "events.jsonl",
        repo_root=repo,
        task_header_prefix="## HAO-",
    )

    assert daemon._branch_changed_paths("implementation/task") == {"feature.txt"}


def test_implementation_daemon_commits_declared_nested_submodule_outputs(tmp_path):
    sys.path.insert(0, str(IPFS_DATASETS_ROOT))
    from ipfs_datasets_py.optimizers.todo_daemon.implementation_daemon import PortalImplementationDaemon, PortalTask

    repo = tmp_path / "repo"
    parent = repo / "hallucinate_app"
    nested = parent / "swissknife"
    nested.mkdir(parents=True)
    _git(nested, "init")
    _git(nested, "checkout", "-b", "main")
    _git(nested, "config", "user.name", "Test User")
    _git(nested, "config", "user.email", "test@example.invalid")
    (nested / "README.md").write_text("nested\n", encoding="utf-8")
    _git(nested, "add", "README.md")
    _git(nested, "commit", "-m", "base")

    (parent / ".gitmodules").write_text(
        """[submodule "swissknife"]
\tpath = swissknife
\turl = ../swissknife.git
""",
        encoding="utf-8",
    )
    contracts = nested / "contracts"
    contracts.mkdir()
    (contracts / "interaction_envelope.schema.json").write_text('{"type":"object"}\n', encoding="utf-8")

    daemon = PortalImplementationDaemon(
        todo_path=repo / "todo.md",
        state_path=repo / "state.json",
        strategy_path=repo / "strategy.json",
        events_path=repo / "events.jsonl",
        repo_root=repo,
        task_header_prefix="## HAO-",
    )
    task = PortalTask(
        task_id="HAO-999",
        title="Commit nested outputs",
        status="todo",
        completion="manual",
        priority="P1",
        track="runtime",
    )

    results = daemon._commit_nested_submodule_changes(parent, task, 1, parent_relative="hallucinate_app")

    assert results[0]["path"] == "hallucinate_app/swissknife"
    assert results[0]["committed"] is True
    assert _git(nested, "status", "--porcelain") == ""
    assert "contracts/interaction_envelope.schema.json" in _git(nested, "show", "--name-only", "--format=", "HEAD")


def test_hallucinate_supervisor_repairs_stale_runtime_markers(tmp_path):
    supervisor = _load_script_module("hallucinate_multimodal_control_todo_supervisor")
    state_dir = tmp_path / "state"
    state_dir.mkdir()
    stale_pid = 99999999
    prefix = "hallucinate_multimodal_control"
    managed_pid = state_dir / f"{prefix}_managed_daemon.pid"
    wrapper_pid = state_dir / f"{prefix}_supervisor_wrapper.pid"
    status_path = state_dir / f"{prefix}_supervisor_status.json"
    lock_path = state_dir / "implementation.lock"
    managed_pid.write_text(f"{stale_pid}\n", encoding="utf-8")
    wrapper_pid.write_text(f"{stale_pid}\n", encoding="utf-8")
    lock_path.write_text(json.dumps({"kind": "implementation", "pid": stale_pid}), encoding="utf-8")
    status_path.write_text(
        json.dumps(
            {
                "status": "running",
                "supervisor_pid": stale_pid,
                "daemon_pid": stale_pid,
            }
        ),
        encoding="utf-8",
    )

    repairs = supervisor.repair_hallucinate_supervisor_runtime(state_dir, prefix)

    assert str(managed_pid) in repairs["removed"]
    assert str(wrapper_pid) in repairs["removed"]
    assert str(lock_path) in repairs["removed"]
    assert not managed_pid.exists()
    assert not wrapper_pid.exists()
    assert not lock_path.exists()
    status = json.loads(status_path.read_text(encoding="utf-8"))
    assert status["status"] == "stale"
    assert status["repair_reason"] == "supervisor_pid_not_running"
    assert not supervisor.hallucinate_supervisor_is_running(state_dir, prefix)


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
    events_path.write_text("\n".join(json.dumps(event) for event in events) + "\n", encoding="utf-8")

    findings = daemon_module.record_retry_budget_findings(
        todo_path=todo_path,
        events_path=events_path,
        strategy_path=strategy_path,
        discovery_dir=discovery_dir,
        retry_budget=3,
    )

    expected_discovery = discovery_dir / f"{datetime.now(timezone.utc).date().isoformat()}-hao-014-hao-003-retry-budget.md"
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


def test_merge_retry_budget_finding_blocks_repeated_merge_failure(tmp_path):
    daemon_module = _load_script_module("hallucinate_multimodal_control_todo_daemon")
    todo_path = tmp_path / "todo.md"
    events_path = tmp_path / "events.jsonl"
    strategy_path = tmp_path / "strategy.json"
    discovery_dir = tmp_path / "discovery"
    todo_path.write_text(
        """# Temporary Board

## HAO-004 Discover logic APIs

- Status: completed
- Completion: manual
- Priority: P0
- Track: logic
- Depends on:
- Outputs: data/hallucinate_multimodal_control/discovery
- Validation: true
- Acceptance: Discovery is complete.

## HAO-005 Define the formal multimodal control policy IR

- Status: todo
- Completion: manual
- Priority: P0
- Track: logic
- Depends on: HAO-004
- Outputs: hallucinate_app/python/hallucinate_app/control_surface_logic_ir.py
- Validation: python3 hallucinate_app/python/hallucinate_app/test/test_control_surface_logic_ir.py
- Acceptance: Formal IR is defined.
""",
        encoding="utf-8",
    )
    merge_result = {
        "attempted": True,
        "merged": False,
        "returncode": 2,
        "branch": "implementation/hao-005-attempt-2-1779566133",
        "target_branch": "main",
        "command": ["git", "merge", "--no-ff", "--no-edit", "implementation/hao-005-attempt-2-1779566133"],
        "reason": "main_checkout_dirty_conflict",
        "dirty_paths": ["swissknife"],
        "main_worktree_path": "/repo",
    }
    events = [
        {
            "type": "implementation_finished",
            "timestamp": "2026-05-23T00:01:00+00:00",
            "task_id": "HAO-005",
            "attempt": 2,
            "returncode": 2,
            "implementation_commit": "abc123",
            "merge_result": merge_result,
            "validation_result": {"attempted": True, "passed": True, "returncode": 0},
        },
        {
            "type": "merge_reconciled",
            "timestamp": "2026-05-23T00:02:00+00:00",
            "task_id": "HAO-005",
            "attempt": 2,
            "resolved": False,
            "reason": "merge_retried",
            "merge_result": merge_result,
        },
        {
            "type": "merge_reconciled",
            "timestamp": "2026-05-23T00:03:00+00:00",
            "task_id": "HAO-005",
            "attempt": 2,
            "resolved": False,
            "reason": "merge_retried",
            "merge_result": merge_result,
        },
    ]
    events_path.write_text("\n".join(json.dumps(event) for event in events) + "\n", encoding="utf-8")

    findings = daemon_module.record_retry_budget_findings(
        todo_path=todo_path,
        events_path=events_path,
        strategy_path=strategy_path,
        discovery_dir=discovery_dir,
        retry_budget=3,
    )

    expected_discovery = (
        discovery_dir
        / f"{datetime.now(timezone.utc).date().isoformat()}-hao-006-hao-005-merge-retry-budget.md"
    )
    assert findings == [
        {
            "source_task_id": "HAO-005",
            "follow_up_task_id": "HAO-006",
            "failure_count": 3,
            "failed_command": "git merge --no-ff --no-edit implementation/hao-005-attempt-2-1779566133",
            "discovery_path": str(expected_discovery),
            "failure_kind": "merge",
        }
    ]

    updated = todo_path.read_text(encoding="utf-8")
    assert "## HAO-006 Resolve merge retry-budget failure for HAO-005" in updated
    assert "Depends on: HAO-004" in updated

    sys.path.insert(0, str(IPFS_DATASETS_ROOT))
    from ipfs_datasets_py.optimizers.todo_daemon.implementation_daemon import parse_task_file

    tasks = {task.task_id: task for task in parse_task_file(todo_path, "## HAO-")}
    assert tasks["HAO-006"].depends_on == ["HAO-004"]
    assert len(tasks["HAO-006"].validation) == 1
    assert "blocked_tasks" in tasks["HAO-006"].validation[0]

    strategy = json.loads(strategy_path.read_text(encoding="utf-8"))
    assert "HAO-005" in strategy["blocked_tasks"]
    discovery = expected_discovery.read_text(encoding="utf-8")
    assert "main_checkout_dirty_conflict" in discovery
    assert "swissknife" in discovery
