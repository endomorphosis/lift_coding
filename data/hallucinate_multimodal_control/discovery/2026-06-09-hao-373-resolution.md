# HAO-373 Resolution

Date: 2026-06-09
Source: external/ipfs_kit/archive/mcp_final_20250414_082801/controllers/ipfs_controller_anyio.py:1465
Kind: swallowed_exception → fixed

## Finding

In `find_peer()`, the request-body parsing fallback had two bare `except Exception`
clauses that silently swallowed all errors:

```python
try:
    body = await request.json()
    peer_id = body.get("arg") or body.get("peer_id")
except Exception:                          # line 1460 – too broad
    try:
        form = await request.form()
        peer_id = form.get("arg") or form.get("peer_id")
    except Exception:                      # line 1465 – bare pass
        pass
```

The outer `except Exception` at 1460 masked unexpected runtime errors (e.g.
network/stream faults) that should propagate. The inner `except Exception: pass`
at 1465 silently discarded any error from the form-data fallback, making
debugging impossible.

## Fix

1. Outer handler narrowed to `except (ValueError, UnicodeDecodeError, RuntimeError)` –
   the expected failure modes when the body is not JSON.
2. Inner handler changed to `except Exception as form_exc` with a
   `logger.debug(...)` call so operators can observe the fallback when
   troubleshooting parameter-extraction failures.
3. Both handlers now emit a `logger.debug` message describing the failure.

## Validation

`python3 -m py_compile` fails on this file due to a **pre-existing syntax error
in the import block** (lines 16-27, `from fastapi import (` is incomplete) that
predates this task and is unrelated to the swallowed-exception fix. The fix
itself is syntactically correct Python; the pre-existing import error prevents
the whole-file compile check from passing.

## Status

Fixed. Pre-existing syntax error in imports noted; out of scope for HAO-373.
