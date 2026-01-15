"""Tests for session token management."""

import time
from datetime import UTC, datetime, timedelta
from unittest.mock import MagicMock

import pytest
import redis

from handsfree.sessions import SessionTokenManager


@pytest.fixture
def redis_client():
    """Create a Redis client for testing."""
    try:
        client = redis.Redis(host="localhost", port=6379, db=15, decode_responses=False)
        # Test connection
        client.ping()
        # Clean up test data
        for key in client.scan_iter(match="test_session:*"):
            client.delete(key)
        yield client
        # Clean up after tests
        for key in client.scan_iter(match="test_session:*"):
            client.delete(key)
    except redis.ConnectionError:
        pytest.skip("Redis not available for testing")


@pytest.fixture
def session_manager(redis_client):
    """Create a SessionTokenManager for testing."""
    return SessionTokenManager(
        redis_client=redis_client, default_ttl_hours=24, key_prefix="test_session:"
    )


class TestSessionTokenManager:
    """Tests for SessionTokenManager."""

    def test_create_session(self, session_manager):
        """Test creating a new session token."""
        user_id = "user-123"
        device_id = "device-456"

        session = session_manager.create_session(user_id, device_id)

        assert session.token is not None
        assert len(session.token) > 32  # URL-safe tokens are longer than raw bytes
        assert session.user_id == user_id
        assert session.device_id == device_id
        assert session.created_at <= datetime.now(UTC)
        assert session.expires_at > datetime.now(UTC)

    def test_create_session_with_custom_ttl(self, session_manager):
        """Test creating a session with custom TTL."""
        user_id = "user-123"
        device_id = "device-456"
        custom_ttl = 48

        session = session_manager.create_session(user_id, device_id, ttl_hours=custom_ttl)

        expected_expiry = datetime.now(UTC) + timedelta(hours=custom_ttl)
        # Allow 1 second tolerance for timing
        assert abs((session.expires_at - expected_expiry).total_seconds()) < 1

    def test_create_session_with_metadata(self, session_manager):
        """Test creating a session with metadata."""
        user_id = "user-123"
        device_id = "device-456"
        metadata = {"device_type": "wearable", "app_version": "1.0.0", "os": "Android"}

        session = session_manager.create_session(user_id, device_id, metadata=metadata)

        assert session.metadata == metadata

    def test_validate_session_success(self, session_manager):
        """Test validating a valid session token."""
        user_id = "user-123"
        device_id = "device-456"

        # Create session
        created_session = session_manager.create_session(user_id, device_id)

        # Validate it
        validated_session = session_manager.validate_session(created_session.token)

        assert validated_session is not None
        assert validated_session.user_id == user_id
        assert validated_session.device_id == device_id
        assert validated_session.token == created_session.token

    def test_validate_session_invalid_token(self, session_manager):
        """Test validating an invalid token returns None."""
        invalid_token = "invalid_token_12345"

        result = session_manager.validate_session(invalid_token)

        assert result is None

    def test_validate_session_nonexistent_token(self, session_manager):
        """Test validating a non-existent token returns None."""
        # Generate a valid-looking token that doesn't exist
        import secrets

        fake_token = secrets.token_urlsafe(32)

        result = session_manager.validate_session(fake_token)

        assert result is None

    def test_revoke_session(self, session_manager):
        """Test revoking a session token."""
        user_id = "user-123"
        device_id = "device-456"

        # Create and validate session
        session = session_manager.create_session(user_id, device_id)
        assert session_manager.validate_session(session.token) is not None

        # Revoke it
        success = session_manager.revoke_session(session.token)
        assert success is True

        # Verify it's invalid now
        assert session_manager.validate_session(session.token) is None

    def test_revoke_nonexistent_session(self, session_manager):
        """Test revoking a non-existent session returns False."""
        import secrets

        fake_token = secrets.token_urlsafe(32)

        success = session_manager.revoke_session(fake_token)
        assert success is False

    def test_revoke_user_sessions(self, session_manager):
        """Test revoking all sessions for a user."""
        user_id = "user-123"

        # Create multiple sessions for the user
        session1 = session_manager.create_session(user_id, "device-1")
        session2 = session_manager.create_session(user_id, "device-2")
        session3 = session_manager.create_session(user_id, "device-3")

        # Create a session for a different user
        other_session = session_manager.create_session("user-999", "device-999")

        # Revoke all sessions for user-123
        count = session_manager.revoke_user_sessions(user_id)
        assert count == 3

        # Verify user-123's sessions are revoked
        assert session_manager.validate_session(session1.token) is None
        assert session_manager.validate_session(session2.token) is None
        assert session_manager.validate_session(session3.token) is None

        # Verify other user's session is still valid
        assert session_manager.validate_session(other_session.token) is not None

    def test_revoke_device_sessions(self, session_manager):
        """Test revoking all sessions for a device."""
        device_id = "device-123"

        # Create multiple sessions for the device (different users)
        session1 = session_manager.create_session("user-1", device_id)
        session2 = session_manager.create_session("user-2", device_id)

        # Create a session for a different device
        other_session = session_manager.create_session("user-1", "device-999")

        # Revoke all sessions for device-123
        count = session_manager.revoke_device_sessions(device_id)
        assert count == 2

        # Verify device-123's sessions are revoked
        assert session_manager.validate_session(session1.token) is None
        assert session_manager.validate_session(session2.token) is None

        # Verify other device's session is still valid
        assert session_manager.validate_session(other_session.token) is not None

    def test_extend_session(self, session_manager):
        """Test extending a session's expiration time."""
        user_id = "user-123"
        device_id = "device-456"

        # Create session with short TTL
        session = session_manager.create_session(user_id, device_id, ttl_hours=1)

        # Extend the session
        success = session_manager.extend_session(session.token, additional_hours=2)
        assert success is True

        # Validate and check new expiration
        extended_session = session_manager.validate_session(session.token)
        assert extended_session is not None

        # New expiration should be ~3 hours from now (1 + 2)
        expected_expiry = datetime.now(UTC) + timedelta(hours=3)
        assert abs((extended_session.expires_at - expected_expiry).total_seconds()) < 2

    def test_extend_nonexistent_session(self, session_manager):
        """Test extending a non-existent session returns False."""
        import secrets

        fake_token = secrets.token_urlsafe(32)

        success = session_manager.extend_session(fake_token, additional_hours=1)
        assert success is False

    def test_session_auto_expiration(self, session_manager):
        """Test that sessions auto-expire in Redis."""
        user_id = "user-123"
        device_id = "device-456"

        # Create session with very short TTL (1 second)
        # Redis minimum TTL is 1 second (since we convert to int)
        session = session_manager.create_session(user_id, device_id, ttl_hours=1 / 3600)

        # Verify it exists initially
        assert session_manager.validate_session(session.token) is not None

        # Wait for expiration (1 second + buffer)
        time.sleep(2)

        # Verify it's expired
        assert session_manager.validate_session(session.token) is None

    def test_token_hashing(self, session_manager):
        """Test that tokens are hashed before storage."""
        user_id = "user-123"
        device_id = "device-456"

        session = session_manager.create_session(user_id, device_id)

        # The token itself should not be stored in Redis
        # Only the hash should be used as a key
        token_hash = session_manager._hash_token(session.token)
        redis_key = session_manager._make_redis_key(token_hash)

        # Verify the key exists
        assert session_manager.redis.exists(redis_key)

        # Verify we can't find the raw token in Redis
        # (This is a security check - tokens should not be stored in plaintext)
        pattern = f"{session_manager.key_prefix}*"
        for key in session_manager.redis.scan_iter(match=pattern):
            assert session.token.encode() not in key

    def test_concurrent_sessions_same_user(self, session_manager):
        """Test that a user can have multiple concurrent sessions."""
        user_id = "user-123"

        # Create multiple sessions for the same user
        session1 = session_manager.create_session(user_id, "device-1")
        session2 = session_manager.create_session(user_id, "device-2")
        session3 = session_manager.create_session(user_id, "device-3")

        # All should be valid
        assert session_manager.validate_session(session1.token) is not None
        assert session_manager.validate_session(session2.token) is not None
        assert session_manager.validate_session(session3.token) is not None

        # Each should be independent
        session_manager.revoke_session(session1.token)
        assert session_manager.validate_session(session1.token) is None
        assert session_manager.validate_session(session2.token) is not None
        assert session_manager.validate_session(session3.token) is not None

    def test_session_token_uniqueness(self, session_manager):
        """Test that generated tokens are unique."""
        tokens = set()

        # Generate 100 tokens
        for i in range(100):
            session = session_manager.create_session(f"user-{i}", f"device-{i}")
            tokens.add(session.token)

        # All should be unique
        assert len(tokens) == 100


