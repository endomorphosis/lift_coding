#!/usr/bin/env python3
"""Run the accelerator todo supervisor for display-widget work."""

from __future__ import annotations

import logging
import os
import shlex
import shutil
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
TODO_PATH = REPO_ROOT / "implementation_plan" / "docs" / "18-swissknife-meta-glasses-display-widgets.todo.md"
STATE_DIR = REPO_ROOT / "data" / "meta_glasses_display_widgets" / "state"
WORKTREE_ROOT = REPO_ROOT / "data" / "meta_glasses_display_widgets" / "worktrees"
DISCOVERY_DIR = REPO_ROOT / "data" / "meta_glasses_display_widgets" / "discovery"
DAEMON_SCRIPT_PATH = REPO_ROOT / "scripts" / "meta_glasses_display_todo_daemon.py"
INITIAL_BACKLOG_TASK_IDS = tuple(f"MGW-{index:03d}" for index in range(1, 13))
INITIAL_BACKLOG_DEPENDENCIES = ", ".join(INITIAL_BACKLOG_TASK_IDS)
CODEBASE_SCAN_SKIP_PREFIXES = (
    "data/meta_glasses_display_widgets/discovery/",
    "data/meta_glasses_display_widgets/state/",
    "data/meta_glasses_display_widgets/worktrees/",
)

SCRIPTS_DIR = Path(__file__).resolve().parent
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

from meta_glasses_display_todo_daemon import (  # noqa: E402
    _bootstrap_android_validation_env,
    _ensure_runtime_pythonpath,
    android_validation_environment,
    enforce_android_validation_environment,
    META_DISPLAY_WORKTREE_SUBMODULE_PATHS,
    record_retry_budget_findings,
)

logger = logging.getLogger("meta_glasses_display_todo_supervisor")

DISCOVERY_EXPANSION_TASK = f"""## MGW-013 Investigate implementation unknowns and expand the backlog

- Status: todo
- Completion: manual
- Priority: P2
- Track: ops
- Depends on: {INITIAL_BACKLOG_DEPENDENCIES}
- Outputs: implementation_plan/docs/18-swissknife-meta-glasses-display-widgets.todo.md, implementation_plan/docs/18-swissknife-meta-glasses-display-widgets.md, data/meta_glasses_display_widgets/discovery
- Validation: PYTHONPATH=external/ipfs_accelerate:external/ipfs_datasets pytest tests/test_meta_glasses_display_todo_queue.py; rg -n "MGW-013|unknown unknowns|Discovery Expansion|discovered" implementation_plan/docs/18-swissknife-meta-glasses-display-widgets.todo.md implementation_plan/docs/18-swissknife-meta-glasses-display-widgets.md
- Acceptance: After the initial backlog completes, investigate the Swissknife, HandsFree backend, mobile DAT bridge, external Meta DAT references, and hardware-free test harness code paths for missed work. Append new daemon-parseable MGW tasks for discovered gaps, or write a dated no-new-unknowns discovery report with evidence and commands run.
"""

SUPERVISOR_GUARDRAIL_TASK = """## MGW-014 Add supervisor validation-environment and retry-budget guardrails

- Status: todo
- Completion: manual
- Priority: P1
- Track: ops
- Depends on: MGW-013
- Outputs: scripts/meta_glasses_display_todo_supervisor.py, scripts/meta_glasses_display_todo_daemon.py, tests/test_meta_glasses_display_todo_queue.py, data/meta_glasses_display_widgets/discovery
- Validation: PYTHONPATH=external/ipfs_accelerate:external/ipfs_datasets pytest tests/test_meta_glasses_display_todo_queue.py; PYTHONPATH=external/ipfs_accelerate:external/ipfs_datasets python3 scripts/meta_glasses_display_todo_supervisor.py --once
- Acceptance: Discovered during MGW-010: Android validation needs the repo-local JDK 17/Android SDK environment, and repeated validation failures should become evidence-backed discovery follow-up items instead of indefinite retry loops. The supervisor documents/enforces the validation environment and records retry-budget findings as daemon-parseable backlog work.
"""


def _with_default(argv: list[str], flag: str, value: str) -> list[str]:
    if flag in argv:
        return argv
    return [flag, value, *argv]


def _with_flag_default(argv: list[str], flag: str) -> list[str]:
    if flag in argv:
        return argv
    return [flag, *argv]


def _with_repeated_default(argv: list[str], flag: str, values: tuple[str, ...]) -> list[str]:
    if flag in argv:
        return argv
    defaults: list[str] = []
    for value in values:
        defaults.extend([flag, value])
    return [*defaults, *argv]


def _default_llm_merge_resolver_command() -> str:
    configured = os.environ.get("HANDSFREE_MGW_LLM_MERGE_RESOLVER_COMMAND", "").strip()
    if configured:
        return configured
    configured = os.environ.get("IPFS_ACCELERATE_AGENT_LLM_MERGE_RESOLVER_COMMAND", "").strip()
    if configured:
        return configured
    codex = shutil.which("codex")
    if not codex:
        return ""
    return f"{shlex.quote(codex)} exec --dangerously-bypass-approvals-and-sandbox -C . -"


def _task_is_present(todo_text: str, task_id: str) -> bool:
    return f"## {task_id} " in todo_text


