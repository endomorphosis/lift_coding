# external/meta-wearables-dat-android to external/ipfs_kit Interop

Task: VAI-670
Goal: VAIOS-G711
Packet: goal_packet/interoperability/external/6595cbbfadb9
Evidence: objective validation repair

This contract proves `external/meta-wearables-dat-android` interoperates with
`external/ipfs_kit` through an importable contract, interface descriptors,
runtime handoff behavior, and an integration test:

- `tests/integration/test_external_meta_wearables_dat_android_external_ipfs_kit_interop.py`
- `src/handsfree/meta_wearables_dat_android_ipfs_kit_interop.py`
- `docs/integration/external_meta_wearables_dat_android-external_ipfs_kit.md`
- interface contract external/meta-wearables-dat-android external/ipfs_kit
- `external/meta-wearables-dat-android/.cursor/rules/display-access.mdc`
- `external/meta-wearables-dat-android/.cursor/rules/session-lifecycle.mdc`
- `external/meta-wearables-dat-android/.cursor/rules/permissions-registration.mdc`
- `external/meta-wearables-dat-android/samples/DisplayAccess/app/src/main/AndroidManifest.xml`
- `external/meta-wearables-dat-android/samples/DisplayAccess/app/src/main/java/com/meta/wearable/dat/externalsampleapps/displayaccess/display/DisplayViewModel.kt`
- `external/ipfs_kit/archive/archive_clutter/fix_scripts/fix_mcp_schema.py`
- `external/ipfs_kit/backup/archive_clutter/fix_scripts/fix_mcp_schema.py`
- `external/ipfs_kit/backup/patches/fixes/fix_mcp_schema.py`
- `external/ipfs_kit/data/deprecations_report.schema.json`
- `external/ipfs_kit/docs/implementation/BUCKET_VFS_INTERFACES_COMPLETE.md`
- `external/ipfs_kit/docs/py-ipld-dag-pb/ipld_dag_pb/dag-pb.proto`
- `external/ipfs_kit/ipfs_kit_py/bucket_vfs_cli.py`
- `external/ipfs_kit/mcp/bucket_vfs_mcp_tools.py`
- `external/ipfs_kit/ipfs_kit_py/mcp/servers/enhanced_integrated_mcp_server.py`
- `external/ipfs_kit/ipfs_kit_py/bucket_vfs_manager.py`

## Contract

The source surface is the Meta Wearables DAT Android Display/session flow. The
validated descriptors prove these terms are present:

- `Wearables.createSession`
- `addDisplay`
- `DisplayState.STARTED`
- `sendContent`
- `flexBox`
- `Wearables.startRegistration`
- `checkPermissionStatus`
- `RequestPermissionContract`
- `PermissionStatus.Granted`
- Android manifest metadata keys `com.meta.wearable.mwdat.APPLICATION_ID` and
  `com.meta.wearable.mwdat.CLIENT_TOKEN`
- Android permissions `BLUETOOTH`, `BLUETOOTH_CONNECT`, and `INTERNET`

The target surface is `external/ipfs_kit`. The validated descriptors prove:

- the three `fix_mcp_schema.py` scripts expose `fix_mcp_schema()` and normalize
  `mcpServers` settings from invalid arrays to server-name objects
- deprecations report JSON Schema with required keys `report_version`,
  `generated_at`, `deprecated`, `summary`, `policy`, and `raw`
- CLI interface `ipfs_kit_py/bucket_vfs_cli.py`
- MCP API interface `mcp/bucket_vfs_mcp_tools.py`
- enhanced MCP server integration `mcp/enhanced_integrated_mcp_server.py`
  implemented at `ipfs_kit_py/mcp/servers/enhanced_integrated_mcp_server.py`
- S3-like bucket semantics
- Bucket VFS MCP tools `bucket_create`, `bucket_list`, `bucket_delete`,
  `bucket_add_file`, `bucket_export_car`, `bucket_cross_query`,
  `bucket_get_info`, and `bucket_status`
- CLI commands `create`, `list`, `delete`, `add-file`, `export`, and `query`
- VFS structure types `UNIXFS`, `GRAPH`, `VECTOR`, and `HYBRID`
- IPLD compatibility through DAG-PB messages `PBLink` and `PBNode`
- analytics integration through the Bucket VFS interface summary

## Runtime Handoff

`build_meta_wearables_dat_android_ipfs_kit_handoff()` produces a deterministic
receipt with:

- source repository `external/meta-wearables-dat-android`
- target repository `external/ipfs_kit`
- route `meta-wearables-dat-android-display-to-ipfs-kit-bucket-vfs`
- Bucket VFS bucket `meta-wearables-dat-android-display-events`
- Bucket VFS path `/wearables/meta/dat/android/display/events/latest.json`
- content CID `sha256:<payload_sha256>`

The payload models a display event in `STARTED` state with a `flexBox` display
content record. `external/ipfs_kit` can validate its MCP settings shape with
`fix_mcp_schema()`, validate a deprecations report before ingest, persist the
event through Bucket VFS operations such as `bucket_create`, `bucket_add_file`,
`bucket_export_car`, and `bucket_cross_query`, and exchange the content-addressed
record through DAG-PB `PBLink`/`PBNode` messages.

## Validation

The integration test validates all descriptors on disk, compiles the three
`fix_mcp_schema.py` scripts, checks the deprecations schema with `jsonschema`,
builds the handoff twice to prove deterministic content addressing, and verifies
the objective heap and discovery record include the VAI-670 objective validation
repair evidence for VAIOS-G711 while preserving the shared packet context for
VAIOS-G709 and VAIOS-G710.

Validation command:

```bash
python -m pytest tests/integration -q
```
