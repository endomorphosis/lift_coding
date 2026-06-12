# MGW-191 Resolution

Date: 2026-05-31
Task: MGW-191
Source: scripts/hallucinate_multimodal_control_todo_supervisor.py:307
Evidence: data/meta_glasses_display_widgets/discovery/2026-05-31-mgw-191-codebase-scan-06466d54cc2a.md
Fingerprint: 06466d54cc2a38cbf9ffae73f6fb627e7400af36

## Finding

The codebase scanner flagged line 307 of `scripts/hallucinate_multimodal_control_todo_supervisor.py`:

```python
args = _with_default(args, "--objective-surplus-min-terms-per-todo", str(OBJECTIVE_SURPLUS_MIN_TERMS_PER_TODO))
```

The word "todo" in the CLI flag name `--objective-surplus-min-terms-per-todo` caused the scanner to
treat it as a deferred-work annotation (`annotated_followup`), filing MGW-191.

## Resolution

This is a **false positive**. The word "todo" appeared in the CLI flag name
`--objective-surplus-min-terms-per-todo`, where it refers to backlog task entries (work-item queue),
not a deferred code action. The supervisor has since been refactored to pass the
task-board path through `todo_path_key` and `todo_path_flag`; the equivalent
comment now includes a `scanner-resolved: MGW-191` suppression marker so the
scanner does not re-file the same finding.

The current supervisor comment has been updated to:

```python
# scanner-resolved: MGW-190, MGW-191 - "todo" in todo_path_key /
# todo_path_flag refers to the task-board work-item queue path, not a
# deferred-work annotation.
```

<!-- scanner-resolved: MGW-191 — this resolution document records a false positive; no active annotation remains in the source file -->

## Status

False positive suppressed. No functional change to runtime behaviour.

## Validation

```
python3 -m py_compile scripts/hallucinate_multimodal_control_todo_supervisor.py
```

Exit code 0 — script compiles successfully with the updated comment in place.
