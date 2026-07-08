# Hallucinate App / Mobile Interop

VAI-674 repairs VAIOS-G707 for `objective/interoperability/hallucinate_app-mobile`.
The objective validation repair proves the `interface contract hallucinate_app mobile`
handoff from Hallucinate App's content-browser search surface to the mobile ORB
bridge.

## Contract

- Goal: `VAIOS-G707`
- Interface contract: `interface contract hallucinate_app mobile`
- Runtime event: `hallucinate-app:mobile-interop-handoff`
- Source surface: `hallucinate_app`
- Target surface: `mobile`
- Canonical route: `/v1/mobile/orb/invoke_service`
- Receipt artifacts: `interaction_envelope`, `policy_decision`, `mediation_receipt`

## Evidence

- `src/handsfree/hallucinate_app_mobile_interop.py` is the importable Python
  contract helper. It statically discovers the Hallucinate App search interface,
  Hallucinate test fixture, mobile ORB descriptors, mobile ORB bridge, and
  DuckDB persistence schema before building a deterministic handoff receipt.
- `hallucinate_app/hallucinate_app/node/dashboard/content_browser/search_interface.js`
  exports `HALLUCINATE_APP_MOBILE_INTEROP_INTERFACE`,
  `HALLUCINATE_APP_MOBILE_INTEROP_DESCRIPTOR`, and
  `buildHallucinateAppMobileSearchHandoff()`. The search surface emits
  `hallucinate-app:mobile-interop-handoff` and keeps the older
  `hallucinate_app-mobile:handoff` event for compatibility.
- `mobile/src/orb/metaGlassesOrbDescriptors.js` exports the matching
  `HALLUCINATE_APP_MOBILE_INTEROP_INTERFACE` and
  `HALLUCINATE_APP_MOBILE_INTEROP_DESCRIPTOR`.
- `mobile/src/orb/metaGlassesMobileOrbBridge.js` advertises the Hallucinate App
  descriptor during mobile ORB edge capability registration.
- `hallucinate_app/hallucinate_app/node/views/test_interface.html` contains the
  machine-readable fixture for `VAIOS-G707`, the canonical runtime event, and
  the descriptor symbols.
- `hallucinate_app/ipfs_accelerate_py/data/duckdb/db_schema/time_series_schema.sql`
  records `hallucinate_app_mobile_interop_receipts` and
  `hallucinate_app_mobile_interop_events`.
- `hallucinate_app/ipfs_accelerate_py/data/duckdb/scripts/create_benchmark_schema.py`
  exposes scanner-visible constants for the same contract, event name,
  descriptor symbols, routes, and persistence tables.
- `tests/integration/test_hallucinate_app_mobile_interop.py` validates the
  importable contract, JS exports, mobile bridge wiring, fixture/schema/script
  terms, this document, discovery evidence, and the objective heap.
- `docs/integration/hallucinate_app-mobile.md` is this contract note for the
  supervisor-fed objective heap.

Discovery evidence is recorded in
`data/virtual_ai_os/discovery/2026-07-08-vai-674-objective-validation-repair.md`.
No smaller child goals are needed; the validation gap is a single contract,
runtime handoff, persistence, docs, and test repair.
