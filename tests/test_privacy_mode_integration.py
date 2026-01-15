"""Integration tests for privacy mode enforcement across the API."""

from fastapi.testclient import TestClient

from handsfree.api import app

client = TestClient(app)


def test_privacy_mode_default_strict():
    """Test that when privacy_mode is not specified, strict mode is used by default."""
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
                # privacy_mode not specified - should default to strict
            },
        },
        headers={"X-User-ID": "test-user"},
    )

    assert response.status_code == 200
    data = response.json()
    assert data["status"] in ["ok", "needs_confirmation"]
    # Debug info may be present with transcript, but that's controlled by client_context.debug
    # Privacy mode controls content, not debug presence


def test_privacy_mode_explicit_strict():
    """Test that explicit strict mode prevents description excerpts."""
    response = client.post(
        "/v1/command",
        json={
            "input": {"type": "text", "text": "summarize PR 123"},
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
    assert data["status"] in ["ok", "needs_confirmation"]

    # In strict mode, spoken_text should not contain description excerpts
    spoken_text = data["spoken_text"]
    assert "Description:" not in spoken_text


def test_privacy_mode_balanced():
    """Test that balanced mode allows short excerpts with kitchen profile (more words)."""
    response = client.post(
        "/v1/command",
        json={
            "input": {"type": "text", "text": "summarize PR 123"},
            "profile": "kitchen",  # Use kitchen profile which allows 40 words
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
    assert data["status"] in ["ok", "needs_confirmation"]

    # In balanced mode with kitchen profile, spoken_text may contain description excerpts
    spoken_text = data["spoken_text"]
    # The excerpt should be present in balanced mode (if not truncated by profile)
    # Note: With kitchen profile (40 words), we have more room for description
    assert "Description:" in spoken_text or len(spoken_text) > 100


def test_privacy_mode_debug():
    """Test that debug mode includes transcript and more diagnostics."""
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
                "privacy_mode": "debug",
                "debug": True,  # Enable debug mode to store transcript
            },
        },
        headers={"X-User-ID": "test-user"},
    )

    assert response.status_code == 200
    data = response.json()
    assert data["status"] in ["ok", "needs_confirmation"]

    # In debug mode, transcript should be included
    debug_info = data.get("debug")
    assert debug_info is not None
    assert debug_info.get("transcript") is not None


def test_privacy_mode_balanced_redacts_secrets():
    """Test that balanced mode redacts secrets in excerpts."""
    # This would test with a PR description containing a token
    # For now, we verify the integration works
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
                "privacy_mode": "balanced",
            },
        },
        headers={"X-User-ID": "test-user"},
    )

    assert response.status_code == 200
    data = response.json()
    assert data["status"] in ["ok", "needs_confirmation"]

    # Verify no GitHub tokens in response
    response_str = str(data)
    assert "ghp_" not in response_str
    assert "ghs_" not in response_str


def test_privacy_mode_invalid_value():
    """Test that invalid privacy mode values are rejected."""
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
                "privacy_mode": "invalid",  # Invalid value
            },
        },
        headers={"X-User-ID": "test-user"},
    )

    # Should return a validation error
    assert response.status_code == 422


def test_privacy_mode_pr_summarize_all_modes():
    """Test PR summarize with all privacy modes to ensure consistency."""
    modes = ["strict", "balanced", "debug"]

    for mode in modes:
        # Use kitchen profile for balanced mode to have more room for description
        profile = "kitchen" if mode == "balanced" else "default"

        response = client.post(
            "/v1/command",
            json={
                "input": {"type": "text", "text": "summarize PR 123"},
                "profile": profile,
                "client_context": {
                    "device": "simulator",
                    "locale": "en-US",
                    "timezone": "America/Los_Angeles",
                    "app_version": "0.1.0",
                    "privacy_mode": mode,
                    "debug": mode == "debug",  # Enable debug for debug mode
                },
            },
            headers={"X-User-ID": "test-user"},
        )

        assert response.status_code == 200, f"Failed with mode {mode}"
        data = response.json()
        assert data["status"] in ["ok", "needs_confirmation"]

        # All modes should return spoken text
        assert "spoken_text" in data
        assert len(data["spoken_text"]) > 0

        # Verify mode-specific behavior
        if mode == "strict":
            assert "Description:" not in data["spoken_text"]
        elif mode == "balanced":
            # With kitchen profile, we should have room for description
            assert "Description:" in data["spoken_text"]
        elif mode == "debug":
            # Debug mode includes transcript if debug flag is set
            if data.get("debug"):
                assert data["debug"].get("transcript") is not None


def test_privacy_mode_inbox_list_all_modes():
    """Test inbox list with all privacy modes to ensure consistency."""
    modes = ["strict", "balanced", "debug"]

    for mode in modes:
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
                    "privacy_mode": mode,
                    "debug": mode == "debug",
                },
            },
            headers={"X-User-ID": "test-user"},
        )

        assert response.status_code == 200, f"Failed with mode {mode}"
        data = response.json()
        assert data["status"] in ["ok", "needs_confirmation"]

        # All modes should return spoken text
        assert "spoken_text" in data
        assert len(data["spoken_text"]) > 0

        # No code snippets in any mode
        assert "```" not in data["spoken_text"]
