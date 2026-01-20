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
