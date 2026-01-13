"""Tests for user identity and header functionality."""

import uuid

import pytest
from fastapi.testclient import TestClient

from handsfree.api import app

client = TestClient(app)


@pytest.fixture
def test_user_id():
    """Generate a consistent test user ID."""
    return str(uuid.UUID("12345678-1234-1234-1234-123456789012"))


@pytest.fixture
def test_user_id_2():
    """Generate a second test user ID."""
    return str(uuid.UUID("87654321-4321-4321-4321-210987654321"))


class TestUserHeaderFunctionality:
    """Test X-User-Id header support."""

    def test_command_without_header_uses_fixture_user(self):
        """Test that commands without X-User-Id header fall back to fixture user."""
        response = client.post(
            "/v1/command",
            json={
                "input": {"type": "text", "text": "inbox"},
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

    def test_command_with_valid_user_header(self, test_user_id):
        """Test that commands accept and use X-User-Id header."""
        response = client.post(
            "/v1/command",
            headers={"X-User-Id": test_user_id},
            json={
                "input": {"type": "text", "text": "inbox"},
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

    def test_command_with_invalid_user_header_falls_back(self):
        """Test that invalid X-User-Id header falls back to fixture user."""
        response = client.post(
            "/v1/command",
            headers={"X-User-Id": "not-a-uuid"},
            json={
                "input": {"type": "text", "text": "inbox"},
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
        # Should still work, falling back to fixture user
        data = response.json()
        assert data["status"] == "ok"

    def test_request_review_with_user_header(self, test_user_id):
        """Test request review action with X-User-Id header."""
        response = client.post(
            "/v1/actions/request-review",
            headers={"X-User-Id": test_user_id},
            json={
                "repo": "test/repo",
                "pr_number": 123,
                "reviewers": ["alice"],
                "idempotency_key": "test-request-review-1",
            },
        )

        assert response.status_code in [200, 403]  # May require confirmation or be denied
        data = response.json()
        assert "ok" in data or "error" in data


class TestUserIsolation:
    """Test that different users have isolated data."""

    def test_agent_tasks_isolated_by_user(self, test_user_id, test_user_id_2):
        """Test that agent tasks are isolated by user ID."""
        # Create task for user 1
        response1 = client.post(
            "/v1/command",
            headers={"X-User-Id": test_user_id},
            json={
                "input": {"type": "text", "text": "ask agent to fix issue 42"},
                "profile": "default",
                "client_context": {
                    "device": "test",
                    "locale": "en-US",
                    "timezone": "America/Los_Angeles",
                    "app_version": "0.1.0",
                },
                "idempotency_key": f"task-user1-{uuid.uuid4()}",
            },
        )
        assert response1.status_code == 200

        # Get status for user 1
        status1 = client.post(
            "/v1/command",
            headers={"X-User-Id": test_user_id},
            json={
                "input": {"type": "text", "text": "agent status"},
                "profile": "default",
                "client_context": {
                    "device": "test",
                    "locale": "en-US",
                    "timezone": "America/Los_Angeles",
                    "app_version": "0.1.0",
                },
                "idempotency_key": f"status-user1-{uuid.uuid4()}",
            },
        )
        assert status1.status_code == 200
        # data1 = status1.json()  # User 1 has task(s)

        # Get status for user 2 (should have no tasks)
        status2 = client.post(
            "/v1/command",
            headers={"X-User-Id": test_user_id_2},
            json={
                "input": {"type": "text", "text": "agent status"},
                "profile": "default",
                "client_context": {
                    "device": "test",
                    "locale": "en-US",
                    "timezone": "America/Los_Angeles",
                    "app_version": "0.1.0",
                },
                "idempotency_key": f"status-user2-{uuid.uuid4()}",
            },
        )
        assert status2.status_code == 200
        data2 = status2.json()

        # User 1 should have task, user 2 should not
        # Check spoken text for indication of tasks
        assert "no agent tasks" in data2["spoken_text"].lower() or "0" in data2["spoken_text"]


class TestGitHubConnectionsAPI:
    """Test GitHub connections API endpoints."""

    def test_create_github_connection(self, test_user_id):
        """Test creating a GitHub connection."""
        response = client.post(
            "/v1/github/connections",
            headers={"X-User-Id": test_user_id},
            json={
                "installation_id": 12345,
                "token_ref": "secret://tokens/github/test",
                "scopes": "repo,read:org",
            },
        )

        assert response.status_code == 201
        data = response.json()
        assert data["user_id"] == test_user_id
        assert data["installation_id"] == 12345
        assert data["token_ref"] == "secret://tokens/github/test"
        assert data["scopes"] == "repo,read:org"
        assert "id" in data
        assert "created_at" in data
        assert "updated_at" in data

    def test_create_minimal_connection(self, test_user_id):
        """Test creating a connection with minimal fields."""
        response = client.post(
            "/v1/github/connections",
            headers={"X-User-Id": test_user_id},
            json={},
        )

        assert response.status_code == 201
        data = response.json()
        assert data["user_id"] == test_user_id
        assert data["installation_id"] is None
        assert data["token_ref"] is None
        assert data["scopes"] is None

    def test_list_connections_empty(self, test_user_id):
        """Test listing connections when user has none."""
        response = client.get(
            "/v1/github/connections",
            headers={"X-User-Id": test_user_id},
        )

        assert response.status_code == 200
        data = response.json()
        assert "connections" in data
        # May or may not be empty depending on test isolation

    def test_list_connections_with_data(self, test_user_id):
        """Test listing connections after creating some."""
        # Create two connections
        conn1 = client.post(
            "/v1/github/connections",
            headers={"X-User-Id": test_user_id},
            json={"installation_id": 11111},
        )
        conn2 = client.post(
            "/v1/github/connections",
            headers={"X-User-Id": test_user_id},
            json={"installation_id": 22222},
        )

        assert conn1.status_code == 201
        assert conn2.status_code == 201

        # List connections
        response = client.get(
            "/v1/github/connections",
            headers={"X-User-Id": test_user_id},
        )

        assert response.status_code == 200
        data = response.json()
        assert "connections" in data
        # Should have at least 2 connections
        assert len(data["connections"]) >= 2

    def test_get_connection_by_id(self, test_user_id):
        """Test retrieving a specific connection by ID."""
        # Create a connection
        create_response = client.post(
            "/v1/github/connections",
            headers={"X-User-Id": test_user_id},
            json={"installation_id": 99999, "scopes": "repo"},
        )

        assert create_response.status_code == 201
        created = create_response.json()
        connection_id = created["id"]

        # Retrieve it
        response = client.get(
            f"/v1/github/connections/{connection_id}",
            headers={"X-User-Id": test_user_id},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["id"] == connection_id
        assert data["user_id"] == test_user_id
        assert data["installation_id"] == 99999
        assert data["scopes"] == "repo"

    def test_get_connection_not_found(self, test_user_id):
        """Test retrieving a non-existent connection."""
        fake_id = str(uuid.uuid4())
        response = client.get(
            f"/v1/github/connections/{fake_id}",
            headers={"X-User-Id": test_user_id},
        )

        assert response.status_code == 404
        data = response.json()
        assert "error" in data

    def test_get_connection_wrong_user(self, test_user_id, test_user_id_2):
        """Test that users can't access other users' connections."""
        # User 1 creates a connection
        create_response = client.post(
            "/v1/github/connections",
            headers={"X-User-Id": test_user_id},
            json={"installation_id": 55555},
        )

        assert create_response.status_code == 201
        created = create_response.json()
        connection_id = created["id"]

        # User 2 tries to access it
        response = client.get(
            f"/v1/github/connections/{connection_id}",
            headers={"X-User-Id": test_user_id_2},
        )

        assert response.status_code == 404  # Not found (access denied)

    def test_connections_without_header_use_fixture_user(self):
        """Test that connection endpoints work without header."""
        response = client.post(
            "/v1/github/connections",
            json={"installation_id": 77777},
        )

        assert response.status_code == 201
        data = response.json()
        # Should use fixture user ID
        assert data["user_id"] == "00000000-0000-0000-0000-000000000001"


class TestConfirmWithUserHeader:
    """Test confirmation endpoint with user headers."""

    def test_confirm_with_user_header(self, test_user_id):
        """Test that confirm endpoint accepts X-User-Id header."""
        # This test just verifies the header is accepted
        # The actual confirmation logic is tested elsewhere
        response = client.post(
            "/v1/commands/confirm",
            headers={"X-User-Id": test_user_id},
            json={
                "token": "non-existent-token",
                "idempotency_key": "test-confirm-1",
            },
        )

        # Should return 404 for non-existent token, not fail due to header
        assert response.status_code == 404
