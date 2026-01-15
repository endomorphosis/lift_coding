"""Tests for repository subscriptions API endpoints."""

import json
import pathlib

import pytest
from fastapi.testclient import TestClient

from handsfree.api import app, get_db
from handsfree.db.notifications import list_notifications
from handsfree.db.repo_subscriptions import create_repo_subscription

client = TestClient(app)


@pytest.fixture(autouse=True)
def reset_api_state():
    """Reset API state before each test."""
    from handsfree import api

    # Reset global state in api.py
    api._db_conn = None
    api._webhook_store = None
    api._command_router = None

    # Get fresh DB connection and clear data
    conn = api.get_db()
    conn.execute("DELETE FROM repo_subscriptions")
    conn.execute("DELETE FROM notifications")


@pytest.fixture
def test_user_id():
    """Generate a consistent test user ID."""
    return "00000000-0000-0000-0000-000000000001"


@pytest.fixture
def test_user_id_2():
    """Generate a second test user ID."""
    return "00000000-0000-0000-0000-000000000002"


class TestRepoSubscriptionsAPI:
    """Test repository subscriptions API endpoints."""

    def test_create_repo_subscription(self, test_user_id):
        """Test creating a repository subscription."""
        response = client.post(
            "/v1/repos/subscriptions",
            json={
                "repo_full_name": "octocat/Hello-World",
                "installation_id": 12345,
            },
            headers={"X-User-ID": test_user_id},
        )

        assert response.status_code == 201
        data = response.json()

        assert "id" in data
        assert data["user_id"] == test_user_id
        assert data["repo_full_name"] == "octocat/Hello-World"
        assert data["installation_id"] == 12345
        assert "created_at" in data

    def test_create_repo_subscription_without_installation_id(self, test_user_id):
        """Test creating a subscription without installation_id."""
        response = client.post(
            "/v1/repos/subscriptions",
            json={"repo_full_name": "octocat/Spoon-Knife"},
            headers={"X-User-ID": test_user_id},
        )

        assert response.status_code == 201
        data = response.json()

        assert data["user_id"] == test_user_id
        assert data["repo_full_name"] == "octocat/Spoon-Knife"
        assert data["installation_id"] is None

    def test_list_repo_subscriptions_empty(self, test_user_id):
        """Test listing subscriptions when there are none."""
        response = client.get(
            "/v1/repos/subscriptions",
            headers={"X-User-ID": test_user_id},
        )

        assert response.status_code == 200
        data = response.json()

        assert "subscriptions" in data
        assert len(data["subscriptions"]) == 0

    def test_list_repo_subscriptions_with_data(self, test_user_id):
        """Test listing subscriptions with existing data."""
        # Create subscriptions directly in the database
        db = get_db()
        create_repo_subscription(
            conn=db,
            user_id=test_user_id,
            repo_full_name="owner/repo1",
            installation_id=111,
        )
        create_repo_subscription(
            conn=db,
            user_id=test_user_id,
            repo_full_name="owner/repo2",
            installation_id=222,
        )

        response = client.get(
            "/v1/repos/subscriptions",
            headers={"X-User-ID": test_user_id},
        )

        assert response.status_code == 200
        data = response.json()

        assert len(data["subscriptions"]) == 2
        # Should be ordered by created_at DESC (most recent first)
        assert data["subscriptions"][0]["repo_full_name"] == "owner/repo2"
        assert data["subscriptions"][1]["repo_full_name"] == "owner/repo1"

    def test_list_repo_subscriptions_filters_by_user(self, test_user_id, test_user_id_2):
        """Test that listing subscriptions filters by user_id."""
        db = get_db()

        # Create subscriptions for two users
        create_repo_subscription(
            conn=db,
            user_id=test_user_id,
            repo_full_name="owner/user1-repo",
        )
        create_repo_subscription(
            conn=db,
            user_id=test_user_id_2,
            repo_full_name="owner/user2-repo",
        )

        # List for first user
        response = client.get(
            "/v1/repos/subscriptions",
            headers={"X-User-ID": test_user_id},
        )

        assert response.status_code == 200
        data = response.json()

        assert len(data["subscriptions"]) == 1
        assert data["subscriptions"][0]["user_id"] == test_user_id
        assert data["subscriptions"][0]["repo_full_name"] == "owner/user1-repo"

    def test_delete_repo_subscription(self, test_user_id):
        """Test deleting a repository subscription."""
        # Create subscription
        db = get_db()
        create_repo_subscription(
            conn=db,
            user_id=test_user_id,
            repo_full_name="owner/repo-to-delete",
        )

        # Delete subscription
        response = client.delete(
            "/v1/repos/subscriptions/owner/repo-to-delete",
            headers={"X-User-ID": test_user_id},
        )

        assert response.status_code == 204

        # Verify it's deleted
        response = client.get(
            "/v1/repos/subscriptions",
            headers={"X-User-ID": test_user_id},
        )

        assert response.status_code == 200
        data = response.json()
        assert len(data["subscriptions"]) == 0

    def test_delete_nonexistent_subscription(self, test_user_id):
        """Test deleting a subscription that doesn't exist."""
        response = client.delete(
            "/v1/repos/subscriptions/owner/nonexistent",
            headers={"X-User-ID": test_user_id},
        )

        assert response.status_code == 404
        data = response.json()
        assert data["error"] == "not_found"

    def test_delete_subscription_wrong_user(self, test_user_id, test_user_id_2):
        """Test that users can't delete other users' subscriptions."""
        # Create subscription for user 1
        db = get_db()
        create_repo_subscription(
            conn=db,
            user_id=test_user_id,
            repo_full_name="owner/repo1",
        )

        # Try to delete as user 2
        response = client.delete(
            "/v1/repos/subscriptions/owner/repo1",
            headers={"X-User-ID": test_user_id_2},
        )

        assert response.status_code == 404

        # Verify subscription still exists for user 1
        response = client.get(
            "/v1/repos/subscriptions",
            headers={"X-User-ID": test_user_id},
        )

        assert response.status_code == 200
        data = response.json()
        assert len(data["subscriptions"]) == 1


