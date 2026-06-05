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
    apply_env_defaults,
    build_runtime_environment_callbacks,
    env_str,
    repo_external_package_roots,
    repo_root_from_env,
)


REPO_ROOT = repo_root_from_env(fallback=SCRIPT_REPO_ROOT)
IPFS_ACCELERATE_ROOT, IPFS_DATASETS_ROOT = repo_external_package_roots(
    REPO_ROOT,
    ("ipfs_accelerate", "ipfs_datasets"),
)

VAI_MGW_HAO_IMPLEMENTATION_TRACK_CONFIGS = (
    ("VAI", "scripts/virtual_ai_os_todo_supervisor.py", "data/virtual_ai_os/state", "virtual_ai_os"),
    (
        "MGW",
        "scripts/meta_glasses_display_todo_supervisor.py",
        "data/meta_glasses_display_widgets/state",
        "meta_glasses_display",
    ),
    (
        "HAO",
        "scripts/hallucinate_multimodal_control_todo_supervisor.py",
        "data/hallucinate_multimodal_control/state",
        "hallucinate_multimodal_control",
    ),
)


_RUNTIME_ENVIRONMENT = build_runtime_environment_callbacks(
    REPO_ROOT,
    (IPFS_ACCELERATE_ROOT, IPFS_DATASETS_ROOT),
)
MULTI_SUPERVISOR_ENV_DEFAULTS = {
    "PYTHONUNBUFFERED": "1",
    "CODEX_MERGE_RESOLVER_TIMEOUT_SECONDS": "60",
    "PREFER_COPILOT_MERGE_RESOLVER": "1",
}


def configure_environment() -> None:
    """Apply lift runtime defaults before launching child supervisor processes."""

    apply_env_defaults(MULTI_SUPERVISOR_ENV_DEFAULTS)
    _RUNTIME_ENVIRONMENT.ensure_pythonpath()


configure_environment()

from ipfs_accelerate_py.agent_supervisor.multi_supervisor_runner import (  # noqa: E402
    ConfiguredMultiSupervisorCliRunner,
    build_configured_multi_supervisor_cli_runner,
    implementation_supervisor_compact_track_specs,
    utc_run_stamp,
)


VAI_MGW_HAO_IMPLEMENTATION_TRACKS = implementation_supervisor_compact_track_specs(
    VAI_MGW_HAO_IMPLEMENTATION_TRACK_CONFIGS
)


def build_runner() -> ConfiguredMultiSupervisorCliRunner:
    """Return the configured reusable runner for this repository's tracks."""

    resolver_command = f"bash {REPO_ROOT / 'scripts' / 'llm_merge_resolver_fallback.sh'}"
    return build_configured_multi_supervisor_cli_runner(
        repo_root=REPO_ROOT,
        duration_seconds=env_str("DURATION_SECONDS", "28800"),
        stamp=env_str("STAMP", utc_run_stamp()),
        master_dir="data/agent_supervisor",
        label="VAI/MGW/HAO supervisor run",
        implementation_supervisor_defaults=True,
        implementation_supervisor_command=resolver_command,
        implementation_tracks=VAI_MGW_HAO_IMPLEMENTATION_TRACKS,
    )


def main(argv: Sequence[str] | None = None) -> int:
    """Run the configured VAI/MGW/HAO multi-supervisor CLI."""

    return build_runner().run(sys.argv[1:] if argv is None else argv)


if __name__ == "__main__":
    raise SystemExit(main())
