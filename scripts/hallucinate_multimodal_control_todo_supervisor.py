#!/usr/bin/env python3
"""Run the accelerator task supervisor for Hallucinate multimodal-control work."""

from __future__ import annotations

import logging
import os
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
IPFS_ACCELERATE_ROOT = REPO_ROOT / "external" / "ipfs_accelerate"
SCRIPTS_DIR = Path(__file__).resolve().parent
if str(IPFS_ACCELERATE_ROOT) not in sys.path:
    sys.path.insert(0, str(IPFS_ACCELERATE_ROOT))
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

from ipfs_accelerate_py.agent_supervisor.wrapper_utils import (  # noqa: E402
    default_llm_merge_resolver_command as _shared_default_llm_merge_resolver_command,
    with_default as _with_default,
    with_flag_default as _with_flag_default,
    with_repeated_default as _with_repeated_default,
)
from ipfs_accelerate_py.agent_supervisor.todo_daemon.supervisor_runtime import (  # noqa: E402
    ensure_supervisor_running as _ensure_supervisor_running,
    pop_bool_flag as _pop_bool_flag,
    repair_supervisor_runtime as _repair_supervisor_runtime,
    supervisor_is_running as _supervisor_is_running,
)
from hallucinate_multimodal_control_todo_daemon import (  # noqa: E402
    CODEBASE_SCAN_COOLDOWN_SECONDS,
    CODEBASE_SCAN_MAX_FINDINGS,
    CODEBASE_SCAN_MIN_OPEN_TASKS,
    CODEBASE_SCAN_SKIP_PREFIXES,
    DISCOVERY_DIR,
    HALLUCINATE_WORKTREE_SUBMODULE_PATHS,
    OBJECTIVE_BUNDLE_DIR,
    OBJECTIVE_DATASET_DIR,
    OBJECTIVE_SCAN_COOLDOWN_SECONDS,
    OBJECTIVE_SCAN_MAX_FINDINGS,
    OBJECTIVE_SCAN_MIN_OPEN_TASKS,
    OBJECTIVE_SURPLUS_FINDINGS_PER_GOAL,
    OBJECTIVE_SURPLUS_MIN_TERMS_PER_TODO,
    OBJECTIVE_TODO_VECTOR_INDEX_PATH,
    HALLUCINATE_INTEROPERABILITY_FOCUS,
    TASK_BOARD_PATH_KEY,
    TASK_BOARD_PATH_OPTION,
    _ensure_runtime_pythonpath,
    ensure_hallucinate_multimodal_bootstrap_paths,
    record_codebase_scan_findings,
    record_objective_goal_findings,
    record_retry_budget_findings,
)


logger = logging.getLogger("hallucinate_multimodal_control_todo_supervisor")
DAEMON_SCRIPT_PATH = REPO_ROOT / "scripts" / "hallucinate_multimodal_control_todo_daemon.py"
OBJECTIVE_GRAPH_PATH = REPO_ROOT / "data" / "hallucinate_multimodal_control" / "objective_graph.json"
HALLUCINATE_SUPERVISOR_PROCESS_MARKERS = (
    "hallucinate_multimodal_control_todo_supervisor.py",
    "hallucinate_multimodal_control_autopilot.py",
)


def _default_llm_merge_resolver_command() -> str:
    return _shared_default_llm_merge_resolver_command(
        primary_env_var="HANDSFREE_HAO_LLM_MERGE_RESOLVER_COMMAND"
    )


def repair_hallucinate_supervisor_runtime(state_dir: Path, state_prefix: str) -> dict[str, object]:
    """Clear stale Hallucinate supervisor/daemon markers before health checks."""

    return _repair_supervisor_runtime(state_dir, state_prefix)


def hallucinate_supervisor_is_running(state_dir: Path, state_prefix: str) -> bool:
    return _supervisor_is_running(
        state_dir,
        state_prefix,
        process_match_any=HALLUCINATE_SUPERVISOR_PROCESS_MARKERS,
    )


