"""Tests for webhook events persistence."""

import uuid

import pytest

from handsfree.db import init_db
from handsfree.db.webhook_events import (
    get_webhook_event_by_id,
    get_webhook_events,
    store_webhook_event,
)


@pytest.fixture
def db_conn():
    """Create an in-memory database connection for testing."""
    conn = init_db(":memory:")
    yield conn
    conn.close()


def test_store_webhook_event(db_conn):
    """Test storing a webhook event."""
    event = store_webhook_event(
        db_conn,
        source="github",
        signature_ok=True,
        event_type="push",
        delivery_id="12345",
        payload={"ref": "refs/heads/main", "commits": []},
    )

    assert event.id is not None
    assert event.source == "github"
    assert event.signature_ok is True
    assert event.event_type == "push"
    assert event.delivery_id == "12345"
    assert event.payload == {"ref": "refs/heads/main", "commits": []}


def test_store_webhook_event_with_invalid_signature(db_conn):
    """Test storing an event with invalid signature."""
    event = store_webhook_event(
        db_conn,
        source="github",
        signature_ok=False,
        event_type="pull_request",
        payload={"action": "opened"},
    )

    assert event.signature_ok is False


def test_get_webhook_events(db_conn):
    """Test querying webhook events."""
    # Create multiple events
    store_webhook_event(db_conn, source="github", signature_ok=True, event_type="push")
    store_webhook_event(db_conn, source="github", signature_ok=True, event_type="pull_request")
    store_webhook_event(db_conn, source="github", signature_ok=False, event_type="push")

    # Get all events
    events = get_webhook_events(db_conn)
    assert len(events) == 3

    # Filter by event type
    push_events = get_webhook_events(db_conn, event_type="push")
    assert len(push_events) == 2

    # Filter by signature validity
    valid_events = get_webhook_events(db_conn, signature_ok=True)
    assert len(valid_events) == 2


def test_get_webhook_events_with_limit(db_conn):
    """Test limiting the number of returned events."""
    # Create 5 events
    for _i in range(5):
        store_webhook_event(db_conn, source="github", signature_ok=True)

    # Request only 3
    events = get_webhook_events(db_conn, limit=3)
    assert len(events) == 3


def test_get_webhook_event_by_id(db_conn):
    """Test retrieving a specific webhook event."""
    created = store_webhook_event(
        db_conn,
        source="github",
        signature_ok=True,
        event_type="issue_comment",
        payload={"action": "created"},
    )

    retrieved = get_webhook_event_by_id(db_conn, created.id)

    assert retrieved is not None
    assert retrieved.id == created.id
    assert retrieved.source == "github"
    assert retrieved.event_type == "issue_comment"
    assert retrieved.payload == {"action": "created"}


def test_get_nonexistent_webhook_event(db_conn):
    """Test retrieving a non-existent webhook event."""
    result = get_webhook_event_by_id(db_conn, str(uuid.uuid4()))
    assert result is None


def test_webhook_event_ordering(db_conn):
    """Test that events are returned in descending order by received time."""
    # Create events
    event1 = store_webhook_event(db_conn, source="github", signature_ok=True, event_type="first")
    event2 = store_webhook_event(db_conn, source="github", signature_ok=True, event_type="second")
    event3 = store_webhook_event(db_conn, source="github", signature_ok=True, event_type="third")

    # Retrieve events
    events = get_webhook_events(db_conn)

    # Should be in reverse order (newest first)
    assert events[0].id == event3.id
    assert events[1].id == event2.id
    assert events[2].id == event1.id


def test_webhook_event_with_complex_payload(db_conn):
    """Test storing and retrieving complex JSON payloads."""
    complex_payload = {
        "action": "opened",
        "pull_request": {
            "number": 123,
            "title": "Fix bug",
            "labels": [{"name": "bug"}, {"name": "urgent"}],
        },
        "repository": {
            "full_name": "owner/repo",
            "private": False,
        },
    }

    event = store_webhook_event(
        db_conn,
        source="github",
        signature_ok=True,
        event_type="pull_request",
        payload=complex_payload,
    )

    retrieved = get_webhook_event_by_id(db_conn, event.id)
    assert retrieved is not None
    assert retrieved.payload == complex_payload
