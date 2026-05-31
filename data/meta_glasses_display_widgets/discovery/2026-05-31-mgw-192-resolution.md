# MGW-192 Resolution

Date: 2026-05-31
Task: MGW-192
Source: scripts/hallucinate_multimodal_control_todo_supervisor.py:308
Evidence: data/meta_glasses_display_widgets/discovery/2026-05-31-mgw-192-codebase-scan-c0b8d370e688.md
Fingerprint: c0b8d370e6882c1792dbe40437bf137fc39dfbb5

## Finding

The codebase scanner flagged line 308 of `scripts/hallucinate_multimodal_control_todo_supervisor.py`:

```python
args = _with_default(args, "--objective-surplus-min-terms-per-todo", str(OBJECTIVE_SURPLUS_MIN_TERMS_PER_TODO))
```

The word "todo" in the CLI flag name `--objective-surplus-min-terms-per-todo` caused the scanner to
treat it as a deferred-work annotation (`annotated_followup`), filing MGW-192. This is the same line
that was previously flagged as MGW-191; the suppression comment on the preceding line only referenced
MGW-191, so the scanner refiled under a new task ID.

## Resolution

This is a **false positive**. The word "todo" appears in the CLI flag name
`--objective-surplus-min-terms-per-todo`, where it refers to backlog task entries (work-item queue),
not a deferred code action. The suppression comment on line 307 has been updated to include both
`MGW-191` and `MGW-192` so the scanner does not re-file the same finding under yet another ID.

The comment at line 307 has been updated to:

```python
# scanner-resolved: MGW-191, MGW-192 — "todo" below is part of the CLI flag name --objective-surplus-min-terms-per-todo (backlog task-board entry count), not a deferred-work annotation.
```

<!-- scanner-resolved: MGW-192 — this resolution document records a false positive; no active annotation remains in the source file -->

## Status

False positive suppressed. No functional change to runtime behaviour.

## Validation

```
python3 -m py_compile scripts/hallucinate_multimodal_control_todo_supervisor.py
```

Exit code 0 — script compiles successfully with the updated comment in place.
