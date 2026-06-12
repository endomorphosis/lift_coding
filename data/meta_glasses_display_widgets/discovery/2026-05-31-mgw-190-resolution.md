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

This is a **false positive**. The word "todo" appears in the CLI flag name
`--objective-todo-vector-index-path`, where it refers to the backlog task-board (work-item queue),
not a deferred code action. The supervisor no longer injects that flag directly; it now imports
the shared `TASK_BOARD_PATH_KEY` and `TASK_BOARD_PATH_OPTION` values from the daemon and passes
them into `build_script_supervisor_bootstrap_runner`.

The remaining `todo_path_key` and `todo_path_flag` wrapper argument names are part of the shared
supervisor API. The source comment now records the false positive so the scanner does not re-file
the same finding:

```python
# scanner-resolved: MGW-190 - the old objective-todo flag is gone; these
# todo_path_* wrapper arguments name the backlog work-item queue path.
```

<!-- scanner-resolved: MGW-190 - this resolution document records a false positive; no active annotation remains in the source file -->

## Status

False positive suppressed. No functional change to runtime behavior.

## Validation

```
python3 -m py_compile scripts/hallucinate_multimodal_control_todo_supervisor.py
```

Exit code 0 - script compiles successfully with the updated comment in place.
