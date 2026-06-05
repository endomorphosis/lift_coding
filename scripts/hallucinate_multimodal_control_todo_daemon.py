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
    prefixed_codebase_scan_env_settings as _prefixed_codebase_scan_env_settings,
    prefixed_env_path as _prefixed_env_path,
    prefixed_interoperability_focus as _prefixed_interoperability_focus,
    prefixed_objective_refill_env_settings as _prefixed_objective_refill_env_settings,
    task_board_filename as _task_board_filename,
    task_board_path_key as _task_board_path_key,
    task_board_path_option as _task_board_path_option,
)

DEFAULT_TODO_PATH = (
    REPO_ROOT
    / "hallucinate_app"
    / "docs"
    / _task_board_filename("MULTIMODAL_CONTROL_SURFACE_LOGIC_IDL")
)
HALLUCINATE_ENV_PREFIX = "HANDSFREE_HAO"
TASK_BOARD_PATH_OPTION = _task_board_path_option()
TASK_BOARD_PATH_KEY = _task_board_path_key()
DEFAULT_OBJECTIVE_GOAL_HEAP_PATH = _prefixed_env_path(
    HALLUCINATE_ENV_PREFIX,
    "OBJECTIVE_GOAL_HEAP_PATH",
    REPO_ROOT / "implementation_plan" / "docs" / "23-virtual-ai-os-objective-goal-heap.md",
)
DEFAULT_STATE_DIR = REPO_ROOT / "data" / "hallucinate_multimodal_control" / "state"
DEFAULT_WORKTREE_ROOT = REPO_ROOT / "data" / "hallucinate_multimodal_control" / "worktrees"
DISCOVERY_DIR = REPO_ROOT / "data" / "hallucinate_multimodal_control" / "discovery"
OBJECTIVE_BUNDLE_DIR = REPO_ROOT / "data" / "hallucinate_multimodal_control" / "objective_bundles"
OBJECTIVE_DATASET_DIR = REPO_ROOT / "data" / "hallucinate_multimodal_control" / "objective_datasets"
OBJECTIVE_TODO_VECTOR_INDEX_PATH = OBJECTIVE_BUNDLE_DIR / "todo_vector_index.json"
DISCOVERY_OUTPUT_PATH = "data/hallucinate_multimodal_control/discovery"
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
CODEBASE_SCAN_SKIP_PREFIXES = (
    "scripts/",  # supervisor/daemon scripts embed task-board paths by design; exclude from annotation scan
    "data/hallucinate_multimodal_control/discovery/",
    "data/hallucinate_multimodal_control/objective_bundles/",
    "data/hallucinate_multimodal_control/objective_datasets/",
    "data/hallucinate_multimodal_control/state/",
    "data/hallucinate_multimodal_control/worktrees/",
    "data/meta_glasses_display_widgets/discovery/",
    "data/meta_glasses_display_widgets/state/",
    "data/meta_glasses_display_widgets/worktrees/",
    "data/virtual_ai_os/discovery/",
    "data/virtual_ai_os/objective_bundles/",
    "data/virtual_ai_os/objective_datasets/",
    "data/virtual_ai_os/state/",
    "data/virtual_ai_os/worktrees/",
)
HALLUCINATE_WORKTREE_SUBMODULE_PATHS = ("hallucinate_app", "ipfs_datasets_py", "swissknife")

if str(IPFS_ACCELERATE_ROOT) not in sys.path:
    sys.path.insert(0, str(IPFS_ACCELERATE_ROOT))

from ipfs_accelerate_py.agent_supervisor.wrapper_utils import (  # noqa: E402
    build_prefixed_bootstrap_path_callbacks as _build_prefixed_bootstrap_path_callbacks,
    build_repo_runtime_environment_callbacks as _build_repo_runtime_environment_callbacks,
)
from ipfs_accelerate_py.agent_supervisor.backlog_refinery import (  # noqa: E402
    ConfiguredCodebaseScanRecorder,
    ConfiguredObjectiveBacklogRecorder,
    ConfiguredRetryBudgetRecorder,
)
from ipfs_accelerate_py.agent_supervisor.implementation_daemon_runner import (  # noqa: E402
    build_configured_implementation_daemon_runner,
    build_daemon_refill_hooks_from_recorders,
)

