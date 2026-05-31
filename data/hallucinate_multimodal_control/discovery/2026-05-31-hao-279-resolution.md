# HAO-279 Resolution

Date: 2026-05-31
Source: hallucinate_app/hallucinate_app/python/hallucinate_app/test/test_graphrag.py:49
Finding: swallowed_exception

## Fix

Changed bare `except:` to `except OSError:` in the `tearDown` method's
`shutil.rmtree` call. `OSError` is the appropriate exception class for
filesystem operations and avoids swallowing `KeyboardInterrupt`, `SystemExit`,
and other non-filesystem signals.

## Status

Fixed. Validation passed: `python3 -m py_compile` exits 0.
