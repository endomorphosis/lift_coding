"""Tests for Redis-backed pending actions manager."""

import time
from datetime import UTC, datetime

import pytest
import redis

from handsfree.commands.pending_actions import RedisPendingActionManager


@pytest.fixture
def redis_client():
    """Create a Redis client for testing."""
    try:
        client = redis.Redis(host="localhost", port=6379, db=15, decode_responses=False)
        # Test connection
        client.ping()
        # Clean up test data
        for key in client.scan_iter(match="test_pending:*"):
            client.delete(key)
        yield client
        # Clean up after tests
        for key in client.scan_iter(match="test_pending:*"):
            client.delete(key)
    except redis.ConnectionError:
        pytest.skip("Redis not available for testing")


@pytest.fixture
def redis_manager(redis_client):
    """Create a Redis-backed pending action manager for testing."""
    return RedisPendingActionManager(
        redis_client=redis_client, default_expiry_seconds=60, key_prefix="test_pending:"
    )


@pytest.fixture
def fallback_manager():
    """Create a manager with no Redis (uses in-memory fallback)."""
    return RedisPendingActionManager(redis_client=None, default_expiry_seconds=60)


class TestRedisPendingActionCreation:
    """Test creating pending actions with Redis backend."""

    def test_create_action(self, redis_manager: RedisPendingActionManager) -> None:
        """Test creating a new pending action in Redis."""
        action = redis_manager.create(
            intent_name="pr.request_review",
            entities={"reviewers": ["alice"], "pr_number": 123},
            summary="Request review from alice on PR 123",
        )

        assert action.token is not None
        assert len(action.token) > 20
        assert action.intent_name == "pr.request_review"
        assert action.entities["reviewers"] == ["alice"]
        assert action.summary == "Request review from alice on PR 123"
        assert action.expires_at > datetime.now(UTC)

    def test_create_with_custom_expiry(self, redis_manager: RedisPendingActionManager) -> None:
        """Test creating action with custom expiry time."""
        action = redis_manager.create(
            intent_name="pr.merge",
            entities={"pr_number": 456},
            summary="Merge PR 456",
            expiry_seconds=120,
        )

        time_until_expiry = (action.expires_at - datetime.now(UTC)).total_seconds()
        assert 115 < time_until_expiry < 125

    def test_create_with_user_id(self, redis_manager: RedisPendingActionManager) -> None:
        """Test creating action with user ID."""
        action = redis_manager.create(
            intent_name="pr.merge",
            entities={},
            summary="Test",
            user_id="user123",
        )

        assert action.user_id == "user123"

    def test_unique_tokens(self, redis_manager: RedisPendingActionManager) -> None:
        """Test that each action gets a unique token."""
        action1 = redis_manager.create("intent1", {}, "summary1")
        action2 = redis_manager.create("intent2", {}, "summary2")

        assert action1.token != action2.token

    def test_action_persisted_in_redis(
        self, redis_manager: RedisPendingActionManager, redis_client
    ) -> None:
        """Test that actions are actually stored in Redis."""
        action = redis_manager.create("test.intent", {"key": "value"}, "Test action")

        # Check Redis directly
        redis_key = redis_manager._make_redis_key(action.token)
        assert redis_client.exists(redis_key)

    def test_ttl_set_correctly(
        self, redis_manager: RedisPendingActionManager, redis_client
    ) -> None:
        """Test that TTL is set correctly in Redis."""
        action = redis_manager.create("test.intent", {}, "Test", expiry_seconds=300)  # 5 minutes

        redis_key = redis_manager._make_redis_key(action.token)
        ttl = redis_client.ttl(redis_key)

        # TTL should be around 300 seconds (allow some tolerance)
        assert 295 <= ttl <= 305


class TestRedisPendingActionRetrieval:
    """Test retrieving pending actions from Redis."""

    def test_get_existing_action(self, redis_manager: RedisPendingActionManager) -> None:
        """Test retrieving an existing action."""
        created = redis_manager.create("test.intent", {"key": "value"}, "Test action")
        retrieved = redis_manager.get(created.token)

        assert retrieved is not None
        assert retrieved.token == created.token
        assert retrieved.intent_name == "test.intent"
        assert retrieved.entities["key"] == "value"

    def test_get_nonexistent_action(self, redis_manager: RedisPendingActionManager) -> None:
        """Test retrieving a non-existent action."""
        result = redis_manager.get("nonexistent-token")
        assert result is None

    def test_get_expired_action(self, redis_manager: RedisPendingActionManager) -> None:
        """Test that expired actions return None."""
        action = redis_manager.create(
            "test.intent",
            {},
            "Test",
            expiry_seconds=1,
        )

        # Wait for expiry
        time.sleep(2)

        # Should return None due to Redis auto-expiry
        result = redis_manager.get(action.token)
        assert result is None

    def test_get_complex_entities(self, redis_manager: RedisPendingActionManager) -> None:
        """Test retrieving action with complex nested entities."""
        complex_entities = {
            "repo": "owner/repo",
            "pr_number": 456,
            "options": {
                "merge_method": "squash",
                "delete_branch": True,
            },
            "labels": ["urgent", "bug-fix"],
        }

        action = redis_manager.create("test.intent", complex_entities, "Test")
        retrieved = redis_manager.get(action.token)

        assert retrieved is not None
        assert retrieved.entities == complex_entities


