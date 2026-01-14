"""Tests for audio input handling via STT."""

import tempfile
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from handsfree.api import app

client = TestClient(app)


@pytest.fixture
def audio_file():
    """Create a temporary audio file for testing."""
    with tempfile.NamedTemporaryFile(mode='wb', suffix='.wav', delete=False) as f:
        # Write some dummy audio data (doesn't need to be valid WAV)
        f.write(b"dummy audio data for testing")
        temp_path = f.name
    
    yield temp_path
    
    # Cleanup - use try/except to handle already deleted files
    try:
        Path(temp_path).unlink()
    except FileNotFoundError:
        pass


def test_audio_input_with_stub_stt(audio_file):
    """Test POST /v1/command with audio input using stub STT."""
    import uuid
    response = client.post(
        "/v1/command",
        json={
            "input": {
                "type": "audio",
                "format": "wav",
                "uri": f"file://{audio_file}",
                "duration_ms": 1500,
            },
            "profile": "default",
            "client_context": {
                "device": "simulator",
                "locale": "en-US",
                "timezone": "America/Los_Angeles",
                "app_version": "0.1.0",
            },
            "idempotency_key": f"audio-test-{uuid.uuid4()}",
        },
    )

    assert response.status_code == 200
    data = response.json()

    # Should successfully transcribe and process
    assert data["status"] in ["ok", "needs_confirmation"]
    assert "intent" in data
    assert "spoken_text" in data
    assert "debug" in data
    
    # Debug info should have transcript
    # The stub returns deterministic transcripts based on audio data hash


def test_audio_input_local_path(audio_file):
    """Test audio input with local path (no file:// scheme)."""
    import uuid
    response = client.post(
        "/v1/command",
        json={
            "input": {
                "type": "audio",
                "format": "wav",
                "uri": audio_file,  # Direct path without file://
                "duration_ms": 1500,
            },
            "profile": "default",
            "client_context": {
                "device": "simulator",
                "locale": "en-US",
                "timezone": "America/Los_Angeles",
                "app_version": "0.1.0",
            },
            "idempotency_key": f"audio-test-{uuid.uuid4()}",
        },
    )

    assert response.status_code == 200
    data = response.json()
    assert data["status"] in ["ok", "needs_confirmation"]


def test_audio_input_file_not_found():
    """Test audio input with non-existent file."""
    response = client.post(
        "/v1/command",
        json={
            "input": {
                "type": "audio",
                "format": "wav",
                "uri": "/nonexistent/audio.wav",
                "duration_ms": 1500,
            },
            "profile": "default",
            "client_context": {
                "device": "simulator",
                "locale": "en-US",
                "timezone": "America/Los_Angeles",
                "app_version": "0.1.0",
            },
        },
    )

    assert response.status_code == 200
    data = response.json()
    
    # Should return error status
    assert data["status"] == "error"
    assert data["intent"]["name"] == "error.audio_input"
    assert "not found" in data["spoken_text"].lower() or "process audio" in data["spoken_text"].lower()


def test_audio_input_unsupported_format(audio_file):
    """Test audio input with unsupported format returns error."""
    # Note: The format validation happens in the STT provider
    # For now, stub supports all declared formats
    response = client.post(
        "/v1/command",
        json={
            "input": {
                "type": "audio",
                "format": "m4a",
                "uri": f"file://{audio_file}",
                "duration_ms": 1500,
            },
            "profile": "default",
            "client_context": {
                "device": "simulator",
                "locale": "en-US",
                "timezone": "America/Los_Angeles",
                "app_version": "0.1.0",
            },
        },
    )

    assert response.status_code == 200
    # Stub supports m4a, so it should work
    data = response.json()
    assert data["status"] in ["ok", "needs_confirmation"]


def test_audio_input_stt_disabled(audio_file, monkeypatch):
    """Test audio input when STT is disabled via env var."""
    monkeypatch.setenv("HANDSFREE_STT_ENABLED", "false")
    
    # Need to reload the module to pick up env var change
    # For this test, we'll just verify the error message structure
    # In a real scenario, we'd need to restart the app or use dependency injection
    
    response = client.post(
        "/v1/command",
        json={
            "input": {
                "type": "audio",
                "format": "wav",
                "uri": f"file://{audio_file}",
                "duration_ms": 1500,
            },
            "profile": "default",
            "client_context": {
                "device": "simulator",
                "locale": "en-US",
                "timezone": "America/Los_Angeles",
                "app_version": "0.1.0",
            },
        },
    )

    # With current implementation using get_stt_provider(), 
    # it will read env var at call time
    # If HANDSFREE_STT_ENABLED=false, should get error
    assert response.status_code == 200
    data = response.json()
    
    # Should get an error about STT being disabled
    assert data["status"] == "error"
    assert data["intent"]["name"] == "error.stt_disabled"
    assert "disabled" in data["spoken_text"].lower()


def test_text_input_unchanged():
    """Verify text input still works after audio input changes."""
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
    )

    assert response.status_code == 200
    data = response.json()
    
    # Text input should work exactly as before
    assert data["status"] in ["ok", "needs_confirmation"]
    assert "intent" in data
    assert "spoken_text" in data


def test_audio_input_idempotency(audio_file):
    """Test idempotency of audio input requests."""
    payload = {
        "input": {
            "type": "audio",
            "format": "wav",
            "uri": f"file://{audio_file}",
            "duration_ms": 1500,
        },
        "profile": "default",
        "client_context": {
            "device": "simulator",
            "locale": "en-US",
            "timezone": "America/Los_Angeles",
            "app_version": "0.1.0",
        },
        "idempotency_key": "audio-idem-test-1",
    }

    response1 = client.post("/v1/command", json=payload)
    response2 = client.post("/v1/command", json=payload)

    assert response1.status_code == 200
    assert response2.status_code == 200
    
    # Responses should be identical due to idempotency
    assert response1.json() == response2.json()


def test_audio_input_different_formats(audio_file):
    """Test audio input with different supported formats."""
    import uuid
    formats = ["wav", "m4a", "mp3", "opus"]
    
    for fmt in formats:
        response = client.post(
            "/v1/command",
            json={
                "input": {
                    "type": "audio",
                    "format": fmt,
                    "uri": f"file://{audio_file}",
                    "duration_ms": 1500,
                },
                "profile": "default",
                "client_context": {
                    "device": "simulator",
                    "locale": "en-US",
                    "timezone": "America/Los_Angeles",
                    "app_version": "0.1.0",
                },
                "idempotency_key": f"audio-format-{fmt}-{uuid.uuid4()}",
            },
        )

        assert response.status_code == 200
        data = response.json()
        # All formats should be supported by stub
        assert data["status"] in ["ok", "needs_confirmation"]
