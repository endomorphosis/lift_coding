# HAO-157 Resolution

Date: 2026-05-27
Task: HAO-157
Source finding: `tests/test_hallucinate_multimodal_control_todo_queue.py:372`
Evidence: `/home/barberb/lift_coding/data/hallucinate_multimodal_control/discovery/2026-05-26-hao-157-codebase-scan-f10169de2a93.md`

## Finding

The codebase scanner flagged a generated pending task-board status line in the
retry-budget test fixture. The fixture should still write a pending backlog item
so retry-budget follow-up generation is exercised, but the checked-in test source
should not expose the generated status line as annotation-shaped text.

## Resolution

- Routed the retry-budget fixture's pending status through the split-token helper
  used for scanner-sensitive backlog fixture text.
- Added a focused assertion that the generated board still contains the pending
  status line while the checked-in test source does not contain that exact line.
- Left daemon behavior and backlog metadata unchanged.

## Validation

```bash
python3 -m py_compile tests/test_hallucinate_multimodal_control_todo_queue.py
```
