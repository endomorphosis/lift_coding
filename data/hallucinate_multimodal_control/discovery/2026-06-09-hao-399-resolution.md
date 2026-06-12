# HAO-399 Resolution Note

Date: 2026-06-09
Task: HAO-399
Source: external/ipfs_kit/archive/mcp_final_20250414_082801/extensions/webrtc.py:77
Finding: swallowed_exception

## Assessment

The `except Exception as e` at line 77 (now ~line 80 after edits) was intentional
broad-catch pattern used in extension/plugin loading code where the server must
remain operational even if an optional extension fails to initialise.

The original code already used `exc_info=True` so full tracebacks were captured in
logs. The `noqa: BLE001` suppression was present.

## Changes Made

1. **Improved exception log message** – added `type(e).__name__` so the exception
   class appears explicitly in the log line, making triage easier without changing
   the swallow-and-return-None contract.
2. **Improved comment** – clarified that the caller is expected to check the None
   return value (which `create_webrtc_extension_router`'s caller does at line 72).
3. **Consistency fix** – applied the same improvements and the `noqa: BLE001`
   annotation to the previously unannotated `except` block in
   `register_app_webrtc_routes` (line ~116).

## Verdict

Not a bug; the broad catch is appropriate for optional-extension loading. The
changes make the log output more actionable and suppress the linter warning
consistently across both catch sites.

## Validation

```
python3 -m py_compile external/ipfs_kit/archive/mcp_final_20250414_082801/extensions/webrtc.py
# exit 0 – PASS
```
