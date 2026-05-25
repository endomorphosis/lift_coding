# HAO-040 E2E Runner Unblock

Date: 2026-05-25
Task: HAO-040
Source task: HAO-037

## Finding

The HAO-037 retry budget was exhausted before Playwright executed any E2E
specs. Each failed attempt ran:

```bash
cd hallucinate_app && npm run test:e2e
```

The package script used a bare `playwright test` command. In fresh daemon
worktrees there is no `hallucinate_app/node_modules`, so shell resolution found
`/home/barberb/miniforge3/bin/playwright`. That binary is the browser CLI and
does not include the `test` subcommand, producing:

```text
error: unknown command 'test'
```

## Fix

`npm run test:e2e` now calls `scripts/run_playwright_test.mjs`, which runs the
project-local `@playwright/test` CLI. If a daemon-created worktree has no local
Node dependencies, the wrapper bootstraps the declared `hallucinate_app`
dependencies with:

```bash
npm install --package-lock=false --no-audit --no-fund --include=dev
```

The bootstrap sets `SKIP_POSTINSTALL=true` and `SKIP_SUBMODULE_INSTALL=true` so
the project submodule installer is not run as part of E2E validation. No
package-lock is generated, and `node_modules` remains ignored.

`test/e2e/run-tests.sh` uses the same wrapper so direct E2E invocations do not
fall back to an unrelated global Playwright binary.

## Strategy Unblock

`HAO-037` was removed from the strategy `blocked_tasks` list after the runner
failure was addressed, allowing the original security backlog item to be retried
without another indefinite loop on the wrong Playwright binary.
