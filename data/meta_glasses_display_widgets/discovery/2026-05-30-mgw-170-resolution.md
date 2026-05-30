# MGW-170 Resolution

Date: 2026-05-30
Source: data/virtual_ai_os/discovery/2026-05-28-vai-122-resolution.md:17
Finding: prose on line 17 contains task-board terminology triggering scanner as annotation

## Resolution

Line 17 of the VAI-122 resolution document reads:

> not a code-level annotation marker.

The surrounding prose (lines 15–17) explains that the codebase scanner had
misidentified the string `--objective-surplus-min-terms-per-task-board-item`
embedded in a Python flag name as an unresolved annotation. The prose is
retrospective documentation of a completed fix; no active annotation exists.

This is a **false positive**, consistent with the assessment in the MGW-169
merge-conflict resolution (which catalogued MGW-169 through MGW-173 as the same
class of re-trigger on completed resolution notes).

A `<!-- scanner-resolved: MGW-170 -->` suppression comment has been appended
immediately after the affected paragraph in `vai-122-resolution.md` so that
future scans classify this block as historical documentation only.

No source-code changes were required.

## Verdict

False positive: scanner flagged prose describing task-board terminology inside a
completed resolution note. The VAI-122 resolution document has been updated with
a suppression comment to prevent re-triggering.

## Validation

- `test -f data/virtual_ai_os/discovery/2026-05-28-vai-122-resolution.md` → PASS
