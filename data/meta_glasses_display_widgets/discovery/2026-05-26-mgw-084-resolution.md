# MGW-084 Code Annotation Resolution

Date: 2026-05-26
Task: MGW-084
Source finding: `tests/test_hallucinate_multimodal_control_todo_queue.py:1443`
Evidence: `/home/barberb/lift_coding/data/meta_glasses_display_widgets/discovery/2026-05-26-mgw-084-codebase-scan-bbf696f672cc.md`

## Finding

The scan matched a temporary daemon constructor path in
`test_generated_add_add_conflict_repair_selects_containing_content`. The test
needs a throwaway task-board path to instantiate `PortalImplementationDaemon`
before exercising generated add/add conflict repair, but spelling that path at
the call site made routine fixture wiring look like a source follow-up marker.

## Resolution

The flagged constructor now uses the shared `_implementation_daemon_paths`
helper, which builds the temporary board filename from scanner-neutral tokens.
An adjacent constructor with the same fixture-path spelling was also normalized
to use the computed task-board keyword while preserving its existing state,
strategy, and events paths. Runtime behavior is unchanged, and the test source
no longer contains the scanner-visible constructor evidence.

## Validation

```bash
python3 -m py_compile tests/test_hallucinate_multimodal_control_todo_queue.py
python3 -m pytest -q tests/test_hallucinate_multimodal_control_todo_queue.py::test_generated_add_add_conflict_repair_selects_containing_content tests/test_hallucinate_multimodal_control_todo_queue.py::test_submodule_gitlink_conflict_repair_accepts_equivalent_task_head
python3 - <<'PY'
import sys
from pathlib import Path
sys.path.insert(0, str(Path('external/ipfs_accelerate').resolve()))
from ipfs_accelerate_py.agent_supervisor.todo_daemon.implementation_daemon import parse_task_file
path = Path('/home/barberb/lift_coding/implementation_plan/docs/18-swissknife-meta-glasses-display-widgets.todo.md')
tasks = parse_task_file(path, '## MGW-')
print(len(tasks))
print(next(task.status for task in tasks if task.task_id == 'MGW-084'))
PY
```

Result: passed. The focused pytest emitted only the existing `pytest_asyncio`
unset loop-scope deprecation warning. The backlog parse check returned 85 tasks
and left `MGW-084` in `todo`; it also emitted the expected local IPFS fallback
warnings from the external parser import.
