# HAO-378 Fix: Swallowed Exception in peer_websocket_controller.py

Date: 2026-06-09
Task: HAO-378
Kind: swallowed_exception
Source: external/ipfs_kit/archive/mcp_final_20250414_082801/controllers/peer_websocket_controller.py:561

## Finding

The codebase scan at line 561 flagged a `except Exception` pattern inside
`disconnect_from_server`. The inner try-except block was:

```python
try:
    self.peer_websocket_client = None
except Exception as clear_err:
    logger.warning(f"Failed to clear peer_websocket_client reference: {clear_err}")
```

## Root Cause

Attribute assignment (`self.peer_websocket_client = None`) cannot raise an
exception in normal Python unless a `__setattr__` override does so. This inner
try-except is therefore dead/unreachable code. If it had been written as a bare
`except Exception:` (no logging), it would have fully swallowed any unexpected
error silently.

## Fix Applied

Removed the unnecessary inner try-except block. The attribute is now assigned
directly inside the outer `except Exception as e:` handler, which already logs
the primary error with `logger.error`. The comment was updated to clarify the
rationale.

```python
except Exception as e:
    logger.error(f"Error stopping WebSocket client: {e}")

    # Clear the client reference to prevent resource leaks even on error.
    # Attribute assignment cannot raise, so no inner try-except is needed.
    self.peer_websocket_client = None

    return {
        "success": False,
        ...
    }
```

## Validation

```
python3 -m py_compile external/ipfs_kit/archive/mcp_final_20250414_082801/controllers/peer_websocket_controller.py
# Exit code: 0 (PASS)
```
