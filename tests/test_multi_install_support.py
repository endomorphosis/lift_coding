"""Tests for GitHub App multi-installation support.

This test module validates that the system correctly handles multiple GitHub App
installations per user and selects the correct installation for each repository.
"""

import uuid
from datetime import UTC, datetime, timedelta
from unittest.mock import Mock

import pytest

from handsfree.db import init_db
from handsfree.db.github_connections import (
    create_github_connection,
    get_installation_for_repo,
)
from handsfree.db.repo_subscriptions import create_repo_subscription
from handsfree.github.auth import UserTokenProvider, get_user_token_provider


@pytest.fixture
def db_conn():
    """Create an in-memory database connection for testing."""
    conn = init_db(":memory:")
    yield conn
    conn.close()


@pytest.fixture
def test_user_id():
    """Generate a consistent test user ID."""
    return str(uuid.UUID("12345678-1234-1234-1234-123456789012"))


@pytest.fixture
def mock_http_client():
    """Create a mock HTTP client for token minting."""

    def create_mock_response(installation_id: str):
        """Create a mock response for a specific installation."""
        response = Mock()
        response.status_code = 201
        response.json.return_value = {
            "token": f"ghs_mock_token_install_{installation_id}",
            "expires_at": (datetime.now(UTC) + timedelta(hours=1)).isoformat(),
        }
        return response

    client = Mock()
    # Store responses per installation_id
    client.responses = {}

    def mock_post(url, **kwargs):
        # Extract installation_id from URL
        # URL format: https://api.github.com/app/installations/{installation_id}/access_tokens
        parts = url.split("/")
        if "installations" in parts:
            idx = parts.index("installations")
            if idx + 1 < len(parts):
                installation_id = parts[idx + 1]
                if installation_id not in client.responses:
                    client.responses[installation_id] = create_mock_response(installation_id)
                return client.responses[installation_id]

        # Default response
        return create_mock_response("unknown")

    client.post.side_effect = mock_post
    return client


@pytest.fixture
def valid_private_key():
    """Return a valid RSA private key for testing."""
    # This is a test key generated for this purpose only
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


class TestGetInstallationForRepo:
    """Test get_installation_for_repo helper function."""

    def test_returns_none_when_no_connections(self, db_conn, test_user_id):
        """Should return None when user has no connections."""
        result = get_installation_for_repo(
            conn=db_conn,
            user_id=test_user_id,
            repo_full_name="owner/repo1",
        )
        assert result is None

    def test_returns_installation_from_repo_subscription(self, db_conn, test_user_id):
        """Should return installation_id from repo_subscriptions when available."""
        # Create a repo subscription with specific installation
        create_repo_subscription(
            conn=db_conn,
            user_id=test_user_id,
            repo_full_name="owner/repo1",
            installation_id=11111,
        )

        result = get_installation_for_repo(
            conn=db_conn,
            user_id=test_user_id,
            repo_full_name="owner/repo1",
        )
        assert result == 11111

    def test_returns_none_from_repo_subscription_without_installation(
        self, db_conn, test_user_id
    ):
        """Should fall back when repo subscription has no installation_id."""
        # Create a repo subscription without installation_id
        create_repo_subscription(
            conn=db_conn,
            user_id=test_user_id,
            repo_full_name="owner/repo1",
            installation_id=None,
        )

        # Create a github connection as fallback
        create_github_connection(
            conn=db_conn,
            user_id=test_user_id,
            installation_id=99999,
        )

        result = get_installation_for_repo(
            conn=db_conn,
            user_id=test_user_id,
            repo_full_name="owner/repo1",
        )
        # Should fall back to github_connection
        assert result == 99999

    def test_falls_back_to_github_connection(self, db_conn, test_user_id):
        """Should fall back to github_connections when no repo subscription."""
        # Create github connections (most recent is returned first)
        create_github_connection(
            conn=db_conn,
            user_id=test_user_id,
            installation_id=22222,
        )
        create_github_connection(
            conn=db_conn,
            user_id=test_user_id,
            installation_id=33333,
        )

        result = get_installation_for_repo(
            conn=db_conn,
            user_id=test_user_id,
            repo_full_name="owner/repo1",
        )
        # Should return most recent connection's installation_id (33333, created last)
        assert result == 33333

    def test_prefers_repo_subscription_over_connection(self, db_conn, test_user_id):
        """Repo subscription should take priority over github_connections."""
        # Create github connection
        create_github_connection(
            conn=db_conn,
            user_id=test_user_id,
            installation_id=99999,
        )

        # Create repo subscription with different installation
        create_repo_subscription(
            conn=db_conn,
            user_id=test_user_id,
            repo_full_name="owner/repo1",
            installation_id=11111,
        )

        result = get_installation_for_repo(
            conn=db_conn,
            user_id=test_user_id,
            repo_full_name="owner/repo1",
        )
        # Should use repo subscription's installation
        assert result == 11111


