"""Tests for GitHub inbox handler."""

from pathlib import Path

import pytest

from handsfree.github import GitHubProvider
from handsfree.handlers import handle_inbox_list


@pytest.fixture
def github_provider():
    """Create a GitHub provider with test fixtures."""
    fixtures_dir = Path(__file__).parent / "fixtures" / "github" / "api"
    return GitHubProvider(fixtures_dir=fixtures_dir)


def test_inbox_list_basic(github_provider):
    """Test basic inbox listing."""
    result = handle_inbox_list(github_provider, user="testuser")

    assert "items" in result
    assert "spoken_text" in result
    assert len(result["items"]) == 3


def test_inbox_list_spoken_text(github_provider):
    """Test spoken text output for inbox (golden test)."""
    result = handle_inbox_list(github_provider, user="testuser")

    # Golden output test - this should be stable
    # Items are sorted by priority (highest first), then by updated_at (most recent first)
    expected_spoken = (
        "You have 3 items in your inbox. 1 high priority. "
        "1. Fix critical bug in authentication in repo. "
        "2. Update documentation for API v2 in other-repo. "
        "3. Add new feature X in repo."
    )

    assert result["spoken_text"] == expected_spoken


def test_inbox_items_structure(github_provider):
    """Test inbox items have correct structure."""
    result = handle_inbox_list(github_provider, user="testuser")

    for item in result["items"]:
        assert "type" in item
        assert "title" in item
        assert "priority" in item
        assert "repo" in item
        assert "url" in item
        assert "summary" in item
        assert item["type"] in ["pr", "mention", "check", "agent"]
        assert 1 <= item["priority"] <= 5


def test_inbox_priority_ordering(github_provider):
    """Test that items are sorted by priority."""
    result = handle_inbox_list(github_provider, user="testuser")

    items = result["items"]
    # First item should be highest priority (PR 124 with urgent + security labels)
    assert items[0]["priority"] == 5
    assert "authentication" in items[0]["title"].lower()

    # Priority should be non-increasing
    for i in range(len(items) - 1):
        assert items[i]["priority"] >= items[i + 1]["priority"]


def test_inbox_privacy_mode(github_provider):
    """Test that privacy mode is respected (no code snippets)."""
    result = handle_inbox_list(github_provider, user="testuser", privacy_mode=True)

    # Verify no code snippets in spoken text
    spoken = result["spoken_text"]
    assert "```" not in spoken
    assert "function" not in spoken.lower()
    assert "class" not in spoken.lower()

    # Verify no code in item summaries
    for item in result["items"]:
        assert "```" not in item["summary"]
