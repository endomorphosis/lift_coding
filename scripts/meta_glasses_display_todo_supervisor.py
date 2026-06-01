#!/usr/bin/env python3
"""Run the accelerator backlog supervisor for display-widget work."""

from __future__ import annotations

import logging
import os
import shlex
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
IPFS_ACCELERATE_ROOT = REPO_ROOT / "external" / "ipfs_accelerate"
IPFS_DATASETS_ROOT = REPO_ROOT / "external" / "ipfs_datasets"
TASK_BOARD_PATH = REPO_ROOT / "implementation_plan" / "docs" / (
    "18-swissknife-meta-glasses-display-widgets." + "to" + "do.md"
)
TASK_BOARD_PATH_OPTION = "--" + "to" + "do" + "-path"
STATE_DIR = REPO_ROOT / "data" / "meta_glasses_display_widgets" / "state"
WORKTREE_ROOT = REPO_ROOT / "data" / "meta_glasses_display_widgets" / "worktrees"
DISCOVERY_DIR = REPO_ROOT / "data" / "meta_glasses_display_widgets" / "discovery"
DAEMON_SCRIPT_PATH = REPO_ROOT / "scripts" / "meta_glasses_display_todo_daemon.py"
OBJECTIVE_HEAP_PATH = REPO_ROOT / "implementation_plan" / "docs" / "23-virtual-ai-os-objective-goal-heap.md"
OBJECTIVE_GRAPH_PATH = REPO_ROOT / "data" / "meta_glasses_display_widgets" / "objective_graph.json"
OBJECTIVE_BUNDLE_DIR = REPO_ROOT / "data" / "meta_glasses_display_widgets" / "objective_bundles"
OBJECTIVE_DATASET_DIR = REPO_ROOT / "data" / "meta_glasses_display_widgets" / "objective_datasets"
OBJECTIVE_TODO_VECTOR_INDEX_PATH = OBJECTIVE_BUNDLE_DIR / "todo_vector_index.json"
OBJECTIVE_SCAN_MIN_OPEN_TASKS = int(os.environ.get("HANDSFREE_MGW_OBJECTIVE_SCAN_MIN_OPEN_TASKS", "20"))
OBJECTIVE_SCAN_MAX_FINDINGS = int(os.environ.get("HANDSFREE_MGW_OBJECTIVE_SCAN_MAX_FINDINGS", "12"))
OBJECTIVE_SCAN_COOLDOWN_SECONDS = int(os.environ.get("HANDSFREE_MGW_OBJECTIVE_SCAN_COOLDOWN_SECONDS", "900"))
OBJECTIVE_SURPLUS_FINDINGS_PER_GOAL = int(os.environ.get("HANDSFREE_MGW_OBJECTIVE_SURPLUS_FINDINGS_PER_GOAL", "6"))
OBJECTIVE_SURPLUS_MIN_TERMS_PER_TODO = int(os.environ.get("HANDSFREE_MGW_OBJECTIVE_SURPLUS_MIN_TERMS_PER_TODO", "4"))
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
DISCOVERY_EXPANSION_OUTPUTS = (
    TASK_BOARD_PATH.relative_to(REPO_ROOT).as_posix(),
    "implementation_plan/docs/18-swissknife-meta-glasses-display-widgets.md",
    DISCOVERY_DIR.relative_to(REPO_ROOT).as_posix(),
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
    f"{TASK_BOARD_PATH.relative_to(REPO_ROOT).as_posix()} "
    "implementation_plan/docs/18-swissknife-meta-glasses-display-widgets.md"
)

if str(IPFS_ACCELERATE_ROOT) not in sys.path:
    sys.path.insert(0, str(IPFS_ACCELERATE_ROOT))

from ipfs_accelerate_py.agent_supervisor.wrapper_utils import (  # noqa: E402
    build_runtime_environment_callback as _build_runtime_environment_callback,
    default_llm_merge_resolver_command as _shared_default_llm_merge_resolver_command,
    env_csv_tuple as _env_csv_tuple,
)
from ipfs_accelerate_py.agent_supervisor.backlog_refinery import (  # noqa: E402
    ensure_task_blocks_present as _ensure_task_blocks_present,
)
from ipfs_accelerate_py.agent_supervisor.implementation_supervisor_runner import (  # noqa: E402
    CodebaseRefillDefaults,
    ImplementationSupervisorDefaults,
    ObjectiveRefillDefaults,
    apply_portal_implementation_supervisor_defaults,
    build_supervisor_refill_hooks,
    build_supervisor_retry_budget_refill_callback,
    run_configured_portal_implementation_supervisor,
)

