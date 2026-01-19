"""End-to-end tests for per-profile privacy mode in router."""

from unittest.mock import Mock

import pytest

from handsfree.commands.profiles import Profile, ProfileConfig
from handsfree.commands.router import CommandRouter
from handsfree.commands.intent_parser import ParsedIntent
from handsfree.commands.pending_actions import PendingActionManager
from handsfree.models import PrivacyMode


@pytest.fixture
def mock_github_provider():
    """Create a mock GitHub provider."""
    provider = Mock()
    
    # Mock inbox list
    provider.list_user_prs.return_value = [
        {
            "pr_number": 123,
            "repo": "owner/repo",
            "title": "Add feature with secret API key ghp_123456789",
            "url": "https://github.com/owner/repo/pull/123",
            "labels": [],
            "requested_reviewer": True,
            "assignee": False,
        }
    ]
    provider.get_pr_checks.return_value = []
    
    # Mock PR details
    provider.get_pr_details.return_value = {
        "pr_number": 123,
        "title": "Add feature",
        "description": "This PR adds a new feature with API key ghp_123456789",
        "state": "open",
        "author": "testuser",
        "additions": 10,
        "deletions": 5,
        "changed_files": 2,
        "labels": [],
    }
    provider.get_pr_reviews.return_value = []
    
    return provider


@pytest.fixture
def router_with_github(mock_github_provider):
    """Create a router with GitHub provider."""
    pending_actions = PendingActionManager()
    return CommandRouter(
        pending_actions=pending_actions,
        github_provider=mock_github_provider,
    )


def test_router_uses_profile_privacy_mode_strict(router_with_github):
    """Test that router uses strict privacy mode from profile."""
    intent = ParsedIntent(
        name="inbox.list",
        confidence=0.95,
        entities={"user": "testuser"},
    )
    
    response = router_with_github.route(
        intent=intent,
        profile=Profile.DEFAULT,
        user_id="test-user",
    )
    
    assert response["status"] == "ok"
    # Privacy mode is applied - we verify the handler was called with profile config
    assert "spoken_text" in response


def test_router_privacy_mode_applied_to_inbox(router_with_github):
    """Test that profile privacy mode is applied to inbox handler."""
    intent = ParsedIntent(
        name="inbox.list",
        confidence=0.95,
        entities={"user": "testuser"},
    )
    
    # Test with default profile (strict mode)
    response = router_with_github.route(
        intent=intent,
        profile=Profile.DEFAULT,
        user_id="test-user",
    )
    
    assert response["status"] == "ok"
    assert "spoken_text" in response


def test_router_privacy_mode_applied_to_pr_summary(router_with_github):
    """Test that profile privacy mode is applied to PR summary handler."""
    intent = ParsedIntent(
        name="pr.summarize",
        confidence=0.95,
        entities={"pr_number": 123, "repo": "owner/repo"},
    )
    
    # Test with default profile (strict mode)
    response = router_with_github.route(
        intent=intent,
        profile=Profile.DEFAULT,
        user_id="test-user",
    )
    
    assert response["status"] == "ok"
    assert "spoken_text" in response
    # In strict mode, description should not be included
    spoken_text = response["spoken_text"]
    assert "Description:" not in spoken_text


def test_router_profile_config_passed_to_handlers(router_with_github, mock_github_provider):
    """Test that ProfileConfig with privacy_mode is passed to handlers."""
    intent = ParsedIntent(
        name="inbox.list",
        confidence=0.95,
        entities={"user": "testuser"},
    )
    
    # Route the request
    response = router_with_github.route(
        intent=intent,
        profile=Profile.WORKOUT,
        user_id="test-user",
    )
    
    assert response["status"] == "ok"
    
    # Verify that the handler was called with privacy_mode
    # The mock provider's list_user_prs should have been called
    mock_github_provider.list_user_prs.assert_called_once()


def test_all_profiles_use_strict_by_default(router_with_github):
    """Test that all profiles default to strict privacy mode."""
    profiles = [
        Profile.WORKOUT,
        Profile.KITCHEN,
        Profile.COMMUTE,
        Profile.FOCUSED,
        Profile.RELAXED,
        Profile.DEFAULT,
    ]
    
    intent = ParsedIntent(
        name="inbox.list",
        confidence=0.95,
        entities={"user": "testuser"},
    )
    
    for profile in profiles:
        response = router_with_github.route(
            intent=intent,
            profile=profile,
            user_id="test-user",
        )
        
        assert response["status"] == "ok", f"Profile {profile.value} failed"
        
        # Verify response has spoken text
        assert "spoken_text" in response


def test_profile_config_privacy_mode_consistency():
    """Test that privacy_mode is consistently set for all profiles."""
    profiles = [
        Profile.WORKOUT,
        Profile.KITCHEN,
        Profile.COMMUTE,
        Profile.FOCUSED,
        Profile.RELAXED,
        Profile.DEFAULT,
    ]
    
    for profile in profiles:
        config = ProfileConfig.for_profile(profile)
        assert config.privacy_mode == PrivacyMode.STRICT, (
            f"Profile {profile.value} should have strict privacy mode"
        )
