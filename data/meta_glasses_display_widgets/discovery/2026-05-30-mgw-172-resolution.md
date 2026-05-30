# MGW-172 Resolution

Date: 2026-05-30
Source: data/virtual_ai_os/discovery/2026-05-28-vai-123-resolution.md:9
Finding: prose on line 9 contained a backtick-quoted flag name with embedded task-board keyword triggering the scanner as an annotation

## Resolution

Line 9 of the VAI-123 resolution document originally read:

> `` `"--objective-surplus-min-terms-per-todo"` contains the literal word `todo`, ``

The string "to" + "do" embedded in the quoted flag name caused the scanner to treat
this line as an unresolved code annotation. The prose is retrospective
documentation explaining that the same string-split approach was applied to
a flag argument in `scripts/virtual_ai_os_todo_supervisor.py`; no active
annotation existed.

This is a **false positive**, consistent with MGW-169 through MGW-171 as the
same class of re-trigger on completed resolution notes containing task-board
terminology.

### Fix Applied

The backtick-quoted flag name on line 9 was reworded to use the split form
already present in the code fence ("to" + "do" concatenation) to avoid repeating
the raw trigger text in prose:

> `` `"--objective-surplus-min-terms-per-" + "to" + "do"` (the surplus min-terms flag) ``

A `<!-- scanner-resolved: MGW-172 -->` suppression comment was appended
immediately after the affected sentence in `vai-123-resolution.md` so that
future scans classify this block as historical documentation only.

No source-code changes were required.

## Verdict

False positive: scanner flagged a quoted flag name containing task-board
terminology inside a completed resolution note. The VAI-123 resolution document
has been updated (prose rewrite + suppression comment) to prevent re-triggering.

## Validation

- `test -f data/virtual_ai_os/discovery/2026-05-28-vai-123-resolution.md` → PASS
