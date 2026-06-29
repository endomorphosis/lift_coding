"""Cross-server Profile-C/D interop guard.

The ipfs_kit_py delegation validator must agree with ipfs_accelerate_py's
canonical validator on allow/deny + reason for the unsigned path, so third
parties get identical authorization decisions regardless of server.
"""
import importlib.util
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "external" / "ipfs_kit"))


def _accel_validate():
    p = ROOT / "external" / "ipfs_accelerate" / "ipfs_accelerate_py" / "mcp_server" / "mcplusplus" / "delegation.py"
    if not p.exists():
        pytest.skip("accelerate delegation not present")
    spec = importlib.util.spec_from_file_location("_acc_deleg", p)
    mod = importlib.util.module_from_spec(spec)
    sys.modules["_acc_deleg"] = mod
    spec.loader.exec_module(mod)
    return mod.validate_raw_delegation_chain


CHAINS = [
    [{"issuer": "did:a", "audience": "did:b", "capabilities": [{"resource": "ipfs", "ability": "*"}]},
     {"issuer": "did:b", "audience": "did:c", "capabilities": [{"resource": "ipfs", "ability": "read"}]}],
    [{"issuer": "did:a", "audience": "did:b", "capabilities": [{"resource": "ipfs", "ability": "read"}]},
     {"issuer": "did:b", "audience": "did:c", "capabilities": [{"resource": "ipfs", "ability": "write"}]}],
    [{"issuer": "did:a", "audience": "did:b", "capabilities": [{"resource": "ipfs", "ability": "read"}]},
     {"issuer": "did:X", "audience": "did:c", "capabilities": [{"resource": "ipfs", "ability": "read"}]}],
]


@pytest.mark.parametrize("chain", CHAINS)
def test_kit_and_accelerate_agree(chain):
    from ipfs_kit_py.mcp_server.mcplusplus import delegation as kit
    accel = _accel_validate()
    kr = kit.validate_raw_delegation_chain(raw_chain=chain, resource="ipfs", ability="read", actor="did:c")
    ar = accel(raw_chain=chain, resource="ipfs", ability="read", actor="did:c", require_signatures=False)
    a = ar.to_dict() if hasattr(ar, "to_dict") else ar
    assert kr["allowed"] == a["allowed"], f"allow mismatch: {kr} vs {a}"
    assert kr["reason"] == a["reason"], f"reason mismatch: {kr} vs {a}"
