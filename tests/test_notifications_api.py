"""Tests for notifications API endpoint and integration."""

from datetime import UTC, datetime

import pytest
from fastapi.testclient import TestClient

from handsfree.api import app
from handsfree.db.notifications import create_notification

client = TestClient(app)


@pytest.fixture
def test_user_id():
    """Fixture user ID for testing."""
    return "00000000-0000-0000-0000-000000000001"


class TestNotificationsEndpoint:
    """Test GET /v1/notifications endpoint."""

    def test_get_notifications_empty(self):
        """Test getting notifications when there are none."""
        # Use a unique user ID to avoid interference from other tests
        response = client.get(
            "/v1/notifications",
            headers={"X-User-ID": "empty-user-00000000-0000-0000-0000-000000000000"}
        )

        assert response.status_code == 200
        data = response.json()
        assert "notifications" in data
        assert "count" in data
        # With a unique user ID, count should be 0
        assert data["count"] == 0
        assert len(data["notifications"]) == 0

    def test_get_notifications_with_data(self):
        """Test getting notifications with existing data."""
        # Create some notifications directly in the database
        from handsfree.api import get_db
        from handsfree.db.notifications import create_notification

        db = get_db()
        # Use a unique user ID for this test
        user_id = "test-user-with-data-0000-0000-0000-000000000001"

        create_notification(
            conn=db,
            user_id=user_id,
            event_type="test_event_1",
            message="Test message 1",
            metadata={"key": "value1"},
        )
        create_notification(
            conn=db,
            user_id=user_id,
            event_type="test_event_2",
            message="Test message 2",
            metadata={"key": "value2"},
        )

        response = client.get(
            "/v1/notifications",
            headers={"X-User-ID": user_id}
        )

        assert response.status_code == 200
        data = response.json()
        assert data["count"] == 2
        assert len(data["notifications"]) == 2

        # Check notification structure
        notif = data["notifications"][0]
        assert "id" in notif
        assert "user_id" in notif
        assert "event_type" in notif
        assert "message" in notif
        assert "metadata" in notif
        assert "created_at" in notif

    def test_get_notifications_with_limit(self):
        """Test getting notifications with limit parameter."""
        from handsfree.api import get_db

        db = get_db()
        user_id = "00000000-0000-0000-0000-000000000001"

        # Create multiple notifications
        for i in range(10):
            create_notification(
                conn=db,
                user_id=user_id,
                event_type=f"event_{i}",
                message=f"Message {i}",
            )

        response = client.get("/v1/notifications?limit=5")

        assert response.status_code == 200
        data = response.json()
        assert data["count"] == 5
        assert len(data["notifications"]) == 5

    def test_get_notifications_with_since_filter(self):
        """Test getting notifications with since timestamp."""
        import time

        from handsfree.api import get_db

        db = get_db()
        user_id = "00000000-0000-0000-0000-000000000001"

        # Create old notification
        create_notification(
            conn=db,
            user_id=user_id,
            event_type="old_event",
            message="Old message",
        )

        # Get timestamp
        cutoff = datetime.now(UTC)
        time.sleep(0.01)

        # Create new notification
        create_notification(
            conn=db,
            user_id=user_id,
            event_type="new_event",
            message="New message",
        )

        # Query with since filter
        response = client.get(
            f"/v1/notifications?since={cutoff.isoformat()}"
        )

        assert response.status_code == 200
        data = response.json()
        assert data["count"] == 1
        assert data["notifications"][0]["message"] == "New message"

    def test_get_notifications_with_custom_user_header(self):
        """Test getting notifications with custom user ID header."""
        from handsfree.api import get_db

        db = get_db()
        custom_user_id = "custom-user-123"

        # Create notification for custom user
        create_notification(
            conn=db,
            user_id=custom_user_id,
            event_type="custom_event",
            message="Custom user message",
        )

        # Query with custom user header
        response = client.get(
            "/v1/notifications",
            headers={"X-User-ID": custom_user_id},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["count"] == 1
        assert data["notifications"][0]["message"] == "Custom user message"

    def test_get_notifications_invalid_since_format(self):
        """Test getting notifications with invalid since format."""
        response = client.get("/v1/notifications?since=invalid-timestamp")

        assert response.status_code == 400
        data = response.json()
        assert "error" in data or "detail" in data


class TestAgentServiceNotifications:
    """Test that agent service emits notifications."""

    def test_delegate_creates_notification(self):
        """Test that delegating an agent task creates a notification."""
        from handsfree.agents.service import AgentService
        from handsfree.api import get_db
        from handsfree.db.notifications import list_notifications

        db = get_db()
        service = AgentService(db)
        user_id = "00000000-0000-0000-0000-000000000001"

        # Delegate a task
        result = service.delegate(
            user_id=user_id,
            instruction="Fix the bug",
            provider="copilot",
        )

        # Check that a notification was created
        notifs = list_notifications(conn=db, user_id=user_id)
        assert len(notifs) >= 1
        
        # Find the task_created notification
        task_notifs = [n for n in notifs if n.event_type == "task_created"]
        assert len(task_notifs) >= 1
        assert result["task_id"] in task_notifs[0].message
        assert task_notifs[0].metadata.get("task_id") == result["task_id"]

    def test_state_change_creates_notification(self):
        """Test that advancing task state creates a notification."""
        from handsfree.agents.service import AgentService
        from handsfree.api import get_db
        from handsfree.db.notifications import list_notifications

        db = get_db()
        service = AgentService(db)
        user_id = "00000000-0000-0000-0000-000000000001"

        # Create a task
        result = service.delegate(
            user_id=user_id,
            instruction="Fix the bug",
            provider="copilot",
        )
        task_id = result["task_id"]

        # Count notifications before state change
        notifs_before = list_notifications(conn=db, user_id=user_id)
        count_before = len(notifs_before)

        # Advance state
        service.advance_task_state(task_id=task_id, new_state="running")

        # Check that a new notification was created
        notifs_after = list_notifications(conn=db, user_id=user_id)
        assert len(notifs_after) == count_before + 1

        # Find the state_changed notification
        state_notifs = [n for n in notifs_after if n.event_type == "state_changed"]
        assert len(state_notifs) >= 1
        assert task_id in state_notifs[0].message


class TestWebhookNotifications:
    """Test that webhook events create notifications."""

    def test_pr_opened_webhook_creates_notification(self):
        """Test that PR opened webhook creates a notification."""
        from handsfree.api import get_db
        from handsfree.db.notifications import list_notifications

        db = get_db()
        # Use unique delivery ID to avoid duplicate rejection
        import uuid
        delivery_id = f"test-delivery-pr-opened-{uuid.uuid4()}"
        user_id = "00000000-0000-0000-0000-000000000001"

        # Count notifications before
        notifs_before = list_notifications(conn=db, user_id=user_id)
        count_before = len(notifs_before)

        # Send a PR opened webhook
        payload = {
            "action": "opened",
            "pull_request": {
                "number": 123,
                "title": "Test PR",
                "state": "open",
                "merged": False,
                "html_url": "https://github.com/test/repo/pull/123",
                "user": {"login": "testuser"},
                "base": {"ref": "main"},
                "head": {"ref": "feature", "sha": "abc123"},
            },
            "repository": {"full_name": "test/repo"},
        }

        response = client.post(
            "/v1/webhooks/github",
            json=payload,
            headers={
                "X-GitHub-Event": "pull_request",
                "X-GitHub-Delivery": delivery_id,
                "X-Hub-Signature-256": "dev",
            },
        )

        assert response.status_code == 202

        # Check that a notification was created
        notifs_after = list_notifications(conn=db, user_id=user_id)
        assert len(notifs_after) == count_before + 1

        # Find the webhook notification - get the most recent one
        webhook_notifs = [n for n in notifs_after if n.event_type == "webhook.pr_opened"]
        assert len(webhook_notifs) >= 1
        # Check the most recent notification
        latest_notif = webhook_notifs[0]
        assert "PR #123" in latest_notif.message
        assert "test/repo" in latest_notif.message
        assert latest_notif.metadata.get("pr_number") == 123

    def test_check_suite_completed_webhook_creates_notification(self):
        """Test that check_suite completed webhook creates a notification."""
        from handsfree.api import get_db
        from handsfree.db.notifications import list_notifications

        db = get_db()
        user_id = "00000000-0000-0000-0000-000000000001"

        # Count notifications before
        notifs_before = list_notifications(conn=db, user_id=user_id)
        count_before = len(notifs_before)

        # Send a check_suite completed webhook
        payload = {
            "action": "completed",
            "check_suite": {
                "id": 456,
                "conclusion": "success",
                "status": "completed",
                "head_sha": "abc123",
                "head_branch": "main",
                "pull_requests": [],
            },
            "repository": {"full_name": "test/repo"},
        }

        response = client.post(
            "/v1/webhooks/github",
            json=payload,
            headers={
                "X-GitHub-Event": "check_suite",
                "X-GitHub-Delivery": "test-delivery-check-suite",
                "X-Hub-Signature-256": "dev",
            },
        )

        assert response.status_code == 202

        # Check that a notification was created
        notifs_after = list_notifications(conn=db, user_id=user_id)
        assert len(notifs_after) == count_before + 1

        # Find the webhook notification
        webhook_notifs = [
            n for n in notifs_after if n.event_type == "webhook.check_suite_success"
        ]
        assert len(webhook_notifs) == 1
        assert "success" in webhook_notifs[0].message
        assert "test/repo" in webhook_notifs[0].message

    def test_review_submitted_webhook_creates_notification(self):
        """Test that pull_request_review submitted webhook creates a notification."""
        from handsfree.api import get_db
        from handsfree.db.notifications import list_notifications

        db = get_db()
        user_id = "00000000-0000-0000-0000-000000000001"

        # Count notifications before
        notifs_before = list_notifications(conn=db, user_id=user_id)
        count_before = len(notifs_before)

        # Send a review submitted webhook
        payload = {
            "action": "submitted",
            "review": {
                "id": 789,
                "state": "approved",
                "user": {"login": "reviewer"},
                "body": "LGTM",
                "html_url": "https://github.com/test/repo/pull/123#review-789",
            },
            "pull_request": {
                "number": 123,
            },
            "repository": {"full_name": "test/repo"},
        }

        response = client.post(
            "/v1/webhooks/github",
            json=payload,
            headers={
                "X-GitHub-Event": "pull_request_review",
                "X-GitHub-Delivery": "test-delivery-review",
                "X-Hub-Signature-256": "dev",
            },
        )

        assert response.status_code == 202

        # Check that a notification was created
        notifs_after = list_notifications(conn=db, user_id=user_id)
        assert len(notifs_after) == count_before + 1

        # Find the webhook notification
        webhook_notifs = [
            n for n in notifs_after if n.event_type == "webhook.review_approved"
        ]
        assert len(webhook_notifs) == 1
        assert "approved" in webhook_notifs[0].message
        assert "reviewer" in webhook_notifs[0].message
        assert "PR #123" in webhook_notifs[0].message
