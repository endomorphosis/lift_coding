# Hallucinate App Mobile Interop

This note records the VAIOS-G707 objective validation repair for the
`interface contract hallucinate_app mobile` evidence term.

## Contract

- Source surface: `hallucinate_app`
- Target surface: `mobile`
- Descriptor namespace: `handsfree.hallucinate_app.mobile`
- Descriptor name: `hallucinate_app_mobile_content_browser`
- Descriptor version: `0.1.0`
- Dashboard event: `hallucinate-app:mobile-interop-handoff`
- Mobile route: `mobile://hallucinate_app/content-browser/search`

The Hallucinate content browser exposes
`HALLUCINATE_APP_MOBILE_INTEROP_DESCRIPTOR` and
`buildHallucinateAppMobileSearchHandoff()` in
`hallucinate_app/hallucinate_app/node/dashboard/content_browser/search_interface.js`.
Search and filter actions emit a descriptor-shaped handoff payload containing the
query, filter, descriptor, route, `VAIOS-G707`, and the literal contract term.

The mobile app exposes the matching
`HALLUCINATE_APP_MOBILE_INTEROP_INTERFACE` and
`buildHallucinateAppMobileInteropReceipt()` in
`mobile/src/orb/metaGlassesOrbDescriptors.js`. The mobile ORB bridge advertises
that descriptor during edge capability registration so a mobile session can
accept Hallucinate App content-browser handoffs alongside the existing ORB and
display-widget interfaces.

## Runtime Handoff

1. The Hallucinate dashboard builds a handoff with action
   `ingest_content_search` or `apply_content_filter`.
2. The event bus emits `hallucinate-app:mobile-interop-handoff`.
3. Mobile normalizes the handoff into an accepted receipt with the same
   namespace, version, objective id, and route.
4. DuckDB records the event in `hallucinate_app_mobile_interop_events`; optional
   latency or throughput metrics use `hallucinate_app_mobile_benchmark_samples`.

## Validation

`tests/integration/test_hallucinate_app_mobile_interop.py` verifies the shared
descriptor terms, event name, mobile route, HTML fixture contract, DuckDB schema,
and importable benchmark schema creator. This keeps the supervisor-fed backlog
aligned with `implementation_plan/docs/23-virtual-ai-os-objective-goal-heap.md`
without adding child goals.
