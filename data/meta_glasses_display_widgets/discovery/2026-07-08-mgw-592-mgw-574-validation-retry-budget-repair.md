# MGW-592 Validation Retry-Budget Repair

Date: 2026-07-08
Task: MGW-592
Source task: MGW-574

## Finding

The retry-budget evidence in
`data/meta_glasses_display_widgets/state/discovery/2026-07-08-mgw-592-mgw-574-retry-budget.md`
showed three consecutive failures of:

```bash
python -m pytest tests/integration -q
```

Investigation across the three MGW-574 attempt logs
(`data/meta_glasses_display_widgets/state/lane-0/implementation_logs/mgw-574-attempt-1.log`,
`-attempt-2.log`, `-attempt-3.log`) showed MGW-574's own deliverable
(`tests/integration/test_swissknife_external_meta_wearables_dat_android_interop.py`)
passing cleanly every time. The retry budget was actually exhausted by two
separate, pre-existing regressions in the `swissknife` submodule that were
unrelated to MGW-574's diff but still made the shared
`python -m pytest tests/integration -q` validation command fail:

1. **Shared contract `$comment` overwrite.** `swissknife/contracts/mediation_receipt.schema.json`
   is a shared evidence surface for every task in
   `goal_packet/interoperability/swissknife/06921590135c` (VAIOS-G700..G706).
   The convention (visible in `control_surface_contract.schema.json` and
   `interaction_envelope.schema.json`) is to *append* each task's stamp to the
   existing `$comment` string. A prior update to `mediation_receipt.schema.json`
   replaced the `$comment` outright instead of appending, dropping the
   `MGW-571 objective validation repair` stamp required by
   `tests/integration/test_swissknife_external_ipfs_datasets_interop.py::test_swissknife_control_surface_and_interaction_envelope_validate_for_ipfs_datasets`.
2. **Deleted goal-packet interop descriptors.** A large legitimate swissknife
   refactor (`chore: add pending swissknife staged changes`) was merged
   (`06889432 Merge commit 'f76e6ee6' into merge/swissknife-into-origin-main`)
   with a divergent feature branch. Because the refactor branch deleted files
   that the feature branch had not touched, the 3-way merge kept those
   deletions, silently dropping
   `swissknife/src/services/mcp/ipfs-accelerate-duckdb-interop-descriptor.ts`,
   `ipfs-datasets-bucket-vfs-interop-descriptor.ts`,
   `ipfs-kit-mcp-schema-interop-descriptor.ts`,
   `mcp-plus-plus-interop-descriptor.ts`, and
   `meta-wearables-dat-ios-display-interop-descriptor.ts` from the checked out
   commit, which broke
   `test_swissknife_descriptor_module_exports_interop_contract` in five sibling
   interop test files across the same goal packet.

The same merge also dropped `swissknife/web/src/browser-main.ts`,
`swissknife/src/services/mcp-plus-plus.ts`,
`swissknife/src/services/mcp-plus-plus-connector.ts`,
`swissknife/src/services/meta-glasses-mobile-orb-bridge.ts`,
`swissknife/src/services/meta-glasses-display-orb-adapter.ts`,
`swissknife/src/services/meta-glasses-widget-compiler.ts`,
`swissknife/src/services/ipfs-interface-registry.ts`, and
`swissknife/src/services/mcp-ipfs-kit-tools-manifest.json` (all moved into
`src/services/mcp/`, `src/services/glasses/`, `src/services/ipfs/`, or
`web/legacy-archive/src/` by the same refactor while the outer harness's
`tests/integration/test_desktop_app_integrations.py`,
`tests/integration/test_mcp_plus_plus.py`,
`tests/integration/test_mcp_pp_connector.py`,
`tests/integration/test_glasses_control_plane.py`, and
`tests/integration/test_mcp_kit_dashboard_sync.py` still expected the old flat
paths). These failures were unrelated to any goal-packet interoperability
track but were blocking the shared `python -m pytest tests/integration -q`
gate used by MGW-574/MGW-592 and effectively every other task in this
backlog, so they are fixed here as part of unblocking the shared validation
command (this task's track is `ops`).

## Repair

- Fast-forwarded the `swissknife` submodule to
  `567939bd HAO-730: add sibling goal-packet interop descriptors and fix
  drifted evidence`, an already-authored fix (reachable from the current
  submodule HEAD) that restores the five missing goal-packet interop
  descriptors and re-appends the dropped `MGW-571 objective validation repair`
  stamp to `mediation_receipt.schema.json`.
- Restored `swissknife/web/src/browser-main.ts` from its last known-good
  pre-archive content (`d009156f`, the commit immediately preceding the
  destructive merge).
- Restored `swissknife/src/services/mcp-plus-plus.ts` and
  `mcp-plus-plus-connector.ts` as thin re-export shims (same pattern already
  used in swissknife history) pointing at the current
  `src/services/mcp/mcp-plus-plus*.ts` implementations while preserving the
  legacy literal-string contract the older assertions still check for.
- Added thin re-export shims at the old flat `src/services/` paths for
  `meta-glasses-mobile-orb-bridge.ts`, `meta-glasses-display-orb-adapter.ts`,
  `meta-glasses-widget-compiler.ts`, and `ipfs-interface-registry.ts`, which
  moved into `src/services/glasses/` and `src/services/ipfs/`.
- Added `src/services/mcp-ipfs-kit-tools-manifest.json` as a synced copy of
  the canonical `src/services/ipfs/mcp-ipfs-kit-tools-manifest.json` so the
  cross-repo dashboard/server manifest guard has a copy at the path the outer
  test expects.
- Committed all of the above inside the `swissknife` submodule and updated
  the outer repo's `swissknife` gitlink pointer.
- Cleared `MGW-574` from
  `data/meta_glasses_display_widgets/state/lane-0/meta_glasses_display_lane_0_strategy.json`'s
  `blocked_tasks` list.

## Validation Gate

```bash
python -m pytest tests/integration -q
```

Result: `464 passed, 79 skipped` (0 failed, 0 errors), re-run twice for
stability. This closes the MGW-574 retry-budget blocker and unblocks every
other task in this backlog that shares the same validation command.
