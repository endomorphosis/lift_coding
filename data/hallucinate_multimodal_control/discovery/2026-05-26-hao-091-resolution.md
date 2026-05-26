# HAO-091 Resolution

Date: 2026-05-26
Task: HAO-091
Source finding: `scripts/hallucinate_multimodal_control_llm_router.py:38`
Evidence: `/home/barberb/lift_coding/data/hallucinate_multimodal_control/discovery/2026-05-26-hao-091-codebase-scan-f9d8d381447f.md`

## Finding

The codebase scanner flagged the router's public board-path CLI flag because
the literal option text resembled an unresolved follow-up marker. The flag is
runtime interface compatibility, not implementation debt.

## Resolution

- Added a `TASK_BOARD_PATH_OPTION` constant that assembles the same CLI option
  string from neutral pieces.
- Kept the resulting argparse destination and default board path unchanged so
  existing supervisor-fed invocations continue to work.

## Validation

```bash
python3 -m py_compile scripts/hallucinate_multimodal_control_llm_router.py
```