class TestMultiInstallationScenario:
    """Test multi-installation scenarios with different repos."""

    def test_different_installations_for_different_repos(
        self, db_conn, test_user_id, monkeypatch, valid_private_key, mock_http_client
    ):
        """Test that different repos use different installation IDs."""
        # Setup environment
        monkeypatch.setenv("GITHUB_APP_ID", "12345")
        monkeypatch.setenv("GITHUB_APP_PRIVATE_KEY_PEM", valid_private_key)
        monkeypatch.delenv("GITHUB_TOKEN", raising=False)

        # Create repo subscriptions with different installations
        create_repo_subscription(
            conn=db_conn,
            user_id=test_user_id,
            repo_full_name="org1/repo1",
            installation_id=11111,
        )
        create_repo_subscription(
            conn=db_conn,
            user_id=test_user_id,
            repo_full_name="org2/repo2",
            installation_id=22222,
        )

        # Get token provider for repo1
        provider1 = get_user_token_provider(
            db_conn=db_conn,
            user_id=test_user_id,
            repo_full_name="org1/repo1",
            http_client=mock_http_client,
        )
        token1 = provider1.get_token()

        # Get token provider for repo2
        provider2 = get_user_token_provider(
            db_conn=db_conn,
            user_id=test_user_id,
            repo_full_name="org2/repo2",
            http_client=mock_http_client,
        )
        token2 = provider2.get_token()

        # Verify different tokens were minted for different installations
        assert token1 == "ghs_mock_token_install_11111"
        assert token2 == "ghs_mock_token_install_22222"
        assert token1 != token2

    def test_fixture_mode_with_multiple_installations(self, db_conn, test_user_id, monkeypatch):
        """Test that fixture mode works correctly with multiple installations."""
        # Don't configure GitHub App
        monkeypatch.delenv("GITHUB_APP_ID", raising=False)
        monkeypatch.delenv("GITHUB_APP_PRIVATE_KEY_PEM", raising=False)
        monkeypatch.delenv("GITHUB_TOKEN", raising=False)

        # Create repo subscriptions
        create_repo_subscription(
            conn=db_conn,
            user_id=test_user_id,
            repo_full_name="org1/repo1",
            installation_id=11111,
        )
        create_repo_subscription(
            conn=db_conn,
            user_id=test_user_id,
            repo_full_name="org2/repo2",
            installation_id=22222,
        )

        # Get token providers
        provider1 = get_user_token_provider(
            db_conn=db_conn,
            user_id=test_user_id,
            repo_full_name="org1/repo1",
        )
        provider2 = get_user_token_provider(
            db_conn=db_conn,
            user_id=test_user_id,
            repo_full_name="org2/repo2",
        )

        # Should return None (fixture mode)
        assert provider1.get_token() is None
        assert provider2.get_token() is None

    def test_falls_back_to_default_installation(
        self, db_conn, test_user_id, monkeypatch, valid_private_key, mock_http_client
    ):
        """Test fallback to default installation when repo has no specific mapping."""
        # Setup environment
        monkeypatch.setenv("GITHUB_APP_ID", "12345")
        monkeypatch.setenv("GITHUB_APP_PRIVATE_KEY_PEM", valid_private_key)
        monkeypatch.delenv("GITHUB_TOKEN", raising=False)

        # Create a default github connection
        create_github_connection(
            conn=db_conn,
            user_id=test_user_id,
            installation_id=99999,
        )

        # Create repo subscription for one repo only
        create_repo_subscription(
            conn=db_conn,
            user_id=test_user_id,
            repo_full_name="org1/repo1",
            installation_id=11111,
        )

        # Get token for repo with specific installation
        provider1 = get_user_token_provider(
            db_conn=db_conn,
            user_id=test_user_id,
            repo_full_name="org1/repo1",
            http_client=mock_http_client,
        )
        token1 = provider1.get_token()
        assert token1 == "ghs_mock_token_install_11111"

        # Get token for repo without specific installation (should use default)
        provider2 = get_user_token_provider(
            db_conn=db_conn,
            user_id=test_user_id,
            repo_full_name="org2/repo2",
            http_client=mock_http_client,
        )
        token2 = provider2.get_token()
        assert token2 == "ghs_mock_token_install_99999"

    def test_user_token_provider_without_repo_uses_default(
        self, db_conn, test_user_id, monkeypatch, valid_private_key, mock_http_client
    ):
        """Test that UserTokenProvider without repo_full_name uses default installation."""
        # Setup environment
        monkeypatch.setenv("GITHUB_APP_ID", "12345")
        monkeypatch.setenv("GITHUB_APP_PRIVATE_KEY_PEM", valid_private_key)
        monkeypatch.delenv("GITHUB_TOKEN", raising=False)

        # Create connections
        create_github_connection(
            conn=db_conn,
            user_id=test_user_id,
            installation_id=88888,
        )

        # Create repo subscription
        create_repo_subscription(
            conn=db_conn,
            user_id=test_user_id,
            repo_full_name="org1/repo1",
            installation_id=11111,
        )

        # Get token without specifying repo
        provider = UserTokenProvider(
            db_conn=db_conn,
            user_id=test_user_id,
            repo_full_name=None,
            http_client=mock_http_client,
        )
        token = provider.get_token()

        # Should use default connection (most recent)
        assert token == "ghs_mock_token_install_88888"


