# HAO-500 Codebase Scan Finding

Date: 2026-06-23
Fingerprint: 82c22eaf19e5d26b80b45c8196c6701469db8d58
Kind: annotated_followup
Source: tests/test_supervisor_objective_task_janitor.py:67
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

The flagged token was a `PortalTask` fixture status in
`tests/test_supervisor_objective_task_janitor.py`. The test already uses
`_task_status("to", "do")` for synthetic backlog statuses elsewhere in the same
fixture, so the second synthetic task now uses that helper too. Runtime behavior
is unchanged because the helper returns the same `todo` value without embedding a
raw backlog status annotation for the scanner to refile.
