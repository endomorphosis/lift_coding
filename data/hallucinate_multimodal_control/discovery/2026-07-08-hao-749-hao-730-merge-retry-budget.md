# HAO-749 Merge Retry-Budget Finding: HAO-730

Date: 2026-07-08
Source task: HAO-730
Follow-up task: HAO-749
Retry budget: 3
Observed consecutive merge failures: 3

## Evidence

- Failed command: `git merge (main_checkout_dirty_conflict)`
- Attempts: 1, 2, 4
- Logs: /home/barberb/lift_coding/data/hallucinate_multimodal_control/state/implementation_logs/hao-730-attempt-1.log, /home/barberb/lift_coding/data/hallucinate_multimodal_control/state/implementation_logs/hao-730-attempt-2.log, /home/barberb/lift_coding/data/hallucinate_multimodal_control/state/implementation_logs/hao-730-attempt-4.log
- Merge reason: `main_checkout_dirty_conflict`
- Dirty paths: hallucinate_app
- Branch: `implementation/hao-730-attempt-4-1783529528`
- Main worktree: `/home/barberb/lift_coding`


## Guardrail Result

The accelerator backlog refinery classified this as backlog work instead of
allowing another implementation attempt to loop on the same failure. The source
task is added to the strategy `blocked_tasks` list and the follow-up task below
is appended for normal daemon parsing.

## Resolution

The HAO-730 implementation itself was valid: attempts 1, 2, and 4 all reached
validation-passed states in their logs. The repeated merge failure was caused by
`main_checkout_dirty_conflict` on `hallucinate_app` in the main checkout, not by
a semantic conflict in the SwissKnife/mobile contract files.

This HAO-749 repair records the HAO-730 attempt-4 validation evidence in:

- `data/hallucinate_multimodal_control/discovery/2026-07-08-hao-730-attempt-4-validation-confirmation.md`
- `implementation_plan/docs/23-virtual-ai-os-objective-goal-heap.md`
- `tests/integration/test_swissknife_mobile_interop.py`
- `docs/integration/swissknife-mobile.md`
- `mobile/src/orb/metaGlassesOrbDescriptors.js`
- `mobile/src/utils/metaWearablesDatDisplayWidgetContract.js`
- `swissknife/contracts/control_surface_contract.schema.json`
- `swissknife/contracts/interaction_envelope.schema.json`

The dirty `hallucinate_app` path traced to an uncommitted nested gitlink chain
under `hallucinate_app/ipfs_accelerate_py`. The concrete semantic pointer was
inside:

`hallucinate_app/ipfs_accelerate_py/ipfs_datasets_py/.tools/ipfs_kit_py/ipfs_accelerate_py/ipfs_datasets_py/.tools/ipfs_kit_py`

That pointer moved from `0b9fb4db5d0ae7411d0580164389397b158e5713` to
`9a808ea58e601d53c666b4e1c35e40dcd66fddde`, matching the newer `ipfs_kit_py`
revision already used by the HAO-730/HAO-731 branch family. The repair committed
that pointer in its owning nested repository and propagated the gitlinks outward:

- `f65b96991` in the nested `ipfs_datasets_py` repository records the
  `.tools/ipfs_kit_py` pointer.
- `a3080aae` in the nested `.tools/ipfs_kit_py/ipfs_accelerate_py` repository
  records the repaired `ipfs_datasets_py` pointer.
- `a4a3fea3` in the nested `.tools/ipfs_kit_py` repository records the repaired
  `ipfs_accelerate_py` pointer.
- `69f57024d` in `hallucinate_app/ipfs_accelerate_py/ipfs_datasets_py` records
  the repaired `.tools/ipfs_kit_py` pointer.
- `ba14a7ba` in `hallucinate_app/ipfs_accelerate_py` records the repaired
  `ipfs_datasets_py` pointer.
- `4382360` in `hallucinate_app` records the repaired `ipfs_accelerate_py`
  pointer.

`ipfs-accelerate-agent-merge-resolver --events-path ... --apply` was not run for
this repair because the recorded blocker is `main_checkout_dirty_conflict`, not
an unresolved semantic merge conflict. After the nested gitlink propagation,
`git -C hallucinate_app status --porcelain=v1` is clean and the outer worktree
contains only this repair's tracked evidence changes plus the updated
`hallucinate_app` gitlink.

## Validation

- `test -f /home/barberb/lift_coding/data/hallucinate_multimodal_control/discovery/2026-07-08-hao-749-hao-730-merge-retry-budget.md`
- `python -m pytest tests/integration/test_swissknife_mobile_interop.py -q`
  passed with 7 tests.
- `python -m pytest tests/integration -q` passed with 457 passed, 86 skipped,
  and 16 warnings after initializing the recorded `Mcp-Plus-Plus`,
  `external/ipfs_kit`, `external/meta-wearables-dat-android`, and
  `external/meta-wearables-dat-ios` gitlink submodules.
- `git -C hallucinate_app status --porcelain=v1` is clean in this HAO-749
  repair worktree after the nested gitlink commits.
