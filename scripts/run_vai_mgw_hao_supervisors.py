#!/usr/bin/env python3
"""Run the lift-specific VAI/MGW/HAO supervisor tracks."""

from __future__ import annotations

import os
import sys
from typing import Sequence

from lift_ipfs_accelerate_bootstrap import bootstrap_ipfs_accelerate


_PREIMPORT_BOOTSTRAP = bootstrap_ipfs_accelerate(__file__)
SCRIPT_REPO_ROOT = _PREIMPORT_BOOTSTRAP.script_repo_root
BOOTSTRAP_IPFS_ACCELERATE_ROOT = _PREIMPORT_BOOTSTRAP.package_root

from ipfs_accelerate_py.agent_supervisor.wrapper_utils import build_repo_script_bootstrap  # noqa: E402


_SCRIPT_BOOTSTRAP = build_repo_script_bootstrap(__file__, environ={})
SCRIPT_REPO_ROOT = _SCRIPT_BOOTSTRAP.script_repo_root
BOOTSTRAP_IPFS_ACCELERATE_ROOT = _SCRIPT_BOOTSTRAP.package_root
REPO_ROOT = _SCRIPT_BOOTSTRAP.repo_root


from ipfs_accelerate_py.agent_supervisor.multi_supervisor_runner import (  # noqa: E402
    ConfiguredMultiSupervisorCliRunner,
    ConfiguredMultiSupervisorLauncher,
    build_repo_implementation_multi_supervisor_launcher,
    implementation_multi_supervisor_env_defaults,
    implementation_supervisor_namespace_track_configs,
)


MULTI_SUPERVISOR_ENV_DEFAULTS = {
    **implementation_multi_supervisor_env_defaults(
        prefer_copilot_merge_resolver=False,
    ),
    "IMPLEMENTATION_SUPERVISOR_LANES_PER_TRACK": os.environ.get(
        "IMPLEMENTATION_SUPERVISOR_LANES_PER_TRACK",
        "2",
    ),
}


DETACHED_WORKTREE_POLICY = (
    "default to --detach for long VAI/MGW/HAO supervisor runs; implementation "
    "work happens in namespace task worktrees, and component submodules track "
    ".gitmodules branches while the superproject records each reviewed gitlink"
)

MERGE_CLEANUP_DEFAULTS = {
    "worktree_reconciliation_max_merges": "3",
    "merge_reconciliation_max_merges": "3",
    "daemon_merged_worktree_cleanup_max": "50",
}

REFILL_DEFAULTS = {
    "objective_scan_min_open_tasks": "20",
    "objective_scan_max_findings": "6",
    "objective_surplus_findings_per_goal": "2",
    "codebase_scan_min_open_tasks": "8",
    "codebase_scan_max_findings": "3",
    "objective_max_interoperability_goals": "12",
}

VAI_MGW_HAO_INTEROPERABILITY_COMPONENT_PATHS = (
    "mobile",
    "swissknife",
    "hallucinate_app",
    "external/ipfs_accelerate",
    "external/ipfs_datasets",
    "external/ipfs_kit",
    "Mcp-Plus-Plus",
    "external/meta-wearables-dat-android",
    "external/meta-wearables-dat-ios",
)

VAI_MGW_HAO_INTEROPERABILITY_COMPONENT_ARGS = tuple(
    item
    for path in VAI_MGW_HAO_INTEROPERABILITY_COMPONENT_PATHS
    for item in ("--objective-interoperability-component-path", path)
)

VAI_MGW_HAO_LAUNCH_MISSION_TERMS = (
    "phone-hosted Swissknife virtual desktop",
    "desktop peer offload",
    "Hallucinate App mediation",
    "Hallucinate App menus",
    "Hallucinate App dashboards",
    "Hallucinate App MCP dashboard",
    "Hallucinate App dashboard capability catalog",
    "Hallucinate App daemon health",
    "Hallucinate App tools/list",
    "Hallucinate App tools/call",
    "Meta glasses interface",
    "Meta Wearables DAT",
    "camera",
    "microphone",
    "headphones",
    "Neural Band",
    "captouch",
    "mobile phone",
    "IPFS",
    "libp2p",
    "MCP++",
    "MCP server",
    "MCP dashboard",
    "dashboard capability catalog",
    "daemon health",
    "tools/list",
    "tools/call",
    "ipfs_accelerate_py",
    "ipfs_datasets_py",
    "ipfs_kit_py",
    "Python MCP package names",
    "Swissknife applications",
    "control plane",
    "production readiness",
    "launch readiness",
    "Playwright launch replay",
    "cross-device e2e validation",
    "launch readiness receipt",
)

