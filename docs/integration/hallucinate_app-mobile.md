# Hallucinate App Mobile Interop

HAO-740 proves `interface contract hallucinate_app mobile` for VAIOS-G707: the
Hallucinate App desktop search surface can hand a search request off to the
mobile ORB bridge, and mobile can advertise a matching interop descriptor
back through edge capability registration. This is the objective validation
repair for the HAO-740 attempt 2 objective gap fingerprint
`7edb316279e5` (see
`data/hallucinate_multimodal_control/discovery/2026-07-08-hao-740-objective-gap-7edb316279e5.md`
and
`data/hallucinate_multimodal_control/discovery/2026-07-08-hao-740-objective-validation-repair.md`).

## The interop path

- `hallucinate_app/hallucinate_app/node/dashboard/content_browser/search_interface.js`
  exports `HALLUCINATE_APP_MOBILE_SEARCH_INTEROP_CONTRACT` (contract id
  `interface contract hallucinate_app mobile`, route
  `/v1/mobile/orb/invoke_service`, operation `invoke_service`) and
  `buildHallucinateAppMobileSearchHandoff(query, options)`, which normalizes a
  desktop search query and filter into a handoff envelope. The
  `SearchInterface.search()` method calls this builder and emits
  `hallucinate_app-mobile:handoff` (event bus) and `mobile-handoff` (local
  listeners) so a live search reaches the mobile ORB bridge.
- `hallucinate_app/hallucinate_app/node/views/test_interface.html` renders a
  `Hallucinate App Mobile Handoff` card
  (`data-contract-id="interface contract hallucinate_app mobile"`) with a
  machine-readable JSON fixture of the same contract id, source/target
  surfaces, `/v1/mobile/orb/*` routes, and required artifacts
  (`interaction_envelope`, `policy_decision`, `mediation_receipt`) for manual
  and desktop-side probing.
- `mobile/src/orb/metaGlassesOrbDescriptors.js` exports
  `HALLUCINATE_APP_MOBILE_INTEROP_INTERFACE` and
  `HALLUCINATE_APP_MOBILE_INTEROP_DESCRIPTOR`, binding the mobile ORB bridge
  operations (`register_edge_capabilities`, `publish_glasses_event`,
  `bind_service`, `invoke_service`, `subscribe_service_updates`,
  `dispatch_glasses_response`, `revoke_binding`) to the same contract id,
  schema refs (`search_interface`, `test_interface`, `time_series_schema`,
  `benchmark_schema_script`), and runtime handoff route/operation/table
  (`hallucinate_app_mobile_interop_receipts`).
- `mobile/src/orb/metaGlassesMobileOrbBridge.js` imports that descriptor
  alongside the existing SwissKnife and `external/ipfs_accelerate` interop
  descriptors and advertises it (`descriptorRef(...)` +
  `interop_descriptor: HALLUCINATE_APP_MOBILE_INTEROP_DESCRIPTOR`) during
  `registerEdgeCapabilities()`, keeping the diagnostics contract
  (`MOBILE_ORB_DIAGNOSTICS_CONTRACT`) parseable after the wiring.
- `hallucinate_app/ipfs_accelerate_py/data/duckdb/db_schema/time_series_schema.sql`
  declares `hallucinate_app_mobile_interop_receipts`, a time-series table that
  records the control-surface receipts exchanged during the handoff
  (`contract_id`, `source_surface`, `target_surface`, `route`, `operation`,
  `edge_session_id`, `binding_handle`, `correlation_id`,
  `interaction_envelope`, `policy_decision`, `mediation_receipt`,
  `receipt_cid`), indexed by `route`.
- `hallucinate_app/ipfs_accelerate_py/data/duckdb/scripts/create_benchmark_schema.py`
  mirrors the same contract id, table name, `/v1/mobile/orb/*` routes, and
  artifact refs as self-contained literals
  (`HALLUCINATE_APP_MOBILE_INTEROP_CONTRACT_ID`,
  `HALLUCINATE_APP_MOBILE_INTEROP_TABLE`,
  `HALLUCINATE_APP_MOBILE_INTEROP_ROUTES`,
  `HALLUCINATE_APP_MOBILE_INTEROP_ARTIFACT_REFS`), so a benchmark schema build
  can identify and populate interop receipt evidence without depending on the
  JavaScript modules.

## Validation

`tests/integration/test_hallucinate_app_mobile_interop.py` is the proof:

1. Confirms `search_interface.js` and `metaGlassesMobileOrbBridge.js` remain
   valid ES modules after the contract wiring.
2. Loads the JavaScript contract/descriptor exports and asserts the contract
   id, routes, schema refs, and objective goal (`VAIOS-G707`) match across
   the desktop and mobile sides.
3. Invokes `buildHallucinateAppMobileSearchHandoff` through Node and checks
   the normalized handoff payload and intent.
4. Asserts the `search()` method wires the handoff builder into both the
   event-bus and local-listener emit paths.
5. Parses the `test_interface.html` fixture and validates it against the
   live JavaScript contract.
6. Asserts the DuckDB schema and benchmark script pair declare matching
   table/column/route evidence, and that the fixture routes stay a subset of
   the benchmark script routes.
7. Asserts this doc, the discovery objective-validation-repair record
   (`data/hallucinate_multimodal_control/discovery/2026-07-08-hao-740-objective-validation-repair.md`),
   and the objective heap
   (`implementation_plan/docs/23-virtual-ai-os-objective-goal-heap.md`) all
   record the HAO-740 objective validation repair for VAIOS-G707.

Proof is covered by
`tests/integration/test_hallucinate_app_mobile_interop.py` and documented in
`docs/integration/hallucinate_app-mobile.md`.

This objective validation repair keeps VAIOS-G707 aligned with the
supervisor-fed backlog without requiring smaller child goals: the missing
evidence term was `objective validation repair`, and it is now closed by a
cohesive contract, handoff builder, mobile descriptor, integration test,
discovery record, and objective heap entry.
