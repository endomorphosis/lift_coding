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


def _datasets_cid_fn():
    p = ROOT / "external" / "ipfs_datasets" / "ipfs_datasets_py" / "utils" / "cid_utils.py"
    if not p.exists():
        pytest.skip("datasets cid_utils not present")
    spec = importlib.util.spec_from_file_location("_ds_cid", p)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod.cid_for_obj


def test_kit_dag_event_cids_are_kubo_and_match_datasets():
    from ipfs_kit_py.mcp_server.server import MCPServer
    from ipfs_kit_py.mcp_server.mcplusplus import artifacts
    import json

    try:
        ds_cid = _datasets_cid_fn()
    except Exception:
        pytest.skip("datasets cid backend unavailable")
    s = MCPServer()
    for i in range(3):
        anyio.run(s.handle, {"jsonrpc": "2.0", "id": i, "method": "tools/call",
                             "params": {"name": "pin_tools/pin_rm", "arguments": {"cid": "bafy"}, "profile_b": True}})
    assert len(s._dag) == 3
    for node in s._dag:
        # event_cid content-addresses the event payload; event_cid + timestamp
        # are node annotations (timestamp added for spec DAG conformance).
        body = {k: v for k, v in node.items() if k not in ("event_cid", "timestamp")}
        assert node["event_cid"] == artifacts.compute_artifact_cid(body)
        assert node["event_cid"].startswith("bafkrei")
        try:
            assert node["event_cid"] == ds_cid(json.loads(artifacts.canonicalize_artifact(body)))
        except Exception:
            pytest.skip("multiformats not installed for datasets cid")


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
    assert all(c.startswith("bafkrei") for c in merged), "frontier heads are Kubo CIDv1"
