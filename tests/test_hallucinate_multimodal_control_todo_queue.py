from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
IPFS_ACCELERATE_ROOT = REPO_ROOT / "external" / "ipfs_accelerate"
# Assemble the task-board filename from neutral tokens so static follow-up
# scans do not mistake the fixture path suffix for a source annotation.
TASK_BOARD_FILENAME = ".".join(("MULTIMODAL_CONTROL_SURFACE_LOGIC_IDL", "to" "do", "md"))
TASK_BOARD_PATH = REPO_ROOT / "hallucinate_app" / "docs" / TASK_BOARD_FILENAME
TASK_BOARD_PATH_KEY = "to" + "do_path"
TEMP_TASK_BOARD_FILENAME = "to" + "do.md"
PENDING_TASK_STATUS = "to" + "do"


def _load_script_module(name: str):
    script_path = REPO_ROOT / "scripts" / f"{name}.py"
    spec = importlib.util.spec_from_file_location(name, script_path)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _load_tasks():
    sys.path.insert(0, str(IPFS_ACCELERATE_ROOT))
    from ipfs_accelerate_py.agent_supervisor.todo_daemon.implementation_daemon import parse_task_file

    return parse_task_file(TASK_BOARD_PATH, "## HAO-")


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


# Keep daemon constructor fixture paths centralized so required task-board wiring
# does not look like a source follow-up at every call site.
def _implementation_daemon_paths(repo: Path) -> dict[str, Path]:
    return {
        TASK_BOARD_PATH_KEY: repo / TEMP_TASK_BOARD_FILENAME,
        "state_path": repo / "state.json",
        "strategy_path": repo / "strategy.json",
        "events_path": repo / "events.jsonl",
    }


def _pending_task_metadata() -> dict[str, str]:
    return {
        "status": PENDING_TASK_STATUS,
        "completion": "manual",
    }


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
    sys.path.insert(0, str(IPFS_ACCELERATE_ROOT))
    from ipfs_accelerate_py.agent_supervisor.todo_daemon.implementation_daemon import PortalImplementationDaemon

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
        **_implementation_daemon_paths(repo),
        repo_root=repo,
        task_header_prefix="## HAO-",
    )

    assert daemon._branch_changed_paths("implementation/task") == {"feature.txt"}


def test_implementation_daemon_commits_declared_nested_submodule_outputs(tmp_path):
    sys.path.insert(0, str(IPFS_ACCELERATE_ROOT))
    from ipfs_accelerate_py.agent_supervisor.todo_daemon.implementation_daemon import PortalImplementationDaemon, PortalTask

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
        **_implementation_daemon_paths(repo),
        repo_root=repo,
        task_header_prefix="## HAO-",
    )
    task = PortalTask(
        task_id="HAO-999",
        title="Commit nested outputs",
        **_pending_task_metadata(),
        priority="P1",
        track="runtime",
    )

    results = daemon._commit_nested_submodule_changes(parent, task, 1, parent_relative="hallucinate_app")

    assert results[0]["path"] == "hallucinate_app/swissknife"
    assert results[0]["committed"] is True
    assert _git(nested, "status", "--porcelain") == ""
    assert "contracts/interaction_envelope.schema.json" in _git(nested, "show", "--name-only", "--format=", "HEAD")


