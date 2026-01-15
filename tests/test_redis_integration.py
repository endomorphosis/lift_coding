"""Integration tests for Redis-backed components."""

import pytest
import redis

from handsfree.commands.pending_actions import RedisPendingActionManager
from handsfree.commands.session_context import RedisSessionContext
from handsfree.redis_client import get_redis_client


@pytest.fixture
def redis_integration_client():
    """Get a Redis client for integration testing, skip if unavailable."""
    client = get_redis_client()
    if client is None:
        pytest.skip("Redis not available for integration testing")

    # Clean up test data
    for key in client.scan_iter(match="integration_test:*"):
        client.delete(key)

    yield client

    # Clean up after tests
    for key in client.scan_iter(match="integration_test:*"):
        client.delete(key)


class TestRedisIntegration:
    """Integration tests for Redis-backed components."""

    def test_pending_action_and_session_context_together(
        self, redis_integration_client: redis.Redis
    ) -> None:
        """Test using both Redis-backed managers together."""
        # Create managers
        pending_mgr = RedisPendingActionManager(
            redis_client=redis_integration_client,
            default_expiry_seconds=60,
            key_prefix="integration_test:pending:",
        )

        session_ctx = RedisSessionContext(
            redis_client=redis_integration_client,
            default_ttl_seconds=300,
            key_prefix="integration_test:session:",
        )

        # Create a pending action
        action = pending_mgr.create(
            intent_name="pr.merge", entities={"pr_number": 123}, summary="Merge PR 123"
        )

        # Set session context
        session_id = "test-session-123"
        session_ctx.set_repo_pr(session_id, "owner/repo", pr_number=123)

        # Verify both are retrievable
        retrieved_action = pending_mgr.get(action.token)
        assert retrieved_action is not None
        assert retrieved_action.intent_name == "pr.merge"

        retrieved_context = session_ctx.get_repo_pr(session_id)
        assert retrieved_context["repo"] == "owner/repo"
        assert retrieved_context["pr_number"] == 123

        # Confirm the action (consume it)
        confirmed = pending_mgr.confirm(action.token)
        assert confirmed is not None

        # Verify it's consumed
        assert pending_mgr.get(action.token) is None

        # Session context should still exist
        retrieved_context = session_ctx.get_repo_pr(session_id)
        assert retrieved_context["repo"] == "owner/repo"

    def test_redis_client_factory_respects_env_vars(self) -> None:
        """Test that get_redis_client respects environment variables."""
        import os

        # Save original value
        original_enabled = os.environ.get("REDIS_ENABLED")

        try:
            # Test with REDIS_ENABLED=false
            os.environ["REDIS_ENABLED"] = "false"
            client = get_redis_client()
            assert client is None

            # Test with REDIS_ENABLED=true (should connect to localhost)
            os.environ["REDIS_ENABLED"] = "true"
            client = get_redis_client()
            # This may be None if Redis isn't running, which is fine
            # We just verify the factory respects the env var

        finally:
            # Restore original value
            if original_enabled is not None:
                os.environ["REDIS_ENABLED"] = original_enabled
            elif "REDIS_ENABLED" in os.environ:
                del os.environ["REDIS_ENABLED"]

    def test_managers_work_with_no_redis(self) -> None:
        """Test that managers gracefully fall back when Redis is unavailable."""
        # Create managers with no Redis client
        pending_mgr = RedisPendingActionManager(redis_client=None)
        session_ctx = RedisSessionContext(redis_client=None)

        # Should still work with in-memory fallback
        action = pending_mgr.create("test.intent", {}, "Test action")
        assert action is not None
        assert pending_mgr.get(action.token) is not None

        session_ctx.set_repo_pr("session-1", "owner/repo")
        context = session_ctx.get_repo_pr("session-1")
        assert context["repo"] == "owner/repo"

    def test_multiple_pending_actions_lifecycle(
        self, redis_integration_client: redis.Redis
    ) -> None:
        """Test managing multiple pending actions with realistic workflow."""
        pending_mgr = RedisPendingActionManager(
            redis_client=redis_integration_client,
            key_prefix="integration_test:multi:",
        )

        # Create multiple actions
        action1 = pending_mgr.create("pr.merge", {"pr": 100}, "Merge PR 100")
        action2 = pending_mgr.create("pr.comment", {"pr": 200}, "Comment on PR 200")
        action3 = pending_mgr.create("pr.review", {"pr": 300}, "Review PR 300")

        # All should be retrievable
        assert pending_mgr.get(action1.token) is not None
        assert pending_mgr.get(action2.token) is not None
        assert pending_mgr.get(action3.token) is not None

        # Confirm action1
        confirmed1 = pending_mgr.confirm(action1.token)
        assert confirmed1 is not None
        assert confirmed1.token == action1.token

        # Cancel action2
        cancelled = pending_mgr.cancel(action2.token)
        assert cancelled is True

        # Action1 and action2 should be gone
        assert pending_mgr.get(action1.token) is None
        assert pending_mgr.get(action2.token) is None

        # Action3 should still exist
        assert pending_mgr.get(action3.token) is not None

        # Confirm action3
        confirmed3 = pending_mgr.confirm(action3.token)
        assert confirmed3 is not None

        # All should be gone now
        assert pending_mgr.get(action1.token) is None
        assert pending_mgr.get(action2.token) is None
        assert pending_mgr.get(action3.token) is None

    def test_session_context_realistic_workflow(
        self, redis_integration_client: redis.Redis
    ) -> None:
        """Test session context with realistic multi-session workflow."""
        session_ctx = RedisSessionContext(
            redis_client=redis_integration_client,
            key_prefix="integration_test:workflow:",
        )

        # User1 browsing PR 100
        session_ctx.set_repo_pr("user1-session", "owner/repo", pr_number=100)

        # User2 browsing PR 200
        session_ctx.set_repo_pr("user2-session", "owner/repo", pr_number=200)

        # User3 just looking at repo
        session_ctx.set_repo_pr("user3-session", "owner/repo")

        # Each should have independent context
        ctx1 = session_ctx.get_repo_pr("user1-session")
        assert ctx1["pr_number"] == 100

        ctx2 = session_ctx.get_repo_pr("user2-session")
        assert ctx2["pr_number"] == 200

        ctx3 = session_ctx.get_repo_pr("user3-session")
        assert "pr_number" not in ctx3

        # User1 switches to PR 150
        session_ctx.set_repo_pr("user1-session", "owner/repo", pr_number=150)

        # User1's context should update
        ctx1_updated = session_ctx.get_repo_pr("user1-session")
        assert ctx1_updated["pr_number"] == 150

        # Other sessions unchanged
        ctx2_check = session_ctx.get_repo_pr("user2-session")
        assert ctx2_check["pr_number"] == 200

        # Clear user2's session
        session_ctx.clear_session("user2-session")

        # User2's context should be gone
        ctx2_cleared = session_ctx.get_repo_pr("user2-session")
        assert ctx2_cleared == {}

        # Other sessions unchanged
        ctx1_check = session_ctx.get_repo_pr("user1-session")
        assert ctx1_check["pr_number"] == 150
