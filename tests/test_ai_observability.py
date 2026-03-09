"""Tests for AI backend policy observability helpers."""

from datetime import UTC, datetime, timedelta
import uuid

import pytest

from handsfree.ai.observability import (
    build_ai_backend_policy_history_report,
    build_ai_backend_policy_report,
)
from handsfree.db import init_db
from handsfree.db.action_logs import write_action_log
from handsfree.github.auth import GhCliTokenProvider


@pytest.fixture
def db_conn():
    """Create an in-memory database connection for testing."""
    conn = init_db(":memory:")
    yield conn
    conn.close()


def test_build_ai_backend_policy_report_returns_typed_summary(db_conn, monkeypatch):
    """Report should summarize recent AI execution logs and remaps."""
    user_id = str(uuid.uuid4())
    monkeypatch.setenv("HANDSFREE_AI_DEFAULT_SUMMARY_BACKEND", "accelerated")
    monkeypatch.setenv("HANDSFREE_AI_DEFAULT_FAILURE_BACKEND", "composite")
    monkeypatch.setenv("HANDS_FREE_GITHUB_MODE", "live")
    monkeypatch.delenv("GITHUB_TOKEN", raising=False)
    monkeypatch.setattr(GhCliTokenProvider, "get_token", lambda self: "gho_cli_token")

    write_action_log(
        db_conn,
        user_id=user_id,
        action_type="ai.execute.github.pr.accelerated_summary",
        ok=True,
        result={
            "policy_resolution": {
                "requested_workflow": "pr_rag_summary",
                "resolved_workflow": "accelerated_pr_summary",
                "requested_capability_id": None,
                "resolved_capability_id": "github.pr.accelerated_summary",
                "policy_applied": True,
            }
        },
    )
    write_action_log(
        db_conn,
        user_id=user_id,
        action_type="ai.execute.github.check.failure_rag_explain",
        ok=True,
        result={
            "policy_resolution": {
                "requested_workflow": "failure_rag_explain",
                "resolved_workflow": "failure_rag_explain",
                "requested_capability_id": None,
                "resolved_capability_id": "github.check.failure_rag_explain",
                "policy_applied": False,
            }
        },
    )
    write_action_log(
        db_conn,
        user_id=user_id,
        action_type="request_review",
        ok=True,
        result={"ok": True},
    )

    report = build_ai_backend_policy_report(db_conn, user_id=user_id, limit=50)

    assert report.policy.summary_backend == "accelerated"
    assert report.policy.failure_backend == "composite"
    assert report.policy.github_auth_source == "gh_cli"
    assert report.policy.github_live_mode_requested is True
    assert report.recent_window.log_limit == 50
    assert report.recent_window.ai_execute_logs == 2
    assert report.recent_window.policy_applied_count == 1
    assert [(item.capability_id, item.count) for item in report.top_capabilities.overall] == [
        ("github.check.failure_rag_explain", 1),
        ("github.pr.accelerated_summary", 1),
    ]
    assert [(item.capability_id, item.count) for item in report.top_capabilities.remapped] == [
        ("github.pr.accelerated_summary", 1)
    ]
    assert [(item.capability_id, item.count) for item in report.top_capabilities.direct] == [
        ("github.check.failure_rag_explain", 1)
    ]
    assert [(item.remap_key, item.count) for item in report.top_remaps] == [
        ("pr_rag_summary->accelerated_pr_summary", 1)
    ]
    assert report.remapped_capability_counts == {"github.pr.accelerated_summary": 1}
    assert report.direct_capability_counts == {"github.check.failure_rag_explain": 1}
    assert report.requested_workflow_counts == {"pr_rag_summary": 1}
    assert report.resolved_workflow_counts == {"accelerated_pr_summary": 1}
    assert report.remap_counts == {"pr_rag_summary->accelerated_pr_summary": 1}
    assert report.action_counts == {
        "ai.execute.github.check.failure_rag_explain": 1,
        "ai.execute.github.pr.accelerated_summary": 1,
    }


