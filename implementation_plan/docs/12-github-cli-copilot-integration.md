# GitHub CLI + Copilot CLI Integration Improvement Plan

## Goals
- Integrate `gh` (GitHub CLI) and `gh copilot` workflows into HandsFree command execution.
- Enable AI/ML-assisted experiences (explain, summarize, generate, triage) through trusted CLI pathways.
- Keep the system safe-by-default with strict allowlists, policy gates, and auditable task traces.

## Why this matters
The current system already supports agent delegation and GitHub integrations, but its Copilot provider path is mostly stubbed. Adding a first-class CLI integration layer gives us:
- faster access to mature GitHub/Copilot capabilities without custom API wrappers for every workflow
- a practical bridge to AI/ML services for code understanding, issue triage, and suggested remediations
- consistent user experience for voice-driven and text-driven command execution

## Current baseline in this repository
- Agent providers exist in `src/handsfree/agent_providers.py` (`copilot`, `custom`, `mock`, `github_issue_dispatch`).
- Default provider selection exists in `src/handsfree/agents/service.py`.
- Command parsing and routing are already in place (`src/handsfree/commands/*`, `src/handsfree/api.py`).
- Fixture-driven testing patterns already exist (`tests/fixtures/*`, `tests/test_agent_*`, `tests/test_command_*`).

## Target architecture

### 1) CLI execution layer (new module boundary)
Create a dedicated boundary for all subprocess execution:
- `src/handsfree/cli/executor.py`
- `src/handsfree/cli/policy.py`
- `src/handsfree/cli/parsers.py`

Responsibilities:
- detect `gh` / `gh copilot` availability and versions
- execute only allowlisted command templates
- enforce timeouts, output limits, and exit-code handling
- normalize structured outputs for router/handlers

### 2) Capability adapters
Add focused adapters that translate product intents to CLI invocations:
- `GitHubCLIAdapter`: PR/issue/check/review operations best served by `gh`
- `CopilotCLIAdapter`: explain/suggest/fix/summarize flows via `gh copilot`

Each adapter should:
- return typed result objects (status, spoken summary, raw trace metadata)
- support fixture mode for deterministic tests when CLI is unavailable
- emit safe, redacted traces for audit/debug

### 3) Provider integration
Extend provider resolution so CLI-backed providers can be selected by policy:
- `copilot_cli` provider for AI/ML code assistance flows
- optional `github_cli` provider for operational GitHub actions

Provider selection order (proposed):
1. explicit provider in command entities
2. `HANDSFREE_AGENT_DEFAULT_PROVIDER`
3. `github_issue_dispatch` (if configured)
4. `copilot_cli` when `gh copilot` is available
5. existing `copilot` fallback path

### 4) Command and API surface updates
Extend command grammar and routing for CLI-backed intents:
- `ai.explain`
- `ai.suggest_fix`
- `ai.summarize_diff`
- `repo.actions.run` (guarded)

Add response contracts that include:
- short spoken summary
- optional structured `debug.tool_calls`
- explicit confirmation prompts for side-effect commands

## Security and governance requirements
- Allowlist-only command execution (no arbitrary shell pass-through).
- Token model must remain least-privilege (GitHub App preferred; PAT only for development).
- Sensitive output redaction before logs, notifications, and spoken responses.
- Confirmation gate for destructive or write operations.
- Trace every CLI call: command template ID, duration, exit status, redaction outcome.

## Implementation roadmap

### Phase 0 — Discovery and guardrails
- inventory required `gh` and `gh copilot` commands by user intent
- define command allowlist and redaction patterns
- finalize env/config contract in `CONFIGURATION.md`

### Phase 1 — Core CLI platform
- implement executor/policy/parser modules
- add health checks for CLI capability detection
- add fixture fallbacks for local/CI environments without CLI

### Phase 2 — GitHub CLI operational workflows
- wire read-heavy intents first (status, list, summarize)
- add guarded write flows (comment, review request) behind confirmation
- validate behavior parity against existing GitHub provider paths

### Phase 3 — Copilot CLI AI/ML workflows
- integrate `gh copilot explain` and suggestion-style workflows
- map outputs to concise spoken responses + optional debug payloads
- add profile-aware verbosity controls (workout/kitchen/commute)

### Phase 4 — Quality gates
- unit tests for command policy and parser normalization
- integration tests for provider selection and router behavior
- fixture replay tests for representative `gh` and `gh copilot` outputs
- regression tests for existing command paths

### Phase 5 — Rollout and observability
- staged rollout via feature flags
- telemetry for latency, success rate, and fallback frequency
- rollback toggles to force non-CLI provider path

## Testing strategy
- **Unit tests**: executor timeout handling, allowlist matching, output parsing.
- **Integration tests**: intent -> router -> provider -> response pipeline.
- **Fixture tests**: deterministic CLI stdout/stderr replay using JSON/text fixtures.
- **Safety tests**: destructive command requires confirmation; secret redaction always applied.
- **Backward compatibility tests**: existing non-CLI provider behavior unchanged when CLI is disabled.

## Documentation updates required as phases land
- `CONFIGURATION.md`: env vars for CLI enablement, timeout, and provider defaults.
- `spec/command_grammar.md`: new AI/ML intent phrases and disambiguation.
- `docs/agent-runner-setup.md`: CLI-enabled runner setup and auth prerequisites.
- `DOCUMENTATION_INDEX.md`: references to finalized CLI integration docs.

## Success criteria
- Users can trigger AI/ML assistance flows through voice/text commands using `gh copilot`.
- GitHub operational commands can use `gh` where it improves reliability or speed.
- All new flows pass tests in fixture and non-fixture modes.
- Security constraints (allowlist, redaction, confirmations, traceability) are enforced by default.

## Risks and mitigations
- **CLI availability variance**: mitigate with capability checks + fixture fallback.
- **Command output drift**: mitigate with parser versioning and fixture coverage.
- **Privilege overreach**: mitigate with scoped tokens and policy-layer confirmation requirements.
- **Latency for spoken UX**: mitigate with short summaries and async follow-up details.
# GitHub CLI + Copilot CLI + Endomorphosis IPFS Stack Integration Plan

## Objective
Integrate `gh`, `gh copilot`, `endomorphosis/ipfs_datasets_py`, `endomorphosis/ipfs_accelerate_py`, and `endomorphosis/ipfs_kit_py` into one coherent AI/ML execution layer for HandsFree. The target state is a system where:
- GitHub context is gathered through `gh` or the existing GitHub provider
- Copilot CLI provides draft AI assistance for review, failure triage, and code understanding
- `llm_router`, `embeddings_router`, and `ipfs_router` from `ipfs_datasets_py` provide local or remote AI/ML primitives
- `ipfs_accelerate_py` provides acceleration-aware backend/runtime selection where direct router calls are too static
- `ipfs_kit_py` provides richer IPFS content lifecycle and packaging helpers beyond the narrow router seam
- routing between those backends is explicit, policy-controlled, fixture-testable, and observable

This plan extends, rather than replaces, the work already captured in:
- `implementation_plan/docs/11-devloop-vscode.md`
- `implementation_plan/docs/14-mcp-plus-plus-ipfs-server-integration.md`

## Why this matters
The repository already has three partially overlapping AI paths:
- GitHub/Copilot CLI for code-hosting and Copilot assistance
- `ipfs_datasets_py` direct router adapters for LLM, embeddings, and IPFS functions
- MCP-backed IPFS providers for delegated background tasks

To reach the target stack you described, this should be treated as a five-family backend model:
- GitHub CLI
- Copilot CLI
- `ipfs_datasets_py`
- `ipfs_accelerate_py`
- `ipfs_kit_py`

What is missing is one plan that defines how these fit together under a single execution model.

