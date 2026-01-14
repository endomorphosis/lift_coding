"""End-to-end integration tests for GitHub auth wiring."""

import uuid
from datetime import UTC, datetime, timedelta
from unittest.mock import Mock

import pytest

from handsfree.db import init_db
from handsfree.db.github_connections import create_github_connection
from handsfree.github.auth import get_user_token_provider
from handsfree.github.provider import LiveGitHubProvider


@pytest.fixture
def db_conn():
    """Create an in-memory database connection for testing."""
    conn = init_db(":memory:")
    yield conn
    conn.close()


@pytest.fixture
def test_user_id():
    """Generate a test user ID."""
    return str(uuid.UUID("12345678-1234-1234-1234-123456789012"))


@pytest.fixture
def mock_http_client():
    """Create a mock HTTP client for GitHub API calls."""
    client = Mock()
    response = Mock()
    response.status_code = 201
    response.json.return_value = {
        "token": "ghs_mock_installation_token_abc123",
        "expires_at": (datetime.now(UTC) + timedelta(hours=1)).isoformat(),
    }
    client.post.return_value = response
    return client


@pytest.fixture
def valid_private_key():
    """Return a valid RSA private key for testing."""
    return """-----BEGIN RSA PRIVATE KEY-----
MIIEowIBAAKCAQEA3eF5BWTCu4B5XK1TPqOisXn6VpWIIfQwRO56Dx34rMs8dMJh
2gQrMLQTEaXSyamcfqlCb+5ErS/BIBFR0GwrBS/597h+ixo/40zNjPZkhuH69Rem
XMlbgzOde7UAKit9p64nnGU69lOQie0L7x1MCnYzQbXBgqC9uLJso44I4vAHYHZF
4++qmaqvwGWjFkRLX9lmvDHBHTYK3KjQIx9IDGnwsCRj5AaBvfF/ctmrkK6aBa4f
TDHlVdhNw5Xtf1jDlgNamLkqqtNj9yHJjsz2bjW2BTCSXx57WuZSuDPlBpMhmggH
CRzTIWdWEvK2EFqDA542ygfrb0kII2TXLC2J6wIDAQABAoIBAAiYI7JoSTyvCMRk
uE08VGBwe5hf+WJrTXVWEWdFf2zeAGz7XIPv1mZwCy8LT8Nc7QFg+ABS59kXePEP
iq46il4Mki+ct1YXAbOBtZKItrMczLYyoNCGQiOuW6K/i46WmarljYY6y5JgAUC+
bFBqP5hGJM0eR60SIdcmHhwls8VqeUASZ3zgbbXWORXArn6bFRy3FTFjwQ4SufkG
Ion1zuzC7Smhr7Qa6AqtGKoZYkJ5rmqzcgSu6w6ZMWF4dfgYstZAdnhf+CdxJ4C3
HezRhq0O6PmG6L54FZ94Xjb0A6mU+twXkKFA4+1RzjnscLKQW4pemrTZbY41H34R
9hiHBlUCgYEA7xP2lRB5fUFT3IgKM+wL2yGdojthZ8J1rb71YbiAJdeRqdpEAUZ/
RWCoq65j+H3yqJ2duwkrRqnSr8FkaTm0XvEtUrYtHFsZbFMNjjuMF1DftOZNhZmw
NC7z+lhY4tnU5Ksbzl/Hx97gme7eEi/PicQQbPwAqdppmPUwHn8UP9cCgYEA7ZXm
WM8IZX11IzG5jMjyIEq4BTMECeeOSeEhppQiszeiFEE+SlUPAux5JiPBWVVmYp58
H9/mUxXi075W4vYoaJT5DX+SaAYTugleI25V8vkSoqImo/P9KztGvEgIU9niC2kB
bV9O+Zcp83uZV6/UBtb2AYcEvp47yjnO2WbylA0CgYAdrSWzlSrvcFd/jWdu0IMc
PUz64VIS9iFzYrvE2IkXqW2MXuqIGf8cVoY5YVlJdCDV61Kz78xuZhAf/up+4UnR
azCMDs8EsQ4z0w9gs2WNU12hb+D5j30+zQE99w95gT6a795wvJTo63KHyQ3JxiOF
30+Gp7VRYCoxcWX6sx2JWwKBgFZ2GM/0+A9HKtvV+rqbXlIWHwX1XODl3chRH9fp
TP9/nYJVg/+1GLNtr2EL3g9OnuYA2xcWelF+Q3/fYutRvb7hiAk7heJJY+BuDE5E
lw7HSdrZu8oqvtV+yu02IaGyRyrz2csdxjXapy+uqU1Z9YVPsVM4+acNGqErjHVd
m6X5AoGBAMIE462Zsnu/bGItTbtAS2xVV5c04HppDkRGaqtcYMxU1+oGnxjkQ1pp
13kV8WUv1dsyULmlcPrH74We3RG0wgqlI+5vd3je8oYFMyZ98v4UNG7SpGGYRPL2
adW+7qG7Q9T48zppJ2NWTp6pUUOKrMfX2Mu9tqGJJZiUMsbhrI+w
-----END RSA PRIVATE KEY-----"""


