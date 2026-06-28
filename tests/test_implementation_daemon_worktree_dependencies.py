from __future__ import annotations

import subprocess
import sys
import time
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
IPFS_ACCELERATE_ROOT = REPO_ROOT / "external" / "ipfs_accelerate"


def _daemon_module():
    sys.path.insert(0, str(IPFS_ACCELERATE_ROOT))
    from ipfs_accelerate_py.agent_supervisor.todo_daemon import implementation_daemon

    return implementation_daemon


def test_launch_js_node_modules_are_linked_into_validation_worktrees(tmp_path):
    module = _daemon_module()
    shared_paths = {
        "mobile/node_modules",
        "swissknife/node_modules",
        "hallucinate_app/node_modules",
    }

    repo_root = tmp_path / "repo"
    worktree_path = tmp_path / "worktree"
    repo_root.mkdir()
    worktree_path.mkdir()
    for relative in shared_paths:
        source = repo_root / relative
        source.mkdir(parents=True)
        (source / ".installed").write_text("ready\n", encoding="utf-8")

    stale_target = worktree_path / "mobile" / "node_modules"
    stale_target.mkdir(parents=True)
    (stale_target / "stale").write_text("remove me\n", encoding="utf-8")

    daemon = module.PortalImplementationDaemon(
        todo_path=tmp_path / "todo.md",
        state_path=tmp_path / "state.json",
        strategy_path=tmp_path / "strategy.json",
        events_path=tmp_path / "events.jsonl",
        repo_root=repo_root,
    )

    daemon._link_shared_worktree_paths(worktree_path)

    for relative in shared_paths:
        target = worktree_path / relative
        assert target.is_symlink()
        assert target.resolve() == (repo_root / relative).resolve()
        assert (target / ".installed").read_text(encoding="utf-8") == "ready\n"


def test_self_looping_shared_node_modules_path_is_skipped(tmp_path):
    module = _daemon_module()

    repo_root = tmp_path / "repo"
    worktree_path = tmp_path / "worktree"
    repo_root.mkdir()
    worktree_path.mkdir()

    loop = repo_root / "mobile" / "node_modules"
    loop.parent.mkdir(parents=True)
    loop.symlink_to(loop, target_is_directory=True)

    valid_source = repo_root / "swissknife" / "node_modules"
    valid_source.mkdir(parents=True)
    (valid_source / ".installed").write_text("ready\n", encoding="utf-8")

    daemon = module.PortalImplementationDaemon(
        todo_path=tmp_path / "todo.md",
        state_path=tmp_path / "state.json",
        strategy_path=tmp_path / "strategy.json",
        events_path=tmp_path / "events.jsonl",
        repo_root=repo_root,
    )

    daemon._link_shared_worktree_paths(worktree_path)

    assert not (worktree_path / "mobile" / "node_modules").exists()
    linked = worktree_path / "swissknife" / "node_modules"
    assert linked.is_symlink()
    assert linked.resolve() == valid_source.resolve()


def test_launch_js_node_modules_are_ephemeral_commit_paths():
    module = _daemon_module()

    for relative in (
        "mobile/node_modules",
        "swissknife/node_modules",
        "hallucinate_app/node_modules",
    ):
        assert relative in module.SHARED_WORKTREE_PATHS
        assert relative in module.EPHEMERAL_WORKTREE_PATHS


