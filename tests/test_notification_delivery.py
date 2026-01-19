"""Tests for notification delivery provider."""

import os

import pytest

from handsfree.db import init_db
from handsfree.db.notification_subscriptions import create_subscription
from handsfree.db.notifications import create_notification
from handsfree.notifications import DevLoggerProvider, WebPushProvider, get_notification_provider


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

    def test_returns_webpush_provider_when_configured(self):
        """Test that WebPush provider is returned when configured with VAPID keys."""
        os.environ["HANDSFREE_NOTIFICATION_PROVIDER"] = "webpush"
        os.environ["HANDSFREE_WEBPUSH_VAPID_PUBLIC_KEY"] = "test-public-key"
        os.environ["HANDSFREE_WEBPUSH_VAPID_PRIVATE_KEY"] = "test-private-key"
        os.environ["HANDSFREE_WEBPUSH_VAPID_SUBJECT"] = "mailto:test@example.com"

        provider = get_notification_provider()
        assert isinstance(provider, WebPushProvider)
        assert provider.vapid_public_key == "test-public-key"
        assert provider.vapid_private_key == "test-private-key"
        assert provider.vapid_subject == "mailto:test@example.com"

        # Clean up
        os.environ.pop("HANDSFREE_NOTIFICATION_PROVIDER", None)
        os.environ.pop("HANDSFREE_WEBPUSH_VAPID_PUBLIC_KEY", None)
        os.environ.pop("HANDSFREE_WEBPUSH_VAPID_PRIVATE_KEY", None)
        os.environ.pop("HANDSFREE_WEBPUSH_VAPID_SUBJECT", None)

    def test_returns_none_when_webpush_missing_credentials(self):
        """Test that None is returned when WebPush is requested but credentials are missing."""
        os.environ["HANDSFREE_NOTIFICATION_PROVIDER"] = "webpush"
        # Don't set VAPID keys

        provider = get_notification_provider()
        assert provider is None

        # Clean up
        os.environ.pop("HANDSFREE_NOTIFICATION_PROVIDER", None)


