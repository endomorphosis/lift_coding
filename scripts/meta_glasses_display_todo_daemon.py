#!/usr/bin/env python3
"""Run the accelerator backlog implementation daemon for display-widget work."""

from __future__ import annotations

import logging
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
IPFS_ACCELERATE_ROOT = REPO_ROOT / "external" / "ipfs_accelerate"

if str(IPFS_ACCELERATE_ROOT) not in sys.path:
    sys.path.insert(0, str(IPFS_ACCELERATE_ROOT))

from ipfs_accelerate_py.agent_supervisor.wrapper_utils import (  # noqa: E402
    build_android_validation_callbacks as _build_android_validation_callbacks,
    build_prefixed_bootstrap_path_callbacks as _build_prefixed_bootstrap_path_callbacks,
    build_repo_runtime_environment_callbacks as _build_repo_runtime_environment_callbacks,
    task_board_filename as _task_board_filename,
    task_board_path_option as _task_board_path_option,
)

TASK_BOARD_PATH = REPO_ROOT / "implementation_plan" / "docs" / (
    _task_board_filename("18-swissknife-meta-glasses-display-widgets")
)
TASK_BOARD_PATH_OPTION = _task_board_path_option()
META_DISPLAY_ENV_PREFIX = "HANDSFREE_MGW"
STATE_DIR = REPO_ROOT / "data" / "meta_glasses_display_widgets" / "state"
WORKTREE_ROOT = REPO_ROOT / "data" / "meta_glasses_display_widgets" / "worktrees"
DISCOVERY_DIR = REPO_ROOT / "data" / "meta_glasses_display_widgets" / "discovery"
OBJECTIVE_HEAP_PATH = REPO_ROOT / "implementation_plan" / "docs" / "23-virtual-ai-os-objective-goal-heap.md"
OBJECTIVE_BUNDLE_DIR = REPO_ROOT / "data" / "meta_glasses_display_widgets" / "objective_bundles"
_META_DISPLAY_BOOTSTRAP_PATHS = _build_prefixed_bootstrap_path_callbacks(
    REPO_ROOT,
    META_DISPLAY_ENV_PREFIX,
    (
        ("todo_path", TASK_BOARD_PATH),
        ("state_dir", STATE_DIR),
        ("worktree_root", WORKTREE_ROOT),
        ("discovery_dir", DISCOVERY_DIR),
        ("objective_heap_path", OBJECTIVE_HEAP_PATH),
        ("objective_bundle_dir", OBJECTIVE_BUNDLE_DIR),
    ),
    ("state_dir", "worktree_root", "discovery_dir", "objective_bundle_dir"),
)
META_DISPLAY_BOOTSTRAP_SPECS = _META_DISPLAY_BOOTSTRAP_PATHS.specs
DISCOVERY_OUTPUT_PATH = _META_DISPLAY_BOOTSTRAP_PATHS.output_path(
    "discovery_dir",
    "data/meta_glasses_display_widgets/discovery",
    {"discovery_dir": DISCOVERY_DIR},
)
VALIDATION_RETRY_BUDGET = 3
META_DISPLAY_WORKTREE_SUBMODULE_PATHS = (
    "swissknife",
    "external/meta-wearables-dat-android",
    "external/meta-wearables-dat-ios",
)

from ipfs_accelerate_py.agent_supervisor.backlog_refinery import ConfiguredRetryBudgetRecorder  # noqa: E402
from ipfs_accelerate_py.agent_supervisor.implementation_daemon_runner import (  # noqa: E402
    build_configured_implementation_daemon_runner,
    build_daemon_refill_hooks_factory_from_recorders,
)

logger = logging.getLogger("meta_glasses_display_todo_daemon")
meta_display_bootstrap_paths = _META_DISPLAY_BOOTSTRAP_PATHS.resolve
ensure_meta_display_bootstrap_paths = _META_DISPLAY_BOOTSTRAP_PATHS.ensure
_RUNTIME_ENVIRONMENT = _build_repo_runtime_environment_callbacks(
    REPO_ROOT,
    primary_package_names=("ipfs_accelerate",),
)
_enter_runtime_environment = _RUNTIME_ENVIRONMENT.enter
_ensure_ipfs_accelerate_path = _RUNTIME_ENVIRONMENT.ensure_primary_pythonpath
_ensure_runtime_pythonpath = _RUNTIME_ENVIRONMENT.ensure_pythonpath
_android_validation_callbacks = _build_android_validation_callbacks(
    REPO_ROOT,
    todo_path=TASK_BOARD_PATH,
)


android_validation_environment = _android_validation_callbacks.environment_contract
_bootstrap_android_validation_env = _android_validation_callbacks.apply_environment
with_android_validation_env = _android_validation_callbacks.wrap_command
enforce_android_validation_environment = _android_validation_callbacks.enforce_todo


record_retry_budget_findings = ConfiguredRetryBudgetRecorder(
    todo_path=TASK_BOARD_PATH,
    events_path=STATE_DIR / "meta_glasses_display_events.jsonl",
    strategy_path=STATE_DIR / "meta_glasses_display_strategy.json",
    discovery_dir=DISCOVERY_DIR,
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


def _meta_display_retry_budget_extra_kwargs(paths: dict[str, Path]):
    return {
        "discovery_output_path": _META_DISPLAY_BOOTSTRAP_PATHS.output_path(
            "discovery_dir",
            "data/meta_glasses_display_widgets/discovery",
            paths,
        ),
    }


_meta_display_refill_hooks = build_daemon_refill_hooks_factory_from_recorders(
    retry_budget_recorder=record_retry_budget_findings,
    discovery_dir_key="discovery_dir",
    retry_budget_extra_kwargs_factory=_meta_display_retry_budget_extra_kwargs,
    scope_label="validation",
)


def main(argv: list[str] | None = None) -> None:
    args = list(sys.argv[1:] if argv is None else argv)

    build_configured_implementation_daemon_runner(
        repo_root=REPO_ROOT,
        logger=logger,
        default_worktree_submodule_paths=META_DISPLAY_WORKTREE_SUBMODULE_PATHS,
        default_objective_path=OBJECTIVE_HEAP_PATH,
        default_objective_bundle_dir=OBJECTIVE_BUNDLE_DIR,
        pass_complete_message="Display-widget implementation daemon pass complete: %s",
    ).run_configured_from_bootstrap(
        args,
        ensure_paths=ensure_meta_display_bootstrap_paths,
        enter_runtime_environment=_enter_runtime_environment,
        enter_runtime_before_paths=True,
        path_callbacks=(_prepare_meta_display_paths,),
        task_prefix="## MGW-",
        state_prefix="meta_glasses_display",
        todo_path_flag=TASK_BOARD_PATH_OPTION,
        objective_path_key="objective_heap_path",
        objective_bundle_dir_key="objective_bundle_dir",
        worktree_submodule_paths=META_DISPLAY_WORKTREE_SUBMODULE_PATHS,
        hooks_factory=_meta_display_refill_hooks,
    )


if __name__ == "__main__":
    main()
