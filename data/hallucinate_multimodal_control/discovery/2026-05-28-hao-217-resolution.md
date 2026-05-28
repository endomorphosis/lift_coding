# HAO-217 Resolution

Date: 2026-05-28
Source: hallucinate_app/hallucinate_app/python/hallucinate_app/ipfs_accelerate_server_mp.py:175
Kind: swallowed_exception
Priority: P1
Track: runtime

## Finding

`PlasmaManager.put()` caught all exceptions via `except Exception as e:`, logged
a one-line message, and silently returned `None`. Callers that used the return
value as a plasma ObjectID would fail later with a confusing `AttributeError` or
`TypeError` rather than surfacing the root cause.

Two additional bare `except:` clauses (lines 198, 351) suppressed
`BaseException` subclasses (including `KeyboardInterrupt`) during temporary-file
cleanup.

## Fix

1. **Line 175 – `PlasmaManager.put()`**: changed `except Exception as e` to
   re-raise after logging with `exc_info=True` so the full traceback is
   captured and callers receive the exception instead of `None`.  Updated
   return-type annotation from `Optional[bytes]` to `bytes` and added a
   `Raises` section to the docstring.

2. **Line 198 / 351 – cleanup `except` clauses**: narrowed from bare `except:`
   to `except OSError:` since the only operation inside is `os.unlink()`.

3. **`PlasmaManager.get()` and `PlasmaManager.delete()`**: added `exc_info=True`
   to their existing `logger.error` calls for consistency (tracebacks now appear
   in logs for all three methods).

## Validation

```
python3 -m py_compile hallucinate_app/hallucinate_app/python/hallucinate_app/ipfs_accelerate_server_mp.py
# → exit 0
```
