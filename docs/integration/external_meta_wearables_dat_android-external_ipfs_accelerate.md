# external/meta-wearables-dat-android to external/ipfs_accelerate

Task: HAO-737
Goal: VAIOS-G709
Packet: goal_packet/interoperability/external/6595cbbfadb9

This objective validation repair covers the interface contract external/meta-wearables-dat-android external/ipfs_accelerate. The Android DAT
producer envelope from HAO-739 carries latency, memory, and power telemetry that
maps directly to `external/ipfs_accelerate/data/duckdb/db_schema/time_series_schema.sql`.

Runtime proof:

- `external/meta-wearables-dat-android/python/meta_wearables_dat_android/ipfs_kit_handoff.py`
  normalizes wearable samples.
- `external/ipfs_accelerate/data/duckdb/db_schema/time_series_schema.sql`
  exposes `latency_ms`, `memory_mb`, `power_watts`, `hardware_platforms`, and
  `run_group_id` descriptors for telemetry ingestion.
- `tests/integration/test_external_meta_wearables_dat_android_external_ipfs_accelerate_interop.py`
  checks the handoff projection and required schema files.

Validation:

```bash
python -m pytest tests/integration/test_external_meta_wearables_dat_android_external_ipfs_accelerate_interop.py -q
```