class TestWebPushProvider:
    """Test the WebPushProvider."""

    def test_send_notification_success(self, monkeypatch):
        """Test successful WebPush notification send."""

        # Mock pywebpush.webpush
        class MockResponse:
            status_code = 201

        def mock_webpush(subscription_info, data, vapid_private_key, vapid_claims):
            # Verify parameters
            assert subscription_info["endpoint"] == "https://push.example.com/test"
            assert "p256dh" in subscription_info["keys"]
            assert "auth" in subscription_info["keys"]
            assert vapid_private_key == "test-private-key"
            assert vapid_claims["sub"] == "mailto:test@example.com"
            return MockResponse()

        # Patch webpush
        import pywebpush

        monkeypatch.setattr(pywebpush, "webpush", mock_webpush)

        # Create provider
        provider = WebPushProvider(
            vapid_public_key="test-public-key",
            vapid_private_key="test-private-key",
            vapid_subject="mailto:test@example.com",
        )

        # Send notification
        result = provider.send(
            subscription_endpoint="https://push.example.com/test",
            notification_data={
                "id": "notif-123",
                "event_type": "test_event",
                "message": "Test notification",
            },
            subscription_keys={"p256dh": "test-p256dh", "auth": "test-auth"},
        )

        assert result["ok"] is True
        assert "Notification sent" in result["message"]
        assert result["delivery_id"] is not None
        assert result["delivery_id"].startswith("webpush-")

    def test_send_notification_missing_subscription_keys(self):
        """Test WebPush send fails when subscription keys are missing."""
        provider = WebPushProvider(
            vapid_public_key="test-public-key",
            vapid_private_key="test-private-key",
            vapid_subject="mailto:test@example.com",
        )

        # Send without subscription keys
        result = provider.send(
            subscription_endpoint="https://push.example.com/test",
            notification_data={"message": "Test"},
            subscription_keys=None,
        )

        assert result["ok"] is False
        assert "Missing subscription keys" in result["message"]
        assert result["delivery_id"] is None

    def test_send_notification_missing_required_keys(self):
        """Test WebPush send fails when required keys (p256dh, auth) are missing."""
        provider = WebPushProvider(
            vapid_public_key="test-public-key",
            vapid_private_key="test-private-key",
            vapid_subject="mailto:test@example.com",
        )

        # Send with incomplete keys (missing auth)
        result = provider.send(
            subscription_endpoint="https://push.example.com/test",
            notification_data={"message": "Test"},
            subscription_keys={"p256dh": "test-p256dh"},
        )

        assert result["ok"] is False
        assert "p256dh and auth are required" in result["message"]
        assert result["delivery_id"] is None

        # Send with incomplete keys (missing p256dh)
        result = provider.send(
            subscription_endpoint="https://push.example.com/test",
            notification_data={"message": "Test"},
            subscription_keys={"auth": "test-auth"},
        )

        assert result["ok"] is False
        assert "p256dh and auth are required" in result["message"]

    def test_send_notification_webpush_exception(self, monkeypatch):
        """Test WebPush send handles WebPushException gracefully."""
        from pywebpush import WebPushException

        def mock_webpush(subscription_info, data, vapid_private_key, vapid_claims):
            raise WebPushException("Expired subscription")

        # Patch webpush
        import pywebpush

        monkeypatch.setattr(pywebpush, "webpush", mock_webpush)

        provider = WebPushProvider(
            vapid_public_key="test-public-key",
            vapid_private_key="test-private-key",
            vapid_subject="mailto:test@example.com",
        )

        result = provider.send(
            subscription_endpoint="https://push.example.com/test",
            notification_data={"message": "Test"},
            subscription_keys={"p256dh": "test-p256dh", "auth": "test-auth"},
        )

        assert result["ok"] is False
        assert "WebPush error" in result["message"]
        assert "Expired subscription" in result["message"]
        assert result["delivery_id"] is None

    def test_send_notification_unexpected_exception(self, monkeypatch):
        """Test WebPush send handles unexpected exceptions gracefully."""

        def mock_webpush(subscription_info, data, vapid_private_key, vapid_claims):
            raise ValueError("Unexpected error")

        # Patch webpush
        import pywebpush

        monkeypatch.setattr(pywebpush, "webpush", mock_webpush)

        provider = WebPushProvider(
            vapid_public_key="test-public-key",
            vapid_private_key="test-private-key",
            vapid_subject="mailto:test@example.com",
        )

        result = provider.send(
            subscription_endpoint="https://push.example.com/test",
            notification_data={"message": "Test"},
            subscription_keys={"p256dh": "test-p256dh", "auth": "test-auth"},
        )

        assert result["ok"] is False
        assert "Unexpected error" in result["message"]
        assert result["delivery_id"] is None

    def test_send_notification_pywebpush_not_installed(self, monkeypatch):
        """Test WebPush gracefully handles missing pywebpush library."""
        # Create a provider and mark pywebpush as unavailable
        provider = WebPushProvider(
            vapid_public_key="test-public-key",
            vapid_private_key="test-private-key",
            vapid_subject="mailto:test@example.com",
        )
        provider._pywebpush_available = False

        result = provider.send(
            subscription_endpoint="https://push.example.com/test",
            notification_data={"message": "Test"},
            subscription_keys={"p256dh": "test-p256dh", "auth": "test-auth"},
        )

        assert result["ok"] is False
        assert "pywebpush library not installed" in result["message"]
        assert result["delivery_id"] is None


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
        assert delivery_calls[0]["data"]["notification_id"] == delivery_calls[0]["data"]["id"]
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
            headers={"X-User-Id": test_user_id},
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
            headers={"X-User-Id": test_user_id},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["count"] >= 1


