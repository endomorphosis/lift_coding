"""Profile configuration for context-aware responses."""

import re
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
    max_summary_sentences: int  # Maximum sentences in summaries
    max_inbox_items: int  # Maximum items to return in inbox listing
    detail_level: str  # "minimal", "brief", "moderate", "detailed"

    @classmethod
    def for_profile(cls, profile: Profile) -> "ProfileConfig":
        """Get configuration for the given profile."""
        configs = {
            Profile.WORKOUT: cls(
                profile=Profile.WORKOUT,
                max_spoken_words=15,  # Very short responses
                confirmation_required=True,  # More confirmations for safety
                speech_rate=1.0,
                max_summary_sentences=2,  # Ultra-brief: 1-2 sentences max
                max_inbox_items=3,  # Only top 3 items
                detail_level="minimal",  # Key numbers only
            ),
            Profile.KITCHEN: cls(
                profile=Profile.KITCHEN,
                max_spoken_words=40,  # Step-by-step instructions
                confirmation_required=True,
                speech_rate=0.85,  # Slower for noisy environment
                max_summary_sentences=4,  # Moderate: 3-4 sentences
                max_inbox_items=5,
                detail_level="moderate",  # Conversational
            ),
            Profile.COMMUTE: cls(
                profile=Profile.COMMUTE,
                max_spoken_words=30,  # Medium verbosity
                confirmation_required=False,  # Fewer interruptions
                speech_rate=1.0,
                max_summary_sentences=3,  # Brief: 2-3 sentences
                max_inbox_items=5,
                detail_level="brief",  # Essential info
            ),
            Profile.FOCUSED: cls(
                profile=Profile.FOCUSED,
                max_spoken_words=20,  # Brief, actionable
                confirmation_required=False,  # Minimal interruption
                speech_rate=1.0,
                max_summary_sentences=2,  # Minimal interruption
                max_inbox_items=3,  # Only actionable items
                detail_level="minimal",  # Brief, actionable items only
            ),
            Profile.RELAXED: cls(
                profile=Profile.RELAXED,
                max_spoken_words=100,  # Full detail
                confirmation_required=False,
                speech_rate=1.0,
                max_summary_sentences=10,  # Detailed: full context
                max_inbox_items=10,  # More items
                detail_level="detailed",  # All details
            ),
            Profile.DEFAULT: cls(
                profile=Profile.DEFAULT,
                max_spoken_words=25,
                confirmation_required=False,
                speech_rate=1.0,
                max_summary_sentences=4,  # Moderate: balanced detail
                max_inbox_items=5,
                detail_level="moderate",  # Balanced detail
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

    def truncate_summary(self, text: str) -> str:
        """Truncate summary text to respect max_summary_sentences limit.

        Splits by sentence boundaries (. ! ?) and keeps first N sentences.
        Always preserves critical information like "security alert" or "failing".

        Args:
            text: The summary text to truncate

        Returns:
            Truncated summary with up to max_summary_sentences
        """
        if not text:
            return text

        # Simple sentence splitting by . ! ?
        sentences = re.split(r"(?<=[.!?])\s+", text)

        # Check for critical keywords that should always be included
        critical_keywords = ["security", "alert", "failing", "failed", "error", "critical"]
        has_critical = any(keyword in text.lower() for keyword in critical_keywords)

        # If we have critical info, ensure at least the first sentence with critical info is included
        if has_critical and len(sentences) > self.max_summary_sentences:
            critical_sentences = []
            other_sentences = []

            for sentence in sentences:
                if any(keyword in sentence.lower() for keyword in critical_keywords):
                    critical_sentences.append(sentence)
                else:
                    other_sentences.append(sentence)

            # Include all critical sentences plus fill up to max with others
            result_sentences = critical_sentences[:]
            remaining_slots = self.max_summary_sentences - len(critical_sentences)
            if remaining_slots > 0:
                result_sentences.extend(other_sentences[:remaining_slots])

            return " ".join(result_sentences)

        # No critical info, just truncate normally
        if len(sentences) <= self.max_summary_sentences:
            return text

        return " ".join(sentences[: self.max_summary_sentences])

    def filter_inbox_items(self, items: list[dict]) -> list[dict]:
        """Filter inbox items based on profile's max_inbox_items limit.

        For FOCUSED profile, prioritize actionable items (review requests, failures).
        For other profiles, just limit the count.

        Args:
            items: List of inbox item dictionaries

        Returns:
            Filtered list of items
        """
        if not items:
            return items

        # FOCUSED profile: prioritize actionable items
        if self.profile == Profile.FOCUSED:
            # Separate actionable from informational
            actionable = []
            informational = []

            for item in items:
                # Determine if actionable based on type or status
                is_actionable = (
                    item.get("requested_reviewer", False)
                    or item.get("assignee", False)
                    or "failing" in str(item.get("title", "")).lower()
                    or "failed" in str(item.get("title", "")).lower()
                    or any(label in ["bug", "security"] for label in item.get("labels", []))
                )

                if is_actionable:
                    actionable.append(item)
                else:
                    informational.append(item)

            # Return actionable items first, up to max_inbox_items
            result = actionable[:self.max_inbox_items]
            remaining_slots = self.max_inbox_items - len(result)
            if remaining_slots > 0:
                result.extend(informational[:remaining_slots])
            return result

        # Other profiles: just limit count
        return items[: self.max_inbox_items]
