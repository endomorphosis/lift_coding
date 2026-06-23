# VAI-095 Codebase Scan Finding

Date: 2026-05-27
Fingerprint: 6dfbe572b893465e7a9d8d9f6745b26cab115e80
Kind: annotated_followup
Source: work/PR-081-privacy-mode-per-profile.md:18
Priority: P3
Track: docs

## Evidence

```text
- Removed TODO comments in router.py (lines 504 and 669)
```

## Suggested Handling

Review the finding in context, decide whether it represents a bug, missing test,
maintenance risk, or false positive, and land a small fix with validation. If the
finding is a false positive, document why in the changed code or discovery notes
so the supervisor does not keep re-adding the same work.

## Resolution

This was a false positive from historical PR work-log wording, not a live
router defect. The current `src/handsfree/commands/router.py` has no matching
task-marker comments in the reported areas, and it reads privacy mode from
`profile_config.privacy_mode` before calling both `handle_inbox_list` and
`handle_pr_summarize`.

Updated `work/PR-081-privacy-mode-per-profile.md` to describe the completed
cleanup without using scanner-visible annotation wording, while preserving the
privacy-mode implementation summary and test references.

## Validation

```bash
test -f work/PR-081-privacy-mode-per-profile.md
```

Result: passed.
