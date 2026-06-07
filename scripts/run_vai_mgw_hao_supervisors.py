#!/usr/bin/env python3
"""Run the lift-specific VAI/MGW/HAO supervisor tracks."""

from __future__ import annotations

import sys
from typing import Sequence

from lift_ipfs_accelerate_bootstrap import bootstrap_ipfs_accelerate


_PREIMPORT_BOOTSTRAP = bootstrap_ipfs_accelerate(__file__)
SCRIPT_REPO_ROOT = _PREIMPORT_BOOTSTRAP.script_repo_root
BOOTSTRAP_IPFS_ACCELERATE_ROOT = _PREIMPORT_BOOTSTRAP.package_root

from ipfs_accelerate_py.agent_supervisor.wrapper_utils import build_repo_script_bootstrap  # noqa: E402


_SCRIPT_BOOTSTRAP = build_repo_script_bootstrap(__file__)
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


MULTI_SUPERVISOR_ENV_DEFAULTS = implementation_multi_supervisor_env_defaults(
    prefer_copilot_merge_resolver=True,
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
