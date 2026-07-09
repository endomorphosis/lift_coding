# MGW-595 Objective Validation Repair

Date: 2026-07-09
Task: MGW-595
Goal: VAIOS-G719
Bundle: objective/interoperability/mobile-external_ipfs_accelerate
Source gap: data/meta_glasses_display_widgets/discovery/2026-07-09-mgw-595-objective-gap-c1edafa875e6.md
Repair record: data/meta_glasses_display_widgets/discovery/2026-07-09-mgw-595-objective-validation-repair.md
Merge family: objective/VAIOS-G719
Evidence: objective validation repair

## Repair Summary

MGW-595 re-validates the VAIOS-G719 mobile/external_ipfs_accelerate objective validation repair for the `meta_glasses_display_widgets` backlog. The earlier VAI-672 implementation and VAI-686/MGW-580 validation repairs already provided the runtime path; this record makes the active MGW-595 evidence scanner-visible and keeps the supervisor-fed backlog aligned with implementation_plan/docs/23-virtual-ai-os-objective-goal-heap.md.

## Evidence Terms

- VAIOS-G719
- MGW-595
- objective/interoperability/mobile-external_ipfs_accelerate
- objective validation repair
- interface contract mobile external/ipfs_accelerate
- tests/integration/test_mobile_external_ipfs_accelerate_interop.py
- docs/integration/mobile-external_ipfs_accelerate.md
- src/handsfree/mobile_ipfs_accelerate_interop.py
- mobile/src/orb/metaGlassesOrbDescriptors.js
- mobile/src/utils/ipfsAccelerateBenchmarkWidgetContract.js
- mobile/src/orb/metaGlassesMobileOrbBridge.js
- external/ipfs_accelerate/data/duckdb/db_schema/time_series_schema.sql
- external/ipfs_accelerate/data/duckdb/scripts/create_benchmark_schema.py
- external/ipfs_accelerate/data/duckdb/utils/check_database_schema.py
- external/ipfs_accelerate/data/duckdb/utils/check_db_schema.py

## Coverage

`tests/integration/test_mobile_external_ipfs_accelerate_interop.py` proves the four external DuckDB descriptors exist, verifies `time_series_schema.sql` declares the required `performance_baselines`, `performance_regressions`, `performance_trends`, and `regression_notifications` tables, and verifies `create_benchmark_schema.py`, `check_database_schema.py`, and `check_db_schema.py` expose the schema creation and inspection functions consumed by the mobile benchmark handoff.

`src/handsfree/mobile_ipfs_accelerate_interop.py` keeps the contract importable from the Handsfree runtime without importing `external/ipfs_accelerate` Python. It builds a deterministic `MobileIPFSAccelerateHandoff` receipt for the `ipfs-accelerate-benchmark-to-mobile-widget` route and verifies the mobile widget action list.

`mobile/src/orb/metaGlassesOrbDescriptors.js` records `MGW-595` as the active validation repair task for `IPFS_ACCELERATE_MOBILE_INTEROP_DESCRIPTOR`, while preserving `VAI-672`, `VAI-686`, and `MGW-580` as prior repair lineage. `mobile/src/utils/ipfsAccelerateBenchmarkWidgetContract.js` maps each mobile benchmark widget action to an ORB operation, a Meta Wearables DAT-style method name, and the relevant `external/ipfs_accelerate` time-series table. `mobile/src/orb/metaGlassesMobileOrbBridge.js` advertises the descriptor during edge capability registration.

`docs/integration/mobile-external_ipfs_accelerate.md` and implementation_plan/docs/23-virtual-ai-os-objective-goal-heap.md now name this MGW-595 repair alongside the existing VAI/MGW history. No smaller child goals are required because the importable contract, interface descriptor, runtime handoff, documentation, discovery, and integration-test evidence terms are all covered in this bundle.

## Validation

- Focused gate: `python -m pytest tests/integration/test_mobile_external_ipfs_accelerate_interop.py -q`
- Required gate: `python -m pytest tests/integration -q`
