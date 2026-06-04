#!/usr/bin/env python3
"""Run the generalized accelerator backlog daemon for Hallucinate multimodal-control work."""

from __future__ import annotations

import logging
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
IPFS_DATASETS_ROOT = REPO_ROOT / "external" / "ipfs_datasets"
IPFS_ACCELERATE_ROOT = REPO_ROOT / "external" / "ipfs_accelerate"

if str(IPFS_ACCELERATE_ROOT) not in sys.path:
    sys.path.insert(0, str(IPFS_ACCELERATE_ROOT))

from ipfs_accelerate_py.agent_supervisor.wrapper_utils import (  # noqa: E402
    prefixed_env_csv_tuple as _prefixed_env_csv_tuple,
    prefixed_env_int as _prefixed_env_int,
    prefixed_env_path as _prefixed_env_path,
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
OBJECTIVE_SCAN_MIN_OPEN_TASKS = _prefixed_env_int(
    HALLUCINATE_ENV_PREFIX,
    "OBJECTIVE_SCAN_MIN_OPEN_TASKS",
    20,
)
OBJECTIVE_SCAN_MAX_FINDINGS = _prefixed_env_int(
    HALLUCINATE_ENV_PREFIX,
    "OBJECTIVE_SCAN_MAX_FINDINGS",
    12,
)
OBJECTIVE_SCAN_COOLDOWN_SECONDS = _prefixed_env_int(
    HALLUCINATE_ENV_PREFIX,
    "OBJECTIVE_SCAN_COOLDOWN_SECONDS",
    900,
)
OBJECTIVE_SURPLUS_FINDINGS_PER_GOAL = _prefixed_env_int(
    HALLUCINATE_ENV_PREFIX,
    "OBJECTIVE_SURPLUS_FINDINGS_PER_GOAL",
    6,
)
OBJECTIVE_SURPLUS_MIN_TERMS_PER_TODO = _prefixed_env_int(
    HALLUCINATE_ENV_PREFIX,
    "OBJECTIVE_SURPLUS_MIN_TERMS_PER_TODO",
    4,
)
CODEBASE_SCAN_MIN_OPEN_TASKS = _prefixed_env_int(
    HALLUCINATE_ENV_PREFIX,
    "CODEBASE_SCAN_MIN_OPEN_TASKS",
    5,
)
CODEBASE_SCAN_MAX_FINDINGS = _prefixed_env_int(
    HALLUCINATE_ENV_PREFIX,
    "CODEBASE_SCAN_MAX_FINDINGS",
    5,
)
CODEBASE_SCAN_COOLDOWN_SECONDS = _prefixed_env_int(
    HALLUCINATE_ENV_PREFIX,
    "CODEBASE_SCAN_COOLDOWN_SECONDS",
    21600,
)
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
    build_runtime_environment_callback as _build_runtime_environment_callback,
)
from ipfs_accelerate_py.agent_supervisor.backlog_refinery import (  # noqa: E402
    ConfiguredCodebaseScanRecorder,
    ConfiguredObjectiveBacklogRecorder,
    ConfiguredRetryBudgetRecorder,
)
from ipfs_accelerate_py.agent_supervisor.implementation_daemon_runner import (  # noqa: E402
    ImplementationDaemonDefaults,
    apply_portal_implementation_daemon_defaults,
    build_daemon_codebase_scan_refill_callback,
    build_daemon_objective_refill_callback,
    build_daemon_refill_hooks,
    build_daemon_retry_budget_refill_callback,
    run_configured_portal_implementation_daemon,
)

HALLUCINATE_INTEROPERABILITY_FOCUS = _prefixed_env_csv_tuple(
    HALLUCINATE_ENV_PREFIX,
    "INTEROPERABILITY_FOCUS",
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
_enter_runtime_environment = _build_runtime_environment_callback(
    REPO_ROOT,
    (IPFS_ACCELERATE_ROOT, IPFS_DATASETS_ROOT),
)
_ensure_ipfs_accelerate_path = _build_runtime_environment_callback(
    REPO_ROOT,
    (IPFS_ACCELERATE_ROOT,),
    chdir=False,
)
_ensure_runtime_pythonpath = _build_runtime_environment_callback(
    REPO_ROOT,
    (IPFS_ACCELERATE_ROOT, IPFS_DATASETS_ROOT),
    chdir=False,
)

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
    min_open_tasks=OBJECTIVE_SCAN_MIN_OPEN_TASKS,
    max_findings=OBJECTIVE_SCAN_MAX_FINDINGS,
    cooldown_seconds=OBJECTIVE_SCAN_COOLDOWN_SECONDS,
    surplus_findings_per_goal=OBJECTIVE_SURPLUS_FINDINGS_PER_GOAL,
    surplus_min_terms_per_todo=OBJECTIVE_SURPLUS_MIN_TERMS_PER_TODO,
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
    min_open_tasks=CODEBASE_SCAN_MIN_OPEN_TASKS,
    max_findings=CODEBASE_SCAN_MAX_FINDINGS,
    cooldown_seconds=CODEBASE_SCAN_COOLDOWN_SECONDS,
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


def main(argv: list[str] | None = None) -> None:
    args = list(sys.argv[1:] if argv is None else argv)
    paths = ensure_hallucinate_multimodal_bootstrap_paths()
    _enter_runtime_environment()

    args = apply_portal_implementation_daemon_defaults(
        args,
        defaults=ImplementationDaemonDefaults(
            todo_path=paths[TASK_BOARD_PATH_KEY],
            state_dir=paths["state_dir"],
            task_prefix="## HAO-",
            state_prefix="hallucinate_multimodal_control",
            worktree_root=paths["worktree_root"],
            todo_path_flag=TASK_BOARD_PATH_OPTION,
            objective_path=paths["objective_goal_heap_path"],
            objective_bundle_dir=OBJECTIVE_BUNDLE_DIR,
            worktree_submodule_paths=HALLUCINATE_WORKTREE_SUBMODULE_PATHS,
        ),
    )

    objective_hook = build_daemon_objective_refill_callback(
        record_objective_goal_findings,
        discovery_dir=DISCOVERY_DIR,
        objective_path=paths["objective_goal_heap_path"],
        repo_root=REPO_ROOT,
    )
    codebase_scan_hook = build_daemon_codebase_scan_refill_callback(
        record_codebase_scan_findings,
        discovery_dir=DISCOVERY_DIR,
        repo_root=REPO_ROOT,
    )
    retry_budget_hook = build_daemon_retry_budget_refill_callback(
        record_retry_budget_findings,
        discovery_dir=DISCOVERY_DIR,
    )

    run_configured_portal_implementation_daemon(
        args,
        repo_root=REPO_ROOT,
        logger=logger,
        default_worktree_submodule_paths=HALLUCINATE_WORKTREE_SUBMODULE_PATHS,
        default_objective_path=paths["objective_goal_heap_path"],
        default_objective_bundle_dir=OBJECTIVE_BUNDLE_DIR,
        hooks=build_daemon_refill_hooks(
            (
                ("objective-goal", objective_hook),
                ("codebase-scan", codebase_scan_hook),
                ("retry-budget", retry_budget_hook),
            ),
            scope_label="Hallucinate",
            after_order=("retry-budget", "objective-goal", "codebase-scan"),
        ),
        pass_complete_message="Hallucinate multimodal-control daemon pass complete: %s",
    )


if __name__ == "__main__":
    main()
