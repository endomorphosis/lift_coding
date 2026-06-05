#!/usr/bin/env python3
"""Run the generalized accelerator backlog daemon for Hallucinate multimodal-control work."""

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
    data_namespace_scan_skip_prefixes as _data_namespace_scan_skip_prefixes,
    prefixed_codebase_scan_env_settings as _prefixed_codebase_scan_env_settings,
    prefixed_env_path as _prefixed_env_path,
    prefixed_interoperability_focus as _prefixed_interoperability_focus,
    prefixed_objective_refill_env_settings as _prefixed_objective_refill_env_settings,
    repo_doc_path as _repo_doc_path,
    repo_task_board_path as _repo_task_board_path,
    task_board_path_key as _task_board_path_key,
    task_board_path_option as _task_board_path_option,
)

DEFAULT_TODO_PATH = _repo_task_board_path(
    REPO_ROOT,
    "MULTIMODAL_CONTROL_SURFACE_LOGIC_IDL",
    docs_dir="hallucinate_app/docs",
)
HALLUCINATE_ENV_PREFIX = "HANDSFREE_HAO"
HALLUCINATE_DATA_PATHS = _agent_supervisor_namespace_paths(REPO_ROOT, "hallucinate_multimodal_control")
TASK_BOARD_PATH_OPTION = _task_board_path_option()
TASK_BOARD_PATH_KEY = _task_board_path_key()
DEFAULT_OBJECTIVE_GOAL_HEAP_PATH = _prefixed_env_path(
    HALLUCINATE_ENV_PREFIX,
    "OBJECTIVE_GOAL_HEAP_PATH",
    _repo_doc_path(REPO_ROOT, "23-virtual-ai-os-objective-goal-heap.md"),
)
DEFAULT_WORKTREE_ROOT = HALLUCINATE_DATA_PATHS.worktree_root
DISCOVERY_DIR = HALLUCINATE_DATA_PATHS.discovery_dir
OBJECTIVE_BUNDLE_DIR = HALLUCINATE_DATA_PATHS.objective_bundle_dir
OBJECTIVE_DATASET_DIR = HALLUCINATE_DATA_PATHS.objective_dataset_dir
OBJECTIVE_TODO_VECTOR_INDEX_PATH = HALLUCINATE_DATA_PATHS.objective_todo_vector_index_path
DISCOVERY_OUTPUT_PATH = HALLUCINATE_DATA_PATHS.discovery_output_path()
VALIDATION_RETRY_BUDGET = 3
MERGE_RETRY_BUDGET = 3
OBJECTIVE_REFILL_SETTINGS = _prefixed_objective_refill_env_settings(HALLUCINATE_ENV_PREFIX)
OBJECTIVE_SCAN_MIN_OPEN_TASKS = OBJECTIVE_REFILL_SETTINGS.min_open_tasks
OBJECTIVE_SCAN_MAX_FINDINGS = OBJECTIVE_REFILL_SETTINGS.max_findings
OBJECTIVE_SCAN_COOLDOWN_SECONDS = OBJECTIVE_REFILL_SETTINGS.cooldown_seconds
OBJECTIVE_SURPLUS_FINDINGS_PER_GOAL = OBJECTIVE_REFILL_SETTINGS.surplus_findings_per_goal
OBJECTIVE_SURPLUS_MIN_TERMS_PER_TODO = OBJECTIVE_REFILL_SETTINGS.surplus_min_terms_per_todo
CODEBASE_SCAN_SETTINGS = _prefixed_codebase_scan_env_settings(HALLUCINATE_ENV_PREFIX)
CODEBASE_SCAN_MIN_OPEN_TASKS = CODEBASE_SCAN_SETTINGS.min_open_tasks
CODEBASE_SCAN_MAX_FINDINGS = CODEBASE_SCAN_SETTINGS.max_findings
CODEBASE_SCAN_COOLDOWN_SECONDS = CODEBASE_SCAN_SETTINGS.cooldown_seconds
CODEBASE_SCAN_SKIP_PREFIXES = _data_namespace_scan_skip_prefixes(
    {
        "hallucinate_multimodal_control": (
            "discovery",
            "objective_bundles",
            "objective_datasets",
            "state",
            "worktrees",
        ),
        "meta_glasses_display_widgets": ("discovery", "state", "worktrees"),
        "virtual_ai_os": (
            "discovery",
            "objective_bundles",
            "objective_datasets",
            "state",
            "worktrees",
        ),
    },
    include_scripts=True,
)
HALLUCINATE_WORKTREE_SUBMODULE_PATHS = ("hallucinate_app", "ipfs_datasets_py", "swissknife")

