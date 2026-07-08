# MGW-588 Merge Retry-Budget Finding: MGW-573

Date: 2026-07-08
Source task: MGW-573
Follow-up task: MGW-588
Retry budget: 3
Observed consecutive merge failures: 3

## Evidence

- Failed command: `git merge (main_checkout_dirty_conflict)`
- Attempts: 1, 2, 3
- Logs: /home/barberb/lift_coding/data/meta_glasses_display_widgets/state/implementation_logs/mgw-573-attempt-1.log, /home/barberb/lift_coding/data/meta_glasses_display_widgets/state/implementation_logs/mgw-573-attempt-3.log
- Merge reason: `main_checkout_dirty_conflict`
- Dirty paths: external/ipfs_datasets, hallucinate_app
- Branch: `implementation/mgw-573-attempt-3-1783527337`
- Main worktree: `/home/barberb/lift_coding`


## Guardrail Result

The accelerator backlog refinery classified this as backlog work instead of
allowing another implementation attempt to loop on the same failure. The source
task is added to the strategy `blocked_tasks` list and the follow-up task below
is appended for normal daemon parsing.

## Repair

MGW-588 confirms the MGW-573 objective validation repair is not blocked by a
semantic merge conflict in the SwissKnife/Mcp-Plus-Plus interop surface. The
intended evidence stack is present in this worktree, anchored by
`data/meta_glasses_display_widgets/discovery/2026-07-08-mgw-573-objective-gap-57359897bf4f.md`:

- `tests/integration/test_swissknife_mcp_plus_plus_interop.py`
- `docs/integration/swissknife-mcp_plus_plus.md`
- `swissknife/src/services/mcp/mcp-plus-plus-interop-descriptor.ts`
- `swissknife/contracts/control_surface_contract.schema.json`
- `swissknife/contracts/interaction_envelope.schema.json`
- `swissknife/contracts/mcp_plus_plus_compatibility_receipt.schema.json`
- `Mcp-Plus-Plus/tests-py/fixtures/valid/mcp_idl_descriptor.json`
- `Mcp-Plus-Plus/tests-py/fixtures/valid/swissknife_mcp_plus_plus_interop_descriptor.json`

The repeated merge failure was `main_checkout_dirty_conflict`: the main
checkout at `/home/barberb/lift_coding` had dirty `external/ipfs_datasets` and
`hallucinate_app` submodule chains before MGW-573 could be merged. Inspection
showed those dirty paths were unrelated to the MGW-573 SwissKnife/Mcp-Plus-Plus
implementation:

- `external/ipfs_datasets` was dirty through nested
  `.tools/ipfs_kit_py/examples/demo_bucket_vfs_interfaces.py`, a Bucket VFS
  demo staged for the separate HAO-738/external ipfs_kit evidence lane.
- `hallucinate_app` was dirty through nested `ipfs_accelerate_py` and
  `ipfs_datasets_py` submodules, including broad deletion state inside legacy
  CEC/multimedia nested repositories. Those changes are not part of MGW-573 and
  were not reverted or folded into this repair.

Because the blocker is a dirty main checkout rather than a semantic conflict,
`ipfs-accelerate-agent-merge-resolver --events-path ... --apply` is not the
appropriate repair mechanism for this task. The merge can be retried after the
dirty unrelated submodule chains are isolated by their owning tasks or cleaned
by the supervisor.

MGW-588 records the MGW-573 repair lineage in the objective heap and interop
fixtures so the supervisor can release MGW-573 from `blocked_tasks` without
rerunning the same merge loop.

Scanner terms: MGW-573, MGW-588, VAI-665, VAIOS-G704,
`goal_packet/interoperability/swissknife/06921590135c`, objective validation
repair, interface contract swissknife Mcp-Plus-Plus,
`tests/integration/test_swissknife_mcp_plus_plus_interop.py`,
`swissknife/src/services/mcp/mcp-plus-plus-interop-descriptor.ts`,
`swissknife/contracts/control_surface_contract.schema.json`,
`swissknife/contracts/interaction_envelope.schema.json`,
`Mcp-Plus-Plus/tests-py/fixtures/valid/mcp_idl_descriptor.json`,
`data/meta_glasses_display_widgets/discovery/2026-07-08-mgw-573-objective-gap-57359897bf4f.md`.
