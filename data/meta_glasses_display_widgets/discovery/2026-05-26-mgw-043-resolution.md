# MGW-043 Swallowed Exception Resolution

Date: 2026-05-26
Task: MGW-043
Source finding: `src/handsfree/redis_client.py:77`
Evidence: `/home/barberb/lift_coding/data/meta_glasses_display_widgets/discovery/2026-05-26-mgw-043-codebase-scan-7a1ac1883655.md`

## Finding

The Redis client factory treated every unexpected exception from client
construction or `ping()` as an optional Redis outage. That preserved in-memory
fallback behavior, but it also hid unrelated programming and configuration
errors during API startup.

## Resolution

`get_redis_client()` now catches Redis-library errors after the specific
connection-error case and lets non-Redis exceptions propagate. The optional
Redis fallback contract remains in place for genuine Redis failures, with a
warning that includes the target host, port, and DB.

## Validation

```bash
python3 -m py_compile src/handsfree/redis_client.py
PYTHONPATH=./src pytest tests/test_redis_client.py
```
