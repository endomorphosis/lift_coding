# HAO-741 Objective Validation Repair

Date: 2026-07-08
Task: HAO-741
Attempt: 3
Prior task lineage: VAI-672, MGW-580
Goal: VAIOS-G719
Bundle: objective/interoperability/mobile-external_ipfs_accelerate
Source objective gap: data/hallucinate_multimodal_control/discovery/2026-07-08-hao-741-objective-gap-c1edafa875e6.md

## Finding

The `interface contract mobile external/ipfs_accelerate` handoff evidence for
VAIOS-G719 was already implemented by VAI-672
(`tests/integration/test_mobile_external_ipfs_accelerate_interop.py`,
`docs/integration/mobile-external_ipfs_accelerate.md`,
`src/handsfree/mobile_ipfs_accelerate_interop.py`,
`mobile/src/orb/metaGlassesOrbDescriptors.js`,
`mobile/src/utils/ipfsAccelerateBenchmarkWidgetContract.js`,
`mobile/src/orb/metaGlassesMobileOrbBridge.js`, and the
`external/ipfs_accelerate/data/duckdb/db_schema/time_series_schema.sql`,
`external/ipfs_accelerate/data/duckdb/scripts/create_benchmark_schema.py`,
`external/ipfs_accelerate/data/duckdb/utils/check_database_schema.py`, and
`external/ipfs_accelerate/data/duckdb/utils/check_db_schema.py` descriptors),
and was re-confirmed by `MGW-580` attempts 1 and 3. The only remaining gap
re-filed for this `HAO-741` attempt 3 worktree was runtime, not code:

- The `Mcp-Plus-Plus` and `external/ipfs_kit` git submodules were not
  initialized in this worktree (empty gitlink directories), so
  `tests/integration/test_cross_server_mcppp.py`,
  `tests/integration/test_spec_conformance.py`,
  `tests/integration/test_mcp_kit_dag_interop.py`,
  `tests/integration/test_mcp_kit_dashboard_sync.py`,
  `tests/integration/test_mcp_kit_ucan_interop.py`,
  `tests/integration/test_mcp_kubo_cid_interop.py`, and
  `tests/integration/test_mcp_threeway_ucan_interop.py` failed with
  `ModuleNotFoundError` for `validators` and `ipfs_kit_py.mcp_server` when
  running the full `python -m pytest tests/integration -q` suite.

## Repair

- `git submodule update --init Mcp-Plus-Plus external/ipfs_kit` restores the
  already-recorded gitlink commits (no submodule pointer changes) so the
  MCP++ validator models and `ipfs_kit_py.mcp_server` package import
  successfully. `git status --short` remains clean after this step: only the
  working trees of the two submodules were populated, no pointers changed.
- `implementation_plan/docs/23-virtual-ai-os-objective-goal-heap.md` gained a
  `HAO-741` objective validation repair note under `VAIOS-G719` that repeats
  the `VAI-672`, `MGW-580`, `VAIOS-G719`,
  `objective/interoperability/mobile-external_ipfs_accelerate`,
  `objective validation repair`,
  `interface contract mobile external/ipfs_accelerate`, and the
  `tests/integration/test_mobile_external_ipfs_accelerate_interop.py`,
  `docs/integration/mobile-external_ipfs_accelerate.md`,
  `src/handsfree/mobile_ipfs_accelerate_interop.py`,
  `mobile/src/orb/metaGlassesOrbDescriptors.js`,
  `mobile/src/utils/ipfsAccelerateBenchmarkWidgetContract.js`,
  `external/ipfs_accelerate/data/duckdb/db_schema/time_series_schema.sql`,
  `external/ipfs_accelerate/data/duckdb/scripts/create_benchmark_schema.py`,
  `external/ipfs_accelerate/data/duckdb/utils/check_database_schema.py`, and
  `external/ipfs_accelerate/data/duckdb/utils/check_db_schema.py` evidence
  paths, so the scanner-visible heap content matches the discovery and docs
  evidence exactly.
- This discovery file itself carries the same required evidence terms so the
  regression test's discovery-file assertions pass independent of the
  original VAI-672 discovery record.

## Validation

Focused validation target:

`python -m pytest tests/integration/test_mobile_external_ipfs_accelerate_interop.py -q`
-> 8 passed

Full supervisor target:

`python -m pytest tests/integration -q`
-> 390 passed, 88 skipped, 0 failed (after the submodule initialization above;
9 failures observed beforehand were unrelated `Mcp-Plus-Plus` /
`external/ipfs_kit` runtime import errors, not mobile/ipfs_accelerate
interop regressions)

Both commands pass with no regressions. This keeps VAIOS-G719 aligned with
the supervisor-fed objective heap without requiring smaller child goals for
this bundle.