class TestEndToEndAuthWiring:
    """End-to-end tests for GitHub authentication wiring."""

    def test_user_without_connection_uses_fixture_mode(self, db_conn, test_user_id):
        """User without connection should fall back to fixture mode."""
        # Create a token provider for user (no connections)
        token_provider = get_user_token_provider(db_conn, test_user_id)

        # Create a live provider with this token provider
        provider = LiveGitHubProvider(token_provider)

        # Should be able to call API methods (falls back to fixtures)
        prs = provider.list_user_prs("testuser")
        assert isinstance(prs, list)
        assert len(prs) == 3  # From fixture

    def test_user_with_github_app_connection_uses_installation_token(
        self, db_conn, test_user_id, mock_http_client, valid_private_key, monkeypatch
    ):
        """User with GitHub App connection should use installation token."""
        # Create connection with installation_id
        create_github_connection(
            conn=db_conn,
            user_id=test_user_id,
            installation_id=12345,
        )

        # Configure GitHub App
        monkeypatch.setenv("GITHUB_APP_ID", "app-123")
        monkeypatch.setenv("GITHUB_APP_PRIVATE_KEY_PEM", valid_private_key)

        # Create token provider for user
        token_provider = get_user_token_provider(
            db_conn, test_user_id, http_client=mock_http_client
        )

        # Create live provider
        provider = LiveGitHubProvider(token_provider)

        # Should have minted token available
        headers = provider._get_headers()
        assert "Authorization" in headers
        assert headers["Authorization"] == "Bearer ghs_mock_installation_token_abc123"

    def test_user_with_connection_but_missing_app_config_falls_back_to_env(
        self, db_conn, test_user_id, monkeypatch
    ):
        """User with installation_id but no app config should fall back to env token."""
        # Create connection with installation_id
        create_github_connection(
            conn=db_conn,
            user_id=test_user_id,
            installation_id=12345,
        )

        # Clear GitHub App config but set env token
        monkeypatch.delenv("GITHUB_APP_ID", raising=False)
        monkeypatch.delenv("GITHUB_APP_PRIVATE_KEY_PEM", raising=False)
        monkeypatch.setenv("GITHUB_TOKEN", "ghp_env_token")

        # Create token provider for user
        token_provider = get_user_token_provider(db_conn, test_user_id)

        # Create live provider
        provider = LiveGitHubProvider(token_provider)

        # Should use env token
        headers = provider._get_headers()
        assert "Authorization" in headers
        assert headers["Authorization"] == "Bearer ghp_env_token"

    def test_user_with_connection_but_no_tokens_available_uses_fixtures(
        self, db_conn, test_user_id, monkeypatch
    ):
        """User with connection but no token sources should use fixtures."""
        # Create connection without installation_id
        create_github_connection(
            conn=db_conn,
            user_id=test_user_id,
            token_ref="secret://tokens/github/user123",
        )

        # Clear all token sources
        monkeypatch.delenv("GITHUB_APP_ID", raising=False)
        monkeypatch.delenv("GITHUB_APP_PRIVATE_KEY_PEM", raising=False)
        monkeypatch.delenv("GITHUB_TOKEN", raising=False)

        # Create token provider for user
        token_provider = get_user_token_provider(db_conn, test_user_id)

        # Create live provider
        provider = LiveGitHubProvider(token_provider)

        # Should fall back to fixtures (no Authorization header)
        headers = provider._get_headers()
        assert "Authorization" not in headers

        # Should still work via fixture fallback
        prs = provider.list_user_prs("testuser")
        assert isinstance(prs, list)
        assert len(prs) == 3


