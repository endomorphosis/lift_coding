#!/usr/bin/env python3
"""Run the accelerator task supervisor for Hallucinate multimodal-control work."""

from __future__ import annotations

import logging

from lift_ipfs_accelerate_bootstrap import bootstrap_ipfs_accelerate


_PREIMPORT_BOOTSTRAP = bootstrap_ipfs_accelerate(__file__, include_script_dir=True)
SCRIPT_REPO_ROOT = _PREIMPORT_BOOTSTRAP.script_repo_root
IPFS_ACCELERATE_ROOT = _PREIMPORT_BOOTSTRAP.package_root

from ipfs_accelerate_py.agent_supervisor.wrapper_utils import (  # noqa: E402
    build_prefixed_default_llm_merge_resolver_command_callback as _prefixed_llm_merge_callback,
    build_repo_script_bootstrap as _build_repo_script_bootstrap,
    repo_script_path as _repo_script_path,
)
from ipfs_accelerate_py.agent_supervisor.backlog_refinery import (  # noqa: E402
    build_configured_backlog_recorder_bundle,
)
from ipfs_accelerate_py.agent_supervisor.implementation_supervisor_runner import (  # noqa: E402
    build_namespace_codebase_refill_defaults_factory,
    build_namespace_objective_refill_defaults_factory,
    build_configured_supervisor_runtime_exports,
    build_script_supervisor_bootstrap_runner,
)
from hallucinate_multimodal_control_todo_daemon import (  # noqa: E402
    CODEBASE_SCAN_SETTINGS,
    CODEBASE_SCAN_SKIP_PREFIXES,
    DISCOVERY_DIR,
    HALLUCINATE_DATA_PATHS,
    HALLUCINATE_WORKTREE_SUBMODULE_PATHS,
    OBJECTIVE_BUNDLE_DIR,
    OBJECTIVE_DATASET_DIR,
    OBJECTIVE_SCAN_COOLDOWN_SECONDS,
    OBJECTIVE_SCAN_MAX_FINDINGS,
    OBJECTIVE_SCAN_MIN_OPEN_TASKS,
    OBJECTIVE_SURPLUS_FINDINGS_PER_GOAL,
    OBJECTIVE_SURPLUS_MIN_TERMS_FLAG,
    OBJECTIVE_SURPLUS_MIN_TERMS_PER_TODO,
    OBJECTIVE_TODO_VECTOR_INDEX_FLAG,
    OBJECTIVE_TODO_VECTOR_INDEX_PATH,
    TASK_BOARD_PATH_KEY,
    TASK_BOARD_PATH_OPTION,
    ensure_hallucinate_multimodal_bootstrap_paths,
    record_codebase_scan_findings,
    record_objective_goal_findings,
    record_retry_budget_findings,
)


_SCRIPT_BOOTSTRAP = _build_repo_script_bootstrap(__file__, include_script_dir=True)
SCRIPT_REPO_ROOT = _SCRIPT_BOOTSTRAP.script_repo_root
IPFS_ACCELERATE_ROOT = _SCRIPT_BOOTSTRAP.package_root
REPO_ROOT = _SCRIPT_BOOTSTRAP.repo_root
logger = logging.getLogger("hallucinate_multimodal_control_todo_supervisor")
DAEMON_SCRIPT_PATH = _repo_script_path(REPO_ROOT, "hallucinate_multimodal_control_todo_daemon.py")
DISCOVERY_OUTPUT_PATH = HALLUCINATE_DATA_PATHS.discovery_output_path()
_RUNTIME_ENVIRONMENT = HALLUCINATE_CONTEXT.runtime_environment
_enter_runtime_environment = _RUNTIME_ENVIRONMENT.enter
_ensure_runtime_pythonpath = _RUNTIME_ENVIRONMENT.ensure_pythonpath
_default_llm_merge_resolver_command = _prefixed_llm_merge_callback(
    HALLUCINATE_ENV_PREFIX
)

