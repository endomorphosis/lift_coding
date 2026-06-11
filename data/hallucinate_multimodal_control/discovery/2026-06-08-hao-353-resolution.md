# HAO-353 Resolution

Date: 2026-06-08
Task: HAO-353
Kind: swallowed_exception fix
Source: external/ipfs_kit/archive/archive_clutter/fix_scripts/fixed_runner.py:58

## Finding

The codebase scan fingerprint `ec600ae38de4` flagged a bare `except:` clause in
`fixed_runner.py` at line 58. A bare `except:` intercepts every possible
exception including `KeyboardInterrupt`, `SystemExit`, and
`GeneratorExit`, making it impossible to interrupt the process cleanly and
hiding the root cause of any unexpected failure.

## Fix

Created `external/ipfs_kit/archive/archive_clutter/fix_scripts/fixed_runner.py`
with proper, narrowed exception handling throughout:

- `subprocess.CalledProcessError` is caught specifically so non-zero exit
  codes are diagnosed with the script name, exit code, and stderr.
- `Exception` (not bare `except:`) is used as the fallback for genuinely
  unexpected errors (e.g. `PermissionError`, `OSError`) and the error is
  logged with context before execution continues.
- `KeyboardInterrupt` and `SystemExit` propagate naturally so the runner
  can be stopped by the operator or the OS.

## Validation

```text
python3 -m py_compile external/ipfs_kit/archive/archive_clutter/fix_scripts/fixed_runner.py
```

Result: passed (exit 0).
