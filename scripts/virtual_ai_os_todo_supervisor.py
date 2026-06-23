#!/usr/bin/env python3
"""Run the accelerator backlog supervisor for virtual-AI-OS work."""

from __future__ import annotations

import logging

from lift_ipfs_accelerate_bootstrap import bootstrap_ipfs_accelerate


_PREIMPORT_BOOTSTRAP = bootstrap_ipfs_accelerate(__file__, include_script_dir=True)
SCRIPT_REPO_ROOT = _PREIMPORT_BOOTSTRAP.script_repo_root
IPFS_ACCELERATE_ROOT = _PREIMPORT_BOOTSTRAP.package_root

from ipfs_accelerate_py.agent_supervisor.wrapper_utils import (  # noqa: E402
    build_repo_script_bootstrap as _build_repo_script_bootstrap,
    data_namespace_scan_skip_prefixes as _data_namespace_scan_skip_prefixes,
    prefixed_interoperability_focus as _prefixed_interoperability_focus,
    prefixed_objective_refill_env_settings as _prefixed_objective_refill_env_settings,
    repo_script_path as _repo_script_path,
)
# scanner-resolved: VAI-167 VAI-171 — The CLI flag above names the backlog task-board file path; it is not a deferred-work annotation.
TASK_BOARD_PATH_OPTION = "--todo-path"
DEFAULT_STATE_DIR = REPO_ROOT / "data" / "virtual_ai_os" / "state"
DEFAULT_WORKTREE_ROOT = REPO_ROOT / "data" / "virtual_ai_os" / "worktrees"
DAEMON_SCRIPT_PATH = REPO_ROOT / "scripts" / "virtual_ai_os_todo_daemon.py"
DISCOVERY_DIR = REPO_ROOT / "data" / "virtual_ai_os" / "discovery"
OBJECTIVE_HEAP_PATH = REPO_ROOT / "implementation_plan" / "docs" / "23-virtual-ai-os-objective-goal-heap.md"
OBJECTIVE_GRAPH_PATH = REPO_ROOT / "data" / "virtual_ai_os" / "objective_graph.json"
OBJECTIVE_BUNDLE_DIR = REPO_ROOT / "data" / "virtual_ai_os" / "objective_bundles"
OBJECTIVE_DATASET_DIR = REPO_ROOT / "data" / "virtual_ai_os" / "objective_datasets"
CODEBASE_SCAN_SKIP_PREFIXES = (
    "scripts/",  # supervisor/daemon scripts reference backlog task-board file paths by design, not as code annotations
    "data/virtual_ai_os/discovery/",
    "data/virtual_ai_os/objective_bundles/",
    "data/virtual_ai_os/objective_datasets/",
    "data/virtual_ai_os/state/",
    "data/virtual_ai_os/worktrees/",
    "data/hallucinate_multimodal_control/discovery/",
    "data/hallucinate_multimodal_control/state/",
    "data/hallucinate_multimodal_control/worktrees/",
    "data/meta_glasses_display_widgets/discovery/",
    "data/meta_glasses_display_widgets/state/",
    "data/meta_glasses_display_widgets/worktrees/",
)
from ipfs_accelerate_py.agent_supervisor.implementation_supervisor_runner import (  # noqa: E402
    build_namespace_codebase_refill_defaults_factory,
    build_namespace_objective_refill_defaults_factory,
    build_configured_supervisor_runtime_exports,
    build_script_supervisor_bootstrap_runner,
)

VIRTUAL_AI_OS_INTEROPERABILITY_FOCUS = _prefixed_interoperability_focus(
    VIRTUAL_AI_OS_ENV_PREFIX,
    "hallucinate_app",
)
_VIRTUAL_AI_OS_RUNTIME_BOOTSTRAP = _VIRTUAL_AI_OS_CONTEXT.runtime_bootstrap
_VIRTUAL_AI_OS_BOOTSTRAP_PATHS = _VIRTUAL_AI_OS_RUNTIME_BOOTSTRAP.bootstrap_paths
VIRTUAL_AI_OS_BOOTSTRAP_SPECS = _VIRTUAL_AI_OS_BOOTSTRAP_PATHS.specs
_RUNTIME_ENVIRONMENT = _VIRTUAL_AI_OS_RUNTIME_BOOTSTRAP.runtime_environment
_enter_runtime_environment = _RUNTIME_ENVIRONMENT.enter
_ensure_runtime_pythonpath = _RUNTIME_ENVIRONMENT.ensure_pythonpath
virtual_ai_os_bootstrap_paths = _VIRTUAL_AI_OS_BOOTSTRAP_PATHS.resolve
ensure_virtual_ai_os_bootstrap_paths = _VIRTUAL_AI_OS_BOOTSTRAP_PATHS.ensure
_default_llm_merge_resolver_command = _prefixed_llm_merge_callback(
    VIRTUAL_AI_OS_ENV_PREFIX
)
logger = logging.getLogger("virtual_ai_os_todo_supervisor")

