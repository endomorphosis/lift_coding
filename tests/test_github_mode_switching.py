"""Tests for GitHub provider mode switching via environment variables."""

import pytest

from handsfree.github.auth import (
    EnvTokenProvider,
    FixtureTokenProvider,
    get_token_provider,
)
from handsfree.github.provider import GitHubProvider, LiveGitHubProvider


class TestEnvironmentVariableSwitching:
    """Tests for environment variable-based mode switching."""

    def test_hands_free_github_mode_live(self, monkeypatch):
        """Test HANDS_FREE_GITHUB_MODE=live enables live mode."""
        monkeypatch.setenv("HANDS_FREE_GITHUB_MODE", "live")
        monkeypatch.setenv("GITHUB_TOKEN", "ghp_test_token")

        provider = get_token_provider()
        assert isinstance(provider, EnvTokenProvider)
        assert provider.get_token() == "ghp_test_token"

    def test_github_live_mode_true(self, monkeypatch):
        """Test GITHUB_LIVE_MODE=true enables live mode."""
        monkeypatch.setenv("GITHUB_LIVE_MODE", "true")
        monkeypatch.setenv("GITHUB_TOKEN", "ghp_test_token")

        provider = get_token_provider()
        assert isinstance(provider, EnvTokenProvider)
        assert provider.get_token() == "ghp_test_token"

    def test_github_live_mode_1(self, monkeypatch):
        """Test GITHUB_LIVE_MODE=1 enables live mode."""
        monkeypatch.setenv("GITHUB_LIVE_MODE", "1")
        monkeypatch.setenv("GITHUB_TOKEN", "ghp_test_token")

        provider = get_token_provider()
        assert isinstance(provider, EnvTokenProvider)

    def test_github_live_mode_yes(self, monkeypatch):
        """Test GITHUB_LIVE_MODE=yes enables live mode."""
        monkeypatch.setenv("GITHUB_LIVE_MODE", "yes")
        monkeypatch.setenv("GITHUB_TOKEN", "ghp_test_token")

        provider = get_token_provider()
        assert isinstance(provider, EnvTokenProvider)

    def test_default_is_fixture_mode(self, monkeypatch):
        """Test that default mode is fixture when no env vars set."""
        # Clear any existing env vars
        monkeypatch.delenv("HANDS_FREE_GITHUB_MODE", raising=False)
        monkeypatch.delenv("GITHUB_LIVE_MODE", raising=False)
        monkeypatch.delenv("GITHUB_TOKEN", raising=False)

        provider = get_token_provider()
        assert isinstance(provider, FixtureTokenProvider)
        assert provider.get_token() is None

    def test_live_mode_without_token_falls_back_to_fixture(self, monkeypatch):
        """Test that live mode without token falls back to fixture."""
        monkeypatch.setenv("HANDS_FREE_GITHUB_MODE", "live")
        monkeypatch.delenv("GITHUB_TOKEN", raising=False)

        provider = get_token_provider()
        assert isinstance(provider, FixtureTokenProvider)

    def test_fixture_mode_explicit(self, monkeypatch):
        """Test explicit fixture mode setting."""
        monkeypatch.setenv("HANDS_FREE_GITHUB_MODE", "fixtures")
        monkeypatch.setenv("GITHUB_TOKEN", "ghp_test_token")

        provider = get_token_provider()
        # Should still be fixture mode even with token
        assert isinstance(provider, FixtureTokenProvider)


class TestLiveProviderIntegration:
    """Tests for LiveGitHubProvider integration with environment variables."""

    def test_live_provider_with_env_token(self, monkeypatch):
        """Test LiveGitHubProvider can be created with env token provider."""
        monkeypatch.setenv("HANDS_FREE_GITHUB_MODE", "live")
        monkeypatch.setenv("GITHUB_TOKEN", "ghp_test_token")

        token_provider = get_token_provider()
        provider = LiveGitHubProvider(token_provider)

        # Should have token available
        headers = provider._get_headers()
        assert "Authorization" in headers
        assert headers["Authorization"] == "Bearer ghp_test_token"

    def test_live_provider_fallback_behavior(self, monkeypatch):
        """Test LiveGitHubProvider falls back to fixtures when needed."""
        monkeypatch.setenv("HANDS_FREE_GITHUB_MODE", "live")
        monkeypatch.setenv("GITHUB_TOKEN", "ghp_test_token")

        token_provider = get_token_provider()
        provider = LiveGitHubProvider(token_provider)

        # API not implemented yet, should fall back to fixtures
        prs = provider.list_user_prs("testuser")
        assert len(prs) == 3  # From fixture


class TestProviderFactoryPattern:
    """Tests for creating providers using factory functions."""

    def test_create_fixture_provider(self, monkeypatch):
        """Test creating a fixture-only provider."""
        monkeypatch.delenv("HANDS_FREE_GITHUB_MODE", raising=False)
        monkeypatch.delenv("GITHUB_LIVE_MODE", raising=False)

        # Default GitHubProvider uses fixtures
        provider = GitHubProvider()
        prs = provider.list_user_prs("testuser")
        assert len(prs) == 3

    def test_create_live_provider_with_factory(self, monkeypatch):
        """Test creating a live provider using factory function."""
        monkeypatch.setenv("HANDS_FREE_GITHUB_MODE", "live")
        monkeypatch.setenv("GITHUB_TOKEN", "ghp_test_token")

        token_provider = get_token_provider()
        provider = LiveGitHubProvider(token_provider)

        # Verify it's properly configured
        assert provider._token_provider.get_token() == "ghp_test_token"


class TestTokenProviderInterface:
    """Tests for TokenProvider interface implementation."""

    def test_fixture_token_provider_returns_none(self):
        """Test FixtureTokenProvider always returns None."""
        provider = FixtureTokenProvider()
        assert provider.get_token() is None

    def test_env_token_provider_reads_from_env(self, monkeypatch):
        """Test EnvTokenProvider reads from GITHUB_TOKEN."""
        monkeypatch.setenv("GITHUB_TOKEN", "ghp_my_token")
        provider = EnvTokenProvider()
        assert provider.get_token() == "ghp_my_token"

    def test_env_token_provider_returns_none_when_not_set(self, monkeypatch):
        """Test EnvTokenProvider returns None when env var not set."""
        monkeypatch.delenv("GITHUB_TOKEN", raising=False)
        provider = EnvTokenProvider()
        assert provider.get_token() is None


class TestErrorHandling:
    """Tests for error handling in live mode."""

    def test_live_provider_requires_token_provider_type(self):
        """Test LiveGitHubProvider validates token provider type."""
        with pytest.raises(TypeError, match="TokenProvider"):
            LiveGitHubProvider("not a token provider")

    def test_make_request_raises_when_no_token(self):
        """Test _make_request raises RuntimeError when no token available."""
        token_provider = FixtureTokenProvider()
        provider = LiveGitHubProvider(token_provider)

        with pytest.raises(RuntimeError, match="GitHub token not available"):
            provider._make_request("/test/endpoint")
