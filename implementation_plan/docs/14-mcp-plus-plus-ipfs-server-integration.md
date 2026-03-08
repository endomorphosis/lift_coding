# MCP++ IPFS Server Integration Plan

## Goal
Add a first-class integration path that lets HandsFree use MCP server implementations from:
- `endomorphosis/ipfs_datasets_py`
- `endomorphosis/ipfs_kit_py`
- `endomorphosis/ipfs_accelerate_py`

...through the `endomorphosis/Mcp-Plus-Plus` protocol, while fitting the package's existing agent lifecycle, command router, and Meta glasses interaction model.

## Why this needs its own plan
The repo already has pieces of this story, but they are split across:
- agent-provider orchestration
- direct `ipfs_datasets_py` router adapters
- Meta glasses voice command plans
- hierarchical planner plans
- Bluetooth/libp2p transport work

What is missing is one concrete plan that says how MCP++ servers become usable inside this package without bypassing current abstractions or creating a separate parallel stack.

## Current state in this repo
The following integration points already exist and should be reused:
- `src/handsfree/agent_providers.py`
  - stable provider contract: `start_task`, `check_status`, `cancel_task`
  - current provider registry and provider-name dispatch
- `src/handsfree/agents/service.py`
  - provider selection precedence
  - task creation, notification emission, and trace updates
- `src/handsfree/commands/router.py`
  - existing `agent.delegate` command path
  - confirmation gating for side-effectful actions
- `src/handsfree/ipfs_datasets_routers.py`
  - existing optional direct-import adapters for `ipfs_datasets_py`
  - useful as the prototype and fallback path

This means the MCP++ work should be implemented as an extension of the existing provider and command system, not as a separate top-level subsystem.

## Target outcomes
1. A user can delegate IPFS-capable tasks through named MCP-backed providers.
2. Meta glasses flows can trigger those tasks with short, voice-safe confirmations and progress summaries.
3. The natural-language planning layer can target the same MCP-backed capabilities deterministically.
4. The system can run in two modes:
   - prototype: direct import or CLI
   - production: MCP++ remote execution
5. Existing non-IPFS providers continue to work unchanged.

## Architectural decision
Use a two-layer integration model:

### Layer 1: MCP++ client and capability runtime
Add a shared MCP++ runtime inside `src/handsfree/` that handles:
- endpoint configuration
- session setup and handshake
- capability discovery
- tool invocation
- async status polling or event consumption
- timeout, retry, and idempotency behavior
- response normalization

This layer should know MCP++.

### Layer 2: HandsFree-facing provider and planner adapters
Build HandsFree-specific adapters on top of that runtime:
- agent providers for delegated tasks
- tool executors for direct command/planner execution
- trace and spoken-summary mapping

This layer should know HandsFree concepts such as:
- `AgentTask`
- command intent names
- proof/planner node execution
- notification text

Keeping these layers separate avoids leaking protocol details into the command router and avoids hard-coding task lifecycle behavior inside the raw MCP client.

## MCP++ integration surfaces

### A) Delegated agent-provider surface
This is the fastest path to production value because the repo already has a task lifecycle.

Add three new providers:
- `ipfs_datasets_mcp`
- `ipfs_kit_mcp`
- `ipfs_accelerate_mcp`

Each provider should:
- implement `AgentProvider`
- map a HandsFree task instruction into one or more MCP++ tool calls
- persist external request metadata in the task trace
- expose progress through `check_status`

This path is best for:
- longer-running jobs
- remote execution
- auditable traces
- notification-driven progress updates

### B) Direct tool-execution surface
This is needed for voice-first workflows where `agent.delegate` is too indirect.

Add a shared internal tool execution contract, for example:
- `execute_tool(server_family, tool_name, arguments, execution_mode, context)`

Supported execution modes:
- `direct_import`
- `direct_cli`
- `mcp_remote`

This execution surface should be used by:
- future IPFS command intents
- the hierarchical planner described in `13-nl-prompt-to-hierarchical-tools-ipfs-datasets.md`
- direct Meta glasses command flows where the user expects immediate execution rather than a delegated agent task

### C) Capability-grounding surface
The planner needs a capability model that is stable even if MCP servers evolve.

Define a local capability registry with:
- canonical HandsFree capability ids
- server family mapping
- MCP tool name
- input schema
- confirmation policy
- voice-summary formatter
- fallback availability in direct mode

Example capability families:
- dataset search and selection
- manifest/provenance generation
- CID pinning and publishing
- content fetch and metadata lookup
- accelerated execution or batching

This registry becomes the contract between:
- prompt parsing
- theorem/proof validation
- execution routing
- spoken response synthesis

## Proposed module layout
Recommended additions under `src/handsfree/`:

- `mcp/client.py`
  - low-level MCP++ transport, handshake, request/response handling
- `mcp/models.py`
  - typed MCP++ request, response, and error models
- `mcp/config.py`
  - env-driven endpoint and auth configuration
