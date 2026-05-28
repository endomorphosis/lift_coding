# VAI-138 Resolution

Date: 2026-05-28
Task: VAI-138
Source finding: hallucinate_app/hallucinate_app/python/hallucinate_app/ipfs_accelerate_server_mp.py:202
Fingerprint: bd5d75fcd4e5502d03848e45546036e5fe6250b6
Kind: swallowed_exception

## Finding

Bare `except OSError: pass` at line 202 of `ipfs_accelerate_server_mp.py` (inside
the file-based fallback path of the `get` method on `PlasmaIPCManager`) silently
swallowed any `OSError` raised when deleting a temporary file after reading it.

## Fix

Changed:
```python
except OSError:
    pass
```
to:
```python
except OSError as e:
    logger.warning("Failed to clean up temporary file %s: %s", file_path, e)
```

The block does not re-raise because this is best-effort cleanup — the object has
already been read and returned successfully. Logging the warning ensures that
persistent cleanup failures (e.g., permission errors, NFS stale handles) surface
in logs rather than being silently discarded.

## Validation

```
python3 -m py_compile hallucinate_app/hallucinate_app/python/hallucinate_app/ipfs_accelerate_server_mp.py
```
→ OK

## Submodule Commit

Fix applied in hallucinate_app submodule at: `d341a926fa4ba5eef79503d4bcbc5309d64d58d1`