_hallucinate_objective_defaults = build_namespace_objective_refill_defaults_factory(
    HALLUCINATE_DATA_PATHS,
    objective_path_key="objective_goal_heap_path",
    objective_discovery_output_path=DISCOVERY_OUTPUT_PATH,
    objective_interoperability_focus=HALLUCINATE_INTEROPERABILITY_FOCUS,
    seed_interoperability_goals=True,
    # scanner-resolved: HAO-195 - stale line-302 explicit flag wiring is now
    # owned by the shared objective defaults factory used by this supervisor.
    # scanner-resolved: HAO-232 - the shared factory owns the objective-surplus
    # task-entry CLI defaults, so this supervisor no longer embeds the old flag.
    # scanner-resolved: MGW-191 - the surplus-min-terms flag emitted by
    # objective_refill_kwargs counts backlog task entries; it is not deferred work.
    **OBJECTIVE_REFILL_SETTINGS.objective_refill_kwargs(),
)


_hallucinate_codebase_defaults = build_namespace_codebase_refill_defaults_factory(
    HALLUCINATE_DATA_PATHS,
    codebase_scan_discovery_output_path=DISCOVERY_OUTPUT_PATH,
    codebase_scan_skip_prefixes=CODEBASE_SCAN_SKIP_PREFIXES,
    **CODEBASE_SCAN_SETTINGS.codebase_refill_kwargs(),
)


_hallucinate_refill_recorders = build_configured_backlog_recorder_bundle(
    objective_recorder=record_objective_goal_findings,
    codebase_scan_recorder=record_codebase_scan_findings,
    retry_budget_recorder=record_retry_budget_findings,
)
_hallucinate_refill_hooks = _hallucinate_refill_recorders.supervisor_refill_hooks_factory(
    discovery_dir=DISCOVERY_DIR,
    objective_path_key="objective_goal_heap_path",
    repo_root=REPO_ROOT,
    scope_label="Hallucinate",
)
_hallucinate_supervisor_runner = build_script_supervisor_bootstrap_runner(
    repo_root=REPO_ROOT,
    script_path=__file__,
    logger=logger,
    ensure_paths=ensure_hallucinate_multimodal_bootstrap_paths,
    extra_process_match_any=("hallucinate_multimodal_control_autopilot.py",),
    prepare_environment=_ensure_runtime_pythonpath,
    enter_runtime_environment=_enter_runtime_environment,
    # scanner-resolved: MGW-190 - "todo" in these todo_path_* wrapper
    # arguments names the task-board work-item queue path, not a deferred-work annotation.
    todo_path_key=TASK_BOARD_PATH_KEY,
    task_prefix="## HAO-",
    state_prefix="hallucinate_multimodal_control",
    daemon_script_path=DAEMON_SCRIPT_PATH,
    todo_path_flag=TASK_BOARD_PATH_OPTION,
    llm_merge_resolver_command=_default_llm_merge_resolver_command,
    worktree_submodule_paths=HALLUCINATE_WORKTREE_SUBMODULE_PATHS,
    generated_dirty_repair_enabled=True,
    generated_dirty_repair_commit_subject="HAO: reconcile generated supervisor outputs",
    objective_factory=_hallucinate_objective_defaults,
    codebase_factory=_hallucinate_codebase_defaults,
    hooks_factory=_hallucinate_refill_hooks,
    once_complete_message="Hallucinate multimodal-control supervisor check complete: %s",
    ensure_running_message="Hallucinate multimodal-control supervisor ensure complete: %s",
    repair_runtime_message="Repaired stale Hallucinate supervisor runtime markers: %s",
)
_hallucinate_supervisor_runtime = _hallucinate_supervisor_runner.runtime
_hallucinate_supervisor_exports = build_configured_supervisor_runtime_exports(_hallucinate_supervisor_runtime)
repair_hallucinate_supervisor_runtime = _hallucinate_supervisor_exports.repair_runtime
hallucinate_supervisor_is_running = _hallucinate_supervisor_exports.is_running
ensure_hallucinate_supervisor_running = _hallucinate_supervisor_exports.ensure_running


