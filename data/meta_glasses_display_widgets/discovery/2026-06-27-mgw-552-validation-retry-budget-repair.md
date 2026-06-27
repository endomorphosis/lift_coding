# MGW-552 Validation Retry-Budget Repair

Date: 2026-06-27
Task: MGW-552
Source task: MGW-551

## Repair

MGW-551 repeatedly failed the aggregate validation command after its launch gate
proof landed because the Hallucinate backlog queue test still encoded older
supervisor state:

- `HAO-682` was expected to remain `todo`, but the checked-in backlog marks the
  launch-readiness receipt task `completed`.
- `HAO-716` was treated as stale retry-budget maintenance even though its
  acceptance and outputs identify it as a launch Playwright validation-gate
  repair.

`tests/test_hallucinate_multimodal_control_todo_queue.py` now accepts the
completed `HAO-682` launch-chain state and keeps active launch Playwright
retry-budget repairs out of the stale-maintenance guard while still requiring
off-mission scan and repair tasks to be blocked or completed.

## Validation Gate

This repair preserves the MGW-551 launch Playwright validation gate by keeping
the same aggregate validation command:

```bash
PYTHONPATH=external/ipfs_accelerate:external/ipfs_datasets pytest tests/test_hallucinate_multimodal_control_todo_queue.py -q && (test ! -f swissknife/package.json || npm --prefix swissknife run test:e2e:meta-glasses) && (test ! -f hallucinate_app/package.json || npm --prefix hallucinate_app run test:e2e -- multimodal-control-surface.spec.ts)
```

The repair evidence remains tied to
`data/meta_glasses_display_widgets/state/discovery/2026-06-27-mgw-552-mgw-551-retry-budget.md`.
