# HAO-117 Resolution

Date: 2026-05-26
Task: HAO-117
Source finding: `scripts/virtual_ai_os_llm_router.py:59`
Evidence: `/home/barberb/lift_coding/data/hallucinate_multimodal_control/discovery/2026-05-26-hao-117-codebase-scan-08f229ba3bff.md`

## Finding

The codebase scanner flagged the virtual-AI-OS LLM router's no-match error
message because it used the board's literal open-state label in prose. The
message reports a runtime selection failure, not pending implementation work.

## Resolution

- Reworded the no-match error to use `open task` terminology.
- Kept task selection behavior unchanged: tasks whose status resolves to
  `todo` or `ready` are still eligible when no explicit task id is supplied.
- Matched the wording already used by the Hallucinate multimodal-control LLM
  router for the same selection path.

## Validation

```bash
python3 -m py_compile scripts/virtual_ai_os_llm_router.py
```
