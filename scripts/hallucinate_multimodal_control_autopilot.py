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
    implementation_supervisor_args as _implementation_supervisor_args,
)


def with_autopilot_defaults(argv: list[str]) -> list[str]:
    return _implementation_supervisor_args(argv)


def main(argv: list[str] | None = None) -> None:
    args = with_autopilot_defaults(list(sys.argv[1:] if argv is None else argv))
    from hallucinate_multimodal_control_todo_supervisor import main as supervisor_main

    supervisor_main(args)


if __name__ == "__main__":
    main()
