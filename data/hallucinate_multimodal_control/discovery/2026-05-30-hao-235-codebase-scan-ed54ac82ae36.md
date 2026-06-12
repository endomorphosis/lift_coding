# HAO-235 Codebase Scan Finding

Date: 2026-05-30
Fingerprint: ed54ac82ae36ea138f368285b2b17d19b8cc44b5
Kind: annotated_followup
Source: scripts/virtual_ai_os_todo_supervisor.py:159
Priority: P3
Track: runtime

## Evidence

```text
args = _with_default(args, "--objective-todo-vector-index-path", str(OBJECTIVE_TODO_VECTOR_INDEX_PATH))
```

## Suggested Handling

Review the finding in context, decide whether it represents a bug, missing test,
maintenance risk, or false positive, and land a small fix with validation. If the
finding is a false positive, document why in the changed code or discovery notes
so the supervisor does not keep re-adding the same work.

## Resolution

Reviewed 2026-06-12. The evidence is a stale scanner hit from the pre-refactor
wrapper path. `scripts/virtual_ai_os_todo_supervisor.py` now delegates objective
refill defaults to `build_namespace_objective_refill_defaults_factory`, which
passes `VIRTUAL_AI_OS_DATA_PATHS.objective_todo_vector_index_path` into
`ObjectiveRefillDefaults.objective_todo_vector_index_path`. The shared supervisor
runner then emits `--objective-todo-vector-index-path` from that default when it
constructs daemon arguments.

No runtime bug remains in the wrapper. The script annotation was expanded so the
scanner has local evidence that the vector-index path is intentional runtime
wiring rather than an unresolved deferred-work marker.
