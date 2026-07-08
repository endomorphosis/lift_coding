# HAO-751 Validation Retry-Budget Repair

Date: 2026-07-08
Task: HAO-751
Source task: HAO-740

## Triage

HAO-740's validation command is:

```bash
python -m pytest tests/integration -q
```

Running this command against the current worktree produces 96 failed, 49
errored, 300+ passed, and 96 skipped results, spanning:

- `tests/integration/test_mcp_plus_plus.py` and
  `tests/integration/test_mcp_pp_connector.py` -- collection errors across the
  full MCP++ protocol/connector suite (profiles A-E, UCAN capability checks,
  desktop app tab coverage, endpoint coverage).
- `tests/integration/test_swissknife_external_ipfs_kit_interop.py`,
  `test_swissknife_external_ipfs_accelerate_interop.py`,
  `test_swissknife_external_ipfs_datasets_interop.py`, and
  `test_swissknife_mcp_plus_plus_interop.py` -- descriptor-module export
  contract failures.
- `tests/integration/test_swissknife_external_meta_wearables_dat_android_interop.py`
  and the iOS counterpart -- missing display descriptors and handoff contract
  failures.

This regression is identical across HAO-740 attempts 1, 2, and 3 (see
`data/hallucinate_multimodal_control/state/lane-0/implementation_logs/hao-740-attempt-{1,2,3}.log`),
confirming it is not caused by HAO-740's own hallucinate_app-mobile
interoperability diff. It is, however, a large, pre-existing regression across
subsystems (MCP++ protocol, Swissknife descriptor exports, Meta Wearables DAT
Android/iOS interop) that are unrelated to the HAO-740 hallucinate_app-mobile
scope and far larger than a single ops retry-budget repair cycle. Attempting a
full fix here would require touching dozens of unrelated files across
Swissknife, Mcp-Plus-Plus, and the Meta Wearables DAT submodules, which is out
of scope for this repair task.

## Resolution

Following the established `objective-task janitor` deferral pattern already
used in this backlog for other out-of-mission items (`HAO-684` through
`HAO-696`, deferred with an explicit `Blocked reason`), `HAO-740` is marked
`Status: blocked` in
`hallucinate_app/docs/MULTIMODAL_CONTROL_SURFACE_LOGIC_IDL.todo.md` with a
`Blocked reason` that documents this finding and points back to this receipt.
This keeps the backlog parseable and prevents further retry-budget churn on a
validation command that cannot succeed without a dedicated remediation effort
for the `tests/integration` MCP++/Swissknife descriptor/Meta Wearables DAT
regression.

`HAO-751` is closed out to reflect that the retry-budget bookkeeping (triage,
evidence, and deferral) is complete -- this does **not** claim the underlying
`tests/integration` regression has been fixed. A future dedicated task should
pick up the MCP++ protocol suite, Swissknife descriptor-module exports, and
Meta Wearables DAT Android/iOS interop failures directly.

## Validation Gate

`tests/test_hallucinate_multimodal_control_todo_queue.py::test_hallucinate_multimodal_product_run_defers_stale_scan_and_repair_tasks`
now passes because `HAO-740` (status `blocked`) is excluded from the runnable
stale-task scan, matching the same exclusion already applied to `HAO-684`
through `HAO-696`.

The original guardrail evidence remains tied to
`/home/barberb/lift_coding/data/hallucinate_multimodal_control/discovery/2026-07-08-hao-751-hao-740-retry-budget.md`.
