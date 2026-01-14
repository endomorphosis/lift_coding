"""Integration tests for JWT authentication mode with API endpoints."""

import os
import uuid
from datetime import UTC, datetime, timedelta
from unittest.mock import patch

import jwt
import pytest
from fastapi.testclient import TestClient

from handsfree.api import app

client = TestClient(app)


@pytest.fixture
def jwt_secret():
    """JWT secret for testing."""
    return "test-jwt-secret-for-integration"


@pytest.fixture
def test_user_id():
    """Test user ID."""
    return str(uuid.uuid4())


def create_jwt_token(user_id: str, secret: str, expired: bool = False) -> str:
    """Create a test JWT token."""
    payload = {
        "user_id": user_id,
        "iat": datetime.now(UTC),
        "exp": datetime.now(UTC) + timedelta(hours=-1 if expired else 1),
    }
    return jwt.encode(payload, secret, algorithm="HS256")


class TestDevModeAuthentication:
    """Test that dev mode (default) works as before."""

    def test_command_without_auth_uses_fixture(self):
        """Test command endpoint without auth in dev mode."""
        with patch.dict(os.environ, {"HANDSFREE_AUTH_MODE": "dev"}):
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

    def test_command_with_header_in_dev_mode(self, test_user_id):
        """Test command endpoint with X-User-Id header in dev mode."""
        with patch.dict(os.environ, {"HANDSFREE_AUTH_MODE": "dev"}):
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

    def test_github_connection_without_auth_in_dev_mode(self):
        """Test GitHub connection creation without auth in dev mode."""
        with patch.dict(os.environ, {"HANDSFREE_AUTH_MODE": "dev"}):
            response = client.post(
                "/v1/github/connections",
                json={"installation_id": 12345},
            )
            assert response.status_code == 201
            data = response.json()
            # Should use fixture user ID in dev mode
            assert data["user_id"] == "00000000-0000-0000-0000-000000000001"


