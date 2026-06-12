# VAI-289 Codebase Scan Finding

Date: 2026-06-09
Fingerprint: 4eb43647c4ffd49ed5f19ed4a49afce784ba38d2
Kind: swallowed_exception
Source: external/ipfs_kit/archive/mcp_development/mcp_test_suite.py:262
Priority: P1
Track: quality

## Evidence

```text
except Exception as e:
```

## Suggested Handling

Review the finding in context, decide whether it represents a bug, missing test,
maintenance risk, or false positive, and land a small fix with validation. If the
finding is a false positive, document why in the changed code or discovery notes
so the supervisor does not keep re-adding the same work.

## Resolution

Fixed in VAI-289. The `except Exception as e:` blocks at lines 262, 316, and 366 were swallowing full tracebacks.

Changes made:
- Added `exc_info=True` to all `logger.error()` calls in these except blocks so full tracebacks are preserved in logs.
- Split each bare `except Exception` into a `requests.RequestException` catch (for expected network errors) followed by a catch-all `Exception` (for unexpected errors like JSON decode failures), both with `exc_info=True`.

This is a genuine improvement: the exception is still handled gracefully (returning `None`/`[]`/`False`), but the full diagnostic context is now available in log output.
