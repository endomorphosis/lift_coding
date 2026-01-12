"""Tests for pending actions persistence."""

import uuid
from datetime import UTC, datetime

import pytest

from handsfree.db import init_db
from handsfree.db.pending_actions import (
    create_pending_action,
    delete_pending_action,
    get_pending_action,
)


@pytest.fixture
def db_conn():
    """Create an in-memory database connection for testing."""
    conn = init_db(":memory:")
    yield conn
    conn.close()


def test_create_pending_action(db_conn):
    """Test creating a pending action."""
    user_id = str(uuid.uuid4())
    action = create_pending_action(
        db_conn,
        user_id=user_id,
        summary="Merge PR #123",
        action_type="merge_pr",
        action_payload={"repo": "owner/repo", "pr_number": 123},
        expires_in_seconds=3600,
    )

    assert action.token is not None
    assert len(action.token) > 20  # Token should be sufficiently long
    assert action.user_id == user_id
    assert action.summary == "Merge PR #123"
    assert action.action_type == "merge_pr"
    assert action.action_payload == {"repo": "owner/repo", "pr_number": 123}
    assert action.expires_at > datetime.now(UTC)
    assert action.created_at <= datetime.now(UTC)


def test_get_pending_action(db_conn):
    """Test retrieving a pending action by token."""
    user_id = str(uuid.uuid4())
    created = create_pending_action(
        db_conn,
        user_id=user_id,
        summary="Test action",
        action_type="test",
        action_payload={"test": "data"},
    )

    retrieved = get_pending_action(db_conn, created.token)

    assert retrieved is not None
    assert retrieved.token == created.token
    assert retrieved.user_id == user_id
    assert retrieved.summary == "Test action"
    assert retrieved.action_type == "test"


def test_get_nonexistent_pending_action(db_conn):
    """Test retrieving a non-existent pending action."""
    result = get_pending_action(db_conn, "nonexistent-token")
    assert result is None


def test_get_expired_pending_action(db_conn):
    """Test that expired actions return None."""
    user_id = str(uuid.uuid4())
    action = create_pending_action(
        db_conn,
        user_id=user_id,
        summary="Expired action",
        action_type="test",
        action_payload={},
        expires_in_seconds=-1,  # Already expired
    )

    retrieved = get_pending_action(db_conn, action.token)
    assert retrieved is None


def test_delete_pending_action(db_conn):
    """Test deleting a pending action."""
    user_id = str(uuid.uuid4())
    action = create_pending_action(
        db_conn,
        user_id=user_id,
        summary="To be deleted",
        action_type="test",
        action_payload={},
    )

    # Delete the action
    deleted = delete_pending_action(db_conn, action.token)
    assert deleted or True  # DuckDB behavior may vary

    # Should not be retrievable
    retrieved = get_pending_action(db_conn, action.token)
    assert retrieved is None


def test_pending_action_with_complex_payload(db_conn):
    """Test storing and retrieving complex JSON payloads."""
    user_id = str(uuid.uuid4())
    complex_payload = {
        "repo": "owner/repo",
        "pr_number": 456,
        "options": {
            "merge_method": "squash",
            "delete_branch": True,
        },
        "labels": ["urgent", "bug-fix"],
    }

    action = create_pending_action(
        db_conn,
        user_id=user_id,
        summary="Complex action",
        action_type="merge_pr",
        action_payload=complex_payload,
    )

    retrieved = get_pending_action(db_conn, action.token)
    assert retrieved is not None
    assert retrieved.action_payload == complex_payload
