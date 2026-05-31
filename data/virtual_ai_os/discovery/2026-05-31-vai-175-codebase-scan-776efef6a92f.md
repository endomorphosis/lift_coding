# VAI-175 Codebase Scan Finding

Date: 2026-05-31
Fingerprint: 776efef6a92f73235106bdca32d4dfa0b9de2f24
Kind: annotated_followup
Source: scripts/hallucinate_multimodal_control_todo_supervisor.py:307
Priority: P3
Track: runtime

## Evidence

```text
# scanner-resolved: MGW-191, MGW-192, HAO-244, HAO-248, HAO-249, VAI-166, HAO-254, VAI-170, HAO-258 — "todo" in --objective-surplus-min-terms-per-todo refers to backlog task entries (CLI flag name, not a deferred-work annotation).
```

## Suggested Handling

Review the finding in context, decide whether it represents a bug, missing test,
maintenance risk, or false positive, and land a small fix with validation. If the
finding is a false positive, document why in the changed code or discovery notes
so the supervisor does not keep re-adding the same work.
