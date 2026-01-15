"""Session token management for mobile and wearable clients.

This module provides production-ready session token management with:
- Short-lived session tokens
- Redis-backed storage for fast lookup
- Automatic expiration
- User association
- Device tracking
"""

import hashlib
import logging
import secrets
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

import redis

logger = logging.getLogger(__name__)


@dataclass
class SessionToken:
    """Represents a session token."""

    token: str
    user_id: str
    device_id: str
    created_at: datetime
    expires_at: datetime
    metadata: dict


class SessionTokenManager:
    """Manages short-lived session tokens for mobile/wearable clients.

    Session tokens are used to authenticate mobile and wearable clients
    without requiring them to send long-lived credentials with every request.

    Features:
    - Cryptographically secure token generation
    - Redis-backed storage for performance
    - Automatic expiration
    - Device tracking for security audit
    - Metadata support (e.g., device type, app version)

    Security considerations:
    - Tokens are random and unpredictable
    - Short TTL (default 24 hours) limits exposure
    - Tokens are hashed before storage
    - Failed lookups don't reveal if token exists
    """

    def __init__(
        self, redis_client: redis.Redis, default_ttl_hours: int = 24, key_prefix: str = "session:"
    ):
        """Initialize the session token manager.

        Args:
            redis_client: Redis client for token storage
            default_ttl_hours: Default token time-to-live in hours (default: 24)
            key_prefix: Prefix for Redis keys (default: "session:")
        """
        self.redis = redis_client
        self.default_ttl_hours = default_ttl_hours
        self.key_prefix = key_prefix
        logger.info("Initialized SessionTokenManager with TTL=%d hours", default_ttl_hours)

    def _hash_token(self, token: str) -> str:
        """Hash a token for storage.

        Tokens are hashed before storage to prevent theft if Redis is compromised.

        Args:
            token: Raw token string

        Returns:
            SHA-256 hash of the token
        """
        return hashlib.sha256(token.encode()).hexdigest()

    def _make_redis_key(self, token_hash: str) -> str:
        """Create a Redis key for a token.

        Args:
            token_hash: Hashed token

        Returns:
            Redis key
        """
        return f"{self.key_prefix}{token_hash}"

    def create_session(
        self,
        user_id: str,
        device_id: str,
        ttl_hours: int | None = None,
        metadata: dict | None = None,
    ) -> SessionToken:
        """Create a new session token.

        Args:
            user_id: User ID to associate with the session
            device_id: Device ID (for tracking and audit)
            ttl_hours: Token lifetime in hours (default: from constructor)
            metadata: Optional metadata (e.g., {"device_type": "wearable", "app_version": "1.0"})

        Returns:
            SessionToken object with the generated token

        Raises:
            redis.RedisError: If Redis operation fails
        """
        # Generate cryptographically secure random token
        # 32 bytes = 256 bits of entropy
        token = secrets.token_urlsafe(32)

        # Calculate expiration
        ttl = ttl_hours if ttl_hours is not None else self.default_ttl_hours
        now = datetime.now(UTC)
        expires_at = now + timedelta(hours=ttl)

        # Prepare session data
        session_data = {
            "user_id": user_id,
            "device_id": device_id,
            "created_at": now.isoformat(),
            "expires_at": expires_at.isoformat(),
            "metadata": str(metadata or {}),
        }

        # Store in Redis with expiration
        token_hash = self._hash_token(token)
        redis_key = self._make_redis_key(token_hash)

        # Use Redis pipeline for atomic operation
        pipe = self.redis.pipeline()
        pipe.hset(redis_key, mapping=session_data)
        pipe.expire(redis_key, int(ttl * 3600))  # Convert hours to seconds as integer
        pipe.execute()

        logger.info(
            "Created session token for user_id=%s, device_id=%s, expires_at=%s",
            user_id,
            device_id,
            expires_at.isoformat(),
        )

        return SessionToken(
            token=token,
            user_id=user_id,
            device_id=device_id,
            created_at=now,
            expires_at=expires_at,
            metadata=metadata or {},
        )

    def validate_session(self, token: str) -> SessionToken | None:
        """Validate a session token and return session info.

        Args:
            token: The session token to validate

        Returns:
            SessionToken object if valid, None if invalid or expired
        """
        token_hash = self._hash_token(token)
        redis_key = self._make_redis_key(token_hash)

        # Retrieve session data
        try:
            session_data = self.redis.hgetall(redis_key)

            if not session_data:
                logger.debug("Session token not found or expired")
                return None

            # Decode bytes to strings (Redis returns bytes)
            session_data = {
                k.decode() if isinstance(k, bytes) else k: v.decode() if isinstance(v, bytes) else v
                for k, v in session_data.items()
            }

            # Parse dates
            created_at = datetime.fromisoformat(session_data["created_at"])
            expires_at = datetime.fromisoformat(session_data["expires_at"])

            # Check if expired (defensive check, Redis should auto-expire)
            if expires_at < datetime.now(UTC):
                logger.warning("Expired session token found (should have been auto-expired)")
                self.revoke_session(token)
                return None

            # Parse metadata (stored as string)
            metadata_str = session_data.get("metadata", "{}")
            try:
                metadata = eval(metadata_str)  # Safe since we control the input
            except Exception:
                metadata = {}

            return SessionToken(
                token=token,
                user_id=session_data["user_id"],
                device_id=session_data["device_id"],
                created_at=created_at,
                expires_at=expires_at,
                metadata=metadata,
            )

        except redis.RedisError as e:
            logger.error("Redis error during session validation: %s", e)
            return None
        except Exception as e:
            logger.error("Error validating session: %s", e)
            return None

    def revoke_session(self, token: str) -> bool:
        """Revoke a session token.

        Args:
            token: The session token to revoke

        Returns:
            True if revoked, False if token didn't exist
        """
        token_hash = self._hash_token(token)
        redis_key = self._make_redis_key(token_hash)

        try:
            result = self.redis.delete(redis_key)
            if result:
                logger.info("Revoked session token")
                return True
            else:
                logger.debug("Session token not found for revocation")
                return False
        except redis.RedisError as e:
            logger.error("Redis error during session revocation: %s", e)
            return False

    def revoke_user_sessions(self, user_id: str) -> int:
        """Revoke all session tokens for a user.

        This is useful for:
        - User logout from all devices
        - Security incident response
        - Password reset

        Args:
            user_id: User ID whose sessions to revoke

        Returns:
            Number of sessions revoked
        """
        # Scan for all session keys
        pattern = f"{self.key_prefix}*"
        revoked_count = 0

        try:
            for key in self.redis.scan_iter(match=pattern, count=100):
                # Check if this session belongs to the user
                session_data = self.redis.hgetall(key)
                if session_data:
                    stored_user_id = session_data.get(b"user_id", b"").decode()
                    if stored_user_id == user_id:
                        self.redis.delete(key)
                        revoked_count += 1

            logger.info("Revoked %d session(s) for user_id=%s", revoked_count, user_id)
            return revoked_count

        except redis.RedisError as e:
            logger.error("Redis error during user session revocation: %s", e)
            return revoked_count

    def revoke_device_sessions(self, device_id: str) -> int:
        """Revoke all session tokens for a device.

        This is useful for:
        - Device lost/stolen
        - Device deregistration

        Args:
            device_id: Device ID whose sessions to revoke

        Returns:
            Number of sessions revoked
        """
        # Scan for all session keys
        pattern = f"{self.key_prefix}*"
        revoked_count = 0

        try:
            for key in self.redis.scan_iter(match=pattern, count=100):
                # Check if this session belongs to the device
                session_data = self.redis.hgetall(key)
                if session_data:
                    stored_device_id = session_data.get(b"device_id", b"").decode()
                    if stored_device_id == device_id:
                        self.redis.delete(key)
                        revoked_count += 1

            logger.info("Revoked %d session(s) for device_id=%s", revoked_count, device_id)
            return revoked_count

        except redis.RedisError as e:
            logger.error("Redis error during device session revocation: %s", e)
            return revoked_count

    def extend_session(self, token: str, additional_hours: int = 24) -> bool:
        """Extend the expiration time of a session.

        Args:
            token: The session token to extend
            additional_hours: Hours to add to current expiration

        Returns:
            True if extended, False if token not found
        """
        session = self.validate_session(token)
        if not session:
            return False

        token_hash = self._hash_token(token)
        redis_key = self._make_redis_key(token_hash)

        try:
            # Calculate new expiration
            new_expires_at = session.expires_at + timedelta(hours=additional_hours)
            remaining_seconds = int((new_expires_at - datetime.now(UTC)).total_seconds())

            if remaining_seconds > 0:
                # Update expiration in Redis
                self.redis.hset(redis_key, "expires_at", new_expires_at.isoformat())
                self.redis.expire(redis_key, remaining_seconds)
                logger.info("Extended session token by %d hours", additional_hours)
                return True
            else:
                logger.warning("Cannot extend session: calculated expiration is in the past")
                return False

        except redis.RedisError as e:
            logger.error("Redis error during session extension: %s", e)
            return False
