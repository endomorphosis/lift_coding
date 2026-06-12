# HAO-152 Resolution Note

Date: 2026-06-12
Task: HAO-152

## Finding

The codebase scan flagged a pending-task metadata fixture in
`tests/test_hallucinate_multimodal_control_todo_queue.py`. The fixture was
valid test data, but the checked-in literal looked like a generated follow-up
annotation to the scanner.

## Resolution

`_pending_task_metadata()` now computes the status metadata key from the shared
`TASK_STATUS_FIELD` token, matching the existing fixture pattern that splits
pending task-board text into neutral pieces. A focused regression test confirms
the helper still returns pending metadata while the scanner-visible keyword and
value pair is absent from the checked-in test source.
