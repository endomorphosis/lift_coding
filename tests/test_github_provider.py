"""Tests for GitHub provider."""

from pathlib import Path

import pytest

from handsfree.github import GitHubProvider


@pytest.fixture
def github_provider():
    """Create a GitHub provider with test fixtures."""
    fixtures_dir = Path(__file__).parent / "fixtures" / "github" / "api"
    return GitHubProvider(fixtures_dir=fixtures_dir)


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