- `mcp/ipfs_registry.py`
  - mapping of HandsFree capability ids to server/tool metadata
- `mcp/tool_runtime.py`
  - normalized `execute_tool(...)` orchestration
- `mcp/providers.py`
  - shared base class for MCP-backed `AgentProvider` implementations
- `mcp/tracing.py`
  - trace payload builders and metadata redaction

Recommended additions under `src/handsfree/commands/` and planner-related areas:
- command router hooks for IPFS intent families
- planner-to-tool-runtime binding
- result summarizers for voice output

## Provider behavior contract
Each MCP-backed provider should produce HandsFree lifecycle states only from this allowlist:
- `created`
- `running`
- `needs_input`
- `completed`
- `failed`

Suggested mapping:
- MCP accepted or running -> `running`
- MCP requests missing params or confirmation -> `needs_input`
- MCP result available -> `completed`
- MCP protocol or tool failure -> `failed`

Each provider trace should include:
- `provider`
- `mcp_server_family`
- `mcp_endpoint`
- `mcp_request_id`
- `mcp_run_id` if the protocol exposes one
- `tool_name`
- `capability_id`
- `correlation_id`
- `retry_count`
- `last_protocol_state`

## Configuration model
Use repo-consistent environment-driven configuration.

Global flags:
- `HANDSFREE_MCP_ENABLED=true|false`
- `HANDSFREE_IPFS_EXECUTION_MODE=direct_import|direct_cli|mcp_remote`
- `HANDSFREE_IPFS_DIRECT_FALLBACK=true|false`

Per-server configuration:
- `HANDSFREE_MCP_IPFS_DATASETS_URL`
- `HANDSFREE_MCP_IPFS_KIT_URL`
- `HANDSFREE_MCP_IPFS_ACCELERATE_URL`
- `HANDSFREE_MCP_IPFS_DATASETS_AUTH_SECRET`
- `HANDSFREE_MCP_IPFS_KIT_AUTH_SECRET`
- `HANDSFREE_MCP_IPFS_ACCELERATE_AUTH_SECRET`
- `HANDSFREE_MCP_DEFAULT_TIMEOUT_S`
- `HANDSFREE_MCP_DEFAULT_POLL_INTERVAL_S`

Per-provider toggles:
- `HANDSFREE_AGENT_ENABLE_IPFS_DATASETS_MCP`
- `HANDSFREE_AGENT_ENABLE_IPFS_KIT_MCP`
- `HANDSFREE_AGENT_ENABLE_IPFS_ACCELERATE_MCP`

Startup validation should fail clearly when a provider is selected but its endpoint or auth configuration is missing.

## Execution model

### Prototype mode
Use direct import first where available:
- keep `src/handsfree/ipfs_datasets_routers.py`
- add equivalent optional adapters for `ipfs_kit_py` and `ipfs_accelerate_py` if direct imports are needed
- allow CLI fallback only through explicit allowlists

Prototype mode is for:
- local development
- schema discovery
- rapid capability iteration
- regression comparison against MCP mode

### Production mode
Use MCP++ only:
- no arbitrary local execution
- no raw shell passthrough
- all calls routed through configured MCP endpoints
- strict auth, correlation ids, and audit traces

Production mode is for:
- remote execution boundaries
- operational control
- observability
- policy enforcement

## Command and planner integration

### Phase 1 command path
Use the existing `agent.delegate` intent to reach MCP providers first.

This requires:
- parser support for explicit providers such as `ipfs_datasets_mcp`
- router support for provider-specific spoken copy
- no large grammar expansion on day one

Example utterances:
- "Ask the IPFS datasets agent to find legal datasets"
- "Ask the IPFS kit agent to pin this CID"
- "Ask the IPFS accelerate agent to run the ingestion pipeline"

### Phase 2 command path
Add first-class IPFS intent families to the command system:
- `ipfs.search_dataset`
- `ipfs.publish`
- `ipfs.pin`
- `ipfs.provenance`
- `ipfs.accelerate`

These intents should compile to the same capability registry and tool runtime used by the planner.

### Planner path
The hierarchy from `13-nl-prompt-to-hierarchical-tools-ipfs-datasets.md` should target canonical capability ids, not raw MCP tool names.

Planner flow:
1. prompt -> intent candidates
2. intent candidates -> logical form
3. logical form -> theorem/proof validation
4. validated plan nodes -> capability ids
5. capability ids -> tool runtime
6. tool runtime -> direct or MCP execution

This keeps prompt interpretation stable while execution mode changes underneath it.

## Meta glasses UX implications
The Meta glasses integration should stay voice-first and short.

Required UX behaviors:
- concise confirmation before side effects
- short progress phrases during long-running MCP tasks
- "needs input" prompts that ask for one missing value at a time
- completion summaries that mention the outcome, not protocol jargon

Example spoken progress:
- "Dataset search is running."
- "I need the CID."
- "Publishing finished. I saved the CID to the task trace."

