# HAO-365 Codebase Scan Finding

Date: 2026-06-09
Fingerprint: cd4db5b3767756b7500e796cbe578a0b0888fcd9
Kind: swallowed_exception
Source: external/ipfs_kit/archive/mcp_development/mcp_test_suite.py:220
Priority: P1
Track: quality

## Evidence

```text
except Exception:
```

## Suggested Handling

Review the finding in context, decide whether it represents a bug, missing test,
maintenance risk, or false positive, and land a small fix with validation. If the
finding is a false positive, document why in the changed code or discovery notes
so the supervisor does not keep re-adding the same work.

## Resolution (HAO-365)

Status: **Addressed**

The bare `except Exception:` at line 220 was replaced with `except OSError as e:` paired
with `logger.debug(f"Could not read server log file: {e}")`.

Rationale:
- The try block reads the server log file purely for diagnostic output during the startup
  health-check polling loop. Failing to read the log file is non-fatal and intentionally
  benign, so DEBUG level is appropriate.
- Narrowing the catch from `Exception` to `OSError` prevents accidentally swallowing
  unexpected errors (e.g. MemoryError, KeyboardInterrupt descendants) that should
  propagate.
- No test was added for this path because the fix is a tightening of an exception
  type, not a logic change, and the relevant code path is already exercised by the
  existing server startup integration flow.

The file `external/ipfs_kit/archive/mcp_development/mcp_test_suite.py` was added to
the worktree with the corrected exception handler in place.
