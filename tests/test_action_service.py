"""Tests for shared action execution services."""

from handsfree.actions import DirectActionRequest, execute_confirmed_action
from handsfree.actions.service import (
    execute_direct_action,
    process_direct_action_request,
    process_direct_action_request_detailed,
)
from handsfree.db import init_db
from handsfree.db.idempotency_keys import get_idempotency_response
from handsfree.db.repo_policies import create_or_update_repo_policy


def test_execute_confirmed_comment_fixture(monkeypatch):
    """Confirmed comment actions should execute through CLI fixture mode."""
    monkeypatch.setenv("HANDSFREE_CLI_FIXTURE_MODE", "true")
    monkeypatch.setenv("HANDSFREE_GH_CLI_ENABLED", "true")
    conn = init_db(":memory:")
    try:
        response = execute_confirmed_action(
            conn=conn,
            user_id="00000000-0000-0000-0000-000000000001",
            action_type="comment",
            action_payload={
                "repo": "test/repo",
                "pr_number": 123,
                "comment_body": "looks good",
            },
            via_router_token=True,
        )

        assert response.status == "ok"
        assert "comment posted" in response.spoken_text.lower()
    finally:
        conn.close()


def test_execute_confirmed_merge_fixture(monkeypatch):
    """Confirmed merge actions should execute through CLI fixture mode."""
    monkeypatch.setenv("HANDSFREE_CLI_FIXTURE_MODE", "true")
    monkeypatch.setenv("HANDSFREE_GH_CLI_ENABLED", "true")
    conn = init_db(":memory:")
    try:
        response = execute_confirmed_action(
            conn=conn,
            user_id="00000000-0000-0000-0000-000000000001",
            action_type="merge",
            action_payload={
                "repo": "test/repo",
                "pr_number": 200,
                "merge_method": "squash",
            },
        )

        assert response.status == "ok"
        assert "merged successfully" in response.spoken_text.lower()
    finally:
        conn.close()


def test_execute_direct_request_review_fixture(monkeypatch):
    """Direct request-review actions should execute through CLI fixture mode."""
    monkeypatch.setenv("HANDSFREE_CLI_FIXTURE_MODE", "true")
    monkeypatch.setenv("HANDSFREE_GH_CLI_ENABLED", "true")
    conn = init_db(":memory:")
    try:
        response = execute_direct_action(
            conn=conn,
            user_id="00000000-0000-0000-0000-000000000001",
            action_type="request_review",
            action_payload={
                "repo": "test/repo",
                "pr_number": 100,
                "reviewers": ["alice"],
            },
        )

        assert response.ok is True
        assert "review requested" in response.message.lower()
    finally:
        conn.close()


def test_execute_direct_rerun_fixture(monkeypatch):
    """Direct rerun actions should execute through fixture mode."""
    monkeypatch.setenv("HANDSFREE_CLI_FIXTURE_MODE", "true")
    monkeypatch.setenv("HANDSFREE_GH_CLI_ENABLED", "true")
    conn = init_db(":memory:")
    try:
        response = execute_direct_action(
            conn=conn,
            user_id="00000000-0000-0000-0000-000000000001",
            action_type="rerun",
            action_payload={
                "repo": "test/repo",
                "pr_number": 77,
            },
        )

        assert response.ok is True
        assert "workflow checks re-run" in response.message.lower()
    finally:
        conn.close()


def test_execute_direct_comment_fixture(monkeypatch):
    """Direct comment actions should execute through CLI fixture mode."""
    monkeypatch.setenv("HANDSFREE_CLI_FIXTURE_MODE", "true")
    monkeypatch.setenv("HANDSFREE_GH_CLI_ENABLED", "true")
    conn = init_db(":memory:")
    try:
        response = execute_direct_action(
            conn=conn,
            user_id="00000000-0000-0000-0000-000000000001",
            action_type="comment",
            action_payload={
                "repo": "test/repo",
                "pr_number": 123,
                "comment_body": "looks good",
            },
        )

        assert response.ok is True
        assert "comment posted" in response.message.lower()
    finally:
        conn.close()


