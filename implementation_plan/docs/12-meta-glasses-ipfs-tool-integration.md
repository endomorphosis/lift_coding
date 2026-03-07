# Meta AI Glasses + IPFS Tooling Integration Plan

## Goal
Integrate `ipfs_datasets`, `ipfs_kit`, and `ipfs_accelerate` capabilities into the Meta AI glasses workflow with a two-mode strategy:

1. **Prototype mode (local/direct):**
   - direct CLI invocation and/or direct Python package imports
   - optimized for rapid iteration and validation
2. **Production mode (remote/MCP):**
   - tool execution through MCP servers (Mcp-Plus-Plus compatible)
   - optimized for security boundaries, scalability, and remote operation

## Why two modes
- Prototype mode minimizes integration friction and shortens the build-measure-learn loop.
- Production mode reduces local device coupling, centralizes execution, and supports policy/observability at service boundaries.
- A shared tool abstraction lets us validate behavior locally while preserving a migration path to MCP remote execution.

## Current-state assumptions
- Agent delegation and provider abstractions already exist in backend orchestration.
- Meta glasses app is the user interaction surface for voice/audio-driven commands.
- IPFS tool repositories are vendored as git submodules under `external/` for predictable local prototyping.

## Target architecture
### 1) Tool execution adapter layer
Introduce a single adapter contract in backend orchestration:
- `execute(tool_name, action, args, execution_mode)`
- `execution_mode in {direct_cli, direct_import, mcp_remote}`

This keeps command parsing and user experience stable while execution backends evolve.

### 2) Direct prototype adapters
- **CLI adapter**: shells out to tool CLIs with strict allowlisted commands and argument validation.
- **Import adapter**: imports package APIs directly when available for lower latency and richer typed responses.

### 3) MCP production adapter
- Route calls to MCP servers for:
  - datasets operations (`ipfs_datasets`)
  - IPFS utility operations (`ipfs_kit`)
  - acceleration/runtime operations (`ipfs_accelerate`)
- Normalize MCP responses into internal task states and spoken summaries.

### 4) Meta glasses command surface
Map high-value spoken intents to tool actions, for example:
- “Index this dataset in IPFS”
- “Pin this CID”
- “Run accelerated pipeline for <job>”
- “Summarize last IPFS task status”

## Phased implementation plan
### Phase A — foundation (submodules + contracts)
- Add git submodules for the three tool repos under `external/`.
- Define adapter interface and execution mode selection strategy.
- Add configuration schema for prototype/production mode selection.

### Phase B — prototype path (direct local execution)
- Implement CLI adapter with command allowlists, timeout controls, and output normalization.
- Implement import adapter where stable package entry points exist.
- Add local smoke flows from backend command path to adapters.

### Phase C — MCP remote path (production)
- Implement MCP client adapter for remote invocation.
- Add provider-specific mappings for datasets/kit/accelerate operations.
- Add retries, idempotency keys, and correlation IDs for long-running tasks.

### Phase D — Meta glasses UX alignment
- Add concise spoken confirmations and progress summaries for each tool class.
- Add “needs input” prompts for missing parameters.
- Ensure voice-first error messages are short and actionable.

### Phase E — hardening + rollout
- Add observability dashboards for success/error/latency by execution mode.
- Run staged rollout:
  1. internal prototype on direct mode
  2. shadow mode MCP verification
  3. production MCP default with direct fallback disabled by policy

## Configuration model
- `HANDSFREE_IPFS_EXECUTION_MODE` = `direct_cli|direct_import|mcp_remote`
- `HANDSFREE_IPFS_ALLOW_DIRECT` = `true|false` (prototype safety gate)
- Per-tool MCP endpoint settings (URL, auth, timeout)
- Per-tool direct mode settings (binary path/module toggle/timeouts)

## Security and safety requirements
- No raw shell passthrough from user utterances; enforce strict action allowlists.
- Secrets (tokens/credentials) sourced from existing secret manager paths, never logged.
- Task trace stores tool/action/correlation metadata; redact sensitive values.
- Production profile disables direct execution and enforces MCP remote only.

## Testing strategy
- Unit:
  - adapter mode selection
  - argument validation and normalization
  - state mapping from tool/MCP responses
- Integration:
  - direct CLI happy path + timeout/error handling
  - direct import happy path + import failure fallback
  - MCP mocked contracts for all three tool families
- End-to-end:
  - command -> task -> spoken response for representative intents

## Success criteria
- Prototype: a developer can run at least one end-to-end workflow per tool via direct mode.
- Production: same workflows succeed via MCP remote mode with parity in user-facing responses.
- Safety: no sensitive values exposed in traces/logs; command allowlists enforced.
- Reliability: retriable remote failures degrade gracefully with clear user feedback.

## Deliverables
- Submodule wiring under `external/`
- Adapter abstraction + mode routing
- Direct execution prototype path
- MCP remote production path
- Documentation/runbook for operating both modes
