"""Tests for HTTPS audio URI fetching with security controls."""

import os
import tempfile
from pathlib import Path
from unittest.mock import patch

import httpx
import pytest
from fastapi.testclient import TestClient

from handsfree.api import app
from handsfree.audio_fetch import _get_config, fetch_audio_data

client = TestClient(app)


@pytest.fixture
def audio_file():
    """Create a temporary audio file for testing."""
    with tempfile.NamedTemporaryFile(mode="wb", suffix=".wav", delete=False) as f:
        # Write some dummy audio data (doesn't need to be valid WAV)
        f.write(b"dummy audio data for testing")
        temp_path = f.name

    yield temp_path

    # Cleanup
    try:
        Path(temp_path).unlink()
    except FileNotFoundError:
        pass


class TestAudioFetchHTTPS:
    """Test HTTPS audio URI fetching with various security controls."""

    def test_https_audio_fetch_success_allowed_host(self, respx_mock):
        """Test successful HTTPS audio fetch from allowed host."""
        audio_data = b"mock audio data from https"
        mock_url = "https://storage.example.com/audio/sample.wav"

        # Mock the HTTP response
        respx_mock.get(mock_url).mock(
            return_value=httpx.Response(
                200,
                content=audio_data,
                headers={
                    "content-type": "audio/wav",
                    "content-length": str(len(audio_data)),
                },
            )
        )

        # Allow this host
        with patch.dict(os.environ, {"AUDIO_ALLOWED_HOSTS": "storage.example.com"}):
            result = fetch_audio_data(mock_url)
            assert result == audio_data

    def test_https_audio_fetch_host_not_in_allowlist(self, respx_mock):
        """Test HTTPS audio fetch fails when host is not in allowlist."""
        mock_url = "https://untrusted.example.com/audio/sample.wav"

        respx_mock.get(mock_url).mock(
            return_value=httpx.Response(
                200,
                content=b"audio data",
                headers={"content-type": "audio/wav"},
            )
        )

        # Configure allowlist without this host
        with patch.dict(os.environ, {"AUDIO_ALLOWED_HOSTS": "trusted.example.com"}):
            with pytest.raises(ValueError) as exc_info:
                fetch_audio_data(mock_url)
            assert "not in the allowed list" in str(exc_info.value)
            assert "untrusted.example.com" in str(exc_info.value)

    def test_https_audio_fetch_host_in_denylist(self, respx_mock):
        """Test HTTPS audio fetch fails when host is in denylist."""
        mock_url = "https://blocked.example.com/audio/sample.wav"

        respx_mock.get(mock_url).mock(
            return_value=httpx.Response(
                200,
                content=b"audio data",
                headers={"content-type": "audio/wav"},
            )
        )

        # Configure denylist
        with patch.dict(os.environ, {"AUDIO_DENIED_HOSTS": "blocked.example.com"}):
            with pytest.raises(ValueError) as exc_info:
                fetch_audio_data(mock_url)
            assert "denied by security policy" in str(exc_info.value)
            assert "blocked.example.com" in str(exc_info.value)

    def test_https_audio_fetch_content_too_large_header(self, respx_mock):
        """Test HTTPS audio fetch fails when content-length exceeds limit."""
        # Get the current max size
        max_size, _, _, _ = _get_config()

        mock_url = "https://storage.example.com/audio/large.wav"
        oversized_length = max_size + 1000

        # Mock response with oversized content-length header
        respx_mock.get(mock_url).mock(
            return_value=httpx.Response(
                200,
                content=b"this won't be downloaded",
                headers={
                    "content-type": "audio/wav",
                    "content-length": str(oversized_length),
                },
            )
        )

        with patch.dict(os.environ, {"AUDIO_ALLOWED_HOSTS": "storage.example.com"}):
            with pytest.raises(RuntimeError) as exc_info:
                fetch_audio_data(mock_url)
            assert "too large" in str(exc_info.value).lower()
            assert str(max_size) in str(exc_info.value)

    def test_https_audio_fetch_content_too_large_actual(self, respx_mock):
        """Test HTTPS audio fetch fails when actual download exceeds limit."""
        # Get the current max size
        max_size, _, _, _ = _get_config()

        mock_url = "https://storage.example.com/audio/large.wav"
        # Create oversized content
        oversized_content = b"x" * (max_size + 1000)

        # Mock response without content-length header (streaming scenario)
        respx_mock.get(mock_url).mock(
            return_value=httpx.Response(
                200,
                content=oversized_content,
                headers={"content-type": "audio/wav"},
            )
        )

        with patch.dict(os.environ, {"AUDIO_ALLOWED_HOSTS": "storage.example.com"}):
            with pytest.raises(RuntimeError) as exc_info:
                fetch_audio_data(mock_url)
            assert "exceeded size limit" in str(exc_info.value).lower()

    def test_https_audio_fetch_invalid_content_type(self, respx_mock):
        """Test HTTPS audio fetch fails with invalid content-type."""
        mock_url = "https://storage.example.com/audio/sample.wav"

        # Mock response with invalid content-type
        respx_mock.get(mock_url).mock(
            return_value=httpx.Response(
                200,
                content=b"not audio",
                headers={
                    "content-type": "text/html",
                    "content-length": "9",
                },
            )
        )

        with patch.dict(os.environ, {"AUDIO_ALLOWED_HOSTS": "storage.example.com"}):
            with pytest.raises(RuntimeError) as exc_info:
                fetch_audio_data(mock_url)
            assert "invalid audio content-type" in str(exc_info.value).lower()
            assert "text/html" in str(exc_info.value)

    def test_https_audio_fetch_timeout(self, respx_mock):
        """Test HTTPS audio fetch times out appropriately."""
        mock_url = "https://storage.example.com/audio/sample.wav"

        # Mock timeout
        respx_mock.get(mock_url).mock(side_effect=httpx.TimeoutException("Connection timeout"))

        with patch.dict(
            os.environ,
            {
                "AUDIO_ALLOWED_HOSTS": "storage.example.com",
                "AUDIO_FETCH_TIMEOUT_SECONDS": "5",
            },
        ):
            with pytest.raises(RuntimeError) as exc_info:
                fetch_audio_data(mock_url)
            assert "timeout" in str(exc_info.value).lower()
            assert "5 seconds" in str(exc_info.value)

    def test_https_audio_fetch_http_error(self, respx_mock):
        """Test HTTPS audio fetch handles HTTP errors."""
        mock_url = "https://storage.example.com/audio/notfound.wav"

        # Mock 404 response
        respx_mock.get(mock_url).mock(return_value=httpx.Response(404, content=b"Not Found"))

        with patch.dict(os.environ, {"AUDIO_ALLOWED_HOSTS": "storage.example.com"}):
            with pytest.raises(RuntimeError) as exc_info:
                fetch_audio_data(mock_url)
            assert "http error" in str(exc_info.value).lower()
            assert "404" in str(exc_info.value)

    def test_https_audio_fetch_network_error(self, respx_mock):
        """Test HTTPS audio fetch handles network errors."""
        mock_url = "https://storage.example.com/audio/sample.wav"

        # Mock network error
        respx_mock.get(mock_url).mock(side_effect=httpx.ConnectError("Connection failed"))

        with patch.dict(os.environ, {"AUDIO_ALLOWED_HOSTS": "storage.example.com"}):
            with pytest.raises(RuntimeError) as exc_info:
                fetch_audio_data(mock_url)
            assert "network error" in str(exc_info.value).lower()

    def test_https_audio_various_content_types(self, respx_mock):
        """Test HTTPS audio fetch accepts various valid audio content-types."""
        valid_types = [
            "audio/wav",
            "audio/wave",
            "audio/x-wav",
            "audio/mp4",
            "audio/m4a",
            "audio/mpeg",
            "audio/opus",
            "application/octet-stream",
        ]

        for content_type in valid_types:
            mock_url = f"https://storage.example.com/audio/{content_type.replace('/', '_')}.dat"
            audio_data = b"test audio"

            respx_mock.get(mock_url).mock(
                return_value=httpx.Response(
                    200,
                    content=audio_data,
                    headers={
                        "content-type": content_type,
                        "content-length": str(len(audio_data)),
                    },
                )
            )

            with patch.dict(os.environ, {"AUDIO_ALLOWED_HOSTS": "storage.example.com"}):
                result = fetch_audio_data(mock_url)
                assert result == audio_data

    def test_file_uri_still_works(self, audio_file):
        """Test backward compatibility with file:// URIs."""
        result = fetch_audio_data(f"file://{audio_file}")
        assert result == b"dummy audio data for testing"

    def test_local_path_still_works(self, audio_file):
        """Test backward compatibility with local paths."""
        result = fetch_audio_data(audio_file)
        assert result == b"dummy audio data for testing"

    def test_unsupported_scheme(self):
        """Test that unsupported URI schemes are rejected."""
        with pytest.raises(ValueError) as exc_info:
            fetch_audio_data("ftp://example.com/audio.wav")
        assert "unsupported" in str(exc_info.value).lower()
        assert "ftp" in str(exc_info.value)