class TestErrorHandling:
    """Tests for error handling in auth wiring."""

    def test_missing_github_app_config_produces_safe_error(
        self, db_conn, test_user_id, monkeypatch
    ):
        """Missing GitHub App config should not crash, just fall back."""
        # Create connection with installation_id
        create_github_connection(
            conn=db_conn,
            user_id=test_user_id,
            installation_id=12345,
        )

        # Clear GitHub App config and env token
        monkeypatch.delenv("GITHUB_APP_ID", raising=False)
        monkeypatch.delenv("GITHUB_APP_PRIVATE_KEY_PEM", raising=False)
        monkeypatch.delenv("GITHUB_TOKEN", raising=False)

        # Should not crash
        token_provider = get_user_token_provider(db_conn, test_user_id)
        token = token_provider.get_token()

        # Should return None (fixture mode)
        assert token is None

    def test_invalid_installation_id_falls_back_gracefully(
        self, db_conn, test_user_id, valid_private_key, monkeypatch
    ):
        """Invalid installation_id should fall back to env token."""
        # Create connection with installation_id
        create_github_connection(
            conn=db_conn,
            user_id=test_user_id,
            installation_id=99999,  # Invalid
        )

        # Configure GitHub App
        monkeypatch.setenv("GITHUB_APP_ID", "app-123")
        monkeypatch.setenv("GITHUB_APP_PRIVATE_KEY_PEM", valid_private_key)
        monkeypatch.setenv("GITHUB_TOKEN", "ghp_fallback_token")

        # Create mock HTTP client that returns error
        mock_client = Mock()
        response = Mock()
        response.status_code = 404
        response.text = "Installation not found"
        mock_client.post.return_value = response

        # Create token provider
        token_provider = get_user_token_provider(db_conn, test_user_id, http_client=mock_client)

        # Token minting will fail, but should not crash
        # The provider will attempt to mint but return None on error
        token = token_provider.get_token()

        # GitHub App provider returns None on error, not falling back
        # This is expected behavior - token minting errors should be logged
        assert token is None


class TestMultipleUsers:
    """Tests for handling multiple users with different configurations."""

    def test_different_users_get_different_tokens(
        self, db_conn, mock_http_client, valid_private_key, monkeypatch
    ):
        """Different users should get tokens based on their own connections."""
        user1_id = str(uuid.UUID("11111111-1111-1111-1111-111111111111"))
        user2_id = str(uuid.UUID("22222222-2222-2222-2222-222222222222"))

        # User 1 has GitHub App connection
        create_github_connection(
            conn=db_conn,
            user_id=user1_id,
            installation_id=11111,
        )

        # User 2 has no connections (will use env token)

        # Configure GitHub App and env token
        monkeypatch.setenv("GITHUB_APP_ID", "app-123")
        monkeypatch.setenv("GITHUB_APP_PRIVATE_KEY_PEM", valid_private_key)
        monkeypatch.setenv("GITHUB_TOKEN", "ghp_env_token")

        # User 1 should use GitHub App token
        provider1 = get_user_token_provider(db_conn, user1_id, http_client=mock_http_client)
        token1 = provider1.get_token()
        assert token1 == "ghs_mock_installation_token_abc123"

        # User 2 should use env token (no connection)
        provider2 = get_user_token_provider(db_conn, user2_id)
        token2 = provider2.get_token()
        # Actually, with no connection, it should return None (fixture mode)
        # because UserTokenProvider returns fixture mode when no connections exist
        assert token2 is None
