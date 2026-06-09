#!/usr/bin/env python3
"""Run the accelerator backlog implementation daemon for virtual-AI-OS work."""

from __future__ import annotations

import logging

from lift_ipfs_accelerate_bootstrap import bootstrap_ipfs_accelerate

_PREIMPORT_BOOTSTRAP = bootstrap_ipfs_accelerate(__file__)
SCRIPT_REPO_ROOT = _PREIMPORT_BOOTSTRAP.script_repo_root
IPFS_ACCELERATE_ROOT = _PREIMPORT_BOOTSTRAP.package_root

from ipfs_accelerate_py.agent_supervisor.wrapper_utils import (  # noqa: E402
    build_agent_supervisor_namespace_context as _build_agent_supervisor_namespace_context,
)
from ipfs_accelerate_py.agent_supervisor.wrapper_utils import (
    build_prefixed_default_llm_merge_resolver_command_callback as _prefixed_llm_merge_callback,
)
from ipfs_accelerate_py.agent_supervisor.wrapper_utils import (
    build_repo_script_bootstrap as _build_repo_script_bootstrap,
)
from ipfs_accelerate_py.agent_supervisor.wrapper_utils import (
    repo_doc_path as _repo_doc_path,
)

_SCRIPT_BOOTSTRAP = _build_repo_script_bootstrap(__file__)
SCRIPT_REPO_ROOT = _SCRIPT_BOOTSTRAP.script_repo_root
IPFS_ACCELERATE_ROOT = _SCRIPT_BOOTSTRAP.package_root
REPO_ROOT = _SCRIPT_BOOTSTRAP.repo_root
VIRTUAL_AI_OS_ENV_PREFIX = "HANDSFREE_VAI_OS"
OBJECTIVE_HEAP_PATH = _repo_doc_path(REPO_ROOT, "23-virtual-ai-os-objective-goal-heap.md")
_VIRTUAL_AI_OS_CONTEXT = _build_agent_supervisor_namespace_context(
    REPO_ROOT,
    VIRTUAL_AI_OS_ENV_PREFIX,
    namespace="virtual_ai_os",
    task_board_stem="19-virtual-ai-os-submodule-integration",
    objective_path=OBJECTIVE_HEAP_PATH,
)
VIRTUAL_AI_OS_CONTEXT = _VIRTUAL_AI_OS_CONTEXT
TASK_BOARD_PATH = _VIRTUAL_AI_OS_CONTEXT.task_board_path
TASK_BOARD_PATH_KEY = _VIRTUAL_AI_OS_CONTEXT.task_board_path_key
VIRTUAL_AI_OS_DATA_PATHS = _VIRTUAL_AI_OS_CONTEXT.namespace_paths
TASK_BOARD_PATH_OPTION = _VIRTUAL_AI_OS_CONTEXT.task_board_path_option
STATE_DIR = VIRTUAL_AI_OS_DATA_PATHS.state_dir
WORKTREE_ROOT = VIRTUAL_AI_OS_DATA_PATHS.worktree_root
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

_VIRTUAL_AI_OS_RUNTIME_BOOTSTRAP = _VIRTUAL_AI_OS_CONTEXT.runtime_bootstrap
_VIRTUAL_AI_OS_BOOTSTRAP_PATHS = _VIRTUAL_AI_OS_RUNTIME_BOOTSTRAP.bootstrap_paths
VIRTUAL_AI_OS_BOOTSTRAP_SPECS = _VIRTUAL_AI_OS_BOOTSTRAP_PATHS.specs
_RUNTIME_ENVIRONMENT = _VIRTUAL_AI_OS_RUNTIME_BOOTSTRAP.runtime_environment
_enter_runtime_environment = _RUNTIME_ENVIRONMENT.enter
_ensure_runtime_pythonpath = _RUNTIME_ENVIRONMENT.ensure_pythonpath
virtual_ai_os_bootstrap_paths = _VIRTUAL_AI_OS_BOOTSTRAP_PATHS.resolve
ensure_virtual_ai_os_bootstrap_paths = _VIRTUAL_AI_OS_BOOTSTRAP_PATHS.ensure
_default_llm_merge_resolver_command = _prefixed_llm_merge_callback(VIRTUAL_AI_OS_ENV_PREFIX)
logger = logging.getLogger("virtual_ai_os_todo_daemon")
_virtual_ai_os_daemon_runner = build_namespace_daemon_bootstrap_runner(
    repo_root=REPO_ROOT,
    logger=logger,
    namespace_paths=VIRTUAL_AI_OS_DATA_PATHS,
    ensure_paths=ensure_virtual_ai_os_bootstrap_paths,
    enter_runtime_environment=_enter_runtime_environment,
    task_prefix="## VAI-",
    state_prefix="virtual_ai_os",
    todo_path_key=TASK_BOARD_PATH_KEY,
    todo_path_flag=TASK_BOARD_PATH_OPTION,
    objective_path=OBJECTIVE_HEAP_PATH,
    default_worktree_submodule_paths=VIRTUAL_AI_OS_WORKTREE_SUBMODULE_PATHS,
    default_objective_path=OBJECTIVE_HEAP_PATH,
    llm_merge_resolver_command=_default_llm_merge_resolver_command,
    pass_complete_message="Virtual-AI-OS implementation daemon pass complete: %s",
)


def main(argv: list[str] | None = None) -> None:
    _virtual_ai_os_daemon_runner.run(argv)


if __name__ == "__main__":
    main()
