# HAO-272 Resolution

Date: 2026-05-31
Source: hallucinate_app/hallucinate_app/python/hallucinate_app/pyarrow_content_index.py:2572
Finding kind: swallowed_exception

## Summary

The scanner flagged line 2572 for a bare `except:` clause that silently discarded
any exception raised while deleting temporary Parquet/JSON export files created
during `test_self()`. The code had already been partially hardened to
`except OSError:` in a prior pass, but the exception was still swallowed with
a bare `pass` — no variable binding, no log message.

## Fix

Changed the cleanup block from:

```python
except OSError:
    pass
```

to:

```python
except OSError as e:
    # Cleanup of temporary test files is best-effort; a failure
    # here must not be counted as a test failure.
    logger.debug("Could not remove temporary test export file %s: %s", test_export_path, e)
```

Rationale: silently ignoring cleanup failures is acceptable (a stale temp file
in `/tmp` is not a test failure), but we must not drop the information entirely.
Binding the exception to `e` and emitting a `logger.debug` message gives operators
a visible trace when the file system is misbehaving, without failing the
self-test that called the cleanup.

## Validation

```
python3 -m py_compile hallucinate_app/hallucinate_app/python/hallucinate_app/pyarrow_content_index.py
# → exit 0 (PASSED)
```
