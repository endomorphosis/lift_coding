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


class TestProfileTruncation:
    """Test profile-based spoken text truncation."""

    def test_truncate_within_limit(self) -> None:
        """Test that text within limit is not truncated."""
        config = ProfileConfig.for_profile(Profile.WORKOUT)
        text = "This is a short message"  # 5 words
        result = config.truncate_spoken_text(text)
        assert result == text
        assert "..." not in result

    def test_truncate_exceeds_limit(self) -> None:
        """Test that text exceeding limit is truncated."""
        config = ProfileConfig.for_profile(Profile.WORKOUT)  # 15 words max
        # Create a 20-word text
        text = " ".join([f"word{i}" for i in range(20)])
        result = config.truncate_spoken_text(text)

        # Should have exactly 15 words plus "..."
        words = result.replace("...", "").split()
        assert len(words) == 15
        assert result.endswith("...")

    def test_truncate_exactly_at_limit(self) -> None:
        """Test that text exactly at limit is not truncated."""
        config = ProfileConfig.for_profile(Profile.WORKOUT)  # 15 words max
        # Create a 15-word text
        text = " ".join([f"word{i}" for i in range(15)])
        result = config.truncate_spoken_text(text)

        assert result == text
        assert "..." not in result

    def test_truncate_empty_text(self) -> None:
        """Test that empty text is handled correctly."""
        config = ProfileConfig.for_profile(Profile.WORKOUT)
        assert config.truncate_spoken_text("") == ""
        assert config.truncate_spoken_text("   ") == "   "

    def test_truncate_workout_vs_default(self) -> None:
        """Test that workout profile truncates more aggressively than default."""
        workout_config = ProfileConfig.for_profile(Profile.WORKOUT)  # 15 words
        default_config = ProfileConfig.for_profile(Profile.DEFAULT)  # 25 words

        # Create a 30-word text
        text = " ".join([f"word{i}" for i in range(30)])

        workout_result = workout_config.truncate_spoken_text(text)
        default_result = default_config.truncate_spoken_text(text)

        # Both should be truncated
        assert "..." in workout_result
        assert "..." in default_result

        # Workout should be shorter
        workout_words = len(workout_result.replace("...", "").split())
        default_words = len(default_result.replace("...", "").split())
        assert workout_words < default_words
        assert workout_words == 15
        assert default_words == 25

    def test_truncate_preserves_word_boundaries(self) -> None:
        """Test that truncation preserves complete words."""
        config = ProfileConfig.for_profile(Profile.WORKOUT)  # 15 words max
        text = (
            "The quick brown fox jumps over the lazy dog and runs through "
            "the forest quickly to escape from danger"
        )
        result = config.truncate_spoken_text(text)

        # Should have complete words, no partial words
        words = result.replace("...", "").strip().split()
        assert len(words) == 15
        # First 15 words should match
        original_words = text.split()
        for i, word in enumerate(words):
            assert word == original_words[i]
