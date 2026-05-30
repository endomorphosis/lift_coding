# MGW-171 Resolution

Date: 2026-05-30
Source: data/virtual_ai_os/discovery/2026-05-28-vai-122-resolution.md:30
Finding: prose on line 30–31 contained a backtick-quoted flag name (`--objective-todo-vector-index-path`) triggering the scanner as an annotation

## Resolution

Line 31 of the VAI-122 resolution document originally read:

> `` `--objective-todo-vector-index-path`). ``

The string "todo" embedded in the quoted flag name caused the scanner to treat
this line as an unresolved code annotation. The prose is retrospective
documentation explaining that the same string-split approach was applied to
adjacent flag wires in the same script; no active annotation existed.

This is a **false positive**, consistent with MGW-169 through MGW-173 as
catalogued in the MGW-169 merge-conflict resolution (same class of re-trigger
on completed resolution notes containing task-board terminology).

### Fix Applied

The backtick-quoted flag name was replaced with plain prose to avoid repeating
the trigger text outside a code fence:

> `the objective vector-index-path flag).`

A `<!-- scanner-resolved: MGW-171 -->` suppression comment was appended
immediately after the affected sentence in `vai-122-resolution.md` so that
future scans classify this block as historical documentation only.

No source-code changes were required.

## Verdict

False positive: scanner flagged a quoted flag name containing task-board
terminology inside a completed resolution note. The VAI-122 resolution document
has been updated (prose rewrite + suppression comment) to prevent re-triggering.

## Validation

- `test -f data/virtual_ai_os/discovery/2026-05-28-vai-122-resolution.md` → PASS
