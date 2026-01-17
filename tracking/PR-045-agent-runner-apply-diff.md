# PR-045: Agent runner apply diff patches

## Goal
Make the agent runner capable of performing deterministic, auditable work without an LLM by allowing dispatch issues to include fenced `diff` / `patch` blocks that are applied with `git apply --index`.

## Changes
- GitHub Actions workflow applies instruction patches before writing the trace file.
- Docker runner (`agent-runner/runner.py`) applies the same instruction patches via a shared helper.
- Documentation updated to explain how to include diff blocks in dispatch issues.

## Notes
- Patch application failure aborts the task to avoid creating misleading PRs.
- Commit messages are kept small (instruction text may contain large diffs).
