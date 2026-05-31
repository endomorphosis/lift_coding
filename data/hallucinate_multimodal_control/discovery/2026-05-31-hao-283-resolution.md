# HAO-283 Resolution

Date: 2026-05-31
Source: hallucinate_app/hallucinate_app/python/hallucinate_app/test/test_secure_pyarrow_index_manager.py:525
Kind: swallowed_exception

## Finding

Bare `except Exception: pass` at line 525 in `test_12_delete_entry` silently swallowed all
exceptions, including unexpected ones unrelated to the "entry not found" scenario.

## Fix

Changed `except Exception:` to `except RuntimeError:` so that:
- The expected case (implementation raises `RuntimeError` for missing entry) is explicitly handled
- Unexpected exceptions (e.g., `AttributeError`, `TypeError`, programming errors) propagate
  and cause the test to fail, as intended

## Analysis

The mock's `lookup_by_cid` returns `None` for deleted entries (no exception), so the
`assertIsNone` branch is the normal path in unit tests. The `RuntimeError` catch is retained
as a safety net for integration environments where the backing store may raise on missing
entries (consistent with `RuntimeError` patterns in `secure_pyarrow_index_manager.py`).

## Validation

```
python3 -m py_compile hallucinate_app/hallucinate_app/python/hallucinate_app/test/test_secure_pyarrow_index_manager.py
```

Exit code: 0
