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

The `external/meta-wearables-dat-android` and `external/meta-wearables-dat-ios`
Git submodules were registered in `.gitmodules` and pinned in the Git index,
but had never been checked out (`git submodule status` reported both with a
leading `-`, meaning uninitialized). Every MGW-574 attempt therefore failed
`tests/integration/test_swissknife_external_meta_wearables_dat_android_interop.py`
(and the sibling
`tests/integration/test_swissknife_external_meta_wearables_dat_ios_interop.py`,
`tests/integration/test_external_meta_wearables_dat_android_external_ipfs_*_interop.py`
files) with `SwissKnifeMetaWearablesDATAndroidInteropError: ... Display
descriptors missing`, because the `.cursor/rules/*.mdc` and
`samples/DisplayAccess/app/src/main/...` files the discovery/interop contract
reads from disk did not exist on the worktree filesystem.

## Repair

Initialized the missing submodules for this worktree:

```bash
git submodule update --init external/meta-wearables-dat-android external/meta-wearables-dat-ios
```

This checks out the pinned commits
(`4e56e1864a5e78194bababc3a68775c4196cbed0` for
`external/meta-wearables-dat-android` and
`2b5695d16a710f3d2d7341f88570b86d01723d50` for
`external/meta-wearables-dat-ios`) and materializes the
`display-access.mdc`, `session-lifecycle.mdc`, `permissions-registration.mdc`
rule docs plus the `samples/DisplayAccess/app/src/main/AndroidManifest.xml`
and `DisplayViewModel.kt` sample sources that
`src/handsfree/swissknife_meta_wearables_dat_android_interop.py` and
`tests/integration/test_swissknife_external_meta_wearables_dat_android_interop.py`
require.

No source, contract, or documentation edits were required: the
`swissknife/contracts/control_surface_contract.schema.json`,
`swissknife/contracts/interaction_envelope.schema.json`,
`swissknife/contracts/mcp_plus_plus_compatibility_receipt.schema.json`,
`swissknife/contracts/mediation_receipt.schema.json`,
`docs/integration/swissknife-external_meta_wearables_dat_android.md`, and
`implementation_plan/docs/23-virtual-ai-os-objective-goal-heap.md` outputs
already carried the HAO-735/VAIOS-G705 content the tests assert against; the
blocker was purely the uninitialized submodule checkout.

## Validation Gate

This closes the MGW-574 retry-budget blocker:

```bash
python -m pytest tests/integration/test_swissknife_external_meta_wearables_dat_android_interop.py -q
```

now passes all 7 tests. A full
`python -m pytest tests/integration -q` run in this worktree produces the
exact same failing/error test set (`66 failed`, `49 errors`) as an unmodified
checkout of the base repository, confirming every remaining failure is a
pre-existing, unrelated baseline condition and that the MGW-574 blocker
(meta-wearables-dat-android interop) is fully repaired. MGW-574 can be
released from the lane strategy `blocked_tasks` list.
