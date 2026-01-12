"""Tests for profile configuration."""

from handsfree.commands.profiles import Profile, ProfileConfig


class TestProfile:
    """Test Profile enum."""

    def test_profile_values(self) -> None:
        """Test that all expected profiles exist."""
        assert Profile.WORKOUT.value == "workout"
        assert Profile.KITCHEN.value == "kitchen"
        assert Profile.COMMUTE.value == "commute"
        assert Profile.DEFAULT.value == "default"


class TestProfileConfig:
    """Test ProfileConfig settings."""

    def test_workout_profile(self) -> None:
        """Test workout profile configuration."""
        config = ProfileConfig.for_profile(Profile.WORKOUT)

        assert config.profile == Profile.WORKOUT
        assert config.max_spoken_words == 15  # Very short
        assert config.confirmation_required is True  # More confirmations
        assert config.speech_rate == 1.0

    def test_kitchen_profile(self) -> None:
        """Test kitchen profile configuration."""
        config = ProfileConfig.for_profile(Profile.KITCHEN)

        assert config.profile == Profile.KITCHEN
        assert config.max_spoken_words == 40  # Step-by-step
        assert config.confirmation_required is True
        assert config.speech_rate == 0.85  # Slower

    def test_commute_profile(self) -> None:
        """Test commute profile configuration."""
        config = ProfileConfig.for_profile(Profile.COMMUTE)

        assert config.profile == Profile.COMMUTE
        assert config.max_spoken_words == 30  # Medium
        assert config.confirmation_required is False  # Fewer interruptions
        assert config.speech_rate == 1.0

    def test_default_profile(self) -> None:
        """Test default profile configuration."""
        config = ProfileConfig.for_profile(Profile.DEFAULT)

        assert config.profile == Profile.DEFAULT
        assert config.max_spoken_words == 25
        assert config.confirmation_required is False
        assert config.speech_rate == 1.0

    def test_all_profiles_have_config(self) -> None:
        """Test that all profiles have configurations."""
        for profile in Profile:
            config = ProfileConfig.for_profile(profile)
            assert config.profile == profile
            assert config.max_spoken_words > 0
            assert isinstance(config.confirmation_required, bool)
            assert config.speech_rate > 0
