#!/usr/bin/env python3
"""Run the accelerator backlog implementation daemon for display-widget work."""

from __future__ import annotations

import logging
from pathlib import Path

from lift_ipfs_accelerate_bootstrap import bootstrap_ipfs_accelerate


_PREIMPORT_BOOTSTRAP = bootstrap_ipfs_accelerate(__file__)
SCRIPT_REPO_ROOT = _PREIMPORT_BOOTSTRAP.script_repo_root
IPFS_ACCELERATE_ROOT = _PREIMPORT_BOOTSTRAP.package_root

from ipfs_accelerate_py.agent_supervisor.wrapper_utils import (  # noqa: E402
    build_android_validation_callbacks as _build_android_validation_callbacks,
    build_agent_supervisor_namespace_context as _build_agent_supervisor_namespace_context,
    build_repo_script_bootstrap as _build_repo_script_bootstrap,
    repo_doc_path as _repo_doc_path,
)

_SCRIPT_BOOTSTRAP = _build_repo_script_bootstrap(__file__)
SCRIPT_REPO_ROOT = _SCRIPT_BOOTSTRAP.script_repo_root
IPFS_ACCELERATE_ROOT = _SCRIPT_BOOTSTRAP.package_root
REPO_ROOT = _SCRIPT_BOOTSTRAP.repo_root
META_DISPLAY_ENV_PREFIX = "HANDSFREE_MGW"
OBJECTIVE_HEAP_PATH = _repo_doc_path(REPO_ROOT, "23-virtual-ai-os-objective-goal-heap.md")
_META_DISPLAY_CONTEXT = _build_agent_supervisor_namespace_context(
    REPO_ROOT,
    META_DISPLAY_ENV_PREFIX,
    namespace="meta_glasses_display_widgets",
    task_board_stem="18-swissknife-meta-glasses-display-widgets",
    objective_path=OBJECTIVE_HEAP_PATH,
    namespace_keys=("state_dir", "worktree_root", "discovery_dir", "objective_bundle_dir"),
    runtime_primary_package_names=("ipfs_accelerate",),
)
TASK_BOARD_PATH = _META_DISPLAY_CONTEXT.task_board_path
TASK_BOARD_PATH_OPTION = _META_DISPLAY_CONTEXT.task_board_path_option
META_DISPLAY_DATA_PATHS = _META_DISPLAY_CONTEXT.namespace_paths
WORKTREE_ROOT = META_DISPLAY_DATA_PATHS.worktree_root
DISCOVERY_DIR = META_DISPLAY_DATA_PATHS.discovery_dir
OBJECTIVE_BUNDLE_DIR = META_DISPLAY_DATA_PATHS.objective_bundle_dir
_META_DISPLAY_RUNTIME_BOOTSTRAP = _META_DISPLAY_CONTEXT.runtime_bootstrap
_META_DISPLAY_BOOTSTRAP_PATHS = _META_DISPLAY_RUNTIME_BOOTSTRAP.bootstrap_paths
META_DISPLAY_BOOTSTRAP_SPECS = _META_DISPLAY_BOOTSTRAP_PATHS.specs
META_DISPLAY_DISCOVERY_OUTPUT_DEFAULT = META_DISPLAY_DATA_PATHS.discovery_output_path()
_meta_display_discovery_output_path = _META_DISPLAY_BOOTSTRAP_PATHS.output_path_factory(
    "discovery_dir",
    META_DISPLAY_DISCOVERY_OUTPUT_DEFAULT,
)
_meta_display_discovery_output_kwargs = _META_DISPLAY_BOOTSTRAP_PATHS.output_path_kwargs_factory(
    "discovery_output_path",
    "discovery_dir",
    META_DISPLAY_DISCOVERY_OUTPUT_DEFAULT,
)
DISCOVERY_OUTPUT_PATH = _meta_display_discovery_output_path({"discovery_dir": DISCOVERY_DIR})
VALIDATION_RETRY_BUDGET = 3
META_DISPLAY_WORKTREE_SUBMODULE_PATHS = (
    "swissknife",
    "external/meta-wearables-dat-android",
    "external/meta-wearables-dat-ios",
)

