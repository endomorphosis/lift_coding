#!/usr/bin/env python3
"""Run the generalized accelerator backlog daemon for Hallucinate multimodal-control work."""

from __future__ import annotations

import logging
import os
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
IPFS_DATASETS_ROOT = REPO_ROOT / "external" / "ipfs_datasets"
IPFS_ACCELERATE_ROOT = REPO_ROOT / "external" / "ipfs_accelerate"
DEFAULT_TODO_PATH = REPO_ROOT / "hallucinate_app" / "docs" / ("MULTIMODAL_CONTROL_SURFACE_LOGIC_IDL." + "to" + "do.md")
TASK_BOARD_PATH_OPTION = "--" + "to" + "do" + "-path"
TASK_BOARD_PATH_KEY = "to" + "do_path"
DEFAULT_OBJECTIVE_GOAL_HEAP_PATH = Path(
    os.environ.get(
        "HANDSFREE_HAO_OBJECTIVE_GOAL_HEAP_PATH",
        str(REPO_ROOT / "implementation_plan" / "docs" / "23-virtual-ai-os-objective-goal-heap.md"),
    )
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
OBJECTIVE_SCAN_MIN_OPEN_TASKS = int(os.environ.get("HANDSFREE_HAO_OBJECTIVE_SCAN_MIN_OPEN_TASKS", "20"))
OBJECTIVE_SCAN_MAX_FINDINGS = int(os.environ.get("HANDSFREE_HAO_OBJECTIVE_SCAN_MAX_FINDINGS", "12"))
OBJECTIVE_SCAN_COOLDOWN_SECONDS = int(os.environ.get("HANDSFREE_HAO_OBJECTIVE_SCAN_COOLDOWN_SECONDS", "900"))
OBJECTIVE_SURPLUS_FINDINGS_PER_GOAL = int(os.environ.get("HANDSFREE_HAO_OBJECTIVE_SURPLUS_FINDINGS_PER_GOAL", "6"))
OBJECTIVE_SURPLUS_MIN_TERMS_PER_TODO = int(os.environ.get("HANDSFREE_HAO_OBJECTIVE_SURPLUS_MIN_TERMS_PER_TODO", "4"))
CODEBASE_SCAN_MIN_OPEN_TASKS = int(os.environ.get("HANDSFREE_HAO_CODEBASE_SCAN_MIN_OPEN_TASKS", "5"))
CODEBASE_SCAN_MAX_FINDINGS = int(os.environ.get("HANDSFREE_HAO_CODEBASE_SCAN_MAX_FINDINGS", "5"))
CODEBASE_SCAN_COOLDOWN_SECONDS = int(os.environ.get("HANDSFREE_HAO_CODEBASE_SCAN_COOLDOWN_SECONDS", "21600"))
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
    BootstrapPathSpec,
    bootstrap_runtime_environment as _bootstrap_runtime_environment,
    ensure_named_directories as _ensure_named_directories,
    env_csv_tuple as _env_csv_tuple,
    resolve_bootstrap_paths as _resolve_bootstrap_paths,
)
from ipfs_accelerate_py.agent_supervisor.implementation_daemon_runner import (  # noqa: E402
    ImplementationDaemonDefaults,
    ImplementationDaemonRunContext,
    apply_portal_implementation_daemon_defaults,
    build_daemon_refill_hooks,
    build_portal_implementation_daemon_from_args,
    configure_daemon_logging,
    run_portal_implementation_daemon_loop,
)

HALLUCINATE_INTEROPERABILITY_FOCUS = _env_csv_tuple(
    "HANDSFREE_HAO_INTEROPERABILITY_FOCUS",
    "hallucinate_app",
)

logger = logging.getLogger("hallucinate_multimodal_control_todo_daemon")


def hallucinate_multimodal_bootstrap_paths() -> dict[str, Path]:
    return _resolve_bootstrap_paths(
        REPO_ROOT,
        (
            BootstrapPathSpec(TASK_BOARD_PATH_KEY, DEFAULT_TODO_PATH, "HANDSFREE_HAO_TODO_PATH"),
            BootstrapPathSpec(
                "objective_goal_heap_path",
                DEFAULT_OBJECTIVE_GOAL_HEAP_PATH,
                "HANDSFREE_HAO_OBJECTIVE_GOAL_HEAP_PATH",
            ),
            BootstrapPathSpec("state_dir", DEFAULT_STATE_DIR, "HANDSFREE_HAO_STATE_DIR"),
            BootstrapPathSpec("worktree_root", DEFAULT_WORKTREE_ROOT, "HANDSFREE_HAO_WORKTREE_ROOT"),
        ),
    )