def ensure_post_initial_discovery_backlog(todo_path: Path = TODO_PATH) -> bool:
    """Keep the post-initial discovery expansion tasks in the supervised board."""
    if not todo_path.exists():
        return False

    todo_text = todo_path.read_text(encoding="utf-8")
    additions: list[str] = []

    if not _task_is_present(todo_text, "MGW-013"):
        additions.append(DISCOVERY_EXPANSION_TASK.strip())
    if not _task_is_present(todo_text, "MGW-014"):
        additions.append(SUPERVISOR_GUARDRAIL_TASK.strip())

    if not additions:
        return False

    updated = todo_text.rstrip() + "\n\n" + "\n\n".join(additions) + "\n"
    todo_path.write_text(updated, encoding="utf-8")
    return True


def validation_environment_summary() -> dict[str, object]:
    """Expose the enforced Android validation environment for tests and operators."""

    return android_validation_environment(REPO_ROOT)


def _run_supervisor(argv: list[str]) -> None:
    from ipfs_accelerate_py.agent_supervisor.todo_daemon.implementation_supervisor import (
        PortalImplementationSupervisor,
        PortalSupervisorConfig,
        ensure_implementation_supervisor_running,
        parse_args,
        repair_implementation_supervisor_runtime,
        split_csv_values,
    )

    parsed = parse_args(argv)
    logging.basicConfig(
        level=getattr(logging, parsed.log_level),
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )
    state_path = parsed.state_dir / f"{parsed.state_prefix}_task_state.json"
    strategy_path = parsed.state_dir / f"{parsed.state_prefix}_strategy.json"
    events_path = parsed.state_dir / f"{parsed.state_prefix}_supervisor_events.jsonl"
    daemon_events_path = parsed.state_dir / f"{parsed.state_prefix}_events.jsonl"
    record_retry_budget_findings(
        todo_path=parsed.todo_path,
        events_path=daemon_events_path,
        strategy_path=strategy_path,
        discovery_dir=DISCOVERY_DIR,
        task_header_prefix=parsed.task_prefix,
    )
    config = PortalSupervisorConfig(
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
        implementation_timeout=parsed.implementation_timeout,
        implementation_log_stall_seconds=parsed.implementation_log_stall_seconds,
        use_ephemeral_worktree=parsed.implement and not parsed.no_ephemeral_worktree,
        worktree_root=parsed.worktree_root,
        worktree_submodule_paths=tuple(parsed.worktree_submodule_path or META_DISPLAY_WORKTREE_SUBMODULE_PATHS),
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
        repo_root=REPO_ROOT,
        daemon_script_path=parsed.daemon_script_path or DAEMON_SCRIPT_PATH,
    )
    if parsed.ensure_running:
        result = ensure_implementation_supervisor_running(
            config,
            argv,
            launcher_path=Path(__file__).resolve(),
            process_fragments=("meta_glasses_display_todo_supervisor.py",),
            startup_wait_seconds=parsed.ensure_startup_wait_seconds,
        )
        logger.info("Display-widget implementation supervisor ensure complete: %s", result)
        return

    repairs = repair_implementation_supervisor_runtime(config)
    if repairs.get("removed") or repairs.get("updated_status"):
        logger.info("Repaired stale display-widget supervisor runtime markers: %s", repairs)

    supervisor = PortalImplementationSupervisor(config)
    if parsed.once:
        result = supervisor.run_once()
        record_retry_budget_findings(
            todo_path=parsed.todo_path,
            events_path=daemon_events_path,
            strategy_path=strategy_path,
            discovery_dir=DISCOVERY_DIR,
            task_header_prefix=parsed.task_prefix,
        )
        logger.info("Display-widget implementation supervisor check complete: %s", result)
        return
    supervisor.run_forever()


def main(argv: list[str] | None = None) -> None:
    args = list(sys.argv[1:] if argv is None else argv)
    os.chdir(REPO_ROOT)
    _bootstrap_android_validation_env()
    ensure_post_initial_discovery_backlog(TODO_PATH)
    enforce_android_validation_environment(TODO_PATH)
    _ensure_runtime_pythonpath()

    args = _with_default(args, "--todo-path", str(TODO_PATH))
    args = _with_default(args, "--state-dir", str(STATE_DIR))
    args = _with_default(args, "--task-prefix", "## MGW-")
    args = _with_default(args, "--state-prefix", "meta_glasses_display")
    args = _with_default(args, "--worktree-root", str(WORKTREE_ROOT))
    args = _with_default(args, "--daemon-script-path", str(DAEMON_SCRIPT_PATH))
    args = _with_default(args, "--supervisor-script-path", str(Path(__file__).resolve()))
    args = _with_default(args, "--max-restarts", "0")
    resolver_command = _default_llm_merge_resolver_command()
    if resolver_command:
        args = _with_default(args, "--llm-merge-resolver-command", resolver_command)
    args = _with_flag_default(args, "--codebase-refill-scan")
    args = _with_default(args, "--codebase-scan-discovery-dir", str(DISCOVERY_DIR))
    args = _with_default(args, "--codebase-scan-discovery-output-path", "data/meta_glasses_display_widgets/discovery")
    args = _with_default(args, "--codebase-scan-min-open-tasks", "0")
    args = _with_repeated_default(args, "--codebase-scan-skip-prefix", CODEBASE_SCAN_SKIP_PREFIXES)
    _run_supervisor(args)


if __name__ == "__main__":
    main()
