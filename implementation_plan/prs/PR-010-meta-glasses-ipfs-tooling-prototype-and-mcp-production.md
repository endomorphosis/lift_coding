# PR-010: Meta glasses IPFS tooling integration (prototype direct, production MCP)

## Goal
Implement the first delivery slice that integrates `ipfs_datasets`, `ipfs_kit`, and `ipfs_accelerate` into the Meta AI glasses workflow with:
- **prototype execution** via direct CLI/package imports
- **production execution** via MCP remote servers

## Scope
- Add adapter contract for execution mode routing.
- Add direct CLI/import adapters for local prototyping.
- Add MCP adapter for remote execution compatibility.
- Add config flags and safety gates to separate prototype vs production behavior.
- Add task trace + observability for all execution modes.

## Out of scope
- Full intent grammar expansion for every tool command.
- Production rollout to all users in this PR (staged rollout only).
- Non-IPFS tooling integrations.

## Acceptance criteria
- A representative command per tool works in direct prototype mode.
- The same commands work in MCP remote mode with equivalent user-facing status.
- Production mode can enforce MCP-only execution via configuration.
- Logs/traces redact sensitive values and preserve correlation IDs.

## Dependencies
- `implementation_plan/docs/12-meta-glasses-ipfs-tool-integration.md`
- Existing agent orchestration/provider infrastructure
