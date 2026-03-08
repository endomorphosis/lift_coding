# PR-009: MCP++ integration for IPFS agent providers

## Goal
Add a production-ready integration path for `lift_coding` to use MCP server implementations from:
- `endomorphosis/ipfs_datasets_py`
- `endomorphosis/ipfs_kit_py`
- `endomorphosis/ipfs_accelerate_py`

...via the `endomorphosis/Mcp-Plus-Plus` protocol.

## Why (from the plan)
- `implementation_plan/docs/07-agent-orchestration.md`: provider abstraction and task lifecycle already exist.
- `src/handsfree/agent_providers.py`: provider interface (`start_task`, `check_status`, `cancel_task`) is ready for additional backends.
- Existing delegation paths are either stubbed or GitHub-dispatch based; MCP++ enables direct tool-capable providers.

## Scope
1. **Protocol and client foundation**
   - Add an MCP++ client module for:
     - server discovery/handshake
     - tool listing and invocation
     - request/response correlation for async task progress
   - Standardize error handling and timeout behavior across MCP++ calls.

2. **Provider implementations**
   - Add `ipfs_datasets_mcp`, `ipfs_kit_mcp`, and `ipfs_accelerate_mcp` providers implementing `AgentProvider`.
   - Add a shared MCP provider base that maps `lift_coding` task lifecycle to MCP++ states:
     - `created` -> `running` -> `needs_input`/`completed`/`failed`

3. **Provider selection and configuration**
   - Extend provider resolution to support MCP providers by explicit provider name.
   - Add environment configuration for each MCP server:
     - URL/transport
     - auth/token secret reference
     - per-provider enable/disable and timeout controls
   - Preserve existing precedence and fallback semantics.

4. **Traceability and observability**
   - Persist MCP++ metadata in task trace:
     - server id, tool name, request id, correlation id, external run id
   - Add structured logs for protocol calls (without logging secrets).
   - Add minimal metrics hooks for latency, success/failure, and retry counts.

5. **Tests**
   - Unit tests for:
     - provider registry and selection
     - MCP response-to-task-state mapping
     - retry and timeout behavior
   - Contract-style tests using mocked MCP++ responses for each IPFS provider.

6. **Documentation**
   - Update configuration docs and `.env.example` with MCP provider settings.
   - Add operator guide for running with MCP++ servers locally and in production.

## Out of scope
- Rewriting current non-MCP providers.
- Changes to mobile command UX beyond provider naming support.
- Auto-merge behavior (remains policy-gated and manual approval based).

## Issues this PR should close (create these issues)
- Agent: add MCP++ client and protocol adapter
- Agent: add ipfs_datasets MCP provider
- Agent: add ipfs_kit MCP provider
- Agent: add ipfs_accelerate MCP provider
- Configuration: MCP provider env vars and secure auth handling
- Testing: MCP provider contract tests and lifecycle mapping tests
- Observability: MCP protocol traces and metrics

## Acceptance criteria
- A delegated task can run through each MCP provider by name:
  - `ipfs_datasets_mcp`
  - `ipfs_kit_mcp`
  - `ipfs_accelerate_mcp`
- Provider calls conform to MCP++ protocol and return deterministic lifecycle transitions.
- Existing providers (`copilot`, `custom`, `mock`, `github_issue_dispatch`) continue to work unchanged.
- Configuration is documented and validated at startup with clear errors on missing required values.
- Tests cover success, timeout, and protocol-error scenarios for all MCP providers.

## Dependencies
- PR-008 (agent orchestration stub and provider abstraction)
- Existing env/config and secret management paths in current backend
