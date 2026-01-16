"""Redis client factory and utilities.

Provides a central point for Redis connection management with graceful fallback.
"""

import logging
import os
from types import SimpleNamespace

try:
    import redis  # type: ignore

    REDIS_AVAILABLE = True
except ImportError:  # pragma: no cover
    # Make Redis an optional dependency.
    # We provide a minimal stub so type annotations and exception handlers
    # don't crash at import time.
    class _RedisStubError(Exception):
        pass

    redis = SimpleNamespace(  # type: ignore
        Redis=object,
        RedisError=_RedisStubError,
        ConnectionError=_RedisStubError,
    )
    REDIS_AVAILABLE = False

logger = logging.getLogger(__name__)


def get_redis_client(
    host: str | None = None,
    port: int | None = None,
    db: int = 0,
    decode_responses: bool = False,
) -> redis.Redis | None:
    """Get a Redis client or None if Redis is unavailable/disabled.

    Args:
        host: Redis host (default: from REDIS_HOST env or "localhost")
        port: Redis port (default: from REDIS_PORT env or 6379)
        db: Redis database number (default: 0)
        decode_responses: Whether to decode responses to strings (default: False)

    Returns:
        Redis client if available, None if disabled or connection fails
    """
    if not REDIS_AVAILABLE:
        logger.info("Redis Python package not installed; Redis integration disabled")
        return None

    # Check if Redis is explicitly disabled
    if os.environ.get("REDIS_ENABLED", "true").lower() == "false":
        logger.info("Redis is disabled via REDIS_ENABLED environment variable")
        return None

    # Get connection parameters from environment or defaults
    host = host or os.environ.get("REDIS_HOST", "localhost")
    port = port or int(os.environ.get("REDIS_PORT", "6379"))

    try:
        client = redis.Redis(
            host=host,
            port=port,
            db=db,
            decode_responses=decode_responses,
            socket_connect_timeout=2,
            socket_timeout=2,
        )
        # Test connection
        client.ping()
        logger.info("Connected to Redis at %s:%s (db=%s)", host, port, db)
        return client
    except redis.ConnectionError as e:
        logger.warning("Could not connect to Redis at %s:%s: %s", host, port, e)
        return None
    except Exception as e:
        logger.error("Unexpected error connecting to Redis: %s", e)
        return None
