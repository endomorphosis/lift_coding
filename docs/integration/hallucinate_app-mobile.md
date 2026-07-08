# Hallucinate App / Mobile Interop

VAI-674 closes the VAIOS-G707 objective validation repair for `interface contract hallucinate_app mobile`.

## Contract

- Producer: `hallucinate_app`
- Consumer: `mobile`
- Interface contract: `interface contract hallucinate_app mobile`
- Descriptor id: `hallucinate-app-mobile-interop@0.1.0`
- Runtime event: `hallucinate-app:mobile-interop-handoff`
- ORB route: `/v1/mobile/orb/invoke_service`
- Operation: `invoke_service`
- Control surface contract ref: `control_surface_contract:hallucinate-app:remote-client`

The desktop content browser builds the handoff in `hallucinate_app/hallucinate_app/node/dashboard/content_browser/search_interface.js`.
`buildHallucinateAppMobileSearchHandoff()` normalizes a content search into a mobile ORB `invoke_service` payload with `interaction_envelope`, `policy_decision`, and `mediation_receipt` artifact requirements. `SearchInterface.search()` emits both the legacy `hallucinate_app-mobile:handoff` event and the canonical `hallucinate-app:mobile-interop-handoff` event.

## Mobile Descriptor

`mobile/src/orb/metaGlassesOrbDescriptors.js` exports `HALLUCINATE_APP_MOBILE_INTEROP_INTERFACE` and `HALLUCINATE_APP_MOBILE_INTEROP_DESCRIPTOR`. The interface advertises the mobile ORB bridge methods plus the Hallucinate App search handoff methods:

- `forward_content_browser_search`
- `render_content_search_results`
- `open_content_result`
- `acknowledge_mobile_handoff`

`mobile/src/orb/metaGlassesMobileOrbBridge.js` adds the descriptor to default edge capability registration, so a mobile edge session advertises VAIOS-G707 support beside the base ORB, display widget, SwissKnife, and ipfs_accelerate interfaces.

## Evidence Persistence

`hallucinate_app/ipfs_accelerate_py/data/duckdb/db_schema/time_series_schema.sql` defines `hallucinate_app_mobile_interop_receipts` and `hallucinate_app_mobile_interop_events` for receipt and event evidence. `hallucinate_app/ipfs_accelerate_py/data/duckdb/scripts/create_benchmark_schema.py` exposes matching constants so benchmark schema tooling can discover the same tables and the `hallucinate-app:mobile-interop-handoff` event name.

## Validation

`tests/integration/test_hallucinate_app_mobile_interop.py` is the validation gate for this objective. It proves:

- the Hallucinate App search handoff payload is deterministic and includes the descriptor;
- the mobile descriptor exports the matching `HALLUCINATE_APP_MOBILE_INTEROP_INTERFACE`;
- the mobile ORB bridge advertises `HALLUCINATE_APP_MOBILE_INTEROP_DESCRIPTOR`;
- the HTML fixture, DuckDB schema, benchmark schema constants, discovery note, and objective heap contain the `objective validation repair` evidence terms.

Evidence paths:

- `tests/integration/test_hallucinate_app_mobile_interop.py`
- `docs/integration/hallucinate_app-mobile.md`
- `data/virtual_ai_os/discovery/2026-07-08-vai-674-objective-validation-repair.md`
- `hallucinate_app/hallucinate_app/node/dashboard/content_browser/search_interface.js`
- `mobile/src/orb/metaGlassesOrbDescriptors.js`
- `mobile/src/orb/metaGlassesMobileOrbBridge.js`

No smaller child goals are required for VAIOS-G707.
