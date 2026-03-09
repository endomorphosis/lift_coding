"""Persistence helpers for reusable AI history artifacts."""

from __future__ import annotations

import os
import uuid
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

import duckdb


@dataclass
class AIHistoryRecord:
    """Indexed persisted AI artifact available for future retrieval."""

    id: str
    user_id: str
    capability_id: str
    repo: str | None
    pr_number: int | None
    failure_target: str | None
    failure_target_type: str | None
    ipfs_cid: str
    created_at: datetime


def store_ai_history_record(
    conn: duckdb.DuckDBPyConnection,
    *,
    user_id: str,
    capability_id: str,
    ipfs_cid: str,
    repo: str | None = None,
    pr_number: int | None = None,
    failure_target: str | None = None,
    failure_target_type: str | None = None,
) -> AIHistoryRecord:
    """Store a reusable persisted AI artifact unless it already exists for the user/CID."""
    _maybe_prune_ai_history(conn, user_id=user_id, capability_id=capability_id)

    existing = conn.execute(
        """
        SELECT id, user_id, capability_id, repo, pr_number, failure_target,
               failure_target_type, ipfs_cid, created_at
        FROM ai_history_index
        WHERE user_id = ? AND capability_id = ? AND ipfs_cid = ?
        LIMIT 1
        """,
        [user_id, capability_id, ipfs_cid],
    ).fetchone()
    if existing:
        return _row_to_record(existing)

    record_id = str(uuid.uuid4())
    created_at = datetime.now(UTC)
    conn.execute(
        """
        INSERT INTO ai_history_index
        (id, user_id, capability_id, repo, pr_number, failure_target,
         failure_target_type, ipfs_cid, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        [
            record_id,
            user_id,
            capability_id,
            repo,
            pr_number,
            failure_target,
            failure_target_type,
            ipfs_cid,
            created_at,
        ],
    )
    _maybe_prune_ai_history(conn, user_id=user_id, capability_id=capability_id)
    return AIHistoryRecord(
        id=record_id,
        user_id=user_id,
        capability_id=capability_id,
        repo=repo,
        pr_number=pr_number,
        failure_target=failure_target,
        failure_target_type=failure_target_type,
        ipfs_cid=ipfs_cid,
        created_at=created_at,
    )


def prune_ai_history_records(
    conn: duckdb.DuckDBPyConnection,
    *,
    older_than_days: int,
    capability_id: str | None = None,
) -> int:
    """Delete indexed AI history records older than the configured retention window."""
    if older_than_days < 0:
        raise ValueError("older_than_days must be non-negative")

    cutoff = datetime.now(UTC) - timedelta(days=older_than_days)
    query = "DELETE FROM ai_history_index WHERE created_at < ?"
    params: list[object] = [cutoff]
    if capability_id:
        query += " AND capability_id = ?"
        params.append(capability_id)
    query += " RETURNING id"
    rows = conn.execute(query, params).fetchall()
    return len(rows)


def prune_ai_history_records_to_limit(
    conn: duckdb.DuckDBPyConnection,
    *,
    user_id: str,
    max_records: int,
    capability_id: str | None = None,
) -> int:
    """Keep only the newest indexed history records for a user, optionally per capability."""
    if max_records < 0:
        raise ValueError("max_records must be non-negative")

    rows = conn.execute(
        """
        SELECT id
        FROM ai_history_index
        WHERE user_id = ?
        {capability_clause}
        ORDER BY created_at DESC
        OFFSET ?
        """.replace(
            "{capability_clause}",
            "AND capability_id = ?" if capability_id else "",
        ),
        [user_id, capability_id, max_records] if capability_id else [user_id, max_records],
    ).fetchall()
    if not rows:
        return 0

    ids = [str(row[0]) for row in rows]
    placeholders = ", ".join(["?"] * len(ids))
    conn.execute(f"DELETE FROM ai_history_index WHERE id IN ({placeholders})", ids)
    return len(ids)


def get_ai_history_records(
    conn: duckdb.DuckDBPyConnection,
    *,
    user_id: str,
    capability_id: str | None = None,
    repo: str | None = None,
    failure_target: str | None = None,
    failure_target_type: str | None = None,
    exclude_pr_number: int | None = None,
    limit: int = 50,
) -> list[AIHistoryRecord]:
    """Query indexed persisted AI artifacts using the failure-analysis lookup shape."""
    query = """
        SELECT id, user_id, capability_id, repo, pr_number, failure_target,
               failure_target_type, ipfs_cid, created_at
        FROM ai_history_index
        WHERE user_id = ?
    """
    params: list[object] = [user_id]

    if capability_id:
        query += " AND capability_id = ?"
        params.append(capability_id)
    if repo:
        query += " AND repo = ?"
        params.append(repo)
    if failure_target:
        query += " AND failure_target = ?"
        params.append(failure_target)
    if failure_target_type:
        query += " AND failure_target_type = ?"
        params.append(failure_target_type)
    if exclude_pr_number is not None:
        query += " AND (pr_number IS NULL OR pr_number != ?)"
        params.append(exclude_pr_number)

    query += " ORDER BY created_at DESC LIMIT ?"
    params.append(limit)
    rows = conn.execute(query, params).fetchall()
    return [_row_to_record(row) for row in rows]


def _maybe_prune_ai_history(
    conn: duckdb.DuckDBPyConnection,
    *,
    user_id: str,
    capability_id: str,
) -> int:
    """Best-effort env-driven pruning hook for long-running deployments."""
    deleted = 0
    raw_days = os.getenv("HANDSFREE_AI_HISTORY_RETENTION_DAYS", "").strip()
    if raw_days:
        try:
            retention_days = int(raw_days)
        except ValueError:
            retention_days = -1
        if retention_days >= 0:
            deleted += prune_ai_history_records(conn, older_than_days=retention_days)

    raw_max_records = os.getenv("HANDSFREE_AI_HISTORY_MAX_RECORDS_PER_USER", "").strip()
    if raw_max_records:
        try:
            max_records = int(raw_max_records)
        except ValueError:
            max_records = -1
        if max_records >= 0:
            deleted += prune_ai_history_records_to_limit(
                conn,
                user_id=user_id,
                capability_id=capability_id,
                max_records=max_records,
            )
    return deleted


def _row_to_record(row: tuple[object, ...]) -> AIHistoryRecord:
    return AIHistoryRecord(
        id=str(row[0]),
        user_id=str(row[1]),
        capability_id=str(row[2]),
        repo=row[3] if row[3] is None else str(row[3]),
        pr_number=None if row[4] is None else int(row[4]),
        failure_target=row[5] if row[5] is None else str(row[5]),
        failure_target_type=row[6] if row[6] is None else str(row[6]),
        ipfs_cid=str(row[7]),
        created_at=row[8],
    )
