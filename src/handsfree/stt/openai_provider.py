"""OpenAI Whisper STT provider implementation.

This provider uses OpenAI's Whisper API for speech-to-text transcription.
It requires the openai package to be installed and an API key to be configured.
"""

import logging
import os
import tempfile
import time

logger = logging.getLogger(__name__)

# Try to import openai - if not available, class instantiation will fail with helpful error
try:
    import openai
    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False
    openai = None  # type: ignore


class OpenAISTTProvider:
    """OpenAI Whisper STT provider with timeouts, retries, and error handling."""

    # Supported audio formats per OpenAI Whisper API
    # https://platform.openai.com/docs/guides/speech-to-text
    SUPPORTED_FORMATS = ["wav", "m4a", "mp3", "opus", "flac", "webm"]
    
    # Max file size: 25MB per OpenAI docs
    MAX_FILE_SIZE = 25 * 1024 * 1024  # 25MB in bytes
    
    def __init__(
        self,
        api_key: str | None = None,
        timeout: float = 30.0,
        max_retries: int = 3,
    ):
        """Initialize OpenAI STT provider.

        Args:
            api_key: OpenAI API key (defaults to OPENAI_API_KEY env var)
            timeout: Request timeout in seconds (default: 30)
            max_retries: Maximum number of retry attempts (default: 3)

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
                "OPENAI_API_KEY environment variable is required for OpenAI STT provider"
            )

        # Initialize OpenAI client
        self.client = openai.OpenAI(api_key=self.api_key)
        
        # Configuration
        self.model = os.environ.get("OPENAI_STT_MODEL", "whisper-1")
        self.timeout = float(os.environ.get("HANDS_FREE_STT_TIMEOUT", str(timeout)))
        self.max_retries = int(os.environ.get("HANDS_FREE_STT_MAX_RETRIES", str(max_retries)))
        self.retry_delay = 2.0  # Base retry delay in seconds

        logger.info(
            "Initialized OpenAI STT provider: model=%s, timeout=%s, max_retries=%s",
            self.model,
            self.timeout,
            self.max_retries,
        )

    def transcribe(self, audio_data: bytes, format: str) -> str:
        """Transcribe audio data to text using OpenAI Whisper API.

        Args:
            audio_data: Raw audio data bytes
            format: Audio format (wav, m4a, mp3, opus)

        Returns:
            Transcribed text

        Raises:
            ValueError: If audio format is unsupported or audio data is invalid
            RuntimeError: If transcription fails after retries
        """
        # Validate audio data
        if not audio_data or len(audio_data) == 0:
            raise ValueError("Audio data cannot be empty")

        # Check max file size (25MB as per OpenAI's limit)
        if len(audio_data) > self.MAX_FILE_SIZE:
            raise ValueError(
                f"Audio file too large: {len(audio_data)} bytes. "
                f"Maximum is {self.MAX_FILE_SIZE} bytes (25MB)."
            )

        # Validate format
        if format not in self.SUPPORTED_FORMATS:
            raise ValueError(
                f"Unsupported audio format: {format}. "
                f"Supported formats: {', '.join(self.SUPPORTED_FORMATS)}"
            )

        logger.info(
            "Transcribing audio: format=%s, size=%d bytes",
            format,
            len(audio_data),
        )

        # Retry logic with exponential backoff
        last_error = None
        for attempt in range(self.max_retries):
            try:
                # Create a temporary file for the audio data
                # OpenAI API requires a file-like object
                with tempfile.NamedTemporaryFile(suffix=f".{format}", delete=True) as tmp:
                    tmp.write(audio_data)
                    tmp.flush()
                    tmp.seek(0)  # Reset to start for reading

                    # Call OpenAI Whisper API
                    response = self.client.audio.transcriptions.create(
                        model=self.model,
                        file=tmp,
                        response_format="text",
                        timeout=self.timeout,
                    )

                # OpenAI API returns the transcript as a string directly
                transcript = response.strip() if isinstance(response, str) else str(response).strip()
                
                logger.info(
                    "Successfully transcribed audio (attempt %d): length=%d chars",
                    attempt + 1,
                    len(transcript),
                )
                
                return transcript

            except Exception as e:
                last_error = e
                logger.warning(
                    "OpenAI STT transcription failed (attempt %d/%d): %s",
                    attempt + 1,
                    self.max_retries,
                    str(e),
                )

                # If not last attempt, wait before retrying with exponential backoff
                if attempt < self.max_retries - 1:
                    backoff_delay = min(self.retry_delay * (2 ** attempt), 30.0)
                    logger.info("Retrying in %.1f seconds...", backoff_delay)
                    time.sleep(backoff_delay)

        # All retries exhausted
        error_msg = (
            f"Audio transcription failed after {self.max_retries} attempts. "
            "Please try again or use text input."
        )
        logger.error("%s Last error: %s", error_msg, last_error)
        raise RuntimeError(error_msg) from last_error

