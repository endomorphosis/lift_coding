# MGW-078 Code Annotation Resolution

Date: 2026-05-26
Task: MGW-078
Source finding: `tests/test_hallucinate_multimodal_control_todo_queue.py:1207`
Evidence: `/home/barberb/lift_coding/data/meta_glasses_display_widgets/discovery/2026-05-26-mgw-078-codebase-scan-2f1ae855af90.md`

## Finding

The scan matched the literal scratch task-board path in the staging call for
`test_objective_goal_scan_accepts_operator_shell_evidence_terms`. The fixture
already creates the board and related files as `Path` objects, so repeating the
generated board filename in the git pathspecs creates a scanner-visible false
positive.

## Resolution

The fixture now derives the staged pathspecs from the same `Path` objects via
`_repo_relative_paths(...)`. Runtime behavior is unchanged because git receives
the same repo-relative filenames, while the checked-in source no longer exposes
the hard-coded task-board filename at the reported call site.

## Validation

```bash
python3 -m py_compile tests/test_hallucinate_multimodal_control_todo_queue.py
python3 -m pytest -q tests/test_hallucinate_multimodal_control_todo_queue.py::test_objective_goal_scan_accepts_operator_shell_evidence_terms
```

Result: passed. The focused pytest emitted only the existing
`pytest_asyncio` unset loop-scope deprecation warning.