VAI_MGW_HAO_LAUNCH_MISSION_ARGS = tuple(
    item
    for term in VAI_MGW_HAO_LAUNCH_MISSION_TERMS
    for item in ("--objective-mission-term", term)
)


VAI_MGW_HAO_IMPLEMENTATION_TRACK_CONFIGS = implementation_supervisor_namespace_track_configs(
    repo_root=REPO_ROOT,
    track_specs=(
        ("VAI", "scripts/virtual_ai_os_todo_supervisor.py", "virtual_ai_os"),
        (
            "MGW",
            "scripts/meta_glasses_display_todo_supervisor.py",
            "meta_glasses_display_widgets",
            "meta_glasses_display",
        ),
        (
            "HAO",
            "scripts/hallucinate_multimodal_control_todo_supervisor.py",
            "hallucinate_multimodal_control",
        ),
    ),
)

VAI_MGW_HAO_RECONCILIATION_COMMON_ARGS = (
    "--retry-budget-commit-outputs",
    "--dependency-guardrail-commit-outputs",
    "--auto-commit-generated-dirty",
    "--worktree-reconciliation-max-merges",
    MERGE_CLEANUP_DEFAULTS["worktree_reconciliation_max_merges"],
    "--merge-reconciliation-max-merges",
    MERGE_CLEANUP_DEFAULTS["merge_reconciliation_max_merges"],
    "--daemon-merged-worktree-cleanup-max",
    MERGE_CLEANUP_DEFAULTS["daemon_merged_worktree_cleanup_max"],
    "--codebase-scan-min-open-tasks",
    REFILL_DEFAULTS["codebase_scan_min_open_tasks"],
    "--codebase-scan-max-findings",
    REFILL_DEFAULTS["codebase_scan_max_findings"],
    "--objective-max-refinement-children",
    "2",
    "--objective-max-refinement-depth",
    "2",
    "--objective-max-interoperability-goals",
    REFILL_DEFAULTS["objective_max_interoperability_goals"],
    *VAI_MGW_HAO_INTEROPERABILITY_COMPONENT_ARGS,
    "--objective-task-janitor-max-deprioritized-tasks",
    "500",
    *VAI_MGW_HAO_LAUNCH_MISSION_ARGS,
    "--objective-scan-min-open-tasks",
    REFILL_DEFAULTS["objective_scan_min_open_tasks"],
    "--objective-scan-max-findings",
    REFILL_DEFAULTS["objective_scan_max_findings"],
    "--objective-surplus-findings-per-goal",
    REFILL_DEFAULTS["objective_surplus_findings_per_goal"],
)


def build_launcher() -> ConfiguredMultiSupervisorLauncher:
    """Return the configured reusable launcher for this repository's tracks."""

    return build_repo_implementation_multi_supervisor_launcher(
        repo_root=REPO_ROOT,
        implementation_track_configs=VAI_MGW_HAO_IMPLEMENTATION_TRACK_CONFIGS,
        duration_seconds=28800,
        duration_seconds_env_var="DURATION_SECONDS",
        stamp_env_var="STAMP",
        master_dir="data/agent_supervisor",
        label="VAI/MGW/HAO supervisor run",
        common_args=VAI_MGW_HAO_RECONCILIATION_COMMON_ARGS,
        env_defaults=MULTI_SUPERVISOR_ENV_DEFAULTS,
    )


def build_runner() -> ConfiguredMultiSupervisorCliRunner:
    """Return the configured reusable runner for this repository's tracks."""

    return build_launcher().runner


def default_launch_args(argv: Sequence[str]) -> list[str]:
    """Return wrapper CLI args, defaulting long runs to detached mode."""

    launch_args = list(argv)
    if "--foreground" in launch_args:
        return [arg for arg in launch_args if arg != "--foreground"]
    if "--detach" not in launch_args:
        launch_args.append("--detach")
    return launch_args


def main(argv: Sequence[str] | None = None) -> int:
    """Run the configured VAI/MGW/HAO multi-supervisor CLI."""

    cli_args = sys.argv[1:] if argv is None else argv
    return build_launcher().run_cli(default_launch_args(cli_args))


if __name__ == "__main__":
    raise SystemExit(main())
