"""Tests for voice command flow with pr.request_review action.

Tests the end-to-end flow:
1. Voice command -> intent parsing
2. Intent -> policy evaluation
3. Policy decision -> needs_confirmation or direct execution
4. Confirmation -> exactly-once execution
5. Audit logging throughout
"""

import pytest
from fastapi.testclient import TestClient

from handsfree.api import app
from handsfree.db.action_logs import get_action_logs
from handsfree.db.repo_policies import create_or_update_repo_policy


@pytest.fixture
def reset_db():
    """Reset the database connection before each test."""
    global _db_conn
    import handsfree.api as api_module

    api_module._db_conn = None
    api_module._command_router = None  # Also reset the router so it gets new db_conn
    yield
    api_module._db_conn = None
    api_module._command_router = None


client = TestClient(app)


class TestVoiceCommandParsing:
    """Test that voice commands are correctly parsed into pr.request_review intents."""

    def test_request_review_from_alice_on_pr_123(self, reset_db):
        """Test: 'request review from alice on PR 123'"""
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
        assert data["intent"]["entities"]["reviewers"] == ["alice"]
        assert data["intent"]["entities"]["pr_number"] == 123

    def test_ask_bob_to_review_pr_123(self, reset_db):
        """Test: 'ask bob to review PR 123'"""
        response = client.post(
            "/v1/command",
            json={
                "input": {"type": "text", "text": "ask bob to review PR 123"},
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
        assert data["intent"]["entities"]["reviewers"] == ["bob"]
        assert data["intent"]["entities"]["pr_number"] == 123

    def test_request_reviewers_alice_bob_for_pr_123(self, reset_db):
        """Test: 'request reviewers alice bob for PR 123'"""
        response = client.post(
            "/v1/command",
            json={
                "input": {"type": "text", "text": "request reviewers alice bob for PR 123"},
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
        assert "alice" in data["intent"]["entities"]["reviewers"]
        assert "bob" in data["intent"]["entities"]["reviewers"]
        assert data["intent"]["entities"]["pr_number"] == 123


class TestVoiceCommandPolicyIntegration:
    """Test that voice commands integrate with policy evaluation."""

    def test_default_policy_requires_confirmation(self, reset_db):
        """Test that default policy returns needs_confirmation for voice commands."""
        response = client.post(
            "/v1/command",
            json={
                "input": {"type": "text", "text": "request review from alice on PR 456"},
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
        assert data["status"] == "needs_confirmation"
        assert data["pending_action"] is not None
        assert data["pending_action"]["token"] is not None
        assert "confirm" in data["spoken_text"].lower()

    def test_allow_policy_without_confirmation(self, reset_db):
        """Test that allowed repo executes immediately without confirmation."""
        from handsfree.api import get_db

        db = get_db()

        # Create policy that allows without confirmation
        create_or_update_repo_policy(
            db,
            user_id="00000000-0000-0000-0000-000000000001",
            repo_full_name="default/repo",
            allow_request_review=True,
            require_confirmation=False,
        )

        response = client.post(
            "/v1/command",
            json={
                "input": {"type": "text", "text": "request review from bob on PR 789"},
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
        assert data["status"] == "ok"
        assert data["pending_action"] is None
        assert "review requested" in data["spoken_text"].lower()


class TestVoiceCommandConfirmation:
    """Test confirmation flow for voice commands."""

    def test_confirm_executes_action_once(self, reset_db):
        """Test that confirming a voice command executes the action exactly once."""
        from handsfree.api import get_db

        db = get_db()

        # Step 1: Issue voice command
        response = client.post(
            "/v1/command",
            json={
                "input": {"type": "text", "text": "request review from carol on PR 111"},
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
        assert data["status"] == "needs_confirmation"
        token = data["pending_action"]["token"]

        # Step 2: Confirm the action
        confirm_response = client.post(
            "/v1/commands/confirm",
            json={"token": token},
        )

        assert confirm_response.status_code == 200
        confirm_data = confirm_response.json()
        assert confirm_data["status"] == "ok"
        assert "review requested" in confirm_data["spoken_text"].lower()

        # Step 3: Check audit log shows confirmation
        logs = get_action_logs(db, action_type="request_review", limit=10)
        confirmation_logs = [log for log in logs if log.result.get("via_confirmation")]
        assert len(confirmation_logs) == 1
        assert confirmation_logs[0].ok is True
        assert confirmation_logs[0].target == "default/repo#111"

    def test_confirm_via_voice_followup_command(self, reset_db):
        """Test that saying 'confirm' via /v1/command executes the latest pending action."""
        from handsfree.api import get_db

        db = get_db()

        # Step 1: Create a pending action
        response = client.post(
            "/v1/command",
            json={
                "input": {"type": "text", "text": "request review from frank on PR 444"},
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
        assert data["status"] == "needs_confirmation"
        token = data["pending_action"]["token"]

        # Step 2: Follow up with a global voice command "confirm"
        confirm_via_command = client.post(
            "/v1/command",
            json={
                "input": {"type": "text", "text": "confirm"},
                "profile": "default",
                "client_context": {
                    "device": "test",
                    "locale": "en-US",
                    "timezone": "America/Los_Angeles",
                    "app_version": "0.1.0",
                },
            },
        )

        assert confirm_via_command.status_code == 200
        confirm_data = confirm_via_command.json()
        assert confirm_data["status"] == "ok"
        assert "review requested" in confirm_data["spoken_text"].lower()

        # Step 3: Ensure token was consumed (cannot confirm again)
        retry = client.post("/v1/commands/confirm", json={"token": token})
        assert retry.status_code == 404

        # Step 4: Ensure audit logs show exactly one confirmation execution
        logs = get_action_logs(db, action_type="request_review", limit=10)
        confirmation_logs = [log for log in logs if log.result.get("via_confirmation")]
        assert len(confirmation_logs) == 1

    def test_cancel_via_voice_followup_command(self, reset_db):
        """Test that saying 'cancel' via /v1/command cancels the latest pending action."""
        # Step 1: Create a pending action
        response = client.post(
            "/v1/command",
            json={
                "input": {"type": "text", "text": "request review from grace on PR 555"},
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
        assert data["status"] == "needs_confirmation"
        token = data["pending_action"]["token"]

        # Step 2: Follow up with "cancel"
        cancel_via_command = client.post(
            "/v1/command",
            json={
                "input": {"type": "text", "text": "cancel"},
                "profile": "default",
                "client_context": {
                    "device": "test",
                    "locale": "en-US",
                    "timezone": "America/Los_Angeles",
                    "app_version": "0.1.0",
                },
            },
        )

        assert cancel_via_command.status_code == 200
        cancel_data = cancel_via_command.json()
        assert cancel_data["status"] == "ok"
        assert cancel_data["intent"]["name"] == "system.cancel"

        # Step 3: Original token should no longer be confirmable
        confirm_after_cancel = client.post("/v1/commands/confirm", json={"token": token})
        assert confirm_after_cancel.status_code == 404

    def test_retry_confirmation_fails(self, reset_db):
        """Test that retrying confirmation returns 404 and doesn't duplicate execution."""
        from handsfree.api import get_db

        db = get_db()

        # Step 1: Issue voice command
        response = client.post(
            "/v1/command",
            json={
                "input": {"type": "text", "text": "request review from dave on PR 222"},
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
        token = data["pending_action"]["token"]

        # Step 2: Confirm once
        confirm_response = client.post(
            "/v1/commands/confirm",
            json={"token": token},
        )
        assert confirm_response.status_code == 200

        # Count audit logs after first confirmation
        logs_after_first = get_action_logs(db, action_type="request_review", limit=10)
        confirmation_logs_first = [
            log for log in logs_after_first if log.result.get("via_confirmation")
        ]
        assert len(confirmation_logs_first) == 1

        # Step 3: Try to confirm again (should fail)
        retry_response = client.post(
            "/v1/commands/confirm",
            json={"token": token},
        )

        assert retry_response.status_code == 404
        error_data = retry_response.json()
        assert error_data["error"] == "not_found"

        # Verify no duplicate audit logs
        logs_after_retry = get_action_logs(db, action_type="request_review", limit=10)
        confirmation_logs_retry = [
            log for log in logs_after_retry if log.result.get("via_confirmation")
        ]
        assert len(confirmation_logs_retry) == 1  # Still only one


class TestVoiceCommandAuditLogging:
    """Test audit logging for voice command flows."""

    def test_audit_log_for_needs_confirmation(self, reset_db):
        """Test that audit log is created when confirmation is required."""
        from handsfree.api import get_db

        db = get_db()

        response = client.post(
            "/v1/command",
            json={
                "input": {"type": "text", "text": "request review from eve on PR 333"},
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
        assert data["status"] == "needs_confirmation"

        # Check audit log
        logs = get_action_logs(db, action_type="request_review", limit=10)
        recent_log = logs[0]
        assert recent_log.ok is True  # Request was valid
        assert recent_log.result.get("status") == "needs_confirmation"
        assert recent_log.target == "default/repo#333"

    def test_audit_log_for_direct_execution(self, reset_db):
        """Test that audit log is created for direct execution without confirmation."""
        from handsfree.api import get_db

        db = get_db()

        # Create policy that allows without confirmation
        create_or_update_repo_policy(
            db,
            user_id="00000000-0000-0000-0000-000000000001",
            repo_full_name="default/repo",
            allow_request_review=True,
            require_confirmation=False,
        )

        response = client.post(
            "/v1/command",
            json={
                "input": {"type": "text", "text": "request review from frank on PR 444"},
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
        assert data["status"] == "ok"

        # Check audit log
        logs = get_action_logs(db, action_type="request_review", limit=10)
        recent_log = logs[0]
        assert recent_log.ok is True
        assert recent_log.result.get("status") == "success"
        assert recent_log.target == "default/repo#444"

    def test_audit_log_for_confirmation_execution(self, reset_db):
        """Test that audit log is created when confirmation is executed."""
        from handsfree.api import get_db

        db = get_db()

        # Step 1: Issue voice command
        response = client.post(
            "/v1/command",
            json={
                "input": {"type": "text", "text": "request review from grace on PR 555"},
                "profile": "default",
                "client_context": {
                    "device": "test",
                    "locale": "en-US",
                    "timezone": "America/Los_Angeles",
                    "app_version": "0.1.0",
                },
            },
        )

        token = response.json()["pending_action"]["token"]

        # Step 2: Confirm
        client.post(
            "/v1/commands/confirm",
            json={"token": token},
        )

        # Check audit logs
        logs = get_action_logs(db, action_type="request_review", limit=10)

        # Should have 2 logs: one for needs_confirmation, one for execution
        needs_conf_logs = [log for log in logs if log.result.get("status") == "needs_confirmation"]
        exec_logs = [log for log in logs if log.result.get("via_confirmation")]

        assert len(needs_conf_logs) >= 1
        assert len(exec_logs) == 1
        assert exec_logs[0].ok is True
        assert exec_logs[0].target == "default/repo#555"


class TestVoiceCommandEdgeCases:
    """Test edge cases and error handling."""

    def test_voice_command_without_pr_number(self, reset_db):
        """Test that voice command without PR number returns an error."""
        response = client.post(
            "/v1/command",
            json={
                "input": {"type": "text", "text": "request review from alice"},
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
        assert data["status"] == "error"
        assert "pr number" in data["spoken_text"].lower()

    def test_voice_command_with_multiple_reviewers(self, reset_db):
        """Test voice command with multiple reviewers (space-separated)."""
        response = client.post(
            "/v1/command",
            json={
                "input": {"type": "text", "text": "request reviewers alice bob charlie for PR 666"},
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
        reviewers = data["intent"]["entities"]["reviewers"]
        assert len(reviewers) == 3
        assert "alice" in reviewers
        assert "bob" in reviewers
        assert "charlie" in reviewers

    def test_voice_command_idempotency(self, reset_db):
        """Test that voice commands support idempotency."""
        idempotency_key = "test-voice-idempotency-123"

        # First request
        response1 = client.post(
            "/v1/command",
            json={
                "input": {"type": "text", "text": "request review from alice on PR 777"},
                "profile": "default",
                "client_context": {
                    "device": "test",
                    "locale": "en-US",
                    "timezone": "America/Los_Angeles",
                    "app_version": "0.1.0",
                },
                "idempotency_key": idempotency_key,
            },
        )

        data1 = response1.json()
        token1 = data1["pending_action"]["token"]

        # Second request with same key
        response2 = client.post(
            "/v1/command",
            json={
                "input": {"type": "text", "text": "request review from alice on PR 777"},
                "profile": "default",
                "client_context": {
                    "device": "test",
                    "locale": "en-US",
                    "timezone": "America/Los_Angeles",
                    "app_version": "0.1.0",
                },
                "idempotency_key": idempotency_key,
            },
        )

        data2 = response2.json()
        token2 = data2["pending_action"]["token"]

        # Should return the same token
        assert token1 == token2
        assert data1 == data2
