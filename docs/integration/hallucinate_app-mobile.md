# Hallucinate App / Mobile Interop

VAI-674 performs an objective validation repair for the VAI-671/VAIOS-G707
objective validation gap covering the
`objective/interoperability/hallucinate_app-mobile` bundle.

The repaired `interface contract hallucinate_app mobile` path is:

- `hallucinate_app/hallucinate_app/node/dashboard/content_browser/search_interface.js`
  exports `HALLUCINATE_APP_MOBILE_SEARCH_INTEROP_CONTRACT`,
  `buildHallucinateAppMobileSearchHandoff()`,
  `HALLUCINATE_APP_MOBILE_INTEROP_DESCRIPTOR`, and
  `emitHallucinateAppMobileInteropHandoff()`. The descriptor records the
  `hallucinate-app:mobile-interop-handoff` event name and the
  `hallucinate_app_mobile_interop_receipts` DuckDB receipt table advertised by
  the mobile ORB descriptor pack.
- `hallucinate_app/hallucinate_app/node/views/test_interface.html` carries a
  machine-readable fixture (`data-contract-id`, `data-event-name`,
  `data-receipt-table`, `data-vai-task-id`, `data-goal-id`) proving the
  contract is scanner-visible and testable.
- `hallucinate_app/ipfs_accelerate_py/data/duckdb/db_schema/time_series_schema.sql`
  defines the `hallucinate_app_mobile_interop_receipts` table (route,
  operation, edge session id, binding handle, correlation id, interaction
  envelope, policy decision, and mediation receipt columns) that records every
  control-surface handoff.
- `hallucinate_app/ipfs_accelerate_py/data/duckdb/scripts/create_benchmark_schema.py`
  mirrors the contract id, receipt table name, routes, and required artifact
  refs as importable Python literals
  (`HALLUCINATE_APP_MOBILE_INTEROP_CONTRACT_ID`,
  `HALLUCINATE_APP_MOBILE_INTEROP_TABLE`,
  `HALLUCINATE_APP_MOBILE_INTEROP_ROUTES`,
  `HALLUCINATE_APP_MOBILE_INTEROP_ARTIFACT_REFS`).
- `src/handsfree/hallucinate_app_mobile_interop.py` statically discovers those
  four descriptors (without importing any `hallucinate_app` JavaScript or
  Python), verifies the event name, receipt table, and required routes are
  declared, and builds a deterministic `HallucinateAppMobileHandoff` receipt
  for the `/v1/mobile/orb/invoke_service` route.
- `mobile/src/orb/metaGlassesOrbDescriptors.js` exports
  `HALLUCINATE_APP_MOBILE_INTEROP_INTERFACE` and
  `HALLUCINATE_APP_MOBILE_INTEROP_DESCRIPTOR`, binding the mobile ORB bridge
  and search-results widget operations to the `hallucinate_app` schema refs.
- `mobile/src/utils/hallucinateAppSearchWidgetContract.js` exports
  `HALLUCINATE_APP_SEARCH_WIDGET_ACTION_CONTRACT`, mapping search widget
  action ids to mobile ORB operations, DAT-style method names, and the
  `hallucinate_app` route each action calls.
- `mobile/src/orb/metaGlassesMobileOrbBridge.js` advertises the interop
  descriptor during edge capability registration and keeps diagnostics
  parseable after the contract wiring.

## Runtime handoff

1. The Hallucinate App desktop content-browser search surface builds a
   normalized handoff envelope with `buildHallucinateAppMobileSearchHandoff()`
   and emits it as a `hallucinate-app:mobile-interop-handoff` event via
   `emitHallucinateAppMobileInteropHandoff()`.
2. The mobile ORB bridge registers edge capabilities and advertises the
   `HALLUCINATE_APP_MOBILE_INTEROP_DESCRIPTOR` alongside the existing mobile
   ORB bridge, display widget, SwissKnife, and IPFS Accelerate descriptors.
3. A search widget action (for example
   `mobile_render_search_results_widget`) resolves to an ORB operation
   (`render_search_results_widget`) and the
   `/v1/mobile/orb/invoke_service` route via
   `hallucinateAppSearchWidgetContract.js`.
4. The Handsfree backend uses `build_hallucinate_app_mobile_handoff()` from
   `src/handsfree/hallucinate_app_mobile_interop.py` to build a deterministic,
   content-addressed receipt (`sha256:` content CID) for the search handoff
   payload before it is routed to the mobile display widget and recorded in
   the `hallucinate_app_mobile_interop_receipts` DuckDB table.

## Validation evidence

Validation evidence lives in
`tests/integration/test_hallucinate_app_mobile_interop.py`. It verifies the
Hallucinate App search/test-interface/DuckDB descriptors exist and declare
the expected contract id, event name, and receipt table, loads the
JavaScript descriptor exports on both the `hallucinate_app` and `mobile`
sides, verifies the search widget action mapping, exercises the Python
`hallucinate_app_mobile_interop` handoff builder, and asserts this objective
validation repair is recorded in
`data/virtual_ai_os/discovery/2026-07-08-vai-674-objective-validation-repair.md`
and the objective heap
(`implementation_plan/docs/23-virtual-ai-os-objective-goal-heap.md`).
