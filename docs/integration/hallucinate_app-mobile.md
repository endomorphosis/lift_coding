# Hallucinate App <-> Mobile Interoperability

VAIOS-G707 proves that `hallucinate_app` and `mobile` interoperate through a
shared, importable interface descriptor and a runtime handoff path. The contract
is intentionally narrow: Hallucinate App owns content search and mediation,
while mobile owns the Meta glasses ORB edge session and delivery receipts.

## Interface Contract

- Contract: `handsfree.interop.hallucinate_app_mobile/handoff@0.1.0`
- Objective: `VAIOS-G707`
- Source surface: `hallucinate_app`
- Target surface: `mobile`
- Runtime operation: `dispatch_content_search`
- Mobile descriptor:
  `handsfree.interop.hallucinate_app_mobile.hallucinate_app_mobile_interop@0.1.0`

Mobile exports `HALLUCINATE_APP_MOBILE_INTEROP_INTERFACE` from
`mobile/src/orb/metaGlassesOrbDescriptors.js`. The mobile ORB bridge advertises
that descriptor with the standard `mobile_orb_bridge` and `display_widget_bridge`
descriptors during `registerEdgeCapabilities`, so Hallucinate App can validate
the edge before sending a search handoff.

Hallucinate App exports `HALLUCINATE_APP_MOBILE_SEARCH_DESCRIPTOR` from
`hallucinate_app/hallucinate_app/node/dashboard/content_browser/search_interface.js`.
`SearchInterface.buildMobileHandoffSearchRequest()` turns the current dashboard
query and filters into a mobile ORB handoff envelope with:

- `query`
- `filters`
- `edge_session_id`
- `correlation_id`
- `handoff.ipfs_cids`
- `handoff.libp2p_peer_id`
- `handoff.libp2p_session_id`
- `mediation_receipt`

## Runtime Handoff

1. Mobile registers an ORB edge session with `register_edge_capabilities`.
2. The registration includes `local_interface_cids` for mobile ORB, display
   widget, and Hallucinate App mobile interop descriptors.
3. Hallucinate App builds a `dispatch_content_search` handoff envelope from the
   dashboard search interface.
4. Mobile receives the request through the ORB bridge, records mediation
   artifacts, and returns a receipt CID.
5. Hallucinate App records the evidence in
   `hallucinate_app_mobile_handoff_events` for objective validation and replay.

## Validation

The integration gate is
`tests/integration/test_hallucinate_app_mobile_interop.py`. It verifies that the
contract descriptors are present, the mobile bridge advertises the interop
descriptor, Hallucinate App emits the handoff descriptor, the Electron test view
contains a Mobile ORB runner, and the DuckDB schema can persist runtime handoff
receipts.

