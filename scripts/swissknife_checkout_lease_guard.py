#!/usr/bin/env python3
"""Fail-closed verification for SwissKnife-writing supervisor entrypoints.

The Node lease wrapper publishes an unforgeable-by-accident ownership record
and places the foreground command in the recorded process group.  Repository
supervisor wrappers call this module before enabling implementation so an old
direct launch cannot silently bypass SWR-135.
"""

from __future__ import annotations

import json
import os
import socket
from collections.abc import Mapping, Sequence
from pathlib import Path

LEASE_NAMESPACE = "swissknife-supervisor-checkout-lease-v1"
DIRTY_ATTEMPTS_ENV = "IPFS_ACCELERATE_AGENT_MAX_DIRTY_ATTEMPTS"
LEASE_ID_ENV = "SWISSKNIFE_CHECKOUT_LEASE_ID"
LEASE_LANE_ENV = "SWISSKNIFE_CHECKOUT_LEASE_LANE"
LEASE_BOARD_ENV = "SWISSKNIFE_CHECKOUT_LEASE_BOARD"
LEASE_OWNER_FILE_ENV = "SWISSKNIFE_CHECKOUT_LEASE_OWNER_FILE"


class SwissKnifeLeaseGuardError(RuntimeError):
    """Implementation was requested without the matching live checkout lease."""


def _linux_start_ticks(pid: int) -> str:
    source = Path(f"/proc/{pid}/stat").read_text(encoding="utf-8")
    command_end = source.rfind(") ")
    if command_end < 0:
        raise SwissKnifeLeaseGuardError(f"cannot parse process identity for PID {pid}")
    fields_from_state = source[command_end + 2 :].split()
    if len(fields_from_state) <= 19 or not fields_from_state[19].isdigit():
        raise SwissKnifeLeaseGuardError(f"process identity for PID {pid} has no start ticks")
    return fields_from_state[19]


def _verify_live_linux_process(pid: object, identity: object, label: str) -> None:
    if not isinstance(pid, int) or pid <= 0 or not isinstance(identity, dict):
        raise SwissKnifeLeaseGuardError(f"lease {label} identity is incomplete")
    if identity.get("method") != "linux-procfs-starttime-v1":
        raise SwissKnifeLeaseGuardError(f"lease {label} identity method is not supported")
    try:
        os.kill(pid, 0)
        current_ticks = _linux_start_ticks(pid)
    except (OSError, ValueError) as exc:
        raise SwissKnifeLeaseGuardError(f"lease {label} PID {pid} is not verifiably live") from exc
    if current_ticks != identity.get("startTicks"):
        raise SwissKnifeLeaseGuardError(f"lease {label} PID {pid} identity no longer matches")


def _implementation_requested(argv: Sequence[str]) -> bool:
    # --no-implement is mutually exclusive in the shared parser.  Checking the
    # positive flag avoids imposing a writer lease on read-only observation.
    return "--implement" in argv and "--no-implement" not in argv


def require_swissknife_checkout_lease(
    argv: Sequence[str],
    *,
    allowed_lanes: Mapping[str, str],
    environ: Mapping[str, str] | None = None,
) -> None:
    """Require a matching live lease when ``argv`` enables implementation.

    ``allowed_lanes`` maps inventory lane IDs to their canonical board paths.
    The function returns without side effects for observation-only commands.
    """

    if not _implementation_requested(argv):
        return
    env = os.environ if environ is None else environ
    if env.get(DIRTY_ATTEMPTS_ENV) != "0":
        raise SwissKnifeLeaseGuardError(f"{DIRTY_ATTEMPTS_ENV} must be exactly 0")

    lease_id = env.get(LEASE_ID_ENV, "")
    lane_id = env.get(LEASE_LANE_ENV, "")
    board = env.get(LEASE_BOARD_ENV, "")
    owner_file_value = env.get(LEASE_OWNER_FILE_ENV, "")
    if not lease_id or lane_id not in allowed_lanes or not owner_file_value:
        raise SwissKnifeLeaseGuardError(
            "SwissKnife implementation must be the foreground child of "
            "swissknife/scripts/swissknife-checkout-lease.mjs --run"
        )
    if board != allowed_lanes[lane_id]:
        raise SwissKnifeLeaseGuardError(
            f"lease board {board!r} does not match registered lane {lane_id!r}"
        )

    owner_file = Path(owner_file_value)
    try:
        owner = json.loads(owner_file.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise SwissKnifeLeaseGuardError("lease owner metadata is unavailable or invalid") from exc

    if not isinstance(owner, dict):
        raise SwissKnifeLeaseGuardError("lease owner metadata must be a JSON object")
    recorded_lane = owner.get("lane")
    recorded_owner = owner.get("owner")
    namespace = owner.get("namespace")
    if (
        owner.get("schemaVersion") != 1
        or owner.get("leaseId") != lease_id
        or not isinstance(namespace, dict)
        or namespace.get("name") != LEASE_NAMESPACE
        or not isinstance(recorded_lane, dict)
        or recorded_lane.get("id") != lane_id
        or recorded_lane.get("board") != board
        or not isinstance(recorded_owner, dict)
        or recorded_owner.get("hostname") != socket.gethostname()
    ):
        raise SwissKnifeLeaseGuardError("lease owner metadata does not match this supervisor lane")

    if os.name != "posix" or not Path("/proc/self/stat").exists():
        raise SwissKnifeLeaseGuardError("SWR-135 process identity guard requires Linux procfs")
    _verify_live_linux_process(
        recorded_owner.get("pid"), recorded_owner.get("processIdentity"), "wrapper"
    )
    _verify_live_linux_process(owner.get("childPid"), owner.get("childProcessIdentity"), "child")
    process_group = owner.get("childProcessGroupId")
    if not isinstance(process_group, int) or process_group <= 0 or os.getpgrp() != process_group:
        raise SwissKnifeLeaseGuardError(
            "supervisor is not in the lease holder's protected foreground process group"
        )


__all__ = [
    "SwissKnifeLeaseGuardError",
    "require_swissknife_checkout_lease",
]
