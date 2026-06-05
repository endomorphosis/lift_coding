#!/usr/bin/env python3
"""Run the accelerator task supervisor for Hallucinate multimodal-control work."""

from __future__ import annotations

import logging
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
    build_prefixed_default_llm_merge_resolver_command_callback as _prefixed_llm_merge_callback,
    build_repo_runtime_environment_callbacks as _build_repo_runtime_environment_callbacks,
    repo_script_path as _repo_script_path,
)
from ipfs_accelerate_py.agent_supervisor.implementation_supervisor_runner import (  # noqa: E402
    build_configured_supervisor_bootstrap_runner,
    build_script_supervisor_runtime,
    build_namespace_codebase_refill_defaults_factory,
    build_namespace_objective_refill_defaults_factory,
    build_supervisor_refill_hooks_factory_from_recorders,
)
from hallucinate_multimodal_control_todo_daemon import (  # noqa: E402
    CODEBASE_SCAN_SETTINGS,
    CODEBASE_SCAN_SKIP_PREFIXES,
    DISCOVERY_DIR,
    HALLUCINATE_DATA_PATHS,
    HALLUCINATE_WORKTREE_SUBMODULE_PATHS,
    OBJECTIVE_REFILL_SETTINGS,
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
DAEMON_SCRIPT_PATH = _repo_script_path(REPO_ROOT, "hallucinate_multimodal_control_todo_daemon.py")
DISCOVERY_OUTPUT_PATH = HALLUCINATE_DATA_PATHS.discovery_output_path()
_RUNTIME_ENVIRONMENT = _build_repo_runtime_environment_callbacks(REPO_ROOT)
_enter_runtime_environment = _RUNTIME_ENVIRONMENT.enter
_ensure_runtime_pythonpath = _RUNTIME_ENVIRONMENT.ensure_pythonpath
_default_llm_merge_resolver_command = _prefixed_llm_merge_callback(
    HALLUCINATE_ENV_PREFIX
)
_hallucinate_supervisor_runtime = build_script_supervisor_runtime(
    repo_root=REPO_ROOT,
    script_path=__file__,
    extra_process_match_any=("hallucinate_multimodal_control_autopilot.py",),
    prepare_environment=_ensure_runtime_pythonpath,
)
repair_hallucinate_supervisor_runtime = _hallucinate_supervisor_runtime.repair_runtime
hallucinate_supervisor_is_running = _hallucinate_supervisor_runtime.is_running
ensure_hallucinate_supervisor_running = _hallucinate_supervisor_runtime.ensure_running


_hallucinate_objective_defaults = build_namespace_objective_refill_defaults_factory(
    HALLUCINATE_DATA_PATHS,
    objective_path_key="objective_goal_heap_path",
    objective_discovery_output_path=DISCOVERY_OUTPUT_PATH,
    objective_interoperability_focus=HALLUCINATE_INTEROPERABILITY_FOCUS,
    seed_interoperability_goals=True,
    **OBJECTIVE_REFILL_SETTINGS.objective_refill_kwargs(),
)


_hallucinate_codebase_defaults = build_namespace_codebase_refill_defaults_factory(
    HALLUCINATE_DATA_PATHS,
    codebase_scan_discovery_output_path=DISCOVERY_OUTPUT_PATH,
    codebase_scan_skip_prefixes=CODEBASE_SCAN_SKIP_PREFIXES,
    **CODEBASE_SCAN_SETTINGS.codebase_refill_kwargs(),
)


_hallucinate_refill_hooks = build_supervisor_refill_hooks_factory_from_recorders(
    objective_recorder=record_objective_goal_findings,
    codebase_scan_recorder=record_codebase_scan_findings,
    retry_budget_recorder=record_retry_budget_findings,
    discovery_dir=DISCOVERY_DIR,
    objective_path_key="objective_goal_heap_path",
    repo_root=REPO_ROOT,
    scope_label="Hallucinate",
)
_hallucinate_supervisor_runner = build_configured_supervisor_bootstrap_runner(
    runtime=_hallucinate_supervisor_runtime,
    logger=logger,
    ensure_paths=ensure_hallucinate_multimodal_bootstrap_paths,
    enter_runtime_environment=_enter_runtime_environment,
    todo_path_key=TASK_BOARD_PATH_KEY,
    task_prefix="## HAO-",
    state_prefix="hallucinate_multimodal_control",
    daemon_script_path=DAEMON_SCRIPT_PATH,
    todo_path_flag=TASK_BOARD_PATH_OPTION,
    llm_merge_resolver_command=_default_llm_merge_resolver_command,
    worktree_submodule_paths=HALLUCINATE_WORKTREE_SUBMODULE_PATHS,
    objective_factory=_hallucinate_objective_defaults,
    codebase_factory=_hallucinate_codebase_defaults,
    hooks_factory=_hallucinate_refill_hooks,
    once_complete_message="Hallucinate multimodal-control supervisor check complete: %s",
    ensure_running_message="Hallucinate multimodal-control supervisor ensure complete: %s",
    repair_runtime_message="Repaired stale Hallucinate supervisor runtime markers: %s",
)


def main(argv: list[str] | None = None) -> None:
    args = list(sys.argv[1:] if argv is None else argv)

    _hallucinate_supervisor_runner.run(args)


if __name__ == "__main__":
    main()
