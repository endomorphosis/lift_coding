# VAI-152 Swallowed Exception Review

Date: 2026-06-23
Task: VAI-152
Source finding: `hallucinate_app/hallucinate_app/python/hallucinate_app/ipfs_model_manager.py:454`

## Finding

The scan evidence flagged a bare `except:` in the IPFS import self-test cleanup path. The current exception handling now records the IPFS import failure in the returned test details and logs the traceback with `logger.exception`.

## Follow-up Fix

The reviewed code also had two cleanup paths for the same temporary file: a success-path `os.unlink(test_file)` and a `finally` block that unlinks the same file. After a successful cleanup, the `finally` block could log a misleading warning for the already-removed file.

The implementation now relies on the single `finally` cleanup path so success and failure cases use the same logged cleanup behavior.

## Validation

Run:

```sh
python3 -m py_compile hallucinate_app/hallucinate_app/python/hallucinate_app/ipfs_model_manager.py
```
