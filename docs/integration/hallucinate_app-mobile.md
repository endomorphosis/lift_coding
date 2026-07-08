# Hallucinate App / Mobile Interop

MGW-579 repairs the VAIOS-G707 objective validation gap covering the
`objective/interoperability/hallucinate_app-mobile` bundle.

The repaired `interface contract hallucinate_app mobile` path is:

- `hallucinate_app/hallucinate_app/node/dashboard/content_browser/search_interface.js`
  exports `HALLUCINATE_APP_MOBILE_SEARCH_INTEROP_CONTRACT`,
  `HALLUCINATE_APP_MOBILE_INTEROP_DESCRIPTOR`, and
  `buildHallucinateAppMobileSearchHandoff()`. The search surface emits the
  `hallucinate-app:mobile-interop-handoff` event with a normalized mobile ORB
  `invoke_service` payload.
- `mobile/src/orb/metaGlassesOrbDescriptors.js` exports
  `HALLUCINATE_APP_MOBILE_INTEROP_INTERFACE` and
  `HALLUCINATE_APP_MOBILE_INTEROP_DESCRIPTOR`, binding the Hallucinate App
  content-browser methods to the existing mobile ORB bridge operations.
- `mobile/src/orb/metaGlassesMobileOrbBridge.js` advertises the
  `HALLUCINATE_APP_MOBILE_INTEROP_DESCRIPTOR` during edge capability
  registration so a mobile edge session can accept Hallucinate App search
  handoffs without importing Electron or dashboard runtime code.
- `hallucinate_app/hallucinate_app/node/views/test_interface.html` carries a
  machine-readable fixture for `hallucinate-app-mobile-interop@0.1.0`.
- `hallucinate_app/ipfs_accelerate_py/data/duckdb/db_schema/time_series_schema.sql`
  defines `hallucinate_app_mobile_interop_receipts`, the receipt table for
  `interaction_envelope`, `policy_decision`, and `mediation_receipt` evidence.
- `hallucinate_app/ipfs_accelerate_py/data/duckdb/scripts/create_benchmark_schema.py`
  exposes the same contract id, receipt table, routes, and artifact refs as
  scanner-visible benchmark-schema constants.

## Runtime Handoff

1. The Hallucinate App content browser calls
   `buildHallucinateAppMobileSearchHandoff()` when a desktop search is run.
   The payload carries `interface contract hallucinate_app mobile`,
   `hallucinate-app-mobile-interop@0.1.0`, `/v1/mobile/orb/invoke_service`,
   and a normalized `hallucinate_app.content_browser.search` intent.
2. The dashboard event bus emits both the legacy
   `hallucinate_app-mobile:handoff` event and the validation-visible
   `hallucinate-app:mobile-interop-handoff` event for consumers that bind by
   descriptor id.
3. The mobile ORB bridge registers local interface CIDs for the base mobile
   bridge, display widget bridge, SwissKnife interop, IPFS Accelerate interop,
   and Hallucinate App interop. The advertised descriptor includes the schema
   refs and `hallucinate_app_mobile_interop_receipts` storage target.
4. Receipt producers persist the control-surface artifacts into
   `hallucinate_app_mobile_interop_receipts`, preserving the same
   interaction-envelope, policy-decision, and mediation-receipt terms used by
   the control plane.

## Validation Evidence

Validation evidence lives in
`tests/integration/test_hallucinate_app_mobile_interop.py`. It loads the
Hallucinate App and mobile JavaScript descriptor exports, verifies the mobile
ORB bridge advertises `HALLUCINATE_APP_MOBILE_INTEROP_DESCRIPTOR`, parses the
HTML contract fixture, checks the DuckDB receipt schema and benchmark script,
and asserts this objective validation repair is recorded in
`docs/integration/hallucinate_app-mobile.md`,
`data/meta_glasses_display_widgets/discovery/2026-07-08-mgw-579-objective-validation-repair.md`
and `implementation_plan/docs/23-virtual-ai-os-objective-goal-heap.md`.
