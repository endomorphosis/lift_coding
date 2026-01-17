"""Tests for APNS and FCM platform support in notification subscriptions."""

import os

import pytest
from fastapi.testclient import TestClient

from handsfree.api import app
from handsfree.db import init_db
from handsfree.db.notification_subscriptions import create_subscription
from handsfree.notifications.provider import (
    APNSProvider,
    FCMProvider,
    get_provider_for_platform,
)

client = TestClient(app)


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


class TestAPNSProvider:
    """Test APNS provider stub."""

    def test_apns_provider_initialization(self):
        """Test APNS provider can be initialized with credentials."""
        provider = APNSProvider(
            team_id="TEST123456",
            key_id="ABC123DEF456",
            key_path="/path/to/key.p8",
            bundle_id="com.example.app",
            use_sandbox=True,
        )

        assert provider.team_id == "TEST123456"
        assert provider.key_id == "ABC123DEF456"
        assert provider.key_path == "/path/to/key.p8"
        assert provider.bundle_id == "com.example.app"
        assert provider.use_sandbox is True

    def test_apns_provider_send_stub(self):
        """Test APNS provider send (stub implementation)."""
        provider = APNSProvider(
            team_id="TEST123456",
            key_id="ABC123DEF456",
            key_path="/path/to/key.p8",
            bundle_id="com.example.app",
            use_sandbox=True,
        )

        result = provider.send(
            subscription_endpoint="device-token-abc123def456",
            notification_data={
                "id": "notif-123",
                "event_type": "test_event",
                "message": "Test iOS notification",
            },
        )

        assert result["ok"] is True
        assert "stub mode" in result["message"]
        assert result["delivery_id"] is not None
        assert result["delivery_id"].startswith("apns-stub-")

    def test_apns_provider_send_with_subscription_keys(self):
        """Test APNS provider send with subscription keys (ignored in stub)."""
        provider = APNSProvider(
            team_id="TEST123456",
            key_id="ABC123DEF456",
            key_path="/path/to/key.p8",
            bundle_id="com.example.app",
        )

        result = provider.send(
            subscription_endpoint="device-token-xyz789",
            notification_data={"message": "Test"},
            subscription_keys={"some": "key"},
        )

        assert result["ok"] is True


class TestFCMProvider:
    """Test FCM provider stub."""

    def test_fcm_provider_initialization(self):
        """Test FCM provider can be initialized with credentials."""
        provider = FCMProvider(
            project_id="my-firebase-project",
            credentials_path="/path/to/credentials.json",
        )

        assert provider.project_id == "my-firebase-project"
        assert provider.credentials_path == "/path/to/credentials.json"

    def test_fcm_provider_send_stub(self):
        """Test FCM provider send (stub implementation)."""
        provider = FCMProvider(
            project_id="my-firebase-project",
            credentials_path="/path/to/credentials.json",
        )

        result = provider.send(
            subscription_endpoint="fcm-token-abc123def456",
            notification_data={
                "id": "notif-456",
                "event_type": "test_event",
                "message": "Test Android notification",
            },
        )

        assert result["ok"] is True
        assert "stub mode" in result["message"]
        assert result["delivery_id"] is not None
        assert result["delivery_id"].startswith("fcm-stub-")

    def test_fcm_provider_send_with_subscription_keys(self):
        """Test FCM provider send with subscription keys (ignored in stub)."""
        provider = FCMProvider(
            project_id="my-firebase-project",
            credentials_path="/path/to/credentials.json",
        )

        result = provider.send(
            subscription_endpoint="fcm-token-xyz789",
            notification_data={"message": "Test"},
            subscription_keys={"some": "key"},
        )

        assert result["ok"] is True


