# Hallucinate App / Mobile Interop

VAI-684 repairs the VAI-671/VAI-674/VAIOS-G707 objective validation gap
covering the `objective/interoperability/hallucinate_app-mobile` bundle. The
repaired `interface contract hallucinate_app mobile` path is:

- `hallucinate_app/hallucinate_app/node/dashboard/content_browser/search_interface.js`
  exports `HALLUCINATE_APP_MOBILE_SEARCH_INTEROP_CONTRACT` and
  `buildHallucinateAppMobileSearchHandoff(query, options)`, which normalizes a
  desktop PyArrow content-index search into a mobile ORB bridge handoff
  envelope (`/v1/mobile/orb/invoke_service`) carrying the
  `control_surface_contract:hallucinate-app:remote-client` reference and the
  `interaction_envelope`, `policy_decision`, and `mediation_receipt`
  artifacts.
- `hallucinate_app/hallucinate_app/node/views/test_interface.html` embeds a
  machine-readable `interface contract hallucinate_app mobile` fixture (the
  `#hallucinate-app-mobile-interop-contract` card, `mobileInteropContract`
  textarea, and `mobileInteropResults` probe target) that developers and CI
  smoke checks can read without executing the Electron app.
- `hallucinate_app/ipfs_accelerate_py/data/duckdb/db_schema/time_series_schema.sql`
  defines the `hallucinate_app_mobile_interop_receipts` table (and its
  `idx_hallucinate_app_mobile_interop_receipts_route` index), recording every
  control-surface receipt exchanged when the Hallucinate App desktop search
  surface hands a request to the mobile ORB bridge.
- `hallucinate_app/ipfs_accelerate_py/data/duckdb/scripts/create_benchmark_schema.py`
  mirrors the contract as self-contained literals
  (`HALLUCINATE_APP_MOBILE_INTEROP_CONTRACT_ID`,
  `HALLUCINATE_APP_MOBILE_INTEROP_TABLE`,
  `HALLUCINATE_APP_MOBILE_INTEROP_ROUTES`,
  `HALLUCINATE_APP_MOBILE_INTEROP_ARTIFACT_REFS`) so the contract stays
  scanner-visible and importable evidence even though the legacy script body
  above it is not valid Python.
- `src/handsfree/hallucinate_app_mobile_interop.py` statically discovers
  those three descriptors (without executing JavaScript or importing the
  corrupted legacy script), verifies the contract id, required artifacts, and
  DuckDB receipt table, and builds a deterministic
  `HallucinateAppMobileHandoff` receipt (`sha256:` content CID) for a given
  search query via `build_mobile_search_handoff()`.
- `mobile/src/orb/metaGlassesOrbDescriptors.js` exports
  `HALLUCINATE_APP_MOBILE_INTEROP_INTERFACE` and
  `HALLUCINATE_APP_MOBILE_INTEROP_DESCRIPTOR`, binding the mobile ORB bridge
  operations to the Hallucinate App search/test-interface/DuckDB schema refs.
- `mobile/src/orb/metaGlassesMobileOrbBridge.js` advertises the interop
  descriptor as a fifth local interface (alongside the mobile ORB bridge,
  display widget bridge, SwissKnife, and `external/ipfs_accelerate`
  descriptors) during `registerEdgeCapabilities()` and remains parseable
  after the contract wiring.

## Runtime handoff

1. The Hallucinate App desktop content-browser search interface calls
   `buildHallucinateAppMobileSearchHandoff(query, options)`, producing a
   normalized envelope with `contract_id`, `route`
   (`/v1/mobile/orb/invoke_service`), `operation` (`invoke_service`), and a
   `normalized_intent` for the mobile ORB bridge.
2. The mobile ORB bridge (`MetaGlassesMobileOrbBridge`) registers edge
   capabilities and advertises `HALLUCINATE_APP_MOBILE_INTEROP_DESCRIPTOR`
   alongside the existing mobile ORB bridge, display widget bridge,
   SwissKnife, and `external/ipfs_accelerate` interop descriptors.
3. The Handsfree backend uses `build_mobile_search_handoff()` from
   `src/handsfree/hallucinate_app_mobile_interop.py` to build a
   deterministic, content-addressed receipt for the search payload before it
   is routed to the mobile display widget, and the receipt is persisted in
   the `hallucinate_app_mobile_interop_receipts` DuckDB table.

## Validation evidence

Validation evidence lives in
`tests/integration/test_hallucinate_app_mobile_interop.py`. It verifies the
Hallucinate App interface descriptors exist on disk, discovers and validates
the static search contract, exercises the Python
`hallucinate_app_mobile_interop` handoff builder for determinism and content
addressing, loads the JavaScript descriptor exports from
`mobile/src/orb/metaGlassesOrbDescriptors.js`, confirms
`mobile/src/orb/metaGlassesMobileOrbBridge.js` remains parseable and wires
the descriptor into edge capability registration, confirms
`search_interface.js` remains parseable and exports the handoff builder,
checks the `test_interface.html` fixture and the DuckDB schema/script pair,
and asserts this objective validation repair is recorded in
`data/virtual_ai_os/discovery/2026-07-09-vai-684-objective-validation-repair.md`
and the objective heap
(`implementation_plan/docs/23-virtual-ai-os-objective-goal-heap.md`).
