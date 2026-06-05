#!/usr/bin/env python3
"""Run the lift-specific VAI/MGW/HAO supervisor tracks."""

from __future__ import annotations

import os
import sys
from pathlib import Path
from typing import Sequence


REPO_ROOT = Path(
    os.environ.get("REPO_ROOT") or Path(__file__).resolve().parents[1]
).resolve()
IPFS_ACCELERATE_ROOT = REPO_ROOT / "external" / "ipfs_accelerate"
IPFS_DATASETS_ROOT = REPO_ROOT / "external" / "ipfs_datasets"

VAI_MGW_HAO_IMPLEMENTATION_TRACKS = (
    "VAI|scripts/virtual_ai_os_todo_supervisor.py|data/virtual_ai_os/state|virtual_ai_os",
    "MGW|scripts/meta_glasses_display_todo_supervisor.py|data/meta_glasses_display_widgets/state|meta_glasses_display",
    "HAO|scripts/hallucinate_multimodal_control_todo_supervisor.py|data/hallucinate_multimodal_control/state|hallucinate_multimodal_control",
)


if str(IPFS_ACCELERATE_ROOT) not in sys.path:
    sys.path.insert(0, str(IPFS_ACCELERATE_ROOT))

from ipfs_accelerate_py.agent_supervisor.wrapper_utils import (  # noqa: E402
    apply_env_defaults,
    build_runtime_environment_callbacks,
    env_str,
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
    utc_run_stamp,
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
