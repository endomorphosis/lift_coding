"""Unit tests for STT provider selection and OpenAI provider with mocked SDK."""

import os
import sys
import tempfile
from unittest.mock import MagicMock, Mock, patch

import pytest


# Test helper to mock openai module
def _setup_mock_openai(api_key="sk-test-key", mock_response=None):
    """Helper to set up mocked openai module for testing.
    
    Args:
        api_key: API key to set in environment
        mock_response: Response to return from transcriptions.create call
        
    Returns:
        Tuple of (mock_openai, mock_client)
    """
    if api_key:
        os.environ["OPENAI_API_KEY"] = api_key
    
    # Mock openai module
    mock_openai = MagicMock()
    mock_client = MagicMock()
    mock_openai.OpenAI.return_value = mock_client
    
    if mock_response is not None:
        mock_client.audio.transcriptions.create.return_value = mock_response
    
    sys.modules["openai"] = mock_openai
    
    # Reload the module to pick up the mock
    import importlib
    import handsfree.stt.openai_provider
    importlib.reload(handsfree.stt.openai_provider)
    
    return mock_openai, mock_client


def _teardown_mock_openai():
    """Clean up mocked openai module."""
    os.environ.pop("OPENAI_API_KEY", None)
    os.environ.pop("HANDS_FREE_STT_MAX_RETRIES", None)
    if "openai" in sys.modules:
        del sys.modules["openai"]


def test_get_stt_provider_default_stub():
    """Test that get_stt_provider returns StubSTTProvider by default."""
    from handsfree.stt import get_stt_provider
    from handsfree.stt.stub_provider import StubSTTProvider

    provider = get_stt_provider()
    assert isinstance(provider, StubSTTProvider)


def test_get_stt_provider_stub_explicit(monkeypatch):
    """Test that get_stt_provider returns StubSTTProvider when explicitly requested."""
    monkeypatch.setenv("HANDS_FREE_STT_PROVIDER", "stub")

    from handsfree.stt import get_stt_provider
    from handsfree.stt.stub_provider import StubSTTProvider

    provider = get_stt_provider()
    assert isinstance(provider, StubSTTProvider)


def test_get_stt_provider_disabled(monkeypatch):
    """Test that get_stt_provider returns disabled StubSTTProvider when disabled."""
    monkeypatch.setenv("HANDSFREE_STT_ENABLED", "false")

    from handsfree.stt import get_stt_provider
    from handsfree.stt.stub_provider import StubSTTProvider

    provider = get_stt_provider()
    assert isinstance(provider, StubSTTProvider)
    assert not provider.enabled


def test_get_stt_provider_openai_fallback_without_key(monkeypatch):
    """Test that requesting OpenAI provider without API key falls back to stub."""
    monkeypatch.setenv("HANDS_FREE_STT_PROVIDER", "openai")
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)

    from handsfree.stt import get_stt_provider
    from handsfree.stt.stub_provider import StubSTTProvider

    # Should fall back to stub when OpenAI provider fails to initialize
    provider = get_stt_provider()
    assert isinstance(provider, StubSTTProvider)


def test_get_stt_provider_unknown_fallback(monkeypatch):
    """Test that unknown provider type falls back to stub."""
    monkeypatch.setenv("HANDS_FREE_STT_PROVIDER", "unknown_provider")

    from handsfree.stt import get_stt_provider
    from handsfree.stt.stub_provider import StubSTTProvider

    provider = get_stt_provider()
    assert isinstance(provider, StubSTTProvider)


def test_stub_provider_transcribe():
    """Test StubSTTProvider transcribe method."""
    from handsfree.stt.stub_provider import StubSTTProvider

    provider = StubSTTProvider(enabled=True)

    # Test with some audio data
    audio_data = b"test audio data"
    transcript = provider.transcribe(audio_data, "wav")

    # Should return one of the deterministic responses
    assert isinstance(transcript, str)
    assert len(transcript) > 0


