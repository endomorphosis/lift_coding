"""ipfs_kit_py MCP++ output must pass the canonical Mcp-Plus-Plus validators.

The Mcp-Plus-Plus submodule owns the packet specification. A live tool call on
the kit server emits a `_mcppp` execution envelope + receipt + DAG event; these
must validate against the canonical Python validators so third parties can
interoperate with the kit server as a conformant MCP++ peer.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
KIT = ROOT / "external" / "ipfs_kit"
SPEC = ROOT / "Mcp-Plus-Plus" / "tests-py"

for path in (KIT, SPEC):
    if not path.exists():
        pytest.skip(f"{path} not present", allow_module_level=True)
    sys.path.insert(0, str(path))

anyio = pytest.importorskip("anyio")


def _meta(tmp_path: Path):
    try:
        from ipfs_kit_py.mcp_server import core_operations
        from ipfs_kit_py.mcp_server.tests_e2e_interop import (
            _AuthorizedServer,
            _HermeticCoreBackend,
        )
    except Exception as exc:  # pragma: no cover
        pytest.skip(f"kit e2e harness unavailable: {exc}")

    backend = _HermeticCoreBackend(tmp_path / "core")
    with core_operations.use_core_backend(backend):
        harness = _AuthorizedServer(tmp_path / "srv")
        resp = harness.call(
            "pin_tools/pin_add",
            {"cid": "bafy"},
            profile_b=True,
            request_id=1,
        )
    assert "result" in resp, resp
    assert "_mcppp" in resp["result"], resp
    return resp["result"]["_mcppp"], harness


def test_envelope_passes_spec_validator(tmp_path: Path):
    from validators.cid_artifacts import CIDExecutionValidator

    meta, _ = _meta(tmp_path)
    res = CIDExecutionValidator().validate_execution_envelope(meta)
    assert res.is_valid, res.errors


def test_receipt_passes_spec_validator(tmp_path: Path):
    from validators.cid_artifacts import CIDExecutionValidator

    meta, _ = _meta(tmp_path)
    res = CIDExecutionValidator().validate_execution_receipt(meta)
    assert res.is_valid, res.errors


def test_dag_event_passes_spec_validator(tmp_path: Path):
    from validators.event_dag import EventDAGValidator

    meta, _ = _meta(tmp_path)
    event = {"event_cid": meta["event_cid"], "timestamp": "x", **meta["event"]}
    res = EventDAGValidator().validate_event(event)
    assert res.is_valid, res.errors