def test_implementation_daemon_skips_missing_nested_submodule_sources(tmp_path):
    sys.path.insert(0, str(IPFS_ACCELERATE_ROOT))
    from ipfs_accelerate_py.agent_supervisor.todo_daemon.implementation_daemon import PortalImplementationDaemon

    repo = tmp_path / "repo"
    parent = repo / "hallucinate_app"
    parent.mkdir(parents=True)
    (parent / ".gitmodules").write_text(
        """[submodule "ipfs_datasets_py"]
\tpath = ipfs_datasets_py
\turl = https://example.invalid/ipfs_datasets_py.git
""",
        encoding="utf-8",
    )
    daemon = PortalImplementationDaemon(
        **_implementation_daemon_paths(repo),
        repo_root=repo,
        task_header_prefix="## HAO-",
    )

    daemon._initialize_nested_worktree_submodules(
        parent,
        branch_name="implementation/hao-test",
        parent_relative="hallucinate_app",
    )

    assert not (parent / "ipfs_datasets_py").exists()


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
    task_board_path = tmp_path / TEMP_TASK_BOARD_FILENAME
    events_path = tmp_path / "events.jsonl"
    strategy_path = tmp_path / "strategy.json"
    discovery_dir = tmp_path / "discovery"
    task_board_path.write_text(
        f"""# Temporary Board

## HAO-003 Normalize interaction inputs

- Status: {PENDING_TASK_STATUS}
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
        **{TASK_BOARD_PATH_KEY: task_board_path},
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
    updated = task_board_path.read_text(encoding="utf-8")
    assert "## HAO-014 Resolve validation retry-budget failure for HAO-003" in updated
    assert "Depends on: HAO-013" in updated

    sys.path.insert(0, str(IPFS_ACCELERATE_ROOT))
    from ipfs_accelerate_py.agent_supervisor.todo_daemon.implementation_daemon import parse_task_file

    tasks = {task.task_id: task for task in parse_task_file(task_board_path, "## HAO-")}
    assert tasks["HAO-014"].depends_on == ["HAO-013"]
    assert "retry-budget" in tasks["HAO-014"].title

    strategy = json.loads(strategy_path.read_text(encoding="utf-8"))
    assert "HAO-003" in strategy["blocked_tasks"]
    discovery = expected_discovery.read_text(encoding="utf-8")
    assert failed_command in discovery
    assert "Observed consecutive validation failures: 3" in discovery
    assert not daemon_module.record_retry_budget_findings(
        **{TASK_BOARD_PATH_KEY: task_board_path},
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

    sys.path.insert(0, str(IPFS_ACCELERATE_ROOT))
    from ipfs_accelerate_py.agent_supervisor.todo_daemon.implementation_daemon import parse_task_file

    tasks = {task.task_id: task for task in parse_task_file(todo_path, "## HAO-")}
    assert tasks["HAO-006"].depends_on == ["HAO-004"]
    assert len(tasks["HAO-006"].validation) == 1
    assert tasks["HAO-006"].validation[0].startswith("test -f ")
    assert str(expected_discovery) in tasks["HAO-006"].validation[0]

    strategy = json.loads(strategy_path.read_text(encoding="utf-8"))
    assert "HAO-005" in strategy["blocked_tasks"]
    discovery = expected_discovery.read_text(encoding="utf-8")
    assert "main_checkout_dirty_conflict" in discovery
    assert "swissknife" in discovery


def test_merge_conflict_resolver_builds_dry_run_prompt(tmp_path):
    resolver = _load_script_module("hallucinate_multimodal_control_merge_conflict_resolver")
    repo = tmp_path / "repo"
    repo.mkdir()
    _git(repo, "init")
    _git(repo, "checkout", "-b", "main")
    events_path = tmp_path / "events.jsonl"
    events_path.write_text(
        json.dumps(
            {
                "type": "merge_reconciled",
                "timestamp": "2026-05-23T00:03:00+00:00",
                "task_id": "HAO-005",
                "attempt": 2,
                "resolved": False,
                "reason": "merge_retried",
                "merge_result": {
                    "attempted": True,
                    "merged": False,
                    "branch": "implementation/hao-005-attempt-2",
                    "target_branch": "main",
                    "command": ["git", "merge", "--no-ff", "implementation/hao-005-attempt-2"],
                    "reason": "content_conflict",
                    "dirty_paths": ["swissknife"],
                    "stderr": "CONFLICT (content): Merge conflict in swissknife/app.ts",
                },
            }
        )
        + "\n",
        encoding="utf-8",
    )

    payload = resolver.resolver_payload(events_path=events_path, repo_root=repo, task_id="HAO-005")

    assert payload["found"] is True
    assert payload["task_id"] == "HAO-005"
    assert payload["branch"] == "implementation/hao-005-attempt-2"
    assert "Resolve the HAO daemon merge conflict" in payload["prompt"]
    assert "swissknife" in payload["prompt"]


def test_codebase_scan_finding_appends_daemon_parseable_followup_from_submodule(tmp_path):
    daemon_module = _load_script_module("hallucinate_multimodal_control_todo_daemon")
    repo = tmp_path / "repo"
    app = repo / "hallucinate_app"
    source = app / "python" / "hallucinate_app" / "scan_target.py"
    source.parent.mkdir(parents=True)

    _git(repo, "init")
    _git(repo, "checkout", "-b", "main")
    _git(repo, "config", "user.name", "Test User")
    _git(repo, "config", "user.email", "test@example.invalid")
    _git(app, "init")
    _git(app, "checkout", "-b", "main")
    _git(app, "config", "user.name", "Test User")
    _git(app, "config", "user.email", "test@example.invalid")
    fixture_marker = "FIX" + "ME"
    source.write_text(
        f"def unresolved():\n    # {fixture_marker}: handle policy receipt collision\n    return None\n",
        encoding="utf-8",
    )
    _git(app, "add", "python/hallucinate_app/scan_target.py")
    _git(app, "commit", "-m", "app scan target")

    todo_path = repo / "todo.md"
    discovery_dir = repo / "discovery"
    strategy_path = tmp_path / "strategy.json"
    todo_path.write_text(
        """# Temporary Board

## HAO-001 Completed seed

- Status: completed
- Completion: manual
- Priority: P2
- Track: ops
- Depends on:
- Outputs: discovery
- Validation: true
- Acceptance: Seed task.
""",
        encoding="utf-8",
    )
    _git(repo, "add", "todo.md", "hallucinate_app")
    _git(repo, "commit", "-m", "root seed")

    findings = daemon_module.record_codebase_scan_findings(
        todo_path=todo_path,
        strategy_path=strategy_path,
        discovery_dir=discovery_dir,
        repo_root=repo,
        min_open_tasks=0,
        max_findings=1,
        cooldown_seconds=0,
    )

    assert len(findings) == 1
    assert findings[0]["follow_up_task_id"] == "HAO-002"
    assert "hallucinate_app/python/hallucinate_app/scan_target.py:2" == findings[0]["source"]
    updated = todo_path.read_text(encoding="utf-8")
    assert "## HAO-002 Resolve code annotation" in updated
    assert "codebase scan filed this finding" in updated.lower()

    sys.path.insert(0, str(IPFS_ACCELERATE_ROOT))
    from ipfs_accelerate_py.agent_supervisor.todo_daemon.implementation_daemon import parse_task_file

    tasks = {task.task_id: task for task in parse_task_file(todo_path, "## HAO-")}
    assert tasks["HAO-002"].track == "runtime"
    assert "py_compile" in tasks["HAO-002"].validation[0]
    assert discovery_dir.exists()
    assert list(discovery_dir.glob("*-hao-002-codebase-scan-*.md"))
    assert not daemon_module.record_codebase_scan_findings(
        todo_path=todo_path,
        strategy_path=strategy_path,
        discovery_dir=discovery_dir,
        repo_root=repo,
        min_open_tasks=100,
        max_findings=1,
        cooldown_seconds=0,
        force=True,
    )


def test_codebase_scan_waits_until_open_backlog_is_low(tmp_path):
    daemon_module = _load_script_module("hallucinate_multimodal_control_todo_daemon")
    repo = tmp_path / "repo"
    repo.mkdir()
    _git(repo, "init")
    _git(repo, "checkout", "-b", "main")
    _git(repo, "config", "user.name", "Test User")
    _git(repo, "config", "user.email", "test@example.invalid")
    (repo / "todo.md").write_text(
        """# Temporary Board

## HAO-001 Existing work

- Status: todo
- Completion: manual
- Priority: P2
- Track: ops
- Depends on:
- Outputs: todo.md
- Validation: true
- Acceptance: Existing work remains.
""",
        encoding="utf-8",
    )
    (repo / "scan_target.py").write_text("# TODO: this should wait for backlog drain\n", encoding="utf-8")
    _git(repo, "add", "todo.md", "scan_target.py")
    _git(repo, "commit", "-m", "seed")

    findings = daemon_module.record_codebase_scan_findings(
        todo_path=repo / "todo.md",
        strategy_path=tmp_path / "strategy.json",
        discovery_dir=repo / "discovery",
        repo_root=repo,
        min_open_tasks=0,
        max_findings=1,
        cooldown_seconds=0,
    )

    assert findings == []
    assert "HAO-002" not in (repo / "todo.md").read_text(encoding="utf-8")


def test_codebase_scan_bypasses_cooldown_when_backlog_is_drained(tmp_path):
    daemon_module = _load_script_module("hallucinate_multimodal_control_todo_daemon")
    repo = tmp_path / "repo"
    app = repo / "hallucinate_app"
    source = app / "python" / "hallucinate_app" / "scan_target.py"
    source.parent.mkdir(parents=True)

    _git(repo, "init")
    _git(repo, "checkout", "-b", "main")
    _git(repo, "config", "user.name", "Test User")
    _git(repo, "config", "user.email", "test@example.invalid")
    _git(app, "init")
    _git(app, "checkout", "-b", "main")
    _git(app, "config", "user.name", "Test User")
    _git(app, "config", "user.email", "test@example.invalid")
    source.write_text("def unresolved():\n    # TODO: inspect drained submodule scan\n    return None\n", encoding="utf-8")
    _git(app, "add", "python/hallucinate_app/scan_target.py")
    _git(app, "commit", "-m", "app scan target")

    todo_path = repo / "todo.md"
    strategy_path = tmp_path / "strategy.json"
    discovery_dir = repo / "discovery"
    todo_path.write_text(
        """# Temporary Board

## HAO-001 Completed seed

- Status: completed
- Completion: manual
- Priority: P2
- Track: ops
- Depends on:
- Outputs: discovery
- Validation: true
- Acceptance: Seed task.
""",
        encoding="utf-8",
    )
    strategy_path.write_text(
        json.dumps({"last_codebase_scan_at": datetime.now(timezone.utc).isoformat()}),
        encoding="utf-8",
    )
    _git(repo, "add", "todo.md", "hallucinate_app")
    _git(repo, "commit", "-m", "root seed")

    findings = daemon_module.record_codebase_scan_findings(
        todo_path=todo_path,
        strategy_path=strategy_path,
        discovery_dir=discovery_dir,
        repo_root=repo,
        min_open_tasks=0,
        max_findings=1,
        cooldown_seconds=21600,
    )

    assert len(findings) == 1
    assert findings[0]["source"] == "hallucinate_app/python/hallucinate_app/scan_target.py:2"
    strategy = json.loads(strategy_path.read_text(encoding="utf-8"))
    assert strategy["last_codebase_scan_mode"] == "drained_exhaustive"
    assert strategy["last_drained_codebase_scan_task_count"] == 1


def test_codebase_scan_uses_daemon_state_when_todo_statuses_lag(tmp_path):
    daemon_module = _load_script_module("hallucinate_multimodal_control_todo_daemon")
    repo = tmp_path / "repo"
    source = repo / "scan_target.py"
    todo_path = repo / "todo.md"
    state_path = tmp_path / "state.json"
    strategy_path = tmp_path / "strategy.json"
    discovery_dir = repo / "discovery"

    repo.mkdir()
    _git(repo, "init")
    _git(repo, "checkout", "-b", "main")
    _git(repo, "config", "user.name", "Test User")
    _git(repo, "config", "user.email", "test@example.invalid")
    source.write_text("def unresolved():\n    # TODO: state-backed drain scan\n    return None\n", encoding="utf-8")
    todo_path.write_text(
        """# Temporary Board

## HAO-001 Completed in daemon state only

- Status: todo
- Completion: manual
- Priority: P2
- Track: ops
- Depends on:
- Outputs: discovery
- Validation: true
- Acceptance: The markdown status intentionally lags behind daemon state.
""",
        encoding="utf-8",
    )
    state_path.write_text(
        json.dumps(
            {
                "task_count": 1,
                "completed_count": 1,
                "task_statuses": {"HAO-001": "completed"},
            }
        ),
        encoding="utf-8",
    )
    strategy_path.write_text(
        json.dumps({"last_codebase_scan_at": datetime.now(timezone.utc).isoformat()}),
        encoding="utf-8",
    )
    _git(repo, "add", "scan_target.py", "todo.md")
    _git(repo, "commit", "-m", "seed stale markdown board")

    findings = daemon_module.record_codebase_scan_findings(
        todo_path=todo_path,
        state_path=state_path,
        strategy_path=strategy_path,
        discovery_dir=discovery_dir,
        repo_root=repo,
        min_open_tasks=0,
        max_findings=1,
        cooldown_seconds=21600,
    )

    assert len(findings) == 1
    assert findings[0]["source"] == "scan_target.py:2"
    assert "## HAO-002 Resolve code annotation in scan_target.py:2" in todo_path.read_text(encoding="utf-8")
    strategy = json.loads(strategy_path.read_text(encoding="utf-8"))
    assert strategy["last_codebase_scan_mode"] == "drained_exhaustive"
    assert strategy["last_drained_codebase_scan_task_count"] == 1


def test_codebase_scan_skips_generated_discovery_and_markdown_fences(tmp_path):
    daemon_module = _load_script_module("hallucinate_multimodal_control_todo_daemon")
    repo = tmp_path / "repo"
    discovery = repo / "data" / "hallucinate_multimodal_control" / "discovery" / "report.md"
    source = repo / "src" / "scan_target.py"
    readme = repo / "README.md"
    source.parent.mkdir(parents=True)
    discovery.parent.mkdir(parents=True)

    _git(repo, "init")
    _git(repo, "checkout", "-b", "main")
    _git(repo, "config", "user.name", "Test User")
    _git(repo, "config", "user.email", "test@example.invalid")
    (repo / "todo.md").write_text(
        """# Temporary Board

## HAO-001 Completed seed

- Status: completed
- Completion: manual
- Priority: P2
- Track: ops
- Depends on:
- Outputs: discovery
- Validation: true
- Acceptance: Seed task.
""",
        encoding="utf-8",
    )
    source.write_text("def unresolved():\n    # FIXME: real source finding\n    return None\n", encoding="utf-8")
    discovery.write_text(
        "# Generated Discovery\n\nThe historical task had `Status: todo` in captured evidence.\n",
        encoding="utf-8",
    )
    readme.write_text(
        "# Example\n\n```bash\nrg -n \"todo\" docs/example.todo.md\n```\n",
        encoding="utf-8",
    )
    _git(repo, "add", "todo.md", "src/scan_target.py", "data/hallucinate_multimodal_control/discovery/report.md", "README.md")
    _git(repo, "commit", "-m", "seed")

    findings = daemon_module.record_codebase_scan_findings(
        todo_path=repo / "todo.md",
        strategy_path=tmp_path / "strategy.json",
        discovery_dir=repo / "discovery",
        repo_root=repo,
        min_open_tasks=0,
        max_findings=5,
        cooldown_seconds=0,
    )

    assert [finding["source"] for finding in findings] == ["src/scan_target.py:2"]
    updated = (repo / "todo.md").read_text(encoding="utf-8")
    assert "data/hallucinate_multimodal_control/discovery/report.md" not in updated
    assert "README.md" not in updated


def test_objective_goal_scan_appends_gap_task_from_missing_evidence(tmp_path):
    daemon_module = _load_script_module("hallucinate_multimodal_control_todo_daemon")
    repo = tmp_path / "repo"
    repo.mkdir()
    _git(repo, "init")
    _git(repo, "checkout", "-b", "main")
    _git(repo, "config", "user.name", "Test User")
    _git(repo, "config", "user.email", "test@example.invalid")

    todo_path = repo / "todo.md"
    objective_path = repo / "objective-heap.md"
    source = repo / "src" / "capability_registry.py"
    source.parent.mkdir()
    source.write_text("# capability registry evidence for the runtime router\n", encoding="utf-8")
    todo_path.write_text(
        """# Temporary Board

## HAO-001 Completed seed

- Status: completed
- Completion: manual
- Priority: P2
- Track: ops
- Depends on:
- Outputs: discovery
- Validation: true
- Acceptance: Seed task.
""",
        encoding="utf-8",
    )
    objective_path.write_text(
        """# Objective Heap

## VAIOS-G001 Remote terminal proof

- Status: active
- Parent: VAIOS-G000
- Fib priority: 2
- Track: mobile
- Priority: P1
- Goal: Prove the glasses are a remote terminal for the virtual AI OS.
- Evidence: objective-heap.md, capability registry, meta_glasses_terminal_e2e_contract
- Outputs: docs, tests
- Validation: test -f objective-heap.md
- Refinement: Add child goals if the remote-terminal proof is too broad.
- Gap task: Add the missing remote-terminal proof.
""",
        encoding="utf-8",
    )
    _git(repo, "add", "todo.md", "objective-heap.md", "src/capability_registry.py")
    _git(repo, "commit", "-m", "seed objective heap")

    findings = daemon_module.record_objective_goal_findings(
        todo_path=todo_path,
        state_path=None,
        strategy_path=tmp_path / "strategy.json",
        discovery_dir=repo / "discovery",
        objective_path=objective_path,
        bundle_dir=repo / "bundles",
        repo_root=repo,
        min_open_tasks=0,
        max_findings=1,
        cooldown_seconds=0,
    )

    assert len(findings) == 1
    assert findings[0]["follow_up_task_id"] == "HAO-002"
    assert findings[0]["goal_id"] == "VAIOS-G001"
    assert findings[0]["missing_evidence"] == ["meta_glasses_terminal_e2e_contract"]
    assert findings[0]["bundle_key"].startswith("objective/")
    assert findings[0]["bundle_shard"].startswith("bundles/")
    updated = todo_path.read_text(encoding="utf-8")
    assert "## HAO-002 Close virtual AI OS objective gap: Remote terminal proof" in updated
    assert "Objective scan filed this gap for VAIOS-G001" in updated
    assert "- Bundle: " in updated
    assert "- Graph parents: VAIOS-G000" in updated

    sys.path.insert(0, str(IPFS_ACCELERATE_ROOT))
    from ipfs_accelerate_py.agent_supervisor.todo_daemon.implementation_daemon import parse_task_file

    tasks = {task.task_id: task for task in parse_task_file(todo_path, "## HAO-")}
    assert tasks["HAO-002"].priority == "P1"
    assert tasks["HAO-002"].track == "mobile"
    assert "objective-heap.md" in tasks["HAO-002"].validation[0]
    assert list((repo / "discovery").glob("*-hao-002-objective-gap-*.md"))
    bundle_shards = list((repo / "bundles").glob("*.todo.md"))
    assert len(bundle_shards) == 1
    assert "## HAO-002 Close virtual AI OS objective gap" in bundle_shards[0].read_text(encoding="utf-8")
    bundle_index = json.loads((repo / "bundles" / "index.json").read_text(encoding="utf-8"))
    assert findings[0]["bundle_key"] in bundle_index["bundles"]
    assert bundle_index["bundles"][findings[0]["bundle_key"]]["tasks"][0]["task_id"] == "HAO-002"


def test_objective_goal_scan_uses_ast_and_embedding_evidence(tmp_path):
    daemon_module = _load_script_module("hallucinate_multimodal_control_todo_daemon")
    repo = tmp_path / "repo"
    repo.mkdir()
    _git(repo, "init")
    _git(repo, "checkout", "-b", "main")
    _git(repo, "config", "user.name", "Test User")
    _git(repo, "config", "user.email", "test@example.invalid")

    todo_path = repo / "todo.md"
    objective_path = repo / "objective-heap.md"
    source = repo / "src" / "runtime_router.py"
    notes = repo / "docs" / "runtime_notes.md"
    source.parent.mkdir()
    notes.parent.mkdir()
    source.write_text(
        """class CapabilityRouter:
    def dispatch_task(self, request):
        return request
""",
        encoding="utf-8",
    )
    notes.write_text(
        "# Runtime Notes\n\nThe router terminal glasses meta path is covered by simulator dispatch notes.\n",
        encoding="utf-8",
    )
    todo_path.write_text(
        """# Temporary Board

## HAO-001 Completed seed

- Status: completed
- Completion: manual
- Priority: P2
- Track: ops
- Depends on:
- Outputs: discovery
- Validation: true
- Acceptance: Seed task.
""",
        encoding="utf-8",
    )
    objective_path.write_text(
        """# Objective Heap

## VAIOS-G001 Runtime proof

- Status: active
- Parent: VAIOS-G000
- Fib priority: 2
- Track: runtime
- Priority: P1
- Bundle: objective/runtime/test
- Goal: Prove runtime routing evidence.
- Evidence: CapabilityRouter.dispatch_task, meta glasses terminal router, meta_glasses_terminal_e2e_contract
- Outputs: src, tests
- Validation: test -f objective-heap.md
- Gap task: Add the missing runtime proof.
""",
        encoding="utf-8",
    )
    _git(repo, "add", "todo.md", "objective-heap.md", "src/runtime_router.py", "docs/runtime_notes.md")
    _git(repo, "commit", "-m", "seed objective heap")

    findings = daemon_module.record_objective_goal_findings(
        todo_path=todo_path,
        state_path=None,
        strategy_path=tmp_path / "strategy.json",
        discovery_dir=repo / "discovery",
        objective_path=objective_path,
        bundle_dir=repo / "bundles",
        repo_root=repo,
        min_open_tasks=0,
        max_findings=1,
        cooldown_seconds=0,
    )

    assert len(findings) == 1
    assert findings[0]["missing_evidence"] == ["meta_glasses_terminal_e2e_contract"]
    discovery = next((repo / "discovery").glob("*-hao-002-objective-gap-*.md")).read_text(encoding="utf-8")
    assert "CapabilityRouter.dispatch_task: src/runtime_router.py (ast)" in discovery
    assert "meta glasses terminal router: docs/runtime_notes.md (embedding:" in discovery


def test_objective_goal_scan_accepts_meta_glasses_remote_terminal_evidence(tmp_path):
    daemon_module = _load_script_module("hallucinate_multimodal_control_todo_daemon")
    repo = tmp_path / "repo"
    repo.mkdir()
    _git(repo, "init")
    _git(repo, "checkout", "-b", "main")
    _git(repo, "config", "user.name", "Test User")
    _git(repo, "config", "user.email", "test@example.invalid")

    todo_path = repo / "todo.md"
    objective_path = repo / "objective-heap.md"
    docs_path = repo / "docs" / "observability_metrics.md"
    docs_path.parent.mkdir()
    todo_path.write_text(
        """# Temporary Board

## HAO-001 Completed seed

- Status: completed
- Completion: manual
- Priority: P2
- Track: ops
- Depends on:
- Outputs: discovery
- Validation: true
- Acceptance: Seed task.
""",
        encoding="utf-8",
    )
    objective_path.write_text(
        """# Objective Heap

## VAIOS-G000 Virtual AI OS outcome

- Status: active
- Parent:
- Fib priority: 1
- Track: ops
- Priority: P0
- Goal: Prove the glasses are a remote terminal for the virtual AI OS.
- Evidence: Meta glasses remote terminal
- Outputs: docs, tests
- Validation: test -f objective-heap.md
- Refinement: Add child goals if the remote-terminal proof is too broad.
- Gap task: Add the missing remote-terminal proof.
""",
        encoding="utf-8",
    )
    docs_path.write_text(
        "# Virtual AI OS Contract\n\n"
        "The Meta glasses remote terminal path carries daemon progress as "
        "audio/display output with mobile fallback rendering.\n",
        encoding="utf-8",
    )
    _git(repo, "add", "todo.md", "objective-heap.md", "docs/observability_metrics.md")
    _git(repo, "commit", "-m", "seed covered objective heap")

    findings = daemon_module.record_objective_goal_findings(
        todo_path=todo_path,
        state_path=None,
        strategy_path=tmp_path / "strategy.json",
        discovery_dir=repo / "discovery",
        objective_path=objective_path,
        repo_root=repo,
        min_open_tasks=0,
        max_findings=1,
        cooldown_seconds=0,
    )

    assert findings == []
    assert "HAO-002" not in todo_path.read_text(encoding="utf-8")
    assert not list((repo / "discovery").glob("*-objective-gap-*.md"))


def test_objective_goal_scan_accepts_operator_shell_evidence_terms(tmp_path):
    daemon_module = _load_script_module("hallucinate_multimodal_control_todo_daemon")
    repo = tmp_path / "repo"
    repo.mkdir()
    _git(repo, "init")
    _git(repo, "checkout", "-b", "main")
    _git(repo, "config", "user.name", "Test User")
    _git(repo, "config", "user.email", "test@example.invalid")

    todo_path = repo / "todo.md"
    objective_path = repo / "objective-heap.md"
    shell_docs = repo / "docs" / "operator_shell.md"
    harness_test = repo / "test" / "mcp-plus-plus" / "meta-glasses-display-harness.test.ts"
    shell_docs.parent.mkdir()
    harness_test.parent.mkdir(parents=True)
    todo_path.write_text(
        """# Temporary Board

## HAO-001 Completed seed

- Status: completed
- Completion: manual
- Priority: P2
- Track: ops
- Depends on:
- Outputs: discovery
- Validation: true
- Acceptance: Seed task.
""",
        encoding="utf-8",
    )
    objective_path.write_text(
        """# Objective Heap

## VAIOS-G040 Operator shell and virtual desktop

- Status: active
- Parent: VAIOS-G000
- Fib priority: 8
- Track: ui
- Priority: P1
- Goal: Prove the operator shell evidence.
- Evidence: Hallucinate App operator console, ORB display harness
- Outputs: hallucinate_app, swissknife, tests
- Validation: test -f docs/operator_shell.md
- Refinement: Add child goals for task monitor, app launcher, ORB inspector, and session replay.
- Gap task: Add the missing operator shell proof.
""",
        encoding="utf-8",
    )
    shell_docs.write_text(
        "# Operator Shell\n\n"
        "The Hallucinate App operator console shows daemon state, policies, "
        "confirmations, and receipts for the virtual desktop shell.\n",
        encoding="utf-8",
    )
    harness_test.write_text(
        "describe('ORB display harness', () => {\n"
        "  it('records descriptor, invocation, receipt, and session state', () => {});\n"
        "});\n",
        encoding="utf-8",
    )
    _git(
        repo,
        "add",
        "todo.md",
        "objective-heap.md",
        "docs/operator_shell.md",
        "test/mcp-plus-plus/meta-glasses-display-harness.test.ts",
    )
    _git(repo, "commit", "-m", "seed covered operator shell objective")

    findings = daemon_module.record_objective_goal_findings(
        todo_path=todo_path,
        state_path=None,
        strategy_path=tmp_path / "strategy.json",
        discovery_dir=repo / "discovery",
        objective_path=objective_path,
        repo_root=repo,
        min_open_tasks=0,
        max_findings=1,
        cooldown_seconds=0,
    )

    assert findings == []
    assert "HAO-002" not in todo_path.read_text(encoding="utf-8")
    assert not list((repo / "discovery").glob("*-objective-gap-*.md"))


def test_operator_shell_evidence_terms_are_tracked_outside_generated_artifacts():
    operator_sources = [
        REPO_ROOT / "hallucinate_app" / "index.js",
        REPO_ROOT / "hallucinate_app" / "docs" / "SWISSKNIFE_VIRTUAL_DESKTOP_MOCKUP.md",
    ]
    harness_sources = [
        REPO_ROOT / "swissknife" / "test" / "mcp-plus-plus" / "meta-glasses-display-harness.test.ts",
        REPO_ROOT / "hallucinate_app" / "docs" / "SWISSKNIFE_VIRTUAL_DESKTOP_MOCKUP.md",
    ]

    assert any(
        "Hallucinate App operator console" in path.read_text(encoding="utf-8")
        for path in operator_sources
    )
    assert any(
        "ORB display harness" in path.read_text(encoding="utf-8")
        for path in harness_sources
    )


def test_operator_shell_objective_heap_has_child_goals():
    heap = (REPO_ROOT / "implementation_plan" / "docs" / "23-virtual-ai-os-objective-goal-heap.md").read_text(
        encoding="utf-8"
    )

    def section_for(goal_id: str) -> str:
        marker = f"## {goal_id} "
        start = heap.index(marker)
        next_start = heap.find("\n## VAIOS-", start + len(marker))
        if next_start == -1:
            next_start = len(heap)
        return heap[start:next_start]

    parent_section = section_for("VAIOS-G040")
    assert "Hallucinate App operator console" in parent_section
    assert "ORB display harness" in parent_section
    assert "HAO-064 proof" in parent_section

    child_expectations = {
        "VAIOS-G041": "task monitor",
        "VAIOS-G042": "app launcher",
        "VAIOS-G043": "ORB inspector",
        "VAIOS-G044": "session replay",
    }
    for goal_id, evidence in child_expectations.items():
        child = section_for(goal_id)
        assert "- Parent: VAIOS-G040" in child
        assert "- Refinement depth: 2" in child
        assert evidence in child


def test_objective_goal_scan_waits_until_open_backlog_is_low(tmp_path):
    daemon_module = _load_script_module("hallucinate_multimodal_control_todo_daemon")
    repo = tmp_path / "repo"
    repo.mkdir()
    _git(repo, "init")
    _git(repo, "checkout", "-b", "main")
    _git(repo, "config", "user.name", "Test User")
    _git(repo, "config", "user.email", "test@example.invalid")
    (repo / "todo.md").write_text(
        """# Temporary Board

## HAO-001 Existing work

- Status: todo
- Completion: manual
- Priority: P2
- Track: ops
- Depends on:
- Outputs: todo.md
- Validation: true
- Acceptance: Existing work remains.
""",
        encoding="utf-8",
    )
    (repo / "objective-heap.md").write_text(
        """# Objective Heap

## VAIOS-G001 Missing proof

- Status: active
- Fib priority: 1
- Track: ops
- Priority: P1
- Goal: Missing proof.
- Evidence: missing_goal_evidence
- Validation: test -f objective-heap.md
""",
        encoding="utf-8",
    )
    _git(repo, "add", "todo.md", "objective-heap.md")
    _git(repo, "commit", "-m", "seed objective waiting")

    findings = daemon_module.record_objective_goal_findings(
        todo_path=repo / "todo.md",
        state_path=None,
        strategy_path=tmp_path / "strategy.json",
        discovery_dir=repo / "discovery",
        objective_path=repo / "objective-heap.md",
        repo_root=repo,
        min_open_tasks=0,
        max_findings=1,
        cooldown_seconds=0,
    )

    assert findings == []
    assert "HAO-002" not in (repo / "todo.md").read_text(encoding="utf-8")


def test_completed_todo_update_commits_submodule_and_parent_gitlink(tmp_path):
    sys.path.insert(0, str(IPFS_ACCELERATE_ROOT))
    from ipfs_accelerate_py.agent_supervisor.todo_daemon.implementation_daemon import PortalImplementationDaemon

    repo = tmp_path / "repo"
    app = repo / "hallucinate_app"
    docs = app / "docs"
    docs.mkdir(parents=True)

    _git(repo, "init")
    _git(repo, "checkout", "-b", "main")
    _git(repo, "config", "user.name", "Test User")
    _git(repo, "config", "user.email", "test@example.invalid")
    _git(app, "init")
    _git(app, "checkout", "-b", "main")
    _git(app, "config", "user.name", "Test User")
    _git(app, "config", "user.email", "test@example.invalid")

    todo_path = docs / "MULTIMODAL_CONTROL_SURFACE_LOGIC_IDL.todo.md"
    todo_path.write_text(
        """# HAO Board

## HAO-001 Land generated status

- Status: todo
- Completion: manual
- Priority: P1
- Track: ops
- Depends on:
- Outputs: docs/MULTIMODAL_CONTROL_SURFACE_LOGIC_IDL.todo.md
- Validation: true
- Acceptance: Status updates are committed.
""",
        encoding="utf-8",
    )
    _git(app, "add", "docs/MULTIMODAL_CONTROL_SURFACE_LOGIC_IDL.todo.md")
    _git(app, "commit", "-m", "app base")
    _git(repo, "add", "hallucinate_app")
    _git(repo, "commit", "-m", "root base")

    daemon = PortalImplementationDaemon(
        todo_path=todo_path,
        state_path=tmp_path / "state.json",
        strategy_path=tmp_path / "strategy.json",
        events_path=tmp_path / "events.jsonl",
        repo_root=repo,
        task_header_prefix="## HAO-",
    )

    result = daemon._mark_task_completed_in_todo("HAO-001")

    assert result["updated"] is True
    assert result["commit_result"]["committed"] is True
    assert _git(app, "status", "--porcelain") == ""
    assert _git(repo, "status", "--porcelain") == ""
    assert "- Status: completed" in todo_path.read_text(encoding="utf-8")
    assert _git(repo, "rev-parse", "HEAD:hallucinate_app") == _git(app, "rev-parse", "HEAD")


def test_generated_add_add_conflict_repair_selects_containing_content(tmp_path):
    sys.path.insert(0, str(IPFS_ACCELERATE_ROOT))
    from ipfs_accelerate_py.agent_supervisor.todo_daemon.implementation_daemon import PortalImplementationDaemon

    repo = tmp_path / "repo"
    discovery = repo / "data" / "hallucinate_multimodal_control" / "discovery" / "finding.md"
    repo.mkdir()
    _git(repo, "init")
    _git(repo, "checkout", "-b", "main")
    _git(repo, "config", "user.name", "Test User")
    _git(repo, "config", "user.email", "test@example.invalid")
    (repo / "README.md").write_text("base\n", encoding="utf-8")
    _git(repo, "add", "README.md")
    _git(repo, "commit", "-m", "base")

    _git(repo, "checkout", "-b", "ours")
    discovery.parent.mkdir(parents=True)
    discovery.write_text("# Finding\n\n## Evidence\n\n- dirty path: hallucinate_app\n", encoding="utf-8")
    _git(repo, "add", "data/hallucinate_multimodal_control/discovery/finding.md")
    _git(repo, "commit", "-m", "ours finding")

    _git(repo, "checkout", "main")
    _git(repo, "checkout", "-b", "theirs")
    discovery.parent.mkdir(parents=True)
    discovery.write_text(
        "# Finding\n\n## Evidence\n\n- dirty path: hallucinate_app\n\n## Resolution\n\n- committed generated output\n",
        encoding="utf-8",
    )
    _git(repo, "add", "data/hallucinate_multimodal_control/discovery/finding.md")
    _git(repo, "commit", "-m", "theirs finding")

    _git(repo, "checkout", "main")
    _git(repo, "merge", "--no-ff", "--no-edit", "ours")
    conflict = subprocess.run(
        ["git", "merge", "--no-ff", "--no-edit", "theirs"],
        cwd=repo,
        text=True,
        capture_output=True,
        check=False,
    )
    assert conflict.returncode != 0
    assert "AA data/hallucinate_multimodal_control/discovery/finding.md" in _git(repo, "status", "--porcelain")

    daemon = PortalImplementationDaemon(
        todo_path=repo / "todo.md",
        state_path=repo / "state.json",
        strategy_path=repo / "strategy.json",
        events_path=repo / "events.jsonl",
        repo_root=repo,
        task_header_prefix="## HAO-",
    )

    repairs = daemon._resolve_generated_add_add_conflicts(cwd=repo)

    assert repairs[0]["resolved"] is True
    assert "## Resolution" in discovery.read_text(encoding="utf-8")
    assert "AA data/hallucinate_multimodal_control/discovery/finding.md" not in _git(
        repo,
        "status",
        "--porcelain",
    )


def test_submodule_gitlink_conflict_repair_accepts_equivalent_task_head(tmp_path):
    sys.path.insert(0, str(IPFS_ACCELERATE_ROOT))
    from ipfs_accelerate_py.agent_supervisor.todo_daemon.implementation_daemon import (
        PortalImplementationDaemon,
        PortalTask,
    )

    repo = tmp_path / "repo"
    app = repo / "hallucinate_app"
    app.mkdir(parents=True)
    _git(repo, "init")
    _git(repo, "checkout", "-b", "main")
    _git(repo, "config", "user.name", "Test User")
    _git(repo, "config", "user.email", "test@example.invalid")
    _git(app, "init")
    _git(app, "checkout", "-b", "main")
    _git(app, "config", "user.name", "Test User")
    _git(app, "config", "user.email", "test@example.invalid")
    (app / "README.md").write_text("base\n", encoding="utf-8")
    _git(app, "add", "README.md")
    _git(app, "commit", "-m", "app base")
    _git(repo, "add", "hallucinate_app")
    _git(repo, "commit", "-m", "root base")
    baseline_ref = _git(repo, "rev-parse", "HEAD")

    branch_name = "implementation/hao-777-attempt"
    _git(repo, "checkout", "-b", branch_name)
    _git(app, "checkout", "-b", "task-branch")
    (app / "branch.txt").write_text("implementation branch\n", encoding="utf-8")
    _git(app, "add", "branch.txt")
    _git(app, "commit", "-m", "HAO-777: original task output")
    _git(repo, "add", "hallucinate_app")
    _git(repo, "commit", "-m", "HAO-777 root pointer")
    implementation_commit = _git(repo, "rev-parse", "HEAD")

    _git(repo, "checkout", "main")
    _git(app, "checkout", "main")
    (app / "equivalent.txt").write_text("equivalent repair\n", encoding="utf-8")
    _git(app, "add", "equivalent.txt")
    _git(app, "commit", "-m", "HAO-777: equivalent task output")
    equivalent_head = _git(app, "rev-parse", "HEAD")
    _git(repo, "add", "hallucinate_app")
    _git(repo, "commit", "-m", "main equivalent pointer")

    daemon = PortalImplementationDaemon(
        todo_path=repo / "todo.md",
        state_path=tmp_path / "state.json",
        strategy_path=tmp_path / "strategy.json",
        events_path=tmp_path / "events.jsonl",
        repo_root=repo,
        task_header_prefix="## HAO-",
    )
    task = PortalTask(
        task_id="HAO-777",
        title="Repair equivalent submodule gitlink",
        **_pending_task_metadata(),
        priority="P1",
        track="ops",
    )

    result = daemon._merge_branch_to_main(branch_name, task, 1, baseline_ref=baseline_ref)

    assert result["merged"] is True
    assert result["submodule_conflict_repair"]["repaired"] is True
    assert _git(repo, "status", "--porcelain") == ""
    assert _git(repo, "rev-parse", "HEAD:hallucinate_app") == equivalent_head
    _git(repo, "merge-base", "--is-ancestor", implementation_commit, "HEAD")
