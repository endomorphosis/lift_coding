# Command Grammar (Recommended)

This document defines phrases and patterns that map cleanly to intents in noisy environments.

## Global controls
- "repeat" -> system.repeat
- "cancel" -> system.cancel
- "confirm" -> system.confirm
- "slower" / "faster" -> system.speech_rate (optional)
- "workout mode" / "kitchen mode" / "commute mode" -> system.set_profile

## Inbox & triage
### inbox.list
- "what needs my attention"
- "inbox"
- "pr inbox"
- "anything failing"

### checks.status
- "checks for pr 412"
- "ci status"
- "what's failing on <repo>"

## Pull requests
### pr.summarize
- "summarize pr 412"
- "summarize pull request 412"
- "summarize the last pr"
- "what changed in pr 412"

Disambiguation strategy:
- If repo not provided, use last active repo or ask a single follow-up:
  - "Which repo? I have 412 in ownerA/repo1 and ownerB/repo2."

### pr.request_review (side effect -> needs confirmation)
- "request review from alex on pr 412"
- "add reviewers alex and priya"
- "ask alex to review"

Confirmation phrasing:
- "I can request review from Alex and Priya on PR 412. Say 'confirm' to proceed."

### pr.merge (strict)
- "merge pr 412"
- "merge when green"
- "squash merge pr 412"

Policy gates:
- checks green
- required approvals met
- no blocking labels
- confirm required unless explicitly configured for “merge when green” with strict repo allowlist

## Agent delegation
### agent.delegate
- "ask the agent to fix issue 918"
- "have the agent address review comments on pr 412"
- "tell copilot to handle issue 918" (maps to agent.delegate, provider=copilot)

### agent.progress
- "agent status"
- "what's the agent doing"
- "summarize agent progress"

## Profiles and context tuning
Profiles tune response length and confirmation strictness:
- workout: short + frequent confirms; fewer notifications
- kitchen: slower, step-by-step; timers possible
- commute: medium verbosity; batch notifications

## Testing guidance
Create transcript fixtures:
- `tests/fixtures/transcripts/clean/*.txt`
- `tests/fixtures/transcripts/noisy/*.txt`

Each intent should have at least:
- 5 clean examples
- 5 noisy/ambiguous examples
- 2 negative examples (should return "I didn't catch that")
