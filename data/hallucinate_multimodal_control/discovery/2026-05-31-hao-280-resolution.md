# HAO-280 Resolution

Date: 2026-05-31
Task: HAO-280
Source: hallucinate_app/hallucinate_app/python/hallucinate_app/test/test_secure_model_manager.py:111

## Finding

Bare `except:` clause in `tearDown` swallowed all exceptions including
`KeyboardInterrupt` and `SystemExit`, which are not `Exception` subclasses and
should never be silently swallowed.

## Fix

Replaced bare `except:` with `except OSError:` since the only expected failures
from `shutil.rmtree` on a missing or already-cleaned test directory are OS-level
errors (e.g. `FileNotFoundError`, `PermissionError`).

## Validation

`python3 -m py_compile` passes with exit code 0.