Without that, the project risks:
- duplicated orchestration logic
- separate prompt and tracing models per backend
- inconsistent safety rules between GitHub CLI and IPFS-backed AI calls
- fragmented fixture/test coverage

## Current state in this repo

### Implemented summary
The following parts of the integration are already implemented in the codebase:
- shared CLI execution and allowlisting for `gh` and `gh copilot`
- shared GitHub action execution for read and guarded write flows
- shared AI capability routing across:
  - Copilot CLI
  - `llm_router`
  - `embeddings_router`
  - `ipfs_router`
- command-layer AI intents for:
  - PR explanation
  - diff summarization
  - failure explanation
  - augmented PR summary
  - accelerated generate-and-store
  - stored-output CID reads
- typed AI API request/response models
- typed AI API endpoints for the current workflow families
- optional IPFS persistence for composite AI outputs
- CID-based readback for stored AI outputs
- indexed persisted AI history lookup via:
  - `migrations/013_add_ai_history_index.sql`
  - `src/handsfree/db/ai_history_index.py`
  - `src/handsfree/ai/history.py`
- idempotency and audit logging for the AI execution endpoint
- OpenAPI coverage for the implemented AI routes, schemas, and examples

What remains primarily falls into three categories:
- broader direct API test coverage once local optional dependencies are available
- further planner/delegation integration on top of the shared AI contract
- deeper retrieval, indexing, and policy controls for IPFS-backed AI workflows

### Existing GitHub CLI / Copilot CLI integration
The repository already contains a meaningful scaffold:
- `src/handsfree/cli/executor.py`
- `src/handsfree/cli/policy.py`
- `src/handsfree/cli/parsers.py`
- `src/handsfree/cli/adapters.py`
- `src/handsfree/actions/service.py`
- `src/handsfree/github/execution.py`
- `src/handsfree/commands/router.py`
- `src/handsfree/commands/intent_parser.py`

Implemented capabilities already include:
- fixture-backed `gh pr view`
- fixture-backed `gh copilot explain`
- guarded write flows for reviewer request, comment, rerun, and merge
- AI intents for:
  - `ai.explain_pr`
  - `ai.summarize_diff`
  - `ai.explain_failure`
  - `ai.rag_summary`
  - `ai.read_cid`
- session-context reuse across PR-centric AI commands
- shared AI capability routing via:
  - `src/handsfree/ai/models.py`
  - `src/handsfree/ai/capabilities.py`
  - `src/handsfree/ai/serialization.py`
- typed AI API execution via:
  - `POST /v1/ai/execute`
  - `POST /v1/ai/copilot/explain-pr`
  - `POST /v1/ai/copilot/summarize-diff`
  - `POST /v1/ai/copilot/explain-failure`
  - `POST /v1/ai/rag-summary`
  - `POST /v1/ai/failure-rag-explain`
  - `POST /v1/ai/read-stored-output`
- typed request models for:
  - Copilot PR explain
  - Copilot diff summary
  - Copilot failure explain
  - PR RAG summary
  - failure RAG explain
  - stored-output CID read
- typed response models for:
  - Copilot outputs
  - augmented PR summaries
  - augmented failure analysis
  - stored-output reads
- optional IPFS persistence and CID readback for composite AI outputs

### Existing IPFS datasets router integration
The repository also already contains direct adapter seams for `ipfs_datasets_py`:
- `src/handsfree/ipfs_datasets_routers.py`

That module provides lazy, optional adapters for:
- `ipfs_datasets_py.embeddings_router`
- `ipfs_datasets_py.ipfs_backend_router`
- `ipfs_datasets_py.llm_router`

Current behavior:
- if `ipfs_datasets_py` is installed, adapters delegate directly to router modules
- if it is not installed, safe fallback stubs raise `NotImplementedError`

### Validated upstream package surfaces
The upstream Endomorphosis repositories are now present in this repo as git submodules under:
- `external/ipfs_datasets`
- `external/ipfs_accelerate`
- `external/ipfs_kit`

Those checkouts were used to validate the real package/import and CLI surfaces before extending adapter contracts.

Validated findings:
- `external/ipfs_datasets/pyproject.toml`
  - package name: `ipfs_datasets_py`
  - import family: `ipfs_datasets_py.*`
  - CLI entry is currently script-centric via `external/ipfs_datasets/ipfs_datasets_cli.py`
  - MCP surface is real and lives under `external/ipfs_datasets/ipfs_datasets_py/mcp_server`
- `external/ipfs_accelerate/pyproject.toml`
  - package name: `ipfs_accelerate_py`
  - import family: `ipfs_accelerate_py.*`
  - published CLI scripts:
    - `ipfs_accelerate = ipfs_accelerate_py.ai_inference_cli:main`
    - `ipfs-accelerate = ipfs_accelerate_py.cli_entry:main`
  - MCP surface is real and lives under `external/ipfs_accelerate/ipfs_accelerate_py/mcp_server`
- `external/ipfs_kit/pyproject.toml`
  - package name: `ipfs_kit_py`
  - import family: `ipfs_kit_py.*`
  - published CLI script:
    - `ipfs-kit = ipfs_kit_py.cli:sync_main`
  - MCP compatibility shims live under `external/ipfs_kit/mcp`
  - canonical package MCP implementation is exposed from `external/ipfs_kit/ipfs_kit_py/mcp/*`

Planning implications:
- `ipfs_datasets_py` should continue to be treated as a direct-import router dependency first, not a CLI-first dependency.
- `ipfs_accelerate_py` should be modeled as both:
  - a direct-import acceleration/runtime adapter
  - an optional CLI surface through `ipfs_accelerate` or `ipfs-accelerate`
- `ipfs_kit_py` should be modeled as both:
  - a direct-import content lifecycle adapter
  - an operational CLI/MCP host surface through `ipfs-kit` and `ipfs_kit_py.mcp.*`
- adapter contracts in HandsFree should prefer the canonical package import paths above, and treat top-level compatibility shims as secondary.

### GitHub auth token fallback
GitHub-backed live flows now support a dev fallback to the local GitHub CLI auth session:
- GitHub App installation token remains the first live source when configured
- `GITHUB_TOKEN` remains the first simple fallback
- `gh auth token` is now the next fallback when live mode is explicitly requested

Current rule:
- the `gh` token fallback is only used when live mode is explicitly requested through:
  - `HANDS_FREE_GITHUB_MODE=live`, or
  - `GITHUB_LIVE_MODE=true|1|yes`
- it does not silently enable live GitHub mode in default fixture-oriented test paths

This keeps local developer ergonomics high without changing the project’s default safety model.

Known upstream issue discovered during validation:
- `external/ipfs_accelerate` currently has a broken nested submodule reference for recursive init:
  - submodule path: `external/ipfs_accelerate/ipfs_datasets_py`
  - failure: missing URL in that repo's `.gitmodules`
- This does not block inspection of the checked-out repo itself, but it means recursive submodule bootstrap should not be assumed to work without an upstream fix or local patching step.
- behavior is covered by `tests/test_ipfs_datasets_routers.py`

### Planned `ipfs_accelerate_py` integration
The repository does not yet expose `ipfs_accelerate_py` as a first-class adapter seam.

Recommended role in this project:
- choose accelerated/local/remote execution profiles when `llm_router` and `embeddings_router` alone are too narrow
- provide a future bridge for planner-controlled backend choice where latency and cost matter
- stay behind the same typed AI capability contract as the rest of the stack

Recommended code boundary:
- `src/handsfree/ipfs_accelerate_adapters.py`

Candidate capability families:
- `ipfs.accelerate.generate`
- `ipfs.accelerate.embed`
- `ipfs.accelerate.rank`

### Planned `ipfs_kit_py` integration
The repository also does not yet expose `ipfs_kit_py` as a first-class adapter seam.

