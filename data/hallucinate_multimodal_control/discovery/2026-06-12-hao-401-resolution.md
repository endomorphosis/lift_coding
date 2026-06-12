# HAO-401 Resolution

Date: 2026-06-12
Source: external/ipfs_kit/archive/mcp_final_20250414_082801/extensions/websocket.py:131
Finding: annotated_followup - `# TODO: Register event handlers for various MCP operations`

## Action Taken

Replaced the placeholder MCP event-hook TODO with idempotent WebSocket event
handler registration for the core MCP operations:

- `initialize`
- `tools/list`
- `tools/call`
- `resources/list`
- `resources/read`
- `prompts/list`
- `prompts/get`
- `notifications/initialized`
- `ping`

Each registered handler now broadcasts MCP event payloads to both
operation-specific `mcp:<operation>` channels and the aggregate `mcp:all`
channel. The setup path validates that the WebSocket service exposes both
event-handler registration and a broadcast-capable manager before reporting
success.

Also fixed the malformed `update_websocket_status` dictionary literal in the
same file so the module compiles.

## Validation

```text
python3 -m py_compile external/ipfs_kit/archive/mcp_final_20250414_082801/extensions/websocket.py
# exit 0
```
