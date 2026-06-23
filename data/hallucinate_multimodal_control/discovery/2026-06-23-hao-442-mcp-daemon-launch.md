# HAO-442 MCP Daemon Launch Path

Date: 2026-06-23
Task: HAO-442
Track: launch
Scope: Hallucinate App launch ownership for `ipfs_accelerate_py`,
`ipfs_datasets_py`, and `ipfs_kit_py` MCP daemons.

## Summary

Hallucinate App now owns the Python MCP daemon launch path. The Electron main
process starts the daemons, supervises daemon health, records launch receipts,
and exposes renderer-safe IPC methods that Swissknife and Meta glasses can use
to render daemon status. Swissknife applications may request capabilities, but
the launch contract keeps process ownership in Hallucinate App.

## Launch Order

| Order | Daemon id | Package | Entrypoint | Port | Health |
| --- | --- | --- | --- | --- | --- |
| 10 | `ipfs-kit` | `ipfs_kit_py` | `python -m ipfs_kit_py.cli mcp start` | `3001` | `GET /health` plus process liveness |
| 20 | `ipfs-datasets` | `ipfs_datasets_py` | `python -m ipfs_datasets_py.mcp_server --http --port 3002` | `3002` | `GET /health` plus process liveness |
| 30 | `ipfs-accelerate` | `ipfs_accelerate_py` | `python -m ipfs_accelerate_py.cli mcp start --port 3003` | `3003` | `GET /health` plus process liveness |

Shutdown runs in reverse order so `ipfs_accelerate_py` and
`ipfs_datasets_py` leave before the storage/IPFS daemon.

## Environment

Each daemon receives a bounded launch environment from
`hallucinate_app/node/mcp_daemon_manager.js`:

- `PYTHONUNBUFFERED=1`
- `PYTHONPATH=<daemon cwd>:<hallucinate_app root>:<existing PYTHONPATH>`
- `HALLUCINATE_APP_MCP_DAEMON_ID`
- `HALLUCINATE_APP_MCP_PACKAGE`
- `HALLUCINATE_APP_MCP_PORT`
- `HALLUCINATE_APP_CONTROL_SURFACE_CONTRACT_REF`
- `CONTROL_SURFACE_DAEMON_MEDIATION`, default `shadow`

The receipt path records only this redacted subset and does not persist
credentials, raw service payloads, transcripts, prompts, media, or arguments.

## Health Checks And Restart Behavior

Daemon health checks combine process liveness with a bounded HTTP health probe.
Startup waits for an initial health result and emits `launch_health_checked`.
The periodic daemon health loop emits `daemon_health` receipts every configured
interval, default `30000ms`.

Crash exits and failed process liveness both schedule an auto-restart when the
daemon has not exceeded `MCP_DAEMON_MAX_RESTARTS`, default `3`. Restart events
emit `restart_scheduled` receipts that include restart count, limit, reason,
and delay. Manual restarts go through the same stop/start path and receipt
schema.

## Mediation Hooks

The launch path preserves the existing daemon mediation hook:
`ControlSurfaceInvocationGate.beforeInvoke`. Daemon-managed service dispatch
uses `beforeInvoke()` or `invokeManagedService()` before transport callbacks.
The daemon-specific contract refs are:

- `control_surface_contract:mcp-daemon:ipfs-kit`
- `control_surface_contract:mcp-daemon:ipfs-datasets`
- `control_surface_contract:mcp-daemon:ipfs-accelerate`

Renderer callers can inspect launch state through `hallucinate_app/preload.js`:

- `window.electronAPI.daemon.getLaunchPlan()`
- `window.electronAPI.daemon.getLaunchReceipts(limit)`
- `window.electronAPI.daemon.checkHealth(daemonId)`
- `window.electronAPI.daemon.startAll()`
- `window.electronAPI.daemon.stopAll()`

## Launch Receipts

Every launch and daemon health receipt uses
`receipt_schema: mcp_daemon_launch_receipt_v1` with `task_id: HAO-442`.
Receipts include daemon id, package, startup order, exact entrypoint, cwd, pid,
port, endpoint, transport, RPC path, health path, mediation hook, control
surface contract ref, Swissknife consumer, Meta glasses render profile,
restart count, max restart limit, redaction profile, event details, and a
deterministic `receipt_cid`.

Swissknife and Meta glasses should render the receipt profile
`daemon-health-summary`: daemon id, package, status/outcome, port, health
summary, restart count, and latest receipt CID.

## Implementation Evidence

- `hallucinate_app/hallucinate_app/node/mcp_daemon_manager.js` defines ordered
  daemon configs, launch environment construction, health checks, restart
  receipts, `getLaunchPlan()`, `getLaunchReceipts()`, and
  `checkDaemonHealth()`.
- `hallucinate_app/index.js` exposes launch-plan, launch-receipt, health,
  start-all, and stop-all IPC handlers.
- `hallucinate_app/preload.js` exposes the daemon launch and daemon health IPC
  methods to renderers without enabling Node integration.
- `hallucinate_app/scripts/verify_mcp_daemon_launch.mjs` validates the HAO-442
  launch contract without spawning Python daemons.
- `hallucinate_app/docs/MCP_DAEMON_ARCHITECTURE.md` documents the launch path,
  daemon health checks, restart behavior, mediation hooks, and receipt fields.