Recommended role in this project:
- manage richer IPFS lifecycle operations than the current router seam covers
- support pin/unpin/resolve/package flows without pushing those concerns into the CLI or planner layers
- package persisted analysis corpora and other reusable content bundles

Recommended code boundary:
- `src/handsfree/ipfs_kit_adapters.py`

Candidate capability families:
- `ipfs.kit.pin`
- `ipfs.kit.unpin`
- `ipfs.kit.resolve`
- `ipfs.kit.package_dataset`

### Existing MCP-based IPFS provider path
The repo also has a delegated task path via MCP-related modules:
- `src/handsfree/mcp/`
- `src/handsfree/agent_providers.py`
- `src/handsfree/agents/service.py`

This means there are already two IPFS-related execution styles in the codebase:
- direct router import for synchronous local operations
- MCP-backed remote provider execution for delegated jobs

## Core design decision
Treat `gh`, `gh copilot`, `llm_router`, `embeddings_router`, `ipfs_router`, `ipfs_accelerate_py`, and `ipfs_kit_py` as backends behind one shared capability-routing layer.

Do not let each integration invent its own execution path.

The system should decide per capability whether to use:
- GitHub REST provider
- GitHub CLI
- Copilot CLI
- `ipfs_datasets_py` direct routers
- `ipfs_accelerate_py` accelerated execution
- `ipfs_kit_py` content/node helpers
- MCP-backed IPFS providers

That selection must be driven by a single routing contract, not scattered handler logic.

## Current implemented AI API surface

### Generic execution endpoint
- `POST /v1/ai/execute`
- accepts:
  - raw `capability_id`
  - higher-level `workflow`
  - typed context
  - typed option groups for generation, embeddings, and IPFS
- provides:
  - typed response models for the major Copilot and composite workflows
  - request idempotency
  - audit logging
  - normalized workflow/check failure context

### Typed workflow endpoints
Thin adapter endpoints now exist for the main workflow shapes:
- `POST /v1/ai/copilot/explain-pr`
- `POST /v1/ai/copilot/summarize-diff`
- `POST /v1/ai/copilot/explain-failure`
- `POST /v1/ai/rag-summary`
- `POST /v1/ai/accelerated-rag-summary`
- `POST /v1/ai/failure-rag-explain`
- `POST /v1/ai/accelerated-failure-explain`
- `POST /v1/ai/find-similar-failures`
- `POST /v1/ai/read-stored-output`
- `POST /v1/ai/accelerate-generate-and-store`

These endpoints are intentionally shallow. They convert typed workflow requests into the shared `AICapabilityExecuteRequest` contract and then delegate to the same execution path used by the generic endpoint.

### When to use generic vs typed endpoints
- Use typed endpoints when the client already knows the workflow it wants.
- Use `POST /v1/ai/execute` when the client needs low-level capability control or wants to dispatch by `capability_id`.
- Prefer typed endpoints for external consumers because they provide narrower request schemas and clearer validation failures.
- Prefer the generic endpoint for internal orchestration layers, planners, or experiments that may target multiple capabilities dynamically.

### Typed request models
The following typed request models now exist in `src/handsfree/models.py`:
- `AICopilotExplainPRExecuteRequest`
- `AICopilotSummarizeDiffExecuteRequest`
- `AICopilotExplainFailureExecuteRequest`
- `AIPRRAGSummaryExecuteRequest`
- `AIAcceleratedPRSummaryExecuteRequest`
- `AIFailureRAGExplainExecuteRequest`
- `AIAcceleratedFailureExplainExecuteRequest`
- `AIFindSimilarFailuresExecuteRequest`
- `AIStoredOutputReadExecuteRequest`
- `AIAccelerateGenerateAndStoreExecuteRequest`

This is the correct direction for client integrations. External callers should prefer these workflow-specific shapes where possible, and use the generic execution contract only when a lower-level capability call is actually needed.

### Typed response models
The following response types are already implemented:
- `AICopilotOutput`
- `AIRAGSummaryOutput`
- `AIFailureAnalysisOutput`
- `AISimilarFailuresOutput`
- `AIStoredOutputRead`
- `AIAcceleratedStoredOutput`

Each typed output includes:
- `schema_name`
- `schema_version`
- normalized workflow output fields

That schema versioning is important because persisted IPFS payloads and external API consumers will need a stable compatibility signal as the AI contract evolves.

API responses now also expose `policy_resolution` so clients can see when a workflow alias was remapped by backend policy. The current fields are:
- `requested_workflow`
- `resolved_workflow`
- `requested_capability_id`
- `resolved_capability_id`
- `policy_applied`

Command-router debug payloads now expose the same `policy_resolution` shape for summary and failure intents so command traces and API traces stay aligned.
Delegated PR-oriented agent task traces now expose the same `policy_resolution` shape as well.
There is now also a small admin/debug report route:
- `GET /v1/admin/ai/backend-policy`
- `GET /v1/admin/ai/backend-policy/history`
- `GET /v1/admin/ai/backend-policy/snapshots`

That report exposes:
- the currently resolved summary and failure backend policy
- the current non-secret GitHub auth source for live-mode requests:
  - `github_app`
  - `env_token`
  - `gh_cli`
  - `fixtures`
- capability-usage totals split into:
  - `remapped_capability_counts`
  - `direct_capability_counts`
- a compact `top_capabilities` summary for:
  - `overall`
  - `remapped`
  - `direct`
- a compact `top_remaps` summary for the busiest workflow remap pairs
- recent `ai.execute.*` action counts
- per-workflow remap totals by requested and resolved workflow
- recent policy remap counts derived from audit logs
- fixed recency buckets:
  - `last_hour`
  - `last_24_hours`

The history route exposes:
- bucketed `ai.execute.*` activity over a caller-selected recent window
- bucketed `policy_applied_count`
- bucketed remap-pair counts
- the same current non-secret policy/auth context used by the snapshot route

The snapshots route exposes:
- persisted point-in-time backend-policy snapshots
- current backend defaults and GitHub auth source at snapshot time
- snapshot-level remap counts, top capabilities, and top remaps

Current behavior:
- `GET /v1/admin/ai/backend-policy` now stores a point-in-time snapshot opportunistically by default
- `GET /v1/admin/ai/backend-policy?capture=false` skips snapshot persistence for read-only inspection
- the snapshots route lists those stored observations newest-first
- snapshot persistence now supports best-effort retention controls:
  - `HANDSFREE_AI_POLICY_SNAPSHOT_RETENTION_DAYS`
  - `HANDSFREE_AI_POLICY_SNAPSHOT_MAX_RECORDS_PER_USER`
  - `HANDSFREE_AI_POLICY_SNAPSHOT_MIN_INTERVAL_SECONDS`

### PR summary backend selection
The command-layer PR summary flow now supports backend selection without requiring separate user-facing command families.

Current behavior:
- `ai.rag_summary` defaults to `github.pr.rag_summary`
- if `HANDSFREE_AI_DEFAULT_SUMMARY_BACKEND=accelerated`, `ai.rag_summary` switches to `github.pr.accelerated_summary`
- phrase-level override is also supported, for example:
  - `use acceleration for augmented summary for pr 123`
  - `use acceleration for augmented summary for pr 124 to ipfs`
- the explicit `ai.accelerated_rag_summary` command surface still exists as a direct override

This keeps the voice/text contract simple while still allowing backend rollout and comparison.

The typed API route now supports the same selection pattern:
- `POST /v1/ai/rag-summary` accepts optional `summary_backend`
- `summary_backend=accelerated` dispatches to `github.pr.accelerated_summary`
- the dedicated `POST /v1/ai/accelerated-rag-summary` route remains available as an explicit workflow-specific entry point