The glasses flow should not expose MCP request ids directly in audio, but those ids should be stored in traces for the app UI and debugging.

## Relation to Bluetooth/libp2p track
`12-p2p-bluetooth-libp2p.md` should remain a separate transport track, but there is a future integration point:

- MCP++ can initially run over normal backend-reachable transports only.
- Later, the Bluetooth/libp2p runtime can act as an edge transport or relay path for MCP-style requests when backend connectivity is constrained.

That should be treated as a later optimization, not part of the first MCP++ rollout. The first milestone should assume normal network reachability to MCP servers.

## Security requirements
- No direct execution from raw user utterances in production mode.
- All tool invocations must pass schema validation before MCP submission.
- Secrets must come from the existing secret-management path, not raw env logging.
- Traces must redact auth headers, tokens, and sensitive tool arguments.
- Destructive or externally visible actions must remain confirmation-gated.
- Production policy should be able to force `mcp_remote` and disable all direct fallbacks.

## Observability requirements
Add structured logs and metrics for:
- MCP handshake success and failure
- per-tool latency
- per-provider task success and failure
- retry counts
- `needs_input` frequency
- fallback usage in prototype mode

Store enough trace context to answer:
- which server handled the task
- which tool was called
- which request ids were issued
- what lifecycle transitions occurred

## Testing strategy

### Unit tests
- provider registry recognizes the three new MCP providers
- env/config parsing and startup validation
- MCP state -> HandsFree lifecycle mapping
- capability id -> tool mapping
- spoken summary formatting for IPFS actions

### Contract tests
- mocked MCP++ handshake
- mocked tool listing and capability resolution
- success, timeout, malformed response, and auth failure for each server family
- polling and `needs_input` transitions

### Integration tests
- `agent.delegate` using each MCP provider
- direct mode vs MCP mode parity for representative operations
- planner leaf-node execution against mocked MCP responses

### End-to-end tests
- transcript -> parse -> confirm -> delegate -> status summary
- transcript -> plan -> theorem check -> MCP tool execution -> spoken response

## Phased rollout

### Phase 0: protocol and capability discovery
- confirm the exact MCP++ handshake and tool invocation patterns exposed by the three target repos
- inventory tool names, schemas, long-running behavior, and auth expectations
- freeze a compatibility matrix in this repo

### Phase 1: MCP++ runtime foundation
- add shared client, config, models, and tracing modules
- add startup validation
- add mocked contract tests

### Phase 2: delegated provider integration
- implement `ipfs_datasets_mcp`, `ipfs_kit_mcp`, `ipfs_accelerate_mcp`
- register providers in `agent_providers.py`
- wire provider selection and status polling

### Phase 3: capability registry and direct/MCP unification
- add canonical capability ids
- add `execute_tool(...)` runtime
- bridge direct adapters and MCP adapters behind one contract

### Phase 4: command and Meta glasses integration
- add initial agent utterances and provider-specific spoken responses
- add first-class IPFS intents for the highest-value operations
- keep confirmation and short voice summaries

### Phase 5: planner and theorem-prover binding
- bind hierarchical plan leaves to capability ids
- enforce proof checks before MCP submission
- add clarification generation for missing parameters

### Phase 6: hardening and rollout
- shadow direct mode against MCP mode for parity
- disable direct fallback in production profile
- add dashboards, runbooks, and failure recovery docs

## PR breakdown
- `PR-009`: MCP++ runtime and delegated provider foundation
- `PR-010`: Meta glasses IPFS command path using the shared runtime
- `PR-011`: NL prompt -> hierarchical capability planning and theorem checks
- follow-up PR: first-class IPFS command intents and capability registry
- follow-up PR: observability, rollout flags, and production hardening

## Acceptance criteria
- The package can delegate tasks through all three MCP-backed providers by name.
- MCP-backed tasks persist normalized traces and lifecycle transitions.
- Direct and MCP execution paths share one capability contract.
- The Meta glasses flow can start, monitor, and summarize representative IPFS operations.
- The planner targets canonical capabilities and can execute them through MCP.
- Existing non-IPFS providers remain unaffected.

## Decisions to lock early
- exact MCP++ transport and authentication model used by each target server
- canonical HandsFree capability ids
- which tool families are exposed in Phase 1 versus deferred
- whether `ipfs_kit_py` and `ipfs_accelerate_py` also need direct-import prototype adapters
- what constitutes a long-running MCP task versus a synchronous tool call

## Recommended next implementation slice
Start with the delegated provider path, not the full planner.

The first coding slice should:
1. add a shared MCP++ client scaffold
2. add `ipfs_datasets_mcp` as the first provider
3. wire `AgentService.delegate()` to use it by explicit provider name
4. persist MCP trace metadata
5. add mocked contract tests

That sequence gives the repo a working end-to-end path quickly, and the planner and Meta glasses intent expansion can then build on a real execution backend instead of another placeholder.
