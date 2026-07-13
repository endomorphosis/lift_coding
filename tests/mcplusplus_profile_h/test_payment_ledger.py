from __future__ import annotations

import pytest

from mcplusplus_profile_h import DuckDBPaymentLedger
from mcplusplus_profile_h.errors import PAYMENT_REPLAY, RECONCILIATION_REQUIRED, ProfileHError


def quoted(ledger, key="key", request="request"):
    return ledger.create_quote(key, request, "tool:pin", "capability", "quote")


def test_ledger_is_durable_and_records_state_lineage(tmp_path):
    path = tmp_path / "ledger.duckdb"
    ledger = DuckDBPaymentLedger(path)
    quoted(ledger)
    ledger.bind_payment("key", "payment")
    ledger.mark_verified("key", "verification")
    ledger.begin_settlement("key", "settlement-lease")
    ledger.mark_settled("key", "settlement")
    ledger.claim_execution("key", "execution-lease")
    ledger.mark_executed("key", "access-receipt")
    assert [item["to"] for item in ledger.history("key")] == [
        "quoted", "verified", "settling", "settled", "executing", "executed"
    ]
    ledger.close()

    reopened = DuckDBPaymentLedger(path)
    entry = reopened.get("key")
    assert entry.state == "executed"
    assert entry.result_cid == "access-receipt"
    assert reopened.paid_evidence("request", "capability") == "settlement"
    assert reopened.diagnostics()["durable"] is True


def test_idempotency_and_payment_commitment_are_unique(tmp_path):
    ledger = DuckDBPaymentLedger(tmp_path / "ledger.duckdb")
    quoted(ledger)
    assert quoted(ledger).state == "quoted"
    with pytest.raises(ProfileHError) as mismatch:
        quoted(ledger, request="different")
    assert mismatch.value.code == PAYMENT_REPLAY
    ledger.bind_payment("key", "payment")
    quoted(ledger, "other", "other-request")
    with pytest.raises(ProfileHError) as replay:
        ledger.bind_payment("other", "payment")
    assert replay.value.code == PAYMENT_REPLAY


def test_invalid_transition_fails_closed_and_crash_states_are_reconcilable(tmp_path):
    ledger = DuckDBPaymentLedger(tmp_path / "ledger.duckdb")
    quoted(ledger)
    with pytest.raises(ProfileHError) as raised:
        ledger.claim_execution("key", "lease")
    assert raised.value.code == RECONCILIATION_REQUIRED
    ledger.bind_payment("key", "payment")
    ledger.mark_verified("key", "verification")
    ledger.begin_settlement("key", "lease")
    pending = ledger.pending_reconciliation()
    assert [(item.idempotency_key, item.state) for item in pending] == [("key", "settling")]
    ledger.mark_failed("key", "H_RECONCILIATION_REQUIRED", reconciliation=True)
    assert ledger.get("key").lease_token is None
    assert ledger.diagnostics()["reconciliationRequired"] == 1

