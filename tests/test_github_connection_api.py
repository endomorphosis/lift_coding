"""Tests for GitHub connection API endpoints."""

import uuid

import pytest
from fastapi.testclient import TestClient

from handsfree.api import app
from handsfree.db import init_db


@pytest.fixture
def client():
    """Create test client."""
    return TestClient(app)


@pytest.fixture
def test_user_id():
    """Generate a test user ID."""
    return str(uuid.uuid4())


@pytest.fixture
def setup_db():
    """Initialize test database."""
    # The app uses a lazy-initialized in-memory DB
    # Force initialization by getting the db
    from handsfree.api import get_db

    db = get_db()
    yield db


class TestCreateGitHubConnection:
    """Test POST /v1/github/connect endpoint."""

    def test_create_connection_basic(self, client, test_user_id, setup_db):
        """Test creating a basic GitHub connection."""
        response = client.post(
            "/v1/github/connect",
            json={
                "installation_id": 12345,
                "token_ref": "secret://tokens/github/user123",
                "scopes": "repo,read:org",
            },
            headers={"X-User-Id": test_user_id},
        )

        assert response.status_code == 201
        data = response.json()
        assert data["user_id"] == test_user_id
        assert data["installation_id"] == 12345
        assert data["token_ref"] == "secret://tokens/github/user123"
        assert data["scopes"] == "repo,read:org"
        assert "id" in data
        assert "created_at" in data
        assert "updated_at" in data

    def test_create_connection_minimal(self, client, test_user_id, setup_db):
        """Test creating a connection with minimal fields."""
        response = client.post(
            "/v1/github/connect",
            json={},
            headers={"X-User-Id": test_user_id},
        )

        assert response.status_code == 201
        data = response.json()
        assert data["user_id"] == test_user_id
        assert data["installation_id"] is None
        assert data["token_ref"] is None
        assert data["scopes"] is None

    def test_create_connection_default_user(self, client, setup_db):
        """Test creating a connection with default fixture user."""
        response = client.post(
            "/v1/github/connect",
            json={"installation_id": 99999},
        )

        assert response.status_code == 201
        data = response.json()
        # Should use fixture user ID
        assert data["user_id"] == "00000000-0000-0000-0000-000000000001"
        assert data["installation_id"] == 99999

    def test_update_existing_connection(self, client, test_user_id, setup_db):
        """Test updating an existing connection."""
        # Create first connection
        response1 = client.post(
            "/v1/github/connect",
            json={"installation_id": 11111, "scopes": "repo"},
            headers={"X-User-Id": test_user_id},
        )
        assert response1.status_code == 201
        conn1 = response1.json()

        # Create second connection (should update the first)
        response2 = client.post(
            "/v1/github/connect",
            json={"installation_id": 22222, "scopes": "repo,read:org"},
            headers={"X-User-Id": test_user_id},
        )
        assert response2.status_code == 201
        conn2 = response2.json()

        # Should have same ID (updated, not created)
        assert conn2["id"] == conn1["id"]
        assert conn2["installation_id"] == 22222
        assert conn2["scopes"] == "repo,read:org"


class TestGetGitHubConnection:
    """Test GET /v1/github/connection endpoint."""

    def test_get_connection_empty(self, client, test_user_id, setup_db):
        """Test getting connection when none exists."""
        response = client.get(
            "/v1/github/connection",
            headers={"X-User-Id": test_user_id},
        )

        assert response.status_code == 200
        data = response.json()
        assert "connections" in data
        assert len(data["connections"]) == 0

    def test_get_connection_exists(self, client, test_user_id, setup_db):
        """Test getting connection after creating one."""
        # Create connection
        create_response = client.post(
            "/v1/github/connect",
            json={"installation_id": 12345, "scopes": "repo"},
            headers={"X-User-Id": test_user_id},
        )
        assert create_response.status_code == 201

        # Get connection
        get_response = client.get(
            "/v1/github/connection",
            headers={"X-User-Id": test_user_id},
        )

        assert get_response.status_code == 200
        data = get_response.json()
        assert len(data["connections"]) == 1
        conn = data["connections"][0]
        assert conn["user_id"] == test_user_id
        assert conn["installation_id"] == 12345
        assert conn["scopes"] == "repo"

    def test_get_connection_default_user(self, client, setup_db):
        """Test getting connection with default fixture user."""
        # Create connection for fixture user
        client.post(
            "/v1/github/connect",
            json={"installation_id": 99999},
        )

        # Get connection without explicit user ID
        response = client.get("/v1/github/connection")

        assert response.status_code == 200
        data = response.json()
        assert len(data["connections"]) == 1
        assert data["connections"][0]["installation_id"] == 99999

    def test_get_connection_isolation(self, client, setup_db):
        """Test that connections are isolated per user."""
        user1_id = str(uuid.uuid4())
        user2_id = str(uuid.uuid4())

        # Create connection for user 1
        client.post(
            "/v1/github/connect",
            json={"installation_id": 11111},
            headers={"X-User-Id": user1_id},
        )

        # Create connection for user 2
        client.post(
            "/v1/github/connect",
            json={"installation_id": 22222},
            headers={"X-User-Id": user2_id},
        )

        # Get connections for user 1
        response1 = client.get(
            "/v1/github/connection",
            headers={"X-User-Id": user1_id},
        )
        data1 = response1.json()
        assert len(data1["connections"]) == 1
        assert data1["connections"][0]["installation_id"] == 11111

        # Get connections for user 2
        response2 = client.get(
            "/v1/github/connection",
            headers={"X-User-Id": user2_id},
        )
        data2 = response2.json()
        assert len(data2["connections"]) == 1
        assert data2["connections"][0]["installation_id"] == 22222


class TestDeleteGitHubConnection:
    """Test DELETE /v1/github/connection/{connection_id} endpoint."""

    def test_delete_connection(self, client, test_user_id, setup_db):
        """Test deleting a connection."""
        # Create connection
        create_response = client.post(
            "/v1/github/connect",
            json={"installation_id": 12345},
            headers={"X-User-Id": test_user_id},
        )
        conn_id = create_response.json()["id"]

        # Delete connection
        delete_response = client.delete(
            f"/v1/github/connection/{conn_id}",
            headers={"X-User-Id": test_user_id},
        )
        assert delete_response.status_code == 204

        # Verify it's gone
        get_response = client.get(
            "/v1/github/connection",
            headers={"X-User-Id": test_user_id},
        )
        data = get_response.json()
        assert len(data["connections"]) == 0

    def test_delete_connection_not_found(self, client, test_user_id, setup_db):
        """Test deleting a non-existent connection."""
        fake_id = str(uuid.uuid4())
        response = client.delete(
            f"/v1/github/connection/{fake_id}",
            headers={"X-User-Id": test_user_id},
        )
        assert response.status_code == 404

    def test_delete_connection_wrong_user(self, client, setup_db):
        """Test that users cannot delete other users' connections."""
        user1_id = str(uuid.uuid4())
        user2_id = str(uuid.uuid4())

        # Create connection for user 1
        create_response = client.post(
            "/v1/github/connect",
            json={"installation_id": 12345},
            headers={"X-User-Id": user1_id},
        )
        conn_id = create_response.json()["id"]

        # Try to delete as user 2
        delete_response = client.delete(
            f"/v1/github/connection/{conn_id}",
            headers={"X-User-Id": user2_id},
        )
        assert delete_response.status_code == 404

        # Verify connection still exists for user 1
        get_response = client.get(
            "/v1/github/connection",
            headers={"X-User-Id": user1_id},
        )
        data = get_response.json()
        assert len(data["connections"]) == 1
