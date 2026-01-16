"""TTS (Text-to-Speech) module for HandsFree Dev Companion."""

import logging
import os

from handsfree.tts.provider import TTSProvider
from handsfree.tts.stub_provider import StubTTSProvider

logger = logging.getLogger(__name__)

__all__ = ["TTSProvider", "StubTTSProvider", "get_tts_provider"]


def get_tts_provider() -> TTSProvider:
    """Get the configured TTS provider.

    Returns the appropriate TTS provider based on environment configuration:
    - If HANDSFREE_TTS_PROVIDER=stub or unset: returns StubTTSProvider (default)
    - If HANDSFREE_TTS_PROVIDER=openai: returns OpenAITTSProvider (if configured)

    Returns:
        A TTSProvider instance

    Environment variables:
        HANDSFREE_TTS_PROVIDER: Provider type (default: "stub", options: "stub", "openai")
        OPENAI_API_KEY: Required for openai provider
    """
    provider_type = os.environ.get("HANDSFREE_TTS_PROVIDER", "stub").lower()

    if provider_type == "stub":
        return StubTTSProvider()
    elif provider_type == "openai":
        # Only import OpenAI provider if requested (requires optional dependency)
        try:
            from handsfree.tts.openai_provider import OpenAITTSProvider

            return OpenAITTSProvider()
        except ImportError:
            logger.error(
                "OpenAI TTS provider requested but openai package not installed. "
                "Install with: pip install 'handsfree-dev-companion[openai]'"
            )
            logger.warning("Falling back to stub TTS provider")
            return StubTTSProvider()
        except Exception as e:
            logger.error("Failed to initialize OpenAI TTS provider: %s", e)
            logger.warning("Falling back to stub TTS provider")
            return StubTTSProvider()
    else:
        # Unknown provider - fall back to stub
        logger.warning("Unknown TTS provider '%s', falling back to stub", provider_type)
        return StubTTSProvider()
