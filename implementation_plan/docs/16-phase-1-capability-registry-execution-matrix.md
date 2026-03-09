# Phase 1 Capability Registry And Execution Matrix

## Goal
Turn the roadmap in `15-meta-wearables-dat-mcpplusplus-integration-roadmap.md` into the first implementation slice:

- one canonical capability registry
- one normalized result envelope
- one parity matrix across `direct_import`, `direct_cli`, and `mcp_remote`
- one set of acceptance tests that can run without wearable hardware

This is the backend/control-plane prerequisite for both DAT mobile work and full MCP++ rollout.

## Why this is first
The repository already has partial capability and provider seams:

- `src/handsfree/mcp/catalog.py`
- `src/handsfree/mcp/capabilities.py`
- `src/handsfree/mcp/config.py`
- `src/handsfree/agent_providers.py`
- `src/handsfree/commands/router.py`
- `src/handsfree/ipfs_accelerate_adapters.py`
- `src/handsfree/ipfs_kit_adapters.py`

What is still missing is a single execution contract that the command router, task service, mobile cards, and MCP providers can all target consistently.

## Deliverables

### 1. Canonical capability model
Each supported capability needs one canonical definition with:

- `capability_id`
- `provider_name`
- `server_family`
- `title`
- `description`
- `execution_modes`
- `default_execution_mode`
- `confirmation_policy`
- `input_schema_ref`
- `result_schema_ref`
- `voice_formatter`
- `follow_up_action_builder`

### 2. Normalized execution result envelope
Every route should resolve into one shared payload:

```json
{
  "capability_id": "ipfs.kit.pin",
  "provider": "ipfs_kit_mcp",
  "server_family": "ipfs_kit",
  "execution_mode": "mcp_remote",
  "status": "completed",
  "spoken_text": "Pin completed.",
  "summary": "Pinned CID bafy...",
  "structured_output": {},
  "follow_up_actions": [],
  "trace": {
    "request_id": "req_123",
    "run_id": "run_456",
    "tool_name": "tools_dispatch"
  },
  "artifact_refs": {
    "result_cid": "bafy...",
    "receipt_ref": null,
    "event_dag_ref": null
  }
}
```

### 3. Execution-mode selector
Mode selection should be deterministic:

1. explicit request override
2. capability-supported modes
3. provider/server configuration
4. environment policy
5. fallback only if permitted

### 4. Parity matrix
The first capability set should be small and testable:

| Capability ID | Provider family | Direct import | Direct CLI | MCP remote | User-facing entry point |
| --- | --- | --- | --- | --- | --- |
| `embedding` | `ipfs_datasets` | yes | no | yes | AI/search workflows |
| `ipfs_pin` | `ipfs_kit` | yes | optional | yes | command/router + follow-up actions |
| `workflow` | `ipfs_accelerate` | optional | optional | yes | delegated task workflows |
| `agentic_fetch` | `ipfs_accelerate` | no | optional | yes | task/delegation |
| `dataset_discovery` | `ipfs_datasets` | no | optional | yes | dataset search |
| `storage` | `ipfs_kit` | no | optional | yes | result storage management |

The first implementation target is not perfect feature parity. It is deterministic routing and normalized output parity where each route exists.

## Required code changes

### Registry and models
- extend `src/handsfree/mcp/catalog.py`
- add richer result and schema models to `src/handsfree/mcp/models.py`
- add normalization helpers under `src/handsfree/mcp/capabilities.py`

### Runtime and routing
- add or extend a shared execution runtime under `src/handsfree/mcp/`
- route command and task entry points through the same normalization path
- ensure `src/handsfree/agent_providers.py` stores `capability_id` and `execution_mode` consistently in task trace

### Cards and follow-up actions
- map normalized results to follow-up actions once
- consume them from mobile UI instead of provider-specific branches where possible

## Acceptance criteria

### Functional
- each of the six initial capabilities resolves through the registry
- unsupported execution modes fail clearly and predictably
- direct and remote executions produce the same top-level result shape
- task traces capture `capability_id`, `execution_mode`, `server_family`, and tool metadata

### Testing
- unit tests cover registry lookup and mode resolution
- contract tests cover result-envelope normalization
- parity tests compare direct and remote output shapes for the initial capability set
- regression tests confirm existing providers still work

## Sequencing after Phase 1
Once this lands:

1. DAT mobile diagnostics can consume capability/routing state from stable backend payloads.
2. `ipfs_accelerate_py` can become the first fully productionized remote MCP++ path.
3. `ipfs_kit_py` and `ipfs_datasets_py` can be added incrementally without inventing new orchestration contracts.
