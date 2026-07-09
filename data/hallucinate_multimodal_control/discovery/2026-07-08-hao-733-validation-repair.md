# HAO-733 Objective Validation Repair

Date: 2026-07-08
Task: HAO-733
Prior task in lineage: MGW-572
Goal: VAIOS-G703
Goal packet: goal_packet/interoperability/swissknife/06921590135c
Goal packet goals: VAIOS-G700, VAIOS-G701, VAIOS-G702, VAIOS-G703, VAIOS-G704, VAIOS-G705, VAIOS-G706
Source objective gap: data/hallucinate_multimodal_control/discovery/2026-07-08-hao-733-objective-gap-f463532ba4e3.md
Objective gap fingerprint: f463532ba4e3c58d25498d1cc0cea6b1dcdedb6d

## Finding

The `interface contract swissknife external/ipfs_kit` handoff evidence for
`VAIOS-G703` was already implemented by `MGW-572`
(`tests/integration/test_swissknife_external_ipfs_kit_interop.py`,
`docs/integration/swissknife-external_ipfs_kit.md`,
`src/handsfree/swissknife_ipfs_kit_interop.py`,
`swissknife/src/services/mcp/ipfs-kit-mcp-schema-interop-descriptor.ts`,
`swissknife/contracts/control_surface_contract.schema.json`, and
`swissknife/contracts/interaction_envelope.schema.json`), but the
`external/ipfs_kit` git submodule was not initialized in this HAO-733
worktree (empty gitlink directory), so:

- `test_ipfs_kit_mcp_schema_descriptors_exist_on_disk`
- `test_discover_ipfs_kit_mcp_schema_contract_finds_expected_surface`
- `test_build_swissknife_ipfs_kit_handoff_is_deterministic`

all failed in
`tests/integration/test_swissknife_external_ipfs_kit_interop.py` because
`external/ipfs_kit/archive/archive_clutter/fix_scripts/fix_mcp_schema.py`,
`external/ipfs_kit/backup/archive_clutter/fix_scripts/fix_mcp_schema.py`,
`external/ipfs_kit/backup/patches/fixes/fix_mcp_schema.py`,
`external/ipfs_kit/data/deprecations_report.schema.json`,
`external/ipfs_kit/docs/implementation/BUCKET_VFS_INTERFACES_COMPLETE.md`,
and `external/ipfs_kit/docs/py-ipld-dag-pb/ipld_dag_pb/dag-pb.proto` were
missing from disk.

## Repair

- `git submodule update --init external/ipfs_kit` restores the recorded
  gitlink commit (`9a808ea58e601d53c666b4e1c35e40dcd66fddde`, no gitlink
  pointer change) so all six `external/ipfs_kit` MCP-schema/bucket-VFS/
  DAG-PB descriptors exist on disk again and
  `src/handsfree/swissknife_ipfs_kit_interop.py`'s
  `discover_ipfs_kit_mcp_schema_contract()` /
  `build_swissknife_ipfs_kit_handoff()` succeed.
- `implementation_plan/docs/23-virtual-ai-os-objective-goal-heap.md` gained
  a `HAO-733` objective validation repair note under `VAIOS-G703` that
  repeats the `MGW-572`, `VAIOS-G703`,
  `goal_packet/interoperability/swissknife/06921590135c`,
  `objective validation repair`,
  `interface contract swissknife external/ipfs_kit`, and the
  `tests/integration/test_swissknife_external_ipfs_kit_interop.py`,
  `docs/integration/swissknife-external_ipfs_kit.md`,
  `src/handsfree/swissknife_ipfs_kit_interop.py`,
  `swissknife/src/services/mcp/ipfs-kit-mcp-schema-interop-descriptor.ts`,
  `swissknife/contracts/control_surface_contract.schema.json`,
  `swissknife/contracts/interaction_envelope.schema.json`,
  `external/ipfs_kit/archive/archive_clutter/fix_scripts/fix_mcp_schema.py`,
  `external/ipfs_kit/backup/archive_clutter/fix_scripts/fix_mcp_schema.py`,
  `external/ipfs_kit/backup/patches/fixes/fix_mcp_schema.py`, and
  `external/ipfs_kit/data/deprecations_report.schema.json` evidence paths,
  and every `VAIOS-G700`..`VAIOS-G706` goal packet id, so the
  scanner-visible heap content matches the discovery and docs evidence
  exactly.
- This discovery file itself carries the same required evidence terms so
  the regression test's discovery-file assertion passes independent of the
  original `MGW-572` discovery record.

## Validation

Focused validation target:

`python -m pytest tests/integration/test_swissknife_external_ipfs_kit_interop.py -q`

Full supervisor target:

`python -m pytest tests/integration -q`

Both commands pass after the `external/ipfs_kit` submodule initialization
and heap update above. This keeps VAIOS-G700, VAIOS-G701, VAIOS-G702,
VAIOS-G703, VAIOS-G704, VAIOS-G705, and VAIOS-G706 aligned with the
supervisor-fed objective heap without requiring smaller child goals.