class TestJWTModeAuthentication:
    """Test JWT authentication mode."""

    def test_command_requires_token_in_jwt_mode(self, jwt_secret):
        """Test that command endpoint requires token in JWT mode."""
        with patch.dict(
            os.environ, {"HANDSFREE_AUTH_MODE": "jwt", "JWT_SECRET_KEY": jwt_secret}
        ):
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
            assert response.status_code == 401
            data = response.json()
            # Check for either FastAPI error format or our custom format
            assert (
                "authentication required" in str(data).lower()
                or "error" in data
            )

    def test_command_with_valid_token_in_jwt_mode(self, jwt_secret, test_user_id):
        """Test command endpoint with valid JWT token."""
        with patch.dict(
            os.environ, {"HANDSFREE_AUTH_MODE": "jwt", "JWT_SECRET_KEY": jwt_secret}
        ):
            token = create_jwt_token(test_user_id, jwt_secret)
            response = client.post(
                "/v1/command",
                headers={"Authorization": f"Bearer {token}"},
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

    def test_command_with_expired_token(self, jwt_secret, test_user_id):
        """Test that expired tokens are rejected."""
        with patch.dict(
            os.environ, {"HANDSFREE_AUTH_MODE": "jwt", "JWT_SECRET_KEY": jwt_secret}
        ):
            token = create_jwt_token(test_user_id, jwt_secret, expired=True)
            response = client.post(
                "/v1/command",
                headers={"Authorization": f"Bearer {token}"},
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
            assert response.status_code == 401
            data = response.json()
            # Check for expired token message
            assert "expired" in str(data).lower() or "error" in data

    def test_command_with_invalid_token(self, jwt_secret):
        """Test that invalid tokens are rejected."""
        with patch.dict(
            os.environ, {"HANDSFREE_AUTH_MODE": "jwt", "JWT_SECRET_KEY": jwt_secret}
        ):
            response = client.post(
                "/v1/command",
                headers={"Authorization": "Bearer invalid-token"},
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
            assert response.status_code == 401

    def test_jwt_mode_ignores_x_user_id_header(self, jwt_secret, test_user_id):
        """Test that JWT mode ignores X-User-Id header."""
        with patch.dict(
            os.environ, {"HANDSFREE_AUTH_MODE": "jwt", "JWT_SECRET_KEY": jwt_secret}
        ):
            # Even with X-User-Id header, should require JWT token
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
            assert response.status_code == 401

    def test_github_connection_requires_token_in_jwt_mode(self, jwt_secret):
        """Test GitHub connection creation requires token in JWT mode."""
        with patch.dict(
            os.environ, {"HANDSFREE_AUTH_MODE": "jwt", "JWT_SECRET_KEY": jwt_secret}
        ):
            response = client.post(
                "/v1/github/connections",
                json={"installation_id": 12345},
            )
            assert response.status_code == 401

    def test_github_connection_with_valid_token(self, jwt_secret, test_user_id):
        """Test GitHub connection creation with valid JWT token."""
        with patch.dict(
            os.environ, {"HANDSFREE_AUTH_MODE": "jwt", "JWT_SECRET_KEY": jwt_secret}
        ):
            token = create_jwt_token(test_user_id, jwt_secret)
            response = client.post(
                "/v1/github/connections",
                headers={"Authorization": f"Bearer {token}"},
                json={"installation_id": 12345},
            )
            assert response.status_code == 201
            data = response.json()
            # Should use user_id from JWT token
            assert data["user_id"] == test_user_id

    def test_list_connections_requires_token(self, jwt_secret):
        """Test listing connections requires token in JWT mode."""
        with patch.dict(
            os.environ, {"HANDSFREE_AUTH_MODE": "jwt", "JWT_SECRET_KEY": jwt_secret}
        ):
            response = client.get("/v1/github/connections")
            assert response.status_code == 401

    def test_list_connections_with_valid_token(self, jwt_secret, test_user_id):
        """Test listing connections with valid JWT token."""
        with patch.dict(
            os.environ, {"HANDSFREE_AUTH_MODE": "jwt", "JWT_SECRET_KEY": jwt_secret}
        ):
            token = create_jwt_token(test_user_id, jwt_secret)
            response = client.get(
                "/v1/github/connections",
                headers={"Authorization": f"Bearer {token}"},
            )
            assert response.status_code == 200

    def test_request_review_requires_token(self, jwt_secret):
        """Test request review action requires token in JWT mode."""
        with patch.dict(
            os.environ, {"HANDSFREE_AUTH_MODE": "jwt", "JWT_SECRET_KEY": jwt_secret}
        ):
            response = client.post(
                "/v1/actions/request-review",
                json={
                    "repo": "test/repo",
                    "pr_number": 123,
                    "reviewers": ["alice"],
                    "idempotency_key": "test-key",
                },
            )
            assert response.status_code == 401

    def test_request_review_with_valid_token(self, jwt_secret, test_user_id):
        """Test request review action with valid JWT token."""
        with patch.dict(
            os.environ, {"HANDSFREE_AUTH_MODE": "jwt", "JWT_SECRET_KEY": jwt_secret}
        ):
            token = create_jwt_token(test_user_id, jwt_secret)
            response = client.post(
                "/v1/actions/request-review",
                headers={"Authorization": f"Bearer {token}"},
                json={
                    "repo": "test/repo",
                    "pr_number": 123,
                    "reviewers": ["alice"],
                    "idempotency_key": "test-key",
                },
            )
            # Should either succeed or require confirmation, but not fail auth
            assert response.status_code in [200, 403]


class TestJWTModeUserIsolation:
    """Test that JWT mode properly isolates users."""

    def test_different_users_have_different_connections(self, jwt_secret):
        """Test that different JWT users see different connections."""
        user1_id = str(uuid.uuid4())
        user2_id = str(uuid.uuid4())

        with patch.dict(
            os.environ, {"HANDSFREE_AUTH_MODE": "jwt", "JWT_SECRET_KEY": jwt_secret}
        ):
            # User 1 creates a connection
            token1 = create_jwt_token(user1_id, jwt_secret)
            create_response = client.post(
                "/v1/github/connections",
                headers={"Authorization": f"Bearer {token1}"},
                json={"installation_id": 11111},
            )
            assert create_response.status_code == 201

            # User 2 lists connections (should not see user 1's connection)
            token2 = create_jwt_token(user2_id, jwt_secret)
            list_response = client.get(
                "/v1/github/connections",
                headers={"Authorization": f"Bearer {token2}"},
            )
            assert list_response.status_code == 200
            data = list_response.json()
            # User 2 should have no connections
            assert len(data["connections"]) == 0

            # User 1 lists connections (should see their connection)
            list_response1 = client.get(
                "/v1/github/connections",
                headers={"Authorization": f"Bearer {token1}"},
            )
            assert list_response1.status_code == 200
            data1 = list_response1.json()
            # User 1 should have at least 1 connection
            assert len(data1["connections"]) >= 1
