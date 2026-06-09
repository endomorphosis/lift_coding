# HAO-314 Codebase Scan — Swallowed Exception in direct_mcp_server.py:159

## Finding

**File:** `external/ipfs_kit/archive/applied_patches/direct_mcp_server.py`  
**Line:** 159  
**Function:** `get_other_instance_pid()`

```python
def get_other_instance_pid():
    """Get the PID of the other instance (blue if we're green, green if we're blue)."""
    other_pid_file = DEPLOYMENT_CONFIG["green_pid_file"] if is_blue else DEPLOYMENT_CONFIG["blue_pid_file"]
    try:
        if os.path.exists(other_pid_file):
            with open(other_pid_file, "r") as f:
                return int(f.read().strip())
    except Exception as e:          # <-- line 159: swallows all exceptions
        logger.error(f"Error reading other instance PID file: {e}")
    return None
```

## Problem

`except Exception` is overly broad. It catches and silences every exception—including programming errors, unexpected I/O failures, and `KeyboardInterrupt` subclasses—rather than only the anticipated I/O and parsing errors. This prevents unexpected failures from surfacing and makes debugging harder.

The two anticipated failure modes here are:
- `OSError` (including `PermissionError`, `FileNotFoundError`) — from `open()`
- `ValueError` — from `int()` if the PID file contains non-integer content

## Fix Applied

Replaced `except Exception` with `except (OSError, ValueError)` so only expected failures are handled; all other exceptions propagate normally.

```python
    except (OSError, ValueError) as e:
        logger.error(f"Error reading other instance PID file: {e}")
    return None
```

## Impact

Low risk. The function already returns `None` on failure; callers must handle `None` either way. Narrowing the except clause makes it stricter without changing observable behaviour for the anticipated failure modes.