def test_submodule_worktree_add_retries_invalid_gitlink_ref(tmp_path, monkeypatch):
    module = _daemon_module()

    repo_root = tmp_path / "repo"
    source = repo_root / "external" / "ipfs_accelerate" / "ipfs_datasets_py"
    worktree_path = tmp_path / "worktree"
    source.mkdir(parents=True)
    worktree_path.mkdir()

    subprocess.run(["git", "init"], cwd=source, check=True, capture_output=True)
    subprocess.run(["git", "config", "user.email", "test@example.com"], cwd=source, check=True)
    subprocess.run(["git", "config", "user.name", "Test User"], cwd=source, check=True)
    (source / "README.md").write_text("source\n", encoding="utf-8")
    subprocess.run(["git", "add", "README.md"], cwd=source, check=True)
    subprocess.run(["git", "commit", "-m", "source"], cwd=source, check=True, capture_output=True)

    daemon = module.PortalImplementationDaemon(
        todo_path=tmp_path / "todo.md",
        state_path=tmp_path / "state.json",
        strategy_path=tmp_path / "strategy.json",
        events_path=tmp_path / "events.jsonl",
        repo_root=repo_root,
    )
    bad_ref = "65d07e486d423b1349b6d26d865db46af3075179"
    calls = []
    events = []

    monkeypatch.setattr(daemon, "_submodule_gitlink_ref", lambda _worktree, _relative: bad_ref)
    monkeypatch.setattr(
        daemon,
        "_git_ref_exists_in_repo",
        lambda _cwd, ref: ref == bad_ref,
    )
    monkeypatch.setattr(daemon, "_record_event", lambda event, payload: events.append((event, payload)))

    def fake_run_git(command, *, cwd):
        calls.append((tuple(command), Path(cwd)))
        if tuple(command[-1:]) == (bad_ref,):
            raise RuntimeError(f"git worktree add failed: fatal: invalid reference: {bad_ref}")
        return type("Result", (), {"stdout": ""})()

    monkeypatch.setattr(daemon, "_run_git", fake_run_git)

    created = daemon._create_local_submodule_worktree(
        worktree_path,
        "ipfs_datasets_py",
        branch_name="implementation/mgw-368-attempt-26",
        source_relative="external/ipfs_accelerate/ipfs_datasets_py",
    )

    assert created is True
    assert calls[0][0][-1] == bad_ref
    assert calls[1][0][-1] != bad_ref
    assert events[0][0] == "submodule_worktree_base_ref_retried"
    assert events[0][1]["bad_ref"] == bad_ref


def test_missing_validation_worktree_is_recorded_without_implementation_exception(tmp_path, monkeypatch):
    module = _daemon_module()

    repo_root = tmp_path / "repo"
    worktree_root = tmp_path / "worktrees"
    repo_root.mkdir()
    events = []

    daemon = module.PortalImplementationDaemon(
        todo_path=tmp_path / "todo.md",
        state_path=tmp_path / "state.json",
        strategy_path=tmp_path / "strategy.json",
        events_path=tmp_path / "events.jsonl",
        repo_root=repo_root,
        worktree_root=worktree_root,
    )
    monkeypatch.setattr(daemon, "_record_event", lambda event, payload: events.append((event, payload)))
    monkeypatch.setattr(
        daemon,
        "_build_implementation_command",
        lambda _worktree: [
            sys.executable,
            "-c",
            "import os, shutil; shutil.rmtree(os.getcwd())",
        ],
    )

    def create_seeded_worktree(worktree_path, _branch_name, *, task):
        worktree_path.mkdir(parents=True)
        return "baseline"

    monkeypatch.setattr(daemon, "_create_seeded_worktree", create_seeded_worktree)
    monkeypatch.setattr(daemon, "_git_ref_exists", lambda _branch_name: False)
    monkeypatch.setattr(daemon, "_worktree_path_registered_in_repo", lambda _cwd, _worktree: False)
    monkeypatch.setattr(time, "time", lambda: 1782661704)

    task = module.PortalTask(
        task_id="MGW-547",
        title="Close objective gap",
        status="todo",
        completion="manual",
        priority="P0",
        track="launch",
        validation=["true"],
    )
    state = module.PortalTaskState()

    result = daemon._run_implementation_in_ephemeral_worktree(
        task=task,
        state=state,
        attempt=8,
        started_at=module.utc_now(),
        log_path=tmp_path / "implementation.log",
        prompt="implement",
    )

    assert result["returncode"] == 1
    assert result["validation_result"]["reason"] == "validation_workspace_missing"
    assert result["cleanup_result"]["cleaned"] is True
    assert "failed_preservation_result" not in result or not result["failed_preservation_result"]
    assert any(event == "validation_workspace_missing" for event, _payload in events)
    assert not any(event == "implementation_exception" for event, _payload in events)
