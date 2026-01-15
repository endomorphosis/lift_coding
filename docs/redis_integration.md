# Redis Integration for Pending Actions and Session Context

## Overview

This implementation adds Redis-backed storage for:
1. **Pending Actions** - Short-lived action confirmation tokens
2. **Session Context** - User session state (repo/PR context)

## Features

### Pending Actions (RedisPendingActionManager)
- **Atomic token consumption** using Redis WATCH/MULTI transactions
- **Automatic expiration** via Redis TTL
- **Exactly-once semantics** for confirmation tokens
- **Graceful fallback** to in-memory storage if Redis unavailable

### Session Context (RedisSessionContext)
- **Process restart resilience** - context survives server restarts
- **Automatic expiration** via Redis TTL (default: 1 hour)
- **Per-session isolation** - multiple users/devices maintained independently
- **Graceful fallback** to in-memory storage if Redis unavailable

## Configuration

### Environment Variables

```bash
# Redis connection (defaults shown)
REDIS_HOST=localhost
REDIS_PORT=6379

# Disable Redis (use in-memory fallback)
REDIS_ENABLED=false
```

### Docker Compose

Redis is pre-configured in `docker-compose.yml`:

```yaml
services:
  redis:
    image: redis:7
    ports:
      - "6379:6379"
```

Start with: `docker compose up -d`

## Usage

### Programmatic Usage

```python
from handsfree.redis_client import get_redis_client
from handsfree.commands.pending_actions import RedisPendingActionManager
from handsfree.commands.session_context import RedisSessionContext

# Get Redis client (returns None if unavailable)
redis_client = get_redis_client()

# Create Redis-backed manager
pending_mgr = RedisPendingActionManager(
    redis_client=redis_client,
    default_expiry_seconds=60
)

# Create action (automatically uses fallback if redis_client is None)
action = pending_mgr.create(
    intent_name="pr.merge",
    entities={"pr_number": 123},
    summary="Merge PR 123"
)

# Confirm action (atomic, exactly-once)
confirmed = pending_mgr.confirm(action.token)

# Session context
session_ctx = RedisSessionContext(redis_client=redis_client)
session_ctx.set_repo_pr("session-123", "owner/repo", pr_number=456)
context = session_ctx.get_repo_pr("session-123")
```

### API Usage

The API automatically uses Redis-backed managers if Redis is available:

```python
# In src/handsfree/api.py:
_redis_client = get_redis_client()
if _redis_client is not None:
    _pending_action_manager = RedisPendingActionManager(redis_client=_redis_client)
else:
    _pending_action_manager = PendingActionManager()  # fallback
```

## Testing

### Run Redis-specific tests

```bash
# Start Redis
docker compose up -d

# Run Redis integration tests
pytest tests/test_redis_pending_actions.py
pytest tests/test_redis_session_context.py
pytest tests/test_redis_integration.py

# All tests (includes fallback tests)
make test
```

### Test without Redis

Tests automatically skip if Redis is unavailable:

```python
@pytest.fixture
def redis_client():
    try:
        client = redis.Redis(host="localhost", port=6379, db=15)
        client.ping()
        yield client
    except redis.ConnectionError:
        pytest.skip("Redis not available for testing")
```

## Architecture

### Pending Actions

```
Client Request
    ↓
Create Action → [Redis: token → action_data (TTL: 60s)]
    ↓
Return token to client
    ↓
Client confirms
    ↓
Confirm Action → [Redis: WATCH + GET + DELETE] (atomic)
    ↓
Execute action
```

**Key features:**
- Token stored in Redis with TTL
- Confirmation uses Redis transactions for atomic consume
- Expired tokens automatically cleaned up by Redis

### Session Context

```
Voice Command
    ↓
Parse Intent (e.g., "summarize PR 123")
    ↓
Store Context → [Redis: session_id → {repo, pr_number} (TTL: 1h)]
    ↓
Next Command (e.g., "request review")
    ↓
Retrieve Context ← [Redis: session_id]
    ↓
Execute with context
```

**Key features:**
- Session state persists across process restarts
- Automatic expiration prevents stale data
- Each session isolated by session_id

## Backward Compatibility

All Redis features have in-memory fallbacks:
- **No Redis dependency** - works without Redis installed
- **Graceful degradation** - falls back to in-memory if Redis unavailable
- **No code changes required** - API usage unchanged
- **Test compatibility** - existing tests work with or without Redis

## Performance

### Pending Actions
- **Create**: O(1) - single SET with TTL
- **Get**: O(1) - single GET
- **Confirm**: O(1) - WATCH + GET + DELETE (atomic)
- **Network overhead**: ~2-3ms per operation (localhost)

### Session Context
- **Set**: O(1) - single SET with TTL
- **Get**: O(1) - single GET
- **Clear**: O(1) - single DELETE
- **Network overhead**: ~1-2ms per operation (localhost)

## Monitoring

### Redis Commands Used
- `SET` with `EX` - store with expiration
- `SETEX` - atomic set with TTL
- `GET` - retrieve value
- `DELETE` - remove key
- `WATCH` - transaction monitoring
- `MULTI/EXEC` - atomic transactions

### Key Patterns
- Pending actions: `pending_action:{token}`
- Session context: `session_context:{session_id}`

### Monitoring Examples

```bash
# Check key count
docker exec lift_coding-redis-1 redis-cli DBSIZE

# Monitor operations
docker exec lift_coding-redis-1 redis-cli MONITOR

# Check TTL of a key
docker exec lift_coding-redis-1 redis-cli TTL "pending_action:abc123"

# List all pending actions
docker exec lift_coding-redis-1 redis-cli KEYS "pending_action:*"
```

## Troubleshooting

### Redis not connecting

Check logs:
```bash
docker logs lift_coding-redis-1
```

Test connection:
```bash
docker exec lift_coding-redis-1 redis-cli ping
# Should return: PONG
```

### Fallback to in-memory

If Redis connection fails, the system automatically falls back to in-memory storage. Check logs:
```
WARNING: Redis not available, using in-memory fallback for pending actions
```

### Clear Redis data

```bash
# Clear all data (be careful!)
docker exec lift_coding-redis-1 redis-cli FLUSHDB

# Clear specific pattern
docker exec lift_coding-redis-1 redis-cli KEYS "pending_action:*" | xargs docker exec -i lift_coding-redis-1 redis-cli DEL
```

## Future Enhancements

Potential improvements:
1. **Connection pooling** - Redis connection pool for high concurrency
2. **Redis Cluster** - Distributed Redis for high availability
3. **Metrics** - Prometheus metrics for Redis operations
4. **Rate limiting** - Use Redis for API rate limiting
5. **Deduplication** - Use Redis for webhook event deduplication
