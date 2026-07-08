# Hallucinate App Mobile Interop

This document records the VAIOS-G707 objective validation repair for the
`hallucinate_app` and `mobile` interoperability pair.

## Interface Contract

- Contract: `handsfree.hallucinate_app/mobile-search-handoff@0.1.0`
- Action id: `mobile_hallucinate_app_search`
- Runtime handoff: `content-search-to-mobile-results`
- Control route: `hallucinate_app.mobile.search_handoff`
- Event profile: `swissknife.mcp++/event-envelope@0.1.0`

The Hallucinate App content browser builds a runtime handoff envelope in
`hallucinate_app/hallucinate_app/node/dashboard/content_browser/search_interface.js`.
The envelope carries the content search query, filters, IPFS CIDs,
`edge_session_id`, optional `libp2p_peer_id`, and a `mediation_receipt` so the
mobile surface can acknowledge the request without reinterpreting dashboard UI
state.

## Runtime Handoff

The dashboard exports `buildHallucinateAppMobileSearchEnvelope`,
`buildMobileHandoffSearchRequest`, `dispatchMobileAction`,
`publishMobileHandoff`, and `launchMobileSearch`. These functions emit
`hallucinate_app:mobile-handoff-search` and `content-browser:mobile-search`
events for bridge adapters.

The mobile app accepts the same interface contract through
`mobile/src/utils/hallucinateAppMobileInterop.js`. The local structured action
dispatcher in `mobile/src/utils/agentActions.js` recognizes
`mobile_hallucinate_app_search`, normalizes the payload, and navigates to the
`Results` surface with `{ hallucinateAppSearch: payload }`.

## Persistence

`hallucinate_app/ipfs_accelerate_py/data/duckdb/db_schema/time_series_schema.sql`
and
`hallucinate_app/ipfs_accelerate_py/data/duckdb/scripts/create_benchmark_schema.py`
define:

- `hallucinate_app_mobile_handoffs`
- `hallucinate_app_mobile_handoff_assertions`
- `hallucinate_app_mobile_interop_status`

These objects persist interface contract, runtime handoff, control-plane,
mobile payload, IPFS CID, libp2p peer, and mediation receipt evidence for
hardware-free validation and later operator diagnostics.

## Validation

`tests/integration/test_hallucinate_app_mobile_interop.py` proves the objective
validation repair by checking:

- the importable Python contract helper;
- the Node-importable Hallucinate App handoff builder;
- the mobile normalization and local action dispatcher;
- the Hallucinate App operator fixture panel;
- the DuckDB schema and benchmark schema creator;
- the objective heap and discovery evidence.

This closes the retry-budget validation blocker filed by VAI-673 for VAI-671.
