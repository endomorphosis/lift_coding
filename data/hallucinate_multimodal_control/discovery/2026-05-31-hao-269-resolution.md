# HAO-269 Resolution

Date: 2026-05-31
Task: HAO-269 — Review swallowed exception path in secure_duckdb_ipld_manager.py:1249
Status: Fixed

## Finding

`_extract_table_name` at line 1249 caught `Exception` and only printed `str(e)`,
discarding the full traceback. Since this function is in the authorization path
(its `None` return silently falls back to wildcard capability checks), any
unexpected failure here would be invisible and hard to debug.

## Fix

1. Added `import traceback` to the module-level imports (line 12).
2. Updated the except block to include `traceback.format_exc()` in the print output,
   so the full stack trace is visible in logs on any unexpected failure.

```python
# Before
except Exception as e:
    print(f"Error extracting table name: {e}")
    return None

# After
except Exception as e:
    print(f"Error extracting table name: {e}\n{traceback.format_exc()}")
    return None
```

## Validation

```
python3 -m py_compile hallucinate_app/hallucinate_app/python/hallucinate_app/secure_duckdb_ipld_manager.py
# exit 0 — no compile errors
```

## Notes

Returning `None` on failure remains appropriate: the caller at line 341 handles
`None` by falling back to general wildcard capability checks, which is already
the safe default. The fix ensures failures are surfaced rather than silently
swallowed.
