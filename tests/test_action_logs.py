"""Tests for action logs persistence."""

import uuid

import pytest

from handsfree.db import init_db
from handsfree.db.action_logs import (
    get_action_log_by_id,
    get_action_logs,
    write_action_log,
)


@pytest.fixture
def db_conn():
    """Create an in-memory database connection for testing."""
    conn = init_db(":memory:")
    yield conn
    conn.close()


def test_write_action_log(db_conn):
    """Test writing an action log."""
    user_id = str(uuid.uuid4())
    log = write_action_log(
        db_conn,
        user_id=user_id,
        action_type="merge_pr",
        ok=True,
        target="owner/repo#123",
        request={"method": "squash"},
        result={"sha": "abc123"},
    )

    assert log.id is not None
    assert log.user_id == user_id
    assert log.action_type == "merge_pr"
    assert log.ok is True
    assert log.target == "owner/repo#123"
    assert log.request == {"method": "squash"}
    assert log.result == {"sha": "abc123"}


def test_write_action_log_with_idempotency_key(db_conn):
    """Test that idempotency keys prevent duplicate logs."""
    user_id = str(uuid.uuid4())
    idempotency_key = "unique-key-123"

    # First write should succeed
    log1 = write_action_log(
        db_conn,
        user_id=user_id,
        action_type="test",
        ok=True,
        idempotency_key=idempotency_key,
    )
    assert log1.idempotency_key == idempotency_key

    # Second write with same key should fail
    with pytest.raises(ValueError, match="already exists"):
        write_action_log(
            db_conn,
            user_id=user_id,
            action_type="test",
            ok=True,
            idempotency_key=idempotency_key,
        )


def test_get_action_logs(db_conn):
    """Test querying action logs."""
    user_id = str(uuid.uuid4())

    # Create multiple logs
    write_action_log(db_conn, user_id=user_id, action_type="merge_pr", ok=True)
    write_action_log(db_conn, user_id=user_id, action_type="rerun_workflow", ok=True)
    write_action_log(db_conn, user_id=user_id, action_type="merge_pr", ok=False)

    # Get all logs for user
    logs = get_action_logs(db_conn, user_id=user_id)
    assert len(logs) == 3

    # Filter by action type
    merge_logs = get_action_logs(db_conn, user_id=user_id, action_type="merge_pr")
    assert len(merge_logs) == 2


def test_get_action_logs_with_limit(db_conn):
    """Test limiting the number of returned logs."""
    user_id = str(uuid.uuid4())

    # Create 5 logs
    for _i in range(5):
        write_action_log(db_conn, user_id=user_id, action_type="test", ok=True)

    # Request only 3
    logs = get_action_logs(db_conn, user_id=user_id, limit=3)
    assert len(logs) == 3


def test_get_action_log_by_id(db_conn):
    """Test retrieving a specific action log."""
    user_id = str(uuid.uuid4())
    created = write_action_log(
        db_conn,
        user_id=user_id,
        action_type="test",
        ok=True,
        target="test-target",
    )

    retrieved = get_action_log_by_id(db_conn, created.id)

    assert retrieved is not None
    assert retrieved.id == created.id
    assert retrieved.user_id == user_id
    assert retrieved.action_type == "test"
    assert retrieved.target == "test-target"


def test_get_nonexistent_action_log(db_conn):
    """Test retrieving a non-existent action log."""
    result = get_action_log_by_id(db_conn, str(uuid.uuid4()))
    assert result is None


def test_action_log_ordering(db_conn):
    """Test that logs are returned in descending order by creation time."""
    user_id = str(uuid.uuid4())

    # Create logs with different action types
    log1 = write_action_log(db_conn, user_id=user_id, action_type="first", ok=True)
    log2 = write_action_log(db_conn, user_id=user_id, action_type="second", ok=True)
    log3 = write_action_log(db_conn, user_id=user_id, action_type="third", ok=True)

    # Retrieve logs
    logs = get_action_logs(db_conn, user_id=user_id)

    # Should be in reverse order (newest first)
    assert logs[0].id == log3.id
    assert logs[1].id == log2.id
    assert logs[2].id == log1.id
