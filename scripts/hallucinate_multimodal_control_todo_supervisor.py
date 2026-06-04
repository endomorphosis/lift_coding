#!/usr/bin/env python3
"""Run the accelerator task supervisor for Hallucinate multimodal-control work."""

from __future__ import annotations

import logging
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
IPFS_ACCELERATE_ROOT = REPO_ROOT / "external" / "ipfs_accelerate"
IPFS_DATASETS_ROOT = REPO_ROOT / "external" / "ipfs_datasets"
SCRIPTS_DIR = Path(__file__).resolve().parent
if str(IPFS_ACCELERATE_ROOT) not in sys.path:
    sys.path.insert(0, str(IPFS_ACCELERATE_ROOT))
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

from ipfs_accelerate_py.agent_supervisor.wrapper_utils import (  # noqa: E402
    build_prefixed_default_llm_merge_resolver_command_callback as _prefixed_llm_merge_callback,
    build_runtime_environment_callbacks as _build_runtime_environment_callbacks,
    repo_relative_or_default as _repo_relative_or_default,
)
from ipfs_accelerate_py.agent_supervisor.implementation_supervisor_runner import (  # noqa: E402
    apply_portal_implementation_supervisor_defaults_from_paths,
    build_codebase_refill_defaults_from_paths,
    build_objective_refill_defaults_from_paths,
    build_supervisor_codebase_scan_refill_callback,
    build_supervisor_objective_refill_callback,
    build_supervisor_refill_hooks,
    build_supervisor_retry_budget_refill_callback,
    build_supervisor_runtime_callbacks,
    run_configured_portal_implementation_supervisor,
)
from ipfs_accelerate_py.agent_supervisor.todo_daemon.supervisor_runtime import (  # noqa: E402
    build_supervisor_runtime_operations,
    pop_bool_flag as _pop_bool_flag,
)
from hallucinate_multimodal_control_todo_daemon import (  # noqa: E402
    CODEBASE_SCAN_SETTINGS,
    CODEBASE_SCAN_SKIP_PREFIXES,
    DISCOVERY_DIR,
    HALLUCINATE_WORKTREE_SUBMODULE_PATHS,
    OBJECTIVE_BUNDLE_DIR,
    OBJECTIVE_DATASET_DIR,
    OBJECTIVE_REFILL_SETTINGS,
    OBJECTIVE_TODO_VECTOR_INDEX_PATH,
    HALLUCINATE_INTEROPERABILITY_FOCUS,
    HALLUCINATE_ENV_PREFIX,
    TASK_BOARD_PATH_KEY,
    TASK_BOARD_PATH_OPTION,
    ensure_hallucinate_multimodal_bootstrap_paths,
    record_codebase_scan_findings,
    record_objective_goal_findings,
    record_retry_budget_findings,
)


logger = logging.getLogger("hallucinate_multimodal_control_todo_supervisor")
DAEMON_SCRIPT_PATH = REPO_ROOT / "scripts" / "hallucinate_multimodal_control_todo_daemon.py"
OBJECTIVE_GRAPH_PATH = REPO_ROOT / "data" / "hallucinate_multimodal_control" / "objective_graph.json"
DISCOVERY_OUTPUT_PATH = _repo_relative_or_default(
    DISCOVERY_DIR,
    REPO_ROOT,
    "data/hallucinate_multimodal_control/discovery",
)
HALLUCINATE_SUPERVISOR_PROCESS_MARKERS = (
    "hallucinate_multimodal_control_todo_supervisor.py",
    "hallucinate_multimodal_control_autopilot.py",
)
_RUNTIME_ENVIRONMENT = _build_runtime_environment_callbacks(
    REPO_ROOT,
    (IPFS_ACCELERATE_ROOT, IPFS_DATASETS_ROOT),
)
_enter_runtime_environment = _RUNTIME_ENVIRONMENT.enter
_ensure_runtime_pythonpath = _RUNTIME_ENVIRONMENT.ensure_pythonpath
_default_llm_merge_resolver_command = _prefixed_llm_merge_callback(
    HALLUCINATE_ENV_PREFIX
)
_hallucinate_supervisor_runtime = build_supervisor_runtime_operations(
    repo_root=REPO_ROOT,
    script_path=Path(__file__).resolve(),
    process_match_any=HALLUCINATE_SUPERVISOR_PROCESS_MARKERS,
    prepare_environment=_ensure_runtime_pythonpath,
)


def repair_hallucinate_supervisor_runtime(state_dir: Path, state_prefix: str) -> dict[str, object]:
    """Clear stale Hallucinate supervisor/daemon markers before health checks."""

    return _hallucinate_supervisor_runtime.repair_runtime(state_dir, state_prefix)


