# Drained Codebase Scan Feeder

Date: 2026-05-25

## Change

The HAO daemon now treats an empty backlog as a drain boundary. When every task
is completed, the next codebase scan bypasses the normal cooldown once for that
completed task count and runs in exhaustive traversal mode across the root
checkout and nested git worktrees, including submodules.

The scan still appends a bounded number of tasks per pass. Unappended findings
are not marked seen, so after those tasks drain the next exhausted-board scan
continues feeding the codex loop from the remaining codebase findings.

Generated discovery directories remain skipped, and fenced markdown examples
remain ignored, so the feeder does not recursively file tasks from its own
evidence reports.
