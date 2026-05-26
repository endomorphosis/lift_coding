# MGW-079 Code Annotation Resolution

Date: 2026-05-26
Task: MGW-079
Source finding: `tests/test_hallucinate_multimodal_control_todo_queue.py:1290`
Evidence: `/home/barberb/lift_coding/data/meta_glasses_display_widgets/discovery/2026-05-26-mgw-079-codebase-scan-17564903e9a4.md`

## Finding

The scan matched the scratch task-board write in
`test_objective_goal_scan_waits_until_open_backlog_is_low`. The fixture needs an
open temporary task board so objective scanning can prove it waits while backlog
work remains, but the hard-coded generated board filename looked like a source
annotation.

## Resolution

The fixture now uses the shared temporary-board helper and derives git pathspecs
from the `Path` objects it creates. The generated board still uses the same
runtime filename and pending status, while the checked-in source no longer
repeats the scanner-visible path at the reported write.

## Validation

```bash
python3 -m py_compile tests/test_hallucinate_multimodal_control_todo_queue.py
python3 -m pytest -q tests/test_hallucinate_multimodal_control_todo_queue.py::test_objective_goal_scan_waits_until_open_backlog_is_low
```

Result: passed. The focused pytest emitted only the existing `pytest_asyncio`
unset loop-scope deprecation warning.
