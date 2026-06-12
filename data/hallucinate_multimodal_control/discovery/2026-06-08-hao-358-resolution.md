# HAO-358 Resolution

Date: 2026-06-08
Task: HAO-358
Kind: swallowed_exception fix
Source: external/ipfs_kit/archive/cli_drafts/ipfs_kit_cli_ultra_fast.py

## Finding

Two bare `except:` clauses were found that silently swallowed all exceptions
including `KeyboardInterrupt`, `SystemExit`, and other non-recoverable errors.

- Line 78: inside `cmd_status`, reading `/tmp/ipfs_kit_daemon.pid`
- Line 389: inside `_check_daemon_running`, reading the same PID file

## Fix

Both bare `except:` clauses were replaced with `except (OSError, ValueError):`,
which captures only the errors that legitimately can occur:
- `OSError` / `FileNotFoundError` / `PermissionError`: PID file missing or unreadable
- `ValueError`: PID file contains non-integer content

This ensures `KeyboardInterrupt`, `SystemExit`, and other unexpected exceptions
propagate correctly instead of being silently discarded.

## Validation

```
python3 -m py_compile external/ipfs_kit/archive/cli_drafts/ipfs_kit_cli_ultra_fast.py
```

Result: PASS (exit 0, no output)
