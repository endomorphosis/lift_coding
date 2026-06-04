#!/usr/bin/env python3
"""Run the accelerator backlog supervisor for display-widget work."""

from __future__ import annotations

import logging
import shlex
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
IPFS_ACCELERATE_ROOT = REPO_ROOT / "external" / "ipfs_accelerate"
IPFS_DATASETS_ROOT = REPO_ROOT / "external" / "ipfs_datasets"

if str(IPFS_ACCELERATE_ROOT) not in sys.path:
    sys.path.insert(0, str(IPFS_ACCELERATE_ROOT))

from ipfs_accelerate_py.agent_supervisor.wrapper_utils import (  # noqa: E402
    build_prefixed_bootstrap_path_callbacks as _build_prefixed_bootstrap_path_callbacks,
    build_prefixed_default_llm_merge_resolver_command_callback as _prefixed_llm_merge_callback,
    prefixed_interoperability_focus as _prefixed_interoperability_focus,
    prefixed_objective_refill_env_settings as _prefixed_objective_refill_env_settings,
    task_board_filename as _task_board_filename,
    task_board_path_option as _task_board_path_option,
)

TASK_BOARD_PATH = REPO_ROOT / "implementation_plan" / "docs" / (
    _task_board_filename("18-swissknife-meta-glasses-display-widgets")
)
META_DISPLAY_ENV_PREFIX = "HANDSFREE_MGW"
TASK_BOARD_PATH_OPTION = _task_board_path_option()
STATE_DIR = REPO_ROOT / "data" / "meta_glasses_display_widgets" / "state"
WORKTREE_ROOT = REPO_ROOT / "data" / "meta_glasses_display_widgets" / "worktrees"
DISCOVERY_DIR = REPO_ROOT / "data" / "meta_glasses_display_widgets" / "discovery"
DAEMON_SCRIPT_PATH = REPO_ROOT / "scripts" / "meta_glasses_display_todo_daemon.py"
OBJECTIVE_HEAP_PATH = REPO_ROOT / "implementation_plan" / "docs" / "23-virtual-ai-os-objective-goal-heap.md"
OBJECTIVE_GRAPH_PATH = REPO_ROOT / "data" / "meta_glasses_display_widgets" / "objective_graph.json"
OBJECTIVE_BUNDLE_DIR = REPO_ROOT / "data" / "meta_glasses_display_widgets" / "objective_bundles"
OBJECTIVE_DATASET_DIR = REPO_ROOT / "data" / "meta_glasses_display_widgets" / "objective_datasets"
OBJECTIVE_TODO_VECTOR_INDEX_PATH = OBJECTIVE_BUNDLE_DIR / "todo_vector_index.json"
_META_DISPLAY_BOOTSTRAP_PATHS = _build_prefixed_bootstrap_path_callbacks(
    REPO_ROOT,
    META_DISPLAY_ENV_PREFIX,
    (
        ("todo_path", TASK_BOARD_PATH),
        ("state_dir", STATE_DIR),
        ("worktree_root", WORKTREE_ROOT),
        ("discovery_dir", DISCOVERY_DIR),
        ("objective_heap_path", OBJECTIVE_HEAP_PATH),
        ("objective_graph_path", OBJECTIVE_GRAPH_PATH),
        ("objective_bundle_dir", OBJECTIVE_BUNDLE_DIR),
        ("objective_dataset_dir", OBJECTIVE_DATASET_DIR),
        ("objective_todo_vector_index_path", OBJECTIVE_TODO_VECTOR_INDEX_PATH),
    ),
    ("state_dir", "worktree_root", "discovery_dir", "objective_bundle_dir", "objective_dataset_dir"),
)
META_DISPLAY_BOOTSTRAP_SPECS = _META_DISPLAY_BOOTSTRAP_PATHS.specs
OBJECTIVE_REFILL_SETTINGS = _prefixed_objective_refill_env_settings(META_DISPLAY_ENV_PREFIX)
OBJECTIVE_SCAN_MIN_OPEN_TASKS = OBJECTIVE_REFILL_SETTINGS.min_open_tasks
OBJECTIVE_SCAN_MAX_FINDINGS = OBJECTIVE_REFILL_SETTINGS.max_findings
OBJECTIVE_SCAN_COOLDOWN_SECONDS = OBJECTIVE_REFILL_SETTINGS.cooldown_seconds
OBJECTIVE_SURPLUS_FINDINGS_PER_GOAL = OBJECTIVE_REFILL_SETTINGS.surplus_findings_per_goal
OBJECTIVE_SURPLUS_MIN_TERMS_PER_TODO = OBJECTIVE_REFILL_SETTINGS.surplus_min_terms_per_todo
INITIAL_BACKLOG_TASK_IDS = tuple(f"MGW-{index:03d}" for index in range(1, 13))
INITIAL_BACKLOG_DEPENDENCIES = ", ".join(INITIAL_BACKLOG_TASK_IDS)
BACKLOG_PENDING_STATUS = "to" + "do"
CODEBASE_SCAN_SKIP_PREFIXES = (
    "data/meta_glasses_display_widgets/discovery/",
    "data/meta_glasses_display_widgets/objective_bundles/",
    "data/meta_glasses_display_widgets/objective_datasets/",
    "data/hallucinate_multimodal_control/discovery/",
    "data/meta_glasses_display_widgets/state/",
    "data/meta_glasses_display_widgets/worktrees/",
)
TASK_BOARD_OUTPUT_PATH = _META_DISPLAY_BOOTSTRAP_PATHS.output_path(
    "todo_path",
    f"implementation_plan/docs/{_task_board_filename('18-swissknife-meta-glasses-display-widgets')}",
    {"todo_path": TASK_BOARD_PATH},
)
DISCOVERY_OUTPUT_PATH = _META_DISPLAY_BOOTSTRAP_PATHS.output_path(
    "discovery_dir",
    "data/meta_glasses_display_widgets/discovery",
    {"discovery_dir": DISCOVERY_DIR},
)
DISCOVERY_EXPANSION_OUTPUTS = (
    TASK_BOARD_OUTPUT_PATH,
    "implementation_plan/docs/18-swissknife-meta-glasses-display-widgets.md",
    DISCOVERY_OUTPUT_PATH,
)
DISCOVERY_EXPANSION_OUTPUTS_TEXT = ", ".join(DISCOVERY_EXPANSION_OUTPUTS)
DISCOVERY_EXPANSION_SEARCH_PATTERN = "|".join(
    (
        "MGW-013",
        "unknown " + "unknowns",
        "Discovery Expansion",
        "discovered",
    )
)
DISCOVERY_EXPANSION_VALIDATION = (
    "PYTHONPATH=external/ipfs_accelerate:external/ipfs_datasets "
    "pytest tests/test_meta_glasses_display_todo_queue.py; "
    f"rg -n {shlex.quote(DISCOVERY_EXPANSION_SEARCH_PATTERN)} "
    f"{TASK_BOARD_OUTPUT_PATH} "
    "implementation_plan/docs/18-swissknife-meta-glasses-display-widgets.md"
)