def ensure_hallucinate_multimodal_bootstrap_paths(
    paths: dict[str, Path] | None = None,
) -> dict[str, Path]:
    resolved = paths or hallucinate_multimodal_bootstrap_paths()
    return _ensure_named_directories(resolved, ("state_dir", "worktree_root"))


def _ensure_ipfs_accelerate_path() -> None:
    _bootstrap_runtime_environment(REPO_ROOT, (IPFS_ACCELERATE_ROOT,), chdir=False)


def _ensure_runtime_pythonpath() -> None:
    _bootstrap_runtime_environment(REPO_ROOT, (IPFS_ACCELERATE_ROOT, IPFS_DATASETS_ROOT), chdir=False)


def record_objective_goal_findings(
    *,
    todo_path: Path = DEFAULT_TODO_PATH,
    state_path: Path | None = DEFAULT_STATE_DIR / "hallucinate_multimodal_control_task_state.json",
    strategy_path: Path = DEFAULT_STATE_DIR / "hallucinate_multimodal_control_strategy.json",
    discovery_dir: Path = DISCOVERY_DIR,
    objective_path: Path = DEFAULT_OBJECTIVE_GOAL_HEAP_PATH,
    bundle_dir: Path | None = None,
    dataset_dir: Path | None = None,
    todo_vector_index_path: Path | None = None,
    task_header_prefix: str = "## HAO-",
    repo_root: Path = REPO_ROOT,
    min_open_tasks: int = OBJECTIVE_SCAN_MIN_OPEN_TASKS,
    max_findings: int = OBJECTIVE_SCAN_MAX_FINDINGS,
    cooldown_seconds: int = OBJECTIVE_SCAN_COOLDOWN_SECONDS,
    surplus_findings_per_goal: int = OBJECTIVE_SURPLUS_FINDINGS_PER_GOAL,
    surplus_min_terms_per_todo: int = OBJECTIVE_SURPLUS_MIN_TERMS_PER_TODO,
    force: bool = False,
) -> list[dict[str, object]]:
    """Feed the HAO board from missing evidence in the objective heap."""

    _ensure_ipfs_accelerate_path()
    from ipfs_accelerate_py.agent_supervisor.backlog_refinery import record_configured_objective_backlog_findings

    return record_configured_objective_backlog_findings(
        repo_root=repo_root,
        objective_path=objective_path,
        todo_path=todo_path,
        discovery_dir=discovery_dir,
        bundle_dir=bundle_dir,
        dataset_dir=dataset_dir,
        default_bundle_dir=(
            repo_root
            / "data"
            / "hallucinate_multimodal_control"
            / "objective_bundles"
        ),
        default_dataset_dir=(
            repo_root
            / "data"
            / "hallucinate_multimodal_control"
            / "objective_datasets"
        ),
        strategy_path=strategy_path,
        state_path=state_path,
        task_header_prefix_value=task_header_prefix,
        depends_on_if_present=("HAO-013",),
        min_open_tasks=min_open_tasks,
        max_findings=max_findings,
        cooldown_seconds=cooldown_seconds,
        force=force,
        write_todo_vector_index=True,
        todo_vector_index_path=todo_vector_index_path
        or (
            bundle_dir
            or repo_root
            / "data"
            / "hallucinate_multimodal_control"
            / "objective_bundles"
        )
        / "todo_vector_index.json",
        surplus_findings_per_goal=surplus_findings_per_goal,
        surplus_min_terms_per_todo=surplus_min_terms_per_todo,
        summary_prefix="Close virtual AI OS objective gap",
        discovery_output_path_default=DISCOVERY_OUTPUT_PATH,
        commit_outputs=True,
        commit_subject="HAO: record objective goal backlog findings",
    )


def record_codebase_scan_findings(
    *,
    todo_path: Path = DEFAULT_TODO_PATH,
    state_path: Path | None = DEFAULT_STATE_DIR / "hallucinate_multimodal_control_task_state.json",
    strategy_path: Path = DEFAULT_STATE_DIR / "hallucinate_multimodal_control_strategy.json",
    discovery_dir: Path = DISCOVERY_DIR,
    task_header_prefix: str = "## HAO-",
    repo_root: Path = REPO_ROOT,
    min_open_tasks: int = CODEBASE_SCAN_MIN_OPEN_TASKS,
    max_findings: int = CODEBASE_SCAN_MAX_FINDINGS,
    cooldown_seconds: int = CODEBASE_SCAN_COOLDOWN_SECONDS,
    force: bool = False,
) -> list[dict[str, object]]:
    """Feed the HAO board with accelerator static-scan findings when backlog runs low."""

    _ensure_ipfs_accelerate_path()
    from ipfs_accelerate_py.agent_supervisor.backlog_refinery import record_configured_codebase_scan_findings

    return record_configured_codebase_scan_findings(
        todo_path=todo_path,
        state_path=state_path,
        strategy_path=strategy_path,
        discovery_dir=discovery_dir,
        repo_root=repo_root,
        task_header_prefix_value=task_header_prefix,
        depends_on_if_present=("HAO-013",),
        min_open_tasks=min_open_tasks,
        max_findings=max_findings,
        cooldown_seconds=cooldown_seconds,
        force=force,
        discovery_output_path_default=DISCOVERY_OUTPUT_PATH,
        skip_prefixes=CODEBASE_SCAN_SKIP_PREFIXES,
        commit_outputs=True,
        commit_subject="HAO: record codebase scan backlog findings",
    )


