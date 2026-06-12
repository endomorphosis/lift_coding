# HAO-195 Resolution

Date: 2026-06-12
Source: scripts/hallucinate_multimodal_control_todo_supervisor.py:302
Kind: annotated_followup
Status: resolved

## Finding

The codebase scan evidence captured an older supervisor argument default:

```text
args = _with_default(args, "--objective-todo-vector-index-path", str(OBJECTIVE_TODO_VECTOR_INDEX_PATH))
```

## Resolution

The explicit `_with_default` argument wiring is no longer present in
`scripts/hallucinate_multimodal_control_todo_supervisor.py`. The supervisor now
delegates objective refill defaults to
`build_namespace_objective_refill_defaults_factory()`, which derives the
objective vector-index path from `HALLUCINATE_DATA_PATHS`.

This keeps the runtime path default centralized with the shared supervisor
factory and removes the stale literal flag wiring that triggered the scan. An
inline `scanner-resolved: HAO-195` comment now ties the current delegation point
back to the old line-302 finding so it is not re-filed as unresolved work.

## Validation

```bash
python3 -m py_compile scripts/hallucinate_multimodal_control_todo_supervisor.py
```

Result: passed on 2026-06-12.
