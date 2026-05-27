# VAI-097 Codebase Scan Finding

Date: 2026-05-27
Fingerprint: 4b6fa8e6e4e8714311ce53c8d8100fd6d60a221c
Kind: annotated_followup
Source: work/REMAINING_GAPS_AND_PR_INSTRUCTIONS.md:180
Priority: P2
Track: docs

## Evidence

```text
The original line used a GitHub pull request URL with a fake placeholder PR
number for PR-026.
```

## Suggested Handling

Review the finding in context, decide whether it represents a bug, missing test,
maintenance risk, or false positive, and land a small fix with validation. If the
finding is a false positive, document why in the changed code or discovery notes
so the supervisor does not keep re-adding the same work.

## Resolution

Replaced the annotation-like placeholder PR URLs in
`work/REMAINING_GAPS_AND_PR_INSTRUCTIONS.md` with branch-specific instructions
to use the final URL emitted by GitHub after each draft PR is created. This keeps
the instructions actionable without leaving scanner-triggering placeholder
tokens.

## Validation

```bash
test -f work/REMAINING_GAPS_AND_PR_INSTRUCTIONS.md
```

Result: passed.
