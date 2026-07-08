# HAO-737 Objective Validation Repair

Task: HAO-737
Goal: VAIOS-G709
Goal packet: goal_packet/interoperability/external/6595cbbfadb9
Goal packet goals: VAIOS-G709, VAIOS-G710, VAIOS-G711
Gap fingerprint: 56ff358535c4964cf9ba25a7e4ed04327a9b6077
Missing evidence: objective validation repair

This repair closes the objective scanner gap filed in
`data/hallucinate_multimodal_control/discovery/2026-07-08-hao-737-objective-gap-56ff358535c4.md`
by making the `interface contract external/meta-wearables-dat-android external/ipfs_accelerate`
handoff scanner-visible and testable.

The implementation validates the Android DAT DisplayAccess contract in
`external/meta-wearables-dat-android/samples/DisplayAccess/README.md`,
`external/meta-wearables-dat-android/samples/DisplayAccess/app/build.gradle.kts`,
`external/meta-wearables-dat-android/samples/DisplayAccess/app/src/main/java/com/meta/wearable/dat/externalsampleapps/displayaccess/display/DisplayViewModel.kt`,
and `external/meta-wearables-dat-android/.cursor/rules/display-access.mdc`.
The tracked Python contract maps Android DAT benchmark methods
`renderPerformanceBenchmarkWidget`, `updatePerformanceBenchmarkWidget`,
`clearPerformanceBenchmarkWidget`, and `refreshPerformanceBenchmarkMetrics`
to the `performance_baselines`, `performance_trends`,
`regression_notifications`, and `performance_regressions` tables declared by
`external/ipfs_accelerate/data/duckdb/db_schema/time_series_schema.sql`.

The Python proof module
`src/handsfree/meta_wearables_dat_android_ipfs_accelerate_interop.py`
statically discovers those Android DAT DisplayAccess files plus the
`external/ipfs_accelerate/data/duckdb/scripts/create_benchmark_schema.py`,
`external/ipfs_accelerate/data/duckdb/utils/check_database_schema.py`, and
`external/ipfs_accelerate/data/duckdb/utils/check_db_schema.py` descriptors.
It verifies the expected time-series tables, benchmark creation functions,
schema-check functions, goal packet metadata, and DAT method mapping before
building a deterministic `sha256:` handoff receipt for the
`ipfs-accelerate-benchmark-to-meta-wearables-dat-android` route.

Proof is covered by
`tests/integration/test_external_meta_wearables_dat_android_external_ipfs_accelerate_interop.py`
and documented in
`docs/integration/external_meta_wearables_dat_android-external_ipfs_accelerate.md`.
This objective validation repair keeps the supervisor-fed backlog aligned
with the objective heap for VAIOS-G709 while recording the shared packet
context for VAIOS-G710 and VAIOS-G711. No smaller child goals are required
for this HAO-737 gap because the missing evidence terms are now covered by a
cohesive contract, handoff builder, integration test, discovery record, and
objective heap entry.

## Validation

Attempt 3 retargeted the active proof from the parallel MGW backlog lane to
the HAO-737 lane by binding `TASK_ID`, the integration test, and this
discovery receipt to `HAO-737` and
`data/hallucinate_multimodal_control/discovery/2026-07-08-hao-737-objective-validation-repair.md`.
The focused gate
`python -m pytest tests/integration/test_external_meta_wearables_dat_android_external_ipfs_accelerate_interop.py -q`
passed with 7 tests. The full requested gate
`python -m pytest tests/integration -q` passed with 436 passed, 89 skipped,
and 16 warnings after checking out the recorded
`external/meta-wearables-dat-android` and `external/ipfs_kit` submodule
pointers in this worktree without changing gitlink commits.
