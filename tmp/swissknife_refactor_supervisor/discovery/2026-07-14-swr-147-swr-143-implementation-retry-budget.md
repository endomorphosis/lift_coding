# SWR-147 Discovery: SWR-143 Implementation Retry-Budget Failure

- Task: SWR-147 "Resolve implementation retry-budget failure for SWR-143"
- Filed by: implementation retry-budget guardrail (repeated implementation failures on SWR-143)
- Depends on: SWR-136
- Date: 2026-07-14

## Summary

The retry-budget guardrail opened this repair task after SWR-143 ("Inventory
restored service duplicates by basename, normalized content, and behavior")
exhausted its implementation attempts without a passing validation run. This
was **not** a defect in the SWR-143 deliverables themselves — all three
SWR-143 attempts produced a complete, schema-correct inventory. It was a
**runtime/toolchain setup blocker**: the SwissKnife submodule had no pinned,
portable Node resolution at the time SWR-143 ran, so `npm run
services:audit` / `npm run typecheck:services` were executed against
whatever Node happened to be first on `PATH` in each lane container. The
fix for that class of failure (SWR-146) landed *after* SWR-143's attempts
had already exhausted their retry budget, so SWR-143 never got a chance to
re-validate against a resolved toolchain.

## Evidence timeline (swissknife submodule commit history)

| Time (UTC-7) | Commit | Event |
| --- | --- | --- |
| 02:49:10 | `89dbaec7` | SWR-143 attempt 1 commit (inventory produced) |
| 03:02:02 | `bd99d7bf` | SWR-143 attempt 2 commit (inventory re-produced) |
| 03:15:26 | `76ecc861` | SWR-143 attempt 3 commit (inventory re-produced; retry budget exhausted here) |
| 03:42:33 | `63024515` | SWR-146 attempt 2 commit: adds `.nvmrc`, `scripts/verify-browser-toolchain.mjs`, CI workflow Node pin fixes |
| 03:51:34 | `f3c1e7bd` | SWR-146 attempt 3 commit: finalizes toolchain receipts |

At each of the three SWR-143 commits, `.nvmrc` and
`scripts/verify-browser-toolchain.mjs` **did not exist** (confirmed via
`git show <sha>:.nvmrc` / `git show <sha>:scripts/verify-browser-toolchain.mjs`
returning "path exists on disk, but not in `<sha>`"). `package.json` only
declared a loose `"engines": {"node": ">=18.0.0"}` floor with no resolver
script to select a matching, portable Node executable before invoking
`npm run services:audit` / `npm run typecheck:services`. This is exactly the
failure class the plan document calls out: "a stale PATH entry, an
incompatible system Node fallback, or a host-specific binary path recorded
as repository configuration is a failing state," and it is the class of
bug SWR-146 was opened to fix.

Because SWR-146 (also depending on SWR-136) landed its Node-toolchain pin
*after* SWR-143 had already exhausted its retry budget on the stale
runtime, the supervisor's retry-budget guardrail correctly filed this
ops/repair ticket (SWR-147) rather than letting SWR-143 retry indefinitely
against an unresolved environment blocker.

## Root cause

Setup/runtime blocker: no pinned, portable Node/npm toolchain resolution
existed in the `swissknife` submodule when SWR-143 ran, so validation
commands (`npm run services:audit`, `npm run typecheck:services`) were
exposed to whatever Node binary a lane's `PATH` happened to resolve first,
which was not guaranteed to satisfy the `engines` contract or produce a
consistent `tsc`/`jest`/`node` toolchain across supervisor lane containers.

## Resolution

SWR-146 (merged into this lane before this repair task ran) fixed the
underlying blocker by:

- Pinning `swissknife/.nvmrc` to `20.19.0` and widening
  `package.json#engines.node` to `^20.19.0 || >=22.12.0`.
- Adding `swissknife/scripts/verify-browser-toolchain.mjs`, a
  dependency-free Node-builtin-only resolver that locates a supported Node
  executable, records its resolved absolute path, semantic version, npm
  version, and lockfile fingerprint into a verification receipt (schema
  `swissknife.browser-validation-toolchain.v1`), and fails loudly on an
  absent runtime, a stale `PATH` fallback, or a mismatched symlink.
- Wiring `scripts/swissknife_lane_worktrees.py` (outer supervisor) to run
  and validate that receipt (`validate_browser_toolchain_receipt`) before
  any lane invokes `npm`/`tsc`/`jest`/Playwright/libp2p commands, rejecting
  incomplete, stale, or unrelated verifier output.
- Updating CI workflows (`.github/workflows/*.yml`) to resolve Node from
  the same pinned policy instead of a workflow-local `actions/setup-node`
  default.

With that fix in place, this repair task re-ran SWR-143's full validation
surface against the now-pinned toolchain and confirms it passes cleanly:

```
$ node -v && npm -v && cat .nvmrc
v20.19.2
10.8.2
20.19.0

$ node scripts/verify-browser-toolchain.mjs
Browser toolchain verified: node 20.19.2 (.../node-v20.19.2-linux-x64/bin/node),
npm 10.8.2, sha256:4a0da5b9e1985402f76fdfea784198600f149e46bf62c7c1d0ffdc7bfd2a7474;
receipt test-results/browser-toolchain/verification-receipt.json

$ npm run services:audit
... modules: 57, unknown files: 0, forbidden imports: 0, ownership conflicts: 0,
    browser unsafe imports: 0, restored service duplicate policy violations: 0,
    unapproved service duplicate content hashes: 0, unclassified service
    normalized-content collisions: 0, unclassified service
    behavioral-equivalence groups: 0
exit code: 0

$ npm run typecheck:services
exit code: 0 (tsc --noEmit -p tsconfig.host.json, ~4s)

$ npm run test:fast -- test/architecture/source-module-boundaries.test.js
PASS fast test/architecture/source-module-boundaries.test.js
Tests: 34 passed, 34 total
exit code: 0 (~21s)
```

All SWR-143 expected outputs were confirmed present and structurally sound
on re-inspection:

- `swissknife/docs/restored-service-duplicate-inventory.json` — schema
  `1`, 476 inventoried service executable files, 0 unclassified basename
  collisions, 0 unclassified normalized-content collisions, 0
  unclassified behavioral-equivalence groups, 0 restored duplicate policy
  violations.
- `swissknife/docs/restored-service-duplicate-inventory.md` — human-
  readable summary table matching the JSON ledger.
- `swissknife/src/module-ownership.json` — schema `1`, manifest version
  `2026-07-14`, 57 modules, 16 explicitly-owned root compatibility files,
  0 unknown files, 0 ownership conflicts.
- `swissknife/test/architecture/source-module-boundaries.test.js` — 34
  passing regression assertions covering manifest completeness, root-file
  ownership, forbidden imports, and duplicate-basename policy.

No code or data changes to the SWR-143 outputs were required; the fix was
purely environmental (Node toolchain pinning, already delivered by
SWR-146). This document is the recorded evidence artifact required by the
retry-budget guardrail so the supervisor can release SWR-143 from
`strategy blocked_tasks`.

## Disposition

- SWR-147 status: completed (manual completion, ops/repair task).
- SWR-143's outputs are verified current and passing against the fixed
  toolchain; no further implementation attempts are required for SWR-143's
  existing deliverables. SWR-143 remains available for the supervisor to
  advance its own lifecycle (e.g., re-run its validation gate and mark it
  complete) now that the retry-budget block has been resolved.
