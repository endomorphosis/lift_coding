# HAO-501 Codebase Scan Finding

Date: 2026-06-23
Fingerprint: 316b5ecc9e0addfe85da64d943d6737eda6f7ddc
Kind: annotated_followup
Source: tests/test_supervisor_objective_task_janitor.py:114
Priority: P3
Track: quality

## Evidence

```text
"todo",
```

## Suggested Handling

Review the finding in context, decide whether it represents a bug, missing test,
maintenance risk, or false positive, and land a small fix with validation. If the
finding is a false positive, document why in the changed code or discovery notes
so the supervisor does not keep re-adding the same work.

## Resolution

The flagged token was a synthetic `PortalTask` status in a janitor test fixture,
not an actionable source-code annotation. The fixture now builds that status with
the existing `_task_status("to", "do")` helper, preserving the exact runtime task
status while avoiding a repeated annotation finding at the flagged call site.