The same pattern now exists for failure analysis:
- `POST /v1/ai/failure-rag-explain` accepts optional `failure_backend`
- `failure_backend=accelerated` dispatches to `github.check.accelerated_failure_explain`
- the dedicated `POST /v1/ai/accelerated-failure-explain` route remains available as an explicit workflow-specific entry point

Command-level failure analysis now also supports phrase-level backend override on the standard intent:
- `ai.explain_failure` now follows `HANDSFREE_AI_DEFAULT_FAILURE_BACKEND` by default
- explicit phrase override is supported, for example:
  - `use acceleration for explain failure for pr 321`
  - `use acceleration for explain workflow CI Linux for pr 322`
  - `use acceleration for explain failure for pr 323 to ipfs`
- the explicit `ai.accelerated_explain_failure` command surface still exists as a direct override

Preferred backend policy env vars:
- `HANDSFREE_AI_DEFAULT_SUMMARY_BACKEND`
  - supported values: `default`, `accelerated`
- `HANDSFREE_AI_DEFAULT_FAILURE_BACKEND`
  - supported values: `default`, `accelerated`, `composite`

These policy defaults now apply to:
- command-layer backend selection
- typed workflow endpoints that use default workflow aliases
- generic `POST /v1/ai/execute` calls when they supply `workflow`
- delegated PR-oriented agent tasks that resolve through the shared AI capability contract

Explicit low-level `capability_id` calls still bypass policy remapping by design.

Legacy compatibility env vars still work as fallback:
- `HANDSFREE_AI_ACCELERATED_SUMMARY_ENABLED=true`
- `HANDSFREE_AI_COMPOSITE_FAILURE_ENABLED=true`

### Endpoint matrix

| Route | Primary request model | Workflow | Typed output | Required context/input |
| --- | --- | --- | --- | --- |
| `POST /v1/ai/execute` | `AICapabilityExecuteRequest` | caller-provided | varies by capability | depends on `workflow` or `capability_id` |
| `POST /v1/ai/copilot/explain-pr` | `AICopilotExplainPRExecuteRequest` | `copilot_explain_pr` | `AICopilotOutput` | `pr_number` |
| `POST /v1/ai/copilot/summarize-diff` | `AICopilotSummarizeDiffExecuteRequest` | `copilot_summarize_diff` | `AICopilotOutput` | `pr_number` |
| `POST /v1/ai/copilot/explain-failure` | `AICopilotExplainFailureExecuteRequest` | `copilot_explain_failure` | `AICopilotOutput` | `pr_number`; optional `workflow_name` or `check_name` |
| `POST /v1/ai/rag-summary` | `AIPRRAGSummaryExecuteRequest` | `pr_rag_summary` or `accelerated_pr_summary` via `summary_backend` | `AIRAGSummaryOutput` | `pr_number`; optional `summary_backend=accelerated` |
| `POST /v1/ai/accelerated-rag-summary` | `AIAcceleratedPRSummaryExecuteRequest` | `accelerated_pr_summary` | `AIRAGSummaryOutput` | `pr_number`; optional generation/embedding options |
| `POST /v1/ai/failure-rag-explain` | `AIFailureRAGExplainExecuteRequest` | `failure_rag_explain` or `accelerated_failure_explain` via `failure_backend` | `AIFailureAnalysisOutput` | `pr_number`; optional `workflow_name` or `check_name`; optional `failure_backend=accelerated`; optional explicit `history_cids`; otherwise recent matching persisted failure-analysis CIDs may be auto-discovered |
| `POST /v1/ai/accelerated-failure-explain` | `AIAcceleratedFailureExplainExecuteRequest` | `accelerated_failure_explain` | `AIFailureAnalysisOutput` | `pr_number`; optional `workflow_name` or `check_name`; optional explicit `history_cids`; otherwise recent matching persisted failure-analysis CIDs may be auto-discovered |
| `POST /v1/ai/find-similar-failures` | `AIFindSimilarFailuresExecuteRequest` | `find_similar_failures` | `AISimilarFailuresOutput` | `pr_number`; optional `history_candidates`; optional explicit `history_cids`; otherwise recent matching persisted failure-analysis CIDs may be auto-discovered; optional `workflow_name` or `check_name` |
| `POST /v1/ai/read-stored-output` | `AIStoredOutputReadExecuteRequest` | `read_stored_output` | `AIStoredOutputRead` | `cid` |
| `POST /v1/ai/accelerate-generate-and-store` | `AIAccelerateGenerateAndStoreExecuteRequest` | `accelerate_generate_and_store` | `AIAcceleratedStoredOutput` | `prompt`; optional generation/IPFS options; optional `kit_pin`; optional metadata |

### Automatic history fallback
For `POST /v1/ai/failure-rag-explain`, `POST /v1/ai/accelerated-failure-explain`, and `POST /v1/ai/find-similar-failures`, callers can still provide `history_cids` explicitly.

If `history_cids` are omitted and the request has enough context, the runtime now auto-discovers recent persisted failure-analysis outputs from `ai_history_index` and only falls back to older `action_logs` records when the index has no match. Discovery currently filters on:
- the same user
- the same repo
- the same workflow/check target when present
- a different PR than the current request

This keeps the request contract explicit while reducing the need for clients to carry prior CID state themselves, while also moving steady-state lookups off the audit log table.

### Validation and failure matrix

All of these cases should currently produce `400 invalid_request` from the API layer.

| Request shape | Affected route(s) | Current validation message |
| --- | --- | --- |
| Missing `pr_number` for PR-based workflows | `POST /v1/ai/execute`, `POST /v1/ai/copilot/explain-pr`, `POST /v1/ai/copilot/summarize-diff`, `POST /v1/ai/copilot/explain-failure`, `POST /v1/ai/rag-summary`, `POST /v1/ai/accelerated-rag-summary`, `POST /v1/ai/failure-rag-explain`, `POST /v1/ai/accelerated-failure-explain`, `POST /v1/ai/find-similar-failures` | `<capability_id> requires context.pr_number` |
| Missing `cid` for stored-output reads | `POST /v1/ai/execute`, `POST /v1/ai/read-stored-output` | `ipfs.content.read_ai_output requires inputs.cid or options.cid` |
| Missing `prompt` for accelerated generate/store | `POST /v1/ai/execute`, `POST /v1/ai/accelerate-generate-and-store` | `ipfs.accelerate.generate_and_store requires inputs.prompt or options.prompt` |
| `failure_target_type` without `failure_target` | generic execute and typed failure routes | `failure_target and failure_target_type must be provided together` |
| `workflow_name` and `check_name` both present in typed failure requests | `POST /v1/ai/copilot/explain-failure`, `POST /v1/ai/failure-rag-explain`, `POST /v1/ai/accelerated-failure-explain` | `workflow_name and check_name are mutually exclusive` |
| `workflow_name` conflicts with explicit `failure_target` | `POST /v1/ai/execute` for failure workflows | `workflow_name conflicts with context.failure_target` |
| `workflow_name` conflicts with explicit `failure_target_type` | `POST /v1/ai/execute` for failure workflows | `workflow_name conflicts with context.failure_target_type` |
| `check_name` conflicts with explicit `failure_target` | `POST /v1/ai/execute` for failure workflows | `check_name conflicts with context.failure_target` |
| `check_name` conflicts with explicit `failure_target_type` | `POST /v1/ai/execute` for failure workflows | `check_name conflicts with context.failure_target_type` |
| Missing both `workflow` and `capability_id` on the generic endpoint | `POST /v1/ai/execute` | `Either capability_id or workflow must be provided` |

### OpenAPI update checklist

`spec/openapi.yaml` should remain synchronized with the implemented AI execution surface. Keep the following coverage in place as the AI API evolves:

