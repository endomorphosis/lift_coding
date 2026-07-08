# Hallucinate App Mobile Interop

This document records the interface contract hallucinate_app mobile proof for
VAIOS-G707 / MGW-579.

## Contract

Hallucinate App publishes content-browser handoff events when an operator searches,
filters, or clears PyArrow content index results:

- Event: `hallucinate-app:mobile-interop-handoff`
- Descriptor: `HALLUCINATE_APP_MOBILE_INTEROP_DESCRIPTOR`
- Source: `hallucinate_app.content_browser.search_interface`
- Route: `hallucinate_app` to `mobile` over `mobile_orb_bridge`
- Target surface: `meta_glasses_display`

The payload always carries the evidence terms needed by the mobile bridge:
`contract`, `descriptor`, `source`, `action`, `query`, `filter`, `route`, and
`timestamp`.

## Mobile Receiver

`mobile/src/orb/metaGlassesOrbDescriptors.js` exposes
`HALLUCINATE_APP_MOBILE_INTEROP_INTERFACE` with the local interface key
`handsfree.meta_glasses.mobile.hallucinate_app_mobile_interop@0.1.0`.
`mobile/src/orb/metaGlassesMobileOrbBridge.js` and
`mobile/src/orb/metaGlassesMobileOrbRuntime.js` include that descriptor in default
edge registration, next to the mobile ORB and display widget descriptors.

The mobile operations are:

- `accept_handoff`
- `acknowledge_handoff`

## Persistence

Handoff receipts are stored in DuckDB table
`hallucinate_app_mobile_interop_events`, defined by
`hallucinate_app/ipfs_accelerate_py/data/duckdb/db_schema/time_series_schema.sql`
and created by
`hallucinate_app/ipfs_accelerate_py/data/duckdb/scripts/create_benchmark_schema.py`.

## Validation

`tests/integration/test_hallucinate_app_mobile_interop.py` verifies the descriptor,
dashboard fixture, mobile edge registration, schema table, schema creator, heap
alignment, and objective validation repair evidence file without requiring
Electron, React Native, or DuckDB to be installed.