from ipfs_accelerate_py.agent_supervisor.wrapper_utils import (  # noqa: E402
    build_runtime_environment_callbacks as _build_runtime_environment_callbacks,
)
from ipfs_accelerate_py.agent_supervisor.backlog_refinery import (  # noqa: E402
    build_task_blocks_ensurer as _build_task_blocks_ensurer,
)
from ipfs_accelerate_py.agent_supervisor.implementation_supervisor_runner import (  # noqa: E402
    apply_portal_implementation_supervisor_defaults_from_paths,
    build_codebase_refill_defaults_from_paths,
    build_configured_supervisor_runtime,
    build_objective_refill_defaults_from_paths,
    build_supervisor_refill_hooks,
    build_supervisor_retry_budget_refill_callback,
)
from ipfs_accelerate_py.agent_supervisor.todo_daemon.supervisor_runtime import (  # noqa: E402
    pop_bool_flag as _pop_bool_flag,
)

META_DISPLAY_INTEROPERABILITY_FOCUS = _prefixed_interoperability_focus(
    META_DISPLAY_ENV_PREFIX,
    "hallucinate_app",
)

SCRIPTS_DIR = Path(__file__).resolve().parent
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

from meta_glasses_display_todo_daemon import (  # noqa: E402
    _bootstrap_android_validation_env,
    android_validation_environment,
    enforce_android_validation_environment,
    META_DISPLAY_WORKTREE_SUBMODULE_PATHS,
    record_retry_budget_findings,
)

