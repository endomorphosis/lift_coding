PR-007: Policy engine + one safe write action

This is a placeholder *draft* PR to enable later execution via Copilot coding agents.

- Source spec: implementation_plan/prs/PR-007-policy-engine-and-safe-action.md
- Stack note: docs/specs assume DuckDB (embedded) + Redis.

## Task checklist
- [ ] Implement the work described in the source spec
- [ ] Add/extend fixture-first tests
- [ ] Ensure CI passes (fmt/lint/test/openapi)

---

# PR-007: Policy engine + one safe write action

## Goal
Deliver MVP3: one policy-gated side effect with confirmations and full audit logging.

## Why (from the plan)
- `docs/01-requirements.md`: “safe actions” with confirmation + policy gates
- `docs/08-security-privacy.md`: least privilege + audit log + anomaly/rate limiting
- `docs/10-mvp-checklists.md`: MVP3 = `pr.request_review` OR `checks.rerun`
- `db/schema.sql`: `repo_policies`, `pending_actions`, `action_logs`

## Scope
- Implement policy evaluation for a user+repo:
  - allowlist/denylist behavior (`repo_policies`)
  - `require_confirmation`
  - `require_checks_green` (if data available)
  - `required_approvals`
- Implement idempotency for side-effect endpoints (`idempotency_key`)
- Implement ONE safe action end-to-end (pick one):
  - Option A: `POST /v1/actions/request-review` + intent `pr.request_review`
  - Option B: `POST /v1/actions/rerun-checks` + intent `checks.rerun`
- Audit log entries for every attempt (allowed/denied/executed)
- Rate limiting for side effects (basic)

## Out of scope
- Merge action (`/v1/actions/merge`) unless you want to add it as a follow-up (it is intentionally strict)

## Issues this PR should close (create these issues)
- Policy: implement repo-level policy storage + evaluation
- Actions: implement one safe write action w/ confirmation path
- Audit: write `action_logs` entries for allow/deny/execute
- Idempotency: de-dupe side effects using `idempotency_key`

## Acceptance criteria
- For a denied repo, action returns a clear policy error and logs an audit entry
- For an allowed repo, action returns `needs_confirmation` unless policy config says otherwise
- On confirm, action executes exactly once even if confirm is retried (idempotent)

## Dependencies
- PR-004 (pending action flow)
- PR-005 (GitHub provider or fixture provider to exercise behavior)
- PR-003 (audit + policy persistence)
