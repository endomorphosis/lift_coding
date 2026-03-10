"""Tests for persisted AI backend-policy snapshots."""

from datetime import UTC, datetime
import uuid

import pytest

from handsfree.ai.observability import build_ai_backend_policy_report
from handsfree.db import init_db
from handsfree.db.action_logs import write_action_log
from handsfree.db.ai_backend_policy_snapshots import (
    get_ai_backend_policy_snapshots,
    get_latest_ai_backend_policy_snapshot,
    get_next_ai_backend_policy_snapshot_capture,
    prune_ai_backend_policy_snapshots,
    prune_ai_backend_policy_snapshots_to_limit,
    store_ai_backend_policy_snapshot,
)
from handsfree.github.auth import GhCliTokenProvider


@pytest.fixture
def db_conn():
    """Create an in-memory database connection for testing."""
    conn = init_db(":memory:")
    yield conn
    conn.close()


def test_store_and_read_ai_backend_policy_snapshot(db_conn, monkeypatch):
    """Snapshots should persist the current typed backend-policy report."""
    user_id = str(uuid.uuid4())
    monkeypatch.delenv("HANDS_FREE_GITHUB_MODE", raising=False)
    monkeypatch.delenv("GITHUB_LIVE_MODE", raising=False)
    monkeypatch.delenv("GITHUB_TOKEN", raising=False)
    monkeypatch.setattr(GhCliTokenProvider, "get_token", lambda self: None)

    write_action_log(
        db_conn,
        user_id=user_id,
        action_type="ai.execute.github.pr.accelerated_summary",
        ok=True,
        result={
            "capability_id": "github.pr.accelerated_summary",
            "policy_resolution": {
                "requested_workflow": "pr_rag_summary",
                "resolved_workflow": "accelerated_pr_summary",
                "requested_capability_id": None,
                "resolved_capability_id": "github.pr.accelerated_summary",
                "policy_applied": True,
            },
        },
    )

    report = build_ai_backend_policy_report(db_conn, user_id=user_id, limit=20)
    snapshot = store_ai_backend_policy_snapshot(db_conn, user_id=user_id, report=report)
    stored = get_ai_backend_policy_snapshots(db_conn, user_id=user_id, limit=10)

    assert snapshot.user_id == user_id
    assert snapshot.summary_backend == report.policy.summary_backend
    assert snapshot.failure_backend == report.policy.failure_backend
    assert isinstance(snapshot.created_at, datetime)
    assert snapshot.created_at.tzinfo == UTC
    assert snapshot.reused is False
    assert len(stored) == 1
    assert stored[0].id == snapshot.id
    assert stored[0].reused is False
    assert stored[0].remap_counts == {"pr_rag_summary->accelerated_pr_summary": 1}
    assert stored[0].top_remaps[0]["remap_key"] == "pr_rag_summary->accelerated_pr_summary"
    assert stored[0].top_capabilities["remapped"][0]["capability_id"] == "github.pr.accelerated_summary"


def test_get_ai_backend_policy_snapshots_orders_newest_first(db_conn):
    """Snapshot listing should return newest snapshots first."""
    user_id = str(uuid.uuid4())
    db_conn.execute(
        """
        INSERT INTO ai_backend_policy_snapshots
        (id, user_id, summary_backend, failure_backend, github_auth_source,
         github_live_mode_requested, ai_execute_logs, policy_applied_count,
         remap_counts, top_capabilities, top_remaps, created_at)
        VALUES
        ('older', ?, 'default', 'default', 'fixtures', false, 1, 0, '{}', '{}', '[]', ?),
        ('newer', ?, 'accelerated', 'composite', 'gh_cli', true, 2, 1, '{}', '{}', '[]', ?)
        """,
        [
            user_id,
            datetime(2026, 3, 8, 10, 0, tzinfo=UTC),
            user_id,
            datetime(2026, 3, 8, 12, 0, tzinfo=UTC),
        ],
    )

    snapshots = get_ai_backend_policy_snapshots(db_conn, user_id=user_id, limit=10)

    assert [snapshot.id for snapshot in snapshots] == ["newer", "older"]


