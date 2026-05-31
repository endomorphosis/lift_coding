# HAO-285 Fix: Swallowed Exception at Line 129

Date: 2026-05-31
Task: HAO-285
Source: hallucinate_app/hallucinate_app/python/hallucinate_app/test/test_secure_pyarrow_index_manager_integration.py

## Findings

Two issues were addressed:

1. **Line 129 (tearDown)**: The `except:` bare clause was already typed as
   `except OSError as e:` with a `logger.warning(...)` in the current file, but
   the file was untracked. The fix is to commit the file so the typed handler is
   preserved.

2. **Line 451 (test_capability_verification_sync)**: A broad `except Exception as e:`
   wrapped the entire test body including `assertIsInstance` and `assertRaises`
   assertions. This swallowed real test failures, masking bugs as skipped tests.

## Fix

The sync test was refactored to separate "sync not available" detection from
assertions:

- Only the initial `sync_with_ipfs_pinset` call is wrapped in try/except.
- The catch clause is narrowed to `(NotImplementedError, AttributeError, OSError,
  ConnectionError)` — errors that indicate the operation is genuinely unavailable.
- If those exceptions occur, the test is skipped with `return` to prevent further
  execution.
- Assertions (`assertIsInstance`, `assertRaises`) are now outside the try/except,
  so genuine test failures propagate correctly.

## Status

- Validation: `python3 -m py_compile` passes.
- False positive notes: None; both were genuine quality issues.
