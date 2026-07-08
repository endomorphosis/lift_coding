# Hallucinate App Mobile Interop

MGW-579 repairs the VAIOS-G707 objective validation gap for
`objective/interoperability/hallucinate_app-mobile`.

The repaired `interface contract hallucinate_app mobile` path is:

- `hallucinate_app/hallucinate_app/node/dashboard/content_browser/search_interface.js`
  exports `HALLUCINATE_APP_MOBILE_INTEROP_DESCRIPTOR` and emits
  `hallucinate-app:mobile-interop-handoff` when the desktop content browser
  hands a normalized search request to mobile.
- `mobile/src/orb/metaGlassesOrbDescriptors.js` exports
  `HALLUCINATE_APP_MOBILE_INTEROP_INTERFACE` and
  `HALLUCINATE_APP_MOBILE_INTEROP_DESCRIPTOR`, binding the Hallucinate App
  content-browser handoff to the mobile ORB bridge routes.
- `mobile/src/orb/metaGlassesMobileOrbBridge.js` advertises that descriptor
  during edge capability registration so a mobile edge session can accept the
  Hallucinate App handoff alongside the existing mobile ORB and display-widget
  descriptors.
- `hallucinate_app/hallucinate_app/node/views/test_interface.html` carries the
  same contract, route, event, artifact, and receipt-table fixture for operator
  validation.
- `hallucinate_app/ipfs_accelerate_py/data/duckdb/db_schema/time_series_schema.sql`
  defines `hallucinate_app_mobile_interop_receipts`, and
  `hallucinate_app/ipfs_accelerate_py/data/duckdb/scripts/create_benchmark_schema.py`
  exposes the matching constants so the receipt evidence is scanner-visible.

Validation evidence lives in this document
(`docs/integration/hallucinate_app-mobile.md`) and
`tests/integration/test_hallucinate_app_mobile_interop.py`. The test loads the
Hallucinate App JavaScript handoff builder, verifies the mobile descriptor
exports, confirms the bridge advertises `HALLUCINATE_APP_MOBILE_INTEROP_DESCRIPTOR`,
checks the HTML fixture, and asserts the objective heap plus
`data/meta_glasses_display_widgets/discovery/2026-07-08-mgw-579-objective-validation-repair.md`
record this objective validation repair. No smaller child goals are required.
