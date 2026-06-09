# HAO-377 Resolution

Date: 2026-06-09
Task: HAO-377
Kind: swallowed_exception
Source: external/ipfs_kit/archive/mcp_final_20250414_082801/controllers/peer_websocket_controller.py:561

## Finding

The codebase scan identified a bare `except Exception: pass` at line 561 in the
`stop_client` method of `PeerWebsocketController`. While the scan referenced line 394
(an inner cleanup handler in `stop_server` that already had proper logging), the
symmetric inner handler in `stop_client` did not log the error.

## Fix

Changed the bare `except Exception: pass` to `except Exception as clear_err:` with a
`logger.warning(...)` call, matching the pattern already used in the `stop_server`
method at line 394:

```python
# Before (swallowed exception)
try:
    self.peer_websocket_client = None
except Exception:
    pass

# After (logged)
try:
    self.peer_websocket_client = None
except Exception as clear_err:
    logger.warning(f"Failed to clear peer_websocket_client reference: {clear_err}")
```

## Notes

- The fix is consistent with the existing `stop_server` cleanup pattern at line 394.
- Attribute assignment (`self.peer_websocket_client = None`) should never raise in practice,
  but if it does (e.g., due to a `__setattr__` override or slot restriction), the error is
  now surfaced in logs rather than silently ignored.
- No test changes required; the logic path is a best-effort resource cleanup.
