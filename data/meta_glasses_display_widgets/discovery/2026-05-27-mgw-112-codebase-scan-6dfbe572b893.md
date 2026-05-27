# MGW-112 Codebase Scan Finding

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

The cited work-log bullet was stale cleanup wording, not an unresolved code
task. Current `CommandRouter` behavior already reads
`profile_config.privacy_mode` for both GitHub-backed inbox listing and PR
summary paths, then passes that value to `handle_inbox_list()` and
`handle_pr_summarize()`. `ProfileConfig` includes a `privacy_mode` field, and
all built-in profiles continue to default to `PrivacyMode.STRICT`.

`work/PR-081-privacy-mode-per-profile.md` now describes the implemented router
behavior directly instead of mentioning removed cleanup comments.
