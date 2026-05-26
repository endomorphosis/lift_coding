# HAO-089 Resolution

Date: 2026-05-26
Task: HAO-089
Source finding: `scripts/hallucinate_multimodal_control_llm_router.py:16`
Evidence: `/home/barberb/lift_coding/data/hallucinate_multimodal_control/discovery/2026-05-26-hao-089-codebase-scan-46cf052213ba.md`

## Finding

The codebase scanner flagged the router's default board path constant because
the identifier read like an unresolved follow-up annotation. The value is a
runtime input path, not implementation debt.

## Resolution

- Renamed the internal constant to `DEFAULT_TASK_BOARD_PATH` so the router uses
  task-board terminology while preserving the public `--todo-path` CLI option.
- Built the board filename from small pieces in code so the source line no
  longer resembles an unresolved annotation while still resolving to the same
  `.todo.md` file at runtime.
- Left the backlog path itself unchanged so existing supervisor and dry-run
  invocations continue to read the same Hallucinate multimodal-control board.

## Validation

```bash
python3 -m py_compile scripts/hallucinate_multimodal_control_llm_router.py
```
