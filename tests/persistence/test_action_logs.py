"""Tests for action logs persistence."""

from src.handsfree.persistence import (
    create_action_log,
    get_action_logs,
)
from tests.persistence.conftest import create_test_user


def test_create_action_log(db_conn, test_user_id):
    """Test creating an action log entry."""
    log_id = create_action_log(
        db_conn,
        user_id=test_user_id,
        action_type="merge_pr",
        ok=True,
        target="owner/repo#123",
        request={"pr_number": 123},
        result={"status": "merged"},
    )

    assert log_id is not None


def test_action_log_with_idempotency_key(db_conn, test_user_id):
    """Test that idempotency_key prevents duplicates."""
    idempotency_key = "test-key-123"

    # Create first log
    log_id_1 = create_action_log(
        db_conn,
        user_id=test_user_id,
        action_type="test",
        ok=True,
        idempotency_key=idempotency_key,
    )

    # Create second log with same idempotency_key
    log_id_2 = create_action_log(
        db_conn,
        user_id=test_user_id,
        action_type="test",
        ok=True,
        idempotency_key=idempotency_key,
    )

    # Should return the same ID
    assert log_id_1 == log_id_2

    # Verify only one entry exists
    logs = get_action_logs(db_conn, user_id=test_user_id)
    assert len(logs) == 1


def test_get_action_logs_no_filter(db_conn, test_user_id):
    """Test retrieving action logs without filters."""
    # Create some logs
    for i in range(3):
        create_action_log(
            db_conn,
            user_id=test_user_id,
            action_type=f"action_{i}",
            ok=True,
        )

    logs = get_action_logs(db_conn)
    assert len(logs) >= 3


def test_get_action_logs_by_user(db_conn):
    """Test filtering action logs by user."""
    user_1 = create_test_user(db_conn)
    user_2 = create_test_user(db_conn)

    # Create logs for different users
    create_action_log(db_conn, user_id=user_1, action_type="action_1", ok=True)
    create_action_log(db_conn, user_id=user_1, action_type="action_2", ok=True)
    create_action_log(db_conn, user_id=user_2, action_type="action_3", ok=True)

    # Query by user_1
    logs = get_action_logs(db_conn, user_id=user_1)
    assert len(logs) == 2
    assert all(log["user_id"] == str(user_1) for log in logs)


def test_get_action_logs_by_type(db_conn, test_user_id):
    """Test filtering action logs by action type."""
    create_action_log(db_conn, user_id=test_user_id, action_type="merge_pr", ok=True)
    create_action_log(db_conn, user_id=test_user_id, action_type="merge_pr", ok=True)
    create_action_log(db_conn, user_id=test_user_id, action_type="rerun_workflow", ok=True)

    logs = get_action_logs(db_conn, action_type="merge_pr")
    assert len(logs) == 2
    assert all(log["action_type"] == "merge_pr" for log in logs)


def test_action_log_with_all_fields(db_conn, test_user_id):
    """Test creating an action log with all fields populated."""
    create_action_log(
        db_conn,
        user_id=test_user_id,
        action_type="complex_action",
        ok=False,
        target="owner/repo#456",
        request={"param1": "value1", "param2": 123},
        result={"error": "Something went wrong", "details": {"code": 500}},
        idempotency_key="unique-key-456",
    )

    logs = get_action_logs(db_conn, user_id=test_user_id)
    assert len(logs) >= 1

    log = logs[0]
    assert log["action_type"] == "complex_action"
    assert log["ok"] is False
    assert log["target"] == "owner/repo#456"
    assert log["request"]["param1"] == "value1"
    assert log["result"]["error"] == "Something went wrong"
    assert log["idempotency_key"] == "unique-key-456"


def test_action_logs_ordering(db_conn, test_user_id):
    """Test that action logs are returned in reverse chronological order."""
    # Create logs in sequence
    create_action_log(db_conn, user_id=test_user_id, action_type="first", ok=True)
    create_action_log(db_conn, user_id=test_user_id, action_type="second", ok=True)
    create_action_log(db_conn, user_id=test_user_id, action_type="third", ok=True)

    logs = get_action_logs(db_conn, user_id=test_user_id)

    # Most recent should be first
    assert logs[0]["action_type"] == "third"
    assert logs[1]["action_type"] == "second"
    assert logs[2]["action_type"] == "first"
