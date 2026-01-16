"""Pending action management for confirmation flow."""

import json
import logging
import secrets
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from types import SimpleNamespace
from typing import Any

try:
    import redis  # type: ignore

    REDIS_AVAILABLE = True
except ImportError:  # pragma: no cover

    class _RedisStubError(Exception):
        pass

    redis = SimpleNamespace(  # type: ignore
        Redis=object,
        RedisError=_RedisStubError,
        WatchError=_RedisStubError,
    )
    REDIS_AVAILABLE = False

logger = logging.getLogger(__name__)


@dataclass
class PendingAction:
    """A pending action awaiting confirmation."""

    token: str
    intent_name: str
    entities: dict[str, Any]
    summary: str
    expires_at: datetime
    user_id: str | None = None

    def is_expired(self) -> bool:
        """Check if this action has expired."""
        return datetime.now(UTC) >= self.expires_at

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for API responses."""
        return {
            "token": self.token,
            "expires_at": self.expires_at.isoformat(),
            "summary": self.summary,
        }


class PendingActionManager:
    """Manage pending actions requiring confirmation."""

    def __init__(self, default_expiry_seconds: int = 60) -> None:
        """Initialize the manager.

        Args:
            default_expiry_seconds: Default time until actions expire (default: 60s)
        """
        self.default_expiry_seconds = default_expiry_seconds
        # In-memory storage: token -> PendingAction
        # In production, this should use Redis or similar
        self._pending: dict[str, PendingAction] = {}

    def create(
        self,
        intent_name: str,
        entities: dict[str, Any],
        summary: str,
        user_id: str | None = None,
        expiry_seconds: int | None = None,
    ) -> PendingAction:
        """Create a new pending action.

        Args:
            intent_name: The intent to execute on confirmation
            entities: The entities extracted from the command
            summary: Human-readable description for confirmation
            user_id: Optional user identifier
            expiry_seconds: Custom expiry time, or use default

        Returns:
            PendingAction with a unique token
        """
        # Generate secure random token
        token = secrets.token_urlsafe(32)

        # Calculate expiry time
        expiry = expiry_seconds or self.default_expiry_seconds
        expires_at = datetime.now(UTC) + timedelta(seconds=expiry)

        action = PendingAction(
            token=token,
            intent_name=intent_name,
            entities=entities,
            summary=summary,
            expires_at=expires_at,
            user_id=user_id,
        )

        self._pending[token] = action
        return action

    def get(self, token: str) -> PendingAction | None:
        """Retrieve a pending action by token.

        Args:
            token: The action token

        Returns:
            PendingAction if found and not expired, None otherwise
        """
        action = self._pending.get(token)
        if action is None:
            return None

        if action.is_expired():
            # Clean up expired action
            del self._pending[token]
            return None

        return action

    def confirm(self, token: str) -> PendingAction | None:
        """Confirm and consume a pending action.

        Args:
            token: The action token

        Returns:
            PendingAction if found and confirmed, None if not found or expired
        """
        action = self.get(token)
        if action is None:
            return None

        # Remove from pending after confirmation
        del self._pending[token]
        return action

    def cancel(self, token: str) -> bool:
        """Cancel a pending action.

        Args:
            token: The action token

        Returns:
            True if action was cancelled, False if not found or expired
        """
        action = self.get(token)
        if action is None:
            return False

        del self._pending[token]
        return True

    def cleanup_expired(self) -> int:
        """Remove all expired actions.

        Returns:
            Number of expired actions removed
        """
        now = datetime.now(UTC)
        expired_tokens = [
            token for token, action in self._pending.items() if action.expires_at <= now
        ]

        for token in expired_tokens:
            del self._pending[token]

        return len(expired_tokens)


class RedisPendingActionManager:
    """Redis-backed pending action manager with atomic operations.

    This implementation provides:
    - Persistent storage across process restarts
    - Atomic token consumption (exactly-once semantics)
    - Automatic expiration via Redis TTL
    - Fallback to in-memory if Redis unavailable
    """

    def __init__(
        self,
        redis_client: redis.Redis | None = None,
        default_expiry_seconds: int = 60,
        key_prefix: str = "pending_action:",
    ) -> None:
        """Initialize the Redis-backed manager.

        Args:
            redis_client: Redis client instance (None to use in-memory fallback)
            default_expiry_seconds: Default time until actions expire (default: 60s)
            key_prefix: Prefix for Redis keys (default: "pending_action:")
        """
        self.redis = redis_client
        self.default_expiry_seconds = default_expiry_seconds
        self.key_prefix = key_prefix

        # Fallback to in-memory if Redis unavailable
        if (not REDIS_AVAILABLE) or self.redis is None:
            logger.warning("Redis not available, using in-memory fallback for pending actions")
            self._fallback = PendingActionManager(default_expiry_seconds)
        else:
            logger.info("Using Redis-backed pending action storage")
            self._fallback = None

    def _make_redis_key(self, token: str) -> str:
        """Create a Redis key for a token."""
        return f"{self.key_prefix}{token}"

    def _serialize_action(self, action: PendingAction) -> str:
        """Serialize a pending action to JSON."""
        return json.dumps(
            {
                "token": action.token,
                "intent_name": action.intent_name,
                "entities": action.entities,
                "summary": action.summary,
                "expires_at": action.expires_at.isoformat(),
                "user_id": action.user_id,
            }
        )

    def _deserialize_action(self, data: str) -> PendingAction:
        """Deserialize a pending action from JSON."""
        obj = json.loads(data)
        return PendingAction(
            token=obj["token"],
            intent_name=obj["intent_name"],
            entities=obj["entities"],
            summary=obj["summary"],
            expires_at=datetime.fromisoformat(obj["expires_at"]),
            user_id=obj.get("user_id"),
        )

    def create(
        self,
        intent_name: str,
        entities: dict[str, Any],
        summary: str,
        user_id: str | None = None,
        expiry_seconds: int | None = None,
    ) -> PendingAction:
        """Create a new pending action.

        Args:
            intent_name: The intent to execute on confirmation
            entities: The entities extracted from the command
            summary: Human-readable description for confirmation
            user_id: Optional user identifier
            expiry_seconds: Custom expiry time, or use default

        Returns:
            PendingAction with a unique token
        """
        # Use fallback if Redis unavailable
        if self._fallback is not None:
            return self._fallback.create(intent_name, entities, summary, user_id, expiry_seconds)

        # Generate secure random token
        token = secrets.token_urlsafe(32)

        # Calculate expiry time
        expiry = expiry_seconds or self.default_expiry_seconds
        expires_at = datetime.now(UTC) + timedelta(seconds=expiry)

        action = PendingAction(
            token=token,
            intent_name=intent_name,
            entities=entities,
            summary=summary,
            expires_at=expires_at,
            user_id=user_id,
        )

        # Store in Redis with TTL
        try:
            redis_key = self._make_redis_key(token)
            serialized = self._serialize_action(action)
            self.redis.setex(redis_key, expiry, serialized)
            logger.debug("Created pending action %s with TTL %ds", token[:8], expiry)
        except redis.RedisError as e:
            logger.error("Redis error creating pending action: %s", e)
            # Fall through - action object still returned even if storage fails

        return action

    def get(self, token: str) -> PendingAction | None:
        """Retrieve a pending action by token.

        Args:
            token: The action token

        Returns:
            PendingAction if found and not expired, None otherwise
        """
        # Use fallback if Redis unavailable
        if self._fallback is not None:
            return self._fallback.get(token)

        try:
            redis_key = self._make_redis_key(token)
            data = self.redis.get(redis_key)

            if data is None:
                return None

            # Decode if bytes
            if isinstance(data, bytes):
                data = data.decode()

            action = self._deserialize_action(data)

            # Double-check expiry (defensive, Redis should handle this)
            if action.is_expired():
                logger.warning("Found expired action in Redis (should have auto-expired)")
                self.redis.delete(redis_key)
                return None

            return action

        except redis.RedisError as e:
            logger.error("Redis error retrieving pending action: %s", e)
            return None
        except (json.JSONDecodeError, KeyError) as e:
            logger.error("Error deserializing pending action: %s", e)
            return None

    def confirm(self, token: str) -> PendingAction | None:
        """Confirm and consume a pending action atomically.

        This uses Redis transaction to ensure exactly-once semantics.

        Args:
            token: The action token

        Returns:
            PendingAction if found and confirmed, None if not found or expired
        """
        # Use fallback if Redis unavailable
        if self._fallback is not None:
            return self._fallback.confirm(token)

        try:
            redis_key = self._make_redis_key(token)

            # Use pipeline with WATCH for atomic get-and-delete
            # This ensures exactly-once consumption
            pipe = self.redis.pipeline()
            pipe.watch(redis_key)

            # Get the action
            data = pipe.get(redis_key)
            if data is None:
                pipe.unwatch()
                return None

            # Decode if bytes
            if isinstance(data, bytes):
                data = data.decode()

            action = self._deserialize_action(data)

            # Check expiry
            if action.is_expired():
                pipe.unwatch()
                pipe.delete(redis_key)
                pipe.execute()
                return None

            # Atomic delete (consume the token)
            pipe.multi()
            pipe.delete(redis_key)
            pipe.execute()

            logger.debug("Confirmed and consumed pending action %s", token[:8])
            return action

        except redis.WatchError:
            # Another process consumed the token
            logger.debug("Concurrent consumption detected for token %s", token[:8])
            return None
        except redis.RedisError as e:
            logger.error("Redis error confirming pending action: %s", e)
            return None
        except (json.JSONDecodeError, KeyError) as e:
            logger.error("Error deserializing pending action: %s", e)
            return None

    def cancel(self, token: str) -> bool:
        """Cancel a pending action.

        Args:
            token: The action token

        Returns:
            True if action was cancelled, False if not found or expired
        """
        # Use fallback if Redis unavailable
        if self._fallback is not None:
            return self._fallback.cancel(token)

        try:
            # First check if it exists and is valid
            action = self.get(token)
            if action is None:
                return False

            # Delete from Redis
            redis_key = self._make_redis_key(token)
            result = self.redis.delete(redis_key)
            return result > 0

        except redis.RedisError as e:
            logger.error("Redis error cancelling pending action: %s", e)
            return False

    def cleanup_expired(self) -> int:
        """Remove all expired actions.

        Note: Redis automatically expires keys with TTL, so this is mostly
        a no-op. It's provided for API compatibility.

        Returns:
            Number of expired actions removed (always 0 for Redis backend)
        """
        # Use fallback if Redis unavailable
        if self._fallback is not None:
            return self._fallback.cleanup_expired()

        # Redis handles expiry automatically, nothing to do
        logger.debug("cleanup_expired called on Redis backend (no-op)")
        return 0
