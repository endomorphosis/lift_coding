"""Tests for image input support with privacy mode enforcement."""

import os
from pathlib import Path
import pytest
from fastapi.testclient import TestClient

from handsfree.api import app

client = TestClient(app)

# Get absolute path to test fixtures
FIXTURES_DIR = os.path.join(os.path.dirname(__file__), "fixtures")
TEST_IMAGE_PATH = os.path.join(FIXTURES_DIR, "test_image.jpg")
TEST_IMAGE_URI = Path(TEST_IMAGE_PATH).as_uri()


class TestImageInputPrivacyEnforcement:
    """Test image input behavior across different privacy modes."""

    def test_image_input_strict_mode_rejected(self):
        """Test that image input is rejected in strict privacy mode."""
        response = client.post(
            "/v1/command",
            json={
                "input": {
                    "type": "image",
                    "uri": "https://example.com/snapshot.jpg",
                    "content_type": "image/jpeg",
                },
                "profile": "default",
                "client_context": {
                    "device": "simulator",
                    "locale": "en-US",
                    "timezone": "America/Los_Angeles",
                    "app_version": "0.1.0",
                    "privacy_mode": "strict",
                },
            },
            headers={"X-User-ID": "test-user"},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "error"
        assert data["intent"]["name"] == "error.image_not_supported"
        assert "not supported in strict privacy mode" in data["spoken_text"]
        # Ensure image URI is not in spoken_text
        assert "https://example.com/snapshot.jpg" not in data["spoken_text"]

    def test_image_input_strict_mode_default(self):
        """Test that strict mode is default and rejects images."""
        response = client.post(
            "/v1/command",
            json={
                "input": {
                    "type": "image",
                    "uri": "https://example.com/snapshot.jpg",
                },
                "profile": "default",
                "client_context": {
                    "device": "simulator",
                    "locale": "en-US",
                    "timezone": "America/Los_Angeles",
                    "app_version": "0.1.0",
                    # privacy_mode not specified - defaults to strict
                },
            },
            headers={"X-User-ID": "test-user"},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "error"
        assert data["intent"]["name"] == "error.image_not_supported"

    def test_image_input_balanced_mode_accepted(self):
        """Test that image input is accepted in balanced mode and processed with OCR."""
        response = client.post(
            "/v1/command",
            json={
                "input": {
                    "type": "image",
                    "uri": TEST_IMAGE_URI,
                    "content_type": "image/jpeg",
                },
                "profile": "default",
                "client_context": {
                    "device": "simulator",
                    "locale": "en-US",
                    "timezone": "America/Los_Angeles",
                    "app_version": "0.1.0",
                    "privacy_mode": "balanced",
                },
            },
            headers={"X-User-ID": "test-user"},
        )

        assert response.status_code == 200
        data = response.json()
        # With OCR enabled, the image text is extracted and parsed through intent parsing
        # The stub OCR provider returns "show my inbox" which maps to inbox.list intent
        assert data["status"] in ["ok", "needs_confirmation"]
        assert data["intent"]["name"] == "inbox.list"
        # Ensure image URI is not leaked in spoken_text
        assert "test_image.jpg" not in data["spoken_text"]

    def test_image_input_debug_mode_accepted_with_debug_info(self):
        """Test that image input in debug mode includes debug information."""
        response = client.post(
            "/v1/command",
            json={
                "input": {
                    "type": "image",
                    "uri": TEST_IMAGE_URI,
                    "content_type": "image/jpeg",
                },
                "profile": "default",
                "client_context": {
                    "device": "simulator",
                    "locale": "en-US",
                    "timezone": "America/Los_Angeles",
                    "app_version": "0.1.0",
                    "privacy_mode": "debug",
                    "debug": True,
                },
            },
            headers={"X-User-ID": "test-user"},
        )

        assert response.status_code == 200
        data = response.json()
        # With OCR enabled, the image is processed and routed through intent parsing
        assert data["status"] in ["ok", "needs_confirmation"]
        assert data["intent"]["name"] == "inbox.list"

        # Debug info should be present
        assert data["debug"] is not None
        # The transcript should be the OCR output
        assert data["debug"]["transcript"] == "show my inbox"

        # Image URI should still not be in spoken_text
        assert "test_image.jpg" not in data["spoken_text"]

    def test_image_input_without_content_type(self):
        """Test that image input works without content_type."""
        response = client.post(
            "/v1/command",
            json={
                "input": {
                    "type": "image",
                    "uri": TEST_IMAGE_URI,
                },
                "profile": "default",
                "client_context": {
                    "device": "simulator",
                    "locale": "en-US",
                    "timezone": "America/Los_Angeles",
                    "app_version": "0.1.0",
                    "privacy_mode": "balanced",
                    "debug": True,
                },
            },
            headers={"X-User-ID": "test-user"},
        )

        assert response.status_code == 200
        data = response.json()
        # With OCR enabled, the image is processed
        assert data["status"] in ["ok", "needs_confirmation"]
        assert data["intent"]["name"] == "inbox.list"


class TestImageInputOpenAPISchema:
    """Test that OpenAPI schema accepts image input."""

    def test_openapi_schema_includes_image_input(self):
        """Test that the OpenAPI schema is available and includes image input."""
        from handsfree.models import CommandRequest, ImageInput

        # Test that ImageInput can be instantiated
        image_input = ImageInput(
            type="image",
            uri="https://example.com/test.jpg",
            content_type="image/jpeg",
        )
        assert image_input.type == "image"
        assert image_input.uri == "https://example.com/test.jpg"

        # Test that CommandRequest accepts ImageInput
        request = CommandRequest(
            input=image_input,
            profile="default",
            client_context={
                "device": "test",
                "locale": "en-US",
                "timezone": "UTC",
                "app_version": "1.0.0",
            },
        )
        assert isinstance(request.input, ImageInput)

    def test_image_input_validation(self):
        """Test that ImageInput validates required fields."""
        from pydantic import ValidationError

        from handsfree.models import ImageInput

        # Missing URI should raise validation error
        with pytest.raises(ValidationError):
            ImageInput(type="image")

        # Valid without content_type (optional)
        img = ImageInput(type="image", uri="file:///tmp/test.jpg")
        assert img.content_type is None


class TestImageInputLogging:
    """Test that image URIs are properly handled in logs."""

    def test_image_uri_not_in_spoken_text_strict_mode(self):
        """Test that image URI never appears in spoken_text in strict mode."""
        response = client.post(
            "/v1/command",
            json={
                "input": {
                    "type": "image",
                    "uri": "https://secret.example.com/private/image123.jpg",
                },
                "profile": "default",
                "client_context": {
                    "device": "simulator",
                    "locale": "en-US",
                    "timezone": "America/Los_Angeles",
                    "app_version": "0.1.0",
                    "privacy_mode": "strict",
                },
            },
            headers={"X-User-ID": "test-user"},
        )

        data = response.json()
        assert "secret.example.com" not in data["spoken_text"]
        assert "image123.jpg" not in data["spoken_text"]

    def test_image_uri_not_in_spoken_text_balanced_mode(self):
        """Test that image URI never appears in spoken_text in balanced mode."""
        response = client.post(
            "/v1/command",
            json={
                "input": {
                    "type": "image",
                    "uri": TEST_IMAGE_URI,
                },
                "profile": "default",
                "client_context": {
                    "device": "simulator",
                    "locale": "en-US",
                    "timezone": "America/Los_Angeles",
                    "app_version": "0.1.0",
                    "privacy_mode": "balanced",
                },
            },
            headers={"X-User-ID": "test-user"},
        )

        data = response.json()
        assert "test_image.jpg" not in data["spoken_text"]
        assert "fixtures" not in data["spoken_text"]

    def test_image_uri_not_in_spoken_text_debug_mode(self):
        """Test that image URI never appears in spoken_text even in debug mode."""
        response = client.post(
            "/v1/command",
            json={
                "input": {
                    "type": "image",
                    "uri": TEST_IMAGE_URI,
                },
                "profile": "default",
                "client_context": {
                    "device": "simulator",
                    "locale": "en-US",
                    "timezone": "America/Los_Angeles",
                    "app_version": "0.1.0",
                    "privacy_mode": "debug",
                    "debug": True,
                },
            },
            headers={"X-User-ID": "test-user"},
        )

        data = response.json()
        # URI should not be in spoken_text
        assert "test_image.jpg" not in data["spoken_text"]
        assert "fixtures" not in data["spoken_text"]
        # Debug info can contain metadata but not the actual URI


class TestImageInputBackwardCompatibility:
    """Test that existing clients without image support still work."""

    def test_text_input_still_works(self):
        """Test that text input continues to work as before."""
        response = client.post(
            "/v1/command",
            json={
                "input": {"type": "text", "text": "show my inbox"},
                "profile": "default",
                "client_context": {
                    "device": "simulator",
                    "locale": "en-US",
                    "timezone": "America/Los_Angeles",
                    "app_version": "0.1.0",
                },
            },
            headers={"X-User-ID": "test-user"},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["status"] in ["ok", "needs_confirmation"]

    def test_audio_input_still_works(self):
        """Test that audio input continues to work as before."""
        # Note: This will fail STT because we don't have a real audio file,
        # but we're testing that the API accepts audio input type
        response = client.post(
            "/v1/command",
            json={
                "input": {
                    "type": "audio",
                    "format": "wav",
                    "uri": "file:///tmp/nonexistent.wav",
                },
                "profile": "default",
                "client_context": {
                    "device": "simulator",
                    "locale": "en-US",
                    "timezone": "America/Los_Angeles",
                    "app_version": "0.1.0",
                },
            },
            headers={"X-User-ID": "test-user"},
        )

        # Should return 200 with an error status (not 400/500)
        assert response.status_code == 200
        data = response.json()
        # Will be error because file doesn't exist, but that's expected
        assert data["status"] == "error"


class TestImageInputOCRIntegration:
    """Test that OCR text flows through intent parsing correctly."""

    def test_ocr_text_routed_through_intent_parser(self):
        """Test that OCR extracted text is routed through intent parsing."""
        response = client.post(
            "/v1/command",
            json={
                "input": {
                    "type": "image",
                    "uri": TEST_IMAGE_URI,
                    "content_type": "image/jpeg",
                },
                "profile": "default",
                "client_context": {
                    "device": "simulator",
                    "locale": "en-US",
                    "timezone": "America/Los_Angeles",
                    "app_version": "0.1.0",
                    "privacy_mode": "balanced",
                    "debug": True,
                },
            },
            headers={"X-User-ID": "test-user"},
        )

        assert response.status_code == 200
        data = response.json()

        # The stub OCR returns "show my inbox" which should parse to inbox.list
        assert data["debug"]["transcript"] == "show my inbox"
        assert data["intent"]["name"] == "inbox.list"
        assert data["status"] in ["ok", "needs_confirmation"]

    def test_ocr_disabled_mode(self, monkeypatch):
        """Test that OCR can be disabled via environment variable."""
        monkeypatch.setenv("HANDSFREE_OCR_ENABLED", "false")

        response = client.post(
            "/v1/command",
            json={
                "input": {
                    "type": "image",
                    "uri": TEST_IMAGE_URI,
                    "content_type": "image/jpeg",
                },
                "profile": "default",
                "client_context": {
                    "device": "simulator",
                    "locale": "en-US",
                    "timezone": "America/Los_Angeles",
                    "app_version": "0.1.0",
                    "privacy_mode": "balanced",
                },
            },
            headers={"X-User-ID": "test-user"},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "error"
        assert data["intent"]["name"] == "error.ocr_disabled"
        assert "OCR is disabled" in data["spoken_text"]


class TestImageInputSecurityGating:
    """Test security gating for local file access."""

    def test_local_file_access_denied_when_env_var_not_set(self, monkeypatch):
        """Test that local file access is denied when HANDSFREE_ALLOW_LOCAL_IMAGE_URIS is not set."""
        # Temporarily disable the env var
        monkeypatch.delenv("HANDSFREE_ALLOW_LOCAL_IMAGE_URIS", raising=False)

        response = client.post(
            "/v1/command",
            json={
                "input": {
                    "type": "image",
                    "uri": TEST_IMAGE_URI,
                    "content_type": "image/jpeg",
                },
                "profile": "default",
                "client_context": {
                    "device": "simulator",
                    "locale": "en-US",
                    "timezone": "America/Los_Angeles",
                    "app_version": "0.1.0",
                    "privacy_mode": "balanced",
                },
            },
            headers={"X-User-ID": "test-user"},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "error"
        assert data["intent"]["name"] == "error.image_input"
        assert "Could not process image input" in data["spoken_text"]

    def test_local_file_access_enabled_when_env_var_set(self):
        """Test that local file access works when HANDSFREE_ALLOW_LOCAL_IMAGE_URIS is enabled."""
        # This test relies on conftest.py setting the env var
        response = client.post(
            "/v1/command",
            json={
                "input": {
                    "type": "image",
                    "uri": TEST_IMAGE_URI,
                    "content_type": "image/jpeg",
                },
                "profile": "default",
                "client_context": {
                    "device": "simulator",
                    "locale": "en-US",
                    "timezone": "America/Los_Angeles",
                    "app_version": "0.1.0",
                    "privacy_mode": "balanced",
                },
            },
            headers={"X-User-ID": "test-user"},
        )

        assert response.status_code == 200
        data = response.json()
        # With OCR enabled and local files allowed, this should succeed
        assert data["status"] in ["ok", "needs_confirmation"]

    def test_local_file_size_limit_enforced(self, monkeypatch, tmp_path):
        """Test that size limits are enforced for local files."""
        # Create a large file that exceeds the limit
        large_file = tmp_path / "large_image.jpg"
        # Set a small size limit for this test
        monkeypatch.setenv("IMAGE_MAX_SIZE_BYTES", "100")
        
        # Create a file larger than the limit
        large_file.write_bytes(b"x" * 200)
        large_file_uri = large_file.as_uri()

        response = client.post(
            "/v1/command",
            json={
                "input": {
                    "type": "image",
                    "uri": large_file_uri,
                    "content_type": "image/jpeg",
                },
                "profile": "default",
                "client_context": {
                    "device": "simulator",
                    "locale": "en-US",
                    "timezone": "America/Los_Angeles",
                    "app_version": "0.1.0",
                    "privacy_mode": "balanced",
                },
            },
            headers={"X-User-ID": "test-user"},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "error"
        assert data["intent"]["name"] == "error.image_input"
        assert "Could not process image input" in data["spoken_text"]


class TestImageInputHTTPSFetching:
    """Test HTTPS image fetching with security controls."""

    def test_fail_fast_content_length_rejection(self, monkeypatch, respx_mock):
        """Test that oversized images are rejected based on Content-Length before download."""
        import respx
        from httpx import Response
        
        # Set a small size limit for this test
        monkeypatch.setenv("IMAGE_MAX_SIZE_BYTES", "1000")
        # Enable strict host checking and configure allowed host
        monkeypatch.setenv("IMAGE_STRICT_HOST_CHECKING", "1")
        monkeypatch.setenv("IMAGE_ALLOWED_HOSTS", "example.com")
        
        # Mock a response with Content-Length exceeding the limit
        mock_route = respx_mock.get("https://example.com/large.jpg")
        mock_route.mock(return_value=Response(
            200,
            headers={
                "content-length": "5000",  # Exceeds limit
                "content-type": "image/jpeg",
            },
            content=b"should not be downloaded",
        ))

        response = client.post(
            "/v1/command",
            json={
                "input": {
                    "type": "image",
                    "uri": "https://example.com/large.jpg",
                    "content_type": "image/jpeg",
                },
                "profile": "default",
                "client_context": {
                    "device": "simulator",
                    "locale": "en-US",
                    "timezone": "America/Los_Angeles",
                    "app_version": "0.1.0",
                    "privacy_mode": "balanced",
                },
            },
            headers={"X-User-ID": "test-user"},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "error"
        assert data["intent"]["name"] == "error.image_input"
        # Verify the mock was called (connection attempted)
        assert mock_route.called

    def test_content_length_within_limit_downloads(self, monkeypatch, respx_mock):
        """Test that images with Content-Length within limit proceed to download."""
        import respx
        from httpx import Response
        
        # Set a reasonable size limit
        monkeypatch.setenv("IMAGE_MAX_SIZE_BYTES", "10000")
        # Configure allowed host
        monkeypatch.setenv("IMAGE_STRICT_HOST_CHECKING", "1")
        monkeypatch.setenv("IMAGE_ALLOWED_HOSTS", "example.com")
        
        # Create minimal valid JPEG data
        jpeg_data = b"\xff\xd8\xff\xe0\x00\x10JFIF" + b"\x00" * 100 + b"\xff\xd9"
        
        # Mock a response with Content-Length within the limit
        mock_route = respx_mock.get("https://example.com/small.jpg")
        mock_route.mock(return_value=Response(
            200,
            headers={
                "content-length": str(len(jpeg_data)),
                "content-type": "image/jpeg",
            },
            content=jpeg_data,
        ))

        response = client.post(
            "/v1/command",
            json={
                "input": {
                    "type": "image",
                    "uri": "https://example.com/small.jpg",
                    "content_type": "image/jpeg",
                },
                "profile": "default",
                "client_context": {
                    "device": "simulator",
                    "locale": "en-US",
                    "timezone": "America/Los_Angeles",
                    "app_version": "0.1.0",
                    "privacy_mode": "balanced",
                },
            },
            headers={"X-User-ID": "test-user"},
        )

        assert response.status_code == 200
        data = response.json()
        # Should succeed and route through OCR
        assert data["status"] in ["ok", "needs_confirmation"]
        assert mock_route.called

    def test_invalid_content_length_handled_gracefully(self, monkeypatch, respx_mock):
        """Test that invalid Content-Length headers are handled gracefully."""
        import respx
        from httpx import Response
        
        # Configure allowed host
        monkeypatch.setenv("IMAGE_STRICT_HOST_CHECKING", "1")
        monkeypatch.setenv("IMAGE_ALLOWED_HOSTS", "example.com")
        
        # Create minimal valid JPEG data
        jpeg_data = b"\xff\xd8\xff\xe0\x00\x10JFIF" + b"\x00" * 100 + b"\xff\xd9"
        
        # Mock a response with invalid Content-Length
        mock_route = respx_mock.get("https://example.com/invalid-cl.jpg")
        mock_route.mock(return_value=Response(
            200,
            headers={
                "content-length": "not-a-number",  # Invalid
                "content-type": "image/jpeg",
            },
            content=jpeg_data,
        ))

        response = client.post(
            "/v1/command",
            json={
                "input": {
                    "type": "image",
                    "uri": "https://example.com/invalid-cl.jpg",
                    "content_type": "image/jpeg",
                },
                "profile": "default",
                "client_context": {
                    "device": "simulator",
                    "locale": "en-US",
                    "timezone": "America/Los_Angeles",
                    "app_version": "0.1.0",
                    "privacy_mode": "balanced",
                },
            },
            headers={"X-User-ID": "test-user"},
        )

        assert response.status_code == 200
        data = response.json()
        # Should succeed despite invalid Content-Length header
        assert data["status"] in ["ok", "needs_confirmation"]
        assert mock_route.called

    def test_strict_host_checking_enabled_by_default(self, monkeypatch, respx_mock):
        """Test that strict host checking is enabled by default (deny-all when no allowlist)."""
        import respx
        from httpx import Response
        
        # Don't set IMAGE_ALLOWED_HOSTS, which should trigger default-deny
        monkeypatch.delenv("IMAGE_ALLOWED_HOSTS", raising=False)
        # Don't explicitly set IMAGE_STRICT_HOST_CHECKING (should default to enabled)
        monkeypatch.delenv("IMAGE_STRICT_HOST_CHECKING", raising=False)
        
        # Mock a response (shouldn't be reached due to host checking)
        mock_route = respx_mock.get("https://example.com/test.jpg")
        mock_route.mock(return_value=Response(200, content=b"test"))

        response = client.post(
            "/v1/command",
            json={
                "input": {
                    "type": "image",
                    "uri": "https://example.com/test.jpg",
                    "content_type": "image/jpeg",
                },
                "profile": "default",
                "client_context": {
                    "device": "simulator",
                    "locale": "en-US",
                    "timezone": "America/Los_Angeles",
                    "app_version": "0.1.0",
                    "privacy_mode": "balanced",
                },
            },
            headers={"X-User-ID": "test-user"},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "error"
        # Should be rejected before HTTP request
        assert not mock_route.called

    def test_strict_host_checking_can_be_disabled(self, monkeypatch, respx_mock):
        """Test that strict host checking can be disabled for backward compatibility."""
        import respx
        from httpx import Response
        
        # Disable strict host checking
        monkeypatch.setenv("IMAGE_STRICT_HOST_CHECKING", "0")
        # Don't set IMAGE_ALLOWED_HOSTS
        monkeypatch.delenv("IMAGE_ALLOWED_HOSTS", raising=False)
        
        # Create minimal valid JPEG data
        jpeg_data = b"\xff\xd8\xff\xe0\x00\x10JFIF" + b"\x00" * 100 + b"\xff\xd9"
        
        # Mock a response
        mock_route = respx_mock.get("https://example.com/test.jpg")
        mock_route.mock(return_value=Response(
            200,
            headers={"content-type": "image/jpeg"},
            content=jpeg_data,
        ))

        response = client.post(
            "/v1/command",
            json={
                "input": {
                    "type": "image",
                    "uri": "https://example.com/test.jpg",
                    "content_type": "image/jpeg",
                },
                "profile": "default",
                "client_context": {
                    "device": "simulator",
                    "locale": "en-US",
                    "timezone": "America/Los_Angeles",
                    "app_version": "0.1.0",
                    "privacy_mode": "balanced",
                },
            },
            headers={"X-User-ID": "test-user"},
        )

        assert response.status_code == 200
        data = response.json()
        # Should succeed with strict checking disabled
        assert data["status"] in ["ok", "needs_confirmation"]
        assert mock_route.called