META_DISPLAY_INTEROPERABILITY_FOCUS = _env_csv_tuple(
    "HANDSFREE_MGW_INTEROPERABILITY_FOCUS",
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
_enter_runtime_environment = _build_runtime_environment_callback(
    REPO_ROOT,
    (IPFS_ACCELERATE_ROOT, IPFS_DATASETS_ROOT),
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


def _default_llm_merge_resolver_command() -> str:
    return _shared_default_llm_merge_resolver_command(
        primary_env_var="HANDSFREE_MGW_LLM_MERGE_RESOLVER_COMMAND"
    )


def ensure_post_initial_discovery_backlog(todo_path: Path = TASK_BOARD_PATH) -> bool:
    """Keep the post-initial discovery expansion tasks in the supervised board."""
    return _ensure_task_blocks_present(
        todo_path,
        (
            ("MGW-013", DISCOVERY_EXPANSION_TASK),
            ("MGW-014", SUPERVISOR_GUARDRAIL_TASK),
        ),
    )


def validation_environment_summary() -> dict[str, object]:
    """Expose the enforced Android validation environment for tests and operators."""

    return android_validation_environment(REPO_ROOT)


def _run_supervisor(argv: list[str]) -> None:
    retry_budget_hook = build_supervisor_retry_budget_refill_callback(
        record_retry_budget_findings,
        discovery_dir=DISCOVERY_DIR,
    )

    if "--ensure-running" in argv:
        logger.info("Display-widget supervisor ensure requested; running supervisor in foreground.")
    run_configured_portal_implementation_supervisor(
        argv,
        repo_root=REPO_ROOT,
        logger=logger,
        daemon_script_path=DAEMON_SCRIPT_PATH,
        worktree_submodule_paths=META_DISPLAY_WORKTREE_SUBMODULE_PATHS,
        hooks=build_supervisor_refill_hooks(
            (("retry-budget", retry_budget_hook),),
            scope_label="validation",
        ),
        once_complete_message="Display-widget implementation supervisor check complete: %s",
    )


def main(argv: list[str] | None = None) -> None:
    args = list(sys.argv[1:] if argv is None else argv)
    _enter_runtime_environment()
    _bootstrap_android_validation_env()
    ensure_post_initial_discovery_backlog(TASK_BOARD_PATH)
    enforce_android_validation_environment(TASK_BOARD_PATH)

    args = apply_portal_implementation_supervisor_defaults(
        args,
        defaults=ImplementationSupervisorDefaults(
            todo_path=TASK_BOARD_PATH,
            state_dir=STATE_DIR,
            task_prefix="## MGW-",
            state_prefix="meta_glasses_display",
            worktree_root=WORKTREE_ROOT,
            daemon_script_path=DAEMON_SCRIPT_PATH,
            supervisor_script_path=Path(__file__).resolve(),
            todo_path_flag=TASK_BOARD_PATH_OPTION,
            llm_merge_resolver_command=_default_llm_merge_resolver_command(),
        ),
        objective=ObjectiveRefillDefaults(
            objective_path=OBJECTIVE_HEAP_PATH,
            objective_graph_path=OBJECTIVE_GRAPH_PATH,
            objective_bundle_dir=OBJECTIVE_BUNDLE_DIR,
            objective_dataset_dir=OBJECTIVE_DATASET_DIR,
            objective_discovery_dir=DISCOVERY_DIR,
            objective_discovery_output_path="data/meta_glasses_display_widgets/discovery",
            objective_scan_min_open_tasks=OBJECTIVE_SCAN_MIN_OPEN_TASKS,
            objective_scan_max_findings=OBJECTIVE_SCAN_MAX_FINDINGS,
            objective_scan_cooldown_seconds=OBJECTIVE_SCAN_COOLDOWN_SECONDS,
            objective_todo_vector_index_path=OBJECTIVE_TODO_VECTOR_INDEX_PATH,
            objective_surplus_findings_per_goal=OBJECTIVE_SURPLUS_FINDINGS_PER_GOAL,
            objective_surplus_min_terms_per_todo=OBJECTIVE_SURPLUS_MIN_TERMS_PER_TODO,
            objective_interoperability_focus=META_DISPLAY_INTEROPERABILITY_FOCUS,
            seed_interoperability_goals=True,
        ),
        codebase=CodebaseRefillDefaults(
            codebase_scan_discovery_dir=DISCOVERY_DIR,
            codebase_scan_discovery_output_path="data/meta_glasses_display_widgets/discovery",
            codebase_scan_min_open_tasks=0,
            codebase_scan_skip_prefixes=CODEBASE_SCAN_SKIP_PREFIXES,
        ),
    )
    _run_supervisor(args)


if __name__ == "__main__":
    main()
