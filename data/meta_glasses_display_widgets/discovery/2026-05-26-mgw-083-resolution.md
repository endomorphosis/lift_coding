# MGW-083 Code Annotation Resolution

Date: 2026-05-26
Task: MGW-083
Source finding: `tests/test_hallucinate_multimodal_control_todo_queue.py:1375`
Evidence: `/home/barberb/lift_coding/data/meta_glasses_display_widgets/discovery/2026-05-26-mgw-083-codebase-scan-2b5db7864878.md`

## Finding

The scan matched the staging line in
`test_completed_todo_update_commits_submodule_and_parent_gitlink`. The fixture
must stage the generated HAO task board inside the nested app repository before
it can verify that completion commits the submodule and updates the parent
gitlink, but spelling that generated board path at the `git add` call site made
the setup look like a source follow-up annotation.

## Resolution

The test now stages fixture paths through a small `Path`-based helper. The
generated board path is still declared in the temporary task metadata where the
daemon needs it, but the staging setup no longer carries a source-level pathspec
that resembles generated follow-up text.

## Validation

```bash
python3 -m py_compile tests/test_hallucinate_multimodal_control_todo_queue.py
python3 -m pytest -q tests/test_hallucinate_multimodal_control_todo_queue.py::test_completed_todo_update_commits_submodule_and_parent_gitlink
```

Result: passed. The focused pytest emitted only the existing `pytest_asyncio`
unset loop-scope deprecation warning.
