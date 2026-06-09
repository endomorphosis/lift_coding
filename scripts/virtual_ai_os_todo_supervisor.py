#!/usr/bin/env python3
"""Run the accelerator backlog supervisor for virtual-AI-OS work."""

from __future__ import annotations

import logging

from lift_ipfs_accelerate_bootstrap import bootstrap_ipfs_accelerate

_PREIMPORT_BOOTSTRAP = bootstrap_ipfs_accelerate(__file__, include_script_dir=True)
SCRIPT_REPO_ROOT = _PREIMPORT_BOOTSTRAP.script_repo_root
IPFS_ACCELERATE_ROOT = _PREIMPORT_BOOTSTRAP.package_root

from ipfs_accelerate_py.agent_supervisor.wrapper_utils import (  # noqa: E402
    build_repo_script_bootstrap as _build_repo_script_bootstrap,
)
from ipfs_accelerate_py.agent_supervisor.wrapper_utils import (
    data_namespace_scan_skip_prefixes as _data_namespace_scan_skip_prefixes,
)
from ipfs_accelerate_py.agent_supervisor.wrapper_utils import (
    prefixed_interoperability_focus as _prefixed_interoperability_focus,
)
from ipfs_accelerate_py.agent_supervisor.wrapper_utils import (
    prefixed_objective_refill_env_settings as _prefixed_objective_refill_env_settings,
)
from ipfs_accelerate_py.agent_supervisor.wrapper_utils import (
    repo_script_path as _repo_script_path,
)

_SCRIPT_BOOTSTRAP = _build_repo_script_bootstrap(__file__, include_script_dir=True)
SCRIPT_REPO_ROOT = _SCRIPT_BOOTSTRAP.script_repo_root
IPFS_ACCELERATE_ROOT = _SCRIPT_BOOTSTRAP.package_root
REPO_ROOT = _SCRIPT_BOOTSTRAP.repo_root

from virtual_ai_os_todo_daemon import (  # noqa: E402
    OBJECTIVE_HEAP_PATH,
    VIRTUAL_AI_OS_CONTEXT,
    VIRTUAL_AI_OS_ENV_PREFIX,
    VIRTUAL_AI_OS_WORKTREE_SUBMODULE_PATHS,
)

_VIRTUAL_AI_OS_CONTEXT = VIRTUAL_AI_OS_CONTEXT
DEFAULT_TODO_PATH = _VIRTUAL_AI_OS_CONTEXT.task_board_path
VIRTUAL_AI_OS_DATA_PATHS = _VIRTUAL_AI_OS_CONTEXT.namespace_paths
TASK_BOARD_PATH_OPTION = _VIRTUAL_AI_OS_CONTEXT.task_board_path_option
DEFAULT_STATE_DIR = VIRTUAL_AI_OS_DATA_PATHS.state_dir
DEFAULT_WORKTREE_ROOT = VIRTUAL_AI_OS_DATA_PATHS.worktree_root
DAEMON_SCRIPT_PATH = _repo_script_path(REPO_ROOT, "virtual_ai_os_todo_daemon.py")
DISCOVERY_DIR = VIRTUAL_AI_OS_DATA_PATHS.discovery_dir
OBJECTIVE_GRAPH_PATH = VIRTUAL_AI_OS_DATA_PATHS.objective_graph_path
OBJECTIVE_BUNDLE_DIR = VIRTUAL_AI_OS_DATA_PATHS.objective_bundle_dir
OBJECTIVE_DATASET_DIR = VIRTUAL_AI_OS_DATA_PATHS.objective_dataset_dir
# scanner-resolved: HAO-235 - This module-level vector-index alias is runtime
# wiring; the shared objective defaults factory below passes the same namespace path.
OBJECTIVE_TODO_VECTOR_INDEX_PATH = VIRTUAL_AI_OS_DATA_PATHS.objective_todo_vector_index_path
DISCOVERY_OUTPUT_PATH = VIRTUAL_AI_OS_DATA_PATHS.discovery_output_path()
OBJECTIVE_REFILL_SETTINGS = _prefixed_objective_refill_env_settings(VIRTUAL_AI_OS_ENV_PREFIX)
OBJECTIVE_SCAN_MIN_OPEN_TASKS = OBJECTIVE_REFILL_SETTINGS.min_open_tasks
OBJECTIVE_SCAN_MAX_FINDINGS = OBJECTIVE_REFILL_SETTINGS.max_findings
OBJECTIVE_SCAN_COOLDOWN_SECONDS = OBJECTIVE_REFILL_SETTINGS.cooldown_seconds
OBJECTIVE_SURPLUS_FINDINGS_PER_GOAL = OBJECTIVE_REFILL_SETTINGS.surplus_findings_per_goal
OBJECTIVE_SURPLUS_MIN_TERMS_PER_TODO = OBJECTIVE_REFILL_SETTINGS.surplus_min_terms_per_todo
# scanner-resolved: VAI-168, HAO-235 - "scripts/" in CODEBASE_SCAN_SKIP_PREFIXES
# is intentionally excluded because these supervisor wrappers reference task-board
# paths and daemon script names as runtime wiring.
CODEBASE_SCAN_SKIP_PREFIXES = _data_namespace_scan_skip_prefixes(
    {
        "virtual_ai_os": (
            "discovery",
            "objective_bundles",
            "objective_datasets",
            "state",
            "worktrees",
        ),
        "hallucinate_multimodal_control": ("discovery", "state", "worktrees"),
        "meta_glasses_display_widgets": ("discovery", "state", "worktrees"),
    },
    include_scripts=True,
)

