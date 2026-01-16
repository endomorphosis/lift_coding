"""Unit tests for TTS provider selection and factory function."""

import os
import sys
from unittest.mock import MagicMock

import pytest


# Test helper to mock openai module
def _setup_mock_openai(api_key="sk-test-key", mock_response=None):
    """Helper to set up mocked openai module for testing.

    Args:
        api_key: API key to set in environment
        mock_response: Response to return from speech.create call

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
        mock_client.audio.speech.create.return_value = mock_response

    sys.modules["openai"] = mock_openai

    # Reload the module to pick up the mock
    import importlib

    import handsfree.tts.openai_provider

    importlib.reload(handsfree.tts.openai_provider)

    return mock_openai, mock_client


def _teardown_mock_openai():
    """Clean up mocked openai module."""
    os.environ.pop("OPENAI_API_KEY", None)
    os.environ.pop("HANDSFREE_TTS_PROVIDER", None)
    os.environ.pop("OPENAI_TTS_MODEL", None)
    os.environ.pop("OPENAI_TTS_VOICE", None)
    if "openai" in sys.modules:
        del sys.modules["openai"]


def test_get_tts_provider_default_stub():
    """Test that get_tts_provider returns StubTTSProvider by default."""
    from handsfree.tts import get_tts_provider
    from handsfree.tts.stub_provider import StubTTSProvider

    provider = get_tts_provider()
    assert isinstance(provider, StubTTSProvider)


def test_get_tts_provider_stub_explicit(monkeypatch):
    """Test that get_tts_provider returns StubTTSProvider when explicitly requested."""
    monkeypatch.setenv("HANDSFREE_TTS_PROVIDER", "stub")

    from handsfree.tts import get_tts_provider
    from handsfree.tts.stub_provider import StubTTSProvider

    provider = get_tts_provider()
    assert isinstance(provider, StubTTSProvider)


def test_get_tts_provider_unknown_fallback(monkeypatch):
    """Test that get_tts_provider falls back to stub for unknown providers."""
    monkeypatch.setenv("HANDSFREE_TTS_PROVIDER", "unknown_provider")

    from handsfree.tts import get_tts_provider
    from handsfree.tts.stub_provider import StubTTSProvider

    provider = get_tts_provider()
    assert isinstance(provider, StubTTSProvider)


def test_get_tts_provider_openai_no_package(monkeypatch):
    """Test that get_tts_provider falls back to stub when openai package is not installed."""
    monkeypatch.setenv("HANDSFREE_TTS_PROVIDER", "openai")

    # Ensure openai is not available
    if "openai" in sys.modules:
        del sys.modules["openai"]

    # Temporarily remove openai from path if it exists
    import importlib.util

    openai_spec = importlib.util.find_spec("openai")
    if openai_spec is not None:
        # openai is installed, skip this test
        pytest.skip("openai package is installed, cannot test missing dependency fallback")

    from handsfree.tts import get_tts_provider
    from handsfree.tts.stub_provider import StubTTSProvider

    provider = get_tts_provider()
    assert isinstance(provider, StubTTSProvider)


def test_get_tts_provider_openai_with_mock():
    """Test that get_tts_provider returns OpenAITTSProvider when configured with mock."""
    try:
        # Set up mock
        _setup_mock_openai(api_key="sk-test-key")

        # Set environment for OpenAI provider
        os.environ["HANDSFREE_TTS_PROVIDER"] = "openai"

        # Import after mock is set up
        import importlib

        import handsfree.tts

        importlib.reload(handsfree.tts)

        from handsfree.tts import get_tts_provider
        from handsfree.tts.openai_provider import OpenAITTSProvider

        provider = get_tts_provider()
        assert isinstance(provider, OpenAITTSProvider)

    finally:
        _teardown_mock_openai()


def test_openai_tts_provider_no_api_key():
    """Test that OpenAITTSProvider raises error when API key is missing."""
    try:
        # Set up mock without API key
        _setup_mock_openai(api_key=None)

        from handsfree.tts.openai_provider import OpenAITTSProvider

        with pytest.raises(ValueError, match="OPENAI_API_KEY"):
            OpenAITTSProvider()

    finally:
        _teardown_mock_openai()


def test_openai_tts_provider_synthesize():
    """Test OpenAITTSProvider synthesize with mock."""
    try:
        # Create mock response
        mock_response = MagicMock()
        mock_response.content = b"fake_audio_data"

        # Set up mock
        _, mock_client = _setup_mock_openai(api_key="sk-test-key", mock_response=mock_response)

        from handsfree.tts.openai_provider import OpenAITTSProvider

        provider = OpenAITTSProvider()
        audio_bytes, content_type = provider.synthesize("Hello world", format="mp3")

        # Verify the call was made
        mock_client.audio.speech.create.assert_called_once()

        # Check results
        assert audio_bytes == b"fake_audio_data"
        assert content_type == "audio/mpeg"

    finally:
        _teardown_mock_openai()


def test_openai_tts_provider_empty_text():
    """Test that OpenAITTSProvider raises error for empty text."""
    try:
        _setup_mock_openai(api_key="sk-test-key")

        from handsfree.tts.openai_provider import OpenAITTSProvider

        provider = OpenAITTSProvider()

        with pytest.raises(ValueError, match="Text cannot be empty"):
            provider.synthesize("", format="mp3")

    finally:
        _teardown_mock_openai()


def test_openai_tts_provider_format_fallback():
    """Test that OpenAITTSProvider falls back to mp3 for unsupported formats."""
    try:
        mock_response = MagicMock()
        mock_response.content = b"fake_audio_data"

        _, mock_client = _setup_mock_openai(api_key="sk-test-key", mock_response=mock_response)

        from handsfree.tts.openai_provider import OpenAITTSProvider

        provider = OpenAITTSProvider()
        audio_bytes, content_type = provider.synthesize("Test", format="unsupported")

        # Should fall back to mp3
        call_args = mock_client.audio.speech.create.call_args
        assert call_args.kwargs["response_format"] == "mp3"

    finally:
        _teardown_mock_openai()


def test_openai_tts_provider_voice_fallback():
    """Test that OpenAITTSProvider falls back to default voice for unknown voices."""
    try:
        mock_response = MagicMock()
        mock_response.content = b"fake_audio_data"

        _, mock_client = _setup_mock_openai(api_key="sk-test-key", mock_response=mock_response)

        from handsfree.tts.openai_provider import OpenAITTSProvider

        provider = OpenAITTSProvider()
        audio_bytes, content_type = provider.synthesize("Test", voice="unknown_voice")

        # Should fall back to default voice (alloy)
        call_args = mock_client.audio.speech.create.call_args
        assert call_args.kwargs["voice"] == "alloy"

    finally:
        _teardown_mock_openai()


def test_openai_tts_provider_custom_voice():
    """Test that OpenAITTSProvider uses custom voice when valid."""
    try:
        mock_response = MagicMock()
        mock_response.content = b"fake_audio_data"

        _, mock_client = _setup_mock_openai(api_key="sk-test-key", mock_response=mock_response)

        from handsfree.tts.openai_provider import OpenAITTSProvider

        provider = OpenAITTSProvider()
        audio_bytes, content_type = provider.synthesize("Test", voice="nova")

        # Should use the provided voice
        call_args = mock_client.audio.speech.create.call_args
        assert call_args.kwargs["voice"] == "nova"

    finally:
        _teardown_mock_openai()
