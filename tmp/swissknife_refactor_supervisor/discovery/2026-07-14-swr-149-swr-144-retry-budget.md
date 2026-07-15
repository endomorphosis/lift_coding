# SWR-149 Resolution: SWR-144 Validation Retry-Budget Failure

- Date: 2026-07-14
- Source task: SWR-144
- Repair task: SWR-149
- Retry budget: 3
- Observed consecutive validation failures: 3
- Failed command: `cd swissknife && npm run services:audit && npm run typecheck:services && npm run test:fast -- test/architecture/source-module-boundaries.test.js`

## Finding

All three source-task attempts stopped at the same environmental failure; none
failed the service canonicalization checks:

| Attempt | Service audit | Host typecheck | Architecture test | Daemon result |
| --- | --- | --- | --- | --- |
| 1 | passed | `tsc: not found` | not reached by chained gate | exit 127 |
| 2 | passed | `tsc: not found` | not reached by chained gate | exit 127 |
| 3 | passed | `tsc: not found` | not reached by chained gate | exit 127 |

The failures are recorded at lines 17653-17657, 132504-132508, and
242713-242717 of these logs:

- `/home/barberb/barberb/copilot-worktrees/lift_coding/hallucinate-llc-psychic-adventure/tmp/swissknife_refactor_supervisor/state/implementation_logs/swr-144-attempt-1.log`
- `/home/barberb/barberb/copilot-worktrees/lift_coding/hallucinate-llc-psychic-adventure/tmp/swissknife_refactor_supervisor/state/implementation_logs/swr-144-attempt-2.log`
- `/home/barberb/barberb/copilot-worktrees/lift_coding/hallucinate-llc-psychic-adventure/tmp/swissknife_refactor_supervisor/state/implementation_logs/swr-144-attempt-3.log`

Attempt 2 also contains the decisive control. With a temporary link to the
integration checkout's installed dependencies, it passed
`typecheck:services`, `typecheck:browser`, and the architecture suite (35/35,
lines 126960-127006). The agent then removed its task-local dependency link as
required before handoff (line 127009). The daemon tried to restore shared paths
before its validation, but no source link existed at the refactor lane root, so
the chained validation immediately returned to `tsc: not found`.

## Root cause

The supervisor runs with the refactor lane as `repo_root`, but the lane had no
`swissknife/node_modules`. The implementation daemon correctly propagates that
lane path into each task worktree, while the healthy install lived in the
integration checkout at
`/home/barberb/barberb/copilot-worktrees/lift_coding/hallucinate-llc-psychic-adventure/swissknife/node_modules`.
Because missing shared paths were skipped, the daemon could not reconstruct the
task link. The pinned Node 20.19.2/npm 10.8.2 toolchain from SWR-146 was healthy;
only the lane-to-task dependency-link chain was incomplete.

## Repair

`scripts/swissknife_lane_worktrees.py` now establishes the missing first link
when a lane starts and revalidates it before clean-checkout validation:

- required `swissknife/node_modules` is linked from the integration checkout;
- optional web and IPFS JavaScript dependency trees are linked when installed;
- an existing correct link is reused and a stale target is replaced;
- a missing or non-directory required install fails lane startup early with an
  actionable `npm ci` instruction;
- links remain ephemeral ignored inputs, not repository configuration.

Regression coverage exercises separate integration/lane roots, stale target
replacement, absent optional dependencies, required-dependency failure,
startup reporting, and validation-time relinking. The current refactor lane was
repaired with the same helper, giving the daemon a stable source for future task
worktrees.

## Recovered SWR-144 implementation

The strongest already-validated source-task result was recovered directly from
its preserved commit:

- outer rescue commit: `e5cab43df09c88a27306a400d7275720d0f37d94`
- SwissKnife commit: `499b160cedbd29c632837392e1ccaff96a45cf9d`
- rescue branch: `rescue/swr-144-attempt-2-1784049509-failed-validation`

That commit contains the SWR-144 canonicalization, migration records, zero
duplicate-policy violations, and the public API/migration guide. Recovery also
exposed a malformed MCP copy of the deontic UI manifest containing literal
merge markers. The copy was deleted, `src/services/apps/mcp-deontic-ui-manifest.ts`
is now the single apps-owned implementation and public entrypoint, and the
migration ledger records the removed MCP path. The source audit now treats
unresolved merge markers as a `--fail-on-legacy` violation, closing the gap that
previously let the malformed shadow escape the gate.

## Validation

```text
node v20.19.2
npm 10.8.2
.nvmrc 20.19.0

python -m pytest tests/test_swissknife_lane_worktrees.py tests/test_implementation_daemon_worktree_dependencies.py -q
20 passed

cd swissknife && npm run services:audit && npm run typecheck:services && npm run test:fast -- test/architecture/source-module-boundaries.test.js
service audit: no ownership, import, legacy, merge-marker, or unclassified duplicate violations
typecheck:services: passed
architecture: 35/35 passed

node_modules/.bin/jest --config=config/jest/jest.base.config.cjs --runInBand --runTestsByPath test/mcp-plus-plus/mcp-deontic-ui-manifest.test.ts test/browser-compat/browser-entrypoints.test.js
21/21 passed

npm run typecheck:browser
passed
```

## Disposition

- SWR-149 is complete.
- The repeated validation blocker is repaired and regression-tested.
- SWR-144 may be removed from strategy `blocked_tasks`; its validated outputs
  have been recovered into this repair lane.
