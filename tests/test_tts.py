"""Tests for TTS (Text-to-Speech) endpoint."""


from fastapi.testclient import TestClient

from handsfree.api import app

client = TestClient(app)


def test_tts_basic_wav() -> None:
    """Test basic TTS request with WAV format."""
    response = client.post(
        "/v1/tts",
        json={
            "text": "Hello, world!",
            "format": "wav",
        },
    )

    assert response.status_code == 200
    assert response.headers["content-type"] == "audio/wav"
    assert "content-disposition" in response.headers
    assert "speech.wav" in response.headers["content-disposition"]

    # Verify non-empty audio payload
    audio_data = response.content
    assert len(audio_data) > 0

    # Verify it's a valid WAV file by checking header
    assert audio_data[:4] == b"RIFF"
    assert audio_data[8:12] == b"WAVE"


def test_tts_basic_mp3() -> None:
    """Test basic TTS request with MP3 format."""
    response = client.post(
        "/v1/tts",
        json={
            "text": "Hello, world!",
            "format": "mp3",
        },
    )

    assert response.status_code == 200
    assert response.headers["content-type"] == "audio/mpeg"
    assert "content-disposition" in response.headers
    assert "speech.mp3" in response.headers["content-disposition"]

    # Verify non-empty audio payload
    audio_data = response.content
    assert len(audio_data) > 0


def test_tts_default_format() -> None:
    """Test TTS with default format (should be WAV)."""
    response = client.post(
        "/v1/tts",
        json={
            "text": "Default format test",
        },
    )

    assert response.status_code == 200
    assert response.headers["content-type"] == "audio/wav"
    assert len(response.content) > 0


def test_tts_with_voice() -> None:
    """Test TTS with voice parameter."""
    response = client.post(
        "/v1/tts",
        json={
            "text": "Testing voice parameter",
            "voice": "en-US-male",
            "format": "wav",
        },
    )

    assert response.status_code == 200
    assert response.headers["content-type"] == "audio/wav"
    assert len(response.content) > 0


def test_tts_empty_text() -> None:
    """Test TTS with empty text returns 422."""
    response = client.post(
        "/v1/tts",
        json={
            "text": "",
            "format": "wav",
        },
    )

    # Pydantic validation returns 422 for constraint violations
    assert response.status_code == 422


def test_tts_whitespace_only_text() -> None:
    """Test TTS with whitespace-only text returns 400."""
    response = client.post(
        "/v1/tts",
        json={
            "text": "   \n\t  ",
            "format": "wav",
        },
    )

    assert response.status_code == 400
    data = response.json()
    assert data["error"] == "invalid_input"
    assert "empty" in data["message"].lower()


def test_tts_text_too_long() -> None:
    """Test TTS with text exceeding maximum length returns 422."""
    # Create text longer than 5000 characters
    long_text = "a" * 5001

    response = client.post(
        "/v1/tts",
        json={
            "text": long_text,
            "format": "wav",
        },
    )

    # Pydantic validation returns 422 for constraint violations
    assert response.status_code == 422


def test_tts_text_at_max_length() -> None:
    """Test TTS with text at maximum length (5000 chars) succeeds."""
    # Create text exactly 5000 characters
    max_text = "a" * 5000

    response = client.post(
        "/v1/tts",
        json={
            "text": max_text,
            "format": "wav",
        },
    )

    assert response.status_code == 200
    assert response.headers["content-type"] == "audio/wav"
    assert len(response.content) > 0


def test_tts_missing_text_field() -> None:
    """Test TTS without required text field returns 422."""
    response = client.post(
        "/v1/tts",
        json={
            "format": "wav",
        },
    )

    # FastAPI returns 422 for missing required fields
    assert response.status_code == 422


def test_tts_wav_duration_scales_with_text() -> None:
    """Test that WAV file duration scales with text length."""
    # Short text
    short_response = client.post(
        "/v1/tts",
        json={
            "text": "Hi",
            "format": "wav",
        },
    )

    # Long text
    long_response = client.post(
        "/v1/tts",
        json={
            "text": (
                "This is a much longer piece of text that should result in "
                "a longer audio file duration when synthesized to speech."
            ),
            "format": "wav",
        },
    )

    assert short_response.status_code == 200
    assert long_response.status_code == 200

    short_audio = short_response.content
    long_audio = long_response.content

    # Longer text should produce larger audio file
    assert len(long_audio) > len(short_audio)


def test_tts_deterministic_output() -> None:
    """Test that same input produces same output (fixture-first behavior)."""
    text = "Deterministic test"

    response1 = client.post(
        "/v1/tts",
        json={
            "text": text,
            "format": "wav",
        },
    )

    response2 = client.post(
        "/v1/tts",
        json={
            "text": text,
            "format": "wav",
        },
    )

    assert response1.status_code == 200
    assert response2.status_code == 200

    # Should produce identical output for same input
    assert response1.content == response2.content


def test_tts_special_characters() -> None:
    """Test TTS handles special characters properly."""
    response = client.post(
        "/v1/tts",
        json={
            "text": "Hello! How are you? I'm fine, thanks. #DevOps @user",
            "format": "wav",
        },
    )

    assert response.status_code == 200
    assert response.headers["content-type"] == "audio/wav"
    assert len(response.content) > 0


def test_tts_unicode_text() -> None:
    """Test TTS handles Unicode text properly."""
    response = client.post(
        "/v1/tts",
        json={
            "text": "Hello 世界 🌍 Привет",
            "format": "wav",
        },
    )

    assert response.status_code == 200
    assert response.headers["content-type"] == "audio/wav"
    assert len(response.content) > 0
