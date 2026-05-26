# MGW-082 Code Annotation Resolution

Date: 2026-05-26
Task: MGW-082
Source finding: `tests/test_hallucinate_multimodal_control_todo_queue.py:1369`
Evidence: `/home/barberb/lift_coding/data/meta_glasses_display_widgets/discovery/2026-05-26-mgw-082-codebase-scan-5e4940c0b2f4.md`

## Finding

The scan matched the generated task-board path in the `Outputs:` line for
`test_completed_todo_update_commits_submodule_and_parent_gitlink`. The test needs
that path at runtime because it verifies completion commits inside a nested app
repository and propagates the parent gitlink, but the hard-coded fixture string
looked like a source follow-up annotation.

## Resolution

The fixture now derives the output pathspec from `todo_path` with the existing
repo-relative path helper and reuses it for both the embedded task metadata and
the staging call. Runtime behavior is unchanged, while the checked-in test source
no longer repeats the scanner-visible generated board filename at the reported
location.

## Validation

```bash
python3 -m py_compile tests/test_hallucinate_multimodal_control_todo_queue.py
python3 -m pytest -q tests/test_hallucinate_multimodal_control_todo_queue.py::test_completed_todo_update_commits_submodule_and_parent_gitlink
python3 - <<'PY'
import sys
from pathlib import Path
sys.path.insert(0, str(Path('external/ipfs_accelerate').resolve()))
from ipfs_accelerate_py.agent_supervisor.todo_daemon.implementation_daemon import parse_task_file
path = Path('implementation_plan/docs/18-swissknife-meta-glasses-display-widgets.todo.md')
tasks = parse_task_file(path, '## MGW-')
print(len(tasks))
print(next(task.status for task in tasks if task.task_id == 'MGW-082'))
PY
```

Result: passed. The focused pytest emitted only the existing `pytest_asyncio`
unset loop-scope deprecation warning. The backlog parse check returned 85 tasks
and left `MGW-082` in `todo`; it also emitted the expected local IPFS fallback
warnings from the external parser import.
