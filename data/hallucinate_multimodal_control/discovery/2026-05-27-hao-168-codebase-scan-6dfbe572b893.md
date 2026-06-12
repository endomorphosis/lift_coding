# HAO-168 Codebase Scan Finding

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

The flagged PR-log line described completed cleanup, not unresolved router work.
Current `src/handsfree/commands/router.py` creates a `ProfileConfig` from the
selected profile and passes `profile_config.privacy_mode` through the inbox and
PR summary handler paths. The work log wording was updated to avoid
annotation-style cleanup language on the scanner-flagged summary line.

## Attempt 2 Verification

Rechecked the worktree for HAO-168. The current PR log line 18 says the router
uses the profile privacy-mode configuration through both handler paths, and the
live router code passes `profile_config.privacy_mode` to both
`handle_inbox_list()` and `handle_pr_summarize()`. Focused validation coverage
remains in `tests/test_profile_privacy_mode.py` and
`tests/test_router_privacy_mode.py`, so no product-code change is needed for
this docs-track finding.

## Attempt 1 Verification - 2026-06-12

Rechecked the current worktree for this backlog item. The implementation already
resolves the selected `ProfileConfig` before routing and passes
`profile_config.privacy_mode` into both GitHub-backed inbox and PR summary
handler calls. The PR work log line was tightened so the scanner-flagged line
states the completed handler behavior directly instead of resembling an
unresolved code annotation.
