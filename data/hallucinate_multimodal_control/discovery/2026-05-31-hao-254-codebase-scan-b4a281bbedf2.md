# HAO-254 Codebase Scan Finding

Date: 2026-05-31
Fingerprint: b4a281bbedf2520231ad06e6e7f57ebf7c4bc413
Kind: annotated_followup
Source: scripts/hallucinate_multimodal_control_todo_supervisor.py:307
Priority: P3
Track: runtime

## Evidence

```text
# scanner-resolved: MGW-191, MGW-192, HAO-244, HAO-248 — "todo" in --objective-surplus-min-terms-per-todo refers to backlog task entries (CLI flag name, not a deferred-work annotation).
```

## Suggested Handling

Review the finding in context, decide whether it represents a bug, missing test,
maintenance risk, or false positive, and land a small fix with validation. If the
finding is a false positive, document why in the changed code or discovery notes
so the supervisor does not keep re-adding the same work.