from ipfs_accelerate_py.agent_supervisor.implementation_supervisor_runner import (  # noqa: E402
    build_configured_supervisor_runtime_exports,
    build_namespace_codebase_refill_defaults_factory,
    build_namespace_objective_refill_defaults_factory,
    build_script_supervisor_bootstrap_runner,
)
from ipfs_accelerate_py.agent_supervisor.wrapper_utils import (  # noqa: E402
    build_prefixed_default_llm_merge_resolver_command_callback as _prefixed_llm_merge_callback,
)

VIRTUAL_AI_OS_INTEROPERABILITY_FOCUS = _prefixed_interoperability_focus(
    VIRTUAL_AI_OS_ENV_PREFIX,
    "hallucinate_app",
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
logger = logging.getLogger("virtual_ai_os_todo_supervisor")

_virtual_ai_os_objective_defaults = build_namespace_objective_refill_defaults_factory(
    VIRTUAL_AI_OS_DATA_PATHS,
    objective_path=OBJECTIVE_HEAP_PATH,
    objective_discovery_output_path=DISCOVERY_OUTPUT_PATH,
    objective_interoperability_focus=VIRTUAL_AI_OS_INTEROPERABILITY_FOCUS,
    seed_interoperability_goals=True,
    **OBJECTIVE_REFILL_SETTINGS.objective_refill_kwargs(),
)


_virtual_ai_os_codebase_defaults = build_namespace_codebase_refill_defaults_factory(
    VIRTUAL_AI_OS_DATA_PATHS,
    codebase_scan_discovery_output_path=DISCOVERY_OUTPUT_PATH,
    codebase_scan_min_open_tasks=0,
    codebase_scan_skip_prefixes=CODEBASE_SCAN_SKIP_PREFIXES,
)
_virtual_ai_os_supervisor_runner = build_script_supervisor_bootstrap_runner(
    repo_root=REPO_ROOT,
    script_path=__file__,
    logger=logger,
    ensure_paths=ensure_virtual_ai_os_bootstrap_paths,
    prepare_environment=_ensure_runtime_pythonpath,
    enter_runtime_environment=_enter_runtime_environment,
    task_prefix="## VAI-",
    state_prefix="virtual_ai_os",
    daemon_script_path=DAEMON_SCRIPT_PATH,
    llm_merge_resolver_command=_default_llm_merge_resolver_command,
    worktree_submodule_paths=VIRTUAL_AI_OS_WORKTREE_SUBMODULE_PATHS,
    generated_dirty_repair_enabled=True,
    generated_dirty_repair_commit_subject="VAI: reconcile generated supervisor outputs",
    objective_factory=_virtual_ai_os_objective_defaults,
    codebase_factory=_virtual_ai_os_codebase_defaults,
    once_complete_message="Virtual-AI-OS implementation supervisor check complete: %s",
    ensure_running_message="Virtual-AI-OS implementation supervisor ensure complete: %s",
    repair_runtime_message="Repaired stale virtual-AI-OS supervisor runtime markers: %s",
)
_virtual_ai_os_supervisor_runtime = _virtual_ai_os_supervisor_runner.runtime
_virtual_ai_os_supervisor_exports = build_configured_supervisor_runtime_exports(
    _virtual_ai_os_supervisor_runtime
)
VIRTUAL_AI_OS_SUPERVISOR_PROCESS_MARKERS = _virtual_ai_os_supervisor_exports.process_match_any
repair_virtual_ai_os_supervisor_runtime = _virtual_ai_os_supervisor_exports.repair_runtime
virtual_ai_os_supervisor_is_running = _virtual_ai_os_supervisor_exports.is_running
ensure_virtual_ai_os_supervisor_running = _virtual_ai_os_supervisor_exports.ensure_running


def main(argv: list[str] | None = None) -> None:
    _virtual_ai_os_supervisor_runner.run(argv)


if __name__ == "__main__":
    main()
