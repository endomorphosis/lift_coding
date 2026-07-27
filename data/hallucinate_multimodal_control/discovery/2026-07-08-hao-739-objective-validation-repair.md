# HAO-739 Objective Validation Repair

Task: HAO-739
Virtual task alias: VAI-670
Goal: VAIOS-G711
Goal packet: goal_packet/interoperability/external/6595cbbfadb9
Goal packet goals: VAIOS-G709, VAIOS-G710, VAIOS-G711
Gap fingerprint: 853e023f8d1df17520bfd2ce1d6727075d944b37
Missing evidence: objective validation repair

This repair closes the objective scanner gap filed in
`data/hallucinate_multimodal_control/discovery/2026-07-08-hao-739-objective-gap-853e023f8d1d.md`
by making the `interface contract external/meta-wearables-dat-android external/ipfs_kit`
handoff scanner-visible and testable from the HAO backlog lane as well as the
VAI-670 virtual objective lane.

The importable proof module
`src/handsfree/meta_wearables_dat_android_ipfs_kit_interop.py` validates the
Meta Wearables DAT Android Display/session descriptors:

- `external/meta-wearables-dat-android/.cursor/rules/display-access.mdc`
- `external/meta-wearables-dat-android/.cursor/rules/session-lifecycle.mdc`
- `external/meta-wearables-dat-android/.cursor/rules/permissions-registration.mdc`
- `external/meta-wearables-dat-android/samples/DisplayAccess/app/src/main/AndroidManifest.xml`
- `external/meta-wearables-dat-android/samples/DisplayAccess/app/src/main/java/com/meta/wearable/dat/externalsampleapps/displayaccess/display/DisplayViewModel.kt`

The same contract validates the `external/ipfs_kit` MCP schema,
deprecations-report, Bucket VFS, and DAG-PB descriptors:

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

`build_meta_wearables_dat_android_ipfs_kit_handoff()` emits a deterministic
`sha256:` handoff receipt for the
`meta-wearables-dat-android-display-to-ipfs-kit-bucket-vfs` route. The receipt
binds the Android DAT `DisplayState.STARTED` and `flexBox` display event to the
`external/ipfs_kit` Bucket VFS bucket `meta-wearables-dat-android-display-events`
and path `/wearables/meta/dat/android/display/events/latest.json`, then covers
the required operations `ipfs_kit.mcp_schema.fix_servers_schema`,
`ipfs_kit.mcp_schema.validate_deprecations_report`,
`ipfs_kit.bucket_vfs.bucket_create`, `ipfs_kit.bucket_vfs.bucket_add_file`,
`ipfs_kit.bucket_vfs.bucket_export_car`, `ipfs_kit.bucket_vfs.bucket_cross_query`,
`ipfs_kit.dag_pb.encode_node`, and `ipfs_kit.dag_pb.decode_node`.

Proof is covered by
`tests/integration/test_external_meta_wearables_dat_android_external_ipfs_kit_interop.py`
and documented in
`docs/integration/external_meta_wearables_dat_android-external_ipfs_kit.md`.
The test asserts descriptor presence, compile safety for the three
`fix_mcp_schema.py` scripts, JSON Schema validity for
`external/ipfs_kit/data/deprecations_report.schema.json`, deterministic content
addressing, objective heap alignment, and both HAO-739 and VAI-670 discovery
receipts.

This objective validation repair keeps the supervisor-fed backlog aligned with
the objective heap for VAIOS-G711 while preserving the shared packet context for
VAIOS-G709 and VAIOS-G710. No smaller child goals are required.

## Validation

Focused validation:

```bash
python -m pytest tests/integration/test_external_meta_wearables_dat_android_external_ipfs_kit_interop.py -q
```

Requested validation:

```bash
python -m pytest tests/integration -q
```