def test_process_direct_action_request_executes_and_persists_idempotency(monkeypatch):
    """Shared direct-action helper should execute and persist cached results."""
    monkeypatch.setenv("HANDSFREE_CLI_FIXTURE_MODE", "true")
    monkeypatch.setenv("HANDSFREE_GH_CLI_ENABLED", "true")
    user_id = "00000000-0000-0000-0000-000000000001"
    conn = init_db(":memory:")
    try:
        create_or_update_repo_policy(
            conn,
            user_id=user_id,
            repo_full_name="test/repo",
            allow_request_review=True,
            require_confirmation=False,
        )
        cache: dict[str, object] = {}
        request = DirectActionRequest(
            endpoint="/v1/actions/request-review",
            action_type="request_review",
            execution_action_type="request_review",
            pending_action_type="request_review",
            repo="test/repo",
            pr_number=123,
            action_payload={"repo": "test/repo", "pr_number": 123, "reviewers": ["alice"]},
            log_request={"reviewers": ["alice"]},
            pending_summary="Request review from alice on test/repo#123",
            idempotency_key="idem-123",
            anomaly_request_data={"reviewers": ["alice"]},
        )

        response = process_direct_action_request(conn, user_id, request, cache)

        assert response.ok is True
        assert "review requested" in response.message.lower()
        cached = get_idempotency_response(conn, "idem-123")
        assert cached is not None
        assert cached["ok"] is True
    finally:
        conn.close()


def test_process_direct_action_request_creates_pending_confirmation(monkeypatch):
    """Shared direct-action helper should persist confirmation responses too."""
    user_id = "00000000-0000-0000-0000-000000000001"
    conn = init_db(":memory:")
    try:
        create_or_update_repo_policy(
            conn,
            user_id=user_id,
            repo_full_name="owner/repo",
            allow_comment=True,
            require_confirmation=True,
        )
        cache: dict[str, object] = {}
        request = DirectActionRequest(
            endpoint="/v1/actions/comment",
            action_type="comment",
            execution_action_type="comment",
            pending_action_type="comment",
            repo="owner/repo",
            pr_number=55,
            action_payload={
                "repo": "owner/repo",
                "pr_number": 55,
                "comment_body": "please update tests",
            },
            log_request={"comment_body": "please update tests"},
            pending_summary="Post comment on owner/repo#55: please update tests",
            idempotency_key="idem-comment-55",
            anomaly_request_data={"comment_body": "please update tests"},
        )

        response = process_direct_action_request(conn, user_id, request, cache)

        assert response.ok is False
        assert "confirmation required" in response.message.lower()
        cached = get_idempotency_response(conn, "idem-comment-55")
        assert cached is not None
        assert cached["ok"] is False
    finally:
        conn.close()


def test_process_direct_action_request_detailed_returns_pending_metadata():
    """Detailed direct-action helper should preserve pending action metadata."""
    user_id = "00000000-0000-0000-0000-000000000001"
    conn = init_db(":memory:")
    try:
        create_or_update_repo_policy(
            conn,
            user_id=user_id,
            repo_full_name="owner/repo",
            allow_request_review=True,
            require_confirmation=True,
        )
        cache: dict[str, object] = {}
        request = DirectActionRequest(
            endpoint="/v1/command",
            action_type="request_review",
            execution_action_type="request_review",
            pending_action_type="request_review",
            repo="owner/repo",
            pr_number=77,
            action_payload={
                "repo": "owner/repo",
                "pr_number": 77,
                "reviewers": ["alice"],
            },
            log_request={"reviewers": ["alice"]},
            pending_summary="Request review from alice on owner/repo#77",
            anomaly_request_data={"reviewers": ["alice"]},
        )

        detailed = process_direct_action_request_detailed(conn, user_id, request, cache)

        assert detailed.action_result is not None
        assert detailed.action_result.ok is False
        assert detailed.pending_token is not None
        assert detailed.pending_expires_at is not None
        assert detailed.pending_summary == "Request review from alice on owner/repo#77"
    finally:
        conn.close()
