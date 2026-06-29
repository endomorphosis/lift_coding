"""ipfs_kit_py MCP++ output must pass the canonical Mcp-Plus-Plus validators.

The Mcp-Plus-Plus submodule owns the packet specification. A live tool call on
the kit server emits a `_mcppp` execution envelope + receipt + DAG event; these
must validate against the canonical Python validators so third parties can
interoperate with the kit server as a conformant MCP++ peer.
"""
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
KIT = ROOT / "external" / "ipfs_kit"
SPEC = ROOT / "Mcp-Plus-Plus" / "tests-py"

for p in (KIT, SPEC):
    if not p.exists():
        pytest.skip(f"{p} not present", allow_module_level=True)
    sys.path.insert(0, str(p))

anyio = pytest.importorskip("anyio")


def _meta():
    from ipfs_kit_py.mcp_server.server import MCPServer
    s = MCPServer()
    resp = anyio.run(s.handle, {"jsonrpc": "2.0", "id": 1, "method": "tools/call",
                                "params": {"name": "pin_tools/pin_rm",
                                           "arguments": {"cid": "bafy"},
                                           "profile_b": True}})
    return resp["result"]["_mcppp"], s


def test_envelope_passes_spec_validator():
    from validators.cid_artifacts import CIDExecutionValidator
    meta, _ = _meta()
    res = CIDExecutionValidator().validate_execution_envelope(meta)
    assert res.is_valid, res.errors


def test_receipt_passes_spec_validator():
    from validators.cid_artifacts import CIDExecutionValidator
    meta, _ = _meta()
    res = CIDExecutionValidator().validate_execution_receipt(meta)
    assert res.is_valid, res.errors


def test_dag_event_passes_spec_validator():
    from validators.event_dag import EventDAGValidator
    meta, srv = _meta()
    event = {"event_cid": meta["event_cid"], "timestamp": "x", **meta["event"]}
    res = EventDAGValidator().validate_event(event)
    assert res.is_valid, res.errors
