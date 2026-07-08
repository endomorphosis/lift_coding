# SwissKnife / external/ipfs_accelerate Interop

VAI-662 repairs the VAIOS-G701 objective validation gap for the shared
`goal_packet/interoperability/swissknife/06921590135c` packet covering
VAIOS-G700, VAIOS-G701, VAIOS-G702, VAIOS-G703, VAIOS-G704, VAIOS-G705, and
VAIOS-G706.

The repaired `interface contract swissknife external/ipfs_accelerate` path
is:

- `external/ipfs_accelerate/data/duckdb/db_schema/time_series_schema.sql`
  defines the DuckDB time-series schema extension, including the
  `performance_baselines`, `performance_regressions`, `performance_trends`,
  and `regression_notifications` tables consumed by SwissKnife's benchmark
  surface.
- `external/ipfs_accelerate/data/duckdb/scripts/create_benchmark_schema.py`
  creates the base benchmark schema (`create_performance_tables`,
  `create_common_tables`, `create_views`, ...) that the time-series
  extension builds on.
- `external/ipfs_accelerate/data/duckdb/utils/check_database_schema.py` and
  `external/ipfs_accelerate/data/duckdb/utils/check_db_schema.py` expose
  `check_schema`, `get_all_tables`, and `get_performance_results` for
  verifying the benchmark database before SwissKnife consumes it.
- `src/handsfree/swissknife_ipfs_accelerate_interop.py` statically discovers
  those four descriptors (without importing `external/ipfs_accelerate`
  Python, since `create_benchmark_schema.py` is not import-safe in this
  worktree), verifies the required time-series tables and schema-check
  functions are present, and builds a deterministic
  `SwissKnifeIPFSAccelerateHandoff` receipt.
- `swissknife/src/services/mcp/ipfs-accelerate-duckdb-interop-descriptor.ts`
  exports `SWISSKNIFE_IPFS_ACCELERATE_INTEROP_INTERFACE` (a canonical
  MCP-IDL Profile A `MCPPPInterfaceDescriptor`) and
  `SWISSKNIFE_IPFS_ACCELERATE_INTEROP_DESCRIPTOR`, plus
  `registerSwissKnifeIPFSAccelerateDuckDBInterop()` /
  `createMCPPlusPlusClientWithSwissKnifeIPFSAccelerateInterop()` to register
  the descriptor on a live `MCPPlusPlus` runtime registry alongside the
  pre-built `IPFS_ACCELERATE_INTERFACE`, and
  `buildSwissKnifeIPFSAccelerateControlSurfaceContract()` /
  `buildSwissKnifeIPFSAccelerateInteractionEnvelope()` to build representative
  control-surface and interaction-envelope payloads.
- `swissknife/contracts/control_surface_contract.schema.json` and
  `swissknife/contracts/interaction_envelope.schema.json` validate those
  SwissKnife-to-`external/ipfs_accelerate` control surface and interaction
  envelope payloads (preserving the scanner-visible `agent_identity`,
  `allowed_surfaces`, and `arguments_hash` norm refs), and
  `swissknife/contracts/mediation_receipt.schema.json` remains the receipt
  schema ref advertised by the descriptor.

## Runtime handoff

1. `SWISSKNIFE_IPFS_ACCELERATE_INTEROP_INTERFACE` registers six
   `accelerate.duckdb.*` operations (`check_schema`, `get_all_tables`,
   `get_performance_results`, `create_performance_tables`,
   `create_common_tables`, `create_views`) as an MCP-IDL Profile A interface
   descriptor, compatible with the pre-built `IPFS_ACCELERATE_INTERFACE`
   already registered by `createMCPPlusPlusClient()`.
2. A SwissKnife control-surface event (for example
   `get_performance_results`) resolves to
   `accelerate.duckdb.get_performance_results` via the
   `swissknife.ipfs_accelerate.data-service` control surface, mediated by the
   `policy:swissknife:ipfs-accelerate-duckdb-interop` policy bundle.
3. `src/handsfree/swissknife_ipfs_accelerate_interop.py` builds a
   deterministic, content-addressed receipt (`sha256:` content CID) for the
   benchmark-schema handoff via `build_swissknife_duckdb_handoff()`, which
   statically re-derives the same time-series table set and required
   `accelerate.duckdb.*` operations advertised by the TypeScript descriptor.

## Validation evidence

Validation evidence lives in
`tests/integration/test_swissknife_external_ipfs_accelerate_interop.py`. It
verifies the DuckDB schema descriptors under `external/ipfs_accelerate`
exist and declare the expected tables/functions, exercises the Python
`swissknife_ipfs_accelerate_interop` discovery and handoff builder, statically
inspects the SwissKnife TypeScript descriptor module for the expected
exports/goal-packet metadata, validates representative SwissKnife
control-surface and interaction-envelope payloads, and asserts this
objective validation repair is recorded in
`data/virtual_ai_os/discovery/2026-07-08-vai-662-objective-validation-repair.md`
and the objective heap
(`implementation_plan/docs/23-virtual-ai-os-objective-goal-heap.md`).
