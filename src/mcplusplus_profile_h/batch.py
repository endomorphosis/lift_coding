"""Fail-closed EVM batch-settlement model for Profile H.

This module models the off-chain accounting boundary only.  It is deliberately
not an EVM contract or a mainnet switch: callers must separately provide
testnet deployment evidence and an approved security review to enable the
feature.  All values are unsigned integers in the asset's atomic unit.
"""

from __future__ import annotations

import json
import threading
import time
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import duckdb

from .canonical import canonical_json, cid_for
from .errors import ProfileHError
from .metering import ArtifactSigner, _canonical_uint

BATCH_DISABLED = "H_BATCH_SETTLEMENT_DISABLED"
BATCH_INVALID = "H_BATCH_INVALID"
BATCH_INSOLVENT = "H_BATCH_INSOLVENT"
BATCH_EXPIRED = "H_BATCH_EXPIRED"
BATCH_REPLAY = "H_BATCH_REPLAY"
BATCH_RECONCILIATION_REQUIRED = "H_BATCH_RECONCILIATION_REQUIRED"
BATCH_WITHDRAWAL_BLOCKED = "H_BATCH_WITHDRAWAL_BLOCKED"

TESTNET_CHAIN_IDS = frozenset({"eip155:11155111", "eip155:84532", "eip155:421614"})
REQUIRED_ENABLEMENT_CONTROLS = (
    "testnetDeployment",
    "depositSolvency",
    "signedVouchers",
    "sellerRedemption",
    "duplicateProtection",
    "expiry",
    "withdrawal",
    "failureRecovery",
    "reconciliation",
    "maximumExposure",
    "securityReviewApproved",
)


@dataclass(frozen=True, slots=True)
class DepositIntent:
    """Human-reviewable deposit approval; never accepts display-only amounts."""

    deposit_id: str
    payer_scope_cid: str
    escrow_contract: str
    network: str
    asset: str
    atomic_amount: int
    maximum_exposure: int
    issued_at_ms: int
    expires_at_ms: int
    withdrawal_delay_ms: int

    def __post_init__(self) -> None:
        for name in ("deposit_id", "payer_scope_cid", "escrow_contract", "asset"):
            if not getattr(self, name):
                raise ValueError(f"{name} must be non-empty")
        if self.network not in TESTNET_CHAIN_IDS:
            raise ProfileHError(BATCH_DISABLED, "batch deposits are restricted to approved testnets")
        amount = _canonical_uint(self.atomic_amount, "deposit amount", positive=True)
        maximum = _canonical_uint(self.maximum_exposure, "maximum exposure", positive=True)
        delay = _canonical_uint(self.withdrawal_delay_ms, "withdrawal delay", positive=True)
        if amount > maximum:
            raise ProfileHError(BATCH_INSOLVENT, "deposit exceeds the user's approved exposure")
        if self.expires_at_ms <= self.issued_at_ms:
            raise ValueError("deposit expiry must follow issuance")
        object.__setattr__(self, "atomic_amount", amount)
        object.__setattr__(self, "maximum_exposure", maximum)
        object.__setattr__(self, "withdrawal_delay_ms", delay)

    def artifact(self) -> dict[str, Any]:
        return {
            "schema": "mcp++/profile-h/batch-deposit-intent@1.0",
            "depositId": self.deposit_id,
            "payerScopeCid": self.payer_scope_cid,
            "escrowContract": self.escrow_contract,
            "network": self.network,
            "asset": self.asset,
            "atomicAmount": str(self.atomic_amount),
            "maximumExposure": str(self.maximum_exposure),
            "issuedAt": self.issued_at_ms,
            "expiresAt": self.expires_at_ms,
            "withdrawalAvailableAt": self.expires_at_ms + self.withdrawal_delay_ms,
            "withdrawalDelayMs": self.withdrawal_delay_ms,
            "settlementTiming": "batched-voucher-redemption",
            "approvalMode": "fresh-explicit",
        }

    def approval_view(self) -> dict[str, Any]:
        """Return the exact fields a wallet UX must show before signing."""
        return {
            "title": "Fund testnet batch-payment escrow",
            "warning": "The full deposit is at risk until vouchers expire or funds are withdrawn.",
            "requiresFreshApproval": True,
            "network": self.network,
            "asset": self.asset,
            "atomicAmount": str(self.atomic_amount),
            "maximumExposure": str(self.maximum_exposure),
            "escrowContract": self.escrow_contract,
            "voucherExpiry": self.expires_at_ms,
            "withdrawalAvailableAt": self.expires_at_ms + self.withdrawal_delay_ms,
            "actions": ["approve deposit", "cancel"],
        }


