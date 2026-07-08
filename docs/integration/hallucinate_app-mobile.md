# Hallucinate App / Mobile Interop

This document is `docs/integration/hallucinate_app-mobile.md`.

HAO-740 repairs the VAIOS-G707 objective validation gap for the
`objective/interoperability/hallucinate_app-mobile` bundle. The repaired
`interface contract hallucinate_app mobile` path proves that the Hallucinate App
desktop surface can hand a content-browser search to the mobile ORB bridge with
scanner-visible interface descriptors, runtime handoff evidence, receipt
storage, and integration tests.

The proof stack is:

- `hallucinate_app/hallucinate_app/node/dashboard/content_browser/search_interface.js`
  exports `HALLUCINATE_APP_MOBILE_INTEROP_INTERFACE`,
  `HALLUCINATE_APP_MOBILE_INTEROP_DESCRIPTOR`, and
  `buildHallucinateAppMobileSearchHandoff()`. Search execution emits both
  `hallucinate-app:mobile-interop-handoff` and the compatibility
  `hallucinate_app-mobile:handoff` event.
- `mobile/src/orb/metaGlassesOrbDescriptors.js` exports the matching
  `HALLUCINATE_APP_MOBILE_INTEROP_INTERFACE` and
  `HALLUCINATE_APP_MOBILE_INTEROP_DESCRIPTOR`, binding the mobile ORB bridge
  operations to the app search interface, app test fixture, and DuckDB receipt
  schema.
- `mobile/src/orb/metaGlassesMobileOrbBridge.js` advertises the Hallucinate App
  descriptor during default edge capability registration, alongside the base
  mobile/display descriptors and the existing SwissKnife/IPFS interop
  descriptors.
- `hallucinate_app/hallucinate_app/node/views/test_interface.html` carries a
  machine-readable fixture for `interface contract hallucinate_app mobile`.
- `hallucinate_app/ipfs_accelerate_py/data/duckdb/db_schema/time_series_schema.sql`
  defines `hallucinate_app_mobile_interop_receipts` with
  `interaction_envelope`, `policy_decision`, and `mediation_receipt` JSON
  columns.
- `hallucinate_app/ipfs_accelerate_py/data/duckdb/scripts/create_benchmark_schema.py`
  exposes `HALLUCINATE_APP_MOBILE_INTEROP_CONTRACT_ID`,
  `HALLUCINATE_APP_MOBILE_INTEROP_TABLE`,
  `HALLUCINATE_APP_MOBILE_INTEROP_ROUTES`, and
  `HALLUCINATE_APP_MOBILE_INTEROP_ARTIFACT_REFS` so benchmark schema creation
  can identify the interop receipt table.

## Runtime Handoff

1. The Hallucinate App content browser calls
   `buildHallucinateAppMobileSearchHandoff()` for
   `hallucinate_app.content_browser.search`.
2. The handoff targets
   `handsfree.meta_glasses.mobile.mobile_orb_bridge.invoke_service` and carries
   the `hallucinate-app-mobile-interop@0.1.0` descriptor id plus schema refs.
3. The mobile ORB bridge advertises the same descriptor during
   `register_edge_capabilities`, allowing the backend to match the app-side
   handoff to the mobile-side ORB operations.
4. Policy mediation produces `interaction_envelope`, `policy_decision`, and
   `mediation_receipt` artifacts, which are stored in
   `hallucinate_app_mobile_interop_receipts`.

## Validation Evidence

Validation evidence lives in
`tests/integration/test_hallucinate_app_mobile_interop.py`. It loads the
JavaScript exports from the app and mobile descriptor files, executes the app
handoff builder, verifies the emitted handoff event names, confirms the mobile
ORB bridge advertises `HALLUCINATE_APP_MOBILE_INTEROP_DESCRIPTOR`, validates
the app test fixture, checks the DuckDB receipt schema/builder terms, and
asserts this HAO-740 objective validation repair is recorded in
`data/hallucinate_multimodal_control/discovery/2026-07-08-hao-740-objective-validation-repair.md`
and `implementation_plan/docs/23-virtual-ai-os-objective-goal-heap.md`.

The original objective gap fingerprint is
`7edb316279e5a093e45d963b421d143361ec8d50`. No smaller child goals are required
because one cohesive contract now covers the app search surface, mobile ORB
descriptor, runtime handoff behavior, receipt persistence, docs, and tests for
VAIOS-G707.
