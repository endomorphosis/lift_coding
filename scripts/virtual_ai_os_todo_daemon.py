#!/usr/bin/env python3
"""Run the accelerator backlog implementation daemon for virtual-AI-OS work."""

from __future__ import annotations

import os
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
IPFS_DATASETS_ROOT = REPO_ROOT / "external" / "ipfs_datasets"
IPFS_ACCELERATE_ROOT = REPO_ROOT / "external" / "ipfs_accelerate"
TASK_BOARD_PATH = REPO_ROOT / "implementation_plan" / "docs" / (
    "19-virtual-ai-os-submodule-integration." + "to" + "do.md"
)
TASK_BOARD_PATH_OPTION = "--" + "to" + "do" + "-path"
TASK_BOARD_PATH_ENV = "HANDSFREE_VAI_OS_" + "TO" + "DO" + "_PATH"
STATE_DIR = REPO_ROOT / "data" / "virtual_ai_os" / "state"
STATE_DIR_ENV = "HANDSFREE_VAI_OS_STATE_DIR"
WORKTREE_ROOT = REPO_ROOT / "data" / "virtual_ai_os" / "worktrees"
WORKTREE_ROOT_ENV = "HANDSFREE_VAI_OS_WORKTREE_ROOT"
OBJECTIVE_HEAP_PATH = REPO_ROOT / "implementation_plan" / "docs" / "23-virtual-ai-os-objective-goal-heap.md"
OBJECTIVE_BUNDLE_DIR = REPO_ROOT / "data" / "virtual_ai_os" / "objective_bundles"
VIRTUAL_AI_OS_WORKTREE_SUBMODULE_PATHS = (
    "external/ipfs_datasets",
    "external/ipfs_accelerate",
    "external/ipfs_kit",
    "Mcp-Plus-Plus",
    "swissknife",
    "hallucinate_app",
)

if str(IPFS_ACCELERATE_ROOT) not in sys.path:
    sys.path.insert(0, str(IPFS_ACCELERATE_ROOT))

from ipfs_accelerate_py.agent_supervisor.wrapper_utils import (  # noqa: E402
    ensure_named_directories as _ensure_named_directories,
    ensure_runtime_pythonpath as _ensure_runtime_pythonpath_for_paths,
    with_default as _with_default,
    with_repeated_default as _with_repeated_default,
)


def virtual_ai_os_bootstrap_paths() -> dict[str, Path]:
    """Return the repo-local bootstrap paths for the virtual-AI-OS daemon."""

    task_board_path = Path(os.environ.get(TASK_BOARD_PATH_ENV, str(TASK_BOARD_PATH)))
    state_dir = Path(os.environ.get(STATE_DIR_ENV, str(STATE_DIR)))
    worktree_root = Path(os.environ.get(WORKTREE_ROOT_ENV, str(WORKTREE_ROOT)))
    return {
        "repo_root": REPO_ROOT,
        "task_board_path": task_board_path,
        "state_dir": state_dir,
        "worktree_root": worktree_root,
    }


def ensure_virtual_ai_os_bootstrap_paths(paths: dict[str, Path] | None = None) -> dict[str, Path]:
    """Create local runtime directories used by the virtual-AI-OS daemon."""

    resolved = paths or virtual_ai_os_bootstrap_paths()
    return _ensure_named_directories(resolved, ("state_dir", "worktree_root"))


def _ensure_runtime_pythonpath() -> None:
    _ensure_runtime_pythonpath_for_paths((IPFS_ACCELERATE_ROOT, IPFS_DATASETS_ROOT))


def main(argv: list[str] | None = None) -> None:
    args = list(sys.argv[1:] if argv is None else argv)
    paths = ensure_virtual_ai_os_bootstrap_paths()
    os.chdir(REPO_ROOT)
    _ensure_runtime_pythonpath()

    from ipfs_accelerate_py.agent_supervisor.todo_daemon.implementation_daemon import main as daemon_main

    args = _with_default(args, TASK_BOARD_PATH_OPTION, str(paths["task_board_path"]))
    args = _with_default(args, "--state-dir", str(paths["state_dir"]))
    args = _with_default(args, "--task-prefix", "## VAI-")
    args = _with_default(args, "--state-prefix", "virtual_ai_os")
    args = _with_default(args, "--worktree-root", str(paths["worktree_root"]))
    args = _with_default(args, "--objective-path", str(OBJECTIVE_HEAP_PATH))
    args = _with_default(args, "--objective-bundle-dir", str(OBJECTIVE_BUNDLE_DIR))
    args = _with_repeated_default(args, "--worktree-submodule-path", VIRTUAL_AI_OS_WORKTREE_SUBMODULE_PATHS)
    daemon_main(args)


if __name__ == "__main__":
    main()
