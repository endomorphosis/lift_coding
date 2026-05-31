# HAO-281 Resolution

Date: 2026-05-31
Task: HAO-281
Source: hallucinate_app/hallucinate_app/python/hallucinate_app/test/test_secure_pyarrow_index_manager.py:525

## Finding

Bare `except:` clause swallowed all exceptions including `KeyboardInterrupt` and
`SystemExit`, which are not `Exception` subclasses and should never be silently
swallowed.

## Fix

Replaced bare `except:` with `except Exception:` in the `tearDown`-context cleanup
block at line 525. `Exception` is the appropriate base class for expected runtime
errors during cleanup; non-recoverable signals (`KeyboardInterrupt`, `SystemExit`)
are no longer swallowed.

## Merge Conflict Resolution

The implementation branch (`implementation/hao-281-attempt-1-1780248240`) and the
VAI-187 implementation branch both advanced the `hallucinate_app` submodule pointer
from a common base, causing a `UU hallucinate_app` conflict on merge. Resolution:

- Merged both submodule branches inside `hallucinate_app` to produce merge commit
  `97221c4a`, which carries all changes from both HAO-281 and VAI-187.
- Updated the parent repo `hallucinate_app` pointer to `97221c4a`.

## Validation

`python3 -m py_compile` passes with exit code 0.