class TestAudioFetchIntegration:
    """Integration tests with /v1/command endpoint."""

    def test_command_with_https_audio_success(self, respx_mock):
        """Test /v1/command with HTTPS audio URI."""
        import uuid

        audio_data = b"mock audio data"
        mock_url = "https://storage.example.com/audio/command.wav"

        respx_mock.get(mock_url).mock(
            return_value=httpx.Response(
                200,
                content=audio_data,
                headers={
                    "content-type": "audio/wav",
                    "content-length": str(len(audio_data)),
                },
            )
        )

        with patch.dict(os.environ, {"AUDIO_ALLOWED_HOSTS": "storage.example.com"}):
            response = client.post(
                "/v1/command",
                json={
                    "input": {
                        "type": "audio",
                        "format": "wav",
                        "uri": mock_url,
                        "duration_ms": 1500,
                    },
                    "profile": "default",
                    "client_context": {
                        "device": "ios",
                        "locale": "en-US",
                        "timezone": "America/Los_Angeles",
                        "app_version": "0.1.0",
                    },
                    "idempotency_key": f"https-audio-test-{uuid.uuid4()}",
                },
            )

        assert response.status_code == 200
        data = response.json()
        assert data["status"] in ["ok", "needs_confirmation"]
        assert "intent" in data
        assert "spoken_text" in data

    def test_command_with_https_audio_blocked_host(self, respx_mock):
        """Test /v1/command with HTTPS audio from blocked host."""
        import uuid

        mock_url = "https://malicious.example.com/audio/command.wav"

        respx_mock.get(mock_url).mock(
            return_value=httpx.Response(
                200,
                content=b"audio",
                headers={"content-type": "audio/wav"},
            )
        )

        with patch.dict(os.environ, {"AUDIO_ALLOWED_HOSTS": "trusted.example.com"}):
            response = client.post(
                "/v1/command",
                json={
                    "input": {
                        "type": "audio",
                        "format": "wav",
                        "uri": mock_url,
                        "duration_ms": 1500,
                    },
                    "profile": "default",
                    "client_context": {
                        "device": "ios",
                        "locale": "en-US",
                        "timezone": "America/Los_Angeles",
                        "app_version": "0.1.0",
                    },
                    "idempotency_key": f"blocked-audio-test-{uuid.uuid4()}",
                },
            )

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "error"
        assert data["intent"]["name"] == "error.audio_input"
        assert "not in the allowed list" in data["spoken_text"].lower()

    def test_command_with_https_audio_oversized(self, respx_mock):
        """Test /v1/command with oversized HTTPS audio."""
        import uuid

        # Get the current max size
        max_size, _, _, _ = _get_config()

        mock_url = "https://storage.example.com/audio/large.wav"
        oversized_length = max_size + 1000

        respx_mock.get(mock_url).mock(
            return_value=httpx.Response(
                200,
                content=b"dummy",
                headers={
                    "content-type": "audio/wav",
                    "content-length": str(oversized_length),
                },
            )
        )

        with patch.dict(os.environ, {"AUDIO_ALLOWED_HOSTS": "storage.example.com"}):
            response = client.post(
                "/v1/command",
                json={
                    "input": {
                        "type": "audio",
                        "format": "wav",
                        "uri": mock_url,
                        "duration_ms": 1500,
                    },
                    "profile": "default",
                    "client_context": {
                        "device": "ios",
                        "locale": "en-US",
                        "timezone": "America/Los_Angeles",
                        "app_version": "0.1.0",
                    },
                    "idempotency_key": f"oversized-audio-test-{uuid.uuid4()}",
                },
            )

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "error"
        assert data["intent"]["name"] == "error.audio_input"
        assert "too large" in data["spoken_text"].lower()
