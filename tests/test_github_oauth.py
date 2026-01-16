"""Tests for GitHub OAuth flow endpoints."""

from unittest.mock import Mock, patch

import pytest
from fastapi.testclient import TestClient

from handsfree.api import app


@pytest.fixture
def client():
    """Create a test client."""
    return TestClient(app)


@pytest.fixture
def mock_oauth_env(monkeypatch):
    """Mock OAuth environment variables."""
    monkeypatch.setenv("GITHUB_OAUTH_CLIENT_ID", "test_client_id")
    monkeypatch.setenv("GITHUB_OAUTH_CLIENT_SECRET", "test_client_secret")
    monkeypatch.setenv("GITHUB_OAUTH_REDIRECT_URI", "http://localhost:8080/v1/github/oauth/callback")
    monkeypatch.setenv("GITHUB_OAUTH_SCOPES", "repo,user:email")


@pytest.fixture
def auth_headers():
    """Create authentication headers for dev mode."""
    return {"X-User-ID": "test-user-123"}


class TestGitHubOAuthStart:
    """Test GitHub OAuth start endpoint."""

    def test_oauth_start_success(self, client, mock_oauth_env, auth_headers):
        """Test successful OAuth start request."""
        response = client.get(
            "/v1/github/oauth/start",
            headers=auth_headers,
        )

        assert response.status_code == 200
        data = response.json()

        assert "authorize_url" in data
        assert "https://github.com/login/oauth/authorize" in data["authorize_url"]
        assert "client_id=test_client_id" in data["authorize_url"]
        redirect_uri_encoded = (
            "redirect_uri=http%3A%2F%2Flocalhost%3A8080%2Fv1%2Fgithub%2Foauth%2Fcallback"
        )
        assert redirect_uri_encoded in data["authorize_url"]
        assert "scope=repo%2Cuser%3Aemail" in data["authorize_url"]

    def test_oauth_start_custom_scopes(self, client, mock_oauth_env, auth_headers):
        """Test OAuth start with custom scopes."""
        response = client.get(
            "/v1/github/oauth/start?scopes=repo,admin:org",
            headers=auth_headers,
        )

        assert response.status_code == 200
        data = response.json()

        assert "authorize_url" in data
        assert "scope=repo%2Cadmin%3Aorg" in data["authorize_url"]

    def test_oauth_start_missing_config(self, client, auth_headers, monkeypatch):
        """Test OAuth start with missing configuration."""
        # Clear OAuth env vars
        monkeypatch.delenv("GITHUB_OAUTH_CLIENT_ID", raising=False)
        monkeypatch.delenv("GITHUB_OAUTH_CLIENT_SECRET", raising=False)
        monkeypatch.delenv("GITHUB_OAUTH_REDIRECT_URI", raising=False)

        response = client.get(
            "/v1/github/oauth/start",
            headers=auth_headers,
        )

        assert response.status_code == 500
        data = response.json()
        assert data["error"] == "oauth_not_configured"