def test_build_ai_backend_policy_report_ignores_other_users_and_missing_policy_data(
    db_conn,
    monkeypatch,
):
    """Report should only use matching-user AI logs with valid policy metadata."""
    user_id = str(uuid.uuid4())
    other_user_id = str(uuid.uuid4())
    monkeypatch.delenv("HANDS_FREE_GITHUB_MODE", raising=False)
    monkeypatch.delenv("GITHUB_LIVE_MODE", raising=False)
    monkeypatch.delenv("GITHUB_TOKEN", raising=False)
    monkeypatch.setattr(GhCliTokenProvider, "get_token", lambda self: None)

    write_action_log(
        db_conn,
        user_id=user_id,
        action_type="ai.execute.github.pr.rag_summary",
        ok=True,
        result={"ok": True},
    )
    write_action_log(
        db_conn,
        user_id=other_user_id,
        action_type="ai.execute.github.pr.accelerated_summary",
        ok=True,
        result={
            "policy_resolution": {
                "requested_workflow": "pr_rag_summary",
                "resolved_workflow": "accelerated_pr_summary",
                "requested_capability_id": None,
                "resolved_capability_id": "github.pr.accelerated_summary",
                "policy_applied": True,
            }
        },
    )

    report = build_ai_backend_policy_report(db_conn, user_id=user_id, limit=10)

    assert report.policy.github_auth_source == "fixtures"
    assert report.policy.github_live_mode_requested is False
    assert report.recent_window.ai_execute_logs == 1
    assert report.recent_window.policy_applied_count == 0
    assert [(item.capability_id, item.count) for item in report.top_capabilities.overall] == [
        ("github.pr.rag_summary", 1)
    ]
    assert report.top_remaps == []
    assert report.remapped_capability_counts == {}
    assert report.direct_capability_counts == {"github.pr.rag_summary": 1}
    assert report.requested_workflow_counts == {}
    assert report.resolved_workflow_counts == {}
    assert report.remap_counts == {}
    assert report.action_counts == {"ai.execute.github.pr.rag_summary": 1}


def test_build_ai_backend_policy_report_includes_time_buckets(db_conn, monkeypatch):
    """Report should separate recent remaps into fixed time buckets."""
    user_id = str(uuid.uuid4())
    monkeypatch.delenv("HANDS_FREE_GITHUB_MODE", raising=False)
    monkeypatch.delenv("GITHUB_LIVE_MODE", raising=False)
    monkeypatch.delenv("GITHUB_TOKEN", raising=False)
    monkeypatch.setattr(GhCliTokenProvider, "get_token", lambda self: None)

    recent = write_action_log(
        db_conn,
        user_id=user_id,
        action_type="ai.execute.github.pr.accelerated_summary",
        ok=True,
        result={
            "policy_resolution": {
                "requested_workflow": "pr_rag_summary",
                "resolved_workflow": "accelerated_pr_summary",
                "requested_capability_id": None,
                "resolved_capability_id": "github.pr.accelerated_summary",
                "policy_applied": True,
            }
        },
    )
    older = write_action_log(
        db_conn,
        user_id=user_id,
        action_type="ai.execute.github.check.accelerated_failure_explain",
        ok=True,
        result={
            "policy_resolution": {
                "requested_workflow": "failure_rag_explain",
                "resolved_workflow": "accelerated_failure_explain",
                "requested_capability_id": None,
                "resolved_capability_id": "github.check.accelerated_failure_explain",
                "policy_applied": True,
            }
        },
    )

    db_conn.execute(
        "UPDATE action_logs SET created_at = ? WHERE id = ?",
        [datetime.now(UTC) - timedelta(hours=2), older.id],
    )
    db_conn.execute(
        "UPDATE action_logs SET created_at = ? WHERE id = ?",
        [datetime.now(UTC) - timedelta(days=2), recent.id],
    )

    latest = write_action_log(
        db_conn,
        user_id=user_id,
        action_type="ai.execute.github.pr.accelerated_summary",
        ok=True,
        result={
            "policy_resolution": {
                "requested_workflow": "pr_rag_summary",
                "resolved_workflow": "accelerated_pr_summary",
                "requested_capability_id": None,
                "resolved_capability_id": "github.pr.accelerated_summary",
                "policy_applied": True,
            }
        },
    )
    assert latest is not None

    report = build_ai_backend_policy_report(db_conn, user_id=user_id, limit=20)

    assert report.time_buckets["last_hour"].ai_execute_logs == 1
    assert report.time_buckets["last_hour"].policy_applied_count == 1
    assert report.time_buckets["last_hour"].remapped_capability_counts == {
        "github.pr.accelerated_summary": 1
    }
    assert report.time_buckets["last_hour"].direct_capability_counts == {}
    assert report.time_buckets["last_hour"].requested_workflow_counts == {"pr_rag_summary": 1}
    assert report.time_buckets["last_hour"].resolved_workflow_counts == {
        "accelerated_pr_summary": 1
    }
    assert report.time_buckets["last_hour"].remap_counts == {
        "pr_rag_summary->accelerated_pr_summary": 1
    }
    assert report.time_buckets["last_24_hours"].ai_execute_logs == 2
    assert report.time_buckets["last_24_hours"].policy_applied_count == 2
    assert report.time_buckets["last_24_hours"].remapped_capability_counts == {
        "github.check.accelerated_failure_explain": 1,
        "github.pr.accelerated_summary": 1,
    }
    assert report.time_buckets["last_24_hours"].direct_capability_counts == {}
    assert report.time_buckets["last_24_hours"].requested_workflow_counts == {
        "failure_rag_explain": 1,
        "pr_rag_summary": 1,
    }
    assert report.time_buckets["last_24_hours"].resolved_workflow_counts == {
        "accelerated_failure_explain": 1,
        "accelerated_pr_summary": 1,
    }
    assert report.time_buckets["last_24_hours"].remap_counts == {
        "failure_rag_explain->accelerated_failure_explain": 1,
        "pr_rag_summary->accelerated_pr_summary": 1,
    }


