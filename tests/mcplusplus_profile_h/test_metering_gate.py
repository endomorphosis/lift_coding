from __future__ import annotations

from mcplusplus_profile_h.canonical import cid_for
from mcplusplus_profile_h.metering_gate import run_metering_gate


def test_cross_seller_metering_gate_is_deterministic(tmp_path):
    report = run_metering_gate(state_dir=tmp_path / "first")
    reproduced = run_metering_gate(state_dir=tmp_path / "second")
    assert report == reproduced
    assert report["decision"] == "pass" and report["sellerCount"] == 3
    assert all(row["reproducible"] and row["usageSignatureVerified"] for row in report["meters"])
    evidence = report.pop("evidenceCid")
    assert evidence == cid_for(report)
