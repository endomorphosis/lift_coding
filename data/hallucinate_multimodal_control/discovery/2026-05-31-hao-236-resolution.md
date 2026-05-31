# HAO-236 Resolution

Date: 2026-05-31
Source: hallucinate_app/hallucinate_app/python/hallucinate_app/ipfs_model_manager.py:463
Kind: swallowed_exception
Status: fixed

## Finding

Bare `except:` clause at line 463 silently swallowed any exception from
`os.unlink(test_file)` during cleanup in the `test` method.  A bare `except`
catches `BaseException` (including `KeyboardInterrupt`, `SystemExit`, etc.),
which is wider than intended and hides unexpected failures.

## Fix

Replaced bare `except:` with `except OSError:`, which is the correct exception
type for file-system operations like `os.unlink`.  Other exceptions (including
`KeyboardInterrupt`) will now propagate normally.

## Validation

```
python3 -m py_compile hallucinate_app/hallucinate_app/python/hallucinate_app/ipfs_model_manager.py
```
Passed with exit code 0.
