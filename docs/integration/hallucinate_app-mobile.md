# Hallucinate App / Mobile Interop

VAI-674 repairs the VAIOS-G707 objective validation gap covering the
`objective/interoperability/hallucinate_app-mobile` bundle.

The repaired `interface contract hallucinate_app mobile` path is:

- `hallucinate_app/hallucinate_app/node/dashboard/content_browser/search_interface.js`
  exports `HALLUCINATE_APP_MOBILE_INTEROP_DESCRIPTOR` and
  `buildHallucinateAppMobileSearchHandoff()`. The search surface emits both
  `hallucinate_app-mobile:handoff` and
  `hallucinate-app:mobile-interop-handoff` events so legacy listeners and the
  objective scanner-visible contract receive the same normalized payload.
- `mobile/src/orb/metaGlassesOrbDescriptors.js` exports
  `HALLUCINATE_APP_MOBILE_INTEROP_INTERFACE` and
  `HALLUCINATE_APP_MOBILE_INTEROP_DESCRIPTOR`, binding Hallucinate App content
  browser operations to the mobile ORB bridge operations.
- `mobile/src/orb/metaGlassesMobileOrbBridge.js` advertises the Hallucinate
  App interop descriptor during edge capability registration alongside the
  existing mobile ORB, display widget, SwissKnife, and IPFS Accelerate
  descriptors.
- `hallucinate_app/hallucinate_app/node/views/test_interface.html` carries a
  machine-readable fixture for the same descriptor, including the
  `objective validation repair` evidence term.
- `hallucinate_app/ipfs_accelerate_py/data/duckdb/db_schema/time_series_schema.sql`
  defines `hallucinate_app_mobile_interop_receipts` for the control-surface
  receipts exchanged during the handoff.
- `hallucinate_app/ipfs_accelerate_py/data/duckdb/scripts/create_benchmark_schema.py`
  exposes `HALLUCINATE_APP_MOBILE_INTEROP_*` constants so schema creation
  tooling can identify the same receipt table, routes, and artifact refs.
- `src/handsfree/hallucinate_app_mobile_interop.py` statically discovers those
  Hallucinate App and mobile descriptors without importing JavaScript, verifies
  required operations and receipt metadata, and builds a deterministic
  `HallucinateAppMobileHandoff` receipt with a `sha256:` content CID.

## Runtime Handoff

1. The Hallucinate App content browser normalizes a desktop search into an
   `invoke_service` handoff for `/v1/mobile/orb/invoke_service`.
2. The mobile ORB bridge registers edge capabilities and advertises
   `HALLUCINATE_APP_MOBILE_INTEROP_DESCRIPTOR`, allowing the backend to bind
   Hallucinate App search events to mobile, Meta glasses, and remote-client
   surfaces.
3. The receipt payload carries `interaction_envelope`, `policy_decision`, and
   `mediation_receipt` artifact refs and can be persisted to
   `hallucinate_app_mobile_interop_receipts`.

## Validation Evidence

Validation evidence lives in this integration note
(`docs/integration/hallucinate_app-mobile.md`) and in
`tests/integration/test_hallucinate_app_mobile_interop.py`. It loads the
JavaScript descriptor exports, checks the Hallucinate App handoff builder,
verifies the mobile bridge advertises the descriptor, exercises the Python
`build_hallucinate_app_mobile_search_handoff()` receipt builder, and asserts
this objective validation repair is recorded in
`data/virtual_ai_os/discovery/2026-07-08-vai-674-objective-validation-repair.md`
and the objective heap
(`implementation_plan/docs/23-virtual-ai-os-objective-goal-heap.md`).
