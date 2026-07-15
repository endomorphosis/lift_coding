from __future__ import annotations

import json
import os
import socket
import sys
from pathlib import Path

import pytest

SCRIPTS_DIR = Path(__file__).resolve().parents[1] / "scripts"
sys.path.insert(0, str(SCRIPTS_DIR))

from swissknife_checkout_lease_guard import (  # noqa: E402
    SwissKnifeLeaseGuardError,
    require_swissknife_checkout_lease,
)

LANES = {"test-lane": "implementation_plan/docs/test.todo.md"}


def _start_ticks(pid: int) -> str:
    source = Path(f"/proc/{pid}/stat").read_text(encoding="utf-8")
    return source[source.rfind(") ") + 2 :].split()[19]


def _lease_environment(tmp_path: Path) -> dict[str, str]:
    lease_id = "00000000-0000-4000-8000-000000000001"
    identity = {
        "method": "linux-procfs-starttime-v1",
        "startTicks": _start_ticks(os.getpid()),
    }
    owner = {
        "schemaVersion": 1,
        "leaseId": lease_id,
        "namespace": {"name": "swissknife-supervisor-checkout-lease-v1"},
        "owner": {
            "pid": os.getpid(),
            "hostname": socket.gethostname(),
            "processIdentity": identity,
        },
        "lane": {"id": "test-lane", "board": LANES["test-lane"]},
        "childPid": os.getpid(),
        "childProcessIdentity": identity,
        "childProcessGroupId": os.getpgrp(),
    }
    owner_file = tmp_path / "owner.json"
    owner_file.write_text(json.dumps(owner), encoding="utf-8")
    return {
        "IPFS_ACCELERATE_AGENT_MAX_DIRTY_ATTEMPTS": "0",
        "SWISSKNIFE_CHECKOUT_LEASE_ID": lease_id,
        "SWISSKNIFE_CHECKOUT_LEASE_LANE": "test-lane",
        "SWISSKNIFE_CHECKOUT_LEASE_BOARD": LANES["test-lane"],
        "SWISSKNIFE_CHECKOUT_LEASE_OWNER_FILE": str(owner_file),
    }


def test_observation_does_not_require_writer_lease() -> None:
    require_swissknife_checkout_lease(["--no-implement", "--once"], allowed_lanes=LANES, environ={})


def test_direct_implementation_without_lease_is_refused() -> None:
    with pytest.raises(SwissKnifeLeaseGuardError, match="foreground child"):
        require_swissknife_checkout_lease(
            ["--implement", "--no-worktree-reconciliation"],
            allowed_lanes=LANES,
            environ={"IPFS_ACCELERATE_AGENT_MAX_DIRTY_ATTEMPTS": "0"},
        )


@pytest.mark.skipif(not Path("/proc/self/stat").exists(), reason="SWR-135 v1 requires Linux procfs")
def test_matching_live_foreground_lease_is_accepted(tmp_path: Path) -> None:
    require_swissknife_checkout_lease(
        ["--implement"],
        allowed_lanes=LANES,
        environ=_lease_environment(tmp_path),
    )


@pytest.mark.skipif(not Path("/proc/self/stat").exists(), reason="SWR-135 v1 requires Linux procfs")
def test_stale_or_mismatched_identity_fails_closed(tmp_path: Path) -> None:
    environment = _lease_environment(tmp_path)
    owner_path = Path(environment["SWISSKNIFE_CHECKOUT_LEASE_OWNER_FILE"])
    owner = json.loads(owner_path.read_text(encoding="utf-8"))
    owner["owner"]["processIdentity"]["startTicks"] = "1"
    owner_path.write_text(json.dumps(owner), encoding="utf-8")
    with pytest.raises(SwissKnifeLeaseGuardError, match="identity no longer matches"):
        require_swissknife_checkout_lease(
            ["--implement"],
            allowed_lanes=LANES,
            environ=environment,
        )