def test_stub_provider_disabled():
    """Test that disabled stub provider raises NotImplementedError."""
    from handsfree.stt.stub_provider import StubSTTProvider

    provider = StubSTTProvider(enabled=False)

    with pytest.raises(NotImplementedError, match="Audio STT is disabled"):
        provider.transcribe(b"test", "wav")


def test_stub_provider_unsupported_format():
    """Test that stub provider rejects unsupported formats."""
    from handsfree.stt.stub_provider import StubSTTProvider

    provider = StubSTTProvider(enabled=True)

    with pytest.raises(ValueError, match="Unsupported audio format"):
        provider.transcribe(b"test", "unsupported")


# OpenAI provider tests with mocked SDK
# Note: These tests mock the openai module at import time


def test_openai_provider_init_requires_api_key():
    """Test that OpenAI provider requires API key."""
    try:
        # Setup without API key
        old_key = os.environ.pop("OPENAI_API_KEY", None)
        _setup_mock_openai(api_key=None)

        from handsfree.stt.openai_provider import OpenAISTTProvider

        with pytest.raises(ValueError, match="OPENAI_API_KEY"):
            OpenAISTTProvider()
    finally:
        if old_key:
            os.environ["OPENAI_API_KEY"] = old_key
        _teardown_mock_openai()


def test_openai_provider_transcribe_validates_input():
    """Test that OpenAI provider validates input."""
    try:
        _setup_mock_openai()

        from handsfree.stt.openai_provider import OpenAISTTProvider

        provider = OpenAISTTProvider()

        # Test empty audio
        with pytest.raises(ValueError, match="Audio data cannot be empty"):
            provider.transcribe(b"", "wav")

        # Test unsupported format
        with pytest.raises(ValueError, match="Unsupported audio format"):
            provider.transcribe(b"test", "unsupported_format")

        # Test file too large (use constant + 1MB)
        large_audio = b"x" * (OpenAISTTProvider.MAX_FILE_SIZE + 1024 * 1024)
        with pytest.raises(ValueError, match="Audio file too large"):
            provider.transcribe(large_audio, "wav")

    finally:
        _teardown_mock_openai()


def test_openai_provider_transcribe_success():
    """Test successful OpenAI transcription."""
    try:
        _setup_mock_openai(mock_response="Test transcription")

        from handsfree.stt.openai_provider import OpenAISTTProvider

        provider = OpenAISTTProvider()
        audio_data = b"fake audio data"

        transcript = provider.transcribe(audio_data, "wav")

        assert transcript == "Test transcription"

    finally:
        _teardown_mock_openai()


def test_openai_provider_transcribe_with_retry():
    """Test that OpenAI provider retries on failure."""
    try:
        mock_openai, mock_client = _setup_mock_openai()

        # Fail first, succeed second
        mock_client.audio.transcriptions.create.side_effect = [
            Exception("Temporary error"),
            "Success on retry",
        ]

        from handsfree.stt.openai_provider import OpenAISTTProvider

        provider = OpenAISTTProvider()
        audio_data = b"fake audio data"

        transcript = provider.transcribe(audio_data, "wav")

        assert transcript == "Success on retry"
        assert mock_client.audio.transcriptions.create.call_count == 2

    finally:
        _teardown_mock_openai()


def test_openai_provider_transcribe_max_retries():
    """Test that OpenAI provider fails after max retries."""
    try:
        os.environ["HANDS_FREE_STT_MAX_RETRIES"] = "2"
        mock_openai, mock_client = _setup_mock_openai()

        # Always fail
        mock_client.audio.transcriptions.create.side_effect = Exception("API error")

        from handsfree.stt.openai_provider import OpenAISTTProvider

        provider = OpenAISTTProvider()
        audio_data = b"fake audio data"

        with pytest.raises(RuntimeError, match="Audio transcription failed after 2 attempts"):
            provider.transcribe(audio_data, "wav")

        # Should have tried 2 times
        assert mock_client.audio.transcriptions.create.call_count == 2

    finally:
        _teardown_mock_openai()
