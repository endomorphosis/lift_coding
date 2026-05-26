# MGW-074 Code Annotation Resolution

Date: 2026-05-26
Task: MGW-074
Source finding: `tests/test_hallucinate_multimodal_control_todo_queue.py:1022`
Evidence: `/home/barberb/lift_coding/data/meta_glasses_display_widgets/discovery/2026-05-26-mgw-074-codebase-scan-a13f54fcc8a8.md`

## Finding

The scan matched the git staging call in
`test_objective_goal_scan_uses_ast_and_embedding_evidence`. The fixture already
builds the scratch repository files as `Path` objects, so the staging call should
use those same paths instead of repeating literal pathspecs.

## Resolution

The fixture now stages the generated task board, objective heap, source file, and
notes file through their repo-relative `Path` values. Runtime behavior is
unchanged, but the test can no longer drift between the files it writes and the
files it commits when fixture paths are renamed.

## Validation

```bash
python3 -m py_compile tests/test_hallucinate_multimodal_control_todo_queue.py
python3 -m pytest -q tests/test_hallucinate_multimodal_control_todo_queue.py::test_objective_goal_scan_uses_ast_and_embedding_evidence
```

Result: passed. The focused pytest emitted only the existing `pytest_asyncio`
unset loop-scope deprecation warning.
