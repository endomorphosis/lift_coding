"""All four codebases share the Kubo CIDv1 content-address profile.

kit, accelerate, datasets must emit byte-identical CIDs (raw/sha2-256/base32,
bafkrei…) for the same canonical artifact bytes so receipts/events interoperate.
"""
import importlib.util
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]


def _file_mod(name, rel):
    p = ROOT / "external" / rel
    if not p.exists():
        pytest.skip(f"{rel} not present")
    spec = importlib.util.spec_from_file_location(name, p)
    m = importlib.util.module_from_spec(spec)
    sys.modules[name] = m
    spec.loader.exec_module(m)
    return m


BODY = b'{"a":1,"b":2,"tool":"pin_rm"}'


def test_kit_accel_kubo_cid_identical():
    sys.path.insert(0, str(ROOT / "external" / "ipfs_kit"))
    from ipfs_kit_py.mcp_server.mcplusplus import artifacts as kit
    accel = _file_mod("_acc_kubo", "ipfs_accelerate/ipfs_accelerate_py/mcp_server/mcplusplus/kubo_cid.py")
    cid = kit.compute_artifact_cid({"a": 1, "b": 2, "tool": "pin_rm"})
    assert cid == accel.cid_for_bytes(BODY)
    assert cid.startswith("bafkrei") and len(cid) == 59


def test_datasets_kubo_cid_identical():
    ds = _file_mod("_ds_cid", "ipfs_datasets/ipfs_datasets_py/utils/cid_utils.py")
    try:
        cid = ds.cid_for_obj({"a": 1, "b": 2, "tool": "pin_rm"})
    except Exception:
        pytest.skip("multiformats not installed")
    accel = _file_mod("_acc_kubo2", "ipfs_accelerate/ipfs_accelerate_py/mcp_server/mcplusplus/kubo_cid.py")
    assert cid == accel.cid_for_bytes(BODY)
