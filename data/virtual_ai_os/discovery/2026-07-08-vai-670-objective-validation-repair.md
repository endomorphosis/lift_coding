# VAI-670 Objective Validation Repair

Date: 2026-07-08
Task: VAI-670
Goal: VAIOS-G711
Packet: goal_packet/interoperability/external/6595cbbfadb9
Packet goals: VAIOS-G709, VAIOS-G710, VAIOS-G711
Gap source: data/virtual_ai_os/discovery/2026-07-08-vai-670-objective-gap-853e023f8d1d.md
Evidence: objective validation repair

VAI-670 repairs the VAIOS-G711 objective gap for:

interface contract external/meta-wearables-dat-android external/ipfs_kit

The repair adds `src/handsfree/meta_wearables_dat_android_ipfs_kit_interop.py`
as the importable contract and
`tests/integration/test_external_meta_wearables_dat_android_external_ipfs_kit_interop.py`
as the scanner-visible validation gate. The contract statically validates the
Meta Wearables DAT Android Display/session descriptors and the `external/ipfs_kit`
MCP schema, deprecations, Bucket VFS, and DAG-PB descriptors, then emits a
deterministic `sha256:` handoff receipt for the
`meta-wearables-dat-android-display-to-ipfs-kit-bucket-vfs` route.

## Android DAT evidence

- `external/meta-wearables-dat-android/.cursor/rules/display-access.mdc`
- `external/meta-wearables-dat-android/.cursor/rules/session-lifecycle.mdc`
- `external/meta-wearables-dat-android/.cursor/rules/permissions-registration.mdc`
- `external/meta-wearables-dat-android/samples/DisplayAccess/app/src/main/AndroidManifest.xml`
- `external/meta-wearables-dat-android/samples/DisplayAccess/app/src/main/java/com/meta/wearable/dat/externalsampleapps/displayaccess/display/DisplayViewModel.kt`

These descriptors prove `Wearables.createSession`, `addDisplay`,
`DisplayState.STARTED`, `sendContent`, `flexBox`,
`Wearables.startRegistration`, `checkPermissionStatus`,
`RequestPermissionContract`, `PermissionStatus.Granted`, the DAT manifest
metadata keys, Android Bluetooth/Internet permissions, display icons, and
button styles required for a glasses display event handoff.

## ipfs_kit evidence

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

These descriptors prove `fix_mcp_schema()` support for `mcpServers`, the
deprecations report JSON Schema required keys, Bucket VFS CLI integration,
MCP API interface, enhanced MCP server integration, S3-like bucket semantics,
Bucket VFS tools `bucket_create`, `bucket_list`, `bucket_delete`,
`bucket_add_file`, `bucket_export_car`, `bucket_cross_query`,
`bucket_get_info`, and `bucket_status`, VFS structure types `UNIXFS`, `GRAPH`,
`VECTOR`, and `HYBRID`, IPLD compatibility through DAG-PB `PBLink`/`PBNode`,
and analytics integration.

## Runtime handoff proof

`build_meta_wearables_dat_android_ipfs_kit_handoff()` binds:

- source repository `external/meta-wearables-dat-android`
- target repository `external/ipfs_kit`
- route `meta-wearables-dat-android-display-to-ipfs-kit-bucket-vfs`
- bucket `meta-wearables-dat-android-display-events`
- path `/wearables/meta/dat/android/display/events/latest.json`
- content CID `sha256:<payload_sha256>`

The deterministic receipt covers `meta_wearables_dat_android.session.start`,
`meta_wearables_dat_android.display.send_content`,
`ipfs_kit.mcp_schema.fix_servers_schema`,
`ipfs_kit.mcp_schema.validate_deprecations_report`,
`ipfs_kit.bucket_vfs.bucket_create`, `ipfs_kit.bucket_vfs.bucket_add_file`,
`ipfs_kit.bucket_vfs.bucket_export_car`, `ipfs_kit.bucket_vfs.bucket_cross_query`,
`ipfs_kit.dag_pb.encode_node`, and `ipfs_kit.dag_pb.decode_node`.

## Validation

The objective validation repair is recorded in:

- `docs/integration/external_meta_wearables_dat_android-external_ipfs_kit.md`
- `implementation_plan/docs/23-virtual-ai-os-objective-goal-heap.md`
- `tests/integration/test_external_meta_wearables_dat_android_external_ipfs_kit_interop.py`

Validation command:

```bash
python -m pytest tests/integration -q
```

No smaller child goals are required. This keeps the supervisor-fed backlog
aligned with the objective heap for VAIOS-G711 and carries the shared packet
context for VAIOS-G709 and VAIOS-G710.
