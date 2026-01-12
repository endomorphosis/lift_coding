PR-004: Command system (intent parsing + profiles + confirmations)

Placeholder branch for a future draft PR.

- Source spec: implementation_plan/prs/PR-004-command-router-and-confirmations.md
- Stack note: docs/specs assume DuckDB (embedded) + Redis.

## Task checklist
- [ ] Implement the work described in the source spec
- [ ] Add/extend fixture-first tests
- [ ] Ensure CI passes (fmt/lint/test/openapi)

---

# PR-004: Command system (intent parsing + profiles + confirmations)

## Goal
Implement the command pipeline: parse transcript text into intents/entities, route to tools, and enforce the confirmation model for side effects.

## Why (from the plan)
- `docs/06-command-system.md`: intent parser, router, policy gate, pending action token
- `spec/command_grammar.md`: phrase sets + disambiguation + negative examples
- `docs/01-requirements.md`: profiles; safe actions require confirmation

## Scope
- Intent parser (text-first) supporting at least:
  - `inbox.list`
  - `pr.summarize`
  - `system.confirm`, `system.cancel`, `system.repeat`
  - `agent.delegate` (can be stubbed to storage in PR-008)
- Profile handling (`workout`, `kitchen`, `commute`, `default`) affecting response verbosity and confirmation strictness
- Pending action flow:
  - for side-effect intents, return `needs_confirmation` + `pending_action` token
  - `POST /v1/commands/confirm` executes stored action payload (can no-op until PR-007)
  - token expiry + cancellation
- Transcript fixture tests (clean + noisy) mapping to expected parsed intent

## Out of scope
- Real GitHub behavior and summaries (PR-005)
- Real side effects like requesting reviews (PR-007)

## Issues this PR should close (create these issues)
- Command: implement intent parser using `spec/command_grammar.md`
- Command: implement confirmation + token lifecycle
- Profiles: implement profile-based response tuning
- Tests: transcript fixture suite (clean/noisy/negative)

## Acceptance criteria
- Given transcript fixtures, intent parser returns deterministic `ParsedIntent`
- Confirmation flow works end-to-end with token create/confirm/expire
- `system.repeat` replays last spoken response (or last command result) per user session

## Dependencies
- PR-002 (API skeleton)
- PR-003 for persistence (recommended; otherwise in-memory for MVP-only)
