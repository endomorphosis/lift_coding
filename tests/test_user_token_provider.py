"""Tests for UserTokenProvider with connection metadata."""

import uuid
from datetime import UTC, datetime, timedelta
from unittest.mock import Mock

import pytest

from handsfree.db import init_db
from handsfree.db.github_connections import create_github_connection
from handsfree.github.auth import (
    EnvTokenProvider,
    FixtureTokenProvider,
    GitHubAppTokenProvider,
    UserTokenProvider,
    get_user_token_provider,
)


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
    # This is a test key generated for this purpose only (not used in production)
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


class TestUserTokenProviderNoConnection:
    """Tests for UserTokenProvider when user has no connections."""

    def test_no_connection_returns_fixture_mode(self, db_conn, test_user_id):
        """When user has no connections, should use fixture mode."""
        provider = UserTokenProvider(db_conn, test_user_id)
        token = provider.get_token()
        assert token is None

    def test_get_provider_returns_fixture_provider(self, db_conn, test_user_id):
        """When user has no connections, _get_provider returns FixtureTokenProvider."""
        provider = UserTokenProvider(db_conn, test_user_id)
        inner_provider = provider._get_provider()
        assert isinstance(inner_provider, FixtureTokenProvider)


class TestUserTokenProviderWithConnection:
    """Tests for UserTokenProvider when user has connections."""

    def test_connection_with_installation_id_and_app_config(
        self, db_conn, test_user_id, mock_http_client, valid_private_key, monkeypatch
    ):
        """When connection has installation_id and app is configured, should use GitHubApp."""
        # Create connection with installation_id
        create_github_connection(
            conn=db_conn,
            user_id=test_user_id,
            installation_id=12345,
        )

        # Set up GitHub App configuration
        monkeypatch.setenv("GITHUB_APP_ID", "app-123")
        monkeypatch.setenv("GITHUB_APP_PRIVATE_KEY_PEM", valid_private_key)

        provider = UserTokenProvider(db_conn, test_user_id, http_client=mock_http_client)
        inner_provider = provider._get_provider()
        
        assert isinstance(inner_provider, GitHubAppTokenProvider)
        
        # Should be able to get token
        token = provider.get_token()
        assert token == "ghs_mock_installation_token_abc123"

    def test_connection_with_installation_id_but_no_app_config_falls_back(
        self, db_conn, test_user_id, monkeypatch
    ):
        """When connection has installation_id but app not configured, should fall back."""
        # Create connection with installation_id
        create_github_connection(
            conn=db_conn,
            user_id=test_user_id,
            installation_id=12345,
        )

        # Clear GitHub App configuration
        monkeypatch.delenv("GITHUB_APP_ID", raising=False)
        monkeypatch.delenv("GITHUB_APP_PRIVATE_KEY_PEM", raising=False)
        
        # Set environment token as fallback
        monkeypatch.setenv("GITHUB_TOKEN", "ghp_test_token")

        provider = UserTokenProvider(db_conn, test_user_id)
        inner_provider = provider._get_provider()
        
        # Should fall back to EnvTokenProvider
        assert isinstance(inner_provider, EnvTokenProvider)
        
        token = provider.get_token()
        assert token == "ghp_test_token"

    def test_connection_without_installation_id_uses_env_token(
        self, db_conn, test_user_id, monkeypatch
    ):
        """When connection has no installation_id, should use env token."""
        # Create connection without installation_id
        create_github_connection(
            conn=db_conn,
            user_id=test_user_id,
            token_ref="secret://tokens/github/user123",
        )

        # Set environment token
        monkeypatch.setenv("GITHUB_TOKEN", "ghp_test_token")

        provider = UserTokenProvider(db_conn, test_user_id)
        inner_provider = provider._get_provider()
        
        assert isinstance(inner_provider, EnvTokenProvider)
        
        token = provider.get_token()
        assert token == "ghp_test_token"

    def test_connection_without_installation_id_and_no_env_token(
        self, db_conn, test_user_id, monkeypatch
    ):
        """When connection has no installation_id and no env token, should use fixture mode."""
        # Create connection without installation_id
        create_github_connection(
            conn=db_conn,
            user_id=test_user_id,
            token_ref="secret://tokens/github/user123",
        )

        # Clear environment token
        monkeypatch.delenv("GITHUB_TOKEN", raising=False)

        provider = UserTokenProvider(db_conn, test_user_id)
        inner_provider = provider._get_provider()
        
        assert isinstance(inner_provider, FixtureTokenProvider)
        
        token = provider.get_token()
        assert token is None


class TestUserTokenProviderMultipleConnections:
    """Tests for UserTokenProvider when user has multiple connections."""

    def test_uses_most_recent_connection(
        self, db_conn, test_user_id, mock_http_client, valid_private_key, monkeypatch
    ):
        """When user has multiple connections, should use most recent one."""
        # Create two connections (most recent has installation_id)
        create_github_connection(
            conn=db_conn,
            user_id=test_user_id,
            installation_id=11111,  # Older connection
        )
        create_github_connection(
            conn=db_conn,
            user_id=test_user_id,
            installation_id=22222,  # Newer connection
        )

        # Set up GitHub App configuration
        monkeypatch.setenv("GITHUB_APP_ID", "app-123")
        monkeypatch.setenv("GITHUB_APP_PRIVATE_KEY_PEM", valid_private_key)

        provider = UserTokenProvider(db_conn, test_user_id, http_client=mock_http_client)
        inner_provider = provider._get_provider()
        
        assert isinstance(inner_provider, GitHubAppTokenProvider)
        
        # Verify it uses the most recent installation_id (22222)
        assert inner_provider.installation_id == "22222"


class TestUserTokenProviderCaching:
    """Tests for UserTokenProvider provider caching."""

    def test_provider_is_cached(self, db_conn, test_user_id, monkeypatch):
        """Provider should be cached after first call."""
        create_github_connection(
            conn=db_conn,
            user_id=test_user_id,
        )

        monkeypatch.setenv("GITHUB_TOKEN", "ghp_test_token")

        provider = UserTokenProvider(db_conn, test_user_id)
        
        # First call should create provider
        provider1 = provider._get_provider()
        
        # Second call should return same instance
        provider2 = provider._get_provider()
        
        assert provider1 is provider2


class TestGetUserTokenProvider:
    """Tests for get_user_token_provider factory function."""

    def test_returns_user_token_provider(self, db_conn, test_user_id):
        """Should return a UserTokenProvider instance."""
        provider = get_user_token_provider(db_conn, test_user_id)
        assert isinstance(provider, UserTokenProvider)
        assert provider.user_id == test_user_id

    def test_passes_http_client(self, db_conn, test_user_id, mock_http_client):
        """Should pass http_client to UserTokenProvider."""
        provider = get_user_token_provider(db_conn, test_user_id, http_client=mock_http_client)
        assert isinstance(provider, UserTokenProvider)
        assert provider.http_client is mock_http_client
