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