class TestAutoPushEnabled:
    """Test NOTIFICATIONS_AUTO_PUSH_ENABLED environment variable."""

    @staticmethod
    def _setup_delivery_tracking(monkeypatch):
        """Helper to set up delivery call tracking with mock_send.

        Returns:
            List that will be populated with delivery calls.
        """
        delivery_calls = []
        original_send = DevLoggerProvider.send

        def mock_send(self, subscription_endpoint, notification_data, subscription_keys=None):
            delivery_calls.append(
                {
                    "endpoint": subscription_endpoint,
                    "data": notification_data,
                }
            )
            return original_send(self, subscription_endpoint, notification_data, subscription_keys)

        monkeypatch.setattr(DevLoggerProvider, "send", mock_send)
        return delivery_calls

    def test_auto_push_disabled_via_env_var(self, db_conn, test_user_id, monkeypatch):
        """Test that notifications are not delivered when NOTIFICATIONS_AUTO_PUSH_ENABLED=false."""
        # Enable provider but disable auto-push
        monkeypatch.setenv("HANDSFREE_NOTIFICATION_PROVIDER", "logger")
        monkeypatch.setenv("NOTIFICATIONS_AUTO_PUSH_ENABLED", "false")

        # Create a subscription
        create_subscription(
            conn=db_conn,
            user_id=test_user_id,
            endpoint="https://push.example.com/test-endpoint",
        )

        # Track delivery calls
        delivery_calls = self._setup_delivery_tracking(monkeypatch)

        # Create a notification
        create_notification(
            conn=db_conn,
            user_id=test_user_id,
            event_type="test_event",
            message="Test notification message",
        )

        # Verify delivery was NOT called
        assert len(delivery_calls) == 0

    def test_auto_push_enabled_by_default(self, db_conn, test_user_id, monkeypatch):
        """Test that auto-push is enabled by default (when env var is not set)."""
        # Enable provider, don't set NOTIFICATIONS_AUTO_PUSH_ENABLED
        monkeypatch.setenv("HANDSFREE_NOTIFICATION_PROVIDER", "logger")
        monkeypatch.delenv("NOTIFICATIONS_AUTO_PUSH_ENABLED", raising=False)

        # Create a subscription
        create_subscription(
            conn=db_conn,
            user_id=test_user_id,
            endpoint="https://push.example.com/test-endpoint",
        )

        # Track delivery calls
        delivery_calls = self._setup_delivery_tracking(monkeypatch)

        # Create a notification
        create_notification(
            conn=db_conn,
            user_id=test_user_id,
            event_type="test_event",
            message="Test notification message",
        )

        # Verify delivery WAS called (auto-push enabled by default)
        assert len(delivery_calls) == 1

    def test_auto_push_enabled_explicitly(self, db_conn, test_user_id, monkeypatch):
        """Test that auto-push works when NOTIFICATIONS_AUTO_PUSH_ENABLED=true."""
        # Enable provider and auto-push explicitly
        monkeypatch.setenv("HANDSFREE_NOTIFICATION_PROVIDER", "logger")
        monkeypatch.setenv("NOTIFICATIONS_AUTO_PUSH_ENABLED", "true")

        # Create a subscription
        create_subscription(
            conn=db_conn,
            user_id=test_user_id,
            endpoint="https://push.example.com/test-endpoint",
        )

        # Track delivery calls
        delivery_calls = self._setup_delivery_tracking(monkeypatch)

        # Create a notification
        create_notification(
            conn=db_conn,
            user_id=test_user_id,
            event_type="test_event",
            message="Test notification message",
        )

        # Verify delivery WAS called
        assert len(delivery_calls) == 1


