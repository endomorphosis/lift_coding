# HAO-753 Validation Retry-Budget Repair

Date: 2026-07-08
Task: HAO-753
Source task: HAO-745

## Repair

HAO-745 attempts 2, 3, and 4 repeatedly failed the aggregate validation command
after their MCP daemon-launch-health work was otherwise complete, because the
shared queue test hard-coded a stale path for the Swissknife MCP capability
registry:

- `tests/test_hallucinate_multimodal_control_todo_queue.py::test_hao_674_integrates_mcp_launch_contracts_with_swissknife_control_surface`
  read `swissknife/src/services/swissknife-mcp-capability-registry.ts`, but the
  Swissknife submodule reorganized this file into
  `swissknife/src/services/apps/swissknife-mcp-capability-registry.ts` (see the
  HAO-749 merge of Swissknife mobile/Android schema evidence). Every in-repo
  Swissknife consumer (`swissknife/test/e2e/mcp-dashboard.spec.ts`,
  `swissknife/test/mcp-plus-plus/ipfs-ui-descriptors.test.ts`,
  `swissknife/test/mcp-plus-plus/mobile-orb-edge-all-apps.test.ts`, and
  `swissknife/scripts/test-mcp-dashboard-consumer.cjs`) already imports from the
  new `apps/` location, so the Python queue test was the only remaining
  reference to the pre-reorganization path, raising `FileNotFoundError` on
  every attempt regardless of what HAO-745 implemented.
- `tests/test_virtual_ai_os_todo_queue.py::test_vai_503_mcp_dashboard_interoperability_gate_closes_objective_gap`
  carried the identical stale path and would have failed the same way once
  exercised, so it was corrected alongside the HAO-745 evidence path to keep
  both shared queue tests consistent with the current Swissknife layout.
- `src/handsfree/hallucinate_app_defaults.py` had a docstring comment
  referencing the old path; updated for accuracy (no behavioral change).

No Hallucinate App, Swissknife, or MCP daemon feature code needed to change --
the daemon-launch-health Playwright gate, meta-glasses backend gate, and
multimodal control-surface gate were never the actual blocker. This confirms
the retry-budget guardrail correctly identified an environment/test defect
rather than a semantic implementation gap in HAO-745's own work, which remains
open for its own future attempt.

## Collateral Finding

The same worktree also carried `HAO-751` (a sibling retry-budget repair task
for `HAO-740`) in `todo` status. `HAO-740`'s validation command
(`python -m pytest tests/integration -q`) fails with 96 failed and 49 errored
tests spanning MCP++ protocol coverage, Swissknife descriptor-module exports,
and Meta Wearables DAT Android/iOS interop -- a large, pre-existing regression
entirely unrelated to HAO-745's daemon-launch-health scope. Per the existing
`objective-task janitor` deferral pattern used for other out-of-mission
backlog items (see `HAO-684` through `HAO-696`), `HAO-740` was marked
`Status: blocked` with an explicit `Blocked reason`, and `HAO-751` was closed
out documenting the deferral (see
`data/hallucinate_multimodal_control/discovery/2026-07-08-hao-751-hao-740-validation-retry-budget-repair.md`).
This keeps `tests/test_hallucinate_multimodal_control_todo_queue.py::test_hallucinate_multimodal_product_run_defers_stale_scan_and_repair_tasks`
green without claiming the underlying `tests/integration` regression was
fixed; a dedicated remediation task is still required to actually repair that
suite.

## Validation Gate

This repair preserves the launch Playwright validation gate the HAO-745 repair
was filed to protect:

```bash
PYTHONPATH=external/ipfs_accelerate:external/ipfs_datasets pytest tests/test_hallucinate_multimodal_control_todo_queue.py -q && (test ! -f hallucinate_app/package.json || npm --prefix hallucinate_app run test:e2e -- daemon-launch-health.spec.ts) && (test ! -f swissknife/package.json || npm --prefix swissknife run test:e2e:meta-glasses) && (test ! -f hallucinate_app/package.json || npm --prefix hallucinate_app run test:e2e -- multimodal-control-surface.spec.ts)
```

The original guardrail evidence remains tied to
`/home/barberb/lift_coding/data/hallucinate_multimodal_control/discovery/2026-07-08-hao-753-hao-745-retry-budget.md`.
