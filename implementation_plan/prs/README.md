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
- PR-009 (MCP++ IPFS providers) depends on PR-008
- PR-010 (Meta glasses IPFS direct prototype + MCP production) depends on PR-009
- PR-011 (NL prompt -> hierarchical IPFS tool planning) depends on PR-010
- PR-012 (p2p bluetooth transport foundation) extends transport/provider baseline and can proceed in parallel with mobile data-channel preparation
- PR-013 (mobile bluetooth data-channel bridge) depends on PR-009 protocol contract
- PR-014 (peer session handshake + identity) depends on PR-010 + PR-009
- PR-015 (peer messaging UX + command integration) depends on PR-011
- PR-016 (resilience/security/rollout) depends on PR-009 through PR-012

Files:
- PR-001-repo-foundation.md
- PR-002-backend-api-skeleton.md
- PR-003-db-migrations-and-models.md
- PR-004-command-router-and-confirmations.md
- PR-005-github-readonly-inbox-and-summary.md
- PR-006-github-webhook-ingestion-and-replay.md
- PR-007-policy-engine-and-safe-action.md
- PR-008-agent-orchestration-stub.md
- PR-009-mcp-plus-plus-ipfs-integration.md
- PR-010-meta-glasses-ipfs-tooling-prototype-and-mcp-production.md
- PR-011-nl-prompt-to-hierarchical-ipfs-tool-planning.md
- PR-012-p2p-bluetooth-transport-foundation.md
- PR-013-mobile-bluetooth-data-channel-bridge.md
- PR-014-peer-session-handshake-and-identity.md
- PR-015-peer-messaging-ux-and-command-integration.md
- PR-016-resilience-security-and-rollout-controls.md
