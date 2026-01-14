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


def get_stt_provider() -> STTProvider:
    """Get the configured STT provider.

    Returns the appropriate STT provider based on environment configuration:
    - If HANDS_FREE_STT_PROVIDER=stub or unset: returns StubSTTProvider
    - If HANDS_FREE_STT_PROVIDER=openai: returns OpenAISTTProvider (if configured)
    - If HANDSFREE_STT_ENABLED=false: returns disabled StubSTTProvider

    Returns:
        An STTProvider instance

    Environment variables:
        HANDS_FREE_STT_PROVIDER: Provider type (default: "stub", options: "stub", "openai")
        HANDSFREE_STT_ENABLED: Whether STT is enabled (default: "true")
        OPENAI_API_KEY: Required for openai provider
    """
    provider_type = os.environ.get("HANDS_FREE_STT_PROVIDER", "stub").lower()
    enabled = os.environ.get("HANDSFREE_STT_ENABLED", "true").lower() in (
        "true",
        "1",
        "yes",
    )

    if provider_type == "stub":
        from handsfree.stt.stub_provider import StubSTTProvider

        return StubSTTProvider(enabled=enabled)
    elif provider_type == "openai":
        # Only import OpenAI provider if requested (requires optional dependency)
        try:
            from handsfree.stt.openai_provider import OpenAISTTProvider

            return OpenAISTTProvider()
        except ImportError:
            logger.error(
                "OpenAI STT provider requested but openai package not installed. "
                "Install with: pip install 'handsfree-dev-companion[openai]'"
            )
            logger.warning("Falling back to stub STT provider")
            from handsfree.stt.stub_provider import StubSTTProvider

            return StubSTTProvider(enabled=enabled)
        except Exception as e:
            logger.error("Failed to initialize OpenAI STT provider: %s", e)
            logger.warning("Falling back to stub STT provider")
            from handsfree.stt.stub_provider import StubSTTProvider

            return StubSTTProvider(enabled=enabled)
    else:
        # Unknown provider - fall back to stub
        logger.warning("Unknown STT provider '%s', falling back to stub", provider_type)
        from handsfree.stt.stub_provider import StubSTTProvider

        return StubSTTProvider(enabled=enabled)
