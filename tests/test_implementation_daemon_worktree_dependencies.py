from __future__ import annotations

import sys
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


def test_launch_js_node_modules_are_ephemeral_commit_paths():
    module = _daemon_module()

    for relative in (
        "mobile/node_modules",
        "swissknife/node_modules",
        "hallucinate_app/node_modules",
    ):
        assert relative in module.SHARED_WORKTREE_PATHS
        assert relative in module.EPHEMERAL_WORKTREE_PATHS
