# Hallucinate App / Mobile Interop

VAI-674 repairs the VAIOS-G707 objective validation gap covering the
`objective/interoperability/hallucinate_app-mobile` bundle.

The repaired `interface contract hallucinate_app mobile` path is:

- `hallucinate_app/hallucinate_app/node/dashboard/content_browser/search_interface.js`
  exports `HALLUCINATE_APP_MOBILE_SEARCH_INTEROP_CONTRACT`,
  `buildHallucinateAppMobileSearchHandoff()`,
  `HALLUCINATE_APP_MOBILE_INTEROP_DESCRIPTOR`, and
  `emitHallucinateAppMobileInteropHandoff()`. The last function builds a
  normalized handoff envelope for a desktop search query and emits it on the
  `hallucinate-app:mobile-interop-handoff` event name.
- `hallucinate_app/hallucinate_app/node/views/test_interface.html` carries a
  machine-readable JSON fixture (`#hallucinate-app-mobile-interop-contract`)
  with the `contract_id`, `event_name`, `receipt_table`, and `validation`
  fields that mirror the JavaScript descriptors, so the handoff contract can
  be validated without executing the Electron dashboard.
- `hallucinate_app/ipfs_accelerate_py/data/duckdb/db_schema/time_series_schema.sql`
  defines the `hallucinate_app_mobile_interop_receipts` table (contract id,
  source/target surface, route, operation, edge session, binding handle,
  correlation id, and the `interaction_envelope`/`policy_decision`/
  `mediation_receipt` JSON artifacts) plus a
  `hallucinate_app_mobile_interop_evidence` view recording the `VAI-674` task
  id and `VAIOS-G707` goal id directly in the DuckDB schema.
- `hallucinate_app/ipfs_accelerate_py/data/duckdb/scripts/create_benchmark_schema.py`
  defines the matching `HALLUCINATE_APP_MOBILE_INTEROP_CONTRACT_ID`,
  `HALLUCINATE_APP_MOBILE_INTEROP_TABLE`, `HALLUCINATE_APP_MOBILE_INTEROP_ROUTES`,
  and `HALLUCINATE_APP_MOBILE_INTEROP_ARTIFACT_REFS` constants, plus the
  `VAI-674`/`VAIOS-G707`-specific constants and
  `build_hallucinate_app_mobile_interop_evidence_record()` helper. This block
  is self-contained (pure literals) so it stays importable/parseable
  evidence independent of the pre-existing, unrelated legacy script body
  above it.
- `mobile/src/orb/metaGlassesOrbDescriptors.js` exports
  `HALLUCINATE_APP_MOBILE_INTEROP_INTERFACE` and
  `HALLUCINATE_APP_MOBILE_INTEROP_DESCRIPTOR`, binding the mobile ORB bridge
  and display widget operations to the `hallucinate_app` search interface and
  DuckDB schema refs.
- `mobile/src/orb/metaGlassesMobileOrbBridge.js` advertises the
  `HALLUCINATE_APP_MOBILE_INTEROP_DESCRIPTOR` as a fifth local interface
  during edge capability registration, alongside the existing mobile ORB
  bridge, display widget, SwissKnife, and `external/ipfs_accelerate`
  descriptors, and keeps diagnostics parseable after the contract wiring.

## Runtime handoff

1. The Hallucinate App desktop search surface calls
   `buildHallucinateAppMobileSearchHandoff(query, options)` to build a
   normalized handoff envelope, then
   `emitHallucinateAppMobileInteropHandoff(eventBus, query, options)` emits
   that envelope on the `hallucinate-app:mobile-interop-handoff` event.
2. The mobile ORB bridge registers edge capabilities and advertises the
   `HALLUCINATE_APP_MOBILE_INTEROP_DESCRIPTOR` alongside the existing mobile
   ORB bridge, display widget, SwissKnife, and `external/ipfs_accelerate`
   descriptors.
3. The handoff envelope's `route` (`/v1/mobile/orb/invoke_service`) and
   `operation` (`invoke_service`) map directly onto the mobile ORB bridge's
   `invoke_service` operation, and the resulting receipt is recorded in the
   `hallucinate_app_mobile_interop_receipts` DuckDB table.

## Validation evidence

This document (`docs/integration/hallucinate_app-mobile.md`) and validation
evidence live in
`tests/integration/test_hallucinate_app_mobile_interop.py`. It verifies the
Hallucinate App search-interface and test-interface fixtures exist and
declare the expected contract fields, loads the JavaScript descriptor
exports from `mobile/src/orb/metaGlassesOrbDescriptors.js` and
`hallucinate_app/hallucinate_app/node/dashboard/content_browser/search_interface.js`,
verifies the DuckDB schema/script pair records the shared
`hallucinate_app_mobile_interop_receipts` table and `VAI-674`/`VAIOS-G707`
evidence constants, exercises the mobile ORB bridge's descriptor wiring, and
asserts this objective validation repair is recorded in
`data/virtual_ai_os/discovery/2026-07-08-vai-674-objective-validation-repair.md`
and the objective heap
(`implementation_plan/docs/23-virtual-ai-os-objective-goal-heap.md`).
