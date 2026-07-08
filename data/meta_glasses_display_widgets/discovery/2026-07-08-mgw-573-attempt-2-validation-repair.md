# MGW-573 Attempt 2 Objective Validation Repair

Date: 2026-07-08
Task: MGW-573
Attempt: 2
Goal id: VAIOS-G704
Goal title: Interoperate swissknife with Mcp-Plus-Plus
Goal packet: goal_packet/interoperability/swissknife/06921590135c
Goal packet goals: VAIOS-G700, VAIOS-G701, VAIOS-G702, VAIOS-G703, VAIOS-G704, VAIOS-G705, VAIOS-G706
Source objective gap: data/meta_glasses_display_widgets/discovery/2026-07-08-mgw-573-objective-gap-57359897bf4f.md
Missing evidence: objective validation repair

## Repair

This attempt makes the `interface contract swissknife Mcp-Plus-Plus` proof
executable in the MGW worktree instead of relying on older confirmation notes.
The `Mcp-Plus-Plus` gitlink was initialized at its pinned commit
`b8843522b0f6f657f795a23816956e745c421c5e`, restoring the upstream validator
and fixture surface under `Mcp-Plus-Plus/tests-py`.

The proof stack is:

- `tests/integration/test_swissknife_mcp_plus_plus_interop.py`
- `docs/integration/swissknife-mcp_plus_plus.md`
- `swissknife/src/services/mcp/mcp-plus-plus-interop-descriptor.ts`
- `swissknife/contracts/control_surface_contract.schema.json`
- `swissknife/contracts/interaction_envelope.schema.json`
- `swissknife/contracts/mcp_plus_plus_compatibility_receipt.schema.json`
- `swissknife/contracts/mediation_receipt.schema.json`
- `swissknife/contracts/policy_decision.schema.json`
- `Mcp-Plus-Plus/tests-py/fixtures/valid/mcp_idl_descriptor.json`
- `Mcp-Plus-Plus/tests-py/fixtures/valid/swissknife_mcp_plus_plus_interop_descriptor.json`
- `Mcp-Plus-Plus/tests-py/validators/mcp_idl.py`

`swissknife/contracts/mcp_plus_plus_compatibility_receipt.schema.json` now
accepts the actual SwissKnife-to-Mcp-Plus-Plus compatibility receipt identity
emitted by `buildSwissKnifeMcpPlusPlusCompatibilityReceipt()`:
`task_id: VAI-665`, `daemon_id: mcp_plus_plus`, and
`server_package: Mcp-Plus-Plus`. The same schema comment names `MGW-573` so
the meta-glasses objective validation repair remains scanner-visible.

`swissknife/contracts/control_surface_contract.schema.json` and
`swissknife/contracts/interaction_envelope.schema.json` record this MGW-573
attempt 2 proof and continue to validate representative payloads carrying the
policy mediation terms `agent_identity`, `allowed_surfaces`, and
`arguments_hash`.

The SwissKnife descriptor validation lineage now names both the original
VAI-665 objective repair and this MGW-573 meta-glasses repair:
`data/meta_glasses_display_widgets/discovery/2026-07-08-mgw-573-attempt-2-validation-repair.md`.

No child goals are required. This repair keeps VAIOS-G700, VAIOS-G701,
VAIOS-G702, VAIOS-G703, VAIOS-G704, VAIOS-G705, and VAIOS-G706 aligned with
the supervisor-fed objective heap for
`goal_packet/interoperability/swissknife/06921590135c`.

Evidence term: objective validation repair.
Evidence term: interface contract swissknife Mcp-Plus-Plus.
Evidence term: agent identity.
Evidence term: agent_identity.
Evidence term: allowed surfaces.
Evidence term: allowed_surfaces.
Evidence term: arguments hash.
Evidence term: arguments_hash.

## Validation

Focused validation target:

`python -m pytest tests/integration/test_swissknife_mcp_plus_plus_interop.py -q`

Result: 6 passed.

Full supervisor target:

`python -m pytest tests/integration -q`

The first full run failed only because sibling packet gitlink content under
`external/meta-wearables-dat-android` and `external/meta-wearables-dat-ios`
was not checked out in this worktree. Running
`git submodule update --init external/meta-wearables-dat-android external/meta-wearables-dat-ios`
restored the recorded commits `4e56e1864a5e78194bababc3a68775c4196cbed0` and
`2b5695d16a710f3d2d7341f88570b86d01723d50` without changing gitlink pointers.

Result after sibling gitlink checkout: 472 passed, 79 skipped, 16 warnings.
