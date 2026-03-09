# PR-017: Capability registry and execution parity foundation

## Goal
Implement the first roadmap slice that unifies direct-import, direct-CLI, and MCP-remote execution behind one canonical capability registry and one normalized result envelope.

## Why
- `implementation_plan/docs/15-meta-wearables-dat-mcpplusplus-integration-roadmap.md`
- `implementation_plan/docs/16-phase-1-capability-registry-execution-matrix.md`
- the repo already has partial registry/config/provider seams, but they do not yet define one end-to-end execution contract

## Scope

### Registry
- extend capability descriptors to include confirmation policy, schema refs, and result normalization metadata
- ensure provider aliases and server-family mapping remain stable

### Runtime
- add a shared execution entry point for capability execution
- centralize execution-mode resolution and fallback policy
- normalize success, failure, and `needs_input` payloads

### Trace and task integration
- persist `capability_id`, `server_family`, `execution_mode`, `tool_name`, `request_id`, and `run_id` consistently
- make delegated task flows and direct command flows use the same normalization layer

### Tests
- registry lookup tests
- execution-mode selection tests
- direct-vs-remote parity tests for the initial capability matrix
- regression tests for existing non-MCP providers

## Out of scope
- mobile DAT native implementation
- full provenance receipt persistence
- broad new natural-language grammar expansion

## Acceptance criteria
- the first six capability IDs in the Phase 1 matrix are executable through one shared runtime
- top-level result envelopes are shape-compatible across execution modes
- command router and task service emit consistent trace metadata
- existing providers continue to pass regression coverage

## Dependencies
- existing MCP provider/config groundwork in `src/handsfree/mcp/*`
- existing adapter seams for `ipfs_kit_py` and `ipfs_accelerate_py`
