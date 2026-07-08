# Hallucinate App / Mobile Interop

This note records the MGW-579 objective validation repair for VAIOS-G707.
It proves the `interface contract hallucinate_app mobile` path with a
scanner-visible descriptor, a mobile ORB registration, a runtime handoff
payload, and DuckDB time-series evidence.

Objective bundle: `objective/interoperability/hallucinate_app-mobile`.

Primary proof files:

- `tests/integration/test_hallucinate_app_mobile_interop.py`
- `docs/integration/hallucinate_app-mobile.md`
- `hallucinate_app/hallucinate_app/node/dashboard/content_browser/search_interface.js`
- `hallucinate_app/hallucinate_app/node/views/test_interface.html`
- `mobile/src/orb/metaGlassesOrbDescriptors.js`
- `mobile/src/orb/metaGlassesMobileOrbBridge.js`
- `hallucinate_app/ipfs_accelerate_py/data/duckdb/db_schema/time_series_schema.sql`
- `hallucinate_app/ipfs_accelerate_py/data/duckdb/scripts/create_benchmark_schema.py`

## Contract

- Source surface: `hallucinate_app`
- Target surface: `mobile`
- Contract id: `interface contract hallucinate_app mobile`
- Descriptor id: `hallucinate-app-mobile-interop@0.1.0`
- Handoff event: `hallucinate-app:mobile-interop-handoff`
- Mobile policy id: `policy:hallucinate-app:mobile-interop`

`hallucinate_app/hallucinate_app/node/dashboard/content_browser/search_interface.js`
exports `HALLUCINATE_APP_MOBILE_INTEROP_DESCRIPTOR` and
`buildHallucinateAppMobileSearchHandoff()`. The builder normalizes a desktop
content-browser search into the mobile ORB `invoke_service` route with
`interaction_envelope`, `policy_decision`, and `mediation_receipt` artifact
requirements.

`mobile/src/orb/metaGlassesOrbDescriptors.js` exports
`HALLUCINATE_APP_MOBILE_INTEROP_INTERFACE` and
`HALLUCINATE_APP_MOBILE_INTEROP_DESCRIPTOR`. The descriptor advertises the
same contract id and registers `hallucinate_app_mobile_interop_events` as the
time-series table for receipt evidence.

`mobile/src/orb/metaGlassesMobileOrbBridge.js` includes the descriptor during
`register_edge_capabilities`, so a mobile edge session can discover the
Hallucinate App handoff without importing Electron or dashboard runtime code.

## Fixtures and Storage

`hallucinate_app/hallucinate_app/node/views/test_interface.html` includes a
machine-readable fixture for the contract, descriptor id, handoff event, and
mobile ORB routes.

`hallucinate_app/ipfs_accelerate_py/data/duckdb/db_schema/time_series_schema.sql`
declares `hallucinate_app_mobile_interop_events` and a compatibility view named
`hallucinate_app_mobile_interop_receipts`. The schema creation script records
the same table in `HALLUCINATE_APP_MOBILE_INTEROP_TABLE`.

## Validation

Focused validation:

```text
python -m pytest tests/integration/test_hallucinate_app_mobile_interop.py -q
```

Supervisor validation:

```text
python -m pytest tests/integration -q
```

The discovery record for this objective validation repair is
`data/meta_glasses_display_widgets/discovery/2026-07-08-mgw-579-objective-validation-repair.md`.
