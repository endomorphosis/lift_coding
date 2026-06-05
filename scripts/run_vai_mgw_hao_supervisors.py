#!/usr/bin/env python3
"""Run the lift-specific VAI/MGW/HAO supervisor tracks."""

from __future__ import annotations

from typing import Sequence

from lift_ipfs_accelerate_bootstrap import bootstrap_ipfs_accelerate


_PREIMPORT_BOOTSTRAP = bootstrap_ipfs_accelerate(__file__)
SCRIPT_REPO_ROOT = _PREIMPORT_BOOTSTRAP.script_repo_root
BOOTSTRAP_IPFS_ACCELERATE_ROOT = _PREIMPORT_BOOTSTRAP.package_root

from ipfs_accelerate_py.agent_supervisor.wrapper_utils import (  # noqa: E402
    agent_supervisor_namespace_paths,
    build_repo_script_bootstrap,
)


_SCRIPT_BOOTSTRAP = build_repo_script_bootstrap(__file__)
SCRIPT_REPO_ROOT = _SCRIPT_BOOTSTRAP.script_repo_root
BOOTSTRAP_IPFS_ACCELERATE_ROOT = _SCRIPT_BOOTSTRAP.package_root
REPO_ROOT = _SCRIPT_BOOTSTRAP.repo_root


from ipfs_accelerate_py.agent_supervisor.multi_supervisor_runner import (  # noqa: E402
    ConfiguredMultiSupervisorCliRunner,
    ConfiguredMultiSupervisorLauncher,
    build_repo_implementation_multi_supervisor_launcher,
    implementation_multi_supervisor_env_defaults,
    implementation_supervisor_namespace_track_config,
)


MULTI_SUPERVISOR_ENV_DEFAULTS = implementation_multi_supervisor_env_defaults(
    prefer_copilot_merge_resolver=True,
)


VAI_MGW_HAO_IMPLEMENTATION_TRACK_CONFIGS = (
    implementation_supervisor_namespace_track_config(
        name="VAI",
        script_path="scripts/virtual_ai_os_todo_supervisor.py",
        namespace_paths=agent_supervisor_namespace_paths(REPO_ROOT, "virtual_ai_os"),
    ),
    implementation_supervisor_namespace_track_config(
        name="MGW",
        script_path="scripts/meta_glasses_display_todo_supervisor.py",
        namespace_paths=agent_supervisor_namespace_paths(REPO_ROOT, "meta_glasses_display_widgets"),
        state_prefix="meta_glasses_display",
    ),
    implementation_supervisor_namespace_track_config(
        name="HAO",
        script_path="scripts/hallucinate_multimodal_control_todo_supervisor.py",
        namespace_paths=agent_supervisor_namespace_paths(REPO_ROOT, "hallucinate_multimodal_control"),
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


def main(argv: Sequence[str] | None = None) -> int:
    """Run the configured VAI/MGW/HAO multi-supervisor CLI."""

    return build_launcher().run_cli(argv)


if __name__ == "__main__":
    raise SystemExit(main())
