"""Durable DuckDB-derived payment, replay, execution, and reconciliation index."""

from __future__ import annotations

import hashlib
import os
import shutil
import tempfile
import threading
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import duckdb

from .canonical import redact
from .errors import PAYMENT_REPLAY, RECONCILIATION_REQUIRED, ProfileHError

TERMINAL_STATES = frozenset({"executed", "failed", "declined"})
RECOVERABLE_STATES = frozenset({"verified", "settling", "settled", "executing", "reconciliation_required"})


@dataclass(frozen=True, slots=True)
class LedgerEntry:
    idempotency_key: str
    request_cid: str
    operation_key: str
    capability_cid: str
    state: str
    quote_cid: str | None = None
    payment_commitment: str | None = None
    verification_cid: str | None = None
    settlement_cid: str | None = None
    result_cid: str | None = None
    error_code: str | None = None
    lease_token: str | None = None
    created_at_ms: int = 0
    updated_at_ms: int = 0


class DuckDBPaymentLedger:
    """Short-transaction state machine; raw x402 payloads are never stored.

    DuckDB is the derived query index. Immutable receipt/artifact CIDs remain
    the provenance records. A process-local lock serializes transitions on one
    ledger instance; database uniqueness constraints provide replay fencing
    between instances and after restart.
    """

    def __init__(self, path: str | Path = ":memory:", *, connection: Any | None = None) -> None:
        self.path = str(path)
        if self.path != ":memory:":
            Path(self.path).parent.mkdir(parents=True, exist_ok=True)
        self._owns_connection = connection is None
        self.connection = connection or duckdb.connect(self.path)
        self._lock = threading.RLock()
        self._initialize()

    def _initialize(self) -> None:
        with self._lock:
            self.connection.execute(
                """
                CREATE TABLE IF NOT EXISTS profile_h_payments (
                    idempotency_key VARCHAR PRIMARY KEY,
                    request_cid VARCHAR NOT NULL,
                    operation_key VARCHAR NOT NULL,
                    capability_cid VARCHAR NOT NULL,
                    state VARCHAR NOT NULL,
                    quote_cid VARCHAR,
                    payment_commitment VARCHAR UNIQUE,
                    verification_cid VARCHAR,
                    settlement_cid VARCHAR,
                    result_cid VARCHAR,
                    error_code VARCHAR,
                    lease_token VARCHAR,
                    created_at_ms BIGINT NOT NULL,
                    updated_at_ms BIGINT NOT NULL
                )
                """
            )
            self.connection.execute(
                """
                CREATE TABLE IF NOT EXISTS profile_h_transitions (
                    sequence BIGINT PRIMARY KEY,
                    idempotency_key VARCHAR NOT NULL,
                    from_state VARCHAR,
                    to_state VARCHAR NOT NULL,
                    artifact_cid VARCHAR,
                    reason_code VARCHAR,
                    occurred_at_ms BIGINT NOT NULL
                )
                """
            )
            self.connection.execute(
                "CREATE SEQUENCE IF NOT EXISTS profile_h_transition_sequence START 1"
            )

    @staticmethod
    def _now() -> int:
        return time.time_ns() // 1_000_000

    @staticmethod
    def _entry(row: tuple[Any, ...] | None) -> LedgerEntry | None:
        return LedgerEntry(*row) if row else None

    def get(self, idempotency_key: str) -> LedgerEntry | None:
        with self._lock:
            row = self.connection.execute(
                """SELECT idempotency_key, request_cid, operation_key, capability_cid,
                          state, quote_cid, payment_commitment, verification_cid,
                          settlement_cid, result_cid, error_code, lease_token,
                          created_at_ms, updated_at_ms
                   FROM profile_h_payments WHERE idempotency_key = ?""",
                [idempotency_key],
            ).fetchone()
            return self._entry(row)

    def get_by_artifact(self, artifact_cid: str) -> LedgerEntry | None:
        """Resolve a public payment artifact without exposing arbitrary blocks."""
        if not artifact_cid:
            return None
        with self._lock:
            row = self.connection.execute(
                """SELECT idempotency_key, request_cid, operation_key, capability_cid,
                          state, quote_cid, payment_commitment, verification_cid,
                          settlement_cid, result_cid, error_code, lease_token,
                          created_at_ms, updated_at_ms
                   FROM profile_h_payments
                   WHERE quote_cid = ? OR verification_cid = ? OR settlement_cid = ? OR result_cid = ?
                   ORDER BY updated_at_ms DESC LIMIT 1""",
                [artifact_cid, artifact_cid, artifact_cid, artifact_cid],
            ).fetchone()
            return self._entry(row)

    def create_quote(
        self,
        idempotency_key: str,
        request_cid: str,
        operation_key: str,
        capability_cid: str,
        quote_cid: str,
    ) -> LedgerEntry:
        if not all((idempotency_key, request_cid, operation_key, capability_cid, quote_cid)):
            raise ValueError("ledger identity and quote fields must be non-empty")
        with self._lock:
            existing = self.get(idempotency_key)
            if existing:
                if (existing.request_cid, existing.operation_key, existing.capability_cid) != (
                    request_cid,
                    operation_key,
                    capability_cid,
                ):
                    raise ProfileHError(PAYMENT_REPLAY, "idempotency key is bound to another request")
                return existing
            now = self._now()
            try:
                self.connection.execute("BEGIN TRANSACTION")
                self.connection.execute(
                    """INSERT INTO profile_h_payments
                       (idempotency_key, request_cid, operation_key, capability_cid,
                        state, quote_cid, created_at_ms, updated_at_ms)
                       VALUES (?, ?, ?, ?, 'quoted', ?, ?, ?)""",
                    [idempotency_key, request_cid, operation_key, capability_cid, quote_cid, now, now],
                )
                self._transition_row(idempotency_key, None, "quoted", quote_cid, None, now)
                self.connection.execute("COMMIT")
            except Exception:
                self.connection.execute("ROLLBACK")
                # A competing connection may have won the uniqueness race.
                existing = self.get(idempotency_key)
                if existing and (existing.request_cid, existing.operation_key, existing.capability_cid) == (
                    request_cid, operation_key, capability_cid
                ):
                    return existing
                raise
            result = self.get(idempotency_key)
            assert result is not None
            return result

    def bind_payment(self, idempotency_key: str, payment_commitment: str) -> LedgerEntry:
        """Atomically fence a signed payload commitment against replay."""
        with self._lock:
            entry = self._require(idempotency_key)
            if entry.payment_commitment:
                if entry.payment_commitment != payment_commitment:
                    raise ProfileHError(PAYMENT_REPLAY, "different payment already bound to request")
                return entry
            if entry.state != "quoted":
                raise ProfileHError(PAYMENT_REPLAY, f"cannot bind payment in state {entry.state}")
            try:
                self.connection.execute(
                    "UPDATE profile_h_payments SET payment_commitment = ?, updated_at_ms = ? WHERE idempotency_key = ?",
                    [payment_commitment, self._now(), idempotency_key],
                )
            except duckdb.ConstraintException as exc:
                raise ProfileHError(PAYMENT_REPLAY, "payment commitment was already used") from exc
            return self._require(idempotency_key)

    def mark_verified(self, idempotency_key: str, verification_cid: str) -> LedgerEntry:
        return self._move(idempotency_key, {"quoted"}, "verified", artifact_cid=verification_cid, verification_cid=verification_cid)

    def begin_settlement(self, idempotency_key: str, lease_token: str) -> LedgerEntry:
        return self._move(idempotency_key, {"verified"}, "settling", lease_token=lease_token)

    def mark_settled(self, idempotency_key: str, settlement_cid: str) -> LedgerEntry:
        entry = self._require(idempotency_key)
        if entry.state == "settled" and entry.settlement_cid == settlement_cid:
            return entry
        return self._move(idempotency_key, {"settling"}, "settled", artifact_cid=settlement_cid, settlement_cid=settlement_cid, lease_token=None)

    def claim_execution(self, idempotency_key: str, lease_token: str) -> LedgerEntry:
        return self._move(idempotency_key, {"settled"}, "executing", lease_token=lease_token)

    def mark_executed(self, idempotency_key: str, result_cid: str) -> LedgerEntry:
        entry = self._require(idempotency_key)
        if entry.state == "executed" and entry.result_cid == result_cid:
            return entry
        return self._move(idempotency_key, {"executing"}, "executed", artifact_cid=result_cid, result_cid=result_cid, lease_token=None)

    def mark_failed(self, idempotency_key: str, error_code: str, *, reconciliation: bool = False) -> LedgerEntry:
        state = "reconciliation_required" if reconciliation else "failed"
        entry = self._require(idempotency_key)
        if entry.state in TERMINAL_STATES:
            return entry
        return self._move(idempotency_key, {entry.state}, state, reason_code=error_code, error_code=error_code, lease_token=None)

    def reset_for_reconciliation(self, idempotency_key: str, target_state: str, artifact_cid: str | None = None) -> LedgerEntry:
        """Operator/reconciler transition after external state has been checked."""
        if target_state not in {"verified", "settled", "failed", "reconciliation_required"}:
            raise ValueError("invalid reconciliation target")
        entry = self._require(idempotency_key)
        fields: dict[str, Any] = {"lease_token": None}
        if target_state == "settled" and artifact_cid:
            fields["settlement_cid"] = artifact_cid
        return self._move(idempotency_key, {entry.state}, target_state, artifact_cid=artifact_cid, **fields)

    def paid_evidence(self, request_cid: str, capability_cid: str) -> str | None:
        """Return settled evidence for the exact request and capability."""
        with self._lock:
            row = self.connection.execute(
                """SELECT settlement_cid FROM profile_h_payments
                   WHERE request_cid = ? AND capability_cid = ?
                     AND state IN ('settled', 'executing', 'executed')
                   ORDER BY updated_at_ms DESC LIMIT 1""",
                [request_cid, capability_cid],
            ).fetchone()
            return row[0] if row else None

    def pending_reconciliation(self, *, stale_before_ms: int | None = None) -> list[LedgerEntry]:
        with self._lock:
            query = """SELECT idempotency_key, request_cid, operation_key, capability_cid,
                              state, quote_cid, payment_commitment, verification_cid,
                              settlement_cid, result_cid, error_code, lease_token,
                              created_at_ms, updated_at_ms
                       FROM profile_h_payments
                       WHERE state IN ('verified','settling','settled','executing','reconciliation_required')"""
            params: list[Any] = []
            if stale_before_ms is not None:
                query += " AND updated_at_ms <= ?"
                params.append(stale_before_ms)
            query += " ORDER BY updated_at_ms, idempotency_key"
            return [self._entry(row) for row in self.connection.execute(query, params).fetchall()]  # type: ignore[misc]

    def history(self, idempotency_key: str) -> list[dict[str, Any]]:
        with self._lock:
            rows = self.connection.execute(
                """SELECT sequence, from_state, to_state, artifact_cid, reason_code, occurred_at_ms
                   FROM profile_h_transitions WHERE idempotency_key = ? ORDER BY sequence""",
                [idempotency_key],
            ).fetchall()
        return [
            {"sequence": row[0], "from": row[1], "to": row[2], "artifactCid": row[3], "reasonCode": row[4], "occurredAt": row[5]}
            for row in rows
        ]

    def diagnostics(self) -> dict[str, Any]:
        with self._lock:
            rows = self.connection.execute(
                "SELECT state, count(*) FROM profile_h_payments GROUP BY state ORDER BY state"
            ).fetchall()
        return redact({
            "ready": True,
            "durable": self.path != ":memory:",
            "states": {state: count for state, count in rows},
            "reconciliationRequired": sum(count for state, count in rows if state in RECOVERABLE_STATES),
        })

    def health_probe(self) -> dict[str, Any]:
        """Return a redacted structural/readiness probe without payment identifiers."""
        started = time.monotonic_ns()
        try:
            with self._lock:
                self.connection.execute("SELECT 1").fetchone()
                tables = {
                    row[0] for row in self.connection.execute(
                        "SELECT table_name FROM information_schema.tables WHERE table_schema = 'main'"
                    ).fetchall()
                }
                required = {"profile_h_payments", "profile_h_transitions"}
                orphaned = self.connection.execute(
                    """SELECT count(*) FROM profile_h_transitions t
                       LEFT JOIN profile_h_payments p ON p.idempotency_key = t.idempotency_key
                       WHERE p.idempotency_key IS NULL"""
                ).fetchone()[0]
                invalid_settled = self.connection.execute(
                    """SELECT count(*) FROM profile_h_payments
                       WHERE state IN ('settled','executing','executed') AND settlement_cid IS NULL"""
                ).fetchone()[0]
                pending = len(self.pending_reconciliation())
            healthy = required.issubset(tables) and orphaned == 0 and invalid_settled == 0
            return {
                "component": "profile-h-ledger",
                "status": "ready" if healthy else "degraded",
                "ready": healthy,
                "durable": self.path != ":memory:",
                "integrity": "ok" if healthy else "inconsistent",
                "pendingReconciliation": pending,
                "latencyMs": max(0, (time.monotonic_ns() - started) // 1_000_000),
            }
        except Exception:
            return {
                "component": "profile-h-ledger", "status": "unavailable", "ready": False,
                "durable": self.path != ":memory:", "integrity": "unknown",
                "pendingReconciliation": None,
                "latencyMs": max(0, (time.monotonic_ns() - started) // 1_000_000),
            }

    def backup(self, destination: str | Path) -> dict[str, Any]:
        """Checkpoint and atomically copy a durable ledger, returning public evidence."""
        if self.path == ":memory:":
            raise ValueError("an in-memory ledger cannot be backed up")
        target = Path(destination)
        target.parent.mkdir(parents=True, exist_ok=True)
        with self._lock:
            self.connection.execute("CHECKPOINT")
            fd, temporary_name = tempfile.mkstemp(prefix=".profile-h-ledger-", dir=target.parent)
            os.close(fd)
            temporary = Path(temporary_name)
            try:
                shutil.copy2(self.path, temporary)
                with temporary.open("rb") as stream:
                    digest = hashlib.sha256(stream.read()).hexdigest()
                os.replace(temporary, target)
            finally:
                temporary.unlink(missing_ok=True)
        return {"format": "duckdb-checkpoint-v1", "sha256": digest, "sizeBytes": target.stat().st_size}

    @staticmethod
    def restore_backup(source: str | Path, destination: str | Path, *, sha256: str) -> None:
        """Verify and atomically restore a ledger. The destination must not be open."""
        source_path, target = Path(source), Path(destination)
        if target.exists():
            raise FileExistsError("ledger restore target already exists")
        digest = hashlib.sha256(source_path.read_bytes()).hexdigest()
        if digest != sha256:
            raise OSError("ledger backup digest mismatch")
        target.parent.mkdir(parents=True, exist_ok=True)
        fd, temporary_name = tempfile.mkstemp(prefix=".profile-h-restore-", dir=target.parent)
        os.close(fd)
        temporary = Path(temporary_name)
        try:
            shutil.copy2(source_path, temporary)
            # Reject a corrupt or non-Profile-H database before replacement.
            probe = duckdb.connect(str(temporary), read_only=True)
            try:
                tables = {row[0] for row in probe.execute(
                    "SELECT table_name FROM information_schema.tables WHERE table_schema = 'main'"
                ).fetchall()}
                if not {"profile_h_payments", "profile_h_transitions"}.issubset(tables):
                    raise OSError("backup is not a Profile H ledger")
            finally:
                probe.close()
            os.replace(temporary, target)
        finally:
            temporary.unlink(missing_ok=True)

    def _require(self, idempotency_key: str) -> LedgerEntry:
        entry = self.get(idempotency_key)
        if entry is None:
            raise KeyError(idempotency_key)
        return entry

    def _move(
        self,
        idempotency_key: str,
        allowed: set[str],
        target: str,
        *,
        artifact_cid: str | None = None,
        reason_code: str | None = None,
        **fields: Any,
    ) -> LedgerEntry:
        with self._lock:
            entry = self._require(idempotency_key)
            if entry.state not in allowed:
                raise ProfileHError(
                    RECONCILIATION_REQUIRED,
                    f"transition {entry.state} -> {target} is not permitted",
                    retryable=entry.state in RECOVERABLE_STATES,
                )
            now = self._now()
            assignments = ["state = ?", "updated_at_ms = ?"]
            params: list[Any] = [target, now]
            allowed_fields = {"verification_cid", "settlement_cid", "result_cid", "error_code", "lease_token"}
            for name, value in fields.items():
                if name not in allowed_fields:
                    raise ValueError(f"unsupported ledger field: {name}")
                assignments.append(f"{name} = ?")
                params.append(value)
            params.extend([idempotency_key, entry.state])
            try:
                self.connection.execute("BEGIN TRANSACTION")
                self.connection.execute(
                    f"UPDATE profile_h_payments SET {', '.join(assignments)} WHERE idempotency_key = ? AND state = ?",
                    params,
                )
                current = self.connection.execute(
                    "SELECT state FROM profile_h_payments WHERE idempotency_key = ?", [idempotency_key]
                ).fetchone()
                if not current or current[0] != target:
                    raise ProfileHError(PAYMENT_REPLAY, "another worker won the payment transition")
                self._transition_row(idempotency_key, entry.state, target, artifact_cid, reason_code, now)
                self.connection.execute("COMMIT")
            except Exception:
                self.connection.execute("ROLLBACK")
                raise
            return self._require(idempotency_key)

    def _transition_row(self, key: str, old: str | None, new: str, cid: str | None, reason: str | None, now: int) -> None:
        self.connection.execute(
            """INSERT INTO profile_h_transitions
               VALUES (nextval('profile_h_transition_sequence'), ?, ?, ?, ?, ?, ?)""",
            [key, old, new, cid, reason, now],
        )

    def close(self) -> None:
        if self._owns_connection:
            with self._lock:
                self.connection.close()

    def __enter__(self) -> DuckDBPaymentLedger:
        return self

    def __exit__(self, *_: object) -> None:
        self.close()