#### Paths that must exist
- `POST /v1/ai/execute`
- `POST /v1/ai/copilot/explain-pr`
- `POST /v1/ai/copilot/summarize-diff`
- `POST /v1/ai/copilot/explain-failure`
- `POST /v1/ai/rag-summary`
- `POST /v1/ai/accelerated-rag-summary`
- `POST /v1/ai/failure-rag-explain`
- `POST /v1/ai/accelerated-failure-explain`
- `POST /v1/ai/find-similar-failures`
- `POST /v1/ai/read-stored-output`
- `POST /v1/ai/accelerate-generate-and-store`

#### Request schemas that must exist
- `AICapabilityExecuteRequest`
- `AICapabilityContext`
- `AIGenerationOptions`
- `AIEmbeddingOptions`
- `AIIPFSOptions`
- `AICopilotExplainPRExecuteRequest`
- `AICopilotSummarizeDiffExecuteRequest`
- `AICopilotExplainFailureExecuteRequest`
- `AIPRRAGSummaryExecuteRequest`
- `AIAcceleratedPRSummaryExecuteRequest`
- `AIFailureRAGExplainExecuteRequest`
- `AIAcceleratedFailureExplainExecuteRequest`
- `AIFindSimilarFailuresExecuteRequest`
- `AIStoredOutputReadExecuteRequest`
- `AIAccelerateGenerateAndStoreExecuteRequest`

#### Response schemas that must exist
- `AICapabilityExecuteResponse`
- `AICopilotOutput`
- `AIRAGSummaryOutput`
- `AIFailureAnalysisOutput`
- `AISimilarFailuresOutput`
- `AIStoredOutputRead`

#### Enums and shared schema details that must exist
- `AIWorkflow`
- typed `workflow` enum values:
  - `copilot_explain_pr`
  - `copilot_summarize_diff`
  - `copilot_explain_failure`
  - `pr_rag_summary`
  - `failure_rag_explain`
  - `find_similar_failures`
  - `read_stored_output`
- `typed_output` should be modeled as a union/`oneOf` over:
  - `AICopilotOutput`
  - `AIRAGSummaryOutput`
  - `AIFailureAnalysisOutput`
  - `AISimilarFailuresOutput`
  - `AIStoredOutputRead`

#### Error response behavior to document
- generic invalid AI requests currently return:
  - HTTP `400`
  - `error=invalid_request`
  - validation message in `message`
- the OpenAPI spec should include examples for:
  - missing `pr_number`
  - missing `cid`
  - conflicting `workflow_name` and `check_name`
  - missing `workflow` and `capability_id` on `POST /v1/ai/execute`

#### Examples to carry in the spec
- one generic `POST /v1/ai/execute` example using `workflow=pr_rag_summary`
- one Copilot read-only example
- one composite failure-analysis example
- one CID read example

#### Follow-up spec work
- decide whether typed endpoints should each get their own operation-specific response examples, or whether they should all share a common `AICapabilityExecuteResponse` example set
- decide whether `capability_id` should remain open-ended in the spec or be documented as an implementation-defined string rather than a closed enum

### Example requests and responses

#### Generic execution example

Request:

```json
{
  "workflow": "pr_rag_summary",
  "profile": "default",
  "context": {
    "repo": "openai/example",
    "pr_number": 123
  },
  "persist_output": true,
  "generation": {
    "model": "llama3",
    "temperature": 0.2,
    "max_tokens": 256
  },
  "embeddings": {
    "model": "minilm",
    "dimensions": 384
  },
  "ipfs": {
    "pin": true
  }
}
```

Representative response:

```json
{
  "ok": true,
  "capability_id": "github.pr.rag_summary",
  "workflow": "pr_rag_summary",
  "execution_mode": "orchestrated",
  "output_type": "rag_summary",
  "typed_output": {
    "schema_name": "rag_summary",
    "schema_version": 1,
    "headline": "Augmented PR summary",
    "summary": "This PR consolidates AI routing and typed workflow execution.",
    "spoken_text": "PR 123 centralizes AI capability routing and adds typed workflow endpoints.",
    "repo": "openai/example",
    "pr_number": 123,
    "source_summary": "PR summary from GitHub context",
    "embedding_dimensions": 384,
    "ipfs_cid": "bafyexample123"
  },
  "output": {
    "headline": "Augmented PR summary",
    "summary": "This PR consolidates AI routing and typed workflow execution.",
    "spoken_text": "PR 123 centralizes AI capability routing and adds typed workflow endpoints.",
    "repo": "openai/example",
    "pr_number": 123,
    "source_summary": "PR summary from GitHub context",
    "embedding_dimensions": 384,
    "ipfs_cid": "bafyexample123"
  },
  "trace": {
    "capability_id": "github.pr.rag_summary"
  }
}
```

#### Typed Copilot explain PR example

Endpoint:
- `POST /v1/ai/copilot/explain-pr`

Request:

```json
{
  "pr_number": 123,
  "repo": "openai/example",
  "profile": "default"
}
```

Representative response:

```json
{
  "ok": true,
  "capability_id": "copilot.pr.explain",
  "workflow": "copilot_explain_pr",
  "execution_mode": "fixture",
  "output_type": "copilot_output",
  "typed_output": {
    "schema_name": "copilot_output",
    "schema_version": 1,
    "headline": "Copilot explanation",
    "summary": "This PR refactors AI execution into one shared contract.",
    "spoken_text": "PR 123 moves Copilot and IPFS-backed AI execution onto one shared path."
  },
  "output": {
    "headline": "Copilot explanation",
    "summary": "This PR refactors AI execution into one shared contract.",
    "spoken_text": "PR 123 moves Copilot and IPFS-backed AI execution onto one shared path."
  },
  "trace": {
    "command_id": "gh.copilot.explain"
  }
}
```

#### Typed Copilot summarize diff example

Endpoint:
- `POST /v1/ai/copilot/summarize-diff`

Request:

```json
{
  "pr_number": 123,
  "repo": "openai/example",
  "profile": "default"
}
```

Representative response:

```json
{
  "ok": true,
  "capability_id": "copilot.pr.diff_summary",
  "workflow": "copilot_summarize_diff",
  "execution_mode": "fixture",
  "output_type": "copilot_output",
  "typed_output": {
    "schema_name": "copilot_output",
    "schema_version": 1,
    "headline": "Copilot diff summary",
    "summary": "The diff primarily unifies AI request routing and typed API models.",
    "spoken_text": "This diff mostly consolidates AI execution and adds typed workflow contracts."
  },
  "output": {
    "headline": "Copilot diff summary",
    "summary": "The diff primarily unifies AI request routing and typed API models.",
    "spoken_text": "This diff mostly consolidates AI execution and adds typed workflow contracts."
  },
  "trace": {
    "command_id": "gh.copilot.summarize_diff"
  }
}
```

#### Typed Copilot explain failure example

Endpoint:
- `POST /v1/ai/copilot/explain-failure`

Request:

```json
{
  "pr_number": 123,
  "repo": "openai/example",
  "workflow_name": "CI Linux",
  "profile": "default"
}
```

Representative response:

```json
{
  "ok": true,
  "capability_id": "copilot.pr.failure_explain",
  "workflow": "copilot_explain_failure",
  "execution_mode": "fixture",
  "output_type": "copilot_output",
  "typed_output": {
    "schema_name": "copilot_output",
    "schema_version": 1,
    "headline": "Failure analysis",
    "summary": "CI Linux is failing while preparing the environment.",
    "spoken_text": "Copilot thinks the CI Linux workflow is failing during environment setup."
  },
  "output": {
    "headline": "Failure analysis",
    "summary": "CI Linux is failing while preparing the environment.",
    "spoken_text": "Copilot thinks the CI Linux workflow is failing during environment setup."
  },
  "trace": {
    "command_id": "gh.copilot.explain_failure"
  }
}
```

#### Typed PR RAG summary example

Endpoint:
- `POST /v1/ai/rag-summary`

