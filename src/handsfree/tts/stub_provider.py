"""Stub TTS provider for fixture-first development and testing."""

import struct

from handsfree.tts.provider import TTSProvider


class StubTTSProvider(TTSProvider):
    """Stub TTS provider that returns a deterministic WAV file.

    This provider generates a minimal valid WAV file without external dependencies.
    The audio contains silence but is a valid audio file that can be played.
    """

    def synthesize(
        self,
        text: str,
        voice: str | None = None,
        format: str = "wav",
    ) -> tuple[bytes, str]:
        """Generate a deterministic stub WAV file.

        Args:
            text: Text to convert to speech (used for length calculation)
            voice: Optional voice identifier (ignored in stub)
            format: Audio format (only 'wav' and 'mp3' supported)

        Returns:
            Tuple of (audio_bytes, content_type)
        """
        if format == "wav":
            return self._generate_wav(text), "audio/wav"
        elif format == "mp3":
            # Return a minimal MP3-like header for testing
            # In production, this would be actual MP3 data
            return self._generate_mp3_stub(text), "audio/mpeg"
        else:
            # Default to WAV for unsupported formats
            return self._generate_wav(text), "audio/wav"

    def _generate_wav(self, text: str) -> bytes:
        """Generate a minimal valid WAV file.

        Creates a WAV file with silence. Duration scales with text length.

        Args:
            text: Text to convert (length affects duration)

        Returns:
            Valid WAV file as bytes
        """
        # Calculate duration based on text length
        # Assume ~150 words per minute speaking rate, ~5 chars per word
        # So ~12.5 chars per second
        duration_seconds = max(1, len(text) // 13)  # Minimum 1 second
        sample_rate = 16000  # 16kHz
        num_channels = 1  # Mono
        bits_per_sample = 16
        num_samples = duration_seconds * sample_rate

        # Generate silence (all zeros)
        audio_data = bytes(num_samples * num_channels * (bits_per_sample // 8))

        # WAV file header
        subchunk2_size = len(audio_data)
        chunk_size = 36 + subchunk2_size

        # Build WAV header
        header = struct.pack(
            "<4sI4s4sIHHIIHH4sI",
            b"RIFF",
            chunk_size,
            b"WAVE",
            b"fmt ",
            16,  # Subchunk1Size (PCM)
            1,  # AudioFormat (PCM)
            num_channels,
            sample_rate,
            sample_rate * num_channels * (bits_per_sample // 8),  # ByteRate
            num_channels * (bits_per_sample // 8),  # BlockAlign
            bits_per_sample,
            b"data",
            subchunk2_size,
        )

        return header + audio_data

    def _generate_mp3_stub(self, text: str) -> bytes:
        """Generate a minimal MP3-like stub for testing.

        This is not a valid MP3, just a placeholder with MP3 header magic bytes.
        Real MP3 generation would require an encoder library.

        Args:
            text: Text to convert

        Returns:
            Stub MP3 data as bytes
        """
        # Minimal ID3v2 header + fake frame header
        # This is sufficient for content-type testing but not playable
        id3_header = b"ID3\x04\x00\x00\x00\x00\x00\x00"
        # MP3 frame sync + minimal header
        frame_header = b"\xff\xfb"

        # Add some deterministic data based on text length
        data_size = max(100, len(text) * 10)
        stub_data = (text.encode("utf-8") * ((data_size // len(text)) + 1))[:data_size]

        return id3_header + frame_header + stub_data
