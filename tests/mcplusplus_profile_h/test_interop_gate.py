from __future__ import annotations

import asyncio
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
for path in (ROOT / "external/ipfs_kit", ROOT / "external/ipfs_datasets", ROOT / "external/ipfs_accelerate"):
    sys.path.insert(0, str(path))

from mcplusplus_profile_h.canonical import cid_for
from mcplusplus_profile_h.interop import run_interop


def test_three_seller_http_libp2p_gate(tmp_path):
    report = asyncio.run(run_interop(state_dir=tmp_path))
    assert report["decision"] == "pass"
    assert report["sellerCount"] == 3
    assert len(report["representativePayments"]) == 6
    assert len(report["parityMatrix"]) == 3
    assert all(row["status"] == "pass" for row in report["parityMatrix"])
    assert {dag["scenario"] for dag in report["eventDags"]} == {
        "timeout-and-reconciliation", "crash-after-settlement", "durable-restart-replay"
    }
    evidence_cid = report.pop("evidenceCid")
    assert evidence_cid == cid_for(report)

