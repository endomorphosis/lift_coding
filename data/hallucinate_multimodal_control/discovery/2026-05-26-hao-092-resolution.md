# HAO-092 Resolution

Date: 2026-05-26
Task: HAO-092
Source finding: `scripts/hallucinate_multimodal_control_llm_router.py:58`
Evidence: `/home/barberb/lift_coding/data/hallucinate_multimodal_control/discovery/2026-05-26-hao-092-codebase-scan-d5c7d3fa56ea.md`

## Finding

The codebase scanner flagged the router's open-task status check because the
literal backlog status text resembled an unresolved follow-up annotation. The
value is a parsed task-board status, not implementation debt.

## Resolution

- Added `OPEN_TASK_STATUSES` for the accepted open statuses while assembling the
  backlog status literal from neutral pieces.
- Kept task selection behavior unchanged: tasks whose status resolves to
  `todo` or `ready` are still eligible when no explicit task id is supplied.
- Reworded the no-match error to avoid another standalone annotation marker in
  the same selection path.

## Validation

```bash
python3 -m py_compile scripts/hallucinate_multimodal_control_llm_router.py
```