class TestGitHubOAuthCallback:
    """Test GitHub OAuth callback endpoint."""

    @patch("httpx.post")
    @patch("handsfree.api.get_default_secret_manager")
    def test_oauth_callback_success(
        self,
        mock_secret_manager,
        mock_httpx_post,
        client,
        mock_oauth_env,
        auth_headers,
    ):
        """Test successful OAuth callback."""
        # Mock GitHub OAuth token exchange response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "access_token": "gho_test_token_123",
            "token_type": "bearer",
            "scope": "repo,user:email",
        }
        mock_httpx_post.return_value = mock_response

        # Mock secret manager
        mock_sm = Mock()
        mock_sm.store_secret.return_value = "secret_ref_123"
        mock_secret_manager.return_value = mock_sm

        response = client.get(
            "/v1/github/oauth/callback?code=test_auth_code",
            headers=auth_headers,
        )

        assert response.status_code == 200
        data = response.json()

        assert "connection_id" in data
        assert data["scopes"] == "repo,user:email"

        # Verify token exchange was called correctly
        mock_httpx_post.assert_called_once()
        call_args = mock_httpx_post.call_args
        assert call_args[0][0] == "https://github.com/login/oauth/access_token"
        assert call_args[1]["data"]["code"] == "test_auth_code"
        assert call_args[1]["data"]["client_id"] == "test_client_id"
        assert call_args[1]["data"]["client_secret"] == "test_client_secret"

        # Verify secret was stored
        mock_sm.store_secret.assert_called_once()
        store_call = mock_sm.store_secret.call_args
        assert store_call[1]["value"] == "gho_test_token_123"
        assert "oauth" in store_call[1]["metadata"]["source"]

    def test_oauth_callback_missing_code(self, client, mock_oauth_env, auth_headers):
        """Test OAuth callback with missing code."""
        response = client.get(
            "/v1/github/oauth/callback",
            headers=auth_headers,
        )

        assert response.status_code == 400
        data = response.json()
        assert data["error"] == "missing_code"

    @patch("httpx.post")
    def test_oauth_callback_github_error(
        self,
        mock_httpx_post,
        client,
        mock_oauth_env,
        auth_headers,
    ):
        """Test OAuth callback when GitHub returns an error."""
        # Mock GitHub OAuth error response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "error": "bad_verification_code",
            "error_description": "The code passed is incorrect or expired.",
        }
        mock_httpx_post.return_value = mock_response

        response = client.get(
            "/v1/github/oauth/callback?code=invalid_code",
            headers=auth_headers,
        )

        assert response.status_code == 400
        data = response.json()
        assert data["error"] == "oauth_error"
        assert "expired" in data["message"].lower() or "incorrect" in data["message"].lower()

    @patch("httpx.post")
    def test_oauth_callback_http_error(
        self,
        mock_httpx_post,
        client,
        mock_oauth_env,
        auth_headers,
    ):
        """Test OAuth callback with HTTP error."""
        # Mock HTTP error
        mock_response = Mock()
        mock_response.status_code = 500
        mock_httpx_post.return_value = mock_response

        response = client.get(
            "/v1/github/oauth/callback?code=test_code",
            headers=auth_headers,
        )

        assert response.status_code == 500
        data = response.json()
        assert data["error"] == "token_exchange_failed"

    @patch("httpx.post")
    @patch("handsfree.api.get_default_secret_manager")
    def test_oauth_callback_storage_failure(
        self,
        mock_secret_manager,
        mock_httpx_post,
        client,
        mock_oauth_env,
        auth_headers,
    ):
        """Test OAuth callback when secret storage fails."""
        # Mock successful GitHub response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "access_token": "gho_test_token_123",
            "token_type": "bearer",
            "scope": "repo",
        }
        mock_httpx_post.return_value = mock_response

        # Mock secret manager that raises an error
        mock_sm = Mock()
        mock_sm.store_secret.side_effect = Exception("Storage backend unavailable")
        mock_secret_manager.return_value = mock_sm

        response = client.get(
            "/v1/github/oauth/callback?code=test_code",
            headers=auth_headers,
        )

        assert response.status_code == 500
        data = response.json()
        assert data["error"] == "storage_error"

    def test_oauth_callback_missing_config(self, client, auth_headers, monkeypatch):
        """Test OAuth callback with missing configuration."""
        # Clear OAuth env vars
        monkeypatch.delenv("GITHUB_OAUTH_CLIENT_ID", raising=False)
        monkeypatch.delenv("GITHUB_OAUTH_CLIENT_SECRET", raising=False)
        monkeypatch.delenv("GITHUB_OAUTH_REDIRECT_URI", raising=False)

        response = client.get(
            "/v1/github/oauth/callback?code=test_code",
            headers=auth_headers,
        )

        assert response.status_code == 500
        data = response.json()
        assert data["error"] == "oauth_not_configured"


class TestOAuthIntegration:
    """Integration tests for OAuth flow."""

    @patch("httpx.post")
    @patch("handsfree.api.get_default_secret_manager")
    def test_full_oauth_flow(
        self,
        mock_secret_manager,
        mock_httpx_post,
        client,
        mock_oauth_env,
        auth_headers,
    ):
        """Test complete OAuth flow from start to callback."""
        # Step 1: Get authorization URL
        start_response = client.get(
            "/v1/github/oauth/start",
            headers=auth_headers,
        )
        assert start_response.status_code == 200
        authorize_url = start_response.json()["authorize_url"]
        assert "github.com/login/oauth/authorize" in authorize_url

        # Step 2: Mock GitHub token exchange
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "access_token": "gho_integration_token",
            "token_type": "bearer",
            "scope": "repo,user:email",
        }
        mock_httpx_post.return_value = mock_response

        # Mock secret manager
        mock_sm = Mock()
        mock_sm.store_secret.return_value = "secret_ref_integration"
        mock_secret_manager.return_value = mock_sm

        # Step 3: Complete callback
        callback_response = client.get(
            "/v1/github/oauth/callback?code=integration_code",
            headers=auth_headers,
        )
        assert callback_response.status_code == 200
        callback_data = callback_response.json()

        assert "connection_id" in callback_data
        assert callback_data["scopes"] == "repo,user:email"

        # Step 4: Verify connection was created and can be retrieved
        connection_id = callback_data["connection_id"]
        get_response = client.get(
            f"/v1/github/connections/{connection_id}",
            headers=auth_headers,
        )
        assert get_response.status_code == 200
        connection_data = get_response.json()
        assert connection_data["id"] == connection_id
        assert connection_data["scopes"] == "repo,user:email"
        assert connection_data["token_ref"] == "secret_ref_integration"
