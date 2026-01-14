"""Tests for notification subscriptions persistence and API."""

import pytest
from fastapi.testclient import TestClient

from handsfree.api import app
from handsfree.db import init_db
from handsfree.db.notification_subscriptions import (
    create_subscription,
    delete_subscription,
    get_subscription,
    list_subscriptions,
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


class TestNotificationSubscriptionPersistence:
    """Test notification subscription database operations."""

    def test_create_subscription(self, db_conn, test_user_id):
        """Test creating a notification subscription."""
        subscription = create_subscription(
            conn=db_conn,
            user_id=test_user_id,
            endpoint="https://push.example.com/subscription-123",
            subscription_keys={"auth": "secret123", "p256dh": "key456"},
        )

        assert subscription.id is not None
        assert subscription.user_id == test_user_id
        assert subscription.endpoint == "https://push.example.com/subscription-123"
        assert subscription.subscription_keys == {"auth": "secret123", "p256dh": "key456"}
        assert subscription.created_at is not None
        assert subscription.updated_at is not None

    def test_create_subscription_without_keys(self, db_conn, test_user_id):
        """Test creating a subscription without keys."""
        subscription = create_subscription(
            conn=db_conn,
            user_id=test_user_id,
            endpoint="https://push.example.com/subscription-456",
        )

        assert subscription.id is not None
        assert subscription.subscription_keys is None

    def test_list_subscriptions(self, db_conn, test_user_id):
        """Test listing subscriptions for a user."""
        # Create multiple subscriptions
        sub1 = create_subscription(
            conn=db_conn,
            user_id=test_user_id,
            endpoint="https://push.example.com/sub1",
        )
        sub2 = create_subscription(
            conn=db_conn,
            user_id=test_user_id,
            endpoint="https://push.example.com/sub2",
        )

        # List subscriptions
        subscriptions = list_subscriptions(conn=db_conn, user_id=test_user_id)

        assert len(subscriptions) == 2
        # Should be ordered by created_at DESC (most recent first)
        assert subscriptions[0].id == sub2.id
        assert subscriptions[1].id == sub1.id

    def test_list_subscriptions_filters_by_user(self, db_conn, test_user_id):
        """Test that list_subscriptions filters by user_id."""
        user2_id = "00000000-0000-0000-0000-000000000002"

        # Create subscriptions for two users
        create_subscription(
            conn=db_conn,
            user_id=test_user_id,
            endpoint="https://push.example.com/user1",
        )
        create_subscription(
            conn=db_conn,
            user_id=user2_id,
            endpoint="https://push.example.com/user2",
        )

        # List for first user
        subscriptions1 = list_subscriptions(conn=db_conn, user_id=test_user_id)
        assert len(subscriptions1) == 1
        assert subscriptions1[0].endpoint == "https://push.example.com/user1"

        # List for second user
        subscriptions2 = list_subscriptions(conn=db_conn, user_id=user2_id)
        assert len(subscriptions2) == 1
        assert subscriptions2[0].endpoint == "https://push.example.com/user2"

    def test_get_subscription(self, db_conn, test_user_id):
        """Test getting a specific subscription by ID."""
        subscription = create_subscription(
            conn=db_conn,
            user_id=test_user_id,
            endpoint="https://push.example.com/sub1",
            subscription_keys={"auth": "secret"},
        )

        # Retrieve the subscription
        retrieved = get_subscription(conn=db_conn, subscription_id=subscription.id)

        assert retrieved is not None
        assert retrieved.id == subscription.id
        assert retrieved.endpoint == subscription.endpoint
        assert retrieved.subscription_keys == {"auth": "secret"}

    def test_get_subscription_not_found(self, db_conn):
        """Test getting a non-existent subscription."""
        result = get_subscription(conn=db_conn, subscription_id="non-existent-id")
        assert result is None

    def test_delete_subscription(self, db_conn, test_user_id):
        """Test deleting a subscription."""
        subscription = create_subscription(
            conn=db_conn,
            user_id=test_user_id,
            endpoint="https://push.example.com/sub1",
        )

        # Delete the subscription
        deleted = delete_subscription(conn=db_conn, subscription_id=subscription.id)
        assert deleted is True

        # Verify it's gone
        result = get_subscription(conn=db_conn, subscription_id=subscription.id)
        assert result is None

    def test_delete_subscription_not_found(self, db_conn):
        """Test deleting a non-existent subscription."""
        deleted = delete_subscription(conn=db_conn, subscription_id="non-existent-id")
        assert deleted is False

    def test_subscription_to_dict(self, db_conn, test_user_id):
        """Test converting subscription to dict."""
        subscription = create_subscription(
            conn=db_conn,
            user_id=test_user_id,
            endpoint="https://push.example.com/sub1",
            subscription_keys={"auth": "secret"},
        )

        sub_dict = subscription.to_dict()

        assert sub_dict["id"] == subscription.id
        assert sub_dict["user_id"] == test_user_id
        assert sub_dict["endpoint"] == "https://push.example.com/sub1"
        assert sub_dict["subscription_keys"] == {"auth": "secret"}
        assert "created_at" in sub_dict
        assert "updated_at" in sub_dict


class TestNotificationSubscriptionAPI:
    """Test notification subscription API endpoints."""

    def test_create_subscription_via_api(self):
        """Test creating a subscription via POST /v1/notifications/subscriptions."""
        response = client.post(
            "/v1/notifications/subscriptions",
            json={
                "endpoint": "https://push.example.com/test-sub",
                "subscription_keys": {"auth": "test-secret", "p256dh": "test-key"},
            },
            headers={"X-User-Id": "00000000-0000-0000-0000-000000000001"},
        )

        assert response.status_code == 201
        data = response.json()
        assert "id" in data
        assert data["user_id"] == "00000000-0000-0000-0000-000000000001"
        assert data["endpoint"] == "https://push.example.com/test-sub"
        assert data["subscription_keys"]["auth"] == "test-secret"

    def test_create_subscription_without_keys(self):
        """Test creating a subscription without subscription_keys."""
        response = client.post(
            "/v1/notifications/subscriptions",
            json={"endpoint": "https://push.example.com/minimal"},
            headers={"X-User-Id": "00000000-0000-0000-0000-000000000001"},
        )

        assert response.status_code == 201
        data = response.json()
        assert data["endpoint"] == "https://push.example.com/minimal"
        assert data["subscription_keys"] == {}

    def test_list_subscriptions_via_api(self):
        """Test listing subscriptions via GET /v1/notifications/subscriptions."""
        user_id = "00000000-0000-0000-0000-000000000001"

        # Create some subscriptions
        client.post(
            "/v1/notifications/subscriptions",
            json={"endpoint": "https://push.example.com/sub1"},
            headers={"X-User-Id": user_id},
        )
        client.post(
            "/v1/notifications/subscriptions",
            json={"endpoint": "https://push.example.com/sub2"},
            headers={"X-User-Id": user_id},
        )

        # List subscriptions
        response = client.get(
            "/v1/notifications/subscriptions",
            headers={"X-User-Id": user_id},
        )

        assert response.status_code == 200
        data = response.json()
        assert "subscriptions" in data
        assert len(data["subscriptions"]) >= 2

    def test_delete_subscription_via_api(self):
        """Test deleting a subscription via DELETE /v1/notifications/subscriptions/{id}."""
        user_id = "00000000-0000-0000-0000-000000000001"

        # Create a subscription
        create_response = client.post(
            "/v1/notifications/subscriptions",
            json={"endpoint": "https://push.example.com/to-delete"},
            headers={"X-User-Id": user_id},
        )
        subscription_id = create_response.json()["id"]

        # Delete it
        delete_response = client.delete(
            f"/v1/notifications/subscriptions/{subscription_id}",
            headers={"X-User-Id": user_id},
        )

        assert delete_response.status_code == 204

        # Verify it's gone
        from handsfree.api import get_db

        db = get_db()
        result = get_subscription(conn=db, subscription_id=subscription_id)
        assert result is None

    def test_delete_subscription_not_found(self):
        """Test deleting a non-existent subscription."""
        response = client.delete(
            "/v1/notifications/subscriptions/non-existent-id",
            headers={"X-User-Id": "00000000-0000-0000-0000-000000000001"},
        )

        assert response.status_code == 404
        data = response.json()
        assert data["error"] == "not_found"

    def test_delete_subscription_wrong_user(self):
        """Test that users can only delete their own subscriptions."""
        user1_id = "00000000-0000-0000-0000-000000000001"
        user2_id = "00000000-0000-0000-0000-000000000002"

        # User 1 creates a subscription
        create_response = client.post(
            "/v1/notifications/subscriptions",
            json={"endpoint": "https://push.example.com/user1-sub"},
            headers={"X-User-Id": user1_id},
        )
        subscription_id = create_response.json()["id"]

        # User 2 tries to delete it
        delete_response = client.delete(
            f"/v1/notifications/subscriptions/{subscription_id}",
            headers={"X-User-Id": user2_id},
        )

        assert delete_response.status_code == 404
