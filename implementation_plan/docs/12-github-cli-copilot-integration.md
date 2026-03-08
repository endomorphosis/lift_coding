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
# GitHub CLI + Copilot CLI + IPFS Router Integration Plan

## Objective
Integrate `gh`, `gh copilot`, and the optional `ipfs_datasets_py` router adapters into one coherent AI/ML execution layer for HandsFree. The target state is a system where:
- GitHub context is gathered through `gh` or the existing GitHub provider
- Copilot CLI provides draft AI assistance for review, failure triage, and code understanding
- `llm_router`, `embeddings_router`, and `ipfs_router` from `ipfs_datasets_py` provide local or remote AI/ML primitives
- routing between those backends is explicit, policy-controlled, fixture-testable, and observable

This plan extends, rather than replaces, the work already captured in:
- `implementation_plan/docs/11-devloop-vscode.md`
- `implementation_plan/docs/14-mcp-plus-plus-ipfs-server-integration.md`

## Why this matters
The repository already has three partially overlapping AI paths:
- GitHub/Copilot CLI for code-hosting and Copilot assistance
- `ipfs_datasets_py` direct router adapters for LLM, embeddings, and IPFS functions
- MCP-backed IPFS providers for delegated background tasks

What is missing is one plan that defines how these fit together under a single execution model.

Without that, the project risks:
- duplicated orchestration logic
- separate prompt and tracing models per backend
- inconsistent safety rules between GitHub CLI and IPFS-backed AI calls
- fragmented fixture/test coverage

## Current state in this repo

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
- session-context reuse across PR-centric AI commands

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
- behavior is covered by `tests/test_ipfs_datasets_routers.py`

### Existing MCP-based IPFS provider path
The repo also has a delegated task path via MCP-related modules:
- `src/handsfree/mcp/`
- `src/handsfree/agent_providers.py`
- `src/handsfree/agents/service.py`

This means there are already two IPFS-related execution styles in the codebase:
- direct router import for synchronous local operations
- MCP-backed remote provider execution for delegated jobs

## Core design decision
Treat `gh`, `gh copilot`, `llm_router`, `embeddings_router`, and `ipfs_router` as backends behind one shared capability-routing layer.

Do not let each integration invent its own execution path.

The system should decide per capability whether to use:
- GitHub REST provider
- GitHub CLI
- Copilot CLI
- `ipfs_datasets_py` direct routers
- MCP-backed IPFS providers

That selection must be driven by a single routing contract, not scattered handler logic.

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
- `ipfs.store_context`
- `ipfs.fetch_context`
- `ipfs.search_notes`

These should not all ship at once, but the plan should reserve the namespaces now.

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
- `HANDSFREE_AI_DEFAULT_EXPLAIN_BACKEND=copilot_cli|llm_router`
- `HANDSFREE_AI_DEFAULT_EMBEDDINGS_BACKEND=ipfs_datasets`
- `HANDSFREE_AI_DEFAULT_STORAGE_BACKEND=ipfs_router`
- `HANDSFREE_AI_RAG_ENABLED`
- `HANDSFREE_AI_EMBEDDING_NAMESPACE`
- `HANDSFREE_AI_MAX_CONTEXT_ITEMS`

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

### Phase 3: Hybrid GitHub + AI workflows
- add RAG-style capability flows using GitHub context + embeddings + llm_router
- add draft comment synthesis flows using Copilot + llm_router
- add IPFS persistence for analysis artifacts

### Phase 4: Planner integration
- let the future planner and theorem-checking layer target the same capability registry
- ensure planner nodes can call GitHub, Copilot, and IPFS-backed AI capabilities through one execution contract

### Phase 5: Productionization and rollout
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

### PR C: Hybrid GitHub + AI read workflows
- implement shared capability execution for:
  - explain PR
  - summarize diff
  - explain failure
- add backend-selection trace metadata

### PR D: embeddings-backed retrieval
- add similarity-search capability contracts
- persist or index small fixture corpora
- add tests for “find similar failure” workflows

### PR E: IPFS persistence workflows
- store generated analysis records via `ipfs_router`
- surface CID in command responses and debug traces

### PR F: planner binding
- connect the capability registry to the future hierarchical planner work

## Success criteria
This integration is successful when:
1. GitHub CLI, Copilot CLI, and `ipfs_datasets_py` routers are all reachable through one capability-routing model.
2. The same user intent can select fixture, direct, CLI, or MCP execution without changing handler logic.
3. AI-generated text can be drafted, transformed, and optionally persisted without bypassing policy controls.
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

That is the cleanest path to unify the GitHub CLI / Copilot CLI work already in the repo with the existing `ipfs_datasets_py` router adapters.
