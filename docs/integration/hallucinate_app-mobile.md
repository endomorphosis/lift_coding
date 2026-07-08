# Hallucinate App Mobile Interoperability

VAIOS-G707 uses a shared handoff contract to move a Hallucinate App content-browser search into the mobile Results surface without relying on a desktop-only UI state.

This document is the objective validation repair record for the `hallucinate_app` and `mobile` interoperability gap.

## Contract

- Contract: `handsfree.hallucinate_app/mobile-search-handoff@0.1.0`
- Action id: `mobile_hallucinate_app_search`
- Event: `hallucinate_app:mobile-search-handoff`
- Source surface: `hallucinate_app.content_browser`
- Target surface: `mobile.results`
- Profile: `swissknife.mcp++/event-envelope@0.1.0`

The canonical envelope is importable from `src/handsfree/hallucinate_app_mobile_interop.py`, exported by `hallucinate_app/hallucinate_app/node/dashboard/content_browser/search_interface.js`, and normalized on mobile by `mobile/src/utils/hallucinateAppMobileInterop.js`.

## Runtime Flow

1. Hallucinate App builds an envelope with `buildHallucinateAppMobileSearchEnvelope`.
2. `SearchInterface.launchMobileSearch` emits `hallucinate_app:mobile-search-handoff` and `content-browser:mobile-search`.
3. If the desktop bridge exposes `publishMobileHandoff` or `dispatchMobileAction`, the same envelope is sent through that bridge.
4. Mobile receives an action item with `id: mobile_hallucinate_app_search` and `mobile_payload`.
5. `executeLocalStructuredAction` validates the payload and navigates to the `Results` tab with `{ hallucinateAppSearch: payload }`.
6. Benchmark evidence can be recorded in `hallucinate_app_mobile_handoffs` and `hallucinate_app_mobile_handoff_assertions`.

## Required Payload Fields

The mobile payload uses snake_case fields:

- `contract`
- `type`
- `request_id`
- `query`
- `filters`
- `result_limit`
- `cid`
- `path`
- `source_surface`
- `target_surface`
- `metadata`

The outer envelope also carries `correlation_id`, `event_type: transport.handoff`, `handoff`, `control_plane`, `policy`, `receipts`, and `mobile_payload` so it can participate in the same MCP++/ORB evidence stream as the other mobile control-plane routes.

## Validation

Run:

```bash
python -m pytest tests/integration/test_hallucinate_app_mobile_interop.py -q
```

The broader integration gate remains:

```bash
python -m pytest tests/integration -q
```
