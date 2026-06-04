#!/usr/bin/env python3
"""Run the accelerator backlog implementation daemon for virtual-AI-OS work."""

from __future__ import annotations

import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
IPFS_DATASETS_ROOT = REPO_ROOT / "external" / "ipfs_datasets"
IPFS_ACCELERATE_ROOT = REPO_ROOT / "external" / "ipfs_accelerate"

if str(IPFS_ACCELERATE_ROOT) not in sys.path:
    sys.path.insert(0, str(IPFS_ACCELERATE_ROOT))

from ipfs_accelerate_py.agent_supervisor.wrapper_utils import (  # noqa: E402
    build_prefixed_bootstrap_path_callbacks as _build_prefixed_bootstrap_path_callbacks,
    build_runtime_environment_callbacks as _build_runtime_environment_callbacks,
    task_board_filename as _task_board_filename,
    task_board_path_option as _task_board_path_option,
)

TASK_BOARD_PATH = REPO_ROOT / "implementation_plan" / "docs" / (
    _task_board_filename("19-virtual-ai-os-submodule-integration")
)
VIRTUAL_AI_OS_ENV_PREFIX = "HANDSFREE_VAI_OS"
TASK_BOARD_PATH_OPTION = _task_board_path_option()
STATE_DIR = REPO_ROOT / "data" / "virtual_ai_os" / "state"
WORKTREE_ROOT = REPO_ROOT / "data" / "virtual_ai_os" / "worktrees"
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

from ipfs_accelerate_py.agent_supervisor.implementation_daemon_runner import (  # noqa: E402
    apply_portal_implementation_daemon_defaults_from_paths,
)

_VIRTUAL_AI_OS_BOOTSTRAP_PATHS = _build_prefixed_bootstrap_path_callbacks(
    REPO_ROOT,
    VIRTUAL_AI_OS_ENV_PREFIX,
    (
        ("task_board_path", TASK_BOARD_PATH, "todo_path"),
        ("state_dir", STATE_DIR),
        ("worktree_root", WORKTREE_ROOT),
    ),
    ("state_dir", "worktree_root"),
)
VIRTUAL_AI_OS_BOOTSTRAP_SPECS = _VIRTUAL_AI_OS_BOOTSTRAP_PATHS.specs
_RUNTIME_ENVIRONMENT = _build_runtime_environment_callbacks(
    REPO_ROOT,
    (IPFS_ACCELERATE_ROOT, IPFS_DATASETS_ROOT),
)
_enter_runtime_environment = _RUNTIME_ENVIRONMENT.enter
_ensure_runtime_pythonpath = _RUNTIME_ENVIRONMENT.ensure_pythonpath
virtual_ai_os_bootstrap_paths = _VIRTUAL_AI_OS_BOOTSTRAP_PATHS.resolve
ensure_virtual_ai_os_bootstrap_paths = _VIRTUAL_AI_OS_BOOTSTRAP_PATHS.ensure


def main(argv: list[str] | None = None) -> None:
    args = list(sys.argv[1:] if argv is None else argv)
    paths = ensure_virtual_ai_os_bootstrap_paths()
    _enter_runtime_environment()

    from ipfs_accelerate_py.agent_supervisor.todo_daemon.implementation_daemon import main as daemon_main

    args = apply_portal_implementation_daemon_defaults_from_paths(
        args,
        paths,
        todo_path_key="task_board_path",
        task_prefix="## VAI-",
        state_prefix="virtual_ai_os",
        todo_path_flag=TASK_BOARD_PATH_OPTION,
        objective_path=OBJECTIVE_HEAP_PATH,
        objective_bundle_dir=OBJECTIVE_BUNDLE_DIR,
        worktree_submodule_paths=VIRTUAL_AI_OS_WORKTREE_SUBMODULE_PATHS,
    )
    daemon_main(args)


if __name__ == "__main__":
    main()