Request:

```json
{
  "pr_number": 123,
  "repo": "openai/example",
  "profile": "default",
  "persist_output": true,
  "embeddings": {
    "dimensions": 384
  },
  "ipfs": {
    "pin": true
  }
}
```

Representative response:

```json
{
  "ok": true,
  "capability_id": "github.pr.rag_summary",
  "workflow": "pr_rag_summary",
  "execution_mode": "orchestrated",
  "output_type": "rag_summary",
  "typed_output": {
    "schema_name": "rag_summary",
    "schema_version": 1,
    "headline": "Augmented PR summary",
    "summary": "This PR unifies AI workflow execution and typed endpoint coverage.",
    "spoken_text": "The PR adds typed AI workflow endpoints and centralizes AI capability routing.",
    "repo": "openai/example",
    "pr_number": 123,
    "source_summary": "PR summary from GitHub context",
    "embedding_dimensions": 384,
    "ipfs_cid": "bafyexample123"
  },
  "output": {
    "headline": "Augmented PR summary",
    "summary": "This PR unifies AI workflow execution and typed endpoint coverage.",
    "spoken_text": "The PR adds typed AI workflow endpoints and centralizes AI capability routing.",
    "repo": "openai/example",
    "pr_number": 123,
    "source_summary": "PR summary from GitHub context",
    "embedding_dimensions": 384,
    "ipfs_cid": "bafyexample123"
  },
  "trace": {
    "capability_id": "github.pr.rag_summary"
  }
}
```

#### Typed failure analysis example

Endpoint:
- `POST /v1/ai/failure-rag-explain`

Request:

```json
{
  "pr_number": 123,
  "repo": "openai/example",
  "workflow_name": "CI Linux",
  "profile": "default",
  "generation": {
    "model": "llama3"
  },
  "embeddings": {
    "dimensions": 384
  }
}
```

Representative response:

```json
{
  "ok": true,
  "capability_id": "github.check.failure_rag_explain",
  "workflow": "failure_rag_explain",
  "execution_mode": "orchestrated",
  "output_type": "failure_analysis",
  "typed_output": {
    "schema_name": "failure_analysis",
    "schema_version": 1,
    "headline": "Failure analysis",
    "summary": "CI Linux is failing during dependency setup.",
    "spoken_text": "The CI Linux workflow is failing during setup before the test phase starts.",
    "repo": "openai/example",
    "pr_number": 123,
    "failure_target": "CI Linux",
    "failure_target_type": "workflow",
    "checks_context": "setup-python failed after dependency install",
    "embedding_dimensions": 384,
    "ipfs_cid": null
  },
  "output": {
    "headline": "Failure analysis",
    "summary": "CI Linux is failing during dependency setup.",
    "spoken_text": "The CI Linux workflow is failing during setup before the test phase starts.",
    "repo": "openai/example",
    "pr_number": 123,
    "failure_target": "CI Linux",
    "failure_target_type": "workflow",
    "checks_context": "setup-python failed after dependency install",
    "embedding_dimensions": 384,
    "ipfs_cid": null
  },
  "trace": {
    "capability_id": "github.check.failure_rag_explain"
  }
}
```

#### Typed stored-output read example

Endpoint:
- `POST /v1/ai/read-stored-output`

Request:

```json
{
  "cid": "bafyexample123",
  "profile": "default"
}
```

Representative response:

```json
{
  "ok": true,
  "capability_id": "ipfs.content.read_ai_output",
  "workflow": "read_stored_output",
  "execution_mode": "direct_import",
  "output_type": "stored_output",
  "typed_output": {
    "schema_name": "stored_output",
    "schema_version": 1,
    "headline": "Stored AI output",
    "summary": "Recovered a previously stored augmented PR summary.",
    "spoken_text": "I loaded the stored AI output from CID bafyexample123.",
    "cid": "bafyexample123",
    "stored_capability_id": "github.pr.rag_summary",
    "metadata": {
      "schema_version": 1,
      "repo": "openai/example",
      "pr_number": 123
    },
    "payload": {
      "summary": "This PR consolidates AI routing and typed workflow execution."
    }
  },
  "output": {
    "headline": "Stored AI output",
    "summary": "Recovered a previously stored augmented PR summary.",
    "spoken_text": "I loaded the stored AI output from CID bafyexample123.",
    "cid": "bafyexample123",
    "stored_capability_id": "github.pr.rag_summary",
    "metadata": {
      "schema_version": 1,
      "repo": "openai/example",
      "pr_number": 123
    },
    "payload": {
      "summary": "This PR consolidates AI routing and typed workflow execution."
    }
  },
  "trace": {
    "capability_id": "ipfs.content.read_ai_output"
  }
}
```

## Target architecture

### 1) Unified capability routing layer
Add a new internal layer, conceptually:
- `src/handsfree/ai/capabilities.py`
- `src/handsfree/ai/router.py`
- `src/handsfree/ai/models.py`
- `src/handsfree/ai/tracing.py`

This layer should accept a normalized request such as:
- capability id
- user/session context
- repository / PR context
- privacy mode
- execution mode preferences
- confirmation and audit requirements

Example capability ids:
- `github.pr.read.summary`
- `github.pr.read.checks`
- `copilot.pr.explain`
- `copilot.pr.diff_summary`
- `copilot.pr.failure_explain`
- `ipfs.llm.generate`
- `ipfs.embeddings.embed_text`
- `ipfs.embeddings.embed_texts`
- `ipfs.content.add_bytes`
- `ipfs.content.cat`
- `ipfs.rag.answer_from_context`

### 2) Backend adapters under the capability layer
Use backend-specific adapters, but keep them behind the shared router.

Backends already present or implied by the repo:
- `GitHubProvider` for current API-backed reads
- `GitHubCLIAdapter` for `gh`
- `CopilotCLIAdapter` for `gh copilot`
- `get_llm_router()` for direct `ipfs_datasets_py.llm_router`
- `get_embeddings_router()` for direct `ipfs_datasets_py.embeddings_router`
- `get_ipfs_router()` for direct `ipfs_datasets_py.ipfs_backend_router`
- future `ipfs_accelerate_py` adapter boundary for acceleration-aware execution selection
- future `ipfs_kit_py` adapter boundary for richer IPFS lifecycle operations
- MCP-backed IPFS providers for delegated/remote execution

### 3) Execution-mode model
Every capability should declare which execution modes it supports:
- `fixture`
- `direct_import`
- `cli_live`
- `api_live`
- `mcp_remote`

Recommended default mapping:
- GitHub read actions: `fixture -> cli_live or api_live`
- Copilot read actions: `fixture -> cli_live`
- embeddings generation: `fixture -> direct_import -> mcp_remote`
- LLM generation: `fixture -> direct_import -> mcp_remote`
- IPFS storage/retrieval: `fixture -> direct_import -> mcp_remote`
- acceleration-aware generation/embedding: `fixture -> direct_import -> mcp_remote`
- richer IPFS lifecycle operations: `fixture -> direct_import -> mcp_remote`

This lets the same intent or planner node route cleanly in local dev, CI, and production.

## Proposed backend responsibilities

### GitHub CLI (`gh`)
Use for:
- PR summary and structured PR reads where CLI output is stable enough
- guarded write actions already flowing through the action service
- context hydration for Copilot prompts when repo/PR info must be resolved

Do not use it as the general AI backend.
Its role is GitHub state access and safe GitHub-side mutations.

### Copilot CLI (`gh copilot`)
Use for:
- explanation
- summarization
- draft generation
- failure analysis
- draft comment or review-body suggestions

Do not let Copilot CLI write directly to GitHub.
Copilot output should be draft material that may later flow into a guarded `gh` write action.

