#!/usr/bin/env python3
"""Run the accelerator task supervisor for Meta glasses display-widget work."""

from __future__ import annotations

import logging

from lift_ipfs_accelerate_bootstrap import bootstrap_ipfs_accelerate


_PREIMPORT_BOOTSTRAP = bootstrap_ipfs_accelerate(__file__, include_script_dir=True)
SCRIPT_REPO_ROOT = _PREIMPORT_BOOTSTRAP.script_repo_root
IPFS_ACCELERATE_ROOT = _PREIMPORT_BOOTSTRAP.package_root

from ipfs_accelerate_py.agent_supervisor.implementation_supervisor_runner import (  # noqa: E402
    build_configured_supervisor_runtime_exports,
    build_namespace_codebase_refill_defaults_factory,
    build_namespace_objective_refill_defaults_factory,
    build_script_supervisor_bootstrap_runner,
)
from ipfs_accelerate_py.agent_supervisor.wrapper_utils import (  # noqa: E402
    build_prefixed_default_llm_merge_resolver_command_callback as _prefixed_llm_merge_callback,
    build_repo_script_bootstrap as _build_repo_script_bootstrap,
    data_namespace_scan_skip_prefixes as _data_namespace_scan_skip_prefixes,
    prefixed_codebase_scan_env_settings as _prefixed_codebase_scan_env_settings,
    prefixed_interoperability_focus as _prefixed_interoperability_focus,
    prefixed_objective_refill_env_settings as _prefixed_objective_refill_env_settings,
    repo_script_path as _repo_script_path,
)
from meta_glasses_display_todo_daemon import (  # noqa: E402
    DEFAULT_TODO_PATH,
    DISCOVERY_DIR,
    DISCOVERY_OUTPUT_PATH,
    META_DISPLAY_WORKTREE_SUBMODULE_PATHS,
    META_GLASSES_DISPLAY_CONTEXT,
    META_GLASSES_DISPLAY_DATA_PATHS,
    META_GLASSES_DISPLAY_ENV_PREFIX,
    META_GLASSES_DISPLAY_WORKTREE_SUBMODULE_PATHS,
    OBJECTIVE_HEAP_PATH,
    TASK_BOARD_PATH_KEY,
    TASK_BOARD_PATH_OPTION,
    ensure_meta_glasses_display_bootstrap_paths,
)


_SCRIPT_BOOTSTRAP = _build_repo_script_bootstrap(__file__, include_script_dir=True)
SCRIPT_REPO_ROOT = _SCRIPT_BOOTSTRAP.script_repo_root
IPFS_ACCELERATE_ROOT = _SCRIPT_BOOTSTRAP.package_root
REPO_ROOT = _SCRIPT_BOOTSTRAP.repo_root

TODO_PATH = DEFAULT_TODO_PATH
DEFAULT_STATE_DIR = META_GLASSES_DISPLAY_DATA_PATHS.state_dir
STATE_DIR = DEFAULT_STATE_DIR
DEFAULT_WORKTREE_ROOT = META_GLASSES_DISPLAY_DATA_PATHS.worktree_root
WORKTREE_ROOT = DEFAULT_WORKTREE_ROOT
OBJECTIVE_GRAPH_PATH = META_GLASSES_DISPLAY_DATA_PATHS.objective_graph_path
OBJECTIVE_BUNDLE_DIR = META_GLASSES_DISPLAY_DATA_PATHS.objective_bundle_dir
OBJECTIVE_DATASET_DIR = META_GLASSES_DISPLAY_DATA_PATHS.objective_dataset_dir
OBJECTIVE_TODO_VECTOR_INDEX_PATH = META_GLASSES_DISPLAY_DATA_PATHS.objective_todo_vector_index_path
OBJECTIVE_REFILL_SETTINGS = _prefixed_objective_refill_env_settings(
    META_GLASSES_DISPLAY_ENV_PREFIX
)
CODEBASE_SCAN_SETTINGS = _prefixed_codebase_scan_env_settings(
    META_GLASSES_DISPLAY_ENV_PREFIX,
    min_open_tasks=8,
    max_findings=3,
)
OBJECTIVE_SCAN_MIN_OPEN_TASKS = OBJECTIVE_REFILL_SETTINGS.min_open_tasks
OBJECTIVE_SCAN_MAX_FINDINGS = OBJECTIVE_REFILL_SETTINGS.max_findings
OBJECTIVE_SCAN_COOLDOWN_SECONDS = OBJECTIVE_REFILL_SETTINGS.cooldown_seconds
OBJECTIVE_SURPLUS_FINDINGS_PER_GOAL = OBJECTIVE_REFILL_SETTINGS.surplus_findings_per_goal
OBJECTIVE_SURPLUS_MIN_TERMS_PER_TODO = OBJECTIVE_REFILL_SETTINGS.surplus_min_terms_per_todo
CODEBASE_SCAN_SKIP_PREFIXES = _data_namespace_scan_skip_prefixes(
    {
        "meta_glasses_display_widgets": (
            "discovery",
            "objective_bundles",
            "objective_datasets",
            "state",
            "worktrees",
        ),
        "hallucinate_multimodal_control": ("discovery", "state", "worktrees"),
        "virtual_ai_os": (
            "discovery",
            "objective_bundles",
            "objective_datasets",
            "state",
            "worktrees",
        ),
    },
    include_scripts=True,
    extra_prefixes=(
        "archive/",
        "backup/",
        "cleanup-archive/",
        "external/ipfs_accelerate/test/duckdb_api/",
        "external/ipfs_accelerate/test/generators/",
        "external/ipfs_accelerate/test/huggingface_transformers/",
        "external/ipfs_accelerate/test/skills/",
        "external/ipfs_kit/archive/",
        "external/ipfs_kit/backup/",
        "swissknife/cleanup-archive/",
        "swissknife/docs/validation/",
        "hallucinate_app/swissknife/cleanup-archive/",
        "hallucinate_app/swissknife/docs/validation/",
    ),
)
CODEBASE_SCAN_SKIP_PREFIXES = CODEBASE_SCAN_SKIP_PREFIXES + (
    "swissknife/docs/DEVELOPER_GUIDE.md",
    "hallucinate_app/swissknife/docs/DEVELOPER_GUIDE.md",
)

