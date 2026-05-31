# MGW-207 Codebase Scan Finding

Date: 2026-05-31
Fingerprint: 5013c2cad7fa01e54dc2f562ac715ca73071ccc2
Kind: annotated_followup
Source: data/virtual_ai_os/discovery/2026-05-31-vai-162-resolution.md:7
Priority: P3
Track: docs

## Evidence

```text
The scan flagged the string `--objective-surplus-min-terms-per-todo` as a <!-- scanner-resolved: MGW-202 — false positive; "todo" here is part of a CLI flag name referring to backlog task entries (work-item queue), not a deferred-work annot
```

## Suggested Handling

Review the finding in context, decide whether it represents a bug, missing test,
maintenance risk, or false positive, and land a small fix with validation. If the
finding is a false positive, document why in the changed code or discovery notes
so the supervisor does not keep re-adding the same work.