### `llm_router`
Use for:
- project-owned LLM prompts that should not depend on GitHub Copilot
- structured prompt templates for RAG, synthesis, and policy-aware summarization
- cases where the system needs model choice, deterministic fallback, or future on-prem model selection

Candidate uses:
- summarize GitHub events without Copilot dependency
- synthesize voice-safe responses from large intermediate context
- build planner explanations and IPFS-backed dataset answers

### `embeddings_router`
Use for:
- embedding text from GitHub artifacts, transcripts, and local notes
- indexing PR summaries, review comments, notifications, run logs, and user intent history
- similarity search for contextual retrieval before LLM or Copilot prompts

Candidate uses:
- finding similar past failing checks
- retrieving relevant policy or repo docs for a PR
- retrieving similar issue or review history
- powering voice follow-ups like “is this similar to the last failure?”

### `ipfs_router`
Use for:
- persisting normalized context blobs or AI artifacts under content addressing
- storing prompt bundles, redacted code context, summaries, embeddings metadata, or planner traces
- retrieving durable context for later AI reasoning and audit workflows

Candidate uses:
- store PR context packages keyed by CID
- store RAG corpora snapshots
- store structured failure-analysis records
- store reusable embedding index manifests

### `ipfs_accelerate_py`
Use for:
- acceleration-aware generation and embedding dispatch
- runtime/backend selection when the system should choose between multiple inference paths
- future planner-driven optimization for AI/ML execution cost or latency

It should remain a backend family behind the shared capability registry, not a separate orchestration model.

### `ipfs_kit_py`
Use for:
- richer IPFS lifecycle operations
- pin/unpin/resolve/package flows
- packaging reusable analysis corpora, snapshots, or retrieval bundles

It should also remain a backend family behind the shared capability registry, not a parallel execution path.

## How these should work together

### Pattern A: GitHub + Copilot only
Example: “Explain PR 412.”
1. resolve repo/PR context
2. fetch or reuse PR metadata via `gh` or GitHub provider
3. call Copilot CLI capability `copilot.pr.explain`
4. return spoken summary + structured card + trace

### Pattern B: GitHub + embeddings + llm_router
Example: “Is this failure similar to the last one?”
1. resolve current repo/PR/check context
2. fetch current failure summary
3. embed current failure text through `embeddings_router`
4. query similar stored incidents from local/IPFS-backed index
5. synthesize answer with `llm_router`
6. optionally surface source CIDs or references in debug metadata

### Pattern C: GitHub + IPFS + llm_router
Example: “Create an incident summary for this PR failure and save it.”
1. gather GitHub check/run context
2. synthesize structured summary with `llm_router`
3. persist summary record with `ipfs_router.add_bytes`
4. return CID and spoken confirmation

### Pattern D: GitHub + Copilot + llm_router
Example: “Draft a PR comment explaining the failure in our tone.”
1. use Copilot CLI for raw technical explanation
2. use `llm_router` to rewrite into project tone / shorter voice-safe or comment-safe format
3. return draft only
4. optional follow-up confirmation can post it through guarded `gh pr comment`

### Pattern E: embeddings + IPFS + llm_router RAG flow
Example: “Search our stored design notes and answer whether this PR matches prior architecture.”
1. embed query with `embeddings_router`
2. retrieve top matching note fragments from local or IPFS-indexed store
3. synthesize answer with `llm_router`
4. cite matching records via CID or source metadata in debug output

### Pattern F: GitHub + accelerate + llm/embeddings
Example: “Run the faster local path for this failure analysis.”
1. resolve GitHub PR/check context
2. use `ipfs_accelerate_py` to choose or optimize the active LLM/embedding backend
3. execute the requested explanation, ranking, or synthesis workflow
4. return the same typed response contract as the non-accelerated path

### Pattern G: GitHub + IPFS kit packaging
Example: “Package this failure corpus and pin it.”
1. gather GitHub-derived summaries, failure records, or retrieved context
2. package the bundle through `ipfs_kit_py`
3. pin or publish it
4. return CID/package metadata through the same typed AI or storage response contract

## Capability registry design
Each capability should declare:
- `capability_id`
- `backend_family`
- `execution_modes`
- `input_schema`
- `requires_github_context`
- `requires_confirmation`
- `privacy_mode_behavior`
- `fixture_support`
- `trace_formatter`
- `spoken_response_formatter`

Example capability entries:

### `copilot.pr.explain`
- backend: `copilot_cli`
- inputs: `repo?`, `pr_number`
- modes: `fixture`, `cli_live`
- confirmation: no
- output: headline, summary, spoken_text

### `ipfs.embeddings.embed_texts`
- backend: `embeddings_router`
- inputs: `texts[]`, `model?`, `namespace?`
- modes: `fixture`, `direct_import`, `mcp_remote`
- confirmation: no
- output: vectors, metadata

### `ipfs.content.add_bytes`
- backend: `ipfs_router`
- inputs: `bytes`, `content_type?`, `pin?`, `tags?`
- modes: `fixture`, `direct_import`, `mcp_remote`
- confirmation: maybe, depending on persistence policy
- output: CID, size, storage metadata

### `ipfs.llm.generate`
- backend: `llm_router`
- inputs: `prompt`, `system_prompt?`, `model?`, `context_refs?`
- modes: `fixture`, `direct_import`, `mcp_remote`
- confirmation: no
- output: text, citations, model metadata

## Router and command-layer changes

### Command intents to add or extend
Keep the current AI intents, but classify them by backend family.

GitHub/Copilot-facing intents:
- `ai.explain_pr`
- `ai.summarize_diff`
- `ai.explain_failure`
- `ai.draft_pr_comment`
- `ai.draft_review_comment`

IPFS/ML-facing intents:
- `ai.embed_text`
- `ai.find_similar`
- `ai.answer_with_context`
- `ai.accelerate_generate_and_store`
- `ipfs.store_context`
- `ipfs.fetch_context`
- `ipfs.search_notes`

These should not all ship at once, but the plan should reserve the namespaces now.

### Implemented AI command phrases
The current command layer already supports representative user-facing phrases such as:
- `explain pr 123`
- `summarize diff for pr 123`
- `explain workflow CI Linux for pr 123`
- `rag summary for pr 123`
- `find similar failures for pr 125`
- `read summary from cid bafy123`
- `accelerate and store summarize the failure cluster`
- `generate and store with acceleration summarize the failure cluster to ipfs`

The accelerated phrases currently map to:
- capability: `ipfs.accelerate.generate_and_store`
- behavior: generate through `ipfs_accelerate_py`, store through IPFS, and optionally pin through `ipfs_kit_py` when the phrase explicitly asks for storage to IPFS

### Session context rules
Session context should expand from just `repo` and `pr_number` to also track optional AI context:
- `current_check_name`
- `current_workflow_name`
- `last_cid`
- `last_similarity_query`
- `last_embedding_namespace`

That will allow natural follow-ups such as:
- “Explain that failure again”
- “Save this analysis to IPFS”
- “Find similar ones”
- “Use the same repo”

## Data model improvements
Add structured trace metadata for AI/ML execution results.

Recommended shared trace fields:
- `capability_id`
- `backend_family`
- `execution_mode`
- `tool_name` or `command_id`
- `model_name` if applicable
- `fixture_name` when replayed
- `repo`
- `pr_number`
- `failure_target`
- `embedding_namespace`
- `cid`
- `retrieved_context_count`
- `duration_ms`
- `redaction_applied`
- `fallback_reason`

This should flow through:
- command responses
- action logs where relevant
- agent task traces
- future observability exports

## Configuration model
Introduce explicit configuration for AI backend selection.

