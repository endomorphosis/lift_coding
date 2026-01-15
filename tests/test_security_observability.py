"""Tests for security and observability features (PR-014).

Tests:
- Request ID propagation
- Secret redaction (GitHub tokens, Authorization headers)
- Structured logging
"""

import logging
import re
from io import StringIO

import pytest
from fastapi.testclient import TestClient

from handsfree.api import app
from handsfree.logging_utils import (
    clear_request_id,
    get_request_id,
    log_error,
    log_info,
    log_warning,
    redact_secrets,
    set_request_id,
)


@pytest.fixture
def client():
    """Create a test client."""
    return TestClient(app)


@pytest.fixture
def reset_db():
    """Reset the database connection before each test."""
    import handsfree.api as api_module

    api_module._db_conn = None
    api_module._command_router = None
    yield
    api_module._db_conn = None
    api_module._command_router = None


class TestSecretRedaction:
    """Test secret redaction functionality."""

    def test_redact_github_personal_token(self):
        """Test that GitHub personal access tokens are redacted."""
        text = "Using token ghp_1234567890abcdefghijklmnopqrstuvwxyz"
        redacted = redact_secrets(text)
        assert "ghp_1234567890abcdefghijklmnopqrstuvwxyz" not in redacted
        assert "ghp_***REDACTED***" in redacted

    def test_redact_github_app_token(self):
        """Test that GitHub App tokens are redacted."""
        text = "Auth with ghs_abcdefghijklmnopqrstuvwxyz123456"
        redacted = redact_secrets(text)
        assert "ghs_abcdefghijklmnopqrstuvwxyz123456" not in redacted
        assert "ghs_***REDACTED***" in redacted

    def test_redact_github_oauth_token(self):
        """Test that GitHub OAuth tokens are redacted."""
        text = "OAuth token: gho_zyxwvutsrqponmlkjihgfedcba987654"
        redacted = redact_secrets(text)
        assert "gho_zyxwvutsrqponmlkjihgfedcba987654" not in redacted
        assert "gho_***REDACTED***" in redacted

    def test_redact_github_fine_grained_token(self):
        """Test that fine-grained GitHub PATs are redacted."""
        text = "Token: github_pat_1234567890ABCDEFGHIJKLMNOP"
        redacted = redact_secrets(text)
        assert "github_pat_1234567890ABCDEFGHIJKLMNOP" not in redacted
        assert "github_pat_***REDACTED***" in redacted

    def test_redact_authorization_header(self):
        """Test that Authorization header values are redacted."""
        # Test with Bearer token
        text = "Authorization: Bearer ghp_secrettoken123456"
        redacted = redact_secrets(text)
        assert "ghp_secrettoken123456" not in redacted
        assert "Authorization: ***REDACTED***" in redacted

        # Test with token keyword
        text = "Authorization: token ghp_anothertoken"
        redacted = redact_secrets(text)
        assert "ghp_anothertoken" not in redacted
        assert "***REDACTED***" in redacted

    def test_redact_multiple_secrets(self):
        """Test that multiple secrets in same text are all redacted."""
        text = "Token ghp_token1 and Authorization: Bearer ghs_token2"
        redacted = redact_secrets(text)
        assert "ghp_token1" not in redacted
        assert "ghs_token2" not in redacted
        assert "ghp_***REDACTED***" in redacted
        assert "ghs_***REDACTED***" in redacted

    def test_redact_none_input(self):
        """Test that None input returns empty string."""
        redacted = redact_secrets(None)
        assert redacted == ""

    def test_redact_non_string_input(self):
        """Test that non-string input is converted to string."""
        redacted = redact_secrets(12345)
        assert redacted == "12345"


class TestRequestIDContext:
    """Test request ID context management."""

    def teardown_method(self):
        """Clean up request ID after each test."""
        clear_request_id()

    def test_set_and_get_request_id(self):
        """Test setting and getting request ID."""
        set_request_id("test-request-123")
        assert get_request_id() == "test-request-123"

    def test_generate_request_id(self):
        """Test that request ID is generated if not provided."""
        request_id = set_request_id()
        assert request_id is not None
        assert get_request_id() == request_id
        # Should be a UUID
        assert len(request_id) == 36  # UUID format

    def test_clear_request_id(self):
        """Test clearing request ID."""
        set_request_id("test-request-456")
        assert get_request_id() == "test-request-456"

        clear_request_id()
        assert get_request_id() is None

    def test_request_id_isolation(self):
        """Test that request IDs are isolated per context."""
        # Set request ID
        set_request_id("request-1")
        assert get_request_id() == "request-1"

        # Clear and set new one
        clear_request_id()
        set_request_id("request-2")
        assert get_request_id() == "request-2"


