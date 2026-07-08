# MGW-579 Objective Validation Repair

Date: 2026-07-08
Task: MGW-579
Goal: VAIOS-G707
Bundle: objective/interoperability/hallucinate_app-mobile
Merge key: dce12a84320c8baf
Merge family: objective/VAIOS-G707
Source objective gap: data/meta_glasses_display_widgets/discovery/2026-07-08-mgw-579-objective-gap-7edb316279e5.md

## Objective Validation Repair

This repair makes the `interface contract hallucinate_app mobile` handoff
scanner-visible and testable in the expected MGW-579 outputs. Hallucinate App
owns the desktop content-browser search surface and emits a normalized mobile
ORB handoff. Mobile owns the ORB descriptor export and advertises that
descriptor during edge capability registration.

Evidence term: objective validation repair.
Evidence term: interface contract hallucinate_app mobile.
Evidence term: hallucinate-app:mobile-interop-handoff.
Evidence term: HALLUCINATE_APP_MOBILE_INTEROP_DESCRIPTOR.
Evidence term: HALLUCINATE_APP_MOBILE_INTEROP_INTERFACE.
Evidence term: hallucinate_app_mobile_interop_events.
Evidence term: VAIOS-G707.

- `tests/integration/test_hallucinate_app_mobile_interop.py`
- `docs/integration/hallucinate_app-mobile.md`
- `hallucinate_app/hallucinate_app/node/dashboard/content_browser/search_interface.js`
- `hallucinate_app/hallucinate_app/node/views/test_interface.html`
- `mobile/src/orb/metaGlassesOrbDescriptors.js`
- `mobile/src/orb/metaGlassesMobileOrbBridge.js`
- `hallucinate_app/ipfs_accelerate_py/data/duckdb/db_schema/time_series_schema.sql`
- `hallucinate_app/ipfs_accelerate_py/data/duckdb/scripts/create_benchmark_schema.py`
- `implementation_plan/docs/23-virtual-ai-os-objective-goal-heap.md`

## Runtime Handoff Evidence

`search_interface.js` exports `HALLUCINATE_APP_MOBILE_INTEROP_DESCRIPTOR` and
`buildHallucinateAppMobileSearchHandoff()`. The generated payload includes the
`hallucinate-app:mobile-interop-handoff` event, the descriptor id, the contract
id, the `/v1/mobile/orb/invoke_service` route, and the normalized search intent
that mobile renders as a card or display-widget result.

`mobile/src/orb/metaGlassesOrbDescriptors.js` exports the matching
`HALLUCINATE_APP_MOBILE_INTEROP_INTERFACE` and descriptor. The descriptor names
VAIOS-G707, the `policy:hallucinate-app:mobile-interop` policy id, the mobile
ORB operations, and the `hallucinate_app_mobile_interop_events` table.

`mobile/src/orb/metaGlassesMobileOrbBridge.js` appends the Hallucinate
App/mobile descriptor to the default edge capability registration, alongside
the local mobile ORB and display-widget descriptors.

The DuckDB schema declares `hallucinate_app_mobile_interop_events` for receipt
storage and keeps `hallucinate_app_mobile_interop_receipts` as a compatibility
view for older scanner terms.

## Validation

Focused validation target:

`python -m pytest tests/integration/test_hallucinate_app_mobile_interop.py -q`

Full supervisor target:

`python -m pytest tests/integration -q`
