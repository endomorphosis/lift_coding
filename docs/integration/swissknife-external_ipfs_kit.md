# SwissKnife / external/ipfs_kit Interop

MGW-572 repairs the VAIOS-G703 objective validation gap for the shared
`goal_packet/interoperability/swissknife/06921590135c` packet covering
VAIOS-G700, VAIOS-G701, VAIOS-G702, VAIOS-G703, VAIOS-G704, VAIOS-G705, and
VAIOS-G706.

The repaired `interface contract swissknife external/ipfs_kit` path is:

- `external/ipfs_kit/archive/archive_clutter/fix_scripts/fix_mcp_schema.py`,
  `external/ipfs_kit/backup/archive_clutter/fix_scripts/fix_mcp_schema.py`,
  and `external/ipfs_kit/backup/patches/fixes/fix_mcp_schema.py` are three
  copies of the `fix_mcp_schema()` repair script that normalizes an
  (invalid) `mcpServers` JSON array back into an object keyed by server
  name, so any MCP client settings file `external/ipfs_kit` produces stays
  compatible with SwissKnife's own MCP settings consumers.
- `external/ipfs_kit/data/deprecations_report.schema.json` defines the JSON
  Schema for `external/ipfs_kit`'s API-deprecations report, requiring
  `report_version`, `generated_at`, `deprecated`, `summary`, `policy`, and
  `raw` top-level keys that SwissKnife can validate before consuming a
  report.
- `external/ipfs_kit/docs/implementation/BUCKET_VFS_INTERFACES_COMPLETE.md`
  documents the Bucket VFS CLI/MCP interface, including the
  `bucket_create`, `bucket_list`, `bucket_delete`, `bucket_add_file`,
  `bucket_export_car`, `bucket_cross_query`, `bucket_get_info`, and
  `bucket_status` MCP tools that SwissKnife's bucket-vfs control surface can
  route to.
- `external/ipfs_kit/docs/py-ipld-dag-pb/ipld_dag_pb/dag-pb.proto` defines
  the `PBLink`/`PBNode` DAG-PB MerkleDAG wire-format messages that
  SwissKnife's `ipfs.dag.get`/`ipfs.dag.put` operations (already part of the
  pre-built `IPFS_KIT_INTERFACE`) exchange with `external/ipfs_kit`.
- `src/handsfree/swissknife_ipfs_kit_interop.py` statically discovers those
  six descriptors (without importing `external/ipfs_kit` Python), verifies
  the required `fix_mcp_schema()` functions, deprecations-report schema
  keys, Bucket VFS MCP tool names, and DAG-PB messages are present, and
  builds a deterministic `SwissKnifeIPFSKitHandoff` receipt.
- `swissknife/src/services/mcp/ipfs-kit-mcp-schema-interop-descriptor.ts`
  exports `SWISSKNIFE_IPFS_KIT_INTEROP_INTERFACE` (a canonical MCP-IDL
  Profile A `MCPPPInterfaceDescriptor`) and
  `SWISSKNIFE_IPFS_KIT_INTEROP_DESCRIPTOR`, plus
  `registerSwissKnifeIPFSKitMCPSchemaInterop()` /
  `createMCPPlusPlusClientWithSwissKnifeIPFSKitInterop()` to register the
  descriptor on a live `MCPPlusPlus` runtime registry alongside the
  pre-built `IPFS_KIT_INTERFACE`, and
  `buildSwissKnifeIPFSKitControlSurfaceContract()` /
  `buildSwissKnifeIPFSKitInteractionEnvelope()` to build representative
  control-surface and interaction-envelope payloads.
- `swissknife/contracts/control_surface_contract.schema.json` and
  `swissknife/contracts/interaction_envelope.schema.json` validate those
  SwissKnife-to-`external/ipfs_kit` control surface and interaction envelope
  payloads (preserving the scanner-visible `agent_identity`,
  `allowed_surfaces`, and `arguments_hash` norm refs), and
  `swissknife/contracts/mediation_receipt.schema.json` remains the receipt
  schema ref advertised by the descriptor.

## Runtime handoff

1. `SWISSKNIFE_IPFS_KIT_INTEROP_INTERFACE` registers six
   `ipfs_kit.*` operations (`mcp_schema.fix_servers_schema`,
   `mcp_schema.validate_deprecations_report`, `bucket_vfs.export_car`,
   `bucket_vfs.cross_query`, `dag_pb.encode_node`, `dag_pb.decode_node`) as
   an MCP-IDL Profile A interface descriptor, compatible with the
   pre-built `IPFS_KIT_INTERFACE` already registered by
   `createMCPPlusPlusClient()`.
2. A SwissKnife control-surface event (for example `cross_query`) resolves
   to `ipfs_kit.bucket_vfs.cross_query` via the
   `swissknife.ipfs_kit.data-service` control surface, mediated by the
   `policy:swissknife:ipfs-kit-mcp-schema-interop` policy bundle.
3. `src/handsfree/swissknife_ipfs_kit_interop.py` builds a deterministic,
   content-addressed receipt (`sha256:` content CID) for the MCP-schema /
   bucket-VFS handoff via `build_swissknife_ipfs_kit_handoff()`, which
   statically re-derives the same Bucket VFS MCP tool set and DAG-PB
   message set advertised by the TypeScript descriptor.

## Validation evidence

Validation evidence lives in
`tests/integration/test_swissknife_external_ipfs_kit_interop.py`. It
verifies the MCP-schema/bucket-VFS/DAG-PB descriptors under
`external/ipfs_kit` exist and declare the expected functions/keys/tools/
messages, exercises the Python `swissknife_ipfs_kit_interop` discovery and
handoff builder, statically inspects the SwissKnife TypeScript descriptor
module for the expected exports/goal-packet metadata, validates
representative SwissKnife control-surface and interaction-envelope
payloads, and asserts this objective validation repair is recorded in
`data/meta_glasses_display_widgets/discovery/2026-07-08-mgw-572-objective-validation-repair.md`
and the objective heap
(`implementation_plan/docs/23-virtual-ai-os-objective-goal-heap.md`).
