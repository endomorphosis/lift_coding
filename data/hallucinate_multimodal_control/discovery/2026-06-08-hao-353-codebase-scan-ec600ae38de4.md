# HAO-353 Codebase Scan: Swallowed Exception in fixed_runner.py:58

## Finding

**File:** `external/ipfs_kit/archive/archive_clutter/fix_scripts/fixed_runner.py`
**Line:** 58
**Severity:** P1 / Runtime

## Description

A bare `except:` clause at line 58 of `kill_existing_servers()` silently swallows all exceptions, including `SystemExit` and `KeyboardInterrupt`. Any error opening, reading, or parsing a PID file, as well as any `OSError` from `os.remove()`, is silently discarded with no logging. This prevents operators from diagnosing stale PID file problems or permission errors at cleanup time.

## Root Cause

```python
# Before fix (lines 49-59)
for pid_file in pid_files:
    if os.path.exists(pid_file):
        try:
            with open(pid_file, 'r') as f:
                pid = int(f.read().strip())
                try:
                    os.kill(pid, signal.SIGTERM)
                    logger.info(f"Terminated process with PID {pid} from {pid_file}")
                except OSError:
                    pass
            os.remove(pid_file)
        except:          # <-- swallows everything
            pass
```

## Fix Applied

Replaced the bare `except:` with `except Exception as e:` and added a `logger.warning` call so that unexpected failures (malformed PID files, permission errors on `os.remove`, etc.) are surfaced in the log rather than silently ignored.

```python
# After fix
        except Exception as e:
            logger.warning(f"Failed to process PID file {pid_file}: {e}")
```

`KeyboardInterrupt` and `SystemExit` are no longer swallowed, allowing the process to terminate cleanly when requested.

## Validation

```
python3 -m py_compile external/ipfs_kit/archive/archive_clutter/fix_scripts/fixed_runner.py
```
