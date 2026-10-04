# Branch and worktree review — 2026-10-04

Reviewed the parent repository and eight direct submodule repositories, fetching their GitHub origins before cleanup. The existing published reconciliation already incorporates parent branch history. Local parent `main` was fast-forwarded to `origin/main`; the dirty checkout remains on `chore/fmt-check-main` with its source changes preserved.

## Completed cleanup

- 13 local branches removed after ancestry checks and expected-object comparisons.
- 815 GitHub branches removed using atomic pushes with explicit expected-object leases.
- 2 clean, inactive worktrees removed.
- 43 inactive temporary test/cache directories older than 24 hours removed (22,239 bytes of file contents).
- Default and rootless Docker contexts checked; both had zero containers.

## Remaining work preserved

Active supervisors still use several worktrees. Dirty, locked, artifact-bearing and embedded-submodule worktrees remain, including missing locked worktree registrations that preserve Git recovery stores. Two clean worktrees could not be removed normally because they contain submodules; no forced removal was performed. Git administrative directories reported as main worktrees were retained.

All parent branch tips were already ancestors of published main. The datasets ModelManager branch changes match published main byte-for-byte in all six changed files. Original accelerator PGIR history and datasets local-source snapshot have verified sanitized equivalents in published main; originals remain in archive/recovery branches. The Android upstream assets branch is separate upstream asset history and was retained.

Open pull request head/base dependencies and checked-out branches were excluded from remote cleanup. No source modifications or new merges were necessary. No source tests were run for ref-only cleanup; verification used fresh fetches, ancestry checks, exact file object comparisons, expected-object deletion and worktree status/process checks.

Temporary bare reconciliation repositories, database files, scripts, logs, sockets, locks, active caches and system-owned temporary files remain preserved. They are not established disposable caches.

## Audit files

`inventory.json` records initial refs, worktrees and dirty status across nine repositories. `sanitized-history-verification.json` records published sanitized history mappings. `branch-cleanup-plan.json`, `branch-cleanup-results.json`, `worktree-cleanup-results.json`, `tmp-inventory.json`, `tmp-cleanup-results.json`, `open-prs.json` and `final-verification.json` record cleanup and remaining resources. These local audit files were not committed or published.
