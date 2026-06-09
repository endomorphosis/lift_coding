# VAI-152 Resolution

Date: 2026-06-09
Task: VAI-152 — Review swallowed exception path in ipfs_model_manager.py:454
Kind: swallowed_exception fix

## Finding

The original scan flagged a bare `except:` near line 454 in
`hallucinate_app/hallucinate_app/python/hallucinate_app/ipfs_model_manager.py`.
By the time of this fix, the bare `except:` had already been narrowed to
`except Exception:`, but two residual problems remained in the IPFS import test
block of `IPFSModelManager.test()`:

1. **Resource leak**: `test_file` (the NamedTemporaryFile path) was only cleaned
   up in the happy path.  If an exception occurred between the file's creation
   and the inner `os.unlink` call the temp file was never removed.

2. **Swallowed error detail**: The `except Exception:` block logged the traceback
   via `logger.exception` but did not record any error message in the returned
   test-results dict, making it hard for callers to surface the failure reason.

## Fix Applied

- Initialised `test_file = None` before the `try` block so the variable is
  always defined in the `finally` clause.
- Moved temp-file cleanup into a `finally` block so it runs regardless of
  success or exception.
- Bound the caught exception to a name (`except Exception as exc`) and stored
  `str(exc)` in `ipfs_import_error`.
- Added `ipfs_import_result` dict (`{"success": …, "error": …}`) to the
  returned results under `imports.ipfs_details` so callers can inspect failure
  reasons without parsing log output.

## Validation

```
python3 -m py_compile hallucinate_app/hallucinate_app/python/hallucinate_app/ipfs_model_manager.py
```

Passes with exit code 0.
