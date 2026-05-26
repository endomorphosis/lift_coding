#!/usr/bin/env python3
"""Run the accelerator backlog implementation daemon for virtual-AI-OS work."""

from __future__ import annotations

import os
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
IPFS_DATASETS_ROOT = REPO_ROOT / "external" / "ipfs_datasets"
IPFS_ACCELERATE_ROOT = REPO_ROOT / "external" / "ipfs_accelerate"
TODO_PATH = REPO_ROOT / "implementation_plan" / "docs" / "19-virtual-ai-os-submodule-integration.todo.md"
STATE_DIR = REPO_ROOT / "data" / "virtual_ai_os" / "state"
WORKTREE_ROOT = REPO_ROOT / "data" / "virtual_ai_os" / "worktrees"
VIRTUAL_AI_OS_WORKTREE_SUBMODULE_PATHS = (
    "external/ipfs_datasets",
    "external/ipfs_accelerate",
    "external/ipfs_kit",
    "Mcp-Plus-Plus",
    "swissknife",
    "hallucinate_app",
)


def _with_default(argv: list[str], flag: str, value: str) -> list[str]:
    if flag in argv:
        return argv
    return [flag, value, *argv]


def _with_repeated_default(argv: list[str], flag: str, values: tuple[str, ...]) -> list[str]:
    if flag in argv:
        return argv
    defaults: list[str] = []
    for value in values:
        defaults.extend([flag, value])
    return [*defaults, *argv]


def _ensure_runtime_pythonpath() -> None:
    for path in (IPFS_ACCELERATE_ROOT, IPFS_DATASETS_ROOT):
        if str(path) not in sys.path:
            sys.path.insert(0, str(path))
    existing = os.environ.get("PYTHONPATH", "")
    paths = [str(IPFS_ACCELERATE_ROOT), str(IPFS_DATASETS_ROOT)]
    os.environ["PYTHONPATH"] = os.pathsep.join([*paths, existing] if existing else paths)


def main(argv: list[str] | None = None) -> None:
    args = list(sys.argv[1:] if argv is None else argv)
    os.chdir(REPO_ROOT)
    _ensure_runtime_pythonpath()

    from ipfs_accelerate_py.agent_supervisor.todo_daemon.implementation_daemon import main as daemon_main

    args = _with_default(args, "--todo-path", str(TODO_PATH))
    args = _with_default(args, "--state-dir", str(STATE_DIR))
    args = _with_default(args, "--task-prefix", "## VAI-")
    args = _with_default(args, "--state-prefix", "virtual_ai_os")
    args = _with_default(args, "--worktree-root", str(WORKTREE_ROOT))
    args = _with_repeated_default(args, "--worktree-submodule-path", VIRTUAL_AI_OS_WORKTREE_SUBMODULE_PATHS)
    daemon_main(args)


if __name__ == "__main__":
    main()
