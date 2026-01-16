"""OpenAI TTS provider implementation.

This provider uses OpenAI's Text-to-Speech API for speech synthesis.
It requires the openai package to be installed and an API key to be configured.
"""

import logging
import os

from handsfree.tts.provider import TTSProvider

logger = logging.getLogger(__name__)

# Try to import openai - if not available, class instantiation will fail with helpful error
try:
    import openai

    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False
    openai = None  # type: ignore


class OpenAITTSProvider(TTSProvider):
    """OpenAI TTS provider with error handling and fallback support."""

    # Supported audio formats per OpenAI TTS API
    # https://platform.openai.com/docs/guides/text-to-speech
    SUPPORTED_FORMATS = ["mp3", "opus", "aac", "flac", "wav", "pcm"]

    # Available voices
    AVAILABLE_VOICES = ["alloy", "echo", "fable", "onyx", "nova", "shimmer"]

    def __init__(
        self,
        api_key: str | None = None,
        model: str | None = None,
        timeout: float = 30.0,
    ):
        """Initialize OpenAI TTS provider.

        Args:
            api_key: OpenAI API key (defaults to OPENAI_API_KEY env var)
            model: TTS model to use (defaults to OPENAI_TTS_MODEL env var or "tts-1")
            timeout: Request timeout in seconds (default: 30)

        Raises:
            ValueError: If OpenAI API key is not configured
            ImportError: If openai package is not installed
        """
        if not OPENAI_AVAILABLE or openai is None:
            raise ImportError(
                "OpenAI package not installed. "
                "Install with: pip install 'handsfree-dev-companion[openai]'"
            )

        # Get API key from parameter or environment
        self.api_key = api_key or os.environ.get("OPENAI_API_KEY")
        if not self.api_key:
            raise ValueError(
                "OPENAI_API_KEY environment variable is required for OpenAI TTS provider"
            )

        # Initialize OpenAI client
        self.client = openai.OpenAI(api_key=self.api_key)

        # Configuration
        self.model = model or os.environ.get("OPENAI_TTS_MODEL", "tts-1")
        self.timeout = float(os.environ.get("HANDSFREE_TTS_TIMEOUT", str(timeout)))
        self.default_voice = os.environ.get("OPENAI_TTS_VOICE", "alloy")

        logger.info(
            "Initialized OpenAI TTS provider: model=%s, default_voice=%s, timeout=%s",
            self.model,
            self.default_voice,
            self.timeout,
        )

    def synthesize(
        self,
        text: str,
        voice: str | None = None,
        format: str = "wav",
    ) -> tuple[bytes, str]:
        """Synthesize speech from text using OpenAI TTS API.

        Args:
            text: Text to convert to speech
            voice: Optional voice identifier (uses default if not provided)
            format: Audio format (mp3, opus, aac, flac, wav, pcm)

        Returns:
            Tuple of (audio_bytes, content_type)

        Raises:
            ValueError: If text is empty or format is unsupported
            RuntimeError: If synthesis fails
        """
        # Validate text
        if not text or not text.strip():
            raise ValueError("Text cannot be empty")

        # Validate and normalize format
        format_lower = format.lower()
        if format_lower not in self.SUPPORTED_FORMATS:
            logger.warning(
                "Unsupported format '%s', falling back to 'mp3'. Supported: %s",
                format,
                ", ".join(self.SUPPORTED_FORMATS),
            )
            format_lower = "mp3"

        # Select voice (use provided voice, or default)
        selected_voice = voice or self.default_voice
        if selected_voice not in self.AVAILABLE_VOICES:
            logger.warning(
                "Unknown voice '%s', using default '%s'. Available: %s",
                selected_voice,
                self.default_voice,
                ", ".join(self.AVAILABLE_VOICES),
            )
            selected_voice = self.default_voice

        logger.info(
            "Synthesizing speech: text_length=%d, voice=%s, format=%s",
            len(text),
            selected_voice,
            format_lower,
        )

        try:
            # Call OpenAI TTS API
            response = self.client.audio.speech.create(
                model=self.model,
                voice=selected_voice,
                input=text,
                response_format=format_lower,
                timeout=self.timeout,
            )

            # Read the audio content
            audio_bytes = response.content

            # Determine content type
            content_type = self._get_content_type(format_lower)

            logger.info(
                "Successfully synthesized speech: size=%d bytes",
                len(audio_bytes),
            )

            return audio_bytes, content_type

        except Exception as e:
            error_msg = f"TTS synthesis failed: {str(e)}"
            logger.error(error_msg)
            raise RuntimeError(error_msg) from e

    def _get_content_type(self, format: str) -> str:
        """Get the MIME content type for an audio format.

        Args:
            format: Audio format

        Returns:
            MIME content type string
        """
        content_type_map = {
            "mp3": "audio/mpeg",
            "opus": "audio/opus",
            "aac": "audio/aac",
            "flac": "audio/flac",
            "wav": "audio/wav",
            "pcm": "audio/pcm",
        }
        return content_type_map.get(format, "audio/mpeg")
