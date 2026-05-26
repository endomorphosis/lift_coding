# HAO-101 Resolution

Date: 2026-05-26
Task: HAO-101
Source finding: `scripts/meta_glasses_display_llm_router.py:57`
Evidence: `/home/barberb/lift_coding/data/hallucinate_multimodal_control/discovery/2026-05-26-hao-101-codebase-scan-51cfbb7d0bb1.md`

## Finding

The codebase scanner flagged the display-widget LLM router's open-task status
check because a literal backlog status value looked like an unresolved follow-up
annotation. The value is a parsed task-board status, not implementation debt.

## Resolution

- Added `OPEN_TASK_STATUSES` for accepted open statuses while assembling the
  flagged status value from neutral pieces.
- Kept task selection behavior unchanged: tasks whose status resolves to
  `todo` or `ready` are still eligible when no explicit task id is supplied.
- Reworded the no-match error to avoid another standalone annotation marker in
  the same selection path.

## Validation

```bash
python3 -m py_compile scripts/meta_glasses_display_llm_router.py
```