if str(IPFS_ACCELERATE_ROOT) not in sys.path:
    sys.path.insert(0, str(IPFS_ACCELERATE_ROOT))

from ipfs_accelerate_py.agent_supervisor.wrapper_utils import (  # noqa: E402
    build_agent_supervisor_bootstrap_path_callbacks as _build_agent_supervisor_bootstrap_path_callbacks,
    build_repo_runtime_environment_callbacks as _build_repo_runtime_environment_callbacks,
)
from ipfs_accelerate_py.agent_supervisor.backlog_refinery import (  # noqa: E402
    build_namespace_codebase_scan_recorder,
    build_namespace_objective_backlog_recorder,
    build_namespace_retry_budget_recorder,
)
from ipfs_accelerate_py.agent_supervisor.implementation_daemon_runner import (  # noqa: E402
    build_daemon_refill_hooks_factory_from_recorders,
    build_namespace_daemon_bootstrap_runner,
    namespace_implementation_state_artifact_paths,
)

HALLUCINATE_INTEROPERABILITY_FOCUS = _prefixed_interoperability_focus(
    HALLUCINATE_ENV_PREFIX,
    "hallucinate_app",
)
_HALLUCINATE_BOOTSTRAP_PATHS = _build_agent_supervisor_bootstrap_path_callbacks(
    REPO_ROOT,
    HALLUCINATE_ENV_PREFIX,
    DEFAULT_TODO_PATH,
    HALLUCINATE_DATA_PATHS,
    todo_key=TASK_BOARD_PATH_KEY,
    objective_path=DEFAULT_OBJECTIVE_GOAL_HEAP_PATH,
    objective_path_key="objective_goal_heap_path",
)
HALLUCINATE_BOOTSTRAP_SPECS = _HALLUCINATE_BOOTSTRAP_PATHS.specs
_RUNTIME_ENVIRONMENT = _build_repo_runtime_environment_callbacks(
    REPO_ROOT,
    primary_package_names=("ipfs_accelerate",),
)
_enter_runtime_environment = _RUNTIME_ENVIRONMENT.enter
_ensure_ipfs_accelerate_path = _RUNTIME_ENVIRONMENT.ensure_primary_pythonpath
_ensure_runtime_pythonpath = _RUNTIME_ENVIRONMENT.ensure_pythonpath

logger = logging.getLogger("hallucinate_multimodal_control_todo_daemon")
hallucinate_multimodal_bootstrap_paths = _HALLUCINATE_BOOTSTRAP_PATHS.resolve
ensure_hallucinate_multimodal_bootstrap_paths = _HALLUCINATE_BOOTSTRAP_PATHS.ensure
HALLUCINATE_STATE_PATHS = namespace_implementation_state_artifact_paths(HALLUCINATE_DATA_PATHS)


