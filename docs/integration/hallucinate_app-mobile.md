# Hallucinate App / Mobile Interop

MGW-579 repairs the VAIOS-G707 objective validation gap covering the
`objective/interoperability/hallucinate_app-mobile` bundle. This document is
`docs/integration/hallucinate_app-mobile.md`.

The repaired `interface contract hallucinate_app mobile` path is:

- `hallucinate_app/hallucinate_app/node/dashboard/content_browser/search_interface.js`
  exports `HALLUCINATE_APP_MOBILE_SEARCH_INTEROP_CONTRACT`,
  `HALLUCINATE_APP_MOBILE_INTEROP_DESCRIPTOR`, and
  `buildHallucinateAppMobileSearchHandoff()`. A desktop content-browser search
  emits the `hallucinate_app-mobile:handoff` event with a normalized
  `/v1/mobile/orb/invoke_service` payload.
- `mobile/src/orb/metaGlassesOrbDescriptors.js` exports
  `HALLUCINATE_APP_MOBILE_INTEROP_INTERFACE` and
  `HALLUCINATE_APP_MOBILE_INTEROP_DESCRIPTOR`, binding Hallucinate App search
  handoffs to mobile ORB bridge methods and the nested Hallucinate App DuckDB
  receipt schema.
- `mobile/src/orb/metaGlassesMobileOrbBridge.js` advertises the
  Hallucinate App/mobile descriptor during `register_edge_capabilities`, next
  to the existing SwissKnife/mobile and ipfs_accelerate/mobile descriptors.
- `hallucinate_app/hallucinate_app/node/views/test_interface.html` carries a
  machine-readable fixture for `interface contract hallucinate_app mobile` with
  the `/v1/mobile/orb/register_edge_capabilities`,
  `/v1/mobile/orb/invoke_service`,
  `/v1/mobile/orb/dispatch_glasses_response`, and
  `/v1/mobile/orb/diagnostics` routes.
- `hallucinate_app/ipfs_accelerate_py/data/duckdb/db_schema/time_series_schema.sql`
  defines the `hallucinate_app_mobile_interop_receipts` receipt table for
  `interaction_envelope`, `policy_decision`, and `mediation_receipt` evidence.
- `hallucinate_app/ipfs_accelerate_py/data/duckdb/scripts/create_benchmark_schema.py`
  exposes scanner-visible constants for the same contract id, route set, and
  receipt table.
- `src/handsfree/hallucinate_app_mobile_interop.py` statically discovers those
  Hallucinate App and mobile descriptors without booting Electron or React
  Native, then builds a deterministic `HallucinateAppMobileHandoff` receipt
  with a `sha256:` content CID.

## Runtime Handoff

1. Hallucinate App builds a search handoff with
   `buildHallucinateAppMobileSearchHandoff()`.
2. The search interface emits `hallucinate_app-mobile:handoff` with
   `descriptor_id: hallucinate-app-mobile-interop@0.1.0`,
   `route: /v1/mobile/orb/invoke_service`, and the required
   `interaction_envelope`, `policy_decision`, and `mediation_receipt`
   artifact refs.
3. The mobile ORB bridge advertises
   `HALLUCINATE_APP_MOBILE_INTEROP_DESCRIPTOR` during edge registration so the
   mobile runtime can accept the handoff through the existing
   `invoke_service` and `dispatch_glasses_response` methods.
4. Receipt evidence can be persisted in
   `hallucinate_app_mobile_interop_receipts` for objective scanner and
   benchmark-schema validation.

## Validation Evidence

Validation evidence lives in
`tests/integration/test_hallucinate_app_mobile_interop.py`. It verifies the
JavaScript descriptor exports, checks that `MetaGlassesMobileOrbBridge`
advertises the descriptor, validates the test-interface and DuckDB receipt
schema terms, exercises
`src/handsfree/hallucinate_app_mobile_interop.py`, and asserts this
objective validation repair is recorded in
`data/meta_glasses_display_widgets/discovery/2026-07-08-mgw-579-objective-validation-repair.md`
and `implementation_plan/docs/23-virtual-ai-os-objective-goal-heap.md`.
