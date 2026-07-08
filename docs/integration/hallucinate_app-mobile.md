# Hallucinate App Mobile Interoperability

VAIOS-G707 proves `hallucinate_app` and `mobile` interoperate through one
shared control-surface contract instead of separate desktop and handset
protocols.

## Contract

- Contract: `handsfree.hallucinate-app/mobile-search-handoff@0.1.0`
- Control surface: `control_surface_contract:hallucinate-app:remote-client`
- Mobile diagnostics: `handsfree.meta-glasses/mobile-orb-diagnostics@0.1.0`
- Display action contract: `handsfree.meta-glasses/display-widget-action@0.1.0`
- Handoff event: `hallucinate-app:mobile-search-handoff`
- Receipt table: `hallucinate_mobile_handoff_receipts`

`hallucinate_app/hallucinate_app/node/dashboard/content_browser/search_interface.js`
exports `HALLUCINATE_APP_MOBILE_INTEROP_CONTRACT` and emits a mobile handoff
payload whenever the content browser performs a search.  The payload carries the
query, active filter, `control_surface_contract_ref`, target mobile operation,
and fallback display-widget payload expected by the mobile ORB bridge.

`mobile/src/orb/metaGlassesMobileOrbBridge.js` is the handset runtime endpoint.
It normalizes remote client artifacts into
`control_surface_contract:hallucinate-app:remote-client`, produces mediation
receipts, and dispatches display-widget operations through
`mobile/src/utils/metaWearablesDatDisplayWidgetContract.js`.

## Runtime Handoff

1. The Hallucinate App content browser builds a search handoff with
   `buildHallucinateAppMobileSearchHandoff`.
2. The dashboard event bus emits `hallucinate-app:mobile-search-handoff`.
3. The mobile bridge receives or reconstructs the display-widget action and
   normalizes it into `render_widget`, `update_widget`, `clear_widget`, or the
   other display-widget ORB operations.
4. The mobile ORB bridge attaches the Hallucinate App mediation receipt and
   returns receipt CIDs through its diagnostics contract.
5. Integration results can persist the evidence in
   `hallucinate_mobile_handoff_receipts` for objective validation repair.

## Validation

`tests/integration/test_hallucinate_app_mobile_interop.py` is a non-skipped
validation gate.  It validates the dashboard descriptor, the test interface
descriptor, the mobile ORB/display-widget contract terms, and the DuckDB receipt
schema created by
`hallucinate_app/ipfs_accelerate_py/data/duckdb/scripts/create_benchmark_schema.py`.
