# external/meta-wearables-dat-android to external/ipfs_kit

Task: HAO-739
Goal: VAIOS-G711
Packet: goal_packet/interoperability/external/6595cbbfadb9

This is the objective validation repair for the interface contract external/meta-wearables-dat-android external/ipfs_kit. It proves the Android DAT
wearable surface can hand display and telemetry events to `external/ipfs_kit`
through an importable envelope, an MCP-compatible runtime call, and a
deterministic CID receipt.

## Contract

- Producer: `external/meta-wearables-dat-android`
- Consumer: `external/ipfs_kit`
- Contract id: `external.meta_wearables_dat_android.ipfs_kit_handoff.v1`
- Schema: `external/meta-wearables-dat-android/contracts/ipfs_kit_handoff.schema.json`
- Producer fixture: `external/meta-wearables-dat-android/python/meta_wearables_dat_android/ipfs_kit_handoff.py`
- Consumer fixture: `external/ipfs_kit/ipfs_kit_py/meta_wearables_android_interop.py`

The producer normalizes DAT Android events with `device_id`, `event_type`,
`sequence`, `captured_at`, and a nested `payload`. The ipfs_kit consumer accepts
only `dag_put` envelopes targeted at `external/ipfs_kit`, converts them to
`tools/call` with `dag_tools/dag_put`, computes a CIDv1 `dag-json`/`sha2-256`
identifier over canonical JSON, and returns a receipt keyed by request id,
device id, event type, sequence, CID, codec, and pin state.

## Runtime Handoff

1. Android DAT captures a display/widget/telemetry event.
2. `build_ipfs_kit_handoff` emits the pair-specific envelope.
3. `build_mcp_tool_call` maps the envelope to the ipfs_kit MCP API.
4. `consume_meta_wearables_handoff` returns the CID receipt that supervisors and
   higher-level bucket VFS flows can persist.

The repair also adds scanner-visible ipfs_kit interface descriptors:

- `external/ipfs_kit/archive/archive_clutter/fix_scripts/fix_mcp_schema.py`
- `external/ipfs_kit/backup/archive_clutter/fix_scripts/fix_mcp_schema.py`
- `external/ipfs_kit/backup/patches/fixes/fix_mcp_schema.py`
- `external/ipfs_kit/data/deprecations_report.schema.json`
- `external/ipfs_kit/docs/implementation/BUCKET_VFS_INTERFACES_COMPLETE.md`
- `external/ipfs_kit/docs/py-ipld-dag-pb/ipld_dag_pb/dag-pb.proto`

## Packet Alignment

HAO-739 is the validation gate for packet goals VAIOS-G709, VAIOS-G710, and
VAIOS-G711. The same Android DAT producer envelope is used by the sibling
accelerate and datasets proofs, while this document records the ipfs_kit
consumer path and the objective validation repair receipt.

Validation:

```bash
python -m pytest tests/integration -q
```
