# HAO-333 Resolution

Date: 2026-06-08
Task: HAO-333
Kind: swallowed_exception fix
Source: external/ipfs_kit/archive/applied_patches/fix_lassie_integration.py:273

## Finding

The scanner reported a broad `except Exception:` in `restart_mcp_server()`.
That handler wrapped the fallback `pkill -f enhanced_mcp_server.py` cleanup
attempt and silently ignored failures, which made unexpected restart cleanup
problems invisible.

## Fix

The handler now binds the exception and logs a warning with the failure details.
The restart flow still continues after a failed best-effort `pkill`, but the
runtime problem is no longer swallowed without evidence.

## Validation

```text
python3 -m py_compile external/ipfs_kit/archive/applied_patches/fix_lassie_integration.py
# exit 0
```