class TestPlatformSubscriptions:
    """Test platform-specific subscription creation."""

    def test_create_apns_subscription_via_api(self):
        """Test creating an APNS subscription via API."""
        response = client.post(
            "/v1/notifications/subscriptions",
            json={
                "endpoint": "ios-device-token-abc123",
                "platform": "apns",
                "subscription_keys": {},
            },
            headers={"X-User-Id": "00000000-0000-0000-0000-000000000001"},
        )

        assert response.status_code == 201
        data = response.json()
        assert data["platform"] == "apns"
        assert data["endpoint"] == "ios-device-token-abc123"

    def test_create_fcm_subscription_via_api(self):
        """Test creating an FCM subscription via API."""
        response = client.post(
            "/v1/notifications/subscriptions",
            json={
                "endpoint": "android-fcm-token-xyz789",
                "platform": "fcm",
                "subscription_keys": {},
            },
            headers={"X-User-Id": "00000000-0000-0000-0000-000000000002"},
        )

        assert response.status_code == 201
        data = response.json()
        assert data["platform"] == "fcm"
        assert data["endpoint"] == "android-fcm-token-xyz789"

    def test_create_webpush_subscription_defaults(self):
        """Test creating a WebPush subscription with default platform."""
        response = client.post(
            "/v1/notifications/subscriptions",
            json={
                "endpoint": "https://push.example.com/webpush",
                # platform not specified, should default to 'webpush'
                "subscription_keys": {"auth": "secret", "p256dh": "key"},
            },
            headers={"X-User-Id": "00000000-0000-0000-0000-000000000003"},
        )

        assert response.status_code == 201
        data = response.json()
        assert data["platform"] == "webpush"

    def test_create_subscription_with_explicit_webpush_platform(self):
        """Test creating a subscription with explicit webpush platform."""
        response = client.post(
            "/v1/notifications/subscriptions",
            json={
                "endpoint": "https://push.example.com/explicit",
                "platform": "webpush",
                "subscription_keys": {"auth": "secret", "p256dh": "key"},
            },
            headers={"X-User-Id": "00000000-0000-0000-0000-000000000004"},
        )

        assert response.status_code == 201
        data = response.json()
        assert data["platform"] == "webpush"

    def test_create_subscription_invalid_platform(self):
        """Test creating a subscription with an invalid platform."""
        response = client.post(
            "/v1/notifications/subscriptions",
            json={
                "endpoint": "some-endpoint",
                "platform": "invalid-platform",
            },
            headers={"X-User-Id": "00000000-0000-0000-0000-000000000005"},
        )

        # Should fail validation
        assert response.status_code == 422

    def test_list_subscriptions_includes_platform(self):
        """Test that listing subscriptions includes platform information."""
        user_id = "00000000-0000-0000-0000-000000000006"

        # Create subscriptions for different platforms
        client.post(
            "/v1/notifications/subscriptions",
            json={"endpoint": "ios-token", "platform": "apns"},
            headers={"X-User-Id": user_id},
        )
        client.post(
            "/v1/notifications/subscriptions",
            json={"endpoint": "android-token", "platform": "fcm"},
            headers={"X-User-Id": user_id},
        )
        client.post(
            "/v1/notifications/subscriptions",
            json={"endpoint": "https://push.example.com/web", "platform": "webpush"},
            headers={"X-User-Id": user_id},
        )

        # List subscriptions
        response = client.get(
            "/v1/notifications/subscriptions",
            headers={"X-User-Id": user_id},
        )

        assert response.status_code == 200
        data = response.json()
        assert len(data["subscriptions"]) == 3

        platforms = {sub["platform"] for sub in data["subscriptions"]}
        assert "apns" in platforms
        assert "fcm" in platforms
        assert "webpush" in platforms


class TestPlatformProviderSelection:
    """Test platform-specific provider selection."""

    def test_get_provider_for_apns_platform(self, monkeypatch):
        """Test getting APNS provider for apns platform."""
        # Configure APNS credentials
        monkeypatch.setenv("HANDSFREE_APNS_TEAM_ID", "TEST123456")
        monkeypatch.setenv("HANDSFREE_APNS_KEY_ID", "ABC123")
        monkeypatch.setenv("HANDSFREE_APNS_KEY_PATH", "/path/to/key.p8")
        monkeypatch.setenv("HANDSFREE_APNS_BUNDLE_ID", "com.example.app")

        provider = get_provider_for_platform("apns")

        assert isinstance(provider, APNSProvider)
        assert provider.team_id == "TEST123456"
        assert provider.key_id == "ABC123"

    def test_get_provider_for_fcm_platform(self, monkeypatch):
        """Test getting FCM provider for fcm platform."""
        # Configure FCM credentials
        monkeypatch.setenv("HANDSFREE_FCM_PROJECT_ID", "my-project")
        monkeypatch.setenv("HANDSFREE_FCM_CREDENTIALS_PATH", "/path/to/creds.json")

        provider = get_provider_for_platform("fcm")

        assert isinstance(provider, FCMProvider)
        assert provider.project_id == "my-project"
        assert provider.credentials_path == "/path/to/creds.json"

    def test_get_provider_for_webpush_platform(self, monkeypatch):
        """Test getting WebPush provider for webpush platform."""
        from handsfree.notifications.provider import WebPushProvider

        # Configure WebPush credentials
        monkeypatch.setenv("HANDSFREE_WEBPUSH_VAPID_PUBLIC_KEY", "test-public")
        monkeypatch.setenv("HANDSFREE_WEBPUSH_VAPID_PRIVATE_KEY", "test-private")
        monkeypatch.setenv("HANDSFREE_WEBPUSH_VAPID_SUBJECT", "mailto:test@example.com")

        provider = get_provider_for_platform("webpush")

        assert isinstance(provider, WebPushProvider)
        assert provider.vapid_public_key == "test-public"

    def test_get_provider_returns_none_when_credentials_missing(self, monkeypatch):
        """Test that None is returned when credentials are not configured."""
        # Clear any environment variables that might be set
        monkeypatch.delenv("HANDSFREE_APNS_TEAM_ID", raising=False)
        monkeypatch.delenv("HANDSFREE_APNS_KEY_ID", raising=False)
        monkeypatch.delenv("HANDSFREE_APNS_KEY_PATH", raising=False)
        monkeypatch.delenv("HANDSFREE_APNS_BUNDLE_ID", raising=False)
        monkeypatch.delenv("HANDSFREE_FCM_PROJECT_ID", raising=False)
        monkeypatch.delenv("HANDSFREE_FCM_CREDENTIALS_PATH", raising=False)

        apns_provider = get_provider_for_platform("apns")
        assert apns_provider is None

        fcm_provider = get_provider_for_platform("fcm")
        assert fcm_provider is None

    def test_get_provider_returns_none_for_unknown_platform(self):
        """Test that None is returned for unknown platform."""
        provider = get_provider_for_platform("unknown-platform")
        assert provider is None

    def test_dev_logger_overrides_all_platforms(self, monkeypatch):
        """Test that dev logger provider is returned for all platforms when configured."""
        from handsfree.notifications.provider import DevLoggerProvider

        # Set dev logger as default provider
        monkeypatch.setenv("HANDSFREE_NOTIFICATION_PROVIDER", "logger")

        # Should return DevLoggerProvider for all platforms
        apns_provider = get_provider_for_platform("apns")
        assert isinstance(apns_provider, DevLoggerProvider)

        fcm_provider = get_provider_for_platform("fcm")
        assert isinstance(fcm_provider, DevLoggerProvider)

        webpush_provider = get_provider_for_platform("webpush")
        assert isinstance(webpush_provider, DevLoggerProvider)


