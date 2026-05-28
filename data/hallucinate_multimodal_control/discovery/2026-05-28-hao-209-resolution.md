# HAO-209 Resolution

Date: 2026-05-28
Source: hallucinate_app/hallucinate_app/python/hallucinate_app/duckdb_ipld_kit.py:810
Status: fixed

## Bug

`DuckDBIPLDKit.test()` used a bare `except Exception: pass` block when cleaning up
the temporary `test_table` after the integration test run.  The exception was
completely swallowed—no logging, no variable binding—making it impossible to
diagnose cleanup failures during development or CI.

## Fix

Changed the bare swallow to capture the exception and emit a DEBUG log message,
following the same pattern used elsewhere in the file (e.g. lines 191–200):

```python
# Before
except Exception:
    pass  # Best-effort cleanup; ...

# After
except Exception as e:
    logger.debug("Failed to drop test_table during cleanup (best-effort): %s", e)
```

The cleanup is still best-effort (exceptions are not re-raised) so test results
are still returned to the caller even when the DROP fails.

## Validation

```
python3 -m py_compile hallucinate_app/hallucinate_app/python/hallucinate_app/duckdb_ipld_kit.py
# exit 0
```