class TestExpoPushProvider:
    """Test the ExpoPushProvider."""

    def test_send_notification_stub_mode(self):
        """Test sending a notification via ExpoPushProvider in stub mode."""
        from handsfree.notifications import ExpoPushProvider

        provider = ExpoPushProvider(mode="stub")

        result = provider.send(
            subscription_endpoint="ExponentPushToken[xxxxxxxxxxxxxxxxxxxxxx]",
            notification_data={
                "id": "notif-123",
                "event_type": "test_event",
                "message": "Test notification",
            },
        )

        assert result["ok"] is True
        assert "message" in result
        assert "delivery_id" in result
        assert result["message"] == "Expo notification logged (stub mode)"
        assert result["delivery_id"].startswith("expo-stub-")

    def test_send_notification_real_mode_success(self, monkeypatch):
        """Test successful Expo notification send in real mode."""
        from handsfree.notifications import ExpoPushProvider

        # Mock httpx response
        class MockResponse:
            status_code = 200

            def json(self):
                return {
                    "data": {
                        "status": "ok",
                        "id": "test-ticket-id-123",
                    }
                }

        class MockClient:
            def __init__(self, timeout):
                pass

            def __enter__(self):
                return self

            def __exit__(self, *args):
                pass

            def post(self, url, json, headers):
                # Verify parameters
                assert url == "https://exp.host/--/api/v2/push/send"
                assert json["to"] == "ExponentPushToken[xxxxxxxxxxxxxxxxxxxxxx]"
                assert json["title"] == "Test Event"
                assert json["body"] == "Test notification"
                assert "Authorization" not in headers  # No access token
                return MockResponse()

        # Patch httpx.Client
        import httpx

        monkeypatch.setattr(httpx, "Client", MockClient)

        # Create provider in real mode
        provider = ExpoPushProvider(mode="real")

        # Send notification
        result = provider.send(
            subscription_endpoint="ExponentPushToken[xxxxxxxxxxxxxxxxxxxxxx]",
            notification_data={
                "id": "notif-123",
                "event_type": "test_event",
                "title": "Test Event",
                "message": "Test notification",
            },
        )

        assert result["ok"] is True
        assert "Expo notification sent" in result["message"]
        assert result["delivery_id"] == "test-ticket-id-123"

    def test_send_notification_with_access_token(self, monkeypatch):
        """Test Expo notification send with access token."""
        from handsfree.notifications import ExpoPushProvider

        # Mock httpx response
        class MockResponse:
            status_code = 200

            def json(self):
                return {
                    "data": {
                        "status": "ok",
                        "id": "test-ticket-id-456",
                    }
                }

        class MockClient:
            def __init__(self, timeout):
                pass

            def __enter__(self):
                return self

            def __exit__(self, *args):
                pass

            def post(self, url, json, headers):
                # Verify access token is included
                assert headers["Authorization"] == "Bearer test-access-token"
                return MockResponse()

        # Patch httpx.Client
        import httpx

        monkeypatch.setattr(httpx, "Client", MockClient)

        # Create provider with access token
        provider = ExpoPushProvider(access_token="test-access-token", mode="real")

        # Send notification
        result = provider.send(
            subscription_endpoint="ExponentPushToken[xxxxxxxxxxxxxxxxxxxxxx]",
            notification_data={
                "id": "notif-123",
                "event_type": "test_event",
                "message": "Test notification",
            },
        )

        assert result["ok"] is True
        assert result["delivery_id"] == "test-ticket-id-456"

    def test_send_notification_expo_error_in_ticket(self, monkeypatch):
        """Test Expo notification send with error in push ticket."""
        from handsfree.notifications import ExpoPushProvider

        # Mock httpx response with error in ticket
        class MockResponse:
            status_code = 200

            def json(self):
                return {
                    "data": {
                        "status": "error",
                        "message": "DeviceNotRegistered",
                        "details": {"error": "DeviceNotRegistered"},
                    }
                }

        class MockClient:
            def __init__(self, timeout):
                pass

            def __enter__(self):
                return self

            def __exit__(self, *args):
                pass

            def post(self, url, json, headers):
                return MockResponse()

        # Patch httpx.Client
        import httpx

        monkeypatch.setattr(httpx, "Client", MockClient)

        # Create provider
        provider = ExpoPushProvider(mode="real")

        # Send notification
        result = provider.send(
            subscription_endpoint="ExponentPushToken[xxxxxxxxxxxxxxxxxxxxxx]",
            notification_data={
                "message": "Test",
            },
        )

        assert result["ok"] is False
        assert "DeviceNotRegistered" in result["message"]
        assert result["delivery_id"] is None

    def test_send_notification_http_error(self, monkeypatch):
        """Test Expo notification send with HTTP error."""
        from handsfree.notifications import ExpoPushProvider

        # Mock httpx response with HTTP error
        class MockResponse:
            status_code = 500
            text = "Internal server error"

        class MockClient:
            def __init__(self, timeout):
                pass

            def __enter__(self):
                return self

            def __exit__(self, *args):
                pass

            def post(self, url, json, headers):
                return MockResponse()

        # Patch httpx.Client
        import httpx

        monkeypatch.setattr(httpx, "Client", MockClient)

        # Create provider
        provider = ExpoPushProvider(mode="real")

        # Send notification
        result = provider.send(
            subscription_endpoint="ExponentPushToken[xxxxxxxxxxxxxxxxxxxxxx]",
            notification_data={
                "message": "Test",
            },
        )

        assert result["ok"] is False
        assert "500" in result["message"]
        assert result["delivery_id"] is None

    def test_send_notification_unexpected_exception(self, monkeypatch):
        """Test Expo notification send handles unexpected exceptions."""
        from handsfree.notifications import ExpoPushProvider

        class MockClient:
            def __init__(self, timeout):
                pass

            def __enter__(self):
                return self

            def __exit__(self, *args):
                pass

            def post(self, url, json, headers):
                raise ValueError("Unexpected error")

        # Patch httpx.Client
        import httpx

        monkeypatch.setattr(httpx, "Client", MockClient)

        # Create provider
        provider = ExpoPushProvider(mode="real")

        # Send notification
        result = provider.send(
            subscription_endpoint="ExponentPushToken[xxxxxxxxxxxxxxxxxxxxxx]",
            notification_data={
                "message": "Test",
            },
        )

        assert result["ok"] is False
        assert "Unexpected error" in result["message"]
        assert result["delivery_id"] is None

    def test_default_notification_fields(self, monkeypatch):
        """Test that notification fields have sensible defaults."""
        from handsfree.notifications import ExpoPushProvider

        # Mock httpx response
        class MockResponse:
            status_code = 200

            def json(self):
                return {
                    "data": {
                        "status": "ok",
                        "id": "test-id",
                    }
                }

        class MockClient:
            def __init__(self, timeout):
                pass

            def __enter__(self):
                return self

            def __exit__(self, *args):
                pass

            def post(self, url, json, headers):
                # Verify default fields
                assert json["title"] == "webhook.test_event"  # Falls back to event_type
                assert json["body"] == ""  # Empty message
                # Default to silent so the app can speak via TTS.
                assert json["sound"] is None
                assert json["priority"] == "high"
                return MockResponse()

        # Patch httpx.Client
        import httpx

        monkeypatch.setattr(httpx, "Client", MockClient)

        # Create provider
        provider = ExpoPushProvider(mode="real")

        # Send notification with minimal data
        result = provider.send(
            subscription_endpoint="ExponentPushToken[xxxxxxxxxxxxxxxxxxxxxx]",
            notification_data={
                "event_type": "webhook.test_event",
            },
        )

        assert result["ok"] is True