def record_retry_budget_findings(
    *,
    todo_path: Path = DEFAULT_TODO_PATH,
    events_path: Path = DEFAULT_STATE_DIR / "hallucinate_multimodal_control_events.jsonl",
    strategy_path: Path = DEFAULT_STATE_DIR / "hallucinate_multimodal_control_strategy.json",
    discovery_dir: Path = DISCOVERY_DIR,
    task_header_prefix: str = "## HAO-",
    retry_budget: int = VALIDATION_RETRY_BUDGET,
    merge_retry_budget: int = MERGE_RETRY_BUDGET,
) -> list[dict[str, object]]:
    """Turn repeated validation or merge failures into accelerator backlog items."""

    _ensure_ipfs_accelerate_path()
    from ipfs_accelerate_py.agent_supervisor.backlog_refinery import record_configured_retry_budget_findings

    return record_configured_retry_budget_findings(
        todo_path=todo_path,
        events_path=events_path,
        strategy_path=strategy_path,
        discovery_dir=discovery_dir,
        task_header_prefix_value=task_header_prefix,
        validation_retry_budget=retry_budget,
        merge_retry_budget=merge_retry_budget,
        validation_depends_on_if_present=("HAO-013",),
        discovery_output_path_default=DISCOVERY_OUTPUT_PATH,
        strip_validation_failure_kind=True,
        commit_outputs=True,
        commit_subject="HAO: record retry-budget guardrail outputs",
    )


def main(argv: list[str] | None = None) -> None:
    args = list(sys.argv[1:] if argv is None else argv)
    paths = ensure_hallucinate_multimodal_bootstrap_paths()
    _bootstrap_runtime_environment(REPO_ROOT, (IPFS_ACCELERATE_ROOT, IPFS_DATASETS_ROOT))

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

    from ipfs_accelerate_py.agent_supervisor.todo_daemon.implementation_daemon import parse_args

    parsed = parse_args(args)
    configure_daemon_logging(parsed)
    daemon, context = build_portal_implementation_daemon_from_args(
        parsed,
        repo_root=REPO_ROOT,
        default_worktree_submodule_paths=HALLUCINATE_WORKTREE_SUBMODULE_PATHS,
        default_objective_path=paths["objective_goal_heap_path"],
        default_objective_bundle_dir=OBJECTIVE_BUNDLE_DIR,
    )

    def objective_hook(ctx: ImplementationDaemonRunContext) -> list[dict[str, object]]:
        return record_objective_goal_findings(
            todo_path=ctx.parsed.todo_path,
            state_path=ctx.state_path,
            strategy_path=ctx.strategy_path,
            discovery_dir=DISCOVERY_DIR,
            objective_path=paths["objective_goal_heap_path"],
            task_header_prefix=ctx.parsed.task_prefix,
            repo_root=REPO_ROOT,
        )

    def codebase_scan_hook(ctx: ImplementationDaemonRunContext) -> list[dict[str, object]]:
        return record_codebase_scan_findings(
            todo_path=ctx.parsed.todo_path,
            state_path=ctx.state_path,
            strategy_path=ctx.strategy_path,
            discovery_dir=DISCOVERY_DIR,
            task_header_prefix=ctx.parsed.task_prefix,
            repo_root=REPO_ROOT,
        )

    def retry_budget_hook(ctx: ImplementationDaemonRunContext) -> list[dict[str, object]]:
        return record_retry_budget_findings(
            todo_path=ctx.parsed.todo_path,
            events_path=ctx.events_path,
            strategy_path=ctx.strategy_path,
            discovery_dir=DISCOVERY_DIR,
            task_header_prefix=ctx.parsed.task_prefix,
        )

    run_portal_implementation_daemon_loop(
        daemon,
        context,
        logger=logger,
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