def test_get_latest_ai_backend_policy_snapshot_returns_newest(db_conn):
    """Latest snapshot helper should return the newest persisted snapshot."""
    user_id = str(uuid.uuid4())
    db_conn.execute(
        """
        INSERT INTO ai_backend_policy_snapshots
        (id, user_id, summary_backend, failure_backend, github_auth_source,
         github_live_mode_requested, ai_execute_logs, policy_applied_count,
         remap_counts, top_capabilities, top_remaps, created_at)
        VALUES
        ('older', ?, 'default', 'default', 'fixtures', false, 1, 0, '{}', '{}', '[]', ?),
        ('newer', ?, 'accelerated', 'composite', 'gh_cli', true, 2, 1, '{}', '{}', '[]', ?)
        """,
        [
            user_id,
            datetime(2026, 3, 8, 10, 0, tzinfo=UTC),
            user_id,
            datetime(2026, 3, 8, 12, 0, tzinfo=UTC),
        ],
    )

    latest = get_latest_ai_backend_policy_snapshot(db_conn, user_id=user_id)

    assert latest is not None
    assert latest.id == "newer"


def test_prune_ai_backend_policy_snapshots_by_age(db_conn):
    """Age-based pruning should remove older snapshot rows."""
    user_id = str(uuid.uuid4())
    db_conn.execute(
        """
        INSERT INTO ai_backend_policy_snapshots
        (id, user_id, summary_backend, failure_backend, github_auth_source,
         github_live_mode_requested, ai_execute_logs, policy_applied_count,
         remap_counts, top_capabilities, top_remaps, created_at)
        VALUES
        ('old', ?, 'default', 'default', 'fixtures', false, 1, 0, '{}', '{}', '[]', ?),
        ('new', ?, 'default', 'default', 'fixtures', false, 1, 0, '{}', '{}', '[]', ?)
        """,
        [
            user_id,
            datetime(2026, 3, 1, 10, 0, tzinfo=UTC),
            user_id,
            datetime.now(UTC),
        ],
    )

    deleted = prune_ai_backend_policy_snapshots(db_conn, older_than_days=3)
    snapshots = get_ai_backend_policy_snapshots(db_conn, user_id=user_id, limit=10)

    assert deleted == 1
    assert [snapshot.id for snapshot in snapshots] == ["new"]


def test_prune_ai_backend_policy_snapshots_to_limit(db_conn):
    """Count-based pruning should keep only the newest user snapshots."""
    user_id = str(uuid.uuid4())
    db_conn.execute(
        """
        INSERT INTO ai_backend_policy_snapshots
        (id, user_id, summary_backend, failure_backend, github_auth_source,
         github_live_mode_requested, ai_execute_logs, policy_applied_count,
         remap_counts, top_capabilities, top_remaps, created_at)
        VALUES
        ('first', ?, 'default', 'default', 'fixtures', false, 1, 0, '{}', '{}', '[]', ?),
        ('second', ?, 'default', 'default', 'fixtures', false, 1, 0, '{}', '{}', '[]', ?),
        ('third', ?, 'default', 'default', 'fixtures', false, 1, 0, '{}', '{}', '[]', ?)
        """,
        [
            user_id,
            datetime(2026, 3, 8, 10, 0, tzinfo=UTC),
            user_id,
            datetime(2026, 3, 8, 11, 0, tzinfo=UTC),
            user_id,
            datetime(2026, 3, 8, 12, 0, tzinfo=UTC),
        ],
    )

    deleted = prune_ai_backend_policy_snapshots_to_limit(
        db_conn,
        user_id=user_id,
        max_records=2,
    )
    snapshots = get_ai_backend_policy_snapshots(db_conn, user_id=user_id, limit=10)

    assert deleted == 1
    assert [snapshot.id for snapshot in snapshots] == ["third", "second"]


