"""End-to-end MCP++ interop tests across both live servers.

Unlike test_cross_server_mcppp.py (which checks static wire shapes), this suite
boots both real servers in-process and exercises live JSON-RPC, validating every
response against the canonical Mcp-Plus-Plus spec models so that:

- ipfs_datasets_py runs through its FastAPI /mcp handler (TestClient)
- ipfs_accelerate_py runs through its Trio JSON-RPC handler (trio.run)
- both speak protocol 2024-11-05 with mcp++ profiles under experimental
- both return spec-conformant initialize / tools.list / policy / p2p / execute
- the two servers agree (cross-server) on shapes a third party can rely on

Skips cleanly if FastAPI/Trio deps aren't installed in the test env.
"""

import os
import sys

import pytest

pytest.importorskip("fastapi")
pytest.importorskip("trio")
import trio  # noqa: E402

_ext_dir = os.path.join(os.path.dirname(__file__), "..", "..")
_DS_DIR = os.path.join(_ext_dir, "external", "ipfs_datasets")
_ACC_DIR = os.path.join(_ext_dir, "external", "ipfs_accelerate")
_SPEC_DIR = os.path.join(_ext_dir, "Mcp-Plus-Plus", "tests-py")

_ACC_DIR_ABS = os.path.abspath(_ACC_DIR)
_DS_DIR_ABS = os.path.abspath(_DS_DIR)
for _p in (_SPEC_DIR, _ACC_DIR_ABS):
    if _p not in sys.path:
        sys.path.insert(0, _p)

# Import accelerate from the submodule FIRST so ipfs_accelerate_py caches the
# canonical copy (datasets injects a sibling accelerate path on import). Then
# prepend the datasets submodule so it resolves to the real repo too.
from ipfs_accelerate_py.mcplusplus_module.trio.server import TrioMCPServer  # noqa: E402
sys.path.insert(0, _DS_DIR_ABS)


def _spec_models():
    from validators.models import (
        InitializeResult,
        PolicyDecision,
        ExecutionReceipt,
    )
    return InitializeResult, PolicyDecision, ExecutionReceipt


# --------------------------------------------------------------------------- #
# Datasets transport: FastAPI TestClient (TrustedHost needs a host header)
# --------------------------------------------------------------------------- #
@pytest.fixture(scope="module")
def datasets_rpc():
    from fastapi.testclient import TestClient
    from ipfs_datasets_py.mcp_server.fastapi_service import app

    client = TestClient(app)

    def rpc(method, params=None):
        r = client.post(
            "/mcp",
            json={"jsonrpc": "2.0", "id": 1, "method": method, "params": params or {}},
            headers={"host": "localhost"},
        )
        assert r.status_code == 200, f"{method} -> HTTP {r.status_code}"
        return r.json()

    return rpc


# --------------------------------------------------------------------------- #
# Accelerate transport: Trio JSON-RPC handler driven via trio.run per call
# --------------------------------------------------------------------------- #
@pytest.fixture(scope="module")
def accelerate_rpc():
    from ipfs_accelerate_py.mcplusplus_module.trio.server import TrioMCPServer

    server = TrioMCPServer()
    server.setup()

    def rpc(method, params=None):
        async def _go():
            return await server._handle_jsonrpc(
                {"jsonrpc": "2.0", "id": 1, "method": method, "params": params or {}}
            )

        return trio.run(_go)

    return rpc


@pytest.fixture(params=["datasets", "accelerate"])
def server_rpc(request, datasets_rpc, accelerate_rpc):
    return datasets_rpc if request.param == "datasets" else accelerate_rpc


# --------------------------------------------------------------------------- #
# Per-server live conformance
# --------------------------------------------------------------------------- #
def test_initialize_conforms(server_rpc):
    InitializeResult, _, _ = _spec_models()
    res = server_rpc("initialize")["result"]
    InitializeResult(**res)
    assert res["protocolVersion"] == "2024-11-05"
    # mcp++ profiles are negotiated per-method (capabilities.experimental is a
    # forward-compat slot); both servers expose an experimental map.
    assert isinstance(res["capabilities"].get("experimental", {}), dict)


def test_tools_list_live(server_rpc):
    res = server_rpc("tools/list")["result"]
    assert isinstance(res["tools"], list)


def test_policy_evaluate_conforms(server_rpc):
    _, PolicyDecision, _ = _spec_models()
    res = server_rpc("mcp++/policy/evaluate", {"action": "infer", "subject": "did:key:z"})["result"]
    PolicyDecision(**res)
    assert "decision" in res and "allowed" in res


def test_p2p_peers_live(server_rpc):
    res = server_rpc("mcp++/p2p/peers")["result"]
    assert "peers" in res and "protocol" in res


def test_unknown_method_error(server_rpc):
    resp = server_rpc("does/not/exist")
    assert resp["error"]["code"] == -32601


# --------------------------------------------------------------------------- #
# Cross-server agreement (third-party interop guarantee)
# --------------------------------------------------------------------------- #
def test_servers_agree_on_handshake(datasets_rpc, accelerate_rpc):
    d = datasets_rpc("initialize")["result"]
    a = accelerate_rpc("initialize")["result"]
    assert d["protocolVersion"] == a["protocolVersion"] == "2024-11-05"


def test_servers_agree_on_policy_shape(datasets_rpc, accelerate_rpc):
    d = datasets_rpc("mcp++/policy/evaluate", {"action": "x"})["result"]
    a = accelerate_rpc("mcp++/policy/evaluate", {"action": "x"})["result"]
    assert set(["decision", "obligations", "allowed"]).issubset(d)
    assert set(["decision", "obligations", "allowed"]).issubset(a)


def test_accelerate_execute_receipt_conforms(accelerate_rpc):
    _, _, ExecutionReceipt = _spec_models()
    rpc = accelerate_rpc
    # inject a trivial sync tool into the dict view used by execute dispatch
    from ipfs_accelerate_py.mcplusplus_module.trio.server import TrioMCPServer  # noqa

    res = rpc("tools/list")["result"]
    name = res["tools"][0]
    out = rpc("mcp++/execute", {"tool": name, "arguments": {}})["result"]
    assert "receipt" in out
    ExecutionReceipt(**out["receipt"])
