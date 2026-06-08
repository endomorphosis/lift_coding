# MGW-283 Codebase Scan Finding

Date: 2026-06-08
Fingerprint: 662ccbd32fa500d4fe38d35f6221828059763deb
Kind: annotated_followup
Source: data/virtual_ai_os/discovery/2026-05-31-vai-166-false-positive-resolved.md:12
Priority: P3
Track: docs

## Evidence

```text
flag name `--objective-surplus-min-terms-per-todo` refers to backlog task entries, not a
```

## Suggested Handling

Review the finding in context, decide whether it represents a bug, missing test,
maintenance risk, or false positive, and land a small fix with validation. If the
finding is a false positive, document why in the changed code or discovery notes
so the supervisor does not keep re-adding the same work.
