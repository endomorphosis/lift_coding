#!/usr/bin/env python3
"""Monitor and recover only the registered SVF systemd service.

The reusable implementation lives in ipfs_accelerate_py. This entrypoint
supplies the workspace import bootstrap and the campaign's pinned config.
"""
from __future__ import annotations

import sys

from lift_ipfs_accelerate_bootstrap import bootstrap_ipfs_accelerate


def main(argv: list[str] | None = None) -> int:
    args = list(sys.argv[1:] if argv is None else argv)
    if "--config" not in args:
        args = ["--config", "config/swissknife_visual_functional_watchdog.json", *args]
    bootstrap_ipfs_accelerate(__file__, include_script_dir=True)
    from ipfs_accelerate_py.agent_supervisor.rescue.leased_service_watchdog import main as observe
    return observe(args)


if __name__ == "__main__":
    raise SystemExit(main())