logger = logging.getLogger("meta_glasses_display_todo_supervisor")
meta_display_bootstrap_paths = _META_DISPLAY_BOOTSTRAP_PATHS.resolve
ensure_meta_display_bootstrap_paths = _META_DISPLAY_BOOTSTRAP_PATHS.ensure
_RUNTIME_ENVIRONMENT = _build_runtime_environment_callbacks(
    REPO_ROOT,
    (IPFS_ACCELERATE_ROOT, IPFS_DATASETS_ROOT),
)
_enter_runtime_environment = _RUNTIME_ENVIRONMENT.enter
_ensure_runtime_pythonpath = _RUNTIME_ENVIRONMENT.ensure_pythonpath
META_DISPLAY_SUPERVISOR_PROCESS_MARKERS = ("meta_glasses_display_todo_supervisor.py",)
_meta_display_supervisor_runtime = build_configured_supervisor_runtime(
    repo_root=REPO_ROOT,
    script_path=Path(__file__).resolve(),
    process_match_any=META_DISPLAY_SUPERVISOR_PROCESS_MARKERS,
    prepare_environment=_ensure_runtime_pythonpath,
)


def repair_meta_display_supervisor_runtime(state_dir: Path, state_prefix: str) -> dict[str, object]:
    """Clear stale Meta-display supervisor/daemon markers before health checks."""

    return _meta_display_supervisor_runtime.repair_runtime(state_dir, state_prefix)


def meta_display_supervisor_is_running(state_dir: Path, state_prefix: str) -> bool:
    return _meta_display_supervisor_runtime.is_running(state_dir, state_prefix)


def ensure_meta_display_supervisor_running(argv: list[str], *, state_dir: Path, state_prefix: str) -> dict[str, object]:
    return _meta_display_supervisor_runtime.ensure_running(
        argv,
        state_dir=state_dir,
        state_prefix=state_prefix,
    )

DISCOVERY_EXPANSION_TASK = f"""## MGW-013 Investigate implementation unknowns and expand the backlog

- Status: {BACKLOG_PENDING_STATUS}
- Completion: manual
- Priority: P2
- Track: ops
- Depends on: {INITIAL_BACKLOG_DEPENDENCIES}
- Outputs: {DISCOVERY_EXPANSION_OUTPUTS_TEXT}
- Validation: {DISCOVERY_EXPANSION_VALIDATION}
- Acceptance: After the initial backlog completes, investigate the Swissknife, HandsFree backend, mobile DAT bridge, external Meta DAT references, and hardware-free test harness code paths for missed work. Append new daemon-parseable MGW tasks for discovered gaps, or write a dated no-new-unknowns discovery report with evidence and commands run.
"""

SUPERVISOR_GUARDRAIL_TASK = f"""## MGW-014 Add supervisor validation-environment and retry-budget guardrails

- Status: {BACKLOG_PENDING_STATUS}
- Completion: manual
- Priority: P1
- Track: ops
- Depends on: MGW-013
- Outputs: scripts/meta_glasses_display_todo_supervisor.py, scripts/meta_glasses_display_todo_daemon.py, tests/test_meta_glasses_display_todo_queue.py, data/meta_glasses_display_widgets/discovery
- Validation: PYTHONPATH=external/ipfs_accelerate:external/ipfs_datasets pytest tests/test_meta_glasses_display_todo_queue.py; PYTHONPATH=external/ipfs_accelerate:external/ipfs_datasets python3 scripts/meta_glasses_display_todo_supervisor.py --once
- Acceptance: Discovered during MGW-010: Android validation needs the repo-local JDK 17/Android SDK environment, and repeated validation failures should become evidence-backed discovery follow-up items instead of indefinite retry loops. The supervisor documents/enforces the validation environment and records retry-budget findings as daemon-parseable backlog work.
"""


