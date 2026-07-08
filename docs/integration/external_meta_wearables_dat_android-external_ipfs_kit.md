# external/meta-wearables-dat-android to external/ipfs_kit

This contract closes the VAIOS-G711 validation gap for
`external/meta-wearables-dat-android` and `external/ipfs_kit`. It is part of
goal packet `goal_packet/interoperability/external/6595cbbfadb9`, alongside
VAIOS-G709 and VAIOS-G710.

## Contract

The Android side is discovered from the real Meta Wearables DAT Android sample
descriptors:

- `external/meta-wearables-dat-android/samples/DisplayAccess/app/build.gradle.kts`
- `external/meta-wearables-dat-android/samples/DisplayAccess/app/src/main/AndroidManifest.xml`
- `external/meta-wearables-dat-android/samples/CameraAccess/app/build.gradle.kts`
- `external/meta-wearables-dat-android/samples/CameraAccess/app/src/main/AndroidManifest.xml`

`handsfree.meta_wearables_ipfs_kit_interop` normalizes those descriptors into
an importable Python interface contract. The Display Access sample advertises
`display.output` through `mwdat.display`, requires Bluetooth and Internet
permissions, and carries the DAT application/client-token placeholders needed
by the Android runtime.

The IPFS Kit side is discovered from the pinned external checkout:

- `external/ipfs_kit/data/deprecations_report.schema.json`
- `external/ipfs_kit/archive/archive_clutter/fix_scripts/fix_mcp_schema.py`
- `external/ipfs_kit/backup/archive_clutter/fix_scripts/fix_mcp_schema.py`
- `external/ipfs_kit/backup/patches/fixes/fix_mcp_schema.py`
- `external/ipfs_kit/docs/implementation/BUCKET_VFS_INTERFACES_COMPLETE.md`
- `external/ipfs_kit/docs/py-ipld-dag-pb/ipld_dag_pb/dag-pb.proto`
- `external/ipfs_kit/ipfs_kit_py/bucket_vfs_cli.py`
- `external/ipfs_kit/ipfs_kit_py/mcp/servers/bucket_vfs_mcp_tools.py`
- `external/ipfs_kit/ipfs_kit_py/mcp/servers/enhanced_integrated_mcp_server.py`

The handoff receipt routes a `display.output` payload from the DAT Display
Access sample to the existing IPFS descriptor pack entry `ipfs.add`, whose HTTP
facade is `/v1/ipfs/add` with method `POST`. The receipt is JSON-serializable
and content-addressed with a deterministic `sha256:` CID so it can cross MCP,
HTTP, or supervisor boundaries without keeping Android or IPFS runtime objects
alive.

## Validation

`tests/integration/test_external_meta_wearables_dat_android_external_ipfs_kit_interop.py`
proves:

- the two external submodules are initialized at the expected paths;
- Android Gradle and manifest descriptors expose DAT dependencies,
  permissions, placeholders, and capabilities;
- IPFS Kit exposes the deprecations schema, bucket/VFS descriptors, MCP server
  descriptors, IPLD DAG-PB descriptor, and all three MCP schema repair scripts;
- the repair scripts parse and compile as Python;
- the Display Access sample can produce a deterministic handoff receipt for
  `/v1/ipfs/add`;
- objective evidence terms such as `interface contract`, `integration test`,
  `anyio`, `argparse`, `ast`, `atexit`, `binascii`, `collections`,
  `aiofiles`, `aiohttp`, `boto3`, `botocore`, and
  `check_high_level_api_syntax` are present for supervisor scanning.

Run:

```bash
python -m pytest tests/integration/test_external_meta_wearables_dat_android_external_ipfs_kit_interop.py -q
```

In this worktree, `python` is not on `PATH`; `python3 -m pytest ...` was used
for local verification.
