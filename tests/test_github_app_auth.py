"""Tests for GitHub App authentication and token minting."""

from datetime import UTC, datetime, timedelta
from unittest.mock import Mock

import pytest

from handsfree.github.auth import (
    EnvTokenProvider,
    FixtureTokenProvider,
    GitHubAppTokenProvider,
    get_token_provider,
)


class TestFixtureTokenProvider:
    """Tests for FixtureTokenProvider."""

    def test_get_token_returns_none(self):
        """FixtureTokenProvider always returns None."""
        provider = FixtureTokenProvider()
        assert provider.get_token() is None


class TestEnvTokenProvider:
    """Tests for EnvTokenProvider."""

    def test_no_token_set(self, monkeypatch):
        """When no token is set, should return None."""
        monkeypatch.delenv("GITHUB_TOKEN", raising=False)
        provider = EnvTokenProvider()
        assert provider.get_token() is None

    def test_token_set(self, monkeypatch):
        """When token is set, should return it."""
        test_token = "ghp_test_token_123"
        monkeypatch.setenv("GITHUB_TOKEN", test_token)
        provider = EnvTokenProvider()
        assert provider.get_token() == test_token


class TestGitHubAppTokenProvider:
    """Tests for GitHubAppTokenProvider."""

    @pytest.fixture
    def mock_http_client(self):
        """Create a mock HTTP client."""
        client = Mock()
        # Default successful response
        response = Mock()
        response.status_code = 201
        response.json.return_value = {
            "token": "ghs_mock_installation_token_abc123",
            "expires_at": (datetime.now(UTC) + timedelta(hours=1)).isoformat(),
        }
        client.post.return_value = response
        return client

    @pytest.fixture
    def valid_private_key(self):
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

    def test_not_configured_returns_none(self, monkeypatch):
        """When not configured, should return None."""
        monkeypatch.delenv("GITHUB_APP_ID", raising=False)
        monkeypatch.delenv("GITHUB_APP_PRIVATE_KEY_PEM", raising=False)
        monkeypatch.delenv("GITHUB_INSTALLATION_ID", raising=False)

        provider = GitHubAppTokenProvider()
        assert provider.get_token() is None

    def test_is_configured_check(self, monkeypatch, valid_private_key):
        """Test configuration check."""
        # Not configured
        monkeypatch.delenv("GITHUB_APP_ID", raising=False)
        monkeypatch.delenv("GITHUB_APP_PRIVATE_KEY_PEM", raising=False)
        monkeypatch.delenv("GITHUB_INSTALLATION_ID", raising=False)
        provider = GitHubAppTokenProvider()
        assert not provider._is_configured()

        # Fully configured
        monkeypatch.setenv("GITHUB_APP_ID", "12345")
        monkeypatch.setenv("GITHUB_APP_PRIVATE_KEY_PEM", valid_private_key)
        monkeypatch.setenv("GITHUB_INSTALLATION_ID", "67890")
        provider = GitHubAppTokenProvider()
        assert provider._is_configured()

    def test_generate_jwt_creates_valid_token(self, monkeypatch, valid_private_key):
        """Test JWT generation."""
        monkeypatch.setenv("GITHUB_APP_ID", "12345")
        monkeypatch.setenv("GITHUB_APP_PRIVATE_KEY_PEM", valid_private_key)
        monkeypatch.setenv("GITHUB_INSTALLATION_ID", "67890")

        provider = GitHubAppTokenProvider()
        jwt_token = provider._generate_jwt()

        assert jwt_token is not None
        assert isinstance(jwt_token, str)
        assert len(jwt_token) > 0

        # Decode without verification to check payload structure
        import jwt

        decoded = jwt.decode(jwt_token, options={"verify_signature": False})
        assert "iat" in decoded
        assert "exp" in decoded
        assert "iss" in decoded
        assert decoded["iss"] == "12345"

        # Check expiration is within expected range
        exp_delta = decoded["exp"] - decoded["iat"]
        assert exp_delta == provider.JWT_EXPIRATION_SECONDS

    def test_generate_jwt_with_escaped_newlines(self, monkeypatch):
        """Test that escaped newlines in private key are handled correctly."""
        # Use a private key with \n instead of actual newlines
        escaped_key = (
            "-----BEGIN RSA PRIVATE KEY-----\\n"
            "MIIEowIBAAKCAQEA3eF5BWTCu4B5XK1TPqOisXn6VpWIIfQwRO56Dx34rMs8dMJh\\n"
            "2gQrMLQTEaXSyamcfqlCb+5ErS/BIBFR0GwrBS/597h+ixo/40zNjPZkhuH69Rem\\n"
            "XMlbgzOde7UAKit9p64nnGU69lOQie0L7x1MCnYzQbXBgqC9uLJso44I4vAHYHZF\\n"
            "4++qmaqvwGWjFkRLX9lmvDHBHTYK3KjQIx9IDGnwsCRj5AaBvfF/ctmrkK6aBa4f\\n"
            "TDHlVdhNw5Xtf1jDlgNamLkqqtNj9yHJjsz2bjW2BTCSXx57WuZSuDPlBpMhmggH\\n"
            "CRzTIWdWEvK2EFqDA542ygfrb0kII2TXLC2J6wIDAQABAoIBAAiYI7JoSTyvCMRk\\n"
            "uE08VGBwe5hf+WJrTXVWEWdFf2zeAGz7XIPv1mZwCy8LT8Nc7QFg+ABS59kXePEP\\n"
            "iq46il4Mki+ct1YXAbOBtZKItrMczLYyoNCGQiOuW6K/i46WmarljYY6y5JgAUC+\\n"
            "bFBqP5hGJM0eR60SIdcmHhwls8VqeUASZ3zgbbXWORXArn6bFRy3FTFjwQ4SufkG\\n"
            "Ion1zuzC7Smhr7Qa6AqtGKoZYkJ5rmqzcgSu6w6ZMWF4dfgYstZAdnhf+CdxJ4C3\\n"
            "HezRhq0O6PmG6L54FZ94Xjb0A6mU+twXkKFA4+1RzjnscLKQW4pemrTZbY41H34R\\n"
            "9hiHBlUCgYEA7xP2lRB5fUFT3IgKM+wL2yGdojthZ8J1rb71YbiAJdeRqdpEAUZ/\\n"
            "RWCoq65j+H3yqJ2duwkrRqnSr8FkaTm0XvEtUrYtHFsZbFMNjjuMF1DftOZNhZmw\\n"
            "NC7z+lhY4tnU5Ksbzl/Hx97gme7eEi/PicQQbPwAqdppmPUwHn8UP9cCgYEA7ZXm\\n"
            "WM8IZX11IzG5jMjyIEq4BTMECeeOSeEhppQiszeiFEE+SlUPAux5JiPBWVVmYp58\\n"
            "H9/mUxXi075W4vYoaJT5DX+SaAYTugleI25V8vkSoqImo/P9KztGvEgIU9niC2kB\\n"
            "bV9O+Zcp83uZV6/UBtb2AYcEvp47yjnO2WbylA0CgYAdrSWzlSrvcFd/jWdu0IMc\\n"
            "PUz64VIS9iFzYrvE2IkXqW2MXuqIGf8cVoY5YVlJdCDV61Kz78xuZhAf/up+4UnR\\n"
            "azCMDs8EsQ4z0w9gs2WNU12hb+D5j30+zQE99w95gT6a795wvJTo63KHyQ3JxiOF\\n"
            "30+Gp7VRYCoxcWX6sx2JWwKBgFZ2GM/0+A9HKtvV+rqbXlIWHwX1XODl3chRH9fp\\n"
            "TP9/nYJVg/+1GLNtr2EL3g9OnuYA2xcWelF+Q3/fYutRvb7hiAk7heJJY+BuDE5E\\n"
            "lw7HSdrZu8oqvtV+yu02IaGyRyrz2csdxjXapy+uqU1Z9YVPsVM4+acNGqErjHVd\\n"
            "m6X5AoGBAMIE462Zsnu/bGItTbtAS2xVV5c04HppDkRGaqtcYMxU1+oGnxjkQ1pp\\n"
            "13kV8WUv1dsyULmlcPrH74We3RG0wgqlI+5vd3je8oYFMyZ98v4UNG7SpGGYRPL2\\n"
            "adW+7qG7Q9T48zppJ2NWTp6pUUOKrMfX2Mu9tqGJJZiUMsbhrI+w\\n"
            "-----END RSA PRIVATE KEY-----"
        )

        monkeypatch.setenv("GITHUB_APP_ID", "12345")
        monkeypatch.setenv("GITHUB_APP_PRIVATE_KEY_PEM", escaped_key)
        monkeypatch.setenv("GITHUB_INSTALLATION_ID", "67890")

        provider = GitHubAppTokenProvider()
        # Should handle the escaped newlines correctly
        assert provider.private_key_pem.count("\n") > 0
        assert "\\n" not in provider.private_key_pem

    def test_mint_installation_token_success(
        self, monkeypatch, valid_private_key, mock_http_client
    ):
        """Test successful installation token minting."""
        monkeypatch.setenv("GITHUB_APP_ID", "12345")
        monkeypatch.setenv("GITHUB_APP_PRIVATE_KEY_PEM", valid_private_key)
        monkeypatch.setenv("GITHUB_INSTALLATION_ID", "67890")

        provider = GitHubAppTokenProvider(http_client=mock_http_client)
        token, expires_at = provider._mint_installation_token()

        assert token == "ghs_mock_installation_token_abc123"
        assert isinstance(expires_at, datetime)
        assert expires_at > datetime.now(UTC)

        # Verify HTTP request was made correctly
        mock_http_client.post.assert_called_once()
        call_args = mock_http_client.post.call_args
        assert "https://api.github.com/app/installations/67890/access_tokens" in call_args[0]

        headers = call_args[1]["headers"]
        assert headers["Accept"] == "application/vnd.github+json"
        assert headers["Authorization"].startswith("Bearer ")

    def test_mint_installation_token_failure(self, monkeypatch, valid_private_key):
        """Test installation token minting failure."""
        monkeypatch.setenv("GITHUB_APP_ID", "12345")
        monkeypatch.setenv("GITHUB_APP_PRIVATE_KEY_PEM", valid_private_key)
        monkeypatch.setenv("GITHUB_INSTALLATION_ID", "67890")

        # Create mock client that returns error
        mock_client = Mock()
        response = Mock()
        response.status_code = 401
        response.text = "Unauthorized"
        mock_client.post.return_value = response

        provider = GitHubAppTokenProvider(http_client=mock_client)

        with pytest.raises(
            RuntimeError, match="(Failed to mint installation token|JWT generation failed)"
        ):
            provider._mint_installation_token()

    def test_token_caching(self, monkeypatch, valid_private_key, mock_http_client):
        """Test that tokens are cached and reused."""
        monkeypatch.setenv("GITHUB_APP_ID", "12345")
        monkeypatch.setenv("GITHUB_APP_PRIVATE_KEY_PEM", valid_private_key)
        monkeypatch.setenv("GITHUB_INSTALLATION_ID", "67890")

        provider = GitHubAppTokenProvider(http_client=mock_http_client)

        # First call should mint a token
        token1 = provider.get_token()
        assert token1 == "ghs_mock_installation_token_abc123"
        assert mock_http_client.post.call_count == 1

        # Second call should use cached token
        token2 = provider.get_token()
        assert token2 == token1
        assert mock_http_client.post.call_count == 1  # No additional call

    def test_token_refresh_before_expiry(self, monkeypatch, valid_private_key, mock_http_client):
        """Test that tokens are refreshed before they expire."""
        monkeypatch.setenv("GITHUB_APP_ID", "12345")
        monkeypatch.setenv("GITHUB_APP_PRIVATE_KEY_PEM", valid_private_key)
        monkeypatch.setenv("GITHUB_INSTALLATION_ID", "67890")

        # Set up mock to return token expiring soon
        response = Mock()
        response.status_code = 201
        near_expiry = datetime.now(UTC) + timedelta(
            seconds=200
        )  # Less than refresh window
        response.json.return_value = {
            "token": "ghs_expiring_soon",
            "expires_at": near_expiry.isoformat(),
        }
        mock_http_client.post.return_value = response

        provider = GitHubAppTokenProvider(http_client=mock_http_client)

        # First call
        token1 = provider.get_token()
        assert token1 == "ghs_expiring_soon"
        assert mock_http_client.post.call_count == 1

        # Set up new token for refresh
        response.json.return_value = {
            "token": "ghs_refreshed_token",
            "expires_at": (datetime.now(UTC) + timedelta(hours=1)).isoformat(),
        }

        # Second call should refresh because token is near expiry
        token2 = provider.get_token()
        assert token2 == "ghs_refreshed_token"
        assert mock_http_client.post.call_count == 2  # Token was refreshed

    def test_should_refresh_token_logic(self, monkeypatch, valid_private_key):
        """Test token refresh decision logic."""
        monkeypatch.setenv("GITHUB_APP_ID", "12345")
        monkeypatch.setenv("GITHUB_APP_PRIVATE_KEY_PEM", valid_private_key)
        monkeypatch.setenv("GITHUB_INSTALLATION_ID", "67890")

        provider = GitHubAppTokenProvider()

        # No cached token - should refresh
        assert provider._should_refresh_token() is True

        # Set a fresh token - should not refresh
        provider._cached_token = "test_token"
        provider._token_expires_at = datetime.now(UTC) + timedelta(hours=1)
        assert provider._should_refresh_token() is False

        # Set a token expiring soon - should refresh
        provider._token_expires_at = datetime.now(UTC) + timedelta(seconds=200)
        assert provider._should_refresh_token() is True

        # Set an expired token - should refresh
        provider._token_expires_at = datetime.now(UTC) - timedelta(seconds=10)
        assert provider._should_refresh_token() is True