@dataclass(frozen=True, slots=True)
class DepositStatus:
    deposit_id: str
    state: str
    deposited: int
    reserved: int
    redeemed: int
    withdrawable: int
    maximum_exposure: int
    expires_at_ms: int


@dataclass(frozen=True, slots=True)
class VoucherStatus:
    voucher_id: str
    deposit_id: str
    seller_did: str
    nonce: int
    amount: int
    state: str
    expires_at_ms: int
    outcome_reference_cid: str | None


class DuckDBVoucherLedger:
    """Transactional test ledger for deposits, vouchers, redemption, and recovery."""

    def __init__(self, path: str | Path = ":memory:") -> None:
        self.path = str(path)
        if self.path != ":memory:":
            Path(self.path).parent.mkdir(parents=True, exist_ok=True)
        self.connection = duckdb.connect(self.path)
        self._lock = threading.RLock()
        self.connection.execute("""CREATE TABLE IF NOT EXISTS profile_h_batch_deposits (
            deposit_id VARCHAR PRIMARY KEY, artifact_json JSON NOT NULL, network VARCHAR NOT NULL,
            asset VARCHAR NOT NULL, deposited HUGEINT NOT NULL, reserved HUGEINT NOT NULL,
            redeemed HUGEINT NOT NULL, maximum_exposure HUGEINT NOT NULL, expires_at_ms BIGINT NOT NULL,
            withdrawal_at_ms BIGINT NOT NULL, state VARCHAR NOT NULL, updated_at_ms BIGINT NOT NULL)""")
        self.connection.execute("""CREATE TABLE IF NOT EXISTS profile_h_batch_vouchers (
            voucher_id VARCHAR PRIMARY KEY, deposit_id VARCHAR NOT NULL, seller_did VARCHAR NOT NULL,
            nonce BIGINT NOT NULL, amount HUGEINT NOT NULL, expires_at_ms BIGINT NOT NULL,
            artifact_json JSON NOT NULL, state VARCHAR NOT NULL, outcome_ref_cid VARCHAR,
            updated_at_ms BIGINT NOT NULL, UNIQUE(deposit_id, seller_did, nonce))""")

    def record_deposit(self, intent: DepositIntent, *, confirmed_at_ms: int) -> dict[str, Any]:
        artifact = intent.artifact()
        if confirmed_at_ms > intent.expires_at_ms:
            raise ProfileHError(BATCH_EXPIRED, "deposit confirmation arrived after approval expiry")
        with self._lock:
            existing = self.connection.execute(
                "SELECT artifact_json FROM profile_h_batch_deposits WHERE deposit_id = ?",
                [intent.deposit_id],
            ).fetchone()
            if existing:
                saved = json.loads(existing[0]) if isinstance(existing[0], str) else existing[0]
                if saved != artifact:
                    raise ProfileHError(BATCH_REPLAY, "deposit id was reused with different terms")
                return saved
            self.connection.execute(
                """INSERT INTO profile_h_batch_deposits VALUES (?, ?, ?, ?, ?, 0, 0, ?, ?, ?, 'active', ?)""",
                [intent.deposit_id, canonical_json(artifact).decode(), intent.network, intent.asset,
                 intent.atomic_amount, intent.maximum_exposure, intent.expires_at_ms,
                 intent.expires_at_ms + intent.withdrawal_delay_ms, confirmed_at_ms],
            )
        return artifact

    def issue_voucher(
        self, deposit_id: str, *, seller_did: str, nonce: int, atomic_amount: int,
        expires_at_ms: int, issued_at_ms: int, buyer_signer: ArtifactSigner,
    ) -> dict[str, Any]:
        if not seller_did.startswith("did:"):
            raise ValueError("seller_did must be a DID")
        sequence = _canonical_uint(nonce, "voucher nonce")
        amount = _canonical_uint(atomic_amount, "voucher amount", positive=True)
        with self._lock:
            row = self.connection.execute(
                """SELECT network, asset, deposited, reserved, redeemed, expires_at_ms, state,
                artifact_json FROM profile_h_batch_deposits WHERE deposit_id = ?""", [deposit_id]
            ).fetchone()
            if not row:
                raise KeyError(deposit_id)
            if row[6] != "active" or issued_at_ms > row[5] or expires_at_ms > row[5] or expires_at_ms <= issued_at_ms:
                raise ProfileHError(BATCH_EXPIRED, "deposit or voucher validity window is closed")
            unsigned = {
                "schema": "mcp++/profile-h/batch-voucher@1.0", "depositId": deposit_id,
                "sellerDid": seller_did, "nonce": sequence, "atomicAmount": str(amount),
                "network": row[0], "asset": row[1], "issuedAt": issued_at_ms,
                "expiresAt": expires_at_ms,
            }
            voucher = buyer_signer.sign(unsigned)
            voucher_id = cid_for(voucher)
            existing = self.connection.execute(
                "SELECT voucher_id, artifact_json FROM profile_h_batch_vouchers WHERE deposit_id=? AND seller_did=? AND nonce=?",
                [deposit_id, seller_did, sequence],
            ).fetchone()
            if existing:
                saved = json.loads(existing[1]) if isinstance(existing[1], str) else existing[1]
                if saved != voucher:
                    raise ProfileHError(BATCH_REPLAY, "voucher nonce was reused with different terms")
                return {**saved, "voucherId": existing[0]}
            if int(row[3]) + int(row[4]) + amount > int(row[2]):
                raise ProfileHError(BATCH_INSOLVENT, "outstanding vouchers exceed escrow balance")
            try:
                self.connection.execute("BEGIN TRANSACTION")
                self.connection.execute(
                    "INSERT INTO profile_h_batch_vouchers VALUES (?, ?, ?, ?, ?, ?, ?, 'issued', NULL, ?)",
                    [voucher_id, deposit_id, seller_did, sequence, amount, expires_at_ms,
                     canonical_json(voucher).decode(), issued_at_ms],
                )
                self.connection.execute(
                    "UPDATE profile_h_batch_deposits SET reserved=reserved+?, updated_at_ms=? WHERE deposit_id=?",
                    [amount, issued_at_ms, deposit_id],
                )
                self.connection.execute("COMMIT")
            except Exception:
                self.connection.execute("ROLLBACK")
                raise
            return {**voucher, "voucherId": voucher_id}

    def redeem(
        self, voucher: Mapping[str, Any], *, seller_did: str, now_ms: int,
        expected_buyer_public_key: str, outcome: str = "confirmed",
        outcome_reference: Mapping[str, Any] | None = None,
    ) -> dict[str, Any]:
        if outcome not in {"confirmed", "failed", "unknown"}:
            raise ValueError("outcome must be confirmed, failed, or unknown")
        value = dict(voucher)
        voucher_id = str(value.pop("voucherId", cid_for(value)))
        if voucher_id != cid_for(value) or not ArtifactSigner.verify(
            value, expected_public_key=expected_buyer_public_key
        ):
            raise ProfileHError(BATCH_INVALID, "voucher signature or CID is invalid")
        if value.get("sellerDid") != seller_did:
            raise ProfileHError(BATCH_INVALID, "voucher belongs to another seller")
        with self._lock:
            row = self.connection.execute(
                "SELECT deposit_id, amount, expires_at_ms, state, outcome_ref_cid FROM profile_h_batch_vouchers WHERE voucher_id=?",
                [voucher_id],
            ).fetchone()
            if not row:
                raise ProfileHError(BATCH_INVALID, "voucher is not reserved in this ledger")
            if row[3] in {"redeemed", "failed"}:
                return {"voucherId": voucher_id, "state": row[3], "duplicate": True,
                        "outcomeReferenceCid": row[4]}
            if row[3] == "reconciliation_required":
                raise ProfileHError(BATCH_RECONCILIATION_REQUIRED, "redemption outcome is unknown")
            if now_ms > row[2]:
                self._release(voucher_id, row[0], int(row[1]), now_ms, "expired")
                raise ProfileHError(BATCH_EXPIRED, "voucher expired before redemption")
            ref_cid = cid_for(outcome_reference) if outcome_reference else None
            if outcome == "unknown":
                self.connection.execute(
                    "UPDATE profile_h_batch_vouchers SET state='reconciliation_required', outcome_ref_cid=?, updated_at_ms=? WHERE voucher_id=?",
                    [ref_cid, now_ms, voucher_id],
                )
                self.connection.execute(
                    "UPDATE profile_h_batch_deposits SET state='reconciliation_required', updated_at_ms=? WHERE deposit_id=?",
                    [now_ms, row[0]],
                )
                return {"voucherId": voucher_id, "state": "reconciliation_required", "duplicate": False,
                        "outcomeReferenceCid": ref_cid}
            if outcome == "failed":
                # A known failed transaction does not consume or release the still-valid voucher.
                self.connection.execute(
                    "UPDATE profile_h_batch_vouchers SET outcome_ref_cid=?, updated_at_ms=? WHERE voucher_id=?",
                    [ref_cid, now_ms, voucher_id],
                )
                return {"voucherId": voucher_id, "state": "issued", "duplicate": False,
                        "retryable": True, "outcomeReferenceCid": ref_cid}
            self._confirm(voucher_id, row[0], int(row[1]), now_ms, ref_cid)
            return {"voucherId": voucher_id, "state": "redeemed", "duplicate": False,
                    "outcomeReferenceCid": ref_cid}

    def reconcile(self, voucher_id: str, *, confirmed: bool, now_ms: int,
                  outcome_reference: Mapping[str, Any]) -> dict[str, Any]:
        ref_cid = cid_for(outcome_reference)
        with self._lock:
            row = self.connection.execute(
                "SELECT deposit_id, amount, state FROM profile_h_batch_vouchers WHERE voucher_id=?", [voucher_id]
            ).fetchone()
            if not row:
                raise KeyError(voucher_id)
            if row[2] != "reconciliation_required":
                raise ProfileHError(BATCH_INVALID, "voucher does not require reconciliation")
            if confirmed:
                self._confirm(voucher_id, row[0], int(row[1]), now_ms, ref_cid)
                state = "redeemed"
            else:
                self.connection.execute(
                    "UPDATE profile_h_batch_vouchers SET state='issued', outcome_ref_cid=?, updated_at_ms=? WHERE voucher_id=?",
                    [ref_cid, now_ms, voucher_id],
                )
                state = "issued"
            pending = self.connection.execute(
                "SELECT COUNT(*) FROM profile_h_batch_vouchers WHERE deposit_id=? AND state='reconciliation_required'", [row[0]]
            ).fetchone()[0]
            if not pending:
                self.connection.execute(
                    "UPDATE profile_h_batch_deposits SET state='active', updated_at_ms=? WHERE deposit_id=?",
                    [now_ms, row[0]],
                )
            return {"voucherId": voucher_id, "state": state, "outcomeReferenceCid": ref_cid}

    def expire_vouchers(self, deposit_id: str, *, now_ms: int) -> int:
        with self._lock:
            rows = self.connection.execute(
                "SELECT voucher_id, amount FROM profile_h_batch_vouchers WHERE deposit_id=? AND state='issued' AND expires_at_ms < ?",
                [deposit_id, now_ms],
            ).fetchall()
            for voucher_id, amount in rows:
                self._release(voucher_id, deposit_id, int(amount), now_ms, "expired")
            return len(rows)

    def withdraw(self, deposit_id: str, *, now_ms: int) -> dict[str, Any]:
        self.expire_vouchers(deposit_id, now_ms=now_ms)
        with self._lock:
            row = self.connection.execute(
                "SELECT deposited, reserved, redeemed, withdrawal_at_ms, state FROM profile_h_batch_deposits WHERE deposit_id=?",
                [deposit_id],
            ).fetchone()
            if not row:
                raise KeyError(deposit_id)
            if row[4] == "reconciliation_required" or row[1] != 0 or now_ms < row[3]:
                raise ProfileHError(BATCH_WITHDRAWAL_BLOCKED, "withdrawal delay, vouchers, or reconciliation still blocks funds")
            amount = int(row[0]) - int(row[2])
            self.connection.execute(
                "UPDATE profile_h_batch_deposits SET state='withdrawn', deposited=redeemed, updated_at_ms=? WHERE deposit_id=?",
                [now_ms, deposit_id],
            )
            return {"depositId": deposit_id, "state": "withdrawn", "atomicAmount": str(amount)}

    def status(self, deposit_id: str) -> DepositStatus:
        row = self.connection.execute(
            "SELECT state, deposited, reserved, redeemed, maximum_exposure, expires_at_ms FROM profile_h_batch_deposits WHERE deposit_id=?",
            [deposit_id],
        ).fetchone()
        if not row:
            raise KeyError(deposit_id)
        available = int(row[1]) - int(row[2]) - int(row[3])
        return DepositStatus(deposit_id, row[0], int(row[1]), int(row[2]), int(row[3]),
                             available, int(row[4]), int(row[5]))

    def voucher_status(self, voucher_id: str) -> VoucherStatus:
        """Return redacted redemption state suitable for authorized status UX."""
        row = self.connection.execute(
            """SELECT deposit_id, seller_did, nonce, amount, state, expires_at_ms,
            outcome_ref_cid FROM profile_h_batch_vouchers WHERE voucher_id=?""", [voucher_id]
        ).fetchone()
        if not row:
            raise KeyError(voucher_id)
        return VoucherStatus(voucher_id, row[0], row[1], int(row[2]), int(row[3]), row[4],
                             int(row[5]), row[6])

    def audit(self, deposit_id: str) -> dict[str, Any]:
        """Reproduce solvency from durable balances and voucher states."""
        status = self.status(deposit_id)
        rows = self.connection.execute(
            "SELECT state, COUNT(*), COALESCE(SUM(amount), 0) FROM profile_h_batch_vouchers WHERE deposit_id=? GROUP BY state",
            [deposit_id],
        ).fetchall()
        vouchers = {
            state: {"count": int(count), "atomicAmount": str(int(amount))}
            for state, count, amount in rows
        }
        issued = int(vouchers.get("issued", {}).get("atomicAmount", "0"))
        pending = int(vouchers.get("reconciliation_required", {}).get("atomicAmount", "0"))
        reserved_reproduced = issued + pending
        solvent = (
            reserved_reproduced == status.reserved
            and status.reserved + status.redeemed <= status.deposited
            and status.deposited <= status.maximum_exposure
        )
        return {
            "depositId": deposit_id,
            "state": status.state,
            "deposited": str(status.deposited),
            "reserved": str(status.reserved),
            "redeemed": str(status.redeemed),
            "withdrawable": str(status.withdrawable),
            "maximumExposure": str(status.maximum_exposure),
            "voucherStates": vouchers,
            "solvent": solvent,
        }

    def _confirm(self, voucher_id: str, deposit_id: str, amount: int, now_ms: int,
                 ref_cid: str | None) -> None:
        try:
            self.connection.execute("BEGIN TRANSACTION")
            self.connection.execute(
                "UPDATE profile_h_batch_vouchers SET state='redeemed', outcome_ref_cid=?, updated_at_ms=? WHERE voucher_id=?",
                [ref_cid, now_ms, voucher_id],
            )
            self.connection.execute(
                "UPDATE profile_h_batch_deposits SET reserved=reserved-?, redeemed=redeemed+?, updated_at_ms=? WHERE deposit_id=?",
                [amount, amount, now_ms, deposit_id],
            )
            self.connection.execute("COMMIT")
        except Exception:
            self.connection.execute("ROLLBACK")
            raise

    def _release(self, voucher_id: str, deposit_id: str, amount: int, now_ms: int,
                 state: str) -> None:
        try:
            self.connection.execute("BEGIN TRANSACTION")
            self.connection.execute(
                "UPDATE profile_h_batch_vouchers SET state=?, updated_at_ms=? WHERE voucher_id=?",
                [state, now_ms, voucher_id],
            )
            self.connection.execute(
                "UPDATE profile_h_batch_deposits SET reserved=reserved-?, updated_at_ms=? WHERE deposit_id=?",
                [amount, now_ms, deposit_id],
            )
            self.connection.execute("COMMIT")
        except Exception:
            self.connection.execute("ROLLBACK")
            raise

    def close(self) -> None:
        self.connection.close()


def evaluate_batch_enablement(evidence: Mapping[str, Any]) -> dict[str, Any]:
    """Return a fail-closed rollout decision from independently supplied evidence."""
    controls = {name: evidence.get(name) is True for name in REQUIRED_ENABLEMENT_CONTROLS}
    missing = [name for name, passed in controls.items() if not passed]
    network = evidence.get("network")
    testnet_only = network in TESTNET_CHAIN_IDS
    if not testnet_only:
        missing.append("approvedTestnetNetwork")
    enabled = not missing
    return {
        "schema": "mcp++/profile-h/batch-enablement-decision@1.0",
        "enabled": enabled,
        "decision": "enabled-testnet-only" if enabled else "disabled",
        "network": network,
        "controls": controls,
        "missingControls": sorted(set(missing)),
        "mainnetEnabled": False,
        "evaluatedAtPolicyVersion": "xph-111/1.0",
    }