def test_build_ai_backend_policy_report_prefers_env_auth_source(db_conn, monkeypatch):
    """Report should identify env-token auth before gh CLI fallback."""
    user_id = str(uuid.uuid4())
    monkeypatch.setenv("GITHUB_TOKEN", "ghp_test_token")
    monkeypatch.setenv("GITHUB_LIVE_MODE", "true")
    monkeypatch.setattr(GhCliTokenProvider, "get_token", lambda self: "gho_cli_token")

    report = build_ai_backend_policy_report(db_conn, user_id=user_id, limit=5)

    assert report.policy.github_auth_source == "env_token"
    assert report.policy.github_live_mode_requested is True


def test_build_ai_backend_policy_history_report_buckets_activity(db_conn, monkeypatch):
    """History report should bucket AI executions and remaps over time."""
    user_id = str(uuid.uuid4())
    monkeypatch.delenv("HANDS_FREE_GITHUB_MODE", raising=False)
    monkeypatch.delenv("GITHUB_LIVE_MODE", raising=False)
    monkeypatch.delenv("GITHUB_TOKEN", raising=False)
    monkeypatch.setattr(GhCliTokenProvider, "get_token", lambda self: None)

    first = write_action_log(
        db_conn,
        user_id=user_id,
        action_type="ai.execute.github.pr.accelerated_summary",
        ok=True,
        result={
            "policy_resolution": {
                "requested_workflow": "pr_rag_summary",
                "resolved_workflow": "accelerated_pr_summary",
                "requested_capability_id": None,
                "resolved_capability_id": "github.pr.accelerated_summary",
                "policy_applied": True,
            }
        },
    )
    second = write_action_log(
        db_conn,
        user_id=user_id,
        action_type="ai.execute.github.check.failure_rag_explain",
        ok=True,
        result={
            "policy_resolution": {
                "requested_workflow": "failure_rag_explain",
                "resolved_workflow": "failure_rag_explain",
                "requested_capability_id": None,
                "resolved_capability_id": "github.check.failure_rag_explain",
                "policy_applied": False,
            }
        },
    )

    now = datetime.now(UTC)
    db_conn.execute(
        "UPDATE action_logs SET created_at = ? WHERE id = ?",
        [now - timedelta(hours=3, minutes=30), first.id],
    )
    db_conn.execute(
        "UPDATE action_logs SET created_at = ? WHERE id = ?",
        [now - timedelta(hours=1, minutes=15), second.id],
    )

    report = build_ai_backend_policy_history_report(
        db_conn,
        user_id=user_id,
        window_hours=4,
        bucket_hours=2,
        limit=20,
    )

    assert report.window_hours == 4
    assert report.bucket_hours == 2
    assert len(report.buckets) == 2
    assert report.policy.github_auth_source == "fixtures"
    assert report.buckets[0].ai_execute_logs == 1
    assert report.buckets[0].policy_applied_count == 1
    assert report.buckets[0].remap_counts == {"pr_rag_summary->accelerated_pr_summary": 1}
    assert report.buckets[1].ai_execute_logs == 1
    assert report.buckets[1].policy_applied_count == 0
    assert report.buckets[1].remap_counts == {}
