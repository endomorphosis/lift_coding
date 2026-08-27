"""PCSM executor bootstrap must not SIGTERM the supervisor on one stalled peer."""

from __future__ import annotations

import importlib.util
import os
import socket
import time
from pathlib import Path
from types import SimpleNamespace

import pytest

ROOT = Path(__file__).resolve().parents[1]
OPERATOR = ROOT / "scripts" / "run_agent_supervisor_proof_carrying_semantic_minification.py"


def _load_operator():
    spec = importlib.util.spec_from_file_location("pcsm_operator", OPERATOR)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.mark.timeout(10)
def test_bootstrap_request_timeout_does_not_sigterm_the_supervisor(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    operator = _load_operator()
    killed: list[tuple[int, int]] = []
    monkeypatch.setattr(
        operator.os,
        "kill",
        lambda pid, sig: killed.append((int(pid), int(sig))),
    )
    import ipfs_accelerate_py.agent_supervisor.task_sources.state_owner_bootstrap as bootstrap

    def _timeout(_channel: socket.socket) -> dict[str, object]:
        raise TimeoutError("stalled executor bootstrap request")

    monkeypatch.setattr(bootstrap, "_receive_frame", _timeout)

    listener = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    address = "\0pcsm-broker-timeout-" + os.urandom(8).hex()
    listener.bind(address)
    listener.listen(1)
    board = SimpleNamespace(
        max_lanes=4,
        board_namespace="proof-carrying-semantic-minification-v1",
    )
    broker = operator._ExecutorBootstrapBroker(
        channel=listener,
        server=SimpleNamespace(
            revoke_typed_client_grant=lambda _grant: None,
            identity=SimpleNamespace(server_id="server:test"),
        ),
        board=board,
        paths={"runtime": tmp_path},
        initial_execution_route_policy=SimpleNamespace(
            policy_id="policy:test",
            public_summary=lambda: {},
            to_dict=lambda: {},
        ),
    )
    peer = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    broker.start()
    try:
        peer.connect(address)
        time.sleep(0.5)
        assert killed == []
        assert broker.failure == ""
        assert broker._thread.is_alive() is True
    finally:
        peer.close()
        broker.stop()
