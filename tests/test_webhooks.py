"""Tests for GitHub webhook ingestion and replay."""

import json
import pathlib

import pytest
from fastapi.testclient import TestClient

from handsfree.api import app
from handsfree.db import get_connection
from handsfree.db.webhook_events import get_db_webhook_store
from handsfree.webhooks import normalize_github_event


@pytest.fixture(autouse=True)
def reset_webhook_store():
    """Reset webhook store before each test."""
    # Clean up DB-backed store
    with get_connection() as conn:
        conn.execute("DELETE FROM webhook_events")


@pytest.fixture
def client():
    """Create FastAPI test client."""
    return TestClient(app)


def load_fixture(filename: str) -> dict:
    """Load a webhook fixture from tests/fixtures/github/webhooks/."""
    fixture_path = pathlib.Path(__file__).parent / "fixtures" / "github" / "webhooks" / filename
    return json.loads(fixture_path.read_text(encoding="utf-8"))


def infer_event_type_from_filename(filename: str) -> str:
    """Infer GitHub event type from fixture filename.

    Example: pull_request.opened.json -> pull_request
    """
    return filename.split(".")[0]


class TestWebhookIngestion:
    """Test webhook endpoint with signature verification and replay protection."""

    def test_pull_request_opened(self, client):
        """Test ingesting a pull_request opened event."""
        payload = load_fixture("pull_request.opened.json")
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
        data = response.json()
        assert "event_id" in data
        assert data["message"] == "Webhook accepted"

        # Verify event was stored
        store = get_db_webhook_store()
        event = store.get_event(data["event_id"])
        assert event is not None
        assert event["source"] == "github"
        assert event["event_type"] == "pull_request"
        assert event["delivery_id"] == "test-delivery-001"
        assert event["signature_ok"] is True
        assert event["payload"]["action"] == "opened"

    def test_pull_request_synchronize(self, client):
        """Test ingesting a pull_request synchronize event."""
        payload = load_fixture("pull_request.synchronize.json")
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

    def test_check_suite_completed(self, client):
        """Test ingesting a check_suite completed event."""
        payload = load_fixture("check_suite.completed.json")
        response = client.post(
            "/v1/webhooks/github",
            json=payload,
            headers={
                "X-GitHub-Event": "check_suite",
                "X-GitHub-Delivery": "test-delivery-003",
                "X-Hub-Signature-256": "dev",
            },
        )
        assert response.status_code == 202

    def test_check_run_completed(self, client):
        """Test ingesting a check_run completed event."""
        payload = load_fixture("check_run.completed.json")
        response = client.post(
            "/v1/webhooks/github",
            json=payload,
            headers={
                "X-GitHub-Event": "check_run",
                "X-GitHub-Delivery": "test-delivery-004",
                "X-Hub-Signature-256": "dev",
            },
        )
        assert response.status_code == 202

    def test_pull_request_review_submitted(self, client):
        """Test ingesting a pull_request_review submitted event."""
        payload = load_fixture("pull_request_review.submitted.json")
        response = client.post(
            "/v1/webhooks/github",
            json=payload,
            headers={
                "X-GitHub-Event": "pull_request_review",
                "X-GitHub-Delivery": "test-delivery-005",
                "X-Hub-Signature-256": "dev",
            },
        )
        assert response.status_code == 202

    def test_duplicate_delivery_rejected(self, client):
        """Test that duplicate delivery IDs are rejected (replay protection)."""
        payload = load_fixture("pull_request.opened.json")

        # First delivery should succeed
        response1 = client.post(
            "/v1/webhooks/github",
            json=payload,
            headers={
                "X-GitHub-Event": "pull_request",
                "X-GitHub-Delivery": "test-delivery-duplicate",
                "X-Hub-Signature-256": "dev",
            },
        )
        assert response1.status_code == 202

        # Second delivery with same ID should be rejected
        response2 = client.post(
            "/v1/webhooks/github",
            json=payload,
            headers={
                "X-GitHub-Event": "pull_request",
                "X-GitHub-Delivery": "test-delivery-duplicate",
                "X-Hub-Signature-256": "dev",
            },
        )
        assert response2.status_code == 400
        assert "Duplicate delivery ID" in response2.json()["detail"]

    def test_invalid_signature_rejected(self, client):
        """Test that webhooks with invalid signatures are rejected."""
        payload = load_fixture("pull_request.opened.json")
        response = client.post(
            "/v1/webhooks/github",
            json=payload,
            headers={
                "X-GitHub-Event": "pull_request",
                "X-GitHub-Delivery": "test-delivery-006",
                "X-Hub-Signature-256": "sha256=invalid",
            },
        )
        assert response.status_code == 400
        assert "Invalid signature" in response.json()["detail"]

    def test_all_fixtures_can_be_replayed(self, client):
        """Test that all fixtures in the webhooks directory can be successfully ingested."""
        fixtures_dir = pathlib.Path(__file__).parent / "fixtures" / "github" / "webhooks"
        fixtures = list(fixtures_dir.glob("*.json"))
        assert len(fixtures) > 0, "No fixtures found"

        for fixture_file in fixtures:
            payload = json.loads(fixture_file.read_text(encoding="utf-8"))
            event_type = infer_event_type_from_filename(fixture_file.name)
            delivery_id = f"test-replay-{fixture_file.name}"

            response = client.post(
                "/v1/webhooks/github",
                json=payload,
                headers={
                    "X-GitHub-Event": event_type,
                    "X-GitHub-Delivery": delivery_id,
                    "X-Hub-Signature-256": "dev",
                },
            )

            assert response.status_code == 202, (
                f"Failed to ingest fixture {fixture_file.name}: "
                f"{response.status_code} {response.text}"
            )


class TestEventNormalization:
    """Test event normalization for different webhook types."""

    def test_pull_request_opened_normalized(self, client):
        """Test that pull_request opened events are normalized correctly."""
        payload = load_fixture("pull_request.opened.json")
        normalized = normalize_github_event("pull_request", payload)

        assert normalized is not None
        assert normalized["event_type"] == "pull_request"
        assert normalized["action"] == "opened"
        assert normalized["repo"] == "testorg/testrepo"
        assert normalized["pr_number"] == 123
        assert normalized["pr_title"] == "Add webhook ingestion feature"
        assert normalized["pr_author"] == "testuser"
        assert normalized["base_ref"] == "main"
        assert normalized["head_ref"] == "feature-branch"

    def test_check_suite_completed_normalized(self, client):
        """Test that check_suite completed events are normalized correctly."""
        payload = load_fixture("check_suite.completed.json")
        normalized = normalize_github_event("check_suite", payload)

        assert normalized is not None
        assert normalized["event_type"] == "check_suite"
        assert normalized["action"] == "completed"
        assert normalized["repo"] == "testorg/testrepo"
        assert normalized["conclusion"] == "success"
        assert normalized["status"] == "completed"
        assert 123 in normalized["pr_numbers"]

    def test_pull_request_review_submitted_normalized(self, client):
        """Test that pull_request_review submitted events are normalized correctly."""
        payload = load_fixture("pull_request_review.submitted.json")
        normalized = normalize_github_event("pull_request_review", payload)

        assert normalized is not None
        assert normalized["event_type"] == "pull_request_review"
        assert normalized["action"] == "submitted"
        assert normalized["repo"] == "testorg/testrepo"
        assert normalized["pr_number"] == 123
        assert normalized["review_state"] == "approved"
        assert normalized["review_author"] == "reviewer1"
