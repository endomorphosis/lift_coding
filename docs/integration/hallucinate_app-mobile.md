# Hallucinate App / Mobile Interop

HAO-752 repairs the HAO-740 objective validation gap for `VAIOS-G707`
(`Interoperate hallucinate_app with mobile`), recorded in
`data/hallucinate_multimodal_control/discovery/2026-07-08-hao-752-objective-gap-7edb316279e5.md`.

## The gap

`hallucinate_app/ipfs_accelerate_py/data/duckdb/db_schema/time_series_schema.sql`
and `hallucinate_app/ipfs_accelerate_py/data/duckdb/scripts/create_benchmark_schema.py`
both referenced a
`mobile/src/orb/metaGlassesOrbDescriptors.js::HALLUCINATE_APP_MOBILE_INTEROP_CONTRACT`
export that did not exist, and `interface contract hallucinate_app mobile` had no
integration test or docs proving the runtime handoff worked end to end.

## The repair

The `interface contract hallucinate_app mobile` path is now:

- `mobile/src/orb/metaGlassesOrbDescriptors.js` exports
  `HALLUCINATE_APP_MOBILE_INTEROP_INTERFACE` (a canonical MCP-IDL style interface
  descriptor scoped to `VAIOS-G707`) and `HALLUCINATE_APP_MOBILE_INTEROP_DESCRIPTOR`,
  plus the scanner-visible `HALLUCINATE_APP_MOBILE_INTEROP_CONTRACT_ID`,
  `HALLUCINATE_APP_MOBILE_INTEROP_RECEIPTS_TABLE`,
  `HALLUCINATE_APP_MOBILE_INTEROP_ROUTES`, and
  `HALLUCINATE_APP_MOBILE_INTEROP_ARTIFACT_REFS` constants that mirror the
  Python constants added by HAO-740 in
  `hallucinate_app/ipfs_accelerate_py/data/duckdb/scripts/create_benchmark_schema.py`.
- `mobile/src/orb/metaGlassesMobileOrbBridge.js` advertises
  `HALLUCINATE_APP_MOBILE_INTEROP_DESCRIPTOR` during `registerEdgeCapabilities()`,
  alongside the pre-existing SwissKnife/mobile and ipfs_accelerate/mobile interop
  descriptors, so a mobile edge session negotiates all three interop contracts in
  one round trip.
- `hallucinate_app/hallucinate_app/node/dashboard/content_browser/search_interface.js`
  exports `HALLUCINATE_APP_MOBILE_SEARCH_INTEROP_CONTRACT` and
  `buildHallucinateAppMobileSearchHandoff()`, which builds the normalized mobile
  ORB handoff envelope (`route: /v1/mobile/orb/invoke_service`,
  `control_surface_contract_ref: control_surface_contract:hallucinate-app:remote-client`)
  emitted whenever a desktop content search runs, via the
  `hallucinate_app-mobile:handoff` event bus channel and the `mobile-handoff`
  component event.
- `hallucinate_app/hallucinate_app/node/views/test_interface.html` carries a
  machine-readable `interface contract hallucinate_app mobile` fixture
  (`#hallucinate-app-mobile-interop-contract`) and a `#mobileInteropResults`
  runtime-handoff probe area, plus a live backend check against
  `GET /v1/mobile/orb/diagnostics`.
- `hallucinate_app/ipfs_accelerate_py/data/duckdb/db_schema/time_series_schema.sql`
  defines the `hallucinate_app_mobile_interop_receipts` table that records the
  control-surface receipts (`interaction_envelope`, `policy_decision`,
  `mediation_receipt`) exchanged for every handoff.
- `hallucinate_app/ipfs_accelerate_py/data/duckdb/scripts/create_benchmark_schema.py`
  defines the matching `HALLUCINATE_APP_MOBILE_INTEROP_CONTRACT_ID`,
  `HALLUCINATE_APP_MOBILE_INTEROP_TABLE`, `HALLUCINATE_APP_MOBILE_INTEROP_ROUTES`,
  and `HALLUCINATE_APP_MOBILE_INTEROP_ARTIFACT_REFS` Python constants so the
  benchmark schema build can identify and populate interop receipt evidence.

Validation evidence lives in
`tests/integration/test_hallucinate_app_mobile_interop.py`. It loads the
JavaScript descriptor exports via a sandboxed `vm` evaluation (no build step
required), invokes `buildHallucinateAppMobileSearchHandoff()` to prove the
runtime handoff payload shape, cross-checks the DuckDB schema/script pair
against the JS descriptor's contract id/routes/table name/artifact refs, and
asserts that this objective validation repair is recorded in
`data/hallucinate_multimodal_control/discovery/2026-07-08-hao-752-objective-validation-repair.md`
and the objective heap (`implementation_plan/docs/23-virtual-ai-os-objective-goal-heap.md`).

No smaller child goals were needed: `VAIOS-G707` remains a single
interoperability goal covering `hallucinate_app` and `mobile`, and this repair
closes the objective validation gap without splitting it further.
