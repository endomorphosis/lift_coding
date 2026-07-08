# Mobile / external/ipfs_accelerate Interop

VAI-672 repairs the VAI-661/VAIOS-G719 objective validation gap covering the
`objective/interoperability/mobile-external_ipfs_accelerate` bundle.

The repaired `interface contract mobile external/ipfs_accelerate` path is:

- `external/ipfs_accelerate/data/duckdb/db_schema/time_series_schema.sql`
  defines the DuckDB time-series schema extension, including the
  `performance_baselines`, `performance_regressions`, `performance_trends`,
  and `regression_notifications` tables consumed by the mobile benchmark
  widget.
- `external/ipfs_accelerate/data/duckdb/scripts/create_benchmark_schema.py`
  creates the base benchmark schema (`create_performance_tables`,
  `create_common_tables`, `create_views`, ...) that the time-series
  extension builds on.
- `external/ipfs_accelerate/data/duckdb/utils/check_database_schema.py` and
  `external/ipfs_accelerate/data/duckdb/utils/check_db_schema.py` expose
  `check_schema`, `get_all_tables`, and `get_performance_results` for
  verifying the benchmark database before mobile consumes it.
- `src/handsfree/mobile_ipfs_accelerate_interop.py` statically discovers
  those four descriptors (without importing `external/ipfs_accelerate`
  Python), verifies the required time-series tables and schema-check
  functions are present, and builds a deterministic
  `MobileIPFSAccelerateHandoff` receipt routed through the existing IPFS
  descriptor pack's `ipfs.capabilities` endpoint.
- `mobile/src/orb/metaGlassesOrbDescriptors.js` exports
  `IPFS_ACCELERATE_MOBILE_INTEROP_INTERFACE` and
  `IPFS_ACCELERATE_MOBILE_INTEROP_DESCRIPTOR`, binding the mobile ORB bridge
  and benchmark widget operations to the `external/ipfs_accelerate` DuckDB
  schema refs.
- `mobile/src/utils/ipfsAccelerateBenchmarkWidgetContract.js` exports
  `IPFS_ACCELERATE_BENCHMARK_WIDGET_ACTION_CONTRACT`, mapping benchmark
  widget action ids to mobile ORB operations, Meta Wearables DAT-style
  method names, and the `external/ipfs_accelerate` time-series table each
  action reads.
- `mobile/src/orb/metaGlassesMobileOrbBridge.js` advertises the interop
  descriptor during edge capability registration and keeps diagnostics
  parseable after the contract wiring.

## Runtime handoff

1. The mobile ORB bridge registers edge capabilities and advertises the
   `IPFS_ACCELERATE_MOBILE_INTEROP_DESCRIPTOR` alongside the existing mobile
   ORB bridge and display widget descriptors.
2. A benchmark widget action (for example
   `mobile_render_performance_benchmark_widget`) resolves to an ORB
   operation (`render_performance_benchmark_widget`) and a DuckDB
   time-series table (`performance_baselines`) via
   `ipfsAccelerateBenchmarkWidgetContract.js`.
3. The Handsfree backend uses
   `build_mobile_benchmark_widget_handoff()` from
   `src/handsfree/mobile_ipfs_accelerate_interop.py` to build a
   deterministic, content-addressed receipt (`sha256:` content CID) for the
   benchmark payload before it is routed to the mobile display widget.

## Validation evidence

Validation evidence lives in
`tests/integration/test_mobile_external_ipfs_accelerate_interop.py`. It
verifies the DuckDB schema descriptors under `external/ipfs_accelerate`
exist and declare the expected tables/functions, loads the JavaScript
descriptor exports, verifies the benchmark widget action mapping, exercises
the Python `mobile_ipfs_accelerate_interop` handoff builder, and asserts this
objective validation repair is recorded in
`data/virtual_ai_os/discovery/2026-07-08-vai-672-objective-validation-repair.md`
plus the attempt-five confirmation record
`data/virtual_ai_os/discovery/2026-07-08-vai-672-attempt-5-validation-confirmation.md`
and the objective heap
(`implementation_plan/docs/23-virtual-ai-os-objective-goal-heap.md`).
