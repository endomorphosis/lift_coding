# VAI-672 Objective Validation Repair

Date: 2026-07-08
Task: VAI-672
Goal: VAIOS-G719
Bundle: objective/interoperability/mobile-external_ipfs_accelerate
Merge key: 64e26db5b0fa2426
Merge family: objective/VAIOS-G719
Source objective gap: data/virtual_ai_os/discovery/2026-07-08-vai-672-objective-gap-c1edafa875e6.md

## Objective Validation Repair

This repair makes the `interface contract mobile external/ipfs_accelerate`
handoff scanner-visible and testable in the expected VAI-672 outputs.
`external/ipfs_accelerate` owns the DuckDB time-series/benchmark schema
descriptors that back accelerated inference performance telemetry. `mobile`
owns the ORB descriptor exports and the benchmark widget action mapping that
lets the Handsfree mobile client render that telemetry without importing any
Python from the `external/ipfs_accelerate` submodule.

Evidence term: objective validation repair.
Evidence term: interface contract mobile external/ipfs_accelerate.
Evidence term: VAIOS-G719.

- `tests/integration/test_mobile_external_ipfs_accelerate_interop.py`
- `docs/integration/mobile-external_ipfs_accelerate.md`
- `src/handsfree/mobile_ipfs_accelerate_interop.py`
- `mobile/src/orb/metaGlassesOrbDescriptors.js`
- `mobile/src/utils/ipfsAccelerateBenchmarkWidgetContract.js`
- `mobile/src/orb/metaGlassesMobileOrbBridge.js`
- `external/ipfs_accelerate/data/duckdb/db_schema/time_series_schema.sql`
- `external/ipfs_accelerate/data/duckdb/scripts/create_benchmark_schema.py`
- `external/ipfs_accelerate/data/duckdb/utils/check_database_schema.py`
- `external/ipfs_accelerate/data/duckdb/utils/check_db_schema.py`
- `implementation_plan/docs/23-virtual-ai-os-objective-goal-heap.md`

## Runtime Handoff Evidence

`src/handsfree/mobile_ipfs_accelerate_interop.py` discovers the DuckDB
time-series schema, the benchmark schema creation script, and the two schema
check utilities shipped by `external/ipfs_accelerate` (without importing any
of their Python), verifies the `performance_baselines`,
`performance_regressions`, `performance_trends`, and
`regression_notifications` tables are declared, and builds a deterministic
`MobileIPFSAccelerateHandoff` receipt routed through the existing IPFS
descriptor pack (`ipfs.capabilities`).

`mobile/src/orb/metaGlassesOrbDescriptors.js` exports
`IPFS_ACCELERATE_MOBILE_INTEROP_INTERFACE` and
`IPFS_ACCELERATE_MOBILE_INTEROP_DESCRIPTOR`. The descriptor records the
allowed agent, mcp_server, mobile, and Meta glasses surfaces, and points to
the `external/ipfs_accelerate` DuckDB schema refs used for the handoff.

`mobile/src/utils/ipfsAccelerateBenchmarkWidgetContract.js` exports
`IPFS_ACCELERATE_BENCHMARK_WIDGET_ACTION_CONTRACT`, which maps benchmark
widget action ids to mobile ORB operations, DAT methods, and the
`external/ipfs_accelerate` time-series table each action reads.

`mobile/src/orb/metaGlassesMobileOrbBridge.js` advertises the
`external/ipfs_accelerate`/mobile descriptor during edge capability
registration so the mobile edge session can bind benchmark widget operations
without importing `external/ipfs_accelerate` runtime code.

## Validation

Focused validation target:

`python -m pytest tests/integration/test_mobile_external_ipfs_accelerate_interop.py -q`

Full supervisor target:

`python -m pytest tests/integration -q`
