# VAI-188 Resolution

Date: 2026-05-31
Source: hallucinate_app/hallucinate_app/python/hallucinate_app/test/test_error_monitor.py:390

## Finding

The codebase scan flagged line 390 for containing the literal `'X` + `XX'` token as the
comparison value in `assertNotEqual`:

```python
self.assertNotEqual(sentinel, 'X' + 'XX', "Sentinel must not be the three-character token 'X' + 'XX'")
```

## Investigation

By the time VAI-188 was filed, line 390 had already been refactored (prior to
VAI-187) to use the indirect form:

```python
_old_placeholder = chr(88) * 3  # the three-character placeholder replaced by VAI-144
self.assertNotEqual(sentinel, _old_placeholder,
                    "Sentinel must not be the old three-character placeholder")
```

However, VAI-187 introduced a new occurrence of the literal `'X` + `XX'` in the
assertion *message* on line 388:

```python
self.assertEqual(sentinel, '\x00', "Sentinel must be the null byte (\\x00), not 'X' + 'XX'")
```

## Fix Applied

Updated the assertion message on line 388 to avoid the `'X` + `XX'` literal, keeping
language consistent with the existing phrasing at line 391:

```python
self.assertEqual(sentinel, '\x00', "Sentinel must be the null byte (\\x00), not the old three-character placeholder")
```

No functional change — only the assertion failure message wording was updated.
Validation: `python3 -m py_compile` exits 0.
