# Command System

## Goals
- Robust in noisy environments
- Minimal user memorization
- Safe execution with confirmations
- Deterministic in tests (fixtures) and debuggable in VS Code

## Pipeline
1. STT produces text (or you submit text directly in dev)
2. Intent Parser maps to:
   - intent name
   - entities (repo, PR number, user)
   - confidence
3. Command Router selects tool(s)
4. Policy Engine authorizes and may require confirmation
5. Response Composer creates short spoken output + optional UI cards

## Intent examples
- inbox.list
- pr.summarize {repo?, number}
- pr.request_review {repo?, number, reviewers}
- checks.status {repo?, branch?}
- agent.delegate {issue/pr, instruction}
- system.confirm / system.cancel / system.repeat

## Confirmation model
- Side-effects create a pending action token:
  - “I can request review from Alex and Priya on PR 412. Say ‘confirm’ to proceed.”
- Confirm/cancel are global intents.
- Pending actions expire after N seconds.

## Profiles
- Workout: shortest responses, more confirmations, fewer notifications
- Kitchen: slower speech, step-by-step, timers
- Commute: medium verbosity, batch notifications

## Command grammar file
See `spec/command_grammar.md` for recommended phrases + disambiguation patterns.
