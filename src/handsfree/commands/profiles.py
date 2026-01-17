"""Profile configuration for context-aware responses."""

from dataclasses import dataclass
from enum import Enum


class Profile(str, Enum):
    """User context profiles affecting response verbosity and confirmation strictness."""

    WORKOUT = "workout"
    KITCHEN = "kitchen"
    COMMUTE = "commute"
    FOCUSED = "focused"
    RELAXED = "relaxed"
    DEFAULT = "default"


@dataclass
class ProfileConfig:
    """Configuration settings for each profile."""

    profile: Profile
    max_spoken_words: int
    confirmation_required: bool
    speech_rate: float  # multiplier: 1.0 = normal, 0.8 = slower, 1.2 = faster

    @classmethod
    def for_profile(cls, profile: Profile) -> "ProfileConfig":
        """Get configuration for the given profile."""
        configs = {
            Profile.WORKOUT: cls(
                profile=Profile.WORKOUT,
                max_spoken_words=15,  # Ultra-brief: 1-2 sentences max
                confirmation_required=True,  # More confirmations for safety
                speech_rate=1.0,
            ),
            Profile.KITCHEN: cls(
                profile=Profile.KITCHEN,
                max_spoken_words=40,  # Moderate: 3-4 sentences, conversational
                confirmation_required=True,
                speech_rate=0.85,  # Slower for noisy environment
            ),
            Profile.COMMUTE: cls(
                profile=Profile.COMMUTE,
                max_spoken_words=30,  # Brief: 2-3 sentences, essential info
                confirmation_required=False,  # Fewer interruptions
                speech_rate=1.0,
            ),
            Profile.FOCUSED: cls(
                profile=Profile.FOCUSED,
                max_spoken_words=20,  # Minimal interruption: brief, actionable items only
                confirmation_required=False,  # No interruptions
                speech_rate=1.1,  # Slightly faster
            ),
            Profile.RELAXED: cls(
                profile=Profile.RELAXED,
                max_spoken_words=100,  # Detailed: full context, all details
                confirmation_required=False,  # No rush
                speech_rate=0.95,  # Slightly slower for comprehension
            ),
            Profile.DEFAULT: cls(
                profile=Profile.DEFAULT,
                max_spoken_words=25,  # Moderate: balanced detail
                confirmation_required=False,
                speech_rate=1.0,
            ),
        }
        return configs[profile]

    def truncate_spoken_text(self, text: str) -> str:
        """Truncate spoken text to respect max_spoken_words limit.

        Uses word-based truncation for deterministic, stable behavior.

        Args:
            text: The spoken text to truncate

        Returns:
            Truncated text, ending with "..." if truncated
        """
        if not text:
            return text

        words = text.split()
        if len(words) <= self.max_spoken_words:
            return text

        # Truncate to max words and add ellipsis
        truncated_words = words[: self.max_spoken_words]
        return " ".join(truncated_words) + "..."