HALLUCINATE_INTEROPERABILITY_FOCUS = _prefixed_interoperability_focus(
    HALLUCINATE_ENV_PREFIX,
    "hallucinate_app",
)
_HALLUCINATE_BOOTSTRAP_PATHS = _build_prefixed_bootstrap_path_callbacks(
    REPO_ROOT,
    HALLUCINATE_ENV_PREFIX,
    (
        (TASK_BOARD_PATH_KEY, DEFAULT_TODO_PATH),
        ("objective_goal_heap_path", DEFAULT_OBJECTIVE_GOAL_HEAP_PATH),
        ("state_dir", DEFAULT_STATE_DIR),
        ("worktree_root", DEFAULT_WORKTREE_ROOT),
    ),
    ("state_dir", "worktree_root"),
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


record_objective_goal_findings = ConfiguredObjectiveBacklogRecorder(
    repo_root=REPO_ROOT,
    objective_path=DEFAULT_OBJECTIVE_GOAL_HEAP_PATH,
    todo_path=DEFAULT_TODO_PATH,
    discovery_dir=DISCOVERY_DIR,
    default_bundle_dir=OBJECTIVE_BUNDLE_DIR,
    default_dataset_dir=OBJECTIVE_DATASET_DIR,
    strategy_path=DEFAULT_STATE_DIR / "hallucinate_multimodal_control_strategy.json",
    state_path=DEFAULT_STATE_DIR / "hallucinate_multimodal_control_task_state.json",
    task_header_prefix_value="## HAO-",
    depends_on_if_present=("HAO-013",),
    **OBJECTIVE_REFILL_SETTINGS.recorder_kwargs(),
    summary_prefix="Close virtual AI OS objective gap",
    discovery_output_path_default=DISCOVERY_OUTPUT_PATH,
    commit_outputs=True,
    commit_subject="HAO: record objective goal backlog findings",
    prepare_environment=_ensure_ipfs_accelerate_path,
)

record_codebase_scan_findings = ConfiguredCodebaseScanRecorder(
    todo_path=DEFAULT_TODO_PATH,
    state_path=DEFAULT_STATE_DIR / "hallucinate_multimodal_control_task_state.json",
    strategy_path=DEFAULT_STATE_DIR / "hallucinate_multimodal_control_strategy.json",
    discovery_dir=DISCOVERY_DIR,
    repo_root=REPO_ROOT,
    task_header_prefix_value="## HAO-",
    depends_on_if_present=("HAO-013",),
    **CODEBASE_SCAN_SETTINGS.recorder_kwargs(),
    discovery_output_path_default=DISCOVERY_OUTPUT_PATH,
    skip_prefixes=CODEBASE_SCAN_SKIP_PREFIXES,
    commit_outputs=True,
    commit_subject="HAO: record codebase scan backlog findings",
    prepare_environment=_ensure_ipfs_accelerate_path,
)

record_retry_budget_findings = ConfiguredRetryBudgetRecorder(
    todo_path=DEFAULT_TODO_PATH,
    events_path=DEFAULT_STATE_DIR / "hallucinate_multimodal_control_events.jsonl",
    strategy_path=DEFAULT_STATE_DIR / "hallucinate_multimodal_control_strategy.json",
    discovery_dir=DISCOVERY_DIR,
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


def _hallucinate_refill_hooks(paths: dict[str, Path]):
    return build_daemon_refill_hooks_from_recorders(
        objective_recorder=record_objective_goal_findings,
        codebase_scan_recorder=record_codebase_scan_findings,
        retry_budget_recorder=record_retry_budget_findings,
        discovery_dir=DISCOVERY_DIR,
        objective_path=paths["objective_goal_heap_path"],
        repo_root=REPO_ROOT,
        scope_label="Hallucinate",
        after_order=("retry-budget", "objective-goal", "codebase-scan"),
    )


def main(argv: list[str] | None = None) -> None:
    args = list(sys.argv[1:] if argv is None else argv)

    build_configured_implementation_daemon_runner(
        repo_root=REPO_ROOT,
        logger=logger,
        default_worktree_submodule_paths=HALLUCINATE_WORKTREE_SUBMODULE_PATHS,
        default_objective_path=DEFAULT_OBJECTIVE_GOAL_HEAP_PATH,
        default_objective_bundle_dir=OBJECTIVE_BUNDLE_DIR,
        pass_complete_message="Hallucinate multimodal-control daemon pass complete: %s",
    ).run_configured_from_bootstrap(
        args,
        ensure_paths=ensure_hallucinate_multimodal_bootstrap_paths,
        enter_runtime_environment=_enter_runtime_environment,
        todo_path_key=TASK_BOARD_PATH_KEY,
        task_prefix="## HAO-",
        state_prefix="hallucinate_multimodal_control",
        todo_path_flag=TASK_BOARD_PATH_OPTION,
        objective_path_key="objective_goal_heap_path",
        objective_bundle_dir=OBJECTIVE_BUNDLE_DIR,
        worktree_submodule_paths=HALLUCINATE_WORKTREE_SUBMODULE_PATHS,
        hooks_factory=_hallucinate_refill_hooks,
    )


if __name__ == "__main__":
    main()
