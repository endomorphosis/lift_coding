"""XPH-111 deterministic batch-settlement evaluation gate."""

from __future__ import annotations

import tempfile
from pathlib import Path
from typing import Any

from .batch import (
    BATCH_INSOLVENT,
    BATCH_WITHDRAWAL_BLOCKED,
    DepositIntent,
    DuckDBVoucherLedger,
    evaluate_batch_enablement,
)
from .canonical import cid_for
from .errors import ProfileHError
from .metering import ArtifactSigner

NOW = 1_783_843_200_000
BUYER = ArtifactSigner.from_seed(bytes.fromhex("33" * 32), key_id="did:key:buyer#xph-111")


def run_batch_gate(*, state_dir: Path | None = None) -> dict[str, Any]:
    """Prove the local model and return a deliberately disabled rollout decision."""
    temporary: tempfile.TemporaryDirectory[str] | None = None
    if state_dir is None:
        temporary = tempfile.TemporaryDirectory(prefix="xph-111-")
        state_dir = Path(temporary.name)
    state_dir.mkdir(parents=True, exist_ok=True)
    ledger = DuckDBVoucherLedger(state_dir / "batch.duckdb")
    try:
        intent = DepositIntent(
            "xph-111:deposit:primary", cid_for({"buyer": "SwissKnife"}),
            "0x1111111111111111111111111111111111111111", "eip155:84532",
            "eip155:84532/erc20:0x0000000000000000000000000000000000000001",
            1_000, 1_000, NOW, NOW + 10_000, 5_000,
        )
        ledger.record_deposit(intent, confirmed_at_ms=NOW + 1)
        voucher = ledger.issue_voucher(
            intent.deposit_id, seller_did="did:web:ipfs-kit.test", nonce=0,
            atomic_amount=300, expires_at_ms=NOW + 8_000, issued_at_ms=NOW + 100,
            buyer_signer=BUYER,
        )
        replayed_issue = ledger.issue_voucher(
            intent.deposit_id, seller_did="did:web:ipfs-kit.test", nonce=0,
            atomic_amount=300, expires_at_ms=NOW + 8_000, issued_at_ms=NOW + 100,
            buyer_signer=BUYER,
        )
        redemption = ledger.redeem(
            voucher, seller_did="did:web:ipfs-kit.test", now_ms=NOW + 200,
            expected_buyer_public_key=BUYER.public_key,
            outcome_reference={"testnetReceipt": "confirmed-1"},
        )
        duplicate = ledger.redeem(
            voucher, seller_did="did:web:ipfs-kit.test", now_ms=NOW + 201,
            expected_buyer_public_key=BUYER.public_key,
            outcome_reference={"testnetReceipt": "confirmed-1"},
        )

        expiring = ledger.issue_voucher(
            intent.deposit_id, seller_did="did:web:ipfs-datasets.test", nonce=0,
            atomic_amount=200, expires_at_ms=NOW + 7_000, issued_at_ms=NOW + 300,
            buyer_signer=BUYER,
        )
        withdrawal_blocked = False
        try:
            ledger.withdraw(intent.deposit_id, now_ms=NOW + 1_000)
        except ProfileHError as error:
            withdrawal_blocked = error.code == BATCH_WITHDRAWAL_BLOCKED
        expired_count = ledger.expire_vouchers(intent.deposit_id, now_ms=NOW + 7_001)

        insolvent_rejected = False
        try:
            ledger.issue_voucher(
                intent.deposit_id, seller_did="did:web:ipfs-accelerate.test", nonce=0,
                atomic_amount=701, expires_at_ms=NOW + 9_000, issued_at_ms=NOW + 400,
                buyer_signer=BUYER,
            )
        except ProfileHError as error:
            insolvent_rejected = error.code == BATCH_INSOLVENT

        recovery = ledger.issue_voucher(
            intent.deposit_id, seller_did="did:web:ipfs-accelerate.test", nonce=1,
            atomic_amount=100, expires_at_ms=NOW + 9_000, issued_at_ms=NOW + 500,
            buyer_signer=BUYER,
        )
        known_failure = ledger.redeem(
            recovery, seller_did="did:web:ipfs-accelerate.test", now_ms=NOW + 600,
            expected_buyer_public_key=BUYER.public_key, outcome="failed",
            outcome_reference={"testnetReceipt": "reverted-1"},
        )
        unknown = ledger.redeem(
            recovery, seller_did="did:web:ipfs-accelerate.test", now_ms=NOW + 700,
            expected_buyer_public_key=BUYER.public_key, outcome="unknown",
            outcome_reference={"rpcRequest": "timeout-1"},
        )
        reconciled = ledger.reconcile(
            recovery["voucherId"], confirmed=False, now_ms=NOW + 800,
            outcome_reference={"testnetReceipt": "not-found-finalized"},
        )
        ledger.expire_vouchers(intent.deposit_id, now_ms=NOW + 10_001)
        withdrawal = ledger.withdraw(intent.deposit_id, now_ms=NOW + 15_001)
        status = ledger.status(intent.deposit_id)
        audit = ledger.audit(intent.deposit_id)

        local_controls = {
            "depositSolvency": insolvent_rejected and audit["solvent"],
            "signedVouchers": voucher["signatureAlg"] == "Ed25519",
            "sellerRedemption": redemption["state"] == "redeemed",
            "duplicateProtection": replayed_issue["voucherId"] == voucher["voucherId"] and duplicate["duplicate"],
            "expiry": expired_count == 1,
            "withdrawal": withdrawal_blocked and withdrawal["atomicAmount"] == "700",
            "failureRecovery": known_failure["retryable"] and unknown["state"] == "reconciliation_required",
            "reconciliation": reconciled["state"] == "issued",
            "maximumExposure": intent.atomic_amount <= intent.maximum_exposure,
        }
        if not all(local_controls.values()):
            raise AssertionError(f"batch safety invariant failed: {local_controls}")
        # Local simulation is not testnet deployment evidence or a security review.
        enablement = evaluate_batch_enablement({
            **local_controls, "network": intent.network,
            "testnetDeployment": False, "securityReviewApproved": False,
        })
        if enablement["enabled"]:
            raise AssertionError("batch settlement enabled without external evidence")
        report: dict[str, Any] = {
            "schema": "mcp++/profile-h/batch-gate-report@1.0",
            "task": "XPH-111", "profile": "mcp++/x402-payments",
            "profileVersion": "1.0", "gateResult": "pass",
            "rolloutDecision": enablement,
            "escrowDepositUx": intent.approval_view(),
            "ledgerEvidence": {
                "depositId": intent.deposit_id, "depositAmount": "1000",
                "redeemedAmount": "300", "withdrawnAmount": withdrawal["atomicAmount"],
                "voucherCid": voucher["voucherId"], "expiredVoucherCid": expiring["voucherId"],
                "duplicateRedemptionIdempotent": True, "unknownOutcomeReconciled": True,
                "finalState": status.state, "solvencyAudit": audit,
            },
            "localControls": local_controls,
            "threatModel": "docs/mcplusplus-profile-h-batch-threat-model.md",
            "limitations": [
                "deterministic ledger evidence is not an EVM contract deployment",
                "no independent smart-contract security review is recorded",
                "mainnet batch settlement is unconditionally disabled",
            ],
        }
        report["evidenceCid"] = cid_for(report)
        return report
    finally:
        ledger.close()
        if temporary is not None:
            temporary.cleanup()
