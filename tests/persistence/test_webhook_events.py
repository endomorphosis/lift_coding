"""Tests for webhook events persistence."""

from src.handsfree.persistence import (
    create_webhook_event,
    get_webhook_events,
)


def test_create_webhook_event(db_conn):
    """Test storing a webhook event."""
    event_id = create_webhook_event(
        db_conn,
        source="github",
        signature_ok=True,
        payload={"action": "opened", "number": 123},
        event_type="pull_request",
        delivery_id="abc-123",
    )

    assert event_id is not None


def test_webhook_event_signature_verification(db_conn):
    """Test storing webhook events with signature verification status."""
    # Valid signature
    create_webhook_event(
        db_conn,
        source="github",
        signature_ok=True,
        payload={"test": "data"},
    )

    # Invalid signature
    create_webhook_event(
        db_conn,
        source="github",
        signature_ok=False,
        payload={"test": "data"},
    )

    # Query valid events
    valid_events = get_webhook_events(db_conn, signature_ok=True)
    assert len(valid_events) >= 1
    assert all(event["signature_ok"] is True for event in valid_events)

    # Query invalid events
    invalid_events = get_webhook_events(db_conn, signature_ok=False)
    assert len(invalid_events) >= 1
    assert all(event["signature_ok"] is False for event in invalid_events)


def test_get_webhook_events_by_source(db_conn):
    """Test filtering webhook events by source."""
    create_webhook_event(db_conn, source="github", signature_ok=True, payload={})
    create_webhook_event(db_conn, source="github", signature_ok=True, payload={})
    create_webhook_event(db_conn, source="gitlab", signature_ok=True, payload={})

    github_events = get_webhook_events(db_conn, source="github")
    assert len(github_events) == 2
    assert all(event["source"] == "github" for event in github_events)


def test_get_webhook_events_by_type(db_conn):
    """Test filtering webhook events by event type."""
    create_webhook_event(
        db_conn,
        source="github",
        signature_ok=True,
        payload={},
        event_type="pull_request",
    )
    create_webhook_event(
        db_conn,
        source="github",
        signature_ok=True,
        payload={},
        event_type="push",
    )

    pr_events = get_webhook_events(db_conn, event_type="pull_request")
    assert len(pr_events) == 1
    assert pr_events[0]["event_type"] == "pull_request"


def test_webhook_event_payload_storage(db_conn):
    """Test that complex payloads are stored and retrieved correctly."""
    complex_payload = {
        "action": "opened",
        "pull_request": {
            "id": 12345,
            "number": 42,
            "title": "Fix bug",
            "user": {"login": "testuser"},
        },
        "repository": {"full_name": "owner/repo"},
    }

    create_webhook_event(
        db_conn,
        source="github",
        signature_ok=True,
        payload=complex_payload,
        event_type="pull_request",
    )

    events = get_webhook_events(db_conn, event_type="pull_request")
    assert len(events) >= 1

    event = events[0]
    assert event["payload"]["action"] == "opened"
    assert event["payload"]["pull_request"]["number"] == 42
    assert event["payload"]["repository"]["full_name"] == "owner/repo"


def test_webhook_events_ordering(db_conn):
    """Test that webhook events are returned in reverse chronological order."""
    create_webhook_event(db_conn, source="github", signature_ok=True, payload={"seq": 1})
    create_webhook_event(db_conn, source="github", signature_ok=True, payload={"seq": 2})
    create_webhook_event(db_conn, source="github", signature_ok=True, payload={"seq": 3})

    events = get_webhook_events(db_conn, source="github")

    # Most recent should be first
    assert events[0]["payload"]["seq"] == 3
    assert events[1]["payload"]["seq"] == 2
    assert events[2]["payload"]["seq"] == 1
