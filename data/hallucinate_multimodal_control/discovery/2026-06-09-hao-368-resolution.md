# HAO-368 Resolution

Date: 2026-06-09
Task: HAO-368
Finding: swallowed_exception at external/ipfs_kit/archive/mcp_final_20250414_082801/auth/service.py:286

## Finding

The codebase scan flagged a bare `except Exception as e:` at line 286 in the auth
service module, inside the `_verify_password` method of `AuthenticationService`.

The original handler:
```python
except Exception as e:
    logger.error(f"Error verifying password: {e}")
    return False
```

This swallowed the exception silently: `logger.error` with only the exception string
discards the full traceback, making it impossible to diagnose the root cause of any
unexpected failures during password verification.

## Fix

Updated `external/ipfs_kit/archive/mcp_final_20250414_082801/auth/service.py` with:

1. **Narrow exception type for the expected case** – `ValueError` is raised when
   `hashed_password` does not contain the expected `$` separator (malformed hash).
   This is logged with `logger.exception` (full traceback) and returns `False`.

2. **Broad catch retains traceback** – the remaining `except Exception:` catch now
   uses `logger.exception` instead of `logger.error(f"...")` so the full stack trace
   is always preserved in the log output.

3. **Syntax errors fixed** – the source file copied from the upstream archive
   contained several garbled import blocks and function signatures (missing commas,
   bad indentation) that prevented compilation.  All were corrected as part of this
   fix so the module compiles cleanly.

No bare `except Exception as e:` with only a string-format log call exists in the
delivered file.  The security intent (return False rather than propagate) is
preserved; only the diagnostic fidelity is improved.

## Validation

`python3 -m py_compile external/ipfs_kit/archive/mcp_final_20250414_082801/auth/service.py` → OK
