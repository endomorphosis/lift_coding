# HAO-148 Resolution

Date: 2026-05-26
Source finding: 2026-05-26-hao-148-codebase-scan-74ff113b87c6.md

## Finding

The codebase scan flagged `_close_runtime_stream` because cleanup failures from
the py-libp2p stream `close()` path were swallowed before falling back to
`reset()`. A second broad handler also hid reset failures.

## Resolution

Runtime stream cleanup remains best-effort so transport teardown can continue,
but close and reset failures are now logged at warning level with traceback
context. The adapter still tries `reset()` after a failed `close()`, while making
both cleanup failures observable for runtime diagnosis.

## Validation

Passed from the HAO-148 worktree:

```bash
python3 -m py_compile src/handsfree/transport/libp2p_bluetooth.py
pytest tests/test_transport_providers.py -k runtime_stream_cleanup
```