_virtual_ai_os_objective_defaults = build_namespace_objective_refill_defaults_factory(
    VIRTUAL_AI_OS_DATA_PATHS,
    objective_path=OBJECTIVE_HEAP_PATH,
    objective_discovery_output_path=DISCOVERY_OUTPUT_PATH,
    objective_interoperability_focus=VIRTUAL_AI_OS_INTEROPERABILITY_FOCUS,
    seed_interoperability_goals=True,
    **OBJECTIVE_REFILL_SETTINGS.objective_refill_kwargs(),
)


_virtual_ai_os_codebase_defaults = build_namespace_codebase_refill_defaults_factory(
    VIRTUAL_AI_OS_DATA_PATHS,
    codebase_scan_discovery_output_path=DISCOVERY_OUTPUT_PATH,
    codebase_scan_min_open_tasks=0,
    codebase_scan_skip_prefixes=CODEBASE_SCAN_SKIP_PREFIXES,
)
_virtual_ai_os_supervisor_runner = build_script_supervisor_bootstrap_runner(
    repo_root=REPO_ROOT,
    script_path=__file__,
    logger=logger,
    ensure_paths=ensure_virtual_ai_os_bootstrap_paths,
    prepare_environment=_ensure_runtime_pythonpath,
    enter_runtime_environment=_enter_runtime_environment,
    task_prefix="## VAI-",
    state_prefix="virtual_ai_os",
    daemon_script_path=DAEMON_SCRIPT_PATH,
    llm_merge_resolver_command=_default_llm_merge_resolver_command,
    worktree_submodule_paths=VIRTUAL_AI_OS_WORKTREE_SUBMODULE_PATHS,
    generated_dirty_repair_enabled=True,
    generated_dirty_repair_commit_subject="VAI: reconcile generated supervisor outputs",
    objective_factory=_virtual_ai_os_objective_defaults,
    codebase_factory=_virtual_ai_os_codebase_defaults,
    once_complete_message="Virtual-AI-OS implementation supervisor check complete: %s",
    ensure_running_message="Virtual-AI-OS implementation supervisor ensure complete: %s",
    repair_runtime_message="Repaired stale virtual-AI-OS supervisor runtime markers: %s",
)
_virtual_ai_os_supervisor_runtime = _virtual_ai_os_supervisor_runner.runtime
_virtual_ai_os_supervisor_exports = build_configured_supervisor_runtime_exports(_virtual_ai_os_supervisor_runtime)
VIRTUAL_AI_OS_SUPERVISOR_PROCESS_MARKERS = _virtual_ai_os_supervisor_exports.process_match_any
repair_virtual_ai_os_supervisor_runtime = _virtual_ai_os_supervisor_exports.repair_runtime
virtual_ai_os_supervisor_is_running = _virtual_ai_os_supervisor_exports.is_running
ensure_virtual_ai_os_supervisor_running = _virtual_ai_os_supervisor_exports.ensure_running


def main(argv: list[str] | None = None) -> None:
    args = list(sys.argv[1:] if argv is None else argv)
    paths = ensure_virtual_ai_os_bootstrap_paths()
    os.chdir(REPO_ROOT)
    _ensure_runtime_pythonpath()

    from ipfs_accelerate_py.agent_supervisor.todo_daemon.implementation_supervisor import main as supervisor_main

    args = _with_default(args, TASK_BOARD_PATH_OPTION, str(paths["todo_path"]))
    args = _with_default(args, "--state-dir", str(paths["state_dir"]))
    args = _with_default(args, "--task-prefix", "## VAI-")
    args = _with_default(args, "--state-prefix", "virtual_ai_os")
    args = _with_default(args, "--worktree-root", str(paths["worktree_root"]))
    args = _with_default(args, "--daemon-script-path", str(DAEMON_SCRIPT_PATH))
    args = _with_default(args, "--supervisor-script-path", str(Path(__file__).resolve()))
    args = _with_default(args, "--max-restarts", "0")
    args = _with_repeated_default(args, "--worktree-submodule-path", VIRTUAL_AI_OS_WORKTREE_SUBMODULE_PATHS)
    args = _with_flag_default(args, "--objective-refill-scan")
    args = _with_default(args, "--objective-path", str(OBJECTIVE_HEAP_PATH))
    args = _with_default(args, "--objective-graph-path", str(OBJECTIVE_GRAPH_PATH))
    args = _with_default(args, "--objective-bundle-dir", str(OBJECTIVE_BUNDLE_DIR))
    args = _with_default(args, "--objective-dataset-dir", str(OBJECTIVE_DATASET_DIR))
    args = _with_default(args, "--objective-discovery-dir", str(DISCOVERY_DIR))
    args = _with_default(args, "--objective-discovery-output-path", "data/virtual_ai_os/discovery")
    args = _with_default(args, "--objective-scan-min-open-tasks", "0")
    args = _with_flag_default(args, "--codebase-refill-scan")
    args = _with_default(args, "--codebase-scan-discovery-dir", str(DISCOVERY_DIR))
    args = _with_default(args, "--codebase-scan-discovery-output-path", "data/virtual_ai_os/discovery")
    args = _with_default(args, "--codebase-scan-min-open-tasks", "0")
    args = _with_repeated_default(args, "--codebase-scan-skip-prefix", CODEBASE_SCAN_SKIP_PREFIXES)
    supervisor_main(args)


if __name__ == "__main__":
    main()