_default_llm_merge_resolver_command = _prefixed_llm_merge_callback(
    META_DISPLAY_ENV_PREFIX
)


ensure_post_initial_discovery_backlog = _build_task_blocks_ensurer(
    (
        ("MGW-013", DISCOVERY_EXPANSION_TASK),
        ("MGW-014", SUPERVISOR_GUARDRAIL_TASK),
    ),
    default_todo_path=TASK_BOARD_PATH,
)


def validation_environment_summary() -> dict[str, object]:
    """Expose the enforced Android validation environment for tests and operators."""

    return android_validation_environment(REPO_ROOT)


def _run_supervisor(argv: list[str], *, paths: dict[str, Path], ensure_running: bool) -> None:
    retry_budget_hook = build_supervisor_retry_budget_refill_callback(
        record_retry_budget_findings,
        discovery_dir=paths["discovery_dir"],
        extra_kwargs={
            "discovery_output_path": _META_DISPLAY_BOOTSTRAP_PATHS.output_path(
                "discovery_dir",
                "data/meta_glasses_display_widgets/discovery",
                paths,
            ),
        },
    )

    if ensure_running:
        logger.info("Display-widget supervisor ensure requested; running supervisor in foreground.")
    _meta_display_supervisor_runtime.run_configured(
        argv,
        logger=logger,
        daemon_script_path=DAEMON_SCRIPT_PATH,
        worktree_submodule_paths=META_DISPLAY_WORKTREE_SUBMODULE_PATHS,
        hooks=build_supervisor_refill_hooks(
            (("retry-budget", retry_budget_hook),),
            scope_label="validation",
        ),
        once_complete_message="Display-widget implementation supervisor check complete: %s",
        ensure_running=ensure_running,
        ensure_running_message="Display-widget implementation supervisor ensure complete: %s",
        repair_runtime_message="Repaired stale display-widget supervisor runtime markers: %s",
    )


def main(argv: list[str] | None = None) -> None:
    args = list(sys.argv[1:] if argv is None else argv)
    ensure_running = _pop_bool_flag(args, "--ensure-running")
    _enter_runtime_environment()
    paths = ensure_meta_display_bootstrap_paths()
    _bootstrap_android_validation_env()
    ensure_post_initial_discovery_backlog(paths["todo_path"])
    enforce_android_validation_environment(paths["todo_path"])
    discovery_output_path = _META_DISPLAY_BOOTSTRAP_PATHS.output_path(
        "discovery_dir",
        "data/meta_glasses_display_widgets/discovery",
        paths,
    )

    args = apply_portal_implementation_supervisor_defaults_from_paths(
        args,
        paths,
        task_prefix="## MGW-",
        state_prefix="meta_glasses_display",
        daemon_script_path=DAEMON_SCRIPT_PATH,
        supervisor_script_path=Path(__file__).resolve(),
        todo_path_flag=TASK_BOARD_PATH_OPTION,
        llm_merge_resolver_command=_default_llm_merge_resolver_command(),
        objective=build_objective_refill_defaults_from_paths(
            paths,
            objective_path_key="objective_heap_path",
            objective_graph_path_key="objective_graph_path",
            objective_bundle_dir_key="objective_bundle_dir",
            objective_dataset_dir_key="objective_dataset_dir",
            objective_discovery_dir_key="discovery_dir",
            objective_discovery_output_path=discovery_output_path,
            objective_todo_vector_index_path_key="objective_todo_vector_index_path",
            objective_interoperability_focus=META_DISPLAY_INTEROPERABILITY_FOCUS,
            seed_interoperability_goals=True,
            **OBJECTIVE_REFILL_SETTINGS.objective_refill_kwargs(),
        ),
        codebase=build_codebase_refill_defaults_from_paths(
            paths,
            codebase_scan_discovery_dir_key="discovery_dir",
            codebase_scan_discovery_output_path=discovery_output_path,
            codebase_scan_min_open_tasks=0,
            codebase_scan_skip_prefixes=CODEBASE_SCAN_SKIP_PREFIXES,
        ),
    )
    _run_supervisor(args, paths=paths, ensure_running=ensure_running)


if __name__ == "__main__":
    main()