class TestThreadSafety:
    """Test thread-safety of token refresh."""

    def test_concurrent_token_refresh(self, monkeypatch, valid_private_key):
        """Test that concurrent calls to get_token don't cause issues."""
        import threading

        from handsfree.github.auth import GitHubAppTokenProvider

        # Setup environment
        monkeypatch.setenv("GITHUB_APP_ID", "12345")
        monkeypatch.setenv("GITHUB_APP_PRIVATE_KEY_PEM", valid_private_key)

        # Create a mock client that simulates slow response
        mock_client = Mock()
        response = Mock()
        response.status_code = 201

        call_lock = threading.Lock()
        mint_count = [0]  # Use list to allow mutation in closure

        def slow_json():
            """Simulate slow JSON parsing and track calls."""
            import time

            with call_lock:
                mint_count[0] += 1
            time.sleep(0.05)  # Small delay to encourage race conditions
            return {
                "token": "ghs_mock_token",
                "expires_at": (datetime.now(UTC) + timedelta(hours=1)).isoformat(),
            }

        response.json = slow_json
        mock_client.post.return_value = response

        # Create a single provider instance shared by all threads
        provider = GitHubAppTokenProvider(
            app_id="12345",
            private_key_pem=valid_private_key,
            installation_id="11111",
            http_client=mock_client,
        )

        # Call get_token concurrently from multiple threads
        tokens = []
        errors = []

        def get_token_threaded():
            try:
                token = provider.get_token()
                with call_lock:
                    tokens.append(token)
            except Exception as e:
                with call_lock:
                    errors.append(e)

        threads = [threading.Thread(target=get_token_threaded) for _ in range(5)]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join()

        # Verify no errors occurred
        assert len(errors) == 0, f"Errors occurred: {errors}"

        # Verify all threads got a token
        assert len(tokens) == 5

        # All tokens should be the same (cached)
        assert all(t == "ghs_mock_token" for t in tokens)

        # Token should have been minted only once or a few times due to the lock
        # The lock should prevent too many concurrent minting attempts
        assert mint_count[0] <= 3, f"Token was minted {mint_count[0]} times (expected <= 3)"