def ensure_hallucinate_supervisor_running(argv: list[str], *, state_dir: Path, state_prefix: str) -> dict[str, object]:
    return _ensure_supervisor_running(
        argv,
        state_dir=state_dir,
        state_prefix=state_prefix,
        repo_root=REPO_ROOT,
        script_path=Path(__file__).resolve(),
        process_match_any=HALLUCINATE_SUPERVISOR_PROCESS_MARKERS,
        prepare_environment=_ensure_runtime_pythonpath,
    )


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
    args = _with_flag_default(args, "--objective-seed-interoperability-goals")
    args = _with_repeated_default(args, "--objective-interoperability-focus", HALLUCINATE_INTEROPERABILITY_FOCUS)
    args = _with_default(args, "--objective-path", str(paths["objective_goal_heap_path"]))
    args = _with_default(args, "--objective-graph-path", str(OBJECTIVE_GRAPH_PATH))
    args = _with_default(args, "--objective-bundle-dir", str(OBJECTIVE_BUNDLE_DIR))
    args = _with_default(args, "--objective-dataset-dir", str(OBJECTIVE_DATASET_DIR))
    args = _with_default(args, "--objective-discovery-dir", str(DISCOVERY_DIR))
    args = _with_default(args, "--objective-discovery-output-path", DISCOVERY_DIR.relative_to(REPO_ROOT).as_posix())
    args = _with_default(args, "--objective-scan-min-open-tasks", str(OBJECTIVE_SCAN_MIN_OPEN_TASKS))
    args = _with_default(args, "--objective-scan-max-findings", str(OBJECTIVE_SCAN_MAX_FINDINGS))
    args = _with_default(args, "--objective-scan-cooldown-seconds", str(OBJECTIVE_SCAN_COOLDOWN_SECONDS))
    # scanner-resolved: MGW-189, MGW-190, HAO-247, VAI-165, HAO-253, VAI-169, HAO-257, HAO-262, VAI-174 — "todo" below is part of the CLI flag name --objective-todo-vector-index-path (work-item queue path), not a deferred-work annotation.
    args = _with_default(args, "--objective-todo-vector-index-path", str(OBJECTIVE_TODO_VECTOR_INDEX_PATH))
    args = _with_default(args, "--objective-surplus-findings-per-goal", str(OBJECTIVE_SURPLUS_FINDINGS_PER_GOAL))
    # scanner-resolved: MGW-191, MGW-192, HAO-244, HAO-248, HAO-249, VAI-166, HAO-254, VAI-170, HAO-258, HAO-263, VAI-175, VAI-178, MGW-206 — "todo" in --objective-surplus-min-terms-per-todo refers to backlog task entries (CLI flag name, not a deferred-work annotation).
    args = _with_default(args, "--objective-surplus-min-terms-per-todo", str(OBJECTIVE_SURPLUS_MIN_TERMS_PER_TODO))
    args = _with_flag_default(args, "--codebase-refill-scan")
    args = _with_default(args, "--codebase-scan-discovery-dir", str(DISCOVERY_DIR))
    args = _with_default(args, "--codebase-scan-discovery-output-path", DISCOVERY_DIR.relative_to(REPO_ROOT).as_posix())
    args = _with_default(args, "--codebase-scan-min-open-tasks", str(CODEBASE_SCAN_MIN_OPEN_TASKS))
    args = _with_default(args, "--codebase-scan-max-findings", str(CODEBASE_SCAN_MAX_FINDINGS))
    args = _with_default(args, "--codebase-scan-cooldown-seconds", str(CODEBASE_SCAN_COOLDOWN_SECONDS))
    args = _with_repeated_default(args, "--codebase-scan-skip-prefix", CODEBASE_SCAN_SKIP_PREFIXES)

    from ipfs_accelerate_py.agent_supervisor.todo_daemon.implementation_supervisor import (
        PortalImplementationSupervisor,
        parse_args,
        supervisor_config_from_args,
    )

    parsed = parse_args(args)
    logging.basicConfig(
        level=getattr(logging, parsed.log_level),
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )
    config = supervisor_config_from_args(
        parsed,
        repo_root=REPO_ROOT,
        daemon_script_path=parsed.daemon_script_path or DAEMON_SCRIPT_PATH,
        worktree_submodule_paths=parsed.worktree_submodule_path or HALLUCINATE_WORKTREE_SUBMODULE_PATHS,
    )
    state_path = config.state_path
    strategy_path = config.strategy_path
    events_path = config.events_path
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

    supervisor = PortalImplementationSupervisor(config)
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
