"""Tests for Redis-backed session context manager."""

import time

import pytest
import redis

from handsfree.commands.session_context import RedisSessionContext


@pytest.fixture
def redis_client():
    """Create a Redis client for testing."""
    try:
        client = redis.Redis(host="localhost", port=6379, db=15, decode_responses=False)
        # Test connection
        client.ping()
        # Clean up test data
        for key in client.scan_iter(match="test_session_ctx:*"):
            client.delete(key)
        yield client
        # Clean up after tests
        for key in client.scan_iter(match="test_session_ctx:*"):
            client.delete(key)
    except redis.ConnectionError:
        pytest.skip("Redis not available for testing")


@pytest.fixture
def redis_session_context(redis_client):
    """Create a Redis-backed session context manager for testing."""
    return RedisSessionContext(
        redis_client=redis_client, default_ttl_seconds=300, key_prefix="test_session_ctx:"
    )


@pytest.fixture
def fallback_session_context():
    """Create a session context with no Redis (uses in-memory fallback)."""
    return RedisSessionContext(redis_client=None, default_ttl_seconds=300)


class TestRedisSessionContextSetGet:
    """Test setting and getting session context with Redis."""

    def test_set_and_get_repo(self, redis_session_context: RedisSessionContext) -> None:
        """Test setting and retrieving repo context."""
        session_id = "session-123"
        redis_session_context.set_repo_pr(session_id, "owner/repo")

        context = redis_session_context.get_repo_pr(session_id)

        assert context["repo"] == "owner/repo"
        assert "pr_number" not in context

    def test_set_and_get_repo_pr(self, redis_session_context: RedisSessionContext) -> None:
        """Test setting and retrieving repo and PR context."""
        session_id = "session-456"
        redis_session_context.set_repo_pr(session_id, "owner/repo", pr_number=789)

        context = redis_session_context.get_repo_pr(session_id)

        assert context["repo"] == "owner/repo"
        assert context["pr_number"] == 789

    def test_get_nonexistent_session(self, redis_session_context: RedisSessionContext) -> None:
        """Test getting context for non-existent session."""
        context = redis_session_context.get_repo_pr("nonexistent-session")
        assert context == {}

    def test_get_with_fallback_repo(self, redis_session_context: RedisSessionContext) -> None:
        """Test getting context with fallback repo."""
        context = redis_session_context.get_repo_pr("nonexistent-session", fallback_repo="default/repo")
        assert context["repo"] == "default/repo"

    def test_empty_session_id(self, redis_session_context: RedisSessionContext) -> None:
        """Test handling of empty session ID."""
        redis_session_context.set_repo_pr("", "owner/repo")
        context = redis_session_context.get_repo_pr("")
        # Should not set/get with empty session_id
        assert context == {}

    def test_none_session_id(self, redis_session_context: RedisSessionContext) -> None:
        """Test handling of None session ID."""
        context = redis_session_context.get_repo_pr(None)
        assert context == {}

    def test_update_existing_session(self, redis_session_context: RedisSessionContext) -> None:
        """Test updating an existing session context."""
        session_id = "session-update"

        # Set initial context
        redis_session_context.set_repo_pr(session_id, "owner/repo1", pr_number=100)

        # Update with new context
        redis_session_context.set_repo_pr(session_id, "owner/repo2", pr_number=200)

        # Should have the updated context
        context = redis_session_context.get_repo_pr(session_id)
        assert context["repo"] == "owner/repo2"
        assert context["pr_number"] == 200


class TestRedisSessionContextPersistence:
    """Test that session context persists in Redis."""

    def test_context_persisted_in_redis(
        self, redis_session_context: RedisSessionContext, redis_client
    ) -> None:
        """Test that context is actually stored in Redis."""
        session_id = "session-persist"
        redis_session_context.set_repo_pr(session_id, "owner/repo", pr_number=123)

        # Check Redis directly
        redis_key = redis_session_context._make_redis_key(session_id)
        assert redis_client.exists(redis_key)

    def test_ttl_set_correctly(
        self, redis_session_context: RedisSessionContext, redis_client
    ) -> None:
        """Test that TTL is set correctly in Redis."""
        session_id = "session-ttl"
        redis_session_context.set_repo_pr(session_id, "owner/repo")

        redis_key = redis_session_context._make_redis_key(session_id)
        ttl = redis_client.ttl(redis_key)

        # TTL should be around 300 seconds (allow some tolerance)
        assert 295 <= ttl <= 305

    def test_context_expires(self, redis_client) -> None:
        """Test that session context expires after TTL."""
        # Create context with very short TTL
        short_ttl_context = RedisSessionContext(
            redis_client=redis_client, default_ttl_seconds=1, key_prefix="test_session_ctx:"
        )

        session_id = "session-expire"
        short_ttl_context.set_repo_pr(session_id, "owner/repo")

        # Verify it exists
        context = short_ttl_context.get_repo_pr(session_id)
        assert context["repo"] == "owner/repo"

        # Wait for expiry
        time.sleep(2)

        # Should be gone
        context = short_ttl_context.get_repo_pr(session_id)
        assert context == {}


