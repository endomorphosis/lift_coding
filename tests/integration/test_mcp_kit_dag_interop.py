"""Cross-server Profile-E DAG interop guard.

Proves the ipfs_kit_py MCP++ server emits canonical event CIDs that are
byte-compatible with ipfs_accelerate_py's artifact algorithm, so DAG frontiers
from different servers can merge into one content-addressed event history.
"""
import importlib.util
import sys
from pathlib import Path

import anyio
import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "external" / "ipfs_kit"))


def _accel_cid_fn():
    p = ROOT / "external" / "ipfs_accelerate" / "ipfs_accelerate_py" / "mcp_server" / "mcplusplus" / "artifacts.py"
    if not p.exists():
        pytest.skip("accelerate artifacts not present")
    spec = importlib.util.spec_from_file_location("_acc_art", p)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod.compute_artifact_cid


def test_kit_dag_event_cids_match_accelerate():
    from ipfs_kit_py.mcp_server.server import MCPServer
    from ipfs_kit_py.mcp_server.mcplusplus import artifacts

    accel_cid = _accel_cid_fn()
    s = MCPServer()
    for i in range(3):
        anyio.run(s.handle, {"jsonrpc": "2.0", "id": i, "method": "tools/call",
                             "params": {"name": "pin_tools/pin_rm", "arguments": {"cid": "bafy"}, "profile_b": True}})
    assert len(s._dag) == 3
    for node in s._dag:
        recomputed = artifacts.compute_artifact_cid({k: v for k, v in node.items() if k != "event_cid"})
        assert node["event_cid"] == recomputed
        assert node["event_cid"] == accel_cid({k: v for k, v in node.items() if k != "event_cid"})


def test_frontier_merges_across_servers():
    from ipfs_kit_py.mcp_server.server import MCPServer

    a, b = MCPServer(), MCPServer()
    anyio.run(a.handle, {"jsonrpc": "2.0", "id": 1, "method": "tools/call",
                         "params": {"name": "pin_tools/pin_rm", "arguments": {"cid": "x"}, "profile_b": True}})
    anyio.run(b.handle, {"jsonrpc": "2.0", "id": 2, "method": "tools/call",
                         "params": {"name": "pin_tools/pin_rm", "arguments": {"cid": "x"}, "profile_b": True}})
    fa = anyio.run(a.handle, {"jsonrpc": "2.0", "id": 3, "method": "mcp++/dag/frontier"})["result"]
    fb = anyio.run(b.handle, {"jsonrpc": "2.0", "id": 4, "method": "mcp++/dag/frontier"})["result"]
    merged = set(fa["frontier"]) | set(fb["frontier"])
    assert len(merged) == 2, "two independent events form a mergeable two-head frontier"
    assert all(c.startswith("cidv1-sha256-") for c in merged), "frontier heads are canonical CIDs"
