# MGW-166 Codebase Scan Finding

Date: 2026-05-28
Fingerprint: a83ddc64fab6678740331f528f191a059dc46e4c
Kind: annotated_followup
Source: data/virtual_ai_os/discovery/2026-05-28-vai-119-resolution.md:11
Priority: P3
Track: docs

## Evidence

```text
`--objective-surplus-min-terms-per-todo` flag names include the word "todo" as part of
```

## Suggested Handling

Review the finding in context, decide whether it represents a bug, missing test,
maintenance risk, or false positive, and land a small fix with validation. If the
finding is a false positive, document why in the changed code or discovery notes
so the supervisor does not keep re-adding the same work.
