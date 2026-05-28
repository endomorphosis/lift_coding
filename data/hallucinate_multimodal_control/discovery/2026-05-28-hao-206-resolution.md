# HAO-206 Resolution

Date: 2026-05-28
Task: HAO-206
Kind: swallowed_exception
Source: hallucinate_app/hallucinate_app/python/hallucinate_app/duckdb_ipld_kit.py:188 (originally reported as :796)

## Finding

Bare `except:` clause at line 188 (inner try block in `execute()`) caught all
exceptions including `KeyboardInterrupt` and `SystemExit`, which are not subclasses
of `Exception` and should never be silenced. The handler also called
`result_cursor.execute("SELECT changes()")` which is not a valid DuckDB pattern for
obtaining row counts and would likely raise another exception.

A second `except Exception: pass` at line 803 (test cleanup) was flagged as
intentional but lacked an explanatory comment.

## Fix

1. **Line 188**: Replaced bare `except:` with `except Exception:` and fixed the
   fallback row-count logic to use `result_cursor.rowcount` (with a nested guard)
   instead of calling `.execute("SELECT changes()")` which is not supported on a
   DuckDB result cursor.

2. **Line 803**: Added an inline comment to the `except Exception: pass` in the test
   cleanup block so future readers understand it is intentional (best-effort DROP,
   result already captured).

## Validation

```
python3 -m py_compile hallucinate_app/hallucinate_app/python/hallucinate_app/duckdb_ipld_kit.py
```

Exit code 0 — no syntax errors.
