#!/usr/bin/env python3
"""Run the accelerator backlog daemon for Meta glasses display-widget work."""

from __future__ import annotations

import logging

from lift_ipfs_accelerate_bootstrap import bootstrap_ipfs_accelerate


_PREIMPORT_BOOTSTRAP = bootstrap_ipfs_accelerate(__file__)
SCRIPT_REPO_ROOT = _PREIMPORT_BOOTSTRAP.script_repo_root
IPFS_ACCELERATE_ROOT = _PREIMPORT_BOOTSTRAP.package_root

from ipfs_accelerate_py.agent_supervisor.implementation_daemon_runner import (  # noqa: E402
    build_namespace_daemon_bootstrap_runner,
)
from ipfs_accelerate_py.agent_supervisor.wrapper_utils import (  # noqa: E402
    build_agent_supervisor_namespace_context as _build_agent_supervisor_namespace_context,
    build_prefixed_default_llm_merge_resolver_command_callback as _prefixed_llm_merge_callback,
    build_repo_script_bootstrap as _build_repo_script_bootstrap,
    repo_doc_path as _repo_doc_path,
)


_SCRIPT_BOOTSTRAP = _build_repo_script_bootstrap(__file__)
SCRIPT_REPO_ROOT = _SCRIPT_BOOTSTRAP.script_repo_root
IPFS_ACCELERATE_ROOT = _SCRIPT_BOOTSTRAP.package_root
REPO_ROOT = _SCRIPT_BOOTSTRAP.repo_root

META_GLASSES_DISPLAY_ENV_PREFIX = "HANDSFREE_MGW"
OBJECTIVE_HEAP_PATH = _repo_doc_path(REPO_ROOT, "23-virtual-ai-os-objective-goal-heap.md")
_META_GLASSES_DISPLAY_CONTEXT = _build_agent_supervisor_namespace_context(
    REPO_ROOT,
    META_GLASSES_DISPLAY_ENV_PREFIX,
    namespace="meta_glasses_display_widgets",
    task_board_stem="18-swissknife-meta-glasses-display-widgets",
    objective_path=OBJECTIVE_HEAP_PATH,
)
META_GLASSES_DISPLAY_CONTEXT = _META_GLASSES_DISPLAY_CONTEXT
DEFAULT_TODO_PATH = _META_GLASSES_DISPLAY_CONTEXT.task_board_path
TODO_PATH = DEFAULT_TODO_PATH
TASK_BOARD_PATH = DEFAULT_TODO_PATH
TASK_BOARD_PATH_KEY = _META_GLASSES_DISPLAY_CONTEXT.task_board_path_key
TASK_BOARD_PATH_OPTION = _META_GLASSES_DISPLAY_CONTEXT.task_board_path_option
META_GLASSES_DISPLAY_DATA_PATHS = _META_GLASSES_DISPLAY_CONTEXT.namespace_paths
DEFAULT_STATE_DIR = META_GLASSES_DISPLAY_DATA_PATHS.state_dir
STATE_DIR = DEFAULT_STATE_DIR
DEFAULT_WORKTREE_ROOT = META_GLASSES_DISPLAY_DATA_PATHS.worktree_root
WORKTREE_ROOT = DEFAULT_WORKTREE_ROOT
DISCOVERY_DIR = META_GLASSES_DISPLAY_DATA_PATHS.discovery_dir
OBJECTIVE_GRAPH_PATH = META_GLASSES_DISPLAY_DATA_PATHS.objective_graph_path
OBJECTIVE_BUNDLE_DIR = META_GLASSES_DISPLAY_DATA_PATHS.objective_bundle_dir
OBJECTIVE_DATASET_DIR = META_GLASSES_DISPLAY_DATA_PATHS.objective_dataset_dir
OBJECTIVE_TODO_VECTOR_INDEX_PATH = META_GLASSES_DISPLAY_DATA_PATHS.objective_todo_vector_index_path
DISCOVERY_OUTPUT_PATH = META_GLASSES_DISPLAY_DATA_PATHS.discovery_output_path()
META_GLASSES_DISPLAY_WORKTREE_SUBMODULE_PATHS = (
    "external/ipfs_accelerate",
    "external/ipfs_datasets",
    "external/ipfs_kit",
    "hallucinate_app",
    "swissknife",
)
META_DISPLAY_WORKTREE_SUBMODULE_PATHS = META_GLASSES_DISPLAY_WORKTREE_SUBMODULE_PATHS

_META_GLASSES_DISPLAY_RUNTIME_BOOTSTRAP = _META_GLASSES_DISPLAY_CONTEXT.runtime_bootstrap
_META_GLASSES_DISPLAY_BOOTSTRAP_PATHS = _META_GLASSES_DISPLAY_RUNTIME_BOOTSTRAP.bootstrap_paths
META_GLASSES_DISPLAY_BOOTSTRAP_SPECS = _META_GLASSES_DISPLAY_BOOTSTRAP_PATHS.specs
_RUNTIME_ENVIRONMENT = _META_GLASSES_DISPLAY_RUNTIME_BOOTSTRAP.runtime_environment
_enter_runtime_environment = _RUNTIME_ENVIRONMENT.enter
_ensure_runtime_pythonpath = _RUNTIME_ENVIRONMENT.ensure_pythonpath
meta_glasses_display_bootstrap_paths = _META_GLASSES_DISPLAY_BOOTSTRAP_PATHS.resolve
ensure_meta_glasses_display_bootstrap_paths = _META_GLASSES_DISPLAY_BOOTSTRAP_PATHS.ensure
_default_llm_merge_resolver_command = _prefixed_llm_merge_callback(
    META_GLASSES_DISPLAY_ENV_PREFIX
)

logger = logging.getLogger("meta_glasses_display_todo_daemon")
_meta_glasses_display_daemon_runner = build_namespace_daemon_bootstrap_runner(
    repo_root=REPO_ROOT,
    logger=logger,
    namespace_paths=META_GLASSES_DISPLAY_DATA_PATHS,
    ensure_paths=ensure_meta_glasses_display_bootstrap_paths,
    enter_runtime_environment=_enter_runtime_environment,
    task_prefix="## MGW-",
    state_prefix="meta_glasses_display",
    todo_path_key=TASK_BOARD_PATH_KEY,
    todo_path_flag=TASK_BOARD_PATH_OPTION,
    objective_path=OBJECTIVE_HEAP_PATH,
    default_worktree_submodule_paths=META_GLASSES_DISPLAY_WORKTREE_SUBMODULE_PATHS,
    default_objective_path=OBJECTIVE_HEAP_PATH,
    llm_merge_resolver_command=_default_llm_merge_resolver_command,
    pass_complete_message="Meta glasses display-widget daemon pass complete: %s",
)


def main(argv: list[str] | None = None) -> None:
    _meta_glasses_display_daemon_runner.run(argv)


if __name__ == "__main__":
    main()
