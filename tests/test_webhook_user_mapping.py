"""Tests for webhook user mapping and production secret configuration."""

import json
import os
import pathlib
import uuid

import pytest
from fastapi.testclient import TestClient

from handsfree.api import app, get_db
from handsfree.auth import FIXTURE_USER_ID
from handsfree.db.github_connections import create_github_connection
from handsfree.db.notifications import list_notifications
from handsfree.db.repo_subscriptions import create_repo_subscription
from handsfree.webhooks import extract_installation_id, get_webhook_secret


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
    conn.execute("DELETE FROM webhook_events")
    conn.execute("DELETE FROM notifications")
    conn.execute("DELETE FROM repo_subscriptions")
    conn.execute("DELETE FROM github_connections")

    # Clear environment variable for clean state
    if "GITHUB_WEBHOOK_SECRET" in os.environ:
        del os.environ["GITHUB_WEBHOOK_SECRET"]


@pytest.fixture
def client():
    """Create FastAPI test client."""
    return TestClient(app)


def load_fixture(filename: str) -> dict:
    """Load a webhook fixture from tests/fixtures/github/webhooks/."""
    fixture_path = pathlib.Path(__file__).parent / "fixtures" / "github" / "webhooks" / filename
    return json.loads(fixture_path.read_text(encoding="utf-8"))


class TestWebhookSecretConfiguration:
    """Test environment-controlled webhook secret verification."""

    def test_dev_mode_accepts_dev_signature(self, client):
        """Test that 'dev' signature works when no secret is configured."""
        # Ensure no secret is set
        assert get_webhook_secret() is None

        payload = load_fixture("pull_request.opened.json")
        response = client.post(
            "/v1/webhooks/github",
            json=payload,
            headers={
                "X-GitHub-Event": "pull_request",
                "X-GitHub-Delivery": f"test-dev-sig-{uuid.uuid4()}",
                "X-Hub-Signature-256": "dev",
            },
        )
        assert response.status_code == 202

    def test_dev_signature_rejected_when_secret_configured(self, client, monkeypatch):
        """Test that 'dev' signature is rejected when a real secret is configured."""
        # Set a secret
        monkeypatch.setenv("GITHUB_WEBHOOK_SECRET", "my-secret-key")
        assert get_webhook_secret() == "my-secret-key"

        payload = load_fixture("pull_request.opened.json")
        response = client.post(
            "/v1/webhooks/github",
            json=payload,
            headers={
                "X-GitHub-Event": "pull_request",
                "X-GitHub-Delivery": f"test-reject-dev-{uuid.uuid4()}",
                "X-Hub-Signature-256": "dev",
            },
        )
        assert response.status_code == 400
        assert "Invalid signature" in response.json()["message"]

    def test_production_mode_requires_valid_signature(self, client, monkeypatch):
        """Test that invalid signatures are rejected when secret is configured."""
        # Set a secret
        monkeypatch.setenv("GITHUB_WEBHOOK_SECRET", "my-secret-key")

        payload = load_fixture("pull_request.opened.json")
        response = client.post(
            "/v1/webhooks/github",
            json=payload,
            headers={
                "X-GitHub-Event": "pull_request",
                "X-GitHub-Delivery": f"test-invalid-sig-{uuid.uuid4()}",
                "X-Hub-Signature-256": "sha256=invalid",
            },
        )
        assert response.status_code == 400
        assert "Invalid signature" in response.json()["message"]

    def test_production_mode_accepts_valid_signature(self, client, monkeypatch):
        """Test that valid HMAC signatures work when secret is configured."""
        import hashlib
        import hmac

        # Set a secret
        secret = "my-secret-key"
        monkeypatch.setenv("GITHUB_WEBHOOK_SECRET", secret)

        payload = load_fixture("pull_request.opened.json")
        payload_bytes = json.dumps(payload, separators=(",", ":")).encode("utf-8")

        # Compute valid signature
        signature = hmac.new(
            secret.encode("utf-8"),
            payload_bytes,
            hashlib.sha256,
        ).hexdigest()

        response = client.post(
            "/v1/webhooks/github",
            data=payload_bytes,
            headers={
                "X-GitHub-Event": "pull_request",
                "X-GitHub-Delivery": f"test-valid-sig-{uuid.uuid4()}",
                "X-Hub-Signature-256": f"sha256={signature}",
                "Content-Type": "application/json",
            },
        )
        assert response.status_code == 202


