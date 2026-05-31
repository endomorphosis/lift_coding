# HAO-248 Codebase Scan Finding

Date: 2026-05-31
Fingerprint: 5473dc5ddeb3389b8b2ba7aad2c568e30b9bc08f
Kind: annotated_followup
Source: scripts/hallucinate_multimodal_control_todo_supervisor.py:307
Priority: P3
Track: runtime

## Evidence

```text
# scanner-resolved: MGW-191, MGW-192, HAO-244 — "todo" in --objective-surplus-min-terms-per-todo refers to backlog task entries (CLI flag name, not a deferred-work marker).
```

## Suggested Handling

Review the finding in context, decide whether it represents a bug, missing test,
maintenance risk, or false positive, and land a small fix with validation. If the
finding is a false positive, document why in the changed code or discovery notes
so the supervisor does not keep re-adding the same work.
