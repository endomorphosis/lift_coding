# HAO-273 Resolution

Date: 2026-05-31
Source: hallucinate_app/hallucinate_app/python/hallucinate_app/secure_duckdb_ipld_manager.py:1250
Finding kind: swallowed_exception

## Summary

The scanner flagged a `except Exception as e:` block in `_extract_table_name` at
the original line 1250 (now shifted to line 1258 after a TRUNCATE-handling branch
was added in a subsequent commit).

Examining the current state revealed two exception handlers in the function:

1. `except re.error as e:` (line 1255) — silently returns `None` after logging a
   bare warning with no context about *which* SQL triggered the failure.
2. `except Exception as e:` (line 1258) — logs the error and **re-raises**, so the
   exception is not swallowed.

The `except Exception` path was already correct. The real maintenance risk was the
`except re.error` branch: its warning message carried no contextual information
(no `sql_type`, no SQL snippet), making it hard for operators to diagnose unusual
inputs that trigger regex failures.  Because `_extract_table_name` is called on the
hot path of SQL authorization, a silent failure silently degrades the capability
check from per-table (`capability:table_name`) to wildcard (`capability:*`).  That
broader check is still enforced, but the degradation was invisible in logs.

## Fix

Improved the `except re.error` warning to include `sql_type` and a truncated
`sql_snippet` (up to 120 chars) so operators can identify the unexpected SQL.
Also tidied the `except Exception` log call to include `sql_type` consistently.

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
except Exception as e:
    logger.error(
        "Unexpected error extracting table name (sql_type=%r): %s",
        sql_type,
        e,
        exc_info=True,
    )
    raise
```

The graceful-degradation design (`re.error` → return None) is intentional and
preserved; a bad regex in a SQL-parsing helper must not abort an otherwise valid
SQL execution.

## Validation

```
python3 -m py_compile hallucinate_app/hallucinate_app/python/hallucinate_app/secure_duckdb_ipld_manager.py
# → exit 0 (PASSED)
```