class TestWebhookUserMapping:
    """Test webhook notification routing based on user subscriptions."""

    def test_webhook_notification_routed_to_subscribed_user_by_repo(self, client):
        """Test that webhook notifications go to users subscribed by repo name."""
        db = get_db()
        test_user_id = str(uuid.uuid4())
        repo_name = "testorg/testrepo"

        # Create a repo subscription for test user
        create_repo_subscription(db, test_user_id, repo_name)

        # Send webhook
        payload = load_fixture("pull_request.opened.json")
        response = client.post(
            "/v1/webhooks/github",
            json=payload,
            headers={
                "X-GitHub-Event": "pull_request",
                "X-GitHub-Delivery": f"test-user-mapping-{uuid.uuid4()}",
                "X-Hub-Signature-256": "dev",
            },
        )
        assert response.status_code == 202

        # Check that notification was created for test user
        notifs = list_notifications(db, test_user_id)
        assert len(notifs) == 1
        assert notifs[0].event_type == "webhook.pr_opened"
        assert "testorg/testrepo" in notifs[0].message

        # Verify fixture user did NOT receive the notification
        fixture_notifs = list_notifications(db, FIXTURE_USER_ID)
        assert len(fixture_notifs) == 0

    def test_webhook_notification_routed_to_subscribed_user_by_installation(self, client):
        """Test that webhook notifications go to users connected via installation_id."""
        db = get_db()
        test_user_id = str(uuid.uuid4())
        installation_id = 12345

        # Create a GitHub connection for test user with installation_id
        create_github_connection(db, test_user_id, installation_id=installation_id)

        # Load and modify payload to include installation
        payload = load_fixture("pull_request.opened.json")
        payload["installation"] = {"id": installation_id}

        response = client.post(
            "/v1/webhooks/github",
            json=payload,
            headers={
                "X-GitHub-Event": "pull_request",
                "X-GitHub-Delivery": f"test-installation-mapping-{uuid.uuid4()}",
                "X-Hub-Signature-256": "dev",
            },
        )
        assert response.status_code == 202

        # Check that notification was created for test user
        notifs = list_notifications(db, test_user_id)
        assert len(notifs) == 1
        assert notifs[0].event_type == "webhook.pr_opened"

        # Verify fixture user did NOT receive the notification
        fixture_notifs = list_notifications(db, FIXTURE_USER_ID)
        assert len(fixture_notifs) == 0

    def test_webhook_notification_to_multiple_subscribed_users(self, client):
        """Test that webhook notifications are sent to all subscribed users."""
        db = get_db()
        user1_id = str(uuid.uuid4())
        user2_id = str(uuid.uuid4())
        repo_name = "testorg/testrepo"

        # Create subscriptions for both users
        create_repo_subscription(db, user1_id, repo_name)
        create_repo_subscription(db, user2_id, repo_name)

        # Send webhook
        payload = load_fixture("pull_request.opened.json")
        response = client.post(
            "/v1/webhooks/github",
            json=payload,
            headers={
                "X-GitHub-Event": "pull_request",
                "X-GitHub-Delivery": f"test-multi-user-{uuid.uuid4()}",
                "X-Hub-Signature-256": "dev",
            },
        )
        assert response.status_code == 202

        # Check that both users received notifications
        notifs1 = list_notifications(db, user1_id)
        assert len(notifs1) == 1

        notifs2 = list_notifications(db, user2_id)
        assert len(notifs2) == 1

    def test_webhook_without_subscription_creates_no_notification(self, client):
        """Test that webhooks for unsubscribed repos don't create notifications."""
        db = get_db()

        # Send webhook without any subscriptions
        payload = load_fixture("pull_request.opened.json")
        response = client.post(
            "/v1/webhooks/github",
            json=payload,
            headers={
                "X-GitHub-Event": "pull_request",
                "X-GitHub-Delivery": f"test-no-subscription-{uuid.uuid4()}",
                "X-Hub-Signature-256": "dev",
            },
        )
        assert response.status_code == 202

        # Verify no notifications were created for fixture user
        fixture_notifs = list_notifications(db, FIXTURE_USER_ID)
        assert len(fixture_notifs) == 0

    def test_check_suite_webhook_routing(self, client):
        """Test that check_suite webhooks are routed correctly."""
        db = get_db()
        test_user_id = str(uuid.uuid4())
        repo_name = "testorg/testrepo"

        create_repo_subscription(db, test_user_id, repo_name)

        payload = load_fixture("check_suite.completed.json")
        response = client.post(
            "/v1/webhooks/github",
            json=payload,
            headers={
                "X-GitHub-Event": "check_suite",
                "X-GitHub-Delivery": f"test-check-suite-routing-{uuid.uuid4()}",
                "X-Hub-Signature-256": "dev",
            },
        )
        assert response.status_code == 202

        notifs = list_notifications(db, test_user_id)
        assert len(notifs) == 1
        assert notifs[0].event_type == "webhook.check_suite_success"

    def test_review_webhook_routing(self, client):
        """Test that review webhooks are routed correctly."""
        db = get_db()
        test_user_id = str(uuid.uuid4())
        repo_name = "testorg/testrepo"

        create_repo_subscription(db, test_user_id, repo_name)

        payload = load_fixture("pull_request_review.submitted.json")
        response = client.post(
            "/v1/webhooks/github",
            json=payload,
            headers={
                "X-GitHub-Event": "pull_request_review",
                "X-GitHub-Delivery": f"test-review-routing-{uuid.uuid4()}",
                "X-Hub-Signature-256": "dev",
            },
        )
        assert response.status_code == 202

        notifs = list_notifications(db, test_user_id)
        assert len(notifs) == 1
        assert notifs[0].event_type == "webhook.review_approved"

    def test_issue_comment_mention_notification(self, client):
        """Test that issue_comment webhooks create mention notifications for subscribed users."""
        db = get_db()
        # Create a test user with UUID
        test_user_id = str(uuid.uuid4())
        repo_name = "testorg/testrepo"

        # Create a repo subscription for the user
        create_repo_subscription(db, test_user_id, repo_name)

        payload = load_fixture("issue_comment.created.json")
        response = client.post(
            "/v1/webhooks/github",
            json=payload,
            headers={
                "X-GitHub-Event": "issue_comment",
                "X-GitHub-Delivery": f"test-mention-{uuid.uuid4()}",
                "X-Hub-Signature-256": "dev",
            },
        )
        assert response.status_code == 202

        # Check that notification was created for subscribed user
        notifs = list_notifications(db, test_user_id)
        assert len(notifs) == 1
        assert notifs[0].event_type == "webhook.mention"
        assert "commenter" in notifs[0].message
        assert "testorg/testrepo" in notifs[0].message
        assert "PR #42" in notifs[0].message
        assert notifs[0].metadata["comment_author"] == "commenter"
        assert notifs[0].metadata["is_pull_request"] is True
        assert "testuser" in notifs[0].metadata["mentions"]
        assert "anotheruser" in notifs[0].metadata["mentions"]

    def test_issue_comment_no_mention_no_notification(self, client):
        """Test that issue_comment webhooks without mentions don't create notifications."""
        db = get_db()
        test_user_id = str(uuid.uuid4())
        repo_name = "testorg/testrepo"

        # Create a repo subscription
        create_repo_subscription(db, test_user_id, repo_name)

        # Modify the payload to have no mentions
        payload = load_fixture("issue_comment.created.json")
        payload["comment"]["body"] = "This is a comment without any mentions."
        
        response = client.post(
            "/v1/webhooks/github",
            json=payload,
            headers={
                "X-GitHub-Event": "issue_comment",
                "X-GitHub-Delivery": f"test-no-mention-{uuid.uuid4()}",
                "X-Hub-Signature-256": "dev",
            },
        )
        assert response.status_code == 202

        # Check that no notification was created when there are no mentions
        notifs = list_notifications(db, test_user_id)
        assert len(notifs) == 0

    def test_issue_comment_multiple_mentions(self, client):
        """Test that issue_comment webhooks notify all subscribed users when there are mentions."""
        db = get_db()
        # Create test users with UUIDs
        user1_id = str(uuid.uuid4())
        user2_id = str(uuid.uuid4())
        repo_name = "testorg/testrepo"

        # Create subscriptions for both users
        create_repo_subscription(db, user1_id, repo_name)
        create_repo_subscription(db, user2_id, repo_name)

        payload = load_fixture("issue_comment.created.json")
        response = client.post(
            "/v1/webhooks/github",
            json=payload,
            headers={
                "X-GitHub-Event": "issue_comment",
                "X-GitHub-Delivery": f"test-multi-mention-{uuid.uuid4()}",
                "X-Hub-Signature-256": "dev",
            },
        )
        assert response.status_code == 202

        # Check that both subscribed users received notifications
        notifs1 = list_notifications(db, user1_id)
        assert len(notifs1) == 1
        assert notifs1[0].event_type == "webhook.mention"
        assert "testuser" in notifs1[0].metadata["mentions"]
        assert "anotheruser" in notifs1[0].metadata["mentions"]

        notifs2 = list_notifications(db, user2_id)
        assert len(notifs2) == 1
        assert notifs2[0].event_type == "webhook.mention"


class TestWebhookPayloadExtraction:
    """Test helper functions for extracting data from webhook payloads."""

    def test_extract_installation_id_present(self):
        """Test extracting installation_id from payload."""
        payload = {"installation": {"id": 12345}}
        assert extract_installation_id(payload) == 12345

    def test_extract_installation_id_missing(self):
        """Test extracting installation_id when not present."""
        payload = {"repository": {"full_name": "test/repo"}}
        assert extract_installation_id(payload) is None

    def test_extract_installation_id_invalid_format(self):
        """Test extracting installation_id with invalid format."""
        payload = {"installation": "not-a-dict"}
        assert extract_installation_id(payload) is None
