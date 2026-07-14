#!/usr/bin/env python3
"""Lease-enforcing entrypoint for direct SwissKnife supervisor boards."""

from __future__ import annotations

import sys
from collections.abc import Sequence

from lift_ipfs_accelerate_bootstrap import bootstrap_ipfs_accelerate
from swissknife_checkout_lease_guard import (
    SwissKnifeLeaseGuardError,
    require_swissknife_checkout_lease,
)

_PREIMPORT_BOOTSTRAP = bootstrap_ipfs_accelerate(__file__, include_script_dir=True)

from ipfs_accelerate_py.agent_supervisor.todo_daemon.implementation_supervisor import (  # noqa: E402
    main as implementation_supervisor_main,
)

LEASED_BOARDS = {
    "all-tools": "implementation_plan/docs/37-swissknife-virtual-desktop-ipfs-mcp-orb-meta-glasses-plan-2026-07-07.md",
    "refactor": "implementation_plan/docs/38-swissknife-repository-refactoring-plan-2026-07-08.todo.md",
    "mcpplusplus-profile-g": "implementation_plan/docs/38-mcpplusplus-risk-consensus-scheduling-p2p-plan-2026-07-12.md",
    "mcpplusplus-profile-h": "implementation_plan/docs/41-mcpplusplus-profile-h-x402-payments-plan-2026-07-12.todo.md",
}


def main(argv: Sequence[str] | None = None) -> None:
    launch_args = list(sys.argv[1:] if argv is None else argv)
    require_swissknife_checkout_lease(
        launch_args,
        allowed_lanes=LEASED_BOARDS,
    )
    implementation_supervisor_main(launch_args)


if __name__ == "__main__":
    try:
        main()
    except SwissKnifeLeaseGuardError as exc:
        print(f"error: {exc}", file=sys.stderr)
        raise SystemExit(78) from None
