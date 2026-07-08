# Hallucinate App / Mobile Interop

MGW-579 repairs the VAIOS-G707 objective validation gap for the
`objective/interoperability/hallucinate_app-mobile` bundle.

The repaired `interface contract hallucinate_app mobile` path is:

- `hallucinate_app/hallucinate_app/node/dashboard/content_browser/search_interface.js`
  exports `HALLUCINATE_APP_MOBILE_INTEROP_DESCRIPTOR`,
  `HALLUCINATE_APP_CONTENT_BROWSER_OPERATIONS`,
  `HALLUCINATE_APP_MOBILE_WIDGET_ACTIONS`, and
  `buildHallucinateAppMobileInteropHandoff()`. The search UI emits
  `hallucinate-app:mobile-interop-handoff` when a search runs, preserving the
  query/filter payload for mobile display widget rendering.
- `hallucinate_app/hallucinate_app/node/views/test_interface.html` carries the
  machine-readable `hallucinate-app-mobile-interop-fixture` JSON fixture for
  the dashboard test surface.
- `hallucinate_app/ipfs_accelerate_py/data/duckdb/db_schema/time_series_schema.sql`
  defines `hallucinate_app_mobile_interop_events` so Hallucinate App to mobile
  handoff evidence can be stored with benchmark/time-series data.
- `hallucinate_app/ipfs_accelerate_py/data/duckdb/scripts/create_benchmark_schema.py`
  exposes `create_hallucinate_app_mobile_interop_tables()` and
  `HALLUCINATE_APP_MOBILE_INTEROP_TABLES` for the same table.
- `src/handsfree/hallucinate_app_mobile_interop.py` statically discovers those
  Hallucinate App assets without importing submodule Python and builds a
  deterministic `HallucinateAppMobileHandoff` receipt.
- `mobile/src/orb/metaGlassesOrbDescriptors.js` exports the matching
  `HALLUCINATE_APP_MOBILE_INTEROP_INTERFACE` and
  `HALLUCINATE_APP_MOBILE_INTEROP_DESCRIPTOR`.
- `mobile/src/orb/metaGlassesMobileOrbBridge.js` advertises that descriptor
  during edge capability registration alongside the existing mobile, display
  widget, SwissKnife, and IPFS Accelerate descriptors.

## Runtime Handoff

1. Hallucinate App content browser search emits
   `hallucinate-app:mobile-interop-handoff` with the search query, active
   filter, target mobile widget action, schema refs, and VAIOS-G707 metadata.
2. The mobile ORB bridge advertises
   `HALLUCINATE_APP_MOBILE_INTEROP_DESCRIPTOR` when registering edge
   capabilities.
3. The backend can call
   `build_hallucinate_app_mobile_handoff()` from
   `src/handsfree/hallucinate_app_mobile_interop.py` to produce a deterministic
   `sha256:` receipt for the handoff payload.
4. DuckDB records durable evidence in
   `hallucinate_app_mobile_interop_events` with the same
   `interface contract hallucinate_app mobile`, `VAIOS-G707`, and
   `objective validation repair` terms used by the objective scanner.

## Validation Evidence

Validation evidence lives in
`tests/integration/test_hallucinate_app_mobile_interop.py`. It verifies the
Hallucinate App JS descriptor, HTML fixture, DuckDB schema/script entries,
mobile descriptor export, mobile bridge registration wiring, deterministic
Python receipt builder, this document
(`docs/integration/hallucinate_app-mobile.md`), the discovery record
`data/meta_glasses_display_widgets/discovery/2026-07-08-mgw-579-objective-validation-repair.md`,
and the objective heap entry in
`implementation_plan/docs/23-virtual-ai-os-objective-goal-heap.md`.
