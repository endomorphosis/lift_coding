# Hallucinate App / Mobile Interop

HAO-740 (attempt 3) repairs the VAIOS-G707 objective validation gap covering
the `objective/interoperability/hallucinate_app-mobile` bundle.

The repaired `interface contract hallucinate_app mobile` path is:

- `hallucinate_app/hallucinate_app/node/dashboard/content_browser/search_interface.js`
  exports `HALLUCINATE_APP_MOBILE_SEARCH_INTEROP_CONTRACT` and
  `buildHallucinateAppMobileSearchHandoff()`, normalizing a desktop content
  search into an `invoke_service` payload that is handed off to the mobile
  ORB bridge over the shared `control_surface_contract:hallucinate-app:remote-client`
  contract ref.
- `hallucinate_app/hallucinate_app/node/views/test_interface.html` embeds a
  machine-readable fixture of the interface descriptor
  (`data-contract-id="interface contract hallucinate_app mobile"`) inside the
  Electron testing dashboard's "Hallucinate App Mobile Handoff" card, listing
  the `/v1/mobile/orb/register_edge_capabilities`, `/v1/mobile/orb/invoke_service`,
  `/v1/mobile/orb/dispatch_glasses_response`, and `/v1/mobile/orb/diagnostics`
  routes and the `interaction_envelope`, `policy_decision`, and
  `mediation_receipt` required artifacts.
- `hallucinate_app/ipfs_accelerate_py/data/duckdb/db_schema/time_series_schema.sql`
  defines the `hallucinate_app_mobile_interop_receipts` DuckDB table that
  records every control-surface receipt (`interaction_envelope`,
  `policy_decision`, `mediation_receipt`, `receipt_cid`) exchanged during a
  handoff.
- `hallucinate_app/ipfs_accelerate_py/data/duckdb/scripts/create_benchmark_schema.py`
  mirrors the same contract id, table name, routes, and required artifacts as
  importable Python literals (`HALLUCINATE_APP_MOBILE_INTEROP_CONTRACT_ID`,
  `HALLUCINATE_APP_MOBILE_INTEROP_TABLE`, `HALLUCINATE_APP_MOBILE_INTEROP_ROUTES`,
  `HALLUCINATE_APP_MOBILE_INTEROP_ARTIFACT_REFS`) so a benchmark schema build
  can identify and populate interop receipt evidence.
- `src/handsfree/hallucinate_app_mobile_interop.py` statically discovers those
  four descriptors (without executing any `hallucinate_app` Node.js code),
  verifies the required routes, artifacts, and DuckDB table are present, and
  builds a deterministic `HallucinateAppMobileHandoff` receipt
  (`build_hallucinate_app_mobile_search_handoff()`).
- `mobile/src/orb/metaGlassesOrbDescriptors.js` exports
  `HALLUCINATE_APP_MOBILE_INTEROP_INTERFACE` and
  `HALLUCINATE_APP_MOBILE_INTEROP_DESCRIPTOR`, binding the mobile ORB bridge
  to the `hallucinate_app` search/test-interface/DuckDB descriptors.
- `mobile/src/utils/hallucinateAppMobileSearchContract.js` exports
  `HALLUCINATE_APP_MOBILE_SEARCH_ACTION_CONTRACT`, mapping mobile search
  widget action ids to mobile ORB operations, DAT-style method names, and
  transport routes.
- `mobile/src/orb/metaGlassesMobileOrbBridge.js` advertises the interop
  descriptor during edge capability registration (alongside the existing
  swissknife and `external/ipfs_accelerate` interop descriptors) and keeps
  diagnostics parseable after the contract wiring.

## Runtime handoff

1. The Hallucinate App desktop content-browser search surface calls
   `buildHallucinateAppMobileSearchHandoff(query, options)` to normalize a
   search request into an `invoke_service` envelope addressed at
   `/v1/mobile/orb/invoke_service`.
2. The mobile ORB bridge registers edge capabilities and advertises the
   `HALLUCINATE_APP_MOBILE_INTEROP_DESCRIPTOR` alongside the existing mobile
   ORB bridge, display widget, swissknife, and `external/ipfs_accelerate`
   interop descriptors.
3. A mobile search widget action (for example
   `mobile_dispatch_hallucinate_app_search_query`) resolves to an ORB
   operation (`invoke_service`) and a DAT-style method
   (`dispatchHallucinateAppSearchQuery`) via
   `hallucinateAppMobileSearchContract.js`.
4. The Handsfree backend uses
   `build_hallucinate_app_mobile_search_handoff()` from
   `src/handsfree/hallucinate_app_mobile_interop.py` to build a
   deterministic, content-addressed receipt (`sha256:` content CID) for the
   search payload before it is routed to the mobile display widget, and the
   `hallucinate_app_mobile_interop_receipts` DuckDB table records the
   `interaction_envelope`, `policy_decision`, and `mediation_receipt`
   artifacts for that handoff.

## Validation evidence

Validation evidence lives in
`tests/integration/test_hallucinate_app_mobile_interop.py`. It verifies the
four `hallucinate_app` descriptors exist and declare the expected contract
id/routes/table, loads the JavaScript descriptor exports (search interface,
mobile ORB descriptor, and mobile search action contract), exercises the
Python `hallucinate_app_mobile_interop` handoff builder for determinism and
error handling, checks the Electron testing dashboard fixture in
`test_interface.html`, and asserts this objective validation repair is
recorded in
`data/hallucinate_multimodal_control/discovery/2026-07-08-hao-740-objective-validation-repair.md`
plus the attempt-three confirmation record
`data/hallucinate_multimodal_control/discovery/2026-07-08-hao-740-attempt-3-validation-confirmation.md`
and the objective heap
(`implementation_plan/docs/23-virtual-ai-os-objective-goal-heap.md`).