class TestRepoSubscriptionsWebhookIntegration:
    """Test integration of repo subscriptions with webhook notifications."""

    def test_webhook_notification_routing(self, test_user_id):
        """Test that webhook notifications are routed to subscribed users."""
        # Create a repo subscription (must match the repository in the fixture)
        db = get_db()
        create_repo_subscription(
            conn=db,
            user_id=test_user_id,
            repo_full_name="testorg/testrepo",  # Matches pull_request.opened.json
        )

        # Load webhook fixture
        fixture_path = (
            pathlib.Path(__file__).parent
            / "fixtures"
            / "github"
            / "webhooks"
            / "pull_request.opened.json"
        )
        payload = json.loads(fixture_path.read_text(encoding="utf-8"))

        # Send webhook
        response = client.post(
            "/v1/webhooks/github",
            json=payload,
            headers={
                "X-GitHub-Event": "pull_request",
                "X-GitHub-Delivery": "test-delivery-001",
                "X-Hub-Signature-256": "dev",
            },
        )

        assert response.status_code == 202

        # Check that notification was created for the subscribed user
        notifications = list_notifications(conn=db, user_id=test_user_id, limit=10)

        assert len(notifications) > 0
        # The notification should be for the pull_request.opened event
        assert notifications[0].event_type == "webhook.pr_opened"
        assert notifications[0].user_id == test_user_id

    def test_webhook_without_subscription_no_notification(self, test_user_id):
        """Test that users without subscriptions don't receive notifications."""
        # Don't create any subscription
        db = get_db()

        # Load webhook fixture
        fixture_path = (
            pathlib.Path(__file__).parent
            / "fixtures"
            / "github"
            / "webhooks"
            / "pull_request.opened.json"
        )
        payload = json.loads(fixture_path.read_text(encoding="utf-8"))

        # Send webhook
        response = client.post(
            "/v1/webhooks/github",
            json=payload,
            headers={
                "X-GitHub-Event": "pull_request",
                "X-GitHub-Delivery": "test-delivery-002",
                "X-Hub-Signature-256": "dev",
            },
        )

        assert response.status_code == 202

        # Check that no notification was created for this user
        notifications = list_notifications(conn=db, user_id=test_user_id, limit=10)

        assert len(notifications) == 0

    def test_webhook_multiple_subscribers(self, test_user_id, test_user_id_2):
        """Test that webhooks notify multiple subscribed users."""
        # Create subscriptions for two users (must match the repository in the fixture)
        db = get_db()
        create_repo_subscription(
            conn=db,
            user_id=test_user_id,
            repo_full_name="testorg/testrepo",  # Matches pull_request.opened.json
        )
        create_repo_subscription(
            conn=db,
            user_id=test_user_id_2,
            repo_full_name="testorg/testrepo",  # Matches pull_request.opened.json
        )

        # Load webhook fixture
        fixture_path = (
            pathlib.Path(__file__).parent
            / "fixtures"
            / "github"
            / "webhooks"
            / "pull_request.opened.json"
        )
        payload = json.loads(fixture_path.read_text(encoding="utf-8"))

        # Send webhook
        response = client.post(
            "/v1/webhooks/github",
            json=payload,
            headers={
                "X-GitHub-Event": "pull_request",
                "X-GitHub-Delivery": "test-delivery-003",
                "X-Hub-Signature-256": "dev",
            },
        )

        assert response.status_code == 202

        # Check that both users received notifications
        notifications_user1 = list_notifications(conn=db, user_id=test_user_id, limit=10)
        notifications_user2 = list_notifications(conn=db, user_id=test_user_id_2, limit=10)

        assert len(notifications_user1) > 0
        assert len(notifications_user2) > 0
        assert notifications_user1[0].event_type == "webhook.pr_opened"
        assert notifications_user2[0].event_type == "webhook.pr_opened"