class TestRedisSessionContextClear:
    """Test clearing session context."""

    def test_clear_session(self, redis_session_context: RedisSessionContext) -> None:
        """Test clearing a session context."""
        session_id = "session-clear"
        redis_session_context.set_repo_pr(session_id, "owner/repo", pr_number=123)

        # Verify it exists
        context = redis_session_context.get_repo_pr(session_id)
        assert context["repo"] == "owner/repo"

        # Clear it
        redis_session_context.clear_session(session_id)

        # Should be gone
        context = redis_session_context.get_repo_pr(session_id)
        assert context == {}

    def test_clear_nonexistent_session(
        self, redis_session_context: RedisSessionContext
    ) -> None:
        """Test clearing a non-existent session (should not error)."""
        redis_session_context.clear_session("nonexistent-session")
        # Should not raise error


class TestRedisSessionContextMultipleSessions:
    """Test managing multiple session contexts."""

    def test_independent_sessions(self, redis_session_context: RedisSessionContext) -> None:
        """Test that different sessions are independent."""
        redis_session_context.set_repo_pr("session-1", "owner/repo1", pr_number=100)
        redis_session_context.set_repo_pr("session-2", "owner/repo2", pr_number=200)
        redis_session_context.set_repo_pr("session-3", "owner/repo3", pr_number=300)

        # Each should have its own context
        ctx1 = redis_session_context.get_repo_pr("session-1")
        ctx2 = redis_session_context.get_repo_pr("session-2")
        ctx3 = redis_session_context.get_repo_pr("session-3")

        assert ctx1["repo"] == "owner/repo1"
        assert ctx1["pr_number"] == 100

        assert ctx2["repo"] == "owner/repo2"
        assert ctx2["pr_number"] == 200

        assert ctx3["repo"] == "owner/repo3"
        assert ctx3["pr_number"] == 300

    def test_clearing_one_session_doesnt_affect_others(
        self, redis_session_context: RedisSessionContext
    ) -> None:
        """Test that clearing one session doesn't affect others."""
        redis_session_context.set_repo_pr("session-1", "owner/repo1")
        redis_session_context.set_repo_pr("session-2", "owner/repo2")

        # Clear session-1
        redis_session_context.clear_session("session-1")

        # session-1 should be gone
        ctx1 = redis_session_context.get_repo_pr("session-1")
        assert ctx1 == {}

        # session-2 should still exist
        ctx2 = redis_session_context.get_repo_pr("session-2")
        assert ctx2["repo"] == "owner/repo2"


class TestFallbackSessionContext:
    """Test fallback to in-memory manager when Redis unavailable."""

    def test_set_get_without_redis(
        self, fallback_session_context: RedisSessionContext
    ) -> None:
        """Test set/get with in-memory fallback."""
        session_id = "fallback-session"
        fallback_session_context.set_repo_pr(session_id, "owner/repo", pr_number=456)

        context = fallback_session_context.get_repo_pr(session_id)
        assert context["repo"] == "owner/repo"
        assert context["pr_number"] == 456

    def test_clear_without_redis(
        self, fallback_session_context: RedisSessionContext
    ) -> None:
        """Test clear with in-memory fallback."""
        session_id = "fallback-clear"
        fallback_session_context.set_repo_pr(session_id, "owner/repo")

        # Verify it exists
        context = fallback_session_context.get_repo_pr(session_id)
        assert context["repo"] == "owner/repo"

        # Clear it
        fallback_session_context.clear_session(session_id)

        # Should be gone
        context = fallback_session_context.get_repo_pr(session_id)
        assert context == {}

    def test_fallback_with_fallback_repo(
        self, fallback_session_context: RedisSessionContext
    ) -> None:
        """Test fallback repo parameter works with in-memory fallback."""
        context = fallback_session_context.get_repo_pr(
            "nonexistent", fallback_repo="default/repo"
        )
        assert context["repo"] == "default/repo"
