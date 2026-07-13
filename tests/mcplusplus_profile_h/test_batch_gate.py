from __future__ import annotations

from mcplusplus_profile_h.batch_gate import run_batch_gate
from mcplusplus_profile_h.canonical import cid_for


def test_batch_gate_is_deterministic_and_fails_closed(tmp_path):
    first = run_batch_gate(state_dir=tmp_path / "one")
    second = run_batch_gate(state_dir=tmp_path / "two")
    assert first == second
    assert first["gateResult"] == "pass"
    assert first["rolloutDecision"]["decision"] == "disabled"
    assert {"testnetDeployment", "securityReviewApproved"}.issubset(
        first["rolloutDecision"]["missingControls"]
    )
    evidence = first.pop("evidenceCid")
    assert evidence == cid_for(first)
