PR-008: Agent orchestration stub (task lifecycle + notifications)

Placeholder branch for a future draft PR.

- Source spec: implementation_plan/prs/PR-008-agent-orchestration-stub.md
- Stack note: docs/specs assume DuckDB (embedded) + Redis.

## Task checklist
- [ ] Implement the work described in the source spec
- [ ] Add/extend fixture-first tests
- [ ] Ensure CI passes (fmt/lint/test/openapi)

---

# PR-008: Agent orchestration stub (task lifecycle + notifications)

## Goal
Deliver MVP4 foundation: accept “delegate to agent” commands, track lifecycle, and notify user on state changes.

## Why (from the plan)
- `docs/07-agent-orchestration.md`: task lifecycle, safety, traceability
- `docs/01-requirements.md`: R4 delegate tasks; notify when opened/blocked
- `db/schema.sql`: `agent_tasks`

## Scope
- Implement `agent.delegate` intent handling:
  - create an `agent_tasks` record with `created`/`running` transitions
  - store instruction + target (issue/pr)
- Implement provider abstraction:
  - `copilot` provider (placeholder)
  - `custom` provider (placeholder)
  - initial implementation can be “mock runner” that transitions states on a timer or via a dev endpoint
- Add notification events (initially logged or returned as spoken updates):
  - created/running/needs_input/completed/failed
- Store an agent trace skeleton (links/prompt/tools used) as fields or separate table

## Out of scope
- Actually invoking a real coding agent in production
- Auto-merge (explicitly prohibited by plan)

## Issues this PR should close (create these issues)
- Agent: implement task lifecycle storage + state machine
- Agent: implement `agent.delegate` command path
- Notifications: emit user-facing updates for state changes (mock is fine)
- Safety: ensure no agent path can merge without policy + explicit approval

## Acceptance criteria
- Delegation command creates a task and returns a short spoken confirmation
- Task state transitions are persisted and queryable
- A user can ask for “agent status” and get a summary (even if minimal)

## Dependencies
- PR-004 (intent routing)
- PR-003 (agent task persistence)
