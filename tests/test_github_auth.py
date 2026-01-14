"""Tests for GitHub authentication providers."""

from handsfree.github.auth import (
    EnvironmentTokenProvider,
    FixtureOnlyProvider,
    get_default_auth_provider,
)


class TestFixtureOnlyProvider:
    """Tests for FixtureOnlyProvider."""

    def test_get_token_returns_none(self):
        """FixtureOnlyProvider always returns None for tokens."""
        provider = FixtureOnlyProvider()
        assert provider.get_token("user123") is None

    def test_supports_live_mode_returns_false(self):
        """FixtureOnlyProvider never supports live mode."""
        provider = FixtureOnlyProvider()
        assert provider.supports_live_mode() is False


class TestEnvironmentTokenProvider:
    """Tests for EnvironmentTokenProvider."""

    def test_no_env_vars_set(self, monkeypatch):
        """When no env vars are set, provider should not support live mode."""
        monkeypatch.delenv("GITHUB_TOKEN", raising=False)
        monkeypatch.delenv("GITHUB_LIVE_MODE", raising=False)

        provider = EnvironmentTokenProvider()
        assert provider.get_token("user123") is None
        assert provider.supports_live_mode() is False

    def test_token_set_but_live_mode_disabled(self, monkeypatch):
        """When token is set but live mode is disabled, should not support live mode."""
        monkeypatch.setenv("GITHUB_TOKEN", "ghp_test_token_123")
        monkeypatch.delenv("GITHUB_LIVE_MODE", raising=False)

        provider = EnvironmentTokenProvider()
        assert provider.get_token("user123") is None
        assert provider.supports_live_mode() is False

    def test_live_mode_enabled_but_no_token(self, monkeypatch):
        """When live mode is enabled but no token, should not support live mode."""
        monkeypatch.delenv("GITHUB_TOKEN", raising=False)
        monkeypatch.setenv("GITHUB_LIVE_MODE", "true")

        provider = EnvironmentTokenProvider()
        assert provider.get_token("user123") is None
        assert provider.supports_live_mode() is False

    def test_both_token_and_live_mode_enabled(self, monkeypatch):
        """When both token and live mode are set, should support live mode."""
        test_token = "ghp_test_token_xyz"
        monkeypatch.setenv("GITHUB_TOKEN", test_token)
        monkeypatch.setenv("GITHUB_LIVE_MODE", "true")

        provider = EnvironmentTokenProvider()
        assert provider.get_token("user123") == test_token
        assert provider.supports_live_mode() is True

    def test_live_mode_various_true_values(self, monkeypatch):
        """Test that various true values work for GITHUB_LIVE_MODE."""
        test_token = "ghp_test_token_abc"
        monkeypatch.setenv("GITHUB_TOKEN", test_token)

        for true_value in ["true", "True", "TRUE", "1", "yes", "Yes", "YES"]:
            monkeypatch.setenv("GITHUB_LIVE_MODE", true_value)
            provider = EnvironmentTokenProvider()
            assert provider.supports_live_mode() is True, f"Failed for value: {true_value}"

    def test_live_mode_false_values(self, monkeypatch):
        """Test that false values disable live mode."""
        test_token = "ghp_test_token_def"
        monkeypatch.setenv("GITHUB_TOKEN", test_token)

        for false_value in ["false", "False", "0", "no", "", "random"]:
            monkeypatch.setenv("GITHUB_LIVE_MODE", false_value)
            provider = EnvironmentTokenProvider()
            assert provider.supports_live_mode() is False, f"Failed for value: {false_value}"


class TestGetDefaultAuthProvider:
    """Tests for get_default_auth_provider factory function."""

    def test_returns_fixture_only_by_default(self, monkeypatch):
        """When no env vars are set, should return FixtureOnlyProvider."""
        monkeypatch.delenv("GITHUB_LIVE_MODE", raising=False)
        monkeypatch.delenv("GITHUB_TOKEN", raising=False)

        provider = get_default_auth_provider()
        assert isinstance(provider, FixtureOnlyProvider)

    def test_returns_environment_provider_when_live_mode_enabled(self, monkeypatch):
        """When GITHUB_LIVE_MODE is set, should return EnvironmentTokenProvider."""
        monkeypatch.setenv("GITHUB_LIVE_MODE", "true")
        monkeypatch.setenv("GITHUB_TOKEN", "ghp_test_token")

        provider = get_default_auth_provider()
        assert isinstance(provider, EnvironmentTokenProvider)

    def test_returns_fixture_only_when_only_token_set(self, monkeypatch):
        """When only token is set without live mode, should return FixtureOnlyProvider."""
        monkeypatch.setenv("GITHUB_TOKEN", "ghp_test_token")
        monkeypatch.delenv("GITHUB_LIVE_MODE", raising=False)

        provider = get_default_auth_provider()
        assert isinstance(provider, FixtureOnlyProvider)
