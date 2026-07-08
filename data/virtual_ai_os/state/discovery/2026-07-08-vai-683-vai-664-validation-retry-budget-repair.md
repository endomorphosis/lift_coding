# VAI-683 Validation Retry-Budget Repair

Date: 2026-07-08
Task: VAI-683
Source task: VAI-664
Goal id: VAIOS-G703
Goal packet: goal_packet/interoperability/swissknife/06921590135c
Goal packet goals: VAIOS-G700, VAIOS-G701, VAIOS-G702, VAIOS-G703, VAIOS-G704, VAIOS-G705, VAIOS-G706

## Finding

The retry-budget evidence in
`data/virtual_ai_os/state/discovery/2026-07-08-vai-683-vai-664-retry-budget.md`
showed three consecutive failures of:

```bash
python -m pytest tests/integration -q
```

Root cause: `tests/integration/test_swissknife_external_ipfs_kit_interop.py::test_swissknife_descriptor_module_exports_interop_contract`
failed with a `FileNotFoundError` for
`swissknife/src/services/mcp/ipfs-kit-mcp-schema-interop-descriptor.ts`. All
three VAI-664 attempts left the Python side of the `interface contract
swissknife external/ipfs_kit` contract
(`src/handsfree/swissknife_ipfs_kit_interop.py`), the discovery/heap records,
and the docs page in place, but never authored the required SwissKnife
TypeScript descriptor module that the module-export test statically inspects
for `SWISSKNIFE_IPFS_KIT_INTEROP_INTERFACE`,
`SWISSKNIFE_IPFS_KIT_INTEROP_DESCRIPTOR`,
`registerSwissKnifeIPFSKitMCPSchemaInterop`,
`createMCPPlusPlusClientWithSwissKnifeIPFSKitInterop`,
`buildSwissKnifeIPFSKitControlSurfaceContract`, and
`buildSwissKnifeIPFSKitInteractionEnvelope`. Every other repository artifact
required by the goal ((`external/ipfs_kit/archive/archive_clutter/fix_scripts/fix_mcp_schema.py`,
`external/ipfs_kit/backup/archive_clutter/fix_scripts/fix_mcp_schema.py`,
`external/ipfs_kit/backup/patches/fixes/fix_mcp_schema.py`,
`external/ipfs_kit/data/deprecations_report.schema.json`,
`swissknife/contracts/control_surface_contract.schema.json`,
`swissknife/contracts/interaction_envelope.schema.json`,
`docs/integration/swissknife-external_ipfs_kit.md`, and the objective
heap/discovery evidence) already existed and validated cleanly.

## Repair

Added `swissknife/src/services/mcp/ipfs-kit-mcp-schema-interop-descriptor.ts`,
mirroring the existing sibling descriptors
(`swissknife/src/services/mcp/meta-wearables-dat-android-display-interop-descriptor.ts`)
and the pre-built `IPFS_KIT_INTERFACE` in `swissknife/src/services/mcp/mcp-plus-plus.ts`.
It exports:

- `SWISSKNIFE_IPFS_KIT_INTEROP_INTERFACE`, a canonical MCP-IDL Profile A
  `MCPPPInterfaceDescriptor` registering the six
  `ipfs_kit.mcp_schema.fix_servers_schema`,
  `ipfs_kit.mcp_schema.validate_deprecations_report`,
  `ipfs_kit.bucket_vfs.export_car`, `ipfs_kit.bucket_vfs.cross_query`,
  `ipfs_kit.dag_pb.encode_node`, and `ipfs_kit.dag_pb.decode_node` operations,
  compatible with `IPFS_KIT_INTERFACE`, `IPFS_ACCELERATE_INTERFACE`, and
  `IPFS_DATASETS_INTERFACE`.
- `SWISSKNIFE_IPFS_KIT_INTEROP_DESCRIPTOR`, bundling the interface, goal
  packet metadata (`VAIOS-G700`-`VAIOS-G706`), schema refs
  (`swissknife/contracts/control_surface_contract.schema.json`,
  `swissknife/contracts/interaction_envelope.schema.json`,
  `swissknife/contracts/mediation_receipt.schema.json`), the
  `external/ipfs_kit` fix-script/deprecations-report/bucket-VFS/DAG-PB
  descriptor paths, and the `MGW-572` / `VAIOS-G703` validation refs.
- `registerSwissKnifeIPFSKitMCPSchemaInterop()` and
  `createMCPPlusPlusClientWithSwissKnifeIPFSKitInterop()` to register the
  descriptor on a live `MCPPlusPlus` runtime registry.
- `buildSwissKnifeIPFSKitControlSurfaceContract()` and
  `buildSwissKnifeIPFSKitInteractionEnvelope()`, TypeScript mirrors of the
  representative control-surface and interaction-envelope payloads the
  Python integration test validates against
  `swissknife/contracts/control_surface_contract.schema.json` and
  `swissknife/contracts/interaction_envelope.schema.json`, preserving the
  scanner-visible `agent_identity`, `allowed_surfaces`, and `arguments_hash`
  norm refs.
- `buildSwissKnifeIPFSKitMCPPlusPlusCompatibilityReceipt()`, matching the
  sibling descriptors' compatibility-receipt shape for consistency.

## Validation Gate

This closes the VAI-664 retry-budget blocker:

```bash
python -m pytest tests/integration/test_swissknife_external_ipfs_kit_interop.py -q
```

now passes 7/7, and the broader
`python -m pytest tests/integration -q` gate no longer fails on the
`swissknife`/`external/ipfs_kit` interop contract. VAI-683 is marked
`Status: completed` in
`implementation_plan/docs/19-virtual-ai-os-submodule-integration.todo.md` so
the supervisor can release VAI-664 from strategy `blocked_tasks`.