class TestGetProviderForPlatformExpo:
    """Test get_provider_for_platform with Expo platform."""

    def test_returns_expo_provider_for_expo_platform(self, monkeypatch):
        """Test that ExpoPushProvider is returned for 'expo' platform."""
        from handsfree.notifications import ExpoPushProvider, get_provider_for_platform

        # Clear logger override
        monkeypatch.delenv("HANDSFREE_NOTIFICATION_PROVIDER", raising=False)
        
        # Don't set access token (it's optional)
        monkeypatch.delenv("HANDSFREE_EXPO_ACCESS_TOKEN", raising=False)

        provider = get_provider_for_platform("expo")
        assert isinstance(provider, ExpoPushProvider)
        assert provider.mode == "stub"  # Default mode

    def test_returns_expo_provider_with_access_token(self, monkeypatch):
        """Test that ExpoPushProvider is configured with access token."""
        from handsfree.notifications import ExpoPushProvider, get_provider_for_platform

        # Clear logger override
        monkeypatch.delenv("HANDSFREE_NOTIFICATION_PROVIDER", raising=False)
        
        # Set access token
        monkeypatch.setenv("HANDSFREE_EXPO_ACCESS_TOKEN", "test-token-123")

        provider = get_provider_for_platform("expo")
        assert isinstance(provider, ExpoPushProvider)
        assert provider.access_token == "test-token-123"

    def test_returns_expo_provider_in_real_mode(self, monkeypatch):
        """Test that ExpoPushProvider can be configured in real mode."""
        from handsfree.notifications import ExpoPushProvider, get_provider_for_platform

        # Clear logger override
        monkeypatch.delenv("HANDSFREE_NOTIFICATION_PROVIDER", raising=False)
        
        # Set real mode
        monkeypatch.setenv("HANDSFREE_EXPO_MODE", "real")

        provider = get_provider_for_platform("expo")
        assert isinstance(provider, ExpoPushProvider)
        assert provider.mode == "real"

    def test_logger_override_applies_to_expo(self, monkeypatch):
        """Test that dev logger override applies to Expo platform."""
        from handsfree.notifications import DevLoggerProvider, get_provider_for_platform

        # Set logger override
        monkeypatch.setenv("HANDSFREE_NOTIFICATION_PROVIDER", "logger")

        provider = get_provider_for_platform("expo")
        assert isinstance(provider, DevLoggerProvider)


