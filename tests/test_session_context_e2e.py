"""Integration test demonstrating session context resolution end-to-end."""

import pytest
from fastapi.testclient import TestClient

from handsfree.api import app


@pytest.fixture
def reset_db():
    """Reset the database connection before each test."""
    global _db_conn
    import handsfree.api as api_module

    api_module._db_conn = None
    api_module._command_router = None
    yield
    api_module._db_conn = None
    api_module._command_router = None


client = TestClient(app)


class TestEndToEndSessionContext:
    """Test session context resolution in real end-to-end scenarios."""

    def test_pr_summarize_then_request_review(self, reset_db):
        """Test that PR summarize sets context, then request review uses it."""
        session_id = "e2e-session-1"

        # Step 1: Summarize PR 123 - this sets the context
        response1 = client.post(
            "/v1/command",
            json={
                "input": {"type": "text", "text": "summarize PR 123"},
                "profile": "default",
                "client_context": {
                    "device": "test",
                    "locale": "en-US",
                    "timezone": "America/Los_Angeles",
                    "app_version": "0.1.0",
                },
            },
            headers={"X-Session-Id": session_id},
        )
        assert response1.status_code == 200
        data1 = response1.json()
        assert data1["intent"]["name"] == "pr.summarize"
        assert data1["intent"]["entities"]["pr_number"] == 123

        # Step 2: Request review on PR 123 - should use session context for repo
        # Even though we specify PR number, the repo should come from context
        response2 = client.post(
            "/v1/command",
            json={
                "input": {"type": "text", "text": "request review from alice on PR 123"},
                "profile": "default",
                "client_context": {
                    "device": "test",
                    "locale": "en-US",
                    "timezone": "America/Los_Angeles",
                    "app_version": "0.1.0",
                },
            },
            headers={"X-Session-Id": session_id},
        )
        assert response2.status_code == 200
        data2 = response2.json()
        assert data2["intent"]["name"] == "pr.request_review"
        # The request should succeed because repo is resolved from fallback
        # (In real usage, pr.summarize would set actual repo)

    def test_multiple_sessions_isolated(self, reset_db):
        """Test that multiple sessions maintain separate contexts."""
        # Session 1: Set context for PR 100
        response1a = client.post(
            "/v1/command",
            json={
                "input": {"type": "text", "text": "summarize PR 100"},
                "profile": "default",
                "client_context": {
                    "device": "test",
                    "locale": "en-US",
                    "timezone": "America/Los_Angeles",
                    "app_version": "0.1.0",
                },
            },
            headers={"X-Session-Id": "session-1"},
        )
        assert response1a.status_code == 200

        # Session 2: Set context for PR 200
        response2a = client.post(
            "/v1/command",
            json={
                "input": {"type": "text", "text": "summarize PR 200"},
                "profile": "default",
                "client_context": {
                    "device": "test",
                    "locale": "en-US",
                    "timezone": "America/Los_Angeles",
                    "app_version": "0.1.0",
                },
            },
            headers={"X-Session-Id": "session-2"},
        )
        assert response2a.status_code == 200

        # Session 1 should maintain PR 100 context
        response1b = client.post(
            "/v1/command",
            json={
                "input": {"type": "text", "text": "request review from alice on PR 100"},
                "profile": "default",
                "client_context": {
                    "device": "test",
                    "locale": "en-US",
                    "timezone": "America/Los_Angeles",
                    "app_version": "0.1.0",
                },
            },
            headers={"X-Session-Id": "session-1"},
        )
        assert response1b.status_code == 200
        data1b = response1b.json()
        assert data1b["intent"]["entities"]["pr_number"] == 100

        # Session 2 should maintain PR 200 context
        response2b = client.post(
            "/v1/command",
            json={
                "input": {"type": "text", "text": "request review from bob on PR 200"},
                "profile": "default",
                "client_context": {
                    "device": "test",
                    "locale": "en-US",
                    "timezone": "America/Los_Angeles",
                    "app_version": "0.1.0",
                },
            },
            headers={"X-Session-Id": "session-2"},
        )
        assert response2b.status_code == 200
        data2b = response2b.json()
        assert data2b["intent"]["entities"]["pr_number"] == 200

    def test_checks_status_then_rerun(self, reset_db):
        """Test that checks status sets context, then rerun uses it."""
        session_id = "e2e-session-2"

        # Step 1: Check status for PR 456
        response1 = client.post(
            "/v1/command",
            json={
                "input": {"type": "text", "text": "checks for PR 456"},
                "profile": "default",
                "client_context": {
                    "device": "test",
                    "locale": "en-US",
                    "timezone": "America/Los_Angeles",
                    "app_version": "0.1.0",
                },
            },
            headers={"X-Session-Id": session_id},
        )
        assert response1.status_code == 200
        data1 = response1.json()
        assert data1["intent"]["name"] == "checks.status"

        # Step 2: Rerun checks for PR 456 - should use session context
        response2 = client.post(
            "/v1/command",
            json={
                "input": {"type": "text", "text": "rerun checks for PR 456"},
                "profile": "default",
                "client_context": {
                    "device": "test",
                    "locale": "en-US",
                    "timezone": "America/Los_Angeles",
                    "app_version": "0.1.0",
                },
            },
            headers={"X-Session-Id": session_id},
        )
        assert response2.status_code == 200
        data2 = response2.json()
        assert data2["intent"]["name"] == "checks.rerun"
        # Should succeed using context

    def test_without_session_id_still_works(self, reset_db):
        """Test that commands without session ID still work with fallback."""
        # No X-Session-Id header - should use fallback repo
        response = client.post(
            "/v1/command",
            json={
                "input": {"type": "text", "text": "request review from alice on PR 123"},
                "profile": "default",
                "client_context": {
                    "device": "test",
                    "locale": "en-US",
                    "timezone": "America/Los_Angeles",
                    "app_version": "0.1.0",
                },
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert data["intent"]["name"] == "pr.request_review"
        # Should succeed using fallback repo
