# HAO-147 Resolution

Date: 2026-05-26
Source finding: 2026-05-26-hao-147-codebase-scan-7a1ac1883655.md

## Finding

The codebase scan flagged the Redis client initialization path because a broad
exception handler could swallow unexpected runtime defects while returning the
same `None` fallback used for Redis being unavailable.

## Resolution

`get_redis_client` now keeps the Redis fallback path constrained to Redis
connection/client errors and invalid Redis port configuration. A malformed
`REDIS_PORT` is logged and returns `None`, matching the factory contract, while
non-Redis initialization defects are allowed to propagate instead of being
silently converted to the fallback.

## Validation

Run from the HAO-147 worktree:

```bash
python3 -m py_compile src/handsfree/redis_client.py
pytest tests/test_redis_client.py
```
