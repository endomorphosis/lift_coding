# Hallucinate App / Mobile Interoperability

Evidence: objective validation repair
Path: docs/integration/hallucinate_app-mobile.md

This document records the VAI-685 repair for `VAIOS-G707` and the
`objective/interoperability/hallucinate_app-mobile` lane. The repaired evidence
proves the `interface contract hallucinate_app mobile` handoff through an
importable desktop contract, a mobile ORB descriptor, runtime handoff behavior,
and integration tests.

## Contract

The Hallucinate App desktop content browser exports
`HALLUCINATE_APP_MOBILE_SEARCH_INTEROP_CONTRACT` and
`buildHallucinateAppMobileSearchHandoff()` from
`hallucinate_app/hallucinate_app/node/dashboard/content_browser/search_interface.js`.
The builder emits a normalized `invoke_service` payload for
`/v1/mobile/orb/invoke_service` with `interaction_envelope`,
`policy_decision`, and `mediation_receipt` artifact requirements.

The mobile side exports `HALLUCINATE_APP_MOBILE_INTEROP_INTERFACE` and
`HALLUCINATE_APP_MOBILE_INTEROP_DESCRIPTOR` from
`mobile/src/orb/metaGlassesOrbDescriptors.js`. `mobile/src/orb/metaGlassesMobileOrbBridge.js`
advertises that descriptor during edge capability registration so a mobile edge
session can receive Hallucinate App search handoff traffic.

## Runtime Proof

`SearchInterface.search()` builds the mobile handoff and emits it to both the
event bus as `hallucinate_app-mobile:handoff` and direct component listeners as
`mobile-handoff`. The Hallucinate App test UI fixture in
`hallucinate_app/hallucinate_app/node/views/test_interface.html` exposes the
same routes and artifact list for manual and automated probes.

The receipt persistence surface is `hallucinate_app_mobile_interop_receipts` in
`hallucinate_app/ipfs_accelerate_py/data/duckdb/db_schema/time_series_schema.sql`.
The companion constants in
`hallucinate_app/ipfs_accelerate_py/data/duckdb/scripts/create_benchmark_schema.py`
keep the contract id, route list, and artifact refs scanner-visible without
importing the legacy benchmark schema script.

## Validation

`tests/integration/test_hallucinate_app_mobile_interop.py` validates:

- the Hallucinate App search contract and handoff payload,
- event-bus and direct-listener runtime handoff behavior,
- the mobile ORB descriptor and bridge advertisement wiring,
- the Hallucinate App test fixture and DuckDB receipt table,
- this document, the VAI-685 discovery repair record, and the objective heap.

Repair record:
`data/virtual_ai_os/discovery/2026-07-08-vai-685-objective-validation-repair.md`.
Gap record:
`data/virtual_ai_os/discovery/2026-07-08-vai-685-objective-gap-7edb316279e5.md`.
