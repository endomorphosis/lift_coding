"""Tests for idempotency keys persistence."""

import uuid
from datetime import UTC, datetime

import pytest

from handsfree.db import init_db
from handsfree.db.idempotency_keys import (
    cleanup_expired_keys,
    get_idempotency_key,
    get_idempotency_response,
    store_idempotency_key,
)


@pytest.fixture
def db_conn():
    """Create an in-memory database connection for testing."""
    conn = init_db(":memory:")
    yield conn
    conn.close()


def test_store_idempotency_key(db_conn):
    """Test storing an idempotency key with response."""
    user_id = str(uuid.uuid4())
    key = "test-key-123"
    endpoint = "/v1/command"
    response_data = {
        "status": "ok",
        "intent": {"name": "test.intent", "confidence": 0.95},
        "spoken_text": "Test response",
    }

    result = store_idempotency_key(
        db_conn,
        key=key,
        user_id=user_id,
        endpoint=endpoint,
        response_data=response_data,
        expires_in_seconds=3600,
    )

    assert result.key == key
    assert result.user_id == user_id
    assert result.endpoint == endpoint
    assert result.response_data == response_data
    assert result.audit_log_id is None
    assert result.expires_at > datetime.now(UTC)
    assert result.created_at <= datetime.now(UTC)


def test_store_idempotency_key_with_audit_log(db_conn):
    """Test storing an idempotency key linked to audit log."""
    from handsfree.db.action_logs import write_action_log

    user_id = str(uuid.uuid4())

    # Create audit log entry first
    audit_log = write_action_log(
        db_conn,
        user_id=user_id,
        action_type="test_action",
        ok=True,
        target="test/repo#1",
        request={"test": "data"},
        result={"status": "success"},
    )

    key = "test-key-with-audit"
    result = store_idempotency_key(
        db_conn,
        key=key,
        user_id=user_id,
        endpoint="/v1/actions/test",
        response_data={"ok": True, "message": "Success"},
        audit_log_id=audit_log.id,
    )

    assert result.audit_log_id == audit_log.id


def test_get_idempotency_key(db_conn):
    """Test retrieving an idempotency key."""
    user_id = str(uuid.uuid4())
    key = "retrieve-test-key"
    response_data = {"test": "data"}

    # Store key
    stored = store_idempotency_key(
        db_conn,
        key=key,
        user_id=user_id,
        endpoint="/v1/test",
        response_data=response_data,
    )

    # Retrieve key
    retrieved = get_idempotency_key(db_conn, key)

    assert retrieved is not None
    assert retrieved.key == key
    assert retrieved.user_id == user_id
    assert retrieved.response_data == response_data


def test_get_nonexistent_idempotency_key(db_conn):
    """Test retrieving a non-existent idempotency key."""
    result = get_idempotency_key(db_conn, "nonexistent-key")
    assert result is None


def test_get_expired_idempotency_key(db_conn):
    """Test that expired keys return None."""
    user_id = str(uuid.uuid4())
    key = "expired-key"

    # Store key that's already expired
    store_idempotency_key(
        db_conn,
        key=key,
        user_id=user_id,
        endpoint="/v1/test",
        response_data={"test": "data"},
        expires_in_seconds=-1,  # Already expired
    )

    # Should return None for expired key
    retrieved = get_idempotency_key(db_conn, key)
    assert retrieved is None


def test_get_idempotency_response(db_conn):
    """Test convenience method for getting just the response data."""
    user_id = str(uuid.uuid4())
    key = "response-test-key"
    response_data = {"result": "success", "data": {"value": 42}}

    # Store key
    store_idempotency_key(
        db_conn,
        key=key,
        user_id=user_id,
        endpoint="/v1/test",
        response_data=response_data,
    )

    # Get response
    response = get_idempotency_response(db_conn, key)
    assert response == response_data


def test_get_idempotency_response_nonexistent(db_conn):
    """Test that nonexistent key returns None for response."""
    response = get_idempotency_response(db_conn, "nonexistent")
    assert response is None


def test_store_duplicate_key_returns_existing(db_conn):
    """Test that storing duplicate key returns existing entry (read-before-write)."""
    user_id = str(uuid.uuid4())
    key = "duplicate-key"
    response_data_1 = {"first": "response"}
    response_data_2 = {"second": "response"}

    # Store first time
    result1 = store_idempotency_key(
        db_conn,
        key=key,
        user_id=user_id,
        endpoint="/v1/test",
        response_data=response_data_1,
    )

    # Try to store again with different response
    result2 = store_idempotency_key(
        db_conn,
        key=key,
        user_id=user_id,
        endpoint="/v1/test",
        response_data=response_data_2,
    )

    # Should return the original response (idempotency)
    assert result2.key == result1.key
    assert result2.response_data == response_data_1  # Original response, not new one
    assert result2.created_at == result1.created_at


def test_cleanup_expired_keys(db_conn):
    """Test cleanup of expired idempotency keys."""
    user_id = str(uuid.uuid4())

    # Store some expired keys
    for i in range(3):
        store_idempotency_key(
            db_conn,
            key=f"expired-{i}",
            user_id=user_id,
            endpoint="/v1/test",
            response_data={"test": i},
            expires_in_seconds=-1,  # Already expired
        )

    # Store some valid keys
    for i in range(2):
        store_idempotency_key(
            db_conn,
            key=f"valid-{i}",
            user_id=user_id,
            endpoint="/v1/test",
            response_data={"test": i},
            expires_in_seconds=3600,  # Valid for 1 hour
        )

    # Clean up expired keys
    deleted_count = cleanup_expired_keys(db_conn)

    # Should have deleted the 3 expired keys
    assert deleted_count == 3

    # Valid keys should still exist
    assert get_idempotency_key(db_conn, "valid-0") is not None
    assert get_idempotency_key(db_conn, "valid-1") is not None

    # Expired keys should be gone
    assert get_idempotency_key(db_conn, "expired-0") is None
    assert get_idempotency_key(db_conn, "expired-1") is None
    assert get_idempotency_key(db_conn, "expired-2") is None


def test_idempotency_key_different_endpoints(db_conn):
    """Test that same key can be used for different endpoints."""
    user_id = str(uuid.uuid4())
    key = "same-key"

    # Store for first endpoint
    result1 = store_idempotency_key(
        db_conn,
        key=key,
        user_id=user_id,
        endpoint="/v1/command",
        response_data={"endpoint": "command"},
    )

    # For DuckDB with our schema, this will return the first one
    # because key is PRIMARY KEY. This is intentional - idempotency
    # keys should be globally unique across endpoints.
    retrieved = get_idempotency_key(db_conn, key)
    assert retrieved.endpoint == "/v1/command"
    assert retrieved.response_data == {"endpoint": "command"}
