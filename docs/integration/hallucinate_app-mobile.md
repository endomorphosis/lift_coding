# Hallucinate App / Mobile Interop

VAI-674 repairs the VAIOS-G707 objective validation gap for the
`objective/interoperability/hallucinate_app-mobile` bundle.

The repaired `interface contract hallucinate_app mobile` path is:

- `hallucinate_app/hallucinate_app/node/dashboard/content_browser/search_interface.js`
  exports `HALLUCINATE_APP_MOBILE_SEARCH_INTEROP_CONTRACT`,
  `HALLUCINATE_APP_MOBILE_INTEROP_DESCRIPTOR`, and
  `buildHallucinateAppMobileSearchHandoff()`. The handoff builder emits
  `hallucinate-app:mobile-interop-handoff` payloads for the mobile ORB
  `invoke_service` route.
- `mobile/src/orb/metaGlassesOrbDescriptors.js` exports the matching
  `HALLUCINATE_APP_MOBILE_INTEROP_INTERFACE` and
  `HALLUCINATE_APP_MOBILE_INTEROP_DESCRIPTOR`, including the VAI-674
  `objective validation repair` evidence, schema refs, mobile ORB methods,
  and Hallucinate App search operations.
- `mobile/src/orb/metaGlassesMobileOrbBridge.js` advertises the Hallucinate
  App/mobile descriptor during edge capability registration so a mobile edge
  session can accept Hallucinate App search handoffs alongside the existing
  mobile bridge descriptors.
- `hallucinate_app/hallucinate_app/node/views/test_interface.html` carries a
  machine-readable fixture for the same interface contract and mobile ORB
  routes.
- `hallucinate_app/ipfs_accelerate_py/data/duckdb/db_schema/time_series_schema.sql`
  defines `hallucinate_app_mobile_interop_receipts` for persisted
  interaction-envelope, policy-decision, and mediation-receipt evidence.
- `hallucinate_app/ipfs_accelerate_py/data/duckdb/scripts/create_benchmark_schema.py`
  mirrors the contract id, table name, mobile routes, and receipt artifact
  refs as importable scanner-visible constants.

## Runtime Handoff

1. The Hallucinate App content browser calls
   `buildHallucinateAppMobileSearchHandoff(query, options)` with the desktop
   search query and current filters.
2. The builder returns a normalized control-surface handoff with
   `contract_id: interface contract hallucinate_app mobile`,
   `descriptor_id: hallucinate-app-mobile-interop@0.1.0`, and
   `event_type: hallucinate-app:mobile-interop-handoff`.
3. The mobile ORB bridge registers edge capabilities with
   `HALLUCINATE_APP_MOBILE_INTEROP_DESCRIPTOR`, binds the `invoke_service`
   route, and preserves the control-surface artifacts expected by the
   Hallucinate App mediation flow.
4. Receipt persistence stores the interaction envelope, policy decision, and
   mediation receipt in `hallucinate_app_mobile_interop_receipts`.

## Validation Evidence

Validation evidence lives in
`tests/integration/test_hallucinate_app_mobile_interop.py`. It verifies the
expected Hallucinate App/mobile artifacts exist, loads the JavaScript
descriptor exports, exercises the search handoff builder, checks the mobile
ORB bridge descriptor advertisement, confirms the persistence schema records
receipt evidence, and asserts this `objective validation repair` is recorded
in `docs/integration/hallucinate_app-mobile.md`,
`data/virtual_ai_os/discovery/2026-07-08-vai-674-objective-validation-repair.md`
and `implementation_plan/docs/23-virtual-ai-os-objective-goal-heap.md`.

Source gap:
`data/virtual_ai_os/discovery/2026-07-08-vai-674-objective-gap-7edb316279e5.md`.
No smaller child goals are required because the existing VAIOS-G707 objective
can be proven by one cohesive Hallucinate App/mobile contract, runtime
handoff, persistence, documentation, and integration-test proof stack.
