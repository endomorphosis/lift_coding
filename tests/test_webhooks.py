"""Tests for GitHub webhook ingestion and replay."""

import json
import pathlib

import pytest
from fastapi.testclient import TestClient

from handsfree.api import app, get_db_webhook_store
from handsfree.webhooks import normalize_github_event


@pytest.fixture(autouse=True)
def reset_webhook_store():
    """Reset webhook store before each test."""
    # Clean up DB-backed store using the shared connection from api.py
    from handsfree import api

    # Reset global state in api.py
    api._db_conn = None
    api._webhook_store = None
    api._command_router = None

    # Get fresh DB connection and clear webhook events
    conn = api.get_db()
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

    def test_issue_comment_created(self, client):
        """Test ingesting an issue_comment created event."""
        payload = load_fixture("issue_comment.created.json")
        response = client.post(
            "/v1/webhooks/github",
            json=payload,
            headers={
                "X-GitHub-Event": "issue_comment",
                "X-GitHub-Delivery": "test-delivery-006",
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
        assert event["event_type"] == "issue_comment"
        assert event["delivery_id"] == "test-delivery-006"
        assert event["signature_ok"] is True
        assert event["payload"]["action"] == "created"

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
        assert "Duplicate delivery ID" in response2.json()["message"]

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
        assert "Invalid signature" in response.json()["message"]

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

    def test_issue_comment_created_normalized(self, client):
        """Test that issue_comment created events are normalized correctly."""
        payload = load_fixture("issue_comment.created.json")
        normalized = normalize_github_event("issue_comment", payload)

        assert normalized is not None
        assert normalized["event_type"] == "issue_comment"
        assert normalized["action"] == "created"
        assert normalized["repo"] == "testorg/testrepo"
        assert normalized["issue_number"] == 42
        assert normalized["is_pull_request"] is True
        assert normalized["comment_author"] == "commenter"
        assert (
            normalized["comment_url"]
            == "https://github.com/testorg/testrepo/issues/42#issuecomment-999888777"
        )
        assert "testuser" in normalized["mentions"]
        assert "anotheruser" in normalized["mentions"]
        assert len(normalized["mentions"]) == 2


class TestDatabaseBackedStore:
    """Test database-backed webhook storage and replay protection."""

    def test_db_store_persists_events(self, client):
        """Test that events are persisted to the database."""
        payload = load_fixture("pull_request.opened.json")
        response = client.post(
            "/v1/webhooks/github",
            json=payload,
            headers={
                "X-GitHub-Event": "pull_request",
                "X-GitHub-Delivery": "test-db-persist-001",
                "X-Hub-Signature-256": "dev",
            },
        )
        assert response.status_code == 202
        event_id = response.json()["event_id"]

        # Verify the event can be retrieved from DB
        store = get_db_webhook_store()
        event = store.get_event(event_id)
        assert event is not None
        assert event["id"] == event_id
        assert event["delivery_id"] == "test-db-persist-001"
        assert event["source"] == "github"
        assert event["event_type"] == "pull_request"
        assert event["signature_ok"] is True
        assert event["payload"]["action"] == "opened"

    def test_db_replay_protection_across_sessions(self, client):
        """Test that replay protection works across sessions (via DB)."""
        payload = load_fixture("pull_request.opened.json")
        delivery_id = "test-db-replay-001"

        # First request should succeed
        response1 = client.post(
            "/v1/webhooks/github",
            json=payload,
            headers={
                "X-GitHub-Event": "pull_request",
                "X-GitHub-Delivery": delivery_id,
                "X-Hub-Signature-256": "dev",
            },
        )
        assert response1.status_code == 202

        # Create a new store instance (simulating a new session/process)
        store = get_db_webhook_store()

        # Replay protection should still work via DB
        assert store.is_duplicate_delivery(delivery_id) is True

        # Second request with same delivery ID should fail
        response2 = client.post(
            "/v1/webhooks/github",
            json=payload,
            headers={
                "X-GitHub-Event": "pull_request",
                "X-GitHub-Delivery": delivery_id,
                "X-Hub-Signature-256": "dev",
            },
        )
        assert response2.status_code == 400
        assert "Duplicate delivery ID" in response2.json()["message"]

    def test_db_list_events(self, client):
        """Test that list_events retrieves events from database."""
        # Post multiple events
        for i in range(5):
            payload = load_fixture("pull_request.opened.json")
            client.post(
                "/v1/webhooks/github",
                json=payload,
                headers={
                    "X-GitHub-Event": "pull_request",
                    "X-GitHub-Delivery": f"test-db-list-{i:03d}",
                    "X-Hub-Signature-256": "dev",
                },
            )

        # Retrieve events
        store = get_db_webhook_store()
        events = store.list_events(limit=10)

        assert len(events) >= 5
        # Events should be ordered by received_at DESC
        delivery_ids = [
            e["delivery_id"] for e in events if e["delivery_id"].startswith("test-db-list-")
        ]
        assert len(delivery_ids) == 5


class TestWebhookProcessingFailures:
    """Test webhook processing failure tracking and retry mechanism."""

    def test_normalization_failure_recorded(self, client, monkeypatch):
        """Test that normalization failures are recorded in the database."""

        # Monkeypatch normalize_github_event to raise an exception
        def failing_normalize(event_type, payload):
            raise ValueError("Simulated normalization failure")

        # Patch where it's imported in api.py
        from handsfree import api

        monkeypatch.setattr(api, "normalize_github_event", failing_normalize)

        payload = load_fixture("pull_request.opened.json")
        response = client.post(
            "/v1/webhooks/github",
            json=payload,
            headers={
                "X-GitHub-Event": "pull_request",
                "X-GitHub-Delivery": "test-failure-001",
                "X-Hub-Signature-256": "dev",
            },
        )
        # Event should still be accepted (202) even if normalization fails
        assert response.status_code == 202
        event_id = response.json()["event_id"]

        # Check that the failure was recorded
        store = get_db_webhook_store()
        event = store.get_event(event_id)
        assert event is not None
        assert event["processed_ok"] is False
        assert event["processing_error"] is not None
        assert "ValueError" in event["processing_error"]
        assert "normalization" in event["processing_error"]
        assert event["processed_at"] is not None
        # Ensure raw payload is NOT in the error message
        assert "testuser" not in event["processing_error"]

    def test_successful_processing_recorded(self, client):
        """Test that successful processing is recorded."""
        payload = load_fixture("pull_request.opened.json")
        response = client.post(
            "/v1/webhooks/github",
            json=payload,
            headers={
                "X-GitHub-Event": "pull_request",
                "X-GitHub-Delivery": "test-success-001",
                "X-Hub-Signature-256": "dev",
            },
        )
        assert response.status_code == 202
        event_id = response.json()["event_id"]

        # Check that success was recorded
        store = get_db_webhook_store()
        event = store.get_event(event_id)
        assert event is not None
        assert event["processed_ok"] is True
        assert event["processing_error"] is None
        assert event["processed_at"] is not None

    def test_retry_endpoint_reprocesses_failed_event(self, client, monkeypatch):
        """Test that the retry endpoint can reprocess a failed event."""

        # First, create a failed event
        def failing_normalize(event_type, payload):
            raise ValueError("Simulated normalization failure")

        from handsfree import api

        monkeypatch.setattr(api, "normalize_github_event", failing_normalize)

        payload = load_fixture("pull_request.opened.json")
        response = client.post(
            "/v1/webhooks/github",
            json=payload,
            headers={
                "X-GitHub-Event": "pull_request",
                "X-GitHub-Delivery": "test-retry-001",
                "X-Hub-Signature-256": "dev",
            },
        )
        assert response.status_code == 202
        event_id = response.json()["event_id"]

        # Verify it failed
        store = get_db_webhook_store()
        event = store.get_event(event_id)
        assert event["processed_ok"] is False

        # Now restore normal normalization and retry
        monkeypatch.undo()

        retry_response = client.post(f"/v1/webhooks/retry/{event_id}")
        assert retry_response.status_code == 200
        retry_data = retry_response.json()
        assert retry_data["status"] == "success"
        assert retry_data["event_id"] == event_id

        # Verify it now shows as successful
        event = store.get_event(event_id)
        assert event["processed_ok"] is True
        assert event["processing_error"] is None

    def test_retry_endpoint_handles_invalid_event_id(self, client):
        """Test that retry endpoint returns 404 for non-existent event."""
        response = client.post("/v1/webhooks/retry/non-existent-event-id")
        assert response.status_code == 404
        data = response.json()
        assert data["error"] == "not_found"

    def test_retry_endpoint_marks_failure_on_repeated_error(self, client, monkeypatch):
        """Test that retry endpoint records failure if error persists."""
        # Create a successful event first
        payload = load_fixture("pull_request.opened.json")
        response = client.post(
            "/v1/webhooks/github",
            json=payload,
            headers={
                "X-GitHub-Event": "pull_request",
                "X-GitHub-Delivery": "test-retry-fail-001",
                "X-Hub-Signature-256": "dev",
            },
        )
        assert response.status_code == 202
        event_id = response.json()["event_id"]

        # Now make normalization fail on retry
        def failing_normalize(event_type, payload):
            raise RuntimeError("Persistent failure")

        from handsfree import api

        monkeypatch.setattr(api, "normalize_github_event", failing_normalize)

        retry_response = client.post(f"/v1/webhooks/retry/{event_id}")
        assert retry_response.status_code == 200
        retry_data = retry_response.json()
        assert retry_data["status"] == "failed"
        assert "RuntimeError" in retry_data["message"]

        # Verify failure is recorded
        store = get_db_webhook_store()
        event = store.get_event(event_id)
        assert event["processed_ok"] is False
        assert "RuntimeError" in event["processing_error"]

    def test_unsupported_event_type_not_marked_as_failure(self, client):
        """Test that unsupported event types are not marked as failures."""
        # Create a payload for an unsupported event type
        payload = {"action": "started", "repository": {"full_name": "test/repo"}}
        response = client.post(
            "/v1/webhooks/github",
            json=payload,
            headers={
                "X-GitHub-Event": "unsupported_event",
                "X-GitHub-Delivery": "test-unsupported-001",
                "X-Hub-Signature-256": "dev",
            },
        )
        assert response.status_code == 202
        event_id = response.json()["event_id"]

        # Event should be stored but not marked as failed (since it's just unsupported)
        store = get_db_webhook_store()
        event = store.get_event(event_id)
        assert event is not None
        # processed_ok should be None for unsupported events
        assert event["processed_ok"] is None
        assert event["processing_error"] is None
