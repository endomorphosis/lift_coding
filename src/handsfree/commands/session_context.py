"""Session context manager for tracking repo/PR state across voice commands."""

import json
import logging
from typing import Any, Optional

import redis

logger = logging.getLogger(__name__)


class SessionContext:
    """Manages session context for voice commands.

    Tracks the last referenced repo/PR from commands like inbox.list,
    pr.summarize, and checks.status so that subsequent side-effect commands
    (like pr.request_review, checks.rerun, pr.comment) can omit the repo/PR
    and still work correctly.
    """

    def __init__(self) -> None:
        """Initialize the session context manager."""
        # Maps session_id -> {"repo": str, "pr_number": int}
        self._contexts: dict[str, dict[str, Any]] = {}

    def set_repo_pr(self, session_id: str, repo: str, pr_number: int | None = None) -> None:
        """Store repo/PR context for a session.

        Args:
            session_id: Session identifier
            repo: Repository name (e.g., "owner/repo")
            pr_number: Optional PR number
        """
        if not session_id:
            return

        context = {"repo": repo}
        if pr_number is not None:
            context["pr_number"] = pr_number

        self._contexts[session_id] = context

    def get_repo_pr(
        self, session_id: str | None, fallback_repo: str | None = None
    ) -> dict[str, Any]:
        """Retrieve repo/PR context for a session.

        Args:
            session_id: Session identifier
            fallback_repo: Optional fallback repo if no session context exists

        Returns:
            Dictionary with "repo" and optionally "pr_number" keys
        """
        if not session_id or session_id not in self._contexts:
            if fallback_repo:
                return {"repo": fallback_repo}
            return {}

        return self._contexts[session_id].copy()

    def clear_session(self, session_id: str) -> None:
        """Clear context for a specific session.

        Args:
            session_id: Session identifier to clear
        """
        if session_id in self._contexts:
            del self._contexts[session_id]


class RedisSessionContext:
    """Redis-backed session context manager with persistence.

    This implementation provides:
    - Session context that survives process restarts
    - Automatic expiration via Redis TTL
    - Fallback to in-memory if Redis unavailable
    """

    def __init__(
        self,
        redis_client: Optional[redis.Redis] = None,
        default_ttl_seconds: int = 3600,
        key_prefix: str = "session_context:",
    ) -> None:
        """Initialize the Redis-backed session context manager.

        Args:
            redis_client: Redis client instance (None to use in-memory fallback)
            default_ttl_seconds: Default TTL for session context (default: 1 hour)
            key_prefix: Prefix for Redis keys (default: "session_context:")
        """
        self.redis = redis_client
        self.default_ttl_seconds = default_ttl_seconds
        self.key_prefix = key_prefix

        # Fallback to in-memory if Redis unavailable
        if self.redis is None:
            logger.warning("Redis not available, using in-memory fallback for session context")
            self._fallback = SessionContext()
        else:
            logger.info("Using Redis-backed session context storage")
            self._fallback = None

    def _make_redis_key(self, session_id: str) -> str:
        """Create a Redis key for a session."""
        return f"{self.key_prefix}{session_id}"

    def set_repo_pr(self, session_id: str, repo: str, pr_number: int | None = None) -> None:
        """Store repo/PR context for a session.

        Args:
            session_id: Session identifier
            repo: Repository name (e.g., "owner/repo")
            pr_number: Optional PR number
        """
        if not session_id:
            return

        # Use fallback if Redis unavailable
        if self._fallback is not None:
            self._fallback.set_repo_pr(session_id, repo, pr_number)
            return

        context = {"repo": repo}
        if pr_number is not None:
            context["pr_number"] = pr_number

        try:
            redis_key = self._make_redis_key(session_id)
            serialized = json.dumps(context)
            # Store with TTL to auto-expire inactive sessions
            self.redis.setex(redis_key, self.default_ttl_seconds, serialized)
            logger.debug(
                "Set session context for %s: repo=%s, pr=%s", session_id[:8], repo, pr_number
            )
        except redis.RedisError as e:
            logger.error("Redis error setting session context: %s", e)

    def get_repo_pr(
        self, session_id: str | None, fallback_repo: str | None = None
    ) -> dict[str, Any]:
        """Retrieve repo/PR context for a session.

        Args:
            session_id: Session identifier
            fallback_repo: Optional fallback repo if no session context exists

        Returns:
            Dictionary with "repo" and optionally "pr_number" keys
        """
        # Use fallback if Redis unavailable
        if self._fallback is not None:
            return self._fallback.get_repo_pr(session_id, fallback_repo)

        if not session_id:
            if fallback_repo:
                return {"repo": fallback_repo}
            return {}

        try:
            redis_key = self._make_redis_key(session_id)
            data = self.redis.get(redis_key)

            if data is None:
                if fallback_repo:
                    return {"repo": fallback_repo}
                return {}

            # Decode if bytes
            if isinstance(data, bytes):
                data = data.decode()

            context = json.loads(data)
            logger.debug("Retrieved session context for %s: %s", session_id[:8], context)
            return context

        except redis.RedisError as e:
            logger.error("Redis error getting session context: %s", e)
            if fallback_repo:
                return {"repo": fallback_repo}
            return {}
        except json.JSONDecodeError as e:
            logger.error("Error deserializing session context: %s", e)
            if fallback_repo:
                return {"repo": fallback_repo}
            return {}

    def clear_session(self, session_id: str) -> None:
        """Clear context for a specific session.

        Args:
            session_id: Session identifier to clear
        """
        # Use fallback if Redis unavailable
        if self._fallback is not None:
            self._fallback.clear_session(session_id)
            return

        try:
            redis_key = self._make_redis_key(session_id)
            self.redis.delete(redis_key)
            logger.debug("Cleared session context for %s", session_id[:8])
        except redis.RedisError as e:
            logger.error("Redis error clearing session context: %s", e)
