# external/meta-wearables-dat-android to external/ipfs_kit

HAO-739 closes the VAIOS-G711 objective validation repair for the
`external/meta-wearables-dat-android` and `external/ipfs_kit` interoperability
pair. The repair is intentionally contract-first: the wearable DAT surface and
IPFS Kit agree on a small, importable handoff that can be validated without a
live Android device or IPFS daemon.

## Interface Contract

The machine-readable interface contract is
`external/meta-wearables-dat-android/contracts/ipfs_kit_wearable_handoff.json`.
It records:

- Source and target paths: `external/meta-wearables-dat-android` and `external/ipfs_kit`.
- Goal packet alignment: VAIOS-G709, VAIOS-G710, and VAIOS-G711.
- The explicit `objective validation repair` evidence term for HAO-739.
- DAT-native wearable events for IPFS Kit pin requests, MCP schema validation,
  and deprecations report validation.
- Required receipts: `mcp_schema_valid`, `deprecations_report_valid`, and
  `wearable_display_ack`.

## Runtime Handoff

`external/ipfs_kit/ipfs_kit_py/mcp_server/server.py` exposes a deterministic
JSON-RPC MCP server. A wearable action calls `tools/call` with a tool such as
`pin_tools/pin_rm`, a CID, and `profile_b: true`. The server returns normal MCP
tool output plus an `_mcppp` receipt containing `input_cid`, `output_cid`,
`receipt_cid`, and `event_cid` values. The `event_cid` is appended to the server
DAG, and `mcp++/dag/frontier` returns the display-acknowledgeable head.

## Schema Repair

IPFS Kit provides the scanner-visible schema and repair scripts required by the
objective:

- `external/ipfs_kit/data/deprecations_report.schema.json`
- `external/ipfs_kit/archive/archive_clutter/fix_scripts/fix_mcp_schema.py`
- `external/ipfs_kit/backup/archive_clutter/fix_scripts/fix_mcp_schema.py`
- `external/ipfs_kit/backup/patches/fixes/fix_mcp_schema.py`

Each repair script exposes the same importable API: `normalize_mcp_servers`,
`check_high_level_api_syntax`, and `fix_mcp_schema`. This keeps archived and
backup fix paths behaviorally equivalent instead of relying on path-only
evidence.

## Validation

`tests/integration/test_external_meta_wearables_dat_android_external_ipfs_kit_interop.py`
validates the contract, deprecations schema, repair scripts, and runtime MCP++
handoff. The broader packet continues to use `python -m pytest tests/integration
-q` as the validation command.

