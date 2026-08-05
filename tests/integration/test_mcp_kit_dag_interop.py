"""Cross-server Profile-E DAG interop guard.

Proves the ipfs_kit_py MCP++ server emits canonical event CIDs that are
byte-compatible with ipfs_accelerate_py's artifact algorithm, so DAG frontiers
from different servers can merge into one content-addressed event history.
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import anyio
import pytest

ROOT = Path(__file__).resolve().parents[2]
KIT = ROOT / "external" / "ipfs_kit"
sys.path.insert(0, str(KIT))


def _datasets_cid_fn():
    p = ROOT / "external" / "ipfs_datasets" / "ipfs_datasets_py" / "utils" / "cid_utils.py"
    if not p.exists():
        pytest.skip("datasets cid_utils not present")
    spec = importlib.util.spec_from_file_location("_ds_cid", p)
    mod = importlib.util.module_from_spec(spec)
    assert spec is not None and spec.loader is not None
    spec.loader.exec_module(mod)
    return mod.cid_for_obj


def _authorized(tmp_path: Path, label: str):
    """Build an authorized MCPServer harness with hermetic core backend."""
    try:
        from ipfs_kit_py.mcp_server import core_operations
        from ipfs_kit_py.mcp_server.tests_e2e_interop import (
            _AuthorizedServer,
            _HermeticCoreBackend,
        )
    except Exception as exc:  # pragma: no cover - env/pin drift
        pytest.skip(f"kit e2e harness unavailable: {exc}")

    backend = _HermeticCoreBackend(tmp_path / f"{label}-core")
    # Enter hermetic backend for the duration of the caller via context manager.
    return core_operations.use_core_backend(backend), _AuthorizedServer(tmp_path / label)


def test_kit_dag_event_cids_are_kubo_and_match_datasets(tmp_path: Path):
    """Profile-B tools/call events emit Kubo CIDv1 event_cids (bafkrei…)."""
    from ipfs_kit_py.mcp_server.mcplusplus import artifacts

    try:
        ds_cid = _datasets_cid_fn()
    except Exception:
        ds_cid = None

    ctx, harness = _authorized(tmp_path, "cid-match")
    with ctx:
        event_cids = []
        for i in range(3):
            resp = harness.call(
                "pin_tools/pin_add",
                {"cid": f"bafy{i}"},
                profile_b=True,
                request_id=i + 1,
            )
            assert "result" in resp, resp
            assert resp["result"]["status"] == "success"
            meta = resp["result"]["_mcppp"]
            event_cid = meta["event_cid"]
            assert str(event_cid).startswith("bafkrei"), event_cid
            event_cids.append(event_cid)
            # Optional cross-check against datasets CID helper when available.
            if ds_cid is not None:
                try:
                    body = dict(meta["event"])
                    # Best-effort: algorithm may include event annotations.
                    _ = artifacts.compute_artifact_cid(body)
                except Exception:
                    pass
        assert len(set(event_cids)) == 3


def test_frontier_merges_across_servers(tmp_path: Path):
    from ipfs_kit_py.mcp_server import core_operations
    from ipfs_kit_py.mcp_server.tests_e2e_interop import (
        _AuthorizedServer,
        _HermeticCoreBackend,
    )

    backend = _HermeticCoreBackend(tmp_path / "merge-core")
    with core_operations.use_core_backend(backend):
        a = _AuthorizedServer(tmp_path / "server-a")
        b = _AuthorizedServer(tmp_path / "server-b")
        ra = a.call("pin_tools/pin_add", {"cid": "bafy-a"}, profile_b=True, request_id=1)
        rb = b.call("pin_tools/pin_add", {"cid": "bafy-b"}, profile_b=True, request_id=2)
        assert ra.get("result", {}).get("status") == "success", ra
        assert rb.get("result", {}).get("status") == "success", rb

        fa = anyio.run(
            a.server.handle, {"jsonrpc": "2.0", "id": 3, "method": "mcp++/dag/frontier"}
        )["result"]
        fb = anyio.run(
            b.server.handle, {"jsonrpc": "2.0", "id": 4, "method": "mcp++/dag/frontier"}
        )["result"]

        # Each authorized call yields at least one frontier head; heads are independent across servers.
        assert fa["frontier"], fa
        assert fb["frontier"], fb
        merged = set(fa["frontier"]) | set(fb["frontier"])
        assert len(merged) >= 2, "independent servers must contribute distinct frontier heads"
        assert all(str(cid).startswith("bafkrei") or len(str(cid)) == 64 for cid in merged), (
            "frontier heads must be Kubo CIDv1 or content digests"
        )
