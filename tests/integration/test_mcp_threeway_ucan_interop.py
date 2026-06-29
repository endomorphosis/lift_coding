"""Three-way Profile-C interop: kit, accelerate, datasets agree on auth.

The three independent UCAN implementations use different internal models (chain
vs CID-store) but must agree on the boundary decisions: a fully valid root->leaf
chain grants, and an empty/broken chain denies. Keeps third parties confident a
delegation accepted by one server is honored by the others.
"""
import importlib.util
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "external" / "ipfs_kit"))


def _load(name, rel):
    p = ROOT / "external" / rel
    if not p.exists():
        pytest.skip(f"{rel} not present")
    spec = importlib.util.spec_from_file_location(name, p)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


VALID = [
    {"issuer": "did:a", "audience": "did:b", "capabilities": [{"resource": "ipfs", "ability": "*"}]},
    {"issuer": "did:b", "audience": "did:c", "capabilities": [{"resource": "ipfs", "ability": "read"}]},
]


def _kit():
    from ipfs_kit_py.mcp_server.mcplusplus import delegation as kit
    return lambda ch: kit.validate_raw_delegation_chain(raw_chain=ch, resource="ipfs", ability="read", actor="did:c")["allowed"]


def _accel():
    m = _load("_acc_d", "ipfs_accelerate/ipfs_accelerate_py/mcp_server/mcplusplus/delegation.py")
    return lambda ch: m.validate_raw_delegation_chain(raw_chain=ch, resource="ipfs", ability="read", actor="did:c", require_signatures=False).allowed


def _datasets():
    m = _load("_ds_d", "ipfs_datasets/ipfs_datasets_py/mcp_server/ucan_delegation.py")

    def go(ch):
        ev = m.DelegationEvaluator()
        prev = None
        leaf = ""
        for i, d in enumerate(ch):
            cid = f"d{i}"
            caps = [m.Capability(resource=c["resource"], ability=c["ability"]) for c in d["capabilities"]]
            ev.add(m.Delegation(cid=cid, issuer=d["issuer"], audience=d["audience"], capabilities=caps, proof_cid=prev))
            prev, leaf = cid, cid
        if not leaf:
            return False
        ok, _ = ev.can_invoke(leaf, "ipfs", "did:c", ability="read")
        return bool(ok)
    return go


def test_all_three_allow_valid_chain():
    assert _kit()(VALID) and _accel()(VALID) and _datasets()(VALID)


def test_all_three_deny_empty_chain():
    assert not _kit()([]) and not _accel()([]) and not _datasets()([])
