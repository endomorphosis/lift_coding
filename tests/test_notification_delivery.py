"""Tests for notification delivery provider."""

import os

import pytest

from handsfree.db import init_db
from handsfree.db.notification_subscriptions import create_subscription
from handsfree.db.notifications import create_notification
from handsfree.notifications import DevLoggerProvider, get_notification_provider


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


class TestDevLoggerProvider:
    """Test the DevLoggerProvider."""

    def test_send_notification(self):
        """Test sending a notification via DevLoggerProvider."""
        provider = DevLoggerProvider()

        result = provider.send(
            subscription_endpoint="https://push.example.com/test",
            notification_data={
                "id": "notif-123",
                "event_type": "test_event",
                "message": "Test notification",
            },
        )

        assert result["ok"] is True
        assert "message" in result
        assert "delivery_id" in result
        assert result["message"] == "Notification logged (dev mode)"

    def test_send_with_subscription_keys(self):
        """Test sending with subscription keys (ignored by logger)."""
        provider = DevLoggerProvider()

        result = provider.send(
            subscription_endpoint="https://push.example.com/test",
            notification_data={"message": "Test"},
            subscription_keys={"auth": "secret", "p256dh": "key"},
        )

        assert result["ok"] is True


class TestGetNotificationProvider:
    """Test get_notification_provider factory function."""

    def test_returns_none_by_default(self):
        """Test that provider is None when not configured."""
        # Clear environment variable
        os.environ.pop("HANDSFREE_NOTIFICATION_PROVIDER", None)

        provider = get_notification_provider()
        assert provider is None

    def test_returns_logger_provider_when_configured(self):
        """Test that logger provider is returned when configured."""
        os.environ["HANDSFREE_NOTIFICATION_PROVIDER"] = "logger"
        provider = get_notification_provider()
        assert isinstance(provider, DevLoggerProvider)

        os.environ["HANDSFREE_NOTIFICATION_PROVIDER"] = "dev"
        provider = get_notification_provider()
        assert isinstance(provider, DevLoggerProvider)

        # Clean up
        os.environ.pop("HANDSFREE_NOTIFICATION_PROVIDER", None)


