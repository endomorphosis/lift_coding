#!/usr/bin/env python3
"""Run the Hallucinate multimodal-control supervisor in implementation mode."""

from __future__ import annotations

import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
IPFS_ACCELERATE_ROOT = REPO_ROOT / "external" / "ipfs_accelerate"

if str(IPFS_ACCELERATE_ROOT) not in sys.path:
    sys.path.insert(0, str(IPFS_ACCELERATE_ROOT))

from ipfs_accelerate_py.agent_supervisor.todo_daemon.supervisor_runtime import (  # noqa: E402
    build_configured_implementation_supervisor_entrypoint,
)


def _supervisor_main(argv: list[str]) -> None:
    from hallucinate_multimodal_control_todo_supervisor import main as supervisor_main

    return supervisor_main(argv)


AUTOPILOT_ENTRYPOINT = build_configured_implementation_supervisor_entrypoint(_supervisor_main)


def with_autopilot_defaults(argv: list[str]) -> list[str]:
    return AUTOPILOT_ENTRYPOINT.with_defaults(argv)


def main(argv: list[str] | None = None) -> None:
    AUTOPILOT_ENTRYPOINT.run(argv)


if __name__ == "__main__":
    main()
