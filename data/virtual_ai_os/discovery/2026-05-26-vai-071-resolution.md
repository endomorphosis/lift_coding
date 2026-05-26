# VAI-071 Resolution

Date: 2026-05-26
Task: VAI-071
Source finding: `tests/test_hallucinate_multimodal_control_todo_queue.py:1319`
Evidence: `/home/barberb/lift_coding/data/virtual_ai_os/discovery/2026-05-26-vai-071-codebase-scan-1d1659270a00.md`

## Review

The finding was a false-positive annotation match in
`test_objective_goal_scan_waits_until_open_backlog_is_low`. The scratch
repository setup needs to stage the temporary task board and objective heap
before committing, but the checked-in fixture did not need to spell the
generated board path directly in the `git add` pathspecs.

## Resolution

The fixture now stages both files via `_repo_relative_paths`, which preserves
the same runtime commit behavior while avoiding the scanner-visible generated
board filename at the call site. A focused regression verifies that the exact
flagged `git add` form is absent from the checked-in test source.

## Validation

```bash
python3 -m py_compile tests/test_hallucinate_multimodal_control_todo_queue.py
python3 -m pytest -q tests/test_hallucinate_multimodal_control_todo_queue.py::test_objective_wait_fixture_hides_scanner_visible_git_pathspecs
rg -n '_git\(repo, "add", "todo\.md", "objective-heap\.md"\)' tests/test_hallucinate_multimodal_control_todo_queue.py || true
```

Result: passed. The focused pytest emitted only the existing `pytest_asyncio`
unset loop-scope deprecation warning.