class TestGetTokenProvider:
    """Tests for get_token_provider factory function."""

    def test_returns_fixture_only_by_default(self, monkeypatch):
        """When no env vars are set, should return FixtureTokenProvider."""
        monkeypatch.delenv("GITHUB_TOKEN", raising=False)
        monkeypatch.delenv("GITHUB_APP_ID", raising=False)
        monkeypatch.delenv("GITHUB_APP_PRIVATE_KEY_PEM", raising=False)
        monkeypatch.delenv("GITHUB_INSTALLATION_ID", raising=False)

        provider = get_token_provider()
        assert isinstance(provider, FixtureTokenProvider)

    def test_returns_env_provider_when_token_set(self, monkeypatch):
        """When GITHUB_TOKEN is set, should return EnvTokenProvider."""
        monkeypatch.setenv("GITHUB_TOKEN", "ghp_test_token")
        monkeypatch.delenv("GITHUB_APP_ID", raising=False)

        provider = get_token_provider()
        assert isinstance(provider, EnvTokenProvider)

    def test_returns_github_app_provider_when_configured(self, monkeypatch):
        """When GitHub App is configured, should return GitHubAppTokenProvider."""
        monkeypatch.setenv("GITHUB_APP_ID", "12345")
        monkeypatch.setenv("GITHUB_APP_PRIVATE_KEY_PEM", "test_key")
        monkeypatch.setenv("GITHUB_INSTALLATION_ID", "67890")
        # Also set GITHUB_TOKEN to ensure App takes priority
        monkeypatch.setenv("GITHUB_TOKEN", "ghp_test_token")

        provider = get_token_provider()
        assert isinstance(provider, GitHubAppTokenProvider)

    def test_github_app_takes_priority_over_env_token(self, monkeypatch):
        """GitHub App provider should take priority over environment token."""
        monkeypatch.setenv("GITHUB_TOKEN", "ghp_test_token")
        monkeypatch.setenv("GITHUB_APP_ID", "12345")
        monkeypatch.setenv("GITHUB_APP_PRIVATE_KEY_PEM", "test_key")
        monkeypatch.setenv("GITHUB_INSTALLATION_ID", "67890")

        provider = get_token_provider()
        assert isinstance(provider, GitHubAppTokenProvider)
        assert not isinstance(provider, EnvTokenProvider)
