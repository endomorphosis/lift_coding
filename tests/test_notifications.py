"""Tests for notifications persistence and retrieval."""

from datetime import UTC, datetime

import pytest

from handsfree.db import init_db
from handsfree.db.notifications import create_notification, list_notifications


@pytest.fixture
def db_conn():
    """Create an in-memory database connection for testing."""
    conn = init_db(":memory:")
    yield conn
    conn.close()


@pytest.fixture
def test_user_id():
    """Generate a consistent test user ID."""
    return "00000000-0000-0000-0000-000000000001"


class TestNotificationCreation:
    """Test notification creation."""

    def test_create_basic_notification(self, db_conn, test_user_id):
        """Test creating a basic notification."""
        notif = create_notification(
            conn=db_conn,
            user_id=test_user_id,
            event_type="test_event",
            message="Test notification message",
            metadata={"key": "value"},
        )

        assert notif.id is not None
        assert notif.user_id == test_user_id
        assert notif.event_type == "test_event"
        assert notif.message == "Test notification message"
        assert notif.metadata == {"key": "value"}
        assert notif.created_at is not None

    def test_create_notification_without_metadata(self, db_conn, test_user_id):
        """Test creating a notification without metadata."""
        notif = create_notification(
            conn=db_conn,
            user_id=test_user_id,
            event_type="simple_event",
            message="Simple message",
        )

        assert notif.id is not None
        assert notif.metadata is None

    def test_create_notification_with_string_user_id(self, db_conn):
        """Test creating a notification with non-UUID user ID."""
        notif = create_notification(
            conn=db_conn,
            user_id="test-user-string",
            event_type="test",
            message="Test message",
        )

        assert notif.id is not None
        assert notif.user_id == "test-user-string"


class TestNotificationRetrieval:
    """Test notification retrieval."""

    def test_list_notifications_basic(self, db_conn, test_user_id):
        """Test listing notifications for a user."""
        # Create multiple notifications
        create_notification(
            conn=db_conn,
            user_id=test_user_id,
            event_type="event1",
            message="Message 1",
        )
        create_notification(
            conn=db_conn,
            user_id=test_user_id,
            event_type="event2",
            message="Message 2",
        )
        create_notification(
            conn=db_conn,
            user_id=test_user_id,
            event_type="event3",
            message="Message 3",
        )

        # List notifications
        notifs = list_notifications(conn=db_conn, user_id=test_user_id)

        assert len(notifs) == 3
        # Should be ordered by created_at DESC
        assert notifs[0].message == "Message 3"
        assert notifs[1].message == "Message 2"
        assert notifs[2].message == "Message 1"

    def test_list_notifications_with_limit(self, db_conn, test_user_id):
        """Test listing notifications with a limit."""
        # Create multiple notifications
        for i in range(10):
            create_notification(
                conn=db_conn,
                user_id=test_user_id,
                event_type=f"event{i}",
                message=f"Message {i}",
            )

        # List with limit
        notifs = list_notifications(conn=db_conn, user_id=test_user_id, limit=5)

        assert len(notifs) == 5

    def test_list_notifications_with_since_filter(self, db_conn, test_user_id):
        """Test listing notifications with since timestamp filter."""
        # Create notifications at different times
        create_notification(
            conn=db_conn,
            user_id=test_user_id,
            event_type="old_event",
            message="Old message",
        )

        # Get current time for filtering
        cutoff_time = datetime.now(UTC)

        # Sleep a tiny bit to ensure different timestamp
        import time

        time.sleep(0.01)

        create_notification(
            conn=db_conn,
            user_id=test_user_id,
            event_type="new_event",
            message="New message",
        )

        # List notifications since cutoff
        notifs = list_notifications(conn=db_conn, user_id=test_user_id, since=cutoff_time)

        assert len(notifs) == 1
        assert notifs[0].message == "New message"

    def test_list_notifications_filters_by_user(self, db_conn, test_user_id, test_user_id_2):
        """Test that list_notifications filters by user_id."""
        # Create notifications for two users
        create_notification(
            conn=db_conn,
            user_id=test_user_id,
            event_type="user1_event",
            message="User 1 message",
        )
        create_notification(
            conn=db_conn,
            user_id=test_user_id_2,
            event_type="user2_event",
            message="User 2 message",
        )

        # List for first user
        notifs1 = list_notifications(conn=db_conn, user_id=test_user_id)
        assert len(notifs1) == 1
        assert notifs1[0].message == "User 1 message"

        # List for second user
        notifs2 = list_notifications(conn=db_conn, user_id=test_user_id_2)
        assert len(notifs2) == 1
        assert notifs2[0].message == "User 2 message"

    def test_list_notifications_empty(self, db_conn, test_user_id):
        """Test listing notifications when there are none."""
        notifs = list_notifications(conn=db_conn, user_id=test_user_id)
        assert len(notifs) == 0


class TestNotificationConversion:
    """Test notification conversion to dict."""

    def test_to_dict(self, db_conn, test_user_id):
        """Test converting notification to dict."""
        notif = create_notification(
            conn=db_conn,
            user_id=test_user_id,
            event_type="test_event",
            message="Test message",
            metadata={"key": "value"},
        )

        notif_dict = notif.to_dict()

        assert notif_dict["id"] == notif.id
        assert notif_dict["user_id"] == test_user_id
        assert notif_dict["event_type"] == "test_event"
        assert notif_dict["message"] == "Test message"
        assert notif_dict["metadata"] == {"key": "value"}
        assert "created_at" in notif_dict

    def test_to_dict_with_null_metadata(self, db_conn, test_user_id):
        """Test converting notification with null metadata to dict."""
        notif = create_notification(
            conn=db_conn,
            user_id=test_user_id,
            event_type="test_event",
            message="Test message",
        )

        notif_dict = notif.to_dict()

        assert notif_dict["metadata"] == {}
