# HAO-273 Resolution

Date: 2026-05-31
Source: hallucinate_app/hallucinate_app/python/hallucinate_app/secure_duckdb_ipld_manager.py:1250
Finding kind: swallowed_exception

## Summary

The scanner flagged a `except Exception as e:` block in `_extract_table_name` at
the original line 1250 (now shifted to line 1258 after a TRUNCATE-handling branch
was added in a subsequent commit).

Examining the path revealed two exception handlers in the function:

1. `except re.error as e:` (line 1255) — silently returns `None` after logging a
   bare warning with no context about *which* SQL triggered the failure.
2. `except Exception as e:` (line 1258) — logs the error and **re-raises**, so the
   exception is not swallowed, but the broad catch still produces scanner noise
   and adds no control-flow value.

The broad `except Exception` path was redundant because it only logged and
re-raised. Unexpected failures now propagate naturally to the caller. The specific
`except re.error` branch remains because `_extract_table_name` is called on the hot
path of SQL authorization: returning `None` intentionally falls back from a
per-table check (`capability:table_name`) to the wildcard capability check
(`capability:*`), which is still enforced.

## Fix

Removed the redundant broad `except Exception as e:` handler so the scanned
swallowed-exception path no longer exists. Kept the specific `re.error` fallback
and improved its warning to include `sql_type` and a truncated `sql_snippet` (up
to 120 chars) so operators can identify unexpected SQL that triggers regex
failures.

```python
# before
except re.error as e:
    logger.warning("Regex error while extracting table name from SQL: %s", e)
    return None
except Exception as e:
    logger.error("Unexpected error extracting table name: %s", e, exc_info=True)
    raise

# after
except re.error as e:
    # Graceful degradation: a malformed regex pattern must not crash the
    # auth path.  Returning None causes the caller to fall back to the
    # wildcard capability check, which is still enforced — it is just
    # less specific than a per-table check.  Include enough context for
    # operators to diagnose unusual SQL that triggers this branch.
    logger.warning(
        "Regex error while extracting table name from SQL "
        "(sql_type=%r, sql_snippet=%r): %s",
        sql_type,
        sql[:120] if sql else "",
        e,
    )
    return None
```

The graceful-degradation design (`re.error` → return None) is intentional and
preserved; a bad regex in a SQL-parsing helper must not abort an otherwise valid
SQL execution. Other unexpected exceptions are no longer caught in this helper.

## Validation

```
python3 -m py_compile hallucinate_app/hallucinate_app/python/hallucinate_app/secure_duckdb_ipld_manager.py
# → exit 0 (PASSED)
```