class TestSessionTokenManagerEdgeCases:
    """Edge case tests for SessionTokenManager."""

    def test_session_manager_with_redis_error(self):
        """Test handling of Redis connection errors."""
        # Create a mock Redis client that always fails
        mock_redis = MagicMock()
        mock_redis.hgetall.side_effect = redis.RedisError("Connection failed")

        manager = SessionTokenManager(mock_redis)

        # Validation should handle the error gracefully
        result = manager.validate_session("any_token")
        assert result is None

    def test_session_with_empty_metadata(self, session_manager):
        """Test creating a session with empty metadata."""
        session = session_manager.create_session("user-123", "device-456", metadata={})

        assert session.metadata == {}

        # Validate and verify metadata is preserved
        validated = session_manager.validate_session(session.token)
        assert validated is not None
        assert validated.metadata == {}

    def test_session_with_complex_metadata(self, session_manager):
        """Test session with complex metadata structures."""
        metadata = {
            "device_type": "wearable",
            "nested": {"key": "value"},
            "list": [1, 2, 3],
            "number": 42,
        }

        session = session_manager.create_session("user-123", "device-456", metadata=metadata)

        # Validate and verify metadata roundtrip
        validated = session_manager.validate_session(session.token)
        assert validated is not None
        assert validated.metadata == metadata
