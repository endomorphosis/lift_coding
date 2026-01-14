"""TTS provider interface."""

from abc import ABC, abstractmethod


class TTSProvider(ABC):
    """Abstract base class for TTS providers."""

    @abstractmethod
    def synthesize(
        self,
        text: str,
        voice: str | None = None,
        format: str = "wav",
    ) -> tuple[bytes, str]:
        """Synthesize speech from text.

        Args:
            text: Text to convert to speech
            voice: Optional voice identifier
            format: Audio format (wav, mp3, etc.)

        Returns:
            Tuple of (audio_bytes, content_type)
        """
        pass
