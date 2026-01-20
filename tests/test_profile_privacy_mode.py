"""Tests for per-profile privacy mode configuration."""

from handsfree.commands.profiles import Profile, ProfileConfig
from handsfree.models import PrivacyMode


def test_profile_config_has_privacy_mode():
    """Test that ProfileConfig includes privacy_mode field."""
    config = ProfileConfig.for_profile(Profile.DEFAULT)
    assert hasattr(config, 'privacy_mode')
    assert isinstance(config.privacy_mode, PrivacyMode)


def test_all_profiles_default_to_strict():
    """Test that all profiles default to strict privacy mode."""
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
            f"Profile {profile.value} should default to strict mode"
        )


def test_profile_config_privacy_mode_workout():
    """Test workout profile has strict privacy mode."""
    config = ProfileConfig.for_profile(Profile.WORKOUT)
    assert config.privacy_mode == PrivacyMode.STRICT


def test_profile_config_privacy_mode_kitchen():
    """Test kitchen profile has strict privacy mode."""
    config = ProfileConfig.for_profile(Profile.KITCHEN)
    assert config.privacy_mode == PrivacyMode.STRICT


def test_profile_config_privacy_mode_commute():
    """Test commute profile has strict privacy mode."""
    config = ProfileConfig.for_profile(Profile.COMMUTE)
    assert config.privacy_mode == PrivacyMode.STRICT


def test_profile_config_privacy_mode_focused():
    """Test focused profile has strict privacy mode."""
    config = ProfileConfig.for_profile(Profile.FOCUSED)
    assert config.privacy_mode == PrivacyMode.STRICT


def test_profile_config_privacy_mode_relaxed():
    """Test relaxed profile has strict privacy mode."""
    config = ProfileConfig.for_profile(Profile.RELAXED)
    assert config.privacy_mode == PrivacyMode.STRICT


def test_profile_config_privacy_mode_default():
    """Test default profile has strict privacy mode."""
    config = ProfileConfig.for_profile(Profile.DEFAULT)
    assert config.privacy_mode == PrivacyMode.STRICT


def test_profile_config_custom_privacy_mode():
    """Test that ProfileConfig can be created with custom privacy mode."""
    # Create a custom config with balanced mode
    config = ProfileConfig(
        profile=Profile.DEFAULT,
        max_spoken_words=25,
        confirmation_required=False,
        speech_rate=1.0,
        max_summary_sentences=4,
        max_inbox_items=5,
        detail_level="moderate",
        privacy_mode=PrivacyMode.BALANCED,
    )
    
    assert config.privacy_mode == PrivacyMode.BALANCED


def test_profile_config_debug_privacy_mode():
    """Test that ProfileConfig can be created with debug mode."""
    # Create a custom config with debug mode
    config = ProfileConfig(
        profile=Profile.RELAXED,
        max_spoken_words=100,
        confirmation_required=False,
        speech_rate=0.95,
        max_summary_sentences=10,
        max_inbox_items=10,
        detail_level="detailed",
        privacy_mode=PrivacyMode.DEBUG,
    )
    
    assert config.privacy_mode == PrivacyMode.DEBUG
