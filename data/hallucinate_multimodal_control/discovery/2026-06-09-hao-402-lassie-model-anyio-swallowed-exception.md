# HAO-402 Fix: Swallowed Exception in lassie_model_anyio.py

Date: 2026-06-09
Task: HAO-402
Source: external/ipfs_kit/archive/mcp_final_20250414_082801/models/storage/lassie_model_anyio.py:623

## Finding

The codebase scan found a bare `except Exception: pass` at line 623 inside
a cleanup block within the `ipfs_to_lassie` method of `LassieModelAnyIO`.

The cleanup block:
```python
if temp_file:
    try:
        os.unlink(temp_file.name)
    except Exception:
        pass
```

This pattern silently discards filesystem errors (permission denied, file
in use, etc.) that occur while cleaning up temporary files. When cleanup
fails in error paths, leftover temp files accumulate without any trace in
logs, making it hard to debug disk space issues or permission problems.

An identical pattern also existed at line 746 in the async equivalent
`ipfs_to_lassie_async`.

The file also had 33 pre-existing syntax errors (misindented function
parameters and missing closing parentheses throughout the archive file)
that prevented compilation entirely.

## Fix Applied

**Primary fix (swallowed exceptions):**
- `lassie_model_anyio.py:623` (sync): Changed `except Exception: pass`
  to `except Exception as cleanup_err: logger.warning(...)` so cleanup
  failures are logged at WARNING level with the filename and error.
- `lassie_model_anyio.py:746` (async): Same fix applied to the async
  counterpart.

**Secondary fix (syntax errors):**
Fixed 30 distinct syntax issues in the corrupted archive file:
- Malformed `__init__` parameters (args at column 0, missing commas/closing paren)
- Missing `)` in `warnings.warn()` call
- Missing `)` in `await anyio.to_thread.run_sync(...)` calls
- Missing `):` before docstrings in function definitions
- Missing `)` in `.get("error", ...)` calls
- Misindented keyword arguments in `fetch_cid()` call sites
- Missing `)` in `callable(getattr(...))` expressions
- Missing `)` in `logger.warning(...)` calls

## Validation

```
python3 -m py_compile external/ipfs_kit/archive/mcp_final_20250414_082801/models/storage/lassie_model_anyio.py
# Exit code 0 - compilation successful
```

## Notes

The 33 syntax errors in the original file indicate the archive was stored
in a corrupted state (likely during the original archiving on 2025-04-14).
All fixes are minimal and conservative, preserving the intended logic of
each function.