def hallucinate_supervisor_is_running(state_dir: Path, state_prefix: str) -> bool:
    return _hallucinate_supervisor_runtime.is_running(state_dir, state_prefix)


def ensure_hallucinate_supervisor_running(argv: list[str], *, state_dir: Path, state_prefix: str) -> dict[str, object]:
    return _hallucinate_supervisor_runtime.ensure_running(
        argv,
        state_dir=state_dir,
        state_prefix=state_prefix,
    )


def main(argv: list[str] | None = None) -> None:
    args = list(sys.argv[1:] if argv is None else argv)
    ensure_running = _pop_bool_flag(args, "--ensure-running")
    paths = ensure_hallucinate_multimodal_bootstrap_paths()
    _enter_runtime_environment()

    args = apply_portal_implementation_supervisor_defaults_from_paths(
        args,
        paths,
        todo_path_key=TASK_BOARD_PATH_KEY,
        task_prefix="## HAO-",
        state_prefix="hallucinate_multimodal_control",
        daemon_script_path=DAEMON_SCRIPT_PATH,
        supervisor_script_path=Path(__file__).resolve(),
        todo_path_flag=TASK_BOARD_PATH_OPTION,
        llm_merge_resolver_command=_default_llm_merge_resolver_command(),
        objective=build_objective_refill_defaults_from_paths(
            paths,
            objective_path_key="objective_goal_heap_path",
            objective_graph_path=OBJECTIVE_GRAPH_PATH,
            objective_bundle_dir=OBJECTIVE_BUNDLE_DIR,
            objective_dataset_dir=OBJECTIVE_DATASET_DIR,
            objective_discovery_dir=DISCOVERY_DIR,
            objective_discovery_output_path=DISCOVERY_OUTPUT_PATH,
            objective_todo_vector_index_path=OBJECTIVE_TODO_VECTOR_INDEX_PATH,
            objective_interoperability_focus=HALLUCINATE_INTEROPERABILITY_FOCUS,
            seed_interoperability_goals=True,
            **OBJECTIVE_REFILL_SETTINGS.objective_refill_kwargs(),
        ),
        codebase=build_codebase_refill_defaults_from_paths(
            paths,
            codebase_scan_discovery_dir=DISCOVERY_DIR,
            codebase_scan_discovery_output_path=DISCOVERY_OUTPUT_PATH,
            codebase_scan_skip_prefixes=CODEBASE_SCAN_SKIP_PREFIXES,
            **CODEBASE_SCAN_SETTINGS.codebase_refill_kwargs(),
        ),
    )

    objective_hook = build_supervisor_objective_refill_callback(
        record_objective_goal_findings,
        discovery_dir=DISCOVERY_DIR,
        objective_path=paths["objective_goal_heap_path"],
        repo_root=REPO_ROOT,
    )
    codebase_scan_hook = build_supervisor_codebase_scan_refill_callback(
        record_codebase_scan_findings,
        discovery_dir=DISCOVERY_DIR,
        repo_root=REPO_ROOT,
    )
    retry_budget_hook = build_supervisor_retry_budget_refill_callback(
        record_retry_budget_findings,
        discovery_dir=DISCOVERY_DIR,
    )

    runtime_callbacks = build_supervisor_runtime_callbacks(
        args,
        repo_root=REPO_ROOT,
        script_path=Path(__file__).resolve(),
        process_match_any=HALLUCINATE_SUPERVISOR_PROCESS_MARKERS,
        prepare_environment=_ensure_runtime_pythonpath,
    )

    run_configured_portal_implementation_supervisor(
        args,
        repo_root=REPO_ROOT,
        logger=logger,
        daemon_script_path=DAEMON_SCRIPT_PATH,
        worktree_submodule_paths=HALLUCINATE_WORKTREE_SUBMODULE_PATHS,
        hooks=build_supervisor_refill_hooks(
            (
                ("objective-goal", objective_hook),
                ("codebase-scan", codebase_scan_hook),
                ("retry-budget", retry_budget_hook),
            ),
            scope_label="Hallucinate",
        ),
        once_complete_message="Hallucinate multimodal-control supervisor check complete: %s",
        ensure_running=ensure_running,
        ensure_running_callback=runtime_callbacks.ensure_running,
        ensure_running_message="Hallucinate multimodal-control supervisor ensure complete: %s",
        repair_runtime_callback=runtime_callbacks.repair_runtime,
        repair_runtime_message="Repaired stale Hallucinate supervisor runtime markers: %s",
    )


if __name__ == "__main__":
    main()
