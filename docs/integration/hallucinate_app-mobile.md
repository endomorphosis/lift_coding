# Hallucinate App / Mobile Interop

VAI-674 closes the VAIOS-G707 objective validation repair for the
`objective/interoperability/hallucinate_app-mobile` bundle.

The repaired `interface contract hallucinate_app mobile` path is:

- `hallucinate_app/hallucinate_app/node/dashboard/content_browser/search_interface.js`
  exports `HALLUCINATE_APP_MOBILE_SEARCH_INTEROP_CONTRACT` and builds a
  normalized `invoke_service` handoff for desktop content-browser searches.
- `hallucinate_app/hallucinate_app/node/views/test_interface.html` exposes a
  machine-readable fixture for the Hallucinate App to mobile ORB route.
- `mobile/src/orb/metaGlassesOrbDescriptors.js` exports
  `HALLUCINATE_APP_MOBILE_INTEROP_INTERFACE` and
  `HALLUCINATE_APP_MOBILE_INTEROP_DESCRIPTOR` for mobile capability discovery.
- `mobile/src/utils/hallucinateAppSearchWidgetContract.js` maps mobile search
  widget action ids to ORB operations, DAT-style method names, result targets,
  and the `hallucinate_app_mobile_interop_receipts` receipt table.
- `mobile/src/orb/metaGlassesMobileOrbBridge.js` advertises the Hallucinate App
  interop descriptor during default edge capability registration.
- `hallucinate_app/ipfs_accelerate_py/data/duckdb/db_schema/time_series_schema.sql`
  records handoff receipts in `hallucinate_app_mobile_interop_receipts`.
- `hallucinate_app/ipfs_accelerate_py/data/duckdb/scripts/create_benchmark_schema.py`
  exposes scanner-visible constants for the same contract id, routes, and
  receipt artifacts.

## Runtime Handoff

1. Hallucinate App content search calls
   `buildHallucinateAppMobileSearchHandoff()` with the query, filter, result
   target, and correlation id.
2. The search interface emits `hallucinate_app-mobile:handoff` on the event
   bus and `mobile-handoff` for direct listeners.
3. The mobile ORB bridge registers edge capabilities with the
   `HALLUCINATE_APP_MOBILE_INTEROP_DESCRIPTOR`, then receives the handoff over
   `/v1/mobile/orb/invoke_service`.
4. Mobile search widget actions resolve through
   `HALLUCINATE_APP_SEARCH_WIDGET_ACTION_CONTRACT` and persist mediation
   evidence in `hallucinate_app_mobile_interop_receipts`.

## Validation Evidence

Validation evidence lives in
`tests/integration/test_hallucinate_app_mobile_interop.py` and this contract
note at `docs/integration/hallucinate_app-mobile.md`. The test verifies the
Hallucinate App search handoff, event emission, mobile descriptor exports,
search widget action contract, ORB bridge descriptor registration wiring, HTML
fixture, DuckDB receipt schema, benchmark schema constants, objective heap, and
this objective validation repair record:

`data/virtual_ai_os/discovery/2026-07-08-vai-674-objective-validation-repair.md`.
