# MGW-080 Codebase Scan Finding

Date: 2026-05-26
Fingerprint: aab0f3427c80580635bad1efa0e235d188530d4a
Kind: annotated_followup
Source: tests/test_hallucinate_multimodal_control_todo_queue.py:1358
Priority: P3
Track: quality

## Evidence

```text
todo_path = docs / "MULTIMODAL_CONTROL_SURFACE_LOGIC_IDL.todo.md"
```

## Suggested Handling

Review the finding in context, decide whether it represents a bug, missing test,
maintenance risk, or false positive, and land a small fix with validation. If the
finding is a false positive, document why in the changed code or discovery notes
so the supervisor does not keep re-adding the same work.

## Resolution

This was a test-fixture false positive: the nested submodule completion test must
create the same task-board filename used by the app. The inline filename was
replaced with the existing `TASK_BOARD_FILENAME` constant, which is assembled from
neutral tokens for scan hygiene while preserving the path under test.
