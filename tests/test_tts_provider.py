"""Tests for TTS provider implementations."""

from handsfree.tts import StubTTSProvider, TTSProvider


def test_stub_provider_implements_interface() -> None:
    """Test that StubTTSProvider implements TTSProvider interface."""
    provider = StubTTSProvider()
    assert isinstance(provider, TTSProvider)


def test_stub_provider_wav_synthesis() -> None:
    """Test StubTTSProvider generates valid WAV files."""
    provider = StubTTSProvider()
    audio_bytes, content_type = provider.synthesize("Hello world", format="wav")

    assert content_type == "audio/wav"
    assert len(audio_bytes) > 0

    # Check WAV header
    assert audio_bytes[:4] == b"RIFF"
    assert audio_bytes[8:12] == b"WAVE"
    assert b"fmt " in audio_bytes[:50]
    assert b"data" in audio_bytes[:100]


def test_stub_provider_mp3_synthesis() -> None:
    """Test StubTTSProvider generates MP3-like stub."""
    provider = StubTTSProvider()
    audio_bytes, content_type = provider.synthesize("Hello world", format="mp3")

    assert content_type == "audio/mpeg"
    assert len(audio_bytes) > 0

    # Check for ID3 header or MP3 frame sync
    assert b"ID3" in audio_bytes[:20] or b"\xff\xfb" in audio_bytes[:50]


def test_stub_provider_default_format() -> None:
    """Test StubTTSProvider defaults to WAV for unknown formats."""
    provider = StubTTSProvider()
    audio_bytes, content_type = provider.synthesize("Test", format="unknown")

    # Should fallback to WAV
    assert content_type == "audio/wav"
    assert audio_bytes[:4] == b"RIFF"


def test_stub_provider_duration_scales() -> None:
    """Test that audio duration scales with text length."""
    provider = StubTTSProvider()

    short_audio, _ = provider.synthesize("Hi", format="wav")
    long_audio, _ = provider.synthesize(
        "This is a much longer piece of text that should result in longer audio",
        format="wav",
    )

    # Longer text should produce larger WAV file
    assert len(long_audio) > len(short_audio)


def test_stub_provider_deterministic() -> None:
    """Test that StubTTSProvider produces deterministic output."""
    provider = StubTTSProvider()
    text = "Deterministic output test"

    audio1, content_type1 = provider.synthesize(text, format="wav")
    audio2, content_type2 = provider.synthesize(text, format="wav")

    assert content_type1 == content_type2
    assert audio1 == audio2


def test_stub_provider_voice_parameter() -> None:
    """Test that voice parameter is accepted but doesn't change output in stub."""
    provider = StubTTSProvider()
    text = "Voice test"

    audio1, _ = provider.synthesize(text, voice=None, format="wav")
    audio2, _ = provider.synthesize(text, voice="en-US-male", format="wav")

    # In stub implementation, voice is ignored, so output should be identical
    assert audio1 == audio2


def test_stub_provider_empty_text() -> None:
    """Test StubTTSProvider handles empty text gracefully."""
    provider = StubTTSProvider()

    # Should still generate valid audio (minimum duration)
    audio_bytes, content_type = provider.synthesize("", format="wav")

    assert content_type == "audio/wav"
    assert len(audio_bytes) > 0
    assert audio_bytes[:4] == b"RIFF"


def test_stub_provider_special_characters() -> None:
    """Test StubTTSProvider handles special characters."""
    provider = StubTTSProvider()
    text = "Hello! @user #tag $money 50%"

    audio_bytes, content_type = provider.synthesize(text, format="wav")

    assert content_type == "audio/wav"
    assert len(audio_bytes) > 0


def test_stub_provider_unicode() -> None:
    """Test StubTTSProvider handles Unicode text."""
    provider = StubTTSProvider()
    text = "Hello 世界 🌍 Привет"

    audio_bytes, content_type = provider.synthesize(text, format="wav")

    assert content_type == "audio/wav"
    assert len(audio_bytes) > 0
