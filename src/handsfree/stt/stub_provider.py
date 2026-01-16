"""Stub STT provider that returns deterministic responses for testing.

This is the default implementation used in CI and dev environments.
It doesn't require any external dependencies or API keys.
"""

import logging

logger = logging.getLogger(__name__)


class StubSTTProvider:
    """Stub STT provider that returns deterministic responses for testing.

    This is the default implementation used in CI and dev environments.
    It doesn't require any external dependencies or API keys.
    """

    def __init__(self, enabled: bool = True):
        """Initialize stub STT provider.

        Args:
            enabled: Whether STT is enabled. If False, raises NotImplementedError.
        """
        self.enabled = enabled

    def transcribe(self, audio_data: bytes, format: str) -> str:
        """Return a deterministic transcript for testing.

        Args:
            audio_data: Raw audio data bytes (analyzed for deterministic response)
            format: Audio format (wav, m4a, mp3, opus)

        Returns:
            Deterministic transcript based on audio data

        Raises:
            NotImplementedError: If STT is disabled
            ValueError: If format is unsupported
        """
        if not self.enabled:
            raise NotImplementedError(
                "Audio STT is disabled. Set HANDSFREE_STT_ENABLED=true to enable."
            )

        # Validate format
        supported_formats = ["wav", "m4a", "mp3", "opus"]
        if format not in supported_formats:
            raise ValueError(
                f"Unsupported audio format: {format}. "
                f"Supported formats: {', '.join(supported_formats)}"
            )

        # Always return a known, parseable command.
        # Python's built-in hash() is intentionally randomized per process, and some
        # plausible transcripts may not map to a supported intent. Keeping this
        # stable prevents flaky integration tests.
        return "show my inbox"
