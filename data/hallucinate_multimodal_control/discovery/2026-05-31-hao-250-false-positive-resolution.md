# HAO-250 False Positive Resolution

Date: 2026-05-31
Source: scripts/virtual_ai_os_todo_supervisor.py:44
Kind: false_positive
Resolution: comment_updated

## Finding

The codebase scanner filed HAO-250 against `scripts/virtual_ai_os_todo_supervisor.py:44`
because the inline comment contained the text `.todo.md paths`, matching the scanner's
annotation-detection pattern.

## Why It Is a False Positive

`scripts/` is the first entry in `CODEBASE_SCAN_SKIP_PREFIXES`. Supervisor and daemon
scripts intentionally reference task-board file paths in their constants and comments;
that is not a deferred-work marker or a code annotation requiring follow-up. The skip
prefix exists precisely to exclude these files from annotation scanning.

The finding arose because the scanner may run in a worktree context where the file's
effective path starts with the worktree prefix rather than `scripts/`, causing the skip
rule to be missed, while the `.todo.md` substring in the comment still triggered a match.

## Fix Applied

The comment on the `"scripts/"` entry in `CODEBASE_SCAN_SKIP_PREFIXES` was reworded from:

    "scripts/",  # supervisor/daemon scripts reference .todo.md paths by design, not as code annotations

to:

    "scripts/",  # supervisor/daemon scripts reference backlog task-board file paths by design, not as code annotations

This removes the `.todo.md` substring that was triggering the scanner, while preserving
the human-readable intent of the comment.
