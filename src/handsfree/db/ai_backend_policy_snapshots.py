"""Persistence helpers for admin AI backend-policy snapshots."""

from __future__ import annotations

import json
import os
import uuid
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

import duckdb

from handsfree.models import AIBackendPolicyReport


@dataclass
class AIBackendPolicySnapshot:
    """Persisted point-in-time backend-policy snapshot."""

    id: str
    user_id: str
    summary_backend: str
    failure_backend: str
    github_auth_source: str | None
    github_live_mode_requested: bool
    ai_execute_logs: int
    policy_applied_count: int
    remap_counts: dict[str, int]
    top_capabilities: dict[str, object]
    top_remaps: list[dict[str, object]]
    created_at: datetime


def store_ai_backend_policy_snapshot(
    conn: duckdb.DuckDBPyConnection,
    *,
    user_id: str,
    report: AIBackendPolicyReport,
) -> AIBackendPolicySnapshot:
    """Store a point-in-time backend-policy report snapshot."""
    _maybe_prune_ai_backend_policy_snapshots(conn, user_id=user_id)
    existing = _get_reusable_recent_snapshot(conn, user_id=user_id)
    if existing is not None:
        return existing

    snapshot_id = str(uuid.uuid4())
    created_at = datetime.now(UTC)

    top_capabilities = report.top_capabilities.model_dump(mode="json")
    top_remaps = [entry.model_dump(mode="json") for entry in report.top_remaps]

    conn.execute(
        """
        INSERT INTO ai_backend_policy_snapshots
        (id, user_id, summary_backend, failure_backend, github_auth_source,
         github_live_mode_requested, ai_execute_logs, policy_applied_count,
         remap_counts, top_capabilities, top_remaps, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        [
            snapshot_id,
            user_id,
            report.policy.summary_backend,
            report.policy.failure_backend,
            report.policy.github_auth_source,
            report.policy.github_live_mode_requested,
            report.recent_window.ai_execute_logs,
            report.recent_window.policy_applied_count,
            json.dumps(report.remap_counts),
            json.dumps(top_capabilities),
            json.dumps(top_remaps),
            created_at,
        ],
    )

    _maybe_prune_ai_backend_policy_snapshots(conn, user_id=user_id)

    return AIBackendPolicySnapshot(
        id=snapshot_id,
        user_id=user_id,
        summary_backend=report.policy.summary_backend,
        failure_backend=report.policy.failure_backend,
        github_auth_source=report.policy.github_auth_source,
        github_live_mode_requested=report.policy.github_live_mode_requested,
        ai_execute_logs=report.recent_window.ai_execute_logs,
        policy_applied_count=report.recent_window.policy_applied_count,
        remap_counts=dict(report.remap_counts),
        top_capabilities=top_capabilities,
        top_remaps=top_remaps,
        created_at=created_at,
    )


def get_ai_backend_policy_snapshots(
    conn: duckdb.DuckDBPyConnection,
    *,
    user_id: str,
    limit: int = 50,
) -> list[AIBackendPolicySnapshot]:
    """Return recent backend-policy snapshots for a user."""
    rows = conn.execute(
        """
        SELECT id, user_id, summary_backend, failure_backend, github_auth_source,
               github_live_mode_requested, ai_execute_logs, policy_applied_count,
               remap_counts, top_capabilities, top_remaps, created_at
        FROM ai_backend_policy_snapshots
        WHERE user_id = ?
        ORDER BY created_at DESC
        LIMIT ?
        """,
        [user_id, limit],
    ).fetchall()
    return [_row_to_snapshot(row) for row in rows]


def prune_ai_backend_policy_snapshots(
    conn: duckdb.DuckDBPyConnection,
    *,
    older_than_days: int,
) -> int:
    """Delete backend-policy snapshots older than the configured retention window."""
    if older_than_days < 0:
        raise ValueError("older_than_days must be non-negative")

    cutoff = datetime.now(UTC) - timedelta(days=older_than_days)
    rows = conn.execute(
        "DELETE FROM ai_backend_policy_snapshots WHERE created_at < ? RETURNING id",
        [cutoff],
    ).fetchall()
    return len(rows)


def prune_ai_backend_policy_snapshots_to_limit(
    conn: duckdb.DuckDBPyConnection,
    *,
    user_id: str,
    max_records: int,
) -> int:
    """Keep only the newest backend-policy snapshots for a user."""
    if max_records < 0:
        raise ValueError("max_records must be non-negative")

    rows = conn.execute(
        """
        SELECT id
        FROM ai_backend_policy_snapshots
        WHERE user_id = ?
        ORDER BY created_at DESC
        OFFSET ?
        """,
        [user_id, max_records],
    ).fetchall()
    if not rows:
        return 0

    ids = [str(row[0]) for row in rows]
    placeholders = ", ".join(["?"] * len(ids))
    conn.execute(f"DELETE FROM ai_backend_policy_snapshots WHERE id IN ({placeholders})", ids)
    return len(ids)


def _maybe_prune_ai_backend_policy_snapshots(
    conn: duckdb.DuckDBPyConnection,
    *,
    user_id: str,
) -> int:
    """Best-effort env-driven pruning hook for persisted policy snapshots."""
    deleted = 0

    raw_days = os.getenv("HANDSFREE_AI_POLICY_SNAPSHOT_RETENTION_DAYS", "").strip()
    if raw_days:
        try:
            retention_days = int(raw_days)
        except ValueError:
            retention_days = -1
        if retention_days >= 0:
            deleted += prune_ai_backend_policy_snapshots(conn, older_than_days=retention_days)

    raw_max_records = os.getenv("HANDSFREE_AI_POLICY_SNAPSHOT_MAX_RECORDS_PER_USER", "").strip()
    if raw_max_records:
        try:
            max_records = int(raw_max_records)
        except ValueError:
            max_records = -1
        if max_records >= 0:
            deleted += prune_ai_backend_policy_snapshots_to_limit(
                conn,
                user_id=user_id,
                max_records=max_records,
            )

    return deleted


def _get_reusable_recent_snapshot(
    conn: duckdb.DuckDBPyConnection,
    *,
    user_id: str,
) -> AIBackendPolicySnapshot | None:
    """Return the latest snapshot when within the configured reuse interval."""
    raw_seconds = os.getenv("HANDSFREE_AI_POLICY_SNAPSHOT_MIN_INTERVAL_SECONDS", "").strip()
    if not raw_seconds:
        return None
    try:
        min_interval_seconds = int(raw_seconds)
    except ValueError:
        return None
    if min_interval_seconds < 0:
        return None

    row = conn.execute(
        """
        SELECT id, user_id, summary_backend, failure_backend, github_auth_source,
               github_live_mode_requested, ai_execute_logs, policy_applied_count,
               remap_counts, top_capabilities, top_remaps, created_at
        FROM ai_backend_policy_snapshots
        WHERE user_id = ?
        ORDER BY created_at DESC
        LIMIT 1
        """,
        [user_id],
    ).fetchone()
    if not row:
        return None

    snapshot = _row_to_snapshot(row)
    if snapshot.created_at.tzinfo is None:
        now = datetime.now()
        snapshot_created_at = snapshot.created_at
    else:
        now = datetime.now(UTC)
        snapshot_created_at = snapshot.created_at.astimezone(UTC)
    if now - snapshot_created_at <= timedelta(seconds=min_interval_seconds):
        return snapshot
    return None


def _row_to_snapshot(row: tuple[object, ...]) -> AIBackendPolicySnapshot:
    return AIBackendPolicySnapshot(
        id=str(row[0]),
        user_id=str(row[1]),
        summary_backend=str(row[2]),
        failure_backend=str(row[3]),
        github_auth_source=None if row[4] is None else str(row[4]),
        github_live_mode_requested=bool(row[5]),
        ai_execute_logs=int(row[6]),
        policy_applied_count=int(row[7]),
        remap_counts=_load_json_object(row[8]),
        top_capabilities=_load_json_object(row[9]),
        top_remaps=_load_json_array(row[10]),
        created_at=row[11],
    )


def _load_json_object(value: object) -> dict[str, object]:
    if isinstance(value, str) and value:
        loaded = json.loads(value)
        return loaded if isinstance(loaded, dict) else {}
    if isinstance(value, dict):
        return value
    return {}


def _load_json_array(value: object) -> list[dict[str, object]]:
    if isinstance(value, str) and value:
        loaded = json.loads(value)
        return loaded if isinstance(loaded, list) else []
    if isinstance(value, list):
        return value
    return []
