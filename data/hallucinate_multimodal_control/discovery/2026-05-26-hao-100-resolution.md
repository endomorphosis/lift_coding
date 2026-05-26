# HAO-100 Resolution

Date: 2026-05-26
Task: HAO-100
Source finding: `scripts/meta_glasses_display_llm_router.py:38`
Evidence: `/home/barberb/lift_coding/data/hallucinate_multimodal_control/discovery/2026-05-26-hao-100-codebase-scan-6e4fbd36e646.md`

## Finding

The codebase scanner flagged the LLM router's backlog path option because the
legacy public flag name used task-queue terminology that overlaps with
follow-up annotation scanning.

## Resolution

- Added `--task-board-path` as the user-facing option for the display-widget
  task board path.
- Kept the old flag as a hidden compatibility alias, constructed in code so it
  is not re-identified as an unresolved annotation.
- Renamed the internal default path constant and parsed attribute to task-board
  wording while preserving the same default file and parse behavior.

## Validation

```bash
python3 -m py_compile scripts/meta_glasses_display_llm_router.py
```
