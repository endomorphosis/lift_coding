# Hallucinate App / Mobile Interop

MGW-579 repairs the `VAIOS-G707` objective validation gap for the
`objective/interoperability/hallucinate_app-mobile` bundle, recorded in
`data/meta_glasses_display_widgets/discovery/2026-07-08-mgw-579-objective-gap-7edb316279e5.md`
(fingerprint `7edb316279e5a093e45d963b421d143361ec8d50`).

## Goal

Prove `hallucinate_app` interoperates with `mobile` through importable
contracts, interface descriptors, runtime handoff behavior, and integration
tests. This document is `docs/integration/hallucinate_app-mobile.md`.

## The `interface contract hallucinate_app mobile` path

- `hallucinate_app/hallucinate_app/node/dashboard/content_browser/search_interface.js`
  exports `HALLUCINATE_APP_MOBILE_SEARCH_INTEROP_CONTRACT` and
  `buildHallucinateAppMobileSearchHandoff()`. The desktop dashboard's content
  search surface uses these to normalize a search query into a handoff
  envelope routed to `/v1/mobile/orb/invoke_service` on the mobile ORB
  bridge, with a `normalized_intent` targeting
  `handsfree.meta_glasses.mobile.mobile_orb_bridge.invoke_service`.
- `hallucinate_app/hallucinate_app/node/views/test_interface.html` carries a
  machine-readable fixture of the same contract
  (`data-contract-id="interface contract hallucinate_app mobile"`) and a
  runtime handoff probe panel ("Hallucinate App Mobile Handoff") plus a live
  backend integration test for `GET /v1/mobile/orb/diagnostics`.
- `hallucinate_app/ipfs_accelerate_py/data/duckdb/db_schema/time_series_schema.sql`
  defines the `hallucinate_app_mobile_interop_receipts` DuckDB table that
  records the control-surface receipts (`interaction_envelope`,
  `policy_decision`, `mediation_receipt`) exchanged during each handoff, keyed
  by `route` and `operation`.
- `hallucinate_app/ipfs_accelerate_py/data/duckdb/scripts/create_benchmark_schema.py`
  mirrors those constants in pure, self-contained Python literals
  (`HALLUCINATE_APP_MOBILE_INTEROP_CONTRACT_ID`,
  `HALLUCINATE_APP_MOBILE_INTEROP_TABLE`,
  `HALLUCINATE_APP_MOBILE_INTEROP_ROUTES`,
  `HALLUCINATE_APP_MOBILE_INTEROP_ARTIFACT_REFS`) so a benchmark schema build
  can identify and populate interop receipt evidence without depending on the
  rest of that legacy script.
- `mobile/src/orb/metaGlassesOrbDescriptors.js` exports the mobile-side
  counterpart: `HALLUCINATE_APP_MOBILE_INTEROP_CONTRACT` (the same flat
  contract fixture embedded in `test_interface.html`),
  `HALLUCINATE_APP_MOBILE_INTEROP_INTERFACE` (an MCP-IDL-style interface
  descriptor scoped to `VAIOS-G707`, binding both the mobile ORB bridge
  operations and the display widget bridge operations to the Hallucinate App
  search interface and test interface files), and
  `HALLUCINATE_APP_MOBILE_INTEROP_DESCRIPTOR` (the full descriptor with
  `schema_refs`, `runtime_handoff`, and `validation` metadata pointing back
  at this objective gap and its repair).
- `mobile/src/orb/metaGlassesMobileOrbBridge.js` advertises the
  `HALLUCINATE_APP_MOBILE_INTEROP_DESCRIPTOR` alongside the existing mobile
  ORB bridge, display widget, SwissKnife, and `external/ipfs_accelerate`
  interop descriptors during `register_edge_capabilities`, and implements
  `handleHallucinateAppMobileSearchHandoff()` to actually run the handoff:
  it validates the incoming `contract_id`, requires an active edge session,
  invokes `invoke_service` with the normalized intent's arguments, and
  dispatches the service result to the requested mobile render target
  (`mobile_card` by default) through `dispatch_glasses_response`.

## Runtime handoff

1. The Hallucinate App desktop search surface calls
   `buildHallucinateAppMobileSearchHandoff(query, options)` to produce a
   normalized envelope carrying `contract_id`,
   `control_surface_contract_ref`, `payload`, and `normalized_intent`.
2. The mobile ORB bridge's `handleHallucinateAppMobileSearchHandoff()`
   receives that envelope, checks it against
   `HALLUCINATE_APP_MOBILE_INTEROP_CONTRACT.contract_id`, and calls
   `invokeService()` with the normalized intent's method and arguments,
   producing a real control-surface receipt (`receipt_cid`,
   `policy_decision`, `mediation_receipt`).
3. The bridge then calls `dispatchGlassesResponse()` with the service result
   routed to the `result_target` requested by the desktop surface
   (`mobile_card` by default), completing the round trip.
4. `mobile/src/orb/__tests__/metaGlassesMobileOrbBridge.hallucinateAppInterop.test.js`
   exercises this handoff against a mocked backend, asserting both the
   `invoke_service` and `dispatch_glasses_response` calls and their
   correlation ids, plus the failure paths (unsupported contract id, missing
   edge session).

## Validation evidence

Validation evidence lives in
`tests/integration/test_hallucinate_app_mobile_interop.py`. It:

- Loads the `HALLUCINATE_APP_MOBILE_SEARCH_INTEROP_CONTRACT` export and
  invokes `buildHallucinateAppMobileSearchHandoff()` from
  `hallucinate_app/hallucinate_app/node/dashboard/content_browser/search_interface.js`
  through a Node VM to prove the desktop-side contract and handoff builder
  are importable and produce the expected envelope shape.
- Loads `HALLUCINATE_APP_MOBILE_INTEROP_CONTRACT`,
  `HALLUCINATE_APP_MOBILE_INTEROP_INTERFACE`, and
  `HALLUCINATE_APP_MOBILE_INTEROP_DESCRIPTOR` from
  `mobile/src/orb/metaGlassesOrbDescriptors.js` and asserts they agree with
  the desktop-side contract (same `contract_id`,
  `control_surface_contract_ref`, and route set).
- Confirms `mobile/src/orb/metaGlassesMobileOrbBridge.js` remains valid ESM
  after the contract wiring, imports the new descriptor, advertises it during
  edge capability registration, and defines
  `handleHallucinateAppMobileSearchHandoff`.
- Confirms the DuckDB schema and benchmark schema script under
  `hallucinate_app/ipfs_accelerate_py/data/duckdb` declare the
  `hallucinate_app_mobile_interop_receipts` table and the matching
  self-contained Python constants.
- Confirms `hallucinate_app/hallucinate_app/node/views/test_interface.html`
  carries the machine-readable fixture for the same contract.
- Asserts this objective validation repair is recorded in
  `data/meta_glasses_display_widgets/discovery/2026-07-08-mgw-579-objective-validation-repair.md`
  and the objective heap
  (`implementation_plan/docs/23-virtual-ai-os-objective-goal-heap.md`).
