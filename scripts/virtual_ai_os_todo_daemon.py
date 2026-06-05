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
    build_agent_supervisor_runtime_bootstrap_callbacks as _build_agent_supervisor_runtime_bootstrap_callbacks,
    repo_doc_path as _repo_doc_path,
    repo_task_board_path as _repo_task_board_path,
    task_board_path_option as _task_board_path_option,
)

TASK_BOARD_PATH = _repo_task_board_path(REPO_ROOT, "19-virtual-ai-os-submodule-integration")
VIRTUAL_AI_OS_ENV_PREFIX = "HANDSFREE_VAI_OS"
VIRTUAL_AI_OS_DATA_PATHS = _agent_supervisor_namespace_paths(REPO_ROOT, "virtual_ai_os")
TASK_BOARD_PATH_OPTION = _task_board_path_option()
STATE_DIR = VIRTUAL_AI_OS_DATA_PATHS.state_dir
WORKTREE_ROOT = VIRTUAL_AI_OS_DATA_PATHS.worktree_root
OBJECTIVE_HEAP_PATH = _repo_doc_path(REPO_ROOT, "23-virtual-ai-os-objective-goal-heap.md")
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
    build_namespace_daemon_bootstrap_runner,
)

_VIRTUAL_AI_OS_RUNTIME_BOOTSTRAP = _build_agent_supervisor_runtime_bootstrap_callbacks(
    REPO_ROOT,
    VIRTUAL_AI_OS_ENV_PREFIX,
    TASK_BOARD_PATH,
    VIRTUAL_AI_OS_DATA_PATHS,
    todo_key="task_board_path",
    todo_setting="todo_path",
)
_VIRTUAL_AI_OS_BOOTSTRAP_PATHS = _VIRTUAL_AI_OS_RUNTIME_BOOTSTRAP.bootstrap_paths
VIRTUAL_AI_OS_BOOTSTRAP_SPECS = _VIRTUAL_AI_OS_BOOTSTRAP_PATHS.specs
_RUNTIME_ENVIRONMENT = _VIRTUAL_AI_OS_RUNTIME_BOOTSTRAP.runtime_environment
_enter_runtime_environment = _RUNTIME_ENVIRONMENT.enter
_ensure_runtime_pythonpath = _RUNTIME_ENVIRONMENT.ensure_pythonpath
virtual_ai_os_bootstrap_paths = _VIRTUAL_AI_OS_BOOTSTRAP_PATHS.resolve
ensure_virtual_ai_os_bootstrap_paths = _VIRTUAL_AI_OS_BOOTSTRAP_PATHS.ensure
logger = logging.getLogger("virtual_ai_os_todo_daemon")
_virtual_ai_os_daemon_runner = build_namespace_daemon_bootstrap_runner(
    repo_root=REPO_ROOT,
    logger=logger,
    namespace_paths=VIRTUAL_AI_OS_DATA_PATHS,
    ensure_paths=ensure_virtual_ai_os_bootstrap_paths,
    enter_runtime_environment=_enter_runtime_environment,
    task_prefix="## VAI-",
    state_prefix="virtual_ai_os",
    todo_path_key="task_board_path",
    todo_path_flag=TASK_BOARD_PATH_OPTION,
    objective_path=OBJECTIVE_HEAP_PATH,
    default_worktree_submodule_paths=VIRTUAL_AI_OS_WORKTREE_SUBMODULE_PATHS,
    default_objective_path=OBJECTIVE_HEAP_PATH,
    pass_complete_message="Virtual-AI-OS implementation daemon pass complete: %s",
)


def main(argv: list[str] | None = None) -> None:
    _virtual_ai_os_daemon_runner.run(argv)


if __name__ == "__main__":
    main()
