# Requirements

## User stories
### R1: Triage while hands-free
- Ask “What needs my attention?” and hear top PRs, mentions, failing checks.

### R2: Understand quickly
- Ask “Summarize PR 123” and hear a 15–30s summary.

### R3: Take safe actions
- Say “Request review from Alex” or “Rerun checks” and the system confirms before executing.

### R4: Delegate to an agent
- Say “Ask the agent to fix issue 918” and get notified when a PR is opened or blocked.

### R5: Context profiles
- Switch profiles (“Workout mode”) that tune verbosity, confirmations, notification frequency.

## Functional requirements
- Voice capture -> STT -> command -> tool execution -> TTS response
- GitHub auth (GitHub App recommended) and per-repo permissions
- Webhook ingestion for PR/check/review/issue events
- Notification delivery to mobile -> wearable audio (or phone audio during dev)
- Action audit log + idempotency for side effects

## Non-functional requirements
- Latency: typical command round trip < 2–3s for read actions
- Reliability: queue commands briefly if network drops
- Privacy: configurable data minimization (no images, no code snippets, etc.)
- Security: least privilege tokens, policy gates, full audit trail

## MVP scope
- PR inbox + PR summary
- Read-only check status + mention alerts
- One safe action: “request review” OR “rerun checks”
- One agent action: “delegate to agent” and notify on PR creation

## Developer experience requirements (critical)
- Wearable simulator for local iteration
- Deterministic fixtures for GitHub + agent orchestration
- Contract tests for the command API and webhook ingestion
- CI that runs unit + contract tests and lints the OpenAPI spec
