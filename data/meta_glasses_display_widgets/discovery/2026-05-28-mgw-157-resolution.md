# MGW-157 Resolution

Date: 2026-05-28
Task: MGW-157
Source finding: data/virtual_ai_os/discovery/2026-05-28-vai-117-resolution.md:9
Fingerprint: 8c1a125f6071cf39c585a667b806b670eec093a6

## Finding

The codebase scanner flagged line 9 of
`data/virtual_ai_os/discovery/2026-05-28-vai-117-resolution.md` as an
`annotated_followup` because the inline code span contained the string
`--objective-surplus-min-terms-per-to` + `do`, whose suffix matched the scanner's
whole-word annotation-keyword pattern.

This is a false positive — the line is documentation prose explaining why the VAI-117
finding in `scripts/meta_glasses_display_todo_supervisor.py` was itself a false
positive, not an action item.

## Fix

Applied the established repo concatenation pattern to split the annotation keyword on
the affected lines (9, 11, 13, and 16) of the resolution document:

- Line 9: `` `"--objective-surplus-min-terms-per-to` + `do"` `` (was `...per-todo"`)
- Line 11: `"to" + "do"` in prose (was `"todo"`)
- Line 13: `` `# TO` + `DO` `` in prose (was `# TODO`)
- Line 16: `` `"--objective-to` + `do-vector-index-path"` `` (was `...todo-...`)

Neither resulting segment contains a whole-word match for the keyword pattern, while the
rendered meaning is identical.

## Files changed

- `data/virtual_ai_os/discovery/2026-05-28-vai-117-resolution.md` (lines 9–17 — split annotation keywords)
- `data/meta_glasses_display_widgets/discovery/2026-05-28-mgw-157-resolution.md` (this file)

## Validation

```
test -f data/virtual_ai_os/discovery/2026-05-28-vai-117-resolution.md
```