class TestRedisPendingActionConfirmation:
    """Test confirming pending actions with atomic semantics."""

    def test_confirm_action(self, redis_manager: RedisPendingActionManager) -> None:
        """Test confirming a pending action."""
        created = redis_manager.create("test.intent", {"data": "value"}, "Test action")
        confirmed = redis_manager.confirm(created.token)

        assert confirmed is not None
        assert confirmed.token == created.token
        assert confirmed.intent_name == "test.intent"

        # Action should be removed after confirmation
        result = redis_manager.get(created.token)
        assert result is None

    def test_confirm_nonexistent(self, redis_manager: RedisPendingActionManager) -> None:
        """Test confirming a non-existent action."""
        result = redis_manager.confirm("nonexistent-token")
        assert result is None

    def test_confirm_expired(self, redis_manager: RedisPendingActionManager) -> None:
        """Test confirming an expired action."""
        action = redis_manager.create("test.intent", {}, "Test", expiry_seconds=1)
        time.sleep(2)

        result = redis_manager.confirm(action.token)
        assert result is None

    def test_atomic_consume(self, redis_manager: RedisPendingActionManager, redis_client) -> None:
        """Test that confirmation consumes the token atomically."""
        action = redis_manager.create("test.intent", {}, "Test")

        # First confirmation should succeed
        result1 = redis_manager.confirm(action.token)
        assert result1 is not None

        # Second confirmation should fail (already consumed)
        result2 = redis_manager.confirm(action.token)
        assert result2 is None

        # Verify it's gone from Redis
        redis_key = redis_manager._make_redis_key(action.token)
        assert not redis_client.exists(redis_key)


class TestRedisPendingActionCancellation:
    """Test cancelling pending actions."""

    def test_cancel_action(self, redis_manager: RedisPendingActionManager) -> None:
        """Test cancelling a pending action."""
        created = redis_manager.create("test.intent", {}, "Test action")
        result = redis_manager.cancel(created.token)

        assert result is True

        # Action should be removed
        retrieved = redis_manager.get(created.token)
        assert retrieved is None

    def test_cancel_nonexistent(self, redis_manager: RedisPendingActionManager) -> None:
        """Test cancelling a non-existent action."""
        result = redis_manager.cancel("nonexistent-token")
        assert result is False

    def test_cancel_expired(self, redis_manager: RedisPendingActionManager) -> None:
        """Test cancelling an expired action."""
        action = redis_manager.create("test.intent", {}, "Test", expiry_seconds=1)
        time.sleep(2)

        result = redis_manager.cancel(action.token)
        assert result is False


class TestRedisPendingActionCleanup:
    """Test cleanup operations."""

    def test_cleanup_expired(self, redis_manager: RedisPendingActionManager) -> None:
        """Test cleanup method (no-op for Redis backend)."""
        # Create some actions
        redis_manager.create("test1", {}, "Test1", expiry_seconds=1)
        redis_manager.create("test2", {}, "Test2", expiry_seconds=5)

        time.sleep(2)

        # Cleanup returns 0 for Redis (auto-expiry handles it)
        removed_count = redis_manager.cleanup_expired()
        assert removed_count == 0


class TestFallbackManager:
    """Test fallback to in-memory manager when Redis unavailable."""

    def test_create_without_redis(self, fallback_manager: RedisPendingActionManager) -> None:
        """Test creating action with in-memory fallback."""
        action = fallback_manager.create("test.intent", {"key": "value"}, "Test")

        assert action.token is not None
        assert action.intent_name == "test.intent"

    def test_get_without_redis(self, fallback_manager: RedisPendingActionManager) -> None:
        """Test retrieving action with in-memory fallback."""
        created = fallback_manager.create("test.intent", {"key": "value"}, "Test")
        retrieved = fallback_manager.get(created.token)

        assert retrieved is not None
        assert retrieved.token == created.token

    def test_confirm_without_redis(self, fallback_manager: RedisPendingActionManager) -> None:
        """Test confirming action with in-memory fallback."""
        created = fallback_manager.create("test.intent", {}, "Test")
        confirmed = fallback_manager.confirm(created.token)

        assert confirmed is not None
        assert confirmed.token == created.token

        # Should be removed
        result = fallback_manager.get(created.token)
        assert result is None

    def test_cancel_without_redis(self, fallback_manager: RedisPendingActionManager) -> None:
        """Test cancelling action with in-memory fallback."""
        created = fallback_manager.create("test.intent", {}, "Test")
        result = fallback_manager.cancel(created.token)

        assert result is True

    def test_cleanup_without_redis(self, fallback_manager: RedisPendingActionManager) -> None:
        """Test cleanup with in-memory fallback."""
        fallback_manager.create("test1", {}, "Test1", expiry_seconds=1)
        fallback_manager.create("test2", {}, "Test2", expiry_seconds=5)

        time.sleep(2)

        # Cleanup should work with fallback
        removed_count = fallback_manager.cleanup_expired()
        assert removed_count == 1