class TestStructuredLogging:
    """Test structured logging with context."""

    def setup_method(self):
        """Set up logging capture."""
        self.logger = logging.getLogger("test_logger")
        self.logger.setLevel(logging.DEBUG)

        # Create string stream handler to capture logs
        self.log_stream = StringIO()
        self.handler = logging.StreamHandler(self.log_stream)
        self.handler.setLevel(logging.DEBUG)
        self.logger.addHandler(self.handler)

    def teardown_method(self):
        """Clean up logging and request ID."""
        self.logger.removeHandler(self.handler)
        self.handler.close()
        clear_request_id()

    def get_log_output(self) -> str:
        """Get captured log output."""
        return self.log_stream.getvalue()

    def test_log_info_with_context(self):
        """Test that log_info includes structured context."""
        set_request_id("test-request-789")

        log_info(self.logger, "Test message", user_id="user-123", action="test")

        output = self.get_log_output()
        assert "Test message" in output
        assert "request_id=test-request-789" in output
        assert "user_id=user-123" in output
        assert "action=test" in output

    def test_log_warning_with_context(self):
        """Test that log_warning includes structured context."""
        set_request_id("warn-request")

        log_warning(self.logger, "Warning message", code="W001")

        output = self.get_log_output()
        assert "Warning message" in output
        assert "request_id=warn-request" in output
        assert "code=W001" in output

    def test_log_error_with_context(self):
        """Test that log_error includes structured context."""
        set_request_id("error-request")

        log_error(self.logger, "Error occurred", error_type="ValueError")

        output = self.get_log_output()
        assert "Error occurred" in output
        assert "request_id=error-request" in output
        assert "error_type=ValueError" in output

    def test_log_without_request_id(self):
        """Test logging without request ID set."""
        # Don't set request ID
        log_info(self.logger, "Message without request ID", key="value")

        output = self.get_log_output()
        assert "Message without request ID" in output
        assert "key=value" in output
        # Should not have request_id in output
        assert "request_id=" not in output

    def test_log_redacts_secrets_in_context(self):
        """Test that secrets in log context are redacted."""
        set_request_id("redact-test")

        log_info(
            self.logger,
            "Processing request",
            token="ghp_secrettoken123",
            auth="Authorization: Bearer ghs_token456",
        )

        output = self.get_log_output()
        # Secrets should be redacted
        assert "ghp_secrettoken123" not in output
        assert "ghs_token456" not in output
        assert "ghp_***REDACTED***" in output
        assert "ghs_***REDACTED***" in output


class TestLogRedactionInAPI:
    """Test that API endpoints never log sensitive data."""

    def test_authorization_header_not_logged(self, client, reset_db, monkeypatch, caplog):
        """Test that Authorization header values are never logged."""
        # Set log level to capture all logs
        caplog.set_level(logging.DEBUG)

        # Mock auth to allow any token
        monkeypatch.setenv("HANDSFREE_AUTH_MODE", "dev")

        # Make request with Authorization header
        response = client.post(
            "/v1/command",
            json={
                "input": {"type": "text", "text": "list inbox"},
                "profile": "default",
                "client_context": {
                    "device": "test",
                    "locale": "en-US",
                    "timezone": "UTC",
                    "app_version": "0.1.0",
                },
            },
            headers={
                "Authorization": "Bearer ghp_mysecrettoken123456",
                "X-User-ID": "test-user",
            },
        )

        assert response.status_code == 200

        # Check that the token never appears in logs
        for record in caplog.records:
            # Check message
            assert "ghp_mysecrettoken123456" not in record.message
            # Check any args
            if hasattr(record, "args") and record.args:
                for arg in record.args:
                    if isinstance(arg, str):
                        assert "ghp_mysecrettoken123456" not in arg

    def test_request_id_in_command_logs(self, client, reset_db, monkeypatch, caplog):
        """Test that request ID appears in /v1/command logs."""
        caplog.set_level(logging.INFO)
        monkeypatch.setenv("HANDSFREE_AUTH_MODE", "dev")

        response = client.post(
            "/v1/command",
            json={
                "input": {"type": "text", "text": "what's my inbox"},
                "profile": "default",
                "client_context": {
                    "device": "test",
                    "locale": "en-US",
                    "timezone": "UTC",
                    "app_version": "0.1.0",
                },
            },
            headers={
                "X-Request-ID": "custom-request-id-123",
                "X-User-ID": "test-user",
            },
        )

        assert response.status_code == 200

        # Check that request ID appears in at least one log entry
        found_request_id = False
        for record in caplog.records:
            if "custom-request-id-123" in record.message:
                found_request_id = True
                break

        assert found_request_id, "Request ID should appear in logs"

    def test_generated_request_id_in_logs(self, client, reset_db, monkeypatch, caplog):
        """Test that generated request ID appears in logs when not provided."""
        caplog.set_level(logging.INFO)
        monkeypatch.setenv("HANDSFREE_AUTH_MODE", "dev")

        response = client.post(
            "/v1/command",
            json={
                "input": {"type": "text", "text": "list inbox"},
                "profile": "default",
                "client_context": {
                    "device": "test",
                    "locale": "en-US",
                    "timezone": "UTC",
                    "app_version": "0.1.0",
                },
            },
            headers={
                "X-User-ID": "test-user",
            },
        )

        assert response.status_code == 200

        # Check that a request_id (UUID format) appears in logs
        found_uuid_pattern = False
        uuid_pattern = re.compile(
            r"request_id=[a-f0-9]{8}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{12}"
        )

        for record in caplog.records:
            if uuid_pattern.search(record.message):
                found_uuid_pattern = True
                break

        assert found_uuid_pattern, "Generated request ID (UUID) should appear in logs"
