# Hallucinate App / Mobile Interop

HAO-751 repairs the HAO-740 retry-budget blocker for `VAIOS-G707` and
`objective/interoperability/hallucinate_app-mobile`.

The repaired `interface contract hallucinate_app mobile` path is:

- `hallucinate_app/hallucinate_app/node/dashboard/content_browser/search_interface.js`
  exports `HALLUCINATE_APP_MOBILE_INTEROP_DESCRIPTOR` and
  `buildHallucinateAppMobileSearchHandoff()`. The builder emits a normalized
  `invoke_service` handoff with `interaction_envelope`, `policy_decision`, and
  `mediation_receipt` artifact requirements.
- `mobile/src/orb/metaGlassesOrbDescriptors.js` exports
  `HALLUCINATE_APP_MOBILE_INTEROP_INTERFACE` and
  `HALLUCINATE_APP_MOBILE_INTEROP_DESCRIPTOR`, binding Hallucinate App desktop
  search requests to the mobile ORB bridge.
- `mobile/src/orb/metaGlassesMobileOrbBridge.js` advertises the Hallucinate App
  descriptor during `register_edge_capabilities`, next to the existing mobile
  ORB, display widget, SwissKnife, and IPFS Accelerate descriptors.
- `hallucinate_app/hallucinate_app/node/views/test_interface.html` carries a
  machine-readable fixture for the same contract, route, and receipt artifacts.
- `hallucinate_app/ipfs_accelerate_py/data/duckdb/db_schema/time_series_schema.sql`
  defines `hallucinate_app_mobile_interop_receipts` for persisted handoff
  evidence.
- `hallucinate_app/ipfs_accelerate_py/data/duckdb/scripts/create_benchmark_schema.py`
  exposes `HALLUCINATE_APP_MOBILE_INTEROP_CONTRACT_ID`,
  `HALLUCINATE_APP_MOBILE_INTEROP_TABLE`,
  `HALLUCINATE_APP_MOBILE_INTEROP_ROUTES`, and
  `HALLUCINATE_APP_MOBILE_INTEROP_ARTIFACT_REFS` for benchmark/schema tooling.

## Runtime handoff

1. Hallucinate App content browser search calls
   `buildHallucinateAppMobileSearchHandoff()` with the query, filter, target,
   correlation id, and timestamp.
2. The payload is routed to `/v1/mobile/orb/invoke_service` with normalized
   intent `hallucinate_app.content_browser.search`, method `invoke_service`,
   and target ref
   `handsfree.meta_glasses.mobile.mobile_orb_bridge.invoke_service`.
3. The mobile ORB bridge advertises
   `HALLUCINATE_APP_MOBILE_INTEROP_DESCRIPTOR` during edge capability
   registration so the desktop handoff can be matched to a local mobile
   interface CID.
4. The receipt path records `interaction_envelope`, `policy_decision`, and
   `mediation_receipt` data in `hallucinate_app_mobile_interop_receipts`.

## Validation evidence

Validation evidence lives in
`tests/integration/test_hallucinate_app_mobile_interop.py`. It verifies the
Hallucinate App search descriptor and handoff builder, the mobile descriptor
exports, mobile ORB bridge advertisement, the HTML fixture, the DuckDB receipt
schema/script evidence, and the objective heap/discovery repair records.
This document is `docs/integration/hallucinate_app-mobile.md`.

The retry-budget source is
`data/hallucinate_multimodal_control/discovery/2026-07-08-hao-751-hao-740-retry-budget.md`.
The repair evidence is
`data/hallucinate_multimodal_control/discovery/2026-07-08-hao-751-hao-740-validation-repair.md`.
This is an `objective validation repair` for HAO-740 and HAO-751.
