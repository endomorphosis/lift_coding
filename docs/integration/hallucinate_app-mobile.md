# Hallucinate App / Mobile Interop

MGW-579 repairs the VAIOS-G707 objective validation gap by making the
`interface contract hallucinate_app mobile` handoff scanner-visible in code,
tests, docs, and receipt storage. This contract note lives at
`docs/integration/hallucinate_app-mobile.md`.

## Contract

The Hallucinate App content browser exports
`HALLUCINATE_APP_MOBILE_INTEROP_DESCRIPTOR` from
`hallucinate_app/hallucinate_app/node/dashboard/content_browser/search_interface.js`.
The descriptor wraps the desktop search handoff contract:

- source surface: `hallucinate_app`
- target surface: `mobile`
- event: `hallucinate-app:mobile-interop-handoff`
- route: `/v1/mobile/orb/invoke_service`
- operation: `invoke_service`
- required artifacts: `interaction_envelope`, `policy_decision`, `mediation_receipt`

`buildHallucinateAppMobileSearchHandoff()` normalizes desktop search requests
into the mobile ORB payload. The payload carries the shared
`control_surface_contract:hallucinate-app:remote-client` reference, a
correlation id, the query/filter body, and a normalized intent targeting
`handsfree.meta_glasses.mobile.mobile_orb_bridge.invoke_service`.

## Mobile Descriptor

`mobile/src/orb/metaGlassesOrbDescriptors.js` exports the matching
`HALLUCINATE_APP_MOBILE_INTEROP_INTERFACE` and
`HALLUCINATE_APP_MOBILE_INTEROP_DESCRIPTOR`. The descriptor records VAIOS-G707,
the `objective validation repair` evidence term, the Hallucinate App search
interface, the HTML test fixture, the DuckDB receipt table, and the mobile ORB
bridge path.

`mobile/src/orb/metaGlassesMobileOrbBridge.js` advertises this descriptor during
edge capability registration when the local Hallucinate App interface CID is
present. That keeps the mobile edge session discoverable through the same ORB
registration path used by other interop descriptors.

## Receipt Evidence

`hallucinate_app/ipfs_accelerate_py/data/duckdb/db_schema/time_series_schema.sql`
defines `hallucinate_app_mobile_interop_receipts`. The table records the shared
contract id, route, operation, edge session, binding handle, correlation id,
`interaction_envelope`, `policy_decision`, `mediation_receipt`, receipt CID, and
timestamp for each Hallucinate App to mobile handoff.

`hallucinate_app/ipfs_accelerate_py/data/duckdb/scripts/create_benchmark_schema.py`
mirrors the same table, contract id, routes, and artifact names as scanner-visible
constants for schema generation workflows.

## Validation

The non-skipped integration gate is
`tests/integration/test_hallucinate_app_mobile_interop.py`. It validates the
Hallucinate App descriptor and payload builder with Node, verifies the mobile
descriptor and bridge registration wiring, checks the machine-readable fixture
in `hallucinate_app/hallucinate_app/node/views/test_interface.html`, confirms the
DuckDB receipt schema, and asserts the discovery record plus objective heap both
retain the `objective validation repair` evidence. No smaller child goals are
needed for VAIOS-G707.
