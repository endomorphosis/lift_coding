from __future__ import annotations

import pytest

from mcplusplus_profile_h import (
    ArtifactSigner, DepositIntent, DuckDBVoucherLedger, evaluate_batch_enablement,
)
from mcplusplus_profile_h.batch import (
    BATCH_DISABLED, BATCH_INSOLVENT, BATCH_RECONCILIATION_REQUIRED,
    REQUIRED_ENABLEMENT_CONTROLS,
)
from mcplusplus_profile_h.canonical import cid_for
from mcplusplus_profile_h.errors import ProfileHError

NOW = 1_783_843_200_000
BUYER = ArtifactSigner.from_seed(b"v" * 32, key_id="buyer")


def intent(amount=1000, maximum=1000, network="eip155:84532"):
    return DepositIntent(
        "deposit-1", cid_for({"payer": 1}), "0x" + "1" * 40, network, "test:asset",
        amount, maximum, NOW, NOW + 1000, 100,
    )


def test_deposit_ux_is_explicit_and_testnet_only():
    view = intent().approval_view()
    assert view["requiresFreshApproval"] is True
    assert view["atomicAmount"] == view["maximumExposure"] == "1000"
    assert "full deposit" in view["warning"].lower()
    with pytest.raises(ProfileHError) as raised:
        intent(network="eip155:1")
    assert raised.value.code == BATCH_DISABLED
    with pytest.raises(ProfileHError) as raised:
        intent(amount=1001)
    assert raised.value.code == BATCH_INSOLVENT


def test_vouchers_reserve_solvency_redeem_once_and_withdraw(tmp_path):
    ledger = DuckDBVoucherLedger(tmp_path / "batch.duckdb")
    deposit = intent()
    ledger.record_deposit(deposit, confirmed_at_ms=NOW)
    voucher = ledger.issue_voucher(
        deposit.deposit_id, seller_did="did:web:seller.test", nonce=0,
        atomic_amount=600, expires_at_ms=NOW + 900, issued_at_ms=NOW + 1,
        buyer_signer=BUYER,
    )
    with pytest.raises(ProfileHError) as raised:
        ledger.issue_voucher(
            deposit.deposit_id, seller_did="did:web:other.test", nonce=0,
            atomic_amount=401, expires_at_ms=NOW + 900, issued_at_ms=NOW + 2,
            buyer_signer=BUYER,
        )
    assert raised.value.code == BATCH_INSOLVENT
    first = ledger.redeem(
        voucher, seller_did="did:web:seller.test", now_ms=NOW + 3,
        expected_buyer_public_key=BUYER.public_key,
    )
    replay = ledger.redeem(
        voucher, seller_did="did:web:seller.test", now_ms=NOW + 4,
        expected_buyer_public_key=BUYER.public_key,
    )
    assert first["state"] == "redeemed" and replay["duplicate"] is True
    assert ledger.voucher_status(voucher["voucherId"]).state == "redeemed"
    assert ledger.audit(deposit.deposit_id)["solvent"] is True
    withdrawn = ledger.withdraw(deposit.deposit_id, now_ms=NOW + 1101)
    assert withdrawn["atomicAmount"] == "400"


def test_unknown_redemption_blocks_replay_until_reconciled(tmp_path):
    ledger = DuckDBVoucherLedger(tmp_path / "recover.duckdb")
    ledger.record_deposit(intent(), confirmed_at_ms=NOW)
    voucher = ledger.issue_voucher(
        "deposit-1", seller_did="did:web:seller.test", nonce=9,
        atomic_amount=100, expires_at_ms=NOW + 900, issued_at_ms=NOW + 1,
        buyer_signer=BUYER,
    )
    ledger.redeem(
        voucher, seller_did="did:web:seller.test", now_ms=NOW + 2,
        expected_buyer_public_key=BUYER.public_key, outcome="unknown",
    )
    with pytest.raises(ProfileHError) as raised:
        ledger.redeem(
            voucher, seller_did="did:web:seller.test", now_ms=NOW + 3,
            expected_buyer_public_key=BUYER.public_key,
        )
    assert raised.value.code == BATCH_RECONCILIATION_REQUIRED
    result = ledger.reconcile(
        voucher["voucherId"], confirmed=True, now_ms=NOW + 4,
        outcome_reference={"receipt": "final"},
    )
    assert result["state"] == "redeemed"


def test_enablement_requires_every_control_and_never_enables_mainnet():
    evidence = {name: True for name in REQUIRED_ENABLEMENT_CONTROLS}
    enabled = evaluate_batch_enablement({**evidence, "network": "eip155:84532"})
    assert enabled["enabled"] and not enabled["mainnetEnabled"]
    assert evaluate_batch_enablement({**evidence, "network": "eip155:1"})["decision"] == "disabled"
    evidence["securityReviewApproved"] = False
    assert evaluate_batch_enablement({**evidence, "network": "eip155:84532"})["decision"] == "disabled"