def test_store_ai_backend_policy_snapshot_honors_env_pruning(db_conn, monkeypatch):
    """Snapshot store should apply env-driven pruning opportunistically."""
    user_id = str(uuid.uuid4())
    monkeypatch.setenv("HANDSFREE_AI_POLICY_SNAPSHOT_MAX_RECORDS_PER_USER", "2")
    monkeypatch.delenv("HANDSFREE_AI_POLICY_SNAPSHOT_RETENTION_DAYS", raising=False)
    monkeypatch.delenv("HANDS_FREE_GITHUB_MODE", raising=False)
    monkeypatch.delenv("GITHUB_LIVE_MODE", raising=False)
    monkeypatch.delenv("GITHUB_TOKEN", raising=False)
    monkeypatch.setattr(GhCliTokenProvider, "get_token", lambda self: None)

    for i in range(3):
        write_action_log(
            db_conn,
            user_id=user_id,
            action_type="ai.execute.github.pr.rag_summary",
            ok=True,
            result={"capability_id": "github.pr.rag_summary"},
        )
        report = build_ai_backend_policy_report(db_conn, user_id=user_id, limit=20)
        store_ai_backend_policy_snapshot(db_conn, user_id=user_id, report=report)

    snapshots = get_ai_backend_policy_snapshots(db_conn, user_id=user_id, limit=10)
    assert len(snapshots) == 2


def test_store_ai_backend_policy_snapshot_reuses_recent_snapshot(db_conn, monkeypatch):
    """Minimum snapshot interval should prevent near-duplicate inserts."""
    user_id = str(uuid.uuid4())
    monkeypatch.setenv("HANDSFREE_AI_POLICY_SNAPSHOT_MIN_INTERVAL_SECONDS", "3600")
    monkeypatch.delenv("HANDSFREE_AI_POLICY_SNAPSHOT_MAX_RECORDS_PER_USER", raising=False)
    monkeypatch.delenv("HANDSFREE_AI_POLICY_SNAPSHOT_RETENTION_DAYS", raising=False)
    monkeypatch.delenv("HANDS_FREE_GITHUB_MODE", raising=False)
    monkeypatch.delenv("GITHUB_LIVE_MODE", raising=False)
    monkeypatch.delenv("GITHUB_TOKEN", raising=False)
    monkeypatch.setattr(GhCliTokenProvider, "get_token", lambda self: None)

    write_action_log(
        db_conn,
        user_id=user_id,
        action_type="ai.execute.github.pr.rag_summary",
        ok=True,
        result={"capability_id": "github.pr.rag_summary"},
    )
    report = build_ai_backend_policy_report(db_conn, user_id=user_id, limit=20)
    first = store_ai_backend_policy_snapshot(db_conn, user_id=user_id, report=report)
    second = store_ai_backend_policy_snapshot(db_conn, user_id=user_id, report=report)
    snapshots = get_ai_backend_policy_snapshots(db_conn, user_id=user_id, limit=10)

    assert second.id == first.id
    assert first.reused is False
    assert second.reused is True
    assert len(snapshots) == 1


