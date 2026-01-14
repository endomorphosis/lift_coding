"""Profile configuration for context-aware responses."""

from dataclasses import dataclass
from enum import Enum


class Profile(str, Enum):
    """User context profiles affecting response verbosity and confirmation strictness."""

    WORKOUT = "workout"
    KITCHEN = "kitchen"
    COMMUTE = "commute"
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
                max_spoken_words=15,  # Very short responses
                confirmation_required=True,  # More confirmations for safety
                speech_rate=1.0,
            ),
            Profile.KITCHEN: cls(
                profile=Profile.KITCHEN,
                max_spoken_words=40,  # Step-by-step instructions
                confirmation_required=True,
                speech_rate=0.85,  # Slower for noisy environment
            ),
            Profile.COMMUTE: cls(
                profile=Profile.COMMUTE,
                max_spoken_words=30,  # Medium verbosity
                confirmation_required=False,  # Fewer interruptions
                speech_rate=1.0,
            ),
            Profile.DEFAULT: cls(
                profile=Profile.DEFAULT,
                max_spoken_words=25,
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
