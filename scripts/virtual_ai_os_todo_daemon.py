#!/usr/bin/env python3
"""Run the accelerator backlog implementation daemon for virtual-AI-OS work."""

from __future__ import annotations

import logging
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
IPFS_ACCELERATE_ROOT = REPO_ROOT / "external" / "ipfs_accelerate"

if str(IPFS_ACCELERATE_ROOT) not in sys.path:
    sys.path.insert(0, str(IPFS_ACCELERATE_ROOT))

from ipfs_accelerate_py.agent_supervisor.wrapper_utils import (  # noqa: E402
    agent_supervisor_namespace_paths as _agent_supervisor_namespace_paths,
    build_agent_supervisor_bootstrap_path_callbacks as _build_agent_supervisor_bootstrap_path_callbacks,
    build_repo_runtime_environment_callbacks as _build_repo_runtime_environment_callbacks,
    task_board_filename as _task_board_filename,
    task_board_path_option as _task_board_path_option,
)

TASK_BOARD_PATH = REPO_ROOT / "implementation_plan" / "docs" / (
    _task_board_filename("19-virtual-ai-os-submodule-integration")
)
VIRTUAL_AI_OS_ENV_PREFIX = "HANDSFREE_VAI_OS"
VIRTUAL_AI_OS_DATA_PATHS = _agent_supervisor_namespace_paths(REPO_ROOT, "virtual_ai_os")
TASK_BOARD_PATH_OPTION = _task_board_path_option()
STATE_DIR = VIRTUAL_AI_OS_DATA_PATHS.state_dir
WORKTREE_ROOT = VIRTUAL_AI_OS_DATA_PATHS.worktree_root
OBJECTIVE_HEAP_PATH = REPO_ROOT / "implementation_plan" / "docs" / "23-virtual-ai-os-objective-goal-heap.md"
OBJECTIVE_BUNDLE_DIR = VIRTUAL_AI_OS_DATA_PATHS.objective_bundle_dir
VIRTUAL_AI_OS_WORKTREE_SUBMODULE_PATHS = (
    "external/ipfs_datasets",
    "external/ipfs_accelerate",
    "external/ipfs_kit",
    "Mcp-Plus-Plus",
    "swissknife",
    "hallucinate_app",
)

from ipfs_accelerate_py.agent_supervisor.implementation_daemon_runner import (  # noqa: E402
    build_configured_implementation_daemon_runner,
)

_VIRTUAL_AI_OS_BOOTSTRAP_PATHS = _build_agent_supervisor_bootstrap_path_callbacks(
    REPO_ROOT,
    VIRTUAL_AI_OS_ENV_PREFIX,
    TASK_BOARD_PATH,
    VIRTUAL_AI_OS_DATA_PATHS,
    todo_key="task_board_path",
    todo_setting="todo_path",
)
VIRTUAL_AI_OS_BOOTSTRAP_SPECS = _VIRTUAL_AI_OS_BOOTSTRAP_PATHS.specs
_RUNTIME_ENVIRONMENT = _build_repo_runtime_environment_callbacks(REPO_ROOT)
_enter_runtime_environment = _RUNTIME_ENVIRONMENT.enter
_ensure_runtime_pythonpath = _RUNTIME_ENVIRONMENT.ensure_pythonpath
virtual_ai_os_bootstrap_paths = _VIRTUAL_AI_OS_BOOTSTRAP_PATHS.resolve
ensure_virtual_ai_os_bootstrap_paths = _VIRTUAL_AI_OS_BOOTSTRAP_PATHS.ensure
logger = logging.getLogger("virtual_ai_os_todo_daemon")


def main(argv: list[str] | None = None) -> None:
    args = list(sys.argv[1:] if argv is None else argv)

    build_configured_implementation_daemon_runner(
        repo_root=REPO_ROOT,
        logger=logger,
        default_worktree_submodule_paths=VIRTUAL_AI_OS_WORKTREE_SUBMODULE_PATHS,
        default_objective_path=OBJECTIVE_HEAP_PATH,
        default_objective_bundle_dir=OBJECTIVE_BUNDLE_DIR,
        pass_complete_message="Virtual-AI-OS implementation daemon pass complete: %s",
    ).run_configured_from_bootstrap(
        args,
        ensure_paths=ensure_virtual_ai_os_bootstrap_paths,
        enter_runtime_environment=_enter_runtime_environment,
        todo_path_key="task_board_path",
        task_prefix="## VAI-",
        state_prefix="virtual_ai_os",
        todo_path_flag=TASK_BOARD_PATH_OPTION,
        objective_path=OBJECTIVE_HEAP_PATH,
        objective_bundle_dir=OBJECTIVE_BUNDLE_DIR,
        worktree_submodule_paths=VIRTUAL_AI_OS_WORKTREE_SUBMODULE_PATHS,
    )


if __name__ == "__main__":
    main()
