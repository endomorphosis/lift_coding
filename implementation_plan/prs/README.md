# PR Drafts (Parallel Tracks)

These are *draft* pull request descriptions derived from the documents in `implementation_plan/`.

Recommended order:
1. PR-001: repo + CI + dev loop scaffolding
2. PR-002: backend API skeleton (OpenAPI-aligned)
3. PR-003: database + migrations + persistence primitives

Then parallelize:
- PR-004 (command system) can run alongside PR-005 (GitHub read-only) and PR-006 (webhook ingest)
- PR-007 (policy + safe write action) depends on PR-004 + PR-005
- PR-008 (agent orchestration) depends on PR-004 + PR-003

Files:
- PR-001-repo-foundation.md
- PR-002-backend-api-skeleton.md
- PR-003-db-migrations-and-models.md
- PR-004-command-router-and-confirmations.md
- PR-005-github-readonly-inbox-and-summary.md
- PR-006-github-webhook-ingestion-and-replay.md
- PR-007-policy-engine-and-safe-action.md
- PR-008-agent-orchestration-stub.md
