"""Tests for GitHub provider."""

from pathlib import Path

import pytest

from handsfree.github import GitHubProvider
from handsfree.github.auth import EnvironmentTokenProvider, FixtureOnlyProvider


@pytest.fixture
def github_provider():
    """Create a GitHub provider with test fixtures."""
    fixtures_dir = Path(__file__).parent / "fixtures" / "github" / "api"
    return GitHubProvider(fixtures_dir=fixtures_dir)


@pytest.fixture
def fixture_only_provider():
    """Create a provider that always uses fixtures."""
    fixtures_dir = Path(__file__).parent / "fixtures" / "github" / "api"
    return GitHubProvider(fixtures_dir=fixtures_dir, auth_provider=FixtureOnlyProvider())


@pytest.fixture
def live_mode_provider(monkeypatch):
    """Create a provider with live mode enabled (but still using fixtures)."""
    fixtures_dir = Path(__file__).parent / "fixtures" / "github" / "api"
    monkeypatch.setenv("GITHUB_TOKEN", "ghp_test_token")
    monkeypatch.setenv("GITHUB_LIVE_MODE", "true")
    auth_provider = EnvironmentTokenProvider()
    return GitHubProvider(fixtures_dir=fixtures_dir, auth_provider=auth_provider)


def test_provider_initialization():
    """Test provider initialization with default path."""
    provider = GitHubProvider()
    assert provider.fixtures_dir.exists()


def test_list_user_prs(github_provider):
    """Test listing user PRs."""
    prs = github_provider.list_user_prs(user="testuser")

    assert isinstance(prs, list)
    assert len(prs) == 3

    # Check structure of first PR
    pr = prs[0]
    assert "repo" in pr
    assert "pr_number" in pr
    assert "title" in pr
    assert "url" in pr


def test_get_pr_details(github_provider):
    """Test getting PR details."""
    details = github_provider.get_pr_details(repo="owner/repo", pr_number=123)

    assert isinstance(details, dict)
    assert details["pr_number"] == 123
    assert details["title"] == "Add new feature X"
    assert details["repo"] == "owner/repo"
    assert "additions" in details
    assert "deletions" in details
    assert "changed_files" in details


def test_get_pr_checks(github_provider):
    """Test getting PR checks."""
    checks = github_provider.get_pr_checks(repo="owner/repo", pr_number=123)

    assert isinstance(checks, list)
    assert len(checks) == 3

    # Verify check structure
    check = checks[0]
    assert "name" in check
    assert "status" in check
    assert "conclusion" in check


def test_get_pr_reviews(github_provider):
    """Test getting PR reviews."""
    reviews = github_provider.get_pr_reviews(repo="owner/repo", pr_number=123)

    assert isinstance(reviews, list)
    assert len(reviews) == 2

    # Verify review structure
    review = reviews[0]
    assert "user" in review
    assert "state" in review
    assert "submitted_at" in review


def test_missing_fixture_raises_error(github_provider):
    """Test that missing fixture raises appropriate error."""
    with pytest.raises(FileNotFoundError):
        github_provider.get_pr_details(repo="owner/repo", pr_number=999)


class TestLiveModeToggling:
    """Tests for live mode toggling functionality."""

    def test_fixture_only_provider_always_uses_fixtures(self, fixture_only_provider):
        """FixtureOnlyProvider should always use fixtures regardless of user_id."""
        # Without user_id (fixture mode)
        prs1 = fixture_only_provider.list_user_prs(user="testuser")
        assert len(prs1) == 3

        # With user_id (should still use fixtures)
        prs2 = fixture_only_provider.list_user_prs(user="testuser", user_id="user123")
        assert len(prs2) == 3
        assert prs1 == prs2

    def test_live_mode_provider_with_user_id(self, live_mode_provider):
        """Live mode provider should attempt live mode when user_id provided."""
        # Note: Since we haven't implemented actual GitHub API calls yet,
        # this should still fall back to fixtures
        prs = live_mode_provider.list_user_prs(user="testuser", user_id="user123")
        assert len(prs) == 3  # Falls back to fixtures

    def test_live_mode_provider_without_user_id(self, live_mode_provider):
        """Live mode provider should use fixtures when no user_id provided."""
        prs = live_mode_provider.list_user_prs(user="testuser")
        assert len(prs) == 3

    def test_is_live_mode_with_fixture_only(self, fixture_only_provider):
        """_is_live_mode should return False for FixtureOnlyProvider."""
        assert fixture_only_provider._is_live_mode("user123") is False
        assert fixture_only_provider._is_live_mode(None) is False

    def test_is_live_mode_with_environment_provider(self, live_mode_provider):
        """_is_live_mode should return True when conditions are met."""
        # With user_id, should be True
        assert live_mode_provider._is_live_mode("user123") is True

        # Without user_id, should be False
        assert live_mode_provider._is_live_mode(None) is False


class TestProviderBackwardCompatibility:
    """Tests for backward compatibility with existing code."""

    def test_methods_work_without_user_id_parameter(self, github_provider):
        """All methods should work without passing user_id (backward compatible)."""
        # list_user_prs
        prs = github_provider.list_user_prs(user="testuser")
        assert len(prs) == 3

        # get_pr_details
        details = github_provider.get_pr_details(repo="owner/repo", pr_number=123)
        assert details["pr_number"] == 123

        # get_pr_checks
        checks = github_provider.get_pr_checks(repo="owner/repo", pr_number=123)
        assert len(checks) == 3

        # get_pr_reviews
        reviews = github_provider.get_pr_reviews(repo="owner/repo", pr_number=123)
        assert len(reviews) == 2
