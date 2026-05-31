# HAO-282 Resolution

Date: 2026-05-31
Task: HAO-282
Source: hallucinate_app/hallucinate_app/python/hallucinate_app/test/test_error_monitor.py:388

## Finding

The codebase scanner flagged line 388 of `test_error_monitor.py` because the
assertion message contained the literal string `'XXX'` — the old three-character
sentinel placeholder — which scanner heuristics flag as a code annotation marker:

```python
self.assertEqual(sentinel, '\x00', "Sentinel must be the null byte (\\x00), not 'XXX'")
```

The string `'XXX'` is `chr(88)*3`, which was the original `_SIMILAR_SENTINEL` value
before VAI-144 replaced it with a null byte (`'\x00'`).  In the assertion message
it was intended to name the old value explicitly, but visually it resembles a TODO
placeholder, triggering the scanner.

## Resolution

The assertion message was already corrected in commit
`5f41933 VAI-188: Fix 'XXX' literal in assertion message on line 388`
by replacing `"not 'XXX'"` with `"not the old three-character placeholder"`.
The current submodule HEAD (`db2f5d78`) already contains this change; no
additional code edit is required for HAO-282.

The actual sentinel value (`_SIMILAR_SENTINEL = '\x00'`) remains correct and
the surrounding tests (`assertNotEqual`, `assertFalse`) provide adequate coverage.

## Validation

`python3 -m py_compile hallucinate_app/hallucinate_app/python/hallucinate_app/test/test_error_monitor.py`
passes with exit code 0.
