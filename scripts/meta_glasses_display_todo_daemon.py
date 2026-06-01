#!/usr/bin/env python3
"""Run the accelerator backlog implementation daemon for display-widget work."""

from __future__ import annotations

import logging
import sys
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[1]
IPFS_DATASETS_ROOT = REPO_ROOT / "external" / "ipfs_datasets"
IPFS_ACCELERATE_ROOT = REPO_ROOT / "external" / "ipfs_accelerate"
TASK_BOARD_PATH = REPO_ROOT / "implementation_plan" / "docs" / (
    "18-swissknife-meta-glasses-display-widgets." + "to" + "do.md"
)
TASK_BOARD_PATH_OPTION = "--" + "to" + "do" + "-path"
STATE_DIR = REPO_ROOT / "data" / "meta_glasses_display_widgets" / "state"
WORKTREE_ROOT = REPO_ROOT / "data" / "meta_glasses_display_widgets" / "worktrees"
DISCOVERY_DIR = REPO_ROOT / "data" / "meta_glasses_display_widgets" / "discovery"
OBJECTIVE_HEAP_PATH = REPO_ROOT / "implementation_plan" / "docs" / "23-virtual-ai-os-objective-goal-heap.md"
OBJECTIVE_BUNDLE_DIR = REPO_ROOT / "data" / "meta_glasses_display_widgets" / "objective_bundles"
LOCAL_JDK = REPO_ROOT / ".tools" / "jdk17" / "jdk-17.0.18+8"
LOCAL_ANDROID_SDK = REPO_ROOT / ".tools" / "android-sdk"
VALIDATION_RETRY_BUDGET = 3
META_DISPLAY_WORKTREE_SUBMODULE_PATHS = (
    "swissknife",
    "external/meta-wearables-dat-android",
    "external/meta-wearables-dat-ios",
)

if str(IPFS_ACCELERATE_ROOT) not in sys.path:
    sys.path.insert(0, str(IPFS_ACCELERATE_ROOT))

