# PR-058: Agent delegation default provider when configured

## Goal
Make `agent.delegate` work out-of-the-box when GitHub issue dispatch is configured, without needing to always specify a provider.

## Current gap
- If the caller doesn’t supply `provider`, `AgentService.delegate()` defaults to `HANDSFREE_AGENT_DEFAULT_PROVIDER` else `copilot`.
- `copilot` is a stub in this repo, so delegation can appear “successful” but does not dispatch real work.

## Scope
- Backend:
  - If `provider` is not provided and `HANDSFREE_AGENT_DEFAULT_PROVIDER` is not set:
    - Prefer `github_issue_dispatch` when it is configured (has `HANDSFREE_AGENT_DISPATCH_REPO` + token).
    - Otherwise keep current default behavior.
  - Document the precedence rules.
- Tests:
  - Add tests that confirm provider selection precedence.

## Acceptance criteria
- With `HANDSFREE_AGENT_DISPATCH_REPO` + `GITHUB_TOKEN` set (and no explicit provider), `agent.delegate` uses `github_issue_dispatch`.
- Existing tests remain green.

## References
- src/handsfree/agents/service.py
- src/handsfree/agent_providers.py
- tracking/PR-054-agent-delegation-real-dispatch.md