record_objective_goal_findings = build_namespace_objective_backlog_recorder(
    repo_root=REPO_ROOT,
    namespace_paths=HALLUCINATE_DATA_PATHS,
    objective_path=DEFAULT_OBJECTIVE_GOAL_HEAP_PATH,
    todo_path=DEFAULT_TODO_PATH,
    strategy_path=HALLUCINATE_STATE_PATHS["strategy_path"],
    state_path=HALLUCINATE_STATE_PATHS["state_path"],
    task_header_prefix_value="## HAO-",
    depends_on_if_present=("HAO-013",),
    **OBJECTIVE_REFILL_SETTINGS.recorder_kwargs(),
    summary_prefix="Close virtual AI OS objective gap",
    discovery_output_path_default=DISCOVERY_OUTPUT_PATH,
    commit_outputs=True,
    commit_subject="HAO: record objective goal backlog findings",
    prepare_environment=_ensure_ipfs_accelerate_path,
)

record_codebase_scan_findings = build_namespace_codebase_scan_recorder(
    repo_root=REPO_ROOT,
    namespace_paths=HALLUCINATE_DATA_PATHS,
    todo_path=DEFAULT_TODO_PATH,
    state_path=HALLUCINATE_STATE_PATHS["state_path"],
    strategy_path=HALLUCINATE_STATE_PATHS["strategy_path"],
    task_header_prefix_value="## HAO-",
    depends_on_if_present=("HAO-013",),
    **CODEBASE_SCAN_SETTINGS.recorder_kwargs(),
    discovery_output_path_default=DISCOVERY_OUTPUT_PATH,
    skip_prefixes=CODEBASE_SCAN_SKIP_PREFIXES,
    commit_outputs=True,
    commit_subject="HAO: record codebase scan backlog findings",
    prepare_environment=_ensure_ipfs_accelerate_path,
)

record_retry_budget_findings = build_namespace_retry_budget_recorder(
    namespace_paths=HALLUCINATE_DATA_PATHS,
    todo_path=DEFAULT_TODO_PATH,
    events_path=HALLUCINATE_STATE_PATHS["events_path"],
    strategy_path=HALLUCINATE_STATE_PATHS["strategy_path"],
    task_header_prefix_value="## HAO-",
    validation_retry_budget=VALIDATION_RETRY_BUDGET,
    merge_retry_budget=MERGE_RETRY_BUDGET,
    validation_depends_on_if_present=("HAO-013",),
    discovery_output_path_default=DISCOVERY_OUTPUT_PATH,
    strip_validation_failure_kind=True,
    commit_outputs=True,
    commit_subject="HAO: record retry-budget guardrail outputs",
    prepare_environment=_ensure_ipfs_accelerate_path,
)


_hallucinate_refill_hooks = build_daemon_refill_hooks_factory_from_recorders(
    objective_recorder=record_objective_goal_findings,
    codebase_scan_recorder=record_codebase_scan_findings,
    retry_budget_recorder=record_retry_budget_findings,
    discovery_dir=DISCOVERY_DIR,
    objective_path_key="objective_goal_heap_path",
    repo_root=REPO_ROOT,
    scope_label="Hallucinate",
    after_order=("retry-budget", "objective-goal", "codebase-scan"),
)
_hallucinate_daemon_runner = build_namespace_daemon_bootstrap_runner(
    repo_root=REPO_ROOT,
    logger=logger,
    namespace_paths=HALLUCINATE_DATA_PATHS,
    ensure_paths=ensure_hallucinate_multimodal_bootstrap_paths,
    enter_runtime_environment=_enter_runtime_environment,
    task_prefix="## HAO-",
    state_prefix="hallucinate_multimodal_control",
    todo_path_key=TASK_BOARD_PATH_KEY,
    todo_path_flag=TASK_BOARD_PATH_OPTION,
    objective_path_key="objective_goal_heap_path",
    hooks_factory=_hallucinate_refill_hooks,
    default_worktree_submodule_paths=HALLUCINATE_WORKTREE_SUBMODULE_PATHS,
    default_objective_path=DEFAULT_OBJECTIVE_GOAL_HEAP_PATH,
    pass_complete_message="Hallucinate multimodal-control daemon pass complete: %s",
)


def main(argv: list[str] | None = None) -> None:
    _hallucinate_daemon_runner.run(argv)


if __name__ == "__main__":
    main()
