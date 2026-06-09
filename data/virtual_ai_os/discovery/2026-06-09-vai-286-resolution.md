# VAI-286 Resolution

Date: 2026-06-09
Task: VAI-286
Kind: swallowed_exception
Source: external/ipfs_kit/archive/legacy_servers/vscode_mcp_server.py:304

## Finding

The codebase scan identified a bare `except: pass` at line 304 in the
`system_health_tool` function that silently swallowed `OSError` exceptions
raised during `psutil.disk_usage()` calls for common paths.

Original code:
```python
except:
    pass
```

## Fix Applied

HAO-359 (commits `cb1230ff` and `66701704`) already fixed this finding
before VAI-286 was actioned. The bare except was replaced with a specific
`OSError` handler that records the error in the result dict:

```python
except OSError as path_err:
    health_data["disk_usage"][path] = {"error": str(path_err)}
```

This change ensures that:
- Only `OSError` (the expected exception for inaccessible paths) is caught
- The error message is preserved and returned to the caller instead of silently dropped
- The outer `except Exception` handler at line 313 still catches any unexpected errors

## Validation

```
python3 -m py_compile external/ipfs_kit/archive/legacy_servers/vscode_mcp_server.py
```

Result: PASS (exit code 0)

## Status

RESOLVED — fix already in place via HAO-359. No additional code changes required.
