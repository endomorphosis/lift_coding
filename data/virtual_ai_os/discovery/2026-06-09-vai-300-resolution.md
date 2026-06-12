# VAI-300 Resolution

Date: 2026-06-09
Task: VAI-300
Kind: swallowed_exception fix
Source: external/ipfs_kit/archive/mcp_final_20250414_082801/controllers/peer_websocket_controller_anyio.py:565

## Fix

Replaced bare `except Exception: pass` inside the cleanup block of `stop_peer_websocket_client`
with `except Exception as inner_exc: logger.warning(...)` so failures to clear the
`peer_websocket_client` attribute are surfaced in logs rather than silently discarded.

## Validation

```
python3 -m py_compile external/ipfs_kit/archive/mcp_final_20250414_082801/controllers/peer_websocket_controller_anyio.py
```
Exit code 0 — file compiles cleanly.
