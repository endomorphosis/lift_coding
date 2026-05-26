# MGW-076 Code Annotation Resolution

Date: 2026-05-26
Task: MGW-076
Source finding: `tests/test_hallucinate_multimodal_control_todo_queue.py:1122`
Evidence: `/home/barberb/lift_coding/data/meta_glasses_display_widgets/discovery/2026-05-26-mgw-076-codebase-scan-d3c194c9a502.md`

## Finding

The scan matched a fixture staging call in
`test_objective_goal_scan_accepts_meta_glasses_remote_terminal_evidence`.
The test writes its scratch task board through `Path` objects, so the git add
step should stage those generated paths instead of repeating literal pathspecs.

## Resolution

The fixture now stages the task board, objective heap, and observability
document with repo-relative paths derived from the same `Path` values used to
create them. This keeps the test aligned if the temporary board filename changes
and removes the scanner-visible hard-coded path at the reported line.

The merge-conflict markers left around this fixture and the adjacent MGW backlog
entries were also resolved so the test module compiles and the supervised task
board remains parseable. Existing task statuses were preserved.

## Validation

```bash
python3 -m py_compile tests/test_hallucinate_multimodal_control_todo_queue.py
python3 -m pytest -q tests/test_hallucinate_multimodal_control_todo_queue.py::test_objective_goal_scan_accepts_meta_glasses_remote_terminal_evidence
```

Result: passed. The focused pytest emitted only the existing
`pytest_asyncio` unset loop-scope deprecation warning.