def test_get_next_ai_backend_policy_snapshot_capture_reports_reuse(db_conn, monkeypatch):
    """Snapshot listing helper should describe whether the next capture would reuse."""
    user_id = str(uuid.uuid4())
    monkeypatch.setenv("HANDSFREE_AI_POLICY_SNAPSHOT_MIN_INTERVAL_SECONDS", "3600")
    monkeypatch.delenv("HANDSFREE_AI_POLICY_SNAPSHOT_MAX_RECORDS_PER_USER", raising=False)
    monkeypatch.delenv("HANDSFREE_AI_POLICY_SNAPSHOT_RETENTION_DAYS", raising=False)
    monkeypatch.delenv("HANDS_FREE_GITHUB_MODE", raising=False)
    monkeypatch.delenv("GITHUB_LIVE_MODE", raising=False)
    monkeypatch.delenv("GITHUB_TOKEN", raising=False)
    monkeypatch.setattr(GhCliTokenProvider, "get_token", lambda self: None)

    write_action_log(
        db_conn,
        user_id=user_id,
        action_type="ai.execute.github.pr.rag_summary",
        ok=True,
        result={"capability_id": "github.pr.rag_summary"},
    )
    report = build_ai_backend_policy_report(db_conn, user_id=user_id, limit=20)
    snapshot = store_ai_backend_policy_snapshot(db_conn, user_id=user_id, report=report)

    mode, next_snapshot = get_next_ai_backend_policy_snapshot_capture(db_conn, user_id=user_id)

    assert mode == "reused"
    assert next_snapshot is not None
    assert next_snapshot.id == snapshot.id
    assert next_snapshot.reused is True


def test_get_next_ai_backend_policy_snapshot_capture_reports_create_without_reuse_window(
    db_conn,
    monkeypatch,
):
    """Without a reusable interval, the next capture should create a new snapshot."""
    user_id = str(uuid.uuid4())
    monkeypatch.delenv("HANDSFREE_AI_POLICY_SNAPSHOT_MIN_INTERVAL_SECONDS", raising=False)
    monkeypatch.delenv("HANDSFREE_AI_POLICY_SNAPSHOT_MAX_RECORDS_PER_USER", raising=False)
    monkeypatch.delenv("HANDSFREE_AI_POLICY_SNAPSHOT_RETENTION_DAYS", raising=False)
    monkeypatch.delenv("HANDS_FREE_GITHUB_MODE", raising=False)
    monkeypatch.delenv("GITHUB_LIVE_MODE", raising=False)
    monkeypatch.delenv("GITHUB_TOKEN", raising=False)
    monkeypatch.setattr(GhCliTokenProvider, "get_token", lambda self: None)

    write_action_log(
        db_conn,
        user_id=user_id,
        action_type="ai.execute.github.pr.rag_summary",
        ok=True,
        result={"capability_id": "github.pr.rag_summary"},
    )
    report = build_ai_backend_policy_report(db_conn, user_id=user_id, limit=20)
    snapshot = store_ai_backend_policy_snapshot(db_conn, user_id=user_id, report=report)

    mode, next_snapshot = get_next_ai_backend_policy_snapshot_capture(db_conn, user_id=user_id)

    assert mode == "created"
    assert next_snapshot is not None
    assert next_snapshot.id == snapshot.id
    assert next_snapshot.reused is False


def test_backend_policy_report_exposes_snapshot_policy_config(db_conn, monkeypatch):
    """Report policy should surface effective snapshot retention and reuse config."""
    user_id = str(uuid.uuid4())
    monkeypatch.setenv("HANDSFREE_AI_POLICY_SNAPSHOT_RETENTION_DAYS", "14")
    monkeypatch.setenv("HANDSFREE_AI_POLICY_SNAPSHOT_MAX_RECORDS_PER_USER", "9")
    monkeypatch.setenv("HANDSFREE_AI_POLICY_SNAPSHOT_MIN_INTERVAL_SECONDS", "120")
    monkeypatch.delenv("HANDS_FREE_GITHUB_MODE", raising=False)
    monkeypatch.delenv("GITHUB_LIVE_MODE", raising=False)
    monkeypatch.delenv("GITHUB_TOKEN", raising=False)
    monkeypatch.setattr(GhCliTokenProvider, "get_token", lambda self: None)

    report = build_ai_backend_policy_report(db_conn, user_id=user_id, limit=5)

    assert report.policy.snapshot_retention_days == 14
    assert report.policy.snapshot_max_records_per_user == 9
    assert report.policy.snapshot_min_interval_seconds == 120
