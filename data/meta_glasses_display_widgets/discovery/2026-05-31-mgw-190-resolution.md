# MGW-190 Resolution

Date: 2026-05-31
Task: MGW-190
Source: scripts/hallucinate_multimodal_control_todo_supervisor.py:305
Evidence: data/meta_glasses_display_widgets/discovery/2026-05-31-mgw-190-codebase-scan-969bf9b8ee48.md
Fingerprint: 969bf9b8ee48867ade61424bcdf9374e6e5b7a5f

## Finding

The codebase scanner flagged line 305 of `scripts/hallucinate_multimodal_control_todo_supervisor.py`:

```python
args = _with_default(args, "--objective-todo-vector-index-path", str(OBJECTIVE_TODO_VECTOR_INDEX_PATH))
```

The word "todo" in the CLI flag name `--objective-todo-vector-index-path` caused the scanner to
treat it as a deferred-work annotation (`annotated_followup`), filing MGW-190.

## Resolution

This is a **false positive**. The flagged line came from the earlier supervisor
implementation, where the CLI flag name referred to the backlog task-board
vector index, not a deferred code action. The current supervisor has since been
reduced to a 129-line bootstrap wrapper, so the original source line 305 no
longer exists.

The remaining scanner-sensitive fields in the current wrapper are the bootstrap
path-key and path-flag arguments passed into `build_script_supervisor_bootstrap_runner`.
They name the backlog task-board location. The source comment now records the
MGW-190 suppression without repeating the old flag-name text:

```python
# scanner-resolved: MGW-190 - these bootstrap path fields name the
# backlog task-board location; they are not deferred-work annotations.
```

<!-- scanner-resolved: MGW-190 — this resolution document records a false positive; no active annotation remains in the source file -->

## Status

False positive suppressed. No functional change to runtime behaviour.

## Validation

```
python3 -m py_compile scripts/hallucinate_multimodal_control_todo_supervisor.py
```

Exit code 0 — script compiles successfully with the updated comment in place.