class TestNotificationDelivery:
    """Test notification delivery integration."""

    def test_notification_delivered_when_provider_enabled(self, db_conn, test_user_id, monkeypatch):
        """Test that notifications are delivered when provider is enabled."""
        # Enable dev logger provider
        monkeypatch.setenv("HANDSFREE_NOTIFICATION_PROVIDER", "logger")

        # Create a subscription for the user
        create_subscription(
            conn=db_conn,
            user_id=test_user_id,
            endpoint="https://push.example.com/test-endpoint",
            subscription_keys={"auth": "secret"},
        )

        # Track delivery calls
        delivery_calls = []

        original_send = DevLoggerProvider.send

        def mock_send(self, subscription_endpoint, notification_data, subscription_keys=None):
            delivery_calls.append(
                {
                    "endpoint": subscription_endpoint,
                    "data": notification_data,
                    "keys": subscription_keys,
                }
            )
            return original_send(self, subscription_endpoint, notification_data, subscription_keys)

        monkeypatch.setattr(DevLoggerProvider, "send", mock_send)

        # Create a notification (should trigger delivery)
        create_notification(
            conn=db_conn,
            user_id=test_user_id,
            event_type="test_event",
            message="Test notification message",
            metadata={"key": "value"},
        )

        # Verify delivery was called
        assert len(delivery_calls) == 1
        assert delivery_calls[0]["endpoint"] == "https://push.example.com/test-endpoint"
        assert delivery_calls[0]["data"]["event_type"] == "test_event"
        assert delivery_calls[0]["data"]["message"] == "Test notification message"
        assert delivery_calls[0]["keys"] == {"auth": "secret"}

    def test_notification_not_delivered_when_provider_disabled(
        self, db_conn, test_user_id, monkeypatch
    ):
        """Test that notifications are not delivered when provider is disabled."""
        # Disable provider
        monkeypatch.delenv("HANDSFREE_NOTIFICATION_PROVIDER", raising=False)

        # Create a subscription
        create_subscription(
            conn=db_conn,
            user_id=test_user_id,
            endpoint="https://push.example.com/test-endpoint",
        )

        # Track delivery calls
        delivery_calls = []

        def mock_send(self, subscription_endpoint, notification_data, subscription_keys=None):
            delivery_calls.append(True)
            return {"ok": True}

        monkeypatch.setattr(DevLoggerProvider, "send", mock_send)

        # Create a notification
        create_notification(
            conn=db_conn,
            user_id=test_user_id,
            event_type="test_event",
            message="Test message",
        )

        # Verify delivery was NOT called (provider disabled)
        assert len(delivery_calls) == 0

    def test_notification_not_delivered_when_no_subscriptions(
        self, db_conn, test_user_id, monkeypatch
    ):
        """Test that nothing happens when user has no subscriptions."""
        # Enable provider
        monkeypatch.setenv("HANDSFREE_NOTIFICATION_PROVIDER", "logger")

        # Don't create any subscriptions
        delivery_calls = []

        def mock_send(self, subscription_endpoint, notification_data, subscription_keys=None):
            delivery_calls.append(True)
            return {"ok": True}

        monkeypatch.setattr(DevLoggerProvider, "send", mock_send)

        # Create a notification
        create_notification(
            conn=db_conn,
            user_id=test_user_id,
            event_type="test_event",
            message="Test message",
        )

        # Verify delivery was NOT called (no subscriptions)
        assert len(delivery_calls) == 0

    def test_notification_delivered_to_multiple_subscriptions(
        self, db_conn, test_user_id, monkeypatch
    ):
        """Test that notifications are delivered to all user subscriptions."""
        # Enable provider
        monkeypatch.setenv("HANDSFREE_NOTIFICATION_PROVIDER", "logger")

        # Create multiple subscriptions
        create_subscription(
            conn=db_conn,
            user_id=test_user_id,
            endpoint="https://push.example.com/endpoint1",
        )
        create_subscription(
            conn=db_conn,
            user_id=test_user_id,
            endpoint="https://push.example.com/endpoint2",
        )

        # Track delivery calls
        delivery_calls = []

        def mock_send(self, subscription_endpoint, notification_data, subscription_keys=None):
            delivery_calls.append(subscription_endpoint)
            return {"ok": True}

        monkeypatch.setattr(DevLoggerProvider, "send", mock_send)

        # Create a notification
        create_notification(
            conn=db_conn,
            user_id=test_user_id,
            event_type="test_event",
            message="Test message",
        )

        # Verify delivery was called for both subscriptions
        assert len(delivery_calls) == 2
        assert "https://push.example.com/endpoint1" in delivery_calls
        assert "https://push.example.com/endpoint2" in delivery_calls

    def test_delivery_failure_does_not_break_notification_creation(
        self, db_conn, test_user_id, monkeypatch
    ):
        """Test that delivery failures don't prevent notification creation."""
        # Enable provider
        monkeypatch.setenv("HANDSFREE_NOTIFICATION_PROVIDER", "logger")

        # Create a subscription
        create_subscription(
            conn=db_conn,
            user_id=test_user_id,
            endpoint="https://push.example.com/failing-endpoint",
        )

        # Make provider.send raise an exception
        def mock_send(self, subscription_endpoint, notification_data, subscription_keys=None):
            raise Exception("Simulated delivery failure")

        monkeypatch.setattr(DevLoggerProvider, "send", mock_send)

        # Create a notification (should succeed despite delivery failure)
        notification = create_notification(
            conn=db_conn,
            user_id=test_user_id,
            event_type="test_event",
            message="Test message",
        )

        # Verify notification was created
        assert notification.id is not None
        assert notification.message == "Test message"

        # Verify notification is retrievable via polling
        from handsfree.db.notifications import list_notifications

        notifications = list_notifications(conn=db_conn, user_id=test_user_id)
        assert len(notifications) >= 1
        assert any(n.id == notification.id for n in notifications)


class TestBackwardCompatibility:
    """Test that polling-based notifications still work."""

    def test_polling_still_works_with_provider_enabled(self, test_user_id, monkeypatch):
        """Test that GET /v1/notifications still works when push is enabled."""
        from fastapi.testclient import TestClient

        from handsfree.api import app, get_db

        # Enable provider
        monkeypatch.setenv("HANDSFREE_NOTIFICATION_PROVIDER", "logger")

        # Get the API's database connection
        db = get_db()

        # Create a subscription (to enable push)
        create_subscription(
            conn=db,
            user_id=test_user_id,
            endpoint="https://push.example.com/test",
        )

        # Create a notification
        create_notification(
            conn=db,
            user_id=test_user_id,
            event_type="test_event",
            message="Test message",
        )

        # Poll via API
        client = TestClient(app)
        response = client.get(
            "/v1/notifications",
            headers={"X-User-ID": test_user_id},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["count"] >= 1

    def test_polling_still_works_with_provider_disabled(self, test_user_id, monkeypatch):
        """Test that GET /v1/notifications still works when push is disabled."""
        from fastapi.testclient import TestClient

        from handsfree.api import app, get_db

        # Disable provider
        monkeypatch.delenv("HANDSFREE_NOTIFICATION_PROVIDER", raising=False)

        # Get the API's database connection
        db = get_db()

        # Create a notification
        create_notification(
            conn=db,
            user_id=test_user_id,
            event_type="test_event",
            message="Test message without push",
        )

        # Poll via API
        client = TestClient(app)
        response = client.get(
            "/v1/notifications",
            headers={"X-User-ID": test_user_id},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["count"] >= 1
