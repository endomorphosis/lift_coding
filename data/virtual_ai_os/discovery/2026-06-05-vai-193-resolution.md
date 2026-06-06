# VAI-193 Resolution

Date: 2026-06-05
Task: VAI-193
Kind: swallowed_exception fix
Source: hallucinate_app/hallucinate_app/python/ipfs_accelerate_py.py:624

## Finding

Bare `except:` clause at line 624 swallowed all exceptions (including
`KeyboardInterrupt` and `SystemExit`) when attempting to put an error result
into the IPC result queue, with no logging whatsoever.

## Fix Applied

Replaced:
```python
except:
    pass
```

With:
```python
except Exception as queue_err:
    logger.warning(f"Failed to send error to result queue for {model_id}: {queue_err}")
```

This change:
- Narrows the catch to `Exception`, allowing `KeyboardInterrupt`/`SystemExit` to propagate normally.
- Logs a warning so queue failures are observable without crashing the subprocess.

## Validation

```
python3 -m py_compile hallucinate_app/hallucinate_app/python/ipfs_accelerate_py.py
```
Exit code: 0 (pass)
