"""Tests for live GitHub provider."""

import pytest

from handsfree.github.auth import FixtureOnlyProvider, GitHubAuthProvider
from handsfree.github.provider import LiveGitHubProvider


class MockTokenProvider(GitHubAuthProvider):
    """Mock token provider for testing."""

    def __init__(self, token: str | None = None):
        self._token = token

    def get_token(self, user_id: str) -> str | None:
        return self._token

    def supports_live_mode(self) -> bool:
        return self._token is not None


class TestLiveGitHubProvider:
    """Test live GitHub provider."""

    def test_initialization(self):
        """Test provider initialization."""
        token_provider = MockTokenProvider("test_token")
        provider = LiveGitHubProvider(token_provider)
        assert provider is not None

    def test_initialization_requires_token_provider(self):
        """Test that initialization requires a GitHubAuthProvider instance."""
        with pytest.raises(TypeError, match="GitHubAuthProvider"):
            LiveGitHubProvider("not a token provider")

    def test_fallback_to_fixture_when_no_token(self):
        """Test that provider falls back to fixtures when no token available."""
        token_provider = MockTokenProvider(None)
        provider = LiveGitHubProvider(token_provider)

        # Should fall back to fixtures
        prs = provider.list_user_prs("testuser")
        assert isinstance(prs, list)
        assert len(prs) == 3  # From fixture

    def test_get_pr_details_fallback(self):
        """Test get_pr_details falls back to fixture."""
        token_provider = MockTokenProvider(None)
        provider = LiveGitHubProvider(token_provider)

        details = provider.get_pr_details("owner/repo", 123)
        assert details["pr_number"] == 123
        assert details["title"] == "Add new feature X"

    def test_get_pr_checks_fallback(self):
        """Test get_pr_checks falls back to fixture."""
        token_provider = MockTokenProvider(None)
        provider = LiveGitHubProvider(token_provider)

        checks = provider.get_pr_checks("owner/repo", 123)
        assert isinstance(checks, list)
        assert len(checks) == 3

    def test_get_pr_reviews_fallback(self):
        """Test get_pr_reviews falls back to fixture."""
        token_provider = MockTokenProvider(None)
        provider = LiveGitHubProvider(token_provider)

        reviews = provider.get_pr_reviews("owner/repo", 123)
        assert isinstance(reviews, list)
        assert len(reviews) == 2

    def test_with_token_but_not_implemented(self):
        """Test that provider falls back even with token (API not implemented)."""
        token_provider = MockTokenProvider("ghp_test1234567890")
        provider = LiveGitHubProvider(token_provider)

        # Should still fall back since live API calls are not implemented
        prs = provider.list_user_prs("testuser")
        assert isinstance(prs, list)
        assert len(prs) == 3  # From fixture

    def test_headers_include_authorization(self):
        """Test that headers include authorization when token available."""
        token_provider = MockTokenProvider("ghp_test1234567890")
        provider = LiveGitHubProvider(token_provider)

        headers = provider._get_headers()
        assert "Authorization" in headers
        assert headers["Authorization"] == "Bearer ghp_test1234567890"
        assert headers["Accept"] == "application/vnd.github.v3+json"
        assert "User-Agent" in headers

    def test_headers_without_token(self):
        """Test that headers don't include authorization without token."""
        token_provider = MockTokenProvider(None)
        provider = LiveGitHubProvider(token_provider)

        headers = provider._get_headers()
        assert "Authorization" not in headers
        assert headers["Accept"] == "application/vnd.github.v3+json"
