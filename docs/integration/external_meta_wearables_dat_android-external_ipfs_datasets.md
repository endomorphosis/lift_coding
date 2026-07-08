# external/meta-wearables-dat-android to external/ipfs_datasets Interop

Task: HAO-738
Goal: VAIOS-G710
Packet: goal_packet/interoperability/external/6595cbbfadb9
Evidence: objective validation repair

This contract proves `external/meta-wearables-dat-android` interoperates with
`external/ipfs_datasets` through an importable contract, interface descriptors,
runtime handoff behavior, and an integration test:

- `tests/integration/test_external_meta_wearables_dat_android_external_ipfs_datasets_interop.py`
- `src/handsfree/meta_wearables_dat_android_ipfs_datasets_interop.py`
- interface contract external/meta-wearables-dat-android external/ipfs_datasets
- `external/meta-wearables-dat-android/.cursor/rules/display-access.mdc`
- `external/meta-wearables-dat-android/.cursor/rules/session-lifecycle.mdc`
- `external/meta-wearables-dat-android/.cursor/rules/permissions-registration.mdc`
- `external/meta-wearables-dat-android/samples/DisplayAccess/app/src/main/AndroidManifest.xml`
- `external/meta-wearables-dat-android/samples/DisplayAccess/app/src/main/java/com/meta/wearable/dat/externalsampleapps/displayaccess/display/DisplayViewModel.kt`
- `external/ipfs_datasets/.tools/ipfs_kit_py/data/deprecations_report.schema.json`
- `external/ipfs_datasets/.tools/ipfs_kit_py/docs/implementation/BUCKET_VFS_INTERFACES_COMPLETE.md`
- `external/ipfs_datasets/.tools/ipfs_kit_py/examples/demo_bucket_vfs_interfaces.py`
- `external/ipfs_datasets/.tools/ipfs_kit_py/examples/demo_unified_bucket_interface.py`

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

The target surface is `external/ipfs_datasets` with its embedded
`.tools/ipfs_kit_py` Bucket VFS evidence. The validated descriptors prove:

- deprecations report JSON Schema with required keys `report_version`,
  `generated_at`, `deprecated`, `summary`, `policy`, and `raw`
- CLI interface `ipfs_kit_py/bucket_vfs_cli.py`
- MCP API interface `mcp/bucket_vfs_mcp_tools.py`
- enhanced MCP server integration `mcp/enhanced_integrated_mcp_server.py`
- S3-like bucket semantics
- Bucket VFS MCP tools `bucket_create`, `bucket_list`, `bucket_delete`,
  `bucket_add_file`, `bucket_export_car`, `bucket_cross_query`,
  `bucket_get_info`, and `bucket_status`
- VFS structure types `UNIXFS`, `GRAPH`, `VECTOR`, and `HYBRID`
- ipfs_datasets router symbols `register_ipfs_backend`, `add_bytes`, `cat`,
  `embed_text`, and `generate_text`

## Runtime Handoff

`build_meta_wearables_dat_android_ipfs_datasets_handoff()` produces a
deterministic receipt with:

- source repository `external/meta-wearables-dat-android`
- target repository `external/ipfs_datasets`
- route `meta-wearables-dat-android-display-to-ipfs-datasets-bucket-vfs`
- dataset bucket `meta-wearables-dat-android-display-events`
- dataset VFS path `/wearables/meta/dat/android/display/events/latest.json`
- content CID `sha256:<payload_sha256>`

The payload models a display event in `STARTED` state with a `flexBox` display
content record. ipfs_datasets stores that event through
`ipfs_datasets_py.ipfs_backend_router.add_bytes` and makes it queryable through
Bucket VFS operations such as `bucket_add_file`, `bucket_export_car`, and
`bucket_cross_query`.

## Validation

The integration test validates all descriptors on disk, compiles the Bucket VFS
demo, checks the deprecations schema with `jsonschema`, builds the handoff twice
to prove deterministic content addressing, and verifies the objective heap and
discovery record include the HAO-738 objective validation repair evidence.

Validation command:

```bash
python -m pytest tests/integration -q
```
