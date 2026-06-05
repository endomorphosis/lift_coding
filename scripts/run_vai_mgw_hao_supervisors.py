#!/usr/bin/env python3
"""Run the lift-specific VAI/MGW/HAO supervisor tracks."""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Sequence


SCRIPT_REPO_ROOT = Path(__file__).resolve().parents[1]
BOOTSTRAP_IPFS_ACCELERATE_ROOT = SCRIPT_REPO_ROOT / "external" / "ipfs_accelerate"

if str(BOOTSTRAP_IPFS_ACCELERATE_ROOT) not in sys.path:
    sys.path.insert(0, str(BOOTSTRAP_IPFS_ACCELERATE_ROOT))

from ipfs_accelerate_py.agent_supervisor.wrapper_utils import (  # noqa: E402
    agent_supervisor_namespace_paths,
    repo_root_from_env,
)


REPO_ROOT = repo_root_from_env(fallback=SCRIPT_REPO_ROOT)
MULTI_SUPERVISOR_ENV_DEFAULTS = {
    "PYTHONUNBUFFERED": "1",
    "CODEX_MERGE_RESOLVER_TIMEOUT_SECONDS": "60",
    "PREFER_COPILOT_MERGE_RESOLVER": "1",
}


from ipfs_accelerate_py.agent_supervisor.multi_supervisor_runner import (  # noqa: E402
    ConfiguredMultiSupervisorCliRunner,
    ConfiguredMultiSupervisorLauncher,
    build_repo_implementation_multi_supervisor_launcher,
    implementation_supervisor_namespace_track_config,
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
        resolver_script_path="scripts/llm_merge_resolver_fallback.sh",
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

    return build_launcher().run(sys.argv[1:] if argv is None else argv)


if __name__ == "__main__":
    raise SystemExit(main())