from ipfs_accelerate_py.agent_supervisor.wrapper_utils import (  # noqa: E402
    apply_environment_contract as _apply_environment_contract,
    bootstrap_runtime_environment as _bootstrap_runtime_environment,
    environment_assignment_prefix as _environment_assignment_prefix,
    repo_relative_or_default as _repo_relative_or_default,
    rewrite_validation_commands as _rewrite_validation_commands,
    unique_path_entries as _unique_path_entries,
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

logger = logging.getLogger("meta_glasses_display_todo_daemon")


def _ensure_ipfs_accelerate_path() -> None:
    _bootstrap_runtime_environment(REPO_ROOT, (IPFS_ACCELERATE_ROOT,), chdir=False)


def _ensure_runtime_pythonpath() -> None:
    _bootstrap_runtime_environment(REPO_ROOT, (IPFS_ACCELERATE_ROOT, IPFS_DATASETS_ROOT), chdir=False)


def _discovery_output_path(repo_root: Path, discovery_dir: Path) -> str:
    return _repo_relative_or_default(discovery_dir, repo_root, "data/meta_glasses_display_widgets/discovery")


def android_validation_environment(repo_root: Path = REPO_ROOT) -> dict[str, Any]:
    """Return the repo-local Android validation environment contract."""

    local_jdk = repo_root / ".tools" / "jdk17" / "jdk-17.0.18+8"
    local_android_sdk = repo_root / ".tools" / "android-sdk"
    env: dict[str, str] = {}
    path_entries: list[str] = []
    missing: list[str] = []

    if (local_jdk / "bin" / "java").exists():
        env["JAVA_HOME"] = str(local_jdk)
        path_entries.append(str(local_jdk / "bin"))
    else:
        missing.append(str(local_jdk / "bin" / "java"))

    if local_android_sdk.exists():
        env["ANDROID_HOME"] = str(local_android_sdk)
        env["ANDROID_SDK_ROOT"] = str(local_android_sdk)
        for candidate in (
            local_android_sdk / "platform-tools",
            local_android_sdk / "cmdline-tools" / "latest" / "bin",
            local_android_sdk / "cmdline-tools" / "bin",
        ):
            if candidate.exists():
                path_entries.append(str(candidate))
    else:
        missing.append(str(local_android_sdk))

    return {
        "env": env,
        "path_entries": _unique_path_entries(path_entries),
        "missing": missing,
        "repo_root": str(repo_root),
    }


def _bootstrap_android_validation_env(repo_root: Path = REPO_ROOT) -> dict[str, Any]:
    return _apply_environment_contract(android_validation_environment(repo_root))


def _android_env_assignment_prefix(repo_root: Path = REPO_ROOT) -> str:
    return _environment_assignment_prefix(
        android_validation_environment(repo_root),
        env_keys=("JAVA_HOME", "ANDROID_HOME", "ANDROID_SDK_ROOT"),
    )


def _validation_command_needs_android_env(command: str) -> bool:
    normalized = " ".join(command.split())
    if "./gradlew" not in normalized:
        return False
    if "mobile/android" not in normalized and "cd android" not in normalized:
        return False
    return "JAVA_HOME=" not in normalized and "org.gradle.java.home" not in normalized


def with_android_validation_env(command: str, repo_root: Path = REPO_ROOT) -> str:
    if not _validation_command_needs_android_env(command):
        return command
    prefix = _android_env_assignment_prefix(repo_root)
    if not prefix:
        return command
    return command.replace("./gradlew", f"env {prefix} ./gradlew", 1)


def enforce_android_validation_environment(todo_path: Path = TASK_BOARD_PATH, repo_root: Path = REPO_ROOT) -> bool:
    """Rewrite bare Android Gradle validations to use the repo-local JDK/SDK."""

    return _rewrite_validation_commands(
        todo_path,
        lambda command: with_android_validation_env(command, repo_root),
    )


def record_retry_budget_findings(
    *,
    todo_path: Path = TASK_BOARD_PATH,
    events_path: Path = STATE_DIR / "meta_glasses_display_events.jsonl",
    strategy_path: Path = STATE_DIR / "meta_glasses_display_strategy.json",
    discovery_dir: Path = DISCOVERY_DIR,
    task_header_prefix: str = "## MGW-",
    retry_budget: int = VALIDATION_RETRY_BUDGET,
) -> list[dict[str, Any]]:
    """Turn repeated validation failures into accelerator backlog items."""

    _ensure_ipfs_accelerate_path()
    from ipfs_accelerate_py.agent_supervisor.backlog_refinery import record_configured_retry_budget_findings

    return record_configured_retry_budget_findings(
        todo_path=todo_path,
        events_path=events_path,
        strategy_path=strategy_path,
        discovery_dir=discovery_dir,
        task_header_prefix_value=task_header_prefix,
        validation_retry_budget=retry_budget,
        merge_retry_budget=0,
        implementation_retry_budget=0,
        validation_depends_on_if_present=("MGW-014",),
        validation_task_command_transform=with_android_validation_env,
        discovery_output_path=_discovery_output_path(REPO_ROOT, discovery_dir),
        strip_validation_failure_kind=True,
    )


def main(argv: list[str] | None = None) -> None:
    args = list(sys.argv[1:] if argv is None else argv)
    _bootstrap_runtime_environment(REPO_ROOT, (IPFS_ACCELERATE_ROOT, IPFS_DATASETS_ROOT))
    _bootstrap_android_validation_env()
    enforce_android_validation_environment(TASK_BOARD_PATH)

    from ipfs_accelerate_py.agent_supervisor.todo_daemon.implementation_daemon import parse_args

    args = apply_portal_implementation_daemon_defaults(
        args,
        defaults=ImplementationDaemonDefaults(
            todo_path=TASK_BOARD_PATH,
            state_dir=STATE_DIR,
            task_prefix="## MGW-",
            state_prefix="meta_glasses_display",
            worktree_root=WORKTREE_ROOT,
            todo_path_flag=TASK_BOARD_PATH_OPTION,
            objective_path=OBJECTIVE_HEAP_PATH,
            objective_bundle_dir=OBJECTIVE_BUNDLE_DIR,
            worktree_submodule_paths=META_DISPLAY_WORKTREE_SUBMODULE_PATHS,
        ),
    )
    parsed = parse_args(args)
    configure_daemon_logging(parsed)
    daemon, context = build_portal_implementation_daemon_from_args(
        parsed,
        repo_root=REPO_ROOT,
        default_worktree_submodule_paths=META_DISPLAY_WORKTREE_SUBMODULE_PATHS,
        default_objective_path=OBJECTIVE_HEAP_PATH,
        default_objective_bundle_dir=OBJECTIVE_BUNDLE_DIR,
    )

    def retry_budget_hook(ctx: ImplementationDaemonRunContext) -> list[dict[str, Any]]:
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
            (("retry-budget", retry_budget_hook),),
            scope_label="validation",
        ),
        pass_complete_message="Display-widget implementation daemon pass complete: %s",
    )


if __name__ == "__main__":
    main()
