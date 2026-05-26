# MCP++ Canonical Source Resolution

Date: 2026-05-22

## Question

Should `mcp_plus_plus` be added as a root-tracked submodule in this monorepo?

## Evidence

- Requested upstream under review: `https://github.com/endomorphosis/mcp_plus_plus`
- Source-check result on 2026-05-22: `remote: Repository not found`
- Existing integration evidence inside this repo already places MCP++-like behavior across multiple component repos:
  - `swissknife` owns ORB, MCP-IDL, and operator-surface integrations.
  - `external/ipfs_accelerate` contributes runtime-placement and execution surfaces.
  - `external/ipfs_datasets` contributes grounding, autonomous task-board supervision, and MCP task routing.

## Decision

Do not add a root-tracked `mcp_plus_plus` submodule at this time.

Treat MCP++ as a distributed protocol surface across the reviewed component repos until a valid canonical upstream can be reviewed and pinned safely.

## Operational contract

- `.gitmodules` must remain free of a speculative or broken `mcp_plus_plus` URL.
- The virtual AI OS plan should continue to refer to canonical-source resolution as complete for the current review cycle because the safe outcome was documented, not because the repository was found.
- Re-open this task only when a valid upstream repository exists and its scope is clearly distinct from the already-integrated surfaces in `swissknife`, `ipfs_accelerate_py`, and `ipfs_datasets_py`.
