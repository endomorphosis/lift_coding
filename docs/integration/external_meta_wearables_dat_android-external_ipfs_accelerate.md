# Meta Wearables DAT Android / external/ipfs_accelerate Interop

HAO-737 repairs the VAIOS-G709 objective validation gap for the shared
`goal_packet/interoperability/external/6595cbbfadb9` packet covering
VAIOS-G709, VAIOS-G710, and VAIOS-G711.

The repaired `interface contract external/meta-wearables-dat-android external/ipfs_accelerate`
path is:

- `external/meta-wearables-dat-android/samples/DisplayAccess/README.md`,
  `external/meta-wearables-dat-android/samples/DisplayAccess/app/build.gradle.kts`,
  `external/meta-wearables-dat-android/samples/DisplayAccess/app/src/main/java/com/meta/wearable/dat/externalsampleapps/displayaccess/display/DisplayViewModel.kt`,
  and `external/meta-wearables-dat-android/.cursor/rules/display-access.mdc`
  prove the Android DAT side exposes display-capable device selection,
  `mwdat-display`, `addDisplay`, `sendContent`, and `DisplayState.STARTED`
  lifecycle semantics that can consume benchmark widget payloads.
- `external/ipfs_accelerate/data/duckdb/db_schema/time_series_schema.sql`
  defines the `performance_baselines`, `performance_regressions`,
  `performance_trends`, and `regression_notifications` time-series tables
  that feed the Android DAT benchmark widget.
- `external/ipfs_accelerate/data/duckdb/scripts/create_benchmark_schema.py`
  provides `create_performance_tables`, `create_common_tables`, and
  `create_views`, which create the benchmark schema underneath the
  time-series extension.
- `external/ipfs_accelerate/data/duckdb/utils/check_database_schema.py` and
  `external/ipfs_accelerate/data/duckdb/utils/check_db_schema.py` expose
  `check_schema`, `get_all_tables`, and `get_performance_results` for
  validating the benchmark database before a DAT display handoff.
- `src/handsfree/meta_wearables_dat_android_ipfs_accelerate_interop.py`
  statically discovers those Android DAT DisplayAccess files and the four
  `external/ipfs_accelerate` descriptors, verifies the required tables and
  functions, binds Android DAT benchmark methods to the corresponding
  `external/ipfs_accelerate` tables, and builds a deterministic
  content-addressed handoff receipt.

## Runtime handoff

1. `external/ipfs_accelerate` produces benchmark rows in its DuckDB
   time-series tables.
2. The Android DAT descriptor maps each display method to the table it
   consumes: `renderPerformanceBenchmarkWidget` reads
   `performance_baselines`, `updatePerformanceBenchmarkWidget` reads
   `performance_trends`, `clearPerformanceBenchmarkWidget` records
   `regression_notifications`, and `refreshPerformanceBenchmarkMetrics`
   reads `performance_regressions`.
3. `build_meta_wearables_dat_android_ipfs_accelerate_handoff()` returns a
   deterministic `sha256:` receipt for the
   `ipfs-accelerate-benchmark-to-meta-wearables-dat-android` route so the
   objective can prove runtime handoff behavior without Android hardware.

## Validation evidence

Validation evidence lives in
`tests/integration/test_external_meta_wearables_dat_android_external_ipfs_accelerate_interop.py`.
It verifies the Android DAT DisplayAccess files expose the required display
surface, verifies the DAT benchmark method mapping to the expected
`external/ipfs_accelerate` tables, verifies the DuckDB schema descriptors
under `external/ipfs_accelerate`, exercises the Python discovery and handoff
builder, and asserts this objective validation repair is recorded in
`data/hallucinate_multimodal_control/discovery/2026-07-08-hao-737-objective-validation-repair.md`
with this contract note at
`docs/integration/external_meta_wearables_dat_android-external_ipfs_accelerate.md`,
and the objective heap
(`implementation_plan/docs/23-virtual-ai-os-objective-goal-heap.md`).
