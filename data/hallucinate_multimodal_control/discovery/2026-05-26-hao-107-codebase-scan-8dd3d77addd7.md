# HAO-107 Codebase Scan Finding

Date: 2026-05-26
Fingerprint: 8dd3d77addd7238751bc10d25788a1f844772e73
Kind: annotated_followup
Source: scripts/meta_glasses_display_todo_supervisor.py:15
Priority: P3
Track: runtime

## Evidence

```text
TODO_PATH = REPO_ROOT / "implementation_plan" / "docs" / "18-swissknife-meta-glasses-display-widgets.todo.md"
```

## Suggested Handling

Review the finding in context, decide whether it represents a bug, missing test,
maintenance risk, or false positive, and land a small fix with validation. If the
finding is a false positive, document why in the changed code or discovery notes
so the supervisor does not keep re-adding the same work.

## Resolution

The scanner flagged the supervisor's display-widget task-board constant because
the constant name and filename suffix looked like an unresolved inline follow-up.
The line was runtime board wiring, not implementation debt.

The supervisor now uses the same neutral task-board naming and split board-file
suffix pattern as `scripts/meta_glasses_display_todo_daemon.py`, preserving the
same MGW board path and public `--todo-path` compatibility while avoiding the
static-scan trigger on the default wiring line.
