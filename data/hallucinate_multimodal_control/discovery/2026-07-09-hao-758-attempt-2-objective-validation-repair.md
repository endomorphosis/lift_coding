# HAO-758 Attempt 2 Objective Validation Repair

Date: 2026-07-09
Task: HAO-758
Attempt: 2
Goal: VAIOS-G719
Bundle: objective/interoperability/mobile-external_ipfs_accelerate
Source objective gap: data/hallucinate_multimodal_control/discovery/2026-07-09-hao-758-objective-gap-c1edafa875e6.md
Active repair record: data/hallucinate_multimodal_control/discovery/2026-07-09-hao-758-attempt-2-objective-validation-repair.md
Prior repair lineage: VAI-672, VAI-686, MGW-596, HAO-741 attempts 1-7, HAO-748, HAO-758 attempt 1

## Repair

This attempt-2 receipt is the active hallucinate_multimodal_control
objective validation repair for the re-filed `VAIOS-G719` scanner gap. It
keeps the supervisor-fed backlog aligned with
`objective/interoperability/mobile-external_ipfs_accelerate` by promoting a
fresh HAO-758 evidence record while preserving the original
`data/hallucinate_multimodal_control/discovery/2026-07-09-hao-758-objective-validation-repair.md`
lineage.

The `interface contract mobile external/ipfs_accelerate` proof remains
scanner-visible through:

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

`src/handsfree/mobile_ipfs_accelerate_interop.py` statically discovers the
DuckDB benchmark descriptors from `external/ipfs_accelerate`, verifies the
`performance_baselines`, `performance_regressions`, `performance_trends`,
and `regression_notifications` time-series tables, checks the schema utility
functions, and emits a deterministic `MobileIPFSAccelerateHandoff` receipt
for the mobile benchmark widget. The mobile descriptors export
`IPFS_ACCELERATE_MOBILE_INTEROP_INTERFACE`,
`IPFS_ACCELERATE_MOBILE_INTEROP_DESCRIPTOR`, and
`IPFS_ACCELERATE_BENCHMARK_WIDGET_ACTION_CONTRACT`, keeping the runtime
handoff importable without requiring the React Native client to import
Python from the external submodule.

## Validation

- `python -m pytest tests/integration/test_mobile_external_ipfs_accelerate_interop.py -q`
  passes in this worktree: 8 passed.
- `python -m pytest tests/integration -q` passes in this worktree:
  464 passed, 82 skipped, 16 warnings.

Evidence terms: HAO-758, VAIOS-G719,
objective/interoperability/mobile-external_ipfs_accelerate, objective
validation repair, interface contract mobile external/ipfs_accelerate.

No smaller child goals are required. The missing evidence is covered by
importable contracts, interface descriptors, runtime handoff behavior,
integration tests, docs, this discovery receipt, and the VAIOS-G719
objective heap entry.
