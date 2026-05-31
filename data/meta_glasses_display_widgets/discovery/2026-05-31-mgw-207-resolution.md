# MGW-207 Resolution

Date: 2026-05-31
Source finding: `data/virtual_ai_os/discovery/2026-05-31-vai-162-resolution.md:7`
Resolution: false_positive

## Summary

The scanner flagged line 7 of `data/virtual_ai_os/discovery/2026-05-31-vai-162-resolution.md`
because the sentence contains `--objective-surplus-min-terms-per-todo`, and the scanner
matched the substring "todo" as a potential deferred-work annotation.

This is the same recurring false positive previously resolved as MGW-191, MGW-192, HAO-244,
HAO-248, HAO-249, VAI-166, HAO-254, VAI-170, HAO-258, HAO-263, MGW-202, and related tickets.
The scanner re-flagged the inline `scanner-resolved` comment on that line because the comment
text still contains "todo" (as part of the CLI flag name being documented).

## Action Taken

Added MGW-207 to the inline `scanner-resolved` comment at line 7 of
`data/virtual_ai_os/discovery/2026-05-31-vai-162-resolution.md` to prevent future re-flagging:

```markdown
<!-- scanner-resolved: MGW-202, MGW-207 — false positive; "todo" here is part of a CLI flag name referring to backlog task entries (work-item queue), not a deferred-work annotation marker; no open annotation remains in the source code -->
```

## Validation

`test -f data/virtual_ai_os/discovery/2026-05-31-vai-162-resolution.md` — passes.