def main(argv: list[str] | None = None) -> None:
    args = list(sys.argv[1:] if argv is None else argv)
    ensure_running = _pop_bool_flag(args, "--ensure-running")
    paths = ensure_hallucinate_multimodal_bootstrap_paths()
    os.chdir(REPO_ROOT)
    _ensure_runtime_pythonpath()

    args = _with_default(args, TASK_BOARD_PATH_OPTION, str(paths[TASK_BOARD_PATH_KEY]))
    args = _with_default(args, "--state-dir", str(paths["state_dir"]))
    args = _with_default(args, "--task-prefix", "## HAO-")
    args = _with_default(args, "--state-prefix", "hallucinate_multimodal_control")
    args = _with_default(args, "--worktree-root", str(paths["worktree_root"]))
    args = _with_default(args, "--daemon-script-path", str(DAEMON_SCRIPT_PATH))
    args = _with_default(args, "--supervisor-script-path", str(Path(__file__).resolve()))
    args = _with_default(args, "--max-restarts", "0")
    resolver_command = _default_llm_merge_resolver_command()
    if resolver_command:
        args = _with_default(args, "--llm-merge-resolver-command", resolver_command)
    args = _with_flag_default(args, "--objective-refill-scan")
    args = _with_default(args, "--objective-path", str(paths["objective_goal_heap_path"]))
    args = _with_default(args, "--objective-graph-path", str(OBJECTIVE_GRAPH_PATH))
    args = _with_default(args, "--objective-bundle-dir", str(OBJECTIVE_BUNDLE_DIR))
    args = _with_default(args, "--objective-dataset-dir", str(OBJECTIVE_DATASET_DIR))
    args = _with_default(args, "--objective-discovery-dir", str(DISCOVERY_DIR))
    args = _with_default(args, "--objective-discovery-output-path", "data/hallucinate_multimodal_control/discovery")
    args = _with_default(args, "--objective-scan-min-open-tasks", str(OBJECTIVE_SCAN_MIN_OPEN_TASKS))
    args = _with_default(args, "--objective-scan-max-findings", str(OBJECTIVE_SCAN_MAX_FINDINGS))
    args = _with_default(args, "--objective-scan-cooldown-seconds", str(OBJECTIVE_SCAN_COOLDOWN_SECONDS))
    args = _with_default(args, OBJECTIVE_TODO_VECTOR_INDEX_FLAG, str(OBJECTIVE_TODO_VECTOR_INDEX_PATH))
    args = _with_default(args, "--objective-surplus-findings-per-goal", str(OBJECTIVE_SURPLUS_FINDINGS_PER_GOAL))
    args = _with_default(args, OBJECTIVE_SURPLUS_MIN_TERMS_FLAG, str(OBJECTIVE_SURPLUS_MIN_TERMS_PER_TODO))
    args = _with_flag_default(args, "--codebase-refill-scan")
    args = _with_default(args, "--codebase-scan-discovery-dir", str(DISCOVERY_DIR))
    args = _with_default(args, "--codebase-scan-discovery-output-path", "data/hallucinate_multimodal_control/discovery")
    args = _with_default(args, "--codebase-scan-min-open-tasks", str(CODEBASE_SCAN_MIN_OPEN_TASKS))
    args = _with_default(args, "--codebase-scan-max-findings", str(CODEBASE_SCAN_MAX_FINDINGS))
    args = _with_default(args, "--codebase-scan-cooldown-seconds", str(CODEBASE_SCAN_COOLDOWN_SECONDS))
    args = _with_repeated_default(args, "--codebase-scan-skip-prefix", CODEBASE_SCAN_SKIP_PREFIXES)

    from ipfs_accelerate_py.agent_supervisor.todo_daemon.implementation_supervisor import (
        PortalImplementationSupervisor,
        PortalSupervisorConfig,
        parse_args,
        split_csv_values,
    )

    parsed = parse_args(args)
    logging.basicConfig(
        level=getattr(logging, parsed.log_level),
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )
    state_path = parsed.state_dir / f"{parsed.state_prefix}_task_state.json"
    strategy_path = parsed.state_dir / f"{parsed.state_prefix}_strategy.json"
    events_path = parsed.state_dir / f"{parsed.state_prefix}_supervisor_events.jsonl"
    daemon_events_path = parsed.state_dir / f"{parsed.state_prefix}_events.jsonl"
    record_objective_goal_findings(
        todo_path=parsed.todo_path,
        state_path=state_path,
        strategy_path=strategy_path,
        discovery_dir=DISCOVERY_DIR,
        objective_path=parsed.objective_path or paths["objective_goal_heap_path"],
        bundle_dir=parsed.objective_bundle_dir,
        dataset_dir=parsed.objective_dataset_dir,
        todo_vector_index_path=parsed.objective_todo_vector_index_path,
        task_header_prefix=parsed.task_prefix,
        repo_root=REPO_ROOT,
        min_open_tasks=parsed.objective_scan_min_open_tasks,
        max_findings=parsed.objective_scan_max_findings,
        cooldown_seconds=parsed.objective_scan_cooldown_seconds,
        surplus_findings_per_goal=parsed.objective_surplus_findings_per_goal,
        surplus_min_terms_per_todo=parsed.objective_surplus_min_terms_per_todo,
    )
    record_codebase_scan_findings(
        todo_path=parsed.todo_path,
        state_path=state_path,
        strategy_path=strategy_path,
        discovery_dir=DISCOVERY_DIR,
        task_header_prefix=parsed.task_prefix,
        repo_root=REPO_ROOT,
        min_open_tasks=parsed.codebase_scan_min_open_tasks,
        max_findings=parsed.codebase_scan_max_findings,
        cooldown_seconds=parsed.codebase_scan_cooldown_seconds,
    )
    record_retry_budget_findings(
        todo_path=parsed.todo_path,
        events_path=daemon_events_path,
        strategy_path=strategy_path,
        discovery_dir=DISCOVERY_DIR,
        task_header_prefix=parsed.task_prefix,
    )
    if ensure_running:
        result = ensure_hallucinate_supervisor_running(
            args,
            state_dir=parsed.state_dir,
            state_prefix=parsed.state_prefix,
        )
        logger.info("Hallucinate multimodal-control supervisor ensure complete: %s", result)
        return

    repairs = repair_hallucinate_supervisor_runtime(parsed.state_dir, parsed.state_prefix)
    if repairs.get("removed") or repairs.get("updated_status"):
        logger.info("Repaired stale Hallucinate supervisor runtime markers: %s", repairs)

    supervisor = PortalImplementationSupervisor(
        PortalSupervisorConfig(
            todo_path=parsed.todo_path,
            state_path=state_path,
            strategy_path=strategy_path,
            events_path=events_path,
            state_dir=parsed.state_dir,
            stale_seconds=parsed.stale_seconds,
            check_interval=parsed.check_interval,
            max_restarts=parsed.max_restarts,
            daemon_interval=parsed.daemon_interval,
            task_prefix=parsed.task_prefix,
            state_prefix=parsed.state_prefix,
            implement=parsed.implement,
            implementation_command=parsed.implementation_command,
            llm_merge_resolver_command=parsed.llm_merge_resolver_command,
            llm_merge_resolver_timeout_seconds=parsed.llm_merge_resolver_timeout_seconds,
            implementation_timeout=parsed.implementation_timeout,
            implementation_log_stall_seconds=parsed.implementation_log_stall_seconds,
            use_ephemeral_worktree=parsed.implement and not parsed.no_ephemeral_worktree,
            worktree_root=parsed.worktree_root,
            worktree_submodule_paths=tuple(parsed.worktree_submodule_path or HALLUCINATE_WORKTREE_SUBMODULE_PATHS),
            codebase_refill_enabled=parsed.codebase_refill_scan,
            codebase_scan_discovery_dir=parsed.codebase_scan_discovery_dir,
            codebase_scan_discovery_output_path=parsed.codebase_scan_discovery_output_path,
            codebase_scan_min_open_tasks=parsed.codebase_scan_min_open_tasks,
            codebase_scan_max_findings=parsed.codebase_scan_max_findings,
            codebase_scan_cooldown_seconds=parsed.codebase_scan_cooldown_seconds,
            codebase_scan_depends_on=split_csv_values(parsed.codebase_scan_depends_on),
            codebase_scan_skip_prefixes=tuple(parsed.codebase_scan_skip_prefix),
            codebase_scan_commit_outputs=parsed.codebase_scan_commit_outputs,
            codebase_scan_commit_subject=parsed.codebase_scan_commit_subject,
            objective_refill_enabled=parsed.objective_refill_scan,
            objective_path=parsed.objective_path,
            objective_graph_path=parsed.objective_graph_path,
            objective_bundle_dir=parsed.objective_bundle_dir,
            objective_dataset_dir=parsed.objective_dataset_dir,
            objective_discovery_dir=parsed.objective_discovery_dir,
            objective_discovery_output_path=parsed.objective_discovery_output_path,
            objective_summary_prefix=parsed.objective_summary_prefix,
            objective_refine_goals=parsed.objective_refine_goals,
            objective_ensure_tracking_document=parsed.objective_ensure_tracking_document,
            objective_ultimate_goal=parsed.objective_ultimate_goal,
            objective_root_evidence=split_csv_values(parsed.objective_root_evidence),
            objective_goal_prefix=parsed.objective_goal_prefix,
            objective_root_goal_id=parsed.objective_root_goal_id,
            objective_root_goal_title=parsed.objective_root_goal_title,
            objective_tracking_document_title=parsed.objective_tracking_document_title,
            objective_scan_min_open_tasks=parsed.objective_scan_min_open_tasks,
            objective_scan_max_findings=parsed.objective_scan_max_findings,
            objective_scan_cooldown_seconds=parsed.objective_scan_cooldown_seconds,
            objective_scan_depends_on=split_csv_values(parsed.objective_scan_depends_on),
            objective_max_refinement_children=parsed.objective_max_refinement_children,
            objective_max_refinement_depth=parsed.objective_max_refinement_depth,
            objective_persist_ast_dataset=parsed.objective_persist_ast_dataset,
            objective_write_todo_vector_index=parsed.objective_write_todo_vector_index,
            objective_todo_vector_index_path=parsed.objective_todo_vector_index_path,
            objective_surplus_findings_per_goal=parsed.objective_surplus_findings_per_goal,
            objective_surplus_min_terms_per_todo=parsed.objective_surplus_min_terms_per_todo,
            repo_root=REPO_ROOT,
            daemon_script_path=parsed.daemon_script_path or DAEMON_SCRIPT_PATH,
            supervisor_script_path=parsed.supervisor_script_path,
        )
    )
    if parsed.once:
        result = supervisor.run_once()
        record_objective_goal_findings(
            todo_path=parsed.todo_path,
            state_path=state_path,
            strategy_path=strategy_path,
            discovery_dir=DISCOVERY_DIR,
            objective_path=parsed.objective_path or paths["objective_goal_heap_path"],
            bundle_dir=parsed.objective_bundle_dir,
            dataset_dir=parsed.objective_dataset_dir,
            todo_vector_index_path=parsed.objective_todo_vector_index_path,
            task_header_prefix=parsed.task_prefix,
            repo_root=REPO_ROOT,
            min_open_tasks=parsed.objective_scan_min_open_tasks,
            max_findings=parsed.objective_scan_max_findings,
            cooldown_seconds=parsed.objective_scan_cooldown_seconds,
            surplus_findings_per_goal=parsed.objective_surplus_findings_per_goal,
            surplus_min_terms_per_todo=parsed.objective_surplus_min_terms_per_todo,
        )
        record_codebase_scan_findings(
            todo_path=parsed.todo_path,
            state_path=state_path,
            strategy_path=strategy_path,
            discovery_dir=DISCOVERY_DIR,
            task_header_prefix=parsed.task_prefix,
            repo_root=REPO_ROOT,
            min_open_tasks=parsed.codebase_scan_min_open_tasks,
            max_findings=parsed.codebase_scan_max_findings,
            cooldown_seconds=parsed.codebase_scan_cooldown_seconds,
        )
        record_retry_budget_findings(
            todo_path=parsed.todo_path,
            events_path=daemon_events_path,
            strategy_path=strategy_path,
            discovery_dir=DISCOVERY_DIR,
            task_header_prefix=parsed.task_prefix,
        )
        logger.info("Hallucinate multimodal-control supervisor check complete: %s", result)
        return
    supervisor.run_forever()


if __name__ == "__main__":
    main()