logger = logging.getLogger("meta_glasses_display_todo_supervisor")
DAEMON_SCRIPT_PATH = _repo_script_path(REPO_ROOT, "meta_glasses_display_todo_daemon.py")
_RUNTIME_ENVIRONMENT = META_GLASSES_DISPLAY_CONTEXT.runtime_environment
_enter_runtime_environment = _RUNTIME_ENVIRONMENT.enter
_ensure_runtime_pythonpath = _RUNTIME_ENVIRONMENT.ensure_pythonpath
_default_llm_merge_resolver_command = _prefixed_llm_merge_callback(
    META_GLASSES_DISPLAY_ENV_PREFIX
)
META_GLASSES_DISPLAY_INTEROPERABILITY_FOCUS = _prefixed_interoperability_focus(
    META_GLASSES_DISPLAY_ENV_PREFIX,
    "swissknife,hallucinate_app,external/meta-wearables-dat-android,external/meta-wearables-dat-ios",
)
META_GLASSES_DISPLAY_INTEROPERABILITY_COMPONENT_PATHS = (
    "mobile",
    "swissknife",
    "hallucinate_app",
    "external/ipfs_accelerate",
    "external/ipfs_datasets",
    "external/ipfs_kit",
    "Mcp-Plus-Plus",
    "external/meta-wearables-dat-android",
    "external/meta-wearables-dat-ios",
)

_meta_glasses_display_objective_defaults = build_namespace_objective_refill_defaults_factory(
    META_GLASSES_DISPLAY_DATA_PATHS,
    objective_path=OBJECTIVE_HEAP_PATH,
    objective_discovery_output_path=DISCOVERY_OUTPUT_PATH,
    objective_interoperability_focus=META_GLASSES_DISPLAY_INTEROPERABILITY_FOCUS,
    objective_interoperability_component_paths=META_GLASSES_DISPLAY_INTEROPERABILITY_COMPONENT_PATHS,
    objective_max_interoperability_goals=12,
    seed_interoperability_goals=True,
    **OBJECTIVE_REFILL_SETTINGS.objective_refill_kwargs(),
)
_meta_glasses_display_codebase_defaults = build_namespace_codebase_refill_defaults_factory(
    META_GLASSES_DISPLAY_DATA_PATHS,
    codebase_scan_discovery_output_path=DISCOVERY_OUTPUT_PATH,
    codebase_scan_skip_prefixes=CODEBASE_SCAN_SKIP_PREFIXES,
    **CODEBASE_SCAN_SETTINGS.codebase_refill_kwargs(),
)
_meta_glasses_display_supervisor_runner = build_script_supervisor_bootstrap_runner(
    repo_root=REPO_ROOT,
    script_path=__file__,
    logger=logger,
    ensure_paths=ensure_meta_glasses_display_bootstrap_paths,
    prepare_environment=_ensure_runtime_pythonpath,
    enter_runtime_environment=_enter_runtime_environment,
    task_prefix="## MGW-",
    state_prefix="meta_glasses_display",
    daemon_script_path=DAEMON_SCRIPT_PATH,
    todo_path_key=TASK_BOARD_PATH_KEY,
    todo_path_flag=TASK_BOARD_PATH_OPTION,
    llm_merge_resolver_command=_default_llm_merge_resolver_command,
    worktree_submodule_paths=META_GLASSES_DISPLAY_WORKTREE_SUBMODULE_PATHS,
    generated_dirty_repair_enabled=True,
    generated_dirty_repair_commit_subject="MGW: reconcile generated supervisor outputs",
    objective_factory=_meta_glasses_display_objective_defaults,
    codebase_factory=_meta_glasses_display_codebase_defaults,
    once_complete_message="Meta glasses display-widget supervisor check complete: %s",
    ensure_running_message="Meta glasses display-widget supervisor ensure complete: %s",
    repair_runtime_message="Repaired stale Meta glasses display-widget supervisor runtime markers: %s",
)
_meta_glasses_display_supervisor_runtime = _meta_glasses_display_supervisor_runner.runtime
_meta_glasses_display_supervisor_exports = build_configured_supervisor_runtime_exports(
    _meta_glasses_display_supervisor_runtime
)
META_GLASSES_DISPLAY_SUPERVISOR_PROCESS_MARKERS = (
    _meta_glasses_display_supervisor_exports.process_match_any
)
repair_meta_glasses_display_supervisor_runtime = (
    _meta_glasses_display_supervisor_exports.repair_runtime
)
meta_glasses_display_supervisor_is_running = _meta_glasses_display_supervisor_exports.is_running
ensure_meta_glasses_display_supervisor_running = (
    _meta_glasses_display_supervisor_exports.ensure_running
)


def main(argv: list[str] | None = None) -> None:
    _meta_glasses_display_supervisor_runner.run(argv)


if __name__ == "__main__":
    main()
