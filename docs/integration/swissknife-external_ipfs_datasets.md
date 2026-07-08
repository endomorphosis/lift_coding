# SwissKnife / external/ipfs_datasets Interop

MGW-571 repairs the VAIOS-G702 objective validation gap for the shared
`goal_packet/interoperability/swissknife/06921590135c` packet covering
VAIOS-G700, VAIOS-G701, VAIOS-G702, VAIOS-G703, VAIOS-G704, VAIOS-G705, and
VAIOS-G706.

The repaired `interface contract swissknife external/ipfs_datasets` path is:

- `external/ipfs_datasets/.tools/ipfs_kit_py/data/deprecations_report.schema.json`
  defines the JSON Schema for the nested `ipfs_kit_py` deprecations report,
  requiring `report_version`, `generated_at`, `deprecated`, `summary`,
  `policy`, and `raw` top-level keys that SwissKnife validates before
  consuming API-deprecation data.
- `external/ipfs_datasets/.tools/ipfs_kit_py/docs/implementation/BUCKET_VFS_INTERFACES_COMPLETE.md`
  documents the Bucket VFS CLI/MCP interface, including the `bucket_create`,
  `bucket_list`, `bucket_delete`, `bucket_add_file`, `bucket_export_car`,
  `bucket_cross_query`, `bucket_get_info`, and `bucket_status` MCP tools that
  SwissKnife's bucket-vfs control surface can route to.
- `external/ipfs_datasets/.tools/ipfs_kit_py/examples/demo_bucket_vfs_interfaces.py`
  is a dependency-light demo that exposes the same CLI commands and MCP tool
  names as parseable Python constants, plus `demo_cli_interface()`,
  `demo_mcp_api()`, and `build_demo_report()` evidence for S3-like bucket
  semantics, CAR export, and cross-bucket SQL queries.
- `external/ipfs_datasets/.tools/ipfs_kit_py/examples/demo_unified_bucket_interface.py`
  demonstrates the `UnifiedBucketInterface`, `BackendType`, `BucketType`, and
  `VFSStructureType` imports used for multi-backend buckets. The static
  contract verifies the demo uses `initialize()`, `create_backend_bucket()`,
  `add_content_pin()`, `list_backend_buckets()`, `get_vfs_composition()`,
  `sync_bucket_indices()`, and `query_across_backends()` across PARQUET,
  ARROW, S3, SSHFS, and GDRIVE backends.
- `src/handsfree/swissknife_ipfs_datasets_interop.py` statically discovers
  those four descriptors without importing `external/ipfs_datasets` Python,
  verifies the required deprecations-report keys, Bucket VFS MCP tool names,
  CLI commands, demo functions/classes, unified bucket imports, methods, and
  backends, and builds a deterministic `SwissKnifeIPFSDatasetsHandoff`
  receipt.
- `swissknife/src/services/mcp/ipfs-datasets-bucket-vfs-interop-descriptor.ts`
  exports `SWISSKNIFE_IPFS_DATASETS_INTEROP_INTERFACE` (a canonical MCP-IDL
  Profile A `MCPPPInterfaceDescriptor`) and
  `SWISSKNIFE_IPFS_DATASETS_INTEROP_DESCRIPTOR`, plus
  `registerSwissKnifeIPFSDatasetsBucketVFSInterop()` /
  `createMCPPlusPlusClientWithSwissKnifeIPFSDatasetsInterop()` to register
  the descriptor on a live `MCPPlusPlus` runtime registry alongside the
  pre-built `IPFS_KIT_INTERFACE`, and
  `buildSwissKnifeIPFSDatasetsControlSurfaceContract()` /
  `buildSwissKnifeIPFSDatasetsInteractionEnvelope()` to build representative
  control-surface and interaction-envelope payloads.
- `swissknife/contracts/control_surface_contract.schema.json` and
  `swissknife/contracts/interaction_envelope.schema.json` validate those
  SwissKnife-to-`external/ipfs_datasets` payloads while preserving the
  scanner-visible `agent_identity`, `allowed_surfaces`, and `arguments_hash`
  norm refs. `swissknife/contracts/mediation_receipt.schema.json` remains the
  receipt schema ref advertised by the descriptor.

## Runtime Handoff

1. `SWISSKNIFE_IPFS_DATASETS_INTEROP_INTERFACE` registers seven
   `ipfs_datasets.*` operations: `bucket_vfs.create_bucket`,
   `bucket_vfs.add_file`, `bucket_vfs.export_car`, `bucket_vfs.cross_query`,
   `unified_bucket.create_backend_bucket`, `unified_bucket.sync_indices`, and
   `deprecations.validate_report`.
2. A SwissKnife control-surface event, for example `cross_query`, resolves to
   `ipfs_datasets.bucket_vfs.cross_query` via the
   `swissknife.ipfs_datasets.data-service` control surface, mediated by the
   `policy:swissknife:ipfs-datasets-bucket-vfs-interop` policy bundle.
3. `src/handsfree/swissknife_ipfs_datasets_interop.py` builds a deterministic,
   content-addressed receipt (`sha256:` content CID) for the Bucket VFS
   handoff via `build_swissknife_ipfs_datasets_handoff()`, re-deriving the
   same Bucket VFS MCP tools and unified bucket backends advertised by the
   TypeScript descriptor.

## Validation Evidence

Validation evidence lives in
`tests/integration/test_swissknife_external_ipfs_datasets_interop.py`. It
verifies the Bucket VFS descriptors under `external/ipfs_datasets` exist and
declare the expected schema keys/tools/commands/imports/methods/backends,
exercises the Python discovery and handoff builder, statically inspects the
SwissKnife TypeScript descriptor module for the expected exports and
goal-packet metadata, validates representative SwissKnife control-surface and
interaction-envelope payloads, and asserts this objective validation repair is
recorded in
`data/meta_glasses_display_widgets/discovery/2026-07-08-mgw-571-objective-validation-repair.md`
and the objective heap
(`implementation_plan/docs/23-virtual-ai-os-objective-goal-heap.md`).
