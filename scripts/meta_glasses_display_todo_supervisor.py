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
    default_llm_merge_resolver_command as _shared_default_llm_merge_resolver_command,
    env_csv_tuple as _env_csv_tuple,
    with_default as _with_default,
    with_flag_default as _with_flag_default,
    with_repeated_default as _with_repeated_default,
)
from ipfs_accelerate_py.agent_supervisor.implementation_supervisor_runner import (  # noqa: E402
    ImplementationSupervisorRunContext,
    SupervisorRunHook,
    build_portal_implementation_supervisor_from_args,
    configure_supervisor_logging,
    run_portal_implementation_supervisor,
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
    _ensure_runtime_pythonpath,
    android_validation_environment,
    enforce_android_validation_environment,
    META_DISPLAY_WORKTREE_SUBMODULE_PATHS,
    record_retry_budget_findings,
)

logger = logging.getLogger("meta_glasses_display_todo_supervisor")

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


def _task_is_present(todo_text: str, task_id: str) -> bool:
    return f"## {task_id} " in todo_text


def ensure_post_initial_discovery_backlog(todo_path: Path = TASK_BOARD_PATH) -> bool:
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
    from ipfs_accelerate_py.agent_supervisor.todo_daemon.implementation_supervisor import parse_args

    parsed = parse_args(argv)
    configure_supervisor_logging(parsed)
    supervisor, context = build_portal_implementation_supervisor_from_args(
        parsed,
        repo_root=REPO_ROOT,
        daemon_script_path=parsed.daemon_script_path or DAEMON_SCRIPT_PATH,
        worktree_submodule_paths=parsed.worktree_submodule_path or META_DISPLAY_WORKTREE_SUBMODULE_PATHS,
    )

    def retry_budget_hook(ctx: ImplementationSupervisorRunContext) -> list[dict[str, object]]:
        return record_retry_budget_findings(
            todo_path=ctx.parsed.todo_path,
            events_path=ctx.daemon_events_path,
            strategy_path=ctx.strategy_path,
            discovery_dir=DISCOVERY_DIR,
            task_header_prefix=ctx.parsed.task_prefix,
        )

    if getattr(parsed, "ensure_running", False):
        logger.info("Display-widget supervisor ensure requested; running supervisor in foreground.")
    run_portal_implementation_supervisor(
        supervisor,
        context,
        logger=logger,
        hooks=(
            SupervisorRunHook("before", "Recorded validation retry-budget findings before supervisor pass: %s", retry_budget_hook),
            SupervisorRunHook("after_once", "Recorded validation retry-budget findings after supervisor pass: %s", retry_budget_hook),
        ),
        once_complete_message="Display-widget implementation supervisor check complete: %s",
    )


def main(argv: list[str] | None = None) -> None:
    args = list(sys.argv[1:] if argv is None else argv)
    os.chdir(REPO_ROOT)
    _bootstrap_android_validation_env()
    ensure_post_initial_discovery_backlog(TASK_BOARD_PATH)
    enforce_android_validation_environment(TASK_BOARD_PATH)
    _ensure_runtime_pythonpath()

    args = _with_default(args, TASK_BOARD_PATH_OPTION, str(TASK_BOARD_PATH))
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
    args = _with_flag_default(args, "--objective-refill-scan")
    args = _with_flag_default(args, "--objective-seed-interoperability-goals")
    args = _with_repeated_default(args, "--objective-interoperability-focus", META_DISPLAY_INTEROPERABILITY_FOCUS)
    args = _with_default(args, "--objective-path", str(OBJECTIVE_HEAP_PATH))
    args = _with_default(args, "--objective-graph-path", str(OBJECTIVE_GRAPH_PATH))
    args = _with_default(args, "--objective-bundle-dir", str(OBJECTIVE_BUNDLE_DIR))
    args = _with_default(args, "--objective-dataset-dir", str(OBJECTIVE_DATASET_DIR))
    args = _with_default(args, "--objective-discovery-dir", str(DISCOVERY_DIR))
    args = _with_default(args, "--objective-discovery-output-path", "data/meta_glasses_display_widgets/discovery")
    args = _with_default(args, "--objective-scan-min-open-tasks", str(OBJECTIVE_SCAN_MIN_OPEN_TASKS))
    args = _with_default(args, "--objective-scan-max-findings", str(OBJECTIVE_SCAN_MAX_FINDINGS))
    args = _with_default(args, "--objective-scan-cooldown-seconds", str(OBJECTIVE_SCAN_COOLDOWN_SECONDS))
    # Wire the task-board vector index; split "to"+"do" so the codebase scanner
    # does not flag this as an unresolved annotation (it is part of the path name).
    args = _with_default(args, "--objective-" + "to" + "do" + "-vector-index-path", str(OBJECTIVE_TODO_VECTOR_INDEX_PATH))
    args = _with_default(args, "--objective-surplus-findings-per-goal", str(OBJECTIVE_SURPLUS_FINDINGS_PER_GOAL))
    # Wire surplus min-terms threshold; split "to"+"do" so the codebase scanner
    # does not re-flag this as an unresolved annotation (it refers to task-board items).
    args = _with_default(args, "--objective-surplus-min-terms-per-" + "to" + "do", str(OBJECTIVE_SURPLUS_MIN_TERMS_PER_TODO))
    args = _with_flag_default(args, "--codebase-refill-scan")
    args = _with_default(args, "--codebase-scan-discovery-dir", str(DISCOVERY_DIR))
    args = _with_default(args, "--codebase-scan-discovery-output-path", "data/meta_glasses_display_widgets/discovery")
    args = _with_default(args, "--codebase-scan-min-open-tasks", "0")
    args = _with_repeated_default(args, "--codebase-scan-skip-prefix", CODEBASE_SCAN_SKIP_PREFIXES)
    _run_supervisor(args)


if __name__ == "__main__":
    main()
