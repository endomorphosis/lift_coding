# VAI-674 Objective Validation Repair

Date: 2026-07-08
Task: VAI-674
Attempt: 2
Goal: VAIOS-G707
Bundle: objective/interoperability/hallucinate_app-mobile
Merge key: dce12a84320c8baf
Merge family: objective/VAIOS-G707
Source objective gap: data/virtual_ai_os/discovery/2026-07-08-vai-674-objective-gap-7edb316279e5.md

## Objective Validation Repair

This repair makes the `interface contract hallucinate_app mobile` handoff
scanner-visible and testable in the expected VAI-674 outputs. `hallucinate_app`
owns the Electron desktop content-browser search surface, its machine-readable
test-interface fixture, and the DuckDB time-series/benchmark schema
descriptors that back the `hallucinate_app_mobile_interop_receipts` receipt
table. `mobile` owns the ORB descriptor exports and the search widget action
mapping that let the Handsfree mobile client render a Hallucinate App search
handoff without importing any JavaScript or Python from the `hallucinate_app`
submodule.

Evidence term: objective validation repair.
Evidence term: interface contract hallucinate_app mobile.
Evidence term: VAIOS-G707.

- `tests/integration/test_hallucinate_app_mobile_interop.py`
- `docs/integration/hallucinate_app-mobile.md`
- `src/handsfree/hallucinate_app_mobile_interop.py`
- `mobile/src/orb/metaGlassesOrbDescriptors.js`
- `mobile/src/utils/hallucinateAppSearchWidgetContract.js`
- `mobile/src/orb/metaGlassesMobileOrbBridge.js`
- `hallucinate_app/hallucinate_app/node/dashboard/content_browser/search_interface.js`
- `hallucinate_app/hallucinate_app/node/views/test_interface.html`
- `hallucinate_app/ipfs_accelerate_py/data/duckdb/db_schema/time_series_schema.sql`
- `hallucinate_app/ipfs_accelerate_py/data/duckdb/scripts/create_benchmark_schema.py`
- `implementation_plan/docs/23-virtual-ai-os-objective-goal-heap.md`

## Runtime Handoff Evidence

`hallucinate_app/hallucinate_app/node/dashboard/content_browser/search_interface.js`
exports `HALLUCINATE_APP_MOBILE_SEARCH_INTEROP_CONTRACT`,
`buildHallucinateAppMobileSearchHandoff()`,
`HALLUCINATE_APP_MOBILE_INTEROP_DESCRIPTOR`, and
`emitHallucinateAppMobileInteropHandoff()`. The descriptor declares the
`hallucinate-app:mobile-interop-handoff` event name and the
`hallucinate_app_mobile_interop_receipts` receipt table.

`hallucinate_app/hallucinate_app/node/views/test_interface.html` carries the
machine-readable fixture (`data-contract-id`, `data-event-name`,
`data-receipt-table`, `data-vai-task-id`, `data-goal-id`).

`hallucinate_app/ipfs_accelerate_py/data/duckdb/db_schema/time_series_schema.sql`
and
`hallucinate_app/ipfs_accelerate_py/data/duckdb/scripts/create_benchmark_schema.py`
record the `hallucinate_app_mobile_interop_receipts` table and its Python
literal mirrors.

`src/handsfree/hallucinate_app_mobile_interop.py` discovers those four
descriptors (without importing any `hallucinate_app` JavaScript or Python),
verifies the event name, receipt table, and required routes are declared,
and builds a deterministic `HallucinateAppMobileHandoff` receipt.

`mobile/src/orb/metaGlassesOrbDescriptors.js` exports
`HALLUCINATE_APP_MOBILE_INTEROP_INTERFACE` and
`HALLUCINATE_APP_MOBILE_INTEROP_DESCRIPTOR`. The descriptor records the
allowed agent, remote_client, mobile, and Meta glasses surfaces, and points to
the `hallucinate_app` schema refs used for the handoff.

`mobile/src/utils/hallucinateAppSearchWidgetContract.js` exports
`HALLUCINATE_APP_SEARCH_WIDGET_ACTION_CONTRACT`, which maps search widget
action ids to mobile ORB operations, DAT-style method names, and the
`hallucinate_app` route each action calls.

`mobile/src/orb/metaGlassesMobileOrbBridge.js` advertises the
`hallucinate_app`/mobile descriptor during edge capability registration so the
mobile edge session can bind search widget operations without importing
`hallucinate_app` runtime code.

## Validation

Focused validation target:

`python -m pytest tests/integration/test_hallucinate_app_mobile_interop.py -q`

Full supervisor target:

`python -m pytest tests/integration -q`
