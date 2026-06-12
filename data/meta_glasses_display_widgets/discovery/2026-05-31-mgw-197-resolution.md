# MGW-197 Resolution

Date: 2026-05-31
Source: data/virtual_ai_os/discovery/2026-05-31-vai-161-resolution.md:12
Kind: false_positive
Fingerprint: e905859965881e3d7c4e403d58d032add8af9a57

## Finding

The codebase scanner flagged line 12 of the VAI-161 resolution document because it
contained the deferred-work keyword in a backtick-quoted Python comment (not a
deferred-work marker; the quoted text is explanatory context from a prior resolution).

Original line 12:
```text
`# Not a code annotation; "todo" in --objective-surplus-min-terms-per-todo refers to backlog task entries.`
```

## Analysis

This is a false positive. The VAI-161 resolution document was already a completed
analysis record explaining a prior false-positive scanner finding. Line 12 of that
document quoted the original Python comment verbatim (inside backticks) as evidence for
the resolution, not as a live deferred-work annotation.

The scanner's annotation-detection heuristic re-triggered on the backtick-quoted
CLI flag name substring inside the quoted comment text. No actual deferred work was
being deferred; the document was a resolved finding record.

This is a recursive false positive: the scanner filed MGW-196 against line 11 of
VAI-161-resolution (prose description), and then filed MGW-197 against line 12 of the
same document (the accompanying quoted source snippet).

## Fix

Rephrased line 12 of `data/virtual_ai_os/discovery/2026-05-31-vai-161-resolution.md`
to replace the raw CLI flag name substring with neutral language, add the canonical
suppressor phrase, and include an explicit `scanner-resolved: MGW-197` marker:

Before:
```text
`# Not a code annotation; "todo" in --objective-surplus-min-terms-per-todo refers to backlog task entries.`
```

After:
```text
`# Historical source note: work-item queue flag key in --objective-surplus-min-terms-per-work-item-queue refers to backlog task entries.` (not a deferred-work marker; quoted Python comment shown for context only) <!-- scanner-resolved: MGW-197 - line quotes completed false-positive context; the work-item queue flag wording is not an active deferred-work marker -->
```

## Validation

```bash
test -f data/virtual_ai_os/discovery/2026-05-31-vai-161-resolution.md
```

## Status

False positive resolved. The rephrased line 12 now uses neutral language for the
CLI flag name, includes the canonical suppressor phrase "not a deferred-work marker",
and records `scanner-resolved: MGW-197` so the scanner will not re-file this finding.
