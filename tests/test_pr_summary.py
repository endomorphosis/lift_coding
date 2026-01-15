"""Tests for PR summary handler."""

from pathlib import Path

import pytest

from handsfree.github import GitHubProvider
from handsfree.handlers import handle_pr_summarize


@pytest.fixture
def github_provider():
    """Create a GitHub provider with test fixtures."""
    fixtures_dir = Path(__file__).parent / "fixtures" / "github" / "api"
    return GitHubProvider(fixtures_dir=fixtures_dir)


def test_pr_summarize_basic(github_provider):
    """Test basic PR summarization."""
    result = handle_pr_summarize(github_provider, repo="owner/repo", pr_number=123)

    assert "pr_number" in result
    assert "title" in result
    assert "spoken_text" in result
    assert result["pr_number"] == 123
    assert "feature X" in result["title"]


def test_pr_summarize_spoken_text_passing_checks(github_provider):
    """Test spoken text output for PR with passing checks (golden test)."""
    result = handle_pr_summarize(github_provider, repo="owner/repo", pr_number=123)

    # Golden output test - this should be stable
    expected_spoken = (
        "PR 123: Add new feature X. By contributor. "
        "12 files changed, 450 additions, 120 deletions. "
        "All 3 checks passing. Reviews: 1 approved. "
        "Latest review: APPROVED by reviewer2."
    )

    assert result["spoken_text"] == expected_spoken


def test_pr_summarize_spoken_text_failing_checks(github_provider):
    """Test spoken text output for PR with failing checks (golden test)."""
    result = handle_pr_summarize(github_provider, repo="owner/repo", pr_number=124)

    # Golden output test - this should be stable
    expected_spoken = (
        "PR 124: Fix critical bug in authentication. By security-team. "
        "3 files changed, 85 additions, 42 deletions. "
        "Checks: 1 failing, 2 passing. Reviews: 1 requested changes. "
        "Latest review: CHANGES_REQUESTED by security-lead. "
        "Labels: bug, urgent, security."
    )

    assert result["spoken_text"] == expected_spoken


def test_pr_summary_structure(github_provider):
    """Test PR summary has correct structure."""
    result = handle_pr_summarize(github_provider, repo="owner/repo", pr_number=123)

    # Verify all required fields
    assert "pr_number" in result
    assert "title" in result
    assert "state" in result
    assert "author" in result
    assert "additions" in result
    assert "deletions" in result
    assert "changed_files" in result
    assert "labels" in result
    assert "checks" in result
    assert "reviews" in result
    assert "spoken_text" in result

    # Verify nested structures
    checks = result["checks"]
    assert "total" in checks
    assert "passed" in checks
    assert "failed" in checks
    assert "pending" in checks

    reviews = result["reviews"]
    assert "total" in reviews
    assert "approved" in reviews
    assert "changes_requested" in reviews
    assert "commented" in reviews


def test_pr_summary_privacy_mode(github_provider):
    """Test that privacy mode is respected (no code snippets)."""
    result = handle_pr_summarize(
        github_provider, repo="owner/repo", pr_number=123, privacy_mode=True
    )

    # Verify no code snippets in spoken text
    spoken = result["spoken_text"]
    assert "```" not in spoken
    # In privacy mode, description is not included
    assert "improves the user experience" not in spoken


def test_pr_summary_checks_analysis(github_provider):
    """Test check runs analysis."""
    result = handle_pr_summarize(github_provider, repo="owner/repo", pr_number=123)

    checks = result["checks"]
    assert checks["total"] == 3
    assert checks["passed"] == 3
    assert checks["failed"] == 0
    assert checks["pending"] == 0


def test_pr_summary_failing_checks_analysis(github_provider):
    """Test check runs analysis with failures."""
    result = handle_pr_summarize(github_provider, repo="owner/repo", pr_number=124)

    checks = result["checks"]
    assert checks["total"] == 3
    assert checks["passed"] == 2
    assert checks["failed"] == 1
    assert checks["pending"] == 0


def test_pr_summary_reviews_analysis(github_provider):
    """Test reviews analysis."""
    result = handle_pr_summarize(github_provider, repo="owner/repo", pr_number=123)

    reviews = result["reviews"]
    assert reviews["total"] == 2
    assert reviews["approved"] == 1
    assert reviews["changes_requested"] == 0
    assert reviews["commented"] == 1


def test_pr_summary_changes_requested_reviews(github_provider):
    """Test reviews analysis with changes requested."""
    result = handle_pr_summarize(github_provider, repo="owner/repo", pr_number=124)

    reviews = result["reviews"]
    assert reviews["total"] == 1
    assert reviews["approved"] == 0
    assert reviews["changes_requested"] == 1
    assert reviews["commented"] == 0


def test_pr_summary_diff_stats(github_provider):
    """Test diff statistics are included."""
    result = handle_pr_summarize(github_provider, repo="owner/repo", pr_number=123)

    assert result["additions"] == 450
    assert result["deletions"] == 120
    assert result["changed_files"] == 12

    # Verify in spoken text
    spoken = result["spoken_text"]
    assert "12 files" in spoken
    assert "450 additions" in spoken
    assert "120 deletions" in spoken


def test_pr_summary_mixed_reviews(github_provider):
    """Test that mixed reviews (both approved and changes requested) are reported."""
    result = handle_pr_summarize(github_provider, repo="owner/repo", pr_number=125)

    reviews = result["reviews"]
    assert reviews["total"] == 3
    assert reviews["approved"] == 2
    assert reviews["changes_requested"] == 1

    # Verify both types are mentioned in spoken text
    spoken = result["spoken_text"]
    assert "1 requested changes" in spoken
    assert "2 approved" in spoken


def test_pr_summary_latest_review(github_provider):
    """Test that the latest review is identified and reported correctly."""
    result = handle_pr_summarize(github_provider, repo="owner/repo", pr_number=125)

    # PR 125 has 3 reviews:
    # - reviewer1: CHANGES_REQUESTED at 2026-01-12T12:00:00Z
    # - reviewer2: APPROVED at 2026-01-12T13:00:00Z
    # - reviewer3: APPROVED at 2026-01-12T13:30:00Z (latest)
    spoken = result["spoken_text"]
    assert "Latest review: APPROVED by reviewer3" in spoken


def test_pr_summary_no_reviews(github_provider):
    """Test PR summary when there are no reviews."""
    # Create a custom fixture scenario with no reviews
    from handsfree.handlers.pr_summary import _get_latest_review

    # Test with empty list
    latest = _get_latest_review([])
    assert latest is None

    # Test with reviews missing timestamps (edge case)
    reviews_no_timestamp = [
        {"user": "reviewer1", "state": "APPROVED"},
        {"user": "reviewer2", "state": "COMMENTED"},
    ]
    latest = _get_latest_review(reviews_no_timestamp)
    # Should return first review if none have timestamps
    assert latest is not None
    assert latest["user"] == "reviewer1"