class TestPlatformPersistence:
    """Test platform field persistence in database."""

    def test_create_subscription_with_platform_db(self, db_conn, test_user_id):
        """Test creating subscriptions with different platforms in DB."""
        # Create APNS subscription
        apns_sub = create_subscription(
            conn=db_conn,
            user_id=test_user_id,
            endpoint="ios-device-token",
            platform="apns",
        )
        assert apns_sub.platform == "apns"

        # Create FCM subscription
        fcm_sub = create_subscription(
            conn=db_conn,
            user_id=test_user_id,
            endpoint="android-fcm-token",
            platform="fcm",
        )
        assert fcm_sub.platform == "fcm"

        # Create WebPush subscription
        webpush_sub = create_subscription(
            conn=db_conn,
            user_id=test_user_id,
            endpoint="https://push.example.com/web",
            platform="webpush",
        )
        assert webpush_sub.platform == "webpush"

    def test_platform_defaults_to_webpush(self, db_conn, test_user_id):
        """Test that platform defaults to webpush when not specified."""
        subscription = create_subscription(
            conn=db_conn,
            user_id=test_user_id,
            endpoint="https://push.example.com/default",
            # platform not specified
        )
        assert subscription.platform == "webpush"

    def test_list_subscriptions_by_platform(self, db_conn, test_user_id):
        """Test that we can filter/identify subscriptions by platform."""
        from handsfree.db.notification_subscriptions import list_subscriptions

        # Create multiple subscriptions with different platforms
        create_subscription(conn=db_conn, user_id=test_user_id, endpoint="ios-1", platform="apns")
        create_subscription(
            conn=db_conn, user_id=test_user_id, endpoint="android-1", platform="fcm"
        )
        create_subscription(
            conn=db_conn,
            user_id=test_user_id,
            endpoint="https://push.example.com/web-1",
            platform="webpush",
        )

        # List all subscriptions
        subscriptions = list_subscriptions(conn=db_conn, user_id=test_user_id)

        assert len(subscriptions) == 3

        # Group by platform
        by_platform = {}
        for sub in subscriptions:
            if sub.platform not in by_platform:
                by_platform[sub.platform] = []
            by_platform[sub.platform].append(sub)

        assert "apns" in by_platform
        assert "fcm" in by_platform
        assert "webpush" in by_platform
        assert len(by_platform["apns"]) == 1
        assert len(by_platform["fcm"]) == 1
        assert len(by_platform["webpush"]) == 1


class TestMigrationCompatibility:
    """Test that migration adds platform field correctly."""

    def test_platform_field_exists_in_schema(self, db_conn):
        """Test that platform field exists in the notification_subscriptions table."""
        # Query the table schema using PRAGMA table_info
        result = db_conn.execute("PRAGMA table_info(notification_subscriptions)").fetchall()

        # PRAGMA table_info returns: (cid, name, type, notnull, dflt_value, pk)
        column_names = [row[1] for row in result]
        assert "platform" in column_names

    def test_platform_index_exists(self, db_conn):
        """Test that platform index exists."""
        # Check if the index exists using DuckDB's duckdb_indexes system table
        result = db_conn.execute(
            "SELECT index_name FROM duckdb_indexes() "
            "WHERE table_name = 'notification_subscriptions' "
            "AND index_name = 'idx_notification_subscriptions_platform'"
        ).fetchall()

        # Should have the index
        assert len(result) == 1
