"""Redis client factory and utilities.

Provides a central point for Redis connection management with graceful fallback.
"""

import logging
import os
from typing import Optional

import redis

logger = logging.getLogger(__name__)


def get_redis_client(
    host: Optional[str] = None,
    port: Optional[int] = None,
    db: int = 0,
    decode_responses: bool = False,
) -> Optional[redis.Redis]:
    """Get a Redis client or None if Redis is unavailable/disabled.

    Args:
        host: Redis host (default: from REDIS_HOST env or "localhost")
        port: Redis port (default: from REDIS_PORT env or 6379)
        db: Redis database number (default: 0)
        decode_responses: Whether to decode responses to strings (default: False)

    Returns:
        Redis client if available, None if disabled or connection fails
    """
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