Recommended variables:
- `HANDSFREE_GH_CLI_ENABLED`
- `HANDSFREE_GH_COPILOT_ENABLED`
- `HANDSFREE_CLI_FIXTURE_MODE`
- `HANDSFREE_IPFS_DATASETS_DIRECT_ENABLED`
- `HANDSFREE_IPFS_DATASETS_MCP_ENABLED`
- `HANDSFREE_IPFS_ACCELERATE_ENABLED`
- `HANDSFREE_IPFS_KIT_ENABLED`
- `HANDSFREE_AI_DEFAULT_EXPLAIN_BACKEND=copilot_cli|llm_router`
- `HANDSFREE_AI_DEFAULT_EMBEDDINGS_BACKEND=ipfs_datasets`
- `HANDSFREE_AI_DEFAULT_STORAGE_BACKEND=ipfs_router`
- `HANDSFREE_AI_DEFAULT_ACCELERATION_BACKEND=ipfs_accelerate`
- `HANDSFREE_AI_DEFAULT_IPFS_KIT_BACKEND=ipfs_kit`
- `HANDSFREE_AI_RAG_ENABLED`
- `HANDSFREE_AI_EMBEDDING_NAMESPACE`
- `HANDSFREE_AI_MAX_CONTEXT_ITEMS`
- `HANDSFREE_AI_HISTORY_RETENTION_DAYS`
- `HANDSFREE_AI_HISTORY_MAX_RECORDS_PER_USER`

`HANDSFREE_AI_HISTORY_RETENTION_DAYS` now controls best-effort pruning of `ai_history_index` on write. If unset, no automatic age-based pruning occurs. If set, records older than that many days are removed opportunistically as new persisted failure-analysis outputs are indexed.
`HANDSFREE_AI_HISTORY_MAX_RECORDS_PER_USER` now controls best-effort per-user/per-capability count pruning of `ai_history_index` on write. If unset, no automatic count-based pruning occurs.

Precedence should be:
1. explicit capability configuration
2. backend feature flag
3. backend availability check
4. fixture fallback

## Security and privacy rules
This integration touches AI and storage, so the safety model must be explicit.

Required rules:
- Copilot CLI remains draft-only unless routed through a guarded GitHub write action
- `llm_router` prompts must respect privacy mode and code-excerpt limits
- `embeddings_router` should operate on redacted or bounded-size text by default
- `ipfs_router` writes should never persist raw secrets or unredacted auth context
- every backend call should log backend family and redaction status
- no arbitrary shell passthrough to `gh` or `gh copilot`
- no direct persistence of large repository snapshots without explicit operator intent

## Development model
Use the same fixture-first loop described in `11-devloop-vscode.md`.

Add fixture categories for:
- `tests/fixtures/cli/gh/`
- `tests/fixtures/cli/copilot/`
- `tests/fixtures/ipfs_datasets/llm/`
- `tests/fixtures/ipfs_datasets/embeddings/`
- `tests/fixtures/ipfs_datasets/ipfs/`

Required test layers:
- parser tests for new intents
- router tests for backend selection and session context
- adapter tests for direct routers and CLI paths
- fallback tests when `ipfs_datasets_py` is missing
- integration tests for hybrid flows like GitHub -> embeddings -> llm

## Phased roadmap

### Phase 0: Consolidate existing foundations
- keep `agent_providers.py` as the canonical provider registry
- finish removing remaining duplicated action-routing logic
- document current CLI and IPFS adapter seams in one place

### Phase 1: Introduce shared AI capability router
- add `src/handsfree/ai/` capability-routing modules
- define typed capability requests/results
- wrap existing Copilot CLI and `ipfs_datasets_py` adapters behind that layer

### Phase 2: Register direct IPFS AI capabilities
- expose `llm_router`, `embeddings_router`, and `ipfs_router` as backend families
- add fixture-backed adapter tests
- add execution-mode selection and fallback rules

### Phase 3: Add `ipfs_accelerate_py` and `ipfs_kit_py` adapter seams
- add `src/handsfree/ipfs_accelerate_adapters.py`
- add `src/handsfree/ipfs_kit_adapters.py`
- define typed capability wrappers for acceleration-aware execution and richer IPFS lifecycle operations
- keep both packages behind the same shared capability registry

### Phase 4: Hybrid GitHub + AI workflows
- add RAG-style capability flows using GitHub context + embeddings + llm_router
- add draft comment synthesis flows using Copilot + llm_router
- add acceleration-aware execution selection
- add IPFS persistence and packaging for analysis artifacts

### Phase 5: Planner integration
- let the future planner and theorem-checking layer target the same capability registry
- ensure planner nodes can call GitHub, Copilot, and IPFS-backed AI capabilities through one execution contract

### Phase 6: Productionization and rollout
- observability and redaction audits
- backend health reporting
- feature-flag rollout by capability family
- broader integration coverage in CI

## Suggested PR slicing

### PR A: Capability registry foundation
- add `src/handsfree/ai/models.py`
- add `src/handsfree/ai/capabilities.py`
- add minimal registry for current Copilot CLI intents

### PR B: `ipfs_datasets_py` capability adapters
- wrap `get_llm_router`, `get_embeddings_router`, and `get_ipfs_router`
- add fixture and fallback tests

### PR C: `ipfs_accelerate_py` adapter layer
- add `src/handsfree/ipfs_accelerate_adapters.py`
- define typed capability wrappers for accelerated generation and embeddings
- add fallback behavior when acceleration backends are unavailable

### PR D: `ipfs_kit_py` adapter layer
- add `src/handsfree/ipfs_kit_adapters.py`
- define typed capability wrappers for richer IPFS lifecycle flows
- add fixture and fallback tests for packaging/pinning primitives

### PR E: Hybrid GitHub + AI read workflows
- implement shared capability execution for:
  - explain PR
  - summarize diff
  - explain failure
- add backend-selection trace metadata

### PR F: embeddings-backed retrieval
- add similarity-search capability contracts
- persist or index small fixture corpora
- add tests for “find similar failure” workflows

### PR G: IPFS persistence workflows
- store generated analysis records via `ipfs_router`
- optionally package result sets via `ipfs_kit_py`
- surface CID in command responses and debug traces

### PR H: planner binding
- connect the capability registry to the future hierarchical planner work

## Success criteria
This integration is successful when:
1. GitHub CLI, Copilot CLI, `ipfs_datasets_py`, `ipfs_accelerate_py`, and `ipfs_kit_py` are all reachable through one capability-routing model.
2. The same user intent can select fixture, direct, accelerated, CLI, or MCP execution without changing handler logic.
3. AI-generated text can be drafted, transformed, accelerated, and optionally persisted without bypassing policy controls.
4. Embeddings and IPFS-backed storage are usable for retrieval and traceable context reuse.
5. Tests cover fallback behavior when any optional backend is missing.
6. The planner can eventually target this stack without inventing another execution abstraction.

## Immediate next implementation step
The next concrete engineering step should be:
- create `src/handsfree/ai/models.py` and `src/handsfree/ai/capabilities.py`
- register the already implemented Copilot CLI capabilities there
- then add adapter-backed capability entries for:
  - `ipfs.llm.generate`
  - `ipfs.embeddings.embed_text`
  - `ipfs.content.add_bytes`

That is the cleanest path to unify the GitHub CLI / Copilot CLI work already in the repo with `ipfs_datasets_py` today while leaving a clean adapter seam for `ipfs_accelerate_py` and `ipfs_kit_py`.

## Package-role assumptions to validate early
This plan assumes the following package roles:
- `endomorphosis/ipfs_datasets_py`: direct AI/data router primitives such as `llm_router`, `embeddings_router`, and IPFS router helpers
- `endomorphosis/ipfs_accelerate_py`: acceleration and backend/runtime selection layer
- `endomorphosis/ipfs_kit_py`: broader IPFS content lifecycle and packaging layer

Validate those assumptions early in implementation discovery and keep the capability contract stable even if the concrete adapter APIs differ.
