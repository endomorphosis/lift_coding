# HAO-205 Resolution

Date: 2026-05-28
Finding: swallowed_exception
Source: hallucinate_app/hallucinate_app/python/hallucinate_app/duckdb_ipld_kit.py:704

## Fix

Replaced bare `except:` (which silently discarded any database error) with
`except Exception as e:`. The caught error is now stored in `table_count_error`
and surfaced in the `get_stats()` return dict so callers can detect and log
connection/query failures without crashing the stats call.

## Validation

```
python3 -m py_compile hallucinate_app/hallucinate_app/python/hallucinate_app/duckdb_ipld_kit.py
# exit 0 ✓
```