class TestExpoIntegration:
    """Test Expo push integration end-to-end."""

    def test_expo_subscription_delivers_notification(self, db_conn, test_user_id, monkeypatch):
        """Test that notifications are delivered to Expo subscriptions."""
        from handsfree.db.notification_subscriptions import create_subscription
        from handsfree.db.notifications import create_notification
        from handsfree.notifications import ExpoPushProvider

        # Enable Expo provider in stub mode
        monkeypatch.delenv("HANDSFREE_NOTIFICATION_PROVIDER", raising=False)
        monkeypatch.setenv("HANDSFREE_EXPO_MODE", "stub")

        # Create an Expo subscription
        create_subscription(
            conn=db_conn,
            user_id=test_user_id,
            endpoint="ExponentPushToken[xxxxxxxxxxxxxxxxxxxxxx]",
            platform="expo",
        )

        # Track delivery calls
        delivery_calls = []

        def mock_send(self, subscription_endpoint, notification_data, subscription_keys=None):
            delivery_calls.append(
                {
                    "endpoint": subscription_endpoint,
                    "data": notification_data,
                }
            )
            return {
                "ok": True,
                "message": "Test delivery",
                "delivery_id": "test-id",
            }

        monkeypatch.setattr(ExpoPushProvider, "send", mock_send)

        # Create a notification
        create_notification(
            conn=db_conn,
            user_id=test_user_id,
            event_type="webhook.pr_opened",
            message="PR #123 opened",
        )

        # Verify delivery was called with correct endpoint
        assert len(delivery_calls) == 1
        assert delivery_calls[0]["endpoint"] == "ExponentPushToken[xxxxxxxxxxxxxxxxxxxxxx]"
        assert "webhook.pr_opened" in delivery_calls[0]["data"]["event_type"]

    def test_multiple_platform_subscriptions(self, db_conn, test_user_id, monkeypatch):
        """Test that user can have both Expo and other platform subscriptions."""
        from handsfree.db.notification_subscriptions import create_subscription, list_subscriptions

        # Create subscriptions for different platforms
        expo_sub = create_subscription(
            conn=db_conn,
            user_id=test_user_id,
            endpoint="ExponentPushToken[xxxxxxxxxxxxxxxxxxxxxx]",
            platform="expo",
        )

        webpush_sub = create_subscription(
            conn=db_conn,
            user_id=test_user_id,
            endpoint="https://fcm.googleapis.com/fcm/send/...",
            platform="webpush",
            subscription_keys={"auth": "test", "p256dh": "test"},
        )

        # List subscriptions
        subscriptions = list_subscriptions(conn=db_conn, user_id=test_user_id)

        assert len(subscriptions) == 2
        platforms = {sub.platform for sub in subscriptions}
        assert "expo" in platforms
        assert "webpush" in platforms
