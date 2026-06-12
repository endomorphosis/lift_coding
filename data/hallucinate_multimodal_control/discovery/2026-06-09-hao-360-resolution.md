# HAO-360 Resolution

Date: 2026-06-09
Task: HAO-360
Finding: swallowed_exception at external/ipfs_kit/archive/legacy_servers/vscode_mcp_server.py:304

## Change

Replaced bare `except: pass` with `except OSError as path_err:` that records the
error string in `health_data["disk_usage"][path]` instead of silently discarding it.

The original bare `except:` masked access failures on disk paths silently; the fix
gives callers visibility into which paths could not be queried while still allowing
the health check to succeed for other paths.

## Validation

`python3 -m py_compile external/ipfs_kit/archive/legacy_servers/vscode_mcp_server.py` → OK
