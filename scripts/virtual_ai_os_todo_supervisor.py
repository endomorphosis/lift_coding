#!/usr/bin/env python3
"""Run the ipfs_datasets_py todo supervisor for virtual-AI-OS work."""

from __future__ import annotations

import os
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
IPFS_DATASETS_ROOT = REPO_ROOT / "external" / "ipfs_datasets"
DEFAULT_TODO_PATH = REPO_ROOT / "implementation_plan" / "docs" / "19-virtual-ai-os-submodule-integration.todo.md"
DEFAULT_STATE_DIR = REPO_ROOT / "data" / "virtual_ai_os" / "state"
DEFAULT_WORKTREE_ROOT = REPO_ROOT / "data" / "virtual_ai_os" / "worktrees"


def virtual_ai_os_bootstrap_paths() -> dict[str, Path]:
    """Return the repo-local bootstrap contract for virtual-AI-OS supervision."""

    todo_path = Path(os.environ.get("HANDSFREE_VAI_OS_TODO_PATH", str(DEFAULT_TODO_PATH)))
    state_dir = Path(os.environ.get("HANDSFREE_VAI_OS_STATE_DIR", str(DEFAULT_STATE_DIR)))
    worktree_root = Path(
        os.environ.get("HANDSFREE_VAI_OS_WORKTREE_ROOT", str(DEFAULT_WORKTREE_ROOT))
    )
    return {
        "repo_root": REPO_ROOT,
        "todo_path": todo_path,
        "state_dir": state_dir,
        "worktree_root": worktree_root,
    }


def ensure_virtual_ai_os_bootstrap_paths(paths: dict[str, Path] | None = None) -> dict[str, Path]:
    """Create the local state and worktree directories used by the supervisor."""

    resolved = paths or virtual_ai_os_bootstrap_paths()
    resolved["state_dir"].mkdir(parents=True, exist_ok=True)
    resolved["worktree_root"].mkdir(parents=True, exist_ok=True)
    return resolved


def _with_default(argv: list[str], flag: str, value: str) -> list[str]:
    if flag in argv:
        return argv
    return [flag, value, *argv]


def main(argv: list[str] | None = None) -> None:
    args = list(sys.argv[1:] if argv is None else argv)
    paths = ensure_virtual_ai_os_bootstrap_paths()
    os.chdir(REPO_ROOT)
    sys.path.insert(0, str(IPFS_DATASETS_ROOT))
    existing = os.environ.get("PYTHONPATH", "")
    os.environ["PYTHONPATH"] = os.pathsep.join(
        [str(IPFS_DATASETS_ROOT), existing] if existing else [str(IPFS_DATASETS_ROOT)]
    )

    from ipfs_datasets_py.optimizers.todo_daemon.implementation_supervisor import main as supervisor_main

    args = _with_default(args, "--todo-path", str(paths["todo_path"]))
    args = _with_default(args, "--state-dir", str(paths["state_dir"]))
    args = _with_default(args, "--task-prefix", "## VAI-")
    args = _with_default(args, "--state-prefix", "virtual_ai_os")
    args = _with_default(args, "--worktree-root", str(paths["worktree_root"]))
    supervisor_main(args)


if __name__ == "__main__":
    main()