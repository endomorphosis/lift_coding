# HAO-740 Objective Validation Repair

Task: HAO-740
Attempt: 2
Goal: VAIOS-G707
Goal title: Interoperate hallucinate_app with mobile
Bundle: objective/interoperability/hallucinate_app-mobile
Gap fingerprint: 7edb316279e5a093e45d963b421d143361ec8d50
Missing evidence: objective validation repair

This repair closes the objective scanner gap filed in
`data/hallucinate_multimodal_control/discovery/2026-07-08-hao-740-objective-gap-7edb316279e5.md`
by making the `interface contract hallucinate_app mobile` handoff between the
Hallucinate App desktop search surface and the mobile ORB bridge
scanner-visible and testable.

## What was missing

The Hallucinate App side already advertised the contract:
`hallucinate_app/hallucinate_app/node/dashboard/content_browser/search_interface.js`
exported `HALLUCINATE_APP_MOBILE_SEARCH_INTEROP_CONTRACT` and
`buildHallucinateAppMobileSearchHandoff()`, and
`hallucinate_app/hallucinate_app/node/views/test_interface.html` already
carried a matching JSON fixture. The DuckDB evidence pair
(`hallucinate_app/ipfs_accelerate_py/data/duckdb/db_schema/time_series_schema.sql`
and
`hallucinate_app/ipfs_accelerate_py/data/duckdb/scripts/create_benchmark_schema.py`)
already declared `hallucinate_app_mobile_interop_receipts` and the mirrored
`HALLUCINATE_APP_MOBILE_INTEROP_*` literals.

What was missing was the **mobile side of the contract** and the tests/docs
that prove both sides agree:

- `mobile/src/orb/metaGlassesOrbDescriptors.js` did not export a
  `HALLUCINATE_APP_MOBILE_INTEROP_INTERFACE`/`_DESCRIPTOR` pair (the
  benchmark schema script comment referenced it, but it did not exist).
- `mobile/src/orb/metaGlassesMobileOrbBridge.js` did not import or advertise
  that descriptor during `registerEdgeCapabilities()`.
- `tests/integration/test_hallucinate_app_mobile_interop.py` did not exist.
- `docs/integration/hallucinate_app-mobile.md` did not exist.

## What this repair adds

- `mobile/src/orb/metaGlassesOrbDescriptors.js` now exports
  `HALLUCINATE_APP_MOBILE_INTEROP_INTERFACE` (contract id
  `interface contract hallucinate_app mobile`, objective goal `VAIOS-G707`,
  methods bound to `MOBILE_ORB_BRIDGE_OPERATIONS`) and
  `HALLUCINATE_APP_MOBILE_INTEROP_DESCRIPTOR` (schema refs for the search
  interface, test interface, time-series schema, and benchmark schema script;
  runtime handoff route `/v1/mobile/orb/invoke_service`, operation
  `invoke_service`, and interop table
  `hallucinate_app_mobile_interop_receipts`).
- `mobile/src/orb/metaGlassesMobileOrbBridge.js` imports that descriptor,
  adds it to `this.localInterfaceCids`, and advertises it (via
  `descriptorRef()` + `interop_descriptor`) in the `descriptors` list built
  by `registerEdgeCapabilities()`, alongside the existing SwissKnife and
  `external/ipfs_accelerate` interop descriptors.
- `tests/integration/test_hallucinate_app_mobile_interop.py` is the proof: it
  loads the JavaScript contract/descriptor exports on both sides, invokes
  `buildHallucinateAppMobileSearchHandoff` through Node, asserts the
  `search()` method wires the handoff into both the event-bus and
  local-listener emit paths, parses the `test_interface.html` fixture,
  cross-checks the DuckDB schema/script pair, and asserts this discovery
  record and the objective heap stay aligned.
- `docs/integration/hallucinate_app-mobile.md` documents the full path.

Proof is covered by
`tests/integration/test_hallucinate_app_mobile_interop.py` and documented in
`docs/integration/hallucinate_app-mobile.md`. This objective validation
repair keeps VAIOS-G707 aligned with the supervisor-fed objective heap
without adding smaller child goals: the missing evidence term
(`objective validation repair`) is now covered by a cohesive contract,
mobile descriptor, integration test, discovery record, and objective heap
entry.

## Validation

`python -m pytest tests/integration/test_hallucinate_app_mobile_interop.py -q`
is the focused gate for this repair. The full requested gate
`python -m pytest tests/integration -q` is the acceptance validation command
for HAO-740.
