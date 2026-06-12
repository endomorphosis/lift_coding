# HAO-209 Resolution

Date: 2026-05-28
Source: hallucinate_app/hallucinate_app/python/hallucinate_app/duckdb_ipld_kit.py:810
Status: fixed

## Bug

`DuckDBIPLDKit.test()` intentionally catches exceptions from the Arrow export
self-test so it can return a structured failed test result. The path previously
only encoded the error in the returned payload, which made unexpected Arrow
runtime failures easy to miss in logs during development or CI.

## Fix

Kept the self-test behavior of returning a structured failed result, but made the
exception observable in logs with traceback via `logger.exception(...)`:

```python
# Before
except Exception as e:
    results["tests"]["arrow_export"] = {
        "success": False,
        "error": str(e)
    }

# After
except Exception as e:
    logger.exception("DuckDB-IPLD self-test arrow export failed")
    results["tests"]["arrow_export"] = {
        "success": False,
        "error": str(e)
    }
```

The exception is still not re-raised because this method is a module self-test
that reports per-check failures through its result object.

## Validation

```
python3 -m py_compile hallucinate_app/hallucinate_app/python/hallucinate_app/duckdb_ipld_kit.py
# exit 0
```
