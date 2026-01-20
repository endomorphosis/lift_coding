"""Tests for confirming router-issued pending action tokens.

This test suite validates that router-issued tokens (from PendingActionManager)
execute real action handlers instead of returning fixture responses.
"""

import pytest
from fastapi.testclient import TestClient

from handsfree.api import app
from handsfree.auth import FIXTURE_USER_ID

client = TestClient(app)


class TestConfirmRouterTokens:
    """Test confirmation flow for router-issued tokens."""

    def test_confirm_pr_request_review_router_token(self):
        """Test that confirming a router-issued pr.request_review token executes real handler."""
        # First, create a pending action using pr.request_review intent in workout profile
        # which requires confirmation
        cmd_response = client.post(
            "/v1/command",
            json={
                "input": {"type": "text", "text": "request review from alice on pr 100"},
                "profile": "workout",
                "client_context": {
                    "device": "simulator",
                    "locale": "en-US",
                    "timezone": "America/Los_Angeles",
                    "app_version": "0.1.0",
                },
            },
        )

        assert cmd_response.status_code == 200
        cmd_data = cmd_response.json()
        assert cmd_data["status"] == "needs_confirmation"
        assert "pending_action" in cmd_data
        token = cmd_data["pending_action"]["token"]

        # Now confirm it - should execute real handler, not return fixture text
        confirm_response = client.post(
            "/v1/commands/confirm",
            json={"token": token, "idempotency_key": "confirm-test-request-review"},
        )

        assert confirm_response.status_code == 200
        data = confirm_response.json()
        assert data["status"] == "ok"
        assert data["intent"]["name"] == "request_review.confirmed"
        
        # Should NOT contain "(Fixture response)" text anymore
        assert "(Fixture response)" not in data["spoken_text"]
        
        # Should mention the action was executed
        assert "review requested" in data["spoken_text"].lower() or "alice" in data["spoken_text"].lower()

    def test_confirm_pr_merge_router_token(self):
        """Test that confirming a router-issued pr.merge token executes real handler."""
        # Create pending action using pr.merge intent in workout profile
        cmd_response = client.post(
            "/v1/command",
            json={
                "input": {"type": "text", "text": "merge pr 200"},
                "profile": "workout",
                "client_context": {
                    "device": "simulator",
                    "locale": "en-US",
                    "timezone": "America/Los_Angeles",
                    "app_version": "0.1.0",
                },
            },
        )

        assert cmd_response.status_code == 200
        cmd_data = cmd_response.json()
        assert cmd_data["status"] == "needs_confirmation"
        assert "pending_action" in cmd_data
        token = cmd_data["pending_action"]["token"]

        # Confirm the merge
        confirm_response = client.post(
            "/v1/commands/confirm",
            json={"token": token, "idempotency_key": "confirm-test-merge"},
        )

        assert confirm_response.status_code == 200
        data = confirm_response.json()
        assert data["status"] == "ok"
        assert data["intent"]["name"] == "merge.confirmed"
        
        # Should NOT contain "(Fixture response)" text
        assert "(Fixture response)" not in data["spoken_text"]
        
        # Should mention merge action
        assert "merged" in data["spoken_text"].lower()

    def test_confirm_agent_delegate_router_token(self):
        """Test that confirming a router-issued agent.delegate token creates an agent task."""
        # Create pending action using agent.delegate intent in workout profile
        cmd_response = client.post(
            "/v1/command",
            json={
                "input": {"type": "text", "text": "ask agent to handle issue 42"},
                "profile": "workout",
                "client_context": {
                    "device": "simulator",
                    "locale": "en-US",
                    "timezone": "America/Los_Angeles",
                    "app_version": "0.1.0",
                },
            },
        )

        assert cmd_response.status_code == 200
        cmd_data = cmd_response.json()
        assert cmd_data["status"] == "needs_confirmation"
        assert "pending_action" in cmd_data
        token = cmd_data["pending_action"]["token"]

        # Confirm the delegation
        confirm_response = client.post(
            "/v1/commands/confirm",
            json={"token": token, "idempotency_key": "confirm-test-agent-delegate"},
        )

        assert confirm_response.status_code == 200
        data = confirm_response.json()
        
        # Agent service should be available (DB initialized in tests)
        # If not available, should get a clear error, not "(Fixture response)"
        assert "(Fixture response)" not in data["spoken_text"]
        
        # Should either succeed with task creation or fail with clear error
        if data["status"] == "ok":
            assert data["intent"]["name"] == "agent.delegate.confirmed"
            assert "task" in data["spoken_text"].lower() or "created" in data["spoken_text"].lower()
        else:
            # If it fails, should be due to service availability, not fixture mode
            assert "not available" in data["spoken_text"].lower() or "required" in data["spoken_text"].lower()

    def test_confirm_router_token_with_idempotency(self):
        """Test that idempotency works for router token confirmations."""
        # Create a pending action
        cmd_response = client.post(
            "/v1/command",
            json={
                "input": {"type": "text", "text": "request review from bob on pr 300"},
                "profile": "workout",
                "client_context": {
                    "device": "simulator",
                    "locale": "en-US",
                    "timezone": "America/Los_Angeles",
                    "app_version": "0.1.0",
                },
            },
        )

        assert cmd_response.status_code == 200
        cmd_data = cmd_response.json()
        token = cmd_data["pending_action"]["token"]
        idempotency_key = "idempotent-confirm-test"

        # First confirmation
        confirm_response1 = client.post(
            "/v1/commands/confirm",
            json={"token": token, "idempotency_key": idempotency_key},
        )

        assert confirm_response1.status_code == 200
        data1 = confirm_response1.json()

        # Second confirmation with same idempotency key should return cached response
        # even though the token is now consumed
        confirm_response2 = client.post(
            "/v1/commands/confirm",
            json={"token": "any-token", "idempotency_key": idempotency_key},
        )

        assert confirm_response2.status_code == 200
        data2 = confirm_response2.json()

        # Should return the same response
        assert data1["spoken_text"] == data2["spoken_text"]
        assert data1["intent"]["name"] == data2["intent"]["name"]

    def test_confirm_router_token_twice_fails(self):
        """Test that confirming a router token twice fails on second attempt."""
        # Create a pending action
        cmd_response = client.post(
            "/v1/command",
            json={
                "input": {"type": "text", "text": "merge pr 400"},
                "profile": "workout",
                "client_context": {
                    "device": "simulator",
                    "locale": "en-US",
                    "timezone": "America/Los_Angeles",
                    "app_version": "0.1.0",
                },
            },
        )

        assert cmd_response.status_code == 200
        cmd_data = cmd_response.json()
        token = cmd_data["pending_action"]["token"]

        # First confirmation should succeed
        confirm_response1 = client.post(
            "/v1/commands/confirm",
            json={"token": token, "idempotency_key": "first-confirm"},
        )

        assert confirm_response1.status_code == 200

        # Second confirmation with different idempotency key should fail (token consumed)
        confirm_response2 = client.post(
            "/v1/commands/confirm",
            json={"token": token, "idempotency_key": "second-confirm"},
        )

        assert confirm_response2.status_code == 404
        data2 = confirm_response2.json()
        assert "error" in data2
        assert "not_found" in data2["error"] or "expired" in data2["error"]

    def test_no_pr_005_references_in_responses(self):
        """Test that no responses contain outdated PR-005 references."""
        # Test various command types to ensure no PR-005 mentions
        test_commands = [
            "request review from alice on pr 500",
            "merge pr 501",
            "ask agent to handle issue 50",
        ]

        for text in test_commands:
            # Create pending action
            cmd_response = client.post(
                "/v1/command",
                json={
                    "input": {"type": "text", "text": text},
                    "profile": "workout",
                    "client_context": {
                        "device": "simulator",
                        "locale": "en-US",
                        "timezone": "America/Los_Angeles",
                        "app_version": "0.1.0",
                    },
                },
            )

            if cmd_response.status_code == 200:
                cmd_data = cmd_response.json()
                
                # Check command response for PR-005 references
                assert "PR-005" not in cmd_data["spoken_text"]
                
                if cmd_data["status"] == "needs_confirmation":
                    token = cmd_data["pending_action"]["token"]
                    
                    # Confirm and check confirmation response
                    confirm_response = client.post(
                        "/v1/commands/confirm",
                        json={"token": token},
                    )
                    
                    if confirm_response.status_code == 200:
                        confirm_data = confirm_response.json()
                        assert "PR-005" not in confirm_data["spoken_text"]
