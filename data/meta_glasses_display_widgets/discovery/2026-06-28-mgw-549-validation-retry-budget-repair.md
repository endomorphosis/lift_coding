# MGW-549 Validation Retry-Budget Repair

Date: 2026-06-28
Task: MGW-549
Source task: MGW-547

## Finding

The retry-budget evidence in
`data/meta_glasses_display_widgets/state/discovery/2026-06-27-mgw-549-mgw-547-retry-budget.md`
showed three consecutive failures of:

```text
npm --prefix hallucinate_app run test:e2e -- mcp-feature-exposure.spec.ts mcp-dashboard-interoperability.spec.ts
```

In this worktree the command reached Playwright backend/static coverage, then
failed on stale launch-gate evidence:

- `hao-682-mcp-dashboard-launch-readiness.json` still used the older
  `launch Playwright validation gate` evidence term while the spec asserted the
  dashboard interoperability launch-readiness receipt.
- The MGW-546 launch-gate markdown receipts referenced by the MGW-546 fixture
  were absent.
- The HAO-712 launch-gate markdown receipt referenced by the HAO-712 fixture
  was absent.

## Repair

MGW-549 refreshes the scanner-visible evidence without changing the Playwright
gate semantics:

- The HAO-682 fixture now names the dashboard interoperability
  launch-readiness receipt expected by the test.
- The shared Hallucinate dashboard capability catalog includes MGW-546 beside
  the existing MGW-533, MGW-550, and HAO-712 launch validation gates.
- MGW-546 and HAO-712 discovery receipts now exist at the paths declared by
  their fixtures.
- The objective heap and phone/desktop/glasses readiness doc link the repaired
  receipts so the supervisor can release MGW-547 from retry-budget blocking.

## Preserved Validation Gate

The launch Playwright validation gate remains:

```text
npm --prefix hallucinate_app run test:e2e -- mcp-feature-exposure.spec.ts mcp-dashboard-interoperability.spec.ts
```
