# VAI-284 Resolution

Date: 2026-06-08
Task: VAI-284
Kind: swallowed_exception
Source: external/ipfs_kit/archive/legacy_servers/enhanced_mcp_server_direct_ipfs.py:232

## Fix

Replaced bare `except: pass` with `except Exception as kill_err:` that logs the
error via `logger.warning`. This ensures that failures in the force-kill fallback
are visible in logs without crashing the cleanup path.

## Validation

`python3 -m py_compile external/ipfs_kit/archive/legacy_servers/enhanced_mcp_server_direct_ipfs.py` → OK
