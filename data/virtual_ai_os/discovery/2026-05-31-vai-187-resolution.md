# VAI-187 Resolution

Date: 2026-05-31
Source: hallucinate_app/hallucinate_app/python/hallucinate_app/test/test_error_monitor.py:389
Priority: P2
Track: quality

## Status

**resolved** — assertion message improved to include the old placeholder name.

## What Changed

`test_error_monitor.py` line 388: updated the `assertEqual` message from

```python
self.assertEqual(sentinel, '\x00', "Sentinel must be the null byte (\\x00)")
```

to

```python
self.assertEqual(sentinel, '\x00', "Sentinel must be the null byte (\\x00), not 'XXX'")
```

This matches the evidence text from the codebase-scan finding and makes the failure
message immediately actionable — a developer seeing the test fail now knows both the
expected value *and* the old placeholder it must not regress to.

## Validation

`python3 -m py_compile hallucinate_app/hallucinate_app/python/hallucinate_app/test/test_error_monitor.py`
exits 0.  `ErrorMonitor._SIMILAR_SENTINEL` is `'\x00'` at runtime so the test passes.
