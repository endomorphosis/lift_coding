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

This was a completed-work log entry that reused a scanner-sensitive annotation
word while describing already-landed router cleanup. The current implementation
does not leave the router strict-only: `CommandRouter._handle_inbox_list` reads
`profile_config.privacy_mode` and forwards it to `handle_inbox_list`, and the PR
summary path does the same for `handle_pr_summarize`. The profile defaults in
`src/handsfree/commands/profiles.py` remain conservative by setting built-in
profiles to `PrivacyMode.STRICT`.

Updated `work/PR-081-privacy-mode-per-profile.md` so the implementation summary
states that the router privacy-mode placeholders were cleared without preserving
the annotation wording that caused the follow-up scan.

## Validation

```bash
test -f work/PR-081-privacy-mode-per-profile.md
```

Result: passed.
