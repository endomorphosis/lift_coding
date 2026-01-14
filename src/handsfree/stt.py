"""Speech-to-Text (STT) abstraction layer.

Provides an interface for STT providers with a safe stub implementation for CI/dev.
"""

import logging
import os
from typing import Protocol

logger = logging.getLogger(__name__)


class STTProvider(Protocol):
    """Protocol for STT providers."""

    def transcribe(self, audio_data: bytes, format: str) -> str:
        """Transcribe audio data to text.

        Args:
            audio_data: Raw audio data bytes
            format: Audio format (wav, m4a, mp3, opus)

        Returns:
            Transcribed text

        Raises:
            NotImplementedError: If STT is not enabled/available
            ValueError: If audio format is unsupported
        """
        ...


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

        # Return deterministic transcript based on audio data hash
        # This allows tests to be predictable while still being somewhat realistic
        data_hash = hash(audio_data) % 1000

        # Map hash to common test commands
        if data_hash < 200:
            return "show my inbox"
        elif data_hash < 400:
            return "summarize PR 42"
        elif data_hash < 600:
            return "request review from alice on PR 100"
        elif data_hash < 800:
            return "what is the status of my agent tasks"
        else:
            return "list my pull requests"


def get_stt_provider() -> STTProvider:
    """Get the configured STT provider.

    Returns the appropriate STT provider based on environment configuration:
    - If HANDSFREE_STT_PROVIDER=stub or unset: returns StubSTTProvider
    - If HANDSFREE_STT_ENABLED=false: returns disabled StubSTTProvider
    - Future: Support for real providers (whisper, google, azure, etc.)

    Returns:
        An STTProvider instance

    Environment variables:
        HANDSFREE_STT_PROVIDER: Provider type (default: "stub")
        HANDSFREE_STT_ENABLED: Whether STT is enabled (default: "true")
    """
    provider_type = os.environ.get("HANDSFREE_STT_PROVIDER", "stub").lower()
    enabled = os.environ.get("HANDSFREE_STT_ENABLED", "true").lower() in (
        "true",
        "1",
        "yes",
    )

    if provider_type == "stub":
        return StubSTTProvider(enabled=enabled)
    else:
        # Future: Support other providers
        logger.warning("Unknown STT provider '%s', falling back to stub", provider_type)
        return StubSTTProvider(enabled=enabled)
