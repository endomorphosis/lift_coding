# HAO-206 Resolution

Date: 2026-06-12
Task: HAO-206
Kind: swallowed_exception
Source: hallucinate_app/hallucinate_app/python/hallucinate_app/duckdb_ipld_kit.py:796

## Finding

The self-test Parquet export cleanup path previously risked hiding cleanup
failures. A failure during temporary directory removal should not be swallowed
silently because it can leave files behind and hide useful runtime diagnostics.

## Fix

The cleanup handler catches `Exception` explicitly, marks the `parquet_export`
self-test unsuccessful, records `cleanup_error`, marks the overall test result
unsuccessful, and now logs the failure with traceback context via
`exc_info=True`.

## Validation

```sh
python3 -m py_compile hallucinate_app/hallucinate_app/python/hallucinate_app/duckdb_ipld_kit.py
```

Exit code 0. No syntax errors.