from ipfs_accelerate_py.agent_supervisor.backlog_refinery import (  # noqa: E402
    build_configured_backlog_recorder_bundle,
    build_namespace_retry_budget_recorder,
)
from ipfs_accelerate_py.agent_supervisor.implementation_daemon_runner import (  # noqa: E402
    build_namespace_daemon_bootstrap_runner,
    namespace_implementation_state_artifact_paths,
)

logger = logging.getLogger("meta_glasses_display_todo_daemon")
meta_display_bootstrap_paths = _META_DISPLAY_BOOTSTRAP_PATHS.resolve
ensure_meta_display_bootstrap_paths = _META_DISPLAY_BOOTSTRAP_PATHS.ensure
_RUNTIME_ENVIRONMENT = _META_DISPLAY_RUNTIME_BOOTSTRAP.runtime_environment
_enter_runtime_environment = _RUNTIME_ENVIRONMENT.enter
_ensure_ipfs_accelerate_path = _RUNTIME_ENVIRONMENT.ensure_primary_pythonpath
_ensure_runtime_pythonpath = _RUNTIME_ENVIRONMENT.ensure_pythonpath
META_DISPLAY_STATE_PATHS = namespace_implementation_state_artifact_paths(
    META_DISPLAY_DATA_PATHS,
    state_prefix="meta_glasses_display",
)
_android_validation_callbacks = _build_android_validation_callbacks(
    REPO_ROOT,
    todo_path=TASK_BOARD_PATH,
)


android_validation_environment = _android_validation_callbacks.environment_contract
_bootstrap_android_validation_env = _android_validation_callbacks.apply_environment
with_android_validation_env = _android_validation_callbacks.wrap_command
enforce_android_validation_environment = _android_validation_callbacks.enforce_todo


record_retry_budget_findings = build_namespace_retry_budget_recorder(
    namespace_paths=META_DISPLAY_DATA_PATHS,
    todo_path=TASK_BOARD_PATH,
    events_path=META_DISPLAY_STATE_PATHS["events_path"],
    strategy_path=META_DISPLAY_STATE_PATHS["strategy_path"],
    task_header_prefix_value="## MGW-",
    validation_retry_budget=VALIDATION_RETRY_BUDGET,
    merge_retry_budget=0,
    implementation_retry_budget=0,
    validation_depends_on_if_present=("MGW-014",),
    validation_task_command_transform=lambda command: with_android_validation_env(command),
    discovery_output_path_default=DISCOVERY_OUTPUT_PATH,
    strip_validation_failure_kind=True,
    repo_root=REPO_ROOT,
    prepare_environment=_ensure_ipfs_accelerate_path,
)


def _prepare_meta_display_paths(paths: dict[str, Path]) -> None:
    _bootstrap_android_validation_env()
    enforce_android_validation_environment(paths["todo_path"])


_meta_display_refill_recorders = build_configured_backlog_recorder_bundle(
    retry_budget_recorder=record_retry_budget_findings,
)
_meta_display_refill_hooks = _meta_display_refill_recorders.daemon_refill_hooks_factory(
    discovery_dir_key="discovery_dir",
    retry_budget_extra_kwargs_factory=_meta_display_discovery_output_kwargs,
    scope_label="validation",
)
_meta_display_daemon_runner = build_namespace_daemon_bootstrap_runner(
    repo_root=REPO_ROOT,
    logger=logger,
    namespace_paths=META_DISPLAY_DATA_PATHS,
    ensure_paths=ensure_meta_display_bootstrap_paths,
    enter_runtime_environment=_enter_runtime_environment,
    enter_runtime_before_paths=True,
    path_callbacks=(_prepare_meta_display_paths,),
    hooks_factory=_meta_display_refill_hooks,
    use_bootstrap_keys=True,
    task_prefix="## MGW-",
    state_prefix="meta_glasses_display",
    todo_path_flag=TASK_BOARD_PATH_OPTION,
    objective_path_key="objective_heap_path",
    default_worktree_submodule_paths=META_DISPLAY_WORKTREE_SUBMODULE_PATHS,
    default_objective_path=OBJECTIVE_HEAP_PATH,
    pass_complete_message="Display-widget implementation daemon pass complete: %s",
)


def main(argv: list[str] | None = None) -> None:
    _meta_display_daemon_runner.run(argv)


if __name__ == "__main__":
    main()
