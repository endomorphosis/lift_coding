# VAI-180 Swallowed Exception Resolution

Date: 2026-06-23
Task: VAI-180
Source finding: hallucinate_app/hallucinate_app/python/hallucinate_app/pyarrow_content_index.py:925

## Resolution

The `lookup_by_path` implementation wrapped the full lookup path in a broad
`except Exception` block, logged the exception, and immediately re-raised it.
Because the handler did not recover or add actionable context, it duplicated
traceback logging while preserving the same failure behavior.

The handler was removed so lookup failures now propagate with their original
traceback. Normal not-found behavior still returns `None` through the existing
indexed and prefix-match lookup paths.

## Validation

Passed:

```bash
python3 -m py_compile hallucinate_app/hallucinate_app/python/hallucinate_app/pyarrow_content_index.py
```
